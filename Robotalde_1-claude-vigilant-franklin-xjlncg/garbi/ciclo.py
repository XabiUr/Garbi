"""Ciclo de Garbi (M4 de la especificación técnica): máquina de estados a 30 Hz.

    Escena (percepción o verdad de la simulación) → Ciclo.paso() → Orden (postura del robot y señal «aspirar»)

Estados (tabla de M4):

| Estado | Postura | Sale cuando |
|---|---|---|
| APARCADO | Alto y recogido, respira | Taladro visible en la zona → SEGUIR |
| SEGUIR | Boca a 80 mm del marcador, 45 mm sobre la madera, 25° | Quieto 0,3 s → PREAPUNTO · fuera 1 s → IR_A_LIMPIAR (si hay agujeros) o APARCAR |
| PREAPUNTO | La cámara de la muñeca mira la punta a 120 mm (`garbi.percepcion.postura_mirar_broca`, T1); si no hay, 30 mm más atrás que al acompañar y 20 mm sobre la punta, 15° | Apoyada → ACOMPANAR · se mueve > 12 mm → SEGUIR |
| ACOMPANAR | Boca a 30 mm de la broca, 15°; en dos fases (baja y entra); corrige ≤ 5 mm | Punta > 8 mm sobre la madera → SEGUIR |
| IR_A_LIMPIAR | Boca a 60°, 35 mm del centro del agujero, 30 mm de altura | Llega → LIMPIAR |
| LIMPIAR | La `Habilidad` (ACT o el barrido programado) durante DURACION_LIMPIEZA | Fin → REVISAR |
| REVISAR | Boca alta sobre el agujero | Limpio → asiente y siguiente o APARCAR · sucio 1.ª → repasa · sucio 2.ª → siguiente |
| PASADA_FINAL | Zigzag de 4 carriles sobre la madera, boca a 45-60°, 40 mm/s (se pide con `pasada_final()`) | Fin → APARCAR |
| APARCAR | Va al aparcado | Llega → APARCADO |

El repaso de REVISAR pasa por IR_A_LIMPIAR para que la habilidad empiece siempre en la posición de partida (ACT se
entrena desde ahí).

Guardias en cada paso, también sobre lo que sale de la habilidad:
- ≤ 75 °/s por articulación: la orden avanza como mucho `MAX_GRADOS_PASO` por paso (como `max_relative_target`); si la
  habilidad pide un salto mayor que `SALTO_HABILIDAD`, se para y se pasa al barrido programado (M5, seguridad);
- borde de la boca ≥ 3 mm sobre la superficie que tiene debajo (madera o tapete);
- holgura ≥ 10 mm con el taladro (cuerpo, portabrocas y mano), salvo que el paso la aumente (se está apartando).
Si una guardia falla, el robot se queda quieto; si sigue fallando `FRENADAS_MAX` pasos, vuelve a SEGUIR (con el taladro)
o aparca (sin él). La muñeca y la pinza se fuerzan siempre (`forzar_montaje`).

Agujeros: el punto de la broca al apoyarla (tras `T_AGUJERO` s apoyada), en el marco de la madera: si se mueve la
madera, el agujero va con ella. Los índices de `Escena.viruta` son los de `Ciclo.agujeros`.

También aquí `escena_verdad`: una `Escena` construida con la verdad de la simulación, para probar sin visión. La
habilidad programada es `garbi.habilidad.HabilidadEspiral` (T3).
"""
from __future__ import annotations

import weakref
from collections import deque
from dataclasses import dataclass
from enum import Enum
from itertools import pairwise

import numpy as np

import garbi.lateral as L
from garbi import contrato as g
from garbi.habilidad import inclinaciones_partida
from garbi.tipos import (DURACION_LIMPIEZA, HZ_CONTROL, UMBRAL_FRACCION_VIRUTA, UMBRAL_PARTICULAS_VIRUTA, ZONA_TALADRO,
                         Broca, Escena, Habilidad, Mano, Orden, Taladro, en_zona_taladro, forzar_montaje)

# --- posturas (mm y grados) ------------------------------------------------------------------------------------
SEGUIR_DIST, SEGUIR_ALTURA, SEGUIR_INC = 80.0, 45.0, (25.0, 35.0, 15.0)
# Mientras no se sabe el eje de la broca (taladro quizá inclinado, ver INCLINACION_DUDA) se sigue más lejos: a 80 mm la
# peor holgura era de 13-18 mm y, desde ahí, el camino a la postura de mirar bajaba de la guardia (robustez del ciclo:
# PREAPUNTO ↔ SEGUIR sin fin); a 100 mm es de 31-36 mm.
SEGUIR_DIST_DUDA = 100.0
# centro de la boca sobre la madera al acompañar: con la boca a 15° el borde queda a ~7,5 mm (con 20 quedaba a 5,5 y,
# con el brazo estirado y el temblor de la mano, el borde real bajó a 2 mm: robustez del ciclo)
ALTURA_TRABAJO = 22.0
ALTURA_PASO = 40.0  # mm que sube sobre el objetivo cuando llega desde una postura que no mira hacia él
PREAPUNTO_ATRAS, PREAPUNTO_SUBIDA = 30.0, 20.0
# Al apartarse de la broca levantada: hasta esta distancia en planta (radio del portabrocas, de la boca y holgura) la
# boca solo se aleja (sin subir ni cambiar la inclinación): al subir o picar más, el tubo de la boca se encontraba con
# el portabrocas, que también sube (robustez del ciclo: holgura real 6-8 mm)
DIST_LIBRE = 55.0
TRABAJO_INC = (15.0, 20.0, 25.0)
# PREAPUNTO: la cámara de la muñeca mira la punta a 120 mm, en el píxel (150, 120) (fuera de las mordazas) y 10° hacia
# abajo. Con la distancia de 80 mm que propone T1 la boca queda bajo la cara de la madera (borde a -19 mm) si la broca
# está en la madera; a 120 mm y u = 150 el borde queda a ~34 mm y la holgura a ~41 mm.
MIRAR_DISTANCIA, MIRAR_UV, MIRAR_BAJADA = 120.0, (150.0, 120.0), 10.0
# Si la postura de mirar no deja holgura con la punta donde se cree que está y también si estuviera ±MIRAR_DUDA mm al
# lado (solo vista desde arriba, la punta va con ±10-15 mm), se prueba algo más lejos. Robustez del ciclo: en el primer
# agujero (sin apoyos que corrijan la altura por la bola) la punta estimada caía ~14 mm al lado y la postura de mirar
# pasaba a < 10 mm del taladro de verdad.
MIRAR_DISTANCIAS = (120.0, 150.0, 180.0)
MIRAR_DUDA = 15.0
# Taladro inclinado: hasta que la muñeca mide la punta, no se sabe cuánto ni hacia dónde (la persona lo inclina hasta
# ~8°; la bola, que es lo que se ve desde arriba, queda hasta 47 mm al lado de la vertical de la punta). Mientras el eje
# no se sabe (`Broca.eje` None), la holgura es la peor de las del taladro inclinado INCLINACION_DUDA hacia
# RUMBOS_DUDA rumbos alrededor de la bola (y vertical). Así la postura de mirar sale más lejos (150-180 mm) y, en cuanto
# la muñeca mide la punta, se vuelve a calcular cerca (120 mm) con el eje medido.
INCLINACION_DUDA = 8.0
RUMBOS_DUDA = 8
DESFASE_DUDA = g.ALTURA_BOLA_SOBRE_PUNTA * np.sin(np.radians(INCLINACION_DUDA))  # 47 mm
# De seguir a mirar, la recta en articulaciones cruza por delante del taladro (la boca y la cámara quedan a lados
# distintos: el giro de la base cambia ~30°) y la holgura bajaba a 2-15 mm con las de los extremos a 34-36 (robustez
# del ciclo). Se pasa antes por la postura de mirar desde MIRAR_LEJOS mm: de seguir a ella y de ella a las de 120-180
# mm la holgura no baja de ~28 mm.
MIRAR_LEJOS = 220.0
PREAPUNTO_INC = (15.0, 20.0, 25.0, 30.0, 35.0)  # cerca del robot (r < 300 mm) no llega a 15°
DIST_BROCA = 30.0  # en planta, de la boca al eje de la broca
VELOCIDAD_RAMPA = np.array([50.0, 50.0, 45.0]) / HZ_CONTROL  # por paso: mm (planta), mm (altura), grados
PARTIDA_DIST, PARTIDA_ALTURA = 35.0, 30.0  # posición de partida de la limpieza
PARTIDA_INC = 60.0
REVISAR_DIST, REVISAR_ALTURA, REVISAR_INC = 40.0, 90.0, (60.0, 45.0, 30.0)
LIMPIEZA_INC = (60.0, 55.0, 50.0, 45.0)  # dentro de la especificación (45-60°)
RESPALDO_INC = (40.0, 35.0, 30.0)  # fuera de la especificación: lejos del robot (r > 400 mm) no llega a 45°
PASADA_CARRILES = (-70.0, -25.0, 20.0, 65.0)  # x de cada carril en el marco de la madera
PASADA_MARGEN = 20.0  # mm del final de cada carril al canto de la madera
PASADA_VELOCIDAD = 40.0  # mm/s
ALTURA_LIMPIEZA = 15.0  # centro de la boca sobre la superficie al limpiar (borde a 7,5 mm con 60°)
BORDE_LIMPIEZA = 7.5  # mm mínimos del borde de la boca al limpiar (la guardia para a 3; el brazo simulado va ~3 mm por detrás) (7,5 con la boca a 7°: en la pasada final el brazo se quedaba 3,6 mm por debajo)

# --- tiempos y umbrales -------------------------------------------------------------------------------------------
MAX_GRADOS_PASO = 75.0 / HZ_CONTROL  # 2,5° por paso
SALTO_HABILIDAD = 15.0  # grados entre dos acciones seguidas de la habilidad: más es que no sigue una trayectoria suave
T_QUIETO = 0.3
T_FUERA = 1.0
T_AGUJERO = 1.0  # s apoyada para apuntar el agujero
MOVIDA_PREAPUNTO = 12.0
CORRIGE_MAX, MOVIDA_ACOMPANAR = 5.0, 12.0
LEVANTADA = 8.0  # punta sobre la madera para dejar de acompañar
# Con el taladro quieto y la punta vista solo desde arriba, la altura por el radio de la bola va con ±25 mm (M3) y,
# lejos del eje de la cámara, 15 mm de altura de más mueven la punta estimada ~14 mm en planta. Para mirar la broca
# (PREAPUNTO), si la altura estimada es menor que esto se supone apoyada: el marcador proyectado en el plano de la bola
# apoyada (`Taladro.xy`) es entonces exacto. Integración (T6): sin esto, en (310, 90) la postura de mirar apuntaba
# 14 mm al lado, la guardia de holgura (con la punta mal puesta) la frenaba y la broca nunca se veía apoyada.
ALTURA_DUDOSA = 30.0
MISMO_AGUJERO = 8.0
T_REVISAR = 0.5  # s mirando el agujero antes de decidir
T_ASENTIR = 1.0
UMBRAL_VIRUTA = UMBRAL_PARTICULAS_VIRUTA  # partículas (verdad de la simulación); con píxeles manda la fracción
MARGEN_HOLGURA = 10.0
# La guardia de holgura se calcula con la punta percibida (y el eje de la broca, si se sabe): para que la holgura real
# sea ≥ MARGEN_HOLGURA se le suma el error de la percepción en planta (muñeca y arriba fusionadas: ~2-4 mm, hasta 5 con
# el temblor de la mano) y lo que el brazo real se queda por detrás de la orden.
MARGEN_PERCEPCION = 5.0
# Huida: si con la postura actual la holgura (percibida) baja de la guardia, porque el taladro viene hacia el brazo, el
# brazo se aparta en vez de quedarse quieto (el paso de 2,5° por articulación que más la aumenta, o hacia el aparcado).
HUIDA_HISTERESIS = 2.0  # mm por debajo de la guardia para empezar a huir
# La huida se decide con la guardia base (sin MARGEN_INCIERTO) y, si la punta solo se ve desde arriba, con la peor
# holgura de la punta y de la punta ±MIRAR_DUDA en planta: con una sola estimación desviada 12 mm (al levantar la
# broca) la huida movía el brazo hacia el taladro de verdad (robustez del ciclo).
# Cerca del taladro (holgura de la orden < guardia + CERCA_LENTO) el brazo va a media velocidad: el brazo real se queda
# por detrás de la orden y, si una articulación se retrasa más que otras (el giro de la base, 3-4°), su camino se
# aparta del de las órdenes (holgura real 9 mm con la de la orden a 22).
CERCA_LENTO = 15.0
CAIDA_MAX = 8.0  # mm: lo más que se descuenta de la guardia del borde por lo que el brazo real cae bajo la orden
# Con la broca en el aire y vista solo desde arriba, la punta va con retraso y ±10-20 mm (altura por el radio de la
# bola): al seguirla (SEGUIR), la guardia de holgura deja este margen de más (en PREAPUNTO la postura de mirar ya se
# elige con esa duda, MIRAR_DUDA)
MARGEN_INCIERTO = 10.0
MARGEN_BORDE = 3.0
# Zona de taladro (tipos.ZONA_TALADRO, 320-420 mm del eje del robot). Solo se acompaña con la punta quieta dentro (con
# TOLERANCIA_ZONA, el error de la percepción); se sigue a distancia mientras esté a ±BANDA_SEGUIR de la zona; si
# viene hacia el robot (a menos de RADIO_APARTARSE de su eje), se aparca y no estorba (aparcado, la holgura con el
# taladro es ≥ 50 mm aunque la punta esté a 150 mm del eje).
TOLERANCIA_ZONA = 5.0
BANDA_SEGUIR = 30.0
RADIO_APARTARSE = ZONA_TALADRO[0] - 20.0  # 300 mm
# Sin el eje medido, la punta estimada desde arriba puede estar hasta DESFASE_DUDA mm al lado de la de verdad (bola de
# un taladro inclinado INCLINACION_DUDA): la zona se mira con esa tolerancia de más (para seguir y para ir a mirar la
# broca) y solo se aparca si la punta está seguro cerca del robot. Al medir la punta, la zona se mira ya con
# TOLERANCIA_ZONA (y si está fuera no se acompaña). Robustez del ciclo: con el taladro inclinado 5° hacia el robot la
# punta estimada caía a < 300 mm y Garbi se quedaba aparcado todo el agujero.
RADIO_BOCA = 15.0  # boquilla de Ø30
FRENADAS_MAX = 10
ANTICIPACION = 2.0  # pasos que se adelanta la guardia del borde
SUBIDA_ESCAPE = 2.0  # mm por paso que sube la boca cuando la recta hacia el objetivo la bajaría demasiado
LLEGADA = 1.0  # grados: ha llegado a la postura


class Estado(str, Enum):
    APARCADO = "aparcado"
    SEGUIR = "seguir"
    PREAPUNTO = "preapunto"
    ACOMPANAR = "acompanar"
    IR_A_LIMPIAR = "ir_a_limpiar"
    LIMPIAR = "limpiar"
    REVISAR = "revisar"
    PASADA_FINAL = "pasada_final"
    APARCAR = "aparcar"


ASPIRA = (Estado.ACOMPANAR, Estado.LIMPIAR, Estado.PASADA_FINAL)
CON_TALADRO = (Estado.SEGUIR, Estado.PREAPUNTO, Estado.ACOMPANAR)


def _lr_a_q4(q_lr) -> np.ndarray:
    from sim.entorno import lerobot_a_rad

    return lerobot_a_rad(np.asarray(q_lr, float))[:4]


class Cinematica:
    """Posturas del montaje lateral con inclinaciones a elegir y arranque en caliente (sobre `ControlLateral`)."""

    def __init__(self, control: L.ControlLateral):
        self.c = control

    def junto_a(self, P, distancia, altura, inc):
        return self.c._junto_a(np.asarray(P, float), distancia, altura)(inc)

    def limpiar(self, punto, inc):
        """El eje de la boca corta la superficie en `punto`. El centro de la boca va a ALTURA_LIMPIEZA, o más alto si
        con esa inclinación el borde quedaría a menos de BORDE_LIMPIEZA (margen para lo que el brazo real se queda
        por detrás de la orden)."""
        altura = max(ALTURA_LIMPIEZA, BORDE_LIMPIEZA + RADIO_BOCA * np.cos(np.radians(inc)))
        return self.junto_a(punto, altura / np.tan(np.radians(inc)), altura, inc)

    def trayectoria(self, puntos, incs, q0=None, por_punto=None):
        """Posturas (LeRobot) que limpian `puntos` uno tras otro con una sola inclinación, la primera de `incs` que
        llega a todos sin saltar de rama (o con la inclinación de cada punto, `por_punto`). Devuelve (posturas,
        inclinación, última q4) o None."""
        for inc in ([None] if por_punto is not None else incs):
            q, posturas = q0, []
            for k, p in enumerate(puntos):
                i_k = float(por_punto[k]) if por_punto is not None else inc
                res = self.resolver(lambda i, p=p: self.limpiar(p, i), (i_k,), q)
                if res is None or (q is not None and posturas and np.max(np.abs(res[0] - q)) > np.radians(10.0)):
                    break
                q = res[0]
                posturas.append(self.c.a_lerobot(q))
            if len(posturas) == len(puntos):
                return posturas, inc, q
        return None

    def resolver(self, residuo_de, incs, q0=None) -> tuple[np.ndarray, float] | None:
        """(q4 en rad, inclinación) con la primera inclinación de `incs` que tenga solución. Con `q0` prueba antes en
        caliente desde ahí (rápido); si no, con todas las semillas."""
        if q0 is not None:
            for inc in incs:
                q, err = self.c._resolver(residuo_de(inc), q0, iteraciones=40)
                if err < 0.8:
                    return q, inc
        for inc in incs:
            residuo = residuo_de(inc)
            for semilla in self.c.semillas:
                q, err = self.c._resolver(residuo, semilla)
                if err < 0.8:
                    return q, inc
        return None


@dataclass
class Transicion:
    t: float
    de: str
    a: str
    motivo: str


class Ciclo:
    """Máquina de estados de M4. `paso(escena, obs)` a 30 Hz devuelve la `Orden` (postura en grados de LeRobot)."""

    def __init__(self, control: L.ControlLateral, habilidad: Habilidad, respaldo: Habilidad | None = None,
                 umbral_viruta: float = UMBRAL_VIRUTA, q_inicial=None,
                 umbral_fraccion: float = UMBRAL_FRACCION_VIRUTA):
        self.control = control
        self.cin = Cinematica(control)
        self.habilidad = habilidad
        self.respaldo = respaldo  # barrido programado si salta una guardia con la habilidad (None: se revisa)
        # «Limpio»: si la escena trae `viruta_fraccion` (percepción por píxeles), fracción del círculo < umbral_fraccion;
        # si no (verdad de la simulación), `viruta` (partículas) ≤ umbral_viruta.
        self.umbral_viruta = umbral_viruta
        self.umbral_fraccion = umbral_fraccion
        self.inclinaciones_partida: list[tuple[int, float]] = []  # (agujero, inclinación) de cada partida
        self.q = forzar_montaje(L.APARCADO if q_inicial is None else q_inicial)  # orden actual
        self.estado = Estado.APARCADO
        self.agujeros: list[np.ndarray] = []  # (x, y) en el marco de la madera
        self.limpios: set[int] = set()
        self.fallidos: set[int] = set()
        self.pendientes: deque[int] = deque()
        self.transiciones: list[Transicion] = []
        self.frenadas = 0  # pasos en que una guardia no dejó moverse
        self.saltos_habilidad = 0
        self.subidas = 0  # pasos en que subió la boca para no bajar de MARGEN_BORDE
        self.fuera_de_especificacion: list[tuple[str, float]] = []  # (qué, inclinación) cuando no llega a la pedida
        self.detalle = "aparcado"
        self._pasada_pedida = False
        self._t = 0.0
        self._entrada = 0.0  # t de entrada al estado
        self._q4 = None  # última postura objetivo (rad), para arrancar en caliente
        self._frenadas_seguidas = 0
        self._quieto_desde = None
        self._fuera_desde = None
        self._ancla = None  # punta (mm, mesa) en PREAPUNTO y ACOMPANAR
        self._apoyo_desde = None
        self._apuntado = False
        self._puntas_apoyo: list = []  # punta (x, y) en cada paso del primer segundo apoyada (desde arriba)
        self._puntas_muneca: list = []  # las medidas por la muñeca (el último segundo antes de apoyar y el primero)
        self._muneca_preapunto: deque = deque(maxlen=40)  # (t, punta x, y) medidas por la muñeca en PREAPUNTO
        self._fase = "bajar"
        self._mirar = None  # postura de PREAPUNTO para mirar la broca (False: no hay)
        self._v = None  # objetivo intermedio (distancia, z, inclinación) de la boca, ver `_junto`
        self._inc_obj = None
        self._ultimo = None
        self._agujero = None  # índice del agujero que se limpia
        self._repasos = 0
        self._hab_activa: Habilidad | None = None
        self._accion_anterior = None
        self._revisado_desde = None
        self._asentir_desde = None
        self._pasada = None  # posturas (LeRobot) de la pasada final
        self.inclinaciones_pasada: list[float] = []  # de cada tramo de la última pasada final
        self._pasada_s = 0.0
        self._madera = None
        self._margen_holgura = MARGEN_HOLGURA
        self._apartarse = False  # al dejar de acompañar: apartarse en planta antes de subir
        self._P_taladro = None  # punta percibida del taladro (mm, mesa) en este paso, para las guardias; None si no se ve
        self._incierta = False  # la punta solo se ve desde arriba y no está apoyada
        self._caida = 0.0  # mm que el borde de la boca real queda por debajo del de la orden (con el taladro)
        self._eje = None  # eje de la broca percibido (None: vertical)
        self._sin_taladro_desde = None  # t desde el que no se ve el taladro (para limpiar desde APARCADO)
        self.huidas = 0  # pasos en que el brazo se apartó del taladro que venía hacia él
        self.deslizadas = 0  # pasos de lado (una o dos articulaciones) porque el recto acercaba al taladro
        self._mirar_con_eje = False  # la postura de mirar se calculó con el eje de la broca medido
        self._mirar_desde = 0  # primera de MIRAR_DISTANCIAS que se prueba (sube si la guardia no deja llegar)
        self._paso_mirar = None  # postura de paso (mirar desde MIRAR_LEJOS) antes de la de mirar
        self._con_paso = False  # al entrar en PREAPUNTO: hay que calcular la postura de paso
        self._marcador_ancla = None  # marcador del taladro (plano de la bola) al entrar en PREAPUNTO
        self._desde_apartarse = None  # punta apoyada al dejar de acompañar: de ella se aparta (no de la estimada)

    # --- API -----------------------------------------------------------------------------------------------------
    def pasada_final(self) -> None:
        """Pide la pasada final: se hace en cuanto no haya taladro ni agujeros pendientes."""
        self._pasada_pedida = True

    def agujero_en_mesa(self, i: int) -> np.ndarray:
        madera = self._madera or g.PoseTabla(0.0, 0.0, 0.0)
        return np.array([*madera.a_mesa(self.agujeros[i]), g.ALTURA_CARA_TABLA])

    def paso(self, escena: Escena, obs: dict | None = None) -> Orden:
        self._t = escena.t
        if escena.madera is not None:
            self._madera = escena.madera
        self._obs = obs
        incierta = escena.broca.fuente == "arriba" and not escena.broca.apoyada
        # sin eje medido, la holgura ya es la peor con el taladro inclinado (la punta hasta 47 mm al lado): no se suma
        # además MARGEN_INCIERTO (con los dos, el brazo no podía bajar del aparcado a seguir: robustez del ciclo)
        self._margen_holgura = MARGEN_HOLGURA + MARGEN_PERCEPCION + (
            MARGEN_INCIERTO if incierta and self.estado == Estado.SEGUIR and escena.broca.eje is not None else 0.0)
        P = self._punta(escena) if escena.taladro.visible else None
        self._P_taladro, self._eje = P, (escena.broca.eje if P is not None else None)
        self._incierta = incierta
        # Con el taladro (acompañando, con el brazo estirado) el brazo real cae unos mm bajo la orden por la gravedad:
        # la guardia del borde lo descuenta y ACOMPANAR trabaja esos mm más alto (robustez del ciclo: borde real 0,5 mm
        # con el de la orden a ~5 mm). Media móvil, para no seguir el retraso del brazo cuando se mueve.
        real = (obs or {}).get("state")
        if real is not None and self.estado in CON_TALADRO:
            caida = float(np.clip(self.borde(_lr_a_q4(self.q)) - self.borde(_lr_a_q4(real)), 0.0, CAIDA_MAX))
            self._caida += 0.1 * (caida - self._caida)
        elif self.estado not in CON_TALADRO:
            self._caida = 0.0
        if P is None:
            self._sin_taladro_desde = self._t if self._sin_taladro_desde is None else self._sin_taladro_desde
        else:
            self._sin_taladro_desde = None
        dentro = escena.taladro.visible and escena.taladro.en_zona and P is not None and \
            en_zona_taladro(P, self._tolerancia_zona())
        if dentro and self.estado not in CON_TALADRO:
            self._cambiar(Estado.SEGUIR, "taladro en la zona")
        elif self._cerca_del_robot(P) and self.estado in CON_TALADRO:
            self._cambiar(Estado.APARCAR, "el taladro viene hacia el robot (fuera de la zona): me aparto")
        if P is not None and self._huir():
            self.q = forzar_montaje(self.q)
            return Orden(q=self.q.copy(), aspirar=self.estado in ASPIRA, estado=self.estado.value,
                         detalle=self.detalle)
        manejador = {
            Estado.APARCADO: self._aparcado, Estado.SEGUIR: self._seguir, Estado.PREAPUNTO: self._preapunto,
            Estado.ACOMPANAR: self._acompanar, Estado.IR_A_LIMPIAR: self._ir_a_limpiar, Estado.LIMPIAR: self._limpiar,
            Estado.REVISAR: self._revisar, Estado.PASADA_FINAL: self._pasada_final, Estado.APARCAR: self._aparcar,
        }[self.estado]
        manejador(escena)
        self.q = forzar_montaje(self.q)
        return Orden(q=self.q.copy(), aspirar=self.estado in ASPIRA, estado=self.estado.value, detalle=self.detalle)

    # --- utilidades ------------------------------------------------------------------------------------------------
    def _cambiar(self, nuevo: Estado, motivo: str) -> None:
        if nuevo == self.estado:
            return
        self.transiciones.append(Transicion(self._t, self.estado.value, nuevo.value, motivo))
        self.estado = nuevo
        self._entrada = self._t
        self._v = self._inc_obj = self._ultimo = None
        self._mirar = None
        self._frenadas_seguidas = 0
        if nuevo == Estado.REVISAR:
            self._revisado_desde = self._asentir_desde = None
        if nuevo in (Estado.SEGUIR, Estado.APARCADO, Estado.APARCAR):
            self._ancla = None
        if nuevo != Estado.SEGUIR:
            self._apartarse = False
        if nuevo == Estado.PREAPUNTO:
            self._con_paso, self._paso_mirar, self._marcador_ancla = True, None, None
            self._muneca_preapunto.clear()
        if nuevo == Estado.SEGUIR:
            self._quieto_desde = None
            self._fuera_desde = None

    def _tolerancia_zona(self) -> float:
        """mm de más a cada lado de la zona de taladro: TOLERANCIA_ZONA, más DESFASE_DUDA si no se sabe el eje."""
        return TOLERANCIA_ZONA + (DESFASE_DUDA if self._eje is None else 0.0)

    def _cerca_del_robot(self, P) -> bool:
        """¿La punta está fuera de la zona de taladro, seguro a menos de RADIO_APARTARSE del eje del robot?"""
        duda = DESFASE_DUDA if self._eje is None else 0.0
        return P is not None and float(np.hypot(P[0], P[1])) < RADIO_APARTARSE - duda

    def holgura(self, q4, P=None) -> float:
        """Holgura (mm) de la postura q4 (rad) con el taladro percibido (punta P o la de este paso, y su eje). Sin eje
        medido, la peor con el taladro inclinado hasta INCLINACION_DUDA alrededor de la bola."""
        P = self._P_taladro if P is None else P
        if P is None:
            return np.inf
        if self._eje is not None:
            return self.control.holgura(q4, P, self._eje)
        return min(self.control.holgura(q4, tip, eje) for tip, eje in self._inclinaciones(P))

    @staticmethod
    def _inclinaciones(P):
        """(punta, eje) del taladro vertical con la punta en P y de los inclinados INCLINACION_DUDA con la bola en el
        mismo sitio (la punta se desplaza al otro lado)."""
        P = np.asarray(P, float)
        s, c = np.sin(np.radians(INCLINACION_DUDA)), np.cos(np.radians(INCLINACION_DUDA))
        out = [(P, None)]
        for k in range(RUMBOS_DUDA):
            a = 2 * np.pi * k / RUMBOS_DUDA
            e = np.array([s * np.cos(a), s * np.sin(a), c])
            out.append((P - np.array([e[0], e[1], 0.0]) * g.ALTURA_BOLA_SOBRE_PUNTA, e))
        return out

    def _holgura_dudosa(self, q4) -> float:
        """La holgura de `holgura`, y si la punta es incierta (solo desde arriba), la peor con la punta ±MIRAR_DUDA."""
        P = self._P_taladro
        if P is None:
            return np.inf
        if not self._incierta:
            return self.holgura(q4, P)
        return min(self.holgura(q4, P + np.array([dx, dy, 0.0]))
                   for dx, dy in ((0, 0), (MIRAR_DUDA, 0), (-MIRAR_DUDA, 0), (0, MIRAR_DUDA), (0, -MIRAR_DUDA)))

    def _huir(self) -> bool:
        """Si la holgura con la postura ordenada o con la real (la del brazo, que va por detrás) ha bajado de la
        guardia base (el taladro viene hacia el brazo), da el paso que más la aumenta: hacia el aparcado,
        ±MAX_GRADOS_PASO en una articulación o quedarse donde está el brazo (frenar), sin bajar el borde de la boca.
        Devuelve si ha huido."""
        umbral = MARGEN_HOLGURA + MARGEN_PERCEPCION - HUIDA_HISTERESIS
        real = (self._obs or {}).get("state")
        h_orden = self.holgura(_lr_a_q4(self.q))
        h_real = np.inf if real is None else self.holgura(_lr_a_q4(real))
        if min(h_orden, h_real) >= umbral:
            return False
        h0 = self._holgura_dudosa(_lr_a_q4(self.q))
        candidatos = [self._hacia(L.APARCADO)]
        if real is not None:
            candidatos.append(forzar_montaje(real))
        for j in range(4):
            for s in (-1.0, 1.0):
                c = self.q.copy()
                c[j] += s * MAX_GRADOS_PASO
                candidatos.append(c)
        mejor, h_mejor = None, h0
        for c in candidatos:
            q4 = _lr_a_q4(c)
            if self.borde(q4) < MARGEN_BORDE:
                continue
            h = self._holgura_dudosa(q4)
            if h > h_mejor + 0.2:
                mejor, h_mejor = c, h
        if mejor is None:
            return False
        self.q = mejor
        self._v = self._inc_obj = self._ultimo = None  # la rampa de `_junto` vuelve a empezar desde aquí
        self.huidas += 1
        self.detalle = f"el taladro viene hacia mí: me aparto (holgura {h0:.0f} → {h_mejor:.0f} mm)"
        return True

    def _punta(self, escena: Escena) -> np.ndarray | None:
        """Punta de la broca (mm, mesa): la medida, o la estimada bajo el marcador del taladro."""
        if escena.broca.punta is not None:
            return np.asarray(escena.broca.punta, float)
        if escena.taladro.xy is not None:
            return np.array([*escena.taladro.xy[:2], g.ALTURA_CARA_TABLA])
        return None

    def _punta_quieta(self, escena: Escena) -> np.ndarray | None:
        """Punta para mirar la broca con el taladro quieto: la de `_punta`, salvo si solo se ve desde arriba, no está
        apoyada y la altura estimada es baja (< ALTURA_DUDOSA): entonces, apoyada bajo el marcador."""
        P = self._punta(escena)
        b, ta = escena.broca, escena.taladro
        if P is not None and b.fuente == "arriba" and not b.apoyada and ta.xy is not None and \
                P[2] - g.ALTURA_CARA_TABLA < ALTURA_DUDOSA:
            xy = np.asarray(ta.xy, float)
            if b.eje is not None:  # taladro inclinado: la punta queda al otro lado de la bola
                xy = xy - b.eje[:2] / b.eje[2] * g.ALTURA_BOLA_SOBRE_PUNTA
            return np.array([xy[0], xy[1], g.ALTURA_CARA_TABLA])
        return P

    def _superficie(self, xy) -> float:
        if self._madera is not None and self._madera.contiene(xy, margen=-RADIO_BOCA):
            return g.ALTURA_CARA_TABLA
        return g.ALFOMBRILLA_GROSOR

    def borde(self, q4) -> float:
        """mm del punto más bajo del borde de la boca sobre la superficie que tiene debajo."""
        b, e = self.control.boca(q4)
        return float(b[2] - RADIO_BOCA * np.sqrt(max(0.0, 1.0 - e[2] ** 2)) - self._superficie(b[:2]))

    def _guardia(self, candidato, taladro_P, destino=None) -> str:
        """'' si se puede ir a `candidato` (LeRobot); si no, el motivo."""
        q4 = _lr_a_q4(candidato)
        if self.borde(q4) - self._caida < MARGEN_BORDE:
            return "borde de la boca bajo"
        # el brazo va por detrás de la orden (~6 mm a 75 °/s en la simulación): si sigue en esa dirección, ¿bajaría
        # de la superficie? Se mira ANTICIPACION pasos más allá (sin pasar de
        # `destino`)
        d = (forzar_montaje(destino) if destino is not None else np.asarray(candidato)) - self.q
        m = float(np.max(np.abs(d)))
        adelante = self.q + (d if m <= (1 + ANTICIPACION) * MAX_GRADOS_PASO else d * ((1 + ANTICIPACION) * MAX_GRADOS_PASO / m))
        if self.borde(_lr_a_q4(adelante)) < MARGEN_BORDE and self.borde(_lr_a_q4(adelante)) < self.borde(q4):
            return "borde de la boca bajo (anticipado)"
        P = taladro_P if taladro_P is not None else self._P_taladro
        if P is not None:
            h = self.holgura(q4, P)
            if h < self._margen_holgura and h < self.holgura(_lr_a_q4(self.q), P):
                return f"holgura {h:.0f} mm"
        return ""

    def _avanzar(self, destino, taladro_P=None, anticipar=None) -> str:
        """Avanza hacia `destino` (LeRobot) con la velocidad limitada y las guardias. Devuelve el motivo si frena.
        `anticipar`: hasta dónde mira la guardia del borde (por defecto, hasta `destino`)."""
        candidato = self._hacia(destino)
        P = taladro_P if taladro_P is not None else self._P_taladro
        if P is not None and self.holgura(_lr_a_q4(candidato), P) < self._margen_holgura + CERCA_LENTO:
            candidato = self._hacia(destino, 0.5)  # cerca del taladro, a media velocidad
        motivo = self._guardia(candidato, taladro_P, destino if anticipar is None else anticipar)
        if motivo.startswith("borde"):  # la recta entre posturas baja la boca: primero la sube un poco
            subida = self._subir()
            if subida is not None and not self._guardia(subida, taladro_P):
                self.q = subida
                self.subidas += 1
                return ""
        if motivo.startswith("holgura"):  # la recta acerca el brazo al taladro: ¿se puede avanzar de lado?
            lado = self._deslizar(destino, taladro_P)
            if lado is not None:
                self.q = lado
                self.deslizadas += 1
                self._frenadas_seguidas = 0
                return ""
        if motivo:
            self.frenadas += 1
            self._frenadas_seguidas += 1
            return motivo
        self.q = candidato
        self._frenadas_seguidas = 0
        return ""

    def _deslizar(self, destino, taladro_P=None) -> np.ndarray | None:
        """Cuando la guardia de holgura no deja dar el paso recto hacia `destino`: el paso que más acerca a `destino`
        moviendo una sola articulación (o dos) y que sí cumple las guardias; None si ninguno acerca. Robustez del ciclo:
        sin eje medido (holgura con el taladro quizá inclinado) la recta del aparcado a seguir, o de seguir a mirar,
        se quedaba frenada y el brazo no bajaba en todo el agujero."""
        d = forzar_montaje(destino) - self.q
        d0 = float(np.linalg.norm(d))
        mejor, d_mejor = None, d0 - 0.5
        paso = np.clip(d, -MAX_GRADOS_PASO, MAX_GRADOS_PASO)
        for js in ((0,), (1,), (2,), (3,), (0, 1), (1, 2), (2, 3), (0, 3)):
            c = self.q.copy()
            c[list(js)] += paso[list(js)]
            dist = float(np.linalg.norm(forzar_montaje(destino) - c))
            if dist >= d_mejor:
                continue
            if self._guardia(c, taladro_P, destino):
                continue
            mejor, d_mejor = c, dist
        return mejor

    def _hacia(self, destino, fraccion: float = 1.0) -> np.ndarray:
        """Un paso hacia `destino` en línea recta (en articulaciones), como mucho `fraccion` · MAX_GRADOS_PASO en
        cada una."""
        d = forzar_montaje(destino) - self.q
        m = float(np.max(np.abs(d)))
        maximo = fraccion * MAX_GRADOS_PASO
        return self.q + (d if m <= maximo else d * (maximo / m))

    def _subir(self) -> np.ndarray | None:
        """Un paso que sube la boca SUBIDA_ESCAPE mm sin moverla en planta ni cambiar su inclinación."""
        c = self.control
        q0 = _lr_a_q4(self.q)
        b, e = c.boca(q0)
        inc0 = np.radians(c.inclinacion(e))
        objetivo = b + np.array([0.0, 0.0, SUBIDA_ESCAPE])

        def residuo(q):
            bb, ee = c.boca(q)
            return np.array([*(bb - objetivo), 30.0 * (np.radians(c.inclinacion(ee)) - inc0)])
        q, err = c._resolver(residuo, q0, iteraciones=20)
        if err > 1.0:
            return None
        return self._hacia(c.a_lerobot(q))

    def _llegado(self, destino) -> bool:
        return bool(np.max(np.abs(forzar_montaje(destino) - self.q)) < LLEGADA)

    def _virtual_desde_q(self, P):
        """(distancia en planta por detrás de P, z de la boca, inclinación) de la postura actual, si mira hacia P."""
        b, e = self.control.boca(_lr_a_q4(self.q))
        n = np.hypot(e[0], e[1])
        if n < 1e-6:
            return None
        d = float(np.dot(np.asarray(P, float)[:2] - b[:2], e[:2] / n))
        inc = self.control.inclinacion(e)
        if d <= 0.0 or not -5.0 <= inc <= 75.0:
            return None
        return np.array([d, b[2], inc])

    def _junto(self, P, distancia, altura, incs, que, taladro_P=None, especificacion=None, extra=None,
               apartarse=False):
        """Lleva la boca a `distancia` en planta por detrás de P y `altura` sobre él con la primera inclinación de
        `incs` que tenga solución. El objetivo se mueve en el espacio de la boca (distancia, altura, inclinación) a
        velocidad limitada desde la postura actual, para que la interpolación entre posturas cercanas no baje la boca.
        Devuelve (motivo si frena, ha llegado)."""
        P = np.asarray(P, float)
        if self._inc_obj not in incs:
            r = self.cin.resolver(lambda inc: self.cin.junto_a(P, distancia, altura, inc), incs, self._q4)
            if r is None:
                return "sin postura", False
            self._inc_obj = r[1]
            if especificacion is not None and r[1] not in especificacion:
                self.fuera_de_especificacion.append((que, r[1]))
        meta = np.array([distancia, P[2] + altura, self._inc_obj])
        if self._v is None:
            self._v = self._virtual_desde_q(P)
            if self._v is not None and self._v[0] < distancia - 5.0 and self._v[1] > meta[1] + ALTURA_PASO:
                # está alta y casi encima de P (viene de mirar la broca, a 150-180 mm de la cámara): primero atrás a
                # su altura y después baja; si no, la rampa se quedaba encima, junto al portabrocas (robustez del
                # ciclo: la boca a 114 mm de la madera y a 16 mm del eje durante todo el taladro)
                self._v = np.array([distancia, self._v[1], self._inc_obj])
            if self._v is None:  # no mira hacia P: primero a una postura alta sobre el objetivo y después baja
                b, _ = self.control.boca(_lr_a_q4(self.q))
                self._v = np.array([distancia, max(b[2], meta[1]) + ALTURA_PASO, self._inc_obj])
        if self._ultimo is None or np.max(np.abs(self.q - self._ultimo)) < 3 * MAX_GRADOS_PASO:
            paso = np.clip(meta - self._v, -VELOCIDAD_RAMPA, VELOCIDAD_RAMPA)
            # sube antes de apartarse o acercarse, y se coloca en planta antes de bajar
            # al apartarse se aleja en planta y sube a la vez (en diagonal): sin subir, la boca iba ~1 s a 5 mm de
            # la madera y, con el brazo estirado, el seguimiento la bajaba hasta tocar (integración, T6)
            if apartarse and meta[0] - self._v[0] > 1.0:
                # pero hasta DIST_LIBRE sube despacio: al levantar la broca, el portabrocas (Ø45) sube a la altura
                # de la boca y del brazo (robustez del ciclo: subiendo a la vez la holgura real bajaba a 8 mm)
                if self._v[0] < DIST_LIBRE:
                    paso[1:] = 0.0
            elif paso[1] > 0 and meta[1] - self._v[1] > 1.0:
                paso[0] = 0.0
            elif paso[1] < 0 and abs(meta[0] - self._v[0]) > 1.0:
                paso[1] = 0.0
            self._v = self._v + paso
        v = self._v
        r = self.cin.resolver(lambda inc: self.cin.junto_a(P, v[0], v[1] - P[2], inc), (float(v[2]),), self._q4)
        if r is None:  # el camino intermedio no tiene solución: directo al objetivo
            self._v = meta.copy()
            r = self.cin.resolver(lambda inc: self.cin.junto_a(P, distancia, altura, inc), (self._inc_obj,), self._q4)
            if r is None:
                return "sin postura", False
        self._q4 = r[0]
        destino = self.control.a_lerobot(r[0])
        self._ultimo = destino
        if extra is not None:
            destino = destino + extra
        motivo = self._avanzar(destino, taladro_P)
        return motivo, bool(not motivo and np.allclose(self._v, meta) and self._llegado(destino))

    def _frenado_demasiado(self, escena: Escena, motivo: str) -> bool:
        if self._frenadas_seguidas < FRENADAS_MAX:
            return False
        if escena.taladro.visible:
            self._cambiar(Estado.SEGUIR, f"guardia: {motivo}")
        else:
            self._cambiar(Estado.APARCAR, f"guardia: {motivo}")
        return True

    # --- estados ---------------------------------------------------------------------------------------------------
    def _aparcado(self, escena: Escena) -> None:
        # se apartó porque el taladro venía hacia el robot: cuando ya no se ve, limpia lo que quede
        if self.pendientes and self._sin_taladro_desde is not None and self._t - self._sin_taladro_desde >= T_FUERA:
            self._cambiar(Estado.IR_A_LIMPIAR, "el taladro salió hace 1 s")
            return
        if self._pasada_pedida and not self.pendientes:
            self._empezar_pasada()
            return
        f = 2.0 * np.sin(2 * np.pi * (self._t - self._entrada) / 4.0)  # respira: ±2° cada 4 s
        self._avanzar(L.APARCADO + np.array([0.0, f, 0.0, -f, 0.0, 0.0]))
        self.detalle = "aparcado (respira)"

    def _seguir(self, escena: Escena) -> None:
        ta = escena.taladro
        P = self._punta(escena)
        if not (ta.visible and ta.en_zona and P is not None and en_zona_taladro(P, BANDA_SEGUIR)):
            if self._fuera_desde is None:
                self._fuera_desde = self._t
            self.detalle = "el taladro ha salido: espero"
            if self._t - self._fuera_desde >= T_FUERA:
                if self.pendientes:
                    self._cambiar(Estado.IR_A_LIMPIAR, "el taladro salió hace 1 s")
                else:
                    self._cambiar(Estado.APARCAR, "el taladro salió y no hay agujeros")
            return
        self._fuera_desde = None
        quieto = ta.quieto_desde is not None and self._t - ta.quieto_desde >= T_QUIETO
        fuera_de_zona = quieto and not en_zona_taladro(self._punta_quieta(escena), self._tolerancia_zona())
        if fuera_de_zona:
            quieto = False  # fuera de la zona de taladro no se acompaña: se sigue a distancia
        if quieto:
            self._ancla = self._punta_quieta(escena).copy()
            self._cambiar(Estado.PREAPUNTO, "taladro quieto 0,3 s")
            self._preapunto(escena)
            return
        # la punta (medida, o estimada con su altura) manda sobre el marcador proyectado en el plano de la bola apoyada
        xy = P[:2] if escena.broca.punta is not None else (ta.xy if ta.xy is not None else P[:2])
        if self._apartarse and self._desde_apartarse is not None:
            # al levantar la broca, la punta estimada desde arriba va con retraso (10-20 mm al lado): se aparta del
            # sitio donde estaba apoyada, que se conoce bien
            xy = self._desde_apartarse[:2]
        objetivo = np.array([xy[0], xy[1], g.ALTURA_CARA_TABLA])
        distancia = SEGUIR_DIST if self._eje is not None else SEGUIR_DIST_DUDA
        self._junto(objetivo, distancia, SEGUIR_ALTURA, SEGUIR_INC, "seguir", P, apartarse=self._apartarse)
        if self._v is not None and self._v[0] >= SEGUIR_DIST - 1.0:
            self._apartarse = False
            self._desde_apartarse = None
        self.detalle = ("taladro quieto fuera de la zona de taladro: no acompaño" if fuera_de_zona
                        else "sigo al taladro a distancia")

    def _preapunto(self, escena: Escena) -> None:
        ta = escena.taladro
        P = self._punta_quieta(escena)
        if not (ta.visible and ta.en_zona) or P is None:
            self._cambiar(Estado.SEGUIR, "taladro fuera")
            return
        if escena.broca.eje is not None and not self._mirar_con_eje:
            # la muñeca acaba de medir la punta (y el eje): la punta estimada desde arriba se corrige de golpe (hasta
            # 47 mm con 8°), no es que se haya movido. Se mira otra vez, ya de cerca.
            self._ancla, self._mirar, self._mirar_con_eje = P.copy(), None, True
        # Se ha movido si se han apartado la punta y también el marcador: la punta estimada desde arriba salta al
        # cambiar su altura estimada (o al medirla la muñeca) sin que el taladro se mueva, y el marcador proyectado se
        # desplaza al bajar la broca en vertical (robustez del ciclo: PREAPUNTO → SEGUIR sin moverse el taladro)
        marcador = ta.xy if ta.xy is not None else P[:2]
        if self._marcador_ancla is None:
            self._marcador_ancla = np.asarray(marcador, float).copy()
        if np.linalg.norm(P[:2] - self._ancla[:2]) > MOVIDA_PREAPUNTO and \
                np.linalg.norm(np.asarray(marcador) - self._marcador_ancla) > MOVIDA_PREAPUNTO:
            self._cambiar(Estado.SEGUIR, "el taladro se ha movido > 12 mm")
            return
        if escena.broca.eje is not None and not en_zona_taladro(P, TOLERANCIA_ZONA):
            self._cambiar(Estado.SEGUIR, "la punta medida está fuera de la zona de taladro: no acompaño")
            return
        if escena.broca.fuente == "muneca":
            self._muneca_preapunto.append((self._t, np.asarray(escena.broca.punta, float)[:2].copy()))
        if escena.broca.apoyada:
            self._ancla = np.array([P[0], P[1], g.ALTURA_CARA_TABLA])
            self._fase, self._apoyo_desde, self._apuntado, self._puntas_apoyo = "bajar", self._t, False, []
            self._puntas_muneca = [p for t, p in self._muneca_preapunto if self._t - t <= 1.0]
            self._cambiar(Estado.ACOMPANAR, "broca apoyada")
            self._acompanar(escena)
            return
        if self._mirar is None:
            self._mirar_con_eje = escena.broca.eje is not None
            self._mirar_desde = 0
            self._mirar = self._postura_mirar(self._ancla, MIRAR_DUDA if escena.broca.fuente != "muneca"
                                              else MARGEN_PERCEPCION)
            if self._con_paso and self._mirar is not False:
                self._con_paso = False
                self._paso_mirar = self._postura_paso(self._ancla)
        if self._mirar is not False:  # la cámara de la muñeca ve la punta de cerca (T1)
            if self._paso_mirar is not None:
                motivo = self._avanzar(self._paso_mirar, P)
                if self._llegado(self._paso_mirar):
                    self._paso_mirar = None
            else:
                motivo = self._avanzar(self._mirar, P)
            if motivo and self._frenadas_seguidas >= FRENADAS_MAX and \
                    self._mirar_desde + 1 < len(MIRAR_DISTANCIAS):
                # la guardia no deja llegar a esta postura de mirar: se prueba desde más lejos
                self._mirar_desde += 1
                otra = self._postura_mirar(self._ancla, MIRAR_DUDA if escena.broca.fuente != "muneca"
                                           else MARGEN_PERCEPCION)
                if otra is not False:
                    self._mirar, self._frenadas_seguidas, motivo = otra, 0, ""
        else:  # respaldo: la postura de preapunto de `garbi.lateral` (la broca queda lejos de la cámara)
            motivo, _ = self._junto(self._ancla, DIST_BROCA + PREAPUNTO_ATRAS, PREAPUNTO_SUBIDA, PREAPUNTO_INC,
                                    "preapunto", P)
        if motivo and self._frenado_demasiado(escena, motivo):
            return
        self.detalle = "preapunto: miro la broca"

    def _postura_paso(self, P):
        """Postura de paso hacia la de mirar: la de mirar la punta P desde MIRAR_LEJOS mm, si cumple las guardias de
        borde y holgura; si no, None (se va directo)."""
        from garbi.percepcion import postura_mirar_broca

        q = postura_mirar_broca(self.control, P, distancia=MIRAR_LEJOS, uv=MIRAR_UV, bajada=MIRAR_BAJADA)
        if q is None:
            return None
        q4 = _lr_a_q4(q)
        if self.borde(q4) < MARGEN_BORDE + 3.0 or self.holgura(q4, P) < MARGEN_HOLGURA + MARGEN_PERCEPCION:
            return None
        return forzar_montaje(q)

    def _postura_mirar(self, P, duda: float = MIRAR_DUDA):
        """Postura en la que la cámara de la muñeca ve la punta P de cerca (`garbi.percepcion.postura_mirar_broca`),
        a la primera distancia de MIRAR_DISTANCIAS que cumple las guardias de borde y holgura con la punta en P y a
        ±`duda` mm en planta; si ninguna, False."""
        from garbi.percepcion import postura_mirar_broca

        P = np.asarray(P, float)
        dudas = [P] + [P + np.array([dx, dy, 0.0]) for dx, dy in ((duda, 0), (-duda, 0), (0, duda), (0, -duda))]
        for k in range(self._mirar_desde, len(MIRAR_DISTANCIAS)):
            distancia = MIRAR_DISTANCIAS[k]
            q = postura_mirar_broca(self.control, P, distancia=distancia, uv=MIRAR_UV, bajada=MIRAR_BAJADA)
            if q is None:
                continue
            q4 = _lr_a_q4(q)
            if self.borde(q4) < MARGEN_BORDE + 3.0:
                continue
            if min(self.holgura(q4, d) for d in dudas) < MARGEN_HOLGURA + MARGEN_PERCEPCION:
                continue
            self._mirar_desde = k
            return forzar_montaje(q)
        return False

    def _acompanar(self, escena: Escena) -> None:
        ta = escena.taladro
        P = self._punta(escena)
        if not ta.visible or P is None:
            self._cambiar(Estado.SEGUIR, "taladro fuera")
            return
        # con la cámara de arriba sola la altura de la punta va con retraso: si la percepción dice que ya no está
        # apoyada (el marcador se ha apartado de donde estaba al apoyar), se da por levantada
        if P[2] - g.ALTURA_CARA_TABLA > LEVANTADA or (not escena.broca.apoyada and escena.broca.fuente == "arriba"):
            self._desde_apartarse = self._ancla.copy()
            self._cambiar(Estado.SEGUIR, "broca levantada")
            self._apartarse = True
            return
        desplazada = float(np.linalg.norm(P[:2] - self._ancla[:2]))
        if desplazada > MOVIDA_ACOMPANAR:
            self._cambiar(Estado.SEGUIR, "la broca se ha movido")
            self._apartarse = True
            return
        if not self._apuntado:
            # El agujero: la mediana de las puntas medidas por la muñeca en el último segundo antes de apoyar (la broca
            # baja en vertical: la punta en planta no cambia) y en el primero apoyada, a ≤ CORRIGE_MAX de la de ahora;
            # si hay menos de 3, la de todas las lecturas del primer segundo. Con una sola lectura (la primera
            # «apoyada», desde la postura de mirar lejana) el agujero iba a 3-6 mm del de verdad.
            (self._puntas_muneca if escena.broca.fuente == "muneca" else self._puntas_apoyo).append(P[:2].copy())
            if self._t - self._apoyo_desde >= T_AGUJERO:
                cerca = [p for p in self._puntas_muneca if np.linalg.norm(p - P[:2]) <= CORRIGE_MAX]
                puntas = cerca if len(cerca) >= 3 else self._puntas_apoyo + self._puntas_muneca
                self._apuntar(np.median(np.array(puntas), axis=0))
                self._apuntado = True
        A = self._ancla.copy()
        if desplazada <= CORRIGE_MAX:  # corrige si la broca se desplaza poco (sin mover el agujero apuntado)
            A[:2] = P[:2]
        # en dos fases: baja a la altura de trabajo sin acercarse y después entra en horizontal
        if self._fase == "bajar":
            _, llegado = self._junto(A, DIST_BROCA + PREAPUNTO_ATRAS, ALTURA_TRABAJO + self._caida, TRABAJO_INC,
                                     "acompañar", P)
            if llegado:
                self._fase = "entrar"
            self.detalle = "broca apoyada: bajo a la altura de trabajo y aspiro"
        else:
            self._junto(A, DIST_BROCA, ALTURA_TRABAJO + self._caida, TRABAJO_INC, "acompañar", P)
            self.detalle = "aspiro junto a la broca"

    def _apuntar(self, punta_mesa) -> None:
        madera = self._madera or g.PoseTabla(0.0, 0.0, 0.0)
        p = madera.a_tabla(np.asarray(punta_mesa, float)[:2])
        for i, h in enumerate(self.agujeros):
            if np.linalg.norm(h - p) < MISMO_AGUJERO:
                if i not in self.pendientes and i not in self.limpios:
                    self.pendientes.append(i)
                return
        self.agujeros.append(p)
        self.pendientes.append(len(self.agujeros) - 1)

    def _ir_a_limpiar(self, escena: Escena) -> None:
        if self._agujero is None or self._agujero not in self.pendientes:
            if not self.pendientes:
                self._cambiar(Estado.APARCAR, "no quedan agujeros")
                return
            self._agujero, self._repasos = self.pendientes[0], 0
        H = self.agujero_en_mesa(self._agujero)
        # las mismas inclinaciones que la espiral (`garbi.habilidad.inclinaciones_partida`): la habilidad empieza donde
        # la deja el ciclo (60° cerca del robot; lejos, hasta 45°)
        incs = inclinaciones_partida(H)
        motivo, llegado = self._junto(H, PARTIDA_DIST, PARTIDA_ALTURA, incs, "partida", None, incs)
        if motivo == "sin postura":
            self._terminar_agujero(False, "no alcanza la posición de partida")
            return
        if motivo and self._frenado_demasiado(escena, motivo):
            return
        self.detalle = f"voy al agujero {self._agujero + 1}"
        if llegado:
            self._hab_activa = self.habilidad
            try:
                self._hab_activa.reiniciar(self.agujero_en_mesa(self._agujero))
            except ValueError as e:  # la habilidad no alcanza el agujero
                self._terminar_agujero(False, f"la habilidad no puede: {e}")
                return
            self._accion_anterior = None
            self.inclinaciones_partida.append((self._agujero, float(self._inc_obj)))
            self._cambiar(Estado.LIMPIAR, f"en la posición de partida ({self._inc_obj:.0f}°)")

    def _limpiar(self, escena: Escena) -> None:
        if self._t - self._entrada >= DURACION_LIMPIEZA - 1e-6:
            self._cambiar(Estado.REVISAR, "fin de la limpieza")
            self._revisar(escena)
            return
        obs = dict(self._obs or {})
        obs["state"] = self.q.copy()
        accion = forzar_montaje(self._hab_activa.accion(obs))
        anterior, self._accion_anterior = self._accion_anterior, accion
        if anterior is not None and np.max(np.abs(accion - anterior)) > SALTO_HABILIDAD:
            self.saltos_habilidad += 1
            self._pasar_a_respaldo("la habilidad pide un salto")
            return
        # la acción de la habilidad es el paso siguiente: la guardia mira la misma dirección ANTICIPACION pasos más allá
        motivo = self._avanzar(accion, anticipar=self.q + (1 + ANTICIPACION) * (accion - self.q))
        if motivo and self._frenadas_seguidas >= FRENADAS_MAX:
            self._pasar_a_respaldo(motivo)
            return
        self.detalle = f"limpio el agujero {self._agujero + 1}"

    def _pasar_a_respaldo(self, motivo: str) -> None:
        self.detalle = f"guardia en la limpieza: {motivo}"
        if self.respaldo is not None and self._hab_activa is not self.respaldo:
            self._hab_activa = self.respaldo
            try:
                self._hab_activa.reiniciar(self.agujero_en_mesa(self._agujero))
            except ValueError:
                self._cambiar(Estado.REVISAR, f"guardia: {motivo}; el respaldo no alcanza")
                return
            self._entrada = self._t  # el respaldo tiene su tiempo entero
            self._accion_anterior = None
            self._frenadas_seguidas = 0
            self.transiciones.append(Transicion(self._t, "limpiar", "limpiar", f"respaldo: {motivo}"))
        else:
            self._cambiar(Estado.REVISAR, f"guardia: {motivo}")

    def _revisar(self, escena: Escena) -> None:
        H = self.agujero_en_mesa(self._agujero)
        if self._asentir_desde is not None:  # asiente: baja y sube la muñeca
            f = (self._t - self._asentir_desde) / T_ASENTIR
            self._junto(H, REVISAR_DIST, REVISAR_ALTURA, REVISAR_INC, "revisar",
                        extra=np.array([0, 0, 0, 10.0 * np.sin(np.pi * min(f, 1.0)), 0, 0]))
            self.detalle = f"agujero {self._agujero + 1} limpio"
            if f >= 1.0:
                self._terminar_agujero(True, "limpio")
            return
        _, llegado = self._junto(H, REVISAR_DIST, REVISAR_ALTURA, REVISAR_INC, "revisar")
        if not llegado and self._revisado_desde is None:
            self.detalle = f"subo a mirar el agujero {self._agujero + 1}"
            return
        if self._revisado_desde is None:
            self._revisado_desde = self._t
        if self._t - self._revisado_desde < T_REVISAR:
            self.detalle = f"miro el agujero {self._agujero + 1}"
            return
        viruta, limpio = self.viruta_y_limpio(escena, self._agujero)
        if viruta is None or limpio:
            self._asentir_desde = self._t
            self.detalle = f"agujero {self._agujero + 1} limpio" + (" (sin dato de viruta)" if viruta is None else "")
        elif self._repasos == 0:
            self._repasos = 1
            self._cambiar(Estado.IR_A_LIMPIAR, f"queda viruta ({viruta}): repaso")
        else:
            self._terminar_agujero(False, f"sigue sucio ({viruta}) tras el repaso")

    def viruta_y_limpio(self, escena: Escena, i: int):
        """(viruta del agujero i como texto, ¿limpio?) o (None, None) si la escena no la trae. Con la percepción por
        píxeles decide la fracción del círculo; con la verdad de la simulación, las partículas."""
        fraccion = (escena.viruta_fraccion or {}).get(i)
        if fraccion is not None:
            return f"{100 * fraccion:.1f} %", fraccion < self.umbral_fraccion
        viruta = escena.viruta.get(i)
        if viruta is None:
            return None, None
        return viruta, viruta <= self.umbral_viruta

    def _terminar_agujero(self, limpio: bool, motivo: str) -> None:
        i = self._agujero
        if i in self.pendientes:
            self.pendientes.remove(i)
        (self.limpios if limpio else self.fallidos).add(i)
        self._agujero = None
        if self.pendientes:
            self._cambiar(Estado.IR_A_LIMPIAR, f"agujero {i + 1} {motivo}: siguiente")
        elif self._pasada_pedida:
            self._empezar_pasada()
        else:
            self._cambiar(Estado.APARCAR, f"agujero {i + 1} {motivo}")

    # --- pasada final ----------------------------------------------------------------------------------------------
    def _empezar_pasada(self) -> None:
        madera = self._madera
        self._pasada_pedida = False
        if madera is None:
            self._cambiar(Estado.APARCAR, "sin madera para la pasada final")
            return
        ymax = g.TABLA_TAMANO[1] / 2 - PASADA_MARGEN
        esquinas = []
        for k, x in enumerate(PASADA_CARRILES):
            carril = [(x, -ymax), (x, ymax)]
            esquinas += carril if k % 2 == 0 else carril[::-1]
        pts = madera.a_mesa(np.array(esquinas))
        # puntos cada PASADA_VELOCIDAD / HZ_CONTROL mm a lo largo del zigzag; en cada tramo (carril o cambio de
        # carril) una sola inclinación, la más alta que llega a todo el tramo
        paso = PASADA_VELOCIDAD / HZ_CONTROL
        tramos = []
        for k, (a, b) in enumerate(pairwise(pts)):
            n = max(1, int(np.ceil(np.linalg.norm(b - a) / paso)))
            tramos.append([np.array([*(a + (b - a) * (j / n)), g.ALTURA_CARA_TABLA])
                           for j in range(0 if k == 0 else 1, n + 1)])
        # cada carril (tramos pares) con una sola inclinación, la más alta que llega a todo él; en los cambios de
        # carril la inclinación pasa poco a poco de la de un carril a la del siguiente (si no, la boca salta)
        incs = {}
        for k in range(0, len(tramos), 2):
            r = self.cin.trayectoria(tramos[k], LIMPIEZA_INC + RESPALDO_INC)
            if r is not None:
                incs[k] = r[1]
                if r[1] not in LIMPIEZA_INC:
                    self.fuera_de_especificacion.append((f"pasada final, carril {k // 2 + 1}", r[1]))
        self._pasada, self.inclinaciones_pasada = [], [incs.get(k) for k in range(0, len(tramos), 2)]
        q0 = None
        for k, tramo in enumerate(tramos):
            if k % 2 == 0:
                if k not in incs:
                    continue  # carril inalcanzable: lo salta
                por_punto = [incs[k]] * len(tramo)
            else:
                i0, i1 = incs.get(k - 1), incs.get(k + 1)
                if i0 is None or i1 is None:
                    continue
                por_punto = list(np.linspace(i0, i1, len(tramo)))
            r = self.cin.trayectoria(tramo, None, q0, por_punto)
            if r is not None:
                self._pasada += r[0]
                q0 = r[2]
        self._pasada_s = 0
        if not self._pasada:
            self._cambiar(Estado.APARCAR, "la pasada final no alcanza la madera")
            return
        self._cambiar(Estado.PASADA_FINAL, "pasada final pedida")

    def _pasada_final(self, escena: Escena) -> None:
        k = int(self._pasada_s)
        destino = self._pasada[min(k, len(self._pasada) - 1)]
        motivo = self._avanzar(destino)
        if motivo and self._frenado_demasiado(escena, motivo):
            return
        # avanza por el camino solo cuando la orden ha alcanzado (casi) el punto: así va a 40 mm/s como mucho
        if k == 0:
            if self._llegado(destino):
                self._pasada_s = 1
        elif np.max(np.abs(forzar_montaje(destino) - self.q)) < 3 * MAX_GRADOS_PASO:
            self._pasada_s += 1
        self.detalle = f"pasada final ({100 * k // len(self._pasada)} %)"
        if self._pasada_s >= len(self._pasada):
            self._cambiar(Estado.APARCAR, "fin de la pasada final")

    def _aparcar(self, escena: Escena) -> None:
        if self._pasada_pedida and not self.pendientes:
            self._empezar_pasada()
            return
        self._avanzar(L.APARCADO)
        self.detalle = "aparco"
        if self._llegado(L.APARCADO):
            self._q4 = None
            self._cambiar(Estado.APARCADO, "aparcado")


# --- escena desde la verdad de la simulación -----------------------------------------------------------------------
RADIO_ZONA_VIRUTA = 35.0  # círculo alrededor del agujero donde se cuenta la viruta (M3)
VENTANA_VELOCIDAD = 0.3  # s
QUIETO_MM_S = 5.0
APOYADA_MM = 3.0


class _Historial:
    def __init__(self):
        self.puntos: deque = deque()  # (t, xy del marcador)
        self.quieto_desde = None
        self.t = -1.0


_historiales: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()


def escena_verdad(mundo, t: float | None = None, agujeros=None) -> Escena:
    """`Escena` con la verdad de la simulación (sin visión). La viruta es el número de partículas sobre la madera a
    menos de RADIO_ZONA_VIRUTA de cada agujero; los agujeros son `agujeros` (marco de la madera, p. ej.
    `Ciclo.agujeros`) o, si no se dan, los que ha hecho el mundo. La velocidad del taladro se mide con lo visto en
    llamadas anteriores con el mismo mundo (llamar una vez por paso)."""
    from garbi.mundo import EN_TABLA

    t = mundo.t if t is None else t
    j = mundo.juez
    hist = _historiales.get(mundo)
    if hist is None or t < hist.t:
        hist = _historiales[mundo] = _Historial()
    hist.t = t
    taladro, broca = Taladro(visible=False), Broca()
    if j.taladro_visible:
        cuerpo = mundo.modelo.body("taladro").id
        R = mundo.datos.xmat[cuerpo].reshape(3, 3)
        punta = j.taladro_punta.copy()
        bola = punta + R[:, 2] * g.ALTURA_BOLA_SOBRE_PUNTA
        hist.puntos.append((t, bola[:2].copy()))
        while hist.puntos and t - hist.puntos[0][0] > VENTANA_VELOCIDAD + 1e-6:
            hist.puntos.popleft()
        t0, p0 = hist.puntos[0]
        velocidad = float(np.linalg.norm(bola[:2] - p0) / (t - t0)) if t > t0 else 0.0
        if velocidad < QUIETO_MM_S:
            hist.quieto_desde = t if hist.quieto_desde is None else hist.quieto_desde
        else:
            hist.quieto_desde = None
        r = float(np.hypot(*punta[:2]))
        en_zona = (j.tabla is not None and j.tabla.contiene(punta[:2], margen=-15.0)
                   and L.RADIO_TALADRO_MIN - 30 <= r <= L.RADIO_TALADRO_MAX + 20)
        taladro = Taladro(True, bola[:2].copy(), velocidad, hist.quieto_desde, en_zona,
                          agarrado=bool(getattr(j, "mano_en_taladro", True)))
        broca = Broca(punta, bool(punta[2] - g.ALTURA_CARA_TABLA <= APOYADA_MM), "muneca",
                      np.asarray(j.taladro_eje, float).copy())
    else:
        hist.puntos.clear()
        hist.quieto_desde = None
    viruta = {}
    lista = j.agujeros if agujeros is None else agujeros
    sel = j.viruta_donde == EN_TABLA
    for i, h in enumerate(lista):
        d = np.linalg.norm(j.viruta_pos[sel] - np.asarray(h, float)[None, :2], axis=1)
        viruta[i] = int(np.sum(d <= RADIO_ZONA_VIRUTA))
    return Escena(t=t, madera=j.tabla, taladro=taladro, broca=broca, viruta=viruta, manos=manos_verdad(mundo))


def en_tapete(xy, margen: float = 0.0) -> bool:
    """¿El punto (x, y en la mesa) está sobre el tapete (la alfombrilla)?"""
    cx, cy = g.ALFOMBRILLA_CENTRO
    return (abs(float(xy[0]) - cx) <= g.ALFOMBRILLA_TAMANO[0] / 2 + margen
            and abs(float(xy[1]) - cy) <= g.ALFOMBRILLA_TAMANO[1] / 2 + margen)


def manos_verdad(mundo) -> list[Mano]:
    """Las manos de la simulación: la que sujeta el taladro (si está agarrado) y la otra (si está en la escena)."""
    manos = []
    mano_taladro = mundo.mano_taladro_en_mesa() if hasattr(mundo, "mano_taladro_en_mesa") else None
    if mano_taladro is not None:
        manos.append(Mano(mano_taladro[:2].copy(), en_tapete(mano_taladro[:2]), fuente="verdad"))
    libre = getattr(mundo.juez, "mano_libre", None)
    if libre is not None:
        manos.append(Mano(np.asarray(libre, float)[:2].copy(), en_tapete(libre[:2]), fuente="verdad"))
    return manos
