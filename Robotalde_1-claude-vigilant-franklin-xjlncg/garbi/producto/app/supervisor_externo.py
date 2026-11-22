"""La app de Garbi manejando el supervisor del equipo (`plana/supervisor.py`) como un proceso aparte.

    python -m garbi.producto.app --supervisor                     # supervisor con --real --cerebro zonas
    python -m garbi.producto.app --supervisor --supervisor-args "--sin-robot --cerebro zonas"

- Encender → lanza `python supervisor.py <args>` con `cwd` en la carpeta del supervisor (lee config.json, zona.json...).
- Apagar   → SIGTERM: el supervisor lo atiende como la tecla Q (vuelve a reposo y cierra). Si a los `espera_apagado`
             segundos no ha salido, SIGINT (cierra sin volver a reposo) y, si tampoco, SIGKILL.
- Emergencia (seta / botón rojo) → SIGUSR1 = PARADA (como ESPACIO). Rearmar → SIGUSR2 = continuar (como C).
- El resto de comandos (limpiezas, parar) todavía no existen en el supervisor: se anotan como no disponibles.

Las cámaras las tiene abiertas el supervisor (con su propia ventana de OpenCV), así que la app no enseña vídeo.
"""
from __future__ import annotations

import logging
import os
import shlex
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
                if self._enviar(signal.SIGUSR1):
                    self._parada = True
                    self._anotar("¡EMERGENCIA! PARADA en el supervisor")
            elif comando is Comando.REARMAR:
                if self._enviar(signal.SIGUSR2):
                    self._parada = False
                    self._anotar("Rearmado: el supervisor vuelve a reposo")
            else:
                self._anotar(f"«{comando.value}» aún no está disponible con el supervisor")

    def estado_app(self) -> EstadoApp:
        with self._cerrojo:
            self._revisar()
            vivo = self._vivo()
            if not vivo:
                estado, detalle = Estado.APAGADO, "Supervisor cerrado"
            elif self._apagando:
                estado, detalle = Estado.REPOSO, "Apagando: vuelve a reposo y se cierra"
            elif self._parada:
                estado, detalle = Estado.EMERGENCIA, "PARADA en el supervisor (rearmar para continuar)"
            else:
                estado, detalle = Estado.REPOSO, f"Supervisor en marcha (PID {self._proceso.pid})"
            return EstadoApp(
                estado=estado, detalle=detalle, aspiradora=False, politica=self.politica,
                tecnologias={
                    "robot": f"ok: supervisor ({' '.join(self.args)})" if vivo else "aviso: supervisor cerrado",
                    "vision": "ok: en la ventana del supervisor" if vivo else "aviso: apagada",
                    "aspiradora": "manual",
                },
                eventos=list(self._eventos))

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
