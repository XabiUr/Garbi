#!/usr/bin/env python3
"""
calibrar_boquilla.py - Calibración del barrido por cinemática inversa → boquilla.json. Independiente del taladro.

FASE 1 · PIVOTE (dónde está la punta de la boquilla respecto a la muñeca)
    Marca un punto en la mesa (una cruz). Apoya la PUNTA de la boquilla en él y pulsa ESPACIO.
    Cambia la inclinación (muñeca/codo, y si puedes el giro de la base) SIN mover la punta del punto y pulsa ESPACIO.
    Repite hasta 4-6 posturas lo más distintas posible. N = calcular y pasar a la fase 2.
    Te dice el error en mm: si es > 5 mm, R y repite con inclinaciones más variadas.
    S = saltar el pivote y usar una punta aproximada (--punta X Y Z en cm, por defecto 0.4 0.2 -14.5). Vale para
    barrer porque el barrido mantiene la inclinación de los toques: lo que cuenta es el error de los toques.

FASE 2 · TOQUES (relación cámara ↔ mesa)
    Apoya la punta en un punto de la mesa, haz CLIC en la imagen justo donde está la punta y pulsa ESPACIO.
    Repite en 5-8 puntos REPARTIDOS por toda la zona donde puede ir la tabla (esquinas, centro), con la boquilla
    INCLINADA COMO QUIERES QUE BARRA (más o menos igual en todos los toques).
    G = guardar boquilla.json (te dice el error de cada toque; si alguno pasa de 12 mm te avisa: Z borra el último
    toque, o pulsa G otra vez para guardar igualmente).

Otras teclas: R = repetir la fase actual · Q / ESC = salir sin guardar

Uso:
    python calibrar_boquilla.py --real --a-mano    # mueves el brazo a mano (torque desactivado)
    python calibrar_boquilla.py --real             # con el líder
"""

import argparse
import json
import time

import cv2
import numpy as np

from cinematica import Cinematica, resolver_pivote, resolver_pivote_con_desfases
from grabar_posturas import crear_robot_y_teleop

MOTORES = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"]


def ajustar_toques(cin: Cinematica, toques):
    """Homografía px → (x,y) del robot, plano z(x,y) y error de cada toque (mm)."""
    px = np.array([t["px"] for t in toques], np.float32)
    xyz = np.array([cin.punta(t["postura"]) for t in toques])
    H, _ = cv2.findHomography(px, xyz[:, :2].astype(np.float32), 0)
    A = np.c_[xyz[:, 0], xyz[:, 1], np.ones(len(xyz))]
    plano, *_ = np.linalg.lstsq(A, xyz[:, 2], rcond=None)
    xy_pred = cv2.perspectiveTransform(px.reshape(-1, 1, 2), H).reshape(-1, 2)
    err_xy = np.linalg.norm(xy_pred - xyz[:, :2], axis=1) * 1000
    err_z = np.abs(A @ plano - xyz[:, 2]) * 1000
    return H, plano, err_xy, err_z


def main():
    ap = argparse.ArgumentParser(description="Calibrar la boquilla para el barrido por cinemática inversa")
    ap.add_argument("--sin-robot", action="store_true")
    ap.add_argument("--real", action="store_true")
    ap.add_argument("--a-mano", action="store_true")
    ap.add_argument("--punta", type=float, nargs=3, default=[0.4, 0.2, -14.5], metavar=("X", "Y", "Z"),
                    help="punta aproximada en cm (si te saltas el pivote con S)")
    args = ap.parse_args()
    if not (args.sin_robot or args.real):
        raise SystemExit("❌ Debes especificar --sin-robot o --real")

    config = json.load(open("config.json"))
    cin = Cinematica()
    robot, teleop = crear_robot_y_teleop(config, args.sin_robot, args.a_mano)
    robot.connect(calibrate=False)
    if args.a_mano and hasattr(robot, "bus"):
        for m in MOTORES:
            robot.bus.write("Torque_Enable", m, 0)
    elif teleop is not None:
        teleop.connect()
    print(__doc__)

    est = {"fase": 1, "pivote": [], "toques": [], "clic": None, "tcp": None}

    def raton(evento, x, y, *_):
        if evento == cv2.EVENT_LBUTTONDOWN and est["fase"] == 2:
            est["clic"] = (float(x), float(y))

    VENT = "Calibrar boquilla"
    cv2.namedWindow(VENT)
    cv2.setMouseCallback(VENT, raton)
    guardado = False
    try:
        while True:
            obs = robot.get_observation()
            if teleop is not None and not args.a_mano:
                robot.send_action(teleop.get_action())
            postura = {f"{m}.pos": float(obs[f"{m}.pos"]) for m in MOTORES}
            img = cv2.cvtColor(obs["front"], cv2.COLOR_RGB2BGR)

            if est["fase"] == 1:
                msg = f"PIVOTE: punta en la marca + ESPACIO ({len(est['pivote'])}) · N = calcular · S = saltar"
            else:
                for t in est["toques"]:
                    cv2.circle(img, (int(t["px"][0]), int(t["px"][1])), 6, (0, 255, 0), 2)
                if est["clic"]:
                    cv2.drawMarker(img, (int(est["clic"][0]), int(est["clic"][1])), (0, 0, 255), cv2.MARKER_CROSS, 16, 2)
                msg = f"TOQUES: punta en la mesa, CLIC en la punta + ESPACIO ({len(est['toques'])}) · G = guardar"
            cv2.putText(img, msg, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 3)
            cv2.putText(img, msg, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
            cv2.imshow(VENT, img)

            tecla = cv2.waitKey(30) & 0xFF
            if tecla in (ord("q"), 27):
                break
            elif tecla == ord("r"):
                est["pivote" if est["fase"] == 1 else "toques"] = []
                est["clic"] = None
                print("[Boquilla] fase reiniciada")
            elif tecla == ord("s") and est["fase"] == 1:
                est["tcp"] = np.array(args.punta) / 100.0
                est["desfases"] = [0.0] * 5
                cin.tcp = est["tcp"]
                est["fase"] = 2
                print(f"[Pivote] saltado: uso la punta aproximada {args.punta} cm. "
                      "Lo que cuenta es el error de los toques (al guardar)")
            elif tecla == ord(" ") and est["fase"] == 1:
                est["pivote"].append(postura)
                print(f"[Pivote] postura {len(est['pivote'])} guardada")
            elif tecla == ord("n") and est["fase"] == 1:
                if len(est["pivote"]) < 3:
                    print("[Pivote] hacen falta al menos 3 posturas (mejor 4-6)")
                    continue
                with open("pivote.json", "w") as f:   # para poder analizarlo si sale mal
                    json.dump(est["pivote"], f, indent=2)
                t, p, err = resolver_pivote(cin, est["pivote"])
                print(f"[Pivote] sin corregir el modelo: punta = {np.round(t * 100, 1).tolist()} cm · "
                      f"error (mm): {np.round(err * 1000, 1).tolist()}")
                est["desfases"] = [0.0] * 5
                if err.max() > 0.005 and len(est["pivote"]) >= 6:
                    t, p, d, err = resolver_pivote_con_desfases(cin, est["pivote"])
                    est["desfases"] = d.tolist()
                    print(f"[Pivote] corrigiendo el modelo: desfases hombro/codo/muñeca = "
                          f"{np.round(d[1:4], 1).tolist()}° · punta = {np.round(t * 100, 1).tolist()} cm · "
                          f"error (mm): {np.round(err * 1000, 1).tolist()}")
                elif err.max() > 0.005:
                    print("   Con 6 o más posturas puedo corregir el modelo: pulsa R y haz 8 posturas variadas")
                if err.max() > 0.005:
                    print("⚠️  Error > 5 mm: R y repite (punta bien quieta, inclinaciones más distintas)")
                    continue
                est["tcp"] = t
                cin.tcp = t
                est["fase"] = 2
            elif tecla == ord("z") and est["fase"] == 2 and est["toques"]:
                est["toques"].pop()
                est["aviso_dado"] = False
                print(f"[Toques] último toque borrado (quedan {len(est['toques'])})")
            elif tecla == ord(" ") and est["fase"] == 2:
                if est["clic"] is None:
                    print("[Toques] haz clic en la imagen donde está la punta")
                    continue
                est["toques"].append({"px": list(est["clic"]), "postura": postura})
                est["clic"] = None
                print(f"[Toques] toque {len(est['toques'])} guardado: punta en "
                      f"{np.round(cin.punta(postura) * 100, 1).tolist()} cm")
            elif tecla == ord("g") and est["fase"] == 2:
                if len(est["toques"]) < 4:
                    print("[Toques] hacen falta al menos 4 toques (mejor 5-8)")
                    continue
                H, plano, exy, ez = ajustar_toques(cin, est["toques"])
                print(f"[Toques] error en la mesa (mm): {np.round(exy, 1).tolist()} · altura (mm): {np.round(ez, 1).tolist()}")
                malos = [i + 1 for i, (a_, b_) in enumerate(zip(exy, ez)) if a_ > 12 or b_ > 12]
                if malos:
                    print(f"⚠️  Toques con más de 12 mm de error: {malos}. Z = borrar el último toque · "
                          "o sigue añadiendo y vuelve a pulsar G. Para guardar igualmente pulsa G otra vez.")
                    if not est.get("aviso_dado"):
                        est["aviso_dado"] = True
                        continue
                datos = {"tcp": est["tcp"].tolist(), "desfases": est.get("desfases", [0.0] * 5), "pivote": est["pivote"], "toques": est["toques"],
                         "fecha": time.strftime("%Y-%m-%d %H:%M:%S")}
                with open("boquilla.json", "w") as f:
                    json.dump(datos, f, indent=2)
                print("✓ Guardado boquilla.json")
                guardado = True
                break
    except KeyboardInterrupt:
        pass
    finally:
        if args.a_mano and hasattr(robot, "bus"):
            obs = robot.get_observation()
            robot.send_action({f"{m}.pos": obs[f"{m}.pos"] for m in MOTORES})
            for m in MOTORES:
                robot.bus.write("Torque_Enable", m, 1)
        if teleop is not None:
            teleop.disconnect()
        robot.disconnect()
        cv2.destroyAllWindows()
    if not guardado:
        print("Salgo sin guardar")


if __name__ == "__main__":
    main()
