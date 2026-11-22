"""Imágenes de ejemplo del estéreo v2 con lo detectado dibujado encima, para revisarlas a ojo.

Pinta escenas de la mesa de montaje con las dos cámaras sintéticas (T, esquina, junta girada, chapa inclinada,
chapa tumbada en la zona libre), calibra el estéreo con fotos sintéticas del tablero como se haría con las webcams
reales, pasa el `SeguidorEstereo` y dibuja en cada cámara: ArUco detectados con su id, ejes de la base y de la
móvil con su pose estimada, el cordón (0 → 120 mm) de la junta reconocida, la punta triangulada (cruz) frente a la
verdad (círculo) con su altura sobre la chapa, y arriba la junta con su posición de soldeo, la confianza y el
motivo si está incompleta. Las de exposición baja se aclaran solo para verlas.

Uso: PYTHONPATH=. python herramientas/ver_estereo.py   →   salidas/estereo/*.png (a | b, una por escena)
"""
from pathlib import Path

import cv2
import numpy as np

from lewelder import contrato as c
from lewelder.escena_sintetica import EscenaSintetica
from lewelder.estereo import (
    TABLERO_EN_MESA,
    CalibracionEstereo,
    SeguidorEstereo,
    detectar_marcadores_v2,
)
from lewelder.juntas import (
    CENTRO_MOVIL,
    Pose,
    apoyada,
    marco_cordon,
    pose_base,
    pose_movil_montada,
    pose_movil_tumbada,
    punta_en_cordon,
    rot_x,
    rot_y,
    rot_z,
)

RAIZ = Path(__file__).resolve().parents[1]
SALIDA = RAIZ / "salidas" / "estereo"
AMARILLO, NARANJA, VERDE, ROJO, AZUL, BLANCO = (0, 220, 255), (255, 160, 0), (0, 255, 0), (0, 0, 255), (255, 0, 0), \
    (255, 255, 255)


def _aclarar(img):
    """Gamma para ver una imagen de exposición baja (solo visualización)."""
    if img.mean() > 60:
        return img.copy()
    tabla = (255 * (np.arange(256) / 255) ** 0.45).astype(np.uint8)
    return cv2.LUT(img, tabla)


def _p(uv):
    return tuple(int(np.round(v)) for v in uv)


def _ejes(vista, cam, pose: Pose, origen, largo=30.0):
    o, ex, ey, ez = cam.proyectar(pose.aplicar(np.array(origen) + np.vstack([np.zeros(3), np.eye(3) * largo])))
    for fin, col in ((ex, ROJO), (ey, VERDE), (ez, AZUL)):
        cv2.arrowedLine(vista, _p(o), _p(fin), col, 2, cv2.LINE_AA, tipLength=0.2)


def _ascii(texto: str) -> str:
    """Las fuentes de OpenCV no tienen tildes ni eñes."""
    return texto.translate(str.maketrans("áéíóúüñÁÉÍÓÚÑ°", "aeiouunAEIOUN*"))


def _texto(vista, lineas, x=12, y=28):
    for k, (linea, color) in enumerate(lineas):
        linea = _ascii(linea)
        pos = (x, y + 26 * k)
        cv2.putText(vista, linea, pos, cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 4, cv2.LINE_AA)
        cv2.putText(vista, linea, pos, cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2, cv2.LINE_AA)


def dibujar(img, cam, nombre, seguidor: SeguidorEstereo, verdad) -> np.ndarray:
    vista = _aclarar(img)
    for i, esq in detectar_marcadores_v2(img).items():
        cv2.polylines(vista, [np.round(esq).astype(np.int32)], True, NARANJA, 2)
        cv2.putText(vista, str(i), _p(esq[0] + [-4, -6]), cv2.FONT_HERSHEY_SIMPLEX, 0.5, NARANJA, 2)
    if seguidor.base is not None:
        _ejes(vista, cam, seguidor.base.pose, (0.0, 0.0, 0.0))
    if seguidor.movil is not None:
        _ejes(vista, cam, seguidor.movil.pose, CENTRO_MOVIL, 20.0)
    junta = seguidor.junta
    if junta.cordon is not None:
        cordon = cam.proyectar(junta.cordon.aplicar([(x, 0.0, 0.0) for x in np.linspace(0, c.LONGITUD_CORDON, 25)]))
        color = AMARILLO if junta.completa else (0, 120, 255)
        cv2.polylines(vista, [np.round(cordon).astype(np.int32)], False, color, 2, cv2.LINE_AA)
        cv2.circle(vista, _p(cordon[0]), 5, color, -1, cv2.LINE_AA)  # inicio del cordón
    lineas = [(f"camara {nombre}: {junta.nombre}  (confianza {junta.confianza:.2f})", BLANCO)]
    if junta.motivo and not junta.completa:
        lineas.append((junta.motivo, (0, 160, 255)))
    if verdad.led is not None:
        cv2.circle(vista, _p(cam.proyectar([verdad.led])[0]), 9, ROJO, 1, cv2.LINE_AA)
    if seguidor.punta is not None:
        u, v = cam.proyectar([seguidor.punta])[0]
        cv2.drawMarker(vista, _p((u, v)), VERDE, cv2.MARKER_CROSS, 18, 2, cv2.LINE_AA)
        if junta.cordon is not None:
            x, y, z = punta_en_cordon(seguidor.punta, junta)
            estado = "APOYADA" if apoyada(z) else "en el aire"
            error = np.linalg.norm(seguidor.punta - np.asarray(verdad.led)) if verdad.led is not None else np.nan
            lineas.append((f"punta x={x:.1f} y={y:.1f} z={z:.1f} mm ({estado}); error 3D {error:.2f} mm",
                           VERDE if apoyada(z) else BLANCO))
    elif verdad.led is not None:
        lineas.append(("LED: sin punta (no se ve en las dos camaras)", (0, 160, 255)))
    # Recorte ampliado x2 alrededor de la base (o del centro de la imagen) para ver la junta.
    centro = cam.proyectar([seguidor.base.pose.t])[0] if seguidor.base is not None else (640, 360)
    alto, ancho = vista.shape[:2]
    x0 = int(np.clip(centro[0] - ancho / 4, 0, ancho / 2))
    y0 = int(np.clip(centro[1] - alto / 4 - 30, 0, alto / 2))
    vista = cv2.resize(vista[y0:y0 + alto // 2, x0:x0 + ancho // 2], (ancho, alto), interpolation=cv2.INTER_LINEAR)
    _texto(vista, lineas)
    return vista


def escenas():
    base = pose_base()
    girada = pose_base(245.0, 15.0, 35.0)
    a_90 = pose_base(250.0, 0.0, 90.0)
    tumbada = pose_movil_tumbada(135.0, 195.0, 25.0)
    yield "t", base, pose_movil_montada(c.TipoJunta.T, base), (c.TipoJunta.T, (60.0, -2.0, 0.8))
    yield "esquina", base, pose_movil_montada(c.TipoJunta.ESQUINA, base), (c.TipoJunta.ESQUINA, (90.0, -2.0, 5.0))
    yield "t_girada_35", girada, pose_movil_montada(c.TipoJunta.T, girada), (c.TipoJunta.T, (100.0, -2.0, 1.0))
    yield "esquina_girada_90", a_90, pose_movil_montada(c.TipoJunta.ESQUINA, a_90), None
    yield "inclinada_12", base, pose_movil_montada(c.TipoJunta.T, base, inclinacion=-12.0), None
    yield "desplazada_9mm", base, pose_movil_montada(c.TipoJunta.ESQUINA, base, desplazamiento=(0, -9, 0)), None
    yield "tumbada_zona_libre", base, tumbada, None
    yield "sin_movil", base, None, None


def main():
    SALIDA.mkdir(parents=True, exist_ok=True)
    escena = EscenaSintetica(semilla=2)
    # Calibración como con las webcams reales: tablero sostenido en 16 poses y luego tumbado en la mesa.
    rng = np.random.default_rng(0)
    pares = []
    for _ in range(20):
        centro = np.array([c.POSICION_BASE.x + rng.uniform(0, 130), c.POSICION_BASE.y + rng.uniform(-70, 70),
                           rng.uniform(40, 160)])
        R = rot_z(90.0 + rng.uniform(-30, 30)) @ rot_x(180.0 + rng.uniform(15, 45)) @ rot_y(rng.uniform(-25, 25)) \
            @ rot_z(rng.uniform(-10, 10))
        pares.append(escena.renderizar_tablero(Pose(R, centro - R @ np.array([100.0, 62.5, 0.0]))))
    estereo = CalibracionEstereo.calibrar([a for a, _ in pares], [b for _, b in pares])
    error_mesa = estereo.calibrar_mesa_tablero(*escena.renderizar_tablero(TABLERO_EN_MESA))
    estereo.guardar(SALIDA / "calibracion_sintetica.json")
    print(f"calibración: estéreo {estereo.error_rms:.3f} px, mesa {error_mesa:.3f} px")
    cv2.imwrite(str(SALIDA / "tablero_a.png"), pares[0][0])
    cam_a, cam_b = estereo.camaras()
    for nombre, base, movil, punta in escenas():
        seguidor = SeguidorEstereo(estereo)
        img_a, img_b, verdad = escena.renderizar(base, movil)
        seguidor.procesar(img_a, img_b, 0.0)  # la junta se reconoce antes de encender el LED
        if punta is not None:
            tipo, p = punta
            img_a, img_b, verdad = escena.renderizar(base, movil, marco_cordon(tipo, base).aplicar(p))
            seguidor.procesar(img_a, img_b, 1 / 30)
        vista = np.hstack([dibujar(img_a, cam_a, "a", seguidor, verdad), dibujar(img_b, cam_b, "b", seguidor, verdad)])
        cv2.imwrite(str(SALIDA / f"{nombre}.png"), vista)
        print(f"{nombre}: {seguidor.junta.nombre}; {seguidor.junta.motivo or 'completa'}")
    print(f"imágenes en {SALIDA}")


if __name__ == "__main__":
    main()
