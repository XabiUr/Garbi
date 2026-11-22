"""Integración de Garbi (T6): imágenes renderizadas a 640 × 480 → `Percepcion` (calibrada con el tapete y el anillo
verde) → `Ciclo` → `CuerpoSim`, con la habilidad programada y el juez simulado (`garbi.correr.JuezSim`).

La percepción no lee nada de la verdad de la simulación; el juez sí, solo para medir. Lento (renderiza a 15 Hz):
`pytest -m lento tests/test_garbi_integracion.py`. Necesita render sin pantalla (MUJOCO_GL=egl u osmesa).
"""
from __future__ import annotations

import numpy as np
import pytest

from garbi.tipos import UMBRAL_FRACCION_VIRUTA

SITIOS = [(-20.0, 40.0), (45.0, 20.0)]  # uno cerca (a 60°) y otro en la mitad lejana (a 45-55°)


@pytest.fixture(scope="module")
def sesion(tmp_path_factory):
    from garbi.correr import correr_sim
    from garbi.mundo import MundoGarbi

    try:
        mundo = MundoGarbi(render=True, montaje="lateral")
        mundo.imagen("top", (640, 480))
    except Exception as e:  # sin librerías de render
        pytest.skip(f"no hay render sin pantalla: {e}")
    juez, ciclo, detector, lector = correr_sim(SITIOS, registros=tmp_path_factory.mktemp("registros"), mundo=mundo,
                                               segundos=400.0)
    print("\n", juez.resumen())
    return juez, ciclo, detector, lector


@pytest.mark.lento
def test_dos_ciclos_con_percepcion_real(sesion):
    juez, ciclo, _, _ = sesion
    res = juez.resumen()
    assert juez.terminado and res["agujeros"] == len(SITIOS)
    assert res["aciertos"] == len(SITIOS), res  # agujero limpio (verdad) y sin contacto
    # Especificación (M4): holgura ≥ 10 mm con el taladro de verdad (la guardia suma a los 10 mm el error de la
    # percepción, `ciclo.MARGEN_PERCEPCION`) y borde ≥ 3 mm
    assert res["holgura_min"] >= 10.0 and res["borde_min"] >= 3.0, res
    assert all(15.0 <= d <= 45.0 for d in res["duraciones"]), res["duraciones"]
    assert ciclo.limpios == set(range(len(SITIOS))) and not ciclo.fallidos


@pytest.mark.lento
def test_percepcion_sin_fallos(sesion):
    juez, ciclo, _, lector = sesion
    res = juez.resumen()
    assert res["apoyo_no_visto"] == 0 and res["apoyos_falsos"] == 0, res
    assert all(res["agujero_apuntado"]), (res, ciclo.agujeros)  # agujeros a < 3 mm de los de verdad
    assert lector.lecturas > 0
    # la viruta que ve la percepción al acabar está por debajo del umbral (fracción del círculo)
    assert all(f < UMBRAL_FRACCION_VIRUTA for f in lector.ultima.viruta_fraccion.values())


@pytest.mark.lento
def test_pasada_final_y_registro(sesion):
    juez, ciclo, detector, _ = sesion
    assert juez.duracion_pasada > 5.0 and juez.contactos_pasada == 0
    assert ("aparcado", "pasada_final") in {(tr.de, tr.a) for tr in ciclo.transiciones}
    assert len(detector.resumenes) >= len(SITIOS) and all(r.acierto for r in detector.resumenes[:len(SITIOS)])
    assert np.isfinite(juez.holgura_min)


@pytest.mark.lento
def test_primer_agujero_con_la_broca_vista_de_lado(tmp_path):
    """(310, 90) en la mesa, primer agujero (sin apoyos que corrijan la altura por la bola): la muñeca ve la broca de
    lado. Antes la postura de mirar pasaba a < 10 mm del taladro y el ciclo no llegaba a acompañar."""
    from garbi.correr import correr_sim
    from garbi.mundo import MundoGarbi

    try:
        mundo = MundoGarbi(render=True, montaje="lateral")
        mundo.imagen("top", (640, 480))
    except Exception as e:  # sin librerías de render
        pytest.skip(f"no hay render sin pantalla: {e}")
    juez, ciclo, _, _ = correr_sim([(310.0 - 360.0, 90.0)], registros=tmp_path, mundo=mundo, segundos=200.0)
    res = juez.resumen()
    assert res["aciertos"] == 1 and res["apoyo_no_visto"] == 0, res
    assert ("preapunto", "acompanar") in {(tr.de, tr.a) for tr in ciclo.transiciones}
    assert res["holgura_min"] >= 10.0 and res["borde_min"] >= 3.0, res
