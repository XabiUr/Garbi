"""Genera el material de hardware de LeWelder a partir de `lewelder/contrato.py`.

El contrato es la única fuente de verdad de medidas. Este script lo lee y produce lo que Andoni necesita para el
CAD y la impresión, sin números copiados a mano:

- `contrato.md`: medidas, tablas, comprobaciones (solapes, cámara) y requisitos de cada pieza.
- `planos/*.png` y `planos/*.svg`: vistas superiores y secciones acotadas.
- `aruco/*.png` (600 ppp), `aruco/marcadores_a4.pdf` y `aruco/tablero_calibracion_a4.pdf` (vectoriales, A4, 100 %).
- `lista_material.md`: qué imprimir, qué comprar y en qué orden.

Si la simulación mueve los anclajes en el contrato, basta con volver a ejecutarlo. Es idempotente: con las mismas
entradas escribe los mismos bytes (sin fechas ni marcas de tiempo).

Uso:
    python herramientas/generar_hardware.py              # escribe en hardware/
    python herramientas/generar_hardware.py --salida DIR
    python herramientas/generar_hardware.py --v2         # material de la v2 en hardware/v2/
"""
from __future__ import annotations

import argparse
import inspect
import math
import shutil
import subprocess
import sys
import tempfile
import zlib
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))
from lewelder import contrato as c  # noqa: E402
from lewelder.camara_sintetica import PoseCamara  # noqa: E402

# =================================================================================================================
# Recomendaciones de fabricación (no son contrato: solo afectan al CAD, no al software)
# =================================================================================================================
PPP = 600  # resolución de los PNG de marcadores
HOLGURA_ENCAJE = 0.3  # mm por lado entre la pieza y los topes de la loseta (ajustar con la pieza de prueba)
TOPE_ALTO = 4.0  # mm sobre la superficie de la loseta (menor que CHAPA_GROSOR para no estorbar a la antorcha)
TOPE_GROSOR = 4.0
TOPE_LARGO = 20.0  # largo de cada brazo de los topes en L de las esquinas
CHAFLAN_LLAVE = 10.0  # chaflán a 45° en la esquina (fin del cordón, +Y) de cada pieza: solo entra en una posición
PROFUNDIDAD_JUNTA = 3.0  # ranura de la unión a tope (ancho HOLGURA_JUNTA); el resto une las dos chapas
HOLGURA_IMAN_FONDO = 0.2  # el imán queda 0,2 mm por debajo de la cara: la pieza apoya en plástico, no en imán
# Valores que la rama principal ya tiene en el contrato; se leen de allí si existen.
MARGEN_BLANCO = float(getattr(c, "MARGEN_BLANCO_ARUCO", 5.0))  # mm de borde blanco alrededor de cada ArUco
PIEZA_EN_ANCLAJE = tuple(getattr(c, "PIEZA_EN_ANCLAJE", (0.0, 0.0, c.ALTURA_SUPERFICIE_PIEZA)))
REBAJE_PEGATINA = (0.4, 0.4)  # (holgura total en XY, profundidad) del rebaje donde se pega cada ArUco
MARGEN_LOSETA = 3.0  # borde de la loseta más allá del margen blanco del ArUco del anclaje
TORNILLO_LOSETA = 4.5  # diámetro de los agujeros pasantes para fijar la loseta al tablero (M4 o tirafondo 4 mm)
LETRA_ALTO = 10.0  # letra del anclaje grabada en la loseta
SEPARACION_MIN_LOSETAS = 0.5  # mm: los anclajes van en fila y las losetas contiguas se imprimen unidas (base única por tramos)
MARGEN_ROBOT = 15.0  # mm libres alrededor de la base del robot

# Medidas del SO-101 sacadas del modelo MuJoCo de `assets/so101` (sin cargar MuJoCo aquí para que el script sea
# ligero). Marco del cuerpo `base` = origen de la mesa del contrato.
BASE_ROBOT_X = (-31.0, 64.6)  # mm, huella de la base (placa + soporte del motor)
BASE_ROBOT_Y = (-55.5, 55.5)
BASE_ROBOT_ALTO = 69.6
EJE_HOMBRO_X = 38.8  # el eje de giro del hombro (shoulder_pan) está 38,8 mm por delante del origen
# Dedos de la pinza (aprox., pinza en posición media). "a" = distancia hacia atrás desde la punta del dedo fijo.
PUNTA_DEDO_SOBRE_GRIPPERFRAME = 6.3  # el extremo del dedo fijo está 6,3 mm por delante del sitio gripperframe
DEDOS = [  # (a mm, ancho dedo fijo, grosor dedo fijo, ancho dedo móvil, grosor dedo móvil)
    (8.0, 12.2, 8.7, 12.4, 10.6),
    (16.0, 14.0, 10.0, 14.2, 12.2),
    (26.0, 15.5, 11.9, 15.6, 12.8),
    (36.0, 17.1, 15.3, 16.9, 14.0),
    (46.0, 19.2, 17.0, 19.1, 14.9),
]

# Cámara de seguimiento: la pose es la de todo el software (`PoseCamara.por_defecto()` de
# `lewelder/camara_sintetica.py`); aquí solo se calcula qué campo de visión hace falta para una webcam 1080p.
FOV_HORIZONTAL = (65.0, 70.0, 74.0, 78.0)  # webcams típicas (65° = la de la cámara sintética)
RESOLUCION = (1920, 1080)
MARGEN_IMAGEN = 0.05  # fracción libre en cada borde de la imagen
ANCHO_IMPRESORA = 250.0  # mm de cama (Bambu/Prusa MK4); los tramos de la base deben caber

# Tipografía (Liberation Sans tiene las mismas métricas que Helvetica, la fuente estándar del PDF)
FUENTES = {
    False: ["/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "Arial.ttf", "DejaVuSans.ttf"],
    True: ["/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
           "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "Arial Bold.ttf", "DejaVuSans-Bold.ttf"],
}

ROJO, VERDE, AZUL, GRIS, GRIS_CLARO, NARANJA = "#c62828", "#2e7d32", "#1565c0", "#757575", "#e0e0e0", "#ef6c00"


def fmt(v: float, dec: int = 2) -> str:
    """Número en formato español, sin ceros sobrantes: 20.75 → '20,75', 10.0 → '10'."""
    s = f"{v:.{dec}f}"
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    if s in ("-0", ""):
        s = "0"
    return s.replace(".", ",")


# =================================================================================================================
# Geometría de piezas, losetas y anclajes
# =================================================================================================================
def ancho_base(tipo: c.TipoPieza) -> float:
    """Ancho (Y) de la base de la pieza según el contrato."""
    if c.TipoPieza(tipo) is c.TipoPieza.RECTA:
        return 2 * c.CHAPA_ANCHO + c.HOLGURA_JUNTA
    return 2 * c.CHAPA_ANCHO


ANCHO_HUELLA = max(ancho_base(t) for t in c.TipoPieza)  # una sola huella para las dos piezas
X_PIEZA = (-c.MARGEN_X, c.LONGITUD_CORDON + c.MARGEN_X)


def modulo_aruco(lado: float) -> float:
    """Lado de un módulo: un 4x4 tiene 4 bits + 1 de borde negro a cada lado = 6 módulos."""
    return lado / 6


def lado_con_margen(lado: float) -> float:
    return lado + 2 * MARGEN_BLANCO


def rect_centrado(cx: float, cy: float, lado: float) -> tuple[float, float, float, float]:
    return (cx - lado / 2, cy - lado / 2, cx + lado / 2, cy + lado / 2)


def huella_pieza_local() -> tuple[float, float, float, float]:
    return (X_PIEZA[0], -ANCHO_HUELLA / 2, X_PIEZA[1], ANCHO_HUELLA / 2)


def pieza_a_anclaje(x: float, y: float) -> tuple[float, float]:
    """Punto del marco de la pieza → marco del anclaje (PIEZA_EN_ANCLAJE en XY)."""
    return x + PIEZA_EN_ANCLAJE[0], y + PIEZA_EN_ANCLAJE[1]


def huella_en_anclaje() -> tuple[float, float, float, float]:
    x0, y0, x1, y1 = huella_pieza_local()
    return (*pieza_a_anclaje(x0, y0), *pieza_a_anclaje(x1, y1))


def aruco_anclaje_local(con_margen: bool = True) -> tuple[float, float, float, float]:
    lado = lado_con_margen(c.LADO_ARUCO_ANCLAJE) if con_margen else c.LADO_ARUCO_ANCLAJE
    return rect_centrado(c.ARUCO_EN_ANCLAJE[0], c.ARUCO_EN_ANCLAJE[1], lado)


def aruco_pieza_local(con_margen: bool = True) -> tuple[float, float, float, float]:
    lado = lado_con_margen(c.LADO_ARUCO_PIEZA) if con_margen else c.LADO_ARUCO_PIEZA
    return rect_centrado(c.ARUCO_EN_PIEZA[0], c.ARUCO_EN_PIEZA[1], lado)


def _hacia_fuera(v: float, paso: float = 0.5) -> float:
    return math.floor(v / paso) * paso if v < 0 else math.ceil(v / paso) * paso


def loseta_local() -> tuple[float, float, float, float]:
    """Rectángulo de la loseta de un anclaje en su marco (= marco de la pieza), redondeado hacia fuera a 0,5 mm."""
    hx0, hy0, hx1, hy1 = huella_en_anclaje()
    ext = HOLGURA_ENCAJE + TOPE_GROSOR
    ax0, ay0, ax1, ay1 = aruco_anclaje_local()
    x0 = min(hx0 - ext, ax0 - MARGEN_LOSETA)
    x1 = max(hx1 + ext, ax1 + MARGEN_LOSETA)
    y0 = min(hy0 - ext, ay0 - MARGEN_LOSETA)
    y1 = max(hy1 + ext, ay1 + MARGEN_LOSETA)
    return tuple(_hacia_fuera(v) for v in (x0, y0, x1, y1))


def imanes_local() -> list[tuple[float, float]]:
    """Centros de los imanes (iguales en la cara inferior de la pieza y en la cara superior de la loseta)."""
    xs = (c.LONGITUD_CORDON / 2 - 50.0, c.LONGITUD_CORDON / 2 + 50.0)
    ys = (-(c.HOLGURA_JUNTA / 2 + c.CHAPA_ANCHO / 2), c.HOLGURA_JUNTA / 2 + c.CHAPA_ANCHO / 2)
    pos = [(x, y) for x in xs for y in ys]
    assert len(pos) == c.IMANES_POR_PIEZA, "la disposición de imanes asume 4 por pieza"
    return pos


def tornillos_loseta() -> list[tuple[float, float]]:
    """Dos agujeros de fijación en la franja del ArUco del anclaje, lejos de topes, imanes y marcador."""
    lx0, ly0, _, _ = loseta_local()
    y = (ly0 + (-ANCHO_HUELLA / 2 - HOLGURA_ENCAJE - TOPE_GROSOR)) / 2
    return [(0.0, y), (c.LONGITUD_CORDON, y)]


def topes_local() -> list[list[tuple[float, float]]]:
    """Polígonos de los topes en L de las cuatro esquinas y del bloque llave (chaflán) en (fin, +Y)."""
    hx0, hy0, hx1, hy1 = huella_en_anclaje()
    h, g, l = HOLGURA_ENCAJE, TOPE_GROSOR, TOPE_LARGO
    x0, y0, x1, y1 = hx0 - h, hy0 - h, hx1 + h, hy1 + h  # caras interiores
    polis = []
    for sx, sy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        xc = x0 if sx < 0 else x1  # esquina interior
        yc = y0 if sy < 0 else y1
        # L: brazo a lo largo de X y brazo a lo largo de Y, por fuera de la huella
        pts = [(xc + sx * g, yc + sy * g), (xc - sx * l, yc + sy * g), (xc - sx * l, yc), (xc, yc),
               (xc, yc - sy * l), (xc + sx * g, yc - sy * l)]
        polis.append(pts)
    cb = bloque_llave()
    polis.append([(x1, y1), (x1, y1 - cb), (x1 - cb, y1)])
    return polis


def bloque_llave() -> float:
    """Cateto del bloque triangular de la loseta para que el chaflán de la pieza quede a HOLGURA_ENCAJE."""
    return CHAFLAN_LLAVE + 2 * HOLGURA_ENCAJE - HOLGURA_ENCAJE * math.sqrt(2)


def ejes_anclaje(an: c.Anclaje) -> tuple[np.ndarray, np.ndarray]:
    """Direcciones X (avance del cordón) e Y de la pieza en la mesa. giro 0 → el cordón avanza en +Y de la mesa."""
    g = math.radians(an.giro)
    return np.array([-math.sin(g), math.cos(g)]), np.array([-math.cos(g), -math.sin(g)])


def a_mesa(an: c.Anclaje, xp: float, yp: float) -> tuple[float, float]:
    ex, ey = ejes_anclaje(an)
    p = np.array([an.x, an.y]) + xp * ex + yp * ey
    return float(p[0]), float(p[1])


def a_pieza(an: c.Anclaje, xm: float, ym: float) -> tuple[float, float]:
    ex, ey = ejes_anclaje(an)
    d = np.array([xm - an.x, ym - an.y])
    return float(d @ ex), float(d @ ey)


def rect_a_mesa(an: c.Anclaje, r: tuple[float, float, float, float]) -> list[tuple[float, float]]:
    x0, y0, x1, y1 = r
    return [a_mesa(an, x, y) for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))]


def _area(pol) -> float:
    return 0.5 * sum(p[0] * q[1] - q[0] * p[1] for p, q in zip(pol, pol[1:] + pol[:1]))


def _ccw(pol):
    return pol if _area(pol) >= 0 else pol[::-1]


def interseccion(a, b) -> list[tuple[float, float]]:
    """Intersección de dos polígonos convexos (Sutherland-Hodgman)."""
    salida = _ccw(list(a))
    clip = _ccw(list(b))
    for c1, c2 in zip(clip, clip[1:] + clip[:1]):
        entrada, salida = salida, []
        if not entrada:
            break

        def dentro(p):
            return (c2[0] - c1[0]) * (p[1] - c1[1]) - (c2[1] - c1[1]) * (p[0] - c1[0]) >= -1e-9

        def cruce(p, q):
            a1, b1 = c2[1] - c1[1], c1[0] - c2[0]
            c_1 = a1 * c1[0] + b1 * c1[1]
            a2, b2 = q[1] - p[1], p[0] - q[0]
            c_2 = a2 * p[0] + b2 * p[1]
            det = a1 * b2 - a2 * b1
            return ((b2 * c_1 - b1 * c_2) / det, (a1 * c_2 - a2 * c_1) / det)

        for i, p in enumerate(entrada):
            q = entrada[i - 1]
            if dentro(p):
                if not dentro(q):
                    salida.append(cruce(q, p))
                salida.append(p)
            elif dentro(q):
                salida.append(cruce(q, p))
    return salida


def area_solape(a, b) -> float:
    pol = interseccion(a, b)
    return abs(_area(pol)) if len(pol) >= 3 else 0.0


def separacion(a, b) -> float:
    """Separación por ejes separadores (cota inferior de la distancia; negativa si se solapan)."""
    mejor = -math.inf
    for pol in (a, b):
        for p, q in zip(pol, pol[1:] + pol[:1]):
            n = np.array([q[1] - p[1], p[0] - q[0]], dtype=float)
            n /= np.linalg.norm(n)
            pa = [n @ np.array(v) for v in a]
            pb = [n @ np.array(v) for v in b]
            mejor = max(mejor, min(pb) - max(pa), min(pa) - max(pb))
    return float(mejor)


def huellas(an: c.Anclaje) -> dict[str, list]:
    return {
        "pieza": rect_a_mesa(an, huella_en_anclaje()),
        "aruco": rect_a_mesa(an, aruco_anclaje_local()),
        "loseta": rect_a_mesa(an, loseta_local()),
    }


def base_robot(margen: float = 0.0) -> list[tuple[float, float]]:
    x0, x1 = BASE_ROBOT_X
    y0, y1 = BASE_ROBOT_Y
    return [(x0 - margen, y0 - margen), (x1 + margen, y0 - margen), (x1 + margen, y1 + margen),
            (x0 - margen, y1 + margen)]


@dataclass
class Problema:
    tipo: str  # "pieza", "loseta" o "robot"
    a: str
    b: str
    area: float  # mm² de solape (0 si solo están demasiado cerca)
    separacion: float  # mm (negativa = se solapan)

    def texto(self) -> str:
        if self.tipo == "robot":
            return (f"la loseta {self.a} invade la base del robot (+{fmt(MARGEN_ROBOT, 0)} mm de margen): "
                    f"{fmt(self.area, 0)} mm²")
        que = "las huellas de las piezas (con su ArUco)" if self.tipo == "pieza" else "las losetas"
        if self.area > 0:
            return f"{que} {self.a} y {self.b} se solapan {fmt(self.area, 0)} mm²"
        return f"{que} {self.a} y {self.b} quedan a {fmt(self.separacion, 1)} mm (< {fmt(SEPARACION_MIN_LOSETAS)} mm)"


def comprobar_huellas(anclajes: dict[str, c.Anclaje]) -> list[Problema]:
    """Devuelve los problemas: solapes de piezas+ArUco, losetas solapadas o demasiado juntas, robot invadido."""
    problemas = []
    nombres = sorted(anclajes)
    hs = {n: huellas(anclajes[n]) for n in nombres}
    for i, a in enumerate(nombres):
        for b in nombres[i + 1:]:
            area = sum(area_solape(p, q) for p in (hs[a]["pieza"], hs[a]["aruco"])
                       for q in (hs[b]["pieza"], hs[b]["aruco"]))
            if area > 1e-6:
                problemas.append(Problema("pieza", a, b, area, -1.0))
            area_l = area_solape(hs[a]["loseta"], hs[b]["loseta"])
            sep = separacion(hs[a]["loseta"], hs[b]["loseta"])
            if area_l > 1e-6 or sep < SEPARACION_MIN_LOSETAS - 1e-9:
                problemas.append(Problema("loseta", a, b, area_l, sep))
    robot = base_robot(MARGEN_ROBOT)
    for n in nombres:
        area = area_solape(hs[n]["loseta"], robot)
        if area > 1e-6:
            problemas.append(Problema("robot", n, "robot", area, separacion(hs[n]["loseta"], robot)))
    return problemas


def huellas_sin_solape(anclajes: dict[str, c.Anclaje]) -> bool:
    """True si ninguna pieza (con su ArUco de anclaje) pisa a otra."""
    return not any(p.tipo == "pieza" for p in comprobar_huellas(anclajes))


def cordon_en_mesa(an: c.Anclaje) -> tuple[tuple[float, float], tuple[float, float]]:
    return a_mesa(an, *pieza_a_anclaje(0.0, 0.0)), a_mesa(an, *pieza_a_anclaje(c.LONGITUD_CORDON, 0.0))


def distancia_hombro(an: c.Anclaje) -> tuple[float, float]:
    """Distancia horizontal mínima y máxima del cordón al eje del hombro (orientativa para el alcance)."""
    ds = []
    for k in range(c.N_TRAMOS + 1):
        x, y = a_mesa(an, *pieza_a_anclaje(k * c.TAMANO_TRAMO, 0.0))
        ds.append(math.hypot(x - EJE_HOMBRO_X, y))
    return min(ds), max(ds)


def sep_min_losetas(anclajes) -> float:
    """Separación mínima entre losetas vecinas (las que están a menos de 10 mm)."""
    hs = [huellas(an)["loseta"] for _, an in sorted(anclajes.items())]
    seps = [separacion(a, b) for i, a in enumerate(hs) for b in hs[i + 1:]]
    cerca = [d for d in seps if d < 10.0]
    return min(cerca) if cerca else min(seps)


def dims_base(anclajes=None) -> tuple[float, float]:
    """Lado mayor y menor del rectángulo que envuelve todas las losetas (la base única)."""
    x0, y0, x1, y1 = zona_trabajo(anclajes or c.ANCLAJES)
    a, b = x1 - x0, y1 - y0
    return max(a, b), min(a, b)


def dims_tablero(anclajes=None) -> tuple[float, float]:
    """Tablero común (X, Y) que abarca robot y base con 30 mm de margen, redondeado a 50 mm."""
    x0, y0, x1, y1 = zona_trabajo(anclajes or c.ANCLAJES)
    x0, y0 = min(x0, BASE_ROBOT_X[0]) - 30, min(y0, BASE_ROBOT_Y[0]) - 30
    x1, y1 = max(x1, BASE_ROBOT_X[1]) + 30, max(y1, BASE_ROBOT_Y[1]) + 30
    return math.ceil((x1 - x0) / 50) * 50, math.ceil((y1 - y0) / 50) * 50


def zona_trabajo(anclajes: dict[str, c.Anclaje]) -> tuple[float, float, float, float]:
    pts = [p for an in anclajes.values() for p in huellas(an)["loseta"]]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


# =================================================================================================================
# Cámara de seguimiento
# =================================================================================================================
Z_SUPERFICIE = c.ALTURA_BASE_ANCLAJES + PIEZA_EN_ANCLAJE[2]  # Z de la mesa donde está Z = 0 de la pieza


@dataclass
class Camara:
    pos: np.ndarray  # mm, marco de la mesa
    adelante: np.ndarray
    derecha: np.ndarray
    arriba: np.ndarray
    fov_h: float
    fov_v: float

    def proyectar(self, p) -> tuple[float, float, float]:
        """(u, v, profundidad) normalizados: |u|,|v| <= 1 dentro de la imagen."""
        v = np.asarray(p, dtype=float) - self.pos
        z = v @ self.adelante
        if z <= 1e-6:
            return math.inf, math.inf, z
        u = (v @ self.derecha) / z / math.tan(math.radians(self.fov_h) / 2)
        w = (v @ self.arriba) / z / math.tan(math.radians(self.fov_v) / 2)
        return u, w, z


def fov_vertical(fov_h: float, aspecto: float = RESOLUCION[0] / RESOLUCION[1]) -> float:
    return math.degrees(2 * math.atan(math.tan(math.radians(fov_h) / 2) / aspecto))


def parametros_pose() -> dict:
    """Altura, inclinación, azimut y objetivo por defecto de `PoseCamara.por_defecto` (leídos, no copiados)."""
    firma = inspect.signature(PoseCamara.por_defecto)
    return {k: v.default for k, v in firma.parameters.items() if v.default is not inspect.Parameter.empty}


def camara_por_defecto(fov_h: float) -> Camara:
    """La webcam de seguimiento en la pose común del software, con un campo de visión horizontal `fov_h`."""
    pose = PoseCamara.por_defecto()
    R = np.asarray(pose.R, dtype=float)  # filas: X derecha, Y abajo, Z delante de la cámara, en la mesa
    return Camara(np.asarray(pose.centro, dtype=float), R[2], R[0], -R[1], fov_h, fov_vertical(fov_h))


def puntos_a_ver(anclajes) -> list[tuple[float, float, float]]:
    pts = []
    for an in anclajes.values():
        for x, y in huellas(an)["loseta"]:
            pts.append((x, y, c.ALTURA_BASE_ANCLAJES))
            pts.append((x, y, Z_SUPERFICIE + c.ALMA_ALTO))  # el alma de la T, por arriba
    return pts


def fov_necesario(cam: Camara, anclajes) -> float:
    """FOV horizontal mínimo (16:9) para ver todas las losetas y el alma de la T con MARGEN_IMAGEN libre."""
    v = np.array(puntos_a_ver(anclajes)) - cam.pos
    z = v @ cam.adelante
    if np.any(z <= 1e-6):
        return math.inf
    aspecto = RESOLUCION[0] / RESOLUCION[1]
    t = max(np.max(np.abs(v @ cam.derecha) / z), np.max(np.abs(v @ cam.arriba) / z) * aspecto)
    return math.degrees(2 * math.atan(t / (1 - 2 * MARGEN_IMAGEN)))


def ve_todo(cam: Camara, anclajes) -> bool:
    return fov_necesario(cam, anclajes) <= cam.fov_h + 1e-9


def mm_por_pixel(cam: Camara, anclajes) -> tuple[float, float]:
    """Tamaño de un píxel sobre la superficie de las piezas (mejor y peor punto de la zona)."""
    vals = []
    f = RESOLUCION[0] / 2 / math.tan(math.radians(cam.fov_h) / 2)
    for x, y, _ in puntos_a_ver(anclajes):
        z = (np.array([x, y, Z_SUPERFICIE]) - cam.pos) @ cam.adelante
        vals.append(z / f)
    return min(vals), max(vals)


def _segmento_corta_caja(p, q, caja) -> bool:
    """¿El segmento p→q atraviesa la caja alineada (xmin, ymin, zmin, xmax, ymax, zmax)? (método de losas)"""
    p, q = np.asarray(p, float), np.asarray(q, float)
    d = q - p
    t0, t1 = 0.0, 1.0
    for k in range(3):
        lo, hi = caja[k], caja[k + 3]
        if abs(d[k]) < 1e-12:
            if p[k] < lo or p[k] > hi:
                return False
        else:
            a, b = (lo - p[k]) / d[k], (hi - p[k]) / d[k]
            a, b = min(a, b), max(a, b)
            t0, t1 = max(t0, a), min(t1, b)
            if t0 > t1:
                return False
    return t1 > 1e-6 and t0 < 1 - 1e-6


def visibilidad_t(an: c.Anclaje, cam: Camara) -> float:
    """Fracción del cordón de la T (punta a ALTURA_PUNTA, antorcha a 45°) que la cámara ve sin que la tape el alma."""
    caja = (X_PIEZA[0], 0.0, 0.0, X_PIEZA[1], c.ALMA_GROSOR, c.ALMA_ALTO)  # alma, marco de la pieza
    # cámara en el marco de la pieza
    cx, cy = a_pieza(an, cam.pos[0], cam.pos[1])
    cx, cy = cx - PIEZA_EN_ANCLAJE[0], cy - PIEZA_EN_ANCLAJE[1]
    cz = cam.pos[2] - Z_SUPERFICIE
    s = c.ALTURA_PUNTA / math.sqrt(2)
    vistos = 0
    n = c.N_TRAMOS + 1
    for k in range(n):
        punta = (k * c.TAMANO_TRAMO, -s, s)
        if not _segmento_corta_caja(punta, (cx, cy, cz), caja):
            vistos += 1
    return vistos / n


def visibilidad_aruco(an: c.Anclaje, cam: Camara) -> float:
    """Fracción de esquinas de los ArUco (el de la pieza y el del anclaje) que se ven con una T colocada:
    dentro de la imagen y sin que el alma se interponga."""
    caja = (X_PIEZA[0], 0.0, 0.0, X_PIEZA[1], c.ALMA_GROSOR, c.ALMA_ALTO)
    cx, cy = a_pieza(an, cam.pos[0], cam.pos[1])
    cam_pieza = (cx - PIEZA_EN_ANCLAJE[0], cy - PIEZA_EN_ANCLAJE[1], cam.pos[2] - Z_SUPERFICIE)
    esquinas = []  # (punto en el marco de la pieza, punto en la mesa)
    x0, y0, x1, y1 = aruco_pieza_local(con_margen=False)
    for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
        esquinas.append(((x, y, 0.0), (*a_mesa(an, *pieza_a_anclaje(x, y)), Z_SUPERFICIE)))
    x0, y0, x1, y1 = aruco_anclaje_local(con_margen=False)
    for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
        esquinas.append(((x - PIEZA_EN_ANCLAJE[0], y - PIEZA_EN_ANCLAJE[1], -PIEZA_EN_ANCLAJE[2]),
                         (*a_mesa(an, x, y), c.ALTURA_BASE_ANCLAJES)))
    lim = 1 - MARGEN_IMAGEN
    vistas = 0
    for p_pieza, p_mesa in esquinas:
        u, w, z = cam.proyectar(p_mesa)
        if z > 0 and abs(u) <= lim and abs(w) <= lim and not _segmento_corta_caja(p_pieza, cam_pieza, caja):
            vistas += 1
    return vistas / len(esquinas)


# =================================================================================================================
# Lienzo: primitivas en mm (y hacia abajo) con salida PNG, SVG y PDF
# =================================================================================================================
def _ruta_fuente(negrita: bool) -> str | None:
    for r in FUENTES[negrita]:
        try:
            ImageFont.truetype(r, 10)
            return r
        except OSError:
            continue
    return None


_CACHE_FUENTES: dict = {}


def fuente(tam_px: float, negrita: bool = False):
    clave = (round(tam_px), negrita)
    if clave not in _CACHE_FUENTES:
        ruta = _ruta_fuente(negrita)
        _CACHE_FUENTES[clave] = (ImageFont.truetype(ruta, max(1, round(tam_px))) if ruta
                                 else ImageFont.load_default(max(1, round(tam_px))))
    return _CACHE_FUENTES[clave]


def ancho_texto(s: str, tam: float, negrita: bool = False) -> float:
    """Ancho en mm de un texto de `tam` mm (medido con la fuente a 100 px/mm)."""
    return fuente(tam * 100, negrita).getlength(s) / 100


class Lienzo:
    def __init__(self, ancho: float, alto: float):
        self.ancho, self.alto = ancho, alto
        self.ops: list[tuple] = []

    def rect(self, x, y, w, h, relleno=None, trazo=None, grosor=0.25, guiones=None):
        self.ops.append(("rect", (x, y, x + w, y + h), relleno, trazo, grosor, guiones))

    def poligono(self, pts, relleno=None, trazo="#000000", grosor=0.25, guiones=None, cerrado=True):
        self.ops.append(("pol", [tuple(map(float, p)) for p in pts], relleno, trazo, grosor, guiones, cerrado))

    def linea(self, p, q, trazo="#000000", grosor=0.25, guiones=None):
        self.poligono([p, q], None, trazo, grosor, guiones, cerrado=False)

    def circulo(self, centro, r, relleno=None, trazo="#000000", grosor=0.25, guiones=None):
        self.ops.append(("circ", tuple(map(float, centro)), float(r), relleno, trazo, grosor, guiones))

    def texto(self, p, s, tam=3.0, color="#000000", ancla="izq", negrita=False, vertical=False):
        """`p` es la línea base del texto (izquierda, centro o derecha según `ancla`)."""
        self.ops.append(("txt", tuple(map(float, p)), str(s), float(tam), color, ancla, negrita, vertical))

    # --- PNG -----------------------------------------------------------------------------------------------------
    def a_png(self, ruta: Path, ppp: float, gris: bool = False):
        s = ppp / 25.4
        modo = "L" if gris else "RGB"
        blanco = 255 if gris else (255, 255, 255)
        img = Image.new(modo, (round(self.ancho * s), round(self.alto * s)), blanco)
        d = ImageDraw.Draw(img)

        def col(h):
            if h is None:
                return None
            rgb = tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))
            return round(0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]) if gris else rgb

        def px(p):
            return (p[0] * s, p[1] * s)

        for op in self.ops:
            if op[0] == "rect":
                _, (x0, y0, x1, y1), rel, tr, gr, gu = op
                if rel:
                    d.rectangle([round(x0 * s), round(y0 * s), round(x1 * s) - 1, round(y1 * s) - 1], fill=col(rel))
                if tr:
                    _png_trazo(d, [px(p) for p in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))], True, col(tr),
                               max(1, round(gr * s)), gu and [g * s for g in gu])
            elif op[0] == "pol":
                _, pts, rel, tr, gr, gu, cerrado = op
                if rel and len(pts) >= 3:
                    d.polygon([px(p) for p in pts], fill=col(rel))
                if tr:
                    _png_trazo(d, [px(p) for p in pts], cerrado, col(tr), max(1, round(gr * s)),
                               gu and [g * s for g in gu])
            elif op[0] == "circ":
                _, (cx, cy), r, rel, tr, gr, gu = op
                if rel:
                    d.ellipse([(cx - r) * s, (cy - r) * s, (cx + r) * s, (cy + r) * s], fill=col(rel))
                if tr:
                    pts = [px((cx + r * math.cos(t), cy + r * math.sin(t))) for t in np.linspace(0, 2 * math.pi, 73)]
                    _png_trazo(d, pts[:-1], True, col(tr), max(1, round(gr * s)), gu and [g * s for g in gu])
            elif op[0] == "txt":
                _, p, txt, tam, color, ancla, neg, vertical = op
                f = fuente(tam * s, neg)
                if not vertical:
                    d.text(px(p), txt, font=f, fill=col(color), anchor={"izq": "ls", "centro": "ms", "der": "rs"}[ancla])
                else:
                    caja = d.textbbox((0, 0), txt, font=f, anchor="ls")
                    w, h = caja[2] - caja[0] + 4, caja[3] - caja[1] + 4
                    tmp = Image.new("L", (w, h), 0)
                    ImageDraw.Draw(tmp).text((2 - caja[0], 2 - caja[1]), txt, font=f, fill=255, anchor="ls")
                    tmp = tmp.rotate(90, expand=True)
                    x, y = px(p)
                    x0 = round(x - tmp.width + 0.25 * tam * s)
                    y0 = round(y - tmp.height / 2)
                    capa = Image.new(modo, tmp.size, col(color))
                    img.paste(capa, (x0, y0), tmp)
        ruta.parent.mkdir(parents=True, exist_ok=True)
        img.save(ruta, dpi=(ppp, ppp), optimize=True)
        return img

    # --- SVG -----------------------------------------------------------------------------------------------------
    def a_svg(self, ruta: Path):
        def esc(t):
            return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        def estilo(rel, tr, gr, gu):
            e = f'fill="{rel or "none"}"'
            if tr:
                e += f' stroke="{tr}" stroke-width="{gr:.3f}"'
                if gu:
                    e += f' stroke-dasharray="{" ".join(f"{g:.2f}" for g in gu)}"'
            return e

        out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.ancho:.2f}mm" height="{self.alto:.2f}mm" '
               f'viewBox="0 0 {self.ancho:.3f} {self.alto:.3f}">',
               f'<rect x="0" y="0" width="{self.ancho:.3f}" height="{self.alto:.3f}" fill="#ffffff"/>']
        for op in self.ops:
            if op[0] == "rect":
                _, (x0, y0, x1, y1), rel, tr, gr, gu = op
                out.append(f'<rect x="{x0:.3f}" y="{y0:.3f}" width="{x1 - x0:.3f}" height="{y1 - y0:.3f}" '
                           f'{estilo(rel, tr, gr, gu)}/>')
            elif op[0] == "pol":
                _, pts, rel, tr, gr, gu, cerrado = op
                etiqueta = "polygon" if cerrado else "polyline"
                ps = " ".join(f"{x:.3f},{y:.3f}" for x, y in pts)
                out.append(f'<{etiqueta} points="{ps}" {estilo(rel if cerrado else None, tr, gr, gu)}/>')
            elif op[0] == "circ":
                _, (cx, cy), r, rel, tr, gr, gu = op
                out.append(f'<circle cx="{cx:.3f}" cy="{cy:.3f}" r="{r:.3f}" {estilo(rel, tr, gr, gu)}/>')
            elif op[0] == "txt":
                _, (x, y), txt, tam, color, ancla, neg, vertical = op
                a = {"izq": "start", "centro": "middle", "der": "end"}[ancla]
                rot = f' transform="rotate(-90 {x:.3f} {y:.3f})"' if vertical else ""
                peso = ' font-weight="bold"' if neg else ""
                out.append(f'<text x="{x:.3f}" y="{y:.3f}" font-size="{tam:.3f}" fill="{color}" text-anchor="{a}"'
                           f' font-family="Liberation Sans, Arial, Helvetica, sans-serif"{peso}{rot}>{esc(txt)}</text>')
        out.append("</svg>\n")
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text("\n".join(out), encoding="utf-8")


def _png_trazo(d: ImageDraw.ImageDraw, pts, cerrado, color, ancho, guiones):
    if cerrado:
        pts = list(pts) + [pts[0]]
    if not guiones:
        d.line(pts, fill=color, width=ancho, joint="curve")
        return
    patron = list(guiones)
    i, resto, dibuja = 0, patron[0], True
    for p, q in zip(pts, pts[1:]):
        p, q = np.array(p), np.array(q)
        largo = np.linalg.norm(q - p)
        t = 0.0
        while largo > 0 and t < largo:
            paso = min(resto, largo - t)
            if dibuja:
                a, b = p + (q - p) * t / largo, p + (q - p) * (t + paso) / largo
                d.line([tuple(a), tuple(b)], fill=color, width=ancho)
            t += paso
            resto -= paso
            if resto <= 1e-9:
                i = (i + 1) % len(patron)
                resto, dibuja = patron[i], not dibuja


def lienzos_a_pdf(paginas: list[Lienzo], ruta: Path):
    """PDF vectorial mínimo (Helvetica, WinAnsi). Tamaño de página = tamaño del lienzo en mm → imprime al 100 %."""
    k = 72 / 25.4
    objetos: list[bytes] = []

    def nuevo(contenido: bytes) -> int:
        objetos.append(contenido)
        return len(objetos)

    cat = nuevo(b"")  # se rellena al final
    paginas_id = nuevo(b"")
    f1 = nuevo(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
    f2 = nuevo(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>")
    ids_pag = []
    for lz in paginas:
        H = lz.alto

        def P(x, y):
            return f"{x * k:.3f} {(H - y) * k:.3f}"

        def color(h, trazo=False):
            r, g, b = (int(h[i:i + 2], 16) / 255 for i in (1, 3, 5))
            return f"{r:.3f} {g:.3f} {b:.3f} {'RG' if trazo else 'rg'}"

        cs = []
        for op in lz.ops:
            if op[0] in ("rect", "pol", "circ"):
                if op[0] == "rect":
                    _, (x0, y0, x1, y1), rel, tr, gr, gu = op
                    camino = f"{x0 * k:.3f} {(H - y1) * k:.3f} {(x1 - x0) * k:.3f} {(y1 - y0) * k:.3f} re"
                elif op[0] == "pol":
                    _, pts, rel, tr, gr, gu, cerrado = op
                    camino = f"{P(*pts[0])} m " + " ".join(f"{P(*p)} l" for p in pts[1:]) + (" h" if cerrado else "")
                    if not cerrado:
                        rel = None
                else:
                    _, (cx, cy), r, rel, tr, gr, gu = op
                    m = 0.5523 * r
                    camino = (f"{P(cx + r, cy)} m {P(cx + r, cy + m)} {P(cx + m, cy + r)} {P(cx, cy + r)} c "
                              f"{P(cx - m, cy + r)} {P(cx - r, cy + m)} {P(cx - r, cy)} c "
                              f"{P(cx - r, cy - m)} {P(cx - m, cy - r)} {P(cx, cy - r)} c "
                              f"{P(cx + m, cy - r)} {P(cx + r, cy - m)} {P(cx + r, cy)} c h")
                pre = []
                if rel:
                    pre.append(color(rel))
                if tr:
                    pre.append(color(tr, True))
                    pre.append(f"{gr * k:.3f} w")
                    pre.append(f"[{' '.join(f'{g * k:.2f}' for g in gu)}] 0 d" if gu else "[] 0 d")
                pinta = "B" if rel and tr else ("f" if rel else "S")
                cs.append(" ".join(pre + [camino, pinta]))
            elif op[0] == "txt":
                _, (x, y), txt, tam, col_t, ancla, neg, vertical = op
                w = ancho_texto(txt, tam, neg)
                dx = {"izq": 0.0, "centro": -w / 2, "der": -w}[ancla]
                t = txt.encode("cp1252", errors="replace").replace(b"\\", b"\\\\").replace(b"(", b"\\(") \
                    .replace(b")", b"\\)").decode("latin-1")
                fuente_pdf = "/F2" if neg else "/F1"
                if vertical:
                    matriz = f"0 1 -1 0 {x * k:.3f} {(H - y - dx) * k:.3f} Tm"
                else:
                    matriz = f"1 0 0 1 {(x + dx) * k:.3f} {(H - y) * k:.3f} Tm"
                cs.append(f"BT {color(col_t)} {fuente_pdf} {tam * k:.3f} Tf {matriz} ({t}) Tj ET")
        datos = zlib.compress("\n".join(cs).encode("latin-1"), 9)
        flujo = nuevo(b"<< /Length %d /Filter /FlateDecode >>\nstream\n" % len(datos) + datos + b"\nendstream")
        pag = nuevo((f"<< /Type /Page /Parent {paginas_id} 0 R /MediaBox [0 0 {lz.ancho * k:.3f} {lz.alto * k:.3f}] "
                     f"/Resources << /Font << /F1 {f1} 0 R /F2 {f2} 0 R >> >> /Contents {flujo} 0 R >>").encode())
        ids_pag.append(pag)
    objetos[cat - 1] = (f"<< /Type /Catalog /Pages {paginas_id} 0 R "
                        f"/ViewerPreferences << /PrintScaling /None >> >>").encode()
    objetos[paginas_id - 1] = (f"<< /Type /Pages /Kids [{' '.join(f'{i} 0 R' for i in ids_pag)}] "
                               f"/Count {len(ids_pag)} >>").encode()
    salida = bytearray(b"%PDF-1.6\n%\xe2\xe3\xcf\xd3\n")
    offsets = []
    for i, obj in enumerate(objetos, 1):
        offsets.append(len(salida))
        salida += f"{i} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref = len(salida)
    salida += f"xref\n0 {len(objetos) + 1}\n0000000000 65535 f \n".encode()
    for o in offsets:
        salida += f"{o:010d} 00000 n \n".encode()
    salida += f"trailer\n<< /Size {len(objetos) + 1} /Root {cat} 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_bytes(bytes(salida))


# =================================================================================================================
# Vista: coordenadas del mundo (mm, y hacia arriba) → lienzo, y cotas
# =================================================================================================================
class Vista:
    """Dibuja en un lienzo con coordenadas del mundo. `giro_pagina` = 90 pone el +X del mundo hacia arriba."""

    def __init__(self, lz: Lienzo, escala: float, origen: tuple[float, float], giro_pagina: int = 0):
        self.lz, self.e, self.o, self.g = lz, escala, origen, giro_pagina

    def p(self, x, y):
        if self.g == 90:  # mundo X → arriba de la página, mundo Y → izquierda
            x, y = -y, x
        return (self.o[0] + x * self.e, self.o[1] - y * self.e)

    def rect(self, r, **kw):
        x0, y0, x1, y1 = r
        self.pol([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], **kw)

    def pol(self, pts, **kw):
        self.lz.poligono([self.p(*q) for q in pts], **kw)

    def linea(self, a, b, **kw):
        self.lz.linea(self.p(*a), self.p(*b), **kw)

    def circulo(self, centro, r, **kw):
        self.lz.circulo(self.p(*centro), r * self.e, **kw)

    def texto(self, pt, s, **kw):
        self.lz.texto(self.p(*pt), s, **kw)

    def flecha(self, a, b, color="#000000", grosor=0.3, punta=2.0):
        pa, pb = np.array(self.p(*a)), np.array(self.p(*b))
        self.lz.linea(tuple(pa), tuple(pb), trazo=color, grosor=grosor)
        _punta(self.lz, pa, pb, color, punta)

    def cota(self, a, b, desplazamiento, texto=None, tam=2.6, color=AZUL):
        """Cota entre a y b (mundo), desplazada `desplazamiento` mm de papel hacia la izquierda de a→b."""
        pa, pb = np.array(self.p(*a)), np.array(self.p(*b))
        d = pb - pa
        largo = np.linalg.norm(d)
        if largo < 1e-6:
            return
        u = d / largo
        n = np.array([u[1], -u[0]])  # izquierda de a→b en la página (y hacia abajo)
        qa, qb = pa + n * desplazamiento, pb + n * desplazamiento
        s = np.sign(desplazamiento) or 1
        for p0, q0 in ((pa, qa), (pb, qb)):
            self.lz.linea(tuple(p0 + n * s * 0.8), tuple(q0 + n * s * 1.2), trazo=color, grosor=0.15)
        self.lz.linea(tuple(qa), tuple(qb), trazo=color, grosor=0.2)
        _punta(self.lz, qb, qa, color, 1.6)
        _punta(self.lz, qa, qb, color, 1.6)
        if texto is None:
            texto = fmt(math.dist(a, b))
        medio = (qa + qb) / 2
        vertical = abs(u[0]) < 0.3
        lado = n * s * (tam * 0.35)
        if vertical:
            self.lz.texto(tuple(medio + lado + np.array([-0.2 * tam if s > 0 else tam, 0])), texto, tam=tam,
                          color=color, ancla="centro", vertical=True)
        else:
            self.lz.texto(tuple(medio + n * s * 0.8 + (np.array([0, -0.3]) if n[1] * s < 0 else np.array([0, tam]))),
                          texto, tam=tam, color=color, ancla="centro")


def _punta(lz: Lienzo, desde, hasta, color, tam):
    desde, hasta = np.asarray(desde, float), np.asarray(hasta, float)
    d = hasta - desde
    if np.linalg.norm(d) < 1e-9:
        return
    u = d / np.linalg.norm(d)
    n = np.array([-u[1], u[0]])
    base = hasta - u * tam
    lz.poligono([tuple(hasta), tuple(base + n * tam * 0.35), tuple(base - n * tam * 0.35)], relleno=color,
                trazo=None)


def cuadro_titulo(lz: Lienzo, titulo: str, lineas: list[str]):
    lz.texto((8, 10), titulo, tam=5.0, negrita=True)
    for i, t in enumerate(lineas):
        lz.texto((8, 16 + i * 4.2), t, tam=3.0, color="#333333")


# =================================================================================================================
# ArUco
# =================================================================================================================
def diccionario():
    return cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, c.DICCIONARIO_ARUCO))


def bits_aruco(id_aruco: int) -> np.ndarray:
    """Matriz 6x6 (True = negro) con el borde incluido. Fila 0 = arriba del marcador (Y+ del marcador)."""
    img = cv2.aruco.generateImageMarker(diccionario(), id_aruco, 6, borderBits=1)
    return img < 128


def dibujar_aruco_pagina(lz: Lienzo, id_aruco: int, x: float, y: float, lado: float):
    """Marcador con su esquina superior izquierda (sin margen) en (x, y) de la página. Módulos con borde exacto."""
    bits = bits_aruco(id_aruco)
    m = lado / 6
    for f in range(6):
        for col in range(6):
            if bits[f, col]:
                lz.rect(x + col * m, y + f * m, m, m, relleno="#000000")


def dibujar_aruco_mundo(v: Vista, id_aruco: int, centro, lado: float, ejes: tuple = ((1, 0), (0, 1)),
                        margen: bool = True):
    """Marcador en una vista: columnas a lo largo de `ejes[0]` (X del marcador), filas de +Y a −Y del marcador."""
    ex, ey = np.array(ejes[0], float), np.array(ejes[1], float)
    bits = bits_aruco(id_aruco)
    m = lado / 6
    c0 = np.array(centro, float)
    if margen:
        lb = lado_con_margen(lado) / 2
        esquinas = [c0 + sx * lb * ex + sy * lb * ey for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        v.pol([tuple(p) for p in esquinas], relleno="#ffffff", trazo=GRIS, grosor=0.15, guiones=(1.0, 0.7))
    for f in range(6):
        for col in range(6):
            if bits[f, col]:
                x0, x1 = -lado / 2 + col * m, -lado / 2 + (col + 1) * m
                y1, y0 = lado / 2 - f * m, lado / 2 - (f + 1) * m
                pts = [c0 + a * ex + b * ey for a, b in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))]
                v.pol([tuple(p) for p in pts], relleno="#000000", trazo=None)


def regla(lz: Lienzo, x: float, y: float, largo: float = 50.0):
    """Regla de comprobación de escala: marcas cada mm, más largas cada 5 y 10."""
    lz.rect(x, y, largo, 0.25, relleno="#000000")
    for i in range(int(largo) + 1):
        h = 4.0 if i % 10 == 0 else (2.8 if i % 5 == 0 else 1.6)
        lz.rect(x + i - 0.1, y, 0.2, h, relleno="#000000")
        if i % 10 == 0:
            lz.texto((x + i, y + 7.0), str(i), tam=2.6, ancla="centro")
    lz.texto((x + largo + 3, y + 3.5), f"{fmt(largo)} mm: mídela antes de recortar", tam=2.6)


def etiqueta_id(id_aruco: int) -> str:
    tipo = c.tipo_por_id(id_aruco)
    if tipo is not None:
        return f"id {id_aruco} · {'recta' if tipo is c.TipoPieza.RECTA else 'T'}"
    return f"id {id_aruco} · anclaje {c.IDS_ANCLAJE[id_aruco]}"


def nombre_png(id_aruco: int) -> str:
    tipo = c.tipo_por_id(id_aruco)
    if tipo is not None:
        return f"aruco_{id_aruco:02d}_{tipo.value}.png"
    return f"aruco_{id_aruco:02d}_anclaje_{c.IDS_ANCLAJE[id_aruco]}.png"


A4 = (210.0, 297.0)


def hoja_marcadores(ids: list[int], titulo: str, lado: float) -> Lienzo:
    lz = Lienzo(*A4)
    lz.texto((12, 14), titulo, tam=4.6, negrita=True)
    lz.texto((12, 20), f"{c.DICCIONARIO_ARUCO} · lado {fmt(lado)} mm (solo la parte negra) · margen blanco "
                       f"{fmt(MARGEN_BLANCO)} mm (módulo {fmt(modulo_aruco(lado))} mm) incluido en el recorte",
             tam=2.7)
    lz.texto((12, 24.5), "Imprimir a escala 100 % ('tamaño real', sin 'ajustar a la página'), en papel adhesivo "
                         "mate. Recorta por la línea gris.", tam=2.7)
    lz.texto((12, 29), "Al pegarlo: +X → en el sentido de avance del cordón; el lado de arriba del marcador "
                       "(donde está el texto) hacia +Y de la pieza.", tam=2.7)
    regla(lz, 12, 33)
    lb = lado_con_margen(lado)
    m = MARGEN_BLANCO
    cols, celda_w, celda_h = 4, 46.0, 47.0
    x_ini = (A4[0] - cols * celda_w) / 2 + (celda_w - lb) / 2
    y_ini = 50.0
    for i, id_aruco in enumerate(ids):
        f, col = divmod(i, cols)
        x = x_ini + col * celda_w
        y = y_ini + f * celda_h
        lz.texto((x, y + 3.2), etiqueta_id(id_aruco), tam=3.0, negrita=True)
        lz.texto((x + lb, y + 3.2), "+X →", tam=3.0, ancla="der", color=ROJO)
        yc = y + 5.0
        lz.rect(x, yc, lb, lb, trazo="#9e9e9e", grosor=0.15, guiones=(1.2, 0.8))
        dibujar_aruco_pagina(lz, id_aruco, x + m, yc + m, lado)
    return lz


def hoja_tablero() -> tuple[Lienzo, tuple[float, float]]:
    """Tablero de ajedrez 10x7 cuadros de 25 mm (9x6 esquinas interiores) en A4 apaisado."""
    lz = Lienzo(A4[1], A4[0])
    cols, filas, lado = 10, 7, 25.0
    x0 = (lz.ancho - cols * lado) / 2
    y0 = 25.0
    lz.texto((x0, 10), "LeWelder · tablero de calibración de cámara", tam=4.6, negrita=True)
    lz.texto((x0, 16), "9x6 esquinas interiores · cuadro de 25 mm · imprimir al 100 % y pegar sobre un cartón "
                       "rígido y plano", tam=2.7)
    regla(lz, x0 + 170, 8)
    for f in range(filas):
        for col in range(cols):
            if (f + col) % 2 == 0:
                lz.rect(x0 + col * lado, y0 + f * lado, lado, lado, relleno="#000000")
    lz.rect(x0, y0, cols * lado, filas * lado, trazo="#000000", grosor=0.1)
    return lz, (x0, y0)


# =================================================================================================================
# Verificación (OpenCV)
# =================================================================================================================
def detectar_aruco(img_gris: np.ndarray, ppp: float) -> dict[int, float]:
    """Detecta marcadores y devuelve {id: lado medio en mm}. Reduce a ~150 ppp para detectar y escala de vuelta."""
    factor = max(1, int(round(ppp / 150)))
    peq = cv2.resize(img_gris, (img_gris.shape[1] // factor, img_gris.shape[0] // factor),
                     interpolation=cv2.INTER_AREA) if factor > 1 else img_gris
    params = cv2.aruco.DetectorParameters()
    params.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX
    det = cv2.aruco.ArucoDetector(diccionario(), params)
    esquinas, ids, _ = det.detectMarkers(peq)
    res: dict[int, float] = {}
    if ids is None:
        return res
    for esq, i in zip(esquinas, ids.ravel()):
        e = esq.reshape(4, 2) * (img_gris.shape[1] / peq.shape[1])
        lados = [np.linalg.norm(e[k] - e[(k + 1) % 4]) for k in range(4)]
        res[int(i)] = float(np.mean(lados)) / ppp * 25.4
    return res


def leer_gris(ruta: Path) -> tuple[np.ndarray, float]:
    im = Image.open(ruta)
    ppp = float(im.info.get("dpi", (PPP, PPP))[0])
    return np.array(im.convert("L")), ppp


def rasterizar_pdf(ruta: Path, ppp: int = PPP) -> list[np.ndarray] | None:
    """Rasteriza un PDF con pdftoppm (poppler). None si no está instalado."""
    if shutil.which("pdftoppm") is None:
        return None
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(["pdftoppm", "-r", str(ppp), "-gray", "-png", str(ruta), str(Path(tmp) / "p")], check=True,
                       capture_output=True)
        return [np.array(Image.open(p).convert("L")) for p in sorted(Path(tmp).glob("p*.png"))]


def medir_tablero(img_gris: np.ndarray, ppp: float) -> float | None:
    """Detecta el tablero 9x6 y devuelve el lado medio del cuadro en mm (None si no lo encuentra)."""
    factor = max(1, int(round(ppp / 100)))
    peq = cv2.resize(img_gris, (img_gris.shape[1] // factor, img_gris.shape[0] // factor),
                     interpolation=cv2.INTER_AREA)
    ok, esq = cv2.findChessboardCorners(peq, (9, 6))
    if not ok:
        return None
    esq = cv2.cornerSubPix(peq, esq, (5, 5), (-1, -1),
                           (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 50, 0.01))
    e = esq.reshape(6, 9, 2) * factor
    d = np.concatenate([np.linalg.norm(np.diff(e, axis=1), axis=2).ravel(),
                        np.linalg.norm(np.diff(e, axis=0), axis=2).ravel()])
    return float(np.mean(d)) / ppp * 25.4


# =================================================================================================================
# Planos
# =================================================================================================================
def _ids_ejemplo(tipo: c.TipoPieza) -> int:
    return list(c.IDS_PIEZA[tipo])[0]


def plano_pieza_superior(tipo: c.TipoPieza) -> Lienzo:
    lz = Lienzo(250, 170)
    v = Vista(lz, 1.2, (40, 100))
    recta = c.TipoPieza(tipo) is c.TipoPieza.RECTA
    hx0, hy0, hx1, hy1 = huella_pieza_local()
    yb = ancho_base(tipo) / 2
    ch = CHAFLAN_LLAVE
    contorno = [(hx0, -yb), (hx1, -yb), (hx1, yb - ch), (hx1 - ch, yb), (hx0, yb)]
    v.pol(contorno, relleno="#f5f5f5", trazo="#000000", grosor=0.35)
    if recta:
        j = c.HOLGURA_JUNTA / 2
        v.rect((hx0, -j, hx1, j), relleno="#bdbdbd", trazo="#000000", grosor=0.2)
    else:
        v.rect((hx0, 0, hx1, c.ALMA_GROSOR), relleno="#bdbdbd", trazo="#000000", grosor=0.3)
        v.texto((c.LONGITUD_CORDON + 2, c.ALMA_GROSOR / 2 - 1.0), "alma", tam=2.4)
        if yb < ANCHO_HUELLA / 2:
            v.rect((hx0, -ANCHO_HUELLA / 2, hx1, ANCHO_HUELLA / 2), trazo=NARANJA, grosor=0.2, guiones=(1.5, 1))
    for x, y in imanes_local():
        v.circulo((x, y), c.IMAN_DIAMETRO / 2, trazo=GRIS, grosor=0.2, guiones=(1, 0.6))
    dibujar_aruco_mundo(v, _ids_ejemplo(tipo), c.ARUCO_EN_PIEZA[:2], c.LADO_ARUCO_PIEZA)
    v.flecha((0, 0), (c.LONGITUD_CORDON, 0), color=ROJO, grosor=0.6, punta=3)
    v.circulo((0, 0), 1.2, relleno=ROJO, trazo=None)
    v.flecha((0, 0), (0, 22), color=VERDE, grosor=0.4)
    v.texto((2, 18), "+Y", tam=2.6, color=VERDE)
    v.texto((c.LONGITUD_CORDON / 2, 2.2 if recta else -3.5), "cordón (X de la pieza, sentido de avance)",
            tam=2.6, color=ROJO, ancla="centro")
    v.texto((-2, -4), "origen (0, 0, 0)", tam=2.4, color=ROJO, ancla="der")
    # cotas
    v.cota((hx0, yb), (hx1, yb), -14, f"{fmt(c.CHAPA_LARGO)}")
    v.cota((0, yb), (c.LONGITUD_CORDON, yb), -7, f"cordón {fmt(c.LONGITUD_CORDON)}")
    v.cota((hx0, -yb), (0, -yb), 7, fmt(c.MARGEN_X))
    v.cota((hx0, -yb), (hx0, yb), 10, fmt(2 * yb))
    if recta:
        v.cota((hx1, c.HOLGURA_JUNTA / 2), (hx1, yb - ch), -4, fmt(c.CHAPA_ANCHO - ch))
        v.texto((hx1 + 3, -1), f"junta {fmt(c.HOLGURA_JUNTA)} × {fmt(PROFUNDIDAD_JUNTA)} prof.", tam=2.4)
    ax, ay = c.ARUCO_EN_PIEZA[:2]
    lb = lado_con_margen(c.LADO_ARUCO_PIEZA)
    v.cota((0, -yb), (ax, -yb), 14, f"ArUco X = {fmt(ax)}")
    v.cota((ax - c.LADO_ARUCO_PIEZA / 2, ay - c.LADO_ARUCO_PIEZA / 2),
           (ax + c.LADO_ARUCO_PIEZA / 2, ay - c.LADO_ARUCO_PIEZA / 2), 5, fmt(c.LADO_ARUCO_PIEZA))
    v.cota((ax + lb / 2, 0), (ax + lb / 2, ay), 8, f"Y = {fmt(ay)}")
    xi, yi = imanes_local()[0]
    v.cota((xi, -yb), (xi, yi), -6, fmt(abs(yi)))
    v.texto((xi, yi - c.IMAN_DIAMETRO / 2 - 2.5), f"imán Ø{fmt(c.IMAN_DIAMETRO)} (abajo)", tam=2.2, color=GRIS,
            ancla="centro")
    v.cota((hx1 - ch, yb), (hx1, yb - ch), -3, f"chaflán {fmt(ch)}×45°")
    nombre = "unión a tope recta" if recta else "unión en T"
    lineas = [f"Vista superior en el marco de la pieza (mm). Z = 0 en la cara superior de la chapa"
              f"{'s' if recta else ' base'}; grosor {fmt(c.CHAPA_GROSOR)}.",
              f"ArUco id {_ids_ejemplo(tipo)} dibujado tal cual se pega (lado {fmt(c.LADO_ARUCO_PIEZA)} + margen "
              f"blanco hasta {fmt(lb)}). Imanes: X = {', '.join(fmt(x) for x in sorted({p[0] for p in imanes_local()}))}"
              f", Y = ±{fmt(abs(yi))}, cara inferior."]
    if not recta and yb < ANCHO_HUELLA / 2:
        lineas.append(f"Naranja: huella común de {fmt(ANCHO_HUELLA)} mm (propuesta para que la T no baile "
                      f"{fmt((ANCHO_HUELLA - 2 * yb) / 2)} mm por lado en la loseta).")
    cuadro_titulo(lz, f"Pieza {nombre}", lineas)
    return lz


def plano_pieza_seccion(tipo: c.TipoPieza) -> Lienzo:
    recta = c.TipoPieza(tipo) is c.TipoPieza.RECTA
    lz = Lienzo(220, 150 if recta else 175)
    v = Vista(lz, 1.6, (110, 95 if recta else 125))
    yb = ancho_base(tipo) / 2
    g = c.CHAPA_GROSOR
    zi = c.IMAN_ALTO + HOLGURA_IMAN_FONDO
    v.rect((-ANCHO_HUELLA / 2 - 6, -g - 1.5, ANCHO_HUELLA / 2 + 6, -g), relleno="#d7ccc8", trazo=None)
    v.texto((ANCHO_HUELLA / 2 + 7, -g - 1.2), "loseta (Z mesa = " + fmt(c.ALTURA_BASE_ANCLAJES) + ")", tam=2.4)
    if recta:
        j = c.HOLGURA_JUNTA / 2
        pts = [(-yb, -g), (yb, -g), (yb, 0), (j, 0), (j, -PROFUNDIDAD_JUNTA), (-j, -PROFUNDIDAD_JUNTA), (-j, 0),
               (-yb, 0)]
        v.pol(pts, relleno="#eeeeee", trazo="#000000", grosor=0.35)
        v.cota((-j, 0), (j, 0), 10, fmt(c.HOLGURA_JUNTA))
        v.cota((j, 0), (j, -PROFUNDIDAD_JUNTA), -12, fmt(PROFUNDIDAD_JUNTA))
    else:
        pts = [(-yb, -g), (yb, -g), (yb, 0), (c.ALMA_GROSOR, 0), (c.ALMA_GROSOR, c.ALMA_ALTO), (0, c.ALMA_ALTO),
               (0, 0), (-yb, 0)]
        v.pol(pts, relleno="#eeeeee", trazo="#000000", grosor=0.35)
        v.cota((c.ALMA_GROSOR, 0), (c.ALMA_GROSOR, c.ALMA_ALTO), -8, fmt(c.ALMA_ALTO))
        v.cota((0, c.ALMA_ALTO), (c.ALMA_GROSOR, c.ALMA_ALTO), 6, fmt(c.ALMA_GROSOR))
        # antorcha a 45° desde −Y
        s = c.ALTURA_PUNTA / math.sqrt(2)
        punta = (-s, s)
        lejos = (-s - 45, s + 45)
        v.linea(lejos, punta, trazo=ROJO, grosor=0.8)
        v.circulo(punta, 0.9, relleno=VERDE, trazo=None)
        v.texto((-s - 44, s + 47), "antorcha a 45° (ángulo de trabajo)", tam=2.4, color=ROJO)
        v.texto((-s - 2, s + 3.5), f"punta a {fmt(c.ALTURA_PUNTA)} mm", tam=2.2, color=VERDE, ancla="der")
    for y in (-abs(imanes_local()[0][1]), abs(imanes_local()[0][1])):
        r = c.AGUJEROS_IMAN_PRUEBA[1] / 2
        v.rect((y - r, -g, y + r, -g + zi), relleno="#ffffff", trazo=GRIS, grosor=0.25, guiones=(1, 0.6))
    yi = abs(imanes_local()[0][1])
    v.cota((yi + c.AGUJEROS_IMAN_PRUEBA[1] / 2, -g), (yi + c.AGUJEROS_IMAN_PRUEBA[1] / 2, -g + zi), -6, fmt(zi))
    # ArUco (pegatina) sobre Y < 0
    ay = c.ARUCO_EN_PIEZA[1]
    lb = lado_con_margen(c.LADO_ARUCO_PIEZA)
    v.rect((ay - lb / 2, 0, ay + lb / 2, 0.6), relleno="#000000", trazo=None)
    v.texto((ay, 3), "ArUco (pegatina)", tam=2.4, ancla="centro")
    v.cota((-yb, -g), (-yb, 0), 8, fmt(g))
    v.cota((-yb, -g), (yb, -g), -10, fmt(2 * yb))
    v.circulo((0, 0), 1.0, relleno=ROJO, trazo=None)
    v.texto((1.5, -2.5) if recta else (-1.5, -2.5), "cordón (Y = 0, Z = 0)", tam=2.4, color=ROJO,
            ancla="izq" if recta else "der")
    if recta:
        v.circulo((0, c.ALTURA_PUNTA), 0.9, relleno=VERDE, trazo=None)
        v.linea((0, c.ALTURA_PUNTA), (0, 40), trazo=ROJO, grosor=0.8)
        v.texto((1.5, 30), "antorcha vertical (90°)", tam=2.4, color=ROJO)
        v.texto((1.5, c.ALTURA_PUNTA + 1.5), f"punta a {fmt(c.ALTURA_PUNTA)} mm", tam=2.2, color=VERDE)
    nombre = "unión a tope recta" if recta else "unión en T"
    cuadro_titulo(lz, f"Sección YZ de la {nombre} (X = cualquiera)",
                  ["Vista desde el final del cordón (mirando hacia −X): +Y a la derecha, Z arriba. Z = 0 en la "
                   "cara de apoyo de la punta.",
                   f"Agujeros de imán dibujados con Ø{fmt(c.AGUJEROS_IMAN_PRUEBA[1])} (elige con la pieza de "
                   f"prueba) y {fmt(zi)} de profundidad desde abajo, en X = "
                   f"{', '.join(fmt(x) for x in sorted({p[0] for p in imanes_local()}))}."])
    return lz


def plano_loseta() -> Lienzo:
    lz = Lienzo(250, 200)
    v = Vista(lz, 1.15, (42, 88))
    lx0, ly0, lx1, ly1 = loseta_local()
    v.rect((lx0, ly0, lx1, ly1), relleno="#efebe9", trazo="#000000", grosor=0.4)
    hx0, hy0, hx1, hy1 = huella_en_anclaje()
    ch = CHAFLAN_LLAVE
    v.pol([(hx0, hy0), (hx1, hy0), (hx1, hy1 - ch), (hx1 - ch, hy1), (hx0, hy1)], trazo=GRIS, grosor=0.25,
          guiones=(2, 1))
    for pol in topes_local():
        v.pol(pol, relleno="#8d6e63", trazo="#3e2723", grosor=0.2)
    for x, y in imanes_local():
        v.circulo(pieza_a_anclaje(x, y), c.IMAN_DIAMETRO / 2, trazo="#000000", grosor=0.25)
    for x, y in tornillos_loseta():
        v.circulo((x, y), TORNILLO_LOSETA / 2, trazo="#000000", grosor=0.25)
        v.circulo((x, y), 4.0, trazo=GRIS, grosor=0.15, guiones=(0.8, 0.5))
    dibujar_aruco_mundo(v, 0, c.ARUCO_EN_ANCLAJE[:2], c.LADO_ARUCO_ANCLAJE)
    v.texto((95, tornillos_loseta()[0][1] - LETRA_ALTO / 2), "A", tam=LETRA_ALTO * v.e, negrita=True,
            color="#6d4c41", ancla="centro")
    v.flecha((0, 0), (c.LONGITUD_CORDON, 0), color=ROJO, grosor=0.5, punta=3)
    v.circulo((0, 0), 1.2, relleno=ROJO, trazo=None)
    v.texto((c.LONGITUD_CORDON / 2, 2.5), "cordón de la pieza colocada", tam=2.4, color=ROJO, ancla="centro")
    v.flecha((0, 0), (0, 22), color=VERDE, grosor=0.4)
    v.texto((2, 18), "+Y", tam=2.6, color=VERDE)
    v.cota((lx0, ly1), (lx1, ly1), -8, fmt(lx1 - lx0))
    v.cota((lx0, ly0), (lx0, ly1), 9, fmt(ly1 - ly0))
    v.cota((lx0, ly1), (0, ly1), -15, fmt(-lx0))
    v.cota((hx0 - HOLGURA_ENCAJE, hy1 + HOLGURA_ENCAJE + TOPE_GROSOR), (hx1 + HOLGURA_ENCAJE,
           hy1 + HOLGURA_ENCAJE + TOPE_GROSOR), -2, f"hueco {fmt(hx1 - hx0 + 2 * HOLGURA_ENCAJE)}")
    v.cota((hx1 + HOLGURA_ENCAJE + TOPE_GROSOR, hy0 - HOLGURA_ENCAJE),
           (hx1 + HOLGURA_ENCAJE + TOPE_GROSOR, hy1 + HOLGURA_ENCAJE), 4,
           f"hueco {fmt(hy1 - hy0 + 2 * HOLGURA_ENCAJE)}")
    ax, ay = c.ARUCO_EN_ANCLAJE[:2]
    v.cota((ax + lado_con_margen(c.LADO_ARUCO_ANCLAJE) / 2, 0), (ax + lado_con_margen(c.LADO_ARUCO_ANCLAJE) / 2, ay),
           -6, f"Y = {fmt(ay)}")
    v.cota((0, ly0), (ax, ly0), 6, f"X = {fmt(ax)}")
    tx, ty = tornillos_loseta()[1]
    v.cota((tx, ty), (tx, ly0), 4, fmt(ty - ly0))
    lineas = [f"Una loseta por anclaje, grosor {fmt(c.ALTURA_BASE_ANCLAJES)} mm. Marco del anclaje = marco de la "
              f"pieza colocada (origen al inicio del cordón).",
              f"Topes en L de {fmt(TOPE_ALTO)} mm de alto y {fmt(TOPE_GROSOR)} de grueso a {fmt(HOLGURA_ENCAJE)} mm "
              f"de la pieza; bloque llave de {fmt(bloque_llave())} mm en la esquina del chaflán.",
              f"Imanes Ø{fmt(c.IMAN_DIAMETRO)} con la cara a {fmt(HOLGURA_IMAN_FONDO)} mm bajo la superficie; "
              f"tornillos Ø{fmt(TORNILLO_LOSETA)} pasantes; ArUco del anclaje (id 0 = A, 1 = B, 2 = C, 3 = D)."]
    cuadro_titulo(lz, "Loseta de anclaje (vista superior)", lineas)
    return lz


def plano_base(anclajes: dict[str, c.Anclaje], titulo: str, problemas: list[Problema]) -> Lienzo:
    x0, y0, x1, y1 = zona_trabajo(anclajes)
    x0, x1 = min(x0, BASE_ROBOT_X[0]) - 20, max(x1, 0) + 20
    y0, y1 = min(y0, BASE_ROBOT_Y[0]) - 20, max(y1, BASE_ROBOT_Y[1]) + 20
    ancho_mm = 260.0
    e = min(ancho_mm / (y1 - y0), 230.0 / (x1 - x0))
    lz = Lienzo(ancho_mm + 30, (x1 - x0) * e + 55)
    # mundo X → arriba, Y → izquierda; origen de página tal que y1 quede a la izquierda
    v = Vista(lz, e, (15 + y1 * e, 45 + x1 * e), giro_pagina=90)
    v.rect((BASE_ROBOT_X[0], BASE_ROBOT_Y[0], BASE_ROBOT_X[1], BASE_ROBOT_Y[1]), relleno="#cfd8dc", trazo="#37474f",
           grosor=0.3)
    v.circulo((EJE_HOMBRO_X, 0), 3, trazo="#37474f", grosor=0.3)
    v.texto((BASE_ROBOT_X[0] + 8, 0), "base SO-101", tam=2.6, ancla="centro")
    v.flecha((0, 0), (60, 0), color=ROJO, grosor=0.4)
    v.flecha((0, 0), (0, 60), color=VERDE, grosor=0.4)
    v.texto((62, -4), "+X mesa", tam=2.4, color=ROJO)
    v.texto((4, 62), "+Y mesa", tam=2.4, color=VERDE)
    v.circulo((0, 0), 1.5, relleno="#000000", trazo=None)
    hay_solape = {(p.a, p.b) for p in problemas if p.tipo in ("pieza", "loseta")}
    for n, an in sorted(anclajes.items()):
        h = huellas(an)
        v.pol(h["loseta"], relleno="#efebe9", trazo="#5d4037", grosor=0.3)
        v.pol(h["pieza"], relleno="#e3f2fd", trazo=AZUL, grosor=0.3)
    # solapes debajo de marcadores y etiquetas para que estas se sigan leyendo
    nombres = sorted(anclajes)
    for i, a in enumerate(nombres):
        for b in nombres[i + 1:]:
            if (a, b) not in hay_solape:
                continue
            ha, hb = huellas(anclajes[a]), huellas(anclajes[b])
            pol = interseccion(ha["loseta"], hb["loseta"])
            if len(pol) >= 3:
                v.pol(pol, relleno="#ffcdd2", trazo=ROJO, grosor=0.3, guiones=(1.5, 1))
            for p in (ha["pieza"], ha["aruco"]):
                for q in (hb["pieza"], hb["aruco"]):
                    pol = interseccion(p, q)
                    if len(pol) >= 3:
                        v.pol(pol, relleno="#e57373", trazo=ROJO, grosor=0.5)
    for n, an in sorted(anclajes.items()):
        ex, ey = ejes_anclaje(an)
        id_a = [k for k, nom in c.IDS_ANCLAJE.items() if nom == n][0]
        ax, ay = a_mesa(an, *c.ARUCO_EN_ANCLAJE[:2])
        dibujar_aruco_mundo(v, id_a, (ax, ay), c.LADO_ARUCO_ANCLAJE, ejes=(tuple(ex), tuple(ey)))
        p0, p1 = cordon_en_mesa(an)
        v.flecha(p0, p1, color=ROJO, grosor=0.5, punta=2.5)
        v.circulo(p0, 1.3, relleno=ROJO, trazo=None)
        cx, cy = a_mesa(an, c.LONGITUD_CORDON / 2, -ANCHO_HUELLA / 4)
        v.texto((cx, cy), n, tam=7, negrita=True, ancla="centro", color="#5d4037")
        v.texto((cx - 9 / e, cy), f"({fmt(an.x, 1)}, {fmt(an.y, 1)}, {fmt(an.giro, 1)}°)", tam=2.4, ancla="centro")
    estado = "SIN SOLAPES" if not problemas else f"{len(problemas)} PROBLEMA(S): rojo = solape"
    cuadro_titulo(lz, titulo, [f"Marco de la mesa (mm), visto desde arriba con el robot abajo. Azul: pieza; "
                               f"marrón: loseta; flecha roja: cordón. {estado}.",
                               "Etiqueta: (x, y, giro) del anclaje = inicio del cordón en la mesa."])
    return lz


def plano_prueba_imanes() -> Lienzo:
    lz = Lienzo(200, 120)
    v = Vista(lz, 2.0, (25, 85))
    n = len(c.AGUJEROS_IMAN_PRUEBA)
    paso = 18.0
    largo = paso * n + 6
    v.rect((0, 0, largo, 22), relleno="#eeeeee", trazo="#000000", grosor=0.35)
    for i, d in enumerate(c.AGUJEROS_IMAN_PRUEBA):
        x = 12 + i * paso
        v.circulo((x, 13), d / 2, relleno="#ffffff", trazo="#000000", grosor=0.25)
        v.texto((x, 2.5), fmt(d, 1), tam=3.2, ancla="centro")
    v.cota((0, 0), (largo, 0), 8, fmt(largo))
    v.cota((0, 0), (0, 22), 8, "22")
    v.texto((0, -16), f"Placa de {fmt(largo)} × 22 × {fmt(c.CHAPA_GROSOR)} mm. Agujeros ciegos de "
                      f"{fmt(c.IMAN_ALTO + HOLGURA_IMAN_FONDO)} mm de profundidad (imán de {fmt(c.IMAN_DIAMETRO)}×"
                      f"{fmt(c.IMAN_ALTO)}).", tam=2.8)
    v.texto((0, -20.5), "Números grabados 0,4 mm. Imprímela con la cara de los agujeros arriba y la misma "
                        "configuración que las piezas.", tam=2.8)
    # prueba de encaje de los topes
    v2 = Vista(lz, 2.0, (25 + (largo + 10) * 2.0, 85))
    for i, hol in enumerate((0.2, 0.3, 0.4)):
        x = i * 14
        v2.rect((x, 0, x + 12, 22), relleno="#efebe9", trazo="#000000", grosor=0.3)
        v2.rect((x + 2, 4, x + 10, 22), relleno="#ffffff", trazo="#000000", grosor=0.25)
        v2.texto((x + 6, 1.0), fmt(hol, 1), tam=2.6, ancla="centro")
    v2.texto((0, -16), "Ranuras de 8 + 2×holgura para un taco de 8,0 mm:", tam=2.8)
    v2.texto((0, -20.5), "elige la holgura de los topes de la loseta.", tam=2.8)
    cuadro_titulo(lz, "Piezas de prueba: imanes y encaje",
                  [f"Diámetros de agujero a probar (contrato): {', '.join(fmt(d, 1) for d in c.AGUJEROS_IMAN_PRUEBA)} "
                   f"mm. El imán debe entrar a presión con el pulgar y no caerse boca abajo.",
                   "Si todos quedan flojos o duros, anota cuál y ajusta el resto de agujeros con ese valor."])
    return lz


def plano_camara(anclajes, cam: Camara, fov_min: float, visib: dict[str, float], visib_aruco: dict[str, float]) \
        -> Lienzo:
    """Vista superior: losetas, robot, posición de la cámara y lo que ve sobre el plano de las piezas."""
    pp = parametros_pose()
    obj = np.asarray(pp["objetivo"], dtype=float)
    # huella de la imagen sobre el plano Z_SUPERFICIE
    th, tv = math.tan(math.radians(cam.fov_h) / 2), math.tan(math.radians(cam.fov_v) / 2)
    huella_img = []
    for su, sv in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        d = cam.adelante + su * th * cam.derecha + sv * tv * cam.arriba
        t = (Z_SUPERFICIE - cam.pos[2]) / d[2]
        q = cam.pos + t * d
        huella_img.append((q[0], q[1]))
    xs = [p[0] for p in huella_img] + [cam.pos[0], BASE_ROBOT_X[0]]
    ys = [p[1] for p in huella_img] + [cam.pos[1]]
    x0, x1, y0, y1 = min(xs) - 20, max(xs) + 20, min(ys) - 20, max(ys) + 20
    e = min(180 / (y1 - y0), 150 / (x1 - x0))
    lz = Lienzo(270, (x1 - x0) * e + 45)
    v = Vista(lz, e, (10 + y1 * e, 40 + x1 * e), giro_pagina=90)
    v.pol(huella_img, relleno="#e3f2fd", trazo=AZUL, grosor=0.3, guiones=(2, 1))
    v.rect((BASE_ROBOT_X[0], BASE_ROBOT_Y[0], BASE_ROBOT_X[1], BASE_ROBOT_Y[1]), relleno="#cfd8dc", trazo="#37474f",
           grosor=0.3)
    for n, an in sorted(anclajes.items()):
        h = huellas(an)
        v.pol(h["loseta"], relleno="#efebe9", trazo="#5d4037", grosor=0.3)
        v.pol(h["pieza"], trazo="#5d4037", grosor=0.2)
        if c.ALMA_GROSOR:
            v.pol(rect_a_mesa(an, (*pieza_a_anclaje(X_PIEZA[0], 0.0), *pieza_a_anclaje(X_PIEZA[1], c.ALMA_GROSOR))),
                  relleno="#8d6e63", trazo=None)
        cx, cy = a_mesa(an, *pieza_a_anclaje(c.LONGITUD_CORDON / 2, -ANCHO_HUELLA / 4))
        v.texto((cx, cy), n, tam=6, negrita=True, ancla="centro", color="#5d4037")
    v.linea((cam.pos[0], cam.pos[1]), (obj[0], obj[1]), trazo=ROJO, grosor=0.4)
    v.circulo((obj[0], obj[1]), 1.5 / e, relleno=ROJO, trazo=None)
    v.circulo((cam.pos[0], cam.pos[1]), 3 / e, relleno="#000000", trazo=None)
    v.texto((cam.pos[0], cam.pos[1] - 6 / e), f"webcam ({fmt(cam.pos[0], 0)}, {fmt(cam.pos[1], 0)}, "
                                               f"{fmt(cam.pos[2], 0)})", tam=2.6)
    tx = 190
    lz.texto((tx, 40), "Pose (PoseCamara.por_defecto)", tam=3.0, negrita=True)
    filas = [f"altura {fmt(pp['altura'], 0)} mm", f"inclinación {fmt(pp['inclinacion'], 0)}° desde la vertical",
             f"azimut {fmt(pp['azimut'], 0)}° (0 = desde +X)",
             f"mira a ({', '.join(fmt(float(q), 0) for q in obj)})", f"FOV mínimo {fmt(fov_min, 1)}° (16:9)"]
    for i, t in enumerate(filas):
        lz.texto((tx, 46 + i * 4.5), t, tam=2.7)
    lz.texto((tx, 74), "Se ve con una T colocada", tam=3.0, negrita=True)
    for i, (n, f) in enumerate(sorted(visib.items())):
        fa = visib_aruco[n]
        ok = f > 0.99 and fa > 0.99
        lz.texto((tx, 80 + i * 4.5), f"{n}: cordón {fmt(100 * f, 0)} %, ArUco {fmt(100 * fa, 0)} %", tam=2.7,
                 color=VERDE if ok else ROJO)
    cuadro_titulo(lz, "Webcam de seguimiento (vista superior de la mesa)",
                  [f"Azul: lo que ve una webcam de FOV horizontal {fmt(cam.fov_h, 0)}° sobre el plano de las piezas "
                   f"(Z mesa = {fmt(Z_SUPERFICIE)}). Marrón oscuro: alma de la T.",
                   "Robot abajo, +X de la mesa hacia arriba. Línea roja: eje de la cámara hasta el punto al que mira."])
    return lz

def plano_antorcha_robot() -> Lienzo:
    lz = Lienzo(240, 120)
    v = Vista(lz, 1.1, (75, 80))
    # dedo fijo (perfil aproximado), eje de aproximación hacia +X
    a = [d[0] for d in DEDOS]
    t = [d[2] for d in DEDOS]
    perfil = [(PUNTA_DEDO_SOBRE_GRIPPERFRAME, 0.0)] + [(PUNTA_DEDO_SOBRE_GRIPPERFRAME - ai, -ti) for ai, ti in
                                                       zip(a, t)] + [(-50, -t[-1]), (-50, 0)]
    v.pol(perfil, relleno="#cfd8dc", trazo="#37474f", grosor=0.3)
    v.texto((-30, -24), "dedo fijo (no se mueve)", tam=2.6)
    r = 6.0
    v.rect((-45, 0.3, 0, 0.3 + 2 * r + 4), relleno="#ffe0b2", trazo=NARANJA, grosor=0.3)
    v.texto((-44, 2 * r + 7), "adaptador impreso (abraza el dedo fijo)", tam=2.4, color=NARANJA)
    v.rect((-40, 0.3 + 2, c.LONGITUD_ANTORCHA_ROBOT - 4, 0.3 + 2 + 2 * r), relleno="#eeeeee", trazo="#000000",
           grosor=0.35)
    led = (c.LONGITUD_ANTORCHA_ROBOT, 0.3 + 2 + r)
    v.circulo(led, 2.5, relleno=VERDE, trazo=None)
    v.linea((-50, led[1]), (c.LONGITUD_ANTORCHA_ROBOT + 12, led[1]), trazo=ROJO, grosor=0.2, guiones=(3, 1, 0.5, 1))
    v.linea((0, -26), (0, 22), trazo=GRIS, grosor=0.2, guiones=(1, 1))
    v.texto((0.5, -27), "gripperframe", tam=2.4, color=GRIS)
    v.cota((0, led[1]), led, 13, f"{fmt(c.LONGITUD_ANTORCHA_ROBOT)} (contrato)")
    v.cota((PUNTA_DEDO_SOBRE_GRIPPERFRAME, -4), (c.LONGITUD_ANTORCHA_ROBOT, -4), 6,
           fmt(c.LONGITUD_ANTORCHA_ROBOT - PUNTA_DEDO_SOBRE_GRIPPERFRAME))
    v.cota((0, 0), (0, led[1]), 6, fmt(led[1], 1))
    cuadro_titulo(lz, "Antorcha del robot (esquema, no forma definitiva)",
                  [f"Eje de la antorcha paralelo al eje de aproximación de la pinza; LED {c.COLOR_LED} en la punta a "
                   f"{fmt(c.LONGITUD_ANTORCHA_ROBOT)} mm del sitio gripperframe.",
                   f"Con antorcha de Ø{fmt(2 * r)} junto a la cara interior del dedo fijo, el eje queda a "
                   f"≈{fmt(led[1], 1)} mm de esa cara: la simulación debe usar el mismo desplazamiento."])
    return lz


# =================================================================================================================
# Markdown
# =================================================================================================================
def tabla(cabecera: list[str], filas: list[list]) -> str:
    out = ["| " + " | ".join(cabecera) + " |", "|" + "|".join("---" for _ in cabecera) + "|"]
    out += ["| " + " | ".join(str(x) for x in f) + " |" for f in filas]
    return "\n".join(out)


def _pt(p) -> str:
    return f"({fmt(p[0], 1)}, {fmt(p[1], 1)})"


def resumen_anclajes(anclajes) -> str:
    filas = []
    for n, an in sorted(anclajes.items()):
        id_a = [k for k, nom in c.IDS_ANCLAJE.items() if nom == n][0]
        p0, p1 = cordon_en_mesa(an)
        dmin, dmax = distancia_hombro(an)
        filas.append([n, id_a, fmt(an.x, 1), fmt(an.y, 1), f"{fmt(an.giro, 1)}°", _pt(p0), _pt(p1),
                      _pt(a_mesa(an, *c.ARUCO_EN_ANCLAJE[:2])), f"{fmt(dmin, 0)}–{fmt(dmax, 0)}"])
    return tabla(["Anclaje", "ArUco", "x", "y", "giro", "inicio del cordón", "fin del cordón", "centro ArUco anclaje",
                  "dist. al eje del hombro"], filas)


def tabla_losetas(anclajes) -> str:
    filas = []
    for n, an in sorted(anclajes.items()):
        esq = huellas(an)["loseta"]
        t = [a_mesa(an, *p) for p in tornillos_loseta()]
        filas.append([n, " ".join(_pt(p) for p in esq), " ".join(_pt(p) for p in t)])
    return tabla(["Loseta", "esquinas en la mesa (x, y)", "agujeros de tornillo en la mesa"], filas)


def texto_problemas(problemas: list[Problema]) -> str:
    if not problemas:
        return "**Sin solapes**: ninguna pieza (con su ArUco de anclaje) pisa a otra, las losetas quedan a ≥ " \
               f"{fmt(SEPARACION_MIN_LOSETAS)} mm entre sí y ninguna invade la base del robot."
    return "\n".join(f"- ⚠ {p.texto()}" for p in problemas)


def generar_contrato_md(sal: Path, problemas, camaras, cam_rec, fov_min, visib, visib_aruco, verif) -> str:
    lb_p = lado_con_margen(c.LADO_ARUCO_PIEZA)
    lb_a = lado_con_margen(c.LADO_ARUCO_ANCLAJE)
    mod = modulo_aruco(c.LADO_ARUCO_PIEZA)
    lx0, ly0, lx1, ly1 = loseta_local()
    hx0, hy0, hx1, hy1 = huella_pieza_local()
    yi = abs(imanes_local()[0][1])
    xs_im = sorted({p[0] for p in imanes_local()})
    zi = c.IMAN_ALTO + HOLGURA_IMAN_FONDO
    avisos = []
    if problemas:
        avisos.append(f"**Los anclajes del contrato se solapan** ({len(problemas)} problemas, sección 2.3). No "
                      f"fabriques la base hasta resolverlo.")
    if ancho_base(c.TipoPieza.T) != ancho_base(c.TipoPieza.RECTA):
        avisos.append(f"La base de la T mide {fmt(ancho_base(c.TipoPieza.T))} mm de ancho y la recta "
                      f"{fmt(ancho_base(c.TipoPieza.RECTA))}: con una sola huella la T baila "
                      f"{fmt((ANCHO_HUELLA - ancho_base(c.TipoPieza.T)) / 2)} mm por lado. **Recomendado: imprimir la "
                      f"base de la T a {fmt(ANCHO_HUELLA)} mm** (no cambia ningún marco ni el ArUco).")
    malos = [n for n in visib if visib[n] < 0.99 or visib_aruco[n] < 0.99]
    if malos:
        avisos.append(f"Con la webcam en su pose por defecto, el alma de la T tapa la punta o algún ArUco en los "
                      f"anclajes {', '.join(malos)} (sección 6.2).")
    if not ve_todo(cam_rec, c.ANCLAJES):
        avisos.append(f"Ninguna webcam típica ve toda la base desde la pose por defecto: hace falta un FOV horizontal "
                      f"de {fmt(fov_min, 1)}° (sección 6.2).")
    avisos.append("El ArUco de la pieza está en medio del cordón, junto a la junta: la mano o la antorcha lo taparán "
                  "a mitad de pasada. El software debe guardar la pose (la pieza está fija con imanes) o usar el "
                  "ArUco del anclaje.")
    if c.COLOR_LED == "verde":
        avisos.append("LED verde y ESP32: un verde de alta luminosidad cae 3,0-3,2 V y el pin da 3,3 V; con ESP32, "
                      "aliméntalo a 5 V con un transistor (sección 4).")
    avisos.append("La IMU no debe usar el magnetómetro: los imanes de neodimio de piezas y losetas lo desvían "
                  "(BNO055 en modo IMU/IMUPLUS, BNO085 con *Game Rotation Vector*).")

    md = [f"# Contrato de hardware de LeWelder",
          "",
          "> Generado por `herramientas/generar_hardware.py` a partir de `lewelder/contrato.py`. **No lo edites a "
          "mano**: cambia el contrato y vuelve a ejecutar el script (`python herramientas/generar_hardware.py`).",
          "",
          "Todas las medidas en **milímetros** y grados. Los planos están en [`planos/`](planos/) (PNG y SVG, a "
          "escala en el SVG).",
          "",
          "## Avisos",
          "",
          *[f"{i}. {a}" for i, a in enumerate(avisos, 1)],
          "",
          "## 0. Marcos de coordenadas",
          "",
          "- **Mesa:** origen en el centro de la base del robot soldador sobre la mesa (= origen del cuerpo `base` del "
          f"modelo MuJoCo: {fmt(-BASE_ROBOT_X[0], 1)} mm por delante del borde trasero de la base, centrado en Y, y "
          f"{fmt(EJE_HOMBRO_X, 1)} mm por detrás del eje de giro del hombro). X hacia delante (lejos del robot), "
          "Y a la izquierda vista desde detrás del robot, Z arriba. La superficie de la mesa (o del tablero común) "
          "es Z = 0.",
          "- **Pieza:** origen al **inicio del cordón**, X a lo largo del cordón (sentido de avance), Y a la "
          "izquierda del avance, Z arriba desde la cara superior de la chapa donde se apoya la punta. Unión a tope: "
          "el cordón es la junta (Y = 0, Z = 0). Unión en T: la esquina entre la base y el alma; el alma en Y ≥ 0.",
          "- **Anclaje:** se toma igual que el de la pieza colocada (origen al inicio del cordón) pero sobre la cara "
          f"superior de la loseta (Z mesa = {fmt(c.ALTURA_BASE_ANCLAJES)}). Z = 0 de la pieza está a Z mesa = "
          f"{fmt(Z_SUPERFICIE)}.",
          "- **Giro del anclaje:** alrededor de Z; **giro 0 → el cordón avanza en +Y de la mesa** y el +Y de la pieza "
          "apunta a −X de la mesa (hacia el robot). En general: X pieza = (−sen g, cos g), Y pieza = (−cos g, −sen g).",
          "",
          "## 1. Piezas",
          "",
          "Las dos piezas comparten huella, imanes y posición del ArUco, así cualquiera entra en cualquier anclaje.",
          "",
          "### 1.1 Unión a tope recta",
          "",
          "![Recta, vista superior](planos/pieza_recta_superior.png)",
          "",
          tabla(["Medida", "Valor", "Nota"], [
              ["Largo (X)", fmt(c.CHAPA_LARGO), f"de X = {fmt(X_PIEZA[0])} a X = {fmt(X_PIEZA[1])}"],
              ["Cordón", fmt(c.LONGITUD_CORDON), f"de X = 0 a X = {fmt(c.LONGITUD_CORDON)}, {c.N_TRAMOS} tramos de "
                                                  f"{fmt(c.TAMANO_TRAMO)}"],
              ["Ancho de cada chapa", fmt(c.CHAPA_ANCHO), "dos chapas iguales, simétricas respecto a Y = 0"],
              ["Junta", f"{fmt(c.HOLGURA_JUNTA)} de ancho", f"ranura de {fmt(PROFUNDIDAD_JUNTA)} de profundidad; las "
                                                             f"chapas quedan unidas por los "
                                                             f"{fmt(c.CHAPA_GROSOR - PROFUNDIDAD_JUNTA)} mm de abajo "
                                                             f"(una sola impresión)"],
              ["Ancho total (Y)", fmt(ancho_base(c.TipoPieza.RECTA)), f"de Y = {fmt(-ancho_base('recta') / 2)} a "
                                                                      f"{fmt(ancho_base('recta') / 2)}"],
              ["Grosor", fmt(c.CHAPA_GROSOR), "Z = 0 en la cara superior; cara inferior en Z = "
                                              f"{fmt(-c.CHAPA_GROSOR)}"],
              ["Chaflán llave", f"{fmt(CHAFLAN_LLAVE)} × 45°", "esquina (X máx., +Y): fin del cordón, lado izquierdo"],
          ]),
          "",
          "![Recta, sección](planos/pieza_recta_seccion.png)",
          "",
          "### 1.2 Unión en T",
          "",
          "![T, vista superior](planos/pieza_t_superior.png)",
          "",
          tabla(["Medida", "Valor", "Nota"], [
              ["Base", f"{fmt(c.CHAPA_LARGO)} × {fmt(ancho_base(c.TipoPieza.T))} × {fmt(c.CHAPA_GROSOR)}",
               f"centrada en Y = 0 (contrato). Recomendado {fmt(ANCHO_HUELLA)} de ancho para la huella común"
               if ancho_base(c.TipoPieza.T) != ANCHO_HUELLA else "centrada en Y = 0"],
              ["Alma", f"{fmt(c.CHAPA_LARGO)} × {fmt(c.ALMA_GROSOR)} × {fmt(c.ALMA_ALTO)} de alto",
               f"cara en Y = 0, ocupa 0 ≤ Y ≤ {fmt(c.ALMA_GROSOR)}, apoyada sobre la base (arista viva en el cordón)"],
              ["Cordón", fmt(c.LONGITUD_CORDON), "esquina base-alma (Y = 0, Z = 0)"],
              ["Antorcha", f"{fmt(c.ANGULO_TRABAJO_OBJETIVO['t'], 0)}° de trabajo", "llega desde −Y (lado del ArUco)"],
              ["Chaflán llave", f"{fmt(CHAFLAN_LLAVE)} × 45°", "misma esquina que la recta (no toca el alma)"],
          ]),
          "",
          "![T, sección](planos/pieza_t_seccion.png)",
          "",
          "### 1.3 ArUco de la pieza",
          "",
          tabla(["Dato", "Valor"], [
              ["Diccionario", f"`{c.DICCIONARIO_ARUCO}`"],
              ["Lado (solo negro)", fmt(c.LADO_ARUCO_PIEZA)],
              ["Módulo", f"{fmt(mod)} (lado / 6)"],
              ["Margen blanco", f"≥ 1 módulo → recorte de {fmt(lb_p)} × {fmt(lb_p)}"],
              ["Centro en el marco de la pieza", f"({', '.join(fmt(v) for v in c.ARUCO_EN_PIEZA)})"],
              ["Orientación", "X del marcador = X de la pieza (flecha +X de la hoja en el sentido de avance), arriba del "
                              "marcador hacia +Y (hacia la junta)"],
              ["Ids recta / T", f"{min(c.IDS_PIEZA[c.TipoPieza.RECTA])}–{max(c.IDS_PIEZA[c.TipoPieza.RECTA])} / "
                                f"{min(c.IDS_PIEZA[c.TipoPieza.T])}–{max(c.IDS_PIEZA[c.TipoPieza.T])} (uno por pieza)"],
              ["Holgura en la chapa", f"el recorte deja {fmt(c.CHAPA_ANCHO / 2 - lb_p / 2)} mm a cada lado en Y "
                                      f"(entre el borde exterior y la junta)"],
              ["Rebaje en el CAD", f"{fmt(lb_p + REBAJE_PEGATINA[0])} × {fmt(lb_p + REBAJE_PEGATINA[0])} × "
                                   f"{fmt(REBAJE_PEGATINA[1])} de profundidad, centrado en el ArUco: así la "
                                   f"pegatina cae siempre en su sitio"],
          ]),
          "",
          "### 1.4 Imanes de la pieza (cara inferior)",
          "",
          f"4 imanes de {fmt(c.IMAN_DIAMETRO)} × {fmt(c.IMAN_ALTO)} en X = {', '.join(fmt(x) for x in xs_im)} e "
          f"Y = ±{fmt(yi)} (centro de cada chapa), en agujeros ciegos de {fmt(zi)} de profundidad desde abajo "
          f"(quedan {fmt(c.CHAPA_GROSOR - zi)} mm de plástico por encima). El diámetro del agujero se elige con la "
          f"pieza de prueba (sección 3). **Polaridad**: los dos imanes del inicio del cordón (X = {fmt(xs_im[0])}) con "
          f"el norte hacia abajo y los dos del final (X = {fmt(xs_im[1])}) con el sur hacia abajo; en la loseta al "
          "revés. Así, girada 180°, la pieza se repele. Marca la cara norte de cada imán con rotulador antes de pegar "
          "(cianoacrilato).",
          "",
          "## 2. Base de anclajes",
          "",
          "### 2.1 Loseta de cada anclaje",
          "",
          f"Los anclajes van en fila y sus losetas quedan a ~{fmt(sep_min_losetas(c.ANCLAJES), 1)} mm unas de otras: "
          f"la base se diseña como **una base única de ~{fmt(dims_base()[0], 0)} × {fmt(dims_base()[1], 0)} × "
          f"{fmt(c.ALTURA_BASE_ANCLAJES)} mm** (la unión de las {len(c.ANCLAJES)} losetas de la tabla 2.2) y se "
          f"**imprime en {len(c.ANCLAJES)} tramos**, uno por anclaje (cada tramo de {fmt(lx1 - lx0)} × "
          f"{fmt(ly1 - ly0)} cabe en una cama de {fmt(ANCHO_IMPRESORA, 0)} mm), cortados por la línea media entre "
          "losetas contiguas. **Uniones**: cola de milano de 10 mm en cada junta (holgura 0,2 mm, lejos de topes, "
          "imanes y ArUco) más los tornillos de cada tramo al tablero común; la junta queda a ras, sin escalón. Cada "
          "tramo lleva la geometría de su loseta tal cual (abajo, en el marco de su anclaje).",
          "",
          "![Loseta](planos/loseta_anclaje.png)",
          "",
          tabla(["Elemento", "Medida (marco del anclaje)"], [
              ["Loseta", f"X de {fmt(lx0)} a {fmt(lx1)}, Y de {fmt(ly0)} a {fmt(ly1)}, grosor "
                         f"{fmt(c.ALTURA_BASE_ANCLAJES)}"],
              ["Huella de la pieza", f"X de {fmt(hx0)} a {fmt(hx1)}, Y de {fmt(hy0)} a {fmt(hy1)} "
                                     f"({fmt(hx1 - hx0)} × {fmt(hy1 - hy0)})"],
              ["Topes", f"4 L en las esquinas, brazos de {fmt(TOPE_LARGO)}, {fmt(TOPE_GROSOR)} de grueso, "
                        f"{fmt(TOPE_ALTO)} de alto, caras interiores a {fmt(HOLGURA_ENCAJE)} de la huella (hueco "
                        f"{fmt(hx1 - hx0 + 2 * HOLGURA_ENCAJE)} × {fmt(hy1 - hy0 + 2 * HOLGURA_ENCAJE)})"],
              ["Llave", f"bloque triangular de catetos {fmt(bloque_llave())} en la esquina (X máx., +Y): solo deja "
                        f"entrar la pieza con su chaflán en esa esquina"],
              ["Por qué topes y no rebaje", "la pieza apoya en la cara de la loseta: si se hunde en un rebaje, cambia "
                                            "la Z del contrato"],
              ["Imanes", f"mismos X, Y que en la pieza; agujero desde arriba de {fmt(zi)}, polaridad contraria"],
              ["ArUco del anclaje", f"centro ({', '.join(fmt(v) for v in c.ARUCO_EN_ANCLAJE)}), lado "
                                    f"{fmt(c.LADO_ARUCO_ANCLAJE)}, recorte {fmt(lb_a)}, rebaje "
                                    f"{fmt(lb_a + REBAJE_PEGATINA[0])} × {fmt(REBAJE_PEGATINA[1])}; id 0 = A, 1 = B, "
                                    f"2 = C, 3 = D; mismos ejes que el anclaje"],
              ["Tornillos", f"2 pasantes Ø{fmt(TORNILLO_LOSETA)} en {', '.join(_pt(p) for p in tornillos_loseta())}, "
                            f"avellanados"],
              ["Letra", f"letra del anclaje grabada (0,6 mm, {fmt(LETRA_ALTO)} de alto) junto al tornillo derecho"],
          ]),
          "",
          "### 2.2 Posición de cada anclaje (contrato)",
          "",
          resumen_anclajes(c.ANCLAJES),
          "",
          tabla_losetas(c.ANCLAJES),
          "",
          "![Base de anclajes](planos/base_anclajes.png)",
          "",
          "### 2.3 Comprobación de solapes",
          "",
          f"Se comprueban los polígonos reales en la mesa: pieza + recorte del ArUco del anclaje, losetas (separación "
          f"mínima {fmt(SEPARACION_MIN_LOSETAS)} mm) y base del robot (+{fmt(MARGEN_ROBOT)} mm).",
          "",
          texto_problemas(problemas),
          "",
          "### 2.4 Fijación a la mesa y referencia al robot",
          "",
          f"1. **Tablero común** (DM o contrachapado de 10-15 mm, unos {fmt(dims_tablero()[0], 0)} (X) × "
          f"{fmt(dims_tablero()[1], 0)} (Y) mm): el robot se atornilla o se "
          "embrida a él y las losetas se atornillan encima. El marco de la mesa queda unido al robot: se puede mover "
          "el conjunto sin perder la calibración. El tablero se sujeta a la mesa del evento con 2 sargentos. Su cara "
          "superior es Z = 0.",
          f"2. **Replanteo**: marca en el tablero el eje X (línea que pasa por el centro de la base del robot, hacia "
          f"delante) y el origen. Con escuadra y regla, marca los agujeros de tornillo de cada loseta (tabla de 2.2) "
          f"y taladra guías de 3 mm. Error admisible: ±1 mm (la cámara mide el resto con el ArUco del anclaje).",
          "3. **Comprobación**: con la cámara de seguimiento, la posición medida de cada ArUco de anclaje debe caer a "
          "menos de 2 mm de la de la tabla. Si no, corrige la loseta o anota la medida real en el contrato.",
          "",
          "## 3. Imanes y piezas de prueba",
          "",
          "![Pruebas](planos/prueba_imanes.png)",
          "",
          f"- Imán del contrato: **{fmt(c.IMAN_DIAMETRO)} × {fmt(c.IMAN_ALTO)} mm** de neodimio (N35 o mejor), "
          f"{c.IMANES_POR_PIEZA} por pieza y {c.IMANES_POR_PIEZA} por loseta.",
          f"- Agujeros a probar: **{', '.join(fmt(d, 1) for d in c.AGUJEROS_IMAN_PRUEBA)} mm**, profundidad "
          f"{fmt(zi)}. Elige el que entra a presión con el pulgar; si el imán gira o se cae boca abajo, demasiado "
          "flojo; si hay que martillear, demasiado duro (el PLA se raja). Pega siempre con una gota de cianoacrilato.",
          "- Ranuras de encaje 0,2 / 0,3 / 0,4 mm por lado: elige la holgura de los topes (por defecto "
          f"{fmt(HOLGURA_ENCAJE)}).",
          "- Imprime las pruebas con la misma impresora, filamento y perfil que las piezas: la holgura depende de "
          "ellos.",
          "",
          "## 4. Antorcha del alumno (requisitos, la forma es libre)",
          "",
          tabla(["Requisito", "Detalle"], [
              ["LED en la punta", f"LED {c.COLOR_LED} de 5 mm de alta luminosidad, centrado en el eje de la boquilla y "
                                  "asomando 2-3 mm: es el punto que sigue la cámara. Lijado o difuso para que se vea "
                                  "de lado (la cámara no lo ve de frente). Nada brillante cerca de la punta"],
              ["Eje de la antorcha", "del mango a la punta. Si la boquilla tiene cuello curvo, el eje es el del "
                                     "**tramo final** (boquilla)"],
              ["IMU", f"montada rígida y plana, con **+X paralelo al eje de la boquilla, hacia la punta** "
                      f"(contrato: {c.EJE_ANTORCHA_EN_IMU}). Lejos (> 3 cm) de imanes y del cable del LED. Sin "
                      "magnetómetro en la fusión"],
              ["Gatillo", "pulsador o microinterruptor de palanca bajo el índice, a GND con `INPUT_PULLUP`; recorrido "
                          "corto y tope mecánico"],
              ["Microcontrolador", "hueco para Arduino Nano (≈ 45 × 18 mm, + 2 mm de holgura) **o** ESP32 DevKit "
                                   "(≈ 55 × 28 mm); mide tu placa. Conector USB accesible para programar sin "
                                   "desmontar"],
              ["Cable", "USB de 3 m saliendo por detrás del mango, con **alivio de tensión**: brida o abrazadera "
                        "interior que muerda la funda + manguito flexible a la salida. El conector de la placa no "
                        "debe soportar tirones"],
              ["Cableado interno", "canal de Ø 4 mm del mango a la punta para 2 hilos del LED; IMU con 4 hilos "
                                   "(VCC, GND, SDA, SCL) cortos"],
              ["Montaje", "dos mitades atornilladas (M3 + insertos térmicos) para poder abrir; impresas sobre la cara "
                          "de corte"],
              ["Peso y tamaño", "parecido a una antorcha MIG pequeña: 180-250 mm, mango de Ø 30-35 mm, < 250 g"],
              ["Reposo / calibración (opcional)", "cuna en una esquina del tablero que sujete la antorcha en una "
                                                  "posición conocida (por ejemplo vertical): sirve de soporte y para "
                                                  "poner a cero la IMU"],
          ]),
          "",
          "Pines y protocolo (del contrato):",
          "",
          tabla(["Placa", "Gatillo", "LED", "SDA", "SCL"],
                [[k, v["gatillo"], v["led"], v["sda"], v["scl"]] for k, v in c.PINES.items()]),
          "",
          f"Serie a {c.BAUDIOS} baudios, {c.FRECUENCIA_ANTORCHA} Hz, una línea JSON por muestra "
          '`{"t": ms, "g": 0|1, "q": [w, x, y, z]}`; responde a `?` con `{"id": "alumno"}`.',
          "",
          "**LED y resistencia**: con Nano (5 V): LED verde (≈ 3,1 V a 15-20 mA) + resistencia de **100-150 Ω** "
          "directamente del pin. Con ESP32 (3,3 V) el verde casi no luce: usa un transistor NPN (BC547/2N2222, base "
          "con 1 kΩ) o un MOSFET lógico que conmute el LED desde 5 V (pin VIN/5V) con 100-150 Ω.",
          "",
          "## 5. Antorcha del robot",
          "",
          "![Antorcha del robot](planos/antorcha_robot.png)",
          "",
          tabla(["Requisito", "Detalle"], [
              ["Longitud", f"**{fmt(c.LONGITUD_ANTORCHA_ROBOT)} mm** desde el sitio `gripperframe` del modelo hasta "
                           f"el centro del LED, a lo largo del eje de aproximación de la pinza. En el robot real "
                           f"`gripperframe` está {fmt(PUNTA_DEDO_SOBRE_GRIPPERFRAME, 1)} mm por detrás del extremo del "
                           f"dedo fijo → el LED queda a "
                           f"**{fmt(c.LONGITUD_ANTORCHA_ROBOT - PUNTA_DEDO_SOBRE_GRIPPERFRAME, 1)} mm del extremo del "
                           f"dedo fijo**"],
              ["LED", f"{c.COLOR_LED}, igual que el del alumno, centrado en el eje y asomando 2-3 mm; responde a "
                      f"`{c.ORDEN_LED_ON.strip()}`/`{c.ORDEN_LED_OFF.strip()}` y a `?` con `{{\"id\": \"robot\"}}`"],
              ["Sujeción", "adaptador impreso que abraza el **dedo fijo** (no se mueve con la pinza) con 2 bridas o un "
                           "tornillo M3 pasante. No dependas de que la pinza apriete: deja la pinza en una posición "
                           "fija abierta para que el motor no trabaje en bloqueo"],
              ["Que no gire", "caras planas del adaptador contra las caras del dedo + antorcha con un plano o chaveta "
                              "en el adaptador. Con el robot quieto, empuja la punta con el dedo: no debe moverse "
                              "más de 0,5 mm"],
              ["Rigidez", "lo más corta y gruesa posible (Ø 12-16 mm), impresa tumbada (capas a lo largo) o con un "
                          "tubo de aluminio/carbono dentro"],
              ["Cable", "2 hilos del LED hasta un Nano en la muñeca o en la base; USB de 3 m con holgura para todo el "
                        "recorrido del brazo (incluido el giro de muñeca), sujeto con espiral al brazo"],
              ["Simulación", "la tarea de simulación debe poner la punta a la misma distancia y con el mismo "
                             "desplazamiento lateral (radio de la antorcha si va pegada a la cara interior del dedo)"],
          ]),
          "",
          "Medidas aproximadas de los dedos sacadas del modelo (`assets/so101`; **compruébalas con el calibre** en el "
          "robot real). a = distancia hacia atrás desde el extremo del dedo; ancho = perpendicular al cierre; "
          "grosor = en la dirección de cierre.",
          "",
          tabla(["a (mm)", "ancho dedo fijo", "grosor dedo fijo", "ancho dedo móvil", "grosor dedo móvil"],
                [[fmt(d[0]), fmt(d[1], 1), fmt(d[2], 1), fmt(d[3], 1), fmt(d[4], 1)] for d in DEDOS]),
          "",
          "Las caras interiores de los dedos no son paralelas (el dedo móvil gira): una antorcha redonda apretada "
          "entre ellos se va de lado; por eso el adaptador va al dedo fijo.",
          "",
          "## 6. Soportes de cámara",
          "",
          "### 6.1 Cámara de muñeca (política)",
          "",
          "- En el cuerpo de la pinza (gira con la muñeca), mirando a la punta de la antorcha. Parte del soporte "
          "de cámara de muñeca del SO-101 de LeRobot y añádele la inclinación.",
          f"- Si la cámara queda a 30 mm por detrás de `gripperframe` y a 40-50 mm del eje de la antorcha, inclínala "
          f"≈ {fmt(math.degrees(math.atan2(45, c.LONGITUD_ANTORCHA_ROBOT + 30)), 0)}° hacia el eje: la punta queda en "
          "el tercio inferior de la imagen y se ve el cordón por delante.",
          "- No debe sobresalir por debajo de la punta ni chocar con el alma de la T con la antorcha a 45° "
          "(compruébalo en la simulación); cable USB sujeto al brazo con holgura en la muñeca.",
          "",
          "### 6.2 Webcam de seguimiento",
          "",
          f"La pose de la webcam es la de todo el software: `PoseCamara.por_defecto()` de "
          f"`lewelder/camara_sintetica.py`: **{fmt(parametros_pose()['altura'], 0)} mm de altura, inclinada "
          f"{fmt(parametros_pose()['inclinacion'], 0)}° respecto a la vertical, azimut "
          f"{fmt(parametros_pose()['azimut'], 0)}°** (0 = desde +X, enfrente del robot; negativo hacia −Y, el lado del "
          f"anclaje A), mirando a ({', '.join(fmt(float(q), 0) for q in parametros_pose()['objetivo'])}). Centro "
          f"óptico en ({fmt(cam_rec.pos[0], 0)}, {fmt(cam_rec.pos[1], 0)}, {fmt(cam_rec.pos[2], 0)}) del marco de la "
          "mesa. Desde +X el alma de la T del anclaje A (girado −90°) taparía la punta; desde este lado no.",
          "",
          f"Para ver todas las losetas y la altura del alma con un {fmt(100 * MARGEN_IMAGEN, 0)} % de margen hace "
          f"falta un **FOV horizontal ≥ {fmt(fov_min, 1)}°** (16:9). Webcams típicas en 1080p:",
          "",
          tabla(["FOV horizontal", "FOV vertical", "¿ve toda la base?", "mm por píxel en las piezas"],
                [[f"{fmt(cm.fov_h, 0)}°", f"{fmt(cm.fov_v, 1)}°", "sí" if ve_todo(cm, c.ANCLAJES) else "no",
                  f"{fmt(mm_por_pixel(cm, c.ANCLAJES)[0], 2)}–{fmt(mm_por_pixel(cm, c.ANCLAJES)[1], 2)}"]
                 for _, cm in sorted(camaras.items())]),
          "",
          f"**Recomendado**: FOV ≈ {fmt(cam_rec.fov_h, 0)}° o más, en la pose de arriba. El alumno se coloca a un "
          "lado, no entre la cámara y la base. Exposición manual fija y baja.",
          "",
          "![Cámara](planos/camara_seguimiento.png)",
          "",
          "Con una T colocada en cada anclaje y esta cámara (FOV recomendado), se ve: " +
          ", ".join(f"{n}: cordón {fmt(100 * visib[n], 0)} %, esquinas de ArUco {fmt(100 * visib_aruco[n], 0)} %"
                    for n in sorted(visib)) + ". (Cordón: la punta a "
          f"{fmt(c.ALTURA_PUNTA)} mm con la antorcha a 45°, sin que el alma se interponga.)",
          "",
          "Soporte: rosca de 1/4\" de la webcam en un trípode o brazo articulado, o una pinza impresa a un tubo de "
          "Ø 20 mm; debe poder bloquearse (si la cámara se mueve hay que recalibrar). Calibra la cámara con el "
          "tablero de `aruco/tablero_calibracion_a4.pdf`.",
          "",
          "## 7. Tolerancias e impresión (PLA)",
          "",
          tabla(["Tema", "Recomendación"], [
              ["Capa / paredes / relleno", "0,2 mm; 3-4 perímetros; 20-30 % giroide (losetas 30 %: pesan y no se "
                                          "mueven)"],
              ["Pata de elefante", "compensación 0,15 mm o chaflán de 0,5 mm en las aristas de la cara de abajo: si "
                                   "no, la huella crece y no entra entre los topes"],
              ["Agujeros", "salen 0,1-0,3 mm más pequeños: por eso la pieza de prueba de imanes"],
              ["Holguras de encaje", f"deslizante 0,2-0,3 mm por lado (topes: {fmt(HOLGURA_ENCAJE)}); a presión "
                                     "0,05-0,1 mm"],
              ["Contracción", "PLA ≈ 0,2-0,3 %: en 140 mm, hasta −0,4 mm. Mide la primera pieza y corrige la escala "
                              "XY del laminador si se pasa de ±0,3"],
              ["Orientación", "piezas y losetas planas, cara inferior en la cama (los agujeros de imán de la pieza "
                              "quedan abajo y salen bien sin soportes); antorchas en dos mitades sobre la cara de "
                              "corte; antorcha del robot tumbada"],
              ["Color", "PLA mate gris oscuro o negro para piezas y losetas: más contraste con el LED y sin "
                        "reflejos; los ArUco llevan su margen blanco en la pegatina"],
              ["Pegatinas", "papel adhesivo mate, impresora láser si puede ser; nada de plastificar (brilla)"],
          ]),
          "",
          "## 8. Lista de verificación con calibre (±0,3 mm salvo que se diga)",
          "",
          *[f"- [ ] {t}" for t in [
              "Hoja de marcadores: la regla mide 50,0 mm (±0,3). Si no, se imprimió escalada: repetir al 100 %",
              f"Lado negro de un ArUco impreso: {fmt(c.LADO_ARUCO_PIEZA)} (±0,2)",
              f"Recta: largo {fmt(c.CHAPA_LARGO)}, ancho {fmt(ancho_base('recta'))}, grosor {fmt(c.CHAPA_GROSOR)}, "
              f"junta {fmt(c.HOLGURA_JUNTA)} (±0,2)",
              f"T: base {fmt(c.CHAPA_LARGO)} × {fmt(ancho_base('t'))}, alma {fmt(c.ALMA_GROSOR)} de grueso y "
              f"{fmt(c.ALMA_ALTO)} sobre la base (total {fmt(c.ALMA_ALTO + c.CHAPA_GROSOR)}); del borde −Y de la base a "
              f"la cara del alma {fmt(ancho_base('t') / 2)}",
              f"Chaflán llave de {fmt(CHAFLAN_LLAVE)} en la esquina correcta (fin del cordón, lado +Y)",
              f"Centro del ArUco pegado: a {fmt(c.ARUCO_EN_PIEZA[0])} del inicio del cordón (o "
              f"{fmt(c.ARUCO_EN_PIEZA[0] + c.MARGEN_X)} del borde) y a {fmt(abs(c.ARUCO_EN_PIEZA[1]))} de la junta",
              "Imanes: entran con el agujero elegido, quedan 0,1-0,3 mm por debajo de la cara y con la polaridad "
              "marcada",
              f"Loseta: grosor {fmt(c.ALTURA_BASE_ANCLAJES)}, hueco entre topes {fmt(hx1 - hx0 + 2 * HOLGURA_ENCAJE)} "
              f"× {fmt(hy1 - hy0 + 2 * HOLGURA_ENCAJE)}; la pieza entra sin forzar, no baila más de 0,3 y no entra "
              "girada 180°",
              f"Altura de la cara de la pieza colocada sobre el tablero: {fmt(Z_SUPERFICIE)}",
              "Losetas en el tablero: tornillos a ±1 mm de la tabla de 2.2",
              f"Antorcha del robot: LED a {fmt(c.LONGITUD_ANTORCHA_ROBOT - PUNTA_DEDO_SOBRE_GRIPPERFRAME, 1)} del "
              "extremo del dedo fijo; no gira ni cede al empujarla",
              "Antorcha del alumno: la IMU marca +X hacia la punta (inclina la antorcha hacia abajo y mira el signo)",
          ]],
          "",
          "## 9. Marcadores ArUco y tablero de calibración",
          "",
          "- [`aruco/marcadores_a4.pdf`](aruco/marcadores_a4.pdf): página 1, piezas (ids "
          f"{min(c.IDS_PIEZA[c.TipoPieza.RECTA])}-{max(c.IDS_PIEZA[c.TipoPieza.T])}: los de recta y T, con "
          "repuestos); página 2, anclajes (0-3, dos de cada). Vectorial, A4, imprimir al 100 %.",
          "- [`aruco/tablero_calibracion_a4.pdf`](aruco/tablero_calibracion_a4.pdf): tablero de 9 × 6 esquinas "
          "interiores, cuadro de 25 mm (A4 apaisado).",
          f"- `aruco/aruco_XX_*.png`: cada marcador suelto a {PPP} ppp con su margen blanco; `aruco/hoja_*.png`: las "
          "páginas en PNG.",
          "",
          "Verificación automática (OpenCV vuelve a leer lo generado):",
          "",
          *[f"- {t}" for t in verif],
          "",
      ]
    return "\n".join(md)


def _dist_objetivo(cam: Camara) -> float:
    """Distancia de la cámara al punto donde su eje corta el plano de las piezas."""
    t = (cam.pos[2] - Z_SUPERFICIE) / -cam.adelante[2]
    return float(t)


def generar_lista_material(sal: Path) -> str:
    lx0, ly0, lx1, ly1 = loseta_local()
    vol_recta = c.CHAPA_LARGO * ancho_base("recta") * c.CHAPA_GROSOR / 1000
    vol_t = (c.CHAPA_LARGO * ANCHO_HUELLA * c.CHAPA_GROSOR + c.CHAPA_LARGO * c.ALMA_GROSOR * c.ALMA_ALTO) / 1000
    vol_loseta = (lx1 - lx0) * (ly1 - ly0) * c.ALTURA_BASE_ANCLAJES / 1000
    g = 1.24 * 0.45  # g/cm³ del PLA × fracción sólida típica (paredes + 25 % de relleno)
    n_anclajes = len(c.ANCLAJES)
    n_piezas = 3 + 3
    imanes = c.IMANES_POR_PIEZA * (n_piezas + n_anclajes) + len(c.AGUJEROS_IMAN_PRUEBA)
    imprimir = [
        ("Piezas de prueba: imanes + encaje", "1", "—", "≈ 10"),
        ("Pieza recta", "2 + 1 repuesto", "—", f"≈ {vol_recta * g:.0f} c/u"),
        ("Pieza en T", "2 + 1 repuesto", "—", f"≈ {vol_t * g:.0f} c/u"),
        (f"Base de anclajes única (~{fmt(dims_base()[0], 0)} × {fmt(dims_base()[1], 0)}) en {n_anclajes} tramos "
         f"de {fmt(lx1 - lx0)} × {fmt(ly1 - ly0)} con uniones de cola de milano", f"{n_anclajes} tramos", "—",
         f"≈ {vol_loseta * g * 0.8:.0f} por tramo"),
        ("Antorcha del alumno (2 mitades + gatillo)", "1 + gatillo de repuesto", "—", "≈ 60-90"),
        ("Antorcha del robot + adaptador al dedo fijo", "1 + 1 repuesto", "—", "≈ 20 c/u"),
        ("Soporte de cámara de muñeca", "1", "—", "≈ 15"),
        ("Soporte / pinza de la webcam de seguimiento", "1", "—", "≈ 30"),
        ("Cuna de reposo de la antorcha (opcional)", "1", "—", "≈ 20"),
    ]
    comprar = [
        ("IMU BNO055 o BNO085 (fusión en el chip); MPU6050 (GY-521) de respaldo barato", "2", "si no hay en casa"),
        ("Cable USB de 3 m (del tipo de tu placa: mini-USB Nano clásico, micro-USB o USB-C)", "2 + 1", ""),
        ("Hub USB con alimentación propia (≥ 4 puertos)", "1", "antorchas + webcams"),
        (f"Imanes de neodimio {fmt(c.IMAN_DIAMETRO)} × {fmt(c.IMAN_ALTO)} mm (N35+)", f"{imanes} → pedir "
         f"{int(math.ceil(imanes * 1.25 / 10) * 10)}", f"{c.IMANES_POR_PIEZA}/pieza × {n_piezas} piezas + "
                                                       f"{c.IMANES_POR_PIEZA}/loseta × {n_anclajes} + prueba"),
        (f"LED {c.COLOR_LED} 5 mm alta luminosidad (difuso o para lijar)", "10", "2 en uso + repuestos"),
        ("Resistencias 100 Ω y 150 Ω (1/4 W)", "10 de cada", ""),
        ("Transistor NPN BC547/2N2222 + resistencia 1 kΩ", "4", "solo si se usa ESP32"),
        ("Pulsador / microinterruptor de palanca (gatillo)", "2 + 1", ""),
        ("Microcontroladores (Nano o ESP32)", "2 + 1 repuesto", "uno por antorcha"),
        ("Papel adhesivo A4 mate", "5 hojas", "marcadores"),
        (f"Tablero DM/contrachapado 10-15 mm, ≈ {fmt(dims_tablero()[0], 0)} × {fmt(dims_tablero()[1], 0)}", "1",
         "base común robot + base de anclajes"),
        ("Sargentos", "2", "tablero a la mesa"),
        ("Tornillos M4 o tirafondos 4 × 16 avellanados", f"{2 * n_anclajes + 4}", "losetas"),
        ("Tornillos M3 + insertos térmicos M3", "10 + 10", "antorchas"),
        ("Cianoacrilato, bridas, termorretráctil, cable fino, funda espiral", "—", ""),
        ("PLA mate gris oscuro o negro", "1 kg", f"total estimado ≈ {_masa_total(vol_recta, vol_t, vol_loseta, g):.0f} g"),
    ]
    lineas = [
        "# Lista de material de LeWelder",
        "",
        "> Generada por `herramientas/generar_hardware.py` a partir de `lewelder/contrato.py`. Medidas en "
        "[contrato.md](contrato.md).",
        "",
        "## Imprimir",
        "",
        "Masas orientativas (PLA, 3-4 perímetros, 25 % de relleno). Tiempo: ≈ 12 g/h en una impresora clásica, "
        "≈ 30-40 g/h en una rápida.",
        "",
        tabla(["", "Pieza", "Cantidad", "Masa (g)"], [["☐", n, q, m] for n, q, _, m in imprimir]),
        "",
        "## Comprar o confirmar",
        "",
        tabla(["", "Material", "Cantidad", "Nota"], [["☐", n, q, nota] for n, q, nota in comprar]),
        "",
        "## Orden de impresión (todo listo antes del jueves 19)",
        "",
        "1. **Lun 16, noche — piezas de prueba** (imanes + encaje). Elegir agujero de imán y holgura de topes; "
        "imprimir la hoja de marcadores y medir la regla.",
        "2. **Mar 17, mañana — un tramo de la base y una recta.** Validar: la pieza entra sin bailar, no entra girada, imanes, "
        "pegatina en su rebaje, medidas con calibre (±0,3). Si algo falla, corregir antes de seguir.",
        "3. **Mar 17, tarde — antorcha del alumno** (lo que más se retrasa: electrónica dentro). Montar gatillo, LED e "
        "IMU y probar el firmware.",
        "4. **Mar 17, noche — resto de tramos de la base** (impresiones largas, de noche); probar las uniones "
        "entre tramos.",
        "5. **Mié 18 — piezas en T y recta de repuesto; antorcha del robot + adaptador; soportes de cámara.**",
        "6. **Jue 19, mañana — repuestos** (T, antorcha del robot, gatillo) y montaje del tablero con el robot. "
        "**Jue 19, tarde — prueba integrada.**",
        "",
    ]
    return "\n".join(lineas)


def _masa_total(vol_recta, vol_t, vol_loseta, g) -> float:
    return (3 * vol_recta + 3 * vol_t + len(c.ANCLAJES) * vol_loseta * 0.8) * g + 90 + 40 + 15 + 30 + 20 + 10


# =================================================================================================================
# Programa principal
# =================================================================================================================
def ids_hoja_piezas() -> list[int]:
    return list(c.IDS_PIEZA[c.TipoPieza.RECTA]) + list(c.IDS_PIEZA[c.TipoPieza.T])


def ids_hoja_anclajes() -> list[int]:
    return sorted(c.IDS_ANCLAJE) * 2


def marcador_suelto(id_aruco: int, lado: float) -> Lienzo:
    lb = lado_con_margen(lado)
    lz = Lienzo(lb, lb)
    m = (lb - lado) / 2
    dibujar_aruco_pagina(lz, id_aruco, m, m, lado)
    return lz


def generar(salida: Path, verificar: bool = True) -> dict:
    """Genera todo en `salida`. Devuelve un resumen con problemas y verificaciones (para los tests)."""
    salida = Path(salida)
    planos, aruco = salida / "planos", salida / "aruco"
    for d in (planos, aruco):
        d.mkdir(parents=True, exist_ok=True)

    # --- comprobaciones geométricas ---
    problemas = comprobar_huellas(c.ANCLAJES)
    camaras = {fh: camara_por_defecto(fh) for fh in FOV_HORIZONTAL}
    cam_tmp = camaras[FOV_HORIZONTAL[0]]
    fov_min = fov_necesario(cam_tmp, c.ANCLAJES)
    validas = [fh for fh in FOV_HORIZONTAL if fh >= fov_min]
    cam_rec = camaras[validas[0]] if validas else camara_por_defecto(math.ceil(min(fov_min, 150.0)))
    visib = {n: visibilidad_t(an, cam_rec) for n, an in c.ANCLAJES.items()}
    visib_aruco = {n: visibilidad_aruco(an, cam_rec) for n, an in c.ANCLAJES.items()}

    # --- planos ---
    dibujos = {
        "pieza_recta_superior": plano_pieza_superior(c.TipoPieza.RECTA),
        "pieza_recta_seccion": plano_pieza_seccion(c.TipoPieza.RECTA),
        "pieza_t_superior": plano_pieza_superior(c.TipoPieza.T),
        "pieza_t_seccion": plano_pieza_seccion(c.TipoPieza.T),
        "loseta_anclaje": plano_loseta(),
        "base_anclajes": plano_base(c.ANCLAJES, "Base de anclajes (contrato)", problemas),
        "prueba_imanes": plano_prueba_imanes(),
        "camara_seguimiento": plano_camara(c.ANCLAJES, cam_rec, fov_min, visib, visib_aruco),
        "antorcha_robot": plano_antorcha_robot(),
    }
    for ext in ("png", "svg"):  # plano de una versión anterior que ya no aplica
        (planos / f"base_anclajes_propuesta.{ext}").unlink(missing_ok=True)
    for nombre, lz in dibujos.items():
        lz.a_png(planos / f"{nombre}.png", 200)
        lz.a_svg(planos / f"{nombre}.svg")

    # --- ArUco ---
    hojas = [hoja_marcadores(ids_hoja_piezas(), "LeWelder · ArUco de las piezas (recta 10-19, T 20-29)",
                             c.LADO_ARUCO_PIEZA),
             hoja_marcadores(ids_hoja_anclajes(), "LeWelder · ArUco de los anclajes (0 = A, 1 = B, 2 = C, 3 = D)",
                             c.LADO_ARUCO_ANCLAJE)]
    lienzos_a_pdf(hojas, aruco / "marcadores_a4.pdf")
    hojas[0].a_png(aruco / "hoja_piezas.png", PPP, gris=True)
    hojas[1].a_png(aruco / "hoja_anclajes.png", PPP, gris=True)
    for id_aruco in ids_hoja_piezas() + sorted(c.IDS_ANCLAJE):
        lado = c.LADO_ARUCO_ANCLAJE if id_aruco in c.IDS_ANCLAJE else c.LADO_ARUCO_PIEZA
        marcador_suelto(id_aruco, lado).a_png(aruco / nombre_png(id_aruco), PPP, gris=True)
    tablero, _ = hoja_tablero()
    lienzos_a_pdf([tablero], aruco / "tablero_calibracion_a4.pdf")
    tablero.a_png(aruco / "tablero_calibracion.png", PPP, gris=True)

    # --- verificación ---
    verif, detalle = [], {}
    if verificar:
        verif, detalle = verificar_salida(salida)

    (salida / "contrato.md").write_text(
        generar_contrato_md(salida, problemas, camaras, cam_rec, fov_min, visib, visib_aruco, verif),
        encoding="utf-8")
    (salida / "lista_material.md").write_text(generar_lista_material(salida), encoding="utf-8")
    return {"problemas": problemas, "verificacion": detalle, "camara": cam_rec, "fov_necesario": fov_min,
            "visibilidad": visib, "visibilidad_aruco": visib_aruco}


def verificar_salida(salida: Path) -> tuple[list[str], dict]:
    """Vuelve a leer PNG y PDF con OpenCV: ids y lado en mm. Devuelve (líneas para el md, detalle)."""
    aruco = salida / "aruco"
    lineas, detalle = [], {}
    tol = 0.15
    esperados = {"hoja_piezas.png": (ids_hoja_piezas(), c.LADO_ARUCO_PIEZA),
                 "hoja_anclajes.png": (sorted(set(ids_hoja_anclajes())), c.LADO_ARUCO_ANCLAJE)}
    for nombre, (ids, lado) in esperados.items():
        img, ppp = leer_gris(aruco / nombre)
        det = detectar_aruco(img, ppp)
        ok = set(det) == set(ids) and all(abs(v - lado) < tol for v in det.values())
        detalle[nombre] = {"ids": det, "ok": ok, "ppp": ppp}
        lados = list(det.values()) or [float("nan")]
        lineas.append(f"`{nombre}` ({fmt(ppp, 0)} ppp): {len(det)} ids detectados de {len(set(ids))} esperados, "
                      f"lado {fmt(min(lados), 2)}–{fmt(max(lados), 2)} mm (contrato {fmt(lado)}) → "
                      f"{'OK' if ok else 'FALLA'}")
    sueltos_ok = True
    for id_aruco in ids_hoja_piezas() + sorted(c.IDS_ANCLAJE):
        img, ppp = leer_gris(aruco / nombre_png(id_aruco))
        # margen extra para que el detector vea el borde blanco completo
        img = cv2.copyMakeBorder(img, 60, 60, 60, 60, cv2.BORDER_CONSTANT, value=255)
        det = detectar_aruco(img, ppp)
        lado = c.LADO_ARUCO_ANCLAJE if id_aruco in c.IDS_ANCLAJE else c.LADO_ARUCO_PIEZA
        ok = list(det) == [id_aruco] and abs(det[id_aruco] - lado) < tol
        sueltos_ok &= ok
        detalle[nombre_png(id_aruco)] = {"ids": det, "ok": ok, "ppp": ppp}
    lineas.append(f"PNG sueltos ({len(ids_hoja_piezas()) + len(c.IDS_ANCLAJE)}): "
                  f"{'todos con su id y lado correctos' if sueltos_ok else 'ALGUNO FALLA'}")
    paginas = rasterizar_pdf(aruco / "marcadores_a4.pdf")
    if paginas is None:
        lineas.append("`marcadores_a4.pdf`: no verificado (falta `pdftoppm`)")
        detalle["marcadores_a4.pdf"] = None
    else:
        res = []
        for pag, (ids, lado) in zip(paginas, esperados.values()):
            det = detectar_aruco(pag, PPP)
            res.append((det, set(det) == set(ids) and all(abs(v - lado) < tol for v in det.values())))
        ok = len(paginas) == 2 and all(r[1] for r in res)
        lados = [v for det, _ in res for v in det.values()] or [float("nan")]
        detalle["marcadores_a4.pdf"] = {"ok": ok, "paginas": [r[0] for r in res]}
        lineas.append(f"`marcadores_a4.pdf` rasterizado a {PPP} ppp con pdftoppm: {len(paginas)} páginas, "
                      f"{sum(len(r[0]) for r in res)} ids, lado {fmt(min(lados), 2)}–{fmt(max(lados), 2)} mm → "
                      f"{'OK' if ok else 'FALLA'}")
    img, ppp = leer_gris(aruco / "tablero_calibracion.png")
    lado_t = medir_tablero(img, ppp)
    ok_t = lado_t is not None and abs(lado_t - 25.0) < 0.2
    detalle["tablero"] = {"lado": lado_t, "ok": ok_t}
    lineas.append(f"Tablero: 9×6 esquinas detectadas, cuadro de {fmt(lado_t or 0, 2)} mm (25) → "
                  f"{'OK' if ok_t else 'FALLA'}")
    paginas_t = rasterizar_pdf(aruco / "tablero_calibracion_a4.pdf")
    if paginas_t:
        lado_pdf = medir_tablero(paginas_t[0], PPP)
        ok_tp = lado_pdf is not None and abs(lado_pdf - 25.0) < 0.2
        detalle["tablero_pdf"] = {"lado": lado_pdf, "ok": ok_tp}
        lineas.append(f"`tablero_calibracion_a4.pdf` rasterizado: cuadro de {fmt(lado_pdf or 0, 2)} mm → "
                      f"{'OK' if ok_tp else 'FALLA'}")
    return lineas, detalle


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--salida", type=Path, default=None, help="por defecto hardware/ (v1) o hardware/v2/ (--v2)")
    ap.add_argument("--sin-verificar", action="store_true", help="no relee los marcadores con OpenCV")
    ap.add_argument("--v2", action="store_true", help="genera el material de la v2 (generar_hardware_v2.py)")
    args = ap.parse_args(argv)
    if args.v2:
        import generar_hardware_v2  # en herramientas/, junto a este script

        return generar_hardware_v2.main((["--salida", str(args.salida)] if args.salida else []) +
                                        (["--sin-verificar"] if args.sin_verificar else []))
    args.salida = args.salida or RAIZ / "hardware"
    res = generar(args.salida, verificar=not args.sin_verificar)
    print(f"Generado en {args.salida}")
    for p in res["problemas"]:
        print(f"  AVISO: {p.texto()}")
    malos = [k for k, v in res["verificacion"].items() if v is not None and not v["ok"]]
    if malos:
        print(f"  VERIFICACIÓN FALLIDA: {', '.join(malos)}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
