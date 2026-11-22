"""Piezas comunes de las herramientas del sitio de Garbi (cámaras, ventanas, mover el brazo despacio, confirmar).

No es una herramienta: la importan `garbi_camaras.py`, `garbi_ajustar_color.py`, `garbi_calibrar.py`,
`garbi_teleop_grabar.py` y `garbi_probar_robot.py`. Funciona igual en Windows (COMx, índices de cámara, DirectShow)
y en Linux (/dev/ttyACM0, /dev/videoN o índices).
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from garbi.tipos import forzar_montaje  # noqa: E402

VELOCIDAD_LENTA = 20.0  # °/s: para ir a posturas de prueba o de calibración
HZ = 30.0
TOLERANCIA_LLEGADA = 2.5  # ° en las 5 primeras articulaciones (la pinza no cuenta)
ESPERA_LLEGADA = 3.0  # s como mucho esperando a que pare tras la rampa


class Ayuda(argparse.RawDescriptionHelpFormatter, argparse.ArgumentDefaultsHelpFormatter):
    """`--help` con el texto del módulo tal cual y los valores por defecto."""


def fuente_camara(texto) -> int | str:
    """"0" → 0 (índice, Windows o Linux); "/dev/video2" se deja como ruta."""
    texto = str(texto)
    return int(texto) if texto.isdigit() else texto


def anadir_camaras(p: argparse.ArgumentParser) -> None:
    p.add_argument("--top", default="0", help="índice (0, 1, ...) o ruta (/dev/videoN) de la cámara de arriba")
    p.add_argument("--wrist", default="1", help="índice o ruta de la cámara de la muñeca")
    p.add_argument("--exposicion", type=float, default=15.6, help="exposición fija en ms (C920 con flexo: 15,6)")
    p.add_argument("--balance", type=int, default=4000, help="balance de blancos fijo (K)")
    p.add_argument("--foco", type=int, default=0, help="foco fijo (0 = infinito en la C920)")


def anadir_robot(p: argparse.ArgumentParser, obligatorio: bool = True) -> None:
    p.add_argument("--puerto", required=obligatorio,
                   help="puerto serie del follower: COM5 (Windows) o /dev/ttyACM0 (Linux); lerobot-find-port lo dice")
    p.add_argument("--id", default="garbi", help="id de la calibración de LeRobot del follower")


def ajustes_desde(ns):
    from garbi.real import AjustesCamara

    return AjustesCamara(exposicion_ms=ns.exposicion, balance_k=ns.balance, foco=ns.foco)


def camaras_desde(ns, cuales=("top", "wrist")) -> dict:
    return {c: fuente_camara(getattr(ns, c)) for c in cuales if getattr(ns, c, None) not in (None, "", "no")}


# --- mover el brazo despacio ---------------------------------------------------------------------------------------
def rampa(q_inicio, q_fin, velocidad: float = VELOCIDAD_LENTA, hz: float = HZ) -> list[np.ndarray]:
    """Posturas intermedias de q_inicio a q_fin a `velocidad` °/s (la articulación que más se mueve marca el paso).
    Muñeca a 0 y pinza cerrada en todas."""
    a, b = forzar_montaje(q_inicio), forzar_montaje(q_fin)
    paso = velocidad / hz
    n = max(1, int(np.ceil(np.max(np.abs(b - a)) / paso)))
    return [a + (b - a) * (k / n) for k in range(1, n + 1)]


def error_postura(q, objetivo) -> float:
    """Máximo error (°) en las 5 primeras articulaciones."""
    return float(np.max(np.abs(np.asarray(q, float)[:5] - np.asarray(objetivo, float)[:5])))


def mover_despacio(cuerpo, objetivo, velocidad: float = VELOCIDAD_LENTA, hz: float = HZ, dormir=time.sleep,
                   tolerancia: float = TOLERANCIA_LLEGADA, espera_max: float = ESPERA_LLEGADA, reloj=time.monotonic
                   ) -> float:
    """Lleva el `Cuerpo` a `objetivo` (grados de LeRobot) despacio y espera a que llegue. Devuelve el error final (°).
    Si se pulsa Ctrl+C, el brazo se queda quieto donde está y se relanza el `KeyboardInterrupt`."""
    objetivo = forzar_montaje(objetivo)
    try:
        for q in rampa(cuerpo.q(), objetivo, velocidad, hz):
            cuerpo.enviar(q)
            dormir(1.0 / hz)
        t0 = reloj()
        while True:
            err = error_postura(cuerpo.q(), objetivo)
            if err <= tolerancia or reloj() - t0 >= espera_max:
                return err
            cuerpo.enviar(objetivo)
            dormir(1.0 / hz)
    except KeyboardInterrupt:
        parar_quieto(cuerpo)
        raise


def parar_quieto(cuerpo) -> None:
    """El brazo se queda donde está (objetivo = postura actual)."""
    try:
        if hasattr(cuerpo, "quieto"):
            cuerpo.quieto()
        else:
            cuerpo.enviar(cuerpo.q())
    except Exception as e:  # al parar no puede saltar otra excepción
        print(f"(no he podido parar el brazo: {e})")


def confirmar(texto: str, entrada=input) -> bool:
    """Enter para seguir; «n» o «q» para no. Ctrl+C se propaga."""
    r = entrada(f"{texto} [Enter = sí, n = no] ").strip().lower()
    return r not in ("n", "no", "q")


# --- dibujo ------------------------------------------------------------------------------------------------------
COLORES_BGR = {  # para pintar cada color del yaml en las ventanas
    "tapete_azul": (255, 120, 0), "madera": (80, 180, 230), "bola_naranja": (0, 140, 255),
    "anillo_verde": (60, 255, 60), "piel": (180, 160, 255), "pegatina": (255, 0, 255),
}


def a_bgr(img_rgb: np.ndarray) -> np.ndarray:
    return np.ascontiguousarray(img_rgb[..., ::-1])


def superponer(img_bgr: np.ndarray, mascara: np.ndarray, color_bgr, alfa: float = 0.45) -> np.ndarray:
    """Tiñe de `color_bgr` los píxeles de la máscara (en el sitio) y devuelve la imagen."""
    m = mascara > 0
    if np.any(m):
        img_bgr[m] = (img_bgr[m] * (1 - alfa) + np.array(color_bgr, float) * alfa).astype(np.uint8)
    return img_bgr


def rotulo(img_bgr: np.ndarray, lineas, origen=(8, 20), color=(255, 255, 255), escala: float = 0.5) -> np.ndarray:
    """Texto con fondo oscuro, una línea debajo de otra."""
    import cv2

    x, y = origen
    for linea in lineas:
        (w, h), _ = cv2.getTextSize(linea, cv2.FONT_HERSHEY_SIMPLEX, escala, 1)
        cv2.rectangle(img_bgr, (x - 3, y - h - 4), (x + w + 3, y + 4), (0, 0, 0), -1)
        cv2.putText(img_bgr, linea, (x, y), cv2.FONT_HERSHEY_SIMPLEX, escala, color, 1, cv2.LINE_AA)
        y += h + 10
    return img_bgr


def mosaico(imagenes: list[np.ndarray], alto: int = 480) -> np.ndarray:
    """Imágenes BGR lado a lado, a la misma altura."""
    import cv2

    filas = []
    for img in imagenes:
        if img.shape[0] != alto:
            img = cv2.resize(img, (int(img.shape[1] * alto / img.shape[0]), alto))
        filas.append(img)
    return np.hstack(filas)


def comprobar_ventanas() -> None:
    """OpenCV sin GUI (opencv-python-headless) no puede abrir ventanas: se avisa con el remedio."""
    import cv2

    try:
        cv2.namedWindow("garbi_prueba", cv2.WINDOW_NORMAL)
        cv2.destroyWindow("garbi_prueba")
    except cv2.error as e:
        raise SystemExit("OpenCV no puede abrir ventanas (¿opencv-python-headless?). Arreglo:\n"
                         "  pip uninstall -y opencv-python-headless opencv-python && pip install opencv-python\n"
                         f"({e})") from None
