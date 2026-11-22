"""Convierte la matriz 5×3 del equipo (carpeta `plana/` del hackathon) al CSV que lee `garbi/producto/matriz.py`.

    python herramientas/convertir_matriz_plana.py --plana ../plana --salida garbi/producto/matriz_equipo.csv

Entrada (lo que grabó el equipo):
- `posturas.json`: posturas 3-17 (rejilla 5×3, unidades de LeRobot con `use_degrees: false`) y `reposo`.
- `zona.json`: 4 esquinas en px de la cámara de arriba (640×360), medidas con el **círculo morado** puesto en cada
  esquina (delante-izq, delante-der, detrás-der, detrás-izq). Así que la posición de la matriz es la del círculo,
  igual que la que usa el respaldo del producto (sin problema de paralaje).
- `config.json` → `trayectorias`: offsets finales (`altura_final` a shoulder_lift, `offset_lateral_final` a
  shoulder_pan, `distancia_final` a elbow_flex) que el equipo suma a la postura grabada para el punto final. Se
  incluyen en la matriz para que el respaldo acabe en el mismo sitio que los episodios del dataset (`--sin-offsets`
  para no hacerlo).

Rejilla del equipo (cerebros.py): número → (columna u 0-4, fila v 0-2); u: izq→der, v: delante→detrás.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import cv2
import numpy as np

MOTORES = ("shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper")
MAPEO = {str(3 + j * 5 + i): (i, j) for j in range(3) for i in range(5)}   # '3'→(0,0) … '17'→(4,2)


def convertir(plana: Path, con_offsets: bool = True) -> list[dict]:
    posturas = json.loads((plana / "posturas.json").read_text())["posturas"]
    esquinas = np.array(json.loads((plana / "zona.json").read_text())["esquinas_px"], np.float32)
    unidad = np.array([[0, 0], [1, 0], [1, 1], [0, 1]], np.float32)
    H = cv2.getPerspectiveTransform(unidad, esquinas)   # (u,v) normalizado → px
    offsets = dict.fromkeys(MOTORES, 0.0)
    if con_offsets:
        tray = json.loads((plana / "config.json").read_text()).get("trayectorias", {})
        offsets["shoulder_lift"] = float(tray.get("altura_final", 0.0))
        offsets["shoulder_pan"] = float(tray.get("offset_lateral_final", 0.0))
        offsets["elbow_flex"] = float(tray.get("distancia_final", 0.0))
    filas = []
    for num, (i, j) in MAPEO.items():
        p = posturas[num]
        uv = cv2.perspectiveTransform(np.array([[[i / 4.0, j / 2.0]]], np.float32), H)[0, 0]
        fila = {"punto": num, "u": round(float(uv[0]), 2), "v": round(float(uv[1]), 2)}
        for m in MOTORES:
            fila[m] = round(float(p[f"{m}.pos"]) + offsets[m], 3)
        filas.append(fila)
    return filas


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--plana", default="../plana", help="carpeta del trabajo del hackathon (posturas.json, zona.json)")
    ap.add_argument("--salida", default="garbi/producto/matriz_equipo.csv")
    ap.add_argument("--sin-offsets", action="store_true", help="no sumar los offsets finales de trayectorias")
    a = ap.parse_args(argv)
    plana = Path(a.plana)
    filas = convertir(plana, not a.sin_offsets)
    salida = Path(a.salida)
    with salida.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0]))
        w.writeheader()
        w.writerows(filas)
    reposo = json.loads((plana / "posturas.json").read_text())["reposo"]
    print(f"{len(filas)} puntos → {salida}")
    print("postura_reposo:", [round(float(reposo[f"{m}.pos"]), 2) for m in MOTORES])


if __name__ == "__main__":
    main()
