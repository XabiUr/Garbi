"""Indicadores de la sesión, como en una planta: agujeros acompañados, tiempo aspirando, limpiezas, tiempo en emergencia
y disponibilidad (% del tiempo que Garbi está listo: ni apagado ni en emergencia). Y el registro de eventos con fecha
para exportarlo en CSV (trazabilidad, como un MES).

`Indicadores.observar(estado, aspirando, t)` se llama con cada muestra del estado; integra los tiempos y cuenta las
entradas en cada estado. Lo usan el `OrquestadorFalso` y el servidor (cuando el orquestador no trae los suyos).
"""
from __future__ import annotations

import csv
import io
import threading
import time
from collections import deque
from datetime import datetime

from garbi.producto.contrato import Estado

NO_DISPONIBLE = (Estado.APAGADO, Estado.EMERGENCIA)
HUECO_MAX = 2.0   # s: si entre dos muestras pasa más, no se integra (pausa del proceso, depurador...)

CLAVES = ("agujeros", "t_aspirando", "limpiezas_tabla", "limpiezas_tapete", "t_emergencia", "disponibilidad",
          "t_sesion")
ETIQUETAS = {
    "agujeros": "Agujeros acompañados", "t_aspirando": "Tiempo aspirando (s)",
    "limpiezas_tabla": "Limpiezas de tabla", "limpiezas_tapete": "Limpiezas de tapete",
    "t_emergencia": "Tiempo en emergencia (s)", "disponibilidad": "Disponibilidad (%)", "t_sesion": "Sesión (s)",
}


class Indicadores:
    def __init__(self, hueco_max: float = HUECO_MAX):
        self.hueco_max = hueco_max
        self._t: float | None = None
        self._estado: Estado | None = None
        self._aspirando = False
        self.agujeros = 0
        self.limpiezas_tabla = 0
        self.limpiezas_tapete = 0
        self.t_aspirando = 0.0
        self.t_emergencia = 0.0
        self.t_disponible = 0.0
        self.t_sesion = 0.0

    def observar(self, estado: Estado, aspirando: bool, t: float) -> None:
        if self._t is not None:
            dt = t - self._t
            if 0 < dt <= self.hueco_max:   # el tiempo cuenta para el estado anterior
                self.t_sesion += dt
                if self._estado is Estado.EMERGENCIA:
                    self.t_emergencia += dt
                if self._estado not in NO_DISPONIBLE:
                    self.t_disponible += dt
                if self._aspirando:
                    self.t_aspirando += dt
        if estado is not self._estado:
            if estado is Estado.EN_BROCA:
                self.agujeros += 1
            elif estado is Estado.LIMPIEZA_TABLA:
                self.limpiezas_tabla += 1
            elif estado is Estado.LIMPIEZA_TAPETE:
                self.limpiezas_tapete += 1
        self._t, self._estado, self._aspirando = t, estado, aspirando

    def como_dict(self) -> dict[str, float]:
        return {
            "agujeros": self.agujeros, "t_aspirando": round(self.t_aspirando, 1),
            "limpiezas_tabla": self.limpiezas_tabla, "limpiezas_tapete": self.limpiezas_tapete,
            "t_emergencia": round(self.t_emergencia, 1),
            "disponibilidad": round(self.t_disponible / self.t_sesion, 4) if self.t_sesion > 0 else 1.0,
            "t_sesion": round(self.t_sesion, 1),
        }


class Registro:
    """Eventos con fecha y hora completas para exportar. Seguro entre hilos."""

    def __init__(self, maximo: int = 5000):
        self._filas: deque[tuple[str, str, str, str]] = deque(maxlen=maximo)
        self._vistos: deque[str] = deque(maxlen=200)   # eventos del orquestador ya apuntados
        self._cerrojo = threading.Lock()

    def anotar(self, tipo: str, detalle: str, origen: str = "", cuando: float | None = None) -> None:
        fecha = datetime.fromtimestamp(cuando if cuando is not None else time.time()).isoformat(timespec="seconds")
        with self._cerrojo:
            self._filas.append((fecha, tipo, origen, detalle))

    def eventos_orquestador(self, eventos: list[str]) -> None:
        """Apunta los eventos nuevos de `EstadoApp.eventos` (vienen del más nuevo al más viejo)."""
        nuevos = []
        with self._cerrojo:
            for ev in eventos:
                if ev in self._vistos:
                    break
                nuevos.append(ev)
            for ev in reversed(nuevos):
                self._vistos.append(ev)
        for ev in reversed(nuevos):
            self.anotar("evento", ev.split(" · ", 1)[-1], "garbi")

    def filas(self) -> list[tuple[str, str, str, str]]:
        with self._cerrojo:
            return list(self._filas)

    def csv(self, indicadores: dict[str, float], extra: dict[str, str] | None = None) -> str:
        """CSV con `;` (Excel en español) y BOM: primero los indicadores de la sesión, luego los eventos."""
        salida = io.StringIO()
        salida.write("﻿")
        w = csv.writer(salida, delimiter=";", lineterminator="\r\n")
        ahora = datetime.now().isoformat(timespec="seconds")
        w.writerow(["fecha_hora", "tipo", "origen", "detalle", "valor"])
        for clave, valor in (extra or {}).items():
            w.writerow([ahora, "sesion", "", clave, valor])
        for clave in CLAVES:
            if clave in indicadores:
                valor = indicadores[clave]
                if clave == "disponibilidad":
                    valor = round(100 * valor, 1)
                w.writerow([ahora, "indicador", "", ETIQUETAS[clave], _numero(valor)])
        for fecha, tipo, origen, detalle in self.filas():
            w.writerow([fecha, tipo, origen, detalle, ""])
        return salida.getvalue()


def _numero(valor: float) -> str:
    """Coma decimal (Excel en español)."""
    return f"{valor:g}".replace(".", ",") if isinstance(valor, float) else str(valor)
