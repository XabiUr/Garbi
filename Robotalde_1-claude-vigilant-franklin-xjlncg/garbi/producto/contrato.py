"""Contratos entre los módulos del producto Garbi (21-11). Ver `.plans/aspira/producto.md`.

Todo va en **píxeles de la cámara de arriba** salvo las articulaciones (grados, orden de LeRobot). La relación píxel →
postura del robot la da la **matriz** que el equipo marcó a mano sobre el tapete (`garbi.producto.matriz`).

    cámaras ─> VisionProducto.leer() ─> Vista ─> Orquestador.paso() ─> Orden (q, aspirar) ─> robot
                                                   ^          │
    app (botones, chat con LLM, seta) ── Comando ──┘          └──> EstadoApp ──> app (estado, cámaras, tecnologías)
"""
from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Protocol

import numpy as np


class Estado(str, enum.Enum):
    APAGADO = "apagado"            # no se mueve ni mira; «enciéndete» lo pasa a REPOSO
    ARRANCANDO = "arrancando"      # encendido pero aún no listo (conectando el robot, yendo a reposo)
    REPOSO = "reposo"              # postura de reposo (girado a la derecha), esperando mano + taladro quieto
    ACERCAMIENTO = "acercamiento"  # la política (ACT o círculo) lleva la boca a la punta de la broca
    EN_BROCA = "en_broca"          # ha llegado: quieto junto a la broca, aspirando, hasta que se va mano + taladro
    DESPIERTO = "despierto"        # entre agujeros: postura de espera, sin volver a reposo
    LIMPIEZA_TABLA = "limpieza_tabla"    # barrido completo de la tabla a altura fija
    LIMPIEZA_TAPETE = "limpieza_tapete"  # barrido fijo de todo el tapete (siempre el mismo)
    EMERGENCIA = "emergencia"      # seta (barra espaciadora): quieto con par, aspiradora apagada


class Comando(str, enum.Enum):
    ENCENDER = "encender"
    APAGAR = "apagar"
    LIMPIAR_TABLA = "limpiar_tabla"
    LIMPIAR_TAPETE = "limpiar_tapete"
    PARAR = "parar"                # vuelve a reposo y apaga la aspiradora
    EMERGENCIA = "emergencia"      # seta
    REARMAR = "rearmar"            # salir de la emergencia (a REPOSO)


@dataclass
class Circulo:
    """El círculo morado de la trasera del taladro, en la cámara de arriba."""
    uv: np.ndarray          # centro (px)
    radio: float            # px
    quieto_desde: float | None = None  # t desde el que no se mueve (más de TOL_QUIETO px); None si se mueve


@dataclass
class Vista:
    """Lo que ve Garbi en un instante (cámara de arriba, píxeles)."""
    t: float
    circulo: Circulo | None = None
    manos: list[np.ndarray] = field(default_factory=list)   # centros de las manos (px)
    taladro_agarrado: bool = False   # mano + taladro juntos (regla del usuario: nunca mano sola ni taladro solo)
    tabla: np.ndarray | None = None  # 4 esquinas de la tabla (px) si está sobre el tapete; None si no hay tabla
    tapete: np.ndarray | None = None  # 4 esquinas del tapete (px); fijo, de la configuración


@dataclass
class Orden:
    q: np.ndarray | None   # 6 articulaciones (grados) o None = no mover (quedarse donde está)
    aspirar: bool
    estado: Estado
    detalle: str = ""


@dataclass
class EstadoApp:
    """Lo que la app enseña."""
    estado: Estado
    detalle: str
    aspiradora: bool
    politica: str                       # "act" o "circulo"
    tecnologias: dict[str, str]         # nombre → "ok" | "aviso: ..." | "error: ..." (visión, manos, política, robot...)
    agujeros: int = 0                   # acercamientos completados en esta sesión
    eventos: list[str] = field(default_factory=list)  # últimos eventos legibles («Taladro quieto 1 s: me acerco»)
    # Indicadores de la sesión (opcional; si viene vacío, la app los calcula observando el estado). Claves:
    # agujeros, t_aspirando (s), limpiezas_tabla, limpiezas_tapete, t_emergencia (s), disponibilidad (0..1), t_sesion (s)
    indicadores: dict[str, float] = field(default_factory=dict)


class Politica(Protocol):
    """La única política de acercamiento: ACT entrenado o el respaldo del círculo + matriz. Mismo uso para las dos."""
    nombre: str

    def reiniciar(self, vista: Vista, q: np.ndarray) -> None: ...

    def accion(self, obs: dict, vista: Vista) -> np.ndarray: ...   # obs: {"top", "wrist", "state"} → 6 grados

    def llegado(self) -> bool: ...   # ha llegado a la broca (converge / último punto)
