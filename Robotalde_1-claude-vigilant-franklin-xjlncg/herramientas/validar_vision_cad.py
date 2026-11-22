"""Validación de la visión con la geometría real del CAD antes de imprimir (tarea 1 del plan v2).

Pinta la base y la chapa móvil con las mallas STL de `hardware/v2/cad/stl` (ranura, tope, aleta, chaflanes y los
rebajes de 0,3 mm de las pegatinas) desde las dos webcams, en T y en esquina con la base girada y con la chapa tumbada
en la zona libre, y mide para cada ArUco (30, 40, 41) y cada cámara:

- si se ve (sin tapar y de cara) y si OpenCV lo detecta (varias realizaciones de ruido, exposición baja);
- su tamaño en la imagen (lado más corto del cuadro negro, px) y el ángulo entre su normal y la cámara;

y si la escuela reconoce la junta (`SeguidorEstereo` con la calibración exacta). Compara las poses de cámara del
contrato (`CAMARAS_ESTEREO`) con las anteriores (validadas con la mesa antigua).

Uso: PYTHONPATH=. python herramientas/validar_vision_cad.py [--repeticiones 4]
     [--fov 78] [--resolucion 1920x1080]
     → salidas/estereo/validacion_tablas_<alto>p_fov<fov>.md y salidas/estereo/cad_*.png
"""
import argparse
from pathlib import Path

import cv2
import numpy as np

from lewelder import contrato as c
from lewelder.escena_sintetica import EscenaSintetica, pose_camara_estereo
from lewelder.estereo import CalibracionEstereo, SeguidorEstereo, detectar_marcadores_v2
from lewelder.juntas import (
    MARCADORES,
    EstadoJunta,
    esquinas_marcador,
    pose_base,
    pose_movil_montada,
    pose_movil_tumbada,
)

RAIZ = Path(__file__).resolve().parents[1]
SALIDA = RAIZ / "salidas" / "estereo"
IDS = (c.ID_BASE, c.IDS_MOVIL["cara_aleta"], c.IDS_MOVIL["cara_lisa"])


def escenas():
    for giro in (0.0, 30.0, -30.0, 60.0, -60.0, 90.0, 180.0):
        base = pose_base(giro=giro)
        for tipo in c.TipoJunta:
            yield f"{tipo.value} giro {giro:+.0f}", base, pose_movil_montada(tipo, base), tipo.value
    zl = c.ZONA_LIBRE
    # El centro de la chapa en las cuatro esquinas y en el centro de la zona libre, con giros de -60° a 60°.
    for x, y, g in ((zl["x"][0], zl["y"][0], 0.0), (np.mean(zl["x"]), np.mean(zl["y"]), 45.0),
                    (zl["x"][1], zl["y"][1], -60.0), (zl["x"][1], zl["y"][0], 60.0), (zl["x"][0], zl["y"][1], -30.0)):
        yield f"tumbada ({x:.0f}, {y:.0f}) {g:+.0f}°", pose_base(), pose_movil_tumbada(x, y, g), "incompleta"


def medir(cam, pose, id_aruco):
    """(lado mínimo en px del cuadro negro, ángulo de visión en grados) del marcador."""
    m = MARCADORES[id_aruco]
    esq = pose.aplicar(esquinas_marcador(id_aruco))
    uv = cam.proyectar(esq)
    lado = min(np.linalg.norm(uv[i] - uv[(i + 1) % 4]) for i in range(4))
    n = pose.R @ m.normal
    rayo = cam.centro - esq.mean(axis=0)
    angulo = np.degrees(np.arccos(np.clip(n @ rayo / np.linalg.norm(rayo), -1, 1)))
    return lado, angulo


# Las del contrato antes de cambiar la mesa (base en (250, 0), zona libre a la derecha del robot), para comparar.
ANTERIORES = {k: {"altura": 500.0, "inclinacion": 45.0, "azimut": az, "objetivo": (230.0, -80.0, 16.0)}
              for k, az in (("a", -35.0), ("b", 35.0))}


def matriz_k(fov: float, ancho: int = 1280, alto: int = 720) -> np.ndarray:
    f = (ancho / 2) / np.tan(np.radians(fov) / 2)
    return np.array([[f, 0, (ancho - 1) / 2], [0, f, (alto - 1) / 2], [0, 0, 1]])


def validar(nombre_config, poses, repeticiones, exposicion, fov, ancho=1280, alto=720):
    escena = EscenaSintetica({n: pose_camara_estereo(n, poses) for n in "ab"}, ancho=ancho, alto=alto,
                             K=matriz_k(fov, ancho, alto), semilla=4, geometria="cad")
    estereo = CalibracionEstereo.desde_escena(escena)
    cams = dict(zip("ab", estereo.camaras()))
    filas, resumen = [], {"juntas": [0, 0], "ids": {}}
    for nombre, base, movil, esperado in escenas():
        celdas, aciertos = [], 0
        for k in range(repeticiones):
            img_a, img_b, verdad = escena.renderizar(base, movil, exposicion=exposicion)
            det = {"a": detectar_marcadores_v2(img_a), "b": detectar_marcadores_v2(img_b)}
            _, junta = SeguidorEstereo(estereo).procesar(img_a, img_b, 0.0)
            ok = junta.tipo == EstadoJunta(esperado)
            aciertos += ok
            if k == 0:
                for n in "ab":
                    for i in IDS:
                        pose = base if i == c.ID_BASE else movil
                        lado, ang = medir(cams[n], pose, i)
                        visible = i in verdad.marcadores_visibles[n]
                        celdas.append([n, i, visible, 0, lado, ang])
                if "giro +0" in nombre or "tumbada" in nombre and "+45" in nombre:
                    vista = np.hstack([img_a, img_b])
                    nombre_png = nombre.replace(" ", "_").replace("(", "").replace(")", "").replace(",", "")
                    cv2.imwrite(str(SALIDA / f"cad_{nombre_config}_{escena.alto}p_{nombre_png.replace('°', '')}.png"), vista)
            for celda in celdas:
                celda[3] += celda[1] in det[celda[0]]
        resumen["juntas"][0] += aciertos
        resumen["juntas"][1] += repeticiones
        texto = []
        for n, i, visible, detectado, lado, ang in celdas:
            if not visible:
                texto.append(f"{n}:{i} —")
                continue
            texto.append(f"{n}:{i} {detectado}/{repeticiones} ({lado:.0f} px, {ang:.0f}°)")
            r = resumen["ids"].setdefault(i, [0, 0])
            r[0] += detectado
            r[1] += repeticiones
        filas.append(f"| {nombre} | {' · '.join(texto)} | {junta.tipo.value} {aciertos}/{repeticiones} |")
    return filas, resumen


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repeticiones", type=int, default=4)
    parser.add_argument("--exposicion", default="baja")
    parser.add_argument("--fov", type=float, default=78.0, help="FOV horizontal de la webcam")
    parser.add_argument("--resolucion", default="1280x720")
    args = parser.parse_args()
    SALIDA.mkdir(parents=True, exist_ok=True)
    ancho, alto = (int(v) for v in args.resolucion.split("x"))
    salida = [(f"Webcam {args.resolucion} con FOV horizontal de {args.fov:.0f}°. Exposición {args.exposicion}, "
               f"{args.repeticiones} realizaciones de ruido por escena. Celda: cámara:id detectado/repeticiones (lado "
               "mínimo del cuadro negro en px, ángulo de visión); — = no se ve (tapado o de espaldas).\n")]
    for nombre, poses in (("contrato", c.CAMARAS_ESTEREO), ("anteriores", ANTERIORES)):
        filas, resumen = validar(nombre, poses, args.repeticiones, args.exposicion, args.fov, ancho, alto)
        ids = ", ".join(f"{i}: {d}/{t}" for i, (d, t) in sorted(resumen["ids"].items()))
        j = resumen["juntas"]
        salida += [f"\n### Cámaras {nombre}\n", (f"Detección cuando se ve: {ids}. Juntas bien reconocidas: "
                                                   f"{j[0]}/{j[1]}.\n"), "| Escena | ArUco por cámara | Junta reconocida |", "|---|---|---|", *filas]
        print(f"{nombre}: detección {ids}; juntas {j[0]}/{j[1]}")
    (SALIDA / f"validacion_tablas_{alto}p_fov{args.fov:.0f}.md").write_text("\n".join(salida) + "\n", encoding="utf-8")
    print(f"tablas en {SALIDA}")


if __name__ == "__main__":
    main()
