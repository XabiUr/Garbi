"""Pruebas M8 del ciclo completo con percepción real (imágenes renderizadas) y ruido realista (`garbi.robustez`).

- 20 ciclos, cada uno con su semilla: madera girada ±8°, sitio al azar de la zona de taladro (320-420 mm), taladro
  inclinado 0-8° con rumbo cualquiera, velocidad de entrada ×0,6-1,6, broca quieta en el aire a 10-40 mm antes de
  apoyar y temblor de ±1-2 mm al taladrar. Criterios: ≥ 19/20 aciertos, holgura real ≥ 10 mm, borde ≥ 3 mm; de los 20
  apoyos, ≥ 18 detectados; de los 20 «en el aire», ningún apoyo falso.
- 5 seguidos y la pasada final: 5/5 y ≤ 3 min.

Muy lento (decenas de minutos; reparte las sesiones en procesos): `pytest -m lento tests/test_garbi_robustez.py`.
La tabla completa: `python herramientas/garbi_robustez_ciclo.py ciclos`.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "herramientas"))

N_CICLOS = 20
PROCESOS = int(os.environ.get("GARBI_PROCESOS", "4"))


def _render_o_saltar():
    try:
        from garbi.mundo import MundoGarbi

        MundoGarbi(render=True, montaje="lateral").imagen("top", (640, 480))
    except Exception as e:  # sin librerías de render
        pytest.skip(f"no hay render sin pantalla: {e}")


@pytest.fixture(scope="module")
def ciclos():
    _render_o_saltar()
    from garbi_robustez_ciclo import correr, tabla_ciclos

    res = correr(range(N_CICLOS), PROCESOS, agujeros=1)
    return res, tabla_ciclos(res)


@pytest.mark.lento
def test_veinte_ciclos_con_ruido(ciclos):
    res, tot = ciclos
    assert not [r for r in res if "error" in r], [r for r in res if "error" in r]
    assert tot["aciertos"] >= 19, tot
    assert tot["holgura_min"] >= 10.0 and tot["borde_min"] >= 3.0, tot


@pytest.mark.lento
def test_veinte_apoyos_y_veinte_en_el_aire(ciclos):
    _, tot = ciclos
    assert tot["apoyos_detectados"] >= 18, tot
    # M8: ningún apoyo falso con la broca quieta en el aire (10-40 mm). Las lecturas «apoyada» con la broca a > 8 mm
    # al levantarla (una lectura de retraso) se informan aparte en la tabla
    assert tot["aire_falsos"] == 0, tot


@pytest.mark.lento
def test_cinco_seguidos_y_pasada_final():
    _render_o_saltar()
    from garbi_robustez_ciclo import correr

    r = correr([0], 1, agujeros=5, pasada_final=True, flota=False)[0]
    assert "error" not in r, r
    assert r["aciertos"] == 5 and r["terminado"], r
    assert r["holgura_min"] >= 10.0 and r["borde_min"] >= 3.0, r
    assert sum(r["duraciones"]) + r["pasada_final"] <= 180.0, (r["duraciones"], r["pasada_final"])
    assert r["contactos_pasada"] == 0
