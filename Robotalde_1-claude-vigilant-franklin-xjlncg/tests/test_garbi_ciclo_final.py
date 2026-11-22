"""Ciclo final de Garbi (solución final, 20-11) con la verdad de la simulación: la sesión de los 5 intentos y las
variantes (`garbi.sesion.JuezSesion`), y casos sueltos: reglas mano + taladro, descanso, agujero ≥ 2 s, madera
movida, ACT frenado por la guardia y respaldo, corte de los episodios del acercamiento."""
from __future__ import annotations

import numpy as np
import pytest

from garbi import contrato as g
from garbi.acercamiento import T_CLAVADA, DetectorClavada, HabilidadAcercamientoProgramado
from garbi.ciclo import escena_verdad
from garbi.ciclo_final import ESPERA, T_AGUJERO, T_DESCANSO, CicloFinal, EstadoFinal
from garbi.grabador import EMPEZAR, TERMINAR, CorteAcercamiento, GrabadorAcercamiento
from garbi.lateral import APARCADO, ControlLateral
from garbi.mundo import MundoGarbi
from garbi.sesion import JuezSesion, intentos_estandar
from garbi.tipos import Broca, Escena, Mano, Taladro, forzar_montaje
from sim.entorno import lerobot_a_rad

TABLA = g.PoseTabla(360.0, 0.0, 0.0)


class Banco:
    """Mundo + ciclo final; `correr(s)` avanza con la escena de la verdad y mide holgura y borde reales."""

    def __init__(self, acercamiento=None, respaldo=None):
        """`acercamiento` y `respaldo`: funciones control → habilidad (o None: las de por defecto)."""
        self.m = MundoGarbi(render=False, montaje="lateral")
        self.c = ControlLateral(self.m)
        self.m.reset(0, tabla=TABLA, q_inicial=APARCADO)
        self.ciclo = CicloFinal(self.c, acercamiento and acercamiento(self.c), respaldo and respaldo(self.c))
        self.ciclo.q = self.m.estado().astype(float)
        self.estados: list[str] = []
        self.aspirar: list[tuple[str, bool]] = []
        self.holgura_min = np.inf
        self.dq_max = 0.0

    def paso(self):
        m = self.m
        e = escena_verdad(m, m.t, self.ciclo.agujeros)
        antes = self.ciclo.q.copy()
        o = self.ciclo.paso(e, {"state": m.estado()})
        self.dq_max = max(self.dq_max, float(np.max(np.abs(o.q - antes))))
        if not self.estados or self.estados[-1] != o.estado:
            self.estados.append(o.estado)
        self.aspirar.append((o.estado, o.aspirar))
        m.aspiradora = o.aspirar
        m.step(o.q, observar=False)
        if m.juez.taladro_visible:
            q4 = lerobot_a_rad(m.estado().astype(float))[:4]
            self.holgura_min = min(self.holgura_min, self.c.holgura(q4, m.juez.taladro_punta, m.juez.taladro_eje))
        return o

    def correr(self, segundos, cada=None):
        for _ in range(round(segundos * g.FPS)):
            if cada is not None:
                cada()
            self.paso()

    def esperar(self, estado, maximo):
        for _ in range(round(maximo * g.FPS)):
            if self.ciclo.estado.value == estado:
                return True
            self.paso()
        return self.ciclo.estado.value == estado


# --- la sesión entera -----------------------------------------------------------------------------------------------
@pytest.fixture(scope="module")
def sesion():
    m = MundoGarbi(render=False, montaje="lateral")
    m.reset(0, tabla=TABLA, q_inicial=APARCADO)
    c = ControlLateral(m)
    ciclo = CicloFinal(c)
    ciclo.q = m.estado().astype(float)
    juez = JuezSesion(m, ciclo, intentos_estandar(), c)
    aspira = []
    while not juez.terminado and m.t < 400:
        juez.paso(m.t)
        e = escena_verdad(m, m.t, ciclo.agujeros)
        o = ciclo.paso(e, {"state": m.estado()})
        aspira.append((o.estado, o.aspirar))
        m.aspiradora = o.aspirar
        m.step(o.q, observar=False)
        juez.medir(e)
    return juez, ciclo, aspira


def test_cinco_intentos_y_variantes(sesion):
    juez, ciclo, _ = sesion
    res = juez.resumen()
    print("\n", res)
    assert juez.terminado
    assert res["aciertos"] == res["intentos"] == 5
    assert all(res["variantes_ok"].values()) and len(res["variantes_ok"]) == 2
    assert res["holgura_min"] >= 10.0
    assert res["holgura_mano_min"] >= 10.0
    assert res["borde_min"] >= 3.0
    assert res["falsos_agujeros"] == 0 and res["perdidos"] == 0
    assert res["sin_agarre"] == 0
    assert all(res["descansa"])
    assert not any(res["contactos"])


def test_cada_estado_y_aspiradora(sesion):
    juez, ciclo, aspira = sesion
    visitados = {e for e, _ in aspira}
    assert visitados == {e.value for e in EstadoFinal}
    for estado, a in aspira:
        assert a == (estado in ("acercamiento", "limpieza")), estado


def test_apoyo_corto_no_cuenta_y_reclavada_si(sesion):
    juez, _, _ = sesion
    r = juez.resultados
    assert len(r[1].agujeros) == 2 and r[1].agujeros_ciclo == 2  # re-clavada: dos agujeros
    assert len(r[2].agujeros) == 1 and r[2].agujeros_ciclo == 1  # apoyo de < 2 s: no es agujero
    assert "acercamiento→retirada→prudente→acercamiento" in "→".join(r[2].estados)


def test_madera_movida_limpia_en_su_sitio(sesion):
    juez, _, _ = sesion
    r = juez.resultados
    # intentos 3 y 5 mueven la madera después de taladrar: los agujeros se limpian donde están ahora
    assert r[2].intento.mover_madera and r[4].intento.mover_madera
    assert r[2].viruta_restante == [0] and r[4].viruta_restante == [0]


def test_mano_que_se_cruza_aparta_y_vuelve(sesion):
    juez, ciclo, _ = sesion
    assert ciclo.apartadas_mano >= 1
    assert juez.resultados[3].holgura_mano_min >= 10.0


# --- reglas sueltas ----------------------------------------------------------------------------------------------------
def test_mano_sola_despierta_y_descansa():
    b = Banco()
    b.m.poner_mano_libre(420.0, -100.0, g.ALTURA_CARA_TABLA)
    b.correr(1.0)
    assert b.ciclo.estado == EstadoFinal.DESPIERTO
    b.correr(3.0)
    assert b.ciclo.estado == EstadoFinal.DESPIERTO  # con manos no descansa
    b.m.quitar_mano_libre()
    b.correr(T_DESCANSO - 0.5)
    assert b.ciclo.estado == EstadoFinal.DESPIERTO  # aún no han pasado 3 s
    assert b.esperar("descanso", 1.5)
    assert "prudente" not in b.estados


def test_taladro_sin_mano_no_se_sigue():
    b = Banco()
    b.m.poner_mano_libre(420.0, -100.0, g.ALTURA_CARA_TABLA)
    b.m.poner_taladro(360.0, 20.0)  # de pie en la madera, sin mano
    b.m.soltar_taladro()
    b.correr(3.0)
    assert b.ciclo.estado == EstadoFinal.DESPIERTO
    assert "prudente" not in b.estados and "acercamiento" not in b.estados
    b.m.poner_taladro(360.0, 20.0, g.ALTURA_CARA_TABLA + 50.0)  # ahora sí, agarrado
    b.m.coger_taladro()
    b.correr(0.5)
    assert b.ciclo.estado == EstadoFinal.PRUDENTE


def _clavar(b, xy, segundos):
    b.m.poner_mano_libre(440.0, -110.0, g.ALTURA_CARA_TABLA)
    b.m.poner_taladro(xy[0], xy[1], g.ALTURA_CARA_TABLA + 50.0)
    b.correr(3.0)
    assert b.ciclo.estado == EstadoFinal.PRUDENTE
    b.m.poner_taladro(xy[0], xy[1])
    b.correr(segundos)


def test_agujero_solo_con_dos_segundos_clavada():
    b = Banco()
    _clavar(b, (350.0, 30.0), T_CLAVADA + 1.2)  # 1,5 s clavada
    assert b.ciclo.estado == EstadoFinal.ACERCAMIENTO
    assert not b.ciclo.agujeros
    b.correr(T_AGUJERO - 1.2 + 0.2)
    assert len(b.ciclo.agujeros) == 1
    assert np.linalg.norm(b.ciclo.agujero_en_mesa(0)[:2] - [350.0, 30.0]) < 1.0
    b.m.poner_taladro(350.0, 30.0, g.ALTURA_CARA_TABLA + 50.0)  # levanta: RETIRADA (lo decide la percepción)
    b.correr(0.3)
    assert b.ciclo.estado == EstadoFinal.RETIRADA
    assert b.holgura_min >= 10.0


def test_agujero_va_con_la_madera():
    b = Banco()
    b.ciclo._madera = TABLA
    b.ciclo._apuntar(np.array([350.0, 30.0]))
    b.m.mover_tabla(10.0, -5.0, 3.0)
    b.correr(0.1)
    esperado = b.m.juez.tabla.a_mesa(TABLA.a_tabla(np.array([350.0, 30.0])))
    assert np.allclose(b.ciclo.agujero_en_mesa(0)[:2], esperado, atol=1e-6)


class HabilidadKamikaze:
    """Una habilidad que se pasa: lleva la boca al eje de la broca (como un ACT que se acerca de más)."""

    nombre = "kamikaze"

    def __init__(self, control):
        self.p = HabilidadAcercamientoProgramado(control)
        self.c = control

    def reiniciar(self, punta):
        self.p.reiniciar(punta)
        self.P = np.asarray(punta, float)

    def accion(self, obs):
        from garbi.ciclo import Cinematica

        r = Cinematica(self.c).resolver(lambda inc: Cinematica(self.c).junto_a(self.P, 5.0, 22.0, inc), (15.0,))
        destino = forzar_montaje(self.c.a_lerobot(r[0]))
        q = np.asarray(obs["state"], float)
        return q + np.clip(destino - q, -2.0, 2.0)


class HabilidadSaltona:
    nombre = "saltona"

    def reiniciar(self, punta):
        self.k = 0

    def accion(self, obs):
        self.k += 1
        q = np.asarray(obs["state"], float).copy()
        q[1] += 30.0 if self.k % 2 else -30.0
        return q


def test_act_que_se_pasa_lo_frena_la_guardia_y_entra_el_respaldo():
    b = Banco(HabilidadKamikaze)
    _clavar(b, (350.0, 30.0), 5.0)
    assert b.ciclo.frenadas_habilidad >= 10
    assert b.ciclo.respaldos == 1
    assert b.ciclo.estado == EstadoFinal.ACERCAMIENTO
    assert b.ciclo._hab_acerc is b.ciclo.respaldo_acercamiento
    assert b.holgura_min >= 10.0
    assert b.dq_max <= 2.5 + 1e-6


def test_salto_de_la_habilidad_pasa_al_respaldo():
    b = Banco(lambda c: HabilidadSaltona())
    _clavar(b, (350.0, 30.0), 2.0)
    assert b.ciclo.saltos_habilidad >= 1 and b.ciclo.respaldos == 1
    assert b.dq_max <= 2.5 + 1e-6


def test_si_el_respaldo_tampoco_puede_se_retira_y_espera():
    b = Banco(HabilidadKamikaze, HabilidadKamikaze)
    _clavar(b, (350.0, 30.0), 6.0)
    assert b.ciclo.estado in (EstadoFinal.RETIRADA, EstadoFinal.PRUDENTE)
    assert b.ciclo._bloqueo
    assert b.holgura_min >= 10.0


def test_espera_es_alta_y_lejos_de_la_madera():
    c = ControlLateral(MundoGarbi(render=False, montaje="lateral"))
    boca, _ = c.boca(lerobot_a_rad(ESPERA)[:4])
    assert boca[2] > 300.0 and np.hypot(boca[0], boca[1]) < 250.0


# --- corte de los episodios del acercamiento ----------------------------------------------------------------------
def _escena(t, apoyada=True, agarrado=True, xy=(350.0, 30.0), alto=0.0):
    punta = np.array([*xy, g.ALTURA_CARA_TABLA + alto])
    return Escena(t=t, madera=TABLA, taladro=Taladro(True, np.array(xy), agarrado=agarrado),
                  broca=Broca(punta, apoyada, "muneca"), manos=[Mano(np.array([430.0, 30.0]), True)])


def test_detector_clavada_con_histeresis():
    d = DetectorClavada()
    assert d.actualizar(_escena(0.0)) is None
    assert d.actualizar(_escena(T_CLAVADA - 0.05)) is None
    assert d.actualizar(_escena(T_CLAVADA + 0.01)) == "clavada"
    assert d.actualizar(_escena(0.5, apoyada=False)) is None  # un parpadeo no la levanta
    assert d.actualizar(_escena(0.55)) is None
    assert d.actualizar(_escena(0.6, apoyada=False, alto=20.0)) == "levantada"  # alta: al momento
    d2 = DetectorClavada()
    for k in range(20):  # sin mano no hay clavada
        assert d2.actualizar(_escena(k / 30, agarrado=False)) is None


class GrabadorFalso:
    def __init__(self):
        self.grabando, self.episodios, self._actual = False, [], None

    def empezar(self, **info):
        self.grabando, self._actual = True, {"fotogramas": 0, **info}

    def fotograma(self, imagenes, estado, accion):
        self._actual["fotogramas"] += 1
        self._actual.setdefault("estados", []).append(np.asarray(estado).copy())

    def terminar(self, guardar, **info):
        ep = {**self._actual, **info, "guardado": guardar}
        self.episodios.append(ep)
        self.grabando, self._actual = False, None
        return ep

    def escribir_json(self):
        pass

    def cerrar(self):
        return {}


def test_grabador_acercamiento_corta_solo():
    gf = GrabadorFalso()
    gr = GrabadorAcercamiento(gf, min_fotogramas=5)
    imgs = {"top": np.zeros((4, 4, 3), np.uint8), "wrist": np.zeros((4, 4, 3), np.uint8)}
    eventos = []
    t = 0.0
    for k in range(60):  # 0,5 s en el aire, 1 s clavada, levanta
        t = k / 30
        clav = 0.5 <= t < 1.5
        eventos.append(gr.paso(_escena(t, apoyada=clav, alto=0.0 if clav else 30.0), np.full(6, float(k)), imgs))
    assert eventos.count(EMPEZAR) == 1 and eventos.count(TERMINAR) == 1
    ep = gf.episodios[0]
    assert ep["guardado"] and 18 <= ep["fotogramas"] <= 24
    # state = la orden anterior (la acción del paso anterior)
    assert ep["estados"][1][0] == ep["estados"][0][0] + 1


def test_corte_no_empieza_si_ya_estaba_clavada():
    c = CorteAcercamiento()
    ev = [c.evento(k / 30, _escena(k / 30), False) for k in range(20)]
    assert EMPEZAR not in ev


def test_detector_usa_la_clavada_de_la_percepcion():
    """Con la percepción final (`Broca.clavada_desde`, `evento`) manda ella: sin esperar T_CLAVADA ni T_LEVANTADA."""
    d = DetectorClavada()
    e = _escena(1.0, apoyada=True)
    e.broca.clavada_desde, e.broca.evento = 0.8, "clavada"
    assert d.actualizar(e) == "clavada"
    assert d.ancla_desde == pytest.approx(0.8)
    e2 = _escena(1.1, apoyada=True)
    e2.broca.clavada_desde = 0.8
    assert d.actualizar(e2) is None
    e3 = _escena(1.2, apoyada=False)
    e3.broca.levantada_en, e3.broca.evento = 1.2, "levantada"
    assert d.actualizar(e3) == "levantada"


# --- con la percepción por imágenes (lento: ~5 min) ------------------------------------------------------------------
@pytest.mark.lento
def test_dos_intentos_con_la_percepcion():
    """Normal y re-clavada con la percepción final (imágenes renderizadas, manos por color, agarre y clavada de la
    percepción): las 3 clavadas se ven, agujeros limpios, sin contacto y con las holguras de la especificación."""
    from garbi.correr import correr_sim_final

    intentos = intentos_estandar()[:2]
    juez, ciclo, _ = correr_sim_final(intentos, verdad=False, manos_verdad=False)
    res = juez.resumen()
    assert res["aciertos"] == 2, res
    assert res["holgura_min"] >= 10.0 and res["holgura_mano_min"] >= 10.0 and res["borde_min"] >= 3.0
    assert res["falsos_agujeros"] == 0 and res["perdidos"] == 0
    clavadas = [x for x in ciclo.transiciones if x.motivo == "broca clavada"]
    assert len(clavadas) == 3 and ciclo.sin_prudente < 30  # casi siempre en la postura que mira la broca


# --- postura prudente: la cámara de la muñeca mira la broca (F4) -----------------------------------------------------
def test_prudente_mira_la_broca_con_holgura():
    """En PRUDENTE el brazo va a la postura prudente (la cámara de la muñeca ve la punta sobre la madera desde 180 mm),
    con holgura > 30 mm con el taladro."""
    from garbi.acercamiento import postura_prudente

    b = Banco()
    b.m.poner_mano_libre(440.0, -110.0, g.ALTURA_CARA_TABLA)
    b.m.poner_taladro(350.0, 30.0, g.ALTURA_CARA_TABLA + 50.0)
    b.correr(4.0)
    assert b.ciclo.estado == EstadoFinal.PRUDENTE
    q = postura_prudente(b.c, np.array([350.0, 30.0, 0.0]))
    assert np.max(np.abs(b.ciclo.q[:4] - q[:4])) < 1.5
    q4 = lerobot_a_rad(b.m.estado().astype(float))[:4]
    assert b.c.ve(q4, np.array([350.0, 30.0, g.ALTURA_CARA_TABLA]))
    assert b.c.holgura(q4, np.array([350.0, 30.0, g.ALTURA_CARA_TABLA])) > 30.0
    assert b.holgura_min >= 15.0 and b.ciclo.sin_prudente == 0


def test_prudente_con_otro_pixel_si_estorba_la_mano():
    """Con la mano libre apoyada donde caería el brazo, la postura prudente mira la punta desde otro píxel y deja
    holgura con la mano."""
    from garbi.ciclo import _lr_a_q4

    b = Banco()
    b.m.poner_mano_libre(418.0, -132.0, g.ALTURA_CARA_TABLA)
    b.m.poner_taladro(387.0, 16.0, g.ALTURA_CARA_TABLA + 50.0)
    b.correr(4.0)
    assert b.ciclo.estado == EstadoFinal.PRUDENTE and b.ciclo._prudente_uv != 0
    assert b.ciclo.holgura_manos(_lr_a_q4(b.ciclo.q)) >= 25.0 and b.ciclo.sin_prudente == 0
    q4 = lerobot_a_rad(b.m.estado().astype(float))[:4]
    assert b.c.ve(q4, np.array([387.0, 16.0, g.ALTURA_CARA_TABLA]))


def test_acercamiento_desde_la_prudente_pasa_por_la_entrada():
    """Desde la postura prudente la boca está a un lado de la broca: el programado va antes a la de entrada (boca a
    100 mm mirándola) y después baja y entra, con holgura ≥ 10 mm."""
    b = Banco()
    _clavar(b, (350.0, 30.0), 0.1)
    fases = set()
    for _ in range(round(5.0 * g.FPS)):
        b.paso()
        if b.ciclo._hab_acerc is not None:
            fases.add(b.ciclo._hab_acerc.fase)
    assert b.ciclo.estado == EstadoFinal.ACERCAMIENTO
    assert {"entrada", "bajar", "aspirar"} <= fases
    assert b.ciclo._hab_acerc.en_posicion
    assert b.holgura_min >= 10.0


def _apoyo(k, agarrado):
    return _escena(k / 30, apoyada=k >= 5, agarrado=agarrado, alto=0.0 if k >= 5 else 30.0)


def test_corte_avisa_por_que_no_corta_y_sin_agarre_si():
    c = CorteAcercamiento()
    ev = [c.evento(k / 30, _apoyo(k, False), False) for k in range(20)]
    assert EMPEZAR not in ev and "mano" in c.aviso and "--sin-agarre" in c.aviso
    c2 = CorteAcercamiento(exigir_agarre=False)
    ev = [c2.evento(k / 30, _apoyo(k, False), False) for k in range(20)]
    assert EMPEZAR in ev and c2.aviso == ""


def test_grabador_descarta_si_no_parte_de_la_prudente():
    gf = GrabadorFalso()
    gr = GrabadorAcercamiento(gf, min_fotogramas=5, partida=lambda e, q: 20.0)
    imgs = {"top": np.zeros((4, 4, 3), np.uint8), "wrist": np.zeros((4, 4, 3), np.uint8)}
    for k in range(60):
        t = k / 30
        clav = 0.5 <= t < 1.5
        gr.paso(_escena(t, apoyada=clav, alto=0.0 if clav else 30.0), np.full(6, float(k)), imgs)
    ep = gf.episodios[0]
    assert not ep["guardado"] and ep["motivo"].startswith("no parte de la postura prudente")
    assert ep["dif_partida"] == 20.0
