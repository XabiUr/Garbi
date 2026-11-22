"""Simulador de la demo v2: la mesa en 3D, el robot en tiempo real, el juez con el ratón y la tablet, todo junto.

    python -m lewelder.simulador [--puerto 8080] [--guion jurado] [--dataset RUTA] [--checkpoint-vla RUTA]

Abre `http://localhost:8080/` (vista combinada: mesa 3D + tablet + panel del juez, pensada para 1920x1080),
`/sim` (la mesa 3D con el panel del juez) o `/tablet` (la tablet v2 de `web/v2/`, la de verdad).
`/?guion=jurado` reproduce sola la secuencia del pitch de principio a fin. Guía de uso: `docs/simulador.md`.

Qué corre en este proceso
-------------------------
- **Física** (`MesaSim`): el SO-101 de MuJoCo integrado a 480 Hz en un hilo propio y las piezas del CAD.
- **Robot** (`guion_robot.crear_ejecutor`): política entrenada si hay checkpoint → replay de un dataset v2 si lo hay
  y tiene la orden → guion (cinemática inversa). Mismo vocabulario que el VLA (`contrato.ORDENES`).
- **La clase v2** (`ClaseSim`): la máquina de estados de la ronda arcade (de facto la tarea 6b para la ronda
  simulada) que habla con la tablet por **`/ws2`** con el protocolo de `web/v2/PROTOCOLO.md`. Reconoce la junta con
  `juntas.reconocer_junta` sobre las poses de la física (lo que daría el estéreo), comprueba el alcance
  (`alcance`), graba la pasada del robot como fantasma (`fantasma`) y puntúa al juez (`puntuacion`), con las frases
  de Chispas (`personaje`) y la voz de `voz` (`POST /api/voz`).
- **El juez con el ratón**: la vista 3D manda la punta de su antorcha (punto de la mesa), el gatillo y los ángulos;
  entran por el mismo camino que la antorcha real (`AntorchaJuezRaton`: lectura de la IMU virtual → `Fusion` →
  marco del cordón de la junta reconocida → `MarcadorEnVivo` → puntos).

WebSockets
----------
- `/ws2`: el de la tablet (`PROTOCOLO.md`).
- `/ws_sim`: el de la vista 3D: recibe todo lo de `/ws2` y además `mundo` a 30 Hz (`MesaSim.instantanea` + la
  antorcha del juez + el marco del cordón + medidas) y `escena` al conectar (cámaras, zona libre, soporte). Órdenes
  propias (campo `orden`): `antorcha_juez {p:[x,y,z] mm mesa, gatillo, trabajo, avance}`, `robot {orden}` (orden
  del vocabulario ya confirmada), `mover_base {x, y, giro}`, `soltar_chapa {x, y, giro}`, `montar_a_mano {junta}`,
  `terminar`, `reiniciar`, `guion {nombre}`, `fps {fps}` (lo que mide el navegador), más todas las de la tablet
  (`jugar`, `confirmar`, `voz`, `iniciales`, `monto_yo`).
HTTP: `/api/mallas` + `/api/mallas.bin` (mallas para three.js), `/api/estado`, `/api/voz`,
`/api/webcam/{a|b}.jpg` (lo que verían las webcams, con `escena_sintetica`).
"""
from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import logging
import os
import re
import time
import warnings
from pathlib import Path

import numpy as np
from aiohttp import WSMsgType, web

from lewelder import contrato as c
from lewelder import juntas
from lewelder.alcance import Alcance
from lewelder.antorcha import LecturaAntorcha, cuaternion_desde_angulos
from lewelder.contrato import LONGITUD_CORDON, N_TRAMOS, TAMANO_TRAMO, Muestra, TipoJunta
from lewelder.fantasma import FANTASMA, JUEZ, Fantasma
from lewelder.fusion import Fusion
from lewelder.guion_robot import NoLlego, crear_ejecutor
from lewelder.mesa_sim import MesaSim, pose_base
from lewelder.metricas import calidad_tramo
from lewelder.personaje import Personaje
from lewelder.puntuacion import MarcadorEnVivo, Ranking, puntuar
from lewelder.voz import (
    DESMONTA,
    JUNTA_DE_ORDEN,
    MONTA_ESQUINA,
    MONTA_T,
    SENALA,
    SUELDA,
    MAX_TEXTO,
    Contexto,
    comprobar,
    contexto_de_escuela,
    interpretar,
)

log = logging.getLogger("lewelder.simulador")
if hasattr(web, "NotAppKeyWarning"):  # claves de texto en la app, como en `servidor.py`
    warnings.filterwarnings("ignore", category=web.NotAppKeyWarning)

RAIZ = Path(__file__).resolve().parents[1]
DIR_WEB = RAIZ / "web"
HZ_MUNDO = 30.0
HZ_ROBOT_TABLET = 10.0
HZ_MUESTRAS = 30.0
HZ_CARRERA = 4.0
T_CUENTA_ATRAS = 3.6  # s entre `cuenta_atras` y `ronda` (la tablet cuenta sola)
T_FIN = 2.0  # s con el gatillo suelto al final del cordón para cerrar la ronda
T_ABANDONO = 8.0
DURACION_MAX_RONDA = 90.0
T_INICIALES = 25.0  # s esperando la firma; luego firma "SIM"
TAM_COLA = 400
FICHAS = {
    "esquina": {"titulo": "Unión en esquina",
                "para_que": "Cerrar cajas y bastidores: dos chapas que se tocan por el canto.",
                "donde_se_usa": "Armarios eléctricos, depósitos, chasis y carrocería.",
                "angulo": "45° entre las dos chapas · 0-20° de empuje · ritmo de 4-6 mm/s"},
    "t": {"titulo": "Unión en T",
          "para_que": "Poner una chapa de pie sobre otra: refuerzos, nervios y soportes.",
          "donde_se_usa": "Estructuras metálicas, barcos, vigas y escaleras.",
          "angulo": "45° entre la base y el alma · 0-20° de empuje · ritmo de 4-6 mm/s"},
}
EMOCION = {"montado": "chulo", "montaje_fallido": "sorprendido", "girar_pieza": "serio", "senalar": "serio",
           "demostrar": "chulo", "reto": "chulo", "juez_gana": "picado", "robot_gana": "chulo", "record": "sorprendido",
           "desmontado": "alegre", "antorcha": "alegre", "ocupado": "serio", "no_aprendido": "serio",
           "sin_junta": "serio", "ya_montada": "alegre", "otra_montada": "serio", "junta_incompleta": "sorprendido"}
TIPO_EVENTO = {"combo": "bueno", "ritmo": "bueno", "quemado": "malo", "sin_apoyo": "malo", "combo_roto": "malo",
               "te_adelanta": "malo", "adelantas": "epico", "perfecta": "epico", "gana_fantasma": "epico"}


# --- poses de la física → poses de `juntas` (el marco de la móvil de juntas.py: X largo, Y grosor, Z alto) --------
_M_A_JUNTAS = np.array([[-1.0, 0.0, 0.0], [0.0, 0.0, 1.0], [0.0, 1.0, 0.0]])


def poses_para_juntas(mesa: MesaSim) -> tuple[juntas.Pose, juntas.Pose]:
    """(base, móvil) como las daría el estéreo, sacadas de la física."""
    b = pose_base(mesa.base)
    m = mesa.chapa.pose
    return juntas.Pose(b.R, b.p), juntas.Pose(m.R @ _M_A_JUNTAS, m.p)


def reconocer(mesa: MesaSim) -> juntas.Junta:
    """Reconocimiento de la junta con las poses reales (adaptador de la tarea 1: con el estéreo de verdad, las poses
    salen de `SeguidorEstereo.procesar`)."""
    base, movil = poses_para_juntas(mesa)
    return juntas.reconocer_junta(base, movil)


# --- antorcha del juez con el ratón --------------------------------------------------------------------------------
class AntorchaJuezRaton:
    """La antorcha del juez movida con el ratón, por el mismo camino que la real: la IMU virtual da el cuaternión de
    los ángulos pedidos, el "estéreo" da la punta solo con el LED encendido (gatillo) y `Fusion` los une."""

    def __init__(self):
        self.fusion = Fusion()
        tara = LecturaAntorcha(0.0, False, cuaternion_desde_angulos(90.0, 0.0), time.monotonic())
        self.fusion.tara(0.0, tara)
        self.t0 = time.monotonic()
        self.ultima: dict | None = None  # lo último que mandó la vista (para pintarlo en las demás)

    def procesar(self, p_mesa, gatillo: bool, trabajo: float, avance: float, junta: juntas.Junta | None,
                 t: float | None = None) -> Muestra | None:
        ahora = time.monotonic()
        t = ahora - self.t0 if t is None else t
        q = cuaternion_desde_angulos(float(trabajo), float(avance))
        self.fusion.anadir_lectura(LecturaAntorcha(t, bool(gatillo), q, ahora))
        posicion = None
        if gatillo and junta is not None and junta.cordon is not None:  # el LED solo luce con el gatillo
            x, y, z = juntas.punta_en_cordon(p_mesa, junta)
            posicion = Muestra(t, x, y, z, False)
        return self.fusion.fusionar(posicion, t, ahora)


def _r(v, n=2):
    return None if v is None else round(float(v), n)


# --- la clase v2 en el simulador -------------------------------------------------------------------------------------
class ClaseSim:
    """Máquina de estados de la ronda arcade sobre la mesa simulada. Todo en el bucle de asyncio."""

    def __init__(self, mesa: MesaSim, ejecutor, alcance: Alcance, *, nivel: str = c.NIVEL_JURADO,
                 ranking: Ranking | None = None, cliente_llm=None, auto: bool = True, semilla: int | None = None,
                 t_cuenta_atras: float = T_CUENTA_ATRAS):
        self.mesa, self.ejecutor, self.alcance = mesa, ejecutor, alcance
        self.nivel = nivel
        self.ranking = ranking or Ranking(None)
        self.cliente_llm = cliente_llm
        self.auto = auto
        self.t_cuenta_atras = t_cuenta_atras
        self.personaje = Personaje(semilla)
        self.tablets: set[asyncio.Queue] = set()
        self.vistas: set[asyncio.Queue] = set()
        self.juez = AntorchaJuezRaton()
        self.nivel_robot = 2  # escalera de alcance: "gira la junta" (nivel 3) aún no
        self.pantalla = "atraccion"
        self.tarea_robot: asyncio.Task | None = None
        self._tareas: set[asyncio.Task] = set()
        self._flujo: asyncio.Task | None = None
        self._director: asyncio.Task | None = None
        self.orden_robot: str | None = None
        self.fase_robot: str | None = None
        self.progreso_robot = 0.0
        self.junta: juntas.Junta | None = None
        self.junta_pedida: str | None = None
        self.fantasma: Fantasma | None = None
        self.puntos_robot: int | None = None
        self.muestras_robot: list[Muestra] = []
        self.marcador: MarcadorEnVivo | None = None
        self.muestras_juez: list[Muestra] = []
        self.ultimo_resultado: dict | None = None
        self._firma: asyncio.Future | None = None
        self._firma_pendiente: str | None = None
        self._ronda_fin: asyncio.Event | None = None
        self._t_ult_soldando: float | None = None
        self._x_ult_soldando = 0.0
        self._t0_ronda: float | None = None
        self._ultimo_envio = {"muestra": 0.0, "carrera": 0.0, "robot": 0.0}
        self.fps_navegador: float | None = None
        self.hz_publicacion = 0.0
        self.alcance_actual: dict | None = None

    # --- difusión ------------------------------------------------------------------------------------------------
    def suscribir(self, vista: bool = False) -> asyncio.Queue:
        cola: asyncio.Queue = asyncio.Queue(maxsize=TAM_COLA)
        (self.vistas if vista else self.tablets).add(cola)
        return cola

    def desuscribir(self, cola) -> None:
        self.tablets.discard(cola)
        self.vistas.discard(cola)

    @staticmethod
    def _poner(cola: asyncio.Queue, texto: str) -> None:
        if cola.full():
            with contextlib.suppress(asyncio.QueueEmpty):
                cola.get_nowait()
        cola.put_nowait(texto)

    def emitir(self, msg: dict) -> None:
        """A las tablets y a las vistas."""
        texto = json.dumps(msg, ensure_ascii=False, separators=(",", ":"))
        for cola in list(self.tablets) + list(self.vistas):
            self._poner(cola, texto)

    def emitir_vistas(self, msg: dict) -> None:
        texto = json.dumps(msg, ensure_ascii=False, separators=(",", ":"))
        for cola in list(self.vistas):
            self._poner(cola, texto)

    def ir_a(self, pantalla: str) -> None:
        self.pantalla = pantalla
        self.emitir({"tipo": "pantalla", "nombre": pantalla})

    def decir(self, evento: str, **datos) -> str:
        frase = self.personaje.frase(evento, **datos)
        self.emitir({"tipo": "personaje", "frase": frase, "emocion": EMOCION.get(evento, "alegre"),
                     "nombre": self.personaje.nombre})
        return frase

    def _tarea(self, corrutina) -> asyncio.Task:
        t = asyncio.create_task(corrutina)
        self._tareas.add(t)
        t.add_done_callback(self._tareas.discard)
        t.add_done_callback(_log_fallo)
        return t

    def saludo(self) -> list[dict]:
        """Lo que recibe una tablet al conectar."""
        msgs = [{"tipo": "pantalla", "nombre": self.pantalla}, self._msg_ranking()]
        if self.junta is not None:
            msgs.append(self._msg_junta(self.junta))
        if self.fantasma is not None:
            msgs.append(self._msg_fantasma())
        return msgs

    # --- estado --------------------------------------------------------------------------------------------------
    @property
    def robot_ocupado(self) -> bool:
        return self.tarea_robot is not None and not self.tarea_robot.done()

    @property
    def junta_montada(self):
        """Para `voz.contexto_de_escuela`: la junta que hay en la base (`TipoJunta`, "incompleta" o None)."""
        j = reconocer(self.mesa)
        if j.completa:
            return j.tipo_junta
        if j.tipo == juntas.EstadoJunta.INCOMPLETA and self.mesa.chapa.estado in ("encima", "montada"):
            return "incompleta"
        return None

    def contexto(self) -> Contexto:
        return Contexto(junta_montada=self.junta_montada, robot_ocupado=self.robot_ocupado,
                        nivel_max=self.nivel_robot)

    def estado(self) -> dict:
        return {"pantalla": self.pantalla, "orden_robot": self.orden_robot, "fase_robot": self.fase_robot,
                "progreso_robot": round(self.progreso_robot, 3), "ocupado": self.robot_ocupado,
                "junta": self.junta.a_dict() if self.junta else None, "alcance": self.alcance_actual,
                "politica": getattr(self.ejecutor, "activo", "guion"), "aviso_politica":
                getattr(self.ejecutor, "aviso", None), "marcador": self.marcador.estado() if self.marcador else None,
                "resultado": self.ultimo_resultado, "hz_fisica": round(self.mesa.hz_medida, 1),
                "hz_publicacion": round(self.hz_publicacion, 1), "fps_navegador": self.fps_navegador,
                "n_muestras_juez": len(self.muestras_juez)}

    def mundo(self) -> dict:
        m = self.mesa.instantanea()
        m["tipo"] = "mundo"
        j = self.junta
        if j is not None and j.cordon is not None:
            m["cordon"] = {"o": [round(v, 2) for v in j.cordon.t], "R": [round(v, 5) for v in j.cordon.R.ravel()],
                           "junta": j.tipo.value if j.completa else (j.candidata.value if j.candidata else None)}
        m["juez"] = self.juez.ultima
        m["pantalla"] = self.pantalla
        m["robot"] = {"orden": self.orden_robot, "fase": self.fase_robot, "progreso": round(self.progreso_robot, 3),
                      "politica": getattr(self.ejecutor, "activo", "guion")}
        m["hz_publicacion"] = round(self.hz_publicacion, 1)
        if self.marcador is not None:
            e = self.marcador.estado()
            m["marcador"] = {"puntos": e["puntos"], "combo": e["combo"], "racha": e["racha"]}
        return m

    def escena(self) -> dict:
        """Lo fijo de la mesa para la vista 3D."""
        from lewelder.escena_sintetica import pose_camara_estereo

        camaras = {}
        for nombre, p in c.CAMARAS_ESTEREO.items():
            pc = pose_camara_estereo(nombre, c.CAMARAS_ESTEREO)
            camaras[nombre] = {"origen": [round(v, 1) for v in pc.centro], "objetivo": list(p["objetivo"]),
                               "fov_h": 70.0, "aspecto": 16 / 9}
        return {"tipo": "escena", "camaras": camaras, "zona_libre": c.ZONA_LIBRE, "soporte": c.SOPORTE_ANTORCHA,
                "base_por_defecto": {"x": c.POSICION_BASE.x, "y": c.POSICION_BASE.y, "giro": c.POSICION_BASE.giro},
                "medidas": {"largo_base": c.LARGO_BASE, "ancho_base": c.ANCHO_BASE, "grosor": c.GROSOR_CHAPA,
                            "largo_movil": c.LARGO_MOVIL, "alto_movil": c.ALTO_MOVIL,
                            "longitud_cordon": LONGITUD_CORDON, "altura_apoyo": c.ALTURA_APOYO},
                "ordenes": list(c.ORDENES), "personaje": self.personaje.info()}

    # --- mensajes de la tablet -------------------------------------------------------------------------------------
    def _msg_junta(self, j: juntas.Junta) -> dict:
        nombre = j.tipo.value if j.completa else "incompleta"
        return {"tipo": "junta", "junta": nombre, "posicion_soldeo": j.posicion or "PB",
                "confianza": round(j.confianza, 2), "motivo": j.motivo,
                "ficha": FICHAS.get(nombre) if j.completa else None}

    def _msg_fantasma(self) -> dict:
        f = self.fantasma
        return {"tipo": "fantasma", "duracion": round(f.duracion, 2),
                "tramos": [{"x0": i * TAMANO_TRAMO, "velocidad": t.velocidad or c.VELOCIDAD_OBJETIVO[0],
                            "angulo": t.angulo_trabajo} for i, t in enumerate(f.tramos)]}

    def _msg_ranking(self, posicion_nueva: int | None = None) -> dict:
        top = [{"iniciales": p.iniciales, "puntos": p.puntos, "junta": p.junta} for p in self.ranking.top()]
        msg = {"tipo": "ranking", "top": top}
        if posicion_nueva:
            msg["posicion_nueva"] = posicion_nueva
        return msg

    # --- órdenes ------------------------------------------------------------------------------------------------
    async def orden(self, msg: dict) -> str | None:
        """Una orden de la tablet o de la vista; devuelve un texto de error o None."""
        o = msg.get("orden")
        if o == "antorcha_juez":
            try:
                self.antorcha_juez([float(v) for v in msg["p"]], bool(msg.get("gatillo")),
                                   float(msg.get("trabajo", 45.0)), float(msg.get("avance", 10.0)))
            except (KeyError, TypeError, ValueError):
                return "antorcha_juez sin p"
            return None
        if o == "jugar":
            self.jugar()
            return None
        if o == "confirmar":
            if msg.get("si") and msg.get("orden_confirmada"):
                return self.pedir_orden(str(msg["orden_confirmada"]))
            self.decir("cancelado")
            return None
        if o == "robot":
            return self.pedir_orden(str(msg.get("orden_robot") or msg.get("texto") or ""))
        if o == "voz":
            await self.voz(str(msg.get("texto", "")))
            return None
        if o == "iniciales":
            self.firmar(str(msg.get("texto", "")))
            return None
        if o == "monto_yo":
            self._lanzar_flujo(self._plan_b())
            return None
        if o == "mover_base":
            self.mesa.mover_base(float(msg["x"]), float(msg["y"]), float(msg.get("giro", 0.0)))
            self._junta_cambiada()
            return None
        if o == "soltar_chapa":
            if not self.mesa.soltar_chapa_en(float(msg["x"]), float(msg["y"]), float(msg.get("giro", 0.0))):
                return "la chapa está en la pinza"
            self._junta_cambiada()
            return None
        if o == "montar_a_mano":
            self.mesa.montar_a_mano(msg.get("junta", "t"))
            self._junta_cambiada()
            return None
        if o == "terminar":
            if self._ronda_fin is not None:
                self._ronda_fin.set()
            return None
        if o == "reiniciar":
            await self.reiniciar()
            return None
        if o == "guion":
            self.lanzar_guion(str(msg.get("nombre", "jurado")), bool(msg.get("bucle")))
            return None
        if o == "fps":
            with contextlib.suppress(TypeError, ValueError):
                self.fps_navegador = round(float(msg.get("fps")), 1)
            return None
        if o in ("estado", "reiniciar_vista"):
            return None
        return f"orden desconocida: {o}"

    def jugar(self) -> None:
        if self.pantalla in ("ronda", "cuenta_atras") or self.robot_ocupado:
            return
        self._cancelar_flujo()
        self.ir_a("pedir")
        self.emitir({"tipo": "personaje", "frase": "¿Qué junta te monto: una T o una esquina?", "emocion": "alegre",
                     "nombre": self.personaje.nombre})

    async def voz(self, texto: str) -> None:
        r = await interpretar(texto, self.contexto(), cliente=self.cliente_llm, personaje=self.personaje)
        if r.respuesta:
            self.emitir({"tipo": "personaje", "frase": r.respuesta, "emocion": "alegre" if r.confirmable else "serio",
                         "nombre": self.personaje.nombre})
        if r.confirmable or r.aclaracion:
            d = r.a_dict()
            self.emitir({"tipo": "orden_propuesta", "texto_oido": texto, "orden": r.orden,
                         "pregunta": r.pregunta or r.aclaracion, "botones": d["botones"]})

    def pedir_orden(self, orden: str) -> str | None:
        """Una orden del vocabulario ya confirmada por el juez."""
        if orden not in c.ORDENES:
            return f"orden fuera del vocabulario: {orden}"
        motivo = comprobar(orden, self.contexto())
        if motivo in ("ya_montada",) and orden in JUNTA_DE_ORDEN:
            self.decir(motivo, junta=JUNTA_DE_ORDEN[orden])
            self.junta_pedida = JUNTA_DE_ORDEN[orden].value
            self._lanzar_flujo(self._tras_montar(JUNTA_DE_ORDEN[orden].value))
            return None
        if motivo == "otra_montada":
            motivo = None  # el guion desmonta y vuelve a montar
        if motivo:
            self.decir(motivo, junta=self.junta_montada if isinstance(self.junta_montada, TipoJunta) else None)
            return None
        if orden in JUNTA_DE_ORDEN:
            self.junta_pedida = JUNTA_DE_ORDEN[orden].value
            self._lanzar_flujo(self._montar(orden))
        elif orden == SENALA:
            self._lanzar_flujo(self._senalar(seguir=False))
        elif orden == SUELDA:
            self._lanzar_flujo(self._demostrar(seguir=self.auto))
        elif orden == DESMONTA:
            self._lanzar_flujo(self._desmontar())
        else:
            self._lanzar_flujo(self._robot_simple(orden))
        return None

    def _cancelar_flujo(self) -> None:
        if self._flujo is not None and not self._flujo.done():
            self._flujo.cancel()
        self._flujo = None

    def _lanzar_flujo(self, corrutina) -> None:
        self._cancelar_flujo()
        self._flujo = self._tarea(corrutina)

    async def reiniciar(self) -> None:
        if self._director is not None and not self._director.done() and asyncio.current_task() is not self._director:
            self._director.cancel()
        self._cancelar_flujo()
        if self.tarea_robot is not None and not self.tarea_robot.done():
            self.ejecutor.parar()
            self.tarea_robot.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await self.tarea_robot
        self.mesa.reiniciar()
        self.marcador = None
        self.fantasma = None
        self.junta = None
        self.alcance_actual = None
        self.orden_robot = self.fase_robot = None
        self.progreso_robot = 0.0
        self.muestras_juez = []
        self.juez.ultima = None
        self.ir_a("atraccion")
        self.emitir(self._msg_ranking())

    # --- robot ------------------------------------------------------------------------------------------------------
    def _avisar(self, fase: str, progreso: float) -> None:
        self.fase_robot, self.progreso_robot = fase, progreso
        if fase == "soldando" and self.mesa.led:
            pose = self.mesa.punta_antorcha()
            if pose is not None and self.junta is not None and self.junta.cordon is not None:
                x, y, z = juntas.punta_en_cordon(pose.p, self.junta)
                d = self.junta.cordon.R.T @ pose.R[:, 2]
                trabajo = float(np.degrees(np.arctan2(-d[2], d[1])))
                avance = float(np.degrees(np.arctan2(d[0], -d[2])))
                t = self.mesa.t
                if not self.muestras_robot or t > self.muestras_robot[-1].t:
                    self.muestras_robot.append(Muestra(t, x, y, z, True, trabajo, avance))
        ahora = time.monotonic()
        if ahora - self._ultimo_envio["robot"] >= 1.0 / HZ_ROBOT_TABLET:
            self._ultimo_envio["robot"] = ahora
            msg = {"tipo": "robot", "tarea": self.orden_robot, "fase": fase, "progreso": round(progreso, 3)}
            if self.pantalla == "demostracion":
                x = self.muestras_robot[-1].x if self.muestras_robot and self.mesa.led else (
                    LONGITUD_CORDON if self.muestras_robot else 0.0)
                msg["progreso"] = round(float(np.clip(x / LONGITUD_CORDON, 0.0, 1.0)), 3)
            self.emitir(msg)

    async def robot(self, orden: str) -> bool:
        """Ejecuta una orden con el ejecutor (espera a que acabe). True si la ha hecho."""
        if self.robot_ocupado:
            return False
        self.orden_robot, self.fase_robot, self.progreso_robot = orden, "buscando", 0.0
        self.tarea_robot = asyncio.create_task(self.ejecutor.ejecutar(orden, self._avisar))
        try:
            ok = await self.tarea_robot
        except NoLlego as e:
            log.info("el robot no puede «%s»: %s", orden, e)
            self.emitir_vistas({"tipo": "aviso_sim", "texto": f"Chispas no puede: {e}"})
            ok = False
        finally:
            self.fase_robot = None
        self.emitir({"tipo": "robot", "tarea": orden, "fase": "hecho", "progreso": 1.0})
        return ok

    async def _robot_simple(self, orden: str) -> None:
        if orden == "acércame la antorcha":
            self.decir("antorcha")
        await self.robot(orden)

    # --- flujo de la clase ---------------------------------------------------------------------------------------
    def _junta_cambiada(self) -> None:
        """Tras una perturbación: se vuelve a reconocer la junta y su alcance (si ya se había reconocido)."""
        if self.junta is not None:
            self.junta = reconocer(self.mesa)
            self.emitir(self._msg_junta(self.junta))
            if self.junta.completa:
                self._tarea(self._comprobar_alcance())

    async def _comprobar_alcance(self) -> bool:
        # En un hilo: la primera consulta (y la búsqueda de la propuesta) tarda y no debe parar la publicación.
        r = await asyncio.to_thread(self.alcance.comprobar, self.junta.tipo_junta, self.mesa.base)
        prop = r.propuesta
        self.alcance_actual = {"tipo": "alcance", "llega": bool(r.llega), "texto": r.frase or None,
                               "giro_grados": prop.giro if prop else None}
        self.emitir(self.alcance_actual)
        return bool(r.llega)

    async def _montar(self, orden: str) -> None:
        junta = JUNTA_DE_ORDEN[orden].value
        self.ir_a("montaje")
        self.junta, self.fantasma = None, None
        ok = await self.robot(orden)
        j = reconocer(self.mesa)
        if not ok or not j.completa or j.tipo.value != junta:
            self.decir("montaje_fallido")
            self.junta = j if j.tipo != juntas.EstadoJunta.SIN_MOVIL else None
            if self.junta is not None:
                self.emitir(self._msg_junta(j))
            await asyncio.sleep(2.5)
            self.ir_a("pedir")
            return
        self.decir("montado", junta=junta)
        await asyncio.sleep(1.5)
        await self._tras_montar(junta)

    async def _plan_b(self) -> None:
        self.ir_a("plan_b")
        while True:
            j = reconocer(self.mesa)
            if j.completa:
                break
            await asyncio.sleep(0.3)
        await self._tras_montar(j.tipo.value)

    async def _tras_montar(self, junta: str) -> None:
        """Reconocer → alcance (y esperar a que la giren) → señalar → demostrar → ronda."""
        self.junta = reconocer(self.mesa)
        self.ir_a("reconocer")
        self.emitir(self._msg_junta(self.junta))
        await asyncio.sleep(0.6)
        llega = await self._comprobar_alcance()
        if not llega:
            self.decir("girar_pieza")
            while not llega:  # el juez mueve la base en la vista 3D; cada cambio se vuelve a comprobar
                await asyncio.sleep(0.5)
                j = reconocer(self.mesa)
                if j.completa:
                    self.junta = j
                    r = await asyncio.to_thread(self.alcance.comprobar, j.tipo_junta, self.mesa.base, proponer=False)
                    llega = bool(r.llega)
            self.emitir(self._msg_junta(self.junta))
            await self._comprobar_alcance()
        await asyncio.sleep(2.5)
        if self.auto:
            await self._senalar(seguir=True)

    async def _senalar(self, seguir: bool) -> None:
        if self.junta is None or not self.junta.completa:
            self.decir("sin_junta")
            return
        self.decir("senalar")
        await self.robot(SENALA)
        if seguir:
            await self._demostrar(seguir=True)

    async def _demostrar(self, seguir: bool) -> None:
        self.junta = reconocer(self.mesa)
        if not self.junta.completa:
            self.decir("sin_junta")
            return
        self.ir_a("demostracion")
        self.decir("demostrar", junta=self.junta.tipo_junta)
        self.muestras_robot = []
        ok = await self.robot(SUELDA)
        if not ok or not self.muestras_robot:
            self.decir("montaje_fallido")
            return
        self.fantasma = Fantasma(self.muestras_robot, self.junta.tipo_junta, self.nivel)
        self.puntos_robot = puntuar(self.fantasma.resultado).total
        self.emitir(self._msg_fantasma())
        self.decir("reto", junta=self.junta.tipo_junta)
        if seguir:
            await asyncio.sleep(2.0)
            await self._ronda()

    async def _ronda(self) -> None:
        self.ir_a("cuenta_atras")
        await asyncio.sleep(self.t_cuenta_atras)
        self.marcador = MarcadorEnVivo(self.junta.tipo_junta, self.nivel, fantasma=self.fantasma)
        self.muestras_juez = []
        self._t_ult_soldando, self._t0_ronda = None, time.monotonic()
        self._ronda_fin = asyncio.Event()
        self.ir_a("ronda")
        self.emitir({"tipo": "puntos", "total": 0, "combo": 0, "multiplicador": 1})
        vigilante = self._tarea(self._vigilar_ronda())
        await self._ronda_fin.wait()
        vigilante.cancel()
        await self._terminar_ronda()

    async def _vigilar_ronda(self) -> None:
        while True:
            await asyncio.sleep(0.25)
            ahora = time.monotonic()
            if ahora - self._t0_ronda > DURACION_MAX_RONDA:
                break
            if self._t_ult_soldando is None:
                continue
            pausa = ahora - self._t_ult_soldando
            if (pausa >= T_FIN and self._x_ult_soldando >= LONGITUD_CORDON - 2 * TAMANO_TRAMO) or pausa >= T_ABANDONO:
                break
        self._ronda_fin.set()

    def antorcha_juez(self, p, gatillo: bool, trabajo: float, avance: float) -> None:
        """Una lectura de la antorcha del juez (ratón o guion): pinta y, en la ronda, puntúa."""
        junta = self.junta if self.junta is not None and self.junta.cordon is not None else None
        apoyada = None
        if junta is not None:
            apoyada = juntas.apoyada(juntas.punta_en_cordon(p, junta)[2])
        self.juez.ultima = {"p": [round(v, 1) for v in p], "gatillo": gatillo, "trabajo": round(trabajo, 1),
                            "avance": round(avance, 1), "apoyada": apoyada}
        m = self.juez.procesar(p, gatillo, trabajo, avance, junta)
        if m is None or self.pantalla != "ronda" or self.marcador is None:
            return
        self.muestras_juez.append(m)
        eventos = self.marcador.anadir(m)
        ev = self.marcador.evaluador
        sobre = m.z <= ev.apoyo
        if m.gatillo and sobre and 0.0 <= m.x <= LONGITUD_CORDON:
            self._t_ult_soldando, self._x_ult_soldando = time.monotonic(), m.x
        ahora = time.monotonic()
        if ahora - self._ultimo_envio["muestra"] >= 1.0 / HZ_MUESTRAS or not m.gatillo:
            self._ultimo_envio["muestra"] = ahora
            self.emitir({"tipo": "muestra", "t": _r(m.t, 3), "x": _r(m.x), "y": _r(m.y), "z": _r(m.z),
                         "apoyada": bool(sobre), "gatillo": bool(m.gatillo), "calidad": self._calidad(m, sobre)})
        for e in eventos:
            msg = {"tipo": "puntos", "total": int(max(0, self.marcador.puntos)), "combo": self.marcador._racha.racha,
                   "multiplicador": self.marcador._racha.multiplicador}
            if e.tipo in TIPO_EVENTO:
                msg["evento"] = {"texto": e.texto, "tipo": TIPO_EVENTO[e.tipo]}
            self.emitir(msg)
        if self.marcador.carrera is not None and ahora - self._ultimo_envio["carrera"] >= 1.0 / HZ_CARRERA:
            self._ultimo_envio["carrera"] = ahora
            e = self.marcador.carrera.estado()
            if e.get("ventaja_mm") is not None:
                self.emitir({"tipo": "fantasma_vivo", "ventaja_mm": e["ventaja_mm"], "ventaja_s": e["ventaja_s"],
                             "va_ganando": "robot" if e["va_ganando"] == FANTASMA else "juez"})

    def _calidad(self, m: Muestra, apoyada: bool) -> str:
        if not (m.gatillo and apoyada):
            return "suelto"
        ev = self.marcador.evaluador
        if ev.en_parada:
            return "quemado"
        malo = ev.velocidad_fiable and not (c.VELOCIDAD_OBJETIVO[0] * 0.8 <= ev.velocidad <=
                                            c.VELOCIDAD_OBJETIVO[1] * 1.2)
        return "regular" if abs(m.y) > ev.tolerancia or malo else "bien"

    async def _terminar_ronda(self) -> None:
        self._ronda_fin = None
        marcador = self.marcador
        p = marcador.terminar()
        r = marcador.evaluador.terminar()
        tol = r.tolerancia_mm
        tramos = [calidad_tramo(tr, tol) if tr.cubierto else None for tr in r.tramos]
        n_sold = max(1, len([m for m in self.muestras_juez if m.gatillo]))
        apoyo = 1.0 - min(1.0, r.tiempo_sin_apoyo_s / max(r.duracion_s + r.tiempo_sin_apoyo_s, 1e-6)) \
            if n_sold else 0.0
        record = self.ranking.es_record(p.total)
        resultado = {
            "tipo": "resultado", "puntos": p.total, "nota": r.nota,
            "metricas": {"cobertura": round(r.cobertura_pct / 100, 3),
                         "ritmo": round(r.pct_tiempo_velocidad_ok / 100, 3), "quemados": r.n_quemados,
                         "desvio": round(r.desvio_medio_mm, 1),
                         "angulo": _r(r.angulo_trabajo_medio, 0) if r.angulo_trabajo_medio is not None else None,
                         "apoyo": round(apoyo, 3)},
            "tramos": [None if q is None else round(q, 3) for q in tramos],
            "gana_al_robot": bool(p.gana_fantasma or (self.puntos_robot is not None and p.total >= self.puntos_robot)),
            "record": record, "entra_en_ranking": self.ranking.posicion(p.total) is not None,
            "puntos_robot": self.puntos_robot,
        }
        self.ultimo_resultado = resultado
        self.ir_a("resultado")
        self.emitir(resultado)
        evento = Personaje.reaccion_puntuacion(p.total, self.puntos_robot,
                                               self.ranking.record.puntos + 1 if self.ranking.record else None)
        if evento == "record" and not record:
            evento = "juez_gana"
        self.decir(evento, puntos=p.total, diferencia=p.total - (self.puntos_robot or 0))
        await asyncio.sleep(4.5)
        self.ir_a("iniciales")
        self.emitir({"tipo": "puntos", "total": p.total, "combo": 0, "multiplicador": 1})
        self._firma = asyncio.get_running_loop().create_future()
        if self._firma_pendiente:
            self._firma.set_result(self._firma_pendiente)
            self._firma_pendiente = None
        try:
            iniciales = await asyncio.wait_for(self._firma, T_INICIALES)
        except asyncio.TimeoutError:
            iniciales = "SIM"
        self._firma = None
        junta = self.junta.tipo_junta if self.junta and self.junta.completa else "t"
        resumen = self.ranking.anotar_ronda(iniciales, p.total, junta, self.nivel, r.aprobado)
        if resumen.insignia_nueva:
            resultado["insignia"] = {"nombre": resumen.insignia_nueva, "nivel": self.nivel}
        self.emitir(self._msg_ranking(resumen.posicion))
        self.ir_a("ranking")

    def firmar(self, texto: str) -> None:
        ini = "".join(ch for ch in texto.upper() if ch.isalpha())[:3]
        if len(ini) != 3:
            return
        if self._firma is not None and not self._firma.done():
            self._firma.set_result(ini)
        elif self.pantalla == "resultado":
            self._firma_pendiente = ini  # firmó antes de que saliera la pantalla de iniciales

    async def _desmontar(self) -> None:
        self.ir_a("montaje")
        ok = await self.robot(DESMONTA)
        if ok:
            self.decir("desmontado")
        self.junta, self.fantasma, self.alcance_actual = None, None, None
        await asyncio.sleep(1.0)
        self.ir_a("pedir")

    # --- guion del jurado --------------------------------------------------------------------------------------------
    def lanzar_guion(self, nombre: str, bucle: bool = False) -> None:
        if self._director is not None and not self._director.done():
            return
        self._director = self._tarea(self._guion_jurado(bucle))

    async def _guion_jurado(self, bucle: bool) -> None:
        """La secuencia del pitch: el juez pide una esquina, el robot la monta, la señala, la suelda y el juez
        (virtual, por el mismo camino que el ratón) suelda contra el fantasma, firma y entra en el ranking."""
        while True:
            await self.reiniciar()
            await asyncio.sleep(2.0)
            self.jugar()
            await asyncio.sleep(2.0)
            texto = "¡Móntame una esquina!"
            self.emitir_vistas({"tipo": "aviso_sim", "texto": f"Juez: «{texto}»"})
            await self.voz(texto)
            await asyncio.sleep(2.5)
            self.emitir({"tipo": "pantalla", "nombre": "pedir"})
            self.pedir_orden(MONTA_ESQUINA)
            while self.pantalla != "ronda":
                if self._flujo is None or self._flujo.done():
                    return
                await asyncio.sleep(0.2)
            await asyncio.sleep(1.0)
            await self.soldar_virtual()
            while self.pantalla != "iniciales":
                await asyncio.sleep(0.2)
            await asyncio.sleep(3.0)
            self.firmar("JUR")
            while self.pantalla != "ranking":
                await asyncio.sleep(0.2)
            if not bucle:
                return
            await asyncio.sleep(8.0)

    async def soldar_virtual(self, velocidad: float = 4.8, semilla: int = 3, hz: float = 50.0) -> None:
        """El juez virtual del guion: acerca la antorcha, suelda el cordón entero con algo de temblor y la retira."""
        if self.junta is None or self.junta.cordon is None:
            return
        rng = np.random.default_rng(semilla)
        cordon = self.junta.cordon

        def punto(x, y, z):
            return cordon.aplicar([x, y, z])

        periodo = 1.0 / hz
        for k in range(int(1.0 * hz)):  # se acerca
            s = k / hz
            self.antorcha_juez(punto(-8.0, -20 * (1 - s), 30 * (1 - s) + 0.5), False, 45.0, 10.0)
            await asyncio.sleep(periodo)
        x, deriva = -3.0, 0.0
        while x < LONGITUD_CORDON + 3.0 and self.pantalla == "ronda":
            deriva = 0.9 * deriva + rng.normal(0, 0.25)
            v = velocidad * (1 + 0.05 * np.sin(x / 9.0))
            x += v * periodo
            self.antorcha_juez(punto(x, 0.6 * deriva, 0.5 + abs(rng.normal(0, 0.15))), True,
                               45.0 + rng.normal(0, 2.0), 10.0 + rng.normal(0, 2.0))
            await asyncio.sleep(periodo)
        for k in range(int(3.0 * hz)):  # suelta el gatillo y se queda al final
            if self.pantalla != "ronda":
                break
            self.antorcha_juez(punto(LONGITUD_CORDON + 3.0, 0.0, 0.5 + 12 * min(1.0, k / hz)), False, 45.0, 10.0)
            await asyncio.sleep(periodo)

    # --- ciclo de vida ----------------------------------------------------------------------------------------------
    async def publicar(self) -> None:
        """El mundo a las vistas a `HZ_MUNDO`."""
        periodo = 1.0 / HZ_MUNDO
        siguiente = time.perf_counter()
        n, t0 = 0, time.perf_counter()
        while True:
            if self.vistas:
                self.emitir_vistas(self.mundo())
            n += 1
            ahora = time.perf_counter()
            if ahora - t0 >= 1.0:
                self.hz_publicacion, n, t0 = n / (ahora - t0), 0, ahora
            siguiente += periodo
            await asyncio.sleep(max(0.0, siguiente - time.perf_counter()))
            if time.perf_counter() - siguiente > 0.5:
                siguiente = time.perf_counter()

    async def cerrar(self) -> None:
        self.ejecutor.parar()
        for t in list(self._tareas) + [x for x in (self.tarea_robot,) if x is not None]:
            t.cancel()
        for t in list(self._tareas):
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await t


def _log_fallo(tarea: asyncio.Task) -> None:
    if not tarea.cancelled() and tarea.exception() is not None:
        log.error("tarea del simulador fallida", exc_info=tarea.exception())


# --- partidas (varias sesiones a la vez) ------------------------------------------------------------------------------
PARTIDA_PRINCIPAL = "principal"
MAX_PARTIDAS = int(os.environ.get("LEWELDER_MAX_PARTIDAS", "6"))
INACTIVIDAD = 600.0  # s sin nadie conectado: la partida se cierra (salvo la principal)
_ID_VALIDO = re.compile(r"^[A-Za-z0-9_-]{1,40}$")


class Partida:
    """Una partida: su mesa (física en su hilo), su robot y su clase, y quién la mira."""

    def __init__(self, ident: str, clase: ClaseSim):
        self.id, self.clase = ident, clase
        self.conectados = 0
        self.ultima_actividad = time.monotonic()
        self.publicar: asyncio.Task | None = None

    async def arrancar(self) -> None:
        if self.clase.mesa.tiempo_real:  # (en las pruebas la física la avanza quien prueba)
            self.clase.mesa.iniciar()
        self.publicar = asyncio.create_task(self.clase.publicar())

    async def cerrar(self) -> None:
        if self.publicar is not None:
            self.publicar.cancel()
        await self.clase.cerrar()
        self.clase.mesa.parar()


class Partidas:
    """Las partidas abiertas. Modo `una`: todos comparten la principal (la demo en el portátil, con la tablet de verdad
    al lado). Modo `por_pestana`: cada pestaña del navegador trae su `?partida=ID` y tiene su propia física, robot y
    puntuación (el Space de Hugging Face); con `MAX_PARTIDAS` llenas, las nuevas entran en la principal como
    compartida (la vista lo avisa). El ranking del día es común a todas."""

    def __init__(self, fabrica, modo: str = "una", maximo: int = MAX_PARTIDAS):
        self.fabrica, self.modo, self.maximo = fabrica, modo, maximo
        self.abiertas: dict[str, Partida] = {}
        self._creando: dict[str, asyncio.Task] = {}

    def resolver(self, pedida: str | None) -> tuple[str, bool]:
        """(id de la partida, compartida) para lo que pide una conexión."""
        if self.modo != "por_pestana" or not pedida or not _ID_VALIDO.match(pedida):
            return PARTIDA_PRINCIPAL, self.modo != "por_pestana"
        if pedida in self.abiertas or pedida in self._creando or len(self.abiertas) < self.maximo:
            return pedida, False
        return PARTIDA_PRINCIPAL, True

    async def obtener(self, ident: str) -> Partida:
        if ident in self.abiertas:
            return self.abiertas[ident]
        if ident not in self._creando:
            async def crear():
                clase = await asyncio.to_thread(self.fabrica)
                p = Partida(ident, clase)
                await p.arrancar()
                self.abiertas[ident] = p
                log.info("partida %s abierta (%d en marcha)", ident, len(self.abiertas))
                return p
            self._creando[ident] = asyncio.create_task(crear())
        try:
            return await asyncio.shield(self._creando[ident])
        finally:
            if self._creando.get(ident) is not None and self._creando[ident].done():
                self._creando.pop(ident, None)

    def de_peticion(self, request: web.Request) -> str:
        """Partida de una petición HTTP: `?partida=` o, si no, la de la página que la hace (Referer)."""
        pedida = request.query.get("partida")
        if pedida is None and request.headers.get("Referer"):
            from urllib.parse import parse_qs, urlparse

            pedida = (parse_qs(urlparse(request.headers["Referer"]).query).get("partida") or [None])[0]
        return self.resolver(pedida)[0]

    async def limpiar(self) -> None:
        while True:
            await asyncio.sleep(30.0)
            ahora = time.monotonic()
            for ident, p in list(self.abiertas.items()):
                if ident != PARTIDA_PRINCIPAL and p.conectados == 0 and ahora - p.ultima_actividad > INACTIVIDAD:
                    self.abiertas.pop(ident, None)
                    await p.cerrar()
                    log.info("partida %s cerrada por inactividad", ident)

    async def cerrar(self) -> None:
        for p in list(self.abiertas.values()):
            await p.cerrar()
        self.abiertas.clear()


# --- aplicación web -------------------------------------------------------------------------------------------------
async def _ws(request: web.Request, vista: bool) -> web.WebSocketResponse:
    partidas: Partidas = request.app["partidas"]
    ident, compartida = partidas.resolver(request.query.get("partida"))
    ws = web.WebSocketResponse(heartbeat=10.0, max_msg_size=1 << 20)
    await ws.prepare(request)
    partida = await partidas.obtener(ident)
    clase = partida.clase
    partida.conectados += 1
    cola = clase.suscribir(vista)
    if vista:
        escena = clase.escena()
        escena.update(partida=ident, compartida=compartida, modo_partidas=partidas.modo,
                      conectados=partida.conectados)
        await ws.send_str(json.dumps(escena, ensure_ascii=False))
    for msg in clase.saludo():
        await ws.send_str(json.dumps(msg, ensure_ascii=False))

    async def enviar():
        while True:
            await ws.send_str(await cola.get())

    emisor = asyncio.create_task(enviar())
    try:
        async for mensaje in ws:
            if mensaje.type != WSMsgType.TEXT:
                continue
            partida.ultima_actividad = time.monotonic()
            try:
                datos = json.loads(mensaje.data)
                if not isinstance(datos, dict):
                    raise ValueError
                error = await clase.orden(datos)
            except (ValueError, KeyError, TypeError) as e:
                error = f"mensaje no válido: {e}"
            if error:
                await ws.send_str(json.dumps({"tipo": "error", "texto": error}, ensure_ascii=False))
    finally:
        emisor.cancel()
        with contextlib.suppress(asyncio.CancelledError, Exception):
            await emisor
        clase.desuscribir(cola)
        partida.conectados -= 1
        partida.ultima_actividad = time.monotonic()
    return ws


async def _ws2(request):
    return await _ws(request, vista=False)


async def _ws_sim(request):
    return await _ws(request, vista=True)


def _pagina(nombre: str):
    async def manejador(request: web.Request) -> web.FileResponse:
        return web.FileResponse(request.app["dir_web"] / "sim" / nombre)
    return manejador


async def _tablet(request: web.Request):
    destino = "/v2/index.html" if (request.app["dir_web"] / "v2" / "index.html").exists() else "/index.html"
    if request.query_string:
        destino += "?" + request.query_string
    raise web.HTTPFound(destino)


async def _clase(request: web.Request) -> ClaseSim:
    partidas: Partidas = request.app["partidas"]
    return (await partidas.obtener(partidas.de_peticion(request))).clase


def _mallas_de(app) -> tuple[dict, bytes]:
    cache = app["cache"]
    if "mallas" not in cache:
        cache["mallas"] = app["mesa_mallas"]().mallas()
    return cache["mallas"]


async def _mallas(request: web.Request):
    return web.json_response((await asyncio.to_thread(_mallas_de, request.app))[0])


async def _mallas_bin(request: web.Request):
    datos = (await asyncio.to_thread(_mallas_de, request.app))[1]
    return web.Response(body=datos, content_type="application/octet-stream")


async def _estado(request: web.Request):
    partidas: Partidas = request.app["partidas"]
    clase = await _clase(request)
    e = clase.estado()
    e["partidas"] = {"modo": partidas.modo, "abiertas": len(partidas.abiertas), "maximo": partidas.maximo}
    return web.json_response(e)


async def _voz(request: web.Request):
    """`POST /api/voz` (el de `voz.api_voz`) con el contexto de la partida de quien pregunta."""
    try:
        datos = await request.json()
    except (ValueError, UnicodeDecodeError):
        return web.json_response({"error": "el cuerpo no es JSON"}, status=400)
    if not isinstance(datos, dict) or not isinstance(datos.get("texto"), str) or len(datos["texto"]) > MAX_TEXTO:
        return web.json_response({"error": "falta el texto o es demasiado largo"}, status=400)
    clase = await _clase(request)
    alternativas = [a for a in (datos.get("alternativas") or []) if isinstance(a, str) and len(a) <= MAX_TEXTO]
    ctx = Contexto.de_dict(datos.get("contexto"), base=contexto_de_escuela(clase))
    r = await interpretar(datos["texto"], ctx, cliente=clase.cliente_llm, personaje=clase.personaje,
                          alternativas=alternativas[:5])
    return web.json_response({**r.a_dict(), "personaje": clase.personaje.info()})


async def _webcam(request: web.Request):
    """Lo que vería la webcam A o B ahora (render de `escena_sintetica` con las mallas del CAD, sin ruido)."""
    import cv2

    from lewelder.escena_sintetica import EscenaSintetica, pose_camara_estereo

    nombre = request.match_info["cual"]
    if nombre not in c.CAMARAS_ESTEREO:
        raise web.HTTPNotFound()
    clase = await _clase(request)
    cache = request.app["cache"]
    if "escena_sintetica" not in cache:
        cache["escena_sintetica"] = EscenaSintetica(
            {k: pose_camara_estereo(k, c.CAMARAS_ESTEREO) for k in c.CAMARAS_ESTEREO}, ancho=960, alto=540,
            geometria="cad")
    escena = cache["escena_sintetica"]
    base, movil = poses_para_juntas(clase.mesa)
    led = None
    if clase.juez.ultima and clase.juez.ultima.get("gatillo"):
        led = np.array(clase.juez.ultima["p"])
    a, b, _ = await asyncio.to_thread(escena.renderizar, base, movil, led, ruido=False)
    _, jpg = cv2.imencode(".jpg", a if nombre == "a" else b, [cv2.IMWRITE_JPEG_QUALITY, 80])
    return web.Response(body=jpg.tobytes(), content_type="image/jpeg")


@web.middleware
async def _sin_cache(request, handler):
    respuesta = await handler(request)
    respuesta.headers["Cache-Control"] = "no-store"
    return respuesta


def crear_app(fabrica, dir_web: Path = DIR_WEB, iniciar: bool = True, modo: str = "una",
              maximo: int = MAX_PARTIDAS) -> web.Application:
    """Aplicación aiohttp. `fabrica`: una `ClaseSim` ya hecha (una sola partida, para pruebas) o una función que
    crea una nueva por partida (`modo="por_pestana"`)."""
    app = web.Application(middlewares=[_sin_cache])
    if isinstance(fabrica, ClaseSim):
        hecha = fabrica
        partidas = Partidas(lambda: hecha, "una", 1)
        app["mesa_mallas"] = lambda: hecha.mesa
    else:
        partidas = Partidas(fabrica, modo, maximo)
        app["mesa_mallas"] = MesaSim
    app["partidas"] = partidas
    app["dir_web"] = Path(dir_web)
    app["cache"] = {}  # mallas, render de las webcams y tareas (la app no se toca una vez arrancada)
    app.router.add_get("/ws2", _ws2)
    app.router.add_get("/ws_sim", _ws_sim)
    app.router.add_get("/", _pagina("index.html"))
    app.router.add_get("/sim", _pagina("sim.html"))
    app.router.add_get("/tablet", _tablet)
    app.router.add_get("/api/estado", _estado)
    app.router.add_get("/api/mallas", _mallas)
    app.router.add_get("/api/mallas.bin", _mallas_bin)
    app.router.add_get("/api/webcam/{cual}.jpg", _webcam)
    app.router.add_post("/api/voz", _voz)
    app.router.add_static("/", Path(dir_web), follow_symlinks=False)

    async def arrancar(app):
        if iniciar:
            await partidas.obtener(PARTIDA_PRINCIPAL)
        app["cache"]["limpiar"] = asyncio.create_task(partidas.limpiar())

    async def parar(app):
        app["cache"]["limpiar"].cancel()
        await partidas.cerrar()

    app.on_startup.append(arrancar)
    app.on_cleanup.append(parar)
    return app


def crear_clase(args=None, *, ranking: Ranking | None = None, cliente_llm=None) -> ClaseSim:
    """Una partida: mesa, robot (con su respaldo) y clase. No importa torch ni LeRobot salvo que haya política."""
    mesa = MesaSim()
    alcance = Alcance()
    kw = {}
    if args is not None:
        kw = {"checkpoint_vla": args.checkpoint_vla, "checkpoint_act": args.checkpoint_act,
              "dataset": args.dataset, "dispositivo": args.dispositivo, "escala_tiempo": args.escala_robot}
    ejecutor = crear_ejecutor(mesa, alcance, **kw)
    return ClaseSim(mesa, ejecutor, alcance, ranking=ranking or Ranking(None), cliente_llm=cliente_llm,
                    auto=not getattr(args, "manual", False))


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description="Simulador de la demo LeWelder v2 (http://localhost:PUERTO/)")
    p.add_argument("--puerto", type=int, default=int(os.environ.get("PORT", "8080")),
                   help="puerto (por defecto $PORT o 8080; Hugging Face Spaces usa 7860)")
    p.add_argument("--host", default="0.0.0.0")
    p.add_argument("--partidas", choices=["una", "por_pestana"], default=os.environ.get("LEWELDER_PARTIDAS", "una"),
                   help="una: todos comparten la partida (demo local con la tablet de verdad); por_pestana: cada "
                        "pestaña la suya (Space)")
    p.add_argument("--max-partidas", type=int, default=MAX_PARTIDAS)
    p.add_argument("--guion", choices=["jurado"], default=None, help="arranca reproduciendo la secuencia del pitch")
    p.add_argument("--checkpoint-vla", default=None, help="SmolVLA v2 (multitarea) para mover el robot")
    p.add_argument("--checkpoint-act", default=None)
    p.add_argument("--dataset", default=None, help="LeRobotDataset v2 para el replay (episodios con la orden)")
    p.add_argument("--dispositivo", default="cpu")
    p.add_argument("--escala-robot", type=float, default=1.0, help=">1 acelera el robot del guion")
    p.add_argument("--manual", action="store_true", help="sin encadenar señalar → demostrar → ronda tras montar")
    p.add_argument("--sin-llm", action="store_true", help="voz y frases solo por reglas")
    p.add_argument("--ranking", default=c.RUTA_RANKING, help="JSON del ranking del día (relativo al repo)")
    args = p.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logging.getLogger("aiohttp.access").setLevel(logging.WARNING)
    ranking = Ranking(RAIZ / args.ranking)
    cliente = None
    if not args.sin_llm:
        from lewelder.instructor import crear_cliente_llm

        cliente = crear_cliente_llm()
    app = crear_app(lambda: crear_clase(args, ranking=ranking, cliente_llm=cliente), modo=args.partidas,
                    maximo=args.max_partidas)

    async def preparar(app):
        # La tabla de alcance tarda unos segundos la primera vez (se cachea en salidas/alcance).
        principal = await app["partidas"].obtener(PARTIDA_PRINCIPAL)
        await asyncio.to_thread(principal.clase.alcance.preparar)
        if args.guion:
            principal.clase.lanzar_guion(args.guion)
    app.on_startup.append(preparar)
    print(f"LeWelder · simulador en http://localhost:{args.puerto}/  (/sim mesa 3D, /tablet tablet, "
          f"?guion=jurado demo del pitch · partidas: {args.partidas})", flush=True)
    web.run_app(app, host=args.host, port=args.puerto, print=None)


if __name__ == "__main__":
    main()
