"""Voz → orden: respaldo por reglas sin red, LLM simulado, contexto que impide órdenes y endpoint `/api/voz`."""
import asyncio
import json
import time
from types import SimpleNamespace

import pytest
from aiohttp.test_utils import TestClient, TestServer

from lewelder import voz
from lewelder.contrato import ORDENES, TipoJunta, orden_montar
from lewelder.personaje import NOMBRE, Personaje
from lewelder.voz import Contexto, interpretar, interpretar_por_reglas

T = orden_montar(TipoJunta.T)
ESQ = orden_montar(TipoJunta.ESQUINA)
SEN = "señala el cordón"
SOL = "coge la antorcha y suelda la junta"
DES = "desmonta la junta"
ACE = "acércame la antorcha"
GIR = "gira la junta hacia ti"


def test_constantes_del_vocabulario():
    assert {T, ESQ, SEN, SOL, DES, ACE, GIR} == set(ORDENES)
    assert set(voz.PREGUNTAS) == set(ORDENES)
    assert voz.PREGUNTAS[ESQ] == "¿Monto una unión en esquina?"


# --- reglas sin red ----------------------------------------------------------------------------------------------
FRASES = [
    # las del vocabulario, tal cual
    ("Monta una unión en T", T),
    ("monta una unión en esquina", ESQ),
    ("señala el cordón", SEN),
    ("coge la antorcha y suelda la junta", SOL),
    ("desmonta la junta", DES),
    ("acércame la antorcha", ACE),
    ("gira la junta hacia ti", GIR),
    # como las diría un juez
    ("móntame una esquina", ESQ),
    ("monta una T", T),
    ("pon la té", T),
    ("hazme una ele", ESQ),
    ("una esquina", ESQ),
    ("¿dónde se suelda?", SEN),
    ("suelda tú", SOL),
    ("enséñame", SOL),
    ("recoge", DES),
    ("dame la antorcha", ACE),
    ("quiero una T", T),
    ("prepárame una unión en L", ESQ),
    ("ponme una unión en ángulo", ESQ),
    ("señálame dónde va el cordón", SEN),
    ("¿por dónde tengo que soldar?", SEN),
    ("enséñame dónde se suelda", SEN),
    ("apunta al cordón", SEN),
    ("a ver cómo lo haces tú", SOL),
    ("demuéstrame cómo se suelda", SOL),
    ("suelda la junta", SOL),
    ("quita la pieza", DES),
    ("recoge la mesa", DES),
    ("pásame la antorcha", ACE),
    ("tráeme el soplete", ACE),
    ("gírala hacia ti", GIR),
    ("dale la vuelta a la junta", GIR),
    ("MÓNTAME UNA ESQUINA!!!", ESQ),
    ("no la T, la esquina", ESQ),
    ("te monto una esquina", ESQ),
    # mal transcritas por el reconocimiento de voz
    ("montame una es quina", ESQ),
    ("des monta la junta", DES),
    ("hasme una unión en te", T),
    ("móntame una té", T),
    ("zelda la junta", SOL),
    ("señal a el cordón", SEN),
    ("monta una unión en tea", T),
    ("monta una esquín", ESQ),
]

FUERA = ["¿qué tiempo hace mañana?", "hola", "", "   ", "cuéntame un chiste", "¿cuántos años tienes?"]


@pytest.mark.parametrize("texto, orden", FRASES)
def test_reglas_entienden_frases_variadas(texto, orden):
    r = interpretar_por_reglas(texto)
    assert r.orden == orden, f"{texto!r} → {r.orden!r}"
    assert r.aclaracion is None
    assert r.confianza >= 0.6
    assert r.origen == "reglas"


def test_hay_al_menos_40_frases():
    assert len(FRASES) + len(FUERA) + 2 >= 40


@pytest.mark.parametrize("texto", FUERA)
def test_fuera_de_vocabulario_no_se_entiende(texto):
    r = interpretar_por_reglas(texto)
    assert r.orden is None and r.confianza == 0.0 and r.aclaracion is None
    assert not r.confirmable


@pytest.mark.parametrize("texto", ["monta", "móntame una", "una T o una esquina"])
def test_ambiguo_pregunta_t_o_esquina(texto):
    r = interpretar_por_reglas(texto)
    assert r.orden is None and r.aclaracion == "¿T o esquina?"
    assert set(r.opciones) == {T, ESQ}
    assert 0 < r.confianza < voz.UMBRAL_REGLAS and not r.confirmable


def test_las_frases_claras_superan_el_umbral():
    for texto in ["móntame una esquina", "pon la té", "desmonta la junta", "¿dónde se suelda?"]:
        assert interpretar_por_reglas(texto).confianza >= voz.UMBRAL_REGLAS


def test_confirmable_con_pregunta_de_tarjeta():
    r = interpretar_por_reglas("móntame una esquina")
    assert r.confirmable and r.permitida
    assert r.pregunta == "¿Monto una unión en esquina?"
    d = r.a_dict()
    assert d["orden"] == ESQ and d["pregunta"] == r.pregunta and d["confirmable"] is True
    assert isinstance(d["respuesta"], str) and d["respuesta"]
    json.dumps(d)  # serializable


# --- contexto ------------------------------------------------------------------------------------------------
def test_no_se_desmonta_sin_junta():
    r = interpretar_por_reglas("desmonta la junta", Contexto(junta_montada=None))
    assert r.orden == DES and not r.permitida and not r.confirmable
    assert r.motivo == "sin_junta"
    assert r.respuesta in Personaje().banco("sin_junta", junta=None)


@pytest.mark.parametrize("texto", ["señala el cordón", "suelda tú", "gírala hacia ti"])
def test_sin_junta_no_se_senala_ni_suelda_ni_gira(texto):
    r = interpretar_por_reglas(texto, Contexto(junta_montada=None))
    assert not r.permitida and r.motivo == "sin_junta"


def test_con_junta_si_se_desmonta_y_senala():
    for texto in ["recoge", "¿dónde se suelda?", "suelda tú"]:
        r = interpretar_por_reglas(texto, Contexto(junta_montada=TipoJunta.T))
        assert r.permitida and r.confirmable


def test_montar_la_misma_junta_o_otra():
    r = interpretar_por_reglas("móntame una T", Contexto(junta_montada="t"))
    assert not r.permitida and r.motivo == "ya_montada"
    r = interpretar_por_reglas("móntame una T", Contexto(junta_montada="esquina"))
    assert not r.permitida and r.motivo == "otra_montada"
    assert "esquina" in r.respuesta.lower()


def test_junta_incompleta_solo_se_desmonta():
    ctx = Contexto(junta_montada="incompleta")
    assert interpretar_por_reglas("desmonta la junta", ctx).permitida
    assert interpretar_por_reglas("señala el cordón", ctx).motivo == "junta_incompleta"


def test_robot_ocupado_no_admite_ordenes():
    r = interpretar_por_reglas("acércame la antorcha", Contexto(robot_ocupado=True))
    assert not r.permitida and r.motivo == "ocupado"


def test_orden_de_nivel_no_alcanzado():
    r = interpretar_por_reglas("gira la junta hacia ti", Contexto(junta_montada="t", nivel_max=2))
    assert not r.permitida and r.motivo == "no_aprendido"


def test_junta_desconocida_no_restringe():
    ctx = Contexto(sabe_junta=False)
    assert interpretar_por_reglas("desmonta la junta", ctx).permitida
    assert interpretar_por_reglas("móntame una T", ctx).permitida


def test_contexto_desde_dict():
    ctx = Contexto.de_dict({"junta_montada": "esquina", "robot_ocupado": True, "nivel_max": 2, "otro": 1})
    assert ctx.junta_montada == TipoJunta.ESQUINA and ctx.robot_ocupado and ctx.nivel_max == 2
    assert Contexto.de_dict({"junta_montada": "rara"}).junta_montada is None
    assert Contexto.de_dict(None) == Contexto()


# --- LLM simulado ------------------------------------------------------------------------------------------------
class ClienteFalso:
    """Imita `AsyncAnthropic().beta.messages.create` con salida estructurada."""

    def __init__(self, respuesta=None, espera=0.0, error=None, stop_reason="end_turn", texto=None):
        self.llamadas = []
        self.respuesta, self.espera, self.error, self.stop_reason = respuesta, espera, error, stop_reason
        self.texto = texto
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._crear))

    async def _crear(self, **kwargs):
        self.llamadas.append(kwargs)
        await asyncio.sleep(self.espera)
        if self.error:
            raise self.error
        texto = self.texto if self.texto is not None else json.dumps(self.respuesta, ensure_ascii=False)
        bloques = [SimpleNamespace(type="thinking", thinking=""), SimpleNamespace(type="text", text=texto)]
        return SimpleNamespace(content=bloques, stop_reason=self.stop_reason)


@pytest.mark.asyncio
async def test_reglas_seguras_no_llaman_al_llm():
    cliente = ClienteFalso({"orden": T, "confianza": 0.9, "aclaracion": ""})
    r = await interpretar("móntame una esquina", Contexto(), cliente=cliente)
    assert r.orden == ESQ and r.origen == "reglas" and cliente.llamadas == []


@pytest.mark.asyncio
async def test_llm_valido_cuando_las_reglas_dudan():
    cliente = ClienteFalso({"orden": ESQ, "confianza": 0.9, "aclaracion": ""})
    texto = "eso que hace un ángulo recto con dos chapas por el borde"
    assert interpretar_por_reglas(texto).confianza < voz.UMBRAL_REGLAS
    r = await interpretar(texto, Contexto(), cliente=cliente, modelo="claude-opus-5-5")
    assert r.orden == ESQ and r.origen == "llm" and r.confirmable and r.modelo == "claude-opus-5-5"
    peticion = cliente.llamadas[0]
    assert peticion["model"] == "claude-opus-5-5"
    assert peticion["system"] == voz.SISTEMA_VOZ
    formato = peticion["output_config"]["format"]
    assert formato["type"] == "json_schema"
    esquema = formato["schema"]
    assert set(esquema["properties"]["orden"]["enum"]) == set(ORDENES) | {voz.NINGUNA}
    assert esquema["additionalProperties"] is False
    assert peticion["output_config"]["effort"] == "low"
    assert texto in peticion["messages"][0]["content"]


@pytest.mark.asyncio
async def test_llm_aclaracion():
    cliente = ClienteFalso({"orden": voz.NINGUNA, "confianza": 0.4, "aclaracion": "¿T o esquina?"})
    r = await interpretar("móntame una de esas", Contexto(), cliente=cliente)
    assert r.orden is None and r.aclaracion == "¿T o esquina?" and r.origen == "llm"


@pytest.mark.asyncio
async def test_llm_ninguna_es_no_entendido():
    cliente = ClienteFalso({"orden": voz.NINGUNA, "confianza": 0.9, "aclaracion": ""})
    r = await interpretar("¿qué tiempo hace?", Contexto(), cliente=cliente)
    assert r.orden is None and r.aclaracion is None and r.origen == "llm" and r.motivo == "no_entendido"


@pytest.mark.asyncio
@pytest.mark.parametrize("cliente", [
    ClienteFalso({"orden": "baila la conga", "confianza": 0.9, "aclaracion": ""}),
    ClienteFalso({"orden": ESQ}),
    ClienteFalso(texto="no es json"),
    ClienteFalso(texto="[1, 2]"),
    ClienteFalso({"orden": ESQ, "confianza": "mucha", "aclaracion": ""}),
    ClienteFalso(stop_reason="refusal", texto=""),
    ClienteFalso(error=ConnectionError("sin red")),
])
async def test_llm_invalido_usa_reglas(cliente):
    r = await interpretar("monta", Contexto(), cliente=cliente)
    assert r.origen == "reglas" and r.aclaracion == "¿T o esquina?"


@pytest.mark.asyncio
async def test_llm_lento_se_corta():
    inicio = time.monotonic()
    r = await interpretar("monta", Contexto(), cliente=ClienteFalso(espera=10.0), tiempo_max=0.2)
    assert r.origen == "reglas" and time.monotonic() - inicio < 1.0


@pytest.mark.asyncio
async def test_contexto_se_aplica_tambien_al_llm():
    cliente = ClienteFalso({"orden": DES, "confianza": 0.9, "aclaracion": ""})
    r = await interpretar("haz desaparecer eso de la base", Contexto(junta_montada=None), cliente=cliente)
    assert r.origen == "llm" and r.orden == DES and not r.permitida and r.motivo == "sin_junta"


@pytest.mark.asyncio
async def test_alternativas_del_reconocedor():
    r = await interpretar("mon tame una es", Contexto(), alternativas=["móntame una esquina", "mon tame una s"])
    assert r.orden == ESQ and r.texto == "móntame una esquina"


@pytest.mark.asyncio
async def test_sin_cliente_ni_texto():
    r = await interpretar("", Contexto(), cliente=ClienteFalso({"orden": T, "confianza": 1, "aclaracion": ""}))
    assert r.orden is None and r.origen == "reglas"


# --- endpoint ------------------------------------------------------------------------------------------------------
class FuenteQuieta:
    nombre = "prueba"

    async def iniciar(self):
        pass

    async def muestras(self):
        while True:
            await asyncio.sleep(3600)
            yield None

    def pieza(self):
        from lewelder.contrato import TipoPieza
        return TipoPieza.T, "B"

    def estado(self):
        return {"fuente": self.nombre}

    async def cerrar(self):
        pass


@pytest.mark.asyncio
async def test_endpoint_voz(tmp_path):
    from lewelder.servidor import Escuela, crear_app

    escuela = Escuela(FuenteQuieta(), None, dir_pasadas=tmp_path)
    cliente = TestClient(TestServer(crear_app(escuela, iniciar=False)))
    await cliente.start_server()
    try:
        r = await cliente.post("/api/voz", json={"texto": "móntame una esquina"})
        assert r.status == 200
        d = await r.json()
        assert d["orden"] == ESQ and d["confirmable"] and d["pregunta"] == "¿Monto una unión en esquina?"
        assert d["personaje"]["nombre"] == NOMBRE and d["personaje"]["voz"]["lang"] == "es-ES"
        assert d["respuesta"]

        # el contexto de la petición manda sobre lo que no sabe el servidor
        r = await cliente.post("/api/voz", json={"texto": "desmonta la junta", "contexto": {"junta_montada": None}})
        d = await r.json()
        assert d["orden"] == DES and d["permitida"] is False and d["motivo"] == "sin_junta"

        r = await cliente.post("/api/voz", json={"texto": "mon ta", "alternativas": ["monta una T"]})
        assert (await r.json())["orden"] == T

        for malo in [{"texto": 3}, {"nada": 1}, {"texto": "x" * 1000}]:
            assert (await cliente.post("/api/voz", json=malo)).status == 400
        assert (await cliente.post("/api/voz", data="no es json")).status == 400
        assert (await cliente.get("/voz.js")).status == 200
        assert (await cliente.get("/voz.css")).status == 200
    finally:
        await cliente.close()
