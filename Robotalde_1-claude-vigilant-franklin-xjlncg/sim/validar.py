"""Validación de la simulación: seguimiento del cordón en todos los anclajes, vídeo e imágenes de una demostración.

Uso:
    MUJOCO_GL=egl python -m sim.validar                 # tabla de errores + vídeo + imágenes en salidas/sim/
    MUJOCO_GL=egl python -m sim.validar --sin-video
"""
from __future__ import annotations

import argparse
from pathlib import Path

import av
import cv2
import numpy as np
from PIL import Image

from lewelder import contrato as c
from sim import escena
from sim.demostraciones import Guion, ejecutar
from sim.entorno import EntornoSoldadura

RAIZ = Path(__file__).resolve().parents[1]
SALIDA = RAIZ / "salidas" / "sim"
LIMITE_ERROR = 2.0  # mm


def tabla_seguimiento(anclajes=None, tipos=("recta", "t"), guion: Guion | None = None):
    """Recorre el guion sin ruido en cada anclaje y tipo; devuelve la lista de resultados."""
    guion = guion or Guion(ruido=0.0)
    ent = EntornoSoldadura(render=False)
    resultados = [ejecutar(ent, a, t, guion) for a in (anclajes or list(c.ANCLAJES)) for t in tipos]
    ent.cerrar()
    return resultados


def detectar_aruco(img_rgb: np.ndarray) -> list[int]:
    diccionario = cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, c.DICCIONARIO_ARUCO))
    _, ids, _ = cv2.aruco.ArucoDetector(diccionario).detectMarkers(cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY))
    return [] if ids is None else sorted(int(i) for i in ids.reshape(-1))


def grabar_video(ruta: Path, anclaje: str, tipo: str, resolucion=(320, 240), semilla: int = 0,
                 ruido: float = 1.0) -> dict:
    """Vídeo mp4 (cenital | muñeca) de una demostración y algunas imágenes sueltas."""
    ent = EntornoSoldadura(resolucion=resolucion, render=True)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    contenedor = av.open(str(ruta), mode="w")
    flujo = contenedor.add_stream("libx264", rate=c.FPS_DATASET)
    flujo.width, flujo.height = resolucion[0] * 2, resolucion[1]
    flujo.pix_fmt = "yuv420p"
    fotos, cuadros = {}, []  # cuadros comprimidos en PNG para no llenar la memoria

    def al_fotograma(obs, accion):
        cuadro = np.hstack([obs["observation.images.cenital"], obs["observation.images.muneca"]])
        for paquete in flujo.encode(av.VideoFrame.from_ndarray(cuadro, format="rgb24")):
            contenedor.mux(paquete)
        cuadros.append(cv2.imencode(".png", cuadro)[1])

    res = ejecutar(ent, anclaje, tipo, Guion(ruido=ruido), semilla=semilla, al_fotograma=al_fotograma)
    for paquete in flujo.encode():
        contenedor.mux(paquete)
    contenedor.close()
    # Imágenes: reposo, inicio del cordón, mitad del cordón y fin
    con_gatillo = [i for i, m in enumerate(res.muestras) if m.gatillo]
    elegidos = {"reposo": 0, "inicio": con_gatillo[0], "mitad": con_gatillo[len(con_gatillo) // 2],
                "final": con_gatillo[-1]}
    for nombre, i in elegidos.items():
        fotos[nombre] = ruta.with_name(f"{ruta.stem}_{nombre}.png")
        Image.fromarray(cv2.imdecode(cuadros[i], cv2.IMREAD_UNCHANGED)).save(fotos[nombre])
    ids = detectar_aruco(cv2.imdecode(cuadros[0], cv2.IMREAD_UNCHANGED)[:, : resolucion[0]])
    ent.cerrar()
    return {"video": ruta, "fotos": fotos, "aruco_cenital": ids, "resultado": res}


def vista_general(ruta: Path, anclaje: str, tipo: str):
    """Imagen grande desde la cámara cenital con la pieza en el anclaje (para revisar la escena y los ArUco)."""
    ent = EntornoSoldadura(resolucion=(960, 720), render=True)
    ent.reset(anclaje, tipo)
    img = ent.imagen("cenital")
    Image.fromarray(img).save(ruta)
    ent.cerrar()
    return detectar_aruco(img)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--sin-video", action="store_true")
    p.add_argument("--anclaje", default="B", help="anclaje del vídeo")
    p.add_argument("--tipo", default="t", help="tipo de pieza del vídeo")
    a = p.parse_args(argv)
    SALIDA.mkdir(parents=True, exist_ok=True)

    print(f"Seguimiento del cordón con el guion sin ruido (límite {LIMITE_ERROR} mm):")
    print(f"{'anclaje':8s}{'tipo':7s}{'err. máx':>10s}{'err. medio':>12s}{'|y| máx':>10s}{'trabajo':>9s}"
          f"{'avance':>8s}{'s/epis.':>9s}")
    peor = 0.0
    for r in tabla_seguimiento():
        peor = max(peor, r.error_max)
        print(f"{r.anclaje:8s}{r.tipo:7s}{r.error_max:10.2f}{r.error_medio:12.2f}{r.lateral_max:10.2f}"
              f"{r.trabajo_medio:9.1f}{r.avance_medio:8.1f}{r.segundos:9.1f}")
    print("OK" if peor < LIMITE_ERROR else "FALLA", f"(peor {peor:.2f} mm)")

    for anclaje in c.ANCLAJES:
        ids = vista_general(SALIDA / f"cenital_{anclaje}.png", anclaje, "recta" if anclaje in "AC" else "t")
        print(f"cenital con pieza en {anclaje}: ArUco detectados {ids}")
    if not a.sin_video:
        info = grabar_video(SALIDA / f"demo_{a.anclaje}_{a.tipo}.mp4", a.anclaje, a.tipo)
        print("vídeo:", info["video"])
        for nombre, ruta in info["fotos"].items():
            print(f"  {nombre}: {ruta}")
        print("ArUco en la cenital (320x240):", info["aruco_cenital"])
    print("MJCF:", escena.guardar_mjcf(SALIDA / "lewelder.xml"))


if __name__ == "__main__":
    main()
