"""Instructor: avisos de oficio durante la pasada y valoración hablada al final.

Dos partes, con criterios distintos:

- **Avisos en vivo (reglas, sin red).** `EvaluadorEnVivo` ya decide qué fallos hay en cada muestra; aquí se decide
  qué se enseña: uno cada vez, por prioridad (un punto quemado o un hueco importan más que el ángulo) y sin saturar
  (un mínimo de tiempo entre avisos; uno más grave puede adelantarse). Un aviso que espera demasiado se descarta:
  a mitad de cordón no sirve de nada que te digan lo que hiciste hace tres segundos.
- **Valoración final (LLM, con respaldo).** Dos frases en tono de maestro soldador, en español, a partir del
  `Resultado`. Se pide al LLM con un tiempo máximo (`TIEMPO_MAX_LLM`); si no hay clave, no hay red, tarda o se
  niega, se usa la valoración por reglas, que siempre está. La demo nunca espera al LLM más de eso.

Modelo: `claude-opus-5-5` con esfuerzo `low` (dos frases no necesitan más razonamiento y así responde antes).
Se puede cambiar con la variable de entorno `LEWELDER_MODELO_LLM` (p. ej. `claude-haiku-5-5` si la latencia del
evento no deja llegar en `TIEMPO_MAX_LLM`).
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import dataclass

from lewelder.metricas import (
    AVISO_AVANCE_EXCESIVO,
    AVISO_DESVIO,
    AVISO_EMPUJA,
    AVISO_FIRME,
    AVISO_GATILLO,
    AVISO_LENTO,
    AVISO_RAPIDO,
    AVISO_RITMO,
    AVISO_TUMBA_MAS,
    AVISO_TUMBA_MENOS,
    AVISO_VERTICAL,
    NOTA_APROBADO,
    Resultado,
)

log = logging.getLogger(__name__)

MODELO_LLM = os.environ.get("LEWELDER_MODELO_LLM", "claude-opus-5-5")
TIEMPO_MAX_LLM = 3.0  # s
MAX_TOKENS_LLM = 1024  # dos frases + el poco razonamiento del esfuerzo bajo

# --- avisos en vivo ----------------------------------------------------------------------------------------------
ALTA, MEDIA, BAJA = 3, 2, 1
NOMBRE_PRIORIDAD = {ALTA: "alta", MEDIA: "media", BAJA: "baja"}
PRIORIDADES = {
    AVISO_GATILLO: ALTA,
    AVISO_DESVIO: MEDIA,
    AVISO_RAPIDO: MEDIA,
    AVISO_LENTO: MEDIA,
    AVISO_RITMO: BAJA,
    AVISO_TUMBA_MENOS: BAJA,
    AVISO_TUMBA_MAS: BAJA,
    AVISO_VERTICAL: BAJA,
    AVISO_EMPUJA: BAJA,
    AVISO_AVANCE_EXCESIVO: BAJA,
    AVISO_FIRME: BAJA,
}
INTERVALO_AVISOS = 1.5  # s mínimos entre dos avisos mostrados
INTERVALO_URGENTE = 0.5  # s: un aviso más grave que el último puede adelantarse hasta aquí
CADUCIDAD_AVISO = 1.5  # s que un aviso puede esperar su turno


def prioridad(texto: str) -> int:
    if texto.startswith("te has quedado parado"):
        return ALTA
    return PRIORIDADES.get(texto, MEDIA)


@dataclass
class Aviso:
    texto: str
    prioridad: int
    t: float

    def a_dict(self) -> dict:
        return {"texto": self.texto, "prioridad": NOMBRE_PRIORIDAD[self.prioridad], "t": round(self.t, 3)}


class InstructorEnVivo:
    """Filtra los avisos del evaluador: uno cada vez, por prioridad y sin saturar.

    `recibir(avisos, t)` se llama con cada muestra (aunque no traiga avisos, para soltar el que espera) y devuelve
    los avisos que hay que enseñar ahora (casi siempre ninguno, como mucho uno).
    """

    def __init__(self, intervalo: float = INTERVALO_AVISOS, intervalo_urgente: float = INTERVALO_URGENTE,
                 caducidad: float = CADUCIDAD_AVISO):
        self.intervalo, self.intervalo_urgente, self.caducidad = intervalo, intervalo_urgente, caducidad
        self.reiniciar()

    def reiniciar(self) -> None:
        self._pendiente: Aviso | None = None
        self._ultimo: Aviso | None = None
        self.mostrados: list[Aviso] = []

    def recibir(self, avisos: list[str], t: float) -> list[Aviso]:
        for texto in avisos:
            nuevo = Aviso(texto, prioridad(texto), t)
            if self._pendiente is None or nuevo.prioridad >= self._pendiente.prioridad:
                self._pendiente = nuevo
        p = self._pendiente
        if p is None:
            return []
        if t - p.t > self.caducidad:
            self._pendiente = None
            return []
        if self._ultimo is not None:
            desde = t - self._ultimo.t
            urgente = p.prioridad > self._ultimo.prioridad and desde >= self.intervalo_urgente
            if desde < self.intervalo and not urgente:
                return []
        self._pendiente = None
        mostrado = Aviso(p.texto, p.prioridad, t)
        self._ultimo = mostrado
        self.mostrados.append(mostrado)
        return [mostrado]


# --- valoración final --------------------------------------------------------------------------------------------
def _mm(v: float) -> str:
    return f"{round(v)} mm"


def _fallo_principal(r: Resultado) -> str | None:
    """El consejo más importante, en lenguaje de oficio (o None si no hay nada que corregir)."""
    if r.duracion_s == 0:
        return "Aprieta el gatillo con la punta sobre la junta y avanza despacio, que hoy no ha prendido nada."
    if r.huecos:
        a, b = r.huecos[0]
        extra = f" y {len(r.huecos) - 1} más" if len(r.huecos) > 1 else ""
        return (f"Te has dejado sin soldar de {_mm(a)} a {_mm(b)}{extra}: no sueltes el gatillo hasta llegar al "
                f"final.")
    if r.n_quemados:
        return "Te has quedado parado y has quemado la chapa: mantén el avance aunque dudes."
    if r.desvio_medio_mm > r.tolerancia_mm / 2:
        return "Te vas del cordón: apoya la muñeca y mira la junta, no la punta."
    if r.velocidad_media > 6.0:
        return "Vas con prisa: baja el ritmo para que el baño moje bien los dos bordes."
    if 0 < r.velocidad_media < 4.0:
        return "Vas muy lento y metes demasiado calor: avanza con más decisión."
    if r.cv_velocidad > 0.25:
        return "El ritmo va a tirones: busca una velocidad constante de principio a fin."
    if r.pct_tiempo_angulo_ok is not None and r.pct_tiempo_angulo_ok < 60:
        objetivo = "a 45 grados entre las dos chapas" if r.tipo == "t" else "vertical sobre la junta"
        return f"Cuida el ángulo: la antorcha {objetivo} y empujando un poco hacia delante."
    return None


def valoracion_por_reglas(r: Resultado) -> str:
    """Dos frases de maestro soldador sin LLM: juicio general y el consejo más importante."""
    nota = f"{r.nota:.1f}".replace(".", ",")
    consejo = _fallo_principal(r)
    if r.duracion_s == 0:
        juicio = "Así no hay cordón que valga."
    elif r.aprobado and not r.huecos and r.nota >= 8.5 and consejo is None:
        juicio = f"Un {nota}: cordón completo, regular y bien centrado, así se suelda."
    elif r.aprobado and not r.huecos and r.nota >= 8.5:
        juicio = f"Un {nota}: buen cordón, completo y sin huecos."
    elif r.aprobado:
        juicio = f"Un {nota}: apruebas, pero a este cordón todavía le falta oficio."
    elif r.nota >= NOTA_APROBADO[r.nivel] - 1.5:
        juicio = f"Un {nota}: te has quedado cerca, pero esta pieza no pasaría la inspección."
    else:
        juicio = f"Un {nota}: esta pieza habría que repetirla."
    if consejo is None:
        consejo = ("Sigue así y pásate al nivel maestro." if r.nivel != "maestro"
                   else "Pocos soldadores dejan un cordón así.")
    return f"{juicio} {consejo}"


SISTEMA_INSTRUCTOR = (
    "Eres el maestro soldador de LeWelder, una escuela de soldadura. Acabas de ver la pasada de un alumno sobre "
    "una pieza de prácticas y le das tu valoración en voz alta, delante de todos. Hablas en español de España, "
    "tuteas, con el tono de un maestro de taller veterano: directo, cercano y con palabras de oficio (cordón, "
    "baño, junta, avance, ángulo de la antorcha, quemado). Responde con exactamente dos frases y como mucho 40 "
    "palabras en total: la primera da tu juicio y la nota redondeada a un decimal; la segunda, el consejo más "
    "importante para la próxima pasada. Usa solo los datos que te dan; no inventes cifras. Sin listas, sin "
    "emojis, sin comillas: es texto que se va a leer en voz alta."
)


def resumen_para_llm(r: Resultado) -> dict:
    """Los datos del resultado que necesita el LLM (sin el detalle por tramos)."""
    return {
        "union": "en T" if r.tipo == "t" else "a tope recta",
        "nivel": r.nivel,
        "nota": r.nota,
        "aprobado": r.aprobado,
        "nota_para_aprobar": NOTA_APROBADO[r.nivel],
        "cobertura_pct": r.cobertura_pct,
        "huecos_mm": [[round(a), round(b)] for a, b in r.huecos],
        "puntos_quemados_mm": [round(x) for x in r.puntos_quemados],
        "velocidad_media_mm_s": r.velocidad_media,
        "velocidad_buena_mm_s": [4, 6],
        "regularidad_cv": r.cv_velocidad,
        "desvio_medio_mm": r.desvio_medio_mm,
        "tolerancia_mm": r.tolerancia_mm,
        "pct_tiempo_angulo_correcto": r.pct_tiempo_angulo_ok,
        "angulo_trabajo_medio": r.angulo_trabajo_medio,
        "angulo_avance_medio": r.angulo_avance_medio,
        "avisos": r.avisos,
    }


def crear_cliente_llm(timeout: float = TIEMPO_MAX_LLM):
    """Cliente asíncrono de la API de Claude, o None si no se puede crear (sin SDK o sin credenciales).

    Sin reintentos: con un tiempo máximo de 3 s no hay margen para reintentar, y la valoración por reglas está ahí.
    """
    try:
        import anthropic
    except ImportError:
        return None
    # El SDK busca las credenciales (variable de entorno o perfil de `ant auth login`); si no hay ninguna, la
    # llamada falla al momento y se usan las reglas.
    try:
        return anthropic.AsyncAnthropic(timeout=timeout, max_retries=0)
    except Exception as e:  # sin credenciales u otra configuración inválida
        log.info("sin cliente LLM: %s", e)
        return None


async def _pedir_llm(cliente, r: Resultado, modelo: str) -> str | None:
    respuesta = await cliente.beta.messages.create(
        model=modelo,
        max_tokens=MAX_TOKENS_LLM,
        system=SISTEMA_INSTRUCTOR,
        output_config={"effort": "low"},
        # Si el modelo se niega (clasificadores de seguridad), el servidor reintenta con otro modelo en la misma
        # llamada; si toda la cadena se niega, stop_reason == "refusal" y se usan las reglas.
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        messages=[{
            "role": "user",
            "content": "Resultado de la pasada (JSON):\n" + json.dumps(resumen_para_llm(r), ensure_ascii=False),
        }],
    )
    if getattr(respuesta, "stop_reason", None) == "refusal":
        return None
    texto = " ".join(b.text for b in respuesta.content if getattr(b, "type", None) == "text").strip()
    return " ".join(texto.split()) or None


async def valorar(r: Resultado, cliente=None, modelo: str = MODELO_LLM,
                  tiempo_max: float = TIEMPO_MAX_LLM) -> dict:
    """Valoración final: `{"texto", "origen": "llm" | "reglas", "modelo"}`. Nunca lanza excepciones ni tarda más
    de `tiempo_max` (más lo que tarde en cancelarse la petición)."""
    if cliente is not None and r.duracion_s > 0:
        try:
            texto = await asyncio.wait_for(_pedir_llm(cliente, r, modelo), timeout=tiempo_max)
            if texto:
                return {"texto": texto, "origen": "llm", "modelo": modelo}
        except asyncio.TimeoutError:
            log.info("el LLM no ha contestado en %.1f s: valoración por reglas", tiempo_max)
        except Exception as e:  # red, credenciales, límite de uso... la demo sigue
            log.info("LLM no disponible (%s): valoración por reglas", type(e).__name__)
    return {"texto": valoracion_por_reglas(r), "origen": "reglas", "modelo": None}
