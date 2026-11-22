#!/usr/bin/env python3
"""
grabar_posturas_mesa.py - Graba las posturas de BARRIDO sobre la rejilla de la mesa → posturas_mesa.json.

Independiente del taladro: no usa el morado ni posturas.json (solo la postura de reposo para nada; no la toca).
Necesita mesa.json (python calibrar_mesa.py).

En la imagen se dibujan los puntos de la rejilla (3×3 por defecto) sobre la mesa. Para cada punto:
lleva la BOQUILLA justo encima de ese punto, a la altura a la que quieres que barra, y pulsa su tecla.
    Teclas 1-9 (y A-F si la rejilla tiene más de 9 puntos): grabar ese punto
    Q / ESC: salir (se guarda tras cada punto)

Numeración (vista como en la imagen; 1 = esquina 1 de mesa.json, delante-izq):
    7 8 9      ← detrás
    4 5 6
    1 2 3      ← delante

Uso:
    python grabar_posturas_mesa.py --real --a-mano    # sin líder: mueves el brazo a mano (torque desactivado)
    python grabar_posturas_mesa.py --real             # con el líder
    python grabar_posturas_mesa.py --sin-robot        # simulado
"""

import argparse
import json

import cv2
import numpy as np

from calibrar_mesa import puntos_rejilla_px
from grabar_posturas import crear_robot_y_teleop

MOTORES = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"]
TECLAS = "123456789abcdef"
RUTA = "posturas_mesa.json"


def cargar(n_u, n_v):
    try:
        with open(RUTA) as f:
            d = json.load(f)
        if d.get("rejilla") != {"n_u": n_u, "n_v": n_v}:
            print(f"⚠️  {RUTA} tiene otra rejilla ({d.get('rejilla')}): empiezo de cero")
            raise FileNotFoundError
        return d
    except FileNotFoundError:
        return {"rejilla": {"n_u": n_u, "n_v": n_v}, "posturas": {},
                "nota": "Postura de la boquilla sobre cada punto de la rejilla de mesa.json. "
                        "Clave 'i,j': i = columna (u), j = fila (v), desde la esquina 1."}


def main():
    ap = argparse.ArgumentParser(description="Grabar posturas de barrido sobre la mesa")
    ap.add_argument("--sin-robot", action="store_true")
    ap.add_argument("--real", action="store_true")
    ap.add_argument("--a-mano", action="store_true", help="sin líder: torque desactivado, mueves el brazo a mano")
    args = ap.parse_args()
    if not (args.sin_robot or args.real):
        raise SystemExit("❌ Debes especificar --sin-robot o --real")

    config = json.load(open("config.json"))
    try:
        mesa = json.load(open("mesa.json"))
    except FileNotFoundError:
        raise SystemExit("❌ Falta mesa.json. Ejecuta primero: python calibrar_mesa.py")
    n_u, n_v = mesa["rejilla"]["n_u"], mesa["rejilla"]["n_v"]
    if n_u * n_v > len(TECLAS):
        raise SystemExit(f"❌ Rejilla {n_u}×{n_v} demasiado grande (máx {len(TECLAS)} puntos)")
    puntos = puntos_rejilla_px(np.array(mesa["esquinas_px"]), n_u, n_v)
    tecla_a_ij = {TECLAS[j * n_u + i]: (i, j) for j in range(n_v) for i in range(n_u)}
    datos = cargar(n_u, n_v)

    robot, teleop = crear_robot_y_teleop(config, args.sin_robot, args.a_mano)
    robot.connect(calibrate=False)
    if args.a_mano and hasattr(robot, "bus"):
        for m in MOTORES:
            robot.bus.write("Torque_Enable", m, 0)
        print("✓ Torque desactivado: mueve el brazo con la mano")
    elif teleop is not None:
        teleop.connect()
        print("✓ Líder conectado")
    print(__doc__)

    try:
        while True:
            obs = robot.get_observation()
            if teleop is not None and not args.a_mano:
                robot.send_action(teleop.get_action())
            img = cv2.cvtColor(obs["front"], cv2.COLOR_RGB2BGR)
            cv2.polylines(img, [np.round(mesa["esquinas_px"]).astype(np.int32)], True, (0, 255, 255), 1)
            for t, (i, j) in tecla_a_ij.items():
                x, y = puntos[(i, j)]
                hecho = f"{i},{j}" in datos["posturas"]
                color = (0, 255, 0) if hecho else (0, 0, 255)
                cv2.circle(img, (int(x), int(y)), 7, color, 2)
                cv2.putText(img, t.upper(), (int(x) + 9, int(y) - 7), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            faltan = n_u * n_v - len(datos["posturas"])
            msg = f"Boquilla sobre el punto + su tecla · faltan {faltan} · Q salir"
            cv2.putText(img, msg, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 3)
            cv2.putText(img, msg, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 1)
            cv2.imshow("Grabar posturas mesa", img)

            tecla = cv2.waitKey(30) & 0xFF
            if tecla in (ord("q"), 27):
                break
            c = chr(tecla).lower() if tecla < 128 else ""
            if c in tecla_a_ij:
                i, j = tecla_a_ij[c]
                datos["posturas"][f"{i},{j}"] = {f"{m}.pos": float(obs[f"{m}.pos"]) for m in MOTORES}
                with open(RUTA, "w") as f:
                    json.dump(datos, f, indent=2)
                print(f"✓ Punto {c.upper()} ({i},{j}) guardado")
    except KeyboardInterrupt:
        pass
    finally:
        if args.a_mano and hasattr(robot, "bus"):
            # mantener la postura actual al reactivar el torque
            obs = robot.get_observation()
            robot.send_action({f"{m}.pos": obs[f"{m}.pos"] for m in MOTORES})
            for m in MOTORES:
                robot.bus.write("Torque_Enable", m, 1)
            print("✓ Torque reactivado")
        if teleop is not None:
            teleop.disconnect()
        robot.disconnect()
        cv2.destroyAllWindows()

    faltan = [t.upper() for t, (i, j) in tecla_a_ij.items() if f"{i},{j}" not in datos["posturas"]]
    print(f"\nPosturas de mesa: {n_u * n_v - len(faltan)}/{n_u * n_v}" + (f" · faltan {', '.join(faltan)}" if faltan else " ✅"))


if __name__ == "__main__":
    main()
