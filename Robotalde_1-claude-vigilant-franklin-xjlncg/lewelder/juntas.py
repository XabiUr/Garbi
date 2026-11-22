"""Juntas v2: geometría de la base y la chapa móvil, reconocimiento de la junta montada y marco del cordón.

Con las poses 3D de la base y de la chapa móvil (de `estereo.py` o de la simulación) se decide qué junta hay:

- **T**: la móvil de pie sobre la línea central de la base (en la ranura `GUIA_T`), con la cara lisa en Y = 0.
- **Esquina** (interior): la móvil de pie junto al tope del canto +Y de la base, con la cara lisa en Y = `Y_CORDON` (31).
- **Incompleta**: la móvil está, pero no en una de las dos posiciones (inclinada, girada, lejos de la guía, corrida a
  lo largo, sin apoyar, tumbada o del revés). El motivo se da en palabras para la tablet ("la chapa está inclinada
  12°").
- **Sin móvil** / **sin base**: no se ve la chapa (o no hay pose).

El **marco del cordón** es el marco de la pieza de la v1 (origen al inicio del cordón, X a lo largo, Y transversal con
el alma en Y >= 0, Z hacia arriba desde la cara de la base) calculado con la pose de la base, así que las métricas de la
v1 funcionan igual. La posición de soldeo (ISO 6947) sale de la orientación del cordón y de la bisectriz del ángulo de
la junta respecto a la gravedad: con la base tumbada en la mesa, T y esquina son PB.

Marcos (mm):
- **Base:** origen en el centro de su cara superior, X a lo largo del lado largo, Y transversal, Z arriba (contrato).
  Sobre la mesa con `giro` 0, la X de la base apunta a +Y de la mesa (mismo convenio que `Anclaje`).
- **Chapa móvil** (el de `hardware/v2/contrato.md` §1 y el CAD): origen en el centro del canto que apoya, X a lo
  largo (-70..70), Y = grosor (cara lisa en Y = -3, la del cordón; cara de la aleta en Y = +3, la aleta sobresale
  hacia +Y), Z = altura de pie (0..40). Montada, sus ejes son los de la base.
- **ArUco:** cada marcador tiene sus ejes X (derecha) e Y (arriba) en su cara, mirando hacia fuera; las esquinas
  van en el orden de OpenCV. Tabla del contrato de hardware: 30 alineado con la base; 41 (cara lisa) con +X = +X de la
  chapa y arriba = +Z; 40 (cara de la aleta) con +X = -X de la chapa y arriba = +Z (los dos se leen derechos mirando
  su cara con el canto que apoya abajo).
- **CAD** (`hardware/v2/cad/stl`, Y arriba): base (X, Y, Z)_stl = (X_b + 100, Z_b + 6, 40 - Y_b); móvil
  (X, Y, Z)_stl = (X_m + 70, Z_m, 21 - Y_m). `escena_sintetica.malla_cad` los lee ya en el marco de su chapa.

Convención de poses: `Pose(R, t)` de "A respecto a B" lleva puntos de A a B: `p_B = R @ p_A + t`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

import numpy as np

from lewelder.contrato import (
    ALETA,
    ALTO_MOVIL,
    ALTURA_APOYO,
    ANCHO_BASE,
    ARUCO_EN_BASE,
    ARUCO_EN_MOVIL,
    GROSOR_CHAPA,
    ID_BASE,
    IDS_MOVIL,
    LADO_ARUCO_V2,
    LARGO_BASE,
    LARGO_MOVIL,
    LONGITUD_CORDON,
    NOMBRE_JUNTA,
    POSICION_BASE,
    POSICIONES_SOLDEO,
    TOPE_ESQUINA,
    Y_CORDON,
    Z_CANTO_MOVIL,
    Anclaje,
    TipoJunta,
)


# --- poses -------------------------------------------------------------------------------------------------------
def rot_x(grados: float) -> np.ndarray:
    a = np.radians(grados)
    return np.array([[1.0, 0.0, 0.0], [0.0, np.cos(a), -np.sin(a)], [0.0, np.sin(a), np.cos(a)]])


def rot_y(grados: float) -> np.ndarray:
    a = np.radians(grados)
    return np.array([[np.cos(a), 0.0, np.sin(a)], [0.0, 1.0, 0.0], [-np.sin(a), 0.0, np.cos(a)]])


def rot_z(grados: float) -> np.ndarray:
    a = np.radians(grados)
    return np.array([[np.cos(a), -np.sin(a), 0.0], [np.sin(a), np.cos(a), 0.0], [0.0, 0.0, 1.0]])


@dataclass
class Pose:
    """Transformación rígida `p_B = R @ p_A + t` (de A a B)."""

    R: np.ndarray
    t: np.ndarray

    def __post_init__(self):
        self.R = np.asarray(self.R, dtype=float).reshape(3, 3)
        self.t = np.asarray(self.t, dtype=float).reshape(3)

    @classmethod
    def identidad(cls) -> Pose:
        return cls(np.eye(3), np.zeros(3))

    def aplicar(self, p) -> np.ndarray:
        """Lleva puntos (3,) o (N, 3) de A a B."""
        p = np.asarray(p, dtype=float)
        return p @ self.R.T + self.t

    def inversa(self) -> Pose:
        return Pose(self.R.T, -self.R.T @ self.t)

    def __matmul__(self, otra: Pose) -> Pose:
        """Composición: (self @ otra).aplicar(p) == self.aplicar(otra.aplicar(p))."""
        return Pose(self.R @ otra.R, self.R @ otra.t + self.t)

    def diferencia(self, otra: Pose) -> tuple[float, float]:
        """(distancia entre orígenes en mm, ángulo entre orientaciones en grados)."""
        cos = (np.trace(self.R.T @ otra.R) - 1) / 2
        return float(np.linalg.norm(self.t - otra.t)), float(np.degrees(np.arccos(np.clip(cos, -1.0, 1.0))))

    def a_dict(self) -> dict:
        return {"R": self.R.tolist(), "t": self.t.tolist()}


# --- geometría de las piezas v2 -----------------------------------------------------------------------------------
# Cajas (xmin, xmax, ymin, ymax, zmin, zmax), cada una en el marco de su chapa.
CAJA_BASE = (-LARGO_BASE / 2, LARGO_BASE / 2, -ANCHO_BASE / 2, ANCHO_BASE / 2, -GROSOR_CHAPA, 0.0)
# Tope de la esquina: nervio dentro de la base, en el canto +Y (CAD: Y 37 a 40, Z 0 a 3, X -75 a 75).
CAJA_TOPE = (-75.0, 75.0, ANCHO_BASE / 2 - TOPE_ESQUINA["ancho"], ANCHO_BASE / 2, 0.0, TOPE_ESQUINA["alto"])
CAJA_MOVIL = (-LARGO_MOVIL / 2, LARGO_MOVIL / 2, -GROSOR_CHAPA / 2, GROSOR_CHAPA / 2, 0.0, ALTO_MOVIL)
# Aleta: lámina de `grosor` (en Z) que sobresale `alto` de la cara +Y, centrada en la altura de la chapa.
CAJA_ALETA = (ALETA["x"] - ALETA["largo"] / 2, ALETA["x"] + ALETA["largo"] / 2,
              GROSOR_CHAPA / 2, GROSOR_CHAPA / 2 + ALETA["alto"],
              ALTO_MOVIL / 2 - ALETA["grosor"] / 2, ALTO_MOVIL / 2 + ALETA["grosor"] / 2)
# Centro de la chapa móvil (de su caja) en su marco.
CENTRO_MOVIL = np.array([0.0, 0.0, ALTO_MOVIL / 2])

# Juegos de ids de la móvil (aleta, lisa): el principal y los repuestos del contrato.
PARES_MOVIL = [(IDS_MOVIL["cara_aleta"] + 2 * k, IDS_MOVIL["cara_lisa"] + 2 * k) for k in range(3)]


@dataclass(frozen=True)
class Marcador:
    chapa: str  # "base" o "movil"
    centro: tuple[float, float, float]  # en el marco de la chapa
    eje_x: tuple[float, float, float]
    eje_y: tuple[float, float, float]
    lado: float = LADO_ARUCO_V2

    @property
    def normal(self) -> np.ndarray:
        return np.cross(self.eje_x, self.eje_y)


MARCADORES: dict[int, Marcador] = {ID_BASE: Marcador("base", tuple(ARUCO_EN_BASE), (1, 0, 0), (0, 1, 0))}
for _aleta, _lisa in PARES_MOVIL:
    _x, _z = ARUCO_EN_MOVIL
    MARCADORES[_aleta] = Marcador("movil", (_x, GROSOR_CHAPA / 2, _z), (-1, 0, 0), (0, 0, 1))
    MARCADORES[_lisa] = Marcador("movil", (_x, -GROSOR_CHAPA / 2, _z), (1, 0, 0), (0, 0, 1))


def esquinas_marcador(id_aruco: int) -> np.ndarray:
    """Esquinas (4, 3) del marcador `id_aruco` en el marco de su chapa, en el orden de OpenCV."""
    m = MARCADORES[id_aruco]
    c, ex, ey = (np.asarray(v, dtype=float) for v in (m.centro, m.eje_x, m.eje_y))
    h = m.lado / 2
    return np.array([c - h * ex + h * ey, c + h * ex + h * ey, c + h * ex - h * ey, c - h * ex - h * ey])


def pose_base(x: float | None = None, y: float | None = None, giro: float | None = None,
              anclaje: Anclaje = POSICION_BASE) -> Pose:
    """Pose de la base tumbada en la mesa (base → mesa). Por defecto, en `POSICION_BASE`."""
    x = anclaje.x if x is None else x
    y = anclaje.y if y is None else y
    giro = anclaje.giro if giro is None else giro
    return Pose(rot_z(giro + 90.0), [x, y, GROSOR_CHAPA])


def pose_movil_montada(tipo: TipoJunta | str, base: Pose, inclinacion: float = 0.0, giro: float = 0.0,
                       desplazamiento=(0.0, 0.0, 0.0)) -> Pose:
    """Pose (móvil → mesa) de la chapa móvil montada en la junta `tipo` sobre `base`, con errores opcionales.

    `inclinacion` (grados) la vuelca alrededor del canto que apoya por el lado de la cara lisa (positivo = hacia el
    cordón, -Y de la base); `giro` (grados) la gira alrededor de la vertical por su centro; `desplazamiento` (mm, en
    el marco de la base) la mueve.
    """
    tipo = TipoJunta(tipo)
    nominal = Pose(np.eye(3), [0.0, Y_CORDON[tipo] + GROSOR_CHAPA / 2, Z_CANTO_MOVIL[tipo]])
    pivote = np.array([0.0, Y_CORDON[tipo], Z_CANTO_MOVIL[tipo]])
    volcar = Pose(rot_x(inclinacion), pivote - rot_x(inclinacion) @ pivote)
    centro = nominal.aplicar(CENTRO_MOVIL)
    girar = Pose(rot_z(giro), centro - rot_z(giro) @ centro)
    mover = Pose(np.eye(3), desplazamiento)
    return base @ mover @ girar @ volcar @ nominal


def pose_movil_tumbada(x: float, y: float, giro: float = 0.0, aleta_arriba: bool = True) -> Pose:
    """Pose (móvil → mesa) de la chapa móvil tumbada en la mesa con su centro en (x, y) y X girada `giro`° desde +X."""
    # Aleta arriba: la Y de la chapa (hacia la aleta) apunta a +Z de la mesa; si no, a -Z.
    R = rot_z(giro) @ rot_x(90.0 if aleta_arriba else -90.0)
    z_centro = GROSOR_CHAPA / 2
    return Pose(R, np.array([x, y, z_centro]) - R @ CENTRO_MOVIL)


def marco_cordon(tipo: TipoJunta | str, base: Pose | Anclaje) -> Pose:
    """Marco del cordón (→ mesa): origen al inicio del cordón en la cara de la base, X a lo largo, alma en Y >= 0.

    Es el de `alcance.marco_cordon` (origen en (-60, Y_CORDON, 0) de la base, ejes de la base). `base` puede ser la
    pose medida o un `Anclaje` (la base tumbada en la mesa).
    """
    if isinstance(base, Anclaje):
        base = pose_base(anclaje=base)
    return base @ Pose(np.eye(3), [-LONGITUD_CORDON / 2, Y_CORDON[TipoJunta(tipo)], 0.0])


# Bisectriz del ángulo de la junta (en el marco de la base): entre la normal de la cara de la base (+Z) y la de la
# cara lisa de la móvil (-Y). Igual en la T y en la esquina interior.
BISECTRIZ_JUNTA = np.array([0.0, -1.0, 1.0]) / np.sqrt(2.0)


def posicion_soldeo(tipo: TipoJunta | str, base: Pose) -> str:
    """Posición de soldeo ISO 6947 de una junta en ángulo, por la orientación respecto a la gravedad (Z de la mesa).

    Cordón a más de 45° de la horizontal: PF (se avanza hacia arriba) o PG (hacia abajo). Si no, por el ángulo entre
    la bisectriz de la junta y la vertical: < 22,5° PA (plana), < 67,5° PB (horizontal en ángulo), < 112,5° PC,
    < 157,5° PD (en ángulo bajo techo) y si no PE.
    """
    TipoJunta(tipo)
    avance = base.R[:, 0]
    if abs(avance[2]) > np.sin(np.radians(45.0)):
        return "PF" if avance[2] > 0 else "PG"
    bisectriz = base.R @ BISECTRIZ_JUNTA
    angulo = float(np.degrees(np.arccos(np.clip(bisectriz[2], -1.0, 1.0))))
    for limite, posicion in ((22.5, "PA"), (67.5, "PB"), (112.5, "PC"), (157.5, "PD")):
        if angulo < limite:
            return posicion
    return "PE"


# --- reconocimiento ----------------------------------------------------------------------------------------------
class EstadoJunta(str, Enum):
    T = "t"
    ESQUINA = "esquina"
    INCOMPLETA = "incompleta"
    SIN_MOVIL = "sin_movil"
    SIN_BASE = "sin_base"


# Tolerancias de una junta bien montada (las guías y los imanes centran la chapa; esto es lo que admiten).
TOLERANCIAS_JUNTA = {
    "inclinacion": 5.0,  # grados fuera de la vertical (volcada o con un extremo más alto)
    "giro": 5.0,  # grados respecto a la guía (alrededor de la vertical)
    "guia": 3.0,  # mm de la cara de la chapa a su guía (transversal)
    "a_lo_largo": 10.0,  # mm del centro de la chapa al de la base, a lo largo del cordón
    "hueco": 3.0,  # mm entre el canto de la chapa y donde debe apoyar
}
# Centro (Y, Z) de la caja de la móvil, en la base, en cada junta bien montada.
_CENTRO_MONTADA = {tipo: (Y_CORDON[tipo] + GROSOR_CHAPA / 2, Z_CANTO_MOVIL[tipo] + ALTO_MOVIL / 2)
                   for tipo in TipoJunta}


@dataclass
class Junta:
    """Junta reconocida. `tipo` es el estado; `candidata` la junta más parecida (también si está incompleta)."""

    tipo: EstadoJunta
    confianza: float = 0.0
    motivo: str | None = None
    candidata: TipoJunta | None = None
    posicion: str | None = None  # "PB", ... (ISO 6947) de la candidata
    cordon: Pose | None = None  # marco del cordón → mesa (de la candidata)
    base: Pose | None = None
    movil: Pose | None = None
    errores: dict[str, float] = field(default_factory=dict)

    @property
    def completa(self) -> bool:
        return self.tipo in (EstadoJunta.T, EstadoJunta.ESQUINA)

    @property
    def tipo_junta(self) -> TipoJunta | None:
        """La junta montada (T o esquina) o None si no está completa."""
        return TipoJunta(self.tipo.value) if self.completa else None

    @property
    def nombre(self) -> str:
        if self.completa:
            texto = f"unión {NOMBRE_JUNTA[self.tipo_junta]}"
            return f"{texto}, posición {self.posicion}" if self.posicion else texto
        return {EstadoJunta.INCOMPLETA: "junta incompleta", EstadoJunta.SIN_MOVIL: "sin chapa móvil",
                EstadoJunta.SIN_BASE: "sin base"}[self.tipo]

    def a_dict(self) -> dict:
        return {
            "tipo": self.tipo.value, "nombre": self.nombre, "confianza": round(self.confianza, 3),
            "motivo": self.motivo, "candidata": self.candidata.value if self.candidata else None,
            "posicion": self.posicion, "cordon": self.cordon.a_dict() if self.cordon else None,
            "errores": {k: round(v, 2) for k, v in self.errores.items()},
        }


def _angulo(seno: float) -> float:
    return float(np.degrees(np.arcsin(np.clip(abs(seno), 0.0, 1.0))))


# Con la móvil vista por una sola cámara su distancia es supuesta (apoya en la base): la posición se mide peor.
TOLERANCIAS_UNA_CAMARA = {**TOLERANCIAS_JUNTA, "guia": 5.0, "a_lo_largo": 15.0, "hueco": 5.0}


def reconocer_junta(base: Pose | None, movil: Pose | None, calidad: float = 1.0,
                    tolerancias: dict[str, float] | None = None) -> Junta:
    """Tipo de junta con las poses (→ mesa) de la base y de la chapa móvil.

    `tolerancias`: las de `TOLERANCIAS_JUNTA` por defecto (`TOLERANCIAS_UNA_CAMARA` si la móvil la ve una sola
    cámara). `calidad` (0-1) escala la confianza (p. ej. menos si la pose sale de una sola cámara). La confianza de
    una junta completa baja del 1 al 0,5 a medida que los errores se acercan a su tolerancia; la de una incompleta
    sube del 0,5 al 1 a medida que el peor error pasa del doble de su tolerancia.
    """
    if base is None:
        return Junta(EstadoJunta.SIN_BASE, confianza=calidad, motivo="no se ve la base", movil=movil)
    if movil is None:
        return Junta(EstadoJunta.SIN_MOVIL, confianza=calidad, motivo="no se ve la chapa móvil", base=base)
    en_base = base.inversa() @ movil
    eje_x, normal, eje_alto = en_base.R.T  # filas de R^T = columnas de R
    centro = en_base.aplicar(CENTRO_MOVIL)

    def incompleta(motivo: str, candidata: TipoJunta | None = None, errores=None, exceso: float = 2.0) -> Junta:
        confianza = calidad * float(np.clip(0.5 + 0.5 * (exceso - 1.0), 0.5, 1.0))
        cordon = marco_cordon(candidata, base) if candidata else None
        posicion = posicion_soldeo(candidata, base) if candidata else None
        return Junta(EstadoJunta.INCOMPLETA, confianza, motivo, candidata, posicion, cordon, base, movil,
                     errores or {})

    sobre_base = abs(centro[0]) < LARGO_BASE / 2 and abs(centro[1]) < ANCHO_BASE / 2 + 10.0
    if abs(normal[2]) > np.cos(np.radians(45.0)):
        lugar = "sobre la base" if sobre_base and centro[2] > -GROSOR_CHAPA else "en la mesa, sin montar"
        return incompleta(f"la chapa está tumbada {lugar}")
    if eje_alto[2] < 0:
        return incompleta("la chapa está del revés: apoya por el canto de arriba")

    candidata = min(TipoJunta, key=lambda tipo: abs(centro[1] - _CENTRO_MONTADA[tipo][0]))
    caja = np.array([[x, y, z] for x in CAJA_MOVIL[:2] for y in CAJA_MOVIL[2:4] for z in CAJA_MOVIL[4:]])
    errores = {
        "inclinacion": max(_angulo(normal[2]), _angulo(eje_x[2])),
        "giro": float(np.degrees(np.arctan2(abs(normal[0]), abs(normal[1])))),
        "guia": float(centro[1] - _CENTRO_MONTADA[candidata][0]),
        "a_lo_largo": float(centro[0]),
        "hueco": float(en_base.aplicar(caja)[:, 2].min() - Z_CANTO_MOVIL[candidata]),
    }
    if abs(errores["guia"]) > 20.0 or abs(errores["a_lo_largo"]) > LARGO_BASE / 2 or errores["hueco"] > 20.0:
        return incompleta("la chapa no está sobre la base", errores=errores)
    tolerancias = tolerancias or TOLERANCIAS_JUNTA
    proporcion = {k: abs(v) / tolerancias[k] for k, v in errores.items()}
    motivos = {
        "inclinacion": f"la chapa está inclinada {errores['inclinacion']:.0f}°",
        "giro": f"la chapa está girada {errores['giro']:.0f}° respecto a la guía",
        "guia": f"la chapa está a {abs(errores['guia']):.0f} mm de la guía",
        "a_lo_largo": f"la chapa está desplazada {abs(errores['a_lo_largo']):.0f} mm a lo largo de la base",
        "hueco": f"la chapa no apoya en la base: queda a {abs(errores['hueco']):.0f} mm",
    }
    for clave in TOLERANCIAS_JUNTA:  # el primero que se pasa, por orden de importancia
        if proporcion[clave] > 1.0:
            return incompleta(motivos[clave], candidata, errores, proporcion[clave])
    if normal[1] < 0:
        return incompleta("la aleta queda del lado del cordón: dale la vuelta a la chapa", candidata, errores)
    confianza = calidad * (1.0 - 0.5 * max(proporcion.values()))
    return Junta(EstadoJunta(candidata.value), confianza, None, candidata, posicion_soldeo(candidata, base),
                 marco_cordon(candidata, base), base, movil, errores)


# --- punta de la antorcha ----------------------------------------------------------------------------------------
# Por debajo de la cara de la chapa la punta no puede estar: más de esto es un error de medida, no un apoyo.
MARGEN_BAJO_CHAPA = 5.0  # mm


def punta_en_cordon(p_mesa, junta: Junta) -> tuple[float, float, float]:
    """Punto de la mesa en el marco del cordón de `junta` (x a lo largo, y transversal, z altura sobre la base)."""
    if junta.cordon is None:
        raise ValueError(f"la junta no tiene cordón ({junta.tipo.value})")
    x, y, z = junta.cordon.inversa().aplicar(np.asarray(p_mesa, dtype=float))
    return float(x), float(y), float(z)


def apoyada(z: float) -> bool:
    """¿La punta, a altura `z` (mm) sobre la chapa, está apoyada? (< `ALTURA_APOYO`, sin pasar de la chapa)."""
    return -MARGEN_BAJO_CHAPA < z < ALTURA_APOYO


# Nombre corto de la posición (para la tablet).
def nombre_posicion(posicion: str | None) -> str | None:
    return POSICIONES_SOLDEO.get(posicion) if posicion else None
