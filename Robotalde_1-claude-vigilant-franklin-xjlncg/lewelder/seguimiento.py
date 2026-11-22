"""Seguimiento por cámara: punta de la antorcha (LED) y pieza (ArUco) → coordenadas de la pieza.

Por qué así:
- **LED por brillo y color con exposición baja.** Con la exposición manual baja el fondo queda oscuro y el LED
  satura: un umbral basta y no depende de la luz de la sala. El núcleo saturado sale casi blanco; el halo, del color
  del LED. Se exige ese color para descartar brillos blancos y un tamaño mínimo para descartar reflejos pequeños.
- **La pieza vive en un plano conocido.** Un solo ArUco de 25 mm da una pose 6D ruidosa (sobre todo la inclinación).
  Pero la pieza está apoyada en la base de anclajes: los ArUco de los anclajes, repartidos por la base, dan el plano de
  la mesa con precisión, y de la pieza solo hace falta la posición y el giro en ese plano (3 grados de libertad).
  Si no se ve ningún anclaje se cae a la pose 6D del marcador (`metodo = "pnp"`).
- **Punta = rayo ∩ plano.** La punta va a `ALTURA_PUNTA` sobre la superficie de la pieza: el píxel del LED da un rayo
  que se corta con el plano Z = altura de la pieza.
- **La pieza casi no se mueve.** Su pose se cachea, se refresca cada N fotogramas (ArUco es lo caro) y se suaviza.

Convención de poses: `R, t` de "A respecto a B" llevan puntos de A a B: `p_B = R @ p_A + t`.
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

from lewelder.contrato import (
    ALTURA_BASE_ANCLAJES,
    ALTURA_PUNTA,
    ALTURA_SUPERFICIE_PIEZA,
    ANCLAJES,
    ARUCO_EN_ANCLAJE,
    ARUCO_EN_PIEZA,
    COLOR_LED,
    DICCIONARIO_ARUCO,
    IDS_ANCLAJE,
    LADO_ARUCO_ANCLAJE,
    LADO_ARUCO_PIEZA,
    Anclaje,
    Muestra,
    TipoPieza,
    tipo_por_id,
)

# Z (marco de la mesa) de la superficie de la pieza (Z = 0 del marco de la pieza).
ALTURA_PLANO_PIEZA = ALTURA_BASE_ANCLAJES + ALTURA_SUPERFICIE_PIEZA
# Canal BGR dominante de cada color de LED.
CANAL_COLOR = {"azul": 0, "verde": 1, "rojo": 2}


# --- geometría del contrato --------------------------------------------------------------------------------------
def rot_z(grados: float) -> np.ndarray:
    a = np.radians(grados)
    return np.array([[np.cos(a), -np.sin(a), 0.0], [np.sin(a), np.cos(a), 0.0], [0.0, 0.0, 1.0]])


def pose_anclaje(anclaje: Anclaje | str, z: float = ALTURA_PLANO_PIEZA) -> tuple[np.ndarray, np.ndarray]:
    """Pose (R, t) del marco de la pieza colocada en `anclaje` respecto a la mesa, con su origen a altura `z`.

    Con giro 0 el cordón (X de la pieza) avanza en +Y de la mesa, así que X_pieza = Rz(giro + 90°) · X_mesa.
    Con `z = ALTURA_BASE_ANCLAJES` es el marco del anclaje (sobre la base, donde van sus ArUco).
    """
    a = ANCLAJES[anclaje] if isinstance(anclaje, str) else anclaje
    return rot_z(a.giro + 90.0), np.array([a.x, a.y, z])


def esquinas_cuadrado(centro, lado: float) -> np.ndarray:
    """Esquinas (4, 3) de un ArUco en su plano, en el orden de OpenCV: (-L/2, +L/2), (+, +), (+, -), (-, -)."""
    m = lado / 2
    cx, cy, cz = centro
    return np.array([[cx - m, cy + m, cz], [cx + m, cy + m, cz], [cx + m, cy - m, cz], [cx - m, cy - m, cz]])


def esquinas_aruco_anclaje(nombre: str) -> np.ndarray:
    """Esquinas (4, 3) del ArUco del anclaje `nombre` en el marco de la mesa."""
    R, t = pose_anclaje(nombre, ALTURA_BASE_ANCLAJES)
    return esquinas_cuadrado(ARUCO_EN_ANCLAJE, LADO_ARUCO_ANCLAJE) @ R.T + t


def anclaje_mas_cercano(x: float, y: float, giro: float, dist_max: float = 30.0,
                        giro_max: float = 30.0) -> str | None:
    """Anclaje cuyo origen está a menos de `dist_max` mm y con giro parecido; None si la pieza está fuera."""
    mejor, d_mejor = None, dist_max
    for nombre, a in ANCLAJES.items():
        d = float(np.hypot(x - a.x, y - a.y))
        dg = abs((giro - a.giro + 180.0) % 360.0 - 180.0)
        if d < d_mejor and dg < giro_max:
            mejor, d_mejor = nombre, d
    return mejor


# --- calibración -------------------------------------------------------------------------------------------------
@dataclass
class CalibracionCamara:
    K: np.ndarray  # 3x3
    dist: np.ndarray  # coeficientes de distorsión de OpenCV
    ancho: int
    alto: int
    error_rms: float | None = None  # px, si viene de calibrar

    def __post_init__(self):
        self.K = np.asarray(self.K, dtype=float).reshape(3, 3)
        self.dist = np.asarray(self.dist, dtype=float).ravel()

    @classmethod
    def por_defecto(cls, ancho: int = 1280, alto: int = 720, fov_horizontal: float = 65.0) -> CalibracionCamara:
        """Calibración aproximada de una webcam típica (sin distorsión) para cuando aún no se ha calibrado."""
        f = (ancho / 2) / np.tan(np.radians(fov_horizontal) / 2)
        K = [[f, 0, (ancho - 1) / 2], [0, f, (alto - 1) / 2], [0, 0, 1]]
        return cls(K, np.zeros(5), ancho, alto)

    def guardar(self, ruta: str | Path) -> None:
        datos = {"K": self.K.tolist(), "dist": self.dist.tolist(), "ancho": self.ancho, "alto": self.alto,
                 "error_rms": self.error_rms}
        Path(ruta).write_text(json.dumps(datos, indent=2), encoding="utf-8")

    @classmethod
    def cargar(cls, ruta: str | Path) -> CalibracionCamara:
        d = json.loads(Path(ruta).read_text(encoding="utf-8"))
        return cls(d["K"], d["dist"], d["ancho"], d["alto"], d.get("error_rms"))

    @classmethod
    def calibrar_tablero(cls, imagenes, tablero: tuple[int, int] = (9, 6),
                         cuadro_mm: float = 25.0) -> CalibracionCamara:
        """Calibra con fotos de un tablero de ajedrez de `tablero` esquinas interiores (columnas, filas).

        Hacen falta unas 10-20 fotos con el tablero inclinado en distintas direcciones y cubriendo la imagen.
        El error de reproyección queda en `error_rms` (px); por debajo de 0,5 es una buena calibración.
        """
        objeto = np.zeros((tablero[0] * tablero[1], 3), np.float32)
        objeto[:, :2] = np.mgrid[0:tablero[0], 0:tablero[1]].T.reshape(-1, 2) * cuadro_mm
        puntos_obj, puntos_img, tamano = [], [], None
        criterio = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 1e-3)
        for img in imagenes:
            gris = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
            tamano = gris.shape[::-1]
            ok, esquinas = cv2.findChessboardCorners(gris, tablero)
            if not ok:
                continue
            esquinas = cv2.cornerSubPix(gris, esquinas, (5, 5), (-1, -1), criterio)
            puntos_obj.append(objeto)
            puntos_img.append(esquinas)
        if len(puntos_img) < 3:
            raise ValueError(f"tablero encontrado en {len(puntos_img)} imágenes; hacen falta al menos 3")
        error, K, dist, _, _ = cv2.calibrateCamera(puntos_obj, puntos_img, tamano, None, None)
        return cls(K, dist, tamano[0], tamano[1], float(error))

    def rayos(self, pixeles) -> np.ndarray:
        """Direcciones (N, 3) en el marco de la cámara (z = 1) de los píxeles (N, 2), quitando la distorsión."""
        p = np.asarray(pixeles, dtype=np.float64).reshape(-1, 1, 2)
        n = cv2.undistortPoints(p, self.K, self.dist).reshape(-1, 2)
        return np.column_stack([n, np.ones(len(n))])


# --- LED ---------------------------------------------------------------------------------------------------------
def detectar_led(imagen_bgr: np.ndarray, color: str = COLOR_LED, umbral_brillo: int = 150, umbral_color: int = 40,
                 area_min: int = 15, roi: tuple[int, int, int, int] | None = None) -> tuple[float, float, float] | None:
    """Busca el LED: devuelve (u, v, brillo) con (u, v) en píxeles (subpíxel) o None si no lo ve.

    Un píxel es candidato si su canal del color del LED supera `umbral_brillo` y, o bien domina a los otros dos en
    `umbral_color`, o bien está saturado (núcleo del LED). De cada mancha conectada se exige: área >= `area_min`
    (descarta reflejos pequeños), que una parte sea del color del LED (descarta brillos blancos) y forma compacta.
    Gana la de más energía; su centro es el centroide ponderado por intensidad. `brillo` es la intensidad media
    (0-255) de la mancha. `roi = (x, y, ancho, alto)` limita la búsqueda (para seguir el LED más rápido).
    """
    x0 = y0 = 0
    if roi is not None:
        x0, y0, w, h = roi
        x0, y0 = max(0, x0), max(0, y0)
        imagen_bgr = imagen_bgr[y0:y0 + h, x0:x0 + w]
        if imagen_bgr.size == 0:
            return None
    k = CANAL_COLOR[color]
    canales = cv2.split(imagen_bgr)
    principal = canales[k]
    otros = cv2.max(canales[(k + 1) % 3], canales[(k + 2) % 3])
    dominio = cv2.subtract(principal, otros)  # cuánto domina el color del LED (saturado a 0)
    brillante = principal >= umbral_brillo
    de_color = dominio >= umbral_color
    saturado = otros >= 250
    mascara = (brillante & (de_color | saturado)).astype(np.uint8)
    n, etiquetas, stats, _ = cv2.connectedComponentsWithStats(mascara, connectivity=8)
    mejor, energia_mejor = None, 0.0
    for i in range(1, n):
        x, y, w, h, area = stats[i]
        if area < area_min or not (0.4 <= w / h <= 2.5) or area < 0.45 * w * h:
            continue
        ventana = (slice(y, y + h), slice(x, x + w))
        propia = etiquetas[ventana] == i
        if np.count_nonzero(de_color[ventana] & propia) < max(4, 0.15 * area):
            continue  # brillo blanco sin halo del color del LED
        energia = float(principal[ventana][propia].sum())
        if energia > energia_mejor:
            mejor, energia_mejor = i, energia
    if mejor is None:
        return None
    # Centro: se pondera con el canal más débil (mínimo de BGR), que solo es alto en el núcleo del LED. El halo de
    # color no sirve: se recorta con el fondo y, con exposición normal, se funde con papeles blancos cercanos.
    # Núcleo = región saturada en los tres canales (o, si no satura, por encima de media altura) más cercana al
    # centro del halo de color (un papel blanco junto al LED también satura, pero no está en el centro del halo).
    # El centroide se pondera en ese núcleo más un borde de 2 px, con umbral a media altura entre fondo y pico.
    x, y, w, h, area = stats[mejor]
    m = 3
    xa, ya = max(0, x - m), max(0, y - m)
    xb, yb = min(principal.shape[1], x + w + m), min(principal.shape[0], y + h + m)
    propia = cv2.dilate((etiquetas[ya:yb, xa:xb] == mejor).astype(np.uint8), np.ones((2 * m + 1, 2 * m + 1)))
    ventana = imagen_bgr[ya:yb, xa:xb].min(axis=2).astype(np.float32)
    borde = np.concatenate([ventana[0], ventana[-1], ventana[:, 0], ventana[:, -1]])
    fondo = float(np.median(borde))
    pico = float(ventana[propia > 0].max())
    umbral_nucleo = 250.0 if pico >= 250 else (fondo + pico) / 2
    nucleo = ((ventana >= umbral_nucleo) & (propia > 0)).astype(np.uint8)
    n_n, etiq_n, _, centros_n = cv2.connectedComponentsWithStats(nucleo, connectivity=8)
    if n_n < 2:
        return None
    halo_v, halo_u = np.nonzero(de_color[ya:yb, xa:xb] & (propia > 0))
    if len(halo_u):
        centro_halo = np.array([halo_u.mean(), halo_v.mean()])
        elegido = 1 + int(np.argmin(np.linalg.norm(centros_n[1:] - centro_halo, axis=1)))
    else:
        elegido = 1
    region = cv2.dilate((etiq_n == elegido).astype(np.uint8), np.ones((5, 5), np.uint8))
    region[(etiq_n > 0) & (etiq_n != elegido)] = 0  # sin los otros brillos saturados (papel)
    pesos = np.clip(ventana - (fondo + pico) / 2, 0, None) * region
    total = float(pesos.sum())
    if total <= 0:
        return None
    vs, us = np.mgrid[ya:yb, xa:xb]
    u = float((pesos * us).sum() / total) + x0
    v = float((pesos * vs).sum() / total) + y0
    brillo = energia_mejor / area
    return u, v, brillo


# --- marcadores y poses ------------------------------------------------------------------------------------------
_DETECTORES: dict[float, cv2.aruco.ArucoDetector] = {}
PERIMETRO_MIN = 0.06  # perímetro mínimo de un marcador, en fracción del lado mayor de la imagen


def _detector(perimetro_min: float = PERIMETRO_MIN) -> cv2.aruco.ArucoDetector:
    if perimetro_min not in _DETECTORES:
        diccionario = cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, DICCIONARIO_ARUCO))
        parametros = cv2.aruco.DetectorParameters()
        parametros.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX
        parametros.cornerRefinementWinSize = 4
        parametros.cornerRefinementMinAccuracy = 0.01
        # Dos tamaños de ventana (en vez de tres) y contornos de al menos ~20 px de lado: 3-6 ms en vez de 10-60.
        parametros.adaptiveThreshWinSizeMin = 13
        parametros.adaptiveThreshWinSizeMax = 23
        parametros.adaptiveThreshWinSizeStep = 10
        parametros.minMarkerPerimeterRate = perimetro_min
        _DETECTORES[perimetro_min] = cv2.aruco.ArucoDetector(diccionario, parametros)
    return _DETECTORES[perimetro_min]


def detectar_marcadores(imagen: np.ndarray, calib: CalibracionCamara | None = None,
                        ids_clave=None, perimetro_min: float = PERIMETRO_MIN) -> dict[int, np.ndarray]:
    """ArUco visibles: {id: esquinas (4, 2) en píxeles, en el orden de OpenCV}.

    Se busca en la imagen tal cual (el umbral adaptativo aguanta la exposición baja). Solo si no aparece ningún
    marcador clave (`ids_clave`; por defecto, los de pieza de la v1) y la imagen es muy oscura se repite con más
    ganancia y un suavizado (subir la ganancia sin suavizar multiplica el ruido y los contornos candidatos: 10 veces
    más lento). `calib` no se usa para detectar (las esquinas se devuelven con distorsión); está para que la firma
    sea la misma que en el resto del módulo. `perimetro_min` (fracción del lado mayor de la imagen) descarta los
    contornos pequeños: con 0,06 un marcador de menos de ~19 px de lado a 1280x720 (~29 px a 1920x1080) no se busca.
    """
    gris = cv2.cvtColor(imagen, cv2.COLOR_BGR2GRAY) if imagen.ndim == 3 else imagen
    marcadores = _buscar(gris, perimetro_min)
    es_clave = (lambda i: tipo_por_id(i) is not None) if ids_clave is None else (lambda i: i in ids_clave)
    if not any(es_clave(i) for i in marcadores):
        media = float(cv2.mean(gris)[0])
        if media < 40:
            realzada = cv2.GaussianBlur(cv2.convertScaleAbs(gris, alpha=min(4.0, 60.0 / max(media, 1.0))), (3, 3), 0)
            marcadores = {**marcadores, **_buscar(realzada, perimetro_min)}
    return marcadores


def _buscar(gris: np.ndarray, perimetro_min: float = PERIMETRO_MIN) -> dict[int, np.ndarray]:
    esquinas, ids, _ = _detector(perimetro_min).detectMarkers(gris)
    if ids is None:
        return {}
    return {int(i): e.reshape(4, 2).astype(np.float64) for i, e in zip(ids.ravel(), esquinas)}


@dataclass
class PoseMesa:
    """Pose de la mesa respecto a la cámara (p_cam = R @ p_mesa + t), estimada con los ArUco de los anclajes."""

    R: np.ndarray
    t: np.ndarray
    n_marcadores: int
    error_px: float

    @property
    def centro_camara(self) -> np.ndarray:
        """Posición de la cámara en el marco de la mesa."""
        return -self.R.T @ self.t


@dataclass
class PosePieza:
    """Pose de la pieza respecto a la cámara: p_cam = R @ p_pieza + t (mm)."""

    tipo: TipoPieza
    id_aruco: int
    R: np.ndarray
    t: np.ndarray
    anclaje: str | None = None
    en_mesa: tuple[float, float, float] | None = None  # (x, y, giro) del origen de la pieza en la mesa
    metodo: str = "plano_mesa"  # "plano_mesa" (3 GDL sobre la mesa) o "pnp" (6 GDL con el marcador)
    error_px: float = 0.0
    esquinas: np.ndarray | None = field(default=None, repr=False)  # píxeles del marcador de la pieza

    def a_camara(self, p_pieza) -> np.ndarray:
        return self.R @ np.asarray(p_pieza, dtype=float) + self.t

    def a_pieza(self, p_camara) -> np.ndarray:
        return self.R.T @ (np.asarray(p_camara, dtype=float) - self.t)


def _reproyeccion(obj, img, rvec, tvec, calib) -> float:
    proy, _ = cv2.projectPoints(obj, rvec, tvec, calib.K, calib.dist)
    return float(np.sqrt(np.mean(np.sum((proy.reshape(-1, 2) - img) ** 2, axis=1))))


def estimar_pose_mesa(marcadores: dict[int, np.ndarray], calib: CalibracionCamara) -> PoseMesa | None:
    """Pose de la mesa con todos los ArUco de anclaje visibles (todas sus esquinas a la vez); None si no hay."""
    ids = [i for i in marcadores if i in IDS_ANCLAJE]
    if not ids:
        return None
    obj = np.vstack([esquinas_aruco_anclaje(IDS_ANCLAJE[i]) for i in ids])
    img = np.vstack([marcadores[i] for i in ids])
    if len(ids) == 1:
        # Un solo marcador: IPPE_SQUARE en su marco local y luego al de la mesa.
        R_a, t_a = pose_anclaje(IDS_ANCLAJE[ids[0]], ALTURA_BASE_ANCLAJES)
        local = esquinas_cuadrado((0.0, 0.0, 0.0), LADO_ARUCO_ANCLAJE)
        ok, rvec, tvec = cv2.solvePnP(local, img, calib.K, calib.dist, flags=cv2.SOLVEPNP_IPPE_SQUARE)
        if not ok:
            return None
        R_cm = cv2.Rodrigues(rvec)[0]
        centro = R_a @ np.array(ARUCO_EN_ANCLAJE) + t_a  # centro del marcador en la mesa
        R = R_cm @ R_a.T  # marcador alineado con el anclaje
        t = tvec.ravel() - R @ centro
    else:
        # SQPnP: global y sin el problema de IPPE, que solo admite el plano Z = 0 (los anclajes están en Z = 10).
        ok, rvec, tvec = cv2.solvePnP(obj, img, calib.K, calib.dist, flags=cv2.SOLVEPNP_SQPNP)
        if not ok:
            return None
        rvec, tvec = cv2.solvePnPRefineLM(obj, img, calib.K, calib.dist, rvec, tvec)
        R, t = cv2.Rodrigues(rvec)[0], tvec.ravel()
    error = _reproyeccion(obj, img, cv2.Rodrigues(R)[0], t, calib)
    return PoseMesa(R, t, len(ids), error)


def _id_pieza(marcadores: dict[int, np.ndarray]) -> int | None:
    ids = [i for i in marcadores if tipo_por_id(i) is not None]
    return min(ids) if ids else None


def estimar_pose_pieza(marcadores: dict[int, np.ndarray], calib: CalibracionCamara,
                       mesa: PoseMesa | None = None) -> PosePieza | None:
    """Pose de la pieza a partir de su ArUco; None si no se ve ninguno de pieza.

    Con `mesa`: las esquinas del marcador se proyectan al plano de la superficie de la pieza y se ajusta un giro y
    una traslación en ese plano (3 GDL). Sin `mesa`: pose 6D del marcador con IPPE_SQUARE. El anclaje se deduce de
    la posición en la mesa o, sin mesa, del ArUco de anclaje visible más cercano a donde debería estar.
    """
    id_pieza = _id_pieza(marcadores)
    if id_pieza is None:
        return None
    tipo = tipo_por_id(id_pieza)
    esquinas = marcadores[id_pieza]
    modelo = esquinas_cuadrado(ARUCO_EN_PIEZA, LADO_ARUCO_PIEZA)  # en el marco de la pieza
    if mesa is not None:
        # Rayos de las esquinas → mesa → corte con Z = ALTURA_PLANO_PIEZA.
        rayos = calib.rayos(esquinas) @ mesa.R  # (R^T · d)^T = d^T · R
        c = mesa.centro_camara
        s = (ALTURA_PLANO_PIEZA - c[2]) / rayos[:, 2]
        medidos = c[:2] + s[:, None] * rayos[:, :2]
        # Ajuste rígido 2D (Kabsch) modelo → medidos.
        m0, p0 = modelo[:, :2].mean(axis=0), medidos.mean(axis=0)
        H = (modelo[:, :2] - m0).T @ (medidos - p0)
        theta = np.arctan2(H[0, 1] - H[1, 0], H[0, 0] + H[1, 1])
        R_tp = rot_z(np.degrees(theta))
        origen = p0 - R_tp[:2, :2] @ m0
        t_tp = np.array([origen[0], origen[1], ALTURA_PLANO_PIEZA])
        R = mesa.R @ R_tp
        t = mesa.R @ t_tp + mesa.t
        giro = (np.degrees(theta) - 90.0 + 180.0) % 360.0 - 180.0
        en_mesa = (float(origen[0]), float(origen[1]), float(giro))
        anclaje = anclaje_mas_cercano(*en_mesa)
        metodo = "plano_mesa"
    else:
        local = esquinas_cuadrado((0.0, 0.0, 0.0), LADO_ARUCO_PIEZA)
        ok, rvec, tvec = cv2.solvePnP(local, esquinas, calib.K, calib.dist, flags=cv2.SOLVEPNP_IPPE_SQUARE)
        if not ok:
            return None
        R = cv2.Rodrigues(rvec)[0]
        t = tvec.ravel() - R @ np.array(ARUCO_EN_PIEZA)  # el marcador está alineado con la pieza
        en_mesa, metodo = None, "pnp"
        anclaje = _anclaje_por_marcadores(marcadores, calib, R, t)
    error = _reproyeccion(modelo, esquinas, cv2.Rodrigues(R)[0], t, calib)
    return PosePieza(tipo, id_pieza, R, t, anclaje, en_mesa, metodo, error, esquinas)


def _anclaje_por_marcadores(marcadores, calib, R, t, dist_max: float = 30.0) -> str | None:
    """Sin mesa: el ArUco de anclaje visible cuyo centro (pose propia) está donde la pieza dice que estaría."""
    esperado = R @ (np.array(ARUCO_EN_ANCLAJE) - [0.0, 0.0, ALTURA_SUPERFICIE_PIEZA]) + t
    local = esquinas_cuadrado((0.0, 0.0, 0.0), LADO_ARUCO_ANCLAJE)
    mejor, d_mejor = None, dist_max
    for i, esq in marcadores.items():
        if i not in IDS_ANCLAJE:
            continue
        ok, _, tvec = cv2.solvePnP(local, esq, calib.K, calib.dist, flags=cv2.SOLVEPNP_IPPE_SQUARE)
        d = float(np.linalg.norm(tvec.ravel() - esperado)) if ok else np.inf
        if d < d_mejor:
            mejor, d_mejor = IDS_ANCLAJE[i], d
    return mejor


def punto_en_pieza(u: float, v: float, pose: PosePieza, calib: CalibracionCamara,
                   altura: float = ALTURA_PUNTA) -> tuple[float, float, float] | None:
    """Punto (x, y, z) del marco de la pieza donde el rayo del píxel (u, v) corta el plano Z = `altura`.

    None si el rayo es paralelo al plano o el corte queda detrás de la cámara.
    """
    d = pose.R.T @ calib.rayos([(u, v)])[0]  # dirección en el marco de la pieza
    o = -pose.R.T @ pose.t  # centro de la cámara en el marco de la pieza
    if abs(d[2]) < 1e-9:
        return None
    s = (altura - o[2]) / d[2]
    if s <= 0:
        return None
    p = o + s * d
    return float(p[0]), float(p[1]), float(altura)


def _suavizar_pose(vieja: PosePieza, nueva: PosePieza, alfa: float) -> PosePieza:
    """Media exponencial de dos poses cercanas (rotación promediada y reortogonalizada)."""
    U, _, Vt = np.linalg.svd((1 - alfa) * vieja.R + alfa * nueva.R)
    R = U @ Vt
    t = (1 - alfa) * vieja.t + alfa * nueva.t
    en_mesa = None
    if vieja.en_mesa is not None and nueva.en_mesa is not None:
        dg = (nueva.en_mesa[2] - vieja.en_mesa[2] + 180.0) % 360.0 - 180.0
        en_mesa = (
            (1 - alfa) * vieja.en_mesa[0] + alfa * nueva.en_mesa[0],
            (1 - alfa) * vieja.en_mesa[1] + alfa * nueva.en_mesa[1],
            vieja.en_mesa[2] + alfa * dg,
        )
    return PosePieza(nueva.tipo, nueva.id_aruco, R, t, nueva.anclaje, en_mesa, nueva.metodo, nueva.error_px,
                     nueva.esquinas)


def _diferencia_pose(a: PosePieza, b: PosePieza) -> tuple[float, float]:
    """(distancia entre orígenes en mm, ángulo entre orientaciones en grados)."""
    cos = (np.trace(a.R.T @ b.R) - 1) / 2
    return float(np.linalg.norm(a.t - b.t)), float(np.degrees(np.arccos(np.clip(cos, -1.0, 1.0))))


# --- filtro del trazo --------------------------------------------------------------------------------------------
class FiltroUnEuro:
    """Filtro One Euro (Casiez et al., 2012) para un vector: suaviza mucho en reposo y poco en movimiento.

    La frecuencia de corte crece con la velocidad (`min_corte + beta·|v|`), así que el temblor de la mano se filtra
    cuando la punta va despacio y el retraso no crece cuando va deprisa.
    """

    def __init__(self, min_corte: float = 1.5, beta: float = 0.05, d_corte: float = 1.0):
        self.min_corte, self.beta, self.d_corte = min_corte, beta, d_corte
        self.reiniciar()

    def reiniciar(self):
        self._x = self._dx = self._t = None

    @staticmethod
    def _alfa(corte: float, dt: float) -> float:
        tau = 1.0 / (2 * np.pi * corte)
        return 1.0 / (1.0 + tau / dt)

    def filtrar(self, t: float, x) -> np.ndarray:
        x = np.asarray(x, dtype=float)
        if self._x is None:
            self._x, self._dx, self._t = x, np.zeros_like(x), t
            return x.copy()
        dt = max(t - self._t, 1e-4)
        dx = (x - self._x) / dt
        self._dx = self._dx + self._alfa(self.d_corte, dt) * (dx - self._dx)
        corte = self.min_corte + self.beta * float(np.linalg.norm(self._dx))
        self._x = self._x + self._alfa(corte, dt) * (x - self._x)
        self._t = t
        return self._x.copy()


class FiltroTrazo:
    """Limpia el trazo de la punta: rechaza saltos imposibles y suaviza con un filtro One Euro.

    - Un punto a más de `salto_max` mm del último aceptado se rechaza (reflejo, falso positivo).
    - Si el "salto" se repite `reenganche` veces seguidas en el mismo sitio, es que la punta está de verdad allí
      (se levantó la antorcha, se perdió el LED): el filtro se reinicia en la nueva posición.
    - Tras un hueco de más de `hueco_reinicio` s sin puntos, se empieza de cero.
    """

    def __init__(self, salto_max: float = 30.0, reenganche: int = 3, hueco_reinicio: float = 0.5,
                 min_corte: float = 1.5, beta: float = 0.05, d_corte: float = 1.0):
        self.salto_max, self.reenganche, self.hueco_reinicio = salto_max, reenganche, hueco_reinicio
        self.un_euro = FiltroUnEuro(min_corte, beta, d_corte)
        self.reiniciar()

    def reiniciar(self):
        self.un_euro.reiniciar()
        self._ultimo = self._t_ultimo = None
        self._rechazados: list[np.ndarray] = []

    def filtrar(self, t: float, punto) -> tuple[float, float, float] | None:
        p = np.asarray(punto, dtype=float)
        if self._t_ultimo is not None and t - self._t_ultimo > self.hueco_reinicio:
            self.reiniciar()
        if self._ultimo is not None and np.linalg.norm(p - self._ultimo) > self.salto_max:
            if self._rechazados and np.linalg.norm(p - self._rechazados[-1]) > self.salto_max:
                self._rechazados = []  # rechazos sin relación entre sí: ruido, no un sitio nuevo
            self._rechazados.append(p)
            if len(self._rechazados) < self.reenganche:
                return None
            self.reiniciar()
        self._rechazados = []
        self._ultimo, self._t_ultimo = p, t
        return tuple(float(v) for v in self.un_euro.filtrar(t, p))


# --- seguidor ----------------------------------------------------------------------------------------------------
class Seguidor:
    """Une todo: imagen → `Muestra` en el marco de la pieza.

    La pose de la pieza (y el plano de la mesa) se calcula en el primer fotograma y se refresca cada `cada_n`; entre
    medias solo se busca el LED, primero cerca de donde estaba. `gatillo` y los ángulos los rellena quien fusiona
    con la antorcha. Atributos útiles: `pose`, `mesa`, `anclaje`, `cambio_anclaje` (True solo en el fotograma en que
    la pieza aparece en otro anclaje), `led` (último (u, v, brillo) o None).
    """

    def __init__(self, calib: CalibracionCamara, color: str = COLOR_LED, cada_n: int = 30,
                 altura: float = ALTURA_PUNTA, filtro: FiltroTrazo | None = None, alfa_pose: float = 0.3,
                 radio_busqueda: int = 80):
        self.calib, self.color, self.cada_n, self.altura = calib, color, cada_n, altura
        self.filtro = filtro if filtro is not None else FiltroTrazo()
        self.alfa_pose, self.radio_busqueda = alfa_pose, radio_busqueda
        self.reiniciar()

    def reiniciar(self):
        self.pose: PosePieza | None = None
        self.mesa: PoseMesa | None = None
        self.anclaje: str | None = None
        self._ultimo_anclaje: str | None = None  # último anclaje conocido (para no avisar dos veces al pasar por None)
        self.cambio_anclaje = False
        self.led: tuple[float, float, float] | None = None
        self._n = 0
        self.filtro.reiniciar()

    def refrescar_pose(self, imagen: np.ndarray) -> PosePieza | None:
        """Detecta los ArUco, actualiza la mesa y la pose de la pieza (suavizada). Devuelve la pose vigente."""
        marcadores = detectar_marcadores(imagen, self.calib)
        mesa = estimar_pose_mesa(marcadores, self.calib)
        if mesa is not None and (self.mesa is None or mesa.n_marcadores >= self.mesa.n_marcadores):
            self.mesa = mesa  # la cámara está fija: nos quedamos con la estimación con más marcadores
        nueva = estimar_pose_pieza(marcadores, self.calib, self.mesa)
        if nueva is None:
            return self.pose  # pieza tapada (la mano): seguimos con la última pose
        if self.pose is not None and nueva.id_aruco == self.pose.id_aruco:
            dist, angulo = _diferencia_pose(self.pose, nueva)
            if dist < 5.0 and angulo < 3.0:
                nueva = _suavizar_pose(self.pose, nueva, self.alfa_pose)
        if self.pose is not None and _diferencia_pose(self.pose, nueva)[0] > 5.0:
            self.filtro.reiniciar()  # la pieza se ha movido: el trazo anterior ya no vale
        if nueva.anclaje is not None:
            if self._ultimo_anclaje is not None and nueva.anclaje != self._ultimo_anclaje:
                self.cambio_anclaje = True
            self._ultimo_anclaje = nueva.anclaje
        self.anclaje = nueva.anclaje
        self.pose = nueva
        return self.pose

    def _buscar_led(self, imagen: np.ndarray):
        if self.led is not None:
            r = self.radio_busqueda
            roi = (int(self.led[0]) - r, int(self.led[1]) - r, 2 * r, 2 * r)
            led = detectar_led(imagen, self.color, roi=roi)
            if led is not None:
                return led
        return detectar_led(imagen, self.color)

    def procesar(self, imagen: np.ndarray, t: float) -> Muestra | None:
        """Una imagen → Muestra (gatillo False, ángulos None) o None si no hay pieza o no se ve el LED."""
        self.cambio_anclaje = False
        if self.pose is None or self._n % self.cada_n == 0:
            self.refrescar_pose(imagen)
        self._n += 1
        if self.pose is None:
            return None
        self.led = self._buscar_led(imagen)
        if self.led is None:
            return None
        p = punto_en_pieza(self.led[0], self.led[1], self.pose, self.calib, self.altura)
        if p is None:
            return None
        filtrado = self.filtro.filtrar(t, p)
        if filtrado is None:
            return None
        return Muestra(t=t, x=filtrado[0], y=filtrado[1], z=filtrado[2], gatillo=False)


# --- webcam real -------------------------------------------------------------------------------------------------
def abrir_webcam(indice: int = 0, ancho: int = 1280, alto: int = 720,
                 exposicion: float | None = -7) -> cv2.VideoCapture | None:
    """Abre la webcam con resolución y exposición manual fijas; None si no hay cámara.

    `exposicion` va en las unidades del backend: en Windows (DirectShow) es log2 de segundos (-7 ≈ 1/128 s); en
    Linux (V4L2) son centenas de microsegundos (p. ej. 50 = 5 ms). None deja la exposición automática.
    Ajustar mirando la imagen: fondo oscuro y LED saturado pero pequeño.
    """
    backend = cv2.CAP_DSHOW if sys.platform.startswith("win") else cv2.CAP_ANY
    try:
        cap = cv2.VideoCapture(indice, backend)
    except cv2.error:
        return None
    if not cap.isOpened():
        cap.release()
        return None
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, ancho)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, alto)
    if exposicion is not None:
        # Modo manual: 0.25 en DirectShow/V4L2 antiguo, 1 en V4L2 moderno. Probamos ambos.
        if sys.platform.startswith("win"):
            cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
        elif not cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1):
            cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
        cap.set(cv2.CAP_PROP_EXPOSURE, exposicion)
    cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)
    cap.set(cv2.CAP_PROP_AUTO_WB, 0)
    return cap
