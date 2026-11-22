"""Demostraciones guionizadas de la v2 (mesa de montaje) y grabación a un `LeRobotDataset` multitarea.

Órdenes del núcleo (`task` = la orden exacta del vocabulario del contrato):
- `monta una unión en T` / `monta una unión en esquina`: aproximación a la aleta de la chapa tumbada → bajada →
  cierre → elevación → transporte girándola 90° → bajada hasta dejar el canto a unos milímetros de la línea →
  suelta (los imanes cierran la junta) → retirada → reposo. Si la muñeca no llega a dejar la chapa vertical, la
  deja algo inclinada hacia el cordón (`inclinacion`) y los imanes la enderezan.
- `señala el cordón`: con la pinza cerrada, la punta de la pinza recorre el cordón de la junta montada por encima
  y por fuera (a `DISTANCIA_SENAL` mm de la línea) y vuelve a reposo.
- `coge la antorcha y suelda la junta`: coge la antorcha del soporte por el mango → suelda el cordón con el
  planificador de la v1 (45°, empuje, velocidad del contrato) → la devuelve al soporte → reposo.

El guion se planifica por tramos y se replanifica con lo que mide la simulación después de cada agarre (la pose
real de la chapa o de la antorcha en la pinza), igual que haría un operador que mira lo que tiene en la mano. La
acción grabada es la posición articular objetivo, como la que manda el brazo guía.

Uso:
    python -m sim.demostraciones montaje --por-orden 4 --salida datos/lewelder_v2 --repo-id local/lewelder_v2
    python -m sim.demos_montaje --por-orden 4 --ordenes "monta una unión en T" --ruido 0
"""
from __future__ import annotations

import argparse
import json
import shutil
import time
from dataclasses import dataclass, field, replace
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from lewelder import contrato as c
from sim import montaje as mt
from sim.cinematica import Cinematica
from sim.demostraciones import (V_MAX_ARTICULAR, Guion, Planificador, _minimo_tiron, _ruido_suave,
                                caracteristicas)
from sim.entorno import RESOLUCION, ROBOT_TYPE, lerobot_a_rad, rad_a_lerobot
from sim.montaje import TipoJunta

RAIZ = Path(__file__).resolve().parents[1]
MM = mt.MM
DISTANCIA_SENAL = (8.0, 8.0)  # mm: la punta de la pinza va por fuera (-Y) y por encima (+Z) del cordón
REINTENTOS_SEMILLA = 5
LIMITE_IK_MM = 1.0
LIMITE_IK_GRADOS = 1.0
# Al dejar la chapa, la muñeca de 5 ejes no siempre corrige el pequeño giro que la aleta coge en la pinza: hasta 3°
# los imanes lo absorben.
LIMITE_COLOCACION_GRADOS = 3.0


@dataclass
class GuionV2:
    """Parámetros de una demostración v2 (mm, s, grados). `ruido = 0` es el guion exacto."""

    ruido: float = 1.0
    t_aproximacion: float = 2.5
    t_bajada: float = 1.2
    t_cierre: float = 0.6
    t_espera: float = 0.3
    t_elevacion: float = 1.0
    t_transporte: float = 3.0
    t_colocacion: float = 1.2
    t_suelta: float = 0.5
    t_retirada: float = 1.0
    t_vuelta: float = 2.5
    t_final: float = 0.5
    altura_aproximacion: float = 35.0  # mm por encima de lo que se va a coger, a lo largo de la aproximación
    altura_elevacion: float = 35.0
    elevacion_antorcha: float = 75.0  # mm para sacar la antorcha del tubo del soporte (punta a 6, tubo hasta 66)
    altura_colocacion: float = 90.0  # la chapa llega a su sitio bajando esto en vertical (desde arriba de la base)
    holgura_suelta: float = 3.0  # mm entre el canto de la chapa y la base al soltarla
    retirada: float = 30.0  # mm hacia atrás a lo largo de la aproximación tras soltar
    cabeceo_retirada: float = 15.0  # grados que baja la pinza para soltar la aleta antes de retroceder
    inclinaciones: tuple[float, ...] = (0.0, 3.0, 6.0, 9.0, 12.0, 15.0, 18.0)
    velocidad_senal: float = 30.0  # mm/s al recorrer el cordón señalándolo
    soldadura: Guion = field(default_factory=Guion)  # guion de la v1 para el cordón
    # ruido (desviación típica con ruido = 1)
    ruido_duracion: float = 0.15
    ruido_reposo: float = 4.0  # grados
    ruido_agarre: float = 2.0  # mm a lo largo de la aleta y del mango
    ruido_posicion: float = 1.0  # mm en los puntos de paso
    ruido_inclinacion: float = 1.5  # grados al soltar la chapa


@dataclass
class ResultadoV2:
    orden: str
    junta: str
    semilla: int
    exito: bool
    fotogramas: int
    segundos: float
    pose_chapa: tuple | None = None
    inclinacion: float | None = None
    info: dict = field(default_factory=dict)
    muestras: list = field(default_factory=list)
    nota: float | None = None
    episodio: int | None = None
    motivo: str = ""


class SinSolucion(RuntimeError):
    """La IK no encuentra una postura válida para este guion (se reintenta con otra semilla)."""


# --- planificador de un cordón (v1) en la mesa de montaje -----------------------------------------------------------
class PlanificadorCordon(Planificador):
    """El planificador de soldadura de la v1, con el marco del cordón de la junta montada y la punta medida."""

    def __init__(self, entorno: mt.EntornoMontaje, junta):
        junta = TipoJunta(junta)
        self.ent = SimpleNamespace(anclaje=f"montaje ({junta.value})", tipo=junta)
        self.cin = Cinematica(entorno.modelo, sitio_pose="herramienta")
        self.junta = junta
        lo, hi = self.cin.rangos[:5, 0], self.cin.rangos[:5, 1]
        rng = np.random.default_rng(1234)
        self._semillas = [np.r_[rng.uniform(lo * 0.9, hi * 0.9), 0.0] for _ in range(40)]

    def _ik(self, p_pieza, d_pieza, q_ini):
        R, o = mt.marco_cordon(self.junta)
        return self.cin.inversa_pose((o + R @ np.asarray(p_pieza)) * MM, R @ np.asarray(d_pieza), q_ini)


# --- ejecución por tramos -------------------------------------------------------------------------------------------
class Demostrador:
    """Planifica y ejecuta una demostración por tramos. `al_fotograma(obs, accion)` se llama antes de cada paso."""

    def __init__(self, entorno: mt.EntornoMontaje, guion: GuionV2, rng: np.random.Generator, al_fotograma=None):
        self.ent = entorno
        self.g = guion
        self.rng = rng
        self.al_fotograma = al_fotograma
        self.cin = Cinematica(entorno.modelo, sitio_pose="gripperframe")
        self.obs = entorno.observacion()
        self.q = lerobot_a_rad(entorno.estado().astype(float))  # último objetivo mandado (rad)
        self.q_reposo = self.q.copy()
        self.fotogramas = 0
        self.fases: list[str] = []
        self.gatillo: list[bool] = []
        self.muestras: list = []
        lo, hi = self.cin.rangos[:5, 0], self.cin.rangos[:5, 1]
        semillas = np.random.default_rng(4321)
        self._semillas = [np.r_[semillas.uniform(lo * 0.9, hi * 0.9), 0.0] for _ in range(30)]

    # --- utilidades ----------------------------------------------------------------------------------------
    def dur(self, t: float) -> float:
        return max(0.3, t * (1 + self.g.ruido * self.g.ruido_duracion * self.rng.normal()))

    def ruido_mm(self, escala: float = 1.0) -> np.ndarray:
        return self.g.ruido * self.g.ruido_posicion * escala * self.rng.normal(size=3)

    def mover(self, objetivos, fase: str, gatillo=None, registrar_muestras: bool = False) -> None:
        for k, q in enumerate(objetivos):
            q = np.asarray(q, dtype=float)
            accion = rad_a_lerobot(q).astype(np.float32)
            if self.al_fotograma is not None:
                self.al_fotograma(self.obs, accion)
            self.obs = self.ent.step(accion)
            self.q = q.copy()
            self.fotogramas += 1
            self.fases.append(fase)
            g = bool(gatillo[k]) if gatillo is not None else False
            self.gatillo.append(g)
            if registrar_muestras:
                self.muestras.append(self.ent.muestra(gatillo=g))

    def quieto(self, t: float, fase: str) -> None:
        self.mover([self.q] * int(round(t * c.FPS_DATASET)), fase)

    def articular(self, q_b, t: float) -> list[np.ndarray]:
        """Interpolación articular de mínimo tirón desde el último objetivo (respeta la velocidad máxima)."""
        q_a = self.q
        t = max(self.dur(t), 1.875 * np.max(np.abs(np.asarray(q_b)[:5] - q_a[:5])) / V_MAX_ARTICULAR)
        n = max(1, int(round(t * c.FPS_DATASET)))
        return [q_a + _minimo_tiron((k + 1) / n) * (np.asarray(q_b) - q_a) for k in range(n)]

    def pinza(self, valor: float, t: float) -> list[np.ndarray]:
        n = max(1, int(round(self.dur(t) * c.FPS_DATASET)))
        q0 = self.q.copy()
        out = []
        for k in range(n):
            q = q0.copy()
            q[5] = q0[5] + _minimo_tiron((k + 1) / n) * (valor - q0[5])
            out.append(q)
        return out

    def ik(self, R, p_mm, q_ini, sitio="gripperframe", solo_direccion=False):
        """IK de la pose (R, p en mm) del sitio; con `solo_direccion`, solo posición y eje x (aproximación)."""
        if solo_direccion:
            q, e, a = self.cin.inversa_pose(np.asarray(p_mm) * MM, R[:, 0], q_ini, sitio=sitio, eje_local=(1, 0, 0))
        else:
            q, e, a = self.cin.inversa_6d(np.asarray(p_mm) * MM, R, q_ini, sitio=sitio)
        return q, e / MM, np.degrees(a)

    def ik_rama(self, R, p_mm, q_ref, sitio="gripperframe", siguientes=(), lim_mm=LIMITE_IK_MM,
                lim_grados=LIMITE_IK_GRADOS, solo_direccion=False):
        """IK desde muchas semillas; de las ramas que también llegan a `siguientes` (poses (R, p) recorridas por
        continuidad), la más cercana a `q_ref` y lejos de los límites."""
        lo, hi = self.cin.rangos[:5, 0], self.cin.rangos[:5, 1]
        mejor, mejor_coste = None, np.inf
        vistas = []
        for s in [q_ref] + self._semillas:
            s = np.array(s, dtype=float)
            s[5] = q_ref[5]
            q, e, a = self.ik(R, p_mm, s, sitio, solo_direccion)
            if e > lim_mm or a > lim_grados or any(np.max(np.abs(q[:5] - v[:5])) < 0.05 for v in vistas):
                continue
            vistas.append(q)
            holgura = float(np.min(np.minimum(q[:5] - lo, hi - q[:5])))
            qq, bien = q, True
            for Rs, ps in siguientes:
                qq, e2, a2 = self.ik(Rs, ps, qq, sitio, solo_direccion)
                bien = bien and e2 < lim_mm and a2 < lim_grados
                holgura = min(holgura, float(np.min(np.minimum(qq[:5] - lo, hi - qq[:5]))))
            if not bien:
                continue
            coste = np.linalg.norm(q[:5] - q_ref[:5]) - 4.0 * min(holgura, 0.3)
            if coste < mejor_coste:
                mejor, mejor_coste = q, coste
        return mejor

    def cartesiano(self, poses, sitio="gripperframe", lim_mm=LIMITE_IK_MM, lim_grados=LIMITE_IK_GRADOS,
                   comprobar_final_solo=False, solo_direccion=False):
        """IK fotograma a fotograma a lo largo de `poses` [(R, p_mm)], por continuidad desde el último objetivo.

        Con `solo_direccion` solo se pide la posición y la dirección de aproximación (eje x del sitio): 5 condiciones
        para 5 articulaciones, siempre alcanzable si la pose lo era (para retirarse sin pelear con el giro)."""
        q = self.q.copy()
        out = []
        for k, (R, p) in enumerate(poses):
            q, e, a = self.ik(R, p, q, sitio, solo_direccion)
            if (not comprobar_final_solo or k == len(poses) - 1) and (e > lim_mm or a > lim_grados):
                raise SinSolucion(f"IK cartesiana: {e:.1f} mm / {a:.1f}°")
            out.append(q.copy())
        return out

    def recta(self, R, p_a, p_b, t: float, R_b=None):
        """Poses de una recta de p_a a p_b (mm) en `t` s con perfil de mínimo tirón (y giro interpolado si R_b)."""
        n = max(1, int(round(self.dur(t) * c.FPS_DATASET)))
        poses = []
        for k in range(n):
            s = _minimo_tiron((k + 1) / n)
            Rk = R if R_b is None else _interpolar_giro(R, R_b, s)
            poses.append((Rk, np.asarray(p_a) + s * (np.asarray(p_b) - np.asarray(p_a))))
        return poses

    def pivotar(self, R, p, pivote, grados: float, t: float):
        """Poses que giran la pinza `grados` alrededor de su eje y (b) por `pivote`, hacia donde baja la
        aproximación (las yemas bajan)."""
        b = R[:, 1]
        signo = 1.0
        if (_giro_eje(b, 5.0) @ R[:, 0])[2] > (_giro_eje(b, -5.0) @ R[:, 0])[2]:
            signo = -1.0
        n = max(1, int(round(self.dur(t) * c.FPS_DATASET)))
        poses = []
        for k in range(n):
            G = _giro_eje(b, signo * grados * _minimo_tiron((k + 1) / n))
            poses.append((G @ R, pivote + G @ (np.asarray(p) - pivote)))
        return poses

    def volver_a_reposo(self) -> None:
        q_fin = self.q_reposo.copy()
        q_fin[:5] += np.radians(self.g.ruido * self.g.ruido_reposo * 0.5 * self.rng.normal(size=5))
        q_fin[5] = self.q[5]
        self.mover(self.articular(q_fin, self.g.t_vuelta), "vuelta")
        self.quieto(self.g.t_final, "final")


def _base_con_aproximacion(a) -> np.ndarray:
    """Una base ortonormal (columnas) con el eje x en la dirección `a` (los otros dos, cualesquiera)."""
    a = np.asarray(a, dtype=float) / np.linalg.norm(a)
    ref = np.array([0.0, 0.0, 1.0]) if abs(a[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
    y = np.cross(ref, a)
    y /= np.linalg.norm(y)
    return np.column_stack([a, y, np.cross(a, y)])


def _giro_eje(eje, grados):
    """Matriz de giro de `grados` alrededor de `eje` (Rodrigues)."""
    eje = np.asarray(eje, dtype=float) / np.linalg.norm(eje)
    K = np.array([[0, -eje[2], eje[1]], [eje[2], 0, -eje[0]], [-eje[1], eje[0], 0]])
    a = np.radians(grados)
    return np.eye(3) + np.sin(a) * K + (1 - np.cos(a)) * K @ K


def _interpolar_giro(Ra, Rb, s):
    """Giro intermedio (slerp) entre Ra y Rb."""
    Rr = Ra.T @ Rb
    ang = np.arccos(np.clip((np.trace(Rr) - 1) / 2, -1.0, 1.0))
    if ang < 1e-9:
        return Ra
    eje = np.array([Rr[2, 1] - Rr[1, 2], Rr[0, 2] - Rr[2, 0], Rr[1, 0] - Rr[0, 1]]) / (2 * np.sin(ang))
    K = np.array([[0, -eje[2], eje[1]], [eje[2], 0, -eje[0]], [-eje[1], eje[0], 0]])
    a = s * ang
    return Ra @ (np.eye(3) + np.sin(a) * K + (1 - np.cos(a)) * K @ K)


# --- guiones --------------------------------------------------------------------------------------------------------
def guion_montar(d: Demostrador, junta) -> dict:
    """Coge la chapa por la aleta, la gira 90° y la deja junto a la línea de `junta` para que la cierren los imanes."""
    g, ent = d.g, d.ent
    junta = TipoJunta(junta)
    # 1) Agarre de la aleta (pose medida de la chapa tumbada)
    Rl, pl = ent.pose_movil()
    Rg, pg = mt.agarre_aleta()
    pg = pg + np.array([g.ruido * g.ruido_agarre * d.rng.normal(), 0.0, 0.0])  # a lo largo de la aleta
    R_ag, p_ag = mt.componer(Rl, pl, Rg, pg)
    aprox = R_ag[:, 0]
    p_pre = p_ag - g.altura_aproximacion * aprox + d.ruido_mm()
    q_pre = d.ik_rama(R_ag, p_pre, d.q, siguientes=[(R_ag, p_ag)])
    if q_pre is None:
        raise SinSolucion("sin IK para coger la aleta")
    q_pre[5] = mt.PINZA_ABIERTA
    d.mover(d.articular(q_pre, g.t_aproximacion), "aproximacion")
    d.mover(d.cartesiano(d.recta(R_ag, p_pre, p_ag, g.t_bajada)), "bajada")
    d.mover(d.pinza(mt.PINZA_CERRADA, g.t_cierre), "cierre")
    d.quieto(g.t_espera, "cierre")
    arriba = p_ag + np.array([0.0, 0.0, g.altura_elevacion]) + d.ruido_mm()
    d.mover(d.cartesiano(d.recta(R_ag, p_ag, arriba, g.t_elevacion)), "elevacion")
    if not ent.chapa_agarrada():
        raise SinSolucion("la chapa no ha quedado cogida")

    # 2) Colocación: se planifica con la pose real de la chapa en la pinza (sitio `herramienta` = origen de la chapa)
    ent.medir_herramienta("movil")
    R0, p0 = mt.pose_montada(junta)
    pivote = np.array([0.0, 0.0, -c.GROSOR_CHAPA / 2])  # canto inferior del lado de la aleta
    elegido = None
    for inc in g.inclinaciones:
        inc_k = max(0.0, inc + g.ruido * g.ruido_inclinacion * d.rng.normal()) if inc > 0 else inc
        Rr = R0 @ mt.rot_x(inc_k)
        pr = p0 + R0 @ (pivote - mt.rot_x(inc_k) @ pivote) + np.array([0.0, 0.0, g.holgura_suelta])
        pr = pr + np.r_[d.ruido_mm(0.5)[:2], 0.0]
        p_alto = pr + np.array([0.0, 0.0, g.altura_colocacion])
        q_alto = d.ik_rama(Rr, p_alto, d.q, sitio="herramienta", siguientes=[(Rr, pr)],
                           lim_grados=LIMITE_COLOCACION_GRADOS)
        if q_alto is not None:
            elegido = (inc_k, Rr, pr, p_alto, q_alto)
            break
    if elegido is None:
        raise SinSolucion(f"sin IK para dejar la chapa en la junta {junta.value}")
    inc_k, Rr, pr, p_alto, q_alto = elegido
    q_alto[5] = d.q[5]
    d.mover(d.articular(q_alto, g.t_transporte), "transporte")
    d.mover(d.cartesiano(d.recta(Rr, p_alto, pr, g.t_colocacion), sitio="herramienta",
                         lim_grados=LIMITE_COLOCACION_GRADOS), "colocacion")

    # 3) Suelta: los imanes hacen el resto
    d.mover(d.pinza(0.35, g.t_suelta), "suelta")
    d.quieto(g.t_espera, "suelta")
    # Retirada: el dedo fijo queda bajo la aleta. Se cabecea la pinza hacia abajo pivotando en el extremo libre de
    # la aleta (las yemas bajan y la sueltan), se retrocede a lo largo de la aproximación y se sube.
    s = ent.modelo.site("gripperframe").id
    Rs = ent.datos.site_xmat[s].reshape(3, 3).copy()
    ps = ent.datos.site_xpos[s] / MM
    pivote_aleta = ps - (mt.PROFUNDIDAD_AGARRE + 1.0) * Rs[:, 0]
    poses = d.pivotar(Rs, ps, pivote_aleta, g.cabeceo_retirada, 0.6)
    R1, p1 = poses[-1]
    atras = p1 - g.retirada * R1[:, 0]
    arriba = atras + np.array([0.0, 0.0, 30.0])
    poses += d.recta(R1, p1, atras, g.t_retirada) + d.recta(R1, atras, arriba, 0.6)
    d.mover(d.cartesiano(poses, solo_direccion=True), "retirada")
    d.volver_a_reposo()
    return {"inclinacion": round(float(inc_k), 2)}


def guion_senalar(d: Demostrador) -> dict:
    """Con la pinza cerrada, recorre el cordón de la junta montada con la punta de la pinza."""
    g, ent = d.g, d.ent
    junta = ent.junta_cerrada or ent.junta
    R_c, _ = mt.marco_cordon(junta)
    dy, dz = DISTANCIA_SENAL
    dy += g.ruido * 1.0 * d.rng.normal()
    dz += g.ruido * 1.0 * d.rng.normal()
    x0, x1 = -4.0, c.LONGITUD_CORDON + 4.0
    p_ini = mt.cordon_a_mesa(junta, (x0, -dy, dz))
    p_fin = mt.cordon_a_mesa(junta, (x1, -dy, dz))
    p_pre = p_ini + np.array([0.0, 0.0, g.altura_aproximacion])
    # La pinza apunta hacia abajo y hacia fuera (por encima de la chapa de pie). Con 5 ejes la aproximación va en
    # el plano vertical del brazo: la inclinación es radial en cada punto. Se busca la más vertical a la que llega
    # en todo el cordón; solo cuentan la posición y la dirección (el giro alrededor del eje queda libre).
    def orientacion(p, inc):
        radial = np.array([p[0], p[1], 0.0]) / np.hypot(p[0], p[1])
        return _base_con_aproximacion(np.cos(np.radians(inc)) * radial - np.sin(np.radians(inc)) * np.array([0, 0, 1.0]))

    elegido = None
    for inc in (90.0, 80.0, 75.0, 70.0, 65.0, 60.0):
        inc_k = inc - abs(g.ruido * 2.0 * d.rng.normal()) if inc < 90 else inc
        p_mid = (p_ini + p_fin) / 2
        p_sal = p_fin + np.array([0, 0, g.altura_aproximacion])
        q_pre = d.ik_rama(orientacion(p_pre, inc_k), p_pre, d.q, sitio="punta_pinza", solo_direccion=True,
                          siguientes=[(orientacion(p, inc_k), p) for p in (p_ini, p_mid, p_fin, p_sal)])
        if q_pre is not None:
            elegido = inc_k
            break
    if elegido is None:
        raise SinSolucion("sin IK para señalar el cordón")
    q_pre[5] = mt.PINZA_CERRADA
    d.mover(d.articular(q_pre, g.t_aproximacion), "aproximacion")
    poses = [(orientacion(p, elegido), p) for _, p in d.recta(np.eye(3), p_pre, p_ini, g.t_bajada)]
    d.mover(d.cartesiano(poses, sitio="punta_pinza", solo_direccion=True), "bajada")
    d.quieto(0.3, "senal")
    # Recorrido con una pequeña ondulación humana (suavizada)
    t = (x1 - x0) / (g.velocidad_senal * (1 + 0.1 * g.ruido * d.rng.normal()))
    n = max(2, int(round(t * c.FPS_DATASET)))
    ondula = g.ruido * 1.0 * _ruido_suave(d.rng, n, 0.6)
    poses = []
    for k in range(n):
        s = _minimo_tiron((k + 1) / n)
        p = p_ini + s * (p_fin - p_ini) + R_c @ np.array([0.0, ondula[k], 0.0])
        poses.append((orientacion(p, elegido), p))
    d.mover(d.cartesiano(poses, sitio="punta_pinza", solo_direccion=True), "senal")
    d.quieto(0.3, "senal")
    poses = [(orientacion(p, elegido), p) for _, p in
             d.recta(np.eye(3), p_fin, p_fin + np.array([0, 0, g.altura_aproximacion]), g.t_retirada)]
    d.mover(d.cartesiano(poses, sitio="punta_pinza", solo_direccion=True, lim_mm=5.0, lim_grados=10.0), "retirada")
    d.volver_a_reposo()
    return {"inclinacion": round(float(elegido), 2)}


def guion_soldar(d: Demostrador) -> dict:
    """Coge la antorcha del soporte, suelda el cordón de la junta montada y la devuelve al soporte."""
    g, ent = d.g, d.ent
    junta = ent.junta_cerrada or ent.junta
    # 1) Coger la antorcha por el mango
    Ra, pa = ent.pose_antorcha()
    Rm, pm = mt.agarre_mango()
    pm = pm + np.array([0.0, 0.0, g.ruido * g.ruido_agarre * 0.5 * d.rng.normal()])  # a lo largo del eje
    R_ag, p_ag = mt.componer(Ra, pa, Rm, pm)
    # La pinza llega en horizontal (dedos a los lados de las caras planas) pero baja en vertical: acercarse desde el
    # robot a la altura del mango queda fuera de alcance.
    p_pre = p_ag + np.array([0.0, 0.0, g.altura_aproximacion]) + d.ruido_mm()
    p_arriba = p_ag + np.array([0.0, 0.0, g.elevacion_antorcha])
    # Con 5 ejes queda un giro residual de ~2,5° (el mango no está justo en el plano del brazo): se admite hasta 3°.
    lim = LIMITE_COLOCACION_GRADOS
    q_pre = d.ik_rama(R_ag, p_pre, d.q, siguientes=[(R_ag, p_ag), (R_ag, p_arriba)], lim_grados=lim)
    if q_pre is None:
        raise SinSolucion("sin IK para coger la antorcha")
    q_pre[5] = mt.PINZA_ABIERTA
    d.mover(d.articular(q_pre, g.t_aproximacion), "aproximacion")
    d.mover(d.cartesiano(d.recta(R_ag, p_pre, p_ag, g.t_bajada), lim_grados=lim), "bajada")
    d.mover(d.pinza(mt.PINZA_CERRADA, g.t_cierre), "cierre")
    d.quieto(g.t_espera, "cierre")
    d.mover(d.cartesiano(d.recta(R_ag, p_ag, p_arriba, 1.5 * g.t_elevacion), lim_grados=lim), "elevacion")
    if not ent.antorcha_agarrada():
        raise SinSolucion("la antorcha no ha quedado cogida")
    q_arriba = d.q.copy()

    # 2) Soldar con el planificador de la v1 (punta medida en la pinza)
    ent.medir_herramienta("antorcha")
    try:
        plan = PlanificadorCordon(ent, junta).planificar(rad_a_lerobot(d.q), replace(g.soldadura, ruido=g.ruido),
                                                         d.rng)
    except RuntimeError as e:
        raise SinSolucion(str(e)) from e
    if plan.error_ik > 0.5 or plan.error_ik_ang > 0.5:
        raise SinSolucion(f"IK del cordón: {plan.error_ik:.1f} mm / {plan.error_ik_ang:.1f}°")
    fin = plan.fase.index("vuelta") if "vuelta" in plan.fase else len(plan)
    for fase in ("aproximacion", "bajada", "espera", "cordon", "subida"):
        idx = [k for k in range(fin) if plan.fase[k] == fase]
        if idx:
            qs = [np.r_[plan.q[k][:5], d.q[5]] for k in idx]
            d.mover(qs, "soldar_" + fase, gatillo=[plan.gatillo[k] for k in idx], registrar_muestras=True)

    # 3) Devolver la antorcha al soporte: misma postura que al cogerla, otra vez arriba y bajando en vertical
    d.mover(d.articular(q_arriba, g.t_transporte), "devolver")
    d.mover(d.cartesiano(d.recta(R_ag, p_arriba, p_ag + np.array([0.0, 0.0, 1.0]), g.t_colocacion),
                         lim_mm=2.0, lim_grados=lim), "devolver")
    d.mover(d.pinza(mt.PINZA_ABIERTA, g.t_suelta), "suelta")
    d.quieto(g.t_espera, "suelta")
    s = ent.modelo.site("gripperframe").id
    ps = ent.datos.site_xpos[s] / MM
    d.mover(d.cartesiano(d.recta(R_ag, ps, ps + np.array([0.0, 0.0, g.altura_aproximacion]), g.t_retirada),
                         lim_mm=2.0, lim_grados=lim), "retirada")
    d.volver_a_reposo()
    return {"error_ik_cordon_mm": round(plan.error_ik, 3)}


def ejecutar_orden(entorno: mt.EntornoMontaje, orden: str, guion: GuionV2, semilla: int = 0, junta=None,
                   pose_chapa=None, al_fotograma=None) -> ResultadoV2:
    """Reinicia el entorno para `orden` y ejecuta su demostración. Lanza `SinSolucion` si la IK no llega (antes o
    durante la ejecución); el llamador decide si reintenta con otra semilla."""
    t0 = time.perf_counter()
    rng = np.random.default_rng(semilla)
    if junta is None and mt.junta_de_orden(orden) is None:  # la junta montada varía aunque no haya ruido
        junta = list(TipoJunta)[int(np.random.default_rng([semilla, 11]).integers(len(TipoJunta)))]
    entorno.reset(orden, semilla=semilla if guion.ruido > 0 else None, junta=junta,
                  pose_chapa=pose_chapa if pose_chapa is not None else (
                      entorno.pose_aleatoria_chapa(np.random.default_rng([semilla, 7]))
                      if mt.junta_de_orden(orden) is not None else None))
    d = Demostrador(entorno, guion, rng, al_fotograma)
    junta_m = mt.junta_de_orden(orden)
    try:
        if junta_m is not None:
            extra = guion_montar(d, junta_m)
        elif orden == mt.ORDEN_SENALAR:
            extra = guion_senalar(d)
        elif orden == mt.ORDEN_SOLDAR:
            extra = guion_soldar(d)
        else:
            raise NotImplementedError(orden)
    except SinSolucion as e:
        raise SinSolucion(f"{e} (después de: {d.fases[-1] if d.fases else 'nada'})") from e
    res = ResultadoV2(orden=orden, junta=(entorno.junta.value if entorno.junta else ""), semilla=semilla,
                      exito=entorno.exito(orden), fotogramas=d.fotogramas, segundos=time.perf_counter() - t0,
                      pose_chapa=entorno.pose_inicial_chapa, inclinacion=extra.get("inclinacion"),
                      info={**entorno.info(), **extra}, muestras=d.muestras)
    if orden == mt.ORDEN_SOLDAR and d.muestras:
        from lewelder.metricas import evaluar_pasada

        res.nota = float(evaluar_pasada(d.muestras, c.TipoPieza.T, c.NIVEL_JURADO).nota)
    return res


# --- dataset --------------------------------------------------------------------------------------------------------
def grabar_v2(salida: Path, repo_id: str, ordenes: list[str], por_orden: int, guion: GuionV2,
              resolucion=RESOLUCION, semilla: int = 0, sobrescribir: bool = False, sombras: bool = True,
              max_intentos: int = REINTENTOS_SEMILLA) -> list[ResultadoV2]:
    """Graba `por_orden` demostraciones con éxito de cada orden (intercaladas). Solo entran en el dataset las que
    terminan con `exito`; las que no tienen solución de IK se reintentan con otra semilla (sin grabar nada) y las
    fallidas se descartan. Todo queda en `<salida>/exitos.json` (y la nota de las soldaduras en `notas.json`)."""
    from lerobot.datasets.lerobot_dataset import LeRobotDataset

    salida = Path(salida)
    if salida.exists():
        if not sobrescribir:
            raise FileExistsError(f"{salida} ya existe (usa --sobrescribir)")
        shutil.rmtree(salida)
    ds = LeRobotDataset.create(repo_id=repo_id, fps=c.FPS_DATASET, features=caracteristicas(resolucion),
                               root=salida, robot_type=ROBOT_TYPE, use_videos=True, image_writer_threads=4)
    entorno = mt.EntornoMontaje(resolucion=resolucion, render=True, sombras=sombras)
    resultados: list[ResultadoV2] = []
    try:
        for i in range(por_orden):
            for k, orden in enumerate(ordenes):
                hecho = False
                for intento in range(max_intentos):
                    semilla_i = semilla + 1000 * i + 37 * k + 100_000 * intento

                    def guardar(obs, accion, orden=orden):
                        ds.add_frame({**obs, "action": accion, "task": orden})

                    try:
                        res = ejecutar_orden(entorno, orden, guion, semilla_i, al_fotograma=guardar)
                    except SinSolucion as e:
                        ds.clear_episode_buffer()
                        res = ResultadoV2(orden, entorno.junta.value if entorno.junta else "", semilla_i, False,
                                          0, 0.0, pose_chapa=entorno.pose_inicial_chapa, motivo=str(e))
                    t1 = time.perf_counter()
                    if res.exito:
                        res.episodio = ds.num_episodes
                        ds.save_episode(parallel_encoding=False)  # sin fork: el render EGL usa hilos
                        hecho = True
                    else:
                        ds.clear_episode_buffer()
                        res.motivo = res.motivo or "no cumple la orden"
                    res.segundos += time.perf_counter() - t1
                    resultados.append(res)
                    print(f"{orden:38s} {res.junta:8s} semilla {semilla_i:7d} "
                          f"{'GUARDADA' if res.exito else 'descartada':10s} {res.fotogramas:5d} fotogramas "
                          f"{res.segundos:6.1f} s  {res.motivo}", flush=True)
                    if hecho:
                        break
    finally:
        ds.finalize()
        entorno.cerrar()
        guardar_registro(salida, resultados)
    return resultados


def guardar_registro(salida: Path, resultados: list[ResultadoV2]) -> None:
    """`exitos.json` (todas las demostraciones intentadas) y `notas.json` (nota de las soldaduras)."""
    salida = Path(salida)
    salida.mkdir(parents=True, exist_ok=True)
    demos = [{"demo": i, "orden": r.orden, "junta": r.junta, "semilla": r.semilla, "exito": r.exito,
              "episodio": r.episodio, "fotogramas": r.fotogramas, "segundos": round(r.segundos, 2),
              "pose_chapa": r.pose_chapa, "inclinacion": r.inclinacion, "motivo": r.motivo,
              "nota": r.nota, "info": r.info} for i, r in enumerate(resultados)]
    por_orden = {}
    for r in resultados:
        e = por_orden.setdefault(r.orden, {"intentos": 0, "exitos": 0, "segundos_medios": 0.0})
        e["intentos"] += 1
        e["exitos"] += int(r.exito)
    for o, e in por_orden.items():
        ok = [r.segundos for r in resultados if r.orden == o and r.exito]
        e["segundos_medios"] = round(float(np.mean(ok)), 1) if ok else None
        e["fotogramas_medios"] = round(float(np.mean([r.fotogramas for r in resultados
                                                      if r.orden == o and r.exito])), 0) if ok else None
    (salida / "exitos.json").write_text(json.dumps({"total": len(demos), "guardadas": sum(r.exito for r in resultados),
                                                    "por_orden": por_orden, "demostraciones": demos},
                                                   ensure_ascii=False, indent=1, default=_json), encoding="utf-8")
    notas = [{"demo": d["demo"], "episodio": d["episodio"], "junta": d["junta"], "nota": d["nota"],
              "exito": d["exito"]} for d in demos if d["orden"] == mt.ORDEN_SOLDAR]
    (salida / "notas.json").write_text(json.dumps({"nivel": c.NIVEL_JURADO, "soldaduras": notas},
                                                  ensure_ascii=False, indent=1), encoding="utf-8")


def _json(o):
    if isinstance(o, (np.floating, np.integer)):
        return o.item()
    if isinstance(o, np.ndarray):
        return o.tolist()
    raise TypeError(type(o))


def main(argv=None):
    p = argparse.ArgumentParser(description="Graba demostraciones v2 (montaje, señalar, soldar) en un LeRobotDataset.")
    p.add_argument("--ordenes", default="|".join(mt.ORDENES_NUCLEO),
                   help="órdenes separadas por '|' (por defecto las cuatro del núcleo)")
    p.add_argument("--por-orden", type=int, default=4, help="demostraciones con éxito por orden")
    p.add_argument("--salida", default=str(RAIZ / "datos" / "lewelder_v2"))
    p.add_argument("--repo-id", default="local/lewelder_v2")
    p.add_argument("--ruido", type=float, default=1.0, help="escala de la variabilidad humana (0 = guion exacto)")
    p.add_argument("--resolucion", default=f"{RESOLUCION[0]}x{RESOLUCION[1]}", help="ANCHOxALTO")
    p.add_argument("--semilla", type=int, default=0)
    p.add_argument("--sin-sombras", action="store_true", help="render sin sombras (más rápido)")
    p.add_argument("--sobrescribir", action="store_true")
    a = p.parse_args(argv)
    ordenes = [o.strip() for o in a.ordenes.split("|") if o.strip()]
    for o in ordenes:
        if o not in mt.ORDENES_NUCLEO:
            p.error(f"orden no simulada: {o!r} (válidas: {mt.ORDENES_NUCLEO})")
    resolucion = tuple(int(v) for v in a.resolucion.lower().split("x"))
    t0 = time.perf_counter()
    res = grabar_v2(Path(a.salida), a.repo_id, ordenes, a.por_orden, GuionV2(ruido=a.ruido), resolucion,
                    a.semilla, a.sobrescribir, sombras=not a.sin_sombras)
    total = time.perf_counter() - t0
    print(f"\n{len(res)} intentos en {total:.0f} s → {a.salida}")
    for o in ordenes:
        rs = [r for r in res if r.orden == o]
        ok = [r for r in rs if r.exito]
        media = np.mean([r.segundos for r in ok]) if ok else float("nan")
        print(f"  {o:38s} {len(ok)}/{len(rs)} con éxito, {media:.1f} s por episodio")


if __name__ == "__main__":
    main()
