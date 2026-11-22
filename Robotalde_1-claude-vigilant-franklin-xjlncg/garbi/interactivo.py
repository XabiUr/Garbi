"""Comportamiento interactivo de Garbi con el montaje lateral (petición del usuario, 20-11): un compañero que reacciona
al taladro en cada fotograma, no una secuencia cerrada.

- Entra el taladro en escena → sale del aparcado y lo **sigue** a una distancia de espera (`DIST_ESPERA` en planta y
  `ALTURA_ESPERA` sobre la madera), sin estorbar.
- Apoyas la broca en la madera y la dejas quieta un momento → **se acerca** a `DISTANCIA_BROCA` y enciende la
  aspiradora.
- Levantas la broca o la mueves → vuelve a la distancia de espera y te sigue.
- Cada vez que la broca ha estado apoyada `T_AGUJERO` s se apunta un agujero, en el marco de la madera (si mueves la
  madera, el agujero va con ella).
- Sale el taladro de escena → espera `T_ESPERA` s aspirando y **limpia todos los agujeros** con la boca más picada
  (ya no hay taladro con el que chocar); después aparca.

Cada fotograma: postura objetivo con la cinemática del montaje lateral arrancando desde la anterior (rápido), y la
orden al robot avanza hacia ella con la velocidad de cada articulación limitada.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from enum import Enum

import numpy as np

import garbi.lateral as L
from garbi import contrato as g

DIST_ESPERA, ALTURA_ESPERA = 80.0, 45.0  # mm: dónde espera mientras sigue al taladro
INCLINACIONES_ESPERA = (15.0, 25.0, 35.0)  # siguiendo puede ir algo más picada (cerca del robot no llega a 15°)
INCLINACION_TRABAJO = 15.0  # grados: seguir y acompañar, casi horizontal
INCLINACIONES_LIMPIEZA = (60.0, 45.0, 35.0)  # con el taladro fuera, limpia más picado
# Percepción con ruido (la cámara de arriba tiembla ±3 mm, a 10 Hz y con retraso): la punta se filtra con una
# mediana, los umbrales están por encima del ruido y hay histéresis para no ir y venir.
FILTRO = 9  # fotogramas de la mediana de la punta (0,3 s)
APOYADA_MM = 6.0  # la punta está a menos de esto de la cara de la madera
QUIETA_MM, T_QUIETA = 6.0, 0.5  # para considerar la broca apoyada y quieta
LEVANTADA_MM, MOVIDA_MM = 15.0, 12.0  # para dejar de acompañar: levantarla o moverla más de esto
# Seguridad en cada fotograma: no avanza si se acercaría al taladro (o la mano) a menos de MARGEN_MM, ni si el borde de
# la boca bajaría de la superficie
MARGEN_MM = 10.0
T_AGUJERO = 1.0  # s apoyada para apuntar un agujero
T_ESPERA = 1.5  # s aspirando tras salir el taladro
MAX_GRADOS_FOTOGRAMA = 2.5  # velocidad máxima de cada articulación (75 °/s)
BUSQUEDA_TRAS = 15  # fotogramas sin solución en caliente antes de la búsqueda completa (lenta)


class Estado(str, Enum):
    APARCADO = "aparcado"
    SEGUIR = "seguir"
    ACOMPANAR = "acompañar"
    ESPERAR = "esperar"
    LIMPIAR = "limpiar"
    APARCAR = "aparcar"


@dataclass
class VistaTaladro:
    visible: bool
    punta: np.ndarray | None = None  # mm, marco de la mesa (z de la punta de la broca)


@dataclass
class Seguidor:
    control: L.ControlLateral
    estado: Estado = Estado.APARCADO
    agujeros: list = field(default_factory=list)  # en el marco de la madera
    aspiradora: bool = False
    texto: str = "aparcado"

    def __post_init__(self):
        self.q = L.APARCADO.copy()  # orden actual (unidades de LeRobot)
        self._q4 = None  # postura objetivo (rad) de la que arranca la cinemática en el fotograma siguiente
        self._fallos = 0
        self._inc = INCLINACION_TRABAJO
        self._historial = deque(maxlen=int(T_QUIETA * g.FPS) + 1)
        self._filtro = deque(maxlen=FILTRO)
        self._ancla = None  # punta donde está apoyada la broca mientras acompaña
        self._fase = "bajar"  # acercamiento: primero baja a la altura de trabajo, después entra en horizontal
        self._P = None  # punta (filtrada) para la guardia de seguridad
        self.frenadas = 0  # fotogramas en que la guardia no le dejó avanzar
        self._apoyada_desde = None
        self._agujero_apuntado = False
        self._fuera_desde = None
        self._plan: deque = deque()

    # --- cinemática rápida ---------------------------------------------------------------------------------
    def _objetivo(self, P, distancia, altura, inclinaciones):
        """Postura (rad) con la boca a `distancia` en planta de P y `altura` sobre P, arrancando de la anterior. Usa la
        inclinación de la última postura buena; si no hay solución, busca entre `inclinaciones`."""
        c = self.control
        inclinaciones = tuple(np.atleast_1d(inclinaciones).astype(float))
        inclinacion = self._inc if self._inc in inclinaciones else inclinaciones[0]
        residuo = c._junto_a(P, distancia, altura)(inclinacion)
        if self._q4 is not None:
            q, err = c._resolver(residuo, self._q4, iteraciones=30)
            if err < 3.0:
                self._fallos = 0
                return q
            self._fallos += 1
            if self._fallos < BUSQUEDA_TRAS:  # sin solución en caliente: mantiene el objetivo anterior un momento
                return self._q4
        self._fallos = 0
        anterior = L.INCLINACIONES
        L.INCLINACIONES = inclinaciones
        try:
            r = c._postura(c._junto_a(P, distancia, altura))
        finally:
            L.INCLINACIONES = anterior
        if r is None:
            return None
        self._inc = r[1]
        return r[0]

    def _seguro(self, q_lr) -> bool:
        """¿Puede ir a `q_lr`? No si el borde de la boca baja de la superficie o se acerca al taladro (o la mano) a
        menos de MARGEN_MM (salvo que se esté alejando)."""
        from sim.entorno import lerobot_a_rad

        c = self.control
        q4 = lerobot_a_rad(np.asarray(q_lr, float))[:4]
        b, e = c.boca(q4)
        borde = b[2] - L.ALTURA_BOCA * 0 - 15.0 * np.sqrt(max(0.0, 1 - e[2] ** 2))
        if borde < g.ALFOMBRILLA_GROSOR:
            return False
        if self._P is None:
            return True
        h = c.holgura(q4, self._P)
        if h >= MARGEN_MM:
            return True
        return h >= c.holgura(lerobot_a_rad(self.q)[:4], self._P)  # se está alejando

    def _ir(self, q4) -> None:
        if q4 is None:
            return
        self._q4 = q4
        destino = self.control.a_lerobot(q4)
        candidato = self.q + np.clip(destino - self.q, -MAX_GRADOS_FOTOGRAMA, MAX_GRADOS_FOTOGRAMA)
        if self._seguro(candidato):
            self.q = candidato
        else:
            self.frenadas += 1

    def _hacia(self, destino) -> bool:
        """Avanza hacia una postura (LeRobot) con velocidad limitada; True al llegar."""
        self.q = self.q + np.clip(destino - self.q, -MAX_GRADOS_FOTOGRAMA, MAX_GRADOS_FOTOGRAMA)
        return bool(np.max(np.abs(destino - self.q)) < 0.5)

    # --- un fotograma ---------------------------------------------------------------------------------------
    def paso(self, t: float, vista: VistaTaladro, tabla: g.PoseTabla | None) -> np.ndarray:
        if vista.visible and self._en_zona(vista.punta):
            self._fuera_desde = None
            self._con_taladro(t, vista, tabla)
        else:
            self._sin_taladro(t, tabla)
        return self.q

    def _en_zona(self, P) -> bool:
        r = float(np.hypot(P[0], P[1]))
        return L.RADIO_TALADRO_MIN - 30 <= r <= L.RADIO_TALADRO_MAX + 20

    def _con_taladro(self, t, vista, tabla):
        self._filtro.append(np.asarray(vista.punta, float))
        P = np.median(np.array(self._filtro), axis=0)
        self._P = np.array([P[0], P[1], min(P[2], g.ALTURA_CARA_TABLA + 80.0)])
        superficie = np.array([P[0], P[1], g.ALTURA_CARA_TABLA])
        self._historial.append(P.copy())
        quieta = len(self._historial) == self._historial.maxlen and \
            np.max(np.linalg.norm(np.array(self._historial)[:, :2] - P[:2], axis=1)) < QUIETA_MM
        apoyada = P[2] - g.ALTURA_CARA_TABLA < APOYADA_MM
        if self.estado == Estado.ACOMPANAR and self._ancla is not None:
            # histéresis: sigue acompañando salvo que la broca se levante o se mueva claramente
            if P[2] - g.ALTURA_CARA_TABLA < LEVANTADA_MM and np.linalg.norm(P[:2] - self._ancla[:2]) < MOVIDA_MM:
                apoyada = quieta = True
        if apoyada and quieta:
            if self.estado != Estado.ACOMPANAR:
                self._ancla, self._fase = superficie.copy(), "bajar"
            if self._apoyada_desde is None:
                self._apoyada_desde = t
            if not self._agujero_apuntado and t - self._apoyada_desde >= T_AGUJERO and tabla is not None:
                self.agujeros.append(tabla.a_tabla(self._ancla[:2]))
                self._agujero_apuntado = True
            self.estado, self.aspiradora = Estado.ACOMPANAR, True
            if self._fase == "bajar":
                self.texto = "broca apoyada: bajo a la altura de trabajo"
                q4 = self._objetivo(self._ancla, DIST_ESPERA, L.ALTURA_BOCA, (INCLINACION_TRABAJO, 20.0, 25.0))
                self._ir(q4)
                if q4 is not None and np.max(np.abs(self.control.a_lerobot(q4) - self.q)) < 1.0:
                    self._fase = "entrar"
            else:
                self.texto = "broca apoyada: me acerco y aspiro"
                self._ir(self._objetivo(self._ancla, L.DISTANCIA_BROCA, L.ALTURA_BOCA, (INCLINACION_TRABAJO, 20.0, 25.0)))
        else:
            self._ancla = None
            if not apoyada:
                self._apoyada_desde, self._agujero_apuntado = None, False
            self.estado = Estado.SEGUIR
            self.aspiradora = self.aspiradora and apoyada  # se apaga al levantar la broca
            self.texto = "sigo al taladro a distancia"
            self._ir(self._objetivo(superficie, DIST_ESPERA, ALTURA_ESPERA, INCLINACIONES_ESPERA))

    def _sin_taladro(self, t, tabla):
        self._P = None
        self._filtro.clear()
        self._historial.clear()
        if self.estado in (Estado.SEGUIR, Estado.ACOMPANAR):
            self._fuera_desde = t
            self.estado = Estado.ESPERAR
            self.aspiradora = self.aspiradora or bool(self.agujeros)
            self.texto = "el taladro se ha ido: aspiro un momento"
        if self.estado == Estado.ESPERAR and t - self._fuera_desde >= T_ESPERA:
            self._planear_limpieza(tabla)
        if self.estado == Estado.LIMPIAR:
            if self._plan:
                destino, texto = self._plan[0]
                self.texto = texto
                if self._hacia(destino):
                    self._plan.popleft()
            else:
                self.estado, self.aspiradora, self.texto = Estado.APARCAR, False, "limpio: aparco"
        if self.estado == Estado.APARCAR:
            if self._hacia(L.APARCADO):
                self.estado, self.texto, self._q4 = Estado.APARCADO, "aparcado", None

    def _planear_limpieza(self, tabla):
        c = self.control
        self._plan = deque()
        anterior = L.INCLINACIONES
        L.INCLINACIONES = INCLINACIONES_LIMPIEZA
        try:
            for i, h in enumerate(self.agujeros):
                centro = tabla.a_mesa(np.asarray(h, float)) if tabla is not None else np.asarray(h, float)
                for _, (q4, inc) in c.barrido(centro, radio=22.0, paso=11.0):
                    self._plan.append((c.a_lerobot(q4), f"limpio el agujero {i + 1} de {len(self.agujeros)} ({inc:.0f}°)"))
        finally:
            L.INCLINACIONES = anterior
        self.agujeros = []
        self.estado = Estado.LIMPIAR if self._plan else Estado.APARCAR
        self.aspiradora = bool(self._plan)
