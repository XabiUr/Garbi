"""Demostraciones guionizadas del robot soldador y grabación a un `LeRobotDataset` (LeRobot 0.7).

Cada demostración: reposo → aproximación (articular) → bajada al inicio del cordón (cartesiana) → recorrido de los
120 mm a velocidad constante con la orientación de la unión → subida → vuelta a reposo. La cinemática inversa
(`Cinematica.inversa_pose`) da las posiciones articulares objetivo; esas son la acción, como si las mandara el
brazo guía. Con ruido (por defecto) se añade variabilidad de operador humano: postura inicial, duraciones, velocidad
y pequeñas desviaciones suavizadas de la trayectoria y de los ángulos.

"Aprende del mejor" (filtro de calidad): cada demostración se puntúa con `lewelder.metricas.evaluar_pasada` sobre la
punta de la antorcha (gatillo apretado durante el cordón), igual que al alumno, y solo se guarda en el dataset si la
nota llega a `--umbral-nota`. La nota de todas (también las descartadas) queda en `<salida>/notas.json`. Con
`--incluir-malas N` se graban además N demostraciones malas a propósito (temblorosa, con parada, desviada o
rápida) para que el filtro tenga algo que descartar.

Uso:
    python -m sim.demostraciones --episodios 8 --salida datos/lewelder_sim --repo-id local/lewelder_sim
    python -m sim.demostraciones --episodios 8 --incluir-malas 4 --umbral-nota 9 --salida datos/lewelder_filtrado
"""
from __future__ import annotations

import argparse
import itertools
import json
import shutil
import time
from dataclasses import dataclass, field, replace
from pathlib import Path

import numpy as np

from lewelder import contrato as c
from sim import escena
from sim.entorno import NOMBRES_MOTORES, RESOLUCION, ROBOT_TYPE, EntornoSoldadura, direccion_antorcha, \
    lerobot_a_rad, rad_a_lerobot

RAIZ = Path(__file__).resolve().parents[1]
MM = escena.MM
# Velocidad articular máxima planificada (rad/s). Los servos simulados saturan su par por encima de ~1 rad/s y se
# retrasan; con este límite el brazo sigue al objetivo y llega quieto al inicio del cordón.
V_MAX_ARTICULAR = 0.7
# Una demostración vale si la IK sigue la trayectoria con estos errores; si no, se planifica otra variante.
LIMITE_IK_MM = 0.5
LIMITE_IK_GRADOS = 0.5
MAX_INTENTOS = 5


@dataclass
class Guion:
    """Parámetros de una demostración (mm, s, grados)."""

    velocidad: float = sum(c.VELOCIDAD_OBJETIVO) / 2  # mm/s: el centro de la velocidad buena del contrato
    angulo_avance: float = 10.0  # empuje
    altura_aproximacion: float = 40.0  # mm por encima del inicio del cordón, a lo largo del eje de la antorcha
    t_aproximacion: float = 3.0
    t_bajada: float = 1.5
    t_espera: float = 0.4  # quieto sobre el inicio antes de apretar el gatillo
    t_subida: float = 1.2
    t_vuelta: float = 2.5
    t_final: float = 0.5  # quieto en reposo al terminar
    ruido: float = 1.0  # escala de la variabilidad humana (0 = guion exacto)
    # Amplitudes del ruido con ruido = 1 (desviación típica)
    ruido_lateral: float = 0.5  # mm
    ruido_vertical: float = 0.4  # mm
    ruido_velocidad: float = 0.08  # fracción
    ruido_angulo: float = 2.0  # grados
    ruido_duracion: float = 0.15  # fracción
    ruido_reposo: float = 4.0  # grados por articulación
    # Fallos a propósito (demostraciones malas para probar el filtro de calidad)
    paradas: tuple[tuple[float, float], ...] = ()  # (x_mm, segundos): quieto con el gatillo apretado
    desvio: tuple[float, float, float] | None = None  # (x_inicio, x_fin, mm): desplazamiento lateral


@dataclass
class Plan:
    """Trayectoria fotograma a fotograma: objetivos articulares (rad), gatillo, fase y punto de referencia."""

    q: list[np.ndarray] = field(default_factory=list)
    gatillo: list[bool] = field(default_factory=list)
    fase: list[str] = field(default_factory=list)
    referencia: list[np.ndarray | None] = field(default_factory=list)  # punto ideal (marco de la pieza, mm)
    error_ik: float = 0.0  # peor error de posición de la IK (mm)
    error_ik_ang: float = 0.0  # peor error angular de la IK (grados)

    def anadir(self, q, gatillo=False, fase="", referencia=None):
        self.q.append(np.array(q, dtype=float))
        self.gatillo.append(bool(gatillo))
        self.fase.append(fase)
        self.referencia.append(None if referencia is None else np.array(referencia, dtype=float))

    def __len__(self):
        return len(self.q)


def _minimo_tiron(s):
    """Perfil 0 → 1 de mínimo tirón (arranque y parada suaves)."""
    s = np.clip(s, 0.0, 1.0)
    return s ** 3 * (10 - 15 * s + 6 * s ** 2)


def _ruido_suave(rng, n, sigma_s, fps=c.FPS_DATASET):
    """Ruido gaussiano filtrado (escala temporal `sigma_s` segundos) con desviación típica 1."""
    if n == 0:
        return np.zeros(0)
    k = max(1, int(3 * sigma_s * fps))
    nucleo = np.exp(-0.5 * (np.arange(-k, k + 1) / (sigma_s * fps)) ** 2)
    blanco = rng.normal(size=n + 2 * k)
    r = np.convolve(blanco, nucleo / nucleo.sum(), mode="valid")[:n]
    return (r - r.mean()) / (r.std() + 1e-12)


def _desvio(desvio: tuple[float, float, float] | None, x: float, rampa: float = 3.0) -> float:
    """Desplazamiento lateral (mm) a propósito entre x_inicio y x_fin, con rampas suaves de `rampa` mm."""
    if desvio is None:
        return 0.0
    x0, x1, mm = desvio
    return float(mm * _minimo_tiron((x - x0 + rampa) / rampa) * (1.0 - _minimo_tiron((x - x1) / rampa)))


class Planificador:
    """Planifica demostraciones con la IK de la punta de la antorcha."""

    def __init__(self, entorno: EntornoSoldadura):
        self.ent = entorno
        self.cin = entorno.cin
        lo, hi = self.cin.rangos[:5, 0], self.cin.rangos[:5, 1]
        rng = np.random.default_rng(1234)
        self._semillas = [np.r_[rng.uniform(lo * 0.9, hi * 0.9), 0.0] for _ in range(40)]

    def _ik(self, p_pieza, d_pieza, q_ini):
        """IK de un punto y una dirección dados en el marco de la pieza."""
        R = escena.rotacion_pieza(self.ent.anclaje)
        p = escena.pieza_a_mesa(self.ent.anclaje, p_pieza) * MM
        return self.cin.inversa_pose(p, R @ d_pieza, q_ini)

    def ik_inicio(self, p_pieza, d_pieza, q_ref, comprobar=(), variantes=()):
        """IK del inicio desde muchas semillas y elección de la rama.

        Cada rama distinta se recorre por continuidad a lo largo de `comprobar` (pares punto, dirección en el marco
        de la pieza) y se prueban las `variantes` (índice en `comprobar`, punto, dirección, tolerancia en m)
        partiendo de la solución de ese índice. Se descartan las ramas que fallan y, entre las buenas, se prefiere
        la que más se aleja de los límites articulares y queda más cerca de `q_ref` (rad).
        """
        lo, hi = self.cin.rangos[:5, 0], self.cin.rangos[:5, 1]

        def holgura_de(q):
            return float(np.min(np.minimum(q[:5] - lo, hi - q[:5])))

        def vale(e, a, tol=5e-4):
            return e < tol and a < np.radians(0.5)

        ramas = []
        for s in [q_ref] + self._semillas:
            s = np.array(s, dtype=float)
            s[5] = q_ref[5]
            q, e, a = self._ik(p_pieza, d_pieza, s)
            if vale(e, a) and all(np.max(np.abs(q - r)) > 0.05 for r in ramas):
                ramas.append(q)
        mejor, mejor_coste = None, np.inf
        for q0 in ramas:
            holgura = holgura_de(q0)
            q, bien, cadena = q0, True, []
            for p, d in comprobar:
                q, e, a = self._ik(p, d, q)
                bien = bien and vale(e, a)
                cadena.append(q)
                holgura = min(holgura, holgura_de(q))
            for k, p, d, tol in variantes:
                if not bien:
                    break
                qv, e, a = self._ik(p, d, cadena[k] if cadena else q0)
                bien = vale(e, a, tol)
                holgura = min(holgura, holgura_de(qv))
            if not bien:
                continue
            coste = np.linalg.norm(q0[:5] - q_ref[:5]) - 4.0 * min(holgura, 0.3)
            if coste < mejor_coste:
                mejor, mejor_coste = q0, coste
        if mejor is None:
            raise RuntimeError(f"Sin solución de IK para el cordón del anclaje {self.ent.anclaje} "
                               f"({self.ent.tipo.value})")
        return mejor

    def planificar(self, q_reposo_lr, guion: Guion, rng: np.random.Generator) -> Plan:
        """Plan completo desde la postura `q_reposo_lr` (unidades de LeRobot) para la pieza colocada."""
        g, r = guion, guion.ruido
        fps = c.FPS_DATASET
        q0 = lerobot_a_rad(q_reposo_lr)

        def dur(t):
            return max(0.3, t * (1 + r * g.ruido_duracion * rng.normal()))

        trabajo = c.ANGULO_TRABAJO_OBJETIVO[self.ent.tipo.value]
        # Ángulos del operador para esta pasada (constantes + deriva suave durante el cordón)
        trabajo_0 = trabajo + r * g.ruido_angulo * rng.normal()
        avance_0 = g.angulo_avance + r * g.ruido_angulo * rng.normal()
        d_inicio = direccion_antorcha(trabajo_0, avance_0)
        z_punta = c.ALTURA_PUNTA
        inicio = np.array([0.0, 0.0, z_punta])
        plan = Plan()

        # Ramas de IK que aguantan todo el cordón con ángulos algo peores que los de esta pasada
        comprobar = [(np.array([x, 0.0, z_punta]), d_inicio) for x in np.linspace(0.0, c.LONGITUD_CORDON, 7)]
        # punto de aproximación (en el aire: basta con acercarse a 2 mm)
        variantes = [(0, inicio - g.altura_aproximacion * d_inicio, d_inicio, 2e-3)]
        for k in (0, 3, 6):
            for d_tr, d_av in ((2, 2), (-2, -2), (2, -2), (-2, 2)):  # margen para la deriva de ángulos
                variantes.append((k, comprobar[k][0], direccion_antorcha(trabajo_0 + d_tr, avance_0 + d_av),
                                  1e-3))
        q_ini = self.ik_inicio(inicio, d_inicio, q0, comprobar, variantes)
        pre = inicio - g.altura_aproximacion * d_inicio
        q_pre, e, a = self._ik(pre, d_inicio, q_ini)

        def dur_articular(t, q_a, q_b):
            # el perfil de mínimo tirón tiene un pico de velocidad de 1,875 veces la media
            return max(dur(t), 1.875 * np.max(np.abs(q_b[:5] - q_a[:5])) / V_MAX_ARTICULAR)

        # 1) Aproximación articular reposo → encima del inicio
        n = int(round(dur_articular(g.t_aproximacion, q0, q_pre) * fps))
        for k in range(n):
            s = _minimo_tiron((k + 1) / n)
            plan.anadir(q0 + s * (q_pre - q0), fase="aproximacion")

        # 2) Bajada cartesiana a lo largo del eje de la antorcha
        q = q_pre
        n = int(round(dur(g.t_bajada) * fps))
        for k in range(n):
            s = _minimo_tiron((k + 1) / n)
            q, e, a = self._ik(pre + s * (inicio - pre), d_inicio, q)
            if k == n - 1:  # en el aire da igual; al llegar al inicio, no
                plan.error_ik = max(plan.error_ik, e / MM)
            plan.anadir(q, fase="bajada")
        n = int(round(max(0.3, dur(g.t_espera)) * fps))
        for _ in range(n):
            plan.anadir(q, fase="espera", referencia=inicio)

        # 3) Cordón: velocidad casi constante con pequeñas variaciones suaves
        t_nominal = c.LONGITUD_CORDON / g.velocidad
        n_max = int(t_nominal * fps * 1.6) + 10
        v = g.velocidad * (1 + r * g.ruido_velocidad * _ruido_suave(rng, n_max, 1.5))
        dy = r * g.ruido_lateral * _ruido_suave(rng, n_max, 0.8)
        dz = r * g.ruido_vertical * _ruido_suave(rng, n_max, 0.8)
        dtr = r * g.ruido_angulo * 0.5 * _ruido_suave(rng, n_max, 2.0)
        dav = r * g.ruido_angulo * 0.5 * _ruido_suave(rng, n_max, 2.0)
        # Las desviaciones arrancan en cero (en 1 s) para no dar un salto al empezar el cordón
        entrada = _minimo_tiron(np.arange(n_max) / fps)
        dy, dz, dtr, dav = dy * entrada, dz * entrada, dtr * entrada, dav * entrada
        x = 0.0
        k = 0
        paradas = sorted(g.paradas)
        while x < c.LONGITUD_CORDON and k < n_max:
            # rampa de 0,3 s al arrancar para no dar un tirón
            rampa = min(1.0, (k + 1) / (0.3 * fps))
            x = min(c.LONGITUD_CORDON, x + v[k] * rampa / fps)
            d = direccion_antorcha(trabajo_0 + dtr[k], avance_0 + dav[k])
            p = np.array([x, dy[k] + _desvio(g.desvio, x), z_punta + dz[k]])
            q, e, a = self._ik(p, d, q)
            plan.error_ik = max(plan.error_ik, e / MM)
            plan.error_ik_ang = max(plan.error_ik_ang, np.degrees(a))
            plan.anadir(q, gatillo=True, fase="cordon", referencia=np.array([x, 0.0, z_punta]))
            while paradas and x >= paradas[0][0]:  # punto quemado a propósito
                for _ in range(int(round(paradas.pop(0)[1] * fps))):
                    plan.anadir(q, gatillo=True, fase="cordon", referencia=np.array([x, 0.0, z_punta]))
            k += 1
        fin = np.array([c.LONGITUD_CORDON, dy[k - 1], z_punta + dz[k - 1]])

        # 4) Subida a lo largo del eje
        n = int(round(dur(g.t_subida) * fps))
        arriba = fin - g.altura_aproximacion * d
        for k in range(n):
            s = _minimo_tiron((k + 1) / n)
            q, e, a = self._ik(fin + s * (arriba - fin), d, q)
            plan.anadir(q, fase="subida")

        # 5) Vuelta articular a un reposo (no exactamente el de salida)
        q_fin = q0.copy()
        q_fin[:5] += np.radians(r * g.ruido_reposo * 0.5 * rng.normal(size=5))
        q_sub = q
        n = int(round(dur_articular(g.t_vuelta, q_sub, q_fin) * fps))
        for k in range(n):
            s = _minimo_tiron((k + 1) / n)
            plan.anadir(q_sub + s * (q_fin - q_sub), fase="vuelta")
        for _ in range(int(round(g.t_final * fps))):
            plan.anadir(q_fin, fase="final")
        return plan


@dataclass
class ResultadoEpisodio:
    anclaje: str
    tipo: str
    fotogramas: int
    segundos: float
    error_max: float  # mm, distancia máxima de la punta al cordón (y, z - ALTURA_PUNTA) con gatillo
    error_medio: float
    lateral_max: float  # mm, |y| máximo con gatillo
    trabajo_medio: float
    avance_medio: float
    muestras: list = field(default_factory=list)
    # Filtro de calidad
    variante: str = "buena"
    semilla: int = 0
    nota: float | None = None
    aceptada: bool = True
    episodio: int | None = None  # índice en el dataset (None si se descartó)
    resultado: object = None  # lewelder.metricas.Resultado


def ejecutar(entorno: EntornoSoldadura, anclaje: str, tipo, guion: Guion, semilla: int = 0,
             al_fotograma=None) -> ResultadoEpisodio:
    """Ejecuta una demostración en el entorno. `al_fotograma(obs, accion_lr)` se llama antes de cada paso."""
    t0 = time.perf_counter()
    rng = np.random.default_rng(semilla)
    obs = entorno.reset(anclaje, tipo, semilla=semilla if guion.ruido > 0 else None)
    planificador = Planificador(entorno)
    motivo = ""
    for intento in range(MAX_INTENTOS):
        try:
            plan = planificador.planificar(entorno.estado(), guion, rng)
            if plan.error_ik < LIMITE_IK_MM and plan.error_ik_ang < LIMITE_IK_GRADOS:
                break
            motivo = f"error de IK {plan.error_ik:.1f} mm / {plan.error_ik_ang:.1f}°"
        except RuntimeError as e:
            motivo = str(e)
        rng = np.random.default_rng([semilla, intento + 1])  # otra variante de la misma demostración
    else:
        raise RuntimeError(f"No hay demostración válida en el anclaje {anclaje} ({tipo}): {motivo}")
    muestras, errores, laterales, trabajos, avances = [], [], [], [], []
    for q, gatillo in zip(plan.q, plan.gatillo):
        accion = rad_a_lerobot(q).astype(np.float32)
        if al_fotograma is not None:
            al_fotograma(obs, accion)
        obs = entorno.step(accion)
        m = entorno.muestra(gatillo=gatillo)
        muestras.append(m)
        if gatillo:
            errores.append(np.hypot(m.y, m.z - c.ALTURA_PUNTA))
            laterales.append(abs(m.y))
            trabajos.append(m.angulo_trabajo)
            avances.append(m.angulo_avance)
    return ResultadoEpisodio(anclaje, c.TipoPieza(tipo).value, len(plan), time.perf_counter() - t0,
                             float(np.max(errores)), float(np.mean(errores)), float(np.max(laterales)),
                             float(np.mean(trabajos)), float(np.mean(avances)), muestras)


# --- dataset ------------------------------------------------------------------------------------------------------
def caracteristicas(resolucion=RESOLUCION) -> dict:
    """Features del dataset, construidas como las de `lerobot-record` con el SO-101 seguidor real."""
    from lerobot.utils.feature_utils import hw_to_dataset_features

    ancho, alto = resolucion
    motores = dict.fromkeys(NOMBRES_MOTORES, float)
    camaras = {cam: (alto, ancho, 3) for cam in c.CAMARAS_POLITICA}
    return {**hw_to_dataset_features(motores, "action"),
            **hw_to_dataset_features({**motores, **camaras}, "observation")}


# --- filtro de calidad ("aprende del mejor") ---------------------------------------------------------------------
REINTENTOS_SEMILLA = 5  # posturas iniciales distintas antes de dar por imposible una demostración
UMBRAL_NOTA = 9.0  # nota mínima recomendada (nivel oficial, ±5 mm): las buenas sacan ~9,8 y las malas < 9
# Demostraciones malas a propósito: lo que haría un operador cansado o despistado con el brazo guía.
MALAS = {
    "temblorosa": {"ruido": 5.0},  # 2,5 mm de temblor lateral, ritmo irregular y ángulos que bailan
    "parada": {"paradas": ((40.0, 2.0), (80.0, 2.0))},  # dos veces quieto 2 s con el gatillo: puntos quemados
    "desvio": {"desvio": (40.0, 80.0, 7.5)},  # se sale 7,5 mm del cordón: hueco a ±5 mm
    "rapida": {"velocidad": 11.0},  # el doble de rápido de lo bueno
}


def guion_malo(guion: Guion, variante: str) -> Guion:
    """El guion con el fallo de `variante` (una de `MALAS`)."""
    return replace(guion, **MALAS[variante])


def puntuar(res: ResultadoEpisodio, nivel: str = c.NIVEL_JURADO):
    """Nota de la demostración con las mismas métricas que al alumno (punta con el gatillo del guion)."""
    from lewelder.metricas import evaluar_pasada

    return evaluar_pasada(res.muestras, res.tipo, nivel)


def trabajos(episodios: int, anclajes: list[str], tipos: list[str], malas: int = 0) -> list[tuple[str, str, str]]:
    """(anclaje, tipo, variante) de cada demostración: las buenas repartidas por igual entre las combinaciones y
    las malas intercaladas (una cada pocas buenas), rotando variantes y combinaciones."""
    combinaciones = list(itertools.product(anclajes, tipos))
    buenas = [(*combinaciones[i % len(combinaciones)], "buena") for i in range(episodios)]
    variantes = list(MALAS)
    malas_l = [(*combinaciones[(i * 3 + 1) % len(combinaciones)], variantes[i % len(variantes)])
               for i in range(malas)]
    if not malas_l:
        return buenas
    salida, paso = [], max(1, len(buenas) // len(malas_l))
    for i, b in enumerate(buenas):
        salida.append(b)
        if malas_l and (i + 1) % paso == 0:
            salida.append(malas_l.pop(0))
    return salida + malas_l


def grabar(salida: Path, repo_id: str, episodios: int, anclajes: list[str], tipos: list[str], guion: Guion,
           resolucion=RESOLUCION, semilla: int = 0, sobrescribir: bool = False, umbral_nota: float | None = None,
           malas: int = 0, nivel: str = c.NIVEL_JURADO, sombras: bool = True):
    """Graba `episodios` demostraciones repartidas por igual entre las combinaciones anclaje x tipo (más `malas`
    malas a propósito). Cada una se puntúa y, con `umbral_nota`, solo se guarda si su nota llega. Devuelve todas
    (también las descartadas) y escribe sus notas en `<salida>/notas.json`."""
    from lerobot.datasets.lerobot_dataset import LeRobotDataset

    salida = Path(salida)
    if salida.exists():
        if not sobrescribir:
            raise FileExistsError(f"{salida} ya existe (usa --sobrescribir)")
        shutil.rmtree(salida)
    ds = LeRobotDataset.create(repo_id=repo_id, fps=c.FPS_DATASET, features=caracteristicas(resolucion),
                               root=salida, robot_type=ROBOT_TYPE, use_videos=True, image_writer_threads=4)
    entorno = EntornoSoldadura(resolucion=resolucion, render=True, sombras=sombras)
    resultados = []
    try:
        for i, (anclaje, tipo, variante) in enumerate(trabajos(episodios, anclajes, tipos, malas)):
            tarea = c.instruccion_soldar(tipo, anclaje)

            def guardar(obs, accion):
                ds.add_frame({**obs, "action": accion, "task": tarea})

            g = guion if variante == "buena" else guion_malo(guion, variante)
            # Algunas posturas iniciales aleatorias no tienen solución de IK para todo el cordón (sobre todo la T en
            # el anclaje A, al borde del alcance): se prueba con otra semilla, que cambia la postura inicial. Es
            # seguro reintentar: `ejecutar` planifica antes de grabar ningún fotograma.
            for reintento in range(REINTENTOS_SEMILLA):
                semilla_i = semilla + i + 100_000 * reintento
                try:
                    res = ejecutar(entorno, anclaje, tipo, g, semilla=semilla_i, al_fotograma=guardar)
                    break
                except RuntimeError as e:
                    print(f"demo {i:3d}  {tarea:40s} sin solución con la semilla {semilla_i}: {e}", flush=True)
            else:
                raise RuntimeError(f"Demostración {i} sin solución tras {REINTENTOS_SEMILLA} semillas")
            res.variante, res.semilla = variante, semilla_i
            res.resultado = puntuar(res, nivel)
            res.nota = res.resultado.nota
            res.aceptada = umbral_nota is None or res.nota >= umbral_nota
            t1 = time.perf_counter()
            if res.aceptada:
                res.episodio = ds.num_episodes
                ds.save_episode(parallel_encoding=False)  # sin fork: el render EGL usa hilos
            else:
                ds.clear_episode_buffer()
            res.segundos += time.perf_counter() - t1
            resultados.append(res)
            print(f"demo {i:3d}  {tarea:40s} {variante:10s} nota {res.nota:4.1f} "
                  f"{'GUARDADA' if res.aceptada else 'descartada':10s} {res.fotogramas:5d} fotogramas  "
                  f"{res.segundos:6.1f} s  error máx {res.error_max:.2f} mm", flush=True)
    finally:
        ds.finalize()
        entorno.cerrar()
        guardar_notas(salida, resultados, umbral_nota, nivel)
    return resultados


def guardar_notas(salida: Path, resultados: list[ResultadoEpisodio], umbral_nota: float | None,
                  nivel: str = c.NIVEL_JURADO) -> Path:
    """`<salida>/notas.json`: nota de cada demostración y si entró en el dataset (y en qué episodio)."""
    ruta = Path(salida) / "notas.json"
    ruta.parent.mkdir(parents=True, exist_ok=True)
    demos = []
    for i, r in enumerate(resultados):
        res = r.resultado
        demos.append({
            "demo": i, "episodio": r.episodio, "aceptada": r.aceptada, "anclaje": r.anclaje, "tipo": r.tipo,
            "tarea": c.instruccion_soldar(r.tipo, r.anclaje), "variante": r.variante, "semilla": r.semilla,
            "nota": r.nota,
            "cobertura_pct": res.cobertura_pct if res else None,
            "n_quemados": res.n_quemados if res else None,
            "desvio_medio_mm": res.desvio_medio_mm if res else None,
            "velocidad_media": res.velocidad_media if res else None,
            "huecos": res.huecos if res else None,
            "error_max_mm": round(r.error_max, 3),
        })
    descartadas = [d for d in demos if not d["aceptada"]]
    ruta.write_text(json.dumps({
        "umbral_nota": umbral_nota, "nivel": nivel, "total": len(demos),
        "guardadas": len(demos) - len(descartadas), "descartadas": len(descartadas),
        "malas_descartadas": sum(d["variante"] != "buena" for d in descartadas),
        "buenas_descartadas": sum(d["variante"] == "buena" for d in descartadas),
        "demostraciones": demos,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    return ruta


def main(argv=None):
    import sys

    argv = sys.argv[1:] if argv is None else list(argv)
    if argv and argv[0] == "montaje":  # v2: python -m sim.demostraciones montaje --por-orden 4 ...
        from sim.demos_montaje import main as main_montaje

        return main_montaje(argv[1:])
    p = argparse.ArgumentParser(description="Graba demostraciones de soldadura simuladas en un LeRobotDataset "
                                            "(v1; para la v2 de montaje: `python -m sim.demostraciones montaje -h`).")
    p.add_argument("--episodios", type=int, default=8, help="demostraciones buenas")
    p.add_argument("--anclajes", default=",".join(c.ANCLAJES), help="p. ej. A,B,C,D")
    p.add_argument("--tipos", default="recta,t", help="recta,t")
    p.add_argument("--salida", default=str(RAIZ / "datos" / "lewelder_sim"))
    p.add_argument("--repo-id", default="local/lewelder_sim")
    p.add_argument("--velocidad", type=float, default=Guion.velocidad, help="mm/s a lo largo del cordón")
    p.add_argument("--ruido", type=float, default=1.0, help="escala de la variabilidad humana (0 = sin ruido)")
    p.add_argument("--resolucion", default=f"{RESOLUCION[0]}x{RESOLUCION[1]}", help="ANCHOxALTO")
    p.add_argument("--semilla", type=int, default=0)
    p.add_argument("--umbral-nota", type=float, default=None,
                   help=f"solo entran las demostraciones con esta nota o más (recomendado {UMBRAL_NOTA}); "
                        "sin él entran todas, pero se puntúan igual")
    p.add_argument("--nivel", choices=list(c.TOLERANCIAS), default=c.NIVEL_JURADO, help="tolerancia de la nota")
    p.add_argument("--incluir-malas", type=int, nargs="?", const=len(MALAS), default=0, metavar="N",
                   help=f"graba además N demostraciones malas a propósito ({', '.join(MALAS)}); sin N, una de cada")
    p.add_argument("--sin-sombras", action="store_true", help="render sin sombras (el doble de rápido)")
    p.add_argument("--sobrescribir", action="store_true")
    a = p.parse_args(argv)
    resolucion = tuple(int(v) for v in a.resolucion.lower().split("x"))
    guion = Guion(velocidad=a.velocidad, ruido=a.ruido)
    t0 = time.perf_counter()
    res = grabar(Path(a.salida), a.repo_id, a.episodios, a.anclajes.split(","), a.tipos.split(","), guion,
                 resolucion, a.semilla, a.sobrescribir, a.umbral_nota, a.incluir_malas, a.nivel,
                 sombras=not a.sin_sombras)
    total = time.perf_counter() - t0
    descartadas = [r for r in res if not r.aceptada]
    print(f"\n{len(res)} demostraciones en {total:.0f} s ({total / max(1, len(res)):.1f} s cada una) → {a.salida}")
    print(f"filtro (nota >= {a.umbral_nota}): {len(res) - len(descartadas)} guardadas, {len(descartadas)} "
          f"descartadas ({sum(r.variante != 'buena' for r in descartadas)} de {a.incluir_malas} malas a propósito, "
          f"{sum(r.variante == 'buena' for r in descartadas)} buenas); notas en {Path(a.salida) / 'notas.json'}")


if __name__ == "__main__":
    main()
