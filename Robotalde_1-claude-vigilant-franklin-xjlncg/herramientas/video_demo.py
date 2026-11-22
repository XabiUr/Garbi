"""Graba en vídeo la demo completa de la tablet con el robot SO-101 simulado en MuJoCo.

    MUJOCO_GL=egl python herramientas/video_demo.py [--dataset datos/lewelder_sim_160] [--salida salidas/video]

Los fotogramas se capturan con el screencast de Chromium (CDP) y el MP4 se monta con el ffmpeg del sistema: no
depende del ffmpeg propio de Playwright (que en la nube de Claude no coincide con la versión instalada).

Mismo recorrido que el guion del pitch: el alumno suelda la recta dejándose un hueco → nota y valoración del
maestro → Repaso (el robot recorre el cordón y el LED solo se enciende en el hueco) → una pasada perfecta →
certificado → modo Maestro (el robot suelda la unión en T). El robot usa la política `replay` (demostraciones
grabadas, declaradas como tales) porque es la que hoy suelda bien en simulación; con un checkpoint entrenado se
puede grabar igual con `--politica act|vla --checkpoint-...`.

Sale un MP4 (H.264, se ve en cualquier móvil) a 1280x800.
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import shutil
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from aiohttp import web  # noqa: E402

from herramientas.capturas_tablet import CHROMIUM, esperar  # noqa: E402
from lewelder.antorcha import AntorchaRobot  # noqa: E402
from lewelder.antorcha_virtual import AntorchaRobotVirtual  # noqa: E402
from lewelder.fuentes import ConfigPasada, FuenteSimulada  # noqa: E402
from lewelder.robot_mujoco import RobotMuJoCo  # noqa: E402
from lewelder.servidor import Escuela, crear_app  # noqa: E402

PUERTO = 8766
TAMANO = {"width": 1280, "height": 800}


async def grabar(salida: Path, dataset: Path, politica: str, checkpoints: dict, escala_robot: float,
                 chromium: str) -> Path:
    from playwright.async_api import async_playwright

    salida.mkdir(parents=True, exist_ok=True)
    crudo = salida / "crudo"
    shutil.rmtree(crudo, ignore_errors=True)
    virtual = AntorchaRobotVirtual()
    robot = RobotMuJoCo(politica=politica, dataset=dataset, escala_tiempo=escala_robot,
                        checkpoint_act=checkpoints.get("act"), checkpoint_vla=checkpoints.get("vla"))
    fuente = FuenteSimulada(config=ConfigPasada(huecos=[(40.0, 55.0)], temblor_mm=0.4), tiempo_real=True)
    escuela = Escuela(fuente, robot, AntorchaRobot(virtual.ruta), dir_pasadas=None)
    runner = web.AppRunner(crear_app(escuela))
    await runner.setup()
    await web.TCPSite(runner, "127.0.0.1", PUERTO).start()
    try:
        async with async_playwright() as pw:
            navegador = await pw.chromium.launch(executable_path=chromium, args=[
                "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"])
            contexto = await navegador.new_context(viewport=TAMANO)
            pagina = await contexto.new_page()
            pagina.on("console", lambda m: m.type == "error" and print("consola:", m.text))
            await pagina.goto(f"http://127.0.0.1:{PUERTO}/")
            await pagina.wait_for_function("window.lewelder && window.lewelder.estado.fuente.fuente === 'simulada'")
            # Fotogramas con su marca de tiempo por el screencast de Chromium (no depende del ffmpeg de Playwright).
            cdp = await contexto.new_cdp_session(pagina)
            fotogramas: list[tuple[float, bytes]] = []

            async def al_fotograma(ev):
                fotogramas.append((ev["metadata"]["timestamp"], base64.b64decode(ev["data"])))
                await cdp.send("Page.screencastFrameAck", {"sessionId": ev["sessionId"]})

            cdp.on("Page.screencastFrame", lambda ev: asyncio.ensure_future(al_fotograma(ev)))
            await cdp.send("Page.startScreencast", {"format": "jpeg", "quality": 80,
                                                    "maxWidth": TAMANO["width"], "maxHeight": TAMANO["height"]})
            await asyncio.sleep(2.0)

            print("1/4 examen con hueco", flush=True)
            await pagina.click("#b-examen")
            await esperar(lambda: escuela.modo == "nota" and escuela.valoracion is not None, timeout=180)
            await asyncio.sleep(5.0)  # que se lea la nota y la valoración

            print("2/4 repaso del robot", flush=True)
            await pagina.click("#b-repaso")
            await asyncio.sleep(1.0)
            await esperar(lambda: not escuela.robot_ocupado, timeout=600)
            await asyncio.sleep(4.0)

            print("3/4 pasada perfecta y certificado", flush=True)
            await pagina.click("#b-reiniciar")
            await escuela.orden({"orden": "simulacion", "pasada": "perfecta"})
            await asyncio.sleep(1.0)
            await pagina.click("#b-examen")
            await esperar(lambda: escuela.modo == "nota" and escuela.valoracion is not None, timeout=180)
            await asyncio.sleep(3.0)
            await pagina.click("#b-certificado")
            await esperar(lambda: escuela.modo == "certificado")
            await asyncio.sleep(4.0)

            print("4/4 maestro: el robot suelda la T", flush=True)
            await pagina.click("#cert-maestro")
            await asyncio.sleep(1.0)
            await esperar(lambda: not escuela.robot_ocupado, timeout=600)
            await asyncio.sleep(3.0)

            await cdp.send("Page.stopScreencast")
            await navegador.close()
    finally:
        await runner.cleanup()
        virtual.parar()

    # Cada fotograma dura hasta el siguiente (el screencast solo manda imágenes cuando la página cambia).
    crudo.mkdir(parents=True)
    fotogramas.sort(key=lambda f: f[0])
    lineas = ["ffconcat version 1.0"]
    for i, (t, jpeg) in enumerate(fotogramas):
        ruta = crudo / f"{i:06d}.jpg"
        ruta.write_bytes(jpeg)
        duracion = (fotogramas[i + 1][0] - t) if i + 1 < len(fotogramas) else 1.0
        lineas += [f"file '{ruta.name}'", f"duration {max(duracion, 0.001):.4f}"]
    lineas.append(f"file '{crudo / f'{len(fotogramas) - 1:06d}.jpg'}'")
    (crudo / "lista.txt").write_text("\n".join(lineas) + "\n")
    mp4 = salida / "demo_lewelder.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(crudo / "lista.txt"),
                    "-vf", "fps=25,scale=1280:-2", "-c:v", "libx264", "-preset", "medium", "-crf", "27",
                    "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(mp4)], check=True)
    print(f"vídeo: {mp4} ({len(fotogramas)} fotogramas)", flush=True)
    return mp4


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--salida", type=Path, default=RAIZ / "salidas" / "video")
    p.add_argument("--dataset", type=Path, default=RAIZ / "datos" / "lewelder_sim_160")
    p.add_argument("--politica", default="replay", choices=["replay", "act", "vla"])
    p.add_argument("--checkpoint-act")
    p.add_argument("--checkpoint-vla")
    p.add_argument("--escala-robot", type=float, default=1.5, help="1 = tiempo real; > 1 acelera el robot")
    p.add_argument("--chromium", default=CHROMIUM)
    a = p.parse_args()
    asyncio.run(grabar(a.salida, a.dataset, a.politica, {"act": a.checkpoint_act, "vla": a.checkpoint_vla},
                       a.escala_robot, a.chromium))


if __name__ == "__main__":
    main()
