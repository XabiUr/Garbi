"""Genera el material de hardware de LeWelder v2 a partir de `lewelder/contrato.py` (sección v2).

Completa el brief de CAD `hardware/v2/brief_solidworks.md` (que manda en las decisiones de diseño) con lo que Andoni
necesita para comprobarlo e imprimirlo:

- `contrato.md`: medidas, justificación del diseño para el robot, imanes (fuerza calculada y polaridad), antorcha y
  soporte, webcams estéreo (campo de visión necesario), mesa de montaje, tolerancias y lista de comprobación.
- `planos/*.png` y `planos/*.svg`: base, chapa móvil, antorcha con su soporte, webcams, mesa y pieza de prueba.
- `aruco/marcadores_v2_a4.pdf` (vectorial, A4, 100 %), `aruco/hoja_v2.png` y un PNG suelto por marcador (600 ppp),
  verificados con OpenCV (ids y lado en mm).
- `lista_material.md`: qué imprimir, qué comprar y en qué orden hasta el jueves 19.

Reutiliza las primitivas del generador v1 (`generar_hardware.py`: lienzo, PDF, ArUco, verificación). Es
idempotente: con las mismas entradas escribe los mismos bytes.

Uso:
    python herramientas/generar_hardware.py --v2            # escribe en hardware/v2/
    python herramientas/generar_hardware_v2.py --salida DIR
"""
from __future__ import annotations

import argparse
import math
import sys
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

RAIZ = Path(__file__).resolve().parents[1]
for _p in (RAIZ, RAIZ / "herramientas"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
import generar_hardware as gh  # noqa: E402  (primitivas del generador v1)
from lewelder import contrato as c  # noqa: E402
from lewelder.camara_sintetica import PoseCamara  # noqa: E402

fmt, tabla = gh.fmt, gh.tabla
ROJO, VERDE, AZUL, GRIS, NARANJA = gh.ROJO, gh.VERDE, gh.AZUL, gh.GRIS, gh.NARANJA
T, ESQ = c.TipoJunta.T, c.TipoJunta.ESQUINA

# =================================================================================================================
# Decisiones de fabricación (del brief `hardware/v2/brief_solidworks.md`; no son contrato: solo afectan al CAD)
# =================================================================================================================
BRIEF = "brief_solidworks.md"
# --- base fija (marco de la base: origen en el centro de la cara superior, Z = 0 en esa cara) ---
X_GUIAS = (-75.0, 75.0)  # largo de la ranura de la T y del tope de la esquina
CHAFLAN_RANURA = 1.5  # 45° en las dos aristas superiores de la ranura
TOPE_Y = (c.ANCHO_BASE / 2, c.ANCHO_BASE / 2 + 3.0)  # nervio exterior pegado al canto +Y
CHAFLAN_TOPE = 1.0  # 45° en la arista superior interior del tope
CHAFLAN_BASE_ABAJO = 0.5
# En la base (las dos líneas) y en el canto de la chapa móvil. El brief decía ±50, pero en la chapa el imán de +50
# queda bajo el hueco de la pegatina ArUco (X 17,3-52,7) con 0,55 mm de pared: a ±56 la pared es de 1,15 mm y las
# posiciones siguen siendo simétricas (la polaridad asimétrica sigue rechazando la chapa girada).
X_IMANES = (-56.0, 0.0, 56.0)
X_IMANES_BRIEF = (-50.0, 0.0, 50.0)
AGUJERO_IMAN_BASE = c.AGUJEROS_IMAN_PRUEBA[1]  # Ø nominal 10,4 (se elige con la pieza de prueba)
PROF_IMAN_BASE = {T: 3.2, ESQ: 4.5}  # agujeros ciegos desde la cara inferior
REBAJE_ARUCO = (35.4, 0.3)  # lado y profundidad del hueco de cada pegatina (35 × 35 + 0,2 por lado)
PATAS = [(sx * 90.0, sy * 32.0) for sx in (-1, 1) for sy in (-1, 1)]  # rebajes Ø10 × 1 para tacos de goma
PATA_DIAMETRO = 10.0
# --- chapa móvil (marco: origen en el centro del canto inferior, X a lo largo, Y = grosor, Z = altura) ---
CHAFLAN_MOVIL = 0.5
Z_ALETA = 20.0  # centro de la aleta en altura (el contrato da su X: ALETA["x"])
CHAFLAN_ALETA = 1.5  # 45° en las cuatro aristas del extremo libre
RADIO_RAIZ_ALETA = 2.0
IMAN_MOVIL = (4.0, 4.0)  # Ø × alto, N52: un Ø10 no cabe en 6 mm de grosor
AGUJERO_IMAN_MOVIL = (4.3, 4.3)  # Ø × profundidad (el imán queda 0,3 dentro: la chapa apoya en plástico)
AGUJEROS_IMAN_MOVIL_PRUEBA = (4.1, 4.3, 4.5)
RELLENO_MACIZO_MOVIL = 8.0  # mm inferiores con 100 % de relleno
# Polaridad (cara que mira a la otra pieza), en el orden de X_IMANES. Asimétrica para que la chapa girada 180° se
# repela: la base lleva N, N, S hacia arriba y la chapa S, S, N hacia abajo.
POLARIDAD_BASE = ("N", "N", "S")
POLARIDAD_MOVIL = ("S", "S", "N")
BR_N52 = 1.43  # T, remanencia típica de un N52
# --- antorcha del robot (marco: origen en la punta, +Z hacia el mango) ---
ANTORCHA_DIAMETRO = 14.0
CONO_PUNTA = (12.0, 6.0)  # largo del cono y Ø de la punta
LED_AGUJERO = (5.2, 8.0)
MANGO = {"x": 20.0, "y": 12.0, "largo": 30.0, "chaflan": 2.0}  # caras planas en ±Y: las que aprieta la pinza
CHAVETA = {"plano": 1.0, "z0": 15.0}  # plano en el lado +X, desde z0 hasta el mango
# --- soporte de la antorcha (marco: origen en el centro del pie, sobre el tablero) ---
PIE_SOPORTE = (70.0, 70.0, 6.0)
AGUJEROS_PIE = [(sx * 27.0, sy * 27.0) for sx in (-1, 1) for sy in (-1, 1)]
TUBO = {"exterior": 24.0, "interior": 14.6, "alto": 66.0}  # Z del borde superior
ENTRADA_CONICA = (22.0, 8.0)  # Ø en el borde y altura del cono de entrada
ASIENTO_D = 10.0  # Ø donde el cono de la punta apoya en el asiento cónico (no en el LED)
HOLGURA_PUNTA = 2.0  # mm entre la punta y la cara superior del pie
# --- pieza de prueba ---
PRUEBA_BLOQUE = (70.0, 40.0, 8.0)
PRUEBA_CHAPA_LARGO = 60.0
X_IMANES_PRUEBA = (-15.0, 15.0)
# --- webcams y mesa ---
FOV_CANDIDATOS = (65.0, 70.0, 74.0, 78.0, 90.0)
ANGULO_ARUCO_MAX = 60.0  # más oblicuo que esto, la detección del ArUco es dudosa
PASO_GIRO = 5.0  # grados, muestreo del giro en la zona libre
MARGEN_ZONA = 10.0  # mm libres entre la chapa tumbada y la base
ALTURA_TAPETE = 3.0


# =================================================================================================================
# Geometría derivada (todo sale del contrato y de las decisiones de arriba)
# =================================================================================================================
def y_linea(junta) -> float:
    """Y del eje de la línea de montaje (centro del grosor de la chapa móvil colocada)."""
    return c.Y_CORDON[c.TipoJunta(junta)] + c.GROSOR_CHAPA / 2


def ranura_t() -> tuple[float, float, float, float]:
    """Rectángulo de la ranura de la T (sin chaflanes) en el marco de la base."""
    y = y_linea(T)
    return (X_GUIAS[0], y - c.GUIA_T["ancho"] / 2, X_GUIAS[1], y + c.GUIA_T["ancho"] / 2)


def ranura_t_con_chaflan() -> tuple[float, float, float, float]:
    x0, y0, x1, y1 = ranura_t()
    return (x0, y0 - CHAFLAN_RANURA, x1, y1 + CHAFLAN_RANURA)


def tope_esquina() -> tuple[float, float, float, float]:
    return (X_GUIAS[0], TOPE_Y[0], X_GUIAS[1], TOPE_Y[1])


def z_canto_movil(junta) -> float:
    """Z (marco de la base) del canto inferior de la chapa móvil colocada: en la T entra en la ranura."""
    return -c.GUIA_T["profundo"] if c.TipoJunta(junta) is T else 0.0


def partes_base() -> list[tuple[float, float, float, float]]:
    """Rectángulos convexos que forman la huella de la base (placa + nervio del tope, que baja hasta la mesa)."""
    return [(-c.LARGO_BASE / 2, -c.ANCHO_BASE / 2, c.LARGO_BASE / 2, c.ANCHO_BASE / 2), tope_esquina()]


def imanes_base(junta) -> list[tuple[float, float]]:
    return [(x, y_linea(junta)) for x in X_IMANES]


def z_iman_base(junta) -> tuple[float, float]:
    """(Z inferior, Z superior) del imán de la base, metido hasta el fondo de su agujero ciego (desde abajo)."""
    arriba = -c.GROSOR_CHAPA + PROF_IMAN_BASE[c.TipoJunta(junta)]
    return arriba - c.IMAN_ALTO, arriba


def piel_iman_base(junta) -> float:
    """Plástico entre el imán de la base y la superficie donde apoya la chapa móvil."""
    return z_canto_movil(junta) - z_iman_base(junta)[1]


def aruco_base(con_rebaje: bool = True) -> tuple[float, float, float, float]:
    lado = REBAJE_ARUCO[0] if con_rebaje else c.LADO_ARUCO_V2
    return gh.rect_centrado(c.ARUCO_EN_BASE[0], c.ARUCO_EN_BASE[1], lado)


def aleta_rect() -> tuple[float, float, float, float]:
    """Aleta en el alzado de la chapa móvil: (x0, z0, x1, z1)."""
    a = c.ALETA
    return (a["x"] - a["largo"] / 2, Z_ALETA - a["grosor"] / 2, a["x"] + a["largo"] / 2, Z_ALETA + a["grosor"] / 2)


def aruco_movil(con_rebaje: bool = True) -> tuple[float, float, float, float]:
    """ArUco de cada cara en el alzado de la chapa móvil: (x0, z0, x1, z1)."""
    lado = REBAJE_ARUCO[0] if con_rebaje else c.LADO_ARUCO_V2
    return gh.rect_centrado(c.ARUCO_EN_MOVIL[0], c.ARUCO_EN_MOVIL[1], lado)


def pared_iman_movil() -> float:
    return (c.GROSOR_CHAPA - AGUJERO_IMAN_MOVIL[0]) / 2


def pared_iman_aruco_movil(xs=None) -> float:
    """Plástico mínimo entre los agujeros de imán del canto y el hueco de la pegatina de cada cara: en grosor
    queda la pared del agujero menos la profundidad del hueco; si no se cruzan en el alzado, suma la separación."""
    ax0, az0, ax1, az1 = aruco_movil()
    d, pr = AGUJERO_IMAN_MOVIL
    en_grosor = pared_iman_movil() - REBAJE_ARUCO[1]
    peor = math.inf
    for x in xs or X_IMANES:
        sep_x = max(ax0 - (x + d / 2), (x - d / 2) - ax1, 0.0)
        sep_z = max(az0 - pr, 0.0)
        peor = min(peor, math.hypot(sep_x, sep_z, en_grosor))
    return peor


def solapan(a, b) -> bool:
    """¿Se solapan dos rectángulos (x0, y0, x1, y1) con área?"""
    return min(a[2], b[2]) - max(a[0], b[0]) > 1e-9 and min(a[3], b[3]) - max(a[1], b[1]) > 1e-9


def dentro(a, b) -> bool:
    """¿El rectángulo a está dentro del b?"""
    return a[0] >= b[0] - 1e-9 and a[1] >= b[1] - 1e-9 and a[2] <= b[2] + 1e-9 and a[3] <= b[3] + 1e-9


# --- pinza del SO-101 (medidas del modelo MuJoCo de `assets/so101`) ---------------------------------------------
# Hueco entre las puntas de los dedos (a = 0-5 mm) según el ángulo de la articulación `gripper` (rad), medido con
# las mallas del modelo; cerrada (−0,17 rad) las puntas se tocan.
APERTURA_PUNTA = ((0.0, 15.7), (0.2, 30.3), (0.4, 45.6), (0.6, 62.6))


def grosor_dedo(a: float) -> float:
    """Grosor máximo de los dos dedos (en la dirección de cierre) a `a` mm de la punta (interpolado de gh.DEDOS)."""
    aa = [d[0] for d in gh.DEDOS]
    g = [max(d[2], d[4]) for d in gh.DEDOS]
    return float(np.interp(a, aa, g))


def holgura_dedo_inferior(junta) -> float:
    """Hueco entre el dedo de abajo y lo que hay debajo al dejar la chapa (pinza horizontal, cierre vertical).

    T: debajo de toda la aleta está la cara de la base (Z = 0). Esquina: solo hay base bajo la punta del dedo (el
    tope, de Y +40 a +43, alto TOPE_ESQUINA); más allá, la mesa."""
    junta = c.TipoJunta(junta)
    z_abajo_aleta = z_canto_movil(junta) + Z_ALETA - c.ALETA["grosor"] / 2
    if junta is T:
        return z_abajo_aleta - grosor_dedo(c.ALETA["alto"])
    return z_abajo_aleta - grosor_dedo(TOPE_Y[1] - TOPE_Y[0] + 2.0) - c.TOPE_ESQUINA["alto"]


# --- imanes: modelo de dipolos (orientativo, ±50 % de cerca) ------------------------------------------------------
MU0 = 4e-7 * math.pi


def momento(diametro: float, alto: float, br: float = BR_N52) -> float:
    """Momento magnético (A·m²) de un imán cilíndrico axial: Br/μ0 × volumen."""
    return br / MU0 * math.pi * (diametro / 2000) ** 2 * (alto / 1000)


def fuerza_dipolos(m1, m2, d_mm) -> np.ndarray:
    """Fuerza (N) sobre el dipolo 2 debida al 1; d_mm = posición de 2 menos la de 1, en mm."""
    m1, m2, d = (np.asarray(v, float) for v in (m1, m2, d_mm))
    d = d / 1000
    r = np.linalg.norm(d)
    u = d / r
    k = 3 * MU0 / (4 * math.pi * r ** 4)
    return k * ((m1 @ u) * m2 + (m2 @ u) * m1 + (m1 @ m2) * u - 5 * (m1 @ u) * (m2 @ u) * u)


def _signo(polo_hacia_la_otra: str, la_otra_esta_arriba: bool) -> float:
    """Signo del momento en Z: el norte de un imán es la cara por la que sale su momento."""
    hacia = 1.0 if la_otra_esta_arriba else -1.0
    return hacia if polo_hacia_la_otra == "N" else -hacia


def fuerza_chapa(junta, dz: float = 0.0, dy: float = 0.0, girada: bool = False) -> np.ndarray:
    """Fuerza total (N, en Y y Z de la base) de los imanes de la base sobre la chapa móvil.

    dz: altura del canto de la chapa sobre su asiento; dy: desplazamiento transversal; girada: chapa girada 180°
    alrededor de Z (la aleta hacia el cordón). Z negativa = la base tira de la chapa hacia abajo."""
    junta = c.TipoJunta(junta)
    mb = momento(c.IMAN_DIAMETRO, c.IMAN_ALTO)
    mm_ = momento(*IMAN_MOVIL)
    zb = sum(z_iman_base(junta)) / 2
    zm = z_canto_movil(junta) + dz + (AGUJERO_IMAN_MOVIL[1] - IMAN_MOVIL[1]) + IMAN_MOVIL[1] / 2
    total = np.zeros(3)
    for xb, pb in zip(X_IMANES, POLARIDAD_BASE):
        m1 = np.array([0, 0, _signo(pb, True) * mb])
        for xm, pm in zip(X_IMANES, POLARIDAD_MOVIL):
            x = -xm if girada else xm
            m2 = np.array([0, 0, _signo(pm, False) * mm_])
            total += fuerza_dipolos(m1, m2, (x - xb, dy, zm - zb))
    return total


def masa_chapa() -> float:
    """Masa orientativa de la chapa móvil (g): PLA 1,24 g/cm³ y ~55 % macizo (chapa fina, 8 mm al 100 %)."""
    v = c.LARGO_MOVIL * c.GROSOR_CHAPA * c.ALTO_MOVIL + c.ALETA["largo"] * c.ALETA["alto"] * c.ALETA["grosor"]
    return v / 1000 * 1.24 * 0.55


def masa_base() -> float:
    v = c.LARGO_BASE * c.ANCHO_BASE * c.GROSOR_CHAPA + (X_GUIAS[1] - X_GUIAS[0]) * (TOPE_Y[1] - TOPE_Y[0]) * (
        c.GROSOR_CHAPA + c.TOPE_ESQUINA["alto"])
    return v / 1000 * 1.24 * 0.45


# --- antorcha del robot y soporte -------------------------------------------------------------------------------
def largo_cuerpo_antorcha() -> float:
    """Del LED al hombro del mango: las puntas de los dedos apoyan en el hombro y `gripperframe` queda a
    LONGITUD_ANTORCHA_ROBOT de la punta (está PUNTA_DEDO_SOBRE_GRIPPERFRAME por detrás del extremo del dedo)."""
    return c.LONGITUD_ANTORCHA_ROBOT - gh.PUNTA_DEDO_SOBRE_GRIPPERFRAME


def z_contacto_asiento() -> float:
    """Altura (marco de la antorcha) donde el cono de la punta mide ASIENTO_D."""
    largo, d0 = CONO_PUNTA
    return (ASIENTO_D - d0) / (ANTORCHA_DIAMETRO - d0) * largo


def semiangulo_cono() -> float:
    largo, d0 = CONO_PUNTA
    return math.degrees(math.atan((ANTORCHA_DIAMETRO - d0) / 2 / largo))


def z_asiento() -> float:
    """Z (sobre el tablero) del borde Ø ASIENTO_D del asiento cónico."""
    return PIE_SOPORTE[2] + HOLGURA_PUNTA + z_contacto_asiento()


def z_punta_en_soporte() -> float:
    return z_asiento() - z_contacto_asiento()


def z_mango_real() -> float:
    """Centro del mango sobre el tablero con la antorcha en su soporte."""
    return z_punta_en_soporte() + largo_cuerpo_antorcha() + MANGO["largo"] / 2


def z_gripperframe_en_soporte() -> float:
    return z_punta_en_soporte() + c.LONGITUD_ANTORCHA_ROBOT


def alto_asiento_conico() -> float:
    """Altura del asiento cónico: de Ø ASIENTO_D a Ø interior del tubo con el ángulo de la punta."""
    return (TUBO["interior"] - ASIENTO_D) / 2 / math.tan(math.radians(semiangulo_cono()))


# --- mesa de montaje -------------------------------------------------------------------------------------------
def rect_mesa(an: c.Anclaje, r) -> list[tuple[float, float]]:
    return gh.rect_a_mesa(an, r)


def base_en_mesa() -> list[list[tuple[float, float]]]:
    return [rect_mesa(c.POSICION_BASE, r) for r in partes_base()]


def zona_libre_rect(zona=None) -> list[tuple[float, float]]:
    z = zona or c.ZONA_LIBRE
    (x0, x1), (y0, y1) = z["x"], z["y"]
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def huella_tumbada(giro: float) -> list[tuple[float, float]]:
    """Esquinas de la chapa tumbada (centro en el origen) en la mesa: X de la chapa → (−sen g, cos g)."""
    an = c.Anclaje("tumbada", 0.0, 0.0, giro)
    return gh.rect_a_mesa(an, (-c.LARGO_MOVIL / 2, -c.ALTO_MOVIL / 2, c.LARGO_MOVIL / 2, c.ALTO_MOVIL / 2))


def _envolvente(pts) -> list[tuple[float, float]]:
    """Envolvente convexa (cadena monótona)."""
    pts = sorted(set((round(p[0], 6), round(p[1], 6)) for p in pts))
    if len(pts) <= 2:
        return pts

    def cruz(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    abajo, arriba = [], []
    for p in pts:
        while len(abajo) >= 2 and cruz(abajo[-2], abajo[-1], p) <= 0:
            abajo.pop()
        abajo.append(p)
    for p in reversed(pts):
        while len(arriba) >= 2 and cruz(arriba[-2], arriba[-1], p) <= 0:
            arriba.pop()
        arriba.append(p)
    return abajo[:-1] + arriba[:-1]


def giros_zona(zona=None) -> list[float]:
    g0, g1 = (zona or c.ZONA_LIBRE)["giro"]
    n = max(1, int(round((g1 - g0) / PASO_GIRO)))
    return [g0 + (g1 - g0) * i / n for i in range(n + 1)]


def barridos_zona(zona=None) -> list[list[tuple[float, float]]]:
    """Por cada giro muestreado, el polígono convexo que barre la chapa tumbada con su centro en la zona libre."""
    rect = zona_libre_rect(zona)
    return [_envolvente([(p[0] + q[0], p[1] + q[1]) for p in rect for q in huella_tumbada(g)])
            for g in giros_zona(zona)]


def barrido_total(zona=None) -> list[tuple[float, float]]:
    return _envolvente([p for pol in barridos_zona(zona) for p in pol])


def solape_barrido_base(zona=None) -> tuple[float, float]:
    """(área máxima de solape con la base en un giro, separación mínima) de la chapa tumbada con la base."""
    area, sep = 0.0, math.inf
    for pol in barridos_zona(zona):
        for parte in base_en_mesa():
            area = max(area, gh.area_solape(pol, parte))
            sep = min(sep, gh.separacion(pol, parte))
    return area, sep


def zona_propuesta() -> dict:
    """Zona libre con el mismo x y giro, y su y máxima recortada para que la chapa tumbada no llegue a la base
    (si la del contrato ya queda lejos de la base, se devuelve tal cual)."""
    z = dict(c.ZONA_LIBRE)
    area, sep = solape_barrido_base(z)
    if area <= 1e-6 and sep >= MARGEN_ZONA:
        return z
    ext =max(max(abs(p[1]) for p in huella_tumbada(g)) for g in giros_zona())
    y_base = min(p[1] for parte in base_en_mesa() for p in parte)
    y_max = math.floor((y_base - MARGEN_ZONA - ext) / 5) * 5
    z["y"] = (min(c.ZONA_LIBRE["y"][0], y_max - 60.0), y_max)
    return z


def soporte_en_mesa() -> list[tuple[float, float]]:
    s = c.SOPORTE_ANTORCHA
    w, h = PIE_SOPORTE[0] / 2, PIE_SOPORTE[1] / 2
    return [(s["x"] - w, s["y"] - h), (s["x"] + w, s["y"] - h), (s["x"] + w, s["y"] + h), (s["x"] - w, s["y"] + h)]


@dataclass
class Problema:
    texto: str
    grave: bool = True


def comprobar_mesa() -> list[Problema]:
    """Base, zona libre, soporte y robot: nada debe pisar a nada."""
    probs = []
    robot = gh.base_robot(gh.MARGEN_ROBOT)
    for parte in base_en_mesa():
        if gh.area_solape(parte, robot) > 1e-6:
            probs.append(Problema("la base invade la base del robot"))
        if gh.area_solape(parte, zona_libre_rect()) > 1e-6:
            probs.append(Problema("la base invade la zona libre"))
        if gh.area_solape(parte, soporte_en_mesa()) > 1e-6:
            probs.append(Problema("la base pisa el soporte de la antorcha"))
    if gh.area_solape(soporte_en_mesa(), robot) > 1e-6:
        probs.append(Problema("el soporte de la antorcha invade la base del robot"))
    for pol in barridos_zona():
        if gh.area_solape(pol, robot) > 1e-6:
            probs.append(Problema("la chapa tumbada en la zona libre puede tocar la base del robot"))
            break
    for pol in barridos_zona():
        if gh.area_solape(pol, soporte_en_mesa()) > 1e-6:
            probs.append(Problema("la chapa tumbada en la zona libre puede tocar el soporte de la antorcha"))
            break
    area, sep = solape_barrido_base()
    if area > 1e-6 or sep < MARGEN_ZONA:
        probs.append(Problema(
            f"la chapa tumbada (140 × 40, girada {fmt(c.ZONA_LIBRE['giro'][0], 0)}° a {fmt(c.ZONA_LIBRE['giro'][1], 0)}°) "
            f"con su centro en la zona libre del contrato llega hasta la base: solape de hasta {fmt(area, 0)} mm²"
            if area > 1e-6 else f"la chapa tumbada queda a {fmt(sep, 1)} mm de la base (< {fmt(MARGEN_ZONA, 0)})"))
    return probs


def dims_tablero() -> tuple[tuple[float, float], tuple[float, float]]:
    """Rectángulo del tablero común (x, y) que abarca robot, base, barrido de la zona libre y soporte (+30 mm)."""
    pts = gh.base_robot() + [p for parte in base_en_mesa() for p in parte] + barrido_total() + soporte_en_mesa()
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    x0, x1 = math.floor((min(xs) - 30) / 10) * 10, math.ceil((max(xs) + 30) / 10) * 10
    y0, y1 = math.floor((min(ys) - 30) / 10) * 10, math.ceil((max(ys) + 30) / 10) * 10
    return (x0, x1), (y0, y1)


# --- webcams estéreo -------------------------------------------------------------------------------------------
def camara(nombre: str, fov_h: float) -> gh.Camara:
    p = c.CAMARAS_ESTEREO[nombre]
    pose = PoseCamara.por_defecto(p["altura"], p["inclinacion"], p["objetivo"], p["azimut"])
    R = np.asarray(pose.R, float)
    return gh.Camara(np.asarray(pose.centro, float), R[2], R[0], -R[1], fov_h, gh.fov_vertical(fov_h))


def puntos_a_ver() -> list[tuple[float, float, float]]:
    """Base (con la chapa de pie en T o esquina) y la zona libre (chapa tumbada con la aleta), en la mesa."""
    zb = c.GROSOR_CHAPA  # la cara de la base está a Z mesa = grosor
    pts = []
    for parte in base_en_mesa():
        for x, y in parte:
            pts += [(x, y, 0.0), (x, y, zb + c.TOPE_ESQUINA["alto"])]
    for junta in (T, ESQ):
        y0 = c.Y_CORDON[junta]
        for xb in (-c.LARGO_MOVIL / 2, c.LARGO_MOVIL / 2):
            for yb in (y0, y0 + c.GROSOR_CHAPA):
                x, y = gh.a_mesa(c.POSICION_BASE, xb, yb)
                pts.append((x, y, zb + z_canto_movil(junta) + c.ALTO_MOVIL))
    alto = ALTURA_TAPETE + c.GROSOR_CHAPA + c.ALETA["alto"]
    for x, y in barrido_total():
        pts += [(x, y, 0.0), (x, y, alto)]
    return pts


def fov_necesario(cam: gh.Camara) -> float:
    v = np.array(puntos_a_ver()) - cam.pos
    z = v @ cam.adelante
    if np.any(z <= 1e-6):
        return math.inf
    aspecto = gh.RESOLUCION[0] / gh.RESOLUCION[1]
    t = max(np.max(np.abs(v @ cam.derecha) / z), np.max(np.abs(v @ cam.arriba) / z) * aspecto)
    return math.degrees(2 * math.atan(t / (1 - 2 * gh.MARGEN_IMAGEN)))


def marcadores_en_mesa() -> dict[str, tuple[np.ndarray, np.ndarray]]:
    """{nombre: (centro en la mesa, normal)} de los ArUco que deben ver las webcams."""
    zb = c.GROSOR_CHAPA
    ex, ey = gh.ejes_anclaje(c.POSICION_BASE)
    n_lisa = -np.array([ey[0], ey[1], 0.0])  # la cara lisa mira a −Y de la base
    res = {"30 · base": (np.array([*gh.a_mesa(c.POSICION_BASE, *c.ARUCO_EN_BASE[:2]), zb]), np.array([0, 0, 1.0]))}
    for junta, nombre in ((T, "41 · móvil en T"), (ESQ, "41 · móvil en esquina")):
        x, y = gh.a_mesa(c.POSICION_BASE, c.ARUCO_EN_MOVIL[0], c.Y_CORDON[junta])
        res[nombre] = (np.array([x, y, zb + z_canto_movil(junta) + c.ARUCO_EN_MOVIL[1]]), n_lisa)
    cx, cy = (sum(c.ZONA_LIBRE["x"]) / 2, sum(c.ZONA_LIBRE["y"]) / 2)
    res["40 · móvil tumbada"] = (np.array([cx, cy, ALTURA_TAPETE + c.GROSOR_CHAPA]), np.array([0, 0, 1.0]))
    return res


def vista_marcador(cam: gh.Camara, centro, normal) -> tuple[float, float, float]:
    """(ángulo con la normal en grados, lado aparente mayor y menor en píxeles) de un ArUco de LADO_ARUCO_V2."""
    v = cam.pos - centro
    dist = float(np.linalg.norm(v))
    ang = math.degrees(math.acos(float(np.clip(v @ normal / dist, -1, 1))))
    f = gh.RESOLUCION[0] / 2 / math.tan(math.radians(cam.fov_h) / 2)
    lado = c.LADO_ARUCO_V2 * f / dist
    return ang, lado, lado * math.cos(math.radians(ang))


def huella_imagen(cam: gh.Camara, z: float) -> list[tuple[float, float]]:
    th, tv = math.tan(math.radians(cam.fov_h) / 2), math.tan(math.radians(cam.fov_v) / 2)
    out = []
    for su, sv in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        d = cam.adelante + su * th * cam.derecha + sv * tv * cam.arriba
        t = (z - cam.pos[2]) / d[2]
        q = cam.pos + t * d
        out.append((float(q[0]), float(q[1])))
    return out


def mm_por_pixel(cam: gh.Camara) -> tuple[float, float]:
    f = gh.RESOLUCION[0] / 2 / math.tan(math.radians(cam.fov_h) / 2)
    ds = [(np.array(p) - cam.pos) @ cam.adelante for p in puntos_a_ver()]
    return min(ds) / f, max(ds) / f


# =================================================================================================================
# Planos
# =================================================================================================================
class VistaEspejo(gh.Vista):
    """Vista con la X del mundo hacia la izquierda de la página (la cara +Y de la chapa vista desde +Y)."""

    def p(self, x, y):
        return (self.o[0] - x * self.e, self.o[1] - y * self.e)


def _rect(v, r, **kw):
    v.rect(r, **kw)


def _texto_polo(v, centro, polo, color):
    v.texto((centro[0], centro[1] - 1.0), polo, tam=2.6, negrita=True, color=color, ancla="centro")


def plano_base_superior() -> gh.Lienzo:
    lz = gh.Lienzo(285, 190)
    v = gh.Vista(lz, 1.1, (142, 112))
    L, A = c.LARGO_BASE / 2, c.ANCHO_BASE / 2
    v.rect((-L, -A, L, A), relleno="#f5f5f5", trazo="#000000", grosor=0.35)
    v.rect(tope_esquina(), relleno="#bdbdbd", trazo="#000000", grosor=0.3)
    v.linea((X_GUIAS[0], TOPE_Y[0] + CHAFLAN_TOPE), (X_GUIAS[1], TOPE_Y[0] + CHAFLAN_TOPE), trazo=GRIS, grosor=0.15)
    v.rect(ranura_t_con_chaflan(), relleno="#e0e0e0", trazo=GRIS, grosor=0.15)
    v.rect(ranura_t(), relleno="#bdbdbd", trazo="#000000", grosor=0.3)
    for x, y in PATAS:
        v.circulo((x, y), PATA_DIAMETRO / 2, trazo=GRIS, grosor=0.15, guiones=(0.6, 0.5))
    for junta in (T, ESQ):
        for (x, y), polo in zip(imanes_base(junta), POLARIDAD_BASE):
            v.circulo((x, y), AGUJERO_IMAN_BASE / 2, trazo="#424242", grosor=0.2, guiones=(1, 0.6))
            _texto_polo(v, (x, y), polo, ROJO if polo == "N" else AZUL)
    ax0, ay0, ax1, ay1 = aruco_base()
    v.rect((ax0, ay0, ax1, ay1), trazo=GRIS, grosor=0.2)
    gh.dibujar_aruco_mundo(v, c.ID_BASE, c.ARUCO_EN_BASE[:2], c.LADO_ARUCO_V2)
    for junta in (T, ESQ):
        y0 = c.Y_CORDON[junta]
        v.rect((-c.LARGO_MOVIL / 2, y0, c.LARGO_MOVIL / 2, y0 + c.GROSOR_CHAPA), trazo=AZUL, grosor=0.25,
               guiones=(1.5, 1))
        v.flecha((-c.LONGITUD_CORDON / 2, y0), (c.LONGITUD_CORDON / 2, y0), color=ROJO, grosor=0.6, punta=2.5)
    v.texto((-c.LONGITUD_CORDON / 2, -5.5), "cordón T (Y = 0)", tam=2.4, color=ROJO)
    v.texto((-c.LONGITUD_CORDON / 2, c.Y_CORDON[ESQ] - 5.0), f"cordón esquina (Y = {fmt(c.Y_CORDON[ESQ])})", tam=2.4,
            color=ROJO)
    v.texto((-c.LARGO_MOVIL / 2 - 1, y_linea(T) - 1), "T", tam=3.2, negrita=True, color=AZUL, ancla="der")
    v.texto((-c.LARGO_MOVIL / 2 - 1, y_linea(ESQ) - 1), "ESQ", tam=3.2, negrita=True, color=AZUL, ancla="der")
    v.circulo((0, 0), 1.1, relleno="#000000", trazo=None)
    v.flecha((-L + 5, -A + 6), (-L + 25, -A + 6), color="#000000", grosor=0.35)
    v.flecha((-L + 5, -A + 6), (-L + 5, -A + 22), color="#000000", grosor=0.35)
    v.texto((-L + 26, -A + 5), "+X", tam=2.6)
    v.texto((-L + 6.5, -A + 21), "+Y", tam=2.6)
    # cotas
    v.cota((-L, -A), (L, -A), -9, fmt(c.LARGO_BASE))
    v.cota((-L, -A), (-L, A), 8, fmt(c.ANCHO_BASE))
    v.cota((X_GUIAS[0], TOPE_Y[1]), (X_GUIAS[1], TOPE_Y[1]), 5, f"ranura y tope: X {fmt(X_GUIAS[0])} a +{fmt(X_GUIAS[1])}")
    v.cota((L, A), (L, TOPE_Y[1]), -4, fmt(TOPE_Y[1] - TOPE_Y[0]))
    v.cota((L, 0), (L, y_linea(T)), -12, fmt(y_linea(T)))
    v.cota((L, 0), (L, y_linea(ESQ)), -20, fmt(y_linea(ESQ)))
    v.cota((X_IMANES[0], -A), (X_IMANES[1], -A), -16, fmt(X_IMANES[1] - X_IMANES[0]))
    v.cota((X_IMANES[1], -A), (X_IMANES[2], -A), -16, fmt(X_IMANES[2] - X_IMANES[1]))
    v.cota((0, -A), (c.ARUCO_EN_BASE[0], -A), -23, f"ArUco X = {fmt(c.ARUCO_EN_BASE[0])}")
    v.cota((ax1, 0), (ax1, c.ARUCO_EN_BASE[1]), -3, fmt(c.ARUCO_EN_BASE[1]))
    gh.cuadro_titulo(lz, "BASE-V2 · vista superior (marco de la base, mm)", [
        f"Placa {fmt(c.LARGO_BASE)} × {fmt(c.ANCHO_BASE)} × {fmt(c.GROSOR_CHAPA)}; origen en el centro de la cara "
        f"superior. Ranura T {fmt(c.GUIA_T['ancho'])} × {fmt(c.GUIA_T['profundo'])} (chaflán {fmt(CHAFLAN_RANURA)}); "
        f"tope de {fmt(TOPE_Y[1] - TOPE_Y[0])} × alto {fmt(c.TOPE_ESQUINA['alto'])} sobre la cara.",
        f"Imanes Ø{fmt(c.IMAN_DIAMETRO)}×{fmt(c.IMAN_ALTO)} desde abajo (polo que mira ARRIBA: N rojo, S azul). "
        f"Azul discontinuo: chapa móvil en T y en esquina. Gris: tacos de goma (abajo)."])
    return lz


def perfil_base() -> list[tuple[float, float]]:
    """Sección YZ de la base (X dentro de las guías): ranura con chaflanes y tope que baja hasta la mesa."""
    A, g = c.ANCHO_BASE / 2, c.GROSOR_CHAPA
    _, y0, _, y1 = ranura_t()
    p, ch, ct = c.GUIA_T["profundo"], CHAFLAN_RANURA, CHAFLAN_TOPE
    h = c.TOPE_ESQUINA["alto"]
    return [(-A, -g), (TOPE_Y[1], -g), (TOPE_Y[1], h), (TOPE_Y[0] + ct, h), (TOPE_Y[0], h - ct), (TOPE_Y[0], 0),
            (y1 + ch, 0), (y1, -ch), (y1, -p), (y0, -p), (y0, -ch), (y0 - ch, 0), (-A, 0)]


def _chapa_seccion(v, junta, color):
    y0 = c.Y_CORDON[junta]
    z0 = z_canto_movil(junta)
    g, a = c.GROSOR_CHAPA, c.ALETA
    ch = CHAFLAN_ALETA
    za0, za1 = z0 + Z_ALETA - a["grosor"] / 2, z0 + Z_ALETA + a["grosor"] / 2
    ya = y0 + g + a["alto"]
    pts = [(y0, z0), (y0 + g, z0), (y0 + g, za0), (ya - ch, za0), (ya, za0 + ch), (ya, za1 - ch), (ya - ch, za1),
           (y0 + g, za1), (y0 + g, z0 + c.ALTO_MOVIL), (y0, z0 + c.ALTO_MOVIL)]
    v.pol(pts, relleno="#e3f2fd", trazo=color, grosor=0.3, guiones=(1.5, 0.8))
    d, pr = AGUJERO_IMAN_MOVIL
    yc = y0 + g / 2
    v.rect((yc - d / 2, z0, yc + d / 2, z0 + pr), relleno="#ffffff", trazo=GRIS, grosor=0.2)
    zi = z0 + pr - IMAN_MOVIL[1]
    v.rect((yc - IMAN_MOVIL[0] / 2, zi, yc + IMAN_MOVIL[0] / 2, z0 + pr), relleno="#9e9e9e", trazo=None)
    v.circulo((y0, 0), 0.9, relleno=ROJO, trazo=None)


def plano_base_seccion() -> gh.Lienzo:
    lz = gh.Lienzo(285, 200)
    e = 2.3
    v = gh.Vista(lz, e, (18 + 44 * e, 168))
    v.pol(perfil_base(), relleno="#eeeeee", trazo="#000000", grosor=0.35)
    for junta in (T, ESQ):
        y = y_linea(junta)
        r = AGUJERO_IMAN_BASE / 2
        v.rect((y - r, -c.GROSOR_CHAPA, y + r, -c.GROSOR_CHAPA + PROF_IMAN_BASE[junta]), relleno="#ffffff",
               trazo=GRIS, grosor=0.2)
        zi0, zi1 = z_iman_base(junta)
        v.rect((y - c.IMAN_DIAMETRO / 2, zi0, y + c.IMAN_DIAMETRO / 2, zi1), relleno="#9e9e9e", trazo=None)
        _chapa_seccion(v, junta, AZUL)
    # antorcha a 45° en la T, desde −Y
    s = c.ALTURA_PUNTA / math.sqrt(2)
    v.linea((-s - 30, s + 30), (-s, s), trazo=ROJO, grosor=0.8)
    v.circulo((-s, s), 0.7, relleno=VERDE, trazo=None)
    v.texto((-s - 30, s + 32), "antorcha a 45° (T)", tam=2.4, color=ROJO)
    ye = c.Y_CORDON[ESQ]
    v.linea((ye - s - 14, s + 14), (ye - s, s), trazo=ROJO, grosor=0.8)
    v.texto((ye - s - 15, s + 16), "esquina", tam=2.4, color=ROJO)
    v.texto((y_linea(T), c.ALTO_MOVIL + 1.5), "T (canto en Z = −2)", tam=2.4, color=AZUL, ancla="centro")
    v.texto((y_linea(ESQ), c.ALTO_MOVIL + 3.5), "esquina (canto en Z = 0)", tam=2.4, color=AZUL, ancla="centro")
    # cotas
    _, y0, _, y1 = ranura_t()
    v.cota((y0, -c.GUIA_T["profundo"]), (y1, -c.GUIA_T["profundo"]), 13, fmt(c.GUIA_T["ancho"]))
    v.cota((y1 + CHAFLAN_RANURA + 1, 0), (y1 + CHAFLAN_RANURA + 1, -c.GUIA_T["profundo"]), -4,
           fmt(c.GUIA_T["profundo"]))
    v.cota((-c.ANCHO_BASE / 2, 0), (-c.ANCHO_BASE / 2, -c.GROSOR_CHAPA), -5, fmt(c.GROSOR_CHAPA))
    v.cota((TOPE_Y[1], -c.GROSOR_CHAPA), (TOPE_Y[1], c.TOPE_ESQUINA["alto"]), -5,
           fmt(c.GROSOR_CHAPA + c.TOPE_ESQUINA["alto"]))
    v.cota((TOPE_Y[0], c.TOPE_ESQUINA["alto"]), (TOPE_Y[1], c.TOPE_ESQUINA["alto"]), 4, fmt(TOPE_Y[1] - TOPE_Y[0]))
    for junta in (T, ESQ):
        y = y_linea(junta) + AGUJERO_IMAN_BASE / 2
        v.cota((y, -c.GROSOR_CHAPA), (y, -c.GROSOR_CHAPA + PROF_IMAN_BASE[junta]), -3,
               fmt(PROF_IMAN_BASE[junta]), tam=2.2)
    z0 = z_canto_movil(T)
    v.cota((c.GROSOR_CHAPA + c.ALETA["alto"], z0 + Z_ALETA - c.ALETA["grosor"] / 2),
           (c.GROSOR_CHAPA + c.ALETA["alto"], z0 + Z_ALETA + c.ALETA["grosor"] / 2), -4, fmt(c.ALETA["grosor"]))
    v.cota((c.GROSOR_CHAPA, z0 + Z_ALETA + 6), (c.GROSOR_CHAPA + c.ALETA["alto"], z0 + Z_ALETA + 6), 3,
           fmt(c.ALETA["alto"]))
    gh.cuadro_titulo(lz, "BASE-V2 · sección YZ por X = 0 (por los imanes), con la chapa móvil en T y en esquina", [
        "+Y a la derecha, Z arriba; Z = 0 en la cara superior de la base. Punto rojo: cordón. Gris oscuro: imanes "
        "metidos hasta el fondo de su agujero.",
        f"Piel bajo la chapa: T {fmt(piel_iman_base(T))} mm (suelo de la ranura), esquina {fmt(piel_iman_base(ESQ))}"
        f" mm. El tope es macizo de Z = −{fmt(c.GROSOR_CHAPA)} a +{fmt(c.TOPE_ESQUINA['alto'])} (apoya en la mesa)."])
    return lz


def plano_movil() -> gh.Lienzo:
    lz = gh.Lienzo(285, 215)
    e = 1.25
    L, H = c.LARGO_MOVIL / 2, c.ALTO_MOVIL
    ax0, az0, ax1, az1 = aleta_rect()
    vistas = [(gh.Vista(lz, e, (20 + L * e, 92)), "cara lisa (−Y, la del cordón) vista desde −Y", IDS_CARA["cara_lisa"],
               ((1, 0), (0, 1)), False),
              (VistaEspejo(lz, e, (20 + L * e, 175)), "cara de la aleta (+Y) vista desde +Y", IDS_CARA["cara_aleta"],
               ((-1, 0), (0, 1)), True)]
    for v, titulo, id_a, ejes, con_aleta in vistas:
        v.rect((-L, 0, L, H), relleno="#f5f5f5", trazo="#000000", grosor=0.35)
        v.rect(aruco_movil(), trazo=GRIS, grosor=0.2)
        gh.dibujar_aruco_mundo(v, id_a, c.ARUCO_EN_MOVIL, c.LADO_ARUCO_V2, ejes=ejes)
        for x, polo in zip(X_IMANES, POLARIDAD_MOVIL):
            d, pr = AGUJERO_IMAN_MOVIL
            v.rect((x - d / 2, 0, x + d / 2, pr), relleno="#ffffff", trazo="#424242", grosor=0.2, guiones=(0.8, 0.5))
            v.texto((x, pr + 1.2), f"{polo}↓", tam=2.4, negrita=True, color=ROJO if polo == "N" else AZUL,
                    ancla="centro")
        if con_aleta:
            v.rect((ax0, az0, ax1, az1), relleno="#90caf9", trazo=AZUL, grosor=0.3)
            v.texto(((ax0 + ax1) / 2, az1 + 1.5), "aleta", tam=2.4, color=AZUL, ancla="centro")
        else:
            v.rect((ax0, az0, ax1, az1), trazo=AZUL, grosor=0.2, guiones=(1, 0.7))
            v.linea((-c.LONGITUD_CORDON / 2, 0), (c.LONGITUD_CORDON / 2, 0), trazo=ROJO, grosor=0.8)
        v.texto((0, H + 2.5), titulo, tam=2.8, negrita=True, ancla="centro")
        v.texto((-L if not con_aleta else L, -4.5), "−X" if not con_aleta else "−X", tam=2.4, ancla="centro")
        v.texto((L if not con_aleta else -L, -4.5), "+X", tam=2.4, ancla="centro")
    v1, v2 = vistas[0][0], vistas[1][0]
    v1.cota((-L, 0), (L, 0), -9, fmt(c.LARGO_MOVIL))
    v1.cota((-L, 0), (-L, H), 6, fmt(H))
    v1.cota((0, H), (c.ARUCO_EN_MOVIL[0], H), 7, f"ArUco X = {fmt(c.ARUCO_EN_MOVIL[0])}")
    v1.cota((L, 0), (L, c.ARUCO_EN_MOVIL[1]), -5, fmt(c.ARUCO_EN_MOVIL[1]))
    v1.cota((X_IMANES[0], 0), (X_IMANES[1], 0), -4, fmt(X_IMANES[1] - X_IMANES[0]), tam=2.2)
    v2.cota((ax0, az0), (ax1, az0), 4, fmt(c.ALETA["largo"]))
    v2.cota((0, H), (c.ALETA["x"], H), 7, f"aleta X = {fmt(c.ALETA['x'])}")
    v2.cota((ax0, 0), (ax0, Z_ALETA), -5, fmt(Z_ALETA))
    # sección por la aleta (YZ, X = ALETA["x"])
    vs = gh.Vista(lz, 1.6, (215, 150))
    g, a, ch = c.GROSOR_CHAPA, c.ALETA, CHAFLAN_ALETA
    y0 = -g / 2
    za0, za1 = Z_ALETA - a["grosor"] / 2, Z_ALETA + a["grosor"] / 2
    ya = g / 2 + a["alto"]
    vs.pol([(y0, 0), (g / 2, 0), (g / 2, za0), (ya - ch, za0), (ya, za0 + ch), (ya, za1 - ch), (ya - ch, za1),
            (g / 2, za1), (g / 2, H), (y0, H)], relleno="#e3f2fd", trazo="#000000", grosor=0.3)
    d, pr = AGUJERO_IMAN_MOVIL
    vs.rect((-d / 2, 0, d / 2, pr), relleno="#ffffff", trazo=GRIS, grosor=0.2)
    vs.rect((-IMAN_MOVIL[0] / 2, pr - IMAN_MOVIL[1], IMAN_MOVIL[0] / 2, pr), relleno="#9e9e9e", trazo=None)
    vs.cota((y0, 0), (g / 2, 0), -6, fmt(g))
    vs.cota((g / 2, za1), (ya, za1), 4, fmt(a["alto"]))
    vs.cota((ya, za0), (ya, za1), -4, fmt(a["grosor"]))
    vs.cota((-d / 2, 0), (-d / 2, pr), 3, fmt(pr), tam=2.2)
    vs.texto((g / 2 + 2, H - 2), "+Y", tam=2.4)
    vs.texto((0, H + 3), "sección por la aleta", tam=2.6, negrita=True, ancla="centro")
    vs.texto((ya - 4, za0 - 4), f"chaflán {fmt(ch)}×45°", tam=2.2, color=AZUL, ancla="centro")
    gh.cuadro_titulo(lz, "MOVIL-V2 · chapa móvil con aleta (marco de la chapa, mm)", [
        f"Origen en el centro del canto inferior; X a lo largo (al montarla, X chapa = X base), Z = altura, Y = grosor "
        f"(cara lisa en −Y). Chaflán {fmt(CHAFLAN_MOVIL)} en todas las aristas.",
        f"Imanes Ø{fmt(IMAN_MOVIL[0])}×{fmt(IMAN_MOVIL[1])} N52 en agujeros Ø{fmt(AGUJERO_IMAN_MOVIL[0])} × "
        f"{fmt(AGUJERO_IMAN_MOVIL[1])} desde el canto (polo que mira ABAJO). La cara de la aleta se ve en espejo."])
    return lz


IDS_CARA = c.IDS_MOVIL


def plano_antorcha_soporte() -> gh.Lienzo:
    lz = gh.Lienzo(285, 215)
    e = 1.25
    v = gh.Vista(lz, e, (75, 200))  # X de la antorcha a la derecha, Z (tablero) arriba
    W, Hp = PIE_SOPORTE[0] / 2, PIE_SOPORTE[2]
    ri, re_ = TUBO["interior"] / 2, TUBO["exterior"] / 2
    v.rect((-W, 0, W, Hp), relleno="#d7ccc8", trazo="#000000", grosor=0.3)
    za, ha = z_asiento(), alto_asiento_conico()
    ent_d, ent_h = ENTRADA_CONICA
    for s in (-1, 1):
        # pared del tubo: macizo de Hp a za (con agujero Ø ASIENTO_D), asiento cónico, tubo y entrada
        v.pol([(s * ASIENTO_D / 2, Hp), (s * re_, Hp), (s * re_, TUBO["alto"]), (s * ent_d / 2, TUBO["alto"]),
               (s * ri, TUBO["alto"] - ent_h), (s * ri, za + ha), (s * ASIENTO_D / 2, za)],
              relleno="#d7ccc8", trazo="#000000", grosor=0.3)
    # antorcha en su sitio
    zp = z_punta_en_soporte()
    lc = largo_cuerpo_antorcha()
    r = ANTORCHA_DIAMETRO / 2
    cl, d0 = CONO_PUNTA
    v.pol([(-d0 / 2, zp), (d0 / 2, zp), (r - CHAVETA["plano"], zp + cl), (r - CHAVETA["plano"], zp + lc),
           (-r, zp + lc), (-r, zp + cl)], relleno="#eeeeee", trazo="#000000", grosor=0.35)
    mx = MANGO["x"] / 2
    zm0 = zp + lc
    v.pol([(-mx, zm0), (mx, zm0), (mx, zm0 + MANGO["largo"] - MANGO["chaflan"]),
           (mx - MANGO["chaflan"], zm0 + MANGO["largo"]), (-mx + MANGO["chaflan"], zm0 + MANGO["largo"]),
           (-mx, zm0 + MANGO["largo"] - MANGO["chaflan"])], relleno="#ffe0b2", trazo=NARANJA, grosor=0.35)
    v.circulo((0, zp), 1.6, relleno=VERDE, trazo=None)
    v.linea((r - CHAVETA["plano"], zp + CHAVETA["z0"]), (r - CHAVETA["plano"], zp + lc), trazo=AZUL, grosor=0.5)
    v.texto((r + 1.5, zp + 35), "chaveta (plano de 1 en +X)", tam=2.2, color=AZUL)
    # dedos (esquema): la punta del dedo apoya en el hombro del mango
    # los dedos aprietan las caras ±Y (delante y detrás del plano del dibujo): su contorno, discontinuo
    v.rect((-8.0, zm0 + 0.3, 8.0, zm0 + 40), trazo="#37474f", grosor=0.2, guiones=(1.2, 0.8))
    v.texto((9.0, zm0 + 36), "dedos (en ±Y)", tam=2.2, color="#37474f")
    zg = z_gripperframe_en_soporte()
    v.linea((-30, zg), (30, zg), trazo=GRIS, grosor=0.2, guiones=(1, 1))
    v.texto((31, zg - 0.8), f"gripperframe Z = {fmt(zg, 1)}", tam=2.3, color=GRIS)
    zmr = z_mango_real()
    v.linea((-30, zmr), (-mx, zmr), trazo=NARANJA, grosor=0.2)
    v.texto((-31, zmr - 0.8), f"centro del mango Z = {fmt(zmr, 1)}", tam=2.3, color=NARANJA, ancla="der")
    zc = c.SOPORTE_ANTORCHA["z_mango"]
    if abs(zc - zmr) > 2:
        v.linea((-W, zc), (W + 20, zc), trazo=ROJO, grosor=0.3, guiones=(2, 1))
        v.texto((W + 21, zc - 0.8), f"z_mango del contrato = {fmt(zc)}", tam=2.3, color=ROJO)
    # cotas
    v.cota((-W, 0), (W, 0), -7, fmt(PIE_SOPORTE[0]))
    v.cota((-W, 0), (-W, Hp), 5, fmt(Hp), tam=2.2)
    v.cota((-re_, 0), (-re_, TUBO["alto"]), 6, fmt(TUBO["alto"]))
    v.cota((-ent_d / 2, TUBO["alto"]), (ent_d / 2, TUBO["alto"]), 4, f"Ø{fmt(ent_d)}", tam=2.2)
    v.cota((re_, za), (re_, zp), -5, "", tam=2.2)
    v.texto((re_ + 7, (za + zp) / 2 - 1), f"asiento Ø{fmt(ASIENTO_D)} a Z {fmt(za, 1)}; punta a Z {fmt(zp, 1)}",
            tam=2.2)
    v.cota((mx, zm0), (mx, zm0 + MANGO["largo"]), -4, fmt(MANGO["largo"]), tam=2.2)
    v.cota((-r, zp), (-r, zm0), 32, f"{fmt(lc, 1)} (LED → hombro)", tam=2.2)
    # sección del mango (vista superior XY)
    vm = gh.Vista(lz, 3.0, (230, 70))
    vm.rect((-mx, -MANGO["y"] / 2, mx, MANGO["y"] / 2), relleno="#ffe0b2", trazo=NARANJA, grosor=0.35)
    vm.circulo((0, 0), r, trazo=GRIS, grosor=0.2, guiones=(1, 0.6))
    for s in (-1, 1):
        vm.rect((-8, s * MANGO["y"] / 2, 8, s * (MANGO["y"] / 2 + 6)), relleno="#cfd8dc", trazo="#37474f", grosor=0.2)
        vm.flecha((0, s * (MANGO["y"] / 2 + 10)), (0, s * (MANGO["y"] / 2 + 6.3)), color="#37474f", grosor=0.3)
    vm.cota((-mx, -MANGO["y"] / 2), (mx, -MANGO["y"] / 2), -14, fmt(MANGO["x"]))
    vm.cota((mx, -MANGO["y"] / 2), (mx, MANGO["y"] / 2), -4, fmt(MANGO["y"]))
    vm.texto((0, MANGO["y"] / 2 + 13), "sección del mango y dedos", tam=2.6, negrita=True, ancla="centro")
    vm.texto((mx + 1, 1), "+X", tam=2.4)
    gh.cuadro_titulo(lz, "ANTORCHA-ROBOT-V2 en SOPORTE-ANTORCHA-V2 (sección XZ, Z sobre el tablero)", [
        f"Antorcha Ø{fmt(ANTORCHA_DIAMETRO)}, cono de la punta {fmt(CONO_PUNTA[0])} (Ø{fmt(CONO_PUNTA[1])} → "
        f"Ø{fmt(ANTORCHA_DIAMETRO)}); mango {fmt(MANGO['x'])} × {fmt(MANGO['y'])} × {fmt(MANGO['largo'])} con caras "
        f"planas en ±Y; el cono apoya en el asiento (no el LED).",
        f"Soporte: pie {fmt(PIE_SOPORTE[0])} × {fmt(PIE_SOPORTE[1])} × {fmt(PIE_SOPORTE[2])}, tubo Ø{fmt(TUBO['exterior'])}"
        f"/Ø{fmt(TUBO['interior'])} hasta Z {fmt(TUBO['alto'])}, entrada cónica y plano interior para la chaveta."])
    return lz


def plano_mesa() -> gh.Lienzo:
    (tx0, tx1), (ty0, ty1) = dims_tablero()
    ancho = 255.0
    e = min(ancho / (ty1 - ty0), 165.0 / (tx1 - tx0))
    lz = gh.Lienzo(285, (tx1 - tx0) * e + 50)
    v = gh.Vista(lz, e, (15 + ty1 * e, 40 + tx1 * e), giro_pagina=90)
    v.rect((tx0, ty0, tx1, ty1), relleno="#fafafa", trazo="#8d6e63", grosor=0.3)
    v.rect((gh.BASE_ROBOT_X[0], gh.BASE_ROBOT_Y[0], gh.BASE_ROBOT_X[1], gh.BASE_ROBOT_Y[1]), relleno="#cfd8dc",
           trazo="#37474f", grosor=0.3)
    v.pol(gh.base_robot(gh.MARGEN_ROBOT), trazo="#37474f", grosor=0.15, guiones=(1, 1))
    v.texto((gh.BASE_ROBOT_X[0] + 10, 0), "SO-101", tam=2.6, ancla="centro")
    v.pol(barrido_total(), relleno="#fff3e0", trazo=NARANJA, grosor=0.25, guiones=(2, 1))
    v.pol(barrido_total(zona_propuesta()), trazo=VERDE, grosor=0.3, guiones=(2, 1))
    v.pol(zona_libre_rect(), relleno="#ffe0b2", trazo=NARANJA, grosor=0.4)
    v.pol(zona_libre_rect(zona_propuesta()), trazo=VERDE, grosor=0.4)
    for g in (c.ZONA_LIBRE["giro"][0], 0.0, c.ZONA_LIBRE["giro"][1]):
        cx, cy = sum(c.ZONA_LIBRE["x"]) / 2, sum(c.ZONA_LIBRE["y"]) / 2
        v.pol([(cx + p[0], cy + p[1]) for p in huella_tumbada(g)], trazo=AZUL, grosor=0.15, guiones=(0.8, 0.6))
    for parte in base_en_mesa():
        v.pol(parte, relleno="#eeeeee", trazo="#000000", grosor=0.35)
    for junta in (T, ESQ):
        p0 = gh.a_mesa(c.POSICION_BASE, -c.LONGITUD_CORDON / 2, c.Y_CORDON[junta])
        p1 = gh.a_mesa(c.POSICION_BASE, c.LONGITUD_CORDON / 2, c.Y_CORDON[junta])
        v.flecha(p0, p1, color=ROJO, grosor=0.4, punta=2)
    ax, ay = gh.a_mesa(c.POSICION_BASE, *c.ARUCO_EN_BASE[:2])
    ex, ey = gh.ejes_anclaje(c.POSICION_BASE)
    gh.dibujar_aruco_mundo(v, c.ID_BASE, (ax, ay), c.LADO_ARUCO_V2, ejes=(tuple(ex), tuple(ey)))
    v.pol(soporte_en_mesa(), relleno="#d7ccc8", trazo="#5d4037", grosor=0.3)
    s = c.SOPORTE_ANTORCHA
    v.circulo((s["x"], s["y"]), TUBO["exterior"] / 2, trazo="#5d4037", grosor=0.3)
    v.flecha((0, 0), (60, 0), color=ROJO, grosor=0.35)
    v.flecha((0, 0), (0, 60), color=VERDE, grosor=0.35)
    v.texto((62, -3), "+X", tam=2.4, color=ROJO)
    v.texto((3, 62), "+Y", tam=2.4, color=VERDE)
    b = c.POSICION_BASE
    v.linea((0, 0), (b.x, 0), trazo=AZUL, grosor=0.15, guiones=(1, 1))
    v.texto((b.x - 22, -6), f"base ({fmt(b.x)}, {fmt(b.y)})", tam=2.4, ancla="centro")
    v.texto((s["x"] - 45, s["y"]), f"soporte ({fmt(s['x'])}, {fmt(s['y'])})", tam=2.4, ancla="centro")
    zx, zy = c.ZONA_LIBRE["x"], c.ZONA_LIBRE["y"]
    v.cota((zx[0], zy[0]), (zx[1], zy[0]), -4, f"x {fmt(zx[0])}–{fmt(zx[1])}", tam=2.2)
    v.cota((zx[0], zy[0]), (zx[0], zy[1]), 4, f"y {fmt(zy[0])} a {fmt(zy[1])}", tam=2.2)
    v.cota((tx0, ty1), (tx1, ty1), 6, f"tablero {fmt(tx1 - tx0)} (X)", tam=2.2)
    v.cota((tx0, ty0), (tx0, ty1), -4, f"{fmt(ty1 - ty0)} (Y)", tam=2.2)
    zp = zona_propuesta()
    gh.cuadro_titulo(lz, "Mesa de montaje v2 (vista superior, marco de la mesa, robot abajo)", [
        "Naranja: zona libre del contrato (dónde puede quedar el centro de la chapa) y lo que barre la chapa tumbada; "
        "azul: chapa a −60°, 0° y +60°.",
        f"Verde: zona propuesta (y {fmt(zp['y'][0])} a {fmt(zp['y'][1])}) que no llega a la base. Rojo: cordones T "
        "y esquina. Las webcams están en el plano camaras_estereo."])
    return lz


def plano_camaras(fov: float, fovs_min: dict[str, float]) -> gh.Lienzo:
    """Vista superior con lo que ve cada webcam sobre la mesa + esquema lateral del soporte."""
    cams = {n: camara(n, fov) for n in c.CAMARAS_ESTEREO}
    pts = [p for cam in cams.values() for p in huella_imagen(cam, 0.0)] + \
          [(cam.pos[0], cam.pos[1]) for cam in cams.values()] + gh.base_robot()
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    x0, x1, y0, y1 = min(xs) - 20, max(xs) + 20, min(ys) - 20, max(ys) + 20
    e = min(170 / (y1 - y0), 150 / (x1 - x0))
    lz = gh.Lienzo(285, max((x1 - x0) * e + 45, 175))
    v = gh.Vista(lz, e, (10 + y1 * e, 38 + x1 * e), giro_pagina=90)
    colores = {"a": AZUL, "b": VERDE}
    for n, cam in cams.items():
        v.pol(huella_imagen(cam, 0.0), relleno=None, trazo=colores.get(n, GRIS), grosor=0.35, guiones=(2, 1))
    v.rect((gh.BASE_ROBOT_X[0], gh.BASE_ROBOT_Y[0], gh.BASE_ROBOT_X[1], gh.BASE_ROBOT_Y[1]), relleno="#cfd8dc",
           trazo="#37474f", grosor=0.3)
    v.pol(barrido_total(), relleno="#fff3e0", trazo=NARANJA, grosor=0.25)
    for parte in base_en_mesa():
        v.pol(parte, relleno="#eeeeee", trazo="#000000", grosor=0.3)
    for n, cam in cams.items():
        obj = c.CAMARAS_ESTEREO[n]["objetivo"]
        v.linea((cam.pos[0], cam.pos[1]), (obj[0], obj[1]), trazo=colores.get(n, GRIS), grosor=0.3)
        v.circulo((cam.pos[0], cam.pos[1]), 2.5 / e, relleno="#000000", trazo=None)
        v.texto((cam.pos[0], cam.pos[1] - 6 / e), f"{n.upper()} ({fmt(cam.pos[0], 0)}, {fmt(cam.pos[1], 0)}, "
                                                    f"{fmt(cam.pos[2], 0)})", tam=2.5)
    tx = 190
    lz.texto((tx, 40), f"Huellas con FOV {fmt(fov, 0)}° (16:9)", tam=3.0, negrita=True)
    fila = 46
    for n, p in c.CAMARAS_ESTEREO.items():
        for t in (f"Cámara {n.upper()}: altura {fmt(p['altura'], 0)}, incl. {fmt(p['inclinacion'], 0)}°, "
                  f"azimut {fmt(p['azimut'], 0)}°", f"   FOV mínimo {fmt(fovs_min[n], 1)}°"):
            lz.texto((tx - 5, fila), t, tam=2.4, color=colores.get(n, GRIS))
            fila += 4.2
    # esquema lateral del soporte: cámara inclinada sobre un brazo
    for i, (n, p) in enumerate(c.CAMARAS_ESTEREO.items()):
        vx = gh.Vista(lz, 0.06, (tx + 8 + i * 45, fila + 62))
        vx.linea((0, 0), (0, p["altura"]), trazo="#424242", grosor=0.6)
        vx.linea((0, p["altura"]), (120, p["altura"]), trazo="#424242", grosor=0.6)
        a = math.radians(p["inclinacion"])
        cx, cz = 120, p["altura"]
        vx.linea((cx, cz), (cx + 400 * math.sin(a), cz - 400 * math.cos(a)), trazo=colores.get(n, GRIS), grosor=0.3,
                 guiones=(1, 0.8))
        vx.linea((cx, cz), (cx, cz - 250), trazo=GRIS, grosor=0.15, guiones=(0.6, 0.6))
        vx.rect((cx - 40, cz - 20, cx + 40, cz + 20), relleno="#000000", trazo=None)
        vx.texto((cx + 60, cz - 250), f"{fmt(p['inclinacion'], 0)}°", tam=2.6, color=colores.get(n, GRIS))
        vx.texto((0, -120), f"{n.upper()}: {fmt(p['altura'], 0)} mm", tam=2.5, ancla="centro")
    gh.cuadro_titulo(lz, "Webcams estéreo (vista superior de la mesa y esquema lateral)", [
        "Discontinuo: lo que ve cada webcam sobre la mesa (Z = 0). Naranja: barrido de la chapa tumbada en la zona "
        "libre; gris: base. Robot abajo, +X hacia arriba.",
        "Esquema lateral: brazo o trípode con rosca 1/4\"; inclinación del eje óptico respecto a la vertical."])
    return lz


def plano_prueba() -> gh.Lienzo:
    lz = gh.Lienzo(285, 165)
    v = gh.Vista(lz, 1.6, (20, 118))
    L, A, G = PRUEBA_BLOQUE
    v.rect((0, 0, L, A), relleno="#eeeeee", trazo="#000000", grosor=0.35)
    xs = (L / 2 - 23, L / 2, L / 2 + 23)
    for x, d in zip(xs, c.AGUJEROS_IMAN_PRUEBA):
        v.circulo((x, 8.0), d / 2, relleno="#ffffff", trazo="#000000", grosor=0.25)
        v.texto((x, 1.2), fmt(d, 1), tam=2.6, ancla="centro")
    for x, d in zip(xs, AGUJEROS_IMAN_MOVIL_PRUEBA):
        v.circulo((x, 18.5), d / 2, relleno="#ffffff", trazo="#000000", grosor=0.25)
        v.texto((x + 6, 17.5), fmt(d, 1), tam=2.4, ancla="centro")
    yr = 30.0
    v.rect((0, yr - c.GUIA_T["ancho"] / 2 - CHAFLAN_RANURA, L, yr + c.GUIA_T["ancho"] / 2 + CHAFLAN_RANURA),
           relleno="#e0e0e0", trazo=GRIS, grosor=0.15)
    v.rect((0, yr - c.GUIA_T["ancho"] / 2, L, yr + c.GUIA_T["ancho"] / 2), relleno="#bdbdbd", trazo="#000000",
           grosor=0.25)
    for x, polo in zip(X_IMANES_PRUEBA, ("N", "S")):
        v.circulo((L / 2 + x, yr), AGUJERO_IMAN_BASE / 2, trazo="#424242", grosor=0.2, guiones=(1, 0.6))
        _texto_polo(v, (L / 2 + x, yr), polo, ROJO if polo == "N" else AZUL)
    v.cota((0, 0), (L, 0), -6, fmt(L))
    v.cota((L, 0), (L, A), -5, fmt(A))
    v.texto((0, -13), f"Bloque {fmt(L)} × {fmt(A)} × {fmt(G)}. Fila 1: Ø{', '.join(fmt(d, 1) for d in c.AGUJEROS_IMAN_PRUEBA)}"
                      f" × {fmt(PROF_IMAN_BASE[T])} (base); fila 2: Ø"
                      f"{', '.join(fmt(d, 1) for d in AGUJEROS_IMAN_MOVIL_PRUEBA)} × {fmt(AGUJERO_IMAN_MOVIL[1])} (chapa).",
           tam=2.5)
    v.texto((0, -17.5), f"Ranura {fmt(c.GUIA_T['ancho'])} × {fmt(c.GUIA_T['profundo'])} con chaflán {fmt(CHAFLAN_RANURA)} "
                        f"y 2 imanes Ø{fmt(c.IMAN_DIAMETRO)} desde abajo (piel {fmt(piel_iman_base(T))}) en X = ±15: "
                        "N y S hacia arriba.", tam=2.5)
    # tramo de chapa de prueba (alzado de la cara de la aleta, en espejo)
    vc = VistaEspejo(lz, 1.4, (222, 105))
    Lc = PRUEBA_CHAPA_LARGO / 2
    vc.rect((-Lc, 0, Lc, c.ALTO_MOVIL), relleno="#f5f5f5", trazo="#000000", grosor=0.35)
    a = c.ALETA
    vc.rect((-a["largo"] / 2, Z_ALETA - a["grosor"] / 2, a["largo"] / 2, Z_ALETA + a["grosor"] / 2),
            relleno="#90caf9", trazo=AZUL, grosor=0.3)
    for x, polo in zip(X_IMANES_PRUEBA, ("S", "N")):
        d, pr = AGUJERO_IMAN_MOVIL
        vc.rect((x - d / 2, 0, x + d / 2, pr), relleno="#ffffff", trazo="#424242", grosor=0.2)
        vc.texto((x, pr + 1.2), f"{polo}↓", tam=2.4, negrita=True, color=ROJO if polo == "N" else AZUL, ancla="centro")
    vc.cota((Lc, 0), (-Lc, 0), 6, fmt(PRUEBA_CHAPA_LARGO))
    vc.texto((0, c.ALTO_MOVIL + 3), "tramo de chapa de prueba (cara de la aleta)", tam=2.6, negrita=True, ancla="centro")
    vc.texto((0, -12), f"{fmt(PRUEBA_CHAPA_LARGO)} × {fmt(c.GROSOR_CHAPA)} × {fmt(c.ALTO_MOVIL)}, aleta completa, "
                       f"2 imanes Ø{fmt(IMAN_MOVIL[0])}×{fmt(IMAN_MOVIL[1])} en X = ±15.", tam=2.4, ancla="centro")
    gh.cuadro_titulo(lz, "Pieza de prueba v2 (imprimir PRIMERO): imanes, ranura, polaridad y aleta", [
        "1) Diámetros de los imanes a presión. 2) La chapa entra en la ranura y se centra sola dejándola caer desde "
        "±5 mm. 3) Girada 180° se repele.",
        "4) Con el SO-101: la pinza abierta abraza la aleta con holgura, cerrada la sujeta y la chapa no gira al "
        "levantarla. 5) Distancia a la que la chapa salta sola."])
    return lz


# =================================================================================================================
# ArUco v2
# =================================================================================================================
def etiqueta_v2(id_aruco: int) -> str:
    if id_aruco == c.ID_BASE:
        return f"id {id_aruco} · base"
    for cara, i in c.IDS_MOVIL.items():
        if id_aruco == i:
            return f"id {id_aruco} · móvil, {'cara aleta' if cara == 'cara_aleta' else 'cara lisa'}"
    rep = repuestos()
    if id_aruco in rep:
        return f"id {id_aruco} · repuesto ({'aleta' if rep[id_aruco] == 'cara_aleta' else 'lisa'})"
    return f"id {id_aruco}"


def repuestos() -> dict[int, str]:
    """Ids de repuesto 42-45: pares (cara aleta, cara lisa) para una segunda y tercera chapa móvil."""
    base = max(c.IDS_MOVIL.values()) + 1
    return {base + i: ("cara_aleta" if i % 2 == 0 else "cara_lisa") for i in range(4)}


def ids_unicos() -> list[int]:
    return [c.ID_BASE, c.IDS_MOVIL["cara_aleta"], c.IDS_MOVIL["cara_lisa"], *sorted(repuestos())]


def ids_hoja() -> list[int]:
    """Hoja A4: base y las dos caras de la móvil por duplicado (dos puestos de grabación) y los repuestos."""
    trio = [c.ID_BASE, c.IDS_MOVIL["cara_aleta"], c.IDS_MOVIL["cara_lisa"]]
    return trio + trio + sorted(repuestos())


def nombre_png_v2(id_aruco: int) -> str:
    e = etiqueta_v2(id_aruco).split("· ")[1]
    e = e.replace("móvil, cara ", "movil_").replace("repuesto (", "repuesto_").replace(")", "")
    return f"aruco_{id_aruco:02d}_{e.replace(' ', '_')}.png"


def hoja_marcadores_v2() -> gh.Lienzo:
    lz = gh.Lienzo(*gh.A4)
    lado = c.LADO_ARUCO_V2
    lz.texto((12, 14), "LeWelder v2 · ArUco de la base y de la chapa móvil", tam=4.6, negrita=True)
    lz.texto((12, 20), f"{c.DICCIONARIO_ARUCO} · lado {fmt(lado)} mm (solo la parte negra) · margen blanco "
                       f"{fmt(gh.MARGEN_BLANCO)} mm incluido en el recorte ({fmt(gh.lado_con_margen(lado))} × "
                       f"{fmt(gh.lado_con_margen(lado))}, hueco {fmt(REBAJE_ARUCO[0])}).", tam=2.7)
    lz.texto((12, 24.5), "Imprimir a escala 100 % ('tamaño real'), papel adhesivo mate. Recorta por la línea gris.",
             tam=2.7)
    lz.texto((12, 29), "Base: +X del marcador a lo largo de la base (+X), el texto hacia +Y. Chapa: pégalo leyendo "
                       "derecho al mirar la cara, con el canto que apoya abajo.", tam=2.7)
    gh.regla(lz, 12, 33)
    lb = gh.lado_con_margen(lado)
    m = gh.MARGEN_BLANCO
    cols, celda_w, celda_h = 4, 46.0, 50.0
    x_ini = (gh.A4[0] - cols * celda_w) / 2 + (celda_w - lb) / 2
    for i, id_aruco in enumerate(ids_hoja()):
        f, col = divmod(i, cols)
        x = x_ini + col * celda_w
        y = 50.0 + f * celda_h
        lz.texto((x, y + 3.2), etiqueta_v2(id_aruco), tam=2.8, negrita=True)
        lz.texto((x + lb, y + 7.2), "+X →", tam=2.8, ancla="der", color=ROJO)
        yc = y + 9.0
        lz.rect(x, yc, lb, lb, trazo="#9e9e9e", grosor=0.15, guiones=(1.2, 0.8))
        gh.dibujar_aruco_pagina(lz, id_aruco, x + m, yc + m, lado)
    return lz


def verificar_aruco(salida: Path) -> tuple[list[str], dict]:
    aruco = salida / "aruco"
    lineas, detalle = [], {}
    tol = 0.15
    lado = c.LADO_ARUCO_V2
    img, ppp = gh.leer_gris(aruco / "hoja_v2.png")
    det = gh.detectar_aruco(img, ppp)
    ok = set(det) == set(ids_unicos()) and all(abs(v - lado) < tol for v in det.values())
    detalle["hoja_v2.png"] = {"ids": det, "ok": ok, "ppp": ppp}
    lados = list(det.values()) or [float("nan")]
    lineas.append(f"`hoja_v2.png` ({fmt(ppp, 0)} ppp): {len(det)} ids detectados de {len(ids_unicos())} esperados, "
                  f"lado {fmt(min(lados), 2)}–{fmt(max(lados), 2)} mm (contrato {fmt(lado)}) → {'OK' if ok else 'FALLA'}")
    sueltos_ok = True
    for id_aruco in ids_unicos():
        img, ppp = gh.leer_gris(aruco / nombre_png_v2(id_aruco))
        img = cv2.copyMakeBorder(img, 60, 60, 60, 60, cv2.BORDER_CONSTANT, value=255)
        d = gh.detectar_aruco(img, ppp)
        ok_s = list(d) == [id_aruco] and abs(d[id_aruco] - lado) < tol
        sueltos_ok &= ok_s
        detalle[nombre_png_v2(id_aruco)] = {"ids": d, "ok": ok_s, "ppp": ppp}
    lineas.append(f"PNG sueltos ({len(ids_unicos())}): "
                  f"{'todos con su id y lado correctos' if sueltos_ok else 'ALGUNO FALLA'}")
    paginas = gh.rasterizar_pdf(aruco / "marcadores_v2_a4.pdf")
    if paginas is None:
        lineas.append("`marcadores_v2_a4.pdf`: no verificado (falta `pdftoppm`)")
        detalle["marcadores_v2_a4.pdf"] = None
    else:
        d = gh.detectar_aruco(paginas[0], gh.PPP)
        ok_p = len(paginas) == 1 and set(d) == set(ids_unicos()) and all(abs(x - lado) < tol for x in d.values())
        detalle["marcadores_v2_a4.pdf"] = {"ok": ok_p, "ids": d}
        lados = list(d.values()) or [float("nan")]
        lineas.append(f"`marcadores_v2_a4.pdf` rasterizado a {gh.PPP} ppp con pdftoppm: {len(d)} ids, lado "
                      f"{fmt(min(lados), 2)}–{fmt(max(lados), 2)} mm → {'OK' if ok_p else 'FALLA'}")
    return lineas, detalle


# =================================================================================================================
# Documentos
# =================================================================================================================
def _r(r) -> str:
    return f"X {fmt(r[0])} a {fmt(r[2])}, Y/Z {fmt(r[1])} a {fmt(r[3])}"


def avisos_v2(probs: list[Problema], fov_min: dict[str, float], vistas: dict) -> list[str]:
    av = []
    zc, zr = c.SOPORTE_ANTORCHA["z_mango"], z_mango_real()
    if abs(zc - zr) > 2:
        av.append(f"**`SOPORTE_ANTORCHA['z_mango']` = {fmt(zc)} no es posible.** La antorcha mide "
                  f"{fmt(largo_cuerpo_antorcha() + MANGO['largo'], 1)} mm de la punta al final del mango y se guarda "
                  f"de pie con la punta abajo: con la punta {fmt(HOLGURA_PUNTA)} mm sobre el pie, el centro del mango "
                  f"queda a **Z ≈ {fmt(zr, 1)}** y `gripperframe` a Z ≈ {fmt(z_gripperframe_en_soporte(), 1)}. Con "
                  f"{fmt(zc)} la punta quedaría {fmt(zr - zc, 0)} mm bajo el tablero. **Propuesta: `z_mango` = "
                  f"{fmt(round(zr))}** en el contrato (la simulación debe usar esa altura). El brief se ha corregido.")
    if probs:
        zp = zona_propuesta()
        av.append("**Zona libre**: " + "; ".join(p.texto for p in probs) + f". La zona del contrato es dónde puede "
                  f"quedar el **centro** de la chapa (una chapa de {fmt(c.LARGO_MOVIL)} no cabe entera en "
                  f"{fmt(c.ZONA_LIBRE['x'][1] - c.ZONA_LIBRE['x'][0])} × "
                  f"{fmt(c.ZONA_LIBRE['y'][1] - c.ZONA_LIBRE['y'][0])}). **Propuesta: `ZONA_LIBRE['y']` = "
                  f"({fmt(zp['y'][0])}, {fmt(zp['y'][1])})** (mismo x y giro): la chapa queda a ≥ "
                  f"{fmt(MARGEN_ZONA, 0)} mm de la base (sección 8).")
    av.append(f"**Imanes de la chapa móvil Ø{fmt(IMAN_MOVIL[0])} × {fmt(IMAN_MOVIL[1])}** (no Ø{fmt(c.IMAN_DIAMETRO)} "
              f"× {fmt(c.IMAN_ALTO)}): un Ø{fmt(c.IMAN_DIAMETRO)} no cabe en el canto de una chapa de "
              f"{fmt(c.GROSOR_CHAPA)}. Propuesta: añadir `IMAN_MOVIL = ({fmt(IMAN_MOVIL[0])}, {fmt(IMAN_MOVIL[1])})` al "
              "contrato.")
    av.append(f"**Polaridad corregida en el brief**: con todos los imanes iguales (N arriba en la base, S abajo en la "
              f"chapa) la chapa girada 180° (aleta hacia el cordón) también se pega. Ahora la base lleva "
              f"{'/'.join(POLARIDAD_BASE)} hacia arriba y la chapa {'/'.join(POLARIDAD_MOVIL)} hacia abajo "
              f"(X = {', '.join(fmt(x) for x in X_IMANES)}): girada 180° se repele (sección 4).")
    av.append(f"**Tope de la esquina corregido en el brief**: un nervio de Y +{fmt(TOPE_Y[0])} a +{fmt(TOPE_Y[1])} "
              f"solo de Z 0 a +{fmt(c.TOPE_ESQUINA['alto'])} queda fuera de la placa (flotando) y los agujeros de los "
              f"imanes de la esquina (Ø{fmt(AGUJERO_IMAN_BASE)} en Y = {fmt(y_linea(ESQ))}, hasta Y = "
              f"{fmt(y_linea(ESQ) + AGUJERO_IMAN_BASE / 2)}) saldrían por el canto. El tope es macizo de Z = "
              f"−{fmt(c.GROSOR_CHAPA)} (mesa) a +{fmt(c.TOPE_ESQUINA['alto'])}: la base mide "
              f"{fmt(c.ANCHO_BASE + TOPE_Y[1] - TOPE_Y[0])} de ancho en el tramo del tope.")
    av.append(f"**Altura de la chapa en T y en esquina**: en la T el canto entra {fmt(c.GUIA_T['profundo'])} mm en la "
              f"ranura (canto en Z = −{fmt(c.GUIA_T['profundo'])}); en la esquina apoya en la cara (Z = 0). El "
              f"software (tarea 1) y la simulación (tarea 2) deben usar esta diferencia: centro del ArUco 41 a Z = "
              f"{fmt(z_canto_movil(T) + c.ARUCO_EN_MOVIL[1])} (T) o {fmt(c.ARUCO_EN_MOVIL[1])} (esquina) sobre la "
              f"cara de la base. Propuesta: `Z_CANTO_MOVIL = {{T: −{fmt(c.GUIA_T['profundo'])}, esquina: 0}}` en el "
              "contrato.")
    av.append(f"**Imanes en X = {', '.join(fmt(x) for x in X_IMANES)}** (el brief decía "
              f"{', '.join(fmt(x) for x in X_IMANES_BRIEF)}): en la chapa, el agujero del imán de "
              f"+{fmt(X_IMANES_BRIEF[2])} queda bajo el hueco de la pegatina ArUco (X {fmt(aruco_movil()[0], 1)} a "
              f"{fmt(aruco_movil()[2], 1)}) con {fmt(pared_iman_aruco_movil(X_IMANES_BRIEF), 2)} mm de pared; a "
              f"±{fmt(X_IMANES[2])} la pared es de {fmt(pared_iman_aruco_movil(), 2)} mm. Cambia en la base y en la "
              "chapa a la vez (deben quedar enfrentados). Corregido en el brief.")
    malos = {f"{k} desde {n.upper()}": v for (k, n), v in vistas.items() if k.startswith("41")
             and v[0] > ANGULO_ARUCO_MAX}
    if malos:
        av.append("**El ArUco 41 de la cara lisa se ve muy de lado** desde las webcams (" +
                  ", ".join(f"{k}: {fmt(a, 0)}°" for k, (a, _, _) in sorted(malos.items())) +
                  f" respecto a su normal; más de {fmt(ANGULO_ARUCO_MAX, 0)}° es dudoso). La base (ArUco 30) y la "
                  "chapa tumbada (ArUco 40) se ven bien. Propuesta para la tarea 1: comprobarlo con la cámara "
                  "sintética; si falla, bajar las webcams (inclinación 45-50°) o reconocer la junta con el ArUco 30 "
                  "+ presencia de la chapa en la línea (sección 7).")
    av.append(f"**Antorcha del robot**: el cuerpo pasa de 95 a **{fmt(largo_cuerpo_antorcha(), 1)}** "
              f"(= {fmt(c.LONGITUD_ANTORCHA_ROBOT)} − {fmt(gh.PUNTA_DEDO_SOBRE_GRIPPERFRAME, 1)}): las puntas de los "
              f"dedos apoyan en el hombro del mango (Ø{fmt(ANTORCHA_DIAMETRO)} > {fmt(MANGO['y'])}) y así "
              f"`gripperframe` queda a {fmt(c.LONGITUD_ANTORCHA_ROBOT)} de la punta, como dice el contrato. La "
              f"chaveta empieza en Z = {fmt(CHAVETA['z0'])} para que encaje dentro del tubo del soporte (de Z 60 a 95 "
              "quedaba por encima del tubo). Corregido en el brief.")
    return av


def generar_contrato_md(probs, fovs_min, fov_rec, vistas, verif) -> str:
    av = avisos_v2(probs, fovs_min, vistas)
    a = c.ALETA
    fz = {g: fuerza_chapa(T, dz=g)[2] for g in (5.0, 8.0, 10.0, 12.0, 15.0)}
    peso = masa_chapa() / 1000 * 9.81
    lat = {dy: fuerza_chapa(T, dz=c.GUIA_T["profundo"], dy=dy)[1] for dy in (-5.0, -3.0, 3.0, 5.0)}
    gir = fuerza_chapa(T, dz=5.0, girada=True)[2]
    ok_t = fuerza_chapa(T, dz=5.0)[2]
    zp = zona_propuesta()
    (tx0, tx1), (ty0, ty1) = dims_tablero()
    md = [
        "# Contrato de hardware de LeWelder v2",
        "",
        "> Generado por `herramientas/generar_hardware_v2.py` (`python herramientas/generar_hardware.py --v2`) a partir "
        "de `lewelder/contrato.py` y de las decisiones del brief. **No lo edites a mano.**",
        ">",
        f"> **El documento para modelar en SolidWorks es [`{BRIEF}`]({BRIEF})**: este contrato lo comprueba "
        "(medidas, choques, imanes, cámaras), justifica el diseño y da los planos acotados y la lista de "
        "comprobación.",
        "",
        "Medidas en **mm** y grados. Planos en [`planos/`](planos/) (PNG y SVG a escala). Marcadores en "
        "[`aruco/`](aruco/). Lista de material en [`lista_material.md`](lista_material.md).",
        "",
        "## Avisos (incoherencias y propuestas)",
        "",
        *[f"{i}. {t}" for i, t in enumerate(av, 1)],
        "",
        "## 1. Marcos y convenios",
        "",
        "- **Mesa**: el de la v1 (origen en el centro de la base del robot, X hacia delante, Y a la izquierda, Z arriba; "
        "Z = 0 en el tablero).",
        f"- **Base**: origen en el centro de la cara superior; X a lo largo ({fmt(c.LARGO_BASE)}), Y transversal, Z "
        f"arriba. En la mesa, su centro en ({fmt(c.POSICION_BASE.x)}, {fmt(c.POSICION_BASE.y)}) con giro "
        f"{fmt(c.POSICION_BASE.giro)}: **X base → +Y mesa, +Y base → −X mesa (hacia el robot)**. La cara superior está "
        f"a Z mesa = {fmt(c.GROSOR_CHAPA)}.",
        "- **Chapa móvil**: origen en el centro del canto inferior (el que apoya), X a lo largo, Z = altura de pie, Y = "
        "grosor; cara lisa en −Y (cordón, la ven las webcams), cara de la aleta en +Y (la ve el robot). Montada, sus "
        "ejes son paralelos a los de la base.",
        f"- **Cordón**: T → X −{fmt(c.LONGITUD_CORDON / 2)}…+{fmt(c.LONGITUD_CORDON / 2)} en Y = "
        f"{fmt(c.Y_CORDON[T])}, Z = 0; esquina → mismo X en Y = {fmt(c.Y_CORDON[ESQ])}, Z = 0 (marco de la base).",
        "",
        "Orientación de cada ArUco (para la tarea 1):",
        "",
        tabla(["id", "dónde", "centro", "+X del marcador", "arriba del marcador", "normal (sale de la cara)"], [
            [c.ID_BASE, "cara superior de la base", f"({', '.join(fmt(x) for x in c.ARUCO_EN_BASE)}) base", "+X base",
             "+Y base", "+Z base"],
            [c.IDS_MOVIL["cara_lisa"], "cara lisa (−Y) de la móvil", f"X {fmt(c.ARUCO_EN_MOVIL[0])}, Z "
             f"{fmt(c.ARUCO_EN_MOVIL[1])} (chapa)", "+X chapa", "+Z chapa", "−Y chapa"],
            [c.IDS_MOVIL["cara_aleta"], "cara de la aleta (+Y)", f"X {fmt(c.ARUCO_EN_MOVIL[0])}, Z "
             f"{fmt(c.ARUCO_EN_MOVIL[1])} (chapa)", "**−X chapa**", "+Z chapa", "+Y chapa"],
            [", ".join(str(i) for i in sorted(repuestos())), "repuestos", "igual que 40 (pares) y 41 (impares)", "", "",
             ""],
        ]),
        "",
        "En las dos caras el marcador se pega **leyendo derecho al mirar la cara, con el canto que apoya abajo**; por "
        "eso el +X del 40 va hacia −X de la chapa. Tumbada (cara lisa abajo, aleta arriba) se ve el 40; montada, las "
        "webcams ven el 41.",
        "",
        "## 2. Base fija (BASE-V2)",
        "",
        "![Base, vista superior](planos/base_v2_superior.png)",
        "",
        tabla(["Elemento", "Medida", "Por qué"], [
            ["Placa", f"{fmt(c.LARGO_BASE)} × {fmt(c.ANCHO_BASE)} × {fmt(c.GROSOR_CHAPA)}, chaflán "
                      f"{fmt(CHAFLAN_BASE_ABAJO)} abajo", "contrato; el chaflán evita la pata de elefante"],
            ["Ranura de la T", f"{_r(ranura_t())}; ancho {fmt(c.GUIA_T['ancho'])}, prof. {fmt(c.GUIA_T['profundo'])}, "
                               f"chaflán {fmt(CHAFLAN_RANURA)} × 45° en las dos aristas",
             f"chapa de {fmt(c.GROSOR_CHAPA)} con {fmt((c.GUIA_T['ancho'] - c.GROSOR_CHAPA) / 2)} de holgura por lado; "
             f"captura geométrica ±{fmt((c.GUIA_T['ancho'] - c.GROSOR_CHAPA) / 2 + CHAFLAN_RANURA + CHAFLAN_MOVIL)} "
             f"(holgura + chaflán de la ranura + chaflán de la chapa); los imanes hacen el resto hasta ±5"],
            ["Tope de la esquina", f"nervio X {fmt(X_GUIAS[0])} a {fmt(X_GUIAS[1])}, Y +{fmt(TOPE_Y[0])} a "
                                   f"+{fmt(TOPE_Y[1])}, **macizo de Z −{fmt(c.GROSOR_CHAPA)} a "
                                   f"+{fmt(c.TOPE_ESQUINA['alto'])}**, chaflán {fmt(CHAFLAN_TOPE)} × 45° arriba por "
                                   "dentro",
             "para la chapa por fuera (un error hacia +Y no la tira de la base); el chaflán la guía; la cara exterior "
             "de la chapa queda enrasada con el canto"],
            ["Imanes", f"Ø{fmt(c.IMAN_DIAMETRO)} × {fmt(c.IMAN_ALTO)} N52, agujeros Ø{fmt(AGUJERO_IMAN_BASE)} desde "
                       f"abajo en X = {', '.join(fmt(x) for x in X_IMANES)}; línea T en Y = {fmt(y_linea(T))} "
                       f"(prof. {fmt(PROF_IMAN_BASE[T])}), esquina en Y = {fmt(y_linea(ESQ))} (prof. "
                       f"{fmt(PROF_IMAN_BASE[ESQ])})",
             f"coaxiales con los de la chapa colocada; piel {fmt(piel_iman_base(T))} (T) y {fmt(piel_iman_base(ESQ))} "
             "(esquina): la chapa apoya en plástico, no en imán"],
            ["Polaridad (cara de arriba)", " / ".join(f"X {fmt(x)}: {p}" for x, p in zip(X_IMANES, POLARIDAD_BASE)),
             "asimétrica: la chapa girada 180° se repele (sección 4)"],
            ["Hueco del ArUco 30", f"{fmt(REBAJE_ARUCO[0])} × {fmt(REBAJE_ARUCO[0])} × {fmt(REBAJE_ARUCO[1])} en "
                                   f"({fmt(c.ARUCO_EN_BASE[0])}, {fmt(c.ARUCO_EN_BASE[1])})",
             f"pegatina de {fmt(gh.lado_con_margen(c.LADO_ARUCO_V2))} siempre en su sitio; queda a "
             f"{fmt(ranura_t_con_chaflan()[1] - aruco_base()[3], 1)} mm del chaflán de la ranura y fuera de las dos "
             "chapas y cordones"],
            ["Tacos de goma", f"4 rebajes Ø{fmt(PATA_DIAMETRO)} × 1 abajo en "
                              f"{', '.join(gh._pt(p) for p in PATAS)}",
             "la base no se atornilla (el alumno puede girarla); la goma evita que se mueva al montar"],
            ["Masa", f"≈ {fmt(masa_base(), 0)} g", "PLA, 3 perímetros, 20 %"],
        ]),
        "",
        "![Base, sección](planos/base_v2_seccion.png)",
        "",
        "## 3. Chapa móvil (MOVIL-V2)",
        "",
        "![Chapa móvil](planos/movil_v2.png)",
        "",
        tabla(["Elemento", "Medida", "Por qué"], [
            ["Cuerpo", f"{fmt(c.LARGO_MOVIL)} × {fmt(c.GROSOR_CHAPA)} × {fmt(c.ALTO_MOVIL)}, chaflán "
                       f"{fmt(CHAFLAN_MOVIL)}", "contrato; el chaflán del canto ayuda a entrar en la ranura"],
            ["Aleta", f"{fmt(a['largo'])} (X) × {fmt(a['alto'])} (sobresale en +Y) × {fmt(a['grosor'])} (Z), centro "
                      f"X = {fmt(a['x'])}, Z = {fmt(Z_ALETA)}; chaflán {fmt(CHAFLAN_ALETA)} × 45° en el extremo, R"
                      f"{fmt(RADIO_RAIZ_ALETA)} en la raíz",
             "ver sección 5 (pinza)"],
            ["Imanes del canto", f"Ø{fmt(IMAN_MOVIL[0])} × {fmt(IMAN_MOVIL[1])} N52 en agujeros "
                                 f"Ø{fmt(AGUJERO_IMAN_MOVIL[0])} × {fmt(AGUJERO_IMAN_MOVIL[1])} en X = "
                                 f"{', '.join(fmt(x) for x in X_IMANES)}, Y = 0",
             f"pared de {fmt(pared_iman_movil(), 2)} a cada lado; el imán queda "
             f"{fmt(AGUJERO_IMAN_MOVIL[1] - IMAN_MOVIL[1], 1)} dentro"],
            ["Polaridad (cara de abajo)", " / ".join(f"X {fmt(x)}: {p}" for x, p in zip(X_IMANES, POLARIDAD_MOVIL)),
             "atrae a la base solo en la orientación buena"],
            ["Huecos ArUco 41 (cara lisa) y 40 (aleta)", f"{fmt(REBAJE_ARUCO[0])} × {fmt(REBAJE_ARUCO[0])} × "
                                                        f"{fmt(REBAJE_ARUCO[1])} centrados en X = "
                                                        f"{fmt(c.ARUCO_EN_MOVIL[0])}, Z = {fmt(c.ARUCO_EN_MOVIL[1])}",
             f"lejos de la aleta ({fmt(aruco_movil()[0] - aleta_rect()[2], 1)} mm entre bordes); su borde inferior queda "
             f"a {fmt(aruco_movil()[1] + z_canto_movil(T), 1)} mm sobre la cara de la base en la T: no pisa el cordón"],
            ["Impresión", f"tumbada sobre la cara lisa, aleta arriba, sin soportes; 100 % de relleno en los "
                          f"{fmt(RELLENO_MACIZO_MOVIL)} mm inferiores", "los imanes no se arrancan"],
            ["Masa", f"≈ {fmt(masa_chapa(), 0)} g (peso {fmt(peso, 2)} N)", ""],
        ]),
        "",
        "## 4. Imanes: fuerza y polaridad",
        "",
        f"Estimación con dipolos (N52, Br = {fmt(BR_N52)} T; orientativa, ±50 %). Imanes de la base "
        f"Ø{fmt(c.IMAN_DIAMETRO)}×{fmt(c.IMAN_ALTO)}, de la chapa Ø{fmt(IMAN_MOVIL[0])}×{fmt(IMAN_MOVIL[1])}, 3 + 3, "
        "en la T. Negativo = tira de la chapa hacia la base. A menos de ~5 mm el modelo de dipolos exagera mucho: "
        "en contacto, cuenta con 1-2 N por pareja (catálogo de un Ø4 × 4 N52); lo de verdad se mide con la pieza "
        "de prueba.",
        "",
        tabla(["Canto de la chapa sobre su asiento", "Fuerza vertical", "× peso de la chapa"],
              [[f"{fmt(g)} mm", f"{fmt(f, 2)} N", fmt(-f / peso, 1)] for g, f in fz.items()]),
        "",
        "- **Tiran desde ~10 mm**: a esa altura la atracción ya es del orden del peso de la chapa; a 5 mm la "
        "arrastra con varias veces su peso. El robot solo tiene que soltarla cerca y alineada.",
        "- **Centrado lateral** (chapa apoyada en la cara de la base, desplazada respecto a la ranura; fuerza en Y, "
        "el valor exagera pero el sentido vale): " +
        ", ".join(f"{fmt(dy, 0)} mm → {fmt(f, 1)} N" for dy, f in lat.items()) +
        " (signo contrario al desplazamiento = la lleva hacia la ranura).",
        f"- **Polaridad que impide montarla al revés**: a 5 mm, en la orientación buena "
        f"{fmt(ok_t, 2)} N (atrae); **girada 180° {fmt(gir, 2)} N (repele)**. Volcada (canto de arriba abajo) no hay "
        "imanes que atraigan y la aleta queda a otra altura.",
        "- **Montaje de los imanes**: marca la cara N de cada imán con rotulador usando un imán de referencia (o una "
        "brújula: el norte de la aguja apunta al polo S). Antes de pegar, comprueba la pieza girada 180°: debe "
        "repeler. Una gota de cianoacrilato en el fondo de cada agujero.",
        "",
        "## 5. Diseño para que el robot lo consiga",
        "",
        tabla(["Decisión", "Cómo ayuda al robot"], [
            ["Aleta de " + fmt(a["grosor"]) + " mm de grueso y " + fmt(a["largo"]) + " de largo",
             f"la pinza abierta a 0,2 rad deja {fmt(APERTURA_PUNTA[1][1], 0)} mm entre las puntas (±"
             f"{fmt((APERTURA_PUNTA[1][1] - a['grosor']) / 2, 0)} de error) y cerrada la aprieta; los dedos miden "
             f"{fmt(min(d[1] for d in gh.DEDOS), 0)}-{fmt(max(d[1] for d in gh.DEDOS), 0)} de ancho: ±"
             f"{fmt((a['largo'] - max(d[1] for d in gh.DEDOS[:3])) / 2, 0)} mm de error a lo largo de la aleta"],
            [f"Chaflanes de entrada de {fmt(CHAFLAN_ALETA)} en el extremo de la aleta",
             "si la pinza baja descentrada, el dedo resbala por el chaflán en vez de chocar con la arista"],
            [f"Aleta de {fmt(a['alto'])} mm de alto",
             "la pinza la coge con la punta de los dedos sin tocar la chapa; tumbada, la aleta queda arriba siempre "
             "(la chapa no puede quedar boca abajo)"],
            [f"Aleta a media altura (Z = {fmt(Z_ALETA)})",
             f"con la chapa de pie el dedo de abajo queda a {fmt(holgura_dedo_inferior(T), 1)} mm de la base (T) y a "
             f"{fmt(holgura_dedo_inferior(ESQ), 1)} mm del tope (esquina); colgada de la aleta, la chapa no gira"],
            ["Ranura con chaflanes y tope con chaflán",
             f"corrigen ±{fmt((c.GUIA_T['ancho'] - c.GROSOR_CHAPA) / 2 + CHAFLAN_RANURA + CHAFLAN_MOVIL)} mm por "
             "geometría; en la esquina el tope impide pasarse hacia fuera"],
            ["Imanes que tiran desde ~10 mm y centran", "corrigen el resto hasta ±5 mm y cierran la junta sin apretar"],
            ["Polaridad asimétrica", "la chapa solo encaja en la orientación buena: el fallo es visible y no se monta "
                                     "mal"],
            ["Zona libre con tapete antideslizante (silicona o EVA)",
             "al cerrar la pinza los dedos empujan la aleta: sin tapete la chapa resbala antes de quedar sujeta"],
            ["Mango plano 20 × 12 con hombro y chaveta",
             "la pinza aprieta caras planas (no gira), las puntas de los dedos apoyan en el hombro (siempre a la "
             "misma altura) y la chaveta fija el giro en el soporte"],
            ["Entrada cónica del soporte", "la antorcha cae sola a su sitio al devolverla con un error de "
                                           f"±{fmt((ENTRADA_CONICA[0] - TUBO['interior']) / 2, 1)} mm"],
        ]),
        "",
        "## 6. Antorcha del robot y su soporte",
        "",
        "![Antorcha y soporte](planos/antorcha_soporte_v2.png)",
        "",
        tabla(["Elemento", "Medida"], [
            ["Cuerpo", f"Ø{fmt(ANTORCHA_DIAMETRO)} de Z 0 a **{fmt(largo_cuerpo_antorcha(), 1)}**, cono de la punta Z 0 a "
                       f"{fmt(CONO_PUNTA[0])} (Ø{fmt(CONO_PUNTA[1])} → Ø{fmt(ANTORCHA_DIAMETRO)}, semiángulo "
                       f"{fmt(semiangulo_cono(), 1)}°); LED en Ø{fmt(LED_AGUJERO[0])} × {fmt(LED_AGUJERO[1])}"],
            ["Mango", f"Z {fmt(largo_cuerpo_antorcha(), 1)} a {fmt(largo_cuerpo_antorcha() + MANGO['largo'], 1)}: "
                      f"{fmt(MANGO['x'])} (X) × {fmt(MANGO['y'])} (Y), caras planas en ±Y, chaflán "
                      f"{fmt(MANGO['chaflan'])} arriba"],
            ["Agarre", f"pinza abierta ≥ 0,2 rad ({fmt(APERTURA_PUNTA[1][1], 0)} mm) para entrar; cerrada sobre "
                       f"{fmt(MANGO['y'])}; las puntas de los dedos apoyan en el hombro → `gripperframe` a "
                       f"{fmt(c.LONGITUD_ANTORCHA_ROBOT)} de la punta"],
            ["Chaveta", f"plano de {fmt(CHAVETA['plano'])} en +X de Z {fmt(CHAVETA['z0'])} al mango"],
            ["Soporte", f"pie {fmt(PIE_SOPORTE[0])} × {fmt(PIE_SOPORTE[1])} × {fmt(PIE_SOPORTE[2])} (4 × Ø4,5 en ±27); "
                        f"tubo Ø{fmt(TUBO['exterior'])}/Ø{fmt(TUBO['interior'])} hasta Z {fmt(TUBO['alto'])}; entrada "
                        f"Ø{fmt(ENTRADA_CONICA[0])} → Ø{fmt(TUBO['interior'])} en {fmt(ENTRADA_CONICA[1])}; plano "
                        "interior en +X"],
            ["Asiento", f"cónico, de Ø{fmt(ASIENTO_D)} a Z {fmt(z_asiento(), 1)} a Ø{fmt(TUBO['interior'])} a Z "
                        f"{fmt(z_asiento() + alto_asiento_conico(), 1)} (mismo ángulo que la punta); bajo él, agujero "
                        f"Ø{fmt(ASIENTO_D)} hasta el pie: **el cono apoya, el LED no toca**"],
            ["Alturas con la antorcha dentro", f"punta Z {fmt(z_punta_en_soporte(), 1)}; gripperframe Z "
                                               f"{fmt(z_gripperframe_en_soporte(), 1)}; **centro del mango Z "
                                               f"{fmt(z_mango_real(), 1)}** (contrato: "
                                               f"{fmt(c.SOPORTE_ANTORCHA['z_mango'])}, ver avisos)"],
            ["Posición", f"({fmt(c.SOPORTE_ANTORCHA['x'])}, {fmt(c.SOPORTE_ANTORCHA['y'])}) en la mesa, atornillado "
                         "al tablero; el robot la coge en vertical, desde arriba"],
        ]),
        "",
        "## 7. Webcams estéreo",
        "",
        "![Webcams](planos/camaras_estereo.png)",
        "",
        "Poses del contrato (`CAMARAS_ESTEREO`, mismo convenio que `PoseCamara.por_defecto`). Deben ver la base con "
        "la chapa de pie (T o esquina) y toda la zona que barre la chapa tumbada, con un "
        f"{fmt(100 * gh.MARGEN_IMAGEN, 0)} % de margen en cada borde (16:9).",
        "",
        tabla(["Cámara", "Centro óptico (mesa)", "Distancia al objetivo", "FOV horizontal mínimo"],
              [[n.upper(), f"({', '.join(fmt(float(x), 0) for x in camara(n, 70).pos)})",
                fmt(float(np.linalg.norm(camara(n, 70).pos - np.array(c.CAMARAS_ESTEREO[n]['objetivo']))), 0),
                f"**{fmt(fovs_min[n], 1)}°**"] for n in sorted(c.CAMARAS_ESTEREO)]),
        "",
        tabla(["FOV horizontal"] + [f"¿ve todo {n.upper()}?" for n in sorted(c.CAMARAS_ESTEREO)] +
              [f"mm/px {n.upper()}" for n in sorted(c.CAMARAS_ESTEREO)],
              [[f"{fmt(f, 0)}°"] + ["sí" if fovs_min[n] <= f else "no" for n in sorted(c.CAMARAS_ESTEREO)] +
               [f"{fmt(mm_por_pixel(camara(n, f))[0], 2)}–{fmt(mm_por_pixel(camara(n, f))[1], 2)}"
                for n in sorted(c.CAMARAS_ESTEREO)] for f in FOV_CANDIDATOS]),
        "",
        f"**La 2.ª webcam debe ser igual que la primera y con FOV horizontal ≥ {fmt(max(fovs_min.values()), 1)}°** "
        f"(recomendado {fmt(fov_rec, 0)}° o más, 1080p). Si la primera tiene menos, compra dos iguales.",
        "",
        f"Cómo se ven los ArUco (FOV {fmt(fov_rec, 0)}°; ángulo entre la normal del marcador y la cámara, lado aparente "
        "mayor y menor en píxeles):",
        "",
        tabla(["Marcador"] + [f"cámara {n.upper()}" for n in sorted(c.CAMARAS_ESTEREO)],
              [[k] + [f"{fmt(vistas[(k, n)][0], 0)}°, {fmt(vistas[(k, n)][1], 0)}/{fmt(vistas[(k, n)][2], 0)} px"
                      for n in sorted(c.CAMARAS_ESTEREO)] for k in marcadores_en_mesa()]),
        "",
        "**Soportes**: brazo articulado con pinza de mesa o trípode, con rosca 1/4\" (si hace falta, una pinza "
        "impresa a un tubo de Ø20). Coloca cada cámara con cinta métrica en su centro óptico (±10 mm) y oriéntala "
        "a su objetivo con la inclinación de la tabla (±3°, un nivel con app del móvil vale); el horizonte de la "
        "imagen horizontal. Bloquéala: si se mueve, hay que recalibrar el estéreo con el tablero de "
        "`hardware/aruco/tablero_calibracion_a4.pdf`. Ninguna cámara debe quedar detrás del robot ni del alumno.",
        "",
        "## 8. Mesa de montaje",
        "",
        "![Mesa](planos/mesa_v2.png)",
        "",
        tabla(["Elemento", "Posición (mesa)", "Huella"], [
            ["Base", f"centro ({fmt(c.POSICION_BASE.x)}, {fmt(c.POSICION_BASE.y)}), giro {fmt(c.POSICION_BASE.giro)}",
             "x " + " a ".join(fmt(v) for v in (min(p[0] for q in base_en_mesa() for p in q),
                                              max(p[0] for q in base_en_mesa() for p in q))) +
             ", y " + " a ".join(fmt(v) for v in (min(p[1] for q in base_en_mesa() for p in q),
                                                max(p[1] for q in base_en_mesa() for p in q)))],
            ["Zona libre (centros, contrato)", f"x {fmt(c.ZONA_LIBRE['x'][0])}–{fmt(c.ZONA_LIBRE['x'][1])}, y "
                                               f"{fmt(c.ZONA_LIBRE['y'][0])} a {fmt(c.ZONA_LIBRE['y'][1])}, giro "
                                               f"{fmt(c.ZONA_LIBRE['giro'][0])}° a {fmt(c.ZONA_LIBRE['giro'][1])}°",
             "barrido x " + " a ".join(fmt(f(p[0] for p in barrido_total()), 0) for f in (min, max)) + ", y " +
             " a ".join(fmt(f(p[1] for p in barrido_total()), 0) for f in (min, max))],
            ["Zona libre propuesta", f"y {fmt(zp['y'][0])} a {fmt(zp['y'][1])}",
             "barrido y hasta " + fmt(max(p[1] for p in barrido_total(zp)), 0)],
            ["Soporte de la antorcha", f"({fmt(c.SOPORTE_ANTORCHA['x'])}, {fmt(c.SOPORTE_ANTORCHA['y'])})",
             f"pie {fmt(PIE_SOPORTE[0])} × {fmt(PIE_SOPORTE[1])}"],
            ["Tablero común", f"x {fmt(tx0)} a {fmt(tx1)}, y {fmt(ty0)} a {fmt(ty1)}",
             f"**{fmt(tx1 - tx0)} (X) × {fmt(ty1 - ty0)} (Y)**: robot, base, zona y soporte con 30 mm de margen"],
        ]),
        "",
        "Comprobaciones (polígonos reales; base del robot con " + fmt(gh.MARGEN_ROBOT) + " mm de margen):",
        "",
        *([f"- ⚠ {p.texto}" for p in probs] or ["- Sin choques."]),
        "- La base no invade la base del robot ni el rectángulo de la zona libre; el soporte no toca nada.",
        "",
        "**Tapete de la zona libre**: alfombrilla antideslizante de silicona o goma EVA de 2-3 mm, del tamaño del "
        "barrido de la zona propuesta, pegada al tablero con cinta de doble cara y con el rectángulo de centros "
        "marcado con cinta de carrocero. Color uniforme y mate (no blanco: contraste con las pegatinas).",
        "",
        "## 9. Pieza de prueba (imprimir PRIMERO)",
        "",
        "![Prueba](planos/prueba_v2.png)",
        "",
        f"- **Bloque** {fmt(PRUEBA_BLOQUE[0])} × {fmt(PRUEBA_BLOQUE[1])} × {fmt(PRUEBA_BLOQUE[2])}: agujeros "
        f"Ø{', '.join(fmt(d, 1) for d in c.AGUJEROS_IMAN_PRUEBA)} × {fmt(PROF_IMAN_BASE[T])} (imanes de la base) y "
        f"Ø{', '.join(fmt(d, 1) for d in AGUJEROS_IMAN_MOVIL_PRUEBA)} × {fmt(AGUJERO_IMAN_MOVIL[1])} (imanes de la "
        f"chapa); ranura {fmt(c.GUIA_T['ancho'])} × {fmt(c.GUIA_T['profundo'])} con chaflán {fmt(CHAFLAN_RANURA)} y "
        f"2 imanes Ø{fmt(c.IMAN_DIAMETRO)} desde abajo con {fmt(piel_iman_base(T))} de piel en X = ±15 (N y S hacia "
        "arriba).",
        f"- **Tramo de chapa** {fmt(PRUEBA_CHAPA_LARGO)} × {fmt(c.GROSOR_CHAPA)} × {fmt(c.ALTO_MOVIL)} con la aleta "
        f"completa y 2 imanes Ø{fmt(IMAN_MOVIL[0])}×{fmt(IMAN_MOVIL[1])} (S y N hacia abajo).",
        "- Qué comprobar: los imanes entran a presión con el pulgar y no se caen boca abajo; la chapa entra en la "
        "ranura sin forzar y no baila más de 0,5; soltada desde 5-10 mm de altura y ±5 mm de lado se centra sola; "
        "girada 180° se repele; **con el SO-101 real**: la pinza abierta abraza la aleta y cerrada la levanta sin "
        "que la chapa gire, y el dedo de abajo no toca la ranura al dejarla de pie.",
        "- Elige los diámetros y actualiza el CAD antes de imprimir la base y las chapas.",
        "",
        "## 10. Tolerancias de impresión (PLA)",
        "",
        tabla(["Tema", "Recomendación"], [
            ["Capa / paredes / relleno", "0,2 mm; 3 perímetros; 20 % (chapa móvil: 100 % en los 8 mm inferiores)"],
            ["Agujeros", "salen 0,1-0,3 mm más pequeños: por eso la pieza de prueba"],
            ["Ranura", f"{fmt(c.GUIA_T['ancho'])} para chapa de {fmt(c.GROSOR_CHAPA)}: si la chapa sale gruesa "
                       "(pata de elefante), lija el canto o sube el chaflán"],
            ["Pata de elefante", "compensación 0,15 mm o el chaflán de 0,5 de las aristas de abajo"],
            ["Contracción", "PLA ≈ 0,2-0,3 %: en 200 mm hasta −0,6. Mide la primera base y corrige la escala XY si se "
                            "pasa de ±0,4"],
            ["Orientación", "base y pieza de prueba con la cara inferior en la cama; chapa tumbada sobre la cara lisa; "
                            "antorcha tumbada en dos mitades; soporte de pie"],
            ["Color", "PLA mate gris oscuro o negro (contraste con las pegatinas y el LED, sin reflejos)"],
        ]),
        "",
        "## 11. Lista de comprobación con calibre (±0,3 salvo que se diga)",
        "",
        *[f"- [ ] {t}" for t in [
            "Hoja de marcadores v2: la regla mide 50,0 (±0,3); lado negro de un ArUco 25,0 (±0,2)",
            f"Base: {fmt(c.LARGO_BASE)} × {fmt(c.ANCHO_BASE)} × {fmt(c.GROSOR_CHAPA)}; ancho con el tope "
            f"{fmt(c.ANCHO_BASE + TOPE_Y[1] - TOPE_Y[0])}",
            f"Ranura: ancho {fmt(c.GUIA_T['ancho'])} (±0,2), profundidad {fmt(c.GUIA_T['profundo'])} (±0,2), su eje a "
            f"{fmt(c.ANCHO_BASE / 2 + y_linea(T))} del canto −Y y a {fmt(c.ANCHO_BASE / 2 - y_linea(T))} del canto +Y",
            f"Tope: {fmt(TOPE_Y[1] - TOPE_Y[0])} de grueso, {fmt(c.TOPE_ESQUINA['alto'])} sobre la cara; la chapa "
            "de pie contra el tope queda enrasada con el canto",
            f"Imanes de la base: hundidos en sus agujeros; piel {fmt(piel_iman_base(T))} bajo la ranura (no se "
            "transparenta ni se rompe al apretar con el dedo)",
            f"Chapa: {fmt(c.LARGO_MOVIL)} × {fmt(c.GROSOR_CHAPA)} (±0,15) × {fmt(c.ALTO_MOVIL)}; entra en la ranura "
            "sin forzar",
            f"Aleta: {fmt(a['grosor'])} (±0,2) de grueso, sobresale {fmt(a['alto'])}, centro a "
            f"{fmt(c.LARGO_MOVIL / 2 + a['x'])} del extremo −X y a {fmt(Z_ALETA)} del canto inferior",
            f"Imanes de la chapa: {fmt(AGUJERO_IMAN_MOVIL[1] - IMAN_MOVIL[1], 1)} dentro del canto, polaridad "
            f"{'/'.join(POLARIDAD_MOVIL)} hacia abajo (X {', '.join(fmt(x) for x in X_IMANES)}); la chapa girada "
            "180° se repele",
            f"ArUco pegados: centro de la 30 a ({fmt(c.ARUCO_EN_BASE[0])}, {fmt(c.ARUCO_EN_BASE[1])}); 40 y 41 a "
            f"{fmt(c.LARGO_MOVIL / 2 + c.ARUCO_EN_MOVIL[0])} del extremo −X y {fmt(c.ARUCO_EN_MOVIL[1])} del canto; "
            "el 40 en la cara de la aleta",
            f"Antorcha: {fmt(largo_cuerpo_antorcha(), 1)} de la punta del LED al hombro; mango {fmt(MANGO['x'])} × "
            f"{fmt(MANGO['y'])} (±0,15); entra en el soporte solo con la chaveta en +X",
            f"Soporte: con la antorcha dentro, centro del mango a {fmt(z_mango_real(), 0)} (±2) sobre el tablero; el "
            "LED no toca nada",
            "Webcams: centro óptico a ±10 mm de la tabla de la sección 7 e inclinación a ±3°",
            "Mesa: base, soporte y zona libre a ±2 mm de la sección 8 (medidas desde el centro de la base del robot)",
        ]],
        "",
        "## 12. Marcadores ArUco v2",
        "",
        "- [`aruco/marcadores_v2_a4.pdf`](aruco/marcadores_v2_a4.pdf): ids "
        f"{', '.join(str(i) for i in ids_unicos())} (base y caras de la móvil por duplicado para los dos puestos, y "
        "repuestos 42-45), con su id, la flecha +X y una regla de 50 mm. Vectorial, A4, imprimir al 100 %.",
        f"- `aruco/aruco_XX_*.png`: cada marcador suelto a {gh.PPP} ppp con su margen blanco; `aruco/hoja_v2.png`: "
        "la página en PNG.",
        "",
        "Verificación automática (OpenCV vuelve a leer lo generado):",
        "",
        *[f"- {t}" for t in verif],
        "",
    ]
    return "\n".join(md)


def generar_lista_material(fov_min: float) -> str:
    n_base, n_movil = 2, 3
    imanes_base = 2 * len(X_IMANES) * n_base + len(c.AGUJEROS_IMAN_PRUEBA) + len(X_IMANES_PRUEBA)
    imanes_movil = len(X_IMANES) * n_movil + len(AGUJEROS_IMAN_MOVIL_PRUEBA) + len(X_IMANES_PRUEBA)
    imprimir = [
        ("Pieza de prueba v2: bloque + tramo de chapa", "1", "≈ 25"),
        ("BASE-V2", f"{n_base} (una por puesto; la 2.ª es repuesto)", f"≈ {fmt(masa_base(), 0)} c/u"),
        ("MOVIL-V2 (chapa móvil con aleta)", f"{n_movil} (2 + 1 repuesto)", f"≈ {fmt(masa_chapa(), 0)} c/u"),
        ("ANTORCHA-ROBOT-V2 (dos mitades + pasadores Ø3)", "1 + 1 repuesto", "≈ 20 c/u"),
        ("SOPORTE-ANTORCHA-V2", "1 (+1 para el 2.º puesto si graba «coge la antorcha»)", "≈ 45"),
        ("Pinza de tubo Ø20 con rosca 1/4\" para webcam (solo si el brazo no la trae)", "2", "≈ 15 c/u"),
    ]
    comprar = [
        (f"2.ª webcam **igual que la primera**, 1080p, FOV horizontal ≥ {fmt(fov_min, 1)}°", "1",
         "si la primera no llega, dos nuevas iguales"),
        ("Brazo articulado con pinza de mesa o trípode, rosca 1/4\", que llegue a 750 mm", "2", "uno por webcam"),
        ("Cable alargador USB activo (las webcams quedan a ~0,6 m del robot)", "2", ""),
        (f"Imanes Ø{fmt(c.IMAN_DIAMETRO)} × {fmt(c.IMAN_ALTO)} N52", f"{imanes_base} → pedir "
         f"{int(math.ceil(imanes_base * 1.15 / 10) * 10)}", f"6 por base × {n_base} + prueba"),
        (f"Imanes Ø{fmt(IMAN_MOVIL[0])} × {fmt(IMAN_MOVIL[1])} N52", f"{imanes_movil} → pedir "
         f"{int(math.ceil(imanes_movil * 1.15 / 10) * 10)}", f"3 por chapa × {n_movil} + prueba"),
        ("Tacos de goma adhesivos Ø10 × 1-2 mm", f"{4 * n_base + 4}", "patas de la base"),
        ("Tapete antideslizante de silicona o goma EVA 2-3 mm, ≈ 300 × 300", "1 + 1", "zona libre"),
        ("Papel adhesivo A4 mate", "3 hojas", "marcadores v2"),
        ("LED verde 5 mm alta luminosidad + resistencia 220 Ω", "2 + 2", "antorcha del robot"),
        ("Tornillos 4 × 16 avellanados", "4 + 4", "soporte de la antorcha al tablero"),
        ("Pasadores Ø3 (o filamento de 1,75 cortado)", "4", "mitades de la antorcha"),
        ("Cianoacrilato, rotulador permanente, imán de referencia marcado N o brújula", "—", "polaridad"),
        ("Cinta de carrocero y cinta métrica", "—", "replanteo de la mesa"),
    ]
    zp = zona_propuesta()
    return "\n".join([
        "# Lista de material de LeWelder v2",
        "",
        "> Generada por `herramientas/generar_hardware_v2.py` a partir de `lewelder/contrato.py`. Medidas en "
        f"[contrato.md](contrato.md); modelado en [{BRIEF}]({BRIEF}). La v1 sigue en "
        "[`../lista_material.md`](../lista_material.md).",
        "",
        "## Imprimir",
        "",
        "Masas orientativas (PLA, 3 perímetros, 20 %). ≈ 12 g/h en una impresora clásica, ≈ 30-40 g/h en una rápida.",
        "",
        tabla(["", "Pieza", "Cantidad", "Masa (g)"], [["☐", n, q, m] for n, q, m in imprimir]),
        "",
        "## Comprar o confirmar",
        "",
        tabla(["", "Material", "Cantidad", "Nota"], [["☐", n, q, nota] for n, q, nota in comprar]),
        "",
        "## Orden de impresión (todo listo antes del jueves 19)",
        "",
        "1. **Lun 16, noche — pieza de prueba v2** (bloque + tramo de chapa, ~1 h) e imprimir la hoja "
        "`aruco/marcadores_v2_a4.pdf` (medir la regla). Pedir imanes Ø4 × 4 si no hay.",
        "2. **Mar 17, mañana — probar con el SO-101 real**: diámetros de los imanes, caída en la ranura desde ±5 mm, "
        "polaridad (girada se repele) y agarre de la aleta. Corregir el CAD.",
        "3. **Mar 17, tarde — BASE-V2 n.º 1 y MOVIL-V2 n.º 1** (lo que necesita la grabación de demostraciones). "
        "Comprobar con el calibre (sección 11 del contrato) y montar imanes y pegatinas.",
        "4. **Mar 17, noche — ANTORCHA-ROBOT-V2 y SOPORTE-ANTORCHA-V2**; probar que la pinza la coge y la devuelve.",
        "5. **Mié 18 — MOVIL-V2 n.º 2 y 3, BASE-V2 n.º 2** (segundo puesto de grabación) y soportes de las webcams; "
        f"replantear la mesa (base en (250, 0), zona libre de y {fmt(zp['y'][0])} a {fmt(zp['y'][1])} si se acepta "
        "la propuesta, soporte) y calibrar el estéreo.",
        "6. **Jue 19, mañana — repuestos** (antorcha, chapa) y **tarde — prueba integrada**: montar T y esquina "
        "10 veces a mano y con el robot, y comprobar que la tablet reconoce la junta.",
        "",
    ])


# =================================================================================================================
# Programa principal
# =================================================================================================================
def marcador_suelto(id_aruco: int) -> gh.Lienzo:
    return gh.marcador_suelto(id_aruco, c.LADO_ARUCO_V2)


def generar(salida: Path, verificar: bool = True) -> dict:
    """Genera todo en `salida` (por defecto hardware/v2). Devuelve un resumen para los tests."""
    salida = Path(salida)
    planos, aruco = salida / "planos", salida / "aruco"
    for d in (planos, aruco):
        d.mkdir(parents=True, exist_ok=True)

    probs = comprobar_mesa()
    fovs_min = {n: fov_necesario(camara(n, 70.0)) for n in c.CAMARAS_ESTEREO}
    fov_min = max(fovs_min.values())
    validos = [f for f in FOV_CANDIDATOS if f >= fov_min]
    fov_rec = validos[0] if validos else math.ceil(fov_min)
    vistas = {}
    for k, (centro, normal) in marcadores_en_mesa().items():
        for n in c.CAMARAS_ESTEREO:
            vistas[(k, n)] = vista_marcador(camara(n, fov_rec), centro, normal)
    vistas_41 = {f"{k} desde {n.upper()}": v for (k, n), v in vistas.items() if k.startswith("41")}

    dibujos = {
        "base_v2_superior": plano_base_superior(),
        "base_v2_seccion": plano_base_seccion(),
        "movil_v2": plano_movil(),
        "antorcha_soporte_v2": plano_antorcha_soporte(),
        "camaras_estereo": plano_camaras(fov_rec, fovs_min),
        "mesa_v2": plano_mesa(),
        "prueba_v2": plano_prueba(),
    }
    for nombre, lz in dibujos.items():
        lz.a_png(planos / f"{nombre}.png", 200)
        lz.a_svg(planos / f"{nombre}.svg")

    hoja = hoja_marcadores_v2()
    gh.lienzos_a_pdf([hoja], aruco / "marcadores_v2_a4.pdf")
    hoja.a_png(aruco / "hoja_v2.png", gh.PPP, gris=True)
    for id_aruco in ids_unicos():
        marcador_suelto(id_aruco).a_png(aruco / nombre_png_v2(id_aruco), gh.PPP, gris=True)

    verif, detalle = ([], {})
    if verificar:
        verif, detalle = verificar_aruco(salida)

    (salida / "contrato.md").write_text(generar_contrato_md(probs, fovs_min, fov_rec, vistas, verif),
                                        encoding="utf-8")
    (salida / "lista_material.md").write_text(generar_lista_material(fov_min), encoding="utf-8")
    return {"problemas": probs, "verificacion": detalle, "fov_necesario": fovs_min, "fov_recomendado": fov_rec,
            "vistas": vistas, "vistas_41": vistas_41}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--salida", type=Path, default=RAIZ / "hardware" / "v2")
    ap.add_argument("--sin-verificar", action="store_true", help="no relee los marcadores con OpenCV")
    args = ap.parse_args(argv)
    res = generar(args.salida, verificar=not args.sin_verificar)
    print(f"Generado en {args.salida}")
    for p in res["problemas"]:
        print(f"  AVISO: {p.texto}")
    malos = [k for k, v in res["verificacion"].items() if v is not None and not v["ok"]]
    if malos:
        print(f"  VERIFICACIÓN FALLIDA: {', '.join(malos)}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
