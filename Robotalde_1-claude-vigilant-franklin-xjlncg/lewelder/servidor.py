"""Servidor de LeWelder: une fuente, evaluador, instructor y robot, y se lo enseña a la tablet por WebSocket.

    python -m lewelder.servidor --fuente simulada|raton|real --robot cinematico|mujoco [--anclaje B --tipo recta]
                                [--nivel oficial] [--pasada con_hueco] [--sin-llm] [--puerto 8000]

Con `--robot mujoco` el robot es el SO-101 simulado (`lewelder.robot_mujoco.RobotMuJoCo`) movido por la política
elegida en la tablet: `--checkpoint-vla` (SmolVLA), `--checkpoint-act` (ACT) y `--dataset` (replay, por defecto
`datos/lewelder_sim`). Si la elegida no está, cae a la siguiente (vla → act → replay) y la tablet lo dice.

La tablet abre `http://<ip-del-portátil>:8000/` (página en `web/`, sin internet: three.js va en `web/vendor/`).

Máquina de estados de la demo
-----------------------------
    espera ──empezar_examen──▶ examen ──(fin automático o terminar)──▶ nota
    nota ──repaso (si hay huecos)──▶ repaso        el robot recorre el cordón; LED solo en los huecos
    nota ──certificado (aprobado sin huecos)──▶ certificado
    espera | nota | certificado | repaso/maestro terminados ──maestro──▶ maestro   (cordón entero, LED encendido)
    cualquiera ──reiniciar──▶ espera               (para el robot y apaga el LED)

El examen se cierra solo cuando, después de haber soldado, el gatillo lleva `TIEMPO_FIN` s suelto con la punta al
final del cordón (o `TIEMPO_ABANDONO` s en cualquier sitio), o a los `DURACION_MAX` s.

Protocolo del WebSocket (`/ws`, JSON, un objeto por mensaje)
-----------------------------------------------------------
Servidor → tablet (campo `tipo`):

- `estado`: foto completa al conectar y en cada cambio de modo: `modo`, `nivel`, `pieza {tipo, anclaje}`,
  `fuente {...}`, `robot {politica, nombre_politica, ocupado, instruccion, progreso, punta, led, terminado}`,
  `instruccion`, `certificable`, `puede_repaso`, `huecos`, `resultado`, `valoracion`, `repasados[24]`,
  `cobertura_final`, `politicas`, `pasadas_preparadas`, `certificado {titulo, nivel, nota, fecha}`.
- `historial`: al conectar, las muestras ya recibidas del examen y del robot (`alumno[]`, `robot[]`) para repintar.
- `muestra`: punta del alumno (≤ 30 Hz): `t, x, y, z, gatillo, angulo_trabajo, angulo_avance, calidad`, con
  `calidad` = `bien` (verde) | `regular` (ámbar: rápido, lento o desviado) | `quemado` (rojo) | `suelto`.
- `evaluacion`: estado del evaluador en vivo (~5 Hz): `tramos_cubiertos[24]`, `cobertura_pct`, `nota_parcial`,
  `puntos_quemados`, `velocidad`, `angulo_trabajo`, `angulo_avance`.
- `aviso`: `texto`, `prioridad` (`alta|media|baja`), `t`.
- `resultado`: `resultado` = `Resultado.a_dict()` al acabar el examen (y al cambiar de nivel en la nota).
- `valoracion`: `texto`, `origen` (`llm|reglas`), `modelo`, `id_pasada`. La tablet la lee en voz alta.
- `robot`: punta del robot (≤ 30 Hz y en cada cambio de LED): `punta {x,y,z}`, `led`, `politica` (la elegida),
  `politica_activa` y `aviso_politica` (robot MuJoCo: la que manda de verdad si hubo respaldo, y por qué),
  `progreso`, `repasados[24]`, `instruccion`.
- `robot_fin`: `modo`, `repasados[24]`, `cobertura_final`, `resultado_robot`.
- `robot_imagen`: (solo robot MuJoCo) `jpeg` en base64 de la cámara cenital de la simulación, `ancho`, `alto`
  (~8 por segundo mientras suelda).
- `info` / `error`: `texto` para enseñar un momento.

Tablet → servidor (campo `orden`): `tara`, `empezar_examen`, `terminar`, `repaso`, `maestro` (`tipo?`),
`certificado`, `reiniciar`, `nivel` (`nivel`), `politica` (`politica`), `pieza` (`tipo?`, `anclaje?`; fuentes
simulada y ratón), `simulacion` (`pasada`: nombre de `PASADAS_PREPARADAS` o dict de `ConfigPasada`), `raton`
(`x`, `y`, `gatillo`; fuente ratón), `estado` (pide la foto completa).

HTTP: `/` (la página), `/api/contrato` (medidas del contrato para el gemelo), `/api/estado`.

Cada pasada (examen o robot) se guarda en `salidas/pasadas/*.json` (filtro de dataset y datos del pitch).
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import contextlib
import json
import logging
import time
from datetime import datetime
from pathlib import Path

from aiohttp import WSMsgType, web

from lewelder import contrato as c
from lewelder.contrato import LONGITUD_CORDON, N_TRAMOS, TAMANO_TRAMO, Muestra, TipoPieza, instruccion_soldar
from lewelder.fuentes import (
    PASADAS_PREPARADAS,
    ConfigPasada,
    FuenteRaton,
    FuenteReal,
    FuenteSimulada,
    Latido,
)
from lewelder.instructor import MODELO_LLM, TIEMPO_MAX_LLM, InstructorEnVivo, crear_cliente_llm, valorar
from lewelder.metricas import (
    NOTA_APROBADO,
    SALTO_MAX,
    Z_LEVANTADA,
    EvaluadorEnVivo,
    Resultado,
    evaluar_pasada,
)
from lewelder.robot import POLITICAS, RobotCinematico, punta_sobre_cordon
from lewelder.voz import api_voz

log = logging.getLogger("lewelder.servidor")

RAIZ = Path(__file__).resolve().parents[1]
DIR_WEB = RAIZ / "web"
DIR_PASADAS = RAIZ / "salidas" / "pasadas"

MODOS = ("espera", "examen", "nota", "repaso", "certificado", "maestro")
TIEMPO_FIN = 2.0  # s con el gatillo suelto al final del cordón para cerrar el examen
TIEMPO_ABANDONO = 6.0  # s con el gatillo suelto en cualquier sitio
DURACION_MAX = 120.0  # s
HZ_TABLET = 30.0  # muestras por segundo como mucho hacia la tablet
HZ_EVALUACION = 5.0
TAM_COLA_CLIENTE = 600
PERSISTENCIA_COLOR = 0.3  # s que tiene que durar una velocidad mala para pintar el cordón en ámbar
TITULO_CERTIFICADO = {
    "aprendiz": "Certificado de aprendiz soldador LeWelder",
    "oficial": "Certificado de oficial soldador LeWelder",
    "maestro": "Certificado de maestro soldador LeWelder",
}


def _redondear(d: dict, decimales: int = 2) -> dict:
    return {k: round(v, decimales) if isinstance(v, float) else v for k, v in d.items()}


def contrato_para_web() -> dict:
    """Medidas del contrato que necesita el gemelo (todo en mm, s y grados)."""
    return {
        "longitud_cordon": c.LONGITUD_CORDON, "tamano_tramo": c.TAMANO_TRAMO, "n_tramos": c.N_TRAMOS,
        "chapa": {"largo": c.CHAPA_LARGO, "ancho": c.CHAPA_ANCHO, "grosor": c.CHAPA_GROSOR},
        "holgura_junta": c.HOLGURA_JUNTA, "margen_x": c.MARGEN_X,
        "alma": {"alto": c.ALMA_ALTO, "grosor": c.ALMA_GROSOR},
        "aruco_pieza": {"centro": list(c.ARUCO_EN_PIEZA), "lado": c.LADO_ARUCO_PIEZA,
                        "margen": c.MARGEN_BLANCO_ARUCO},
        "altura_punta": c.ALTURA_PUNTA, "z_levantada": Z_LEVANTADA,
        "tolerancias": c.TOLERANCIAS, "nota_aprobado": NOTA_APROBADO, "nivel_jurado": c.NIVEL_JURADO,
        "velocidad_objetivo": list(c.VELOCIDAD_OBJETIVO),
        "angulo_trabajo_objetivo": c.ANGULO_TRABAJO_OBJETIVO, "margen_angulo_trabajo": c.MARGEN_ANGULO_TRABAJO,
        "angulo_avance_rango": list(c.ANGULO_AVANCE_RANGO),
        "anclajes": {k: {"x": a.x, "y": a.y, "giro": a.giro} for k, a in c.ANCLAJES.items()},
        "politicas": list(POLITICAS),
    }


class Escuela:
    """La demo entera sin HTTP: máquina de estados, evaluación en vivo, robot, LED y difusión a las tablets.

    `emitir` mete cada mensaje (ya en JSON) en la cola de cada tablet conectada (`suscribir`). Las órdenes de la
    tablet entran por `orden(dict)`, que devuelve un texto de error o None.
    """

    def __init__(self, fuente, robot, antorcha_robot=None, *, nivel: str = c.NIVEL_JURADO, cliente_llm=None,
                 modelo_llm: str = MODELO_LLM, tiempo_max_llm: float = TIEMPO_MAX_LLM,
                 dir_pasadas: Path | None = DIR_PASADAS, tiempo_fin: float = TIEMPO_FIN,
                 tiempo_abandono: float = TIEMPO_ABANDONO, hz_tablet: float = HZ_TABLET):
        if nivel not in c.TOLERANCIAS:
            raise ValueError(f"nivel desconocido: {nivel}")
        self.fuente, self.robot, self.antorcha_robot = fuente, robot, antorcha_robot
        self.nivel = nivel
        self.cliente_llm, self.modelo_llm, self.tiempo_max_llm = cliente_llm, modelo_llm, tiempo_max_llm
        self.dir_pasadas = Path(dir_pasadas) if dir_pasadas is not None else None
        self.tiempo_fin, self.tiempo_abandono = tiempo_fin, tiempo_abandono
        self.periodo_tablet = 1.0 / hz_tablet
        self.suscriptores: set[asyncio.Queue] = set()
        self.instructor = InstructorEnVivo()
        self._tareas: set[asyncio.Task] = set()
        self._tarea_fuente: asyncio.Task | None = None
        self._tarea_robot: asyncio.Task | None = None
        self.n_pasada = 0
        self.ultimo_registro: Path | None = None
        if robot is not None and hasattr(robot, "al_imagen"):
            robot.al_imagen = self._imagen_robot  # cámara de la simulación → tablet
        self._reiniciar_estado()
        self.modo = "espera"

    # --- estado ---------------------------------------------------------------------------------------------
    def _reiniciar_estado(self):
        self.evaluador: EvaluadorEnVivo | None = None
        self.muestras_examen: list[Muestra] = []
        self.avisos_mostrados: list[dict] = []
        self.resultado: Resultado | None = None
        self.valoracion: dict | None = None
        self.tipo_examen: TipoPieza | None = None
        self.anclaje_examen: str | None = None
        self._t0_examen: float | None = None
        self._t_examen = 0.0
        self._t_ult_soldando: float | None = None
        self._x_ult_soldando = 0.0
        self._velocidad_mala_desde: float | None = None
        self._ultima_muestra_tablet = 0.0
        self._ultima_evaluacion = 0.0
        self.instructor.reiniciar()
        self._reiniciar_robot()

    def _reiniciar_robot(self):
        self.robot_muestras: list[tuple[Muestra, bool]] = []
        self.repasados = [False] * N_TRAMOS
        self._longitud_repasada = [0.0] * N_TRAMOS
        self.led_robot = False
        self.robot_terminado = False
        self.resultado_robot: Resultado | None = None
        self.instruccion: str | None = None
        self.huecos_robot: list[tuple[float, float]] | None = None
        self.tipo_robot: TipoPieza | None = None
        self.anclaje_robot: str | None = None
        self._ultimo_robot_tablet = 0.0

    def pieza(self) -> tuple[TipoPieza, str | None]:
        return self.fuente.pieza()

    @property
    def certificable(self) -> bool:
        return self.resultado is not None and self.resultado.aprobado and not self.resultado.huecos

    @property
    def puede_repaso(self) -> bool:
        return self.modo == "nota" and self.resultado is not None and bool(self.resultado.huecos) and \
            not self.robot_ocupado

    @property
    def robot_ocupado(self) -> bool:
        return self._tarea_robot is not None and not self._tarea_robot.done()

    def cobertura_final(self) -> float | None:
        if self.resultado is None:
            return None
        cubiertos = [t.cubierto or r for t, r in zip(self.resultado.tramos, self.repasados)]
        return round(100.0 * sum(cubiertos) / N_TRAMOS, 2)

    def estado_robot(self) -> dict:
        e = dict(self.robot.estado()) if self.robot is not None else {"politica": None, "ocupado": False}
        e.update({"led": self.led_robot, "terminado": self.robot_terminado, "disponible": self.robot is not None,
                  "antorcha": self.antorcha_robot is not None})
        return e

    def estado(self) -> dict:
        tipo, anclaje = self.pieza()
        if self.modo in ("repaso", "maestro") and self.tipo_robot is not None:
            tipo, anclaje = self.tipo_robot, self.anclaje_robot
        elif self.tipo_examen is not None and self.modo in ("examen", "nota", "certificado"):
            tipo, anclaje = self.tipo_examen, self.anclaje_examen or anclaje
        certificado = None
        if self.modo == "certificado" and self.resultado is not None:
            certificado = {"titulo": TITULO_CERTIFICADO[self.resultado.nivel], "nivel": self.resultado.nivel,
                           "nota": self.resultado.nota, "fecha": datetime.now().strftime("%d/%m/%Y"),
                           "union": c.NOMBRE_UNION[TipoPieza(self.resultado.tipo)]}
        return {
            "tipo": "estado", "modo": self.modo, "nivel": self.nivel,
            "pieza": {"tipo": TipoPieza(tipo).value, "anclaje": anclaje},
            "fuente": self.fuente.estado(), "robot": self.estado_robot(), "instruccion": self.instruccion,
            "certificable": self.certificable, "puede_repaso": self.puede_repaso,
            "huecos": self.resultado.huecos if self.resultado else [],
            "huecos_robot": self.huecos_robot,
            "resultado": self.resultado.a_dict() if self.resultado else None,
            "valoracion": self.valoracion, "repasados": self.repasados, "cobertura_final": self.cobertura_final(),
            "politicas": list(POLITICAS), "pasadas_preparadas": list(PASADAS_PREPARADAS),
            "certificado": certificado, "id_pasada": self.n_pasada,
        }

    def historial(self) -> dict:
        alumno = [self._mensaje_muestra(m, None) for m in self.muestras_examen[::2]]
        robot = [{"x": m.x, "y": m.y, "z": m.z, "led": led} for m, led in self.robot_muestras[::2]]
        return {"tipo": "historial", "alumno": alumno, "robot": robot}

    # --- difusión -------------------------------------------------------------------------------------------
    def suscribir(self) -> asyncio.Queue:
        cola: asyncio.Queue = asyncio.Queue(maxsize=TAM_COLA_CLIENTE)
        self.suscriptores.add(cola)
        return cola

    def desuscribir(self, cola: asyncio.Queue) -> None:
        self.suscriptores.discard(cola)

    def emitir(self, mensaje: dict) -> None:
        texto = json.dumps(mensaje, ensure_ascii=False, separators=(",", ":"))
        for cola in list(self.suscriptores):
            if cola.full():
                with contextlib.suppress(asyncio.QueueEmpty):
                    cola.get_nowait()  # tablet lenta: se pierde lo más viejo
            cola.put_nowait(texto)

    def emitir_estado(self) -> None:
        self.emitir(self.estado())

    def _tarea(self, corrutina) -> asyncio.Task:
        tarea = asyncio.create_task(corrutina)
        self._tareas.add(tarea)
        tarea.add_done_callback(self._tareas.discard)
        return tarea

    # --- ciclo de vida --------------------------------------------------------------------------------------
    async def iniciar(self) -> None:
        await self.fuente.iniciar()
        self._tarea_fuente = asyncio.create_task(self._leer_fuente())
        if self.robot is not None and hasattr(self.robot, "precargar"):
            self._tarea(self._precargar_robot())

    async def _precargar_robot(self) -> None:
        """Carga las políticas del robot en segundo plano (SmolVLA tarda) y avisa de cuáles hay."""
        try:
            disponibles = await self.robot.precargar()
        except Exception:
            log.exception("no se pudieron precargar las políticas del robot")
            return
        log.info("políticas del robot disponibles: %s", disponibles)
        self.emitir_estado()

    async def cerrar(self) -> None:
        if self.robot is not None:
            self.robot.parar()
        tareas = [t for t in (self._tarea_fuente, self._tarea_robot, *self._tareas) if t is not None]
        for t in tareas:
            t.cancel()
        for t in tareas:
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await t
        self._led(False)
        await self.fuente.cerrar()
        if self.robot is not None and hasattr(self.robot, "cerrar"):
            await asyncio.to_thread(self.robot.cerrar)
        if self.antorcha_robot is not None:
            await asyncio.to_thread(self.antorcha_robot.cerrar)

    async def _leer_fuente(self) -> None:
        while True:
            try:
                async for evento in self.fuente.muestras():
                    self.procesar(evento)
                return
            except asyncio.CancelledError:
                raise
            except Exception:
                log.exception("la fuente ha fallado; se reintenta en 1 s")
                await asyncio.sleep(1.0)

    # --- muestras del alumno --------------------------------------------------------------------------------
    def _calidad(self, m: Muestra) -> str:
        if not m.gatillo:
            return "suelto"
        ev = self.evaluador
        if ev is None:
            return "bien"
        # La misma parada y velocidad que usa el evaluador para los avisos. Al arrancar o al volver a apretar tras
        # un hueco la ventana de velocidad aún no está llena (`velocidad_fiable`): no se juzga la velocidad.
        if ev.en_parada:
            return "quemado"
        v = ev.velocidad
        # El temblor de la mano hace oscilar la velocidad medida: solo se pinta en ámbar si dura un poco.
        if not ev.velocidad_fiable or c.VELOCIDAD_OBJETIVO[0] <= v <= c.VELOCIDAD_OBJETIVO[1]:
            self._velocidad_mala_desde = None
        elif self._velocidad_mala_desde is None:
            self._velocidad_mala_desde = m.t
        velocidad_mala = self._velocidad_mala_desde is not None and \
            m.t - self._velocidad_mala_desde >= PERSISTENCIA_COLOR
        if abs(m.y) > ev.tolerancia or velocidad_mala:
            return "regular"
        return "bien"

    @staticmethod
    def _mensaje_muestra(m: Muestra, calidad: str | None) -> dict:
        d = _redondear(m.a_dict())
        d["tipo"] = "muestra"
        if calidad is not None:
            d["calidad"] = calidad
        return d

    def procesar(self, evento: Muestra | Latido) -> None:
        """Un evento de la fuente (síncrono: no hace nada lento)."""
        if self.modo == "examen":
            self._procesar_examen(evento)
            return
        if isinstance(evento, Muestra):
            ahora = time.monotonic()
            if ahora - self._ultima_muestra_tablet >= self.periodo_tablet or not evento.gatillo:
                self._ultima_muestra_tablet = ahora
                self.emitir(self._mensaje_muestra(evento, "suelto" if not evento.gatillo else "fuera"))

    def _procesar_examen(self, evento: Muestra | Latido) -> None:
        if self._t0_examen is None:
            self._t0_examen = evento.t
        t = evento.t - self._t0_examen
        self._t_examen = t
        ahora = time.monotonic()
        avisos: list[str] = []
        if isinstance(evento, Muestra):
            m = Muestra(t=t, x=evento.x, y=evento.y, z=evento.z, gatillo=evento.gatillo,
                        angulo_trabajo=evento.angulo_trabajo, angulo_avance=evento.angulo_avance)
            self.muestras_examen.append(m)
            avisos = self.evaluador.anadir(m)
            calidad = self._calidad(m)
            if m.gatillo and m.z <= Z_LEVANTADA and 0.0 <= m.x <= LONGITUD_CORDON:
                self._t_ult_soldando, self._x_ult_soldando = t, m.x
            if ahora - self._ultima_muestra_tablet >= self.periodo_tablet or calidad in ("quemado", "suelto"):
                self._ultima_muestra_tablet = ahora
                self.emitir(self._mensaje_muestra(m, calidad))
        for aviso in self.instructor.recibir(avisos, t):
            d = aviso.a_dict()
            self.avisos_mostrados.append(d)
            self.emitir({"tipo": "aviso", **d})
        if ahora - self._ultima_evaluacion >= 1.0 / HZ_EVALUACION and self.muestras_examen:
            self._ultima_evaluacion = ahora
            self.emitir({"tipo": "evaluacion", **self.evaluador.estado()})
        if self._examen_terminado(t):
            self.terminar_examen()

    def _examen_terminado(self, t: float) -> bool:
        if t >= DURACION_MAX:
            return True
        if self._t_ult_soldando is None:
            return False
        pausa = t - self._t_ult_soldando
        al_final = self._x_ult_soldando >= LONGITUD_CORDON - 2 * TAMANO_TRAMO
        return (pausa >= self.tiempo_fin and al_final) or pausa >= self.tiempo_abandono

    # --- transiciones ---------------------------------------------------------------------------------------
    def empezar_examen(self) -> str | None:
        if self.modo == "examen":
            return "ya hay un examen en curso"
        if self.robot_ocupado:
            return "el robot está soldando: espera a que termine o reinicia"
        self._reiniciar_estado()
        self.n_pasada += 1
        self.tipo_examen, self.anclaje_examen = self.pieza()
        self.evaluador = EvaluadorEnVivo(self.tipo_examen, self.nivel)
        self.fuente.empezar_pasada()
        self.modo = "examen"
        self.emitir_estado()
        return None

    def terminar_examen(self) -> str | None:
        if self.modo != "examen":
            return "no hay examen en curso"
        self.resultado = self.evaluador.terminar()
        self.modo = "nota"
        self.emitir({"tipo": "evaluacion", **self.evaluador.estado()})
        self.emitir({"tipo": "resultado", "resultado": self.resultado.a_dict()})
        self.emitir_estado()
        self._tarea(self._valorar_y_guardar(self.n_pasada))
        return None

    async def _valorar_y_guardar(self, id_pasada: int, guardar: bool = True) -> None:
        resultado = self.resultado
        registro = self._registro_examen()
        ruta = await self._guardar(registro, "examen") if guardar else None
        valoracion = await valorar(resultado, self.cliente_llm, self.modelo_llm, self.tiempo_max_llm)
        if id_pasada != self.n_pasada or self.resultado is not resultado:
            return  # ya empezó otra pasada o cambió el nivel
        self.valoracion = {**valoracion, "id_pasada": id_pasada}
        self.emitir({"tipo": "valoracion", **self.valoracion})
        if ruta is not None:
            registro["valoracion"] = self.valoracion
            await self._guardar(registro, "examen", ruta)

    def _registro_examen(self) -> dict:
        return {
            "version": 1, "clase": "examen", "fecha": datetime.now().isoformat(timespec="seconds"),
            "id_pasada": self.n_pasada, "fuente": self.fuente.estado(),
            "tipo": self.tipo_examen.value if self.tipo_examen else None, "anclaje": self.anclaje_examen,
            "nivel": self.nivel, "muestras": [m.a_dict() for m in self.muestras_examen],
            "resultado": self.resultado.a_dict() if self.resultado else None,
            "avisos_mostrados": self.avisos_mostrados, "valoracion": self.valoracion,
        }

    async def _guardar(self, registro: dict, clase: str, ruta: Path | None = None) -> Path | None:
        if self.dir_pasadas is None:
            return None
        if ruta is None:
            sello = datetime.now().strftime("%Y%m%d-%H%M%S")
            ruta = self.dir_pasadas / f"{sello}-{clase}-{self.n_pasada:03d}.json"
            n = 1
            while ruta.exists():
                n += 1
                ruta = self.dir_pasadas / f"{sello}-{clase}-{self.n_pasada:03d}-{n}.json"

        def escribir():
            ruta.parent.mkdir(parents=True, exist_ok=True)
            ruta.write_text(json.dumps(registro, ensure_ascii=False, indent=1), encoding="utf-8")

        try:
            await asyncio.to_thread(escribir)
        except OSError:
            log.exception("no se pudo guardar la pasada en %s", ruta)
            return None
        self.ultimo_registro = ruta
        return ruta

    def cambiar_nivel(self, nivel: str) -> str | None:
        if nivel not in c.TOLERANCIAS:
            return f"nivel desconocido: {nivel}"
        if self.modo in ("examen", "repaso", "maestro") and (self.modo == "examen" or self.robot_ocupado):
            return "no se puede cambiar de nivel en mitad de una pasada"
        self.nivel = nivel
        if self.modo in ("nota", "certificado") and self.muestras_examen:
            # La misma pasada, juzgada con la tolerancia y el aprobado del nuevo nivel.
            self.resultado = evaluar_pasada(self.muestras_examen, self.tipo_examen, nivel)
            self.valoracion = None
            self.modo = "nota"
            self.emitir({"tipo": "resultado", "resultado": self.resultado.a_dict()})
            self._tarea(self._valorar_y_guardar(self.n_pasada, guardar=False))
        self.emitir_estado()
        return None

    def ir_a_certificado(self) -> str | None:
        if self.modo != "nota":
            return "el certificado se da desde la nota"
        if not self.certificable:
            return "para el certificado hay que aprobar sin dejar huecos"
        self.modo = "certificado"
        self.emitir_estado()
        return None

    def empezar_repaso(self) -> str | None:
        if self.modo != "nota" or self.resultado is None:
            return "el repaso se hace después de la nota"
        if not self.resultado.huecos:
            return "no hay huecos que repasar"
        if self.robot is None:
            return "no hay robot"
        if self.robot_ocupado:
            return "el robot ya está soldando"
        self._lanzar_robot("repaso", self.tipo_examen, self.anclaje_examen, list(self.resultado.huecos))
        return None

    def empezar_maestro(self, tipo: str | None = None) -> str | None:
        if self.modo == "examen":
            return "termina el examen antes"
        if self.robot is None:
            return "no hay robot"
        if self.robot_ocupado:
            return "el robot ya está soldando"
        tipo_pieza, anclaje = self.pieza()
        if tipo is not None:
            try:
                tipo_pieza = TipoPieza(tipo)
            except ValueError:
                return f"tipo de pieza desconocido: {tipo}"
        self._lanzar_robot("maestro", tipo_pieza, anclaje, None)
        return None

    def _lanzar_robot(self, modo: str, tipo: TipoPieza, anclaje: str | None, huecos) -> None:
        self._reiniciar_robot()
        anclaje = anclaje or "B"
        self.modo = modo
        self.tipo_robot, self.anclaje_robot = TipoPieza(tipo), anclaje
        self.huecos_robot = huecos
        self.instruccion = instruccion_soldar(self.tipo_robot, anclaje)
        self._tarea_robot = asyncio.create_task(self._soldar(modo))
        self.emitir_estado()

    # --- robot ----------------------------------------------------------------------------------------------
    def _led(self, encendido: bool) -> None:
        self.led_robot = encendido
        if self.antorcha_robot is not None:
            try:
                self.antorcha_robot.led(encendido)
            except Exception:
                log.exception("no se pudo cambiar el LED del robot")

    def led_para(self, m: Muestra, huecos: list[tuple[float, float]] | None) -> bool:
        """¿Debe lucir el LED del robot con la punta en `m`? Solo encima del cordón a la altura de soldar
        (`punta_sobre_cordon`) y, en el repaso, dentro de un tramo pendiente."""
        if not punta_sobre_cordon(m):
            return False
        return huecos is None or any(a <= m.x < b for a, b in huecos)

    def _anotar_repasado(self, m: Muestra, led: bool) -> bool:
        """Suma lo soldado por el robot entre la muestra anterior y esta; True si algún tramo pasa a repasado."""
        if not self.robot_muestras:
            return False
        anterior, led_anterior = self.robot_muestras[-1]
        if not (led and led_anterior) or m.t - anterior.t > SALTO_MAX:
            return False
        a, b = sorted((anterior.x, m.x))
        nuevo = False
        for i in range(N_TRAMOS):
            ini, fin = i * TAMANO_TRAMO, (i + 1) * TAMANO_TRAMO
            self._longitud_repasada[i] += max(0.0, min(b, fin) - max(a, ini))
            if not self.repasados[i] and self._longitud_repasada[i] >= 0.5 * TAMANO_TRAMO:
                self.repasados[i] = nuevo = True
        return nuevo

    def _mensaje_robot(self) -> dict:
        p = self.robot.punta if getattr(self.robot, "punta", None) is not None else None
        e = self.robot.estado()
        punta = e.get("punta") or ({"x": p.x, "y": p.y, "z": p.z} if p is not None else None)
        return {"tipo": "robot", "punta": punta and _redondear(punta), "led": self.led_robot,
                "politica": e.get("politica"), "politica_activa": e.get("politica_activa"),
                "aviso_politica": e.get("aviso_politica"), "progreso": e.get("progreso"),
                "repasados": self.repasados, "instruccion": self.instruccion}

    def _imagen_robot(self, jpeg: bytes) -> None:
        """Fotograma JPEG de la cámara cenital de la simulación para el recuadro de la tablet."""
        from lewelder.robot_mujoco import RESOLUCION_IMAGEN

        self.emitir({"tipo": "robot_imagen", "jpeg": base64.b64encode(jpeg).decode("ascii"),
                     "ancho": RESOLUCION_IMAGEN[0], "alto": RESOLUCION_IMAGEN[1]})

    def _al_moverse_robot(self, m: Muestra) -> None:
        led = self.led_para(m, self.huecos_robot)
        cambio = led != self.led_robot
        if cambio:
            self._led(led)
        nuevo_tramo = self._anotar_repasado(m, led)
        self.robot_muestras.append((m, led))
        ahora = time.monotonic()
        if cambio or nuevo_tramo or ahora - self._ultimo_robot_tablet >= self.periodo_tablet:
            self._ultimo_robot_tablet = ahora
            msg = self._mensaje_robot()
            msg["punta"] = _redondear({"x": m.x, "y": m.y, "z": m.z})
            self.emitir(msg)

    async def _soldar(self, modo: str) -> None:
        try:
            await self.robot.soldar(self.tipo_robot, self.anclaje_robot, self.instruccion, self.huecos_robot,
                                    self._al_moverse_robot)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            log.exception("el robot ha fallado")
            self.emitir({"tipo": "error", "texto": f"el robot ha fallado: {e}"})
        finally:
            self._led(False)
        self.robot_terminado = True
        muestras = [Muestra(t=m.t, x=m.x, y=m.y, z=m.z, gatillo=led) for m, led in self.robot_muestras]
        if muestras:
            self.resultado_robot = evaluar_pasada(muestras, self.tipo_robot, self.nivel)
        self.emitir({"tipo": "robot_fin", "modo": modo, "repasados": self.repasados,
                     "cobertura_final": self.cobertura_final(),
                     "resultado_robot": self.resultado_robot.a_dict() if self.resultado_robot else None})
        self.emitir_estado()
        await self._guardar({
            "version": 1, "clase": modo, "fecha": datetime.now().isoformat(timespec="seconds"),
            "id_pasada": self.n_pasada, "tipo": self.tipo_robot.value, "anclaje": self.anclaje_robot,
            "instruccion": self.instruccion, "politica": self.robot.estado().get("politica"),
            "cambios_politica": getattr(self.robot, "cambios_politica", []), "huecos": self.huecos_robot,
            "muestras": [m.a_dict() for m in muestras], "repasados": self.repasados,
            "cobertura_final": self.cobertura_final(),
            "resultado_robot": self.resultado_robot.a_dict() if self.resultado_robot else None,
        }, modo)

    def cambiar_politica(self, politica: str) -> str | None:
        if self.robot is None:
            return "no hay robot"
        politica = str(politica).lower()
        if politica not in POLITICAS:
            return f"política desconocida: {politica}"
        if hasattr(self.robot, "cambiar_politica"):
            self.robot.cambiar_politica(politica)
        else:
            self.robot.politica = politica
        self.emitir(self._mensaje_robot())
        self.emitir_estado()
        return None

    async def reiniciar(self) -> None:
        if self.robot is not None:
            self.robot.parar()
        if self._tarea_robot is not None and not self._tarea_robot.done():
            self._tarea_robot.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await self._tarea_robot
        self._led(False)
        self._reiniciar_estado()
        self.modo = "espera"
        self.emitir_estado()

    # --- órdenes de la tablet -------------------------------------------------------------------------------
    async def orden(self, msg: dict) -> str | None:
        """Ejecuta una orden de la tablet; devuelve un texto de error para esa tablet o None."""
        orden = msg.get("orden")
        if orden == "raton":
            if isinstance(self.fuente, FuenteRaton):
                try:
                    self.fuente.mover(float(msg["x"]), float(msg["y"]), bool(msg.get("gatillo")))
                except (KeyError, TypeError, ValueError):
                    return "orden raton sin x, y"
            return None
        if orden == "estado":
            return None
        if orden == "tara":
            ok = self.fuente.tara()
            self.emitir({"tipo": "info" if ok else "error",
                         "texto": "Tara hecha: antorcha vertical" if ok else "No hay lectura de la IMU para la tara"})
            self.emitir_estado()
            return None
        if orden == "empezar_examen":
            return self.empezar_examen()
        if orden == "terminar":
            return self.terminar_examen()
        if orden == "repaso":
            return self.empezar_repaso()
        if orden == "maestro":
            return self.empezar_maestro(msg.get("tipo"))
        if orden == "certificado":
            return self.ir_a_certificado()
        if orden == "reiniciar":
            await self.reiniciar()
            return None
        if orden == "nivel":
            return self.cambiar_nivel(str(msg.get("nivel")))
        if orden == "politica":
            return self.cambiar_politica(msg.get("politica"))
        if orden == "pieza":
            if self.modo not in ("espera", "nota", "certificado") or self.robot_ocupado:
                return "la pieza se cambia en espera"
            if not hasattr(self.fuente, "configurar"):
                return "con la fuente real la pieza se detecta por el ArUco"
            try:
                self.fuente.configurar(tipo=msg.get("tipo"), anclaje=msg.get("anclaje"))
            except ValueError as e:
                return str(e)
            self.emitir_estado()
            return None
        if orden == "simulacion":
            if not isinstance(self.fuente, FuenteSimulada):
                return "solo con la fuente simulada"
            pasada = msg.get("pasada")
            if isinstance(pasada, str):
                if pasada not in PASADAS_PREPARADAS:
                    return f"pasada desconocida: {pasada}"
                config = PASADAS_PREPARADAS[pasada]
            elif isinstance(pasada, dict):
                config = ConfigPasada.de_dict(pasada)
            else:
                return "falta la pasada"
            self.fuente.configurar(config=config)
            self.emitir({"tipo": "info", "texto": "Simulación preparada para el próximo examen"})
            self.emitir_estado()
            return None
        return f"orden desconocida: {orden}"


# --- aplicación web ----------------------------------------------------------------------------------------------
async def _ws(request: web.Request) -> web.WebSocketResponse:
    escuela: Escuela = request.app["escuela"]
    ws = web.WebSocketResponse(heartbeat=10.0)
    await ws.prepare(request)
    cola = escuela.suscribir()
    await ws.send_str(json.dumps(escuela.estado(), ensure_ascii=False))
    await ws.send_str(json.dumps(escuela.historial(), ensure_ascii=False))

    async def enviar():
        while True:
            texto = await cola.get()
            await ws.send_str(texto)

    emisor = asyncio.create_task(enviar())
    try:
        async for mensaje in ws:
            if mensaje.type != WSMsgType.TEXT:
                continue
            try:
                datos = json.loads(mensaje.data)
                if not isinstance(datos, dict):
                    raise ValueError
            except ValueError:
                await ws.send_str(json.dumps({"tipo": "error", "texto": "mensaje no válido"}))
                continue
            error = await escuela.orden(datos)
            if error:
                await ws.send_str(json.dumps({"tipo": "error", "texto": error}, ensure_ascii=False))
            elif datos.get("orden") == "estado":
                await ws.send_str(json.dumps(escuela.estado(), ensure_ascii=False))
    finally:
        emisor.cancel()
        with contextlib.suppress(asyncio.CancelledError, Exception):
            await emisor
        escuela.desuscribir(cola)
    return ws


async def _index(request: web.Request) -> web.FileResponse:
    return web.FileResponse(request.app["dir_web"] / "index.html")


async def _contrato(request: web.Request) -> web.Response:
    return web.json_response(contrato_para_web())


async def _estado(request: web.Request) -> web.Response:
    return web.json_response(request.app["escuela"].estado())


@web.middleware
async def _sin_cache(request, handler):
    respuesta = await handler(request)
    respuesta.headers["Cache-Control"] = "no-store"
    return respuesta


def crear_app(escuela: Escuela, dir_web: Path = DIR_WEB, iniciar: bool = True) -> web.Application:
    """Aplicación aiohttp. Con `iniciar`, arranca la fuente al arrancar el servidor y la cierra al pararlo."""
    app = web.Application(middlewares=[_sin_cache])
    app["escuela"] = escuela
    app["dir_web"] = Path(dir_web)
    app.router.add_get("/ws", _ws)
    app.router.add_get("/api/contrato", _contrato)
    app.router.add_get("/api/estado", _estado)
    app.router.add_post("/api/voz", api_voz)  # voz → orden (lewelder/voz.py)
    app.router.add_get("/", _index)
    app.router.add_static("/", Path(dir_web), follow_symlinks=False)
    if iniciar:
        async def arrancar(app):
            await escuela.iniciar()

        async def parar(app):
            await escuela.cerrar()

        app.on_startup.append(arrancar)
        app.on_cleanup.append(parar)
    return app


# --- línea de órdenes --------------------------------------------------------------------------------------------
def _par(texto: str) -> tuple[float, float]:
    a, b = texto.replace(":", "-").split("-")
    return float(a), float(b)


def crear_fuente(args):
    if args.fuente == "simulada":
        config = PASADAS_PREPARADAS.get(args.pasada, ConfigPasada())
        if args.huecos is not None:
            config = ConfigPasada.de_dict({**config.a_dict(), "huecos": [_par(h) for h in args.huecos]})
        return FuenteSimulada(args.tipo, args.anclaje, config=config)
    if args.fuente == "raton":
        return FuenteRaton(args.tipo, args.anclaje)
    return FuenteReal(indice_camara=args.camara, puerto_antorcha=args.puerto_alumno,
                      calibracion=args.calibracion, tipo_por_defecto=args.tipo,
                      buscar=not getattr(args, "ya_buscadas", False))


def crear_antorcha_robot(modo: str, encontradas: dict[str, str] | None = None):
    """(antorcha_robot, antorcha_virtual) según `--antorcha-robot`: virtual, auto, ninguna o un puerto.
    `encontradas` es el resultado de `buscar_antorchas` si ya se hizo (para no preguntar a los puertos dos veces)."""
    from lewelder.antorcha import AntorchaRobot, buscar_antorchas
    from lewelder.antorcha_virtual import AntorchaRobotVirtual

    if modo == "ninguna":
        return None, None
    if modo == "virtual":
        virtual = AntorchaRobotVirtual()
        return AntorchaRobot(virtual.ruta), virtual
    if modo == "auto":
        puerto = (encontradas if encontradas is not None else buscar_antorchas()).get("robot")
        if puerto is None:
            log.warning("no se encuentra la antorcha del robot: el LED solo se verá en la tablet")
            return None, None
        return AntorchaRobot(puerto), None
    return AntorchaRobot(modo), None


def crear_robot(args):
    """El robot según `--robot`: el sustituto cinemático o el SO-101 simulado en MuJoCo con las políticas."""
    if args.robot == "cinematico":
        return RobotCinematico(politica=args.politica, escala_tiempo=args.escala_robot)
    from lewelder.robot_mujoco import RobotMuJoCo

    dataset = args.dataset
    if dataset is not None and not Path(dataset).exists():
        log.warning("no existe el dataset %s: sin replay", dataset)
        dataset = None
    return RobotMuJoCo(politica=args.politica, checkpoint_act=args.checkpoint_act,
                       checkpoint_vla=args.checkpoint_vla, dataset=dataset, escala_tiempo=args.escala_robot,
                       dispositivo=args.dispositivo)


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description="Servidor de LeWelder (tablet en http://<ip>:PUERTO/)")
    p.add_argument("--fuente", choices=["simulada", "raton", "real"], default="simulada")
    p.add_argument("--simulado", action="store_true", help="atajo de --fuente simulada")
    p.add_argument("--robot", choices=["cinematico", "mujoco"], default="cinematico")
    p.add_argument("--politica", choices=list(POLITICAS), default="vla")
    p.add_argument("--escala-robot", type=float, default=1.0, help=">1 acelera el robot (ensayos)")
    p.add_argument("--checkpoint-vla", default=None, help="robot mujoco: pretrained_model de SmolVLA")
    p.add_argument("--checkpoint-act", default=None, help="robot mujoco: pretrained_model de ACT")
    p.add_argument("--dataset", default=str(RAIZ / "datos" / "lewelder_sim"),
                   help="robot mujoco: LeRobotDataset para la reproducción grabada (replay)")
    p.add_argument("--dispositivo", default="cpu", help="robot mujoco: cpu | cuda para la inferencia")
    p.add_argument("--tipo", choices=[t.value for t in TipoPieza], default="recta")
    p.add_argument("--anclaje", choices=list(c.ANCLAJES), default="B")
    p.add_argument("--nivel", choices=list(c.TOLERANCIAS), default=c.NIVEL_JURADO)
    p.add_argument("--pasada", choices=list(PASADAS_PREPARADAS), default="con_hueco",
                   help="pasada de la fuente simulada")
    p.add_argument("--huecos", nargs="*", help="huecos de la pasada simulada, p. ej. 40-55 90-100")
    p.add_argument("--antorcha-robot", default=None,
                   help="virtual | auto | ninguna | PUERTO (por defecto: virtual en simulación, auto en real)")
    p.add_argument("--camara", type=int, default=0)
    p.add_argument("--calibracion", default=None)
    p.add_argument("--puerto-alumno", default=None)
    p.add_argument("--sin-llm", action="store_true", help="valoración final solo por reglas")
    p.add_argument("--host", default="0.0.0.0")
    p.add_argument("--puerto", type=int, default=8000)
    args = p.parse_args(argv)
    if args.simulado:
        args.fuente = "simulada"
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    modo_antorcha = args.antorcha_robot or ("auto" if args.fuente == "real" else "virtual")
    encontradas = None
    if args.fuente == "real" and (args.puerto_alumno is None or modo_antorcha == "auto"):
        from lewelder.antorcha import buscar_antorchas

        encontradas = buscar_antorchas()  # una sola ronda de "?" por todos los puertos
        args.ya_buscadas = True
        log.info("antorchas encontradas: %s", encontradas or "ninguna")
        if args.puerto_alumno is None:
            args.puerto_alumno = encontradas.get("alumno")
    fuente = crear_fuente(args)
    robot = crear_robot(args)
    antorcha_robot, virtual = crear_antorcha_robot(modo_antorcha, encontradas)
    cliente = None if args.sin_llm else crear_cliente_llm()
    escuela = Escuela(fuente, robot, antorcha_robot, nivel=args.nivel, cliente_llm=cliente)
    app = crear_app(escuela)
    if virtual is not None:
        async def parar_virtual(app):
            virtual.parar()
        app.on_cleanup.append(parar_virtual)
    print(f"LeWelder: tablet en http://<ip-de-este-equipo>:{args.puerto}/  (fuente {args.fuente}, "
          f"robot {args.robot}, LLM {'no' if cliente is None else MODELO_LLM})", flush=True)
    web.run_app(app, host=args.host, port=args.puerto, print=None)


if __name__ == "__main__":
    main()
