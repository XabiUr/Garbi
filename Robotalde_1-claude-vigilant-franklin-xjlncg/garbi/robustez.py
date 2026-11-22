"""Robustez del ciclo completo con percepción real (M8 de la especificación técnica), en la simulación.

`JuezRobusto` es un `garbi.correr.JuezSim` con el ruido de una persona de verdad, distinto en cada agujero:

- taladro inclinado 0-8° respecto a la vertical, con la parte de arriba hacia un rumbo cualquiera;
- velocidad de entrada distinta (las fases de entrar, buscar y acercarse duran de ×0,6 a ×1,6);
- broca quieta en el aire a 10-40 mm sobre la madera durante `T_FLOTA` s antes de apoyar (prueba «en el aire»);
- temblor de la mano de ±1-2 mm mientras la broca está apoyada (quieto y taladrando);
- madera girada ±8° y en cualquier sitio de su zona (`contrato.ZONA_TABLA_*`).

Los sitios se eligen al azar dentro de la zona de taladro (`tipos.ZONA_TALADRO`, 320-420 mm del eje del robot) y a
≥ 40 mm del canto de la madera. El juez mide con la verdad de la simulación (la holgura con el taladro inclinado de
verdad); la percepción solo ve las imágenes renderizadas.

`sesion(semilla, ...)` corre una sesión (una madera, n agujeros, con o sin la pasada final) y devuelve un resumen;
`herramientas/garbi_robustez_ciclo.py` las reparte en varios procesos e imprime la tabla.
"""
from __future__ import annotations

import dataclasses
import time

import numpy as np

from garbi import contrato as g
from garbi.correr import JuezSim
from garbi.tipos import ZONA_TALADRO

INCLINACION_MAX = 8.0  # grados
VELOCIDAD_ENTRADA = (0.6, 1.6)  # factor de duración de entrar, buscar y acercarse
ALTURA_FLOTA = (10.0, 40.0)  # mm de la punta sobre la madera, quieta en el aire
T_FLOTA = 2.5  # s
TEMBLOR = (1.0, 2.0)  # mm de amplitud del temblor de la mano
MARGEN_CANTO = 40.0  # mm del sitio al canto de la madera
TOLERANCIA_SITIO = 5.0  # los sitios, a ≥ 5 mm de los bordes de la zona (el error de la percepción en planta)


@dataclasses.dataclass
class Ruido:
    inclinacion: float = 0.0
    rumbo: float = 0.0
    velocidad: float = 1.0  # factor de duración
    flota: float | None = None  # mm; None: sin fase en el aire
    temblor: float = 0.0  # mm
    fases_temblor: tuple = (0.0, 0.0, 0.0, 0.0)

    @classmethod
    def al_azar(cls, rng, flota: bool = True) -> Ruido:
        return cls(inclinacion=float(rng.uniform(0.0, INCLINACION_MAX)), rumbo=float(rng.uniform(0.0, 360.0)),
                   velocidad=float(rng.uniform(*VELOCIDAD_ENTRADA)),
                   flota=float(rng.uniform(*ALTURA_FLOTA)) if flota else None,
                   temblor=float(rng.uniform(*TEMBLOR)), fases_temblor=tuple(rng.uniform(0, 2 * np.pi, 4)))


class JuezRobusto(JuezSim):
    """`JuezSim` con ruido por agujero (`Ruido`). Además del resumen del juez, cuenta por agujero:
    - `aire_falso`: alguna lectura «apoyada» con la broca quieta en el aire (fase «flota»);
    - `traza`: (t, estado, fase, holgura real, error en planta de la punta percibida) en cada lectura nueva."""

    def __init__(self, mundo, ciclo, sitios=None, control=None, pasada_final: bool = False, rng=None,
                 ruido: bool = True, flota: bool = True, ruidos: list[Ruido] | None = None):
        super().__init__(mundo, ciclo, sitios, control, pasada_final=pasada_final)
        self.rng = rng if rng is not None else np.random.default_rng(0)
        self.ruidos = ruidos or [Ruido.al_azar(self.rng, flota) if ruido else Ruido(flota=None)
                                 for _ in self.sitios]
        self.ruido_actual = Ruido()
        self.aire_falso: list[bool] = []
        self.trazas: list[list] = []
        self._aire_falso = False
        self._traza: list = []

    # --- guion -------------------------------------------------------------------------------------------------
    def _empezar(self, t):
        self.ruido_actual = self.ruidos[self._k]
        n = self.ruido_actual
        f = n.velocidad
        fases = [("entra", 2.5 * f), ("busca", 2.0 * f), ("acerca", 1.5 * f)]
        if n.flota is not None:
            fases += [("baja", 0.6), ("flota", T_FLOTA)]
        fases += [("apoya", 0.6), ("quieto", 1.0), ("taladra", 6.0), ("levanta", 0.5), ("sale", 1.8)]
        self.FASES = tuple(fases)
        self._aire_falso = False
        self._traza = []
        super()._empezar(t)

    def _cerrar(self, t):
        self.aire_falso.append(self._aire_falso)
        self.trazas.append(self._traza)
        super()._cerrar(t)

    def _guion(self, t):
        a, A = self._a, self.AIRE
        n = self.ruido_actual
        s = t - self._t_fase
        durs = dict(self.FASES)
        nombres = [f for f, _ in self.FASES]
        while s >= durs[self._fase]:
            s -= durs[self._fase]
            self._t_fase += durs[self._fase]
            i = nombres.index(self._fase) + 1
            if i == len(nombres):
                self.m.quitar_taladro()
                self._fase = "espera"
                return
            self._fase = nombres[i]
        f = 0.5 - 0.5 * np.cos(np.pi * min(1.0, s / durs[self._fase]))
        h = n.flota if n.flota is not None else A
        tramos = {"entra": (self._entrada, a + [40, 30], A + 60, A), "busca": (a + [40, 30], a + [-20, -30], A, A),
                  "acerca": (a + [-20, -30], a, A, A), "baja": (a, a, A, h), "flota": (a, a, h, h),
                  "apoya": (a, a, h, 0.0), "quieto": (a, a, 0.0, 0.0), "taladra": (a, a, 0.0, 0.0),
                  "levanta": (a, a, 0.0, A), "sale": (a, self._entrada, A, A + 60)}
        p0, p1, z0, z1 = tramos[self._fase]
        xy = np.asarray(p0, float) + (np.asarray(p1, float) - np.asarray(p0, float)) * f
        if self._fase in ("quieto", "taladra") and n.temblor > 0:  # temblor de la mano: 3 y 5 Hz, ±temblor mm
            ph = n.fases_temblor
            w = 2 * np.pi * t
            xy = xy + n.temblor * 0.5 * np.array([np.sin(3 * w + ph[0]) + np.sin(5 * w + ph[1]),
                                                  np.sin(3 * w + ph[2]) + np.sin(5 * w + ph[3])])
        self.m.poner_taladro(xy[0], xy[1], g.ALTURA_CARA_TABLA + z0 + (z1 - z0) * f, n.inclinacion, n.rumbo)
        if self._fase == "taladra" and not self._taladrado:
            self.m.taladrar()
            self._taladrado = True

    # --- medida ------------------------------------------------------------------------------------------------
    def medir(self, escena=None, nueva_lectura: bool = True) -> None:
        super().medir(escena, nueva_lectura)
        if self._actual is None or escena is None or not nueva_lectura or not self.m.juez.taladro_visible:
            return
        if self._fase == "flota" and escena.broca.apoyada:
            self._aire_falso = True
        from garbi.ciclo import _lr_a_q4

        verdad = self.m.juez.taladro_punta
        err = np.nan if escena.broca.punta is None else float(np.linalg.norm(escena.broca.punta[:2] - verdad[:2]))
        eje = self.m.juez.taladro_eje
        hol = self.control.holgura(_lr_a_q4(self.m.estado()), verdad, eje)
        q4_orden = _lr_a_q4(self.ciclo.q)
        hol_orden = self.control.holgura(q4_orden, verdad, eje)  # la de la orden (sin el retraso del brazo)
        hol_percibida = self.ciclo.holgura(q4_orden)  # la que calcula el ciclo para la orden
        err_eje = np.nan if escena.broca.eje is None else float(np.degrees(np.arccos(np.clip(
            np.dot(escena.broca.eje, eje), -1, 1))))
        par = self._par_mas_cercano(_lr_a_q4(self.m.estado()), verdad, eje) if hol < 12.0 else ""
        if hol < 12.0:
            par += f" q={np.round(self.m.estado(), 2).tolist()} orden={np.round(self.ciclo.q, 2).tolist()} " \
                   f"P={np.round(verdad, 1).tolist()} eje={np.round(eje, 4).tolist()}"
        self._traza.append((round(self.m.t, 2), self.ciclo.estado.value, self._fase, round(hol, 1), round(err, 1),
                            escena.broca.fuente, bool(escena.broca.apoyada), round(hol_orden, 1),
                            round(float(hol_percibida), 1), round(err_eje, 1), par))

    def _par_mas_cercano(self, q4, P, eje) -> str:
        """Qué pieza del brazo y qué pieza del taladro están más cerca (para el diagnóstico)."""
        import mujoco

        from garbi.lateral import cuaternio_eje

        c = self.control
        c.d.mocap_pos[c._mocap_taladro] = np.asarray(P, float) * 1e-3
        c.d.mocap_quat[c._mocap_taladro] = cuaternio_eje(eje)
        c._poner(q4)
        ft = np.zeros(6)
        d, a, b = min((mujoco.mj_geomDistance(c.M, c.d, a, b, 0.2, ft), a, b) for a in c._g_brazo for b in c._g_taladro)
        return f"{c.M.geom(a).name or a}-{c.M.geom(b).name or b} {d * 1e3:.1f}"


# --- sitios y sesiones ---------------------------------------------------------------------------------------------
def madera_al_azar(rng) -> g.PoseTabla:
    return g.PoseTabla(float(rng.uniform(*g.ZONA_TABLA_X)), float(rng.uniform(*g.ZONA_TABLA_Y)),
                       float(rng.uniform(*g.ZONA_TABLA_GIRO)))


def sitios_en_zona(rng, tabla: g.PoseTabla, n: int, separacion: float = 40.0) -> list[tuple[float, float]]:
    """n sitios (marco de la madera) a ≥ MARGEN_CANTO del canto, con la punta en la zona de taladro (con
    TOLERANCIA_SITIO) y separados entre sí."""
    largo, ancho = g.TABLA_TAMANO[0] / 2 - MARGEN_CANTO, g.TABLA_TAMANO[1] / 2 - MARGEN_CANTO
    r0, r1 = ZONA_TALADRO[0] + TOLERANCIA_SITIO, ZONA_TALADRO[1] - TOLERANCIA_SITIO
    sitios: list[tuple[float, float]] = []
    while len(sitios) < n:
        p = rng.uniform([-largo, -ancho], [largo, ancho])
        if not r0 <= float(np.linalg.norm(tabla.a_mesa(p))) <= r1:
            continue
        if all(np.linalg.norm(p - np.array(s)) > separacion for s in sitios):
            sitios.append((float(p[0]), float(p[1])))
    return sitios


_MUNDO = None


def _mundo():
    global _MUNDO
    if _MUNDO is None:
        from garbi.mundo import MundoGarbi

        _MUNDO = MundoGarbi(render=True, montaje="lateral")
    return _MUNDO


def sesion(semilla: int, agujeros: int = 1, ruido: bool = True, flota: bool = True, pasada_final: bool = False,
           sitios=None, tabla=None, registros=None, segundos: float | None = None) -> dict:
    """Una sesión con percepción real: madera al azar (o `tabla`), `agujeros` sitios al azar de la zona (o `sitios`)
    y el ruido de `JuezRobusto`. Devuelve el resumen del juez con lo de la robustez (por agujero) y el tiempo."""
    import tempfile

    from garbi.correr import correr_sim

    rng = np.random.default_rng(1000 + semilla)
    tabla = tabla or (madera_al_azar(rng) if ruido else g.PoseTabla(360.0, 0.0, 0.0))
    sitios = sitios or sitios_en_zona(rng, tabla, agujeros)
    jueces = []

    def crear_juez(mundo, ciclo, sitios_, control):
        j = JuezRobusto(mundo, ciclo, sitios_, control, pasada_final=pasada_final, rng=rng, ruido=ruido, flota=flota)
        jueces.append(j)
        return j

    t0 = time.time()
    registros = registros or tempfile.mkdtemp(prefix="garbi_robustez_")
    segundos = segundos or 60.0 * len(sitios) + (90.0 if pasada_final else 20.0)
    juez, ciclo, _, lector = correr_sim(sitios, semilla=semilla, segundos=segundos, registros=registros, tabla=tabla,
                                        mundo=_mundo(), crear_juez=crear_juez)
    res = juez.resumen()
    tablam = juez.m.juez.tabla
    res.update({
        "semilla": semilla, "tabla": (round(tabla.x, 1), round(tabla.y, 1), round(tabla.giro, 1)),
        "sitios_mesa": [tuple(round(float(v)) for v in tablam.a_mesa(np.array(s))) for s in sitios],
        "radios": [round(float(np.linalg.norm(tablam.a_mesa(np.array(s)))), 1) for s in sitios],
        "ruidos": [dataclasses.asdict(r) for r in juez.ruidos],
        "aire_falso": list(juez.aire_falso), "terminado": juez.terminado,
        "aciertos_por_agujero": [r.acierto for r in juez.resultados],
        "holguras": [round(float(r.holgura_min), 1) for r in juez.resultados],
        "bordes": [round(float(r.borde_min), 1) for r in juez.resultados],
        "apoyos_vistos": [r.apoyo_visto for r in juez.resultados],
        "falsos": [r.apoyos_falsos for r in juez.resultados],
        "fallidos": sorted(ciclo.fallidos), "transiciones": [(round(tr.t, 1), tr.de, tr.a, tr.motivo)
                                                              for tr in ciclo.transiciones],
        "trazas": juez.trazas, "segundos_reloj": round(time.time() - t0, 1),
    })
    return res
