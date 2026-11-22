"""Puntuación arcade de LeWelder: puntos por tramo, combos, ritmo, penalizaciones, bonus, ranking del día e insignias.

La nota de oficio (`metricas`) sigue debajo y alimenta los puntos (spec v2, 0.1): cada tramo de 5 mm vale según su
calidad (`metricas.calidad_tramo`, 0-1), y encima va el espectáculo.

Reglas (los números están abajo, en MAYÚSCULAS)
-----------------------------------------------
- **Tramo:** `PUNTOS_TRAMO` x calidad x multiplicador de combo, redondeado. Un tramo sin cubrir da 0.
- **Combo:** cada tramo **bien soldado** seguido (`metricas.tramo_bien`) alarga la racha; el multiplicador sube uno
  cada `COMBO_CADA` tramos (x1 los 4 primeros, x2 del 5.º al 8.º, x3 del 9.º al 12.º, x4 desde el 13.º) hasta
  `COMBO_MAX`. Un tramo que no está bien rompe la racha (y puntúa x1 según su calidad).
- **Ritmo constante:** al final, la suma de los tramos se multiplica por `multiplicador_ritmo(cv)`: x1,25 con el
  coeficiente de variación de la velocidad <= 0,05 y x1 desde 0,25 (lineal entre medias).
- **Penalizaciones:** -`PENAL_QUEMADO` por punto quemado, -`PENAL_SIN_APOYO` por episodio de gatillo sin apoyar.
- **Bonus:** +`BONUS_FANTASMA` si gana al fantasma del robot (calidad acumulada, ver `fantasma`), +`BONUS_PERFECTA`
  si la ronda es perfecta (24 tramos bien y con calidad >= `TRAMO_PERFECTO`, ritmo constante, sin quemados ni
  soldar al aire).
- El total nunca baja de 0.

Un tramo cubierto vale `PUNTOS_TRAMO` x (`BASE_CUBIERTO` + (1 - `BASE_CUBIERTO`) x calidad) x combo: cubrir ya da
la mitad, y un cordón entero pero flojo no se queda en nada.

Calibración (pasadas sintéticas, nivel oficial): perfecta 7.200 x 1,25 + 1.000 = **10.000** (+1.000 si además gana
al robot); rondas normales (un hueco, un quemado, mano temblona, prisa, ángulo malo...) entre ~2.500 y ~8.700; mala
(dos huecos, un quemado y temblor) ~1.650; sin soldar, 0. Ver `tests/test_puntuacion.py`.

En vivo, `MarcadorEnVivo` da los eventos para la tablet en el momento en que pasan ("COMBO x4", "¡QUEMADO!",
"¡ADELANTAS AL ROBOT!") y la suma de los puntos de sus eventos es exactamente la cuenta final de `puntuar` cuando el
juez suelda de principio a fin sin volver atrás (los tramos se puntúan al dejarlos atrás y ya no cambian).

Ranking del día (`Ranking`): JSON persistente con todas las partidas; el top 10 es del día. Empates: queda delante
quien lo hizo antes (igualar no adelanta ni es récord). Insignias por junta superada (`aprobado` en un nivel) y nivel
del jugador: aprendiz → oficial (las dos juntas superadas) → maestro (las dos superadas en oficial o maestro).
"""
from __future__ import annotations

import json
import logging
import os
import re
import tempfile
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from pathlib import Path

import numpy as np

from lewelder.contrato import N_TRAMOS, NOMBRE_JUNTA, TOLERANCIAS, Muestra, TipoJunta
from lewelder.fantasma import FANTASMA, JUEZ, Carrera, Fantasma, ResultadoCarrera
from lewelder.metricas import EvaluadorEnVivo, Resultado, calidad_tramo, clave_tipo, tramo_bien

log = logging.getLogger("lewelder.puntuacion")

# --- números del juego ---------------------------------------------------------------------------------------------
PUNTOS_TRAMO = 100
BASE_CUBIERTO = 0.5  # un tramo cubierto ya vale la mitad; la otra mitad, según su calidad
TRAMO_PERFECTO = 0.95  # calidad mínima de cada tramo en una ronda perfecta
CV_PERFECTA = 0.15  # y ritmo constante: coeficiente de variación de la velocidad como mucho este
COMBO_CADA = 4  # tramos bien seguidos para subir el multiplicador
COMBO_MAX = 4
RITMO_MAX = 1.25
CV_RITMO_PERFECTO = 0.05  # coeficiente de variación de la velocidad con el que el ritmo da el máximo
CV_RITMO_NULO = 0.25  # desde aquí (el umbral de "ritmo irregular" de las métricas) no hay multiplicador
PENAL_QUEMADO = 500
PENAL_SIN_APOYO = 300
BONUS_FANTASMA = 1000
BONUS_PERFECTA = 1000

TOP = 10
NIVELES = tuple(TOLERANCIAS)  # ("aprendiz", "oficial", "maestro")
JUNTAS = tuple(j.value for j in TipoJunta)

# Textos de la tablet
TEXTO_COMBO = "COMBO x{}"
TEXTO_COMBO_ROTO = "COMBO ROTO"
TEXTO_QUEMADO = "¡QUEMADO!"
TEXTO_SIN_APOYO = "¡APOYA LA ANTORCHA!"
TEXTO_ADELANTAS = "¡ADELANTAS AL ROBOT!"
TEXTO_TE_ADELANTA = "¡EL ROBOT TE ADELANTA!"
TEXTO_RITMO = "RITMO x{:.2f}"
TEXTO_PERFECTA = "¡RONDA PERFECTA!"
TEXTO_GANAS = "¡HAS GANADO AL ROBOT!"
TEXTO_RECORD = "¡NUEVO RÉCORD!"
TEXTO_RANKING = "¡ENTRAS EN EL RANKING: PUESTO {}!"
TEXTO_INSIGNIA = "¡INSIGNIA: {}!"
TEXTO_ASCENSO = "¡ASCIENDES A {}!"


# --- reglas --------------------------------------------------------------------------------------------------------
def multiplicador_combo(racha: int) -> int:
    """Multiplicador del tramo número `racha` de una racha de tramos bien soldados (1 = primero)."""
    return int(min(1 + max(racha - 1, 0) // COMBO_CADA, COMBO_MAX))


def multiplicador_ritmo(cv: float) -> float:
    """x1,25 con ritmo constante (cv <= 0,05), x1 con ritmo irregular (cv >= 0,25), lineal entre medias."""
    f = np.clip((CV_RITMO_NULO - cv) / (CV_RITMO_NULO - CV_RITMO_PERFECTO), 0.0, 1.0)
    return round(float(1.0 + (RITMO_MAX - 1.0) * f), 3)


@dataclass
class Evento:
    """Algo que la tablet celebra (o lamenta) en el momento en que pasa."""

    t: float | None  # s (reloj de las muestras); None en los eventos del final de la ronda
    tipo: str  # tramo, combo, combo_roto, quemado, sin_apoyo, adelantas, te_adelanta, ritmo, perfecta, gana_fantasma
    texto: str
    puntos: int = 0
    datos: dict = field(default_factory=dict)

    def a_dict(self) -> dict:
        return asdict(self)


class _Racha:
    """Suma de tramos con combos, tramo a tramo (la usan la cuenta final y el marcador en vivo)."""

    def __init__(self):
        self.racha = 0
        self.combo_max = 0
        self.tramos_bien = 0
        self.suma = 0
        self.por_tramo: list[dict] = []

    @property
    def multiplicador(self) -> int:
        return multiplicador_combo(self.racha) if self.racha else 1

    def tramo(self, indice: int, calidad: float, bien: bool, cubierto: bool,
              t: float | None = None) -> list[Evento]:
        eventos = []
        if bien:
            antes = self.multiplicador if self.racha else 0
            self.racha += 1
            self.tramos_bien += 1
            self.combo_max = max(self.combo_max, self.racha)
            mult = multiplicador_combo(self.racha)
            if mult > max(antes, 1):
                eventos.append(Evento(t, "combo", TEXTO_COMBO.format(mult), 0, {"multiplicador": mult}))
        else:
            if self.racha > COMBO_CADA:  # solo se lamenta si había combo de verdad
                eventos.append(Evento(t, "combo_roto", TEXTO_COMBO_ROTO, 0, {"racha": self.racha}))
            self.racha = 0
            mult = 1
        puntos = int(round(PUNTOS_TRAMO * mult * (BASE_CUBIERTO + (1.0 - BASE_CUBIERTO) * calidad))) if cubierto else 0
        self.suma += puntos
        self.por_tramo.append({"indice": indice, "calidad": calidad, "bien": bien, "multiplicador": mult,
                               "puntos": puntos})
        eventos.insert(0, Evento(t, "tramo", f"+{puntos}", puntos,
                                 {"indice": indice, "calidad": calidad, "multiplicador": mult, "bien": bien}))
        return eventos


@dataclass
class Puntuacion:
    total: int
    desglose: dict[str, int | float]  # tramos, multiplicador_ritmo, bonus_ritmo, penal_*, bonus_*
    combo_max: int  # racha más larga de tramos bien soldados
    tramos_bien: int
    perfecta: bool
    gana_fantasma: bool
    por_tramo: list[dict]  # indice, calidad, bien, multiplicador, puntos
    eventos_finales: list[Evento] = field(default_factory=list)  # ritmo, perfecta, gana_fantasma (para la tablet)

    def a_dict(self) -> dict:
        return asdict(self)


def _finales(resultado: Resultado, suma_tramos: int, carrera: ResultadoCarrera | None) -> tuple[list[Evento], dict]:
    """Eventos y partidas del final de la ronda: ritmo, ronda perfecta y fantasma."""
    mult = multiplicador_ritmo(resultado.cv_velocidad) if suma_tramos > 0 else 1.0
    bonus_ritmo = int(round(suma_tramos * (mult - 1.0)))
    tol = resultado.tolerancia_mm
    perfecta = (
        len(resultado.tramos) == N_TRAMOS and resultado.n_quemados == 0 and resultado.n_sin_apoyo == 0
        and resultado.cv_velocidad <= CV_PERFECTA
        and all(tramo_bien(tr, tol) and calidad_tramo(tr, tol) >= TRAMO_PERFECTO for tr in resultado.tramos)
    )
    gana = carrera is not None and carrera.ganador == JUEZ
    eventos = []
    if bonus_ritmo > 0:
        eventos.append(Evento(None, "ritmo", TEXTO_RITMO.format(mult), bonus_ritmo, {"multiplicador": mult}))
    if perfecta:
        eventos.append(Evento(None, "perfecta", TEXTO_PERFECTA, BONUS_PERFECTA))
    if gana:
        eventos.append(Evento(None, "gana_fantasma", TEXTO_GANAS, BONUS_FANTASMA))
    partes = {"multiplicador_ritmo": mult, "bonus_ritmo": bonus_ritmo,
              "bonus_perfecta": BONUS_PERFECTA if perfecta else 0, "bonus_fantasma": BONUS_FANTASMA if gana else 0}
    return eventos, partes


def puntuar(resultado: Resultado, carrera: ResultadoCarrera | None = None) -> Puntuacion:
    """Cuenta final de la ronda a partir de la evaluación de oficio (y del resultado contra el fantasma, si hubo)."""
    racha = _Racha()
    tol = resultado.tolerancia_mm
    for tr in resultado.tramos:
        racha.tramo(tr.indice, calidad_tramo(tr, tol), tramo_bien(tr, tol), tr.cubierto)
    finales, partes = _finales(resultado, racha.suma, carrera)
    desglose = {
        "tramos": racha.suma,
        **partes,
        "penal_quemados": -PENAL_QUEMADO * resultado.n_quemados,
        "penal_sin_apoyo": -PENAL_SIN_APOYO * resultado.n_sin_apoyo,
    }
    total = sum(v for k, v in desglose.items() if k != "multiplicador_ritmo")
    return Puntuacion(
        total=int(max(0, total)),
        desglose=desglose,
        combo_max=racha.combo_max,
        tramos_bien=racha.tramos_bien,
        perfecta=partes["bonus_perfecta"] > 0,
        gana_fantasma=partes["bonus_fantasma"] > 0,
        por_tramo=racha.por_tramo,
        eventos_finales=finales,
    )


# --- marcador en vivo ----------------------------------------------------------------------------------------------
class MarcadorEnVivo:
    """Puntos, combos y eventos mientras suelda el juez (y la carrera contra el fantasma, si lo hay).

    Uso en el servidor: `eventos = marcador.anadir(muestra)` en cada muestra; `marcador.estado()` para pintar;
    `marcador.avisos` son los avisos de oficio de la última muestra (los del `EvaluadorEnVivo`); al acabar,
    `marcador.terminar()` da la `Puntuacion` (con los eventos del final en `eventos_finales`).
    """

    def __init__(self, tipo, nivel: str = "oficial", *, fantasma: Fantasma | None = None,
                 apoyo: float | None = None):
        self.evaluador = EvaluadorEnVivo(tipo, nivel, apoyo=apoyo)
        self.carrera = Carrera(fantasma, evaluador=self.evaluador) if fantasma is not None else None
        self._racha = _Racha()
        self._cerrados = 0
        self._n_sin_apoyo = 0
        self._en_parada = False
        self.puntos = 0  # suma de los eventos hasta ahora (sin el ritmo ni los bonus del final)
        self.avisos: list[str] = []
        self.eventos: list[Evento] = []

    def anadir(self, m: Muestra) -> list[Evento]:
        ev = self.evaluador
        self.avisos = ev.anadir(m)
        eventos: list[Evento] = []
        if ev.en_parada and not self._en_parada:
            eventos.append(Evento(m.t, "quemado", TEXTO_QUEMADO, -PENAL_QUEMADO, {"x": round(m.x, 1)}))
        self._en_parada = ev.en_parada
        if ev.n_sin_apoyo > self._n_sin_apoyo:
            self._n_sin_apoyo = ev.n_sin_apoyo
            eventos.append(Evento(m.t, "sin_apoyo", TEXTO_SIN_APOYO, -PENAL_SIN_APOYO, {"x": round(m.x, 1)}))
        cerrados = ev.tramos_cerrados()
        if cerrados > self._cerrados:
            r = ev.evaluacion()
            for i in range(self._cerrados, cerrados):
                tr = r.tramos[i]
                eventos += self._racha.tramo(i, calidad_tramo(tr, r.tolerancia_mm), tramo_bien(tr, r.tolerancia_mm),
                                             tr.cubierto, m.t)
            self._cerrados = cerrados
        if self.carrera is not None:
            lider = self.carrera.anadir(m)["lider_cambia"]
            if lider == JUEZ:
                eventos.append(Evento(m.t, "adelantas", TEXTO_ADELANTAS))
            elif lider == FANTASMA:
                eventos.append(Evento(m.t, "te_adelanta", TEXTO_TE_ADELANTA))
        self.puntos += sum(e.puntos for e in eventos)
        self.eventos += eventos
        return eventos

    def estado(self) -> dict:
        """Lo que pinta la tablet a 30 Hz (serializable a JSON)."""
        return {
            "puntos": int(max(0, self.puntos)),
            "racha": self._racha.racha,
            "combo": self._racha.multiplicador,
            "combo_max": self._racha.combo_max,
            "tramos_puntuados": self._cerrados,
            "ritmo": multiplicador_ritmo(self._cv_actual()),
            "carrera": None if self.carrera is None else self.carrera.estado(),
            "oficio": self.evaluador.estado(),
        }

    def _cv_actual(self) -> float:
        return self.evaluador.evaluacion().cv_velocidad if self._cerrados else CV_RITMO_NULO

    def terminar(self) -> Puntuacion:
        """Cuenta final (`puntuar` con la evaluación completa). Los puntos del marcador pasan a ser los finales."""
        resultado = self.evaluador.terminar()
        p = puntuar(resultado, self.carrera.terminar() if self.carrera is not None else None)
        self.puntos = p.total
        return p


# --- ranking del día, insignias y niveles --------------------------------------------------------------------------
_INICIALES = re.compile(r"^[A-ZÑ]{3}$")


def _iniciales(texto: str) -> str:
    ini = str(texto).strip().upper()
    if not _INICIALES.match(ini):
        raise ValueError(f"iniciales no válidas: {texto!r} (tres letras)")
    return ini


def _nivel(nivel: str) -> str:
    if nivel not in NIVELES:
        raise ValueError(f"nivel desconocido: {nivel!r} (válidos: {', '.join(NIVELES)})")
    return nivel


def nombre_insignia(junta, nivel: str) -> str:
    return f"unión {NOMBRE_JUNTA[TipoJunta(clave_tipo(junta))]} · {nivel}"


def nivel_jugador(insignias: Iterable[tuple[str, str]]) -> str:
    """aprendiz → oficial (las dos juntas superadas en cualquier nivel) → maestro (las dos en oficial o más)."""
    mejor = {}
    for junta, nivel in insignias:
        mejor[junta] = max(mejor.get(junta, -1), NIVELES.index(nivel))
    alcanzado = 0
    for k in range(len(NIVELES) - 1):  # para subir al nivel k+1 hacen falta todas las juntas en el nivel k o más
        if all(mejor.get(j, -1) >= k for j in JUNTAS):
            alcanzado = k + 1
    return NIVELES[alcanzado]


@dataclass
class Partida:
    iniciales: str
    puntos: int
    junta: str
    nivel: str
    fecha: str  # AAAA-MM-DD
    hora: str  # HH:MM:SS

    def a_dict(self) -> dict:
        return asdict(self)


@dataclass
class ResumenRonda:
    """Lo que pasa al anotar una ronda: puesto, récord, insignia y ascenso (con sus eventos para la tablet)."""

    posicion: int | None
    record: bool
    insignia_nueva: str | None
    nivel_antes: str
    nivel_despues: str
    eventos: list[Evento]

    def a_dict(self) -> dict:
        return asdict(self)


class Ranking:
    """Ranking del día persistente en JSON (`ruta`; None = solo en memoria).

    El fichero guarda todas las partidas (de todos los días) y las insignias por iniciales:
    `{"version": 1, "partidas": [...], "insignias": {"ABC": [["t", "oficial"], ...]}}`.
    Se reescribe entero en cada partida (de forma atómica): son unas decenas al día.
    """

    def __init__(self, ruta: str | Path | None, hoy: date | None = None):
        self.ruta = Path(ruta) if ruta is not None else None
        self._hoy = hoy
        self.partidas: list[Partida] = []
        self._insignias: dict[str, set[tuple[str, str]]] = {}
        self._cargar()

    @property
    def hoy(self) -> str:
        return (self._hoy or date.today()).isoformat()

    # --- fichero --------------------------------------------------------------------------------------------------
    def _cargar(self) -> None:
        if self.ruta is None or not self.ruta.exists():
            return
        try:
            datos = json.loads(self.ruta.read_text(encoding="utf-8"))
            self.partidas = [Partida(**p) for p in datos.get("partidas", [])]
            self._insignias = {k: {tuple(i) for i in v} for k, v in datos.get("insignias", {}).items()}
        except (ValueError, TypeError, AttributeError) as e:
            log.warning("ranking ilegible en %s (%s): empiezo de cero", self.ruta, e)
            self.partidas, self._insignias = [], {}

    def _guardar(self) -> None:
        if self.ruta is None:
            return
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        datos = {"version": 1, "partidas": [p.a_dict() for p in self.partidas],
                 "insignias": {k: sorted(map(list, v)) for k, v in self._insignias.items()}}
        fd, tmp = tempfile.mkstemp(dir=self.ruta.parent, prefix=".ranking", suffix=".json")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=False, indent=1)
        os.replace(tmp, self.ruta)

    # --- consultas ------------------------------------------------------------------------------------------------
    def _del_dia(self) -> list[Partida]:
        # orden estable: a igualdad de puntos, queda delante la que se jugó antes
        return sorted((p for p in self.partidas if p.fecha == self.hoy), key=lambda p: -p.puntos)

    def top(self, n: int = TOP) -> list[Partida]:
        return self._del_dia()[:n]

    @property
    def record(self) -> Partida | None:
        dia = self._del_dia()
        return dia[0] if dia else None

    def posicion(self, puntos: int) -> int | None:
        """Puesto (1-based) que tendría hoy una partida con estos puntos, o None si no entra en el top."""
        puesto = 1 + sum(p.puntos >= puntos for p in self._del_dia())
        return puesto if puesto <= TOP else None

    def es_record(self, puntos: int) -> bool:
        """Bate el récord del día (estrictamente; igualar no cuenta). Con 0 puntos no hay récord."""
        r = self.record
        return puntos > 0 and (r is None or puntos > r.puntos)

    def insignias(self, iniciales: str) -> set[tuple[str, str]]:
        return set(self._insignias.get(_iniciales(iniciales), set()))

    def nivel(self, iniciales: str) -> str:
        return nivel_jugador(self.insignias(iniciales))

    # --- anotar ---------------------------------------------------------------------------------------------------
    def anadir(self, iniciales: str, puntos: int, junta, nivel: str) -> int | None:
        """Guarda la partida y devuelve su puesto en el top del día (None si no entra)."""
        partida = Partida(_iniciales(iniciales), int(puntos), clave_tipo(junta), _nivel(nivel), self.hoy,
                          datetime.now().strftime("%H:%M:%S"))
        puesto = self.posicion(partida.puntos)
        self.partidas.append(partida)
        self._guardar()
        return puesto

    def anotar_ronda(self, iniciales: str, puntos: int, junta, nivel: str, aprobado: bool) -> ResumenRonda:
        """Anota la ronda (ranking + insignia si aprobó) y dice qué celebrar."""
        ini = _iniciales(iniciales)
        record = self.es_record(puntos)
        antes = self.nivel(ini)
        insignia = None
        clave = (clave_tipo(junta), _nivel(nivel))
        if aprobado and clave not in self._insignias.get(ini, set()):
            self._insignias.setdefault(ini, set()).add(clave)
            insignia = nombre_insignia(*clave)
        puesto = self.anadir(ini, puntos, junta, nivel)  # guarda también la insignia
        despues = self.nivel(ini)
        eventos = []
        if record:
            eventos.append(Evento(None, "record", TEXTO_RECORD, 0, {"puntos": int(puntos)}))
        elif puesto is not None:
            eventos.append(Evento(None, "ranking", TEXTO_RANKING.format(puesto), 0, {"puesto": puesto}))
        if insignia:
            eventos.append(Evento(None, "insignia", TEXTO_INSIGNIA.format(insignia), 0, {"insignia": insignia}))
        if despues != antes:
            eventos.append(Evento(None, "ascenso", TEXTO_ASCENSO.format(despues.upper()), 0, {"nivel": despues}))
        return ResumenRonda(puesto, record, insignia, antes, despues, eventos)
