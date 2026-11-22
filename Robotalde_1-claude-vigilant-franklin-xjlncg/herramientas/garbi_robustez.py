"""Prueba de estrés del comportamiento interactivo de Garbi (montaje lateral) en sesiones aleatorias.

En cada sesión cambian: número y sitio de los agujeros (incluidos bordes del alcance), por dónde entra el taladro,
la velocidad a la que se mueve y el ruido de la percepción (la cámara de arriba: temblor de ±σ mm, a 10 Hz y con 0,1 s
de retraso). Se mide, durante TODA la sesión: holgura mínima del brazo con el taladro y la mano, si la boca baja de la
superficie, si se acerca a cada broca apoyada y cuánta viruta queda.

    python herramientas/garbi_robustez.py [sesiones] [ruido_mm]
"""
from __future__ import annotations

import sys
from collections import deque

import numpy as np

from garbi import contrato as g
from garbi.interactivo import Seguidor, VistaTaladro, Estado
from garbi.lateral import APARCADO, ControlLateral
from garbi.mundo import EN_TABLA, MundoGarbi
from sim.entorno import lerobot_a_rad

TABLA = g.PoseTabla(360.0, 0.0, 0.0)


class Percepcion:
    """La cámara de arriba con ruido, a 10 Hz y con retraso: lo que el robot real sabrá de la punta."""

    def __init__(self, rng, ruido_mm, hz=10.0, retraso_s=0.1):
        self.rng, self.ruido = rng, ruido_mm
        self.cada = int(round(g.FPS / hz))
        self.cola = deque(maxlen=int(round(retraso_s * g.FPS)) + 1)
        self.ultima = VistaTaladro(False)
        self.k = 0

    def ver(self, juez) -> VistaTaladro:
        real = VistaTaladro(juez.taladro_visible, juez.taladro_punta.copy() if juez.taladro_visible else None)
        self.cola.append(real)
        if self.k % self.cada == 0:
            v = self.cola[0]
            if v.visible:
                p = v.punta + np.concatenate([self.rng.normal(0, self.ruido, 2), self.rng.normal(0, self.ruido / 2, 1)])
                self.ultima = VistaTaladro(True, p)
            else:
                self.ultima = VistaTaladro(False)
        self.k += 1
        return self.ultima


def sesion(semilla: int, ruido_mm: float, m: MundoGarbi, c: ControlLateral) -> dict:
    rng = np.random.default_rng(semilla)
    m.reset(semilla, tabla=TABLA, q_inicial=APARCADO)
    s = Seguidor(c)
    per = Percepcion(rng, ruido_mm)
    res = {"holgura_min": 1e9, "bajo_superficie": 0, "apoyos": 0, "acompanados": 0, "fotogramas_sin_postura": 0,
           "agujeros": 0, "max_grados_fotograma": 0.0}
    q_prev = s.q.copy()

    def fotograma():
        nonlocal q_prev
        v = per.ver(m.juez)
        q = s.paso(m.t, v, m.juez.tabla)
        m.aspiradora = s.aspiradora
        m.step(q, observar=False)
        res["max_grados_fotograma"] = max(res["max_grados_fotograma"], float(np.max(np.abs(q - q_prev))))
        q_prev = q.copy()
        q4 = lerobot_a_rad(m.estado())[:4]
        b, e = c.boca(q4)
        if b[2] - 15.0 * np.sqrt(max(0.0, 1 - e[2] ** 2)) < g.ALTURA_CARA_TABLA - 2 and \
                TABLA.contiene(b[:2], margen=-10):
            res["bajo_superficie"] += 1
        if m.juez.taladro_visible:
            res["holgura_min"] = min(res["holgura_min"], c.holgura(q4, m.juez.taladro_punta))

    def mover(desde, hasta, vel, z0, z1):
        n = max(2, int(np.linalg.norm(np.asarray(hasta) - desde) / vel * g.FPS))
        for k in range(1, n + 1):
            f = 0.5 - 0.5 * np.cos(np.pi * k / n)
            xy = np.asarray(desde) + (np.asarray(hasta) - np.asarray(desde)) * f
            m.poner_taladro(xy[0], xy[1], g.ALTURA_CARA_TABLA + z0 + (z1 - z0) * f)
            fotograma()

    n_agujeros = int(rng.integers(1, 5))
    puntos = [TABLA.a_mesa(rng.uniform([-90, -140], [90, 140])) for _ in range(n_agujeros)]
    vel = float(rng.uniform(60, 250))  # mm/s con la broca en el aire
    entrada = np.array([g.PERSONA_X + 60, rng.uniform(-250, 250)])
    for _ in range(int(0.5 * g.FPS)):
        fotograma()
    m.poner_taladro(entrada[0], entrada[1], g.ALTURA_CARA_TABLA + 60)
    actual = entrada
    for p in puntos:
        mover(actual, p, vel, 50, 50)
        mover(p, p, 1, 50, 0)  # apoya
        res["apoyos"] += 1
        acompanado = False
        for _ in range(int(1.8 * g.FPS)):
            fotograma()
            q4 = lerobot_a_rad(m.estado())[:4]
            b, _ = c.boca(q4)
            if s.estado == Estado.ACOMPANAR and np.hypot(*(b[:2] - p)) < 45:
                acompanado = True
        if acompanado:
            res["acompanados"] += 1
            m.taladrar()
            res["agujeros"] += 1
        for _ in range(int(1.5 * g.FPS)):
            fotograma()
        mover(p, p, 1, 0, 50)
        actual = p
    mover(actual, entrada, vel, 50, 110)
    m.quitar_taladro()
    for _ in range(int(30 * g.FPS)):
        fotograma()
        if s.estado == Estado.APARCADO:
            break
    res["viruta_queda"] = len(m.viruta_en_mesa(EN_TABLA))
    res["n"] = n_agujeros
    res["vel"] = vel
    res["radios"] = [float(np.hypot(*p)) for p in puntos]
    return res


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    ruido = float(sys.argv[2]) if len(sys.argv) > 2 else 3.0
    m = MundoGarbi(render=False, montaje="lateral")
    c = ControlLateral(m)
    todos = []
    for k in range(n):
        r = sesion(k, ruido, m, c)
        todos.append(r)
        print(f"sesión {k:2d}: {r['n']} agujeros (r {min(r['radios']):.0f}-{max(r['radios']):.0f} mm), vel {r['vel']:.0f} mm/s · "
              f"acompañó {r['acompanados']}/{r['apoyos']} · holgura mín {r['holgura_min']:.0f} mm · "
              f"bajo superficie {r['bajo_superficie']} fot. · viruta queda {r['viruta_queda']} · "
              f"salto máx {r['max_grados_fotograma']:.1f}°/fot", flush=True)
    apo = sum(r["apoyos"] for r in todos); aco = sum(r["acompanados"] for r in todos)
    choques = sum(r["holgura_min"] < 0 for r in todos)
    justos = sum(0 <= r["holgura_min"] < 10 for r in todos)
    print(f"\nRESUMEN ({n} sesiones, ruido {ruido} mm): acompañó {aco}/{apo} apoyos · sesiones con choque {choques} · "
          f"con holgura < 10 mm {justos} · con la boca bajo la superficie {sum(r['bajo_superficie'] > 0 for r in todos)} · "
          f"viruta que queda (media) {np.mean([r['viruta_queda'] for r in todos]):.1f}")


if __name__ == "__main__":
    main()
