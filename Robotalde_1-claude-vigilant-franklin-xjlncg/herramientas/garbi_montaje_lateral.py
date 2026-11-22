"""Montaje lateral de la boquilla (muñeca fija, tubo por el costado derecho del brazo): inclinación mínima de la boca
en el área de trabajo, holgura con el taladro y si la cámara oficial de la muñeca ve la boca y la broca.
Uso: python herramientas/garbi_montaje_lateral.py [imagen.jpg]. Requiere escena.MONTAJE = "lateral" o construir_spec(montaje="lateral")."""
import numpy as np, mujoco, sys
from garbi import escena, contrato as g
from sim.entorno import lerobot_a_rad
M = escena.construir_spec(montaje="lateral").compile(); d = mujoco.MjData(M)
J4 = ("shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex")
qadr = [M.jnt_qposadr[M.joint(n).id] for n in J4 + ("wrist_roll",)]
dadr = [M.jnt_dofadr[M.joint(n).id] for n in J4]
lo = M.jnt_range[[M.joint(n).id for n in J4], 0]; hi = M.jnt_range[[M.joint(n).id for n in J4], 1]
sb = M.site("boca").id
jp = np.zeros((3, M.nv)); jr = np.zeros((3, M.nv))
rng = np.random.default_rng(0)
def ik(obj, picado, q0, it=200):
    q = q0.copy()
    for _ in range(it):
        d.qpos[qadr] = list(q) + [0.0]; mujoco.mj_kinematics(M, d); mujoco.mj_comPos(M, d)
        p = d.site_xpos[sb]; z = d.site_xmat[sb].reshape(3, 3)[:, 2]
        e = np.concatenate([obj * 1e-3 - p, [0.05 * (-np.sin(np.radians(picado)) - z[2])]])
        if np.linalg.norm(e) < 5e-4: break
        mujoco.mj_jacSite(M, d, jp, jr, sb)
        Jz = np.array([np.cross(jr[:, k], z)[2] for k in dadr])
        Jm = np.vstack([jp[:, dadr], 0.05 * Jz])
        q = np.clip(q + np.clip(Jm.T @ np.linalg.solve(Jm @ Jm.T + 1e-6 * np.eye(4), e), -.1, .1), lo, hi)
    d.qpos[qadr] = list(q) + [0.0]; mujoco.mj_kinematics(M, d)
    return np.linalg.norm(obj * 1e-3 - d.site_xpos[sb]) * 1000, d.site_xmat[sb].reshape(3, 3)[:, 2], q
semillas = [rng.uniform(lo, hi) for _ in range(25)]
print("inclinación mínima alcanzable de la boca (grados bajo la horizontal), boca a 15 mm sobre la superficie")
for x in (120, 170, 220, 270, 320):
    fila = []
    for y in (-150, -75, 0, 75, 150):
        z = (g.ALTURA_CARA_TABLA if abs(y) <= 150 and 85 <= x <= 285 else g.ALFOMBRILLA_GROSOR) + 15
        mejor = None
        for pic in (10, 20, 30, 45, 60, 75, 85):
            ok = False
            for q0 in semillas:
                err, eje, q = ik(np.array([x, y, z]), pic, q0)
                if err < 1.5 and abs(-np.degrees(np.arcsin(eje[2])) - pic) < 3:
                    ok = True; break
            if ok:
                mejor = pic; break
        fila.append("  —" if mejor is None else f"{mejor:3d}")
    print(f"x={x:3d}: " + "  ".join(fila), flush=True)
print("(columnas: y = -150, -75, 0, 75, 150 mm; — = no llega)")

# --- acompañar: holgura con el taladro y si la cámara oficial ve la boca y la broca ---------------------------------
from sim import escena as base_escena
cam = M.camera("wrist").id
tal_b = M.body("taladro").id; tal = M.body_mocapid[tal_b]
G_TAL = [i for i in range(M.ngeom) if M.geom_bodyid[i] == tal_b]
G_BRAZO = [i for i in range(M.ngeom) if (M.geom_contype[i], M.geom_conaffinity[i]) == tuple(base_escena._BRAZO)]
ancho, alto = 640, 480
f = (alto / 2) / np.tan(np.radians(M.cam_fovy[cam]) / 2)
def visible(punto_m, geom_objetivo=None):
    mujoco.mj_forward(M, d)
    c = d.cam_xpos[cam]; Rc = d.cam_xmat[cam].reshape(3, 3)
    v = punto_m - c
    pc = Rc.T @ v  # cámara MuJoCo: mira por -z
    if pc[2] >= 0: return False
    u, w = f * pc[0] / -pc[2], f * pc[1] / -pc[2]
    if abs(u) > ancho / 2 or abs(w) > alto / 2: return False
    gid = np.array([-1], dtype=np.int32)
    dist = mujoco.mj_ray(M, d, c, v / np.linalg.norm(v), None, 1, M.body("wrist_camera").id, gid)
    return dist < 0 or dist >= np.linalg.norm(v) - 0.006 or (geom_objetivo is not None and gid[0] in geom_objetivo)
G_BOCA = [M.geom("boca_tubo").id]
G_BROCA = [M.geom("broca").id]
print("\nacompañar (broca 30 mm por delante de la boca, inclinación mínima + margen):")
res = []
for x in (130, 170, 210, 250):
    for y in (-110, -40, 40, 110):
        hecho = None
        for pic in (20, 30, 45, 60, 75):
            for q0 in semillas:
                obj = np.array([x, y, g.ALTURA_CARA_TABLA + 15])
                err, eje, q = ik(obj, pic, q0)
                if err < 1.5 and abs(-np.degrees(np.arcsin(eje[2])) - pic) < 3:
                    planta = np.array([eje[0], eje[1]]) / np.hypot(eje[0], eje[1])
                    pb = obj[:2] + planta * 30
                    d.mocap_pos[tal] = [pb[0] * 1e-3, pb[1] * 1e-3, g.ALTURA_CARA_TABLA * 1e-3]; d.mocap_quat[tal] = [1, 0, 0, 0]
                    d.qpos[qadr] = list(q) + [0.0]; mujoco.mj_forward(M, d)
                    ft = np.zeros(6)
                    h = min(mujoco.mj_geomDistance(M, d, a, b, 0.2, ft) for a in G_BRAZO for b in G_TAL) * 1000
                    boca_v = visible(d.site_xpos[sb] - eje * 0.005, G_BOCA)
                    broca_v = visible(np.array([pb[0], pb[1], g.ALTURA_CARA_TABLA + 8]) * 1e-3, G_BROCA)
                    hecho = (pic, h, boca_v, broca_v)
                    break
            if hecho: break
        res.append(hecho)
        print(f"  broca cerca de ({x:3d},{y:4d}): " + ("no llega" if hecho is None else
              f"inclinación {hecho[0]}° · holgura {hecho[1]:5.1f} mm · cámara ve boca {'sí' if hecho[2] else 'no'} · broca {'sí' if hecho[3] else 'no'}"), flush=True)
# imagen de la cámara oficial en la última postura evaluada y vista desde fuera
import cv2
r = mujoco.Renderer(M, 480, 640)
r.update_scene(d, "wrist"); a = r.render().copy()
r.update_scene(d, "vista_cerca"); b = r.render().copy()
cv2.imwrite(sys.argv[1] if len(sys.argv) > 1 else "camara.jpg", np.hstack([a, b])[:, :, ::-1])
