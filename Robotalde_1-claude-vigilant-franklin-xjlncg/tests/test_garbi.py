"""Tests de la simulación de Garbi (sin render)."""
import numpy as np
import pytest

from garbi import contrato as g
from garbi.arduino import ArduinoVirtual, EnlaceArduino
from garbi.control import ControlBoca
from garbi.mundo import EN_ALFOMBRILLA, EN_TABLA, MundoGarbi


@pytest.fixture(scope="module")
def mundo():
    return MundoGarbi(render=False)


def test_pose_tabla_ida_y_vuelta():
    t = g.PoseTabla(170.0, -20.0, 15.0)
    p = np.array([12.0, -7.0])
    assert np.allclose(t.a_tabla(t.a_mesa(p)), p)
    assert t.contiene(t.a_mesa(p))
    assert not t.contiene(t.a_mesa([200.0, 0.0]))


def test_aruco_alfombrilla_en_la_alfombrilla():
    for p in g.esquinas_aruco_alfombrilla().values():
        assert abs(p[0] - g.ALFOMBRILLA_CENTRO[0]) < g.ALFOMBRILLA_TAMANO[0] / 2
        assert abs(p[1] - g.ALFOMBRILLA_CENTRO[1]) < g.ALFOMBRILLA_TAMANO[1] / 2


def test_taladrar_y_mover_tabla_lleva_la_viruta(mundo):
    mundo.reset(semilla=3)
    tabla = mundo.juez.tabla
    p = tabla.a_mesa(np.array([10.0, 5.0]))
    mundo.poner_taladro(p[0], p[1])
    h = mundo.taladrar()
    assert np.allclose(h, [10.0, 5.0], atol=1e-6)
    antes = mundo.viruta_alrededor(h)
    assert antes > 20
    mundo.mover_tabla(10, -10, 8)
    assert mundo.viruta_alrededor(h) == antes  # la viruta va con la tabla
    pos = mundo.viruta_en_mesa(EN_TABLA)
    assert all(mundo.juez.tabla.contiene(q[:2]) for q in pos)


def test_taladrar_fuera_de_la_tabla_no_hace_nada(mundo):
    mundo.reset(semilla=4)
    mundo.poner_taladro(140.0, -200.0)  # fuera de la madera (300 de ancho)
    assert mundo.taladrar() is None


def test_aspiracion_solo_cerca_y_encendida(mundo):
    mundo.reset(semilla=5)
    mundo.tirar_serrin(200.0, 120.0, n=10, radio=3.0)
    n = len(mundo.viruta_en_mesa(EN_ALFOMBRILLA)) + len(mundo.viruta_en_mesa(EN_TABLA))
    mundo.aspiradora = True
    mundo._aspirar()  # la boca está aparcada, lejos
    assert len(mundo.viruta_en_mesa()) == n


def test_ik_de_la_boca_a_30_grados_en_toda_la_zona(mundo):
    """Acompañar, preapunto y limpiar, por los dos lados, en la tabla y en la alfombrilla."""
    from garbi.control import distancia_limpieza, eje_hacia

    mundo.reset(semilla=0)
    ctl = ControlBoca(mundo.cin)
    for r, th, z in [(130, -30, g.ALTURA_CARA_TABLA), (185, 0, g.ALTURA_CARA_TABLA), (215, 30, g.ALTURA_CARA_TABLA),
                     (150, 40, g.ALFOMBRILLA_GROSOR), (230, -40, g.ALFOMBRILLA_GROSOR)]:
        punto = np.array([r * np.cos(np.radians(th)), r * np.sin(np.radians(th)), z])
        for lado in (1, -1):
            e = eje_hacia(punto, lado)
            for objetivo in (punto - e * g.DISTANCIA_ACOMPANAR, punto - e * distancia_limpieza(),
                             ctl.preapunto(punto, lado)[0]):
                q = ctl.postura(objetivo, e, lado)
                assert np.linalg.norm(ctl.boca(q) - objetivo) < 1.0, (r, th, lado, objetivo)
                assert np.degrees(np.arccos(np.clip(ctl.eje(q) @ e, -1, 1))) < 2.0
                assert ctl.borde_inferior(q) > z, (r, th, lado)


def test_arduino_apaga_sin_latido():
    a = ArduinoVirtual()
    e = EnlaceArduino(a)
    e.aspiradora(True, 0.0)
    for k in range(10):
        e.latido(k * 0.1)
    assert a.aspiradora and a.ok
    a.avanzar(3.0)  # el PC calla 2 s
    assert not a.aspiradora and not a.ok


def test_escenario_completo_limpia_agujero_y_alfombrilla():
    from garbi.escenario import ejecutar
    inf = ejecutar(semilla=1)
    assert abs(inf.distancia_boca_broca - g.DISTANCIA_ACOMPANAR * np.cos(np.radians(g.INCLINACION_BOCA))) < 3
    assert inf.viruta_agujero_tras_taladrar <= g.VIRUTA_POR_AGUJERO - 10  # aspira mientras se taladra
    assert inf.viruta_agujero_al_final <= 2
    assert inf.viruta_alfombrilla_final <= 2


def test_cono_de_captacion_a_lo_largo_del_eje():
    from garbi.mundo import en_cono_captacion

    i = np.radians(g.INCLINACION_BOCA)
    eje = np.array([np.cos(i), 0.0, -np.sin(i)])
    boca = np.array([100.0, 0.0, 38.0])
    delante = boca + eje * 36  # el punto de la superficie que se limpia
    pts = np.array([delante, delante + [0, 20, 0], boca - eje * 10, boca + eje * 80, delante + [0, 40, 0]])
    assert en_cono_captacion(pts, boca, eje).tolist() == [True, True, False, False, False]
