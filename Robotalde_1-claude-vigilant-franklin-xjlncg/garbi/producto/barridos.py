"""Barridos fijos (tabla y tapete) y trayectorias suaves en articulaciones, a 30 Hz.

    b = barrido_tabla(vista.tabla, matriz, offset=cfg.barridos.offset_tabla, paso_px=30, margen_px=10)
    b.posturas        # n × 6 grados, una por paso de control (30 Hz), con rampas y sin pasar de la velocidad máxima
    b.puntos_px       # n × 2: el punto de la imagen de arriba que barre la boca en cada paso
    b = barrido_tapete(cfg.tapete_px, matriz, offset=cfg.barridos.offset_tapete)

    trayectoria_suave(q0, q1, velocidad=60)   # de una postura a otra con perfil de mínimo tirón (n × 6)

El zigzag va en el cuadrilátero de las 4 esquinas (interpolación bilineal de las esquinas, así sigue a la tabla aunque
esté girada o la vea en perspectiva): pasadas paralelas al lado largo, separadas `paso_px`, a `margen_px` del borde.
Cada punto se convierte en postura con la matriz (+ el offset de altura) y el camino denso se recorre con un perfil
trapezoidal (aceleración y velocidad máximas por articulación).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np

log = logging.getLogger("garbi.producto")

HZ = 30.0


def ordenar_esquinas(esquinas) -> np.ndarray:
    """4 esquinas en cualquier orden → sup-izq, sup-der, inf-der, inf-izq (en la imagen, v hacia abajo)."""
    e = np.asarray(esquinas, float).reshape(4, 2)
    c = e.mean(axis=0)
    ang = np.arctan2(e[:, 1] - c[1], e[:, 0] - c[0])
    e = e[np.argsort(ang)]  # en sentido horario en la imagen (v hacia abajo), empezando por arriba-izquierda aprox.
    k = int(np.argmin(e.sum(axis=1)))  # sup-izq: la de menor u + v
    return np.roll(e, -k, axis=0)


# --- trayectorias en articulaciones ----------------------------------------------------------------------------------
def perfil_minimo_tiron(n: int) -> np.ndarray:
    """n valores de 0 a 1 (incluidos) con el perfil de mínimo tirón 10s³ − 15s⁴ + 6s⁵."""
    s = np.linspace(0.0, 1.0, max(int(n), 2))
    return 10 * s**3 - 15 * s**4 + 6 * s**5


def trayectoria_suave(q0, q1, velocidad: float | np.ndarray = 60.0, hz: float = HZ) -> np.ndarray:
    """De `q0` a `q1` (6 grados) con mínimo tirón: arranca y para con velocidad cero y el pico no pasa de
    `velocidad` (°/s, escalar o por articulación). Devuelve n × 6 sin incluir q0 y acabando exactamente en q1."""
    q0, q1 = np.asarray(q0, float), np.asarray(q1, float)
    v = np.broadcast_to(np.asarray(velocidad, float), q0.shape)
    duracion = float(np.max(1.875 * np.abs(q1 - q0) / np.maximum(v, 1e-9)))  # pico del mínimo tirón = 1,875 × media
    n = max(int(np.ceil(duracion * hz)), 1)
    s = perfil_minimo_tiron(n + 1)[1:]
    return q0[None, :] + s[:, None] * (q1 - q0)[None, :]


def por_camino(plan: np.ndarray, velocidad, aceleracion: float = 120.0, hz: float = HZ,
               extra: np.ndarray | None = None):
    """Recorre el camino denso `plan` (m × 6) con un perfil trapezoidal en la «distancia articular» (la mayor
    diferencia entre articulaciones de cada tramo): ninguna articulación pasa de `velocidad` (°/s) ni de
    `aceleracion` (°/s²). Devuelve las posturas a `hz` (n × 6) y, si se da `extra` (m × k), lo mismo interpolado."""
    plan = np.asarray(plan, float)
    v = np.broadcast_to(np.asarray(velocidad, float), (plan.shape[1],))
    if len(plan) < 2:
        return (plan.copy(), None if extra is None else np.asarray(extra, float).copy())
    # distancia normalizada por la velocidad de cada articulación: «segundos a velocidad máxima»
    tramos = np.max(np.abs(np.diff(plan, axis=0)) / np.maximum(v, 1e-9), axis=1)
    s_acum = np.concatenate([[0.0], np.cumsum(tramos)])
    total = s_acum[-1]
    vmax_rel = 1.0  # en estas unidades la velocidad máxima es 1
    a_rel = aceleracion / float(np.max(v))
    if total < 1e-9:
        return plan[-1:].copy(), (None if extra is None else np.asarray(extra, float)[-1:].copy())
    t_acel = vmax_rel / a_rel
    d_acel = 0.5 * a_rel * t_acel**2
    if 2 * d_acel > total:  # triangular
        t_acel = np.sqrt(total / a_rel)
        vpico, t_crucero = a_rel * t_acel, 0.0
    else:
        vpico, t_crucero = vmax_rel, (total - 2 * d_acel) / vmax_rel
    T = 2 * t_acel + t_crucero
    n = max(int(np.ceil(T * hz)), 1)
    t = np.linspace(T / n, T, n)
    s = np.where(t < t_acel, 0.5 * a_rel * t**2,
                 np.where(t < t_acel + t_crucero, 0.5 * a_rel * t_acel**2 + vpico * (t - t_acel),
                          total - 0.5 * a_rel * np.maximum(T - t, 0.0) ** 2))
    s = np.clip(s, 0.0, total)
    s[-1] = total
    salida = np.stack([np.interp(s, s_acum, plan[:, j]) for j in range(plan.shape[1])], axis=1)
    otro = None
    if extra is not None:
        extra = np.asarray(extra, float)
        otro = np.stack([np.interp(s, s_acum, extra[:, j]) for j in range(extra.shape[1])], axis=1)
    return salida, otro


# --- zigzag ----------------------------------------------------------------------------------------------------------
def _bilineal_esquinas(e: np.ndarray, s: np.ndarray, t: np.ndarray) -> np.ndarray:
    """Punto del cuadrilátero (sup-izq, sup-der, inf-der, inf-izq) en (s, t) ∈ [0,1]²: s de izq a der, t de arriba
    abajo."""
    s, t = np.asarray(s, float)[..., None], np.asarray(t, float)[..., None]
    return (1 - s) * (1 - t) * e[0] + s * (1 - t) * e[1] + s * t * e[2] + (1 - s) * t * e[3]


def zigzag_px(esquinas, paso_px: float = 30.0, margen_px: float = 10.0, densidad_px: float = 3.0) -> np.ndarray:
    """Camino denso (m × 2, px) en zigzag que cubre el cuadrilátero `esquinas` menos `margen_px`: pasadas paralelas
    al lado largo, separadas como mucho `paso_px`, con puntos cada `densidad_px` como mucho."""
    e = ordenar_esquinas(esquinas)
    ancho = 0.5 * (np.linalg.norm(e[1] - e[0]) + np.linalg.norm(e[2] - e[3]))
    alto = 0.5 * (np.linalg.norm(e[3] - e[0]) + np.linalg.norm(e[2] - e[1]))
    ms, mt = min(margen_px / max(ancho, 1e-9), 0.49), min(margen_px / max(alto, 1e-9), 0.49)
    horizontal = ancho >= alto  # pasadas a lo largo del lado largo
    largo, corto = (ancho, alto) if horizontal else (alto, ancho)
    m_largo, m_corto = (ms, mt) if horizontal else (mt, ms)
    util_corto = corto * (1 - 2 * m_corto)
    n_pasadas = max(int(np.ceil(util_corto / max(paso_px, 1e-9))) + 1, 2) if util_corto > 1e-6 else 1
    cortes = np.linspace(m_corto, 1 - m_corto, n_pasadas)
    n_puntos = max(int(np.ceil(largo * (1 - 2 * m_largo) / densidad_px)) + 1, 2)
    a_lo_largo = np.linspace(m_largo, 1 - m_largo, n_puntos)
    camino = []
    for k, c in enumerate(cortes):
        tramo = a_lo_largo if k % 2 == 0 else a_lo_largo[::-1]
        if k > 0:  # el giro entre pasadas, también denso
            previo = cortes[k - 1]
            n_giro = max(int(np.ceil(abs(c - previo) * corto / densidad_px)), 1)
            giro = np.linspace(previo, c, n_giro + 1)[1:-1]
            for g in giro:
                camino.append((tramo[0], g))
        camino.extend((x, c) for x in tramo)
    st = np.array(camino)
    s, t = (st[:, 0], st[:, 1]) if horizontal else (st[:, 1], st[:, 0])
    return _bilineal_esquinas(e, s, t)


@dataclass
class Barrido:
    posturas: np.ndarray     # n × 6 grados, una por paso de control
    puntos_px: np.ndarray    # n × 2: punto de la imagen que barre la boca en cada paso
    camino_px: np.ndarray    # el zigzag denso (m × 2)

    def __len__(self) -> int:
        return len(self.posturas)


def barrido_px(esquinas, matriz, offset=None, paso_px: float = 30.0, margen_px: float = 10.0,
               velocidad: float = 40.0, aceleracion: float = 120.0, hz: float = HZ) -> Barrido:
    """Zigzag sobre el cuadrilátero `esquinas` a altura fija (postura de la matriz + `offset`)."""
    camino = zigzag_px(esquinas, paso_px, margen_px)
    avisar_antes = getattr(matriz, "avisar", True)
    fuera = 0
    try:
        if hasattr(matriz, "avisar"):
            matriz.avisar = False   # un solo aviso para todo el barrido, no uno por punto
        plan = []
        for p in camino:
            plan.append(matriz.postura_px(p, offset))
            fuera += bool(getattr(matriz, "fuera", False))
    finally:
        if hasattr(matriz, "avisar"):
            matriz.avisar = avisar_antes
    if fuera:
        log.warning("barrido: %d de %d puntos fuera de la matriz (extrapolados)", fuera, len(camino))
    plan = np.array(plan)
    posturas, puntos = por_camino(plan, velocidad, aceleracion, hz, extra=camino)
    return Barrido(posturas, puntos, camino)


def barrido_tabla(esquinas_px, matriz, altura=None, paso_px: float = 30.0, margen_px: float = 10.0,
                  velocidad: float = 40.0, aceleracion: float = 120.0, hz: float = HZ) -> Barrido:
    """Barrido completo de la tabla detectada (4 esquinas en px) a altura fija: `altura` es el offset (6 grados) que
    se suma a la postura de la matriz."""
    return barrido_px(esquinas_px, matriz, altura, paso_px, margen_px, velocidad, aceleracion, hz)


def barrido_tapete(esquinas_tapete_px, matriz, altura=None, paso_px: float = 30.0, margen_px: float = 10.0,
                   velocidad: float = 40.0, aceleracion: float = 120.0, hz: float = HZ) -> Barrido:
    """Barrido fijo de todo el tapete (esquinas de la configuración), siempre el mismo."""
    return barrido_px(esquinas_tapete_px, matriz, altura, paso_px, margen_px, velocidad, aceleracion, hz)


def limitar_velocidad_paso(q, q_previa, vmax, hz: float = HZ) -> np.ndarray:
    """Recorta el salto de cada articulación a `vmax/hz` (vmax escalar o por articulación)."""
    q = np.asarray(q, float)
    if q_previa is None:
        return q.copy()
    q_previa = np.asarray(q_previa, float)
    paso = np.broadcast_to(np.asarray(vmax, float), q.shape) / hz
    return q_previa + np.clip(q - q_previa, -paso, paso)
