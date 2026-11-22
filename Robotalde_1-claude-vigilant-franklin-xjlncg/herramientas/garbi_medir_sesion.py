"""Mide la sesión final en la simulación con la percepción por imágenes y cuenta las clavadas vistas y perdidas.

    python herramientas/garbi_medir_sesion.py                    # los 5 intentos y las 2 variantes, semilla 0
    python herramientas/garbi_medir_sesion.py --semilla 2 --intentos 0,1
    python herramientas/garbi_medir_sesion.py --verdad           # con la verdad de la simulación (rápido)

Es `python -m garbi.correr --sim --sin-manos-verdad` (percepción final: manos por color, agarre, clavada y levantada
de la percepción) más lo que el juez no cuenta: cada vez que la persona apoya la broca (`apoya`, `apoyo_corto`) se
mira si el ciclo entra en el ACERCAMIENTO antes de que la levante («vista», con el retraso desde que la punta toca la
madera) o no («perdida»); entradas sin apoyo del juez cuentan como «sin apoyo del juez» (p. ej. el taladro que se deja
de pie en la madera, con la mano aún en él). Al final, una línea JSON con todo. Unos 12-13 min de reloj.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

BAJADA_S = 0.6  # s que tarda el juez en bajar la broca a la madera al apoyar (`garbi.sesion`)


def argumentos(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--semilla", type=int, default=0)
    p.add_argument("--intentos", default="todos", help="índices de `intentos_estandar()` separados por comas")
    p.add_argument("--verdad", action="store_true", help="Escena de la verdad de la simulación (sin imágenes)")
    p.add_argument("--madera", default="360,0,0", help="pose de la madera X,Y,GIRO (mm, mm, grados)")
    return p.parse_args(argv)


def contar_clavadas(eventos) -> dict:
    """Clavadas del juez vistas por el ciclo (y con qué retraso), perdidas y entradas sin apoyo del juez."""
    total, vistas, retrasos, sin_apoyo = 0, 0, [], 0
    abierta = None
    for t, quien, que in eventos:
        if quien == "juez" and que in ("apoya", "apoyo_corto"):
            abierta, total = [t + BAJADA_S, False], total + 1
        elif quien == "juez" and que in ("levanta", "mueve", "sale"):
            abierta = None
        elif quien == "ciclo" and "broca clavada" in que:
            if abierta is not None and not abierta[1]:
                abierta[1], vistas = True, vistas + 1
                retrasos.append(round(t - abierta[0], 2))
            elif abierta is None:
                sin_apoyo += 1
    return {"clavadas": total, "vistas": vistas, "perdidas": total - vistas, "retraso_s": retrasos,
            "sin_apoyo_del_juez": sin_apoyo}


def main(argv=None) -> dict:
    ns = argumentos(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s", datefmt="%H:%M:%S")
    from garbi import contrato as g
    from garbi.correr import correr_sim_final, informe_final
    from garbi.sesion import JuezSesion, intentos_estandar

    todos = intentos_estandar()
    intentos = todos if ns.intentos == "todos" else [todos[int(i)] for i in ns.intentos.split(",")]
    eventos: list = []
    original = JuezSesion.paso
    visto = {"fase": None, "n": 0}

    def paso(self, t):  # apunta las fases del juez y las transiciones del ciclo
        original(self, t)
        if self.fase != visto["fase"]:
            eventos.append((round(t, 2), "juez", self.fase))
            visto["fase"] = self.fase
        for x in self.ciclo.transiciones[visto["n"]:]:
            eventos.append((round(x.t, 2), "ciclo", f"{x.de}→{x.a}: {x.motivo}"))
        visto["n"] = len(self.ciclo.transiciones)

    JuezSesion.paso = paso
    t0 = time.time()
    try:
        tabla = g.PoseTabla(*(float(v) for v in ns.madera.split(",")))
        juez, ciclo, _ = correr_sim_final(intentos, verdad=ns.verdad, semilla=ns.semilla, manos_verdad=False,
                                          tabla=tabla)
    finally:
        JuezSesion.paso = original
    informe_final(juez, ciclo)
    res = juez.resumen()
    salida = {"semilla": ns.semilla, "madera": ns.madera, "aciertos": f"{res['aciertos']}/{res['intentos']}",
              "variantes": res["variantes_ok"], "holgura_min": res["holgura_min"],
              "holgura_mano_min": res["holgura_mano_min"], "borde_min": res["borde_min"],
              "falsos": res["falsos_agujeros"], "perdidos": res["perdidos"], **contar_clavadas(eventos),
              "duraciones": res["duraciones"], "t_acercamiento": res["t_acercamiento"], "contactos": res["contactos"],
              "sin_prudente": ciclo.sin_prudente, "apartadas_mano": ciclo.apartadas_mano, "respaldos": ciclo.respaldos,
              "reloj_s": round(time.time() - t0)}
    print(json.dumps(salida, ensure_ascii=False))
    juez.m.cerrar()
    return salida


if __name__ == "__main__":
    main()
