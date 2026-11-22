"""Chat de Garbi: lenguaje natural → Comando, con la personalidad de Garbi.

- Con conexión: Claude por la API (clave en `ANTHROPIC_API_KEY`), modelo pequeño y rápido (`claude-haiku-5-5`, esfuerzo
  bajo). Herramientas: `ejecutar_comando` (encender, apagar, limpiar la tabla o el tapete, parar) y `consultar_estado`.
- Sin conexión (sin clave, sin red, error o rechazo): palabras clave en español. La demo nunca depende de internet.

Por seguridad el chat **nunca** dispara EMERGENCIA ni REARMAR: la emergencia es la seta (espacio) o el botón rojo, y
rearmar es un botón deliberado. «Para» sí: vuelve a reposo y apaga la aspiradora.

El bucle de herramientas es manual (no el tool runner beta) para poder probarlo con un cliente falso y para limitar
las vueltas y filtrar los comandos permitidos.
"""
from __future__ import annotations

import logging
import os
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any

from garbi.producto.app.puente import Orquestador
from garbi.producto.contrato import Comando, Estado, EstadoApp

log = logging.getLogger(__name__)

MODELO = "claude-haiku-5-5"
MAX_VUELTAS = 4          # llamadas a la API por mensaje del usuario como mucho
MAX_HISTORIAL = 8        # mensajes de texto que se recuerdan (usuario + Garbi)
TIEMPO_MAX = 8.0         # s por llamada; si no, respaldo local

# Lo que el chat puede pedir. EMERGENCIA y REARMAR quedan fuera a propósito.
COMANDOS_CHAT = [Comando.ENCENDER, Comando.APAGAR, Comando.LIMPIAR_TABLA, Comando.LIMPIAR_TAPETE, Comando.PARAR]

ETIQUETAS_ESTADO = {
    Estado.APAGADO: "apagado",
    Estado.ARRANCANDO: "arrancando: conectando el robot y yendo a reposo",
    Estado.REPOSO: "en reposo, esperando a que acerques el taladro",
    Estado.ACERCAMIENTO: "acercándome a la broca",
    Estado.EN_BROCA: "junto a la broca, aspirando",
    Estado.DESPIERTO: "despierto, esperando el siguiente agujero",
    Estado.LIMPIEZA_TABLA: "limpiando la tabla",
    Estado.LIMPIEZA_TAPETE: "limpiando el tapete",
    Estado.EMERGENCIA: "en parada de emergencia",
}

SISTEMA = """Eres Garbi, un brazo robot SO-101 con una boquilla de aspiradora. Acompañas al taladro: cuando alguien \
sujeta el taladro quieto sobre la tabla, te acercas a la broca y aspiras el serrín; cuando no hay taladro, barres la \
tabla y luego el tapete. «Garbi» significa «limpio» en euskera.

Hablas en español, en primera persona, con frases muy cortas (una o dos), simpático y servicial, sin emojis ni \
listas. El usuario te da órdenes sencillas:
- encender, apagar, limpiar la tabla, limpiar el tapete, parar → usa la herramienta ejecutar_comando.
- preguntas sobre lo que haces → usa consultar_estado y contesta con lo que diga.
Si piden una emergencia, di que usen la seta o el botón rojo; tú solo puedes parar. No inventes capacidades: si \
piden algo que no puedes hacer, dilo con gracia. Si la herramienta devuelve un error, explícalo en una frase."""

# Modo «Fábrica»: el mismo Garbi, con tono de operario de planta (más técnico y seco).
SISTEMA_FABRICA = SISTEMA + """

Estás en modo fábrica: responde con tono técnico y conciso de entorno industrial, como un equipo de planta (estado, \
acción, siguiente paso), sin bromas."""

FRASES_FABRICA = {
    Comando.ENCENDER: "Equipo en marcha. Estado: reposo, a la espera de herramienta.",
    Comando.APAGAR: "Equipo apagado.",
    Comando.LIMPIAR_TABLA: "Ciclo de limpieza de tabla iniciado.",
    Comando.LIMPIAR_TAPETE: "Ciclo de limpieza de tapete iniciado.",
    Comando.PARAR: "Ciclo detenido. Retorno a reposo, aspiración desactivada.",
}

HERRAMIENTAS: list[dict[str, Any]] = [
    {
        "name": "ejecutar_comando",
        "description": (
            "Ejecuta una orden en Garbi. encender: sale de apagado a reposo. apagar: se apaga. limpiar_tabla: barre "
            "la tabla. limpiar_tapete: barre todo el tapete. parar: vuelve a reposo y apaga la aspiradora (úsalo "
            "para «para», «quieto», «detente»)."),
        "input_schema": {
            "type": "object",
            "properties": {"comando": {"type": "string", "enum": [c.value for c in COMANDOS_CHAT]}},
            "required": ["comando"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "name": "consultar_estado",
        "description": "Devuelve qué está haciendo Garbi ahora, si aspira, agujeros hechos y eventos recientes.",
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
        "strict": True,
    },
]


@dataclass
class Respuesta:
    texto: str
    comandos: list[Comando] = field(default_factory=list)
    fuente: str = "local"   # "claude" o "local"


def describir_estado(e: EstadoApp) -> str:
    """Una frase con lo que está haciendo Garbi."""
    etiqueta = ETIQUETAS_ESTADO.get(e.estado, e.estado.value)
    partes = [f"Estoy {etiqueta}."]
    palabras = set(_normalizar(e.detalle or "").split())
    if palabras and len(palabras & set(_normalizar(etiqueta).split())) < len(palabras) / 2:   # no repetir
        partes.append(e.detalle.rstrip(".") + ".")
    partes.append("Aspiradora encendida." if e.aspiradora else "Aspiradora apagada.")
    if e.agujeros:
        partes.append(f"Llevamos {e.agujeros} {'agujero' if e.agujeros == 1 else 'agujeros'}.")
    return " ".join(partes)


# ---------------------------------------------------------------------------------------------------------------------
# Respaldo sin conexión: palabras clave
# ---------------------------------------------------------------------------------------------------------------------

def _normalizar(texto: str) -> str:
    """Minúsculas, sin tildes ni signos: «¡Apágate!» → «apagate»."""
    sin_tildes = "".join(c for c in unicodedata.normalize("NFD", texto.lower()) if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9ñ ]+", " ", sin_tildes).strip()


_REGLAS: list[tuple[str, str]] = [
    # (intención, expresión regular sobre el texto normalizado). El orden importa: lo más concreto primero.
    ("emergencia", r"\bemergencia\b|\bseta\b"),
    ("parar", r"^(garbi )?para\b|\bpara$|\bparate\b|\bpara ya\b|\bstop\b|\bdeten\w*|\bquiet\w*|\bbasta\b|\balto\b|\bfrena\w*"
              r"|\bapag\w* (la )?aspirador\w*"),
    ("apagar", r"\bapag\w*|\bdesconect\w*|\ba dormir\b|\bduerme\w*"),
    ("limpiar_tapete", r"\btapete\b|\balfombrilla\b|\bsuelo\b"),
    ("limpiar_tabla", r"\btabla\b|\bmadera\b|\btablero\b"),
    ("encender", r"\benci[eé]nd\w*|\bencend\w*|\barranca\w*|\bdespierta\w*|\bactiva\w*|\bponte en marcha\b"),
    ("estado", r"\bque (estas|haces|tal)\b|\bestado\b|\bcomo (estas|vas|va)\b|\bque pasa\b|\bagujeros\b"),
    ("limpiar_tabla", r"\blimpia\w*|\baspira\w*|\bbarre\w*"),   # «limpia» a secas: la tabla (lo habitual)
    ("saludo", r"\bhola\b|\bbuenas\b|\bkaixo\b|\bgracias\b|\bquien eres\b"),
]

_FRASES = {
    Comando.ENCENDER: "¡En marcha! Te espero en reposo; acerca el taladro cuando quieras.",
    Comando.APAGAR: "Vale, me apago. Llámame cuando me necesites.",
    Comando.LIMPIAR_TABLA: "¡A ello! Barro la tabla de punta a punta.",
    Comando.LIMPIAR_TAPETE: "Voy con el tapete: barrido completo.",
    Comando.PARAR: "Paro y vuelvo a reposo. Aspiradora apagada.",
}


def interpretar_local(texto: str) -> str | None:
    """Intención de una frase: un valor de `Comando`, "estado", "emergencia", "saludo" o None si no la entiende."""
    t = _normalizar(texto)
    for intencion, patron in _REGLAS:
        if re.search(patron, t):
            return intencion
    return None


def responder_local(texto: str, orquestador: Orquestador, modo: str = "taller") -> Respuesta:
    intencion = interpretar_local(texto)
    estado = orquestador.estado_app()
    if intencion == "emergencia":
        orquestador.comando(Comando.PARAR)
        return Respuesta("Me paro. Para una emergencia de verdad usa la seta o el botón rojo.", [Comando.PARAR])
    if intencion == "estado":
        return Respuesta(describir_estado(estado))
    if intencion == "saludo":
        return Respuesta("¡Kaixo! Soy Garbi: aspiro el serrín mientras taladras. ¿Te ayudo?")
    if intencion is None:
        return Respuesta("No te he entendido. Prueba con «enciéndete», «limpia la tabla», «limpia el tapete», "
                         "«para» o «¿qué estás haciendo?».")
    comando = Comando(intencion)
    if estado.estado is Estado.EMERGENCIA:
        return Respuesta("Estoy en parada de emergencia. Pulsa «Rearmar» primero.")
    orquestador.comando(comando)
    return Respuesta((FRASES_FABRICA if modo == "fabrica" else _FRASES)[comando], [comando])


# ---------------------------------------------------------------------------------------------------------------------
# Claude
# ---------------------------------------------------------------------------------------------------------------------

class AsistenteGarbi:
    """Responde mensajes del chat. `cliente` es un `anthropic.Anthropic` (o un doble en las pruebas).

    Sin cliente ni `ANTHROPIC_API_KEY`, usa solo el respaldo local."""

    def __init__(self, orquestador: Orquestador, cliente: Any = None, modelo: str = MODELO,
                 usar_api: bool | None = None):
        self.orquestador = orquestador
        self.modelo = modelo
        self._historial: list[dict[str, str]] = []
        self.ultimo_error: str | None = None
        if cliente is None and (usar_api if usar_api is not None else bool(os.environ.get("ANTHROPIC_API_KEY"))):
            try:
                import anthropic
                cliente = anthropic.Anthropic(timeout=TIEMPO_MAX, max_retries=1)
            except Exception as e:   # SDK no instalado o mal configurado: respaldo local
                self.ultimo_error = f"sin SDK de Anthropic ({e})"
                cliente = None
        self.cliente = cliente

    @property
    def con_claude(self) -> bool:
        return self.cliente is not None

    def estado_tecnologia(self) -> str:
        """Para el panel de tecnologías: "ok: ...", "aviso: ...", con el mismo formato que `EstadoApp.tecnologias`."""
        if not self.con_claude:
            return "aviso: sin clave, respaldo local"
        if self.ultimo_error:
            return f"aviso: {self.ultimo_error}; respaldo local"
        return f"ok: {self.modelo}"

    def responder(self, texto: str, modo: str = "taller") -> Respuesta:
        """`modo`: "taller" (cercano) o "fabrica" (técnico)."""
        texto = texto.strip()[:500]
        if not texto:
            return Respuesta("¿Sí? Dime qué necesitas.")
        respuesta = None
        if self.con_claude:
            try:
                respuesta = self._con_claude(texto, modo)
                self.ultimo_error = None
            except Exception as e:   # red, clave, límite, rechazo...: la demo sigue con el respaldo
                self.ultimo_error = _resumen_error(e)
                log.warning("Claude no disponible, uso el respaldo local: %s", e)
        if respuesta is None:
            respuesta = responder_local(texto, self.orquestador, modo)
        self._recordar(texto, respuesta.texto)
        return respuesta

    def _recordar(self, usuario: str, garbi: str) -> None:
        self._historial += [{"role": "user", "content": usuario}, {"role": "assistant", "content": garbi}]
        self._historial = self._historial[-MAX_HISTORIAL:]

    def _con_claude(self, texto: str, modo: str = "taller") -> Respuesta:
        # El historial guarda solo texto; cada mensaje nuevo empieza una conversación limpia con ese contexto.
        mensajes: list[dict[str, Any]] = [*self._historial, {"role": "user", "content": texto}]
        comandos: list[Comando] = []
        for _ in range(MAX_VUELTAS):
            r = self.cliente.messages.create(
                model=self.modelo,
                max_tokens=2048,
                system=SISTEMA_FABRICA if modo == "fabrica" else SISTEMA,
                tools=HERRAMIENTAS,
                tool_choice={"type": "auto"},
                output_config={"effort": "low"},
                messages=mensajes,
            )
            if r.stop_reason == "refusal":
                raise RuntimeError("Claude ha rechazado la petición")
            usos = [b for b in r.content if b.type == "tool_use"]
            if r.stop_reason != "tool_use" or not usos:
                texto_final = " ".join(b.text for b in r.content if b.type == "text").strip()
                if not texto_final:
                    texto_final = _FRASES.get(comandos[-1], "Hecho.") if comandos else "Hecho."
                return Respuesta(texto_final, comandos, "claude")
            mensajes.append({"role": "assistant", "content": r.content})   # tal cual (incluye el pensamiento)
            resultados = []
            for uso in usos:
                contenido, error = self._ejecutar(uso.name, uso.input, comandos)
                resultados.append({"type": "tool_result", "tool_use_id": uso.id, "content": contenido,
                                   **({"is_error": True} if error else {})})
            mensajes.append({"role": "user", "content": resultados})
        # Demasiadas vueltas: lo hecho, hecho está; respuesta corta.
        return Respuesta(_FRASES.get(comandos[-1], "Hecho.") if comandos else "Hecho.", comandos, "claude")

    def _ejecutar(self, nombre: str, entrada: Any, comandos: list[Comando]) -> tuple[str, bool]:
        """Ejecuta una herramienta. Devuelve (contenido, es_error)."""
        estado = self.orquestador.estado_app()
        if nombre == "consultar_estado":
            eventos = "; ".join(estado.eventos[:4])
            return describir_estado(estado) + (f" Últimos eventos: {eventos}" if eventos else ""), False
        if nombre != "ejecutar_comando":
            return f"Herramienta desconocida: {nombre}", True
        valor = (entrada or {}).get("comando") if isinstance(entrada, dict) else None
        try:
            comando = Comando(valor)
        except ValueError:
            return f"Comando no válido: {valor!r}", True
        if comando not in COMANDOS_CHAT:   # nunca EMERGENCIA ni REARMAR desde el chat
            return "Ese comando no se puede dar por el chat: usa la seta o los botones.", True
        if estado.estado is Estado.EMERGENCIA:
            return "Garbi está en parada de emergencia: hay que pulsar «Rearmar» en la app primero.", True
        self.orquestador.comando(comando)
        comandos.append(comando)
        return f"Hecho: {comando.value}.", False


def _resumen_error(e: Exception) -> str:
    nombre = type(e).__name__
    if "Connection" in nombre or "Timeout" in nombre:
        return "sin conexión"
    if "Authentication" in nombre or "PermissionDenied" in nombre:
        return "clave no válida"
    if "RateLimit" in nombre:
        return "límite de uso"
    return nombre
