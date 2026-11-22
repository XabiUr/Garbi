"""Prueba la IK cenital y mira la pinza abierta/cerrada y sus geometrías de colisión."""
import sys
from pathlib import Path

import mujoco
import numpy as np
from PIL import Image

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
from sim.cinematica import Cinematica  # noqa: E402

SALIDA = RAIZ / "salidas" / "exploracion"
modelo = mujoco.MjModel.from_xml_path(str(RAIZ / "assets" / "so101" / "scene.xml"))
datos = mujoco.MjData(modelo)
cin = Cinematica(modelo)

for objetivo in ([0.20, 0.0, 0.03], [0.25, 0.10, 0.03], [0.15, -0.12, 0.05], [0.30, 0.0, 0.03]):
    q, err = cin.inversa(objetivo, np.zeros(6))
    pos, eje = cin.directa(q)
    print(f"objetivo={objetivo} err={err*1000:.1f} mm  q(deg)={np.round(np.degrees(q), 1)} eje={np.round(eje, 2)}")
    print("   direccion mordaza (deg):", round(np.degrees(cin.direccion_mordaza(q)), 1))

q, _ = cin.inversa([0.22, 0.0, 0.03], np.zeros(6))
render = mujoco.Renderer(modelo, 480, 640)
camara = mujoco.MjvCamera()
opciones = mujoco.MjvOption()
for nombre, pinza in (("abierta", 1.7), ("cerrada", -0.17)):
    for grupo_col in (False, True):
        q2 = q.copy()
        q2[5] = pinza
        datos.qpos[:] = q2
        mujoco.mj_forward(modelo, datos)
        opciones.geomgroup[:] = [1, 1, 1, 0, 0, 0]
        if grupo_col:
            opciones.geomgroup[:] = [1, 0, 0, 1, 0, 0]
        camara.lookat[:] = datos.site("gripperframe").xpos
        camara.distance = 0.22
        camara.azimuth = 120
        camara.elevation = -10
        render.update_scene(datos, camara, opciones)
        sufijo = "_colision" if grupo_col else ""
        Image.fromarray(render.render()).save(SALIDA / f"pinza_{nombre}{sufijo}.png")

# Posición de los cuerpos de la pinza respecto a la punta, con la pinza cerrada
datos.qpos[:] = q
datos.qpos[5] = -0.17
mujoco.mj_forward(modelo, datos)
print("punta:", np.round(datos.site("gripperframe").xpos, 4))
for g in range(modelo.ngeom):
    b = modelo.geom_bodyid[g]
    if modelo.body(b).name in ("gripper", "moving_jaw_so101_v1") and modelo.geom_group[g] == 3:
        print(f"geom {g} cuerpo={modelo.body(b).name} malla={modelo.mesh(modelo.geom_dataid[g]).name}"
              f" aabb_centro={np.round(datos.geom_xpos[g], 4)}")
