"""App del producto Garbi: cámaras en vivo con las detecciones, estado, tecnologías, botones, chat con Claude (con
respaldo sin conexión) y la seta de emergencia en la barra espaciadora (en la página y global en el PC).

Uso desde el programa principal (P4), con el orquestador real:

    from garbi.producto.app import arrancar_app
    servidor = arrancar_app(orquestador)          # hilo aparte: no bloquea el bucle a 30 Hz
    ...
    servidor.parar()

Sin robot: `python -m garbi.producto.app --demo`.
"""
from __future__ import annotations

import logging
import webbrowser

from garbi.producto.app.llm import AsistenteGarbi
from garbi.producto.app.puente import Orquestador, OrquestadorFalso
from garbi.producto.app.servidor import CLAVE, ServidorApp, crear_app
from garbi.producto.app.teclado import SetaGlobal

__all__ = ["arrancar_app", "Orquestador", "OrquestadorFalso", "ServidorApp", "SetaGlobal", "AsistenteGarbi"]

log = logging.getLogger(__name__)


def arrancar_app(orquestador: Orquestador, host: str = "127.0.0.1", puerto: int = 8800, demo: bool = False,
                 seta_global: bool = True, abrir_navegador: bool = False,
                 asistente: AsistenteGarbi | None = None) -> ServidorApp:
    """Arranca la app en un hilo y, si se pide, la seta global y el navegador. Devuelve el servidor (tiene `.url`,
    `.parar()` y `.seta`)."""
    app = crear_app(orquestador, asistente, demo=demo)
    ctx = app[CLAVE]
    seta = None
    if seta_global:
        seta = SetaGlobal(lambda: ctx.emergencia("seta global"), ignorar=ctx.escribiendo_en_chat)
        seta.arrancar()
        ctx.seta = seta
    servidor = ServidorApp(app, host, puerto).arrancar()
    servidor.seta = seta
    parar_servidor = servidor.parar

    def parar() -> None:
        if seta:
            seta.parar()
        parar_servidor()

    servidor.parar = parar
    log.info("App de Garbi en %s", servidor.url)
    if abrir_navegador:
        webbrowser.open(servidor.url)
    return servidor
