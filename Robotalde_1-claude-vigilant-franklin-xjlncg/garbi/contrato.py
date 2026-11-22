"""Contrato común de Garbi: constantes que comparten la simulación, la visión, el control y la demo.

Unidades: **milímetros, segundos y grados**, salvo que el nombre diga otra cosa.

Marcos de coordenadas
---------------------
- **Mesa:** origen en el eje de giro del SO-101 sobre la mesa (centro de la huella de su base). X hacia delante
  (lejos del robot), Y hacia la izquierda vista desde detrás del robot, Z hacia arriba; la mesa es Z = 0.
- **Tabla:** origen en el centro de la cara de arriba de la tabla, X a lo largo del lado largo, Z hacia arriba.
  La tabla se coloca en la mesa con (x, y, giro). Los agujeros y la viruta que cae sobre ella se guardan en este
  marco: si alguien mueve la tabla, se mueven con ella.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

FPS = 30

# --- área de trabajo del hackathon (medidas del usuario, 19-11) -------------------------------------------------
# Marco de la mesa: origen en el centro de la huella del robot, sobre el tablero; x hacia la persona (el robot está en
# el borde de atrás, de frente a quien trabaja), y a la izquierda del robot, z hacia arriba. mm.
MESA_FONDO, MESA_ANCHO, MESA_ALTO = 600.0, 1200.0, 750.0
MESA_X_ATRAS = -80.0  # borde de atrás de la mesa (detrás del robot); el de la persona queda en x = 520
MESA_RGBA = (0.80, 0.80, 0.78, 1.0)  # tablero laminado claro
PERSONA_X = MESA_X_ATRAS + MESA_FONDO  # borde de la mesa donde trabaja la persona

# --- tapete de trabajo (azul, con 4 ArUco en las esquinas): 450 de ancho × 400 de fondo -------------------------
ALFOMBRILLA_TAMANO = (400.0, 450.0)  # (x: fondo, y: ancho)
ALFOMBRILLA_X_CERCA = 110.0  # borde del tapete más cercano al robot (la madera va lejos del robot, hacia la persona)
ALFOMBRILLA_CENTRO = (ALFOMBRILLA_X_CERCA + ALFOMBRILLA_TAMANO[0] / 2, 0.0)
ALFOMBRILLA_GROSOR = 2.0
ALFOMBRILLA_RGBA = (0.12, 0.30, 0.70, 1.0)
LADO_ARUCO_ALFOMBRILLA = 40.0  # lado negro (a ~0,8 m de la cámara de arriba)
IDS_ARUCO_ALFOMBRILLA = (10, 11, 12, 13)  # esquinas: (+x,+y), (+x,-y), (-x,-y), (-x,+y)
MARGEN_ARUCO_ALFOMBRILLA = 30.0  # del borde de la alfombrilla al centro del marcador


def esquinas_aruco_alfombrilla() -> dict[int, np.ndarray]:
    """Centro (mm, marco de la mesa) de cada ArUco de la alfombrilla."""
    cx, cy = ALFOMBRILLA_CENTRO
    hx = ALFOMBRILLA_TAMANO[0] / 2 - MARGEN_ARUCO_ALFOMBRILLA
    hy = ALFOMBRILLA_TAMANO[1] / 2 - MARGEN_ARUCO_ALFOMBRILLA
    signos = [(1, 1), (1, -1), (-1, -1), (-1, 1)]
    return {i: np.array([cx + sx * hx, cy + sy * hy, ALFOMBRILLA_GROSOR])
            for i, (sx, sy) in zip(IDS_ARUCO_ALFOMBRILLA, signos)}


# --- madera para taladrar: 300 × 200 × 18, madera natural clara (solución final, 20-11) -------------------------
# En el marco de la tabla, x es su lado de 200 (hacia la persona con giro 0) e y el de 300 (a lo ancho).
# Sin vinilo: la cara es madera clara (contrasta con el tapete azul) y lleva una pegatina de color en una esquina, que
# resuelve la ambigüedad de 180° del rectángulo (ver `garbi.percepcion.detectar_madera`).
TABLA_TAMANO = (200.0, 300.0, 18.0)  # (x, y, grueso)
TABLA_RGBA_CANTO = (0.84, 0.74, 0.57, 1.0)
TABLA_RGBA_CARA = (0.90, 0.83, 0.70, 1.0)  # contrachapado de abedul, claro y poco saturado
PEGATINA_EN_TABLA = (70.0, 120.0)  # centro (marco de la tabla): esquina (+x, +y), a 30 mm de cada borde
PEGATINA_LADO = 30.0  # pegatina cuadrada
PEGATINA_RGBA = (0.92, 0.10, 0.62, 1.0)  # magenta: no se confunde con el tapete, la bola, el anillo ni el robot
LADO_ARUCO_TABLA = 25.0
IDS_ARUCO_TABLA = (20, 21)
ARUCO_TABLA_EN_TABLA = ((-78.0, 128.0), (78.0, -128.0))  # centros (marco de la tabla), en esquinas opuestas
ALTURA_CARA_TABLA = ALFOMBRILLA_GROSOR + TABLA_TAMANO[2]  # z de la cara de arriba sobre la mesa

# Zona donde se deja la madera: lejos del robot, hacia la persona. Con el montaje lateral la boca solo ataca casi en
# horizontal (10-25°) a partir de ~290 mm del robot; con la madera centrada a ~360 mm (de 260 a 460) el taladro cae
# en esa zona.
ZONA_TABLA_X = (350.0, 370.0)  # centro de la madera
ZONA_TABLA_X_MORDAZAS = (175.0, 195.0)  # con el montaje anterior (boquilla en las mordazas, alcance ~220 mm)
ZONA_TABLA_Y = (-30.0, 30.0)
ZONA_TABLA_GIRO = (-8.0, 8.0)
RADIO_TRABAJO_MAX = 220.0  # mm del eje del robot: más allá no llega al preapunto junto al taladro (limpiar llega a 240)
RADIO_TRABAJO_MIN = 120.0
RADIO_LIMPIAR_TAPETE = 280.0  # mm: hasta aquí limpia sobre el tapete (mapa de alcance)


def punto_serrin_tapete(rng) -> np.ndarray:
    """Un sitio del tapete donde tiene sentido que caiga serrín y Garbi lo alcance: a los lados de la madera."""
    lado = rng.choice([-1.0, 1.0])
    return np.array([rng.uniform(100.0, 200.0), lado * rng.uniform(175.0, 205.0)])

# --- agujeros y viruta ------------------------------------------------------------------------------------------
MAX_AGUJEROS = 16
RADIO_AGUJERO = 4.0  # broca de 8 mm
MAX_VIRUTA = 240
VIRUTA_POR_AGUJERO = 36
RADIO_VIRUTA_MIN = 6.0  # anillo de viruta alrededor del agujero
RADIO_VIRUTA_MAX = 22.0
LADO_VIRUTA = 2.6  # cada partícula simulada es un cubito de este lado
VIRUTA_RGBA = (0.92, 0.75, 0.44, 1.0)  # serrín de pino (más amarillo y saturado que la cara de abedul)

# --- boca de aspiración (boquilla recta atornillada a la pinza, siempre a 30°) -----------------------------------
# La boquilla trabaja siempre inclinada `INCLINACION_BOCA` bajo la horizontal: al acompañar al taladro y al limpiar.
# Con el SO-101 esa inclinación se alcanza en toda la zona llegando de lado (la vertical solo en ~6 de 15 puntos), y
# con la boquilla de 110 mm la pinza queda a 18-22 mm del cuerpo del taladro: ver .plans/aspira/montaje-boquilla.md.
DIAMETRO_BOCA = 35.0
LARGO_MANGO = 110.0  # del punto de agarre a la boca: aleja la pinza y la muñeca del cuerpo del taladro
INCLINACION_BOCA = 30.0  # grados bajo la horizontal
GIRO_LLEGADA = 110.0  # la boca mira en planta rotz(±GIRO_LLEGADA) · (radial hacia fuera): de lado, algo hacia el robot
DISTANCIA_ACOMPANAR = 40.0  # a lo largo del eje, del centro de la boca a la punta de la broca (34,6 mm en planta)
# Preapunto (desde donde la cámara del robot mira la broca): la boca SUBIDA_PREAPUNTO más alta y ATRAS_PREAPUNTO más
# atrás (en planta, contra la dirección en la que mira) que en el sitio de acompañar. Subir más acerca el brazo al
# cuerpo del taladro; ahí la holgura es ≥ 27 mm en toda la zona.
SUBIDA_PREAPUNTO = 20.0
ATRAS_PREAPUNTO = 30.0
ALTURA_BOCA_LIMPIEZA = 18.0  # centro de la boca sobre la superficie al limpiar (el borde de abajo queda a ~3 mm)
# Aspiración: cono a lo largo del eje de la boca. Una partícula a `a` mm por delante de la boca (a lo largo del eje) y
# a `l` mm del eje se recoge si 0 ≤ a ≤ ALCANCE_CAPTACION y l ≤ RADIO_CAPTACION + PENDIENTE_CAPTACION · a.
ALCANCE_CAPTACION = 50.0
RADIO_CAPTACION = 14.0
PENDIENTE_CAPTACION = 0.3
DISTANCIA_MINIMA_BROCA = 15.0  # nada de la boca más cerca de la broca

# --- taladro de batería, en vertical para taladrar hacia abajo ----------------------------------------------------
# Forma real simplificada: broca, portabrocas, cuerpo del motor a lo largo del eje, empuñadura que sale en horizontal
# del extremo de arriba hacia la persona y batería al final de la empuñadura. La mano de la persona la sujeta.
LARGO_BROCA = 60.0
DIAMETRO_BROCA = 8.0
PORTABROCAS_LARGO, PORTABROCAS_DIAMETRO = 75.0, 45.0
CUERPO_LARGO, CUERPO_DIAMETRO = 160.0, 60.0
EMPUNADURA_LARGO, EMPUNADURA_ANCHO = 110.0, 38.0  # sale del extremo de arriba del cuerpo, hacia la persona
BATERIA_TAMANO = (80.0, 110.0, 60.0)  # al final de la empuñadura
TALADRO_RGBA = (0.10, 0.45, 0.30, 1.0)  # verde (como muchos taladros de batería)
# Marcador para la cámara de arriba: bola naranja sobre un vástago en la tapa de atrás del motor (arriba del todo)
RADIO_BOLA = 17.0
LARGO_VASTAGO_BOLA = 25.0
ALTURA_BOLA_SOBRE_PUNTA = LARGO_BROCA + PORTABROCAS_LARGO + CUERPO_LARGO + LARGO_VASTAGO_BOLA + RADIO_BOLA
BOLA_RGBA = (1.0, 0.45, 0.0, 1.0)

# --- cámaras ----------------------------------------------------------------------------------------------------
# Cámara de arriba en un soporte de flexo sujeto al lateral de la mesa (a la derecha del robot), mirando al tapete
CAMARA_FIJA_POS = (260.0, -420.0, 780.0)
CAMARA_FIJA_OBJETIVO = (320.0, 0.0, 0.0)
FOVY_FIJA = 50.0
RESOLUCION_VISION = (1280, 960)  # cámara fija para la visión clásica (a ~0,85 m del tapete)
RESOLUCION_POLITICA = (256, 192)  # lo que ve el VLA (fija y muñeca)
CAMARAS_POLITICA = ("top", "wrist")

# --- seguridad y movimiento -------------------------------------------------------------------------------------
VELOCIDAD_MAX_BOCA = 120.0  # mm/s en movimientos programados
VELOCIDAD_ACERCARSE = 50.0  # mm/s al ir hacia el taladro (pedido por el equipo rojo)
ASPIRAR_TRAS_RETIRADA = 2.0  # s que sigue aspirando tras retirar el taladro

# --- órdenes del VLA (frases fijas en inglés) -------------------------------------------------------------------
ORDEN_AGUJERO = "Clean around the new hole."
ORDEN_ALFOMBRILLA = "Clean the chips on the mat."
ORDENES_VLA = (ORDEN_AGUJERO, ORDEN_ALFOMBRILLA)


@dataclass
class PoseTabla:
    x: float
    y: float
    giro: float  # grados

    def matriz(self) -> np.ndarray:
        """Homogénea 3x3 tabla → mesa (plano)."""
        a = np.radians(self.giro)
        c, s = np.cos(a), np.sin(a)
        return np.array([[c, -s, self.x], [s, c, self.y], [0.0, 0.0, 1.0]])

    def a_mesa(self, p_tabla) -> np.ndarray:
        p = np.asarray(p_tabla, dtype=float)
        h = self.matriz() @ np.array([p[..., 0], p[..., 1], np.ones_like(p[..., 0])])
        return np.stack([h[0], h[1]], axis=-1)

    def a_tabla(self, p_mesa) -> np.ndarray:
        p = np.asarray(p_mesa, dtype=float)
        h = np.linalg.inv(self.matriz()) @ np.array([p[..., 0], p[..., 1], np.ones_like(p[..., 0])])
        return np.stack([h[0], h[1]], axis=-1)

    def contiene(self, p_mesa, margen: float = 0.0) -> bool:
        x, y = self.a_tabla(p_mesa)
        return abs(x) <= TABLA_TAMANO[0] / 2 - margen and abs(y) <= TABLA_TAMANO[1] / 2 - margen

    def contiene_varios(self, pts_mesa, margen: float = 0.0) -> np.ndarray:
        """Como `contiene`, para N puntos a la vez (Nx2): vector de booleanos."""
        loc = self.a_tabla(np.asarray(pts_mesa, float).reshape(-1, 2))
        return (np.abs(loc[:, 0]) <= TABLA_TAMANO[0] / 2 - margen) & (np.abs(loc[:, 1]) <= TABLA_TAMANO[1] / 2 - margen)
