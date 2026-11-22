"""Graba demostraciones del ACERCAMIENTO (solución final) en un LeRobotDataset.

    python herramientas/garbi_grabar_acercamiento.py --sim --intentos 40 --salida datos/garbi_acercamiento \\
        --render 320x240 --resolucion 160x120 [--push usuario/garbi_acercamiento]

En la simulación corre el ciclo final con el acercamiento programado y la verdad de la simulación, con el juez de la
sesión (`garbi.sesion.JuezSesion`) en intentos al azar (`intentos_grabacion`): sitios por la zona de taladro, madera
en una pose al azar, la mitad con la broca deslizada a otro punto a mitad del acercamiento (el programado se
corrige), un tercio con la mano libre que se cruza junto a la boca (el robot se aparta y vuelve) y algunos con
re-clavada. Cada episodio va de la clavada a la levantada (corte automático por la percepción,
`garbi.grabador.CorteAcercamiento`); se descartan los cortos y los que tienen contacto.

En el robot real, el mismo grabador (`garbi.grabador.GrabadorAcercamiento`) con teleoperación:
`herramientas/garbi_teleop_grabar.py --corte auto`.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _res(texto: str) -> tuple[int, int]:
    a, b = texto.lower().split("x")
    return int(a), int(b)


def argumentos(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--sim", action="store_true", required=True, help="en la simulación (el real: garbi_teleop_grabar)")
    p.add_argument("--intentos", type=int, default=10, help="intentos del juez (uno o dos acercamientos cada uno)")
    p.add_argument("--salida", required=True, help="carpeta del LeRobotDataset nuevo")
    p.add_argument("--repo-id", default="local/garbi_acercamiento")
    p.add_argument("--render", default="320x240", help="ANCHOxALTO del render de las cámaras")
    p.add_argument("--resolucion", default="160x120", help="ANCHOxALTO de las imágenes del dataset")
    p.add_argument("--semilla", type=int, default=0)
    p.add_argument("--madera-fija", action="store_true", help="madera en (360, 0, 0°) en vez de al azar")
    p.add_argument("--sobrescribir", action="store_true")
    p.add_argument("--push", help="repo del Hub al que subir el dataset al acabar")
    return p.parse_args(argv)


def main(argv=None) -> dict:
    ns = argumentos(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s", datefmt="%H:%M:%S")

    from garbi import contrato as g
    from garbi.correr import correr_sim_final
    from garbi.robustez import madera_al_azar
    from garbi.sesion import intentos_grabacion

    rng = np.random.default_rng(ns.semilla)
    tabla = g.PoseTabla(360.0, 0.0, 0.0) if ns.madera_fija else madera_al_azar(rng)
    intentos = intentos_grabacion(rng, ns.intentos, tabla)
    juez, ciclo, grabador = correr_sim_final(intentos, verdad=True, semilla=ns.semilla, tabla=tabla,
                                             grabar=ns.salida, grabar_resolucion=_res(ns.resolucion),
                                             repo_id=ns.repo_id, render=_res(ns.render), sobrescribir=ns.sobrescribir)
    r = grabador.g.resumen()
    res = juez.resumen()
    print(json.dumps({"guardados": r["guardados"], "intentos_grabados": r["intentos"],
                      "descartes": r["motivos_descarte"], "aciertos_juez": f"{res['aciertos']}/{res['intentos']}",
                      "holgura_min": res["holgura_min"], "holgura_mano_min": res["holgura_mano_min"],
                      "borde_min": res["borde_min"], "apartadas_mano": ciclo.apartadas_mano,
                      "tabla": [round(tabla.x, 1), round(tabla.y, 1), round(tabla.giro, 1)]}, ensure_ascii=False))
    if ns.push and r["guardados"]:
        from lerobot.datasets.lerobot_dataset import LeRobotDataset

        LeRobotDataset(ns.repo_id, root=ns.salida).push_to_hub(repo_id=ns.push, private=True)
    return r


if __name__ == "__main__":
    main()
