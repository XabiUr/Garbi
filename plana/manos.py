#!/usr/bin/env python3
"""
manos.py - Detecta manos con MediaPipe (HandLandmarker) en la cámara "front". Para seguridad de los barridos.

- Modelo: modelos/hand_landmarker.task (dentro de plana: no depende de otras carpetas).
- Solo cuentan las manos dentro del área de trabajo (las 4 esquinas que se le den, ampliadas con `margen`).
- Persistencia: hay_manos pasa a True tras verse `t_on` s seguidos y vuelve a False tras `t_off` s sin verlas
  (así un parpadeo de la detección no para ni arranca nada).

detectar(img_rgb, t) -> dict: hay_manos, n (manos en este fotograma), manos [(cx, cy, puntos px)], ms (tiempo)

Prueba: python manos.py [--camara N]   (dibuja las manos; Q para salir)
"""

import os
import time
from typing import Dict, List, Optional

os.environ.setdefault("GLOG_minloglevel", "2")   # MediaPipe es muy hablador

import cv2
import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
MODELO = os.path.join(AQUI, "modelos", "hand_landmarker.task")

POR_DEFECTO = {
    "confianza_min": 0.45,   # confianza mínima de detección de MediaPipe
    "max_manos": 4,
    "margen": 0.15,          # ampliación del área de trabajo (fracción de su tamaño) para contar una mano
    "t_on": 0.2,             # s seguidos viendo una mano para darla por presente
    "t_off": 0.5,            # s sin verla para darla por ida
}


class DetectorManos:
    def __init__(self, config: Optional[dict] = None, esquinas_area: Optional[np.ndarray] = None,
                 modelo: str = MODELO):
        import mediapipe as mp
        from mediapipe.tasks.python import BaseOptions, vision
        self.mp = mp
        self.p = {**POR_DEFECTO, **((config or {}).get("manos", {}))}
        if not os.path.exists(modelo):
            raise FileNotFoundError(f"Falta el modelo de manos: {modelo}")
        opciones = vision.HandLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=modelo), num_hands=int(self.p["max_manos"]),
            min_hand_detection_confidence=float(self.p["confianza_min"]),
            min_hand_presence_confidence=float(self.p["confianza_min"]),
            running_mode=vision.RunningMode.IMAGE)
        self.det = vision.HandLandmarker.create_from_options(opciones)
        self.area = None
        if esquinas_area is not None:
            e = np.asarray(esquinas_area, np.float32).reshape(4, 2)
            c = e.mean(axis=0)
            self.area = (c + (e - c) * (1 + float(self.p["margen"]))).astype(np.float32)
        self.hay_manos = False
        self._t_cambio = None
        self.ultimo = {"hay_manos": False, "n": 0, "manos": [], "ms": 0.0}

    def _dentro(self, x: float, y: float) -> bool:
        return self.area is None or cv2.pointPolygonTest(self.area, (float(x), float(y)), False) >= 0

    def detectar(self, img_rgb: np.ndarray, t: Optional[float] = None) -> Dict:
        t = time.time() if t is None else t
        t0 = time.perf_counter()
        h, w = img_rgb.shape[:2]
        r = self.det.detect(self.mp.Image(image_format=self.mp.ImageFormat.SRGB, data=np.ascontiguousarray(img_rgb)))
        manos: List = []
        for puntos in r.hand_landmarks:
            px = np.array([[p.x * w, p.y * h] for p in puntos])
            cx, cy = px[[0, 5, 9, 13, 17]].mean(axis=0)   # centro de la palma
            if self._dentro(cx, cy):
                manos.append((float(cx), float(cy), px))
        vista = len(manos) > 0
        # persistencia
        if vista == self.hay_manos:
            self._t_cambio = None
        else:
            if self._t_cambio is None:
                self._t_cambio = t
            if t - self._t_cambio >= (self.p["t_on"] if vista else self.p["t_off"]):
                self.hay_manos, self._t_cambio = vista, None
        self.ultimo = {"hay_manos": self.hay_manos, "n": len(manos), "manos": manos,
                       "ms": (time.perf_counter() - t0) * 1000}
        return self.ultimo

    def dibujar(self, img_bgr: np.ndarray, r: Optional[Dict] = None) -> None:
        r = r or self.ultimo
        color = (0, 0, 255) if r["hay_manos"] else (0, 200, 255)
        for cx, cy, px in r["manos"]:
            for x, y in px:
                cv2.circle(img_bgr, (int(x), int(y)), 2, color, -1)
            x0, y0 = px.min(axis=0).astype(int)
            x1, y1 = px.max(axis=0).astype(int)
            cv2.rectangle(img_bgr, (x0 - 6, y0 - 6), (x1 + 6, y1 + 6), color, 2)
            cv2.putText(img_bgr, "MANO", (x0 - 6, y0 - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 3)
            cv2.putText(img_bgr, "MANO", (x0 - 6, y0 - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

    def cerrar(self):
        try:
            self.det.close()
        except Exception:
            pass


if __name__ == "__main__":
    import argparse
    import json
    ap = argparse.ArgumentParser(description="Probar la detección de manos")
    ap.add_argument("--camara", type=int, default=None)
    args = ap.parse_args()
    cfg = json.load(open("config.json"))
    cam = cfg["robot"]["cameras"]["front"]
    cap = cv2.VideoCapture(args.camara if args.camara is not None else cam["index_or_path"])
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, cam["width"])
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cam["height"])
    d = DetectorManos(cfg)
    while True:
        ok, bgr = cap.read()
        if not ok:
            continue
        r = d.detectar(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
        d.dibujar(bgr, r)
        cv2.putText(bgr, f"manos: {r['n']}  presentes: {'SI' if r['hay_manos'] else 'NO'}  {r['ms']:.0f} ms",
                    (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        cv2.imshow("Manos", bgr)
        if cv2.waitKey(1) & 0xFF in (ord("q"), 27):
            break
    cap.release()
    cv2.destroyAllWindows()
