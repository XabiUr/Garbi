#!/usr/bin/env python3
"""
probar_posicion_intermedia.py - Prueba la posición intermedia configurada.

Mueve el brazo a la posición intermedia definida en config.json
para verificar que es segura y adecuada.

Uso:
    python probar_posicion_intermedia.py --real
"""

import argparse
import json
import time


def cargar_config():
    """Carga config.json"""
    with open('config.json', 'r') as f:
        return json.load(f)


def main():
    parser = argparse.ArgumentParser(description='Probar posición intermedia')
    parser.add_argument('--real', action='store_true', help='Con robot real')
    args = parser.parse_args()

    if not args.real:
        print("❌ Error: Debes especificar --real")
        return

    # Cargar config
    config = cargar_config()

    if "posicion_intermedia" not in config.get("supervisor", {}):
        print("❌ Error: No hay posición intermedia configurada en config.json")
        print("\nEjecuta primero:")
        print("  python guardar_posicion_intermedia.py --real")
        return

    posicion_intermedia = config["supervisor"]["posicion_intermedia"]

    print("\n" + "="*60)
    print("PROBAR POSICIÓN INTERMEDIA")
    print("="*60)
    print("\nPosición intermedia configurada:")
    print("-"*60)
    for key, valor in posicion_intermedia.items():
        motor = key.replace(".pos", "")
        print(f"  {motor:20s}: {valor:7.2f}°")
    print("-"*60)
    print("\nEl robot se moverá a esta posición en 3 segundos.")
    print("Verifica que:")
    print("  • Es suficientemente ALTA (no choca con nada)")
    print("  • Está suficientemente ATRÁS (espacio para retroceder)")
    print("  • Es cómoda para girar hacia el taladro")
    print("="*60 + "\n")

    respuesta = input("¿Mover el robot a esta posición? (s/N): ")
    if respuesta.lower() not in ['s', 'si', 'sí', 'y', 'yes']:
        print("\n❌ Cancelado")
        return

    # Crear robot
    from lerobot.robots.so_follower import SO101Follower, SO101FollowerConfig

    robot_config = SO101FollowerConfig(
        port=config["robot"]["port"],
        use_degrees=config["robot"]["use_degrees"],
        cameras={},
        id=config["robot"]["id"]
    )

    print("\nConectando al robot...")
    robot = SO101Follower(robot_config)
    robot.connect(calibrate=False)

    print("Moviendo a posición intermedia...")
    print("(Movimiento gradual durante 3 segundos)")

    # Mover gradualmente durante 3 segundos
    for _ in range(90):  # 3 segundos a 30Hz
        robot.send_action(posicion_intermedia)
        time.sleep(1.0 / 30)

    print("\n✅ Posición intermedia alcanzada")
    print("\n¿La posición es adecuada?")
    print("  • Si SÍ: Ya está lista para usar con el supervisor")
    print("  • Si NO: Mueve el brazo manualmente y ejecuta:")
    print("           python guardar_posicion_intermedia.py --real")

    input("\nPresiona Enter para finalizar...")

    robot.disconnect()
    print("\n✅ Finalizado")


if __name__ == "__main__":
    main()
