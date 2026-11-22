"""Instructor: avisos en vivo sin saturar y valoración final (LLM con respaldo por reglas)."""
import asyncio
import time
from types import SimpleNamespace

import pytest

from lewelder import instructor as ins
from lewelder.metricas import AVISO_DESVIO, AVISO_GATILLO, AVISO_RAPIDO, AVISO_VERTICAL, aviso_quemado, evaluar_pasada
from lewelder.sintetico import pasada_sintetica


@pytest.fixture(scope="module")
def con_hueco():
    return evaluar_pasada(pasada_sintetica("recta", huecos=[(40, 55)], angulo_trabajo=90, angulo_avance=10), "recta")


@pytest.fixture(scope="module")
def perfecta():
    return evaluar_pasada(pasada_sintetica("recta", angulo_trabajo=90, angulo_avance=10), "recta")


# --- avisos en vivo ----------------------------------------------------------------------------------------------
def test_prioridades():
    assert ins.prioridad(aviso_quemado(40)) == ins.ALTA
    assert ins.prioridad(AVISO_GATILLO) == ins.ALTA
    assert ins.prioridad(AVISO_DESVIO) == ins.MEDIA
    assert ins.prioridad(AVISO_VERTICAL) == ins.BAJA
    assert ins.prioridad("algo nuevo") == ins.MEDIA


def test_no_satura():
    i = ins.InstructorEnVivo()
    assert [a.texto for a in i.recibir([AVISO_RAPIDO], 1.0)] == [AVISO_RAPIDO]
    assert i.recibir([AVISO_DESVIO], 1.2) == []  # demasiado pronto y no es más grave
    assert i.recibir([], 1.6) == []
    mostrados = i.recibir([], 2.6)  # ya ha pasado el intervalo: sale el que esperaba
    assert [a.texto for a in mostrados] == [AVISO_DESVIO]
    assert [a.texto for a in i.mostrados] == [AVISO_RAPIDO, AVISO_DESVIO]


def test_el_mas_grave_se_adelanta():
    i = ins.InstructorEnVivo()
    i.recibir([AVISO_VERTICAL], 0.0)
    assert i.recibir([aviso_quemado(30)], 0.2) == []  # ni el urgente antes de INTERVALO_URGENTE
    salen = i.recibir([], 0.6)
    assert [a.texto for a in salen] == [aviso_quemado(30)] and salen[0].a_dict()["prioridad"] == "alta"


def test_entre_varios_gana_el_mas_grave_y_los_viejos_caducan():
    i = ins.InstructorEnVivo()
    salen = i.recibir([AVISO_VERTICAL, AVISO_GATILLO, AVISO_DESVIO], 0.0)
    assert [a.texto for a in salen] == [AVISO_GATILLO]
    i.recibir([AVISO_VERTICAL], 0.1)
    assert i.recibir([], 0.1 + ins.CADUCIDAD_AVISO + 0.1) == []  # caducado: ya no sirve


# --- valoración por reglas ---------------------------------------------------------------------------------------
def _frases(texto):
    return [f for f in texto.replace(":", ".").split(". ") if f.strip()]


def test_reglas_con_hueco(con_hueco):
    texto = ins.valoracion_por_reglas(con_hueco)
    assert "40 mm a 55 mm" in texto and "gatillo" in texto
    assert texto.count(".") == 2  # dos frases
    assert f"{con_hueco.nota:.1f}".replace(".", ",") in texto


def test_reglas_perfecta(perfecta):
    texto = ins.valoracion_por_reglas(perfecta)
    assert "completo" in texto and texto.count(".") == 2


def test_reglas_sin_soldar():
    r = evaluar_pasada([], "recta")
    assert "gatillo" in ins.valoracion_por_reglas(r)


def test_resumen_para_llm(con_hueco):
    d = ins.resumen_para_llm(con_hueco)
    assert d["huecos_mm"] == [[40, 55]] and "tramos" not in d and d["union"] == "a tope recta"


# --- valoración con LLM (cliente simulado) -----------------------------------------------------------------------
class ClienteFalso:
    """Imita `AsyncAnthropic().beta.messages.create`."""

    def __init__(self, texto="Buen pulso, chaval. Ahora no sueltes el gatillo.", espera=0.0, error=None,
                 stop_reason="end_turn"):
        self.llamadas = []
        self.texto, self.espera, self.error, self.stop_reason = texto, espera, error, stop_reason
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._crear))

    async def _crear(self, **kwargs):
        self.llamadas.append(kwargs)
        await asyncio.sleep(self.espera)
        if self.error:
            raise self.error
        bloques = [SimpleNamespace(type="thinking", thinking=""), SimpleNamespace(type="text", text=self.texto)]
        return SimpleNamespace(content=bloques, stop_reason=self.stop_reason)


@pytest.mark.asyncio
async def test_sin_cliente_usa_reglas(con_hueco):
    v = await ins.valorar(con_hueco, None)
    assert v["origen"] == "reglas" and v["texto"] == ins.valoracion_por_reglas(con_hueco)


@pytest.mark.asyncio
async def test_con_llm(con_hueco):
    cliente = ClienteFalso()
    v = await ins.valorar(con_hueco, cliente, modelo="claude-opus-5-5")
    assert v == {"texto": "Buen pulso, chaval. Ahora no sueltes el gatillo.", "origen": "llm",
                 "modelo": "claude-opus-5-5"}
    peticion = cliente.llamadas[0]
    assert peticion["model"] == "claude-opus-5-5"
    assert peticion["output_config"] == {"effort": "low"}
    assert peticion["system"] == ins.SISTEMA_INSTRUCTOR
    assert "40, 55" in peticion["messages"][0]["content"]
    assert peticion["fallbacks"] == "default"


@pytest.mark.asyncio
async def test_llm_lento_se_corta_y_usa_reglas(con_hueco):
    inicio = time.monotonic()
    v = await ins.valorar(con_hueco, ClienteFalso(espera=10.0), tiempo_max=0.2)
    assert v["origen"] == "reglas" and time.monotonic() - inicio < 1.0


@pytest.mark.asyncio
@pytest.mark.parametrize("cliente", [
    ClienteFalso(error=ConnectionError("sin red")),
    ClienteFalso(stop_reason="refusal", texto=""),
    ClienteFalso(texto="   "),
])
async def test_fallos_del_llm_usan_reglas(con_hueco, cliente):
    v = await ins.valorar(con_hueco, cliente)
    assert v["origen"] == "reglas"


@pytest.mark.asyncio
async def test_pasada_vacia_no_llama_al_llm():
    cliente = ClienteFalso()
    v = await ins.valorar(evaluar_pasada([], "recta"), cliente)
    assert v["origen"] == "reglas" and cliente.llamadas == []


def test_crear_cliente_sin_red_no_falla(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    ins.crear_cliente_llm()  # devuelve un cliente o None, pero nunca lanza
