"""Evaluación de políticas: puntuación de un recorrido, tablas por anclaje y comparativa VLA / ACT / replay."""
import copy
import json

import pytest

from lewelder import contrato as c
from lewelder.contrato import Muestra
from robot.evaluar import comparativa, evaluar_politica, evaluar_recorrido, guardar, main, tabla_politica
from robot.politica import cargar_politica


def _recorrido(desvio=0.0, hasta=125.0):
    """Recorrido ideal del robot: baja al inicio, avanza a 5 mm/s y se levanta."""
    muestras, t = [], 0.0
    for z in range(40, 3, -1):
        muestras.append(Muestra(t, -5.0, 0.0, float(z), False))
        t += 1 / 30
    x = -5.0
    while x < hasta:
        muestras.append(Muestra(t, x, desvio, 3.0, False))
        x += 5 / 30
        t += 1 / 30
    for z in range(3, 40):
        muestras.append(Muestra(t, x, desvio, float(z), False))
        t += 1 / 30
    return muestras


def test_evaluar_recorrido_criterio_de_la_spec():
    bien = evaluar_recorrido(_recorrido(), "recta")
    assert bien["exito"] and bien["cobertura_pct"] == 100.0 and bien["error_medio_mm"] == pytest.approx(0.0)
    assert bien["nota"] > 9
    desviado = evaluar_recorrido(_recorrido(desvio=6.0), "recta")  # fuera de ±5 mm
    assert not desviado["exito"] and desviado["error_medio_mm"] == pytest.approx(6.0)
    corto = evaluar_recorrido(_recorrido(hasta=90.0), "recta")
    assert not corto["exito"] and corto["huecos"]
    assert evaluar_recorrido(_recorrido(desvio=6.0), "recta", nivel="aprendiz")["exito"]  # a ±8 mm sí
    vacio = evaluar_recorrido([], "t")
    assert not vacio["exito"] and vacio["error_medio_mm"] is None


def test_evaluar_replay_y_comparativa(dataset_sim, tmp_path):
    raiz, _ = dataset_sim
    politica = cargar_politica("replay", dataset=raiz)
    informe = evaluar_politica("replay", politica, ["B", "D"], ["recta"], 2, verbose=False)
    assert informe["total"]["tasa_exito"] == 1.0 and informe["total"]["n"] == 4
    assert set(informe["por_anclaje"]) == {"B", "D"} and informe["por_anclaje"]["B"]["cumple_objetivo"]
    assert informe["por_anclaje_tipo"]["D/recta"]["exitos"] == 2
    assert all(r["episodio_replay"] is not None for r in informe["recorridos"])
    assert "| B | recta | 2/2 | 100 % |" in tabla_politica(informe)

    # Sin episodios de la T: cuenta como fallo, no rompe la evaluación.
    sin_t = evaluar_politica("replay", politica, ["B"], ["t"], 1, verbose=False)
    assert sin_t["total"]["tasa_exito"] == 0.0 and sin_t["recorridos"][0]["error"]

    rutas = guardar(informe, tmp_path)
    assert json.loads(rutas["json"].read_text())["politica"] == "replay"
    # Con otro informe (un ACT malo inventado), la comparativa pone las columnas en orden VLA, ACT, replay.
    act = copy.deepcopy(informe)
    act["politica"], act["nombre"] = "act", "ACT"
    for v in act["por_anclaje"].values():
        v.update(tasa_exito=0.0, exitos=0, error_medio_mm=7.5)
    act["total"].update(tasa_exito=0.0, error_medio_mm=7.5)
    rutas = guardar(act, tmp_path)
    md = rutas["comparativa_md"].read_text()
    assert "| Anclaje | ACT | Replay (grabado) |" in md
    assert "| B | 0 % (7.5) | 100 % (" in md
    assert set(json.loads(rutas["comparativa_json"].read_text())) == {"act", "replay"}
    md2, datos = comparativa({"replay": informe})
    assert "VLA" in md2.splitlines()[0] and set(datos) == {"replay"}


def test_cli_evaluar(dataset_sim, tmp_path, capsys):
    raiz, _ = dataset_sim
    main(["--politica", "replay", "act", "--dataset", str(raiz), "--anclajes", "D", "--tipos", "recta",
          "--repeticiones", "1", "--salida", str(tmp_path)])
    salida = capsys.readouterr().out
    assert "act: no disponible" in salida  # sin checkpoint se salta y sigue
    assert (tmp_path / "replay.md").exists() and (tmp_path / "comparativa.md").exists()
    assert not (tmp_path / "act.json").exists()
    datos = json.loads((tmp_path / "replay.json").read_text())
    assert datos["total"]["exitos"] == 1 and datos["nivel"] == c.NIVEL_JURADO
