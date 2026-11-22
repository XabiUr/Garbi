"""Configuración común de las pruebas.

- Marca `lento`: pruebas de más de ~30 s (entrenar e inferir con LeRobot). Se excluyen con `pytest -m "not lento"`.
- `dataset_sim`: un LeRobotDataset pequeño grabado con el filtro de calidad ("aprende del mejor"): 2 demostraciones
  buenas de la recta (anclajes B y D) y 2 malas a propósito (temblorosa y con paradas) que el filtro descarta.
  Imágenes de 64x48 para que se grabe en pocos segundos; lo usan el replay, la evaluación y el servidor.
"""
import ctypes
import os
import sys


def _backend_render() -> str:
    """El de MUJOCO_GL si está definido; si no, egl si se puede cargar libEGL y, si no, osmesa."""
    if os.environ.get("MUJOCO_GL"):
        return os.environ["MUJOCO_GL"]
    if sys.platform in ("win32", "darwin"):  # Windows y macOS: ventana normal (sin EGL ni OSMesa)
        return "glfw"
    try:
        ctypes.CDLL("libEGL.so.1")
        return "egl"
    except OSError:
        return "osmesa"


os.environ["MUJOCO_GL"] = _backend_render()
if os.environ["MUJOCO_GL"] in ("egl", "osmesa"):
    os.environ.setdefault("PYOPENGL_PLATFORM", os.environ["MUJOCO_GL"])

import pytest  # noqa: E402

UMBRAL_PRUEBA = 9.0
ANCLAJES_PRUEBA = ["B", "D"]


def pytest_configure(config):
    config.addinivalue_line("markers", "lento: prueba de más de ~30 s (excluir con -m 'not lento')")


@pytest.fixture(scope="session")
def dataset_sim(tmp_path_factory):
    from sim.demostraciones import Guion, grabar

    raiz = tmp_path_factory.mktemp("datos") / "lewelder_prueba"
    # Velocidad de soldadura real (si no, el filtro las descartaría por rápidas) pero sin esperas largas ni sombras.
    guion = Guion(t_espera=0.3, t_vuelta=1.0, t_final=0.1)
    resultados = grabar(raiz, "local/lewelder_prueba", 2, ANCLAJES_PRUEBA, ["recta"], guion, resolucion=(64, 48),
                        umbral_nota=UMBRAL_PRUEBA, malas=2, sombras=False)
    return raiz, resultados
