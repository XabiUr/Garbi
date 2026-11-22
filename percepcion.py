#!/usr/bin/env python3
"""
percepcion.py - Detecta marca morada y convierte a coordenadas normalizadas (u,v).

Detecta el mayor contorno morado en la imagen "front", lo transforma a coordenadas
normalizadas (u,v) en [0,1] usando la homografía de las 4 esquinas de zona.json.

Incluye:
- Suavizado exponencial
- Memoria corta (mantiene última posición si se pierde < 1s)
- Verifica si está dentro de la zona
- Detecta estabilidad (≥0.5s en la misma posición)
"""

import json
import cv2
import numpy as np
import time
from collections import deque
from typing import Optional, Tuple, Dict


def cargar_config():
    """Carga config.json"""
    with open('config.json', 'r') as f:
        return json.load(f)


def cargar_zona():
    """Carga zona.json con las 4 esquinas"""
    try:
        with open('zona.json', 'r') as f:
            zona = json.load(f)
        esquinas = np.array(zona["esquinas_px"], dtype=np.float32)
        if esquinas.shape != (4, 2):
            raise ValueError("zona.json debe tener 4 esquinas")
        return esquinas
    except FileNotFoundError:
        raise FileNotFoundError(
            "No se encontró zona.json. Ejecuta primero:\n"
            "  python calibrar_zona.py --sin-robot"
        )


class DetectorMorado:
    """
    Detecta marca morada y la convierte a coordenadas normalizadas (u,v).

    Coordenadas (u,v):
    - u=0, v=0: esquina delante-izquierda
    - u=1, v=0: esquina delante-derecha
    - u=1, v=1: esquina detrás-derecha
    - u=0, v=1: esquina detrás-izquierda
    """

    def __init__(self, config):
        self.config = config
        cfg_percepcion = config["percepcion"]

        # Parámetros HSV
        self.hsv_min = np.array(cfg_percepcion["hsv_morado"]["min"])
        self.hsv_max = np.array(cfg_percepcion["hsv_morado"]["max"])

        # Parámetros de área
        self.area_minima = cfg_percepcion["area_minima_px"]
        self.area_maxima = cfg_percepcion["area_maxima_px"]

        # Suavizado exponencial
        self.alpha = cfg_percepcion["suavizado_alpha"]

        # Memoria y estabilidad
        self.timeout_perdida = cfg_percepcion["timeout_perdida_s"]
        self.tiempo_estable_min = cfg_percepcion["tiempo_estable_s"]
        # Distancia máxima en (u,v) de cada detección BRUTA respecto a la mediana
        # de la ventana para considerar el taladro quieto
        self.umbral_movimiento = cfg_percepcion.get("umbral_estable", 0.015)
        # Ventana de detecciones brutas (sin suavizar): [(t, u, v), ...]
        self.ventana_bruta = deque()

        # Margen de zona (aceptar u,v fuera de [0,1])
        self.margen_zona = cfg_percepcion.get("margen_zona", 0.15)

        # Estado interno
        self.ultima_pos_px = None  # Última posición en píxeles
        self.ultima_uv = None  # Última posición en (u,v)
        self.ultima_deteccion_t = None  # Timestamp de última detección
        self.tiempo_estable_inicio = None  # Timestamp cuando empezó a estar estable
        self.posicion_estable_inicio = None  # Posición (u,v) cuando empezó el período estable

        # Homografía
        self.esquinas_px = None
        self.matriz_homografia = None

    def configurar_zona(self, esquinas_px: np.ndarray):
        """
        Configura la zona de trabajo y calcula la homografía.

        Args:
            esquinas_px: Array (4,2) con las esquinas en píxeles
                        [delante-izq, delante-der, detrás-der, detrás-izq]
        """
        self.esquinas_px = esquinas_px

        # Puntos destino en espacio normalizado [0,1]
        # Orden: delante-izq (0,0), delante-der (1,0), detrás-der (1,1), detrás-izq (0,1)
        puntos_destino = np.array([
            [0.0, 0.0],  # delante-izq
            [1.0, 0.0],  # delante-der
            [1.0, 1.0],  # detrás-der
            [0.0, 1.0],  # detrás-izq
        ], dtype=np.float32)

        # Calcular homografía: píxeles -> (u,v)
        self.matriz_homografia = cv2.getPerspectiveTransform(esquinas_px, puntos_destino)

        print("[Percepcion] Homografía configurada ✓")

    def detectar(self, img_rgb: np.ndarray) -> Dict:
        """
        Detecta marca morada en la imagen y devuelve información.

        Args:
            img_rgb: Imagen en RGB (H, W, 3)

        Returns:
            Dict con:
            - "hay_taladro": bool, si se detectó el objeto morado
            - "estable": bool, si lleva ≥0.5s detectado
            - "u": float en [0,1] o None
            - "v": float en [0,1] o None
            - "dentro_zona": bool, si está dentro del rectángulo [0,1]²
            - "centro_px": tuple (x, y) en píxeles o None
            - "area": int, área del contorno en píxeles o 0
        """
        if self.matriz_homografia is None:
            raise RuntimeError("Debes llamar a configurar_zona() primero")

        # Convertir a HSV
        img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
        img_hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)

        # Crear máscara
        mascara = cv2.inRange(img_hsv, self.hsv_min, self.hsv_max)

        # Limpiar ruido
        kernel = np.ones((5, 5), np.uint8)
        mascara = cv2.morphologyEx(mascara, cv2.MORPH_OPEN, kernel)
        mascara = cv2.morphologyEx(mascara, cv2.MORPH_CLOSE, kernel)

        # Encontrar contornos
        contornos, _ = cv2.findContours(mascara, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Buscar contorno más grande que cumpla área
        contorno_valido = None
        area_max = 0

        for cnt in contornos:
            area = cv2.contourArea(cnt)
            if self.area_minima <= area <= self.area_maxima and area > area_max:
                contorno_valido = cnt
                area_max = area

        # Procesar detección
        ahora = time.time()

        if contorno_valido is not None:
            # Calcular centro
            M = cv2.moments(contorno_valido)
            if M["m00"] != 0:
                cx = M["m10"] / M["m00"]
                cy = M["m01"] / M["m00"]

                # (u,v) BRUTO (sin suavizar) para estabilidad y congelado
                punto_bruto = np.array([[cx, cy]], dtype=np.float32).reshape(-1, 1, 2)
                uv_bruto = cv2.perspectiveTransform(punto_bruto, self.matriz_homografia)
                u_bruto, v_bruto = float(uv_bruto[0][0][0]), float(uv_bruto[0][0][1])

                # Suavizado exponencial
                if self.ultima_pos_px is not None:
                    cx = self.alpha * cx + (1 - self.alpha) * self.ultima_pos_px[0]
                    cy = self.alpha * cy + (1 - self.alpha) * self.ultima_pos_px[1]

                self.ultima_pos_px = (cx, cy)

                # Transformar a (u,v) con homografía
                punto_px = np.array([[cx, cy]], dtype=np.float32).reshape(-1, 1, 2)
                punto_uv = cv2.perspectiveTransform(punto_px, self.matriz_homografia)
                u, v = float(punto_uv[0][0][0]), float(punto_uv[0][0][1])

                # Suavizar (u,v)
                if self.ultima_uv is not None:
                    u = self.alpha * u + (1 - self.alpha) * self.ultima_uv[0]
                    v = self.alpha * v + (1 - self.alpha) * self.ultima_uv[1]

                self.ultima_uv = (u, v)
                self.ultima_deteccion_t = ahora

                # Verificar si está dentro de zona con margen
                # Por defecto acepta u,v entre -0.15 y 1.15
                min_zona = -self.margen_zona
                max_zona = 1.0 + self.margen_zona
                dentro_zona = (min_zona <= u <= max_zona) and (min_zona <= v <= max_zona)

                # Estabilidad con detecciones BRUTAS: el taladro está quieto si
                # durante tiempo_estable_s todas las detecciones quedan a menos
                # de umbral_estable de la mediana de la ventana.
                self.ventana_bruta.append((ahora, u_bruto, v_bruto))
                while self.ventana_bruta and ahora - self.ventana_bruta[0][0] > self.tiempo_estable_min:
                    self.ventana_bruta.popleft()

                pts = np.array([(p[1], p[2]) for p in self.ventana_bruta])
                mediana = np.median(pts, axis=0)
                dist_max = float(np.max(np.linalg.norm(pts - mediana, axis=1)))

                if dist_max > self.umbral_movimiento:
                    # Se está moviendo: reiniciar ventana con la detección actual
                    self.ventana_bruta.clear()
                    self.ventana_bruta.append((ahora, u_bruto, v_bruto))
                    self.tiempo_estable_inicio = ahora
                    estable = False
                else:
                    if self.tiempo_estable_inicio is None:
                        self.tiempo_estable_inicio = ahora
                    estable = (ahora - self.tiempo_estable_inicio) >= self.tiempo_estable_min

                # Posición para congelar: mediana bruta (sin retraso del suavizado)
                u_estable, v_estable = (float(mediana[0]), float(mediana[1])) if estable else (None, None)

                return {
                    "hay_taladro": True,
                    "estable": estable,
                    "u": u,
                    "v": v,
                    "u_estable": u_estable,
                    "v_estable": v_estable,
                    "dentro_zona": dentro_zona,
                    "centro_px": (int(cx), int(cy)),
                    "area": int(area_max),
                    "contorno": contorno_valido,
                    "mascara": mascara
                }

        # No hay detección válida
        # Mantener última posición si no ha pasado el timeout
        if self.ultima_deteccion_t is not None:
            tiempo_sin_deteccion = ahora - self.ultima_deteccion_t
            if tiempo_sin_deteccion < self.timeout_perdida:
                # Memoria corta: mantener última posición conocida
                return {
                    "hay_taladro": True,  # Mantener True por memoria
                    "estable": False,  # No estable si no se ve
                    "u": self.ultima_uv[0] if self.ultima_uv else None,
                    "v": self.ultima_uv[1] if self.ultima_uv else None,
                    "dentro_zona": True,  # Asumimos que sigue dentro
                    "centro_px": (int(self.ultima_pos_px[0]), int(self.ultima_pos_px[1])) if self.ultima_pos_px else None,
                    "area": 0,
                    "contorno": None,
                    "mascara": mascara,
                    "memoria": True  # Flag para indicar que es memoria
                }

        # Timeout pasado: resetear todo
        self.ultima_pos_px = None
        self.ultima_uv = None
        self.ultima_deteccion_t = None
        self.tiempo_estable_inicio = None
        self.posicion_estable_inicio = None
        self.ventana_bruta.clear()

        return {
            "hay_taladro": False,
            "estable": False,
            "u": None,
            "v": None,
            "dentro_zona": False,
            "centro_px": None,
            "area": 0,
            "contorno": None,
            "mascara": mascara
        }

    def dibujar_debug(self, img_bgr: np.ndarray, resultado: Dict) -> np.ndarray:
        """
        Dibuja información de debug en la imagen.

        Args:
            img_bgr: Imagen en BGR
            resultado: Dict devuelto por detectar()

        Returns:
            Imagen con overlays dibujados
        """
        img_debug = img_bgr.copy()

        # Dibujar zona (4 esquinas)
        if self.esquinas_px is not None:
            pts = self.esquinas_px.astype(np.int32)
            cv2.polylines(img_debug, [pts], True, (0, 255, 0), 2)

            # Números en esquinas
            for i, (x, y) in enumerate(pts):
                cv2.circle(img_debug, (int(x), int(y)), 6, (0, 255, 0), -1)
                cv2.putText(img_debug, str(i+1), (int(x)+10, int(y)-10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        # Dibujar contorno detectado
        if resultado["contorno"] is not None:
            cv2.drawContours(img_debug, [resultado["contorno"]], -1, (255, 0, 255), 2)

        # Dibujar centro
        if resultado["centro_px"] is not None:
            cx, cy = resultado["centro_px"]
            cv2.circle(img_debug, (cx, cy), 8, (255, 0, 255), -1)
            cv2.circle(img_debug, (cx, cy), 12, (255, 255, 255), 2)

        # Texto con información
        y = 30
        textos = [
            f"Hay taladro: {'SI' if resultado['hay_taladro'] else 'NO'}",
            f"Estable: {'SI' if resultado['estable'] else 'NO'}",
        ]

        if resultado["u"] is not None and resultado["v"] is not None:
            textos.append(f"u={resultado['u']:.3f}, v={resultado['v']:.3f}")
            textos.append(f"Dentro zona: {'SI' if resultado['dentro_zona'] else 'NO'}")
            textos.append(f"Area: {resultado['area']} px")

        if resultado.get("memoria"):
            textos.append("(MEMORIA)")

        for texto in textos:
            cv2.putText(img_debug, texto, (10, y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
            y += 25

        return img_debug


# Script de prueba
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Test de detección de morado')
    parser.add_argument('--sin-robot', action='store_true', help='Usar RobotFalso')
    parser.add_argument('--real', action='store_true', help='Usar robot real')
    args = parser.parse_args()

    if not args.sin_robot and not args.real:
        print("❌ Debes especificar --sin-robot o --real")
        exit(1)

    # Cargar config
    config = cargar_config()

    # Crear robot
    if args.sin_robot:
        from robot_falso import RobotFalso
        robot = RobotFalso(camera_index_front=config["robot"]["cameras"]["front"]["index_or_path"])
    else:
        from lerobot.robots.so_follower import SO100Follower, SO100FollowerConfig
        from lerobot.cameras.opencv import OpenCVCameraConfig
        robot_config = SO100FollowerConfig(
            robot_id=config["robot"]["id"],
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
            }
        )
        robot = SO100Follower(robot_config)

    robot.connect(calibrate=False)

    # Cargar zona y crear detector
    esquinas = cargar_zona()
    detector = DetectorMorado(config)
    detector.configurar_zona(esquinas)

    print("\n" + "="*60)
    print("TEST DE DETECCIÓN DE MORADO")
    print("="*60)
    print("\nPresiona 'q' o ESC para salir")
    print("="*60 + "\n")

    while True:
        # Leer observación
        obs = robot.get_observation()
        img_rgb = obs["front"]

        # Detectar
        resultado = detector.detectar(img_rgb)

        # Dibujar debug
        img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
        img_debug = detector.dibujar_debug(img_bgr, resultado)

        # Mostrar ventanas
        cv2.imshow("Percepcion - Deteccion", img_debug)
        if resultado["mascara"] is not None:
            cv2.imshow("Percepcion - Mascara", resultado["mascara"])

        # Tecla
        tecla = cv2.waitKey(30) & 0xFF
        if tecla == ord('q') or tecla == 27:
            break

    robot.disconnect()
    cv2.destroyAllWindows()
    print("\n✓ Test completado")
