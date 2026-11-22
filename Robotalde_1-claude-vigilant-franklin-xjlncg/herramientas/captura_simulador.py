"""Capturas del simulador de la demo (vista combinada a 1920x1080) en varios momentos de la ronda.

    python herramientas/captura_simulador.py [--url http://localhost:8080] [--salida salidas/capturas_sim]
                                             [--chromium /opt/pw-browsers/chromium] [--solo-inicio]

Abre `/?guion=jurado` (la secuencia del pitch sola) y guarda una captura en cada momento clave: atracción, robot
montando, junta reconocida, robot soldando (demostración), juez soldando con puntos y resultado/ranking. Necesita el
simulador arrancado (`python -m lewelder.simulador`). Usa el Chromium del sistema con SwiftShader (sin GPU).
"""
from __future__ import annotations

import argparse
import asyncio
import json
import time
import urllib.request
from pathlib import Path

CHROMIUM = "/opt/pw-browsers/chromium"
MOMENTOS = [  # (nombre del archivo, condición sobre /api/estado, segundos extra de espera)
    ("01_atraccion", lambda e: True, 3.0),
    ("02_robot_montando", lambda e: e["pantalla"] == "montaje" and e["fase_robot"] in ("girando", "encajando"), 0.0),
    ("03_junta_reconocida", lambda e: e["pantalla"] == "reconocer" and e["junta"], 1.5),
    ("04_robot_senalando", lambda e: e["fase_robot"] == "señalando" and e["progreso_robot"] > 0.4, 0.0),
    ("05_robot_soldando", lambda e: e["pantalla"] == "demostracion" and e["fase_robot"] == "soldando"
     and e["progreso_robot"] > 0.45, 0.0),
    ("06_juez_soldando", lambda e: e["pantalla"] == "ronda" and e["n_muestras_juez"] > 500, 0.0),
    ("07_resultado", lambda e: e["pantalla"] == "resultado", 2.5),
    ("08_ranking", lambda e: e["pantalla"] == "ranking", 2.0),
]


PARTIDA = "captura"


def estado(url: str) -> dict:
    with urllib.request.urlopen(f"{url}/api/estado?partida={PARTIDA}", timeout=5) as r:
        return json.loads(r.read())


async def capturar(url: str, salida: Path, chromium: str, solo_inicio: bool = False, limite: float = 400.0):
    from playwright.async_api import async_playwright

    salida.mkdir(parents=True, exist_ok=True)
    rutas = []
    async with async_playwright() as pw:
        navegador = await pw.chromium.launch(executable_path=chromium,
                                             args=["--use-angle=swiftshader", "--enable-unsafe-swiftshader",
                                                   "--autoplay-policy=no-user-gesture-required"])
        pagina = await navegador.new_page(viewport={"width": 1920, "height": 1080})
        pagina.on("console", lambda m: m.type == "error" and print("consola:", m.text))
        pagina.on("pageerror", lambda e: print("error de la página:", e))
        await pagina.goto(f"{url}/?partida={PARTIDA}" + ("" if solo_inicio else "&guion=jurado"))
        await pagina.wait_for_function("window.lewelderSim && window.lewelderSim.listo", timeout=60000)
        t0 = time.monotonic()
        for nombre, condicion, extra in (MOMENTOS[:1] if solo_inicio else MOMENTOS):
            while not condicion(estado(url)):
                if time.monotonic() - t0 > limite:
                    print("tiempo agotado esperando", nombre, estado(url))
                    break
                await asyncio.sleep(0.3)
            await asyncio.sleep(extra)
            ruta = salida / f"{nombre}.png"
            await pagina.screenshot(path=str(ruta))
            e = estado(url)
            print(f"{ruta}  ·  pantalla {e['pantalla']}, física {e['hz_fisica']} Hz, publicación "
                  f"{e['hz_publicacion']} Hz, navegador {e['fps_navegador']} FPS", flush=True)
            rutas.append(ruta)
        await navegador.close()
    return rutas


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--url", default="http://localhost:8080")
    p.add_argument("--salida", type=Path, default=Path("salidas/capturas_sim"))
    p.add_argument("--chromium", default=CHROMIUM)
    p.add_argument("--solo-inicio", action="store_true")
    a = p.parse_args(argv)
    asyncio.run(capturar(a.url, a.salida, a.chromium, a.solo_inicio))


if __name__ == "__main__":
    main()
