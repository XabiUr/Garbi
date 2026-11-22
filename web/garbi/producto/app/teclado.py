"""Seta de emergencia global: la seta USB del equipo actúa como la barra espaciadora.

Escucha el espacio en todo el PC (aunque la ventana del navegador no tenga el foco) y llama a `al_pulsar` al instante.
Usa `pynput` si está instalado (Windows, macOS y Linux con X); si no, la librería `keyboard` (Windows). Si no hay
ninguna, no hace nada y la seta sigue funcionando dentro de la página.

Mientras el usuario escribe en el chat de la app (`ignorar()` devuelve True), el espacio no dispara la emergencia;
para eso está el botón rojo, y la página lo avisa.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Callable

log = logging.getLogger(__name__)

ANTIRREBOTE = 0.3   # s: una pulsación de la seta puede repetir la tecla


class SetaGlobal:
    def __init__(self, al_pulsar: Callable[[], None], ignorar: Callable[[], bool] = lambda: False,
                 backend: str | None = None, reloj: Callable[[], float] = time.monotonic):
        self.al_pulsar = al_pulsar
        self.ignorar = ignorar
        self.backend_preferido = backend   # "pynput", "keyboard" o None (el primero que funcione)
        self.backend: str | None = None    # el que se está usando
        self.motivo: str = "sin arrancar"
        self._reloj = reloj
        self._ultima = -1e9
        self._cerrojo = threading.Lock()
        self._parar: Callable[[], None] | None = None

    @property
    def activa(self) -> bool:
        return self.backend is not None

    def tecla(self, es_espacio: bool) -> bool:
        """Procesa una tecla. Devuelve True si ha disparado la emergencia. (Lo llaman los backends y las pruebas.)"""
        if not es_espacio or self.ignorar():
            return False
        with self._cerrojo:
            ahora = self._reloj()
            if ahora - self._ultima < ANTIRREBOTE:
                return False
            self._ultima = ahora
        try:
            self.al_pulsar()
        except Exception:   # el hook no puede morir por un fallo del orquestador
            log.exception("Fallo al mandar la emergencia desde la seta global")
        return True

    def arrancar(self) -> bool:
        orden = [self.backend_preferido] if self.backend_preferido else ["pynput", "keyboard"]
        motivos = []
        for nombre in orden:
            try:
                self._parar = getattr(self, f"_arrancar_{nombre}")()
                self.backend, self.motivo = nombre, "ok"
                log.info("Seta global activa con %s (barra espaciadora)", nombre)
                return True
            except Exception as e:   # no instalado, sin pantalla, sin permisos...
                motivos.append(f"{nombre}: {e}")
        self.motivo = "; ".join(motivos) or "sin backend"
        log.warning("Seta global no disponible (%s). Funciona solo con la página enfocada.", self.motivo)
        return False

    def parar(self) -> None:
        if self._parar:
            try:
                self._parar()
            finally:
                self._parar, self.backend = None, None

    def _arrancar_pynput(self) -> Callable[[], None]:
        from pynput import keyboard

        def al_pulsar(tecla):
            self.tecla(tecla == keyboard.Key.space)

        oyente = keyboard.Listener(on_press=al_pulsar)
        oyente.daemon = True
        oyente.start()
        return oyente.stop

    def _arrancar_keyboard(self) -> Callable[[], None]:
        import keyboard

        gancho = keyboard.on_press_key("space", lambda _e: self.tecla(True))
        return lambda: keyboard.unhook(gancho)
