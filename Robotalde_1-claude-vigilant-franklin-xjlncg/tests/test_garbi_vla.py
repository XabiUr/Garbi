"""Habilidad VLA supervisada y demostraciones de limpieza de Garbi (sin entrenar: políticas de mentira)."""
from collections import deque

import numpy as np
import pytest

from garbi import contrato as g
from garbi.control import ControlBoca
from garbi.demostraciones import ejecutar_episodio
from garbi.mundo import APARCADO, MundoGarbi
from garbi.politica import MAX_GRADOS_FOTOGRAMA, HabilidadVLA
from garbi.robot_vivo import LineaBase, PercepcionOraculo


class PoliticaFija:
    """Devuelve siempre la misma acción."""
    nombre = "fija"

    def __init__(self, accion):
        self.a = np.asarray(accion, float)

    def reiniciar(self, *args):
        pass

    def accion(self, obs):
        return self.a


class PoliticaImitaLineaBase:
    """Imita al demostrador (lo que haría un VLA perfectamente entrenado): recalcula el zigzag al empezar."""
    nombre = "imita"

    def __init__(self, mundo):
        self.m = mundo
        self.lb = LineaBase(ControlBoca(mundo.cin))
        self.plan = deque()

    def reiniciar(self, tipo, anclaje, orden):
        self.lb.empezar(orden, self.m.estado(), PercepcionOraculo(self.m))

    def accion(self, obs):
        a = self.lb.accion(None, obs)
        return self.m.estado() if a is None else a


@pytest.mark.parametrize("orden", g.ORDENES_VLA)
@pytest.mark.parametrize("semilla", [0, 1, 2])
def test_demostrador_limpia(orden, semilla):
    m = MundoGarbi(render=False)
    n, ini, fin = ejecutar_episodio(m, orden, semilla)
    assert ini > 0 and fin <= 0.05 * ini and 30 < n < 600


def test_supervision_limita_velocidad_y_altura():
    m = MundoGarbi(render=False)
    m.reset(0)
    ctl = ControlBoca(m.cin)
    q0 = np.asarray(APARCADO, float)
    # Una acción lejana: se acerca como mucho MAX_GRADOS_FOTOGRAMA por articulación
    h = HabilidadVLA(None, ctl, politica=PoliticaFija(q0 + 40))
    h.empezar(g.ORDEN_AGUJERO, q0, PercepcionOraculo(m))
    a = h.accion(q0, {})
    assert np.max(np.abs(a - q0)) <= MAX_GRADOS_FOTOGRAMA + 1e-9
    # Una acción que mete la boca en la tabla: se descarta
    from garbi.control import distancia_limpieza, eje_hacia

    p = np.array([*m.juez.tabla.a_mesa(np.zeros(2)), g.ALTURA_CARA_TABLA])
    e = eje_hacia(p, 1)
    q_bajo = ctl.postura(p - e * distancia_limpieza() + [0, 0, -15], e, 1)
    q_cerca = ctl.postura(p - e * distancia_limpieza(), e, 1)
    assert ctl.borde_inferior(q_bajo) < g.ALTURA_CARA_TABLA
    h = HabilidadVLA(None, ctl, politica=PoliticaFija(q_bajo))
    h.empezar(g.ORDEN_AGUJERO, q_cerca, PercepcionOraculo(m))
    for _ in range(10):
        a = h.accion(q_cerca, {})
        assert ctl.borde_inferior(a) >= g.ALTURA_CARA_TABLA + 1.0
    assert h.descartadas > 0


def test_ciclo_completo_con_habilidad_vla():
    from garbi.escenario import ejecutar

    m = MundoGarbi(render=False)
    hab = HabilidadVLA(None, ControlBoca(m.cin), politica=PoliticaImitaLineaBase(m))
    inf = ejecutar(0, mundo=m, habilidad=hab)
    assert inf.viruta_agujero_al_final <= 2
    assert inf.viruta_alfombrilla_final <= 2
    assert any("política aprendida" in r.texto for r in inf.estados)


class PoliticaChunkImitaLineaBase(PoliticaImitaLineaBase):
    """Como `PoliticaImitaLineaBase`, pero da chunks de 50 acciones (como SmolVLA) para la ejecución asíncrona."""

    def reiniciar(self, tipo, anclaje, orden):
        super().reiniciar(tipo, anclaje, orden)
        self.todo = list(self.lb.plan)
        self.t0 = self.m.t

    def chunk(self, obs):
        """Como una política real: el chunk empieza en el instante de la observación."""
        k = int(round((self.m.t - self.t0) * g.FPS / getattr(self, "factor", 1)))
        trozo = self.todo[k:k + 50]
        while len(trozo) < 50:
            trozo.append(trozo[-1] if trozo else self.todo[-1])
        return np.array(trozo, float)


@pytest.mark.parametrize("latencia, factor", [(0.0, 1), (0.7, 1), (1.2, 2)])
def test_vla_asincrona_no_se_para(latencia, factor):
    """Asíncrona: con latencia ≤ media duración del chunk el robot solo espera al primer chunk y limpia igual.
    1,2 s es SmolVLA medido en CPU: necesita `factor_tiempo=2`."""
    from garbi.escenario import ejecutar

    m = MundoGarbi(render=False)
    pol = PoliticaChunkImitaLineaBase(m)
    pol.factor = factor
    hab = HabilidadVLA(None, ControlBoca(m.cin), politica=pol, asincrona=True, latencia_simulada=latencia,
                       factor_tiempo=factor, margen=45 * factor)
    inf = ejecutar(0, mundo=m, habilidad=hab)
    assert hab.esperas <= int(round(latencia * g.FPS)) + 1  # solo al arrancar, mientras llega el primer chunk
    assert inf.viruta_agujero_al_final <= 2 and inf.viruta_alfombrilla_final <= 2


def test_vla_asincrona_con_latencia_de_cpu_se_atasca_a_velocidad_normal():
    """El límite: 1,2 s por chunk de 50 a 30 Hz deja el robot esperando más de la mitad del tiempo."""
    from garbi.escenario import ejecutar

    m = MundoGarbi(render=False)
    hab = HabilidadVLA(None, ControlBoca(m.cin), politica=PoliticaChunkImitaLineaBase(m), asincrona=True,
                       latencia_simulada=1.2)
    ejecutar(0, mundo=m, habilidad=hab)
    assert hab.esperas > 0.4 * hab.pasos
