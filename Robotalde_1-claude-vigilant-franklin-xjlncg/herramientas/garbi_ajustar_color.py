"""Ajuste de los umbrales de color de Garbi con deslizadores HSV; escribe `garbi/config_vision.yaml`, que leen la
percepción y las demás herramientas.

    python herramientas/garbi_ajustar_color.py --imagen capturas/top_20261120_101500_123.png
    python herramientas/garbi_ajustar_color.py --camara 0            # en vivo (Windows: índice; Linux: 0 o /dev/video0)
    python herramientas/garbi_ajustar_color.py --camara 0 --color bola_naranja

Colores (nombres fijos del yaml): tapete_azul, madera, bola_naranja, anillo_verde, piel, pegatina.

Teclas (con la ventana activa):
    n / p    color siguiente / anterior
    clic     pincha el objeto en la imagen: el rango se centra en ese píxel (mediana de 7 × 7 ± margen)
    s        guardar el yaml (todos los colores)
    z        deshacer: volver a lo que había en el yaml al abrir este color
    espacio  (en vivo) congelar / seguir la imagen
    q / Esc  salir (pregunta si hay cambios sin guardar en la terminal)

Deslizadores: H mín/máx (0-179), S mín/máx, V mín/máx (0-255). Si H mín > H máx, el tono da la vuelta (piel, rojo).
Consejo: ajusta con la luz de la demo y el flexo encendido; que la máscara cubra el objeto entero y nada del fondo.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

import garbi_comun as comun
from garbi_comun import COLORES_BGR, a_bgr, mosaico, rotulo, superponer

from garbi.config_vision import (COLORES, RUTA_DEFECTO, RangoHSV, cargar_config_vision,  # noqa: E402
                                 guardar_config_vision, mascara_hsv, rango_desde_muestra)

VENTANA = "Garbi · ajustar color"
DESLIZADORES = (("H min", 179), ("H max", 179), ("S min", 255), ("S max", 255), ("V min", 255), ("V max", 255))
LADO_MUESTRA = 7


def argumentos(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="python herramientas/garbi_ajustar_color.py", description=__doc__,
                                formatter_class=comun.Ayuda)
    fuente = p.add_mutually_exclusive_group(required=True)
    fuente.add_argument("--imagen", help="captura PNG/JPG (de garbi_camaras.py, tecla s)")
    fuente.add_argument("--camara", help="índice o ruta de la cámara, en vivo (con los ajustes fijos)")
    p.add_argument("--color", choices=COLORES, default=COLORES[0], help="color con el que empezar")
    p.add_argument("--salida", default=str(RUTA_DEFECTO), help="yaml de umbrales que se lee y se escribe")
    p.add_argument("--exposicion", type=float, default=15.6, help="(en vivo) exposición fija en ms")
    p.add_argument("--balance", type=int, default=4000, help="(en vivo) balance de blancos fijo (K)")
    p.add_argument("--foco", type=int, default=0, help="(en vivo) foco fijo")
    return p.parse_args(argv)


class Ajuste:
    """Estado del ajuste, sin ventanas (lo prueban los tests): rangos, color actual y cambios sin guardar."""

    def __init__(self, rangos: dict[str, RangoHSV], ruta: Path, color: str = COLORES[0]):
        self.rangos = rangos
        self.ruta = Path(ruta)
        self.i = COLORES.index(color)
        self.sin_guardar = False
        self._al_abrir = {k: RangoHSV(v.bajo, v.alto, v.nota) for k, v in rangos.items()}

    @property
    def color(self) -> str:
        return COLORES[self.i]

    @property
    def rango(self) -> RangoHSV:
        return self.rangos[self.color]

    def cambiar_color(self, paso: int) -> None:
        self.i = (self.i + paso) % len(COLORES)

    def poner_valores(self, valores) -> bool:
        """valores: (H mín, H máx, S mín, S máx, V mín, V máx) de los deslizadores. Devuelve si cambió algo."""
        h0, h1, s0, s1, v0, v1 = [int(x) for x in valores]
        nuevo = RangoHSV((h0, s0, v0), (h1, s1, v1), self.rango.nota)
        if (nuevo.bajo, nuevo.alto) == (self.rango.bajo, self.rango.alto):
            return False
        self.rangos[self.color] = nuevo
        self.sin_guardar = True
        return True

    def valores(self) -> tuple[int, ...]:
        r = self.rango
        return (r.bajo[0], r.alto[0], r.bajo[1], r.alto[1], r.bajo[2], r.alto[2])

    def pinchar(self, hsv: np.ndarray, u: int, v: int) -> RangoHSV:
        """Centra el rango del color actual en los píxeles alrededor de (u, v)."""
        m = LADO_MUESTRA // 2
        trozo = hsv[max(0, v - m): v + m + 1, max(0, u - m): u + m + 1].reshape(-1, 3)
        self.rangos[self.color] = rango_desde_muestra(trozo, nota=self.rango.nota)
        self.sin_guardar = True
        return self.rango

    def deshacer(self) -> None:
        r = self._al_abrir[self.color]
        self.rangos[self.color] = RangoHSV(r.bajo, r.alto, r.nota)
        self.sin_guardar = True

    def guardar(self) -> Path:
        ruta = guardar_config_vision(self.rangos, self.ruta)
        self.sin_guardar = False
        return ruta

    def vista(self, img_rgb: np.ndarray) -> np.ndarray:
        """Imagen | máscara (BGR) con el nombre del color y su rango."""
        import cv2

        hsv = cv2.cvtColor(np.ascontiguousarray(img_rgb), cv2.COLOR_RGB2HSV)
        m = mascara_hsv(hsv, self.rango)
        izq = superponer(a_bgr(img_rgb).copy(), m, COLORES_BGR[self.color], 0.55)
        der = cv2.cvtColor(m, cv2.COLOR_GRAY2BGR)
        r = self.rango
        rotulo(izq, [f"{self.i + 1}/{len(COLORES)} {self.color}" + (" *sin guardar*" if self.sin_guardar else ""),
                     f"bajo {r.bajo}  alto {r.alto}" + ("  (H da la vuelta)" if r.da_la_vuelta else ""),
                     f"{100.0 * np.count_nonzero(m) / m.size:.1f} % de la imagen", "n/p color · clic · s guardar · q"])
        return mosaico([izq, der])


def main(argv=None) -> None:
    import cv2

    ns = argumentos(argv)
    comun.comprobar_ventanas()
    ajuste = Ajuste(cargar_config_vision(ns.salida), Path(ns.salida), ns.color)
    camara = None
    if ns.imagen:
        bgr = cv2.imread(ns.imagen)
        if bgr is None:
            raise SystemExit(f"no puedo leer {ns.imagen}")
        img = np.ascontiguousarray(bgr[..., ::-1])
    else:
        from garbi.real import AjustesCamara, abrir_camaras

        camara = abrir_camaras({"cam": comun.fuente_camara(ns.camara)},
                               AjustesCamara(ns.exposicion, ns.balance, ns.foco))["cam"]
        img = camara.read_latest()
    congelada = camara is None
    estado = {"hsv": cv2.cvtColor(img, cv2.COLOR_RGB2HSV), "ancho": img.shape[1]}

    cv2.namedWindow(VENTANA, cv2.WINDOW_NORMAL)
    for nombre, maximo in DESLIZADORES:
        cv2.createTrackbar(nombre, VENTANA, 0, maximo, lambda _x: None)

    def a_deslizadores():
        for (nombre, _), valor in zip(DESLIZADORES, ajuste.valores()):
            cv2.setTrackbarPos(nombre, VENTANA, int(valor))

    def al_pinchar(evento, x, y, *_):
        if evento == cv2.EVENT_LBUTTONDOWN and x < estado["ancho"]:
            r = ajuste.pinchar(estado["hsv"], x, y)
            print(f"{ajuste.color}: bajo {r.bajo} alto {r.alto}")
            a_deslizadores()

    cv2.setMouseCallback(VENTANA, al_pinchar)
    a_deslizadores()
    print(__doc__.split("Teclas")[1].split("Deslizadores")[0])
    try:
        while True:
            if not congelada:
                img = camara.read_latest()
            estado["hsv"] = cv2.cvtColor(img, cv2.COLOR_RGB2HSV)
            ajuste.poner_valores([cv2.getTrackbarPos(n, VENTANA) for n, _ in DESLIZADORES])
            cv2.imshow(VENTANA, ajuste.vista(img))
            tecla = cv2.waitKey(30) & 0xFF
            if tecla in (ord("q"), 27):
                if ajuste.sin_guardar and input("Hay cambios sin guardar. ¿Guardar? [s/N] ").strip().lower() == "s":
                    print("guardado en", ajuste.guardar())
                break
            if tecla == ord("n"):
                ajuste.cambiar_color(1)
                a_deslizadores()
            elif tecla == ord("p"):
                ajuste.cambiar_color(-1)
                a_deslizadores()
            elif tecla == ord("s"):
                print("guardado en", ajuste.guardar())
            elif tecla == ord("z"):
                ajuste.deshacer()
                a_deslizadores()
            elif tecla == ord(" ") and camara is not None:
                congelada = not congelada
    finally:
        if camara is not None:
            camara.disconnect()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
