"""Calibración del robot respecto a la mesa con el anillo verde de la boquilla (especificación técnica, M2 paso 3).

El robot lleva la boca a 9 posturas conocidas sobre el tapete; en cada una, la cámara de arriba (ya calibrada con las
esquinas del tapete, ver `garbi.percepcion`) detecta el anillo verde. Con la cinemática directa del brazo se sabe dónde
está el anillo en el marco de la base del robot; el rayo de la cámara cortado con el plano de esa altura dice dónde
está en la mesa. El ajuste rígido en el plano (x, y, giro) de la base sale por mínimos cuadrados. Se comprueba con 5
posturas nuevas: error < 4 mm.

Funciona igual en la simulación que con el robot real: solo necesita una función que lleve el robot a una postura y
devuelva la imagen de arriba. Nada se lee de la verdad de la simulación.

Unidades: mm y grados; posturas en grados de LeRobot (pan, lift, elbow, flex, roll, pinza).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import cv2
import mujoco
import numpy as np

MM = 1e-3
ERROR_MAXIMO = 4.0  # mm en las posturas de comprobación

# Posturas conocidas (grados de LeRobot). Se sacaron con la cinemática inversa del montaje lateral (`garbi.lateral`):
# la boca a 60 mm sobre la mesa en una rejilla de 3 × 3 de la zona de trabajo (y 5 puntos intermedios para comprobar),
# con el anillo a la vista de la cámara de arriba.
POSTURAS_CALIBRACION = np.array([
    [8.9, -21.6, 82.4, -46.0, 0.0, 0.0],  # boca en (270, -110, 60)
    [-16.1, -45.0, 94.8, -35.0, 0.0, 0.0],  # (270, 0, 60)
    [-38.3, -21.6, 82.4, -46.0, 0.0, 0.0],  # (270, 110, 60)
    [6.6, 13.7, 38.1, -37.1, 0.0, 0.0],  # (360, -110, 60)
    [-11.8, 7.7, 47.6, -40.5, 0.0, 0.0],  # (360, 0, 60)
    [-29.0, 13.7, 38.1, -37.0, 0.0, 0.0],  # (360, 110, 60)
    [5.3, 50.0, -25.6, -9.6, 0.0, 0.0],  # (450, -110, 60)
    [-9.3, 42.5, -11.9, -15.8, 0.0, 0.0],  # (450, 0, 60)
    [-23.3, 50.1, -25.8, -9.5, 0.0, 0.0],  # (450, 110, 60)
])
POSTURAS_COMPROBACION = np.array([
    [-2.9, -7.6, 68.6, -46.2, 0.0, 0.0],  # (315, -55, 60)
    [-23.8, -7.6, 68.6, -46.2, 0.0, 0.0],  # (315, 55, 60)
    [-2.2, 25.2, 18.9, -29.3, 0.0, 0.0],  # (405, -55, 60)
    [-18.4, 25.2, 18.9, -29.3, 0.0, 0.0],  # (405, 55, 60)
    [14.4, 20.3, 27.2, -32.8, 0.0, 0.0],  # (360, -160, 60)
])

# Anillo verde lima (HSV de OpenCV, H 0-179): lejos del amarillo del robot (~27) y del verde oscuro del taladro (~77)
VERDE_BAJO, VERDE_ALTO = (40, 80, 25), (66, 255, 255)
AREA_ANILLO_MIN = 25  # px a 640 × 480


@dataclass
class PoseBase:
    """Dónde está la base del robot en la mesa: p_mesa = Rz(giro) · p_robot + (x, y)."""
    x: float = 0.0
    y: float = 0.0
    giro: float = 0.0  # grados

    def rotacion(self) -> np.ndarray:
        a = np.radians(self.giro)
        c, s = np.cos(a), np.sin(a)
        return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])

    def a_mesa(self, p_robot) -> np.ndarray:
        p = np.asarray(p_robot, float)
        return p @ self.rotacion().T + np.array([self.x, self.y, 0.0])

    def a_robot(self, p_mesa) -> np.ndarray:
        p = np.asarray(p_mesa, float)
        return (p - np.array([self.x, self.y, 0.0])) @ self.rotacion()


class CinematicaRobot:
    """Cinemática directa del SO-101 con el montaje de Garbi, a partir del modelo MuJoCo (sin tocar su estado).

    Da la posición de un sitio (el anillo, la boca) y la pose de la cámara de la muñeca para una postura, en el marco
    de la base del robot o, con `base`, en el de la mesa."""

    def __init__(self, modelo: mujoco.MjModel, base: PoseBase | None = None):
        from sim.cinematica import ARTICULACIONES

        self.modelo = modelo
        self.datos = mujoco.MjData(modelo)
        self.qadr = np.array([modelo.jnt_qposadr[modelo.joint(n).id] for n in ARTICULACIONES])
        self.base = base or PoseBase()

    def _poner(self, q_lerobot) -> None:
        from sim.entorno import lerobot_a_rad

        self.datos.qpos[self.qadr] = lerobot_a_rad(np.asarray(q_lerobot, float))
        mujoco.mj_kinematics(self.modelo, self.datos)
        mujoco.mj_camlight(self.modelo, self.datos)

    def sitio_robot(self, q_lerobot, nombre: str = "anillo") -> np.ndarray:
        self._poner(q_lerobot)
        return self.datos.site_xpos[self.modelo.site(nombre).id] / MM

    def eje_boca_robot(self, q_lerobot) -> np.ndarray:
        """Dirección en la que mira la boca (marco del robot)."""
        self._poner(q_lerobot)
        return self.datos.site_xmat[self.modelo.site("boca").id].reshape(3, 3)[:, 2].copy()

    def sitio(self, q_lerobot, nombre: str = "anillo") -> np.ndarray:
        """Sitio en la mesa (mm)."""
        return self.base.a_mesa(self.sitio_robot(q_lerobot, nombre))

    def pose_camara(self, q_lerobot, nombre: str = "wrist") -> tuple[np.ndarray, np.ndarray]:
        """(R, t) de la cámara en la mesa con el convenio de OpenCV: p_cam = R · p_mesa + t (mm)."""
        self._poner(q_lerobot)
        cid = self.modelo.camera(nombre).id
        Rw = (self.datos.cam_xmat[cid].reshape(3, 3) @ np.diag([1.0, -1.0, -1.0])).T  # robot → cámara
        cw = self.datos.cam_xpos[cid] / MM
        Rb = self.base.rotacion()
        R = Rw @ Rb.T
        centro = self.base.a_mesa(cw)
        return R, -R @ centro


def detectar_anillo(img_rgb, roi: np.ndarray | None = None) -> np.ndarray | None:
    """Centro (u, v) del anillo verde en la imagen de arriba, o None. El centro de la silueta de un cilindro corto es
    la proyección de su centro. `roi`: máscara uint8 donde buscar (opcional)."""
    hsv = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2HSV)
    verde = cv2.inRange(hsv, VERDE_BAJO, VERDE_ALTO)
    if roi is not None:
        verde &= roi
    verde = cv2.morphologyEx(verde, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    n, etiquetas, stats, centros = cv2.connectedComponentsWithStats(verde)
    if n <= 1:
        return None
    k = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    if stats[k, cv2.CC_STAT_AREA] < AREA_ANILLO_MIN:
        return None
    return centros[k].astype(float)


def ajuste_rigido_2d(locales: np.ndarray, mesa: np.ndarray) -> tuple[np.ndarray, float]:
    """Traslación y giro (grados) que mejor llevan `locales` a `mesa` (mínimos cuadrados, Kabsch en el plano)."""
    locales, mesa = np.asarray(locales, float), np.asarray(mesa, float)
    ml, mm = locales.mean(axis=0), mesa.mean(axis=0)
    a, b = locales - ml, mesa - mm
    giro = np.arctan2((a[:, 0] * b[:, 1] - a[:, 1] * b[:, 0]).sum(), (a * b).sum())
    c, s = np.cos(giro), np.sin(giro)
    t = mm - np.array([[c, -s], [s, c]]) @ ml
    return t, float(np.degrees(giro))


def _muestras_anillo(n_ang: int = 48, n_largo: int = 4):
    """Puntos (marco del anillo: z a lo largo del eje de la boca, origen en el centro del anillo) y normales de la
    superficie del anillo que puede ver la cámara: la banda exterior y la cara de la punta."""
    from garbi.escena import ANILLO_DIAMETRO, ANILLO_LARGO

    r, h = ANILLO_DIAMETRO / 2, ANILLO_LARGO / 2
    ang = np.linspace(0, 2 * np.pi, n_ang, endpoint=False)
    pts, nor = [], []
    for z in np.linspace(-h + h / n_largo, h - h / n_largo, n_largo):
        pts.append(np.column_stack([r * np.cos(ang), r * np.sin(ang), np.full(n_ang, z)]))
        nor.append(np.column_stack([np.cos(ang), np.sin(ang), np.zeros(n_ang)]))
    # cara de la punta (anillo plano de r_boquilla a r; dentro, la boca abierta no es verde)
    from garbi.escena import BOQUILLA_DIAMETRO

    for rr in np.linspace(BOQUILLA_DIAMETRO / 2, r, 3)[1:]:
        pts.append(np.column_stack([rr * np.cos(ang), rr * np.sin(ang), np.full(n_ang, h)]))
        nor.append(np.tile([0.0, 0.0, 1.0], (n_ang, 1)))
    return np.vstack(pts), np.vstack(nor)


def _corta_cilindro(origen, destino, a, b, radio) -> np.ndarray:
    """¿El segmento origen[i] → destino corta el cilindro de eje a → b y ese radio? (vectorizado en origen)."""
    eje = (b - a) / np.linalg.norm(b - a)
    largo = np.linalg.norm(b - a)
    d = destino[None, :] - origen
    w = origen - a[None, :]
    d_p = d - (d @ eje)[:, None] * eje[None, :]
    w_p = w - (w @ eje)[:, None] * eje[None, :]
    A = np.sum(d_p * d_p, axis=1)
    B = 2 * np.sum(d_p * w_p, axis=1)
    Cc = np.sum(w_p * w_p, axis=1) - radio ** 2
    disc = B * B - 4 * A * Cc
    corta = np.zeros(len(origen), bool)
    ok = (disc > 0) & (A > 1e-12)
    for signo in (-1.0, 1.0):
        s = np.where(ok, (-B + signo * np.sqrt(np.maximum(disc, 0))) / (2 * np.where(A > 1e-12, A, 1.0)), -1.0)
        z = np.sum((w + s[:, None] * d) * eje[None, :], axis=1)
        corta |= ok & (s > 1e-3) & (s < 1.0) & (z >= 0) & (z <= largo)
    return corta


def desvio_anillo(cam, centro_mesa: np.ndarray, eje_mesa: np.ndarray) -> np.ndarray:
    """Cuánto se aparta (px) el centro de la mancha verde que ve la cámara de la proyección del centro del anillo: solo
    se ve la parte del anillo de cara a la cámara y no tapada por la boquilla (que sigue por detrás del anillo)."""
    from garbi.escena import ANILLO_LARGO, BOQUILLA_DIAMETRO, BOQUILLA_LARGO

    e = np.asarray(eje_mesa, float) / np.linalg.norm(eje_mesa)
    x = np.cross(e, [0.0, 0.0, 1.0])
    x = x / np.linalg.norm(x) if np.linalg.norm(x) > 1e-6 else np.array([1.0, 0.0, 0.0])
    y = np.cross(e, x)
    Rm = np.column_stack([x, y, e])
    pl, nl = _muestras_anillo()
    pts = centro_mesa[None, :] + pl @ Rm.T
    nor = nl @ Rm.T
    C = cam.centro
    hacia = C[None, :] - pts
    de_cara = np.sum(nor * hacia, axis=1) > 0
    boca = centro_mesa + e * ANILLO_LARGO / 2
    atras = boca - e * BOQUILLA_LARGO
    # la boquilla (algo más estrecha) solo tapa por detrás del anillo: se toma hasta el anillo
    tapado = _corta_cilindro(pts, C, atras, boca - e * ANILLO_LARGO, BOQUILLA_DIAMETRO / 2)
    vis = de_cara & ~tapado
    if not np.any(vis):
        return np.zeros(2)
    peso = np.sum(nor[vis] * hacia[vis], axis=1) / np.linalg.norm(hacia[vis], axis=1)  # escorzo
    uv = cam.proyectar(pts[vis])
    centro_visto = (uv * peso[:, None]).sum(axis=0) / peso.sum()
    return centro_visto - cam.proyectar(centro_mesa)[0]


def ajustar_base(p_robot: np.ndarray, uv: np.ndarray, cam, ejes: np.ndarray | None = None, iteraciones: int = 4
                 ) -> tuple[PoseBase, np.ndarray]:
    """Pose de la base a partir del centro del anillo en el marco del robot (Nx3, cinemática) y la mancha verde en la
    imagen de arriba (Nx2).

    Cada píxel se lleva a la mesa cortando su rayo con el plano a la altura del anillo (la base está apoyada en la
    mesa: z y la inclinación no cambian) y se hace un ajuste rígido en el plano. La cámara no ve el anillo entero (la
    propia boquilla tapa una parte): con `ejes` (Nx3, eje de la boca en el marco del robot) se corrige el centro visto
    con el modelo del anillo (`desvio_anillo`) y se repite. Devuelve (pose, residuo de cada punto en mm)."""
    p_robot = np.asarray(p_robot, float)
    uv = np.asarray(uv, float)
    corregido = uv.copy()
    base = None
    for it in range(iteraciones if ejes is not None else 1):
        if base is not None:
            R = base.rotacion()
            corregido = np.array([uv[i] - desvio_anillo(cam, base.a_mesa(p_robot[i]), R @ ejes[i])
                                  for i in range(len(uv))])
        en_mesa = np.array([cam.a_plano(corregido[i], p_robot[i, 2])[0] for i in range(len(uv))])
        t, giro = ajuste_rigido_2d(p_robot[:, :2], en_mesa)
        base = PoseBase(float(t[0]), float(t[1]), giro)
    residuos = np.linalg.norm(base.a_mesa(p_robot)[:, :2] - en_mesa, axis=1)
    return base, residuos


@dataclass
class ResultadoCalibracion:
    base: PoseBase
    residuos: np.ndarray  # mm, en las posturas de calibración
    errores: np.ndarray = field(default_factory=lambda: np.zeros(0))  # mm, en las de comprobación
    vistas: int = 0  # posturas en las que se vio el anillo

    @property
    def ok(self) -> bool:
        return self.vistas >= 4 and (len(self.errores) == 0 or float(np.max(self.errores)) < ERROR_MAXIMO)


def calibrar_robot(ir_y_mirar: Callable[[np.ndarray], np.ndarray], cam, cin: CinematicaRobot,
                   posturas=POSTURAS_CALIBRACION, comprobacion=POSTURAS_COMPROBACION) -> ResultadoCalibracion | None:
    """Calibración completa. `ir_y_mirar(q)` lleva el robot a la postura q (grados de LeRobot), espera a que pare y
    devuelve la imagen RGB de la cámara de arriba. `cam`: la cámara de arriba calibrada (`percepcion.CamaraMesa`).

    El error de comprobación es la distancia en la mesa entre donde la cámara ve el anillo y donde lo pone la
    cinemática con la base calibrada."""
    p_robot, ejes, uvs = [], [], []
    for q in posturas:
        uv = detectar_anillo(ir_y_mirar(q))
        if uv is not None:
            p_robot.append(cin.sitio_robot(q, "anillo"))
            ejes.append(cin.eje_boca_robot(q))
            uvs.append(uv)
    if len(uvs) < 4:
        return None
    base, residuos = ajustar_base(np.array(p_robot), np.array(uvs), cam, np.array(ejes))
    errores = []
    for q in comprobacion:
        uv = detectar_anillo(ir_y_mirar(q))
        if uv is None:
            errores.append(np.inf)
            continue
        p = base.a_mesa(cin.sitio_robot(q, "anillo"))
        uv = uv - desvio_anillo(cam, p, base.rotacion() @ cin.eje_boca_robot(q))
        errores.append(float(np.linalg.norm(cam.a_plano(uv, p[2])[0] - p[:2])))
    cin.base = base
    return ResultadoCalibracion(base, residuos, np.array(errores), len(uvs))
