#!/usr/bin/env python3
"""
barrido.py - Barrido de la tabla de madera. Independiente del taladro. Dos modos (config barrido.modo):

  "rejilla" (por defecto): posturas grabadas a mano sobre una rejilla del tapete. Lo que grabas es lo que hace.
      mesa.json           área del tapete en px (python calibrar_mesa.py --n-u 5 --n-v 3)
      posturas_mesa.json  boquilla sobre cada punto, a la altura de barrido (python grabar_posturas_mesa.py --real --a-mano)
      px de la tabla → (u,v) del área → postura interpolada (bilineal) + ajuste_altura.

  "ik" (experimental): cinemática inversa con boquilla.json. Lo de abajo describe este modo.

--- modo "ik" ---

El gesto (zigzag) se calcula sobre la tabla detectada y se repite igual esté donde esté, siempre a la misma altura
sobre la mesa. Calibración: boquilla.json (python calibrar_boquilla.py --real --a-mano):
    - tcp: dónde está la punta de la boquilla respecto a la muñeca (pivote)
    - toques: punta apoyada en puntos de la mesa + su píxel → homografía px → (x,y) del robot y plano de la mesa

Cadena: píxel de la tabla → (x,y) del robot (homografía) → z = plano de la mesa + altura → cinemática inversa
(orientación = la media de los toques, girada con la base) → postura.

Configuración (config.json → "barrido"), ver POR_DEFECTO.
"""

import json
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

import trayectoria
from trayectoria import Trayectoria

POR_DEFECTO = {
    "modo": "rejilla",          # "rejilla" (posturas grabadas) o "ik" (cinemática inversa, experimental)
    "ajuste_altura": 0.0,       # rejilla: offset shoulder_lift sobre las posturas grabadas (negativo = más ARRIBA)
    "altura_pre": -25.0,        # rejilla: offset shoulder_lift del punto "encima" antes de bajar / al subir
    "tapete_n_pasadas": 12,     # barrido de TODO el tapete (tecla T): pasadas a lo largo del lado largo del área
    "tapete_puntos_por_pasada": 10,
    "tapete_margen": 0.03,
    "tapete_velocidad_barrido": 5.0,   # más lento que la tabla: que dé tiempo a aspirar
    "tapete_ajuste_altura": 2.0,  # como ajuste_altura pero para el tapete (positivo = más BAJO). El tapete está por
                                  # debajo de la tabla: va más bajo que ella
    "tapete_duracion_s": None,  # si se pone (p. ej. 20), el zigzag del tapete dura eso y se ignora su velocidad      # >0: se queda un poco dentro del área calibrada (mesa.json)
    "elevar_giros": -8.0,
    "pausa_giros_s": 0.3,       # quieto tras bajar al inicio de cada pasada, antes de barrer (s). 0 = sin pausa       # rejilla: offset shoulder_lift en los cambios de pasada (sube, cambia, baja). 0 = sin
    "margen": -0.08,            # fracción de cada lado de la tabla (negativo = se pasa un poco del borde)
    "n_pasadas": 3,             # pasadas a lo largo del lado largo
    "puntos_por_pasada": 8,     # waypoints por pasada (con IK las rectas son rectas en la mesa)
    "altura_m": 0.015,          # altura de la punta sobre la mesa durante el barrido (m)
    "altura_pre_m": 0.07,       # altura del punto "encima" antes de bajar y al subir para volver (m)
    "peso_orientacion": 0.1,    # cuánto se intenta mantener la inclinación de la boquilla de los toques
    "error_max_m": 0.008,       # si la IK no llega a algún punto con este error, no se barre
    "velocidad_barrido": 8.0,   # unidades/s de la articulación que más se mueve durante el zigzag
    "duracion_min_s": 4.0,
    "automatico": False,        # True: barre solo cuando hay tabla y no hay taladro durante t_sin_taladro_s
    "t_sin_taladro_s": 5.0,
}


def config_barrido(config: Dict) -> Dict:
    return {**POR_DEFECTO, **config.get("barrido", {})}


# --- recorrido ------------------------------------------------------------------------------------------------------------

def recorrido_px(esquinas: np.ndarray, margen: float = 0.0, n_pasadas: int = 3,
                 puntos_por_pasada: int = 8) -> np.ndarray:
    """Zigzag sobre el rectángulo `esquinas` (4×2, orden horario). Pasadas paralelas al lado largo. (N, 2) px."""
    e = np.asarray(esquinas, float).reshape(4, 2)
    if np.linalg.norm(e[1] - e[0]) < np.linalg.norm(e[2] - e[1]):   # que e0→e1 sea el lado largo
        e = np.roll(e, -1, axis=0)
    n_pasadas = max(1, int(n_pasadas))
    k = max(2, int(puntos_por_pasada))
    ts = [0.5] if n_pasadas == 1 else np.linspace(margen, 1 - margen, n_pasadas)
    puntos = []
    for i, t in enumerate(ts):
        ss = np.linspace(margen, 1 - margen, k)
        if i % 2 == 1:
            ss = ss[::-1]
        for s in ss:
            arriba = e[0] + s * (e[1] - e[0])
            abajo = e[3] + s * (e[2] - e[3])
            puntos.append(arriba + t * (abajo - arriba))
    return np.array(puntos)


# --- calibración y cinemática ---------------------------------------------------------------------------------------------

class MapeoIK:
    """px de la mesa → postura del robot, por cinemática inversa con la calibración de boquilla.json."""

    def __init__(self, config: Dict, ruta: str = "boquilla.json"):
        self.cb = config_barrido(config)
        self.ok = False
        try:
            d = json.load(open(ruta))
        except FileNotFoundError:
            print("⚠️  [Barrido] Sin boquilla.json: ejecuta python calibrar_boquilla.py --real --a-mano")
            return
        from cinematica import Cinematica, media_rotaciones
        from calibrar_boquilla import ajustar_toques
        self.cin = Cinematica(tcp=d["tcp"], desfases=d.get("desfases", (0, 0, 0, 0, 0)))
        self.toques = d["toques"]
        self.H, self.plano, exy, ez = ajustar_toques(self.cin, self.toques)
        self.R_ref = media_rotaciones([self.cin.marco(t["postura"])[:3, :3] for t in self.toques])
        xy = np.array([self.cin.punta(t["postura"])[:2] for t in self.toques])
        self.yaw_ref = float(np.arctan2(*xy.mean(axis=0)[::-1]))
        self.ok = True
        print(f"[Barrido] boquilla.json cargado ✓ (error toques: {exy.max():.1f} mm en mesa, {ez.max():.1f} mm en altura)")

    def a_xyz(self, puntos_px: np.ndarray, altura: float) -> np.ndarray:
        xy = cv2.perspectiveTransform(np.asarray(puntos_px, np.float32).reshape(-1, 1, 2), self.H).reshape(-1, 2)
        z = self.plano[0] * xy[:, 0] + self.plano[1] * xy[:, 1] + self.plano[2] + altura
        return np.c_[xy, z]

    def orientacion(self, p: np.ndarray) -> np.ndarray:
        from cinematica import rot_z
        return rot_z(float(np.arctan2(p[1], p[0])) - self.yaw_ref) @ self.R_ref

    def semilla(self, p: np.ndarray) -> Dict:
        """Postura del toque más cercano: arranca la IK en la rama buena del codo."""
        d = [np.linalg.norm(self.cin.punta(t["postura"]) - p) for t in self.toques]
        return dict(self.toques[int(np.argmin(d))]["postura"])

    def posturas(self, puntos_xyz: np.ndarray, semilla: Optional[Dict] = None) -> Tuple[List[Dict], float]:
        """IK encadenada (cada punto parte del anterior). (posturas, error máximo en m)."""
        q = semilla or self.semilla(puntos_xyz[0])
        out, err_max = [], 0.0
        for p in puntos_xyz:
            q, e = self.cin.ik(p, self.orientacion(p), q, self.cb["peso_orientacion"])
            out.append(q)
            err_max = max(err_max, e)
        return out, err_max


# --- modo rejilla ----------------------------------------------------------------------------------------------------------

class MapeoRejilla:
    """px de la mesa → (u,v) del área de mesa.json → postura interpolada de posturas_mesa.json."""

    def __init__(self, config: Dict, ruta_mesa: str = "mesa.json", ruta_posturas: str = "posturas_mesa.json"):
        self.cb = config_barrido(config)
        self.ok = False
        try:
            mesa = json.load(open(ruta_mesa))
            pm = json.load(open(ruta_posturas))
        except FileNotFoundError as e:
            print(f"⚠️  [Barrido] Falta {e.filename}: calibrar_mesa.py --n-u 5 --n-v 3 y grabar_posturas_mesa.py --real --a-mano")
            return
        self.esquinas_px = np.array(mesa["esquinas_px"], float)
        self.H = cv2.getPerspectiveTransform(np.array(mesa["esquinas_px"], np.float32),
                                             np.array([[0, 0], [1, 0], [1, 1], [0, 1]], np.float32))
        self.n_u, self.n_v = pm["rejilla"]["n_u"], pm["rejilla"]["n_v"]
        if mesa.get("rejilla", pm["rejilla"]) != pm["rejilla"]:
            print(f"⚠️  [Barrido] mesa.json ({mesa.get('rejilla')}) y posturas_mesa.json ({pm['rejilla']}) no coinciden")
            return
        M = trayectoria.MOTOR_NAMES
        self.grid = np.full((self.n_u, self.n_v, len(M)), np.nan)
        for clave, q in pm["posturas"].items():
            i, j = (int(x) for x in clave.split(","))
            self.grid[i, j] = [q.get(f"{m}.pos", 0.0) for m in M]
        faltan = [f"{i},{j}" for i in range(self.n_u) for j in range(self.n_v) if np.isnan(self.grid[i, j, 0])]
        if faltan:
            print(f"⚠️  [Barrido] posturas_mesa.json incompleto, faltan {faltan}")
            return
        self.ok = True
        print(f"[Barrido] Modo rejilla {self.n_u}×{self.n_v} cargado ✓")

    def a_uv(self, puntos_px: np.ndarray) -> np.ndarray:
        return cv2.perspectiveTransform(np.asarray(puntos_px, np.float32).reshape(-1, 1, 2), self.H).reshape(-1, 2)

    def postura(self, u: float, v: float) -> Dict[str, float]:
        x = float(np.clip(u, 0, 1)) * (self.n_u - 1)
        y = float(np.clip(v, 0, 1)) * (self.n_v - 1)
        i0, j0 = min(int(x), self.n_u - 2), min(int(y), self.n_v - 2)
        tx, ty = x - i0, y - j0
        g = self.grid
        q = ((1 - tx) * (1 - ty) * g[i0, j0] + tx * (1 - ty) * g[i0 + 1, j0]
             + (1 - tx) * ty * g[i0, j0 + 1] + tx * ty * g[i0 + 1, j0 + 1])
        return {f"{m}.pos": float(q[k]) for k, m in enumerate(trayectoria.MOTOR_NAMES)}


def recorrido_tapete_px(mapeo: "MapeoRejilla", config: Dict) -> np.ndarray:
    """Zigzag sobre TODA el área calibrada (mesa.json)."""
    cb = config_barrido(config)
    from madera import ordenar_esquinas
    return recorrido_px(ordenar_esquinas(mapeo.esquinas_px), cb["tapete_margen"], cb["tapete_n_pasadas"],
                        cb["tapete_puntos_por_pasada"])


def _planificar_rejilla(obs_actual, puntos_px, config, mapeo: MapeoRejilla, puntos_por_pasada=None, velocidad=None,
                        duracion=None, ajuste_altura=None):
    cb = config_barrido(config)
    uv = mapeo.a_uv(puntos_px)
    fuera = float(np.max(np.maximum(-uv, uv - 1)))
    if fuera > 0.15:
        print(f"❌ [Barrido] La tabla se sale un {fuera*100:.0f} % del área calibrada (mesa.json)")
        return None, None, float("inf"), []
    q_barrido = [trayectoria.aplicar_offsets(mapeo.postura(u, v), {"shoulder_lift": cb["ajuste_altura"] if ajuste_altura is None else ajuste_altura})
                 for u, v in uv]
    # giros por arriba: al final de cada pasada sube, cambia de pasada en alto y baja al empezar la siguiente
    k = max(2, int(puntos_por_pasada or cb["puntos_por_pasada"]))
    if cb["elevar_giros"] and len(q_barrido) > k:
        con_giros, inicios = [], []
        for i, q in enumerate(q_barrido):
            if i > 0 and i % k == 0:   # empieza una pasada nueva
                con_giros.append(trayectoria.aplicar_offsets(q_barrido[i - 1], {"shoulder_lift": cb["elevar_giros"]}))
                con_giros.append(trayectoria.aplicar_offsets(q, {"shoulder_lift": cb["elevar_giros"]}))
                inicios.append(len(con_giros))   # índice del punto ya abajo, donde empieza la pasada
            con_giros.append(q)
        q_barrido = con_giros
    else:
        inicios = []
    primero = q_barrido[0]
    actual = {f"{m}.pos": obs_actual.get(f"{m}.pos", 0.0) for m in trayectoria.MOTOR_NAMES}
    intermedia = dict(config["supervisor"]["posicion_intermedia"])
    intermedia["shoulder_pan.pos"] = primero["shoulder_pan.pos"]
    encima = trayectoria.aplicar_offsets(primero, {"shoulder_lift": cb["altura_pre"]})
    p_ida = [actual, intermedia, encima, primero]
    vel = config["trayectorias"]["velocidad_trayectoria"]
    ida = Trayectoria(p_ida, max(3.0, trayectoria.calcular_duracion_optima(p_ida, vel)), interpolacion="pchip")
    tw = ida.tiempos_waypoints
    ida.fases = [("Reposo → Intermedia", 0.0), ("Encima de la tabla", float(tw[1])), ("Bajando", float(tw[2]))]
    dur = duracion or max(cb["duracion_min_s"],
                          trayectoria.calcular_duracion_optima(q_barrido, velocidad or cb["velocidad_barrido"]))
    barr = Trayectoria(q_barrido, dur, interpolacion="pchip")
    # que ninguna articulación supere el tope de seguridad (paso_maximo_por_ciclo · fps), con un 10 % de margen
    tope = 0.9 * config["seguridad"]["paso_maximo_por_ciclo"] * config["supervisor"]["fps"]
    Q = np.array([[barr.muestrear(t, False)[k] for k in barr.puntos[0]] for t in np.linspace(0, dur, 600)])
    pico = float(np.abs(np.diff(Q, axis=0)).max() * 599 / dur)
    if pico > tope:
        dur_nueva = dur * pico / tope
        print(f"[Barrido] {dur:.0f} s es demasiado rápido para la seguridad: lo alargo a {dur_nueva:.0f} s")
        barr = Trayectoria(q_barrido, dur_nueva, interpolacion="pchip")
    if cb["pausa_giros_s"] and inicios:
        barr = ConPausas(barr, [float(barr.tiempos_waypoints[i]) for i in inicios], float(cb["pausa_giros_s"]))
    barr.fases = [("Barriendo", 0.0)]
    return ida, barr, 0.0, [intermedia, encima] + q_barrido


class ConPausas:
    """Una Trayectoria con paradas de `pausa` s en los instantes `t_pausas` (tiempo de la trayectoria original)."""

    def __init__(self, base: Trayectoria, t_pausas: List[float], pausa: float):
        self.base, self.t_pausas, self.pausa = base, sorted(t_pausas), pausa
        self.puntos = base.puntos
        self.duracion = base.duracion + pausa * len(self.t_pausas)
        self.tiempos_waypoints = np.array([self._a_real(t) for t in base.tiempos_waypoints])
        self.fases = base.fases

    def _a_real(self, t_base: float) -> float:
        return t_base + self.pausa * sum(1 for tp in self.t_pausas if tp < t_base)

    def _a_base(self, t: float) -> float:
        for i, tp in enumerate(self.t_pausas):
            inicio = tp + i * self.pausa          # instante real en que empieza esta pausa
            if t < inicio:
                return t - i * self.pausa
            if t < inicio + self.pausa:
                return tp                         # parado
        return t - len(self.t_pausas) * self.pausa

    def muestrear(self, t: float, aplicar_ease: bool = True) -> Dict[str, float]:
        return self.base.muestrear(self._a_base(float(np.clip(t, 0, self.duracion))), aplicar_ease)

    def progreso(self, t: float) -> float:
        return float(np.clip(t / self.duracion, 0.0, 1.0))

    def fase_actual(self, t: float) -> str:
        return self.fases[0][0]


def crear_mapeo(config: Dict):
    """El mapeo del modo configurado (MapeoRejilla o MapeoIK)."""
    return MapeoIK(config) if config_barrido(config)["modo"] == "ik" else MapeoRejilla(config)


# --- trayectorias -----------------------------------------------------------------------------------------------------------

def _vertical(p_abajo: np.ndarray, alto: float, n: int = 4) -> np.ndarray:
    """Puntos en vertical desde p_abajo hasta `alto` metros más arriba."""
    return np.array([p_abajo + np.array([0, 0, alto * s]) for s in np.linspace(0, 1, n)])


def planificar_barrido(obs_actual: Dict, puntos_px: np.ndarray, config: Dict, mapeo,
                       puntos_por_pasada=None, velocidad=None, duracion=None, ajuste_altura=None) -> Tuple[Optional[Trayectoria], Optional[Trayectoria], float, List[Dict]]:
    """(ida, barrido, error máx m, todas las posturas). ida: reposo → intermedia → encima del primer punto → bajada
    vertical. Si la IK no llega a algún punto, devuelve (None, None, error, [])."""
    if isinstance(mapeo, MapeoRejilla):
        return _planificar_rejilla(obs_actual, puntos_px, config, mapeo, puntos_por_pasada, velocidad, duracion,
                                   ajuste_altura)
    cb = config_barrido(config)
    abajo = mapeo.a_xyz(puntos_px, cb["altura_m"])
    bajada = _vertical(abajo[0], cb["altura_pre_m"])[::-1]            # de arriba a abajo
    q_bajada, e1 = mapeo.posturas(bajada)
    q_barrido, e2 = mapeo.posturas(abajo, semilla=q_bajada[-1])
    err = max(e1, e2)
    if err > cb["error_max_m"]:
        return None, None, err, []

    actual = {f"{m}.pos": obs_actual.get(f"{m}.pos", 0.0) for m in trayectoria.MOTOR_NAMES}
    intermedia = dict(config["supervisor"]["posicion_intermedia"])
    intermedia["shoulder_pan.pos"] = q_bajada[0]["shoulder_pan.pos"]
    vel = config["trayectorias"]["velocidad_trayectoria"]
    p_ida = [actual, intermedia] + q_bajada
    ida = Trayectoria(p_ida, max(3.0, trayectoria.calcular_duracion_optima(p_ida, vel)), interpolacion="pchip")
    tw = ida.tiempos_waypoints
    ida.fases = [("Reposo → Intermedia", 0.0), ("Encima de la tabla", float(tw[1])), ("Bajando", float(tw[2]))]

    dur = max(cb["duracion_min_s"], trayectoria.calcular_duracion_optima(q_barrido, cb["velocidad_barrido"]))
    barr = Trayectoria(q_barrido, dur, interpolacion="pchip")
    barr.fases = [("Barriendo", 0.0)]
    return ida, barr, err, q_bajada + q_barrido


def planificar_vuelta_barrido(obs_actual: Dict, config: Dict, postura_reposo: Dict,
                              mapeo: Optional[MapeoIK] = None) -> Trayectoria:
    """SUBE en vertical desde donde esté la punta (IK), luego a la posición intermedia y a reposo."""
    cb = config_barrido(config)
    actual = {f"{m}.pos": obs_actual.get(f"{m}.pos", 0.0) for m in trayectoria.MOTOR_NAMES}
    subida = []
    if isinstance(mapeo, MapeoIK) and mapeo.ok:
        p = mapeo.cin.punta(actual)
        q, e = mapeo.posturas(_vertical(p, cb["altura_pre_m"])[1:], semilla=actual)
        if e <= cb["error_max_m"]:
            subida = q
    if not subida:   # rejilla (o sin IK): primero solo el hombro hacia arriba, lo demás quieto
        arriba = dict(actual)
        arriba["shoulder_lift.pos"] += cb["altura_pre"]
        subida = [arriba]
    intermedia = dict(config["supervisor"]["posicion_intermedia"])
    intermedia["shoulder_pan.pos"] = actual["shoulder_pan.pos"]
    puntos = [actual] + subida + [intermedia, dict(postura_reposo)]
    dur = max(3.0, trayectoria.calcular_duracion_optima(puntos, config["trayectorias"]["velocidad_trayectoria"]))
    traj = Trayectoria(puntos, dur, interpolacion="pchip")
    tw = traj.tiempos_waypoints
    traj.fases = [("Subiendo", 0.0), ("Retrocediendo", float(tw[-3])), ("A reposo", float(tw[-2]))]
    return traj


def dibujar_recorrido(img_bgr: np.ndarray, puntos_px: np.ndarray, color=(255, 255, 0), progreso: Optional[float] = None):
    p = np.round(puntos_px).astype(np.int32)
    cv2.polylines(img_bgr, [p], False, color, 1, cv2.LINE_AA)
    cv2.circle(img_bgr, tuple(int(x) for x in p[0]), 4, color, -1)
    if progreso is not None and len(p) > 1:
        i = progreso * (len(p) - 1)
        j = min(int(i), len(p) - 2)
        q = puntos_px[j] + (i - j) * (puntos_px[j + 1] - puntos_px[j])
        cv2.circle(img_bgr, (int(q[0]), int(q[1])), 7, color, 2)
