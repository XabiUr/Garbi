"""Tests de la cámara sintética: que pinte lo que dice su verdad."""
import cv2
import numpy as np
import pytest

from lewelder import contrato as c
from lewelder.camara_sintetica import CamaraSintetica, FuenteSintetica, PoseCamara


@pytest.fixture(scope="module")
def camara():
    return CamaraSintetica(semilla=1)


def test_imagen_bgr_del_tamano_pedido(camara):
    img, verdad = camara.renderizar(c.TipoPieza.RECTA, "A", led=(60.0, 0.0, c.ALTURA_PUNTA))
    assert img.shape == (720, 1280, 3) and img.dtype == np.uint8
    assert verdad.tipo is c.TipoPieza.RECTA and verdad.anclaje == "A"
    pequena = CamaraSintetica(ancho=640, alto=480)
    img2, _ = pequena.renderizar(c.TipoPieza.T, "B", led=None)
    assert img2.shape == (480, 640, 3)


def test_objetivo_de_la_camara_cae_en_el_centro():
    objetivo = (225.0, 0.0, 16.0)
    cam = CamaraSintetica(pose=PoseCamara.mirando((520.0, 40.0, 600.0), objetivo))
    u, v = cam.proyectar(objetivo)
    assert abs(u - (cam.ancho - 1) / 2) < 1e-6 and abs(v - (cam.alto - 1) / 2) < 1e-6


def test_verdad_del_led_coincide_con_la_proyeccion(camara):
    led = (30.0, -2.0, c.ALTURA_PUNTA)
    img, verdad = camara.renderizar(c.TipoPieza.RECTA, "C", led=led)
    p_mesa = verdad.R_mesa_pieza @ np.array(led) + verdad.t_mesa_pieza
    assert np.allclose(camara.proyectar(p_mesa), verdad.pixel_led, atol=1e-6)
    # El píxel más verde y brillante está en el LED.
    u, v = np.round(verdad.pixel_led).astype(int)
    ventana = img[v - 2:v + 3, u - 2:u + 3, 1]
    assert ventana.max() >= 250


def test_exposicion_baja_es_oscura_y_el_led_satura(camara):
    led = (90.0, 0.0, c.ALTURA_PUNTA)
    baja, v1 = camara.renderizar(c.TipoPieza.RECTA, "B", led=led, exposicion="baja")
    normal, _ = camara.renderizar(c.TipoPieza.RECTA, "B", led=led, exposicion="normal")
    assert baja.mean() < normal.mean() / 3
    u, v = np.round(v1.pixel_led).astype(int)
    assert baja[v, u, 1] >= 250


def test_led_oculto_no_tiene_pixel(camara):
    _, verdad = camara.renderizar(c.TipoPieza.RECTA, "A", led=None)
    assert verdad.pixel_led is None and not verdad.led_visible


@pytest.mark.parametrize("exposicion", ["baja", "normal"])
def test_marcadores_detectables_por_opencv(camara, exposicion):
    img, verdad = camara.renderizar(c.TipoPieza.T, "B", led=(60.0, -2.0, c.ALTURA_PUNTA), exposicion=exposicion)
    diccionario = cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, c.DICCIONARIO_ARUCO))
    detector = cv2.aruco.ArucoDetector(diccionario, cv2.aruco.DetectorParameters())
    gris = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    if exposicion == "baja":
        gris = cv2.convertScaleAbs(gris, alpha=4.0)
    _, ids, _ = detector.detectMarkers(gris)
    ids = set(ids.ravel().tolist())
    assert verdad.id_aruco in ids
    assert len(ids & set(c.IDS_ANCLAJE)) >= 3


def test_esquinas_del_marcador_de_la_pieza_en_su_sitio(camara):
    """La esquina 0 que detecta OpenCV es la (-L/2, +L/2) del marcador en el marco de la pieza."""
    img, verdad = camara.renderizar(c.TipoPieza.RECTA, "D", led=None, exposicion="normal", ruido=False)
    diccionario = cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, c.DICCIONARIO_ARUCO))
    esquinas, ids, _ = cv2.aruco.ArucoDetector(diccionario).detectMarkers(img)
    i = list(ids.ravel()).index(verdad.id_aruco)
    medida = esquinas[i][0]
    m = c.LADO_ARUCO_PIEZA / 2
    cx, cy, _ = c.ARUCO_EN_PIEZA
    modelo = [(cx - m, cy + m, 0), (cx + m, cy + m, 0), (cx + m, cy - m, 0), (cx - m, cy - m, 0)]
    esperada = [camara.proyectar(verdad.R_mesa_pieza @ np.array(p) + verdad.t_mesa_pieza) for p in modelo]
    assert np.abs(medida - np.array(esperada)).max() < 1.5


def test_alma_de_la_t_tapa_el_led_si_la_camara_esta_detras():
    """Con la cámara baja en el lado del alma (+Y de la pieza) el alma queda entre el LED y la cámara."""
    from lewelder.camara_sintetica import PoseCamara
    from sim.escena import pieza_a_mesa

    medio = np.asarray(pieza_a_mesa("B", (60.0, 0.0, 0.0)))
    lado_alma = np.asarray(pieza_a_mesa("B", (60.0, 150.0, 40.0)))  # 150 mm hacia +Y de la pieza, 40 mm de alto
    camara = CamaraSintetica(pose=PoseCamara.mirando(lado_alma, medio), semilla=1)
    _, verdad = camara.renderizar(c.TipoPieza.T, "B", led=(60.0, -2.0, c.ALTURA_PUNTA))
    assert not verdad.led_visible and verdad.pixel_led is None
    # La misma cámara sí ve el LED en la recta (no hay alma)
    _, verdad = camara.renderizar(c.TipoPieza.RECTA, "B", led=(60.0, -2.0, c.ALTURA_PUNTA))
    assert verdad.led_visible


def test_reflejo_tiene_verdad(camara):
    _, verdad = camara.renderizar(c.TipoPieza.RECTA, "A", led=(60.0, 0.0, c.ALTURA_PUNTA), reflejo=True)
    assert len(verdad.pixeles_reflejos) >= 1


def test_fuente_sintetica_lee_como_videocapture():
    fuente = FuenteSintetica(trayectoria=lambda t: (5.0 * t, 0.0, c.ALTURA_PUNTA), fps=30, semilla=2)
    assert fuente.isOpened()
    ok, img = fuente.read()
    assert ok and img.shape == (720, 1280, 3)
    ok, _ = fuente.read()
    assert ok and fuente.t == pytest.approx(1 / 30)  # el primer fotograma es t = 0
    assert fuente.verdad.pixel_led is not None
    fuente.release()
