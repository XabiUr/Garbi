"""Tests del fantasma del robot: referencia por tramo y carrera en vivo del juez contra él."""
import json
import time

import pytest

from lewelder import contrato as c
from lewelder.contrato import Muestra, TipoJunta
from lewelder.fantasma import Carrera, Fantasma
from lewelder.metricas import EvaluadorEnVivo
from lewelder.sintetico import pasada_sintetica

T = TipoJunta.T
ESQUINA = TipoJunta.ESQUINA
BUENA = {"angulo_trabajo": 45.0, "angulo_avance": 10.0}


def _robot(**kw):
    """La pasada del robot: limpia, a 5 mm/s y con los ángulos de libro (como el guion de la simulación)."""
    return pasada_sintetica(T, **{**BUENA, **kw})


def _carrera(fantasma, muestras_juez):
    carrera = Carrera(fantasma)
    estados = [carrera.anadir(m) for m in muestras_juez]
    return carrera, estados


def _en_x(estados, x):
    return next(e for e in estados if e["x_juez"] is not None and e["x_juez"] >= x)


# --- referencia --------------------------------------------------------------------------------------------------
def test_fantasma_referencia_por_tramo():
    f = Fantasma(_robot(), T)
    assert len(f.tramos) == c.N_TRAMOS
    for tr in f.tramos:
        assert tr.velocidad == pytest.approx(5.0, abs=0.2)
        assert tr.angulo_trabajo == pytest.approx(45.0, abs=0.5)
        assert tr.angulo_avance == pytest.approx(10.0, abs=0.5)
        assert tr.calidad >= 0.95
        assert tr.t_fin - tr.t_inicio == pytest.approx(1.0, abs=0.05)  # 5 mm a 5 mm/s
    assert f.duracion == pytest.approx(24.0, abs=0.2)
    assert f.x_en(0.0) == pytest.approx(0.0, abs=0.2)
    assert f.x_en(10.0) == pytest.approx(50.0, abs=0.5)
    assert f.x_en(100.0) == pytest.approx(c.LONGITUD_CORDON, abs=0.5)
    assert f.t_en(60.0) == pytest.approx(12.0, abs=0.1)


def test_fantasma_del_robot_a_3_mm_cuenta():
    # El robot de la simulación suelda con la punta a ALTURA_PUNTA (3 mm): como fantasma vale igual.
    f = Fantasma(_robot(altura_punta=c.ALTURA_PUNTA), T)
    assert min(tr.calidad for tr in f.tramos) >= 0.95


def test_fantasma_posicion_para_pintar():
    f = Fantasma(_robot(), T)
    p = f.posicion(10.0)
    assert p["x"] == pytest.approx(50.0, abs=0.5)
    assert p["angulo_trabajo"] == pytest.approx(45.0, abs=0.5)
    assert f.posicion(-1.0)["x"] == pytest.approx(0.0, abs=0.5)
    d = f.a_dict()
    assert len(d["tramos"]) == c.N_TRAMOS
    assert 200 <= len(d["trazo"]) <= 300  # a 10 Hz
    json.dumps(d, allow_nan=False)


def test_fantasma_sin_soldar_no_rompe():
    f = Fantasma([], T)
    assert f.duracion == 0.0
    assert f.t_en(50.0) is None
    carrera, estados = _carrera(f, pasada_sintetica(T, **BUENA))
    assert carrera.terminar().ganador == "juez"


# --- carrera en vivo ---------------------------------------------------------------------------------------------
def test_juez_mas_rapido_va_por_delante():
    f = Fantasma(_robot(), T)
    _, estados = _carrera(f, pasada_sintetica(T, velocidad=6.0, **BUENA))
    e = _en_x(estados, 60.0)  # el juez llega a 60 mm en 10 s; el robot, en 12 s (en 10 s va por 50 mm)
    assert e["ventaja_mm"] == pytest.approx(10.0, abs=1.0)
    assert e["ventaja_s"] == pytest.approx(2.0, abs=0.2)
    assert e["velocidad_juez"] == pytest.approx(6.0, abs=0.3)
    assert e["velocidad_fantasma"] == pytest.approx(5.0, abs=0.3)
    json.dumps(e, allow_nan=False)


def test_juez_mas_lento_va_por_detras():
    f = Fantasma(_robot(), T)
    _, estados = _carrera(f, pasada_sintetica(T, velocidad=4.0, **BUENA))
    e = _en_x(estados, 60.0)  # 15 s frente a 12 s
    assert e["ventaja_mm"] == pytest.approx(-15.0, abs=1.0)
    assert e["ventaja_s"] == pytest.approx(-3.0, abs=0.2)


def test_juez_igual_que_el_robot_empata():
    f = Fantasma(_robot(), T)
    carrera, estados = _carrera(f, pasada_sintetica(T, **BUENA))
    e = _en_x(estados, 60.0)
    assert e["ventaja_mm"] == pytest.approx(0.0, abs=0.5)
    assert e["ventaja_s"] == pytest.approx(0.0, abs=0.1)
    assert e["dif_trabajo"] == pytest.approx(0.0, abs=0.5)
    assert e["va_ganando"] == "empate"
    r = carrera.terminar()
    assert r.ganador == "empate"
    assert r.por_tramo == ["empate"] * c.N_TRAMOS


def test_diferencia_de_angulo():
    f = Fantasma(_robot(), T)
    _, estados = _carrera(f, pasada_sintetica(T, angulo_trabajo=70.0, angulo_avance=0.0))
    e = _en_x(estados, 60.0)
    assert e["dif_trabajo"] == pytest.approx(25.0, abs=0.5)
    assert e["dif_avance"] == pytest.approx(-10.0, abs=0.5)


def test_el_juez_que_suelda_mejor_gana_y_adelanta():
    # El robot se desvía en la segunda mitad; el juez suelda limpio: empatan al principio y luego gana el juez.
    robot = _robot(desvio_mm=0.0)
    robot = [Muestra(m.t, m.x, 4.5 if m.x > 60 else m.y, m.z, m.gatillo, m.angulo_trabajo, m.angulo_avance)
             for m in robot]
    f = Fantasma(robot, T)
    carrera, estados = _carrera(f, pasada_sintetica(T, **BUENA))
    assert _en_x(estados, 50.0)["va_ganando"] == "empate"
    assert _en_x(estados, 100.0)["va_ganando"] == "juez"
    cambios = [e["lider_cambia"] for e in estados if e["lider_cambia"]]
    assert cambios == ["juez"]
    r = carrera.terminar()
    assert r.ganador == "juez"
    assert r.tramos_ganados["juez"] >= 10 and r.tramos_ganados["fantasma"] == 0
    assert all(g == "empate" for g in r.por_tramo[:11])
    json.dumps(r.a_dict(), allow_nan=False)


def test_el_robot_gana_si_el_juez_deja_un_hueco():
    f = Fantasma(_robot(), T)
    carrera, estados = _carrera(f, pasada_sintetica(T, huecos=[(40.0, 60.0)], **BUENA))
    assert _en_x(estados, 80.0)["va_ganando"] == "fantasma"
    r = carrera.terminar()
    assert r.ganador == "fantasma"
    assert r.por_tramo[8:12] == ["fantasma"] * 4


def test_carrera_con_evaluador_compartido():
    """Con el evaluador del servidor (lo alimenta quien llama) el resultado es el mismo que con el propio."""
    f = Fantasma(_robot(), ESQUINA)
    juez = pasada_sintetica(ESQUINA, huecos=[(40.0, 50.0)], **BUENA)
    ev = EvaluadorEnVivo(ESQUINA)
    compartida = Carrera(f, evaluador=ev)
    for m in juez:
        ev.anadir(m)
        compartida.anadir(m)
    propia, _ = _carrera(f, juez)
    assert compartida.terminar().a_dict() == propia.terminar().a_dict()


def test_carrera_rapida_para_30_hz():
    f = Fantasma(_robot(), T)
    juez = pasada_sintetica(T, frecuencia=30, **BUENA)
    carrera = Carrera(f)
    t0 = time.perf_counter()
    for m in juez:
        carrera.anadir(m)
    por_muestra = (time.perf_counter() - t0) / len(juez)
    assert por_muestra < 0.005  # de sobra para 30 Hz
