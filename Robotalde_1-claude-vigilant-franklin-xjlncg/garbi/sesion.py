"""Juez de la sesión final en la simulación (solución final, 20-11): la persona con las dos manos y el taladro.

Cada intento de la tarea (`Intento`, tipo «tarea"):

    manos entran → coge el taladro → apunta → clava → taladra 4-6 s → levanta
      → (a veces) mueve la broca y vuelve a clavar · (a veces) apoya y levanta sin taladrar (< 2 s: no es agujero)
      → saca el taladro → (a veces) mueve la madera → se van las manos → Garbi limpia y descansa

Con `deslizar`, a mitad del acercamiento la broca se desliza a otro punto sin levantarla (el acercamiento se corrige)
y con `mano_cruza` la mano libre pasa junto a la boca mientras se taladra (el robot se aparta y vuelve): son las
recuperaciones que se graban para ACT. Variantes: «taladro_dejado» (el taladro, de pie en la madera, sin mano: Garbi
no debe seguirlo) y «mano_sola» (la mano libre en el tapete: despierta, pero no sigue nada).

`JuezSesion` tiene la interfaz de `garbi.correr.JuezSim` (`paso(t)` antes de cada paso del bucle, `medir(escena)`
después, `terminado`, `resumen()`) y mide con la verdad: aciertos (todos los agujeros del intento limpios, sin
contacto, sin agujeros falsos ni perdidos y Garbi descansa al final), holgura mínima con el taladro y con la mano
libre, borde mínimo, duraciones, agujeros falsos y pasos siguiendo un taladro sin mano.
"""
from __future__ import annotations

import dataclasses
import logging

import mujoco
import numpy as np

from garbi import contrato as g
from garbi.tipos import UMBRAL_PARTICULAS_VIRUTA

log = logging.getLogger("garbi")

AIRE = 50.0  # mm de la punta sobre la madera al moverse
DESCANSO_MAX = 90.0  # s esperando a que Garbi descanse al final de cada intento
MISMO_AGUJERO = 5.0  # mm para casar un agujero del ciclo con uno de verdad
RADIO_VIRUTA = 35.0


@dataclasses.dataclass
class Intento:
    tipo: str = "tarea"  # "tarea", "taladro_dejado" o "mano_sola"
    sitio: tuple = (0.0, 0.0)  # marco de la madera
    t_taladrar: float = 5.0
    reclavar: tuple | None = None  # segundo sitio (marco de la madera): levanta, mueve y vuelve a clavar
    apoyo_corto: tuple | None = None  # sitio donde apoya < 2 s y levanta sin taladrar
    deslizar: tuple | None = None  # (dx, dy) mm: desliza la broca clavada a mitad del acercamiento
    mano_cruza: bool = False  # la mano libre pasa junto a la boca mientras se taladra
    mover_madera: tuple | None = None  # (dx, dy, dgiro) al final, con la mano libre


@dataclasses.dataclass
class ResultadoIntento:
    intento: Intento
    t_inicio: float
    duracion: float = 0.0  # s, de que entran las manos a que Garbi descansa
    descansa: bool = False
    agujeros: list = dataclasses.field(default_factory=list)  # índices en juez.agujeros (de verdad)
    viruta_restante: list = dataclasses.field(default_factory=list)
    agujeros_ciclo: int = 0  # los que apuntó el ciclo en este intento
    falsos: int = 0  # agujeros del ciclo sin uno de verdad a < 5 mm
    perdidos: int = 0  # agujeros de verdad sin uno del ciclo a < 5 mm
    contactos: int = 0
    holgura_min: float = np.inf  # mm con el taladro (postura real)
    holgura_mano_min: float = np.inf  # mm con la mano libre
    borde_min: float = np.inf
    holgura_donde: str = ""
    borde_donde: str = ""
    sin_agarre: int = 0  # pasos en PRUDENTE/ACERCAMIENTO con el taladro sin mano desde hace > 1 s
    estados: list = dataclasses.field(default_factory=list)  # estados por los que pasa, en orden
    t_acercamiento: list = dataclasses.field(default_factory=list)  # s de la clavada a la postura de aspirar

    @property
    def acierto(self) -> bool:
        if self.intento.tipo == "mano_sola":  # despierta, pero no sigue nada
            return self.descansa and self.contactos == 0 and "despierto" in self.estados and \
                not any(e in self.estados for e in ("prudente", "acercamiento"))
        if self.intento.tipo == "taladro_dejado":  # lo sigue mientras está agarrado; suelto, no
            return self.descansa and self.contactos == 0 and self.sin_agarre == 0 and self.agujeros_ciclo == 0
        return (self.descansa and self.contactos == 0 and self.falsos == 0 and self.perdidos == 0 and
                bool(self.agujeros) and all(0 <= v <= UMBRAL_PARTICULAS_VIRUTA for v in self.viruta_restante))


def intentos_estandar() -> list[Intento]:
    """Los 5 intentos de la tarea (con re-clavada, apoyo corto, deslizamiento, mano que se cruza y madera movida dos
    veces) y las dos variantes. Sitios en el marco de la madera (en la zona de taladro con la madera en (360, 0))."""
    return [
        Intento(sitio=(-20.0, 40.0), t_taladrar=5.0),
        Intento(sitio=(-40.0, -30.0), t_taladrar=4.5, reclavar=(10.0, -45.0)),
        Intento(sitio=(0.0, -80.0), t_taladrar=5.5, apoyo_corto=(-30.0, -100.0), mover_madera=(12.0, -8.0, 4.0)),
        Intento(sitio=(40.0, 20.0), t_taladrar=6.0, mano_cruza=True),
        Intento(sitio=(-20.0, 100.0), t_taladrar=4.0, deslizar=(20.0, -10.0), mover_madera=(-8.0, 12.0, -5.0)),
        Intento(tipo="taladro_dejado", sitio=(10.0, 0.0)),
        Intento(tipo="mano_sola", sitio=(0.0, 0.0)),
    ]


def intentos_grabacion(rng, n: int, tabla: g.PoseTabla | None = None) -> list[Intento]:
    """n intentos al azar para grabar el acercamiento: sitios en la zona de taladro, la mitad con la broca deslizada a
    mitad del acercamiento y un tercio con la mano libre que se cruza; a veces re-clavada."""
    from garbi.robustez import sitios_en_zona

    tabla = tabla or g.PoseTabla(360.0, 0.0, 0.0)
    out = []
    for k in range(n):
        s = sitios_en_zona(rng, tabla, 2, separacion=40.0)
        ang = rng.uniform(0, 2 * np.pi)
        d = rng.uniform(15.0, 25.0)
        out.append(Intento(sitio=s[0], t_taladrar=float(rng.uniform(4.0, 6.0)),
                           deslizar=(float(d * np.cos(ang)), float(d * np.sin(ang))) if k % 2 == 1 else None,
                           mano_cruza=k % 3 == 2, reclavar=s[1] if k % 4 == 3 else None))
    return out


def _suave(f: float) -> float:
    return 0.5 - 0.5 * np.cos(np.pi * min(1.0, max(0.0, f)))


class JuezSesion:
    """La persona simulada (guion por intento, `Intento`) y el juez de la sesión final."""

    def __init__(self, mundo, ciclo, intentos: list[Intento] | None = None, control=None, reposo: float = 2.0):
        self.m = mundo
        self.ciclo = ciclo
        self.intentos = list(intentos_estandar() if intentos is None else intentos)
        self.control = control if control is not None else ciclo.control
        self.resultados: list[ResultadoIntento] = []
        self.holgura_min = np.inf
        self.holgura_mano_min = np.inf
        self.borde_min = np.inf
        self.reposo = reposo
        self.fase = "reposo"
        self._actual: ResultadoIntento | None = None
        self._gen = None
        self._fin = False
        self._t = 0.0
        self._t_sin_agarre = None
        self._geoms_brazo = set(getattr(self.control, "_g_brazo", []))
        M = self.control.M
        self._g_mano = [M.geom(n).id for n in ("mano_libre_palma", "mano_libre_dedos", "mano_libre_brazo")]
        self._mocap_mano = M.body_mocapid[M.body("mano_libre").id]

    @property
    def terminado(self) -> bool:
        return self._fin

    # --- guion -----------------------------------------------------------------------------------------------------
    def paso(self, t: float) -> None:
        self._t = t
        if self._fin:
            return
        if self._gen is None:
            self._gen = self._sesion()
        try:
            next(self._gen)
        except StopIteration:
            self._fin = True

    def _esperar(self, segundos):
        t0 = self._t
        while self._t - t0 < segundos - 1e-9:
            yield

    def _sesion(self):
        yield from self._esperar(self.reposo)
        for it in self.intentos:
            self._actual = ResultadoIntento(intento=it, t_inicio=self._t)
            self.m.coger_taladro()  # la mano vuelve a sujetar el taladro (lo normal)
            n_ag_juez, n_ag_ciclo = len(self.m.juez.agujeros), len(self.ciclo.agujeros)
            if it.tipo == "tarea":
                yield from self._tarea(it)
            elif it.tipo == "taladro_dejado":
                yield from self._taladro_dejado(it)
            else:
                yield from self._mano_sola(it)
            self.fase = "esperar_descanso"
            t0 = self._t
            while self.ciclo.estado.value != "descanso" and self._t - t0 < DESCANSO_MAX:
                yield
            self._cerrar(n_ag_juez, n_ag_ciclo)
            if it.tipo == "taladro_dejado":
                self.m.quitar_taladro()  # la persona se lleva el taladro (con Garbi descansando)
            yield from self._esperar(1.0)

    # posiciones
    def _mesa(self, p_tabla) -> np.ndarray:
        return self.m.juez.tabla.a_mesa(np.asarray(p_tabla, float))

    def _reposo_mano(self, it: Intento) -> np.ndarray:
        """Donde apoya la mano libre: en la madera, hacia la persona y al otro lado del sitio."""
        lado = -1.0 if it.sitio[1] >= 0 else 1.0
        return self._mesa((70.0, lado * 110.0))

    def _mover_mano(self, desde, hasta, z0, z1, segundos):
        n = max(1, round(segundos * g.FPS))
        for k in range(1, n + 1):
            f = _suave(k / n)
            p = np.asarray(desde, float) + (np.asarray(hasta, float) - np.asarray(desde, float)) * f
            self.m.poner_mano_libre(p[0], p[1], g.ALTURA_CARA_TABLA + z0 + (z1 - z0) * f)
            yield

    def _mover_taladro(self, desde, hasta, z0, z1, segundos):
        n = max(1, round(segundos * g.FPS))
        for k in range(1, n + 1):
            f = _suave(k / n)
            p = np.asarray(desde, float) + (np.asarray(hasta, float) - np.asarray(desde, float)) * f
            self.m.poner_taladro(p[0], p[1], g.ALTURA_CARA_TABLA + z0 + (z1 - z0) * f)
            yield

    def _entrada(self, y) -> np.ndarray:
        return np.array([g.PERSONA_X + 60, y])

    def _manos_entran(self, it):
        reposo = self._reposo_mano(it)
        self.fase = "manos_entran"
        self.m.poner_mano_libre(*self._entrada(reposo[1]), g.ALTURA_CARA_TABLA + 80)
        yield from self._mover_mano(self._entrada(reposo[1]), reposo, 80, 0, 1.5)
        yield from self._esperar(1.0)
        return reposo

    def _clavar_y_taladrar(self, a, t_taladrar, it: Intento | None = None, reposo=None):
        """Apoya en a, (desliza), taladra t_taladrar s (con la mano que se cruza) y levanta. Devuelve el punto final."""
        self.fase = "apoya"
        yield from self._mover_taladro(a, a, AIRE, 0.0, 0.6)
        if it is not None and it.deslizar is not None:
            self.fase = "quieto"
            yield from self._esperar(0.6)  # el acercamiento ya ha empezado
            self.fase = "desliza"
            b = a + np.asarray(it.deslizar, float)
            yield from self._mover_taladro(a, b, 0.0, 0.0, 1.0)
            a = b
        self.fase = "quieto"
        yield from self._esperar(0.8)
        self.m.taladrar()
        self.fase = "taladra"
        if it is not None and it.mano_cruza and reposo is not None:
            yield from self._esperar(max(0.0, t_taladrar - 3.0) / 2)
            # la mano pasa junto a la boca (de lado, a ~90 mm de la broca, algo hacia el robot) y vuelve
            hacia_robot = -a / np.linalg.norm(a)
            lado = np.array([-hacia_robot[1], hacia_robot[0]]) * (1.0 if np.dot(reposo - a, [-hacia_robot[1],
                                                                                          hacia_robot[0]]) > 0 else -1.0)
            junto = a + hacia_robot * 30.0 + lado * 70.0
            self.fase = "mano_cruza"
            yield from self._mover_mano(reposo, junto, 0.0, 40.0, 1.2)
            yield from self._mover_mano(junto, reposo, 40.0, 0.0, 1.8)
            self.fase = "taladra"
            yield from self._esperar(max(0.0, t_taladrar - 3.0) / 2)
        else:
            yield from self._esperar(t_taladrar)
        self.fase = "levanta"
        yield from self._mover_taladro(a, a, 0.0, AIRE, 0.5)
        return a

    def _tarea(self, it: Intento):
        reposo = yield from self._manos_entran(it)
        a = self._mesa(it.sitio)
        entrada = self._entrada(a[1])
        self.fase = "coge"
        self.m.poner_taladro(entrada[0], entrada[1], g.ALTURA_CARA_TABLA + AIRE + 60)
        yield from self._mover_taladro(entrada, a + [40, 30], AIRE + 60, AIRE, 2.5)
        self.fase = "apunta"
        yield from self._mover_taladro(a + [40, 30], a, AIRE, AIRE, 1.5)
        a = yield from self._clavar_y_taladrar(a, it.t_taladrar, it, reposo)
        if it.reclavar is not None:
            b = self._mesa(it.reclavar)
            self.fase = "mueve"
            yield from self._mover_taladro(a, b, AIRE, AIRE, 1.5)
            a = yield from self._clavar_y_taladrar(b, 4.0)
        if it.apoyo_corto is not None:
            b = self._mesa(it.apoyo_corto)
            self.fase = "mueve"
            yield from self._mover_taladro(a, b, AIRE, AIRE, 1.5)
            self.fase = "apoyo_corto"
            yield from self._mover_taladro(b, b, AIRE, 0.0, 0.6)
            yield from self._esperar(1.0)
            yield from self._mover_taladro(b, b, 0.0, AIRE, 0.5)
            a = b
        self.fase = "sale"
        yield from self._mover_taladro(a, entrada, AIRE, AIRE + 60, 1.8)
        self.m.quitar_taladro()
        mano = reposo
        if it.mover_madera is not None:
            self.fase = "mueve_madera"
            dx, dy, dgiro = it.mover_madera
            n = round(1.5 * g.FPS)
            for _ in range(n):
                self.m.mover_tabla(dx / n, dy / n, dgiro / n)
                mano = mano + np.array([dx / n, dy / n])
                self.m.poner_mano_libre(mano[0], mano[1], g.ALTURA_CARA_TABLA)
                yield
        self.fase = "manos_salen"
        yield from self._mover_mano(mano, self._entrada(mano[1]), 0.0, 80.0, 1.5)
        self.m.quitar_mano_libre()

    def _taladro_dejado(self, it: Intento):
        reposo = yield from self._manos_entran(it)
        a = self._mesa(it.sitio)
        entrada = self._entrada(a[1])
        self.fase = "coge"
        self.m.poner_taladro(entrada[0], entrada[1], g.ALTURA_CARA_TABLA + AIRE + 60)
        yield from self._mover_taladro(entrada, a, AIRE + 60, AIRE, 3.0)
        yield from self._mover_taladro(a, a, AIRE, 0.0, 0.8)
        self.fase = "dejado"  # lo suelta: el taladro queda de pie en la madera, sin mano
        self.m.poner_taladro(a[0], a[1])
        self.m.soltar_taladro()
        yield from self._esperar(3.0)
        self.fase = "manos_salen"
        yield from self._mover_mano(reposo, self._entrada(reposo[1]), 0.0, 80.0, 1.5)
        self.m.quitar_mano_libre()

    def _mano_sola(self, it: Intento):
        reposo = yield from self._manos_entran(it)
        self.fase = "mano_sola"
        otro = self._mesa((-20.0, 0.0))
        yield from self._mover_mano(reposo, otro, 0.0, 30.0, 2.0)
        yield from self._mover_mano(otro, reposo, 30.0, 0.0, 2.0)
        self.fase = "manos_salen"
        yield from self._mover_mano(reposo, self._entrada(reposo[1]), 0.0, 80.0, 1.5)
        self.m.quitar_mano_libre()

    # --- medida ----------------------------------------------------------------------------------------------------
    def contactos(self) -> int:
        d = self.m.datos
        n = 0
        for i in range(d.ncon):
            c = d.contact[i]
            if c.dist < 0 and ((c.geom1 in self._geoms_brazo) != (c.geom2 in self._geoms_brazo)):
                n += 1
        return n

    def holgura_mano(self, q4) -> float:
        """mm del brazo (postura q4) a la mano libre de verdad."""
        palma = self.m.juez.mano_libre
        if palma is None:
            return np.inf
        c = self.control
        c._poner(q4)
        c.d.mocap_pos[self._mocap_mano] = np.asarray(palma, float) * 1e-3
        mujoco.mj_kinematics(c.M, c.d)
        ft = np.zeros(6)
        h = min(mujoco.mj_geomDistance(c.M, c.d, a, b, 0.3, ft) for a in c._g_brazo for b in self._g_mano) * 1e3
        c.d.mocap_pos[self._mocap_mano] = np.array([0.0, 0.0, -2.0])
        return h

    def medir(self, escena=None, nueva_lectura: bool = True) -> None:
        from garbi.ciclo import _lr_a_q4

        q4 = _lr_a_q4(self.m.estado())
        borde = self.ciclo.borde(q4)
        self.borde_min = min(self.borde_min, borde)
        j = self.m.juez
        holgura = np.inf
        if j.taladro_visible:
            holgura = self.control.holgura(q4, j.taladro_punta, j.taladro_eje)
            self.holgura_min = min(self.holgura_min, holgura)
        h_mano = self.holgura_mano(q4)
        self.holgura_mano_min = min(self.holgura_mano_min, h_mano)
        r = self._actual
        if r is None:
            return
        estado = self.ciclo.estado.value
        if not r.estados or r.estados[-1] != estado:
            r.estados.append(estado)
        if borde < r.borde_min:
            r.borde_min, r.borde_donde = borde, f"{estado}/{self.fase}"
        if holgura < r.holgura_min:
            r.holgura_min, r.holgura_donde = holgura, f"{estado}/{self.fase}"
        r.holgura_mano_min = min(r.holgura_mano_min, h_mano)
        r.contactos += bool(self.contactos() + int(holgura < 0.0) + int(h_mano < 0.0))
        if j.taladro_visible and not j.mano_en_taladro:
            self._t_sin_agarre = self._t if self._t_sin_agarre is None else self._t_sin_agarre
            if self._t - self._t_sin_agarre > 1.0 and estado in ("prudente", "acercamiento"):
                r.sin_agarre += 1
        else:
            self._t_sin_agarre = None

    def _cerrar(self, n_ag_juez: int, n_ag_ciclo: int) -> None:
        r = self._actual
        r.duracion = self._t - r.t_inicio
        r.descansa = self.ciclo.estado.value == "descanso"
        j = self.m.juez
        reales = [np.asarray(h, float) for h in j.agujeros]
        ciclo = [np.asarray(h, float) for h in self.ciclo.agujeros]
        r.agujeros = list(range(n_ag_juez, len(reales)))
        r.viruta_restante = [self.m.viruta_alrededor(reales[i], RADIO_VIRUTA) for i in r.agujeros]
        nuevos = ciclo[n_ag_ciclo:]
        r.agujeros_ciclo = len(nuevos)
        r.falsos = sum(not any(np.linalg.norm(h - v) < MISMO_AGUJERO for v in reales) for h in nuevos)
        r.perdidos = sum(not any(np.linalg.norm(reales[i] - h) < MISMO_AGUJERO for h in ciclo) for i in r.agujeros)
        ts = list(getattr(self.ciclo, "t_en_posicion", []))
        r.t_acercamiento = [round(x, 2) for x in ts[getattr(self, "_n_tpos", 0):]]
        self._n_tpos = len(ts)
        log.info("intento %d (%s): %s · %.1f s · agujeros %d (ciclo %d, falsos %d, perdidos %d) · viruta %s · "
                 "holgura %.1f (%s) · mano %.1f · borde %.1f (%s) · contactos %d · sin agarre %d · %s",
                 len(self.resultados) + 1, r.intento.tipo, "acierto" if r.acierto else "FALLO", r.duracion,
                 len(r.agujeros), r.agujeros_ciclo, r.falsos, r.perdidos, r.viruta_restante, r.holgura_min,
                 r.holgura_donde, r.holgura_mano_min, r.borde_min, r.borde_donde, r.contactos, r.sin_agarre,
                 "→".join(r.estados))
        self.resultados.append(r)
        self._actual = None

    def resumen(self) -> dict:
        rs = self.resultados
        tareas = [r for r in rs if r.intento.tipo == "tarea"]
        return {
            "aciertos": sum(r.acierto for r in tareas), "intentos": len(tareas),
            "variantes_ok": {r.intento.tipo: r.acierto for r in rs if r.intento.tipo != "tarea"},
            "holgura_min": round(float(self.holgura_min), 1), "holgura_mano_min": round(float(self.holgura_mano_min), 1),
            "borde_min": round(float(self.borde_min), 1),
            "duraciones": [round(r.duracion, 1) for r in rs],
            "agujeros": [len(r.agujeros) for r in rs], "agujeros_ciclo": [r.agujeros_ciclo for r in rs],
            "falsos_agujeros": sum(r.falsos for r in rs), "perdidos": sum(r.perdidos for r in rs),
            "viruta_restante": [r.viruta_restante for r in rs], "contactos": [r.contactos for r in rs],
            "sin_agarre": sum(r.sin_agarre for r in rs), "descansa": [r.descansa for r in rs],
            "t_acercamiento": [r.t_acercamiento for r in rs],
            "holgura_donde": [f"{r.holgura_min:.1f} {r.holgura_donde}" for r in rs],
            "borde_donde": [f"{r.borde_min:.1f} {r.borde_donde}" for r in rs],
            "estados": ["→".join(r.estados) for r in rs],
        }
