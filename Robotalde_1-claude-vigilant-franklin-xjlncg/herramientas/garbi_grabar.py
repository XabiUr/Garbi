"""Graba demostraciones automáticas del paso 7 de Garbi (limpiar la zona del agujero) en un LeRobotDataset.

    python herramientas/garbi_grabar.py --salida datos/garbi_limpiar --episodios 40 \\
        [--habilidad espiral|persecucion] [--zonas] [--resolucion 160x120 --render 640x480] \\
        [--repo-id usuario/garbi_limpiar] [--push] [--semilla 0]

Cada episodio (especificación técnica, M5), en la simulación con el montaje lateral:
1. Madera en una pose aleatoria y un agujero en un punto alcanzable de ella; con `--zonas`, el agujero en una de las
   6 zonas de la zona de taladro (`ZONAS`: 320-420 mm del eje del robot, 2 anillos × 3 sectores), por turnos.
2. Viruta: 1/3 de los episodios con el agujero taladrado (anillo de viruta); 2/3 con un agujero ya hecho y serrín
   esparcido alrededor «con la plantilla» (un disco de `--radio-plantilla` mm, por defecto 15-22, desplazado del
   agujero hasta `--desplazamiento` mm).
3. El robot, en la posición de partida con ruido (±5 mm, ±3°): boca a 60°, a 35 mm del agujero y 30 mm de altura.
4. La habilidad con la aspiradora encendida durante 5 s fijos (150 fotogramas a 30 Hz): la espiral programada
   (`HabilidadEspiral`, demostraciones automáticas) o la persecución de la viruta vista desde arriba
   (`garbi.persecucion.HabilidadPersecucion`, el sustituto en la simulación de las teleoperadas). Se graba con
   `garbi.grabador.GrabadorLimpiezas`: `observation.images.top`, `observation.images.wrist` (renderizadas a
   `--render` y reducidas a `--resolucion`), `observation.state` (la orden anterior, como la ve la habilidad en el
   ciclo), `action` (6) y la tarea `TAREA_LIMPIEZA`.

Filtro: solo se guardan los episodios que dejan la zona limpia (en el círculo de 35 mm quedan como mucho
`FRACCION_LIMPIO` de las partículas, y al menos 1). Los descartes y los agujeros que no se alcanzan se apuntan en
`episodios_garbi_limpiar.json`, dentro del dataset.

`--push` sube el dataset al Hub (`LeRobotDataset.push_to_hub`); hace falta haber hecho `hf auth login`.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from garbi import contrato as g  # noqa: E402
from garbi.habilidad import (RADIO_ZONA, HabilidadEspiral, limpiar_en_simulacion,  # noqa: E402
                             posicion_partida)
from garbi.mundo import EN_TABLA, FUERA, MundoGarbi  # noqa: E402

RESOLUCION = (640, 480)  # (ancho, alto), como las cámaras reales
FRACCION_LIMPIO = 0.05  # limpio: quedan ≤ 5 % de las partículas de la zona (y al menos se admite 1)
FRACCION_TALADRADO = 1 / 3
MARGEN_BORDE = 25.0  # mm del agujero al borde de la madera
INTENTOS_AGUJERO = 60
RADIO_PLANTILLA = (15.0, 22.0)
# Zonas de la zona de taladro (marco de la mesa): (radio mín, radio máx) mm desde el eje del robot × (ángulo mín, máx)
# en grados (0 = hacia la persona, + a la izquierda del robot). 320-420 mm es donde funciona el ciclo completo con la
# percepción (T6, `garbi.correr.SITIOS_JUEZ`).
ZONAS = [((r0, r1), (a0, a1)) for (r0, r1) in ((320.0, 370.0), (370.0, 420.0))
         for (a0, a1) in ((-20.0, -7.0), (-7.0, 7.0), (7.0, 20.0))]


def zona_limpia(antes: int, despues: int) -> bool:
    return antes > 0 and despues <= max(1, int(FRACCION_LIMPIO * antes))


def _borrar_viruta_tabla(m: MundoGarbi) -> None:
    m.juez.viruta_donde[m.juez.viruta_donde == EN_TABLA] = FUERA
    m._actualizar_objetos()


def punto_en_zona(m: MundoGarbi, rng, zona) -> np.ndarray | None:
    """Un punto (marco de la madera) de la zona `zona` ((r0, r1), (a0, a1)) que cae en la madera con margen."""
    (r0, r1), (a0, a1) = zona
    largo, ancho = g.TABLA_TAMANO[0] / 2 - MARGEN_BORDE, g.TABLA_TAMANO[1] / 2 - MARGEN_BORDE
    for _ in range(200):
        r, a = rng.uniform(r0, r1), np.radians(rng.uniform(a0, a1))
        p_tabla = m.juez.tabla.a_tabla(np.array([r * np.cos(a), r * np.sin(a)]))
        if abs(p_tabla[0]) <= largo and abs(p_tabla[1]) <= ancho:
            return p_tabla
    return None


def preparar(m: MundoGarbi, control, rng, taladrado: bool, zona=None, radio_plantilla=RADIO_PLANTILLA,
             desplazamiento: float = 0.0) -> tuple[np.ndarray, np.ndarray, int]:
    """Madera, agujero y viruta. Devuelve (agujero en la madera, postura de partida con ruido, agujeros descartados
    por no alcanzarse)."""
    largo, ancho = g.TABLA_TAMANO[0] / 2 - MARGEN_BORDE, g.TABLA_TAMANO[1] / 2 - MARGEN_BORDE
    fuera = 0
    for _ in range(INTENTOS_AGUJERO):
        p_tabla = rng.uniform([-largo, -ancho], [largo, ancho]) if zona is None else punto_en_zona(m, rng, zona)
        if p_tabla is None:
            fuera += 1
            continue
        p_mesa = m.juez.tabla.a_mesa(p_tabla)
        q0 = posicion_partida(control, p_mesa, rng)
        if q0 is not None:
            break
        fuera += 1
    else:
        raise RuntimeError("ningún agujero alcanzable en la madera")
    m.poner_taladro(*p_mesa)
    m.taladrar()
    m.quitar_taladro()
    if not taladrado:  # agujero ya hecho y serrín guardado esparcido con la plantilla
        _borrar_viruta_tabla(m)
        centro = p_mesa
        if desplazamiento > 0:
            ang = rng.uniform(0, 2 * np.pi)
            centro = p_mesa + rng.uniform(0, desplazamiento) * np.array([np.cos(ang), np.sin(ang)])
        m.tirar_serrin(centro[0], centro[1], n=int(rng.integers(20, g.VIRUTA_POR_AGUJERO + 1)),
                       radio=float(rng.uniform(*radio_plantilla)))
    return p_tabla, q0, fuera


def crear_habilidad(nombre: str, control, m: MundoGarbi, render):
    if nombre == "espiral":
        return HabilidadEspiral(control)
    if nombre == "persecucion":
        from garbi.percepcion import calibrar_camara_arriba
        from garbi.persecucion import HabilidadPersecucion

        cam = calibrar_camara_arriba(m.imagen("top", render))  # la cámara de arriba es fija: se calibra una vez
        if cam is None:
            raise RuntimeError("no veo el tapete: no puedo calibrar la cámara de arriba para perseguir la viruta")
        return HabilidadPersecucion(control, camara=cam)
    raise ValueError(f"habilidad desconocida: {nombre}")


def grabar(salida: Path, repo_id: str, episodios: int, resolucion=RESOLUCION, semilla: int = 0,
           sobrescribir: bool = False, push: bool = False, privado: bool = False, habilidad: str = "espiral",
           render=None, zonas: bool = False, radio_plantilla=RADIO_PLANTILLA, desplazamiento: float = 0.0,
           sitios: list | None = None, correccion: str | None = None, pasos_act: int = 45,
           zonas_lista: list[int] | None = None) -> dict:
    """`sitios`: lista opcional de (pose de la madera, agujero en la madera, taladrado) para grabar casos concretos;
    si no, se sortean (`zonas_lista`: solo esas zonas, por turnos).
    `correccion`: modelo ACT. Cada episodio empieza con ACT `pasos_act` pasos sin grabar (con la aspiradora) desde la
    partida y luego la habilidad corrige desde donde lo dejó ACT, y eso es lo que se graba (como `lerobot-rollout
    --strategy.type=dagger`: se para ACT y se graba la corrección)."""
    from garbi.grabador import GrabadorLimpiezas
    from garbi.lateral import ControlLateral

    render = tuple(render or resolucion)
    grab = GrabadorLimpiezas(salida, repo_id, resolucion, sobrescribir,
                             extra={"origen": "garbi_grabar", "habilidad": habilidad, "render": list(render),
                                    "radio_zona_mm": RADIO_ZONA, "fraccion_limpio": FRACCION_LIMPIO,
                                    "radio_plantilla": list(radio_plantilla), "desplazamiento": desplazamiento})
    m = MundoGarbi(render=True, sombras=False, resolucion_politica=render, montaje="lateral")
    control = ControlLateral(m)
    m.reset(semilla=semilla)
    hab = crear_habilidad(habilidad, control, m, render)
    act = None
    if correccion:
        from garbi.habilidad import HabilidadACT

        act = HabilidadACT(correccion)
        grab.extra.update(correccion=str(correccion), pasos_act=pasos_act)
    lista = list(range(len(ZONAS))) if zonas_lista is None else list(zonas_lista)
    fuera_de_alcance = 0
    n = episodios if sitios is None else len(sitios)
    try:
        for i in range(n):
            rng = np.random.default_rng(semilla + i)
            if sitios is None:
                m.reset(semilla=semilla + i)
                taladrado = rng.random() < FRACCION_TALADRADO
                zona = ZONAS[lista[i % len(lista)]] if zonas else None
                p_tabla, q0, fuera = preparar(m, control, rng, taladrado, zona, radio_plantilla, desplazamiento)
                fuera_de_alcance += fuera
            else:
                tabla, p_tabla, taladrado = sitios[i]
                m.reset(semilla=semilla + i, tabla=tabla)
                p_tabla, q0, taladrado = fijar_sitio(m, control, rng, np.asarray(p_tabla, float), taladrado,
                                                     radio_plantilla, desplazamiento)
                zona = None
            grab.empezar(semilla=semilla + i, viruta="taladrado" if taladrado else "plantilla",
                         zona=None if zona is None else ZONAS.index(zona),
                         agujero_tabla=np.round(p_tabla, 1).tolist(),
                         agujero_mesa=np.round(m.juez.tabla.a_mesa(p_tabla), 1).tolist(),
                         tabla=[round(m.juez.tabla.x, 1), round(m.juez.tabla.y, 1), round(m.juez.tabla.giro, 2)])
            if act is not None:  # ACT desde la partida, sin grabar; la corrección empieza donde lo deja
                q0 = correr_act(m, act, p_tabla, q0, pasos_act)
            previa = [np.asarray(q0, np.float32)]

            def guardar(obs, accion):
                imgs = {cam: obs[f"observation.images.{cam}"] for cam in g.CAMARAS_POLITICA}
                grab.fotograma(imgs, previa[0], accion)  # state = la orden anterior (como en el ciclo)
                previa[0] = np.asarray(accion, np.float32)

            antes, despues = limpiar_en_simulacion(m, hab, p_tabla, q0, observar=True, al_paso=guardar)
            limpio = zona_limpia(antes, despues)
            if act is not None and antes == 0 and despues == 0:
                # corrección con la zona ya limpia: lo que enseña es a no irse del agujero (ACT se alejaba)
                limpio = True
            motivo = {} if limpio else {"motivo": "sucio"}
            ep = grab.terminar(limpio, viruta_antes=antes, viruta_despues=despues,
                               recogida=round(1 - despues / max(antes, 1), 3), **motivo)
            print(f"episodio {i:3d}  {ep['viruta']:9s} zona {ep['zona']} agujero {ep['agujero_mesa']}  viruta "
                  f"{antes:2d}→{despues:2d}  {'GUARDADO' if ep['guardado'] else 'descartado'}  {ep['segundos']:5.1f} s",
                  flush=True)
    finally:
        grab.extra["agujeros_fuera_de_alcance"] = fuera_de_alcance
        resumen = grab.cerrar()
        m.cerrar()
    if push:
        grab.ds.push_to_hub(tags=["garbi", "so101", "lerobot-hackathon"], private=privado)
    return resumen


def correr_act(m: MundoGarbi, act, p_tabla, q0, pasos: int) -> np.ndarray:
    """ACT `pasos` pasos desde `q0` con la aspiradora (como en el ciclo: «state» = la orden anterior). Devuelve la
    postura en que queda el robot."""
    agujero_mesa = m.juez.tabla.a_mesa(np.asarray(p_tabla, float))
    m.reset_robot(q0)
    act.reiniciar(np.array([agujero_mesa[0], agujero_mesa[1], g.ALTURA_CARA_TABLA]))
    m.aspiradora = True
    obs, orden = m.observacion(), np.asarray(q0, np.float32)
    for _ in range(pasos):
        entrada = {"state": orden, **{c: obs[f"observation.images.{c}"] for c in g.CAMARAS_POLITICA}}
        orden = np.asarray(act.accion(entrada), np.float32)
        obs = m.step(orden)
    m.aspiradora = False
    return np.asarray(m.estado(), float)


def fijar_sitio(m: MundoGarbi, control, rng, p_tabla, taladrado: bool, radio_plantilla=RADIO_PLANTILLA,
                desplazamiento: float = 0.0):
    """Como `preparar`, pero con el agujero dado (marco de la madera). Devuelve (agujero, partida, taladrado)."""
    p_mesa = m.juez.tabla.a_mesa(p_tabla)
    q0 = posicion_partida(control, p_mesa, rng)
    if q0 is None:
        raise RuntimeError(f"el agujero {p_mesa} no se alcanza")
    m.poner_taladro(*p_mesa)
    m.taladrar()
    m.quitar_taladro()
    if not taladrado:
        _borrar_viruta_tabla(m)
        centro = p_mesa
        if desplazamiento > 0:
            ang = rng.uniform(0, 2 * np.pi)
            centro = p_mesa + rng.uniform(0, desplazamiento) * np.array([np.cos(ang), np.sin(ang)])
        m.tirar_serrin(centro[0], centro[1], n=int(rng.integers(20, g.VIRUTA_POR_AGUJERO + 1)),
                       radio=float(rng.uniform(*radio_plantilla)))
    return p_tabla, q0, taladrado


def _resolucion(texto: str) -> tuple[int, int]:
    ancho, alto = texto.lower().split("x")
    return int(ancho), int(alto)


def _intervalo(texto: str) -> tuple[float, float]:
    a, b = texto.split("-")
    return float(a), float(b)


def main(argv=None) -> dict:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--salida", type=Path, default=Path("datos/garbi_limpiar"))
    p.add_argument("--repo-id", default="local/garbi_limpiar")
    p.add_argument("--episodios", type=int, default=40)
    p.add_argument("--habilidad", choices=("espiral", "persecucion"), default="espiral")
    p.add_argument("--resolucion", type=_resolucion, default=RESOLUCION,
                   help="ANCHOxALTO del dataset (640x480; menos para entrenar en CPU)")
    p.add_argument("--render", type=_resolucion, default=None,
                   help="ANCHOxALTO al que se renderiza (por defecto, la del dataset); las imágenes se reducen")
    p.add_argument("--zonas", action="store_true", help="agujeros repartidos por turnos en las 6 ZONAS (320-420 mm)")
    p.add_argument("--radio-plantilla", type=_intervalo, default=RADIO_PLANTILLA, help="mm, p. ej. 15-22")
    p.add_argument("--desplazamiento", type=float, default=0.0, help="mm máx. del centro de la plantilla al agujero")
    p.add_argument("--solo-zonas", type=lambda t: [int(z) for z in t.split(",")], default=None,
                   help="con --zonas, solo estas (índices de ZONAS separados por comas)")
    p.add_argument("--correccion", help="modelo ACT: graba la corrección tras --pasos-act pasos de ACT (DAgger)")
    p.add_argument("--pasos-act", type=int, default=45)
    p.add_argument("--semilla", type=int, default=0)
    p.add_argument("--sobrescribir", action="store_true")
    p.add_argument("--push", action="store_true", help="sube el dataset al Hub al acabar")
    p.add_argument("--privado", action="store_true", help="con --push, repo privado")
    a = p.parse_args(argv)
    t0 = time.perf_counter()
    r = grabar(a.salida, a.repo_id, a.episodios, a.resolucion, a.semilla, a.sobrescribir, a.push, a.privado,
               a.habilidad, a.render, a.zonas, a.radio_plantilla, a.desplazamiento, correccion=a.correccion,
               pasos_act=a.pasos_act, zonas_lista=a.solo_zonas)
    print(f"{r['guardados']}/{r['intentos']} episodios guardados en {a.salida} "
          f"({r['descartados']} descartados: {r['motivos_descarte']}; {r['agujeros_fuera_de_alcance']} agujeros fuera "
          f"de alcance) "
          f"en {time.perf_counter() - t0:.0f} s")
    return r


if __name__ == "__main__":
    main()
