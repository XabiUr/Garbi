"""Orquestador de Garbi: un solo proceso que manda en el robot, en un bucle de 30 Hz.

Máquina de estados (lo programado, rápido y seguro) que usa dos piezas intercambiables:
- **Percepción** (`Percepcion`): dónde está la tabla, si hay taladro y dónde apunta, dónde está la viruta nueva.
  En simulación hay una versión «oráculo» (lee el mundo) y otra por visión (`garbi.vision`).
- **Habilidades de limpieza** (`Habilidad`): la línea base programada (zigzag sobre el punto que da la percepción) o
  el VLA (una política de LeRobot que recibe la frase y las cámaras).

Regla de seguridad: el robot no se mueve mientras el taladro está en la zona de trabajo, salvo para acercarse a él
cuando está quieto; mientras se taladra está congelado. Si el Arduino deja de responder, se congela.

Estados: APARCADO → ACERCARSE (al preapunto, con la punta que da la cámara de arriba) → APUNTAR (la cámara del robot
mide la punta y la boca entra hasta acompañar) → ACOMPANAR (quieto junto a la broca, aspiradora encendida) →
ESPERAR (taladro retirado, aspira 2 s más) → LIMPIAR (habilidad) → APARCAR → APARCADO. Las órdenes de voz o botón (`ordenar`) entran
por una cola y mandan sobre el ciclo.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol

import numpy as np

from garbi import contrato as g
from garbi.arduino import ArduinoVirtual, EnlaceArduino
from garbi.control import ControlBoca
from garbi.mundo import APARCADO, EN_ALFOMBRILLA, EN_TABLA, MundoGarbi


TEMBLOR_QUIETO = 6.0  # mm que puede variar la punta vista desde arriba sin que cuente como movimiento (el brazo tapa
# a veces parte de la bola al pasar)
MOVIMIENTO_REPLANIFICAR = 15.0  # mm: si la punta vista desde arriba se va más, el taladro se ha movido de verdad
FOTOGRAMAS_FILTRO = 9  # mediana de la punta vista desde arriba en los últimos fotogramas
# Si mueves el taladro cuando Garbi ya está acompañando:
MOVIMIENTO_APARTARSE = 15.0  # mm (vista de arriba): se aparta, espera a que pare y vuelve a apuntar
CORRECCION_MIN = 4.0  # mm (cámara del robot): por debajo no se corrige (vibración, ruido)
CADA_REVISION = 0.5  # s entre revisiones de la broca con la cámara del robot al acompañar
APARTARSE = 40.0  # mm que se aparta en planta (contra la dirección de la boca), y 15 mm hacia arriba


class Estado(str, Enum):
    APARCADO = "aparcado"
    ACERCARSE = "acercarse"
    APUNTAR = "apuntar"
    ACOMPANAR = "acompañar"
    ESPERAR = "esperar"
    LIMPIAR = "limpiar"
    APARCAR = "aparcar"
    CONGELADO = "congelado"


# --- percepción ---------------------------------------------------------------------------------------------------
@dataclass
class VistaTaladro:
    visible: bool
    punta: np.ndarray | None = None  # mm, marco de la mesa


class Percepcion(Protocol):
    def tabla(self) -> g.PoseTabla | None: ...
    def broca_robot(self, aprox=None) -> np.ndarray | None: ...  # punta vista por la cámara del robot (el apunto)
    def taladro(self) -> VistaTaladro: ...
    def viruta(self, donde: str) -> np.ndarray: ...  # puntos (mm, mesa) de la viruta «tabla» o «alfombrilla»


class PercepcionOraculo:
    """Lee la verdad del mundo simulado (para depurar la lógica sin depender de la visión)."""

    def __init__(self, mundo: MundoGarbi):
        self.m = mundo

    def tabla(self):
        return self.m.juez.tabla

    def taladro(self):
        j = self.m.juez
        return VistaTaladro(j.taladro_visible, j.taladro_punta.copy() if j.taladro_visible else None)

    def broca_robot(self, aprox=None):
        j = self.m.juez
        return j.taladro_punta.copy() if j.taladro_visible else None

    def viruta(self, donde: str):
        pts = self.m.viruta_en_mesa(EN_TABLA if donde == "tabla" else EN_ALFOMBRILLA)
        return pts[:, :2]


# --- habilidades de limpieza ---------------------------------------------------------------------------------------
class Habilidad(Protocol):
    nombre: str

    def empezar(self, orden: str, q: np.ndarray, percepcion: Percepcion) -> None: ...
    def accion(self, q: np.ndarray, obs: dict) -> np.ndarray | None: ...  # None = terminado


class LineaBase:
    """Línea base programada: zigzag sobre el centro del montón de viruta que da la percepción (sin aprendizaje)."""

    nombre = "línea base programada"

    def __init__(self, ctl: ControlBoca, lado: int = 1):
        self.ctl = ctl
        self.lado = lado  # lo fija el orquestador antes de empezar
        self.plan: deque = deque()

    def empezar(self, orden, q, percepcion):
        donde = "alfombrilla" if orden == g.ORDEN_ALFOMBRILLA else "tabla"
        pts = percepcion.viruta(donde)
        self.plan = deque()
        if len(pts) == 0:
            return
        centro = np.median(pts, axis=0)
        radio = float(np.clip(np.percentile(np.linalg.norm(pts - centro, axis=1), 90) + 4, 10, 30))
        z = g.ALTURA_CARA_TABLA if donde == "tabla" else g.ALFOMBRILLA_GROSOR
        self.plan = deque(self.ctl.zigzag(q, centro, radio=radio, z=z, lado=self.lado))

    def accion(self, q, obs):
        return self.plan.popleft() if self.plan else None


# --- orquestador ---------------------------------------------------------------------------------------------------
@dataclass
class Registro:
    t: float
    estado: str
    texto: str


@dataclass
class RobotVivo:
    mundo: MundoGarbi
    percepcion: Percepcion
    habilidad: Habilidad
    enlace: EnlaceArduino = field(default_factory=lambda: EnlaceArduino(ArduinoVirtual()))
    lado: int = 1  # la boca llega por la izquierda (+1) o la derecha (-1) del punto de trabajo; «otro lado» lo cambia

    def __post_init__(self):
        self.ctl = ControlBoca(self.mundo.cin)
        self.estado = Estado.APARCADO
        self.plan: deque = deque()
        self.q_obj = np.asarray(APARCADO, float)
        self.ordenes: deque = deque()
        self.registro: list[Registro] = []
        self.orden_activa: str | None = None
        self._punta_previa: np.ndarray | None = None
        self._quieto_desde = 0.0
        self._esperar_hasta = 0.0
        self._estado_antes_congelar: Estado | None = None
        self._objetivo: np.ndarray | None = None  # punta hacia la que va el preapunto
        self.punta_medida: np.ndarray | None = None  # punta que midió la cámara del robot
        self._intentos_apunto = 0
        self._sin_broca = False  # no la ve ni separándose: espera a que se mueva el taladro
        self.holgura_plan = float("nan")  # mm entre el brazo y el taladro en el último acercamiento planeado
        self._puntas: deque = deque(maxlen=FOTOGRAMAS_FILTRO)
        self._avisado_fuera = False
        self._arriba_al_llegar = np.zeros(3)
        self._proxima_revision = 0.0
        self._apartandose = False
        self._arriba_al_llegar = np.zeros(3)
        self._proxima_revision = 0.0
        self._apartandose = False

    # --- entrada --------------------------------------------------------------------------------------------
    def ordenar(self, orden: str) -> None:
        """Órdenes: «ven», «retírate», «otro lado», `ORDEN_AGUJERO`, `ORDEN_ALFOMBRILLA`, «limpia la tabla»."""
        self.ordenes.append(orden)

    def _log(self, texto: str) -> None:
        self.registro.append(Registro(round(self.mundo.t, 2), self.estado.value, texto))

    def _cambiar(self, estado: Estado, texto: str = "") -> None:
        self.estado = estado
        self._log(texto or f"→ {estado.value}")

    def _aspiradora(self, on: bool) -> None:
        if self.enlace.aspiradora_encendida != on:
            self.enlace.aspiradora(on, self.mundo.t)
            self._log("aspiradora " + ("encendida" if on else "apagada"))
        self.mundo.aspiradora = self.enlace.aspiradora_encendida

    # --- un fotograma -----------------------------------------------------------------------------------------
    def tick(self) -> dict:
        t = self.mundo.t
        q = self.mundo.estado()
        self.enlace.latido(t)
        if not self.enlace.sano:
            if self.estado != Estado.CONGELADO:
                self._estado_antes_congelar = self.estado
                self._cambiar(Estado.CONGELADO, "el Arduino no responde: congelado")
            self.mundo.aspiradora = False
            return self.mundo.step(self.q_obj, observar=False)

        vista = self._filtrar(self.percepcion.taladro())
        quieto = self._taladro_quieto(vista, t)
        self._atender_ordenes(q, vista)

        if self.estado == Estado.APARCADO:
            if vista.visible and quieto and self._en_zona(vista.punta):
                self._ir_al_preapunto(q, vista.punta, "taladro quieto en la zona: me acerco")
            elif vista.visible and quieto and not self._avisado_fuera:
                self._avisado_fuera = True
                self._log("el taladro está fuera de mi alcance: no me acerco")
            elif not vista.visible:
                self._avisado_fuera = False
        elif self.estado == Estado.ACERCARSE:
            if self._apartandose and not self.plan:
                self._apartandose = False
            if vista.visible and not quieto and not self._apartandose:
                self.plan.clear()  # el taladro se mueve: me quedo quieto hasta que pare
                self._sin_broca = False
            if not self.plan and not self._sin_broca:
                if vista.visible and quieto:
                    destino, _ = self.ctl.preapunto(self._objetivo, self.lado)
                    if np.linalg.norm(vista.punta[:2] - self._objetivo[:2]) > MOVIMIENTO_REPLANIFICAR:
                        self._ir_al_preapunto(q, vista.punta, "el taladro se ha movido: voy al sitio nuevo")
                    elif np.linalg.norm(self.ctl.boca(q) - destino) > 6:
                        self._ir_al_preapunto(q, self._objetivo, "sigo hacia el taladro", solo_este_lado=True)
                    else:
                        self._apuntar(q, vista.punta)
            if not self.plan:
                if not vista.visible:
                    self._planear(self.ctl.aparcar(q))
                    self._cambiar(Estado.APARCAR, "el taladro se fue antes de llegar")
        elif self.estado == Estado.APUNTAR:
            if vista.visible and not quieto:
                self.plan.clear()
                self._ir_al_preapunto(q, vista.punta, "el taladro se ha movido: vuelvo a apuntar")
            elif not vista.visible:
                self._planear(self.ctl.aparcar(q))
                self._cambiar(Estado.APARCAR, "el taladro se fue antes de llegar")
            elif not self.plan:
                self._aspiradora(True)
                self._arriba_al_llegar = np.asarray(vista.punta, float).copy()
                self._proxima_revision = t + CADA_REVISION
                self._cambiar(Estado.ACOMPANAR, "colocado junto a la broca: listo para taladrar")
        elif self.estado == Estado.ACOMPANAR:
            if not vista.visible:
                self._esperar_hasta = t + g.ASPIRAR_TRAS_RETIRADA
                self._cambiar(Estado.ESPERAR, "taladro retirado: aspiro un poco más")
            elif np.linalg.norm(vista.punta[:2] - self._arriba_al_llegar[:2]) > MOVIMIENTO_APARTARSE:
                self._apartarse(q, "el taladro se ha movido: me aparto y vuelvo a apuntar")
            elif quieto and t >= self._proxima_revision:
                self._proxima_revision = t + CADA_REVISION
                self._revisar_broca(q)
        elif self.estado == Estado.ESPERAR:
            if t >= self._esperar_hasta:
                self._empezar_limpieza(g.ORDEN_AGUJERO, q)
        elif self.estado == Estado.LIMPIAR:
            obs = self.mundo.observacion() if self.mundo.render else {"observation.state": q}
            a = self.habilidad.accion(q, obs)
            if a is None:
                self._aspiradora(False)
                self._planear(self.ctl.aparcar(q))
                self._cambiar(Estado.APARCAR, f"limpieza terminada ({self.habilidad.nombre})")
            else:
                self.q_obj = np.asarray(a, float)
        elif self.estado == Estado.APARCAR:
            if not self.plan:
                self._aspiradora(False)
                self._cambiar(Estado.APARCADO, "aparcado")

        if self.plan:
            self.q_obj = self.plan.popleft()
        return self.mundo.step(self.q_obj, observar=False)

    # --- ayudas -----------------------------------------------------------------------------------------------
    def _planear(self, plan) -> None:
        self.plan = deque(plan)

    def _ir_al_preapunto(self, q, punta, texto: str, solo_este_lado: bool = False) -> None:
        if not solo_este_lado:
            self._intentos_apunto = 0
        self._sin_broca = False
        self._objetivo = np.asarray(punta, float).copy()
        plan, lado, holgura = self.ctl.acercarse_al_taladro(q, self._objetivo, self.lado, solo_este_lado)
        if lado != self.lado:
            texto += " (por el otro lado: por este no paso lejos del taladro)"
            self.lado = lado
        self.holgura_plan = holgura
        self._planear(plan)
        self._cambiar(Estado.ACERCARSE, texto)

    def _apuntar(self, q, punta_arriba) -> None:
        """El apunto: la cámara del robot mide la punta y la boca entra hasta acompañar. Si no la ve, la mira
        desde el otro lado; si sigue sin verla, no se acerca a ciegas: espera a que se enderece o se mueva el taladro."""
        fina = self.percepcion.broca_robot(punta_arriba) if hasattr(self.percepcion, "broca_robot") else None
        if fina is None or np.linalg.norm(fina[:2] - punta_arriba[:2]) > 50:
            if self._intentos_apunto == 0:
                self._intentos_apunto = 1
                self.lado = -self.lado
                self._ir_al_preapunto(q, punta_arriba, "no veo la broca: la miro desde el otro lado",
                                      solo_este_lado=True)
            else:
                self._sin_broca = True
                self._cambiar(Estado.ACERCARSE, "no veo la broca: ¿pones el taladro más recto?")
            return
        self.punta_medida = np.asarray(fina, float)
        corr = np.linalg.norm(fina[:2] - punta_arriba[:2])
        self._planear(self.ctl.afinar(q, self.punta_medida, self.lado))
        self._cambiar(Estado.APUNTAR, f"veo la broca: corrijo {corr:.0f} mm y me coloco")

    def _empezar_limpieza(self, orden: str, q) -> None:
        self.orden_activa = orden
        self._aspiradora(True)
        refrescar = getattr(self.percepcion, "refrescar", None)
        if refrescar is not None:  # decidir con una imagen de ahora, no con la última analizada
            refrescar()
        if hasattr(self.habilidad, "lado"):
            self.habilidad.lado = self.lado
        self.habilidad.empezar(orden, q, self.percepcion)
        self._cambiar(Estado.LIMPIAR, f"«{orden}»")

    def _en_zona(self, p) -> bool:
        r = float(np.linalg.norm(np.asarray(p)[:2]))
        return g.RADIO_TRABAJO_MIN <= r <= g.RADIO_TRABAJO_MAX

    def _revisar_broca(self, q) -> None:
        """Al acompañar, la cámara del robot vuelve a mirar la broca; si se ha desplazado un poco (recolocar antes de
        taladrar), Garbi se corrige despacio. Con la broca dentro de la madera no se mueve en lateral: no hay
        correcciones mientras se taladra."""
        fina = self.percepcion.broca_robot(self.punta_medida) if hasattr(self.percepcion, "broca_robot") else None
        if fina is None:
            return
        desvio = float(np.linalg.norm(fina[:2] - self.punta_medida[:2]))
        if CORRECCION_MIN < desvio <= MOVIMIENTO_APARTARSE:
            self.punta_medida = np.asarray(fina, float)
            self._planear(self.ctl.afinar(q, self.punta_medida, self.lado))
            self._cambiar(Estado.APUNTAR, f"la broca se ha movido {desvio:.0f} mm: me recoloco")

    def _apartarse(self, q, texto: str) -> None:
        """Se aparta enseguida (atrás y arriba, lejos de la broca) y espera a que el taladro vuelva a estar quieto."""
        e = self.ctl.eje(q)
        planta = np.array([e[0], e[1], 0.0]) / (np.hypot(e[0], e[1]) or 1.0)
        destino = self.ctl.boca(q) - planta * APARTARSE + np.array([0.0, 0.0, 15.0])
        self._planear(self.ctl.linea(q, destino, e, velocidad=g.VELOCIDAD_MAX_BOCA))
        self._intentos_apunto = 0
        self._apartandose = True  # este plan no se corta aunque el taladro se siga moviendo
        self._cambiar(Estado.ACERCARSE, texto)

    def _filtrar(self, vista: VistaTaladro) -> VistaTaladro:
        """Mediana de la punta vista desde arriba en los últimos fotogramas (quita los saltos de cuando el brazo tapa
        parte de la bola)."""
        if not vista.visible:
            self._puntas.clear()
            return vista
        self._puntas.append(np.asarray(vista.punta, float))
        return VistaTaladro(True, np.median(np.array(self._puntas), axis=0))

    def _taladro_quieto(self, vista: VistaTaladro, t: float) -> bool:
        if not vista.visible:
            self._punta_previa = None
            return False
        if self._punta_previa is None or np.linalg.norm(vista.punta - self._punta_previa) > TEMBLOR_QUIETO:
            self._quieto_desde = t
        self._punta_previa = vista.punta.copy()
        return t - self._quieto_desde >= 0.5

    def _atender_ordenes(self, q, vista) -> None:
        while self.ordenes:
            orden = self.ordenes.popleft()
            self._log(f"orden: {orden}")
            if orden == "retírate":
                self.plan.clear()
                self._planear(self.ctl.aparcar(q, alejarse=80.0 if vista.visible else 0.0))
                self._cambiar(Estado.APARCAR, "me retiro")
            elif orden == "otro lado":
                self.lado = -self.lado
                if self.estado in (Estado.ACOMPANAR, Estado.ACERCARSE, Estado.APUNTAR) and vista.visible:
                    self._ir_al_preapunto(q, vista.punta, "cambio de lado")
            elif orden == "ven" and vista.visible:
                self._ir_al_preapunto(q, vista.punta, "voy")
            elif orden in g.ORDENES_VLA and not vista.visible:
                self.plan.clear()
                self._empezar_limpieza(orden, q)
            elif orden == "limpia la tabla" and not vista.visible and self.percepcion.tabla() is not None:
                self._aspiradora(True)
                barrido = self.ctl.limpiar_tabla(q, self.percepcion.tabla(), self.lado)
                self._planear(barrido + self.ctl.aparcar(barrido[-1]))
                self._cambiar(Estado.APARCAR, "limpio la tabla entera")
