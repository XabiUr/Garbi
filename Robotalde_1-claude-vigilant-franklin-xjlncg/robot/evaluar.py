"""Evaluación de las políticas del robot soldador en simulación, con las mismas métricas que puntúan al alumno.

    python -m robot.evaluar --politica act --checkpoint salidas/entreno_act --repeticiones 10
    python -m robot.evaluar --politica replay --dataset datos/lewelder_sim
    python -m robot.evaluar --politica vla act replay --checkpoint-vla ... --checkpoint-act ... --dataset ...

Para cada política, anclaje y tipo de unión hace N recorridos en bucle cerrado sobre `EntornoSoldadura` (cada uno
desde una postura de reposo algo distinta, como la deja un operador) y puntúa la punta con `evaluar_pasada`, con el
"gatillo" del robot = el LED luciría (`lewelder.robot.punta_sobre_cordon`).

Criterio de éxito de la spec (sección 7): **cobertura completa a ±5 mm** (nivel oficial, el del jurado). El objetivo
del sábado 20:00 es 8 de 10 por anclaje. Error medio = distancia lateral media de la punta al cordón mientras luce el
LED (`desvio_medio_mm`); también se guarda el error 3D (lateral y de altura) y el máximo.

Escribe en `salidas/evaluacion/`: `<politica>.json` y `<politica>.md` con todos los recorridos y la tabla por
anclaje, y `comparativa.md` / `comparativa.json` con VLA frente a ACT frente a replay a partir de los JSON que haya
(la diapositiva del pitch).
"""
from __future__ import annotations

import argparse
import json
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import numpy as np

from lewelder import contrato as c
from lewelder.metricas import evaluar_pasada
from robot.politica import (MAX_PASOS, PoliticaNoDisponible, cargar_politica, con_gatillo, ejecutar_politica)

RAIZ = Path(__file__).resolve().parents[1]
DIR_EVALUACION = RAIZ / "salidas" / "evaluacion"
NOMBRES = {"vla": "VLA (SmolVLA)", "act": "ACT", "replay": "Replay (grabado)"}
ORDEN = ("vla", "act", "replay")
OBJETIVO = 0.8  # 8 de 10 recorridos completos por anclaje


def evaluar_recorrido(muestras, tipo, nivel: str = c.NIVEL_JURADO) -> dict:
    """Puntuación de un recorrido del robot: nota, éxito (cobertura completa a la tolerancia del nivel) y errores."""
    puntuadas = con_gatillo(muestras)
    r = evaluar_pasada(puntuadas, tipo, nivel)
    sobre = [m for m in puntuadas if m.gatillo]
    lateral = np.array([abs(m.y) for m in sobre]) if sobre else np.zeros(0)
    error_3d = np.array([np.hypot(m.y, m.z - c.ALTURA_PUNTA) for m in sobre]) if sobre else np.zeros(0)
    return {
        "nota": r.nota, "exito": bool(r.cobertura_pct >= 100.0), "cobertura_pct": r.cobertura_pct,
        "error_medio_mm": r.desvio_medio_mm if sobre else None,
        "error_3d_medio_mm": round(float(error_3d.mean()), 3) if sobre else None,
        "error_max_mm": round(float(lateral.max()), 3) if sobre else None,
        "n_quemados": r.n_quemados, "huecos": r.huecos, "velocidad_media": r.velocidad_media,
        "avisos": r.avisos,
    }


def _media(valores) -> float | None:
    valores = [v for v in valores if v is not None]
    return round(float(np.mean(valores)), 3) if valores else None


def resumir(recorridos: list[dict], clave) -> dict:
    """Tasa de éxito, error medio y nota media agrupando por `clave(recorrido)`."""
    grupos = defaultdict(list)
    for r in recorridos:
        grupos[clave(r)].append(r)
    return {k: {"n": len(rs), "exitos": sum(r["exito"] for r in rs),
                "tasa_exito": round(sum(r["exito"] for r in rs) / len(rs), 3),
                "error_medio_mm": _media(r["error_medio_mm"] for r in rs),
                "error_3d_medio_mm": _media(r["error_3d_medio_mm"] for r in rs),
                "nota_media": _media(r["nota"] for r in rs),
                "cumple_objetivo": sum(r["exito"] for r in rs) / len(rs) >= OBJETIVO}
            for k, rs in sorted(grupos.items())}


def evaluar_politica(nombre: str, politica, anclajes, tipos, repeticiones: int, nivel: str = c.NIVEL_JURADO,
                     max_pasos: int = MAX_PASOS, entorno=None, verbose: bool = True) -> dict:
    """N recorridos por (anclaje, tipo) con una política ya cargada. Devuelve el informe (dict serializable)."""
    from sim.entorno import EntornoSoldadura

    propio = entorno is None
    entorno = entorno or EntornoSoldadura(render=politica.necesita_imagenes)
    recorridos = []
    t0 = time.perf_counter()
    try:
        for anclaje in anclajes:
            for tipo in tipos:
                for rep in range(repeticiones):
                    t1 = time.perf_counter()
                    try:
                        muestras = ejecutar_politica(entorno, politica, tipo, anclaje, max_pasos=max_pasos,
                                                     semilla=rep)
                        r = evaluar_recorrido(muestras, tipo, nivel)
                        error = None
                    except PoliticaNoDisponible as e:
                        muestras, error = [], str(e)
                        r = {"nota": 0.0, "exito": False, "cobertura_pct": 0.0, "error_medio_mm": None,
                             "error_3d_medio_mm": None, "error_max_mm": None, "n_quemados": 0, "huecos": [],
                             "velocidad_media": 0.0, "avisos": []}
                    segundos = time.perf_counter() - t1
                    r.update({"anclaje": anclaje, "tipo": c.TipoPieza(tipo).value, "repeticion": rep,
                              "pasos": len(muestras), "segundos": round(segundos, 2),
                              "s_por_paso": round(segundos / max(1, len(muestras)), 4), "error": error,
                              "episodio_replay": getattr(politica, "episodio", None) if nombre == "replay" else None})
                    recorridos.append(r)
                    if verbose:
                        print(f"{nombre:6s} {anclaje} {r['tipo']:5s} #{rep}: nota {r['nota']:4.1f}  "
                              f"cobertura {r['cobertura_pct']:5.1f} %  error {r['error_medio_mm']} mm  "
                              f"{'ÉXITO' if r['exito'] else 'fallo'}  ({len(muestras)} pasos, {segundos:.1f} s)"
                              + (f"  [{error}]" if error else ""), flush=True)
    finally:
        if propio:
            entorno.cerrar()
    return {
        "politica": nombre, "nombre": NOMBRES.get(nombre, nombre), "nivel": nivel,
        "tolerancia_mm": c.TOLERANCIAS[nivel], "fecha": datetime.now().isoformat(timespec="seconds"),
        "checkpoint": str(getattr(politica, "ruta", "")) or None,
        "dataset": str(getattr(politica, "raiz", "")) or None,
        "repeticiones": repeticiones, "anclajes": list(anclajes), "tipos": [c.TipoPieza(t).value for t in tipos],
        "segundos": round(time.perf_counter() - t0, 1),
        "total": resumir(recorridos, lambda r: "total")["total"] if recorridos else None,
        "por_anclaje": resumir(recorridos, lambda r: r["anclaje"]),
        "por_anclaje_tipo": {f"{a}/{t}": v for (a, t), v in
                             resumir(recorridos, lambda r: (r["anclaje"], r["tipo"])).items()},
        "recorridos": recorridos,
    }


# --- tablas ------------------------------------------------------------------------------------------------------
def _fmt(v, sufijo="", dec=1) -> str:
    return "—" if v is None else f"{v:.{dec}f}{sufijo}"


def tabla_politica(informe: dict) -> str:
    """Markdown con la tabla por anclaje y tipo de una política."""
    lineas = [f"# Evaluación: {informe['nombre']}", "",
              f"Nivel {informe['nivel']} (±{informe['tolerancia_mm']:.0f} mm) · {informe['repeticiones']} "
              f"recorridos por anclaje y tipo · éxito = cobertura completa · {informe['fecha']}", ""]
    if informe.get("checkpoint"):
        lineas += [f"Checkpoint: `{informe['checkpoint']}`", ""]
    if informe.get("dataset"):
        lineas += [f"Dataset: `{informe['dataset']}`", ""]
    lineas += ["| Anclaje | Tipo | Éxitos | Tasa de éxito | Error medio (mm) | Error 3D (mm) | Nota media |",
               "|---|---|---|---|---|---|---|"]
    for clave, v in informe["por_anclaje_tipo"].items():
        a, t = clave.split("/")
        lineas.append(f"| {a} | {c.NOMBRE_UNION[c.TipoPieza(t)]} | {v['exitos']}/{v['n']} | "
                      f"{100 * v['tasa_exito']:.0f} % | {_fmt(v['error_medio_mm'], dec=2)} | "
                      f"{_fmt(v['error_3d_medio_mm'], dec=2)} | {_fmt(v['nota_media'])} |")
    lineas += ["", "| Anclaje | Éxitos | Tasa de éxito | Error medio (mm) | Nota media | Objetivo 8/10 |",
               "|---|---|---|---|---|---|"]
    for a, v in informe["por_anclaje"].items():
        lineas.append(f"| {a} | {v['exitos']}/{v['n']} | {100 * v['tasa_exito']:.0f} % | "
                      f"{_fmt(v['error_medio_mm'], dec=2)} | {_fmt(v['nota_media'])} | "
                      f"{'sí' if v['cumple_objetivo'] else 'no'} |")
    if informe["total"]:
        v = informe["total"]
        lineas.append(f"| **Total** | {v['exitos']}/{v['n']} | {100 * v['tasa_exito']:.0f} % | "
                      f"{_fmt(v['error_medio_mm'], dec=2)} | {_fmt(v['nota_media'])} | "
                      f"{'sí' if v['cumple_objetivo'] else 'no'} |")
    return "\n".join(lineas) + "\n"


def comparativa(informes: dict[str, dict]) -> tuple[str, dict]:
    """Tabla VLA frente a ACT frente a replay por anclaje (Markdown y dict)."""
    politicas = [p for p in ORDEN if p in informes] + [p for p in informes if p not in ORDEN]
    anclajes = sorted({a for inf in informes.values() for a in inf["por_anclaje"]})
    datos = {p: {"por_anclaje": informes[p]["por_anclaje"], "total": informes[p]["total"],
                 "repeticiones": informes[p]["repeticiones"], "fecha": informes[p]["fecha"],
                 "checkpoint": informes[p].get("checkpoint")} for p in politicas}
    cab = " | ".join(NOMBRES.get(p, p) for p in politicas)
    lineas = ["# Comparativa de políticas: VLA frente a ACT frente a replay", "",
              f"Simulación MuJoCo · nivel {c.NIVEL_JURADO} (±{c.TOLERANCIAS[c.NIVEL_JURADO]:.0f} mm) · éxito = "
              "cobertura completa del cordón · objetivo: 8 de 10 por anclaje", "",
              "Tasa de éxito (error medio en mm) por anclaje:", "",
              f"| Anclaje | {cab} |", "|---|" + "---|" * len(politicas)]

    def celda(v):
        return "—" if v is None else f"{100 * v['tasa_exito']:.0f} % ({_fmt(v['error_medio_mm'], dec=1)})"

    for a in anclajes:
        lineas.append(f"| {a} | " + " | ".join(celda(informes[p]["por_anclaje"].get(a)) for p in politicas) + " |")
    lineas.append("| **Total** | " + " | ".join(celda(informes[p]["total"]) for p in politicas) + " |")
    lineas += ["", "Nota media (0-10):", "", f"| Anclaje | {cab} |", "|---|" + "---|" * len(politicas)]
    for a in anclajes:
        lineas.append(f"| {a} | " + " | ".join(
            _fmt((informes[p]["por_anclaje"].get(a) or {}).get("nota_media")) for p in politicas) + " |")
    lineas += ["", "Recorridos por anclaje: " + ", ".join(
        f"{NOMBRES.get(p, p)} {informes[p]['repeticiones'] * len(informes[p]['tipos'])}" for p in politicas) + "."]
    return "\n".join(lineas) + "\n", datos


def guardar(informe: dict, carpeta: Path = DIR_EVALUACION) -> dict[str, Path]:
    """Escribe `<politica>.json/.md` y rehace la comparativa con todos los JSON de la carpeta."""
    carpeta = Path(carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)
    p = informe["politica"]
    rutas = {"json": carpeta / f"{p}.json", "md": carpeta / f"{p}.md"}
    rutas["json"].write_text(json.dumps(informe, ensure_ascii=False, indent=1), encoding="utf-8")
    rutas["md"].write_text(tabla_politica(informe), encoding="utf-8")
    informes = {}
    for ruta in sorted(carpeta.glob("*.json")):
        if ruta.stem == "comparativa":
            continue
        try:
            datos = json.loads(ruta.read_text(encoding="utf-8"))
        except ValueError:
            continue
        if "por_anclaje" in datos:
            informes[datos["politica"]] = datos
    md, datos = comparativa(informes)
    rutas["comparativa_md"] = carpeta / "comparativa.md"
    rutas["comparativa_json"] = carpeta / "comparativa.json"
    rutas["comparativa_md"].write_text(md, encoding="utf-8")
    rutas["comparativa_json"].write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")
    return rutas


def main(argv=None):
    p = argparse.ArgumentParser(description="Evalúa VLA / ACT / replay en la simulación con las métricas del alumno.")
    p.add_argument("--politica", nargs="+", choices=list(ORDEN), default=["replay"])
    p.add_argument("--checkpoint", help="checkpoint de la política (si solo se evalúa act o vla)")
    p.add_argument("--checkpoint-act")
    p.add_argument("--checkpoint-vla")
    p.add_argument("--dataset", default=str(RAIZ / "datos" / "lewelder_sim"), help="LeRobotDataset para replay")
    p.add_argument("--anclajes", nargs="+", default=list(c.ANCLAJES), choices=list(c.ANCLAJES))
    p.add_argument("--tipos", nargs="+", default=[t.value for t in c.TipoPieza], choices=[t.value for t in c.TipoPieza])
    p.add_argument("--repeticiones", type=int, default=10)
    p.add_argument("--nivel", choices=list(c.TOLERANCIAS), default=c.NIVEL_JURADO)
    p.add_argument("--max-pasos", type=int, default=MAX_PASOS)
    p.add_argument("--dispositivo", default="cpu")
    p.add_argument("--salida", default=str(DIR_EVALUACION))
    a = p.parse_args(argv)
    for nombre in a.politica:
        checkpoint = {"act": a.checkpoint_act, "vla": a.checkpoint_vla}.get(nombre)
        if checkpoint is None and nombre != "replay" and len(a.politica) == 1:
            checkpoint = a.checkpoint
        try:
            politica = cargar_politica(nombre, checkpoint, a.dataset, a.dispositivo)
        except PoliticaNoDisponible as e:
            print(f"{nombre}: no disponible ({e}); se salta")
            continue
        informe = evaluar_politica(nombre, politica, a.anclajes, a.tipos, a.repeticiones, a.nivel, a.max_pasos)
        if hasattr(politica, "n_inferencias") and politica.n_inferencias:
            informe["s_inferencia_por_paso"] = round(politica.tiempo_inferencia / politica.n_inferencias, 4)
        rutas = guardar(informe, Path(a.salida))
        print()
        print(tabla_politica(informe))
        print(f"→ {rutas['json']}  {rutas['md']}  {rutas['comparativa_md']}")
    comparativa_md = Path(a.salida) / "comparativa.md"
    if comparativa_md.exists():
        print()
        print(comparativa_md.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
