"""Tests del estéreo v2 con la escena sintética: calibración, triangulación del LED, poses de las chapas y seguidor."""
import time

import numpy as np
import pytest

from lewelder import contrato as c
from lewelder.escena_sintetica import EscenaSintetica
from lewelder.estereo import (
    TABLERO_EN_MESA,
    CalibracionEstereo,
    FiltroPose,
    PoseChapa,
    SeguidorEstereo,
    detectar_marcadores_v2,
    detectar_tablero,
    estimar_pose_chapa,
    triangular,
    triangular_led,
)
from lewelder.juntas import (
    EstadoJunta,
    Pose,
    apoyada,
    marco_cordon,
    pose_base,
    pose_movil_montada,
    pose_movil_tumbada,
    punta_en_cordon,
    rot_x,
    rot_y,
    rot_z,
)
from lewelder.seguimiento import detectar_led


@pytest.fixture(scope="module")
def escena():
    return EscenaSintetica(semilla=5)


@pytest.fixture(scope="module")
def verdad(escena):
    """Calibración estéreo exacta (la de la escena sintética), ya referida a la mesa."""
    return CalibracionEstereo.desde_escena(escena)


def poses_tablero_calibracion(n=20, semilla=0):
    """Tablero sostenido delante de las cámaras, inclinado hacia ellas y en poses variadas (→ mesa)."""
    rng = np.random.default_rng(semilla)
    poses = []
    for _ in range(n):
        centro = np.array([c.POSICION_BASE.x + rng.uniform(0, 130), c.POSICION_BASE.y + rng.uniform(-70, 70),
                           rng.uniform(40, 160)])
        # Boca arriba (Z del tablero = -Z de la mesa) con la X a lo largo de Y de la mesa, levantado hacia +X (donde
        # están las cámaras) entre 15° y 45° y algo girado.
        Rz = rot_z(90.0 + rng.uniform(-30, 30))
        inclinado = Rz @ rot_x(180.0 + rng.uniform(15, 45)) @ rot_y(rng.uniform(-25, 25)) @ rot_z(rng.uniform(-10, 10))
        poses.append(Pose(inclinado, centro - inclinado @ np.array([100.0, 62.5, 0.0])))
    return poses


@pytest.fixture(scope="module")
def calibracion(escena):
    """Calibración estéreo hecha con fotos sintéticas del tablero y referida a la mesa con el tablero tumbado."""
    pares = [escena.renderizar_tablero(p) for p in poses_tablero_calibracion()]
    estereo = CalibracionEstereo.calibrar([a for a, _ in pares], [b for _, b in pares])
    img_a, img_b = escena.renderizar_tablero(TABLERO_EN_MESA)
    estereo.calibrar_mesa_tablero(img_a, img_b)
    return estereo


# --- calibración -------------------------------------------------------------------------------------------------
def test_detectar_tablero_en_orden_canonico(escena, verdad):
    from lewelder.estereo import objeto_tablero
    img_a, img_b = escena.renderizar_tablero(TABLERO_EN_MESA)
    obj = TABLERO_EN_MESA.aplicar(objeto_tablero())
    for img, cam in zip((img_a, img_b), verdad.camaras()):
        esquinas = detectar_tablero(img)
        assert esquinas is not None and esquinas.shape == (54, 2)
        assert np.abs(esquinas - cam.proyectar(obj)).max() < 0.5


def test_calibracion_estereo_recupera_la_relativa(calibracion, verdad):
    assert calibracion.error_rms < 0.5
    angulo = Pose(calibracion.R, calibracion.T).diferencia(Pose(verdad.R, verdad.T))[1]
    assert angulo < 0.2
    assert np.linalg.norm(calibracion.T - verdad.T) < 0.01 * np.linalg.norm(verdad.T)
    assert np.allclose(calibracion.a.K, verdad.a.K, rtol=0.01, atol=3.0)


def test_calibracion_mesa_con_tablero(calibracion, verdad):
    for cam, cam_v in zip(calibracion.camaras(), verdad.camaras()):
        assert np.linalg.norm(cam.centro - cam_v.centro) < 3.0
        assert cam.pose.diferencia(cam_v.pose)[1] < 0.3


def test_calibracion_mesa_con_el_aruco_de_la_base(escena, verdad):
    estereo = CalibracionEstereo(verdad.a, verdad.b, verdad.R, verdad.T)
    img_a, img_b, _ = escena.renderizar(pose_base(), None)
    error = estereo.calibrar_mesa_aruco(img_a, img_b)
    assert error < 1.0
    for cam, cam_v in zip(estereo.camaras(), verdad.camaras()):
        assert np.linalg.norm(cam.centro - cam_v.centro) < 10.0
        assert cam.pose.diferencia(cam_v.pose)[1] < 1.0


def test_guardar_y_cargar(tmp_path, calibracion):
    ruta = tmp_path / "estereo.json"
    calibracion.guardar(ruta)
    otra = CalibracionEstereo.cargar(ruta)
    assert np.allclose(otra.R, calibracion.R) and np.allclose(otra.T, calibracion.T)
    assert np.allclose(otra.a.K, calibracion.a.K) and np.allclose(otra.b.dist, calibracion.b.dist)
    assert np.allclose(otra.mesa.R, calibracion.mesa.R) and np.allclose(otra.mesa.t, calibracion.mesa.t)


def test_sin_mesa_no_hay_camaras(verdad):
    with pytest.raises(ValueError):
        CalibracionEstereo(verdad.a, verdad.b, verdad.R, verdad.T).camaras()


# --- triangulación -----------------------------------------------------------------------------------------------
def test_triangular_puntos_exactos(verdad):
    cam_a, cam_b = verdad.camaras()
    P = np.array([[250.0, 0.0, 6.0], [200.0, -150.0, 40.0], [300.0, 60.0, 0.0]])
    p, error = triangular(cam_a, cam_b, cam_a.proyectar(P), cam_b.proyectar(P))
    assert np.abs(p - P).max() < 1e-6 and error.max() < 1e-6


def test_triangular_led_y_rechazo(escena, verdad):
    base = pose_base()
    led = marco_cordon(c.TipoJunta.T, base).aplicar([60.0, -2.0, 1.0])
    img_a, img_b, _ = escena.renderizar(base, pose_movil_montada(c.TipoJunta.T, base), led)
    la, lb = detectar_led(img_a), detectar_led(img_b)
    resultado = triangular_led(verdad, la, lb)
    assert resultado is not None
    p, error = resultado
    assert np.linalg.norm(p - led) < 0.5 and error < 1.0
    # Un LED que no es el mismo en las dos cámaras (reflejo) no casa: error de reproyección grande → None.
    assert triangular_led(verdad, la, (lb[0] + 25.0, lb[1] - 30.0, lb[2])) is None
    assert triangular_led(verdad, None, lb) is None


# --- poses de las chapas -----------------------------------------------------------------------------------------
@pytest.mark.parametrize("x, y, giro", [(250.0, 0.0, 0.0), (240.0, 30.0, 20.0), (260.0, -40.0, -35.0),
                                         (230.0, 10.0, 90.0), (270.0, -10.0, 180.0)])
def test_pose_de_la_base(escena, calibracion, x, y, giro):
    base = pose_base(x, y, giro)
    img_a, img_b, _ = escena.renderizar(base, None)
    pose = estimar_pose_chapa("base", detectar_marcadores_v2(img_a), detectar_marcadores_v2(img_b),
                              calibracion.camaras())
    assert isinstance(pose, PoseChapa) and pose.n_camaras == 2
    distancia, angulo = pose.pose.diferencia(base)
    assert distancia < 3.0 and angulo < 2.0
    # La precisión que importa: los extremos del cordón (a 60 mm del centro), no solo el origen.
    extremos = np.array([[-60.0, 0.0, 0.0], [60.0, 0.0, 0.0]])
    assert np.abs(pose.pose.aplicar(extremos) - base.aplicar(extremos)).max() < 1.5


@pytest.mark.parametrize("caso", ["t", "esquina", "tumbada", "tumbada_lisa_arriba", "inclinada"])
def test_pose_de_la_movil(escena, calibracion, caso):
    base = pose_base(250.0, 0.0, 10.0)
    movil = {
        "t": pose_movil_montada(c.TipoJunta.T, base),
        "esquina": pose_movil_montada(c.TipoJunta.ESQUINA, base),
        "tumbada": pose_movil_tumbada(140.0, 190.0, 30.0),
        "tumbada_lisa_arriba": pose_movil_tumbada(120.0, 215.0, -40.0, aleta_arriba=False),
        "inclinada": pose_movil_montada(c.TipoJunta.T, base, inclinacion=-12.0),
    }[caso]
    img_a, img_b, _ = escena.renderizar(base, movil)
    pose = estimar_pose_chapa("movil", detectar_marcadores_v2(img_a), detectar_marcadores_v2(img_b),
                              calibracion.camaras())
    assert pose is not None and pose.n_camaras == 2
    distancia, angulo = pose.pose.diferencia(movil)
    assert distancia < 3.0 and angulo < 2.0


def test_movil_vista_por_una_sola_camara(escena, calibracion):
    """Volcada 12° hacia las cámaras, su ArUco se ve tan de canto que solo lo detecta una: la orientación sigue
    bien y la distancia se fija suponiendo que apoya en la base."""
    base = pose_base(250.0, 0.0, 10.0)
    movil = pose_movil_montada(c.TipoJunta.T, base, inclinacion=12.0)
    img_a, img_b, _ = escena.renderizar(base, movil)
    ma, mb = detectar_marcadores_v2(img_a), detectar_marcadores_v2(img_b)
    pose = estimar_pose_chapa("movil", ma, mb, calibracion.camaras(), base=base)
    assert pose is not None
    distancia, angulo = pose.pose.diferencia(movil)
    assert angulo < 4.0 and distancia < 6.0
    if pose.n_camaras == 1:
        assert pose.metodo == "1camara_apoyada" and pose.calidad < 0.8


def test_sin_marcadores_no_hay_pose(escena, calibracion):
    img_a, img_b, _ = escena.renderizar(None, None)
    assert estimar_pose_chapa("base", detectar_marcadores_v2(img_a), detectar_marcadores_v2(img_b),
                              calibracion.camaras()) is None


def test_filtro_de_pose_suaviza_y_detecta_movimiento():
    rng = np.random.default_rng(0)
    filtro = FiltroPose(alfa=0.3, confirmar=2)
    real = pose_base()

    def ruidosa(pose):
        return PoseChapa("base", Pose(pose.R @ rot_z(rng.normal(0, 0.3)), pose.t + rng.normal(0, 0.4, 3)),
                         ids=[c.ID_BASE], n_camaras=2, error_px=0.2)

    errores = []
    for _ in range(30):
        pose, movida = filtro.actualizar(ruidosa(real))
        errores.append(pose.pose.diferencia(real)[0])
    assert np.mean(errores[10:]) < 0.5
    # Un valor raro suelto no mueve la pose; dos seguidos en el mismo sitio sí (la base se ha movido).
    lejos = pose_base(300.0, 50.0, 30.0)
    pose, movida = filtro.actualizar(ruidosa(lejos))
    assert not movida and pose.pose.diferencia(real)[0] < 1.0
    pose, movida = filtro.actualizar(ruidosa(lejos))
    assert movida and pose.pose.diferencia(lejos)[0] < 2.0
    # Sin detección se conserva la última pose (una mano tapa el ArUco).
    pose, movida = filtro.actualizar(None)
    assert pose is not None and not movida and not pose.vista


# --- reconocimiento de punta a punta -----------------------------------------------------------------------------
JUNTAS_VARIADAS = [
    (c.TipoJunta.T, 250.0, 0.0, 0.0), (c.TipoJunta.ESQUINA, 250.0, 0.0, 0.0),
    (c.TipoJunta.T, 235.0, 25.0, 25.0), (c.TipoJunta.ESQUINA, 265.0, -30.0, -30.0),
    (c.TipoJunta.T, 255.0, -20.0, -50.0), (c.TipoJunta.ESQUINA, 240.0, 20.0, 45.0),
    (c.TipoJunta.T, 245.0, 10.0, -90.0), (c.TipoJunta.ESQUINA, 260.0, 0.0, 90.0),
    (c.TipoJunta.T, 250.0, -10.0, 15.0), (c.TipoJunta.ESQUINA, 245.0, 15.0, 180.0),
]


def test_tipo_de_junta_correcto_10_de_10(escena, calibracion):
    fallos = []
    for tipo, x, y, giro in JUNTAS_VARIADAS:
        base = pose_base(x, y, giro)
        img_a, img_b, _ = escena.renderizar(base, pose_movil_montada(tipo, base))
        seguidor = SeguidorEstereo(calibracion)
        _, junta = seguidor.procesar(img_a, img_b, 0.0)
        if junta.tipo != EstadoJunta(tipo.value) or junta.posicion != "PB":
            fallos.append((tipo.value, giro, junta.tipo.value, junta.motivo, junta.errores))
    assert not fallos


@pytest.mark.parametrize("caso, texto", [("inclinada", "inclinada"), ("desplazada", "de la guía"),
                                         ("tumbada", "tumbada"), ("girada", "girada")])
def test_junta_incompleta_detectada(escena, calibracion, caso, texto):
    base = pose_base(250.0, 0.0, 15.0)
    movil = {
        "inclinada": pose_movil_montada(c.TipoJunta.T, base, inclinacion=12.0),
        "desplazada": pose_movil_montada(c.TipoJunta.ESQUINA, base, desplazamiento=(0.0, -9.0, 0.0)),
        "tumbada": pose_movil_tumbada(135.0, 195.0, 25.0),
        "girada": pose_movil_montada(c.TipoJunta.T, base, giro=12.0),
    }[caso]
    img_a, img_b, _ = escena.renderizar(base, movil)
    _, junta = SeguidorEstereo(calibracion).procesar(img_a, img_b, 0.0)
    assert junta.tipo is EstadoJunta.INCOMPLETA and texto in junta.motivo


def test_sin_movil(escena, calibracion):
    img_a, img_b, _ = escena.renderizar(pose_base(), None)
    _, junta = SeguidorEstereo(calibracion).procesar(img_a, img_b, 0.0)
    assert junta.tipo is EstadoJunta.SIN_MOVIL


# --- seguidor ----------------------------------------------------------------------------------------------------
def test_apoyo_distinguido_en_el_95_por_ciento(escena, calibracion):
    """Punta a 0-1,5 mm de la chapa → apoyada; a 5 mm → no; en >= 95 % de 200 fotogramas con ruido."""
    rng = np.random.default_rng(3)
    tipo = c.TipoJunta.T
    base = pose_base(250.0, 0.0, 10.0)
    movil = pose_movil_montada(tipo, base)
    cordon = marco_cordon(tipo, base)
    seguidor = SeguidorEstereo(calibracion)
    seguidor.procesar(*escena.renderizar(base, movil)[:2], 0.0)  # la junta se reconoce antes de soldar
    aciertos = {True: [], False: []}
    for k in range(1, 201):
        abajo = (k // 25) % 2 == 0  # tramos de 25 fotogramas apoyado / levantado
        x = 10.0 + 100.0 * (k % 100) / 100
        z = rng.uniform(0.0, 1.5) if abajo else 5.0 + rng.normal(0, 0.2)
        punta = cordon.aplicar([x, rng.uniform(-2.5, -1.0), z])
        img_a, img_b, _ = escena.renderizar(base, movil, punta)
        muestra, _ = seguidor.procesar(img_a, img_b, k / 30)
        if muestra is not None:
            aciertos[abajo].append(apoyada(muestra.z) == abajo)
    for abajo in (True, False):
        assert len(aciertos[abajo]) >= 95
        assert np.mean(aciertos[abajo]) >= 0.95, (abajo, np.mean(aciertos[abajo]))


def test_seguidor_da_la_punta_en_el_marco_del_cordon(escena, calibracion):
    tipo = c.TipoJunta.ESQUINA
    base = pose_base(240.0, -15.0, -20.0)
    movil = pose_movil_montada(tipo, base)
    cordon = marco_cordon(tipo, base)
    seguidor = SeguidorEstereo(calibracion, cada_n=4)
    # Como en la clase: la escuela reconoce la junta antes de que se encienda el LED. Después, el halo del LED tapa
    # a ratos el ArUco de la cara lisa (está encima del cordón) y la pose de la móvil se conserva.
    seguidor.procesar(*escena.renderizar(base, movil)[:2], 0.0)
    errores, errores_muestra = [], []
    for k, x in enumerate(np.linspace(5.0, 115.0, 12), start=1):
        p = np.array([x, -2.0, 1.0])
        img_a, img_b, _ = escena.renderizar(base, movil, cordon.aplicar(p))
        muestra, junta = seguidor.procesar(img_a, img_b, k / 30)
        assert junta.tipo is EstadoJunta.ESQUINA
        if muestra is not None:
            errores.append(np.linalg.norm(np.array(punta_en_cordon(seguidor.punta, junta)) - p))
            errores_muestra.append(np.linalg.norm(np.array([muestra.x, muestra.y, muestra.z]) - p))
    assert len(errores) >= 10 and np.median(errores) < 1.0
    # La muestra va filtrada (One Euro): a 300 mm/s, como aquí, se retrasa unos milímetros.
    assert np.max(errores_muestra) < 8.0 and abs(errores_muestra[-1]) < 4.0


def test_led_tapado_en_una_camara_devuelve_none(escena, calibracion):
    base = pose_base()
    movil = pose_movil_montada(c.TipoJunta.T, base)
    led = marco_cordon(c.TipoJunta.T, base).aplicar([50.0, -2.0, 1.0])
    seguidor = SeguidorEstereo(calibracion)
    for k, oculto in enumerate((("b",), ("a",), ("a", "b"))):
        img_a, img_b, _ = escena.renderizar(base, movil, led, led_oculto_en=oculto)
        muestra, junta = seguidor.procesar(img_a, img_b, k / 30)
        assert muestra is None and junta.tipo is EstadoJunta.T


def test_seguidor_detecta_movimiento_de_la_base(escena, calibracion):
    seguidor = SeguidorEstereo(calibracion, cada_n=1)
    base = pose_base()
    movida = pose_base(280.0, 40.0, 20.0)
    movimientos = []
    for k, b in enumerate([base] * 3 + [movida] * 4):
        img_a, img_b, _ = escena.renderizar(b, pose_movil_montada(c.TipoJunta.T, b))
        _, junta = seguidor.procesar(img_a, img_b, k / 30)
        movimientos.append(seguidor.movimiento)
    assert movimientos[0] and not any(movimientos[1:3]) and any(movimientos[3:])
    assert seguidor.base.pose.diferencia(movida)[0] < 3.0 and junta.tipo is EstadoJunta.T


def test_tiempo_por_par_de_fotogramas(escena, calibracion):
    base = pose_base()
    movil = pose_movil_montada(c.TipoJunta.T, base)
    cordon = marco_cordon(c.TipoJunta.T, base)
    pares = [escena.renderizar(base, movil, cordon.aplicar([x, -2.0, 1.0]))[:2] for x in np.linspace(10, 110, 61)]
    seguidor = SeguidorEstereo(calibracion, cada_n=15)
    seguidor.procesar(*pares[0], 0.0)
    tiempos = []
    for i, (a, b) in enumerate(pares[1:], start=1):
        t0 = time.perf_counter()
        seguidor.procesar(a, b, i / 30)
        tiempos.append((time.perf_counter() - t0) * 1000)
    print(f"\nprocesar par 1280x720: medio {np.mean(tiempos):.1f} ms, mediana {np.median(tiempos):.1f} ms, "
          f"máximo {np.max(tiempos):.1f} ms")
    assert np.mean(tiempos) < 30.0
