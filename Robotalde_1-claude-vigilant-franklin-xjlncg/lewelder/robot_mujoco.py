"""Robot soldador en MuJoCo para el servidor: `EntornoSoldadura` movido por la política activa (VLA, ACT o replay).

Implementa la misma interfaz `Robot` que `lewelder.robot.RobotCinematico` (ver su docstring):

    punta = await robot.soldar(tipo, anclaje, instruccion, huecos, al_moverse)

- Cada soldadura coloca la pieza (tipo, anclaje) en la escena, pone el brazo en reposo y deja mandar a la política
  con la instrucción como tarea hasta que acaba (la punta pasa el final del cordón, se levanta y se queda quieta), se
  le acaban las acciones (replay) o llega a `max_pasos`. Recorre siempre el cordón completo; `huecos` no cambia nada.
- En cada paso (30 por segundo del reloj simulado) informa la punta en el marco de la pieza por `al_moverse`, con
  gatillo False: el LED lo decide el servidor. `escala_tiempo` > 1 acelera (1 = tiempo real; si la CPU no da para
  tiempo real, va todo lo rápido que puede).
- `cambiar_politica()` vale también a mitad de una soldadura: la nueva política sigue desde donde está el brazo (el
  replay busca el fotograma grabado más parecido a la postura actual).
- **Respaldo:** si la política elegida no está disponible (falta el checkpoint o el dataset, no carga) o falla a
  mitad, cae a la siguiente de `RESPALDO` (vla → act → replay) y lo dice en `estado()` (`politica_activa`,
  `aviso_politica`, `disponibles`).
- `al_imagen(jpeg: bytes)`: si se asigna, recibe a `hz_imagen` fotogramas por segundo una imagen JPEG pequeña de la
  cámara cenital de la simulación (la tablet la enseña durante el Repaso).

Todo lo de MuJoCo (física, render EGL e inferencia) corre en un único hilo propio: el contexto EGL queda en ese hilo
y el bucle de asyncio del servidor no se bloquea.
"""
from __future__ import annotations

import asyncio
import inspect
import io
import logging
import time
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

from lewelder import contrato as c
from lewelder.contrato import Muestra, TipoPieza
from lewelder.robot import NOMBRE_POLITICA, AlMoverse, validar_politica

log = logging.getLogger("lewelder.robot_mujoco")

RESPALDO = ("vla", "act", "replay")  # orden en que se cae si una política no está disponible
PASOS_ESPERADOS = 1150  # duración típica de una demostración (para la barra de progreso)
RESOLUCION_IMAGEN = (320, 240)  # imagen de la cámara cenital que se manda a la tablet
CALIDAD_JPEG = 70


class RobotMuJoCo:
    """El SO-101 simulado con la política activa, detrás de la interfaz `Robot` del servidor."""

    tipo_robot = "mujoco"

    def __init__(self, politica: str = "vla", *, checkpoint_act: str | Path | None = None,
                 checkpoint_vla: str | Path | None = None, dataset: str | Path | None = None,
                 escala_tiempo: float = 1.0, dispositivo: str = "cpu", max_pasos: int | None = None,
                 hz_imagen: float = 8.0, politicas: dict | None = None, entorno=None):
        self.politica = validar_politica(politica)
        self.rutas = {"act": checkpoint_act, "vla": checkpoint_vla, "replay": dataset}
        self.escala_tiempo = escala_tiempo
        self.dispositivo = dispositivo
        self.hz_imagen = hz_imagen
        self.al_imagen: Callable[[bytes], None] | None = None
        self._entorno = entorno
        self._max_pasos = max_pasos
        self._hilo = ThreadPoolExecutor(max_workers=1, thread_name_prefix="mujoco")
        self._politicas: dict = dict(politicas or {})  # nombre → política cargada
        self._fallos: dict[str, str] = {}  # nombre → motivo por el que no está disponible
        self._renderer = None
        self.politica_activa: str | None = None
        self.aviso_politica: str | None = None
        self.punta: Muestra | None = None
        self.instruccion: str | None = None
        self.ocupado = False
        self.progreso = 0.0
        self._parar = False
        self._cambio_pendiente = False
        self.cambios_politica: list[tuple[float, str]] = []
        self.ultima_imagen: bytes | None = None

    # --- políticas ---------------------------------------------------------------------------------------------
    def _cargar(self, nombre: str):
        """La política `nombre` (cargándola la primera vez) o None si no está disponible. En el hilo de MuJoCo."""
        if nombre in self._politicas:
            return self._politicas[nombre]
        if nombre in self._fallos:
            return None
        from robot.politica import cargar_politica

        ruta = self.rutas.get(nombre)
        if ruta is None:
            self._fallos[nombre] = "sin checkpoint" if nombre != "replay" else "sin dataset"
            return None
        t0 = time.perf_counter()
        try:
            if nombre == "replay":
                p = cargar_politica("replay", dataset=ruta)
            else:
                p = cargar_politica(nombre, checkpoint=ruta, dispositivo=self.dispositivo)
        except Exception as e:  # noqa: BLE001 - cualquier fallo de carga deja la política fuera
            log.warning("no se pudo cargar la política %s desde %s: %s", nombre, ruta, e)
            self._fallos[nombre] = f"no carga: {e}"
            return None
        log.info("política %s cargada en %.1f s (%s)", nombre, time.perf_counter() - t0, ruta)
        self._politicas[nombre] = p
        return p

    def _candidatas(self, preferida: str) -> list[str]:
        """La preferida y, detrás, las de respaldo que van después de ella."""
        return [preferida] + [p for p in RESPALDO[RESPALDO.index(preferida) + 1:]]

    async def precargar(self, nombres: Sequence[str] | None = None) -> dict:
        """Carga las políticas en segundo plano (SmolVLA tarda) y devuelve `disponibles()`."""
        loop = asyncio.get_running_loop()
        for nombre in nombres or RESPALDO:
            await loop.run_in_executor(self._hilo, self._cargar, nombre)
        return self.disponibles()

    def disponibles(self) -> dict[str, bool | None]:
        """True (cargada), False (no disponible) o None (aún sin intentar) por política."""
        return {p: True if p in self._politicas else False if p in self._fallos else None for p in RESPALDO}

    def cambiar_politica(self, politica: str) -> None:
        self.politica = validar_politica(politica)
        self._cambio_pendiente = True
        if self.punta is not None:
            self.cambios_politica.append((self.punta.t, self.politica))

    def parar(self) -> None:
        self._parar = True

    def cerrar(self) -> None:
        def cerrar_todo():
            if self._renderer is not None:
                self._renderer.close()
                self._renderer = None
            if self._entorno is not None:
                self._entorno.cerrar()
        try:
            self._hilo.submit(cerrar_todo).result(timeout=5)
        except Exception:  # noqa: BLE001
            pass
        self._hilo.shutdown(wait=False)

    def estado(self) -> dict:
        activa = self.politica_activa or self.politica
        return {
            "tipo_robot": self.tipo_robot, "politica": self.politica, "nombre_politica": NOMBRE_POLITICA[activa],
            "politica_activa": self.politica_activa, "aviso_politica": self.aviso_politica,
            "disponibles": self.disponibles(), "ocupado": self.ocupado, "instruccion": self.instruccion,
            "progreso": round(self.progreso, 3),
            "punta": None if self.punta is None else {"x": self.punta.x, "y": self.punta.y, "z": self.punta.z},
        }

    # --- hilo de MuJoCo ----------------------------------------------------------------------------------------
    def _entorno_listo(self):
        if self._entorno is None:
            from sim.entorno import EntornoSoldadura

            self._entorno = EntornoSoldadura(render=False)
        return self._entorno

    def _activar(self, preferida: str, tipo, anclaje: str, instruccion: str, continuar: bool):
        """Elige la primera política disponible desde `preferida` y la prepara. (nombre, política, aviso)."""
        from robot.politica import PoliticaNoDisponible

        motivos = []
        for nombre in self._candidatas(preferida):
            p = self._cargar(nombre)
            if p is None:
                motivos.append(f"{NOMBRE_POLITICA[nombre]} no disponible ({self._fallos.get(nombre)})")
                continue
            try:
                p.reiniciar(tipo, anclaje, instruccion)
                if continuar and hasattr(p, "sincronizar"):
                    p.sincronizar(self._entorno.estado())
            except PoliticaNoDisponible as e:
                motivos.append(f"{NOMBRE_POLITICA[nombre]} no disponible ({e})")
                continue
            aviso = None
            if nombre != preferida:
                aviso = "; ".join(motivos) + f": se usa {NOMBRE_POLITICA[nombre]}"
                log.warning(aviso)
            return nombre, p, aviso
        raise RuntimeError("ninguna política disponible: " + "; ".join(motivos))

    def _empezar(self, tipo, anclaje: str, instruccion: str):
        ent = self._entorno_listo()
        ent.reset(anclaje, tipo)
        nombre, p, aviso = self._activar(self.politica, tipo, anclaje, instruccion, continuar=False)
        ent.render = bool(p.necesita_imagenes)
        obs = ent.observacion()
        return nombre, p, aviso, obs

    def _paso(self, p, obs, t: float):
        ent = self._entorno
        accion = p.accion(obs)
        obs = ent.step(accion)
        return obs, ent.muestra(t=t, gatillo=False)

    def _imagen_jpeg(self) -> bytes:
        import mujoco
        from PIL import Image

        ent = self._entorno
        if self._renderer is None:
            ancho, alto = RESOLUCION_IMAGEN
            self._renderer = mujoco.Renderer(ent.modelo, alto, ancho)
        self._renderer.update_scene(ent.datos, "cenital")
        imagen = Image.fromarray(self._renderer.render())
        buf = io.BytesIO()
        imagen.save(buf, format="JPEG", quality=CALIDAD_JPEG)
        return buf.getvalue()

    # --- soldar -----------------------------------------------------------------------------------------------
    async def soldar(self, tipo: TipoPieza | str, anclaje: str, instruccion: str,
                     huecos: Sequence[tuple[float, float]] | None, al_moverse: AlMoverse) -> list[Muestra]:
        from robot.politica import MAX_PASOS, DetectorFin

        tipo = TipoPieza(tipo)
        if self.ocupado:
            raise RuntimeError("el robot ya está soldando")
        self.ocupado, self._parar, self._cambio_pendiente = True, False, False
        self.instruccion = instruccion
        self.progreso = 0.0
        loop = asyncio.get_running_loop()
        ejecutar = lambda f, *a: loop.run_in_executor(self._hilo, f, *a)  # noqa: E731
        dt = 1.0 / c.FPS_DATASET
        max_pasos = self._max_pasos or MAX_PASOS
        recorrido: list[Muestra] = []
        try:
            nombre, p, aviso, obs = await ejecutar(self._empezar, tipo, anclaje, instruccion)
            self.politica_activa, self.aviso_politica = nombre, aviso
            esperados = len(getattr(p, "_acciones", ())) or PASOS_ESPERADOS
            await self._emitir_imagen(ejecutar)
            fin = DetectorFin()
            periodo_imagen = 1.0 / self.hz_imagen if self.hz_imagen > 0 else None
            ultima_imagen = -np.inf
            reloj = loop.time
            inicio = reloj()
            for i in range(max_pasos):
                if self._parar:
                    break
                if self._cambio_pendiente:  # plan B en caliente: la nueva política sigue desde aquí
                    self._cambio_pendiente = False
                    nombre, p, aviso = await ejecutar(self._activar, self.politica, tipo, anclaje, instruccion, True)
                    self.politica_activa, self.aviso_politica = nombre, aviso
                    self._entorno.render = bool(p.necesita_imagenes)
                    obs = await ejecutar(self._entorno.observacion)
                t = i * dt
                try:
                    obs, m = await ejecutar(self._paso, p, obs, t)
                except Exception as e:  # noqa: BLE001 - la política ha fallado a mitad: respaldo
                    log.exception("la política %s ha fallado", nombre)
                    self._fallos[nombre] = f"ha fallado: {e}"
                    self._politicas.pop(nombre, None)
                    siguiente = self._candidatas(nombre)[1:]
                    if not siguiente:
                        raise
                    nombre, p, aviso = await ejecutar(self._activar, siguiente[0], tipo, anclaje, instruccion, True)
                    self.politica_activa, self.aviso_politica = nombre, aviso
                    self._entorno.render = bool(p.necesita_imagenes)
                    obs = await ejecutar(self._entorno.observacion)
                    continue
                self.punta = m
                self.progreso = min(1.0, (i + 1) / esperados)
                recorrido.append(m)
                r = al_moverse(m)
                if inspect.isawaitable(r):
                    await r
                if p.terminada or fin.actualizar(m):
                    break
                if periodo_imagen is not None and t - ultima_imagen >= periodo_imagen * self.escala_tiempo:
                    ultima_imagen = t
                    await self._emitir_imagen(ejecutar)
                espera = inicio + (t + dt) / self.escala_tiempo - reloj()
                await asyncio.sleep(max(0.0, espera))
            self.progreso = 1.0
            await self._emitir_imagen(ejecutar)
        finally:
            self.ocupado = False
        return recorrido

    async def _emitir_imagen(self, ejecutar) -> None:
        if self.al_imagen is None:
            return
        try:
            self.ultima_imagen = await ejecutar(self._imagen_jpeg)
            self.al_imagen(self.ultima_imagen)
        except Exception:  # noqa: BLE001 - la imagen es un adorno: nunca para al robot
            log.exception("no se pudo mandar la imagen del robot")
