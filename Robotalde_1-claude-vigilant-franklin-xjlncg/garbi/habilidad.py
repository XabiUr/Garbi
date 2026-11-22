"""Paso 7 de Garbi: limpiar la zona del agujero (especificación técnica, M5).

    q0 = posicion_partida(control, agujero_mesa, rng)      # boca a 60°, 35 mm del agujero, 30 mm de altura
    habilidad = HabilidadEspiral(control)                    # barrido programado (demostraciones automáticas)
    habilidad = HabilidadACT("salidas/garbi_act")            # o la política ACT entrenada (carpeta o repo del Hub)
    habilidad.reiniciar(agujero_mesa)
    for _ in range(PASOS_LIMPIEZA):                          # 5 s a 30 Hz, fijos
        q = habilidad.accion({"top": img_top, "wrist": img_wrist, "state": q_actual})

Las dos cumplen el contrato `garbi.tipos.Habilidad` y devuelven 6 articulaciones en grados de LeRobot, con la muñeca
fija y la pinza cerrada (`forzar_montaje`).

Geometría (mm, marco de la mesa; `control` es un `garbi.lateral.ControlLateral` del montaje lateral):
- **Posición de partida**: el centro de la boca a `DISTANCIA_PARTIDA` en planta del centro del agujero (por detrás,
  según hacia dónde mira la boca) y a `ALTURA_PARTIDA` sobre la cara de la madera, inclinada 60°. A 60° el eje de la
  boca solo llega a apuntar hasta ~375 mm del eje del robot, así que lejos se baja la inclinación hasta 45° (el
  mínimo de la especificación): `inclinaciones_partida` elige la más alta con la que la espiral llega hasta
  `MARGEN_ESPIRAL` mm por fuera del agujero (60° hasta r ≈ 354 mm, 55° hasta ≈ 377, 50° hasta ≈ 400 y 45° más allá).
  El ciclo usa la misma lista. Agujeros a más de `ALCANCE_AGUJERO` (433 mm) del eje del robot no se limpian.
- **Espiral**: el punto donde el eje de la boca corta la madera recorre `VUELTAS` vueltas alrededor del agujero, con
  el radio de `RADIO_INICIAL` a `RADIO_FINAL`, la boca a `ALTURA_PARTIDA` y con la inclinación de la partida. Cada
  postura sale de la anterior (sin saltar de rama de la cinemática inversa). Los puntos más allá del alcance
  (`ALCANCE_APUNTAR`, por inclinación) se llevan a ese radio; si aun así no llega, el punto se acerca al robot hasta
  `RECORTE_MAX`, y si ni así, se repite la postura anterior.
- **Velocidad**: si recorrer la espiral a `VELOCIDAD_MAX` no cabe en los 5 s, se dan menos vueltas (`VUELTAS_MIN`);
  y `limitar_velocidad` la sigue por el propio camino (sin recortar esquinas en el espacio articular, que metía la
  boca bajo la madera).
- La espiral empieza en el ángulo en que está la boca respecto al agujero y los primeros `PASOS_MEZCLA` pasos funden
  la postura en que está el robot con la espiral, para no dar un salto si la partida tenía ruido.
- `HabilidadEspiral.registro` guarda por cada agujero la inclinación, las vueltas, el alcance y los recortes.
"""
from __future__ import annotations

import logging
from pathlib import Path

import numpy as np

from garbi import contrato as g
from garbi.tipos import DURACION_LIMPIEZA, HZ_CONTROL, TAREA_LIMPIEZA, forzar_montaje

log = logging.getLogger("garbi")

INCLINACION_PARTIDA = 60.0  # grados bajo la horizontal: la preferida
# Se prueban en orden: lejos del robot (la mitad lejana de la madera) a 60° no llega y se baja hasta 45°, el mínimo de
# la especificación (M4: pasada final a 45-60°). La espiral va con la misma inclinación que la partida.
INCLINACIONES_PARTIDA = (60.0, 55.0, 50.0, 45.0)
DISTANCIA_PARTIDA = 35.0  # mm en planta, del centro de la boca al centro del agujero
ALTURA_PARTIDA = 30.0  # mm del centro de la boca sobre la cara de la madera
RUIDO_MM = 5.0  # ± en x, y, z de la boca al grabar
RUIDO_GRADOS = 3.0  # ± en la inclinación al grabar
VUELTAS = 3.0
VUELTAS_MIN = 1.5  # si la espiral entera no cabe en 5 s a VELOCIDAD_MAX, se dan menos vueltas (nunca menos que esto)
RADIO_INICIAL, RADIO_FINAL = 10.0, 30.0
# Alcance medido (montaje lateral, boca a 30 mm sobre la madera, IK desde todas las semillas): hasta qué radio (mm,
# desde el eje del robot) puede apuntar el eje de la boca a la madera, según la inclinación. Es casi igual en todas
# las direcciones de la madera (±40°: 2-4 mm menos en los extremos); se deja ~2 mm de margen. Más allá, con
# arranque en caliente aún se llega unos mm, pero cerca de la singularidad las articulaciones van mucho más deprisa.
ALCANCE_APUNTAR = {60.0: 374.0, 55.0: 397.0, 50.0: 420.0, 45.0: 443.0}
# Agujeros más lejos que esto del eje del robot no se limpian (`posicion_partida` da None): la espiral iría casi
# entera recortada contra el borde del alcance y, en el límite, la cinemática no la sigue desde la partida.
ALCANCE_AGUJERO = ALCANCE_APUNTAR[45.0] - 10.0  # 433 mm
MARGEN_ESPIRAL = 20.0  # mm: se elige la inclinación más alta con la que la espiral llega hasta este radio por fuera
RECORTE_MAX, RECORTE_PASO = 30.0, 3.0  # mm: si aun así no llega, cuánto más se acerca al robot el punto
MAX_SALTO_GRADOS = 8.0  # por articulación y paso: más sería saltar a otra rama de la cinemática inversa
VELOCIDAD_MAX = 72.0  # °/s por articulación: la guardia del ciclo (M4) para el robot a 75 °/s
PASOS_LIMPIEZA = int(round(DURACION_LIMPIEZA * HZ_CONTROL))  # 150
PASOS_MEZCLA = 12
TOLERANCIA_IK = 0.8  # norma del residuo (mm y rad·30) por debajo de la cual la postura vale
RADIO_ZONA = 35.0  # mm: círculo alrededor del agujero en el que se cuenta la viruta (M3)

# Claves del dataset (`observation.images.top`, ...) para las de la `Habilidad` ({"top", "wrist", "state"})
CLAVES_DATASET = {"top": "observation.images.top", "wrist": "observation.images.wrist",
                  "state": "observation.state"}


def _punto3(agujero_mesa) -> np.ndarray:
    p = np.asarray(agujero_mesa, float).ravel()
    return p.copy() if p.size >= 3 else np.array([p[0], p[1], g.ALTURA_CARA_TABLA])


def postura_boca(control, punto, distancia: float, altura: float, inclinacion: float, q0=None):
    """4 articulaciones (rad) con la boca a `distancia` en planta de `punto` (por detrás, según mira), a `altura`
    sobre él y con `inclinacion`. Prueba primero la semilla `q0` (seguir una trayectoria) y luego las de `control`.
    Devuelve (q4, error) o None si no la alcanza."""
    residuo = control._junto_a(np.asarray(punto, float), distancia, altura)(inclinacion)
    semillas = ([np.asarray(q0, float)] if q0 is not None else []) + list(control.semillas)
    mejor = None
    for s in semillas:
        q, err = control._resolver(residuo, s)
        if mejor is None or err < mejor[1]:
            mejor = (q, err)
        if err < TOLERANCIA_IK:
            return mejor
    return None


def alcance_apuntar(inclinacion: float) -> float:
    """Radio (mm, desde el eje del robot) hasta el que llega a apuntar la boca con esa inclinación (interpolado)."""
    incs = sorted(ALCANCE_APUNTAR)
    return float(np.interp(inclinacion, incs, [ALCANCE_APUNTAR[i] for i in incs]))


def inclinaciones_partida(agujero_mesa, inclinaciones=INCLINACIONES_PARTIDA) -> tuple[float, ...]:
    """Inclinaciones que se prueban, en orden, para la partida y la espiral sobre `agujero_mesa`: desde la más alta
    con la que la espiral llega hasta `MARGEN_ESPIRAL` mm por fuera del agujero (si no, el lado lejano iría pegado al
    borde del alcance, recortado y con las articulaciones casi en la singularidad). El ciclo usa la misma lista."""
    r = float(np.linalg.norm(np.asarray(agujero_mesa, float).ravel()[:2]))
    for k, inc in enumerate(inclinaciones):
        if r + MARGEN_ESPIRAL <= alcance_apuntar(inc):
            return tuple(inclinaciones[k:])
    return tuple(inclinaciones[-1:])


def postura_partida(control, agujero_mesa, rng=None, inclinaciones=INCLINACIONES_PARTIDA):
    """Como `posicion_partida`, pero devuelve (q4 en rad, inclinación usada) o None. Prueba en orden las
    `inclinaciones_partida` (60° cerca del robot; más lejos, hasta 45°); el ruido de la inclinación se suma a la que
    se prueba."""
    p = _punto3(agujero_mesa)
    if np.linalg.norm(p[:2]) > ALCANCE_AGUJERO:
        return None
    inclinaciones = inclinaciones_partida(p, inclinaciones)
    distancia, altura, d_inc = DISTANCIA_PARTIDA, ALTURA_PARTIDA, 0.0
    if rng is not None:
        dx, dy, dz = rng.uniform(-RUIDO_MM, RUIDO_MM, 3)
        p = p + np.array([dx, dy, 0.0])  # desplazar el objetivo en planta desplaza la boca lo mismo
        altura += dz
        d_inc = rng.uniform(-RUIDO_GRADOS, RUIDO_GRADOS)
    for inc in inclinaciones:
        r = postura_boca(control, p, distancia, altura, inc + d_inc)
        if r is not None:
            if inc != INCLINACIONES_PARTIDA[0]:
                log.debug("partida en (%.0f, %.0f) a %.0f°", p[0], p[1], inc)
            return r[0], inc + d_inc
    return None


def posicion_partida(control, agujero_mesa, rng=None) -> np.ndarray | None:
    """Postura (6 articulaciones, grados de LeRobot) de partida del paso 7 sobre `agujero_mesa` ((x, y) o (x, y, z),
    mm, marco de la mesa): boca a 60° (o hasta 45° si a 60° no llega, ver `INCLINACIONES_PARTIDA`), a 35 mm en planta
    del centro del agujero y 30 mm sobre la madera. Con `rng` añade ruido de ±5 mm en la posición de la boca y ±3° en
    la inclinación (para grabar). None si no la alcanza ni a 45°."""
    r = postura_partida(control, agujero_mesa, rng)
    return None if r is None else forzar_montaje(control.a_lerobot(r[0]))


def inclinacion_partida(control, agujero_mesa) -> float | None:
    """Inclinación (grados) con la que se hace la partida y la espiral sobre `agujero_mesa`, o None si no llega."""
    r = postura_partida(control, agujero_mesa)
    return None if r is None else r[1]


def puntos_espiral(centro_xy, angulo0: float, n: int = PASOS_LIMPIEZA, vueltas: float = VUELTAS) -> np.ndarray:
    """n puntos (x, y) de la espiral: `vueltas` vueltas desde `angulo0` (rad), radio de 10 a 30 mm."""
    s = np.linspace(0.0, 1.0, n)
    th = angulo0 + 2 * np.pi * vueltas * s
    r = RADIO_INICIAL + (RADIO_FINAL - RADIO_INICIAL) * s
    return np.asarray(centro_xy, float)[None, :2] + np.stack([np.cos(th) * r, np.sin(th) * r], axis=1)


def _en_camino(plan: np.ndarray, s: float) -> np.ndarray:
    """Postura en la posición `s` (índice fraccionario) del camino `plan`, interpolando entre vértices."""
    i = min(int(np.floor(s)), len(plan) - 1)
    j = min(i + 1, len(plan) - 1)
    return plan[i] + (s - i) * (plan[j] - plan[i])


def pasos_necesarios(plan: np.ndarray, grados_s: float = VELOCIDAD_MAX) -> float:
    """Pasos de control que hacen falta para recorrer `plan` sin pasar de `grados_s` en ninguna articulación."""
    if len(plan) < 2:
        return 0.0
    return float(np.sum(np.max(np.abs(np.diff(np.asarray(plan, float), axis=0)), axis=1)) / (grados_s / HZ_CONTROL))


def limitar_velocidad(plan: np.ndarray, grados_s: float = VELOCIDAD_MAX) -> np.ndarray:
    """La trayectoria `plan` (n × 6, grados) seguida sin pasar de `grados_s` en ninguna articulación y **sin salirse
    del camino**: donde la espiral pide más, la postura avanza por el propio camino lo que le da la velocidad y se
    queda atrás en él (llega más tarde, o no llega al final). Recortar en línea recta en el espacio articular, como se
    hacía antes, se come las esquinas del camino y cerca del alcance metía la boca bajo la madera (borde a -19 mm)."""
    plan = np.asarray(plan, float)
    paso = grados_s / HZ_CONTROL
    out = [plan[0].copy()]
    s = 0.0
    for k in range(1, len(plan)):
        q = out[-1]
        while s < k:
            j = min(int(np.floor(s)) + 1, k)  # siguiente vértice del camino
            if np.max(np.abs(plan[j] - q)) <= paso + 1e-9:
                s = float(j)
                continue
            a, b = s, float(j)  # el punto del tramo a `paso` de q (bisección)
            for _ in range(30):
                m = 0.5 * (a + b)
                if np.max(np.abs(_en_camino(plan, m) - q)) <= paso:
                    a = m
                else:
                    b = m
            s = a
            break
        out.append(_en_camino(plan, s))
    return np.array(out)


class HabilidadEspiral:
    """Barrido programado del paso 7: espiral de 3 vueltas (10 → 30 mm) alrededor del agujero, boca a 60° (hasta 45°
    lejos del robot), en 5 s."""

    nombre = "espiral"

    def __init__(self, control, altura: float = ALTURA_PARTIDA, inclinacion: float = INCLINACION_PARTIDA,
                 pasos: int = PASOS_LIMPIEZA, inclinaciones=None):
        self.control = control
        self.altura = altura
        # inclinaciones que se prueban en orden (la de la partida decide la de la espiral)
        if inclinaciones is None:
            inclinaciones = INCLINACIONES_PARTIDA if inclinacion == INCLINACION_PARTIDA else (inclinacion,)
        self.inclinaciones = tuple(inclinaciones)
        self.inclinacion = self.inclinaciones[0]  # la usada en el último `reiniciar`
        self.pasos = pasos
        self.plan: np.ndarray = np.zeros((0, 6))  # posturas de la espiral (grados de LeRobot)
        self.objetivos: np.ndarray = np.zeros((0, 2))  # punto de la espiral en cada paso
        self.apuntado: np.ndarray = np.zeros((0, 2))  # punto al que apunta de verdad (recortado si no llega)
        self.recortados = 0  # pasos en que el punto se acercó al robot porque no llegaba
        self.inalcanzables = 0  # pasos en que no llegó ni recortando (repite la postura anterior)
        self.alcance = np.inf  # mm del eje del robot hasta donde apunta la espiral (ALCANCE_APUNTAR)
        self.vueltas = VUELTAS  # vueltas de la última espiral (menos si no cabían en 5 s)
        self.avance = 1.0  # fracción del camino que recorre el plan limitado en velocidad
        self.registro: list[dict] = []  # una entrada por `reiniciar` (agujero, inclinación, vueltas, alcance...)
        self._i = 0
        self._q_inicio: np.ndarray | None = None
        self._previa: np.ndarray | None = None
        self.plan_ik: np.ndarray = np.zeros((0, 6))  # la espiral sin limitar la velocidad

    def _seguir(self, objetivo, q_prev):
        """Postura que apunta a `objetivo` desde `q_prev` sin saltar de rama, o None."""
        c = self.control
        delante = self.altura / np.tan(np.radians(self.inclinacion))
        if q_prev is None:
            r = postura_boca(c, objetivo, delante, self.altura, self.inclinacion)
            return None if r is None else r[0]
        residuo = c._junto_a(objetivo, delante, self.altura)(self.inclinacion)
        q, err = c._resolver(residuo, q_prev, iteraciones=40)
        salto = np.degrees(np.max(np.abs(q - q_prev)))
        return q if err < TOLERANCIA_IK and salto <= MAX_SALTO_GRADOS else None

    def _espiral(self, p, angulo0, q_ini, vueltas):
        """Plan de la espiral (posturas en grados de LeRobot, sin limitar) y los puntos apuntados."""
        c = self.control
        self.objetivos = puntos_espiral(p[:2], angulo0, self.pasos, vueltas)
        hacia_robot = -p[:2] / (np.linalg.norm(p[:2]) or 1.0)
        plan, apuntado = [], []
        self.recortados = self.inalcanzables = 0
        q_prev = q_ini
        for xy in self.objetivos:
            r = float(np.linalg.norm(xy))
            if r > self.alcance:  # recorte suave: el lado lejano de la espiral sigue el borde del alcance
                xy = np.asarray(xy) * (self.alcance / r)
                self.recortados += 1
            q = None
            # Al límite del alcance, el punto se acerca al robot de RECORTE_PASO en RECORTE_PASO (en dirección a su
            # eje): la boca sigue con su inclinación y el cono de captación, que es ancho, sigue cubriendo la zona.
            for recorte in np.arange(0.0, RECORTE_MAX + 1e-6, RECORTE_PASO):
                punto = np.asarray(xy) + hacia_robot * recorte
                q = self._seguir(np.array([punto[0], punto[1], p[2]]), q_prev)
                if q is not None:
                    self.recortados += bool(recorte > 0 and r <= self.alcance)
                    apuntado.append(punto)
                    break
            if q is None:
                self.inalcanzables += 1
                if q_prev is None:
                    continue
                apuntado.append(apuntado[-1] if apuntado else xy)
            else:
                q_prev = q
            plan.append(forzar_montaje(c.a_lerobot(q_prev)))
        if not plan:
            raise ValueError(f"la espiral alrededor de {p[:2]} no se alcanza con el montaje lateral")
        while len(plan) < self.pasos:  # los primeros puntos no se alcanzaban: se empieza por el primero que sí
            plan.insert(0, plan[0])
            apuntado.insert(0, apuntado[0])
        return np.array(plan), np.array(apuntado)

    def reiniciar(self, agujero_mesa) -> None:
        c = self.control
        p = _punto3(agujero_mesa)
        partida = postura_partida(c, p, inclinaciones=self.inclinaciones)
        q_ini = None if partida is None else partida[0]
        self.inclinacion = self.inclinaciones[0] if partida is None else partida[1]
        if q_ini is not None:
            boca, _ = c.boca(q_ini)
            angulo0 = float(np.arctan2(boca[1] - p[1], boca[0] - p[0]))
        else:
            angulo0 = float(np.arctan2(-p[1], -p[0]))  # empieza por el lado del robot
        self.alcance = alcance_apuntar(self.inclinacion)
        # Si recorrer la espiral entera a VELOCIDAD_MAX no cabe en los 5 s (cerca del alcance las articulaciones van
        # mucho más deprisa para el mismo camino de la boca), se dan menos vueltas: así se cubre igual de 10 a 30 mm.
        vueltas = VUELTAS
        for _ in range(3):
            plan_ik, apuntado = self._espiral(p, angulo0, q_ini, vueltas)
            necesarios = pasos_necesarios(plan_ik)
            disponibles = self.pasos - PASOS_MEZCLA
            if necesarios <= disponibles or vueltas <= VUELTAS_MIN:
                break
            vueltas = max(VUELTAS_MIN, vueltas * disponibles / necesarios)
        self.vueltas = vueltas
        self.plan_ik = plan_ik
        self.plan = limitar_velocidad(self.plan_ik)
        self.avance = float(min(1.0, (self.pasos - 1) / max(pasos_necesarios(self.plan_ik), 1e-9)))
        self.apuntado = apuntado
        self.registro.append({"agujero": [round(float(v), 1) for v in p[:2]], "inclinacion": round(self.inclinacion, 1),
                              "vueltas": round(vueltas, 2), "alcance": round(float(self.alcance), 1),
                              "recortados": self.recortados, "inalcanzables": self.inalcanzables,
                              "avance": round(self.avance, 2)})
        if self.inclinacion != self.inclinaciones[0] or vueltas < VUELTAS:
            log.info("espiral en (%.0f, %.0f): boca a %.0f°, %.1f vueltas", p[0], p[1], self.inclinacion, vueltas)
        self._i = 0
        self._q_inicio = None
        self._previa: np.ndarray | None = None

    @property
    def velocidad_max(self) -> float:
        """°/s máximos que pediría la espiral sin limitar (la que se ejecuta se queda en `VELOCIDAD_MAX`)."""
        if len(self.plan_ik) < 2:
            return 0.0
        return float(np.max(np.abs(np.diff(self.plan_ik[:, :4], axis=0))) * HZ_CONTROL)

    def accion(self, obs: dict) -> np.ndarray:
        if self._q_inicio is None:
            estado = obs.get("state") if isinstance(obs, dict) else None
            self._q_inicio = self.plan[0] if estado is None else np.asarray(estado, float).copy()
        k = min(self._i, len(self.plan) - 1)
        self._i += 1
        q = self.plan[k]
        if k < PASOS_MEZCLA:
            w = 0.5 - 0.5 * np.cos(np.pi * (k + 1) / PASOS_MEZCLA)
            q = self._q_inicio + (q - self._q_inicio) * w
        previa = self._q_inicio if self._previa is None else self._previa
        q = previa + np.clip(q - previa, -VELOCIDAD_MAX / HZ_CONTROL, VELOCIDAD_MAX / HZ_CONTROL)
        self._previa = forzar_montaje(q)
        return self._previa.copy()


class HabilidadACT:
    """Paso 7 con una política ACT de LeRobot 0.7 (`lerobot-train --policy.type=act`).

    Sirve también para el ACERCAMIENTO del ciclo final con `tarea=TAREA_ACERCAMIENTO` (las entradas de más que da el
    ciclo, `broca` y `caida`, se ignoran: solo mira `top`, `wrist` y `state`).

    `ruta_o_repo`: carpeta local (`pretrained_model`, un checkpoint o la salida del entrenamiento) o repo del Hub
    (`usuario/garbi_act`), que se descarga con `huggingface_hub.snapshot_download`. Las imágenes se redimensionan a la
    resolución con la que se entrenó, si es otra.
    """

    nombre = "act"

    def __init__(self, ruta_o_repo: str | Path, dispositivo: str = "cpu", politica=None, tarea: str = TAREA_LIMPIEZA):
        if politica is None:
            from robot.politica import PoliticaLeRobot

            politica = PoliticaLeRobot(self._resolver(ruta_o_repo), nombre="act", dispositivo=dispositivo)
        self.politica = politica
        self.tarea = tarea  # TAREA_LIMPIEZA (paso 7, ciclo viejo) o TAREA_ACERCAMIENTO (ciclo final)
        self.formas = {}  # clave del dataset → (alto, ancho) con que se entrenó
        config = getattr(politica, "config", None)
        for k, f in (getattr(config, "input_features", None) or {}).items():
            if k.startswith("observation.images.") and len(getattr(f, "shape", ())) == 3:
                self.formas[k] = tuple(f.shape[1:])  # (C, H, W)
        self.agujero: np.ndarray | None = None

    @staticmethod
    def _resolver(ruta_o_repo) -> Path:
        ruta = Path(ruta_o_repo)
        if ruta.exists():
            return ruta
        from huggingface_hub import snapshot_download

        return Path(snapshot_download(str(ruta_o_repo)))

    def reiniciar(self, agujero_mesa) -> None:
        self.agujero = _punto3(agujero_mesa)
        self.politica.reiniciar("garbi", "", self.tarea)

    def observacion(self, obs: dict) -> dict:
        """{"top", "wrist", "state"} → claves del dataset, con las imágenes a la resolución del entrenamiento."""
        import cv2

        salida = {}
        for k, v in obs.items():
            clave = CLAVES_DATASET.get(k, k)
            if clave.startswith("observation.images."):
                img = np.ascontiguousarray(v)
                forma = self.formas.get(clave)
                if forma is not None and img.shape[:2] != forma:
                    img = cv2.resize(img, (forma[1], forma[0]), interpolation=cv2.INTER_AREA)
                salida[clave] = img
            elif clave == "observation.state":
                salida[clave] = np.asarray(v, np.float32)
        return salida

    def accion(self, obs: dict) -> np.ndarray:
        return forzar_montaje(self.politica.accion(self.observacion(obs)))


# --- medir en la simulación -------------------------------------------------------------------------------------------
def limpiar_en_simulacion(mundo, habilidad, agujero_tabla, q_partida, observar: bool = False,
                          al_paso=None, estado_orden: bool = False) -> tuple[int, int]:
    """Pone el robot en `q_partida`, enciende la aspiradora y ejecuta `habilidad` `PASOS_LIMPIEZA` pasos sobre el
    agujero (marco de la madera). `al_paso(obs, accion)` se llama en cada paso antes de mover (para grabar).
    `estado_orden`: la habilidad recibe como «state» la orden anterior (la partida al empezar), como en el ciclo
    (`Ciclo._limpiar`) y en el dataset (`garbi.grabador`); si no, la postura medida.
    Devuelve (viruta antes, viruta después) en un círculo de `RADIO_ZONA` mm alrededor del agujero."""
    agujero_mesa = mundo.juez.tabla.a_mesa(np.asarray(agujero_tabla, float))
    mundo.reset_robot(q_partida)
    antes = mundo.viruta_alrededor(agujero_tabla, RADIO_ZONA)
    habilidad.reiniciar(np.array([agujero_mesa[0], agujero_mesa[1], g.ALTURA_CARA_TABLA]))
    mundo.aspiradora = True
    obs = mundo.observacion() if observar else {"observation.state": mundo.estado()}
    orden = np.asarray(q_partida, np.float32)
    for _ in range(PASOS_LIMPIEZA):
        entrada = {"state": orden if estado_orden else obs["observation.state"]}
        for cam in g.CAMARAS_POLITICA:
            if f"observation.images.{cam}" in obs:
                entrada[cam] = obs[f"observation.images.{cam}"]
        accion = np.asarray(habilidad.accion(entrada), np.float32)
        if al_paso is not None:
            al_paso(obs, accion)
        obs = mundo.step(accion, observar=observar)
        orden = accion
    mundo.aspiradora = False
    return antes, mundo.viruta_alrededor(agujero_tabla, RADIO_ZONA)
