"""Entorno de simulación del robot soldador: SO-101 con antorcha sobre la base de anclajes.

La interfaz imita al SO-101 seguidor de LeRobot 0.7 (`so101_follower`): el estado y la acción son las 6 posiciones
articulares con los nombres `shoulder_pan.pos` … `gripper.pos`, las 5 del brazo en **grados** (calibración por
defecto `use_degrees=True`: 0 en el centro del recorrido, que coincide con el 0 del modelo `so101_new_calib`) y la
pinza en **0-100** (0 = cerrada, 100 = abierta, recorrido completo de la articulación). La acción es la posición
objetivo de cada servo, como la que manda el brazo guía.

Las observaciones salen con las claves del dataset (`observation.state`, `observation.images.cenital`,
`observation.images.muneca`), así el mismo bucle sirve para grabar y para desplegar una política.
"""
from __future__ import annotations

import mujoco
import numpy as np

from lewelder import contrato as c
from sim import escena
from sim.cinematica import ARTICULACIONES, Cinematica

NOMBRES_MOTORES = [f"{n}.pos" for n in ARTICULACIONES]  # orden de `observation.state` y de `action`
ROBOT_TYPE = "so101_follower"
RESOLUCION = (256, 192)  # (ancho, alto) de las dos cámaras de la política
SUBPASOS = 16  # pasos de física por fotograma (el paso de integración del modelo es 1 / (FPS · SUBPASOS))

# Recorrido de la pinza en el modelo (rad): de cerrada a abierta. LeRobot lo normaliza a 0-100.
PINZA_RAD = (-0.17453297762778586, 1.7453291995659765)

# Postura de reposo (grados de LeRobot): brazo recogido, antorcha arriba y lejos de la base de anclajes.
REPOSO = np.array([0.0, -95.0, 85.0, 70.0, 90.0, 0.0])


# --- unidades -----------------------------------------------------------------------------------------------------
def rad_a_lerobot(q_rad) -> np.ndarray:
    """6 articulaciones del modelo (rad) → unidades de LeRobot (grados x5, pinza 0-100)."""
    q = np.asarray(q_rad, dtype=float)
    out = np.degrees(q).astype(float)
    out[..., 5] = (q[..., 5] - PINZA_RAD[0]) / (PINZA_RAD[1] - PINZA_RAD[0]) * 100.0
    return out


def lerobot_a_rad(q_lr) -> np.ndarray:
    """Unidades de LeRobot (grados x5, pinza 0-100) → 6 articulaciones del modelo (rad)."""
    q = np.asarray(q_lr, dtype=float)
    out = np.radians(q).astype(float)
    out[..., 5] = PINZA_RAD[0] + q[..., 5] / 100.0 * (PINZA_RAD[1] - PINZA_RAD[0])
    return out


PINZA_AGARRE_LR = float(rad_a_lerobot(np.r_[np.zeros(5), escena.PINZA_AGARRE])[5])
REPOSO[5] = PINZA_AGARRE_LR


# --- ángulos de la antorcha ---------------------------------------------------------------------------------------
def direccion_antorcha(angulo_trabajo: float, angulo_avance: float) -> np.ndarray:
    """Vector unitario mango → punta, en el marco de la pieza, con esos ángulos (grados; ver el contrato)."""
    d = np.array([np.tan(np.radians(angulo_avance)), 1.0 / np.tan(np.radians(angulo_trabajo)), -1.0])
    return d / np.linalg.norm(d)


def angulos_antorcha(d_pieza) -> tuple[float, float]:
    """(ángulo de trabajo, ángulo de avance) en grados de un eje mango → punta en el marco de la pieza.

    Trabajo: en el plano YZ, ángulo entre el eje y la chapa base medido desde +Y (90° = vertical; en la T, el
    mango en -Y y la punta hacia el alma da 45°). Avance: en el plano XZ, inclinación respecto a la vertical,
    positiva si la punta va por delante del mango (empuje).
    """
    dx, dy, dz = np.asarray(d_pieza, dtype=float)
    return float(np.degrees(np.arctan2(-dz, dy))), float(np.degrees(np.arctan2(dx, -dz)))


class EntornoSoldadura:
    """SO-101 con antorcha en MuJoCo, con la misma interfaz de estado y acción que el robot real."""

    def __init__(self, resolucion: tuple[int, int] = RESOLUCION, render: bool = True, sombras: bool = True):
        self.modelo, _ = escena.construir_modelo()
        self.datos = mujoco.MjData(self.modelo)
        self.cin = Cinematica(self.modelo, sitio_pose="punta_antorcha")
        self.ancho, self.alto = resolucion
        self.render = render
        self.sombras = sombras
        self._renderer: mujoco.Renderer | None = None
        self.qadr = self.cin.qadr
        self.sitio_punta = self.modelo.site("punta_antorcha").id
        self.anclaje = "A"
        self.tipo = c.TipoPieza.RECTA
        self.t = 0.0
        self.dt = 1.0 / c.FPS_DATASET
        assert abs(self.modelo.opt.timestep * SUBPASOS - self.dt) < 1e-9

    # --- ciclo -----------------------------------------------------------------------------------------------
    def reset(self, anclaje: str = "A", tipo=c.TipoPieza.RECTA, semilla: int | None = None,
              q_inicial=None) -> dict:
        """Coloca la pieza y pone el brazo en reposo (o en `q_inicial`, unidades de LeRobot).

        Con `semilla` la postura de reposo varía unos grados (como un operador que nunca deja el brazo igual).
        """
        if anclaje not in c.ANCLAJES:
            raise ValueError(f"Anclaje desconocido: {anclaje}")
        self.anclaje, self.tipo = anclaje, c.TipoPieza(tipo)
        mujoco.mj_resetData(self.modelo, self.datos)
        escena.colocar_pieza(self.modelo, self.datos, anclaje, self.tipo)
        if q_inicial is None:
            q_inicial = REPOSO.copy()
            if semilla is not None:
                rng = np.random.default_rng(semilla)
                q_inicial[:5] += rng.normal(0.0, 4.0, 5)
        q = lerobot_a_rad(q_inicial)
        self.datos.qpos[self.qadr] = q
        self.datos.ctrl[:6] = q
        mujoco.mj_forward(self.modelo, self.datos)
        self.t = 0.0
        return self.observacion()

    def step(self, accion) -> dict:
        """Aplica la acción (posiciones objetivo, unidades de LeRobot; array de 6 o dict con `NOMBRES_MOTORES`)
        durante un fotograma (1 / FPS_DATASET s) y devuelve la observación nueva."""
        if isinstance(accion, dict):
            accion = [accion[n] for n in NOMBRES_MOTORES]
        q = lerobot_a_rad(np.asarray(accion, dtype=float))
        rangos = self.modelo.actuator_ctrlrange[:6]
        self.datos.ctrl[:6] = np.clip(q, rangos[:, 0], rangos[:, 1])
        mujoco.mj_step(self.modelo, self.datos, nstep=SUBPASOS)
        self.t += self.dt
        return self.observacion()

    # --- observación -----------------------------------------------------------------------------------------
    def estado(self) -> np.ndarray:
        """Posiciones articulares medidas (unidades de LeRobot), float32."""
        return rad_a_lerobot(self.datos.qpos[self.qadr]).astype(np.float32)

    def imagen(self, camara: str) -> np.ndarray:
        if self._renderer is None:
            self._renderer = mujoco.Renderer(self.modelo, self.alto, self.ancho)
        self._renderer.update_scene(self.datos, camara)
        self._renderer.scene.flags[mujoco.mjtRndFlag.mjRND_SHADOW] = self.sombras
        return self._renderer.render().copy()

    def observacion(self) -> dict:
        obs = {"observation.state": self.estado()}
        if self.render:
            for cam in c.CAMARAS_POLITICA:
                obs[f"observation.images.{cam}"] = self.imagen(cam)
        return obs

    # --- punta de la antorcha --------------------------------------------------------------------------------
    def punta_en_mesa(self) -> np.ndarray:
        """Posición de la punta (mm) en el marco de la mesa."""
        return self.datos.site_xpos[self.sitio_punta] / escena.MM

    def punta_en_pieza(self) -> tuple[float, float, float]:
        """Posición de la punta (mm) en el marco de la pieza colocada."""
        p = escena.mesa_a_pieza(self.anclaje, self.punta_en_mesa())
        return float(p[0]), float(p[1]), float(p[2])

    def eje_antorcha_en_pieza(self) -> np.ndarray:
        """Eje mango → punta en el marco de la pieza."""
        eje = self.datos.site_xmat[self.sitio_punta].reshape(3, 3)[:, 2]
        return escena.rotacion_pieza(self.anclaje).T @ eje

    def angulos(self) -> tuple[float, float]:
        """(ángulo de trabajo, ángulo de avance) de la antorcha, en grados."""
        return angulos_antorcha(self.eje_antorcha_en_pieza())

    def muestra(self, t: float | None = None, gatillo: bool = False) -> c.Muestra:
        """Muestra del contrato (marco de la pieza) para puntuar al robot con las métricas del alumno."""
        x, y, z = self.punta_en_pieza()
        trabajo, avance = self.angulos()
        return c.Muestra(t=self.t if t is None else t, x=x, y=y, z=z, gatillo=bool(gatillo),
                         angulo_trabajo=trabajo, angulo_avance=avance)

    def cerrar(self) -> None:
        if self._renderer is not None:
            self._renderer.close()
            self._renderer = None
