"""Tests del seguimiento por cámara con imágenes de la cámara sintética."""
import time

import numpy as np
import pytest

from lewelder import contrato as c
from lewelder.camara_sintetica import CamaraSintetica
from lewelder.seguimiento import (
    CalibracionCamara,
    FiltroTrazo,
    PosePieza,
    Seguidor,
    abrir_webcam,
    detectar_led,
    detectar_marcadores,
    estimar_pose_mesa,
    estimar_pose_pieza,
    punto_en_pieza,
)

ANCLAJES = list(c.ANCLAJES)


@pytest.fixture(scope="module")
def camara():
    return CamaraSintetica(semilla=7)


@pytest.fixture(scope="module")
def calib(camara):
    return camara.calibracion()


def _error_xy(medido, verdad):
    return float(np.hypot(medido[0] - verdad[0], medido[1] - verdad[1]))


# --- calibración -------------------------------------------------------------------------------------------------
def test_calibracion_guardar_y_cargar(tmp_path, calib):
    ruta = tmp_path / "calib.json"
    calib.guardar(ruta)
    otra = CalibracionCamara.cargar(ruta)
    assert np.allclose(otra.K, calib.K) and np.allclose(otra.dist, calib.dist)
    assert (otra.ancho, otra.alto) == (calib.ancho, calib.alto)


def test_calibrar_tablero_con_imagenes_sinteticas(camara):
    rng = np.random.default_rng(3)
    imagenes = []
    for _ in range(12):
        giro = np.radians(rng.uniform(-30, 30, size=3))
        imagenes.append(camara.renderizar_tablero(giro, (rng.uniform(-60, 60), rng.uniform(-40, 40), 550.0)))
    calib = CalibracionCamara.calibrar_tablero(imagenes, tablero=(9, 6), cuadro_mm=25.0)
    assert calib.error_rms < 0.5
    assert calib.K[0, 0] == pytest.approx(camara.K[0, 0], rel=0.02)
    assert calib.K[0, 2] == pytest.approx(camara.K[0, 2], abs=10)


# --- LED ---------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("exposicion", ["baja", "normal"])
def test_detectar_led_con_precision_subpixel(camara, exposicion):
    errores = []
    for i, x in enumerate(np.linspace(0, 120, 7)):
        img, verdad = camara.renderizar(c.TipoPieza.RECTA, ANCLAJES[i % 4], led=(x, 1.0, c.ALTURA_PUNTA),
                                        exposicion=exposicion)
        led = detectar_led(img)
        assert led is not None
        errores.append(np.hypot(led[0] - verdad.pixel_led[0], led[1] - verdad.pixel_led[1]))
    assert max(errores) < 0.3


def test_led_oculto_devuelve_none(camara):
    img, _ = camara.renderizar(c.TipoPieza.RECTA, "A", led=None, reflejo=True)
    assert detectar_led(img) is None


@pytest.mark.parametrize("exposicion", ["baja", "normal"])
def test_reflejo_parasito_no_confunde(camara, exposicion):
    img, verdad = camara.renderizar(c.TipoPieza.RECTA, "C", led=(40.0, 0.0, c.ALTURA_PUNTA), reflejo=True,
                                    exposicion=exposicion)
    led = detectar_led(img)
    assert led is not None
    assert np.hypot(led[0] - verdad.pixel_led[0], led[1] - verdad.pixel_led[1]) < 0.5


# --- pose de la pieza --------------------------------------------------------------------------------------------
@pytest.mark.parametrize("tipo", list(c.TipoPieza))
@pytest.mark.parametrize("anclaje", ANCLAJES)
def test_tipo_de_pieza_y_anclaje(camara, calib, tipo, anclaje):
    img, verdad = camara.renderizar(tipo, anclaje, led=None, desfase=(1.5, -1.0, 1.0))
    marcadores = detectar_marcadores(img, calib)
    mesa = estimar_pose_mesa(marcadores, calib)
    assert mesa is not None and mesa.n_marcadores >= 2
    pose = estimar_pose_pieza(marcadores, calib, mesa)
    assert isinstance(pose, PosePieza)
    assert pose.tipo is tipo and pose.id_aruco == verdad.id_aruco
    assert pose.anclaje == anclaje
    assert pose.metodo == "plano_mesa"


def test_pose_sin_anclajes_visibles_usa_pnp(camara, calib):
    img, verdad = camara.renderizar(c.TipoPieza.RECTA, "B", led=None, dibujar_anclajes=False)
    marcadores = detectar_marcadores(img, calib)
    assert estimar_pose_mesa(marcadores, calib) is None
    pose = estimar_pose_pieza(marcadores, calib)
    assert pose is not None and pose.metodo == "pnp"
    # Origen de la pieza respecto a la cámara: cerca de la verdad, pero mucho más ruidoso que con el plano de la mesa
    # (con un solo ArUco de 25 mm a ~0,9 m, la profundidad falla unos cm): error < 8 % de la distancia.
    assert np.linalg.norm(pose.t - verdad.t_camara_pieza) < 0.08 * np.linalg.norm(verdad.t_camara_pieza)


def test_punto_en_pieza_con_pose_exacta(camara, calib):
    led = (75.0, 3.0, c.ALTURA_PUNTA)
    _, verdad = camara.renderizar(c.TipoPieza.RECTA, "A", led=led)
    pose = PosePieza(c.TipoPieza.RECTA, verdad.id_aruco, verdad.R_camara_pieza, verdad.t_camara_pieza)
    p = punto_en_pieza(*verdad.pixel_led, pose, calib)
    assert np.allclose(p, led, atol=1e-6)


def _pose_estimada(camara, calib, tipo, anclaje, desfase):
    img, _ = camara.renderizar(tipo, anclaje, led=None, desfase=desfase)
    marcadores = detectar_marcadores(img, calib)
    return estimar_pose_pieza(marcadores, calib, estimar_pose_mesa(marcadores, calib))


@pytest.mark.parametrize("anclaje", ANCLAJES)
def test_precision_del_punto_a_lo_largo_del_cordon(camara, calib, anclaje):
    """Rejilla a lo largo del cordón: error en el plano < 2 mm de media y < 4 mm de máximo."""
    rng = np.random.default_rng(ANCLAJES.index(anclaje))
    desfase = (rng.uniform(-2, 2), rng.uniform(-2, 2), rng.uniform(-2, 2))
    pose = _pose_estimada(camara, calib, c.TipoPieza.RECTA, anclaje, desfase)
    errores = []
    for x in np.arange(0.0, 121.0, 10.0):
        for y in (-4.0, 0.0, 4.0):
            led = (x, y, c.ALTURA_PUNTA)
            img, verdad = camara.renderizar(c.TipoPieza.RECTA, anclaje, led=led, desfase=desfase)
            u, v, _ = detectar_led(img)
            errores.append(_error_xy(punto_en_pieza(u, v, pose, calib), led))
    print(f"\nanclaje {anclaje}: error medio {np.mean(errores):.2f} mm, máximo {np.max(errores):.2f} mm")
    assert np.mean(errores) < 2.0
    assert np.max(errores) < 4.0


@pytest.mark.parametrize("anclaje", ["A", "B", "C"])
def test_precision_en_la_t(camara, calib, anclaje):
    pose = _pose_estimada(camara, calib, c.TipoPieza.T, anclaje, (1.0, 1.0, -1.0))
    errores = []
    for x in np.arange(0.0, 121.0, 20.0):
        led = (x, -3.0, c.ALTURA_PUNTA)
        img, verdad = camara.renderizar(c.TipoPieza.T, anclaje, led=led, desfase=(1.0, 1.0, -1.0))
        assert verdad.led_visible
        u, v, _ = detectar_led(img)
        errores.append(_error_xy(punto_en_pieza(u, v, pose, calib), led))
    assert np.mean(errores) < 2.0 and np.max(errores) < 4.0


# --- filtro ------------------------------------------------------------------------------------------------------
def test_filtro_rechaza_un_salto():
    filtro = FiltroTrazo()
    for i in range(10):
        assert filtro.filtrar(i / 60, (i * 0.1, 0.0, 3.0)) is not None
    assert filtro.filtrar(10 / 60, (60.0, 0.0, 3.0)) is None  # salto de ~59 mm: imposible
    assert filtro.filtrar(11 / 60, (1.1, 0.0, 3.0)) is not None


def test_filtro_se_reengancha_si_el_salto_persiste():
    filtro = FiltroTrazo()
    for i in range(10):
        filtro.filtrar(i / 60, (0.0, 0.0, 3.0))
    salidas = [filtro.filtrar((10 + i) / 60, (50.0, 0.0, 3.0)) for i in range(5)]
    assert salidas[0] is None
    assert salidas[-1] is not None and salidas[-1][0] == pytest.approx(50.0, abs=1.0)


def test_filtro_suaviza_sin_mucho_retraso():
    rng = np.random.default_rng(0)
    filtro = FiltroTrazo()
    errores_crudo, errores_filtrado = [], []
    for i in range(600):  # 10 s a 60 Hz, avance de 5 mm/s
        t = i / 60
        verdad = np.array([5.0 * t, 0.0, 3.0])
        medido = verdad + rng.normal(0, 0.5, 3) * [1, 1, 0]
        salida = filtro.filtrar(t, medido)
        if i > 60:
            errores_crudo.append(np.linalg.norm(medido - verdad))
            errores_filtrado.append(np.linalg.norm(np.array(salida) - verdad))
    assert np.mean(errores_filtrado) < 0.7 * np.mean(errores_crudo)
    assert np.mean(errores_filtrado) < 1.0  # el retraso a 5 mm/s no se come la precisión


# --- seguidor ----------------------------------------------------------------------------------------------------
def test_seguidor_devuelve_muestras_en_el_marco_de_la_pieza(camara, calib):
    seguidor = Seguidor(calib, cada_n=10)
    errores = []
    for i in range(30):
        t = i / 30
        led = (20.0 + 5.0 * t, 0.5, c.ALTURA_PUNTA)  # avance a 5 mm/s
        img, _ = camara.renderizar(c.TipoPieza.RECTA, "B", led=led)
        m = seguidor.procesar(img, t)
        assert isinstance(m, c.Muestra)
        assert m.gatillo is False and m.angulo_trabajo is None and m.angulo_avance is None
        errores.append(_error_xy((m.x, m.y), led))
    assert seguidor.pose.anclaje == "B" and seguidor.anclaje == "B"
    assert np.mean(errores[10:]) < 2.0


def test_seguidor_sin_led_devuelve_none(camara, calib):
    seguidor = Seguidor(calib)
    img, _ = camara.renderizar(c.TipoPieza.RECTA, "A", led=None)
    assert seguidor.procesar(img, 0.0) is None
    assert seguidor.pose is not None  # la pieza sí se ve


def test_seguidor_detecta_cambio_de_anclaje(camara, calib):
    seguidor = Seguidor(calib, cada_n=5)
    led = (60.0, 0.0, c.ALTURA_PUNTA)
    for i in range(5):
        img, _ = camara.renderizar(c.TipoPieza.RECTA, "A", led=led)
        seguidor.procesar(img, i / 30)
    assert seguidor.anclaje == "A"
    cambios = []
    for i in range(5, 15):
        img, _ = camara.renderizar(c.TipoPieza.RECTA, "C", led=led)
        seguidor.procesar(img, i / 30)
        cambios.append(seguidor.cambio_anclaje)
    assert seguidor.anclaje == "C"
    assert sum(cambios) == 1


def test_tiempo_por_fotograma(camara, calib):
    seguidor = Seguidor(calib, cada_n=30)
    imagenes = [camara.renderizar(c.TipoPieza.RECTA, "B", led=(x, 0.0, c.ALTURA_PUNTA))[0]
                for x in np.linspace(10, 110, 60)]
    seguidor.procesar(imagenes[0], 0.0)  # primer fotograma: detecta mesa y pieza
    tiempos = []
    for i, img in enumerate(imagenes[1:], start=1):
        t0 = time.perf_counter()
        seguidor.procesar(img, i / 60)
        tiempos.append((time.perf_counter() - t0) * 1000)
    print(f"\nprocesar 1280x720: medio {np.mean(tiempos):.1f} ms, mediana {np.median(tiempos):.1f} ms, "
          f"máximo {np.max(tiempos):.1f} ms")
    assert np.mean(tiempos) < 20.0


def test_abrir_webcam_sin_camara_no_rompe():
    assert abrir_webcam(97) is None
