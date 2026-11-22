"""Pruebas de la mesa de montaje v2: piezas del CAD, imanes, soporte, guiones de las cuatro órdenes y dataset."""
import os

os.environ.setdefault("MUJOCO_GL", "egl")

import mujoco  # noqa: E402
import numpy as np  # noqa: E402
import pytest  # noqa: E402

from lewelder import contrato as c  # noqa: E402
from sim import demos_montaje as dm  # noqa: E402
from sim import montaje as mt  # noqa: E402
from sim import piezas_cad as pc  # noqa: E402
from sim.entorno import NOMBRES_MOTORES  # noqa: E402

ORDEN_T = c.orden_montar(c.TipoJunta.T)
ORDEN_ESQUINA = c.orden_montar(c.TipoJunta.ESQUINA)


@pytest.fixture(scope="module")
def entorno():
    ent = mt.EntornoMontaje(render=False)
    yield ent
    ent.cerrar()


# --- piezas del CAD -----------------------------------------------------------------------------------------------
def test_medidas_cad_coinciden_con_el_contrato():
    b = pc.medidas("BASE-V2")
    assert b["ranura_y"] == pytest.approx((3 - c.GUIA_T["ancho"] / 2, 3 + c.GUIA_T["ancho"] / 2), abs=0.3)
    assert b["ranura_suelo_z"] == pytest.approx(c.Z_CANTO_MOVIL[c.TipoJunta.T], abs=0.3)
    assert b["tope_y"] == pytest.approx((c.ANCHO_BASE / 2 - c.TOPE_ESQUINA["ancho"], c.ANCHO_BASE / 2), abs=0.3)
    assert b["tope_z"] == pytest.approx(c.TOPE_ESQUINA["alto"], abs=0.3)
    m = pc.medidas("MOVIL-V2")
    assert np.mean(m["aleta_x"]) == pytest.approx(c.ALETA["x"], abs=0.5)
    assert m["aleta_y"][1] - m["aleta_y"][0] == pytest.approx(c.ALETA["alto"], abs=0.5)
    geo = mt.geometria()
    assert geo["mango_grosor"] == pytest.approx(12.0, abs=0.3)
    assert geo["pie_soporte"] + geo["punta_a_mango"] == pytest.approx(c.SOPORTE_ANTORCHA["z_mango"], abs=1.0)


@pytest.mark.parametrize("pieza", pc.PIEZAS)
def test_colision_ajustada_a_la_malla(pieza):
    assert pc.ajuste_colision(pieza).iou > 0.85


# --- escena y entorno ---------------------------------------------------------------------------------------------
def test_escena_y_observacion():
    ent = mt.EntornoMontaje(render=True, resolucion=(64, 48))
    obs = ent.reset(ORDEN_T, semilla=3)
    assert set(obs) == {"observation.state", "observation.images.cenital", "observation.images.muneca"}
    assert obs["observation.state"].shape == (len(NOMBRES_MOTORES),)
    assert obs["observation.images.cenital"].shape == (48, 64, 3)
    ent.cerrar()


def test_reset_por_orden(entorno):
    entorno.reset(ORDEN_T, semilla=1)
    assert entorno.junta_cerrada is None and not entorno.exito()
    x, y, giro = entorno.pose_inicial_chapa
    z = c.ZONA_LIBRE
    assert z["x"][0] <= x <= z["x"][1] and z["y"][0] <= y <= z["y"][1] and z["giro"][0] <= giro <= z["giro"][1]
    assert entorno.antorcha_en_soporte()
    entorno.reset(mt.ORDEN_SENALAR, junta="esquina")
    assert entorno.junta_cerrada is c.TipoJunta.ESQUINA
    assert entorno.error_montaje("esquina")[0] < mt.ERROR_CERRADA_MM
    poses = entorno.poses_chapas()
    assert set(poses) == {"base", "movil"}
    with pytest.raises(NotImplementedError):
        entorno.reset("desmonta la junta")


def test_cordon_en_el_marco_del_contrato():
    for j in c.TipoJunta:
        R, o = mt.marco_cordon(j)
        assert np.allclose(mt.mesa_a_base(o), (-c.LONGITUD_CORDON / 2, c.Y_CORDON[j], 0.0))
        p = np.array([30.0, -4.0, 2.0])
        assert np.allclose(mt.mesa_a_cordon(j, mt.cordon_a_mesa(j, p)), p)


@pytest.mark.parametrize("junta", list(c.TipoJunta))
def test_imanes_cierran_desde_cerca(entorno, junta):
    entorno.reset(c.orden_montar(junta))
    R0, p0 = mt.pose_montada(junta)
    entorno._poner_libre(entorno.adr_movil, entorno.dadr_movil, R0 @ mt.rot_x(6.0), p0 + np.array([2.0, 1.5, 4.0]))
    mujoco.mj_forward(entorno.modelo, entorno.datos)
    q = entorno.estado()
    for _ in range(40):
        entorno.step(q)
    assert entorno.junta_cerrada is junta
    assert entorno.exito()


def test_imanes_no_cierran_lejos(entorno):
    entorno.reset(ORDEN_T, semilla=0)
    q = entorno.estado()
    for _ in range(10):
        entorno.step(q)
    assert entorno.junta_cerrada is None


def test_detector_de_choques_del_brazo(entorno):
    from sim.validar_montaje import prueba_choques

    assert prueba_choques(entorno)


# --- guiones ------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("orden,semilla", [(ORDEN_T, 0), (ORDEN_ESQUINA, 1), (mt.ORDEN_SENALAR, 0),
                                           (mt.ORDEN_SOLDAR, 1)])
def test_guion_cumple_la_orden_sin_chocar(entorno, orden, semilla):
    res = dm.ejecutar_orden(entorno, orden, dm.GuionV2(ruido=0.0), semilla=semilla)
    assert res.exito, res.info
    assert not entorno.choques
    if orden == mt.ORDEN_SOLDAR:
        assert res.nota is not None and res.nota > 9.0
        assert entorno.antorcha_en_soporte()


def test_guion_con_ruido_monta(entorno):
    res = dm.ejecutar_orden(entorno, ORDEN_T, dm.GuionV2(ruido=1.0), semilla=5)
    assert res.exito, res.info


# --- dataset ------------------------------------------------------------------------------------------------------
def test_dataset_multitarea(tmp_path):
    from lerobot.datasets.lerobot_dataset import LeRobotDataset

    raiz = tmp_path / "v2"
    res = dm.grabar_v2(raiz, "local/v2_prueba", [ORDEN_T, mt.ORDEN_SENALAR], 1, dm.GuionV2(ruido=0.0),
                       resolucion=(64, 48), sombras=False)
    assert sum(r.exito for r in res) == 2
    ds = LeRobotDataset("local/v2_prueba", root=raiz)
    assert ds.num_episodes == 2
    tareas = {ds[0]["task"], ds[len(ds) - 1]["task"]}
    assert tareas == {ORDEN_T, mt.ORDEN_SENALAR}
    assert (raiz / "exitos.json").exists() and (raiz / "notas.json").exists()
