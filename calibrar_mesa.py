#!/usr/bin/env python3
"""
calibrar_mesa.py - Marca el ÁREA DE LA MESA donde puede estar la tabla → mesa.json.

Solo imagen: no hace falta el robot ni el taladro. Es independiente de zona.json (la zona del morado).

Haz clic en las 4 esquinas del área donde puede ponerse la tabla (todo el tapete útil), en el mismo orden que la zona:
    1 delante-izq · 2 delante-der · 3 detrás-der · 4 detrás-izq
Los puntos están en el plano de la mesa, así que no hay paralaje. Se dibuja la rejilla de posturas de barrido
(3×3 por defecto) que luego se graban con grabar_posturas_mesa.py.

Teclas: clic = esquina · R = borrar · G = guardar mesa.json · Q / ESC = salir

Uso:
    python calibrar_mesa.py              # cámara front de config.json
    python calibrar_mesa.py --camara 1
    python calibrar_mesa.py --imagen fotos_madera/xxx.png
"""

import argparse
import json
import time

import cv2
import numpy as np

ORDEN = ["delante-izq", "delante-der", "detras-der", "detras-izq"]


def puntos_rejilla_px(esquinas_px: np.ndarray, n_u: int, n_v: int):
    """{(i,j): (x,y)} de la rejilla n_u × n_v sobre el área (homografía (u,v) → px)."""
    H = cv2.getPerspectiveTransform(np.array([[0, 0], [1, 0], [1, 1], [0, 1]], np.float32),
                                    np.asarray(esquinas_px, np.float32))
    out = {}
    for j in range(n_v):
        for i in range(n_u):
            uv = np.array([[[i / (n_u - 1), j / (n_v - 1)]]], np.float32)
            out[(i, j)] = tuple(cv2.perspectiveTransform(uv, H)[0, 0])
    return out


def main():
    ap = argparse.ArgumentParser(description="Marcar el área de la mesa para el barrido")
    ap.add_argument("--camara", type=int, default=None)
    ap.add_argument("--imagen", type=str, default=None)
    ap.add_argument("--n-u", type=int, default=3, help="columnas de la rejilla de barrido")
    ap.add_argument("--n-v", type=int, default=3, help="filas de la rejilla de barrido")
    args = ap.parse_args()

    config = json.load(open("config.json"))
    cap, foto = None, None
    if args.imagen:
        foto = cv2.imread(args.imagen)
    else:
        cam = config["robot"]["cameras"]["front"]
        indice = args.camara if args.camara is not None else cam["index_or_path"]
        cap = cv2.VideoCapture(indice)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, cam["width"])
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cam["height"])
        if not cap.isOpened():
            raise SystemExit(f"No puedo abrir la cámara {indice}")

    clics = []

    def raton(evento, x, y, *_):
        if evento == cv2.EVENT_LBUTTONDOWN and len(clics) < 4:
            clics.append((float(x), float(y)))
            print(f"  {len(clics)} {ORDEN[len(clics) - 1]}: ({x}, {y})")

    VENT = "Calibrar mesa"
    cv2.namedWindow(VENT)
    cv2.setMouseCallback(VENT, raton)
    print(__doc__)

    while True:
        if cap is not None:
            ok, bgr = cap.read()
            if not ok:
                time.sleep(0.03)
                continue
        else:
            bgr = foto.copy()
        img = bgr.copy()
        for k, c in enumerate(clics):
            cv2.circle(img, (int(c[0]), int(c[1])), 6, (0, 255, 255), -1)
            cv2.putText(img, str(k + 1), (int(c[0]) + 8, int(c[1]) - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        if len(clics) == 4:
            cv2.polylines(img, [np.round(clics).astype(np.int32)], True, (0, 255, 255), 2)
            for (i, j), (x, y) in puntos_rejilla_px(np.array(clics), args.n_u, args.n_v).items():
                n = "123456789ABCDEF"[j * args.n_u + i] if j * args.n_u + i < 15 else "?"
                cv2.circle(img, (int(x), int(y)), 5, (255, 255, 0), -1)
                cv2.putText(img, n, (int(x) + 6, int(y) + 16), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
            msg = "G = guardar   R = repetir"
        else:
            msg = f"Clic en esquina {len(clics) + 1}: {ORDEN[len(clics)]}"
        cv2.putText(img, msg, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 3)
        cv2.putText(img, msg, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1)
        cv2.imshow(VENT, img)

        tecla = cv2.waitKey(30) & 0xFF
        if tecla in (ord("q"), 27):
            print("Salgo sin guardar")
            break
        elif tecla == ord("r"):
            clics.clear()
        elif tecla == ord("g") and len(clics) == 4:
            datos = {"esquinas_px": clics, "orden": ", ".join(ORDEN),
                     "rejilla": {"n_u": args.n_u, "n_v": args.n_v},
                     "nota": "Área de la mesa para el barrido (plano de la mesa, sin paralaje)",
                     "fecha": time.strftime("%Y-%m-%d %H:%M:%S")}
            with open("mesa.json", "w") as f:
                json.dump(datos, f, indent=2)
            print("✓ Guardado mesa.json. Ahora: python grabar_posturas_mesa.py --real --a-mano")
            break

    if cap is not None:
        cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
