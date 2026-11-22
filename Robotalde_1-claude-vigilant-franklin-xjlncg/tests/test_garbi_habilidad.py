"""Paso 7 de Garbi (M5): posición de partida, espiral programada, grabador del dataset, entrenamiento ACT de humo y
`HabilidadACT`. Todo en la simulación con el montaje lateral; imágenes pequeñas para que vaya rápido."""
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from garbi import contrato as g
from garbi.habilidad import (ALTURA_PARTIDA, DISTANCIA_PARTIDA, INCLINACION_PARTIDA, PASOS_LIMPIEZA,
                             VELOCIDAD_MAX, HabilidadACT, HabilidadEspiral, inclinacion_partida,
                             limpiar_en_simulacion, posicion_partida)
from garbi.tipos import HZ_CONTROL, TAREA_LIMPIEZA

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "herramientas"))
RESOLUCION_PRUEBA = (64, 48)


@pytest.fixture(scope="module")
def mundo_lateral():
    from garbi.lateral import ControlLateral
    from garbi.mundo import MundoGarbi

    m = MundoGarbi(render=False, montaje="lateral")
    return m, ControlLateral(m)


def test_posicion_partida_geometria(mundo_lateral):
    m, c = mundo_lateral
    agujero = np.array([320.0, 40.0, g.ALTURA_CARA_TABLA])
    q = posicion_partida(c, agujero)
    assert q is not None and q.shape == (6,)
    assert q[4] == 0.0 and q[5] == 0.0  # forzar_montaje
    from sim.entorno import lerobot_a_rad

    boca, eje = c.boca(lerobot_a_rad(q)[:4])
    assert np.hypot(*(boca[:2] - agujero[:2])) == pytest.approx(DISTANCIA_PARTIDA, abs=1.0)
    assert boca[2] - agujero[2] == pytest.approx(ALTURA_PARTIDA, abs=1.0)
    assert c.inclinacion(eje) == pytest.approx(INCLINACION_PARTIDA, abs=1.0)
    # La boca mira hacia el agujero: su eje en planta apunta a él
    hacia = (agujero[:2] - boca[:2]) / np.linalg.norm(agujero[:2] - boca[:2])
    assert float(hacia @ (eje[:2] / np.linalg.norm(eje[:2]))) > 0.99


def test_posicion_partida_con_ruido(mundo_lateral):
    m, c = mundo_lateral
    from sim.entorno import lerobot_a_rad

    agujero = np.array([320.0, -40.0, g.ALTURA_CARA_TABLA])
    q_fija = posicion_partida(c, agujero)
    b0, _ = c.boca(lerobot_a_rad(q_fija)[:4])
    rng = np.random.default_rng(3)
    desvios, incs = [], []
    for _ in range(8):
        q = posicion_partida(c, agujero, rng)
        b, e = c.boca(lerobot_a_rad(q)[:4])
        desvios.append(np.abs(b - b0))
        incs.append(c.inclinacion(e))
    desvios = np.array(desvios)
    assert desvios.max() <= 5.0 + 1.5 and desvios.max() > 0.5  # hay ruido y no pasa de ±5 mm (+ tolerancia IK)
    assert max(abs(i - INCLINACION_PARTIDA) for i in incs) <= 3.0 + 1.0


def test_lejos_baja_la_inclinacion_hasta_45_y_mas_alla_none(mundo_lateral):
    """A 60° la partida solo llega a < ~390 mm del eje del robot: más lejos se baja hasta 45° (y se registra)."""
    _, c = mundo_lateral
    from sim.entorno import lerobot_a_rad

    assert inclinacion_partida(c, np.array([300.0, 0.0])) == 60.0
    for x, inc_max in [(380.0, 55.0), (410.0, 50.0), (430.0, 45.0)]:
        inc = inclinacion_partida(c, np.array([x, 0.0]))
        assert inc is not None and 45.0 <= inc <= inc_max
        q = posicion_partida(c, np.array([x, 0.0]))
        _, eje = c.boca(lerobot_a_rad(q)[:4])
        assert c.inclinacion(eje) == pytest.approx(inc, abs=1.0)
    h = HabilidadEspiral(c)
    h.reiniciar(np.array([430.0, 20.0]))
    assert h.registro[-1]["inclinacion"] == pytest.approx(h.inclinacion) and 45.0 <= h.inclinacion < 60.0
    assert posicion_partida(c, np.array([440.0, 0.0])) is None  # más allá de ALCANCE_AGUJERO (433 mm)


def _borde(control, q_lr, madera=g.PoseTabla(360.0, 0.0, 0.0)):
    """mm del punto más bajo del borde de la boca sobre la superficie de debajo (como la guardia del ciclo)."""
    from garbi.ciclo import RADIO_BOCA
    from sim.entorno import lerobot_a_rad

    b, e = control.boca(lerobot_a_rad(np.asarray(q_lr, float))[:4])
    sup = g.ALTURA_CARA_TABLA if madera.contiene(b[:2], margen=-RADIO_BOCA) else g.ALFOMBRILLA_GROSOR
    return float(b[2] - RADIO_BOCA * np.sqrt(max(0.0, 1.0 - e[2] ** 2)) - sup)


def test_limitar_velocidad_no_se_come_las_esquinas():
    """El plan limitado sigue el camino (no corta en línea recta en el espacio articular)."""
    from garbi.habilidad import limitar_velocidad

    esquina = np.zeros((20, 6))
    esquina[:10, 1] = np.linspace(0, 30, 10)  # sube 30° en 10 pasos (más deprisa de lo permitido)...
    esquina[10:, 1] = 30.0
    esquina[10:, 2] = np.linspace(3.3, 33, 10)  # ...y luego gira otra articulación
    out = limitar_velocidad(esquina)
    assert np.abs(np.diff(out, axis=0)).max() <= VELOCIDAD_MAX / HZ_CONTROL + 1e-6
    # cada postura está en el camino: mientras la 2.ª articulación no ha acabado de subir, la 3.ª no se mueve
    assert np.all(out[out[:, 1] < 30.0 - 1e-6, 2] == 0.0)


@pytest.mark.parametrize("x", [260.0, 300.0, 340.0, 360.0, 380.0, 400.0, 420.0, 440.0])
def test_espiral_borde_en_toda_la_zona_alcanzable(mundo_lateral, x):
    """Borde de la boca ≥ 3 mm en todo el plan (también entre posturas) para agujeros en toda la madera alcanzable
    (antes, a r ≈ 340-380 mm, recortar la velocidad en el espacio articular dejaba el borde a -19 mm)."""
    _, c = mundo_lateral
    h = HabilidadEspiral(c)
    for y in (-140.0, -100.0, -60.0, -20.0, 0.0, 30.0, 70.0, 110.0, 140.0):
        p = np.array([x, y, g.ALTURA_CARA_TABLA])
        if posicion_partida(c, p) is None:
            continue
        h.reiniciar(p)
        medio = 0.5 * (h.plan[1:] + h.plan[:-1])
        borde = min(_borde(c, q) for q in np.vstack([h.plan, medio]))
        assert borde >= 3.0, (x, y, borde, h.registro[-1])
        assert np.abs(np.diff(h.plan[:, :4], axis=0)).max() * HZ_CONTROL <= VELOCIDAD_MAX + 1e-6
        assert h.inalcanzables == 0 and h.avance > 0.95, h.registro[-1]


def test_espiral_limpia_lejos_del_robot(mundo_lateral):
    """En la mitad lejana de la madera (a 45-55°) la espiral también recoge la viruta."""
    m, c = mundo_lateral
    h = HabilidadEspiral(c)
    m.reset(semilla=3, tabla=g.PoseTabla(360.0, 0.0, 0.0))
    recogidas = []
    for loc in [(30.0, 0.0), (55.0, -60.0), (65.0, 50.0)]:
        m.reset(semilla=3, tabla=g.PoseTabla(360.0, 0.0, 0.0))
        p = m.juez.tabla.a_mesa(np.array(loc))
        m.poner_taladro(*p)
        m.taladrar()
        m.quitar_taladro()
        q0 = posicion_partida(c, p)
        assert q0 is not None
        antes, despues = limpiar_en_simulacion(m, h, np.array(loc), q0)
        recogidas.append(1 - despues / max(antes, 1))
    print("recogida lejos:", np.round(recogidas, 3))
    assert min(recogidas) >= 0.9


def _preparar(m, c, rng, taladrado):
    from garbi_grabar import preparar

    m.reset(semilla=int(rng.integers(1 << 30)))
    return preparar(m, c, rng, taladrado)


def test_espiral_limpia(mundo_lateral):
    """≥ 90 % de la viruta recogida en ≥ 8 de 10 posiciones (con ruido en la partida, 1/2 serrín con plantilla)."""
    m, c = mundo_lateral
    h = HabilidadEspiral(c)
    rng = np.random.default_rng(7)
    recogidas = []
    for i in range(10):
        p_tabla, q0, _ = _preparar(m, c, rng, taladrado=i % 2 == 0)
        antes, despues = limpiar_en_simulacion(m, h, p_tabla, q0)
        assert antes > 0
        recogidas.append(1 - despues / antes)
        # La trayectoria ejecutada respeta la guardia de velocidad del ciclo y el montaje
        assert np.abs(np.diff(h.plan[:, :4], axis=0)).max() * HZ_CONTROL <= VELOCIDAD_MAX + 1e-6
        assert np.all(h.plan[:, 4] == 0) and np.all(h.plan[:, 5] == 0)
    print("recogida por posición:", np.round(recogidas, 3))
    assert sum(r >= 0.90 for r in recogidas) >= 8


def test_espiral_dura_150_pasos_y_cumple_el_contrato(mundo_lateral):
    m, c = mundo_lateral
    h = HabilidadEspiral(c)
    h.reiniciar(np.array([300.0, 0.0]))
    assert len(h.plan) == PASOS_LIMPIEZA == 150
    q0 = posicion_partida(c, np.array([300.0, 0.0]))
    acciones = [h.accion({"state": q0}) for _ in range(PASOS_LIMPIEZA)]
    assert all(a.shape == (6,) and a[4] == 0 and a[5] == 0 for a in acciones)
    assert np.abs(acciones[0] - q0).max() <= VELOCIDAD_MAX / HZ_CONTROL + 1e-6  # sin salto al empezar


# --- grabar, entrenar y ejecutar -----------------------------------------------------------------------------------
@pytest.fixture(scope="module")
def dataset_limpiar(tmp_path_factory):
    from garbi_grabar import grabar

    raiz = tmp_path_factory.mktemp("garbi") / "garbi_limpiar"
    resumen = grabar(raiz, "local/garbi_limpiar", 2, resolucion=RESOLUCION_PRUEBA, semilla=0)
    return raiz, resumen


def test_grabar_dos_episodios_carga_en_lerobot(dataset_limpiar):
    from lerobot.datasets.lerobot_dataset import LeRobotDataset

    raiz, resumen = dataset_limpiar
    assert resumen["intentos"] == 2 and resumen["guardados"] >= 1
    ds = LeRobotDataset("local/garbi_limpiar", root=raiz)
    assert ds.num_episodes == resumen["guardados"]
    assert ds.num_frames == PASOS_LIMPIEZA * ds.num_episodes
    assert ds.fps == 30
    ancho, alto = RESOLUCION_PRUEBA
    assert ds.features["observation.images.top"]["shape"] == (alto, ancho, 3)
    assert ds.features["observation.images.wrist"]["shape"] == (alto, ancho, 3)
    assert ds.features["observation.state"]["shape"] == (6,)
    assert ds.features["action"]["shape"] == (6,)
    muestra = ds[0]
    assert muestra["task"] == TAREA_LIMPIEZA
    assert tuple(muestra["observation.images.top"].shape) == (3, alto, ancho)
    registro = json.loads((raiz / "episodios_garbi_limpiar.json").read_text())
    assert {"descartados", "agujeros_fuera_de_alcance", "episodios"} <= registro.keys()


def test_zona_limpia():
    from garbi_grabar import zona_limpia

    assert zona_limpia(36, 0) and zona_limpia(36, 1) and not zona_limpia(36, 3) and not zona_limpia(0, 0)


def test_entrenar_act_humo_y_habilidad_act(dataset_limpiar, tmp_path):
    raiz, _ = dataset_limpiar
    salida = tmp_path / "act"
    env = dict(os.environ, DATASET="local/garbi_limpiar", DATASET_RAIZ=str(raiz), SALIDA=str(salida),
               LEROBOT_TRAIN=str(Path(sys.executable).parent / "lerobot-train"))
    r = subprocess.run(["bash", str(RAIZ / "herramientas" / "garbi_entrenar.sh"), "humo"], env=env,
                       capture_output=True, text=True, timeout=600)
    assert r.returncode == 0, r.stderr[-3000:]

    h = HabilidadACT(salida)
    h.reiniciar(np.array([320.0, 0.0]))
    # Cámaras a 640×480 (las reales): HabilidadACT las lleva a la resolución con que se entrenó
    obs = {"top": np.zeros((480, 640, 3), np.uint8), "wrist": np.zeros((480, 640, 3), np.uint8),
           "state": np.zeros(6, np.float32)}
    for _ in range(3):
        a = h.accion(obs)
        assert a.shape == (6,) and np.all(np.isfinite(a))
        assert a[4] == 0.0 and a[5] == 0.0
