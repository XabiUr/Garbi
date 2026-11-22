#!/usr/bin/env python3
"""
supervisor.py - Supervisor principal del sistema.

Máquina de estados:
- REPOSO: Brazo en postura de reposo, esperando morado estable y dentro de zona
- YENDO_A_INTERMEDIA: Va a posición intermedia fija (altura segura, posición consistente)
- APROXIMANDO: Desde posición intermedia, sigue el taladro en X-Y manteniendo altura segura
- ACTUANDO: Baja gradualmente desde aproximación a posición de trabajo
- EN_OBJETIVO: Posición final de aspirado, cerca del taladro (solo modo --seguir)
- FIJO: Mantiene postura fija sin consultar cerebro (modo sin --seguir)
- LEVANTANDO: Levanta antes de volver a reposo
- VOLVIENDO: Volver a reposo suavemente
- PARADA: Parada de emergencia (ESPACIO), continuar con C

Modos:
- Sin --seguir (default): Objetivo fijo, pasa a estado FIJO cuando se estabiliza
- Con --seguir: Seguimiento continuo, reactivo a movimiento del taladro

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
    python supervisor.py --cerebro zonas --real --seguir  # Modo seguimiento
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
from typing import Optional, Tuple
import trayectoria


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
    APROXIMANDO = "APROXIMANDO"  # Reproduce trayectoria planificada (ida completa)
    EN_OBJETIVO = "EN_OBJETIVO"  # Llegó abajo, baja más y se acerca (solo modo --seguir)
    FIJO = "FIJO"  # Mantiene postura fija sin consultar cerebro (modo sin seguimiento)
    LIMPIEZA_LOCAL = "LIMPIEZA_LOCAL"  # Limpieza local si está activada
    VOLVIENDO = "VOLVIENDO"  # Reproduce trayectoria de vuelta (levanta + vuelve a reposo)
    PARADA = "PARADA"


class Supervisor:
    """Supervisor principal que orquesta todo el sistema"""

    MOTOR_NAMES = [
        "shoulder_pan", "shoulder_lift", "elbow_flex",
        "wrist_flex", "wrist_roll", "gripper"
    ]

    def __init__(self, robot, config, cerebros_dict, cerebro_inicial, modo_simulado, modo_seguir=False):
        self.robot = robot
        self.config = config
        self.modo_simulado = modo_simulado
        self.modo_seguir = modo_seguir  # True: seguimiento continuo (antiguo), False: posición fija (nuevo)

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

        # Parámetros de estabilización (modo sin seguimiento)
        self.umbral_estabilizacion = config["supervisor"].get("umbral_estabilizacion", 0.5)  # Unidades normalizadas del motor [-100, 100]
        self.tiempo_estabilizacion_s = config["supervisor"].get("tiempo_estabilizacion_s", 1.0)
        self.tiempo_max_actuando_s = config["supervisor"].get("tiempo_max_actuando_s", 7.0)  # Timeout máximo en ACTUANDO
        self.umbral_movimiento_taladro = config["supervisor"].get("umbral_movimiento_taladro", 0.05)

        # Limpieza local
        self.limpieza_local_activada = config["supervisor"].get("limpieza_local_activada", False)
        self.duracion_limpieza_s = config["supervisor"].get("duracion_limpieza_s", 2.0)
        self.tiempo_limpieza = 0.0

        # Parámetros de seguridad y posicionamiento
        self.offset_bajar_altura = config["seguridad"].get("offset_bajar_altura", 10.0)  # Bajar 50mm
        self.offset_distancia_morado = config["seguridad"].get("offset_distancia_morado", 8.0)  # Alejar del morado
        self.offset_distancia_aproximacion = config["seguridad"].get("offset_distancia_aproximacion", 8.0)  # Distancia segura durante aproximación
        self.offset_bajar_muneca = config["seguridad"].get("offset_bajar_muneca", 10.0)  # Bajar muñeca
        self.offset_aproximacion_altura = config["seguridad"].get("offset_aproximacion_altura", -30.0)  # Altura al aproximarse
        self.offset_lateral_bajada = config["seguridad"].get("offset_lateral_bajada", 3.0)  # Desplazamiento lateral durante bajada
        self.offset_acercar_bajada = config["seguridad"].get("offset_acercar_bajada", -4.0)  # Acercarse más durante bajada
        self.offset_bajar_objetivo = config["seguridad"].get("offset_bajar_objetivo", 5.0)  # Bajar más en objetivo
        self.offset_acercar_objetivo = config["seguridad"].get("offset_acercar_objetivo", -3.0)  # Acercarse más en objetivo

        # Trayectorias (nuevo sistema)
        self.uv_congelado = None  # (u, v) congelado al detectar morado estable
        self.trayectoria_actual = None  # Trayectoria en ejecución
        self.tiempo_trayectoria = 0.0  # Tiempo transcurrido en la trayectoria

        # Estado EN_OBJETIVO (modo seguimiento, solo para --seguir)
        self.tiempo_en_objetivo = 0.0
        self.duracion_en_objetivo = 1.5  # Segundos para bajar más y acercarse
        self.ultima_posicion_morado = None  # Para detectar movimiento
        self.umbral_movimiento_morado_seguir = 0.03  # Distancia en (u,v) para considerar que se movió (modo seguir)

        # Estado FIJO (modo sin seguimiento)
        self.postura_fija = None  # Postura a mantener en modo FIJO

        # Posturas
        self.posturas_data = cargar_posturas()
        self.postura_reposo = self.posturas_data["reposo"]
        if self.postura_reposo is None:
            raise ValueError("No hay postura de reposo en posturas.json")

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
            if nuevo_estado == Estado.PARADA:
                self.seguridad.activar_parada()
            elif nuevo_estado == Estado.REPOSO:
                self.tiempo_sin_morado = 0.0
                # Resetear UV congelado y trayectoria
                self.uv_congelado = None
                self.trayectoria_actual = None

    def maquina_estados(self, percepcion: dict):
        """Actualiza la máquina de estados"""
        if self.estado == Estado.PARADA:
            # En parada, solo se sale con tecla 'C'
            return

        elif self.estado == Estado.REPOSO:
            # Esperar morado estable y dentro de zona
            if percepcion["hay_taladro"] and percepcion["estable"] and percepcion["dentro_zona"]:
                # NUEVO: Congelar UV una sola vez y planificar trayectoria
                self.uv_congelado = (percepcion.get("u_estable") if percepcion.get("u_estable") is not None else percepcion["u"],
                                     percepcion.get("v_estable") if percepcion.get("v_estable") is not None else percepcion["v"])
                print(f"[Supervisor] UV congelado en ({self.uv_congelado[0]:.3f}, {self.uv_congelado[1]:.3f})")

                # Planificar trayectoria de ida
                obs_actual = self.robot.get_observation()
                cerebro_nombre = self.cerebros_nombres[self.cerebro_actual_idx]

                # Solo usar trayectorias para CerebroZonas (no para ACT)
                if cerebro_nombre == "zonas":
                    self.trayectoria_actual = trayectoria.planificar(
                        obs_actual, self.uv_congelado, self.config,
                        self.posturas_data, self.cerebro, tipo='ida'
                    )
                    print(f"[Supervisor] Trayectoria planificada: {self.trayectoria_actual.duracion:.2f}s")
                    self.tiempo_trayectoria = 0.0
                    self.transicion_estado(Estado.APROXIMANDO)
                else:
                    # Para ACT, mantener comportamiento antiguo: reset al empezar
                    self.cerebro.reset()
                    self.transicion_estado(Estado.APROXIMANDO)

        elif self.estado == Estado.APROXIMANDO:
            # Reproducir trayectoria planificada o usar cerebro (para ACT)
            self.tiempo_trayectoria += self.dt

            cerebro_nombre = self.cerebros_nombres[self.cerebro_actual_idx]

            # Detectar si el taladro desaparece
            if percepcion["hay_taladro"]:
                self.tiempo_sin_morado = 0.0
            else:
                self.tiempo_sin_morado += self.dt

            # Si se pierde el morado durante aproximación, planificar vuelta
            if self.tiempo_sin_morado >= self.timeout_sin_morado:
                print("[Supervisor] Taladro perdido durante aproximación, planificando vuelta...")
                obs_actual = self.robot.get_observation()
                self.trayectoria_actual = trayectoria.planificar(
                    obs_actual, self.uv_congelado, self.config,
                    self.posturas_data, self.cerebro, tipo='vuelta'
                )
                print(f"[Supervisor] Trayectoria de vuelta planificada: {self.trayectoria_actual.duracion:.2f}s")
                self.tiempo_trayectoria = 0.0
                self.transicion_estado(Estado.VOLVIENDO)
                return

            # Verificar fin de trayectoria (solo para zonas)
            if cerebro_nombre == "zonas" and self.trayectoria_actual:
                if self.tiempo_trayectoria >= self.trayectoria_actual.duracion:
                    # Trayectoria completada
                    if self.modo_seguir:
                        # Modo seguimiento: pasar a EN_OBJETIVO
                        self.tiempo_en_objetivo = 0.0
                        self.ultima_posicion_morado = (percepcion["u"], percepcion["v"]) if percepcion["hay_taladro"] else None
                        self.transicion_estado(Estado.EN_OBJETIVO)
                    else:
                        # Modo posición fija: pasar a FIJO con la postura final
                        self.postura_fija = self.trayectoria_actual.muestrear(self.trayectoria_actual.duracion)
                        print("[Supervisor] Trayectoria completada, pasando a FIJO")
                        self.transicion_estado(Estado.FIJO)

        elif self.estado == Estado.EN_OBJETIVO:
            # Estado final (solo en modo seguimiento): baja más y se acerca más al objetivo
            self.tiempo_en_objetivo += self.dt

            # Detectar si el morado se movió
            if percepcion["hay_taladro"]:
                self.tiempo_sin_morado = 0.0
                posicion_actual = (percepcion["u"], percepcion["v"])

                if self.ultima_posicion_morado is not None:
                    # Calcular distancia de movimiento
                    dist = np.sqrt((posicion_actual[0] - self.ultima_posicion_morado[0])**2 +
                                   (posicion_actual[1] - self.ultima_posicion_morado[1])**2)

                    # Si se movió significativamente, volver a APROXIMANDO (lento)
                    if dist > self.umbral_movimiento_morado_seguir:
                        print(f"[Supervisor] Morado se movió ({dist:.3f}), reacercándose lentamente...")
                        self.tiempo_aproximando = 0.0
                        self.transicion_estado(Estado.APROXIMANDO)
                        return

                # Actualizar última posición
                self.ultima_posicion_morado = posicion_actual
            else:
                self.tiempo_sin_morado += self.dt

            # Si se pierde el morado por más del timeout, planificar vuelta
            if self.tiempo_sin_morado >= self.timeout_sin_morado:
                print("[Supervisor] Taladro perdido en objetivo, planificando vuelta...")
                obs_actual = self.robot.get_observation()
                self.trayectoria_actual = trayectoria.planificar(
                    obs_actual, self.uv_congelado, self.config,
                    self.posturas_data, self.cerebro, tipo='vuelta'
                )
                print(f"[Supervisor] Trayectoria de vuelta planificada: {self.trayectoria_actual.duracion:.2f}s")
                self.tiempo_trayectoria = 0.0
                self.transicion_estado(Estado.VOLVIENDO)

        elif self.estado == Estado.FIJO:
            # Estado FIJO (modo sin seguimiento): mantener postura fija sin consultar cerebro
            # Monitorear si el taladro desaparece
            if percepcion["hay_taladro"]:
                self.tiempo_sin_morado = 0.0
            else:
                self.tiempo_sin_morado += self.dt

            # Si se pierde el morado por más del timeout, ir a limpieza o volver
            if self.tiempo_sin_morado >= self.timeout_sin_morado:
                if self.limpieza_local_activada:
                    # Activar limpieza local
                    print(f"[Supervisor] Taladro desaparecido, iniciando limpieza local ({self.duracion_limpieza_s}s)")
                    self.tiempo_limpieza = 0.0
                    self.transicion_estado(Estado.LIMPIEZA_LOCAL)
                else:
                    # Sin limpieza, planificar trayectoria de vuelta directamente
                    obs_actual = self.robot.get_observation()
                    self.trayectoria_actual = trayectoria.planificar(
                        obs_actual, self.uv_congelado, self.config,
                        self.posturas_data, self.cerebro, tipo='vuelta'
                    )
                    print(f"[Supervisor] Trayectoria de vuelta planificada: {self.trayectoria_actual.duracion:.2f}s")
                    self.tiempo_trayectoria = 0.0
                    self.transicion_estado(Estado.VOLVIENDO)

        elif self.estado == Estado.LIMPIEZA_LOCAL:
            # Estado de limpieza local: mantener postura fija durante limpieza
            self.tiempo_limpieza += self.dt

            # Después de completar limpieza, planificar vuelta
            if self.tiempo_limpieza >= self.duracion_limpieza_s:
                print("[Supervisor] Limpieza local completada, volviendo...")
                obs_actual = self.robot.get_observation()
                self.trayectoria_actual = trayectoria.planificar(
                    obs_actual, self.uv_congelado, self.config,
                    self.posturas_data, self.cerebro, tipo='vuelta'
                )
                print(f"[Supervisor] Trayectoria de vuelta planificada: {self.trayectoria_actual.duracion:.2f}s")
                self.tiempo_trayectoria = 0.0
                self.transicion_estado(Estado.VOLVIENDO)

        elif self.estado == Estado.VOLVIENDO:
            # Reproducir trayectoria de vuelta (continua: levanta + vuelve a reposo)
            self.tiempo_trayectoria += self.dt

            # Verificar fin de trayectoria
            if self.trayectoria_actual and self.tiempo_trayectoria >= self.trayectoria_actual.duracion:
                print("[Supervisor] Trayectoria de vuelta completada")
                self.transicion_estado(Estado.REPOSO)

    def calcular_accion(self, obs: dict, percepcion: dict) -> dict:
        """Calcula la acción según el estado"""
        if self.estado == Estado.REPOSO:
            # Ir a reposo
            return self.postura_reposo.copy()

        elif self.estado == Estado.APROXIMANDO:
            # Muestrear trayectoria o usar cerebro (para ACT en modo antiguo)
            cerebro_nombre = self.cerebros_nombres[self.cerebro_actual_idx]

            if cerebro_nombre == "zonas" and self.trayectoria_actual:
                # Usar trayectoria planificada
                return self.trayectoria_actual.muestrear(self.tiempo_trayectoria)
            else:
                # Para ACT: comportamiento antiguo (con offsets manuales)
                accion = self.cerebro.paso(obs, percepcion)

                # Usar altura de aproximación
                if "shoulder_lift.pos" in accion:
                    accion["shoulder_lift.pos"] += self.offset_aproximacion_altura

                # Mantener distancia segura (adaptativo según v)
                if "elbow_flex.pos" in accion:
                    v = percepcion.get("v", 0.5) if percepcion["hay_taladro"] else 0.5
                    if v > 0.6:  # Fila trasera
                        offset_distancia = self.offset_distancia_aproximacion * 0.4
                    else:
                        offset_distancia = self.offset_distancia_aproximacion
                    accion["elbow_flex.pos"] += offset_distancia

                # Bajar la muñeca
                if "wrist_flex.pos" in accion:
                    accion["wrist_flex.pos"] += self.offset_bajar_muneca

                return accion

        elif self.estado == Estado.VOLVIENDO:
            # Muestrear trayectoria de vuelta
            if self.trayectoria_actual:
                return self.trayectoria_actual.muestrear(self.tiempo_trayectoria)
            else:
                return self.postura_reposo.copy()

        elif self.estado == Estado.FIJO:
            # Mantener postura fija (no consultar cerebro)
            return self.postura_fija.copy() if self.postura_fija else self.postura_reposo.copy()

        elif self.estado == Estado.LIMPIEZA_LOCAL:
            # Mantener postura fija durante limpieza (en el futuro, aquí se activaría el aspirador)
            return self.postura_fija.copy() if self.postura_fija else self.postura_reposo.copy()

        elif self.estado == Estado.EN_OBJETIVO:
            # Usar cerebro activo: la postura interpolada YA es la posición final
            # absoluta (boca junto a la broca). Sin offsets adicionales.
            return self.cerebro.paso(obs, percepcion)

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

        # Dibujar objetivo congelado si existe
        if self.uv_congelado is not None:
            # Convertir UV congelado a píxeles
            u, v = self.uv_congelado
            # Usar la homografía del detector para obtener las coordenadas en píxeles
            # (u,v) ∈ [0,1] → píxeles en imagen
            if hasattr(self.detector, 'homografia'):
                # Aplicar transformación inversa
                try:
                    punto_norm = np.array([[u, v]], dtype=np.float32).reshape(-1, 1, 2)
                    punto_px = cv2.perspectiveTransform(punto_norm, np.linalg.inv(self.detector.homografia))
                    cx_obj, cy_obj = int(punto_px[0][0][0]), int(punto_px[0][0][1])

                    # Dibujar cruz amarilla para el objetivo congelado
                    tamaño_cruz = 15
                    cv2.line(img_debug, (cx_obj - tamaño_cruz, cy_obj),
                            (cx_obj + tamaño_cruz, cy_obj), (0, 255, 255), 2)
                    cv2.line(img_debug, (cx_obj, cy_obj - tamaño_cruz),
                            (cx_obj, cy_obj + tamaño_cruz), (0, 255, 255), 2)
                    cv2.circle(img_debug, (cx_obj, cy_obj), 20, (0, 255, 255), 2)
                    cv2.putText(img_debug, "OBJETIVO", (cx_obj + 25, cy_obj),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
                except:
                    pass

        # Información del sistema
        h, w = img_debug.shape[:2]
        y = h - 180

        info_lines = [
            f"Estado: {self.estado.value}",
            f"Cerebro: {self.cerebros_nombres[self.cerebro_actual_idx]}",
        ]

        # Añadir progreso de trayectoria si existe
        if self.trayectoria_actual is not None:
            progreso = self.trayectoria_actual.progreso(self.tiempo_trayectoria) * 100
            fase = self.trayectoria_actual.fase_actual(self.tiempo_trayectoria)
            info_lines.append(f"Trayectoria: {fase} - {progreso:.0f}%")
            info_lines.append(f"Tiempo: {self.tiempo_trayectoria:.1f}s / {self.trayectoria_actual.duracion:.1f}s")

        # Añadir UV congelado si existe
        if self.uv_congelado is not None:
            info_lines.append(f"UV objetivo: ({self.uv_congelado[0]:.2f}, {self.uv_congelado[1]:.2f})")

        info_lines.extend([
            f"Ciclo: {self.ciclo}",
            f"FPS: {1.0/self.dt if self.dt > 0 else 0:.1f}",
            "",
            "Teclas: ESPACIO=Parada, C=Continuar",
            "        Z=Cerebro-, A=Cerebro+, Q=Salir"
        ])

        for i, line in enumerate(info_lines):
            cv2.putText(img_debug, line, (10, y + i * 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1,
                       cv2.LINE_AA)

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
        print(f"Seguimiento: {'CONTINUO' if self.modo_seguir else 'POSICIÓN FIJA'}")
        print(f"Duración: {duracion_s if duracion_s else 'infinita'}")
        print("="*60 + "\n")

        # Conectar robot
        self.robot.connect(calibrate=False)

        # Ir a reposo lentamente al inicio
        print("\n[Supervisor] Moviendo a posición de reposo...")
        for _ in range(60):  # 2 segundos a 30Hz
            obs = self.robot.get_observation()
            if not self.modo_simulado:
                self.robot.send_action(self.postura_reposo)
            time.sleep(1.0 / 30)
        print("[Supervisor] Posición de reposo alcanzada ✓\n")

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
    parser.add_argument('--seguir', action='store_true',
                       help='Modo seguimiento continuo (default: posición fija)')
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
        modo_simulado=modo_simulado,
        modo_seguir=args.seguir
    )

    supervisor.run(duracion_s=args.duracion)


if __name__ == "__main__":
    main()
