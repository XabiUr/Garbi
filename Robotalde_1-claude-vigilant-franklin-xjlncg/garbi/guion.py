"""Guion de Garbi (montaje lateral): una sesión de trabajo completa en la que la persona sigue un guion fijo y Garbi
reacciona en cada fotograma (`garbi.interactivo`), sin aprendizaje.

    python -m garbi.guion --salida salidas/garbi_guion.mp4     # vídeo con observador, cámara de arriba y de la muñeca

La persona: entra con el taladro, busca el punto con la broca en el aire, la apoya y taladra, se mueve y repite (tres
agujeros) y se va. Garbi la sigue a distancia, se acerca cuando la broca se apoya, se separa cuando se levanta y, al
irse el taladro, limpia todos los agujeros con la boca más picada y aparca. El mundo simulado aplica la física del
brazo y la regla de aspiración. Se ve en el visor 3D con Enter (`python -m garbi.ver`).
"""
from __future__ import annotations

import argparse
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from garbi import contrato as g
from garbi.lateral import APARCADO, ControlLateral
from garbi.mundo import MundoGarbi

TABLA = g.PoseTabla(360.0, 0.0, 0.0)
PUNTO = np.array([-20.0, 40.0])  # punto de taladrado, marco de la madera (a ~340 mm del robot)
SERRIN = np.array([330.0, -195.0])  # montón de serrín en el tapete, a un lado de la madera


@dataclass
class Fotograma:
    t: float
    paso: str
    detalle: str
    aspiradora: bool


def _suave(q0, q1, n):
    q0, q1 = np.asarray(q0, float), np.asarray(q1, float)
    for k in range(1, n + 1):
        yield q0 + (q1 - q0) * (0.5 - 0.5 * np.cos(np.pi * k / n))


class Guion:
    """La persona sigue un guion fijo con el taladro; Garbi reacciona en cada fotograma (`garbi.interactivo`)."""

    def __init__(self, mundo: MundoGarbi | None = None):
        from garbi.interactivo import Seguidor

        self.m = mundo or MundoGarbi(render=False, montaje="lateral")
        self.c = ControlLateral(self.m)
        self.seguidor = Seguidor(self.c)

    def _fotograma(self, paso: str) -> Fotograma:
        from garbi.interactivo import VistaTaladro

        m, s = self.m, self.seguidor
        j = m.juez
        vista = VistaTaladro(j.taladro_visible, j.taladro_punta.copy() if j.taladro_visible else None)
        q = s.paso(m.t, vista, j.tabla)
        m.aspiradora = s.aspiradora
        m.step(q, observar=False)
        return Fotograma(m.t, paso, f"Garbi: {s.texto} ({s.estado.value})", m.aspiradora)

    def _mover(self, paso, desde, hasta, segundos, alto_desde, alto_hasta):
        """La persona lleva el taladro de `desde` a `hasta` (x, y) subiendo o bajando la punta, con suavidad."""
        n = max(1, int(round(segundos * g.FPS)))
        for k in range(1, n + 1):
            f = 0.5 - 0.5 * np.cos(np.pi * k / n)
            xy = np.asarray(desde) + (np.asarray(hasta) - np.asarray(desde)) * f
            z = g.ALTURA_CARA_TABLA + alto_desde + (alto_hasta - alto_desde) * f
            self.m.poner_taladro(xy[0], xy[1], z)
            yield self._fotograma(paso)

    def _quieto(self, paso, segundos):
        for _ in range(max(1, int(round(segundos * g.FPS)))):
            yield self._fotograma(paso)

    def pasos(self) -> Iterator[Fotograma]:
        m = self.m
        m.reset(0, tabla=TABLA, q_inicial=APARCADO)
        self.seguidor.__post_init__()
        agujeros = [TABLA.a_mesa(np.array(p)) for p in ((-20.0, 40.0), (40.0, -70.0), (-40.0, -20.0))]
        entrada = np.array([g.PERSONA_X + 60, 40.0])
        AIRE = 50.0  # mm de la punta sobre la madera mientras se mueve

        yield from self._quieto("1. Reposo", 1.5)
        m.poner_taladro(entrada[0], entrada[1], g.ALTURA_CARA_TABLA + AIRE)
        yield from self._mover("2. Entra el taladro", entrada, agujeros[0] + [40, 30], 2.5, AIRE, AIRE)
        yield from self._mover("3. Buscas el punto (broca en el aire)", agujeros[0] + [40, 30], agujeros[0] + [-20, -40],
                               2.0, AIRE, AIRE)
        yield from self._mover("3. Buscas el punto (broca en el aire)", agujeros[0] + [-20, -40], agujeros[0], 1.5, AIRE, AIRE)
        for i, a in enumerate(agujeros):
            yield from self._mover(f"4. Apoyas la broca (agujero {i + 1})", a, a, 0.6, AIRE, 0.0)
            yield from self._quieto(f"4. Apoyas la broca (agujero {i + 1})", 1.2)
            m.taladrar()
            yield from self._quieto(f"5. Taladras el agujero {i + 1}", 2.0)
            yield from self._mover(f"6. Levantas la broca", a, a, 0.5, 0.0, AIRE)
            if i + 1 < len(agujeros):
                yield from self._mover("6. Te mueves al punto siguiente", a, agujeros[i + 1], 2.0, AIRE, AIRE)
        yield from self._mover("7. Te vas con el taladro", agujeros[-1], entrada, 1.8, AIRE, AIRE + 60)
        m.quitar_taladro()
        for _ in range(int(25 * g.FPS)):  # Garbi limpia todos los agujeros y aparca
            f = self._fotograma("8. Garbi limpia todos los agujeros")
            yield f
            if self.seguidor.estado.value == "aparcado":
                break
        yield from self._quieto("9. Fin de la sesion", 1.0)


def video(salida: Path, cada: int = 2) -> Path:
    import cv2

    from garbi.video import _ascii

    m = MundoGarbi(render=True, montaje="lateral")
    guion = Guion(m)
    vw = None
    for k, f in enumerate(guion.pasos()):
        if k % cada:
            continue
        obs = m.imagen("vista_cerca", (960, 720))
        arriba = m.imagen("top", (480, 360))
        robot = m.imagen("wrist", (480, 360))
        lienzo = np.full((720 + 90, 1440, 3), 30, np.uint8)
        lienzo[:720, :960], lienzo[:360, 960:], lienzo[360:720, 960:] = obs, arriba, robot
        lienzo = cv2.cvtColor(lienzo, cv2.COLOR_RGB2BGR)
        fu = cv2.FONT_HERSHEY_SIMPLEX
        cv2.putText(lienzo, _ascii(f"{f.paso}   t = {f.t:4.1f} s"), (16, 752), fu, 0.9, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(lienzo, _ascii(f.detalle + f"   aspiradora: {'ENCENDIDA' if f.aspiradora else 'apagada'}"
                                   f"   viruta recogida: {m.recogidas}"), (16, 790), fu, 0.6, (200, 220, 160), 1, cv2.LINE_AA)
        if vw is None:
            salida.parent.mkdir(parents=True, exist_ok=True)
            vw = cv2.VideoWriter(str(salida), cv2.VideoWriter_fourcc(*"mp4v"), g.FPS / cada,
                                 (lienzo.shape[1], lienzo.shape[0]))
        vw.write(lienzo)
    vw.release()
    return salida


def main(argv=None) -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--salida", type=Path, default=Path("salidas/garbi_guion.mp4"))
    a = p.parse_args(argv)
    print("vídeo:", video(a.salida))


if __name__ == "__main__":
    main()
