"""Maqueta de Garbi: la demo del hackathon como animación forzada, sin lógica, para ver la solución que queremos.

    python -m garbi.maqueta --salida salidas/garbi_maqueta.mp4      # vídeo con el panel de la app
    (en el visor: Enter; en Windows suenan los sonidos de Garbi)

Todo está fijado en una línea de tiempo (`construir`): dónde está el taladro, la postura del robot, la aspiradora, el
estado que muestra la app (luz de color), lo que dice Garbi y sus sonidos. Las posturas se calculan una vez con la
cinemática del montaje lateral (`garbi.lateral`), solo para que sean reales; al reproducir, el robot va de una a otra
con suavidad. No decide nada.

Sesión (la demo: `.plans/aspira/plan-tecnico.md` §0-§1 y M4 de `.plans/aspira/especificacion-tecnica.md`):
- 5 intentos seguidos del ciclo de un agujero, en 5 sitios distintos de la madera (~30 s cada uno):
  1. entras con el taladro: Garbi sale del aparcado y te sigue a ~80 mm y 45 mm por encima;
  2. buscas el punto;
  3. te quedas quieto: preapunto (30 mm más atrás y 20 mm más arriba que al acompañar);
  4. apoyas la broca: baja, entra a 30 mm con la boca a 15° y enciende la aspiradora;
  5. taladras ~6 s: sale viruta y se aspira;
  6. levantas: vuelve a la espera;
  7. sales con el taladro y Garbi espera 1 s;
  8. se coloca sobre el agujero (boca a 60°, 35 mm, 30 mm de altura) y limpia la zona 5 s (lo hará ACT);
  9. revisa, asiente y aparca (si el taladro ya vuelve a entrar, va directo a seguirlo).
- Cierre: una pasada de limpieza por toda la madera en zigzag de 4 carriles, con la boca a 45-60° (no puntúa).
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import mujoco
import numpy as np

import garbi.lateral as L
from garbi import contrato as g
from garbi.interactivo import ALTURA_ESPERA, DIST_ESPERA, INCLINACIONES_ESPERA
from garbi.mundo import MundoGarbi

TABLA = g.PoseTabla(360.0, 0.0, 0.0)
# Los 5 sitios de los intentos (marco de la madera, mm), repartidos para que cada uno quede lejos del anterior
AGUJEROS = ((-30.0, 60.0), (40.0, -70.0), (-40.0, -110.0), (50.0, 100.0), (0.0, 0.0))
AIRE = 50.0  # mm de la punta sobre la madera mientras mueves el taladro
T_TALADRAR = 6.0  # s taladrando cada agujero
T_ACT = 5.0  # s que dura el episodio de ACT (limpiar la zona)
INCLINACIONES_TRABAJO = (15.0, 20.0, 25.0)  # boca al acompañar y en el preapunto (15° si llega)
SUBIDA_PREAPUNTO = 20.0  # mm más arriba que al acompañar
# Centro de la boca sobre la madera al acompañar: con la boquilla de Ø30 a 15° el borde de abajo queda a ≥ 3 mm de la
# superficie (guardia de M4); con `L.ALTURA_BOCA` (15 mm) quedaría a 0,5 mm.
ALTURA_TRABAJO = 18.0
DIST_PARTIDA, ALTURA_PARTIDA = 35.0, 30.0  # posición de partida de ACT sobre el agujero
INCLINACIONES_PARTIDA = (60.0, 55.0, 50.0)
CARRILES_CIERRE = (285.0, 335.0, 385.0, 435.0)  # x (mm, mesa) de los 4 carriles de la pasada final
VELOCIDAD_CIERRE = 40.0  # mm/s
INCLINACIONES_CIERRE = (60.0, 45.0)
INCLINACIONES_ACT = (60.0, 45.0)  # sin los 35° de `INCLINACIONES_LIMPIEZA`: el borde de la boca quedaría a < 3 mm

# Luz de estado de la app: nombre → (color RGB, texto)
ESTADOS = {
    "reposo": ((150, 150, 150), "en reposo"),
    "sigue": ((40, 120, 255), "te sigo"),
    "preapunto": ((120, 90, 255), "preparado"),
    "aspira": ((40, 200, 90), "aspirando"),
    "va": ((0, 170, 170), "voy a limpiar"),
    "limpia": ((40, 200, 90), "limpiando (ACT)"),
    "revisa": ((0, 200, 220), "revisando"),
    "hecho": ((40, 200, 90), "limpio"),
    "cierre": ((40, 200, 90), "pasada final"),
}
# Sonidos de Garbi: nombre → lista de (frecuencia Hz, ms)
SONIDOS = {
    "hola": [(660, 90), (880, 120)],
    "acerca": [(880, 70), (880, 70)],
    "limpia": [(700, 80), (1050, 110)],
    "ok": [(660, 90), (880, 90), (1320, 160)],
}


@dataclass
class Fotograma:
    q: np.ndarray  # postura del robot (unidades de LeRobot)
    taladro: np.ndarray | None  # punta de la broca (mm) o None si no está
    aspiradora: bool
    estado: str  # luz de la app (clave de ESTADOS)
    paso: str
    detalle: str
    dice: str | None = None  # lo que dice Garbi
    sonido: str | None = None  # sonido de Garbi (solo en el primer fotograma del tramo)
    taladrar: bool = False  # se hace el agujero (primer fotograma del tramo)
    serrin: tuple | None = None  # (x, y, n, radio): sale viruta (primer fotograma del tramo)


def _suave(f):
    return 0.5 - 0.5 * np.cos(np.pi * f)


class Maqueta:
    def __init__(self, mundo: MundoGarbi | None = None):
        self.m = mundo or MundoGarbi(render=False, montaje="lateral")
        self.c = L.ControlLateral(self.m)
        self.fotogramas: list[Fotograma] = []
        self.sin_postura: list[str] = []  # posturas que la cinemática no resolvió (se queda en la anterior)
        self._q = L.APARCADO.copy()
        self._taladro = None

    # --- posturas (se calculan una vez) ---------------------------------------------------------------------
    def _con(self, inclinaciones, funcion, nombre=""):
        anterior = L.INCLINACIONES
        L.INCLINACIONES = inclinaciones
        try:
            r = funcion()
        finally:
            L.INCLINACIONES = anterior
        if r is None:
            self.sin_postura.append(nombre)
            return self._q
        return self.c.a_lerobot(r[0])

    def _junto(self, P, distancia, altura, inclinaciones, nombre, atras=0.0, subida=0.0):
        return self._con(inclinaciones, lambda: self.c._postura(
            self.c._junto_a(P, distancia, altura, atras=atras, subida=subida)), nombre)

    def espera(self, P):
        """SEGUIR: boca a `DIST_ESPERA` de la broca y `ALTURA_ESPERA` sobre la madera."""
        return self._junto(P, DIST_ESPERA, ALTURA_ESPERA, INCLINACIONES_ESPERA, "espera")

    def preapunto(self, P):
        """PREAPUNTO: `ATRAS_PREAPUNTO` más atrás y `SUBIDA_PREAPUNTO` más arriba que al acompañar."""
        return self._junto(P, L.DISTANCIA_BROCA, ALTURA_TRABAJO, INCLINACIONES_TRABAJO, "preapunto",
                           atras=L.ATRAS_PREAPUNTO, subida=SUBIDA_PREAPUNTO)

    def bajar(self, P):
        """Primera fase de la entrada (y la salida): a la altura de trabajo, todavía separada."""
        return self._junto(P, L.DISTANCIA_BROCA, ALTURA_TRABAJO, INCLINACIONES_TRABAJO, "bajar",
                           atras=L.ATRAS_PREAPUNTO)

    def acompanar(self, P):
        """ACOMPAÑAR: boca a `DISTANCIA_BROCA` de la broca, a 15°."""
        return self._junto(P, L.DISTANCIA_BROCA, ALTURA_TRABAJO, INCLINACIONES_TRABAJO, "acompañar")

    def partida(self, P):
        """IR A LIMPIAR: posición de partida de ACT sobre el agujero."""
        return self._junto(P, DIST_PARTIDA, ALTURA_PARTIDA, INCLINACIONES_PARTIDA, "partida")

    def revisar(self, P):
        """REVISAR: boca alta sobre el agujero, mirándolo: la cámara comprueba que está limpio."""
        return self._junto(P, 45.0, 55.0, (45.0, 60.0, 35.0), "revisar")

    def _limpiezas(self, puntos, inclinaciones, nombre):
        """Postura de limpieza de cada punto (el eje de la boca corta la madera en él); salta las que no llegan."""
        anterior = L.INCLINACIONES
        L.INCLINACIONES = inclinaciones
        try:
            out = []
            for p in puntos:
                r = self.c.limpiar(np.asarray(p, float))
                if r is None:
                    self.sin_postura.append(nombre)
                else:
                    out.append((p, self.c.a_lerobot(r[0])))
            return out
        finally:
            L.INCLINACIONES = anterior

    def barrido(self, centro):
        """Lo que hará ACT en la maqueta: un zigzag corto por la zona del agujero, con la boca picada."""
        puntos = [p for p, _ in self.c.barrido(centro, radio=22.0, paso=11.0)]
        return [q for _, q in self._limpiezas(puntos, INCLINACIONES_ACT, "ACT")]

    def pasada_final(self):
        """Zigzag de 4 carriles a lo largo de la madera, con puntos cada ~20 mm: [(punto, postura)]."""
        cara, margen = g.ALTURA_CARA_TABLA, 20.0
        y0, y1 = TABLA.y - g.TABLA_TAMANO[1] / 2 + margen, TABLA.y + g.TABLA_TAMANO[1] / 2 - margen
        ys = np.linspace(y0, y1, int(round((y1 - y0) / 20.0)) + 1)
        puntos = [np.array([x, y, cara]) for i, x in enumerate(CARRILES_CIERRE) for y in (ys if i % 2 == 0 else ys[::-1])]
        return self._limpiezas(puntos, INCLINACIONES_CIERRE, "cierre")

    # --- línea de tiempo ------------------------------------------------------------------------------------
    def tramo(self, segundos, paso, detalle, estado, q=None, taladro=None, aspiradora=False, dice=None, sonido=None,
              taladrar=False, serrin=None, respirar=False):
        """`segundos` de animación. El robot va de su postura actual a `q`; el taladro, de donde estaba a `taladro`
        ("fuera" lo quita)."""
        n = max(1, int(round(segundos * g.FPS)))
        q0, q1 = self._q.copy(), (self._q if q is None else np.asarray(q, float))
        t0 = self._taladro
        t1 = None if isinstance(taladro, str) else (t0 if taladro is None else np.asarray(taladro, float))
        for k in range(1, n + 1):
            f = _suave(k / n)
            q = q0 + (q1 - q0) * f
            if respirar:  # micro-movimiento en reposo: una «respiración» lenta
                fase = 2 * np.pi * (len(self.fotogramas) / g.FPS) / 4.0
                q = q + np.array([0.0, 1.5 * np.sin(fase), -1.0 * np.sin(fase), 2.0 * np.sin(fase), 0.0, 0.0])
            pt = None if (t0 is None or t1 is None) else t0 + (t1 - t0) * f
            if t0 is None and t1 is not None:
                pt = t1
            self.fotogramas.append(Fotograma(q, pt, aspiradora, estado, paso, detalle, dice,
                                             sonido if k == 1 else None, taladrar and k == 1,
                                             serrin if k == 1 else None))
        self._q, self._taladro = q1.copy(), t1

    def asentir(self, paso, detalle, dice):
        arriba = self._q.copy()
        asiente = arriba + np.array([0, 0, 0, 10.0, 0, 0])
        for i, q in enumerate((asiente, arriba, asiente, arriba)):
            self.tramo(0.3, paso, detalle, "hecho", q=q, dice=dice, sonido="ok" if i == 0 else None)

    def ciclo(self, n: int, P: np.ndarray, sigue_al_siguiente: bool) -> None:
        """Un intento: el ciclo completo de un agujero con la punta en P (mm, mesa, en la cara de la madera)."""
        cara = g.ALTURA_CARA_TABLA
        aire = lambda p: np.asarray(p, float) + [0, 0, AIRE]
        entrada = np.array([g.PERSONA_X + 60, 0.5 * P[1] + 40.0, cara + AIRE + 40])
        t = f"Intento {n}/{len(AGUJEROS)}"
        lejos, cerca = P + [55, 45, 0], P + [-25, -30, 0]

        # 1 · entra el taladro: Garbi sale del aparcado y lo sigue
        self.tramo(0.01, f"{t} · 1. Entra el taladro", "", "sigue", taladro=entrada)
        self.tramo(2.2, f"{t} · 1. Entra el taladro", "Garbi sale del aparcado y te sigue a 80 mm y 45 mm por encima.",
                   "sigue", q=self.espera(lejos), taladro=aire(lejos), sonido="hola")
        # 2 · buscas el punto
        self.tramo(1.4, f"{t} · 2. Buscas el punto", "La broca en el aire: te sigue sin estorbar.", "sigue",
                   q=self.espera(cerca), taladro=aire(cerca))
        self.tramo(1.3, f"{t} · 2. Buscas el punto", "La broca en el aire: te sigue sin estorbar.", "sigue",
                   q=self.espera(P), taladro=aire(P))
        # 3 · quieto: preapunto
        self.tramo(0.4, f"{t} · 3. Quieto", "La broca quieta 0,3 s.", "sigue")
        self.tramo(1.0, f"{t} · 3. Preapunto", "30 mm más atrás y 20 mm más arriba: la cámara de la muñeca ve la broca.",
                   "preapunto", q=self.preapunto(P))
        # 4 · apoyas la broca: baja y entra
        self.tramo(0.6, f"{t} · 4. Apoyas la broca", "La punta toca la madera.", "preapunto", taladro=P)
        self.tramo(0.6, f"{t} · 4. Se acerca", "Baja a la altura de trabajo.", "aspira", q=self.bajar(P),
                   aspiradora=True, sonido="acerca")
        self.tramo(0.7, f"{t} · 4. Se acerca", "Entra a 30 mm de la broca, boca a 15°. Aspiradora encendida.", "aspira",
                   q=self.acompanar(P), aspiradora=True)
        # 5 · taladras: sale viruta y se aspira
        for k in range(int(round(T_TALADRAR / 0.5))):
            self.tramo(0.5, f"{t} · 5. Taladras", "Garbi quieto junto a la broca, aspirando la viruta que sale.",
                       "aspira", aspiradora=True, taladrar=(k == 0), serrin=(P[0], P[1], 4, g.RADIO_VIRUTA_MAX))
        # 6 · levantas: vuelve a la espera
        self.tramo(0.5, f"{t} · 6. Levantas la broca", "Garbi se separa.", "sigue", q=self.bajar(P), taladro=aire(P))
        self.tramo(0.7, f"{t} · 6. Levantas la broca", "Vuelve a la distancia de espera.", "sigue", q=self.espera(P))
        # 7 · sales con el taladro; espera 1 s
        self.tramo(1.4, f"{t} · 7. Sales con el taladro", "Sales de la zona de trabajo.", "sigue", taladro=entrada)
        self.tramo(0.01, f"{t} · 7. Sales con el taladro", "", "sigue", taladro="fuera")
        self.tramo(1.0, f"{t} · 7. Sales con el taladro", "Garbi espera 1 s.", "sigue")
        # 8 · se coloca sobre el agujero y ACT limpia la zona
        self.tramo(1.3, f"{t} · 8. Va a limpiar", "Posición de partida: boca a 60°, 35 mm del agujero, 30 mm de alto.",
                   "va", q=self.partida(P), sonido="limpia")
        poses = self.barrido(P[:2])
        primero = 0.8
        dt = (T_ACT - primero) / max(1, len(poses) - 1)
        for i, q in enumerate(poses):
            self.tramo(primero if i == 0 else dt, f"{t} · ACT · limpia la zona",
                       f"El modelo limpia la zona del agujero ({T_ACT:.0f} s).", "limpia", q=q, aspiradora=True)
        # 9 · revisa, asiente y aparca
        self.tramo(1.0, f"{t} · 9. Revisa", "La cámara comprueba que la zona está limpia.", "revisa",
                   q=self.revisar(P))
        self.asentir(f"{t} · 9. Limpio: asiente", "Zona limpia.", "Limpio.")
        if sigue_al_siguiente:  # el taladro vuelve a entrar mientras aparca: no llega a aparcar
            self.tramo(0.8, f"{t} · 9. Aparca", "Ya entra el taladro: va a seguirlo.", "reposo",
                       q=(self._q + L.APARCADO) / 2)
        else:
            self.tramo(1.6, f"{t} · 9. Aparca", "Aspiradora apagada.", "reposo", q=L.APARCADO)
            self.tramo(0.6, f"{t} · 9. Aparca", "Garbi espera, respirando.", "reposo", respirar=True)

    def construir(self) -> list[Fotograma]:
        self.fotogramas, self.sin_postura, self._q, self._taladro = [], [], L.APARCADO.copy(), None
        cara = g.ALTURA_CARA_TABLA
        A = [np.array([*TABLA.a_mesa(np.array(a)), cara]) for a in AGUJEROS]

        self.tramo(2.0, "Reposo", "Garbi espera aparcado, respirando.", "reposo", respirar=True)
        for n, P in enumerate(A, start=1):
            self.ciclo(n, P, sigue_al_siguiente=n in (2, 4))  # en el 2 y el 4 el taladro entra mientras aparca

        # cierre: pasada por toda la madera
        titulo = "Cierre: pasada por toda la madera (no puntúa)"
        pasada = self.pasada_final()
        self.tramo(1.5, titulo, "Zigzag de 4 carriles con la boca a 45-60°.", "cierre", q=pasada[0][1],
                   aspiradora=True, sonido="limpia")
        for (a, _), (b, q) in zip(pasada, pasada[1:]):
            self.tramo(float(np.linalg.norm(b - a)) / VELOCIDAD_CIERRE, titulo,
                       "Zigzag de 4 carriles con la boca a 45-60°, a 40 mm/s.", "cierre", q=q, aspiradora=True)
        self.tramo(1.0, titulo, "Pasada terminada.", "revisa", q=self.revisar(A[-1]))
        self.asentir("Fin: todo limpio", "Gesto de hecho.", "Todo limpio.")
        self.tramo(1.8, "Fin: aparca", "Aspiradora apagada.", "reposo", q=L.APARCADO)
        self.tramo(2.0, "Fin: en reposo", "Garbi espera, respirando.", "reposo", respirar=True)
        return self.fotogramas

    # --- reproducir -----------------------------------------------------------------------------------------
    def reproducir(self, al_fotograma=None):
        """Pone el mundo en cada fotograma (sin física: el robot va exactamente a la postura); la aspiración recoge la
        viruta por donde pasa la boca."""
        m = self.m
        m.reset(0, tabla=TABLA, q_inicial=L.APARCADO)
        mano_id = m.modelo.body_mocapid[m.modelo.body("mano_libre").id]
        m.datos.mocap_pos[mano_id] = [0, 0, -2]  # la otra mano no sale en la demo
        fotos = self.fotogramas or self.construir()
        for k, f in enumerate(fotos):
            m.reset_robot(f.q)
            if f.taladro is None:
                if m.juez.taladro_visible:
                    m.quitar_taladro()
            else:
                m.poner_taladro(*f.taladro)
            if f.taladrar:
                m.taladrar()
            if f.serrin is not None:
                m.tirar_serrin(*f.serrin)
            m.aspiradora = f.aspiradora
            mujoco.mj_forward(m.modelo, m.datos)
            if f.aspiradora:
                m._aspirar()
            m.t = (k + 1) / g.FPS
            if al_fotograma is not None:
                al_fotograma(f)


def panel_app(f: Fotograma, ancho: int, alto: int, recogidas: int) -> np.ndarray:
    """Maqueta del panel de la app: luz de estado, aspiradora y lo que dice Garbi."""
    import cv2

    from garbi.video import _ascii

    p = np.full((alto, ancho, 3), 245, np.uint8)
    color, texto = ESTADOS[f.estado]
    cv2.circle(p, (40, alto // 2), 24, color[::-1], -1)
    fu = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(p, _ascii(f"Garbi: {texto}"), (80, alto // 2 - 6), fu, 0.8, (40, 40, 40), 2, cv2.LINE_AA)
    cv2.putText(p, _ascii("aspiradora " + ("encendida" if f.aspiradora else "apagada") + f" - viruta recogida {recogidas}"),
                (80, alto // 2 + 22), fu, 0.5, (90, 90, 90), 1, cv2.LINE_AA)
    if f.dice:
        cv2.putText(p, _ascii(f"Garbi: \"{f.dice}\""), (ancho // 2, alto // 2 + 10), fu, 0.65, (20, 110, 40), 2,
                    cv2.LINE_AA)
    return p


def video(salida: Path, cada: int = 2, vista: str = "vista_cerca") -> Path:
    import cv2

    from garbi.video import _ascii

    m = MundoGarbi(render=True, montaje="lateral")
    maq = Maqueta(m)
    maq.construir()
    vw = [None]
    cuenta = [0]
    sonando = [None, 0]

    def escribir(f):
        cuenta[0] += 1
        if f.sonido:
            sonando[0], sonando[1] = f.sonido, int(0.8 * g.FPS)
        sonando[1] -= 1
        if cuenta[0] % cada:
            return
        obs = m.imagen(vista, (960, 720))
        arriba, robot = m.imagen("top", (480, 360)), m.imagen("wrist", (480, 360))
        lienzo = np.full((720 + 150, 1440, 3), 30, np.uint8)
        lienzo[:720, :960], lienzo[:360, 960:], lienzo[360:720, 960:] = obs, arriba, robot
        lienzo = cv2.cvtColor(lienzo, cv2.COLOR_RGB2BGR)
        fu = cv2.FONT_HERSHEY_SIMPLEX
        cv2.putText(lienzo, _ascii(f"{f.paso}   t = {m.t:5.1f} s"), (16, 40), fu, 0.8, (0, 0, 0), 4, cv2.LINE_AA)
        cv2.putText(lienzo, _ascii(f"{f.paso}   t = {m.t:5.1f} s"), (16, 40), fu, 0.8, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(lienzo, _ascii(f.detalle), (16, 72), fu, 0.6, (0, 0, 0), 3, cv2.LINE_AA)
        cv2.putText(lienzo, _ascii(f.detalle), (16, 72), fu, 0.6, (230, 230, 200), 1, cv2.LINE_AA)
        if sonando[1] > 0:
            cv2.putText(lienzo, _ascii(f"[sonido: {sonando[0]}]"), (760, 100), fu, 0.7, (0, 0, 0), 4, cv2.LINE_AA)
            cv2.putText(lienzo, _ascii(f"[sonido: {sonando[0]}]"), (760, 100), fu, 0.7, (120, 230, 255), 2, cv2.LINE_AA)
        lienzo[720:, :] = panel_app(f, 1440, 150, m.recogidas)
        if vw[0] is None:
            salida.parent.mkdir(parents=True, exist_ok=True)
            vw[0] = cv2.VideoWriter(str(salida), cv2.VideoWriter_fourcc(*"mp4v"), g.FPS / cada,
                                    (lienzo.shape[1], lienzo.shape[0]))
        vw[0].write(lienzo)

    maq.reproducir(escribir)
    vw[0].release()
    return salida


def main(argv=None) -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--salida", type=Path, default=Path("salidas/garbi_maqueta.mp4"))
    a = p.parse_args(argv)
    print("vídeo:", video(a.salida))


if __name__ == "__main__":
    main()
