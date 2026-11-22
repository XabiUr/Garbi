#!/usr/bin/env python3
"""
grabar_posturas.py - Graba las 15 posturas de la cuadrícula 5×3 para CerebroZonas.

Dos modos:
1. Con teleoperación: Mueves el líder, el seguidor lo imita, presionas 3-17 para grabar
2. A mano (--a-mano): Desactiva torque del seguidor, lo mueves manualmente, presionas 3-17

Cuadrícula 5×3 en (u,v):
  Fila trasera:   13(0.0,1.0)  14(0.25,1.0)  15(0.5,1.0)  16(0.75,1.0)  17(1.0,1.0)
  Fila media:      8(0.0,0.5)   9(0.25,0.5)  10(0.5,0.5)  11(0.75,0.5)  12(1.0,0.5)
  Fila frontal:    3(0.0,0.0)   4(0.25,0.0)   5(0.5,0.0)   6(0.75,0.0)   7(1.0,0.0)

Tecla 'R' guarda reposo (postura neutral cuando no hay taladro).

Uso:
    python grabar_posturas.py --sin-robot            # Simulado con teleop falso
    python grabar_posturas.py --real                 # Con líder y seguidor reales
    python grabar_posturas.py --real --a-mano        # Sin líder, mueves el seguidor a mano
"""

import argparse
import json
import cv2
import numpy as np
import sys
import time


def cargar_config():
    """Carga config.json"""
    with open('config.json', 'r') as f:
        return json.load(f)


def cargar_posturas():
    """Carga posturas.json si existe"""
    try:
        with open('posturas.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        # Crear estructura vacía para grid 5x3
        return {
            "posturas": {},
            "reposo": None,
            "metadata": {
                "orden": "3-17 corresponden a cuadrícula 5x3 en (u,v)",
                "grid": "5 columnas (u: horizontal), 3 filas (v: profundidad)",
                "coordenadas": {
                    # Fila frontal (v=0.0)
                    "3": [0.0, 0.0], "4": [0.25, 0.0], "5": [0.5, 0.0], "6": [0.75, 0.0], "7": [1.0, 0.0],
                    # Fila media (v=0.5)
                    "8": [0.0, 0.5], "9": [0.25, 0.5], "10": [0.5, 0.5], "11": [0.75, 0.5], "12": [1.0, 0.5],
                    # Fila trasera (v=1.0)
                    "13": [0.0, 1.0], "14": [0.25, 1.0], "15": [0.5, 1.0], "16": [0.75, 1.0], "17": [1.0, 1.0]
                }
            }
        }


def guardar_posturas(datos):
    """Guarda posturas.json"""
    with open('posturas.json', 'w') as f:
        json.dump(datos, f, indent=2)
    print("✓ posturas.json guardado")


def crear_robot_y_teleop(config, sin_robot, a_mano):
    """
    Crea robot y teleoperador según flags.

    Returns:
        (robot, teleop) donde teleop puede ser None si --a-mano
    """
    if sin_robot:
        # Modo simulado
        from robot_falso import RobotFalso, TeleoperadorFalso
        robot = RobotFalso(camera_index_front=config["robot"]["cameras"]["front"]["index_or_path"])
        teleop = None if a_mano else TeleoperadorFalso()
        return robot, teleop

    else:
        # Modo real
        from lerobot.robots.so_follower import SO101Follower, SO101FollowerConfig
        from lerobot.cameras.opencv import OpenCVCameraConfig

        # Robot seguidor (follower)
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

        # Teleoperador líder (solo si no es modo a-mano)
        teleop = None
        if not a_mano:
            from lerobot.teleoperators.so_leader import SO101Leader, SO101LeaderConfig
            teleop_config = SO101LeaderConfig(
                port=config["teleop"]["port"],
                id=config["teleop"]["id"]
            )
            teleop = SO101Leader(teleop_config)

        return robot, teleop


class GrabadorPosturas:
    """Grabador interactivo de posturas"""

    # Mapeo de teclas a posiciones (u,v) - Grid 5×3
    CUADRICULA = {
        # Fila frontal (v=0.0)
        '3': (0.0, 0.0), '4': (0.25, 0.0), '5': (0.5, 0.0), '6': (0.75, 0.0), '7': (1.0, 0.0),
        # Fila media (v=0.5)
        '8': (0.0, 0.5), '9': (0.25, 0.5), '10': (0.5, 0.5), '11': (0.75, 0.5), '12': (1.0, 0.5),
        # Fila trasera (v=1.0)
        '13': (0.0, 1.0), '14': (0.25, 1.0), '15': (0.5, 1.0), '16': (0.75, 1.0), '17': (1.0, 1.0),
    }

    def __init__(self, robot, teleop, a_mano):
        self.robot = robot
        self.teleop = teleop
        self.a_mano = a_mano
        self.datos = cargar_posturas()

    def extraer_postura(self, obs):
        """Extrae la postura (articulaciones) de una observación"""
        postura = {}
        for key in obs:
            if key.endswith(".pos"):
                postura[key] = float(obs[key])
        return postura

    def posturas_faltantes(self):
        """Devuelve lista de números (3-17) que faltan"""
        faltantes = []
        for num in [str(i) for i in range(3, 18)]:  # 3-17
            if num not in self.datos["posturas"]:
                faltantes.append(num)
        return faltantes

    def dibujar_cuadricula(self, img_bgr):
        """Dibuja la cuadrícula 5×3 en la imagen"""
        h, w = img_bgr.shape[:2]

        # Dibujar cuadrícula en esquina superior derecha
        x0, y0 = w - 280, 20
        tam = 45

        # Orden: de arriba (fila trasera) a abajo (fila frontal), izq a der
        # Fila trasera: 13-17, Fila media: 8-12, Fila frontal: 3-7
        orden = [13, 14, 15, 16, 17,  # Fila trasera
                 8, 9, 10, 11, 12,    # Fila media
                 3, 4, 5, 6, 7]       # Fila frontal

        for i, num in enumerate(orden):
            fila = i // 5
            col = i % 5
            x = x0 + col * tam
            y = y0 + fila * tam

            num_str = str(num)

            # Color: verde si grabado, rojo si falta
            if num_str in self.datos["posturas"]:
                color = (0, 255, 0)  # Verde
            else:
                color = (0, 0, 255)  # Rojo

            # Rectángulo
            cv2.rectangle(img_bgr, (x, y), (x + tam - 5, y + tam - 5), color, 2)

            # Número (ajustar posición de texto para 2 dígitos)
            offset_x = 10 if num < 10 else 5
            cv2.putText(img_bgr, num_str, (x + offset_x, y + 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

        # Indicador de reposo
        y_reposo = y0 + 150
        color_reposo = (0, 255, 0) if self.datos["reposo"] is not None else (0, 0, 255)
        cv2.putText(img_bgr, "R: Reposo", (x0, y_reposo),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, color_reposo, 2)

    def dibujar_instrucciones(self, img_bgr):
        """Dibuja instrucciones en la imagen"""
        instrucciones = [
            "GRABAR POSTURAS - Cuadricula 5x3",
            "",
            "Teclas 3-9, A-H (A=10..H=17): Grabar postura",
            "Tecla R: Grabar postura de reposo",
            "Tecla Q: Salir y guardar",
            "",
            f"Modo: {'A MANO (mueve el brazo)' if self.a_mano else 'TELEOPERACION (mueve el lider)'}",
            f"Faltan: {len(self.posturas_faltantes())}/15 posturas"
        ]

        y = 30
        for linea in instrucciones:
            cv2.putText(img_bgr, linea, (10, y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
            y += 25

    def run(self):
        """Bucle principal"""
        print("\n" + "="*60)
        print("GRABACIÓN DE POSTURAS")
        print("="*60)
        print("\nCuadrícula 5×3 en coordenadas (u,v):")
        print("  Fila trasera:  13      14      15      16      17")
        print("  Fila media:     8       9      10      11      12")
        print("  Fila frontal:   3       4       5       6       7")
        print("               (izq)                            (der)")
        print("\nTeclas:")
        print("  3-9: Grabar posturas 3-9")
        print("  A-H: Grabar posturas 10-17 (A=10, B=11, ..., H=17)")
        print("  R: Grabar reposo")
        print("  Q: Salir")
        print("="*60 + "\n")

        # Conectar
        self.robot.connect(calibrate=False)

        if self.a_mano:
            # Modo a mano: desactivar torque
            print("⚠️  Desactivando torque del seguidor...")
            print("   Puedes mover el brazo manualmente")
            if hasattr(self.robot, 'bus'):
                # Robot real
                motor_names = ["shoulder_pan", "shoulder_lift", "elbow_flex",
                              "wrist_flex", "wrist_roll", "gripper"]
                for motor in motor_names:
                    self.robot.bus.write("Torque_Enable", motor, 0)
            print("✓ Torque desactivado. Mueve el brazo con la mano.\n")
        else:
            # Modo teleooperación: conectar líder
            if self.teleop is not None:
                self.teleop.connect()
                print("✓ Líder conectado. Mueve el líder para controlar el seguidor.\n")

        # Bucle principal
        try:
            while True:
                # Leer observación del seguidor
                obs = self.robot.get_observation()

                # Si hay teleooperación, enviar acción del líder al seguidor
                if self.teleop is not None and not self.a_mano:
                    action = self.teleop.get_action()
                    self.robot.send_action(action)

                # Mostrar imagen
                img_bgr = cv2.cvtColor(obs["front"], cv2.COLOR_RGB2BGR)
                self.dibujar_instrucciones(img_bgr)
                self.dibujar_cuadricula(img_bgr)

                cv2.imshow("Grabar Posturas", img_bgr)

                # Esperar tecla
                tecla = cv2.waitKey(30) & 0xFF

                if tecla == ord('q') or tecla == 27:
                    print("\nSaliendo...")
                    break

                # Mapeo de teclas a números de postura
                # Teclas 3-9: posturas 3-9
                # Teclas A-H: posturas 10-17 (A=10, B=11, ..., H=17)
                tecla_char = chr(tecla) if tecla < 128 else None
                numero_postura = None

                if tecla_char is not None:
                    if tecla_char in '3456789':
                        numero_postura = tecla_char
                    elif tecla_char in 'abcdefghABCDEFGH':
                        # A/a=10, B/b=11, ..., H/h=17
                        letra_idx = ord(tecla_char.upper()) - ord('A')  # 0-7
                        if letra_idx < 8:
                            numero_postura = str(10 + letra_idx)

                # Grabar postura si se detectó un número válido
                if numero_postura is not None and numero_postura in self.CUADRICULA:
                    postura = self.extraer_postura(obs)
                    u, v = self.CUADRICULA[numero_postura]
                    self.datos["posturas"][numero_postura] = postura
                    print(f"✓ Postura {numero_postura} guardada (u={u}, v={v}): {list(postura.values())[:3]}...")
                    guardar_posturas(self.datos)

                # Tecla R (reposo)
                if tecla_char is not None and (tecla_char == 'r' or tecla_char == 'R'):
                    postura = self.extraer_postura(obs)
                    self.datos["reposo"] = postura
                    print(f"✓ Reposo guardado: {list(postura.values())[:3]}...")
                    guardar_posturas(self.datos)

        except KeyboardInterrupt:
            print("\n\nInterrumpido por usuario")

        finally:
            # Reactivar torque si estaba en modo a-mano
            if self.a_mano and hasattr(self.robot, 'bus'):
                print("\n⚠️  Reactivando torque...")
                motor_names = ["shoulder_pan", "shoulder_lift", "elbow_flex",
                              "wrist_flex", "wrist_roll", "gripper"]
                # Leer posición actual antes de reactivar
                obs_final = self.robot.get_observation()
                postura_final = self.extraer_postura(obs_final)

                # Enviar la posición actual como objetivo
                self.robot.send_action(postura_final)

                # Reactivar torque
                for motor in motor_names:
                    self.robot.bus.write("Torque_Enable", motor, 1)
                print("✓ Torque reactivado. El brazo mantiene la posición.\n")

            # Desconectar
            if self.teleop is not None:
                self.teleop.disconnect()
            self.robot.disconnect()
            cv2.destroyAllWindows()

        # Resumen final
        print("\n" + "="*60)
        print("RESUMEN")
        print("="*60)
        print(f"Posturas grabadas: {len(self.datos['posturas'])}/9")
        print(f"Reposo: {'✓' if self.datos['reposo'] else '✗'}")

        faltantes = self.posturas_faltantes()
        if faltantes:
            print(f"\n⚠️  Faltan posturas: {', '.join(faltantes)}")
        else:
            print("\n✅ TODAS las posturas grabadas!")

        print("="*60)


def main():
    parser = argparse.ArgumentParser(description='Grabar posturas para CerebroZonas')
    parser.add_argument('--sin-robot', action='store_true', help='Modo simulado')
    parser.add_argument('--real', action='store_true', help='Robot real')
    parser.add_argument('--a-mano', action='store_true',
                       help='Modo a mano (sin líder, mueves el seguidor manualmente)')
    args = parser.parse_args()

    if not args.sin_robot and not args.real:
        print("❌ Debes especificar --sin-robot o --real")
        return

    # Cargar config
    config = cargar_config()

    # Crear robot y teleoperador
    robot, teleop = crear_robot_y_teleop(config, args.sin_robot, args.a_mano)

    # Ejecutar grabador
    grabador = GrabadorPosturas(robot, teleop, args.a_mano)
    grabador.run()


if __name__ == "__main__":
    main()
