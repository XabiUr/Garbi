"""Manos de la persona vistas por la cámara de arriba (solución final, 20-11).

Una interfaz, `DetectorManos.detectar(img_top, cam) -> list[Mano]`, y dos implementaciones:

- `ManosMediaPipe`: MediaPipe Hands (robot real). Se importa al primer uso; si falta, dice cómo instalarlo.
- `ManosColor`: color de piel (simulación, y respaldo). Umbrales en `garbi/config_vision.yaml` (color `piel` y
  `parametros.manos`).

Cada `Mano` lleva el centro de la palma en la imagen (`uv`) y en la mesa (`xy`, proyectado a la altura de una palma
apoyada en el tapete, `manos.altura_palma`), y `en_tapete` si ese punto cae dentro del tapete. Una mano en el aire
(la que sujeta el taladro) queda proyectada más lejos de la cámara de lo que está; para saber si sujeta el taladro se
usa `distancia_mano_taladro`, que mide en la imagen (no depende de la altura de la mano).

Unidades: mm y píxeles; marco de la mesa.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Protocol

import cv2
import numpy as np

from garbi.config_vision import ConfigVision, cargar_config, config_por_defecto
from garbi.tipos import Mano

log = logging.getLogger(__name__)

# Modelo de MediaPipe Hands (tareas): se busca aquí, en $GARBI_MODELO_MANOS o en la ruta que se pase
MODELO_MANOS = Path(__file__).resolve().parent.parent / "calib" / "hand_landmarker.task"
URL_MODELO_MANOS = ("https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/"
                    "hand_landmarker.task")
PALMA = (0, 5, 9, 13, 17)  # puntos de MediaPipe que rodean la palma: muñeca y nudillos
# La mano que sujeta el taladro está a la altura del cuerpo y la empuñadura, no junto a la broca: la distancia se mide
# al tramo del eje que va de ALTURA_AGARRE_MIN sobre la punta hasta la bola. Así una mano apoyada en el tapete junto a
# la broca de un taladro dejado ahí no lo «agarra» (salvo que la cámara la vea justo detrás del cuerpo del taladro).
ALTURA_AGARRE_MIN = 135.0  # mm sobre la punta (broca + portabrocas)


class DetectorManos(Protocol):
    def detectar(self, img_top: np.ndarray, cam) -> list[Mano]: ...


def _tapete_mesa():
    from garbi.percepcion import esquinas_tapete_mesa

    return esquinas_tapete_mesa()


def en_tapete(xy) -> bool:
    """¿El punto (x, y) de la mesa cae dentro del tapete?"""
    poli = _tapete_mesa().astype(np.float32)
    return cv2.pointPolygonTest(poli, (float(xy[0]), float(xy[1])), False) >= 0


def mano_de_pixel(uv, cam, confianza: float = 1.0, fuente: str = "", cfg: ConfigVision | None = None) -> Mano:
    """`Mano` con la palma en el píxel `uv` de la cámara de arriba (`cam`: `garbi.percepcion.CamaraMesa`, o None si no
    está calibrada: entonces sin posición en la mesa)."""
    from garbi.percepcion import Z_TAPETE

    cfg = cfg or config_por_defecto()
    uv = np.asarray(uv, float)
    if cam is None:  # cámara sin calibrar (herramientas): solo el píxel
        return Mano(xy=np.full(2, np.nan), en_tapete=False, confianza=float(confianza), uv=uv, fuente=fuente)
    xy = cam.a_plano(uv[None], Z_TAPETE + float(cfg["manos"]["altura_palma"]))[0]
    return Mano(xy=xy, en_tapete=en_tapete(xy), confianza=float(confianza), uv=uv, fuente=fuente)


def distancia_mano_taladro(mano: Mano, cam, xy_taladro, z_arriba: float, z_abajo: float) -> float:
    """Distancia (mm) de la palma al eje del taladro, medida en la imagen.

    El eje se toma vertical por `xy_taladro` (el marcador, o la punta), de `z_abajo` (la punta) a `z_arriba` (la
    bola). Para cada punto del eje, la distancia en píxeles de la palma a su proyección se pasa a mm a la profundidad
    de ese punto (f / profundidad); se da la menor. Así una mano en el aire junto al taladro está cerca aunque su
    proyección al tapete caiga lejos, y una mano apoyada en el tapete lejos del taladro está lejos."""
    if mano.uv is None:
        return float(np.hypot(*(np.asarray(mano.xy) - np.asarray(xy_taladro)[:2])))
    zs = np.linspace(z_abajo, z_arriba, 25)
    pts = np.column_stack([np.full(25, xy_taladro[0]), np.full(25, xy_taladro[1]), zs])
    uv = cam.proyectar(pts)
    prof = (cam.R @ pts.T + cam.t[:, None])[2]
    d_px = np.linalg.norm(uv - np.asarray(mano.uv)[None, :], axis=1)
    return float(np.min(d_px * prof / cam.K[0, 0]))


def distancia_mano_taladro_escena(manos: list[Mano], cam, xy_taladro) -> float | None:
    """La menor distancia (mm) de una mano al cuerpo del taladro (eje vertical por `xy_taladro`, de ALTURA_AGARRE_MIN
    sobre la punta apoyada hasta la bola), o None si no hay manos. Ver `distancia_mano_taladro`."""
    from garbi.percepcion import Z_BOLA, Z_CARA

    if not manos or cam is None or xy_taladro is None:
        return None
    return min(distancia_mano_taladro(m, cam, xy_taladro, Z_BOLA, Z_CARA + ALTURA_AGARRE_MIN) for m in manos)


class ManosColor:
    """Manos por color de piel: manchas de piel de área razonable (sin la bola naranja). Simulación y respaldo."""

    def __init__(self, cfg=None):
        self.cfg = cargar_config(cfg) if cfg is not None else config_por_defecto()

    def detectar(self, img_top: np.ndarray, cam) -> list[Mano]:
        cfg = self.cfg
        hsv = cv2.cvtColor(img_top, cv2.COLOR_RGB2HSV)
        piel = cfg.mascara(hsv, "manos")
        bola = cv2.dilate(cfg.mascara(hsv, "bola"), np.ones((9, 9), np.uint8))
        piel &= ~bola
        piel = cv2.morphologyEx(piel, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
        # cierre grande: la sombra entre la palma y los dedos parte la mancha en dos
        piel = cv2.morphologyEx(piel, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (17, 17)))
        n, _, stats, centros = cv2.connectedComponentsWithStats(piel)
        lo, hi = cfg["manos"]["area"]
        manos = []
        for k in range(1, n):
            area = stats[k, cv2.CC_STAT_AREA]
            if lo <= area <= hi:
                manos.append(mano_de_pixel(centros[k], cam, min(1.0, area / (3.0 * lo)), "color", cfg))
        return manos


class ManosMediaPipe:
    """MediaPipe Hands (API de tareas, `HandLandmarker`) sobre la imagen de arriba. El centro de la palma es la media de
    la muñeca y los cuatro nudillos. Se carga al primer `detectar`.

    `modelo`: ruta al `hand_landmarker.task` (por defecto, $GARBI_MODELO_MANOS o `calib/hand_landmarker.task`)."""

    def __init__(self, modelo: str | os.PathLike | None = None, max_manos: int = 4, confianza_min: float = 0.4,
                 cfg=None):
        self.modelo = Path(modelo or os.environ.get("GARBI_MODELO_MANOS") or MODELO_MANOS)
        self.max_manos = max_manos
        self.confianza_min = confianza_min
        self.cfg = cargar_config(cfg) if cfg is not None else config_por_defecto()
        self._detector = None

    def _cargar(self):
        try:
            import mediapipe as mp
            from mediapipe.tasks.python import vision
            from mediapipe.tasks.python.core.base_options import BaseOptions
        except ImportError as e:
            raise ImportError(
                "ManosMediaPipe necesita MediaPipe: `pip install mediapipe` (o `uv pip install mediapipe`) en el .venv. "
                "Sin él, usa `ManosColor` (color de piel) como respaldo.") from e
        if not self.modelo.exists():
            raise FileNotFoundError(
                f"Falta el modelo de MediaPipe Hands en {self.modelo}. Descárgalo con:\n"
                f"  mkdir -p {self.modelo.parent} && curl -L -o {self.modelo} {URL_MODELO_MANOS}\n"
                "o indica otra ruta con $GARBI_MODELO_MANOS.")
        opciones = vision.HandLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=str(self.modelo)), num_hands=self.max_manos,
            min_hand_detection_confidence=self.confianza_min, min_hand_presence_confidence=self.confianza_min,
            running_mode=vision.RunningMode.IMAGE)
        self._mp = mp
        self._detector = vision.HandLandmarker.create_from_options(opciones)

    def detectar(self, img_top: np.ndarray, cam) -> list[Mano]:
        if self._detector is None:
            self._cargar()
        alto, ancho = img_top.shape[:2]
        imagen = self._mp.Image(image_format=self._mp.ImageFormat.SRGB, data=np.ascontiguousarray(img_top))
        res = self._detector.detect(imagen)
        manos = []
        for k, puntos in enumerate(res.hand_landmarks or []):
            uv = np.array([[puntos[i].x * ancho, puntos[i].y * alto] for i in PALMA]).mean(axis=0)
            conf = 1.0
            if res.handedness and k < len(res.handedness) and res.handedness[k]:
                conf = float(res.handedness[k][0].score)
            manos.append(mano_de_pixel(uv, cam, conf, "mediapipe", self.cfg))
        return manos

    def cerrar(self) -> None:
        if self._detector is not None:
            self._detector.close()
            self._detector = None


def crear_detector(tipo: str = "auto", cfg=None) -> DetectorManos:
    """"mediapipe", "color" o "auto" (MediaPipe si está instalado y con su modelo; si no, color)."""
    if tipo == "color":
        return ManosColor(cfg)
    if tipo == "mediapipe":
        return ManosMediaPipe(cfg=cfg)
    d = ManosMediaPipe(cfg=cfg)
    try:
        d._cargar()
        log.info("manos: MediaPipe (%s)", d.modelo)
        return d
    except (ImportError, FileNotFoundError, OSError, RuntimeError) as e:  # OSError: p. ej. falta libEGL
        log.warning("manos: sin MediaPipe (%s); uso el color de piel", str(e).splitlines()[0])
        return ManosColor(cfg)


def manos_verdad(mundo, cam) -> list[Mano]:
    """Las manos de la simulación según su verdad (para comparar): la del taladro y la libre, en el píxel donde se ve
    el centro de su palma. `cam`: `garbi.percepcion.CamaraMesa`."""
    out = []
    for p in (mundo.mano_taladro_en_mesa(), mundo.juez.mano_libre):
        if p is None:
            continue
        p = np.asarray(p, float).copy()
        if len(p) == 2:
            p = np.array([p[0], p[1], 0.0])
        uv = cam.proyectar(p[None])[0]
        m = mano_de_pixel(uv, cam, 1.0, "verdad")
        m.xy = p[:2]
        m.en_tapete = en_tapete(p[:2]) and p[2] < 60.0
        out.append(m)
    return out
