#!/usr/bin/env python3
"""
test_conexion.py - Script mínimo para probar conexión al robot (real o falso).

Uso:
    python test_conexion.py --sin-robot    # Usa RobotFalso (webcam)
    python test_conexion.py --real         # Usa robot SO-100 real
"""

import argparse
import json
import cv2
import numpy as np


def cargar_config():
    """Carga config.json"""
    with open('config.json', 'r') as f:
        return json.load(f)


def crear_robot(config, sin_robot: bool):
    """
    Crea el robot (real o falso) según el flag.

    Args:
        config: Configuración del archivo config.json
        sin_robot: Si True, usa RobotFalso; si False, usa SO100Follower

    Returns:
        Robot (RobotFalso o SO100Follower)
    """
    if sin_robot:
        # Modo simulado: usar RobotFalso con webcam
        print("🟢 Modo SIN ROBOT (simulado con webcam)")
        from robot_falso import RobotFalso
        robot = RobotFalso(camera_index_front=config["robot"]["cameras"]["front"]["index_or_path"])
        return robot
    else:
        # Modo real: usar LeRobot
        print("🔴 Modo ROBOT REAL")
        from lerobot.robots.so_follower import SO101Follower, SO101FollowerConfig
        from lerobot.cameras.opencv import OpenCVCameraConfig

        # Construir configuración del robot
        robot_config = SO101FollowerConfig(
            port=config["robot"]["port"],
            use_degrees=config["robot"]["use_degrees"],
            cameras={
                name: OpenCVCameraConfig(
                    index_or_path=cam_cfg["index_or_path"],
                    width=cam_cfg["width"],
                    height=cam_cfg["height"],
                    fps=cam_cfg["fps"]
                )
                for name, cam_cfg in config["robot"]["cameras"].items()
            },
            id=config["robot"]["id"]
        )

        robot = SO101Follower(robot_config)
        return robot


def imprimir_observacion(obs):
    """
    Imprime información de una observación.

    Args:
        obs: Dict con la observación del robot
    """
    print("\n" + "=" * 60)
    print("OBSERVACIÓN RECIBIDA")
    print("=" * 60)

    # Claves disponibles
    print(f"\nClaves totales: {len(obs)}")
    print(f"Claves: {list(obs.keys())}")

    # Articulaciones
    print("\nARTICULACIONES:")
    motor_keys = [k for k in obs.keys() if k.endswith(".pos")]
    for key in sorted(motor_keys):
        value = obs[key]
        print(f"  {key:<20} = {value:>8.2f}")

    # Imágenes
    print("\nIMAGENES:")
    image_keys = [k for k in obs.keys() if isinstance(obs[k], np.ndarray) and obs[k].ndim == 3]
    for key in sorted(image_keys):
        img = obs[key]
        h, w, c = img.shape
        dtype = img.dtype
        print(f"  {key:<10} shape: ({h}, {w}, {c}), dtype: {dtype}, min: {img.min()}, max: {img.max()}")

    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description='Test de conexión al robot SO-100')
    parser.add_argument('--sin-robot', action='store_true',
                       help='Usar RobotFalso (simulado con webcam)')
    parser.add_argument('--real', action='store_true',
                       help='Usar robot SO-100 real')
    args = parser.parse_args()

    # Verificar flags
    if not args.sin_robot and not args.real:
        print("❌ Error: Debes especificar --sin-robot o --real")
        print("\nEjemplos:")
        print("  python test_conexion.py --sin-robot    # Modo simulado")
        print("  python test_conexion.py --real         # Robot real")
        return

    if args.sin_robot and args.real:
        print("❌ Error: No puedes usar --sin-robot y --real al mismo tiempo")
        return

    # Cargar configuración
    config = cargar_config()
    print(f"✓ Config cargado: {len(config)} secciones")

    # Crear robot
    print("\nCreando robot...")
    robot = crear_robot(config, sin_robot=args.sin_robot)
    print(f"✓ Robot creado: {type(robot).__name__}")

    # Conectar
    print("\nConectando...")
    robot.connect(calibrate=False)
    print(f"✓ Robot conectado: is_connected = {robot.is_connected}")

    # Leer observación inicial
    print("\nLeyendo observación inicial...")
    obs = robot.get_observation()
    print("✓ Observación recibida")

    # Imprimir detalles
    imprimir_observacion(obs)

    # Mostrar video en vivo de "front"
    if "front" in obs:
        print("\nMostrando VIDEO EN VIVO de 'front'...")
        print("Presiona 'q' o ESC para cerrar")

        # Bucle de video en vivo
        while True:
            # Leer nueva observación
            obs = robot.get_observation()

            # obs["front"] está en RGB, convertir a BGR para cv2.imshow
            img_bgr = cv2.cvtColor(obs["front"], cv2.COLOR_RGB2BGR)

            # Añadir texto con info de articulaciones
            texto = f"shoulder_pan: {obs['shoulder_pan.pos']:.1f}  gripper: {obs['gripper.pos']:.1f}"
            cv2.putText(img_bgr, texto, (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            cv2.imshow("Robot - Front Camera (LIVE)", img_bgr)

            # Esperar tecla (30 fps aproximadamente)
            tecla = cv2.waitKey(30) & 0xFF
            if tecla == ord('q') or tecla == 27:  # 'q' o ESC
                break

        cv2.destroyAllWindows()

    # Desconectar
    print("\nDesconectando...")
    robot.disconnect()
    print("✓ Robot desconectado")

    print("\n" + "=" * 60)
    print("✅ TEST COMPLETADO EXITOSAMENTE")
    print("=" * 60)


if __name__ == "__main__":
    main()
