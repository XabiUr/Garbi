"""`python -m garbi.producto.app --demo`: la app sin robot y con el navegador abierto.

Por defecto la demo usa el **orquestador real** del producto (`garbi.producto.__main__.crear_demo`: robot, cámaras y
escena falsos, a 30 Hz en su hilo) con las detecciones dibujadas por `VisionProducto`. Con `--demo-simple` (o si eso
falla) usa el `OrquestadorFalso` de la app, con imágenes sintéticas más vistosas y un guion corto.
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
import time

from garbi.producto.app import OrquestadorFalso, arrancar_app
from garbi.producto.app.puente import DemoSistema

log = logging.getLogger("garbi.producto.app")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m garbi.producto.app", description="App de Garbi")
    p.add_argument("--demo", action="store_true", help="sin robot: orquestador real con robot y escena falsos")
    p.add_argument("--demo-simple", action="store_true",
                   help="sin robot: orquestador falso de la app (guion corto e imágenes sintéticas)")
    p.add_argument("--config", default=None, help="yaml del producto (por defecto garbi/producto/garbi_producto.yaml)")
    p.add_argument("--host", default="127.0.0.1", help="0.0.0.0 para abrirla desde otro dispositivo (tablet, móvil)")
    p.add_argument("--puerto", type=int, default=8800)
    p.add_argument("--sin-navegador", action="store_true", help="no abrir el navegador")
    p.add_argument("--sin-seta-global", action="store_true", help="no escuchar el espacio fuera de la página")
    p.add_argument("--supervisor", action="store_true",
                   help="Encender/Apagar lanzan y cierran plana/supervisor.py (robot real)")
    p.add_argument("--supervisor-dir", default=None, help="carpeta de supervisor.py (por defecto ../plana)")
    p.add_argument("--supervisor-args", default=None,
                   help='argumentos del supervisor (por defecto "--real --cerebro zonas")')
    p.add_argument("--con-arduino", action="store_true",
                   help="(demo simple) aspiradora controlada por Arduino; por defecto, manual con el pie")
    a = p.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    if a.supervisor:
        return _con_supervisor(a)

    if not (a.demo or a.demo_simple):
        print("Con el robot real la app la arranca el programa principal: python -m garbi.producto\n"
              "Para enseñarla sin robot: python -m garbi.producto.app --demo", file=sys.stderr)
        return 2

    demo = None
    if not a.demo_simple:
        try:
            from garbi.producto.config import cargar_config

            demo = DemoSistema.crear(cargar_config(a.config)).arrancar()
        except Exception as e:
            log.warning("No puedo arrancar la demo con el orquestador real (%s): uso el orquestador falso", e)
    orquestador = demo or OrquestadorFalso(aspiradora_manual=not a.con_arduino)
    servidor = arrancar_app(orquestador, a.host, a.puerto, demo=True, seta_global=not a.sin_seta_global,
                            abrir_navegador=not a.sin_navegador)
    print(f"Garbi (demo) en {servidor.url}  ·  Ctrl+C para salir")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        servidor.parar()
        if demo:
            demo.parar()
    return 0


def _con_supervisor(a) -> int:
    from garbi.producto.app.supervisor_externo import (ARGS_POR_DEFECTO, CARPETA_POR_DEFECTO,
                                                       OrquestadorSupervisor)

    import signal
    import threading
    from datetime import datetime

    orquestador = OrquestadorSupervisor(a.supervisor_dir or CARPETA_POR_DEFECTO, a.supervisor_args or ARGS_POR_DEFECTO)

    # Registro en archivo (plana/Logs/web_*.log): si la web se cierra, queda escrito por qué
    carpeta_logs = orquestador.carpeta / "Logs"
    carpeta_logs.mkdir(exist_ok=True)
    ruta_log = carpeta_logs / f"web_{datetime.now():%Y%m%d_%H%M%S}.log"
    fichero = logging.FileHandler(ruta_log, encoding="utf-8")
    fichero.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logging.getLogger().addHandler(fichero)
    sys.excepthook = lambda t, v, tb: log.critical("Error no controlado: la web se cierra", exc_info=(t, v, tb))
    threading.excepthook = lambda x: log.error("Error en el hilo %s", x.thread.name if x.thread else "?",
                                                exc_info=(x.exc_type, x.exc_value, x.exc_traceback))

    # Cerrar la ventana de Terminal (SIGHUP) o un kill (SIGTERM): salir ordenado, apagando antes el supervisor
    def _senal(num, _frame):
        log.warning("Recibida %s: cierro la web y apago el supervisor", signal.Signals(num).name)
        raise KeyboardInterrupt
    for s in (signal.SIGHUP, signal.SIGTERM):
        signal.signal(s, _senal)
    log.info("Web arrancada (PID %s) · registro en %s", os.getpid(), ruta_log)

    servidor = arrancar_app(orquestador, a.host, a.puerto, demo=False, seta_global=not a.sin_seta_global,
                            abrir_navegador=not a.sin_navegador)
    print(f"Garbi (supervisor en {orquestador.carpeta}) en {servidor.url}  ·  Ctrl+C para salir")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log.info("Cierre pedido (Ctrl+C, ventana cerrada o kill)")
    finally:
        print("Cerrando: apago el supervisor si sigue en marcha...")
        log.info("Cerrando: apago el supervisor si sigue en marcha")
        orquestador.cerrar()
        servidor.parar()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
