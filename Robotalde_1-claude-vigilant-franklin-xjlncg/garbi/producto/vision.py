"""Visión del producto Garbi (P2): todo en **píxeles de la cámara de arriba**. Ver `.plans/aspira/producto.md`.

    VisionProducto(config).leer({"top": img, "wrist": img}, t) -> Vista
    VisionProducto.anotar(img_top, vista) -> img con las detecciones dibujadas (para la app)

Las imágenes son **RGB** (como en el resto de Garbi; OpenCV lee BGR: convertir con `cv2.COLOR_BGR2RGB`).

Qué hace cada parte:

1. **Círculo morado** de la trasera del taladro (`DetectorCirculoColor`): máscara HSV del morado (con vuelta del tono si
   `bajo.H > alto.H`), apertura y cierre, y de los contornos con área en rango el más circular (4πA/P² de la envolvente
   convexa ≥ `circularidad_min`, solidez ≥ `solidez_min`). Centro subpíxel por momentos de la máscara rellena y
   radio = √(área/π). Después `FiltroCirculo`: suaviza el centro, aguanta `perdido_s` sin verlo (que no parpadee) y calcula `quieto_desde`: la
   mediana del centro en una ventana de `ventana_quieto_s` (robusta al temblor de la mano) no se ha alejado más de
   `tol_quieto_px` de un ancla; si se aleja, el ancla se mueve ahí y `quieto_desde` es None ese fotograma.
   **Detector del equipo:** `vision.circulo.detector: "paquete.modulo:Nombre"` (clase con `detectar(img)` o función
   `f(img)`) que devuelva `(uv, radio) | None`; `vision.circulo.orden_color: bgr` si espera BGR. O pasarlo en
   `VisionProducto(config, detector_circulo=obj)`.
2. **Manos**: MediaPipe HandLandmarker (`garbi.manos.ManosMediaPipe`, modelo `calib/hand_landmarker.task` o
   `$GARBI_MODELO_MANOS`) cada `cada_n` fotogramas, con respaldo por color de piel (`garbi.manos.ManosColor`) si
   MediaPipe no carga. Centros de la palma en px.
   **Taladro agarrado** (regla del usuario): solo si hay círculo **y** una mano a menos de `agarre.distancia_px` de su
   centro. Nunca mano sola ni taladro solo. Histéresis en distancia (`histeresis_px`) y en tiempo (`t_on`, `t_off`).
   *Cómo ajustar `distancia_px`:* el círculo está en la trasera del taladro y la palma en la empuñadura, unos cm más
   abajo y a un lado; con la cámara a ~1 m y 640×480 eso son ~60-120 px. Con la herramienta en vivo
   (`python -m garbi.producto.vision --camara N`) se dibuja la distancia mano-círculo: agarra el taladro de forma
   natural, mira la cifra y pon `distancia_px` ≈ 1,5 × esa cifra (por defecto 160 px). Si una mano libre apoyada al
   lado del taladro lo «agarra», bájalo.
3. **Tabla** sobre el tapete: el tapete es fijo, 4 esquinas en px (`tapete_px` en `garbi/producto/garbi_producto.yaml`,
   se marcan con `--marcar-tapete`). Tabla = la mayor región clara (V alto, poco saturada, ni azul ni piel) dentro del
   tapete → `minAreaRect` → 4 esquinas. Se acepta con buena evidencia (relleno del rectángulo ≥ `relleno_min`); si
   la tapan (manos, taladro, robot) se mantiene la última buena; si cambia de verdad (movida) se acepta en cuanto se
   ve bien, o tras `t_forzar` aunque siga tapada; `None` tras `t_retirada` s sin tabla.

Configuración: `VisionProducto(config)` con `config` = None (lee `garbi/producto/garbi_producto.yaml` si existe), la
ruta a un yaml o un dict. Se toma la sección `vision:` (o el dict entero si no la tiene) y la clave `tapete_px` de
arriba. Lo que falte, de `POR_DEFECTO`. Los colores (morado, piel, azul) salen por defecto de `garbi/config_vision.yaml`
(sección `parametros.morado` y colores `piel`, `tapete_azul`); `vision.circulo.morado: {bajo, alto}` los sustituye.

Herramientas:

    python -m garbi.producto.vision --camara 0            # en vivo, anotado (s: guardar captura, q: salir)
    python -m garbi.producto.vision --imagen foto.png     # una foto
    python -m garbi.producto.vision --marcar-tapete --camara 0   # 4 clics en las esquinas del tapete → tapete_px
"""
from __future__ import annotations

import argparse
import copy
import importlib
import logging
import time
from collections import deque
from pathlib import Path

import cv2
import numpy as np

from garbi.config_vision import ConfigVision, RangoHSV, cargar_config, mascara_hsv
from garbi.producto.contrato import Circulo, Vista

log = logging.getLogger(__name__)

RUTA_PRODUCTO = Path(__file__).with_name("garbi_producto.yaml")

POR_DEFECTO: dict = {
    "tapete_px": None,  # [[u, v] × 4] esquinas del tapete en la cámara de arriba; None = toda la imagen
    "config_vision": None,  # ruta al yaml de colores (None = garbi/config_vision.yaml)
    "circulo": {
        "detector": "color",       # "color" (este módulo) o "paquete.modulo:Nombre" (el del equipo)
        "orden_color": "rgb",      # lo que espera el detector del equipo: "rgb" o "bgr"
        "morado": None,            # {bajo: [H,S,V], alto: [H,S,V]}; None = parametros.morado de config_vision.yaml
        "area": [60, 25000],       # px² a 640×480
        "circularidad_min": 0.82,  # 4πA/P² de la envolvente convexa (1 = círculo perfecto; un cuadrado da 0,785)
        "solidez_min": 0.85,       # área / área de la envolvente convexa
        "suavizado": 0.6,          # peso del centro nuevo en la media exponencial (1 = sin suavizar)
        "salto_px": 25.0,          # un salto mayor reinicia el suavizado (no arrastra)
        "perdido_s": 0.3,          # se mantiene el último círculo este tiempo si deja de verse
        "tol_quieto_px": 6.0,      # TOL: el centro (mediana) no se mueve más que esto → quieto
        "ventana_quieto_s": 0.3,   # ventana de la mediana (temblor de la mano)
    },
    "manos": {
        "detector": "auto",        # "auto" (MediaPipe y si no color), "mediapipe", "color" o "ninguno"
        "cada_n": 2,               # MediaPipe cada N fotogramas (el resto reutiliza las últimas manos)
        "caducan_s": 0.4,          # manos más viejas que esto no cuentan
        "modelo": None,            # hand_landmarker.task; None = $GARBI_MODELO_MANOS o calib/hand_landmarker.task
    },
    "agarre": {
        "distancia_px": 160.0,     # mano a menos de esto del centro del círculo → agarrado (ver docstring)
        "histeresis_px": 30.0,     # para soltar hace falta distancia_px + histeresis_px
        "t_on": 0.15,              # s seguidos cumpliendo la regla para pasar a agarrado
        "t_off": 0.4,              # s seguidos sin cumplirla para soltar
    },
    "tabla": {
        "v_min": 130,              # brillo mínimo (HSV) de lo claro
        "s_max": 110,              # saturación máxima de lo claro (la madera clara es poco saturada)
        "area_min": 0.04,          # fracción del área del tapete
        "relleno_min": 0.9,        # área de la región (sin huecos) / área de su minAreaRect para aceptarla sin dudas
        "relleno_forzar": 0.65,    # relleno mínimo para aceptar tras t_forzar una tabla que nunca se ha visto bien
        "coincide_px": 12.0,       # esquinas a menos de esto de la última buena → es la misma tabla
        "t_aparece": 0.3,          # s viéndola bien para darla por puesta
        "t_retirada": 1.0,         # s sin tabla para dar tabla=None
        "t_forzar": 2.0,           # s viendo una tabla distinta (aunque tapada) para aceptarla
        "suavizado": 0.5,          # peso de las esquinas nuevas cuando es la misma tabla
        "escala": 0.5,             # se procesa a esta escala (velocidad)
    },
}


# --- configuración --------------------------------------------------------------------------------------------------

def _mezclar(base: dict, nuevo: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in (nuevo or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _mezclar(out[k], v)
        else:
            out[k] = v
    return out


def cargar_config_vision_producto(config=None) -> dict:
    """Config de la visión del producto (dict completo, con los valores por defecto). Ver el docstring del módulo."""
    import yaml

    if config is None:
        datos = (yaml.safe_load(RUTA_PRODUCTO.read_text(encoding="utf-8")) or {}) if RUTA_PRODUCTO.exists() else {}
    elif isinstance(config, (str, Path)):
        datos = yaml.safe_load(Path(config).read_text(encoding="utf-8")) or {}
    elif isinstance(config, dict):
        datos = config
    else:  # objeto con atributos (p. ej. la config del orquestador)
        datos = {"vision": getattr(config, "vision", None) or {}, "tapete_px": getattr(config, "tapete_px", None)}
    seccion = datos.get("vision") if isinstance(datos.get("vision"), dict) else (
        {} if "vision" in datos else {k: v for k, v in datos.items() if k in POR_DEFECTO})
    cfg = _mezclar(POR_DEFECTO, seccion)
    if datos.get("tapete_px") is not None:
        cfg["tapete_px"] = datos["tapete_px"]
    return cfg


def _rango(v) -> RangoHSV:
    return v if isinstance(v, RangoHSV) else RangoHSV(v["bajo"], v["alto"])


def _cargar_objeto(ruta: str):
    """"paquete.modulo:Nombre" → el objeto (una clase se instancia sin argumentos)."""
    modulo, _, nombre = ruta.partition(":")
    obj = getattr(importlib.import_module(modulo), nombre or "detectar")
    return obj() if isinstance(obj, type) else obj


# --- 1. círculo morado ----------------------------------------------------------------------------------------------

class DetectorCirculoColor:
    """El círculo morado más circular de la imagen RGB. `detectar(img) -> (uv, radio) | None`."""

    def __init__(self, morado: RangoHSV, area=(60, 25000), circularidad_min: float = 0.82, solidez_min: float = 0.85):
        self.morado = _rango(morado)
        self.area = (float(area[0]), float(area[1]))
        self.circularidad_min = float(circularidad_min)
        self.solidez_min = float(solidez_min)
        self.ultima_mascara: np.ndarray | None = None

    def mascara(self, hsv: np.ndarray) -> np.ndarray:
        m = mascara_hsv(hsv, self.morado)
        m = cv2.morphologyEx(m, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))
        return cv2.morphologyEx(m, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))

    def detectar(self, img: np.ndarray, hsv: np.ndarray | None = None):
        if hsv is None:
            hsv = cv2.cvtColor(np.ascontiguousarray(img), cv2.COLOR_RGB2HSV)
        m = self.mascara(hsv)
        self.ultima_mascara = m
        contornos, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        mejor, mejor_c = None, self.circularidad_min
        for c in contornos:
            a = cv2.contourArea(c)
            if not self.area[0] <= a <= self.area[1]:
                continue
            # circularidad con la envolvente convexa (el borde de píxeles, dentado, alarga el perímetro) y solidez
            # (área / área de la envolvente) para descartar formas cóncavas
            envolvente = cv2.convexHull(c)
            a_env, p_env = cv2.contourArea(envolvente), cv2.arcLength(envolvente, True)
            circ = 4.0 * np.pi * a_env / max(p_env * p_env, 1e-9)
            if a / max(a_env, 1e-9) >= self.solidez_min and circ >= mejor_c:
                mejor, mejor_c = c, circ
        if mejor is None:
            return None
        # centro subpíxel: momentos del contorno relleno (contorno de píxeles: área y centro algo sesgados; el relleno
        # da el centroide de los píxeles, exacto para un disco)
        x, y, w, h = cv2.boundingRect(mejor)
        roi = np.zeros((h, w), np.uint8)
        cv2.drawContours(roi, [mejor - np.array([x, y])], -1, 255, -1)
        roi &= m[y:y + h, x:x + w]
        mo = cv2.moments(roi, binaryImage=True)
        if mo["m00"] <= 0:
            return None
        uv = np.array([x + mo["m10"] / mo["m00"], y + mo["m01"] / mo["m00"]])
        return uv, float(np.sqrt(mo["m00"] / np.pi))


class _DetectorExterno:
    """Adapta el detector del equipo: objeto con `detectar(img)` o función `f(img)`."""

    def __init__(self, obj, bgr: bool = False):
        self.f = obj.detectar if hasattr(obj, "detectar") else obj
        self.bgr = bgr

    def detectar(self, img, hsv=None):
        r = self.f(cv2.cvtColor(img, cv2.COLOR_RGB2BGR) if self.bgr else img)
        if r is None:
            return None
        uv, radio = r
        return np.asarray(uv, float).reshape(2), float(radio)


class FiltroCirculo:
    """Filtro temporal del círculo: suavizado, memoria corta si se pierde y `quieto_desde`."""

    def __init__(self, suavizado=0.6, salto_px=25.0, perdido_s=0.3, tol_quieto_px=6.0, ventana_quieto_s=0.3):
        self.a, self.salto, self.perdido = float(suavizado), float(salto_px), float(perdido_s)
        self.tol, self.ventana = float(tol_quieto_px), float(ventana_quieto_s)
        self.reiniciar()

    def reiniciar(self):
        self.uv = None
        self.radio = 0.0
        self.t_visto = -np.inf
        self.hist: deque = deque()
        self.ancla = None
        self.t_ancla = None
        self.quieto_desde = None

    def actualizar(self, det, t: float) -> Circulo | None:
        if det is None:
            if self.uv is None or t - self.t_visto > self.perdido:
                self.reiniciar()
                return None
            return Circulo(self.uv.copy(), self.radio, self.quieto_desde)  # se mantiene lo último un momento
        uv, radio = np.asarray(det[0], float), float(det[1])
        if self.uv is None or np.linalg.norm(uv - self.uv) > self.salto:
            self.uv, self.radio = uv.copy(), radio
        else:
            self.uv = self.a * uv + (1 - self.a) * self.uv
            self.radio = self.a * radio + (1 - self.a) * self.radio
        self.t_visto = t
        # quieto: mediana del centro bruto en la ventana, comparada con el ancla
        self.hist.append((t, uv))
        while self.hist and t - self.hist[0][0] > self.ventana:
            self.hist.popleft()
        mediana = np.median(np.array([p for _, p in self.hist]), axis=0)
        if self.ancla is None or np.linalg.norm(mediana - self.ancla) > self.tol:
            self.ancla, self.t_ancla, self.quieto_desde = mediana, t, None
        else:
            self.quieto_desde = self.t_ancla
        return Circulo(self.uv.copy(), self.radio, self.quieto_desde)


# --- 2. manos y la regla mano + taladro -----------------------------------------------------------------------------

class ManosColorPx:
    """Manos por color de piel (respaldo), solo en píxeles: la misma máscara que `garbi.manos.ManosColor` sin
    proyectar a la mesa (no necesita la cámara calibrada ni importa la percepción de la simulación)."""
    fuente = "color"

    def __init__(self, cfg: ConfigVision):
        self.cfg = cfg

    def detectar_px(self, img: np.ndarray, hsv: np.ndarray | None = None) -> list[np.ndarray]:
        if hsv is None:
            hsv = cv2.cvtColor(np.ascontiguousarray(img), cv2.COLOR_RGB2HSV)
        piel = self.cfg.mascara(hsv, "manos")
        piel &= ~cv2.dilate(self.cfg.mascara(hsv, "bola"), np.ones((9, 9), np.uint8))
        piel = cv2.morphologyEx(piel, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
        piel = cv2.morphologyEx(piel, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (17, 17)))
        n, _, stats, centros = cv2.connectedComponentsWithStats(piel)
        lo, hi = self.cfg["manos"]["area"]
        return [centros[k].astype(float) for k in range(1, n) if lo <= stats[k, cv2.CC_STAT_AREA] <= hi]


class ManosMediaPipePx:
    """MediaPipe HandLandmarker (`garbi.manos.ManosMediaPipe`), solo en píxeles: centro de la palma = media de la
    muñeca y los cuatro nudillos."""
    fuente = "mediapipe"

    def __init__(self, modelo=None, max_manos: int = 4, confianza_min: float = 0.4):
        from garbi.manos import ManosMediaPipe

        self.mp = ManosMediaPipe(modelo, max_manos, confianza_min)
        self.mp._cargar()  # falla aquí (ImportError, FileNotFoundError, OSError) si no se puede: respaldo

    def detectar_px(self, img: np.ndarray, hsv=None) -> list[np.ndarray]:
        from garbi.manos import PALMA

        alto, ancho = img.shape[:2]
        imagen = self.mp._mp.Image(image_format=self.mp._mp.ImageFormat.SRGB, data=np.ascontiguousarray(img))
        res = self.mp._detector.detect(imagen)
        return [np.array([[pt[i].x * ancho, pt[i].y * alto] for i in PALMA]).mean(axis=0)
                for pt in (res.hand_landmarks or [])]

    def cerrar(self) -> None:
        self.mp.cerrar()


def crear_detector_manos(tipo: str, cfg_color: ConfigVision, modelo=None):
    """"auto" (MediaPipe y si no se puede, color), "mediapipe", "color" o "ninguno" → detector con
    `detectar_px(img, hsv) -> [uv]` (o None)."""
    if tipo == "ninguno":
        return None
    if tipo == "color":
        return ManosColorPx(cfg_color)
    try:
        d = ManosMediaPipePx(modelo)
        log.info("manos: MediaPipe (%s)", d.mp.modelo)
        return d
    except (ImportError, FileNotFoundError, OSError, RuntimeError) as e:  # OSError: p. ej. falta libEGL
        if tipo == "mediapipe":
            raise
        log.warning("manos: sin MediaPipe (%s); uso el color de piel", str(e).splitlines()[0])
        return ManosColorPx(cfg_color)


class ReglaAgarre:
    """`taladro_agarrado` con histéresis: círculo **y** una mano cerca (px). Nunca mano sola ni taladro solo."""

    def __init__(self, distancia_px=160.0, histeresis_px=30.0, t_on=0.15, t_off=0.4):
        self.d_on, self.d_off = float(distancia_px), float(distancia_px) + float(histeresis_px)
        self.t_on, self.t_off = float(t_on), float(t_off)
        self.agarrado = False
        self.t_cambio_pedido = None
        self.distancia: float | None = None

    def actualizar(self, circulo: Circulo | None, manos: list[np.ndarray], t: float) -> bool:
        if circulo is None or not manos:
            self.distancia = None
            cumple = False
        else:
            self.distancia = float(min(np.linalg.norm(np.asarray(m) - circulo.uv) for m in manos))
            cumple = self.distancia <= (self.d_off if self.agarrado else self.d_on)
        if cumple == self.agarrado:
            self.t_cambio_pedido = None
        else:
            if self.t_cambio_pedido is None:
                self.t_cambio_pedido = t
            if t - self.t_cambio_pedido >= (self.t_on if cumple else self.t_off):
                self.agarrado, self.t_cambio_pedido = cumple, None
        return self.agarrado


# --- 3. tabla sobre el tapete ---------------------------------------------------------------------------------------

def ordenar_esquinas(pts) -> np.ndarray:
    """4 puntos en orden horario empezando por el de arriba a la izquierda (menor u+v)."""
    p = np.asarray(pts, float).reshape(4, 2)
    c = p.mean(axis=0)
    p = p[np.argsort(np.arctan2(p[:, 1] - c[1], p[:, 0] - c[0]))]  # horario en la imagen (v hacia abajo)
    return np.roll(p, -int(np.argmin(p.sum(axis=1))), axis=0)


def _distancia_esquinas(a: np.ndarray, b: np.ndarray) -> float:
    """Máxima distancia entre esquinas emparejadas (prueba los 4 giros del orden)."""
    return float(min(np.max(np.linalg.norm(np.roll(a, k, axis=0) - b, axis=1)) for k in range(4)))


class SeguidorTabla:
    """La tabla (región clara mayor dentro del tapete) con memoria: aguanta oclusiones y da None si se retira."""

    def __init__(self, p: dict):
        self.p = p
        self.reiniciar()

    def reiniciar(self):
        self.tabla: np.ndarray | None = None   # la última buena (la que se publica)
        self.t_ultima_evidencia = -np.inf      # última vez que se vio algo compatible con una tabla
        self.t_buena_desde = None              # para t_aparece
        self.t_distinta_desde = None           # para t_forzar
        self.candidata: np.ndarray | None = None
        self.relleno = 0.0

    def medir(self, hsv: np.ndarray, mascara_tapete: np.ndarray, excluir: np.ndarray, area_tapete: float,
              encima: np.ndarray | None = None):
        """(esquinas px a escala completa, relleno) de la región clara mayor, o None. `excluir`: lo que no es tabla
        (azul, piel, morado); `encima`: lo que se sabe que tapa (piel, morado), que dentro del rectángulo cuenta como
        tabla para el relleno (una mano que muerde el borde no la invalida)."""
        p, e = self.p, float(self.p["escala"])
        h, w = hsv.shape[:2]
        if e != 1.0:
            hsv = cv2.resize(hsv, (int(w * e), int(h * e)), interpolation=cv2.INTER_NEAREST)
            mascara_tapete = cv2.resize(mascara_tapete, hsv.shape[1::-1], interpolation=cv2.INTER_NEAREST)
            excluir = cv2.resize(excluir, hsv.shape[1::-1], interpolation=cv2.INTER_NEAREST)
            if encima is not None:
                encima = cv2.resize(encima, hsv.shape[1::-1], interpolation=cv2.INTER_NEAREST)
        claro = cv2.inRange(hsv, np.array([0, 0, int(p["v_min"])], np.uint8),
                            np.array([179, int(p["s_max"]), 255], np.uint8))
        claro &= mascara_tapete & ~excluir
        claro = cv2.morphologyEx(claro, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        n, etiquetas, stats, _ = cv2.connectedComponentsWithStats(claro)
        if n <= 1:
            return None
        k = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
        area = float(stats[k, cv2.CC_STAT_AREA])
        if area < float(p["area_min"]) * area_tapete * e * e:
            return None
        # contorno exterior: los huecos de dentro (una mano o el taladro encima, sin tocar el borde) no cuentan
        # contra el relleno; lo que muerde el borde (el robot en una esquina) sí
        contornos, _ = cv2.findContours((etiquetas == k).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        c = max(contornos, key=cv2.contourArea)
        rect = cv2.minAreaRect(c)
        area_rect = max(rect[1][0] * rect[1][1], 1.0)
        caja = cv2.boxPoints(rect)
        esquinas = (caja + 0.5) / e - 0.5  # centros de píxel a escala completa
        if encima is None:
            return ordenar_esquinas(esquinas), cv2.contourArea(c) / area_rect
        en_rect = np.zeros(claro.shape, np.uint8)
        cv2.fillPoly(en_rect, [np.round(caja).astype(np.int32)], 255)
        region = np.zeros(claro.shape, np.uint8)
        cv2.drawContours(region, [c], -1, 255, -1)
        lleno = np.count_nonzero(en_rect & (region | encima))
        return ordenar_esquinas(esquinas), lleno / max(np.count_nonzero(en_rect), 1)

    def actualizar(self, medida, t: float) -> np.ndarray | None:
        p = self.p
        if medida is None:
            self.candidata, self.relleno = None, 0.0
            self.t_buena_desde = self.t_distinta_desde = None
            if self.tabla is not None and t - self.t_ultima_evidencia > float(p["t_retirada"]):
                self.tabla = None
            return self.tabla
        esquinas, relleno = medida
        self.candidata, self.relleno = esquinas, relleno
        buena = relleno >= float(p["relleno_min"])
        if self.tabla is None:
            if buena:
                self.t_ultima_evidencia, self.t_distinta_desde = t, None
                if self.t_buena_desde is None:
                    self.t_buena_desde = t
                if t - self.t_buena_desde >= float(p["t_aparece"]):
                    self.tabla = esquinas
            else:  # puesta ya tapada (p. ej. con el robot encima): se acepta tras t_forzar si se parece a una tabla
                self.t_buena_desde = None
                if relleno >= float(p["relleno_forzar"]):
                    if self.t_distinta_desde is None:
                        self.t_distinta_desde = t
                    if t - self.t_distinta_desde >= float(p["t_forzar"]):
                        self.tabla, self.t_distinta_desde, self.t_ultima_evidencia = esquinas, None, t
                else:
                    self.t_distinta_desde = None
            return self.tabla
        misma = _distancia_esquinas(esquinas, self.tabla) <= float(p["coincide_px"])
        if misma and buena:  # la misma tabla bien vista: se afina
            a = float(p["suavizado"])
            k = int(np.argmin([np.max(np.linalg.norm(np.roll(esquinas, j, axis=0) - self.tabla, axis=1))
                               for j in range(4)]))
            self.tabla = a * np.roll(esquinas, k, axis=0) + (1 - a) * self.tabla
            self.t_ultima_evidencia, self.t_distinta_desde = t, None
        elif buena:  # distinta y bien vista: la han movido
            self.tabla, self.t_ultima_evidencia, self.t_distinta_desde = esquinas, t, None
        else:  # tapada en parte: se mantiene la última buena salvo que lleve mucho siendo distinta
            self.t_ultima_evidencia = t
            if misma or self._cubre(esquinas):
                self.t_distinta_desde = None
            else:
                if self.t_distinta_desde is None:
                    self.t_distinta_desde = t
                if t - self.t_distinta_desde >= float(p["t_forzar"]):
                    self.tabla, self.t_distinta_desde = esquinas, None
        return self.tabla

    def _cubre(self, esquinas: np.ndarray) -> bool:
        """¿La región vista (tapada) cae dentro de la última buena? Entonces es la misma tabla con algo encima."""
        poli = self.tabla.astype(np.float32)
        margen = float(self.p["coincide_px"])
        return all(cv2.pointPolygonTest(poli, (float(u), float(v)), True) >= -margen for u, v in esquinas)


# --- 4. la visión completa ------------------------------------------------------------------------------------------

class VisionProducto:
    """La visión del producto. `leer(imagenes, t) -> Vista`; `anotar(img_top, vista) -> img`."""

    def __init__(self, config=None, detector_circulo=None, detector_manos="config"):
        self.cfg = cargar_config_vision_producto(config)
        self.colores = cargar_config(self.cfg.get("config_vision"))
        c = self.cfg["circulo"]
        morado = _rango(c["morado"]) if c.get("morado") else self.colores.rango("morado")
        if detector_circulo is not None:
            self.detector_circulo = _DetectorExterno(detector_circulo, c["orden_color"] == "bgr")
        elif c["detector"] in (None, "", "color"):
            self.detector_circulo = DetectorCirculoColor(morado, c["area"], c["circularidad_min"], c["solidez_min"])
        else:
            self.detector_circulo = _DetectorExterno(_cargar_objeto(c["detector"]), c["orden_color"] == "bgr")
        self.filtro = FiltroCirculo(c["suavizado"], c["salto_px"], c["perdido_s"], c["tol_quieto_px"],
                                    c["ventana_quieto_s"])
        if detector_manos == "config":
            m = self.cfg["manos"]
            self.detector_manos = crear_detector_manos(m["detector"], self.colores, m.get("modelo"))
        else:  # uno propio con detectar_px(img, hsv) -> [uv]
            self.detector_manos = detector_manos
        self.fuente_manos = getattr(self.detector_manos, "fuente", type(self.detector_manos).__name__)
        if self.detector_manos is None:
            self.fuente_manos = "ninguno"
        self.regla = ReglaAgarre(**self.cfg["agarre"])
        self.seguidor_tabla = SeguidorTabla(self.cfg["tabla"])
        self.tapete = (np.asarray(self.cfg["tapete_px"], float).reshape(4, 2)
                       if self.cfg.get("tapete_px") is not None else None)
        self._mascara_tapete = None
        self._n = 0
        self._manos: list[np.ndarray] = []
        self._t_manos = -np.inf
        self._t_prev = None
        self.fps = 0.0           # según los t que se pasan a leer
        self.ms_proceso = 0.0    # tiempo de cálculo por fotograma (media)

    def _tapete_mascara(self, forma) -> tuple[np.ndarray, float]:
        if self._mascara_tapete is None or self._mascara_tapete.shape != forma:
            m = np.zeros(forma, np.uint8)
            if self.tapete is None:
                m[:] = 255
            else:
                cv2.fillPoly(m, [np.round(self.tapete).astype(np.int32)], 255)
            self._mascara_tapete = m
        return self._mascara_tapete, float(np.count_nonzero(self._mascara_tapete))

    def leer(self, imagenes: dict, t: float) -> Vista:
        t0 = time.perf_counter()
        img = np.ascontiguousarray(imagenes["top"])
        hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV)
        # 1. círculo
        det = self.detector_circulo.detectar(img, hsv)
        circulo = self.filtro.actualizar(det, t)
        # 2. manos (MediaPipe cada N fotogramas)
        if self.detector_manos is not None and self._n % max(1, int(self.cfg["manos"]["cada_n"])) == 0:
            try:
                self._manos = [np.asarray(uv, float) for uv in self.detector_manos.detectar_px(img, hsv)]
                self._t_manos = t
            except Exception as e:  # MediaPipe falla en ejecución → color
                if isinstance(self.detector_manos, ManosColorPx):
                    raise
                log.warning("manos: %s falla (%s); paso al color de piel", self.fuente_manos, e)
                self.detector_manos, self.fuente_manos = ManosColorPx(self.colores), "color"
        manos = self._manos if t - self._t_manos <= float(self.cfg["manos"]["caducan_s"]) else []
        agarrado = self.regla.actualizar(circulo, manos, t)
        # 3. tabla (sin el azul del tapete, la piel ni el morado)
        mt, area_tapete = self._tapete_mascara(hsv.shape[:2])
        encima = self.colores.mascara(hsv, "manos")
        if isinstance(self.detector_circulo, DetectorCirculoColor) and self.detector_circulo.ultima_mascara is not None:
            encima |= self.detector_circulo.ultima_mascara
        excluir = self.colores.mascara(hsv, "tapete") | encima
        medida = self.seguidor_tabla.medir(hsv, mt, excluir, area_tapete, encima)
        tabla = self.seguidor_tabla.actualizar(medida, t)
        # tiempos
        if self._t_prev is not None and t > self._t_prev:
            f = 1.0 / (t - self._t_prev)
            self.fps = f if self.fps == 0 else 0.9 * self.fps + 0.1 * f
        self._t_prev = t
        self._n += 1
        ms = (time.perf_counter() - t0) * 1000.0
        self.ms_proceso = ms if self._n == 1 else 0.9 * self.ms_proceso + 0.1 * ms
        return Vista(t=t, circulo=circulo, manos=[m.copy() for m in manos], taladro_agarrado=agarrado,
                     tabla=None if tabla is None else tabla.copy(),
                     tapete=None if self.tapete is None else self.tapete.copy())

    def reiniciar(self) -> None:
        self.filtro.reiniciar()
        self.seguidor_tabla.reiniciar()
        self.regla = ReglaAgarre(**self.cfg["agarre"])
        self._manos, self._t_manos, self._t_prev, self._n = [], -np.inf, None, 0

    def anotar(self, img_top: np.ndarray, vista: Vista) -> np.ndarray:
        """Copia de la imagen (RGB) con el tapete, la tabla, el círculo (y su tiempo quieto), las manos, «taladro
        agarrado» y los FPS."""
        out = np.ascontiguousarray(img_top).copy()
        fuente = cv2.FONT_HERSHEY_SIMPLEX

        def poli(pts, color, grosor=2):
            cv2.polylines(out, [np.round(pts).astype(np.int32)], True, color, grosor, cv2.LINE_AA)

        def texto(s, org, color, escala=0.55):
            cv2.putText(out, s, org, fuente, escala, (0, 0, 0), 3, cv2.LINE_AA)
            cv2.putText(out, s, org, fuente, escala, color, 1, cv2.LINE_AA)

        if vista.tapete is not None:
            poli(vista.tapete, (80, 160, 255), 1)
        if vista.tabla is not None:
            poli(vista.tabla, (255, 220, 0), 2)
            u, v = vista.tabla[0]
            texto("tabla", (int(u) + 4, int(v) + 16), (255, 220, 0))
        else:
            texto("sin tabla", (10, out.shape[0] - 12), (255, 220, 0))
        c = vista.circulo
        if c is not None:
            centro = tuple(np.round(c.uv).astype(int))
            color = (0, 255, 0) if c.quieto_desde is not None else (255, 0, 255)
            cv2.circle(out, centro, max(2, int(round(c.radio))), color, 2, cv2.LINE_AA)
            cv2.drawMarker(out, centro, color, cv2.MARKER_CROSS, 10, 1)
            quieto = f"quieto {vista.t - c.quieto_desde:.1f} s" if c.quieto_desde is not None else "moviendo"
            texto(quieto, (centro[0] + int(c.radio) + 6, centro[1]), color)
            d = self.cfg["agarre"]["distancia_px"]
            cv2.circle(out, centro, int(d), (120, 120, 120), 1, cv2.LINE_AA)  # zona de agarre
        for m in vista.manos:
            p = tuple(np.round(m).astype(int))
            cv2.circle(out, p, 9, (255, 140, 60), -1, cv2.LINE_AA)
            if c is not None:
                cv2.line(out, p, tuple(np.round(c.uv).astype(int)), (255, 140, 60), 1, cv2.LINE_AA)
                dist = float(np.linalg.norm(m - c.uv))
                texto(f"{dist:.0f} px", (p[0] + 10, p[1] - 10), (255, 140, 60), 0.45)
        if vista.taladro_agarrado:
            texto("TALADRO AGARRADO", (10, 52), (0, 255, 0), 0.8)
        texto(f"{self.fps:4.1f} fps  ({self.ms_proceso:.0f} ms)  manos: {self.fuente_manos}", (10, 22),
              (255, 255, 255))
        return out

    def cerrar(self) -> None:
        if hasattr(self.detector_manos, "cerrar"):
            self.detector_manos.cerrar()


# --- 5. herramientas ------------------------------------------------------------------------------------------------

def guardar_tapete_px(esquinas, ruta: Path = RUTA_PRODUCTO) -> bool:
    """Escribe `tapete_px: [[u, v], ...]` en el yaml del producto conservando el resto del archivo (comentarios
    incluidos). Si el archivo no existe, no lo crea: devuelve False (imprime el valor quien llame)."""
    ruta = Path(ruta)
    if not ruta.exists():
        return False
    linea = "tapete_px: " + formato_tapete(esquinas)
    lineas = ruta.read_text(encoding="utf-8").splitlines()
    for i, l in enumerate(lineas):
        if l.startswith("tapete_px:"):
            lineas[i] = linea
            break
    else:
        lineas += ["", "# Esquinas del tapete en la cámara de arriba (px), de python -m garbi.producto.vision "
                   "--marcar-tapete", linea]
    ruta.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    return True


def formato_tapete(esquinas) -> str:
    return "[" + ", ".join(f"[{u:.1f}, {v:.1f}]" for u, v in np.asarray(esquinas, float).reshape(4, 2)) + "]"


def _resolucion_top() -> tuple[int, int]:
    """(ancho, alto) de la cámara de arriba según `camaras.resolucion.top` del yaml del producto (640 × 480 si no)."""
    try:
        import yaml

        datos = yaml.safe_load(RUTA_PRODUCTO.read_text(encoding="utf-8")) or {}
        r = ((datos.get("camaras") or {}).get("resolucion") or {}).get("top")
        if r:
            return int(r[0]), int(r[1])
    except Exception:
        pass
    return 640, 480


def _abrir_camara(n: int):
    cap = cv2.VideoCapture(n)
    ancho, alto = _resolucion_top()
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, ancho)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, alto)
    if not cap.isOpened():
        raise SystemExit(f"No puedo abrir la cámara {n}")
    return cap


def _captura(args) -> np.ndarray:
    """Una imagen RGB de --imagen o de --camara."""
    if args.imagen:
        img = cv2.imread(args.imagen)
        if img is None:
            raise SystemExit(f"No puedo leer {args.imagen}")
        return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    cap = _abrir_camara(args.camara)
    for _ in range(10):  # la exposición automática necesita unos fotogramas
        ok, img = cap.read()
    cap.release()
    if not ok:
        raise SystemExit("La cámara no da imagen")
    return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)


def marcar_tapete(args) -> None:
    img = _captura(args)
    puntos: list[tuple[int, int]] = []

    def clic(evento, x, y, *_):
        if evento == cv2.EVENT_LBUTTONDOWN and len(puntos) < 4:
            puntos.append((x, y))

    ventana = "Marca las 4 esquinas del tapete (r: borrar, Enter: guardar, q: salir)"
    cv2.namedWindow(ventana)
    cv2.setMouseCallback(ventana, clic)
    while True:
        vis = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        for p in puntos:
            cv2.circle(vis, p, 5, (0, 0, 255), -1)
        if len(puntos) == 4:
            cv2.polylines(vis, [np.round(ordenar_esquinas(puntos)).astype(np.int32)], True, (0, 255, 255), 2)
        cv2.imshow(ventana, vis)
        k = cv2.waitKey(30) & 0xFF
        if k == ord("q"):
            cv2.destroyAllWindows()
            return
        if k == ord("r"):
            puntos.clear()
        if k in (13, 10) and len(puntos) == 4:
            break
    cv2.destroyAllWindows()
    esquinas = ordenar_esquinas(puntos)
    ruta = Path(args.config) if args.config else RUTA_PRODUCTO
    if guardar_tapete_px(esquinas, ruta):
        print(f"Guardado tapete_px en {ruta}")
    else:
        print(f"No existe {ruta}; añade esto a la configuración del producto:")
    print("tapete_px: " + formato_tapete(esquinas))


def en_vivo(args) -> None:
    vision = VisionProducto(args.config)
    carpeta = Path(args.capturas)
    if args.imagen:
        img = _captura(args)
        vista = None
        for k in range(30):  # 2 s de fotogramas iguales para que pasen los filtros temporales
            vista = vision.leer({"top": img}, k / 15.0)
        out = vision.anotar(img, vista)
        salida = str(Path(args.imagen).with_suffix("")) + "_anotada.png"
        cv2.imwrite(salida, cv2.cvtColor(out, cv2.COLOR_RGB2BGR))
        print(f"{vista}\nGuardada {salida}")
        if not args.sin_ventana:
            cv2.imshow("Garbi · visión", cv2.cvtColor(out, cv2.COLOR_RGB2BGR))
            cv2.waitKey(0)
        return
    cap = _abrir_camara(args.camara)
    t0 = time.monotonic()
    print("s: guardar captura (cruda y anotada) · q: salir")
    while True:
        ok, bgr = cap.read()
        if not ok:
            break
        img = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        vista = vision.leer({"top": img}, time.monotonic() - t0)
        out = cv2.cvtColor(vision.anotar(img, vista), cv2.COLOR_RGB2BGR)
        cv2.imshow("Garbi · visión (s: guardar, q: salir)", out)
        k = cv2.waitKey(1) & 0xFF
        if k == ord("q"):
            break
        if k == ord("s"):
            carpeta.mkdir(parents=True, exist_ok=True)
            nombre = time.strftime("vision_%H%M%S")
            cv2.imwrite(str(carpeta / f"{nombre}.png"), bgr)
            cv2.imwrite(str(carpeta / f"{nombre}_anotada.png"), out)
            print(f"Guardadas {carpeta / nombre}*.png")
    cap.release()
    cv2.destroyAllWindows()
    vision.cerrar()


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="python -m garbi.producto.vision", description=__doc__.split("\n")[0])
    ap.add_argument("--camara", type=int, default=0, help="índice de la cámara de arriba")
    ap.add_argument("--imagen", help="probar con una foto en lugar de la cámara")
    ap.add_argument("--config", help="yaml del producto (por defecto garbi/producto/garbi_producto.yaml)")
    ap.add_argument("--marcar-tapete", action="store_true", help="marcar las 4 esquinas del tapete con clics")
    ap.add_argument("--capturas", default="capturas", help="carpeta donde guardar con la tecla s")
    ap.add_argument("--sin-ventana", action="store_true", help="con --imagen: solo guardar la anotada")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO)
    if args.marcar_tapete:
        marcar_tapete(args)
    else:
        en_vivo(args)


if __name__ == "__main__":
    main()
