"""Percepción de Garbi sin ArUco (M2 y M3) contra la verdad de la simulación, con imágenes renderizadas a 640 × 480.

La percepción solo recibe imágenes, la postura del robot y el tiempo; la verdad de la simulación solo se usa aquí para
medir el error. Objetivos de la especificación técnica (tabla M3 y M2):

- cámara de arriba con las esquinas del tapete: ±2 mm en la mesa;
- madera clara (sin vinilo, con pegatina): ±2 mm, ±1°, movida y girada dentro del tapete y con oclusiones;
- manos (color de piel en la simulación) y taladro agarrado (mano + taladro; ni la mano sola ni el taladro solo);
- marcador del taladro: ±15 mm;
- punta de la broca con la cámara de la muñeca: ±2 mm (a ~60-120 mm);
- calibración del robot con el anillo verde: < 4 mm en 5 posturas nuevas.

Necesita render sin pantalla (MUJOCO_GL=egl u osmesa).
"""
import cv2
import numpy as np
import pytest

from garbi import calibracion as C
from garbi import contrato as g
from garbi import percepcion as P
from garbi import tipos as g_tipos
from garbi.tipos import HZ_PERCEPCION

RES = P.RESOLUCION


# --- sin render ----------------------------------------------------------------------------------------------------
def test_clavada_aproximada_desde_arriba():
    """Respaldo de la muñeca: la bola baja ≥ 25 mm, se para 0,4 s y queda baja → apoyada; quieta en el aire, no; con
    la muñeca viendo la punta en el aire, tampoco."""
    def secuencia(alturas, quieto_desde, aire=None):
        per = P.Percepcion()
        per._aire_muneca = aire
        sale = []
        for k, h in enumerate(alturas):
            t = k / HZ_PERCEPCION
            ta = g_tipos.Taladro(True, np.zeros(2), quieto_desde=quieto_desde(t))
            sale.append(per._apoyo_por_arriba(t, h, ta))
        return sale

    bajar = [60.0] * 5 + [45.0, 30.0, 15.0] + [10.0] * 10  # quieto desde la 8.ª lectura
    quieto = lambda t: 8 / HZ_PERCEPCION if t >= 8 / HZ_PERCEPCION else None  # noqa: E731
    s = secuencia(bajar, quieto)
    assert not any(s[:13]) and s[-1]
    assert not any(secuencia([60.0] * 20, lambda t: 0.0))  # quieta en el aire
    assert not any(secuencia(bajar, quieto, aire=0.9))  # la muñeca la acaba de ver en el aire


def test_giro_cercano_resuelve_la_ambiguedad_de_180():
    assert P._giro_cercano(3.0, 0.0) == pytest.approx(3.0)
    assert abs(((P._giro_cercano(3.0, 178.0) - 183.0) + 180) % 360 - 180) < 1e-9
    assert abs(((P._giro_cercano(-87.0, 90.0) - 93.0) + 180) % 360 - 180) < 1e-9


def test_ajustar_rectangulo_con_un_lado_tapado():
    rng = np.random.default_rng(0)
    verdad = np.array([355.0, -12.0, 6.0])
    hx, hy = g.TABLA_TAMANO[0] / 2, g.TABLA_TAMANO[1] / 2
    lados = [np.column_stack([np.full(60, hx), np.linspace(-hy, hy, 60)]),
             np.column_stack([np.full(60, -hx), np.linspace(-hy, hy, 60)]),
             np.column_stack([np.linspace(-hx, hx, 40), np.full(40, hy)])]  # el cuarto lado, tapado
    loc = np.vstack(lados) + rng.normal(0, 0.3, (160, 2))
    loc[:15] += [6.0, 0.0]  # un objeto encima de un lado
    pts = g.PoseTabla(*verdad).a_mesa(loc)
    par, _ = P._ajustar_rectangulo(pts, verdad + [4.0, -3.0, 2.0])
    assert np.hypot(*(par[:2] - verdad[:2])) < 0.5 and abs(par[2] - verdad[2]) < 0.2


def test_ajustar_base_recupera_la_pose_de_la_base():
    """Calibración del robot con datos sintéticos: base desplazada y girada, píxeles con ruido de 0,3 px."""
    K = P.intrinsecas(P.FOVY_TOP)
    from garbi.escena import _mirar

    pos = np.array(g.CAMARA_FIJA_POS, float)
    xy = _mirar(pos, np.array(g.CAMARA_FIJA_OBJETIVO, float), np.array([1.0, 0.0, 0.0])).reshape(2, 3)
    Rc = np.column_stack([xy[0], xy[1], np.cross(xy[0], xy[1])]) @ np.diag([1.0, -1.0, -1.0])
    cam = P.CamaraMesa(K, Rc.T, -Rc.T @ pos)
    verdad = C.PoseBase(6.0, -4.0, 1.5)
    rng = np.random.default_rng(1)
    p_robot = np.column_stack([rng.uniform(260, 460, 9), rng.uniform(-120, 120, 9), rng.uniform(40, 90, 9)])
    uv = cam.proyectar(verdad.a_mesa(p_robot)) + rng.normal(0, 0.3, (9, 2))
    base, residuos = C.ajustar_base(p_robot, uv, cam)
    assert np.hypot(base.x - verdad.x, base.y - verdad.y) < 1.0 and abs(base.giro - verdad.giro) < 0.2
    assert residuos.max() < 1.5


def test_seguidor_taladro_quieto_y_velocidad():
    s = P.SeguidorTaladro()
    madera = g.PoseTabla(360.0, 0.0, 0.0)
    t, dt = 0.0, 1 / 15
    for _ in range(10):  # se mueve a 60 mm/s
        tal = s.actualizar(t, np.array([300.0 + 60.0 * t, 0.0]), madera)
        t += dt
    assert tal.visible and tal.quieto_desde is None and abs(tal.velocidad - 60.0) < 3.0 and tal.en_zona
    x = 300.0 + 60.0 * t
    quieto = None
    for _ in range(12):
        tal = s.actualizar(t, np.array([x, 0.0]), madera)
        if quieto is None and tal.quieto_desde is not None:
            quieto = t
        t += dt
    assert tal.velocidad < P.VELOCIDAD_QUIETO and tal.quieto_desde is not None
    assert quieto is not None and quieto - tal.quieto_desde >= 0.15  # tarda la ventana en decidir que está quieto
    for _ in range(4):  # la mediana de 0,3 s no se cree un salto suelto, pero sí uno que se mantiene
        tal = s.actualizar(t, np.array([600.0, 300.0]), madera)
        t += dt
    assert not tal.en_zona
    assert not s.actualizar(t, None, madera).visible


# --- con render -----------------------------------------------------------------------------------------------------
@pytest.fixture(scope="module")
def mundo():
    from garbi.lateral import APARCADO
    from garbi.mundo import MundoGarbi

    m = MundoGarbi(render=True, montaje="lateral")
    try:
        m.reset(0, q_inicial=APARCADO)
        m.imagen("top", RES)
    except Exception as e:  # sin librerías de render
        pytest.skip(f"no hay render sin pantalla: {e}")
    return m


@pytest.fixture(scope="module")
def cam(mundo):
    from garbi.lateral import APARCADO

    mundo.reset(0, q_inicial=APARCADO)
    c = P.calibrar_camara_arriba(mundo.imagen("top", RES))
    assert c is not None
    return c


def _verdad_camara(m):
    R, t = m.pose_camara("top")
    return P.CamaraMesa(P.intrinsecas(P.FOVY_TOP), R, t)


def test_camara_de_arriba_con_las_esquinas_del_tapete(mundo, cam):
    """Pose de la cámara con el tapete (sin ArUco): centro a < 3 mm y puntos de la mesa a < 2 mm (medido: ~1 mm)."""
    verdad = _verdad_camara(mundo)
    assert np.linalg.norm(cam.centro - verdad.centro) < 3.0
    for x, y, z in [(300, 0, 20), (450, 120, 20), (250, -150, 20), (380, 60, 2)]:
        uv = verdad.proyectar([[x, y, z]])
        assert np.linalg.norm(cam.a_plano(uv, z)[0] - [x, y]) < 2.0


POSES_MADERA = [(360.0, 0.0, 0.0), (352.0, 24.0, -7.0), (368.0, -27.0, 5.5), (345.0, 10.0, 9.0), (372.0, -5.0, -2.5)]


@pytest.mark.parametrize("pose", POSES_MADERA)
def test_madera_sola_y_con_el_taladro_encima(mundo, cam, pose):
    """±2 mm y ±1° (medido: < 1 mm y < 0,15°), también con el taladro y la mano tapando parte de la madera."""
    m = mundo
    m.quitar_taladro()
    verdad = g.PoseTabla(*pose)
    m.colocar_tabla(verdad)
    est = P.detectar_madera(m.imagen("top", RES), cam)
    assert est is not None
    assert np.hypot(est.x - verdad.x, est.y - verdad.y) < 2.0 and abs(est.giro - verdad.giro) < 1.0
    p = verdad.a_mesa(np.array([40.0, 60.0]))
    m.poner_taladro(p[0], p[1])
    est2 = P.detectar_madera(m.imagen("top", RES), cam, est)
    assert np.hypot(est2.x - verdad.x, est2.y - verdad.y) < 2.0 and abs(est2.giro - verdad.giro) < 1.0
    m.quitar_taladro()


def _dif_giro(a, b):
    return abs(((a - b) + 180) % 360 - 180)


def test_pegatina_resuelve_180_y_si_esta_tapada_continuidad(mundo, cam):
    """La pegatina decide el giro aunque la pose anterior diga lo contrario; tapada (mano encima), manda la anterior."""
    m = mundo
    m.quitar_taladro()
    m.quitar_mano_libre()
    for giro in (4.0, 184.0):
        verdad = g.PoseTabla(340.0, 5.0, giro)
        m.colocar_tabla(verdad)
        img = m.imagen("top", RES)
        for previa in (None, g.PoseTabla(340.0, 5.0, giro + 180.0), g.PoseTabla(340.0, 5.0, giro + 2.0)):
            lec = P.LecturaMadera()
            est = P.detectar_madera(img, cam, previa, lectura=lec)
            assert lec.giro_por_pegatina and _dif_giro(est.giro, giro) < 1.0
        # la mano libre tapa la pegatina: sin ella, el giro más cercano al anterior
        peg = verdad.a_mesa(np.array(g.PEGATINA_EN_TABLA))
        m.poner_mano_libre(peg[0], peg[1], g.ALTURA_CARA_TABLA)
        img = m.imagen("top", RES)
        for referencia in (giro, giro + 180.0):
            lec = P.LecturaMadera()
            est = P.detectar_madera(img, cam, g.PoseTabla(340.0, 5.0, referencia + 1.0), lectura=lec)
            assert not lec.giro_por_pegatina and _dif_giro(est.giro, referencia) < 1.0
            assert np.hypot(est.x - verdad.x, est.y - verdad.y) < 2.0
        m.quitar_mano_libre()


CASOS_MADERA_CLARA = [  # (pose, taladro en la madera, mano libre (x, y, rumbo) en la madera)
    ((300.0, -50.0, 15.0), None, None),
    ((345.0, 55.0, -170.0), None, None),
    ((320.0, 0.0, 172.0), (30.0, -50.0), None),
    ((295.0, 30.0, -12.0), None, (-40.0, 60.0, 30.0)),
    ((335.0, -30.0, 8.0), (-20.0, 60.0), (60.0, -90.0, -40.0)),
    ((310.0, 40.0, -178.0), (40.0, 20.0), (-70.0, -120.0, 10.0)),
]


@pytest.mark.parametrize("pose,taladro,mano", CASOS_MADERA_CLARA)
def test_madera_clara_movida_girada_y_tapada(mundo, cam, pose, taladro, mano):
    """Madera clara movida y girada (también 180°) dentro del tapete, con el taladro y su mano y la mano libre (con la
    manga) encima, sin pose anterior: ±2 mm y ±1° (medido en 40 casos al azar: < 0,7 mm y < 0,05°)."""
    m = mundo
    m.quitar_taladro()
    m.quitar_mano_libre()
    verdad = g.PoseTabla(*pose)
    m.colocar_tabla(verdad)
    if taladro is not None:
        p = verdad.a_mesa(np.array(taladro))
        m.poner_taladro(p[0], p[1])
    if mano is not None:
        p = verdad.a_mesa(np.array(mano[:2]))
        m.poner_mano_libre(p[0], p[1], g.ALTURA_CARA_TABLA, mano[2])
    est = P.detectar_madera(m.imagen("top", RES), cam)
    m.quitar_taladro()
    m.quitar_mano_libre()
    assert est is not None
    assert np.hypot(est.x - verdad.x, est.y - verdad.y) < 2.0 and _dif_giro(est.giro, verdad.giro) < 1.0


def test_madera_tapada_mantiene_la_ultima_pose(mundo, cam):
    """Sin evidencia (la madera tapada entera, o casi) se queda la pose anterior; con media madera a la vista, se mide."""
    m = mundo
    m.quitar_taladro()
    m.quitar_mano_libre()
    verdad = g.PoseTabla(330.0, 10.0, 6.0)
    m.colocar_tabla(verdad)
    img = m.imagen("top", RES)
    previa = g.PoseTabla(333.0, 12.0, 5.0)
    tapada = img.copy()
    grande = np.round(P._poligono(cam, verdad.a_mesa(np.array([[-140.0, -190.0], [140.0, -190.0], [140.0, 190.0],
                                                              [-140.0, 190.0]])), P.Z_CARA)).astype(np.int32)
    cv2.fillPoly(tapada, [grande], (90, 90, 95))  # algo gris (un brazo, el robot) encima de toda la madera y más
    lec = P.LecturaMadera()
    assert P.detectar_madera(tapada, cam, previa, lectura=lec) is previa and lec.mantenida
    assert P.detectar_madera(tapada, cam, None) is None
    # media madera tapada por algo que sale de ella por dos lados (como un brazo apoyado): se mide igual
    media = img.copy()
    mitad = np.round(P._poligono(cam, verdad.a_mesa(np.array([[-90.0, 20.0], [150.0, 20.0], [150.0, 200.0],
                                                             [-90.0, 200.0]])), P.Z_CARA)).astype(np.int32)
    cv2.fillPoly(media, [mitad], (90, 90, 95))
    est = P.detectar_madera(media, cam, previa)
    assert np.hypot(est.x - verdad.x, est.y - verdad.y) < 2.0 and _dif_giro(est.giro, verdad.giro) < 1.0


@pytest.mark.parametrize("loc", [(0.0, 0.0), (-60.0, 90.0), (60.0, -100.0), (30.0, 120.0)])
def test_marcador_del_taladro(mundo, cam, loc):
    """Bola naranja → (x, y) del marcador a la altura típica: ±15 mm (medido: < 5 mm con el taladro vertical)."""
    m = mundo
    m.colocar_tabla(g.PoseTabla(360.0, 0.0, 3.0))
    p = m.juez.tabla.a_mesa(np.array(loc))
    m.poner_taladro(p[0], p[1])
    bola = P.detectar_bola(m.imagen("top", RES))
    assert bola is not None
    assert np.linalg.norm(cam.a_plano(bola[0], P.Z_BOLA)[0] - p) < 15.0
    m.quitar_taladro()
    assert P.detectar_bola(m.imagen("top", RES)) is None


@pytest.fixture(scope="module")
def control(mundo):
    from garbi.lateral import ControlLateral

    return ControlLateral(mundo)


@pytest.fixture(scope="module")
def cinematica(mundo):
    return C.CinematicaRobot(mundo.modelo)


CASOS_BROCA = [((10.0, 20.0), 80.0), ((-45.0, -70.0), 80.0), ((50.0, 90.0), 80.0), ((-20.0, 40.0), 60.0),
               ((30.0, -40.0), 120.0)]


@pytest.mark.parametrize("loc,distancia", CASOS_BROCA)
@pytest.mark.parametrize("altura", [0.0, 3.0, 10.0, 25.0])
def test_punta_de_la_broca_con_la_camara_de_la_muneca(mundo, control, cinematica, loc, distancia, altura):
    """Punta 3D por el ancho aparente de la broca y la pose de la muñeca (cinemática): ±2 mm (medido: < 1,2 mm).

    La cámara se pone con `postura_mirar_broca` (la broca a `distancia` mm, fuera de las mordazas)."""
    m = mundo
    m.colocar_tabla(g.PoseTabla(360.0, 0.0, -3.0))
    p = m.juez.tabla.a_mesa(np.array(loc))
    punta = np.array([p[0], p[1], g.ALTURA_CARA_TABLA])
    q = P.postura_mirar_broca(control, punta, distancia)
    assert q is not None
    m.reset_robot(q)
    m.poner_taladro(p[0], p[1], g.ALTURA_CARA_TABLA + altura)
    R, t = cinematica.pose_camara(m.estado(), "wrist")
    aprox = p + np.array([6.0, -5.0])  # lo que daría la cámara de arriba
    med = P.medir_broca(m.imagen("wrist", RES), P.intrinsecas(P.FOVY_WRIST), R, t, aprox)
    assert med is not None
    assert np.linalg.norm(med.punta - [p[0], p[1], g.ALTURA_CARA_TABLA + altura]) < 2.0
    m.quitar_taladro()


@pytest.mark.parametrize("inclinacion,rumbo", [(4.0, 0.0), (8.0, 180.0), (6.0, 90.0)])
def test_punta_de_la_broca_con_el_taladro_inclinado(mundo, control, cinematica, inclinacion, rumbo):
    m = mundo
    m.colocar_tabla(g.PoseTabla(360.0, 0.0, 0.0))
    p = m.juez.tabla.a_mesa(np.array([0.0, 30.0]))
    punta = np.array([p[0], p[1], g.ALTURA_CARA_TABLA])
    m.reset_robot(P.postura_mirar_broca(control, punta, 80.0))
    m.poner_taladro(p[0], p[1], inclinacion=inclinacion, rumbo=rumbo)
    R, t = cinematica.pose_camara(m.estado(), "wrist")
    med = P.medir_broca(m.imagen("wrist", RES), P.intrinsecas(P.FOVY_WRIST), R, t, p)
    assert med is not None and np.linalg.norm(med.punta - punta) < 2.0
    m.quitar_taladro()


def test_broca_tapada_por_las_mordazas_no_se_inventa(mundo, control, cinematica):
    """En el preapunto de `garbi.lateral` la broca apoyada queda detrás de las mordazas: no se da punta."""
    m = mundo
    m.colocar_tabla(g.PoseTabla(360.0, 0.0, 0.0))
    p = m.juez.tabla.a_mesa(np.array([10.0, 20.0]))
    punta = np.array([p[0], p[1], g.ALTURA_CARA_TABLA])
    r = control.preapunto(punta)
    m.reset_robot(control.a_lerobot(r[0]))
    for altura in (0.0, 25.0):
        m.poner_taladro(p[0], p[1], g.ALTURA_CARA_TABLA + altura)
        R, t = cinematica.pose_camara(m.estado(), "wrist")
        med = P.medir_broca(m.imagen("wrist", RES), P.intrinsecas(P.FOVY_WRIST), R, t, p)
        assert med is None or np.linalg.norm(med.punta - [p[0], p[1], g.ALTURA_CARA_TABLA + altura]) < 2.0
    m.quitar_taladro()


def _imagenes(m):
    return {"top": m.imagen("top", RES), "wrist": m.imagen("wrist", RES)}


def test_percepcion_escena_apoyo_con_histeresis_agujero_y_viruta(mundo, control, cinematica, cam):
    """De imágenes + postura + t a `Escena`: madera, taladro, broca (de la muñeca), apoyo con histéresis, el agujero
    apuntado al apoyar y la viruta de alrededor (sucio → limpio)."""
    from garbi.mundo import FUERA

    m = mundo
    m.reset(5, tabla=g.PoseTabla(358.0, 8.0, 2.0), q_inicial=m.estado())
    per = P.Percepcion(cinematica=cinematica)
    per.cam = cam
    p = m.juez.tabla.a_mesa(np.array([-20.0, 35.0]))
    punta = np.array([p[0], p[1], g.ALTURA_CARA_TABLA])
    m.reset_robot(P.postura_mirar_broca(control, punta, 80.0))
    t, dt = 0.0, 1 / HZ_PERCEPCION
    alturas = [12.0] * 3 + [1.0] * 5 + [6.0] * 3 + [10.0] * 3
    estados, eventos, tiempos = [], [], []
    for h in alturas:
        m.poner_taladro(p[0], p[1], g.ALTURA_CARA_TABLA + h)
        esc = per.leer(_imagenes(m), m.estado(), t)
        estados.append(esc.broca.apoyada)
        eventos.append(esc.broca.evento)
        tiempos.append((esc.broca.clavada_desde, esc.broca.levantada_en))
        t += dt
    assert esc.madera is not None and abs(esc.madera.x - 358.0) < 2.0
    assert esc.taladro.visible and esc.taladro.en_zona and np.linalg.norm(esc.taladro.xy - p) < 15.0
    assert esc.broca.fuente == "muneca"
    assert estados[:3] == [False] * 3  # en el aire
    assert estados[3] is False and estados[6] is True  # apoyada tras 0,2 s
    assert all(estados[6:11])  # a 6 mm sigue apoyada (histéresis)
    assert not any(estados[11:])  # a 10 mm ya no
    # instantes de clavado y levantado, para cortar los episodios (fin de ACT = broca levantada)
    assert eventos == [""] * 6 + ["clavada"] + [""] * 4 + ["levantada"] + [""] * 2
    assert tiempos[6][0] == pytest.approx(6 * dt) and tiempos[10][0] == pytest.approx(6 * dt)
    assert tiempos[11] == (None, pytest.approx(11 * dt)) and tiempos[13][1] == pytest.approx(11 * dt)
    assert len(per.agujeros) == 1
    assert np.linalg.norm(m.juez.tabla.a_mesa(per.agujeros[0]) - p) < 3.0  # agujero ±3 mm
    # taladrar deja viruta; el robot se aparta para no tapar
    m.poner_taladro(p[0], p[1])
    m.taladrar()
    m.quitar_taladro()
    from garbi.lateral import APARCADO

    m.reset_robot(APARCADO)
    sucio = per.leer(_imagenes(m), m.estado(), t)
    assert sucio.viruta[0] > 50 and per.fraccion_viruta[0] > 0.05
    m.juez.viruta_donde[:] = FUERA
    m._actualizar_objetos()
    limpio = per.leer(_imagenes(m), m.estado(), t + dt)
    assert limpio.viruta[0] < 5 and per.fraccion_viruta[0] < 0.02
    assert not limpio.taladro.visible and limpio.broca.punta is None


def test_calibracion_del_robot_con_el_anillo_verde(mundo, cam):
    """9 posturas, ajuste (x, y, giro) de la base; 5 posturas nuevas < 4 mm (medido: ~1 mm con la cámara y < 1 mm
    contra la verdad; la base está en el origen)."""
    m = mundo
    m.quitar_taladro()
    m.colocar_tabla(g.PoseTabla(360.0, 0.0, 0.0))
    cin = C.CinematicaRobot(m.modelo)

    def ir_y_mirar(q):
        m.reset_robot(q)
        return m.imagen("top", RES)

    r = C.calibrar_robot(ir_y_mirar, cam, cin)
    assert r is not None and r.vistas == 9 and r.ok
    assert np.max(r.errores) < C.ERROR_MAXIMO
    assert np.hypot(r.base.x, r.base.y) < 2.0 and abs(r.base.giro) < 0.5
    for q in C.POSTURAS_COMPROBACION:
        m.reset_robot(q)
        verdad = m.datos.site_xpos[m.modelo.site("anillo").id] / 1e-3
        assert np.linalg.norm(cin.sitio(q)[:2] - verdad[:2]) < C.ERROR_MAXIMO


# --- manos y taladro agarrado (solución final) ----------------------------------------------------------------------
def test_manos_por_color_en_la_simulacion(mundo, cam):
    """La mano del taladro y la libre, cada una cerca de la verdad (< 50 px); la libre (apoyada) en el tapete."""
    from garbi import manos as Mn

    m = mundo
    m.colocar_tabla(g.PoseTabla(350.0, 0.0, 3.0))
    p = m.juez.tabla.a_mesa(np.array([20.0, 40.0]))
    m.poner_taladro(p[0], p[1])
    q = m.juez.tabla.a_mesa(np.array([-60.0, -110.0]))
    m.poner_mano_libre(q[0], q[1], g.ALTURA_CARA_TABLA)
    img = m.imagen("top", RES)
    manos = Mn.ManosColor().detectar(img, cam)
    verdad = Mn.manos_verdad(m, cam)
    assert len(manos) == 2 and len(verdad) == 2
    for v in verdad:
        cerca = min(manos, key=lambda h: np.linalg.norm(h.uv - v.uv))
        # la manga tapa parte de la palma de la mano libre: el centro de lo que se ve cae hacia los dedos
        assert np.linalg.norm(cerca.uv - v.uv) < 50.0
    libre = min(manos, key=lambda h: np.linalg.norm(h.xy - q))
    assert libre.en_tapete and np.linalg.norm(libre.xy - q) < 70.0
    xy_bola = cam.a_plano(P.detectar_bola(img)[0], P.Z_BOLA)[0]
    d = sorted(Mn.distancia_mano_taladro_escena([h], cam, xy_bola) for h in manos)
    assert d[0] < 90.0 < 150.0 < d[1]  # la del taladro, cerca; la libre, lejos
    m.quitar_taladro()
    m.quitar_mano_libre()
    assert Mn.ManosColor().detectar(m.imagen("top", RES), cam) == []


def _leer_top(per, m, t):
    return per.leer({"top": m.imagen("top", RES)}, None, t)


def test_taladro_agarrado_solo_con_mano_y_taladro(mundo, cam):
    """Mano + taladro: agarrado. Taladro sin mano (dejado en la madera): no. Mano sola: no hay taladro. Taladro sin
    mano y la otra mano en el tapete, lejos: no."""
    m = mundo
    m.quitar_mano_libre()
    m.colocar_tabla(g.PoseTabla(350.0, 0.0, 0.0))
    per = P.Percepcion()
    per.cam = cam
    p = m.juez.tabla.a_mesa(np.array([10.0, 30.0]))
    t, dt = 0.0, 1 / HZ_PERCEPCION
    m.poner_taladro(p[0], p[1])
    for _ in range(3):
        esc = _leer_top(per, m, t)
        t += dt
    assert esc.taladro.visible and esc.taladro.agarrado and esc.taladro.distancia_mano < g_tipos.DIST_MANO_TALADRO
    assert len(esc.manos) == 1
    m.soltar_taladro()  # la mano suelta el taladro: tras AGARRE_MANTENER deja de estar agarrado
    for _ in range(int(P.AGARRE_MANTENER / dt) + 2):
        esc = _leer_top(per, m, t)
        t += dt
    assert esc.taladro.visible and not esc.taladro.agarrado and esc.manos == []
    q = m.juez.tabla.a_mesa(np.array([-70.0, -120.0]))  # la otra mano en el tapete, a ~170 mm del taladro
    m.poner_mano_libre(q[0], q[1], g.ALTURA_CARA_TABLA)
    esc = _leer_top(per, m, t)
    t += dt
    assert esc.taladro.visible and not esc.taladro.agarrado and esc.manos_en_tapete
    m.coger_taladro()
    m.quitar_taladro()  # la mano sola, sin taladro
    esc = _leer_top(per, m, t)
    assert not esc.taladro.visible and not esc.taladro.agarrado and esc.manos_en_tapete
    m.quitar_mano_libre()
    esc = _leer_top(per, m, t + dt)
    assert esc.manos == [] and not esc.manos_en_tapete


def test_configuracion_de_vision_editable(tmp_path, mundo, cam):
    """Los umbrales salen del YAML; uno propio cambia lo que se detecta sin tocar código."""
    from garbi.config_vision import cargar_config, config_por_defecto

    cfg = config_por_defecto()
    assert (cfg.rango("bola").bajo, cfg.rango("bola").alto) == (P.NARANJA_BAJO, P.NARANJA_ALTO)
    assert cfg["madera"]["bordes_min"] > 0 and cfg.rango("manos") == cfg.rangos["piel"]
    otra = cargar_config({"parametros": {"manos": {"area": [1, 2]}}})
    assert otra["manos"]["area"] == [1, 2] and otra["manos"]["altura_palma"] == cfg["manos"]["altura_palma"]
    m = mundo
    m.colocar_tabla(g.PoseTabla(350.0, 0.0, 0.0))
    m.poner_mano_libre(300.0, -190.0)  # en el tapete, al lado de la madera
    ruta = tmp_path / "vision.yaml"
    ruta.write_text("parametros:\n  manos:\n    area: [900000, 1000000]\n", encoding="utf-8")  # ninguna es tan grande
    per = P.Percepcion(config=str(ruta))
    per.cam = cam
    assert _leer_top(per, m, 0.0).manos == []
    per = P.Percepcion()
    per.cam = cam
    assert len(_leer_top(per, m, 0.0).manos) == 1
    m.quitar_mano_libre()


def test_la_herramienta_de_color_conserva_los_parametros(tmp_path):
    from garbi import config_vision as cv

    ruta = tmp_path / "c.yaml"
    ruta.write_text(cv.RUTA_DEFECTO.read_text(encoding="utf-8"), encoding="utf-8")
    rangos = cv.cargar_config_vision(ruta)
    rangos["piel"] = cv.RangoHSV((170, 40, 90), (12, 160, 255))
    cv.guardar_config_vision(rangos, ruta)
    cfg = cv.cargar_config(ruta)
    assert cfg.rango("manos").da_la_vuelta and cfg["madera"]["bordes_min"] == cv.PARAMETROS_POR_DEFECTO["madera"][
        "bordes_min"] and "parametros" in ruta.read_text(encoding="utf-8")


def test_manos_mediapipe_dice_que_falta():
    """Sin MediaPipe o sin su modelo, un error que explica cómo arreglarlo (la importación es perezosa)."""
    from garbi.manos import ManosMediaPipe

    det = ManosMediaPipe(modelo="/no/existe/hand_landmarker.task")
    with pytest.raises((ImportError, FileNotFoundError), match="mediapipe|MediaPipe"):
        det.detectar(np.zeros((480, 640, 3), np.uint8), None)
