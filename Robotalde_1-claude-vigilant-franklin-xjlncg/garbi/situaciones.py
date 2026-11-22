"""Catálogo de situaciones de Garbi en el área de trabajo del hackathon, forzadas en el simulador (sin aprendizaje),
con el montaje lateral: boquilla y tubo por el costado derecho, muñeca fija y cámara oficial en la muñeca.

    python -m garbi.situaciones            # imágenes en .plans/aspira/situaciones/ y tabla de posturas

Cada situación fija la escena (madera, taladro, viruta) y la postura exacta del robot que le corresponde, y la dibuja
desde tres sitios: un observador, la cámara de arriba y la cámara de la muñeca. La descripción de cada una está en
.plans/aspira/situaciones.md.
"""
from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import mujoco
import numpy as np

from garbi import contrato as g
from garbi.lateral import APARCADO, ControlLateral
from garbi.mundo import MundoGarbi

RAIZ = Path(__file__).resolve().parents[1]
SALIDA = RAIZ / ".plans" / "aspira" / "situaciones"
TABLA_TRABAJO = g.PoseTabla(360.0, 0.0, 0.0)
PUNTO_TALADRO = np.array([-20.0, 40.0])  # en el marco de la madera: a ~340 mm del robot
TOTAL = 13


@dataclass
class Situacion:
    numero: int
    nombre: str
    vista: str
    estado: str
    aspiradora: bool
    resumen: str
    q: np.ndarray = field(default_factory=lambda: APARCADO.copy())
    boca: np.ndarray | None = None
    inclinacion: float | None = None
    holgura: float | None = None
    ve_boca: bool | None = None
    ve_broca: bool | None = None


def _ascii(t: str) -> str:
    t = t.replace("«", '"').replace("»", '"').replace("→", "->").replace("·", "-").replace("°", " grados")
    return unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode()


class Simulador:
    def __init__(self, mundo: MundoGarbi | None = None):
        self.m = mundo or MundoGarbi(render=True, montaje="lateral")
        self.c = ControlLateral(self.m)

    def escena(self, tabla=TABLA_TRABAJO, taladro=None, inclinacion: float = 0.0):
        self.m.reset(0, tabla=tabla, q_inicial=APARCADO)
        if taladro is not None:
            self.m.poner_taladro(taladro[0], taladro[1], inclinacion=inclinacion, rumbo=0.0)

    def punta(self, p_tabla=PUNTO_TALADRO, tabla=TABLA_TRABAJO) -> np.ndarray:
        p = tabla.a_mesa(np.asarray(p_tabla, float))
        return np.array([p[0], p[1], g.ALTURA_CARA_TABLA])

    def postura(self, resultado) -> tuple[np.ndarray, float | None]:
        """(q en unidades de LeRobot, inclinación) de un resultado del control; aparcado si no hay solución."""
        if resultado is None:
            return APARCADO.copy(), None
        q4, inc = resultado
        return self.c.a_lerobot(q4), inc

    def poner(self, s: Situacion, taladro_P=None) -> Situacion:
        self.m.reset_robot(s.q)
        mujoco.mj_forward(self.m.modelo, self.m.datos)
        from sim.entorno import lerobot_a_rad

        q4 = lerobot_a_rad(s.q)[:4]
        if not np.allclose(s.q, APARCADO):
            b, e = self.c.boca(q4)
            s.boca, s.inclinacion = b, self.c.inclinacion(e)
            s.ve_boca = self.c.ve(q4, b - e * 5, [self.m.modelo.geom("boca_tubo").id])
        if taladro_P is not None:
            s.holgura = self.c.holgura(q4, taladro_P)
            if not np.allclose(s.q, APARCADO):
                s.ve_broca = self.c.ve(q4, np.asarray(taladro_P) + [0, 0, 8], [self.m.modelo.geom("broca").id])
            # el controlador usa sus propios datos: el taladro del mundo se vuelve a poner donde estaba
            self.m.poner_taladro(*self.m.juez.taladro_punta[:2]) if self.m.juez.taladro_visible else None
        return s

    def dibujar(self, s: Situacion, ruta: Path) -> None:
        obs = self.m.imagen(s.vista, (960, 720))
        arriba = self.m.imagen("top", (480, 360))
        robot = self.m.imagen("wrist", (480, 360))
        lienzo = np.full((720 + 150, 960 + 480, 3), 30, np.uint8)
        lienzo[:720, :960], lienzo[:360, 960:], lienzo[360:720, 960:] = obs, arriba, robot
        lienzo = cv2.cvtColor(lienzo, cv2.COLOR_RGB2BGR)
        f = cv2.FONT_HERSHEY_SIMPLEX
        for texto, (x, y) in (("observador", (12, 28)), ("camara de arriba", (972, 28)), ("camara de la muneca", (972, 388))):
            cv2.putText(lienzo, texto, (x, y), f, 0.7, (0, 0, 0), 4, cv2.LINE_AA)
            cv2.putText(lienzo, texto, (x, y), f, 0.7, (255, 255, 255), 1, cv2.LINE_AA)
        cv2.putText(lienzo, _ascii(f"S{s.numero}. {s.nombre}"), (16, 762), f, 0.95, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(lienzo, _ascii(s.resumen), (16, 800), f, 0.62, (220, 220, 160), 1, cv2.LINE_AA)
        datos = f"estado: {s.estado}   aspiradora: {'ENCENDIDA' if s.aspiradora else 'apagada'}"
        if s.boca is not None:
            datos += f"   boca ({s.boca[0]:.0f}, {s.boca[1]:.0f}, {s.boca[2]:.0f}) mm a {s.inclinacion:.0f} grados"
        if s.holgura is not None:
            datos += f"   holgura {s.holgura:.0f} mm"
        if s.ve_broca is not None:
            datos += f"   la camara ve la broca: {'si' if s.ve_broca else 'no'}"
        cv2.putText(lienzo, _ascii(datos), (16, 838), f, 0.58, (170, 220, 170), 1, cv2.LINE_AA)
        cv2.imwrite(str(ruta), lienzo, [cv2.IMWRITE_JPEG_QUALITY, 85])


class _Lista(Exception):
    def __init__(self, s):
        self.s = s


def poner_situacion(sim: Simulador, numero: int) -> Situacion:
    """Deja el mundo en la situación `numero` (escena y postura del robot), sin dibujar: para el visor."""
    try:
        situaciones(sim, solo=numero)
    except _Lista as e:
        return e.s
    raise ValueError(f"no hay situación {numero}")


def situaciones(sim: Simulador, solo: int | None = None) -> list[Situacion]:
    out: list[Situacion] = []
    c = sim.c
    P = sim.punta()
    tabla_movida = g.PoseTabla(TABLA_TRABAJO.x + 12, TABLA_TRABAJO.y - 25, 6.0)

    def anadir(s: Situacion, resultado=None, taladro_P=None):
        if solo is not None and s.numero != solo:
            return
        if resultado is not None:
            s.q, _ = sim.postura(resultado)
        sim.poner(s, taladro_P)
        if solo is not None:
            raise _Lista(s)
        out.append(s)
        nombre = "".join(ch if ch.isalnum() else "_" for ch in _ascii(s.nombre).lower()).strip("_")[:40]
        sim.dibujar(s, SALIDA / f"{s.numero:02d}_{nombre}.jpg")

    def si(n):  # solo prepara la escena de la situación que toca
        return solo is None or solo == n

    from garbi import interactivo as I
    import garbi.lateral as Lmod

    def espera(Pt):  # siguiendo al taladro a distancia
        anterior = Lmod.INCLINACIONES
        Lmod.INCLINACIONES = I.INCLINACIONES_ESPERA
        try:
            return c._postura(c._junto_a(Pt, I.DIST_ESPERA, I.ALTURA_ESPERA))
        finally:
            Lmod.INCLINACIONES = anterior

    def limpiar_picado(punto):
        anterior = Lmod.INCLINACIONES
        Lmod.INCLINACIONES = I.INCLINACIONES_LIMPIEZA
        try:
            return c.limpiar(punto)
        finally:
            Lmod.INCLINACIONES = anterior

    aire = P + [0, 0, 50]
    if si(1):
        sim.escena()
        anadir(Situacion(1, "Reposo", "vista_persona", "aparcado", False,
                         "Sin taladro: aparcado alto y recogido; el tubo baja por el costado del brazo."))
    if si(2):
        sim.escena(); sim.m.poner_taladro(*aire)
        anadir(Situacion(2, "Entra el taladro: lo sigue a distancia", "vista_cerca", "seguir", False,
                         "Mientras mueves el taladro con la broca en el aire, te sigue a ~80 mm sin estorbar."),
               espera(P), aire)
    if si(3):
        sim.escena(taladro=P)
        anadir(Situacion(3, "Apoyas la broca: se acerca y aspira", "vista_cerca", "acompanar", True,
                         "Broca apoyada y quieta 0,3 s: boca a 30 mm, casi horizontal; aspiradora encendida."),
               c.acompanar(P), P)
    if si(4):
        sim.escena(taladro=P); sim.m.taladrar()
        anadir(Situacion(4, "Taladrando", "vista_lateral", "acompanar", True,
                         "Garbi junto a la broca, aspirando la viruta que sale. Apunta el agujero."), c.acompanar(P), P)
    if si(5):
        P2 = P + [40, -70, 0]
        sim.escena(); sim.m.poner_taladro(*(P2 + [0, 0, 50]))
        anadir(Situacion(5, "Levantas la broca y te mueves: te sigue", "vista_cerca", "seguir", False,
                         "Al levantar la broca se separa a la distancia de espera y te sigue al punto siguiente."),
               espera(P2), P2 + [0, 0, 50])
    if si(6):
        Pf = np.array([230.0, -60.0, g.ALTURA_CARA_TABLA + 50])
        sim.escena(); sim.m.poner_taladro(*Pf)
        anadir(Situacion(6, "Taladro fuera de su alcance", "vista_persona", "aparcado", False,
                         "Mas cerca de ~280 mm no puede atacar casi en horizontal: se queda aparcado y avisa."), taladro_P=Pf)
    if si(7):
        sim.escena()
        for a in ((-20.0, 40.0), (40.0, -70.0), (-40.0, -20.0)):
            pa = TABLA_TRABAJO.a_mesa(np.array(a)); sim.m.poner_taladro(*pa); sim.m.taladrar()
        sim.m.quitar_taladro()
        anadir(Situacion(7, "Sale el taladro: limpia todos los agujeros", "vista_cerca", "limpiar", True,
                         "Espera 1,5 s aspirando y barre cada agujero con la boca mas picada (45-60 grados)."),
               limpiar_picado(P + [-8, 0, 0]))
    if si(8):
        sim.escena()
        sim.m.poner_taladro(*P[:2]); sim.m.taladrar(); sim.m.quitar_taladro()
        sim.m.colocar_tabla(tabla_movida)
        anadir(Situacion(8, "Mueves la madera antes de que limpie", "vista_cerca", "limpiar", True,
                         "Los agujeros van con la madera: la camara de arriba la sigue y limpia cada uno en su sitio."),
               limpiar_picado(sim.punta(tabla=tabla_movida)))
    if si(9):
        sim.escena()
        mont = np.array([330.0, -195.0])
        sim.m.tirar_serrin(mont[0], mont[1], n=30, radio=15)
        anadir(Situacion(9, "\"Limpia el tapete\"", "vista_persona", "limpiar", True,
                         "Por voz o boton: va al monton de serrin del tapete (a su alcance) y lo barre."),
               limpiar_picado(np.array([mont[0], mont[1], g.ALFOMBRILLA_GROSOR])))
    if si(10):
        sim.escena()
        anadir(Situacion(10, "\"Limpia la madera\"", "vista_lateral", "limpiar", True,
                         "Barrido en zigzag de la madera, con la boca picada."),
               limpiar_picado(sim.punta(p_tabla=[-20, -60])))
    if si(11):
        sim.escena(taladro=P)
        anadir(Situacion(11, "\"Retirate\"", "vista_persona", "aparcar", False,
                         "Se separa de la broca y aparca; apaga la aspiradora. Vuelve si se lo pides."), taladro_P=P)
    if si(12):
        sim.escena(taladro=P, inclinacion=15.0)
        anadir(Situacion(12, "No ve la broca", "vista_cerca", "seguir (esperando)", False,
                         "No se acerca a ciegas: se queda a la distancia de espera y pide enderezar el taladro."),
               espera(P), P)
    if si(13):
        sim.escena(taladro=P)
        anadir(Situacion(13, "Emergencia o fallo del Arduino", "vista_lateral", "congelado", False,
                         "Boton de paro o sin latido 1 s: se queda quieto y la aspiradora se apaga."), c.acompanar(P), P)
    return out


def tabla_markdown(lista: list[Situacion]) -> str:
    filas = ["| S | Situación | Estado | Aspiradora | Articulaciones (pan, lift, elbow, flex) ° | Boca (x, y, z) mm | "
             "Inclinación | Holgura | Cámara ve boca / broca |", "|---|---|---|---|---|---|---|---|---|"]
    for s in lista:
        q = ", ".join(f"{v:.0f}" for v in s.q[:4])
        boca = "—" if s.boca is None else f"({s.boca[0]:.0f}, {s.boca[1]:.0f}, {s.boca[2]:.0f})"
        inc = "—" if s.inclinacion is None else f"{s.inclinacion:.0f}°"
        hol = "—" if s.holgura is None else f"{s.holgura:.0f} mm"
        vb = lambda v: "—" if v is None else ("sí" if v else "no")
        filas.append(f"| {s.numero} | {s.nombre} | {s.estado} | {'sí' if s.aspiradora else 'no'} | {q} | {boca} | "
                     f"{inc} | {hol} | {vb(s.ve_boca)} / {vb(s.ve_broca)} |")
    return "\n".join(filas)


def main() -> None:
    SALIDA.mkdir(parents=True, exist_ok=True)
    for viejo in SALIDA.glob("[0-9][0-9]_*.jpg"):
        viejo.unlink()
    lista = situaciones(Simulador())
    (SALIDA / "posturas.md").write_text(tabla_markdown(lista) + "\n")
    print(tabla_markdown(lista))


if __name__ == "__main__":
    main()
