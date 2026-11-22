#!/usr/bin/env python3
"""
grabar_camaras.py - Graba en MP4 lo que ven las cámaras mientras el supervisor está en marcha (para el vídeo).

Lee las imágenes que publica el supervisor (camara_front.jpg con las detecciones dibujadas y camara_gripper.jpg),
así que NO abre las cámaras: funciona a la vez que el supervisor y la web.

Guarda en video/grabaciones/:
    AAAAMMDD_HHMMSS_superior.mp4   cámara de arriba con las detecciones (640×360)
    AAAAMMDD_HHMMSS_muneca.mp4     cámara de la muñeca (640×480)
    AAAAMMDD_HHMMSS_juntas.mp4     las dos lado a lado (1280×480), listo para el montaje

Uso (con el supervisor ya en marcha, desde la web o a mano):
    python grabar_camaras.py                 # hasta Ctrl+C
    python grabar_camaras.py --segundos 30
"""

import argparse
import os
import time

import cv2
import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
FPS = 15


def leer(nombre: str, max_edad: float = 1.5):
    ruta = os.path.join(AQUI, nombre)
    try:
        if time.time() - os.path.getmtime(ruta) > max_edad:
            return None
        img = cv2.imread(ruta)
        return img
    except OSError:
        return None


def main():
    ap = argparse.ArgumentParser(description="Grabar las cámaras del supervisor en MP4")
    ap.add_argument("--segundos", type=float, default=None, help="duración (por defecto hasta Ctrl+C)")
    args = ap.parse_args()

    carpeta = os.path.join(AQUI, "video", "grabaciones")
    os.makedirs(carpeta, exist_ok=True)
    base = os.path.join(carpeta, time.strftime("%Y%m%d_%H%M%S"))
    fourcc = cv2.VideoWriter_fourcc(*"avc1")   # H.264: lo abre iMovie / QuickTime
    sal = {
        "superior": cv2.VideoWriter(base + "_superior.mp4", fourcc, FPS, (640, 360)),
        "muneca": cv2.VideoWriter(base + "_muneca.mp4", fourcc, FPS, (640, 480)),
        "juntas": cv2.VideoWriter(base + "_juntas.mp4", fourcc, FPS, (1280, 480)),
    }

    print("Esperando imágenes del supervisor (¿está en marcha?)...")
    while leer("camara_front.jpg") is None:
        time.sleep(0.5)
    print(f"● Grabando en {base}_*.mp4  ·  Ctrl+C para terminar")

    negro_top = np.zeros((360, 640, 3), np.uint8)
    negro_mun = np.zeros((480, 640, 3), np.uint8)
    ultimo_top, ultimo_mun = negro_top, negro_mun
    t0 = time.time()
    n = 0
    try:
        while args.segundos is None or time.time() - t0 < args.segundos:
            t_frame = t0 + n / FPS
            espera = t_frame - time.time()
            if espera > 0:
                time.sleep(espera)
            top = leer("camara_front.jpg")
            mun = leer("camara_gripper.jpg")
            ultimo_top = cv2.resize(top, (640, 360)) if top is not None else ultimo_top
            ultimo_mun = cv2.resize(mun, (640, 480)) if mun is not None else ultimo_mun
            sal["superior"].write(ultimo_top)
            sal["muneca"].write(ultimo_mun)
            lienzo = np.zeros((480, 1280, 3), np.uint8)
            lienzo[60:420, 0:640] = ultimo_top           # la de arriba, centrada en vertical
            lienzo[:, 640:] = ultimo_mun
            sal["juntas"].write(lienzo)
            n += 1
            if n % (FPS * 5) == 0:
                print(f"  {n / FPS:.0f} s")
    except KeyboardInterrupt:
        pass
    finally:
        for v in sal.values():
            v.release()
        print(f"✓ {n / FPS:.1f} s guardados en {carpeta}")


if __name__ == "__main__":
    main()
