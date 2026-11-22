"""Fuentes de muestras intercambiables: real (webcam + antorcha), simulada (de punta a punta) y ratón (tablet).

Todas tienen la misma interfaz asíncrona y el servidor no sabe cuál tiene delante:

    await fuente.iniciar()
    async for evento in fuente.muestras():     # Muestra (punta vista) o Latido (no se ve la punta)
        ...
    fuente.tara()                              # antorcha vertical, cara superior hacia el avance
    fuente.empezar_pasada()                    # aviso de que empieza un examen (la simulada arranca su guion)
    fuente.pieza()                             # (tipo, anclaje) de la pieza detectada o configurada
    fuente.estado()                            # dict para la tablet
    await fuente.cerrar()

`Latido(t, gatillo)` llega en los fotogramas en los que no se ve la punta: con él el servidor sabe que el tiempo
corre (para cerrar el examen cuando el alumno termina) aunque el LED esté apagado. El LED de la antorcha del alumno
solo luce con el gatillo apretado, así que fuera de la soldadura casi todo son latidos.

- `FuenteReal`: webcam con exposición fija + `Seguidor` + `AntorchaAlumno` por USB, fusionados con `Fusion`.
- `FuenteSimulada`: lo mismo pero con `CamaraSintetica` pintando la escena y `AntorchaAlumnoVirtual` en un pty
  siguiendo una pasada sintética configurable (huecos, temblor, paradas...). Recorre todo el camino real: render →
  detección del LED y del ArUco → serie → parser → tara → ángulos → fusión. `tiempo_real=False` la acelera (para
  los tests): cada fotograma espera a que la antorcha virtual haya mandado su estado, así que el resultado no
  depende de la velocidad del ordenador.
- `FuenteRaton`: la tablet manda la posición del dedo o el ratón sobre el gemelo (`mover(x, y, gatillo)`, en el
  marco de la pieza); gatillo = mantener pulsado. Remuestrea a 30 Hz para que una punta quieta con el gatillo
  apretado cuente como punto quemado, igual que con la antorcha real.
"""
from __future__ import annotations

import asyncio
import math
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

import numpy as np

from lewelder.contrato import (
    ALTURA_PUNTA,
    ANCLAJES,
    ANGULO_TRABAJO_OBJETIVO,
    LONGITUD_CORDON,
    Muestra,
    TipoPieza,
)
from lewelder.fusion import Fusion, giro_de_pieza
from lewelder.sintetico import pasada_sintetica

FRECUENCIA_RATON = 30.0  # Hz
POSTURA_TARA = (90.0, 0.0)  # (trabajo, avance) de la antorcha vertical, la postura de la tara


@dataclass(frozen=True)
class Latido:
    """Fotograma sin punta visible: solo el tiempo (s, reloj de la fuente) y el gatillo de la antorcha."""

    t: float
    gatillo: bool = False


Evento = Muestra | Latido


@runtime_checkable
class Fuente(Protocol):
    nombre: str

    async def iniciar(self) -> None: ...
    def muestras(self) -> AsyncIterator[Evento]: ...
    def tara(self) -> bool: ...
    def empezar_pasada(self) -> None: ...
    def pieza(self) -> tuple[TipoPieza, str | None]: ...
    def estado(self) -> dict: ...
    async def cerrar(self) -> None: ...


# --- pasada simulada ---------------------------------------------------------------------------------------------
@dataclass
class ConfigPasada:
    """Parámetros de la pasada sintética que hace la `FuenteSimulada` en cada examen (ver `pasada_sintetica`)."""

    velocidad: float = 5.0
    huecos: list[tuple[float, float]] = field(default_factory=lambda: [(40.0, 55.0)])
    temblor_mm: float = 0.3
    desvio_mm: float = 0.0
    paradas: list[tuple[float, float]] = field(default_factory=list)
    angulo_trabajo: float | None = None  # None = el objetivo de la pieza
    angulo_avance: float | None = 10.0
    ruido_angulo: float = 3.0
    semilla: int = 0

    @classmethod
    def de_dict(cls, d: dict) -> ConfigPasada:
        base = cls()
        campos = {k: v for k, v in d.items() if k in base.__dataclass_fields__}
        for clave in ("huecos", "paradas"):
            if clave in campos:
                campos[clave] = [tuple(float(v) for v in par) for par in campos[clave]]
        return cls(**{**base.__dict__, **campos})

    def a_dict(self) -> dict:
        return {k: (list(map(list, v)) if k in ("huecos", "paradas") else v) for k, v in self.__dict__.items()}


# Pasadas preparadas para ensayar la demo desde la tablet.
PASADAS_PREPARADAS = {
    "con_hueco": ConfigPasada(),
    "perfecta": ConfigPasada(huecos=[], temblor_mm=0.2, ruido_angulo=2.0),
    "dos_huecos": ConfigPasada(huecos=[(20.0, 30.0), (75.0, 90.0)]),
    "temblorosa": ConfigPasada(huecos=[], temblor_mm=2.5, desvio_mm=2.0, ruido_angulo=8.0),
    "con_parada": ConfigPasada(huecos=[], paradas=[(70.0, 1.5)]),
    "rapida": ConfigPasada(huecos=[(95.0, 105.0)], velocidad=9.0),
}


class GuionPasada:
    """La pasada sintética como función del tiempo: posición de la punta, gatillo y ángulos en el instante t.

    Antes de t = 0 y después del final la antorcha está quieta, vertical y sin gatillo (la postura de la tara).
    """

    FRECUENCIA = 120.0

    def __init__(self, tipo: TipoPieza | str, config: ConfigPasada):
        tipo = TipoPieza(tipo)
        trabajo = config.angulo_trabajo if config.angulo_trabajo is not None else ANGULO_TRABAJO_OBJETIVO[tipo.value]
        self.muestras = pasada_sintetica(
            tipo, velocidad=config.velocidad, frecuencia=self.FRECUENCIA, huecos=config.huecos,
            temblor_mm=config.temblor_mm, desvio_mm=config.desvio_mm, paradas=config.paradas,
            angulo_trabajo=trabajo, angulo_avance=config.angulo_avance, ruido_angulo=config.ruido_angulo,
            semilla=config.semilla,
        )
        self.duracion = self.muestras[-1].t

    def en(self, t: float | None) -> Muestra | None:
        """Estado en el instante t (s desde que empezó la pasada); None si no hay pasada en curso."""
        if t is None or t < 0 or t > self.duracion:
            return None
        return self.muestras[min(int(round(t * self.FRECUENCIA)), len(self.muestras) - 1)]


# --- fuente simulada ---------------------------------------------------------------------------------------------
class FuenteSimulada:
    """Cámara sintética + seguimiento real + antorcha virtual (pty) siguiendo una pasada sintética.

    960x540 a 25 fps: a 640x360 cada píxel son ~1,3 mm en la pieza y el error del seguimiento (±1,5 mm) ya se
    nota en la velocidad en vivo (avisos de "rápido"/"lento" falsos); a 960x540 queda en ±0,25 mm y cada fotograma
    (render + seguimiento) cuesta ~28 ms, que caben en los 40 ms de 25 fps.
    """

    nombre = "simulada"

    def __init__(self, tipo: TipoPieza | str = TipoPieza.RECTA, anclaje: str = "B",
                 config: ConfigPasada | None = None, fps: float = 25.0, tiempo_real: bool = True,
                 ancho: int = 960, alto: int = 540, semilla: int = 0):
        self.tipo = TipoPieza(tipo)
        self.anclaje = anclaje
        self.config = config or ConfigPasada()
        self.fps = fps
        self.tiempo_real = tiempo_real
        self.ancho, self.alto, self.semilla = ancho, alto, semilla
        self.fusion = Fusion()
        self.guion = GuionPasada(self.tipo, self.config)
        self._t_inicio_pasada: float | None = None  # t de la fuente en que empezó la pasada
        self._t = 0.0
        self._k = 0
        self.virtual = self.alumno = self.camara = self.seguidor = None
        self._parar = False
        self.n_fotogramas = self.n_vistos = 0

    async def iniciar(self) -> None:
        from lewelder.antorcha import AntorchaAlumno
        from lewelder.antorcha_virtual import AntorchaAlumnoVirtual
        from lewelder.camara_sintetica import CamaraSintetica
        from lewelder.seguimiento import Seguidor

        self.virtual = AntorchaAlumnoVirtual(giro_pieza_grados=0.0)
        self.virtual.fijar(*POSTURA_TARA, False)
        self.alumno = AntorchaAlumno(self.virtual.ruta)
        self.camara = CamaraSintetica(ancho=self.ancho, alto=self.alto, semilla=self.semilla)
        self.seguidor = Seguidor(self.camara.calibracion())
        # La pieza se localiza con un primer fotograma sin LED; luego la tara (la antorcha arranca vertical).
        img, _ = await asyncio.to_thread(self.camara.renderizar, self.tipo, self.anclaje, None)
        await asyncio.to_thread(self.seguidor.refrescar_pose, img)
        if await self._esperar_antorcha(time.monotonic(), False, timeout=3.0):
            self.tara()

    async def _esperar_antorcha(self, desde: float, gatillo: bool, timeout: float = 0.2) -> bool:
        """Espera a que llegue una lectura de la antorcha posterior a `desde` con ese gatillo."""
        fin = time.monotonic() + timeout
        while time.monotonic() < fin:
            u = self.alumno.ultima
            if u is not None and u.recibido > desde and u.gatillo == gatillo:
                return True
            await asyncio.sleep(0.001)
        return False

    def _giro(self) -> float:
        pose = self.seguidor.pose if self.seguidor is not None else None
        return giro_de_pieza(self.seguidor.anclaje if self.seguidor else self.anclaje,
                             pose.en_mesa if pose is not None else None)

    def tara(self) -> bool:
        if self.alumno is None:
            return False
        self.fusion.anadir_lecturas(_vaciar(self.alumno.cola))
        return self.fusion.tara(self._giro())

    def empezar_pasada(self) -> None:
        self.fusion.reiniciar_trazo()
        self.seguidor.filtro.reiniciar()
        self._t_inicio_pasada = self._t

    def configurar(self, config: ConfigPasada | None = None, tipo: TipoPieza | str | None = None,
                   anclaje: str | None = None) -> None:
        """Cambia la pasada de los próximos exámenes y, si se pide, la pieza (tipo y anclaje)."""
        if config is not None:
            self.config = config
        if anclaje is not None and anclaje in ANCLAJES:
            self.anclaje = anclaje
        if tipo is not None:
            self.tipo = TipoPieza(tipo)
        self.guion = GuionPasada(self.tipo, self.config)
        self._t_inicio_pasada = None
        if self.seguidor is not None:
            self.seguidor.reiniciar()

    def pieza(self) -> tuple[TipoPieza, str | None]:
        if self.seguidor is not None and self.seguidor.pose is not None:
            return self.seguidor.pose.tipo, self.seguidor.anclaje
        return self.tipo, self.anclaje

    def estado(self) -> dict:
        tipo, anclaje = self.pieza()
        return {
            "fuente": self.nombre, "tipo": tipo.value, "anclaje": anclaje,
            "antorcha": self.alumno is not None and self.alumno.conectado,
            "camara": self.seguidor is not None and self.seguidor.pose is not None,
            "tara": self.fusion.q_tara is not None, "pasada": self.config.a_dict(),
            "pasada_en_curso": self._estado_guion() is not None,
        }

    def _estado_guion(self, t: float | None = None) -> Muestra | None:
        if self._t_inicio_pasada is None:
            return None
        return self.guion.en((self._t if t is None else t) - self._t_inicio_pasada)

    def _fotograma(self, led) -> Muestra | None:
        img, _ = self.camara.renderizar(self.tipo, self.anclaje, led=led)
        return self.seguidor.procesar(img, self._t)

    async def muestras(self) -> AsyncIterator[Evento]:
        reloj0 = time.monotonic()
        while not self._parar:
            self._t = self._k / self.fps
            if self.tiempo_real:
                espera = reloj0 + self._t - time.monotonic()
                if espera > 0:
                    await asyncio.sleep(espera)
                elif espera < -0.5:  # muy retrasados (el ordenador no da abasto): se salta tiempo
                    reloj0 = time.monotonic() - self._t
            estado = self._estado_guion()
            gatillo = bool(estado.gatillo) if estado is not None else False
            if estado is not None:
                self.virtual.fijar(estado.angulo_trabajo or POSTURA_TARA[0], estado.angulo_avance or 0.0, gatillo)
            else:
                self.virtual.fijar(*POSTURA_TARA, False)
            fijado = time.monotonic()
            led = (estado.x, estado.y, estado.z) if estado is not None and gatillo else None
            posicion = await asyncio.to_thread(self._fotograma, led)
            if not self.tiempo_real:
                await self._esperar_antorcha(fijado, gatillo)
            self.fusion.anadir_lecturas(_vaciar(self.alumno.cola))
            muestra = self.fusion.fusionar(posicion, self._t, None, self._giro())
            self.n_fotogramas += 1
            self._k += 1
            if muestra is not None:
                self.n_vistos += 1
                yield muestra
            else:
                yield Latido(self._t, self.fusion._gatillo_anterior)
            if not self.tiempo_real and self._k % 10 == 0:
                await asyncio.sleep(0)  # deja respirar al bucle de eventos

    async def cerrar(self) -> None:
        self._parar = True
        for d in (self.alumno, self.virtual):
            if d is not None:
                await asyncio.to_thread(d.cerrar if hasattr(d, "cerrar") else d.parar)


def _vaciar(cola) -> list:
    lecturas = []
    while True:
        try:
            lecturas.append(cola.get_nowait())
        except Exception:  # queue.Empty
            return lecturas


# --- fuente real -------------------------------------------------------------------------------------------------
class FuenteReal:
    """Webcam con exposición fija + `Seguidor` + `AntorchaAlumno` por USB.

    El puerto de la antorcha se busca solo (`buscar_antorchas`) si no se da y `buscar` es True. La calibración de
    la cámara se carga de `calibracion` (JSON de `CalibracionCamara.guardar`) o, si no hay, se usa una aproximada.
    """

    nombre = "real"

    def __init__(self, indice_camara: int = 0, puerto_antorcha: str | None = None, calibracion: str | None = None,
                 ancho: int = 1280, alto: int = 720, exposicion: float | None = -7,
                 tipo_por_defecto: TipoPieza | str = TipoPieza.RECTA, buscar: bool = True):
        self.indice_camara, self.puerto_antorcha, self.ruta_calibracion = indice_camara, puerto_antorcha, calibracion
        self.buscar = buscar
        self.ancho, self.alto, self.exposicion = ancho, alto, exposicion
        self.tipo_por_defecto = TipoPieza(tipo_por_defecto)
        self.fusion = Fusion()
        self.cap = self.alumno = self.seguidor = None
        self._t0 = time.monotonic()
        self._parar = False
        self.error: str | None = None

    async def iniciar(self) -> None:
        from lewelder.antorcha import AntorchaAlumno, buscar_antorchas
        from lewelder.seguimiento import CalibracionCamara, Seguidor, abrir_webcam

        if self.ruta_calibracion:
            calib = CalibracionCamara.cargar(self.ruta_calibracion)
        else:
            calib = CalibracionCamara.por_defecto(self.ancho, self.alto)
        self.seguidor = Seguidor(calib)
        self.cap = await asyncio.to_thread(abrir_webcam, self.indice_camara, self.ancho, self.alto, self.exposicion)
        if self.cap is None:
            self.error = f"no se pudo abrir la webcam {self.indice_camara}"
        puerto = self.puerto_antorcha
        if puerto is None and self.buscar:
            puerto = (await asyncio.to_thread(buscar_antorchas)).get("alumno")
        if puerto is None:
            self.error = (self.error + "; " if self.error else "") + "no se encuentra la antorcha del alumno"
        else:
            self.alumno = AntorchaAlumno(puerto)

    def _giro(self) -> float:
        pose = self.seguidor.pose if self.seguidor is not None else None
        return giro_de_pieza(self.seguidor.anclaje if self.seguidor else None,
                             pose.en_mesa if pose is not None else None)

    def tara(self) -> bool:
        if self.alumno is None:
            return False
        self.fusion.anadir_lecturas(_vaciar(self.alumno.cola))
        return self.fusion.tara(self._giro())

    def empezar_pasada(self) -> None:
        self.fusion.reiniciar_trazo()
        if self.seguidor is not None:
            self.seguidor.filtro.reiniciar()

    def pieza(self) -> tuple[TipoPieza, str | None]:
        if self.seguidor is not None and self.seguidor.pose is not None:
            return self.seguidor.pose.tipo, self.seguidor.anclaje
        return self.tipo_por_defecto, None

    def estado(self) -> dict:
        tipo, anclaje = self.pieza()
        return {
            "fuente": self.nombre, "tipo": tipo.value, "anclaje": anclaje,
            "antorcha": self.alumno is not None and self.alumno.conectado,
            "camara": self.cap is not None, "pieza_vista": self.seguidor is not None and self.seguidor.pose is not None,
            "tara": self.fusion.q_tara is not None, "error": self.error,
        }

    def _leer(self):
        ok, img = self.cap.read()
        instante = time.monotonic()  # instante de captura (aprox.: al volver de read)
        return (img if ok else None), instante

    async def muestras(self) -> AsyncIterator[Evento]:
        while not self._parar:
            if self.cap is None:
                await asyncio.sleep(0.1)
                yield Latido(time.monotonic() - self._t0)
                continue
            img, instante = await asyncio.to_thread(self._leer)
            t = instante - self._t0
            posicion = None
            if img is not None:
                posicion = await asyncio.to_thread(self.seguidor.procesar, img, t)
            if self.alumno is not None:
                self.fusion.anadir_lecturas(_vaciar(self.alumno.cola))
            muestra = self.fusion.fusionar(posicion, t, instante, self._giro())
            yield muestra if muestra is not None else Latido(t, self.fusion._gatillo_anterior)

    async def cerrar(self) -> None:
        self._parar = True
        if self.alumno is not None:
            await asyncio.to_thread(self.alumno.cerrar)
        if self.cap is not None:
            self.cap.release()


# --- fuente ratón ------------------------------------------------------------------------------------------------
class FuenteRaton:
    """Se "suelda" arrastrando el dedo o el ratón sobre el gemelo de la tablet (gatillo = mantener pulsado)."""

    nombre = "raton"

    def __init__(self, tipo: TipoPieza | str = TipoPieza.RECTA, anclaje: str = "B",
                 frecuencia: float = FRECUENCIA_RATON, reloj=time.monotonic):
        self.tipo = TipoPieza(tipo)
        self.anclaje = anclaje
        self.periodo = 1.0 / frecuencia
        self.reloj = reloj
        self._t0 = reloj()
        self._x = self._y = None
        self._gatillo = False
        self._soltado = False  # hay que emitir la muestra de "gatillo soltado"
        self._parar = False

    def mover(self, x: float, y: float, gatillo: bool) -> None:
        """Posición del dedo en el marco de la pieza (mm) y si está pulsando."""
        if not (math.isfinite(x) and math.isfinite(y)):
            return
        self._x, self._y = float(np.clip(x, -40, LONGITUD_CORDON + 40)), float(np.clip(y, -60, 60))
        if self._gatillo and not gatillo:
            self._soltado = True
        self._gatillo = bool(gatillo)

    def soltar(self) -> None:
        if self._gatillo:
            self._soltado = True
        self._gatillo = False

    def tara(self) -> bool:
        return True  # sin IMU: no hay nada que tarar

    def empezar_pasada(self) -> None:
        self._soltado = False

    def configurar(self, tipo: TipoPieza | str | None = None, anclaje: str | None = None) -> None:
        if tipo is not None:
            self.tipo = TipoPieza(tipo)
        if anclaje is not None and anclaje in ANCLAJES:
            self.anclaje = anclaje

    def pieza(self) -> tuple[TipoPieza, str | None]:
        return self.tipo, self.anclaje

    def estado(self) -> dict:
        return {"fuente": self.nombre, "tipo": self.tipo.value, "anclaje": self.anclaje, "antorcha": False,
                "camara": False, "tara": False}

    def evento(self) -> Evento:
        """El evento de este instante (lo que `muestras` emite en cada periodo)."""
        t = self.reloj() - self._t0
        if self._x is not None and (self._gatillo or self._soltado):
            gatillo = self._gatillo
            self._soltado = False
            # Sin IMU no hay ángulos: el ángulo no puntúa (su peso se reparte entre el resto).
            return Muestra(t=t, x=self._x, y=self._y, z=ALTURA_PUNTA, gatillo=gatillo)
        return Latido(t, False)

    async def iniciar(self) -> None:
        self._t0 = self.reloj()

    async def muestras(self) -> AsyncIterator[Evento]:
        siguiente = time.monotonic()
        while not self._parar:
            yield self.evento()
            siguiente += self.periodo
            await asyncio.sleep(max(0.0, siguiente - time.monotonic()))

    async def cerrar(self) -> None:
        self._parar = True
