"""Métricas de una pasada de soldadura: cordón por tramos, nota de 0 a 10, huecos y avisos de oficio.

Es el corazón de la escuela: con estas mismas cuentas se puntúa al alumno en la tablet, se decide qué tramos
repasa el robot (los huecos), se filtran las demostraciones que entran en el dataset y se evalúan las políticas
(VLA frente a ACT). Por eso todo sale de una sola función, `evaluar_pasada`, y el evaluador en vivo la reutiliza
para que lo que se pinta durante la pasada sea exactamente lo que se puntúa al final.

Criterios (unidades y marco de la pieza en `lewelder.contrato`)
---------------------------------------------------------------
- **Soldando:** gatillo apretado, punta sobre la pieza (z <= `Z_LEVANTADA`; más arriba la antorcha está claramente
  levantada) y dentro del cordón (0 <= x <= `LONGITUD_CORDON`). Las métricas de calidad se miden solo ahí.
- **Desvío:** distancia lateral |y| de la punta al cordón (igual en la recta y en la T: el cordón está en y = 0).
- **Cubierto:** una muestra "deposita" si se está soldando con |y| <= tolerancia del nivel. Cada muestra deja un
  charco de ±`RADIO_CHARCO` mm y dos muestras seguidas que depositan unen lo que hay entre ellas (si no se perdió
  el seguimiento más de `SALTO_MAX`). Un tramo de 5 mm está cubierto si al menos `FRACCION_CUBIERTO` de su
  longitud lo está. Así los bordes de un hueco salen con precisión de un tramo sea cual sea la frecuencia.
- **Velocidad (de avance):** |pendiente| de la recta de mínimos cuadrados de x frente a t en una ventana de
  `VENTANA_VELOCIDAD` s (centrada al evaluar la pasada, hacia atrás en vivo). Promediar sobre una ventana evita
  que el ruido del seguimiento se convierta en velocidad, cosa que sí pasa con diferencias entre muestras.
- **Punto quemado:** gatillo apretado con la punta sobre la pieza y avance medio < `VELOCIDAD_PARADO` a lo largo de
  una ventana de `VENTANA_PARADO` s (calibrada para que una parada limpia cuente a partir de `TIEMPO_QUEMADO`). Se
  usa una ventana larga propia y no la velocidad de cada muestra porque con 0,3 mm de ruido en la punta la
  velocidad instantánea de una antorcha quieta ya supera 1 mm/s y ninguna parada se detectaría. Se sitúa en la x
  media de la parada.
- **Ángulo correcto:** el de trabajo a ±`MARGEN_ANGULO_TRABAJO` del objetivo de la pieza y el de avance dentro de
  `ANGULO_AVANCE_RANGO`. Si una muestra solo trae uno de los dos, cuenta ese. Si no hay ningún ángulo (sin IMU),
  el ángulo no puntúa y su peso se reparte entre el resto.

Nota (0-10)
-----------
Suma ponderada de puntuaciones entre 0 y 1 (`PESOS`):

    cobertura 40 % · velocidad 15 % · quemados 15 % · desvío 15 % · ángulo 15 %

- cobertura = tramos cubiertos / 24
- velocidad = fracción del tiempo soldando con la velocidad dentro de `VELOCIDAD_OBJETIVO`
- quemados = 1 - quemados / `QUEMADOS_PARA_CERO` (sin bajar de 0)
- desvío = 1 - desvío medio / tolerancia (entre 0 y 1)
- ángulo = fracción del tiempo con el ángulo correcto

Las cuatro de calidad se miden sobre lo soldado y se **multiplican por la cobertura**: no se puntúa la calidad de lo
que no se soldó. Con todo perfecto y la mitad del cordón sin soldar, la nota es 5. Así la cobertura es lo que más
pesa, como pide la spec:

    nota = 10 · cobertura · (0,40 + Σ peso_k · puntuación_k) / (0,40 + Σ peso_k)

Aprobado si la nota llega a `NOTA_APROBADO[nivel]`; el nivel además fija la tolerancia (`TOLERANCIAS`).

v2: gatillo + apoyo (spec v2, 1.6)
---------------------------------
- **Tipos:** `tipo` puede ser una pieza v1 (`TipoPieza`: recta, t) o una junta v2 (`TipoJunta`: t, esquina), o su
  texto. El ángulo de trabajo objetivo sale de `ANGULO_TRABAJO_OBJETIVO` (45° en la T y en la esquina).
- **Apoyo:** la punta está "sobre la pieza" (y puede soldar) si z <= `apoyo`. Por defecto (`altura_apoyo_por_defecto`)
  es `Z_LEVANTADA` (15 mm, el criterio v1, intacto) para `TipoPieza` y para los textos "recta" y "t", y
  `ALTURA_APOYO` del contrato (2 mm) para `TipoJunta` y para "esquina". Se puede forzar con `apoyo=`.
- **Soldar sin apoyar:** gatillo apretado dentro del cordón con la punta por encima de `apoyo` durante al menos
  `PERSISTENCIA_SIN_APOYO` s seguidos (un episodio). No deposita (deja hueco), y da el aviso `AVISO_APOYA`.
- **Calidad del tramo** (`calidad_tramo`, 0-1): para el fantasma y la puntuación arcade. Un tramo está "bien
  soldado" si está cubierto, sin quemar, sin soldar al aire y con calidad >= `TRAMO_BIEN`.
"""
from __future__ import annotations

from collections import deque
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from enum import Enum

import numpy as np

from lewelder.contrato import (
    ALTURA_APOYO,
    ANGULO_AVANCE_RANGO,
    ANGULO_TRABAJO_OBJETIVO,
    LONGITUD_CORDON,
    MARGEN_ANGULO_TRABAJO,
    N_TRAMOS,
    TAMANO_TRAMO,
    TIEMPO_QUEMADO,
    TOLERANCIAS,
    VELOCIDAD_OBJETIVO,
    VELOCIDAD_PARADO,
    Muestra,
    TipoJunta,
    TipoPieza,
)

# --- parámetros de la evaluación (no son del contrato: solo los usa este módulo) ---------------------------------
PESOS = {"cobertura": 0.40, "velocidad": 0.15, "quemados": 0.15, "desvio": 0.15, "angulo": 0.15}
NOTA_APROBADO = {"aprendiz": 5.0, "oficial": 6.0, "maestro": 7.5}
QUEMADOS_PARA_CERO = 2  # con 2 puntos quemados la puntuación de quemados ya es 0

Z_LEVANTADA = 15.0  # mm: por encima, la antorcha está levantada y no suelda
VENTANA_VELOCIDAD = 0.6  # s: con 0,4 s un temblor de 0,3 mm ya parecía ritmo irregular
# La pendiente por mínimos cuadrados pesa poco los extremos de la ventana, así que con una ventana igual a
# TIEMPO_QUEMADO contarían paradas de ~0,4 s. Calibrado con pasadas sintéticas: con 1,6 veces TIEMPO_QUEMADO
# (0,96 s) una parada limpia empieza a contar justo a los 0,6 s del contrato, y la ventana larga promedia el ruido
# de la punta (sin quemados falsos hasta ~0,7 mm de temblor lento; con 1 mm ya aparecen).
VENTANA_PARADO = TIEMPO_QUEMADO * 1.6  # s
COBERTURA_VENTANA = 0.95  # fracción de la ventana que tiene que haber con muestras para juzgarla
RADIO_CHARCO = 1.0  # mm que deja cada muestra a cada lado
FRACCION_CUBIERTO = 0.5  # fracción de un tramo que tiene que estar soldada para darlo por cubierto
SALTO_MAX = 0.25  # s: más separación entre muestras = seguimiento perdido, no se une lo de en medio
CV_IRREGULAR = 0.25  # coeficiente de variación de la velocidad a partir del cual el ritmo es irregular
PCT_ANGULO_FIRME = 50.0  # % del tiempo con ángulo correcto por debajo del cual se avisa aunque la media esté bien

# Evaluador en vivo
ANTIRREPETICION = 2.0  # s entre dos avisos iguales
PERSISTENCIA_AVISO = 0.5  # s que tiene que durar un fallo de velocidad para avisar (evita avisos al arrancar)
# v2: soldar sin apoyar. Un parpadeo del estéreo (un fotograma por encima) no es un fallo; 0,3 s ya es la mano.
PERSISTENCIA_SIN_APOYO = 0.3  # s
# Un tramo se da por cerrado en vivo cuando la punta lo ha dejado atrás esta distancia (la ventana centrada de la
# velocidad ya no cambia: 0,3 s a 5 mm/s son 1,5 mm).
MARGEN_CIERRE = 2.0  # mm

# Calidad del tramo (0-1): pesos de sus componentes y umbral de "bien soldado"
# Un solo fallo (desvío, velocidad o ángulo) basta para que el tramo no esté "bien" (cada peso > 1 - TRAMO_BIEN).
PESOS_TRAMO = {"desvio": 0.35, "velocidad": 0.30, "angulo": 0.35}
DESVIO_PERFECTO = 1.0  # mm: por debajo, el desvío no resta
MARGEN_VELOCIDAD_TRAMO = 2.0  # mm/s fuera de VELOCIDAD_OBJETIVO con los que la velocidad del tramo ya vale 0
FACTOR_QUEMADO = 0.25  # la calidad de un tramo quemado se multiplica por esto
TRAMO_BIEN = 0.75

# Frases de oficio (la tablet y el instructor las muestran tal cual)
AVISO_RAPIDO = "vas demasiado rápido"
AVISO_LENTO = "vas demasiado lento"
AVISO_RITMO = "lleva un ritmo más constante"
AVISO_DESVIO = "te has desviado del cordón"
AVISO_GATILLO = "has soltado el gatillo: queda un hueco"
AVISO_TUMBA_MENOS = "tumba menos la antorcha"
AVISO_TUMBA_MAS = "tumba más la antorcha"
AVISO_VERTICAL = "pon la antorcha vertical"
AVISO_EMPUJA = "empuja la antorcha: inclínala hacia delante"
AVISO_AVANCE_EXCESIVO = "inclina menos la antorcha hacia delante"
AVISO_FIRME = "mantén firme el ángulo de la antorcha"
AVISO_NADA = "no has soldado nada: aprieta el gatillo sobre el cordón"
AVISO_BIEN = "buen cordón: completo, regular y centrado"
AVISO_APOYA = "¡apoya la antorcha!"


def aviso_quemado(x_mm: float) -> str:
    return f"te has quedado parado: punto quemado en {round(x_mm)} mm"


def _aviso_hueco(inicio: float, fin: float) -> str:
    return f"te has dejado sin soldar de {inicio:.0f} a {fin:.0f} mm"


def _tolerancia(nivel: str) -> float:
    if nivel not in TOLERANCIAS:
        raise ValueError(f"nivel desconocido: {nivel!r} (válidos: {', '.join(TOLERANCIAS)})")
    return TOLERANCIAS[nivel]


# --- tipos de pieza (v1) y de junta (v2) -------------------------------------------------------------------------
def clave_tipo(tipo) -> str:
    """Texto del tipo ("recta", "t", "esquina") de un `TipoPieza`, un `TipoJunta` o un texto (ValueError si no
    existe)."""
    valor = tipo.value if isinstance(tipo, Enum) else str(tipo)
    if valor not in ANGULO_TRABAJO_OBJETIVO:
        raise ValueError(f"tipo desconocido: {tipo!r} (válidos: {', '.join(ANGULO_TRABAJO_OBJETIVO)})")
    return valor


def es_junta_v2(tipo) -> bool:
    """True para las juntas v2 (`TipoJunta` o "esquina"); el texto "t" se queda en la v1 por compatibilidad."""
    return isinstance(tipo, TipoJunta) or clave_tipo(tipo) == TipoJunta.ESQUINA.value


def altura_apoyo_por_defecto(tipo) -> float:
    """Altura máxima de la punta (mm) para contar como apoyada: 15 mm en la v1, `ALTURA_APOYO` en la v2."""
    return ALTURA_APOYO if es_junta_v2(tipo) else Z_LEVANTADA


def _r(v: float | None, decimales: int = 3) -> float | None:
    return None if v is None else round(float(v), decimales)


# --- resultados --------------------------------------------------------------------------------------------------
@dataclass
class ResultadoTramo:
    indice: int
    inicio_mm: float
    fin_mm: float
    cubierto: bool
    fraccion_cubierta: float  # 0-1
    desvio_medio_mm: float | None  # None si no se soldó en el tramo
    velocidad_media: float | None  # mm/s
    quemado: bool
    angulo_correcto: bool | None  # None si no hay ángulos
    sin_apoyo: bool = False  # v2: en el tramo hubo un episodio de gatillo apretado con la punta levantada

    def a_dict(self) -> dict:
        return asdict(self)


@dataclass
class Resultado:
    tipo: str
    nivel: str
    tolerancia_mm: float
    nota: float  # 0-10
    aprobado: bool
    cobertura_pct: float
    velocidad_media: float  # mm/s, mientras se suelda (0 si no se soldó)
    cv_velocidad: float  # coeficiente de variación (desviación típica / media)
    pct_tiempo_velocidad_ok: float  # % del tiempo soldando con la velocidad en VELOCIDAD_OBJETIVO
    n_quemados: int
    puntos_quemados: list[float]  # x (mm) de cada punto quemado
    desvio_medio_mm: float
    pct_tiempo_angulo_ok: float | None  # None sin IMU
    angulo_trabajo_medio: float | None
    angulo_avance_medio: float | None
    duracion_s: float  # tiempo soldando
    huecos: list[tuple[float, float]]  # (inicio_mm, fin_mm), tramos contiguos sin cubrir fusionados
    tramos: list[ResultadoTramo]
    avisos: list[str]
    puntuaciones: dict[str, float | None] = field(default_factory=dict)  # componentes de la nota (0-1)
    # v2
    altura_apoyo_mm: float = Z_LEVANTADA  # criterio de apoyo usado
    n_sin_apoyo: int = 0  # episodios de gatillo apretado con la punta levantada (>= PERSISTENCIA_SIN_APOYO s)
    tiempo_sin_apoyo_s: float = 0.0

    def a_dict(self) -> dict:
        return asdict(self)


# --- cálculo -----------------------------------------------------------------------------------------------------
@dataclass
class _Serie:
    """Las muestras como vectores de numpy (ángulos ausentes = nan)."""

    t: np.ndarray
    x: np.ndarray
    y: np.ndarray
    z: np.ndarray
    gatillo: np.ndarray
    trabajo: np.ndarray
    avance: np.ndarray

    @classmethod
    def de(cls, muestras: Sequence[Muestra]) -> _Serie:
        def col(nombre):
            return np.array([np.nan if (v := getattr(m, nombre)) is None else v for m in muestras], dtype=float)

        return cls(
            t=col("t"), x=col("x"), y=col("y"), z=col("z"),
            gatillo=np.array([bool(m.gatillo) for m in muestras], dtype=bool),
            trabajo=col("angulo_trabajo"), avance=col("angulo_avance"),
        )


def _pendientes(t: np.ndarray, x: np.ndarray, lo: np.ndarray, hi: np.ndarray) -> np.ndarray:
    """Pendiente por mínimos cuadrados de x frente a t en cada ventana [lo, hi) de índices (0 si no hay dos tiempos
    distintos). Con sumas acumuladas: cuesta lo mismo con ventanas largas que cortas."""
    tc = t - t[0]

    def suma(a):
        acum = np.concatenate([[0.0], np.cumsum(a)])
        return acum[hi] - acum[lo]

    k = (hi - lo).astype(float)
    st = suma(tc)
    den = k * suma(tc * tc) - st**2
    ok = den > 1e-12
    return np.where(ok, (k * suma(tc * x) - st * suma(x)) / np.where(ok, den, 1.0), 0.0)


def _velocidades(t: np.ndarray, x: np.ndarray, ventana: float = VENTANA_VELOCIDAD) -> np.ndarray:
    """Velocidad de avance (mm/s, |dx/dt|) en cada muestra, en una ventana centrada de `ventana` s.

    Es la velocidad a lo largo del cordón: el temblor lateral no la infla. La ventana incluye siempre al menos la
    muestra anterior y la siguiente, para que con datos a baja frecuencia no salga cero por falta de puntos.
    """
    n = len(t)
    if n < 2:
        return np.zeros(n)
    tc = t - t[0]
    idx = np.arange(n)
    lo = np.minimum(np.searchsorted(tc, tc - ventana / 2, "left"), np.maximum(idx - 1, 0))
    hi = np.maximum(np.searchsorted(tc, tc + ventana / 2, "right"), np.minimum(idx + 2, n))
    return np.abs(_pendientes(t, x, lo, hi))


def _pesos_tiempo(t: np.ndarray) -> np.ndarray:
    """Duración que representa cada muestra (s), sin contar los saltos del seguimiento."""
    if len(t) < 2:
        return np.ones(len(t))
    dt = np.diff(t)
    w = np.append(dt, np.median(dt))
    return np.clip(w, 0.0, SALTO_MAX)


def _fraccion_cubierta(s: _Serie, deposita: np.ndarray) -> np.ndarray:
    """Fracción (0-1) de cada tramo cubierta por los charcos de las muestras que depositan."""
    ini = list(s.x[deposita] - RADIO_CHARCO)
    fin = list(s.x[deposita] + RADIO_CHARCO)
    seguidas = deposita[:-1] & deposita[1:] & (np.diff(s.t) <= SALTO_MAX)
    a, b = s.x[:-1][seguidas], s.x[1:][seguidas]
    ini += list(np.minimum(a, b) - RADIO_CHARCO)
    fin += list(np.maximum(a, b) + RADIO_CHARCO)
    fraccion = np.zeros(N_TRAMOS)
    if not ini:
        return fraccion
    # Unión de intervalos y reparto por tramos.
    orden = np.argsort(ini)
    unidos: list[list[float]] = []
    for i in orden:
        if unidos and ini[i] <= unidos[-1][1]:
            unidos[-1][1] = max(unidos[-1][1], fin[i])
        else:
            unidos.append([ini[i], fin[i]])
    bordes = np.arange(N_TRAMOS + 1) * TAMANO_TRAMO
    for a, b in unidos:
        fraccion += np.clip(np.minimum(b, bordes[1:]) - np.maximum(a, bordes[:-1]), 0.0, None)
    return np.clip(fraccion / TAMANO_TRAMO, 0.0, 1.0)


def _quemados(s: _Serie, sobre_pieza: np.ndarray) -> list[float]:
    """x (mm) de cada punto quemado dentro del cordón.

    Una ventana de `VENTANA_PARADO` s es "parada" si en toda ella el gatillo está apretado con la punta sobre la
    pieza y el avance medio (pendiente de x frente a t) es menor que VELOCIDAD_PARADO. Las ventanas paradas que se
    solapan forman un punto quemado, situado en su x media.
    """
    n = len(s.t)
    if n < 2:
        return []
    candidata = s.gatillo & sobre_pieza
    tc = s.t - s.t[0]
    lo = np.arange(n)
    hi = np.searchsorted(tc, tc + VENTANA_PARADO, "right")
    cubre = tc[hi - 1] - tc >= COBERTURA_VENTANA * VENTANA_PARADO
    fuera = np.concatenate([[0], np.cumsum(~candidata)])
    toda_candidata = fuera[hi] - fuera[lo] == 0
    parada = cubre & toda_candidata & (np.abs(_pendientes(s.t, s.x, lo, hi)) < VELOCIDAD_PARADO)
    # Marca las muestras de cada ventana parada (array de diferencias) y agrupa las seguidas.
    marca = np.zeros(n + 1, dtype=int)
    np.add.at(marca, lo[parada], 1)
    np.add.at(marca, hi[parada], -1)
    en_parada = np.cumsum(marca[:-1]) > 0
    puntos = []
    bordes = np.flatnonzero(np.diff(np.concatenate([[0], en_parada.astype(int), [0]])))
    for i, j in zip(bordes[::2], bordes[1::2]):
        x = float(np.mean(s.x[i:j]))
        if 0.0 <= x <= LONGITUD_CORDON:
            puntos.append(x)
    return puntos


def _episodios_sin_apoyo(s: _Serie, sin_apoyo: np.ndarray) -> list[tuple[int, int]]:
    """Episodios (i, j) [índices, j exclusivo] de muestras seguidas con `sin_apoyo` (sin saltos del seguimiento de
    más de SALTO_MAX) que duran al menos PERSISTENCIA_SIN_APOYO s."""
    episodios = []
    i, n = 0, len(s.t)
    while i < n:
        if not sin_apoyo[i]:
            i += 1
            continue
        j = i + 1
        while j < n and sin_apoyo[j] and s.t[j] - s.t[j - 1] <= SALTO_MAX:
            j += 1
        if s.t[j - 1] - s.t[i] >= PERSISTENCIA_SIN_APOYO - 1e-9:
            episodios.append((i, j))
        i = j
    return episodios


def _angulos_ok(s: _Serie, tipo: str) -> tuple[np.ndarray, np.ndarray]:
    """(hay ángulo, ángulo correcto) por muestra."""
    objetivo = ANGULO_TRABAJO_OBJETIVO[tipo]
    hay_t, hay_a = ~np.isnan(s.trabajo), ~np.isnan(s.avance)
    with np.errstate(invalid="ignore"):
        ok_t = np.abs(s.trabajo - objetivo) <= MARGEN_ANGULO_TRABAJO
        ok_a = (s.avance >= ANGULO_AVANCE_RANGO[0]) & (s.avance <= ANGULO_AVANCE_RANGO[1])
    return hay_t | hay_a, (ok_t | ~hay_t) & (ok_a | ~hay_a)


def _intervalos(marcas: Sequence[bool]) -> list[tuple[float, float]]:
    """Fusiona los tramos marcados contiguos en intervalos (inicio_mm, fin_mm)."""
    salida: list[tuple[float, float]] = []
    inicio = None
    for i, marcado in enumerate(list(marcas) + [False]):
        if marcado and inicio is None:
            inicio = i
        elif not marcado and inicio is not None:
            salida.append((inicio * TAMANO_TRAMO, i * TAMANO_TRAMO))
            inicio = None
    return salida


def _avisos_angulo(trabajo: float | None, avance: float | None, tipo: str) -> list[str]:
    avisos = []
    if trabajo is not None:
        objetivo = ANGULO_TRABAJO_OBJETIVO[tipo]
        if objetivo < 90.0:  # uniones en ángulo (T, esquina): la antorcha va tumbada
            if trabajo < objetivo - MARGEN_ANGULO_TRABAJO:
                avisos.append(AVISO_TUMBA_MENOS)
            elif trabajo > objetivo + MARGEN_ANGULO_TRABAJO:
                avisos.append(AVISO_TUMBA_MAS)
        elif abs(trabajo - objetivo) > MARGEN_ANGULO_TRABAJO:
            avisos.append(AVISO_VERTICAL)
    if avance is not None:
        if avance < ANGULO_AVANCE_RANGO[0]:
            avisos.append(AVISO_EMPUJA)
        elif avance > ANGULO_AVANCE_RANGO[1]:
            avisos.append(AVISO_AVANCE_EXCESIVO)
    return avisos


def _combinar_nota(cobertura: float, puntuaciones: dict[str, float | None]) -> float:
    """Nota 0-10: la calidad (velocidad, quemados, desvío, ángulo) multiplicada por la cobertura."""
    suma, total = PESOS["cobertura"], PESOS["cobertura"]
    for nombre in ("velocidad", "quemados", "desvio", "angulo"):
        valor = puntuaciones.get(nombre)
        if valor is not None:
            suma += PESOS[nombre] * valor
            total += PESOS[nombre]
    return round(float(10.0 * cobertura * suma / total), 2)


def _media(valores: np.ndarray, pesos: np.ndarray) -> float | None:
    return float(np.average(valores, weights=pesos)) if len(valores) and pesos.sum() > 0 else None


def evaluar_pasada(muestras: Sequence[Muestra], tipo: TipoPieza | TipoJunta | str, nivel: str = "oficial", *,
                   apoyo: float | None = None) -> Resultado:
    """Puntúa una pasada completa. No lanza excepciones por datos raros (vacía, sin IMU, sin gatillo...): devuelve
    un resultado con nota 0 y un aviso. Solo un `nivel` o un `tipo` desconocidos son un error (ValueError).

    `apoyo`: altura máxima (mm) de la punta para que cuente como sobre la pieza; None = según el tipo
    (`altura_apoyo_por_defecto`)."""
    apoyo = altura_apoyo_por_defecto(tipo) if apoyo is None else float(apoyo)
    tipo = clave_tipo(tipo)
    tol = _tolerancia(nivel)
    s = _Serie.de(muestras)
    v = _velocidades(s.t, s.x)
    w = _pesos_tiempo(s.t)
    sobre_pieza = s.z <= apoyo
    en_cordon = (s.x >= 0.0) & (s.x <= LONGITUD_CORDON)
    soldando = s.gatillo & sobre_pieza & en_cordon
    desvio = np.abs(s.y)
    deposita = s.gatillo & sobre_pieza & (desvio <= tol)
    hay_ang, ang_ok = _angulos_ok(s, tipo)
    tramo = np.clip(np.floor(s.x / TAMANO_TRAMO), 0, N_TRAMOS - 1).astype(int) if len(s.t) else np.zeros(0, int)

    fraccion = _fraccion_cubierta(s, deposita) if len(s.t) else np.zeros(N_TRAMOS)
    cubiertos = fraccion >= FRACCION_CUBIERTO
    quemados = _quemados(s, sobre_pieza)
    tramos_quemados = {min(int(x // TAMANO_TRAMO), N_TRAMOS - 1) for x in quemados}
    # v2: gatillo apretado en el cordón con la punta levantada
    episodios = _episodios_sin_apoyo(s, s.gatillo & en_cordon & ~sobre_pieza)
    en_episodio = np.zeros(len(s.t), dtype=bool)
    for i, j in episodios:
        en_episodio[i:j] = True
    tramos_sin_apoyo = set(tramo[en_episodio].tolist())
    tiempo_sin_apoyo = float(w[en_episodio].sum())

    # Métricas globales mientras se suelda.
    ws = w[soldando]
    vs = v[soldando]
    vel_media = _media(vs, ws) or 0.0
    cv = float(np.sqrt(np.average((vs - vel_media) ** 2, weights=ws)) / vel_media) if vel_media > 0 else 0.0
    vel_ok = (vs >= VELOCIDAD_OBJETIVO[0]) & (vs <= VELOCIDAD_OBJETIVO[1])
    pct_vel = 100.0 * ws[vel_ok].sum() / ws.sum() if ws.sum() > 0 else 0.0
    desvio_medio = _media(desvio[soldando], ws) or 0.0
    con_ang = soldando & hay_ang
    pct_ang = 100.0 * w[con_ang & ang_ok].sum() / w[con_ang].sum() if w[con_ang].sum() > 0 else None
    trabajo_s, avance_s = s.trabajo[soldando], s.avance[soldando]
    trabajo_medio = float(np.nanmean(trabajo_s)) if np.any(~np.isnan(trabajo_s)) else None
    avance_medio = float(np.nanmean(avance_s)) if np.any(~np.isnan(avance_s)) else None

    tramos = []
    for i in range(N_TRAMOS):
        m = soldando & (tramo == i)
        mi = m & hay_ang
        tramos.append(
            ResultadoTramo(
                indice=i,
                inicio_mm=i * TAMANO_TRAMO,
                fin_mm=(i + 1) * TAMANO_TRAMO,
                cubierto=bool(cubiertos[i]),
                fraccion_cubierta=_r(fraccion[i]),
                desvio_medio_mm=_r(_media(desvio[m], w[m])),
                velocidad_media=_r(_media(v[m], w[m])),
                quemado=i in tramos_quemados,
                angulo_correcto=bool(w[mi & ang_ok].sum() >= FRACCION_CUBIERTO * w[mi].sum()) if mi.any() else None,
                sin_apoyo=i in tramos_sin_apoyo,
            )
        )

    cobertura = float(cubiertos.mean())
    puntuaciones = {
        "cobertura": cobertura,
        "velocidad": pct_vel / 100.0,
        "quemados": max(0.0, 1.0 - len(quemados) / QUEMADOS_PARA_CERO),
        "desvio": float(np.clip(1.0 - desvio_medio / tol, 0.0, 1.0)) if soldando.any() else 0.0,
        "angulo": None if pct_ang is None else pct_ang / 100.0,
    }
    nota = _combinar_nota(cobertura, puntuaciones)
    huecos = _intervalos(~cubiertos)

    # Avisos de oficio, de lo más grave a lo menos.
    avisos = []
    if not soldando.any():
        avisos.append(AVISO_NADA)
        if episodios:
            avisos.append(AVISO_APOYA)
    else:
        if episodios:  # explica los huecos que vienen detrás
            avisos.append(AVISO_APOYA)
        avisos += [_aviso_hueco(a, b) for a, b in huecos]
        avisos += [aviso_quemado(x) for x in quemados]
        desviados = [t.desvio_medio_mm is not None and t.desvio_medio_mm > tol for t in tramos]
        if any(desviados):
            avisos += [f"{AVISO_DESVIO} entre {a:.0f} y {b:.0f} mm" for a, b in _intervalos(desviados)]
        elif desvio_medio > tol / 2:
            avisos.append(AVISO_DESVIO)
        mediana = float(np.median(vs))
        if mediana > VELOCIDAD_OBJETIVO[1]:
            avisos.append(AVISO_RAPIDO)
        elif mediana < VELOCIDAD_OBJETIVO[0]:
            avisos.append(AVISO_LENTO)
        elif cv > CV_IRREGULAR:
            avisos.append(AVISO_RITMO)
        de_angulo = _avisos_angulo(trabajo_medio, avance_medio, tipo)
        if not de_angulo and pct_ang is not None and pct_ang < PCT_ANGULO_FIRME:
            de_angulo = [AVISO_FIRME]
        avisos += de_angulo
        if not avisos:
            avisos.append(AVISO_BIEN)

    return Resultado(
        tipo=tipo,
        nivel=nivel,
        tolerancia_mm=tol,
        nota=nota,
        aprobado=bool(nota >= NOTA_APROBADO[nivel]),
        cobertura_pct=_r(100.0 * cobertura, 2),
        velocidad_media=_r(vel_media),
        cv_velocidad=_r(cv),
        pct_tiempo_velocidad_ok=_r(pct_vel, 2),
        n_quemados=len(quemados),
        puntos_quemados=[_r(x, 1) for x in quemados],
        desvio_medio_mm=_r(desvio_medio),
        pct_tiempo_angulo_ok=_r(pct_ang, 2),
        angulo_trabajo_medio=_r(trabajo_medio, 2),
        angulo_avance_medio=_r(avance_medio, 2),
        duracion_s=_r(ws.sum()),
        huecos=huecos,
        tramos=tramos,
        avisos=avisos,
        puntuaciones={k: _r(p, 4) for k, p in puntuaciones.items()},
        altura_apoyo_mm=apoyo,
        n_sin_apoyo=len(episodios),
        tiempo_sin_apoyo_s=_r(tiempo_sin_apoyo),
    )


# --- calidad por tramo (fantasma y puntuación arcade) ------------------------------------------------------------
def calidad_tramo(tramo: ResultadoTramo, tolerancia: float) -> float:
    """Calidad (0-1) de un tramo: 0 si no está cubierto; si no, media ponderada (`PESOS_TRAMO`) de desvío,
    velocidad y ángulo (sin ángulos, su peso se reparte), por la fracción cubierta y por `FACTOR_QUEMADO` si se
    quemó.

    - desvío: 1 hasta `DESVIO_PERFECTO` mm y 0 al llegar a la tolerancia del nivel.
    - velocidad: 1 dentro de `VELOCIDAD_OBJETIVO` y 0 a `MARGEN_VELOCIDAD_TRAMO` mm/s fuera.
    - ángulo: 1 si fue correcto en el tramo, 0 si no.
    """
    if not tramo.cubierto:
        return 0.0
    componentes: dict[str, float] = {}
    if tramo.desvio_medio_mm is not None:
        exceso = max(0.0, tramo.desvio_medio_mm - DESVIO_PERFECTO)
        componentes["desvio"] = float(np.clip(1.0 - exceso / max(tolerancia - DESVIO_PERFECTO, 1e-6), 0.0, 1.0))
    if tramo.velocidad_media is not None:
        lo, hi = VELOCIDAD_OBJETIVO
        fuera = max(0.0, lo - tramo.velocidad_media, tramo.velocidad_media - hi)
        componentes["velocidad"] = float(np.clip(1.0 - fuera / MARGEN_VELOCIDAD_TRAMO, 0.0, 1.0))
    if tramo.angulo_correcto is not None:
        componentes["angulo"] = 1.0 if tramo.angulo_correcto else 0.0
    if componentes:
        total = sum(PESOS_TRAMO[k] for k in componentes)
        calidad = sum(PESOS_TRAMO[k] * v for k, v in componentes.items()) / total
    else:  # cubierto solo por charcos vecinos (sin muestras propias): se da por bueno
        calidad = 1.0
    calidad *= min(1.0, float(tramo.fraccion_cubierta))
    if tramo.quemado:
        calidad *= FACTOR_QUEMADO
    return round(float(calidad), 4)


def calidades(resultado: Resultado) -> list[float]:
    """Calidad (0-1) de cada tramo del resultado."""
    return [calidad_tramo(tr, resultado.tolerancia_mm) for tr in resultado.tramos]


def tramo_bien(tramo: ResultadoTramo, tolerancia: float) -> bool:
    """Bien soldado: cubierto, sin quemar, sin soldar al aire y con calidad >= TRAMO_BIEN."""
    return (tramo.cubierto and not tramo.quemado and not tramo.sin_apoyo
            and calidad_tramo(tramo, tolerancia) >= TRAMO_BIEN)


def filtrar_demostraciones(resultados: Sequence[Resultado], umbral: float) -> list[int]:
    """Índices de las demostraciones cuya nota llega al umbral: son las que entran en el dataset."""
    return [i for i, r in enumerate(resultados) if r.nota >= umbral]


# --- evaluador en vivo -------------------------------------------------------------------------------------------
class EvaluadorEnVivo:
    """Evalúa la pasada mientras ocurre.

    `anadir` da avisos instantáneos (con antirrepetición: el mismo aviso como mucho una vez cada
    `ANTIRREPETICION` s; el de punto quemado, una vez por parada). `estado` da lo necesario para pintar la tablet y
    sale de la misma `evaluar_pasada` que puntúa al final, así que los tramos pintados son los que cuentan.
    """

    def __init__(self, tipo: TipoPieza | TipoJunta | str, nivel: str = "oficial", *, apoyo: float | None = None):
        self.apoyo = altura_apoyo_por_defecto(tipo) if apoyo is None else float(apoyo)
        self.tipo_original = tipo  # tal cual llegó (para evaluar_pasada)
        self.tipo = clave_tipo(tipo)
        self.nivel = nivel
        self.tolerancia = _tolerancia(nivel)
        self.n_sin_apoyo = 0  # episodios de gatillo apretado con la punta levantada
        self._sin_apoyo_desde: float | None = None
        self._sin_apoyo_contado = False
        self._x_cerca: float | None = None  # x máxima con la punta cerca de la pieza (z <= Z_LEVANTADA)
        self.muestras: list[Muestra] = []
        self._reciente: deque[Muestra] = deque()  # muestras del último VENTANA_PARADO s
        # Públicos (los usa el servidor para colorear el cordón con el mismo criterio que los avisos):
        self.velocidad = 0.0  # mm/s de avance en la ventana que acaba ahora
        self.velocidad_fiable = False  # la ventana de velocidad está llena con gatillo apretado sin cortes
        self.en_parada = False  # la punta lleva parada lo bastante para quemar
        self._inicio_tramo: float | None = None  # t de la primera muestra del tramo con gatillo en curso
        self._x_max: float | None = None
        self._ultimo_aviso: dict[str, float] = {}
        self._fallo_desde: dict[str, float] = {}
        self._cache: tuple[int, Resultado] | None = None

    # Alias de los nombres antiguos (privados) por compatibilidad.
    @property
    def _velocidad(self) -> float:
        return self.velocidad

    @property
    def _en_parada(self) -> bool:
        return self.en_parada

    @staticmethod
    def _pendiente(muestras: Sequence[Muestra]) -> float:
        """Avance medio (mm/s, con signo) de las muestras: la misma pendiente que en la evaluación."""
        if len(muestras) < 2:
            return 0.0
        t = np.array([m.t for m in muestras])
        x = np.array([m.x for m in muestras])
        return float(_pendientes(t, x, np.array([0]), np.array([len(muestras)]))[0])

    def _sostenido(self, clave: str, condicion: bool, t: float) -> bool:
        """True si `condicion` lleva al menos PERSISTENCIA_AVISO s seguida."""
        if not condicion:
            self._fallo_desde.pop(clave, None)
            return False
        return t - self._fallo_desde.setdefault(clave, t) >= PERSISTENCIA_AVISO

    def anadir(self, muestra: Muestra) -> list[str]:
        """Añade una muestra y devuelve los avisos que tocan ahora (lista vacía casi siempre)."""
        anterior = self.muestras[-1] if self.muestras else None
        self.muestras.append(muestra)
        t = muestra.t
        self._reciente.append(muestra)
        while self._reciente[0].t < t - VENTANA_PARADO:
            self._reciente.popleft()
        if len(self._reciente) < 2 and anterior is not None:
            self._reciente.appendleft(anterior)  # a baja frecuencia, al menos dos puntos
        # Tramo con el gatillo apretado en curso: empieza al apretar (o al recuperar la punta tras un salto).
        if muestra.gatillo:
            if anterior is None or not anterior.gatillo or t - anterior.t > SALTO_MAX:
                self._inicio_tramo = t
        else:
            self._inicio_tramo = None
        # Ventana de velocidad (hacia atrás): las del último VENTANA_VELOCIDAD s, y al menos dos. Con el gatillo
        # apretado no cruza el último corte: al volver a apretar tras un hueco, mezclar los dos lados daba una
        # velocidad falsa (el salto de la mano sin soldar) y un "vas demasiado rápido" que no era verdad.
        desde = t - VENTANA_VELOCIDAD
        validas = list(self._reciente)
        if self._inicio_tramo is not None:
            validas = [m for m in validas if m.t >= self._inicio_tramo]
        ventana = [m for m in validas if m.t >= desde] or [muestra]
        if len(ventana) < 2 and len(validas) >= 2:
            ventana = validas[-2:]
        self.velocidad = v = abs(self._pendiente(ventana))
        self.velocidad_fiable = (
            self._inicio_tramo is not None and len(ventana) >= 2
            and t - self._inicio_tramo >= COBERTURA_VENTANA * VENTANA_VELOCIDAD
        )
        sobre_pieza = muestra.z <= self.apoyo
        if sobre_pieza:
            self._x_max = muestra.x if self._x_max is None else max(self._x_max, muestra.x)
        cerca = muestra.z <= max(Z_LEVANTADA, self.apoyo)
        if cerca:
            self._x_cerca = muestra.x if self._x_cerca is None else max(self._x_cerca, muestra.x)

        en_cordon = 0.0 <= muestra.x <= LONGITUD_CORDON
        soldando = muestra.gatillo and sobre_pieza and en_cordon
        candidatos: list[str] = []
        avisos: list[str] = []

        # v2: soldar sin apoyar. Mismo criterio que `_episodios_sin_apoyo`; el aviso, una vez por episodio.
        if muestra.gatillo and en_cordon and not sobre_pieza:
            seguido = anterior is not None and self._sin_apoyo_desde is not None and t - anterior.t <= SALTO_MAX
            if not seguido:
                self._sin_apoyo_desde, self._sin_apoyo_contado = t, False
            if not self._sin_apoyo_contado and t - self._sin_apoyo_desde >= PERSISTENCIA_SIN_APOYO - 1e-9:
                self._sin_apoyo_contado = True
                self.n_sin_apoyo += 1
                candidatos.append(AVISO_APOYA)
        else:
            self._sin_apoyo_desde = None

        # Punto quemado: mismo criterio que la evaluación sobre la ventana que acaba ahora; una vez por parada.
        parada = (
            soldando
            and t - self._reciente[0].t >= COBERTURA_VENTANA * VENTANA_PARADO
            and all(m.gatillo and m.z <= self.apoyo for m in self._reciente)
            and abs(self._pendiente(self._reciente)) < VELOCIDAD_PARADO
        )
        if parada and not self.en_parada:
            avisos.append(aviso_quemado(float(np.mean([m.x for m in self._reciente]))))
        self.en_parada = parada

        # Velocidad: solo con la ventana llena (al arrancar o al volver a apretar aún no se puede juzgar).
        juzgable = soldando and self.velocidad_fiable
        if self._sostenido("rapido", juzgable and v > VELOCIDAD_OBJETIVO[1], t):
            candidatos.append(AVISO_RAPIDO)
        if self._sostenido("lento", juzgable and not parada and v < VELOCIDAD_OBJETIVO[0], t):
            candidatos.append(AVISO_LENTO)
        if soldando:
            con_gatillo = [m for m in ventana if m.gatillo]
            if np.mean([abs(m.y) for m in con_gatillo]) > self.tolerancia:
                candidatos.append(AVISO_DESVIO)
            trabajo = [m.angulo_trabajo for m in con_gatillo if m.angulo_trabajo is not None]
            avance = [m.angulo_avance for m in con_gatillo if m.angulo_avance is not None]
            candidatos += _avisos_angulo(
                float(np.mean(trabajo)) if trabajo else None, float(np.mean(avance)) if avance else None, self.tipo
            )
        if (
            anterior is not None and anterior.gatillo and not muestra.gatillo and cerca
            and 0.0 < muestra.x < LONGITUD_CORDON - TAMANO_TRAMO / 2
        ):
            candidatos.append(AVISO_GATILLO)

        for texto in candidatos:
            if t - self._ultimo_aviso.get(texto, -np.inf) >= ANTIRREPETICION:
                self._ultimo_aviso[texto] = t
                avisos.append(texto)
        return avisos

    def _evaluacion(self) -> Resultado:
        if self._cache is None or self._cache[0] != len(self.muestras):
            self._cache = (len(self.muestras),
                           evaluar_pasada(self.muestras, self.tipo, self.nivel, apoyo=self.apoyo))
        return self._cache[1]

    def evaluacion(self) -> Resultado:
        """Evaluación de lo que va de pasada (la misma `evaluar_pasada`, cacheada por número de muestras)."""
        return self._evaluacion()

    def tramos_cerrados(self) -> int:
        """Cuántos tramos (desde el primero) ha dejado ya atrás la punta: su evaluación ya no cambia salvo que vuelva
        atrás. Cuenta la punta cerca de la pieza aunque no suelde, para que un hueco también se cierre."""
        if self._x_cerca is None:
            return 0
        return int(np.clip((self._x_cerca - MARGEN_CIERRE) // TAMANO_TRAMO, 0, N_TRAMOS))

    def estado(self) -> dict:
        """Lo necesario para pintar en vivo (serializable a JSON).

        `nota_parcial` es la nota con la cobertura medida solo sobre los tramos que la punta ya ha dejado atrás
        (None hasta pasar el primero).
        """
        r = self._evaluacion()
        cubiertos = [tr.cubierto for tr in r.tramos]
        ultima = self.muestras[-1] if self.muestras else None
        pasados = 0 if self._x_max is None else int(np.clip(self._x_max, 0.0, LONGITUD_CORDON) // TAMANO_TRAMO)
        nota_parcial = _combinar_nota(sum(cubiertos[:pasados]) / pasados, r.puntuaciones) if pasados else None
        return {
            "t": None if ultima is None else ultima.t,
            "posicion": None if ultima is None else {"x": ultima.x, "y": ultima.y, "z": ultima.z},
            "gatillo": None if ultima is None else bool(ultima.gatillo),
            "velocidad": _r(self.velocidad),
            "angulo_trabajo": None if ultima is None else ultima.angulo_trabajo,
            "angulo_avance": None if ultima is None else ultima.angulo_avance,
            "tramos_cubiertos": cubiertos,
            "cobertura_pct": r.cobertura_pct,
            "puntos_quemados": r.puntos_quemados,
            "nota_parcial": nota_parcial,
            # v2
            "apoyada": None if ultima is None else bool(ultima.z <= self.apoyo),
            "altura_apoyo": self.apoyo,
            "n_sin_apoyo": self.n_sin_apoyo,
        }

    def terminar(self) -> Resultado:
        """Resultado final: el mismo que daría `evaluar_pasada` con todas las muestras."""
        return self._evaluacion()
