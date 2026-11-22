"""Fusión de cámara y antorcha, y fuentes (simulada de punta a punta y ratón)."""
import asyncio

import numpy as np
import pytest

from lewelder.antorcha import LecturaAntorcha, cuaternion_desde_angulos
from lewelder.contrato import ANCLAJES, Muestra
from lewelder.fuentes import ConfigPasada, Fuente, FuenteRaton, FuenteSimulada, GuionPasada, Latido
from lewelder.fusion import EDAD_MAX_LECTURA, Fusion, giro_de_pieza

Q_TARA = cuaternion_desde_angulos(90.0, 0.0)


def lectura(recibido, gatillo=True, trabajo=80.0, avance=10.0, giro=0.0, q_tara=Q_TARA):
    q = None if trabajo is None else cuaternion_desde_angulos(trabajo, avance, q_tara=q_tara, giro_pieza_grados=giro)
    return LecturaAntorcha(t=recibido, gatillo=gatillo, q=q, recibido=recibido)


def posicion(t, x=10.0, y=0.5, z=3.0):
    return Muestra(t=t, x=x, y=y, z=z, gatillo=False)


# --- fusión ------------------------------------------------------------------------------------------------------
def test_usa_la_lectura_anterior_al_instante_de_captura():
    f = Fusion()
    f.anadir_lecturas([lectura(1.00, gatillo=False), lectura(1.01, gatillo=True), lectura(1.02, gatillo=False)])
    assert f.lectura_en(1.015).recibido == 1.01
    assert f.lectura_en(None).recibido == 1.02  # sin instante: la última
    assert f.lectura_en(0.5).recibido == 1.00  # fotograma más viejo que el buffer: la más antigua
    m = f.fusionar(posicion(0.0), t=0.0, instante=1.015)
    assert m.gatillo is True  # la de 1.01, no la última (gatillo suelto) que llegó mientras se procesaba


def test_tiempos_y_posicion_salen_de_la_camara():
    f = Fusion()
    f.anadir_lectura(lectura(5.0))
    m = f.fusionar(posicion(0.4, x=33.0, y=-1.0, z=3.0), t=0.4, instante=5.001)
    assert (m.t, m.x, m.y, m.z) == (0.4, 33.0, -1.0, 3.0)


def test_lectura_vieja_es_antorcha_desconectada():
    f = Fusion()
    assert f.tara(lectura=lectura(0.0, trabajo=90.0, avance=0.0))
    f.anadir_lectura(lectura(1.0))
    m = f.fusionar(posicion(0.0), t=0.0, instante=1.0 + EDAD_MAX_LECTURA + 0.05)
    assert m.gatillo is False and m.angulo_trabajo is None and m.angulo_avance is None


def test_angulos_con_tara():
    f = Fusion()
    f.anadir_lectura(lectura(0.0, gatillo=False, trabajo=90.0, avance=0.0))
    m = f.fusionar(posicion(0.0), t=0.0)
    assert m.angulo_trabajo is None  # sin tara no hay ángulos
    assert f.tara(giro_pieza=0.0)
    f.anadir_lectura(lectura(0.1, trabajo=75.0, avance=12.0))
    m = f.fusionar(posicion(0.1), t=0.1)
    assert m.angulo_trabajo == pytest.approx(75.0, abs=0.01)
    assert m.angulo_avance == pytest.approx(12.0, abs=0.01)


def test_angulos_con_giro_de_la_pieza_respecto_a_la_tara():
    # Tara sobre la pieza en el anclaje A (giro 0); luego se suelda en el D (giro -90).
    f = Fusion()
    f.anadir_lectura(lectura(0.0, gatillo=False, trabajo=90.0, avance=0.0))
    assert f.tara(giro_pieza=giro_de_pieza("A"))
    giro = ANCLAJES["D"].giro - ANCLAJES["A"].giro
    f.anadir_lectura(lectura(0.1, trabajo=45.0, avance=15.0, giro=giro))
    m = f.fusionar(posicion(0.1), t=0.1, giro_pieza=giro_de_pieza("D"))
    assert m.angulo_trabajo == pytest.approx(45.0, abs=0.01)
    assert m.angulo_avance == pytest.approx(15.0, abs=0.01)
    # Sin tener en cuenta el giro, el ángulo saldría mal.
    mal = f.fusionar(posicion(0.2), t=0.2, giro_pieza=giro_de_pieza("A"))
    assert abs(mal.angulo_avance - 15.0) > 5


def test_tara_sin_imu_falla():
    f = Fusion()
    f.anadir_lectura(LecturaAntorcha(t=0.0, gatillo=False, q=None, recibido=0.0))
    assert not f.tara()


def test_al_soltar_el_gatillo_una_muestra_en_la_ultima_posicion():
    f = Fusion()
    f.anadir_lectura(lectura(0.0, gatillo=True))
    assert f.fusionar(posicion(0.0, x=40.0), t=0.0).gatillo is True
    f.anadir_lectura(lectura(0.04, gatillo=False))
    soltado = f.fusionar(None, t=0.04)  # el LED se apaga con el gatillo: la cámara ya no ve la punta
    assert soltado is not None and soltado.gatillo is False and soltado.x == 40.0 and soltado.t == 0.04
    assert f.fusionar(None, t=0.08) is None  # solo una


def test_soltar_mucho_despues_no_inventa_posicion():
    f = Fusion()
    f.anadir_lectura(lectura(0.0, gatillo=True))
    f.fusionar(posicion(0.0), t=0.0)
    f.fusionar(None, t=0.5)  # LED tapado medio segundo con el gatillo apretado
    f.anadir_lectura(lectura(1.0, gatillo=False))
    assert f.fusionar(None, t=1.0) is None


def test_giro_de_pieza():
    assert giro_de_pieza("D") == ANCLAJES["D"].giro
    assert giro_de_pieza(None) == 0.0
    assert giro_de_pieza("A", en_mesa=(1.0, 2.0, 3.5)) == 3.5


# --- fuente ratón ------------------------------------------------------------------------------------------------
def test_fuente_raton():
    reloj = iter(np.arange(0, 100, 0.1)).__next__
    f = FuenteRaton(reloj=reloj)
    assert isinstance(f, Fuente)
    assert isinstance(f.evento(), Latido)  # sin dedo
    f.mover(10.0, 1.0, True)
    m = f.evento()
    assert isinstance(m, Muestra) and m.gatillo and (m.x, m.y) == (10.0, 1.0) and m.angulo_trabajo is None
    m2 = f.evento()  # el dedo quieto con el gatillo sigue dando muestras (punto quemado)
    assert isinstance(m2, Muestra) and m2.t > m.t
    f.mover(12.0, 1.0, False)
    suelta = f.evento()
    assert isinstance(suelta, Muestra) and not suelta.gatillo
    assert isinstance(f.evento(), Latido)
    f.mover(float("nan"), 0.0, True)  # se ignora
    assert f.pieza()[1] == "B"


# --- fuente simulada ---------------------------------------------------------------------------------------------
def test_guion_de_la_pasada():
    g = GuionPasada("t", ConfigPasada(huecos=[(40.0, 55.0)], ruido_angulo=0.0))
    assert g.en(None) is None and g.en(-1) is None and g.en(g.duracion + 1) is None
    medio = g.en(g.duracion / 2)
    assert medio.angulo_trabajo == pytest.approx(45.0)  # objetivo de la T
    en_hueco = [m for m in g.muestras if 41 < m.x < 54]
    assert en_hueco and not any(m.gatillo for m in en_hueco)


def test_config_pasada_de_dict():
    c = ConfigPasada.de_dict({"huecos": [[10, 20]], "velocidad": 7, "desconocido": 1})
    assert c.huecos == [(10.0, 20.0)] and c.velocidad == 7
    assert ConfigPasada.de_dict(c.a_dict()) == c


@pytest.mark.asyncio
async def test_fuente_simulada_de_punta_a_punta():
    """Render → LED + ArUco → serie (pty) → parser → tara → ángulos → fusión, contra la pasada de verdad."""
    config = ConfigPasada(velocidad=10.0, huecos=[(40.0, 55.0)], temblor_mm=0.0, ruido_angulo=0.0,
                          angulo_avance=12.0)
    f = FuenteSimulada("recta", "C", config=config, fps=15, tiempo_real=False, ancho=640, alto=360)
    assert isinstance(f, Fuente)
    await f.iniciar()
    try:
        assert f.estado()["tara"] and f.pieza() == (f.tipo, "C")
        f.empezar_pasada()
        muestras, latidos = [], []
        async for ev in f.muestras():
            (latidos if isinstance(ev, Latido) else muestras).append(ev)
            if ev.t > f.guion.duracion + 0.5:
                break
    finally:
        await f.cerrar()
    ts = [e.t for e in sorted(muestras + latidos, key=lambda e: e.t)]
    assert np.allclose(np.diff(ts), 1 / 15)  # un evento por fotograma, al ritmo de la cámara
    soldando = [m for m in muestras if m.gatillo and 2 < m.x < 118]
    assert len(soldando) > 100
    assert not any(42 < m.x < 53 for m in soldando)  # en el hueco no luce el LED
    verdad = [f.guion.en(m.t) for m in soldando]
    error = np.array([[m.x - v.x, m.y - v.y] for m, v in zip(soldando, verdad)])
    assert np.abs(error).mean(axis=0).max() < 2.0  # mm
    assert np.mean([m.angulo_trabajo for m in soldando]) == pytest.approx(90.0, abs=1.0)
    assert np.mean([m.angulo_avance for m in soldando]) == pytest.approx(12.0, abs=1.0)
    sueltas = [m for m in muestras if not m.gatillo]
    assert any(38 < m.x < 42 for m in sueltas)  # la muestra de "gatillo soltado" al entrar en el hueco
