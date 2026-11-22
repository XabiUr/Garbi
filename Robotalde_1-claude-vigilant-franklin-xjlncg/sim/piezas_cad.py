"""Piezas reales de la v2 (CAD de SolidWorks en `hardware/v2/cad/stl/`) para la simulación del montaje.

- Lee los STL (mm, exportados con Y hacia arriba), los pasa al marco de uso de cada pieza (Z arriba, orígenes del brief
  `hardware/v2/brief_solidworks.md`) y los da como mallas visuales para `MjSpec`.
- MuJoCo colisiona con la envolvente convexa de cada malla y estas piezas son cóncavas (ranura, tope, aleta, tubo):
  la colisión va con **primitivas medidas sobre la propia malla** (cortes del voxelizado), no con cotas copiadas.
- `ajuste_colision` compara el voxelizado de la malla con el de las primitivas (IoU y volumen que sobra o falta), para
  el informe de validación del CAD.

Marcos de uso (mm):
- BASE: origen en el centro de la cara superior, X a lo largo (200), Y transversal (80), Z arriba.
- MOVIL: origen en el centro del canto inferior, X a lo largo (140), Y = grosor (cara lisa en −Y, aleta en +Y),
  Z = altura de pie (40). (Es el convenio de `hardware/v2/contrato.md`; `sim.montaje` lo convierte al suyo.)
- ANTORCHA: origen en la punta, Z = eje hacia el mango, caras planas del mango en ±Y.
- SOPORTE: origen en el centro del pie sobre el tablero, Z arriba.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import numpy as np

from sim.escena import _leer_stl

RAIZ = Path(__file__).resolve().parents[1]
CARPETA_STL = RAIZ / "hardware" / "v2" / "cad" / "stl"
PIEZAS = ("BASE-V2", "MOVIL-V2", "ANTORCHA-ROBOT-V2", "SOPORTE-ANTORCHA-V2")


# --- lectura y marcos -------------------------------------------------------------------------------------------------
def leer_stl_crudo(nombre: str) -> tuple[np.ndarray, np.ndarray]:
    """(vértices, caras) del STL tal como sale de SolidWorks. La antorcha une sus dos mitades."""
    if nombre == "ANTORCHA-ROBOT-V2":
        va, fa = _leer_stl(CARPETA_STL / "ANTORCHA-ROBOT-V2_mitad-A.STL")
        vb, fb = _leer_stl(CARPETA_STL / "ANTORCHA-ROBOT-V2_mitad-B.STL")
        return np.vstack([va, vb]), np.vstack([fa, fb + len(va)])
    return _leer_stl(CARPETA_STL / f"{nombre}.STL")


# --- voxelizado (rayos a lo largo de Z con la regla de paridad) ---------------------------------------------------------
@dataclass
class Voxeles:
    ocupado: np.ndarray  # bool [nx, ny, nz]
    origen: np.ndarray  # centro del vóxel (0, 0, 0), mm
    paso: float

    def centros(self, eje: int) -> np.ndarray:
        return self.origen[eje] + self.paso * np.arange(self.ocupado.shape[eje])

    @property
    def volumen(self) -> float:
        return float(self.ocupado.sum()) * self.paso ** 3


def voxelizar(v: np.ndarray, f: np.ndarray, paso: float = 0.5, margen: float = 1.0) -> Voxeles:
    """Ocupación de una malla cerrada en una rejilla de `paso` mm (rayos en +Z desde cada columna XY)."""
    lo, hi = v.min(0) - margen, v.max(0) + margen
    xs = np.arange(lo[0] + paso / 2, hi[0], paso)
    ys = np.arange(lo[1] + paso / 2, hi[1], paso)
    zs = np.arange(lo[2] + paso / 2, hi[2], paso)
    occ = np.zeros((len(xs), len(ys), len(zs)), dtype=bool)
    tri = v[f]  # [m, 3, 3]
    # pequeño desplazamiento para no pasar justo por aristas y vértices
    eps = np.array([1.37e-4, 2.71e-4])
    a, b, c = tri[:, 0], tri[:, 1], tri[:, 2]
    tmin, tmax = tri[:, :, :2].min(1), tri[:, :, :2].max(1)
    for i, x in enumerate(xs):
        sel = (tmin[:, 0] <= x + eps[0]) & (tmax[:, 0] >= x + eps[0])
        if not sel.any():
            continue
        A, B, C = a[sel], b[sel], c[sel]
        for j, y in enumerate(ys):
            p = np.array([x, y]) + eps
            s2 = (tmin[sel, 1] <= p[1]) & (tmax[sel, 1] >= p[1])
            if not s2.any():
                continue
            A2, B2, C2 = A[s2], B[s2], C[s2]
            # coordenadas baricéntricas en XY
            v0, v1 = B2[:, :2] - A2[:, :2], C2[:, :2] - A2[:, :2]
            v2 = p - A2[:, :2]
            den = v0[:, 0] * v1[:, 1] - v1[:, 0] * v0[:, 1]
            ok = np.abs(den) > 1e-12
            if not ok.any():
                continue
            u = (v2[ok, 0] * v1[ok, 1] - v1[ok, 0] * v2[ok, 1]) / den[ok]
            w = (v0[ok, 0] * v2[ok, 1] - v2[ok, 0] * v0[ok, 1]) / den[ok]
            dentro = (u >= 0) & (w >= 0) & (u + w <= 1)
            if not dentro.any():
                continue
            z = (A2[ok][dentro, 2] + u[dentro] * (B2[ok][dentro, 2] - A2[ok][dentro, 2])
                 + w[dentro] * (C2[ok][dentro, 2] - A2[ok][dentro, 2]))
            z = np.sort(z)
            for k in range(0, len(z) - 1, 2):
                occ[i, j, (zs >= z[k]) & (zs <= z[k + 1])] = True
    return Voxeles(occ, np.array([xs[0], ys[0], zs[0]]), paso)


def voxelizar_cajas(cajas, rejilla: Voxeles) -> np.ndarray:
    """Ocupación de una unión de cajas alineadas [(centro, semiejes)] en la rejilla de `rejilla`."""
    X, Y, Z = np.meshgrid(rejilla.centros(0), rejilla.centros(1), rejilla.centros(2), indexing="ij")
    occ = np.zeros(rejilla.ocupado.shape, dtype=bool)
    for centro, medio in cajas:
        occ |= ((np.abs(X - centro[0]) <= medio[0]) & (np.abs(Y - centro[1]) <= medio[1])
                & (np.abs(Z - centro[2]) <= medio[2]))
    return occ


@dataclass
class Ajuste:
    iou: float
    sobra_mm3: float  # volumen de las primitivas fuera de la malla
    falta_mm3: float  # volumen de la malla sin cubrir

    def texto(self) -> str:
        return f"IoU {self.iou:.3f}, sobra {self.sobra_mm3:.0f} mm³, falta {self.falta_mm3:.0f} mm³"


def comparar(malla: Voxeles, prim: np.ndarray) -> Ajuste:
    inter = (malla.ocupado & prim).sum()
    union = (malla.ocupado | prim).sum()
    dv = malla.paso ** 3
    return Ajuste(float(inter / union), float((prim & ~malla.ocupado).sum() * dv),
                  float((malla.ocupado & ~prim).sum() * dv))


# --- marcos de uso ----------------------------------------------------------------------------------------------------
@dataclass
class Pieza:
    nombre: str
    v: np.ndarray  # vértices en el marco de uso (mm)
    f: np.ndarray
    medidas: dict = field(default_factory=dict)


def _transformar(v, R, t):
    return v @ np.asarray(R, float).T + np.asarray(t, float)


# Paso de cada STL al marco de uso: p_uso = R · p_stl + t. Comprobado con los cortes del voxelizado: aleta en
# X −55..−15 y Z 17,5..22,5, ranura centrada en Y +3, tope en Y 37..40, ArUco de la base en X +82, chaveta en +X.
_GIRO_Y_ARRIBA = np.array([[1.0, 0, 0], [0, 0, -1.0], [0, 1.0, 0]])  # (x, y, z)_stl → (x, −z, y)
MARCOS_STL = {
    "BASE-V2": (_GIRO_Y_ARRIBA, (-100.0, 40.0, -6.0)),
    "MOVIL-V2": (_GIRO_Y_ARRIBA, (-70.0, 21.0, 0.0)),
    "ANTORCHA-ROBOT-V2_mitad-A": (_GIRO_Y_ARRIBA, (-10.0, 0.0, 0.0)),
    "ANTORCHA-ROBOT-V2_mitad-B": (_GIRO_Y_ARRIBA, (-10.0, 7.0, 0.0)),
    "SOPORTE-ANTORCHA-V2": (_GIRO_Y_ARRIBA, (-35.0, 35.0, 0.0)),
}


@lru_cache(maxsize=None)
def cargar(nombre: str) -> Pieza:
    """Malla de la pieza en su marco de uso (mm). La antorcha une sus dos mitades."""
    if nombre == "ANTORCHA-ROBOT-V2":
        vs, fs, n = [], [], 0
        for mitad in ("A", "B"):
            v, f = _leer_stl(CARPETA_STL / f"ANTORCHA-ROBOT-V2_mitad-{mitad}.STL")
            R, t = MARCOS_STL[f"ANTORCHA-ROBOT-V2_mitad-{mitad}"]
            vs.append(_transformar(v, R, t))
            fs.append(f + n)
            n += len(v)
        return Pieza(nombre, np.vstack(vs), np.vstack(fs))
    v, f = _leer_stl(CARPETA_STL / f"{nombre}.STL")
    R, t = MARCOS_STL[nombre]
    return Pieza(nombre, _transformar(v, R, t), f)


@lru_cache(maxsize=None)
def voxeles(nombre: str, paso: float = 0.5) -> Voxeles:
    p = cargar(nombre)
    return voxelizar(p.v, p.f, paso)


def _rango(mascara, centros, paso):
    i = np.where(mascara)[0]
    if not len(i):
        return None
    return round(float(centros[i[0]] - paso / 2), 2), round(float(centros[i[-1]] + paso / 2), 2)


def _indice(vx: Voxeles, eje: int, valor: float) -> int:
    return int(np.argmin(np.abs(vx.centros(eje) - valor)))


# --- medidas sobre la malla ---------------------------------------------------------------------------------------------
@lru_cache(maxsize=None)
def medidas(nombre: str) -> dict:
    """Cotas que la simulación necesita, medidas en el voxelizado de la malla (no copiadas del brief)."""
    vx = voxeles(nombre)
    p = vx.paso
    X, Y, Z = vx.centros(0), vx.centros(1), vx.centros(2)
    o = vx.ocupado
    m = {"caja": (_rango(o.any((1, 2)), X, p), _rango(o.any((0, 2)), Y, p), _rango(o.any((0, 1)), Z, p)),
         "volumen_mm3": round(vx.volumen)}
    if nombre == "BASE-V2":
        c = o[_indice(vx, 0, 0.0)]  # sección YZ por el centro
        sin_arriba = ~c[:, (Z > -1.9) & (Z < -0.1)].any(1)
        m["ranura_y"] = _rango(sin_arriba & (Y > -10) & (Y < 15), Y, p)
        col = c[_indice(vx, 1, np.mean(m["ranura_y"]))]
        m["ranura_suelo_z"] = round(float(Z[col].max() + p / 2), 2)
        tope = c[:, Z > 0.4].any(1)
        m["tope_y"] = _rango(tope, Y, p)
        m["tope_z"] = round(float(Z[c[_indice(vx, 1, np.mean(m["tope_y"]))]].max() + p / 2), 2)
        fila = o[:, _indice(vx, 1, 3.0), :]
        m["ranura_x"] = _rango(~fila[:, (Z > -1.9) & (Z < -0.1)].any(1) & (np.abs(X) < 99), X, p)
        m["tope_x"] = _rango(o[:, _indice(vx, 1, 38.5), :][:, Z > 0.4].any(1), X, p)
        # Chaflán de entrada de la ranura (45°): anchura de la boca (cara superior) frente a la del fondo
        boca = _rango(~c[:, _indice(vx, 2, -0.25)] & (Y > -10) & (Y < 15), Y, p)
        m["chaflan_ranura"] = round(max(0.0, min(m["ranura_y"][0] - boca[0], boca[1] - m["ranura_y"][1])), 2)
        # Chaflán de la arista interior del tope: dónde empieza el tope arriba (casi en su cara superior)
        arriba = _rango(c[:, _indice(vx, 2, m["tope_z"] - 0.25)] & (Y > 30), Y, p)
        m["chaflan_tope"] = round(max(0.0, arriba[0] - m["tope_y"][0] - p / 2), 2) if arriba else 0.0
    elif nombre == "MOVIL-V2":
        aleta = o[:, Y > 3.6, :]
        m["aleta_x"] = _rango(aleta.any((1, 2)), X, p)
        m["aleta_y"] = (3.0, _rango(aleta.any((0, 2)), Y[Y > 3.6], p)[1])
        m["aleta_z"] = _rango(aleta.any((0, 1)), Z, p)
        m["chapa_y"] = _rango(o[:, :, _indice(vx, 2, 35.0)].any(0), Y, p)
    elif nombre == "ANTORCHA-ROBOT-V2":
        anchos = np.array([o[:, :, k].any(1).sum() * p for k in range(len(Z))])
        mango = anchos > 17
        m["mango_z"] = _rango(mango, Z, p)
        m["mango_x"] = _rango(o[:, :, mango].any((1, 2)), X, p)
        m["mango_y"] = _rango(o[:, :, mango].any((0, 2)), Y, p)
        cuerpo = (Z > 30) & (Z < 80)
        m["cuerpo_x"] = _rango(o[:, :, cuerpo].any((1, 2)), X, p)
        m["cuerpo_y"] = _rango(o[:, :, cuerpo].any((0, 2)), Y, p)
    elif nombre == "SOPORTE-ANTORCHA-V2":
        lleno = o.reshape(-1, len(Z)).mean(0)
        m["pie_z"] = _rango(lleno > 0.8, Z, p)
        eje = o[_indice(vx, 0, 0.0), _indice(vx, 1, 0.0), :]
        m["eje_hueco_desde_z"] = round(float(Z[(~eje) & (Z > 1)][0] - p / 2), 2)
        radios = {}
        for k, z in enumerate(Z):
            fila = o[:, _indice(vx, 1, 0.0), k]
            hueco = ~fila & (np.abs(X) < 12)
            r = _rango(hueco, X, p)
            radios[round(float(z), 2)] = round((r[1] - r[0]) / 2, 2) if r and z > 1 else 0.0
        m["radio_interior_por_z"] = radios
        m["tubo_exterior_x"] = _rango(o[:, _indice(vx, 1, 0.0), _indice(vx, 2, 40.0)], X, p)
        fila = o[:, _indice(vx, 1, 0.0), _indice(vx, 2, 40.0)]
        m["tubo_interior_x"] = _rango(~fila & (np.abs(X) < 11), X, p)
        filay = o[_indice(vx, 0, 0.0), :, _indice(vx, 2, 40.0)]
        m["tubo_interior_y"] = _rango(~filay & (np.abs(Y) < 11), Y, p)
    return m


# --- primitivas de colisión ------------------------------------------------------------------------------------------
@dataclass
class Primitiva:
    """Caja (`medio` = semiejes) o cilindro (`medio` = (radio, semialto)) en el marco de uso de la pieza (mm)."""

    nombre: str
    tipo: str  # "caja" | "cilindro"
    centro: tuple
    medio: tuple
    giro: np.ndarray = field(default_factory=lambda: np.eye(3))  # ejes de la primitiva (columnas)


def _semi(r):
    return (r[1] - r[0]) / 2


def _medio(r):
    return (r[0] + r[1]) / 2


def _quitar_voxel(r, p=0.5):
    """El voxelizado engorda medio vóxel por cada lado en los cantos inclinados o redondeados: se quita."""
    return r[0] + p / 2, r[1] - p / 2


ANILLO_LADOS = 16
# Cotas que la validación prueba en lugar de las del CAD para proponer un cambio (p. ej. {"chaflan_ranura": 2.5}).
# Solo cambian la colisión; la malla que se ve es la del CAD. Tras cambiarlas: `primitivas.cache_clear()`.
COTAS_PROPUESTAS: dict[str, float] = {}


def _anillo(prefijo, r_in, r_out, z0, z1, r_in_arriba=None, lados=ANILLO_LADOS):
    """Tubo como corona de `lados` cajas (cara interior a `r_in`); con `r_in_arriba`, en cono (entrada)."""
    out = []
    for k in range(lados):
        a = 2 * np.pi * k / lados
        u = np.array([np.cos(a), np.sin(a), 0.0])
        t = np.array([-np.sin(a), np.cos(a), 0.0])
        if r_in_arriba is None:
            rc, grosor = (r_in + r_out) / 2, (r_out - r_in) / 2
            ancho = r_out * np.tan(np.pi / lados) * 1.02
            out.append(Primitiva(f"{prefijo}_{k}", "caja", tuple(rc * u + [0, 0, (z0 + z1) / 2]),
                                 (grosor, ancho, (z1 - z0) / 2), np.column_stack([u, t, [0, 0, 1.0]])))
        else:
            # placa inclinada: cara interior de r_in (abajo) a r_in_arriba (arriba)
            h = z1 - z0
            n = np.array([r_in_arriba - r_in, 0.0, h])
            lado = np.hypot(r_in_arriba - r_in, h)
            eje = (np.array([(r_in_arriba - r_in) * u[0], (r_in_arriba - r_in) * u[1], h]) / lado)
            normal = np.cross(t, eje)  # hacia fuera
            grosor = 1.5
            centro = ((r_in + r_in_arriba) / 2) * u + [0, 0, (z0 + z1) / 2] + grosor * normal
            ancho = r_out * np.tan(np.pi / lados) * 1.02
            del n
            out.append(Primitiva(f"{prefijo}_{k}", "caja", tuple(centro), (grosor, ancho, lado / 2),
                                 np.column_stack([normal, t, eje])))
    return out


@lru_cache(maxsize=None)
def primitivas(nombre: str) -> tuple[Primitiva, ...]:
    """Colisión de la pieza con primitivas sacadas de `medidas` (marco de uso, mm)."""
    m = medidas(nombre)
    (x0, x1), (y0, y1), (z0, z1) = m["caja"]
    out: list[Primitiva] = []
    if nombre == "BASE-V2":
        rs = m["ranura_suelo_z"]
        ry0, ry1 = m["ranura_y"]
        rx0, rx1 = m["ranura_x"]
        ty0, ty1 = m["tope_y"]
        tx0, tx1 = m["tope_x"]
        out.append(Primitiva("losa", "caja", (0, 0, (z0 + rs) / 2), (x1, y1, (rs - z0) / 2)))
        out.append(Primitiva("losa_extremo_menos", "caja", ((x0 + rx0) / 2, 0, rs / 2), ((rx0 - x0) / 2, y1, -rs / 2)))
        out.append(Primitiva("losa_extremo_mas", "caja", ((rx1 + x1) / 2, 0, rs / 2), ((x1 - rx1) / 2, y1, -rs / 2)))
        ch = min(COTAS_PROPUESTAS.get("chaflan_ranura", m["chaflan_ranura"]), -rs - 0.2)
        e0, e1 = ry0 - ch, ry1 + ch  # bordes de la ranura en la cara superior
        # paredes de la ranura: por debajo del chaflán hasta el borde del fondo, por encima hasta el borde de la boca
        out.append(Primitiva("ranura_lado_menos", "caja", (0, (y0 + ry0) / 2, (rs - ch) / 2),
                             (rx1, (ry0 - y0) / 2, (-ch - rs) / 2)))
        out.append(Primitiva("ranura_lado_mas", "caja", (0, (ry1 + y1) / 2, (rs - ch) / 2),
                             (rx1, (y1 - ry1) / 2, (-ch - rs) / 2)))
        if ch > 0:
            out.append(Primitiva("ranura_boca_menos", "caja", (0, (y0 + e0) / 2, -ch / 2), (rx1, (e0 - y0) / 2, ch / 2)))
            out.append(Primitiva("ranura_boca_mas", "caja", (0, (e1 + y1) / 2, -ch / 2), (rx1, (y1 - e1) / 2, ch / 2)))
            # cuña bajo el plano del chaflán: caja girada 45° alrededor de X con una cara en ese plano
            for lado, (ya, yb) in (("menos", (ry0, e0)), ("mas", (ry1, e1))):
                n = np.array([0.0, np.sign(ya - yb), 1.0]) / np.sqrt(2)  # normal del chaflán: arriba y hacia la ranura
                t = np.cross(n, [1.0, 0, 0])
                medio_plano = np.array([0.0, (ya + yb) / 2, -ch / 2])
                h = ch / np.sqrt(2) / 2
                out.append(Primitiva(f"chaflan_{lado}", "caja", tuple(medio_plano - h * n),
                                     (rx1, ch / np.sqrt(2), h), np.column_stack([[1.0, 0, 0], t, n])))
        tz = m["tope_z"]
        cht = min(COTAS_PROPUESTAS.get("chaflan_tope", m["chaflan_tope"]), tz - 0.2, ty1 - ty0 - 0.2)
        # tope: parte de abajo (hasta donde empieza el chaflán), parte de arriba retranqueada y cuña del chaflán
        out.append(Primitiva("tope", "caja", (_medio((tx0, tx1)), _medio((ty0, ty1)), (tz - cht) / 2),
                             (_semi((tx0, tx1)), _semi((ty0, ty1)), (tz - cht) / 2)))
        if cht > 0:
            out.append(Primitiva("tope_arriba", "caja", (_medio((tx0, tx1)), _medio((ty0 + cht, ty1)), tz - cht / 2),
                                 (_semi((tx0, tx1)), _semi((ty0 + cht, ty1)), cht / 2)))
            n = np.array([0.0, -1.0, 1.0]) / np.sqrt(2)  # el chaflán mira arriba y hacia la chapa (−Y)
            t = np.cross(n, [1.0, 0, 0])
            h = cht / np.sqrt(2) / 2
            medio_plano = np.array([_medio((tx0, tx1)), ty0 + cht / 2, tz - cht / 2])
            out.append(Primitiva("tope_chaflan", "caja", tuple(medio_plano - h * n),
                                 (_semi((tx0, tx1)), cht / np.sqrt(2), h), np.column_stack([[1.0, 0, 0], t, n])))
    elif nombre == "MOVIL-V2":
        cy0, cy1 = m["chapa_y"]
        out.append(Primitiva("chapa", "caja", (0, _medio((cy0, cy1)), _medio((z0, z1))),
                             (x1, _semi((cy0, cy1)), _semi((z0, z1)))))
        ax = _quitar_voxel(m["aleta_x"])
        az = _quitar_voxel(m["aleta_z"])
        ay = m["aleta_y"]
        out.append(Primitiva("aleta", "caja", (_medio(ax), _medio(ay), _medio(az)),
                             (_semi(ax), _semi(ay), _semi(az))))
    elif nombre == "ANTORCHA-ROBOT-V2":
        mz0, mz1 = m["mango_z"]
        out.append(Primitiva("mango", "caja", (_medio(m["mango_x"]), _medio(m["mango_y"]), _medio((mz0, mz1))),
                             (_semi(m["mango_x"]), _semi(m["mango_y"]), _semi((mz0, mz1)))))
        r = _semi(m["cuerpo_y"])
        out.append(Primitiva("cuerpo", "cilindro", (0, 0, (12.0 + mz0) / 2), (r, (mz0 - 12.0) / 2)))
        out.append(Primitiva("punta", "cilindro", (0, 0, 6.0), (3.0, 6.0)))  # cono Ø6→Ø14 de la punta
    elif nombre == "SOPORTE-ANTORCHA-V2":
        pz0, pz1 = m["pie_z"]
        out.append(Primitiva("pie", "caja", (0, 0, _medio((pz0, pz1))), (x1, y1, _semi((pz0, pz1)))))
        radios = m["radio_interior_por_z"]
        r_in = float(np.median([r for z, r in radios.items() if pz1 + 2 < z < 50])) + 0.25  # medio vóxel
        r_out = _semi(m["tubo_exterior_x"])
        z_cono = min(z for z, r in radios.items() if z > 40 and r > r_in + 0.4) - 0.75
        r_boca = max(radios.values()) + 0.25
        out += _anillo("tubo", r_in, r_out, pz1, z_cono)
        out += _anillo("entrada", r_in, r_out, z_cono, z1, r_in_arriba=r_boca)
    return tuple(out)


def _dentro(prim: Primitiva, P: np.ndarray) -> np.ndarray:
    L = (P - np.asarray(prim.centro)) @ prim.giro  # coordenadas en los ejes de la primitiva
    if prim.tipo == "caja":
        return np.all(np.abs(L) <= np.asarray(prim.medio), axis=-1)
    r, h = prim.medio
    return (np.hypot(L[..., 0], L[..., 1]) <= r) & (np.abs(L[..., 2]) <= h)


@lru_cache(maxsize=None)
def ajuste_colision(nombre: str) -> Ajuste:
    """Malla frente a primitivas de colisión, en la rejilla del voxelizado (0,5 mm)."""
    vx = voxeles(nombre)
    X, Y, Z = np.meshgrid(vx.centros(0), vx.centros(1), vx.centros(2), indexing="ij")
    P = np.stack([X, Y, Z], axis=-1)
    occ = np.zeros(vx.ocupado.shape, dtype=bool)
    for prim in primitivas(nombre):
        occ |= _dentro(prim, P)
    return comparar(vx, occ)
