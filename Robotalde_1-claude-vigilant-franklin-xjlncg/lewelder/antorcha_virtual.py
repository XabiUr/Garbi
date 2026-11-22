"""Antorchas virtuales: pseudo-terminales (pty) que se comportan como el firmware de las placas.

Sirven para la simulación completa sin hardware. Cada antorcha virtual abre un pty y publica su ruta
(`/dev/pts/N`); `AntorchaAlumno` y `AntorchaRobot` se conectan a ella como a un puerto USB real.

- **Alumno:** emite `{"t": ms, "g": 0|1, "q": [w, x, y, z]}` a 100 Hz. Los ángulos y el gatillo salen de una
  trayectoria `f(t) -> (trabajo, avance, gatillo)` en grados y segundos, del guion por defecto o de `fijar()`
  (control manual, p. ej. desde el ratón de la tablet). El cuaternión se calcula con la convención de tara de
  `lewelder.antorcha` en un marco "mundo" de la IMU que no coincide con el de la pieza (como en la placa real):
  hay que hacer la tara para obtener los ángulos. `q_tara` es lo que leería la IMU en la postura de la tara.
- **Robot:** acepta `L1`/`L0`, registra los cambios y apaga el LED si no recibe órdenes en 2 s, como el firmware.

Ambas responden a `?` con su `{"id": ...}`. Uso por línea de órdenes: `python herramientas/antorcha_virtual.py`.
"""
from __future__ import annotations

import argparse
import math
import os
import select
import threading
import time
import tty
from collections.abc import Callable

import numpy as np

from lewelder import contrato as c
from lewelder.antorcha import (
    ORIENTACION_TARA,
    Cuaternion,
    _giro_z,
    _Lineas,
    cuaternion_desde_angulos,
    cuaternion_desde_matriz,
)

Trayectoria = Callable[[float], tuple[float, float, bool]]

# Marco "mundo" por defecto de la IMU virtual respecto al de la tara: un rumbo cualquiera, como el de una IMU real.
MUNDO_POR_DEFECTO = _giro_z(37.0)
DURACION_GUION = 30.0  # s


def guion_por_defecto(t: float) -> tuple[float, float, bool]:
    """Pasada de ejemplo que se repite cada 30 s.

    0-3 s antorcha vertical sin gatillo (momento de hacer la tara); 3-28 s soldando con trabajo 90 ± 4°, empuje
    10 ± 3° y un hueco sin gatillo entre 11 y 13 s; 28-30 s parada.
    """
    t = t % DURACION_GUION
    if t < 3.0 or t >= 28.0:
        return 90.0, 0.0, False
    trabajo = 90.0 + 4.0 * math.sin(2 * math.pi * 0.3 * t)
    avance = 10.0 + 3.0 * math.sin(2 * math.pi * 0.2 * t)
    return trabajo, avance, not (11.0 <= t < 13.0)


def linea_muestra(t_ms: int, gatillo: bool, q: Cuaternion | None) -> bytes:
    """Línea exactamente como la imprime el firmware (4 decimales)."""
    texto_q = "null" if q is None else "[" + ",".join(f"{v:.4f}" for v in q) + "]"
    return f'{{"t":{t_ms},"g":{int(gatillo)},"q":{texto_q}}}\n'.encode()


def linea_id(identidad: str) -> bytes:
    return f'{{"id":"{identidad}"}}\n'.encode()


class _DispositivoPty:
    """Base: un pty con un hilo que atiende las órdenes del PC."""

    identidad = ""

    def __init__(self):
        self._maestro, self._esclavo = os.openpty()
        tty.setraw(self._esclavo)
        os.set_blocking(self._maestro, False)
        # El esclavo se queda abierto aquí para que el maestro no dé error cuando no hay nadie conectado.
        self.ruta = os.ttyname(self._esclavo)
        self.bytes_perdidos = 0
        self._lineas = _Lineas()
        self._t0 = time.monotonic()
        self._parar = threading.Event()
        self._hilo = threading.Thread(target=self._bucle, name=f"virtual-{self.identidad}", daemon=True)
        self._hilo.start()

    def _escribir(self, datos: bytes):
        """Escribe sin bloquear; si nadie lee y el búfer se llena, se pierde (como un puerto real sin abrir)."""
        try:
            escritos = os.write(self._maestro, datos)
        except (BlockingIOError, OSError):
            escritos = 0
        self.bytes_perdidos += len(datos) - escritos

    def _esperar_ordenes(self, timeout: float) -> list[str]:
        """Espera hasta `timeout` s a que lleguen bytes y devuelve las líneas completas recibidas."""
        try:
            listos, _, _ = select.select([self._maestro], [], [], max(0.0, timeout))
            if not listos:
                return []
            datos = os.read(self._maestro, 1024)
        except (BlockingIOError, InterruptedError):
            return []
        except OSError:
            self._parar.wait(timeout)
            return []
        return [l.strip(b"\r").decode("utf-8", "replace") for l in self._lineas.trocear(datos)]

    def _atender(self, orden: str) -> bool:
        """Responde a `?`. Devuelve True si la orden era válida."""
        if orden == c.ORDEN_IDENTIFICAR.strip():
            self._escribir(linea_id(self.identidad))
            return True
        return False

    def _bucle(self):
        raise NotImplementedError

    def parar(self):
        self._parar.set()
        self._hilo.join(timeout=2)
        for fd in (self._maestro, self._esclavo):
            try:
                os.close(fd)
            except OSError:
                pass

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.parar()


class AntorchaAlumnoVirtual(_DispositivoPty):
    """Antorcha del alumno virtual en un pty.

    `trayectoria(t)` → `(trabajo, avance, gatillo)` con `t` en segundos desde el arranque; por defecto
    `guion_por_defecto`. `mundo` es el marco "mundo" de la IMU respecto al de la tara (matriz 3x3).
    `giro_pieza_grados` es el giro de la pieza respecto a la tara (el consumidor debe pasar el mismo).
    """

    identidad = "alumno"

    def __init__(
        self,
        trayectoria: Trayectoria | None = None,
        *,
        mundo: np.ndarray | None = None,
        giro_pieza_grados: float = 0.0,
        sin_imu: bool = False,
        frecuencia: float = c.FRECUENCIA_ANTORCHA,
    ):
        self.trayectoria = trayectoria or guion_por_defecto
        self.mundo = MUNDO_POR_DEFECTO if mundo is None else np.asarray(mundo, dtype=float)
        self.giro_pieza_grados = giro_pieza_grados
        self.sin_imu = sin_imu
        self.periodo = 1.0 / frecuencia
        self.q_tara: Cuaternion = cuaternion_desde_matriz(self.mundo @ ORIENTACION_TARA)
        self.n_muestras = 0
        self._manual: tuple[float, float, bool] | None = None
        super().__init__()

    def fijar(self, trabajo: float, avance: float, gatillo: bool):
        """Pasa a control manual con estos ángulos y gatillo (deja de seguir la trayectoria)."""
        self._manual = (float(trabajo), float(avance), bool(gatillo))

    def soltar(self):
        """Vuelve a seguir la trayectoria."""
        self._manual = None

    def estado(self, t: float) -> tuple[float, float, bool]:
        return self._manual if self._manual is not None else self.trayectoria(t)

    def muestra(self, t: float) -> bytes:
        trabajo, avance, gatillo = self.estado(t)
        q = None
        if not self.sin_imu:
            q = cuaternion_desde_angulos(trabajo, avance, q_tara=self.q_tara, giro_pieza_grados=self.giro_pieza_grados)
        return linea_muestra(int(t * 1000), gatillo, q)

    def _bucle(self):
        siguiente = self._t0
        while not self._parar.is_set():
            for orden in self._esperar_ordenes(siguiente - time.monotonic()):
                self._atender(orden)
            ahora = time.monotonic()
            if ahora < siguiente:
                continue
            self._escribir(self.muestra(ahora - self._t0))
            self.n_muestras += 1
            siguiente += self.periodo
            if ahora - siguiente > 0.1:  # muy retrasado (p. ej. el proceso estuvo parado): se resincroniza
                siguiente = ahora + self.periodo


class AntorchaRobotVirtual(_DispositivoPty):
    """Antorcha del robot virtual en un pty: LED con `L1`/`L0` y apagado de seguridad.

    `registro` guarda `(t, encendido)` en cada cambio (t en s desde el arranque); `al_cambiar(encendido)` se
    llama en cada cambio (p. ej. para pintar el LED en la simulación).
    """

    identidad = "robot"

    def __init__(
        self, *, tiempo_seguridad: float = c.TIEMPO_SEGURIDAD_LED, al_cambiar: Callable[[bool], None] | None = None
    ):
        self.tiempo_seguridad = tiempo_seguridad
        self.al_cambiar = al_cambiar
        self.encendido = False
        self.registro: list[tuple[float, bool]] = []
        self.n_ordenes = 0
        self._ultima_orden = time.monotonic()
        super().__init__()

    def _poner(self, encendido: bool):
        if encendido == self.encendido:
            return
        self.encendido = encendido
        self.registro.append((time.monotonic() - self._t0, encendido))
        if self.al_cambiar is not None:
            self.al_cambiar(encendido)

    def _atender(self, orden: str) -> bool:
        if orden == c.ORDEN_LED_ON.strip():
            self._poner(True)
        elif orden == c.ORDEN_LED_OFF.strip():
            self._poner(False)
        elif not super()._atender(orden):
            return False
        self.n_ordenes += 1
        self._ultima_orden = time.monotonic()
        return True

    def _bucle(self):
        while not self._parar.is_set():
            for orden in self._esperar_ordenes(0.02):
                self._atender(orden)
            if self.encendido and time.monotonic() - self._ultima_orden > self.tiempo_seguridad:
                self._poner(False)


# --- línea de órdenes --------------------------------------------------------------------------------------------
def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(description="Antorchas virtuales en pseudo-terminales (sin hardware).")
    parser.add_argument("tipo", nargs="?", choices=["alumno", "robot", "ambas"], default="ambas")
    parser.add_argument("--sin-imu", action="store_true", help="la antorcha del alumno manda q nulo")
    args = parser.parse_args(argv)

    dispositivos = []
    if args.tipo in ("alumno", "ambas"):
        alumno = AntorchaAlumnoVirtual(sin_imu=args.sin_imu)
        dispositivos.append(alumno)
        print(f"alumno: {alumno.ruta}  (guion de {DURACION_GUION:.0f} s; tara en los 3 primeros)", flush=True)
    if args.tipo in ("robot", "ambas"):
        robot = AntorchaRobotVirtual(
            al_cambiar=lambda e: print(f"robot: LED {'ENCENDIDO' if e else 'apagado'}", flush=True)
        )
        dispositivos.append(robot)
        print(f"robot: {robot.ruta}", flush=True)
    print("Ctrl+C para salir.", flush=True)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        for d in dispositivos:
            d.parar()


if __name__ == "__main__":
    main()
