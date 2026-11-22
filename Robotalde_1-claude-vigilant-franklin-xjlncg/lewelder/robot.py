"""El robot soldador detrás de una interfaz: el servidor no sabe si es un sustituto cinemático, MuJoCo o el SO-101.

Interfaz (`Robot`)
------------------
    punta = await robot.soldar(tipo, anclaje, instruccion, huecos, al_moverse)

- Recorre **siempre el cordón completo** (spec: la política no sabe de huecos; el servidor enciende el LED de la
  antorcha del robot solo cuando la punta entra en un tramo pendiente). `huecos` se pasa por si una implementación
  quiere usarlo (p. ej. para registrar), pero no debe cambiar la trayectoria.
- `instruccion` es el texto del vocabulario cerrado (`contrato.instruccion_soldar`), el mismo que en el dataset:
  es lo que recibe el VLA.
- `al_moverse(muestra)` se llama en cada paso de control con la punta en el marco de la pieza (`Muestra` con
  gatillo False: el LED lo decide el servidor). Puede ser una función normal o una corrutina.
- Devuelve la lista de muestras de la punta. `parar()` interrumpe una soldadura en curso.
- `politica` ("vla" | "act" | "replay") se puede cambiar en caliente, también a mitad de una soldadura (plan B en
  segundos). `estado()` da un dict serializable para la tablet.

`RobotCinematico` es un sustituto sin física: mueve la punta a lo largo del cordón a velocidad de soldadura con algo
de ruido (más con el VLA que con el ACT, menos con la reproducción). `lewelder.robot_mujoco.RobotMuJoCo` es el SO-101
simulado en MuJoCo movido por las políticas reales (`robot/politica.py`) con esta misma interfaz.
"""
from __future__ import annotations

import asyncio
import inspect
from collections.abc import Awaitable, Callable, Sequence
from typing import Protocol, runtime_checkable

import numpy as np

from lewelder.contrato import ALTURA_PUNTA, LONGITUD_CORDON, Muestra, TipoPieza

POLITICAS = ("vla", "act", "replay")
# El LED de la antorcha del robot solo puede lucir con la punta encima del cordón: dentro de los 120 mm, a menos de
# `BANDA_LED` mm a un lado u otro y entre `Z_MIN_LED` y `metricas.Z_LEVANTADA` de altura. Sin la banda lateral, con
# el brazo en reposo la punta queda por debajo de la superficie de la pieza (z < 0) pero muy lejos en Y, y contaba.
BANDA_LED = 20.0  # mm
Z_MIN_LED = -5.0  # mm
NOMBRE_POLITICA = {"vla": "VLA (SmolVLA)", "act": "ACT", "replay": "Reproducción grabada"}

AlMoverse = Callable[[Muestra], Awaitable[None] | None]


@runtime_checkable
class Robot(Protocol):
    politica: str

    async def soldar(self, tipo: TipoPieza | str, anclaje: str, instruccion: str,
                     huecos: Sequence[tuple[float, float]] | None, al_moverse: AlMoverse) -> list[Muestra]: ...
    def estado(self) -> dict: ...
    def parar(self) -> None: ...


def punta_sobre_cordon(m: Muestra) -> bool:
    """¿Está la punta encima del cordón, a la altura de soldar? (condición para que luzca el LED del robot)."""
    from lewelder.metricas import Z_LEVANTADA

    return Z_MIN_LED <= m.z <= Z_LEVANTADA and 0.0 <= m.x <= LONGITUD_CORDON and abs(m.y) <= BANDA_LED


def validar_politica(politica: str) -> str:
    politica = str(politica).lower()
    if politica not in POLITICAS:
        raise ValueError(f"política desconocida: {politica!r} (válidas: {', '.join(POLITICAS)})")
    return politica


class RobotCinematico:
    """Sustituto cinemático del robot: aproximación, cordón completo a velocidad constante y retirada.

    - `velocidad`: mm/s a lo largo del cordón (la del alumno bueno, 5 mm/s).
    - `frecuencia`: pasos de control por segundo (30, como el dataset).
    - `escala_tiempo`: >1 acelera el reloj (tests y ensayos rápidos); la trayectoria es la misma.
    - `ruido_mm`: desviación típica del error lateral por política.
    """

    RUIDO_POR_POLITICA = {"vla": 0.8, "act": 0.5, "replay": 0.25}
    MARGEN = 8.0  # mm antes y después del cordón
    ALTURA_SEGURA = 40.0  # mm sobre la pieza al llegar y al irse
    TIEMPO_BAJADA = 1.2  # s

    def __init__(self, politica: str = "vla", velocidad: float = 5.0, frecuencia: float = 30.0,
                 escala_tiempo: float = 1.0, semilla: int = 0):
        self.politica = validar_politica(politica)
        self.velocidad = velocidad
        self.frecuencia = frecuencia
        self.escala_tiempo = escala_tiempo
        self.rng = np.random.default_rng(semilla)
        self.punta: Muestra | None = None
        self.instruccion: str | None = None
        self.ocupado = False
        self.progreso = 0.0  # 0-1 del recorrido
        self._parar = False
        self.cambios_politica: list[tuple[float, str]] = []  # (t, política) para el registro

    def cambiar_politica(self, politica: str) -> None:
        self.politica = validar_politica(politica)
        if self.punta is not None:
            self.cambios_politica.append((self.punta.t, self.politica))

    def parar(self) -> None:
        self._parar = True

    def estado(self) -> dict:
        return {
            "tipo_robot": "cinematico", "politica": self.politica, "nombre_politica": NOMBRE_POLITICA[self.politica],
            "ocupado": self.ocupado, "instruccion": self.instruccion, "progreso": round(self.progreso, 3),
            "punta": None if self.punta is None else {"x": self.punta.x, "y": self.punta.y, "z": self.punta.z},
        }

    def _trayectoria(self) -> list[tuple[float, float, float]]:
        """Puntos ideales (x, y, z) a `frecuencia`: bajada, cordón, subida."""
        dt = 1.0 / self.frecuencia
        x0, x1 = -self.MARGEN, LONGITUD_CORDON + self.MARGEN
        n_bajada = max(2, int(self.TIEMPO_BAJADA * self.frecuencia))
        puntos = []
        for i in range(n_bajada):  # bajada suave (coseno) hasta la altura de soldadura
            s = 0.5 - 0.5 * np.cos(np.pi * i / (n_bajada - 1))
            puntos.append((x0, 0.0, self.ALTURA_SEGURA + (ALTURA_PUNTA - self.ALTURA_SEGURA) * s))
        x = x0
        while x < x1:
            x += self.velocidad * dt
            puntos.append((min(x, x1), 0.0, ALTURA_PUNTA))
        for i in range(n_bajada):
            s = 0.5 - 0.5 * np.cos(np.pi * i / (n_bajada - 1))
            puntos.append((x1, 0.0, ALTURA_PUNTA + (self.ALTURA_SEGURA - ALTURA_PUNTA) * s))
        return puntos

    async def soldar(self, tipo: TipoPieza | str, anclaje: str, instruccion: str,
                     huecos: Sequence[tuple[float, float]] | None, al_moverse: AlMoverse) -> list[Muestra]:
        TipoPieza(tipo)  # valida
        if self.ocupado:
            raise RuntimeError("el robot ya está soldando")
        self.ocupado, self._parar = True, False
        self.instruccion = instruccion
        dt = 1.0 / self.frecuencia
        puntos = self._trayectoria()
        recorrido: list[Muestra] = []
        # Error lateral suave (como el temblor de la mano pero más pequeño): paseo aleatorio amortiguado.
        error = np.zeros(2)
        reloj = asyncio.get_running_loop().time
        inicio = reloj()
        try:
            for i, (x, y, z) in enumerate(puntos):
                if self._parar:
                    break
                sigma = self.RUIDO_POR_POLITICA[self.politica]
                error = 0.9 * error + self.rng.normal(0.0, sigma * 0.45, 2)
                t = i * dt
                self.punta = Muestra(t=t, x=float(x + 0.3 * error[1]), y=float(y + error[0]),
                                     z=float(z + 0.2 * abs(error[1])), gatillo=False)
                self.progreso = i / max(1, len(puntos) - 1)
                recorrido.append(self.punta)
                r = al_moverse(self.punta)
                if inspect.isawaitable(r):
                    await r
                espera = inicio + (t + dt) / self.escala_tiempo - reloj()
                await asyncio.sleep(max(0.0, espera))
        finally:
            self.ocupado = False
        return recorrido
