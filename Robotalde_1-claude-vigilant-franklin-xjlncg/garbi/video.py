"""Vídeo de la demo simulada de Garbi: cámara cenital y de muñeca lado a lado, con el estado y la aspiradora.

    python -m garbi.video --semilla 0 --salida salidas/garbi_demo.mp4 [--vision]

Con `--vision` la percepción es la de la cámara (`garbi.vision`) y se dibuja lo que ve: la tabla, la punta de la
broca y la viruta; sin él se usa el oráculo. Necesita render sin pantalla (MUJOCO_GL=egl u osmesa).
"""
from __future__ import annotations

import argparse
import logging
import unicodedata
from pathlib import Path

import cv2
import numpy as np

from garbi import contrato as g
from garbi.escenario import Fotograma, Informe, ejecutar

log = logging.getLogger("garbi.video")

COLOR_ESTADO = {  # BGR
    "aparcado": (160, 160, 160), "acercarse": (0, 200, 255), "acompañar": (0, 140, 255), "esperar": (0, 220, 220),
    "limpiar": (80, 220, 80), "aparcar": (200, 160, 60), "congelado": (40, 40, 230),
}


def _ascii(t: str) -> str:
    """Las fuentes de OpenCV no tienen tildes ni eñes."""
    t = t.replace("«", '"').replace("»", '"').replace("→", "->").replace("·", "-")
    return unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode()


def componer(f: Fotograma, titulo: str = "Garbi") -> np.ndarray:
    """Un fotograma del vídeo (BGR): cenital a la izquierda, muñeca y rótulos a la derecha."""
    cen = cv2.cvtColor(f.cenital, cv2.COLOR_RGB2BGR)
    alto = cen.shape[0]
    mun = cv2.cvtColor(f.muneca, cv2.COLOR_RGB2BGR)
    ancho_der = 360
    mun = cv2.resize(mun, (ancho_der, int(ancho_der * mun.shape[0] / mun.shape[1])))
    panel = np.full((alto, ancho_der, 3), 32, np.uint8)
    panel[: mun.shape[0]] = mun
    y = mun.shape[0] + 34
    fuente = cv2.FONT_HERSHEY_SIMPLEX

    def texto(t, color=(235, 235, 235), escala=0.6, grosor=1):
        nonlocal y
        cv2.putText(panel, _ascii(t), (12, y), fuente, escala, color, grosor, cv2.LINE_AA)
        y += int(30 * escala / 0.6)

    texto(titulo, (255, 255, 255), 0.8, 2)
    texto(f"t = {f.t:5.1f} s")
    texto(f"estado: {f.estado}", COLOR_ESTADO.get(f.estado, (255, 255, 255)), 0.7, 2)
    texto("aspiradora: " + ("ENCENDIDA" if f.aspiradora else "apagada"), (80, 220, 80) if f.aspiradora else (150, 150, 150))
    texto(f"viruta recogida: {f.recogidas}")
    for k in range(0, min(len(f.ultimo_evento), 120), 40):
        texto(f.ultimo_evento[k:k + 40], (200, 200, 120), 0.5)
    return np.hstack([cen, panel])


def escribir(informe: Informe, salida: Path, fps: float, titulo: str = "Garbi") -> Path:
    salida.parent.mkdir(parents=True, exist_ok=True)
    primero = componer(informe.fotogramas[0], titulo)
    vw = cv2.VideoWriter(str(salida), cv2.VideoWriter_fourcc(*"mp4v"), fps, (primero.shape[1], primero.shape[0]))
    for f in informe.fotogramas:
        vw.write(componer(f, titulo))
    vw.release()
    return salida


def demostraciones(n: int, semilla: int = 0) -> Informe:
    """Fotogramas de `n` demostraciones de limpieza (alternando las dos órdenes del VLA), como referencia de lo que
    tiene que hacer quien teleopere: qué orden, desde dónde empieza y cómo barre."""
    from garbi.demostraciones import ejecutar_episodio
    from garbi.mundo import MundoGarbi

    m = MundoGarbi(render=True)
    inf = Informe()
    for i in range(n):
        orden = g.ORDENES_VLA[i % len(g.ORDENES_VLA)]

        def guardar(obs, accion, i=i, orden=orden):
            if int(round(m.t * g.FPS)) % 2 == 0:
                inf.fotogramas.append(Fotograma(m.t, m.imagen("top", g.RESOLUCION_VISION),
                                                obs["observation.images.wrist"], f"demo {i + 1}/{n}", True,
                                                m.recogidas, f"«{orden}»"))

        ejecutar_episodio(m, orden, semilla + i, guardar)
    return inf


def main(argv=None) -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--semilla", type=int, default=0)
    p.add_argument("--salida", type=Path, default=Path("salidas/garbi_demo.mp4"))
    p.add_argument("--vision", action="store_true", help="percepción por cámara en vez del oráculo")
    p.add_argument("--inclinacion", type=float, default=0.0, help="grados que el juez inclina el taladro")
    p.add_argument("--cada", type=int, default=2, help="guardar uno de cada N fotogramas")
    p.add_argument("--demostraciones", type=int, default=0,
                   help="en vez del ciclo, N demostraciones de limpieza (lo que debe aprender el VLA)")
    a = p.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    if a.demostraciones:
        inf = demostraciones(a.demostraciones, a.semilla)
        escribir(inf, a.salida, g.FPS / 2, "Garbi - demos del VLA")
        log.info("vídeo: %s (%d fotogramas)", a.salida, len(inf.fotogramas))
        return
    percepcion = None
    if a.vision:
        from garbi.vision import PercepcionVision
        percepcion = PercepcionVision
    inf = ejecutar(a.semilla, render=True, grabar=True, percepcion=percepcion, cada=a.cada, inclinacion=a.inclinacion)
    titulo = "Garbi · " + ("visión" if a.vision else "oráculo") + (f" · {a.inclinacion:.0f}°" if a.inclinacion else "")
    escribir(inf, a.salida, g.FPS / a.cada, titulo)
    log.info("vídeo: %s (%d fotogramas, %.1f s simulados) · boca-broca %.1f mm · error arriba %.1f / apunto %.1f mm · "
             "agujero %d→%d · alfombrilla %d→%d", a.salida, len(inf.fotogramas), inf.duracion, inf.distancia_boca_broca,
             inf.error_camara_arriba, inf.error_apunto, inf.viruta_agujero_tras_taladrar, inf.viruta_agujero_al_final,
             inf.viruta_alfombrilla_inicial, inf.viruta_alfombrilla_final)


if __name__ == "__main__":
    main()
