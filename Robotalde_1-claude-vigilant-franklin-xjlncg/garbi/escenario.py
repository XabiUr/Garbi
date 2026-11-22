"""Escenario de la demo en simulación: el «juez» simulado y Garbi, de principio a fin.

Guion (tiempos en s): el juez acerca el taladro y lo mueve un poco buscando el punto; lo deja quieto; Garbi se
acerca y se queda junto a la broca con la aspiradora encendida; el juez taladra; retira el taladro y mueve la tabla;
Garbi limpia el agujero nuevo y aparca. Después, el juez tira serrín en la alfombrilla y pide que lo limpie.

`ejecutar` devuelve un informe con lo que pasó (y, si se pide, los fotogramas de la cámara fija para hacer vídeo).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from garbi import contrato as g
from garbi.contrato import punto_serrin_tapete
from garbi.mundo import MundoGarbi
from garbi.robot_vivo import Estado, LineaBase, PercepcionOraculo, RobotVivo


@dataclass
class Fotograma:
    t: float
    cenital: np.ndarray
    muneca: np.ndarray
    estado: str
    aspiradora: bool
    recogidas: int
    ultimo_evento: str


@dataclass
class Informe:
    viruta_agujero_tras_taladrar: int = 0
    viruta_agujero_al_final: int = 0
    viruta_alfombrilla_inicial: int = 0
    viruta_alfombrilla_final: int = 0
    distancia_boca_broca: float = float("nan")  # en planta, del centro de la boca a la punta (34,6 mm a 30°)
    error_apunto: float = float("nan")  # mm entre la punta medida y la real
    error_colocacion: float = float("nan")  # mm entre la boca y su sitio ideal junto a la broca (real) al acompañar
    error_camara_arriba: float = float("nan")  # mm entre la punta que da la bola naranja y la real
    estados: list = field(default_factory=list)
    duracion: float = 0.0
    fotogramas: list = field(default_factory=list)  # list[Fotograma]


def ejecutar(semilla: int = 0, render: bool = False, grabar: bool = False, percepcion=None, habilidad=None,
             mundo: MundoGarbi | None = None, cada: int = 2, inclinacion: float = 0.0,
             mover_al_llegar: tuple[float, float] | None = None, al_paso=None) -> Informe:
    """Corre la demo. `inclinacion`: grados que el juez inclina el taladro (con rumbo al azar). `mover_al_llegar`:
    cuando Garbi ya acompaña, el juez desliza la punta del taladro (dx, dy) mm en 0,6 s, como quien recoloca antes de
    taladrar, y Garbi tiene que volver a colocarse junto al sitio nuevo. `al_paso(robot, mundo)` se llama en cada
    fotograma (para verlo en directo en el visor)."""
    m = mundo or MundoGarbi(render=render)
    m.reset(semilla=semilla)
    rng = np.random.default_rng(semilla + 100)
    per = percepcion(m) if callable(percepcion) else (percepcion or PercepcionOraculo(m))
    robot = RobotVivo(m, per, habilidad or LineaBase(None))
    if isinstance(robot.habilidad, LineaBase) and robot.habilidad.ctl is None:
        robot.habilidad.ctl = robot.ctl
    inf = Informe()

    def correr(segundos: float, cond=None):
        for _ in range(int(segundos * g.FPS)):
            robot.tick()
            if al_paso is not None:
                al_paso(robot, m)
            if grabar and int(round(m.t * g.FPS)) % cada == 0:
                inf.fotogramas.append(Fotograma(
                    m.t, m.imagen("top", g.RESOLUCION_VISION), m.imagen("wrist", g.RESOLUCION_POLITICA),
                    robot.estado.value, m.aspiradora, m.recogidas, robot.registro[-1].texto if robot.registro else ""))
            if cond is not None and cond():
                return True
        return False

    tabla = m.juez.tabla
    # Punto de taladrado elegido por el juez dentro de la parte alcanzable de la tabla
    for _ in range(50):
        p_tabla = rng.uniform([-40, -25], [40, 25])
        p_mesa = tabla.a_mesa(p_tabla)
        if g.RADIO_TRABAJO_MIN + 15 <= np.linalg.norm(p_mesa) <= g.RADIO_TRABAJO_MAX - 25:
            break
    # 1. El juez acerca el taladro y lo mueve buscando el punto
    rumbo = float(rng.uniform(0, 360))
    for k in range(4):
        q = p_mesa + rng.normal(0, 12, 2) * (3 - k) / 3
        m.poner_taladro(q[0], q[1], inclinacion=inclinacion, rumbo=rumbo)
        correr(0.3)
    m.poner_taladro(p_mesa[0], p_mesa[1], inclinacion=inclinacion, rumbo=rumbo)
    # 2. Garbi se acerca y se coloca
    correr(8.0, cond=lambda: robot.estado == Estado.ACOMPANAR)
    if mover_al_llegar is not None:
        correr(1.0)
        inicio = p_mesa.copy()
        for f in (1.0, -1.0, 0.5, -0.5):  # si se saldría de la tabla: hacia el otro lado, o la mitad
            fin = p_mesa + f * np.asarray(mover_al_llegar, float)
            if tabla.contiene(fin, margen=12):
                break
        for k in range(1, 19):
            q = inicio + (fin - inicio) * k / 18
            m.poner_taladro(q[0], q[1], inclinacion=inclinacion, rumbo=rumbo)
            correr(1 / g.FPS)
        p_mesa = fin
        correr(1.5)  # deja de estar en «acompañar» (se aparta o se recoloca)
        correr(12.0, cond=lambda: robot.estado == Estado.ACOMPANAR)
    inf.distancia_boca_broca = float(np.linalg.norm(m.boca_en_mesa()[:2] - p_mesa))
    from garbi.control import eje_hacia

    punta = np.array([p_mesa[0], p_mesa[1], g.ALTURA_CARA_TABLA])
    ideal = punta - eje_hacia(punta, robot.lado) * g.DISTANCIA_ACOMPANAR
    inf.error_colocacion = float(np.linalg.norm(m.boca_en_mesa() - ideal))
    if robot.punta_medida is not None:
        inf.error_apunto = float(np.linalg.norm(robot.punta_medida[:2] - p_mesa))
    if robot._objetivo is not None:
        inf.error_camara_arriba = float(np.linalg.norm(robot._objetivo[:2] - p_mesa))
    # 3. El juez taladra (ráfaga de 3 s) con Garbi quieto y la aspiradora encendida
    correr(1.0)
    agujero = m.taladrar()
    correr(3.0)
    inf.viruta_agujero_tras_taladrar = m.viruta_alrededor(agujero)
    # 4. Retira el taladro y mueve la tabla
    m.quitar_taladro()
    correr(0.5)
    m.mover_tabla(*rng.uniform([-15, -15, -10], [15, 15, 10]))
    # 5. Garbi limpia el agujero nuevo y aparca
    correr(20.0, cond=lambda: robot.estado == Estado.APARCADO)
    inf.viruta_agujero_al_final = m.viruta_alrededor(agujero)
    # 6. El juez tira serrín en la alfombrilla y pide que lo limpie
    tabla = m.juez.tabla
    for _ in range(50):
        p = punto_serrin_tapete(rng)
        if (not tabla.contiene(p, margen=-15)) and np.linalg.norm(p) <= g.RADIO_LIMPIAR_TAPETE - 20:
            break
    m.tirar_serrin(p[0], p[1], n=25)
    inf.viruta_alfombrilla_inicial = len(m.viruta_en_mesa(2))
    robot.ordenar(g.ORDEN_ALFOMBRILLA)
    correr(20.0, cond=lambda: robot.estado == Estado.APARCADO and m.t > 0 and not robot.ordenes)
    correr(0.2)
    correr(20.0, cond=lambda: robot.estado == Estado.APARCADO)
    inf.viruta_alfombrilla_final = len(m.viruta_en_mesa(2))
    inf.estados = robot.registro
    inf.duracion = m.t
    return inf
