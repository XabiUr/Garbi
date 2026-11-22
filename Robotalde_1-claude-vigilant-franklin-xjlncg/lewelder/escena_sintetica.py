"""Escena estéreo sintética (v2): lo que verían las dos webcams de la mesa de montaje, sin hardware.

Pinta, para cada cámara de `CAMARAS_ESTEREO`, la mesa, la **base** (tumbada, en cualquier pose), la **chapa móvil** en
cualquier pose 3D (tumbada en la zona libre, de pie en T o en esquina, a medio colocar) con su aleta, los **ArUco** de
cada chapa (uno por cara de la móvil) en perspectiva correcta y el **LED** de la antorcha en un punto 3D.

Cómo: un rasterizador mínimo con z-buffer. Cada cara de cada caja es un rectángulo plano; para cada píxel de su
recuadro se corta el rayo de la cámara con el plano, se mira si cae dentro y si está más cerca que lo ya pintado. Así
la oclusión sale sola (una cara de espaldas no se pinta; la chapa de pie tapa lo que hay detrás). Los ArUco son
calcomanías sobre su cara (misma profundidad con un pequeño margen) muestreadas con interpolación bilineal, así que
sus bordes tienen la precisión subpíxel de la textura. El LED se tapa si el segmento cámara-LED atraviesa una caja.

La luz, la exposición, el desenfoque, el ruido y el perfil del LED son los de `CamaraSintetica` (se reutilizan sus
cámaras). Cada par de imágenes va con su `VerdadEscena`.
Unidades: mm. Poses: `Pose` de `juntas.py` (`p_mesa = R @ p_chapa + t`).
"""
from __future__ import annotations

import struct
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

from lewelder.camara_sintetica import (
    COLOR_BASE,
    COLOR_PIEZA,
    COLORES_LED_BGR,
    GANANCIA,
    LUZ_DIR,
    PERFIL_LED,
    RADIO_LED,
    CamaraSintetica,
    PoseCamara,
    _segmento_corta_caja,
    textura_tablero,
)
from lewelder.contrato import CAMARAS_ESTEREO, COLOR_LED, ID_BASE
from lewelder.juntas import CAJA_ALETA, CAJA_BASE, CAJA_MOVIL, CAJA_TOPE, MARCADORES, PARES_MOVIL, Pose

COLOR_MOVIL = COLOR_PIEZA
COLOR_MANO = (0.45, 0.55, 0.75)  # BGR, piel
# Margen de profundidad (mm) de una calcomanía sobre su cara.
SESGO_CALCOMANIA = 0.5
# Fracción de la calcomanía que tiene que verse para contarla como visible en la verdad.
VISIBLE_MIN = 0.95




def pose_camara_estereo(nombre: str, poses: dict | None = None) -> PoseCamara:
    """`PoseCamara` de la cámara `nombre` ("a" o "b") con `poses` (por defecto `CAMARAS_ESTEREO` del contrato)."""
    p = (poses or CAMARAS_ESTEREO)[nombre]
    return PoseCamara.por_defecto(p["altura"], p["inclinacion"], p["objetivo"], p["azimut"])


@dataclass
class Caja:
    """Caja `lim` (xmin, xmax, ymin, ymax, zmin, zmax) de un marco con pose `pose` (→ mesa)."""

    lim: tuple[float, ...]
    pose: Pose
    color: tuple[float, float, float]


@dataclass
class VerdadEscena:
    base: Pose | None
    movil: Pose | None
    led: tuple[float, float, float] | None  # marco de la mesa
    exposicion: str
    pixel_led: dict[str, tuple[float, float] | None] = field(default_factory=dict)
    marcadores_visibles: dict[str, set[int]] = field(default_factory=dict)


def _caras(lim) -> list[tuple[np.ndarray, np.ndarray, np.ndarray, float, float]]:
    """Caras de una caja en su marco: (centro, eje_x, eje_y, ancho, alto) con eje_x × eje_y hacia fuera."""
    x0, x1, y0, y1, z0, z1 = lim
    c = np.array([(x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2])
    dx, dy, dz = x1 - x0, y1 - y0, z1 - z0
    X, Y, Z = np.eye(3)
    return [
        (c + Z * dz / 2, X, Y, dx, dy), (c - Z * dz / 2, Y, X, dy, dx),
        (c + Y * dy / 2, Z, X, dz, dx), (c - Y * dy / 2, X, Z, dx, dz),
        (c + X * dx / 2, Y, Z, dy, dz), (c - X * dx / 2, Z, Y, dz, dy),
    ]


# --- CAD ---------------------------------------------------------------------------------------------------------
CARPETA_STL = Path(__file__).resolve().parents[1] / "hardware" / "v2" / "cad" / "stl"
# STL de SolidWorks (Y arriba) → marco de la chapa: p_chapa = M @ p_stl + d (la misma M para las dos piezas).
_M_STL = np.array([[1.0, 0.0, 0.0], [0.0, 0.0, -1.0], [0.0, 1.0, 0.0]])
STL_A_CHAPA = {"base": ("BASE-V2.STL", np.array([-100.0, 40.0, -6.0])),
               "movil": ("MOVIL-V2.STL", np.array([-70.0, 21.0, 0.0]))}
HUECO_PEGATINA = 0.3  # mm: las pegatinas van en un rebaje de 35,4 x 35,4 x 0,3
GROSOR_PEGATINA = 0.1


def leer_stl(ruta) -> tuple[np.ndarray, np.ndarray]:
    """(triángulos (N, 3, 3), normales (N, 3)) de un STL binario."""
    datos = Path(ruta).read_bytes()
    n = struct.unpack("<I", datos[80:84])[0]
    if 84 + 50 * n != len(datos):
        raise ValueError(f"{ruta}: solo se leen STL binarios")
    tipo = np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")])
    registros = np.frombuffer(datos, dtype=tipo, count=n, offset=84)
    return registros["v"].astype(np.float64), registros["n"].astype(np.float64)


def malla_cad(chapa: str) -> tuple[np.ndarray, np.ndarray]:
    """Malla del CAD de la `chapa` ("base" o "movil") en el marco de la chapa: (triángulos, normales)."""
    archivo, d = STL_A_CHAPA[chapa]
    tri, normales = leer_stl(CARPETA_STL / archivo)
    return tri @ _M_STL.T + d, normales @ _M_STL.T


@dataclass
class Malla:
    """Triángulos (N, 3, 3) y normales (N, 3) de un marco con pose `pose` (→ mesa)."""

    triangulos: np.ndarray
    normales: np.ndarray
    pose: Pose
    color: tuple[float, float, float]


class EscenaSintetica:
    """Dos cámaras sintéticas ("a" y "b") mirando la mesa de montaje.

    `geometria`: "cajas" (base, tope, móvil y aleta como cajas; rápido, para los tests) o "cad" (las mallas STL de
    `hardware/v2/cad/stl` con sus chaflanes, la ranura, el tope y los rebajes de las pegatinas; para validar el CAD).
    """

    def __init__(self, poses: dict[str, PoseCamara] | None = None, ancho: int = 1280, alto: int = 720, K=None,
                 semilla: int = 0, ruido: float = 2.0, desenfoque: float = 0.6, geometria: str = "cajas"):
        self.geometria = geometria
        self._mallas = {c: malla_cad(c) for c in ("base", "movil")} if geometria == "cad" else {}
        poses = poses or {n: pose_camara_estereo(n) for n in ("a", "b")}
        self.camaras = {n: CamaraSintetica(K, p, ancho, alto, semilla=semilla + 101 * i, ruido=ruido,
                                           desenfoque=desenfoque) for i, (n, p) in enumerate(poses.items())}
        self.ancho, self.alto = ancho, alto
        self._fondos: dict[str, np.ndarray] = {}
        self._campos_ruido: dict[int, list[np.ndarray]] = {}
        self._estaticas: dict[tuple, tuple] = {}  # escena sin LED (imagen expuesta, marcadores visibles) por cámara
        self._tablero = textura_tablero()

    # --- rasterizador ------------------------------------------------------------------------------------------
    @staticmethod
    def _rasterizar(img, zbuf, cam: CamaraSintetica, centro, ex, ey, ancho, alto, color=None, tex=None,
                    sesgo: float = 0.0, escribir_z: bool = True) -> tuple[int, int]:
        """Pinta el rectángulo (centro, ejes unitarios ex/ey en la mesa, ancho x alto mm) con z-buffer.

        Con `tex`, la fila 0 de la textura queda en +ey y la columna 0 en -ex. Devuelve (píxeles pintados, píxeles
        del rectángulo dentro de la imagen) para saber qué parte se ve.
        """
        R, t, K = cam.pose.R, cam.pose.t, cam.K
        centro, ex, ey = (np.asarray(v, dtype=float) for v in (centro, ex, ey))
        esquinas = centro + np.array([[-1, -1], [1, -1], [1, 1], [-1, 1]]) @ np.vstack([ex * ancho / 2,
                                                                                       ey * alto / 2])
        pc = esquinas @ R.T + t
        if (pc[:, 2] <= 1.0).any():
            return 0, 0
        uv = pc[:, :2] / pc[:, 2:3] * [K[0, 0], K[1, 1]] + [K[0, 2], K[1, 2]]
        x0, y0 = np.maximum(np.floor(uv.min(axis=0)).astype(int), 0)
        x1 = min(int(np.ceil(uv[:, 0].max())) + 1, img.shape[1])
        y1 = min(int(np.ceil(uv[:, 1].max())) + 1, img.shape[0])
        if x1 <= x0 or y1 <= y0:
            return 0, 0
        us, vs = np.meshgrid(np.arange(x0, x1, dtype=np.float64), np.arange(y0, y1, dtype=np.float64))
        dx, dy = (us - K[0, 2]) / K[0, 0], (vs - K[1, 2]) / K[1, 1]
        o, n = R @ centro + t, R @ np.cross(ex, ey)
        exc, eyc = R @ ex, R @ ey
        denom = n[0] * dx + n[1] * dy + n[2]
        with np.errstate(divide="ignore", invalid="ignore"):
            z = np.dot(n, o) / denom
        px, py, pz = z * dx - o[0], z * dy - o[1], z - o[2]
        a = px * exc[0] + py * exc[1] + pz * exc[2]
        b = px * eyc[0] + py * eyc[1] + pz * eyc[2]
        dentro = (np.abs(a) <= ancho / 2) & (np.abs(b) <= alto / 2) & (z > 0)
        zb = zbuf[y0:y1, x0:x1]
        visible = dentro & (z < zb + sesgo)
        if not visible.any():
            return 0, int(dentro.sum())
        roi = img[y0:y1, x0:x1]
        if tex is not None:
            ht, wt = tex.shape[:2]
            mx = ((a + ancho / 2) / ancho * wt - 0.5).astype(np.float32)
            my = ((alto / 2 - b) / alto * ht - 0.5).astype(np.float32)
            muestra = cv2.remap(tex, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
            roi[visible] = muestra[visible] * (color if color is not None else 1.0)
        else:
            roi[visible] = color
        if escribir_z:
            zb[visible] = z[visible]
        return int(visible.sum()), int(dentro.sum())

    def _fondo(self, nombre: str) -> np.ndarray:
        """Pared y mesa de madera (float32 0-255), sin piezas."""
        if nombre not in self._fondos:
            cam = self.camaras[nombre]
            img = np.full((self.alto, self.ancho, 3), 40, np.uint8)
            mesa = cam._textura_mesa()
            cam._pegar_plano(img, mesa, (250.0, 0.0, 0.0), np.array([1.0, 0, 0]), np.array([0, 1.0, 0]),
                             mesa.shape[1], mesa.shape[0])
            self._fondos[nombre] = img.astype(np.float32)
        return self._fondos[nombre]

    @staticmethod
    def _luz(normal) -> float:
        return 0.55 + 0.45 * max(0.0, float(np.dot(normal, LUZ_DIR)))

    def _pintar_caja(self, img, zbuf, cam, caja: Caja) -> None:
        c = cam.pose.centro
        for centro, ex, ey, ancho, alto in _caras(caja.lim):
            centro_m = caja.pose.aplicar(centro)
            exm, eym = caja.pose.R @ ex, caja.pose.R @ ey
            n = np.cross(exm, eym)
            if np.dot(n, c - centro_m) <= 0:
                continue  # cara de espaldas
            color = np.asarray(caja.color, np.float32) * 255 * self._luz(n)
            self._rasterizar(img, zbuf, cam, centro_m, exm, eym, ancho, alto, color=color)

    def _pintar_marcador(self, img, zbuf, cam, id_aruco: int, id_geometria: int, pose: Pose) -> bool:
        """Pinta el ArUco `id_aruco` donde va el marcador `id_geometria`; True si se ve casi entero."""
        m = MARCADORES[id_geometria]
        ex, ey = pose.R @ np.asarray(m.eje_x, float), pose.R @ np.asarray(m.eje_y, float)
        n = np.cross(ex, ey)
        centro = pose.aplicar(m.centro)
        if self.geometria == "cad":  # la pegatina está en el fondo de su rebaje
            centro = centro - n * (HUECO_PEGATINA - GROSOR_PEGATINA)
        if np.dot(n, cam.pose.centro - centro) <= 0:
            return False
        tex, total = cam._textura_aruco(id_aruco, m.lado)
        luz = np.float32(self._luz(n))
        pintados, area = self._rasterizar(img, zbuf, cam, centro, ex, ey, total, total, color=luz,
                                          tex=tex.astype(np.float32), sesgo=SESGO_CALCOMANIA, escribir_z=False)
        return area > 0 and pintados >= VISIBLE_MIN * area

    def _pintar_malla(self, img, zbuf, cam, malla: Malla) -> None:
        """Triángulos de cara a la cámara, con z-buffer (profundidad interpolada en perspectiva) y luz de Lambert."""
        R, t, K = cam.pose.R, cam.pose.t, cam.K
        V = malla.triangulos @ (R @ malla.pose.R).T + (R @ malla.pose.t + t)  # en la cámara
        N = malla.normales @ (R @ malla.pose.R).T
        delante = (np.einsum("ij,ij->i", N, -V[:, 0]) > 0) & (V[:, :, 2] > 1.0).all(axis=1)
        luces = 0.55 + 0.45 * np.clip(malla.normales @ malla.pose.R.T @ LUZ_DIR, 0.0, None)
        color = np.asarray(malla.color, np.float32) * 255
        uv = V[:, :, :2] / V[:, :, 2:3] * [K[0, 0], K[1, 1]] + [K[0, 2], K[1, 2]]
        for k in np.flatnonzero(delante):
            p, z = uv[k], V[k, :, 2]
            x0, y0 = np.maximum(np.floor(p.min(axis=0)).astype(int), 0)
            x1 = min(int(np.ceil(p[:, 0].max())) + 1, self.ancho)
            y1 = min(int(np.ceil(p[:, 1].max())) + 1, self.alto)
            if x1 <= x0 or y1 <= y0:
                continue
            area = (p[1, 0] - p[0, 0]) * (p[2, 1] - p[0, 1]) - (p[1, 1] - p[0, 1]) * (p[2, 0] - p[0, 0])
            if abs(area) < 1e-9:
                continue
            us, vs = np.meshgrid(np.arange(x0, x1, dtype=np.float64), np.arange(y0, y1, dtype=np.float64))
            b = []
            for i in range(3):
                a, c = p[(i + 1) % 3], p[(i + 2) % 3]
                b.append(((c[0] - a[0]) * (vs - a[1]) - (c[1] - a[1]) * (us - a[0])) / area)
            dentro = (b[0] >= 0) & (b[1] >= 0) & (b[2] >= 0)
            if not dentro.any():
                continue
            prof = 1.0 / (b[0] / z[0] + b[1] / z[1] + b[2] / z[2])
            zb = zbuf[y0:y1, x0:x1]
            visible = dentro & (prof < zb)
            img[y0:y1, x0:x1][visible] = color * luces[k]
            zb[visible] = prof[visible]

    # --- render ------------------------------------------------------------------------------------------------
    def renderizar(self, base: Pose | None, movil: Pose | None = None, led=None, exposicion: str = "baja",
                   ruido: bool = True, ids_movil: tuple[int, int] = PARES_MOVIL[0], id_base: int = ID_BASE,
                   led_oculto_en=(), obstaculos: list[Caja] | None = None,
                   color_led: str = COLOR_LED) -> tuple[np.ndarray, np.ndarray, VerdadEscena]:
        """Pinta la escena en las dos cámaras: (imagen_a, imagen_b, verdad).

        `base`, `movil`: poses (chapa → mesa) o None si no están. `led`: punto de la mesa o None (apagado).
        `ids_movil`: (cara de la aleta, cara lisa). `led_oculto_en`: cámaras donde algo (la mano) tapa el LED.
        `obstaculos`: cajas extra que tapan (una mano, la antorcha).
        """
        cajas: list[Caja] = []
        if base is not None:
            cajas += [Caja(CAJA_BASE, base, COLOR_BASE), Caja(CAJA_TOPE, base, COLOR_BASE)]
        if movil is not None:
            cajas += [Caja(CAJA_MOVIL, movil, COLOR_MOVIL), Caja(CAJA_ALETA, movil, COLOR_MOVIL)]
        cajas += obstaculos or []
        marcadores: list[tuple[int, int, Pose]] = []
        if base is not None:
            marcadores.append((id_base, ID_BASE, base))
        if movil is not None:
            marcadores += [(ids_movil[0], PARES_MOVIL[0][0], movil), (ids_movil[1], PARES_MOVIL[0][1], movil)]
        verdad = VerdadEscena(base, movil, None if led is None else tuple(float(v) for v in led), exposicion)
        clave = (exposicion, tuple(ids_movil), id_base,
                 *[np.round(np.concatenate([c.pose.R.ravel(), c.pose.t, c.lim, c.color]), 9).tobytes()
                   for c in cajas])
        if clave not in self._estaticas:
            if len(self._estaticas) > 8:
                self._estaticas.clear()
            mallas = []
            if self.geometria == "cad":
                for chapa, pose, color in (("base", base, COLOR_BASE), ("movil", movil, COLOR_MOVIL)):
                    if pose is not None:
                        mallas.append(Malla(*self._mallas[chapa], pose, color))
                dibujar = mallas + list(obstaculos or [])
            else:
                dibujar = cajas
            self._estaticas[clave] = {n: self._pintar_estatica(n, cam, dibujar, marcadores, exposicion)
                                      for n, cam in self.camaras.items()}
        imagenes = []
        for nombre, cam in self.camaras.items():
            estatica, visibles = self._estaticas[clave][nombre]
            imagen = estatica.copy()
            verdad.marcadores_visibles[nombre] = set(visibles)
            verdad.pixel_led[nombre] = None
            if led is not None and nombre not in led_oculto_en:
                p = np.asarray(led, dtype=float)
                z = (cam.pose.R @ p + cam.pose.t)[2]
                uv = cam._proyectar(p[None])[0]
                tapado = any(_segmento_corta_caja(c.pose.inversa().aplicar(cam.pose.centro),
                                                  c.pose.inversa().aplicar(p), c.lim) for c in cajas)
                dentro = 0 <= uv[0] <= self.ancho - 1 and 0 <= uv[1] <= self.alto - 1 and z > 0
                if dentro and not tapado:
                    a_nucleo, a_halo, k_halo = PERFIL_LED[exposicion]
                    cam._anadir_punto(imagen, uv, z, RADIO_LED, a_nucleo, a_halo, k_halo,
                                      COLORES_LED_BGR[color_led])
                    verdad.pixel_led[nombre] = (float(uv[0]), float(uv[1]))
            imagenes.append(self._acabar(cam, imagen, ruido))
        return imagenes[0], imagenes[1], verdad

    def _pintar_estatica(self, nombre: str, cam: CamaraSintetica, cajas, marcadores,
                         exposicion: str) -> tuple[np.ndarray, set[int]]:
        """Escena sin LED en una cámara, ya expuesta (float32, 0-1), y los marcadores que se ven."""
        img = self._fondo(nombre).copy()
        zbuf = np.full((self.alto, self.ancho), np.inf, np.float32)
        for objeto in cajas:
            if isinstance(objeto, Malla):
                self._pintar_malla(img, zbuf, cam, objeto)
            else:
                self._pintar_caja(img, zbuf, cam, objeto)
        visibles = {id_aruco for id_aruco, id_geo, pose in marcadores
                    if self._pintar_marcador(img, zbuf, cam, id_aruco, id_geo, pose)}
        return img * (cam._luz * (GANANCIA[exposicion] / 255.0)), visibles

    def _ruido(self, cam: CamaraSintetica) -> np.ndarray:
        """Ruido gaussiano (alto, ancho, 3) en unidades de 0-255: un trozo al azar de unos campos pregenerados
        (generarlo entero en cada fotograma es la mitad del tiempo de render)."""
        if id(cam) not in self._campos_ruido:
            extra = 160
            self._campos_ruido[id(cam)] = [
                cam.rng.standard_normal((self.alto + extra, self.ancho, 3), dtype=np.float32) * cam.sigma_ruido
                for _ in range(3)]
        campos = self._campos_ruido[id(cam)]
        k = int(cam.rng.integers(len(campos)))
        o = int(cam.rng.integers(campos[k].shape[0] - self.alto + 1))
        return campos[k][o:o + self.alto]

    def _acabar(self, cam: CamaraSintetica, imagen: np.ndarray, ruido: bool) -> np.ndarray:
        if cam.desenfoque > 0:
            imagen = cv2.GaussianBlur(imagen, (0, 0), cam.desenfoque)
        imagen *= 255.0
        if ruido and cam.sigma_ruido > 0:
            imagen += self._ruido(cam)
        imagen += 0.5
        np.clip(imagen, 0, 255, out=imagen)
        return imagen.astype(np.uint8)

    def renderizar_tablero(self, tablero: Pose, ruido: bool = True,
                           exposicion: str = "normal") -> tuple[np.ndarray, np.ndarray]:
        """Fotos del tablero de calibración 9x6 (cuadro de 25 mm) con pose `tablero` (→ mesa) en las dos cámaras.

        Marco del tablero (el de `estereo.objeto_tablero`): origen en la esquina interior junto al cuadro negro de
        arriba a la izquierda de la hoja, X por las columnas, Y por las filas (hacia abajo de la hoja), Z hacia dentro
        de la hoja (tumbado boca arriba, Z del tablero = -Z de la mesa).
        """
        cuadro = 25.0
        centro = tablero.aplicar([4 * cuadro, 2.5 * cuadro, 0.0])  # centro de la hoja (12 x 9 cuadros con margen)
        ex, ey = tablero.R[:, 0], -tablero.R[:, 1]  # fila 0 de la textura arriba de la hoja (-Y del tablero)
        imagenes = []
        for nombre, cam in self.camaras.items():
            img = self._fondo(nombre).copy()
            zbuf = np.full((self.alto, self.ancho), np.inf, np.float32)
            n = np.cross(ex, ey)
            luz = np.float32(self._luz(n if np.dot(n, cam.pose.centro - centro) > 0 else -n))
            self._rasterizar(img, zbuf, cam, centro, ex, ey, 12 * cuadro, 9 * cuadro, color=luz,
                             tex=self._tablero.astype(np.float32))
            imagen = img * (cam._luz * (GANANCIA[exposicion] / 255.0))
            imagenes.append(self._acabar(cam, imagen, ruido))
        return imagenes[0], imagenes[1]
