#!/usr/bin/env python3
"""
afinar_mirada.py - Calibración de wrist_flex para que cámara gripper apunte a broca.

Para cada fila (v=0, 0.5, 1):
1. Coloca el taladro en esa fila
2. El brazo va al punto de despertar calculado
3. Ajusta wrist_flex con ↑/↓ (paso pequeño) hasta que broca esté en la cruz
4. Ajusta shoulder_pan con ←/→ (opcional, ajuste fino)
5. Presiona G para guardar en mirada.json
6. Presiona N para pasar a la siguiente fila

Teclas:
- ↑/↓: Ajustar wrist_flex (±0.5°)
- ←/→: Ajustar shoulder_pan (±0.2°)
- G: Guardar valores actuales para esta fila
- N: Siguiente fila
- Q: Salir

Uso:
    python afinar_mirada.py --real
"""

import argparse
import json
import cv2
import numpy as np
import time
from datetime import datetime


def cargar_config():
    """Carga config.json"""
    with open('config.json', 'r') as f:
        return json.load(f)


def cargar_posturas():
    """Carga posturas.json"""
    with open('posturas.json', 'r') as f:
        return json.load(f)


def cargar_mirada():
    """Carga mirada.json"""
    try:
        with open('mirada.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError("No se encontró mirada.json")


def guardar_mirada(mirada_data):
    """Guarda mirada.json"""
    # Actualizar metadata
    mirada_data["metadata"]["fecha_calibracion"] = datetime.now().isoformat()

    with open('mirada.json', 'w') as f:
        json.dump(mirada_data, f, indent=2)
    print("✓ mirada.json guardado")


def calcular_punto_despertar_simple(config, posturas, u=0.5, v=0.5, wrist_flex=90.0, shoulder_pan_ajuste=0.0):
    """
    Calcula el punto de despertar para calibración.

    Args:
        config: Configuración del sistema
        posturas: Dict de posturas.json
        u, v: Coordenadas del objetivo (default centro)
        wrist_flex: Valor de wrist_flex a usar
        shoulder_pan_ajuste: Ajuste fino de shoulder_pan

    Returns:
        Dict con postura del punto de despertar
    """
    # Partir de posición intermedia
    punto_despertar = config["supervisor"]["posicion_intermedia"].copy()

    # Calcular postura final para obtener shoulder_pan del objetivo
    # (esto requiere cerebro, pero aquí simplificamos usando valor intermedio para calibración)
    # En la versión real, calcularíamos con interpolar_postura(cerebro, u, v)
    # Por ahora, usar valor fijo razonable para calibración
    # punto_despertar["shoulder_pan.pos"] = valor_de_postura_final

    # Para calibración, simplemente aplicar el ajuste al valor actual
    punto_despertar["shoulder_pan.pos"] += shoulder_pan_ajuste

    # Aplicar wrist_flex de mirada
    punto_despertar["wrist_flex.pos"] = wrist_flex

    return punto_despertar


class AfinadorMirada:
    """Interfaz para calibrar mirada de cámara gripper"""

    FILAS = [
        {"v": 0.0, "nombre": "Frontal (v=0.0)", "key": "v_0.0"},
        {"v": 0.5, "nombre": "Media (v=0.5)", "key": "v_0.5"},
        {"v": 1.0, "nombre": "Trasera (v=1.0)", "key": "v_1.0"}
    ]

    PASO_WRIST = 0.5  # Grados por pulsación
    PASO_PAN = 0.2    # Grados por pulsación

    def __init__(self, robot, config, posturas, mirada):
        self.robot = robot
        self.config = config
        self.posturas = posturas
        self.mirada = mirada

        self.fila_actual = 0
        self.wrist_flex_actual = None
        self.shoulder_pan_ajuste = 0.0
        self.guardado = [False, False, False]  # Estado de guardado por fila

        print("[AfinadorMirada] Inicializado")
        print("  Filas a calibrar: 3 (v=0.0, v=0.5, v=1.0)")

    def cargar_valores_fila(self):
        """Carga los valores guardados para la fila actual"""
        fila = self.FILAS[self.fila_actual]
        key = fila["key"]

        if key in self.mirada["valores"]:
            self.wrist_flex_actual = self.mirada["valores"][key]["wrist_flex"]
            self.shoulder_pan_ajuste = self.mirada["valores"][key].get("shoulder_pan_ajuste", 0.0)
        else:
            self.wrist_flex_actual = 90.0  # Default
            self.shoulder_pan_ajuste = 0.0

    def ir_a_punto_despertar(self):
        """Mueve el robot al punto de despertar de la fila actual"""
        fila = self.FILAS[self.fila_actual]
        v = fila["v"]

        print(f"\n[AfinadorMirada] Moviendo a punto de despertar (fila {fila['nombre']})...")

        # Calcular punto de despertar
        punto_despertar = calcular_punto_despertar_simple(
            self.config, self.posturas,
            u=0.5, v=v,  # Centro horizontal
            wrist_flex=self.wrist_flex_actual,
            shoulder_pan_ajuste=self.shoulder_pan_ajuste
        )

        # Mover gradualmente (2 segundos)
        obs_inicial = self.robot.get_observation()
        fps = 30
        duracion = 2.0
        n_pasos = int(fps * duracion)

        for i in range(n_pasos):
            t = (i + 1) / n_pasos

            # Interpolar linealmente
            accion = {}
            for key in punto_despertar:
                val_inicial = obs_inicial.get(key, 0.0)
                val_final = punto_despertar[key]
                accion[key] = val_inicial + t * (val_final - val_inicial)

            self.robot.send_action(accion)
            time.sleep(1.0 / fps)

        print("✓ Punto de despertar alcanzado")
        print(f"  wrist_flex: {self.wrist_flex_actual:.1f}°")
        print(f"  shoulder_pan ajuste: {self.shoulder_pan_ajuste:+.1f}°")

    def ajustar_wrist_flex(self, delta):
        """Ajusta wrist_flex y actualiza robot"""
        self.wrist_flex_actual += delta

        # Aplicar límites básicos
        self.wrist_flex_actual = np.clip(self.wrist_flex_actual, -100.0, 100.0)

        # Actualizar robot
        obs = self.robot.get_observation()
        accion = {k: v for k, v in obs.items() if k.endswith(".pos")}
        accion["wrist_flex.pos"] = self.wrist_flex_actual

        self.robot.send_action(accion)

        print(f"wrist_flex: {self.wrist_flex_actual:.1f}° ({delta:+.1f}°)")

    def ajustar_shoulder_pan(self, delta):
        """Ajusta shoulder_pan y actualiza robot"""
        self.shoulder_pan_ajuste += delta

        # Actualizar robot
        obs = self.robot.get_observation()
        accion = {k: v for k, v in obs.items() if k.endswith(".pos")}
        accion["shoulder_pan.pos"] = obs["shoulder_pan.pos"] + delta

        self.robot.send_action(accion)

        print(f"shoulder_pan ajuste: {self.shoulder_pan_ajuste:+.1f}° ({delta:+.1f}°)")

    def guardar_valores(self):
        """Guarda los valores actuales en mirada.json"""
        fila = self.FILAS[self.fila_actual]
        key = fila["key"]

        self.mirada["valores"][key] = {
            "wrist_flex": float(self.wrist_flex_actual),
            "shoulder_pan_ajuste": float(self.shoulder_pan_ajuste),
            "descripcion": fila["nombre"]
        }

        guardar_mirada(self.mirada)
        self.guardado[self.fila_actual] = True

        print(f"✓ Valores guardados para {fila['nombre']}")

    def siguiente_fila(self):
        """Avanza a la siguiente fila"""
        if self.fila_actual < len(self.FILAS) - 1:
            self.fila_actual += 1
            self.cargar_valores_fila()
            self.ir_a_punto_despertar()
        else:
            print("\n✓ Todas las filas calibradas")
            if all(self.guardado):
                print("  Todos los valores guardados ✓")
            else:
                print("  ⚠️ Algunas filas no fueron guardadas:")
                for i, fila in enumerate(self.FILAS):
                    if not self.guardado[i]:
                        print(f"    - {fila['nombre']}")

    def dibujar_interfaz(self, img_gripper):
        """Dibuja interfaz con cruz y controles"""
        h, w = img_gripper.shape[:2]
        cx, cy = w // 2, h // 2

        # Dibujar cruz central
        longitud = 40
        cv2.line(img_gripper, (cx - longitud, cy), (cx + longitud, cy), (0, 255, 255), 2)
        cv2.line(img_gripper, (cx, cy - longitud), (cx, cy + longitud), (0, 255, 255), 2)
        cv2.circle(img_gripper, (cx, cy), 20, (0, 255, 255), 2)

        # Información de la fila
        fila = self.FILAS[self.fila_actual]
        y = 30
        cv2.putText(img_gripper, f"Fila: {fila['nombre']}", (10, y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

        y += 35
        cv2.putText(img_gripper, f"wrist_flex: {self.wrist_flex_actual:.1f}", (10, y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

        y += 30
        cv2.putText(img_gripper, f"pan_ajuste: {self.shoulder_pan_ajuste:+.1f}", (10, y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

        # Estado de guardado
        y += 35
        estado = "GUARDADO" if self.guardado[self.fila_actual] else "Sin guardar"
        color = (0, 255, 0) if self.guardado[self.fila_actual] else (0, 0, 255)
        cv2.putText(img_gripper, estado, (10, y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        # Controles
        y = h - 150
        controles = [
            "Controles:",
            "UP/DOWN: wrist_flex +-0.5",
            "LEFT/RIGHT: shoulder_pan +-0.2",
            "G: Guardar",
            "N: Siguiente fila",
            "Q: Salir"
        ]

        for i, texto in enumerate(controles):
            cv2.putText(img_gripper, texto, (10, y + i * 25),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        return img_gripper

    def run(self):
        """Bucle principal"""
        print("\n" + "="*60)
        print("CALIBRACIÓN DE MIRADA")
        print("="*60)
        print("\nInstrucciones:")
        print("1. Coloca el taladro en la fila indicada (frontal/media/trasera)")
        print("2. El brazo se moverá al punto de despertar")
        print("3. Ajusta wrist_flex (↑/↓) hasta que la broca esté en la cruz")
        print("4. Ajusta shoulder_pan (←/→) si es necesario")
        print("5. Presiona G para guardar")
        print("6. Presiona N para la siguiente fila")
        print("="*60 + "\n")

        # Conectar
        self.robot.connect(calibrate=False)

        # Cargar valores de la primera fila
        self.cargar_valores_fila()

        # Ir al primer punto de despertar
        input(f"Coloca el taladro en {self.FILAS[0]['nombre']} y presiona Enter...")
        self.ir_a_punto_despertar()

        # Bucle principal
        try:
            while True:
                # Leer observación
                obs = self.robot.get_observation()

                # Obtener imagen gripper
                if "gripper" not in obs:
                    print("⚠️ No hay cámara gripper")
                    time.sleep(0.1)
                    continue

                img_gripper = cv2.cvtColor(obs["gripper"], cv2.COLOR_RGB2BGR)

                # Dibujar interfaz
                img_viz = self.dibujar_interfaz(img_gripper)

                # Mostrar
                cv2.imshow("Afinar Mirada - Gripper", img_viz)

                # Manejar teclas
                tecla = cv2.waitKey(100) & 0xFF

                if tecla == 82:  # Flecha arriba
                    self.ajustar_wrist_flex(self.PASO_WRIST)

                elif tecla == 84:  # Flecha abajo
                    self.ajustar_wrist_flex(-self.PASO_WRIST)

                elif tecla == 81:  # Flecha izquierda
                    self.ajustar_shoulder_pan(-self.PASO_PAN)

                elif tecla == 83:  # Flecha derecha
                    self.ajustar_shoulder_pan(self.PASO_PAN)

                elif tecla == ord('g') or tecla == ord('G'):
                    self.guardar_valores()

                elif tecla == ord('n') or tecla == ord('N'):
                    if self.fila_actual < len(self.FILAS) - 1:
                        input(f"\nColoca el taladro en {self.FILAS[self.fila_actual + 1]['nombre']} y presiona Enter...")
                    self.siguiente_fila()

                elif tecla == ord('q') or tecla == ord('Q'):
                    print("\n[AfinadorMirada] Saliendo...")
                    if not all(self.guardado):
                        print("⚠️ Advertencia: No todas las filas fueron guardadas")
                    break

        except KeyboardInterrupt:
            print("\n\n[AfinadorMirada] Interrumpido por usuario")

        finally:
            self.robot.disconnect()
            cv2.destroyAllWindows()

            print("\n" + "="*60)
            print("CALIBRACIÓN FINALIZADA")
            print("="*60)
            print("Estado:")
            for i, fila in enumerate(self.FILAS):
                estado = "✓" if self.guardado[i] else "✗"
                print(f"  {estado} {fila['nombre']}")
            print("="*60)


def main():
    parser = argparse.ArgumentParser(description='Calibrar mirada de cámara gripper')
    parser.add_argument('--real', action='store_true', help='Robot real (REQUERIDO)')
    args = parser.parse_args()

    if not args.real:
        print("❌ Este script requiere --real (control del robot)")
        print("   Uso: python afinar_mirada.py --real")
        return

    # Cargar configuración
    config = cargar_config()
    posturas = cargar_posturas()
    mirada = cargar_mirada()

    # Crear robot
    from lerobot.robots.so_follower import SO101Follower, SO101FollowerConfig
    from lerobot.cameras.opencv import OpenCVCameraConfig

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

    # Crear y ejecutar afinador
    afinador = AfinadorMirada(robot, config, posturas, mirada)
    afinador.run()


if __name__ == "__main__":
    main()
