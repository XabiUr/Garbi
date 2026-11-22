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
    Cerebro basado en interpolación bilineal entre posturas de la cuadrícula 3×3.

    Dada una posición (u,v) del taladro, interpola entre las 4 posturas más cercanas
    de la cuadrícula para generar una postura objetivo suave.
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

        # Crear grid 3x3 de posturas
        # Índices: grid[u_idx][v_idx] donde u_idx, v_idx ∈ {0, 1, 2}
        self.grid = self._construir_grid()

        print("[CerebroZonas] Inicializado con cuadrícula 3×3")

    def _construir_grid(self) -> np.ndarray:
        """
        Construye el grid 3×3 de posturas.

        Returns:
            Array de shape (3, 3, N_MOTORS) donde N_MOTORS = 6
        """
        # Mapeo de número de postura a índices del grid
        # Cuadrícula:
        #   7(0,2)  8(1,2)  9(2,2)
        #   4(0,1)  5(1,1)  6(2,1)
        #   1(0,0)  2(1,0)  3(2,0)

        mapeo = {
            '1': (0, 0), '2': (1, 0), '3': (2, 0),
            '4': (0, 1), '5': (1, 1), '6': (2, 1),
            '7': (0, 2), '8': (1, 2), '9': (2, 2),
        }

        grid = np.zeros((3, 3, len(self.MOTOR_NAMES)))

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
        """No hay estado interno que resetear"""
        pass

    def interpolacion_bilineal(self, u: float, v: float) -> np.ndarray:
        """
        Interpola bilinealmente entre las 4 posturas cercanas.

        Args:
            u, v: Coordenadas en [0, 1]

        Returns:
            Array de 6 valores (una postura completa)
        """
        # Mapear (u,v) de [0,1] a [0,2] (índices del grid)
        u_grid = u * 2.0
        v_grid = v * 2.0

        # Clipping por seguridad
        u_grid = np.clip(u_grid, 0.0, 2.0)
        v_grid = np.clip(v_grid, 0.0, 2.0)

        # Índices de las esquinas del cuadrado que contiene (u,v)
        u0 = int(np.floor(u_grid))
        u1 = min(u0 + 1, 2)
        v0 = int(np.floor(v_grid))
        v1 = min(v0 + 1, 2)

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

        # Interpolar según (u,v)
        u = percepcion["u"]
        v = percepcion["v"]

        # Invertir u si las posturas están al revés (descomentar si necesario)
        u = 1.0 - u  # Invierte el eje horizontal

        postura_objetivo = self.interpolacion_bilineal(u, v)

        # Convertir a dict de acción
        accion = {}
        for i, motor in enumerate(self.MOTOR_NAMES):
            key = f"{motor}.pos"
            accion[key] = float(postura_objetivo[i])

        return accion


class CerebroACT(Cerebro):
    """
    Cerebro que ejecuta una política ACT entrenada.

    Carga el modelo desde un directorio o repo de Hugging Face.
    """

    def __init__(self, modelo_path: str, device: str = "mps"):
        """
        Args:
            modelo_path: Ruta a carpeta con modelo ACT o repo de HF (ej: "Xaflas/act-so100-taladro")
            device: "mps" (Apple Silicon), "cuda" (NVIDIA) o "cpu"
        """
        self.modelo_path = modelo_path
        self.device = device

        print(f"[CerebroACT] Cargando modelo desde {modelo_path}...")

        try:
            from lerobot.policies.pretrained import PreTrainedPolicy

            # Cargar política
            # En LeRobot 0.7.0, se hace con PreTrainedPolicy.from_pretrained()
            self.policy = PreTrainedPolicy.from_pretrained(modelo_path)
            self.policy.to(device)
            self.policy.eval()

            print(f"[CerebroACT] Modelo cargado en {device} ✓")

        except Exception as e:
            raise RuntimeError(
                f"Error al cargar modelo ACT desde {modelo_path}:\n{e}\n\n"
                "Verifica:\n"
                "  1. El path existe y contiene un modelo ACT\n"
                "  2. LeRobot está instalado con todas las dependencias\n"
                "  3. El modelo es compatible con LeRobot 0.7.0"
            )

        # Estado interno de ACT (para políticas autoregresivas)
        self.policy_state = None

    def reset(self):
        """Resetea el estado interno de la política"""
        self.policy_state = None
        print("[CerebroACT] Estado reseteado")

    def paso(self, obs: Dict, percepcion: Dict) -> Dict:
        """
        Calcula acción usando la política ACT.

        Args:
            obs: Observación del robot (dict con imágenes y estado)
            percepcion: Resultado de DetectorMorado (no usado directamente por ACT)

        Returns:
            Acción {motor.pos: valor}
        """
        import torch

        # Convertir observación a formato para ACT
        # ACT espera:
        # - observation.images: dict de tensors {cam_key: tensor (1, C, H, W)}
        # - observation.state: dict de tensors {motor_key: tensor (1,)}

        with torch.no_grad():
            # Preparar imágenes (RGB -> tensor normalizado)
            images = {}
            for key in ["front", "gripper"]:
                if key in obs:
                    img_np = obs[key]  # (H, W, 3) en RGB, uint8
                    # Convertir a tensor (1, 3, H, W) y normalizar a [0, 1]
                    img_tensor = torch.from_numpy(img_np).float() / 255.0
                    img_tensor = img_tensor.permute(2, 0, 1).unsqueeze(0)  # (1, 3, H, W)
                    images[key] = img_tensor.to(self.device)

            # Preparar estado (articulaciones)
            state = {}
            for key in obs:
                if key.endswith(".pos"):
                    state[key] = torch.tensor([obs[key]], dtype=torch.float32).to(self.device)

            # Crear dict de observación
            obs_policy = {
                "observation.images": images,
                "observation.state": state
            }

            # Ejecutar política
            action = self.policy.select_action(obs_policy)

            # Convertir acción de tensor a dict
            accion_dict = {}
            for key, tensor in action.items():
                accion_dict[key] = float(tensor.cpu().numpy())

            return accion_dict


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
