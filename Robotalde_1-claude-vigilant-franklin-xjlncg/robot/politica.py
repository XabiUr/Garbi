"""Políticas del robot soldador en simulación: SmolVLA, ACT y reproducción grabada, con una misma interfaz.

    politica = cargar_politica("act", checkpoint="salidas/entreno_act/checkpoints/last/pretrained_model")
    recorrido = ejecutar_politica(entorno, politica, "recta", "B")      # bucle cerrado en EntornoSoldadura

Interfaz (`Politica`)
---------------------
- `reiniciar(tipo, anclaje, instruccion)`: al empezar cada recorrido (vacía la cola de acciones del chunk).
- `accion(obs) -> np.ndarray`: 6 posiciones objetivo en unidades de LeRobot (grados x5, pinza 0-100) a partir de la
  observación del entorno (`observation.state` y, si la política las usa, las imágenes de las dos cámaras).
- `terminada`: True cuando la política sabe que ha acabado (solo la reproducción: se le acaban las acciones).
- `necesita_imagenes`: si hay que renderizar las cámaras (la reproducción no las mira).

Inferencia con LeRobot 0.7 (como `lerobot.inference.sync.SyncInferenceEngine.get_action`)
-----------------------------------------------------------------------------------------
    config  = PreTrainedConfig.from_pretrained(ruta);  config.device = "cpu"
    politica = get_policy_class(config.type).from_pretrained(ruta, config=config)
    pre, post = make_pre_post_processors(config, pretrained_path=ruta, preprocessor_overrides={...})
    obs = prepare_observation_for_inference(obs_numpy, device, task=instruccion, robot_type="so101_follower")
    accion = post(transition_to_policy_action(policy_output_to_transition(politica.select_action(pre(obs)))))

El preprocesador guardado con el checkpoint ya lleva la normalización con las estadísticas del dataset y, en SmolVLA,
el renombrado de cámaras con el que se entrenó (`--rename_map`, `contrato.RENOMBRE_SMOLVLA`: cenital → camera1,
muñeca → camera2); la tercera cámara del modelo base (`--policy.empty_cameras=1`) la rellena el propio SmolVLA con
una imagen vacía. La instrucción del vocabulario cerrado va en `task`: el VLA la lee, el ACT la ignora.

La reproducción (`replay`) es el último recurso de la spec y se declara como tal: reproduce en bucle abierto las
acciones de un episodio grabado del dataset con la misma instrucción (tipo y anclaje); si hay `notas.json` del filtro
de calidad, el de mejor nota.
"""
from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable
from pathlib import Path
from typing import Protocol, runtime_checkable

import numpy as np

from lewelder import contrato as c
from lewelder.contrato import Muestra, TipoPieza
from lewelder.metricas import Z_LEVANTADA
from lewelder.robot import punta_sobre_cordon

log = logging.getLogger("robot.politica")

RAIZ = Path(__file__).resolve().parents[1]
ROBOT_TYPE = "so101_follower"
# Pasos máximos de un recorrido con política aprendida: las demostraciones duran 1050-1250 fotogramas (35-41 s).
MAX_PASOS = 1500
# Fin anticipado: la punta ya pasó el final del cordón, está levantada y quieta este tiempo.
QUIETO_FIN_S = 1.0
ALTURA_FIN = 30.0  # mm sobre la pieza
TIPOS_LEROBOT = {"act": "act", "vla": "smolvla"}
PREFERENCIA_PRINCIPIO = 0.002  # grados por fotograma al sincronizar el replay (2° en 1000 fotogramas)


@runtime_checkable
class Politica(Protocol):
    nombre: str
    necesita_imagenes: bool
    terminada: bool

    def reiniciar(self, tipo: TipoPieza | str, anclaje: str, instruccion: str) -> None: ...
    def accion(self, obs: dict) -> np.ndarray: ...


class PoliticaNoDisponible(RuntimeError):
    """La política no se puede usar (falta el checkpoint, el dataset o el episodio de esa tarea)."""


# --- políticas aprendidas de LeRobot -----------------------------------------------------------------------------
def resolver_checkpoint(ruta: str | Path) -> Path:
    """Acepta la carpeta `pretrained_model`, la de un checkpoint (`checkpoints/000300`) o la de salida del
    entrenamiento (`salidas/entreno_act`, usa `checkpoints/last`)."""
    ruta = Path(ruta)
    for candidata in (ruta, ruta / "pretrained_model", ruta / "checkpoints" / "last" / "pretrained_model"):
        if (candidata / "config.json").is_file() and (candidata / "model.safetensors").is_file():
            return candidata
    raise PoliticaNoDisponible(f"no hay un pretrained_model de LeRobot en {ruta}")


class PoliticaLeRobot:
    """ACT o SmolVLA entrenados con `lerobot-train`, en bucle cerrado sobre las observaciones del entorno."""

    necesita_imagenes = True

    def __init__(self, checkpoint: str | Path, nombre: str | None = None, dispositivo: str = "cpu",
                 renombre: dict[str, str] | None = None):
        import torch
        from lerobot.configs.policies import PreTrainedConfig
        from lerobot.policies.factory import get_policy_class, make_pre_post_processors

        self.ruta = resolver_checkpoint(checkpoint)
        config = PreTrainedConfig.from_pretrained(self.ruta)
        config.device = dispositivo
        self.tipo_lerobot = config.type
        self.nombre = nombre or ("vla" if config.type == "smolvla" else config.type)
        self.dispositivo = torch.device(dispositivo)
        self.politica = get_policy_class(config.type).from_pretrained(self.ruta, config=config)
        self.politica.eval()
        self.config = self.politica.config
        sobrescribir = {"device_processor": {"device": dispositivo}}
        pasos = self._pasos_preprocesador()
        if config.type == "smolvla" and "rename_observations_processor" in pasos:
            sobrescribir["rename_observations_processor"] = {"rename_map": dict(renombre or c.RENOMBRE_SMOLVLA)}
        self.pre, self.post = make_pre_post_processors(config, pretrained_path=self.ruta,
                                                       preprocessor_overrides=sobrescribir)
        self.camaras = [k for k in self.config.input_features if k.startswith("observation.images.")]
        self.instruccion = ""
        self.terminada = False
        self.tiempo_inferencia = 0.0  # s acumulados en select_action (para medir)
        self.n_inferencias = 0

    def _pasos_preprocesador(self) -> set[str]:
        try:
            datos = json.loads((self.ruta / "policy_preprocessor.json").read_text())
            return {p.get("registry_name", "") for p in datos.get("steps", [])}
        except (OSError, ValueError):
            return set()

    def reiniciar(self, tipo: TipoPieza | str, anclaje: str, instruccion: str) -> None:
        self.instruccion = instruccion
        self.terminada = False
        self.politica.reset()
        self.pre.reset()
        self.post.reset()

    def accion(self, obs: dict) -> np.ndarray:
        import torch
        from lerobot.policies.utils import prepare_observation_for_inference
        from lerobot.processor.converters import policy_output_to_transition, transition_to_policy_action

        entrada = {"observation.state": np.asarray(obs["observation.state"], dtype=np.float32)}
        for k, v in obs.items():
            if k.startswith("observation.images."):
                entrada[k] = np.ascontiguousarray(v)
        t0 = time.perf_counter()
        with torch.inference_mode():
            x = prepare_observation_for_inference(entrada, self.dispositivo, self.instruccion, ROBOT_TYPE)
            x = self.pre(x)
            salida = self.politica.select_action(x)
            accion = self.post(transition_to_policy_action(policy_output_to_transition(salida)))
        self.tiempo_inferencia += time.perf_counter() - t0
        self.n_inferencias += 1
        return accion.squeeze(0).cpu().numpy().astype(np.float64)

    def chunk(self, obs: dict) -> np.ndarray:
        """El chunk entero de acciones (n x 6, unidades de LeRobot) para `obs`, sin la cola interna de
        `select_action`: para ejecutar de forma asíncrona (calcular el siguiente mientras se ejecuta el actual)."""
        import torch
        from lerobot.policies.utils import prepare_observation_for_inference
        from lerobot.processor.converters import policy_output_to_transition, transition_to_policy_action

        entrada = {"observation.state": np.asarray(obs["observation.state"], dtype=np.float32)}
        for k, v in obs.items():
            if k.startswith("observation.images."):
                entrada[k] = np.ascontiguousarray(v)
        t0 = time.perf_counter()
        with torch.inference_mode():
            x = prepare_observation_for_inference(entrada, self.dispositivo, self.instruccion, ROBOT_TYPE)
            x = self.pre(x)
            salida = self.politica.predict_action_chunk(x)  # (1, n, 6) normalizado
            acciones = [self.post(transition_to_policy_action(policy_output_to_transition(salida[:, i])))
                        for i in range(salida.shape[1])]
        self.tiempo_inferencia += time.perf_counter() - t0
        self.n_inferencias += 1
        return torch.cat([a.reshape(1, -1) for a in acciones]).cpu().numpy().astype(np.float64)


# --- reproducción grabada ----------------------------------------------------------------------------------------
class PoliticaReplay:
    """Reproduce las acciones grabadas de un episodio del dataset con la misma instrucción (último recurso)."""

    nombre = "replay"
    necesita_imagenes = False

    def __init__(self, dataset: str | Path):
        import pandas as pd

        self.raiz = Path(dataset)
        archivos = sorted((self.raiz / "data").glob("*/*.parquet"))
        if not archivos or not (self.raiz / "meta" / "tasks.parquet").is_file():
            raise PoliticaNoDisponible(f"no hay un LeRobotDataset en {self.raiz}")
        datos = pd.concat([pd.read_parquet(a, columns=["action", "episode_index", "frame_index", "task_index"])
                           for a in archivos])
        tareas = pd.read_parquet(self.raiz / "meta" / "tasks.parquet")
        nombre_tarea = {int(i): str(t) for t, i in zip(tareas.index, tareas["task_index"])}
        self.episodios: dict[int, np.ndarray] = {}
        self.tarea_episodio: dict[int, str] = {}
        for ep, grupo in datos.groupby("episode_index"):
            grupo = grupo.sort_values("frame_index")
            self.episodios[int(ep)] = np.stack(grupo["action"].to_numpy()).astype(np.float64)
            self.tarea_episodio[int(ep)] = nombre_tarea[int(grupo["task_index"].iloc[0])]
        self.notas = self._leer_notas()
        self.episodio: int | None = None
        self._acciones = np.zeros((0, 6))
        self._i = 0
        self.terminada = False

    def _leer_notas(self) -> dict[int, float]:
        try:
            datos = json.loads((self.raiz / "notas.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        return {d["episodio"]: d["nota"] for d in datos.get("demostraciones", [])
                if d.get("episodio") is not None and d.get("nota") is not None}

    def episodios_de(self, instruccion: str) -> list[int]:
        """Episodios grabados con esa instrucción, el de mejor nota primero (si hay notas)."""
        eps = [e for e, t in self.tarea_episodio.items() if t == instruccion]
        return sorted(eps, key=lambda e: (-self.notas.get(e, 0.0), e))

    def reiniciar(self, tipo: TipoPieza | str, anclaje: str, instruccion: str) -> None:
        eps = self.episodios_de(instruccion)
        if not eps:
            raise PoliticaNoDisponible(f"no hay ningún episodio grabado de «{instruccion}» en {self.raiz}")
        self.episodio = eps[0]
        self._acciones = self.episodios[self.episodio]
        self._i = 0
        self.terminada = False

    def sincronizar(self, estado) -> int:
        """Salta al fotograma grabado cuya acción se parece más a la postura `estado` (al cambiar a replay a mitad
        de un recorrido, para no volver al principio). Con una pequeña preferencia por los primeros fotogramas
        (`PREFERENCIA_PRINCIPIO` grados por fotograma): el reposo sale al principio y al final del episodio y debe
        ganar el principio. Devuelve el índice."""
        d = np.max(np.abs(self._acciones[:, :5] - np.asarray(estado, dtype=float)[:5]), axis=1)
        self._i = int(np.argmin(d + PREFERENCIA_PRINCIPIO * np.arange(len(d))))
        self.terminada = False
        return self._i

    def accion(self, obs: dict) -> np.ndarray:
        a = self._acciones[min(self._i, len(self._acciones) - 1)]
        self._i += 1
        self.terminada = self._i >= len(self._acciones)
        return a.copy()


def cargar_politica(nombre: str, checkpoint: str | Path | None = None, dataset: str | Path | None = None,
                    dispositivo: str = "cpu") -> Politica:
    """`vla` y `act` necesitan `checkpoint`; `replay`, `dataset`. Lanza `PoliticaNoDisponible` si falta algo."""
    nombre = nombre.lower()
    if nombre == "replay":
        if dataset is None:
            raise PoliticaNoDisponible("replay necesita --dataset")
        return PoliticaReplay(dataset)
    if nombre not in TIPOS_LEROBOT:
        raise ValueError(f"política desconocida: {nombre}")
    if checkpoint is None:
        raise PoliticaNoDisponible(f"{nombre} necesita un checkpoint")
    politica = PoliticaLeRobot(checkpoint, nombre, dispositivo)
    if politica.tipo_lerobot != TIPOS_LEROBOT[nombre]:
        log.warning("el checkpoint de %s es de tipo %s", nombre, politica.tipo_lerobot)
    return politica


# --- bucle cerrado en la simulación ------------------------------------------------------------------------------
def gatillo_robot(m: Muestra) -> bool:
    """El "gatillo" del robot para puntuarlo: el LED luciría (punta encima del cordón a la altura de soldar), como en
    el modo Maestro del servidor (`lewelder.robot.punta_sobre_cordon`)."""
    return punta_sobre_cordon(m)


class DetectorFin:
    """Fin anticipado de un recorrido: la punta pasó el final del cordón y está levantada y quieta."""

    def __init__(self, fps: float = c.FPS_DATASET):
        self.n_quieto = int(QUIETO_FIN_S * fps)
        self.paso_final = False
        self._quieto = 0
        self._anterior: np.ndarray | None = None

    def actualizar(self, m: Muestra) -> bool:
        p = np.array([m.x, m.y, m.z])
        if m.x >= c.LONGITUD_CORDON - c.TAMANO_TRAMO and m.z <= Z_LEVANTADA:
            self.paso_final = True
        quieto = self._anterior is not None and np.linalg.norm(p - self._anterior) < 0.05
        self._anterior = p
        self._quieto = self._quieto + 1 if (quieto and m.z > ALTURA_FIN) else 0
        return self.paso_final and self._quieto >= self.n_quieto


def ejecutar_politica(entorno, politica: Politica, tipo: TipoPieza | str, anclaje: str,
                      instruccion: str | None = None, max_pasos: int = MAX_PASOS,
                      al_paso: Callable[[Muestra, int], bool | None] | None = None, reiniciar_entorno: bool = True,
                      semilla: int | None = None) -> list[Muestra]:
    """Un recorrido en bucle cerrado: reposo → la política manda hasta que acaba (o `max_pasos`).

    Devuelve las muestras de la punta en el marco de la pieza (gatillo False: el LED lo decide quien puntúa).
    `al_paso(muestra, i)` se llama tras cada paso; si devuelve True, el recorrido se interrumpe.
    """
    tipo = TipoPieza(tipo)
    instruccion = instruccion or c.instruccion_soldar(tipo, anclaje)
    render_antes = entorno.render
    entorno.render = bool(politica.necesita_imagenes)
    try:
        obs = entorno.reset(anclaje, tipo, semilla=semilla) if reiniciar_entorno else entorno.observacion()
        politica.reiniciar(tipo, anclaje, instruccion)
        fin = DetectorFin()
        muestras: list[Muestra] = []
        for i in range(max_pasos):
            accion = politica.accion(obs)
            obs = entorno.step(accion)
            m = entorno.muestra(t=i / c.FPS_DATASET, gatillo=False)
            muestras.append(m)
            if al_paso is not None and al_paso(m, i):
                break
            if politica.terminada or fin.actualizar(m):
                break
        return muestras
    finally:
        entorno.render = render_antes


def con_gatillo(muestras: list[Muestra]) -> list[Muestra]:
    """Las muestras con el gatillo del robot (`gatillo_robot`) para puntuarlas con `evaluar_pasada`."""
    return [Muestra(m.t, m.x, m.y, m.z, gatillo_robot(m), m.angulo_trabajo, m.angulo_avance) for m in muestras]
