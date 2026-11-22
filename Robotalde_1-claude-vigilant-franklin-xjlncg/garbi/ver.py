"""Visor 3D interactivo de Garbi (MuJoCo) en tu ordenador: el área de trabajo del hackathon, las situaciones y el
guion de una sesión completa, con lo último que hay en GitHub.

    python -m garbi.ver            # o herramientas/ver_garbi.bat (Windows), que antes trae lo último de GitHub

Montaje lateral: boquilla y tubo por el costado derecho del brazo, muñeca fija, cámara oficial en la muñeca.

Teclas (con la ventana del visor activa):
    →  ←      situación siguiente / anterior (15 situaciones: postura exacta del robot en cada una)
    Enter     maqueta de la demo como animación forzada, en tiempo real (~3 min): los 5 intentos del ciclo de un
              agujero en 5 sitios de la madera (seguir, preapunto, acompañar aspirando, ACT limpia la zona, revisar y
              aparcar) y la pasada final por toda la madera (→ ← la paran y vuelven a las situaciones)
(Las letras ya tienen atajos propios de MuJoCo: la G pone niebla, la S sombras, la T transparencia…)

Ratón: botón izquierdo gira, derecho desplaza, rueda acerca. Doble clic en una pieza la selecciona. En el panel de la
izquierda, «Rendering» → «Camera» cambia a las cámaras de Garbi («top» y «wrist»).
Necesita: pip install mujoco numpy opencv-python pillow (no hace falta LeRobot).
"""
from __future__ import annotations

import time

import mujoco
import mujoco.viewer
import numpy as np

from garbi import contrato as g
from garbi.mundo import MundoGarbi
from garbi.situaciones import TOTAL, Simulador, poner_situacion

TECLA_DERECHA, TECLA_IZQUIERDA, TECLA_ENTER, TECLA_ENTER_NUMERICO = 262, 263, 257, 335


class _Parar(Exception):
    pass


def sonar(nombre: str) -> None:
    """Sonidos de Garbi. En Windows con los pitidos del sistema (en otro hilo, para no frenar la animación)."""
    import sys
    import threading

    from garbi.maqueta import SONIDOS

    if sys.platform != "win32" or nombre not in SONIDOS:
        return
    import winsound

    def tocar():
        for frecuencia, ms in SONIDOS[nombre]:
            winsound.Beep(frecuencia, ms)

    threading.Thread(target=tocar, daemon=True).start()


class Visor:
    def __init__(self):
        self.m = MundoGarbi(render=False, montaje="lateral")
        self.sim = Simulador(self.m)
        self.numero = 1
        self.pedido: str | None = "situacion"
        self.texto = ("", "")
        self._maqueta = None  # se construye la primera vez que se pide (las posturas tardan unos segundos)

    # --- teclado (lo llama el hilo del visor) -----------------------------------------------------------------
    def tecla(self, codigo: int) -> None:
        if codigo == TECLA_DERECHA:
            self.numero = self.numero % TOTAL + 1
            self.pedido = "situacion"
        elif codigo == TECLA_IZQUIERDA:
            self.numero = (self.numero - 2) % TOTAL + 1
            self.pedido = "situacion"
        elif codigo in (TECLA_ENTER, TECLA_ENTER_NUMERICO):
            self.pedido = "guion"

    # --- dibujar ----------------------------------------------------------------------------------------------
    def rotular(self, visor, titulo: str, detalle: str) -> None:
        self.texto = (titulo, detalle)
        visor.set_texts([(mujoco.mjtFontScale.mjFONTSCALE_150, mujoco.mjtGridPos.mjGRID_TOPLEFT, titulo, detalle)])

    def situacion(self, visor) -> None:
        with visor.lock():
            s = poner_situacion(self.sim, self.numero)
            mujoco.mj_forward(self.m.modelo, self.m.datos)
        detalle = f"{s.resumen}\nestado: {s.estado} · aspiradora: {'ENCENDIDA' if s.aspiradora else 'apagada'}"
        if s.boca is not None:
            detalle += f"\nboca ({s.boca[0]:.0f}, {s.boca[1]:.0f}, {s.boca[2]:.0f}) mm · {s.inclinacion:.0f}°"
        detalle += "\n→ ← situaciones · Enter: maqueta de la demo (5 intentos y pasada final)"
        self.rotular(visor, f"S{s.numero}/{TOTAL}  {s.nombre}", detalle)
        visor.sync()

    def guion(self, visor) -> None:
        """La maqueta de la demo (5 intentos y pasada final) como animación forzada (garbi.maqueta), en tiempo real."""
        from garbi.maqueta import Maqueta

        class _Parar(Exception):
            pass

        inicio = time.perf_counter()

        from garbi.maqueta import ESTADOS

        def al_fotograma(f):
            if self.pedido is not None or not visor.is_running():
                raise _Parar
            if f.sonido:
                sonar(f.sonido)
            lineas = [f.detalle, f"app: [{ESTADOS[f.estado][1].upper()}] · aspiradora "
                      f"{'encendida' if f.aspiradora else 'apagada'} · viruta recogida {self.m.recogidas}"]
            if f.dice:
                lineas.append(f'Garbi: "{f.dice}"')
            lineas.append("→ ←: parar y volver a las situaciones")
            self.rotular(visor, f"{f.paso}  ·  t = {self.m.t:4.1f} s", "\n".join(lineas))
            visor.sync()
            espera = inicio + self.m.t - time.perf_counter()  # tiempo real
            if espera > 0:
                time.sleep(espera)

        if self._maqueta is None:
            self._maqueta = Maqueta(self.m)
            self._maqueta.construir()
        try:
            with visor.lock():
                pass
            self._maqueta.reproducir(al_fotograma)
        except _Parar:
            return
        self.rotular(visor, "Guion terminado", "Enter para repetir · → ← para volver a las situaciones")
        visor.sync()

    # --- bucle principal --------------------------------------------------------------------------------------
    def correr(self) -> None:
        with mujoco.viewer.launch_passive(self.m.modelo, self.m.datos, key_callback=self.tecla) as visor:
            visor.cam.lookat[:] = [0.25, 0.0, 0.05]
            visor.cam.distance, visor.cam.azimuth, visor.cam.elevation = 1.1, 200.0, -30.0
            while visor.is_running():
                pedido, self.pedido = self.pedido, None
                if pedido == "situacion":
                    self.situacion(visor)
                elif pedido == "guion":
                    self.guion(visor)
                else:
                    visor.sync()
                    time.sleep(0.03)


def main() -> None:
    print(__doc__)
    Visor().correr()


if __name__ == "__main__":
    main()
