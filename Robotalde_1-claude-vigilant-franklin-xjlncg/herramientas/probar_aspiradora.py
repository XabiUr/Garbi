"""Prueba del Arduino de la aspiradora, sin robot: la enciende unos segundos, la apaga y prueba el latido.

    python herramientas/probar_aspiradora.py COM5            (Windows)
    python herramientas/probar_aspiradora.py /dev/ttyACM0    (Linux)

Pasos:
1. Enciende 3 s y apaga (lo mismo que hará Garbi al aspirar).
2. Enciende y corta el latido sin mandar "0": el Arduino debe apagarla solo en ~1 s.
Necesita: pip install pyserial
"""
from __future__ import annotations

import sys
import time

import serial


def leer(s: serial.Serial) -> None:
    while s.in_waiting:
        print("   Arduino:", s.readline().decode(errors="replace").strip())


def latir(s: serial.Serial, valor: bytes, segundos: float) -> None:
    fin = time.time() + segundos
    while time.time() < fin:
        s.write(valor)
        leer(s)
        time.sleep(0.2)


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    with serial.Serial(sys.argv[1], 115200, timeout=0.1) as s:
        time.sleep(2.0)  # al abrir el puerto el Arduino se reinicia
        leer(s)
        print("1) Aspiradora ENCENDIDA 3 s")
        latir(s, b"1\n", 3.0)
        print("   ... APAGADA")
        latir(s, b"0\n", 2.0)
        print("2) ENCENDIDA y corto el latido: debe apagarse sola en ~1 s")
        latir(s, b"1\n", 2.0)
        t0 = time.time()
        while time.time() - t0 < 2.5:
            leer(s)
            time.sleep(0.1)
        print("Hecho. Si en el paso 2 siguió encendida más de 1-2 s, revisa el firmware.")


if __name__ == "__main__":
    main()
