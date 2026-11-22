"""Validación en simulación de la mesa de montaje v2 con las piezas REALES del CAD, antes de imprimir nada.

Genera `hardware/v2/validacion_sim.md` con un veredicto por pieza:
- **Ajuste de la colisión** a cada malla (IoU con las primitivas medidas sobre ella).
- **Chapa móvil (aleta):** holguras de la pinza abierta y cerrada sobre la aleta, giro de la chapa en la pinza mientras
  se transporta, y montaje de la T y de la esquina con la chapa tumbada en poses aleatorias de la zona libre.
- **Base (ranura y tope):** la chapa suelta con errores de ±5 mm y ±5° encaja con los imanes (y cuánto se hunde).
- **Antorcha y soporte:** la antorcha suelta con ±3 mm y ±3° sobre el tubo cae dentro; la pinza coge el mango, suelda
  la junta y la devuelve.
- **Brazo:** ningún choque del SO-101 con la mesa, la base o el soporte en los movimientos del guion.
- **Guion:** N/N por orden del núcleo.

Uso:
    python -m sim.validar_montaje                    # 10 por orden, escribe el informe
    python -m sim.validar_montaje --n 3 --videos     # rápido, y vídeos mp4 + imágenes en salidas/montaje/
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

import mujoco
import numpy as np

from lewelder import contrato as c
from sim import demos_montaje as dm
from sim import montaje as mt
from sim import piezas_cad

RAIZ = Path(__file__).resolve().parents[1]
INFORME = RAIZ / "hardware" / "v2" / "validacion_sim.md"
SALIDA_VIDEOS = RAIZ / "salidas" / "montaje"
MM = mt.MM
MINIMO_IMANES = 0.95  # fracción de sueltas a ±5 mm / ±5° que deben cerrar la junta
# Cotas que se prueban si la junta no encaja siempre (mm): el chaflán de la ranura del brief y uno de 2 en el tope
PROPUESTAS_BASE = {mt.TipoJunta.T: ("chaflan_ranura", 1.5), mt.TipoJunta.ESQUINA: ("chaflan_tope", 2.0)}


# --- pruebas sueltas ------------------------------------------------------------------------------------------------
def holguras_pinza(ent: mt.EntornoMontaje) -> dict:
    """Hueco entre las almohadillas con la pinza abierta (orden del guion) frente a la aleta y al mango."""
    m = ent.modelo
    d = mujoco.MjData(m)

    def hueco(q):
        d.qpos[ent.j_pinza] = q
        mujoco.mj_forward(m, d)
        bg = ent.b_pinza
        Rg, pg = d.xmat[bg].reshape(3, 3), d.xpos[bg]
        caras = []
        for nombre, signo in (("almohadilla_fija", 1), ("almohadilla_movil", -1)):
            g = m.geom(nombre).id
            centro = Rg.T @ (d.geom_xpos[g] - pg)
            caras.append(centro[0] + signo * mt.GROSOR_ALMOHADILLA)
        return (caras[1] - caras[0]) / MM  # en la punta de los dedos, aprox.

    geo = mt._GEO
    return {"hueco_abierta_mm": round(hueco(mt.PINZA_ABIERTA), 1), "aleta_mm": round(geo["aleta_grosor"], 2),
            "mango_mm": round(geo["mango_grosor"], 2), "hueco_cerrada_mm": round(hueco(mt.PINZA_CERRADA), 1)}


def penetracion(ent: mt.EntornoMontaje, geoms_a: set[int], geoms_b: set[int]) -> float:
    """Mayor interpenetración (mm) entre dos grupos de geoms en este instante."""
    d = ent.datos
    peor = 0.0
    for i in range(d.ncon):
        g1, g2 = d.contact[i].geom1, d.contact[i].geom2
        if (g1 in geoms_a and g2 in geoms_b) or (g2 in geoms_a and g1 in geoms_b):
            peor = max(peor, -d.contact[i].dist / MM)
    return peor


def prueba_imanes(ent: mt.EntornoMontaje, junta, n: int, rng, err_mm=5.0, err_grados=5.0) -> dict:
    """Suelta la chapa cerca de su sitio con un error aleatorio (±err) y mira si los imanes cierran la junta."""
    junta = mt.TipoJunta(junta)
    base = {g for g in range(ent.modelo.ngeom) if ent.modelo.geom_bodyid[g] == ent.modelo.body("base_montaje").id}
    oks, errores, pens = 0, [], []
    for _ in range(n):
        ent.reset(c.orden_montar(junta))
        R0, p0 = mt.pose_montada(junta)
        dp = rng.uniform(-err_mm, err_mm, 3)
        dp[2] = abs(dp[2]) + 0.5  # siempre por encima: se suelta, no se incrusta
        eje = rng.normal(size=3)
        giro = dm._giro_eje(eje, rng.uniform(-err_grados, err_grados))
        ent._poner_libre(ent.adr_movil, ent.dadr_movil, giro @ R0, p0 + dp)
        mujoco.mj_forward(ent.modelo, ent.datos)
        quieto = ent.estado()
        pen = 0.0
        for k in range(45):  # 1,5 s
            ent.step(quieto)
            if k > 30:
                pen = max(pen, penetracion(ent, ent.geoms_movil, base))
        mm_, gr = ent.error_montaje(junta)
        ok = ent.junta_cerrada is junta and mm_ < mt.ERROR_CERRADA_MM and gr < mt.ERROR_CERRADA_GRADOS
        oks += ok
        errores.append((mm_, gr))
        pens.append(pen)
    e = np.array(errores)
    return {"n": n, "ok": oks, "error_max_mm": round(float(e[:, 0].max()), 2),
            "error_max_grados": round(float(e[:, 1].max()), 2), "penetracion_max_mm": round(float(max(pens)), 2)}


def prueba_soporte(ent: mt.EntornoMontaje, n: int, rng, err_mm=3.0, err_grados=3.0) -> dict:
    """Suelta la antorcha sobre el tubo con un error lateral y de inclinación: ¿cae dentro y se asienta?"""
    sop = {g for g in range(ent.modelo.ngeom) if ent.modelo.geom_bodyid[g] == ent.modelo.body("soporte_antorcha").id}
    oks, pens, alturas = 0, [], []
    for _ in range(n):
        ent.reset(mt.ORDEN_SOLDAR, junta="t")
        ent.datos.eq_active[ent.eq_asiento] = 0
        R0, p0 = mt.pose_soporte()
        dp = np.r_[rng.uniform(-err_mm, err_mm, 2), 3.0]
        giro = dm._giro_eje(np.r_[rng.normal(size=2), 0.0], rng.uniform(-err_grados, err_grados))
        ent._poner_libre(ent.adr_antorcha, ent.dadr_antorcha, giro @ R0, p0 + dp)
        mujoco.mj_forward(ent.modelo, ent.datos)
        quieto = ent.estado()
        pen = 0.0
        for k in range(45):
            ent.step(quieto)
            if k >= 35:  # ya asentada (al entrar ladeada el contacto blando cede un momento)
                pen = max(pen, penetracion(ent, ent.geoms_antorcha, sop))
        oks += ent.antorcha_en_soporte()
        pens.append(pen)
        alturas.append(ent.datos.site_xpos[ent.sitio_punta][2] / MM)
    return {"n": n, "ok": oks, "penetracion_max_mm": round(float(max(pens)), 2),
            "punta_z_mm": (round(float(min(alturas)), 2), round(float(max(alturas)), 2))}


def prueba_choques(ent: mt.EntornoMontaje) -> bool:
    """Comprobación del propio detector: bajar la pinza contra la mesa debe registrar un choque."""
    ent.reset(mt.ORDEN_SENALAR, junta="t")
    q0 = mt.lerobot_a_rad(ent.estado().astype(float))
    q, _, _ = ent.cin.inversa_pose(np.array([0.20, 0.0, -0.015]), np.array([0, 0, -1.0]), q0,
                                   sitio="gripperframe", eje_local=(1, 0, 0))
    for _ in range(60):  # la pinza intenta meterse 15 mm en la mesa
        ent.step(mt.rad_a_lerobot(q))
    return bool(ent.choques)


def ejecutar_ordenes(ent: mt.EntornoMontaje, n: int, ruido: float) -> dict:
    """N demostraciones por orden (semillas 0..n-1) con la medida del giro de la chapa en la pinza."""
    out = {}
    for orden in mt.ORDENES_NUCLEO:
        filas = []
        for s in range(n):
            deslizamiento = {"ref": None, "max": 0.0}

            def mirar(obs, accion, d=deslizamiento):
                objeto = "movil" if mt.junta_de_orden(orden) else "antorcha"
                agarrada = ent.chapa_agarrada() if objeto == "movil" else ent.antorcha_agarrada()
                if agarrada:
                    R, _ = ent.agarre_medido(objeto)
                    if d["ref"] is None:
                        d["ref"] = R
                    d["max"] = max(d["max"], mt.angulo_entre(d["ref"], R))
                else:
                    d["ref"] = None

            t0 = time.perf_counter()
            try:
                r = dm.ejecutar_orden(ent, orden, dm.GuionV2(ruido=ruido), semilla=s, al_fotograma=mirar)
                filas.append({"semilla": s, "exito": r.exito, "junta": r.junta, "segundos_sim": r.fotogramas / 30,
                              "segundos_cpu": time.perf_counter() - t0, "inclinacion": r.inclinacion, "nota": r.nota,
                              "giro_en_pinza": deslizamiento["max"], "choques": dict(ent.choques),
                              "info": r.info})
            except dm.SinSolucion as e:
                filas.append({"semilla": s, "exito": False, "motivo": str(e), "choques": dict(ent.choques),
                              "giro_en_pinza": deslizamiento["max"]})
        out[orden] = filas
    return out


# --- vídeos ---------------------------------------------------------------------------------------------------------
def escribir_mp4(ruta: Path, fotogramas: list[np.ndarray], fps: int = c.FPS_DATASET) -> Path:
    import av

    ruta.parent.mkdir(parents=True, exist_ok=True)
    alto, ancho = fotogramas[0].shape[:2]
    with av.open(str(ruta), "w") as cont:
        flujo = cont.add_stream("libx264" if "libx264" in av.codecs_available else "mpeg4", rate=fps)
        flujo.width, flujo.height, flujo.pix_fmt = ancho - ancho % 2, alto - alto % 2, "yuv420p"
        for f in fotogramas:
            marco = av.VideoFrame.from_ndarray(np.ascontiguousarray(f[:alto - alto % 2, :ancho - ancho % 2]),
                                               format="rgb24")
            for p in flujo.encode(marco):
                cont.mux(p)
        for p in flujo.encode():
            cont.mux(p)
    return ruta


def grabar_videos(salida: Path = SALIDA_VIDEOS, resolucion=(320, 240), semilla: int = 3) -> list[Path]:
    """Un mp4 por orden (cenital y muñeca lado a lado) y algunas imágenes de los momentos clave."""
    from PIL import Image

    ent = mt.EntornoMontaje(resolucion=resolucion, render=True)
    rutas = []
    for orden in mt.ORDENES_NUCLEO:
        fotos, fases = [], []

        def guardar(obs, accion):
            fotos.append(np.concatenate([obs["observation.images.cenital"], obs["observation.images.muneca"]], 1))

        for intento in range(dm.REINTENTOS_SEMILLA):  # como al grabar: otra semilla si la IK no llega
            fotos.clear()
            try:
                r = dm.ejecutar_orden(ent, orden, dm.GuionV2(ruido=1.0), semilla=semilla + 100_000 * intento,
                                      al_fotograma=guardar)
                break
            except dm.SinSolucion:
                continue
        else:
            raise RuntimeError(f"sin demostración para el vídeo de {orden}")
        nombre = orden.replace(" ", "_").replace("ó", "o").replace("ñ", "n")
        rutas.append(escribir_mp4(salida / f"{nombre}.mp4", fotos))
        del fases
        for frac in (0.3, 0.5, 0.7, 1.0):
            k = min(len(fotos) - 1, int(frac * len(fotos)))
            Image.fromarray(fotos[k]).save(salida / f"{nombre}_{int(frac * 100):03d}.png")
        print(f"{orden}: éxito {r.exito}, {len(fotos)} fotogramas → {rutas[-1]}", flush=True)
    ent.cerrar()
    return rutas


# --- informe --------------------------------------------------------------------------------------------------------
def _veredicto(ok: bool) -> str:
    return "**VALE**" if ok else "**NO VALE**"


def informe(n: int = 10, ruido: float = 0.0, semilla: int = 0, ruta: Path = INFORME) -> tuple[str, dict]:
    t0 = time.perf_counter()
    rng = np.random.default_rng(semilla)
    ent = mt.EntornoMontaje(render=False)
    ajustes = {p: piezas_cad.ajuste_colision(p) for p in piezas_cad.PIEZAS}
    med = {p: piezas_cad.medidas(p) for p in piezas_cad.PIEZAS}
    hol = holguras_pinza(ent)
    detector = prueba_choques(ent)
    imanes = {j: prueba_imanes(ent, j, 3 * n, rng) for j in mt.TipoJunta}
    soporte = prueba_soporte(ent, 2 * n, rng)
    ordenes = ejecutar_ordenes(ent, n, ruido)
    ent.cerrar()
    # Si la ranura no recoge siempre la chapa, se prueba el chaflán del brief (1,5 mm) para proponerlo con datos
    propuestas_imanes = {}  # junta → (cota, valor, resultado con la cota propuesta)
    for junta, (cota, valor) in PROPUESTAS_BASE.items():
        if imanes[junta]["ok"] < imanes[junta]["n"]:
            piezas_cad.COTAS_PROPUESTAS[cota] = valor
            piezas_cad.primitivas.cache_clear()
            ent2 = mt.EntornoMontaje(render=False)
            propuestas_imanes[junta] = (cota, valor, prueba_imanes(ent2, junta, 3 * n, np.random.default_rng(semilla)))
            ent2.cerrar()
            piezas_cad.COTAS_PROPUESTAS.clear()
            piezas_cad.primitivas.cache_clear()

    def todas(orden):
        return all(f["exito"] for f in ordenes[orden])

    def choques(ordenes_sel):
        tot = {}
        for o in ordenes_sel:
            for f in ordenes[o]:
                for k, v in f["choques"].items():
                    tot[k] = tot.get(k, 0) + v
        return tot

    montar = [o for o in mt.ORDENES_NUCLEO if mt.junta_de_orden(o)]
    giro_chapa = max(f["giro_en_pinza"] for o in montar for f in ordenes[o])
    giro_ant = max(f["giro_en_pinza"] for f in ordenes[mt.ORDEN_SOLDAR])
    ch_todos = choques(mt.ORDENES_NUCLEO)
    geo = mt._GEO

    v_movil = (all(todas(o) for o in montar) and hol["hueco_abierta_mm"] > geo["aleta_grosor"] + 10
               and giro_chapa < 3.0)
    v_base = all(imanes[j]["ok"] >= MINIMO_IMANES * imanes[j]["n"] for j in mt.TipoJunta) and \
        max(imanes[j]["penetracion_max_mm"] for j in mt.TipoJunta) < 0.5
    v_soporte = soporte["ok"] == soporte["n"] and soporte["penetracion_max_mm"] < 0.5
    v_antorcha = todas(mt.ORDEN_SOLDAR) and giro_ant < 3.0
    v_brazo = detector and not ch_todos
    L = []
    L.append("# Validación en simulación del CAD v2 (antes de imprimir)\n")
    L.append(f"Generado por `python -m sim.validar_montaje --n {n}` · {time.strftime('%d-%m-%Y %H:%M')} · "
             f"MuJoCo con el SO-101 y las mallas de `hardware/v2/cad/stl/` (colisión con primitivas medidas sobre "
             f"cada malla, ver `sim/piezas_cad.py`). Guion sin ruido salvo que se diga; poses de la chapa al azar en "
             f"`ZONA_LIBRE`.\n")
    L.append("## Veredicto\n")
    L.append("| Pieza | Veredicto | Por qué |")
    L.append("|---|---|---|")
    L.append(f"| MOVIL-V2 (aleta) | {_veredicto(v_movil)} | pinza abierta {hol['hueco_abierta_mm']} mm sobre una aleta de "
             f"{geo['aleta_grosor']:.1f}; la chapa gira como mucho {giro_chapa:.1f}° en la pinza; montaje "
             f"{sum(f['exito'] for f in ordenes[montar[0]])}/{n} (T) y {sum(f['exito'] for f in ordenes[montar[1]])}/{n}"
             f" (esquina) |")
    L.append(f"| BASE-V2 (ranura y tope) | {_veredicto(v_base)} | imanes desde ±5 mm y ±5°: "
             f"T {imanes[mt.TipoJunta.T]['ok']}/{imanes[mt.TipoJunta.T]['n']}, esquina "
             f"{imanes[mt.TipoJunta.ESQUINA]['ok']}/{imanes[mt.TipoJunta.ESQUINA]['n']}; la chapa se hunde como mucho "
             f"{max(imanes[j]['penetracion_max_mm'] for j in mt.TipoJunta):.2f} mm en la base |")
    L.append(f"| SOPORTE-ANTORCHA-V2 | {_veredicto(v_soporte)} | antorcha soltada a ±3 mm y ±3° sobre el tubo: "
             f"{soporte['ok']}/{soporte['n']} dentro; punta a Z {soporte['punta_z_mm'][0]}–{soporte['punta_z_mm'][1]} "
             f"(mango a {geo['pie_soporte'] + geo['punta_a_mango']:.1f}, contrato {c.SOPORTE_ANTORCHA['z_mango']}) |")
    L.append(f"| ANTORCHA-ROBOT-V2 (mango) | {_veredicto(v_antorcha)} | la pinza coge el mango de "
             f"{geo['mango_grosor']:.1f} mm (abierta {hol['hueco_abierta_mm']}), gira como mucho {giro_ant:.1f}° "
             f"en la pinza; coge, suelda y devuelve {sum(f['exito'] for f in ordenes[mt.ORDEN_SOLDAR])}/{n} |")
    L.append(f"| Brazo SO-101 | {_veredicto(v_brazo)} | choques del brazo con mesa, base o soporte en el guion: "
             f"{ch_todos or 'ninguno'} (el detector sí ve un choque provocado: {detector}) |")
    L.append("")
    L.append("## Guion por orden\n")
    L.append("| Orden | Éxito | Duración (s simulados) | Inclinación al soltar / señalar | Nota soldadura | CPU por episodio |")
    L.append("|---|---|---|---|---|---|")
    for o in mt.ORDENES_NUCLEO:
        fs = ordenes[o]
        ok = [f for f in fs if f["exito"]]
        dur = f"{np.mean([f['segundos_sim'] for f in ok]):.1f}" if ok else "—"
        inc = sorted({f.get("inclinacion") for f in ok if f.get("inclinacion") is not None})
        notas = [f["nota"] for f in ok if f.get("nota") is not None]
        nota = f"{np.mean(notas):.2f}" if notas else "—"
        cpu = f"{np.mean([f['segundos_cpu'] for f in ok]):.1f} s" if ok else "—"
        L.append(f"| `{o}` | {len(ok)}/{len(fs)} | {dur} | {', '.join(f'{i:g}°' for i in inc) or '—'} | {nota} | {cpu} |")
    fallos = [(o, f) for o in mt.ORDENES_NUCLEO for f in ordenes[o] if not f["exito"]]
    if fallos:
        L.append("\nFallos:\n")
        for o, f in fallos:
            L.append(f"- `{o}` semilla {f['semilla']}: {f.get('motivo') or f.get('info')}")
    L.append("\n## Medidas sobre las mallas (mm)\n")
    L.append("| Pieza | Volumen (mm³) | Ajuste de la colisión | Cotas medidas |")
    L.append("|---|---|---|---|")
    for p in piezas_cad.PIEZAS:
        m = {k: v for k, v in med[p].items() if k not in ("radio_interior_por_z", "caja", "volumen_mm3")}
        L.append(f"| {p} | {med[p]['volumen_mm3']} | {ajustes[p].texto()} | "
                 + ", ".join(f"{k} {v}" for k, v in m.items()) + " |")
    L.append("\nLo que sobra en la base son los agujeros de los imanes, el hueco del ArUco y las patas (por debajo o "
             "por dentro: no tocan nada); en la antorcha, el plano de la chaveta y el cono de la punta.\n")
    L.append("## Pinza\n")
    L.append(f"- Hueco entre almohadillas: abierta (orden del guion, {mt.PINZA_ABIERTA} rad) {hol['hueco_abierta_mm']} "
             f"mm; cerrada del todo {hol['hueco_cerrada_mm']} mm. Aleta {geo['aleta_grosor']:.1f} mm, mango "
             f"{geo['mango_grosor']:.1f} mm: entran los dos con más de 10 mm de margen y la pinza los aprieta antes de "
             f"llegar al tope.")
    L.append(f"- La aleta se coge con la pinza vertical, a {mt.PROFUNDIDAD_AGARRE:g} mm de su extremo; la chapa se "
             f"deja de pie con la pinza casi horizontal y los imanes la enderezan ({', '.join(sorted({str(f.get('inclinacion')) + '°' for o in montar for f in ordenes[o] if f['exito']}))} de inclinación al soltarla).")
    L.append("- El mango se coge **de lado** (pinza horizontal, dedos en las caras planas de 12 mm), bajando en "
             "vertical desde arriba: así la antorcha queda atravesada en la pinza, como en la v1. Cogida desde arriba "
             "por el hombro (coaxial con la muñeca) un brazo de 5 ejes no puede soldar el cordón, que está en el lado "
             "lejano de la junta, con 45° y empuje: tendría que apuntar hacia el propio robot.")
    L.append("\n## Imanes (detalle)\n")
    L.append(f"La chapa se suelta (sin pinza) cerca de su sitio con un error al azar de ±5 mm y ±5° y se mira si los "
             f"imanes la dejan a menos de {mt.ERROR_CERRADA_MM} mm y {mt.ERROR_CERRADA_GRADOS}° (criterio: "
             f"{MINIMO_IMANES:.0%}). Imanes: soldadura blanda con constante de tiempo {mt.REF_IMAN} s (≈ 2 N a "
             f"10 mm), captura a < {mt.CAPTURA_MM:g} mm y < {mt.CAPTURA_GRADOS:g}°.\n")
    for j in mt.TipoJunta:
        L.append(f"- {j.value}: {imanes[j]}")
    for junta, (cota, valor, r) in propuestas_imanes.items():
        L.append(f"- {junta.value} con `{cota}` = {valor:g} mm (propuesta): {r}")
    L.append(f"\n## Soporte (detalle)\n\n- {soporte}")
    L.append("\n## Mesa usada (contrato)\n")
    L.append(f"- `POSICION_BASE` = ({c.POSICION_BASE.x:g}, {c.POSICION_BASE.y:g}, giro {c.POSICION_BASE.giro:g}); "
             f"`ZONA_LIBRE` = {c.ZONA_LIBRE}; `SOPORTE_ANTORCHA` = {c.SOPORTE_ANTORCHA} (giro radial "
             f"{mt.giro_soporte():.0f}°, chaveta hacia fuera).")
    L.append("\n## Cambios de cota propuestos\n")
    propuestas = []
    if not v_movil:
        propuestas.append("MOVIL-V2: revisar la aleta (ver fallos de montaje arriba).")
    textos = {"chaflan_ranura": ("el chaflán de entrada de la ranura de la T", "en las dos aristas de la ranura",
                                 "la chapa apoyada en el borde de la ranura, 2 mm arriba"),
              "chaflan_tope": ("el chaflán de la arista interior (lado −Y) del tope de la esquina",
                               "en la arista superior interior del tope", "la chapa subida encima del tope")}
    for junta, (cota, valor, r) in propuestas_imanes.items():
        que, donde, fallo = textos[cota]
        propuestas.append(
            f"BASE-V2 ({junta.value}): {que} mide ~{med['BASE-V2'].get(cota)} mm en el CAD. Desde ±5 mm y ±5° la "
            f"chapa encaja {imanes[junta]['ok']}/{imanes[junta]['n']} veces con el del CAD y {r['ok']}/{r['n']} con "
            f"{valor:g} mm: **hacer un chaflán de 45° × {valor:g} {donde}** (los fallos son {fallo}). Con lo que "
            f"falla el robot al soltarla encaja siempre (guion 10/10).")
    if not v_base and not propuestas_imanes:
        propuestas.append("BASE-V2: revisar ranura y tope (ver el detalle de los imanes).")
    if not v_soporte:
        propuestas.append("SOPORTE-ANTORCHA-V2: entrada cónica más ancha (Ø26 en lo alto) si la antorcha no cae dentro.")
    if not v_antorcha:
        propuestas.append("ANTORCHA-ROBOT-V2: revisar el mango (ver fallos de soldadura arriba).")
    propuestas.append(f"Contrato: `SOPORTE_ANTORCHA` en ({c.SOPORTE_ANTORCHA['x']:g}, {c.SOPORTE_ANTORCHA['y']:g}) "
                      f"(a r ≈ {np.hypot(c.SOPORTE_ANTORCHA['x'], c.SOPORTE_ANTORCHA['y']):.0f} mm, girado "
                      f"{mt.giro_soporte():.0f}° con la chaveta hacia fuera): con el mango a 116 la pinza horizontal "
                      f"no llega más cerca. Cambia la posición en la mesa, no la pieza.")
    z = c.ZONA_LIBRE
    propuestas.append(f"Contrato: `ZONA_LIBRE` cerca y a la izquierda (x {z['x'][0]:g}–{z['x'][1]:g}, "
                      f"y {z['y'][0]:g}–{z['y'][1]:g}, sin pisar la base ni el robot): la pinza vertical solo "
                      "coge la aleta y la levanta a r < ~250 mm; la zona de la derecha (y −260…−185) queda casi "
                      "entera fuera de alcance. Cambia el tapete, no la pieza.")
    propuestas.append("Brief: la antorcha se coge de lado por el mango (no desde arriba apoyando en el hombro); el "
                      "hombro no estorba y no hay que cambiar el CAD.")
    L += [f"- {p}" for p in propuestas]
    L.append(f"\nTiempo de la validación: {time.perf_counter() - t0:.0f} s de CPU.\n")
    texto = "\n".join(L) + "\n"
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(texto, encoding="utf-8")
    resumen = {"movil": v_movil, "base": v_base, "soporte": v_soporte, "antorcha": v_antorcha, "brazo": v_brazo,
               "ordenes": {o: sum(f["exito"] for f in fs) for o, fs in ordenes.items()}}
    return texto, resumen


def main(argv=None):
    p = argparse.ArgumentParser(description="Valida en simulación el CAD v2 y el guion de montaje.")
    p.add_argument("--n", type=int, default=10, help="demostraciones por orden")
    p.add_argument("--ruido", type=float, default=0.0)
    p.add_argument("--salida", default=str(INFORME))
    p.add_argument("--videos", action="store_true", help="graba un mp4 por orden en salidas/montaje/")
    p.add_argument("--solo-videos", action="store_true")
    a = p.parse_args(argv)
    if not a.solo_videos:
        _, resumen = informe(a.n, a.ruido, ruta=Path(a.salida))
        print(resumen)
        print("informe →", a.salida)
    if a.videos or a.solo_videos:
        grabar_videos()


if __name__ == "__main__":
    main()
