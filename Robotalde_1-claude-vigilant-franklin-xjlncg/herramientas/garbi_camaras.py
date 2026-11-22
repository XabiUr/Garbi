"""Cámaras de Garbi en vivo: lista las cámaras, abre `top` y `wrist` a 640 × 480 con exposición, balance y foco fijos
y superpone lo que ve la percepción (tapete, madera, bola naranja, manos, broca, anillo verde) y las máscaras de color
de `garbi/config_vision.yaml`. Sirve para colocar las cámaras, comprobar la luz y guardar capturas para ajustar
umbrales (`garbi_ajustar_color.py --imagen ...`).

    python herramientas/garbi_camaras.py --listar                 # qué cámaras hay (y una foto de cada una)
    python herramientas/garbi_camaras.py --top 0 --wrist 1        # Windows (índices)
    python herramientas/garbi_camaras.py --top /dev/video0 --wrist /dev/video2
    python herramientas/garbi_camaras.py --top 0 --wrist no       # solo la de arriba

Teclas (con la ventana activa):
    s        guardar captura (top y wrist en PNG, sin dibujos) en --carpeta
    m        máscaras de color sí/no          1-6  cada color: 1 tapete, 2 madera, 3 bola, 4 anillo, 5 piel, 6 pegatina
    p        detecciones de la percepción sí/no
    c        recalibrar la cámara de arriba con el tapete
    r        recargar garbi/config_vision.yaml (tras guardar en garbi_ajustar_color.py)
    q / Esc  salir

Si la percepción no se puede calibrar (no ve las 4 esquinas del tapete), se ven al menos las máscaras de color.
Con intrínsecas en `calib/` (garbi_calibrar.py intrinsecas) se corrige la distorsión y se usan sus K.
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

import numpy as np

import garbi_comun as comun  # noqa: F401  (pone la raíz del repositorio en sys.path)
from garbi_comun import COLORES_BGR, a_bgr, mosaico, rotulo, superponer

from garbi.config_vision import COLORES, cargar_config_vision, mascara_hsv  # noqa: E402



def argumentos(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="python herramientas/garbi_camaras.py", description=__doc__,
                                formatter_class=comun.Ayuda)
    p.add_argument("--listar", action="store_true", help="lista las cámaras, guarda una foto de cada una y sale")
    comun.anadir_camaras(p)
    p.add_argument("--carpeta", default="capturas", help="carpeta de las capturas (tecla s)")
    p.add_argument("--config", default=None, help="yaml de umbrales (por defecto garbi/config_vision.yaml)")
    p.add_argument("--calibracion", default="calib", help="carpeta de calib/ (intrínsecas y base del robot)")
    p.add_argument("--sin-percepcion", action="store_true", help="solo máscaras de color")
    return p.parse_args(argv)


# --- dibujos -------------------------------------------------------------------------------------------------------
class Estado:
    """Lo que se ve y la calibración de la cámara de arriba (se recalcula con la tecla c)."""

    def __init__(self, rangos, K_top=None, K_wrist=None, percepcion: bool = True):
        self.rangos = rangos
        self.visibles = {c: True for c in COLORES}
        self.mascaras = True
        self.percepcion = percepcion
        self.K_top, self.K_wrist = K_top, K_wrist
        self.cam = None  # garbi.percepcion.CamaraMesa
        self.madera = None
        self.intentos_cam = 0

    def alternar_color(self, i: int) -> None:
        if 0 <= i < len(COLORES):
            self.visibles[COLORES[i]] = not self.visibles[COLORES[i]]


def _percepcion():
    try:
        from garbi import percepcion

        return percepcion
    except Exception:  # la percepción final puede estar a medias: las máscaras siguen funcionando
        return None


def _detector_manos(estado: Estado):
    """`garbi.manos.ManosColor` con los colores de `estado.rangos` y los parámetros del yaml (se rehace al recargar)."""
    from garbi.config_vision import ConfigVision, config_por_defecto
    from garbi.manos import ManosColor

    clave = id(estado.rangos)
    if getattr(estado, "_manos", None) is None or estado._manos[0] != clave:
        estado._manos = (clave, ManosColor(ConfigVision(estado.rangos, config_por_defecto().parametros)))
    return estado._manos[1]


def anotar_top(img_rgb: np.ndarray, estado: Estado) -> tuple[np.ndarray, list[str]]:
    """Imagen BGR con las máscaras y las detecciones de la cámara de arriba, y las líneas de texto del estado."""
    import cv2

    hsv = cv2.cvtColor(np.ascontiguousarray(img_rgb), cv2.COLOR_RGB2HSV)
    salida = a_bgr(img_rgb).copy()
    lineas = []
    if estado.mascaras:
        for nombre in COLORES:
            if estado.visibles[nombre] and nombre in estado.rangos:
                m = mascara_hsv(hsv, estado.rangos[nombre])
                superponer(salida, m, COLORES_BGR[nombre])
    # manos: el detector de la percepción (garbi.manos.ManosColor, el respaldo de MediaPipe) con los umbrales cargados
    manos = _detector_manos(estado).detectar(img_rgb, estado.cam)
    for h in manos:
        c = h.uv
        cv2.circle(salida, tuple(int(v) for v in c), 18, COLORES_BGR["piel"], 2)
        texto = "mano" + (" (tapete)" if h.en_tapete else "")
        cv2.putText(salida, texto, (int(c[0]) + 20, int(c[1])), cv2.FONT_HERSHEY_SIMPLEX, 0.5, COLORES_BGR["piel"], 1)
    lineas.append(f"manos (piel): {len(manos)}")
    per = _percepcion() if estado.percepcion else None
    if per is None:
        return salida, lineas + (["percepcion: apagada"] if not estado.percepcion else ["percepcion: no carga"])
    # tapete y cámara de arriba
    try:
        quad = per.esquinas_tapete(img_rgb)
    except Exception:
        quad = None
    if quad is not None:
        cv2.polylines(salida, [np.round(quad).astype(np.int32)], True, COLORES_BGR["tapete_azul"], 2)
    if estado.cam is None and quad is not None and estado.intentos_cam < 3:
        estado.intentos_cam += 1
        try:
            estado.cam = per.calibrar_camara_arriba(img_rgb, estado.K_top)
        except Exception:
            estado.cam = None
    lineas.append("tapete: " + ("4 esquinas" if quad is not None else "NO") + " · camara: " +
                  ("calibrada" if estado.cam is not None else "sin calibrar (c)"))
    # madera (necesita la cámara calibrada)
    if estado.cam is not None:
        try:
            madera = per.detectar_madera(img_rgb, estado.cam, estado.madera, _detector_manos(estado).cfg)
        except Exception:
            madera = None
        estado.madera = madera
        if madera is not None:
            esq = per._esquinas_tabla(madera.x, madera.y, madera.giro)
            poli = per._poligono(estado.cam, esq, per.Z_CARA)
            cv2.polylines(salida, [np.round(poli).astype(np.int32)], True, COLORES_BGR["madera"], 2)
        lineas.append("madera: " + ("NO" if madera is None else f"({madera.x:.0f}, {madera.y:.0f}) mm {madera.giro:.0f}°"))
    # bola naranja
    try:
        bola = per.detectar_bola(img_rgb)
    except Exception:
        bola = None
    if bola is not None:
        (u, v), r = bola
        cv2.circle(salida, (int(u), int(v)), max(3, int(r)), COLORES_BGR["bola_naranja"], 2)
        texto = f"bola: ({u:.0f}, {v:.0f}) px r {r:.0f}"
        if estado.cam is not None:
            xy = estado.cam.a_plano(np.array([u, v]), per.Z_BOLA)[0]
            texto += f" → ({xy[0]:.0f}, {xy[1]:.0f}) mm"
        lineas.append(texto)
    else:
        lineas.append("bola: NO")
    # anillo verde de la boquilla
    try:
        from garbi.calibracion import detectar_anillo

        uv = detectar_anillo(img_rgb)
    except Exception:
        uv = None
    if uv is not None:
        cv2.drawMarker(salida, (int(uv[0]), int(uv[1])), COLORES_BGR["anillo_verde"], cv2.MARKER_CROSS, 20, 2)
    lineas.append("anillo: " + ("NO" if uv is None else f"({uv[0]:.0f}, {uv[1]:.0f}) px"))
    return salida, lineas


def anotar_wrist(img_rgb: np.ndarray, estado: Estado) -> tuple[np.ndarray, list[str]]:
    """Imagen BGR de la muñeca con la broca medida (punta y distancia) y la máscara de la bola."""
    import cv2

    salida = a_bgr(img_rgb).copy()
    if estado.mascaras and estado.visibles["bola_naranja"]:
        superponer(salida, mascara_hsv(cv2.cvtColor(np.ascontiguousarray(img_rgb), cv2.COLOR_RGB2HSV),
                                       estado.rangos["bola_naranja"]), COLORES_BGR["bola_naranja"])
    per = _percepcion() if estado.percepcion else None
    if per is None:
        return salida, []
    K = estado.K_wrist if estado.K_wrist is not None else per.intrinsecas(per.FOVY_WRIST, img_rgb.shape[1::-1])
    try:
        medida = per.medir_broca(img_rgb, K)
    except Exception:
        medida = None
    if medida is None:
        return salida, ["broca: NO"]
    u, v = medida.uv_punta
    cv2.drawMarker(salida, (int(u), int(v)), (0, 0, 255), cv2.MARKER_TILTED_CROSS, 18, 2)
    return salida, [f"broca: punta ({u:.0f}, {v:.0f}) px · a {medida.distancia_eje:.0f} mm · {medida.ancho_px:.0f} px"]


# --- programa ------------------------------------------------------------------------------------------------------
def listar(carpeta: Path) -> list[dict]:
    """Cámaras que ve OpenCV (como `lerobot-find-cameras opencv`) y una foto de cada una para saber cuál es cuál."""
    import cv2
    from lerobot.cameras.opencv import OpenCVCamera

    carpeta.mkdir(parents=True, exist_ok=True)
    encontradas = OpenCVCamera.find_cameras()
    if not encontradas:
        print("No veo ninguna cámara. ¿Están enchufadas? En Windows, cierra la app Cámara/Teams/Zoom.")
    for info in encontradas:
        ident = info["id"]
        perfil = info.get("default_stream_profile", {})
        print(f"- {ident}: {perfil.get('width')}×{perfil.get('height')} a {perfil.get('fps')} fps")
        cap = cv2.VideoCapture(ident)
        ok, img = False, None
        for _ in range(10):  # las primeras salen negras
            ok, img = cap.read()
        cap.release()
        if ok:
            nombre = carpeta / f"camara_{Path(str(ident)).name}.png"
            cv2.imwrite(str(nombre), img)
            print(f"  foto: {nombre}")
    return encontradas


def guardar_captura(carpeta: Path, imagenes: dict) -> list[Path]:
    import cv2

    carpeta.mkdir(parents=True, exist_ok=True)
    marca = time.strftime("%Y%m%d_%H%M%S") + f"_{int(time.time() * 1000) % 1000:03d}"
    rutas = []
    for nombre, img in imagenes.items():
        ruta = carpeta / f"{nombre}_{marca}.png"
        cv2.imwrite(str(ruta), a_bgr(img))
        rutas.append(ruta)
    return rutas


def main(argv=None) -> None:
    import cv2

    ns = argumentos(argv)
    if ns.listar:
        listar(Path(ns.carpeta))
        return
    from garbi.real import CorrectorDistorsion, abrir_camaras, cargar_calibracion, cerrar_camaras

    comun.comprobar_ventanas()
    calib = cargar_calibracion(ns.calibracion)
    estado = Estado(cargar_config_vision(ns.config), calib.K("top"), calib.K("wrist"), not ns.sin_percepcion)
    correctores = {c: CorrectorDistorsion(K, d) for c, (K, d) in calib.intrinsecas.items()}
    camaras = abrir_camaras(comun.camaras_desde(ns), comun.ajustes_desde(ns))
    print(__doc__.split("Teclas")[1].split("Si la")[0])
    ventana = "Garbi · camaras"
    cv2.namedWindow(ventana, cv2.WINDOW_NORMAL)
    try:
        while True:
            imgs = {n: c.read_latest() for n, c in camaras.items()}
            imgs = {n: correctores[n](i) if n in correctores else i for n, i in imgs.items()}
            vistas = []
            if "top" in imgs:
                v, lineas = anotar_top(imgs["top"], estado)
                vistas.append(rotulo(v, ["TOP"] + lineas))
            if "wrist" in imgs:
                v, lineas = anotar_wrist(imgs["wrist"], estado)
                vistas.append(rotulo(v, ["WRIST"] + lineas))
            cv2.imshow(ventana, mosaico(vistas))
            tecla = cv2.waitKey(30) & 0xFF
            if tecla in (ord("q"), 27):
                break
            if tecla == ord("s"):
                for r in guardar_captura(Path(ns.carpeta), imgs):
                    print("captura:", r)
            elif tecla == ord("m"):
                estado.mascaras = not estado.mascaras
            elif tecla == ord("p"):
                estado.percepcion = not estado.percepcion
            elif tecla == ord("c"):
                estado.cam, estado.intentos_cam, estado.madera = None, 0, None
            elif tecla == ord("r"):
                estado.rangos = cargar_config_vision(ns.config)
                print("umbrales recargados")
            elif ord("1") <= tecla <= ord("6"):
                estado.alternar_color(tecla - ord("1"))
    finally:
        cerrar_camaras(camaras)
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
