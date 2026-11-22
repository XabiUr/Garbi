"""Explora el modelo MuJoCo del SO-101: cinemática en la pose cero y renders de prueba.

Uso: .venv\\Scripts\\python.exe herramientas\\explorar_modelo.py
"""
from pathlib import Path

import mujoco
import numpy as np
from PIL import Image

RAIZ = Path(__file__).resolve().parents[1]
SALIDA = RAIZ / "salidas" / "exploracion"
SALIDA.mkdir(parents=True, exist_ok=True)

modelo = mujoco.MjModel.from_xml_path(str(RAIZ / "assets" / "so101" / "scene.xml"))
datos = mujoco.MjData(modelo)

print("Articulaciones:")
for j in range(modelo.njnt):
    print(f"  {j} {modelo.joint(j).name:15s} rango={np.round(modelo.jnt_range[j], 3)}")


def informe(nombre_pose, q):
    datos.qpos[:] = q
    mujoco.mj_forward(modelo, datos)
    sitio = datos.site("gripperframe")
    print(f"\n[{nombre_pose}] q={np.round(q, 2)}")
    print("  gripperframe pos:", np.round(sitio.xpos, 4))
    print("  gripperframe ejes (columnas x,y,z):\n", np.round(sitio.xmat.reshape(3, 3), 3))
    for cuerpo in ("shoulder", "upper_arm", "lower_arm", "wrist", "gripper", "moving_jaw_so101_v1"):
        print(f"  {cuerpo:20s} pos={np.round(datos.body(cuerpo).xpos, 4)}")
    j = modelo.joint("wrist_roll").id
    print("  eje wrist_roll (mundo):", np.round(datos.xaxis[j], 3))


informe("cero", np.zeros(modelo.nq))
informe("brazo_estirado", np.array([0, -1.0, 1.0, 0, 0, 0]))

render = mujoco.Renderer(modelo, 480, 640)
camara = mujoco.MjvCamera()
for i, (azim, elev) in enumerate([(90, -20), (0, -20), (180, -60)]):
    datos.qpos[:] = 0
    mujoco.mj_forward(modelo, datos)
    camara.lookat[:] = [0.1, 0, 0.15]
    camara.distance = 0.7
    camara.azimuth = azim
    camara.elevation = elev
    render.update_scene(datos, camara)
    Image.fromarray(render.render()).save(SALIDA / f"cero_{i}.png")
print("\nRenders guardados en", SALIDA)
