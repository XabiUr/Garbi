"""Lanza antorchas virtuales en pseudo-terminales para probar todo sin placas (solo Linux/macOS).

Imprime la ruta de cada puerto (p. ej. /dev/pts/5); `AntorchaAlumno` y `AntorchaRobot` se conectan a ella como a
un USB real. La del alumno sigue un guion de 30 s (vertical sin gatillo los 3 primeros: momento de la tara).

Uso: .venv/bin/python herramientas/antorcha_virtual.py [alumno|robot|ambas] [--sin-imu]
"""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from lewelder.antorcha_virtual import main  # noqa: E402

if __name__ == "__main__":
    main()
