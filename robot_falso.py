#!/usr/bin/env python3
"""
robot_falso.py - Robot simulado para probar sin hardware.

Compatible con la API de LeRobot 0.7.0 (misma interfaz que SO100Follower).
Usa la webcam del Mac como "front" y simula las articulaciones.
"""

import cv2
import numpy as np
import time
from typing import Dict
from lerobot.lerobot_types import RobotAction, RobotObservation


class RobotFalso:
    """
    Robot simulado con la misma interfaz que SO100Follower.

    - get_observation() devuelve imagen de webcam + articulaciones simuladas
    - send_action() actualiza las articulaciones con un pequeño retardo
    - Articulaciones en [-100, 100] (normalizado) como use_degrees=False
    """

    MOTOR_NAMES = [
        "shoulder_pan", "shoulder_lift", "elbow_flex",
        "wrist_flex", "wrist_roll", "gripper"
    ]

    def __init__(self, camera_index_front: int = 0):
        """
        Args:
            camera_index_front: Índice de la webcam para usar como "front"
        """
        self.camera_index_front = camera_index_front
        self.cap_front = None
        self._is_connected = False

        # Estado de las articulaciones (normalizado [-100, 100] excepto gripper [0, 100])
        self.current_positions = {
            "shoulder_pan": 0.0,
            "shoulder_lift": -20.0,
            "elbow_flex": 30.0,
            "wrist_flex": 10.0,
            "wrist_roll": 0.0,
            "gripper": 50.0  # Semi-abierto
        }

        # Objetivo de las articulaciones (para simular movimiento suave)
        self.target_positions = self.current_positions.copy()

        # Velocidad de seguimiento (simulado)
        self.follow_speed = 0.2  # 20% del camino en cada ciclo

        print("[RobotFalso] Inicializado")

    def connect(self, calibrate: bool = False) -> None:
        """Conecta a la webcam (simula conexión al robot real)"""
        print("[RobotFalso] Conectando...")

        # Abrir cámara frontal (usar backend AVFoundation en macOS)
        # En macOS, el backend CAP_AVFOUNDATION suele funcionar mejor
        try:
            self.cap_front = cv2.VideoCapture(self.camera_index_front, cv2.CAP_AVFOUNDATION)
        except:
            # Fallback a default
            self.cap_front = cv2.VideoCapture(self.camera_index_front)

        if not self.cap_front.isOpened():
            raise RuntimeError(f"No se pudo abrir la cámara {self.camera_index_front}")

        # Configurar resolución
        self.cap_front.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap_front.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        # Configurar autoexposure y otros parámetros
        # Estos pueden ayudar en macOS
        self.cap_front.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.75)  # Auto exposure
        self.cap_front.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Buffer pequeño = menos latencia

        # IMPORTANTE: Leer y descartar los primeros frames (cámara necesita tiempo)
        print("[RobotFalso] Estabilizando cámara (esto puede tardar ~3 segundos)...")
        for i in range(30):
            ret, frame = self.cap_front.read()
            if i % 10 == 0:
                print(f"  Frame {i+1}/30: {'OK' if ret and frame is not None else 'FAIL'}")
            time.sleep(0.1)

        # Verificar que la cámara está dando frames válidos
        ret, test_frame = self.cap_front.read()
        if not ret or test_frame is None:
            raise RuntimeError(
                f"La cámara {self.camera_index_front} no está devolviendo frames válidos.\n"
                "Posibles soluciones:\n"
                "  1. Verifica permisos de cámara en Preferencias del Sistema\n"
                "  2. Cierra otras apps que usen la cámara (Zoom, Teams, etc.)\n"
                "  3. Prueba con otro índice en config.json (index_or_path: 1)"
            )

        # Verificar que el frame tiene datos (no todo negro)
        if test_frame.max() < 10:
            print("⚠️  ADVERTENCIA: La cámara parece estar dando frames negros")
            print("    Intenta aumentar la iluminación o espera unos segundos más")

        self._is_connected = True
        print("[RobotFalso] Conectado ✓")

    def disconnect(self) -> None:
        """Desconecta y libera recursos"""
        if self.cap_front is not None:
            self.cap_front.release()
        self._is_connected = False
        print("[RobotFalso] Desconectado")

    @property
    def is_connected(self) -> bool:
        return self._is_connected

    def get_observation(self) -> RobotObservation:
        """
        Devuelve observación simulada:
        - Imagen de webcam como "front"
        - Imagen negra como "gripper"
        - Posiciones de articulaciones

        Returns:
            Dict con claves:
            - "shoulder_pan.pos", "shoulder_lift.pos", etc. (float)
            - "front": imagen RGB (H, W, 3), dtype uint8
            - "gripper": imagen RGB negra (H, W, 3), dtype uint8
        """
        if not self._is_connected:
            raise RuntimeError("Robot no conectado. Llama a connect() primero.")

        # Leer frame de cámara
        ret, frame = self.cap_front.read()
        if not ret or frame is None:
            # Si falla, crear imagen negra
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            print("[RobotFalso] Advertencia: No se pudo leer frame de cámara")
        else:
            # OpenCV da BGR, convertir a RGB
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Imagen negra para "gripper"
        gripper_img = np.zeros((480, 640, 3), dtype=np.uint8)

        # Actualizar posiciones actuales hacia objetivos (simular movimiento suave)
        for motor in self.MOTOR_NAMES:
            diff = self.target_positions[motor] - self.current_positions[motor]
            self.current_positions[motor] += diff * self.follow_speed

        # Construir observación
        obs = {
            # Imágenes
            "front": frame,
            "gripper": gripper_img,
        }

        # Articulaciones
        for motor in self.MOTOR_NAMES:
            obs[f"{motor}.pos"] = float(self.current_positions[motor])

        return obs

    def send_action(self, action: RobotAction) -> RobotAction:
        """
        Envía acción al robot simulado (actualiza objetivos).

        Args:
            action: Dict con claves "shoulder_pan.pos", etc.

        Returns:
            La misma acción (sin clipping en simulación)
        """
        if not self._is_connected:
            raise RuntimeError("Robot no conectado. Llama a connect() primero.")

        # Actualizar objetivos
        for motor in self.MOTOR_NAMES:
            key = f"{motor}.pos"
            if key in action:
                # Limitar a rangos válidos
                if motor == "gripper":
                    # Gripper: [0, 100]
                    self.target_positions[motor] = np.clip(action[key], 0.0, 100.0)
                else:
                    # Otros motores: [-100, 100]
                    self.target_positions[motor] = np.clip(action[key], -100.0, 100.0)

        return action

    def __enter__(self):
        """Soporte para 'with' statement"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Desconecta automáticamente al salir del bloque 'with'"""
        self.disconnect()


class TeleoperadorFalso:
    """Teleoperador simulado (no hace nada, para compatibilidad)"""

    def __init__(self):
        print("[TeleoperadorFalso] Inicializado")
        self._is_connected = False

    def connect(self) -> None:
        self._is_connected = True
        print("[TeleoperadorFalso] Conectado ✓")

    def disconnect(self) -> None:
        self._is_connected = False
        print("[TeleoperadorFalso] Desconectado")

    @property
    def is_connected(self) -> bool:
        return self._is_connected

    def get_action(self) -> RobotAction:
        """Devuelve acción nula (posición actual sin cambios)"""
        # En teleooperación real esto leería el leader
        # Aquí devolvemos posición neutra
        return {
            "shoulder_pan.pos": 0.0,
            "shoulder_lift.pos": -20.0,
            "elbow_flex.pos": 30.0,
            "wrist_flex.pos": 10.0,
            "wrist_roll.pos": 0.0,
            "gripper.pos": 50.0
        }

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()


if __name__ == "__main__":
    # Test rápido
    print("Test RobotFalso")
    print("=" * 60)

    robot = RobotFalso(camera_index_front=0)
    robot.connect()

    print("\nObservación inicial:")
    obs = robot.get_observation()
    print(f"  Claves: {list(obs.keys())}")
    print(f"  front shape: {obs['front'].shape}")
    print(f"  shoulder_pan.pos: {obs['shoulder_pan.pos']:.2f}")

    print("\nEnviando acción...")
    action = {
        "shoulder_pan.pos": 20.0,
        "gripper.pos": 80.0
    }
    robot.send_action(action)

    print("\nObservación después de acción:")
    obs = robot.get_observation()
    print(f"  shoulder_pan.pos: {obs['shoulder_pan.pos']:.2f}")
    print(f"  gripper.pos: {obs['gripper.pos']:.2f}")

    robot.disconnect()
    print("\n✓ Test completado")
