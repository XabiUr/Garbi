"""Grabar episodios del paso 7 (limpiar la zona del agujero) en un LeRobotDataset (especificación técnica, M5).

Dos maneras, con el mismo grabador:
- `GrabadorLimpiezas`: episodio a episodio (lo usa `herramientas/garbi_grabar.py` con las demostraciones
  automáticas de la simulación).
- `GrabadorCiclo`: dentro del ciclo de Garbi (`python -m garbi.correr --grabar RUTA`), cada LIMPIAR es un episodio.
  Se guarda solo si la percepción da el agujero por limpio al revisarlo (filtro de M3); si queda viruta (repaso), si
  salta una guardia y entra el respaldo, o si el ciclo se corta, se descarta y se apunta por qué.

Cada fotograma: `observation.images.top`, `observation.images.wrist` (reducidas a la resolución del dataset con
`cv2.INTER_AREA`, como hace `HabilidadACT` al ejecutar), `observation.state` (6), `action` (6) y la tarea
`TAREA_LIMPIEZA`. `observation.state` es **lo que el ciclo da a la habilidad**: la orden anterior (`Ciclo.q`), que
en LIMPIAR es también lo que recibe ACT; así entrenamiento y ejecución ven lo mismo. Los episodios y los descartes se
apuntan en `episodios_garbi_limpiar.json`, dentro del dataset.
"""
from __future__ import annotations

import json
import shutil
import time
from pathlib import Path

import numpy as np

from garbi.tipos import HZ_CONTROL, TAREA_ACERCAMIENTO, TAREA_LIMPIEZA

ARCHIVO_EPISODIOS = "episodios_garbi_limpiar.json"
ARCHIVO_EPISODIOS_ACERCAMIENTO = "episodios_garbi_acercamiento.json"
TOLERANCIA_PARTIDA = 8.0  # °: máx. de las 4 articulaciones al empezar un acercamiento respecto a la postura prudente
RESOLUCION_DATASET = (640, 480)  # (ancho, alto): la de las cámaras; en la simulación en CPU se graba más pequeño


def _reducir(img, resolucion) -> np.ndarray:
    import cv2

    img = np.ascontiguousarray(img)
    ancho, alto = resolucion
    if img.shape[:2] == (alto, ancho):
        return img
    return cv2.resize(img, (ancho, alto), interpolation=cv2.INTER_AREA)


class GrabadorLimpiezas:
    """LeRobotDataset con un episodio por limpieza. `empezar(**info)` → `fotograma(...)` × N → `terminar(guardar,
    **info)`; al final `cerrar()` escribe el json de episodios y descartes y devuelve el resumen."""

    def __init__(self, salida, repo_id: str = "local/garbi_limpiar", resolucion=RESOLUCION_DATASET,
                 sobrescribir: bool = False, extra: dict | None = None, tarea: str = TAREA_LIMPIEZA,
                 archivo: str = ARCHIVO_EPISODIOS):
        from lerobot.datasets.lerobot_dataset import LeRobotDataset

        from garbi.demostraciones import ROBOT_TYPE, caracteristicas

        self.salida = Path(salida)
        if self.salida.exists():
            if not sobrescribir:
                raise FileExistsError(f"{self.salida} ya existe (usa --sobrescribir)")
            shutil.rmtree(self.salida)
        self.repo_id = repo_id
        self.tarea = tarea
        self.archivo = archivo
        self.resolucion = tuple(resolucion)
        self.ds = LeRobotDataset.create(repo_id=repo_id, fps=int(HZ_CONTROL), features=caracteristicas(resolucion),
                                        root=self.salida, robot_type=ROBOT_TYPE, use_videos=True,
                                        image_writer_threads=4)
        self.episodios: list[dict] = []
        self.extra = dict(extra or {})
        self._actual: dict | None = None
        self._t0 = 0.0
        self._cerrado = False

    @property
    def grabando(self) -> bool:
        return self._actual is not None

    @property
    def guardados(self) -> int:
        return sum(e["guardado"] for e in self.episodios)

    @classmethod
    def para_acercamiento(cls, salida, repo_id: str = "local/garbi_acercamiento", resolucion=RESOLUCION_DATASET,
                          sobrescribir: bool = False, extra: dict | None = None) -> GrabadorLimpiezas:
        """El mismo grabador para el acercamiento (tarea `TAREA_ACERCAMIENTO`, json de episodios propio)."""
        return cls(salida, repo_id, resolucion, sobrescribir, extra, tarea=TAREA_ACERCAMIENTO,
                   archivo=ARCHIVO_EPISODIOS_ACERCAMIENTO)

    def empezar(self, **info) -> None:
        if self._actual is not None:
            self.terminar(False, motivo="sin terminar")
        self._actual = {"intento": len(self.episodios), **info, "fotogramas": 0}
        self._t0 = time.perf_counter()

    def fotograma(self, imagenes: dict, estado, accion) -> None:
        """`imagenes`: {"top", "wrist"} (RGB, cualquier tamaño); `estado` y `accion`: 6 articulaciones (grados)."""
        frame = {"observation.state": np.asarray(estado, np.float32), "action": np.asarray(accion, np.float32),
                 "task": self.tarea}
        for cam in ("top", "wrist"):
            frame[f"observation.images.{cam}"] = _reducir(imagenes[cam], self.resolucion)
        self.ds.add_frame(frame)
        self._actual["fotogramas"] += 1

    def terminar(self, guardar: bool, **info) -> dict:
        ep = {**self._actual, **info, "guardado": bool(guardar and self._actual["fotogramas"] > 0),
              "episodio_dataset": None}
        if ep["guardado"]:
            ep["episodio_dataset"] = self.ds.num_episodes
            self.ds.save_episode(parallel_encoding=False)  # sin fork: el render usa hilos
        elif self._actual["fotogramas"] > 0:
            self.ds.clear_episode_buffer()
        ep["segundos"] = round(time.perf_counter() - self._t0, 2)
        self.episodios.append(ep)
        self._actual = None
        return ep

    def resumen(self) -> dict:
        guardados = self.guardados
        motivos: dict[str, int] = {}
        for e in self.episodios:
            if not e["guardado"]:
                m = str(e.get("motivo", "sucio"))
                motivos[m] = motivos.get(m, 0) + 1
        return {"repo_id": self.repo_id, "tarea": self.tarea, "resolucion": list(self.resolucion),
                **self.extra, "intentos": len(self.episodios), "guardados": guardados,
                "descartados": len(self.episodios) - guardados, "motivos_descarte": motivos,
                "episodios": self.episodios}

    def escribir_json(self) -> dict:
        r = self.resumen()
        (self.salida / self.archivo).write_text(json.dumps(r, indent=2, ensure_ascii=False, default=float))
        return r

    def cerrar(self) -> dict:
        if self._cerrado:
            return self.resumen()
        if self._actual is not None:
            self.terminar(False, motivo="cortado")
        self.ds.finalize()
        self._cerrado = True
        return self.escribir_json()


class GrabadorCiclo:
    """Graba cada LIMPIAR del `Ciclo` como episodio. Llamar a `paso(ciclo, orden, imagenes)` después de cada
    `ciclo.paso` (lo hace `garbi.correr.bucle` con `al_ordenar`). `verdad(i)` (opcional, simulación): partículas que
    quedan de verdad en el agujero i, solo para el json."""

    def __init__(self, grabador: GrabadorLimpiezas, verdad=None):
        self.g = grabador
        self.verdad = verdad
        self._estado_previo = None  # orden del paso anterior: lo que el ciclo da a la habilidad como «state»
        self._ultimo = None  # estado del ciclo en el paso anterior
        self._pendiente: dict | None = None  # episodio acabado esperando el veredicto de REVISAR
        self._agujero = None
        self._respaldo = False

    def necesita_imagenes(self, ciclo) -> bool:
        """El bucle solo renderiza (o lee las cámaras) cuando hace falta: en LIMPIAR."""
        return ciclo.estado.value == "limpiar"

    def paso(self, ciclo, orden, imagenes: dict) -> None:
        estado = orden.estado
        respaldo = ciclo.respaldo is not None and getattr(ciclo, "_hab_activa", None) is ciclo.respaldo
        if estado == "limpiar" and self._ultimo != "limpiar":
            self._decidir(ciclo, None)  # por si quedaba uno pendiente
            self._agujero = ciclo._agujero
            self.g.empezar(agujero=self._agujero, agujero_madera=np.round(ciclo.agujeros[self._agujero], 1).tolist(),
                           habilidad=getattr(ciclo.habilidad, "nombre", type(ciclo.habilidad).__name__),
                           t=round(float(ciclo._t), 2), repaso=int(getattr(ciclo, "_repasos", 0)))
            self._respaldo = False
        if estado == "limpiar" and self.g.grabando:
            if respaldo:
                self._respaldo = True
            if imagenes.get("top") is not None and imagenes.get("wrist") is not None and self._estado_previo is not None:
                self.g.fotograma(imagenes, self._estado_previo, orden.q)
        if self._ultimo == "limpiar" and estado != "limpiar" and self.g.grabando:
            self._pendiente = {"respaldo": self._respaldo}
        if self._pendiente is not None and self._ultimo == "revisar" and estado != "revisar":
            self._decidir(ciclo, estado)
        elif self._pendiente is not None and estado not in ("revisar", "limpiar"):
            self._decidir(ciclo, estado)  # no pasó por REVISAR (guardia): se descarta
        self._estado_previo = np.asarray(orden.q, float).copy()
        self._ultimo = estado

    def _decidir(self, ciclo, estado) -> None:
        if self._pendiente is None:
            return
        i = self._agujero
        limpio = i in ciclo.limpios
        info = {"limpio_percepcion": bool(limpio), "siguiente": estado}
        if self.verdad is not None:
            info["viruta_verdad"] = int(self.verdad(i))
        if self._pendiente["respaldo"]:
            self.g.terminar(False, motivo="guardia: pasó al respaldo", **info)
        elif not limpio:
            self.g.terminar(False, motivo="sucio según la percepción" if estado == "ir_a_limpiar" else
                            f"no limpio ({estado})", **info)
        else:
            self.g.terminar(True, **info)
        self._pendiente = None
        self.g.escribir_json()

    def cerrar(self) -> dict:
        self._pendiente = None
        return self.g.cerrar()


# --- acercamiento (solución final, 20-11) ----------------------------------------------------------------------------
EMPEZAR, TERMINAR, PAUSAR, REANUDAR = "empezar", "terminar", "pausar", "reanudar"


class CorteAcercamiento:
    """Corte automático de los episodios del acercamiento por la percepción: empieza al clavarse la broca y termina al
    levantarla (ACT no decide el final). Si se levanta, pausa (los fotogramas quedan en espera); si vuelve a clavarse
    antes de `tolerancia` s, reanuda; si no, termina. Interfaz `evento(t, escena, grabando)` → "empezar", "terminar",
    "pausar", "reanudar" o None (la usa también `herramientas/garbi_teleop_grabar.py`).

    «Clavada»: `escena.broca.clavada` si la percepción lo da; si no, `garbi.acercamiento.DetectorClavada` (apoyada
    `T_CLAVADA` s en la madera, con el taladro agarrado y en la zona de taladro, con histéresis), el mismo que usa el
    ciclo final para empezar y acabar el ACERCAMIENTO. `exigir_agarre=False`: no mira `Taladro.agarrado` (percepción
    sin manos; en el robot real, si MediaPipe o el color no ven la mano, con agarre exigido no se graba nada).
    `aviso`: por qué no corta aunque la broca esté apoyada (p. ej. sin mano en el taladro), o ''; cambia solo cuando
    cambia el motivo (`aviso_nuevo` es True en el paso en que cambia), para el log."""

    def __init__(self, tolerancia: float = 0.0, exigir_agarre: bool = True, zona: bool = True):
        from garbi.acercamiento import DetectorClavada

        self.tolerancia = float(tolerancia)
        self.exigir_agarre = bool(exigir_agarre)
        self.detector = DetectorClavada(zona=zona, exigir_agarre=exigir_agarre)
        self._levantada_desde: float | None = None
        self._anterior: bool | None = None
        self._libre = False  # se ha visto la broca sin apoyar
        self.aviso = ""
        self.aviso_nuevo = False

    def clavada(self, escena) -> bool | None:
        if escena is None:
            return None
        directa = getattr(escena.broca, "clavada", None)
        aviso = self.detector.por_que_no(escena)
        self.aviso_nuevo, self.aviso = aviso != self.aviso, aviso
        self.detector.actualizar(escena)
        if directa is not None:
            self._libre = self._libre or not directa
            return bool(directa)
        self._libre = self._libre or not self.detector.candidata(escena)
        return self.detector.clavada

    def evento(self, t: float, escena, grabando: bool) -> str | None:
        clavada = self.clavada(escena)
        if clavada is None:
            return None
        anterior, self._anterior = self._anterior, clavada
        if not grabando:
            self._levantada_desde = None
            # solo al clavarse (flanco) y si antes se ha visto sin apoyar: si se arranca con la broca ya clavada, se
            # espera a que se levante y se vuelva a clavar
            return EMPEZAR if clavada and anterior is False and self._libre else None
        if clavada:
            if self._levantada_desde is not None:
                self._levantada_desde = None
                return REANUDAR
            return None
        if self._levantada_desde is None:
            self._levantada_desde = t
            return TERMINAR if self.tolerancia <= 0 else PAUSAR
        if t - self._levantada_desde >= self.tolerancia:
            self._levantada_desde = None
            return TERMINAR
        return None


class GrabadorAcercamiento:
    """Episodios del ACERCAMIENTO en un LeRobotDataset (top, wrist, state, action, tarea `TAREA_ACERCAMIENTO`), cortados
    solos por `CorteAcercamiento`: desde que la broca se clava hasta que se levanta. Vale para la simulación (el
    acercamiento programado dentro del ciclo final) y para el robot real con teleoperación.

        g = GrabadorAcercamiento(GrabadorLimpiezas.para_acercamiento(ruta, repo_id, (640, 480)))
        en cada paso: g.paso(escena, accion, {"top": ..., "wrist": ...})    # accion: la orden de este paso
        g.invalidar("guardia")       # (opcional) descarta el episodio en curso
        g.cerrar()

    `observation.state` es por defecto **la orden anterior** (la `accion` del paso anterior), el mismo convenio que el
    ciclo final da a `HabilidadACT` en el ACERCAMIENTO (`obs["state"] = Ciclo.q`); con `estado=` se pasa otro (p. ej.
    la postura medida, si se ejecuta igual). Episodios de menos de `min_fotogramas` se descartan.

    Postura de partida: con `partida(escena, estado) → grados` (la diferencia de la postura al empezar con la
    prudente de la broca, `garbi.acercamiento.postura_prudente`), los episodios que no parten de ella (más de
    `tolerancia_partida` grados) se descartan: ACT empieza siempre desde la postura prudente al ejecutar."""

    def __init__(self, grabador: GrabadorLimpiezas, corte: CorteAcercamiento | None = None,
                 min_fotogramas: int = 15, info=None, partida=None, tolerancia_partida: float = TOLERANCIA_PARTIDA):
        self.g = grabador
        self.corte = corte or CorteAcercamiento()
        self.min_fotogramas = min_fotogramas
        self.info = info  # función () → dict con lo que se apunta al empezar cada episodio
        self.partida = partida
        self.tolerancia_partida = float(tolerancia_partida)
        self._anterior = None  # la acción del paso anterior
        self._espera: list = []  # fotogramas durante la pausa (se añaden si se reanuda)
        self._invalido: str | None = None
        self._pausado = False

    @property
    def grabando(self) -> bool:
        return self.g.grabando

    def invalidar(self, motivo: str) -> None:
        if self.g.grabando and self._invalido is None:
            self._invalido = motivo

    def paso(self, escena, accion, imagenes: dict, estado=None) -> str | None:
        """Un paso del bucle. Devuelve el evento del corte (o None)."""
        accion = np.asarray(accion, float)
        estado = self._anterior if estado is None else np.asarray(estado, float)
        evento = self.corte.evento(escena.t, escena, self.g.grabando)
        if evento == EMPEZAR:
            info = self.info() if self.info is not None else {}
            dif = None if self.partida is None or estado is None else self.partida(escena, estado)
            if dif is not None:
                info["dif_partida"] = round(float(dif), 1)
            self.g.empezar(t=round(float(escena.t), 2), **info)
            self._espera, self._invalido, self._pausado = [], None, False
            if self.partida is not None and (dif is None or dif > self.tolerancia_partida):
                self._invalido = "no parte de la postura prudente" + ("" if dif is None else f" ({dif:.0f}°)")
        elif evento == PAUSAR:
            self._pausado = True
        elif evento == REANUDAR:
            for f in self._espera:
                self.g.fotograma(*f)
            self._espera, self._pausado = [], False
        elif evento == TERMINAR:
            self._terminar("levantada")
        hay = imagenes.get("top") is not None and imagenes.get("wrist") is not None
        if self.g.grabando and hay and estado is not None:
            f = (dict(imagenes), estado.copy(), accion.copy())
            if self._pausado:
                self._espera.append(f)
            else:
                self.g.fotograma(*f)
        self._anterior = accion.copy()
        return evento

    def _terminar(self, motivo: str) -> dict:
        n = self.g._actual["fotogramas"]
        guardar = self._invalido is None and n >= self.min_fotogramas
        info = {"fin": motivo}
        if not guardar:
            info["motivo"] = self._invalido or f"corto ({n} fotogramas)"
        self._espera, self._pausado = [], False
        ep = self.g.terminar(guardar, **info)
        self.g.escribir_json()
        return ep

    def cerrar(self) -> dict:
        if self.g.grabando:
            self._invalido = self._invalido or "cortado"
            self._terminar("cortado")
        return self.g.cerrar()
