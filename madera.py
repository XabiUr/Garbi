#!/usr/bin/env python3
"""
madera.py - Detecta la tabla de madera sobre el tapete azul (cámara "front").

Cómo funciona (cada fotograma):
1. Máscara de COLOR de la madera (HSV, rango calibrado haciendo clic sobre la madera).
2. Se QUITA el azul del tapete y el morado del taladro: el fondo nunca cuenta como madera.
3. Limpieza morfológica y la MANCHA MÁS GRANDE dentro de la región de interés.
4. FORMA: rectángulo girado mínimo (minAreaRect) → 4 esquinas, centro, ángulo y tamaño.
   "Relleno" = área de la mancha / área del rectángulo. Una tabla bien vista da ~0.9-1.0.
5. MEMORIA: se acepta una tabla nueva tras `t_aparece` s viéndola bien (relleno ≥ relleno_min).
   Si algo la tapa (mano, taladro, brazo) se mantiene la última buena; si no se ve nada
   compatible durante `t_retirada` s, se da por retirada.

Salida de detectar(img_rgb): dict con
    hay_madera, esquinas_px (4×2, orden horario desde arriba-izq), centro_px, angulo,
    tamano_px (ancho, alto), relleno, area, vista_ahora (si este fotograma la ha visto bien),
    memoria (si es la última buena mantenida), mascara, candidata (lo medido este fotograma)

Herramienta de calibración y prueba:
    python madera.py                    # cámara front de config.json
    python madera.py --camara 1
    python madera.py --imagen foto.png  # sobre una foto guardada

    Clic izquierdo sobre la madera : añade muestra de color (varios clics = rango más robusto)
    Clic derecho sobre el TAPETE   : añade muestra de azul del tapete (para excluirlo mejor)
    R : borrar muestras de madera      T : borrar muestras de tapete
    M : ver/ocultar máscara            F : guardar foto (fotos_madera/)
    G : guardar en config.json         Q / ESC : salir
"""

import argparse
import json
import os
import time
from typing import Dict, Optional

import cv2
import numpy as np

# Valores por defecto (madera clara de pino/contrachapado, tapete azul). Se sobrescriben con config.json → "madera".
POR_DEFECTO = {
    # Medido en el banco (22-11): aglomerado H 16-19, S 76-93, V 172-194; aluminio/cinta/mesa S 3-18.
    # La S mínima es la que separa la madera del aluminio y la cinta: no bajarla de ~40.
    "hsv_min": [8, 45, 110],
    "hsv_max": [30, 150, 255],
    "excluir_azul": True,
    "hsv_azul_min": [90, 60, 30],  # tapete azul
    "hsv_azul_max": [130, 255, 255],
    "excluir_morado": True,        # usa percepcion.hsv_morado
    "roi": "zona",                 # "zona" (zona.json ampliada con margen_roi), "imagen" (toda) o lista de 4 puntos px
    "margen_roi": 0.25,            # ampliación de la zona en (u,v) para la ROI
    "area_min_px": 2500,           # la tabla de prueba (≈9×9 cm) ocupa ~7700 px a 640×360
    "area_max_px": 200000,
    "relleno_min": 0.85,           # para aceptar una tabla "bien vista"
    "proporcion_max": 1.3,         # lado largo / lado corto máximo (la tabla es cuadrada, 9×9 cm). Más alargado →
                                   # algo pegado (mano, brazo): no se acepta como nueva, se mantiene la última buena
    "kernel": 7,                   # tamaño de la limpieza morfológica (px)
    "t_aparece": 0.3,              # s viéndola bien para darla por puesta
    "t_retirada": 1.0,             # s sin evidencia para darla por retirada
    "coincide_px": 15.0,           # esquinas a menos de esto → misma tabla (se suaviza)
    "suavizado": 0.4,              # peso de la medida nueva al suavizar
}


def cargar_json(ruta: str) -> Optional[dict]:
    try:
        with open(ruta, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return None


def ordenar_esquinas(pts) -> np.ndarray:
    """4 puntos en orden horario (en la imagen) empezando por el de arriba a la izquierda."""
    p = np.asarray(pts, float).reshape(4, 2)
    c = p.mean(axis=0)
    p = p[np.argsort(np.arctan2(p[:, 1] - c[1], p[:, 0] - c[0]))]
    return np.roll(p, -int(np.argmin(p.sum(axis=1))), axis=0)


def distancia_esquinas(a: np.ndarray, b: np.ndarray) -> float:
    """Máxima distancia entre esquinas emparejadas (prueba los 4 giros)."""
    return float(min(np.max(np.linalg.norm(np.roll(a, k, axis=0) - b, axis=1)) for k in range(4)))


class DetectorMadera:
    def __init__(self, config: dict, esquinas_zona: Optional[np.ndarray] = None):
        self.p = {**POR_DEFECTO, **config.get("madera", {})}
        morado = config.get("percepcion", {}).get("hsv_morado")
        self.hsv_morado = (np.array(morado["min"], np.uint8), np.array(morado["max"], np.uint8)) if morado else None
        self.esquinas_zona = None if esquinas_zona is None else np.asarray(esquinas_zona, np.float32)
        self._roi_cache = None
        self.reiniciar()

    # --- parámetros -------------------------------------------------------------------------------------------------
    def poner_rango(self, hsv_min, hsv_max):
        self.p["hsv_min"], self.p["hsv_max"] = [int(x) for x in hsv_min], [int(x) for x in hsv_max]

    def poner_rango_azul(self, hsv_min, hsv_max):
        self.p["hsv_azul_min"], self.p["hsv_azul_max"] = [int(x) for x in hsv_min], [int(x) for x in hsv_max]

    def reiniciar(self):
        self.tabla: Optional[np.ndarray] = None
        self.t_ultima_evidencia = -np.inf
        self.t_buena_desde = None

    # --- región de interés ------------------------------------------------------------------------------------------
    def _roi(self, forma) -> np.ndarray:
        if self._roi_cache is not None and self._roi_cache.shape == forma:
            return self._roi_cache
        m = np.zeros(forma, np.uint8)
        roi = self.p["roi"]
        if isinstance(roi, list) and len(roi) == 4:
            cv2.fillPoly(m, [np.round(np.array(roi)).astype(np.int32)], 255)
        elif roi == "zona" and self.esquinas_zona is not None:
            # zona ampliada: se pasa por (u,v) para ampliar en perspectiva
            d = float(self.p["margen_roi"])
            uv = np.array([[-d, -d], [1 + d, -d], [1 + d, 1 + d], [-d, 1 + d]], np.float32)
            H = cv2.getPerspectiveTransform(np.array([[0, 0], [1, 0], [1, 1], [0, 1]], np.float32), self.esquinas_zona)
            pts = cv2.perspectiveTransform(uv.reshape(-1, 1, 2), H).reshape(-1, 2)
            cv2.fillPoly(m, [np.round(pts).astype(np.int32)], 255)
        else:
            m[:] = 255
        self._roi_cache = m
        return m

    def poligono_roi(self, forma):
        cont, _ = cv2.findContours(self._roi(forma), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        return cont

    # --- máscara y medida -------------------------------------------------------------------------------------------
    def mascara(self, img_hsv: np.ndarray) -> np.ndarray:
        p = self.p
        m = cv2.inRange(img_hsv, np.array(p["hsv_min"], np.uint8), np.array(p["hsv_max"], np.uint8))
        if p["excluir_azul"]:
            m &= ~cv2.inRange(img_hsv, np.array(p["hsv_azul_min"], np.uint8), np.array(p["hsv_azul_max"], np.uint8))
        if p["excluir_morado"] and self.hsv_morado is not None:
            m &= ~cv2.inRange(img_hsv, *self.hsv_morado)
        m &= self._roi(m.shape)
        k = max(1, int(p["kernel"]))
        m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((k, k), np.uint8))
        m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((k, k), np.uint8))
        return m

    def medir(self, mascara: np.ndarray) -> Optional[Dict]:
        """La mancha más grande con su rectángulo, o None si no hay ninguna del tamaño adecuado."""
        n, etiquetas, stats, _ = cv2.connectedComponentsWithStats(mascara)
        if n <= 1:
            return None
        k = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
        area = float(stats[k, cv2.CC_STAT_AREA])
        if not (self.p["area_min_px"] <= area <= self.p["area_max_px"]):
            return None
        conts, _ = cv2.findContours((etiquetas == k).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        c = max(conts, key=cv2.contourArea)
        rect = cv2.minAreaRect(c)
        area_rect = max(rect[1][0] * rect[1][1], 1.0)
        # contorno exterior: un hueco dentro (taladro encima) no penaliza; un mordisco en el borde sí
        lados = sorted(rect[1])
        return {"esquinas": ordenar_esquinas(cv2.boxPoints(rect)), "relleno": cv2.contourArea(c) / area_rect,
                "area": area, "contorno": c, "proporcion": lados[1] / max(lados[0], 1.0)}

    # --- seguimiento con memoria ------------------------------------------------------------------------------------
    def detectar(self, img_rgb: np.ndarray, t: Optional[float] = None) -> Dict:
        t = time.time() if t is None else t
        hsv = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2HSV)
        m = self.mascara(hsv)
        medida = self.medir(m)
        buena = (medida is not None and medida["relleno"] >= self.p["relleno_min"]
                 and medida["proporcion"] <= self.p["proporcion_max"])
        vista_ahora = False

        if buena:
            esq = medida["esquinas"]
            self.t_ultima_evidencia = t
            if self.tabla is None:
                if self.t_buena_desde is None:
                    self.t_buena_desde = t
                if t - self.t_buena_desde >= self.p["t_aparece"]:
                    self.tabla = esq
            elif distancia_esquinas(esq, self.tabla) <= self.p["coincide_px"]:
                a = float(self.p["suavizado"])
                k = int(np.argmin([np.max(np.linalg.norm(np.roll(esq, j, axis=0) - self.tabla, axis=1))
                                   for j in range(4)]))
                self.tabla = a * np.roll(esq, k, axis=0) + (1 - a) * self.tabla
            elif self._dentro(esq):
                pass               # un trozo dentro de la última buena: está tapada en parte, se mantiene
            else:
                self.tabla = esq   # bien vista pero en otro sitio: la han movido
            vista_ahora = self.tabla is not None
        else:
            self.t_buena_desde = None
            if medida is not None and self.tabla is not None:
                self.t_ultima_evidencia = t   # hay madera pero tapada: se mantiene la última buena
            if self.tabla is not None and t - self.t_ultima_evidencia > self.p["t_retirada"]:
                self.tabla = None

        r = {"hay_madera": self.tabla is not None, "vista_ahora": vista_ahora,
             "memoria": self.tabla is not None and not vista_ahora, "mascara": m, "candidata": medida,
             "relleno": medida["relleno"] if medida else 0.0, "area": medida["area"] if medida else 0.0,
             "esquinas_px": None, "centro_px": None, "angulo": None, "tamano_px": None}
        if self.tabla is not None:
            e = self.tabla
            lados = np.linalg.norm(np.roll(e, -1, axis=0) - e, axis=1)
            largo = int(np.argmax(lados[:2]))   # lado 0 (arriba) o 1 (derecha), el más largo
            v = e[(largo + 1) % 4] - e[largo]
            ang = float(np.degrees(np.arctan2(v[1], v[0])))
            ang = (ang + 90) % 180 - 90        # [-90, 90): ángulo del lado largo respecto a la horizontal
            r.update(esquinas_px=e.copy(), centro_px=tuple(e.mean(axis=0)), angulo=ang,
                     tamano_px=(float(max(lados[:2])), float(min(lados[:2]))))
        return r

    def _dentro(self, esquinas: np.ndarray) -> bool:
        """¿Todas las esquinas medidas caen dentro (con margen) de la última tabla buena?"""
        poli = self.tabla.astype(np.float32)
        m = float(self.p["coincide_px"])
        return all(cv2.pointPolygonTest(poli, (float(u), float(v)), True) >= -m for u, v in esquinas)

    # --- dibujo -----------------------------------------------------------------------------------------------------
    def dibujar(self, img_bgr: np.ndarray, r: Dict) -> None:
        """Dibujo ligero para el supervisor (en sitio): rectángulo y etiqueta junto a la tabla, sin textos arriba."""
        if r["esquinas_px"] is None:
            return
        color = (0, 255, 0) if r["vista_ahora"] else (0, 165, 255)   # verde: vista ahora · naranja: memoria
        e = np.round(r["esquinas_px"]).astype(np.int32)
        cv2.polylines(img_bgr, [e], True, color, 2)
        cx, cy = r["centro_px"]
        cv2.drawMarker(img_bgr, (int(cx), int(cy)), color, cv2.MARKER_CROSS, 14, 2)
        x, y = int(e[:, 0].min()), int(e[:, 1].min()) - 6
        texto = f"MADERA {r['angulo']:.0f}deg" + (" (mem)" if r["memoria"] else "")
        cv2.putText(img_bgr, texto, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 3)
        cv2.putText(img_bgr, texto, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1)

    def dibujar_debug(self, img_bgr: np.ndarray, r: Dict) -> np.ndarray:
        img = img_bgr.copy()
        cv2.drawContours(img, self.poligono_roi(img.shape[:2]), -1, (120, 120, 120), 1)
        if self.esquinas_zona is not None:
            cv2.polylines(img, [self.esquinas_zona.astype(np.int32)], True, (0, 255, 0), 1)
        cand = r["candidata"]
        if cand is not None:
            cv2.drawContours(img, [cand["contorno"]], -1, (0, 200, 255), 1)
        if r["esquinas_px"] is not None:
            color = (0, 255, 0) if r["vista_ahora"] else (0, 165, 255)
            e = np.round(r["esquinas_px"]).astype(np.int32)
            cv2.polylines(img, [e], True, color, 3)
            for i, (x, y) in enumerate(e):
                cv2.circle(img, (int(x), int(y)), 5, color, -1)
                cv2.putText(img, str(i), (int(x) + 6, int(y) - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
            cx, cy = r["centro_px"]
            cv2.drawMarker(img, (int(cx), int(cy)), color, cv2.MARKER_CROSS, 18, 2)
        textos = [
            f"Madera: {'SI' if r['hay_madera'] else 'NO'}" + ("  (MEMORIA)" if r["memoria"] else ""),
            f"Relleno: {r['relleno']:.2f}  (min {self.p['relleno_min']:.2f})   Area: {int(r['area'])} px"
            + (f"   Prop: {r['candidata']['proporcion']:.2f}" if r["candidata"] else ""),
        ]
        if r["angulo"] is not None:
            textos.append(f"Angulo: {r['angulo']:.1f}   Tamano: {r['tamano_px'][0]:.0f}x{r['tamano_px'][1]:.0f} px")
        y = 22
        for tx in textos:
            cv2.putText(img, tx, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 3)
            cv2.putText(img, tx, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 1)
            y += 22
        return img


# ---------------------------------------------------------------------------------------------------------------------
# Herramienta de calibración
# ---------------------------------------------------------------------------------------------------------------------

def rango_desde_muestras(muestras: list, holgura=(6, 25, 30), percentiles=(3, 97)):
    """Rango HSV a partir de píxeles muestreados (percentiles + holgura). Tono sin vuelta por el 0 (madera ~5-35)."""
    px = np.concatenate(muestras, axis=0)
    lo = np.percentile(px, percentiles[0], axis=0) - holgura
    hi = np.percentile(px, percentiles[1], axis=0) + holgura
    lo = np.clip(lo, 0, [179, 255, 255]).astype(int)
    hi = np.clip(hi, 0, [179, 255, 255]).astype(int)
    return lo.tolist(), hi.tolist()


def main():
    ap = argparse.ArgumentParser(description="Calibrar y probar la detección de la madera")
    ap.add_argument("--camara", type=int, default=None, help="índice de cámara (por defecto front de config.json)")
    ap.add_argument("--imagen", type=str, default=None, help="probar sobre una foto en vez de la cámara")
    args = ap.parse_args()

    config = cargar_json("config.json") or {}
    zona = cargar_json("zona.json")
    esquinas = np.array(zona["esquinas_px"], np.float32) if zona else None
    det = DetectorMadera(config, esquinas)

    cap, foto = None, None
    if args.imagen:
        foto = cv2.imread(args.imagen)
        if foto is None:
            raise SystemExit(f"No puedo leer {args.imagen}")
    else:
        cam = config.get("robot", {}).get("cameras", {}).get("front", {})
        indice = args.camara if args.camara is not None else cam.get("index_or_path", 0)
        cap = cv2.VideoCapture(indice)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, cam.get("width", 640))
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cam.get("height", 360))
        if not cap.isOpened():
            raise SystemExit(f"No puedo abrir la cámara {indice}")

    VENT = "Madera"
    cv2.namedWindow(VENT)
    cv2.namedWindow("Ajustes", cv2.WINDOW_NORMAL)
    nombres = ["H min", "S min", "V min", "H max", "S max", "V max"]
    topes = [179, 255, 255, 179, 255, 255]

    def a_sliders():
        for n, v in zip(nombres, det.p["hsv_min"] + det.p["hsv_max"]):
            cv2.setTrackbarPos(n, "Ajustes", int(v))

    for n, tope, v in zip(nombres, topes, det.p["hsv_min"] + det.p["hsv_max"]):
        cv2.createTrackbar(n, "Ajustes", int(v), tope, lambda _: None)
    cv2.createTrackbar("Relleno min x100", "Ajustes", int(det.p["relleno_min"] * 100), 100, lambda _: None)
    cv2.createTrackbar("Kernel", "Ajustes", int(det.p["kernel"]), 25, lambda _: None)

    estado = {"bgr": None, "madera": [], "azul": [], "ver_mascara": True}

    def raton(evento, x, y, flags, _):
        if estado["bgr"] is None or evento not in (cv2.EVENT_LBUTTONDOWN, cv2.EVENT_RBUTTONDOWN):
            return
        hsv = cv2.cvtColor(estado["bgr"], cv2.COLOR_BGR2HSV)
        r = 7
        parche = hsv[max(0, y - r):y + r + 1, max(0, x - r):x + r + 1].reshape(-1, 3).astype(float)
        if evento == cv2.EVENT_LBUTTONDOWN:
            estado["madera"].append(parche)
            det.poner_rango(*rango_desde_muestras(estado["madera"]))
            a_sliders()
            print(f"[Madera] muestra {len(estado['madera'])} en ({x},{y}) → HSV {det.p['hsv_min']} - {det.p['hsv_max']}")
        else:
            estado["azul"].append(parche)
            det.poner_rango_azul(*rango_desde_muestras(estado["azul"], holgura=(8, 40, 50)))
            print(f"[Tapete] muestra {len(estado['azul'])} → HSV {det.p['hsv_azul_min']} - {det.p['hsv_azul_max']}")

    cv2.setMouseCallback(VENT, raton)
    print(__doc__.split("Herramienta de calibración y prueba:")[1])

    while True:
        if cap is not None:
            ok, bgr = cap.read()
            if not ok:
                time.sleep(0.03)
                continue
        else:
            bgr = foto.copy()
        estado["bgr"] = bgr

        v = [cv2.getTrackbarPos(n, "Ajustes") for n in nombres]
        det.poner_rango(v[:3], v[3:])
        det.p["relleno_min"] = cv2.getTrackbarPos("Relleno min x100", "Ajustes") / 100.0
        det.p["kernel"] = max(1, cv2.getTrackbarPos("Kernel", "Ajustes"))

        r = det.detectar(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
        cv2.imshow(VENT, det.dibujar_debug(bgr, r))
        if estado["ver_mascara"]:
            cv2.imshow("Mascara madera", r["mascara"])

        tecla = cv2.waitKey(30 if foto is not None else 1) & 0xFF
        if tecla in (ord("q"), 27):
            break
        elif tecla == ord("r"):
            estado["madera"].clear()
            print("[Madera] muestras borradas")
        elif tecla == ord("t"):
            estado["azul"].clear()
            print("[Tapete] muestras borradas")
        elif tecla == ord("m"):
            estado["ver_mascara"] = not estado["ver_mascara"]
            if not estado["ver_mascara"]:
                cv2.destroyWindow("Mascara madera")
        elif tecla == ord("f"):
            os.makedirs("fotos_madera", exist_ok=True)
            nombre = time.strftime("fotos_madera/madera_%Y%m%d_%H%M%S.png")
            cv2.imwrite(nombre, bgr)
            print(f"[Foto] guardada {nombre}")
        elif tecla == ord("g"):
            cfg = cargar_json("config.json") or {}
            cfg["madera"] = {**cfg.get("madera", {}), **{k: det.p[k] for k in POR_DEFECTO}}
            with open("config.json", "w") as f:
                json.dump(cfg, f, indent=2, ensure_ascii=False)
            print("[Config] guardado config.json → \"madera\"")

    if cap is not None:
        cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
