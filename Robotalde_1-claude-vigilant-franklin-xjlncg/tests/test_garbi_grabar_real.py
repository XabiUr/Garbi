"""Grabación en el robot real de acercamientos guiados por código (ciclo final con el acercamiento programado), con
dobles: sin hardware. Un episodio va de la clavada a la levantada; si una guardia frena el brazo, se descarta."""
from types import SimpleNamespace as N

import numpy as np

from garbi import correr as C
from garbi.tipos import Broca, Escena, Orden, Taladro

IMG = {"top": np.zeros((48, 64, 3), np.uint8), "wrist": np.zeros((48, 64, 3), np.uint8)}


def _sesion(tmp_path, frenar_en=None):
    ciclo = N(agujeros=[], frenadas=0, saltos_habilidad=0)

    def lector(imgs, q, t):
        clavada = 1.0 <= t < 3.0
        evento = "clavada" if np.isclose(t, 1.0) else ("levantada" if np.isclose(t, 3.0) else None)
        return Escena(t=t, taladro=Taladro(visible=True, agarrado=True),
                      broca=Broca(punta=np.array([360.0, 0.0, 20.0]), apoyada=clavada,
                                  clavada_desde=1.0 if clavada else None, evento=evento))

    g, percepcion, al_ordenar = C.grabador_acercamiento_real(tmp_path / "ds", (64, 48), "local/prueba", ciclo, lector)
    for k in range(121):
        percepcion(IMG, np.zeros(6), k / 30)
        if frenar_en is not None and k == frenar_en:
            ciclo.frenadas += 1
        al_ordenar(IMG, Orden(q=np.full(6, k * 0.1), aspirar=True,
                              estado="acercamiento" if 30 <= k < 90 else "prudente"))
    return g.cerrar()


def test_un_acercamiento_de_la_clavada_a_la_levantada(tmp_path):
    r = _sesion(tmp_path)
    assert r["guardados"] == 1 and r["episodios"][0]["fin"] == "levantada"
    assert r["tarea"] == "Approach the drill bit." and r["origen"] == "real"


def test_si_la_guardia_frena_se_descarta(tmp_path):
    r = _sesion(tmp_path, frenar_en=60)
    assert r["guardados"] == 0 and "guardia" in r["motivos_descarte"]
