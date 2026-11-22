"""Mediciones de viabilidad técnica de Garbi en simulación (par de los servos, sensibilidad a la calibración,
tolerancia de la limpieza). Uso: python herramientas/garbi_viabilidad.py [par|calibracion|tolerancia]

Los resultados y su lectura están en .plans/aspira/viabilidad-tecnica.md.
"""
from __future__ import annotations

import sys

import mujoco
import numpy as np

from garbi import contrato as g
from garbi.control import ControlBoca, distancia_limpieza, eje_hacia
from garbi.mundo import APARCADO, MundoGarbi
from sim.cinematica import ARTICULACIONES
from sim.entorno import lerobot_a_rad

MM = 1e-3


def puntos_zona(z=g.ALTURA_CARA_TABLA, radios=(130, 175, 215), angulos=(-30, 0, 30)):
    return [np.array([r * np.cos(np.radians(t)), r * np.sin(np.radians(t)), z]) for r in radios for t in angulos]


def posturas_trabajo(ctl: ControlBoca) -> dict[str, list[np.ndarray]]:
    """Posturas de cada fase del ciclo en toda la zona y por los dos lados."""
    out = {"acompañar": [], "preapunto": [], "limpiar tabla": [], "limpiar alfombrilla": []}
    for lado in (1, -1):
        for P in puntos_zona():
            e = eje_hacia(P, lado)
            out["acompañar"].append(ctl.postura(P - e * g.DISTANCIA_ACOMPANAR, e, lado))
            out["preapunto"].append(ctl.postura(ctl.preapunto(P, lado)[0], e, lado))
            out["limpiar tabla"].append(ctl.postura(P - e * distancia_limpieza(), e, lado))
        for P in puntos_zona(g.ALFOMBRILLA_GROSOR, radios=(140, 230), angulos=(-40, 40)):
            e = eje_hacia(P, lado)
            out["limpiar alfombrilla"].append(ctl.postura(P - e * distancia_limpieza(), e, lado))
    out["aparcado"] = [np.asarray(APARCADO, float)]
    return out


# --- 1. par de los servos -------------------------------------------------------------------------------------------
def par_estatico(m: mujoco.MjModel, d: mujoco.MjData, q_lr, dofs, cuerpo_herramienta: int, tiron_n: float) -> np.ndarray:
    """N·m que cada articulación tiene que hacer para sostener la postura (gravedad + tirón vertical de la manguera
    en el origen del soporte de la boquilla)."""
    qadr = [m.jnt_qposadr[m.joint(n).id] for n in ARTICULACIONES]
    d.qpos[:] = 0
    d.qpos[qadr] = lerobot_a_rad(q_lr)
    d.qvel[:] = 0
    d.qacc[:] = 0
    mujoco.mj_inverse(m, d)
    tau = d.qfrc_inverse[dofs].copy()
    if tiron_n:
        jp = np.zeros((3, m.nv))
        mujoco.mj_jacBody(m, d, jp, None, cuerpo_herramienta)
        tau += -(jp[:, dofs].T @ np.array([0.0, 0.0, -tiron_n]))  # el motor compensa la fuerza externa
    return tau


def medir_par() -> None:
    mundo = MundoGarbi(render=False)
    m = mundo.modelo
    d = mujoco.MjData(m)
    ctl = ControlBoca(mundo.cin)
    dofs = [m.jnt_dofadr[m.joint(n).id] for n in ARTICULACIONES[:5]]
    cuerpo = m.body("boca_cuerpo").id
    posturas = posturas_trabajo(ctl)
    masa_original = m.body_mass[cuerpo]
    print("Par estático máximo (N·m) por articulación: pan, lift, elbow, wrist_flex, wrist_roll")
    for nombre, masa, tiron in [("brazo sin herramienta", 1e-6, 0.0), ("boquilla+cámara 100 g", 0.10, 0.0),
                                ("boquilla+cámara 150 g", 0.15, 0.0), ("100 g + manguera 1,5 N", 0.10, 1.5),
                                ("100 g + manguera 3 N", 0.10, 3.0)]:
        m.body_mass[cuerpo] = masa
        fila = []
        for fase, qs in posturas.items():
            fila.append((fase, np.max(np.abs([par_estatico(m, d, q, dofs, cuerpo, tiron) for q in qs]), axis=0)))
        maximo = np.max([f[1] for f in fila], axis=0)
        peor = max(fila, key=lambda f: f[1][1])[0]
        print(f"  {nombre:25s} máx {np.round(maximo, 2).tolist()}  (lift peor en «{peor}»)")
    m.body_mass[cuerpo] = masa_original


# --- 2. sensibilidad a la calibración -------------------------------------------------------------------------------
ITERACIONES_SERVO = 3


def medir_calibracion(sigma_grados=(0.5, 1.0, 2.0, 3.0), n=150) -> None:
    """El robot real tiene errores de calibración δ en cada articulación: el controlador cree estar en q y está en
    q + δ. Se mide, en la postura de acompañar y en la de limpiar:
    - el error absoluto de la boca (lo que pasaría sin realimentación visual);
    - el error de la boca respecto a la broca tras el apunto: la cámara del robot ve la punta real desde su pose real,
      pero el controlador proyecta el píxel con la pose que cree (q), y después coloca la boca con ese mismo modelo:
      parte del error se cancela;
    - la altura del borde de la boca al limpiar (depende solo del modelo: no hay realimentación de altura)."""
    mundo = MundoGarbi(render=False)
    ctl = ControlBoca(mundo.cin)
    cin = mundo.cin
    cam = mundo.modelo.camera("wrist").id
    rng = np.random.default_rng(0)

    def pose_cam(q_lr):
        q = lerobot_a_rad(q_lr)
        cin.d.qpos[cin.qadr] = q
        mujoco.mj_kinematics(cin.m, cin.d)
        mujoco.mj_camlight(cin.m, cin.d)
        Rc = cin.d.cam_xmat[cam].reshape(3, 3) @ np.diag([1.0, -1.0, -1.0])
        return Rc.T, -Rc.T @ (cin.d.cam_xpos[cam] / MM)

    for sigma in sigma_grados:
        abs_acomp, rel_acomp, borde, servo = [], [], [], []
        for _ in range(n):
            P = puntos_zona()[rng.integers(9)].copy()
            lado = int(rng.choice([-1, 1]))
            delta = np.concatenate([rng.normal(0, sigma, 5), [0.0]])
            e = eje_hacia(P, lado)
            # (a) sin realimentación: el controlador manda q para acompañar; la boca real está en FK(q + δ)
            q = ctl.postura(P - e * g.DISTANCIA_ACOMPANAR, e, lado)
            objetivo = P - e * g.DISTANCIA_ACOMPANAR
            abs_acomp.append(np.linalg.norm(ctl.boca(q + delta) - objetivo))
            # (b) con apunto desde el preapunto
            qp = ctl.postura(ctl.preapunto(P, lado)[0], e, lado)
            R_real, t_real = pose_cam(qp + delta)
            pc = R_real @ P + t_real
            rayo_cam = pc / pc[2]  # dirección del píxel (coordenadas normalizadas)
            R_cree, t_cree = pose_cam(qp)
            centro = -R_cree.T @ t_cree
            rayo = R_cree.T @ rayo_cam
            s = (g.ALTURA_CARA_TABLA - centro[2]) / rayo[2]
            P_medida = centro + rayo * s
            e2 = eje_hacia(P_medida, lado)
            q2 = ctl.postura(P_medida - e2 * g.DISTANCIA_ACOMPANAR, e2, lado)
            boca_real = ctl.boca(q2 + delta)
            rel_acomp.append(np.linalg.norm(boca_real - (P - e2 * g.DISTANCIA_ACOMPANAR)))
            # (b2) apunto en lazo cerrado y relativo: la cámara va rígida con la boquilla, así que mide la punta
            # respecto a la boca sin pasar por la cinemática (con el plano de la tabla visto por la propia cámara, p. ej.
            # con un ArUco de la tabla); se corrige y se vuelve a medir. Ruido de la medida: 1 mm.
            objetivo = P_medida - e2 * g.DISTANCIA_ACOMPANAR
            q3 = q2
            for _ in range(ITERACIONES_SERVO):
                boca_real = ctl.boca(q3 + delta)
                medido = (P - boca_real) + rng.normal(0, 1.0, 3)  # vector boca→punta medido por la cámara
                objetivo = objetivo + (medido - e2 * g.DISTANCIA_ACOMPANAR)
                q3 = ctl.postura(objetivo, e2, lado, q3)
            servo.append(np.linalg.norm(ctl.boca(q3 + delta) - (P - e2 * g.DISTANCIA_ACOMPANAR)))
            # (c) borde de la boca al limpiar
            ql = ctl.postura(P - e * distancia_limpieza(), e, lado)
            borde.append(ctl.borde_inferior(ql + delta) - ctl.borde_inferior(ql))
        p = lambda x: f"mediana {np.median(x):4.1f} · p95 {np.percentile(x, 95):4.1f}"
        print(f"σ = {sigma:.1f}° por articulación:")
        print(f"   boca al acompañar sin apunto (absoluto)  {p(abs_acomp)} mm")
        print(f"   boca respecto a la broca tras el apunto  {p(rel_acomp)} mm")
        print(f"   ídem con apunto en lazo cerrado ({ITERACIONES_SERVO} it.)  {p(servo)} mm")
        print(f"   altura del borde al limpiar: p5 {np.percentile(borde, 5):+5.1f} · p95 {np.percentile(borde, 95):+5.1f} mm")


# --- 3. tolerancia de la limpieza -----------------------------------------------------------------------------------
def medir_tolerancia(semillas=range(6)) -> None:
    """Viruta recogida por la línea base cuando la boca va más alta, más inclinada o desplazada (lo que tolera la
    aspiración: requisito para la teleoperación y para la política)."""
    from garbi.demostraciones import ejecutar_episodio
    import garbi.control as control

    m = MundoGarbi(render=False)
    base_altura, base_incl = g.ALTURA_BOCA_LIMPIEZA, g.INCLINACION_BOCA
    casos = [("nominal", 0, 0, 0)] + [(f"altura {d:+d} mm", d, 0, 0) for d in (-6, 6, 12, 20)] + \
            [(f"inclinación {d:+d}°", 0, d, 0) for d in (-10, 10)] + \
            [(f"desplazado {d} mm", 0, 0, d) for d in (8, 15)]
    for nombre, dz, dinc, dxy in casos:
        g.ALTURA_BOCA_LIMPIEZA = base_altura + dz
        g.INCLINACION_BOCA = base_incl + dinc
        recogido = []
        for orden in g.ORDENES_VLA:
            for s in semillas:
                if dxy:
                    original = control.ControlBoca.zigzag

                    def zig(self, q, centro, *a, _o=original, **k):
                        return _o(self, q, np.asarray(centro) + [dxy, 0], *a, **k)
                    control.ControlBoca.zigzag = zig
                try:
                    n, ini, fin = ejecutar_episodio(m, orden, s)
                finally:
                    if dxy:
                        control.ControlBoca.zigzag = original
                recogido.append(1 - fin / max(ini, 1))
        print(f"  {nombre:20s} recogida media {np.mean(recogido) * 100:5.1f} % · peor {np.min(recogido) * 100:5.1f} %")
    g.ALTURA_BOCA_LIMPIEZA, g.INCLINACION_BOCA = base_altura, base_incl


if __name__ == "__main__":
    que = sys.argv[1] if len(sys.argv) > 1 else "todo"
    if que in ("par", "todo"):
        medir_par()
    if que in ("calibracion", "todo"):
        medir_calibracion()
    if que in ("tolerancia", "todo"):
        medir_tolerancia()
