"""Mesa de montaje v2 en MuJoCo: base fija, chapa móvil imantada, antorcha en su soporte y entorno `EntornoMontaje`.

La escena sale de `lewelder.contrato` (sección v2) y reutiliza de `sim.escena` el SO-101 con sus mallas simplificadas,
la mesa, las luces, la cámara cenital y las texturas ArUco.

Decisiones (ver el informe de la tarea 2 del plan v2):
- **Almohadillas en los dedos.** MuJoCo colisiona con la envolvente convexa de cada malla y la del dedo fijo rellena
  el hueco entre dedos. Las chapas y la antorcha solo chocan con dos cajas finas (una por dedo) con fricción alta,
  y con la mesa, la base y el soporte; con el resto del brazo no (bits de colisión `_OBJETO` y `_ALMOHADILLA`).
  La almohadilla del dedo móvil queda paralela a la del fijo con la aleta (5 mm) cogida.
- **Imanes = restricción `weld` que se activa.** Cuando la chapa está suelta (ninguna almohadilla la toca) y su canto
  inferior queda a menos de `CAPTURA_MM` de una de las dos líneas de montaje con un giro de menos de
  `CAPTURA_GRADOS`, se activa una soldadura blanda (`solref` de `REF_IMAN` s) hacia la pose exacta de esa junta: el
  último centímetro lo hacen los imanes, como en la pieza real con guía y tope. Queda activa hasta el `reset`.
- **Piezas reales.** Base, chapa móvil, antorcha y soporte son los STL del CAD (`hardware/v2/cad/stl/`, ver
  `sim.piezas_cad`): la malla se ve y la colisión va con primitivas medidas sobre ella (ranura, tope, aleta, mango y
  tubo del soporte de verdad). Las cotas que usa el guion (altura de la aleta, mango, punta) salen de esas medidas.
- **Antorcha de pie en su tubo y cogida de lado.** La pinza entra en horizontal y aprieta las caras planas del mango:
  el eje de la antorcha queda atravesado (perpendicular a la aproximación y al cierre), como en la v1, que es lo único
  que deja soldar el cordón (lado lejano de la junta) con 45° y empuje con 5 ejes. Para planificar la soldadura se
  mide la pose real de la punta en la pinza y se copia en el sitio `herramienta`. Al devolverla, cuando cae dentro del
  tubo y queda a menos de `ASIENTO_MM` de su sitio, una `weld` la fija (lo que en la pieza hace la chaveta).

Marcos (mm): mesa y base como en el contrato. Chapa móvil: origen en el centro del canto inferior (el que lleva los
imanes) a media chapa de grosor, X a lo largo, Y = altura desde el canto, Z = grosor con la cara lisa (ArUco 41) en
+Z y la aleta en -Z. De pie en la base: X = X de la base, Y = Z de la base, Z = -Y de la base. (El CAD usa X, Y =
grosor con la aleta en +Y, Z = altura; `M_MOVIL` pasa de uno a otro.) Antorcha: origen en el centro del mango, z =
eje mango → punta, x = normal de las caras planas del mango, y = dirección en la que entra la pinza.
"""
from __future__ import annotations

import mujoco
import numpy as np

from lewelder import contrato as c
from sim import escena, piezas_cad
from sim.cinematica import Cinematica
from sim.entorno import RESOLUCION, SUBPASOS, EntornoSoldadura, lerobot_a_rad, rad_a_lerobot

MM = escena.MM
TipoJunta = c.TipoJunta

# --- geometría medida en el CAD (sim.piezas_cad) -------------------------------------------------------------------
M_MOVIL = np.array([[1.0, 0, 0], [0, 0, 1.0], [0, -1.0, 0]])  # marco del CAD de la chapa → marco de la simulación
M_ANTORCHA = np.array([[0, 1.0, 0], [1.0, 0, 0], [0, 0, -1.0]])  # CAD de la antorcha (sin trasladar) → simulación
DENSIDAD_PLA = 1240.0  # kg/m³
MASA_IMANES_MOVIL = 0.003  # kg (3 imanes Ø4 × 4)
MASA_ELECTRONICA_ANTORCHA = 0.008  # kg (LED y cables)


def geometria() -> dict:
    """Cotas del CAD que usa la simulación (mm), medidas en las mallas."""
    mm_ = piezas_cad.medidas("MOVIL-V2")
    ma = piezas_cad.medidas("ANTORCHA-ROBOT-V2")
    az = piezas_cad._quitar_voxel(mm_["aleta_z"])
    ax = piezas_cad._quitar_voxel(mm_["aleta_x"])
    return {
        "aleta_y": (az[0] + az[1]) / 2,  # altura del centro de la aleta sobre el canto
        "aleta_x": (ax[0] + ax[1]) / 2,
        "aleta_grosor": az[1] - az[0],
        "aleta_alto": mm_["aleta_y"][1] - mm_["aleta_y"][0],
        "mango_grosor": ma["mango_y"][1] - ma["mango_y"][0],  # entre las caras que aprieta la pinza
        "mango_ancho": ma["mango_x"][1] - ma["mango_x"][0],  # a lo largo de la aproximación
        "mango_largo": ma["mango_z"][1] - ma["mango_z"][0],
        "punta_a_mango": (ma["mango_z"][0] + ma["mango_z"][1]) / 2,  # de la punta al centro del mango
        "pie_soporte": piezas_cad.medidas("SOPORTE-ANTORCHA-V2")["pie_z"][1],  # la punta apoya aquí
    }


_GEO = geometria()
ALETA_Y = _GEO["aleta_y"]
PUNTA_A_MANGO = _GEO["punta_a_mango"]
FRICCION_PLA = 0.35  # PLA contra PLA (piezas impresas); la mesa y las almohadillas llevan la suya
ASIENTO_MM = 2.0  # la antorcha queda fijada en el soporte si cae a menos de esto de su sitio...
ASIENTO_GRADOS = 6.0  # ...y con menos de este giro

# --- imanes ---------------------------------------------------------------------------------------------------------
CAPTURA_MM = 10.0
CAPTURA_GRADOS = 20.0
# s: constante de tiempo de la atracción (soldadura blanda). Con 0,015 s la fuerza sobre la chapa (~50 g) es de unos
# 2 N a 10 mm, como tres parejas de imanes N52 a esa distancia; con 0,05 s no vencía el rozamiento con la base.
REF_IMAN = 0.015
ERROR_CERRADA_MM = 1.5  # junta cerrada si la chapa queda a menos de esto de su sitio...
ERROR_CERRADA_GRADOS = 1.5  # ...y con menos de este giro

# --- pinza ----------------------------------------------------------------------------------------------------------
# Almohadillas (m, marco del cuerpo `gripper`): la cara interior del dedo fijo está en x = X_DEDO_FIJO; las dos
# cubren los últimos 25 mm de los dedos. La del dedo móvil es paralela a la fija con la pinza en Q_PARALELA (rad),
# separada HUECO_PARALELO (la aleta).
X_DEDO_FIJO = -0.0079
Z_ALMOHADILLA = (-0.104, -0.079)
ANCHO_ALMOHADILLA = 0.007  # semiancho a lo largo de los dedos (y de la pinza)
GROSOR_ALMOHADILLA = 0.001  # semigrosor
Q_PARALELA = -0.13
HUECO_PARALELO = 0.005
FRICCION_ALMOHADILLA = (1.5, 0.02, 0.0002)
# Contacto rígido: el servo de la pinza aprieta con ~3,35 N·m (unos 45 N en las yemas); con el contacto por defecto
# la aleta se hundía 3 mm en las almohadillas y la chapa giraba al levantarla.
SOLREF_ALMOHADILLA = (0.004, 1.0)
SOLIMP_ALMOHADILLA = (0.95, 0.99, 0.0005, 0.5, 2.0)
CONDIM_ALMOHADILLA = 4
NOSLIP = 4  # iteraciones del solver sin deslizamiento (opt.noslip_iterations)
PINZA_ABIERTA = 0.55  # rad: abierta para acercarse a la aleta o al mango (~45 mm entre dedos)
PINZA_CERRADA = -0.17453  # rad: orden de cierre (el contacto la para antes)
# Punta de la pinza (para "señala"): centro de las yemas con la pinza cerrada.
PUNTA_PINZA = (-0.0068, 0.0, -0.104)

# Colisiones (contype, conaffinity): brazo (1) y escena (2) como en la v1; objetos sueltos (4) chocan con la escena y
# con las almohadillas (8); las almohadillas solo con los objetos.
_ESCENA = escena._ESCENA
_OBJETO = (4, 2 | 8)
_ALMOHADILLA = (8, 4)

ORDEN_SENALAR = "señala el cordón"
ORDEN_SOLDAR = "coge la antorcha y suelda la junta"
ORDENES_MONTAR = {c.orden_montar(j): TipoJunta(j) for j in TipoJunta}
ORDENES_NUCLEO = [o for o, nivel in c.ORDENES.items() if nivel == 1]

# Postura de reposo (grados de LeRobot): brazo recogido y pinza casi cerrada.
REPOSO = np.array([0.0, -95.0, 85.0, 70.0, 0.0, 5.0])


# --- marcos ---------------------------------------------------------------------------------------------------------
def rot_x(grados: float) -> np.ndarray:
    a = np.radians(grados)
    return np.array([[1.0, 0.0, 0.0], [0.0, np.cos(a), -np.sin(a)], [0.0, np.sin(a), np.cos(a)]])


def rotacion_base() -> np.ndarray:
    """Ejes de la base (columnas) en la mesa: giro 0 = X de la base hacia +Y de la mesa (convenio de `Anclaje`)."""
    return escena.rot_z(c.POSICION_BASE.giro) @ escena.rot_z(90.0)


def origen_base() -> np.ndarray:
    """Centro de la cara superior de la base en la mesa (mm)."""
    return np.array([c.POSICION_BASE.x, c.POSICION_BASE.y, c.GROSOR_CHAPA])


def base_a_mesa(p_mm) -> np.ndarray:
    return origen_base() + rotacion_base() @ np.asarray(p_mm, dtype=float)


def mesa_a_base(p_mm) -> np.ndarray:
    return rotacion_base().T @ (np.asarray(p_mm, dtype=float) - origen_base())


# Chapa móvil de pie en la base (giro y posición del origen de la chapa en el marco de la base)
R_MOVIL_EN_BASE = np.column_stack([(1.0, 0.0, 0.0), (0.0, 0.0, 1.0), (0.0, -1.0, 0.0)])
POS_MOVIL_EN_BASE = {j: np.array([0.0, c.Y_CORDON[j] + c.GROSOR_CHAPA / 2, c.Z_CANTO_MOVIL[j]]) for j in TipoJunta}
# Chapa tumbada con giro 0: altura (Y) hacia +X de la mesa, X hacia +Y de la mesa y cara lisa abajo (aleta arriba).
# Girarla 90° alrededor de su X (un cabeceo de la muñeca) la deja de pie con la aleta hacia el robot.
R_TUMBADA = np.column_stack([(0.0, 1.0, 0.0), (1.0, 0.0, 0.0), (0.0, 0.0, -1.0)])


def pose_montada(junta) -> tuple[np.ndarray, np.ndarray]:
    """(giro 3x3, origen en mm) de la chapa móvil montada en `junta`, en la mesa."""
    j = TipoJunta(junta)
    return rotacion_base() @ R_MOVIL_EN_BASE, base_a_mesa(POS_MOVIL_EN_BASE[j])


def pose_tumbada(x: float, y: float, giro: float) -> tuple[np.ndarray, np.ndarray]:
    """(giro, origen en mm) de la chapa tumbada con el centro de su cara en (x, y) y girada `giro` grados."""
    R = escena.rot_z(giro) @ R_TUMBADA
    centro = np.array([x, y, c.GROSOR_CHAPA / 2])
    return R, centro - R @ np.array([0.0, c.ALTO_MOVIL / 2, 0.0])


def marco_cordon(junta) -> tuple[np.ndarray, np.ndarray]:
    """(giro, origen en mm) del marco de la pieza del contrato para la junta montada: origen al inicio del cordón,
    X a lo largo (de -LONGITUD/2 a +LONGITUD/2 de la base), Y hacia la chapa móvil, Z hacia arriba."""
    j = TipoJunta(junta)
    return rotacion_base(), base_a_mesa((-c.LONGITUD_CORDON / 2, c.Y_CORDON[j], 0.0))


def mesa_a_cordon(junta, p_mm) -> np.ndarray:
    R, o = marco_cordon(junta)
    return R.T @ (np.asarray(p_mm, dtype=float) - o)


def cordon_a_mesa(junta, p_mm) -> np.ndarray:
    R, o = marco_cordon(junta)
    return o + R @ np.asarray(p_mm, dtype=float)


def giro_soporte() -> float:
    """Giro (grados) del soporte en la mesa: su +X (lado de la chaveta) mira lejos del robot, en radial."""
    s = c.SOPORTE_ANTORCHA
    return float(np.degrees(np.arctan2(s["y"], s["x"])))


def pose_soporte() -> tuple[np.ndarray, np.ndarray]:
    """(giro, origen en mm) de la antorcha guardada: de pie con la punta abajo apoyada en el pie del soporte, la pinza
    entra en horizontal desde el robot (y de la antorcha = radial hacia fuera) y aprieta las caras planas del mango.
    El centro del mango queda a `pie + punta_a_mango` (≈ `SOPORTE_ANTORCHA['z_mango']`)."""
    u = escena.rot_z(giro_soporte()) @ np.array([1.0, 0.0, 0.0])
    z = np.array([0.0, 0.0, -1.0])
    R = np.column_stack([np.cross(u, z), u, z])
    s = c.SOPORTE_ANTORCHA
    return R, np.array([s["x"], s["y"], _GEO["pie_soporte"] + PUNTA_A_MANGO])


def angulo_entre(Ra: np.ndarray, Rb: np.ndarray) -> float:
    """Ángulo (grados) del giro que lleva Ra a Rb."""
    return float(np.degrees(np.arccos(np.clip((np.trace(Ra.T @ Rb) - 1) / 2, -1.0, 1.0))))


# Agarres: pose del sitio `gripperframe` (x = aproximación, z = cierre hacia el dedo móvil) en el marco del objeto.
# El objeto queda con su cara a 0,5 mm del dedo fijo, que no se mueve al cerrar: así no se arrastra.
PROFUNDIDAD_AGARRE = 8.0  # mm desde el extremo libre de la aleta / del mango hasta `gripperframe`


def agarre_aleta() -> tuple[np.ndarray, np.ndarray]:
    R = np.column_stack([(0.0, 0.0, 1.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)])
    extremo = -(c.GROSOR_CHAPA / 2 + _GEO["aleta_alto"])
    p = np.array([_GEO["aleta_x"], ALETA_Y - _GEO["aleta_grosor"] / 2 - 0.5, extremo + PROFUNDIDAD_AGARRE])
    return R, p


def agarre_mango() -> tuple[np.ndarray, np.ndarray]:
    R = np.column_stack([(0.0, 1.0, 0.0), (0.0, 0.0, 1.0), (1.0, 0.0, 0.0)])
    p = np.array([-_GEO["mango_grosor"] / 2 - 0.5, -_GEO["mango_ancho"] / 2 + PROFUNDIDAD_AGARRE, 0.0])
    return R, p


def componer(Ra, pa, Rb, pb):
    """(Ra, pa) ∘ (Rb, pb): pose b expresada en el marco padre de a."""
    return Ra @ Rb, pa + Ra @ pb


def invertir(R, p):
    return R.T, -R.T @ p


# --- construcción ---------------------------------------------------------------------------------------------------
def _caja(cuerpo, nombre, centro_mm, medio_mm, rgba=None, material=None, bits=_ESCENA, quat=None, densidad=None):
    g = cuerpo.add_geom(name=nombre, type=mujoco.mjtGeom.mjGEOM_BOX, pos=[v * MM for v in centro_mm],
                        size=[v * MM for v in medio_mm])
    if quat is not None:
        g.quat = list(quat)
    if rgba is not None:
        g.rgba = rgba
    if material is not None:
        g.material = material
    g.contype, g.conaffinity = bits
    if densidad is not None:
        g.density = densidad
    return g


def _pegatina(cuerpo, spec, nombre, id_aruco, centro_mm, normal_negativa=False, densidad=None):
    """ArUco (lado negro LADO_ARUCO_V2 + margen blanco) apoyado en el plano XY del cuerpo, mirando a +Z (o a -Z)."""
    medio = c.LADO_ARUCO_V2 / 2 + escena.MARGEN_BLANCO_ARUCO
    x, y, z = centro_mm
    dz = -0.15 if normal_negativa else 0.15
    quat = (0.0, 1.0, 0.0, 0.0) if normal_negativa else None  # 180° alrededor de X: la cara +Z mira a -Z
    _caja(cuerpo, nombre, (x, y, z + dz), (medio, medio, 0.15), material=escena._material_aruco(spec, id_aruco),
          bits=(0, 0), quat=quat, densidad=densidad)


def _quat(R) -> list[float]:
    return escena._quat(R)


def _pieza_cad(spec, cuerpo, nombre: str, M, t, bits, rgba, masa: float | None = None,
               friccion: float = FRICCION_PLA) -> None:
    """Malla del CAD (visual) y sus primitivas de colisión, pasadas al marco del cuerpo con p' = M p + t (mm)."""
    M = np.asarray(M, dtype=float)
    t = np.asarray(t, dtype=float)
    pieza = piezas_cad.cargar(nombre)
    v = (pieza.v @ M.T + t) * MM
    malla = spec.add_mesh(name=f"malla_{nombre}")
    malla.uservert = v.reshape(-1).tolist()
    malla.userface = pieza.f.reshape(-1).astype(int).tolist()
    g = cuerpo.add_geom(name=f"{nombre}_malla", type=mujoco.mjtGeom.mjGEOM_MESH, meshname=f"malla_{nombre}",
                        rgba=rgba, density=0)
    g.contype, g.conaffinity = 0, 0
    prims = piezas_cad.primitivas(nombre)
    vol = sum(8 * np.prod(p.medio) if p.tipo == "caja" else 2 * np.pi * p.medio[0] ** 2 * p.medio[1] for p in prims)
    densidad = (masa / (vol * MM ** 3)) if masa else 0.0
    for p in prims:
        centro = M @ np.asarray(p.centro, dtype=float) + t
        giro = M @ p.giro
        if p.tipo == "caja":
            gc = cuerpo.add_geom(name=f"{nombre}_{p.nombre}", type=mujoco.mjtGeom.mjGEOM_BOX,
                                 size=[v_ * MM for v_ in p.medio])
        else:
            gc = cuerpo.add_geom(name=f"{nombre}_{p.nombre}", type=mujoco.mjtGeom.mjGEOM_CYLINDER,
                                 size=[p.medio[0] * MM, p.medio[1] * MM, 0])
        gc.pos = (centro * MM).tolist()
        gc.quat = _quat(giro)
        gc.contype, gc.conaffinity = bits
        gc.density = densidad
        gc.friction = [friccion, 0.005, 0.0001]
        gc.group = 3  # las primitivas no se ven (se ve la malla)
        gc.rgba = [0.2, 0.8, 0.2, 0.4]


def _base(spec):
    """Base fija (BASE-V2): ranura de la T, tope de la esquina, ArUco 30 y marcas del cordón."""
    b = spec.worldbody.add_body(name="base_montaje", pos=[v * MM for v in origen_base()],
                                quat=_quat(rotacion_base()))
    _pieza_cad(spec, b, "BASE-V2", np.eye(3), np.zeros(3), _ESCENA, [0.20, 0.36, 0.62, 1])
    x, y, _ = c.ARUCO_EN_BASE
    _pegatina(b, spec, "base_aruco", c.ID_BASE, (x, y, -0.3))
    rojo = [0.9, 0.2, 0.1, 1]
    for junta in TipoJunta:
        y = c.Y_CORDON[junta] - (4.0 if junta is TipoJunta.T else 2.5)
        for i, xm in enumerate((-c.LONGITUD_CORDON / 2, c.LONGITUD_CORDON / 2)):
            _caja(b, f"base_marca_{junta.value}_{i}", (xm, y, 0.1), (0.6, 2.0, 0.1), rgba=rojo, bits=(0, 0))
    return b


def _chapa_movil(spec):
    """Chapa móvil (MOVIL-V2) suelta, con su aleta y un ArUco por cara."""
    b = spec.worldbody.add_body(name="chapa_movil", pos=[0, 0, 0.1])
    b.add_freejoint(name="chapa_movil_libre")
    masa = piezas_cad.medidas("MOVIL-V2")["volumen_mm3"] * MM ** 3 * DENSIDAD_PLA + MASA_IMANES_MOVIL
    _pieza_cad(spec, b, "MOVIL-V2", M_MOVIL, np.zeros(3), _OBJETO, [0.62, 0.64, 0.68, 1], masa)
    G = c.GROSOR_CHAPA
    xa, ya = c.ARUCO_EN_MOVIL
    _pegatina(b, spec, "movil_aruco_lisa", c.IDS_MOVIL["cara_lisa"], (xa, ya, G / 2 - 0.3), densidad=0)
    _pegatina(b, spec, "movil_aruco_aleta", c.IDS_MOVIL["cara_aleta"], (xa, ya, -G / 2 + 0.3), normal_negativa=True,
              densidad=0)
    return b


def _antorcha_suelta(spec):
    """Antorcha del robot (ANTORCHA-ROBOT-V2, las dos mitades) como objeto libre, con el LED y su punta."""
    b = spec.worldbody.add_body(name="antorcha", pos=[0, 0, 0.3])
    b.add_freejoint(name="antorcha_libre")
    masa = (piezas_cad.medidas("ANTORCHA-ROBOT-V2")["volumen_mm3"] * MM ** 3 * DENSIDAD_PLA
            + MASA_ELECTRONICA_ANTORCHA)
    t = M_ANTORCHA @ np.array([0.0, 0.0, -PUNTA_A_MANGO])
    _pieza_cad(spec, b, "ANTORCHA-ROBOT-V2", M_ANTORCHA, t, _OBJETO, [0.85, 0.30, 0.10, 1], masa)
    led = b.add_geom(name="antorcha_led", type=mujoco.mjtGeom.mjGEOM_SPHERE, pos=[0, 0, (PUNTA_A_MANGO - 1.5) * MM],
                     size=[0.0025, 0, 0], rgba=[0.1, 1.0, 0.2, 1], density=0)
    led.contype, led.conaffinity = 0, 0
    b.add_site(name="punta_antorcha", pos=[0, 0, PUNTA_A_MANGO * MM], size=[0.0015, 0, 0], rgba=[1, 0, 0, 1])
    return b


def _soporte(spec):
    """Soporte de la antorcha (SOPORTE-ANTORCHA-V2): pie y tubo con entrada cónica, chaveta hacia fuera."""
    s = c.SOPORTE_ANTORCHA
    b = spec.worldbody.add_body(name="soporte_antorcha", pos=[s["x"] * MM, s["y"] * MM, 0],
                                quat=_quat(escena.rot_z(giro_soporte())))
    _pieza_cad(spec, b, "SOPORTE-ANTORCHA-V2", np.eye(3), np.zeros(3), _ESCENA, [0.35, 0.35, 0.38, 1])
    return b


def _almohadillas(spec):
    pinza = spec.body("gripper")
    z0, z1 = Z_ALMOHADILLA
    zc, hz = (z0 + z1) / 2, (z1 - z0) / 2
    color = [0.15, 0.15, 0.15, 1]

    def almohadilla(cuerpo, nombre, pos, quat=None):
        g = cuerpo.add_geom(name=nombre, type=mujoco.mjtGeom.mjGEOM_BOX, pos=list(pos),
                            size=[GROSOR_ALMOHADILLA, ANCHO_ALMOHADILLA, hz], rgba=color)
        if quat is not None:
            g.quat = list(quat)
        g.contype, g.conaffinity = _ALMOHADILLA
        g.friction = list(FRICCION_ALMOHADILLA)
        g.condim = CONDIM_ALMOHADILLA
        g.solref = list(SOLREF_ALMOHADILLA)
        g.solimp = list(SOLIMP_ALMOHADILLA)
        g.priority = 1  # sus parámetros mandan en el contacto con la aleta o el mango
        g.group = 1
        return g

    almohadilla(pinza, "almohadilla_fija", (X_DEDO_FIJO - GROSOR_ALMOHADILLA, 0.0, zc))
    # Dedo móvil: pose de la almohadilla en el marco de la mordaza para que con Q_PARALELA quede paralela a la fija
    mordaza = spec.body("moving_jaw_so101_v1")
    p_m = np.asarray(mordaza.pos, dtype=float)
    q_m = np.asarray(mordaza.quat, dtype=float)
    R0 = np.zeros(9)
    mujoco.mju_quat2Mat(R0, q_m)
    R_gm = R0.reshape(3, 3) @ escena.rot_z(np.degrees(Q_PARALELA))  # giro de la articulación (eje z de la mordaza)
    centro_g = np.array([X_DEDO_FIJO + HUECO_PARALELO + GROSOR_ALMOHADILLA, 0.0, zc])
    almohadilla(mordaza, "almohadilla_movil", R_gm.T @ (centro_g - p_m), _quat(R_gm.T))
    # mismos ejes que `gripperframe` (x = aproximación, z = cierre)
    pinza.add_site(name="punta_pinza", pos=list(PUNTA_PINZA), quat=list(spec.site("gripperframe").quat),
                   size=[0.002, 0, 0], rgba=[0, 0.6, 1, 0])
    # Sitio de la herramienta que lleve la pinza (se coloca al medir el agarre; z = mango → punta)
    pinza.add_site(name="herramienta", pos=[0, 0, 0], size=[0.0015, 0, 0], rgba=[1, 0, 1, 0])


def _camaras_montaje(spec):
    w = spec.worldbody
    cen = w.add_camera(name="cenital", pos=list(escena.CAMARA_CENITAL_POS), fovy=escena.FOVY_CENITAL)
    cen.alt.type = mujoco.mjtOrientation.mjORIENTATION_XYAXES
    cen.alt.xyaxes = escena._mirar(escena.CAMARA_CENITAL_POS, escena.CAMARA_CENITAL_OBJETIVO,
                                   np.array([1.0, 0.0, 0.0])).tolist()
    # Muñeca: donde va la cámara del soporte oficial, mirando entre las yemas de los dedos un poco más allá
    pos = np.array(CAMARA_MUNECA_EN_PINZA)
    objetivo = np.array(OBJETIVO_MUNECA_EN_PINZA)
    cam = spec.body("gripper").add_camera(name="muneca", pos=list(pos), fovy=escena.FOVY_MUNECA)
    cam.alt.type = mujoco.mjtOrientation.mjORIENTATION_XYAXES
    cam.alt.xyaxes = escena._mirar(pos, objetivo, np.array([0.0, 0.0, 1.0])).tolist()


CAMARA_MUNECA_EN_PINZA = (0.0, 0.048, -0.045)  # m, marco del cuerpo `gripper` (sobre el soporte oficial)
OBJETIVO_MUNECA_EN_PINZA = (-0.004, 0.0, -0.135)


def _imanes(spec):
    for junta in TipoJunta:
        q = _quat(R_MOVIL_EN_BASE)
        p = POS_MOVIL_EN_BASE[junta] * MM
        e = spec.add_equality(name=f"iman_{junta.value}", type=mujoco.mjtEq.mjEQ_WELD,
                              objtype=mujoco.mjtObj.mjOBJ_BODY, name1="base_montaje", name2="chapa_movil")
        e.active = False
        e.data = [0, 0, 0, *p, *q, 1.0, 0.0]
        e.solref = [REF_IMAN, 1.0]
    # Asiento de la antorcha en su soporte (chaveta + tubo): pose de la antorcha en el marco del soporte
    R, p = pose_soporte()
    Rs = escena.rot_z(giro_soporte())
    s = c.SOPORTE_ANTORCHA
    p_rel = Rs.T @ (p - np.array([s["x"], s["y"], 0.0])) * MM
    e = spec.add_equality(name="asiento_antorcha", type=mujoco.mjtEq.mjEQ_WELD, objtype=mujoco.mjtObj.mjOBJ_BODY,
                          name1="soporte_antorcha", name2="antorcha")
    e.active = False
    e.data = [0, 0, 0, *p_rel, *_quat(Rs.T @ R), 1.0, 0.0]
    e.solref = [REF_IMAN, 1.0]


def construir_spec_montaje(simplificar_mm: float | None = 1.5) -> mujoco.MjSpec:
    spec = escena.spec_robot_y_mesa(simplificar_mm)
    spec.modelname = "lewelder_montaje"
    # Sin esto el rozamiento blando de MuJoCo deja que la chapa "fluya" en la pinza (~2°/s) al girarla
    spec.option.noslip_iterations = NOSLIP
    _base(spec)
    _chapa_movil(spec)
    _antorcha_suelta(spec)
    _soporte(spec)
    _almohadillas(spec)
    _imanes(spec)
    _camaras_montaje(spec)
    return spec


def construir_modelo_montaje(simplificar_mm: float | None = 1.5) -> tuple[mujoco.MjModel, mujoco.MjSpec]:
    spec = construir_spec_montaje(simplificar_mm)
    return spec.compile(), spec


# --- entorno --------------------------------------------------------------------------------------------------------
def junta_de_orden(orden: str):
    return ORDENES_MONTAR.get(orden)


class EntornoMontaje(EntornoSoldadura):
    """SO-101 en la mesa de montaje: misma interfaz (estado, acción y cámaras) que `EntornoSoldadura`.

    `reset(tarea, semilla)` prepara la mesa para la orden: para montar, la chapa móvil tumbada en una pose aleatoria
    de `ZONA_LIBRE`; para señalar y soldar, la junta ya montada (T o esquina, al azar o la pedida). La antorcha
    siempre empieza en su soporte. `exito(tarea)` dice si la orden se ha cumplido.
    """

    def __init__(self, resolucion: tuple[int, int] = RESOLUCION, render: bool = True, sombras: bool = True):
        self.modelo, _ = construir_modelo_montaje()
        self.datos = mujoco.MjData(self.modelo)
        self.cin = Cinematica(self.modelo, sitio_pose="gripperframe")
        self.ancho, self.alto = resolucion
        self.render = render
        self.sombras = sombras
        self._renderer: mujoco.Renderer | None = None
        self.qadr = self.cin.qadr
        m = self.modelo
        self.sitio_punta = m.site("punta_antorcha").id
        self.sitio_pinza = m.site("punta_pinza").id
        self.sitio_herramienta = m.site("herramienta").id
        self.b_movil = m.body("chapa_movil").id
        self.b_antorcha = m.body("antorcha").id
        self.b_pinza = m.body("gripper").id
        self.adr_movil = int(m.jnt_qposadr[m.joint("chapa_movil_libre").id])
        self.adr_antorcha = int(m.jnt_qposadr[m.joint("antorcha_libre").id])
        self.dadr_movil = int(m.jnt_dofadr[m.joint("chapa_movil_libre").id])
        self.dadr_antorcha = int(m.jnt_dofadr[m.joint("antorcha_libre").id])
        self.eq_iman = {j: m.equality(f"iman_{j.value}").id for j in TipoJunta}
        self.eq_asiento = m.equality("asiento_antorcha").id
        # Choques del brazo: geoms del brazo (cuerpos del SO-101) contra la escena fija y contra los objetos sueltos
        robot = {m.body(n).id for n in ("base", "shoulder", "upper_arm", "lower_arm", "wrist", "gripper",
                                        "moving_jaw_so101_v1", "wrist_camera_mount", "wrist_camera")}
        self.geoms_brazo = {g for g in range(m.ngeom) if m.geom_bodyid[g] in robot and m.geom_contype[g] == 1}
        mordazas = {m.body("gripper").id, m.body("moving_jaw_so101_v1").id}
        self.geoms_dedos = {g for g in self.geoms_brazo if m.geom_bodyid[g] in mordazas}
        self.geoms_escena = {g for g in range(m.ngeom) if (m.geom_contype[g], m.geom_conaffinity[g]) == _ESCENA
                             and m.geom_bodyid[g] not in robot}
        self.choques: dict[str, int] = {}
        self.geoms_almohadillas = {m.geom("almohadilla_fija").id, m.geom("almohadilla_movil").id}
        self.geoms_movil = {g for g in range(m.ngeom) if m.geom_bodyid[g] == self.b_movil}
        self.geoms_antorcha = {g for g in range(m.ngeom) if m.geom_bodyid[g] == self.b_antorcha}
        self.j_pinza = int(m.jnt_qposadr[m.joint("gripper").id])
        self.tarea = c.orden_montar(TipoJunta.T)
        self.junta: TipoJunta | None = None  # junta que hay montada (o la que se pide montar)
        self.junta_cerrada: TipoJunta | None = None
        self.tramos_senalados: set[int] = set()
        self.tramos_soldados: set[int] = set()
        self.pose_inicial_chapa: tuple[float, float, float] | None = None
        self.t = 0.0
        self.dt = 1.0 / c.FPS_DATASET
        self.anclaje = "montaje"  # compatibilidad con utilidades de la v1
        self.tipo = c.TipoPieza.T
        assert abs(self.modelo.opt.timestep * SUBPASOS - self.dt) < 1e-9

    # --- colocar objetos -------------------------------------------------------------------------------------
    def _poner_libre(self, adr: int, dadr: int, R: np.ndarray, p_mm: np.ndarray) -> None:
        self.datos.qpos[adr:adr + 3] = p_mm * MM
        self.datos.qpos[adr + 3:adr + 7] = _quat(R)
        self.datos.qvel[dadr:dadr + 6] = 0.0

    def colocar_chapa_tumbada(self, x: float, y: float, giro: float) -> None:
        R, p = pose_tumbada(x, y, giro)
        self._poner_libre(self.adr_movil, self.dadr_movil, R, p)
        self.pose_inicial_chapa = (float(x), float(y), float(giro))

    def colocar_chapa_montada(self, junta) -> None:
        R, p = pose_montada(junta)
        self._poner_libre(self.adr_movil, self.dadr_movil, R, p)
        self._activar_iman(TipoJunta(junta))

    def colocar_antorcha_en_soporte(self) -> None:
        R, p = pose_soporte()
        self._poner_libre(self.adr_antorcha, self.dadr_antorcha, R, p + np.array([0.0, 0.0, 0.2]))
        self.datos.eq_active[self.eq_asiento] = 1

    def _activar_iman(self, junta: TipoJunta) -> None:
        for j, i in self.eq_iman.items():
            self.datos.eq_active[i] = 1 if j is junta else 0
        self.junta_cerrada = junta

    @staticmethod
    def pose_aleatoria_chapa(rng: np.random.Generator) -> tuple[float, float, float]:
        """Pose (x, y, giro) de la chapa tumbada al azar en `ZONA_LIBRE`, con la aleta al alcance de la pinza."""
        z = c.ZONA_LIBRE
        for _ in range(1000):
            x, y, giro = rng.uniform(*z["x"]), rng.uniform(*z["y"]), rng.uniform(*z["giro"])
            if aleta_al_alcance(x, y, giro):
                return float(x), float(y), float(giro)
        raise RuntimeError("ZONA_LIBRE sin poses al alcance")

    # --- ciclo -----------------------------------------------------------------------------------------------
    def reset(self, tarea: str = c.orden_montar(TipoJunta.T), semilla: int | None = None, junta=None,
              pose_chapa: tuple[float, float, float] | None = None, q_inicial=None) -> dict:
        """Prepara la mesa para `tarea` (una orden del vocabulario) y pone el brazo en reposo.

        Con `semilla` varían la pose de la chapa tumbada, la junta montada (si no se pide) y la postura de reposo.
        """
        if tarea not in c.ORDENES:
            raise ValueError(f"Orden desconocida: {tarea}")
        if tarea not in ORDENES_NUCLEO:
            raise NotImplementedError(f"Orden de nivel {c.ORDENES[tarea]} aún sin simular: {tarea}")
        self.tarea = tarea
        rng = np.random.default_rng(semilla)
        mujoco.mj_resetData(self.modelo, self.datos)
        self.datos.eq_active[:] = 0
        self.junta_cerrada = None
        self.choques = {}
        self.tramos_senalados, self.tramos_soldados = set(), set()
        self.pose_inicial_chapa = None
        self.colocar_antorcha_en_soporte()
        junta_pedida = junta_de_orden(tarea)
        if junta_pedida is not None:
            self.junta = junta_pedida
            if pose_chapa is None:
                pose_chapa = self.pose_aleatoria_chapa(rng) if semilla is not None else centro_zona_libre()
            self.colocar_chapa_tumbada(*pose_chapa)
        else:
            if junta is None:
                junta = list(TipoJunta)[int(rng.integers(len(TipoJunta)))] if semilla is not None else TipoJunta.T
            self.junta = TipoJunta(junta)
            self.colocar_chapa_montada(self.junta)
        self.tipo = c.TipoPieza.T
        if q_inicial is None:
            q_inicial = REPOSO.copy()
            if semilla is not None:
                q_inicial[:5] += rng.normal(0.0, 4.0, 5)
        q = lerobot_a_rad(q_inicial)
        self.datos.qpos[self.qadr] = q
        self.datos.ctrl[:6] = q
        mujoco.mj_forward(self.modelo, self.datos)
        # Que la chapa y la antorcha se asienten antes del primer fotograma
        for _ in range(int(0.3 / self.modelo.opt.timestep)):
            mujoco.mj_step(self.modelo, self.datos)
        self.datos.qpos[self.qadr] = q
        self.datos.qvel[:] = 0.0
        mujoco.mj_forward(self.modelo, self.datos)
        self.t = 0.0
        return self.observacion()

    def step(self, accion) -> dict:
        if isinstance(accion, dict):
            from sim.entorno import NOMBRES_MOTORES
            accion = [accion[n] for n in NOMBRES_MOTORES]
        q = lerobot_a_rad(np.asarray(accion, dtype=float))
        rangos = self.modelo.actuator_ctrlrange[:6]
        self.datos.ctrl[:6] = np.clip(q, rangos[:, 0], rangos[:, 1])
        for _ in range(SUBPASOS // 4):
            mujoco.mj_step(self.modelo, self.datos, nstep=4)
            self._comprobar_imanes()
        self._registrar_choques()
        self.t += self.dt
        self._seguir_tareas()
        return self.observacion()

    # --- imanes ----------------------------------------------------------------------------------------------
    def _toca(self, geoms_a: set[int], geoms_b: set[int]) -> bool:
        d = self.datos
        for i in range(d.ncon):
            g1, g2 = d.contact[i].geom1, d.contact[i].geom2
            if (g1 in geoms_a and g2 in geoms_b) or (g2 in geoms_a and g1 in geoms_b):
                return True
        return False

    def _pinzada(self, geoms: set[int]) -> bool:
        """El objeto está cogido si lo tocan las dos almohadillas (apoyado en un solo dedo no cuenta)."""
        return all(self._toca({g}, geoms) for g in self.geoms_almohadillas)

    def chapa_agarrada(self) -> bool:
        return self._pinzada(self.geoms_movil)

    def antorcha_agarrada(self) -> bool:
        return self._pinzada(self.geoms_antorcha)

    def error_montaje(self, junta) -> tuple[float, float]:
        """(mm, grados) entre la chapa móvil y su sitio en `junta`."""
        R, p = self.pose_movil()
        R0, p0 = pose_montada(junta)
        return float(np.linalg.norm(p - p0)), angulo_entre(R, R0)

    def _registrar_choques(self) -> None:
        """Cuenta los fotogramas con contacto del brazo contra la mesa, la base o el soporte (por pareja de geoms)."""
        d, m = self.datos, self.modelo
        vistos = set()
        for i in range(d.ncon):
            g1, g2 = d.contact[i].geom1, d.contact[i].geom2
            if g1 in self.geoms_escena:
                g1, g2 = g2, g1
            if g1 in self.geoms_brazo and g2 in self.geoms_escena and d.contact[i].dist < -0.0002:
                vistos.add(f"{m.body(m.geom_bodyid[g1]).name} / {m.geom(g2).name or m.body(m.geom_bodyid[g2]).name}")
        for k in vistos:
            self.choques[k] = self.choques.get(k, 0) + 1

    def _comprobar_imanes(self) -> None:
        d = self.datos
        if d.eq_active[self.eq_asiento]:
            if self.antorcha_agarrada():  # al cogerla, la chaveta deja de sujetarla
                d.eq_active[self.eq_asiento] = 0
        elif not self.antorcha_agarrada():
            R, p = self.pose_antorcha()
            R0, p0 = pose_soporte()
            if np.linalg.norm(p - p0) < ASIENTO_MM and angulo_entre(R, R0) < ASIENTO_GRADOS:
                d.eq_active[self.eq_asiento] = 1
        if self.junta_cerrada is not None or self.chapa_agarrada():
            return
        for junta in TipoJunta:
            mm, grados = self.error_montaje(junta)
            if mm < CAPTURA_MM and grados < CAPTURA_GRADOS:
                self._activar_iman(junta)
                return

    # --- poses (para el reconocimiento) ----------------------------------------------------------------------
    def pose_movil(self) -> tuple[np.ndarray, np.ndarray]:
        """(giro 3x3, origen en mm) de la chapa móvil en la mesa."""
        d = self.datos
        return d.xmat[self.b_movil].reshape(3, 3).copy(), d.xpos[self.b_movil] / MM

    def pose_antorcha(self) -> tuple[np.ndarray, np.ndarray]:
        d = self.datos
        return d.xmat[self.b_antorcha].reshape(3, 3).copy(), d.xpos[self.b_antorcha] / MM

    def poses_chapas(self) -> dict:
        """Pose de cada chapa en la mesa (mm): base (centro de su cara superior) y móvil (centro del canto inferior),
        con su ArUco. Es la verdad del terreno para el reconocimiento estéreo."""
        Rm, pm = self.pose_movil()
        return {
            "base": {"R": rotacion_base(), "p": origen_base(), "aruco": c.ID_BASE},
            "movil": {"R": Rm, "p": pm, "aruco": dict(c.IDS_MOVIL)},
        }

    # --- seguimiento de señalar y soldar ---------------------------------------------------------------------
    def punta_pinza_en_mesa(self) -> np.ndarray:
        return self.datos.site_xpos[self.sitio_pinza] / MM

    def pinza_cerrada(self) -> bool:
        return bool(self.datos.qpos[self.j_pinza] < 0.0)

    def _seguir_tareas(self) -> None:
        if self.junta_cerrada is None:
            return
        j = self.junta_cerrada
        x, y, z = mesa_a_cordon(j, self.punta_pinza_en_mesa())
        if self.pinza_cerrada() and 0 <= x <= c.LONGITUD_CORDON and np.hypot(y, z) < DISTANCIA_SENALAR:
            self.tramos_senalados.add(min(c.N_TRAMOS - 1, int(x / c.TAMANO_TRAMO)))
        x, y, z = mesa_a_cordon(j, self.punta_en_mesa())
        tol = c.TOLERANCIAS[c.NIVEL_JURADO]
        if 0 <= x <= c.LONGITUD_CORDON and abs(y) <= tol and abs(z - c.ALTURA_PUNTA) <= tol:
            self.tramos_soldados.add(min(c.N_TRAMOS - 1, int(x / c.TAMANO_TRAMO)))

    def antorcha_en_soporte(self) -> bool:
        """La antorcha está asentada en el tubo (fijada por la chaveta) y la pinza no la tiene."""
        return bool(self.datos.eq_active[self.eq_asiento]) and not self.antorcha_agarrada()

    # --- éxito -----------------------------------------------------------------------------------------------
    def exito(self, tarea: str | None = None) -> bool:
        tarea = self.tarea if tarea is None else tarea
        junta = junta_de_orden(tarea)
        if junta is not None:
            if self.junta_cerrada is not junta or self.chapa_agarrada():
                return False
            mm, grados = self.error_montaje(junta)
            return mm < ERROR_CERRADA_MM and grados < ERROR_CERRADA_GRADOS
        if tarea == ORDEN_SENALAR:
            return len(self.tramos_senalados) >= FRACCION_SENALAR * c.N_TRAMOS
        if tarea == ORDEN_SOLDAR:
            return len(self.tramos_soldados) == c.N_TRAMOS and self.antorcha_en_soporte()
        raise NotImplementedError(tarea)

    def info(self) -> dict:
        """Resumen del estado de la mesa (para registros y pruebas)."""
        out = {"tarea": self.tarea, "junta": self.junta.value if self.junta else None,
               "junta_cerrada": self.junta_cerrada.value if self.junta_cerrada else None,
               "tramos_senalados": len(self.tramos_senalados), "tramos_soldados": len(self.tramos_soldados),
               "antorcha_en_soporte": self.antorcha_en_soporte(), "chapa_agarrada": self.chapa_agarrada()}
        if self.junta is not None:
            mm, grados = self.error_montaje(self.junta)
            out.update(error_montaje_mm=round(mm, 2), error_montaje_grados=round(grados, 2))
        return out

    # --- herramienta en la pinza -----------------------------------------------------------------------------
    def medir_herramienta(self, objeto: str = "antorcha") -> None:
        """Copia en el sitio `herramienta` de la pinza la pose real (relativa a la pinza) de lo que lleva cogido: la
        punta de la antorcha ("antorcha") o el origen de la chapa móvil ("movil"). Así la IK planifica con el agarre
        de verdad, con sus pequeños deslizamientos."""
        d, m = self.datos, self.modelo
        Rg, pg = d.xmat[self.b_pinza].reshape(3, 3), d.xpos[self.b_pinza]
        if objeto == "antorcha":
            Rp, pp = d.site_xmat[self.sitio_punta].reshape(3, 3), d.site_xpos[self.sitio_punta]
        else:
            Rp, pp = d.xmat[self.b_movil].reshape(3, 3), d.xpos[self.b_movil]
        m.site_pos[self.sitio_herramienta] = Rg.T @ (pp - pg)
        m.site_quat[self.sitio_herramienta] = _quat(Rg.T @ Rp)
        m.site_sameframe[self.sitio_herramienta] = 0  # si no, MuJoCo copia la pose del cuerpo e ignora lo de arriba

    def agarre_medido(self, objeto: str) -> tuple[np.ndarray, np.ndarray]:
        """Pose real de `gripperframe` en el marco del objeto ("movil" o "antorcha"), en mm."""
        d = self.datos
        s = self.modelo.site("gripperframe").id
        Rs, ps = d.site_xmat[s].reshape(3, 3), d.site_xpos[s] / MM
        Ro, po = self.pose_movil() if objeto == "movil" else self.pose_antorcha()
        return Ro.T @ Rs, Ro.T @ (ps - po)

    def punta_en_pieza(self) -> tuple[float, float, float]:
        """Punta de la antorcha en el marco del cordón de la junta montada (o pedida)."""
        x, y, z = mesa_a_cordon(self.junta or TipoJunta.T, self.punta_en_mesa())
        return float(x), float(y), float(z)

    def eje_antorcha_en_pieza(self) -> np.ndarray:
        eje = self.datos.site_xmat[self.sitio_punta].reshape(3, 3)[:, 2]
        return marco_cordon(self.junta or TipoJunta.T)[0].T @ eje


DISTANCIA_SENALAR = 15.0  # mm: la punta de la pinza cuenta como señalando un tramo a menos de esto del cordón
FRACCION_SENALAR = 0.8  # tramos señalados para dar la orden por cumplida
RADIO_ALCANCE_ALETA = (130.0, 280.0)  # mm: radio en la mesa donde la pinza coge la aleta en vertical


def posicion_aleta_tumbada(x: float, y: float, giro: float) -> np.ndarray:
    """Centro de la aleta (mm, mesa) de la chapa tumbada en (x, y, giro)."""
    R, o = pose_tumbada(x, y, giro)
    return o + R @ np.array([_GEO["aleta_x"], ALETA_Y, -(c.GROSOR_CHAPA / 2 + _GEO["aleta_alto"] / 2)])


def aleta_al_alcance(x: float, y: float, giro: float) -> bool:
    """La aleta queda en el anillo de alcance y la chapa no pisa la base del robot."""
    p = posicion_aleta_tumbada(x, y, giro)
    r = float(np.hypot(p[0], p[1]))
    if not RADIO_ALCANCE_ALETA[0] <= r <= RADIO_ALCANCE_ALETA[1]:
        return False
    R, o = pose_tumbada(x, y, giro)
    for sx in (-1, 1):
        for sy in (0, 1):
            esq = o + R @ np.array([sx * c.LARGO_MOVIL / 2, sy * c.ALTO_MOVIL, 0.0])
            if np.hypot(esq[0], esq[1]) < 110.0:
                return False
    return True


def centro_zona_libre() -> tuple[float, float, float]:
    z = c.ZONA_LIBRE
    return float(np.mean(z["x"])), float(np.mean(z["y"])), 0.0


__all__ = ["EntornoMontaje", "construir_modelo_montaje", "pose_montada", "pose_tumbada", "marco_cordon",
           "mesa_a_cordon", "cordon_a_mesa", "pose_soporte", "agarre_aleta", "agarre_mango", "rad_a_lerobot"]
