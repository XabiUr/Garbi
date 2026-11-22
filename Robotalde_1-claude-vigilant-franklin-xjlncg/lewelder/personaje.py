"""El robot como personaje: Chispas, el SO-101 del taller, con voz propia y frases cortas con humor de taller.

Tono arcade (spec v2, 0.1): presume al montar, reta al juez, se pica si le ganan y es el fantasma rival a batir.
Todo en español de España, una sola frase corta por evento y apto para todos los públicos.

- **Banco de frases (reglas, sin red).** Varias por evento; `Personaje.frase(evento, **datos)` elige una al azar
  sin repetir la última de ese evento. Los datos rellenan los huecos: `junta` (`TipoJunta`, "t", "esquina" o
  None), `puntos`, `diferencia` y `pregunta`.
- **Variación con LLM (opcional).** `Personaje.frase_variada(evento, cliente)` pide al LLM una variación de la frase
  del banco con un tiempo máximo (`TIEMPO_MAX_PERSONAJE`); si no hay cliente, tarda, se niega o la frase no pasa los
  filtros (una frase, corta, sin palabras vetadas), se usa la del banco. La demo nunca espera más de eso.

La voz (`VOZ`) la usa la tablet con `speechSynthesis`: algo más rápida y aguda que la del maestro, para que suene a
robot pizpireto y no a locutor.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import random
import re

from lewelder.contrato import TipoJunta
from lewelder.instructor import MODELO_LLM

log = logging.getLogger(__name__)

NOMBRE = "Chispas"
# Parámetros de `SpeechSynthesisUtterance` en la tablet.
VOZ = {"lang": "es-ES", "rate": 1.12, "pitch": 1.35}

MODELO_PERSONAJE = os.environ.get("LEWELDER_MODELO_VOZ", MODELO_LLM)
TIEMPO_MAX_PERSONAJE = 2.0  # s
MAX_TOKENS_PERSONAJE = 512  # una frase + el poco razonamiento del esfuerzo bajo
MAX_CARACTERES = 90

# Nombres de la junta para rellenar las frases.
_NOMBRES = {
    TipoJunta.T: {"junta": "T", "Junta": "T", "la_junta": "la T", "una_junta": "una T"},
    TipoJunta.ESQUINA: {"junta": "esquina", "Junta": "Esquina", "la_junta": "la esquina",
                        "una_junta": "una esquina"},
    None: {"junta": "junta", "Junta": "Junta", "la_junta": "la junta", "una_junta": "una junta"},
}

FRASES: dict[str, list[str]] = {
    # pantalla de atracción (nadie juega)
    "atraccion": [
        "¡Soy {nombre}, el robot soldador más rápido del taller!",
        "Pulsa para jugar, si te atreves a soldar contra {nombre}.",
        "Aquí {nombre}, esperando a alguien con pulso de cirujano.",
        "Pídeme una T o una esquina y te enseño cómo se suelda.",
        "Se buscan soldadores valientes: pulsa para jugar.",
    ],
    # orden entendida, falta el toque en la tablet
    "confirmar": [
        "Toca Sí y me pongo manos a la obra.",
        "Dame el visto bueno en la pantalla y marchando.",
        "Un toque en Sí y te lo preparo en un periquete.",
        "Confírmamelo en la tablet, que no quiero liarla.",
    ],
    "cancelado": [
        "Vale, no hago nada, tú mandas.",
        "Entendido, me quedo quieto como un poste.",
        "Cancelado, dime otra cosa cuando quieras.",
    ],
    # montaje
    "montado": [
        "¡{Junta} servida!",
        "Ahí tienes {una_junta}, bien cerrada y sin holguras.",
        "Listo: {la_junta} está montada, ahora te toca a ti.",
        "¡Tachán, {la_junta} montada a la primera!",
    ],
    "montaje_fallido": [
        "Uy, se me ha resbalado la chapa, déjame intentarlo otra vez.",
        "Eso no ha encajado, hasta los robots tenemos un mal día.",
        "Vaya, los imanes no han cerrado la junta: lo repito.",
        "Mmm, ha quedado torcida, dame otra oportunidad.",
    ],
    "girar_pieza": [
        "No llego bien: gira la pieza 90 grados hacia mí, porfa.",
        "Mis brazos no dan para tanto, ¿me giras la junta hacia aquí?",
        "Gírame la pieza hacia mí, que desde aquí no llego.",
    ],
    # el maestro enseña
    "senalar": [
        "Mira aquí: por esta línea va el cordón.",
        "Justo donde se juntan las dos chapas, ahí va el cordón.",
        "Este es el camino: el cordón va de punta a punta por aquí.",
    ],
    "demostrar": [
        "Mira y aprende.",
        "Fíjate en el ángulo y en el ritmo: así se suelda {una_junta}.",
        "Observa al maestro: pulso firme y velocidad constante.",
        "Atento, que voy a dejar un cordón de exposición.",
    ],
    "reto": [
        "A ver si superas mi cordón, que lo he dejado fino.",
        "Tu turno: intenta ganarme, si puedes.",
        "Te reto a soldar {la_junta} mejor que yo.",
        "Mi cordón es tu fantasma: atrápalo si puedes.",
    ],
    # puntuación
    "juez_gana": [
        "Me has ganado por {diferencia} puntos, pero tenía el sol de cara.",
        "Vale, has ganado, pero exijo la revancha.",
        "Esto no se queda así: mis servos quieren la revancha.",
        "Bah, suerte de principiante, la próxima no te lo pongo tan fácil.",
    ],
    "robot_gana": [
        "Te he ganado por {diferencia} puntos, pero no te desanimes.",
        "Gana la máquina, aunque para ser humano no lo has hecho nada mal.",
        "Robot uno, humano cero: ¿la revancha?",
        "Nada mal, pero mi cordón sigue siendo el más fino del taller.",
    ],
    "record": [
        "¡Nuevo récord con {puntos} puntos, me quito el casco!",
        "¡Récord del día, apunta tus iniciales en la pared de los grandes!",
        "¡Increíble, nuevo récord: hasta me echan chispas los circuitos!",
    ],
    # otras órdenes cumplidas
    "desmontado": [
        "Junta fuera, mesa despejada.",
        "Recogido, el taller limpio como una patena.",
        "Listo, chapa en su sitio y a por la siguiente.",
    ],
    "antorcha": [
        "Aquí tienes la antorcha, que salten chispas.",
        "Antorcha servida, ahora demuéstrame lo que sabes.",
        "Toma la antorcha y enséñame ese pulso.",
    ],
    # no se puede o no se ha entendido
    "no_entendido": [
        "No te he pillado: pídeme una T o una esquina.",
        "Con el ruido del taller no te he oído bien, ¿me lo repites?",
        "Eso no está en mi manual, prueba con «móntame una esquina».",
    ],
    "aclarar": [
        "Perdona, {pregunta}",
        "No me queda claro: {pregunta}",
        "Dímelo más claro, {pregunta}",
    ],
    "sin_junta": [
        "No hay ninguna junta montada, pídeme primero una T o una esquina.",
        "Aquí no hay nada montado todavía, empieza por pedirme una junta.",
        "Primero hay que montar una junta, que soy rápido pero no mago.",
    ],
    "ya_montada": [
        "¡Si ya tienes {la_junta} montada delante!",
        "Esa ya está: {la_junta} te espera montada en la base.",
        "Ya está montada, ahora te toca soldarla a ti.",
    ],
    "otra_montada": [
        "Antes tengo que desmontar {la_junta}, dime «recoge» y la quito.",
        "Ahora mismo está montada {la_junta}: primero la desmonto.",
        "Hay {una_junta} en la base, pídeme que la recoja primero.",
    ],
    "junta_incompleta": [
        "La junta ha quedado a medias, mejor la desmonto y empiezo de nuevo.",
        "Eso no está bien montado, pídeme que lo recoja primero.",
        "Con la junta a medio cerrar no se puede, déjame desmontarla.",
    ],
    "ocupado": [
        "Espera, que tengo las manos ocupadas.",
        "Un momento, termino esto y estoy contigo.",
        "Paciencia, que solo tengo un brazo.",
    ],
    "no_aprendido": [
        "Eso todavía no me lo han enseñado, pero lo estoy practicando.",
        "Esa habilidad es de nivel avanzado y aún no la domino.",
        "Todavía estoy aprendiendo eso, pídeme otra cosa.",
    ],
}
EVENTOS = tuple(FRASES)

# Filtro de lo que diga el LLM (el banco ya está revisado a mano y lo comprueban los tests).
PALABRAS_VETADAS = {
    "mierda", "joder", "coño", "hostia", "hostias", "cabrón", "cabron", "puta", "puto", "gilipollas", "idiota",
    "imbécil", "imbecil", "tonto", "tonta", "estúpido", "estupido", "inútil", "inutil", "subnormal", "capullo",
}
_CORTE_FRASES = re.compile(r"(?<=[.!?…])\s+(?=[¡¿A-ZÁÉÍÓÚÑ])")


def _datos(junta=None, puntos=0, diferencia=0, pregunta="¿cuál quieres?") -> dict:
    try:
        tipo = TipoJunta(junta) if junta is not None else None
    except ValueError:  # "incompleta" u otro estado: se nombra como "la junta"
        tipo = None
    return {**_NOMBRES[tipo], "nombre": NOMBRE, "puntos": int(puntos or 0), "diferencia": abs(int(diferencia or 0)),
            "pregunta": pregunta}


def frase_valida(texto: str) -> bool:
    """Una sola frase, corta, en una línea y sin palabras vetadas."""
    if not texto or "\n" in texto or len(texto) > MAX_CARACTERES:
        return False
    if len(_CORTE_FRASES.split(texto.strip())) != 1:
        return False
    return not set(re.findall(r"\w+", texto.lower())) & PALABRAS_VETADAS


SISTEMA_PERSONAJE = (
    f"Eres {NOMBRE}, el robot SO-101 de LeWelder, una máquina arcade de escuela de soldadura. Eres un personaje "
    "con humor de taller: presumes cuando montas o sueldas, retas al jugador y te picas (con deportividad) si te "
    "gana. Hablas en español de España, tuteas y usas palabras de oficio (cordón, chapa, junta, antorcha, "
    "chispas). Te dan un evento del juego y una frase de ejemplo; responde con UNA sola frase nueva con el mismo "
    f"sentido, de como mucho {MAX_CARACTERES} caracteres, apta para todos los públicos y sin insultos. Usa solo "
    "los datos que te dan. Sin comillas, sin emojis, sin listas: se va a leer en voz alta."
)


class Personaje:
    """Banco de frases por evento, sin repetir la última de cada evento, y variación opcional con LLM."""

    nombre = NOMBRE
    voz = VOZ

    def __init__(self, semilla: int | None = None, frases: dict[str, list[str]] | None = None):
        self.frases = frases if frases is not None else FRASES
        self._azar = random.Random(semilla)
        self._ultima: dict[str, str] = {}

    def info(self) -> dict:
        return {"nombre": self.nombre, "voz": dict(self.voz)}

    def banco(self, evento: str, **datos) -> list[str]:
        """Todas las frases del evento ya rellenas (KeyError si el evento no existe)."""
        valores = _datos(**datos)
        return [plantilla.format(**valores) for plantilla in self.frases[evento]]

    def frase(self, evento: str, **datos) -> str:
        opciones = self.banco(evento, **datos)
        ultima = self._ultima.get(evento)
        candidatas = [f for f in opciones if f != ultima] or opciones
        elegida = self._azar.choice(candidatas)
        self._ultima[evento] = elegida
        return elegida

    @staticmethod
    def reaccion_puntuacion(puntos_juez: float, puntos_robot: float | None, record: float | None = None) -> str:
        """Evento con el que reacciona el robot a la puntuación del juez: récord, el juez gana (empate incluido,
        el robot es caballero) o el robot gana."""
        if record is not None and puntos_juez >= record:
            return "record"
        if puntos_robot is None or puntos_juez >= puntos_robot:
            return "juez_gana"
        return "robot_gana"

    async def frase_variada(self, evento: str, cliente=None, *, modelo: str = MODELO_PERSONAJE,
                            tiempo_max: float = TIEMPO_MAX_PERSONAJE, **datos) -> dict:
        """`{"texto", "origen": "llm" | "banco", "modelo", "evento"}`. Nunca lanza excepciones (salvo un evento
        desconocido) ni tarda más de `tiempo_max`."""
        base = self.frase(evento, **datos)
        if cliente is not None:
            try:
                texto = await asyncio.wait_for(self._pedir_llm(cliente, evento, base, datos, modelo), tiempo_max)
                if texto and frase_valida(texto) and texto != self._ultima.get(f"llm:{evento}"):
                    self._ultima[f"llm:{evento}"] = texto
                    return {"texto": texto, "origen": "llm", "modelo": modelo, "evento": evento}
            except asyncio.TimeoutError:
                log.info("el LLM no ha contestado en %.1f s: frase del banco", tiempo_max)
            except Exception as e:  # red, credenciales, límite de uso... la demo sigue
                log.info("LLM no disponible (%s): frase del banco", type(e).__name__)
        return {"texto": base, "origen": "banco", "modelo": None, "evento": evento}

    @staticmethod
    async def _pedir_llm(cliente, evento: str, base: str, datos: dict, modelo: str) -> str | None:
        contexto = {k: (v.value if isinstance(v, TipoJunta) else v) for k, v in datos.items()}
        respuesta = await cliente.beta.messages.create(
            model=modelo,
            max_tokens=MAX_TOKENS_PERSONAJE,
            system=SISTEMA_PERSONAJE,
            output_config={"effort": "low"},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            messages=[{"role": "user", "content": json.dumps(
                {"evento": evento, "ejemplo": base, "datos": contexto}, ensure_ascii=False)}],
        )
        if getattr(respuesta, "stop_reason", None) == "refusal":
            return None
        texto = " ".join(b.text for b in respuesta.content if getattr(b, "type", None) == "text")
        return " ".join(texto.split()).strip("\"'«» ") or None
