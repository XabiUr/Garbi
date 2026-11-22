"""Contrato común de LeWelder: lo que todas las partes comparten.

Este módulo solo contiene constantes, tipos de datos y ayudas mínimas. Si una parte necesita cambiar algo de aquí,
se cambia aquí (y en `hardware/contrato.md`), nunca con un número copiado en otro sitio.

Unidades: **milímetros, segundos y grados**, salvo que el nombre diga otra cosa.

Marcos de coordenadas
---------------------
- **Mesa:** origen en el centro de la base del robot soldador, proyectado sobre la mesa. X hacia delante (lejos del
  robot), Y hacia la izquierda vista desde detrás del robot, Z hacia arriba. La superficie de la mesa es Z = 0.
- **Anclaje:** origen en el centro del anclaje sobre la superficie de la base de anclajes; girado `giro` grados
  respecto a la mesa alrededor de Z. Una pieza colocada en un anclaje tiene su marco de pieza en el mismo lugar
  que el del anclaje, desplazado por `PIEZA_EN_ANCLAJE`.
- **Pieza:** origen al **inicio del cordón**, X a lo largo del cordón (0 → `LONGITUD_CORDON`, sentido de avance),
  Y transversal (izquierda según el avance), Z hacia arriba desde la superficie donde se apoya la punta.
  En la unión a tope, el cordón es la junta entre las dos chapas (Y = 0, Z = 0). En la unión en T, el cordón es la
  esquina entre la chapa base y el alma vertical; el alma queda en Y >= 0 y el cordón en (Y = 0, Z = 0).

Ángulos de la antorcha (en el marco de la pieza)
------------------------------------------------
El eje de la antorcha apunta del mango a la punta.
- **Ángulo de trabajo:** en el plano YZ (perpendicular al cordón), ángulo entre el eje de la antorcha y la
  superficie de la chapa base. 90° = antorcha vertical. Objetivo: 90° en la unión a tope, 45° en la T.
- **Ángulo de avance:** en el plano XZ, inclinación del eje respecto a la vertical. Positivo = **empuje** (la punta
  va por delante del mango en el sentido de avance +X). Objetivo: entre 0° y 20° de empuje.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum

# --- cordón ------------------------------------------------------------------------------------------------------
LONGITUD_CORDON = 120.0  # mm
TAMANO_TRAMO = 5.0  # mm
N_TRAMOS = int(LONGITUD_CORDON / TAMANO_TRAMO)  # 24

# Tolerancia de desvío lateral (distancia de la punta al cordón en el plano), por nivel.
TOLERANCIAS = {"aprendiz": 8.0, "oficial": 5.0, "maestro": 3.0}
NIVEL_JURADO = "oficial"

# Velocidad de avance buena (mm/s): 120 mm en 20-30 s.
VELOCIDAD_OBJETIVO = (4.0, 6.0)
# Punto quemado: gatillo pulsado con la punta casi parada demasiado tiempo.
VELOCIDAD_PARADO = 1.0  # mm/s
TIEMPO_QUEMADO = 0.6  # s

# Ángulos objetivo (grados) y margen admitido.
ANGULO_TRABAJO_OBJETIVO = {"recta": 90.0, "t": 45.0, "esquina": 45.0}  # la esquina se suelda por dentro
MARGEN_ANGULO_TRABAJO = 15.0
ANGULO_AVANCE_RANGO = (0.0, 20.0)

# Distancia de la punta a la superficie mientras se "suelda" (la punta no toca).
ALTURA_PUNTA = 3.0  # mm


class TipoPieza(str, Enum):
    RECTA = "recta"
    T = "t"


# --- geometría de piezas (mm, en el marco de la pieza) -----------------------------------------------------------
# Unión a tope: dos chapas iguales de LARGO x ANCHO x GROSOR separadas por una junta de HOLGURA_JUNTA,
# simétricas respecto a Y = 0. Se extienden MARGEN_X antes y después del cordón.
CHAPA_LARGO = 140.0
CHAPA_ANCHO = 40.0
CHAPA_GROSOR = 6.0
HOLGURA_JUNTA = 1.5
MARGEN_X = (CHAPA_LARGO - LONGITUD_CORDON) / 2  # 10 mm
# Unión en T: chapa base CHAPA_LARGO x (2*CHAPA_ANCHO) centrada en Y = 0 y alma vertical de ALMA_ALTO x ALMA_GROSOR
# con su cara en Y = 0 (el alma ocupa 0 <= Y <= ALMA_GROSOR) y apoyada sobre la base.
ALMA_ALTO = 40.0
ALMA_GROSOR = 6.0
# La superficie de apoyo de la punta (Z = 0 de la pieza) está CHAPA_GROSOR por encima de la base de anclajes.
ALTURA_SUPERFICIE_PIEZA = CHAPA_GROSOR

# --- ArUco -------------------------------------------------------------------------------------------------------
DICCIONARIO_ARUCO = "DICT_4X4_50"  # cv2.aruco.DICT_4X4_50
LADO_ARUCO_PIEZA = 25.0  # mm, solo la parte negra (sin el margen blanco)
LADO_ARUCO_ANCLAJE = 25.0
MARGEN_BLANCO_ARUCO = 5.0  # mm de borde blanco alrededor de cada marcador impreso
# ArUco de la pieza: pegado sobre la chapa base (Z = 0), con sus ejes alineados con los de la pieza
# (X del marcador = X de la pieza). Centro del marcador en el marco de la pieza:
ARUCO_EN_PIEZA = (LONGITUD_CORDON / 2, -(HOLGURA_JUNTA / 2 + CHAPA_ANCHO / 2), 0.0)  # (60, -20.75, 0)
IDS_PIEZA = {TipoPieza.RECTA: range(10, 20), TipoPieza.T: range(20, 30)}
# ArUco de cada anclaje: en la base de anclajes, delante del hueco de la pieza (en -Y del anclaje).
ARUCO_EN_ANCLAJE = (LONGITUD_CORDON / 2, -(HOLGURA_JUNTA / 2 + CHAPA_ANCHO + 20.0), 0.0)  # fuera de la pieza
IDS_ANCLAJE = {0: "A", 1: "B", 2: "C", 3: "D"}


def tipo_por_id(id_aruco: int) -> TipoPieza | None:
    """Tipo de pieza que corresponde a un id de ArUco, o None si no es de pieza."""
    for tipo, ids in IDS_PIEZA.items():
        if id_aruco in ids:
            return tipo
    return None


# --- base de anclajes (marco de la mesa) -------------------------------------------------------------------------
@dataclass(frozen=True)
class Anclaje:
    nombre: str
    x: float  # mm, posición del origen del marco de la pieza (inicio del cordón) en la mesa
    y: float
    giro: float  # grados alrededor de Z; 0 = el cordón avanza en +Y de la mesa (de derecha a izquierda)


# Validados en simulación (tarea 4, `sim/validar.py`) con la antorcha atravesada en la pinza: recta (vertical) y T
# (45°) con 10° de empuje, error de seguimiento < 2 mm, y margen de ±2° en los ángulos sin llegar a los límites.
# Huella de cada pieza: 140 mm a lo largo del cordón x 119 mm en transversal (de +40,75 a -78,25 en Y de la pieza,
# incluido el ArUco del anclaje con su margen blanco). Con giro 0 la Y de la pieza apunta al robot (-X de la mesa):
# la T se suelda desde fuera con el alma hacia el robot. Zona útil (centro del cordón): x ≈ 240-300 mm; la recta
# vertical no llega más cerca (x < 230) y la T a 45° no llega más lejos (x > 300) ni más a los lados (|y| > 200).
# Por eso van en fila: D, C, B con giro 0 y A con giro -90 (el cordón avanza en +X) en el extremo derecho, más
# estrecho. Huellas en la mesa (mm): A x[185, 325] y[-293, -174]; B x[209, 328] y[-164, -24];
# C x[209, 328] y[-14, 126]; D x[209, 328] y[136, 276]; 10 mm entre huellas vecinas.
ANCLAJES = {
    "A": Anclaje("A", 195.0, -215.0, -90.0),
    "B": Anclaje("B", 250.0, -154.0, 0.0),
    "C": Anclaje("C", 250.0, -4.0, 0.0),
    "D": Anclaje("D", 250.0, 146.0, 0.0),
}
ALTURA_BASE_ANCLAJES = 10.0  # mm, grosor de la base de anclajes sobre la mesa
# Origen del marco de la pieza en el marco del anclaje: el anclaje está en la superficie de la base y la pieza
# apoya encima, así que Z = 0 de la pieza queda CHAPA_GROSOR por encima. El ArUco del anclaje está a Z = 0 del anclaje.
PIEZA_EN_ANCLAJE = (0.0, 0.0, ALTURA_SUPERFICIE_PIEZA)

# --- imanes ------------------------------------------------------------------------------------------------------
IMAN_DIAMETRO = 10.0
IMAN_ALTO = 3.0
AGUJEROS_IMAN_PRUEBA = (10.2, 10.4, 10.6)  # diámetros a imprimir para elegir el ajuste
IMANES_POR_PIEZA = 4

# --- antorchas y electrónica -------------------------------------------------------------------------------------
COLOR_LED = "verde"  # LED de la punta de la antorcha del alumno y del robot
EJE_ANTORCHA_EN_IMU = (1.0, 0.0, 0.0)  # la IMU va montada con +X apuntando a la punta
EJE_ARRIBA_EN_IMU = (0.0, 0.0, 1.0)  # +Z de la IMU hacia la cara superior de la antorcha (la opuesta al gatillo)
# Tara: antorcha vertical, punta abajo, cara superior mirando hacia el avance (+X de la pieza). El cuaternión de la
# IMU es de Hamilton [w, x, y, z] y lleva del marco de la IMU al "mundo" de la IMU; solo se usa el giro desde la tara.
# El ángulo de trabajo va de 0 a 180°: < 90 cuando la punta se inclina hacia +Y (hacia el alma de la T).
LONGITUD_ANTORCHA_ROBOT = 100.0  # mm, de la cara de la pinza a la punta

BAUDIOS = 115200
FRECUENCIA_ANTORCHA = 100  # Hz
# Antorcha del alumno → PC: una línea JSON por muestra: {"t": ms, "g": 0|1, "q": [w, x, y, z] | null}
# ("q": null si no hay IMU).
# PC → antorcha del robot: "L1\n" (LED encendido) / "L0\n" (apagado).
# Cualquiera de las dos responde a "?\n" con {"id": "alumno"} o {"id": "robot"}.
ORDEN_LED_ON = "L1\n"
ORDEN_LED_OFF = "L0\n"
ORDEN_IDENTIFICAR = "?\n"
LATIDO_LED = 1.0  # s: el PC reenvía el estado del LED del robot al menos con esta frecuencia
TIEMPO_SEGURIDAD_LED = 2.0  # s: la antorcha del robot apaga el LED si no recibe nada en este tiempo

PINES = {
    "nano": {"gatillo": 2, "led": 9, "sda": "A4", "scl": "A5"},
    "esp32": {"gatillo": 4, "led": 2, "sda": 21, "scl": 22},
}

# --- muestras ----------------------------------------------------------------------------------------------------
@dataclass
class Muestra:
    """Estado de la punta de la antorcha en un instante, en el marco de la pieza."""

    t: float  # s
    x: float  # mm
    y: float
    z: float
    gatillo: bool
    angulo_trabajo: float | None = None  # grados; None si no hay IMU
    angulo_avance: float | None = None

    def a_dict(self) -> dict:
        return asdict(self)


# --- instrucciones del robot (vocabulario cerrado del dataset) ---------------------------------------------------
NOMBRE_UNION = {TipoPieza.RECTA: "recta", TipoPieza.T: "en T"}


def instruccion_soldar(tipo: TipoPieza, anclaje: str) -> str:
    return f"suelda la unión {NOMBRE_UNION[TipoPieza(tipo)]} del anclaje {anclaje}"


def instruccion_colocar(anclaje: str) -> str:
    return f"coloca la pieza en el anclaje {anclaje}"


# =================================================================================================================
# v2 · escuela-taller (spec v2): el robot monta la junta pedida sobre una base fija y la escuela la reconoce en 3D.
# Lo de arriba (v1) sigue valiendo: unidades, cordón de 120 mm en 24 tramos, tolerancias, Muestra, protocolo serie.
# =================================================================================================================
class TipoJunta(str, Enum):
    T = "t"
    ESQUINA = "esquina"


NOMBRE_JUNTA = {TipoJunta.T: "en T", TipoJunta.ESQUINA: "en esquina"}

# --- piezas v2 (mm) -----------------------------------------------------------------------------------------------
# Marco de la BASE: origen en el centro de la cara superior de la chapa base, X a lo largo del lado largo, Y
# transversal, Z hacia arriba. La base se apoya en la mesa (Z mesa = 0) con su cara inferior.
# Una sola CHAPA MÓVIL sirve para las dos juntas: la junta depende de dónde se coloca.
#   - T: de pie sobre la línea central de la base, ocupando 0 <= Y <= GROSOR_CHAPA.
#   - Esquina (interior): de pie junto al tope del canto +Y, ocupando 31 <= Y <= 37 (el tope ocupa 37 <= Y <= 40).
# Fuente de verdad física: el CAD de SolidWorks en hardware/v2/cad/ (NOTAS_CAD.md).
# En las dos, el cordón va por el lado -Y de la chapa móvil (el lado que miran las webcams) y la aleta por el +Y.
LARGO_BASE = 200.0
ANCHO_BASE = 80.0
GROSOR_CHAPA = 6.0  # base y móvil
LARGO_MOVIL = 140.0
ALTO_MOVIL = 40.0  # lado corto de la chapa móvil: su altura cuando está de pie
# Aleta para la pinza, en la cara +Y de la chapa móvil (hacia arriba cuando está tumbada).
ALETA = {"largo": 40.0, "alto": 18.0, "grosor": 5.0, "x": -35.0}  # x: centro de la aleta respecto al de la chapa
# Guías en la base para que los imanes centren la chapa: ranura en la línea central (T) y tope en el canto (esquina).
GUIA_T = {"ancho": GROSOR_CHAPA + 1.0, "profundo": 2.0}
TOPE_ESQUINA = {"alto": 3.0, "ancho": 3.0}  # nervio dentro de la base, en el canto +Y (Y 37 a 40)
IMANES_LINEA = 3  # imanes por línea de montaje (base) y en el canto inferior de la chapa móvil
# Cordón en el marco de la base: de X = -LONGITUD_CORDON/2 a +LONGITUD_CORDON/2, en Z = 0 (cara de la base).
Y_CORDON = {TipoJunta.T: 0.0, TipoJunta.ESQUINA: ANCHO_BASE / 2 - TOPE_ESQUINA["ancho"] - GROSOR_CHAPA}  # 0 y 31
# Z del canto inferior de la chapa móvil montada, en el marco de la base: en la T entra 2 mm en la ranura.
Z_CANTO_MOVIL = {TipoJunta.T: -2.0, TipoJunta.ESQUINA: 0.0}
IMAN_MOVIL = (4.0, 4.0)  # Ø x alto de los imanes del canto de la chapa móvil (la base usa IMAN_DIAMETRO x IMAN_ALTO)
# Polaridad asimétrica: base N/N/S hacia arriba en X -56/0/+56 y móvil S/S/N hacia abajo: girada 180°, se repele.

# --- ArUco v2 (uno por chapa; la móvil uno por cara) --------------------------------------------------------------
ID_BASE = 30
IDS_MOVIL = {"cara_aleta": 40, "cara_lisa": 41}  # repuestos: 42/43 y 44/45
LADO_ARUCO_V2 = 25.0
# Centro del ArUco de la base en su marco: fuera del cordón y de las dos posiciones de la chapa móvil.
ARUCO_EN_BASE = (82.0, -20.0, 0.0)
# Centro de cada ArUco de la móvil en el marco de la chapa (X a lo largo, Y = altura cuando está de pie, desde el
# canto que apoya): en el lado opuesto a la aleta.
ARUCO_EN_MOVIL = (35.0, ALTO_MOVIL / 2)

# --- mesa de montaje (marco de la mesa, mismo convenio de giro que `Anclaje`) --------------------------------------
# Posición por defecto de la base: centro de la base en (x, y), giro 0 = X de la base hacia +Y de la mesa.
# Ajustadas por la tarea 2 (alcance del SO-101 en simulación, `sim/validar_montaje.py`):
# - base en x = 280: más cerca la muñeca (±95°) suelta la chapa demasiado inclinada; más lejos (290) la antorcha
#   del CAD no llega a soldar la T a 45°. y = 35 pone la aleta (X = −35 de la chapa) en el plano del brazo (y ≈ 0),
#   porque con 5 ejes la pinza no gira de lado.
# - zona libre a la izquierda y cerca: la pinza vertical solo coge la aleta y la levanta a r < ~250 mm; con giro 0 la
#   aleta queda hacia el robot en ese lado. La de la derecha (y −260..−185) queda fuera de alcance casi entera.
#   Con x 110-160 e y 160-230 la chapa tumbada (girada ±60°) no pisa ni la base ni la base del robot
#   (`herramientas/generar_hardware_v2.comprobar_mesa`).
# - soporte a la derecha a r ≈ 255: la pinza coge el mango en horizontal a z = 116 solo a partir de r ≈ 250.
POSICION_BASE = Anclaje("montaje", 280.0, 35.0, 0.0)
# Zona libre donde está tumbada la chapa móvil (rectángulo en la mesa, posición y giro libres dentro).
ZONA_LIBRE = {"x": (110.0, 160.0), "y": (160.0, 230.0), "giro": (-60.0, 60.0)}  # dónde cae el centro de la chapa
# Soporte de la antorcha del robot (mango vertical para que la pinza la coja siempre igual).
SOPORTE_ANTORCHA = {"x": 180.0, "y": -180.0, "z_mango": 116.0}  # mango a 116 sobre el tablero (CAD: 6 + 95 + 15)
ANGULO_AVANCE_ROBOT = 10.0  # grados de empuje con los que suelda el robot
RUTA_RANKING = "salidas/ranking.json"

# --- seguimiento v2 ----------------------------------------------------------------------------------------------
ALTURA_APOYO = 2.0  # mm: la punta cuenta como apoyada si está a menos de esto de la chapa
# Dos webcams en estéreo (mismo convenio que `PoseCamara.por_defecto`): altura, inclinación respecto a la vertical,
# azimut (0 = desde +X de la mesa) y punto al que miran. Validadas por la tarea 1 del plan v2.
# Validadas con el CAD y la mesa de montaje (hardware/v2/validacion_vision.md): webcams 1080p, FOV horizontal >= 60°
# (ven la base y todo el barrido de la zona libre con un 5 % de margen con 55°). Centros ópticos (633, -113, 450) y
# (633, 253, 450): al otro lado de la base respecto al robot, mirando a la cara lisa de la chapa de pie a ~50°.
CAMARAS_ESTEREO = {
    "a": {"altura": 450.0, "inclinacion": 45.0, "azimut": -25.0, "objetivo": (240.0, 70.0, 16.0)},
    "b": {"altura": 450.0, "inclinacion": 45.0, "azimut": 25.0, "objetivo": (240.0, 70.0, 16.0)},
}

# Posiciones de soldeo (ISO 6947), por la orientación del cordón y de la junta respecto a la gravedad.
POSICIONES_SOLDEO = {
    "PA": "plana",
    "PB": "horizontal en ángulo",
    "PC": "horizontal (cornisa)",
    "PD": "en ángulo bajo techo",
    "PE": "bajo techo",
    "PF": "vertical ascendente",
    "PG": "vertical descendente",
}

# --- vocabulario v2 del robot (una sola política multitarea) -----------------------------------------------------
# orden → nivel de la escalera de alcance (1 = núcleo)
ORDENES = {
    "monta una unión en T": 1,
    "monta una unión en esquina": 1,
    "señala el cordón": 1,
    "coge la antorcha y suelda la junta": 1,
    "desmonta la junta": 2,
    "acércame la antorcha": 2,
    "gira la junta hacia ti": 3,
}


def orden_montar(junta: TipoJunta | str) -> str:
    return f"monta una unión {NOMBRE_JUNTA[TipoJunta(junta)]}"


# --- robot ------------------------------------------------------------------------------------------------------
FPS_DATASET = 30
CAMARAS_POLITICA = ("cenital", "muneca")
# Para SmolVLA: --rename_map con estas parejas y --policy.empty_cameras=1
RENOMBRE_SMOLVLA = {
    "observation.images.cenital": "observation.images.camera1",
    "observation.images.muneca": "observation.images.camera2",
}
