"""Control programado de la boquilla: cinemática inversa, trayectorias con velocidad limitada y gestos.

La boquilla va atornillada a la pinza y trabaja siempre inclinada `INCLINACION_BOCA` (30°) bajo la horizontal,
llegando en planta de lado (`GIRO_LLEGADA`), por la izquierda (`lado=+1`) o por la derecha
(`lado=-1`) del punto de trabajo. Es la familia de posturas que el SO-101 alcanza en toda la zona
(ver .plans/aspira/montaje-boquilla.md).

Gestos (cada uno es un plan de posturas articulares que se ejecuta fotograma a fotograma):
- `aparcar`: sube la boca y vuelve a la postura de aparcado por el espacio articular.
- `ir_a`: lleva la boca a un punto con una dirección, bajando en vertical los últimos `RETIRADA` mm.
- `acercarse_al_taladro`: deja la boca en el preapunto (algo más alta y atrás que al acompañar), desde donde la
  cámara del robot ve la broca, sin pasar cerca del taladro; `afinar` la lleva a `DISTANCIA_ACOMPANAR` de la punta
  corregida.
- `zigzag`: pasada de limpieza sobre una zona circular (la línea base programada).
- `limpiar_tabla`: recorrido en zigzag sobre toda la tabla.

Todas las posiciones en mm, marco de la mesa.
"""
from __future__ import annotations

import mujoco
import numpy as np

from garbi import contrato as g
from garbi.mundo import APARCADO
from sim.cinematica import ARTICULACIONES, Cinematica
from sim.entorno import lerobot_a_rad, rad_a_lerobot

MM = 1e-3
PESO_GIRO = 0.05  # m por radián: la dirección de la boca pesa como 5 cm de posición
RETIRADA = 30.0  # mm que la boca sube antes de desplazarse y desde los que baja al llegar
HOLGURA_MIN = 12.0  # mm mínimos entre el brazo y el taladro en todo el acercamiento
ESPERAS = (40.0, 70.0, 100.0)  # mm, en planta, del punto de espera al preapunto (contra la dirección de la boca)
DURACION_ARTICULAR = 1.2  # s de los movimientos por el espacio articular
# Posturas de arranque de la IK para cada lado (convergen en toda la zona: acompañar, preapunto y limpieza)
SEMILLA = {
    1: np.array([30.9, -18.8, 23.3, 49.2, -30.4, 30.0]),
    -1: np.array([-31.1, -18.8, 23.3, 49.2, 35.8, 30.0]),
}


def _rotz(grados: float) -> np.ndarray:
    a = np.radians(grados)
    c, s = np.cos(a), np.sin(a)
    return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])


def eje_hacia(punto_mm, lado: int) -> np.ndarray:
    """Dirección de la boca para trabajar en `punto_mm`: 30° bajo la horizontal, en diagonal hacia el robot."""
    p = np.asarray(punto_mm, float)
    radial = np.array([p[0], p[1], 0.0]) / (np.hypot(p[0], p[1]) or 1.0)
    planta = _rotz(lado * g.GIRO_LLEGADA) @ radial
    i = np.radians(g.INCLINACION_BOCA)
    return np.cos(i) * planta + np.array([0.0, 0.0, -np.sin(i)])


def distancia_limpieza() -> float:
    """A lo largo del eje, de la boca al punto de la superficie que se limpia."""
    return g.ALTURA_BOCA_LIMPIEZA / np.sin(np.radians(g.INCLINACION_BOCA))


class ControlBoca:
    def __init__(self, cin: Cinematica):
        self.cin = cin
        m = cin.m
        self._s = m.site("boca").id
        self._dadr = np.array([m.jnt_dofadr[m.joint(n).id] for n in ARTICULACIONES[:5]])
        self._jp = np.zeros((3, m.nv))
        self._jr = np.zeros((3, m.nv))
        from sim import escena as base

        cuerpo_taladro = m.body("taladro").id
        self._g_taladro = [i for i in range(m.ngeom) if m.geom_bodyid[i] == cuerpo_taladro]
        self._g_brazo = [i for i in range(m.ngeom) if (m.geom_contype[i], m.geom_conaffinity[i]) == tuple(base._BRAZO)]
        self._mocap_taladro = m.body_mocapid[cuerpo_taladro]

    # --- cinemática ------------------------------------------------------------------------------------------
    def ik(self, p_mm, eje, q_lr_ini, iteraciones: int = 150) -> tuple[np.ndarray, float]:
        """Postura (grados de LeRobot) con la boca en `p_mm` mirando hacia `eje`. Devuelve (q, error en mm).

        Mínimos cuadrados amortiguados sobre las 5 articulaciones del brazo (con el giro de muñeca, que con la
        boquilla inclinada también orienta la boca). La pinza se conserva.
        """
        cin = self.cin
        q = lerobot_a_rad(q_lr_ini)
        obj = np.asarray(p_mm, float) * MM
        eje = np.asarray(eje, float) / np.linalg.norm(eje)
        for _ in range(iteraciones):
            p, R = cin.pose(q, self._s)
            e_pos, e_rot = obj - p, np.cross(R[:, 2], eje)
            if np.linalg.norm(e_pos) < 2e-4 and np.linalg.norm(e_rot) < 5e-3:
                break
            mujoco.mj_jacSite(cin.m, cin.d, self._jp, self._jr, self._s)
            J = np.vstack([self._jp[:, self._dadr], PESO_GIRO * self._jr[:, self._dadr]])
            e = np.concatenate([e_pos, PESO_GIRO * e_rot])
            dq = J.T @ np.linalg.solve(J @ J.T + 1e-6 * np.eye(6), e)
            q[:5] = np.clip(q[:5] + np.clip(dq, -0.1, 0.1), cin.rangos[:5, 0], cin.rangos[:5, 1])
        p, _ = cin.pose(q, self._s)
        return rad_a_lerobot(q), float(np.linalg.norm(obj - p) / MM)

    def boca(self, q_lr) -> np.ndarray:
        p, _ = self.cin.pose(lerobot_a_rad(q_lr), self._s)
        return p / MM

    def eje(self, q_lr) -> np.ndarray:
        _, R = self.cin.pose(lerobot_a_rad(q_lr), self._s)
        return R[:, 2].copy()

    def borde_inferior(self, q_lr) -> float:
        """Altura (mm) del punto más bajo del borde de la boca."""
        e = self.eje(q_lr)
        return float(self.boca(q_lr)[2] - g.DIAMETRO_BOCA / 2 * np.sqrt(max(0.0, 1 - e[2] ** 2)))

    def postura(self, p_mm, eje, lado: int, q_previa=None) -> np.ndarray:
        """IK robusta: desde la postura previa y, si no llega, desde la semilla del lado."""
        mejor = None
        for q0 in ([q_previa] if q_previa is not None else []) + [SEMILLA[lado]]:
            q0 = np.asarray(q0, float).copy()
            q, err = self.ik(p_mm, eje, q0)
            if mejor is None or err < mejor[1]:
                mejor = (q, err)
            if err < 1.0:
                break
        return mejor[0]

    def holgura(self, q_lr, punta_broca) -> float:
        """mm entre el brazo (con la boquilla) y un taladro vertical con la punta en `punta_broca`."""
        cin = self.cin
        cin.d.mocap_pos[self._mocap_taladro] = np.asarray(punta_broca, float) * MM
        cin.d.mocap_quat[self._mocap_taladro] = [1, 0, 0, 0]
        cin.d.qpos[cin.qadr] = lerobot_a_rad(q_lr)
        mujoco.mj_kinematics(cin.m, cin.d)
        ft = np.zeros(6)
        return min(mujoco.mj_geomDistance(cin.m, cin.d, a, b, 0.2, ft)
                   for a in self._g_brazo for b in self._g_taladro) / MM

    def holgura_plan(self, plan, punta_broca, cada: int = 3) -> float:
        return min(self.holgura(q, punta_broca) for q in list(plan)[::cada] + [plan[-1]])

    # --- trayectorias ----------------------------------------------------------------------------------------
    def linea(self, q_ini, p_fin, eje_fin=None, velocidad=g.VELOCIDAD_MAX_BOCA) -> list[np.ndarray]:
        """Posturas fotograma a fotograma para llevar la boca en línea recta a `p_fin` a `velocidad` mm/s, girando a
        la vez su dirección hacia `eje_fin` (si se da)."""
        q = np.asarray(q_ini, float)
        p0, e0 = self.boca(q), self.eje(q)
        e1 = e0 if eje_fin is None else np.asarray(eje_fin, float)
        dist = float(np.linalg.norm(np.asarray(p_fin) - p0))
        n = max(1, int(np.ceil(dist / velocidad * g.FPS)), int(np.ceil(np.degrees(np.arccos(np.clip(e0 @ e1, -1, 1))) / 3)))
        plan = []
        for k in range(1, n + 1):
            f = k / n
            p = p0 + (np.asarray(p_fin) - p0) * f
            e = e0 + (e1 - e0) * f
            q, _ = self.ik(p, e / np.linalg.norm(e), q)
            plan.append(q.copy())
        return plan

    def articular(self, q_ini, q_fin, duracion: float) -> list[np.ndarray]:
        n = max(1, int(round(duracion * g.FPS)))
        q_ini, q_fin = np.asarray(q_ini, float), np.asarray(q_fin, float)
        return [q_ini + (q_fin - q_ini) * (0.5 - 0.5 * np.cos(np.pi * k / n)) for k in range(1, n + 1)]

    def _retirarse(self, q) -> list[np.ndarray]:
        """Si la boca está cerca de la superficie, sube en vertical (con la misma dirección)."""
        q = np.asarray(q, float)
        if self.boca(q)[2] > g.ALTURA_CARA_TABLA + 60:
            return []
        return self.linea(q, self.boca(q) + np.array([0.0, 0.0, RETIRADA]))

    # --- gestos ----------------------------------------------------------------------------------------------
    def aparcar(self, q_ini, duracion: float = 1.5, alejarse: float = 0.0) -> list[np.ndarray]:
        """Sube, se aleja `alejarse` mm en planta contra la dirección de la boca (para salir de junto al taladro por
        donde vino) y vuelve a la postura de aparcado."""
        plan = self._retirarse(q_ini)
        q = plan[-1] if plan else np.asarray(q_ini, float)
        if alejarse > 0:
            e = self.eje(q)
            planta = np.array([e[0], e[1], 0.0]) / (np.hypot(e[0], e[1]) or 1.0)
            plan += self.linea(q, self.boca(q) - planta * alejarse)
            q = plan[-1]
        return plan + self.articular(q, APARCADO, duracion)

    def ir_a(self, q_ini, p_mm, eje, lado: int, velocidad=g.VELOCIDAD_MAX_BOCA, espera: float = 0.0) -> list[np.ndarray]:
        """Lleva la boca a `p_mm` mirando hacia `eje`.

        Sin `espera` (no hay taladro): sube, va por el espacio articular a `RETIRADA` mm por encima del punto y baja.
        Con `espera` (junto al taladro): va por el espacio articular a un punto de espera `espera` mm en planta contra
        la dirección de la boca, a la misma altura, y entra en horizontal: subir acercaría el brazo al taladro."""
        q = np.asarray(q_ini, float)
        plan = self._retirarse(q)
        if plan:
            q = plan[-1]
        p_mm = np.asarray(p_mm, float)
        if espera > 0:
            planta = np.array([eje[0], eje[1], 0.0]) / (np.hypot(eje[0], eje[1]) or 1.0)
            q_espera = self.postura(p_mm - planta * espera, eje, lado)
            plan += self.articular(q, q_espera, DURACION_ARTICULAR)
            return plan + self.linea(q_espera, p_mm, eje, velocidad)
        q_entrada = self.postura(p_mm + np.array([0.0, 0.0, RETIRADA]), eje, lado, q)
        plan += self.articular(q, q_entrada, DURACION_ARTICULAR)
        return plan + self.linea(q_entrada, p_mm, eje, velocidad)

    @staticmethod
    def punto_boca(punto_mm, eje, distancia: float) -> np.ndarray:
        return np.asarray(punto_mm, float) - np.asarray(eje, float) * distancia

    def preapunto(self, punta_broca, lado: int) -> tuple[np.ndarray, np.ndarray]:
        """(posición de la boca, dirección) en el preapunto."""
        e = eje_hacia(punta_broca, lado)
        planta = np.array([e[0], e[1], 0.0]) / np.hypot(e[0], e[1])
        p = self.punto_boca(punta_broca, e, g.DISTANCIA_ACOMPANAR) + [0.0, 0.0, g.SUBIDA_PREAPUNTO] - planta * g.ATRAS_PREAPUNTO
        return p, e

    def acercarse_al_taladro(self, q_ini, punta_broca, lado: int,
                             solo_este_lado: bool = False) -> tuple[list[np.ndarray], int, float]:
        """Al preapunto, desde donde la cámara del robot ve la broca. Elige el punto de espera (y, si hace falta y se
        permite, el otro lado) para que el brazo no pase a menos de `HOLGURA_MIN` del taladro.
        Devuelve (plan, lado, holgura en mm)."""
        mejor = None
        for l in (lado,) if solo_este_lado else (lado, -lado):
            destino, e = self.preapunto(punta_broca, l)
            for espera in ESPERAS:
                plan = self.ir_a(q_ini, destino, e, l, velocidad=g.VELOCIDAD_ACERCARSE, espera=espera)
                if np.linalg.norm(self.boca(plan[-1]) - destino) > 2.0:
                    continue  # no llega
                h = self.holgura_plan(plan, punta_broca)
                if mejor is None or h > mejor[2]:
                    mejor = (plan, l, h)
                if h >= HOLGURA_MIN:
                    return mejor
        if mejor is None:
            destino, e = self.preapunto(punta_broca, lado)
            plan = self.ir_a(q_ini, destino, e, lado, velocidad=g.VELOCIDAD_ACERCARSE, espera=ESPERAS[0])
            mejor = (plan, lado, self.holgura_plan(plan, punta_broca))
        return mejor

    def afinar(self, q_ini, punta_broca, lado: int) -> list[np.ndarray]:
        """Del preapunto a acompañar, con la punta ya medida por la cámara del robot."""
        e = eje_hacia(punta_broca, lado)
        return self.linea(q_ini, self.punto_boca(punta_broca, e, g.DISTANCIA_ACOMPANAR), e,
                          velocidad=g.VELOCIDAD_ACERCARSE)

    def _barrido(self, q_ini, puntos_sup: np.ndarray, eje, lado: int) -> list[np.ndarray]:
        d = distancia_limpieza()
        plan = self.ir_a(q_ini, self.punto_boca(puntos_sup[0], eje, d), eje, lado)
        q = plan[-1]
        for p in puntos_sup[1:]:
            tramo = self.linea(q, self.punto_boca(p, eje, d), eje)
            plan += tramo
            q = tramo[-1]
        return plan

    def zigzag(self, q_ini, centro_mm, radio: float, z: float, lado: int, paso: float = 14.0) -> list[np.ndarray]:
        """Pasada en zigzag sobre un círculo de `radio` alrededor de `centro_mm` (x, y) en la superficie de altura z.
        Las filas van de lado a lado de la boca y avanzan desde lo más alejado del robot hacia él."""
        c = np.array([centro_mm[0], centro_mm[1], z])
        e = eje_hacia(c, lado)
        avance = np.array([e[0], e[1], 0.0]) / np.hypot(e[0], e[1])  # hacia donde mira la boca en planta
        lateral = np.array([-avance[1], avance[0], 0.0])
        pts = []
        for i, t in enumerate(np.arange(-radio, radio + 0.1, paso)):
            w = np.sqrt(max(radio ** 2 - t ** 2, 0.0))
            fila = [c + avance * t - lateral * w, c + avance * t + lateral * w]
            pts += fila if i % 2 == 0 else fila[::-1]
        return self._barrido(q_ini, np.array(pts), e, lado)

    def limpiar_tabla(self, q_ini, tabla: g.PoseTabla, lado: int, paso: float = 28.0) -> list[np.ndarray]:
        largo, ancho = g.TABLA_TAMANO[0] / 2 - 10, g.TABLA_TAMANO[1] / 2 - 10
        filas = np.arange(-ancho, ancho + 0.1, paso)
        pts_tabla = []
        for i, y in enumerate(filas):
            fila = [(-largo, y), (largo, y)]
            pts_tabla += fila if i % 2 == 0 else fila[::-1]
        pts = tabla.a_mesa(np.array(pts_tabla))
        pts = np.column_stack([pts, np.full(len(pts), g.ALTURA_CARA_TABLA)])
        e = eje_hacia([tabla.x, tabla.y, g.ALTURA_CARA_TABLA], lado)
        return self._barrido(q_ini, pts, e, lado)
