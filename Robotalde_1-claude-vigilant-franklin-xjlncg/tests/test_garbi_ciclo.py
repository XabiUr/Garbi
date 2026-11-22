"""Ciclo de Garbi (M4) con la verdad de la simulación como `Escena`: 5 ciclos seguidos y la pasada final, y casos
sueltos (broca en el aire, taladro que se mueve en el preapunto, guardia de velocidad)."""
from __future__ import annotations

import numpy as np
import pytest

from garbi import contrato as g
from garbi.ciclo import MAX_GRADOS_PASO, Ciclo, escena_verdad
from garbi.habilidad import HabilidadEspiral
from garbi.lateral import APARCADO, ControlLateral
from garbi.mundo import MundoGarbi
from garbi.tipos import forzar_montaje
from sim.entorno import lerobot_a_rad

TABLA = g.PoseTabla(360.0, 0.0, 5.0)
# marco de la madera; todos con la punta en la zona de taladro (tipos.ZONA_TALADRO, 320-420 mm del eje del robot):
# fuera de ella el ciclo no acompaña ((-50, 90) quedaba a 314 mm y se cambió por (-35, 90), a 329 mm)
SITIOS = [(-20.0, 40.0), (-40.0, -30.0), (0.0, -80.0), (20.0, 10.0), (-35.0, 90.0)]
AIRE = 50.0  # mm de la punta sobre la madera mientras se mueve
T_TALADRAR = 6.0


class Banco:
    """Mundo + ciclo + persona con guion. Mide la holgura real (postura del robot simulado) en cada paso."""

    def __init__(self, habilidad=None, respaldo=None):
        self.m = MundoGarbi(render=False, montaje="lateral")
        self.c = ControlLateral(self.m)
        self.m.reset(0, tabla=TABLA, q_inicial=APARCADO)
        self.ciclo = Ciclo(self.c, habilidad or HabilidadEspiral(self.c), respaldo=respaldo)
        self.holgura_min = np.inf
        self.borde_min = np.inf
        self.dq_max = 0.0
        self.ordenes = []
        self.estados = []
        self.aspirar = []

    def paso(self):
        m = self.m
        escena = escena_verdad(m, m.t, self.ciclo.agujeros)
        anterior = self.ciclo.q.copy()
        orden = self.ciclo.paso(escena, {"state": m.estado()})
        self.dq_max = max(self.dq_max, float(np.max(np.abs(orden.q - anterior))))
        self.ordenes.append(orden.q.copy())
        self.estados.append(orden.estado)
        self.aspirar.append(orden.aspirar)
        m.aspiradora = orden.aspirar
        m.step(orden.q, observar=False)
        q4 = lerobot_a_rad(m.estado().astype(float))[:4]
        if m.juez.taladro_visible:
            self.holgura_min = min(self.holgura_min, self.c.holgura(q4, m.juez.taladro_punta))
        self.borde_min = min(self.borde_min, self.ciclo.borde(q4))
        return orden

    def quieto(self, segundos):
        for _ in range(round(segundos * g.FPS)):
            self.paso()

    def mover(self, desde, hasta, segundos, alto_desde, alto_hasta):
        n = max(1, round(segundos * g.FPS))
        for k in range(1, n + 1):
            f = 0.5 - 0.5 * np.cos(np.pi * k / n)
            xy = np.asarray(desde) + (np.asarray(hasta) - np.asarray(desde)) * f
            self.m.poner_taladro(xy[0], xy[1], g.ALTURA_CARA_TABLA + alto_desde + (alto_hasta - alto_desde) * f)
            self.paso()

    def esperar_estado(self, estado, maximo):
        for _ in range(int(maximo * g.FPS)):
            if self.ciclo.estado.value == estado:
                return True
            self.paso()
        return self.ciclo.estado.value == estado

    def un_agujero(self, sitio):
        """Entrar, buscar, apoyar, taladrar ~6 s, levantar y salir; devuelve la duración del ciclo (hasta aparcar)."""
        t0 = self.m.t
        a = TABLA.a_mesa(np.array(sitio))
        entrada = np.array([g.PERSONA_X + 60, a[1]])
        self.m.poner_taladro(entrada[0], entrada[1], g.ALTURA_CARA_TABLA + AIRE + 60)
        self.mover(entrada, a + [40, 30], 2.5, AIRE + 60, AIRE)  # entra
        self.mover(a + [40, 30], a + [-20, -30], 2.0, AIRE, AIRE)  # busca
        self.mover(a + [-20, -30], a, 1.5, AIRE, AIRE)
        self.mover(a, a, 0.6, AIRE, 0.0)  # apoya
        self.quieto(1.0)
        self.m.taladrar()
        self.quieto(T_TALADRAR)  # taladra
        self.mover(a, a, 0.5, 0.0, AIRE)  # levanta
        self.mover(a, entrada, 1.8, AIRE, AIRE + 60)  # sale
        self.m.quitar_taladro()
        assert self.esperar_estado("aparcado", 40), f"no aparca: {self.ciclo.estado} {self.ciclo.detalle}"
        return self.m.t - t0


@pytest.fixture(scope="module")
def sesion():
    """5 ciclos seguidos en 5 sitios de la madera y la pasada final."""
    b = Banco()
    duraciones = [b.un_agujero(s) for s in SITIOS]
    b.ciclo.pasada_final()
    t0 = b.m.t
    b.paso()
    assert b.esperar_estado("aparcado", 90)
    return b, duraciones, b.m.t - t0


def test_cinco_ciclos_sin_contacto(sesion):
    b, duraciones, t_pasada = sesion
    print(f"\nholgura mínima {b.holgura_min:.1f} mm · borde mínimo {b.borde_min:.1f} mm · "
          f"duraciones {[round(d, 1) for d in duraciones]} s · pasada final {t_pasada:.1f} s · "
          f"frenadas {b.ciclo.frenadas} · fuera de especificación {len(b.ciclo.fuera_de_especificacion)}")
    assert b.holgura_min >= 10.0
    assert b.borde_min >= 3.0 - 0.5  # la postura real va un poco por detrás de la orden


def test_todos_los_agujeros_limpios(sesion):
    b, _, _ = sesion
    assert len(b.ciclo.agujeros) == len(SITIOS)
    assert b.ciclo.limpios == set(range(len(SITIOS))) and not b.ciclo.fallidos
    restos = [b.m.viruta_alrededor(h, 35.0) for h in b.m.juez.agujeros]
    print(f"\nviruta restante por agujero {restos} (de {g.VIRUTA_POR_AGUJERO})")
    assert max(restos) <= 2
    for h_ciclo, h_mundo in zip(b.ciclo.agujeros, b.m.juez.agujeros):
        assert np.linalg.norm(h_ciclo - h_mundo) < 3.0  # memoria de agujeros en el marco de la madera


def test_cada_transicion_ocurre(sesion):
    b, _, _ = sesion
    pares = {(tr.de, tr.a) for tr in b.ciclo.transiciones}
    for par in [("aparcado", "seguir"), ("seguir", "preapunto"), ("preapunto", "acompanar"), ("acompanar", "seguir"),
                ("seguir", "ir_a_limpiar"), ("ir_a_limpiar", "limpiar"), ("limpiar", "revisar"),
                ("revisar", "aparcar"), ("aparcar", "aparcado"), ("aparcado", "pasada_final"),
                ("pasada_final", "aparcar")]:
        assert par in pares, par
    assert len([p for p in b.ciclo.transiciones if p.a == "limpiar"]) >= len(SITIOS)


def test_duracion_por_ciclo(sesion):
    _, duraciones, t_pasada = sesion
    assert all(20.0 <= d <= 36.0 for d in duraciones), duraciones
    assert sum(duraciones) + t_pasada <= 200.0  # 5 seguidos y la pasada final: ~3 min


def test_senal_aspirar_y_montaje(sesion):
    b, _, _ = sesion
    for e, a in zip(b.estados, b.aspirar):
        assert a == (e in ("acompanar", "limpiar", "pasada_final"))
    q = np.array(b.ordenes)
    assert np.all(q[:, 4] == 0.0) and np.all(q[:, 5] == 0.0)
    assert b.dq_max <= MAX_GRADOS_PASO + 1e-9


def test_broca_en_el_aire_no_acompana():
    b = Banco()
    a = TABLA.a_mesa(np.array(SITIOS[0]))
    entrada = np.array([g.PERSONA_X + 60, a[1]])
    b.m.poner_taladro(entrada[0], entrada[1], g.ALTURA_CARA_TABLA + AIRE)
    b.mover(entrada, a, 2.5, AIRE, AIRE)
    b.quieto(4.0)  # quieta en el aire
    assert "preapunto" in b.estados
    assert "acompanar" not in b.estados and not any(b.aspirar)
    assert not b.ciclo.agujeros
    assert b.holgura_min >= 10.0


def test_mover_el_taladro_en_preapunto_vuelve_a_seguir():
    b = Banco()
    a = TABLA.a_mesa(np.array(SITIOS[0]))
    entrada = np.array([g.PERSONA_X + 60, a[1]])
    b.m.poner_taladro(entrada[0], entrada[1], g.ALTURA_CARA_TABLA + AIRE)
    b.mover(entrada, a, 2.5, AIRE, AIRE)
    b.quieto(1.0)
    assert b.ciclo.estado.value == "preapunto"
    b.mover(a, a + [0, 20], 0.5, AIRE, AIRE)  # 20 mm
    assert b.ciclo.estado.value == "seguir"
    assert ("preapunto", "seguir") in {(tr.de, tr.a) for tr in b.ciclo.transiciones}
    assert b.holgura_min >= 10.0


class HabilidadLoca:
    """Pide saltos enormes: la guardia de velocidad no debe dejarlos pasar."""

    def __init__(self):
        self.llamadas = 0

    def reiniciar(self, agujero_mesa):
        pass

    def accion(self, obs):
        self.llamadas += 1
        q = np.asarray(obs["state"], float).copy()
        q[:4] += 90.0 * (-1) ** self.llamadas
        q[4], q[5] = 45.0, 80.0  # muñeca y pinza: forzar_montaje las pone a 0
        return q


def test_guardia_de_velocidad_y_respaldo():
    b = Banco()
    loca = HabilidadLoca()
    respaldo = HabilidadEspiral(b.c)
    b.ciclo.habilidad, b.ciclo.respaldo = loca, respaldo
    a = TABLA.a_mesa(np.array(SITIOS[1]))
    b.un_agujero(SITIOS[1])
    assert loca.llamadas >= 1 and b.ciclo.saltos_habilidad >= 1
    assert b.dq_max <= MAX_GRADOS_PASO + 1e-9
    q = np.array(b.ordenes)
    assert np.all(q[:, 4] == 0.0) and np.all(q[:, 5] == 0.0)
    assert b.ciclo.limpios == {0}  # el barrido programado de respaldo lo limpió
    assert b.m.viruta_alrededor(b.m.juez.agujeros[0], 35.0) <= 2
    assert np.linalg.norm(TABLA.a_mesa(b.ciclo.agujeros[0]) - a) < 3.0


def test_forzar_montaje_en_la_salida():
    assert np.all(forzar_montaje(np.array([1, 2, 3, 4, 5, 6.0]))[4:] == 0.0)


@pytest.mark.parametrize("radio", [260.0, 310.0, 435.0])
def test_fuera_de_la_zona_de_taladro_no_acompana(radio):
    """Zona de taladro (320-420 mm del eje del robot): fuera no acompaña aunque la broca se apoye; si el taladro viene
    hacia el robot (< 300 mm), Garbi se aparca y no estorba. La holgura real no baja de 10 mm."""
    b = Banco()
    a = TABLA.a_mesa(np.array(SITIOS[0]))
    entrada = np.array([g.PERSONA_X + 60, a[1]])
    b.m.poner_taladro(entrada[0], entrada[1], g.ALTURA_CARA_TABLA + AIRE)
    b.mover(entrada, a, 2.5, AIRE, AIRE)
    b.quieto(1.0)
    assert b.ciclo.estado.value == "preapunto"
    fuera = a * (radio / np.linalg.norm(a))
    n = len(b.estados)
    b.mover(a, fuera, 1.5, AIRE, AIRE)  # la persona lleva el taladro fuera de la zona
    b.mover(fuera, fuera, 0.6, AIRE, 0.0)  # y apoya la broca
    b.quieto(4.0)
    despues = b.estados[n:]
    assert "acompanar" not in despues and not any(b.aspirar[n:])
    if radio < 300.0:
        assert b.ciclo.estado.value in ("aparcar", "aparcado")
    assert b.holgura_min >= 10.0
