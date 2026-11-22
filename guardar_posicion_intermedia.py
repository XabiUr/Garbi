#!/usr/bin/env python3
"""
guardar_posicion_intermedia.py - Guarda la posición actual del brazo como posición intermedia.

Uso:
    1. Mueve el brazo manualmente (con torque desactivado) o con teleoperation
       a la posición que quieras como intermedia (alta, segura, atrás)
    2. Ejecuta este script: python guardar_posicion_intermedia.py --real
    3. La posición se guarda automáticamente en config.json

Opciones:
    --sin-robot    Modo simulado (prueba)
    --real         Con robot real
"""

import argparse
import json
import sys


def cargar_config():
    """Carga config.json"""
    with open('config.json', 'r') as f:
        return json.load(f)


def guardar_config(config):
    """Guarda config.json"""
    with open('config.json', 'w') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def main():
    parser = argparse.ArgumentParser(description='Guardar posición intermedia del brazo')
    parser.add_argument('--sin-robot', action='store_true', help='Modo simulado')
    parser.add_argument('--real', action='store_true', help='Con robot real')
    args = parser.parse_args()

    if not args.sin_robot and not args.real:
        print("❌ Error: Debes especificar --sin-robot o --real")
        return

    # Cargar config
    config = cargar_config()

    print("\n" + "="*60)
    print("GUARDAR POSICIÓN INTERMEDIA")
    print("="*60)
    print("\nEste script guardará la posición ACTUAL del brazo")
    print("como la nueva posición intermedia en config.json")
    print("\nAsegúrate de que el brazo esté en la posición deseada:")
    print("  • Alto (para evitar colisiones)")
    print("  • Atrás (suficiente espacio para retroceder)")
    print("  • Centro o posición cómoda para girar")
    print("="*60 + "\n")

    if args.sin_robot:
        print("❌ Modo simulado no soportado para este script")
        print("   Debes usar --real para leer la posición del robot")
        return

    # Crear robot
    from lerobot.robots.so_follower import SO101Follower, SO101FollowerConfig
    from lerobot.cameras.opencv import OpenCVCameraConfig

    robot_config = SO101FollowerConfig(
        port=config["robot"]["port"],
        use_degrees=config["robot"]["use_degrees"],
        cameras={},  # Sin cámaras para ir más rápido
        id=config["robot"]["id"]
    )

    print("Conectando al robot...")
    robot = SO101Follower(robot_config)
    robot.connect(calibrate=False)

    # Leer posición actual
    print("Leyendo posición actual del brazo...")
    obs = robot.get_observation()

    # Extraer posiciones de motores
    posicion_intermedia = {}
    motor_names = [
        "shoulder_pan", "shoulder_lift", "elbow_flex",
        "wrist_flex", "wrist_roll", "gripper"
    ]

    print("\nPosición actual:")
    print("-"*60)
    for motor in motor_names:
        key = f"{motor}.pos"
        if key in obs:
            valor = float(obs[key])
            posicion_intermedia[key] = valor
            print(f"  {motor:20s}: {valor:7.2f}°")
        else:
            print(f"  ⚠️  {motor}: NO ENCONTRADO")

    robot.disconnect()

    # Confirmar guardado
    print("\n" + "="*60)
    respuesta = input("¿Guardar esta posición como intermedia? (s/N): ")

    if respuesta.lower() not in ['s', 'si', 'sí', 'y', 'yes']:
        print("\n❌ Guardado cancelado")
        return

    # Guardar en config
    if "supervisor" not in config:
        config["supervisor"] = {}

    config["supervisor"]["posicion_intermedia"] = posicion_intermedia

    guardar_config(config)

    print("\n✅ Posición intermedia guardada en config.json")
    print("\nLa nueva trayectoria será:")
    print("  REPOSO → YENDO_A_INTERMEDIA (esta posición) → APROXIMANDO → ...")
    print("\nPruébalo con:")
    print("  python supervisor.py --cerebro zonas --real")
    print("\n" + "="*60)


if __name__ == "__main__":
    main()
