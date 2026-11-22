"""Escena MuJoCo de Garbi: SO-101 con boca de aspiración, alfombrilla azul, tabla clara, viruta y taladro (sin ArUco).

Se apoya en `sim.escena.spec_robot_y_mesa` (SO-101 oficial, luces, mesa) y añade lo propio de Garbi:

- **Boca de aspiración** fija en la pinza: un tubo de Ø 35 mm que sale del punto de agarre a lo largo del eje de
  aproximación (hacia los dedos) y termina en el sitio `boca` (eje z = hacia donde mira la boca).
- **Alfombrilla** azul lisa: sus 4 esquinas dan el marco de la mesa a la visión (`garbi.percepcion`).
- **Tabla** de madera natural clara (sin vinilo, solución final) con una **pegatina** magenta en una esquina, que
  resuelve el giro de 180°: cuerpo mocap (se mueve sin recompilar).
- **Anillo verde** en la punta de la boquilla lateral, para calibrar el robot con la cámara de arriba.
- **Agujeros** y **viruta**: cuerpos mocap preasignados (`MAX_AGUJEROS`, `MAX_VIRUTA`) que se esconden bajo la mesa y
  se colocan cuando hace falta. La viruta no colisiona: la física de las partículas no aporta nada a la demo y la
  aspiración se simula con una regla (ver `garbi.mundo`).
- **Taladro** mocap con la bola naranja (marcador) en la tapa y el sitio `punta_broca`, y la mano que lo sujeta (se
  puede esconder para probar «taladro sin mano»: `garbi.mundo.MundoGarbi.soltar_taladro`).
- **Mano libre** (la otra mano de la persona), mocap: `garbi.mundo.MundoGarbi.poner_mano_libre`.
- Cámaras `top` (fija, detrás a la derecha) y `wrist` (en la pinza, mirando a la boca).
"""
from __future__ import annotations

import mujoco
import numpy as np

from garbi import contrato as g
from sim import escena as base

MM = 1e-3
ESCONDITE = (0.0, 0.0, -2.0)  # m, bajo el suelo (fuera de la vista)
CAMARA_ROBOT_LADO = 0.050  # m: la cámara del robot va a un costado del tubo, a esta distancia de su eje
CAMARA_ROBOT_DETRAS_BOCA = 20.0  # mm por detrás de la boca, a lo largo del tubo
_SIN_COLISION = (0, 0)


def _caja(cuerpo, nombre, centro_mm, medio_mm, rgba=None, material=None, colision=True):
    geom = cuerpo.add_geom(name=nombre, type=mujoco.mjtGeom.mjGEOM_BOX,
                           pos=[v * MM for v in centro_mm], size=[v * MM for v in medio_mm])
    if rgba is not None:
        geom.rgba = list(rgba)
    if material is not None:
        geom.material = material
    geom.contype, geom.conaffinity = base._ESCENA if colision else _SIN_COLISION
    return geom


# --- piezas de la escena -----------------------------------------------------------------------------------------
def _alfombrilla(spec):
    w = spec.worldbody
    cx, cy = g.ALFOMBRILLA_CENTRO
    _caja(w, "alfombrilla", (cx, cy, g.ALFOMBRILLA_GROSOR / 2),
          (g.ALFOMBRILLA_TAMANO[0] / 2, g.ALFOMBRILLA_TAMANO[1] / 2, g.ALFOMBRILLA_GROSOR / 2),
          rgba=g.ALFOMBRILLA_RGBA)


def _tabla(spec):
    b = spec.worldbody.add_body(name="tabla", mocap=True, pos=list(ESCONDITE))
    largo, ancho, grueso = g.TABLA_TAMANO
    # El origen del cuerpo es el centro de la cara de arriba
    _caja(b, "tabla_madera", (0, 0, -grueso / 2), (largo / 2, ancho / 2, grueso / 2 - 0.3), rgba=g.TABLA_RGBA_CANTO)
    _caja(b, "tabla_cara", (0, 0, -0.3), (largo / 2, ancho / 2, 0.3), rgba=g.TABLA_RGBA_CARA)
    px, py = g.PEGATINA_EN_TABLA
    _caja(b, "tabla_pegatina", (px, py, 0.1), (g.PEGATINA_LADO / 2, g.PEGATINA_LADO / 2, 0.1), rgba=g.PEGATINA_RGBA,
          colision=False)


def _agujeros(spec):
    for k in range(g.MAX_AGUJEROS):
        b = spec.worldbody.add_body(name=f"agujero_{k}", mocap=True, pos=list(ESCONDITE))
        geom = b.add_geom(name=f"agujero_{k}_g", type=mujoco.mjtGeom.mjGEOM_CYLINDER,
                          size=[g.RADIO_AGUJERO * MM, 0.15 * MM, 0], rgba=[0.02, 0.02, 0.02, 1])
        geom.contype, geom.conaffinity = _SIN_COLISION


def _viruta(spec):
    lado = g.LADO_VIRUTA / 2 * MM
    for k in range(g.MAX_VIRUTA):
        b = spec.worldbody.add_body(name=f"viruta_{k}", mocap=True, pos=list(ESCONDITE))
        geom = b.add_geom(name=f"viruta_{k}_g", type=mujoco.mjtGeom.mjGEOM_BOX, size=[lado, lado, lado * 0.6],
                          rgba=list(g.VIRUTA_RGBA))
        geom.contype, geom.conaffinity = _SIN_COLISION


def _taladro(spec):
    """Taladro de batería en vertical, con la mano que lo sujeta. El origen del cuerpo es la punta de la broca; la
    empuñadura sale hacia +x del cuerpo (hacia la persona)."""
    b = spec.worldbody.add_body(name="taladro", mocap=True, pos=list(ESCONDITE))

    def geom(nombre, tipo, rgba, **kw):
        gg = b.add_geom(name=nombre, type=tipo, rgba=list(rgba), **kw)
        gg.contype, gg.conaffinity = _SIN_COLISION
        return gg

    def cil(nombre, z0, z1, r, rgba):
        return geom(nombre, mujoco.mjtGeom.mjGEOM_CYLINDER, rgba, fromto=[0, 0, z0 * MM, 0, 0, z1 * MM], size=[r * MM, 0, 0])

    z = 0.0
    # broca: cápsula con la punta redondeada justo en el origen (una broca real acaba en punta; con un cilindro de
    # extremo plano la silueta acaba en el borde de la cara de abajo, ~1,6 mm por debajo de la punta vista de lado)
    r_broca = g.DIAMETRO_BROCA / 2
    geom("broca", mujoco.mjtGeom.mjGEOM_CAPSULE, [0.75, 0.75, 0.78, 1],
         fromto=[0, 0, r_broca * MM, 0, 0, (g.LARGO_BROCA - r_broca) * MM], size=[r_broca * MM, 0, 0])
    z += g.LARGO_BROCA
    cil("portabrocas", z, z + g.PORTABROCAS_LARGO, g.PORTABROCAS_DIAMETRO / 2, [0.12, 0.12, 0.12, 1])
    z += g.PORTABROCAS_LARGO
    cil("cuerpo_taladro", z, z + g.CUERPO_LARGO, g.CUERPO_DIAMETRO / 2, g.TALADRO_RGBA); z += g.CUERPO_LARGO
    arriba = z
    # Empuñadura: sale del tercio de arriba del cuerpo hacia la persona, algo inclinada hacia abajo; batería al final
    z_emp = arriba - 40.0
    x0, x1 = g.CUERPO_DIAMETRO / 2 - 5, g.CUERPO_DIAMETRO / 2 + g.EMPUNADURA_LARGO
    geom("empunadura", mujoco.mjtGeom.mjGEOM_CAPSULE, [0.15, 0.15, 0.15, 1],
         fromto=[x0 * MM, 0, z_emp * MM, x1 * MM, 0, (z_emp - 25) * MM], size=[g.EMPUNADURA_ANCHO / 2 * MM, 0, 0])
    bx, by, bz = g.BATERIA_TAMANO
    geom("bateria", mujoco.mjtGeom.mjGEOM_BOX, [0.08, 0.08, 0.08, 1],
         pos=[(x1 + bx / 2 - 10) * MM, 0, (z_emp - 25) * MM], size=[bx / 2 * MM, by / 2 * MM, bz / 2 * MM])
    # Mano y antebrazo de la persona (solo para ver la escena y las oclusiones; sin colisión). El centro de la palma
    # está en MANO_TALADRO_EN_TALADRO; `MundoGarbi.soltar_taladro` los esconde (taladro dejado sin mano).
    piel = list(PIEL_RGBA)
    geom("mano", mujoco.mjtGeom.mjGEOM_ELLIPSOID, piel, pos=[(x0 + 55) * MM, 0, (z_emp - 10) * MM],
         size=[0.045, 0.030, 0.035])
    geom("antebrazo", mujoco.mjtGeom.mjGEOM_CAPSULE, [0.25, 0.35, 0.55, 1],
         fromto=[(x0 + 80) * MM, 0, (z_emp + 5) * MM, (x0 + 260) * MM, 0, (z_emp + 60) * MM], size=[0.033, 0, 0])
    # Marcador para la cámara de arriba: bola naranja sobre un vástago en la tapa de arriba
    cil("vastago_bola", arriba, g.ALTURA_BOLA_SOBRE_PUNTA, 4.0, [0.2, 0.2, 0.2, 1])
    geom("bola_taladro", mujoco.mjtGeom.mjGEOM_SPHERE, g.BOLA_RGBA, pos=[0, 0, g.ALTURA_BOLA_SOBRE_PUNTA * MM],
         size=[g.RADIO_BOLA * MM, 0, 0])
    b.add_site(name="punta_broca", pos=[0, 0, 0], size=[0.002, 0, 0], rgba=[1, 0, 0, 1])


PIEL_RGBA = (0.86, 0.68, 0.55, 1.0)
# Centro de la palma de la mano que sujeta el taladro, en el marco del taladro (origen en la punta de la broca, mm)
MANO_TALADRO_EN_TALADRO = (g.CUERPO_DIAMETRO / 2 - 5 + 55,
                           0.0, g.LARGO_BROCA + g.PORTABROCAS_LARGO + g.CUERPO_LARGO - 40.0 - 10.0)
GEOMS_MANO_TALADRO = ("mano", "antebrazo")


def _mano_libre(spec):
    """La otra mano de la persona (la que no sujeta el taladro), con su antebrazo: cuerpo mocap que mueve la maqueta
    (por ejemplo, para recolocar la madera). El origen es la palma; el antebrazo va hacia la persona (+x)."""
    b = spec.worldbody.add_body(name="mano_libre", mocap=True, pos=list(ESCONDITE))
    piel = list(PIEL_RGBA)
    for nombre, tipo, kw in [
        ("mano_libre_palma", mujoco.mjtGeom.mjGEOM_ELLIPSOID, dict(pos=[0, 0, 0.012], size=[0.05, 0.035, 0.014], rgba=piel)),
        ("mano_libre_dedos", mujoco.mjtGeom.mjGEOM_ELLIPSOID, dict(pos=[-0.055, 0, 0.008], size=[0.03, 0.033, 0.01], rgba=piel)),
        ("mano_libre_brazo", mujoco.mjtGeom.mjGEOM_CAPSULE,
         dict(fromto=[0.04, 0, 0.02, 0.30, 0, 0.16], size=[0.033, 0, 0], rgba=[0.25, 0.35, 0.55, 1])),
    ]:
        gg = b.add_geom(name=nombre, type=tipo, **kw)
        gg.contype, gg.conaffinity = _SIN_COLISION


def _area_de_trabajo(spec):
    """Mesa del hackathon (1200 × 600 × 750) con patas, pértiga de la manguera y la persona al otro lado."""
    w = spec.worldbody
    cx = g.MESA_X_ATRAS + g.MESA_FONDO / 2
    mesa = spec.geom("mesa")
    mesa.pos = [cx * MM, 0, -15 * MM]
    mesa.size = [g.MESA_FONDO / 2 * MM, g.MESA_ANCHO / 2 * MM, 15 * MM]
    mesa.rgba = list(g.MESA_RGBA)
    for sx in (-1, 1):
        for sy in (-1, 1):
            _caja(w, f"pata_{sx}_{sy}", (cx + sx * (g.MESA_FONDO / 2 - 40), sy * (g.MESA_ANCHO / 2 - 40), -390),
                  (20, 20, 360), rgba=[0.3, 0.3, 0.32, 1], colision=False)
    # Pértiga de la manguera: sujeta al borde de atrás, a la izquierda del robot, con un brazo por encima del robot
    _caja(w, "pertiga", (g.MESA_X_ATRAS + 20, 180, 450), (10, 10, 450), rgba=[0.6, 0.6, 0.62, 1], colision=False)
    _caja(w, "pertiga_brazo", (g.MESA_X_ATRAS + 120, 180, 890), (110, 8, 8), rgba=[0.6, 0.6, 0.62, 1], colision=False)
    # Soporte de la cámara de arriba (flexo sujeto al lateral derecho)
    cxs, cys, czs = g.CAMARA_FIJA_POS
    _caja(w, "soporte_camara", (cxs, -g.MESA_ANCHO / 2 + 20, czs / 2), (8, 8, czs / 2), rgba=[0.2, 0.2, 0.2, 1],
          colision=False)
    _caja(w, "soporte_camara_brazo", (cxs, (cys - g.MESA_ANCHO / 2 + 20) / 2, czs + 20),
          (8, abs(cys + g.MESA_ANCHO / 2 - 20) / 2, 8), rgba=[0.2, 0.2, 0.2, 1], colision=False)
    # La persona, de pie al otro lado de la mesa
    px = g.PERSONA_X + 230
    for nombre, tipo, pos, size, rgba in [
        ("persona_tronco", mujoco.mjtGeom.mjGEOM_CAPSULE, (px, 0, 150), (170, 280, 0), [0.25, 0.35, 0.55, 1]),
        ("persona_cabeza", mujoco.mjtGeom.mjGEOM_SPHERE, (px - 20, 0, 600), (100, 0, 0), [0.86, 0.68, 0.55, 1]),
    ]:
        gg = w.add_geom(name=nombre, type=tipo, pos=[v * MM for v in pos], size=[v * MM for v in size], rgba=rgba)
        gg.contype, gg.conaffinity = _SIN_COLISION


def _boca(spec):
    """Boquilla recta atornillada a la pinza, a lo largo de la dirección de las mordazas (-z del sitio `gripperframe`),
    y la cámara del robot en su soporte, mirando por donde aspira."""
    pinza = spec.body("gripper")
    marco = spec.site("gripperframe")
    b = pinza.add_body(name="boca_cuerpo", pos=list(marco.pos), quat=list(marco.quat))
    b.mass = 0.08
    b.inertia = [3e-5, 3e-5, 1e-5]
    b.explicitinertial = True
    r = g.DIAMETRO_BOCA / 2 * MM
    tubo = b.add_geom(name="boca_tubo", type=mujoco.mjtGeom.mjGEOM_CYLINDER,
                      fromto=[0, 0, 0.01, 0, 0, -g.LARGO_MANGO * MM], size=[r, 0, 0], rgba=[0.15, 0.35, 0.85, 1])
    tubo.contype, tubo.conaffinity = base._BRAZO
    # Manguera corrugada: entra por detrás de la boquilla (el resto va colgado de la pértiga)
    manguera = b.add_geom(name="manguera", type=mujoco.mjtGeom.mjGEOM_CYLINDER,
                          fromto=[0, 0, 0.0, 0, 0, 0.09], size=[r * 0.9, 0, 0], rgba=[0.35, 0.35, 0.38, 1])
    manguera.contype, manguera.conaffinity = _SIN_COLISION
    # Sitio en la boca con z = dirección en la que mira la boca (-z del marco): giro de 180° alrededor de x
    b.add_site(name="boca", pos=[0, 0, -g.LARGO_MANGO * MM], quat=[0, 1, 0, 0], size=[0.003, 0, 0],
               rgba=[0, 1, 0, 1])
    # Cámara del robot: a un costado del tubo, cerca de la boca, mirando la broca casi en horizontal. Así queda lejos
    # del eje de la broca (~70 mm) y por debajo del cuerpo del taladro, y el borde de la boca no le tapa la punta.
    # Apunta entre donde queda la punta en el preapunto y al acompañar (marco del soporte; en las posturas de trabajo
    # -x del soporte queda hacia arriba).
    p = np.array([0.0, CAMARA_ROBOT_LADO, -(g.LARGO_MANGO - CAMARA_ROBOT_DETRAS_BOCA) * MM])
    o = np.array([0.012, 0.0, -(g.LARGO_MANGO + g.DISTANCIA_ACOMPANAR + 8) * MM])
    cam = b.add_camera(name="wrist", pos=list(p), fovy=75.0)
    cam.alt.type = mujoco.mjtOrientation.mjORIENTATION_XYAXES
    cam.alt.xyaxes = _mirar(p, o, np.array([-1.0, 0.0, 0.0])).tolist()


def _mirar(pos, objetivo, arriba):
    f = np.asarray(objetivo, float) - np.asarray(pos, float)
    f /= np.linalg.norm(f)
    x = np.cross(f, arriba)
    x /= np.linalg.norm(x)
    y = np.cross(x, f)
    return np.concatenate([x, y])


def _camaras(spec):
    pos = np.asarray(g.CAMARA_FIJA_POS) * MM
    obj = np.asarray(g.CAMARA_FIJA_OBJETIVO) * MM
    cam = spec.worldbody.add_camera(name="top", pos=list(pos), fovy=g.FOVY_FIJA)
    cam.alt.type = mujoco.mjtOrientation.mjORIENTATION_XYAXES
    cam.alt.xyaxes = _mirar(pos, obj, np.array([1.0, 0.0, 0.0])).tolist()
    # Cámaras de observador, solo para ilustrar las situaciones (no las usa Garbi)
    for nombre, p, o in [("vista_lateral", (180, 780, 480), (300, 0, 50)),
                         ("vista_persona", (820, 420, 760), (260, -20, 30)),
                         ("vista_cerca", (470, -320, 260), (330, 0, 30))]:
        p, o = np.asarray(p) * MM, np.asarray(o) * MM
        c = spec.worldbody.add_camera(name=nombre, pos=list(p), fovy=45.0)
        c.alt.type = mujoco.mjtOrientation.mjORIENTATION_XYAXES
        c.alt.xyaxes = _mirar(p, o, np.array([0.0, 0.0, 1.0])).tolist()


# --- montaje lateral (propuesta del usuario, 20-11): boquilla y tubo por el costado derecho, muñeca fija ----------
# La cámara oficial del SO-101 va en su soporte, en el costado izquierdo de la pinza (con la muñeca fija en 0° queda a
# la izquierda del brazo) y mira hacia delante, más allá de las puntas de las mordazas. La boquilla rígida (Ø30 × 40)
# es el final del tubo corrugado: el tubo baja pegado al costado derecho de la pinza y la boca queda junto a las
# mordazas, algo por delante de las puntas y abierta hacia fuera, donde la cámara la ve. El tubo sigue por el costado
# derecho del brazo pasando por la prolongación del eje de cada articulación (así no se separa al girar) y sale por
# detrás de la base: sin pértiga y sin que se retuerza.
BOQUILLA_DIAMETRO, BOQUILLA_LARGO = 30.0, 40.0
TUBO_DIAMETRO = 32.0
TUBO_LADO = 0.050  # m: el tubo corre a esta distancia del plano del brazo, por la derecha
BOCA_ABIERTA = 7.0  # grados que la boca se abre hacia fuera respecto a las mordazas (7° desde el 21-11: la cámara la ve mejor)
BOCA_LATERAL, BOCA_ADELANTE = -70.0, -128.0  # mm: centro de la boca en el marco de la pinza (y: derecha; z: puntas)
# Anillo verde lima en la punta de la boquilla (cinta o pieza impresa): lo ve la cámara de arriba para calibrar. Verde
# lima para no confundirlo con el amarillo del robot ni con el verde oscuro del taladro.
ANILLO_DIAMETRO, ANILLO_LARGO = 35.4, 12.0  # como hardware/garbi/amarre_boca.py (tubo de 29 + pared de 3)
ANILLO_RGBA = (0.35, 0.95, 0.15, 1.0)
# A 70 mm del eje de la pinza la cámara de la muñeca ve la boca y la broca por fuera de las mordazas (a 52 mm las
# mordazas tapan la broca)


def _boca_lateral(spec):
    pinza = spec.body("gripper")
    b = pinza.add_body(name="boca_cuerpo", pos=[0, 0, 0])
    b.mass = 0.05
    b.inertia = [2e-5, 2e-5, 1e-5]
    b.explicitinertial = True
    a = np.radians(BOCA_ABIERTA)
    eje = np.array([0.0, -np.sin(a), -np.cos(a)])  # hacia donde mira la boca (marco de la pinza)
    boca = np.array([-5.0, BOCA_LATERAL, BOCA_ADELANTE]) * MM
    atras = boca - eje * BOQUILLA_LARGO * MM
    g_boq = b.add_geom(name="boca_tubo", type=mujoco.mjtGeom.mjGEOM_CYLINDER, fromto=[*atras, *boca],
                       size=[BOQUILLA_DIAMETRO / 2 * MM, 0, 0], rgba=[0.92, 0.92, 0.90, 1])
    g_boq.contype, g_boq.conaffinity = base._BRAZO
    # anillo verde en la punta: la cámara de arriba lo ve para calibrar el robot respecto a la mesa (M2, paso 3)
    detras_anillo = boca - eje * ANILLO_LARGO * MM
    g_ani = b.add_geom(name="anillo_boca", type=mujoco.mjtGeom.mjGEOM_CYLINDER, fromto=[*detras_anillo, *boca],
                       size=[ANILLO_DIAMETRO / 2 * MM, 0, 0], rgba=list(ANILLO_RGBA))
    g_ani.contype, g_ani.conaffinity = _SIN_COLISION
    b.add_site(name="anillo", pos=list((boca + detras_anillo) / 2), size=[0.003, 0, 0])
    # abrazadera al costado derecho de la pinza
    _caja(b, "abrazadera", (-5.0, (-28.0 + BOCA_LATERAL) / 2, -70.0), (12.0, (BOCA_LATERAL + 28.0) / -2, 8.0),
          rgba=[0.2, 0.2, 0.22, 1], colision=False)
    # sitio en la boca, con z = hacia donde mira
    z = eje
    x = np.array([1.0, 0.0, 0.0])
    y = np.cross(z, x)
    R = np.column_stack([x, y, z])
    q = np.zeros(4)
    mujoco.mju_mat2Quat(q, R.reshape(-1))
    b.add_site(name="boca", pos=list(boca), quat=list(q), size=[0.003, 0, 0])
    return atras / MM  # mm, marco de la pinza: donde empieza el tubo


def _segmento_tubo(cuerpo, nombre, p0_m, p1_m):
    tubo = cuerpo.add_geom(name=nombre, type=mujoco.mjtGeom.mjGEOM_CAPSULE, fromto=[*p0_m, *p1_m],
                           size=[TUBO_DIAMETRO / 2 * MM, 0, 0], rgba=[0.90, 0.90, 0.88, 1])
    tubo.contype, tubo.conaffinity = _SIN_COLISION


def _manguera_brazo(spec, inicio_pinza_mm):
    """Tubo corrugado por el costado derecho del brazo, pasando por la prolongación del eje de cada articulación."""
    modelo = spec.compile()
    datos = mujoco.MjData(modelo)
    mujoco.mj_forward(modelo, datos)
    derecha = np.array([0.0, -1.0, 0.0])

    def signo(articulacion):
        return 1.0 if datos.xaxis[modelo.joint(articulacion).id] @ derecha > 0 else -1.0

    def punto_eje(articulacion):  # en el marco de su propio cuerpo (las articulaciones están en el origen, eje z)
        return np.array([0.0, 0.0, signo(articulacion) * TUBO_LADO])

    def en_padre(hijo: str, p_local):
        cuerpo = spec.body(hijo)
        R = np.zeros(9)
        mujoco.mju_quat2Mat(R, np.asarray(cuerpo.quat, float))
        return np.asarray(cuerpo.pos, float) + R.reshape(3, 3) @ p_local

    # pinza: del principio del tubo en la boquilla, por el costado derecho de la pinza, hacia la muñeca
    p_inicio = np.asarray(inicio_pinza_mm, float) * MM
    p_codo = np.array([-5.0, BOCA_LATERAL, -40.0]) * MM
    _segmento_tubo(spec.body("gripper"), "tubo_pinza", p_inicio, p_codo)
    # la muñeca no gira (wrist_roll fijo en 0): el tramo hasta el eje de wrist_flex va en la pinza
    R = np.zeros(9)
    mujoco.mju_quat2Mat(R, np.asarray(spec.body("gripper").quat, float))
    flex_en_pinza = R.reshape(3, 3).T @ (punto_eje("wrist_flex") - np.asarray(spec.body("gripper").pos, float))
    _segmento_tubo(spec.body("gripper"), "tubo_pinza_muneca", p_codo, flex_en_pinza)
    # antebrazo: del eje de elbow_flex al de wrist_flex
    _segmento_tubo(spec.body("lower_arm"), "tubo_antebrazo", punto_eje("elbow_flex"), en_padre("wrist", punto_eje("wrist_flex")))
    # brazo: del eje de shoulder_lift al de elbow_flex
    _segmento_tubo(spec.body("upper_arm"), "tubo_brazo", punto_eje("shoulder_lift"),
                   en_padre("lower_arm", punto_eje("elbow_flex")))
    # hombro: del eje de shoulder_lift baja hasta el eje de giro (shoulder_pan), y de ahí sale por detrás
    lift_en_hombro = en_padre("upper_arm", punto_eje("shoulder_lift"))
    bajo = np.array([lift_en_hombro[0], lift_en_hombro[1], 0.035])
    eje_pan = np.array([0.0, 0.0, 0.035])
    _segmento_tubo(spec.body("shoulder"), "tubo_hombro", lift_en_hombro, bajo)
    _segmento_tubo(spec.body("shoulder"), "tubo_hombro_eje", bajo, eje_pan)
    hombro_mundo = np.asarray(spec.body("base").pos) + np.asarray(spec.body("shoulder").pos) * [1, 1, 1]
    centro = np.array([hombro_mundo[0], hombro_mundo[1], hombro_mundo[2] - 0.035])
    _segmento_tubo(spec.worldbody, "tubo_salida", centro, [g.MESA_X_ATRAS * MM, centro[1], centro[2]])
    _segmento_tubo(spec.worldbody, "tubo_al_suelo", [g.MESA_X_ATRAS * MM, centro[1], centro[2]],
                   [g.MESA_X_ATRAS * MM - 0.05, centro[1], -0.70])


def _camara_muneca_oficial(spec):
    """Cámara en el soporte oficial del SO-101 (mira hacia delante, más allá de las puntas de las mordazas)."""
    spec.body("wrist_camera").add_camera(name="wrist", pos=[0, 0, 0], quat=[0, 1, 0, 0], fovy=75.0)


MONTAJE = "mordazas"  # «lateral»: boquilla y tubo por el costado derecho (propuesta del 20-11, en estudio); «mordazas»: el anterior


def construir_spec(simplificar_mm: float | None = 1.5, montaje: str | None = None) -> mujoco.MjSpec:
    spec = base.spec_robot_y_mesa(simplificar_mm)
    spec.modelname = "garbi"
    spec.visual.global_.offwidth = 1920
    spec.visual.global_.offheight = 1080
    _area_de_trabajo(spec)
    _mano_libre(spec)
    _alfombrilla(spec)
    _tabla(spec)
    _agujeros(spec)
    _viruta(spec)
    _taladro(spec)
    if (montaje or MONTAJE) == "lateral":
        inicio = _boca_lateral(spec)
        _camara_muneca_oficial(spec)
        _camaras(spec)
        _manguera_brazo(spec, inicio)
    else:
        _boca(spec)
        _camaras(spec)
    for sitio in spec.sites:  # los puntos de control no se ven en las imágenes
        sitio.rgba = [0, 0, 0, 0]
    return spec


def construir_modelo(simplificar_mm: float | None = 1.5, montaje: str | None = None) -> mujoco.MjModel:
    return construir_spec(simplificar_mm, montaje).compile()
