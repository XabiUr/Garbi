"""Ciclo final de Garbi (solución final, 20-11): máquina de estados a 30 Hz.

    Escena (percepción o verdad de la simulación) → CicloFinal.paso() → Orden (postura y señal «aspirar»)

Estados (tabla de `.plans/aspira/solucion-final.md`):

| Estado | Entra | Hace | Aspiradora |
|---|---|---|---|
| DESCANSO | Sin manos en el tapete y sin tareas durante `T_DESCANSO` (3 s) | Aparcado, respira | No |
| DESPIERTO | Manos en el tapete | Postura de espera (`ESPERA`), sin estorbar | No |
| PRUDENTE | Taladro agarrado (mano + taladro) | Postura prudente siguiendo la broca: la cámara de la muñeca mira la punta sobre la madera desde 180 mm (`postura_prudente`; holgura 69 mm, 35 sin eje medido); así ve la clavada y la levantada sin moverse. Si no cumple las guardias, la de entrada (boca a 100 mm) | No |
| ACERCAMIENTO | Broca clavada en la madera, en la zona de taladro | La `Habilidad` de acercamiento (ACT o la programada) | Sí |
| RETIRADA | Broca levantada (lo dice la percepción, no ACT) | Vuelve a la distancia prudente | No |
| LIMPIEZA | Ni taladro agarrado ni manos, y agujeros pendientes | Cada agujero con la boca picada (45-60°), fijo | Sí |

Reglas:
- Solo el taladro **agarrado** (`Taladro.agarrado`: una mano con el taladro) lleva a PRUDENTE: ni la mano sola ni el
  taladro dejado en la mesa. Si se pierde el agarre `T_SIN_AGARRE` s: de PRUDENTE a DESPIERTO; de ACERCAMIENTO a
  RETIRADA (y después a DESPIERTO).
- Agujero: la broca clavada ≥ `T_AGUJERO` (2 s) en el mismo sitio (y `verificar_agujero`, el gancho para la
  comprobación visual, que de momento dice que sí). Se apunta en el marco de la madera: si se mueve la madera, el
  agujero va con ella. Un apoyo de menos de 2 s no cuenta.
- LIMPIEZA: por cada agujero pendiente, a la partida (boca a 60°, o hasta 45° lejos del robot) sobre el agujero en
  su sitio actual y la espiral programada (`HabilidadEspiral`) durante `DURACION_LIMPIEZA`; si la madera se mueve, se
  vuelve a empezar ese agujero. Si aparecen manos o el taladro, se deja para después.
- Guardias por encima de todo, también de ACT (las de `garbi.ciclo.Ciclo`, que se reutiliza): velocidad (≤ 2,5° por
  paso), borde de la boca ≥ 3 mm, holgura con el taladro ≥ 10 mm + margen de la percepción (con huida si el taladro
  viene hacia el brazo) y, nuevo, holgura con las manos libres ≥ `MARGEN_MANO` (con huida). Si la habilidad de
  acercamiento pide un salto o la guardia la frena `FRENADAS_MAX` pasos seguidos, entra el respaldo (el acercamiento
  programado); si también al respaldo, RETIRADA y no se vuelve a acercar hasta que se levante la broca.
- Mano libre que se cruza junto a la boca en el ACERCAMIENTO (se ha movido > `MANO_MOVIDA` y holgura <
  `APARTARSE_MANO`), o mano quieta que frena el camino de la habilidad: se aparta a la de entrada (boca a 100 mm) y
  vuelve cuando la mano se ha ido `T_MANO_FUERA` s. La mano que sujeta el taladro la marca la percepción
  (`Mano.del_taladro`) y no cuenta como libre.

`escena_verdad` (en `garbi.ciclo`) rellena las manos y el agarre con la verdad de la simulación.
"""
from __future__ import annotations

from enum import Enum

import mujoco
import numpy as np

import garbi.lateral as L
from garbi import contrato as g
from garbi.acercamiento import (ALTURA_PRUDENTE, INC_PRUDENTE, DetectorClavada, HabilidadAcercamientoProgramado,
                                UV_PRUDENTE, postura_prudente, punta_de)
from garbi.ciclo import (ANTICIPACION, BANDA_SEGUIR, CAIDA_MAX, FRENADAS_MAX, HUIDA_HISTERESIS, MARGEN_BORDE,
                         MARGEN_HOLGURA, MARGEN_INCIERTO, MARGEN_PERCEPCION, MAX_GRADOS_PASO, PARTIDA_ALTURA,
                         PARTIDA_DIST, SALTO_HABILIDAD, TOLERANCIA_ZONA, UMBRAL_VIRUTA, Ciclo, Transicion,
                         _lr_a_q4)
from garbi.habilidad import HabilidadEspiral, inclinaciones_partida
from garbi.tipos import (DIST_MANO_TALADRO, DISTANCIA_PRUDENTE, DURACION_LIMPIEZA, UMBRAL_FRACCION_VIRUTA, Escena,
                         Habilidad, Orden, en_zona_taladro, forzar_montaje)

# --- posturas ------------------------------------------------------------------------------------------------------
# Despierto: el brazo levantado y algo adelantado, la boca hacia arriba (a ~165 mm del eje del robot y ~395 de alto):
# atento, pero lejos de la madera y de las manos.
ESPERA = np.array([0.0, -80.0, 45.0, -20.0, 0.0, 0.0])

# --- tiempos y umbrales ----------------------------------------------------------------------------------------------
T_DESCANSO = 3.0  # s sin manos en el tapete ni tareas para descansar
T_SIN_MANOS_LIMPIAR = 1.0  # s sin manos (ni taladro agarrado) antes de empezar a limpiar
T_SIN_AGARRE = 0.5  # s sin taladro agarrado para dejar de seguirlo (parpadeos de la percepción)
T_AGUJERO = 2.0  # s con la broca clavada en el mismo sitio para contar un agujero
T_MANO_FUERA = 0.5  # s sin mano cerca para volver al acercamiento
MARGEN_MANO = 15.0  # mm: holgura mínima del brazo con una mano libre (guardia)
APARTARSE_MANO = 40.0  # mm: con una mano libre más cerca, el acercamiento se aparta a la posición prudente
MANO_MOVIDA = 15.0  # mm que se mueve una mano libre (desde que empezó el acercamiento) para apartarse por ella
ALTURAS_MANO = (0.0, 35.0, 70.0)  # mm de la palma sobre la madera que se prueban (la cámara de arriba no da altura)
RADIO_MANO_CERCA = 260.0  # mm en planta de la mano a la boca: más lejos no se calcula la holgura (ahorra tiempo)
MOVIDA_MADERA = 3.0  # mm (o grados) que se mueve la madera para volver a empezar la limpieza de un agujero
MOVIDA_PRUDENTE = 2.0  # mm que se mueve la punta para volver a calcular la postura prudente
HOLGURA_MANO_PRUDENTE = 10.0  # mm por encima de MARGEN_MANO que la postura prudente deja con las manos libres


def manos_libres(escena: Escena) -> list[np.ndarray]:
    """(x, y) de las manos que no sujetan el taladro. La que lo sujeta es la que la percepción marca (`Mano.del_taladro`)
    o, si no marca ninguna, la más cercana al taladro agarrado (a menos de DIST_MANO_TALADRO): esa ya cuenta en la
    holgura con el taladro."""
    ta = escena.taladro
    xy = [np.asarray(m.xy, float)[:2] for m in escena.manos if not getattr(m, "del_taladro", False)]
    if len(xy) < len(escena.manos):
        return xy
    if ta.visible and ta.agarrado and ta.xy is not None and xy:
        d = [float(np.linalg.norm(p - np.asarray(ta.xy, float)[:2])) for p in xy]
        k = int(np.argmin(d))
        if d[k] < DIST_MANO_TALADRO:
            xy.pop(k)
    return xy


class EstadoFinal(str, Enum):
    DESCANSO = "descanso"
    DESPIERTO = "despierto"
    PRUDENTE = "prudente"
    ACERCAMIENTO = "acercamiento"
    RETIRADA = "retirada"
    LIMPIEZA = "limpieza"


ASPIRA = (EstadoFinal.ACERCAMIENTO, EstadoFinal.LIMPIEZA)
CON_TALADRO = (EstadoFinal.PRUDENTE, EstadoFinal.ACERCAMIENTO, EstadoFinal.RETIRADA)


class CicloFinal(Ciclo):
    """Máquina de estados de la solución final. `paso(escena, obs)` a 30 Hz devuelve la `Orden`.

    `acercamiento`: la habilidad del ACERCAMIENTO (`HabilidadACT(..., tarea=TAREA_ACERCAMIENTO)` o la programada);
    `respaldo`: la que entra si la guardia frena a la primera (por defecto, el acercamiento programado; None si la
    primera ya es la programada). `limpieza`: la espiral fija de la LIMPIEZA."""

    def __init__(self, control: L.ControlLateral, acercamiento: Habilidad | None = None,
                 respaldo: Habilidad | None = None, limpieza: Habilidad | None = None,
                 umbral_viruta: float = UMBRAL_VIRUTA, umbral_fraccion: float = UMBRAL_FRACCION_VIRUTA,
                 q_inicial=None):
        limpieza = limpieza or HabilidadEspiral(control)
        super().__init__(control, limpieza, None, umbral_viruta, q_inicial, umbral_fraccion)
        programado = HabilidadAcercamientoProgramado(control)
        self.acercamiento = acercamiento or programado
        if respaldo is None and self.acercamiento is not programado and \
                not isinstance(self.acercamiento, HabilidadAcercamientoProgramado):
            respaldo = programado
        self.respaldo_acercamiento = respaldo
        self.limpieza = limpieza
        self.estado = EstadoFinal.DESCANSO
        self.detector = DetectorClavada()
        self.agujeros_t: list[float] = []  # t en que se apuntó cada agujero
        self.respaldos = 0  # veces que entró el respaldo en el ACERCAMIENTO
        self.frenadas_habilidad = 0  # pasos en que la guardia frenó a la habilidad de acercamiento
        self.apartadas_mano = 0  # veces que el acercamiento se apartó por una mano libre
        self.huidas_mano = 0
        self.t_en_posicion: list[float] = []  # s desde la clavada hasta llegar a aspirar (acercamiento programado)
        self._agarre_visto = None  # t del último paso con el taladro agarrado
        self._sin_manos_desde = 0.0
        self._despierto_desde = 0.0
        self._manos_libres: list[np.ndarray] = []
        self._manos_ref: list[np.ndarray] = []  # manos libres al empezar el acercamiento (o al volver)
        self._hab_acerc: Habilidad | None = None
        self._bloqueo = False  # el respaldo tampoco pudo: no se vuelve a acercar hasta que se levante la broca
        self._ancla_retirada = None
        self._mano_cerca_desde = None
        self._mano_fuera_desde = None
        self._apartado_mano = False
        self._apuntado_ancla = None  # ancla de la clavada para la que ya se apuntó el agujero
        self._fase_limpieza = "ir"
        self._madera_barrido = None
        self._t_barrido = 0.0
        self._clavada_t = None
        self._en_posicion_apuntado = False
        self._prudente_q = self._prudente_xy = None  # postura prudente (mirando la broca) y la punta de su cálculo
        self._prudente_uv = 0  # índice en UV_PRUDENTE de la que se usa
        self.sin_prudente = 0  # pasos en PRUDENTE sin postura que mire la broca (en la de entrada)
        self._mocap_mano = control.M.body_mocapid[control.M.body("mano_libre").id]
        self._g_mano = [control.M.geom(n).id for n in ("mano_libre_palma", "mano_libre_dedos", "mano_libre_brazo")]

    def _junto(self, P, distancia, altura, incs, que, taladro_P=None, especificacion=None, extra=None,
               apartarse=False):
        """El de `Ciclo`, pero si con la inclinación elegida ya no hay postura (la broca se ha movido a donde esa
        inclinación no llega), al paso siguiente se vuelve a elegir entre `incs`."""
        motivo, llegado = super()._junto(P, distancia, altura, incs, que, taladro_P, especificacion, extra, apartarse)
        if motivo == "sin postura":
            self._inc_obj = self._v = None
        return motivo, llegado

    # --- gancho ------------------------------------------------------------------------------------------------
    def verificar_agujero(self, escena: Escena, punta_mesa) -> bool:
        """Gancho para comprobar con la cámara que hay agujero (supletorio, para el final). De momento, sí."""
        return True

    # --- API -----------------------------------------------------------------------------------------------------
    @property
    def tareas_pendientes(self) -> bool:
        return bool(self.pendientes)

    def paso(self, escena: Escena, obs: dict | None = None) -> Orden:
        self._t = escena.t
        if escena.madera is not None:
            self._madera = escena.madera
        self._obs = obs
        ta = escena.taladro
        agarrado = bool(ta.visible and ta.agarrado)
        if agarrado:
            self._agarre_visto = self._t
        incierta = escena.broca.fuente == "arriba" and not escena.broca.apoyada
        self._margen_holgura = MARGEN_HOLGURA + MARGEN_PERCEPCION + (
            MARGEN_INCIERTO if incierta and self.estado == EstadoFinal.PRUDENTE and escena.broca.eje is not None
            else 0.0)
        # cualquier taladro que se vea es un obstáculo para las guardias, aunque no esté agarrado
        P = self._punta(escena) if ta.visible else None
        self._P_taladro, self._eje = P, (escena.broca.eje if P is not None else None)
        self._incierta = incierta
        real = (obs or {}).get("state")
        if real is not None and self.estado in CON_TALADRO:
            caida = float(np.clip(self.borde(_lr_a_q4(self.q)) - self.borde(_lr_a_q4(real)), 0.0, CAIDA_MAX))
            self._caida += 0.1 * (caida - self._caida)
        elif self.estado not in CON_TALADRO:
            self._caida = 0.0
        # manos: la del taladro (cerca de él) ya está en la holgura con el taladro; las demás son «libres»
        self._manos_libres = manos_libres(escena)
        hay_manos = escena.manos_en_tapete or agarrado
        if hay_manos:
            self._sin_manos_desde = None
        elif self._sin_manos_desde is None:
            self._sin_manos_desde = self._t
        evento = self.detector.actualizar(escena)
        self._transiciones(escena, agarrado, hay_manos, evento)
        if (P is not None and self._huir()) or self._huir_mano():
            return self._orden()
        {EstadoFinal.DESCANSO: self._descanso, EstadoFinal.DESPIERTO: self._despierto,
         EstadoFinal.PRUDENTE: self._prudente, EstadoFinal.ACERCAMIENTO: self._acercamiento,
         EstadoFinal.RETIRADA: self._retirada, EstadoFinal.LIMPIEZA: self._limpieza}[self.estado](escena)
        return self._orden()

    def _orden(self) -> Orden:
        self.q = forzar_montaje(self.q)
        return Orden(q=self.q.copy(), aspirar=self.estado in ASPIRA, estado=self.estado.value, detalle=self.detalle)

    # --- transiciones ------------------------------------------------------------------------------------------
    def _cambiar(self, nuevo: EstadoFinal, motivo: str) -> None:
        if nuevo == self.estado:
            return
        self.transiciones.append(Transicion(self._t, self.estado.value, nuevo.value, motivo))
        self.estado = nuevo
        self._entrada = self._t
        self._v = self._inc_obj = self._ultimo = None
        self._frenadas_seguidas = 0
        if nuevo == EstadoFinal.DESPIERTO:
            self._despierto_desde = self._t
            # el taladro ya no está: la próxima vez la postura prudente vuelve a empezar por el primer píxel
            self._prudente_q = self._prudente_xy = None
            self._prudente_uv = 0
        if nuevo == EstadoFinal.LIMPIEZA:
            self._fase_limpieza, self._agujero = "ir", None

    def _transiciones(self, escena, agarrado, hay_manos, evento) -> None:
        e = self.estado
        sin_agarre = self._agarre_visto is None or self._t - self._agarre_visto >= T_SIN_AGARRE - 1e-9
        if evento == "levantada":
            self._bloqueo = False
        if agarrado and e in (EstadoFinal.DESCANSO, EstadoFinal.DESPIERTO, EstadoFinal.LIMPIEZA):
            self._cambiar(EstadoFinal.PRUDENTE, "taladro agarrado")
        elif e == EstadoFinal.PRUDENTE and sin_agarre:
            self._cambiar(EstadoFinal.DESPIERTO, "ya no hay taladro agarrado")
        elif e == EstadoFinal.ACERCAMIENTO and (sin_agarre or evento == "levantada" or not self.detector.clavada):
            self._empezar_retirada("broca levantada" if not sin_agarre else "ya no hay taladro agarrado")
        elif e == EstadoFinal.DESCANSO and hay_manos:
            self._cambiar(EstadoFinal.DESPIERTO, "manos en el tapete")
        elif e == EstadoFinal.LIMPIEZA and hay_manos:
            self._cambiar(EstadoFinal.DESPIERTO, "manos en el tapete: la limpieza, para después")

    def _empezar_retirada(self, motivo: str) -> None:
        self._ancla_retirada = (self.detector.ancla.copy() if self.detector.ancla is not None else
                                (self._P_taladro.copy() if self._P_taladro is not None else None))
        self._cambiar(EstadoFinal.RETIRADA, motivo)

    def _empezar_acercamiento(self, escena, P) -> None:
        self._hab_acerc = self.acercamiento
        self._hab_acerc.reiniciar(P)
        self._accion_anterior = None
        self._apartado_mano = False
        self._mano_cerca_desde = self._mano_fuera_desde = None
        self._manos_ref = [m.copy() for m in self._manos_libres]
        self._clavada_t = self._t
        self._en_posicion_apuntado = False
        self._cambiar(EstadoFinal.ACERCAMIENTO, "broca clavada")

    # --- manos ---------------------------------------------------------------------------------------------------
    def holgura_manos(self, q4, manos=None) -> float:
        """mm del brazo a la mano libre más cercana (la mano de la simulación puesta en cada mano vista, a varias
        alturas: la cámara de arriba no da la altura). inf si no hay manos libres cerca."""
        manos = self._manos_libres if manos is None else manos
        if not manos:
            return np.inf
        c = self.control
        boca, _ = c.boca(q4)
        cerca = [m for m in manos if np.linalg.norm(np.asarray(m)[:2] - boca[:2]) < RADIO_MANO_CERCA]
        if not cerca:
            return np.inf
        ft = np.zeros(6)
        mejor = np.inf
        for m in cerca:
            for h in ALTURAS_MANO:
                c.d.mocap_pos[self._mocap_mano] = np.array([m[0], m[1], g.ALTURA_CARA_TABLA + h]) * L.MM
                mujoco.mj_kinematics(c.M, c.d)
                for a in c._g_brazo:
                    for b in self._g_mano:
                        mejor = min(mejor, mujoco.mj_geomDistance(c.M, c.d, a, b, 0.3, ft) / L.MM)
        c.d.mocap_pos[self._mocap_mano] = np.array([0.0, 0.0, -2.0])
        return mejor

    def _guardia(self, candidato, taladro_P, destino=None) -> str:
        motivo = super()._guardia(candidato, taladro_P, destino)
        if motivo or not self._manos_libres:
            return motivo
        h = self.holgura_manos(_lr_a_q4(candidato))
        if h < MARGEN_MANO and h < self.holgura_manos(_lr_a_q4(self.q)):
            return f"mano a {h:.0f} mm"
        return ""

    def _huir_mano(self) -> bool:
        """Si una mano libre se ha acercado al brazo por debajo de la guardia, el paso que más se aparta de ella."""
        if not self._manos_libres:
            return False
        h0 = self.holgura_manos(_lr_a_q4(self.q))
        if h0 >= MARGEN_MANO - HUIDA_HISTERESIS:
            return False
        candidatos = [self._hacia(L.APARCADO)]
        for j in range(4):
            for s in (-1.0, 1.0):
                c = self.q.copy()
                c[j] += s * MAX_GRADOS_PASO
                candidatos.append(c)
        mejor, h_mejor = None, h0
        for c in candidatos:
            q4 = _lr_a_q4(c)
            if self.borde(q4) < MARGEN_BORDE or self.holgura(q4) < MARGEN_HOLGURA:
                continue
            h = self.holgura_manos(q4)
            if h > h_mejor + 0.2:
                mejor, h_mejor = c, h
        if mejor is None:
            return False
        self.q = mejor
        self._v = self._inc_obj = self._ultimo = None
        self.huidas_mano += 1
        self.detalle = f"una mano viene hacia mí: me aparto (holgura {h0:.0f} → {h_mejor:.0f} mm)"
        return True

    # --- estados ---------------------------------------------------------------------------------------------------
    def _descanso(self, escena: Escena) -> None:
        f = 2.0 * np.sin(2 * np.pi * (self._t - self._entrada) / 4.0)  # respira: ±2° cada 4 s
        self._avanzar(L.APARCADO + np.array([0.0, f, 0.0, -f, 0.0, 0.0]))
        self.detalle = "descanso (respira)"

    def _despierto(self, escena: Escena) -> None:
        self._avanzar(ESPERA)
        self.detalle = "despierto: espero sin estorbar"
        if self._sin_manos_desde is None:
            return
        sin_manos = self._t - self._sin_manos_desde
        if self.pendientes and sin_manos >= T_SIN_MANOS_LIMPIAR:
            self._cambiar(EstadoFinal.LIMPIEZA, "sin manos ni taladro: limpio los agujeros")
        elif not self.pendientes and min(sin_manos, self._t - self._despierto_desde) >= T_DESCANSO:
            self._cambiar(EstadoFinal.DESCANSO, "sin manos ni tareas: descanso")

    def _prudente(self, escena: Escena) -> None:
        P = punta_de(escena) if escena.taladro.visible else None
        if P is None or not (escena.taladro.visible and escena.taladro.agarrado):
            self.detalle = "¿el taladro?"
            return
        tol = TOLERANCIA_ZONA
        if self.detector.clavada and not self._bloqueo and en_zona_taladro(self.detector.ancla, tol):
            self._empezar_acercamiento(escena, self.detector.ancla)
            self._acercamiento(escena)
            return
        if self._cerca_del_robot(P) or not en_zona_taladro(P, BANDA_SEGUIR + tol):
            self._avanzar(ESPERA)
            self._prudente_q = None
            self.detalle = "el taladro está fuera de la zona de taladro: espero"
            return
        aviso = (" · clavada fuera de la zona: no me acerco" if self.detector.clavada else "") + \
            (" · el respaldo no pudo: espero a que levantes" if self._bloqueo else "")
        q = self._postura_prudente(P)
        if q is not None:
            motivo = self._avanzar(q, P)
            self.detalle = "a la distancia prudente, mirando la broca" + (f" (guardia: {motivo})" if motivo else "") + \
                aviso
            return
        # sin postura prudente que cumpla las guardias: la de entrada (boca a 100 mm mirando la broca), sin ver la punta
        objetivo = np.array([P[0], P[1], g.ALTURA_CARA_TABLA])
        motivo, _ = self._junto(objetivo, DISTANCIA_PRUDENTE, ALTURA_PRUDENTE, INC_PRUDENTE, "prudente", P)
        self.sin_prudente += 1
        self.detalle = "a la distancia prudente (sin ver la punta)" + (f" (guardia: {motivo})" if motivo else "") + aviso

    def _postura_prudente(self, P) -> np.ndarray | None:
        """Postura prudente (`garbi.acercamiento.postura_prudente`: la cámara de la muñeca mira la punta sobre la
        madera desde 180 mm) para la punta P, en caliente desde la anterior; se vuelve a calcular si la punta se mueve
        más de `MOVIDA_PRUDENTE` mm. Vale si cumple las guardias de borde y holgura (con la duda de la punta solo vista
        desde arriba) y deja `MARGEN_MANO + HOLGURA_MANO_PRUDENTE` con las manos libres; si no, se prueba con los otros
        píxeles de `UV_PRUDENTE` (empezando por el que se usaba). None si ninguna: entonces se usa la de entrada."""
        xy = np.asarray(P, float)[:2]
        if self._prudente_xy is not None and np.linalg.norm(xy - self._prudente_xy) < MOVIDA_PRUDENTE:
            return self._prudente_q
        orden = [self._prudente_uv] + [k for k in range(len(UV_PRUDENTE)) if k != self._prudente_uv]
        elegida = None
        for k in orden:
            q = postura_prudente(self.control, P, self._prudente_q if k == self._prudente_uv else None, UV_PRUDENTE[k])
            if q is None:
                continue
            q4 = _lr_a_q4(q)
            if self.borde(q4) < MARGEN_BORDE + 3.0 or self._holgura_dudosa(q4) < self._margen_holgura or \
                    self.holgura_manos(q4) < MARGEN_MANO + HOLGURA_MANO_PRUDENTE:
                continue
            elegida = q
            self._prudente_uv = k
            break
        self._prudente_q, self._prudente_xy = elegida, xy.copy()
        return elegida

    def _mano_cerca(self) -> bool:
        """¿Una mano libre que se ha movido (más de MANO_MOVIDA desde que empezó el acercamiento) está a menos de
        APARTARSE_MANO del brazo? Una mano quieta (apoyada en la madera) no aparta el acercamiento: la postura prudente
        y la de entrada pasan a 30-40 mm de la mano apoyada con su altura en duda (0-70 mm) y el acercamiento se
        apartaba al empezar, sin que la mano se moviera (F4). La guardia de MARGEN_MANO sigue valiendo siempre."""
        if self.holgura_manos(_lr_a_q4(self.q)) >= APARTARSE_MANO:
            return False
        return any(all(np.linalg.norm(m - r) > MANO_MOVIDA for r in self._manos_ref) for m in self._manos_libres)

    def _acercamiento(self, escena: Escena) -> None:
        P = punta_de(escena)
        # agujero: clavada ≥ T_AGUJERO en el mismo sitio (y el gancho de la comprobación visual)
        ancla = self.detector.ancla
        if ancla is not None and (self._apuntado_ancla is None or self._apuntado_ancla is not ancla) and \
                self.detector.segundos_en_ancla(self._t) >= T_AGUJERO - 1e-9 and self.verificar_agujero(escena, ancla):
            self._apuntar(ancla)
            self.agujeros_t.append(self._t)
            self._apuntado_ancla = ancla
        # una mano libre se cruza cerca: se aparta a la posición prudente y vuelve cuando se va
        if self._mano_cerca():
            self._mano_fuera_desde = None
            if not self._apartado_mano:
                self._apartado_mano = True
                self.apartadas_mano += 1
                self._v = self._inc_obj = self._ultimo = None
                self.transiciones.append(Transicion(self._t, "acercamiento", "acercamiento", "mano cerca: me aparto"))
        elif self._apartado_mano:
            self._mano_fuera_desde = self._t if self._mano_fuera_desde is None else self._mano_fuera_desde
            if self._t - self._mano_fuera_desde >= T_MANO_FUERA:
                self._apartado_mano = False
                self._manos_ref = [m.copy() for m in self._manos_libres]
                self._hab_acerc.reiniciar(P)
                self._accion_anterior = None
                self.transiciones.append(Transicion(self._t, "acercamiento", "acercamiento", "la mano se fue: vuelvo"))
        if self._apartado_mano:
            objetivo = np.array([P[0], P[1], g.ALTURA_CARA_TABLA])
            self._junto(objetivo, DISTANCIA_PRUDENTE, ALTURA_PRUDENTE, INC_PRUDENTE, "apartado", P, apartarse=True)
            self.detalle = "una mano cerca: me aparto y espero"
            return
        obs = dict(self._obs or {})
        obs["state"] = self.q.copy()
        obs["broca"] = P.copy()
        obs["caida"] = self._caida
        obs["eje_conocido"] = self._eje is not None
        accion = forzar_montaje(self._hab_acerc.accion(obs))
        anterior, self._accion_anterior = self._accion_anterior, accion
        if anterior is not None and np.max(np.abs(accion - anterior)) > SALTO_HABILIDAD:
            self.saltos_habilidad += 1
            self._pasar_a_respaldo_acercamiento(P, "la habilidad pide un salto")
            return
        motivo = self._avanzar(accion, anticipar=self.q + (1 + ANTICIPACION) * (accion - self.q))
        if motivo:
            self.frenadas_habilidad += 1
            if motivo.startswith("mano") and self._frenadas_seguidas >= 3:
                # una mano quieta en el camino (p. ej. apoyada junto a la recta de la prudente a la de entrada): se
                # aparta a la de entrada por otro camino (`_junto`) y vuelve desde ahí; no es culpa de la habilidad
                self._apartado_mano, self._mano_fuera_desde = True, None
                self.apartadas_mano += 1
                self._v = self._inc_obj = self._ultimo = None
                self._frenadas_seguidas = 0
                self.transiciones.append(Transicion(self._t, "acercamiento", "acercamiento",
                                                    f"{motivo}: me aparto y vuelvo por otro camino"))
                return
            if self._frenadas_seguidas >= FRENADAS_MAX:
                self._pasar_a_respaldo_acercamiento(P, motivo)
                return
        en_pos = getattr(self._hab_acerc, "en_posicion", False)
        if en_pos and not self._en_posicion_apuntado:
            self._en_posicion_apuntado = True
            self.t_en_posicion.append(self._t - self._clavada_t)
        self.detalle = ("aspiro junto a la broca" if en_pos else "me acerco a la broca") + \
            (f" (guardia: {motivo})" if motivo else "") + \
            (" [respaldo]" if self._hab_acerc is self.respaldo_acercamiento else "")

    def _pasar_a_respaldo_acercamiento(self, P, motivo: str) -> None:
        if self.respaldo_acercamiento is not None and self._hab_acerc is not self.respaldo_acercamiento:
            self._hab_acerc = self.respaldo_acercamiento
            self._hab_acerc.reiniciar(P)
            self._accion_anterior = None
            self._frenadas_seguidas = 0
            self.respaldos += 1
            self.transiciones.append(Transicion(self._t, "acercamiento", "acercamiento", f"respaldo: {motivo}"))
            self.detalle = f"guardia en el acercamiento: {motivo} → respaldo"
            return
        self._bloqueo = True
        self._empezar_retirada(f"guardia: {motivo}; no me acerco hasta que levantes")

    def _retirada(self, escena: Escena) -> None:
        A = self._ancla_retirada if self._ancla_retirada is not None else self._P_taladro
        if A is None:
            self._cambiar(EstadoFinal.DESPIERTO, "sin taladro")
            return
        objetivo = np.array([A[0], A[1], g.ALTURA_CARA_TABLA])
        motivo, llegado = self._junto(objetivo, DISTANCIA_PRUDENTE, ALTURA_PRUDENTE, INC_PRUDENTE, "retirada",
                                      self._P_taladro, apartarse=True)
        self.detalle = "me retiro a la distancia prudente" + (f" (guardia: {motivo})" if motivo else "")
        lejos = self._v is not None and self._v[0] >= DISTANCIA_PRUDENTE - 1.0
        if llegado or lejos or motivo == "sin postura" or self._frenadas_seguidas >= FRENADAS_MAX:
            agarrado = self._agarre_visto is not None and self._t - self._agarre_visto < T_SIN_AGARRE
            if agarrado:
                self._cambiar(EstadoFinal.PRUDENTE, "en la distancia prudente")
            else:
                self._cambiar(EstadoFinal.DESPIERTO, "retirado; ya no hay taladro agarrado")

    def _limpieza(self, escena: Escena) -> None:
        if self._agujero is None or self._agujero not in self.pendientes:
            if not self.pendientes:
                self._cambiar(EstadoFinal.DESPIERTO, "todo limpio")
                return
            self._agujero, self._repasos, self._fase_limpieza = self.pendientes[0], 0, "ir"
            self._v = self._inc_obj = self._ultimo = None
        H = self.agujero_en_mesa(self._agujero)
        if self._fase_limpieza == "ir":
            incs = inclinaciones_partida(H)
            motivo, llegado = self._junto(H, PARTIDA_DIST, PARTIDA_ALTURA, incs, "partida", None, incs)
            self.detalle = f"voy al agujero {self._agujero + 1}"
            if motivo == "sin postura" or (motivo and self._frenadas_seguidas >= FRENADAS_MAX):
                self._terminar(False, f"no llego a la partida ({motivo})")
                return
            if llegado:
                try:
                    self.limpieza.reiniciar(H)
                except ValueError as e:
                    self._terminar(False, f"la espiral no alcanza: {e}")
                    return
                self._fase_limpieza, self._t_barrido, self._madera_barrido = "barrer", self._t, self._madera
                self.inclinaciones_partida.append((self._agujero, float(self._inc_obj)))
            return
        # barrer: si la madera se ha movido, el agujero se ha ido con ella: se vuelve a la partida
        m0, m1 = self._madera_barrido, self._madera
        if m0 is not None and m1 is not None and (np.hypot(m1.x - m0.x, m1.y - m0.y) > MOVIDA_MADERA or
                                                  abs(m1.giro - m0.giro) > MOVIDA_MADERA):
            self._fase_limpieza = "ir"
            self._v = self._inc_obj = self._ultimo = None
            self.detalle = "la madera se ha movido: vuelvo al agujero"
            return
        if self._t - self._t_barrido >= DURACION_LIMPIEZA - 1e-6:
            viruta, limpio = self.viruta_y_limpio(escena, self._agujero)
            if viruta is None or limpio or self._repasos >= 1:
                self._terminar(viruta is None or bool(limpio), "limpio" if viruta is None or limpio
                               else f"sigue sucio ({viruta})")
            else:
                self._repasos += 1
                self._fase_limpieza = "ir"
                self._v = self._inc_obj = self._ultimo = None
                self.transiciones.append(Transicion(self._t, "limpieza", "limpieza", f"queda viruta ({viruta}): repaso"))
            return
        accion = forzar_montaje(self.limpieza.accion({"state": self.q.copy()}))
        motivo = self._avanzar(accion, anticipar=self.q + (1 + ANTICIPACION) * (accion - self.q))
        if motivo and self._frenadas_seguidas >= FRENADAS_MAX:
            self._terminar(False, f"guardia: {motivo}")
            return
        self.detalle = f"limpio el agujero {self._agujero + 1}"

    def _terminar(self, limpio: bool, motivo: str) -> None:
        i = self._agujero
        if i in self.pendientes:
            self.pendientes.remove(i)
        (self.limpios if limpio else self.fallidos).add(i)
        self.transiciones.append(Transicion(self._t, "limpieza", "limpieza", f"agujero {i + 1}: {motivo}"))
        self._agujero = None
        self._fase_limpieza = "ir"
        self._v = self._inc_obj = self._ultimo = None
