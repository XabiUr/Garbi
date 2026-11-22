"""Robot MuJoCo detrás de la interfaz `Robot`: replay, respaldo, cambio en caliente y Repaso en el servidor."""
import argparse
import asyncio
import json

import numpy as np
import pytest
from aiohttp.test_utils import TestClient, TestServer

from lewelder.antorcha import AntorchaRobot
from lewelder.antorcha_virtual import AntorchaRobotVirtual
from lewelder.contrato import LONGITUD_CORDON, Muestra, instruccion_soldar
from lewelder.fuentes import ConfigPasada, FuenteSimulada
from lewelder.robot import Robot
from lewelder.robot_mujoco import RobotMuJoCo
from lewelder.servidor import Escuela, crear_app, crear_robot
from test_servidor import FuenteGuion, esperar_robot, leer_hasta, soldar

INSTRUCCION = instruccion_soldar("recta", "B")


@pytest.fixture
def robot(dataset_sim):
    r = RobotMuJoCo("replay", dataset=dataset_sim[0], escala_tiempo=1000)
    yield r
    r.cerrar()


class PoliticaQueFalla:
    """Política de prueba que manda quedarse quieto y revienta al cabo de `n` pasos."""

    nombre = "act"
    necesita_imagenes = False
    terminada = False

    def __init__(self, n=40):
        self.n, self.i = n, 0

    def reiniciar(self, tipo, anclaje, instruccion):
        self.i = 0

    def accion(self, obs):
        self.i += 1
        if self.i > self.n:
            raise RuntimeError("política rota")
        return np.asarray(obs["observation.state"], dtype=float)


def test_cumple_la_interfaz(robot):
    assert isinstance(robot, Robot)
    e = robot.estado()
    assert e["tipo_robot"] == "mujoco" and e["politica"] == "replay" and e["ocupado"] is False
    assert e["punta"] is None and e["disponibles"] == {"vla": None, "act": None, "replay": None}
    json.dumps(e)
    with pytest.raises(ValueError):
        robot.cambiar_politica("pi0")


@pytest.mark.asyncio
async def test_replay_recorre_el_cordon_y_manda_imagenes(robot):
    imagenes = []
    robot.al_imagen = imagenes.append
    vistas = []

    async def al_moverse(m):
        vistas.append(m)
        await asyncio.sleep(0)

    recorrido = await robot.soldar("recta", "B", INSTRUCCION, [(40.0, 55.0)], al_moverse)
    assert vistas == recorrido and len(recorrido) > 900
    sobre = [m for m in recorrido if m.z < 6 and abs(m.y) < 3]
    xs = [m.x for m in sobre]
    assert min(xs) < 1.0 and max(xs) > LONGITUD_CORDON - 1.0  # cordón completo aunque haya huecos
    assert not any(m.gatillo for m in recorrido)
    e = robot.estado()
    assert e["politica_activa"] == "replay" and e["aviso_politica"] is None and e["progreso"] == 1.0
    assert e["instruccion"] == INSTRUCCION and not e["ocupado"]
    assert imagenes and all(i[:2] == b"\xff\xd8" for i in imagenes)  # JPEG


@pytest.mark.asyncio
async def test_respaldo_si_falta_la_politica(dataset_sim):
    r = RobotMuJoCo("vla", dataset=dataset_sim[0], escala_tiempo=1000)
    try:
        await r.soldar("recta", "D", instruccion_soldar("recta", "D"), None, lambda m: None)
        e = r.estado()
        assert e["politica"] == "vla" and e["politica_activa"] == "replay"
        assert "VLA (SmolVLA) no disponible" in e["aviso_politica"] and "ACT no disponible" in e["aviso_politica"]
        assert e["nombre_politica"] == "Reproducción grabada"
        assert e["disponibles"] == {"vla": False, "act": False, "replay": True}
    finally:
        r.cerrar()
    sin_nada = RobotMuJoCo("act", escala_tiempo=1000)
    try:
        with pytest.raises(RuntimeError, match="ninguna política"):
            await sin_nada.soldar("recta", "B", INSTRUCCION, None, lambda m: None)
        assert not sin_nada.ocupado
    finally:
        sin_nada.cerrar()


@pytest.mark.asyncio
async def test_si_la_politica_falla_a_mitad_cae_al_replay(dataset_sim):
    r = RobotMuJoCo("act", dataset=dataset_sim[0], escala_tiempo=1000, politicas={"act": PoliticaQueFalla(40)})
    try:
        recorrido = await r.soldar("recta", "B", INSTRUCCION, None, lambda m: None)
        e = r.estado()
        assert e["politica_activa"] == "replay" and e["disponibles"]["act"] is False
        assert "ha fallado" in r._fallos["act"]
        xs = [m.x for m in recorrido if m.z < 6 and abs(m.y) < 3]
        assert xs and max(xs) > LONGITUD_CORDON - 1.0  # el replay termina el cordón
    finally:
        r.cerrar()


@pytest.mark.asyncio
async def test_cambio_de_politica_en_caliente_y_parar(dataset_sim):
    r = RobotMuJoCo("replay", dataset=dataset_sim[0], escala_tiempo=1000, politicas={"act": PoliticaQueFalla(10**6)})
    activas = []

    def al_moverse(m):
        activas.append(r.politica_activa)
        if len(activas) == 300:
            r.cambiar_politica("act")
        if len(activas) == 400:
            r.parar()

    try:
        recorrido = await r.soldar("recta", "D", instruccion_soldar("recta", "D"), None, al_moverse)
        assert activas[0] == "replay" and activas[-1] == "act"
        assert r.cambios_politica and r.cambios_politica[0][1] == "act"
        assert len(recorrido) == 400 and not r.ocupado  # parar() corta el recorrido
        with pytest.raises(RuntimeError):  # no se suelda dos veces a la vez
            r.ocupado = True
            await r.soldar("recta", "D", "x", None, lambda m: None)
    finally:
        r.ocupado = False
        r.cerrar()


def test_cli_crea_el_robot_mujoco(dataset_sim, tmp_path):
    args = argparse.Namespace(robot="mujoco", politica="act", escala_robot=3.0, checkpoint_act=None,
                              checkpoint_vla=None, dataset=str(dataset_sim[0]), dispositivo="cpu")
    r = crear_robot(args)
    assert isinstance(r, RobotMuJoCo) and r.politica == "act" and r.escala_tiempo == 3.0
    assert r.rutas["replay"] == str(dataset_sim[0])
    r.cerrar()
    args.dataset = str(tmp_path / "no_existe")
    r = crear_robot(args)
    assert r.rutas["replay"] is None
    r.cerrar()


# --- servidor -------------------------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_repaso_con_robot_mujoco_led_solo_en_el_hueco(dataset_sim, tmp_path):
    robot = RobotMuJoCo("vla", dataset=dataset_sim[0], escala_tiempo=1000)
    escuela = Escuela(FuenteGuion("recta", "B"), robot, None, dir_pasadas=tmp_path)
    cola = escuela.suscribir()
    try:
        await escuela.orden({"orden": "empezar_examen"})
        soldar(escuela, huecos=[(40, 55)])
        assert escuela.resultado.huecos == [(40.0, 55.0)]
        assert await escuela.orden({"orden": "repaso"}) is None
        await esperar_robot(escuela)
    finally:
        await escuela.cerrar()
    con_led = [m.x for m, led in escuela.robot_muestras if led]
    sin_led = [m for m, led in escuela.robot_muestras if not led]
    assert con_led and min(con_led) >= 40.0 and max(con_led) < 55.0
    assert not any(41.0 < m.x < 54.0 and m.z < 5 and abs(m.y) < 3 for m in sin_led)
    assert escuela.repasados[8:11] == [True] * 3 and sum(escuela.repasados) == 3
    assert escuela.cobertura_final() == 100.0 and not escuela.led_robot
    mensajes = []
    while not cola.empty():
        mensajes.append(json.loads(cola.get_nowait()))
    robot_msgs = [m for m in mensajes if m["tipo"] == "robot"]
    assert robot_msgs and robot_msgs[-1]["politica"] == "vla" and robot_msgs[-1]["politica_activa"] == "replay"
    assert "no disponible" in robot_msgs[-1]["aviso_politica"]
    assert any(m["tipo"] == "robot_imagen" and m["jpeg"] for m in mensajes)
    fin = [m for m in mensajes if m["tipo"] == "robot_fin"]
    assert fin and fin[0]["cobertura_final"] == 100.0


@pytest.mark.asyncio
async def test_punta_a_punta_websocket_con_robot_mujoco(dataset_sim, tmp_path):
    """Fuente simulada con un hueco → examen → Repaso con el robot MuJoCo (replay) → el LED de la antorcha virtual
    se enciende solo en el hueco y la tablet recibe imágenes de la simulación."""
    robot = RobotMuJoCo("replay", dataset=dataset_sim[0], escala_tiempo=30)
    cambios = []
    virtual = AntorchaRobotVirtual(al_cambiar=lambda e: cambios.append((e, robot.punta.x)))
    fuente = FuenteSimulada("recta", "B", config=ConfigPasada(velocidad=10.0, huecos=[(70.0, 85.0)]), fps=15,
                            tiempo_real=False, ancho=640, alto=360)
    escuela = Escuela(fuente, robot, AntorchaRobot(virtual.ruta), dir_pasadas=tmp_path)
    cliente = TestClient(TestServer(crear_app(escuela)))
    await cliente.start_server()
    try:
        ws = await cliente.ws_connect("/ws")
        await leer_hasta(ws, lambda m: m["tipo"] == "historial")
        await ws.send_json({"orden": "empezar_examen"})
        r = await leer_hasta(ws, lambda m: m["tipo"] == "resultado")
        assert r["resultado"]["huecos"] == [[70.0, 85.0]]
        await ws.send_json({"orden": "repaso"})
        vistos = []
        fin = await leer_hasta(ws, lambda m: m["tipo"] == "robot_fin", timeout=120, vistos=vistos)
        con_led = [m["punta"]["x"] for m in vistos if m["tipo"] == "robot" and m["led"]]
        assert con_led and 69.0 <= min(con_led) and max(con_led) <= 86.0
        assert sum(fin["repasados"]) == 3 and fin["cobertura_final"] == 100.0
        imagenes = [m for m in vistos if m["tipo"] == "robot_imagen"]
        assert len(imagenes) >= 3 and imagenes[0]["ancho"] == 320
        await asyncio.sleep(0.1)
        assert [e for _, e in virtual.registro] == [True, False]
        assert cambios[0][1] == pytest.approx(70.0, abs=2.0) and cambios[1][1] == pytest.approx(85.0, abs=2.0)
        await ws.close()
    finally:
        await cliente.close()
        virtual.parar()
