"""El fantasma rival: la pasada del robot como referencia y la carrera en vivo del juez contra ella.

Antes de que suelde el juez, el robot suelda la misma junta; su pasada (medida con el mismo seguimiento, una lista de
`Muestra` en el marco del cordón) es el **fantasma** que hay que batir (spec v2, 0.1 y 1.5).

- `Fantasma`: referencia por tramo (velocidad, ángulos, calidad y tiempos) y dónde iba el robot en cada instante.
  El reloj del fantasma empieza en su primera muestra soldando dentro del cordón.
- `Carrera`: compara al juez con el fantasma muestra a muestra (pensada para pintar la tablet a 30 Hz: interpolar y
  poco más; la evaluación completa solo se recalcula cuando el juez cierra un tramo).

Dos ideas distintas, las dos en pantalla:
- **Ritmo** (quién va por delante): `ventaja_mm` = x del juez - x del fantasma en el mismo instante de su pasada;
  `ventaja_s` = cuánto antes (+) o después (-) que el robot ha llegado el juez a donde está. La x del juez es su
  **frente**: lo más lejos que ha soldado (no retrocede con el temblor).
- **Calidad** (quién va ganando): suma de la calidad de los tramos ya cerrados (`metricas.calidad_tramo`, 0-1 por
  tramo) del juez frente a la del fantasma en esos mismos tramos. Correr más no gana: soldar mejor, sí.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict, dataclass, field

import numpy as np

from lewelder.contrato import LONGITUD_CORDON, N_TRAMOS, TAMANO_TRAMO, Muestra
from lewelder.metricas import (
    Z_LEVANTADA,
    EvaluadorEnVivo,
    Resultado,
    calidades,
    clave_tipo,
    evaluar_pasada,
)

PASO_X = 0.5  # mm: resolución de la tabla x → tiempo del fantasma
EMPATE_TRAMO = 0.05  # diferencia de calidad (0-1) por debajo de la cual un tramo queda en empate
EMPATE_TOTAL = 0.25  # diferencia de calidad acumulada (suma de tramos) por debajo de la cual se va empatado
HZ_TRAZO = 10.0  # muestras por segundo del trazo del fantasma que se manda a la tablet

JUEZ, FANTASMA, EMPATE = "juez", "fantasma", "empate"


def _r(v, decimales: int = 2):
    return None if v is None or not np.isfinite(v) else round(float(v), decimales)


def _quien(diferencia: float, umbral: float) -> str:
    """Quién gana con esta diferencia de calidad (juez - fantasma)."""
    if diferencia > umbral:
        return JUEZ
    if diferencia < -umbral:
        return FANTASMA
    return EMPATE


@dataclass
class TramoFantasma:
    indice: int
    velocidad: float | None  # mm/s
    angulo_trabajo: float | None  # grados (media del tramo)
    angulo_avance: float | None
    calidad: float  # 0-1
    t_inicio: float | None  # s desde que empezó a soldar el robot (None si no llegó)
    t_fin: float | None


class Fantasma:
    """Referencia del robot a partir de su pasada.

    `apoyo`: el robot se mide con el criterio de la v1 (punta a menos de `Z_LEVANTADA`): en la simulación suelda a
    3 mm sin tocar y su pasada es la referencia de ritmo y ángulo, no se le examina de apoyo.
    """

    def __init__(self, muestras: Sequence[Muestra], tipo, nivel: str = "oficial", *, apoyo: float = Z_LEVANTADA):
        self.tipo = clave_tipo(tipo)
        self.tipo_original = tipo
        self.nivel = nivel
        self.muestras = list(muestras)
        self.resultado: Resultado = evaluar_pasada(self.muestras, self.tipo, nivel, apoyo=apoyo)
        self.calidades = calidades(self.resultado)

        soldando = [m for m in self.muestras if m.gatillo and m.z <= apoyo and 0.0 <= m.x <= LONGITUD_CORDON]
        self.t0 = soldando[0].t if soldando else None
        self.duracion = (soldando[-1].t - soldando[0].t) if soldando else 0.0
        # x → primer instante (desde t0) en que el frente del robot llegó a x (inf si no llegó)
        self._xs = np.arange(0.0, LONGITUD_CORDON + PASO_X / 2, PASO_X)
        if soldando:
            t = np.array([m.t for m in soldando]) - self.t0
            frente = np.maximum.accumulate(np.clip([m.x for m in soldando], 0.0, LONGITUD_CORDON))
            i = np.searchsorted(frente, self._xs - 1e-9, "left")
            self._ts = np.where(i < len(t), t[np.minimum(i, len(t) - 1)], np.inf)
            # Para x_en: los instantes en que el frente avanza (estrictamente creciente en t)
            self._t_frente, self._x_frente = t, frente
        else:
            self._ts = np.full(len(self._xs), np.inf)
            self._t_frente = self._x_frente = np.zeros(0)
        # Serie completa (para pintar el fantasma tal cual se movió)
        self._t = np.array([m.t for m in self.muestras], dtype=float) - (self.t0 or 0.0)

        self.tramos: list[TramoFantasma] = []
        for i, tr in enumerate(self.resultado.tramos):
            ang_t, ang_a = self._angulos_tramo(i)
            ini, fin = self.t_en(i * TAMANO_TRAMO), self.t_en((i + 1) * TAMANO_TRAMO)
            self.tramos.append(TramoFantasma(i, _r(tr.velocidad_media, 3), _r(ang_t), _r(ang_a), self.calidades[i],
                                             _r(ini, 3), _r(fin, 3)))

    def _angulos_tramo(self, i: int) -> tuple[float | None, float | None]:
        a, b = i * TAMANO_TRAMO, (i + 1) * TAMANO_TRAMO
        en = [m for m in self.muestras if m.gatillo and a <= m.x < b]
        trabajo = [m.angulo_trabajo for m in en if m.angulo_trabajo is not None]
        avance = [m.angulo_avance for m in en if m.angulo_avance is not None]
        return (float(np.mean(trabajo)) if trabajo else None, float(np.mean(avance)) if avance else None)

    # --- consultas (marco del cordón, s desde que empieza a soldar) ---------------------------------------------
    def t_en(self, x: float) -> float | None:
        """Instante (s desde su inicio) en que el fantasma llegó a x (mm), o None si no llegó."""
        if self.t0 is None:
            return None
        i = int(np.clip(np.ceil(float(x) / PASO_X - 1e-9), 0, len(self._xs) - 1))
        t = self._ts[i]
        return None if not np.isfinite(t) else float(t)

    def x_en(self, tau: float) -> float:
        """Frente del fantasma (mm) a los `tau` s de empezar a soldar."""
        if not len(self._t_frente):
            return 0.0
        return float(np.interp(tau, self._t_frente, self._x_frente))

    def tramo_en(self, x: float) -> TramoFantasma:
        return self.tramos[int(np.clip(float(x) // TAMANO_TRAMO, 0, N_TRAMOS - 1))]

    def posicion(self, tau: float) -> dict:
        """Dónde estaba la punta del robot a los `tau` s (para pintar su antorcha fantasma)."""
        if not self.muestras:
            return {"x": 0.0, "y": 0.0, "z": 0.0, "angulo_trabajo": None, "angulo_avance": None, "gatillo": False}
        i = int(np.clip(np.searchsorted(self._t, tau), 0, len(self.muestras) - 1))
        m = self.muestras[i]
        x = float(np.clip(m.x, 0.0, LONGITUD_CORDON)) if tau < 0 else m.x
        return {"x": _r(x, 1), "y": _r(m.y, 1), "z": _r(m.z, 1), "angulo_trabajo": _r(m.angulo_trabajo, 1),
                "angulo_avance": _r(m.angulo_avance, 1), "gatillo": bool(m.gatillo)}

    def a_dict(self) -> dict:
        """Todo lo que la tablet necesita para pintar el fantasma (una vez, al empezar la ronda)."""
        trazo = []
        if self.t0 is not None:
            for tau in np.arange(0.0, self.duracion + 1e-9, 1.0 / HZ_TRAZO):
                p = self.posicion(float(tau))
                trazo.append({"t": _r(tau, 2), "x": p["x"], "y": p["y"], "trabajo": p["angulo_trabajo"],
                              "avance": p["angulo_avance"]})
        return {"tipo": self.tipo, "duracion": _r(self.duracion), "nota": self.resultado.nota,
                "tramos": [asdict(t) for t in self.tramos], "trazo": trazo}


@dataclass
class ResultadoCarrera:
    ganador: str  # "juez" | "fantasma" | "empate"
    por_tramo: list[str]  # ganador de cada tramo
    tramos_ganados: dict[str, int]
    calidad_juez: float  # suma de calidades de tramo (0-24)
    calidad_fantasma: float
    duracion_juez: float  # s soldando
    duracion_fantasma: float
    calidades_juez: list[float] = field(default_factory=list)
    calidades_fantasma: list[float] = field(default_factory=list)

    def a_dict(self) -> dict:
        return asdict(self)


class Carrera:
    """El juez contra el fantasma, muestra a muestra.

    `evaluador`: el `EvaluadorEnVivo` del juez si ya hay uno (el del servidor); entonces lo alimenta quien llama y
    la carrera solo lo lee. Sin él, la carrera crea el suyo y lo alimenta en `anadir`.
    """

    def __init__(self, fantasma: Fantasma, nivel: str | None = None, *, tipo=None, apoyo: float | None = None,
                 evaluador: EvaluadorEnVivo | None = None):
        self.fantasma = fantasma
        self._propio = evaluador is None
        self.evaluador = evaluador or EvaluadorEnVivo(tipo if tipo is not None else fantasma.tipo_original,
                                                      nivel or fantasma.nivel, apoyo=apoyo)
        self.t0: float | None = None  # primera muestra soldando del juez
        self.frente: float | None = None
        self._calidad_juez: list[float] = []  # tramos ya cerrados, congelados al cerrarse
        self.va_ganando = EMPATE
        self._estado: dict = self._vacio()

    @staticmethod
    def _vacio() -> dict:
        return {"t": None, "x_juez": None, "x_fantasma": None, "ventaja_mm": None, "ventaja_s": None,
                "dif_trabajo": None, "dif_avance": None, "velocidad_juez": None, "velocidad_fantasma": None,
                "tramos_cerrados": 0, "calidad_juez": 0.0, "calidad_fantasma": 0.0,
                "tramos_ganados": {JUEZ: 0, FANTASMA: 0, EMPATE: 0}, "va_ganando": EMPATE, "lider_cambia": None,
                "fantasma": None}

    def anadir(self, m: Muestra) -> dict:
        """Añade una muestra del juez y devuelve el estado de la carrera (serializable a JSON)."""
        ev = self.evaluador
        if self._propio:
            ev.anadir(m)
        soldando = m.gatillo and m.z <= ev.apoyo and 0.0 <= m.x <= LONGITUD_CORDON
        if soldando:
            if self.t0 is None:
                self.t0 = m.t
            self.frente = m.x if self.frente is None else max(self.frente, m.x)
        self._cerrar_tramos(ev.tramos_cerrados())

        e = dict(self._estado)
        e["lider_cambia"] = None
        if self.t0 is not None:
            f = self.fantasma
            tau = m.t - self.t0
            x_f = f.x_en(tau)
            t_f = f.t_en(self.frente)
            tr_f = f.tramo_en(self.frente)
            e.update({
                "t": _r(tau), "x_juez": _r(self.frente), "x_fantasma": _r(x_f),
                "ventaja_mm": _r(self.frente - x_f), "ventaja_s": None if t_f is None else _r(t_f - tau),
                "dif_trabajo": None if m.angulo_trabajo is None or tr_f.angulo_trabajo is None
                else _r(m.angulo_trabajo - tr_f.angulo_trabajo, 1),
                "dif_avance": None if m.angulo_avance is None or tr_f.angulo_avance is None
                else _r(m.angulo_avance - tr_f.angulo_avance, 1),
                "velocidad_juez": _r(ev.velocidad), "velocidad_fantasma": tr_f.velocidad,
                "fantasma": f.posicion(tau),
            })
        n = len(self._calidad_juez)
        cj, cf = sum(self._calidad_juez), sum(self.fantasma.calidades[:n])
        por_tramo = [_quien(a - b, EMPATE_TRAMO) for a, b in zip(self._calidad_juez, self.fantasma.calidades)]
        lider = _quien(cj - cf, EMPATE_TOTAL)
        if lider != self.va_ganando:
            e["lider_cambia"] = lider if lider != EMPATE else None
            self.va_ganando = lider
        e.update({"tramos_cerrados": n, "calidad_juez": _r(cj, 3), "calidad_fantasma": _r(cf, 3),
                  "tramos_ganados": {k: por_tramo.count(k) for k in (JUEZ, FANTASMA, EMPATE)},
                  "va_ganando": lider})
        self._estado = e
        return e

    def _cerrar_tramos(self, cerrados: int) -> None:
        if cerrados > len(self._calidad_juez):
            q = calidades(self.evaluador.evaluacion())
            self._calidad_juez += q[len(self._calidad_juez):cerrados]

    def estado(self) -> dict:
        return dict(self._estado)

    def terminar(self) -> ResultadoCarrera:
        """Resultado final con la evaluación completa del juez (todos los tramos, también los no cerrados)."""
        final = self.evaluador.terminar()
        cj, cf = calidades(final), self.fantasma.calidades
        por_tramo = [_quien(a - b, EMPATE_TRAMO) for a, b in zip(cj, cf)]
        return ResultadoCarrera(
            ganador=_quien(sum(cj) - sum(cf), EMPATE_TOTAL),
            por_tramo=por_tramo,
            tramos_ganados={k: por_tramo.count(k) for k in (JUEZ, FANTASMA, EMPATE)},
            calidad_juez=_r(sum(cj), 3),
            calidad_fantasma=_r(sum(cf), 3),
            duracion_juez=_r(final.duracion_s),
            duracion_fantasma=_r(self.fantasma.duracion),
            calidades_juez=cj,
            calidades_fantasma=list(cf),
        )
