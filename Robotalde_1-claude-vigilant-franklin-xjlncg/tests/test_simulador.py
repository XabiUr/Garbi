"""Simulador de la demo: física de la mesa, guion del robot, la clase v2 por /ws2 y el juez con el ratón."""
import asyncio
import json

import numpy as np
import pytest
from aiohttp.test_utils import TestClient, TestServer

from lewelder import contrato as c
from lewelder import juntas
from lewelder.antorcha import angulos_antorcha, cuaternion_desde_angulos
from lewelder.guion_robot import Planificador, postura_en
from lewelder.mesa_sim import MesaSim, angulo_entre, pose_montada
from lewelder.puntuacion import Ranking
from lewelder.simulador import AntorchaJuezRaton, ClaseSim, crear_app, poses_para_juntas, reconocer


@pytest.fixture(scope="module")
def mesa():
    return MesaSim(tiempo_real=False)


@pytest.fixture(scope="module")
def alcance():
    from lewelder.alcance import Alcance

    return Alcance()


def correr_plan(mesa, plan, hz=120):
    q0 = mesa.q()
    for k in range(int((plan.duracion() + 0.6) * hz)):
        q, tramo, _ = postura_en(plan, q0, k / hz)
        mesa.mandar(q)
        mesa.poner_led(bool(tramo and tramo.led))
        mesa.avanzar(int(mesa.hz_fisica / hz))


# --- física y guion ---------------------------------------------------------------------------------------------
def test_mesa_integra_en_tiempo_real():
    m = MesaSim()
    m.iniciar()
    try:
        import time

        time.sleep(1.6)
        assert m.hz_medida > 300  # 480 Hz nominales
    finally:
        m.parar()


def test_imanes_cierran_la_junta(mesa):
    mesa.reiniciar()
    mesa.montar_a_mano("esquina")
    j = reconocer(mesa)
    assert j.tipo == juntas.EstadoJunta.ESQUINA and j.posicion == "PB"
    mesa.montar_a_mano("t")
    assert reconocer(mesa).tipo == juntas.EstadoJunta.T
    # la base se mueve con la chapa montada
    mesa.mover_base(260.0, 30.0, 20.0)
    assert reconocer(mesa).tipo == juntas.EstadoJunta.T
    mesa.reiniciar()
    assert reconocer(mesa).tipo == juntas.EstadoJunta.INCOMPLETA  # tumbada en la zona libre


@pytest.mark.parametrize("junta", ["t", "esquina"])
def test_el_guion_monta_y_suelda(mesa, alcance, junta):
    mesa.reiniciar()
    pl = Planificador(mesa, alcance)
    correr_plan(mesa, pl.planificar(c.orden_montar(junta), mesa.q()))
    assert mesa.chapa.estado == "montada" and mesa.chapa.junta == junta
    assert angulo_entre(mesa.chapa.pose.R, pose_montada(junta, mesa.base).R) < 1.0
    assert reconocer(mesa).tipo.value == junta
    correr_plan(mesa, pl.planificar("coge la antorcha y suelda la junta", mesa.q()))
    assert mesa.antorcha.estado == "soporte"  # la devuelve a su sitio


# --- antorcha del juez -----------------------------------------------------------------------------------------
def test_angulos_del_raton_por_la_fusion(mesa):
    mesa.reiniciar()
    mesa.montar_a_mano("t")
    j = reconocer(mesa)
    a = AntorchaJuezRaton()
    p = j.cordon.aplicar([30.0, 0.0, 0.5])
    m = a.procesar(p, True, 50.0, 12.0, j)
    assert m is not None and m.gatillo
    assert abs(m.x - 30.0) < 1e-6 and abs(m.z - 0.5) < 1e-6
    assert abs(m.angulo_trabajo - 50.0) < 0.5 and abs(m.angulo_avance - 12.0) < 0.5
    q = cuaternion_desde_angulos(50.0, 12.0)
    assert abs(angulos_antorcha(q, cuaternion_desde_angulos(90.0, 0.0))[0] - 50.0) < 0.5
    # sin gatillo el LED no luce: la cámara no ve la punta (solo una muestra de "gatillo soltado")
    assert not a.procesar(p, False, 50.0, 12.0, j).gatillo
    assert a.procesar(p, False, 50.0, 12.0, j) is None


def test_poses_para_juntas_coinciden_con_el_contrato(mesa):
    mesa.reiniciar()
    mesa.montar_a_mano("esquina")
    base, movil = poses_para_juntas(mesa)
    esperada = juntas.pose_movil_montada("esquina", base)
    d, ang = movil.diferencia(esperada)
    assert d < 1e-6 and ang < 1e-4


# --- servidor -------------------------------------------------------------------------------------------------------
class EjecutorRapido:
    """Ejecutor de prueba: hace lo que haría el robot sin mover el brazo (monta a mano, suelda en recto)."""

    activo, aviso = "prueba", None

    def __init__(self, mesa):
        self.mesa, self.ordenes = mesa, []

    def parar(self):
        pass

    async def ejecutar(self, orden, avisar=None):
        self.ordenes.append(orden)
        if orden in (c.orden_montar("t"), c.orden_montar("esquina")):
            for k in range(5):
                avisar("girando", k / 5)
                await asyncio.sleep(0.01)
            self.mesa.montar_a_mano("t" if "en T" in orden else "esquina")
        elif orden == "coge la antorcha y suelda la junta":
            from lewelder.mesa_sim import Pose, Pieza

            j = reconocer(self.mesa)
            R = j.cordon.R @ np.diag([1.0, -1.0, -1.0])
            for x in np.linspace(0, c.LONGITUD_CORDON, 60):
                self.mesa.antorcha = Pieza("antorcha", Pose(j.cordon.aplicar([x, 0.0, 1.0]), R), "agarrada")
                self.mesa.t += 0.4
                self.mesa.poner_led(True)
                avisar("soldando", x / c.LONGITUD_CORDON)
            self.mesa.poner_led(False)
        await asyncio.sleep(0.01)
        return True


@pytest.fixture
def clase(mesa, alcance):
    mesa.reiniciar()
    return ClaseSim(mesa, EjecutorRapido(mesa), alcance, ranking=Ranking(None), t_cuenta_atras=0.05)


async def recibir_hasta(ws, condicion, tiempo=10.0):
    vistos = []
    async def bucle():
        while True:
            m = json.loads((await ws.receive()).data)
            for x in m if isinstance(m, list) else [m]:
                vistos.append(x)
                if condicion(x):
                    return x
    return await asyncio.wait_for(bucle(), tiempo), vistos


@pytest.mark.asyncio
async def test_paginas_y_websockets_responden(clase):
    app = crear_app(clase, iniciar=False)
    async with TestClient(TestServer(app)) as cli:
        for ruta in ("/", "/sim"):
            r = await cli.get(ruta)
            assert r.status == 200 and "sim.js" in await r.text()
        r = await cli.get("/tablet", allow_redirects=False)
        assert r.status == 302 and r.headers["Location"].startswith("/v2/")
        r = await cli.get("/tablet")
        assert r.status == 200 and "LeWelder" in await r.text()
        indice = await (await cli.get("/api/mallas")).json()
        assert len(indice["robot"]) > 10 and set(indice["piezas"]) >= {"base", "movil", "soporte"}
        assert len(await (await cli.get("/api/mallas.bin")).read()) > 100_000
        ws = await cli.ws_connect("/ws_sim")
        escena, _ = await recibir_hasta(ws, lambda m: m["tipo"] == "escena")
        assert set(escena["camaras"]) == {"a", "b"}
        mundo, _ = await recibir_hasta(ws, lambda m: m["tipo"] == "mundo")
        assert len(mundo["q"]) == 6 and len(mundo["cuerpos"]) == len(indice["cuerpos"])
        ws2 = await cli.ws_connect("/ws2")
        pantalla, _ = await recibir_hasta(ws2, lambda m: m["tipo"] == "pantalla")
        assert pantalla["nombre"] == "atraccion"
        r = await cli.post("/api/voz", json={"texto": "móntame una T"})
        assert (await r.json())["orden"] == "monta una unión en T"


@pytest.mark.asyncio
async def test_orden_monta_t_llega_al_robot_y_la_ronda_puntua(clase):
    app = crear_app(clase, iniciar=False)
    async with TestClient(TestServer(app)) as cli:
        ws2 = await cli.ws_connect("/ws2")
        await ws2.send_json({"orden": "jugar"})
        await recibir_hasta(ws2, lambda m: m.get("nombre") == "pedir")
        await ws2.send_json({"orden": "confirmar", "si": True, "orden_confirmada": "monta una unión en T"})
        junta, _ = await recibir_hasta(ws2, lambda m: m["tipo"] == "junta", 20)
        assert junta["junta"] == "t" and junta["ficha"]["titulo"] == "Unión en T"
        assert clase.ejecutor.ordenes[0] == "monta una unión en T"
        _, vistos = await recibir_hasta(ws2, lambda m: m.get("nombre") == "ronda", 30)
        assert any(m["tipo"] == "fantasma" and len(m["tramos"]) == c.N_TRAMOS for m in vistos)
        assert clase.ejecutor.ordenes == ["monta una unión en T", "señala el cordón",
                                          "coge la antorcha y suelda la junta"]
        # el juez suelda con el ratón por la vista 3D
        vista = await cli.ws_connect("/ws_sim")
        j = clase.junta
        for x in np.arange(-2.0, c.LONGITUD_CORDON + 2, 0.5):
            p = j.cordon.aplicar([x, 0.3, 0.5])
            await vista.send_json({"orden": "antorcha_juez", "p": list(p), "gatillo": True, "trabajo": 45,
                                   "avance": 10})
            await asyncio.sleep(0.1 / 5.0 * 0.5 * 2)  # ~5 mm/s
        puntos, _ = await recibir_hasta(ws2, lambda m: m["tipo"] == "puntos" and m["total"] > 500, 10)
        assert puntos["total"] > 500
        await vista.send_json({"orden": "terminar"})
        resultado, _ = await recibir_hasta(ws2, lambda m: m["tipo"] == "resultado", 10)
        assert resultado["puntos"] > 1000 and resultado["metricas"]["cobertura"] > 0.8
        await ws2.send_json({"orden": "iniciales", "texto": "ABC"})
        ranking, _ = await recibir_hasta(ws2, lambda m: m["tipo"] == "ranking" and m.get("posicion_nueva"), 15)
        assert ranking["top"][0]["iniciales"] == "ABC"


@pytest.mark.asyncio
async def test_perturbacion_fuera_de_alcance_pide_girarla(clase):
    clase.mesa.montar_a_mano("t")
    clase.mesa.mover_base(420.0, 260.0, 70.0)
    cola = clase.suscribir()
    clase.auto = False
    tarea = asyncio.create_task(clase._tras_montar("t"))
    try:
        for _ in range(100):
            await asyncio.sleep(0.05)
            msgs = [json.loads(cola.get_nowait()) for _ in range(cola.qsize())]
            alc = [m for m in msgs if m["tipo"] == "alcance"]
            if alc:
                assert alc[0]["llega"] is False
                break
        else:
            raise AssertionError("no llegó el mensaje de alcance")
        clase.mesa.mover_base(c.POSICION_BASE.x, c.POSICION_BASE.y, c.POSICION_BASE.giro)
        await asyncio.wait_for(tarea, 10)
    finally:
        tarea.cancel()


@pytest.mark.asyncio
async def test_cada_pestana_tiene_su_partida(alcance):
    def fabrica():
        m = MesaSim(tiempo_real=False)
        return ClaseSim(m, EjecutorRapido(m), alcance, ranking=Ranking(None))

    app = crear_app(fabrica, iniciar=False, modo="por_pestana", maximo=2)
    async with TestClient(TestServer(app)) as cli:
        escenas = {}
        for ident in ("uno", "dos", "tres"):
            ws = await cli.ws_connect(f"/ws_sim?partida={ident}")
            escenas[ident], _ = await recibir_hasta(ws, lambda m: m["tipo"] == "escena", 30)
        assert escenas["uno"]["partida"] == "uno" and not escenas["uno"]["compartida"]
        assert escenas["dos"]["partida"] == "dos"
        assert escenas["tres"]["partida"] == "principal" and escenas["tres"]["compartida"]  # aforo lleno
        abiertas = app["partidas"].abiertas
        assert abiertas["uno"].clase.mesa is not abiertas["dos"].clase.mesa
        # una perturbación en una partida no toca la otra
        ws = await cli.ws_connect("/ws_sim?partida=uno")
        await ws.send_json({"orden": "montar_a_mano", "junta": "t"})
        await asyncio.sleep(0.2)
        assert abiertas["uno"].clase.mesa.junta_montada() == "t"
        assert abiertas["dos"].clase.mesa.junta_montada() is None
        # la voz de la tablet usa el contexto de su partida (por el Referer de la página)
        r = await cli.post("/api/voz", json={"texto": "móntame una T"},
                           headers={"Referer": "http://x/v2/index.html?partida=uno"})
        assert (await r.json())["motivo"] == "ya_montada"
