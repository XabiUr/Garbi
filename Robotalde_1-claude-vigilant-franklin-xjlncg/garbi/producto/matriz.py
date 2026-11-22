"""La matriz del equipo: puntos marcados a mano sobre el tapete con la postura del robot junto a la broca apoyada.
Da la postura (6 grados) para cualquier punto del tapete.

    m = cargar_matriz("matriz.csv")                    # o .json; posicion="auto" | "uv" | "xy"
    q = m.postura_px((320, 240))                       # punto de la cámara de arriba → 6 grados
    q_barrer = m.postura_px((320, 240), offset=[0, -8, 4, 0, 0, 0])   # + offset de altura para barrer

Formato esperado (el definitivo aún no se conoce: se aceptan variantes razonables)
-------------------------------------------------------------------------------
Una fila (CSV) u objeto (JSON) por punto marcado, con:

- **Posición**: `u, v` en píxeles de la cámara de arriba, **o** `x, y` en mm del tapete (origen en la esquina
  superior izquierda del tapete tal y como se ve en la cámara de arriba, x hacia la derecha e y hacia abajo; para
  pasar de píxeles a mm se usa la homografía de las 4 esquinas del tapete de la configuración).
  Alias aceptados: u ← `u, px, pixel_x, x_px, cx, col_px`; v ← `v, py, pixel_y, y_px, cy, row_px`;
  x ← `x, x_mm, mm_x`; y ← `y, y_mm, mm_y`. En JSON también `"uv": [u, v]`, `"px": [u, v]` o `"xy": [x, y]`.
  Con `posicion="uv"`, unas columnas `x, y` se leen como píxeles.
- **Articulaciones** (grados de LeRobot): `shoulder_pan, shoulder_lift, elbow_flex, wrist_flex, wrist_roll,
  gripper`, con o sin `.pos`, o los alias `pan/base/j1/q1`, `lift/hombro/j2`, `elbow/codo/j3`, `flex/muneca/j4`,
  `roll/giro/j5`, `pinza/j6`. Si faltan `gripper` o `wrist_roll` (5 + pinza o solo 4), se rellenan con los valores
  de la configuración. En JSON también una lista de 6 (o 5) en `"q"`, `"postura"`, `"joints"` o `"articulaciones"`.
- JSON: una lista de objetos, o `{"puntos": [...]}` (también `points`, `datos`, `data`).
- Las columnas que no se reconocen (índice, nombre, notas...) se ignoran. Nombres sin mayúsculas, tildes ni espacios.

Interpolación
-------------
- **Rejilla regular** (la del equipo: 5 × 3 = 15 puntos): si los puntos forman filas y columnas (aunque la rejilla
  esté algo torcida en la imagen) se interpola **bilineal por celdas**.
- **General**: triangulación de Delaunay (`cv2.Subdiv2D`) con interpolación lineal baricéntrica dentro.
- **Fuera**: en la rejilla, extrapolación lineal de la celda del borde hasta `extrapolar_max` (más lejos se recorta
  al borde de ese margen); en la triangulación, IDW de los 3 vecinos más cercanos. Siempre se avisa
  (`Matriz.fuera` queda a True en la última consulta).
"""
from __future__ import annotations

import csv
import json
import logging
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from garbi.tipos import ARTICULACIONES

log = logging.getLogger("garbi.producto")

ALIAS_POSICION = {
    "u": ("u", "px", "pixel_x", "x_px", "cx", "col_px", "u_px"),
    "v": ("v", "py", "pixel_y", "y_px", "cy", "row_px", "v_px"),
    "x": ("x", "x_mm", "mm_x"),
    "y": ("y", "y_mm", "mm_y"),
}
ALIAS_ARTICULACIONES = {
    "shoulder_pan": ("shoulder_pan", "pan", "base", "j1", "q1", "hombro_giro"),
    "shoulder_lift": ("shoulder_lift", "lift", "hombro", "j2", "q2"),
    "elbow_flex": ("elbow_flex", "elbow", "codo", "j3", "q3"),
    "wrist_flex": ("wrist_flex", "flex", "muneca", "muneca_flex", "j4", "q4"),
    "wrist_roll": ("wrist_roll", "roll", "giro", "muneca_giro", "j5", "q5"),
    "gripper": ("gripper", "pinza", "j6", "q6"),
}
CLAVES_LISTA_Q = ("q", "postura", "joints", "articulaciones", "angulos", "pose")
CLAVES_LISTA_UV = ("uv", "px", "pixel", "pixeles")
CLAVES_LISTA_XY = ("xy", "mm", "pos_mm")


def normalizar_nombre(nombre: str) -> str:
    """`" Shoulder-Pan.pos "` → `"shoulder_pan"` (sin tildes, minúsculas, sin `.pos`)."""
    s = unicodedata.normalize("NFKD", str(nombre)).encode("ascii", "ignore").decode().strip().lower()
    for sufijo in (".pos", "_pos", "_deg", "_grados"):
        if s.endswith(sufijo):
            s = s[: -len(sufijo)]
    return s.replace(" ", "_").replace("-", "_").replace(".", "_")


# --- lectura ---------------------------------------------------------------------------------------------------------
def _filas_json(datos) -> list[dict]:
    if isinstance(datos, dict):
        for k in ("puntos", "points", "datos", "data", "matriz"):
            if k in datos:
                return _filas_json(datos[k])
        raise ValueError("JSON de la matriz: se esperaba una lista de puntos o {'puntos': [...]}")
    filas = []
    for obj in datos:
        fila = {}
        for k, v in obj.items():
            n = normalizar_nombre(k)
            if isinstance(v, (list, tuple)):
                if n in CLAVES_LISTA_Q:
                    nombres = list(ARTICULACIONES) if len(v) >= 6 else [a for a in ARTICULACIONES if a != "gripper"]
                    if len(v) == 4:
                        nombres = list(ARTICULACIONES[:4])
                    fila.update({a: x for a, x in zip(nombres, v)})
                elif n in CLAVES_LISTA_UV:
                    fila["u"], fila["v"] = v[0], v[1]
                elif n in CLAVES_LISTA_XY:
                    fila["x"], fila["y"] = v[0], v[1]
            elif isinstance(v, dict):
                fila.update({normalizar_nombre(kk): vv for kk, vv in v.items()})
            else:
                fila[n] = v
        filas.append(fila)
    return filas


def _filas_csv(texto: str) -> list[dict]:
    muestra = texto[:2048]
    try:
        dialecto = csv.Sniffer().sniff(muestra, delimiters=",;\t")
    except csv.Error:
        dialecto = csv.excel
    lector = csv.DictReader([l for l in texto.splitlines() if l.strip() and not l.lstrip().startswith("#")],
                            dialect=dialecto)
    return [{normalizar_nombre(k): v for k, v in fila.items() if k is not None} for fila in lector]


def _a_float(v) -> float:
    if isinstance(v, str):
        v = v.strip().replace(",", ".") if v.count(",") == 1 and "." not in v else v.strip()
    return float(v)


def _buscar(columnas: set[str], alias: tuple[str, ...]) -> str | None:
    return next((a for a in alias if a in columnas), None)


def leer_puntos(ruta: str | Path, posicion: str = "auto", wrist_roll: float = 0.0,
                pinza: float = 0.0) -> tuple[np.ndarray, np.ndarray, str]:
    """(puntos N×2, posturas N×6, unidades "px" | "mm") del archivo de la matriz (CSV o JSON)."""
    ruta = Path(ruta)
    texto = ruta.read_text(encoding="utf-8-sig")
    if ruta.suffix.lower() == ".json" or texto.lstrip()[:1] in "[{":
        filas = _filas_json(json.loads(texto))
    else:
        filas = _filas_csv(texto)
    if not filas:
        raise ValueError(f"la matriz {ruta} está vacía")
    columnas = set().union(*(f.keys() for f in filas))
    cu, cv = _buscar(columnas, ALIAS_POSICION["u"]), _buscar(columnas, ALIAS_POSICION["v"])
    cx, cy = _buscar(columnas, ALIAS_POSICION["x"]), _buscar(columnas, ALIAS_POSICION["y"])
    if posicion == "uv":
        cols, unidades = ((cu, cv) if cu and cv else (cx, cy)), "px"
    elif posicion == "xy":
        cols, unidades = (cx, cy), "mm"
    else:
        cols, unidades = ((cu, cv), "px") if cu and cv else ((cx, cy), "mm")
    if not all(cols):
        raise ValueError(f"la matriz {ruta} no tiene columnas de posición reconocibles (u,v o x,y): {sorted(columnas)}")
    nombres_q = {a: _buscar(columnas, ALIAS_ARTICULACIONES[a]) for a in ARTICULACIONES}
    faltan = [a for a in ARTICULACIONES[:4] if nombres_q[a] is None]
    if faltan:
        raise ValueError(f"la matriz {ruta} no tiene las articulaciones {faltan}: columnas {sorted(columnas)}")
    rellenos = {"wrist_roll": wrist_roll, "gripper": pinza}
    puntos, posturas = [], []
    for i, f in enumerate(filas):
        try:
            p = [_a_float(f[cols[0]]), _a_float(f[cols[1]])]
            q = [_a_float(f[nombres_q[a]]) if nombres_q[a] and f.get(nombres_q[a]) not in (None, "")
                 else float(rellenos[a]) for a in ARTICULACIONES]
        except (KeyError, TypeError, ValueError) as e:
            log.warning("matriz %s: fila %d ignorada (%s)", ruta.name, i + 1, e)
            continue
        puntos.append(p)
        posturas.append(q)
    if len(puntos) < 3:
        raise ValueError(f"la matriz {ruta} tiene menos de 3 puntos válidos")
    return np.array(puntos, float), np.array(posturas, float), unidades


# --- rejilla regular -------------------------------------------------------------------------------------------------
def detectar_rejilla(puntos: np.ndarray) -> np.ndarray | None:
    """Índices R × C (filas × columnas) si los puntos forman una rejilla (filas separadas en v, columnas ordenadas en
    u en todas las filas); None si no. Prueba todas las factorizaciones R × C con R, C ≥ 2 y las dos orientaciones."""
    n = len(puntos)
    mejor, mejor_nota = None, 0.0
    for eje in (1, 0):  # 1: filas por v (lo normal); 0: filas por u
        otro = 1 - eje
        orden = np.argsort(puntos[:, eje], kind="stable")
        for r in range(2, n // 2 + 1):
            if n % r or n // r < 2:
                continue
            c = n // r
            filas = [orden[i * c:(i + 1) * c] for i in range(r)]
            filas = [f[np.argsort(puntos[f, otro], kind="stable")] for f in filas]
            idx = np.array(filas)
            # separación entre filas (en el eje de las filas) frente a la dispersión dentro de cada fila
            vals = puntos[idx, eje]
            hueco = np.min(vals[1:].min(axis=1) - vals[:-1].max(axis=1))
            dispersion = np.max(vals.max(axis=1) - vals.min(axis=1)) + 1e-9
            # las columnas: cada columna j está a la izquierda de la j+1 en todas las filas
            col = puntos[idx, otro]
            if hueco <= 0 or np.any(np.diff(col, axis=1) <= 0):
                continue
            nota = hueco / dispersion
            if nota > mejor_nota:
                mejor, mejor_nota = idx, nota
    return mejor if mejor_nota > 1.0 else None


def _bilineal(P: np.ndarray, s: float, t: float) -> np.ndarray:
    """P: 2×2×k (P[0,0] esquina (fila 0, col 0)...). s a lo largo de las columnas, t de las filas."""
    return (1 - s) * (1 - t) * P[0, 0] + s * (1 - t) * P[0, 1] + (1 - s) * t * P[1, 0] + s * t * P[1, 1]


def inversa_bilineal(P: np.ndarray, p: np.ndarray, iteraciones: int = 25) -> tuple[float, float]:
    """(s, t) con _bilineal(P, s, t) = p (Newton; sin recortar a [0, 1])."""
    s = t = 0.5
    for _ in range(iteraciones):
        f = _bilineal(P, s, t) - p
        ds = (1 - t) * (P[0, 1] - P[0, 0]) + t * (P[1, 1] - P[1, 0])
        dt = (1 - s) * (P[1, 0] - P[0, 0]) + s * (P[1, 1] - P[0, 1])
        J = np.stack([ds, dt], axis=1)
        try:
            d = np.linalg.solve(J, f)
        except np.linalg.LinAlgError:
            break
        s, t = s - d[0], t - d[1]
        if np.max(np.abs(d)) < 1e-10:
            break
    return float(s), float(t)


def _punto_en_segmento(p, a, b):
    ab = b - a
    k = np.clip(np.dot(p - a, ab) / max(np.dot(ab, ab), 1e-12), 0.0, 1.0)
    return a + k * ab


def _dentro_poligono(p, poligono) -> bool:
    x, y = p
    dentro = False
    n = len(poligono)
    for i in range(n):
        x1, y1 = poligono[i]
        x2, y2 = poligono[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1 + 1e-300) + x1:
            dentro = not dentro
    return dentro


# --- Delaunay --------------------------------------------------------------------------------------------------------
def triangular(puntos: np.ndarray) -> np.ndarray:
    """Triángulos (T × 3 índices) de la triangulación de Delaunay de los puntos (cv2.Subdiv2D)."""
    import cv2

    lo, hi = puntos.min(axis=0), puntos.max(axis=0)
    margen = float(np.max(hi - lo)) + 10.0
    rect = (int(np.floor(lo[0] - margen)), int(np.floor(lo[1] - margen)),
            int(np.ceil(hi[0] - lo[0] + 2 * margen)) + 1, int(np.ceil(hi[1] - lo[1] + 2 * margen)) + 1)
    sub = cv2.Subdiv2D(rect)
    for p in puntos:
        sub.insert((float(p[0]), float(p[1])))
    tris = []
    for t in sub.getTriangleList().reshape(-1, 3, 2):
        d = np.linalg.norm(puntos[None, :, :] - t[:, None, :], axis=2)
        idx = d.argmin(axis=1)
        if np.all(d[np.arange(3), idx] < 1e-2) and len(set(idx.tolist())) == 3:
            tris.append(sorted(idx.tolist()))
    tris = np.unique(np.array(tris, int).reshape(-1, 3), axis=0)
    # sin triángulos degenerados
    a, b, c = (puntos[tris[:, i]] for i in range(3))
    area = np.abs((b - a)[:, 0] * (c - a)[:, 1] - (b - a)[:, 1] * (c - a)[:, 0])
    return tris[area > 1e-9]


# --- la matriz -------------------------------------------------------------------------------------------------------
def homografia_tapete(esquinas_px, tapete_mm) -> np.ndarray:
    """Homografía píxeles → mm del tapete con las 4 esquinas (sup-izq, sup-der, inf-der, inf-izq en la imagen)."""
    import cv2

    from garbi.producto.barridos import ordenar_esquinas

    ancho, alto = float(tapete_mm[0]), float(tapete_mm[1])
    destino = np.array([[0, 0], [ancho, 0], [ancho, alto], [0, alto]], np.float32)
    return cv2.getPerspectiveTransform(ordenar_esquinas(esquinas_px).astype(np.float32), destino)


def aplicar_homografia(H: np.ndarray, p) -> np.ndarray:
    v = H @ np.array([float(p[0]), float(p[1]), 1.0])
    return v[:2] / v[2]


@dataclass
class Matriz:
    puntos: np.ndarray                # N × 2 (unidades de la matriz)
    posturas: np.ndarray              # N × 6 (grados)
    unidades: str = "px"              # "px" o "mm"
    homografia: np.ndarray | None = None   # px → mm (solo si unidades == "mm")
    extrapolar_max: float = 80.0      # en las unidades de la matriz
    rejilla: np.ndarray | None = field(default=None, init=False)     # R × C índices, si es rejilla
    triangulos: np.ndarray = field(default=None, init=False)
    fuera: bool = field(default=False, init=False)                   # la última consulta cayó fuera
    avisar: bool = field(default=True, init=False)                   # False = sin avisos por punto (barridos)
    _avisos: int = field(default=0, init=False, repr=False)

    def __post_init__(self):
        self.puntos = np.asarray(self.puntos, float).reshape(-1, 2)
        self.posturas = np.asarray(self.posturas, float).reshape(-1, 6)
        if len(self.puntos) != len(self.posturas):
            raise ValueError("la matriz tiene distinto número de puntos y de posturas")
        self.rejilla = detectar_rejilla(self.puntos) if len(self.puntos) >= 4 else None
        self.triangulos = triangular(self.puntos) if self.rejilla is None else np.zeros((0, 3), int)
        if self.rejilla is not None:
            r = self.rejilla
            borde = list(r[0]) + list(r[1:, -1]) + list(r[-1, -2::-1]) + list(r[-2:0:-1, 0])
            self.contorno = self.puntos[borde]
        else:
            self.contorno = None

    @property
    def tipo(self) -> str:
        if self.rejilla is not None:
            return f"rejilla {self.rejilla.shape[0]}×{self.rejilla.shape[1]}"
        return f"Delaunay ({len(self.triangulos)} triángulos)"

    def __len__(self) -> int:
        return len(self.puntos)

    def _avisar(self, p, como: str) -> None:
        self.fuera = True
        if not self.avisar:
            return
        self._avisos += 1
        if self._avisos <= 5 or self._avisos % 100 == 0:
            log.warning("matriz: el punto (%.0f, %.0f) cae fuera de los puntos marcados (%s)", p[0], p[1], como)

    # --- rejilla ---
    def _celdas(self):
        r = self.rejilla
        for i in range(r.shape[0] - 1):
            for j in range(r.shape[1] - 1):
                yield r[i:i + 2, j:j + 2]

    def _interpolar_rejilla(self, p: np.ndarray) -> np.ndarray:
        dentro = _dentro_poligono(p, self.contorno)
        if not dentro:
            # el punto más cercano del contorno; si está muy lejos, se recorta a extrapolar_max
            n = len(self.contorno)
            cercanos = [_punto_en_segmento(p, self.contorno[k], self.contorno[(k + 1) % n]) for k in range(n)]
            pb = min(cercanos, key=lambda c: np.linalg.norm(p - c))
            d = float(np.linalg.norm(p - pb))
            if d > self.extrapolar_max:
                p = pb + (p - pb) * (self.extrapolar_max / d)
                self._avisar(p, f"a {d:.0f}, recortado a {self.extrapolar_max:.0f}")
            else:
                self._avisar(p, f"extrapolado {d:.0f}")
        mejor = None
        for idx in self._celdas():
            P = self.puntos[idx]
            s, t = inversa_bilineal(P, p)
            exceso = max(0.0, -s, s - 1, -t, t - 1)
            if mejor is None or exceso < mejor[0]:
                mejor = (exceso, idx, s, t)
            if exceso <= 1e-9:
                break
        _, idx, s, t = mejor
        return _bilineal(self.posturas[idx], s, t)

    # --- Delaunay ---
    def _interpolar_delaunay(self, p: np.ndarray) -> np.ndarray:
        if len(self.triangulos):
            a, b, c = (self.puntos[self.triangulos[:, i]] for i in range(3))
            v0, v1, v2 = b - a, c - a, p[None, :] - a
            den = v0[:, 0] * v1[:, 1] - v1[:, 0] * v0[:, 1]
            l1 = (v2[:, 0] * v1[:, 1] - v1[:, 0] * v2[:, 1]) / den
            l2 = (v0[:, 0] * v2[:, 1] - v2[:, 0] * v0[:, 1]) / den
            l0 = 1 - l1 - l2
            ok = np.where((l0 >= -1e-9) & (l1 >= -1e-9) & (l2 >= -1e-9))[0]
            if len(ok):
                k = ok[0]
                tri = self.triangulos[k]
                return l0[k] * self.posturas[tri[0]] + l1[k] * self.posturas[tri[1]] + l2[k] * self.posturas[tri[2]]
        d = np.linalg.norm(self.puntos - p[None, :], axis=1)
        vecinos = np.argsort(d)[:3]
        self._avisar(p, f"IDW de {len(vecinos)} vecinos, el más cercano a {d[vecinos[0]]:.0f}")
        if d[vecinos[0]] < 1e-9:
            return self.posturas[vecinos[0]].copy()
        w = 1.0 / d[vecinos] ** 2
        return (w[:, None] * self.posturas[vecinos]).sum(axis=0) / w.sum()

    # --- consultas ---
    def interpolar(self, p) -> np.ndarray:
        """Postura (6 grados) en el punto `p`, en las unidades de la matriz."""
        p = np.asarray(p, float).reshape(2)
        self.fuera = False
        if self.rejilla is not None:
            return self._interpolar_rejilla(p)
        return self._interpolar_delaunay(p)

    def a_unidades(self, uv) -> np.ndarray:
        """Píxeles de la cámara de arriba → unidades de la matriz."""
        uv = np.asarray(uv, float).reshape(2)
        if self.unidades == "px":
            return uv
        if self.homografia is None:
            raise ValueError("la matriz va en mm y no hay homografía píxeles → mm (esquinas del tapete)")
        return aplicar_homografia(self.homografia, uv)

    def postura_px(self, uv, offset=None) -> np.ndarray:
        """Postura (6 grados) para un punto de la cámara de arriba, más el `offset` de altura (6 grados) si se da."""
        q = self.interpolar(self.a_unidades(uv))
        if offset is not None:
            q = q + np.asarray(offset, float).reshape(6)
        return q


def cargar_matriz(ruta: str | Path, posicion: str = "auto", wrist_roll: float = 0.0, pinza: float = 0.0,
                  esquinas_tapete_px=None, tapete_mm=(600.0, 400.0), extrapolar_max_px: float = 80.0) -> Matriz:
    """Lee la matriz (CSV o JSON, ver el docstring del módulo). Si va en mm, `esquinas_tapete_px` y `tapete_mm`
    dan la homografía píxeles → mm."""
    puntos, posturas, unidades = leer_puntos(ruta, posicion, wrist_roll, pinza)
    H, extrapolar = None, extrapolar_max_px
    if unidades == "mm":
        if esquinas_tapete_px is not None:
            H = homografia_tapete(esquinas_tapete_px, tapete_mm)
            from garbi.producto.barridos import ordenar_esquinas

            e = ordenar_esquinas(esquinas_tapete_px)
            extrapolar = extrapolar_max_px * float(tapete_mm[0]) / max(float(np.linalg.norm(e[1] - e[0])), 1e-9)
        else:
            log.warning("matriz en mm sin esquinas del tapete: postura_px no funcionará (usa interpolar en mm)")
    m = Matriz(puntos, posturas, unidades, H, extrapolar)
    log.info("matriz %s: %d puntos en %s, %s", Path(ruta).name, len(m), unidades, m.tipo)
    return m


def matriz_desde_config(cfg) -> Matriz:
    """La matriz de un `ConfigProducto`."""
    mc = cfg.matriz
    return cargar_matriz(mc.ruta, mc.posicion, mc.wrist_roll, mc.pinza, cfg.tapete_px, mc.tapete_mm,
                         mc.extrapolar_max_px)
