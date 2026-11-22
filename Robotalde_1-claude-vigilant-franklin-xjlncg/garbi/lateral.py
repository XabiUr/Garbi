"""Posturas de Garbi con el montaje lateral (propuesta del usuario, 20-11).

Montaje:
- La boquilla rígida (Ø30 × 40) es el final del tubo corrugado y va por el costado derecho de la pinza.
- La cámara oficial va en su soporte, a la izquierda.
- La muñeca no gira (`wrist_roll` = 0), para que el tubo, que baja por el costado del brazo, no se retuerza.
- La mordaza móvil va cerrada.

Quedan 4 articulaciones (pan, lift, elbow, flex), que fijan dónde está la boca (3) y cuánto se inclina (1); hacia dónde
mira en planta sale de ellas. Las posturas se resuelven como un sistema de 4 ecuaciones con mínimos cuadrados
amortiguados y diferencias finitas, probando varias semillas. Para cada punto se elige la inclinación más cómoda que
admite entre 10° y 25° (casi horizontal, un poco picada): eso solo es posible a partir de ~280 mm del robot.

Posturas (mm, marco de la mesa):
- `acompanar(P)`: la broca (punta P) queda `DISTANCIA_BROCA` por delante de la boca, en la dirección en que mira, con
  la boca a `ALTURA_BOCA` sobre la cara de la tabla.
- `preapunto(P)`: lo mismo, pero `ATRAS_PREAPUNTO` más separada: desde ahí la cámara mira la broca antes de entrar.
- `apartado(P)`: `ATRAS_APARTADO` más separada, para dejar sitio si mueves el taladro.
- `limpiar(punto)`: el eje de la boca corta la superficie en `punto`.
- `barrido(centro, radio)`: posturas de una pasada en zigzag de limpieza.
"""
from __future__ import annotations

import mujoco
import numpy as np

from garbi import contrato as g
from sim.entorno import lerobot_a_rad, rad_a_lerobot

MM = 1e-3
ARTICULACIONES_4 = ("shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex")
DISTANCIA_BROCA = 30.0  # mm, en planta, de la boca al eje de la broca
ALTURA_BOCA = 15.0  # mm del centro de la boca sobre la superficie
RADIO_TALADRO_MIN, RADIO_TALADRO_MAX = 280.0, 460.0  # mm del eje del robot donde acompaña con la boca a 10-25°
# Preapunto y apartado: a la misma altura que acompañar pero más separados de la broca. Subir junto al taladro acerca
# la boca al portabrocas, que es más ancho que la broca (holgura negativa en la simulación).
ATRAS_PREAPUNTO = 30.0
ATRAS_APARTADO = 55.0
INCLINACIONES = (15.0, 20.0, 10.0, 25.0)  # la boca ataca casi en horizontal, un poco picada (decisión del usuario)
APARCADO = np.array([0.0, -100.0, 60.0, -60.0, 0.0, 0.0])  # recogido y alto, muñeca en 0 y pinza cerrada
PINZA_CERRADA = 0.0


def cuaternio_eje(eje=None) -> np.ndarray:
    """Cuaternio (w, x, y, z) del giro mínimo que lleva la vertical a `eje` (inclinar sin girar en planta)."""
    if eje is None:
        return np.array([1.0, 0.0, 0.0, 0.0])
    e = np.asarray(eje, float)
    e = e / np.linalg.norm(e)
    eje_giro = np.cross([0.0, 0.0, 1.0], e)
    s = np.linalg.norm(eje_giro)
    if s < 1e-9:
        return np.array([1.0, 0.0, 0.0, 0.0])
    a = np.arctan2(s, e[2]) / 2
    return np.array([np.cos(a), *(np.sin(a) * eje_giro / s)])


class ControlLateral:
    def __init__(self, mundo):
        self.m = mundo
        M = mundo.modelo
        self.M = M
        self.d = mujoco.MjData(M)
        self.qadr = [M.jnt_qposadr[M.joint(n).id] for n in ARTICULACIONES_4 + ("wrist_roll", "gripper")]
        rangos = np.array([M.jnt_range[M.joint(n).id] for n in ARTICULACIONES_4])
        self.lo, self.hi = rangos[:, 0], rangos[:, 1]
        self.sitio = M.site("boca").id
        rng = np.random.default_rng(0)
        self.semillas = [np.array([0.0, -0.3, 0.8, 0.9])] + [rng.uniform(self.lo, self.hi) for _ in range(30)]
        cuerpo = M.body("taladro").id
        self._g_taladro = [i for i in range(M.ngeom) if M.geom_bodyid[i] == cuerpo]
        from sim import escena as base

        self._g_brazo = [i for i in range(M.ngeom)
                         if (M.geom_contype[i], M.geom_conaffinity[i]) == tuple(base._BRAZO)]
        self._mocap_taladro = M.body_mocapid[cuerpo]

    # --- cinemática ------------------------------------------------------------------------------------------
    def _poner(self, q4):
        self.d.qpos[self.qadr] = list(q4) + [0.0, lerobot_a_rad(np.array([0, 0, 0, 0, 0, PINZA_CERRADA]))[5]]
        mujoco.mj_kinematics(self.M, self.d)

    def boca(self, q4) -> tuple[np.ndarray, np.ndarray]:
        """(centro de la boca en mm, dirección en la que mira) para las 4 articulaciones (rad)."""
        self._poner(q4)
        return self.d.site_xpos[self.sitio] / MM, self.d.site_xmat[self.sitio].reshape(3, 3)[:, 2].copy()

    @staticmethod
    def inclinacion(eje) -> float:
        return float(np.degrees(np.arcsin(-eje[2])))

    def _resolver(self, residuo, q0, iteraciones=120) -> tuple[np.ndarray, float]:
        q = np.asarray(q0, float).copy()
        for _ in range(iteraciones):
            r = residuo(q)
            if np.linalg.norm(r) < 0.3:
                break
            J = np.zeros((4, 4))
            for j in range(4):
                dq = np.zeros(4)
                dq[j] = 1e-4
                J[:, j] = (residuo(q + dq) - r) / 1e-4
            paso = -J.T @ np.linalg.solve(J @ J.T + 1e-2 * np.eye(4), r)
            q = np.clip(q + np.clip(paso, -0.15, 0.15), self.lo, self.hi)
        return q, float(np.linalg.norm(residuo(q)))

    def _postura(self, residuo_para) -> tuple[np.ndarray, float] | None:
        """Prueba las inclinaciones en orden de preferencia; devuelve (q4 en rad, inclinación) o None."""
        for inc in INCLINACIONES:
            residuo = residuo_para(inc)
            mejor = None
            for q0 in self.semillas:
                q, err = self._resolver(residuo, q0)
                if mejor is None or err < mejor[1]:
                    mejor = (q, err)
                if err < 0.8:
                    break
            if mejor[1] < 0.8:
                return mejor[0], inc
        return None

    def a_lerobot(self, q4) -> np.ndarray:
        q = rad_a_lerobot(np.concatenate([q4, [0.0, 0.0]]))
        q[4], q[5] = 0.0, PINZA_CERRADA
        return q

    # --- posturas --------------------------------------------------------------------------------------------
    def _junto_a(self, P, distancia, altura, atras=0.0, subida=0.0):
        """Residuo: la boca a `distancia` en planta de P (por detrás, según mira), a `altura` sobre P."""
        P = np.asarray(P, float)

        def para(inc):
            def residuo(q):
                b, e = self.boca(q)
                planta = np.array([e[0], e[1]]) / (np.hypot(e[0], e[1]) or 1.0)
                objetivo = P[:2] - planta * (distancia + atras)
                return np.array([b[0] - objetivo[0], b[1] - objetivo[1], b[2] - (P[2] + altura + subida),
                                 30.0 * (np.radians(self.inclinacion(e)) - np.radians(inc))])
            return residuo
        return para

    def acompanar(self, P):
        return self._postura(self._junto_a(P, DISTANCIA_BROCA, ALTURA_BOCA))

    def preapunto(self, P):
        return self._postura(self._junto_a(P, DISTANCIA_BROCA, ALTURA_BOCA, atras=ATRAS_PREAPUNTO))

    def apartado(self, P):
        return self._postura(self._junto_a(P, DISTANCIA_BROCA, ALTURA_BOCA, atras=ATRAS_APARTADO))

    def limpiar(self, punto):
        """El eje de la boca corta la superficie en `punto`, con la boca a `ALTURA_BOCA` sobre ella."""
        punto = np.asarray(punto, float)

        def para(inc):
            delante = ALTURA_BOCA / np.tan(np.radians(inc))
            return self._junto_a(punto, delante, ALTURA_BOCA)(inc)
        return self._postura(para)

    def barrido(self, centro, radio=25.0, paso=15.0, z=None):
        """Puntos de una pasada en zigzag alrededor de `centro` (x, y) y la postura de limpieza de cada uno."""
        z = g.ALTURA_CARA_TABLA if z is None else z
        puntos = []
        for i, dy in enumerate(np.arange(-radio, radio + 0.1, paso)):
            dx = np.sqrt(max(radio ** 2 - dy ** 2, 0.0))
            fila = [(centro[0] - dx, centro[1] + dy), (centro[0] + dx, centro[1] + dy)]
            puntos += fila if i % 2 == 0 else fila[::-1]
        out = []
        for x, y in puntos:
            r = self.limpiar(np.array([x, y, z]))
            if r is not None:
                out.append((np.array([x, y, z]), r))
        return out

    # --- comprobaciones --------------------------------------------------------------------------------------
    def ve(self, q4, punto_mm, geoms_objetivo=()) -> bool:
        """¿La cámara de la muñeca ve `punto_mm` (dentro de la imagen y sin nada delante)?"""
        self._poner(q4)
        mujoco.mj_camlight(self.M, self.d)
        cam = self.M.camera("wrist").id
        c = self.d.cam_xpos[cam]
        Rc = self.d.cam_xmat[cam].reshape(3, 3)
        v = np.asarray(punto_mm, float) * MM - c
        pc = Rc.T @ v
        if pc[2] >= 0:
            return False
        f = 0.5 / np.tan(np.radians(self.M.cam_fovy[cam]) / 2)  # en fracción del alto de la imagen (4:3)
        if abs(pc[0] / -pc[2]) * f > 0.5 * 4 / 3 or abs(pc[1] / -pc[2]) * f > 0.5:
            return False
        gid = np.array([-1], dtype=np.int32)
        dist = mujoco.mj_ray(self.M, self.d, c, v / np.linalg.norm(v), None, 1, self.M.body("wrist_camera").id, gid)
        return dist < 0 or dist >= np.linalg.norm(v) - 0.006 or gid[0] in geoms_objetivo

    def holgura(self, q4, P, eje=None) -> float:
        """mm entre el brazo (con la boquilla) y el taladro con la punta en P. `eje`: dirección de la broca de la punta
        hacia arriba (por defecto, vertical); el taladro se inclina sin girar en planta, como `MundoGarbi.poner_taladro`."""
        self.d.mocap_pos[self._mocap_taladro] = np.asarray(P, float) * MM
        self.d.mocap_quat[self._mocap_taladro] = cuaternio_eje(eje)
        self._poner(q4)
        ft = np.zeros(6)
        return min(mujoco.mj_geomDistance(self.M, self.d, a, b, 0.2, ft)
                   for a in self._g_brazo for b in self._g_taladro) / MM
