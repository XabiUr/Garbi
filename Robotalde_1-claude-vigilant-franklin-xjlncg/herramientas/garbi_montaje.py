"""Compara montajes de la boquilla en el bloque final de la pinza del SO-101 (cara opuesta a la cámara oficial).

Para cada montaje (ángulo de la boquilla respecto a la perpendicular, hacia las puntas, y altura en la pinza) mide en
el área de trabajo real: alcance al acompañar (punta a 30 mm de la broca, boquilla 10° picada, cualquier dirección de
llegada) y al limpiar (boquilla a ras de la superficie), holgura con el taladro y si la cámara de la muñeca ve la punta
de la boquilla y la broca. Uso: python herramientas/garbi_montaje.py
"""
from __future__ import annotations

import itertools
import sys

import mujoco
import numpy as np

from garbi import contrato as g
from garbi.mundo import MundoGarbi
from sim.entorno import lerobot_a_rad, rad_a_lerobot

MM = 1e-3
LARGO_BOQUILLA = 40.0 + 10.0  # boquilla rígida de 40 mm más la abrazadera
INCLINACION = 10.0  # grados que la boquilla va picada bajo la horizontal
DIST_BROCA = 30.0  # mm de la punta de la boquilla al eje de la broca
FOV_H, FOV_V = 80.0, 62.0  # cámara de muñeca (módulo UVC 32x32 típico)

mundo = MundoGarbi(render=False)
M, cin = mundo.modelo, mundo.cin
D = cin.d
GB = M.body("gripper").id
CAM = M.body("wrist_camera").id
DADR = np.array([M.jnt_dofadr[M.joint(n).id] for n in ("shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll")])
LO, HI = cin.rangos[:5, 0], cin.rangos[:5, 1]
CAJA_PINZA = (np.array([-35.0, -28.0, -104.0]), np.array([30.0, 24.0, 1.0]))  # mm, marco de la pinza
EJE_CAM_LOCAL = np.array([0.0, -0.42, -0.91])  # eje óptico de la cámara en el marco de la pinza (aprox.)


def montaje(beta: float, z_base: float):
    """(base, dirección) de la boquilla en el marco de la pinza: sale de la cara -y, inclinada beta hacia las puntas."""
    b = np.radians(beta)
    d = np.array([0.0, -np.cos(b), -np.sin(b)])
    base = np.array([-5.0, CAJA_PINZA[0][1], z_base])
    return base, d


def fk(q):
    D.qpos[cin.qadr] = q
    mujoco.mj_kinematics(M, D)
    return D.xpos[GB] / MM, D.xmat[GB].reshape(3, 3).copy()


def punta(q, base, d):
    p, R = fk(q)
    return p + R @ (base + d * LARGO_BOQUILLA), R @ d


def ik(objetivo, eje, base, d, q0, it=60):
    q = q0.copy()
    for _ in range(it):
        p, a = punta(q, base, d)
        e = np.concatenate([objetivo - p, 40 * (eje - a)])
        if np.linalg.norm(e[:3]) < 0.5 and np.linalg.norm(eje - a) < 0.03:
            break
        J = np.zeros((6, 5))
        for j in range(5):
            dq = np.zeros(6); dq[j] = 1e-4
            p2, a2 = punta(q + dq, base, d)
            J[:, j] = np.concatenate([p2 - p, 40 * (a2 - a)]) / 1e-4
        q[:5] = np.clip(q[:5] + np.clip(J.T @ np.linalg.solve(J @ J.T + 1e-3 * np.eye(6), e), -.2, .2), LO, HI)
    p, a = punta(q, base, d)
    return q, np.linalg.norm(objetivo - p), np.degrees(np.arccos(np.clip(a @ eje, -1, 1)))


rng = np.random.default_rng(0)
N = 30000
Q = np.column_stack([rng.uniform(LO, HI, (N, 5)), np.zeros(N)])
POSES = [fk(q) for q in Q]
P0 = np.array([p for p, _ in POSES]); R0 = np.array([R for _, R in POSES])


def resolver(objetivo, eje, base, d):
    pts = P0 + np.einsum("nij,j->ni", R0, base + d * LARGO_BOQUILLA)
    ejes = np.einsum("nij,j->ni", R0, d)
    coste = np.linalg.norm(pts - objetivo, axis=1) + 80 * np.linalg.norm(ejes - eje, axis=1)
    mejor = None
    for k in np.argsort(coste)[:5]:
        r = ik(objetivo, eje, base, d, Q[k].copy())
        if mejor is None or r[1] + r[2] < mejor[1] + mejor[2]:
            mejor = r
        if r[1] < 1.5 and r[2] < 3:
            break
    return mejor


def direccion(rumbo, picado=INCLINACION):
    a, i = np.radians(rumbo), np.radians(picado)
    return np.array([np.cos(a) * np.cos(i), np.sin(a) * np.cos(i), -np.sin(i)])


CAMARA = {"tipo": "oficial", "pos": None, "eje": None}  # o «boquilla»: misma cara que la boquilla, más arriba


def camara_boquilla(base, d):
    """Cámara en la cara de la boquilla, 40 mm más cerca de la muñeca y 15 mm fuera de la cara, mirando a la broca."""
    pos = np.array([base[0], base[1] - 15.0, base[2] + 40.0])
    objetivo = base + d * (LARGO_BOQUILLA + DIST_BROCA)
    eje = (objetivo - pos) / np.linalg.norm(objetivo - pos)
    return pos, eje


def ve(q, punto) -> bool:
    """¿La cámara ve `punto` (dentro del campo y sin la pinza delante)?"""
    p, R = fk(q)
    if CAMARA["tipo"] == "oficial":
        c = D.xpos[CAM] / MM
        eje = R @ EJE_CAM_LOCAL
    else:
        c = p + R @ CAMARA["pos"]
        eje = R @ CAMARA["eje"]
    v = punto - c
    if np.degrees(np.arccos(np.clip(v @ eje / np.linalg.norm(v), -1, 1))) > min(FOV_H, FOV_V) / 2:
        return False
    # oclusión por la caja de la pinza (en su marco)
    a, b = R.T @ (c - p), R.T @ (punto - p)
    lo, hi = CAJA_PINZA[0] + 2, CAJA_PINZA[1] - 2
    for t in np.linspace(0.05, 0.95, 30):
        x = a + (b - a) * t
        if np.all(x > lo) and np.all(x < hi):
            return False
    return True


cuerpo_taladro = M.body("taladro").id
G_TAL = [i for i in range(M.ngeom) if M.geom_bodyid[i] == cuerpo_taladro]
from sim import escena as base_escena  # noqa: E402

G_BRAZO = [i for i in range(M.ngeom) if (M.geom_contype[i], M.geom_conaffinity[i]) == tuple(base_escena._BRAZO)]


def holgura(q, P) -> float:
    D.mocap_pos[M.body_mocapid[cuerpo_taladro]] = P * MM
    D.mocap_quat[M.body_mocapid[cuerpo_taladro]] = [1, 0, 0, 0]
    D.qpos[cin.qadr] = q
    mujoco.mj_kinematics(M, D)
    ft = np.zeros(6)
    return min(mujoco.mj_geomDistance(M, D, a, b, 0.2, ft) for a in G_BRAZO for b in G_TAL
               if M.geom_bodyid[a] != M.body("boca_cuerpo").id) / MM


def evaluar(beta, z_base, puntos_taladro, puntos_limpieza):
    base, d = montaje(beta, z_base)
    if CAMARA["tipo"] == "boquilla":
        CAMARA["pos"], CAMARA["eje"] = camara_boquilla(base, d)
    rumbos = (0, 45, -45, 90, -90, 135, -135)
    acomp = vista = 0
    hols = []
    for P in puntos_taladro:
        mejor = None
        for r in rumbos:
            e = direccion(r)
            tip = P - np.array([e[0], e[1], 0]) / np.hypot(e[0], e[1]) * DIST_BROCA
            tip[2] = g.ALTURA_CARA_TABLA + 15
            q, ep, er = resolver(tip, e, base, d)
            if ep < 2 and er < 4:
                h = holgura(q, P)
                cam = ve(q, punta(q, base, d)[0]) and ve(q, P + [0, 0, 5])
                score = (h > 10, cam, h)
                if mejor is None or score > mejor[0]:
                    mejor = (score, h, cam)
        if mejor:
            acomp += mejor[0][0]
            vista += mejor[2] and mejor[0][0]
            hols.append(mejor[1])
    limpia = 0
    for P in puntos_limpieza:
        for r in rumbos:
            e = direccion(r)
            tip = P.copy(); tip[2] = P[2] + 17
            q, ep, er = resolver(tip, e, base, d)
            if ep < 2 and er < 4:
                limpia += 1
                break
    return acomp, vista, limpia, (min(hols) if hols else float("nan"))


if __name__ == "__main__":
    tx = np.mean(g.ZONA_TABLA_X)
    pts_tal = [np.array([x, y, g.ALTURA_CARA_TABLA]) for x in (tx - 70, tx - 20, tx + 30, tx + 80) for y in (-120, -40, 40, 120)]
    ax, ay = g.ALFOMBRILLA_CENTRO
    pts_lim = [np.array([x, y, g.ALFOMBRILLA_GROSOR]) for x in np.linspace(90, 450, 5) for y in np.linspace(-200, 200, 5)]
    print(f"{len(pts_tal)} puntos de taladro en la madera · {len(pts_lim)} puntos de limpieza en el tapete")
    CAMARA["tipo"] = sys.argv[1] if len(sys.argv) > 1 else "oficial"
    angulos = (0, 20) if CAMARA["tipo"] == "boquilla" else (0, 20, 40, 60)
    print("cámara:", CAMARA["tipo"])
    for beta, zb in itertools.product(angulos, (-60, -85)):
        a, v, l, h = evaluar(beta, zb, pts_tal, pts_lim)
        print(f"boquilla {beta:2d}° hacia las puntas, a {abs(zb)} mm de la muñeca: acompaña {a}/{len(pts_tal)} "
              f"(la cámara ve punta y broca en {v}) · limpia {l}/{len(pts_lim)} · holgura mín {h:.0f} mm", flush=True)
