"""Mesa de montaje v2 simulada en tiempo real: el SO-101 en MuJoCo y las piezas del CAD (base, chapa móvil,
antorcha del robot y su soporte) para el simulador de la demo (`lewelder.simulador`).

Qué es física y qué es cinemática
---------------------------------
- **El brazo es física de verdad.** El modelo es el de `sim.escena` (SO-101 con sus actuadores de posición, el
  mismo que graba las demostraciones). Un hilo propio integra a `HZ_FISICA` (480 Hz: el paso del modelo) en tiempo
  real y quien manda (guion, replay o política) solo fija las posiciones objetivo con `mandar`.
- **Las piezas son cuerpos cinemáticos (mocap)** con las mallas de los STL del CAD (`hardware/v2/cad/stl`), para que
  las cámaras de MuJoCo las vean si una política las necesita. Se mueven con reglas sencillas que valen para
  cualquier controlador:
    * **Agarre:** si la pinza se cierra (`gripper` < `PINZA_CERRADA`) con su punto de agarre (`gripperframe`) a
      menos de `RADIO_AGARRE` del agarre de una pieza (la aleta de la chapa, el mango de la antorcha), la pieza queda
      pegada a la pinza con la transformación de ese momento. Al abrirla (> `PINZA_ABIERTA`), se suelta.
    * **Imanes:** la chapa que se suelta cerca de su sitio en la base (T o esquina, < `TOL_IMAN_MM` y
      < `TOL_IMAN_GRADOS`) se va sola a su sitio en `T_IMAN` s (las guías y los imanes autocentran, spec v2 §8).
      La antorcha que se suelta cerca del soporte vuelve a él. Lo demás cae a la mesa (o encima de la base:
      "junta incompleta").
- **Esta tarea 2 (montaje con los STL en MuJoCo) se enchufa aquí** cuando esté en main: si su escena trae los
  imanes y el agarre por contacto, `MesaSim` puede delegar en ella (ver `docs/simulador.md`, adaptadores).

Marcos (mm y grados, `lewelder.contrato`)
-----------------------------------------
- **Mesa:** el del contrato (Z = 0 en el tablero, origen en el centro de la huella del robot).
- **Base** (`B`): origen en el centro de su cara superior (Z mesa = `GROSOR_CHAPA`); X a lo largo, Y transversal
  (+Y hacia el tope de la esquina), giro como `POSICION_BASE` (`rot_z(giro) @ rot_z(90)`).
- **Chapa móvil** (`M`): origen en el centro del canto que apoya, a media chapa; X a lo largo, Y hacia arriba cuando
  está de pie (0 a `ALTO_MOVIL`), Z hacia la cara de la aleta. Montada: X_M = -X_B, Y_M = Z_B, Z_M = Y_B (la aleta
  queda en X_B = -35 hacia +Y_B, como dice el contrato); en la T el origen va en (0, 3, -2) de la base y en la
  esquina en (0, 34, 0). Tumbada: Z_M hacia arriba (aleta arriba) y el origen a media chapa sobre la mesa.
- **Antorcha del robot** (`A`): origen en la punta, Z del mango a la punta (como el sitio `punta_antorcha` de la
  escena). En el soporte, la punta toca el fondo del tubo (Z = 6) y el mango queda a `SOPORTE_ANTORCHA["z_mango"]`.
- **Soporte** (`S`): origen en el eje del tubo sobre el tablero.

Los STL vienen con Y hacia arriba (SolidWorks); `MALLAS_CAD` dice cómo se pasa cada uno al marco de su pieza.
"""
from __future__ import annotations

import logging
import math
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

import mujoco
import numpy as np

from lewelder import contrato as c
from lewelder.alcance import marco_base, marco_cordon, rot_z

log = logging.getLogger("lewelder.mesa_sim")

RAIZ = Path(__file__).resolve().parents[1]
DIR_STL = RAIZ / "hardware" / "v2" / "cad" / "stl"
MM = 1e-3

HZ_FISICA = 480  # = 1 / timestep del modelo de `sim.escena`
SUBPASOS = 4  # pasos de física por vuelta del hilo (120 vueltas por segundo)

# Pinza (rad de la articulación `gripper`): abierta, cerrada sobre la aleta y cerrada sobre el mango.
PINZA_ABRIR = 1.0
PINZA_CHAPA = 0.0
PINZA_MANGO = 0.10
PINZA_CERRADA = 0.30  # por debajo: la pinza agarra lo que tenga entre los dedos
PINZA_ABIERTA = 0.50  # por encima: suelta
RADIO_AGARRE = 22.0  # mm del punto de agarre de la pinza al de la pieza para cogerla

# Imanes y soporte
TOL_IMAN_MM = 25.0
TOL_IMAN_GRADOS = 45.0
TOL_SOPORTE_MM = 30.0
T_IMAN = 0.35  # s que tarda la chapa en "chuparse" a su sitio

# Agarre de cada pieza en su marco (mm): el punto donde va `gripperframe`.
AGARRE_ALETA = np.array([-c.ALETA["x"], c.ALTO_MOVIL / 2, c.GROSOR_CHAPA / 2 + 11.0])  # (35, 20, 14)
DIST_MANGO = c.LONGITUD_ANTORCHA_ROBOT  # mm de la punta al punto de agarre (el de la escena: 100)
PUNTA_EN_SOPORTE = 6.0  # mm: la punta apoya en el fondo del tubo
# Origen de la chapa móvil montada, en el marco de la base, y su giro (columnas: X, Y, Z de la chapa en la base).
ORIGEN_MONTADA = {c.TipoJunta.T: np.array([0.0, c.GROSOR_CHAPA / 2, c.Z_CANTO_MOVIL[c.TipoJunta.T]]),
                  c.TipoJunta.ESQUINA: np.array([0.0, c.Y_CORDON[c.TipoJunta.ESQUINA] + c.GROSOR_CHAPA / 2,
                                                 c.Z_CANTO_MOVIL[c.TipoJunta.ESQUINA]])}
R_MONTADA = np.array([[-1.0, 0.0, 0.0], [0.0, 0.0, 1.0], [0.0, 1.0, 0.0]])
CHAPA_POR_DEFECTO = (220.0, -222.0, 15.0)  # (x, y, giro) del centro de la chapa tumbada en la zona libre

# STL del CAD → marco de su pieza: p_pieza = A @ p_stl + b (mm). Ver el docstring del módulo.
MALLAS_CAD = {
    "base": ("BASE-V2.STL", [[1, 0, 0], [0, 0, -1], [0, 1, 0]], [-100.0, 40.0, -6.0]),
    "movil": ("MOVIL-V2.STL", [[-1, 0, 0], [0, 1, 0], [0, 0, -1]], [70.0, 0.0, 21.0]),
    "antorcha_a": ("ANTORCHA-ROBOT-V2_mitad-A.STL", [[-1, 0, 0], [0, 0, -1], [0, -1, 0]], [10.0, 0.0, 0.0]),
    "antorcha_b": ("ANTORCHA-ROBOT-V2_mitad-B.STL", [[1, 0, 0], [0, 0, 1], [0, -1, 0]], [-10.0, 0.0, 0.0]),
    "soporte": ("SOPORTE-ANTORCHA-V2.STL", [[1, 0, 0], [0, 0, -1], [0, 1, 0]], [-35.0, 35.0, 0.0]),
}
COLOR_PIEZA = {"base": [0.80, 0.84, 0.90, 1], "movil": [0.93, 0.95, 0.98, 1], "antorcha_a": [0.95, 0.45, 0.12, 1],
               "antorcha_b": [0.95, 0.45, 0.12, 1], "soporte": [0.55, 0.62, 0.72, 1]}


# --- geometría ----------------------------------------------------------------------------------------------------
@dataclass
class Pose:
    """Posición (mm, mesa) y giro 3x3 (columnas = ejes de la pieza en la mesa)."""

    p: np.ndarray
    R: np.ndarray

    def copia(self) -> Pose:
        return Pose(np.array(self.p, dtype=float), np.array(self.R, dtype=float))

    def aplicar(self, local) -> np.ndarray:
        return self.p + self.R @ np.asarray(local, dtype=float)

    def componer(self, otra: Pose) -> Pose:
        return Pose(self.aplicar(otra.p), self.R @ otra.R)

    def inversa(self) -> Pose:
        return Pose(-self.R.T @ self.p, self.R.T)

    def quat(self) -> list[float]:
        q = np.zeros(4)
        mujoco.mju_mat2Quat(q, np.asarray(self.R, dtype=float).reshape(9))
        return q.tolist()


def angulo_entre(R1: np.ndarray, R2: np.ndarray) -> float:
    """Ángulo (grados) del giro que lleva R1 a R2."""
    cos = (np.trace(R1.T @ R2) - 1.0) / 2.0
    return float(np.degrees(np.arccos(np.clip(cos, -1.0, 1.0))))


def interpolar(a: Pose, b: Pose, s: float) -> Pose:
    """Interpolación lineal en posición y esférica en giro (0 → a, 1 → b)."""
    qa, qb = np.array(a.quat()), np.array(b.quat())
    if qa @ qb < 0:
        qb = -qb
    q = (1 - s) * qa + s * qb  # nlerp: basta para giros cortos
    q /= np.linalg.norm(q)
    R = np.zeros(9)
    mujoco.mju_quat2Mat(R, q)
    return Pose((1 - s) * a.p + s * b.p, R.reshape(3, 3))


def pose_base(base: c.Anclaje) -> Pose:
    o, R = marco_base(base)
    return Pose(o, R)


def pose_montada(junta, base: c.Anclaje) -> Pose:
    """Pose de la chapa móvil montada en la junta `junta` sobre `base`."""
    b = pose_base(base)
    junta = c.TipoJunta(junta)
    return Pose(b.aplicar(ORIGEN_MONTADA[junta]), b.R @ R_MONTADA)


def pose_tumbada(x: float, y: float, giro: float, z_apoyo: float = 0.0) -> Pose:
    """Chapa tumbada con la aleta arriba, centro en (x, y), giro como el de la base (0 = X de la chapa hacia +Y)."""
    R = rot_z(giro) @ rot_z(90.0)
    centro = np.array([x, y, z_apoyo + c.GROSOR_CHAPA / 2])
    return Pose(centro - R[:, 1] * (c.ALTO_MOVIL / 2), R)


def centro_tumbada(pose: Pose) -> tuple[float, float, float]:
    """(x, y, giro) de una chapa tumbada (inversa de `pose_tumbada`)."""
    centro = pose.aplicar([0.0, c.ALTO_MOVIL / 2, 0.0])
    eje = pose.R[:, 0]
    giro = math.degrees(math.atan2(eje[1], eje[0])) - 90.0
    return float(centro[0]), float(centro[1]), (giro + 180.0) % 360.0 - 180.0


def pose_antorcha_en_soporte() -> Pose:
    s = c.SOPORTE_ANTORCHA
    R = np.array([[1.0, 0.0, 0.0], [0.0, -1.0, 0.0], [0.0, 0.0, -1.0]])  # Z de la antorcha hacia abajo
    return Pose(np.array([s["x"], s["y"], PUNTA_EN_SOPORTE]), R)


def pose_soporte() -> Pose:
    s = c.SOPORTE_ANTORCHA
    return Pose(np.array([s["x"], s["y"], 0.0]), np.eye(3))


# --- mallas ---------------------------------------------------------------------------------------------------------
def _leer_stl(ruta: Path) -> tuple[np.ndarray, np.ndarray]:
    datos = ruta.read_bytes()
    n = int(np.frombuffer(datos, dtype="<u4", count=1, offset=80)[0])
    reg = np.frombuffer(datos, dtype=np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")]), count=n,
                        offset=84)
    v, inv = np.unique(reg["v"].reshape(-1, 3), axis=0, return_inverse=True)
    return v.astype(float), inv.reshape(-1, 3).astype(np.int64)


_CACHE_MALLAS: dict[str, tuple[np.ndarray, np.ndarray]] = {}


def malla_cad(nombre: str) -> tuple[np.ndarray, np.ndarray]:
    """(vértices en mm en el marco de su pieza, caras) de una pieza del CAD."""
    if nombre not in _CACHE_MALLAS:
        archivo, A, b = MALLAS_CAD[nombre]
        v, f = _leer_stl(DIR_STL / archivo)
        v = v @ np.asarray(A, dtype=float).T + np.asarray(b, dtype=float)
        if np.linalg.det(np.asarray(A, dtype=float)) < 0:  # (no pasa: todas son giros) conserva la orientación
            f = f[:, ::-1]
        _CACHE_MALLAS[nombre] = (v, f)
    return _CACHE_MALLAS[nombre]


def construir_modelo() -> mujoco.MjModel:
    """El modelo de `sim.escena` (SO-101 + antorcha en la pinza para la IK) sin la mesa de anclajes v1 y con las
    piezas v2 del CAD como cuerpos mocap (solo visuales: las ven las cámaras de MuJoCo, no chocan)."""
    from sim import escena

    spec = escena.construir_spec()
    # Fuera lo de la v1: base de anclajes, piezas y la antorcha pegada a la pinza (se queda su sitio para la IK).
    for g in spec.geoms:
        nombre = g.name or ""
        if nombre.startswith(("base_anclajes", "anclaje_", "recta_", "t_", "antorcha_")):
            g.contype, g.conaffinity = 0, 0
            g.rgba = [0, 0, 0, 0]
            g.group = 5
    for pieza in ("base", "movil", "antorcha_a", "antorcha_b", "soporte"):
        v, f = malla_cad(pieza)
        spec.add_mesh(name=f"cad_{pieza}", uservert=(v * MM).reshape(-1).tolist(),
                      userface=f.reshape(-1).astype(int).tolist())
    cuerpos = {"base": ("base",), "movil": ("movil",), "antorcha": ("antorcha_a", "antorcha_b"),
               "soporte": ("soporte",)}
    for cuerpo, mallas in cuerpos.items():
        b = spec.worldbody.add_body(name=f"v2_{cuerpo}", mocap=True, pos=[0, 0, -1])
        for m in mallas:
            g = b.add_geom(name=f"v2_{m}", type=mujoco.mjtGeom.mjGEOM_MESH, meshname=f"cad_{m}", rgba=COLOR_PIEZA[m])
            g.contype, g.conaffinity = 0, 0
    return spec.compile()


# --- estado de las piezas -------------------------------------------------------------------------------------------
@dataclass
class Pieza:
    nombre: str
    pose: Pose
    estado: str  # chapa: tumbada | agarrada | montada | encima | encajando; antorcha: soporte | agarrada | suelta
    junta: str | None = None  # chapa montada: "t" | "esquina"
    agarre_rel: Pose | None = None  # pose de la pieza en el marco de `gripperframe` mientras está agarrada
    animacion: tuple | None = None  # (pose_ini, pose_fin, t0, duracion, estado_final, junta)
    extra: dict = field(default_factory=dict)


class MesaSim:
    """El SO-101 y las piezas v2 en tiempo real. Hilo de física propio; todo lo público es seguro entre hilos."""

    def __init__(self, hz_fisica: int = HZ_FISICA, tiempo_real: bool = True):
        self.modelo = construir_modelo()
        self.datos = mujoco.MjData(self.modelo)
        self.tiempo_real = tiempo_real
        paso = self.modelo.opt.timestep
        if abs(1.0 / paso - hz_fisica) > 1:
            log.info("el modelo integra a %.0f Hz (pedido %d)", 1.0 / paso, hz_fisica)
        self.hz_fisica = 1.0 / paso
        self._cerrojo = threading.RLock()
        self._hilo: threading.Thread | None = None
        self._parar = threading.Event()
        from sim.cinematica import ARTICULACIONES

        self.qadr = np.array([self.modelo.jnt_qposadr[self.modelo.joint(n).id] for n in ARTICULACIONES])
        self.sitio_pinza = self.modelo.site("gripperframe").id
        self.sitio_punta = self.modelo.site("punta_antorcha").id
        self.mocap = {n: int(self.modelo.body_mocapid[self.modelo.body(f"v2_{n}").id])
                      for n in ("base", "movil", "antorcha", "soporte")}
        self.cuerpos_robot = self._cuerpos_robot()
        # medidas
        self.pasos = 0
        self._medida = (time.perf_counter(), 0)
        self.hz_medida = 0.0
        self.t = 0.0  # s de simulación
        self.reiniciar()

    # --- montaje del mundo ----------------------------------------------------------------------------------------
    def _cuerpos_robot(self) -> list[int]:
        """Cuerpos del brazo con mallas visibles (los que la vista 3D mueve)."""
        ids = []
        for g in range(self.modelo.ngeom):
            b = int(self.modelo.geom_bodyid[g])
            if b and self.modelo.geom_type[g] == mujoco.mjtGeom.mjGEOM_MESH and self.modelo.geom_group[g] == 2 \
                    and b not in ids:
                ids.append(b)
        return ids

    def reiniciar(self, q_lr=None) -> None:
        """Brazo en reposo, base en `POSICION_BASE`, chapa tumbada en la zona libre y antorcha en su soporte."""
        from sim.entorno import REPOSO, lerobot_a_rad

        with self._cerrojo:
            mujoco.mj_resetData(self.modelo, self.datos)
            q = lerobot_a_rad(REPOSO if q_lr is None else q_lr)
            q[5] = PINZA_ABRIR
            self.datos.qpos[self.qadr] = q
            self.datos.ctrl[:6] = q
            self.objetivo = q.copy()
            self.base = c.Anclaje("base", c.POSICION_BASE.x, c.POSICION_BASE.y, c.POSICION_BASE.giro)
            self.chapa = Pieza("chapa", pose_tumbada(*CHAPA_POR_DEFECTO), "tumbada")
            self.antorcha = Pieza("antorcha", pose_antorcha_en_soporte(), "soporte")
            self.led = False
            self.t = 0.0
            mujoco.mj_forward(self.modelo, self.datos)
            self._sincronizar_mocap()

    # --- hilo de física ---------------------------------------------------------------------------------------------
    def iniciar(self) -> None:
        if self._hilo is not None and self._hilo.is_alive():
            return
        self._parar.clear()
        self._hilo = threading.Thread(target=self._bucle, name="fisica-mujoco", daemon=True)
        self._hilo.start()

    def parar(self) -> None:
        self._parar.set()
        if self._hilo is not None:
            self._hilo.join(timeout=2.0)
            self._hilo = None

    def _bucle(self) -> None:
        dt = self.modelo.opt.timestep * SUBPASOS
        siguiente = time.perf_counter()
        while not self._parar.is_set():
            self.avanzar(SUBPASOS)
            if not self.tiempo_real:
                continue
            siguiente += dt
            espera = siguiente - time.perf_counter()
            if espera > 0:
                time.sleep(espera)
            elif espera < -0.25:  # muy por detrás (máquina ocupada): no intentar recuperar todo de golpe
                siguiente = time.perf_counter()

    def avanzar(self, pasos: int = SUBPASOS) -> None:
        """Integra `pasos` pasos de física y aplica agarres, imanes y animaciones (lo llama el hilo o los tests)."""
        with self._cerrojo:
            rangos = self.modelo.actuator_ctrlrange[:6]
            self.datos.ctrl[:6] = np.clip(self.objetivo, rangos[:, 0], rangos[:, 1])
            mujoco.mj_step(self.modelo, self.datos, nstep=pasos)
            self.t += pasos * self.modelo.opt.timestep
            self.pasos += pasos
            self._reglas()
            self._sincronizar_mocap()
        ahora = time.perf_counter()
        t0, n0 = self._medida
        if ahora - t0 >= 1.0:
            self.hz_medida = (self.pasos - n0) / (ahora - t0)
            self._medida = (ahora, self.pasos)

    # --- reglas del mundo -----------------------------------------------------------------------------------------
    def pose_pinza(self) -> Pose:
        return Pose(self.datos.site_xpos[self.sitio_pinza] / MM, self.datos.site_xmat[self.sitio_pinza].reshape(3, 3))

    def pinza(self) -> float:
        return float(self.datos.qpos[self.qadr[5]])

    def punto_agarre(self, pieza: Pieza) -> np.ndarray:
        if pieza is self.chapa:
            return pieza.pose.aplicar(AGARRE_ALETA)
        return pieza.pose.aplicar([0.0, 0.0, -DIST_MANGO])

    def _reglas(self) -> None:
        pinza = self.pose_pinza()
        g = self.pinza()
        sujeta = [p for p in (self.chapa, self.antorcha) if p.estado == "agarrada"]
        if sujeta and g > PINZA_ABIERTA:
            for p in sujeta:
                self._soltar(p)
        elif not sujeta and g < PINZA_CERRADA:
            for p in (self.chapa, self.antorcha):
                if p.animacion is None and np.linalg.norm(self.punto_agarre(p) - pinza.p) < RADIO_AGARRE \
                        and not p.extra.get("descartada"):
                    p.estado, p.junta = "agarrada", None
                    p.agarre_rel = pinza.inversa().componer(p.pose)
                    break
            else:
                # Cerrar en el aire no coge nada aunque luego pase cerca (hay que volver a abrir).
                for p in (self.chapa, self.antorcha):
                    p.extra["descartada"] = True
        if g > PINZA_ABIERTA:
            for p in (self.chapa, self.antorcha):
                p.extra.pop("descartada", None)
        for p in (self.chapa, self.antorcha):
            if p.estado == "agarrada":
                p.pose = pinza.componer(p.agarre_rel)
            if p.animacion is not None:
                ini, fin, t0, dur, estado, junta = p.animacion
                s = min(1.0, (self.t - t0) / dur)
                s = s * s * (3 - 2 * s)
                p.pose = interpolar(ini, fin, s)
                if s >= 1.0:
                    p.animacion, p.estado, p.junta = None, estado, junta

    def _animar(self, p: Pieza, fin: Pose, estado: str, junta: str | None = None, dur: float = T_IMAN) -> None:
        p.estado = "encajando" if p is self.chapa else "suelta"
        p.animacion = (p.pose.copia(), fin, self.t, dur, estado, junta)

    def _soltar(self, p: Pieza) -> None:
        p.agarre_rel = None
        if p is self.antorcha:
            soporte = pose_antorcha_en_soporte()
            cerca = np.linalg.norm(p.pose.p - soporte.p) < TOL_SOPORTE_MM and p.pose.R[2, 2] < -0.8
            if cerca:
                self._animar(p, soporte, "soporte", dur=0.2)
            else:
                self._caer_antorcha(p)
            return
        for junta in c.TipoJunta:
            obj = pose_montada(junta, self.base)
            if np.linalg.norm(p.pose.p - obj.p) < TOL_IMAN_MM and angulo_entre(p.pose.R, obj.R) < TOL_IMAN_GRADOS:
                self._animar(p, obj, "montada", junta.value)
                return
        self._caer_chapa(p)

    def _sobre_base(self, x: float, y: float) -> bool:
        b = pose_base(self.base)
        loc = b.R.T @ (np.array([x, y, b.p[2]]) - b.p)
        return abs(loc[0]) < c.LARGO_BASE / 2 + 10 and abs(loc[1]) < c.ANCHO_BASE / 2 + 10

    def _caer_chapa(self, p: Pieza) -> None:
        """La chapa cae tumbada (con la aleta hacia donde quede más cerca de arriba) en la vertical de su centro."""
        centro = p.pose.aplicar([0.0, c.ALTO_MOVIL / 2, 0.0])
        eje = p.pose.R[:, 0]
        giro = math.degrees(math.atan2(eje[1], eje[0])) - 90.0
        encima = self._sobre_base(centro[0], centro[1])
        fin = pose_tumbada(centro[0], centro[1], giro, c.GROSOR_CHAPA if encima else 0.0)
        if p.pose.R[2, 2] < 0:  # cae con la aleta abajo: se queda boca abajo (y ya no se puede coger)
            fin = Pose(fin.p + np.array([0, 0, c.ALETA["alto"]]), fin.R @ np.diag([1.0, -1.0, -1.0]))
        self._animar(p, fin, "encima" if encima else "tumbada", dur=0.3)

    def _caer_antorcha(self, p: Pieza) -> None:
        punta = p.pose.p
        eje = p.pose.R[:, 2]
        horizontal = np.array([eje[0], eje[1], 0.0])
        horizontal = horizontal / np.linalg.norm(horizontal) if np.linalg.norm(horizontal) > 1e-6 else \
            np.array([1.0, 0.0, 0.0])
        z = horizontal
        x = np.array([0.0, 0.0, 1.0])
        R = np.column_stack([x, np.cross(z, x), z])
        self._animar(p, Pose(np.array([punta[0], punta[1], 7.0]), R), "suelta", dur=0.3)

    def _sincronizar_mocap(self) -> None:
        for nombre, pose in (("base", pose_base(self.base)), ("movil", self.chapa.pose),
                             ("antorcha", self.antorcha.pose), ("soporte", pose_soporte())):
            i = self.mocap[nombre]
            self.datos.mocap_pos[i] = pose.p * MM
            self.datos.mocap_quat[i] = pose.quat()

    # --- órdenes del controlador y del juez ----------------------------------------------------------------------
    def mandar(self, q_rad) -> None:
        """Posiciones objetivo de las 6 articulaciones (rad del modelo)."""
        with self._cerrojo:
            self.objetivo = np.array(q_rad, dtype=float).copy()

    def q(self) -> np.ndarray:
        with self._cerrojo:
            return self.datos.qpos[self.qadr].copy()

    def poner_led(self, encendido: bool) -> None:
        self.led = bool(encendido)

    def mover_base(self, x: float, y: float, giro: float) -> None:
        """Perturbación: el juez mueve o gira la base (la chapa montada, si la hay, va con ella)."""
        with self._cerrojo:
            if self.chapa.estado == "agarrada":
                return
            antes = pose_base(self.base)
            self.base = c.Anclaje("base", float(x), float(y), (float(giro) + 180.0) % 360.0 - 180.0)
            despues = pose_base(self.base)
            if self.chapa.estado in ("montada", "encima", "encajando"):
                self.chapa.animacion = None
                if self.chapa.estado == "encajando":
                    self.chapa.estado = "montada"
                rel = antes.inversa().componer(self.chapa.pose)
                self.chapa.pose = despues.componer(rel)
            self._sincronizar_mocap()

    def soltar_chapa_en(self, x: float, y: float, giro: float) -> bool:
        """Perturbación: el juez deja la chapa tumbada en otro sitio (la quita de la base si estaba montada)."""
        with self._cerrojo:
            if self.chapa.estado == "agarrada":
                return False
            self.chapa = Pieza("chapa", pose_tumbada(x, y, giro, c.GROSOR_CHAPA if self._sobre_base(x, y) else 0.0),
                               "encima" if self._sobre_base(x, y) else "tumbada")
            self._sincronizar_mocap()
            return True

    def montar_a_mano(self, junta) -> None:
        """Plan B / pruebas: la chapa aparece montada en la junta (como si la montara el alumno)."""
        with self._cerrojo:
            self.chapa = Pieza("chapa", pose_montada(junta, self.base), "montada", c.TipoJunta(junta).value)
            self._sincronizar_mocap()

    # --- lo que se ve -----------------------------------------------------------------------------------------
    def junta_montada(self) -> str | None:
        """Verdad de la simulación: "t", "esquina", "incompleta" (chapa encima de la base sin cerrar) o None."""
        if self.chapa.estado == "montada":
            return self.chapa.junta
        if self.chapa.estado == "encima":
            return "incompleta"
        return None

    def punta_antorcha(self) -> Pose | None:
        """Pose de la antorcha del robot (origen en la punta) si la lleva en la pinza."""
        with self._cerrojo:
            return self.antorcha.pose.copia() if self.antorcha.estado == "agarrada" else None

    def marco_cordon(self, junta=None) -> tuple[np.ndarray, np.ndarray] | None:
        junta = junta or self.junta_montada()
        if junta not in ("t", "esquina"):
            return None
        return marco_cordon(junta, self.base)

    def instantanea(self) -> dict:
        """Todo lo que la vista 3D necesita para pintar este instante (JSON, mm y cuaterniones [w, x, y, z])."""
        with self._cerrojo:
            d = self.datos
            cuerpos = [[round(v, 2) for v in (d.xpos[b] / MM)] + [round(v, 5) for v in d.xquat[b]]
                       for b in self.cuerpos_robot]

            def pieza(p: Pieza) -> dict:
                return {"p": [round(v, 2) for v in p.pose.p], "q": [round(v, 5) for v in p.pose.quat()],
                        "estado": p.estado, "junta": p.junta}

            return {
                "t": round(self.t, 3), "q": [round(float(v), 4) for v in d.qpos[self.qadr]],
                "cuerpos": cuerpos,
                "base": {"x": self.base.x, "y": self.base.y, "giro": self.base.giro},
                "chapa": pieza(self.chapa), "antorcha": pieza(self.antorcha), "led": self.led,
                "junta": self.junta_montada(), "hz_fisica": round(self.hz_medida, 1),
            }

    def mallas(self) -> tuple[dict, bytes]:
        """Índice JSON y blob binario (float32 vértices en mm + uint32 caras) de las mallas que pinta la vista 3D:
        las visuales del SO-101 (en el marco de su cuerpo) y las piezas del CAD (en el marco de su pieza)."""
        m = self.modelo
        trozos: list[bytes] = []
        desplazamiento = 0
        indice = {"robot": [], "piezas": {}, "cuerpos": [m.body(b).name for b in self.cuerpos_robot]}

        def anadir(v_mm: np.ndarray, f: np.ndarray) -> dict:
            nonlocal desplazamiento
            bv = np.ascontiguousarray(v_mm, dtype="<f4").tobytes()
            bf = np.ascontiguousarray(f, dtype="<u4").tobytes()
            entrada = {"v": [desplazamiento, len(v_mm)], "f": [desplazamiento + len(bv), len(f)]}
            trozos.extend([bv, bf])
            desplazamiento += len(bv) + len(bf)
            return entrada

        for g in range(m.ngeom):
            b = int(m.geom_bodyid[g])
            if b not in self.cuerpos_robot or m.geom_type[g] != mujoco.mjtGeom.mjGEOM_MESH or m.geom_group[g] != 2:
                continue
            k = int(m.geom_dataid[g])
            va, nv = int(m.mesh_vertadr[k]), int(m.mesh_vertnum[k])
            fa, nf = int(m.mesh_faceadr[k]), int(m.mesh_facenum[k])
            R = np.zeros(9)
            mujoco.mju_quat2Mat(R, m.geom_quat[g])
            v = (m.mesh_vert[va:va + nv] @ R.reshape(3, 3).T + m.geom_pos[g]) / MM
            matid = int(m.geom_matid[g])
            rgba = (m.mat_rgba[matid] if matid >= 0 else m.geom_rgba[g]).tolist()
            entrada = anadir(v, m.mesh_face[fa:fa + nf])
            entrada.update(cuerpo=self.cuerpos_robot.index(b), rgba=[round(x, 3) for x in rgba])
            indice["robot"].append(entrada)
        for nombre in MALLAS_CAD:
            v, f = malla_cad(nombre)
            indice["piezas"][nombre] = anadir(v, f)
        return indice, b"".join(trozos)
