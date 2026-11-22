"""App del producto Garbi: endpoints, emergencia, chat con LLM (respaldo sin conexión y Claude con un cliente falso),
seta global con un doble de teclado, indicadores, registro CSV y el puente con el orquestador real."""
from __future__ import annotations

import time
from types import SimpleNamespace

import numpy as np
import pytest
from aiohttp.test_utils import TestClient, TestServer

from garbi.producto.app.indicadores import Indicadores, Registro
from garbi.producto.app.llm import COMANDOS_CHAT, HERRAMIENTAS, AsistenteGarbi, interpretar_local
from garbi.producto.app.puente import (DemoSistema, Orquestador, OrquestadorFalso, PuenteOrquestador, a_jpeg,
                                       eventos_nuevos)
from garbi.producto.app.servidor import ServidorApp, crear_app
from garbi.producto.app.teclado import SetaGlobal
from garbi.producto.contrato import Comando, Estado


class Reloj:
    def __init__(self, t=1000.0):
        self.t = t

    def __call__(self):
        return self.t


@pytest.fixture
def orq():
    return OrquestadorFalso(reloj=Reloj(), automatico=False)


def asistente_local(orq):
    return AsistenteGarbi(orq, usar_api=False)


# --- puente y orquestador falso ---------------------------------------------------------------------------------------

def test_orquestador_falso_cumple_el_protocolo(orq):
    assert isinstance(orq, Orquestador)
    e = orq.estado_app()
    assert e.estado is Estado.REPOSO and not e.aspiradora
    imgs = orq.imagenes_anotadas()
    assert set(imgs) == {"top", "wrist"} and imgs["top"].shape == (480, 640, 3)
    assert a_jpeg(imgs["top"])[:2] == b"\xff\xd8"


def test_orquestador_falso_recorre_el_guion_e_indicadores():
    reloj = Reloj()
    orq = OrquestadorFalso(reloj=reloj)
    vistos = []
    for _ in range(80):   # 40 s: más de una vuelta del guion
        reloj.t += 0.5
        vistos.append(orq.estado_app().estado)
    for estado in (Estado.ACERCAMIENTO, Estado.EN_BROCA, Estado.DESPIERTO, Estado.LIMPIEZA_TABLA,
                   Estado.LIMPIEZA_TAPETE):
        assert estado in vistos
    ind = orq.estado_app().indicadores
    assert ind["agujeros"] >= 2 and ind["limpiezas_tabla"] >= 1 and ind["limpiezas_tapete"] >= 1
    assert ind["t_aspirando"] > 10 and ind["disponibilidad"] == pytest.approx(1.0)


def test_emergencia_solo_sale_con_rearmar(orq):
    orq.comando(Comando.EMERGENCIA)
    assert orq.estado_app().estado is Estado.EMERGENCIA
    orq.comando(Comando.LIMPIAR_TABLA)
    assert orq.estado_app().estado is Estado.EMERGENCIA
    orq.comando(Comando.REARMAR)
    assert orq.estado_app().estado is Estado.REPOSO


# --- endpoints --------------------------------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_endpoints_estado_comando_emergencia(orq):
    async with TestClient(TestServer(crear_app(orq, asistente_local(orq), demo=True))) as c:
        r = await c.get("/api/estado")
        d = await r.json()
        assert r.status == 200 and d["estado"] == "reposo" and d["demo"] is True
        assert {"vision", "manos", "politica", "robot", "aspiradora", "llm", "seta"} <= set(d["tecnologias"])
        assert d["tecnologias"]["aspiradora"] == "manual" and d["llm"] == "local"
        assert {"agujeros", "t_aspirando", "disponibilidad", "t_emergencia"} <= set(d["indicadores"])

        r = await c.post("/api/comando", json={"comando": "limpiar_tapete"})
        assert r.status == 200
        assert (await (await c.get("/api/estado")).json())["estado"] == "limpieza_tapete"

        r = await c.post("/api/comando", json={"comando": "bailar"})
        assert r.status == 400 and "validos" in await r.json()
        r = await c.post("/api/comando", data="esto no es json")
        assert r.status == 400

        r = await c.post("/api/emergencia?origen=espacio")
        assert r.status == 200 and orq.comandos[-1] is Comando.EMERGENCIA
        assert (await (await c.get("/api/estado")).json())["estado"] == "emergencia"
        await c.post("/api/comando", json={"comando": "rearmar"})
        assert orq.estado_app().estado is Estado.REPOSO


@pytest.mark.asyncio
async def test_pagina_fotos_video_y_estaticos(orq):
    async with TestClient(TestServer(crear_app(orq, asistente_local(orq)))) as c:
        r = await c.get("/")
        html = await r.text()
        assert r.status == 200 and "Garbi" in html and "boton-emergencia" in html
        for ruta in ("/static/app.js", "/static/app.css", "/static/logo.svg"):
            assert (await c.get(ruta)).status == 200
        r = await c.get("/foto/top")
        assert r.status == 200 and r.content_type == "image/jpeg" and (await r.read())[:2] == b"\xff\xd8"
        assert (await c.get("/foto/nariz")).status == 404
        r = await c.get("/video/wrist")
        assert r.headers["Content-Type"].startswith("multipart/x-mixed-replace")
        trozo = await r.content.read(64)
        assert trozo.startswith(b"--frame")
        r.close()


@pytest.mark.asyncio
async def test_sin_imagen_da_sin_senal():
    class SinCamaras(OrquestadorFalso):
        def imagenes_anotadas(self):
            return {"top": None}

    orq = SinCamaras(reloj=Reloj(), automatico=False)
    async with TestClient(TestServer(crear_app(orq, asistente_local(orq)))) as c:
        r = await c.get("/foto/wrist")
        assert r.status == 200 and (await r.read())[:2] == b"\xff\xd8"


@pytest.mark.asyncio
async def test_chat_y_registro_csv(orq):
    async with TestClient(TestServer(crear_app(orq, asistente_local(orq)))) as c:
        d = await (await c.post("/api/chat", json={"texto": "Garbi, limpia la tabla"})).json()
        assert d["comandos"] == ["limpiar_tabla"] and d["fuente"] == "local" and d["respuesta"]
        d = await (await c.post("/api/chat", json={"texto": "para", "modo": "fabrica"})).json()
        assert d["comandos"] == ["parar"] and "detenido" in d["respuesta"].lower()
        await c.post("/api/comando", json={"comando": "apagar"})
        r = await c.get("/api/registro.csv")
        texto = await r.text()
        assert r.status == 200 and "attachment" in r.headers["Content-Disposition"]
        assert texto.startswith("﻿fecha_hora;tipo;origen;detalle;valor")
        assert "Disponibilidad (%)" in texto and ";comando;botón;apagar;" in texto and ";comando;chat;parar;" in texto


@pytest.mark.asyncio
async def test_foco_del_chat_silencia_la_seta_global(orq):
    app = crear_app(orq, asistente_local(orq))
    from garbi.producto.app.servidor import CLAVE

    ctx = app[CLAVE]
    async with TestClient(TestServer(app)) as c:
        await c.post("/api/foco_chat", json={"foco": True})
        assert ctx.escribiendo_en_chat()
        await c.post("/api/foco_chat", json={"foco": False})
        assert not ctx.escribiendo_en_chat()


def test_servidor_en_hilo_no_bloquea(orq):
    import urllib.request

    servidor = ServidorApp(crear_app(orq, asistente_local(orq)), puerto=0)
    t0 = time.perf_counter()
    servidor.arrancar()
    try:
        assert time.perf_counter() - t0 < 5   # arrancar() vuelve enseguida; el servidor sigue en su hilo
        with urllib.request.urlopen(servidor.url + "api/estado", timeout=5) as r:
            assert r.status == 200
    finally:
        servidor.parar()


# --- LLM: respaldo sin conexión ---------------------------------------------------------------------------------------

@pytest.mark.parametrize("frase, intencion", [
    ("¡Apágate!", "apagar"), ("apágate garbi", "apagar"), ("Enciéndete", "encender"), ("despierta", "encender"),
    ("Limpia la tabla", "limpiar_tabla"), ("limpia", "limpiar_tabla"), ("Limpia el tapete", "limpiar_tapete"),
    ("barre el tapete por favor", "limpiar_tapete"), ("para", "parar"), ("Garbi, para", "parar"),
    ("Para de limpiar la tabla", "parar"), ("stop", "parar"), ("apaga la aspiradora", "parar"),
    ("¿Qué estás haciendo?", "estado"), ("¿cómo vas?", "estado"), ("emergencia", "emergencia"),
    ("hola", "saludo"), ("xyzzy", None),
])
def test_respaldo_local_frases(frase, intencion):
    assert interpretar_local(frase) == intencion


def test_respaldo_local_ejecuta_y_nunca_emergencia(orq):
    a = asistente_local(orq)
    r = a.responder("enciéndete")
    assert r.comandos == [Comando.ENCENDER] and r.fuente == "local"
    r = a.responder("¡emergencia!")
    assert Comando.EMERGENCIA not in orq.comandos and r.comandos == [Comando.PARAR]
    r = a.responder("¿qué estás haciendo?")
    assert r.comandos == [] and "Estoy" in r.texto
    orq.comando(Comando.EMERGENCIA)
    n = len(orq.comandos)
    r = a.responder("limpia el tapete")
    assert r.comandos == [] and len(orq.comandos) == n and "Rearmar" in r.texto


def test_sin_clave_usa_respaldo(monkeypatch, orq):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    a = AsistenteGarbi(orq)
    assert not a.con_claude and a.estado_tecnologia().startswith("aviso")


# --- LLM: Claude con un cliente falso ---------------------------------------------------------------------------------

def bloque_texto(texto):
    return SimpleNamespace(type="text", text=texto)


def bloque_herramienta(nombre, entrada, id_="toolu_1"):
    return SimpleNamespace(type="tool_use", name=nombre, input=entrada, id=id_)


class ClienteFalso:
    """Imita `anthropic.Anthropic().messages.create` con respuestas guionizadas."""

    def __init__(self, respuestas=None, error=None):
        self.respuestas = list(respuestas or [])
        self.error = error
        self.llamadas = []
        self.messages = self

    def create(self, **kw):
        self.llamadas.append(kw)
        if self.error:
            raise self.error
        return self.respuestas.pop(0)


def respuesta(stop, *bloques):
    return SimpleNamespace(stop_reason=stop, content=list(bloques))


def test_claude_tool_use_ejecuta_el_comando(orq):
    cliente = ClienteFalso([
        respuesta("tool_use", bloque_herramienta("ejecutar_comando", {"comando": "limpiar_tapete"})),
        respuesta("end_turn", bloque_texto("¡Voy con el tapete!")),
    ])
    a = AsistenteGarbi(orq, cliente=cliente)
    r = a.responder("¿puedes limpiar el tapete?")
    assert r.fuente == "claude" and r.comandos == [Comando.LIMPIAR_TAPETE] and r.texto == "¡Voy con el tapete!"
    assert orq.comandos[-1] is Comando.LIMPIAR_TAPETE
    primera, segunda = cliente.llamadas
    assert primera["model"] == "claude-haiku-5-5" and primera["tools"] == HERRAMIENTAS
    assert primera["output_config"] == {"effort": "low"}
    resultado = segunda["messages"][-1]["content"][0]
    assert resultado["type"] == "tool_result" and resultado["tool_use_id"] == "toolu_1"
    assert a.estado_tecnologia().startswith("ok")


def test_claude_consulta_estado(orq):
    cliente = ClienteFalso([
        respuesta("tool_use", bloque_herramienta("consultar_estado", {})),
        respuesta("end_turn", bloque_texto("Estoy en reposo, esperando el taladro.")),
    ])
    r = AsistenteGarbi(orq, cliente=cliente).responder("¿qué haces?")
    assert r.comandos == [] and "reposo" in r.texto
    assert "Estoy en reposo" in cliente.llamadas[1]["messages"][-1]["content"][0]["content"]


def test_claude_nunca_emergencia_ni_rearmar(orq):
    assert "emergencia" not in HERRAMIENTAS[0]["input_schema"]["properties"]["comando"]["enum"]
    assert Comando.EMERGENCIA not in COMANDOS_CHAT and Comando.REARMAR not in COMANDOS_CHAT
    cliente = ClienteFalso([
        respuesta("tool_use", bloque_herramienta("ejecutar_comando", {"comando": "emergencia"})),
        respuesta("end_turn", bloque_texto("Usa la seta para eso.")),
    ])
    r = AsistenteGarbi(orq, cliente=cliente).responder("emergencia")
    assert r.comandos == [] and Comando.EMERGENCIA not in orq.comandos
    assert cliente.llamadas[1]["messages"][-1]["content"][0]["is_error"] is True


def test_claude_falla_y_usa_respaldo(orq):
    a = AsistenteGarbi(orq, cliente=ClienteFalso(error=ConnectionError("sin red")))
    r = a.responder("apágate")
    assert r.fuente == "local" and r.comandos == [Comando.APAGAR]
    assert "respaldo" in a.estado_tecnologia()


def test_claude_rechazo_usa_respaldo(orq):
    a = AsistenteGarbi(orq, cliente=ClienteFalso([respuesta("refusal")]))
    assert a.responder("para").fuente == "local"


# --- seta global (doble de teclado) -----------------------------------------------------------------------------------

def test_seta_global_espacio_y_antirrebote():
    reloj = Reloj(0.0)
    disparos = []
    seta = SetaGlobal(lambda: disparos.append(reloj.t), reloj=reloj)
    assert seta.tecla(True)
    assert not seta.tecla(True)     # rebote de la misma pulsación
    assert not seta.tecla(False)    # otra tecla
    reloj.t = 1.0
    assert seta.tecla(True)
    assert disparos == [0.0, 1.0]


def test_seta_global_respeta_el_chat_y_sobrevive_a_fallos():
    escribiendo = {"si": True}
    seta = SetaGlobal(lambda: 1 / 0, ignorar=lambda: escribiendo["si"])
    assert not seta.tecla(True)
    escribiendo["si"] = False
    assert seta.tecla(True)   # el fallo del callback no rompe el hook


def test_seta_global_con_backend_doble(monkeypatch):
    """Simula el oyente de pynput: arrancar() lo usa y una pulsación de espacio manda EMERGENCIA."""
    orq = OrquestadorFalso(reloj=Reloj(), automatico=False)
    seta = SetaGlobal(lambda: orq.comando(Comando.EMERGENCIA), backend="pynput")
    capturado = {}

    def arrancar_doble():
        capturado["tecla"] = lambda es_espacio: seta.tecla(es_espacio)
        return lambda: capturado.update(parado=True)

    monkeypatch.setattr(seta, "_arrancar_pynput", arrancar_doble)
    assert seta.arrancar() and seta.activa and seta.backend == "pynput"
    capturado["tecla"](True)
    assert orq.estado_app().estado is Estado.EMERGENCIA
    seta.parar()
    assert capturado["parado"] and not seta.activa


def test_seta_global_sin_backend_no_rompe(monkeypatch):
    seta = SetaGlobal(lambda: None)
    for nombre in ("_arrancar_pynput", "_arrancar_keyboard"):
        monkeypatch.setattr(seta, nombre, lambda: (_ for _ in ()).throw(ImportError("no instalado")))
    assert not seta.arrancar() and not seta.activa and "no instalado" in seta.motivo


# --- indicadores y registro -------------------------------------------------------------------------------------------

def test_indicadores_cuentan_y_disponibilidad():
    ind = Indicadores()
    secuencia = [(Estado.REPOSO, False), (Estado.EN_BROCA, True), (Estado.EN_BROCA, True), (Estado.EMERGENCIA, False),
                 (Estado.EMERGENCIA, False), (Estado.LIMPIEZA_TABLA, True), (Estado.LIMPIEZA_TAPETE, True)]
    for i, (estado, asp) in enumerate(secuencia):
        ind.observar(estado, asp, float(i))
    d = ind.como_dict()
    assert d["agujeros"] == 1 and d["limpiezas_tabla"] == 1 and d["limpiezas_tapete"] == 1
    assert d["t_aspirando"] == 3.0 and d["t_emergencia"] == 2.0
    assert d["disponibilidad"] == pytest.approx(4 / 6, abs=1e-3)


def test_registro_solo_apunta_eventos_nuevos():
    reg = Registro()
    reg.eventos_orquestador(["10:00:01 · b", "10:00:00 · a"])
    reg.eventos_orquestador(["10:00:02 · c", "10:00:01 · b", "10:00:00 · a"])
    assert [f[3] for f in reg.filas()] == ["a", "b", "c"]


def test_eventos_nuevos_con_tope():
    assert eventos_nuevos(["a", "b", "c"], ["b", "c", "d", "e"]) == ["d", "e"]
    assert eventos_nuevos([], ["a"]) == ["a"]
    assert eventos_nuevos(["a"], ["a"]) == []


# --- puente con el orquestador real -----------------------------------------------------------------------------------

def test_puente_con_el_orquestador_real():
    from garbi.producto.__main__ import crear_demo
    from garbi.producto.config import ConfigProducto

    sistema = crear_demo(ConfigProducto().validar())
    puente = PuenteOrquestador(sistema.orquestador, anotar=lambda img, vista: np.zeros_like(img))
    for _ in range(int(6 * sistema.hz)):   # 6 s de la escena guionizada
        with puente.cerrojo:
            sistema.paso()
        puente.publicar(sistema.imagenes, sistema.vista)
    e = puente.estado_app()
    assert e.eventos and " · " in e.eventos[0]           # con hora y el más nuevo primero
    assert puente.imagenes_anotadas()["top"].max() == 0   # anotada con la función dada
    puente.comando(Comando.EMERGENCIA)
    assert puente.estado_app().estado is Estado.EMERGENCIA


def test_demo_sistema_en_hilo():
    from garbi.producto.config import ConfigProducto

    demo = DemoSistema.crear(ConfigProducto().validar()).arrancar()
    try:
        time.sleep(0.5)
        assert demo.sistema.t > 0
        assert demo.imagenes_anotadas()["top"].shape[2] == 3
        demo.comando(Comando.EMERGENCIA)
        assert demo.estado_app().estado is Estado.EMERGENCIA
    finally:
        demo.parar()
