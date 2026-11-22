"""Contratos entre los módulos de Garbi (especificación técnica, 19-11).

Percepción → `Escena` → Ciclo (máquina de estados) → `Orden` → Cuerpo (robot simulado o real).
El paso 7 (limpiar la zona del agujero) lo hace una `Habilidad`: el barrido programado o ACT.

Unidades: mm y grados, marco de la mesa (origen en la base del robot, x hacia la persona, y a la izquierda del robot,
z hacia arriba). Las articulaciones van en el orden de LeRobot: pan, lift, elbow, flex, roll, gripper.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

import numpy as np

from garbi.contrato import PoseTabla

ARTICULACIONES = ("shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper")
HZ_CONTROL = 30.0
HZ_PERCEPCION = 15.0
DURACION_LIMPIEZA = 5.0  # s: cada episodio del paso 7 dura esto, fijo
TAREA_LIMPIEZA = "Clean the hole."
# Solución final (20-11): ACT hace el ACERCAMIENTO a la broca clavada (desde la posición prudente hasta aspirar, y se
# mantiene ahí mientras taladras). La limpieza de los agujeros pasa a ser fija.
TAREA_ACERCAMIENTO = "Approach the drill bit."


@dataclass
class Taladro:
    visible: bool
    xy: np.ndarray | None = None  # marcador proyectado a la mesa (mm)
    velocidad: float = 0.0  # mm/s
    quieto_desde: float | None = None  # t (s) desde el que está quieto; None si se mueve
    en_zona: bool = False  # dentro de la zona de trabajo (sobre la madera, al alcance)
    # Regla del usuario (20-11): solo cuenta como taladro si hay MANO + TALADRO juntos (una mano a menos de
    # DIST_MANO_TALADRO del taladro). Ni la mano sola ni el taladro solo (dejado en la mesa) hacen que Garbi le siga.
    agarrado: bool = False
    distancia_mano: float | None = None  # mm de la mano más cercana al taladro (None: sin manos o sin taladro)


@dataclass
class Mano:
    """Una mano vista por la cámara de arriba (MediaPipe en el robot real; color de piel en la simulación)."""
    xy: np.ndarray  # centro de la palma proyectado a la mesa (mm)
    en_tapete: bool = False
    confianza: float = 1.0
    uv: np.ndarray | None = None  # centro de la palma en la imagen de arriba (px); para medir la distancia al taladro
    fuente: str = ""  # "mediapipe", "color" o "verdad" (la de la simulación)
    del_taladro: bool = False  # la percepción la ha visto sujetando el taladro (no es una mano libre)


@dataclass
class Broca:
    punta: np.ndarray | None = None  # (x, y, z) mm en la mesa
    apoyada: bool = False
    fuente: str = ""  # "muneca" (de cerca, ±2 mm) o "arriba" (estimada, ±25 mm en z)
    # Eje de la broca, de la punta hacia el marcador (unitario, mesa). None: no se sabe (se supone vertical). La
    # percepción lo aprende de la punta medida por la muñeca y la bola vista desde arriba (taladro inclinado).
    eje: np.ndarray | None = None
    # Clavada: la punta apoyada en la madera y quieta (empieza el ACERCAMIENTO con ACT). Levantada: deja de estarlo
    # (termina ACT, retirada fija). Las decide la percepción con histéresis, no ACT.
    clavada_desde: float | None = None  # t (s) en que se clavó (apoyada) la broca, mientras siga clavada
    levantada_en: float | None = None  # t (s) de la última vez que se levantó tras estar clavada
    # "clavada" o "levantada" solo en la lectura en la que ocurre (para cortar episodios); "" en las demás
    evento: str = ""


@dataclass
class Escena:
    """Lo que Garbi sabe del mundo en un instante. Lo produce la percepción (o la verdad de la simulación)."""
    t: float
    madera: PoseTabla | None = None
    taladro: Taladro = field(default_factory=lambda: Taladro(visible=False))
    broca: Broca = field(default_factory=Broca)
    viruta: dict[int, int] = field(default_factory=dict)  # píxeles de viruta alrededor de cada agujero (índice)
    # Fracción (0-1) del círculo de 35 mm alrededor de cada agujero cubierta de viruta. La pone la percepción por
    # píxeles; si está, el ciclo decide «limpio» con ella (umbral UMBRAL_FRACCION_VIRUTA, 2 % en M3) y no con
    # `viruta`. La verdad de la simulación no la pone: allí `viruta` son partículas (umbral en partículas).
    viruta_fraccion: dict[int, float] = field(default_factory=dict)
    manos: list[Mano] = field(default_factory=list)

    @property
    def manos_en_tapete(self) -> bool:
        return any(m.en_tapete for m in self.manos)


# Zona de taladro de la demo: la punta de la broca a 320-420 mm del eje del robot (en planta). Dentro, Garbi acompaña
# (con la boca de lado, 15°, y la holgura de la especificación); fuera no lo intenta: si el taladro se acerca al robot,
# se aparta y espera.
ZONA_TALADRO = (320.0, 420.0)  # mm del eje del robot
DIST_MANO_TALADRO = 120.0  # mm: una mano a menos de esto del taladro (en planta) = taladro agarrado
DISTANCIA_PRUDENTE = 100.0  # mm de la broca a la boca en la posición prudente


def en_zona_taladro(xy, tolerancia: float = 0.0) -> bool:
    """¿La punta (x, y en la mesa) está en la zona de taladro? `tolerancia`: mm de más a cada lado."""
    r = float(np.hypot(xy[0], xy[1]))
    return ZONA_TALADRO[0] - tolerancia <= r <= ZONA_TALADRO[1] + tolerancia


UMBRAL_FRACCION_VIRUTA = 0.02  # limpio: < 2 % del círculo (M3)
UMBRAL_PARTICULAS_VIRUTA = 2  # limpio con la verdad de la simulación: ≤ 2 partículas en el círculo


@dataclass
class Orden:
    """Lo que el ciclo manda en cada paso de control."""
    q: np.ndarray  # 6 articulaciones, grados (roll = 0 y pinza cerrada, siempre)
    aspirar: bool
    estado: str
    detalle: str = ""


class Cuerpo(Protocol):
    """Robot (simulado o real) visto desde el ciclo."""

    def q(self) -> np.ndarray: ...  # postura actual (6, grados)

    def enviar(self, q: np.ndarray) -> None: ...

    def aspirar(self, encendida: bool) -> None: ...

    def imagenes(self) -> dict[str, np.ndarray]: ...  # {"top": RGB 480×640×3, "wrist": RGB 480×640×3}


class Habilidad(Protocol):
    """Paso 7. Se reinicia al empezar cada agujero y devuelve la acción de cada paso durante DURACION_LIMPIEZA."""

    def reiniciar(self, agujero_mesa: np.ndarray) -> None: ...

    def accion(self, obs: dict) -> np.ndarray: ...  # obs: {"top", "wrist", "state"} → 6 articulaciones (grados)


def forzar_montaje(q: np.ndarray) -> np.ndarray:
    """Muñeca fija y pinza cerrada, sea quien sea el que manda (el ciclo o ACT)."""
    q = np.asarray(q, dtype=float).copy()
    q[4] = 0.0
    q[5] = 0.0
    return q
