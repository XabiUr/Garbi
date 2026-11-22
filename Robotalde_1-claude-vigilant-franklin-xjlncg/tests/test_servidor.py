"""Servidor: máquina de estados de la demo, LED del robot solo en los huecos y prueba de punta a punta."""
import asyncio
import json

import pytest
from aiohttp.test_utils import TestClient, TestServer

from lewelder.antorcha import AntorchaRobot
from lewelder.antorcha_virtual import AntorchaRobotVirtual
from lewelder.contrato import LONGITUD_CORDON, Muestra, TipoPieza
from lewelder.fuentes import ConfigPasada, FuenteSimulada, Latido
from lewelder.robot import RobotCinematico
from lewelder.servidor import Escuela, contrato_para_web, crear_app
from lewelder.sintetico import pasada_sintetica


class FuenteGuion:
    """Fuente de prueba: los eventos se meten a mano con `Escuela.procesar`."""

    nombre = "prueba"

    def __init__(self, tipo="recta", anclaje="B"):
        self.tipo, self.anclaje = TipoPieza(tipo), anclaje
        self.pasadas = self.taras = 0

    async def iniciar(self):
        pass

    async def muestras(self):
        while True:
            await asyncio.sleep(3600)
            yield Latido(0.0)

    def tara(self):
        self.taras += 1
        return True

    def empezar_pasada(self):
        self.pasadas += 1

    def pieza(self):
        return self.tipo, self.anclaje

    def configurar(self, tipo=None, anclaje=None):
        if tipo is not None:
            self.tipo = TipoPieza(tipo)
        if anclaje is not None:
            self.anclaje = anclaje

    def estado(self):
        return {"fuente": self.nombre, "tipo": self.tipo.value, "anclaje": self.anclaje}

    async def cerrar(self):
        pass


def soldar(escuela, huecos=(), velocidad=5.0, t0=100.0, **kw):
    """Mete una pasada sintética como la daría la cámara (sin punta mientras el gatillo está suelto) y luego
    latidos hasta que el examen se cierra solo."""
    muestras = pasada_sintetica("recta", velocidad=velocidad, frecuencia=30, huecos=huecos, angulo_trabajo=90,
                                angulo_avance=10, **kw)
    anterior = False
    for m in muestras:
        t = t0 + m.t
        if m.gatillo or anterior:  # la muestra de "gatillo soltado" sí llega
            escuela.procesar(Muestra(t, m.x, m.y, m.z, m.gatillo, m.angulo_trabajo, m.angulo_avance))
        else:
            escuela.procesar(Latido(t))
        anterior = m.gatillo
    t = t0 + muestras[-1].t
    for k in range(1, 300):
        if escuela.modo != "examen":
            return
        escuela.procesar(Latido(t + k / 30))
    raise AssertionError("el examen no se cerró solo")


def mensajes(cola):
    salida = []
    while not cola.empty():
        salida.append(json.loads(cola.get_nowait()))
    return salida


@pytest.fixture
def escuela(tmp_path):
    e = Escuela(FuenteGuion(), RobotCinematico(escala_tiempo=200), None, dir_pasadas=tmp_path)
    yield e


async def esperar_robot(escuela):
    while escuela.robot_ocupado:
        await asyncio.sleep(0.01)
    await asyncio.sleep(0.05)


# --- máquina de estados ------------------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_examen_nota_repaso_con_hueco(escuela, tmp_path):
    cola = escuela.suscribir()
    assert escuela.modo == "espera"
    assert await escuela.orden({"orden": "repaso"}) is not None  # sin nota no hay repaso
    assert await escuela.orden({"orden": "empezar_examen"}) is None
    assert escuela.modo == "examen" and escuela.fuente.pasadas == 1
    assert await escuela.orden({"orden": "empezar_examen"}) == "ya hay un examen en curso"
    soldar(escuela, huecos=[(40, 55)])
    assert escuela.modo == "nota"
    assert escuela.resultado.huecos == [(40.0, 55.0)]
    assert escuela.puede_repaso and not escuela.certificable
    assert await escuela.orden({"orden": "certificado"}) is not None
    tipos = [m["tipo"] for m in mensajes(cola)]
    assert {"estado", "muestra", "evaluacion", "aviso", "resultado"} <= set(tipos)
    await asyncio.sleep(0.05)  # valoración por reglas y registro
    assert escuela.valoracion["origen"] == "reglas"

    assert await escuela.orden({"orden": "repaso"}) is None
    assert escuela.modo == "repaso" and escuela.instruccion == "suelda la unión recta del anclaje B"
    assert await escuela.orden({"orden": "empezar_examen"}) is not None  # robot ocupado
    await esperar_robot(escuela)
    # El LED solo luce con la punta dentro del hueco.
    con_led = [m.x for m, led in escuela.robot_muestras if led]
    sin_led = [m for m, led in escuela.robot_muestras if not led]
    assert con_led and min(con_led) >= 40.0 and max(con_led) < 55.0
    assert not any(40.5 < m.x < 54.5 and m.z < 5 for m in sin_led)
    assert escuela.repasados[8:11] == [True] * 3 and sum(escuela.repasados) == 3
    assert escuela.cobertura_final() == 100.0
    fin = [m for m in mensajes(cola) if m["tipo"] == "robot_fin"]
    assert fin and fin[0]["cobertura_final"] == 100.0
    registros = sorted(p.name for p in tmp_path.glob("*.json"))
    assert any("examen" in r for r in registros) and any("repaso" in r for r in registros)
    examen = json.loads(next(tmp_path.glob("*examen*.json")).read_text())
    assert examen["resultado"]["huecos"] == [[40.0, 55.0]] and examen["valoracion"]["origen"] == "reglas"
    assert len(examen["muestras"]) > 500

    await escuela.orden({"orden": "reiniciar"})
    assert escuela.modo == "espera" and escuela.resultado is None and not escuela.led_robot


@pytest.mark.asyncio
async def test_sin_huecos_certificado_y_maestro(escuela):
    await escuela.orden({"orden": "empezar_examen"})
    soldar(escuela)
    assert escuela.modo == "nota" and escuela.certificable and not escuela.puede_repaso
    assert await escuela.orden({"orden": "repaso"}) == "no hay huecos que repasar"
    assert await escuela.orden({"orden": "certificado"}) is None
    estado = escuela.estado()
    assert estado["modo"] == "certificado"
    assert estado["certificado"]["titulo"] == "Certificado de oficial soldador LeWelder"
    # Desde el certificado, el robot suelda la T entera con el LED encendido en todo el cordón.
    assert await escuela.orden({"orden": "maestro", "tipo": "t"}) is None
    assert escuela.modo == "maestro" and escuela.instruccion == "suelda la unión en T del anclaje B"
    await esperar_robot(escuela)
    sobre_cordon = [(m, led) for m, led in escuela.robot_muestras if 0.5 < m.x < LONGITUD_CORDON - 0.5 and m.z < 5]
    assert sobre_cordon and all(led for _, led in sobre_cordon)
    assert not any(led for m, led in escuela.robot_muestras if m.x < 0 or m.x > LONGITUD_CORDON)
    assert all(escuela.repasados) and escuela.robot_terminado and not escuela.led_robot


@pytest.mark.asyncio
async def test_cambio_de_nivel_rejuzga_la_pasada(escuela):
    await escuela.orden({"orden": "empezar_examen"})
    soldar(escuela, desvio_mm=4.0, temblor_mm=0.3)  # dentro de ±5 mm pero fuera de ±3 mm
    assert escuela.resultado.nivel == "oficial" and not escuela.resultado.huecos and escuela.certificable
    nota_oficial = escuela.resultado.nota
    assert await escuela.orden({"orden": "nivel", "nivel": "maestro"}) is None
    assert escuela.nivel == "maestro" and escuela.resultado.nivel == "maestro"
    assert escuela.resultado.nota < nota_oficial and escuela.resultado.huecos  # a ±3 mm se queda sin cubrir
    assert not escuela.certificable
    assert await escuela.orden({"orden": "certificado"}) is not None
    assert await escuela.orden({"orden": "nivel", "nivel": "experto"}) is not None


@pytest.mark.asyncio
async def test_terminar_a_mano_y_ordenes_varias(escuela):
    assert await escuela.orden({"orden": "terminar"}) is not None
    await escuela.orden({"orden": "empezar_examen"})
    escuela.procesar(Muestra(0.0, 10.0, 0.0, 3.0, True))
    escuela.procesar(Muestra(0.1, 10.5, 0.0, 3.0, True))
    assert await escuela.orden({"orden": "nivel", "nivel": "aprendiz"}) is not None  # en mitad del examen no
    assert await escuela.orden({"orden": "terminar"}) is None
    assert escuela.modo == "nota" and escuela.resultado.cobertura_pct < 10
    assert await escuela.orden({"orden": "tara"}) is None and escuela.fuente.taras == 1
    assert await escuela.orden({"orden": "politica", "politica": "act"}) is None
    assert escuela.robot.politica == "act"
    assert await escuela.orden({"orden": "politica", "politica": "pi0"}) is not None
    assert await escuela.orden({"orden": "pieza", "tipo": "t", "anclaje": "D"}) is None
    assert escuela.pieza() == (TipoPieza.T, "D")
    assert await escuela.orden({"orden": "simulacion", "pasada": "perfecta"}) is not None  # no es simulada
    assert await escuela.orden({"orden": "volar"}) == "orden desconocida: volar"


def test_contrato_para_web():
    c = contrato_para_web()
    assert c["n_tramos"] == 24 and c["tolerancias"]["oficial"] == 5.0 and set(c["anclajes"]) == set("ABCD")


# --- LED del robot con la antorcha virtual -----------------------------------------------------------------------
@pytest.mark.asyncio
async def test_led_del_robot_solo_en_los_huecos_por_serie(tmp_path):
    robot = RobotCinematico(escala_tiempo=10)
    cambios = []
    virtual = AntorchaRobotVirtual(al_cambiar=lambda e: cambios.append((e, robot.punta.x)))
    antorcha = AntorchaRobot(virtual.ruta)
    escuela = Escuela(FuenteGuion(), robot, antorcha, dir_pasadas=None)
    try:
        await escuela.orden({"orden": "empezar_examen"})
        soldar(escuela, huecos=[(20, 30), (75, 90)])
        assert escuela.resultado.huecos == [(20.0, 30.0), (75.0, 90.0)]
        await escuela.orden({"orden": "repaso"})
        await esperar_robot(escuela)
        await asyncio.sleep(0.1)
    finally:
        await asyncio.to_thread(antorcha.cerrar)
        virtual.parar()
    # Registro de la placa virtual: encendido-apagado dos veces, y nada más (el cierre no lo vuelve a encender).
    assert [e for _, e in virtual.registro] == [True, False, True, False]
    encendidos = [x for e, x in cambios if e]
    apagados = [x for e, x in cambios if not e]
    assert encendidos[0] == pytest.approx(20.0, abs=2.0) and apagados[0] == pytest.approx(30.0, abs=2.0)
    assert encendidos[1] == pytest.approx(75.0, abs=2.0) and apagados[1] == pytest.approx(90.0, abs=2.0)


# --- de punta a punta por WebSocket ------------------------------------------------------------------------------
async def leer_hasta(ws, condicion, timeout=60.0, vistos=None):
    async def bucle():
        while True:
            m = json.loads((await ws.receive()).data)
            if vistos is not None:
                vistos.append(m)
            if condicion(m):
                return m
    return await asyncio.wait_for(bucle(), timeout)


@pytest.mark.asyncio
async def test_punta_a_punta_websocket(tmp_path):
    """Servidor con la fuente simulada (pasada con un hueco) → examen → nota con ese hueco → repaso → el LED se
    enciende solo en el hueco → sin certificado; luego una pasada perfecta → certificado."""
    robot = RobotCinematico(escala_tiempo=8)
    cambios = []
    virtual = AntorchaRobotVirtual(al_cambiar=lambda e: cambios.append((e, robot.punta.x)))
    fuente = FuenteSimulada("recta", "B", config=ConfigPasada(velocidad=10.0, huecos=[(40.0, 55.0)]), fps=15,
                            tiempo_real=False, ancho=640, alto=360)
    escuela = Escuela(fuente, robot, AntorchaRobot(virtual.ruta), dir_pasadas=tmp_path)
    cliente = TestClient(TestServer(crear_app(escuela)))
    await cliente.start_server()
    try:
        contrato = await (await cliente.get("/api/contrato")).json()
        assert contrato["longitud_cordon"] == 120.0
        assert (await cliente.get("/")).status == 200
        assert (await cliente.get("/vendor/three-0.170.0.module.min.js")).status == 200
        ws = await cliente.ws_connect("/ws")
        estado = await leer_hasta(ws, lambda m: m["tipo"] == "estado")
        assert estado["modo"] == "espera" and estado["fuente"]["tara"] and estado["fuente"]["fuente"] == "simulada"
        await leer_hasta(ws, lambda m: m["tipo"] == "historial")

        # Examen con un hueco.
        await ws.send_json({"orden": "empezar_examen"})
        vistos = []
        r = await leer_hasta(ws, lambda m: m["tipo"] == "resultado", vistos=vistos)
        muestras = [m for m in vistos if m["tipo"] == "muestra"]
        assert len(muestras) > 50 and {"calidad", "x", "angulo_trabajo"} <= set(muestras[0])
        assert any(m["tipo"] == "evaluacion" for m in vistos)
        assert any(m["tipo"] == "aviso" and "gatillo" in m["texto"] for m in vistos)
        assert r["resultado"]["huecos"] == [[40.0, 55.0]] and r["resultado"]["aprobado"] is True
        valoracion = await leer_hasta(ws, lambda m: m["tipo"] == "valoracion")
        assert "40 mm a 55 mm" in valoracion["texto"]

        # Repaso: el robot recorre el cordón y el LED solo luce en el hueco.
        await ws.send_json({"orden": "repaso"})
        vistos = []
        fin = await leer_hasta(ws, lambda m: m["tipo"] == "robot_fin", vistos=vistos)
        robot_msgs = [m for m in vistos if m["tipo"] == "robot"]
        assert robot_msgs and robot_msgs[0]["instruccion"] == "suelda la unión recta del anclaje B"
        con_led = [m["punta"]["x"] for m in robot_msgs if m["led"]]
        assert con_led and 39.0 <= min(con_led) and max(con_led) <= 56.0
        assert fin["repasados"][8:11] == [True] * 3 and sum(fin["repasados"]) == 3
        assert fin["cobertura_final"] == 100.0
        await asyncio.sleep(0.1)
        assert [e for _, e in virtual.registro] == [True, False]
        assert cambios[0][1] == pytest.approx(40.0, abs=2.0) and cambios[1][1] == pytest.approx(55.0, abs=2.0)
        estado = await leer_hasta(ws, lambda m: m["tipo"] == "estado")
        assert estado["modo"] == "repaso" and estado["robot"]["terminado"] and not estado["certificado"]
        await ws.send_json({"orden": "certificado"})
        assert (await leer_hasta(ws, lambda m: m["tipo"] == "error"))["texto"]

        # Pasada perfecta → certificado.
        await ws.send_json({"orden": "reiniciar"})
        await ws.send_json({"orden": "simulacion", "pasada": {"velocidad": 10.0, "huecos": []}})
        await leer_hasta(ws, lambda m: m["tipo"] == "info")
        await ws.send_json({"orden": "empezar_examen"})
        r = await leer_hasta(ws, lambda m: m["tipo"] == "resultado")
        assert r["resultado"]["huecos"] == [] and r["resultado"]["aprobado"]
        await ws.send_json({"orden": "certificado"})
        estado = await leer_hasta(ws, lambda m: m["tipo"] == "estado" and m["modo"] == "certificado")
        assert estado["certificado"]["titulo"] == "Certificado de oficial soldador LeWelder"
        await ws.close()
        for _ in range(100):  # el registro se escribe en segundo plano
            if len(list(tmp_path.glob("*examen*.json"))) == 2:
                break
            await asyncio.sleep(0.02)
        assert len(list(tmp_path.glob("*examen*.json"))) == 2 and len(list(tmp_path.glob("*repaso*.json"))) == 1
    finally:
        await cliente.close()
        virtual.parar()
