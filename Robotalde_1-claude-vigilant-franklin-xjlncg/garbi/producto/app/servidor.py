"""Servidor web de la app de Garbi.

**aiohttp** y no FastAPI: ya está en las dependencias del proyecto (no hay que instalar nada en el portátil del
hackathon), sirve el vídeo MJPEG con un `StreamResponse` sin más piezas, y su `AppRunner` se arranca en un hilo con su
propio bucle asyncio, así que el bucle de control a 30 Hz nunca espera al servidor. Las llamadas que pueden tardar
(codificar JPEG, preguntar a Claude) van a un hilo aparte con `asyncio.to_thread`.

Rutas:
    GET  /                    la página (static/index.html)
    GET  /api/estado          EstadoApp en JSON + tecnologías de la app (LLM, seta)
    POST /api/comando         {"comando": "encender" | "apagar" | ... }      → 400 si no existe
    POST /api/emergencia      seta / botón rojo: Comando.EMERGENCIA al instante
    POST /api/chat            {"texto": "..."} → {"respuesta", "comandos", "fuente"}
    POST /api/foco_chat       {"foco": true|false}: mientras se escribe, la seta global no dispara
    GET  /video/{camara}      MJPEG de "top" o "wrist" con las detecciones
    GET  /foto/{camara}       un JPEG suelto
    GET  /api/registro.csv    indicadores y eventos de la sesión en CSV (trazabilidad, como un MES)
"""
from __future__ import annotations

import asyncio
import json
import logging
import threading
import time
from datetime import datetime
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np
from aiohttp import web

from garbi.producto.app.indicadores import Indicadores, Registro
from garbi.producto.app.llm import AsistenteGarbi
from garbi.producto.app.puente import Orquestador, a_jpeg
from garbi.producto.contrato import Comando, EstadoApp

log = logging.getLogger(__name__)

ESTATICOS = Path(__file__).parent / "static"
CAMARAS = ("top", "wrist")
FPS_VIDEO = 15
FOCO_CHAT_MAX = 120.0   # s: si la página no avisa de que suelta el chat, la seta global vuelve sola


class CacheImagenes:
    """Pide las imágenes al orquestador y las codifica como mucho `fps` veces por segundo, para todos los clientes."""

    def __init__(self, orquestador: Orquestador, fps: float = 20.0):
        self.orquestador = orquestador
        self.periodo = 1.0 / fps
        self._t = -1e9
        self._jpgs: dict[str, bytes | None] = {}
        self._cerrojo = threading.Lock()

    def jpeg(self, camara: str) -> bytes:
        with self._cerrojo:
            if time.monotonic() - self._t >= self.periodo:
                try:
                    imagenes = self.orquestador.imagenes_anotadas() or {}
                except Exception:
                    log.exception("imagenes_anotadas() ha fallado")
                    imagenes = {}
                self._jpgs = {c: a_jpeg(imagenes.get(c)) for c in CAMARAS}
                self._t = time.monotonic()
            return self._jpgs.get(camara) or _sin_senal(camara)


_SIN_SENAL: dict[str, bytes] = {}


def _sin_senal(camara: str) -> bytes:
    if camara not in _SIN_SENAL:
        img = np.full((480, 640, 3), 32, np.uint8)
        texto = f"{camara}: sin senal"
        (tw, _), _ = cv2.getTextSize(texto, cv2.FONT_HERSHEY_SIMPLEX, 1, 2)
        cv2.putText(img, texto, ((640 - tw) // 2, 250), cv2.FONT_HERSHEY_SIMPLEX, 1, (150, 150, 150), 2, cv2.LINE_AA)
        _SIN_SENAL[camara] = a_jpeg(img)
    return _SIN_SENAL[camara]


@dataclass
class Contexto:
    orquestador: Orquestador
    asistente: AsistenteGarbi
    demo: bool = False
    seta: object | None = None            # SetaGlobal, si está arrancada
    foco_chat_desde: float | None = None  # monotonic
    cache: CacheImagenes | None = None
    cerrojo_chat: asyncio.Lock = field(default_factory=asyncio.Lock)
    indicadores: Indicadores = field(default_factory=Indicadores)   # si el orquestador no trae los suyos
    registro: Registro = field(default_factory=Registro)
    inicio: datetime = field(default_factory=datetime.now)
    cerrojo_muestreo: threading.Lock = field(default_factory=threading.Lock)

    def escribiendo_en_chat(self) -> bool:
        return self.foco_chat_desde is not None and time.monotonic() - self.foco_chat_desde < FOCO_CHAT_MAX

    def comando(self, comando: Comando, origen: str) -> None:
        self.orquestador.comando(comando)
        self.registro.anotar("comando", comando.value, origen)

    def emergencia(self, origen: str) -> None:
        log.warning("EMERGENCIA (%s)", origen)
        self.orquestador.comando(Comando.EMERGENCIA)
        self.registro.anotar("comando", Comando.EMERGENCIA.value, origen)

    def muestrear(self) -> EstadoApp:
        """Lee el estado, alimenta los indicadores propios y apunta los eventos nuevos en el registro."""
        e = self.orquestador.estado_app()
        with self.cerrojo_muestreo:
            self.indicadores.observar(e.estado, bool(e.aspiradora), time.monotonic())
            self.registro.eventos_orquestador(list(e.eventos))
        return e

    def valores_indicadores(self, e: EstadoApp) -> dict[str, float]:
        with self.cerrojo_muestreo:
            propios = self.indicadores.como_dict()
        propios["agujeros"] = max(propios["agujeros"], e.agujeros)
        return {**propios, **(getattr(e, "indicadores", None) or {})}


CLAVE = web.AppKey("contexto", Contexto)


def crear_app(orquestador: Orquestador, asistente: AsistenteGarbi | None = None, demo: bool = False,
              seta: object | None = None) -> web.Application:
    ctx = Contexto(orquestador, asistente or AsistenteGarbi(orquestador), demo=demo, seta=seta,
                   cache=CacheImagenes(orquestador))
    app = web.Application()
    app[CLAVE] = ctx
    app.router.add_get("/", _indice)
    app.router.add_get("/api/estado", _estado)
    app.router.add_post("/api/comando", _comando)
    app.router.add_post("/api/emergencia", _emergencia)
    app.router.add_post("/api/chat", _chat)
    app.router.add_post("/api/foco_chat", _foco_chat)
    app.router.add_get("/video/{camara}", _video)
    app.router.add_get("/foto/{camara}", _foto)
    app.router.add_get("/api/registro.csv", _registro_csv)
    app.router.add_static("/static/", ESTATICOS, append_version=True)
    app.on_startup.append(_arrancar_muestreo)
    app.on_cleanup.append(_parar_muestreo)
    return app


MUESTREO = web.AppKey("muestreo", asyncio.Task)


async def _arrancar_muestreo(app: web.Application) -> None:
    """Muestrea el estado a 4 Hz aunque no haya ninguna página abierta (indicadores y registro siempre al día)."""
    ctx = app[CLAVE]
    ctx.registro.anotar("sesion", "App de Garbi arrancada" + (" (modo demo)" if ctx.demo else ""), "app")

    async def bucle():
        while True:
            try:
                await asyncio.to_thread(ctx.muestrear)
            except Exception:
                log.exception("Fallo al muestrear el estado")
            await asyncio.sleep(0.25)

    app[MUESTREO] = asyncio.create_task(bucle())


async def _parar_muestreo(app: web.Application) -> None:
    tarea = app.get(MUESTREO)
    if tarea:
        tarea.cancel()


# --- manejadores ------------------------------------------------------------------------------------------------------

async def _indice(request: web.Request) -> web.FileResponse:
    return web.FileResponse(ESTATICOS / "index.html", headers={"Cache-Control": "no-store"})


def estado_json(ctx: Contexto) -> dict:
    e = ctx.muestrear()
    tecnologias = dict(e.tecnologias)
    tecnologias.setdefault("llm", ctx.asistente.estado_tecnologia())
    seta = ctx.seta
    if seta is not None and getattr(seta, "activa", False):
        tecnologias.setdefault("seta", "ok: global (espacio)")
    else:
        tecnologias.setdefault("seta", "aviso: solo con la página enfocada")
    return {
        "estado": e.estado.value, "detalle": e.detalle, "aspiradora": bool(e.aspiradora), "politica": e.politica,
        "tecnologias": tecnologias, "agujeros": e.agujeros, "eventos": list(e.eventos)[:30],
        "demo": ctx.demo, "llm": "claude" if ctx.asistente.con_claude else "local",
        "indicadores": ctx.valores_indicadores(e),
    }


async def _estado(request: web.Request) -> web.Response:
    return web.json_response(estado_json(request.app[CLAVE]), headers={"Cache-Control": "no-store"})


async def _leer_json(request: web.Request) -> dict:
    try:
        datos = await request.json()
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise web.HTTPBadRequest(text="JSON no válido")
    if not isinstance(datos, dict):
        raise web.HTTPBadRequest(text="se esperaba un objeto JSON")
    return datos


async def _comando(request: web.Request) -> web.Response:
    ctx = request.app[CLAVE]
    datos = await _leer_json(request)
    try:
        comando = Comando(datos.get("comando"))
    except ValueError:
        return web.json_response({"ok": False, "error": f"comando desconocido: {datos.get('comando')!r}",
                                  "validos": [c.value for c in Comando]}, status=400)
    if comando is Comando.EMERGENCIA:
        ctx.emergencia("botón")
    else:
        ctx.comando(comando, "botón")
    return web.json_response({"ok": True, "comando": comando.value})


async def _emergencia(request: web.Request) -> web.Response:
    origen = request.query.get("origen", "página")
    request.app[CLAVE].emergencia(origen)
    return web.json_response({"ok": True, "comando": Comando.EMERGENCIA.value})


async def _chat(request: web.Request) -> web.Response:
    ctx = request.app[CLAVE]
    datos = await _leer_json(request)
    texto = str(datos.get("texto", ""))
    modo = "fabrica" if datos.get("modo") == "fabrica" else "taller"
    async with ctx.cerrojo_chat:
        r = await asyncio.to_thread(ctx.asistente.responder, texto, modo)
    ctx.registro.anotar("chat", f"«{texto[:200]}» → {r.texto}", r.fuente)
    for c in r.comandos:
        ctx.registro.anotar("comando", c.value, "chat")
    return web.json_response({"respuesta": r.texto, "comandos": [c.value for c in r.comandos], "fuente": r.fuente})


async def _registro_csv(request: web.Request) -> web.Response:
    ctx = request.app[CLAVE]
    e = await asyncio.to_thread(ctx.muestrear)
    extra = {"inicio": ctx.inicio.isoformat(timespec="seconds"), "politica": e.politica,
             "modo": "demo" if ctx.demo else "robot", "estado_actual": e.estado.value}
    texto = ctx.registro.csv(ctx.valores_indicadores(e), extra)
    nombre = f"garbi_registro_{datetime.now():%Y%m%d_%H%M%S}.csv"
    return web.Response(body=texto.encode("utf-8"), content_type="text/csv", charset="utf-8",
                        headers={"Content-Disposition": f'attachment; filename="{nombre}"', "Cache-Control": "no-store"})


async def _foco_chat(request: web.Request) -> web.Response:
    ctx = request.app[CLAVE]
    foco = bool((await _leer_json(request)).get("foco"))
    ctx.foco_chat_desde = time.monotonic() if foco else None
    return web.json_response({"ok": True, "foco": foco})


def _camara(request: web.Request) -> str:
    camara = request.match_info["camara"].removesuffix(".mjpg").removesuffix(".jpg")
    if camara not in CAMARAS:
        raise web.HTTPNotFound(text=f"cámara desconocida: {camara}")
    return camara


async def _foto(request: web.Request) -> web.Response:
    ctx = request.app[CLAVE]
    jpg = await asyncio.to_thread(ctx.cache.jpeg, _camara(request))
    return web.Response(body=jpg, content_type="image/jpeg", headers={"Cache-Control": "no-store"})


async def _video(request: web.Request) -> web.StreamResponse:
    ctx = request.app[CLAVE]
    camara = _camara(request)
    resp = web.StreamResponse(headers={
        "Content-Type": "multipart/x-mixed-replace; boundary=frame", "Cache-Control": "no-store"})
    await resp.prepare(request)
    try:
        while True:
            t0 = time.monotonic()
            jpg = await asyncio.to_thread(ctx.cache.jpeg, camara)
            await resp.write(b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: "
                             + str(len(jpg)).encode() + b"\r\n\r\n" + jpg + b"\r\n")
            await asyncio.sleep(max(0.0, 1.0 / FPS_VIDEO - (time.monotonic() - t0)))
    except (ConnectionResetError, asyncio.CancelledError, RuntimeError):
        pass   # el navegador ha cerrado la conexión
    return resp


# --- servidor en un hilo aparte -------------------------------------------------------------------------------------

class ServidorApp:
    """Arranca la app en un hilo con su propio bucle asyncio. No bloquea al llamador (el bucle de control)."""

    def __init__(self, app: web.Application, host: str = "127.0.0.1", puerto: int = 8800):
        self.app, self.host, self.puerto = app, host, puerto
        self._bucle: asyncio.AbstractEventLoop | None = None
        self._runner: web.AppRunner | None = None
        self._hilo: threading.Thread | None = None
        self._listo = threading.Event()
        self._error: BaseException | None = None

    @property
    def url(self) -> str:
        host = "localhost" if self.host in ("0.0.0.0", "127.0.0.1") else self.host
        return f"http://{host}:{self.puerto}/"

    def arrancar(self, espera: float = 10.0) -> "ServidorApp":
        self._hilo = threading.Thread(target=self._correr, name="garbi-app", daemon=True)
        self._hilo.start()
        if not self._listo.wait(espera):
            raise TimeoutError("el servidor de la app no ha arrancado")
        if self._error:
            raise self._error
        return self

    def _correr(self) -> None:
        self._bucle = asyncio.new_event_loop()
        asyncio.set_event_loop(self._bucle)
        try:
            self._runner = web.AppRunner(self.app, access_log=None, shutdown_timeout=1.0)
            self._bucle.run_until_complete(self._runner.setup())
            sitio = web.TCPSite(self._runner, self.host, self.puerto)
            self._bucle.run_until_complete(sitio.start())
            if self.puerto == 0:   # puerto libre elegido por el sistema (pruebas)
                self.puerto = sitio._server.sockets[0].getsockname()[1]
        except BaseException as e:
            self._error = e
            self._listo.set()
            return
        self._listo.set()
        self._bucle.run_forever()
        self._bucle.run_until_complete(self._runner.cleanup())
        self._bucle.close()

    def parar(self) -> None:
        if self._bucle and self._bucle.is_running():
            self._bucle.call_soon_threadsafe(self._bucle.stop)
        if self._hilo:
            self._hilo.join(timeout=5)
