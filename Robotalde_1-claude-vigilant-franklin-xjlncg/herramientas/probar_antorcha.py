"""Prueba las antorchas reales (o virtuales): las busca, muestra gatillo y ángulos y hace parpadear el LED del robot.

Para comprobar el montaje de la IMU y los signos (ver firmware/README.md):
1. Antorcha vertical, punta abajo, cara superior hacia el avance → pulsa Intro (tara).
2. Inclina la punta en el sentido de avance (empuje): el avance debe subir. Inclínala hacia la izquierda mirando en
   el sentido de avance (+Y de la pieza): el trabajo debe bajar de 90.

Uso: .venv\\Scripts\\python.exe herramientas\\probar_antorcha.py [--alumno COM5] [--robot COM6]
"""
import argparse
import sys
import threading
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from lewelder.antorcha import AntorchaAlumno, AntorchaRobot, buscar_antorchas  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--alumno", help="puerto de la antorcha del alumno (si no, se busca)")
    parser.add_argument("--robot", help="puerto de la antorcha del robot (si no, se busca)")
    args = parser.parse_args()

    puertos = {"alumno": args.alumno, "robot": args.robot}
    if not all(puertos.values()):
        print("Buscando antorchas...")
        encontradas = buscar_antorchas()
        print("Encontradas:", encontradas or "ninguna")
        puertos = {k: v or encontradas.get(k) for k, v in puertos.items()}

    robot = AntorchaRobot(puertos["robot"]) if puertos["robot"] else None
    alumno = AntorchaAlumno(puertos["alumno"]) if puertos["alumno"] else None
    if alumno is None and robot is None:
        return

    def esperar_intro():
        while sys.stdin.readline():  # "" = fin de la entrada
            if alumno is not None:
                print("\nTara hecha." if alumno.tara() else "\nSin orientación: no hay IMU o aún no llega nada.")

    threading.Thread(target=esperar_intro, daemon=True).start()
    print("Intro = tara · Ctrl+C = salir")
    inicio = time.monotonic()
    try:
        while True:
            if robot is not None:
                robot.led(int(time.monotonic() - inicio) % 2 == 0)  # parpadeo de 1 s
            if alumno is not None and alumno.ultima is not None:
                lec = alumno.ultima
                trabajo, avance = alumno.angulos()
                angulos = "sin tara/IMU" if trabajo is None else f"trabajo {trabajo:6.1f}°  avance {avance:6.1f}°"
                print(f"\rt={lec.t:8.2f}s  gatillo={'SÍ' if lec.gatillo else 'no'}  {angulos}   ", end="", flush=True)
            time.sleep(0.05)
    except KeyboardInterrupt:
        print()
    finally:
        for antorcha in (alumno, robot):
            if antorcha is not None:
                antorcha.cerrar()


if __name__ == "__main__":
    main()
