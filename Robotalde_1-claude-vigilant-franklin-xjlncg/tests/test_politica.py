"""Políticas en simulación: filtro de dataset, reproducción grabada (replay) y carga e inferencia de un ACT corto."""
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from lewelder import contrato as c
from lewelder.contrato import Muestra
from lewelder.robot import punta_sobre_cordon
from robot.evaluar import evaluar_recorrido
from robot.politica import (DetectorFin, PoliticaLeRobot, PoliticaNoDisponible, PoliticaReplay, cargar_politica,
                            con_gatillo, ejecutar_politica, resolver_checkpoint)
from sim.entorno import EntornoSoldadura

RAIZ = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def entorno():
    ent = EntornoSoldadura(render=False)
    yield ent
    ent.cerrar()


# --- filtro de dataset ("aprende del mejor") ---------------------------------------------------------------------
def test_filtro_descarta_las_malas(dataset_sim):
    from lerobot.datasets.lerobot_dataset import LeRobotDataset

    raiz, resultados = dataset_sim
    variantes = [(r.variante, r.aceptada) for r in resultados]
    assert sorted(variantes) == [("buena", True), ("buena", True), ("parada", False), ("temblorosa", False)]
    assert all(r.nota >= 9.0 for r in resultados if r.aceptada)
    assert all(r.nota < 9.0 for r in resultados if not r.aceptada)
    notas = json.loads((raiz / "notas.json").read_text(encoding="utf-8"))
    assert notas["umbral_nota"] == 9.0 and notas["guardadas"] == 2 and notas["descartadas"] == 2
    assert notas["malas_descartadas"] == 2 and notas["buenas_descartadas"] == 0
    guardadas = [d for d in notas["demostraciones"] if d["aceptada"]]
    assert [d["episodio"] for d in guardadas] == [0, 1]
    assert all(d["episodio"] is None for d in notas["demostraciones"] if not d["aceptada"])
    # El dataset solo tiene las buenas, con su instrucción.
    ds = LeRobotDataset("local/lewelder_prueba", root=raiz)
    assert ds.num_episodes == 2
    tareas = {ds.meta.episodes[i]["tasks"][0] for i in range(2)}
    assert tareas == {c.instruccion_soldar("recta", "B"), c.instruccion_soldar("recta", "D")}


def test_trabajos_intercala_las_malas():
    from sim.demostraciones import MALAS, trabajos

    t = trabajos(8, ["A", "B", "C", "D"], ["recta", "t"], malas=4)
    assert len(t) == 12 and sum(v == "buena" for *_, v in t) == 8
    assert {v for *_, v in t if v != "buena"} == set(MALAS)
    assert any(v != "buena" for *_, v in t[:6])  # intercaladas, no todas al final


def test_demostraciones_malas_puntuan_peor(entorno):
    from sim.demostraciones import Guion, ejecutar, guion_malo, puntuar

    buena = puntuar(ejecutar(entorno, "C", "recta", Guion(), semilla=5))
    for variante in ("desvio", "rapida"):
        mala = puntuar(ejecutar(entorno, "C", "recta", guion_malo(Guion(), variante), semilla=5))
        assert mala.nota < 9.0 < buena.nota, variante
    desviada = puntuar(ejecutar(entorno, "C", "recta", guion_malo(Guion(), "desvio"), semilla=5))
    assert desviada.huecos  # se sale del cordón: queda un hueco a ±5 mm


# --- replay ------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("anclaje", ["B", "D"])
def test_replay_recorre_el_cordon_completo(dataset_sim, entorno, anclaje):
    raiz, _ = dataset_sim
    politica = cargar_politica("replay", dataset=raiz)
    assert isinstance(politica, PoliticaReplay) and not politica.necesita_imagenes
    muestras = ejecutar_politica(entorno, politica, "recta", anclaje)
    assert politica.terminada and len(muestras) == len(politica.episodios[politica.episodio])
    r = evaluar_recorrido(muestras, "recta")
    assert r["exito"] and r["cobertura_pct"] == 100.0
    assert r["error_medio_mm"] < 1.5 and r["error_max_mm"] < c.TOLERANCIAS["oficial"]
    assert not any(m.gatillo for m in muestras)  # el gatillo/LED lo decide quien puntúa


def test_replay_sin_episodio_de_esa_tarea(dataset_sim, entorno):
    politica = PoliticaReplay(dataset_sim[0])
    with pytest.raises(PoliticaNoDisponible):
        politica.reiniciar("t", "B", c.instruccion_soldar("t", "B"))
    with pytest.raises(PoliticaNoDisponible):
        PoliticaReplay(dataset_sim[0].parent / "no_existe")


def test_replay_sincroniza_a_mitad(dataset_sim):
    politica = PoliticaReplay(dataset_sim[0])
    politica.reiniciar("recta", "D", c.instruccion_soldar("recta", "D"))
    acciones = politica.episodios[politica.episodio]
    assert politica.sincronizar(acciones[0]) == 0  # el reposo: el principio, no el final
    mitad = len(acciones) // 2
    assert abs(politica.sincronizar(acciones[mitad]) - mitad) <= 3
    assert np.allclose(politica.accion({}), acciones[politica._i - 1])


def test_cargar_politica_sin_lo_necesario(tmp_path):
    with pytest.raises(PoliticaNoDisponible):
        cargar_politica("act")
    with pytest.raises(PoliticaNoDisponible):
        cargar_politica("vla", checkpoint=tmp_path)
    with pytest.raises(PoliticaNoDisponible):
        cargar_politica("replay")
    with pytest.raises(ValueError):
        cargar_politica("pi0", checkpoint=tmp_path)
    with pytest.raises(PoliticaNoDisponible):
        resolver_checkpoint(tmp_path)


def test_gatillo_del_robot_solo_encima_del_cordon():
    assert punta_sobre_cordon(Muestra(0, 60.0, 1.0, 3.0, False))
    assert not punta_sobre_cordon(Muestra(0, 60.0, 1.0, 20.0, False))  # levantada
    assert not punta_sobre_cordon(Muestra(0, 130.0, 0.0, 3.0, False))  # pasado el final
    assert not punta_sobre_cordon(Muestra(0, 15.0, 210.0, -45.0, False))  # brazo en reposo, lejos y por debajo
    assert [m.gatillo for m in con_gatillo([Muestra(0, 60.0, 1.0, 3.0, False)])] == [True]


def test_detector_de_fin():
    fin = DetectorFin()
    assert not any(fin.actualizar(Muestra(i / 30, x, 0.0, 3.0, False)) for i, x in enumerate(np.linspace(0, 120, 60)))
    assert fin.paso_final
    quieto = [fin.actualizar(Muestra(2 + i / 30, 120.0, 0.0, 60.0, False)) for i in range(40)]
    assert quieto[-1] and not quieto[0]


# --- ACT corto: entrenar 2 pasos, cargar e inferir ----------------------------------------------------------------
@pytest.mark.lento
def test_act_corto_carga_e_infiere(dataset_sim, tmp_path):
    raiz, _ = dataset_sim
    salida = tmp_path / "act"
    entorno_proc = {**os.environ, "PYTHONPATH": str(RAIZ)}
    cmd = [str(Path(sys.executable).with_name("lerobot-train")), "--dataset.repo_id=local/lewelder_prueba",
           f"--dataset.root={raiz}", "--policy.type=act", "--policy.device=cpu", "--policy.push_to_hub=false",
           "--policy.dim_model=64", "--policy.dim_feedforward=128", "--policy.chunk_size=20",
           "--policy.n_action_steps=20", "--batch_size=2", "--steps=2", "--num_workers=0", "--save_freq=2",
           f"--output_dir={salida}", "--job_name=act_prueba"]
    proc = subprocess.run(cmd, env=entorno_proc, capture_output=True, text=True, timeout=600)
    assert proc.returncode == 0, proc.stderr[-3000:]
    politica = cargar_politica("act", checkpoint=salida)  # acepta la carpeta de salida del entrenamiento
    assert isinstance(politica, PoliticaLeRobot) and politica.tipo_lerobot == "act"
    assert set(politica.camaras) == {"observation.images.cenital", "observation.images.muneca"}
    ent = EntornoSoldadura(resolucion=(64, 48), render=True)
    try:
        acciones = []
        orig = politica.accion
        politica.accion = lambda obs: acciones.append(orig(obs)) or acciones[-1]
        muestras = ejecutar_politica(ent, politica, "recta", "B", max_pasos=30)
    finally:
        ent.cerrar()
    assert len(muestras) == 30 and politica.n_inferencias == 30
    a = np.array(acciones)
    assert a.shape == (30, 6) and np.all(np.isfinite(a))
    assert all(np.isfinite([m.x, m.y, m.z]).all() for m in muestras)
