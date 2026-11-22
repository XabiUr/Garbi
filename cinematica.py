#!/usr/bin/env python3
"""
cinematica.py - Cinemática del SO-101 para llevar la PUNTA DE LA BOQUILLA a un punto de la mesa.

- Unidades: el robot trabaja normalizado (use_degrees=False, -100..100). El modelo (URDF) en grados.
  grados = normalizado · (range_max - range_min) · 180 / (100 · 4095)   (calibración de LeRobot del seguidor)
- Punta (TCP): la boquilla no está en el "gripper_frame_link" del URDF. `tcp` es el vector de la punta en ese
  marco (metros), medido con calibrar_boquilla.py (pivote: misma punta, varias inclinaciones).
- IK con placo: posición de la punta + orientación (peso suave), límites de las juntas y regularización hacia la
  semilla (no salta de rama).
"""

import json
import os
from typing import Dict, Optional, Tuple

import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
URDF = os.path.join(AQUI, "so101", "so101_new_calib.urdf")
CALIB = os.path.expanduser("~/.cache/huggingface/lerobot/calibration/robots/so_follower/so100_follower.json")
JUNTAS = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll"]


class Cinematica:
    def __init__(self, tcp=(0.0, 0.0, 0.0), urdf: str = URDF, calib: str = CALIB, desfases=(0, 0, 0, 0, 0)):
        import placo
        cal = json.load(open(calib))
        self.k = np.array([(cal[m]["range_max"] - cal[m]["range_min"]) * 180.0 / (100.0 * 4095) for m in JUNTAS])
        self.tcp = np.asarray(tcp, float)
        self.desfases = np.asarray(desfases, float)   # grados que se suman al convertir (corrige el "cero" del modelo)
        self.robot = placo.RobotWrapper(urdf)
        self.solver = placo.KinematicsSolver(self.robot)
        self.solver.mask_fbase(True)
        self.solver.mask_dof("gripper")
        # límites REALES del robot (±98 normalizado → grados del modelo): la IK sacrifica orientación antes que pasarse
        for m, k, d in zip(JUNTAS, self.k, self.desfases):
            self.robot.set_joint_limits(m, float(np.deg2rad(-98 * k + d)), float(np.deg2rad(98 * k + d)))
        self.solver.enable_joint_limits(True)
        # posición de la punta: obligatoria · orientación: preferencia (con 5 motores no siempre se puede las dos)
        self.t_pos = self.solver.add_position_task("gripper_frame_link", np.zeros(3))
        self.t_pos.configure("posicion", "soft", 100.0)   # casi obligatoria (hard + límites → QP imposible)
        self.t_ori = self.solver.add_orientation_task("gripper_frame_link", np.eye(3))
        self.reg = self.solver.add_joints_task()   # preferir la solución cercana a la semilla (misma rama del codo)
        self.reg.configure("regularizacion", "soft", 1e-3)

    # --- unidades ---------------------------------------------------------------------------------------------------
    def grados(self, postura: Dict) -> np.ndarray:
        return np.array([postura[f"{m}.pos"] for m in JUNTAS]) * self.k + self.desfases

    def postura(self, q_deg: np.ndarray, gripper: float = 0.0) -> Dict[str, float]:
        p = {f"{m}.pos": float(v) for m, v in zip(JUNTAS, (np.asarray(q_deg) - self.desfases) / self.k)}
        p["gripper.pos"] = float(gripper)
        return p

    def _poner(self, q_deg: np.ndarray):
        for m, v in zip(JUNTAS, np.deg2rad(q_deg)):
            self.robot.set_joint(m, float(v))
        self.robot.update_kinematics()

    # --- directa ----------------------------------------------------------------------------------------------------
    def marco(self, postura: Dict) -> np.ndarray:
        """4×4 del gripper_frame_link."""
        self._poner(self.grados(postura))
        return np.array(self.robot.get_T_world_frame("gripper_frame_link"))

    def punta(self, postura: Dict, tcp: Optional[np.ndarray] = None) -> np.ndarray:
        T = self.marco(postura)
        return T[:3, 3] + T[:3, :3] @ (self.tcp if tcp is None else tcp)

    # --- inversa ----------------------------------------------------------------------------------------------------
    def ik(self, p: np.ndarray, R: np.ndarray, semilla: Dict, peso_orientacion: float = 0.1,
           iteraciones: int = 60) -> Tuple[Dict[str, float], float]:
        """Postura con la punta en p (m) y orientación ≈ R, cerca de `semilla`. (postura, error de posición en m).
        Si alguna articulación se sale de su rango (-100..100 normalizado) el error es inf."""
        p = np.asarray(p, float)
        q0 = self.grados(semilla)
        self._poner(q0)
        self.reg.set_joints({m: float(v) for m, v in zip(JUNTAS, np.deg2rad(q0))})
        self.t_ori.R_world_frame = R
        self.t_ori.configure("orientacion", "soft", peso_orientacion)
        for i in range(iteraciones):
            if i % 5 == 0:   # el marco debe ir a p - R_actual·tcp (la punta cuelga del marco según su giro real)
                R_act = np.array(self.robot.get_T_world_frame("gripper_frame_link"))[:3, :3]
                self.t_pos.target_world = p - R_act @ self.tcp
            self.solver.solve(True)
            self.robot.update_kinematics()
        q = np.rad2deg([self.robot.get_joint(m) for m in JUNTAS])
        sol = self.postura(q, semilla.get("gripper.pos", 0.0))
        if any(abs(sol[f"{m}.pos"]) > 100 for m in JUNTAS):
            return sol, float("inf")
        return sol, float(np.linalg.norm(self.punta(sol) - p))


def rot_z(a: float) -> np.ndarray:
    c, s = np.cos(a), np.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1.0]])


def media_rotaciones(Rs) -> np.ndarray:
    """Rotación media (proyección de la suma sobre SO(3))."""
    U, _, Vt = np.linalg.svd(np.sum(Rs, axis=0))
    R = U @ Vt
    if np.linalg.det(R) < 0:
        U[:, -1] *= -1
        R = U @ Vt
    return R


def resolver_pivote(cin: Cinematica, posturas) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Punta fija en un punto con varias orientaciones: R_i·t + o_i = p. Devuelve (t, p, errores en m)."""
    A, b = [], []
    for q in posturas:
        T = cin.marco(q)
        A.append(np.hstack([T[:3, :3], -np.eye(3)]))
        b.append(-T[:3, 3])
    A, b = np.vstack(A), np.concatenate(b)
    x, *_ = np.linalg.lstsq(A, b, rcond=None)
    err = np.linalg.norm((A @ x - b).reshape(-1, 3), axis=1)
    return x[:3], x[3:], err


def resolver_pivote_con_desfases(cin: Cinematica, posturas, juntas=(1, 2, 3), prior_deg: float = 15.0):
    """Pivote ajustando además un desfase (grados) en las juntas indicadas (por defecto hombro, codo y muñeca).
    Devuelve (t, p, desfases(5), errores en m). Necesita ≥ 6 posturas variadas."""
    from scipy.optimize import least_squares
    t0, p0, _ = resolver_pivote(cin, posturas)
    base = cin.desfases.copy()

    def residuos(x):
        d = base.copy()
        d[list(juntas)] += x[6:]
        cin.desfases = d
        r = [cin.punta(q, x[:3]) - x[3:6] for q in posturas]
        return np.concatenate(r + [x[6:] / prior_deg * 0.002])   # el desfase cuesta como 2 mm cada prior_deg

    sol = least_squares(residuos, np.r_[t0, p0, np.zeros(len(juntas))])
    d = base.copy()
    d[list(juntas)] += sol.x[6:]
    cin.desfases = d
    err = np.array([np.linalg.norm(cin.punta(q, sol.x[:3]) - sol.x[3:6]) for q in posturas])
    return sol.x[:3], sol.x[3:6], d, err
