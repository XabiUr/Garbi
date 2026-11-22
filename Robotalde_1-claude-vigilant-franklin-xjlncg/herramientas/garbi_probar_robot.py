"""Comprobación rápida del SO-101 follower de Garbi, sin percepción ni cámaras: montaje, cables y aspiradora.

    python herramientas/garbi_probar_robot.py --puerto COM5 --aspiradora COM7          # Windows
    python herramientas/garbi_probar_robot.py --puerto /dev/ttyACM0 --aspiradora /dev/ttyACM1
    python herramientas/garbi_probar_robot.py --puerto COM5 --solo-leer                # no mueve nada

Pasos (cada movimiento pide Enter antes; «n» lo salta):
1. Conecta el follower (calibración de LeRobot con --id) y lee la postura (grados; pinza 0-100).
2. Va al APARCADO despacio (--velocidad °/s).
3. Tres posturas seguras de prueba: aparcado girado +20°, aparcado girado −20° y la boca a 60 mm sobre el centro del
   tapete (postura central de la calibración). En cada una dice el error de llegada: > 3° suele ser un cable suelto,
   un servo sin par o el montaje rozando.
4. Vuelve al APARCADO.
5. Aspiradora encendida 2 s y apagada (si se da --aspiradora).

Ctrl+C en cualquier momento: el brazo se queda quieto donde está (con par) y la aspiradora se apaga.
Antes de mover: tapete despejado (sin madera ni taladro) y nadie con la mano cerca del brazo.
"""
from __future__ import annotations

import argparse
import time

import numpy as np

import garbi_comun as comun

ERROR_AVISO = 3.0  # °


def posturas_prueba():
    from garbi.calibracion import POSTURAS_CALIBRACION
    from garbi.lateral import APARCADO

    girar = np.array([20.0, 0, 0, 0, 0, 0])
    return [("aparcado girado +20°", APARCADO + girar), ("aparcado girado −20°", APARCADO - girar),
            ("boca a 60 mm sobre el centro del tapete", POSTURAS_CALIBRACION[4])]


def argumentos(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="python herramientas/garbi_probar_robot.py", description=__doc__,
                                formatter_class=comun.Ayuda)
    comun.anadir_robot(p)
    p.add_argument("--aspiradora", help="puerto serie del Arduino de la aspiradora (COM7, /dev/ttyACM1)")
    p.add_argument("--velocidad", type=float, default=comun.VELOCIDAD_LENTA, help="°/s de los movimientos")
    p.add_argument("--solo-leer", action="store_true", help="solo conectar y leer la postura (no mueve)")
    p.add_argument("--si", action="store_true", help="no pedir Enter antes de cada movimiento (¡cuidado!)")
    return p.parse_args(argv)


def formato_q(q) -> str:
    from garbi.tipos import ARTICULACIONES

    return "  ".join(f"{n}={v:7.1f}" for n, v in zip(ARTICULACIONES, np.asarray(q, float)))


def probar(cuerpo, ns, entrada=input, dormir=time.sleep) -> dict:
    """Los pasos 1-5 sobre un `Cuerpo` ya conectado. Devuelve los errores de llegada (°) por postura."""
    from garbi.lateral import APARCADO

    def preguntar(texto):
        return True if ns.si else comun.confirmar(texto, entrada)

    q = cuerpo.q()
    print("postura actual:", formato_q(q))
    errores = {}
    if ns.solo_leer:
        return errores
    plan = [("APARCADO", APARCADO)] + posturas_prueba() + [("APARCADO (vuelta)", APARCADO)]
    for nombre, objetivo in plan:
        if not preguntar(f"¿Ir a «{nombre}» a {ns.velocidad:.0f} °/s?"):
            continue
        err = comun.mover_despacio(cuerpo, objetivo, ns.velocidad, dormir=dormir)
        errores[nombre] = err
        aviso = "  ← ¡revisa cables/servo/montaje!" if err > ERROR_AVISO else ""
        print(f"  {nombre}: error {err:.1f}°{aviso}\n  leído: {formato_q(cuerpo.q())}")
    if getattr(cuerpo, "senal", None) is not None and preguntar("¿Aspiradora 2 s?"):
        cuerpo.aspirar(True)
        print("  aspiradora ENCENDIDA")
        dormir(2.0)
        cuerpo.aspirar(False)
        print("  aspiradora apagada")
    return errores


def main(argv=None) -> None:
    from garbi.real import CuerpoReal

    ns = argumentos(argv)
    cuerpo = CuerpoReal(ns.puerto, ns.id, camaras={}, puerto_aspiradora=ns.aspiradora)
    cuerpo.conectar()
    try:
        errores = probar(cuerpo, ns)
        malos = [n for n, e in errores.items() if e > ERROR_AVISO]
        print("TODO BIEN" if not malos else f"REVISAR: {', '.join(malos)}")
    except KeyboardInterrupt:
        print("\nCtrl+C: brazo quieto")
        comun.parar_quieto(cuerpo)
    finally:
        cuerpo.cerrar()


if __name__ == "__main__":
    main()
