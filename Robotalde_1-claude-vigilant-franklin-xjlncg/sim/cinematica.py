"""Cinemática inversa numérica del SO-101 en MuJoCo.

Resuelve la postura del brazo para que la punta de la pinza (sitio `gripperframe`) quede en una
posición dada y apuntando hacia abajo (agarre cenital), que es como se coge casi todo en una mesa.

El SO-101 tiene 5 articulaciones de brazo + pinza. Para un agarre cenital bastan 4 para la posición
y la inclinación (pan, lift, elbow, wrist_flex); `wrist_roll` se fija aparte para alinear la pinza
con el objeto.

`inversa_pose` generaliza la IK a cualquier sitio (p. ej. `punta_antorcha`) y a cualquier dirección de
aproximación (un eje del sitio debe apuntar en una dirección dada): usa las 5 articulaciones del brazo,
con 3 restricciones de posición y 2 de dirección (el giro alrededor del propio eje queda libre).
"""
from __future__ import annotations

import mujoco
import numpy as np

ARTICULACIONES = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"]
BRAZO_IK = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex"]
BRAZO_POSE = BRAZO_IK + ["wrist_roll"]
ABAJO = np.array([0.0, 0.0, -1.0])


class Cinematica:
    def __init__(self, modelo: mujoco.MjModel, sitio_pose: str | None = None):
        """`sitio_pose`: sitio por defecto de `inversa_pose`/`pose` (p. ej. "punta_antorcha")."""
        self.m = modelo
        self.d = mujoco.MjData(modelo)  # datos propios: no tocan la simulación
        self.qadr = np.array([modelo.jnt_qposadr[modelo.joint(n).id] for n in ARTICULACIONES])
        self.dadr_ik = np.array([modelo.jnt_dofadr[modelo.joint(n).id] for n in BRAZO_IK])
        self.dadr_pose = np.array([modelo.jnt_dofadr[modelo.joint(n).id] for n in BRAZO_POSE])
        self.rangos = np.array([modelo.jnt_range[modelo.joint(n).id] for n in ARTICULACIONES])
        self.sitio = modelo.site("gripperframe").id
        self.sitio_pose = modelo.site(sitio_pose).id if sitio_pose else self.sitio
        self.j_roll = modelo.joint("wrist_roll").id
        self.b_pinza = modelo.body("gripper").id
        self._jp = np.zeros((3, modelo.nv))
        self._jr = np.zeros((3, modelo.nv))

    # --- cinemática directa -------------------------------------------------------------------
    def directa(self, q: np.ndarray):
        """Devuelve (posición de la punta, eje de aproximación) para las 6 articulaciones q (rad)."""
        self.d.qpos[self.qadr] = q
        mujoco.mj_kinematics(self.m, self.d)
        mujoco.mj_comPos(self.m, self.d)
        pos = self.d.site_xpos[self.sitio].copy()
        eje = self.d.xaxis[self.j_roll].copy()
        # El eje de wrist_roll puede apuntar hacia la muñeca o hacia la punta: lo orientamos a la punta.
        if np.dot(eje, pos - self.d.xpos[self.b_pinza]) < 0:
            eje = -eje
        return pos, eje

    def direccion_mordaza(self, q: np.ndarray) -> float:
        """Ángulo (rad, en el plano XY) del eje X local de la pinza: indica hacia dónde cierran las mordazas."""
        self.directa(q)
        x_local = self.d.xmat[self.b_pinza].reshape(3, 3)[:, 0]
        return float(np.arctan2(x_local[1], x_local[0]))

    # --- cinemática inversa -------------------------------------------------------------------
    def inversa(self, pos_obj, q_ini, roll=None, peso_giro=0.3, iteraciones=300, tol=5e-4):
        """Busca q (rad) con la punta en `pos_obj` y apuntando hacia abajo.

        Devuelve (q, error_en_metros). `roll` fija wrist_roll; si es None se conserva el de q_ini.
        """
        q = np.array(q_ini, dtype=float).copy()
        if roll is not None:
            q[4] = roll
        amort = 1e-3
        for _ in range(iteraciones):
            pos, eje = self.directa(q)
            e_pos = np.asarray(pos_obj) - pos
            e_rot = np.cross(eje, ABAJO)
            if np.linalg.norm(e_pos) < tol and np.linalg.norm(e_rot) < 1e-2:
                break
            mujoco.mj_jacSite(self.m, self.d, self._jp, self._jr, self.sitio)
            J = np.vstack([self._jp[:, self.dadr_ik], peso_giro * self._jr[:, self.dadr_ik]])
            e = np.concatenate([e_pos, peso_giro * e_rot])
            dq = J.T @ np.linalg.solve(J @ J.T + amort * np.eye(6), e)
            dq = np.clip(dq, -0.2, 0.2)
            q[:4] = np.clip(q[:4] + dq, self.rangos[:4, 0], self.rangos[:4, 1])
        pos, _ = self.directa(q)
        return q, float(np.linalg.norm(np.asarray(pos_obj) - pos))

    def inversa_alineada(self, pos_obj, yaw_objeto, q_ini, roll_neutro=0.0):
        """IK cenital girando wrist_roll para que las mordazas queden paralelas a las caras del objeto."""
        q, _ = self.inversa(pos_obj, q_ini, roll=roll_neutro)
        # Cuánto cambia la dirección de la mordaza al girar wrist_roll (signo depende del modelo).
        a0 = self.direccion_mordaza(q)
        q_test = q.copy()
        q_test[4] += 0.1
        signo = np.sign(_envolver(self.direccion_mordaza(q_test) - a0)) or 1.0
        # Un cubo es simétrico cada 90°: buscamos el giro más pequeño (entre -45° y 45°).
        delta = _envolver_90(yaw_objeto - a0)
        roll = np.clip(roll_neutro + signo * delta, self.rangos[4, 0], self.rangos[4, 1])
        return self.inversa(pos_obj, q, roll=roll)


    # --- pose de un sitio arbitrario ------------------------------------------------------------
    def pose(self, q: np.ndarray, sitio: str | int | None = None):
        """(posición, matriz de giro 3x3) del sitio para las 6 articulaciones q (rad)."""
        s = self._id_sitio(sitio)
        self.d.qpos[self.qadr] = q
        mujoco.mj_kinematics(self.m, self.d)
        mujoco.mj_comPos(self.m, self.d)
        return self.d.site_xpos[s].copy(), self.d.site_xmat[s].reshape(3, 3).copy()

    def inversa_pose(self, pos_obj, dir_obj, q_ini, sitio: str | int | None = None, eje_local=(0.0, 0.0, 1.0),
                     peso_giro=0.2, iteraciones=200, tol=2e-5, tol_ang=2e-4):
        """Busca q (rad) con el sitio en `pos_obj` (m) y su eje local `eje_local` apuntando en `dir_obj`.

        Usa las 5 articulaciones del brazo (la pinza se conserva de q_ini). Mínimos cuadrados amortiguados con la
        parte de giro proyectada al plano perpendicular al eje (el giro alrededor del eje no importa).
        Devuelve (q, error_de_posición_m, error_angular_rad).
        """
        s = self._id_sitio(sitio)
        eje_local = np.asarray(eje_local, dtype=float)
        dir_obj = np.asarray(dir_obj, dtype=float) / np.linalg.norm(dir_obj)
        pos_obj = np.asarray(pos_obj, dtype=float)
        q = np.array(q_ini, dtype=float).copy()
        amort = 1e-4
        jp, jr = np.zeros((3, self.m.nv)), np.zeros((3, self.m.nv))
        for _ in range(iteraciones):
            pos, R = self.pose(q, s)
            eje = R @ eje_local
            e_pos = pos_obj - pos
            e_rot = np.cross(eje, dir_obj)  # velocidad angular que lleva eje hacia dir_obj
            if np.dot(eje, dir_obj) < 0 and np.linalg.norm(e_rot) < 1e-6:  # justo al revés: empujón
                e_rot = np.cross(eje, np.array([1.0, 0, 0]) if abs(eje[0]) < 0.9 else np.array([0, 1.0, 0]))
            if np.linalg.norm(e_pos) < tol and np.linalg.norm(e_rot) < tol_ang and np.dot(eje, dir_obj) > 0:
                break
            mujoco.mj_jacSite(self.m, self.d, jp, jr, s)
            P = np.eye(3) - np.outer(eje, eje)
            J = np.vstack([jp[:, self.dadr_pose], peso_giro * (P @ jr[:, self.dadr_pose])])
            e = np.concatenate([e_pos, peso_giro * e_rot])
            dq = J.T @ np.linalg.solve(J @ J.T + amort * np.eye(6), e)
            dq = np.clip(dq, -0.2, 0.2)
            q[:5] = np.clip(q[:5] + dq, self.rangos[:5, 0], self.rangos[:5, 1])
        pos, R = self.pose(q, s)
        eje = R @ eje_local
        ang = float(np.arccos(np.clip(np.dot(eje, dir_obj), -1.0, 1.0)))
        return q, float(np.linalg.norm(pos_obj - pos)), ang

    def inversa_6d(self, pos_obj, R_obj, q_ini, sitio: str | int | None = None, peso_giro=0.05,
                   iteraciones=300, tol=2e-5, tol_ang=2e-4):
        """Busca q (rad) con el sitio en `pos_obj` (m) y con la orientación `R_obj` (3x3, ejes en columnas).

        Con 5 articulaciones no toda pose 6D es alcanzable: es un ajuste por mínimos cuadrados amortiguados con
        `peso_giro` metros por radián (0,05 → 1° pesa como 0,9 mm). La pinza se conserva de q_ini.
        Devuelve (q, error_de_posición_m, error_angular_rad).
        """
        s = self._id_sitio(sitio)
        pos_obj = np.asarray(pos_obj, dtype=float)
        R_obj = np.asarray(R_obj, dtype=float)
        q = np.array(q_ini, dtype=float).copy()
        jp, jr = np.zeros((3, self.m.nv)), np.zeros((3, self.m.nv))
        amort = 1e-5
        for _ in range(iteraciones):
            pos, R = self.pose(q, s)
            e_pos = pos_obj - pos
            e_rot = 0.5 * sum(np.cross(R[:, i], R_obj[:, i]) for i in range(3))
            if np.linalg.norm(e_pos) < tol and np.linalg.norm(e_rot) < tol_ang:
                break
            mujoco.mj_jacSite(self.m, self.d, jp, jr, s)
            J = np.vstack([jp[:, self.dadr_pose], peso_giro * jr[:, self.dadr_pose]])
            e = np.concatenate([e_pos, peso_giro * e_rot])
            dq = np.linalg.solve(J.T @ J + amort * np.eye(5), J.T @ e)
            dq = np.clip(dq, -0.2, 0.2)
            q_nuevo = q.copy()
            q_nuevo[:5] = np.clip(q[:5] + dq, self.rangos[:5, 0], self.rangos[:5, 1])
            if np.max(np.abs(q_nuevo - q)) < 1e-9:
                break
            q = q_nuevo
        pos, R = self.pose(q, s)
        ang = float(np.arccos(np.clip((np.trace(R.T @ R_obj) - 1) / 2, -1.0, 1.0)))
        return q, float(np.linalg.norm(pos_obj - pos)), ang

    def _id_sitio(self, sitio) -> int:
        if sitio is None:
            return self.sitio_pose
        return sitio if isinstance(sitio, (int, np.integer)) else self.m.site(sitio).id


def _envolver(a):
    return (a + np.pi) % (2 * np.pi) - np.pi


def _envolver_90(a):
    return (a + np.pi / 4) % (np.pi / 2) - np.pi / 4
