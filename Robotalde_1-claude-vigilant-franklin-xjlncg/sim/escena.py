"""Escena MuJoCo de LeWelder: SO-101 con antorcha, mesa, base de anclajes, piezas con ArUco y dos cámaras.

La escena sale del modelo oficial del SO-101 (variante con soporte de cámara de muñeca) y de `lewelder.contrato`.
Se construye con `mujoco.MjSpec`, así no hay rutas relativas que arreglar y se puede guardar el MJCF resultante.

Decisiones (ver el informe de la tarea 4):
- **Marco del mundo = marco de la mesa** (metros en MuJoCo, milímetros en el contrato). El robot se desplaza para
  que el centro de su huella (la base impresa) quede en el origen.
- **Antorcha atravesada en la pinza**: cilindro sujeto entre las mordazas, perpendicular al eje de aproximación y a
  la dirección de cierre, con la punta `LONGITUD_ANTORCHA_ROBOT` más allá del punto de agarre (`gripperframe`).
  Con la antorcha coaxial a la muñeca, `wrist_roll` no cambiaría su dirección y un brazo de 5 articulaciones no
  podría dar a la vez el ángulo de trabajo de 45° de la T y el empuje; atravesada, `wrist_roll` la inclina y la
  IK controla posición (3) y dirección (2) con las 5 articulaciones.
- **Piezas como cuerpos mocap**: las dos (recta y T) están siempre en el modelo y se colocan moviendo su pose;
  la que no se usa se esconde bajo la mesa. Cambiar de anclaje o de tipo no reconstruye nada.
"""
from __future__ import annotations

from pathlib import Path

import cv2
import mujoco
import numpy as np
from PIL import Image

from lewelder import contrato as c

RAIZ = Path(__file__).resolve().parents[1]
MODELO_SO101 = RAIZ / "assets" / "so101" / "so101_new_calib_camera.xml"
CACHE = RAIZ / "salidas" / "escena"  # imágenes de los ArUco generadas (ignorado por git)

MM = 1e-3  # milímetros → metros

# Constantes que el contrato de la rama principal ya define (se usan si están; si no, con el mismo valor):
# la pieza apoya sobre el anclaje y su Z = 0 queda CHAPA_GROSOR por encima; margen blanco alrededor de los ArUco.
PIEZA_EN_ANCLAJE = getattr(c, "PIEZA_EN_ANCLAJE", (0.0, 0.0, c.ALTURA_SUPERFICIE_PIEZA))
MARGEN_BLANCO_ARUCO = getattr(c, "MARGEN_BLANCO_ARUCO", 5.0)  # mm alrededor del lado negro

# Centro de la huella de la base impresa del SO-101 en el marco de su cuerpo `base` (medido sobre la malla
# base_so101_v2: x de -22,4 a 64,6 mm, y de -55,5 a 55,5 mm). El robot se coloca para que ese punto sea el origen.
CENTRO_HUELLA_ROBOT = (0.0211, 0.0, 0.0)

# Antorcha del robot (metros, en su propio marco: z del mango a la punta, origen en el punto de agarre).
RADIO_ANTORCHA = 0.007
RADIO_BOQUILLA = 0.004
LONGITUD_BOQUILLA = 0.020
MANGO_TRAS_AGARRE = 0.035  # lo que sobresale la antorcha por detrás de las mordazas
# Ángulo entre el eje de aproximación de la pinza (hacia la punta de los dedos) y la antorcha, girando hacia +y
# local de la pinza: 0° = coaxial (como un lápiz en los dedos), 90° = atravesada.
ANGULO_MONTAJE = 90.0
MASA_ANTORCHA = 0.05  # kg, cuerpo impreso + microcontrolador + LED

# Pinza cerrada sobre el mango de la antorcha (radianes de la articulación `gripper`).
PINZA_AGARRE = 0.10

# Cámaras
# Cenital: alta, sobre el lado lejano de la base y algo inclinada hacia el robot (desde la vertical exacta la
# propia antorcha y la pinza tapan la punta). La parte de arriba de la imagen es +X de la mesa (lejos del robot).
CAMARA_CENITAL_POS = (0.58, -0.01, 0.80)  # m
CAMARA_CENITAL_OBJETIVO = (0.28, -0.01, 0.0)
FOVY_CENITAL = 42.0
FOVY_MUNECA = 75.0
# Cámara de muñeca: sujeta a la pinza por delante de los dedos (no en el soporte oficial, que queda detrás de la
# muñeca: en la T el alma le tapa la punta), y mira a un punto del eje de la antorcha un poco antes de la punta.
# Posición respecto al punto de agarre, en ejes de la pinza: x = cierre de las mordazas, y = antorcha, -z = dedos.
CAMARA_MUNECA_EN_PINZA = (0.0, 0.020, -0.045)  # m
OBJETIVO_MUNECA_EN_ANTORCHA = 0.090  # m desde el agarre

ESCONDITE = (0.0, 0.0, -1.0)  # donde va la pieza que no se usa

# Colisiones: brazo (1) contra escena (2), sin choques del brazo consigo mismo ni de la escena consigo misma.
_BRAZO = (1, 2)  # (contype, conaffinity)
_ESCENA = (2, 1)


# --- marcos -------------------------------------------------------------------------------------------------------
def rot_z(grados: float) -> np.ndarray:
    a = np.radians(grados)
    return np.array([[np.cos(a), -np.sin(a), 0.0], [np.sin(a), np.cos(a), 0.0], [0.0, 0.0, 1.0]])


def rotacion_pieza(anclaje: str) -> np.ndarray:
    """Matriz 3x3 con los ejes de la pieza (columnas X, Y, Z) en el marco de la mesa.

    `giro = 0` hace que el cordón avance en +Y de la mesa; X de la pieza = Rz(giro) · (0, 1, 0).
    """
    return rot_z(c.ANCLAJES[anclaje].giro) @ rot_z(90.0)


def origen_pieza(anclaje: str) -> np.ndarray:
    """Origen del marco de la pieza (inicio del cordón, superficie de apoyo de la punta) en la mesa, en mm."""
    a = c.ANCLAJES[anclaje]
    return np.array([a.x, a.y, c.ALTURA_BASE_ANCLAJES + PIEZA_EN_ANCLAJE[2]])


def pieza_a_mesa(anclaje: str, p_mm) -> np.ndarray:
    """Punto del marco de la pieza (mm) → marco de la mesa (mm)."""
    return origen_pieza(anclaje) + rotacion_pieza(anclaje) @ np.asarray(p_mm, dtype=float)


def mesa_a_pieza(anclaje: str, p_mm) -> np.ndarray:
    """Punto del marco de la mesa (mm) → marco de la pieza (mm)."""
    return rotacion_pieza(anclaje).T @ (np.asarray(p_mm, dtype=float) - origen_pieza(anclaje))


def _quat(R: np.ndarray) -> list[float]:
    q = np.zeros(4)
    mujoco.mju_mat2Quat(q, np.asarray(R, dtype=float).reshape(9))
    return q.tolist()


def huella_pieza(anclaje: str) -> np.ndarray:
    """Esquinas (4x2, mm, mesa) del rectángulo que ocupa una pieza más el ArUco de su anclaje."""
    y_min = ARUCO_ANCLAJE_Y_MIN
    y_max = c.CHAPA_ANCHO + c.HOLGURA_JUNTA / 2  # la base de la T llega a +CHAPA_ANCHO; la recta, un poco más
    x0, x1 = -c.MARGEN_X, c.LONGITUD_CORDON + c.MARGEN_X
    esquinas = [(x0, y_min, 0), (x1, y_min, 0), (x1, y_max, 0), (x0, y_max, 0)]
    return np.array([pieza_a_mesa(anclaje, e)[:2] for e in esquinas])


# Borde exterior (en -Y de la pieza) del ArUco del anclaje con su margen blanco
ARUCO_ANCLAJE_Y_MIN = c.ARUCO_EN_ANCLAJE[1] - c.LADO_ARUCO_ANCLAJE / 2 - MARGEN_BLANCO_ARUCO


# --- ArUco --------------------------------------------------------------------------------------------------------
def imagen_aruco(id_aruco: int, px_modulo: int = 20, lado_negro_mm: float = c.LADO_ARUCO_PIEZA) -> np.ndarray:
    """Imagen RGB del marcador `id_aruco` del diccionario del contrato rodeada de `MARGEN_BLANCO_ARUCO` mm en blanco.

    El marcador 4x4 tiene 6 módulos de lado contando su borde negro; el lado negro mide `LADO_ARUCO_*`.
    """
    diccionario = cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, c.DICCIONARIO_ARUCO))
    negro = cv2.aruco.generateImageMarker(diccionario, id_aruco, 6 * px_modulo)
    m = int(round(MARGEN_BLANCO_ARUCO / lado_negro_mm * 6 * px_modulo))
    img = cv2.copyMakeBorder(negro, m, m, m, m, cv2.BORDER_CONSTANT, value=255)
    return np.stack([img] * 3, axis=-1)


def _archivo_aruco(id_aruco: int) -> str:
    CACHE.mkdir(parents=True, exist_ok=True)
    ruta = CACHE / f"aruco_{c.DICCIONARIO_ARUCO}_{id_aruco}_margen{MARGEN_BLANCO_ARUCO:g}.png"
    if not ruta.exists():
        Image.fromarray(imagen_aruco(id_aruco)).save(ruta)
    return str(ruta)


def id_aruco_pieza(tipo) -> int:
    """Id del ArUco que lleva la pieza simulada de cada tipo (el primero de su rango)."""
    return c.IDS_PIEZA[c.TipoPieza(tipo)][0]


def id_aruco_anclaje(anclaje: str) -> int:
    return next(i for i, n in c.IDS_ANCLAJE.items() if n == anclaje)


# --- construcción -------------------------------------------------------------------------------------------------
def _caja(cuerpo, nombre, centro_mm, medio_mm, rgba=None, material=None, colision=True):
    g = cuerpo.add_geom(name=nombre, type=mujoco.mjtGeom.mjGEOM_BOX,
                        pos=[v * MM for v in centro_mm], size=[v * MM for v in medio_mm])
    if rgba is not None:
        g.rgba = rgba
    if material is not None:
        g.material = material
    g.contype, g.conaffinity = _ESCENA if colision else (0, 0)
    return g


def _material_aruco(spec, id_aruco: int) -> str:
    nombre = f"aruco_{id_aruco}"
    spec.add_texture(name=nombre, type=mujoco.mjtTexture.mjTEXTURE_2D, file=_archivo_aruco(id_aruco))
    mat = spec.add_material(name=nombre)
    mat.textures[mujoco.mjtTextureRole.mjTEXROLE_RGB] = nombre
    return nombre


def _marcador(cuerpo, spec, nombre, id_aruco, centro_mm, lado_negro_mm):
    """Pegatina del ArUco (lado negro + margen blanco) apoyada sobre z = centro_mm[2], ejes alineados."""
    medio = lado_negro_mm / 2 + MARGEN_BLANCO_ARUCO
    x, y, z = centro_mm
    _caja(cuerpo, nombre, (x, y, z + 0.15), (medio, medio, 0.15), material=_material_aruco(spec, id_aruco),
          colision=False)


def _pieza_recta(spec):
    b = spec.worldbody.add_body(name="pieza_recta", mocap=True, pos=list(ESCONDITE))
    gris = [0.62, 0.64, 0.68, 1]
    yc = c.HOLGURA_JUNTA / 2 + c.CHAPA_ANCHO / 2
    xc = c.LONGITUD_CORDON / 2
    medio = (c.CHAPA_LARGO / 2, c.CHAPA_ANCHO / 2, c.CHAPA_GROSOR / 2)
    _caja(b, "recta_chapa_der", (xc, -yc, -c.CHAPA_GROSOR / 2), medio, rgba=gris)
    _caja(b, "recta_chapa_izq", (xc, yc, -c.CHAPA_GROSOR / 2), medio, rgba=gris)
    # Fondo oscuro de la junta: hace visible el cordón desde arriba
    _caja(b, "recta_junta", (xc, 0, -c.CHAPA_GROSOR + 0.5), (c.CHAPA_LARGO / 2, c.HOLGURA_JUNTA / 2, 0.5),
          rgba=[0.12, 0.12, 0.14, 1], colision=False)
    _marcador(b, spec, "recta_aruco", id_aruco_pieza(c.TipoPieza.RECTA), c.ARUCO_EN_PIEZA, c.LADO_ARUCO_PIEZA)
    _marcas_cordon(b, "recta")
    return b


def _pieza_t(spec):
    b = spec.worldbody.add_body(name="pieza_t", mocap=True, pos=list(ESCONDITE))
    gris = [0.62, 0.64, 0.68, 1]
    xc = c.LONGITUD_CORDON / 2
    _caja(b, "t_base", (xc, 0, -c.CHAPA_GROSOR / 2), (c.CHAPA_LARGO / 2, c.CHAPA_ANCHO, c.CHAPA_GROSOR / 2),
          rgba=gris)
    _caja(b, "t_alma", (xc, c.ALMA_GROSOR / 2, c.ALMA_ALTO / 2), (c.CHAPA_LARGO / 2, c.ALMA_GROSOR / 2,
                                                                    c.ALMA_ALTO / 2), rgba=[0.55, 0.58, 0.63, 1])
    _marcador(b, spec, "t_aruco", id_aruco_pieza(c.TipoPieza.T), c.ARUCO_EN_PIEZA, c.LADO_ARUCO_PIEZA)
    _marcas_cordon(b, "t")
    return b


def _marcas_cordon(b, prefijo):
    """Rayitas en el inicio y el final del cordón (como las de la pieza impresa)."""
    for i, x in enumerate((0.0, c.LONGITUD_CORDON)):
        _caja(b, f"{prefijo}_marca_{i}", (x, -6.0, 0.1), (0.6, 4.0, 0.1), rgba=[0.9, 0.2, 0.1, 1], colision=False)


def _base_anclajes(spec):
    """Placa de la base y, sobre ella, la huella y el ArUco de cada anclaje."""
    puntos = np.vstack([huella_pieza(n) for n in c.ANCLAJES])
    margen = 15.0
    (x0, y0), (x1, y1) = puntos.min(0) - margen, puntos.max(0) + margen
    h = c.ALTURA_BASE_ANCLAJES
    w = spec.worldbody
    _caja(w, "base_anclajes", ((x0 + x1) / 2, (y0 + y1) / 2, h / 2), ((x1 - x0) / 2, (y1 - y0) / 2, h / 2),
          rgba=[0.20, 0.36, 0.62, 1])
    for nombre in c.ANCLAJES:
        cuerpo = w.add_body(name=f"anclaje_{nombre}", pos=[v * MM for v in origen_pieza(nombre)[:2]] + [h * MM],
                            quat=_quat(rotacion_pieza(nombre)))
        # Huella rebajada (más clara) donde se apoya la pieza
        _caja(cuerpo, f"anclaje_{nombre}_huella", (c.LONGITUD_CORDON / 2, 0, 0.05),
              (c.CHAPA_LARGO / 2 + 1, c.CHAPA_ANCHO + 1, 0.05), rgba=[0.30, 0.48, 0.75, 1], colision=False)
        _marcador(cuerpo, spec, f"anclaje_{nombre}_aruco", id_aruco_anclaje(nombre), c.ARUCO_EN_ANCLAJE,
                  c.LADO_ARUCO_ANCLAJE)


def _antorcha(spec, angulo_montaje: float):
    """Antorcha rígida sujeta entre las mordazas, con el sitio `punta_antorcha` (z = dirección mango → punta)."""
    pinza = spec.body("gripper")
    agarre = spec.site("gripperframe").pos
    # z de la antorcha = cos(a)·(-z) + sin(a)·(+y) de la pinza: a = 90° la deja perpendicular al eje de aproximación
    # y al cierre de las mordazas, hacia el lado del soporte de la cámara de muñeca. Es un giro Rx(a - 180°).
    th = np.radians(angulo_montaje - 180.0)
    b = pinza.add_body(name="antorcha", pos=list(agarre), quat=[np.cos(th / 2), np.sin(th / 2), 0, 0])
    b.mass = MASA_ANTORCHA
    b.inertia = [2e-5, 2e-5, 2e-6]
    b.explicitinertial = True
    L = c.LONGITUD_ANTORCHA_ROBOT * MM
    largo_cuerpo = L - LONGITUD_BOQUILLA

    def cilindro(nombre, z0, z1, radio, rgba):
        g = b.add_geom(name=nombre, type=mujoco.mjtGeom.mjGEOM_CYLINDER, fromto=[0, 0, z0, 0, 0, z1],
                       size=[radio, 0, 0], rgba=rgba)
        g.contype, g.conaffinity = 0, 0
        g.group = 1

    cilindro("antorcha_cuerpo", -MANGO_TRAS_AGARRE, largo_cuerpo, RADIO_ANTORCHA, [0.85, 0.30, 0.10, 1])
    cilindro("antorcha_boquilla", largo_cuerpo, L - 0.002, RADIO_BOQUILLA, [0.75, 0.75, 0.78, 1])
    led = b.add_geom(name="antorcha_led", type=mujoco.mjtGeom.mjGEOM_SPHERE, pos=[0, 0, L - 0.002],
                     size=[0.0025, 0, 0], rgba=[0.1, 1.0, 0.2, 1])
    led.contype, led.conaffinity = 0, 0
    b.add_site(name="punta_antorcha", pos=[0, 0, L], size=[0.0015, 0, 0], rgba=[1, 0, 0, 1])
    return b


def _mirar(pos, objetivo, arriba):
    """xyaxes de una cámara en `pos` que mira a `objetivo` (todo en el marco del cuerpo padre)."""
    f = np.asarray(objetivo, float) - np.asarray(pos, float)
    f /= np.linalg.norm(f)
    x = np.cross(f, arriba)
    x /= np.linalg.norm(x)
    y = np.cross(x, f)
    return np.concatenate([x, y])


def _camaras(spec):
    w = spec.worldbody
    cen = w.add_camera(name="cenital", pos=list(CAMARA_CENITAL_POS), fovy=FOVY_CENITAL)
    cen.alt.type = mujoco.mjtOrientation.mjORIENTATION_XYAXES
    cen.alt.xyaxes = _mirar(CAMARA_CENITAL_POS, CAMARA_CENITAL_OBJETIVO, np.array([1.0, 0.0, 0.0])).tolist()
    # Muñeca: mirando a la punta de la antorcha.
    marco = spec.compile()  # para conocer la pose de la antorcha respecto a la pinza
    d = mujoco.MjData(marco)
    mujoco.mj_kinematics(marco, d)
    b_pinza, b_ant = marco.body("gripper").id, marco.body("antorcha").id

    def en_pinza(p):
        return d.xmat[b_pinza].reshape(3, 3).T @ (p - d.xpos[b_pinza])

    objetivo = en_pinza(d.xpos[b_ant] + d.xmat[b_ant].reshape(3, 3)[:, 2] * OBJETIVO_MUNECA_EN_ANTORCHA)
    pos = np.asarray(spec.site("gripperframe").pos) + np.asarray(CAMARA_MUNECA_EN_PINZA)
    # "Arriba" de la imagen: hacia la muñeca (-z de la pinza apunta a los dedos; +z hacia atrás)
    cam = spec.body("gripper").add_camera(name="muneca", pos=list(pos), fovy=FOVY_MUNECA)
    cam.alt.type = mujoco.mjtOrientation.mjORIENTATION_XYAXES
    cam.alt.xyaxes = _mirar(pos, objetivo, np.array([0.0, 0.0, 1.0])).tolist()


def _leer_stl(ruta: Path) -> tuple[np.ndarray, np.ndarray]:
    """Vértices (Nx3) y caras (Mx3) de un STL binario, con los vértices repetidos fusionados."""
    datos = ruta.read_bytes()
    n = int(np.frombuffer(datos, dtype="<u4", count=1, offset=80)[0])
    reg = np.frombuffer(datos, dtype=np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")]), count=n,
                        offset=84)
    v, inv = np.unique(reg["v"].reshape(-1, 3), axis=0, return_inverse=True)
    return v.astype(float), inv.reshape(-1, 3)


def _agrupar_vertices(v: np.ndarray, f: np.ndarray, celda: float) -> tuple[np.ndarray, np.ndarray]:
    """Simplifica una malla juntando los vértices que caen en la misma celda de una rejilla (vertex clustering)."""
    claves = np.floor(v / celda).astype(np.int64)
    _, grupo, cuenta = np.unique(claves, axis=0, return_inverse=True, return_counts=True)
    grupo = grupo.reshape(-1)
    nuevos = np.zeros((len(cuenta), 3))
    np.add.at(nuevos, grupo, v)
    nuevos /= cuenta[:, None]
    caras = grupo[f]
    buenas = (caras[:, 0] != caras[:, 1]) & (caras[:, 1] != caras[:, 2]) & (caras[:, 0] != caras[:, 2])
    caras = np.unique(np.sort(caras[buenas], axis=1), axis=0, return_index=True)[1]
    caras = grupo[f][buenas][np.sort(caras)]  # sin duplicados, conservando la orientación original
    return nuevos, caras


def simplificar_mallas(spec: mujoco.MjSpec, celda_mm: float) -> None:
    """Sustituye las mallas STL del robot por versiones simplificadas.

    El render por CPU (llvmpipe) va limitado por el número de triángulos (~400 000 en el SO-101): con celdas de
    1,5 mm quedan unas diez veces menos y la imagen a 256x192 es indistinguible.
    """
    for malla in spec.meshes:
        if not malla.file.lower().endswith(".stl"):
            continue
        v, f = _leer_stl(Path(spec.meshdir) / malla.file)
        v = v * np.asarray(malla.scale)
        v2, f2 = _agrupar_vertices(v, f, celda_mm * MM)
        if len(f2) < 20:  # malla demasiado pequeña para la rejilla: se deja como está
            continue
        malla.file = ""
        malla.scale = [1.0, 1.0, 1.0]
        malla.uservert = v2.reshape(-1).tolist()
        malla.userface = f2.reshape(-1).astype(int).tolist()


def construir_spec(simplificar_mm: float | None = 1.5, angulo_montaje: float = ANGULO_MONTAJE) -> mujoco.MjSpec:
    """MjSpec de la escena completa (sin compilar). `simplificar_mm=None` usa las mallas originales."""
    spec = spec_robot_y_mesa(simplificar_mm)
    _base_anclajes(spec)
    _pieza_recta(spec)
    _pieza_t(spec)
    _antorcha(spec, angulo_montaje)
    _camaras(spec)
    return spec


def spec_robot_y_mesa(simplificar_mm: float | None = 1.5) -> mujoco.MjSpec:
    """Parte común de las escenas (v1 y montaje v2): SO-101, luces, cielo, mesa y suelo, sin compilar."""
    spec = mujoco.MjSpec.from_file(str(MODELO_SO101))
    spec.modelname = "lewelder"
    spec.meshdir = str(MODELO_SO101.parent / "assets")
    # Paso de integración: 16 subpasos por fotograma del dataset
    spec.option.timestep = 1.0 / (c.FPS_DATASET * 16)

    # Robot: huella centrada en el origen; colisiones brazo-escena, no brazo-brazo
    base = spec.body("base")
    base.pos = [-v for v in CENTRO_HUELLA_ROBOT]
    for g in spec.geoms:
        if g.contype or g.conaffinity:
            g.contype, g.conaffinity = _BRAZO

    if simplificar_mm:
        simplificar_mallas(spec, simplificar_mm)

    # Aspecto: luz suave y sin brillos (las cámaras reales llevan exposición fija)
    spec.visual.global_.offwidth = 1280
    spec.visual.global_.offheight = 960
    spec.visual.headlight.ambient = [0.25, 0.25, 0.25]
    spec.visual.headlight.diffuse = [0.25, 0.25, 0.25]
    spec.visual.headlight.specular = [0, 0, 0]
    spec.visual.quality.shadowsize = 1024
    spec.add_texture(name="cielo", type=mujoco.mjtTexture.mjTEXTURE_SKYBOX,
                     builtin=mujoco.mjtBuiltin.mjBUILTIN_GRADIENT, rgb1=[0.55, 0.62, 0.70], rgb2=[0.15, 0.17, 0.2],
                     width=256, height=1536)
    w = spec.worldbody
    w.add_light(name="sol", pos=[0.3, -0.2, 1.5], dir=[-0.15, 0.1, -1], type=mujoco.mjtLightType.mjLIGHT_DIRECTIONAL,
                castshadow=True, diffuse=[0.45, 0.45, 0.45], specular=[0.05, 0.05, 0.05])
    w.add_light(name="relleno", pos=[0.2, 0.6, 0.8], dir=[0, -0.6, -0.8], type=mujoco.mjtLightType.mjLIGHT_DIRECTIONAL,
                castshadow=False, diffuse=[0.15, 0.15, 0.15], specular=[0, 0, 0])

    # Mesa (tablero de 1,2 x 0,8 m con la superficie en z = 0) y suelo
    _caja(w, "mesa", (200.0, 0.0, -15.0), (600.0, 400.0, 15.0), rgba=[0.72, 0.60, 0.45, 1])
    suelo = w.add_geom(name="suelo", type=mujoco.mjtGeom.mjGEOM_PLANE, pos=[0, 0, -0.75], size=[3, 3, 0.1],
                       rgba=[0.3, 0.3, 0.32, 1])
    suelo.contype, suelo.conaffinity = 0, 0
    return spec


def construir_modelo(simplificar_mm: float | None = 1.5,
                     angulo_montaje: float = ANGULO_MONTAJE) -> tuple[mujoco.MjModel, mujoco.MjSpec]:
    spec = construir_spec(simplificar_mm, angulo_montaje)
    return spec.compile(), spec


def guardar_mjcf(ruta: str | Path) -> Path:
    """Escribe el MJCF de la escena (para abrirlo con `python -m mujoco.viewer` o revisarlo)."""
    spec = construir_spec()
    spec.compile()
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(spec.to_xml(), encoding="utf-8")
    return ruta


def colocar_pieza(modelo: mujoco.MjModel, datos: mujoco.MjData, anclaje: str, tipo) -> None:
    """Pone la pieza `tipo` en `anclaje` y esconde la otra. No hace falta recompilar."""
    tipo = c.TipoPieza(tipo)
    usar, esconder = ("pieza_recta", "pieza_t") if tipo is c.TipoPieza.RECTA else ("pieza_t", "pieza_recta")
    i_usar = modelo.body_mocapid[modelo.body(usar).id]
    i_esc = modelo.body_mocapid[modelo.body(esconder).id]
    datos.mocap_pos[i_usar] = origen_pieza(anclaje) * MM
    datos.mocap_quat[i_usar] = _quat(rotacion_pieza(anclaje))
    datos.mocap_pos[i_esc] = ESCONDITE
    datos.mocap_quat[i_esc] = [1, 0, 0, 0]


if __name__ == "__main__":
    print("MJCF guardado en", guardar_mjcf(CACHE / "lewelder.xml"))
