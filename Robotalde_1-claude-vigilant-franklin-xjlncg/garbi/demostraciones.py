"""Demostraciones de limpieza de Garbi en simulación, grabadas en un `LeRobotDataset` para entrenar el VLA.

    python -m garbi.demostraciones --salida datos/garbi_sim --episodios 40 [--resolucion 256x192]

Cada episodio es una de las dos órdenes del VLA (vocabulario cerrado, en `task`):
- `ORDEN_AGUJERO` («Clean around the new hole.»): tabla en pose aleatoria con 0-3 agujeros viejos ya limpios y uno
  nuevo con su anillo de viruta; el robot empieza junto a la broca, por la izquierda o la derecha (donde lo deja el
  ciclo real) y a veces la tabla se
  ha movido después de taladrar. El VLA tiene que ir a la viruta, no a cualquier agujero.
- `ORDEN_ALFOMBRILLA` («Clean the chips on the mat.»): un puñado de serrín en un punto aleatorio de la alfombrilla,
  fuera de la tabla; el robot empieza aparcado.

El demostrador es la línea base programada (zigzag sobre la viruta que da el oráculo) con la aspiradora encendida.
Filtro «aprende del mejor»: el episodio solo se guarda si recoge al menos `MIN_RECOGIDA` de la viruta. Al final se
queda quieto `T_QUIETO` s para que la política aprenda a parar.

Features como `lerobot-record` con el SO-101 (estado y acción de 6 motores, cámaras `top` y `wrist`), así que el
dataset sirve tal cual para `lerobot-train` (SmolVLA con `--rename_map` top→camera1, wrist→camera2, o ACT).
"""
from __future__ import annotations

import argparse
import json
import shutil
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

from garbi import contrato as g
from garbi.contrato import punto_serrin_tapete
from garbi.control import ControlBoca
from garbi.mundo import APARCADO, EN_ALFOMBRILLA, EN_TABLA, FUERA, NOMBRES_MOTORES, MundoGarbi
from garbi.robot_vivo import LineaBase, PercepcionOraculo

ROBOT_TYPE = "so101_follower"
MIN_RECOGIDA = 0.95
T_QUIETO = 0.5  # s quieto al final del episodio
MAX_AGUJEROS_VIEJOS = 3


@dataclass
class Episodio:
    indice: int
    orden: str
    semilla: int
    fotogramas: int
    viruta_inicial: int
    viruta_final: int
    guardado: bool
    episodio_dataset: int | None = None

    @property
    def recogida(self) -> float:
        return 1.0 - self.viruta_final / max(self.viruta_inicial, 1)


def caracteristicas(resolucion=g.RESOLUCION_POLITICA) -> dict:
    """Features del dataset, construidas como las de `lerobot-record` con el SO-101 seguidor real."""
    from lerobot.utils.feature_utils import hw_to_dataset_features

    ancho, alto = resolucion
    motores = dict.fromkeys(NOMBRES_MOTORES, float)
    camaras = {cam: (alto, ancho, 3) for cam in g.CAMARAS_POLITICA}
    return {**hw_to_dataset_features(motores, "action"),
            **hw_to_dataset_features({**motores, **camaras}, "observation")}


# --- preparar la escena de cada orden ----------------------------------------------------------------------------
def _borrar_viruta_tabla(m: MundoGarbi) -> None:
    m.juez.viruta_donde[m.juez.viruta_donde == EN_TABLA] = FUERA
    m._actualizar_objetos()


def _punto_alcanzable_en_tabla(m: MundoGarbi, rng, margen_radio=(15, 25)) -> np.ndarray:
    tabla = m.juez.tabla
    for _ in range(100):
        p = tabla.a_mesa(rng.uniform([-45, -28], [45, 28]))
        if g.RADIO_TRABAJO_MIN + margen_radio[0] <= np.linalg.norm(p) <= g.RADIO_TRABAJO_MAX - margen_radio[1]:
            return p
    raise RuntimeError("no hay punto alcanzable en la tabla")


def preparar_agujero(m: MundoGarbi, ctl: ControlBoca, rng) -> np.ndarray:
    """Agujeros viejos limpios, uno nuevo con viruta y el robot junto a la broca. Devuelve la postura inicial."""
    for _ in range(int(rng.integers(0, MAX_AGUJEROS_VIEJOS + 1))):
        p = _punto_alcanzable_en_tabla(m, rng, (0, 0))
        m.poner_taladro(*p)
        m.taladrar()
    _borrar_viruta_tabla(m)
    p = _punto_alcanzable_en_tabla(m, rng)
    m.poner_taladro(*p)
    lado = int(rng.choice([-1, 1]))
    plan, lado, _ = ctl.acercarse_al_taladro(APARCADO, m.juez.taladro_punta, lado)
    plan += ctl.afinar(plan[-1], m.juez.taladro_punta, lado)
    m.taladrar()
    m.quitar_taladro()
    if rng.random() < 0.5:  # el usuario ha movido la tabla después de retirar el taladro
        m.mover_tabla(*rng.uniform([-15, -15, -10], [15, 15, 10]))
    return plan[-1], lado


def preparar_alfombrilla(m: MundoGarbi, rng) -> np.ndarray:
    tabla = m.juez.tabla
    for _ in range(100):
        p = punto_serrin_tapete(rng)
        if (not tabla.contiene(p, margen=-15)) and np.linalg.norm(p) <= g.RADIO_LIMPIAR_TAPETE - 20:
            break
    m.tirar_serrin(p[0], p[1], n=int(rng.integers(15, 31)), radio=float(rng.uniform(8, 16)))
    return np.asarray(APARCADO, float), int(rng.choice([-1, 1]))


# --- un episodio ---------------------------------------------------------------------------------------------------
def ejecutar_episodio(m: MundoGarbi, orden: str, semilla: int, al_fotograma=None) -> tuple[int, int, int]:
    """Prepara la escena de `orden`, limpia con la línea base y llama a `al_fotograma(obs, accion)` en cada
    fotograma. Devuelve (fotogramas, viruta inicial, viruta final) de la zona de la orden."""
    rng = np.random.default_rng(semilla)
    m.reset(semilla=semilla)
    ctl = ControlBoca(m.cin)
    if orden == g.ORDEN_AGUJERO:
        q0, lado = preparar_agujero(m, ctl, rng)
        donde = EN_TABLA
    else:
        q0, lado = preparar_alfombrilla(m, rng)
        donde = EN_ALFOMBRILLA
    m.reset_robot(q0)
    inicial = len(m.viruta_en_mesa(donde))

    habilidad = LineaBase(ctl, lado)
    habilidad.empezar(orden, m.estado(), PercepcionOraculo(m))
    m.aspiradora = True
    obs = m.observacion()
    n = 0
    accion = m.estado()
    quieto = int(T_QUIETO * g.FPS)
    while True:
        a = habilidad.accion(m.estado(), obs)
        if a is None:
            if quieto == 0:
                break
            quieto -= 1
        else:
            accion = np.asarray(a, np.float32)
        if al_fotograma is not None:
            al_fotograma(obs, accion)
        obs = m.step(accion, observar=al_fotograma is not None)
        n += 1
    m.aspiradora = False
    return n, inicial, len(m.viruta_en_mesa(donde))


# --- grabar ----------------------------------------------------------------------------------------------------------
def grabar(salida: Path, repo_id: str, episodios: int, resolucion=g.RESOLUCION_POLITICA, semilla: int = 0,
           sobrescribir: bool = False, min_recogida: float = MIN_RECOGIDA) -> list[Episodio]:
    """Graba `episodios` demostraciones alternando las dos órdenes. Solo guarda las que limpian bien."""
    from lerobot.datasets.lerobot_dataset import LeRobotDataset

    salida = Path(salida)
    if salida.exists():
        if not sobrescribir:
            raise FileExistsError(f"{salida} ya existe (usa --sobrescribir)")
        shutil.rmtree(salida)
    ds = LeRobotDataset.create(repo_id=repo_id, fps=g.FPS, features=caracteristicas(resolucion), root=salida,
                               robot_type=ROBOT_TYPE, use_videos=True, image_writer_threads=4)
    m = MundoGarbi(render=True, sombras=False, resolucion_politica=resolucion)
    resultados: list[Episodio] = []
    try:
        for i in range(episodios):
            orden = g.ORDENES_VLA[i % len(g.ORDENES_VLA)]
            t0 = time.perf_counter()

            def guardar(obs, accion):
                ds.add_frame({**{k: v for k, v in obs.items()}, "action": accion, "task": orden})

            n, ini, fin = ejecutar_episodio(m, orden, semilla + i, guardar)
            ep = Episodio(i, orden, semilla + i, n, ini, fin, guardado=False)
            if ini > 0 and ep.recogida >= min_recogida:
                ep.guardado, ep.episodio_dataset = True, ds.num_episodes
                ds.save_episode(parallel_encoding=False)  # sin fork: el render usa hilos
            else:
                ds.clear_episode_buffer()
            resultados.append(ep)
            print(f"demo {i:3d}  {orden:30s} {n:4d} fotogramas  viruta {ini:2d}→{fin:2d}  "
                  f"{'GUARDADA' if ep.guardado else 'descartada'}  {time.perf_counter() - t0:5.1f} s", flush=True)
    finally:
        ds.finalize()
        (salida / "episodios_garbi.json").write_text(
            json.dumps([asdict(e) | {"recogida": e.recogida} for e in resultados], indent=2, ensure_ascii=False))
    return resultados


def _resolucion(texto: str) -> tuple[int, int]:
    ancho, alto = texto.lower().split("x")
    return int(ancho), int(alto)


def main(argv=None) -> None:
    p = argparse.ArgumentParser(description="Graba demostraciones de limpieza de Garbi en un LeRobotDataset.")
    p.add_argument("--salida", type=Path, default=Path("datos/garbi_sim"))
    p.add_argument("--repo-id", default="local/garbi_sim")
    p.add_argument("--episodios", type=int, default=40)
    p.add_argument("--resolucion", type=_resolucion, default=g.RESOLUCION_POLITICA, help="ANCHOxALTO")
    p.add_argument("--semilla", type=int, default=0)
    p.add_argument("--sobrescribir", action="store_true")
    a = p.parse_args(argv)
    res = grabar(a.salida, a.repo_id, a.episodios, a.resolucion, a.semilla, a.sobrescribir)
    guardados = sum(e.guardado for e in res)
    print(f"{guardados}/{len(res)} episodios guardados en {a.salida}")


if __name__ == "__main__":
    main()
