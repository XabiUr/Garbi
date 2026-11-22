"""Tests del generador de pasadas sintéticas."""
import numpy as np
import pytest

from lewelder import contrato as c
from lewelder.sintetico import pasada_sintetica


def _xs(muestras):
    return np.array([m.x for m in muestras])


def test_reproducible_con_semilla():
    a = pasada_sintetica(c.TipoPieza.RECTA, temblor_mm=1.0, semilla=3)
    b = pasada_sintetica(c.TipoPieza.RECTA, temblor_mm=1.0, semilla=3)
    d = pasada_sintetica(c.TipoPieza.RECTA, temblor_mm=1.0, semilla=4)
    assert [m.a_dict() for m in a] == [m.a_dict() for m in b]
    assert [m.y for m in a] != [m.y for m in d]


def test_empieza_antes_y_termina_despues_del_cordon():
    m = pasada_sintetica(c.TipoPieza.RECTA)
    xs = _xs(m)
    assert xs.min() < 0 and xs.max() > c.LONGITUD_CORDON
    # Al principio y al final el gatillo está suelto (la persona se coloca y se retira).
    assert not m[0].gatillo and not m[-1].gatillo


def test_tiempo_y_frecuencia():
    m = pasada_sintetica(c.TipoPieza.RECTA, frecuencia=50)
    t = np.array([s.t for s in m])
    assert np.allclose(np.diff(t), 1 / 50)
    # 120 mm a 5 mm/s son 24 s de cordón; con el margen de antes y después, algo más.
    assert 24 < t[-1] - t[0] < 30


def test_velocidad_constante_sin_temblor():
    m = pasada_sintetica(c.TipoPieza.RECTA, velocidad=4.0)
    en_cordon = [s for s in m if 0 <= s.x <= c.LONGITUD_CORDON]
    dt = en_cordon[-1].t - en_cordon[0].t
    assert (en_cordon[-1].x - en_cordon[0].x) / dt == pytest.approx(4.0, rel=0.01)


def test_hueco_suelta_el_gatillo():
    m = pasada_sintetica(c.TipoPieza.RECTA, huecos=[(40.0, 60.0)])
    for s in m:
        if 40.5 < s.x < 59.5:
            assert not s.gatillo
        elif 0 <= s.x <= 39.5 or 60.5 <= s.x <= c.LONGITUD_CORDON:
            assert s.gatillo


def test_desvio_y_altura():
    m = pasada_sintetica(c.TipoPieza.RECTA, desvio_mm=7.0)
    assert all(s.y == pytest.approx(7.0) for s in m)
    assert all(s.z == pytest.approx(c.ALTURA_PUNTA) for s in m)


def test_temblor_mueve_la_punta():
    m = pasada_sintetica(c.TipoPieza.RECTA, temblor_mm=1.0, semilla=1)
    ys = np.array([s.y for s in m])
    assert 0.5 < ys.std() < 1.5


def test_parada_se_queda_quieta():
    m = pasada_sintetica(c.TipoPieza.RECTA, paradas=[(45.0, 1.5)])
    quietas = [s for s in m if abs(s.x - 45.0) < 1e-9]
    assert quietas
    assert quietas[-1].t - quietas[0].t == pytest.approx(1.5, abs=0.05)
    assert all(s.gatillo for s in quietas)


def test_angulos():
    sin = pasada_sintetica(c.TipoPieza.RECTA)
    assert all(s.angulo_trabajo is None and s.angulo_avance is None for s in sin)
    con = pasada_sintetica(c.TipoPieza.T, angulo_trabajo=45.0, angulo_avance=10.0, ruido_angulo=2.0, semilla=2)
    trabajo = np.array([s.angulo_trabajo for s in con])
    assert trabajo.mean() == pytest.approx(45.0, abs=0.5)
    assert 1.0 < trabajo.std() < 3.0
    assert np.mean([s.angulo_avance for s in con]) == pytest.approx(10.0, abs=0.5)


def test_v2_punta_apoyada_por_defecto():
    m = pasada_sintetica(c.TipoJunta.ESQUINA, temblor_mm=0.3, semilla=2)
    assert all(0.0 <= s.z < c.ALTURA_APOYO for s in m)
    # Los tipos v1 siguen a la altura de siempre
    assert all(s.z == pytest.approx(c.ALTURA_PUNTA) for s in pasada_sintetica("t"))


def test_altura_y_tramos_levantados():
    m = pasada_sintetica(c.TipoJunta.T, altura_punta=1.0, levantada=[(40.0, 60.0)], altura_levantada=7.0)
    for s in m:
        if 40.0 <= s.x < 60.0:
            assert s.z == pytest.approx(7.0)
            assert s.gatillo  # levantar no suelta el gatillo
        else:
            assert s.z == pytest.approx(1.0)


def test_valores_son_float_de_python():
    m = pasada_sintetica(c.TipoPieza.RECTA, temblor_mm=0.5, angulo_trabajo=90.0, angulo_avance=5.0)
    s = m[len(m) // 2]
    assert type(s.x) is float and type(s.y) is float and type(s.angulo_trabajo) is float
    assert type(s.gatillo) is bool
