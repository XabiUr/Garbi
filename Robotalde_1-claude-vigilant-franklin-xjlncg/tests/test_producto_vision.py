"""Visión del producto (P2) con imágenes sintéticas: tapete azul, tabla clara, círculo morado y manos color piel."""
from __future__ import annotations

import os
import sys
import time
import types

import cv2
import numpy as np
import pytest

from garbi.producto import vision as pv
from garbi.producto.contrato import Vista

TAPETE = np.array([[40, 30], [600, 30], [600, 450], [40, 450]], float)
AZUL = (30, 60, 170)
MADERA = (225, 200, 160)
MORADO = (128, 0, 160)
PIEL = (220, 160, 130)
CUERPO = (50, 50, 55)  # el taladro, gris oscuro


def escena(circulo=None, radio=14.0, manos=(), tabla=((320, 240), (260, 170), 0.0), tapas=(), ruido=0):
    """Imagen RGB 640×480. `circulo`: centro (u, v) del círculo morado (con el cuerpo del taladro alrededor);
    `manos`: centros de manos; `tabla`: ((u, v), (ancho, alto), giro°) o None; `tapas`: rectángulos oscuros (robot,
    taladro) encima de todo."""
    img = np.full((480, 640, 3), (90, 85, 80), np.uint8)  # mesa
    cv2.fillPoly(img, [TAPETE.astype(np.int32)], AZUL)
    if tabla is not None:
        caja = cv2.boxPoints(tabla)
        cv2.fillPoly(img, [np.round(caja * 16).astype(np.int32)], MADERA, cv2.LINE_AA, shift=4)
    for (u, v) in manos:  # palma + dedos
        cv2.ellipse(img, (int(u), int(v)), (24, 32), 20, 0, 360, PIEL, -1, cv2.LINE_AA)
        cv2.ellipse(img, (int(u) + 8, int(v) - 38), (14, 18), 20, 0, 360, PIEL, -1, cv2.LINE_AA)
    if circulo is not None:
        u, v = circulo
        cv2.circle(img, (int(round(u)), int(round(v))), int(radio) + 10, CUERPO, -1, cv2.LINE_AA)
        cv2.circle(img, (int(round(u * 16)), int(round(v * 16))), int(round(radio * 16)), MORADO, -1, cv2.LINE_AA,
                   shift=4)
    for (x0, y0, x1, y1) in tapas:
        cv2.rectangle(img, (x0, y0), (x1, y1), CUERPO, -1)
    if ruido:
        rng = np.random.default_rng(0)
        img = np.clip(img.astype(int) + rng.integers(-ruido, ruido + 1, img.shape), 0, 255).astype(np.uint8)
    return img


def config(**extra):
    c = {"tapete_px": TAPETE.tolist(), "vision": {"manos": {"detector": "color", "cada_n": 1}}}
    for k, v in extra.items():
        c["vision"][k] = {**c["vision"].get(k, {}), **v}
    return c


def correr(vision, imgs, fps=15.0, t0=0.0):
    vista = None
    for k, img in enumerate(imgs):
        vista = vision.leer({"top": img, "wrist": None}, t0 + k / fps)
    return vista


def esquinas_verdad(tabla):
    return pv.ordenar_esquinas(cv2.boxPoints(tabla))


def error_esquinas(a, b):
    return pv._distancia_esquinas(np.asarray(a), np.asarray(b))


# --- círculo ---------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("uv,radio", [((200.3, 150.7), 14.0), ((420.6, 300.2), 10.5), ((320.0, 240.5), 20.0),
                                      ((100.25, 400.8), 8.0)])
def test_circulo_error_menor_de_2_px(uv, radio):
    det = pv.DetectorCirculoColor(pv.cargar_config(None).rango("morado"))
    r = det.detectar(escena(uv, radio, ruido=6))
    assert r is not None
    assert np.linalg.norm(r[0] - np.array(uv)) < 2.0
    assert abs(r[1] - radio) < 2.0
    # y a través de VisionProducto (con el filtro)
    vista = correr(pv.VisionProducto(config()), [escena(uv, radio)] * 3)
    assert np.linalg.norm(vista.circulo.uv - np.array(uv)) < 2.0


def test_circulo_ignora_manchas_no_circulares_y_el_tapete():
    img = escena(None)
    cv2.rectangle(img, (100, 100), (220, 112), MORADO, -1)  # tira morada alargada
    assert pv.VisionProducto(config()).leer({"top": img}, 0.0).circulo is None
    img = escena((300, 200))
    cv2.rectangle(img, (100, 100), (220, 112), MORADO, -1)
    c = pv.VisionProducto(config()).leer({"top": img}, 0.0).circulo
    assert c is not None and np.linalg.norm(c.uv - [300, 200]) < 2


def test_circulo_quieto_con_temblor_y_movil():
    rng = np.random.default_rng(1)
    v = pv.VisionProducto(config())
    # quieto con temblor de ±2 px durante 2 s
    for k in range(30):
        uv = np.array([300.0, 200.0]) + rng.uniform(-2, 2, 2)
        vista = v.leer({"top": escena(uv)}, k / 15.0)
    assert vista.circulo.quieto_desde is not None
    assert vista.circulo.quieto_desde <= 0.2
    assert vista.t - vista.circulo.quieto_desde >= 1.5
    # se mueve a 150 px/s: casi nunca quieto
    quietos = 0
    for k in range(30, 60):
        vista = v.leer({"top": escena((300.0 + 10.0 * (k - 29), 200.0))}, k / 15.0)
        quietos += vista.circulo is not None and vista.circulo.quieto_desde is not None
    assert quietos <= 3
    # se para: vuelve a quieto, contando desde que se paró
    for k in range(60, 90):
        vista = v.leer({"top": escena((600.0, 200.0))}, k / 15.0)
    assert vista.circulo.quieto_desde is not None and vista.circulo.quieto_desde >= 60 / 15.0 - 0.01
    assert vista.t - vista.circulo.quieto_desde > 1.0


def test_circulo_perdido_un_momento_no_parpadea():
    v = pv.VisionProducto(config())
    correr(v, [escena((300, 200))] * 10)
    vista = v.leer({"top": escena(None)}, 10 / 15.0)  # un fotograma sin verlo
    assert vista.circulo is not None and vista.circulo.quieto_desde is not None
    vista = correr(v, [escena(None)] * 10, t0=11 / 15.0)
    assert vista.circulo is None


def test_detector_del_equipo_por_config(monkeypatch):
    llamadas = []

    class DetectorEquipo:
        def detectar(self, img_bgr):
            llamadas.append(img_bgr[0, 0].copy())
            return (123.0, 45.0), 9.0

    modulo = types.ModuleType("detector_equipo_falso")
    modulo.DetectorEquipo = DetectorEquipo
    monkeypatch.setitem(sys.modules, "detector_equipo_falso", modulo)
    v = pv.VisionProducto(config(circulo={"detector": "detector_equipo_falso:DetectorEquipo", "orden_color": "bgr"}))
    vista = v.leer({"top": escena(None)}, 0.0)
    assert np.allclose(vista.circulo.uv, [123, 45]) and vista.circulo.radio == 9.0
    assert tuple(llamadas[0]) == (80, 85, 90)  # le llega en BGR
    # también como objeto (o función) directamente
    v = pv.VisionProducto(config(), detector_circulo=lambda img: None)
    assert v.leer({"top": escena((300, 200))}, 0.0).circulo is None


# --- manos y agarre --------------------------------------------------------------------------------------------------

def test_manos_por_color_dan_centros_en_px():
    vista = correr(pv.VisionProducto(config()), [escena(None, manos=[(150, 300), (480, 120)])])
    assert len(vista.manos) == 2
    cerca = sorted(vista.manos, key=lambda m: m[0])
    assert np.linalg.norm(cerca[0] - [150, 300]) < 25 and np.linalg.norm(cerca[1] - [480, 120]) < 25


@pytest.mark.parametrize("circulo,manos,esperado", [
    ((300, 200), [(330, 290)], True),     # mano en la empuñadura, ~95 px por debajo del círculo
    ((300, 200), [], False),              # taladro solo (dejado en la mesa)
    (None, [(330, 290)], False),          # mano sola
    ((300, 200), [(540, 400)], False),    # mano lejos (libre)
])
def test_taladro_agarrado_solo_con_mano_y_taladro(circulo, manos, esperado):
    vista = correr(pv.VisionProducto(config()), [escena(circulo, manos=manos)] * 8)
    assert vista.taladro_agarrado is esperado


def test_agarre_con_histeresis_no_parpadea():
    v = pv.VisionProducto(config(agarre={"distancia_px": 120.0, "histeresis_px": 30.0}))
    correr(v, [escena((300, 150), manos=[(300, 260)])] * 8)  # a 110 px: agarrado
    estados = []
    for k in range(30):  # la mano oscila entre 110 y 140 px (dentro de la histéresis)
        d = 110 if k % 2 else 140
        estados.append(v.leer({"top": escena((300, 150), manos=[(300, 150 + d)])}, (8 + k) / 15.0).taladro_agarrado)
    assert all(estados)
    # un fotograma suelto sin mano no lo suelta (t_off)
    assert v.leer({"top": escena((300, 150))}, 40 / 15.0).taladro_agarrado
    vista = correr(v, [escena((300, 150))] * 10, t0=41 / 15.0)
    assert not vista.taladro_agarrado


def test_regla_agarre_unitaria():
    from garbi.producto.contrato import Circulo

    r = pv.ReglaAgarre(distancia_px=100, histeresis_px=20, t_on=0.1, t_off=0.3)
    c = Circulo(np.array([0.0, 0.0]), 10.0)
    assert not r.actualizar(c, [np.array([50.0, 0.0])], 0.0)  # aún no ha pasado t_on
    assert r.actualizar(c, [np.array([50.0, 0.0])], 0.15)
    assert r.actualizar(c, [np.array([115.0, 0.0])], 0.2)      # dentro de la histéresis
    assert r.actualizar(None, [np.array([50.0, 0.0])], 0.3)    # sin círculo, pero aún dentro de t_off
    assert not r.actualizar(None, [np.array([50.0, 0.0])], 0.65)


def test_mediapipe_o_respaldo(monkeypatch):
    """Sin modelo, «auto» cae al color de piel; con modelo (si está), MediaPipe carga y no ve manos en una imagen
    sin manos."""
    monkeypatch.setenv("GARBI_MODELO_MANOS", "/no/existe/hand_landmarker.task")
    v = pv.VisionProducto({"vision": {"manos": {"detector": "auto"}}})
    assert v.fuente_manos == "color"
    modelo = os.environ.get("GARBI_MODELO_MANOS_PRUEBA")
    if not modelo or not os.path.exists(modelo):
        pytest.skip("sin modelo de MediaPipe (GARBI_MODELO_MANOS_PRUEBA)")
    monkeypatch.setenv("GARBI_MODELO_MANOS", modelo)
    v = pv.VisionProducto({"vision": {"manos": {"detector": "auto"}}})
    assert v.fuente_manos == "mediapipe"
    assert v.leer({"top": escena((300, 200))}, 0.0).manos == []
    v.cerrar()


# --- tabla y tapete --------------------------------------------------------------------------------------------------

def test_tapete_por_config_y_tabla_detectada():
    tabla = ((330.0, 235.0), (250.0, 160.0), 12.0)
    vista = correr(pv.VisionProducto(config()), [escena(None, tabla=tabla, ruido=5)] * 8)
    assert np.allclose(vista.tapete, TAPETE)
    assert vista.tabla is not None and vista.tabla.shape == (4, 2)
    assert error_esquinas(vista.tabla, esquinas_verdad(tabla)) < 3.0


def test_tabla_tarda_en_aparecer_y_se_ignora_fuera_del_tapete():
    v = pv.VisionProducto(config())
    assert v.leer({"top": escena(None)}, 0.0).tabla is None  # t_aparece
    # algo claro fuera del tapete no es la tabla
    img = escena(None, tabla=None)
    cv2.rectangle(img, (0, 455), (300, 479), MADERA, -1)
    assert correr(pv.VisionProducto(config()), [img] * 10).tabla is None


def test_tabla_movida_y_girada():
    v = pv.VisionProducto(config())
    a = ((320.0, 240.0), (260.0, 170.0), 0.0)
    b = ((360.0, 260.0), (260.0, 170.0), 25.0)
    correr(v, [escena(None, tabla=a)] * 8)
    vista = correr(v, [escena(None, tabla=b)] * 3, t0=1.0)
    assert error_esquinas(vista.tabla, esquinas_verdad(b)) < 3.0


def test_tabla_tapada_parcialmente_mantiene_la_ultima():
    v = pv.VisionProducto(config())
    tabla = ((320.0, 240.0), (260.0, 170.0), 8.0)
    buena = correr(v, [escena(None, tabla=tabla)] * 8).tabla
    # mano y taladro encima, el robot tapando una esquina
    tapada = escena((250, 200), manos=[(270, 290), (420, 180)], tabla=tabla, tapas=[(380, 280, 470, 340)])
    for k in range(45):  # 3 s tapada
        vista = v.leer({"top": tapada}, 1.0 + k / 15.0)
        assert vista.tabla is not None
        assert error_esquinas(vista.tabla, buena) < 3.0


def test_tabla_retirada_con_histeresis():
    v = pv.VisionProducto(config())
    correr(v, [escena(None)] * 8)
    vista = correr(v, [escena(None, tabla=None)] * 5, t0=1.0)  # 0,3 s sin tabla: aún no
    assert vista.tabla is not None
    vista = correr(v, [escena(None, tabla=None)] * 20, t0=1.4)  # > t_retirada
    assert vista.tabla is None


def test_sin_tapete_configurado_usa_toda_la_imagen():
    v = pv.VisionProducto({"vision": {"manos": {"detector": "ninguno"}}})
    vista = correr(v, [escena(None)] * 8)
    assert vista.tapete is None and vista.tabla is not None


# --- anotar, config y herramientas -----------------------------------------------------------------------------------

def test_anotar_dibuja_y_no_toca_la_original():
    v = pv.VisionProducto(config())
    img = escena((300, 200), manos=[(330, 290)])
    vista = correr(v, [img] * 8)
    assert isinstance(vista, Vista) and vista.taladro_agarrado
    copia = img.copy()
    out = v.anotar(img, vista)
    assert out.shape == img.shape and np.array_equal(img, copia) and not np.array_equal(out, img)


def test_guardar_tapete_px(tmp_path):
    ruta = tmp_path / "garbi_producto.yaml"
    assert not pv.guardar_tapete_px(TAPETE, ruta)  # no existe: no lo crea
    ruta.write_text("# comentario\npolitica: act\n", encoding="utf-8")
    assert pv.guardar_tapete_px(TAPETE, ruta)
    assert pv.guardar_tapete_px(TAPETE + 1, ruta)  # reemplaza, no duplica
    texto = ruta.read_text(encoding="utf-8")
    assert "# comentario" in texto and texto.count("tapete_px:") == 1
    cfg = pv.cargar_config_vision_producto(ruta)
    assert np.allclose(cfg["tapete_px"], TAPETE + 1) and cfg["circulo"]["detector"] == "color"


def test_ordenar_esquinas():
    p = pv.ordenar_esquinas([[600, 450], [40, 30], [40, 450], [600, 30]])
    assert np.allclose(p, TAPETE)


def test_rendimiento_640x480():
    v = pv.VisionProducto(config())
    imgs = [escena((300 + k, 200), manos=[(330 + k, 290)], ruido=4) for k in range(10)]
    correr(v, imgs[:3])
    t0 = time.perf_counter()
    n = 60
    for k in range(n):
        vista = v.leer({"top": imgs[k % 10]}, k / 15.0)
        v.anotar(imgs[k % 10], vista)
    fps = n / (time.perf_counter() - t0)
    assert fps >= 15.0, f"{fps:.1f} fps"


def test_tabla_puesta_con_mano_y_taladro_encima_desde_el_principio():
    tabla = ((330.0, 240.0), (260.0, 170.0), 10.0)
    img = escena((300, 200), manos=[(330, 290)], tabla=tabla)  # la mano muerde el borde de abajo
    vista = correr(pv.VisionProducto(config()), [img] * 8)
    assert vista.tabla is not None and error_esquinas(vista.tabla, esquinas_verdad(tabla)) < 3.0


def test_tabla_puesta_con_el_robot_tapando_una_esquina_se_acepta_tras_t_forzar():
    tabla = ((320.0, 240.0), (260.0, 170.0), 0.0)
    img = escena(None, tabla=tabla, tapas=[(380, 250, 480, 340)])  # muerde ~12 % de la tabla
    v = pv.VisionProducto(config())
    assert correr(v, [img] * 15).tabla is None  # 1 s: aún no
    vista = correr(v, [img] * 30, t0=1.0)
    assert vista.tabla is not None and error_esquinas(vista.tabla, esquinas_verdad(tabla)) < 25.0
