#!/usr/bin/env python3
"""
calibrar_zona.py - Calibra la zona de trabajo y los valores HSV del morado.

Dos modos de captura:
1. --con-marca (PREDETERMINADO): Coloca el taladro con la punta sobre cada esquina (X)
   y pulsa ESPACIO. Captura la posición media de la marca morada en ~15 fotogramas.
2. --con-clic: Click manual en las 4 esquinas de la zona en la mesa.

Después ajusta sliders HSV para detectar el objeto morado.

Uso:
    python calibrar_zona.py --real                  # Con marca (predeterminado)
    python calibrar_zona.py --real --con-clic       # Con clic manual
    python calibrar_zona.py --sin-robot             # Simulado con marca
"""

import argparse
import json
import cv2
import numpy as np
import sys


def cargar_config():
    """Carga config.json"""
    with open('config.json', 'r') as f:
        return json.load(f)


def guardar_config(config):
    """Guarda config.json"""
    with open('config.json', 'w') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def guardar_zona(esquinas):
    """Guarda zona.json con las 4 esquinas"""
    zona = {
        "esquinas_px": esquinas.tolist(),
        "orden": "delante-izq, delante-der, detrás-der, detrás-izq"
    }
    with open('zona.json', 'w') as f:
        json.dump(zona, f, indent=2)
    print(f"\n✓ Zona guardada en zona.json")


class CalibradorZona:
    """Calibrador interactivo de zona y HSV"""

    # Nombres de las esquinas
    NOMBRES_ESQUINAS = [
        "delante-izquierda",
        "delante-derecha",
        "detrás-derecha",
        "detrás-izquierda"
    ]

    def __init__(self, robot, modo_captura="marca"):
        """
        Args:
            robot: Instancia del robot
            modo_captura: "marca" (detectar marca morada) o "clic" (clic manual)
        """
        self.robot = robot
        self.modo_captura = modo_captura
        self.esquinas = []
        self.h_min, self.s_min, self.v_min = 130, 100, 50
        self.h_max, self.s_max, self.v_max = 150, 255, 255
        self.modo = "esquinas"  # "esquinas" o "hsv"

        # Para modo con marca: acumular posiciones
        self.capturando_esquina = False
        self.posiciones_acumuladas = []
        self.frames_para_promediar = 15

    def callback_raton(self, event, x, y, flags, param):
        """Callback para clics del ratón (solo modo clic)"""
        if event == cv2.EVENT_LBUTTONDOWN and self.modo == "esquinas" and self.modo_captura == "clic":
            if len(self.esquinas) < 4:
                self.esquinas.append([x, y])
                nombre = self.NOMBRES_ESQUINAS[len(self.esquinas) - 1]
                print(f"✓ Esquina {len(self.esquinas)} ({nombre}): ({x}, {y})")
                if len(self.esquinas) == 4:
                    print("\n✓ 4 esquinas capturadas. Presiona 's' para guardar o 'r' para reiniciar")

    def callback_trackbar(self, x):
        """Callback vacío para trackbars"""
        pass

    def crear_ventanas(self):
        """Crea ventanas con trackbars HSV"""
        cv2.namedWindow("Calibracion - Original")
        cv2.namedWindow("Calibracion - HSV Ajuste")

        # Callback para clics
        cv2.setMouseCallback("Calibracion - Original", self.callback_raton)

        # Trackbars para HSV
        cv2.createTrackbar("H min", "Calibracion - HSV Ajuste", self.h_min, 179, self.callback_trackbar)
        cv2.createTrackbar("S min", "Calibracion - HSV Ajuste", self.s_min, 255, self.callback_trackbar)
        cv2.createTrackbar("V min", "Calibracion - HSV Ajuste", self.v_min, 255, self.callback_trackbar)
        cv2.createTrackbar("H max", "Calibracion - HSV Ajuste", self.h_max, 179, self.callback_trackbar)
        cv2.createTrackbar("S max", "Calibracion - HSV Ajuste", self.s_max, 255, self.callback_trackbar)
        cv2.createTrackbar("V max", "Calibracion - HSV Ajuste", self.v_max, 255, self.callback_trackbar)

    def dibujar_instrucciones(self, img):
        """Dibuja instrucciones en la imagen"""
        h, w = img.shape[:2]

        if self.modo == "esquinas" and len(self.esquinas) < 4:
            # Instrucciones para definir esquinas
            if self.modo_captura == "marca":
                esquina_actual = len(self.esquinas) + 1
                nombre_esquina = self.NOMBRES_ESQUINAS[len(self.esquinas)] if len(self.esquinas) < 4 else ""

                estado_captura = ""
                if self.capturando_esquina:
                    progreso = len(self.posiciones_acumuladas)
                    estado_captura = f"Capturando... {progreso}/{self.frames_para_promediar}"

                instrucciones = [
                    f"MODO: Con marca morada ({len(self.esquinas)}/4 esquinas)",
                    "",
                    f"Esquina {esquina_actual}: {nombre_esquina.upper()}",
                    "",
                    "1. Coloca la PUNTA del taladro",
                    "   sobre la esquina marcada (X)",
                    "2. Presiona ESPACIO para capturar",
                    "",
                    estado_captura if estado_captura else "Esperando...",
                    "",
                    "Esquinas guardadas:",
                ]

                # Añadir lista de esquinas guardadas
                for i in range(len(self.esquinas)):
                    instrucciones.append(f"  {i+1}. {self.NOMBRES_ESQUINAS[i]} ✓")

                instrucciones.extend([
                    "",
                    "'r' - Reiniciar",
                    "'q' - Salir"
                ])
            else:
                # Modo clic
                instrucciones = [
                    f"MODO: Con clic manual ({len(self.esquinas)}/4 esquinas)",
                    "",
                    "Click en las 4 esquinas:",
                    "  1. Delante-Izquierda",
                    "  2. Delante-Derecha",
                    "  3. Detras-Derecha",
                    "  4. Detras-Izquierda",
                    "",
                    "'r' - Reiniciar esquinas",
                    "'q' - Salir sin guardar"
                ]
        elif len(self.esquinas) == 4:
            # Instrucciones para ajuste HSV
            instrucciones = [
                "MODO: Ajustar HSV para morado",
                "",
                "Ajusta los sliders hasta detectar",
                "solo el objeto morado",
                "",
                "'s' - Guardar y salir",
                "'r' - Reiniciar esquinas",
                "'q' - Salir sin guardar"
            ]
        else:
            instrucciones = []

        # Dibujar fondo semi-transparente
        overlay = img.copy()
        altura_fondo = 10 + len(instrucciones) * 25 + 10
        cv2.rectangle(overlay, (10, 10), (450, altura_fondo), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.7, img, 0.3, 0, img)

        # Dibujar texto
        y = 30
        for linea in instrucciones:
            cv2.putText(img, linea, (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
            y += 25

    def dibujar_esquinas(self, img):
        """Dibuja las esquinas capturadas"""
        for i, (x, y) in enumerate(self.esquinas):
            # Convertir a int para OpenCV
            x_int, y_int = int(x), int(y)

            # Círculo
            cv2.circle(img, (x_int, y_int), 8, (0, 255, 0), -1)
            # Número
            cv2.putText(img, str(i + 1), (x_int + 10, y_int - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

        # Si hay 4 esquinas, dibujar polígono
        if len(self.esquinas) == 4:
            pts = np.array(self.esquinas, dtype=np.int32)
            cv2.polylines(img, [pts], True, (0, 255, 0), 2)

    def detectar_morado(self, img):
        """Detecta morado en la imagen y devuelve máscara"""
        # Convertir RGB a HSV (img viene en RGB del robot)
        img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        img_hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)

        # Leer valores de trackbars
        self.h_min = cv2.getTrackbarPos("H min", "Calibracion - HSV Ajuste")
        self.s_min = cv2.getTrackbarPos("S min", "Calibracion - HSV Ajuste")
        self.v_min = cv2.getTrackbarPos("V min", "Calibracion - HSV Ajuste")
        self.h_max = cv2.getTrackbarPos("H max", "Calibracion - HSV Ajuste")
        self.s_max = cv2.getTrackbarPos("S max", "Calibracion - HSV Ajuste")
        self.v_max = cv2.getTrackbarPos("V max", "Calibracion - HSV Ajuste")

        # Crear máscara
        lower = np.array([self.h_min, self.s_min, self.v_min])
        upper = np.array([self.h_max, self.s_max, self.v_max])
        mascara = cv2.inRange(img_hsv, lower, upper)

        # Limpiar ruido (morfología)
        kernel = np.ones((5, 5), np.uint8)
        mascara = cv2.morphologyEx(mascara, cv2.MORPH_OPEN, kernel)
        mascara = cv2.morphologyEx(mascara, cv2.MORPH_CLOSE, kernel)

        return mascara

    def capturar_esquina_con_marca(self, img_rgb):
        """
        Captura una esquina detectando la marca morada y promediando posiciones.

        Returns:
            True si se completó la captura, False en caso contrario
        """
        # Detectar morado
        mascara = self.detectar_morado(img_rgb)

        # Encontrar contorno más grande
        contornos, _ = cv2.findContours(mascara, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contornos:
            return False

        mayor = max(contornos, key=cv2.contourArea)
        area = cv2.contourArea(mayor)

        if area < 500:  # Área mínima
            return False

        # Calcular centro
        M = cv2.moments(mayor)
        if M["m00"] == 0:
            return False

        cx = M["m10"] / M["m00"]
        cy = M["m01"] / M["m00"]

        # Acumular posición
        self.posiciones_acumuladas.append([cx, cy])

        # Si ya tenemos suficientes frames, calcular promedio
        if len(self.posiciones_acumuladas) >= self.frames_para_promediar:
            posiciones_array = np.array(self.posiciones_acumuladas)
            pos_promedio = np.mean(posiciones_array, axis=0)

            self.esquinas.append(pos_promedio.tolist())
            nombre = self.NOMBRES_ESQUINAS[len(self.esquinas) - 1]
            print(f"✓ Esquina {len(self.esquinas)} ({nombre}): ({pos_promedio[0]:.1f}, {pos_promedio[1]:.1f})")

            # Resetear captura
            self.capturando_esquina = False
            self.posiciones_acumuladas = []

            if len(self.esquinas) == 4:
                print("\n✓ 4 esquinas capturadas. Presiona 's' para guardar o 'r' para reiniciar")

            return True

        return False

    def run(self):
        """Bucle principal de calibración"""
        self.crear_ventanas()

        print("\n" + "="*60)
        print("CALIBRACIÓN DE ZONA Y HSV")
        print("="*60)

        if self.modo_captura == "marca":
            print("\nModo: CAPTURA CON MARCA MORADA")
            print("\nPASO 1: Coloca el taladro con la punta sobre cada esquina (X)")
            print("        y presiona ESPACIO para capturar")
            print("        Orden: delante-izq, delante-der, detrás-der, detrás-izq")
        else:
            print("\nModo: CAPTURA CON CLIC MANUAL")
            print("\nPASO 1: Haz click en las 4 esquinas de la zona de trabajo")
            print("        (delante-izq, delante-der, detrás-der, detrás-izq)")

        print("\nPASO 2: Ajusta los sliders HSV para detectar el objeto morado")
        print("\nPresiona 's' para guardar, 'r' para reiniciar, 'q' para salir")
        print("="*60 + "\n")

        while True:
            # Leer observación
            obs = self.robot.get_observation()
            img_rgb = obs["front"]
            img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)

            # Dibujar instrucciones y esquinas
            img_display = img_bgr.copy()
            self.dibujar_instrucciones(img_display)
            self.dibujar_esquinas(img_display)

            # Si estamos capturando con marca, procesar frame
            if self.capturando_esquina and self.modo_captura == "marca":
                self.capturar_esquina_con_marca(img_rgb)

            # Detectar morado y mostrar máscara
            mascara = self.detectar_morado(img_rgb)

            # Encontrar contornos en la máscara
            contornos, _ = cv2.findContours(mascara, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if contornos:
                # Dibujar contorno más grande
                mayor = max(contornos, key=cv2.contourArea)
                area = cv2.contourArea(mayor)
                if area > 500:
                    # Color diferente si estamos capturando
                    color = (0, 255, 0) if self.capturando_esquina else (255, 0, 255)
                    cv2.drawContours(img_display, [mayor], -1, color, 2)
                    M = cv2.moments(mayor)
                    if M["m00"] != 0:
                        cx = int(M["m10"] / M["m00"])
                        cy = int(M["m01"] / M["m00"])
                        cv2.circle(img_display, (cx, cy), 8, color, -1)
                        cv2.putText(img_display, f"Area: {int(area)}", (cx + 10, cy - 10),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

            # Mostrar ventanas
            cv2.imshow("Calibracion - Original", img_display)
            cv2.imshow("Calibracion - HSV Ajuste", mascara)

            # Esperar tecla
            tecla = cv2.waitKey(30) & 0xFF

            if tecla == ord('q') or tecla == 27:
                print("\nCalibración cancelada")
                break
            elif tecla == ord('r'):
                self.esquinas = []
                self.capturando_esquina = False
                self.posiciones_acumuladas = []
                print("\nEsquinas reiniciadas")
            elif tecla == ord(' ') and self.modo_captura == "marca":
                # ESPACIO: iniciar captura de esquina con marca
                if len(self.esquinas) < 4 and not self.capturando_esquina:
                    self.capturando_esquina = True
                    self.posiciones_acumuladas = []
                    nombre = self.NOMBRES_ESQUINAS[len(self.esquinas)]
                    print(f"\n▶ Iniciando captura de esquina {len(self.esquinas) + 1} ({nombre})...")
            elif tecla == ord('s'):
                if len(self.esquinas) == 4:
                    # Guardar zona
                    esquinas_array = np.array(self.esquinas, dtype=np.float32)
                    guardar_zona(esquinas_array)

                    # Guardar HSV en config
                    config = cargar_config()
                    config["percepcion"]["hsv_morado"]["min"] = [self.h_min, self.s_min, self.v_min]
                    config["percepcion"]["hsv_morado"]["max"] = [self.h_max, self.s_max, self.v_max]
                    guardar_config(config)
                    print(f"✓ HSV guardado en config.json")

                    print("\n" + "="*60)
                    print("✅ CALIBRACIÓN COMPLETADA")
                    print("="*60)
                    break
                else:
                    print("\n❌ Necesitas definir las 4 esquinas primero")

        cv2.destroyAllWindows()


def main():
    parser = argparse.ArgumentParser(description='Calibrar zona de trabajo y HSV')
    parser.add_argument('--sin-robot', action='store_true', help='Usar RobotFalso')
    parser.add_argument('--real', action='store_true', help='Usar robot real')
    parser.add_argument('--con-clic', action='store_true',
                       help='Usar modo clic manual (por defecto usa detección de marca)')
    args = parser.parse_args()

    if not args.sin_robot and not args.real:
        print("❌ Error: Debes especificar --sin-robot o --real")
        return

    # Determinar modo de captura
    modo_captura = "clic" if args.con_clic else "marca"

    # Cargar config y crear robot
    config = cargar_config()

    if args.sin_robot:
        from robot_falso import RobotFalso
        robot = RobotFalso(camera_index_front=config["robot"]["cameras"]["front"]["index_or_path"])
    else:
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

    # Conectar
    robot.connect(calibrate=False)

    # Ejecutar calibración
    calibrador = CalibradorZona(robot, modo_captura=modo_captura)
    calibrador.run()

    # Desconectar
    robot.disconnect()


if __name__ == "__main__":
    main()
