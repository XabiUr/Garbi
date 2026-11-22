"""Capturas (1280x800) y vídeo de la tablet arcade v2 con la maqueta (`web/v2/index.html?maqueta=1`).

    python herramientas/capturas_v2.py [--salida salidas/capturas_v2] [--video] [--sin-capturas]

No arranca el servidor de LeWelder: sirve `web/` con un servidor estático y la maqueta hace de servidor. Las capturas
se toman en momentos fijos de cada escena (`&pantalla=...`); el vídeo graba la ronda completa (~95 s) con el
screencast de Chromium (CDP) y lo monta con el ffmpeg del sistema, como `video_demo.py`.
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import functools
import shutil
import subprocess
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
CHROMIUM = "/opt/pw-browsers/chromium"
PUERTO = 8781
TAMANO = {"width": 1280, "height": 800}
ARGS_CHROMIUM = ["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist",
                 "--autoplay-policy=no-user-gesture-required"]

# (archivo, parámetros de la maqueta, segundos de espera desde que carga o condición JS que esperar)
CAPTURAS = [
    ("01-atraccion.png", "pantalla=atraccion", 8.0),
    ("02-pedir-escuchando.png", "pantalla=pedir", 3.0),
    ("03-pedir-confirmar.png", "pantalla=pedir", 5.0),
    ("04-montaje.png", "pantalla=montaje", 6.5),
    ("05-reconocer.png", "pantalla=reconocer", 3.2),
    ("06-reconocer-perfil.png", "pantalla=reconocer", 6.6),
    ("07-reconocer-girala.png", "pantalla=reconocer&alcance=no", 3.2),
    ("08-demostracion.png", "pantalla=demostracion", 5.0),
    ("09-cuenta-atras.png", "pantalla=cuenta_atras", 1.6),
    ("10-cuenta-suelda.png", "pantalla=cuenta_atras", 3.2),
    ("11-ronda-combo.png", "pantalla=ronda", 9.4),
    ("12-ronda-apoya.png", "pantalla=ronda", "!document.querySelector('#aviso-apoyo').hidden"),
    ("13-ronda-quemado.png", "pantalla=ronda", "[...document.querySelectorAll('.sello.malo')].some(e => /QUEMADO/.test(e.textContent))"),
    ("14-ronda-adelanta.png", "pantalla=ronda", "[...document.querySelectorAll('.sello.epico')].some(e => /ADELANTAS/.test(e.textContent))"),
    ("15-resultado.png", "pantalla=resultado", 5.0),
    ("16-resultado-robot-gana.png", "pantalla=resultado&gana=robot", 4.0),
    ("17-iniciales.png", "pantalla=iniciales", 2.6),
    ("18-ranking.png", "pantalla=ranking", 2.0),
    ("19-plan-b.png", "pantalla=plan_b", 3.0),
    ("20-junta-t.png", "pantalla=reconocer&junta=t", 3.2),
]


def servir(directorio: Path, puerto: int) -> ThreadingHTTPServer:
    class Silencioso(SimpleHTTPRequestHandler):
        def log_message(self, *a):  # noqa: D102
            pass

    srv = ThreadingHTTPServer(("127.0.0.1", puerto), functools.partial(Silencioso, directory=str(directorio)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


async def capturar(salida: Path, chromium: str, solo: list[str] | None) -> None:
    from playwright.async_api import async_playwright

    salida.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as pw:
        nav = await pw.chromium.launch(executable_path=chromium, args=ARGS_CHROMIUM)
        for nombre, params, espera in CAPTURAS:
            if solo and not any(s in nombre for s in solo):
                continue
            pag = await nav.new_page(viewport=TAMANO, device_scale_factor=1)
            pag.on("console", lambda m: m.type == "error" and print("consola:", m.text))
            pag.on("pageerror", lambda e: print("error:", e))
            await pag.goto(f"http://127.0.0.1:{PUERTO}/v2/index.html?maqueta=1&{params}")
            await pag.wait_for_function("window.lewelder && window.lewelder.st.pantalla")
            if isinstance(espera, str):
                await pag.wait_for_function(espera, timeout=60000)
                await asyncio.sleep(0.25)
            else:
                await asyncio.sleep(espera)
            await pag.screenshot(path=str(salida / nombre))
            print("captura:", salida / nombre, flush=True)
            await pag.close()
        await nav.close()


async def grabar(salida: Path, chromium: str, segundos: float) -> Path:
    from playwright.async_api import async_playwright

    salida.mkdir(parents=True, exist_ok=True)
    crudo = salida / "crudo"
    shutil.rmtree(crudo, ignore_errors=True)
    async with async_playwright() as pw:
        nav = await pw.chromium.launch(executable_path=chromium, args=ARGS_CHROMIUM)
        ctx = await nav.new_context(viewport=TAMANO)
        pag = await ctx.new_page()
        pag.on("pageerror", lambda e: print("error:", e))
        await pag.goto(f"http://127.0.0.1:{PUERTO}/v2/index.html?maqueta=1")
        await pag.wait_for_function("window.lewelder && window.lewelder.st.pantalla")
        cdp = await ctx.new_cdp_session(pag)
        fotogramas: list[tuple[float, bytes]] = []

        async def al_fotograma(ev):
            fotogramas.append((ev["metadata"]["timestamp"], base64.b64decode(ev["data"])))
            await cdp.send("Page.screencastFrameAck", {"sessionId": ev["sessionId"]})

        cdp.on("Page.screencastFrame", lambda ev: asyncio.ensure_future(al_fotograma(ev)))
        await cdp.send("Page.startScreencast", {"format": "jpeg", "quality": 80,
                                                "maxWidth": TAMANO["width"], "maxHeight": TAMANO["height"]})
        await asyncio.sleep(segundos)
        await cdp.send("Page.stopScreencast")
        await nav.close()

    crudo.mkdir(parents=True)
    fotogramas.sort(key=lambda f: f[0])
    lineas = ["ffconcat version 1.0"]
    for i, (t, jpeg) in enumerate(fotogramas):
        ruta = crudo / f"{i:06d}.jpg"
        ruta.write_bytes(jpeg)
        duracion = (fotogramas[i + 1][0] - t) if i + 1 < len(fotogramas) else 1.0
        lineas += [f"file '{ruta.name}'", f"duration {max(duracion, 0.001):.4f}"]
    lineas.append(f"file '{len(fotogramas) - 1:06d}.jpg'")
    (crudo / "lista.txt").write_text("\n".join(lineas) + "\n")
    mp4 = salida / "maqueta_v2.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(crudo / "lista.txt"),
                    "-vf", "fps=25,scale=1280:-2", "-c:v", "libx264", "-preset", "medium", "-crf", "26",
                    "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(mp4)], check=True)
    shutil.rmtree(crudo, ignore_errors=True)
    print(f"vídeo: {mp4} ({len(fotogramas)} fotogramas)", flush=True)
    return mp4


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--salida", type=Path, default=RAIZ / "salidas" / "capturas_v2")
    p.add_argument("--chromium", default=CHROMIUM)
    p.add_argument("--video", action="store_true", help="graba también el vídeo de la maqueta")
    p.add_argument("--segundos", type=float, default=98.0, help="duración del vídeo")
    p.add_argument("--sin-capturas", action="store_true")
    p.add_argument("--solo", nargs="*", help="solo las capturas cuyo nombre contenga alguno de estos textos")
    a = p.parse_args()
    srv = servir(RAIZ / "web", PUERTO)
    try:
        if not a.sin_capturas:
            asyncio.run(capturar(a.salida, a.chromium, a.solo))
        if a.video:
            asyncio.run(grabar(a.salida, a.chromium, a.segundos))
    finally:
        srv.shutdown()


if __name__ == "__main__":
    main()
