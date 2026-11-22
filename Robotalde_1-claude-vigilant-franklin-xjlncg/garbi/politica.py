"""Habilidad de limpieza con política aprendida (SmolVLA, o un ACT como respaldo), supervisada por lo programado.

    habilidad = HabilidadVLA("salidas/garbi_smolvla", ctl, percepcion)   # carpeta de `lerobot-train`
    robot = RobotVivo(mundo, percepcion, habilidad)

El VLA recibe la frase de la orden (`ORDEN_AGUJERO` o `ORDEN_ALFOMBRILLA`), las dos cámaras y el estado, y decide
el movimiento: a dónde ir según dónde ve la viruta y cómo barrerla. Lo programado lo envuelve:
- **Velocidad**: cada acción se limita a `MAX_GRADOS_FOTOGRAMA` respecto a la anterior.
- **Altura**: si la acción dejaría el borde de la boca a menos de 1 mm de la superficie, se descarta y se repite la
  anterior.
- **Fin**: termina cuando la percepción ya no ve viruta en la zona de la orden, o cuando la propia política se queda
  quieta `QUIETA_S` (las demostraciones acaban así), siempre tras `MIN_S`; y como mucho a los `MAX_S`.

Cámaras: el dataset de Garbi las llama `top` y `wrist`; SmolVLA se entrena con `--rename_map` a `camera1`/`camera2`.

Ejecución asíncrona (`asincrona=True`): SmolVLA tarda ~1,2 s por chunk de 50 acciones en una CPU de 4 núcleos (medido)
y el chunk dura 1,67 s a 30 Hz. En modo síncrono el robot se pararía 1,2 s cada 1,7 s. En asíncrono, cuando quedan
`margen` acciones en la cola se pide el siguiente chunk con la observación de ese momento; al llegar, se descartan las
acciones que corresponden al tiempo ya pasado y se sustituye la cola. En el robot real el cálculo va en un hilo
(`latencia_simulada=None`); en la simulación se entrega tras `latencia_simulada` s de tiempo simulado, para que sea
reproducible.

Límite medido (test): con un solo cálculo en marcha, cada chunk nuevo aporta (n - latencia) acciones útiles, así que la
ejecución solo es fluida si la latencia no pasa de la mitad de lo que dura un chunk: 0,83 s con 50 acciones a 30 Hz.
SmolVLA en CPU (1,2 s) no llega: hace falta GPU o `factor_tiempo=2` (cada acción dura 2 fotogramas: el movimiento va a
la mitad de velocidad y el límite sube a 1,67 s). ACT (~70 ms por chunk de 100 en CPU) no tiene este problema.
"""
from __future__ import annotations

from collections import deque
from pathlib import Path

import numpy as np

from garbi import contrato as g
from garbi.control import ControlBoca

RENOMBRE_SMOLVLA = {
    "observation.images.top": "observation.images.camera1",
    "observation.images.wrist": "observation.images.camera2",
}
MAX_GRADOS_FOTOGRAMA = 3.0  # 90 °/s a 30 Hz
MIN_S, MAX_S = 1.5, 12.0
VIRUTA_RESTANTE = 0  # puntos de viruta vistos por debajo de los que se da por limpio
QUIETA_S, QUIETA_GRADOS = 0.5, 0.3


class HabilidadVLA:
    def __init__(self, checkpoint: str | Path, ctl: ControlBoca, percepcion=None, dispositivo: str = "cpu",
                 politica=None, asincrona: bool = False, latencia_simulada: float | None = None, margen: int = 45,
                 factor_tiempo: int = 1):
        if politica is None:
            from robot.politica import PoliticaLeRobot

            politica = PoliticaLeRobot(checkpoint, dispositivo=dispositivo, renombre=RENOMBRE_SMOLVLA)
        self.politica = politica
        self.nombre = f"política aprendida ({getattr(politica, 'nombre', 'vla')})"
        self.ctl = ctl
        self.percepcion = percepcion
        self.orden = ""
        self.pasos = 0
        self.previa: np.ndarray | None = None
        self.descartadas = 0  # acciones que la supervisión rechazó por altura
        self.historial: deque = deque(maxlen=int(QUIETA_S * g.FPS))
        self.asincrona = asincrona
        self.latencia_simulada = latencia_simulada
        self.margen = margen  # acciones que quedan en la cola cuando se pide el siguiente chunk
        self._cola: deque = deque()
        self._pedido: dict | None = None  # chunk en cálculo: paso en que se pidió y resultado
        self.esperas = 0  # fotogramas en que la cola estaba vacía (el robot se quedó quieto esperando)
        self.factor_tiempo = factor_tiempo  # cada acción de la política dura este número de fotogramas

    def empezar(self, orden, q, percepcion) -> None:
        self.orden = orden
        self.percepcion = percepcion
        self.pasos = 0
        self.previa = np.asarray(q, float)
        self.descartadas = 0
        self.historial: deque = deque(maxlen=int(QUIETA_S * g.FPS))
        self._cola, self._pedido, self.esperas = deque(), None, 0
        self.politica.reiniciar("garbi", "", orden)

    def _limpio(self) -> bool:
        if self.percepcion is None:
            return False
        donde = "alfombrilla" if self.orden == g.ORDEN_ALFOMBRILLA else "tabla"
        return len(self.percepcion.viruta(donde)) <= VIRUTA_RESTANTE

    def accion(self, q, obs) -> np.ndarray | None:
        t = self.pasos / g.FPS
        if t >= MAX_S or (t >= MIN_S and (self._limpio() or self._quieta())):
            return None
        self.pasos += 1
        a = self._siguiente_asincrona(obs) if self.asincrona else np.asarray(self.politica.accion(obs), float)
        a = self.previa + np.clip(a - self.previa, -MAX_GRADOS_FOTOGRAMA, MAX_GRADOS_FOTOGRAMA)
        suelo = g.ALFOMBRILLA_GROSOR if self.orden == g.ORDEN_ALFOMBRILLA else g.ALTURA_CARA_TABLA
        if self.ctl.borde_inferior(a) < suelo + 1.0:
            self.descartadas += 1
            a = self.previa
        self.previa = a
        self.historial.append(a)
        return a

    # --- ejecución asíncrona -----------------------------------------------------------------------------------
    def _pedir(self, obs) -> None:
        paso = self.pasos
        if self.latencia_simulada is not None:
            self._pedido = {"paso": paso, "chunk": self.politica.chunk(obs),
                            "listo_en": paso + int(round(self.latencia_simulada * g.FPS))}
            return
        import threading

        pedido = {"paso": paso, "chunk": None, "listo_en": None}

        def calcular():
            pedido["chunk"] = self.politica.chunk(obs)

        pedido["hilo"] = threading.Thread(target=calcular, daemon=True)
        pedido["hilo"].start()
        self._pedido = pedido

    def _recoger(self) -> None:
        p = self._pedido
        listo = p["chunk"] is not None and (p["listo_en"] is None or self.pasos >= p["listo_en"])
        if not listo:
            return
        chunk = np.repeat(np.asarray(p["chunk"], float), self.factor_tiempo, axis=0)
        transcurridos = self.pasos - p["paso"]  # fotogramas del chunk que ya corresponden al pasado
        self._cola = deque(chunk[transcurridos:])
        self._pedido = None

    def _siguiente_asincrona(self, obs) -> np.ndarray:
        if self._pedido is not None:
            self._recoger()
        if self._pedido is None and len(self._cola) <= self.margen:
            self._pedir(obs)
            self._recoger()  # con latencia 0 llega en el acto
        if self._cola:
            return np.asarray(self._cola.popleft(), float)
        self.esperas += 1
        return self.previa  # la cola se vació: quieto hasta que llegue el chunk

    def _quieta(self) -> bool:
        h = self.historial
        return len(h) == h.maxlen and float(np.max(np.ptp(np.array(h), axis=0))) < QUIETA_GRADOS
