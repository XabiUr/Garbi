"""La app de Garbi manejando el supervisor del equipo (`plana/supervisor.py`) como un proceso aparte.

    python -m garbi.producto.app --supervisor                     # supervisor con --real --cerebro zonas
    python -m garbi.producto.app --supervisor --supervisor-args "--sin-robot --cerebro zonas"

- Encender → lanza `python supervisor.py <args>` con `cwd` en la carpeta del supervisor (lee config.json, zona.json...).
- Apagar   → SIGTERM: el supervisor lo atiende como la tecla Q (vuelve a reposo y cierra). Si a los `espera_apagado`
             segundos no ha salido, SIGINT (cierra sin volver a reposo) y, si tampoco, SIGKILL.
- Limpiar tabla / Limpiar tapete / Parar / Emergencia / Rearmar → órdenes por UDP a 127.0.0.1:8765
  ("tabla" = tecla B, "tapete" = tecla T, "parar" = interrumpe el barrido, "parada" = ESPACIO, "continuar" = C).
  La emergencia también va por señal (SIGUSR1) por si el canal UDP fallara.
- Estado: el supervisor escribe estado_supervisor.json varias veces por segundo; la app lo traduce a sus estados
  (REPOSO, ACERCAMIENTO, EN_BROCA, LIMPIEZA_TABLA, LIMPIEZA_TAPETE, EMERGENCIA).

Imágenes: el supervisor (el único que abre las cámaras) arranca con --sin-ventana y publica camara_front.jpg (anotada)
y camara_gripper.jpg; la app las enseña en sus paneles "top" y "wrist".
"""
from __future__ import annotations

import logging
import json
import os
import shlex
import socket
import signal
import subprocess
import sys
import threading
import time
from collections import deque
from pathlib import Path

from garbi.producto.contrato import Comando, Estado, EstadoApp

log = logging.getLogger(__name__)

# plana/web/garbi/producto/app/supervisor_externo.py → plana
CARPETA_POR_DEFECTO = Path(__file__).resolve().parents[4]
ARGS_POR_DEFECTO = "--real --cerebro zonas"
PUERTO_COMANDOS = 8765   # solo por defecto; al encender se elige uno libre y se le pasa al supervisor


def _puerto_udp_libre() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]

# estado del supervisor → estado de la app
ESTADOS = {"REPOSO": Estado.REPOSO, "APROXIMANDO": Estado.ACERCAMIENTO, "EN_OBJETIVO": Estado.EN_BROCA,
           "FIJO": Estado.EN_BROCA, "LIMPIEZA_LOCAL": Estado.EN_BROCA, "PARADA": Estado.EMERGENCIA}
DETALLES = {"REPOSO": "En reposo: esperando al taladro", "APROXIMANDO": "Me acerco a la broca",
            "EN_OBJETIVO": "En la broca", "FIJO": "En la broca", "LIMPIEZA_LOCAL": "Limpiando junto a la broca",
            "VOLVIENDO": "Vuelvo a reposo", "PARADA": "PARADA (rearmar para continuar)",
            "BARRIDO_IDA": "Voy a barrer", "BARRIENDO": "Barriendo"}


class OrquestadorSupervisor:
    """Cumple la interfaz `Orquestador` de la app lanzando y cerrando el supervisor. Seguro entre hilos."""

    politica = "supervisor"

    def __init__(self, carpeta: str | Path = CARPETA_POR_DEFECTO, args: str | list[str] = ARGS_POR_DEFECTO,
                 python: str = sys.executable, script: str = "supervisor.py", espera_apagado: float = 15.0,
                 ventana: bool = False):
        self.carpeta = Path(carpeta).resolve()
        self.args = shlex.split(args) if isinstance(args, str) else list(args)
        if not ventana and "--sin-ventana" not in self.args:
            self.args.append("--sin-ventana")   # sin ventana de OpenCV: la imagen se ve en la web
        self.python, self.script, self.espera_apagado = python, script, espera_apagado
        self._cerrojo = threading.RLock()
        self._proceso: subprocess.Popen | None = None
        self._apagando = False
        self._parada = False
        self._eventos: deque[str] = deque(maxlen=60)
        self._udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._ultimo_aviso = ""
        self._puerto = PUERTO_COMANDOS
        self._cerebro = None                # el que usa el supervisor ahora ("act" | "zonas")
        self._cerebros: list[str] = []      # los que tiene cargados
        self._anotar("App lista: pulsa Encender para arrancar el supervisor")

    # --- interfaz del puente ------------------------------------------------------------------------------------------

    def comando(self, comando: Comando) -> None:
        comando = Comando(comando)
        with self._cerrojo:
            self._revisar()
            if comando is Comando.ENCENDER:
                self._encender()
            elif comando is Comando.APAGAR:
                self._apagar()
            elif comando is Comando.EMERGENCIA:
                if self._orden("parada"):
                    self._enviar(signal.SIGUSR1)   # por si el UDP fallara (el supervisor ignora la repetición)
                    self._parada = True
                    self._anotar("¡EMERGENCIA! PARADA en el supervisor")
            elif comando is Comando.REARMAR:
                if self._orden("continuar"):
                    self._parada = False
                    self._anotar("Rearmado: el supervisor vuelve a reposo")
            elif comando is Comando.LIMPIAR_TABLA:
                if self._orden("tabla"):
                    self._anotar("Pedido: limpiar la tabla (B)")
            elif comando is Comando.LIMPIAR_TAPETE:
                if self._orden("tapete"):
                    self._anotar("Pedido: limpiar el tapete (T)")
            elif comando is Comando.PARAR:
                if self._orden("parar"):
                    self._anotar("Pedido: parar el barrido")

    def estado_app(self) -> EstadoApp:
        with self._cerrojo:
            self._revisar()
            vivo = self._vivo()
            if not vivo:
                estado, detalle = Estado.APAGADO, "Supervisor cerrado"
            elif self._apagando:
                estado, detalle = Estado.REPOSO, "Apagando: vuelve a reposo y se cierra"
            else:
                estado, detalle = self._estado_supervisor()
            return EstadoApp(
                estado=estado, detalle=detalle, aspiradora=False, politica=(self._cerebro if vivo and self._cerebro else "—"),
                tecnologias={
                    "robot": f"ok: supervisor ({' '.join(self.args)})" if vivo else "aviso: supervisor cerrado",
                    "politica": (f"ok: {self._cerebro} · cargados: {', '.join(self._cerebros)}"
                                 if vivo and self._cerebro else "aviso: supervisor cerrado"),
                    "vision": "ok: imagen del supervisor" if vivo else "aviso: apagada",
                    "aspiradora": "manual",
                },
                eventos=list(self._eventos))

    def _estado_supervisor(self) -> tuple:
        """Lee estado_supervisor.json (lo escribe el supervisor) y lo traduce a los estados de la app."""
        try:
            d = json.load(open(self.carpeta / "estado_supervisor.json"))
        except (FileNotFoundError, json.JSONDecodeError):
            d = None
        if not d or d.get("pid") != self._proceso.pid or time.time() - d.get("t", 0) > 3.0:
            return Estado.ARRANCANDO, "Arrancando: conectando el robot y yendo a reposo"
        e = d["estado"]
        aviso = d.get("aviso") or ""
        if aviso and aviso != self._ultimo_aviso:
            self._ultimo_aviso = aviso
            self._eventos.appendleft(aviso)
        if e == "ESPERA_OBSTACULO":   # quieto por una mano o el taladro; se puede Parar
            que = "el tapete" if d.get("barrido") == "tapete" else "la tabla"
            estado = Estado.LIMPIEZA_TAPETE if d.get("barrido") == "tapete" else Estado.LIMPIEZA_TABLA
            detalle = f"QUIETO: algo en la zona mientras limpiaba {que}. Vuelvo a reposo cuando se despeje"
        elif d.get("barrido") and e in ("BARRIDO_IDA", "BARRIENDO", "VOLVIENDO"):
            estado = Estado.LIMPIEZA_TAPETE if d["barrido"] == "tapete" else Estado.LIMPIEZA_TABLA
            que = "el tapete" if d["barrido"] == "tapete" else "la tabla"
            detalle = f"Vuelvo a reposo tras barrer {que}" if e == "VOLVIENDO" else f"{DETALLES.get(e, e)} {que}"
        elif e == "VOLVIENDO":   # volviendo a reposo (tras el taladro): el brazo se mueve, no está listo
            estado, detalle = Estado.DESPIERTO, DETALLES["VOLVIENDO"]
        else:
            estado, detalle = ESTADOS.get(e, Estado.REPOSO), DETALLES.get(e, e)
        self._parada = e == "PARADA"
        self._cerebro = d.get("cerebro", self._cerebro)
        self._cerebros = d.get("cerebros", self._cerebros)
        if not d.get("barrido_listo", True):
            detalle += " · barrido sin calibrar"
        return estado, detalle

    def elegir_cerebro(self, nombre: str) -> bool:
        """Pide al supervisor que haga la aproximación con `nombre` ("act" o "zonas"). Decide el supervisor."""
        with self._cerrojo:
            if self._orden(f"cerebro:{nombre}"):
                self._anotar(f"Pedido: aproximación con {nombre.upper()}")
                return True
            return False

    def imagenes_anotadas(self) -> dict:
        """Los JPEG que publica el supervisor (si son recientes)."""
        if not self._vivo():
            return {}
        salida = {}
        for camara, nombre in (("top", "camara_front.jpg"), ("wrist", "camara_gripper.jpg")):
            ruta = self.carpeta / nombre
            try:
                if time.time() - ruta.stat().st_mtime < 2.0:
                    salida[camara] = ruta.read_bytes()
            except OSError:
                pass
        return salida

    def cerrar(self) -> None:
        """Al salir de la app: apaga el supervisor si sigue vivo y espera a que cierre."""
        with self._cerrojo:
            self._apagar()
            proceso = self._proceso
        if proceso is not None:
            try:
                proceso.wait(self.espera_apagado + 10)
            except subprocess.TimeoutExpired:
                pass

    # --- proceso ------------------------------------------------------------------------------------------------------

    def _vivo(self) -> bool:
        return self._proceso is not None and self._proceso.poll() is None

    def _revisar(self) -> None:
        """Detecta que el supervisor ha terminado (Q en su ventana, error, o apagado completado)."""
        if self._proceso is not None and self._proceso.poll() is not None:
            codigo = self._proceso.returncode
            self._anotar("Supervisor cerrado" + ("" if codigo == 0 or self._apagando else f" (código {codigo})"))
            self._proceso, self._apagando, self._parada = None, False, False

    def _encender(self) -> None:
        if self._vivo():
            self._anotar("El supervisor ya está en marcha")
            return
        if not (self.carpeta / self.script).exists():
            self._anotar(f"No encuentro {self.carpeta / self.script}")
            return
        # puerto de órdenes propio: esta web solo habla con SU supervisor aunque haya otro en marcha
        self._puerto = _puerto_udp_libre()
        orden = [self.python, "-u", self.script, *self.args, "--puerto-comandos", str(self._puerto),
                 "--pid-padre", str(os.getpid())]   # si esta web desaparece, el supervisor se apaga solo
        log.info("Lanzando supervisor: %s (en %s)", " ".join(orden), self.carpeta)
        # start_new_session: un Ctrl+C en la terminal de la app no le llega directamente; lo cerramos nosotros.
        self._proceso = subprocess.Popen(orden, cwd=self.carpeta, stdin=subprocess.DEVNULL, start_new_session=True)
        self._apagando = self._parada = False
        self._anotar(f"Supervisor arrancado (PID {self._proceso.pid})")

    def _apagar(self) -> None:
        if not self._vivo():
            if self._proceso is None:
                self._anotar("El supervisor ya estaba cerrado")
            return
        if self._apagando:
            return
        self._apagando = True
        self._enviar(signal.SIGTERM)
        self._anotar("Apagando el supervisor: vuelve a reposo y se cierra")
        threading.Thread(target=self._vigilar_apagado, args=(self._proceso,), name="garbi-apagado", daemon=True).start()

    def _vigilar_apagado(self, proceso: subprocess.Popen) -> None:
        for senal, espera in ((signal.SIGINT, self.espera_apagado), (signal.SIGKILL, 5.0)):
            try:
                proceso.wait(espera)
                return
            except subprocess.TimeoutExpired:
                log.warning("El supervisor no se cierra: envío %s", senal.name)
                with self._cerrojo:
                    self._anotar(f"El supervisor no responde: {senal.name}")
                try:
                    os.kill(proceso.pid, senal)
                except ProcessLookupError:
                    return

    def _orden(self, texto: str) -> bool:
        """Manda una orden al supervisor por UDP (127.0.0.1)."""
        if not self._vivo():
            self._anotar("El supervisor no está en marcha: pulsa Encender")
            return False
        try:
            self._udp.sendto(texto.encode(), ("127.0.0.1", self._puerto))
            return True
        except OSError as e:
            self._anotar(f"No puedo mandar «{texto}» al supervisor ({e})")
            return False

    def _enviar(self, senal: signal.Signals) -> bool:
        if not self._vivo():
            self._anotar("El supervisor no está en marcha")
            return False
        try:
            os.kill(self._proceso.pid, senal)
            return True
        except ProcessLookupError:
            return False

    def _anotar(self, texto: str) -> None:
        self._eventos.appendleft(f"{time.strftime('%H:%M:%S')} · {texto}")
