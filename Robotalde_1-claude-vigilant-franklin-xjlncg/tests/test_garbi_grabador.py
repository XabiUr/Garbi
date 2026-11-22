"""Grabación del paso 7 dentro del ciclo (`garbi.grabador.GrabadorCiclo`) con un ciclo de mentira: un LIMPIAR que
acaba limpio se guarda; uno que acaba en repaso (sucio según la percepción) se descarta y se apunta por qué."""
import json
from types import SimpleNamespace

import numpy as np

from garbi.grabador import ARCHIVO_EPISODIOS, GrabadorCiclo, GrabadorLimpiezas


class _Estado:
    def __init__(self, v):
        self.value = v


def _ciclo():
    return SimpleNamespace(estado=_Estado("aparcado"), respaldo=None, _hab_activa=None, habilidad=SimpleNamespace(
        nombre="espiral"), _agujero=0, agujeros=[np.array([1.0, 2.0])], _t=0.0, _repasos=0, limpios=set())


def _pasos(gc, ciclo, estados, imagenes):
    for k, e in enumerate(estados):
        ciclo.estado = _Estado(e)
        q = np.full(6, float(k))
        q[4] = q[5] = 0.0
        gc.paso(ciclo, SimpleNamespace(estado=e, q=q), imagenes if e == "limpiar" else {})


def test_grabador_ciclo_guarda_limpio_y_descarta_sucio(tmp_path):
    from lerobot.datasets.lerobot_dataset import LeRobotDataset

    raiz = tmp_path / "ciclo"
    gc = GrabadorCiclo(GrabadorLimpiezas(raiz, "local/prueba_ciclo", (32, 24)), verdad=lambda i: 0)
    ciclo = _ciclo()
    imgs = {"top": np.zeros((48, 64, 3), np.uint8), "wrist": np.full((48, 64, 3), 200, np.uint8)}
    # 1.º: limpiar 10 pasos → revisar → sucio (repaso: vuelve a ir_a_limpiar)
    _pasos(gc, ciclo, ["ir_a_limpiar"] + ["limpiar"] * 10 + ["revisar"] * 3 + ["ir_a_limpiar"], imgs)
    # 2.º: limpiar 8 pasos → revisar → limpio
    _pasos(gc, ciclo, ["limpiar"] * 8 + ["revisar"] * 2, imgs)
    ciclo.limpios.add(0)
    _pasos(gc, ciclo, ["aparcar"], imgs)
    r = gc.cerrar()
    assert r["intentos"] == 2 and r["guardados"] == 1 and r["descartados"] == 1
    assert r["motivos_descarte"] == {"sucio según la percepción": 1}
    ds = LeRobotDataset("local/prueba_ciclo", root=raiz)
    assert ds.num_episodes == 1 and ds.num_frames == 8
    assert tuple(ds[0]["observation.images.top"].shape) == (3, 24, 32)
    # state = la orden anterior (lo que el ciclo da a la habilidad); action = la orden de ese paso
    assert float(ds[1]["observation.state"][0]) == float(ds[0]["action"][0])
    assert json.loads((raiz / ARCHIVO_EPISODIOS).read_text())["episodios"][1]["viruta_verdad"] == 0
