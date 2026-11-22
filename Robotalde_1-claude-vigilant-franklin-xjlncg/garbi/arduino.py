"""Arduino de Garbi: enciende y apaga la aspiradora (enchufe comercial de 433 MHz o Shelly) con latido de seguridad.

Protocolo por serie (115200, una línea por mensaje, como el firmware de `firmware/`):
- PC → Arduino: `?` (identificarse) · `A1` / `A0` (aspiradora encendida / apagada) · `L` (latido, cada 0,5 s).
- Arduino → PC: `{"id": "garbi"}` al `?` · `{"t": <ms>, "asp": 0|1, "ok": 0|1}` al cambiar y cada segundo.

Seguridad: si el Arduino no recibe ningún mensaje en `TIEMPO_LATIDO` s, apaga la aspiradora y avisa `ok = 0`. En el
PC, si el Arduino calla `TIEMPO_LATIDO` s, el orquestador congela el robot.

`ArduinoVirtual` reproduce ese comportamiento sin hardware (para la simulación y los tests).
"""
from __future__ import annotations

import json

TIEMPO_LATIDO = 1.0  # s


class ArduinoVirtual:
    def __init__(self):
        self.aspiradora = False
        self.ok = True
        self._ultimo_mensaje = 0.0
        self.t = 0.0
        self.salida: list[str] = []

    def recibir(self, linea: str, t: float) -> None:
        """Mensaje del PC en el instante `t` (s)."""
        self.t = t
        self._ultimo_mensaje = t
        self.ok = True
        linea = linea.strip()
        if linea == "?":
            self.salida.append(json.dumps({"id": "garbi"}))
        elif linea in ("A1", "A0"):
            nuevo = linea == "A1"
            if nuevo != self.aspiradora:
                self.aspiradora = nuevo
                self._informar()

    def avanzar(self, t: float) -> None:
        """Pasa el tiempo; si el PC calla demasiado, apaga la aspiradora."""
        self.t = t
        if t - self._ultimo_mensaje > TIEMPO_LATIDO and (self.aspiradora or self.ok):
            self.aspiradora = False
            self.ok = False
            self._informar()

    def _informar(self) -> None:
        self.salida.append(json.dumps({"t": int(self.t * 1000), "asp": int(self.aspiradora), "ok": int(self.ok)}))


class EnlaceArduino:
    """Lado del PC: manda órdenes y latidos, y vigila que el Arduino responda."""

    def __init__(self, arduino: ArduinoVirtual):
        self.arduino = arduino
        self._ultimo_latido = -1e9

    def aspiradora(self, encendida: bool, t: float) -> None:
        self.arduino.recibir("A1" if encendida else "A0", t)
        self._ultimo_latido = t

    def latido(self, t: float) -> None:
        if t - self._ultimo_latido >= 0.5:
            self.arduino.recibir("L", t)
            self._ultimo_latido = t
        self.arduino.avanzar(t)

    @property
    def aspiradora_encendida(self) -> bool:
        return self.arduino.aspiradora

    @property
    def sano(self) -> bool:
        return self.arduino.ok
