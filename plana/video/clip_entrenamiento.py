#!/usr/bin/env python3
"""
clip_entrenamiento.py - Monta un clip para el vídeo con episodios REALES del dataset de entrenamiento.

Lee el dataset LeRobot local (por defecto Xaflas/taladro-fijo, en ~/.cache/huggingface/lerobot) y junta las dos
cámaras (superior y muñeca) lado a lado a 1920×1080, con un rótulo. Los vídeos del dataset están en AV1: se leen
con PyAV.

    python video/clip_entrenamiento.py                       # episodios 20 y 90 → video/clips/entrenamiento.mp4
    python video/clip_entrenamiento.py --episodios 5 40 100
"""

import argparse
import glob
import os

import av
import cv2
import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont

AQUI = os.path.dirname(os.path.abspath(__file__))
DATASET = os.path.expanduser("~/.cache/huggingface/lerobot/Xaflas/taladro-fijo")
ANCHO, ALTO, FPS = 1920, 1080, 30
FUENTE = "/System/Library/Fonts/HelveticaNeue.ttc"


def fotogramas(dataset: str, ep: pd.Series, camara: str):
    """Fotogramas RGB del episodio `ep` en la cámara `camara` ("front" | "gripper")."""
    k = f"videos/observation.images.{camara}"
    ruta = os.path.join(dataset, "videos", f"observation.images.{camara}",
                        f"chunk-{int(ep[k + '/chunk_index']):03d}", f"file-{int(ep[k + '/file_index']):03d}.mp4")
    t0, t1 = float(ep[k + "/from_timestamp"]), float(ep[k + "/to_timestamp"])
    with av.open(ruta) as c:
        s = c.streams.video[0]
        c.seek(int(t0 / s.time_base), stream=s, backward=True)
        out = []
        for f in c.decode(s):
            t = float(f.pts * s.time_base)
            if t < t0 - 1e-3:
                continue
            if t >= t1 - 1e-3:
                break
            out.append(f.to_ndarray(format="rgb24"))
        return out


def rotulos(n_ep: int) -> Image.Image:
    capa = Image.new("RGBA", (ANCHO, ALTO), (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    f1 = ImageFont.truetype(FUENTE, 46, index=1)
    f2 = ImageFont.truetype(FUENTE, 30)
    d.text((48, 40), "Episodios reales del entrenamiento (ACT)", font=f1, fill=(255, 255, 255))
    d.text((48, 905), "Cámara superior", font=f2, fill=(148, 230, 220))
    d.text((1296, 640), "Cámara de la muñeca", font=f2, fill=(148, 230, 220))
    d.text((1296, 700), "El brazo aprende a llevar la boquilla\njunto a la broca, imitando las\ndemostraciones grabadas.",
           font=f2, fill=(203, 213, 225), spacing=10)
    d.text((1296, 860), f"Episodio {n_ep}", font=f2, fill=(148, 163, 184))
    return capa


def main():
    ap = argparse.ArgumentParser(description="Clip con episodios del dataset de entrenamiento")
    ap.add_argument("--dataset", default=DATASET)
    ap.add_argument("--episodios", type=int, nargs="+", default=[20, 90])
    ap.add_argument("--salida", default=os.path.join(AQUI, "clips", "entrenamiento.mp4"))
    args = ap.parse_args()

    eps = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(f"{args.dataset}/meta/episodes/*/*.parquet"))])
    eps = eps.set_index("episode_index")
    os.makedirs(os.path.dirname(args.salida), exist_ok=True)
    vid = cv2.VideoWriter(args.salida, cv2.VideoWriter_fourcc(*"avc1"), FPS, (ANCHO, ALTO))
    total = 0
    for n in args.episodios:
        ep = eps.loc[n]
        sup, mun = fotogramas(args.dataset, ep, "front"), fotogramas(args.dataset, ep, "gripper")
        capa = rotulos(n)
        for i in range(min(len(sup), len(mun))):
            lienzo = Image.new("RGB", (ANCHO, ALTO), (15, 23, 42))
            lienzo.paste(Image.fromarray(sup[i]).resize((1216, 684)), (48, 120))     # 16:9
            lienzo.paste(Image.fromarray(mun[i]).resize((576, 432)), (1296, 120))    # 4:3
            lienzo.paste(capa, (0, 0), capa)
            vid.write(cv2.cvtColor(np.array(lienzo), cv2.COLOR_RGB2BGR))
            total += 1
        print(f"  episodio {n}: {min(len(sup), len(mun)) / FPS:.1f} s")
    vid.release()
    print(f"✓ {args.salida} ({total / FPS:.1f} s)")


if __name__ == "__main__":
    main()
