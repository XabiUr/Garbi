#!/usr/bin/env python3
"""
montar_video.py - Monta el vídeo final de Garbi (≤ 60 s) con las grabaciones del móvil y los clips ya hechos.

Mensaje: el valor de no tener que parar a quitar la biruta («Tú taladras. Garbi limpia.»).
Cada TRAMO: (fuente, inicio, fin, velocidad, rótulo, etiqueta). Las fuentes pueden ser los .MOV del iPhone (4K, se
leen con PyAV) o los clips de video/clips. Rótulos sobreimpresos, fundido corto entre tramos y sin audio
(la música o la voz se ponen en iMovie).

    python video/montar_video.py        → video/garbi_video.mp4
"""

import os

import av
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from hacer_plantilla import dibujar_rotulo   # mismos rótulos que la plantilla

AQUI = os.path.dirname(os.path.abspath(__file__))
DESCARGAS = os.path.expanduser("~/Downloads")
ANCHO, ALTO, FPS = 1920, 1080, 30
FUENTE = "/System/Library/Fonts/HelveticaNeue.ttc"
FUNDIDO = 8   # fotogramas de fundido entre tramos
ETIQ_ASP = "Aspiradora en integración"

TRAMOS = [
    ("rotulo", 2.5, {"titulo": "Garbi", "texto": "Tú taladras. Garbi limpia.", "pie": "Hackathon LeRobot Bilbao II · Robotalde"}),
    ("IMG_0275.MOV", 0.0, 3.4, 1.0, "Cada agujero deja biruta", None),
    ("IMG_0275.MOV", 5.8, 9.6, 1.0, "Al empezar, Garbi se coloca junto a la broca", None),
    ("clips/entrenamiento.mp4", 1.0, 5.0, 1.0, "Aprendido por imitación (ACT)", None),
    ("IMG_0284.MOV", 1.0, 9.5, 1.25, "Al terminar, limpia la pieza", ETIQ_ASP),
    ("IMG_0279.MOV", 2.0, 40.0, 3.5, "Y deja el puesto limpio", ETIQ_ASP + " · ×3,5"),
    ("clips/seguridad.mp4", 0.0, 11.7, 1.25, None, None),   # ya lleva sus rótulos
    ("rotulo", 4.0, {"titulo": "Sin pausas para limpiar",
                     "texto": "Más tiempo taladrando · Puesto limpio · Menos polvo · Marca siempre visible",
                     "pie": "Nadie tiene que parar a quitar la biruta"}),
    ("rotulo", 3.0, {"titulo": "Garbi", "texto": "Tú taladras. Garbi limpia.",
                     "pie": "github.com/XabiUr/Garbi  ·  huggingface.co/datasets/Xaflas/garbi_V1.0.0"}),
]


def capa(rotulo, etiqueta):
    c = Image.new("RGBA", (ANCHO, ALTO), (0, 0, 0, 0))
    d = ImageDraw.Draw(c)
    if rotulo:
        f = ImageFont.truetype(FUENTE, 64, index=1)
        w = d.textlength(rotulo, font=f)
        x, y = (ANCHO - w) / 2, ALTO - 170
        d.rounded_rectangle([x - 36, y - 22, x + w + 36, y + 92], radius=22, fill=(15, 23, 42, 205))
        d.text((x, y), rotulo, font=f, fill=(255, 255, 255))
    if etiqueta:
        f2 = ImageFont.truetype(FUENTE, 30, index=1)
        w2 = d.textlength(etiqueta, font=f2)
        d.rounded_rectangle([ANCHO - w2 - 84, 36, ANCHO - 40, 96], radius=16, fill=(120, 53, 15, 200))
        d.text((ANCHO - w2 - 62, 48), etiqueta, font=f2, fill=(254, 243, 199))
    return c


def fotogramas_fuente(ruta, inicio, fin, velocidad):
    """Fotogramas (PIL, 1920×1080) de [inicio, fin] a la velocidad dada, muestreados a 30 fps de salida."""
    with av.open(ruta) as c:
        s = c.streams.video[0]
        s.thread_type = "AUTO"
        c.seek(int(max(0, inicio - 1) / s.time_base), stream=s, backward=True)
        siguiente, n = inicio, 0
        for f in c.decode(s):
            t = float(f.pts * s.time_base)
            if t < siguiente - 1e-3:
                continue
            if t > fin:
                break
            im = f.to_image()
            if im.size != (ANCHO, ALTO):
                im = im.resize((ANCHO, ALTO))
            yield im
            n += 1
            siguiente = inicio + n * velocidad / FPS


def main():
    salida = os.path.join(AQUI, "garbi_video.mp4")
    vid = cv2.VideoWriter(salida, cv2.VideoWriter_fourcc(*"avc1"), FPS, (ANCHO, ALTO))
    anterior = None   # último fotograma escrito (para el fundido)
    total = 0
    for tramo in TRAMOS:
        if tramo[0] == "rotulo":
            im = dibujar_rotulo(tramo[2])
            frames = (im for _ in range(int(tramo[1] * FPS)))
            nombre = f"rótulo «{tramo[2]['titulo']}»"
        else:
            fuente, ini, fin, vel, rot, etq = tramo
            ruta = os.path.join(AQUI, fuente) if fuente.startswith("clips/") else os.path.join(DESCARGAS, fuente)
            cp = capa(rot, etq) if (rot or etq) else None
            frames = (Image.alpha_composite(im.convert("RGBA"), cp).convert("RGB") if cp else im
                      for im in fotogramas_fuente(ruta, ini, fin, vel))
            nombre = f"{fuente} {ini}-{fin} s ×{vel}"
        n0 = total
        for i, im in enumerate(frames):
            a = np.array(im)
            if anterior is not None and i < FUNDIDO:   # fundido con el final del tramo anterior
                k = (i + 1) / (FUNDIDO + 1)
                a = (a * k + anterior * (1 - k)).astype(np.uint8)
            vid.write(cv2.cvtColor(a, cv2.COLOR_RGB2BGR))
            anterior = np.array(im)
            total += 1
        print(f"  {nombre}: {(total - n0) / FPS:.1f} s")
    vid.release()
    print(f"✓ {salida} · {total / FPS:.1f} s")


if __name__ == "__main__":
    main()
