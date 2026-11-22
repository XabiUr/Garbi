"""Programa principal de Garbi: bucle de control a 30 Hz, en la simulación o con el robot real.

    python -m garbi.correr --sim                       # simulación con percepción por imágenes (640 × 480) y un juez
    python -m garbi.correr --sim --verdad              # la Escena sale de la verdad de la simulación (sin visión)
    python -m garbi.correr --sim --grabar datos/ciclo  # además, cada LIMPIAR limpio se guarda como episodio (M5)
    python -m garbi.correr --real --puerto /dev/ttyACM0 --aspiradora /dev/ttyUSB0 --top 0 --wrist 2

En cada paso: imágenes → percepción → ciclo → cuerpo (y registro). Ctrl+C (o SIGTERM) para limpio: aspiradora a 0
y el brazo quieto donde está.

Piezas (T1-T4)
--------------
- `garbi.percepcion.Percepcion(cinematica=CinematicaRobot(modelo))`: `calibrar(img_top)` con el tapete (M2 paso 2) y
  `leer(imagenes, q, t, agujeros)` → `Escena`. La pose de la base del robot sale del anillo verde
  (`garbi.calibracion.calibrar_robot`, M2 paso 3) y da la pose de la cámara de la muñeca con la cinemática.
  `LectorEscena` la llama a `HZ_PERCEPCION` (15 Hz) dentro del bucle de 30 Hz y cuenta la viruta en los agujeros del
  ciclo (así los índices de `Escena.viruta` son los de `Ciclo.agujeros`).
- `garbi.ciclo.Ciclo(control, habilidad, umbral_viruta=..., umbral_fraccion=...)`: con la percepción decide «limpio»
  con la fracción del círculo (`Escena.viruta_fraccion` < 2 %); con la verdad, con las partículas (≤ 2).
- `garbi.habilidad.HabilidadEspiral(control)` («programada», por defecto) o `HabilidadACT(modelo)` («act»).
- `garbi.real.CuerpoSim` / `CuerpoReal`.

En la simulación, `JuezSim` hace de persona (5 agujeros en sitios alcanzables y la pasada final) y mide lo que la
percepción no sabe: aciertos (agujero limpio con la verdad y sin contacto), holgura y borde mínimos con la postura
real, duración por ciclo y fallos de percepción (broca apoyada no vista, apoyos falsos). En el robot real,
`ControlLateral` usa un `MundoGarbi(render=False)` solo como modelo cinemático.
"""
from __future__ import annotations

import argparse
import dataclasses
import logging
import signal
import time
from collections.abc import Callable

import numpy as np

from garbi import contrato as g
from garbi.registro import CARPETA, DetectorCiclos, RegistroCiclos, RerunOpcional
from garbi.tipos import HZ_CONTROL, HZ_PERCEPCION, UMBRAL_FRACCION_VIRUTA, UMBRAL_PARTICULAS_VIRUTA, Escena

log = logging.getLogger("garbi")

# Sitios del juez (marco de la madera, mm): repartidos por la zona donde funciona el ciclo completo con la percepción
# (medida en T6: madera en x local -40…+40, es decir, a 320-420 mm del eje del robot; también la mitad lejana, a
# 45-55°). Más cerca del robot (x local -80, r < 300 mm) el taladro de la persona entra por donde está el brazo.
SITIOS_JUEZ = [(-20.0, 40.0), (-40.0, -30.0), (0.0, -80.0), (45.0, 20.0), (-20.0, 110.0)]


# --- percepción dentro del bucle -----------------------------------------------------------------------------------
class LectorEscena:
    """`Percepcion` a `hz` dentro del bucle de control: entre lecturas devuelve la última `Escena` con el t actual.
    `fuente_imagenes()` da las imágenes cuando el bucle no las trae (así solo se renderiza a 15 Hz).
    `agujeros()` da los agujeros del ciclo (marco de la madera) para contar su viruta."""

    def __init__(self, percepcion, fuente_imagenes: Callable[[], dict] | None = None,
                 agujeros: Callable[[], list] | None = None, hz: float = HZ_PERCEPCION):
        self.percepcion = percepcion
        self.fuente_imagenes = fuente_imagenes
        self.agujeros = agujeros
        self.periodo = 1.0 / hz
        self.ultima: Escena | None = None
        self._t_lectura = -np.inf
        self.lecturas = 0
        self.imagenes: dict = {}  # las de la última lectura

    def __call__(self, imagenes, q, t) -> Escena:
        if self.ultima is not None and t - self._t_lectura < self.periodo - 1e-6:
            return dataclasses.replace(self.ultima, t=t)
        if not imagenes and self.fuente_imagenes is not None:
            imagenes = self.fuente_imagenes()
        self.imagenes = imagenes
        agujeros = None if self.agujeros is None else list(self.agujeros())
        self.ultima = self.percepcion.leer(imagenes, q, t, agujeros=agujeros)
        self._t_lectura = t
        self.lecturas += 1
        return self.ultima


def crear_percepcion(modelo, manos: str = "color"):
    """`Percepcion` con la cinemática del brazo (modelo MuJoCo del montaje lateral) para la cámara de la muñeca.
    `manos`: "color" (simulación), "mediapipe" o "auto" (robot real: MediaPipe si está, si no color)."""
    from garbi.calibracion import CinematicaRobot
    from garbi.percepcion import Percepcion

    return Percepcion(cinematica=CinematicaRobot(modelo), manos=manos)


def crear_percepcion_real(modelo, carpeta_calibracion="calib", config_vision=None, manos: str = "auto"):
    """`Percepcion` para el robot real con lo que haya en `calib/` (herramientas/garbi_calibrar.py): intrínsecas de
    `top.yaml` y `wrist.yaml` y la base del robot de `robot.yaml` (si no, la base en el origen: plantilla impresa).
    Los umbrales salen de `garbi/config_vision.yaml` (herramientas/garbi_ajustar_color.py), o de `config_vision`."""
    from garbi.calibracion import CinematicaRobot
    from garbi.config_vision import aplicar_a_percepcion, cargar_config_vision
    from garbi.percepcion import Percepcion
    from garbi.real import cargar_calibracion

    aplicados = aplicar_a_percepcion(cargar_config_vision(config_vision))
    calib = cargar_calibracion(carpeta_calibracion)
    log.info("calibración de %s: intrínsecas %s · base %s · umbrales %s", carpeta_calibracion,
             sorted(calib.intrinsecas) or "nominales", calib.base or "en el origen", aplicados)
    # manos: MediaPipe si está instalado y con su modelo (calib/hand_landmarker.task); si no, color de piel
    return Percepcion(K_top=calib.K("top"), K_wrist=calib.K("wrist"),
                      cinematica=CinematicaRobot(modelo, calib.base), config=config_vision, manos=manos)


def calibrar_sim(mundo, percepcion, resolucion=(640, 480)):
    """M2 en la simulación: la cámara de arriba con el tapete y la base del robot con el anillo verde (9 posturas y 5
    de comprobación). El robot vuelve después a donde estaba. Devuelve el `ResultadoCalibracion`."""
    from garbi.calibracion import calibrar_robot

    q_antes = mundo.estado().copy()
    if not percepcion.calibrar(mundo.imagen("top", resolucion)):
        raise RuntimeError("no veo las 4 esquinas del tapete")

    def ir_y_mirar(q):
        mundo.reset_robot(q)
        return mundo.imagen("top", resolucion)

    r = calibrar_robot(ir_y_mirar, percepcion.cam, percepcion.cin)
    mundo.reset_robot(q_antes)
    if r is None or not r.ok:
        raise RuntimeError(f"calibración del robot con el anillo verde fallida: {r}")
    log.info("calibración: base del robot en (%.1f, %.1f) mm, %.2f° · error de comprobación máx %.1f mm",
             r.base.x, r.base.y, r.base.giro, float(np.max(r.errores)))
    return r


def crear_ciclo(control, habilidad: str = "programada", modelo: str | None = None, con_percepcion: bool = True):
    from garbi.ciclo import Ciclo
    from garbi.habilidad import HabilidadACT, HabilidadEspiral

    respaldo = HabilidadEspiral(control)
    if habilidad == "act":
        if not modelo:
            raise SystemExit("--habilidad act necesita --modelo (carpeta o repo de Hugging Face)")
        paso7 = HabilidadACT(modelo)
    else:
        paso7, respaldo = respaldo, None
    # umbrales de «limpio» explícitos: fracción del círculo (percepción por píxeles) o partículas (verdad)
    return Ciclo(control, paso7, respaldo=respaldo, umbral_viruta=UMBRAL_PARTICULAS_VIRUTA,
                 umbral_fraccion=UMBRAL_FRACCION_VIRUTA)


# --- simulación: el juez ---------------------------------------------------------------------------------------------
@dataclasses.dataclass
class ResultadoAgujero:
    sitio: tuple  # marco de la madera
    t_inicio: float
    duracion: float = 0.0  # s, desde que entra el taladro hasta que Garbi vuelve a aparcar
    viruta_restante: int = -1  # partículas (verdad) a < 35 mm del agujero al acabar
    contactos: int = 0  # pasos con el brazo tocando algo (MuJoCo)
    holgura_min: float = np.inf  # mm, con la postura real
    borde_min: float = np.inf
    apoyo_visto: bool = False  # la percepción vio la broca apoyada mientras lo estaba
    apoyos_falsos: int = 0  # lecturas «apoyada» con la broca en el aire (> 8 mm)
    broca_vista: int = 0  # lecturas con la punta medida por la muñeca (con el taladro visible)
    lecturas_taladro: int = 0
    agujero_apuntado: bool = False  # el ciclo apuntó un agujero a < 3 mm del de verdad
    holgura_donde: str = ""  # estado del ciclo y fase del juez en la holgura mínima
    borde_donde: str = ""
    falsos_donde: list = dataclasses.field(default_factory=list)  # (fase del juez, altura) de los apoyos falsos

    @property
    def acierto(self) -> bool:
        return self.viruta_restante >= 0 and self.viruta_restante <= UMBRAL_PARTICULAS_VIRUTA and self.contactos == 0


class JuezSim:
    """La persona simulada y el juez. Por cada sitio, espera a que Garbi esté aparcado; entra con el taladro en el
    aire, busca, lo deja quieto sobre el punto, apoya la broca, taladra, la levanta y sale. Al acabar los sitios pide
    la pasada final. Mide cada agujero (`ResultadoAgujero`) con la verdad de la simulación. Tiempos en s, como el guion
    de `tests/test_garbi_ciclo.py`."""

    AIRE = 50.0  # mm de la punta sobre la madera mientras se mueve
    FASES = (("entra", 2.5), ("busca", 2.0), ("acerca", 1.5), ("apoya", 0.6), ("quieto", 1.0), ("taladra", 6.0),
             ("levanta", 0.5), ("sale", 1.8))
    ESPERA_MAX = 60.0  # s esperando a que Garbi aparque antes de dar el agujero por perdido

    def __init__(self, mundo, ciclo, sitios=None, control=None, pasada_final: bool = True):
        self.m = mundo
        self.ciclo = ciclo
        self.sitios = list(SITIOS_JUEZ if sitios is None else sitios)
        self.control = control if control is not None else ciclo.control
        self.pasada = pasada_final
        self.resultados: list[ResultadoAgujero] = []
        self.t_pasada: float | None = None
        self.duracion_pasada = 0.0
        self.contactos_pasada = 0
        self.holgura_min = np.inf
        self.borde_min = np.inf
        self._k = 0  # sitio actual
        self._fase = "espera"
        self._t_fase = 0.0
        self._actual: ResultadoAgujero | None = None
        self._fin = False
        self._t0_reposo = 2.0  # deja 2 s de reposo al principio
        self._geoms_brazo = set(getattr(self.control, "_g_brazo", []))

    @property
    def terminado(self) -> bool:
        return self._fin

    def _aparcado(self) -> bool:
        return self.ciclo.estado.value == "aparcado"

    def _taladro(self, xy, alto):
        self.m.poner_taladro(xy[0], xy[1], g.ALTURA_CARA_TABLA + alto)

    def contactos(self) -> int:
        """Contactos del brazo con cualquier otra cosa en el paso actual (MuJoCo)."""
        d = self.m.datos
        n = 0
        for i in range(d.ncon):
            c = d.contact[i]
            if c.dist < 0 and ((c.geom1 in self._geoms_brazo) != (c.geom2 in self._geoms_brazo)):
                n += 1
        return n

    def paso(self, t: float) -> None:
        """Antes de cada paso del bucle: mueve el taladro según el guion."""
        if self._fin:
            return
        if self._fase == "espera":
            if t < self._t0_reposo or not self._aparcado():
                if self._actual is not None and t - self._t_fase > self.ESPERA_MAX:
                    self._cerrar(t)  # no aparca: se da por perdido
                return
            if self._actual is not None:
                self._cerrar(t)
            if self._k < len(self.sitios):
                self._empezar(t)
            elif self.pasada and self.t_pasada is None:
                self.ciclo.pasada_final()
                self.t_pasada = t
                self._fase = "pasada"
            else:
                self._fin = True
            return
        if self._fase == "pasada":
            if t - self.t_pasada > 1.0 and self._aparcado():
                self.duracion_pasada = t - self.t_pasada
                self._fin = True
            return
        self._guion(t)

    def _empezar(self, t):
        sitio = self.sitios[self._k]
        self._k += 1
        self._actual = ResultadoAgujero(sitio=tuple(sitio), t_inicio=t)
        self._a = self.m.juez.tabla.a_mesa(np.array(sitio, float))
        self._entrada = np.array([g.PERSONA_X + 60, self._a[1]])
        self._fase, self._t_fase = "entra", t
        self._taladrado = False
        self._guion(t)

    def _guion(self, t):
        a, A = self._a, self.AIRE
        s = t - self._t_fase
        durs = dict(self.FASES)
        while s >= durs[self._fase]:
            s -= durs[self._fase]
            self._t_fase += durs[self._fase]
            nombres = [f for f, _ in self.FASES]
            i = nombres.index(self._fase) + 1
            if i == len(nombres):
                self.m.quitar_taladro()
                self._fase = "espera"
                return
            self._fase = nombres[i]
        f = 0.5 - 0.5 * np.cos(np.pi * min(1.0, s / durs[self._fase]))
        tramos = {"entra": (self._entrada, a + [40, 30], A + 60, A), "busca": (a + [40, 30], a + [-20, -30], A, A),
                  "acerca": (a + [-20, -30], a, A, A), "apoya": (a, a, A, 0.0), "quieto": (a, a, 0.0, 0.0),
                  "taladra": (a, a, 0.0, 0.0), "levanta": (a, a, 0.0, A), "sale": (a, self._entrada, A, A + 60)}
        p0, p1, z0, z1 = tramos[self._fase]
        xy = np.asarray(p0, float) + (np.asarray(p1, float) - np.asarray(p0, float)) * f
        self._taladro(xy, z0 + (z1 - z0) * f)
        if self._fase == "taladra" and not self._taladrado:
            self.m.taladrar()
            self._taladrado = True

    def _cerrar(self, t):
        r = self._actual
        r.duracion = t - r.t_inicio
        tabla = self.m.juez.tabla
        r.viruta_restante = self.m.viruta_alrededor(np.array(r.sitio, float), 35.0)
        verdad = tabla.a_mesa(np.array(r.sitio, float))
        r.agujero_apuntado = any(np.linalg.norm(self.ciclo.agujero_en_mesa(i)[:2] - verdad) < 3.0
                                 for i in range(len(self.ciclo.agujeros)))
        log.info("agujero %d en %s: %s · %.1f s · viruta %d · holgura %.1f · borde %.1f · contactos %d · apoyo visto %s"
                 " · apoyos falsos %d · broca vista %d/%d", len(self.resultados) + 1, tuple(round(v) for v in
                 tabla.a_mesa(np.array(r.sitio))), "acierto" if r.acierto else "FALLO", r.duracion,
                 r.viruta_restante, r.holgura_min, r.borde_min, r.contactos, r.apoyo_visto, r.apoyos_falsos,
                 r.broca_vista, r.lecturas_taladro)
        self.resultados.append(r)
        self._actual = None

    def medir(self, escena: Escena | None = None, nueva_lectura: bool = True) -> None:
        """Después de cada paso del bucle: holgura, borde y contactos con la postura real; fallos de percepción."""
        from garbi.ciclo import _lr_a_q4

        q4 = _lr_a_q4(self.m.estado())
        borde = self.ciclo.borde(q4)
        self.borde_min = min(self.borde_min, borde)
        holgura = np.inf
        if self.m.juez.taladro_visible:
            holgura = self.control.holgura(q4, self.m.juez.taladro_punta, self.m.juez.taladro_eje)
            self.holgura_min = min(self.holgura_min, holgura)
        # contacto: MuJoCo (el brazo con la escena) o la geometría (el taladro no choca en MuJoCo con el brazo)
        contactos = self.contactos() + int(holgura < 0.0)
        if self._fase == "pasada":
            self.contactos_pasada += bool(contactos)
        r = self._actual
        if r is None:
            return
        if borde < r.borde_min:
            r.borde_min = borde
            r.borde_donde = f"{self.ciclo.estado.value}/{self._fase}"
        if holgura < r.holgura_min:
            r.holgura_min = holgura
            r.holgura_donde = f"{self.ciclo.estado.value}/{self._fase}"
        r.contactos += bool(contactos)
        if escena is None or not nueva_lectura or not self.m.juez.taladro_visible:
            return
        r.lecturas_taladro += 1
        altura = float(self.m.juez.taladro_punta[2] - g.ALTURA_CARA_TABLA)
        if escena.broca.fuente == "muneca":
            r.broca_vista += 1
        if escena.broca.apoyada and altura <= 1.0:
            r.apoyo_visto = True
        if escena.broca.apoyada and altura > 8.0:
            r.apoyos_falsos += 1
            r.falsos_donde.append((self._fase, round(altura), escena.broca.fuente))

    def resumen(self) -> dict:
        rs = self.resultados
        return {
            "aciertos": sum(r.acierto for r in rs), "agujeros": len(rs),
            "holgura_min": round(float(self.holgura_min), 1), "borde_min": round(float(self.borde_min), 1),
            "duraciones": [round(r.duracion, 1) for r in rs], "pasada_final": round(self.duracion_pasada, 1),
            "viruta_restante": [r.viruta_restante for r in rs], "contactos": [r.contactos for r in rs],
            "contactos_pasada": self.contactos_pasada,
            "apoyo_no_visto": sum(not r.apoyo_visto for r in rs), "apoyos_falsos": sum(r.apoyos_falsos for r in rs),
            "broca_vista": [f"{r.broca_vista}/{r.lecturas_taladro}" for r in rs],
            "agujero_apuntado": [r.agujero_apuntado for r in rs],
            "holgura_donde": [f"{r.holgura_min:.1f} {r.holgura_donde}" for r in rs],
            "borde_donde": [f"{r.borde_min:.1f} {r.borde_donde}" for r in rs],
            "falsos_donde": [r.falsos_donde for r in rs],
        }


def correr_sim(sitios=None, verdad: bool = False, habilidad: str = "programada", modelo: str | None = None,
               semilla: int = 0, segundos: float | None = None, registros=CARPETA, rerun: bool = False,
               tiempo_real: bool = False, max_salto: float = 10.0, tabla=None, mundo=None, grabar=None,
               grabar_resolucion=(640, 480), repo_id: str = "local/garbi_limpiar_ciclo", crear_juez=None):
    """Simulación de punta a punta. Devuelve (juez, ciclo, detector, lector o None).
    `grabar`: carpeta de un LeRobotDataset nuevo donde se guarda cada LIMPIAR (ver `garbi.grabador.GrabadorCiclo`).
    `crear_juez(mundo, ciclo, sitios, control)`: otro juez (p. ej. `garbi.robustez.JuezRobusto`, con ruido); por
    defecto `JuezSim`."""
    from garbi.ciclo import escena_verdad
    from garbi.lateral import APARCADO, ControlLateral
    from garbi.mundo import MundoGarbi
    from garbi.real import CuerpoSim

    if mundo is None:
        mundo = MundoGarbi(render=not verdad or rerun or habilidad == "act", montaje="lateral")
    mundo.reset(semilla=semilla, tabla=tabla if tabla is not None else g.PoseTabla(360.0, 0.0, 0.0),
                q_inicial=APARCADO)
    detector = DetectorCiclos(RegistroCiclos(registros), modo="sim" if not verdad else "sim-verdad")
    detector.reloj = lambda: mundo.t  # duraciones en tiempo simulado
    if verdad:
        detector.umbral_limpio = UMBRAL_PARTICULAS_VIRUTA
    cuerpo = CuerpoSim(mundo, max_relative_target=max_salto)
    control = ControlLateral(mundo)
    ciclo = crear_ciclo(control, habilidad, modelo)
    ciclo.q = cuerpo.q().copy()
    juez = (crear_juez or JuezSim)(mundo, ciclo, sitios, control)
    lector = None
    if verdad:
        def percepcion(imagenes, q, t):
            return escena_verdad(mundo, t, ciclo.agujeros)
        con_imagenes = habilidad == "act" or rerun
    else:
        per = crear_percepcion(mundo.modelo)
        calibrar_sim(mundo, per)
        lector = LectorEscena(per, cuerpo.imagenes, lambda: ciclo.agujeros)
        percepcion = lector
        con_imagenes = habilidad == "act" or rerun
    if con_imagenes and not rerun:  # ACT solo mira las cámaras en LIMPIAR: no renderizar en el resto del ciclo
        con_imagenes = lambda: ciclo.estado.value == "limpiar"  # noqa: E731
    grabador = None
    if grabar:
        grabador = crear_grabador(grabar, grabar_resolucion, repo_id,
                                  verdad=lambda i: mundo.viruta_alrededor(np.asarray(ciclo.agujeros[i]), 35.0))
        if not con_imagenes:
            con_imagenes = lambda: grabador.necesita_imagenes(ciclo)  # noqa: E731
    lecturas = [0]

    def antes(t):
        juez.paso(t)

    def despues(escena):
        nueva = lector is None or lector.lecturas != lecturas[0]
        if lector is not None:
            lecturas[0] = lector.lecturas
        juez.medir(escena, nueva)

    def terminado():
        return juez.terminado and not detector.en_ciclo

    try:
        bucle(cuerpo, percepcion, ciclo, detector, RerunOpcional(rerun), segundos=segundos, tiempo=lambda: mundo.t,
              dormir=time.sleep if tiempo_real else (lambda s: None), antes_de_paso=antes,
              con_imagenes=con_imagenes, terminado=terminado, despues_de_paso=despues,
              al_ordenar=None if grabador is None else (lambda imgs, orden: grabador.paso(ciclo, orden, imgs)))
    finally:
        if grabador is not None:
            r = grabador.cerrar()
            log.info("grabación: %d/%d episodios guardados en %s · descartes %s", r["guardados"], r["intentos"],
                     grabar, r["motivos_descarte"])
    return juez, ciclo, detector, lector


def crear_grabador(ruta, resolucion=(640, 480), repo_id: str = "local/garbi_limpiar_ciclo", verdad=None):
    """`GrabadorCiclo` sobre un LeRobotDataset nuevo en `ruta` (cada LIMPIAR del ciclo, un episodio)."""
    from garbi.grabador import GrabadorCiclo, GrabadorLimpiezas

    return GrabadorCiclo(GrabadorLimpiezas(ruta, repo_id, resolucion, extra={"origen": "ciclo"}), verdad=verdad)


# --- ciclo final (solución final, 20-11) ----------------------------------------------------------------------------
def crear_ciclo_final(control, acercamiento: str = "programado", modelo: str | None = None):
    """`CicloFinal` con el acercamiento programado o ACT (`HabilidadACT(modelo, tarea=TAREA_ACERCAMIENTO)`, con el
    programado de respaldo)."""
    from garbi.ciclo_final import CicloFinal
    from garbi.habilidad import HabilidadACT
    from garbi.tipos import TAREA_ACERCAMIENTO

    habilidad = None
    if acercamiento == "act":
        if not modelo:
            raise SystemExit("--acercamiento act necesita --modelo (carpeta o repo de Hugging Face)")
        habilidad = HabilidadACT(modelo, tarea=TAREA_ACERCAMIENTO)
    return CicloFinal(control, habilidad, umbral_viruta=UMBRAL_PARTICULAS_VIRUTA,
                      umbral_fraccion=UMBRAL_FRACCION_VIRUTA)


def con_manos_verdad(escena: Escena, mundo) -> Escena:
    """La escena de la percepción con las manos y el agarre de la verdad de la simulación (hasta que llegue la
    percepción final de manos)."""
    from garbi.ciclo import manos_verdad

    taladro = dataclasses.replace(escena.taladro, agarrado=bool(escena.taladro.visible and
                                                                mundo.juez.mano_en_taladro))
    return dataclasses.replace(escena, manos=manos_verdad(mundo), taladro=taladro)


def correr_sim_final(intentos=None, verdad: bool = True, acercamiento: str = "programado", modelo: str | None = None,
                     semilla: int = 0, segundos: float | None = None, rerun: bool = False, tiempo_real: bool = False,
                     max_salto: float = 10.0, tabla=None, mundo=None, grabar=None, grabar_resolucion=(640, 480),
                     repo_id: str = "local/garbi_acercamiento", manos_verdad: bool = True, render=(640, 480),
                     sobrescribir: bool = False):
    """La sesión final en la simulación: `JuezSesion` (los 5 intentos y las variantes, o `intentos`) con el ciclo
    final. `verdad`: la Escena sale de la verdad de la simulación; si no, de la percepción por imágenes (con
    `manos_verdad`, las manos y el agarre de la verdad, hasta que llegue la percepción final). `grabar`: carpeta de un
    LeRobotDataset nuevo con cada acercamiento (de la clavada a la levantada, `GrabadorAcercamiento`). Devuelve
    (juez, ciclo, grabador o None)."""
    from garbi.ciclo import escena_verdad
    from garbi.lateral import APARCADO, ControlLateral
    from garbi.mundo import MundoGarbi
    from garbi.real import CuerpoSim
    from garbi.sesion import JuezSesion

    if mundo is None:
        mundo = MundoGarbi(render=not verdad or rerun or acercamiento == "act" or bool(grabar), montaje="lateral")
    mundo.reset(semilla=semilla, tabla=tabla if tabla is not None else g.PoseTabla(360.0, 0.0, 0.0),
                q_inicial=APARCADO)
    cuerpo = CuerpoSim(mundo, max_relative_target=max_salto, resolucion=render)
    control = ControlLateral(mundo)
    ciclo = crear_ciclo_final(control, acercamiento, modelo)
    ciclo.q = cuerpo.q().copy()
    juez = JuezSesion(mundo, ciclo, intentos, control)
    ultima: list = [None]
    if verdad:
        def percepcion(imagenes, q, t):
            ultima[0] = escena_verdad(mundo, t, ciclo.agujeros)
            return ultima[0]
        lector = None
    else:
        per = crear_percepcion(mundo.modelo)
        calibrar_sim(mundo, per)
        lector = LectorEscena(per, cuerpo.imagenes, lambda: ciclo.agujeros)

        def percepcion(imagenes, q, t):
            e = lector(imagenes, q, t)
            ultima[0] = con_manos_verdad(e, mundo) if manos_verdad else e
            return ultima[0]
    grabador = None
    if grabar:
        from garbi.acercamiento import diferencia_a_prudente
        from garbi.grabador import GrabadorAcercamiento, GrabadorLimpiezas

        grabador = GrabadorAcercamiento(
            GrabadorLimpiezas.para_acercamiento(grabar, repo_id, grabar_resolucion, sobrescribir=sobrescribir,
                                                extra={"origen": "sim", "acercamiento": acercamiento}),
            info=lambda: {"intento": len(juez.resultados), "fase_juez": juez.fase,
                          "punta": [round(float(v), 1) for v in mundo.juez.taladro_punta[:2]]},
            # ACT parte de la postura prudente al ejecutar: los episodios que no parten de ella se descartan
            partida=lambda escena, q: diferencia_a_prudente(control, escena, q))
    if acercamiento == "act" or grabar or rerun:
        con_imagenes = lambda: rerun or ciclo.estado.value in ("prudente", "acercamiento")  # noqa: E731
    else:
        con_imagenes = False
    contactos = [0]

    def despues(escena):
        juez.medir(escena, True)
        r = juez._actual
        if grabador is not None and r is not None and r.contactos > contactos[0]:
            grabador.invalidar("contacto")
        contactos[0] = 0 if r is None else r.contactos

    def al_ordenar(imagenes, orden):
        if grabador is not None:
            grabador.paso(ultima[0], orden.q, imagenes)

    try:
        bucle(cuerpo, percepcion, ciclo, None, RerunOpcional(rerun), segundos=segundos, tiempo=lambda: mundo.t,
              dormir=time.sleep if tiempo_real else (lambda s: None), antes_de_paso=juez.paso,
              con_imagenes=con_imagenes, terminado=lambda: juez.terminado, despues_de_paso=despues,
              al_ordenar=al_ordenar)
    finally:
        if grabador is not None:
            r = grabador.cerrar()
            log.info("grabación: %d/%d acercamientos guardados en %s · descartes %s", r["guardados"], r["intentos"],
                     grabar, r["motivos_descarte"])
    return juez, ciclo, grabador


def informe_final(juez, ciclo) -> None:
    res = juez.resumen()
    log.info("juez: %d/%d aciertos · variantes %s · holgura mín %.1f mm (mano libre %.1f) · borde mín %.1f mm",
             res["aciertos"], res["intentos"], res["variantes_ok"], res["holgura_min"], res["holgura_mano_min"],
             res["borde_min"])
    log.info("juez: duraciones %s s · agujeros %s (ciclo %s) · falsos %d · perdidos %d · viruta %s · contactos %s · "
             "siguiendo sin mano %d · acercamiento %s s · respaldos %d · frenadas de la habilidad %d · apartadas por "
             "mano %d", res["duraciones"], res["agujeros"], res["agujeros_ciclo"], res["falsos_agujeros"],
             res["perdidos"], res["viruta_restante"], res["contactos"], res["sin_agarre"], res["t_acercamiento"],
             ciclo.respaldos, ciclo.frenadas_habilidad, ciclo.apartadas_mano)


# --- bucle ---------------------------------------------------------------------------------------------------------
def bucle(cuerpo, percepcion: Callable, ciclo, detector: DetectorCiclos | None = None,
          rerun: RerunOpcional | None = None, hz: float = HZ_CONTROL, segundos: float | None = None,
          reloj: Callable[[], float] = time.monotonic, dormir: Callable[[float], None] = time.sleep,
          tiempo: Callable[[], float] | None = None, antes_de_paso: Callable[[float], None] | None = None,
          con_imagenes: bool | Callable[[], bool] = True, terminado: Callable[[], bool] | None = None,
          despues_de_paso: Callable[[Escena], None] | None = None,
          al_ordenar: Callable[[dict, object], None] | None = None) -> int:
    """Corre el bucle hasta `segundos`, `terminado()` o Ctrl+C. Siempre acaba con la aspiradora a 0 y el brazo quieto.
    `tiempo()`: t de la escena (por defecto, segundos desde el arranque con `reloj`). `con_imagenes` puede ser una
    función (se leen las cámaras solo cuando da True). `al_ordenar(imagenes, orden)`: después de cada `ciclo.paso`
    (grabar). Devuelve los pasos dados."""
    periodo = 1.0 / hz
    t0 = reloj()
    tiempo = tiempo or (lambda: reloj() - t0)
    siguiente = t0
    pasos = 0
    try:
        while True:
            t = tiempo()
            if (segundos is not None and t >= segundos - 1e-9) or (terminado is not None and terminado()):
                break
            if antes_de_paso is not None:
                antes_de_paso(t)
            mirar = con_imagenes() if callable(con_imagenes) else con_imagenes
            imagenes = cuerpo.imagenes() if mirar else {}
            q = cuerpo.q()
            escena = percepcion(imagenes, q, t)
            orden = ciclo.paso(escena, {"top": imagenes.get("top"), "wrist": imagenes.get("wrist"), "state": q})
            if al_ordenar is not None:
                al_ordenar(imagenes, orden)
            cuerpo.aspirar(orden.aspirar)
            cuerpo.enviar(orden.q)
            if detector is not None:
                r = detector.paso(escena, orden)
                if r is not None:
                    log.info("ciclo: %s en %.1f s (viruta %d → %d)%s", "acierto" if r.acierto else "fallo",
                             r.duracion, r.viruta_antes, r.viruta_despues,
                             f" · {r.motivo_fallo}" if r.motivo_fallo else "")
            if despues_de_paso is not None:
                despues_de_paso(escena)
            if rerun is not None:
                rerun.paso(t, imagenes or getattr(percepcion, "imagenes", {}), escena, orden, q)
            pasos += 1
            siguiente += periodo
            resto = siguiente - reloj()
            if resto > 0:
                dormir(resto)
            else:
                siguiente = reloj()  # vamos tarde: no intentar recuperar pasos
    except KeyboardInterrupt:
        log.info("Ctrl+C: paro")
    finally:
        parar(cuerpo)
    return pasos


def parar(cuerpo) -> None:
    """Aspiradora a 0 y brazo quieto, pase lo que pase."""
    try:
        cuerpo.aspirar(False)
    finally:
        quieto = getattr(cuerpo, "quieto", None)
        if quieto is not None:
            quieto()


def _sigterm_como_ctrl_c(*_):
    raise KeyboardInterrupt


# --- arranque ------------------------------------------------------------------------------------------------------
def argumentos(argv=None) -> argparse.Namespace:
    a = argparse.ArgumentParser(prog="python -m garbi.correr", description=__doc__.split("\n\n")[0])
    modo = a.add_mutually_exclusive_group(required=True)
    modo.add_argument("--sim", action="store_true", help="mundo simulado (montaje lateral)")
    modo.add_argument("--real", action="store_true", help="SO-101 real")
    a.add_argument("--puerto", help="puerto serie del brazo (p. ej. /dev/ttyACM0 o COM5)")
    a.add_argument("--id", default="garbi", help="id de la calibración de LeRobot")
    a.add_argument("--top", default="0", help="índice o ruta de la cámara de arriba")
    a.add_argument("--wrist", default="1", help="índice o ruta de la cámara de la muñeca")
    a.add_argument("--aspiradora", help="puerto serie de la señal de la aspiradora (línea 1/0 cada 200 ms)")
    a.add_argument("--max-salto", type=float, default=10.0, help="max_relative_target (grados por paso)")
    a.add_argument("--calibracion", default="calib", help="carpeta de la calibración del sitio (herramientas/garbi_calibrar.py)")
    a.add_argument("--ciclo", choices=("final", "viejo"), default="final",
                   help="final: estados de la solución final (por defecto); viejo: el de M4 con el paso 7")
    a.add_argument("--acercamiento", choices=("programado", "act"), default="programado",
                   help="ciclo final: quién hace el ACERCAMIENTO")
    a.add_argument("--sin-manos-verdad", action="store_true",
                   help="sim con percepción y ciclo final: no tomar las manos de la verdad de la simulación")
    a.add_argument("--habilidad", choices=("programada", "act"), default="programada", help="ciclo viejo: paso 7")
    a.add_argument("--modelo", help="ACT: carpeta o repo de Hugging Face")
    a.add_argument("--verdad", action="store_true", help="sim: Escena con la verdad de la simulación")
    a.add_argument("--agujeros", type=int, default=5, help="sim: agujeros que taladra el juez")
    a.add_argument("--semilla", type=int, default=0)
    a.add_argument("--tiempo-real", action="store_true", help="sim: ir a 30 Hz de reloj (si no, lo más rápido)")
    a.add_argument("--segundos", type=float, default=None, help="parar a los N s")
    a.add_argument("--registros", default=str(CARPETA), help="carpeta de los registros por ciclo")
    a.add_argument("--rerun", action="store_true", help="línea de tiempo en Rerun (si está instalado)")
    a.add_argument("--grabar", help="carpeta de un LeRobotDataset nuevo: cada LIMPIAR del ciclo, un episodio (solo los "
                                    "que la percepción da por limpios; descartes en episodios_garbi_limpiar.json)")
    a.add_argument("--grabar-resolucion", default="640x480", help="ANCHOxALTO de las imágenes del dataset")
    a.add_argument("--repo-id", default="local/garbi_limpiar_ciclo", help="repo_id del dataset grabado")
    ns = a.parse_args(argv)
    if ns.real and not ns.puerto:
        a.error("--real necesita --puerto")
    return ns


def main(argv=None) -> None:
    ns = argumentos(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s", datefmt="%H:%M:%S")
    signal.signal(signal.SIGTERM, _sigterm_como_ctrl_c)

    if ns.sim and ns.ciclo == "final":
        juez, ciclo, _ = correr_sim_final(None, ns.verdad, ns.acercamiento, ns.modelo, ns.semilla, ns.segundos,
                                          ns.rerun, ns.tiempo_real, ns.max_salto, grabar=ns.grabar,
                                          grabar_resolucion=_resolucion(ns.grabar_resolucion),
                                          repo_id=ns.repo_id if ns.repo_id != "local/garbi_limpiar_ciclo"
                                          else "local/garbi_acercamiento",
                                          manos_verdad=not ns.sin_manos_verdad)
        informe_final(juez, ciclo)
        juez.m.cerrar()
        return
    if ns.sim:
        sitios = SITIOS_JUEZ[: ns.agujeros] if ns.agujeros <= len(SITIOS_JUEZ) else sitios_aleatorios(ns.agujeros,
                                                                                                       ns.semilla)
        juez, ciclo, detector, lector = correr_sim(sitios, ns.verdad, ns.habilidad, ns.modelo, ns.semilla, ns.segundos,
                                                   ns.registros, ns.rerun, ns.tiempo_real, ns.max_salto,
                                                   grabar=ns.grabar, grabar_resolucion=_resolucion(ns.grabar_resolucion),
                                                   repo_id=ns.repo_id)
        res = juez.resumen()
        log.info("juez: %d/%d aciertos · holgura mín %.1f mm · borde mín %.1f mm · duraciones %s s · pasada final "
                 "%.1f s", res["aciertos"], res["agujeros"], res["holgura_min"], res["borde_min"], res["duraciones"],
                 res["pasada_final"])
        log.info("juez: viruta restante %s · contactos %s (pasada %d) · apoyos no vistos %d · apoyos falsos %d · "
                 "broca vista %s · inclinaciones de partida %s", res["viruta_restante"], res["contactos"],
                 res["contactos_pasada"], res["apoyo_no_visto"], res["apoyos_falsos"], res["broca_vista"],
                 [round(i) for _, i in ciclo.inclinaciones_partida])
        juez.m.cerrar()
    else:
        from garbi.lateral import ControlLateral
        from garbi.mundo import MundoGarbi
        from garbi.real import CuerpoReal

        detector = DetectorCiclos(RegistroCiclos(ns.registros), modo="real")
        from garbi.real import cargar_calibracion

        cuerpo = CuerpoReal(ns.puerto, ns.id, {"top": ns.top, "wrist": ns.wrist}, ns.aspiradora,
                            max_relative_target=ns.max_salto,
                            intrinsecas=cargar_calibracion(ns.calibracion).intrinsecas)
        modelo = MundoGarbi(render=False, montaje="lateral")  # solo cinemática
        # La cámara de arriba se calibra con el tapete en la primera imagen; la base del robot se supone en el origen
        # (plantilla impresa, M2 respaldo del paso 3) hasta que se calibre con el anillo verde.
        if ns.ciclo == "final":
            ciclo = crear_ciclo_final(ControlLateral(modelo), ns.acercamiento, ns.modelo)
            detector = DetectorCiclos(RegistroCiclos(ns.registros), modo="real", estado_reposo="descanso")
        else:
            ciclo = crear_ciclo(ControlLateral(modelo), ns.habilidad, ns.modelo)
        lector = LectorEscena(crear_percepcion_real(modelo.modelo, ns.calibracion), agujeros=lambda: ciclo.agujeros)
        grabador = None
        al_ordenar = None
        percepcion = lector
        if ns.grabar and ns.ciclo == "final":
            # Dataset de ACT con movimientos guiados por código: el ciclo final completo funciona con la percepción y
            # cada ACERCAMIENTO (el programado, o ACT en una 2.ª vuelta) se graba de la clavada a la levantada.
            grabador, percepcion, al_ordenar = grabador_acercamiento_real(
                ns.grabar, _resolucion(ns.grabar_resolucion), ns.repo_id, ciclo, lector, ns.acercamiento)
        elif ns.grabar:
            grabador = crear_grabador(ns.grabar, _resolucion(ns.grabar_resolucion), ns.repo_id)
            al_ordenar = lambda imgs, orden: grabador.paso(ciclo, orden, imgs)  # noqa: E731
        cuerpo.conectar()
        try:
            bucle(cuerpo, percepcion, ciclo, detector, RerunOpcional(ns.rerun), segundos=ns.segundos,
                  al_ordenar=al_ordenar)
        finally:
            cuerpo.cerrar()
            if grabador is not None:
                grabador.cerrar()
    ok = sum(r.acierto for r in detector.resumenes)
    log.info("%d/%d ciclos con acierto · registro en %s", ok, len(detector.resumenes), detector.registro.archivo())


def grabador_acercamiento_real(ruta, resolucion, repo_id, ciclo, lector, acercamiento: str = "programado"):
    """Graba en el robot real cada ACERCAMIENTO del ciclo final (de la clavada a la levantada) como episodio de
    LeRobotDataset, con la acción que manda el ciclo (movimiento guiado por código) y el mismo convenio de
    `observation.state` que usa `HabilidadACT`. Filtro de calidad: se descarta el episodio si alguna guardia frena el
    brazo, si entra el respaldo o si no parte de la postura prudente.

    Devuelve (grabador, percepcion, al_ordenar) para pasárselos a `bucle`."""
    from garbi.acercamiento import diferencia_a_prudente
    from garbi.grabador import GrabadorAcercamiento, GrabadorLimpiezas

    control = ciclo.control if hasattr(ciclo, "control") else None
    ultima = [None]
    vigilancia = {"frenadas": 0, "saltos": 0}
    grabador = GrabadorAcercamiento(
        GrabadorLimpiezas.para_acercamiento(ruta, repo_id, resolucion,
                                            extra={"origen": "real", "acercamiento": acercamiento}),
        info=lambda: {"agujeros": len(ciclo.agujeros)},
        partida=None if control is None else (lambda escena, q: diferencia_a_prudente(control, escena, q)))

    def percepcion(imagenes, q, t):
        ultima[0] = lector(imagenes, q, t)
        return ultima[0]

    def al_ordenar(imagenes, orden):
        frenadas = int(getattr(ciclo, "frenadas", 0))
        saltos = int(getattr(ciclo, "saltos_habilidad", 0))
        if orden.estado == "acercamiento" and (frenadas > vigilancia["frenadas"] or saltos > vigilancia["saltos"]):
            grabador.invalidar("guardia")
        vigilancia["frenadas"], vigilancia["saltos"] = frenadas, saltos
        grabador.paso(ultima[0], orden.q, imagenes)

    return grabador, percepcion, al_ordenar


def _resolucion(texto: str) -> tuple[int, int]:
    ancho, alto = str(texto).lower().split("x")
    return int(ancho), int(alto)


def sitios_aleatorios(n: int, semilla: int = 0, tabla=None) -> list[tuple[float, float]]:
    """n sitios (marco de la madera) alcanzables: a ≥ 40 mm del canto, a ≤ ALCANCE_AGUJERO del robot y separados."""
    from garbi.habilidad import ALCANCE_AGUJERO

    tabla = tabla or g.PoseTabla(360.0, 0.0, 0.0)
    rng = np.random.default_rng(semilla)
    largo, ancho = g.TABLA_TAMANO[0] / 2 - 40, g.TABLA_TAMANO[1] / 2 - 40
    sitios: list[tuple[float, float]] = []
    while len(sitios) < n:
        p = rng.uniform([-largo, -ancho], [largo, ancho])
        if np.linalg.norm(tabla.a_mesa(p)) > ALCANCE_AGUJERO - 8:
            continue
        if all(np.linalg.norm(p - np.array(s)) > 40.0 for s in sitios):
            sitios.append((float(p[0]), float(p[1])))
    return sitios


if __name__ == "__main__":
    main()
