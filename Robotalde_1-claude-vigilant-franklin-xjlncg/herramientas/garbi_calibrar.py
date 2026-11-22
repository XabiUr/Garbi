"""Calibración de Garbi en el sitio (especificación técnica, M2). Todo se guarda en `calib/` (--carpeta).

    # (a) intrínsecas de cada cámara con el tablero de ajedrez (9 × 6 esquinas interiores, cuadros de 25 mm)
    python herramientas/garbi_calibrar.py intrinsecas --camara top --indice 0
    python herramientas/garbi_calibrar.py intrinsecas --camara wrist --indice 1 --fotos 15
    python herramientas/garbi_calibrar.py intrinsecas --camara top --desde calib/tablero_top   # con fotos ya hechas

    # (b) cámara de arriba respecto a la mesa, con las 4 esquinas del tapete azul
    python herramientas/garbi_calibrar.py arriba --top 0

    # (c) robot respecto a la mesa: el follower lleva el anillo verde a 9 posturas + 5 de comprobación
    python herramientas/garbi_calibrar.py robot --puerto COM5 --top 0

Salidas:
    calib/top.yaml, calib/wrist.yaml     K, distorsión, error de reproyección (objetivo < 0,5 px)
    calib/tablero_<cam>/                 fotos del tablero usadas
    calib/camara_arriba.yaml, arriba.png pose de la cámara de arriba (R, t, centro) y las esquinas vistas
    calib/robot.yaml                     base del robot en la mesa (x, y, giro), residuos y errores de comprobación
    calib/robot/                         la foto de arriba en cada postura

(a) Teclas: espacio = foto (solo si ve el tablero), a = automático (una foto cada 1,5 s si ve el tablero y se ha
movido), q = terminar y calibrar con las que haya (mínimo 8). Mueve el tablero por toda la imagen, inclinado y a
distintas distancias.
(c) Antes de cada movimiento pide Enter («n» salta esa postura; --seguido pregunta una sola vez). Velocidad baja
(--velocidad). Ctrl+C: el brazo se queda quieto donde está y no se guarda la calibración del robot. Quita el taladro del tapete; la
madera puede quedarse. Criterio: error de comprobación < 4 mm en las 5 posturas.
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

import numpy as np

import garbi_comun as comun

TABLERO = (9, 6)  # esquinas interiores
LADO_CUADRO = 25.0  # mm
FOTOS = 15
FOTOS_MIN = 8
ERROR_RMS_OBJETIVO = 0.5  # px
PAUSA_FOTO = 0.6  # s de espera tras llegar a una postura antes de la foto (que pare de vibrar)


def argumentos(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="python herramientas/garbi_calibrar.py", description=__doc__,
                                formatter_class=comun.Ayuda)
    p.add_argument("--carpeta", default="calib", help="carpeta de la calibración")
    sub = p.add_subparsers(dest="paso", required=True)

    a = sub.add_parser("intrinsecas", help="(a) K y distorsión con el tablero de ajedrez",
                       formatter_class=comun.Ayuda)
    a.add_argument("--camara", choices=("top", "wrist"), required=True)
    a.add_argument("--indice", default="0", help="índice o ruta de la cámara")
    a.add_argument("--fotos", type=int, default=FOTOS)
    a.add_argument("--tablero", default=f"{TABLERO[0]}x{TABLERO[1]}", help="esquinas interiores COLUMNASxFILAS")
    a.add_argument("--lado", type=float, default=LADO_CUADRO, help="lado del cuadro (mm)")
    a.add_argument("--desde", help="carpeta con fotos del tablero ya hechas (no abre la cámara)")

    b = sub.add_parser("arriba", help="(b) cámara de arriba con el tapete", formatter_class=comun.Ayuda)
    b.add_argument("--top", default="0", help="índice o ruta de la cámara de arriba")
    b.add_argument("--imagen", help="usar esta foto en vez de la cámara")

    c = sub.add_parser("robot", help="(c) base del robot con el anillo verde", formatter_class=comun.Ayuda)
    comun.anadir_robot(c)
    c.add_argument("--top", default="0", help="índice o ruta de la cámara de arriba")
    c.add_argument("--velocidad", type=float, default=15.0, help="°/s entre posturas")
    c.add_argument("--seguido", action="store_true", help="pedir Enter solo una vez, al empezar")
    for sp in (a, b, c):
        sp.add_argument("--exposicion", type=float, default=15.6, help="exposición fija en ms")
        sp.add_argument("--balance", type=int, default=4000, help="balance de blancos fijo (K)")
        sp.add_argument("--foco", type=int, default=0, help="foco fijo")
    return p.parse_args(argv)


def _tablero(texto: str) -> tuple[int, int]:
    c, f = str(texto).lower().split("x")
    return int(c), int(f)


# --- (a) intrínsecas ---------------------------------------------------------------------------------------------
def buscar_tablero(img_rgb: np.ndarray, tablero=TABLERO) -> np.ndarray | None:
    """Esquinas interiores del tablero (Nx1x2, refinadas por debajo del píxel) o None."""
    import cv2

    gris = cv2.cvtColor(np.ascontiguousarray(img_rgb), cv2.COLOR_RGB2GRAY)
    ok, esquinas = cv2.findChessboardCorners(gris, tablero, cv2.CALIB_CB_ADAPTIVE_THRESH +
                                             cv2.CALIB_CB_NORMALIZE_IMAGE + cv2.CALIB_CB_FAST_CHECK)
    if not ok:
        return None
    criterio = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 1e-3)
    return cv2.cornerSubPix(gris, esquinas, (11, 11), (-1, -1), criterio)


def calibrar_intrinsecas(imagenes: list[np.ndarray], tablero=TABLERO, lado: float = LADO_CUADRO):
    """`cv2.calibrateCamera` con las fotos donde se ve el tablero. Devuelve (K, dist, rms px, fotos usadas)."""
    import cv2

    objeto = np.zeros((tablero[0] * tablero[1], 3), np.float32)
    objeto[:, :2] = np.mgrid[0:tablero[0], 0:tablero[1]].T.reshape(-1, 2) * lado
    pts_obj, pts_img, tam = [], [], None
    for img in imagenes:
        esq = buscar_tablero(img, tablero)
        if esq is None:
            continue
        pts_obj.append(objeto)
        pts_img.append(esq)
        tam = (img.shape[1], img.shape[0])
    if len(pts_img) < 3:
        raise ValueError(f"solo {len(pts_img)} fotos con el tablero visible: hacen falta más")
    rms, K, dist, _, _ = cv2.calibrateCamera(pts_obj, pts_img, tam, None, None)
    return K, dist.reshape(-1), float(rms), len(pts_img)


def leer_carpeta(carpeta) -> list[np.ndarray]:
    import cv2

    imgs = []
    for ruta in sorted(Path(carpeta).glob("*")):
        if ruta.suffix.lower() in (".png", ".jpg", ".jpeg", ".bmp"):
            bgr = cv2.imread(str(ruta))
            if bgr is not None:
                imgs.append(np.ascontiguousarray(bgr[..., ::-1]))
    return imgs


def capturar_tablero(camara, carpeta: Path, n: int, tablero) -> list[np.ndarray]:
    """Ventana en vivo para hacer las fotos del tablero (teclas en la ayuda)."""
    import cv2

    comun.comprobar_ventanas()
    carpeta.mkdir(parents=True, exist_ok=True)
    fotos, auto, t_ultima, ultima = [], False, 0.0, None
    ventana = "Garbi · tablero"
    cv2.namedWindow(ventana, cv2.WINDOW_NORMAL)
    try:
        while len(fotos) < n:
            img = camara.read_latest()
            esq = buscar_tablero(img, tablero)
            vista = comun.a_bgr(img).copy()
            if esq is not None:
                cv2.drawChessboardCorners(vista, tablero, esq, True)
            comun.rotulo(vista, [f"fotos {len(fotos)}/{n}" + (" · AUTO" if auto else ""),
                                 "espacio foto · a auto · q terminar", "tablero: " + ("SI" if esq is not None else "no")])
            cv2.imshow(ventana, vista)
            tecla = cv2.waitKey(30) & 0xFF
            if tecla in (ord("q"), 27):
                break
            if tecla == ord("a"):
                auto = not auto
            movido = ultima is None or (esq is not None and float(np.mean(np.linalg.norm(esq - ultima, axis=2))) > 25)
            if esq is not None and (tecla == ord(" ") or (auto and time.time() - t_ultima > 1.5 and movido)):
                fotos.append(img.copy())
                ultima, t_ultima = esq, time.time()
                cv2.imwrite(str(carpeta / f"tablero_{len(fotos):02d}.png"), comun.a_bgr(img))
                print(f"foto {len(fotos)}/{n}")
    finally:
        cv2.destroyWindow(ventana)
    return fotos


def paso_intrinsecas(ns) -> Path:
    from garbi.real import abrir_camaras, cerrar_camaras, guardar_intrinsecas

    carpeta = Path(ns.carpeta)
    tablero = _tablero(ns.tablero)
    if ns.desde:
        fotos = leer_carpeta(ns.desde)
    else:
        camaras = abrir_camaras({ns.camara: comun.fuente_camara(ns.indice)}, comun.ajustes_desde(ns))
        try:
            fotos = capturar_tablero(camaras[ns.camara], carpeta / f"tablero_{ns.camara}", ns.fotos, tablero)
        finally:
            cerrar_camaras(camaras)
    if len(fotos) < FOTOS_MIN:
        print(f"aviso: solo {len(fotos)} fotos (mejor ≥ {FOTOS_MIN})")
    K, dist, rms, usadas = calibrar_intrinsecas(fotos, tablero, ns.lado)
    ruta = guardar_intrinsecas(carpeta / f"{ns.camara}.yaml", K, dist, fotos[0].shape[1::-1], rms, usadas)
    estado = "OK" if rms < ERROR_RMS_OBJETIVO else "ALTO: repite con más fotos y el tablero bien plano"
    print(f"{ns.camara}: fx {K[0, 0]:.1f} fy {K[1, 1]:.1f} cx {K[0, 2]:.1f} cy {K[1, 2]:.1f} · reproyección "
          f"{rms:.3f} px ({estado}) · {usadas} fotos → {ruta}")
    return ruta


# --- (b) cámara de arriba ----------------------------------------------------------------------------------------
def calibrar_arriba(img_rgb: np.ndarray, K: np.ndarray | None):
    """`percepcion.calibrar_camara_arriba` y lo que hay que comprobar: dónde queda la cámara frente a la nominal (M1).
    Devuelve (CamaraMesa | None, informe dict)."""
    from garbi import contrato as g
    from garbi import percepcion as per

    cam = per.calibrar_camara_arriba(img_rgb, K)
    quad = per.esquinas_tapete(img_rgb)
    informe = {"esquinas_px": None if quad is None else np.round(quad, 2).tolist()}
    if cam is not None:
        informe.update(R=np.round(cam.R, 6).tolist(), t=np.round(cam.t, 3).tolist(),
                       centro_mm=np.round(cam.centro, 1).tolist(),
                       desvio_nominal_mm=round(float(np.linalg.norm(cam.centro - np.asarray(g.CAMARA_FIJA_POS))), 1))
    return cam, informe


def paso_arriba(ns) -> Path:
    import cv2
    import yaml

    from garbi.real import CorrectorDistorsion, abrir_camaras, cargar_calibracion, cerrar_camaras

    carpeta = Path(ns.carpeta)
    calib = cargar_calibracion(carpeta)
    if ns.imagen:
        img = np.ascontiguousarray(cv2.imread(ns.imagen)[..., ::-1])
    else:
        camaras = abrir_camaras({"top": comun.fuente_camara(ns.top)}, comun.ajustes_desde(ns))
        try:
            time.sleep(1.0)
            img = camaras["top"].read_latest()
        finally:
            cerrar_camaras(camaras)
    if "top" in calib.intrinsecas:
        img = CorrectorDistorsion(*calib.intrinsecas["top"])(img)
    else:
        print("aviso: sin calib/top.yaml uso la K nominal de la simulación (haz antes «intrinsecas --camara top»)")
    cam, informe = calibrar_arriba(img, calib.K("top"))
    carpeta.mkdir(parents=True, exist_ok=True)
    vista = comun.a_bgr(img).copy()
    if informe["esquinas_px"] is not None:
        cv2.polylines(vista, [np.round(np.array(informe["esquinas_px"])).astype(np.int32)], True, (255, 120, 0), 2)
    cv2.imwrite(str(carpeta / "arriba.png"), vista)
    ruta = carpeta / "camara_arriba.yaml"
    ruta.write_text("# Cámara de arriba en la mesa: p_cam = R · p_mesa + t (mm). Se recalcula al arrancar con el "
                    "tapete; esto es la comprobación.\n" + yaml.safe_dump(informe, sort_keys=False), encoding="utf-8")
    if cam is None:
        print("NO veo las 4 esquinas del tapete: mira calib/arriba.png; ajusta tapete_azul con "
              "garbi_ajustar_color.py o mueve la cámara para que el tapete entre entero.")
    else:
        print(f"cámara de arriba en {informe['centro_mm']} mm (a {informe['desvio_nominal_mm']} mm de la nominal) → "
              f"{ruta}. Compruébalo: mide con regla 4 puntos (±2 mm).")
    return ruta


# --- (c) robot respecto a la mesa --------------------------------------------------------------------------------
class IrYMirar:
    """`ir_y_mirar(q)` para `garbi.calibracion.calibrar_robot` con el robot real: pide Enter, mueve despacio, espera a
    que pare y devuelve la foto de arriba (y la guarda). Si se salta la postura, devuelve una imagen negra (el anillo
    no se ve y esa postura no cuenta)."""

    def __init__(self, cuerpo, carpeta: Path | None, velocidad: float, preguntar: bool = True, entrada=input,
                 dormir=time.sleep, nombres=None):
        self.cuerpo = cuerpo
        self.carpeta = carpeta
        self.velocidad = velocidad
        self.preguntar = preguntar
        self.entrada = entrada
        self.dormir = dormir
        self.nombres = list(nombres or [])
        self.i = 0
        self.errores_llegada: list[float] = []

    def __call__(self, q) -> np.ndarray:
        import cv2

        nombre = self.nombres[self.i] if self.i < len(self.nombres) else f"postura {self.i + 1}"
        self.i += 1
        if self.preguntar and not comun.confirmar(f"¿Ir a {nombre} {np.round(q[:4], 1).tolist()}?", self.entrada):
            self.errores_llegada.append(np.nan)
            return np.zeros((480, 640, 3), np.uint8)
        err = comun.mover_despacio(self.cuerpo, q, self.velocidad, dormir=self.dormir)
        self.errores_llegada.append(err)
        self.dormir(PAUSA_FOTO)
        img = self.cuerpo.imagenes()["top"]
        if self.carpeta is not None:
            self.carpeta.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(self.carpeta / f"postura_{self.i:02d}.png"), comun.a_bgr(img))
        return img


def informe_robot(r) -> list[str]:
    """Texto del resultado de `calibrar_robot` (None si no vio el anillo en ≥ 4 posturas)."""
    from garbi.calibracion import ERROR_MAXIMO

    if r is None:
        return ["FALLO: el anillo verde se vio en menos de 4 posturas. Revisa anillo_verde con garbi_ajustar_color.py "
                "y que la cámara de arriba vea la boquilla."]
    lineas = [f"base del robot en la mesa: x {r.base.x:.1f} mm, y {r.base.y:.1f} mm, giro {r.base.giro:.2f}° "
              f"(anillo visto en {r.vistas}/9)",
              "residuos (9 de calibración): " + ", ".join(f"{e:.1f}" for e in r.residuos) + " mm"]
    for k, e in enumerate(r.errores, 1):
        marca = "ok" if np.isfinite(e) and e < ERROR_MAXIMO else "MAL"
        lineas.append(f"  comprobación {k}: " + ("anillo no visto" if not np.isfinite(e) else f"{e:.1f} mm") + f"  {marca}")
    lineas.append(("OK" if r.ok else "NO VALE") + f": máximo {np.max(r.errores):.1f} mm (criterio < {ERROR_MAXIMO} mm)")
    return lineas


def paso_robot(ns, fabrica_cuerpo=None, entrada=input, dormir=time.sleep):
    """(c). `fabrica_cuerpo(ns, calib)` para los tests."""
    from garbi.calibracion import POSTURAS_CALIBRACION, POSTURAS_COMPROBACION, CinematicaRobot, calibrar_robot
    from garbi.lateral import APARCADO
    from garbi.real import CuerpoReal, cargar_calibracion, guardar_base

    carpeta = Path(ns.carpeta)
    calib = cargar_calibracion(carpeta)
    if fabrica_cuerpo is None:
        cuerpo = CuerpoReal(ns.puerto, ns.id, camaras={"top": comun.fuente_camara(ns.top)},
                            ajustes=comun.ajustes_desde(ns), intrinsecas={k: v for k, v in calib.intrinsecas.items()
                                                                          if k == "top"})
        cuerpo.conectar()
    else:
        cuerpo = fabrica_cuerpo(ns, calib)
    resultado = None
    try:
        from garbi import percepcion as per
        from garbi.mundo import MundoGarbi

        dormir(1.0)
        cam = per.calibrar_camara_arriba(cuerpo.imagenes()["top"], calib.K("top"))
        if cam is None:
            raise SystemExit("No veo las 4 esquinas del tapete con la cámara de arriba: haz antes «arriba».")
        cin = CinematicaRobot(MundoGarbi(render=False, montaje="lateral").modelo)
        preguntar_cada = not ns.seguido
        if ns.seguido and not comun.confirmar("Se moverá por 14 posturas sin preguntar. ¿Seguir?", entrada):
            return None
        if comun.confirmar("¿Ir primero al APARCADO?", entrada) if preguntar_cada else True:
            comun.mover_despacio(cuerpo, APARCADO, ns.velocidad, dormir=dormir)
        nombres = ([f"calibración {k}/9" for k in range(1, 10)] + [f"comprobación {k}/5" for k in range(1, 6)])
        ir = IrYMirar(cuerpo, carpeta / "robot", ns.velocidad, preguntar_cada, entrada, dormir, nombres)
        resultado = calibrar_robot(ir, cam, cin, POSTURAS_CALIBRACION, POSTURAS_COMPROBACION)
        for linea in informe_robot(resultado):
            print(linea)
        if resultado is not None:
            ruta = guardar_base(carpeta / "robot.yaml", resultado.base, resultado.residuos, resultado.errores)
            print("guardado en", ruta)
        if comun.confirmar("¿Volver al APARCADO?", entrada) if preguntar_cada else True:
            comun.mover_despacio(cuerpo, APARCADO, ns.velocidad, dormir=dormir)
    except KeyboardInterrupt:
        print("\nCtrl+C: brazo quieto donde está; no se guarda la calibración del robot")
        comun.parar_quieto(cuerpo)
    finally:
        cuerpo.cerrar()
    return resultado


def main(argv=None) -> None:
    ns = argumentos(argv)
    {"intrinsecas": paso_intrinsecas, "arriba": paso_arriba, "robot": paso_robot}[ns.paso](ns)


if __name__ == "__main__":
    main()
