"""Imágenes de ejemplo del seguimiento con lo detectado dibujado encima, para revisarlas a ojo.

Pinta escenas con la cámara sintética, pasa el seguimiento y dibuja: ArUco detectados con su id, ejes de la pieza,
el cordón (0 → 120 mm) proyectado con la pose estimada, el LED detectado (cruz verde) frente a la verdad (círculo
rojo) y el punto en el marco de la pieza con su error. Las de exposición baja se aclaran solo para verlas.

Uso: PYTHONPATH=. python herramientas/ver_seguimiento.py   →   salidas/seguimiento/*.png
"""
from pathlib import Path

import cv2
import numpy as np

from lewelder import contrato as c
from lewelder.camara_sintetica import CamaraSintetica
from lewelder.seguimiento import (
    ALTURA_PLANO_PIEZA,
    Seguidor,
    detectar_led,
    detectar_marcadores,
    estimar_pose_mesa,
    estimar_pose_pieza,
    punto_en_pieza,
)

RAIZ = Path(__file__).resolve().parents[1]
SALIDA = RAIZ / "salidas" / "seguimiento"


def _proyectar(pose, calib, puntos_pieza):
    rvec = cv2.Rodrigues(pose.R)[0]
    uv, _ = cv2.projectPoints(np.asarray(puntos_pieza, np.float64), rvec, pose.t, calib.K, calib.dist)
    return uv.reshape(-1, 2)


def _aclarar(img):
    """Gamma para ver una imagen de exposición baja (solo visualización)."""
    if img.mean() > 60:
        return img.copy()
    tabla = (255 * (np.arange(256) / 255) ** 0.45).astype(np.uint8)
    return cv2.LUT(img, tabla)


def dibujar(img, calib, verdad=None, rastro=None):
    vista = _aclarar(img)
    marcadores = detectar_marcadores(img, calib)
    mesa = estimar_pose_mesa(marcadores, calib)
    pose = estimar_pose_pieza(marcadores, calib, mesa)
    for i, esq in marcadores.items():
        cv2.polylines(vista, [np.round(esq).astype(np.int32)], True, (255, 160, 0), 2)
        cv2.putText(vista, str(i), tuple(np.round(esq[0]).astype(int) + [-4, -6]), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                    (255, 160, 0), 2)
    texto = []
    if pose is not None:
        cordon = _proyectar(pose, calib, [(x, 0.0, 0.0) for x in np.linspace(0, c.LONGITUD_CORDON, 25)])
        cv2.polylines(vista, [np.round(cordon).astype(np.int32)], False, (0, 200, 255), 2, cv2.LINE_AA)
        o, ex, ey, ez = _proyectar(pose, calib, [(0, 0, 0), (30, 0, 0), (0, 30, 0), (0, 0, 30)])
        for fin, col in ((ex, (0, 0, 255)), (ey, (0, 255, 0)), (ez, (255, 0, 0))):
            cv2.arrowedLine(vista, tuple(np.round(o).astype(int)), tuple(np.round(fin).astype(int)), col, 2,
                            cv2.LINE_AA, tipLength=0.2)
        texto.append(f"pieza {pose.tipo.value} id {pose.id_aruco} anclaje {pose.anclaje} ({pose.metodo})")
        if mesa is not None:
            texto.append(f"mesa: {mesa.n_marcadores} ArUco de anclaje, reproyeccion {mesa.error_px:.2f} px")
    if rastro:
        pts = _proyectar(pose, calib, rastro)
        cv2.polylines(vista, [np.round(pts).astype(np.int32)], False, (255, 0, 255), 2, cv2.LINE_AA)
    led = detectar_led(img)
    if verdad is not None and verdad.pixel_led is not None:
        cv2.circle(vista, tuple(np.round(verdad.pixel_led).astype(int)), 12, (0, 0, 255), 1, cv2.LINE_AA)
    if led is not None:
        u, v, brillo = led
        cv2.drawMarker(vista, (int(round(u)), int(round(v))), (0, 255, 0), cv2.MARKER_CROSS, 30, 1, cv2.LINE_AA)
        linea = f"LED ({u:.1f}, {v:.1f}) px, brillo {brillo:.0f}"
        if pose is not None:
            p = punto_en_pieza(u, v, pose, calib)
            linea += f" -> pieza ({p[0]:.1f}, {p[1]:.1f}, {p[2]:.1f}) mm"
            if verdad is not None and verdad.led is not None:
                linea += f", error {np.hypot(p[0] - verdad.led[0], p[1] - verdad.led[1]):.2f} mm"
        texto.append(linea)
    else:
        texto.append("LED: no se ve")
    for k, t in enumerate(texto):
        cv2.putText(vista, t, (12, 26 + 24 * k), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 4, cv2.LINE_AA)
        cv2.putText(vista, t, (12, 26 + 24 * k), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA)
    return vista


def main():
    SALIDA.mkdir(parents=True, exist_ok=True)
    camara = CamaraSintetica(semilla=4)
    calib = camara.calibracion()
    escenas = {
        "1_recta_A_baja": dict(tipo="recta", anclaje="A", led=(35.0, 1.0, c.ALTURA_PUNTA)),
        "2_t_B_normal_reflejos": dict(tipo="t", anclaje="B", led=(60.0, -3.0, c.ALTURA_PUNTA),
                                      exposicion="normal", reflejo=True),
        "3_recta_D_desfase": dict(tipo="recta", anclaje="D", led=(100.0, -2.0, c.ALTURA_PUNTA),
                                  desfase=(2.0, -1.5, 2.0)),
        "4_t_D_led_tapado_por_el_alma": dict(tipo="t", anclaje="D", led=(60.0, -2.0, c.ALTURA_PUNTA),
                                             exposicion="normal"),
    }
    for nombre, escena in escenas.items():
        img, verdad = camara.renderizar(**escena)
        cv2.imwrite(str(SALIDA / f"{nombre}.png"), dibujar(img, calib, verdad))

    # Una pasada simulada (con temblor) por el Seguidor: el rastro filtrado se dibuja sobre el último fotograma.
    seguidor, rastro, rng = Seguidor(calib), [], np.random.default_rng(0)
    for i in range(150):  # 5 s a 30 fps, de x = 10 a x = 110 mm (más rápido que un alumno, para verlo entero)
        t = i / 30
        led = (10.0 + 20.0 * t, 2.0 * np.sin(t * 3) + rng.normal(0, 0.3), c.ALTURA_PUNTA)
        img, verdad = camara.renderizar("recta", "C", led=led)
        m = seguidor.procesar(img, t)
        if m is not None:
            rastro.append((m.x, m.y, 0.0))
    cv2.imwrite(str(SALIDA / "5_pasada_recta_C.png"), dibujar(img, calib, verdad, rastro))
    print(f"Imágenes en {SALIDA} (plano de la pieza a Z = {ALTURA_PLANO_PIEZA} mm de la mesa)")


if __name__ == "__main__":
    main()
