"""Garbi · amarre de la boca del tubo a la mandíbula fija del SO-101 (CadQuery, paramétrico).

Todo va en el **marco de la pinza** (cuerpo `gripper` del MJCF oficial), en mm, igual que `garbi/escena.py`
(montaje «lateral»), para poder meter el STL tal cual en la simulación:
- z: a lo largo de la pinza; las puntas de las mordazas están en z ≈ -104.
- x: dirección de cierre; la mandíbula fija está en x < 0 y la móvil en x > 0.
- y: la cámara oficial está en +y; **el amarre va en -y** (el lado contrario a la cámara).

La mordaza móvil nunca sale de |y| ≤ 24,1 mm: todo el amarre está en y < -24, así que no la toca en ningún ángulo.

Piezas:
1. `amarre_boca`: placa atornillada a la cara -y de la caja del servo de la pinza (y = -24) con los **dos tornillos
   M2 del servo** de ese lado (se cambian por otros 5 mm más largos), brazo y abrazadera partida que aprieta el tubo
   con dos M3.
2. `anillo_boca`: anillo verde lima en la punta del tubo (marca para calibrar el robot con la cámara de arriba).
3. `silla_brida`: asiento para atar el tubo al costado de un eslabón con dos bridas que abrazan eslabón + tubo
   (hacen falta 4; ver `README.md`). No va en el marco de la pinza: el asiento apoya en z = 0 y el tubo va a lo largo de x.

Uso:  python hardware/garbi/amarre_boca.py [--tubo 29] [--salida hardware/garbi/amarre_boca]
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path

import cadquery as cq

# --- parámetros (mm) ---------------------------------------------------------------------------------------------
TUBO = 29.0  # diámetro EXTERIOR del tubo donde lo coge la abrazadera: MEDIRLO con calibre en las crestas
HOLGURA_TUBO = 0.6  # la abrazadera queda algo más ancha y se cierra con los M3
PARED = 3.0  # pared de la abrazadera
# Boca, igual que la simulación (garbi/escena.py: BOCA_LATERAL, BOCA_ADELANTE, BOCA_ABIERTA)
BOCA = (-5.0, -70.0, -128.0)  # centro de la boca en el marco de la pinza
BOCA_ABIERTA = 7.0  # grados hacia fuera (-y). Recta (0°) se ve algo mejor pero el brazo pasa más cerca de la mano (estudio del 21-11)
ANILLO_LARGO = 12.0  # el anillo verde ocupa los 12 mm de la punta
ANILLO_PARED = 3.0  # más grueso que la pared de la abrazadera para que no lo tape; con 5 la calibración del anillo pierde precisión
ABRAZADERA = (25.0, 57.0)  # tramo de la abrazadera, en mm detrás de la boca (separada del anillo para que se vea)
# Placa sobre la cara -y de la caja del servo (zona plana medida en el STL oficial: x -16…-2, z -6…-32, y = -24)
CARA_Y = -24.0
PLACA_X = (-20.0, -1.0)  # x > -1 choca con los salientes de z -6…-10
PLACA_Z = (-42.0, -6.0)  # z > -6 se acerca a la muñeca
PLACA_GROSOR = 5.0
TORNILLOS_SERVO = ((-13.0, -13.2), (-13.0, -33.7))  # (x, z) de los dos tornillos M2 del servo en la cara -y
M2_PASO, M2_CABEZA, M2_CABEZA_ALTO = 2.4, 4.2, 2.0
BRAZO_GROSOR = 6.0  # en x
HOLGURA_BRAZO = 1.0  # el brazo empieza 1 mm por debajo de la abrazadera (lado -x), fuera del paso del tubo
M3_PASO, M3_TUERCA = 3.4, 6.4  # tuerca M3: 5,5 entre caras → 6,4 entre vértices con holgura
OREJA = 9.0  # cuánto salen las orejas de apriete
RANURA = 2.5  # corte de la abrazadera partida


def _v(*c):
    return cq.Vector(*c)


def geometria(tubo: float = TUBO):
    a = math.radians(BOCA_ABIERTA)
    e = _v(0, -math.sin(a), -math.cos(a))  # hacia donde mira la boca
    n = _v(0, math.cos(a), -math.sin(a))  # perpendicular en el plano y-z, hacia la pinza (+y)
    boca = _v(*BOCA)
    r_in = (tubo + HOLGURA_TUBO) / 2
    r_out = r_in + PARED
    return e, n, boca, r_in, r_out


def amarre(tubo: float = TUBO) -> cq.Workplane:
    e, n, boca, r_in, r_out = geometria(tubo)
    s0, s1 = ABRAZADERA
    c0, c1 = boca - e * s0, boca - e * s1  # extremos del eje de la abrazadera
    largo = s1 - s0
    x0 = BOCA[0]

    # abrazadera (manguito) y orejas de apriete arriba (+x), fuera del camino del tubo, que sale curvándose hacia -y
    manguito = cq.Solid.makeCylinder(r_out, largo, c1, e)
    cuerpo = cq.Workplane().add(manguito)
    lx = 2 * (RANURA / 2 + 4.0)  # dos orejas de 4 mm a los lados de la ranura
    arriba = _v(1, 0, 0)
    centro_orejas = (c0 + c1) * 0.5 + arriba * (r_out + OREJA / 2 - 1.5)
    orejas = cq.Workplane().add(cq.Solid.makeBox(lx, OREJA, largo, _v(-lx / 2, -OREJA / 2, -largo / 2)))
    orejas = _colocar(orejas.val(), e, centro_orejas, n)
    cuerpo = cuerpo.union(cq.Workplane().add(orejas))

    # placa y brazo. El brazo es una lámina paralela al plano y-z que va POR DEBAJO del tubo (lado del dorso de la
    # mandíbula fija, x < x de la boca - radio): así el tubo, al salir por detrás de la abrazadera, no lo toca.
    py0, py1 = CARA_Y - PLACA_GROSOR, CARA_Y
    bx1 = x0 - r_out - HOLGURA_BRAZO  # cara del brazo que mira al tubo
    bx0 = bx1 - BRAZO_GROSOR
    pts = [(py1, PLACA_Z[1]), (py0, PLACA_Z[1]), (py0, PLACA_Z[0]), (py1, PLACA_Z[0])]
    for c in (c0, c1):
        for k in (-5.0, 5.0):
            p = c + n * k
            pts.append((p.y, p.z))
    pts = _envolvente(pts)
    brazo = cq.Workplane("YZ", origin=(bx0, 0, 0)).polyline(pts).close().extrude(BRAZO_GROSOR)
    # nervio que une la lámina con la abrazadera, solo a lo largo de la abrazadera
    huella = [(q.y, q.z) for q in (c0 + n * 5.0, c1 + n * 5.0, c1 - n * 5.0, c0 - n * 5.0)]
    nervio = cq.Workplane("YZ", origin=(bx0, 0, 0)).polyline(huella).close().extrude(x0 - bx0)
    placa = cq.Workplane().add(cq.Solid.makeBox(PLACA_X[1] - bx0, PLACA_GROSOR, PLACA_Z[1] - PLACA_Z[0],
                                               _v(bx0, py0, PLACA_Z[0])))
    cuerpo = cuerpo.union(brazo).union(nervio).union(placa)

    # vaciado del brazo (aligerar) lejos de los bordes
    hueco_c = _v(bx0, py0 - 14, PLACA_Z[0] - 14) * 0.5 + _v(bx0, c1.y, c1.z) * 0.5
    hueco = cq.Solid.makeCylinder(6.0, BRAZO_GROSOR + 2, _v(bx0 - 1, hueco_c.y, hueco_c.z), _v(1, 0, 0))
    cuerpo = cuerpo.cut(cq.Workplane().add(hueco))

    # agujero del tubo, que sale por los dos lados, y ranura de la abrazadera partida
    taladro = cq.Solid.makeCylinder(r_in, largo + 40, c1 - e * 20, e)
    cuerpo = cuerpo.cut(cq.Workplane().add(taladro))
    # boca de salida abocinada por detrás: el tubo sale curvándose hacia fuera sin clavarse en el borde
    cono = cq.Solid.makeCone(r_in, r_in + 2.5, 4.0 + 0.01, c1 + e * 4.0, -e)
    cuerpo = cuerpo.cut(cq.Workplane().add(cono))
    ranura = cq.Solid.makeBox(RANURA, r_out + OREJA + 5, largo + 2, _v(-RANURA / 2, 0, -largo / 2 - 1))
    ranura = _colocar(ranura, e, (c0 + c1) * 0.5, n)
    cuerpo = cuerpo.cut(cq.Workplane().add(ranura))
    # que el manguito no invada el lado de la pinza (la cara del agujero queda abierta, sin material sobrante en y > -24)
    tope = cq.Solid.makeBox(200, 200, 300, _v(-100, CARA_Y, -250))
    cuerpo = cuerpo.cut(cq.Workplane().add(tope))

    # tornillos M3 de apriete atravesando las orejas (dirección n; tuerca en el lado de fuera, -n)
    for f in (0.25, 0.75):
        p = c0 + (c1 - c0) * f + arriba * (r_out + OREJA / 2 - 0.5)
        cuerpo = cuerpo.cut(cq.Workplane().add(cq.Solid.makeCylinder(M3_PASO / 2, 40, p - n * 20, n)))
        plano = cq.Plane(origin=p - n * (lx / 2 + 1), xDir=e, normal=n)
        cuerpo = cuerpo.cut(cq.Workplane(plano).polygon(6, M3_TUERCA).extrude(3.5))

    # tornillos M2 del servo: paso y cajeado para la cabeza por fuera
    for (x, z) in TORNILLOS_SERVO:
        cuerpo = cuerpo.cut(cq.Workplane().add(cq.Solid.makeCylinder(M2_PASO / 2, 20, _v(x, CARA_Y + 5, z), _v(0, -1, 0))))
        cuerpo = cuerpo.cut(cq.Workplane().add(cq.Solid.makeCylinder(M2_CABEZA / 2, M2_CABEZA_ALTO + 5,
                                                                      _v(x, py0 + M2_CABEZA_ALTO, z), _v(0, -1, 0))))
    return cuerpo


def anillo(tubo: float = TUBO) -> cq.Workplane:
    e, n, boca, r_in, r_out = geometria(tubo)
    ri = (tubo + 0.4) / 2
    s = cq.Solid.makeCylinder(ri + ANILLO_PARED, ANILLO_LARGO, boca - e * ANILLO_LARGO, e)
    s = s.cut(cq.Solid.makeCylinder(ri, ANILLO_LARGO + 2, boca - e * (ANILLO_LARGO + 1), e))
    return cq.Workplane().add(s)


def silla(tubo: float = TUBO) -> cq.Workplane:
    """Asiento de 34 × 24 mm: base de 4 mm contra el eslabón y cuna para el tubo, con muescas para dos bridas de 5 mm."""
    largo, ancho, base_alto = 34.0, 24.0, 4.0
    r = (tubo + HOLGURA_TUBO) / 2
    alto = base_alto + r * 0.55  # la cuna abraza algo más de un cuarto del tubo
    b = cq.Workplane().box(largo, ancho, alto, centered=(True, True, False))
    b = b.cut(cq.Workplane().add(cq.Solid.makeCylinder(r, largo + 2, _v(-largo / 2 - 1, 0, base_alto + r), _v(1, 0, 0))))
    for x in (-9.0, 9.0):  # muescas de las bridas en los dos costados y por debajo
        b = b.cut(cq.Workplane().box(5.5, ancho + 2, 1.5, centered=(True, True, False)).translate((x, 0, 0)))
        for sy in (-1, 1):
            b = b.cut(cq.Workplane().box(5.5, 1.5, alto + 2, centered=(True, True, False)).translate((x, sy * (ancho / 2), 0)))
    return b


def _colocar(forma, e, origen, n):
    """Lleva el marco local a: x = n, z = eje de la boca (e), y = +x de la pinza (arriba de la abrazadera)."""
    return forma.moved(cq.Location(cq.Plane(origin=origen, xDir=(n.x, n.y, n.z), normal=e)))


def _envolvente(pts):
    pts = sorted(set((round(p[0], 4), round(p[1], 4)) for p in pts))

    def giro(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    abajo, arriba = [], []
    for p in pts:
        while len(abajo) >= 2 and giro(abajo[-2], abajo[-1], p) <= 0:
            abajo.pop()
        abajo.append(p)
    for p in reversed(pts):
        while len(arriba) >= 2 and giro(arriba[-2], arriba[-1], p) <= 0:
            arriba.pop()
        arriba.append(p)
    return abajo[:-1] + arriba[:-1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tubo", type=float, default=TUBO, help="diámetro exterior del tubo en la abrazadera (mm)")
    ap.add_argument("--salida", default=str(Path(__file__).with_suffix("")))
    a = ap.parse_args()
    out = Path(a.salida)
    out.mkdir(parents=True, exist_ok=True)
    for nombre, pieza in (("amarre_boca", amarre(a.tubo)), ("anillo_boca", anillo(a.tubo)),
                         ("silla_brida", silla(a.tubo))):
        cq.exporters.export(pieza, str(out / f"{nombre}.step"))
        cq.exporters.export(pieza, str(out / f"{nombre}.stl"), tolerance=0.05, angularTolerance=0.1)
        v = pieza.val().Volume()
        print(f"{nombre}: {v / 1000:.1f} cm³ ≈ {v / 1000 * 1.24:.0f} g en PLA macizo")


if __name__ == "__main__":
    main()
