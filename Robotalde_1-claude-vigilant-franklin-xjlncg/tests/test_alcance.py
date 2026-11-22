"""Tests del alcance: ¿puede el SO-101 soldar y señalar la junta montada? Si no, qué giro o desplazamiento pedir."""
import json
import time

import numpy as np
import pytest

from lewelder import contrato as c
from lewelder.alcance import (
    Alcance,
    aplicar,
    frase_propuesta,
    marco_cordon,
)
from lewelder.contrato import Anclaje, TipoJunta

T, ESQUINA = TipoJunta.T, TipoJunta.ESQUINA


@pytest.fixture(scope="module")
def alcance():
    a = Alcance()
    a.preparar()  # tabla de alcance (se cachea en disco) y modelo
    return a


def _base(x=c.POSICION_BASE.x, y=c.POSICION_BASE.y, giro=c.POSICION_BASE.giro):
    return Anclaje("montaje", x, y, giro)


# --- geometría ---------------------------------------------------------------------------------------------------
def test_marco_del_cordon_por_defecto():
    origen, R = marco_cordon(T)
    # giro 0: el cordón avanza en +Y de la mesa y empieza en -LONGITUD_CORDON/2; Y del cordón (hacia la chapa
    # móvil) apunta al robot (-X de la mesa); Z = cara de la base apoyada en la mesa.
    assert np.allclose(origen, [c.POSICION_BASE.x, c.POSICION_BASE.y - c.LONGITUD_CORDON / 2, c.GROSOR_CHAPA])
    assert np.allclose(R[:, 0], [0, 1, 0]) and np.allclose(R[:, 1], [-1, 0, 0]) and np.allclose(R[:, 2], [0, 0, 1])
    origen_e, _ = marco_cordon(ESQUINA)
    assert origen_e[0] == pytest.approx(c.POSICION_BASE.x - c.Y_CORDON[ESQUINA])


def test_frases_para_el_personaje():
    assert frase_propuesta(90, 0, 0) == "gírala 90° hacia mi izquierda"
    assert frase_propuesta(-45, 0, 0) == "gírala 45° hacia mi derecha"
    assert frase_propuesta(180, 0, 0) == "dale media vuelta"
    assert frase_propuesta(0, 200, 0) == "acércala un palmo"
    assert frase_propuesta(0, -100, 0) == "aléjala medio palmo"
    assert frase_propuesta(0, 0, 50) == "muévela un poco a mi izquierda"
    assert frase_propuesta(30, 100, -50) == (
        "gírala 30° hacia mi izquierda, acércala medio palmo y muévela un poco a mi derecha")


def test_aplicar_propuesta():
    nueva = aplicar(_base(250, 0, -90), giro=90, acercar_mm=50, lateral_mm=0)
    # acercar = hacia el eje del robot (en la línea robot-base); lateral = a la izquierda del robot (+Y)
    assert (nueva.x, nueva.y, nueva.giro) == pytest.approx((200.0, 0.0, 0.0), abs=0.1)
    lado = aplicar(_base(250, 0, 0), giro=-30, acercar_mm=0, lateral_mm=40)
    assert (lado.x, lado.y, lado.giro) == pytest.approx((250.0, 40.0, -30.0), abs=0.1)


# --- alcance -----------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("junta", [T, ESQUINA])
def test_pose_por_defecto_llega(alcance, junta):
    r = alcance.comprobar(junta)
    assert r.llega and r.suelda and r.senala
    assert r.propuesta is None
    assert r.error_mm < 0.5 and r.error_grados < 0.5
    assert r.holgura_grados >= 3.0
    json.dumps(r.a_dict(), allow_nan=False)


@pytest.mark.parametrize("junta", [T, ESQUINA])
@pytest.mark.parametrize("giro", [-90.0, 180.0])
def test_girada_no_llega_y_propone_un_giro_que_llega(alcance, junta, giro):
    r = alcance.comprobar(junta, _base(giro=giro))
    assert not r.llega
    assert r.propuesta is not None
    assert r.propuesta.giro != 0
    assert r.frase.startswith("gírala") or r.frase.startswith("dale media vuelta")
    arreglada = alcance.comprobar(junta, r.propuesta.base, proponer=False)
    assert arreglada.llega


@pytest.mark.parametrize("junta", [T, ESQUINA])
def test_muy_lejos_no_llega_y_propone_acercarla(alcance, junta):
    r = alcance.comprobar(junta, _base(x=460.0))
    assert not r.llega and not r.suelda
    p = r.propuesta
    assert p is not None and p.acercar_mm > 0
    assert "acércala" in r.frase
    assert alcance.comprobar(junta, p.base, proponer=False).llega


def test_a_un_lado_tambien_llega(alcance):
    # Un poco desplazada y girada (como la dejaría alguien sin cuidado) todavía llega
    assert alcance.comprobar(T, _base(240.0, 60.0, 20.0)).llega


def test_rapido(alcance):
    for junta, base in [(T, _base()), (ESQUINA, _base(giro=-90.0)), (T, _base(x=460.0))]:
        alcance.limpiar_cache()
        t0 = time.perf_counter()
        r = alcance.comprobar(junta, base)
        ms = (time.perf_counter() - t0) * 1000
        assert ms < 200, (junta, base, ms)
        assert r.ms == pytest.approx(ms, abs=20)
    # Repetir la misma consulta (el servidor la hace a cada fotograma) es inmediato
    t0 = time.perf_counter()
    alcance.comprobar(T, _base(x=460.0))
    assert time.perf_counter() - t0 < 0.005


def test_marco_cualquiera(alcance):
    """Con el marco del cordón que dé el reconocimiento 3D (origen + giro), sin pasar por la base."""
    origen, R = marco_cordon(T)
    assert alcance.comprobar_marco(origen, R).suelda
    lejos = origen + np.array([300.0, 0.0, 0.0])
    assert not alcance.comprobar_marco(lejos, R).suelda
