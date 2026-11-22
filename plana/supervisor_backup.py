#!/usr/bin/env python3
"""
supervisor.py - Supervisor principal del sistema.

Máquina de estados:
- REPOSO: Brazo en postura de reposo, esperando morado estable y dentro de zona
- ACTUANDO: Cerebro activo, siguiendo el objetivo
- VOLVIENDO: Volver a reposo suavemente
- PARADA: Parada de emergencia (ESPACIO), continuar con C

Bucle a 30 Hz con:
- Percepción (detectar morado)
- Cerebro (calcular acción)
- Seguridad (verificar y limitar acción)
- Envío al robot
- Log CSV por ciclo

Teclas:
- ESPACIO: Activar PARADA
- C: Continuar desde PARADA
- Z: Cambiar a cerebro anterior
- A: Cambiar a cerebro siguiente
- Q: Salir (vuelve a reposo primero)

Uso:
    python supervisor.py --cerebro zonas --sin-robot
    python supervisor.py --cerebro zonas --real
    python supervisor.py --cerebro act --modelo <path> --real
    python supervisor.py --cerebro zonas --real --duracion 60  # 60 segundos
"""

import argparse
import json
import cv2
import numpy as np
import time
import csv
from enum import Enum
from typing import Optional


def cargar_config():
    """Carga config.json"""
    with open('config.json', 'r') as f:
        return json.load(f)


def cargar_zona():
    """Carga zona.json"""
    try:
        with open('zona.json', 'r') as f:
            zona = json.load(f)
        return np.array(zona["esquinas_px"], dtype=np.float32)
    except FileNotFoundError:
        raise FileNotFoundError(
            "No se encontró zona.json. Ejecuta primero:\n"
            "  python calibrar_zona.py --sin-robot"
        )


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


class Estado(Enum):
    """Estados de la máquina de estados"""
    REPOSO = "REPOSO"
    APROXIMANDO = "APROXIMANDO"  # Nuevo: se acerca con altura segura
    ACTUANDO = "ACTUANDO"
    LEVANTANDO = "LEVANTANDO"  # Levanta antes de volver
    VOLVIENDO = "VOLVIENDO"
    PARADA = "PARADA"


class Supervisor:
    """Supervisor principal que orquesta todo el sistema"""

    MOTOR_NAMES = [
        "shoulder_pan", "shoulder_lift", "elbow_flex",
        "wrist_flex", "wrist_roll", "gripper"
    ]

    def __init__(self, robot, config, cerebros_dict, cerebro_inicial, modo_simulado):
        self.robot = robot
        self.config = config
        self.modo_simulado = modo_simulado

        # Componentes
        from percepcion import DetectorMorado
        from seguridad import SistemaSeguridad

        self.detector = DetectorMorado(config)
        self.detector.configurar_zona(cargar_zona())

        self.seguridad = SistemaSeguridad(config)
        self.seguridad.configurar_limites(cargar_posturas())

        # Cerebros
        self.cerebros = cerebros_dict
        self.cerebros_nombres = list(cerebros_dict.keys())
        self.cerebro_actual_idx = self.cerebros_nombres.index(cerebro_inicial)
        self.cerebro = self.cerebros[self.cerebros_nombres[self.cerebro_actual_idx]]

        # Máquina de estados
        self.estado = Estado.REPOSO
        self.tiempo_sin_morado = 0.0
        self.ultimo_tick = time.time()

        # Parámetros
        self.fps = config["supervisor"]["fps"]
        self.dt = 1.0 / self.fps
        self.timeout_sin_morado = config["supervisor"]["timeout_sin_morado_s"]

        # Parámetros de seguridad y posicionamiento
        self.offset_bajar_altura = config["seguridad"].get("offset_bajar_altura", 10.0)  # Bajar 50mm
        self.offset_distancia_morado = config["seguridad"].get("offset_distancia_morado", 8.0)  # Alejar del morado
        self.offset_bajar_muneca = config["seguridad"].get("offset_bajar_muneca", 10.0)  # Bajar muñeca
        self.offset_aproximacion_altura = config["seguridad"].get("offset_aproximacion_altura", -30.0)  # Altura al aproximarse
        self.offset_lateral_bajada = config["seguridad"].get("offset_lateral_bajada", 3.0)  # Desplazamiento lateral durante bajada
        self.offset_acercar_bajada = config["seguridad"].get("offset_acercar_bajada", -4.0)  # Acercarse más durante bajada

        # Estado de aproximación
        self.tiempo_aproximando = 0.0
        self.duracion_aproximacion = 3.0  # Segundos en estado APROXIMANDO antes de bajar (más lento)

        # Transición gradual al bajar
        self.tiempo_en_actuando = 0.0
        self.duracion_bajada = 2.0  # Segundos para bajar gradualmente de aproximación a trabajo

        # Postura de reposo
        posturas_data = cargar_posturas()
        self.postura_reposo = posturas_data["reposo"]
        if self.postura_reposo is None:
            raise ValueError("No hay postura de reposo en posturas.json")

        # Postura levantada (para estado LEVANTANDO)
        self.postura_levantada = None
        self.tiempo_levantando = 0.0

        # Logging
        self.log_file = None
        self.log_writer = None

        # Métricas
        self.ciclo = 0
        self.tiempo_inicio = None

        print("[Supervisor] Inicializado")
        print(f"  Estado inicial: {self.estado.value}")
        print(f"  Cerebro inicial: {self.cerebros_nombres[self.cerebro_actual_idx]}")
        print(f"  FPS objetivo: {self.fps}")

    def iniciar_log(self):
        """Inicia el archivo de log CSV"""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        cerebro_nombre = self.cerebros_nombres[self.cerebro_actual_idx]
        filename = f"log_supervisor_{cerebro_nombre}_{timestamp}.csv"

        self.log_file = open(filename, 'w', newline='')
        self.log_writer = csv.writer(self.log_file)

        # Header
        header = [
            "ciclo", "tiempo_s", "estado", "cerebro",
            "hay_taladro", "estable", "u", "v", "dentro_zona",
            "fps_real"
        ]
        # Añadir columnas de articulaciones (obs y action)
        for motor in self.MOTOR_NAMES:
            header.append(f"obs_{motor}")
        for motor in self.MOTOR_NAMES:
            header.append(f"action_{motor}")

        self.log_writer.writerow(header)
        print(f"[Supervisor] Log iniciado: {filename}")

    def cerrar_log(self):
        """Cierra el archivo de log"""
        if self.log_file is not None:
            self.log_file.close()
            print("[Supervisor] Log cerrado")

    def cambiar_cerebro(self, direccion: int):
        """
        Cambia de cerebro.

        Args:
            direccion: +1 para siguiente, -1 para anterior
        """
        # Ir a reposo primero
        if self.estado != Estado.REPOSO:
            print("[Supervisor] Volviendo a reposo antes de cambiar cerebro...")
            self.estado = Estado.VOLVIENDO

        # Cambiar índice
        self.cerebro_actual_idx = (self.cerebro_actual_idx + direccion) % len(self.cerebros_nombres)
        nuevo_nombre = self.cerebros_nombres[self.cerebro_actual_idx]
        self.cerebro = self.cerebros[nuevo_nombre]
        self.cerebro.reset()
        self.seguridad.reset()

        print(f"[Supervisor] Cerebro cambiado a: {nuevo_nombre}")

    def transicion_estado(self, nuevo_estado: Estado):
        """Cambia de estado"""
        if nuevo_estado != self.estado:
            print(f"[Supervisor] {self.estado.value} → {nuevo_estado.value}")
            self.estado = nuevo_estado

            # Acciones al entrar en un estado
            if nuevo_estado == Estado.ACTUANDO:
                self.cerebro.reset()
                self.seguridad.reset()
            elif nuevo_estado == Estado.PARADA:
                self.seguridad.activar_parada()
            elif nuevo_estado == Estado.REPOSO:
                self.tiempo_sin_morado = 0.0

    def maquina_estados(self, percepcion: dict):
        """Actualiza la máquina de estados"""
        if self.estado == Estado.PARADA:
            # En parada, solo se sale con tecla 'C'
            return

        elif self.estado == Estado.REPOSO:
            # Esperar morado estable y dentro de zona
            if percepcion["hay_taladro"] and percepcion["estable"] and percepcion["dentro_zona"]:
                self.tiempo_aproximando = 0.0
                self.transicion_estado(Estado.APROXIMANDO)

        elif self.estado == Estado.APROXIMANDO:
            # Aproximarse con altura segura
            self.tiempo_aproximando += self.dt

            # Después de la duración de aproximación, bajar a posición de trabajo
            if self.tiempo_aproximando >= self.duracion_aproximacion:
                self.tiempo_en_actuando = 0.0  # Resetear contador para bajada gradual
                self.transicion_estado(Estado.ACTUANDO)

            # Si se pierde el morado durante aproximación, volver a reposo
            if not percepcion["hay_taladro"]:
                self.transicion_estado(Estado.LEVANTANDO)

        elif self.estado == Estado.ACTUANDO:
            # Incrementar tiempo en actuando (para bajada gradual)
            self.tiempo_en_actuando += self.dt

            # Seguir actuando mientras hay morado
            if percepcion["hay_taladro"]:
                self.tiempo_sin_morado = 0.0
            else:
                self.tiempo_sin_morado += self.dt

            # Si se pierde el morado por más del timeout, primero levantar
            if self.tiempo_sin_morado >= self.timeout_sin_morado:
                # Guardar posición actual y crear postura levantada
                obs_actual = self.robot.get_observation()
                self.postura_levantada = {}
                for motor in self.MOTOR_NAMES:
                    key = f"{motor}.pos"
                    self.postura_levantada[key] = obs_actual.get(key, 0.0)

                # Levantar shoulder_lift (valores negativos = arriba en SO-101)
                self.postura_levantada["shoulder_lift.pos"] -= 15.0  # Levanta 15 unidades

                self.tiempo_levantando = 0.0
                self.transicion_estado(Estado.LEVANTANDO)

        elif self.estado == Estado.LEVANTANDO:
            # Levantar el brazo antes de volver a reposo
            self.tiempo_levantando += self.dt

            # Después de 1 segundo levantando, ir a reposo
            if self.tiempo_levantando >= 1.0:
                self.transicion_estado(Estado.VOLVIENDO)

        elif self.estado == Estado.VOLVIENDO:
            # Incrementar tiempo sin morado (para que la transición a REPOSO funcione)
            self.tiempo_sin_morado += self.dt

            # Interpolar hacia reposo
            # (La interpolación se hace en el paso de acción)
            # Cuando llegamos, cambiar a REPOSO
            # Por simplicidad, después de 2 segundos consideramos que llegamos
            if self.tiempo_sin_morado >= self.timeout_sin_morado + 3.0:  # +3s (1s levantando + 2s volviendo)
                self.transicion_estado(Estado.REPOSO)

    def calcular_accion(self, obs: dict, percepcion: dict) -> dict:
        """Calcula la acción según el estado"""
        if self.estado == Estado.REPOSO or self.estado == Estado.VOLVIENDO:
            # Ir a reposo
            return self.postura_reposo.copy()

        elif self.estado == Estado.LEVANTANDO:
            # Ir a postura levantada
            return self.postura_levantada.copy() if self.postura_levantada else self.postura_reposo.copy()

        elif self.estado == Estado.APROXIMANDO:
            # Aproximarse con altura segura (más alto)
            accion = self.cerebro.paso(obs, percepcion)

            # Usar altura de aproximación (más alto que posición final)
            if "shoulder_lift.pos" in accion:
                accion["shoulder_lift.pos"] += self.offset_aproximacion_altura

            # Mantener distancia del morado
            if "elbow_flex.pos" in accion:
                accion["elbow_flex.pos"] += self.offset_distancia_morado

            # Bajar la muñeca
            if "wrist_flex.pos" in accion:
                accion["wrist_flex.pos"] += self.offset_bajar_muneca

            return accion

        elif self.estado == Estado.ACTUANDO:
            # Usar cerebro activo
            accion = self.cerebro.paso(obs, percepcion)

            # Aplicar ajustes de seguridad y posicionamiento

            # Interpolación gradual durante los primeros segundos de bajada
            if self.tiempo_en_actuando < self.duracion_bajada:
                # Factor de interpolación (0.0 al inicio, 1.0 al final)
                t = self.tiempo_en_actuando / self.duracion_bajada

                # Interpolación lineal entre altura de aproximación y altura final
                offset_altura_actual = (1.0 - t) * self.offset_aproximacion_altura + t * self.offset_bajar_altura

                # Durante la bajada: añadir desplazamiento lateral (a la izquierda)
                offset_lateral_actual = t * self.offset_lateral_bajada

                # Durante la bajada: acercarse gradualmente más al morado
                offset_distancia_actual = self.offset_distancia_morado + (t * self.offset_acercar_bajada)
            else:
                # Ya ha pasado el tiempo de bajada, usar valores finales
                offset_altura_actual = self.offset_bajar_altura
                offset_lateral_actual = self.offset_lateral_bajada
                offset_distancia_actual = self.offset_distancia_morado + self.offset_acercar_bajada

            # 1. Aplicar altura (con bajada gradual)
            if "shoulder_lift.pos" in accion:
                accion["shoulder_lift.pos"] += offset_altura_actual

            # 2. Desplazamiento lateral (a la izquierda durante bajada)
            if "shoulder_pan.pos" in accion:
                accion["shoulder_pan.pos"] += offset_lateral_actual

            # 3. Mantener distancia del morado (con acercamiento gradual durante bajada)
            if "elbow_flex.pos" in accion:
                accion["elbow_flex.pos"] += offset_distancia_actual

            # 4. Bajar la muñeca unos grados (wrist_flex hacia abajo)
            # Valores positivos = doblar hacia abajo
            if "wrist_flex.pos" in accion:
                accion["wrist_flex.pos"] += self.offset_bajar_muneca

            return accion

        elif self.estado == Estado.PARADA:
            # Mantener posición actual
            accion = {}
            for motor in self.MOTOR_NAMES:
                key = f"{motor}.pos"
                accion[key] = obs.get(key, 0.0)
            return accion

        else:
            # Fallback: mantener posición
            accion = {}
            for motor in self.MOTOR_NAMES:
                key = f"{motor}.pos"
                accion[key] = obs.get(key, 0.0)
            return accion

    def dibujar_visualizacion(self, obs: dict, percepcion: dict) -> np.ndarray:
        """Dibuja la visualización principal"""
        # Imagen principal (front)
        img_bgr = cv2.cvtColor(obs["front"], cv2.COLOR_RGB2BGR)

        # Dibujar zona y detección
        img_debug = self.detector.dibujar_debug(img_bgr, percepcion)

        # Información del sistema
        h, w = img_debug.shape[:2]
        y = h - 150

        info_lines = [
            f"Estado: {self.estado.value}",
            f"Cerebro: {self.cerebros_nombres[self.cerebro_actual_idx]}",
            f"Ciclo: {self.ciclo}",
            f"FPS: {1.0/self.dt if self.dt > 0 else 0:.1f}",
            "",
            "Teclas: ESPACIO=Parada, C=Continuar",
            "        Z=Cerebro-, A=Cerebro+, Q=Salir"
        ]

        for i, line in enumerate(info_lines):
            cv2.putText(img_debug, line, (10, y + i * 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1,
                       cv2.LINE_AA)

        # Miniatura de gripper
        if "gripper" in obs:
            gripper_img = cv2.cvtColor(obs["gripper"], cv2.COLOR_RGB2BGR)
            # Redimensionar a 160x120
            gripper_small = cv2.resize(gripper_img, (160, 120))
            # Poner en esquina inferior derecha
            x_offset = w - 170
            y_offset = h - 130
            img_debug[y_offset:y_offset+120, x_offset:x_offset+160] = gripper_small

            # Borde
            cv2.rectangle(img_debug, (x_offset, y_offset),
                         (x_offset+160, y_offset+120), (0, 255, 255), 2)
            cv2.putText(img_debug, "Gripper", (x_offset, y_offset-5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)

        return img_debug

    def escribir_log(self, obs: dict, percepcion: dict, accion: dict, fps_real: float):
        """Escribe una línea en el log CSV"""
        if self.log_writer is None:
            return

        tiempo_desde_inicio = time.time() - self.tiempo_inicio

        row = [
            self.ciclo,
            f"{tiempo_desde_inicio:.3f}",
            self.estado.value,
            self.cerebros_nombres[self.cerebro_actual_idx],
            int(percepcion["hay_taladro"]),
            int(percepcion["estable"]),
            f"{percepcion['u']:.4f}" if percepcion["u"] is not None else "",
            f"{percepcion['v']:.4f}" if percepcion["v"] is not None else "",
            int(percepcion["dentro_zona"]),
            f"{fps_real:.2f}"
        ]

        # Observación (articulaciones)
        for motor in self.MOTOR_NAMES:
            key = f"{motor}.pos"
            row.append(f"{obs.get(key, 0.0):.4f}")

        # Acción
        for motor in self.MOTOR_NAMES:
            key = f"{motor}.pos"
            row.append(f"{accion.get(key, 0.0):.4f}")

        self.log_writer.writerow(row)

    def run(self, duracion_s: Optional[float] = None):
        """
        Bucle principal del supervisor.

        Args:
            duracion_s: Duración en segundos (None = infinito)
        """
        print("\n" + "="*60)
        print("SUPERVISOR INICIADO")
        print("="*60)
        print(f"Modo: {'SIMULADO' if self.modo_simulado else 'REAL'}")
        print(f"Duración: {duracion_s if duracion_s else 'infinita'}")
        print("="*60 + "\n")

        # Conectar robot
        self.robot.connect(calibrate=False)

        # Iniciar log
        self.iniciar_log()

        self.tiempo_inicio = time.time()
        self.ultimo_tick = self.tiempo_inicio

        try:
            while True:
                tick_inicio = time.time()

                # Verificar duración
                if duracion_s is not None:
                    if (tick_inicio - self.tiempo_inicio) >= duracion_s:
                        print("\n[Supervisor] Duración completada, finalizando...")
                        break

                # 1. Leer observación
                obs = self.robot.get_observation()

                # 2. Percepción
                percepcion = self.detector.detectar(obs["front"])

                # 3. Máquina de estados
                self.maquina_estados(percepcion)

                # 4. Calcular acción
                accion_objetivo = self.calcular_accion(obs, percepcion)

                # 5. Seguridad
                accion_segura, valida = self.seguridad.verificar_accion(accion_objetivo, obs)

                # 6. Enviar al robot (solo si no es simulado)
                if not self.modo_simulado:
                    self.robot.send_action(accion_segura)

                # 7. Visualización
                img_viz = self.dibujar_visualizacion(obs, percepcion)
                cv2.imshow("Supervisor", img_viz)

                # 8. Logging
                tick_fin = time.time()
                fps_real = 1.0 / (tick_fin - self.ultimo_tick) if (tick_fin - self.ultimo_tick) > 0 else 0
                self.escribir_log(obs, percepcion, accion_segura, fps_real)

                # 9. Manejar teclas
                tecla = cv2.waitKey(1) & 0xFF

                if tecla == ord(' '):  # ESPACIO
                    if self.estado != Estado.PARADA:
                        self.transicion_estado(Estado.PARADA)
                    else:
                        print("[Supervisor] Ya en PARADA")

                elif tecla == ord('c') or tecla == ord('C'):  # C
                    if self.estado == Estado.PARADA:
                        self.seguridad.desactivar_parada()
                        self.transicion_estado(Estado.REPOSO)

                elif tecla == ord('z') or tecla == ord('Z'):  # Z (cerebro anterior)
                    self.cambiar_cerebro(-1)

                elif tecla == ord('a') or tecla == ord('A'):  # A (cerebro siguiente)
                    self.cambiar_cerebro(+1)

                elif tecla == ord('q') or tecla == ord('Q'):  # Q (salir)
                    print("\n[Supervisor] Saliendo...")
                    # Volver a reposo antes de salir
                    if self.estado != Estado.REPOSO:
                        print("[Supervisor] Volviendo a reposo...")
                        self.transicion_estado(Estado.VOLVIENDO)
                        for _ in range(60):  # 2 segundos a 30Hz
                            obs = self.robot.get_observation()
                            if not self.modo_simulado:
                                self.robot.send_action(self.postura_reposo)
                            time.sleep(1.0 / 30)
                    break

                # 10. Control de frecuencia
                self.ciclo += 1
                tick_duracion = time.time() - tick_inicio
                sleep_time = self.dt - tick_duracion

                if sleep_time > 0:
                    time.sleep(sleep_time)
                elif tick_duracion > self.dt * 1.5:
                    print(f"⚠️  [Supervisor] Ciclo lento: {tick_duracion*1000:.1f}ms (objetivo: {self.dt*1000:.1f}ms)")

                self.ultimo_tick = tick_inicio

        except KeyboardInterrupt:
            print("\n\n[Supervisor] Interrumpido por usuario")

        finally:
            # Cerrar
            self.cerrar_log()
            self.robot.disconnect()
            cv2.destroyAllWindows()

            print("\n" + "="*60)
            print("SUPERVISOR FINALIZADO")
            print("="*60)
            print(f"Ciclos totales: {self.ciclo}")
            print(f"Tiempo total: {time.time() - self.tiempo_inicio:.1f}s")
            print("="*60)


def main():
    parser = argparse.ArgumentParser(description='Supervisor del sistema')
    parser.add_argument('--sin-robot', action='store_true', help='Modo simulado')
    parser.add_argument('--real', action='store_true', help='Robot real')
    parser.add_argument('--cerebro', type=str, default='zonas',
                       choices=['zonas', 'act'], help='Cerebro a usar')
    parser.add_argument('--modelo', type=str, default=None,
                       help='Path a modelo ACT (requerido si --cerebro act)')
    parser.add_argument('--duracion', type=float, default=None,
                       help='Duración en segundos (None = infinito)')
    args = parser.parse_args()

    if not args.sin_robot and not args.real:
        print("❌ Debes especificar --sin-robot o --real")
        return

    if args.cerebro == 'act' and args.modelo is None:
        print("❌ Debes especificar --modelo cuando usas --cerebro act")
        return

    # Cargar config
    config = cargar_config()

    # Crear robot
    if args.sin_robot:
        from robot_falso import RobotFalso
        robot = RobotFalso(camera_index_front=config["robot"]["cameras"]["front"]["index_or_path"])
        modo_simulado = True
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
        modo_simulado = False

    # Crear cerebros
    from cerebros import CerebroZonas, CerebroACT

    cerebros = {}

    # Siempre crear CerebroZonas
    cerebros["zonas"] = CerebroZonas(config)

    # Crear CerebroACT si se especificó
    if args.cerebro == 'act':
        cerebros["act"] = CerebroACT(args.modelo, device="mps")

    # Crear y ejecutar supervisor
    supervisor = Supervisor(
        robot=robot,
        config=config,
        cerebros_dict=cerebros,
        cerebro_inicial=args.cerebro,
        modo_simulado=modo_simulado
    )

    supervisor.run(duracion_s=args.duracion)


if __name__ == "__main__":
    main()
