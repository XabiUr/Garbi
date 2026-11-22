"""Evalúa el paso 7 (limpiar la zona del agujero) en la simulación: ACT contra la espiral en los mismos agujeros.

    python herramientas/garbi_evaluar_paso7.py --modelo salidas/garbi_act --n 10 [--habilidades act,espiral] \\
        [--n-action-steps 25] [--ensemble 0.01] [--salida evaluacion.json]

Cada agujero sale de una semilla (`--semilla` + i): madera, agujero en la zona `ZONAS[i % 6]` de
`herramientas/garbi_grabar.py`, viruta (1/3 taladrado, 2/3 plantilla) y partida con ruido (±5 mm, ±3°). Así cada
habilidad limpia exactamente los mismos agujeros, y ninguno es de los grabados si las semillas no se solapan.

La habilidad recibe como «state» la orden anterior y las cámaras a 640 × 480 (como en el ciclo); se ejecuta sin
guardias (para ver lo que pide la política) y se mide:
- viruta en el círculo de 35 mm antes y después, % recogida y acierto (quedan ≤ `UMBRAL_PARTICULAS_VIRUTA`);
- borde mínimo de la boca sobre la superficie con la postura real (la guardia del ciclo para a `MARGEN_BORDE`);
- dónde apunta la boca: distancia del punto donde su eje corta la madera al agujero (media, máxima y
  fracción de pasos a más de 40 mm: la espiral va de 10 a 30 mm);
- segundos hasta que la zona queda limpia (`t_limpio`; la espiral y ACT duran 5 s fijos);
- pasos que la guardia del ciclo habría cortado: saltos entre acciones seguidas > `SALTO_HABILIDAD` y órdenes con el
  borde por debajo de `MARGEN_BORDE`; contactos del brazo (MuJoCo).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from garbi_grabar import FRACCION_TALADRADO, RADIO_PLANTILLA, ZONAS, _intervalo, preparar  # noqa: E402

from garbi import contrato as g  # noqa: E402
from garbi.tipos import UMBRAL_PARTICULAS_VIRUTA  # noqa: E402


def crear(nombre: str, control, m, modelo=None, n_action_steps=None, ensemble=None):
    from garbi.habilidad import HabilidadACT, HabilidadEspiral

    if nombre == "espiral":
        return HabilidadEspiral(control)
    if nombre == "persecucion":
        from garbi.percepcion import calibrar_camara_arriba
        from garbi.persecucion import HabilidadPersecucion

        return HabilidadPersecucion(control, camara=calibrar_camara_arriba(m.imagen("top", (640, 480))))
    if nombre == "act":
        h = HabilidadACT(modelo)
        pol = h.politica.politica
        if ensemble is not None:
            from lerobot.policies.act.modeling_act import ACTTemporalEnsembler

            pol.config.n_action_steps = 1
            pol.config.temporal_ensemble_coeff = float(ensemble)
            pol.temporal_ensembler = ACTTemporalEnsembler(float(ensemble), pol.config.chunk_size)
        elif n_action_steps is not None:
            pol.config.n_action_steps = int(n_action_steps)
        return h
    raise ValueError(nombre)


def evaluar_uno(m, control, hab, p_tabla, q0) -> dict:
    from garbi.ciclo import MARGEN_BORDE, RADIO_BOCA, SALTO_HABILIDAD, _lr_a_q4
    from garbi.habilidad import limpiar_en_simulacion

    madera = m.juez.tabla
    geoms_brazo = set(control._g_brazo)

    def borde(q4):
        b, e = control.boca(q4)
        sup = g.ALTURA_CARA_TABLA if madera.contiene(b[:2], margen=-RADIO_BOCA) else g.ALFOMBRILLA_GROSOR
        return float(b[2] - RADIO_BOCA * np.sqrt(max(0.0, 1.0 - e[2] ** 2)) - sup)

    med = {"borde_min": np.inf, "saltos": 0, "bordes_bajos": 0, "contactos": 0, "salto_max": 0.0, "acciones": [],
           "t_limpio": None, "radios": []}
    previa = [None]
    agujero = madera.a_mesa(np.asarray(p_tabla, float))

    def al_paso(obs, accion):
        if med["t_limpio"] is None and m.viruta_alrededor(p_tabla, 35.0) <= UMBRAL_PARTICULAS_VIRUTA:
            med["t_limpio"] = round(len(med["acciones"]) / 30.0, 2)
        med["borde_min"] = min(med["borde_min"], borde(_lr_a_q4(obs["observation.state"])))
        if previa[0] is not None:
            s = float(np.max(np.abs(accion - previa[0])))
            med["salto_max"] = max(med["salto_max"], s)
            med["saltos"] += s > SALTO_HABILIDAD
        med["bordes_bajos"] += borde(_lr_a_q4(accion)) < MARGEN_BORDE
        d = m.datos
        med["contactos"] += any(d.contact[k].dist < 0 and ((d.contact[k].geom1 in geoms_brazo) !=
                                                            (d.contact[k].geom2 in geoms_brazo)) for k in range(d.ncon))
        previa[0] = np.asarray(accion, float)
        med["acciones"].append(np.asarray(accion, float).round(2).tolist())
        # punto donde el eje de la boca corta la madera (postura real), relativo al agujero
        b, e = control.boca(_lr_a_q4(obs["observation.state"]))
        s = (g.ALTURA_CARA_TABLA - b[2]) / e[2] if e[2] < -1e-6 else np.inf
        med["radios"].append(float(np.linalg.norm(b[:2] + s * e[:2] - agujero)) if np.isfinite(s) else 999.0)

    t = time.perf_counter()
    antes, despues = limpiar_en_simulacion(m, hab, p_tabla, q0, observar=True, al_paso=al_paso, estado_orden=True)
    med["borde_min"] = min(med["borde_min"], borde(_lr_a_q4(m.estado())))
    if med["t_limpio"] is None and despues <= UMBRAL_PARTICULAS_VIRUTA:
        med["t_limpio"] = round(len(med["acciones"]) / 30.0, 2)
    med.update(antes=antes, despues=despues, recogida=round(1 - despues / max(antes, 1), 3),
               acierto=bool(despues <= UMBRAL_PARTICULAS_VIRUTA), segundos=round(time.perf_counter() - t, 1),
               borde_min=round(med["borde_min"], 1), salto_max=round(med["salto_max"], 1),
               radio_medio=round(float(np.mean(med["radios"])), 1), radio_max=round(float(np.max(med["radios"])), 1),
               fuera40=round(float(np.mean(np.array(med["radios"]) > 40.0)), 3))
    med["radios"] = np.round(med["radios"], 1).tolist()
    return med


def evaluar(habilidades, n: int = 10, semilla: int = 500, modelo=None, n_action_steps=None, ensemble=None,
            radio_plantilla=(15.0, 30.0), desplazamiento: float = 10.0, sitios=None) -> dict:
    from garbi.lateral import ControlLateral
    from garbi.mundo import MundoGarbi

    m = MundoGarbi(render=True, sombras=False, resolucion_politica=(640, 480), montaje="lateral")
    control = ControlLateral(m)
    m.reset(semilla=semilla)
    habs = {h: crear(h, control, m, modelo, n_action_steps, ensemble) for h in habilidades}
    filas = []
    indices = range(n) if sitios is None else sitios
    for i in indices:
        fila = {"i": int(i)}
        for nombre, hab in habs.items():
            rng = np.random.default_rng(semilla + i)
            m.reset(semilla=semilla + i)
            taladrado = rng.random() < FRACCION_TALADRADO
            p_tabla, q0, _ = preparar(m, control, rng, taladrado, ZONAS[i % len(ZONAS)], radio_plantilla,
                                      desplazamiento)
            r = evaluar_uno(m, control, hab, p_tabla, q0)
            fila.update(agujero_mesa=np.round(m.juez.tabla.a_mesa(p_tabla), 1).tolist(), zona=i % len(ZONAS),
                        viruta="taladrado" if taladrado else "plantilla")
            fila[nombre] = r
            print(f"{i:3d} zona {i % len(ZONAS)} {fila['agujero_mesa']} {nombre:11s} viruta {r['antes']:2d}→"
                  f"{r['despues']:2d} ({100 * r['recogida']:5.1f} %) {'ACIERTO' if r['acierto'] else 'fallo  '} "
                  f"borde {r['borde_min']:5.1f} saltos {r['saltos']} (máx {r['salto_max']:.1f}°) bordes bajos "
                  f"{r['bordes_bajos']} contactos {r['contactos']} · limpio a {r['t_limpio']} s · apunta a "
                  f"{r['radio_medio']:.0f} mm (máx {r['radio_max']:.0f}, {100 * r['fuera40']:.0f} % > 40 mm) · "
                  f"{r['segundos']} s",
                  flush=True)
        filas.append(fila)
    m.cerrar()
    resumen = {}
    for nombre in habs:
        rs = [f[nombre] for f in filas]
        resumen[nombre] = {
            "aciertos": sum(r["acierto"] for r in rs), "n": len(rs),
            "recogida_media": round(float(np.mean([r["recogida"] for r in rs])), 3),
            "recogida_min": round(float(np.min([r["recogida"] for r in rs])), 3),
            "borde_min": round(float(np.min([r["borde_min"] for r in rs])), 1),
            "saltos": int(sum(r["saltos"] for r in rs)), "bordes_bajos": int(sum(r["bordes_bajos"] for r in rs)),
            "contactos": int(sum(r["contactos"] for r in rs)),
            "agujeros_con_guardia": int(sum((r["saltos"] + r["bordes_bajos"]) > 0 for r in rs)),
            "radio_medio": round(float(np.mean([r["radio_medio"] for r in rs])), 1),
            "radio_max": round(float(np.max([r["radio_max"] for r in rs])), 1),
            "fuera40": round(float(np.mean([r["fuera40"] for r in rs])), 3),
            "t_limpio_medio": (round(float(np.mean([r["t_limpio"] for r in rs if r["t_limpio"] is not None])), 2)
                               if any(r["t_limpio"] is not None for r in rs) else None),
        }
    return {"resumen": resumen, "filas": filas, "semilla": semilla, "modelo": str(modelo),
            "n_action_steps": n_action_steps, "ensemble": ensemble}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--modelo", help="ACT: carpeta (pretrained_model, checkpoint o salida) o repo del Hub")
    p.add_argument("--habilidades", default="act,espiral")
    p.add_argument("--n", type=int, default=10)
    p.add_argument("--semilla", type=int, default=500)
    p.add_argument("--n-action-steps", type=int, default=None, help="ACT: acciones del chunk que se ejecutan")
    p.add_argument("--ensemble", type=float, default=None, help="ACT: ensemble temporal (p. ej. 0.01)")
    p.add_argument("--radio-plantilla", type=_intervalo, default=(15.0, 30.0))
    p.add_argument("--desplazamiento", type=float, default=10.0)
    p.add_argument("--salida", type=Path, help="json con los resultados")
    a = p.parse_args(argv)
    r = evaluar(a.habilidades.split(","), a.n, a.semilla, a.modelo, a.n_action_steps, a.ensemble,
                a.radio_plantilla, a.desplazamiento)
    print(json.dumps(r["resumen"], indent=1, ensure_ascii=False))
    if a.salida:
        a.salida.write_text(json.dumps(r, indent=1, ensure_ascii=False, default=float))
    return r


if __name__ == "__main__":
    main()
