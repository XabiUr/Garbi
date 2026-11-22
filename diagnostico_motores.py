#!/usr/bin/env python3
"""
diagnostico_motores.py - Escanea y verifica todos los motores del SO-101 Follower

Uso:
    python diagnostico_motores.py
"""

import json
import sys

def cargar_config():
    """Carga config.json"""
    with open('config.json', 'r') as f:
        return json.load(f)

def escanear_motores():
    """Escanea todos los motores y reporta su estado"""
    config = cargar_config()
    puerto = config["robot"]["port"]

    print("="*60)
    print("DIAGNÓSTICO DE MOTORES - SO-101 Follower")
    print("="*60)
    print(f"Puerto: {puerto}")
    print()

    # Configuración de motores esperada
    motores_esperados = {
        1: "shoulder_pan",
        2: "shoulder_lift",
        3: "elbow_flex",
        4: "wrist_flex",
        5: "wrist_roll",
        6: "gripper"
    }

    try:
        from lerobot.robots.so_follower import SO101Follower, SO101FollowerConfig

        print("Escaneando motores con LeRobot API...")
        print("-"*60)

        motores_ok = []
        motores_error = []

        # Crear configuración mínima (sin cámaras para diagnóstico)
        robot_config = SO101FollowerConfig(
            port=puerto,
            use_degrees=config["robot"]["use_degrees"],
            cameras={},  # Sin cámaras para ir más rápido
            id=config["robot"]["id"]
        )

        try:
            robot = SO101Follower(robot_config)
            print("Intentando conectar al robot...")
            robot.connect(calibrate=False)

            # Si llegó aquí, todos los motores respondieron
            print("\n✓ Conexión exitosa, leyendo posiciones...")
            obs = robot.get_observation()

            for motor_id, nombre in motores_esperados.items():
                key = f"{nombre}.pos"
                if key in obs:
                    print(f"  ✓ Motor {motor_id} ({nombre:15s}): {obs[key]:7.2f}° - OK")
                    motores_ok.append((motor_id, nombre))
                else:
                    print(f"  ✗ Motor {motor_id} ({nombre:15s}): NO EN OBSERVACIÓN")
                    motores_error.append((motor_id, nombre, "No en observación"))

            robot.disconnect()

        except ConnectionError as e:
            # Error específico de conexión con motor
            error_msg = str(e)
            print(f"\n✗ Error de conexión con motor:")
            print(f"  {error_msg}\n")

            # Intentar detectar qué motor falló del mensaje de error
            motor_encontrado = False
            for motor_id, nombre in motores_esperados.items():
                if nombre in error_msg or f"motor ID {motor_id}" in error_msg:
                    print(f"  ✗✗✗ Motor {motor_id} ({nombre:15s}): CAUSÓ EL ERROR ✗✗✗")
                    motores_error.append((motor_id, nombre, error_msg))
                    motor_encontrado = True

                    # Marcar otros como desconocidos
                    for other_id, other_nombre in motores_esperados.items():
                        if other_id != motor_id:
                            print(f"  ? Motor {other_id} ({other_nombre:15s}): No probado")
                    break

            if not motor_encontrado:
                print("  No se pudo identificar el motor problemático del mensaje")
                motores_error.append((0, "GENERAL", error_msg))

        except Exception as e:
            # Otro tipo de error
            error_msg = str(e)
            print(f"\n✗ Error inesperado: {error_msg}")
            motores_error.append((0, "GENERAL", error_msg))

        # Resumen
        print()
        print("="*60)
        print("RESUMEN")
        print("="*60)
        print(f"Motores OK: {len(motores_ok)}/6")
        print(f"Motores con error: {len(motores_error)}/6")
        print()

        if motores_error:
            print("⚠️  MOTORES CON PROBLEMAS:")
            for motor_id, nombre, error in motores_error:
                print(f"  • Motor {motor_id} ({nombre})")
                print(f"    → {error[:80]}")

            print()
            print("POSIBLES SOLUCIONES:")
            print("1. Verificar que el cable del motor esté bien conectado")
            print("2. Verificar que el motor tenga alimentación (LED encendido)")
            print("3. Verificar que el ID del motor sea correcto")
            print("4. Reiniciar el robot (apagar y encender)")
            print("5. Verificar con el software oficial del fabricante")
        else:
            print("✓ ¡Todos los motores funcionan correctamente!")

        print()

        if len(motores_error) > 0:
            sys.exit(1)
        else:
            sys.exit(0)

    except ImportError as e:
        print(f"✗ Error: No se pudo importar FeetechMotorsBus")
        print(f"  {e}")
        sys.exit(1)
    except Exception as e:
        print(f"✗ Error inesperado: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    escanear_motores()
