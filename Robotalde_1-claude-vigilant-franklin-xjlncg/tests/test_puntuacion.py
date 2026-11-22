"""Tests de la puntuación arcade (puntos, combos, ritmo, penalizaciones, bonus), el marcador en vivo, el ranking del
día y las insignias."""
import json
from datetime import date

import pytest

from lewelder import contrato as c
from lewelder.contrato import Muestra, TipoJunta
from lewelder.fantasma import Fantasma
from lewelder.metricas import evaluar_pasada
from lewelder.puntuacion import (
    BONUS_FANTASMA,
    BONUS_PERFECTA,
    COMBO_MAX,
    PENAL_QUEMADO,
    PENAL_SIN_APOYO,
    MarcadorEnVivo,
    Ranking,
    multiplicador_combo,
    multiplicador_ritmo,
    nivel_jugador,
    puntuar,
)
from lewelder.sintetico import pasada_sintetica

T = TipoJunta.T
ESQUINA = TipoJunta.ESQUINA
BUENA = {"angulo_trabajo": 45.0, "angulo_avance": 10.0}


def _puntos(junta=T, **kw):
    return puntuar(evaluar_pasada(pasada_sintetica(junta, **{**BUENA, **kw}), junta))


def _en_vivo(muestras, junta=T, fantasma=None):
    marcador = MarcadorEnVivo(junta, fantasma=fantasma)
    eventos = []
    for m in muestras:
        eventos += marcador.anadir(m)
    final = marcador.terminar()
    return marcador, eventos + final.eventos_finales, final


# --- reglas ------------------------------------------------------------------------------------------------------
def test_multiplicador_de_combo_sube_y_tiene_tope():
    assert [multiplicador_combo(k) for k in range(0, 14)] == [1, 1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3, 4]
    assert multiplicador_combo(100) == COMBO_MAX


def test_multiplicador_de_ritmo():
    assert multiplicador_ritmo(0.0) == pytest.approx(1.25)
    assert multiplicador_ritmo(0.05) == pytest.approx(1.25)
    assert multiplicador_ritmo(0.15) == pytest.approx(1.125)
    assert multiplicador_ritmo(0.4) == pytest.approx(1.0)


# --- rondas completas --------------------------------------------------------------------------------------------
@pytest.mark.parametrize("junta", [T, ESQUINA])
def test_ronda_perfecta_unos_10000(junta):
    p = _puntos(junta)
    assert p.perfecta
    assert p.combo_max == c.N_TRAMOS
    assert p.tramos_bien == c.N_TRAMOS
    assert p.desglose["bonus_perfecta"] == BONUS_PERFECTA
    assert 9_500 <= p.total <= 10_500
    json.dumps(p.a_dict(), allow_nan=False)


@pytest.mark.parametrize(
    "kw",
    [
        {"temblor_mm": 0.3, "semilla": 1, "huecos": [(40.0, 60.0)]},  # se le escapa el gatillo
        {"temblor_mm": 0.3, "semilla": 2, "paradas": [(70.0, 1.2)]},  # un quemado
        {"temblor_mm": 0.7, "semilla": 3},  # mano temblona: ritmo irregular
        {"velocidad": 6.5, "semilla": 4},  # va con prisa
        {"velocidad": 3.5},  # va lento
        {"desvio_mm": 3.0},  # algo desviado
        {"levantada": [(30.0, 50.0)], "semilla": 5},  # suelda al aire un rato
        {"angulo_trabajo": 65.0, "semilla": 6},  # antorcha demasiado vertical todo el rato
        {"huecos": [(60.0, 200.0)]},  # solo medio cordón
    ],
)
def test_rondas_normales_entre_2000_y_9000(kw):
    p = _puntos(**kw)
    assert not p.perfecta
    assert 2_000 <= p.total <= 9_000, (kw, p.total, p.desglose)


def test_ronda_mala_por_debajo():
    p = _puntos(huecos=[(20.0, 35.0), (80.0, 90.0)], paradas=[(60.0, 1.0)], temblor_mm=0.4, semilla=7)
    assert 0 < p.total < 2_000


def test_sin_soldar_cero_puntos():
    p = _puntos(huecos=[(-10.0, 200.0)])
    assert p.total == 0
    assert p.combo_max == 0


def test_combo_se_rompe_con_un_hueco():
    entera = _puntos()
    rota = _puntos(huecos=[(57.0, 63.0)])  # un hueco en medio rompe la racha
    assert rota.combo_max < entera.combo_max
    assert rota.total < entera.total - 1_500  # se nota: se pierde el combo, el ritmo y la ronda perfecta


def test_quemado_resta():
    limpia = _puntos(temblor_mm=0.2, semilla=1)
    quemada = _puntos(temblor_mm=0.2, semilla=1, paradas=[(47.0, 1.5)])
    assert quemada.desglose["penal_quemados"] == -PENAL_QUEMADO
    assert quemada.total < limpia.total - PENAL_QUEMADO


def test_soldar_sin_apoyar_resta():
    p = _puntos(levantada=[(30.0, 40.0)])
    assert p.desglose["penal_sin_apoyo"] == -PENAL_SIN_APOYO


def test_bonus_por_ganar_al_fantasma():
    robot = pasada_sintetica(T, **BUENA)
    robot = [Muestra(m.t, m.x, 4.5 if m.x > 60 else m.y, m.z, m.gatillo, m.angulo_trabajo, m.angulo_avance)
             for m in robot]
    f = Fantasma(robot, T)
    _, eventos, final = _en_vivo(pasada_sintetica(T, **BUENA), fantasma=f)
    assert final.gana_fantasma
    assert final.desglose["bonus_fantasma"] == BONUS_FANTASMA
    textos = [e.texto for e in eventos]
    assert "¡ADELANTAS AL ROBOT!" in textos
    assert "¡HAS GANADO AL ROBOT!" in textos
    # Contra un robot perfecto, una ronda perfecta empata: sin bonus de fantasma
    _, _, empate = _en_vivo(pasada_sintetica(T, **BUENA), fantasma=Fantasma(pasada_sintetica(T, **BUENA), T))
    assert not empate.gana_fantasma and empate.desglose["bonus_fantasma"] == 0


# --- marcador en vivo y eventos ----------------------------------------------------------------------------------
def test_en_vivo_eventos_de_combo_en_orden():
    marcador, eventos, final = _en_vivo(pasada_sintetica(T, **BUENA))
    combos = [e.texto for e in eventos if e.tipo == "combo"]
    assert combos == ["COMBO x2", "COMBO x3", "COMBO x4"]
    assert [e.texto for e in eventos if e.tipo == "perfecta"] == ["¡RONDA PERFECTA!"]
    tiempos = [e.t for e in eventos if e.t is not None]  # los del final de la ronda no llevan tiempo
    assert tiempos == sorted(tiempos)
    assert all(e.t is None for e in final.eventos_finales)
    json.dumps([e.a_dict() for e in eventos], allow_nan=False)


@pytest.mark.parametrize(
    "kw",
    [
        {},
        {"temblor_mm": 0.3, "semilla": 1, "huecos": [(40.0, 60.0)]},
        {"temblor_mm": 0.3, "semilla": 2, "paradas": [(70.0, 1.2)]},
        {"levantada": [(30.0, 50.0)], "semilla": 5},
    ],
)
def test_en_vivo_suma_lo_mismo_que_la_cuenta_final(kw):
    marcador, eventos, final = _en_vivo(pasada_sintetica(T, **{**BUENA, **kw}))
    assert sum(e.puntos for e in eventos) == final.total
    assert marcador.estado()["puntos"] == final.total


def test_en_vivo_quemado_y_combo_roto():
    _, eventos, final = _en_vivo(pasada_sintetica(T, paradas=[(70.0, 1.5)], **BUENA))
    quemados = [e for e in eventos if e.tipo == "quemado"]
    assert len(quemados) == 1
    assert quemados[0].texto == "¡QUEMADO!" and quemados[0].puntos == -PENAL_QUEMADO
    assert 15.0 < quemados[0].t < 16.5  # en cuanto se detecta la parada (llega a 70 mm a los 15,7 s)
    assert any(e.tipo == "combo_roto" for e in eventos)


def test_en_vivo_aviso_de_apoyo_como_evento():
    _, eventos, _ = _en_vivo(pasada_sintetica(T, levantada=[(30.0, 50.0)], **BUENA))
    sin_apoyo = [e for e in eventos if e.tipo == "sin_apoyo"]
    assert len(sin_apoyo) == 1
    assert sin_apoyo[0].texto == "¡APOYA LA ANTORCHA!"


def test_en_vivo_estado_para_la_tablet():
    marcador = MarcadorEnVivo(T, fantasma=Fantasma(pasada_sintetica(T, **BUENA), T))
    for m in pasada_sintetica(T, **BUENA):
        marcador.anadir(m)
        if m.x >= 60.0:
            break
    e = marcador.estado()
    assert e["racha"] >= 10 and e["combo"] == 3
    assert e["puntos"] > 0
    assert e["carrera"]["va_ganando"] == "empate"
    json.dumps(e, allow_nan=False)


# --- ranking del día ---------------------------------------------------------------------------------------------
HOY = date(2026, 11, 21)


def test_ranking_ordena_empata_y_top10(tmp_path):
    r = Ranking(tmp_path / "ranking.json", hoy=HOY)
    for i, puntos in enumerate([5000, 7000, 3000, 7000, 9000, 1000, 2000, 4000, 6000, 8000, 500]):
        r.anadir(f"A{chr(65 + i)}C", puntos, "t", "oficial")
    top = r.top()
    assert len(top) == 10
    assert [e.puntos for e in top] == [9000, 8000, 7000, 7000, 6000, 5000, 4000, 3000, 2000, 1000]
    # Empate: el que lo hizo antes queda delante
    assert [e.iniciales for e in top if e.puntos == 7000] == ["ABC", "ADC"]
    assert r.posicion(7000) == 5  # empatar no adelanta a nadie
    assert r.posicion(1000) is None  # empatar con el décimo no entra
    assert r.posicion(1001) == 10


def test_ranking_persiste_y_solo_cuenta_hoy(tmp_path):
    ruta = tmp_path / "ranking.json"
    ayer = Ranking(ruta, hoy=date(2026, 11, 20))
    ayer.anadir("AYE", 9999, "esquina", "maestro")
    hoy = Ranking(ruta, hoy=HOY)
    assert hoy.top() == []
    assert hoy.anadir("abc", 4200, TipoJunta.ESQUINA, "aprendiz") == 1
    otra = Ranking(ruta, hoy=HOY)
    (e,) = otra.top()
    assert (e.iniciales, e.puntos, e.junta, e.nivel, e.fecha) == ("ABC", 4200, "esquina", "aprendiz", "2026-11-21")
    assert len(json.loads(ruta.read_text(encoding="utf-8"))["partidas"]) == 2


def test_record(tmp_path):
    r = Ranking(tmp_path / "ranking.json", hoy=HOY)
    assert r.es_record(100)
    assert not r.es_record(0)
    r.anadir("AAA", 5000, "t", "oficial")
    assert not r.es_record(5000)  # igualar no es récord
    assert r.es_record(5001)
    assert r.record.iniciales == "AAA"


@pytest.mark.parametrize("malas", ["AB", "ABCD", "A1C", "", "a c"])
def test_iniciales_invalidas(tmp_path, malas):
    with pytest.raises(ValueError):
        Ranking(None, hoy=HOY).anadir(malas, 100, "t", "oficial")


def test_ranking_en_memoria_y_fichero_roto(tmp_path):
    ruta = tmp_path / "ranking.json"
    ruta.write_text("{esto no es json", encoding="utf-8")
    r = Ranking(ruta, hoy=HOY)
    assert r.top() == []
    r.anadir("ÑAN", 10, "t", "aprendiz")
    assert Ranking(ruta, hoy=HOY).top()[0].iniciales == "ÑAN"
    assert Ranking(None, hoy=HOY).top() == []


# --- insignias y niveles -----------------------------------------------------------------------------------------
def test_niveles_del_jugador():
    assert nivel_jugador(set()) == "aprendiz"
    assert nivel_jugador({("t", "aprendiz")}) == "aprendiz"
    assert nivel_jugador({("t", "aprendiz"), ("esquina", "oficial")}) == "oficial"
    assert nivel_jugador({("t", "oficial"), ("esquina", "maestro")}) == "maestro"


def test_anotar_ronda_insignias_y_ascenso(tmp_path):
    r = Ranking(tmp_path / "ranking.json", hoy=HOY)
    primera = r.anotar_ronda("JMO", 6000, "t", "aprendiz", aprobado=True)
    assert primera.posicion == 1 and primera.record
    assert primera.insignia_nueva == "unión en T · aprendiz"
    assert primera.nivel_antes == primera.nivel_despues == "aprendiz"
    textos = [e.texto for e in primera.eventos]
    assert "¡NUEVO RÉCORD!" in textos
    segunda = r.anotar_ronda("JMO", 5000, "esquina", "aprendiz", aprobado=True)
    assert not segunda.record
    assert segunda.nivel_despues == "oficial"
    assert "¡ASCIENDES A OFICIAL!" in [e.texto for e in segunda.eventos]
    suspensa = r.anotar_ronda("JMO", 800, "t", "oficial", aprobado=False)
    assert suspensa.insignia_nueva is None
    assert Ranking(tmp_path / "ranking.json", hoy=HOY).insignias("JMO") == {("t", "aprendiz"),
                                                                           ("esquina", "aprendiz")}
