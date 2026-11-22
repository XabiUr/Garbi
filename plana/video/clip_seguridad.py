#!/usr/bin/env python3
"""
clip_seguridad.py - Clip de la escena de seguridad a partir de una grabación con el móvil (1080p, 30 fps, sin audio).

Recorta [inicio, fin] y sobreimprime rótulos que explican cada momento (RÓTULOS: desde qué segundo del vídeo
original sale cada texto). Por defecto, el IMG_0274.MOV: el brazo va a por la tabla, entra una mano y la coge,
el brazo se queda quieto y, con la zona libre, vuelve a reposo.

    python video/clip_seguridad.py
    python video/clip_seguridad.py --entrada ~/Downloads/OTRO.MOV --inicio 10 --fin 20
"""

import argparse
import os

import av
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

AQUI = os.path.dirname(os.path.abspath(__file__))
ANCHO, ALTO, FPS = 1920, 1080, 30
FUENTE = "/System/Library/Fonts/HelveticaNeue.ttc"

# (segundo del vídeo original desde el que se muestra, texto, color)
RÓTULOS = [
    (27.0, "Garbi va a limpiar la tabla", (255, 255, 255)),
    (29.4, "Entra una mano: se queda QUIETO", (251, 191, 36)),
    (32.2, "Espera a que la zona quede libre…", (255, 255, 255)),
    (35.3, "…y vuelve a reposo", (94, 234, 212)),
]


def capa_rotulo(texto: str, color) -> Image.Image:
    capa = Image.new("RGBA", (ANCHO, ALTO), (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    f = ImageFont.truetype(FUENTE, 64, index=1)
    w = d.textlength(texto, font=f)
    x, y = (ANCHO - w) / 2, ALTO - 170
    d.rounded_rectangle([x - 36, y - 22, x + w + 36, y + 92], radius=22, fill=(15, 23, 42, 200))
    d.text((x, y), texto, font=f, fill=color)
    f2 = ImageFont.truetype(FUENTE, 34, index=1)
    d.rounded_rectangle([40, 36, 520, 100], radius=16, fill=(15, 23, 42, 180))
    d.text((62, 48), "Seguridad · detección de manos", font=f2, fill=(148, 230, 220))
    return capa


def main():
    ap = argparse.ArgumentParser(description="Clip de seguridad con rótulos")
    ap.add_argument("--entrada", default=os.path.expanduser("~/Downloads/IMG_0274.MOV"))
    ap.add_argument("--inicio", type=float, default=27.0)
    ap.add_argument("--fin", type=float, default=38.7)
    ap.add_argument("--salida", default=os.path.join(AQUI, "clips", "seguridad.mp4"))
    args = ap.parse_args()

    os.makedirs(os.path.dirname(args.salida), exist_ok=True)
    capas = [(t, capa_rotulo(tx, col)) for t, tx, col in RÓTULOS]
    vid = cv2.VideoWriter(args.salida, cv2.VideoWriter_fourcc(*"avc1"), FPS, (ANCHO, ALTO))
    with av.open(args.entrada) as c:
        s = c.streams.video[0]
        s.thread_type = "AUTO"
        c.seek(int((args.inicio - 1) / s.time_base), stream=s, backward=True)
        siguiente, n = args.inicio, 0
        for f in c.decode(s):
            t = float(f.pts * s.time_base)
            if t < siguiente - 1e-3:
                continue
            if t > args.fin:
                break
            im = f.to_image().resize((ANCHO, ALTO))
            capa = None
            for t_rot, cp in capas:
                if t >= t_rot:
                    capa = cp
            if capa is not None:
                im.paste(capa, (0, 0), capa)
            vid.write(cv2.cvtColor(np.array(im), cv2.COLOR_RGB2BGR))
            n += 1
            siguiente = args.inicio + n / FPS   # de 60 a 30 fps: un fotograma de cada dos
    vid.release()
    print(f"✓ {args.salida} ({n / FPS:.1f} s)")


if __name__ == "__main__":
    main()
