"""Paso 7 «tipo teleoperación» en la simulación: perseguir la viruta que queda (especificación técnica, M5).

En el hackathon las demostraciones teleoperadas se graban con el brazo guía persiguiendo la viruta que queda. En la
simulación no hay persona, así que `HabilidadPersecucion` hace de teleoperador: mira la cámara de arriba (la misma
imagen que verá ACT), busca los píxeles color serrín sobre la madera cerca del agujero y lleva el punto al que apunta
la boca hacia el montón más cercano. Cuando no ve viruta (o la tapa el brazo) gira despacio alrededor del agujero.

    hab = HabilidadPersecucion(control, camara=calibrar_camara_arriba(img_top))
    hab.reiniciar(agujero_mesa)
    q = hab.accion({"top": img_top, "wrist": img_wrist, "state": q_actual})

Geometría y guardias como `HabilidadEspiral` (de la que hereda la partida, la inclinación y el alcance): la boca a
`ALTURA_PARTIDA` sobre la madera, con la inclinación de la partida; cada postura sale de la anterior por cinemática
inversa en caliente; velocidad de articulación limitada a `VELOCIDAD_MAX`; muñeca fija y pinza cerrada.
"""
from __future__ import annotations

import cv2
import numpy as np

from garbi.habilidad import (ALTURA_PARTIDA, PASOS_MEZCLA, RADIO_ZONA, TOLERANCIA_IK, VELOCIDAD_MAX,
                             HabilidadEspiral, _punto3)
from garbi.tipos import HZ_CONTROL, forzar_montaje

VELOCIDAD_PUNTO = 75.0  # mm/s del punto apuntado (como una persona con el brazo guía, sin prisa)
CADA_PASOS = 3  # se mira la cámara de arriba cada tantos pasos (10 Hz)
RADIO_BUSQUEDA = RADIO_ZONA + 8.0  # mm alrededor del agujero en los que se busca viruta
RADIO_MONTON = 12.0  # mm: la viruta a menos de esto de la más cercana forma su montón (se apunta a su centro)
RADIO_GIRO = 16.0  # mm: sin viruta a la vista, gira a este radio alrededor del agujero
VUELTAS_GIRO_S = 0.5  # vueltas por segundo del giro de espera
CERCA_BOCA = 6.0  # mm: la viruta más cerca que esto del punto apuntado ya se está aspirando: se ignora
# Serrín sobre el vinilo negro (como `garbi.percepcion.SERRIN_BAJO/ALTO`)
SERRIN_BAJO, SERRIN_ALTO = (8, 35, 110), (35, 175, 255)


def viruta_vista(img_top, camara, centro_xy, radio: float = RADIO_BUSQUEDA, z: float | None = None) -> np.ndarray:
    """Puntos (x, y) mm de la mesa de los píxeles color serrín de la cámara de arriba a menos de `radio` del centro,
    proyectados al plano de la cara de la madera. `camara` es una `garbi.percepcion.CamaraMesa` calibrada para la
    resolución de `img_top` (si la imagen es de otro tamaño, se escala la K)."""
    from garbi import contrato as g

    z = g.ALTURA_CARA_TABLA if z is None else z
    hsv = cv2.cvtColor(np.ascontiguousarray(img_top), cv2.COLOR_RGB2HSV)
    mascara = cv2.inRange(hsv, SERRIN_BAJO, SERRIN_ALTO)
    # solo una ventana alrededor del agujero (más rápido y sin el resto del tapete)
    K = camara.K
    ancho_k = 2 * K[0, 2]
    escala = img_top.shape[1] / ancho_k
    uv0 = camara.proyectar(np.array([[centro_xy[0], centro_xy[1], z]]))[0] * escala
    r_px = int(radio / 1.0 * escala) + 4  # ~1 mm/px a 640 × 480 desde arriba: cota holgada
    u0, v0 = int(uv0[0]), int(uv0[1])
    alto, ancho = mascara.shape
    ventana = mascara[max(0, v0 - r_px):min(alto, v0 + r_px), max(0, u0 - r_px):min(ancho, u0 + r_px)]
    vs, us = np.nonzero(ventana)
    if len(us) == 0:
        return np.zeros((0, 2))
    uv = np.column_stack([us + max(0, u0 - r_px), vs + max(0, v0 - r_px)]).astype(float) / escala
    xy = camara.a_plano(uv, z)
    d = np.linalg.norm(xy - np.asarray(centro_xy, float)[None, :2], axis=1)
    return xy[d <= radio]


class HabilidadPersecucion(HabilidadEspiral):
    """Persigue la viruta que queda alrededor del agujero mirando la cámara de arriba (sustituto en la simulación de
    las demostraciones teleoperadas). Sin `camara` (o sin imagen de arriba) gira alrededor del agujero."""

    nombre = "persecucion"

    def __init__(self, control, camara=None, velocidad: float = VELOCIDAD_PUNTO, **kw):
        super().__init__(control, **kw)
        self.camara = camara
        self.velocidad = velocidad
        self.objetivo: np.ndarray | None = None  # punto (x, y) hacia el que va el punto apuntado
        self.punto: np.ndarray | None = None  # punto apuntado actual (x, y)
        self.vistas: list[int] = []  # píxeles de viruta vistos en cada mirada (para el registro)
        self._q4: np.ndarray | None = None
        self._centro: np.ndarray | None = None
        self._ang = 0.0

    def reiniciar(self, agujero_mesa) -> None:
        super().reiniciar(agujero_mesa)  # partida, inclinación, alcance y la espiral (respaldo si la IK no sigue)
        p = _punto3(agujero_mesa)
        self._centro = p
        self.punto = np.asarray(self.apuntado[0], float).copy()
        self._ang = float(np.arctan2(self.punto[1] - p[1], self.punto[0] - p[0]))
        self.objetivo = None
        self.vistas = []
        self._q4 = None

    def _mirar(self, img_top) -> None:
        if self.camara is None or img_top is None:
            self.objetivo = None
            return
        pts = viruta_vista(img_top, self.camara, self._centro[:2])
        self.vistas.append(len(pts))
        if len(pts):
            d = np.linalg.norm(pts - self.punto[None, :], axis=1)
            lejos = d > CERCA_BOCA
            if np.any(lejos):
                pts, d = pts[lejos], d[lejos]
                cercana = pts[np.argmin(d)]
                monton = pts[np.linalg.norm(pts - cercana[None, :], axis=1) <= RADIO_MONTON]
                self.objetivo = monton.mean(axis=0)
                return
        self.objetivo = None

    def _siguiente_punto(self) -> np.ndarray:
        paso = self.velocidad / HZ_CONTROL
        c = self._centro[:2]
        if self.objetivo is None:  # gira alrededor del agujero a RADIO_GIRO
            self._ang += 2 * np.pi * VUELTAS_GIRO_S / HZ_CONTROL
            meta = c + RADIO_GIRO * np.array([np.cos(self._ang), np.sin(self._ang)])
        else:
            meta = self.objetivo
            self._ang = float(np.arctan2(self.punto[1] - c[1], self.punto[0] - c[0]))
        v = meta - self.punto
        n = float(np.linalg.norm(v))
        nuevo = meta if n <= paso else self.punto + v * (paso / n)
        r = float(np.linalg.norm(nuevo))
        if r > self.alcance:  # como la espiral: el lado lejano sigue el borde del alcance
            nuevo = nuevo * (self.alcance / r)
        return nuevo

    def accion(self, obs: dict) -> np.ndarray:
        estado = obs.get("state") if isinstance(obs, dict) else None
        if self._q_inicio is None:
            self._q_inicio = self.plan[0] if estado is None else np.asarray(estado, float).copy()
            from garbi.ciclo import _lr_a_q4

            self._q4 = _lr_a_q4(self.plan[0])
        k = self._i
        self._i += 1
        if k % CADA_PASOS == 0:
            self._mirar(obs.get("top") if isinstance(obs, dict) else None)
        if k >= PASOS_MEZCLA:  # durante la mezcla inicial se va a la primera postura de la espiral
            nuevo = self._siguiente_punto()
            q = self._seguir_desde(np.array([nuevo[0], nuevo[1], self._centro[2]]))
            if q is not None:
                self._q4, self.punto = q, nuevo
        q = forzar_montaje(self.control.a_lerobot(self._q4))
        if k < PASOS_MEZCLA:
            w = 0.5 - 0.5 * np.cos(np.pi * (k + 1) / PASOS_MEZCLA)
            q = self._q_inicio + (q - self._q_inicio) * w
        previa = self._q_inicio if self._previa is None else self._previa
        q = previa + np.clip(q - previa, -VELOCIDAD_MAX / HZ_CONTROL, VELOCIDAD_MAX / HZ_CONTROL)
        self._previa = forzar_montaje(q)
        return self._previa.copy()

    def _seguir_desde(self, objetivo):
        """Postura (4 rad) que apunta a `objetivo` desde la actual sin saltar de rama, o None."""
        c = self.control
        delante = ALTURA_PARTIDA / np.tan(np.radians(self.inclinacion))
        residuo = c._junto_a(objetivo, delante, self.altura)(self.inclinacion)
        q, err = c._resolver(residuo, self._q4, iteraciones=40)
        if err >= TOLERANCIA_IK or np.degrees(np.max(np.abs(q - self._q4))) > 8.0:
            return None
        return q
