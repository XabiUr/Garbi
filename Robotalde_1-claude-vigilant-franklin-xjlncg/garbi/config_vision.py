"""Umbrales de color de la visión de Garbi en el sitio (`garbi/config_vision.yaml`).

Lo escribe `herramientas/garbi_ajustar_color.py` (deslizadores HSV) y lo leen la percepción y las herramientas:

    from garbi.config_vision import cargar_config_vision, mascara_color
    rangos = cargar_config_vision()            # {"tapete_azul": RangoHSV(bajo, alto, nota), ...}
    m = mascara_color(img_rgb, rangos["bola_naranja"])

Formato del yaml (versión 1): `colores: {<nombre>: {bajo: [H, S, V], alto: [H, S, V], nota: ...}}`, HSV de OpenCV
(H 0-179) sobre la imagen RGB. Si `bajo.H > alto.H`, el tono da la vuelta (piel, rojo). Los nombres son fijos:
`COLORES`. Un color que falte en el archivo toma el valor de partida (`POR_DEFECTO`, los de la simulación).

`aplicar_a_percepcion(rangos)` copia los umbrales a las constantes de `garbi.percepcion` y `garbi.calibracion` que
existan (tapete, bola, anillo), para quien use esas constantes.

**Percepción (F1, solución final):** `garbi.percepcion.Percepcion(config=...)` lee este mismo yaml con
`cargar_config(fuente)` → `ConfigVision`: los 6 colores de arriba más una sección opcional `parametros:` con lo que no
es un color de la herramienta (umbrales numéricos de la madera, la pegatina, la bola y las manos; el amarillo del robot,
el serrín y el gris de la broca). Lo que falte toma el valor de `PARAMETROS_POR_DEFECTO` (ajustado en la simulación).
`guardar_config_vision` conserva la sección `parametros` del archivo que reescribe. Para ver las máscaras de una
imagen:

    python -m garbi.config_vision imagen_top.png [config.yaml]
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

RUTA_DEFECTO = Path(__file__).with_name("config_vision.yaml")
VERSION = 1
COLORES = ("tapete_azul", "madera", "bola_naranja", "anillo_verde", "piel", "pegatina")


@dataclass
class RangoHSV:
    bajo: tuple[int, int, int]
    alto: tuple[int, int, int]
    nota: str = ""

    def __post_init__(self):
        self.bajo = _hsv_valido(self.bajo)
        self.alto = _hsv_valido(self.alto)

    @property
    def da_la_vuelta(self) -> bool:
        return self.bajo[0] > self.alto[0]

    def a_dict(self) -> dict:
        return {"bajo": list(self.bajo), "alto": list(self.alto), "nota": self.nota}


def _hsv_valido(v) -> tuple[int, int, int]:
    v = [int(round(float(x))) for x in v]
    if len(v) != 3:
        raise ValueError(f"un HSV tiene 3 valores, no {v}")
    return (int(np.clip(v[0], 0, 179)), int(np.clip(v[1], 0, 255)), int(np.clip(v[2], 0, 255)))


POR_DEFECTO: dict[str, RangoHSV] = {
    "tapete_azul": RangoHSV((100, 100, 35), (130, 255, 255), "tapete azul de corte (esquinas → cámara de arriba)"),
    # ajustados en la simulación (F1): la madera clara es más amarilla (H ≥ 14) que la piel y la piel menos saturada
    # que la bola; con la luz del sitio, retocar con la herramienta
    "madera": RangoHSV((14, 15, 80), (32, 120, 255), "madera clara sin vinilo (también en la sombra del taladro)"),
    "bola_naranja": RangoHSV((5, 150, 110), (22, 255, 255), "bola naranja fluorescente del taladro"),
    "anillo_verde": RangoHSV((40, 80, 25), (66, 255, 255), "anillo verde lima de la boquilla (calibración robot-mesa)"),
    "piel": RangoHSV((0, 55, 110), (15, 165, 255), "manos (respaldo de MediaPipe)"),
    "pegatina": RangoHSV((140, 90, 70), (175, 255, 255), "pegatina de color en una esquina de la madera (magenta por "
                         "defecto; resuelve el giro de 180°)"),
}

CABECERA = """\
# Umbrales de color de la visión de Garbi en el sitio (los escribe herramientas/garbi_ajustar_color.py).
#
# Formato (versión 1), para quien lea este archivo desde la percepción (garbi/config_vision.py lo carga):
#   colores:
#     <nombre>:
#       bajo: [H, S, V]   # HSV de OpenCV: H 0-179, S 0-255, V 0-255 (imagen RGB → cv2.COLOR_RGB2HSV)
#       alto: [H, S, V]
#       nota: texto libre
#   Si bajo.H > alto.H, el tono da la vuelta (p. ej. piel o rojo: H de 170 a 179 y de 0 a 15).
#
# Nombres fijos (no cambiarlos: los usan la percepción, las herramientas y los tests):
#   tapete_azul, madera, bola_naranja, anillo_verde, piel, pegatina
"""


def copia_por_defecto() -> dict[str, RangoHSV]:
    return {k: RangoHSV(v.bajo, v.alto, v.nota) for k, v in POR_DEFECTO.items()}


def cargar_config_vision(ruta=None) -> dict[str, RangoHSV]:
    """Lee el yaml (por defecto `garbi/config_vision.yaml`). Si no existe, los valores de partida."""
    import yaml

    ruta = Path(ruta) if ruta is not None else RUTA_DEFECTO
    rangos = copia_por_defecto()
    if not ruta.exists():
        return rangos
    datos = yaml.safe_load(ruta.read_text(encoding="utf-8")) or {}
    for nombre, v in (datos.get("colores") or {}).items():
        if nombre not in COLORES:
            continue  # un nombre desconocido no rompe nada: se ignora
        rangos[nombre] = RangoHSV(v["bajo"], v["alto"], str(v.get("nota", rangos[nombre].nota)))
    return rangos


def guardar_config_vision(rangos: dict[str, RangoHSV], ruta=None) -> Path:
    """Escribe el yaml con su cabecera explicativa, en el orden de `COLORES`. Conserva la sección `parametros` del
    archivo que había (la de la percepción)."""
    import yaml

    ruta = Path(ruta) if ruta is not None else RUTA_DEFECTO
    ruta.parent.mkdir(parents=True, exist_ok=True)
    cuerpo = {"version": VERSION, "colores": {n: rangos[n].a_dict() for n in COLORES if n in rangos}}
    if ruta.exists():
        previos = yaml.safe_load(ruta.read_text(encoding="utf-8")) or {}
        if previos.get("parametros"):
            cuerpo["parametros"] = previos["parametros"]
    texto = CABECERA + yaml.safe_dump(cuerpo, allow_unicode=True, sort_keys=False, default_flow_style=None, width=200)
    ruta.write_text(texto, encoding="utf-8")
    return ruta


def mascara_hsv(hsv: np.ndarray, rango: RangoHSV) -> np.ndarray:
    """Máscara uint8 (0/255) de los píxeles HSV dentro del rango (con la vuelta del tono si hace falta)."""
    import cv2

    lo, hi = np.array(rango.bajo, np.uint8), np.array(rango.alto, np.uint8)
    if not rango.da_la_vuelta:
        return cv2.inRange(hsv, lo, hi)
    a = cv2.inRange(hsv, np.array([lo[0], lo[1], lo[2]], np.uint8), np.array([179, hi[1], hi[2]], np.uint8))
    b = cv2.inRange(hsv, np.array([0, lo[1], lo[2]], np.uint8), np.array([hi[0], hi[1], hi[2]], np.uint8))
    return a | b


def mascara_color(img_rgb: np.ndarray, rango: RangoHSV) -> np.ndarray:
    import cv2

    return mascara_hsv(cv2.cvtColor(np.ascontiguousarray(img_rgb), cv2.COLOR_RGB2HSV), rango)


def rango_desde_muestra(hsv_pixeles: np.ndarray, margen=(8, 60, 60), nota: str = "") -> RangoHSV:
    """Rango alrededor de unos píxeles HSV (Nx3) pinchados en la imagen: mediana ± margen. El tono se trata como
    circular (0 y 179 son vecinos)."""
    p = np.asarray(hsv_pixeles, float).reshape(-1, 3)
    ang = p[:, 0] * (2 * np.pi / 180.0)
    h = (np.degrees(np.arctan2(np.sin(ang).mean(), np.cos(ang).mean())) / 2.0) % 180.0
    s, v = np.median(p[:, 1]), np.median(p[:, 2])
    dh = max(margen[0], float(np.max(np.abs(((p[:, 0] - h + 90) % 180) - 90))) + 2)
    h_lo, h_hi = (h - dh) % 180, (h + dh) % 180
    return RangoHSV((h_lo, s - margen[1], v - margen[2]), (h_hi, s + margen[1], v + margen[2]), nota)


# constantes de la percepción actual que corresponden a cada color (módulo, nombre bajo, nombre alto)
_EN_PERCEPCION = {
    "tapete_azul": ("garbi.percepcion", "AZUL_BAJO", "AZUL_ALTO"),
    "bola_naranja": ("garbi.percepcion", "NARANJA_BAJO", "NARANJA_ALTO"),
    "anillo_verde": ("garbi.calibracion", "VERDE_BAJO", "VERDE_ALTO"),
}


def aplicar_a_percepcion(rangos: dict[str, RangoHSV]) -> list[str]:
    """Copia los umbrales a las constantes de la percepción que existan. Un rango que da la vuelta no se puede pasar
    a un solo `cv2.inRange` y se salta. Devuelve lo aplicado (`"garbi.percepcion.NARANJA_BAJO"`, ...)."""
    import importlib

    hechos = []
    for color, (modulo, n_bajo, n_alto) in _EN_PERCEPCION.items():
        r = rangos.get(color)
        if r is None or r.da_la_vuelta:
            continue
        try:
            m = importlib.import_module(modulo)
        except Exception:
            continue
        for nombre, valor in ((n_bajo, r.bajo), (n_alto, r.alto)):
            if hasattr(m, nombre):
                setattr(m, nombre, tuple(valor))
                hechos.append(f"{modulo}.{nombre}")
    return hechos


# --- percepción (F1): colores + parámetros numéricos -------------------------------------------------------------
# Nombres de sección que usa `garbi.percepcion` → color del yaml
SECCION_A_COLOR = {"tapete": "tapete_azul", "madera": "madera", "pegatina": "pegatina", "bola": "bola_naranja",
                   "manos": "piel", "anillo": "anillo_verde"}

PARAMETROS_POR_DEFECTO: dict = {
    # lado de fuera del borde de la madera: al menos esta fracción de lo azul (relativo al brillo) que es el tapete
    # (la manga azul de la persona no cuenta como tapete)
    "tapete": {"fuera_min": 0.75},
    # puntos de borde válidos (de ~220) para aceptar una pose nueva, y para aceptar un salto > salto_mm (mm o grados)
    "madera": {"bordes_min": 40, "salto_mm": 6.0, "bordes_min_salto": 80},
    # pegatina: área mínima (px a 640 × 480) y distancia máxima (mm) a donde la pone una de las dos orientaciones
    "pegatina": {"area_min": 40, "distancia_max": 35.0},
    "bola": {"area": [30, 6000]},  # px a 640 × 480
    # manos por color: área (px) y altura (mm) a la que se proyecta el centro de la palma (mano sobre el tapete)
    "manos": {"area": [350, 30000], "altura_palma": 14.0},
    "broca": {"sat_max": 60, "v_min": 70, "v_max": 240},  # gris de la broca (cámara de la muñeca)
    "robot": {"bajo": [15, 100, 60], "alto": [35, 255, 255]},  # amarillo del SO-101 (cámara de la muñeca)
    # serrín: más saturado que la cara de madera clara (en la simulación, pino sobre abedul). Con madera clara de
    # verdad apenas se distingue: la limpieza de la solución final es fija y no depende de esto
    "serrin": {"bajo": [16, 95, 90], "alto": [32, 200, 255]},
    # círculo morado de la trasera del taladro (producto, `garbi.producto.vision`). H ≥ 128 para no tocar el azul del
    # tapete (H ≤ 130 con la saturación alta); se solapa con el magenta de la pegatina (140-175), que el producto no usa
    "morado": {"bajo": [128, 80, 60], "alto": [165, 255, 255]},
}


def _mezclar(base: dict, nuevo: dict) -> dict:
    import copy

    out = copy.deepcopy(base)
    for k, v in (nuevo or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _mezclar(out[k], v)
        else:
            out[k] = v
    return out


@dataclass
class ConfigVision:
    """Umbrales de la percepción: `rangos` (los 6 colores del yaml) y `parametros` (por secciones). `cfg["madera"]`
    da los parámetros de esa sección; `cfg.mascara(hsv, seccion)` la máscara de su color (secciones de
    `SECCION_A_COLOR`, o "robot" y "serrin", que están en `parametros`)."""
    rangos: dict
    parametros: dict

    def __getitem__(self, seccion: str) -> dict:
        return self.parametros.get(seccion, {})

    def rango(self, seccion: str) -> RangoHSV:
        if seccion in SECCION_A_COLOR:
            return self.rangos[SECCION_A_COLOR[seccion]]
        p = self.parametros[seccion]
        return RangoHSV(p["bajo"], p["alto"])

    def mascara(self, hsv: np.ndarray, seccion: str) -> np.ndarray:
        return mascara_hsv(hsv, self.rango(seccion))


def cargar_config(fuente=None) -> ConfigVision:
    """`fuente`: ruta a un yaml (por defecto `garbi/config_vision.yaml`), una `ConfigVision` o un dict con el mismo
    formato que el yaml (`colores` y/o `parametros`)."""
    import yaml

    if isinstance(fuente, ConfigVision):
        return fuente
    if isinstance(fuente, dict):
        datos = fuente
    else:
        ruta = Path(fuente) if fuente is not None else RUTA_DEFECTO
        if fuente is not None and not ruta.exists():
            raise FileNotFoundError(f"No encuentro la configuración de visión {ruta}")
        datos = (yaml.safe_load(ruta.read_text(encoding="utf-8")) or {}) if ruta.exists() else {}
    rangos = copia_por_defecto()
    for nombre, v in (datos.get("colores") or {}).items():
        if nombre in COLORES:
            rangos[nombre] = RangoHSV(v["bajo"], v["alto"], str(v.get("nota", rangos[nombre].nota)))
    return ConfigVision(rangos, _mezclar(PARAMETROS_POR_DEFECTO, datos.get("parametros") or {}))


_por_defecto: ConfigVision | None = None


def config_por_defecto() -> ConfigVision:
    """La del yaml del repositorio (se lee una vez)."""
    global _por_defecto
    if _por_defecto is None:
        _por_defecto = cargar_config()
    return _por_defecto


def mascaras(img_rgb: np.ndarray, cfg: ConfigVision | None = None) -> np.ndarray:
    """Mosaico (RGB) con la imagen y las máscaras de cada color, para ajustar los umbrales."""
    import cv2

    cfg = cfg or config_por_defecto()
    hsv = cv2.cvtColor(np.ascontiguousarray(img_rgb), cv2.COLOR_RGB2HSV)
    teselas = [img_rgb]
    for seccion in ("tapete", "madera", "pegatina", "bola", "manos", "serrin"):
        t = cv2.cvtColor(cfg.mascara(hsv, seccion), cv2.COLOR_GRAY2RGB)
        cv2.putText(t, seccion, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 0, 0), 2)
        teselas.append(t)
    return np.vstack([np.hstack(teselas[:4]), np.hstack(teselas[4:] + [np.zeros_like(img_rgb)])])


if __name__ == "__main__":
    import sys

    import cv2

    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    img = cv2.cvtColor(cv2.imread(sys.argv[1]), cv2.COLOR_BGR2RGB)
    cfg = cargar_config(sys.argv[2] if len(sys.argv) > 2 else None)
    salida = str(Path(sys.argv[1]).with_suffix("")) + "_mascaras.png"
    cv2.imwrite(salida, cv2.cvtColor(mascaras(img, cfg), cv2.COLOR_RGB2BGR))
    print(f"Guardado {salida}")
