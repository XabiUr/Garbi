"""Pruebas M8 del ciclo completo con percepción real (imágenes renderizadas) en la simulación, con ruido realista.

    python herramientas/garbi_robustez_ciclo.py ciclos [n=20|s1,s2,…] [procesos=4]  # 20 ciclos, 1 agujero por sesión
    python herramientas/garbi_robustez_ciclo.py seguidos [semilla=0]          # 5 seguidos + pasada final
    python herramientas/garbi_robustez_ciclo.py uno semilla                   # una sesión, con la traza

`ciclos`: cada sesión es una semilla distinta: madera girada ±8° en su zona, un sitio al azar de la zona de taladro
(320-420 mm del eje del robot), taladro inclinado 0-8° con rumbo cualquiera, velocidad de entrada ×0,6-1,6, broca
quieta en el aire a 10-40 mm 2,5 s (prueba «en el aire») antes de apoyar (prueba de apoyo) y temblor de ±1-2 mm al
taladrar. Imprime una fila por ciclo y el total contra los criterios de M8:
- 20 apoyos y 20 «en el aire»: sin falsos apoyos; ≥ 18/20 detectados;
- 20 ciclos: ≥ 19/20 aciertos, holgura real ≥ 10 mm y borde ≥ 3 mm;
- 5 seguidos con la pasada final: 5/5 y ≤ 3 min.
Necesita render sin pantalla (MUJOCO_GL=egl u osmesa).
"""
from __future__ import annotations

import json
import multiprocessing as mp
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

HOLGURA_MIN, BORDE_MIN = 10.0, 3.0


def _sesion(args):
    semilla, kw = args
    import logging

    logging.basicConfig(level=logging.WARNING)
    from garbi.robustez import sesion

    try:
        return sesion(semilla, **kw)
    except Exception as e:  # que una sesión rota no tire las demás
        return {"semilla": semilla, "error": repr(e)}


def correr(semillas, procesos: int = 4, **kw) -> list[dict]:
    if procesos <= 1:
        return [_sesion((s, kw)) for s in semillas]
    with mp.get_context("spawn").Pool(procesos) as pool:
        return pool.map(_sesion, [(s, kw) for s in semillas], chunksize=1)


def tabla_ciclos(res: list[dict]) -> dict:
    print(f"{'sem':>3} {'madera (x,y,giro)':>20} {'sitio':>11} {'r':>5} {'inc':>4} {'vel':>4} {'flota':>5} "
          f"{'acierto':>7} {'holg':>5} {'borde':>5} {'apoyo':>5} {'aire':>5} {'falsos':>6} {'dur':>5} {'reloj':>6}")
    filas = []
    for r in res:
        if "error" in r:
            print(f"{r['semilla']:>3} ERROR {r['error']}")
            filas.append(dict(acierto=False, holgura=-1, borde=-1, apoyo=False, aire_falso=True, falsos=1, dur=0))
            continue
        for k in range(len(r["sitios_mesa"])):
            ok = k < len(r["aciertos_por_agujero"])
            ru = r["ruidos"][k]
            f = dict(acierto=ok and r["aciertos_por_agujero"][k], holgura=r["holguras"][k] if ok else -1,
                     borde=r["bordes"][k] if ok else -1, apoyo=ok and r["apoyos_vistos"][k],
                     aire_falso=k < len(r["aire_falso"]) and r["aire_falso"][k], falsos=r["falsos"][k] if ok else 0,
                     dur=r["duraciones"][k] if ok else 0)
            filas.append(f)
            print(f"{r['semilla']:>3} {str(r['tabla']):>20} {str(r['sitios_mesa'][k]):>11} {r['radios'][k]:>5.0f} "
                  f"{ru['inclinacion']:>4.1f} {ru['velocidad']:>4.2f} {ru['flota'] or 0:>5.0f} "
                  f"{'sí' if f['acierto'] else 'NO':>7} {f['holgura']:>5.1f} {f['borde']:>5.1f} "
                  f"{'sí' if f['apoyo'] else 'NO':>5} {'FALSO' if f['aire_falso'] else 'ok':>5} {f['falsos']:>6} "
                  f"{f['dur']:>5.1f} {r['segundos_reloj']:>6.0f}")
    n = len(filas)
    tot = {
        "ciclos": n, "aciertos": sum(f["acierto"] for f in filas),
        "holgura_min": min(f["holgura"] for f in filas), "borde_min": min(f["borde"] for f in filas),
        "apoyos_detectados": sum(f["apoyo"] for f in filas), "aire_falsos": sum(f["aire_falso"] for f in filas),
        "lecturas_apoyo_falsas": sum(f["falsos"] for f in filas),
        "duracion": (min(f["dur"] for f in filas), max(f["dur"] for f in filas)),
    }
    print(f"\nAciertos {tot['aciertos']}/{n} (≥ {n - n // 20}) · holgura real mín {tot['holgura_min']:.1f} mm (≥ 10) · "
          f"borde mín {tot['borde_min']:.1f} mm (≥ 3)")
    print(f"Apoyos detectados {tot['apoyos_detectados']}/{n} (≥ {int(0.9 * n)}) · «en el aire» con apoyo falso "
          f"{tot['aire_falsos']}/{n} (0) · lecturas «apoyada» con la broca a > 8 mm: {tot['lecturas_apoyo_falsas']}")
    print(f"Duración por ciclo {tot['duracion'][0]:.1f}-{tot['duracion'][1]:.1f} s")
    return tot


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    modo = argv[0] if argv else "ciclos"
    os.environ.setdefault("MUJOCO_GL", "egl")
    salida = Path(os.environ.get("GARBI_ROBUSTEZ_SALIDA", "robustez_ciclo.json"))
    if modo == "ciclos":
        # n (semillas 0…n-1) o una lista de semillas separadas por comas
        semillas = [int(v) for v in argv[1].split(",")] if len(argv) > 1 and "," in argv[1] else \
            range(int(argv[1]) if len(argv) > 1 else 20)
        procesos = int(argv[2]) if len(argv) > 2 else 4
        res = correr(semillas, procesos, agujeros=1)
        tot = tabla_ciclos(res)
    elif modo == "seguidos":
        semilla = int(argv[1]) if len(argv) > 1 else 0
        res = correr([semilla], 1, agujeros=5, pasada_final=True, flota=False)
        tot = tabla_ciclos(res)
        r = res[0]
        total = sum(r.get("duraciones", [])) + r.get("pasada_final", 0.0)
        print(f"5 seguidos: {r.get('aciertos')}/5 · pasada final {r.get('pasada_final')} s · total {total:.1f} s "
              f"(≤ 180) · contactos en la pasada {r.get('contactos_pasada')}")
        tot["total_s"] = total
    else:
        semilla = int(argv[1]) if len(argv) > 1 else 0
        res = correr([semilla], 1, agujeros=1)
        tot = tabla_ciclos(res)
        for tr in res[0].get("transiciones", []):
            print("  ", tr)
        for fila in (res[0].get("trazas") or [[]])[0]:
            print("  ", fila)
    salida.write_text(json.dumps({"total": tot, "sesiones": res}, default=str, indent=1))
    print(f"(detalle en {salida})")


if __name__ == "__main__":
    main()
