"""Voz → orden: lo que dice el juez, traducido a una orden del vocabulario cerrado del robot (`contrato.ORDENES`).

    interpretar_por_reglas(texto, contexto) -> Interpretacion          # sin red, al instante
    await interpretar(texto, contexto, cliente=..., alternativas=...)  # reglas y, si dudan, LLM con tiempo máximo

Dos capas, como el instructor:

- **Reglas (sin red, siempre).** Palabras clave y sinónimos de taller ("pon la T", "hazme una ele", "recoge",
  "dame el soplete", "¿dónde se suelda?"), tolerantes a los errores típicos del reconocimiento de voz ("es quina",
  "des monta", "zelda", "té", "tea"). Cada frase da una puntuación por orden; la confianza es la de la mejor. Si
  dos órdenes empatan (o se pide montar sin decir cuál) no se adivina: se devuelve una pregunta corta de
  aclaración ("¿T o esquina?").
- **LLM (solo si las reglas no están seguras).** Si la confianza de las reglas no llega a `UMBRAL_REGLAS` y hay
  cliente, se pide al LLM una salida estructurada con la orden restringida al vocabulario (enum), la confianza y
  una aclaración opcional, con un tiempo máximo de `TIEMPO_MAX_VOZ`. Si tarda, falla, se niega o devuelve algo
  fuera del vocabulario, se queda lo de las reglas.

Después, el **contexto** (`Contexto`: junta montada, robot ocupado, nivel de la escalera de alcance) decide si la
orden se puede hacer ahora; si no, la orden se devuelve igual (para que la tablet sepa qué se ha entendido) con
`permitida=False`, el `motivo` y una `respuesta` del personaje que lo explica. Ninguna orden se ejecuta sin el
toque de confirmación en la tablet: `confirmable` dice si se enseña la tarjeta con `pregunta`.

Modelo: el mismo que el instructor (`claude-opus-5-5`) con esfuerzo `low`, que para clasificar una frase en siete
órdenes basta y responde antes. Se puede cambiar con `LEWELDER_MODELO_VOZ` (p. ej. `claude-haiku-5-5` si en la
wifi del evento no llega en 2 s). Las reglas resuelven casi todo, así que el LLM solo se llama en las frases raras.

`POST /api/voz` (`api_voz`): `{"texto", "alternativas"?: [..], "contexto"?: {..}}` → la interpretación en JSON
más `personaje {nombre, voz}` para que la tablet hable con su voz.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import unicodedata
from dataclasses import dataclass, field, fields, replace

from lewelder.contrato import ORDENES, TipoJunta, orden_montar
from lewelder.instructor import MODELO_LLM
from lewelder.personaje import Personaje

log = logging.getLogger(__name__)

MODELO_VOZ = os.environ.get("LEWELDER_MODELO_VOZ", MODELO_LLM)
TIEMPO_MAX_VOZ = 2.0  # s
MAX_TOKENS_VOZ = 1024  # un JSON corto + el poco razonamiento del esfuerzo bajo
UMBRAL_REGLAS = 0.8  # con esta confianza o más, las reglas deciden solas
MARGEN_EMPATE = 0.1  # dos órdenes más cerca que esto → se pregunta
MAX_TEXTO = 300  # caracteres
MAX_ALTERNATIVAS = 5
NINGUNA = "ninguna"  # valor del enum del LLM para "no es ninguna orden"

MONTA_T = orden_montar(TipoJunta.T)
MONTA_ESQUINA = orden_montar(TipoJunta.ESQUINA)
SENALA = "señala el cordón"
SUELDA = "coge la antorcha y suelda la junta"
DESMONTA = "desmonta la junta"
ACERCA = "acércame la antorcha"
GIRA = "gira la junta hacia ti"
assert {MONTA_T, MONTA_ESQUINA, SENALA, SUELDA, DESMONTA, ACERCA, GIRA} == set(ORDENES)

# Tarjeta de confirmación de la tablet.
PREGUNTAS = {
    MONTA_T: "¿Monto una unión en T?",
    MONTA_ESQUINA: "¿Monto una unión en esquina?",
    SENALA: "¿Te señalo el cordón?",
    SUELDA: "¿Cojo la antorcha y sueldo la junta?",
    DESMONTA: "¿Desmonto la junta?",
    ACERCA: "¿Te acerco la antorcha?",
    GIRA: "¿Giro la junta hacia mí?",
}
# Para las preguntas de aclaración entre dos órdenes.
CORTO = {
    MONTA_T: "monto la T", MONTA_ESQUINA: "monto la esquina", SENALA: "señalo el cordón",
    SUELDA: "sueldo la junta", DESMONTA: "desmonto la junta", ACERCA: "te acerco la antorcha",
    GIRA: "giro la junta",
}
# Botones de la tablet (aclaración y respaldo sin voz).
ETIQUETAS = {
    MONTA_T: "T", MONTA_ESQUINA: "Esquina", SENALA: "Señalar", SUELDA: "Soldar", DESMONTA: "Desmontar",
    ACERCA: "Antorcha", GIRA: "Girar",
}
ACLARAR_JUNTA = "¿T o esquina?"
JUNTA_DE_ORDEN = {MONTA_T: TipoJunta.T, MONTA_ESQUINA: TipoJunta.ESQUINA}
_MONTAR_SIN_JUNTA = "montar"  # candidata interna: "monta" sin decir cuál


# --- contexto ----------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Contexto:
    """Lo que hace falta saber del taller para decidir si una orden se puede hacer ahora.

    `junta_montada`: `TipoJunta`, "incompleta" (montaje fallido) o None (base vacía). Con `sabe_junta=False` (el
    servidor todavía no sigue la junta) no se restringe nada por la junta. `nivel_max`: nivel más alto de la
    escalera de alcance que el robot tiene disponible (`ORDENES[orden]`).
    """

    junta_montada: TipoJunta | str | None = None
    robot_ocupado: bool = False
    nivel_max: int = 3
    sabe_junta: bool = True

    @staticmethod
    def _junta(valor) -> TipoJunta | str | None:
        if valor == "incompleta":
            return "incompleta"
        try:
            return TipoJunta(valor) if valor is not None else None
        except ValueError:
            return None

    def __post_init__(self):
        object.__setattr__(self, "junta_montada", self._junta(self.junta_montada))

    @classmethod
    def de_dict(cls, d: dict | None, base: Contexto | None = None) -> Contexto:
        """Contexto desde JSON; los campos que no vienen se toman de `base` (o los de por defecto)."""
        ctx = base if base is not None else cls()
        if not isinstance(d, dict):
            return ctx
        cambios = {}
        if "junta_montada" in d:
            cambios["junta_montada"] = cls._junta(d["junta_montada"])
            cambios["sabe_junta"] = True
        if "robot_ocupado" in d:
            cambios["robot_ocupado"] = bool(d["robot_ocupado"])
        if "nivel_max" in d:
            try:
                cambios["nivel_max"] = int(d["nivel_max"])
            except (TypeError, ValueError):
                pass
        if "sabe_junta" in d:
            cambios["sabe_junta"] = bool(d["sabe_junta"])
        return replace(ctx, **cambios)


def contexto_de_escuela(escuela) -> Contexto:
    """Lo que el servidor sabe del taller. La `Escuela` v1 no sigue la junta: hasta la tarea 6 no se restringe."""
    return Contexto(junta_montada=getattr(escuela, "junta_montada", None),
                    robot_ocupado=bool(getattr(escuela, "robot_ocupado", False)),
                    nivel_max=int(getattr(escuela, "nivel_robot", 3)),
                    sabe_junta=hasattr(escuela, "junta_montada"))


def comprobar(orden: str, ctx: Contexto) -> str | None:
    """Motivo por el que la orden no se puede hacer ahora (un evento del personaje), o None si se puede."""
    if ctx.robot_ocupado:
        return "ocupado"
    if ORDENES[orden] > ctx.nivel_max:
        return "no_aprendido"
    if not ctx.sabe_junta or orden == ACERCA:
        return None
    junta = ctx.junta_montada
    if orden in JUNTA_DE_ORDEN:
        if junta is None:
            return None
        if junta == "incompleta":
            return "junta_incompleta"
        return "ya_montada" if junta == JUNTA_DE_ORDEN[orden] else "otra_montada"
    if junta is None:
        return "sin_junta"
    if junta == "incompleta" and orden != DESMONTA:
        return "junta_incompleta"
    return None


# --- interpretación ----------------------------------------------------------------------------------------------
@dataclass
class Interpretacion:
    texto: str
    orden: str | None  # del vocabulario, o None si no se ha entendido o es ambigua
    confianza: float  # 0-1
    origen: str  # "reglas" | "llm"
    aclaracion: str | None = None  # pregunta corta si es ambigua ("¿T o esquina?")
    opciones: list[str] = field(default_factory=list)  # órdenes entre las que se duda
    permitida: bool = True  # el contexto deja hacerla ahora
    motivo: str | None = None  # evento del personaje: no_entendido, aclarar, sin_junta, ocupado...
    respuesta: str = ""  # lo que dice el robot (frase del personaje)
    modelo: str | None = None

    @property
    def pregunta(self) -> str | None:
        return PREGUNTAS.get(self.orden) if self.orden else None

    @property
    def confirmable(self) -> bool:
        """Se enseña la tarjeta "¿Monto…?" con Sí / No."""
        return self.orden is not None and self.permitida and self.aclaracion is None

    def a_dict(self) -> dict:
        d = {f.name: getattr(self, f.name) for f in fields(self)}
        d["confianza"] = round(self.confianza, 2)
        d.update(pregunta=self.pregunta, confirmable=self.confirmable, nivel=ORDENES.get(self.orden),
                 # botones de la aclaración: tocar uno lleva a su tarjeta de confirmación
                 botones=[{"orden": o, "etiqueta": ETIQUETAS[o], "pregunta": PREGUNTAS[o]} for o in self.opciones])
        return d


def normalizar(texto: str) -> str:
    """Minúsculas, sin tildes ni signos, y arreglos de lo que suele transcribir mal el reconocimiento de voz."""
    t = unicodedata.normalize("NFD", (texto or "").lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    t = re.sub(r"[^a-z0-9]+", " ", t)
    t = f" {' '.join(t.split())} "
    for patron, cambio in _ARREGLOS:
        t = re.sub(patron, cambio, t)
    return " ".join(t.split())


_ARTICULO = r"(una|un|la|el|en|de|letra|forma de|tipo)"
_ARREGLOS = [
    (r"\bes quin", "esquin"),
    (r"\bdes mont", "desmont"),
    (r"\bmon ta", "monta"),
    (r"\bsenal a\b", "senala"),
    (r"\b(zelda|selda|suelda)\b", "suelda"),
    (r"\b(hasme|has me|as me|azme)\b", "hazme"),
    (r"\b(tea|tee|teh)\b", "t"),
    (rf"\b{_ARTICULO} te\b", r"\1 t"),  # "pon la té" → T; "te monto…" (pronombre) se queda
    (rf"\b{_ARTICULO} (ele|elle)\b", r"\1 l"),
    # "no la T, la esquina": lo negado no cuenta
    (r"\bno (?:(?:la|el|una|un|en) )?(?:t|l|esquin\w*)\b", " "),
]

_T = re.compile(r"\bt\b")
_ESQUINA_FUERTE = re.compile(r"\b(esquin\w*|l|escuadra|rincon|(?:en|de) angulo)\b")
_ESQUINA_DEBIL = re.compile(r"\bangulo\b")
_VERBO_MONTAR = re.compile(
    r"\b(mont\w*|pon|ponme|ponla|ponle|pongas|coloc\w*|arm\w*|prepar\w*|haz|hazme|hazla|constru\w*|quiero|dame|"
    r"ensambl\w*)\b")
_HERRAMIENTA = re.compile(r"\b(antorcha|soplete|pistola)\b")
_DAR = re.compile(r"\b(dam\w*|pas\w*|trae\w*|traig\w*|acerc\w*|alcanz\w*|quiero|necesito)\b")
# (orden, patrón, peso): el peso es la confianza que da ese indicio.
_INDICIOS = [
    (DESMONTA, re.compile(r"\b(desmont\w*|quit\w*|recog\w*|retir\w*|deshaz\w*|desarm\w*|separ\w*|despej\w*|"
                          r"limpia la mesa)\b"), 1.0),
    (SENALA, re.compile(r"\b(senal\w*|apunt\w*|indic\w*)\b"), 1.0),
    (SENALA, re.compile(r"\bdonde\b.*\b(suel\w*|sold\w*|cordon|va|tengo|hay que|pongo)\b"), 1.2),
    (SENALA, re.compile(r"\bcordon\b"), 0.6),
    (SUELDA, re.compile(r"\b(suelda\w*|sueld\w*|sold\w*|demuestr\w*|ensen\w*)\b"), 1.0),
    (SUELDA, re.compile(r"\b(hazlo tu|como se suelda|como se hace|como lo haces|mira y aprende|muestrame como)\b"),
     1.0),
    (GIRA, re.compile(r"\b(gir\w*|rot\w*|volte\w*|vuelta)\b"), 1.0),
    (GIRA, re.compile(r"\bhacia (ti|mi|aqui|alli)\b"), 0.6),
]


@dataclass
class _Lectura:
    """Resultado de las reglas antes de aplicar el contexto."""

    texto: str
    orden: str | None
    confianza: float
    aclaracion: str | None = None
    opciones: list[str] = field(default_factory=list)


def _puntuar(t: str) -> dict[str, float]:
    puntos: dict[str, float] = {}

    def anotar(orden, peso):
        puntos[orden] = max(puntos.get(orden, 0.0), peso)

    for orden, patron, peso in _INDICIOS:
        if patron.search(t):
            anotar(orden, peso)
    if _HERRAMIENTA.search(t):
        if _DAR.search(t):
            anotar(ACERCA, 1.1)
        elif SUELDA not in puntos:
            anotar(ACERCA, 0.6)
    verbo = bool(_VERBO_MONTAR.search(t))
    t_dicha = bool(_T.search(t))
    esquina = 0.85 if _ESQUINA_FUERTE.search(t) else (0.6 if _ESQUINA_DEBIL.search(t) else 0.0)
    if t_dicha:
        anotar(MONTA_T, 1.0 if verbo else 0.85)
    if esquina:
        anotar(MONTA_ESQUINA, 1.0 if verbo and esquina > 0.6 else esquina)
    if verbo and not t_dicha and not esquina:
        anotar(_MONTAR_SIN_JUNTA, 0.5)
    return puntos


def _aclaracion(a: str, b: str) -> str:
    if {a, b} == {MONTA_T, MONTA_ESQUINA}:
        return ACLARAR_JUNTA
    texto = f"{CORTO[a]} o {CORTO[b]}"
    return f"¿{texto[0].upper()}{texto[1:]}?"


def _leer(texto: str) -> _Lectura:
    puntos = _puntuar(normalizar(texto))
    if not puntos:
        return _Lectura(texto, None, 0.0)
    orden_puntos = sorted(puntos.items(), key=lambda kv: -kv[1])
    mejor, p1 = orden_puntos[0]
    if mejor == _MONTAR_SIN_JUNTA:
        return _Lectura(texto, None, 0.5, ACLARAR_JUNTA, [MONTA_T, MONTA_ESQUINA])
    if len(orden_puntos) > 1:
        segunda, p2 = orden_puntos[1]
        if segunda != _MONTAR_SIN_JUNTA and p1 - p2 < MARGEN_EMPATE:
            return _Lectura(texto, None, 0.5, _aclaracion(mejor, segunda), [mejor, segunda])
    return _Lectura(texto, mejor, min(p1, 0.95))


def _mejor_lectura(textos: list[str]) -> _Lectura:
    lecturas = [_leer(t) for t in textos] or [_leer("")]
    return max(lecturas, key=lambda l: l.confianza)  # en empate, la primera (la que más cree el reconocedor)


_PERSONAJE = Personaje()


def _terminar(lectura: _Lectura, ctx: Contexto, origen: str, personaje: Personaje,
              modelo: str | None = None) -> Interpretacion:
    r = Interpretacion(lectura.texto, lectura.orden, lectura.confianza, origen, lectura.aclaracion,
                       list(lectura.opciones), modelo=modelo)
    if r.orden is None:
        r.motivo = "aclarar" if r.aclaracion else "no_entendido"
        r.respuesta = personaje.frase(r.motivo, pregunta=r.aclaracion or "")
        return r
    r.motivo = comprobar(r.orden, ctx)
    r.permitida = r.motivo is None
    if r.permitida:
        r.respuesta = personaje.frase("confirmar", junta=JUNTA_DE_ORDEN.get(r.orden))
    else:
        junta = ctx.junta_montada if r.motivo in ("ya_montada", "otra_montada") else None
        r.respuesta = personaje.frase(r.motivo, junta=junta)
    return r


def interpretar_por_reglas(texto: str, contexto: Contexto | None = None, *,
                           personaje: Personaje | None = None) -> Interpretacion:
    """Solo reglas: sin red y al instante."""
    return _terminar(_leer(texto or ""), contexto or Contexto(), "reglas", personaje or _PERSONAJE)


# --- LLM ---------------------------------------------------------------------------------------------------------
ESQUEMA_VOZ = {
    "type": "object",
    "properties": {
        "orden": {"type": "string", "enum": [*ORDENES, NINGUNA]},
        "confianza": {"type": "number"},
        "aclaracion": {"type": "string"},
    },
    "required": ["orden", "confianza", "aclaracion"],
    "additionalProperties": False,
}

SISTEMA_VOZ = (
    "Eres el oído del robot de LeWelder, una máquina arcade de escuela de soldadura. Un juez le habla al robot y "
    "un reconocedor de voz transcribe lo que dice, a veces con errores (palabras partidas, letras que suenan "
    "parecido). Tu trabajo es traducir esa frase a UNA orden de este vocabulario cerrado, o a \"ninguna\":\n"
    "- \"monta una unión en T\": montar la junta en T (el juez puede decir T, té, la te...).\n"
    "- \"monta una unión en esquina\": montar la junta en esquina (esquina, ele, L, en ángulo, escuadra...).\n"
    "- \"señala el cordón\": señalar dónde va el cordón o dónde se suelda.\n"
    "- \"coge la antorcha y suelda la junta\": que el robot suelde o demuestre cómo se suelda.\n"
    "- \"desmonta la junta\": desmontar, quitar o recoger la junta.\n"
    "- \"acércame la antorcha\": darle o acercarle la antorcha al juez.\n"
    "- \"gira la junta hacia ti\": girar la junta hacia el robot.\n"
    "Responde con el JSON pedido: \"orden\" (una del vocabulario o \"ninguna\"), \"confianza\" entre 0 y 1, y "
    "\"aclaracion\": si la frase pide algo del vocabulario pero no se sabe cuál de dos órdenes, pon \"ninguna\" y "
    "una pregunta muy corta en español para el juez (por ejemplo \"¿T o esquina?\"); si no, cadena vacía. Si la "
    "frase no tiene nada que ver con el robot, \"ninguna\" y aclaración vacía. No inventes órdenes."
)


def _validar_llm(datos) -> tuple[str | None, float, str | None]:
    if not isinstance(datos, dict):
        raise ValueError("no es un objeto")
    orden, confianza, aclaracion = datos.get("orden"), datos.get("confianza"), datos.get("aclaracion")
    if orden != NINGUNA and orden not in ORDENES:
        raise ValueError(f"orden fuera del vocabulario: {orden!r}")
    if isinstance(confianza, bool) or not isinstance(confianza, (int, float)):
        raise ValueError("confianza no numérica")
    if not isinstance(aclaracion, str):
        raise ValueError("aclaración no es texto")
    aclaracion = " ".join(aclaracion.split())[:80] or None
    return (None if orden == NINGUNA else orden), max(0.0, min(1.0, float(confianza))), aclaracion


async def _pedir_llm(cliente, texto: str, alternativas: list[str], modelo: str):
    entrada = {"frase": texto}
    if alternativas:
        entrada["otras_transcripciones"] = alternativas
    respuesta = await cliente.beta.messages.create(
        model=modelo,
        max_tokens=MAX_TOKENS_VOZ,
        system=SISTEMA_VOZ,
        output_config={"effort": "low", "format": {"type": "json_schema", "schema": ESQUEMA_VOZ}},
        # Si el modelo se niega, el servidor reintenta con otro en la misma llamada; si toda la cadena se niega,
        # stop_reason == "refusal" y se quedan las reglas.
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        messages=[{"role": "user", "content": json.dumps(entrada, ensure_ascii=False)}],
    )
    if getattr(respuesta, "stop_reason", None) == "refusal":
        raise ValueError("el LLM se ha negado")
    texto_json = "".join(b.text for b in respuesta.content if getattr(b, "type", None) == "text")
    return _validar_llm(json.loads(texto_json))


async def interpretar(texto: str, contexto: Contexto | None = None, *, cliente=None, modelo: str = MODELO_VOZ,
                      tiempo_max: float = TIEMPO_MAX_VOZ, personaje: Personaje | None = None,
                      alternativas=()) -> Interpretacion:
    """Reglas sobre la transcripción y sus alternativas; LLM solo si las reglas no llegan a `UMBRAL_REGLAS`.
    Nunca lanza excepciones ni tarda más de `tiempo_max` (más lo que tarde en cancelarse la petición)."""
    ctx = contexto or Contexto()
    personaje = personaje or _PERSONAJE
    textos = [t for t in [texto, *alternativas] if isinstance(t, str) and t.strip()][:1 + MAX_ALTERNATIVAS]
    lectura = _mejor_lectura(textos)
    if not textos:
        lectura.texto = texto or ""
    if lectura.confianza >= UMBRAL_REGLAS or cliente is None or not textos:
        return _terminar(lectura, ctx, "reglas", personaje)
    try:
        orden, confianza, aclaracion = await asyncio.wait_for(
            _pedir_llm(cliente, textos[0], textos[1:], modelo), timeout=tiempo_max)
    except asyncio.TimeoutError:
        log.info("el LLM no ha contestado en %.1f s: interpretación por reglas", tiempo_max)
        return _terminar(lectura, ctx, "reglas", personaje)
    except Exception as e:  # red, credenciales, JSON inválido, fuera del vocabulario... la demo sigue
        log.info("LLM no válido (%s): interpretación por reglas", type(e).__name__)
        return _terminar(lectura, ctx, "reglas", personaje)
    if orden is None and aclaracion is None and lectura.aclaracion:
        return _terminar(lectura, ctx, "reglas", personaje)  # las reglas al menos saben qué preguntar
    if orden is not None:
        aclaracion = None
    if orden is None:
        confianza = 0.5 if aclaracion else 0.0
    opciones = list(lectura.opciones) if aclaracion else []
    llm = _Lectura(textos[0], orden, confianza, aclaracion, opciones)
    return _terminar(llm, ctx, "llm", personaje, modelo=modelo)


# --- endpoint HTTP -----------------------------------------------------------------------------------------------
async def api_voz(request):
    """`POST /api/voz`: `{"texto", "alternativas"?, "contexto"?}` → interpretación + personaje. El contexto de la
    petición completa (y manda sobre) lo que sabe el servidor."""
    from aiohttp import web

    try:
        datos = await request.json()
    except (ValueError, UnicodeDecodeError):
        return web.json_response({"error": "el cuerpo no es JSON"}, status=400)
    if not isinstance(datos, dict) or not isinstance(datos.get("texto"), str):
        return web.json_response({"error": "falta el texto"}, status=400)
    texto = datos["texto"]
    if len(texto) > MAX_TEXTO:
        return web.json_response({"error": "texto demasiado largo"}, status=400)
    alternativas = datos.get("alternativas") or []
    if not isinstance(alternativas, list):
        alternativas = []
    alternativas = [a for a in alternativas if isinstance(a, str) and len(a) <= MAX_TEXTO][:MAX_ALTERNATIVAS]
    escuela = request.app["escuela"]
    ctx = Contexto.de_dict(datos.get("contexto"), base=contexto_de_escuela(escuela))
    r = await interpretar(texto, ctx, cliente=getattr(escuela, "cliente_llm", None), alternativas=alternativas)
    return web.json_response({**r.a_dict(), "personaje": _PERSONAJE.info()})
