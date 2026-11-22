"""Quién mueve el robot del simulador: el guion (planificador provisional), el replay de un dataset v2 o una política.

Todos cumplen la misma interfaz, `Ejecutor`:

    ok = await ejecutor.ejecutar(orden, mesa, avisar)      # orden del vocabulario v2 (`contrato.ORDENES`)

y solo mandan posiciones articulares a la `MesaSim` (`mesa.mandar(q)`) y el LED de su antorcha (`mesa.poner_led`).
Lo demás (coger la chapa, los imanes, dejar la antorcha en el soporte) lo resuelve la mesa con sus reglas, igual para
todos. `avisar(fase, progreso)` informa de la fase (`buscando`, `cogiendo`, `girando`, `encajando`, `señalando`,
`soldando`, `dejando`, `volviendo`) y del progreso 0-1 de toda la orden.

- **`EjecutorGuion`** (siempre disponible): cinemática inversa de `sim.cinematica` sobre las piezas que ve la mesa.
  Monta la chapa cogiéndola por la aleta con la pinza vertical y la deja de pie sobre la base algo inclinada (con la
  pinza a 20-45° de la horizontal: el SO-101 no llega en horizontal a 25 mm de altura); los imanes la enderezan.
  Suelda con la antorcha del soporte a 45° y 10° de empuje (`alcance`), a `VELOCIDAD_SOLDADURA`.
  Es un **sustituto provisional** del montaje de la tarea 2 (demostraciones en MuJoCo) hasta que haya dataset.
- **`EjecutorAprendido`**: una `robot.politica.Politica` (replay de un LeRobotDataset v2, ACT o SmolVLA) que recibe
  la orden como tarea. Si no sabe hacer esa orden (`PoliticaNoDisponible`: no hay episodio o checkpoint), o falla,
  `EjecutorRespaldo` cae al guion y lo dice.
"""
from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field

import mujoco
import numpy as np

from lewelder import contrato as c
from lewelder.alcance import ANGULO_AVANCE_ROBOT, Alcance, direccion_antorcha
from lewelder.mesa_sim import (
    AGARRE_ALETA,
    CHAPA_POR_DEFECTO,
    MM,
    PINZA_ABRIR,
    PINZA_CHAPA,
    PINZA_MANGO,
    MesaSim,
    Pose,
    pose_antorcha_en_soporte,
    pose_montada,
    pose_tumbada,
)

log = logging.getLogger("lewelder.guion_robot")

Avisar = Callable[[str, float], None]

HZ_CONTROL = 60.0
VELOCIDAD_SOLDADURA = 5.0  # mm/s (el centro de `VELOCIDAD_OBJETIVO`)
VELOCIDAD_ARTICULAR = np.radians(75.0)  # rad/s como mucho en los movimientos libres
T_MIN_TRAMO = 0.7  # s
ALTURA_PUNTA_ROBOT = 1.0  # mm sobre la chapa al soldar
PASO_CORDON = 3.0  # mm entre posturas de la cadena de soldadura
INCLINACIONES = (20.0, 25.0, 30.0, 35.0, 40.0, 45.0)  # grados de la pinza al dejar la chapa de pie
TOL_POS_MM = 3.0
TOL_GRADOS = 10.0
ORDENES_GUION = {"monta una unión en T", "monta una unión en esquina", "señala el cordón",
                 "coge la antorcha y suelda la junta", "desmonta la junta", "acércame la antorcha"}


class NoLlego(RuntimeError):
    """La cinemática inversa no encuentra una postura para algo del plan."""


# --- plan -----------------------------------------------------------------------------------------------------------
@dataclass
class Tramo:
    q: np.ndarray  # postura final (6, rad; la pinza incluida)
    dur: float
    fase: str
    led: bool = False
    denso: np.ndarray | None = None  # posturas intermedias equiespaciadas (trayectorias de soldar y señalar)


@dataclass
class Plan:
    tramos: list[Tramo] = field(default_factory=list)

    def duracion(self) -> float:
        return sum(t.dur for t in self.tramos)


def _suave(s: float) -> float:
    """Perfil de jerk mínimo (0 → 1)."""
    return s * s * s * (10 - 15 * s + 6 * s * s)


def postura_en(plan: Plan, q_inicio: np.ndarray, t: float) -> tuple[np.ndarray, Tramo | None, float]:
    """(postura, tramo en curso, progreso 0-1 del plan) a los t s de empezar."""
    total = plan.duracion() or 1.0
    q0 = np.asarray(q_inicio, dtype=float)
    acumulado = 0.0
    for tramo in plan.tramos:
        if t < acumulado + tramo.dur:
            s = (t - acumulado) / tramo.dur
            if tramo.denso is not None:
                puntos = np.vstack([q0[None], tramo.denso])
                f = s * (len(puntos) - 1)
                i = min(int(f), len(puntos) - 2)
                q = puntos[i] + (puntos[i + 1] - puntos[i]) * (f - i)
            else:
                q = q0 + (tramo.q - q0) * _suave(s)
            return q, tramo, min(1.0, t / total)
        acumulado += tramo.dur
        q0 = tramo.q if tramo.denso is None else tramo.denso[-1]
    return q0.copy(), None, 1.0


# --- cinemática -----------------------------------------------------------------------------------------------------
class Cinematica6:
    """IK de pose completa de la pinza (posición + dirección de aproximación + dirección de cierre, en mínimos
    cuadrados con las 5 articulaciones) y de la punta de la antorcha (posición + eje)."""

    def __init__(self, modelo: mujoco.MjModel):
        from sim.cinematica import Cinematica
        from sim.entorno import REPOSO, lerobot_a_rad

        self.cin = Cinematica(modelo, sitio_pose="punta_antorcha")
        self.reposo = lerobot_a_rad(REPOSO)
        self.reposo[5] = PINZA_ABRIR
        self.sitio_pinza = modelo.site("gripperframe").id
        self.pesos = (0.08, 0.03)  # m por rad: la posición manda; luego la aproximación y, al final, el cierre
        self._jp, self._jr = np.zeros((3, modelo.nv)), np.zeros((3, modelo.nv))
        rng = np.random.default_rng(7)
        self.semillas = [self.reposo] + [self.reposo + np.r_[rng.normal(0, 0.7, 5), 0] for _ in range(8)]

    def _pinza(self, pos_mm, R, q0, iteraciones=150):
        cin, s = self.cin, self.sitio_pinza
        q = np.array(q0, dtype=float).copy()
        objetivo = np.asarray(pos_mm, dtype=float) * MM
        anterior = np.inf
        for _ in range(iteraciones):
            p, Rc = cin.pose(q, s)
            ep = objetivo - p
            er = self.pesos[0] * _cruz(Rc[:, 0], R[:, 0]) + self.pesos[1] * _cruz(Rc[:, 2], R[:, 2])
            resto = np.linalg.norm(ep) + np.linalg.norm(er)
            if resto < 1e-5 or anterior - resto < 1e-8:
                break
            anterior = resto
            mujoco.mj_jacSite(cin.m, cin.d, self._jp, self._jr, s)
            # Prioridad: la posición primero; el giro, en lo que deja libre (espacio nulo de la posición).
            Jp, Jr = self._jp[:, cin.dadr_pose], self._jr[:, cin.dadr_pose]
            Jp_inv = Jp.T @ np.linalg.inv(Jp @ Jp.T + 1e-6 * np.eye(3))
            dq_p = Jp_inv @ ep
            N = np.eye(5) - Jp_inv @ Jp
            JrN = Jr @ N
            dq_r = N @ (JrN.T @ np.linalg.solve(JrN @ JrN.T + 1e-3 * np.eye(3), er / max(self.pesos[0], 1e-9)
                                                - Jr @ dq_p))
            dq = dq_p + 0.5 * dq_r
            q[:5] = np.clip(q[:5] + np.clip(dq, -0.1, 0.1), cin.rangos[:5, 0], cin.rangos[:5, 1])
        p, Rc = cin.pose(q, s)
        err = np.linalg.norm(objetivo - p) / MM
        aprox = np.degrees(np.arccos(np.clip(Rc[:, 0] @ R[:, 0], -1, 1)))
        cierre = np.degrees(np.arccos(np.clip(abs(Rc[:, 2] @ R[:, 2]), -1, 1)))  # la pinza es simétrica
        return q, err, float(max(aprox, 0.5 * cierre))

    def pinza(self, objetivo: Pose, q0, *, buscar: bool = True) -> tuple[np.ndarray, float, float]:
        """Postura con `gripperframe` en `objetivo` (X = aproximación, Z = cierre). Devuelve (q, error mm, error
        de la aproximación en grados). Prueba primero desde `q0` y, si no vale, desde varias semillas."""
        mejor = self._pinza(objetivo.p, objetivo.R, q0)
        if (mejor[1] < TOL_POS_MM and mejor[2] < TOL_GRADOS) or not buscar:
            return mejor
        for semilla in self.semillas:
            q1, _, _ = self.cin.inversa_pose(objetivo.p * MM, objetivo.R[:, 0], semilla, sitio="gripperframe",
                                             eje_local=(1.0, 0.0, 0.0), iteraciones=150)
            for roll in (0.0, np.pi / 2, -np.pi / 2, np.pi, -np.pi):
                q2 = q1.copy()
                q2[4] = q1[4] + roll
                if not self.cin.rangos[4, 0] <= q2[4] <= self.cin.rangos[4, 1]:
                    continue
                r = self._pinza(objetivo.p, objetivo.R, q2)
                if r[1] + 0.5 * r[2] < mejor[1] + 0.5 * mejor[2]:
                    mejor = r
            if mejor[1] < TOL_POS_MM and mejor[2] < TOL_GRADOS:
                break
        return mejor

    def punta(self, pos_mm, eje, q0, *, buscar: bool = True) -> tuple[np.ndarray, float, float]:
        """Postura con la punta de la antorcha (sitio `punta_antorcha`) en `pos_mm` y su eje hacia `eje`."""
        q, e, a = self.cin.inversa_pose(np.asarray(pos_mm) * MM, eje, q0, iteraciones=200)
        mejor = (q, e / MM, float(np.degrees(a)))
        if (mejor[1] < TOL_POS_MM and mejor[2] < TOL_GRADOS) or not buscar:
            return mejor
        for semilla in self.semillas:
            q, e, a = self.cin.inversa_pose(np.asarray(pos_mm) * MM, eje, semilla, iteraciones=250)
            if e / MM + np.degrees(a) < mejor[1] + mejor[2]:
                mejor = (q, e / MM, float(np.degrees(a)))
            if mejor[1] < TOL_POS_MM and mejor[2] < TOL_GRADOS:
                break
        return mejor


def _cruz(a, b) -> np.ndarray:
    """Producto vectorial de 3 componentes (np.cross es lento para vectores sueltos)."""
    return np.array([a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]])


def _con_pinza(q, pinza: float) -> np.ndarray:
    q = np.array(q, dtype=float).copy()
    q[5] = pinza
    return q


def _duracion(q0, q1, minimo: float = T_MIN_TRAMO) -> float:
    return max(minimo, float(np.max(np.abs(np.asarray(q1)[:5] - np.asarray(q0)[:5]))) / VELOCIDAD_ARTICULAR * 1.6)


# --- planificador ---------------------------------------------------------------------------------------------------
# Pinza respecto a la chapa al cogerla por la aleta: aproxima hacia la cara (−Z de la chapa) y cierra a lo ancho de
# la aleta (±Y de la chapa).
def _agarre_aleta(signo: float) -> Pose:
    x = np.array([0.0, 0.0, -1.0])
    z = np.array([0.0, signo, 0.0])
    return Pose(AGARRE_ALETA.copy(), np.column_stack([x, np.cross(z, x), z]))


def _girar_x(R_pieza: np.ndarray, grados: float) -> np.ndarray:
    """Giro de la pieza alrededor de su propio eje X."""
    a = np.radians(grados)
    Rx = np.array([[1, 0, 0], [0, np.cos(a), -np.sin(a)], [0, np.sin(a), np.cos(a)]])
    return R_pieza @ Rx


class Planificador:
    """Planes del guion para cada orden, con la cinemática de la mesa."""

    def __init__(self, mesa: MesaSim, alcance: Alcance | None = None):
        self.mesa = mesa
        self.k = Cinematica6(mesa.modelo)
        self.alcance = alcance or Alcance()

    # montar / desmontar ----------------------------------------------------------------------------------------
    def _coger_chapa(self, plan: Plan, q: np.ndarray, chapa: Pose, fase_buscar="buscando") -> tuple[np.ndarray, Pose]:
        """Añade: ir encima de la aleta, bajar, cerrar y levantar. Devuelve la postura final y el agarre usado."""
        mejor = None
        for signo in (1.0, -1.0):
            agarre = _agarre_aleta(signo)
            objetivo = chapa.componer(agarre)
            r = self.k.pinza(objetivo, q)
            if mejor is None or r[1] + 0.5 * r[2] < mejor[0][1] + 0.5 * mejor[0][2]:
                mejor = (r, agarre, objetivo)
        (q_agarre, err, ang), agarre, objetivo = mejor
        if err > 15.0:
            raise NoLlego(f"no llego a la aleta de la chapa ({err:.0f} mm)")
        arriba = Pose(objetivo.p + objetivo.R[:, 0] * -60.0, objetivo.R)
        q_arriba, _, _ = self.k.pinza(arriba, q_agarre)
        q_arriba = _con_pinza(q_arriba, PINZA_ABRIR)
        plan.tramos.append(Tramo(q_arriba, _duracion(q, q_arriba, 1.2), fase_buscar))
        q_agarre = _con_pinza(q_agarre, PINZA_ABRIR)
        plan.tramos.append(Tramo(q_agarre, 0.9, "cogiendo"))
        q_cerrada = _con_pinza(q_agarre, PINZA_CHAPA)
        plan.tramos.append(Tramo(q_cerrada, 0.6, "cogiendo"))
        levantada = Pose(objetivo.p + np.array([0.0, 0.0, 70.0]), objetivo.R)
        q_lev, _, _ = self.k.pinza(levantada, q_cerrada)
        q_lev = _con_pinza(q_lev, PINZA_CHAPA)
        plan.tramos.append(Tramo(q_lev, 0.9, "girando"))
        return q_lev, agarre

    def _dejar_de_pie(self, plan: Plan, q: np.ndarray, agarre: Pose, junta) -> np.ndarray:
        final = pose_montada(junta, self.mesa.base)
        mejor = None
        for inclinacion in INCLINACIONES:
            R = _girar_x(final.R, -inclinacion)
            pose = Pose(final.p + np.array([0.0, 0.0, 3.0]), R)
            r = self.k.pinza(pose.componer(agarre), q)
            coste = r[1] + 0.5 * r[2]
            if mejor is None or coste < mejor[0]:
                mejor = (coste, r, pose)
            if r[1] < TOL_POS_MM and r[2] < TOL_GRADOS:
                break
        _, (q_dejar, err, _), pose = mejor
        if err > 20.0:
            raise NoLlego(f"no llego a la base ({err:.0f} mm)")
        encima = Pose(pose.p + np.array([0.0, 0.0, 60.0]), pose.R)
        q_encima, _, _ = self.k.pinza(encima.componer(agarre), q_dejar, buscar=False)
        q_encima = _con_pinza(q_encima, PINZA_CHAPA)
        plan.tramos.append(Tramo(q_encima, _duracion(q, q_encima, 1.6), "girando"))
        q_dejar = _con_pinza(q_dejar, PINZA_CHAPA)
        plan.tramos.append(Tramo(q_dejar, 1.0, "encajando"))
        q_abierta = _con_pinza(q_dejar, PINZA_ABRIR)
        plan.tramos.append(Tramo(q_abierta, 0.5, "encajando"))
        objetivo = pose.componer(agarre)
        atras = Pose(objetivo.p - objetivo.R[:, 0] * 50.0 + np.array([0, 0, 20.0]), objetivo.R)
        q_atras, _, _ = self.k.pinza(atras, q_abierta, buscar=False)
        q_atras = _con_pinza(q_atras, PINZA_ABRIR)
        plan.tramos.append(Tramo(q_atras, 0.8, "encajando"))
        return q_atras

    def _dejar_tumbada(self, plan: Plan, q: np.ndarray, agarre: Pose, x: float, y: float, giro: float) -> np.ndarray:
        chapa = pose_tumbada(x, y, giro)
        objetivo = chapa.componer(agarre)
        q_dejar, err, _ = self.k.pinza(Pose(objetivo.p + np.array([0, 0, 4.0]), objetivo.R), q)
        if err > 20.0:
            raise NoLlego(f"no llego a la zona libre ({err:.0f} mm)")
        encima = Pose(objetivo.p + np.array([0.0, 0.0, 70.0]), objetivo.R)
        q_encima, _, _ = self.k.pinza(encima, q_dejar, buscar=False)
        q_encima = _con_pinza(q_encima, PINZA_CHAPA)
        plan.tramos.append(Tramo(q_encima, _duracion(q, q_encima, 1.6), "girando"))
        q_dejar = _con_pinza(q_dejar, PINZA_CHAPA)
        plan.tramos.append(Tramo(q_dejar, 1.0, "encajando"))
        q_abierta = _con_pinza(q_dejar, PINZA_ABRIR)
        plan.tramos.append(Tramo(q_abierta, 0.5, "encajando"))
        q_arriba = _con_pinza(q_encima, PINZA_ABRIR)
        plan.tramos.append(Tramo(q_arriba, 0.8, "encajando"))
        return q_arriba

    def _a_reposo(self, plan: Plan, q: np.ndarray, fase: str = "volviendo") -> np.ndarray:
        q_r = self.k.reposo.copy()
        plan.tramos.append(Tramo(q_r, _duracion(q, q_r, 1.2), fase))
        return q_r

    def montar(self, junta, q: np.ndarray) -> Plan:
        plan = Plan()
        chapa = self.mesa.chapa
        if chapa.estado == "montada":
            q = self._desmontar(plan, q)
            chapa_pose = pose_tumbada(*CHAPA_POR_DEFECTO)
        elif chapa.estado in ("tumbada", "encima"):
            chapa_pose = chapa.pose
        else:
            raise NoLlego("no encuentro la chapa móvil")
        if chapa_pose.R[2, 2] < 0.5:
            raise NoLlego("la chapa está boca abajo: no veo la aleta")
        q, agarre = self._coger_chapa(plan, q, chapa_pose)
        q = self._dejar_de_pie(plan, q, agarre, junta)
        self._a_reposo(plan, q)
        return plan

    def _desmontar(self, plan: Plan, q: np.ndarray) -> np.ndarray:
        chapa = self.mesa.chapa
        mejor = None
        for signo in (1.0, -1.0):
            for inclinacion in INCLINACIONES:
                pose = Pose(chapa.pose.p, _girar_x(chapa.pose.R, -inclinacion))
                agarre = _agarre_aleta(signo)
                r = self.k.pinza(pose.componer(agarre), q)
                if mejor is None or r[1] + 0.5 * r[2] < mejor[0][1] + 0.5 * mejor[0][2]:
                    mejor = (r, agarre, pose)
                if r[1] < TOL_POS_MM and r[2] < TOL_GRADOS:
                    break
        (q_agarre, err, _), agarre, pose = mejor
        if err > 15.0:
            raise NoLlego(f"no llego a la aleta ({err:.0f} mm)")
        objetivo = pose.componer(agarre)
        atras = Pose(objetivo.p - objetivo.R[:, 0] * 50.0 + np.array([0, 0, 20.0]), objetivo.R)
        q_atras, _, _ = self.k.pinza(atras, q_agarre, buscar=False)
        plan.tramos.append(Tramo(_con_pinza(q_atras, PINZA_ABRIR), _duracion(q, q_atras, 1.2), "buscando"))
        plan.tramos.append(Tramo(_con_pinza(q_agarre, PINZA_ABRIR), 0.9, "cogiendo"))
        plan.tramos.append(Tramo(_con_pinza(q_agarre, PINZA_CHAPA), 0.6, "cogiendo"))
        arriba = Pose(objetivo.p + np.array([0, 0, 70.0]), objetivo.R)
        q_arriba, _, _ = self.k.pinza(arriba, q_agarre, buscar=False)
        q_arriba = _con_pinza(q_arriba, PINZA_CHAPA)
        plan.tramos.append(Tramo(q_arriba, 0.9, "girando"))
        # Lo que la pinza agarra de verdad: la chapa sin inclinar (la regla de agarre de la mesa la pega tal cual).
        agarre_real = chapa.pose.inversa().componer(objetivo)
        return self._dejar_tumbada(plan, q_arriba, agarre_real, *CHAPA_POR_DEFECTO)

    def desmontar(self, q: np.ndarray) -> Plan:
        if self.mesa.chapa.estado not in ("montada", "encima"):
            raise NoLlego("no hay ninguna junta montada")
        plan = Plan()
        q = self._desmontar(plan, q)
        self._a_reposo(plan, q)
        return plan

    # señalar -------------------------------------------------------------------------------------------------
    def senalar(self, q: np.ndarray) -> Plan:
        marco = self.mesa.marco_cordon()
        if marco is None:
            raise NoLlego("no hay junta montada")
        origen, R = marco
        geo = self.alcance._modelo()
        posturas = []
        semilla = q
        for x in np.linspace(0.0, c.LONGITUD_CORDON, 9):
            p = origen + R @ np.array([x, 0.0, 0.0])
            qs, _ = self.alcance._senalar_punto(p, [semilla, geo["reposo"]], iteraciones=200)
            if qs is None:
                raise NoLlego(f"no llego a señalar el cordón en x = {x:.0f} mm")
            semilla = qs
            posturas.append(_con_pinza(qs, PINZA_CHAPA))
        plan = Plan()
        plan.tramos.append(Tramo(posturas[0], _duracion(q, posturas[0], 1.4), "señalando"))
        plan.tramos.append(Tramo(posturas[0], 0.9, "señalando"))
        plan.tramos.append(Tramo(posturas[-1], 3.5, "señalando", denso=np.array(posturas[1:])))
        plan.tramos.append(Tramo(posturas[-1], 0.8, "señalando"))
        self._a_reposo(plan, posturas[-1])
        return plan

    # antorcha ------------------------------------------------------------------------------------------------
    def _coger_antorcha(self, plan: Plan, q: np.ndarray) -> np.ndarray:
        s = pose_antorcha_en_soporte()
        abajo = np.array([0.0, 0.0, -1.0])
        q_en, err, _ = self.k.punta(s.p, abajo, q)
        if err > 10.0:
            raise NoLlego("no llego a la antorcha del soporte")
        _, Rp = self.k.cin.pose(q_en, self.k.sitio_pinza)
        aprox = Rp[:, 0]
        q_atras, _, _ = self.k.punta(s.p - aprox * 50.0, abajo, q_en, buscar=False)
        plan.tramos.append(Tramo(_con_pinza(q_atras, PINZA_ABRIR), _duracion(q, q_atras, 1.2), "cogiendo"))
        plan.tramos.append(Tramo(_con_pinza(q_en, PINZA_ABRIR), 0.9, "cogiendo"))
        plan.tramos.append(Tramo(_con_pinza(q_en, PINZA_MANGO), 0.5, "cogiendo"))
        q_fuera, _, _ = self.k.punta(s.p + np.array([0, 0, 120.0]), abajo, q_en, buscar=False)
        q_fuera = _con_pinza(q_fuera, PINZA_MANGO)
        plan.tramos.append(Tramo(q_fuera, 1.0, "cogiendo"))
        return q_fuera

    def _dejar_antorcha(self, plan: Plan, q: np.ndarray) -> np.ndarray:
        s = pose_antorcha_en_soporte()
        abajo = np.array([0.0, 0.0, -1.0])
        q_en, _, _ = self.k.punta(s.p, abajo, q)
        q_fuera, _, _ = self.k.punta(s.p + np.array([0, 0, 120.0]), abajo, q_en, buscar=False)
        plan.tramos.append(Tramo(_con_pinza(q_fuera, PINZA_MANGO), _duracion(q, q_fuera, 1.2), "dejando"))
        plan.tramos.append(Tramo(_con_pinza(q_en, PINZA_MANGO), 1.1, "dejando"))
        plan.tramos.append(Tramo(_con_pinza(q_en, PINZA_ABRIR), 0.5, "dejando"))
        _, Rp = self.k.cin.pose(q_en, self.k.sitio_pinza)
        q_atras, _, _ = self.k.punta(s.p - Rp[:, 0] * 50.0, abajo, q_en, buscar=False)
        plan.tramos.append(Tramo(_con_pinza(q_atras, PINZA_ABRIR), 0.8, "dejando"))
        return _con_pinza(q_atras, PINZA_ABRIR)

    def soldar(self, q: np.ndarray, velocidad: float = VELOCIDAD_SOLDADURA) -> Plan:
        junta = self.mesa.junta_montada()
        marco = self.mesa.marco_cordon()
        if marco is None:
            raise NoLlego("no hay junta montada")
        origen, R = marco
        trabajo = c.ANGULO_TRABAJO_OBJETIVO[junta]
        d = R @ direccion_antorcha(trabajo, ANGULO_AVANCE_ROBOT)
        r = self.alcance.comprobar_marco(origen, R, trabajo)
        if not r.suelda:
            raise NoLlego("no llego a soldar la junta: gírala hacia mí")
        semilla = np.array(r.postura_inicio, dtype=float)
        plan = Plan()
        q = self._coger_antorcha(plan, q)
        puntos = [origen + R @ np.array([x, 0.0, ALTURA_PUNTA_ROBOT])
                  for x in np.arange(0.0, c.LONGITUD_CORDON + 1e-6, PASO_CORDON)]
        cadena = []
        for p in puntos:
            semilla, _, _ = self.k.punta(p, d, semilla, buscar=False)
            cadena.append(_con_pinza(semilla, PINZA_MANGO))
        q_aprox, _, _ = self.k.punta(puntos[0] - d * 40.0, d, cadena[0], buscar=False)
        q_aprox = _con_pinza(q_aprox, PINZA_MANGO)
        plan.tramos.append(Tramo(q_aprox, _duracion(q, q_aprox, 1.6), "soldando"))
        plan.tramos.append(Tramo(cadena[0], 1.0, "soldando"))
        plan.tramos.append(Tramo(cadena[0], 0.6, "soldando", led=True))
        plan.tramos.append(Tramo(cadena[-1], c.LONGITUD_CORDON / velocidad, "soldando", led=True,
                                 denso=np.array(cadena[1:])))
        plan.tramos.append(Tramo(cadena[-1], 0.4, "soldando", led=True))
        q_sale, _, _ = self.k.punta(puntos[-1] - d * 40.0, d, cadena[-1], buscar=False)
        q_sale = _con_pinza(q_sale, PINZA_MANGO)
        plan.tramos.append(Tramo(q_sale, 0.8, "soldando"))
        q = self._dejar_antorcha(plan, q_sale)
        self._a_reposo(plan, q)
        return plan

    def acercar_antorcha(self, q: np.ndarray) -> Plan:
        plan = Plan()
        q = self._coger_antorcha(plan, q)
        # La ofrece en horizontal hacia el juez (delante a la izquierda del robot), espera y la devuelve.
        q_ofrece, _, _ = self.k.punta(np.array([260.0, 120.0, 140.0]), np.array([0.0, 1.0, -0.3]), q)
        q_ofrece = _con_pinza(q_ofrece, PINZA_MANGO)
        plan.tramos.append(Tramo(q_ofrece, _duracion(q, q_ofrece, 1.5), "ofreciendo"))
        plan.tramos.append(Tramo(q_ofrece, 3.0, "ofreciendo"))
        q = self._dejar_antorcha(plan, q_ofrece)
        self._a_reposo(plan, q)
        return plan

    def planificar(self, orden: str, q: np.ndarray, **kw) -> Plan:
        q = np.asarray(q, dtype=float)
        if orden == c.orden_montar(c.TipoJunta.T):
            return self.montar(c.TipoJunta.T, q)
        if orden == c.orden_montar(c.TipoJunta.ESQUINA):
            return self.montar(c.TipoJunta.ESQUINA, q)
        if orden == "señala el cordón":
            return self.senalar(q)
        if orden == "coge la antorcha y suelda la junta":
            return self.soldar(q, **kw)
        if orden == "desmonta la junta":
            return self.desmontar(q)
        if orden == "acércame la antorcha":
            return self.acercar_antorcha(q)
        raise NoLlego(f"esa orden todavía no me la han enseñado: {orden}")


# --- ejecutores -----------------------------------------------------------------------------------------------------
class EjecutorGuion:
    """El planificador del guion, en tiempo real sobre la mesa."""

    nombre = "guion"

    def __init__(self, mesa: MesaSim, alcance: Alcance | None = None, *, escala_tiempo: float = 1.0,
                 velocidad_soldadura: float = VELOCIDAD_SOLDADURA):
        self.mesa = mesa
        self.planificador = Planificador(mesa, alcance)
        self.escala_tiempo = escala_tiempo
        self.velocidad_soldadura = velocidad_soldadura
        self._parar = False
        self.ultimo_plan: Plan | None = None

    def sabe(self, orden: str) -> bool:
        return orden in ORDENES_GUION

    def parar(self) -> None:
        self._parar = True

    async def ejecutar(self, orden: str, avisar: Avisar | None = None) -> bool:
        self._parar = False
        q0 = self.mesa.q()
        kw = {"velocidad": self.velocidad_soldadura} if "suelda" in orden else {}
        plan = await asyncio.to_thread(self.planificador.planificar, orden, q0, **kw)
        self.ultimo_plan = plan
        reloj = time.perf_counter
        inicio = reloj()
        periodo = 1.0 / HZ_CONTROL
        while not self._parar:
            t = (reloj() - inicio) * self.escala_tiempo
            q, tramo, progreso = postura_en(plan, q0, t)
            self.mesa.mandar(q)
            self.mesa.poner_led(bool(tramo and tramo.led))
            if avisar is not None:
                avisar(tramo.fase if tramo else "volviendo", progreso)
            if tramo is None:
                break
            await asyncio.sleep(periodo)
        self.mesa.poner_led(False)
        if not self._parar:
            await asyncio.sleep(0.4)  # que el brazo llegue y se asiente
        return not self._parar


class EjecutorAprendido:
    """Una política de `robot.politica` (replay, ACT o SmolVLA) con la orden como tarea, a 30 Hz sobre la mesa."""

    def __init__(self, politica, nombre: str, mesa: MesaSim, *, max_segundos: float = 90.0):
        self.politica, self.nombre, self.mesa = politica, nombre, mesa
        self.max_segundos = max_segundos
        self._parar = False
        self._renderer = None

    def sabe(self, orden: str) -> bool:
        if hasattr(self.politica, "episodios_de"):
            return bool(self.politica.episodios_de(orden))
        return True

    def parar(self) -> None:
        self._parar = True

    def _observacion(self) -> dict:
        from sim.entorno import RESOLUCION, rad_a_lerobot

        obs = {"observation.state": rad_a_lerobot(self.mesa.q()).astype(np.float32)}
        if getattr(self.politica, "necesita_imagenes", False):
            if self._renderer is None:
                self._renderer = mujoco.Renderer(self.mesa.modelo, RESOLUCION[1], RESOLUCION[0])
            with self.mesa._cerrojo:
                for cam in c.CAMARAS_POLITICA:
                    self._renderer.update_scene(self.mesa.datos, cam)
                    obs[f"observation.images.{cam}"] = self._renderer.render().copy()
        return obs

    async def ejecutar(self, orden: str, avisar: Avisar | None = None) -> bool:
        from sim.entorno import lerobot_a_rad

        self._parar = False
        self.politica.reiniciar(None, None, orden)  # PoliticaNoDisponible si no sabe esta orden
        periodo = 1.0 / c.FPS_DATASET
        n = int(self.max_segundos * c.FPS_DATASET)
        esperados = len(getattr(self.politica, "_acciones", ())) or n
        for i in range(n):
            if self._parar or self.politica.terminada:
                break
            obs = await asyncio.to_thread(self._observacion)
            accion = await asyncio.to_thread(self.politica.accion, obs)
            self.mesa.mandar(lerobot_a_rad(np.asarray(accion, dtype=float)))
            if avisar is not None:
                avisar("trabajando", min(1.0, (i + 1) / esperados))
            await asyncio.sleep(periodo)
        return not self._parar


class EjecutorRespaldo:
    """Por orden de preferencia: los aprendidos que sepan hacer la orden y, si no o si fallan, el guion."""

    def __init__(self, guion: EjecutorGuion, aprendidos: list | None = None):
        self.guion = guion
        self.aprendidos = list(aprendidos or [])
        self.activo = guion.nombre
        self.aviso: str | None = None
        self._actual = None

    def parar(self) -> None:
        for e in (self.guion, *self.aprendidos):
            e.parar()

    async def ejecutar(self, orden: str, avisar: Avisar | None = None) -> bool:
        motivos = []
        for e in self.aprendidos:
            try:
                if not e.sabe(orden):
                    motivos.append(f"{e.nombre}: no sabe «{orden}»")
                    continue
                self.activo, self._actual = e.nombre, e
                self.aviso = "; ".join(motivos) or None
                return await e.ejecutar(orden, avisar)
            except Exception as ex:  # noqa: BLE001 - cualquier fallo de la política: respaldo
                log.warning("la política %s no ha podido con «%s»: %s", e.nombre, orden, ex)
                motivos.append(f"{e.nombre}: {ex}")
        self.activo, self._actual = self.guion.nombre, self.guion
        self.aviso = "; ".join(motivos) or None
        return await self.guion.ejecutar(orden, avisar)


def crear_ejecutor(mesa: MesaSim, alcance: Alcance | None = None, *, checkpoint_vla=None, checkpoint_act=None,
                   dataset=None, dispositivo: str = "cpu", escala_tiempo: float = 1.0,
                   velocidad_soldadura: float = VELOCIDAD_SOLDADURA) -> EjecutorRespaldo:
    """Política entrenada (si hay checkpoint) → replay del dataset (si lo hay) → guion."""
    aprendidos = []
    for nombre, kw in (("vla", {"checkpoint": checkpoint_vla}), ("act", {"checkpoint": checkpoint_act}),
                       ("replay", {"dataset": dataset})):
        if not any(kw.values()):
            continue
        try:
            from robot.politica import cargar_politica

            aprendidos.append(EjecutorAprendido(cargar_politica(nombre, dispositivo=dispositivo, **kw), nombre, mesa))
            log.info("política %s cargada para el simulador", nombre)
        except Exception as e:  # noqa: BLE001
            log.warning("sin %s: %s", nombre, e)
    guion = EjecutorGuion(mesa, alcance, escala_tiempo=escala_tiempo, velocidad_soldadura=velocidad_soldadura)
    return EjecutorRespaldo(guion, aprendidos)
