"""Personaje del robot: banco de frases por evento, sin repetir seguidas, cortas, y variación opcional con LLM."""
import asyncio
import re
import time
from types import SimpleNamespace

import pytest

from lewelder import personaje as p
from lewelder.contrato import TipoJunta
from lewelder.personaje import EVENTOS, FRASES, NOMBRE, VOZ, Personaje

EVENTOS_OBLIGATORIOS = {
    "atraccion", "confirmar", "montado", "montaje_fallido", "girar_pieza", "demostrar", "reto", "juez_gana",
    "robot_gana", "record", "no_entendido", "aclarar", "sin_junta", "ocupado",
}
PALABROTAS = {"mierda", "joder", "coño", "hostia", "cabrón", "puta", "gilipollas", "idiota", "imbécil", "tonto"}
DATOS = [{}, {"junta": TipoJunta.T}, {"junta": "esquina", "puntos": 1234, "diferencia": 56}, {"junta": None}]


def _frases_del_texto(texto: str) -> list[str]:
    return [t for t in re.split(r"(?<=[.!?…])\s+(?=[¡¿A-ZÁÉÍÓÚÑ])", texto.strip()) if t]


def test_nombre_y_voz():
    assert NOMBRE == "Chispas"
    assert VOZ["lang"] == "es-ES" and 0.5 <= VOZ["rate"] <= 2 and 0 <= VOZ["pitch"] <= 2


def test_todos_los_eventos_tienen_varias_frases():
    assert EVENTOS_OBLIGATORIOS <= set(EVENTOS)
    assert set(EVENTOS) == set(FRASES)
    for evento in EVENTOS:
        assert len(FRASES[evento]) >= 3, evento


@pytest.mark.parametrize("evento", sorted(FRASES))
def test_frases_cortas_una_frase_y_limpias(evento):
    for datos in DATOS:
        for frase in Personaje().banco(evento, **datos):
            assert "{" not in frase and "}" not in frase, frase
            assert 3 <= len(frase) <= p.MAX_CARACTERES, frase
            assert len(_frases_del_texto(frase)) == 1, frase
            palabras = set(re.findall(r"\w+", frase.lower()))
            assert not palabras & PALABROTAS, frase


def test_no_repite_seguidas():
    pj = Personaje(semilla=1)
    for evento in EVENTOS:
        anterior = None
        for _ in range(40):
            frase = pj.frase(evento, junta="esquina")
            assert frase != anterior, (evento, frase)
            anterior = frase


def test_recorre_el_banco():
    pj = Personaje(semilla=3)
    vistas = {pj.frase("montado", junta="t") for _ in range(200)}
    assert vistas == set(pj.banco("montado", junta="t"))


def test_montado_nombra_la_junta():
    pj = Personaje(semilla=0)
    assert all("esquina" in f.lower() for f in pj.banco("montado", junta=TipoJunta.ESQUINA))
    assert all(re.search(r"\bT\b", f) for f in pj.banco("montado", junta=TipoJunta.T))
    assert "¡Esquina servida!" in pj.banco("montado", junta="esquina")


def test_evento_desconocido():
    with pytest.raises(KeyError):
        Personaje().frase("bailar")


def test_reacciones_a_la_puntuacion():
    pj = Personaje(semilla=0)
    # (puntos del juez, puntos del robot, récord del día)
    assert pj.reaccion_puntuacion(1000, 900) == "juez_gana"
    assert pj.reaccion_puntuacion(800, 900) == "robot_gana"
    assert pj.reaccion_puntuacion(1000, 900, record=950) == "record"
    assert pj.reaccion_puntuacion(1000, 900, record=1200) == "juez_gana"
    assert pj.reaccion_puntuacion(900, 900) == "juez_gana"  # en empate gana el juez, que el robot es caballero
    assert pj.reaccion_puntuacion(900, None) == "juez_gana"  # sin fantasma del robot no hay con quién comparar


# --- variación con LLM ---------------------------------------------------------------------------------------
class ClienteFalso:
    def __init__(self, texto="¡Esquina servida y sin una rebaba!", espera=0.0, error=None, stop_reason="end_turn"):
        self.llamadas = []
        self.texto, self.espera, self.error, self.stop_reason = texto, espera, error, stop_reason
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._crear))

    async def _crear(self, **kwargs):
        self.llamadas.append(kwargs)
        await asyncio.sleep(self.espera)
        if self.error:
            raise self.error
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=self.texto)], stop_reason=self.stop_reason)


@pytest.mark.asyncio
async def test_frase_llm_valida():
    cliente = ClienteFalso()
    r = await Personaje(semilla=0).frase_variada("montado", cliente, modelo="claude-opus-5-5", junta="esquina")
    assert r == {"texto": "¡Esquina servida y sin una rebaba!", "origen": "llm", "modelo": "claude-opus-5-5",
                 "evento": "montado"}
    peticion = cliente.llamadas[0]
    assert peticion["system"] == p.SISTEMA_PERSONAJE and NOMBRE in p.SISTEMA_PERSONAJE
    assert peticion["output_config"] == {"effort": "low"}
    assert "montado" in peticion["messages"][0]["content"]


@pytest.mark.asyncio
@pytest.mark.parametrize("cliente", [
    ClienteFalso(texto="Una frase. Y otra frase más que sobra."),
    ClienteFalso(texto="x" * 200),
    ClienteFalso(texto="  "),
    ClienteFalso(texto="Eres un idiota."),
    ClienteFalso(stop_reason="refusal", texto=""),
    ClienteFalso(error=ConnectionError("sin red")),
])
async def test_frase_llm_invalida_usa_banco(cliente):
    pj = Personaje(semilla=0)
    r = await pj.frase_variada("reto", cliente)
    assert r["origen"] == "banco" and r["texto"] in pj.banco("reto")


@pytest.mark.asyncio
async def test_frase_llm_lenta_se_corta():
    inicio = time.monotonic()
    r = await Personaje().frase_variada("record", ClienteFalso(espera=10.0), tiempo_max=0.2)
    assert r["origen"] == "banco" and time.monotonic() - inicio < 1.0


@pytest.mark.asyncio
async def test_sin_cliente_usa_banco():
    r = await Personaje().frase_variada("atraccion", None)
    assert r["origen"] == "banco" and r["modelo"] is None
