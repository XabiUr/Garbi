"""Mide la zona de la punta de cada dedo de la pinza para crear almohadillas de colisión (cajas).

MuJoCo usa la envolvente convexa de cada malla para colisionar: con la pieza del dedo fijo eso
rellena el hueco entre dedos. Por eso sustituimos las colisiones de los dedos por cajas simples.
"""
from pathlib import Path

import mujoco
import numpy as np

RAIZ = Path(__file__).resolve().parents[1]
modelo = mujoco.MjModel.from_xml_path(str(RAIZ / "assets" / "so101" / "scene.xml"))
datos = mujoco.MjData(modelo)
datos.qpos[:] = 0
datos.qpos[5] = -0.17  # pinza cerrada
mujoco.mj_forward(modelo, datos)

punta = datos.site("gripperframe").xpos.copy()
b_pinza = modelo.body("gripper").id
eje_aprox = -datos.xmat[b_pinza].reshape(3, 3)[:, 2]  # -z local de la pinza apunta a la punta
print("eje de aproximación (mundo):", np.round(eje_aprox, 3), " punta:", np.round(punta, 4))


def vertices_mundo(nombre_malla, cuerpo):
    for g in range(modelo.ngeom):
        if (modelo.geom_type[g] == mujoco.mjtGeom.mjGEOM_MESH and modelo.geom_group[g] == 3
                and modelo.mesh(modelo.geom_dataid[g]).name == nombre_malla
                and modelo.body(modelo.geom_bodyid[g]).name == cuerpo):
            m = modelo.geom_dataid[g]
            ini, n = modelo.mesh_vertadr[m], modelo.mesh_vertnum[m]
            v = modelo.mesh_vert[ini:ini + n]
            return datos.geom_xpos[g] + v @ datos.geom_xmat[g].reshape(3, 3).T, g
    raise KeyError(nombre_malla)


cajas = {}
for malla, cuerpo in (("wrist_roll_follower_so101_v1", "gripper"), ("moving_jaw_so101_v1", "moving_jaw_so101_v1")):
    vw, g = vertices_mundo(malla, cuerpo)
    # distancia hacia atrás desde la punta, a lo largo del eje de aproximación
    atras = (punta - vw) @ eje_aprox
    zona = vw[(atras > -0.005) & (atras < 0.035)]
    b = modelo.body(cuerpo).id
    R = datos.xmat[b].reshape(3, 3)
    local = (zona - datos.xpos[b]) @ R
    cajas[cuerpo] = (b, R, local.min(0), local.max(0))

# Dirección de cierre: del dedo fijo al móvil
centros = {c: datos.xpos[b] + R @ ((lo + hi) / 2) for c, (b, R, lo, hi) in cajas.items()}
cierre = centros["moving_jaw_so101_v1"] - centros["gripper"]
cierre -= cierre @ eje_aprox * eje_aprox
cierre /= np.linalg.norm(cierre)
print("dirección de cierre (mundo):", np.round(cierre, 3))

GROSOR = 0.0015  # medio grosor de la almohadilla
for cuerpo, (b, R, lo, hi) in cajas.items():
    hacia_otro = R.T @ (cierre if cuerpo == "gripper" else -cierre)  # en ejes locales
    k = int(np.argmax(np.abs(hacia_otro)))
    centro = (lo + hi) / 2
    mitad = (hi - lo) / 2
    cara = hi[k] if hacia_otro[k] > 0 else lo[k]
    centro[k] = cara - np.sign(hacia_otro[k]) * GROSOR
    mitad[k] = GROSOR
    print(f'\n<!-- almohadilla {cuerpo} (eje de cierre local {"xyz"[k]}) -->')
    print(f'<geom name="almohadilla_{cuerpo}" type="box" pos="{centro[0]:.4f} {centro[1]:.4f} {centro[2]:.4f}" '
          f'size="{mitad[0]:.4f} {mitad[1]:.4f} {mitad[2]:.4f}" class="almohadilla"/>')
