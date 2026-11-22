"""Capturas del componente de voz (web/voz.js) en su página de prueba, con el servidor de verdad y sin hardware.

    python herramientas/captura_voz.py [--salida salidas/capturas] [--chromium /opt/pw-browsers/chromium]

Arranca `crear_app` con la fuente simulada (sin leerla), abre `prueba_voz.html` y guarda:
- `voz.png`: "móntame una esquina" → tarjeta "¿Monto una unión en esquina?" con Sí / No.
- `voz_aclaracion.png`: "monta" → "¿T o esquina?" con un botón por junta.
- `voz_inicio.png`: el componente en reposo.
"""
from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from aiohttp.test_utils import TestServer

from lewelder.fuentes import FuenteSimulada
from lewelder.servidor import Escuela, crear_app

CHROMIUM = "/opt/pw-browsers/chromium"


async def capturar(salida: Path, chromium: str) -> list[Path]:
    from playwright.async_api import async_playwright

    salida.mkdir(parents=True, exist_ok=True)
    escuela = Escuela(FuenteSimulada("t", "B"), None, dir_pasadas=None)
    servidor = TestServer(crear_app(escuela, iniciar=False))
    await servidor.start_server()
    rutas = []
    try:
        async with async_playwright() as pw:
            navegador = await pw.chromium.launch(executable_path=chromium)
            pagina = await navegador.new_page(viewport={"width": 1100, "height": 720}, device_scale_factor=2)
            await pagina.goto(str(servidor.make_url("/prueba_voz.html")))
            await pagina.wait_for_selector(".vz")
            await pagina.wait_for_timeout(300)
            rutas.append(salida / "voz_inicio.png")
            await pagina.screenshot(path=rutas[-1])

            await pagina.fill(".vz-entrada", "monta")
            await pagina.press(".vz-entrada", "Enter")
            await pagina.wait_for_selector(".vz-opcion", state="visible")
            await pagina.wait_for_timeout(500)
            rutas.append(salida / "voz_aclaracion.png")
            await pagina.screenshot(path=rutas[-1])
            await pagina.click(".vz-opcion-no")  # "Nada": vuelve el micrófono

            await pagina.fill(".vz-entrada", "móntame una esquina")
            await pagina.press(".vz-entrada", "Enter")
            await pagina.wait_for_selector(".vz-tarjeta[data-tipo=confirmar]", state="visible")
            await pagina.wait_for_timeout(500)
            rutas.append(salida / "voz.png")
            await pagina.screenshot(path=rutas[-1])
            await navegador.close()
    finally:
        await servidor.close()
    return rutas


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--salida", type=Path, default=Path("salidas/capturas"))
    p.add_argument("--chromium", default=CHROMIUM)
    a = p.parse_args()
    for ruta in asyncio.run(capturar(a.salida, a.chromium)):
        print(ruta)


if __name__ == "__main__":
    main()
