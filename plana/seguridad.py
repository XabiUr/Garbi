#!/usr/bin/env python3
"""
seguridad.py - Sistema de seguridad para el robot.

Aplica límites de articulaciones, paso máximo por ciclo y parada de emergencia.
Los límites se calculan desde las posturas grabadas + margen configurable.
"""

import json
import numpy as np
from typing import Dict, Optional, Tuple


def cargar_config():
    """Carga config.json"""
    with open('config.json', 'r') as f:
        return json.load(f)


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


class SistemaSeguridad:
    """
    Sistema de seguridad que verifica y limita acciones del robot.

    Funcionalidades:
    - Límites por articulación (min/max desde posturas grabadas)
    - Paso máximo por ciclo (evita movimientos bruscos)
    - Parada de emergencia (congela todas las articulaciones)
    - Verificación de acción válida antes de enviar al robot
    """

    MOTOR_NAMES = [
        "shoulder_pan", "shoulder_lift", "elbow_flex",
        "wrist_flex", "wrist_roll", "gripper"
    ]

    def __init__(self, config: Optional[Dict] = None):
        """
        Args:
            config: Configuración (si None, carga de config.json)
        """
        if config is None:
            config = cargar_config()

        self.config = config
        cfg_seg = config["seguridad"]

        # Parámetros
        self.margen_limites = cfg_seg["margen_limites"]
        self.paso_maximo = cfg_seg["paso_maximo_por_ciclo"]

        # Estado
        self.parada_activa = False
        self.ultima_accion = None

        # Límites por articulación
        self.limites = {}  # {motor: (min, max)}

        print("[Seguridad] Inicializado")

    def configurar_limites(self, posturas_data: Optional[Dict] = None,
                          dataset_stats: Optional[Dict] = None):
        """
        Calcula los límites de cada articulación desde las posturas grabadas.

        Args:
            posturas_data: Dict de posturas.json (si None, carga automáticamente)
            dataset_stats: Dict con stats de un dataset LeRobot (opcional, amplía límites)
        """
        if posturas_data is None:
            posturas_data = cargar_posturas()

        # Recolectar todos los valores de cada articulación
        valores_por_motor = {motor: [] for motor in self.MOTOR_NAMES}

        # Añadir posturas de la cuadrícula (1-9)
        for key, postura in posturas_data["posturas"].items():
            for motor_key, valor in postura.items():
                motor = motor_key.replace(".pos", "")
                if motor in valores_por_motor:
                    valores_por_motor[motor].append(valor)

        # Añadir reposo
        if posturas_data["reposo"] is not None:
            for motor_key, valor in posturas_data["reposo"].items():
                motor = motor_key.replace(".pos", "")
                if motor in valores_por_motor:
                    valores_por_motor[motor].append(valor)

        # Añadir límites de dataset si se proporcionan
        if dataset_stats is not None and "action" in dataset_stats:
            for motor in self.MOTOR_NAMES:
                key = f"{motor}.pos"
                if key in dataset_stats["action"]:
                    stats = dataset_stats["action"][key]
                    if "min" in stats:
                        valores_por_motor[motor].append(float(stats["min"]))
                    if "max" in stats:
                        valores_por_motor[motor].append(float(stats["max"]))

        # Calcular límites con margen
        for motor, valores in valores_por_motor.items():
            if len(valores) == 0:
                # Sin datos, usar límites muy amplios
                print(f"⚠️  [Seguridad] Sin datos para {motor}, usando límites amplios")
                self.limites[motor] = (-100.0, 100.0)
            else:
                min_val = min(valores)
                max_val = max(valores)
                rango = max_val - min_val
                margen = rango * self.margen_limites

                # Límites finales
                lim_min = min_val - margen
                lim_max = max_val + margen

                # Clipping absoluto para seguridad (normalizado [-100, 100])
                if motor == "gripper":
                    lim_min = max(0.0, lim_min)
                    lim_max = min(100.0, lim_max)
                else:
                    lim_min = max(-100.0, lim_min)
                    lim_max = min(100.0, lim_max)

                self.limites[motor] = (lim_min, lim_max)

        print("[Seguridad] Límites configurados:")
        for motor, (lim_min, lim_max) in self.limites.items():
            print(f"  {motor:<15} [{lim_min:>7.2f}, {lim_max:>7.2f}]")

    def activar_parada(self):
        """Activa la parada de emergencia (congela todo)"""
        self.parada_activa = True
        print("🛑 [Seguridad] PARADA ACTIVADA")

    def desactivar_parada(self):
        """Desactiva la parada de emergencia"""
        self.parada_activa = False
        print("▶️  [Seguridad] Parada desactivada, continuando")

    def verificar_accion(self, accion: Dict, posicion_actual: Dict) -> Tuple[Dict, bool]:
        """
        Verifica y limita una acción antes de enviarla al robot.

        Args:
            accion: Dict con {motor.pos: valor}
            posicion_actual: Dict con {motor.pos: valor} de la observación actual

        Returns:
            (accion_segura, valida):
            - accion_segura: Acción limitada (puede diferir de la original)
            - valida: True si la acción es completamente válida
        """
        if not self.limites:
            raise RuntimeError(
                "Límites no configurados. Llama a configurar_limites() primero."
            )

        # Si hay parada activa, devolver posición actual (congelar)
        if self.parada_activa:
            return posicion_actual.copy(), False

        accion_segura = {}
        totalmente_valida = True

        for motor in self.MOTOR_NAMES:
            key = f"{motor}.pos"

            # Valor objetivo de la acción
            if key in accion:
                valor_objetivo = float(accion[key])
            else:
                # Si no está en la acción, mantener posición actual
                valor_objetivo = float(posicion_actual.get(key, 0.0))

            # Límites de este motor
            lim_min, lim_max = self.limites[motor]

            # 1. Verificar límites de articulación
            valor_limitado = np.clip(valor_objetivo, lim_min, lim_max)
            if valor_limitado != valor_objetivo:
                totalmente_valida = False
                print(f"⚠️  [Seguridad] {motor}: {valor_objetivo:.2f} → {valor_limitado:.2f} (límite de articulación)")

            # 2. Verificar paso máximo (si hay acción previa)
            if self.ultima_accion is not None and key in self.ultima_accion:
                valor_previo = self.ultima_accion[key]
                delta = valor_limitado - valor_previo

                if abs(delta) > self.paso_maximo:
                    # Limitar el paso
                    if delta > 0:
                        valor_limitado = valor_previo + self.paso_maximo
                    else:
                        valor_limitado = valor_previo - self.paso_maximo
                    totalmente_valida = False
                    print(f"⚠️  [Seguridad] {motor}: paso de {abs(delta):.2f}° limitado a {self.paso_maximo}°")

            accion_segura[key] = float(valor_limitado)

        # Guardar como última acción
        self.ultima_accion = accion_segura.copy()

        return accion_segura, totalmente_valida

    def reset(self):
        """Resetea el estado interno (útil al cambiar de cerebro)"""
        self.ultima_accion = None
        self.parada_activa = False
        print("[Seguridad] Estado reseteado")


# Script de test
if __name__ == "__main__":
    print("="*60)
    print("TEST DE SEGURIDAD")
    print("="*60)

    # Cargar config y posturas
    config = cargar_config()
    posturas = cargar_posturas()

    # Crear sistema de seguridad
    seguridad = SistemaSeguridad(config)
    seguridad.configurar_limites(posturas)

    print("\n" + "="*60)
    print("TEST 1: Acción válida")
    print("="*60)

    posicion_actual = {
        "shoulder_pan.pos": 0.0,
        "shoulder_lift.pos": -20.0,
        "elbow_flex.pos": 30.0,
        "wrist_flex.pos": 10.0,
        "wrist_roll.pos": 0.0,
        "gripper.pos": 50.0
    }

    accion = {
        "shoulder_pan.pos": 5.0,
        "shoulder_lift.pos": -18.0,
        "elbow_flex.pos": 32.0,
        "wrist_flex.pos": 12.0,
        "wrist_roll.pos": 2.0,
        "gripper.pos": 55.0
    }

    accion_segura, valida = seguridad.verificar_accion(accion, posicion_actual)
    print(f"Válida: {valida}")
    print(f"Acción segura: {accion_segura}")

    print("\n" + "="*60)
    print("TEST 2: Acción con paso muy grande")
    print("="*60)

    accion_grande = {
        "shoulder_pan.pos": 50.0,  # Paso de 50 desde 5.0
        "shoulder_lift.pos": -18.0,
        "elbow_flex.pos": 32.0,
        "wrist_flex.pos": 12.0,
        "wrist_roll.pos": 2.0,
        "gripper.pos": 55.0
    }

    accion_segura, valida = seguridad.verificar_accion(accion_grande, posicion_actual)
    print(f"Válida: {valida}")
    print(f"shoulder_pan limitado a: {accion_segura['shoulder_pan.pos']:.2f}")

    print("\n" + "="*60)
    print("TEST 3: Parada de emergencia")
    print("="*60)

    seguridad.activar_parada()
    accion_segura, valida = seguridad.verificar_accion(accion, posicion_actual)
    print(f"Válida: {valida} (debería ser False)")
    print(f"Acción (congelada): {accion_segura == posicion_actual}")

    print("\n✓ Tests completados")
