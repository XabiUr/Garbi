"""Tests de las métricas, la nota y el evaluador en vivo, con pasadas sintéticas."""
import json

import pytest

from lewelder import contrato as c
from lewelder.contrato import Muestra, TipoPieza
from lewelder.metricas import (
    EvaluadorEnVivo,
    Resultado,
    ResultadoTramo,
    evaluar_pasada,
    filtrar_demostraciones,
)
from lewelder.sintetico import pasada_sintetica

RECTA = TipoPieza.RECTA
T = TipoPieza.T


def _contiene(avisos, trozo):
    return any(trozo in a for a in avisos)


# --- pasada perfecta ---------------------------------------------------------------------------------------------
def test_pasada_perfecta():
    r = evaluar_pasada(pasada_sintetica(RECTA, angulo_trabajo=90.0, angulo_avance=10.0), RECTA)
    assert isinstance(r, Resultado)
    assert r.nota >= 9.0
    assert r.aprobado
    assert r.huecos == []
    assert r.cobertura_pct == pytest.approx(100.0)
    assert r.n_quemados == 0
    assert r.velocidad_media == pytest.approx(5.0, abs=0.1)
    assert r.pct_tiempo_velocidad_ok == pytest.approx(100.0, abs=1.0)
    assert r.desvio_medio_mm == pytest.approx(0.0, abs=0.01)
    assert r.pct_tiempo_angulo_ok == pytest.approx(100.0)
    assert len(r.tramos) == c.N_TRAMOS
    assert all(isinstance(tr, ResultadoTramo) and tr.cubierto for tr in r.tramos)
    assert not _contiene(r.avisos, "rápido") and not _contiene(r.avisos, "quemado")


def test_pasada_perfecta_en_t_con_ruido_realista():
    m = pasada_sintetica(T, temblor_mm=0.2, angulo_trabajo=45.0, angulo_avance=10.0, ruido_angulo=2.0, semilla=5)
    r = evaluar_pasada(m, T)
    assert r.nota >= 9.0
    assert r.huecos == []


# --- huecos ------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("hueco", [(40.0, 60.0), (42.0, 58.0), (0.0, 12.0), (101.0, 120.0)])
def test_hueco_detectado(hueco):
    r = evaluar_pasada(pasada_sintetica(RECTA, huecos=[hueco]), RECTA)
    assert len(r.huecos) == 1
    inicio, fin = r.huecos[0]
    assert abs(inicio - hueco[0]) <= 5.0
    assert abs(fin - hueco[1]) <= 5.0
    assert r.cobertura_pct < 100.0
    assert _contiene(r.avisos, "sin soldar")


def test_dos_huecos_y_nota_baja():
    r = evaluar_pasada(pasada_sintetica(RECTA, huecos=[(10.0, 30.0), (70.0, 100.0)]), RECTA)
    assert len(r.huecos) == 2
    perfecta = evaluar_pasada(pasada_sintetica(RECTA), RECTA)
    assert r.nota < perfecta.nota - 3.0


def test_huecos_fusionan_tramos_contiguos():
    r = evaluar_pasada(pasada_sintetica(RECTA, huecos=[(20.0, 50.0)]), RECTA)
    assert r.huecos == [(20.0, 50.0)]
    no_cubiertos = [tr.indice for tr in r.tramos if not tr.cubierto]
    assert no_cubiertos == list(range(4, 10))


# --- temblor -----------------------------------------------------------------------------------------------------
def test_pasada_temblorosa_peor_regularidad():
    perfecta = evaluar_pasada(pasada_sintetica(RECTA), RECTA)
    temblorosa = evaluar_pasada(pasada_sintetica(RECTA, temblor_mm=1.0, semilla=7), RECTA)
    assert temblorosa.cv_velocidad > perfecta.cv_velocidad
    assert temblorosa.pct_tiempo_velocidad_ok < perfecta.pct_tiempo_velocidad_ok
    assert temblorosa.desvio_medio_mm > perfecta.desvio_medio_mm
    assert temblorosa.nota < perfecta.nota
    assert temblorosa.cobertura_pct == pytest.approx(100.0)
    assert _contiene(temblorosa.avisos, "ritmo")


@pytest.mark.parametrize("semilla", range(5))
def test_temblor_moderado_no_inventa_quemados(semilla):
    # Límite medido: hasta ~0,5 mm de temblor lento no hay quemados falsos; con 1 mm el ruido ya los inventa.
    assert evaluar_pasada(pasada_sintetica(RECTA, temblor_mm=0.5, semilla=semilla), RECTA).n_quemados == 0


# --- quemado -----------------------------------------------------------------------------------------------------
def test_pasada_quemada():
    r = evaluar_pasada(pasada_sintetica(RECTA, paradas=[(45.0, 1.5)]), RECTA)
    assert r.n_quemados == 1
    assert r.puntos_quemados[0] == pytest.approx(45.0, abs=2.5)
    assert r.tramos[9].quemado
    assert sum(tr.quemado for tr in r.tramos) == 1
    assert _contiene(r.avisos, "punto quemado en 45 mm")
    assert r.nota < evaluar_pasada(pasada_sintetica(RECTA), RECTA).nota


@pytest.mark.parametrize("semilla", range(5))
def test_quemado_con_ruido_de_seguimiento(semilla):
    # El ruido de la punta no debe esconder una parada de 1 s.
    r = evaluar_pasada(pasada_sintetica(RECTA, paradas=[(70.0, 1.0)], temblor_mm=0.3, semilla=semilla), RECTA)
    assert r.n_quemados == 1
    assert r.puntos_quemados[0] == pytest.approx(70.0, abs=2.5)


@pytest.mark.parametrize("segundos, quema", [(0.3, False), (0.5, False), (0.7, True)])
def test_umbral_de_parada(segundos, quema):
    # El contrato dice "más de TIEMPO_QUEMADO" (0,6 s): una parada limpia de 0,5 s no quema y una de 0,7 s sí.
    r = evaluar_pasada(pasada_sintetica(RECTA, paradas=[(45.0, segundos)]), RECTA)
    assert (r.n_quemados == 1) is quema


def test_parada_con_gatillo_suelto_no_quema():
    r = evaluar_pasada(pasada_sintetica(RECTA, paradas=[(50.0, 2.0)], huecos=[(45.0, 55.0)]), RECTA)
    assert r.n_quemados == 0


# --- desvío y niveles --------------------------------------------------------------------------------------------
def test_desviada_7mm_segun_nivel():
    m = pasada_sintetica(RECTA, desvio_mm=7.0)
    oficial = evaluar_pasada(m, RECTA, "oficial")
    aprendiz = evaluar_pasada(m, RECTA, "aprendiz")
    assert oficial.cobertura_pct == 0.0
    assert oficial.huecos == [(0.0, c.LONGITUD_CORDON)]
    assert not oficial.aprobado
    assert aprendiz.cobertura_pct == pytest.approx(100.0)
    assert aprendiz.huecos == []
    assert _contiene(oficial.avisos, "te has desviado del cordón")
    assert oficial.desvio_medio_mm == pytest.approx(7.0)


def test_maestro_mas_exigente():
    m = pasada_sintetica(RECTA, desvio_mm=4.0)
    assert evaluar_pasada(m, RECTA, "oficial").cobertura_pct == pytest.approx(100.0)
    assert evaluar_pasada(m, RECTA, "maestro").cobertura_pct == 0.0


def test_nivel_invalido():
    with pytest.raises(ValueError):
        evaluar_pasada(pasada_sintetica(RECTA), RECTA, "experto")


def test_punta_levantada_no_cubre():
    m = pasada_sintetica(RECTA)
    levantada = [Muestra(s.t, s.x, s.y, 30.0, s.gatillo) for s in m]
    r = evaluar_pasada(levantada, RECTA)
    assert r.cobertura_pct == 0.0


# --- ángulos -----------------------------------------------------------------------------------------------------
def test_sin_angulos_nota_valida():
    r = evaluar_pasada(pasada_sintetica(RECTA), RECTA)
    assert r.pct_tiempo_angulo_ok is None
    assert r.puntuaciones["angulo"] is None
    assert all(tr.angulo_correcto is None for tr in r.tramos)
    assert 9.0 <= r.nota <= 10.0


def test_angulo_malo_en_t():
    buena = evaluar_pasada(pasada_sintetica(T, angulo_trabajo=45.0, angulo_avance=10.0), T)
    vertical = evaluar_pasada(pasada_sintetica(T, angulo_trabajo=80.0, angulo_avance=10.0), T)
    tumbada = evaluar_pasada(pasada_sintetica(T, angulo_trabajo=20.0, angulo_avance=10.0), T)
    assert vertical.pct_tiempo_angulo_ok == 0.0
    assert vertical.nota < buena.nota - 1.0
    assert all(tr.angulo_correcto is False for tr in vertical.tramos)
    assert _contiene(vertical.avisos, "tumba más la antorcha")
    assert _contiene(tumbada.avisos, "tumba menos la antorcha")
    assert not _contiene(buena.avisos, "tumba")


def test_angulo_de_avance_fuera_de_rango():
    r = evaluar_pasada(pasada_sintetica(RECTA, angulo_trabajo=90.0, angulo_avance=-10.0), RECTA)
    assert r.pct_tiempo_angulo_ok == 0.0
    assert _contiene(r.avisos, "empuja")


# --- velocidad ---------------------------------------------------------------------------------------------------
def test_demasiado_rapido_y_lento():
    rapida = evaluar_pasada(pasada_sintetica(RECTA, velocidad=10.0), RECTA)
    lenta = evaluar_pasada(pasada_sintetica(RECTA, velocidad=2.5), RECTA)
    assert rapida.velocidad_media == pytest.approx(10.0, abs=0.2)
    assert rapida.pct_tiempo_velocidad_ok < 5.0
    assert _contiene(rapida.avisos, "vas demasiado rápido")
    assert _contiene(lenta.avisos, "vas demasiado lento")
    assert lenta.n_quemados == 0


def test_frecuencia_baja_cubre_igual():
    r = evaluar_pasada(pasada_sintetica(RECTA, frecuencia=15, velocidad=6.0), RECTA)
    assert r.huecos == []


# --- casos límite y serialización --------------------------------------------------------------------------------
def test_pasada_vacia():
    r = evaluar_pasada([], RECTA)
    assert r.nota == 0.0
    assert not r.aprobado
    assert r.huecos == [(0.0, c.LONGITUD_CORDON)]
    json.dumps(r.a_dict(), allow_nan=False)


def test_a_dict_es_json():
    r = evaluar_pasada(pasada_sintetica(T, paradas=[(30.0, 1.0)], huecos=[(80.0, 90.0)]), T)
    d = json.loads(json.dumps(r.a_dict(), allow_nan=False))
    assert d["tipo"] == "t"
    assert d["nivel"] == "oficial"
    assert len(d["tramos"]) == c.N_TRAMOS
    assert d["huecos"] == [list(h) for h in r.huecos]


def test_acepta_tipo_como_texto():
    assert evaluar_pasada(pasada_sintetica(RECTA), "recta").nota >= 9.0


# --- evaluador en vivo -------------------------------------------------------------------------------------------
def _en_vivo(muestras, tipo=RECTA, nivel="oficial"):
    ev = EvaluadorEnVivo(tipo, nivel)
    avisos = []
    for m in muestras:
        avisos.extend((m.t, a) for a in ev.anadir(m))
    return ev, avisos


@pytest.mark.parametrize(
    "kwargs",
    [
        {},
        {"huecos": [(40.0, 60.0)], "paradas": [(80.0, 1.2)]},
        {"temblor_mm": 0.8, "semilla": 2, "angulo_trabajo": 45.0, "angulo_avance": 5.0, "ruido_angulo": 3.0},
    ],
)
def test_en_vivo_coherente_con_evaluar_pasada(kwargs):
    m = pasada_sintetica(T, **kwargs)
    ev, _ = _en_vivo(m, T)
    final = ev.terminar()
    esperado = evaluar_pasada(m, T)
    assert final.a_dict() == esperado.a_dict()
    assert ev.estado()["tramos_cubiertos"] == [tr.cubierto for tr in esperado.tramos]


def test_en_vivo_estado_durante_la_pasada():
    m = pasada_sintetica(RECTA)
    ev = EvaluadorEnVivo(RECTA)
    assert ev.estado()["nota_parcial"] is None
    mitad = None
    for s in m:
        ev.anadir(s)
        if mitad is None and s.x >= 60.0:
            mitad = ev.estado()
    assert mitad is not None
    assert 10 <= sum(mitad["tramos_cubiertos"]) <= 13
    assert mitad["velocidad"] == pytest.approx(5.0, abs=0.3)
    assert mitad["posicion"]["x"] == pytest.approx(60.0, abs=0.2)
    assert mitad["gatillo"] is True
    assert mitad["nota_parcial"] >= 9.0
    json.dumps(mitad, allow_nan=False)


def test_en_vivo_aviso_de_quemado_una_vez():
    _, avisos = _en_vivo(pasada_sintetica(RECTA, paradas=[(45.0, 2.0)]))
    quemados = [a for _, a in avisos if "punto quemado" in a]
    assert quemados == ["te has quedado parado: punto quemado en 45 mm"]


def test_en_vivo_antirrepeticion():
    m = pasada_sintetica(RECTA, velocidad=10.0)
    _, avisos = _en_vivo(m)
    tiempos = [t for t, a in avisos if a == "vas demasiado rápido"]
    assert len(tiempos) >= 2
    assert all(b - a >= 2.0 - 1e-9 for a, b in zip(tiempos, tiempos[1:]))


def test_en_vivo_desvio_y_angulo():
    _, avisos = _en_vivo(pasada_sintetica(T, desvio_mm=7.0, angulo_trabajo=20.0, angulo_avance=10.0), T)
    textos = {a for _, a in avisos}
    assert "te has desviado del cordón" in textos
    assert "tumba menos la antorcha" in textos


def test_en_vivo_perfecta_sin_avisos_de_fallo():
    _, avisos = _en_vivo(pasada_sintetica(RECTA, angulo_trabajo=90.0, angulo_avance=10.0))
    assert avisos == []


def _pasada_con_salto(a, b, salto_s, frecuencia=30, velocidad=5.0, entregar=True):
    """Suelda de 0 a `a`, suelta el gatillo y salta hasta `b` en `salto_s` s sin soldar (la cámara sigue viendo la
    punta si `entregar`), vuelve a apretar y acaba el cordón."""
    muestras, t, x, dt = [], 0.0, 0.0, 1.0 / frecuencia
    while x < a:
        muestras.append(Muestra(t, x, 0.0, 3.0, True))
        t, x = t + dt, x + velocidad * dt
    n = int(salto_s * frecuencia)
    for k in range(n):
        if entregar or k == 0:
            muestras.append(Muestra(t, a + (b - a) * (k + 1) / n, 0.0, 3.0, False))
        t += dt
    x = b
    while x <= c.LONGITUD_CORDON:
        muestras.append(Muestra(t, x, 0.0, 3.0, True))
        t, x = t + dt, x + velocidad * dt
    return muestras


@pytest.mark.parametrize("entregar", [True, False])
def test_en_vivo_tras_un_hueco_la_velocidad_no_mezcla_los_dos_lados(entregar):
    """Al volver a apretar tras un hueco saltado deprisa, la ventana de velocidad no debe cruzar el tramo con el
    gatillo suelto: antes salían ~80 mm/s y un "vas demasiado rápido" falso."""
    ev = EvaluadorEnVivo(RECTA)
    avisos, velocidades = [], []
    for m in _pasada_con_salto(40.0, 80.0, 0.4, entregar=entregar):
        avisos += ev.anadir(m)
        if m.gatillo and m.x >= 80.0 and ev.velocidad_fiable:
            velocidades.append(ev.velocidad)
        if m.gatillo and m.x >= 80.0 + 0.1:  # desde la segunda muestra tras apretar (con una no hay pendiente)
            assert ev.velocidad == pytest.approx(5.0, abs=0.2)
    assert "vas demasiado rápido" not in avisos and "vas demasiado lento" not in avisos
    assert "has soltado el gatillo: queda un hueco" in avisos
    assert velocidades and all(v == pytest.approx(5.0, abs=0.2) for v in velocidades)
    # Alias de los nombres antiguos
    assert ev._velocidad == ev.velocidad and ev._en_parada == ev.en_parada


def test_en_vivo_velocidad_fiable_solo_con_la_ventana_llena():
    ev = EvaluadorEnVivo(RECTA)
    fiable = []
    for m in pasada_sintetica(RECTA, frecuencia=30):
        ev.anadir(m)
        fiable.append((m.t, m.gatillo, ev.velocidad_fiable))
    t_apretar = next(t for t, g, _ in fiable if g)
    assert not any(f for t, g, f in fiable if t < t_apretar + 0.5)
    assert all(f for t, g, f in fiable if g and t > t_apretar + 0.6)
    assert not any(f for t, g, f in fiable if not g)


# --- filtro de dataset -------------------------------------------------------------------------------------------
def test_filtrar_demostraciones():
    resultados = [
        evaluar_pasada(pasada_sintetica(RECTA), RECTA),
        evaluar_pasada(pasada_sintetica(RECTA, huecos=[(20.0, 80.0)]), RECTA),
        evaluar_pasada(pasada_sintetica(RECTA, temblor_mm=0.3, semilla=1), RECTA),
        evaluar_pasada(pasada_sintetica(RECTA, desvio_mm=7.0), RECTA),
    ]
    assert filtrar_demostraciones(resultados, 8.0) == [0, 2]
    assert filtrar_demostraciones(resultados, 0.0) == [0, 1, 2, 3]
    assert filtrar_demostraciones([], 5.0) == []


# =================================================================================================================
# v2: soldando = gatillo + punta apoyada; junta en esquina; calidad por tramo
# =================================================================================================================
from lewelder.contrato import TipoJunta  # noqa: E402
from lewelder.metricas import (  # noqa: E402
    AVISO_APOYA,
    TRAMO_BIEN,
    Z_LEVANTADA,
    altura_apoyo_por_defecto,
    calidad_tramo,
    calidades,
)

ESQUINA = TipoJunta.ESQUINA
TJ = TipoJunta.T


def test_altura_de_apoyo_por_tipo():
    # v1 (TipoPieza o texto "recta"/"t") conserva el criterio de 15 mm; las juntas v2 usan el contrato (2 mm).
    assert altura_apoyo_por_defecto(RECTA) == Z_LEVANTADA
    assert altura_apoyo_por_defecto("t") == Z_LEVANTADA
    assert altura_apoyo_por_defecto(TJ) == c.ALTURA_APOYO
    assert altura_apoyo_por_defecto(ESQUINA) == c.ALTURA_APOYO
    assert altura_apoyo_por_defecto("esquina") == c.ALTURA_APOYO


@pytest.mark.parametrize("junta", [TJ, ESQUINA])
def test_v2_apoyada_perfecta(junta):
    m = pasada_sintetica(junta, temblor_mm=0.2, angulo_trabajo=45.0, angulo_avance=10.0, ruido_angulo=2.0, semilla=1)
    assert all(s.z < c.ALTURA_APOYO for s in m)  # las juntas v2 se sueldan con la punta apoyada
    r = evaluar_pasada(m, junta)
    assert r.tipo == junta.value
    assert r.altura_apoyo_mm == c.ALTURA_APOYO
    assert r.nota >= 9.0 and r.huecos == []
    assert r.n_sin_apoyo == 0
    assert AVISO_APOYA not in r.avisos


def test_v2_gatillo_sin_apoyo_no_cubre_y_avisa():
    # Gatillo apretado todo el rato pero con la punta 5 mm por encima entre 40 y 70 mm: eso no suelda.
    m = pasada_sintetica(TJ, angulo_trabajo=45.0, angulo_avance=10.0, levantada=[(40.0, 70.0)])
    assert all(s.gatillo for s in m if 0 <= s.x <= c.LONGITUD_CORDON)
    r = evaluar_pasada(m, TJ)
    assert len(r.huecos) == 1
    inicio, fin = r.huecos[0]
    assert abs(inicio - 40.0) <= 5.0 and abs(fin - 70.0) <= 5.0
    assert r.n_sin_apoyo == 1
    assert r.tiempo_sin_apoyo_s == pytest.approx(6.0, abs=0.3)
    assert AVISO_APOYA in r.avisos
    assert [tr.indice for tr in r.tramos if tr.sin_apoyo] == list(range(8, 14))


def test_v2_toda_levantada_no_suelda_nada():
    m = pasada_sintetica(ESQUINA, altura_punta=5.0)
    r = evaluar_pasada(m, ESQUINA)
    assert r.cobertura_pct == 0.0 and r.nota == 0.0
    assert AVISO_APOYA in r.avisos


def test_v2_el_mismo_trazo_en_v1_si_cuenta():
    # A 5 mm la punta está "sobre la pieza" con el criterio v1 (15 mm), pero no apoyada con el v2 (2 mm).
    m = pasada_sintetica("t", altura_punta=5.0)
    assert evaluar_pasada(m, "t").cobertura_pct == pytest.approx(100.0)
    assert evaluar_pasada(m, "t", apoyo=c.ALTURA_APOYO).cobertura_pct == 0.0
    assert evaluar_pasada(m, TJ).cobertura_pct == 0.0


def test_v2_levantar_con_el_gatillo_suelto_no_avisa_de_apoyo():
    m = pasada_sintetica(TJ, huecos=[(40.0, 60.0)], levantada=[(40.0, 60.0)])
    r = evaluar_pasada(m, TJ)
    assert r.n_sin_apoyo == 0 and AVISO_APOYA not in r.avisos


def test_v2_quemado_solo_con_la_punta_apoyada():
    apoyada = evaluar_pasada(pasada_sintetica(TJ, paradas=[(50.0, 1.5)]), TJ)
    levantada = evaluar_pasada(pasada_sintetica(TJ, paradas=[(50.0, 1.5)], levantada=[(45.0, 55.0)]), TJ)
    assert apoyada.n_quemados == 1
    assert levantada.n_quemados == 0


def test_esquina_angulo_de_trabajo_45():
    buena = evaluar_pasada(pasada_sintetica(ESQUINA, angulo_trabajo=45.0, angulo_avance=10.0), ESQUINA)
    vertical = evaluar_pasada(pasada_sintetica(ESQUINA, angulo_trabajo=85.0, angulo_avance=10.0), ESQUINA)
    tumbada = evaluar_pasada(pasada_sintetica(ESQUINA, angulo_trabajo=15.0, angulo_avance=10.0), ESQUINA)
    assert buena.pct_tiempo_angulo_ok == pytest.approx(100.0)
    assert vertical.pct_tiempo_angulo_ok == 0.0
    assert _contiene(vertical.avisos, "tumba más la antorcha")
    assert _contiene(tumbada.avisos, "tumba menos la antorcha")
    assert vertical.nota < buena.nota - 1.0


def test_tipo_desconocido():
    with pytest.raises(ValueError):
        evaluar_pasada(pasada_sintetica(RECTA), "cola de milano")


def test_v2_en_vivo_aviso_de_apoyo_y_coherencia():
    m = pasada_sintetica(TJ, angulo_trabajo=45.0, angulo_avance=10.0, levantada=[(40.0, 70.0)])
    ev, avisos = _en_vivo(m, TJ)
    apoya = [t for t, a in avisos if a == AVISO_APOYA]
    assert len(apoya) >= 1
    # Avisa en cuanto lleva un momento levantada (entre 40 y 70 mm a 5 mm/s: de ~9,7 s a ~15,7 s)
    assert 9.5 < apoya[0] < 10.5
    assert ev.n_sin_apoyo == 1
    assert ev.terminar().a_dict() == evaluar_pasada(m, TJ).a_dict()
    estado = ev.estado()
    assert estado["apoyada"] is True and estado["altura_apoyo"] == c.ALTURA_APOYO
    json.dumps(estado, allow_nan=False)


def test_v2_en_vivo_estado_apoyada():
    ev = EvaluadorEnVivo(TJ)
    ev.anadir(Muestra(0.0, 10.0, 0.0, 6.0, True))
    assert ev.estado()["apoyada"] is False
    ev.anadir(Muestra(0.1, 10.5, 0.0, 0.5, True))
    assert ev.estado()["apoyada"] is True


# --- calidad por tramo (la usan el fantasma y la puntuación arcade) -----------------------------------------------
def test_calidad_tramo_perfecta_y_mala():
    perfecta = evaluar_pasada(pasada_sintetica(TJ, angulo_trabajo=45.0, angulo_avance=10.0), TJ)
    q = calidades(perfecta)
    assert len(q) == c.N_TRAMOS
    assert min(q) >= 0.95
    rapida = evaluar_pasada(pasada_sintetica(TJ, velocidad=8.0, angulo_trabajo=45.0, angulo_avance=10.0), TJ)
    assert max(calidades(rapida)) < TRAMO_BIEN
    hueco = evaluar_pasada(pasada_sintetica(TJ, huecos=[(40.0, 60.0)]), TJ)
    qh = calidades(hueco)
    assert all(qh[i] == 0.0 for i in range(8, 12))
    assert calidad_tramo(hueco.tramos[2], hueco.tolerancia_mm) >= 0.95


def test_calidad_tramo_quemado_y_angulo():
    quemada = evaluar_pasada(pasada_sintetica(TJ, paradas=[(47.0, 1.5)]), TJ)
    q = calidades(quemada)
    assert q[9] < TRAMO_BIEN
    angulo_malo = evaluar_pasada(pasada_sintetica(TJ, angulo_trabajo=80.0, angulo_avance=10.0), TJ)
    assert max(calidades(angulo_malo)) < TRAMO_BIEN
