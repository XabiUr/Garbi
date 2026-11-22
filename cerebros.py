#!/usr/bin/env python3
"""
cerebros.py - Cerebros (controladores) para el robot.

Interfaz común:
- reset() - Reinicia el estado interno
- paso(obs, percepcion) -> accion - Calcula acción para un ciclo

Cerebros disponibles:
- CerebroZonas: Interpolación bilineal entre posturas de la cuadrícula 3×3
- CerebroACT: Ejecuta una política ACT entrenada
"""

import json
import numpy as np
from typing import Dict, Optional, Tuple
from abc import ABC, abstractmethod


def cargar_config():
    """Carga config.json"""
    with open('config.json', 'r') as f:
        return json.load(f)


def cargar_posturas():
    """Carga posturas.json"""
    try:
        with open('posturas.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(
            "No se encontró posturas.json. Ejecuta primero:\n"
            "  python grabar_posturas.py --real --a-mano"
        )


class Cerebro(ABC):
    """Interfaz base para todos los cerebros"""

    @abstractmethod
    def reset(self):
        """Reinicia el estado interno del cerebro"""
        pass

    @abstractmethod
    def paso(self, obs: Dict, percepcion: Dict) -> Dict:
        """
        Calcula la acción para un ciclo.

        Args:
            obs: Observación del robot (dict con claves motor.pos e imágenes)
            percepcion: Dict devuelto por DetectorMorado.detectar()

        Returns:
            Dict con acción {motor.pos: valor}
        """
        pass


class CerebroZonas(Cerebro):
    """
    Cerebro basado en interpolación bilineal entre posturas de la cuadrícula 5×3.

    Dada una posición (u,v) del taladro, interpola entre las 4 posturas más cercanas
    de la cuadrícula para generar una postura objetivo suave.

    Grid 5×3: 5 columnas (eje U, horizontal), 3 filas (eje V, profundidad)
    """

    MOTOR_NAMES = [
        "shoulder_pan", "shoulder_lift", "elbow_flex",
        "wrist_flex", "wrist_roll", "gripper"
    ]

    def __init__(self, config: Optional[Dict] = None):
        if config is None:
            config = cargar_config()

        self.config = config
        self.posturas_data = cargar_posturas()

        # Crear grid 5x3 de posturas
        # Índices: grid[u_idx][v_idx] donde u_idx ∈ {0,1,2,3,4}, v_idx ∈ {0,1,2}
        self.grid = self._construir_grid()

        # Objetivo congelado (para modo sin seguimiento)
        self.objetivo_congelado = None  # (u, v) congelado al inicio del episodio

        print("[CerebroZonas] Inicializado con cuadrícula 5×3")

    def _construir_grid(self) -> np.ndarray:
        """
        Construye el grid 5×3 de posturas.

        Returns:
            Array de shape (5, 3, N_MOTORS) donde N_MOTORS = 6
        """
        # Mapeo de número de postura a índices del grid
        # Cuadrícula 5×3:
        #   13(0,2)  14(1,2)  15(2,2)  16(3,2)  17(4,2)   <- Fila trasera (v=2)
        #    8(0,1)   9(1,1)  10(2,1)  11(3,1)  12(4,1)   <- Fila media (v=1)
        #    3(0,0)   4(1,0)   5(2,0)   6(3,0)   7(4,0)   <- Fila frontal (v=0)
        #    ^                                        ^
        #  izq (u=0)                             der (u=4)

        mapeo = {
            '3': (0, 0), '4': (1, 0), '5': (2, 0), '6': (3, 0), '7': (4, 0),  # Frontal
            '8': (0, 1), '9': (1, 1), '10': (2, 1), '11': (3, 1), '12': (4, 1),  # Media
            '13': (0, 2), '14': (1, 2), '15': (2, 2), '16': (3, 2), '17': (4, 2),  # Trasera
        }

        grid = np.zeros((5, 3, len(self.MOTOR_NAMES)))

        for num, (u_idx, v_idx) in mapeo.items():
            if num in self.posturas_data["posturas"]:
                postura = self.posturas_data["posturas"][num]
                for i, motor in enumerate(self.MOTOR_NAMES):
                    key = f"{motor}.pos"
                    grid[u_idx, v_idx, i] = postura.get(key, 0.0)
            else:
                raise ValueError(f"Falta postura {num} en posturas.json")

        return grid

    def reset(self):
        """Resetea el estado interno del cerebro"""
        self.objetivo_congelado = None
        print("[CerebroZonas] Objetivo congelado reseteado")

    def interpolacion_bilineal(self, u: float, v: float) -> np.ndarray:
        """
        Interpola bilinealmente entre las 4 posturas cercanas.

        Args:
            u, v: Coordenadas en [0, 1]

        Returns:
            Array de 6 valores (una postura completa)
        """
        # Mapear (u,v) de [0,1] a índices del grid
        # u: [0,1] -> [0,4] (5 columnas)
        # v: [0,1] -> [0,2] (3 filas)
        u_grid = u * 4.0
        v_grid = v * 2.0

        # Clipping por seguridad
        u_grid = np.clip(u_grid, 0.0, 4.0)
        v_grid = np.clip(v_grid, 0.0, 2.0)

        # Índices de las esquinas del cuadrado que contiene (u,v)
        u0 = int(np.floor(u_grid))
        u1 = min(u0 + 1, 4)  # Máximo 4 (índice de la columna 5)
        v0 = int(np.floor(v_grid))
        v1 = min(v0 + 1, 2)  # Máximo 2 (índice de la fila 3)

        # Pesos de interpolación
        tu = u_grid - u0
        tv = v_grid - v0

        # Interpolación bilineal
        # P(u,v) = (1-tu)(1-tv)P00 + tu(1-tv)P10 + (1-tu)tv*P01 + tu*tv*P11
        postura = (
            (1 - tu) * (1 - tv) * self.grid[u0, v0] +
            tu * (1 - tv) * self.grid[u1, v0] +
            (1 - tu) * tv * self.grid[u0, v1] +
            tu * tv * self.grid[u1, v1]
        )

        return postura

    def paso(self, obs: Dict, percepcion: Dict) -> Dict:
        """
        Calcula acción interpolando posturas según (u,v) del taladro.

        Args:
            obs: Observación del robot
            percepcion: Resultado de DetectorMorado.detectar()

        Returns:
            Acción {motor.pos: valor}
        """
        # Si no hay taladro o no está en la zona, ir a reposo
        if not percepcion["hay_taladro"] or not percepcion["dentro_zona"]:
            if self.posturas_data["reposo"] is None:
                # Sin reposo definido, mantener posición actual
                accion = {}
                for motor in self.MOTOR_NAMES:
                    key = f"{motor}.pos"
                    accion[key] = obs.get(key, 0.0)
                return accion
            else:
                # Ir a reposo
                return self.posturas_data["reposo"].copy()

        # Congelar objetivo (u,v) en el primer paso del episodio
        if self.objetivo_congelado is None:
            u = percepcion["u"]
            v = percepcion["v"]
            # Recortar u,v a [0,1] para interpolación
            u = np.clip(u, 0.0, 1.0)
            v = np.clip(v, 0.0, 1.0)
            self.objetivo_congelado = (u, v)
            print(f"[CerebroZonas] Objetivo congelado en (u={u:.3f}, v={v:.3f})")

        # Usar objetivo congelado
        u, v = self.objetivo_congelado

        postura_objetivo = self.interpolacion_bilineal(u, v)

        # Convertir a dict de acción
        accion = {}
        for i, motor in enumerate(self.MOTOR_NAMES):
            key = f"{motor}.pos"
            accion[key] = float(postura_objetivo[i])

        return accion


class CerebroACT(Cerebro):
    """
    Cerebro que ejecuta una política ACT entrenada (LeRobot 0.7).

    Carga el modelo y sus procesadores (normalización) desde un directorio
    local o un repo de Hugging Face, y usa la misma ruta de inferencia que
    lerobot-rollout (predict_action).
    """

    # Mismo orden de motores que en el dataset grabado
    MOTORES = [
        "shoulder_pan.pos", "shoulder_lift.pos", "elbow_flex.pos",
        "wrist_flex.pos", "wrist_roll.pos", "gripper.pos",
    ]
    # Misma tarea que en grabar_dataset_auto.py
    TAREA = "Acercar la boca de aspiracion a la broca del taladro"

    def __init__(self, modelo_path: str, device: Optional[str] = None):
        """
        Args:
            modelo_path: Carpeta local o repo de HF (ej: "Xaflas/act_2026-11-21_21-50-02")
            device: "mps", "cuda" o "cpu" (None = automático)
        """
        import torch
        from lerobot.configs.policies import PreTrainedConfig
        from lerobot.policies.factory import get_policy_class, make_pre_post_processors

        if device is None:
            if torch.cuda.is_available():
                device = "cuda"
            elif torch.backends.mps.is_available():
                device = "mps"
            else:
                device = "cpu"
        self.modelo_path = modelo_path
        self.device = device
        self.torch_device = torch.device(device)

        print(f"[CerebroACT] Cargando modelo desde {modelo_path} en {device}...")
        try:
            cfg = PreTrainedConfig.from_pretrained(modelo_path)
            cfg.pretrained_path = modelo_path
            cfg.device = device
            self.policy = get_policy_class(cfg.type).from_pretrained(modelo_path, config=cfg)
            self.policy.to(self.torch_device)
            self.policy.eval()
            self.preprocessor, self.postprocessor = make_pre_post_processors(
                policy_cfg=cfg,
                pretrained_path=modelo_path,
                preprocessor_overrides={"device_processor": {"device": device}},
            )
        except Exception as e:
            raise RuntimeError(
                f"Error al cargar modelo ACT desde {modelo_path}:\n{e}\n\n"
                "Verifica que el repo/carpeta contiene config.json, model.safetensors "
                "y los ficheros policy_preprocessor/postprocessor"
            )

        # Cámaras que espera el modelo (p.ej. ["front", "gripper"])
        self.camaras = [k.removeprefix("observation.images.")
                        for k in cfg.input_features if k.startswith("observation.images.")]
        self.formas = {k.removeprefix("observation.images."): tuple(v.shape)
                       for k, v in cfg.input_features.items() if k.startswith("observation.images.")}
        print(f"[CerebroACT] Modelo cargado ✓ (cámaras: {self.camaras}, "
              f"chunk={getattr(cfg, 'chunk_size', '?')}, pasos por chunk={getattr(cfg, 'n_action_steps', '?')})")

        # Calentamiento: la primera inferencia en MPS tarda ~0.5 s; mejor aquí que
        # en mitad de la primera aproximación
        obs_dummy = {m: 0.0 for m in self.MOTORES}
        for cam, (c, h, w) in self.formas.items():
            obs_dummy[cam] = np.zeros((h, w, c), dtype=np.uint8)
        self.paso(obs_dummy, {})
        self.reset()

    def reset(self):
        """Resetea la cola de acciones de ACT (llamar al empezar cada aproximación)"""
        self.policy.reset()
        self.preprocessor.reset()
        self.postprocessor.reset()
        print("[CerebroACT] Estado reseteado")

    def paso(self, obs: Dict, percepcion: Dict) -> Dict:
        """
        Calcula la acción con la política ACT.

        Args:
            obs: Observación del robot (motores *.pos + imágenes RGB uint8 HxWx3)
            percepcion: No la usa ACT (se mantiene por la interfaz común)

        Returns:
            Acción {motor.pos: valor}
        """
        from lerobot.common.control_utils import predict_action

        observacion = {
            "observation.state": np.array([obs[m] for m in self.MOTORES], dtype=np.float32)
        }
        for cam in self.camaras:
            img = obs[cam]
            c, h, w = self.formas[cam]
            if img.shape[:2] != (h, w):
                raise ValueError(f"Cámara '{cam}' da {img.shape[:2]} y el modelo espera {(h, w)}")
            observacion[f"observation.images.{cam}"] = img

        accion = predict_action(
            observacion, self.policy, self.torch_device,
            self.preprocessor, self.postprocessor,
            use_amp=False, task=self.TAREA, robot_type="so_follower",
        )
        valores = accion.squeeze(0).float().cpu().numpy()
        return {m: float(v) for m, v in zip(self.MOTORES, valores)}


# Script de test
if __name__ == "__main__":
    print("="*60)
    print("TEST DE CEREBROS")
    print("="*60)

    # Cargar posturas y config
    config = cargar_config()
    posturas = cargar_posturas()

    # Test CerebroZonas
    print("\nTest 1: CerebroZonas")
    print("-"*60)

    cerebro_zonas = CerebroZonas(config)

    # Observación de ejemplo
    obs = {
        "shoulder_pan.pos": 0.0,
        "shoulder_lift.pos": -20.0,
        "elbow_flex.pos": 30.0,
        "wrist_flex.pos": 10.0,
        "wrist_roll.pos": 0.0,
        "gripper.pos": 50.0
    }

    # Percepción de ejemplo (centro de la zona)
    percepcion = {
        "hay_taladro": True,
        "estable": True,
        "u": 0.5,
        "v": 0.5,
        "dentro_zona": True
    }

    accion = cerebro_zonas.paso(obs, percepcion)
    print(f"Acción para (u=0.5, v=0.5): {list(accion.values())[:3]}...")

    # Test en esquina
    percepcion["u"] = 0.0
    percepcion["v"] = 0.0
    accion = cerebro_zonas.paso(obs, percepcion)
    print(f"Acción para (u=0.0, v=0.0): {list(accion.values())[:3]}...")

    # Test sin taladro
    percepcion["hay_taladro"] = False
    accion = cerebro_zonas.paso(obs, percepcion)
    print(f"Acción sin taladro (reposo): {list(accion.values())[:3]}...")

    print("\n✓ Tests de CerebroZonas completados")
    print("\nNota: CerebroACT requiere un modelo entrenado para probarse")
