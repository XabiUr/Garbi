"""Comprueba que el amarre de la boca no choca con la pinza del SO-101 (mordaza fija, servo, cámara y móvil en todo su
recorrido). Usa las mallas del MJCF oficial en el marco de la pinza, el mismo del CAD.

Uso:  python hardware/garbi/comprobar_amarre.py   (necesita mujoco, trimesh, rtree y networkx)
"""
from pathlib import Path

import mujoco
import numpy as np
import trimesh

RAIZ = Path(__file__).resolve().parents[2]


def mallas_pinza():
    m = mujoco.MjModel.from_xml_path(str(RAIZ / "assets/so101/so101_new_calib_camera.xml"))
    d = mujoco.MjData(m)
    mujoco.mj_forward(m, d)
    g = m.body("gripper").id
    Rg, pg = d.xmat[g].reshape(3, 3), d.xpos[g]
    out = {}
    for i in range(m.ngeom):
        if m.geom_type[i] != mujoco.mjtGeom.mjGEOM_MESH or m.geom_group[i] == 3:
            continue
        cuerpo = m.body(m.geom_bodyid[i]).name
        if cuerpo not in ("gripper", "wrist", "wrist_camera_mount", "wrist_camera", "moving_jaw_so101_v1"):
            continue
        mid = m.geom_dataid[i]
        a, n = m.mesh_vertadr[mid], m.mesh_vertnum[mid]
        fa, fn = m.mesh_faceadr[mid], m.mesh_facenum[mid]
        w = (d.geom_xmat[i].reshape(3, 3) @ m.mesh_vert[a:a + n].T).T + d.geom_xpos[i]
        out.setdefault(f"{cuerpo}/{m.mesh(mid).name}", trimesh.Trimesh(((w - pg) @ Rg) * 1000, m.mesh_face[fa:fa + fn],
                                                                         process=False))
    eje = m.joint("gripper").id
    return out, (Rg.T @ (d.xanchor[eje] - pg)) * 1000, Rg.T @ d.xaxis[eje]


def holgura_tubo(pq, radio=14.5):
    """Holgura del tubo al salir por detrás de la abrazadera: recto hacia atrás y curvado hacia fuera (-y)."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    import amarre_boca as ab

    a = np.radians(ab.BOCA_ABIERTA)
    e = np.array([0, -np.sin(a), -np.cos(a)])
    boca = np.array(ab.BOCA)
    p0 = boca - e * (ab.ABRAZADERA[1] + 1)
    recto = [p0 - e * s for s in np.linspace(0, 80, 20)]
    c1, p1 = p0 - e * 40, np.array([boca[0], boca[1] - 10, -40.0])
    curvo = [(1 - t) ** 2 * p0 + 2 * (1 - t) * t * c1 + t ** 2 * p1 for t in np.linspace(0, 1, 30)]
    out = {}
    for nombre, linea in (("recto hacia atrás", recto), ("curvado hacia fuera", curvo)):
        pts = []
        for p, q in zip(linea[:-1], linea[1:]):
            t = (q - p) / np.linalg.norm(q - p)
            u = np.cross(t, [1, 0, 0])
            u /= np.linalg.norm(u)
            v = np.cross(t, u)
            pts += [p + radio * (np.cos(th) * u + np.sin(th) * v) for th in np.linspace(0, 2 * np.pi, 48, endpoint=False)]
        out[nombre] = float(-pq.signed_distance(np.array(pts)).max())
    return out


def main():
    amarre = trimesh.load(RAIZ / "hardware/garbi/amarre_boca/amarre_boca.stl")
    pq = trimesh.proximity.ProximityQuery(amarre)
    mallas, ancla, eje = mallas_pinza()
    for nombre, h in holgura_tubo(pq).items():
        print(f"tubo saliendo de la abrazadera, {nombre}: holgura {h:5.1f} mm")

    def holgura(t):
        dist = pq.signed_distance(t.vertices)  # > 0: dentro del amarre
        return int((dist > 0.05).sum()), float(-dist.max())

    for nombre, t in mallas.items():
        if not nombre.startswith("moving_jaw"):
            dentro, h = holgura(t)
            print(f"{nombre:45s} vértices dentro {dentro:4d}   holgura {h:5.1f} mm")
    movil = next(t for n, t in mallas.items() if n.startswith("moving_jaw"))
    for ang in range(-10, 101, 10):
        t = movil.copy()
        t.apply_transform(trimesh.transformations.rotation_matrix(np.radians(ang), eje, ancla))
        dentro, h = holgura(t)
        print(f"mordaza móvil a {ang:4d}°: vértices dentro {dentro:4d}   holgura {h:5.1f} mm")


if __name__ == "__main__":
    main()
