"""Alcance del robot: ¿puede el SO-101 soldar entera la junta montada, con el ángulo correcto, y señalarla?

Si no llega, busca el cambio más pequeño de la base (giro y/o desplazamiento) que lo arregla y lo dice en palabras
del personaje ("gírala 90° hacia mi izquierda", "acércala un palmo") y como datos para la flecha de la tablet
(spec v2, 1.4).

Geometría (marcos del contrato, mm y grados)
---------------------------------------------
- **Base** (`Anclaje`, como `POSICION_BASE`): centro (x, y) en la mesa y `giro` alrededor de Z; giro 0 = X de la
  base hacia +Y de la mesa (`rot_z(giro) @ rot_z(90)`, el mismo convenio que los anclajes v1). La cara superior de
  la base queda a `GROSOR_CHAPA` sobre la mesa.
- **Cordón** (`marco_cordon`): el marco de la pieza v1 puesto en la junta montada: origen en el inicio del cordón
  (X de la base = -LONGITUD_CORDON/2, Y = `Y_CORDON[junta]`, cara de la base), X a lo largo del cordón, Y hacia la
  chapa móvil, Z hacia arriba. Los ángulos de la antorcha (trabajo, avance) son los del contrato en este marco.
- **Soldar:** la punta de la antorcha del robot (`punta_antorcha`) recorre `N_PUNTOS` puntos del cordón a
  `ALTURA_PUNTA_ROBOT` con trabajo = `ANGULO_TRABAJO_OBJETIVO[junta]` (45°) y avance = `ANGULO_AVANCE_ROBOT` (10° de
  empuje), siguiendo una misma rama de la IK (sin saltos de postura), con error < `TOL_MM` / `TOL_GRADOS` y al menos
  `HOLGURA_MIN` grados de margen en cada articulación.
- **Señalar:** la punta de la pinza (`gripperframe`, que apunta con su +X local) a `DISTANCIA_SENALAR` del inicio,
  el centro y el final del cordón, apuntándoles: vertical o, si no llega, inclinada hacia fuera
  (`ELEVACIONES_SENALAR`: 90°, 60° o 45° sobre la horizontal, en la dirección robot → punto). Vertical solo llega
  hasta r ≈ 260 mm; inclinada, hasta ≈ 420 mm.
- No se comprueban choques del brazo con la chapa móvil (la IK no los ve).

Rapidez (< 200 ms)
------------------
El brazo gira entero con `shoulder_pan` alrededor de un eje vertical: un punto con una dirección de antorcha da la
misma postura (salvo el pan) a cualquier rumbo. Así que el alcance de un punto solo depende de su distancia al eje
`r` y del rumbo de la antorcha respecto al del punto `psi` (con la cota y la inclinación fijas por los ángulos).
`TablaAlcance` guarda, en una rejilla (r, psi), si hay solución y su postura; se calcula una vez (~2-4 s, por
continuación desde una solución conocida) y se cachea en `salidas/alcance/`. Con ella:
- la comprobación de verdad (IK en cadena por el cordón) arranca de la postura de la tabla y converge en pocos pasos;
- la búsqueda de la propuesta prueba ~2.400 bases candidatas en la tabla a la vez (numpy) y solo verifica con la IK
  de verdad la elegida.
Además, cada consulta se memoriza: el servidor puede preguntar a cada fotograma.
"""
from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

import mujoco
import numpy as np

from lewelder.contrato import (
    ANGULO_TRABAJO_OBJETIVO,
    GROSOR_CHAPA,
    LONGITUD_CORDON,
    POSICION_BASE,
    Y_CORDON,
    Anclaje,
    TipoJunta,
)

log = logging.getLogger("lewelder.alcance")

RAIZ = Path(__file__).resolve().parents[1]
CACHE = RAIZ / "salidas" / "alcance"
VERSION_TABLA = 1

# --- criterio ------------------------------------------------------------------------------------------------------
ANGULO_AVANCE_ROBOT = 10.0  # grados de empuje con los que suelda el robot (el del guion de la simulación)
ALTURA_PUNTA_ROBOT = 1.0  # mm: punta apoyada
DISTANCIA_SENALAR = 30.0  # mm de la punta de la pinza al cordón, a lo largo de la dirección en que apunta
ELEVACIONES_SENALAR = (90.0, 60.0, 45.0)  # grados sobre la horizontal, de la más natural a la más tumbada
EJE_PINZA = (1.0, 0.0, 0.0)  # eje local de `gripperframe` que apunta hacia la punta de los dedos
N_PUNTOS = 7  # puntos del cordón que se comprueban (cada 20 mm)
TOL_MM = 0.5
TOL_GRADOS = 0.5
TOL_SENALAR_MM = 1.0
TOL_SENALAR_GRADOS = 3.0
HOLGURA_MIN = 3.0  # grados a los límites de cada articulación (también del pan)
ITER_CADENA = 200
ITER_TABLA = 80

# --- tabla ---------------------------------------------------------------------------------------------------------
PASO_R = 10.0  # mm
PASO_PSI = 10.0  # grados
R_TABLA = (60.0, 480.0)

# --- propuesta -----------------------------------------------------------------------------------------------------
GIROS = tuple(range(-165, 181, 15))  # grados (180 = media vuelta)
RADIAL = tuple(range(-250, 251, 50))  # mm, + = alejar del robot
LATERAL = tuple(range(-200, 201, 50))  # mm, + = a la izquierda del robot (+Y de la mesa)
GRADOS_POR_MM = 1.2  # coste: girar 120° "cuesta" como mover 100 mm (pedir un giro es más natural)
COSTE_COMBINAR = 0.35  # coste extra por cada cosa más que pedir a la vez (girar y acercar, acercar y mover a un lado)
CENTRO_BASE = (170.0, 450.0)  # mm: distancia del centro de la base al robot (no lo pisa y queda en la mesa)
ROBUSTEZ = ((10.0, 0.0, 0.0), (-10.0, 0.0, 0.0), (0.0, 25.0, 0.0), (0.0, -25.0, 0.0), (0.0, 0.0, 25.0),
            (0.0, 0.0, -25.0))  # (giro, radial, lateral): la persona no la dejará exacta
MAX_VERIFICAR = 6


# --- geometría ----------------------------------------------------------------------------------------------------
def rot_z(grados: float) -> np.ndarray:
    a = np.radians(grados)
    return np.array([[np.cos(a), -np.sin(a), 0.0], [np.sin(a), np.cos(a), 0.0], [0.0, 0.0, 1.0]])


def marco_base(base: Anclaje = POSICION_BASE) -> tuple[np.ndarray, np.ndarray]:
    """(origen en mm, giro 3x3) del marco de la base en la mesa: origen en el centro de su cara superior."""
    return np.array([base.x, base.y, GROSOR_CHAPA]), rot_z(base.giro) @ rot_z(90.0)


def marco_cordon(junta, base: Anclaje = POSICION_BASE) -> tuple[np.ndarray, np.ndarray]:
    """(origen en mm, giro 3x3) del marco del cordón de la junta montada sobre `base`, en la mesa."""
    o, R = marco_base(base)
    return o + R @ np.array([-LONGITUD_CORDON / 2, Y_CORDON[TipoJunta(junta)], 0.0]), R


def direccion_antorcha(angulo_trabajo: float, angulo_avance: float) -> np.ndarray:
    """Eje mango → punta en el marco del cordón (el mismo convenio que `sim.entorno.direccion_antorcha`)."""
    d = np.array([np.tan(np.radians(angulo_avance)), 1.0 / np.tan(np.radians(angulo_trabajo)), -1.0])
    return d / np.linalg.norm(d)


def aplicar(base: Anclaje, giro: float = 0.0, acercar_mm: float = 0.0, lateral_mm: float = 0.0) -> Anclaje:
    """La base después de girarla `giro` grados sobre su centro, acercarla al robot `acercar_mm` (en la línea
    robot-base) y moverla `lateral_mm` a la izquierda del robot."""
    centro = np.array([base.x, base.y])
    norma = np.linalg.norm(centro)
    u = centro / norma if norma > 1e-9 else np.array([1.0, 0.0])
    v = np.array([-u[1], u[0]])
    nuevo = centro - acercar_mm * u + lateral_mm * v
    giro_nuevo = (base.giro + giro + 180.0) % 360.0 - 180.0
    return Anclaje(base.nombre, round(float(nuevo[0]), 2), round(float(nuevo[1]), 2), round(float(giro_nuevo), 2))


def _medida(mm: float) -> str:
    mm = abs(mm)
    if mm <= 60:
        return "un poco"
    if mm <= 140:
        return "medio palmo"
    if mm <= 260:
        return "un palmo"
    return "dos palmos"


def frase_propuesta(giro: float, acercar_mm: float, lateral_mm: float) -> str:
    """Frase corta del robot para pedir el cambio (la izquierda y la derecha son las del robot)."""
    partes = []
    if round(giro):
        if abs(round(giro)) == 180:
            partes.append("dale media vuelta")
        else:
            partes.append(f"gírala {abs(round(giro))}° hacia mi {'izquierda' if giro > 0 else 'derecha'}")
    if round(acercar_mm):
        partes.append(f"{'acércala' if acercar_mm > 0 else 'aléjala'} {_medida(acercar_mm)}")
    if round(lateral_mm):
        partes.append(f"muévela {_medida(lateral_mm)} a mi {'izquierda' if lateral_mm > 0 else 'derecha'}")
    if len(partes) <= 1:
        return "".join(partes)
    return ", ".join(partes[:-1]) + " y " + partes[-1]


# --- resultados ---------------------------------------------------------------------------------------------------
@dataclass
class Propuesta:
    giro: float  # grados, + = antihorario visto desde arriba (hacia la izquierda del robot)
    acercar_mm: float  # + = hacia el robot
    lateral_mm: float  # + = a la izquierda del robot
    base: Anclaje  # la base como quedaría
    frase: str
    robusta: bool  # también llega con la base algo peor colocada (±10°, ±25 mm)

    def a_dict(self) -> dict:
        d = asdict(self)
        d["base"] = asdict(self.base)
        return d


@dataclass
class ResultadoAlcance:
    llega: bool  # suelda y señala
    suelda: bool
    senala: bool
    junta: str
    base: Anclaje
    error_mm: float  # peor error de posición de la IK a lo largo del cordón (inf si no hay rama)
    error_grados: float
    holgura_grados: float  # menor margen a los límites articulares a lo largo del cordón
    x_sin_alcance: list[float]  # x del cordón (mm) a las que no llega con el ángulo correcto
    propuesta: Propuesta | None
    frase: str  # lo que dice el robot ("" si llega)
    ms: float
    postura_inicio: list[float] | None = None  # q (rad, 6) en el inicio del cordón, si llega
    detalles: dict = field(default_factory=dict)

    def a_dict(self) -> dict:
        d = asdict(self)
        d["base"] = asdict(self.base)
        d["propuesta"] = None if self.propuesta is None else self.propuesta.a_dict()
        for k in ("error_mm", "error_grados", "holgura_grados"):
            if not np.isfinite(d[k]):
                d[k] = None
        return d


@dataclass
class _Cadena:
    suelda: bool
    error_mm: float
    error_grados: float
    holgura: float
    q_inicio: np.ndarray | None


def _envolver(grados):
    return (np.asarray(grados) + 180.0) % 360.0 - 180.0


# --- modelo -------------------------------------------------------------------------------------------------------
_CIN = None


def _cinematica_por_defecto():
    """La cinemática del SO-101 con la antorcha de la escena (se construye una vez por proceso)."""
    global _CIN
    if _CIN is None:
        from sim import escena
        from sim.cinematica import Cinematica

        modelo, _ = escena.construir_modelo()
        _CIN = Cinematica(modelo, sitio_pose="punta_antorcha")
    return _CIN


class Alcance:
    """Comprobación de alcance con caché. `cin`: una `sim.cinematica.Cinematica` con el sitio `punta_antorcha`
    (por defecto, la de la escena de la simulación)."""

    def __init__(self, cin=None, *, cache_disco: bool = True):
        self._cin = cin
        self.cache_disco = cache_disco
        self._tablas: dict[tuple, dict] = {}
        self._senalar: dict | None = None
        self._memo: dict[tuple, ResultadoAlcance] = {}

    # --- preparación ------------------------------------------------------------------------------------------
    @property
    def cin(self):
        if self._cin is None:
            self._cin = _cinematica_por_defecto()
        return self._cin

    def preparar(self, juntas=tuple(TipoJunta)) -> None:
        """Construye (o carga) lo necesario para responder rápido."""
        for j in juntas:
            self._tabla(ANGULO_TRABAJO_OBJETIVO[TipoJunta(j).value], ANGULO_AVANCE_ROBOT)
        self._tabla_senalar()

    def limpiar_cache(self) -> None:
        """Olvida las consultas memorizadas (no las tablas)."""
        self._memo.clear()

    def _modelo(self):
        m = self.cin.m
        if not hasattr(self, "_geo"):
            d = mujoco.MjData(m)
            mujoco.mj_kinematics(m, d)
            j = m.joint("shoulder_pan").id
            self._geo = {
                "ancla": d.xanchor[j][:2] * 1000.0,  # mm
                "signo_pan": float(np.sign(d.xaxis[j][2])) or 1.0,  # girar el mundo +b = pan + b * signo
                "reposo": self._reposo(),
                "firma": hashlib.md5(np.round(np.concatenate([
                    m.body_pos.ravel(), m.body_quat.ravel(), m.jnt_range.ravel(), m.site_pos.ravel(),
                    m.jnt_axis.ravel()]), 6).tobytes()).hexdigest()[:12],
            }
        return self._geo

    @staticmethod
    def _reposo() -> np.ndarray:
        from sim.entorno import REPOSO, lerobot_a_rad

        return lerobot_a_rad(REPOSO)

    def _holgura(self, q: np.ndarray, con_pan: bool = True) -> float:
        lo, hi = self.cin.rangos[:5, 0], self.cin.rangos[:5, 1]
        h = np.minimum(q[:5] - lo, hi - q[:5])
        return float(np.degrees(np.min(h if con_pan else h[1:])))

    # --- tabla (r, psi) ---------------------------------------------------------------------------------------
    def _tabla(self, trabajo: float, avance: float) -> dict:
        clave = (round(trabajo, 3), round(avance, 3))
        if clave in self._tablas:
            return self._tablas[clave]
        geo = self._modelo()
        nombre = (f"tabla_v{VERSION_TABLA}_{geo['firma']}_t{trabajo:g}_a{avance:g}_z{ALTURA_PUNTA_ROBOT:g}"
                  f"_r{PASO_R:g}_p{PASO_PSI:g}.npz")
        ruta = CACHE / nombre
        tabla = None
        if self.cache_disco and ruta.exists():
            try:
                with np.load(ruta) as f:
                    tabla = {k: f[k] for k in f.files}
            except (OSError, ValueError) as e:
                log.warning("tabla de alcance ilegible (%s): la recalculo", e)
        if tabla is None:
            t0 = time.perf_counter()
            tabla = self._construir_tabla(trabajo, avance)
            log.info("tabla de alcance (%g°, %g°) en %.1f s", trabajo, avance, time.perf_counter() - t0)
            if self.cache_disco:
                try:
                    CACHE.mkdir(parents=True, exist_ok=True)
                    np.savez_compressed(ruta, **tabla)
                except OSError as e:
                    log.warning("no se pudo guardar la tabla de alcance: %s", e)
        self._tablas[clave] = tabla
        return tabla

    def _construir_tabla(self, trabajo: float, avance: float) -> dict:
        """Rejilla (r, psi): punto a distancia r del eje del pan en su rumbo 0 y antorcha con rumbo psi. Relleno por
        continuación (inundación) desde las soluciones que encuentran unas cuantas semillas."""
        geo = self._modelo()
        rs = np.arange(R_TABLA[0], R_TABLA[1] + 1e-9, PASO_R)
        psis = np.arange(-180.0, 180.0, PASO_PSI)
        d_loc = direccion_antorcha(trabajo, avance)
        h, dz = float(np.hypot(d_loc[0], d_loc[1])), float(d_loc[2])
        z = GROSOR_CHAPA + ALTURA_PUNTA_ROBOT
        ok = np.zeros((len(rs), len(psis)), dtype=bool)
        Q = np.zeros((len(rs), len(psis), 6))
        intentos = np.zeros_like(ok, dtype=np.int8)

        def objetivo(i, j):
            p = np.array([geo["ancla"][0] + rs[i], geo["ancla"][1], z]) * 1e-3
            a = np.radians(psis[j])
            return p, np.array([h * np.cos(a), h * np.sin(a), dz])

        def resolver(i, j, q_ini, iteraciones):
            p, dv = objetivo(i, j)
            q, e, a = self.cin.inversa_pose(p, dv, q_ini, iteraciones=iteraciones)
            bien = e * 1000 < TOL_MM and np.degrees(a) < TOL_GRADOS and self._holgura(q, con_pan=False) >= HOLGURA_MIN
            return q, bien

        # Semillas: el reposo y unas posturas al azar (con el pan a 0), en celdas variadas
        rng = np.random.default_rng(1234)
        lo, hi = self.cin.rangos[:5, 0], self.cin.rangos[:5, 1]
        semillas = [geo["reposo"].copy()] + [np.r_[rng.uniform(lo * 0.8, hi * 0.8), geo["reposo"][5]]
                                             for _ in range(8)]
        for s in semillas:
            s[0] = 0.0
        pendientes = []
        for i in range(0, len(rs), 4):
            for j in range(0, len(psis), 3):
                for s in semillas[:3]:
                    q, bien = resolver(i, j, s, ITER_CADENA)
                    if bien:
                        ok[i, j], Q[i, j] = True, q
                        pendientes.append((i, j))
                        break
        # Inundación
        while pendientes:
            i, j = pendientes.pop()
            for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                a, b = i + di, (j + dj) % len(psis)
                if not 0 <= a < len(rs) or ok[a, b] or intentos[a, b] >= 4:
                    continue
                intentos[a, b] += 1
                q, bien = resolver(a, b, Q[i, j], ITER_TABLA)
                if bien:
                    ok[a, b], Q[a, b] = True, q
                    pendientes.append((a, b))
        return {"rs": rs, "psis": psis, "ok": ok, "q": Q, "z": np.array(z), "h": np.array(h), "dz": np.array(dz)}

    def _consultar(self, tabla: dict, puntos: np.ndarray, rumbo_dir: np.ndarray):
        """Alcance según la tabla de N puntos (mm, mesa) con la antorcha de rumbo `rumbo_dir` (grados, N).

        Devuelve (ok conservador: las 4 celdas vecinas con solución y el pan dentro de sus límites, índices de la
        celda más cercana, rumbo de cada punto en grados)."""
        geo = self._modelo()
        rel = puntos[..., :2] - geo["ancla"]
        r = np.hypot(rel[..., 0], rel[..., 1])
        rumbo = np.degrees(np.arctan2(rel[..., 1], rel[..., 0]))
        psi = _envolver(rumbo_dir - rumbo)
        rs, psis, ok = tabla["rs"], tabla["psis"], tabla["ok"]
        fi = (r - rs[0]) / PASO_R
        fj = (psi - psis[0]) / PASO_PSI
        i0 = np.floor(fi).astype(int)
        j0 = np.floor(fj).astype(int)
        dentro = (i0 >= 0) & (i0 + 1 < len(rs))
        i0c = np.clip(i0, 0, len(rs) - 2)
        jm = len(psis)
        vecinas = (ok[i0c, j0 % jm] & ok[i0c + 1, j0 % jm] & ok[i0c, (j0 + 1) % jm] & ok[i0c + 1, (j0 + 1) % jm])
        ic = np.clip(np.rint(fi).astype(int), 0, len(rs) - 1)
        jc = np.rint(fj).astype(int) % jm
        pan = np.degrees(tabla["q"][ic, jc, 0]) + rumbo * geo["signo_pan"]
        lo, hi = np.degrees(self.cin.rangos[0])
        pan_ok = (pan >= lo + HOLGURA_MIN) & (pan <= hi - HOLGURA_MIN)
        return dentro & vecinas & pan_ok, (ic, jc), rumbo

    def _senalar_punto(self, p_mm: np.ndarray, semillas, elevaciones=ELEVACIONES_SENALAR,
                       iteraciones: int = ITER_TABLA):
        """(postura en rad, elevación) con la pinza apuntando al punto `p_mm` (mesa) desde DISTANCIA_SENALAR,
        vertical o inclinada hacia fuera; (None, None) si no llega con ninguna elevación."""
        geo = self._modelo()
        radial = np.r_[p_mm[:2] - geo["ancla"], 0.0]
        radial /= max(np.linalg.norm(radial), 1e-9)
        for elev in elevaciones:
            e = np.radians(elev)
            u = np.cos(e) * radial + np.array([0.0, 0.0, -np.sin(e)])
            punta = (p_mm - DISTANCIA_SENALAR * u) * 1e-3
            for s in semillas:
                q, err, ang = self.cin.inversa_pose(punta, u, s, sitio="gripperframe", eje_local=EJE_PINZA,
                                                    iteraciones=iteraciones)
                if err * 1000 < TOL_SENALAR_MM and np.degrees(ang) < TOL_SENALAR_GRADOS and \
                        self._holgura(q) >= HOLGURA_MIN:
                    return q, elev
        return None, None

    def _tabla_senalar(self) -> dict:
        """Alcance de señalar según r en el rumbo 0 (en otro rumbo solo cambia el pan), barrido por continuación
        hacia fuera y hacia dentro desde r = 250 mm. Guarda la postura y la elevación para usarlas de semilla."""
        if self._senalar is not None:
            return self._senalar
        geo = self._modelo()
        rs = np.arange(R_TABLA[0], R_TABLA[1] + 1e-9, PASO_R)
        ok = np.zeros(len(rs), dtype=bool)
        Q = np.zeros((len(rs), 6))
        elev = np.full(len(rs), np.nan)
        i0 = int(np.argmin(np.abs(rs - 250.0)))
        for orden in (range(i0, len(rs)), range(i0, -1, -1)):
            q = geo["reposo"].copy()
            for i in orden:
                p = np.array([geo["ancla"][0] + rs[i], geo["ancla"][1], GROSOR_CHAPA])
                q2, e = self._senalar_punto(p, (q, geo["reposo"]))
                if q2 is not None:
                    ok[i], Q[i], elev[i], q = True, q2, e, q2
        self._senalar = {"rs": rs, "ok": ok, "q": Q, "elev": elev}
        return self._senalar

    def _senala_tabla(self, puntos: np.ndarray) -> np.ndarray:
        t = self._tabla_senalar()
        geo = self._modelo()
        rel = puntos[..., :2] - geo["ancla"]
        r = np.hypot(rel[..., 0], rel[..., 1])
        rumbo = np.degrees(np.arctan2(rel[..., 1], rel[..., 0]))
        f = (r - t["rs"][0]) / PASO_R
        i0 = np.clip(np.floor(f).astype(int), 0, len(t["rs"]) - 2)
        dentro = (f >= 0) & (f <= len(t["rs"]) - 1)
        lo, hi = np.degrees(self.cin.rangos[0])
        return dentro & t["ok"][i0] & t["ok"][i0 + 1] & (np.abs(rumbo) <= min(-lo, hi) - HOLGURA_MIN)

    # --- comprobación de verdad -------------------------------------------------------------------------------
    def _puntos(self, origen, R, d_loc):
        xs = np.linspace(0.0, LONGITUD_CORDON, N_PUNTOS)
        puntos = np.array([origen + R @ np.array([x, 0.0, ALTURA_PUNTA_ROBOT]) for x in xs])
        return xs, puntos, R @ d_loc

    def _cadena(self, puntos: np.ndarray, d: np.ndarray, semillas) -> _Cadena:
        """IK en cadena por los puntos del cordón (misma rama) desde cada semilla; la primera que vale."""
        for s in semillas:
            q, e_max, a_max, holgura, q_inicio = np.array(s, dtype=float), 0.0, 0.0, np.inf, None
            for k, p in enumerate(puntos):
                q, e, a = self.cin.inversa_pose(p * 1e-3, d, q, iteraciones=ITER_CADENA)
                e_max, a_max = max(e_max, e * 1000), max(a_max, np.degrees(a))
                holgura = min(holgura, self._holgura(q))
                if k == 0:
                    q_inicio = q.copy()
                if e_max >= TOL_MM or a_max >= TOL_GRADOS or holgura < HOLGURA_MIN:
                    break
            else:
                return _Cadena(True, e_max, a_max, holgura, q_inicio)
        return _Cadena(False, np.inf, np.inf, -np.inf, None)

    def _semillas(self, tabla, puntos, rumbo_dir) -> list[np.ndarray]:
        geo = self._modelo()
        ok, (ic, jc), rumbo = self._consultar(tabla, puntos[:1], np.array([rumbo_dir]))
        semillas = []
        if tabla["ok"][ic[0], jc[0]]:
            q = tabla["q"][ic[0], jc[0]].copy()
            q[0] += np.radians(rumbo[0]) * geo["signo_pan"]
            semillas.append(q)
        semillas.append(geo["reposo"])
        return semillas

    def comprobar_marco(self, origen, R, angulo_trabajo: float = 45.0,
                        angulo_avance: float = ANGULO_AVANCE_ROBOT) -> ResultadoAlcance:
        """Alcance para un marco del cordón cualquiera (origen en mm y giro 3x3 en la mesa), p. ej. el que dé el
        reconocimiento 3D de la junta. Sin propuesta (para eso, `comprobar` con la base)."""
        t0 = time.perf_counter()
        origen, R = np.asarray(origen, dtype=float), np.asarray(R, dtype=float)
        tabla = self._tabla(angulo_trabajo, angulo_avance)
        xs, puntos, d = self._puntos(origen, R, direccion_antorcha(angulo_trabajo, angulo_avance))
        rumbo_dir = float(np.degrees(np.arctan2(d[1], d[0])))
        ok_pts, _, _ = self._consultar(tabla, puntos, np.full(len(puntos), rumbo_dir))
        cadena = self._cadena(puntos, d, self._semillas(tabla, puntos, rumbo_dir))
        senala = self._senala(origen, R)
        sin = [] if cadena.suelda else [float(x) for x, o in zip(xs, ok_pts) if not o]
        return ResultadoAlcance(
            llega=cadena.suelda and senala, suelda=cadena.suelda, senala=senala, junta="",
            base=Anclaje("marco", float(origen[0]), float(origen[1]), 0.0),
            error_mm=round(cadena.error_mm, 3), error_grados=round(cadena.error_grados, 3),
            holgura_grados=round(cadena.holgura, 2), x_sin_alcance=sin, propuesta=None, frase="",
            ms=round((time.perf_counter() - t0) * 1000, 1),
            postura_inicio=None if cadena.q_inicio is None else [round(float(v), 5) for v in cadena.q_inicio],
        )

    def _senala(self, origen, R) -> bool:
        """Señala el inicio, el centro y el final del cordón (en ese orden, cada postura parte de la anterior)."""
        geo = self._modelo()
        t = self._tabla_senalar()
        q = None
        for x in (0.0, LONGITUD_CORDON / 2, LONGITUD_CORDON):
            p = origen + R @ np.array([x, 0.0, 0.0])
            rel = p[:2] - geo["ancla"]
            i = int(np.clip(np.rint((np.hypot(*rel) - t["rs"][0]) / PASO_R), 0, len(t["rs"]) - 1))
            semillas, elevaciones = [geo["reposo"]], list(ELEVACIONES_SENALAR)
            if t["ok"][i]:  # la postura de la tabla girada con el pan, y su elevación primero
                q_tab = t["q"][i].copy()
                q_tab[0] += np.arctan2(rel[1], rel[0]) * geo["signo_pan"]
                semillas.insert(0, q_tab)
                elevaciones.remove(t["elev"][i])
                elevaciones.insert(0, t["elev"][i])
            if q is not None:
                semillas.insert(0, q)
            q, _ = self._senalar_punto(p, semillas, elevaciones, ITER_CADENA)
            if q is None:
                return False
        return True

    # --- comprobación con propuesta ---------------------------------------------------------------------------
    def comprobar(self, junta, base: Anclaje = POSICION_BASE, *, proponer: bool = True) -> ResultadoAlcance:
        """¿Llega el robot a soldar y señalar la junta `junta` montada sobre `base`? Si no y `proponer`, el cambio
        más pequeño de la base que lo arregla (verificado con la IK de verdad)."""
        junta = TipoJunta(junta)
        clave = (junta.value, round(base.x, 1), round(base.y, 1), round(base.giro, 1), proponer)
        if clave in self._memo:
            return self._memo[clave]
        t0 = time.perf_counter()
        trabajo = ANGULO_TRABAJO_OBJETIVO[junta.value]
        origen, R = marco_cordon(junta, base)
        r = self.comprobar_marco(origen, R, trabajo)
        r.junta, r.base = junta.value, base
        if not r.llega and proponer:
            r.propuesta = self._proponer(junta, base, trabajo)
            r.frase = r.propuesta.frase if r.propuesta else "no llego: acércamela y ponla de frente a mí"
        r.ms = round((time.perf_counter() - t0) * 1000, 1)
        self._memo[clave] = r
        return r

    def _candidatas(self, base: Anclaje):
        g, dr, dl = np.meshgrid(np.array(GIROS, float), np.array(RADIAL, float), np.array(LATERAL, float),
                                indexing="ij")
        g, dr, dl = g.ravel(), dr.ravel(), dl.ravel()
        coste = np.abs(g) / (100.0 * GRADOS_POR_MM) + np.hypot(dr, dl) / 100.0
        piezas = (g != 0).astype(int) + (dr != 0) + (dl != 0)
        coste += COSTE_COMBINAR * np.maximum(piezas - 1, 0)
        coste[piezas == 0] = np.inf  # la que ya no llega
        return g, dr, dl, coste

    def _ok_bases(self, junta, base: Anclaje, tabla, g, dr, dl) -> np.ndarray:
        """Alcance según las tablas (soldar y señalar) de muchas bases a la vez: base girada g, alejada dr y movida
        dl a la izquierda del robot."""
        centro = np.array([base.x, base.y])
        u = centro / max(np.linalg.norm(centro), 1e-9)
        v = np.array([-u[1], u[0]])
        cx = centro[0] + dr * u[0] + dl * v[0]
        cy = centro[1] + dr * u[1] + dl * v[1]
        giro = base.giro + g
        dist = np.hypot(cx, cy)
        valida = (dist >= CENTRO_BASE[0]) & (dist <= CENTRO_BASE[1])
        # Puntos del cordón: centro + Rz(giro + 90) @ (x_base, y_cordón)
        xs_base = np.linspace(-LONGITUD_CORDON / 2, LONGITUD_CORDON / 2, N_PUNTOS)
        a = np.radians(giro + 90.0)[:, None]
        yc = Y_CORDON[junta]
        px = cx[:, None] + np.cos(a) * xs_base - np.sin(a) * yc
        py = cy[:, None] + np.sin(a) * xs_base + np.cos(a) * yc
        puntos = np.stack([px, py], axis=-1)
        d_loc = direccion_antorcha(ANGULO_TRABAJO_OBJETIVO[junta.value], ANGULO_AVANCE_ROBOT)
        rumbo_dir = np.degrees(np.arctan2(np.sin(a) * d_loc[0] + np.cos(a) * d_loc[1],
                                          np.cos(a) * d_loc[0] - np.sin(a) * d_loc[1]))
        ok, _, _ = self._consultar(tabla, puntos, np.broadcast_to(rumbo_dir, px.shape))
        senala = self._senala_tabla(puntos[:, [0, N_PUNTOS // 2, -1]])
        return valida & ok.all(axis=1) & senala.all(axis=1)

    def _proponer(self, junta: TipoJunta, base: Anclaje, trabajo: float) -> Propuesta | None:
        tabla = self._tabla(trabajo, ANGULO_AVANCE_ROBOT)
        g, dr, dl, coste = self._candidatas(base)
        ok = self._ok_bases(junta, base, tabla, g, dr, dl)
        robusta = ok.copy()
        for vg, vr, vl in ROBUSTEZ:
            robusta &= self._ok_bases(junta, base, tabla, g + vg, dr + vr, dl + vl)
        # Primero las robustas por coste; luego las demás
        orden = np.lexsort((coste, ~robusta))
        orden = [k for k in orden if ok[k] and np.isfinite(coste[k])]
        for k in orden[:MAX_VERIFICAR]:
            nueva = aplicar(base, g[k], -dr[k], dl[k])
            if self.comprobar(junta, nueva, proponer=False).llega:
                return Propuesta(float(g[k]), float(-dr[k]), float(dl[k]), nueva,
                                 frase_propuesta(g[k], -dr[k], dl[k]), bool(robusta[k]))
        return None


_POR_DEFECTO: Alcance | None = None


def comprobar_alcance(junta, base: Anclaje = POSICION_BASE, *, proponer: bool = True) -> ResultadoAlcance:
    """Atajo con un `Alcance` compartido por todo el proceso."""
    global _POR_DEFECTO
    if _POR_DEFECTO is None:
        _POR_DEFECTO = Alcance()
    return _POR_DEFECTO.comprobar(junta, base, proponer=proponer)
