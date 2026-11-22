"""Las dos políticas de ACERCAMIENTO del producto (protocolo `contrato.Politica`), intercambiables por configuración.

    politica = crear_politica(cfg, matriz)    # cfg.politica: "act" | "circulo"
    politica.reiniciar(vista, q_medida)
    q = politica.accion({"top": img, "wrist": img, "state": q_medida}, vista)   # 6 grados
    politica.llegado()                          # ha llegado a la broca: el orquestador congela la postura

- `PoliticaACT`: ACT de LeRobot 0.7 (carpeta local del checkpoint o repo del Hub). Lee las `input_features` del
  modelo y monta la observación sola: cámaras (`observation.images.<nombre>`, con alias top/wrist) redimensionadas a
  la resolución del entrenamiento y `observation.state` = la postura medida (convención de `lerobot-record`; o la
  orden anterior con `estado="orden"`). Ensemble temporal opcional. Llega cuando la acción converge.
- `PoliticaCirculo`: el respaldo sin aprendizaje. Destino = matriz(centro del círculo morado); trayectoria de mínimo
  tirón desde la postura actual (por una postura intermedia segura si se configura). Si el círculo se mueve un poco
  durante el acercamiento, re-apunta.
"""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path

import numpy as np

from garbi.producto.barridos import trayectoria_suave
from garbi.producto.contrato import Vista

log = logging.getLogger("garbi.producto")

ROBOT_TYPE = "so101_follower"
PREFIJO_IMAGEN = "observation.images."
# nombre de la cámara en el modelo → nombres aceptados en la observación de Garbi
ALIAS_CAMARAS = {
    "top": ("top", "arriba", "cenital", "overhead", "front", "frontal", "camera1", "cam_high", "superior", "laptop"),
    "wrist": ("wrist", "muneca", "muñeca", "hand", "mano", "camera2", "cam_wrist", "gripper", "phone"),
}


# --- ACT ------------------------------------------------------------------------------------------------------------
def resolver_modelo(ruta_o_repo: str | Path) -> Path:
    """Carpeta con `config.json` + `model.safetensors`: acepta `pretrained_model`, un checkpoint
    (`checkpoints/000300`), la salida del entrenamiento (usa `checkpoints/last`) o un repo del Hub."""
    ruta = Path(ruta_o_repo)
    if not ruta.exists():
        if str(ruta_o_repo).count("/") == 1 and not str(ruta_o_repo).startswith((".", "/")):
            from huggingface_hub import snapshot_download

            ruta = Path(snapshot_download(str(ruta_o_repo)))
        else:
            raise FileNotFoundError(f"no existe el modelo {ruta_o_repo}")
    for c in (ruta, ruta / "pretrained_model", ruta / "checkpoints" / "last" / "pretrained_model"):
        if (c / "config.json").is_file() and (c / "model.safetensors").is_file():
            return c
    raise FileNotFoundError(f"no hay un pretrained_model de LeRobot en {ruta}")


def mapear_camaras(features_modelo: list[str], disponibles: list[str], forzado: dict[str, str] | None = None
                   ) -> dict[str, str]:
    """{clave del modelo (`observation.images.top`) → nombre en la observación de Garbi (`top`)}.

    `forzado`: {nombre del modelo (con o sin prefijo) → nombre de Garbi}. Si no, coincidencia exacta, luego alias, y
    si queda una sola cámara del modelo y una de Garbi sin emparejar, se emparejan."""
    forzado = {(k if k.startswith(PREFIJO_IMAGEN) else PREFIJO_IMAGEN + k): v for k, v in (forzado or {}).items()}
    mapa: dict[str, str] = {}
    libres = list(disponibles)
    for clave in features_modelo:
        if clave in forzado:
            mapa[clave] = forzado[clave]
            if forzado[clave] in libres:
                libres.remove(forzado[clave])
    for clave in features_modelo:
        if clave in mapa:
            continue
        nombre = clave[len(PREFIJO_IMAGEN):]
        n = nombre.lower()
        candidato = None
        if nombre in libres:
            candidato = nombre
        else:
            for garbi, alias in ALIAS_CAMARAS.items():
                if (n in alias or any(a in n for a in alias)) and garbi in libres:
                    candidato = garbi
                    break
        if candidato is not None:
            mapa[clave] = candidato
            libres.remove(candidato)
    sin = [c for c in features_modelo if c not in mapa]
    if len(sin) == 1 and len(libres) == 1:
        mapa[sin[0]] = libres.pop()
        sin = []
    if sin:
        raise ValueError(f"no sé qué cámara darle al modelo para {sin} (tengo {disponibles}); "
                         "ponlo en act.camaras del yaml, p. ej. {front: top}")
    return mapa


class PoliticaACT:
    """ACT de LeRobot 0.7 como política de acercamiento.

    `politica`, `pre`, `post` y `config` se pueden inyectar (tests); si no, se cargan de `ruta_o_repo`."""

    nombre = "act"

    def __init__(self, ruta_o_repo: str | Path | None = None, dispositivo: str = "cpu",
                 camaras: dict[str, str] | None = None, estado: str = "medido", ensemble: float | None = None,
                 umbral_llegada: float = 0.5, pasos_llegada: int = 15, tiempo_max: float = 12.0, hz: float = 30.0,
                 tarea: str = "Approach the drill bit.", camaras_disponibles=("top", "wrist"),
                 politica=None, pre=None, post=None, config=None):
        self.dispositivo = dispositivo
        self.estado = estado
        self.umbral_llegada = float(umbral_llegada)
        self.pasos_llegada = int(pasos_llegada)
        self.pasos_max = int(round(tiempo_max * hz))
        self.tarea = tarea
        self.ruta = None
        if politica is None:
            politica, pre, post, config = self._cargar(ruta_o_repo, dispositivo, ensemble)
        self.politica, self.pre, self.post = politica, pre, post
        self.config = config if config is not None else getattr(politica, "config", None)
        feats = dict(getattr(self.config, "input_features", None) or {})
        self.formas: dict[str, tuple[int, int]] = {}
        for k, f in feats.items():
            if k.startswith(PREFIJO_IMAGEN):
                forma = tuple(getattr(f, "shape", ()))
                self.formas[k] = forma[1:] if len(forma) == 3 else None  # (C, H, W) → (H, W)
        self.camaras = mapear_camaras(list(self.formas), list(camaras_disponibles), camaras)
        self.dim_estado = None
        if "observation.state" in feats:
            self.dim_estado = int(np.prod(getattr(feats["observation.state"], "shape", (6,))))
        salidas = dict(getattr(self.config, "output_features", None) or {})
        self.dim_accion = int(np.prod(getattr(salidas.get("action"), "shape", (6,)))) if salidas else 6
        log.info("ACT: cámaras %s · estado %s (%s) · ensemble %s", self.camaras, self.dim_estado, estado, ensemble)
        self._previa: np.ndarray | None = None
        self._orden: np.ndarray | None = None
        self._quietos = 0
        self._pasos = 0
        self.tiempo_inferencia = 0.0

    @staticmethod
    def _cargar(ruta_o_repo, dispositivo: str, ensemble: float | None):
        from lerobot.configs.policies import PreTrainedConfig
        from lerobot.policies.factory import get_policy_class, make_pre_post_processors

        if ruta_o_repo is None:
            raise ValueError("PoliticaACT necesita la ruta o el repo del modelo")
        ruta = resolver_modelo(ruta_o_repo)
        config = PreTrainedConfig.from_pretrained(ruta)
        config.device = dispositivo
        if ensemble is not None:
            if not hasattr(config, "temporal_ensemble_coeff"):
                raise ValueError(f"el modelo {config.type} no tiene ensemble temporal")
            config.temporal_ensemble_coeff = float(ensemble)
            config.n_action_steps = 1  # obligatorio con el ensemble temporal
        politica = get_policy_class(config.type).from_pretrained(ruta, config=config)
        politica.eval()
        pre, post = make_pre_post_processors(politica.config, pretrained_path=ruta,
                                             preprocessor_overrides={"device_processor": {"device": dispositivo}})
        log.info("ACT cargado de %s (%s)", ruta, config.type)
        return politica, pre, post, politica.config

    # --- protocolo Politica ---
    def reiniciar(self, vista: Vista, q: np.ndarray) -> None:
        for obj in (self.politica, self.pre, self.post):
            if obj is not None and hasattr(obj, "reset"):
                obj.reset()
        self._previa = None
        self._orden = np.asarray(q, float).copy()
        self._quietos = 0
        self._pasos = 0

    def observacion(self, obs: dict) -> dict:
        """{"top", "wrist", "state"} → claves del modelo, con las imágenes a la resolución del entrenamiento."""
        import cv2

        salida = {}
        for clave, nombre in self.camaras.items():
            if nombre not in obs or obs[nombre] is None:
                raise KeyError(f"falta la cámara {nombre!r} para {clave}")
            img = np.ascontiguousarray(obs[nombre])
            forma = self.formas.get(clave)
            if forma is not None and img.shape[:2] != tuple(forma):
                img = cv2.resize(img, (forma[1], forma[0]), interpolation=cv2.INTER_AREA)
            salida[clave] = img
        if self.dim_estado is not None:
            estado = obs.get("state") if self.estado == "medido" or self._orden is None else self._orden
            estado = np.asarray(estado, np.float32).reshape(-1)
            if estado.size != self.dim_estado:
                raise ValueError(f"el modelo espera un estado de {self.dim_estado}, llega {estado.size}")
            salida["observation.state"] = estado
        return salida

    def _inferir(self, entrada: dict) -> np.ndarray:
        import torch
        from lerobot.policies.utils import prepare_observation_for_inference
        from lerobot.processor.converters import policy_output_to_transition, transition_to_policy_action

        with torch.inference_mode():
            x = prepare_observation_for_inference(entrada, torch.device(self.dispositivo), self.tarea, ROBOT_TYPE)
            x = self.pre(x)
            salida = self.politica.select_action(x)
            accion = self.post(transition_to_policy_action(policy_output_to_transition(salida)))
        return accion.squeeze(0).cpu().numpy().astype(np.float64)

    def accion(self, obs: dict, vista: Vista | None = None) -> np.ndarray:
        t0 = time.perf_counter()
        a = np.asarray(self._inferir(self.observacion(obs)), float).reshape(-1)
        self.tiempo_inferencia += time.perf_counter() - t0
        if a.size != 6:
            raise ValueError(f"el modelo da {a.size} acciones; se esperaban 6")
        self._pasos += 1
        if self._previa is not None and np.max(np.abs(a - self._previa)) < self.umbral_llegada:
            self._quietos += 1
        else:
            self._quietos = 0
        self._previa = a.copy()
        self._orden = a.copy()
        return a

    def llegado(self) -> bool:
        return self._quietos >= self.pasos_llegada or self._pasos >= self.pasos_max


# --- círculo + matriz -----------------------------------------------------------------------------------------------
class PoliticaCirculo:
    """Respaldo: postura destino = matriz(centro del círculo) y trayectoria suave hasta ella."""

    nombre = "circulo"

    def __init__(self, matriz, postura_intermedia=None, velocidad: float = 60.0, tolerancia: float = 1.0,
                 actualizar_px: float = 4.0, rango_px: float = 60.0, hz: float = 30.0):
        self.matriz = matriz
        self.intermedia = None if postura_intermedia is None else np.asarray(postura_intermedia, float).reshape(6)
        self.velocidad = velocidad
        self.tolerancia = tolerancia
        self.actualizar_px = actualizar_px
        self.rango_px = rango_px
        self.hz = hz
        self.destino: np.ndarray | None = None
        self.uv: np.ndarray | None = None
        self._plan: list[np.ndarray] = []
        self._ultima: np.ndarray | None = None
        self._final_desde: np.ndarray | None = None  # inicio del tramo final (para re-apuntar)
        self._k_final = 0
        self._n_final = 1
        self._i = 0

    def _tramo_final(self, desde: np.ndarray) -> None:
        tramo = trayectoria_suave(desde, self.destino, self.velocidad, self.hz)
        self._final_desde = desde.copy()
        self._n_final = len(tramo)
        self._k_final = 0

    def reiniciar(self, vista: Vista, q: np.ndarray) -> None:
        if vista is None or vista.circulo is None:
            raise ValueError("la política del círculo necesita ver el círculo morado")
        q = np.asarray(q, float).copy()
        self.uv = np.asarray(vista.circulo.uv, float).copy()
        self.destino = self.matriz.postura_px(self.uv)
        self._plan = list(trayectoria_suave(q, self.intermedia, self.velocidad, self.hz)) if self.intermedia is not None \
            else []
        self._i = 0
        self._ultima = q
        inicio_final = self.intermedia if self.intermedia is not None else q
        self._tramo_final(inicio_final)

    def _reapuntar(self, vista: Vista | None) -> None:
        if vista is None or vista.circulo is None or self.uv is None:
            return
        uv = np.asarray(vista.circulo.uv, float)
        d = float(np.linalg.norm(uv - self.uv))
        if self.actualizar_px < d <= self.rango_px:
            self.uv = uv.copy()
            self.destino = self.matriz.postura_px(uv)
            # A mitad del tramo final basta con mover su extremo (el perfil sigue, el salto es pequeño); si ya había
            # acabado, un tramo nuevo desde donde está.
            if self._i >= len(self._plan) and self._k_final >= self._n_final:
                self._tramo_final(self._ultima)

    def accion(self, obs: dict | None = None, vista: Vista | None = None) -> np.ndarray:
        self._reapuntar(vista)
        if self._i < len(self._plan):
            q = self._plan[self._i]
            self._i += 1
        else:
            self._k_final = min(self._k_final + 1, self._n_final)
            s = _perfil(self._k_final, self._n_final)
            q =self._final_desde + s * (self.destino - self._final_desde)
        self._ultima = np.asarray(q, float).copy()
        return self._ultima.copy()

    def llegado(self) -> bool:
        return (self.destino is not None and self._ultima is not None and self._i >= len(self._plan)
                and self._k_final >= self._n_final
                and float(np.max(np.abs(self._ultima - self.destino))) <= self.tolerancia)


def _perfil(k: int, n: int) -> float:
    s = k / max(n, 1)
    return float(10 * s**3 - 15 * s**4 + 6 * s**5)


# --- selección por configuración ------------------------------------------------------------------------------------
def crear_politica(cfg, matriz=None, **kwargs):
    """La política que dice `cfg.politica` ("act" o "circulo"). Plug and play: solo cambia el yaml (o la app)."""
    if cfg.politica == "circulo":
        if matriz is None:
            raise ValueError("la política del círculo necesita la matriz")
        c = cfg.circulo
        return PoliticaCirculo(matriz, c.postura_intermedia, c.velocidad, c.tolerancia, c.actualizar_px,
                               cfg.tiempos.rango_salida_px, cfg.hz)
    if cfg.politica == "act":
        a = cfg.act
        return PoliticaACT(a.modelo, a.dispositivo, a.camaras or None, a.estado, a.ensemble, a.umbral_llegada,
                           a.pasos_llegada, a.tiempo_max, cfg.hz, a.tarea, **kwargs)
    raise ValueError(f"política desconocida: {cfg.politica}")


def leer_features(ruta_o_repo) -> dict:
    """Las input_features del config.json de un checkpoint (sin cargar el modelo), para enseñar en la app."""
    datos = json.loads((resolver_modelo(ruta_o_repo) / "config.json").read_text(encoding="utf-8"))
    return datos.get("input_features", {})
