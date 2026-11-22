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

Las cámaras las tiene abiertas el supervisor (con su propia ventana de OpenCV), así que la app no enseña vídeo.
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

# Garbi/Robotalde_.../garbi/producto/app/supervisor_externo.py → Garbi/plana
CARPETA_POR_DEFECTO = Path(__file__).resolve().parents[4] / "plana"
ARGS_POR_DEFECTO = "--real --cerebro zonas"
PUERTO_COMANDOS = 8765

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
                 python: str = sys.executable, script: str = "supervisor.py", espera_apagado: float = 15.0):
        self.carpeta = Path(carpeta).resolve()
        self.args = shlex.split(args) if isinstance(args, str) else list(args)
        self.python, self.script, self.espera_apagado = python, script, espera_apagado
        self._cerrojo = threading.RLock()
        self._proceso: subprocess.Popen | None = None
        self._apagando = False
        self._parada = False
        self._eventos: deque[str] = deque(maxlen=60)
        self._udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._ultimo_aviso = ""
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
                estado=estado, detalle=detalle, aspiradora=False, politica=self.politica,
                tecnologias={
                    "robot": f"ok: supervisor ({' '.join(self.args)})" if vivo else "aviso: supervisor cerrado",
                    "vision": "ok: en la ventana del supervisor" if vivo else "aviso: apagada",
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
            return Estado.REPOSO, "Arrancando el supervisor..."
        e = d["estado"]
        aviso = d.get("aviso") or ""
        if aviso and aviso != self._ultimo_aviso:
            self._ultimo_aviso = aviso
            self._eventos.appendleft(aviso)
        if d.get("barrido") and e in ("BARRIDO_IDA", "BARRIENDO", "VOLVIENDO"):
            estado = Estado.LIMPIEZA_TAPETE if d["barrido"] == "tapete" else Estado.LIMPIEZA_TABLA
            que = "el tapete" if d["barrido"] == "tapete" else "la tabla"
            detalle = f"Vuelvo a reposo tras barrer {que}" if e == "VOLVIENDO" else f"{DETALLES.get(e, e)} {que}"
        else:
            estado, detalle = ESTADOS.get(e, Estado.REPOSO), DETALLES.get(e, e)
        self._parada = e == "PARADA"
        if not d.get("barrido_listo", True):
            detalle += " · barrido sin calibrar"
        return estado, detalle

    def imagenes_anotadas(self) -> dict:
        return {}   # las cámaras las usa el supervisor

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
        orden = [self.python, "-u", self.script, *self.args]
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
            self._udp.sendto(texto.encode(), ("127.0.0.1", PUERTO_COMANDOS))
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
