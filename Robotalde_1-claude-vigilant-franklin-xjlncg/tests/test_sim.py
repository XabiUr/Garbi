"""Pruebas de la simulación del robot soldador (escena, cinemática, entorno, demostraciones y dataset)."""
import os

os.environ.setdefault("MUJOCO_GL", "egl")

import mujoco  # noqa: E402
import numpy as np  # noqa: E402
import pytest  # noqa: E402

from lewelder import contrato as c  # noqa: E402
from sim import escena  # noqa: E402
from sim.cinematica import Cinematica  # noqa: E402
from sim.demostraciones import Guion, caracteristicas, ejecutar, grabar  # noqa: E402
from sim.entorno import (NOMBRES_MOTORES, REPOSO, EntornoSoldadura, angulos_antorcha,  # noqa: E402
                         direccion_antorcha, lerobot_a_rad, rad_a_lerobot)


@pytest.fixture(scope="module")
def entorno():
    ent = EntornoSoldadura(render=False)
    yield ent
    ent.cerrar()


# --- unidades y ángulos -------------------------------------------------------------------------------------------
def test_unidades_ida_y_vuelta():
    q = np.array([0.3, -1.2, 1.0, 0.5, -2.0, 0.4])
    assert np.allclose(lerobot_a_rad(rad_a_lerobot(q)), q)
    lr = rad_a_lerobot(q)
    assert np.isclose(lr[0], np.degrees(0.3))
    assert 0 <= lr[5] <= 100
    # pinza: extremos del recorrido = 0 (cerrada) y 100 (abierta)
    assert np.isclose(rad_a_lerobot(np.r_[np.zeros(5), -0.17453297762778586])[5], 0.0)
    assert np.isclose(rad_a_lerobot(np.r_[np.zeros(5), 1.7453291995659765])[5], 100.0)


def test_nombres_como_so101_follower():
    assert NOMBRES_MOTORES == ["shoulder_pan.pos", "shoulder_lift.pos", "elbow_flex.pos", "wrist_flex.pos",
                               "wrist_roll.pos", "gripper.pos"]


@pytest.mark.parametrize("trabajo,avance", [(90, 10), (45, 10), (60, 0), (100, 20)])
def test_angulos_ida_y_vuelta(trabajo, avance):
    tr, av = angulos_antorcha(direccion_antorcha(trabajo, avance))
    assert tr == pytest.approx(trabajo, abs=1e-6)
    assert av == pytest.approx(avance, abs=1e-6)


# --- escena -------------------------------------------------------------------------------------------------------
def test_escena_tiene_lo_necesario(entorno):
    m = entorno.modelo
    for cam in c.CAMARAS_POLITICA:
        assert m.camera(cam).id >= 0
    assert m.site("punta_antorcha").id >= 0
    assert m.body("pieza_recta").mocapid >= 0 and m.body("pieza_t").mocapid >= 0
    # la punta está a LONGITUD_ANTORCHA_ROBOT del punto de agarre
    d = entorno.datos
    mujoco.mj_forward(m, d)
    dist = np.linalg.norm(d.site_xpos[m.site("punta_antorcha").id] - d.site_xpos[m.site("gripperframe").id])
    assert dist == pytest.approx(c.LONGITUD_ANTORCHA_ROBOT * escena.MM, abs=1e-6)


def test_colocar_pieza_y_marcos(entorno):
    for anclaje in c.ANCLAJES:
        for tipo in c.TipoPieza:
            entorno.reset(anclaje, tipo)
            cuerpo = "pieza_recta" if tipo is c.TipoPieza.RECTA else "pieza_t"
            otra = "pieza_t" if tipo is c.TipoPieza.RECTA else "pieza_recta"
            pos = entorno.datos.xpos[entorno.modelo.body(cuerpo).id] / escena.MM
            assert np.allclose(pos, escena.pieza_a_mesa(anclaje, [0, 0, 0]), atol=1e-6)
            assert entorno.datos.xpos[entorno.modelo.body(otra).id][2] < -0.5
    p = np.array([12.0, -3.0, 4.0])
    assert np.allclose(escena.mesa_a_pieza("B", escena.pieza_a_mesa("B", p)), p)


def _se_solapan(a: np.ndarray, b: np.ndarray) -> bool:
    """Prueba de ejes separadores para dos rectángulos (esquinas 4x2)."""
    for poli in (a, b):
        for i in range(4):
            arista = poli[(i + 1) % 4] - poli[i]
            eje = np.array([-arista[1], arista[0]])
            pa, pb = a @ eje, b @ eje
            if pa.max() <= pb.min() or pb.max() <= pa.min():
                return False
    return True


def _inflar(poli: np.ndarray, margen: float) -> np.ndarray:
    """Agranda un rectángulo `margen` mm por cada lado."""
    centro = poli.mean(0)
    u = (poli[1] - poli[0]) / np.linalg.norm(poli[1] - poli[0])
    v = (poli[2] - poli[1]) / np.linalg.norm(poli[2] - poli[1])
    return np.array([p + margen * (np.sign((p - centro) @ u) * u + np.sign((p - centro) @ v) * v) for p in poli])


def test_anclajes_sin_solapes_y_con_giros_distintos():
    huellas = {n: escena.huella_pieza(n) for n in c.ANCLAJES}
    nombres = list(huellas)
    for i, a in enumerate(nombres):
        for b in nombres[i + 1:]:
            # al menos 10 mm entre huellas: agrandadas 4,9 mm cada una no se tocan
            assert not _se_solapan(_inflar(huellas[a], 4.9), _inflar(huellas[b], 4.9)), \
                f"las huellas de {a} y {b} se solapan o están a menos de 10 mm"
    assert len({a.giro for a in c.ANCLAJES.values()}) >= 2
    # ninguna huella invade la base del robot (≈ 90 x 112 mm alrededor del origen, con margen)
    robot = np.array([[-60, -70], [60, -70], [60, 70], [-60, 70]], dtype=float)
    for n, h in huellas.items():
        assert not _se_solapan(h, robot), f"la huella de {n} invade la base del robot"


@pytest.mark.parametrize("anclaje", list(c.ANCLAJES))
def test_render_cenital_ve_los_aruco(anclaje):
    from sim.validar import detectar_aruco

    ent = EntornoSoldadura(resolucion=(640, 480))
    ent.reset(anclaje, "recta")
    ids = detectar_aruco(ent.imagen("cenital"))
    ent.cerrar()
    assert escena.id_aruco_pieza("recta") in ids
    assert escena.id_aruco_anclaje(anclaje) in ids


# --- cinemática ---------------------------------------------------------------------------------------------------
def test_ik_cenital_antigua_sigue_funcionando():
    m = mujoco.MjModel.from_xml_path(str(escena.RAIZ / "assets" / "so101" / "scene.xml"))
    cin = Cinematica(m)
    for objetivo in ([0.20, 0.0, 0.03], [0.25, 0.10, 0.03], [0.15, -0.12, 0.05]):
        q, err = cin.inversa(objetivo, np.zeros(6))
        assert err < 1e-3


@pytest.mark.parametrize("anclaje", list(c.ANCLAJES))
@pytest.mark.parametrize("tipo", ["recta", "t"])
def test_ik_punta_antorcha_con_orientacion(entorno, anclaje, tipo):
    from sim.demostraciones import Planificador

    entorno.reset(anclaje, tipo)
    pl = Planificador(entorno)
    d = direccion_antorcha(c.ANGULO_TRABAJO_OBJETIVO[tipo], 10.0)
    q = pl.ik_inicio(np.array([0.0, 0.0, c.ALTURA_PUNTA]), d, lerobot_a_rad(REPOSO))
    for x in np.linspace(0, c.LONGITUD_CORDON, 7):
        p = np.array([x, 0.0, c.ALTURA_PUNTA])
        q, err, ang = pl._ik(p, d, q)
        assert err < 1e-3 and np.degrees(ang) < 0.5
        pos, R = entorno.cin.pose(q)
        p_pieza = escena.mesa_a_pieza(anclaje, pos / escena.MM)
        assert np.allclose(p_pieza, p, atol=1.0)
        tr, av = angulos_antorcha(escena.rotacion_pieza(anclaje).T @ R[:, 2])
        assert tr == pytest.approx(c.ANGULO_TRABAJO_OBJETIVO[tipo], abs=0.5)
        assert av == pytest.approx(10.0, abs=0.5)


# --- seguimiento con física ---------------------------------------------------------------------------------------
@pytest.mark.parametrize("anclaje", list(c.ANCLAJES))
@pytest.mark.parametrize("tipo", ["recta", "t"])
def test_seguimiento_del_cordon_sin_ruido(entorno, anclaje, tipo):
    r = ejecutar(entorno, anclaje, tipo, Guion(ruido=0.0))
    assert r.error_max < 2.0
    assert abs(r.trabajo_medio - c.ANGULO_TRABAJO_OBJETIVO[tipo]) < c.MARGEN_ANGULO_TRABAJO
    assert c.ANGULO_AVANCE_RANGO[0] <= r.avance_medio <= c.ANGULO_AVANCE_RANGO[1]
    con_gatillo = [m for m in r.muestras if m.gatillo]
    assert con_gatillo[0].x < 5.0 and con_gatillo[-1].x > c.LONGITUD_CORDON - 2.0


def test_demostracion_con_ruido_dentro_de_tolerancia(entorno):
    r = ejecutar(entorno, "A", "recta", Guion(), semilla=3)
    assert r.lateral_max < c.TOLERANCIAS[c.NIVEL_JURADO]
    sin = ejecutar(entorno, "A", "recta", Guion(ruido=0.0))
    assert r.fotogramas != sin.fotogramas  # la variabilidad cambia la duración


def test_muestra_en_marco_de_pieza(entorno):
    entorno.reset("C", "t")
    m = entorno.muestra(t=1.5, gatillo=True)
    assert isinstance(m, c.Muestra) and m.t == 1.5 and m.gatillo
    assert (m.x, m.y, m.z) == pytest.approx(entorno.punta_en_pieza())


# --- dataset ------------------------------------------------------------------------------------------------------
def test_dataset_pequeno_se_carga(tmp_path):
    from lerobot.datasets.lerobot_dataset import LeRobotDataset

    guion = Guion(velocidad=60.0, t_aproximacion=1.0, t_bajada=0.5, t_espera=0.1, t_subida=0.4, t_vuelta=0.8,
                  t_final=0.1)
    raiz = tmp_path / "ds"
    grabar(raiz, "local/prueba", 2, ["A"], ["recta", "t"], guion, resolucion=(64, 48))
    ds = LeRobotDataset("local/prueba", root=raiz)
    assert ds.num_episodes == 2
    assert ds.meta.robot_type == "so101_follower"
    assert ds.fps == c.FPS_DATASET
    assert set(caracteristicas((64, 48))) <= set(ds.features)
    assert ds.features["observation.state"]["names"] == NOMBRES_MOTORES
    item = ds[0]
    assert item["observation.images.cenital"].shape == (3, 48, 64)
    assert item["task"] == c.instruccion_soldar("recta", "A")
    assert ds[len(ds) - 1]["task"] == c.instruccion_soldar("t", "A")


def test_grabar_reintenta_con_otra_semilla_si_no_hay_solucion(tmp_path, monkeypatch):
    """Si una postura inicial no tiene solución de IK, `grabar` prueba otra semilla en vez de abortar todo."""
    import sim.demostraciones as d

    original, llamadas = d.ejecutar, []

    def ejecutar_que_falla_una_vez(entorno, anclaje, tipo, guion, semilla=0, al_fotograma=None):
        llamadas.append(semilla)
        if len(llamadas) == 1:
            raise RuntimeError("Sin solución de IK (simulado)")
        return original(entorno, anclaje, tipo, guion, semilla=semilla, al_fotograma=al_fotograma)

    monkeypatch.setattr(d, "ejecutar", ejecutar_que_falla_una_vez)
    guion = Guion(velocidad=60.0, t_aproximacion=1.0, t_bajada=0.5, t_espera=0.1, t_subida=0.4, t_vuelta=0.8,
                  t_final=0.1)
    resultados = d.grabar(tmp_path / "ds", "local/prueba", 1, ["B"], ["recta"], guion, resolucion=(64, 48))
    assert len(llamadas) == 2 and llamadas[1] != llamadas[0]
    assert len(resultados) == 1 and resultados[0].semilla == llamadas[1]
