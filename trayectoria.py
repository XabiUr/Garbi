#!/usr/bin/env python3
"""
trayectoria.py - Planificador de trayectorias continuas con punto de despertar dinámico.

Genera trayectorias suaves en el espacio de articulaciones con:
- Punto de despertar dinámico (base mira al objetivo, cámara apunta a broca)
- Trayectoria única continua: reposo → despertar → pre-aproximación → final
- Sin detenerse en puntos intermedios (velocidad no nula)
- Interpolación de wrist_flex durante aproximación (cámara sigue broca)
- Perfil ease-in/ease-out global
- Todas las articulaciones sincronizadas

Uso:
    traj = planificar(obs_actual, uv_congelado, config, posturas, cerebro, tipo='ida')
    accion = traj.muestrear(t)  # t ∈ [0, duración]
"""

import json
import numpy as np
from typing import Dict, List, Tuple, Optional
from scipy.interpolate import CubicSpline, PchipInterpolator


MOTOR_NAMES = [
    "shoulder_pan", "shoulder_lift", "elbow_flex",
    "wrist_flex", "wrist_roll", "gripper"
]

# Límite superior de wrist_flex para la mirada: seguridad.py recorta wrist_flex
# al rango de posturas.json + 5% (~58.6). Por encima se recortaría igualmente.
WRIST_FLEX_MAX_MIRADA = 58.0


def cargar_mirada():
    """Carga mirada.json"""
    try:
        with open('mirada.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print("⚠️ No se encontró mirada.json, usando valores por defecto")
        return {
            "valores": {
                "v_0.0": {"wrist_flex": 90.0},
                "v_0.5": {"wrist_flex": 90.0},
                "v_1.0": {"wrist_flex": 90.0}
            }
        }


def interpolar_mirada(v: float, mirada_data: Dict) -> float:
    """
    Interpola el valor de wrist_flex según v desde mirada.json.

    Args:
        v: Coordenada v normalizada [0, 1]
        mirada_data: Dict de mirada.json

    Returns:
        Valor de wrist_flex interpolado
    """
    valores = mirada_data["valores"]

    # Puntos de calibración
    v_puntos = [0.0, 0.5, 1.0]
    wrist_puntos = [
        valores["v_0.0"]["wrist_flex"],
        valores["v_0.5"]["wrist_flex"],
        valores["v_1.0"]["wrist_flex"]
    ]

    # Interpolar linealmente
    wrist_flex = np.interp(v, v_puntos, wrist_puntos)

    return float(wrist_flex)


class Trayectoria:
    """
    Trayectoria continua sincronizada en el espacio de articulaciones.

    Atributos:
        puntos: Lista de posturas (waypoints) en el espacio de articulaciones
        duracion: Duración total de la trayectoria (segundos)
        splines: Dict de splines cúbicas por articulación
        motor_names: Lista de nombres de motores
        fases: Lista con nombre y tiempo de inicio de cada fase
    """

    def __init__(self, puntos: List[Dict[str, float]], duracion: float,
                 motor_names: List[str] = MOTOR_NAMES,
                 fases: Optional[List[Tuple[str, float]]] = None,
                 interpolacion: str = "cubica"):
        """
        Args:
            puntos: Lista de posturas [{motor.pos: valor}] que forman los waypoints
            duracion: Duración total de la trayectoria en segundos
            motor_names: Lista de nombres de motores a interpolar
            fases: Lista de tuplas (nombre_fase, tiempo_inicio)
        """
        self.puntos = puntos
        self.duracion = duracion
        self.motor_names = motor_names
        self.fases = fases or [("Movimiento", 0.0)]
        # "cubica": spline cúbica natural (muy suave, puede sobrepasar waypoints)
        # "pchip": monótona por tramos; si un motor no cambia entre dos waypoints,
        #          se queda QUIETO en ese tramo (permite "primero subir, luego recoger")
        self.interpolacion = interpolacion

        # Crear splines cúbicas por motor
        self.splines = self._crear_splines()

    def _crear_splines(self) -> Dict[str, CubicSpline]:
        """
        Crea splines cúbicas para cada articulación.

        Returns:
            Dict {motor: CubicSpline}
        """
        n_puntos = len(self.puntos)

        # Tiempos de los waypoints PROPORCIONALES al recorrido de cada tramo
        # (motor que más se mueve). Así un tramo de 90 unidades no tarda lo mismo
        # que uno de 5, y el pico de velocidad es menor para la misma duración.
        # Cada tramo tiene al menos un 5% del total para evitar nudos pegados.
        X = np.array([[p.get(f"{m}.pos", 0.0) for m in self.motor_names] for p in self.puntos])
        seg = np.abs(np.diff(X, axis=0)).max(axis=1) if n_puntos > 1 else np.array([])
        total = seg.sum()
        if total <= 1e-9:
            tiempos = np.linspace(0, self.duracion, n_puntos)
        else:
            seg = np.maximum(seg, 0.05 * total)
            tiempos = np.concatenate([[0.0], np.cumsum(seg)])
            tiempos = tiempos / tiempos[-1] * self.duracion
        self.tiempos_waypoints = tiempos

        splines = {}
        for motor in self.motor_names:
            key = f"{motor}.pos"

            # Extraer valores de este motor en cada waypoint
            valores = [punto.get(key, 0.0) for punto in self.puntos]

            # Crear spline cúbica con condiciones de frontera "natural"
            # (derivadas cero en extremos para arranque/llegada suaves)
            if self.interpolacion == "pchip":
                spline = PchipInterpolator(tiempos, valores)
            else:
                spline = CubicSpline(tiempos, valores, bc_type='natural')
            splines[motor] = spline

        return splines

    def muestrear(self, t: float, aplicar_ease: bool = True) -> Dict[str, float]:
        """
        Muestrea la trayectoria en el instante t.

        Args:
            t: Tiempo en segundos [0, duracion]
            aplicar_ease: Si True, aplica perfil ease-in/ease-out sobre el tiempo

        Returns:
            Acción {motor.pos: valor}
        """
        # Clipping por seguridad
        t = np.clip(t, 0.0, self.duracion)

        # Aplicar perfil de velocidad suave (ease-in-out)
        if aplicar_ease:
            t_norm = t / self.duracion  # Normalizar a [0, 1]
            # Función ease-in-out suave (coseno): 0.5 * (1 - cos(π * t))
            t_ease = 0.5 * (1.0 - np.cos(np.pi * t_norm))
            t = t_ease * self.duracion

        # Muestrear cada spline
        accion = {}
        for motor, spline in self.splines.items():
            key = f"{motor}.pos"
            valor = float(spline(t))
            accion[key] = valor

        return accion

    def progreso(self, t: float) -> float:
        """
        Retorna el progreso normalizado [0, 1] en el instante t.

        Args:
            t: Tiempo en segundos

        Returns:
            Progreso en [0, 1]
        """
        return np.clip(t / self.duracion, 0.0, 1.0)

    def fase_actual(self, t: float) -> str:
        """
        Retorna el nombre de la fase actual en el instante t.

        Args:
            t: Tiempo en segundos

        Returns:
            Nombre de la fase
        """
        for i in range(len(self.fases) - 1, -1, -1):
            if t >= self.fases[i][1]:
                return self.fases[i][0]
        return self.fases[0][0] if self.fases else "Desconocido"


def interpolar_postura(cerebro, u: float, v: float) -> Dict[str, float]:
    """
    Calcula la postura interpolada para una posición (u,v) usando CerebroZonas.

    Args:
        cerebro: Instancia de CerebroZonas
        u, v: Coordenadas normalizadas [0, 1]

    Returns:
        Postura {motor.pos: valor}
    """
    # Usar interpolación bilineal del CerebroZonas
    postura_array = cerebro.interpolacion_bilineal(u, v)

    # Convertir a dict
    postura = {}
    for i, motor in enumerate(MOTOR_NAMES):
        key = f"{motor}.pos"
        postura[key] = float(postura_array[i])

    return postura


def aplicar_offsets(postura: Dict[str, float], offsets: Dict[str, float]) -> Dict[str, float]:
    """
    Aplica offsets a una postura.

    Args:
        postura: Postura base {motor.pos: valor}
        offsets: Dict de offsets {motor: delta} (sin el .pos)

    Returns:
        Nueva postura con offsets aplicados
    """
    postura_nueva = postura.copy()

    for motor, delta in offsets.items():
        key = f"{motor}.pos"
        if key in postura_nueva:
            postura_nueva[key] += delta

    return postura_nueva


def calcular_punto_despertar(obs_actual: Dict, uv_congelado: Tuple[float, float],
                             config: Dict, posturas: Dict, cerebro,
                             mirada_data: Dict) -> Dict[str, float]:
    """
    Calcula el punto de despertar dinámico.

    El punto de despertar es una posición segura desde donde iniciar la aproximación:
    - Parte de la posición intermedia (alta y recogida sobre el robot)
    - shoulder_pan = el de la postura final (base mira al taladro)
    - wrist_flex = valor interpolado desde mirada.json (cámara apunta a broca)
    - Resto: valores de la posición intermedia

    Args:
        obs_actual: Observación actual del robot
        uv_congelado: Tupla (u, v) congelada
        config: Configuración del sistema
        posturas: Dict de posturas.json
        cerebro: Instancia de CerebroZonas
        mirada_data: Dict de mirada.json

    Returns:
        Postura del punto de despertar {motor.pos: valor}
    """
    u, v = uv_congelado

    # 1. Partir de posición intermedia (referencia)
    punto_despertar = config["supervisor"]["posicion_intermedia"].copy()

    # 2. Calcular postura final para obtener el shoulder_pan que mira al objetivo
    postura_final = interpolar_postura(cerebro, u, v)

    # Aplicar shoulder_pan de la postura final (base mira al taladro)
    punto_despertar["shoulder_pan.pos"] = postura_final["shoulder_pan.pos"]

    # 3. Aplicar wrist_flex interpolado desde mirada.json (cámara apunta a broca)
    wrist_flex_mirada = interpolar_mirada(v, mirada_data)
    punto_despertar["wrist_flex.pos"] = wrist_flex_mirada

    return punto_despertar


def calcular_offsets_adaptativos(v: float, config: Dict) -> Dict[str, float]:
    """
    Calcula offsets adaptativos según la fila (v) del taladro.

    Args:
        v: Coordenada v normalizada [0, 1]
        config: Configuración del sistema

    Returns:
        Dict de offsets {motor: delta}
    """
    cfg_tray = config["trayectorias"]

    # Regla adaptativa: fila trasera (v > 0.6) usa 40% del offset
    if v > 0.6:  # Fila trasera (zonas 13-17)
        offset_distancia = cfg_tray["distancia_inicio_aproximacion"] * 0.4
    else:
        offset_distancia = cfg_tray["distancia_inicio_aproximacion"]

    return {
        "elbow_flex": offset_distancia
    }


def planificar_ida(obs_actual: Dict, uv_congelado: Tuple[float, float],
                   config: Dict, posturas: Dict, cerebro) -> Trayectoria:
    """
    Planifica la trayectoria de ida con punto de despertar dinámico.

    Trayectoria: reposo → despertar → pre-aproximación → final

    Args:
        obs_actual: Observación actual del robot
        uv_congelado: Tupla (u, v) congelada al detectar morado estable
        config: Configuración del sistema
        posturas: Dict de posturas.json
        cerebro: Instancia de CerebroZonas

    Returns:
        Trayectoria continua sincronizada
    """
    u, v = uv_congelado
    cfg_tray = config["trayectorias"]

    # Cargar mirada
    mirada_data = cargar_mirada()

    # Calcular offsets adaptativos usando v congelado
    offsets_adaptativos = calcular_offsets_adaptativos(v, config)

    # 1. PUNTO INICIAL: Reposo actual
    punto_reposo = {f"{motor}.pos": obs_actual.get(f"{motor}.pos", 0.0)
                    for motor in MOTOR_NAMES}

    # 2. PUNTO DESPERTAR: Dinámico (base mira al objetivo, cámara apunta a broca)
    punto_despertar = calcular_punto_despertar(
        obs_actual, uv_congelado, config, posturas, cerebro, mirada_data
    )

    # 3. PUNTO PRE-APROXIMACIÓN: Elevado y alineado, más lejos que antes
    postura_base = interpolar_postura(cerebro, u, v)

    offsets_pre_aprox = {
        "shoulder_lift": cfg_tray["altura_pre_aproximacion"],
        "elbow_flex": offsets_adaptativos["elbow_flex"],
    }
    punto_pre_aproximacion = aplicar_offsets(postura_base, offsets_pre_aprox)
    # wrist_flex ABSOLUTO desde mirada (no se suma): cámara apunta a broca
    punto_pre_aproximacion["wrist_flex.pos"] = min(
        interpolar_mirada(v, mirada_data), WRIST_FLEX_MAX_MIRADA
    )

    # 4. PUNTO FINAL: la postura grabada YA es la posición de trabajo
    # (boca de la aspiradora junto a la broca). Offsets finales por defecto 0,
    # solo para ajuste fino global opcional. wrist_flex = el de la postura.
    offsets_final = {
        "shoulder_lift": cfg_tray.get("altura_final", 0.0),
        "shoulder_pan": cfg_tray.get("offset_lateral_final", 0.0),
        "elbow_flex": cfg_tray.get("distancia_final", 0.0),
    }
    punto_final = aplicar_offsets(postura_base, offsets_final)

    # Lista de waypoints
    puntos = [
        punto_reposo,
        punto_despertar,
        punto_pre_aproximacion,
        punto_final
    ]

    # Calcular duración según velocidad configurada
    velocidad_maxima = cfg_tray["velocidad_trayectoria"]
    duracion = calcular_duracion_optima(puntos, velocidad_maxima)

    # Mínimo 3 segundos
    duracion = max(duracion, 3.0)

    traj = Trayectoria(puntos, duracion)
    # Fases para visualización (inicio de cada tramo)
    tw = traj.tiempos_waypoints
    traj.fases = [
        ("Reposo → Despertar", 0.0),
        ("Despertar → Pre-aproximación", float(tw[1])),
        ("Aproximación", float(tw[2]))
    ]
    return traj


def planificar_vuelta(obs_actual: Dict, postura_reposo: Dict,
                      config: Dict, posturas: Dict, cerebro,
                      uv_congelado: Optional[Tuple[float, float]] = None) -> Trayectoria:
    """
    Planifica la trayectoria de vuelta pasando por el punto de despertar.

    Trayectoria: final → retroceder hacia despertar → reposo

    Args:
        obs_actual: Observación actual del robot
        postura_reposo: Postura de reposo del robot
        config: Configuración del sistema
        posturas: Dict de posturas.json
        cerebro: Instancia de CerebroZonas
        uv_congelado: Tupla (u, v) opcional (si None, usa centro)

    Returns:
        Trayectoria continua sincronizada
    """
    cfg_tray = config["trayectorias"]

    # 1. PUNTO INICIAL: Postura actual
    punto_inicial = {f"{motor}.pos": obs_actual.get(f"{motor}.pos", 0.0)
                     for motor in MOTOR_NAMES}

    # 2. PUNTO SUBIDA: primero solo sube (shoulder_lift), sin recoger el codo,
    #    para separar la boca de la broca antes de retroceder
    punto_subida = punto_inicial.copy()
    punto_subida["shoulder_lift.pos"] += cfg_tray.get("subida_inicial_vuelta", -12.0)

    # 3. PUNTO RETROCESO: desde arriba, retroceder y seguir subiendo hacia despertar
    punto_retroceso = punto_inicial.copy()
    punto_retroceso["shoulder_lift.pos"] -= 20.0  # Subir 20 unidades
    punto_retroceso["elbow_flex.pos"] += 15.0     # Recoger 15 unidades

    # 4. PUNTO DESPERTAR (opcional, si tenemos UV congelado)
    if uv_congelado is not None:
        mirada_data = cargar_mirada()
        punto_despertar = calcular_punto_despertar(
            obs_actual, uv_congelado, config, posturas, cerebro, mirada_data
        )
        puntos = [
            punto_inicial,
            punto_subida,
            punto_retroceso,
            punto_despertar,
            postura_reposo
        ]
    else:
        # Sin UV, subir, retroceder y volver
        puntos = [
            punto_inicial,
            punto_subida,
            punto_retroceso,
            postura_reposo
        ]

    # Calcular duración (vuelta más rápida, es segura)
    velocidad_maxima = cfg_tray["velocidad_trayectoria"] * cfg_tray.get("factor_velocidad_vuelta", 1.0)
    duracion = calcular_duracion_optima(puntos, velocidad_maxima)

    # Mínimo 3 segundos
    duracion = max(duracion, 3.0)

    # Fases
    # PCHIP: el codo no se mueve mientras el brazo sube (tramo inicial)
    traj = Trayectoria(puntos, duracion, interpolacion="pchip")
    tw = traj.tiempos_waypoints
    traj.fases = [
        ("Subiendo", 0.0),
        ("Retrocediendo", float(tw[1])),
        ("Volviendo a reposo", float(tw[2]))
    ]
    return traj


def calcular_duracion_optima(puntos: List[Dict[str, float]],
                             velocidad_maxima: float) -> float:
    """
    Calcula la duración óptima de la trayectoria según el recorrido máximo.

    Args:
        puntos: Lista de waypoints
        velocidad_maxima: Velocidad máxima permitida (unidades/segundo)

    Returns:
        Duración en segundos
    """
    # Calcular recorrido total por articulación
    recorridos = {motor: 0.0 for motor in MOTOR_NAMES}

    for i in range(len(puntos) - 1):
        for motor in MOTOR_NAMES:
            key = f"{motor}.pos"
            delta = abs(puntos[i+1].get(key, 0.0) - puntos[i].get(key, 0.0))
            recorridos[motor] += delta

    # Encontrar la articulación que más recorre
    recorrido_max = max(recorridos.values())

    # Calcular duración: tiempo = distancia / velocidad
    duracion = recorrido_max / velocidad_maxima

    return duracion


def planificar(obs_actual: Dict, uv_congelado: Optional[Tuple[float, float]],
               config: Dict, posturas: Dict, cerebro, tipo: str = 'ida') -> Trayectoria:
    """
    Función principal para planificar trayectorias.

    Args:
        obs_actual: Observación actual del robot
        uv_congelado: Tupla (u, v) congelada (None para vuelta sin objetivo)
        config: Configuración del sistema
        posturas: Dict de posturas.json
        cerebro: Instancia de CerebroZonas
        tipo: 'ida' o 'vuelta'

    Returns:
        Trayectoria continua sincronizada
    """
    if tipo == 'ida':
        if uv_congelado is None:
            raise ValueError("uv_congelado requerido para trayectoria de ida")
        return planificar_ida(obs_actual, uv_congelado, config, posturas, cerebro)

    elif tipo == 'vuelta':
        return planificar_vuelta(obs_actual, posturas["reposo"], config, posturas, cerebro, uv_congelado)

    else:
        raise ValueError(f"Tipo de trayectoria desconocido: {tipo}")


# Script de test
if __name__ == "__main__":
    import json

    print("="*60)
    print("TEST DE TRAYECTORIAS CON DESPERTAR DINÁMICO")
    print("="*60)

    # Cargar config y posturas
    with open('config.json', 'r') as f:
        config = json.load(f)

    with open('posturas.json', 'r') as f:
        posturas = json.load(f)

    # Crear cerebro
    from cerebros import CerebroZonas
    cerebro = CerebroZonas(config)

    # Observación de ejemplo (reposo)
    obs_actual = {
        "shoulder_pan.pos": 65.8,
        "shoulder_lift.pos": 3.7,
        "elbow_flex.pos": -0.6,
        "wrist_flex.pos": 25.4,
        "wrist_roll.pos": -6.0,
        "gripper.pos": 0.0
    }

    # Test 1: Trayectoria de ida (centro de la zona)
    print("\nTest 1: Trayectoria de ida (u=0.5, v=0.5)")
    print("-"*60)

    uv_congelado = (0.5, 0.5)
    traj_ida = planificar(obs_actual, uv_congelado, config, posturas, cerebro, tipo='ida')

    print(f"Duración: {traj_ida.duracion:.2f}s")
    print(f"Waypoints: {len(traj_ida.puntos)}")
    print(f"Fases: {[f[0] for f in traj_ida.fases]}")

    # Muestrear en varios instantes
    print("\nProgresión de la trayectoria:")
    for t in [0.0, traj_ida.duracion * 0.25, traj_ida.duracion * 0.5,
              traj_ida.duracion * 0.75, traj_ida.duracion]:
        accion = traj_ida.muestrear(t)
        fase = traj_ida.fase_actual(t)
        print(f"  t={t:.2f}s ({fase}): "
              f"shoulder_pan={accion['shoulder_pan.pos']:.1f}°, "
              f"shoulder_lift={accion['shoulder_lift.pos']:.1f}°, "
              f"wrist_flex={accion['wrist_flex.pos']:.1f}°")

    # Test 2: Trayectoria de vuelta
    print("\nTest 2: Trayectoria de vuelta")
    print("-"*60)

    # Simular posición después de actuación
    obs_despues = traj_ida.muestrear(traj_ida.duracion)

    traj_vuelta = planificar(obs_despues, uv_congelado, config, posturas, cerebro, tipo='vuelta')

    print(f"Duración: {traj_vuelta.duracion:.2f}s")
    print(f"Waypoints: {len(traj_vuelta.puntos)}")
    print(f"Fases: {[f[0] for f in traj_vuelta.fases]}")

    # Test 3: Trayectoria en zona trasera (v > 0.6)
    print("\nTest 3: Trayectoria en zona trasera (u=0.5, v=0.9)")
    print("-"*60)

    uv_trasero = (0.5, 0.9)
    traj_trasero = planificar(obs_actual, uv_trasero, config, posturas, cerebro, tipo='ida')

    print(f"Duración: {traj_trasero.duracion:.2f}s")

    # Verificar punto de despertar
    punto_desp = traj_trasero.puntos[1]  # Punto de despertar
    print(f"  Despertar shoulder_pan: {punto_desp['shoulder_pan.pos']:.1f}°")
    print(f"  Despertar wrist_flex: {punto_desp['wrist_flex.pos']:.1f}°")

    print("\n✓ Tests completados")
