"""Capturas de la tablet (1280x800) en los momentos de la demo, con la fuente simulada y Playwright.

    python herramientas/capturas_tablet.py [--salida salidas/capturas] [--chromium /opt/pw-browsers/chromium]

Arranca el servidor en este mismo proceso (fuente simulada acelerada, robot cinemático acelerado, antorcha del
robot virtual), abre la página en Chromium sin ventana y guarda:

1. `1-examen.png`: examen en curso (cordón pintándose, nota provisional, avisos).
2. `2-nota.png`: nota con el hueco y la valoración del maestro.
3. `3-repaso.png`: repaso del robot con el LED encendido dentro del hueco.
4. `4-repaso-terminado.png`: el hueco relleno por el robot.
5. `5-certificado.png`: certificado tras una pasada sin huecos.
6. `6-maestro-t.png`: el robot soldando la unión en T.
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from aiohttp import web  # noqa: E402

from lewelder.antorcha import AntorchaRobot  # noqa: E402
from lewelder.antorcha_virtual import AntorchaRobotVirtual  # noqa: E402
from lewelder.fuentes import ConfigPasada, FuenteSimulada  # noqa: E402
from lewelder.robot import RobotCinematico  # noqa: E402
from lewelder.servidor import Escuela, crear_app  # noqa: E402

PUERTO = 8765
CHROMIUM = "/opt/pw-browsers/chromium"


async def esperar(condicion, timeout: float = 120.0, paso: float = 0.05) -> None:
    fin = asyncio.get_running_loop().time() + timeout
    while not condicion():
        if asyncio.get_running_loop().time() > fin:
            raise TimeoutError("la demo no llegó al estado esperado")
        await asyncio.sleep(paso)


async def capturar(salida: Path, chromium: str) -> list[Path]:
    from playwright.async_api import async_playwright

    salida.mkdir(parents=True, exist_ok=True)
    virtual = AntorchaRobotVirtual()
    robot = RobotCinematico(escala_tiempo=2.5)
    fuente = FuenteSimulada(config=ConfigPasada(huecos=[(40.0, 55.0)], temblor_mm=0.4), tiempo_real=False)
    escuela = Escuela(fuente, robot, AntorchaRobot(virtual.ruta), dir_pasadas=None)
    runner = web.AppRunner(crear_app(escuela))
    await runner.setup()
    await web.TCPSite(runner, "127.0.0.1", PUERTO).start()
    rutas: list[Path] = []
    try:
        async with async_playwright() as pw:
            navegador = await pw.chromium.launch(executable_path=chromium, args=[
                "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"])
            pagina = await navegador.new_page(viewport={"width": 1280, "height": 800}, device_scale_factor=1)
            pagina.on("console", lambda m: m.type == "error" and print("consola:", m.text))
            await pagina.goto(f"http://127.0.0.1:{PUERTO}/")
            await pagina.wait_for_function("window.lewelder && window.lewelder.estado.fuente.fuente === 'simulada'")
            await asyncio.sleep(0.5)

            async def foto(nombre: str, espera: float = 0.4):
                await asyncio.sleep(espera)
                ruta = salida / nombre
                await pagina.screenshot(path=str(ruta))
                rutas.append(ruta)
                print("captura:", ruta)

            # 1. Examen en curso: pasado el hueco, a dos tercios del cordón.
            await pagina.click("#b-examen")
            await esperar(lambda: escuela.muestras_examen and escuela.muestras_examen[-1].x > 82)
            await foto("1-examen.png", 0.15)
            # 2. Nota con el hueco y la valoración.
            await esperar(lambda: escuela.modo == "nota" and escuela.valoracion is not None)
            await foto("2-nota.png", 1.0)
            # 3. Repaso con el LED encendido en el hueco.
            await pagina.click("#b-repaso")
            await esperar(lambda: escuela.led_robot and robot.punta is not None and robot.punta.x > 48)
            await foto("3-repaso.png", 0.1)
            await esperar(lambda: not escuela.robot_ocupado)
            await foto("4-repaso-terminado.png", 0.8)
            # 5. Pasada perfecta → certificado.
            await pagina.click("#b-reiniciar")
            await escuela.orden({"orden": "simulacion", "pasada": "perfecta"})
            await asyncio.sleep(0.3)
            await pagina.click("#b-examen")
            await esperar(lambda: escuela.modo == "nota" and escuela.valoracion is not None)
            await asyncio.sleep(0.5)
            await pagina.click("#b-certificado")
            await esperar(lambda: escuela.modo == "certificado")
            await foto("5-certificado.png", 0.8)
            # 6. El robot suelda la T.
            await pagina.click("#cert-maestro")
            await esperar(lambda: escuela.modo == "maestro" and robot.punta is not None and robot.punta.x > 70)
            await foto("6-maestro-t.png", 0.1)
            await navegador.close()
    finally:
        await runner.cleanup()
        virtual.parar()
    return rutas


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--salida", type=Path, default=RAIZ / "salidas" / "capturas")
    p.add_argument("--chromium", default=CHROMIUM)
    args = p.parse_args()
    asyncio.run(capturar(args.salida, args.chromium))


if __name__ == "__main__":
    main()
