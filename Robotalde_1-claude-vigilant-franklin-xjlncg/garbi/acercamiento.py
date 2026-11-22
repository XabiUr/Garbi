"""Acercamiento a la broca clavada (solución final, 20-11): de la posición prudente a la de aspirar.

    detector = DetectorClavada()                    # la percepción decide clavada / levantada (no ACT)
    evento = detector.actualizar(escena)            # "clavada", "levantada" o None
    habilidad = HabilidadAcercamientoProgramado(control)   # respaldo y generador de demostraciones
    habilidad = HabilidadACT(modelo, tarea=TAREA_ACERCAMIENTO)   # o la política ACT entrenada
    habilidad.reiniciar(punta_mesa)
    q = habilidad.accion({"top": ..., "wrist": ..., "state": orden_anterior, "broca": punta, "caida": mm})

Posturas (mm y grados, marco de la mesa):

| Postura | Qué es | Holgura con el taladro |
|---|---|---|
| **Prudente** (`postura_prudente`) | La cámara de la muñeca mira la punta de la broca **sobre la madera** desde `MIRAR_PRUDENTE` (180 mm), en el píxel `MIRAR_UV` (150, 120) (fuera de las mordazas) y 10° hacia abajo. La boca queda ~92 mm sobre la madera y ~140 mm a un lado de la broca | 69 mm (35 mm con el taladro inclinado 8° hacia cualquier lado, sin eje medido) |
| Entrada (fase 0) | La boca mirando el eje a `ALTURA_PRUDENTE` (45) sobre la madera: con el eje de la broca medido (`obs["eje_conocido"]`), a `DIST_BAJAR` (60) y 15° (20, 25); sin él, a `DISTANCIA_PRUDENTE` (100) y 25° (35, 15, 45) | En la recta desde la prudente: ≥ 28 mm con el eje medido; ≥ 52 mm a 100 (17 mm con el taladro quizá inclinado 8°) |
| Bajar (fase 1) | Distancia `DIST_BAJAR` (60), centro de la boca a `ALTURA_TRABAJO` (26) + caída del brazo, 15° (20, 25) | |
| Aspirar (fase 2) | Distancia `DIST_BROCA` (30), `ALTURA_TRABAJO` (26) + caída, 15° (20, 25) | |

Por qué la prudente mira la broca (F4): desde la postura de antes (la de entrada) la cámara de la muñeca queda a
250-270 mm del eje (más de `DISTANCIA_MUNECA_MAX`) y la punta apoyada, tapada por las mordazas: la clavada solo se
veía yendo a mirar, y una re-clavada se perdía. Desde la prudente la muñeca ve la punta en la madera, a 8 mm y a
50 mm (1-2 mm de error, 170-185 mm de distancia en los 10 sitios de prueba de la zona de taladro): la clavada y la
levantada se ven siempre y a tiempo, sin moverse. Es también la **postura de partida de ACT** (al grabar y al
ejecutar).

El acercamiento programado: desde la prudente la boca no mira hacia la broca (está a un lado), así que primero va a
la de entrada en línea recta en articulaciones (fase 0; la recta directa a bajar pasaba a 2 mm del taladro inclinado)
y después mueve un objetivo virtual (distancia, altura, inclinación) a velocidad limitada: primero se coloca en
planta, después baja y por último entra en horizontal (las dos fases de M4). Si la broca se mueve, el objetivo va con
ella. El ciclo pone por encima las guardias (velocidad, borde, holgura con el taladro y con las manos).

Las entradas que no son de ACT (`broca`, `caida`) las ignora `HabilidadACT` (solo mira `top`, `wrist` y `state`).
"""
from __future__ import annotations

import numpy as np

from garbi import contrato as g
from garbi.habilidad import TOLERANCIA_IK
from garbi.ciclo import (ALTURA_PASO, DIST_BROCA, MIRAR_BAJADA, MIRAR_UV, PREAPUNTO_ATRAS, TOLERANCIA_ZONA,
                         TRABAJO_INC, Cinematica, _lr_a_q4)
from garbi.tipos import DISTANCIA_PRUDENTE, HZ_CONTROL, Escena, en_zona_taladro, forzar_montaje

# Postura prudente: la cámara de la muñeca mira la punta sobre la madera desde aquí (mm). A 150 mm la holgura con el
# taladro inclinado sin eje medido bajaba a 14-17 mm y a 120 mm a 3-6 mm; a 220 mm la muñeca mide peor (> 200 mm).
MIRAR_PRUDENTE = 180.0
# Píxel donde se ve la punta: el primero; si la postura pasa junto a una mano apoyada (el brazo queda 140-175 mm a un
# lado de la broca, y la mano libre suele estar apoyada en la madera hacia la persona), las otras. Las tres ven la punta
# apoyada, a 8 y a 50 mm (1-3 mm, 160-195 mm) en los sitios de prueba; holgura con el taladro 69, 99 y 57 mm.
UV_PRUDENTE = ((150.0, 120.0), (150.0, 60.0), (60.0, 120.0))
# Postura de entrada (la «prudente» de antes): boca a DISTANCIA_PRUDENTE en planta mirando la broca
ALTURA_PRUDENTE = 45.0  # mm del centro de la boca sobre la madera
INC_PRUDENTE = (25.0, 35.0, 15.0, 45.0)  # cerca del robot (broca a < 340 mm) a 25° no llega
LATERAL_MAX = 30.0  # mm: con la boca más a un lado de la broca, el acercamiento pasa antes por la de entrada
VELOCIDAD_ENTRADA = 60.0  # °/s por articulación de la prudente a la de entrada (lejos de la madera; el robot admite 75)
MOVIDA_ENTRADA = 3.0  # mm que se mueve la broca para volver a calcular la postura de entrada
DIST_BAJAR = DIST_BROCA + PREAPUNTO_ATRAS  # 60 mm: baja a la altura de trabajo sin acercarse más
# Clavada / levantada (con histéresis, como la percepción)
T_CLAVADA = 0.3  # s apoyada y en la madera para darla por clavada
T_LEVANTADA = 0.2  # s sin apoyar para darla por levantada
LEVANTADA_MM = 8.0  # punta a más de esto sobre la madera: levantada al momento
# Centro de la boca sobre la madera al aspirar: con 15° el borde queda a ~11 mm. Con los 22 mm de ACOMPANAR (ciclo
# viejo) el brazo simulado, al llegar desde la posición prudente, bajaba hasta 0,7 mm bajo la orden en la bajada.
ALTURA_TRABAJO = 26.0
VELOCIDAD_RAMPA = np.array([40.0, 30.0, 30.0]) / HZ_CONTROL  # por paso: mm (planta), mm (altura), grados
VELOCIDAD_MAX = 45.0  # °/s por articulación de la orden del acercamiento programado (el robot admite 75)
GANANCIA = 0.2  # fracción de lo que falta que avanza el objetivo en cada paso (con el tope de VELOCIDAD_RAMPA)
MOVIDA_ANCLA = 8.0  # mm: si la punta clavada se desliza más que esto, el agujero empieza a contar de nuevo
T_DESLIZA, SIGUE_DESLIZA = 0.4, 5.0  # s tras un deslizamiento en los que el ancla sigue a la punta si se mueve > mm


def postura_prudente(control, punta, q0=None, uv=MIRAR_UV) -> np.ndarray | None:
    """Postura prudente (grados de LeRobot): la cámara de la muñeca mira la punta de la broca **sobre la madera** (x, y
    de `punta`, z de la cara) desde MIRAR_PRUDENTE mm, en el píxel `uv` (`UV_PRUDENTE`: la primera, salvo que una mano
    apoyada estorbe). `q0`: postura de LeRobot desde la que seguir en caliente. None si no hay. La usan el ciclo final
    (PRUDENTE), el grabador simulado y la teleoperación (postura de partida de ACT)."""
    from garbi.percepcion import postura_mirar_broca

    p = np.asarray(punta, float).ravel()
    q4 = None if q0 is None else _lr_a_q4(q0)
    q = postura_mirar_broca(control, np.array([p[0], p[1], g.ALTURA_CARA_TABLA]), distancia=MIRAR_PRUDENTE,
                            uv=uv, bajada=MIRAR_BAJADA, q0=q4)
    return None if q is None else forzar_montaje(q)


def diferencia_a_prudente(control, escena: Escena, q_lr) -> float | None:
    """Grados (máx. de las 4 articulaciones) de la postura `q_lr` a la prudente de la broca de `escena`; None si no se
    ve la broca o no hay postura prudente. Para comprobar la postura de partida de los episodios de ACT."""
    P = punta_de(escena) if escena is not None and escena.taladro.visible else None
    # en caliente desde q_lr: la postura prudente más cercana (hay varias ramas que miran la broca igual; el ciclo la
    # sigue en caliente y, resuelta desde cero, salía otra a 18-19° de la que tenía el brazo)
    if P is None or q_lr is None:
        return None
    difs = [float(np.max(np.abs(np.asarray(q_lr, float)[:4] - q[:4]))) for q in
            (postura_prudente(control, P, q_lr, uv) for uv in UV_PRUDENTE) if q is not None]
    return min(difs) if difs else None


def lateral_de_boca(control, q_lr, P) -> float:
    """mm de la boca a un lado de la recta por la que mira (en planta) respecto al eje de la broca en P."""
    b, e = control.boca(_lr_a_q4(q_lr))
    n = np.hypot(e[0], e[1])
    if n < 1e-6:
        return np.inf
    d = np.asarray(P, float)[:2] - b[:2]
    return float(abs(d[0] * e[1] / n - d[1] * e[0] / n))


def punta_de(escena: Escena) -> np.ndarray | None:
    """Punta de la broca (mm, mesa): la medida o, si no, bajo el marcador del taladro, en la cara de la madera."""
    if escena.broca.punta is not None:
        return np.asarray(escena.broca.punta, float)
    if escena.taladro.xy is not None:
        return np.array([*np.asarray(escena.taladro.xy, float)[:2], g.ALTURA_CARA_TABLA])
    return None


class DetectorClavada:
    """Broca clavada (apoyada en la madera, con el taladro agarrado y, con `zona`, en la zona de taladro) durante
    `T_CLAVADA` s → «clavada»; sin apoyar `T_LEVANTADA` s, o la punta a más de `LEVANTADA_MM` → «levantada».
    `ancla`: punta donde está clavada; `ancla_desde`: t desde el que está clavada ahí (se reinicia si se desliza más
    de `MOVIDA_ANCLA`). Lo usan el ciclo (empieza y acaba el ACERCAMIENTO, cuenta el agujero) y el grabador (corta los
    episodios)."""

    def __init__(self, zona: bool = True, exigir_agarre: bool = True):
        self.zona = zona
        self.exigir_agarre = exigir_agarre
        self._percepcion = False
        self.clavada = False
        self.ancla: np.ndarray | None = None
        self.ancla_desde: float | None = None
        self.desde: float | None = None  # t de la clavada
        self._apoyo_desde: float | None = None
        self._sin_apoyo_desde: float | None = None

    def _de_percepcion(self, b) -> bool:
        """¿La percepción da ya la clavada (`Broca.clavada_desde`, `levantada_en`, `evento`, con su histéresis)? Entonces
        manda ella: no se espera T_CLAVADA ni T_LEVANTADA. La verdad de la simulación no la da (se usa `apoyada`)."""
        if b.clavada_desde is not None or b.levantada_en is not None or b.evento:
            self._percepcion = True
        return self._percepcion

    def candidata(self, escena: Escena) -> bool:
        ta, b = escena.taladro, escena.broca
        P = punta_de(escena)
        apoyada = (b.clavada_desde is not None) if self._de_percepcion(b) else b.apoyada
        if not (ta.visible and (ta.agarrado or not self.exigir_agarre) and apoyada and P is not None):
            return False
        if P[2] - g.ALTURA_CARA_TABLA > LEVANTADA_MM:
            return False
        if escena.madera is not None and not escena.madera.contiene(P[:2]):
            return False
        return not self.zona or en_zona_taladro(P, TOLERANCIA_ZONA)

    def por_que_no(self, escena: Escena) -> str:
        """Si la broca está apoyada pero no cuenta como clavada, por qué (para el log de la grabación); si no, ''."""
        ta, b = escena.taladro, escena.broca
        apoyada = (b.clavada_desde is not None) if self._de_percepcion(b) else b.apoyada
        if not apoyada or self.candidata(escena):
            return ""
        P = punta_de(escena)
        if not ta.visible or P is None:
            return "no veo el taladro (bola naranja)"
        if self.exigir_agarre and not ta.agarrado:
            return ("broca apoyada pero no veo una mano en el taladro (MediaPipe/color): no corto; sin exigir el "
                    "agarre: --sin-agarre")
        if P[2] - g.ALTURA_CARA_TABLA > LEVANTADA_MM:
            return f"punta a {P[2] - g.ALTURA_CARA_TABLA:.0f} mm de la madera"
        if escena.madera is not None and not escena.madera.contiene(P[:2]):
            return "punta fuera de la madera"
        return "punta fuera de la zona de taladro"

    def actualizar(self, escena: Escena) -> str | None:
        t = escena.t
        c = self.candidata(escena)
        P = punta_de(escena)
        if not self.clavada:
            if not c:
                self._apoyo_desde = None
                return None
            self._apoyo_desde = t if self._apoyo_desde is None else self._apoyo_desde
            if self._percepcion and escena.broca.clavada_desde is not None:
                self._apoyo_desde = min(self._apoyo_desde, float(escena.broca.clavada_desde))
            if self._percepcion or t - self._apoyo_desde >= T_CLAVADA - 1e-9:
                self.clavada, self.desde, self._sin_apoyo_desde = True, t, None
                self.ancla, self.ancla_desde = P.copy(), self._apoyo_desde
                return "clavada"
            return None
        alta = P is None or P[2] - g.ALTURA_CARA_TABLA > LEVANTADA_MM
        if c:
            self._sin_apoyo_desde = None
            d = float(np.linalg.norm(P[:2] - self.ancla[:2]))
            # se desliza: el agujero empieza a contar de nuevo; y mientras sigue deslizándose (< T_DESLIZA s desde el
            # último cambio) el ancla va con la punta (si no, se quedaba a mitad del deslizamiento, 6-8 mm del agujero)
            if d > MOVIDA_ANCLA or (d > SIGUE_DESLIZA and t - self.ancla_desde < T_DESLIZA):
                self.ancla, self.ancla_desde = P.copy(), t
            return None
        self._sin_apoyo_desde = t if self._sin_apoyo_desde is None else self._sin_apoyo_desde
        if alta or self._percepcion or \
                not (escena.taladro.visible and (escena.taladro.agarrado or not self.exigir_agarre)) or \
                t - self._sin_apoyo_desde >= T_LEVANTADA - 1e-9:
            self.clavada, self._apoyo_desde = False, None
            return "levantada"
        return None

    def segundos_en_ancla(self, t: float) -> float:
        return 0.0 if not self.clavada or self.ancla_desde is None else t - self.ancla_desde


def virtual_desde(control, q_lr, P):
    """(distancia en planta por detrás de P, z de la boca, inclinación) de la postura q_lr si la boca mira hacia P;
    si no, None. Como `Ciclo._virtual_desde_q`."""
    b, e = control.boca(_lr_a_q4(q_lr))
    n = np.hypot(e[0], e[1])
    if n < 1e-6:
        return None
    d = float(np.dot(np.asarray(P, float)[:2] - b[:2], e[:2] / n))
    inc = control.inclinacion(e)
    if d <= 0.0 or not -5.0 <= inc <= 75.0:
        return None
    return np.array([d, b[2], inc])


class HabilidadAcercamientoProgramado:
    """Acercamiento programado: de donde esté (la posición prudente) a la de aspirar, en dos fases (bajar y entrar), y
    se mantiene ahí siguiendo la broca. Cumple el contrato `garbi.tipos.Habilidad` (con `broca` y `caida` opcionales
    en la observación)."""

    nombre = "acercamiento_programado"

    def __init__(self, control):
        self.control = control
        self.cin = Cinematica(control)
        self.P: np.ndarray | None = None
        self.fase = "bajar"
        self._v = None
        self._q4 = None
        self._inc = None
        self._previa = None
        self._llegado = False
        self._entrada = None  # (q de la postura de entrada, punta para la que se calculó)
        self._eje_conocido = False

    def reiniciar(self, punta_mesa) -> None:
        p = np.asarray(punta_mesa, float).ravel()
        self.P = np.array([p[0], p[1], g.ALTURA_CARA_TABLA])
        self.fase = None  # se decide con la primera observación: "entrada" o "bajar"
        self._v = self._q4 = self._inc = self._previa = None
        self._llegado = False
        self._entrada = None
        self._eje_conocido = False

    def _postura_entrada(self, P, q4) -> np.ndarray | None:
        """Postura de entrada (boca a DISTANCIA_PRUDENTE mirando la broca) para P; en caliente si ya había una."""
        if self._entrada is not None and np.linalg.norm(self._entrada[1][:2] - P[:2]) < MOVIDA_ENTRADA:
            return self._entrada[0]
        previa = None if self._entrada is None else _lr_a_q4(self._entrada[0])
        # con el eje de la broca medido, ya a la distancia de bajar y con la inclinación de trabajo (en la recta desde
        # la prudente la holgura no baja de 28 mm); sin él, a la de 100 mm (la de 60 bajaba a -7 mm con el taladro
        # quizá inclinado 8°)
        distancia, incs = (DIST_BAJAR, TRABAJO_INC) if self._eje_conocido else (DISTANCIA_PRUDENTE, INC_PRUDENTE)
        r = self.cin.resolver(lambda inc: self.cin.junto_a(P, distancia, ALTURA_PRUDENTE, inc), incs, previa)
        if r is None:
            return None
        self._entrada = (forzar_montaje(self.control.a_lerobot(r[0])), P.copy())
        return self._entrada[0]

    def _hacia(self, q, previa, grados_s) -> np.ndarray:
        """Un paso de `previa` hacia `q` en línea recta (en articulaciones), como mucho `grados_s` por articulación."""
        d = q - previa
        m = float(np.max(np.abs(d)))
        maximo = grados_s / HZ_CONTROL
        return forzar_montaje(previa + (d if m <= maximo else d * (maximo / m)))

    @property
    def en_posicion(self) -> bool:
        """¿Ha llegado a la postura de aspirar?"""
        return self.fase == "aspirar" and self._llegado

    def accion(self, obs: dict) -> np.ndarray:
        estado = np.asarray(obs["state"], float)
        broca = obs.get("broca")
        if broca is not None:
            self.P = np.array([float(broca[0]), float(broca[1]), g.ALTURA_CARA_TABLA])
        P = self.P
        caida = float(obs.get("caida", 0.0) or 0.0)
        if self.fase is None:
            # desde la postura prudente la boca está a un lado de la broca: primero a la de entrada
            v = virtual_desde(self.control, estado, P)
            self._eje_conocido = bool(obs.get("eje_conocido", False))
            mira = v is not None and lateral_de_boca(self.control, estado, P) <= LATERAL_MAX
            # mirando la broca pero lejos (p. ej. al volver de apartarse por una mano), con el eje medido también por
            # la de entrada cercana: en línea recta es más rápido que colocar en planta, picar y bajar por separado
            lejos = v is not None and v[0] > DIST_BAJAR + 5.0 and self._eje_conocido
            self.fase = "bajar" if mira and not lejos else "entrada"
        if self.fase == "entrada":
            previa = estado if self._previa is None else self._previa
            q = self._postura_entrada(P, _lr_a_q4(previa))
            if q is not None:
                self._previa = self._hacia(q, previa, VELOCIDAD_ENTRADA)
                if np.max(np.abs(q - self._previa)) < 1.0:
                    self.fase, self._previa = "bajar", None
                    self._q4 = _lr_a_q4(q)
                    estado = q
                else:
                    return self._previa.copy()
            else:
                self.fase = "bajar"  # sin postura de entrada: directo (las guardias del ciclo mandan)
        if self._q4 is None:
            self._q4 = _lr_a_q4(estado)
        if self._inc is None:  # la primera inclinación de TRABAJO_INC con la que se llega a aspirar
            r = self.cin.resolver(lambda inc: self.cin.junto_a(P, DIST_BROCA, ALTURA_TRABAJO, inc), TRABAJO_INC,
                                  self._q4)
            self._inc = TRABAJO_INC[0] if r is None else r[1]
        meta = np.array([DIST_BAJAR if self.fase == "bajar" else DIST_BROCA, P[2] + ALTURA_TRABAJO + caida, self._inc])
        if self._v is None:
            self._v = virtual_desde(self.control, estado, P)
            if self._v is None:  # no mira hacia la broca: primero alto, sobre el objetivo, y después baja
                b, _ = self.control.boca(_lr_a_q4(estado))
                self._v = np.array([DISTANCIA_PRUDENTE, max(b[2], meta[1]) + ALTURA_PASO, self._inc])
        # frena al acercarse a la meta (el 20 % de lo que falta por paso, sin pasar de VELOCIDAD_RAMPA): parar en
        # seco desde la velocidad máxima hacía oscilar el brazo simulado y el borde real bajaba 7 mm bajo la orden
        falta = meta - self._v
        paso = np.clip(np.where(np.abs(falta) < 0.3, falta, GANANCIA * falta), -VELOCIDAD_RAMPA, VELOCIDAD_RAMPA)
        if meta[1] - self._v[1] > 1.0:
            paso[0] = paso[2] = 0.0  # si hay que subir (viene de abajo o la caída del brazo), primero sube
        elif abs(meta[0] - self._v[0]) > 1.0 and self.fase == "bajar":
            # se coloca en planta antes de bajar y de picar menos (cambiar a la vez la distancia y la inclinación
            # pasaba cerca de una singularidad: la muñeca saltaba 18° en un paso)
            paso[1] = paso[2] = 0.0
        elif abs(meta[2] - self._v[2]) > 1.0 and self.fase == "bajar":
            paso[1] = 0.0  # después la inclinación, todavía alta, y por último baja
        self._v = self._v + paso
        v = self._v
        # solo en caliente desde la postura anterior: con todas las semillas podría saltar a otra rama (un salto que
        # el ciclo toma por un fallo de la habilidad); si no hay solución cerca, se queda donde está
        q, err = self.control._resolver(self.cin.junto_a(P, v[0], v[1] - P[2], float(v[2])), self._q4, iteraciones=40)
        if err < TOLERANCIA_IK:
            self._q4 = q
        if np.allclose(self._v, meta, atol=0.5):
            self.fase = "entrar" if self.fase == "bajar" else "aspirar"
        q = forzar_montaje(self.control.a_lerobot(self._q4))
        # como mucho VELOCIDAD_MAX por articulación: la postura sigue a la del objetivo
        previa = estado if self._previa is None else self._previa
        # (en proporción, como `Ciclo._hacia`: recortar cada articulación por separado se salía del camino y la boca
        # bajaba al entrar)
        self._previa = self._hacia(q, previa, VELOCIDAD_MAX)
        self._llegado = bool(np.max(np.abs(q - self._previa)) < 1.0)
        return self._previa.copy()
