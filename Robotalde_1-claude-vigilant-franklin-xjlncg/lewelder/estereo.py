"""Estéreo v2: dos webcams calibradas → pose 3D de cada chapa, junta reconocida y punta de la antorcha en 3D.

Por qué así:
- **Calibración en dos pasos.** Intrínsecos de cada cámara y la pose relativa B-A con el tablero 9x6 de 25 mm
  (`cv2.calibrateCamera` + `cv2.stereoCalibrate` con los intrínsecos fijos), y después la pose de la **mesa** respecto
  a la cámara A, con el tablero tumbado en la mesa en `TABLERO_EN_MESA` (lo más preciso: 54 esquinas en 200 mm) o
  con el ArUco de la base en `POSICION_BASE` (sin tablero, menos preciso en la inclinación). Las dos cámaras quedan
  ligadas por la relativa, así que la mesa se ajusta con las dos a la vez.
- **Pose de una chapa con las dos cámaras a la vez.** Se parte de la mejor de varias poses iniciales (PnP por marcador
  y cámara, con las dos soluciones de IPPE, y triangulación de las esquinas cuando las dos cámaras ven el marcador) y
  se refina con Levenberg-Marquardt minimizando el error de reproyección en las dos cámaras a la vez. Un ArUco de
  25 mm visto por una sola cámara da una inclinación ruidosa; visto desde dos direcciones, la inclinación sale bien.
- **La base está tumbada en la mesa.** Si la pose 6D dice que está plana sobre la mesa, se reajusta con solo 3 grados
  de libertad (x, y, giro) a la altura de su cara (`GROSOR_CHAPA`): la cara de la base queda exactamente en el plano
  de la mesa calibrada y la altura de la punta sobre ella no hereda el ruido de inclinación del marcador.
- **LED triangulado.** El LED se busca en las dos imágenes (`detectar_led`), se triangula y se rechaza si el error de
  reproyección es grande (un reflejo en una cámara y el LED en la otra no casan).
- **Las chapas casi no se mueven.** Su pose se refresca cada `cada_n` fotogramas, se suaviza y se conserva mientras
  no se ven (la mano tapa el ArUco). Un cambio grande solo se acepta si se repite (`FiltroPose`): eso es "movimiento".

Convención de poses: `Pose` de `juntas.py` (`p_B = R @ p_A + t` para "A respecto a B"). La pose de una cámara es la de
la mesa respecto a ella (`p_cam = R @ p_mesa + t`), como en `PoseCamara`.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

from lewelder.contrato import COLOR_LED, GROSOR_CHAPA, ID_BASE, POSICION_BASE, Muestra, TipoJunta
from lewelder.juntas import (
    CAJA_BASE,
    CAJA_MOVIL,
    MARCADORES,
    PARES_MOVIL,
    TOLERANCIAS_UNA_CAMARA,
    Y_CORDON,
    Z_CANTO_MOVIL,
    EstadoJunta,
    Junta,
    Pose,
    pose_base,
    punta_en_cordon,
    reconocer_junta,
    rot_x,
    rot_z,
)
from lewelder.seguimiento import CalibracionCamara, FiltroTrazo, detectar_led, detectar_marcadores

log = logging.getLogger("lewelder.estereo")

TABLERO = (9, 6)  # esquinas interiores (columnas, filas), como el que genera `herramientas/generar_hardware.py`
CUADRO_MM = 25.0
# Tablero tumbado en la mesa para referir las cámaras a ella: hoja boca arriba con su centro (el de las esquinas
# interiores) en el de la base (`POSICION_BASE`, quitando la base), las columnas (X del tablero) hacia +Y de la mesa y
# las filas (Y) hacia +X (lejos del robot). Es decir: el cuadro negro de la esquina de la hoja queda en el lado del
# robot y a la derecha.
TABLERO_EN_MESA = Pose(rot_z(90.0) @ rot_x(180.0),
                       [POSICION_BASE.x - 2.5 * CUADRO_MM, POSICION_BASE.y - 4.0 * CUADRO_MM, 0.0])
ERROR_MAX_LED_PX = 3.0  # reproyección máxima (px) para aceptar el LED triangulado
ERROR_MAX_POSE_PX = 4.0  # reproyección máxima (px) para aceptar la pose de una chapa
MARGEN_LED_MARCADOR_PX = 25  # un marcador con el LED a menos de esto de su recuadro no se usa para la pose
IDS_V2 = frozenset(MARCADORES)
# Perímetro mínimo de un ArUco (fracción del lado mayor de la imagen): la mitad que en la v1, para que los marcadores
# de 25 mm a 60-80 cm (13-20 px de lado con una webcam de 78° a 720p) no se descarten antes de intentar leerlos.
PERIMETRO_MIN_V2 = 0.03


# --- cámaras -----------------------------------------------------------------------------------------------------
@dataclass
class Camara:
    """Cámara calibrada con su pose: la del marco de referencia (la mesa) respecto a ella."""

    calib: CalibracionCamara
    pose: Pose  # p_cam = pose.R @ p_ref + pose.t

    def __post_init__(self):
        self._rvec = cv2.Rodrigues(self.pose.R)[0]
        d = self.calib.dist
        # Modelo de 5 coeficientes (k1, k2, p1, p2, k3) en numpy: 20 veces más rápido que projectPoints para los pocos
        # puntos del ajuste de poses. Con más coeficientes (modelo racional) se usa OpenCV.
        self._numpy = len(d) <= 5 or not np.any(d[5:])
        self._d = np.zeros(5)
        self._d[:min(5, len(d))] = d[:5]

    @property
    def centro(self) -> np.ndarray:
        return -self.pose.R.T @ self.pose.t

    def proyectar(self, P) -> np.ndarray:
        """Píxeles (N, 2) de los puntos (N, 3) del marco de referencia, con la distorsión de la cámara."""
        P = np.asarray(P, dtype=np.float64).reshape(-1, 3)
        if not self._numpy:
            uv, _ = cv2.projectPoints(P, self._rvec, self.pose.t, self.calib.K, self.calib.dist)
            return uv.reshape(-1, 2)
        pc = P @ self.pose.R.T + self.pose.t
        x, y = pc[:, 0] / pc[:, 2], pc[:, 1] / pc[:, 2]
        k1, k2, p1, p2, k3 = self._d
        r2 = x * x + y * y
        radial = 1 + r2 * (k1 + r2 * (k2 + r2 * k3))
        xd = x * radial + 2 * p1 * x * y + p2 * (r2 + 2 * x * x)
        yd = y * radial + p1 * (r2 + 2 * y * y) + 2 * p2 * x * y
        K = self.calib.K
        return np.column_stack([K[0, 0] * xd + K[0, 1] * yd + K[0, 2], K[1, 1] * yd + K[1, 2]])


@dataclass
class CalibracionEstereo:
    """Dos cámaras: intrínsecos, pose relativa (`p_b = R @ p_a + T`) y, si ya se ha calibrado, la mesa respecto a A."""

    a: CalibracionCamara
    b: CalibracionCamara
    R: np.ndarray
    T: np.ndarray
    error_rms: float | None = None  # px, de `stereoCalibrate`
    mesa: Pose | None = None  # mesa → cámara A
    error_mesa_px: float | None = None

    def __post_init__(self):
        self.R = np.asarray(self.R, dtype=float).reshape(3, 3)
        self.T = np.asarray(self.T, dtype=float).reshape(3)

    @property
    def relativa(self) -> Pose:
        return Pose(self.R, self.T)

    def camaras(self) -> tuple[Camara, Camara]:
        """Las dos cámaras con su pose respecto a la mesa (hace falta haber calibrado la mesa)."""
        if self.mesa is None:
            raise ValueError("falta calibrar la mesa (calibrar_mesa_tablero o calibrar_mesa_aruco)")
        return Camara(self.a, self.mesa), Camara(self.b, self.relativa @ self.mesa)

    def _camaras_en_a(self) -> list[Camara]:
        return [Camara(self.a, Pose.identidad()), Camara(self.b, self.relativa)]

    # --- construcción --------------------------------------------------------------------------------------
    @classmethod
    def desde_camaras(cls, cam_a: Camara, cam_b: Camara) -> CalibracionEstereo:
        relativa = cam_b.pose @ cam_a.pose.inversa()
        return cls(cam_a.calib, cam_b.calib, relativa.R, relativa.t, 0.0, cam_a.pose, 0.0)

    @classmethod
    def desde_escena(cls, escena) -> CalibracionEstereo:
        """Calibración exacta de una `EscenaSintetica` (sus cámaras "a" y "b")."""
        cams = [Camara(escena.camaras[n].calibracion(), Pose(escena.camaras[n].pose.R, escena.camaras[n].pose.t))
                for n in ("a", "b")]
        return cls.desde_camaras(*cams)

    @classmethod
    def calibrar(cls, imagenes_a, imagenes_b, tablero: tuple[int, int] = TABLERO, cuadro_mm: float = CUADRO_MM,
                 flags: int = cv2.CALIB_FIX_K3) -> CalibracionEstereo:
        """Calibra las dos cámaras con pares de fotos simultáneas del tablero (10-20 pares, tablero inclinado).

        Los intrínsecos de cada cámara salen de todas sus fotos con el tablero; la relativa, de los pares en que lo
        ven las dos. `error_rms` (px) de `stereoCalibrate`: por debajo de 0,5 es buena.
        """
        objeto = objeto_tablero(tablero, cuadro_mm).astype(np.float32)
        det_a = [detectar_tablero(i, tablero) for i in imagenes_a]
        det_b = [detectar_tablero(i, tablero) for i in imagenes_b]

        def intrinsecos(detecciones, imagenes) -> CalibracionCamara:
            vistas = [d.astype(np.float32).reshape(-1, 1, 2) for d in detecciones if d is not None]
            if len(vistas) < 3:
                raise ValueError(f"tablero encontrado en {len(vistas)} imágenes; hacen falta al menos 3")
            alto, ancho = imagenes[0].shape[:2]
            error, K, dist, _, _ = cv2.calibrateCamera([objeto] * len(vistas), vistas, (ancho, alto), None, None,
                                                       flags=flags)
            return CalibracionCamara(K, dist, ancho, alto, float(error))

        calib_a, calib_b = intrinsecos(det_a, imagenes_a), intrinsecos(det_b, imagenes_b)
        pares = [(da, db) for da, db in zip(det_a, det_b) if da is not None and db is not None]
        if len(pares) < 3:
            raise ValueError(f"tablero visto por las dos cámaras en {len(pares)} pares; hacen falta al menos 3")
        criterio = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 1e-6)
        error, *_, R, T, _, _ = cv2.stereoCalibrate(
            [objeto] * len(pares), [a.astype(np.float32).reshape(-1, 1, 2) for a, _ in pares],
            [b.astype(np.float32).reshape(-1, 1, 2) for _, b in pares], calib_a.K, calib_a.dist, calib_b.K,
            calib_b.dist, (calib_a.ancho, calib_a.alto), flags=cv2.CALIB_FIX_INTRINSIC, criteria=criterio)
        log.info("estéreo calibrado con %d pares: error %.3f px", len(pares), error)
        return cls(calib_a, calib_b, R, T.ravel(), float(error))

    def calibrar_mesa_tablero(self, imagen_a, imagen_b, tablero: Pose = TABLERO_EN_MESA,
                              patron: tuple[int, int] = TABLERO, cuadro_mm: float = CUADRO_MM) -> float:
        """Pose de la mesa con el tablero tumbado en `tablero` (→ mesa). Devuelve el error de reproyección (px)."""
        local = objeto_tablero(patron, cuadro_mm)
        camaras = self._camaras_en_a()
        obs = [Observacion(cam, Pose.identidad(), local, esq)
               for cam, img in zip(camaras, (imagen_a, imagen_b))
               if (esq := detectar_tablero(img, patron)) is not None]
        if not obs:
            raise ValueError("no se ve el tablero en ninguna cámara")
        en_a, error = ajustar_pose(obs)
        self.mesa, self.error_mesa_px = en_a @ tablero.inversa(), error
        return error

    def calibrar_mesa_aruco(self, imagen_a, imagen_b, base: Pose | None = None) -> float:
        """Pose de la mesa con el ArUco de la base colocada en `base` (por defecto en `POSICION_BASE`)."""
        base = pose_base() if base is None else base
        obs = _observaciones([ID_BASE], [detectar_marcadores_v2(imagen_a), detectar_marcadores_v2(imagen_b)],
                             self._camaras_en_a())
        if not obs:
            raise ValueError("no se ve el ArUco de la base en ninguna cámara")
        en_a, error = ajustar_pose(obs)
        self.mesa, self.error_mesa_px = en_a @ base.inversa(), error
        return error

    # --- JSON ----------------------------------------------------------------------------------------------
    def guardar(self, ruta: str | Path) -> None:
        def cam(c: CalibracionCamara) -> dict:
            return {"K": c.K.tolist(), "dist": c.dist.tolist(), "ancho": c.ancho, "alto": c.alto,
                    "error_rms": c.error_rms}

        datos = {"a": cam(self.a), "b": cam(self.b), "R": self.R.tolist(), "T": self.T.tolist(),
                 "error_rms": self.error_rms, "mesa": self.mesa.a_dict() if self.mesa else None,
                 "error_mesa_px": self.error_mesa_px}
        Path(ruta).write_text(json.dumps(datos, indent=2), encoding="utf-8")

    @classmethod
    def cargar(cls, ruta: str | Path) -> CalibracionEstereo:
        d = json.loads(Path(ruta).read_text(encoding="utf-8"))

        def cam(c: dict) -> CalibracionCamara:
            return CalibracionCamara(c["K"], c["dist"], c["ancho"], c["alto"], c.get("error_rms"))

        mesa = Pose(d["mesa"]["R"], d["mesa"]["t"]) if d.get("mesa") else None
        return cls(cam(d["a"]), cam(d["b"]), d["R"], d["T"], d.get("error_rms"), mesa, d.get("error_mesa_px"))


# --- tablero -----------------------------------------------------------------------------------------------------
def objeto_tablero(tablero: tuple[int, int] = TABLERO, cuadro_mm: float = CUADRO_MM) -> np.ndarray:
    """Esquinas interiores (N, 3) en el marco del tablero: origen en la esquina junto al cuadro negro de la esquina
    de la hoja, X por las columnas, Y por las filas, Z hacia dentro de la hoja. Orden de OpenCV (fila a fila)."""
    objeto = np.zeros((tablero[0] * tablero[1], 3))
    objeto[:, :2] = np.mgrid[0:tablero[0], 0:tablero[1]].T.reshape(-1, 2) * cuadro_mm
    return objeto


def detectar_tablero(imagen: np.ndarray, tablero: tuple[int, int] = TABLERO) -> np.ndarray | None:
    """Esquinas interiores (N, 2) del tablero en el orden de `objeto_tablero`, o None si no está.

    OpenCV puede empezar por cualquiera de los dos extremos (y, si el tablero se ve en espejo, recorrer las filas al
    revés). Se fija el orden: filas de modo que el tablero se vea por delante y el primer extremo junto al cuadro negro
    de la esquina (el tablero de 10x7 cuadros tiene el cuadro de la esquina opuesta blanco).
    """
    gris = cv2.cvtColor(imagen, cv2.COLOR_BGR2GRAY) if imagen.ndim == 3 else imagen
    ok, esquinas = cv2.findChessboardCorners(gris, tablero, flags=cv2.CALIB_CB_ADAPTIVE_THRESH
                                             + cv2.CALIB_CB_NORMALIZE_IMAGE)
    if not ok:
        return None
    criterio = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 50, 1e-3)
    esquinas = cv2.cornerSubPix(gris, esquinas, (5, 5), (-1, -1), criterio).reshape(tablero[1], tablero[0], 2)
    esquinas = esquinas.astype(np.float64)
    # Delante: en la hoja X va a la derecha e Y hacia abajo; en la imagen (y hacia abajo) el giro es positivo.
    ex, ey = esquinas[0, 1] - esquinas[0, 0], esquinas[1, 0] - esquinas[0, 0]
    if ex[0] * ey[1] - ex[1] * ey[0] < 0:
        esquinas = esquinas[::-1]

    def gris_en(p) -> float:
        return float(cv2.getRectSubPix(gris, (3, 3), (float(p[0]), float(p[1]))).mean())

    primero = esquinas[0, 0] + 0.5 * (esquinas[0, 0] - esquinas[1, 1])
    ultimo = esquinas[-1, -1] + 0.5 * (esquinas[-1, -1] - esquinas[-2, -2])
    if gris_en(primero) > gris_en(ultimo):
        esquinas = esquinas[::-1, ::-1]
    return esquinas.reshape(-1, 2)


# --- triangulación -----------------------------------------------------------------------------------------------
def triangular(cam_a: Camara, cam_b: Camara, uv_a, uv_b) -> tuple[np.ndarray, np.ndarray]:
    """Puntos (N, 3) de la mesa a partir de sus píxeles en las dos cámaras y su error de reproyección (N,) en px
    (el mayor de las dos cámaras)."""
    uv_a = np.asarray(uv_a, dtype=np.float64).reshape(-1, 2)
    uv_b = np.asarray(uv_b, dtype=np.float64).reshape(-1, 2)
    na = cv2.undistortPoints(uv_a.reshape(-1, 1, 2), cam_a.calib.K, cam_a.calib.dist).reshape(-1, 2)
    nb = cv2.undistortPoints(uv_b.reshape(-1, 1, 2), cam_b.calib.K, cam_b.calib.dist).reshape(-1, 2)
    Pa = np.hstack([cam_a.pose.R, cam_a.pose.t[:, None]])
    Pb = np.hstack([cam_b.pose.R, cam_b.pose.t[:, None]])
    h = cv2.triangulatePoints(Pa, Pb, na.T, nb.T)
    p = (h[:3] / h[3]).T
    error = np.maximum(np.linalg.norm(cam_a.proyectar(p) - uv_a, axis=1),
                       np.linalg.norm(cam_b.proyectar(p) - uv_b, axis=1))
    return p, error


def triangular_led(estereo, led_a, led_b,
                   error_max_px: float = ERROR_MAX_LED_PX) -> tuple[np.ndarray, float] | None:
    """Punto 3D del LED (mesa) con sus detecciones (u, v, brillo) en las dos cámaras y su error (px).

    `estereo`: una `CalibracionEstereo` o el par de `Camara`. None si falta una detección, si el punto queda detrás
    de alguna cámara o si el error de reproyección pasa de `error_max_px` (no es el mismo punto en las dos).
    """
    if led_a is None or led_b is None:
        return None
    cam_a, cam_b = estereo.camaras() if hasattr(estereo, "camaras") else estereo
    p, error = triangular(cam_a, cam_b, [led_a[:2]], [led_b[:2]])
    p, error = p[0], float(error[0])
    if not np.isfinite(p).all() or error > error_max_px:
        return None
    if (cam_a.pose.R @ p + cam_a.pose.t)[2] <= 0 or (cam_b.pose.R @ p + cam_b.pose.t)[2] <= 0:
        return None
    return p, error


# --- ajuste de poses ---------------------------------------------------------------------------------------------
@dataclass
class Observacion:
    """Puntos de un plano de un objeto vistos por una cámara.

    `local`: puntos (N, 3) en el marco del plano (Z = 0); `plano`: pose del plano en el objeto; `pixeles`: (N, 2).
    """

    camara: Camara
    plano: Pose
    local: np.ndarray
    pixeles: np.ndarray

    @property
    def objeto(self) -> np.ndarray:
        return self.plano.aplicar(self.local)


def _agrupar(obs: list[Observacion]) -> list[tuple[Camara, np.ndarray, np.ndarray]]:
    """Observaciones juntadas por cámara: [(cámara, puntos del objeto (N, 3), píxeles (N, 2))]."""
    grupos: dict[int, tuple[Camara, list, list]] = {}
    for o in obs:
        grupos.setdefault(id(o.camara), (o.camara, [], []))
        grupos[id(o.camara)][1].append(o.objeto)
        grupos[id(o.camara)][2].append(o.pixeles)
    return [(cam, np.vstack(objeto), np.vstack(pixeles)) for cam, objeto, pixeles in grupos.values()]


def _residuos(grupos, pose: Pose) -> np.ndarray:
    return np.concatenate([(cam.proyectar(pose.aplicar(objeto)) - pixeles).ravel()
                           for cam, objeto, pixeles in grupos])


def _rodrigues(w: np.ndarray) -> np.ndarray:
    angulo = float(np.linalg.norm(w))
    if angulo < 1e-12:
        return np.eye(3)
    k = w / angulo
    Kx = np.array([[0.0, -k[2], k[1]], [k[2], 0.0, -k[0]], [-k[1], k[0], 0.0]])
    return np.eye(3) + np.sin(angulo) * Kx + (1 - np.cos(angulo)) * (Kx @ Kx)


def _perturbar(pose: Pose, d: np.ndarray) -> Pose:
    return Pose(_rodrigues(d[:3]) @ pose.R, pose.t + d[3:])


def _kabsch(modelo: np.ndarray, medidos: np.ndarray) -> Pose:
    """Pose rígida que mejor lleva `modelo` (N, 3) a `medidos` (N, 3)."""
    m0, p0 = modelo.mean(axis=0), medidos.mean(axis=0)
    U, _, Vt = np.linalg.svd((modelo - m0).T @ (medidos - p0))
    D = np.diag([1.0, 1.0, np.sign(np.linalg.det(Vt.T @ U.T))])
    R = Vt.T @ D @ U.T
    return Pose(R, p0 - R @ m0)


def _poses_iniciales(obs: list[Observacion]) -> list[Pose]:
    """Candidatas: las dos soluciones de IPPE de cada observación y, si dos cámaras ven el mismo plano, la
    triangulación de sus puntos."""
    candidatas = []
    for o in obs:
        ok, rvecs, tvecs, _ = cv2.solvePnPGeneric(o.local, o.pixeles, o.camara.calib.K, o.camara.calib.dist,
                                                  flags=cv2.SOLVEPNP_IPPE)
        for rvec, tvec in zip(rvecs if ok else [], tvecs if ok else []):
            en_cam = Pose(cv2.Rodrigues(rvec)[0], tvec.ravel())
            candidatas.append(o.camara.pose.inversa() @ en_cam @ o.plano.inversa())
    for i, oi in enumerate(obs):
        for oj in obs[i + 1:]:
            if oi.camara is not oj.camara and np.allclose(oi.local, oj.local) and \
                    np.allclose(oi.plano.t, oj.plano.t) and np.allclose(oi.plano.R, oj.plano.R):
                p, _ = triangular(oi.camara, oj.camara, oi.pixeles, oj.pixeles)
                if np.isfinite(p).all():
                    candidatas.append(_kabsch(oi.objeto, p))
    return candidatas


def ajustar_pose(obs: list[Observacion], inicial: Pose | None = None, libres=(0, 1, 2, 3, 4, 5),
                 iteraciones: int = 30, valida=None, preferencia=None,
                 margen_px: float = 0.5) -> tuple[Pose, float]:
    """Pose del objeto (→ marco de las cámaras) que minimiza la reproyección en todas las observaciones a la vez.

    Levenberg-Marquardt con jacobiano numérico. `libres`: parámetros que se ajustan, de (rx, ry, rz, tx, ty, tz)
    (giro alrededor del origen del objeto con los ejes del marco de las cámaras y traslación); p. ej. (2, 3, 4) para
    una pieza que solo se mueve sobre la mesa. Sin `inicial`, se refinan las candidatas de `_poses_iniciales` que
    cumplen `valida(pose)` (si se da) y gana la de menor error; con `preferencia(pose) -> float`, entre las que no
    pasan del mejor error en más de `margen_px`, gana la de menor preferencia (para deshacer la ambigüedad de un
    marcador pequeño visto por una sola cámara). Devuelve (pose, error RMS en px).
    """
    grupos = _agrupar(obs)
    if inicial is None:
        candidatas = _poses_iniciales(obs)
        if valida is not None:
            candidatas = [p for p in candidatas if valida(p)] or candidatas
        if not candidatas:
            raise ValueError("sin pose inicial")
        costes = [float(np.mean(_residuos(grupos, p) ** 2)) for p in candidatas]
        # Se refinan las mejores (IPPE da a veces la buena en segundo lugar).
        ajustes = [_levenberg_marquardt(grupos, candidatas[i], list(libres), iteraciones)
                   for i in np.argsort(costes)[:3]]
        if valida is not None:
            ajustes = [a for a in ajustes if valida(a[0])] or ajustes
        mejor = min(a[1] for a in ajustes)
        if preferencia is not None:
            parecidas = [a for a in ajustes if a[1] <= mejor + margen_px]
            return min(parecidas, key=lambda a: (preferencia(a[0]), a[1]))
        return min(ajustes, key=lambda a: a[1])
    return _levenberg_marquardt(grupos, inicial, list(libres), iteraciones)


def _levenberg_marquardt(grupos, pose: Pose, libres: list[int], iteraciones: int) -> tuple[Pose, float]:
    r = _residuos(grupos, pose)
    coste = float(r @ r)
    lam = 1e-3
    pasos = np.array([1e-6, 1e-6, 1e-6, 1e-4, 1e-4, 1e-4])
    for _ in range(iteraciones):
        J = np.empty((len(r), len(libres)))
        for k, i in enumerate(libres):
            d = np.zeros(6)
            d[i] = pasos[i]
            J[:, k] = (_residuos(grupos, _perturbar(pose, d)) - r) / pasos[i]
        A, g = J.T @ J, J.T @ r
        d = np.zeros(6)
        for _ in range(8):
            d[libres] = np.linalg.solve(A + lam * np.diag(np.diag(A) + 1e-9), -g)
            nueva = _perturbar(pose, d)
            r_nueva = _residuos(grupos, nueva)
            coste_nuevo = float(r_nueva @ r_nueva)
            if coste_nuevo < coste:
                break
            lam *= 10
        else:
            break  # no mejora: mínimo
        mejora = coste - coste_nuevo
        pose, r, coste, lam = nueva, r_nueva, coste_nuevo, max(lam / 10, 1e-9)
        if mejora < 1e-6 * coste or (np.abs(d[:3]).max() < 1e-7 and np.abs(d[3:]).max() < 1e-5):
            break
    return pose, float(np.sqrt(coste / (len(r) / 2)))


# --- pose de cada chapa ------------------------------------------------------------------------------------------
def refinar_esquinas(gris: np.ndarray, esquinas: np.ndarray, muestras: int = 12, paso: float = 0.25) -> np.ndarray:
    """Esquinas (4, 2) de un ArUco refinadas con los bordes: recta ajustada a cada lado exterior e intersecciones.

    `cornerSubPix` (el refinado de ArUco) está pensado para esquinas en X; en las esquinas en L de un marcador con
    desenfoque se va hacia dentro, y más cuanto más de canto se ve (0,3-3 px). El borde negro-blanco de cada lado,
    en cambio, tiene un perfil simétrico: su posición (centroide del gradiente a lo largo de la normal) no tiene
    sesgo, y la recta ajustada a `muestras` puntos promedia el ruido. Si algo sale raro se dejan las esquinas como
    estaban.
    """
    e = np.asarray(esquinas, dtype=np.float64).reshape(4, 2)
    imagen = gris.astype(np.float32)
    rectas = []
    for i in range(4):
        p, q = e[i], e[(i + 1) % 4]
        largo = float(np.linalg.norm(q - p))
        if largo < 12.0:
            return e
        d = (q - p) / largo
        normal = np.array([-d[1], d[0]])
        ancho = min(3.0, 0.4 * largo / 6)  # sin llegar al borde interior del marco negro (una celda = lado / 6)
        s = np.linspace(0.2, 0.8, muestras)[:, None] * largo
        o = np.arange(-ancho, ancho + 1e-9, paso)
        puntos = p + s[:, None, :] * d + o[None, :, None] * normal
        perfil = cv2.remap(imagen, puntos[..., 0].astype(np.float32), puntos[..., 1].astype(np.float32),
                           cv2.INTER_LINEAR)
        gradiente = np.abs(np.diff(perfil, axis=1))
        gradiente = np.clip(gradiente - gradiente.min(axis=1, keepdims=True), 0, None)
        total = gradiente.sum(axis=1)
        if (total <= 0).any():
            return e
        desplazamiento = (gradiente * (o[:-1] + o[1:]) / 2).sum(axis=1) / total
        borde = p + s * d + desplazamiento[:, None] * normal
        centro = borde.mean(axis=0)
        direccion = np.linalg.svd(borde - centro)[2][0]
        rectas.append((centro, direccion))
    nuevas = np.empty((4, 2))
    for i in range(4):
        (c1, d1), (c2, d2) = rectas[i - 1], rectas[i]
        A = np.column_stack([d1, -d2])
        if abs(np.linalg.det(A)) < 1e-6:
            return e
        a = np.linalg.solve(A, c2 - c1)[0]
        nuevas[i] = c1 + a * d1
    if np.abs(nuevas - e).max() > 4.0:
        return e
    return nuevas


def detectar_marcadores_v2(imagen: np.ndarray, refinar: bool = True) -> dict[int, np.ndarray]:
    """ArUco de la v2 (base y chapa móvil) visibles en la imagen: {id: esquinas (4, 2)}, refinadas con los bordes.

    Si falta la base o la móvil, se repite la búsqueda con más ganancia (solo si la imagen es oscura: con exposición
    baja, el ArUco de la cara vertical de la móvil, menos iluminada, queda con muy poco contraste).
    """
    marcadores = detectar_marcadores(imagen, ids_clave=IDS_V2, perimetro_min=PERIMETRO_MIN_V2)
    if ID_BASE not in marcadores or not any(i in MARCADORES and MARCADORES[i].chapa == "movil" for i in marcadores):
        realzados = detectar_marcadores(imagen, ids_clave=frozenset(), perimetro_min=PERIMETRO_MIN_V2)
        marcadores = {**realzados, **marcadores}
    marcadores = {i: e for i, e in marcadores.items() if i in IDS_V2}
    if refinar and marcadores:
        gris = cv2.cvtColor(imagen, cv2.COLOR_BGR2GRAY) if imagen.ndim == 3 else imagen
        marcadores = {i: refinar_esquinas(gris, e) for i, e in marcadores.items()}
    return marcadores


def _plano_marcador(id_aruco: int) -> Pose:
    m = MARCADORES[id_aruco]
    return Pose(np.column_stack([m.eje_x, m.eje_y, m.normal]), m.centro)


MARGEN_MESA = 8.0  # mm que se admite que una chapa "atraviese" la mesa (ruido de la pose)


def _vertices(lim) -> np.ndarray:
    x0, x1, y0, y1, z0, z1 = lim
    return np.array([[x, y, z] for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)])


def _cuadrado(lado: float) -> np.ndarray:
    h = lado / 2
    return np.array([[-h, h, 0.0], [h, h, 0.0], [h, -h, 0.0], [-h, -h, 0.0]])


def _observaciones(ids, marcadores_por_camara, camaras) -> list[Observacion]:
    return [Observacion(cam, _plano_marcador(i), _cuadrado(MARCADORES[i].lado), marcadores[i])
            for cam, marcadores in zip(camaras, marcadores_por_camara) for i in ids if i in marcadores]


@dataclass
class PoseChapa:
    """Pose de una chapa (chapa → mesa) con lo que se ha usado para medirla."""

    chapa: str  # "base" o "movil"
    pose: Pose
    ids: list[int] = field(default_factory=list)
    n_camaras: int = 0
    error_px: float = 0.0
    metodo: str = "6gdl"  # "6gdl" o "plano_mesa" (la base, 3 GDL sobre la mesa)
    vista: bool = True  # False si es la última pose conocida y ahora no se ve

    @property
    def calidad(self) -> float:
        """0-1: menos si la ve una sola cámara (la móvil, aún menos: su distancia es supuesta) o si no se ve ahora."""
        una = 0.8 if self.chapa == "base" else 0.6
        return (1.0 if self.n_camaras >= 2 else una) * (1.0 if self.vista else 0.9)


def _apoyar(pose: Pose, camara: Camara, centro_marcador, caja: np.ndarray, base: Pose | None) -> Pose:
    """Desliza la pose a lo largo del rayo de la cámara hasta que la chapa apoye en la base (si cae encima: en la
    ranura de la T o en la cara junto al tope de la esquina, lo que esté más cerca) o en la mesa.

    Con una sola cámara, la distancia a un ArUco pequeño y oblicuo es lo peor medido (decenas de mm) y la orientación
    y la dirección del rayo, lo mejor; una chapa quieta siempre apoya en algo.
    """
    rayo = pose.aplicar(centro_marcador) - camara.centro
    rayo /= np.linalg.norm(rayo)
    if abs(rayo[2]) < 1e-3:
        return pose

    def a_altura(h: float) -> Pose:
        z_min = float(pose.aplicar(caja)[:, 2].min())
        return Pose(pose.R, pose.t + (h - z_min) / rayo[2] * rayo)

    if base is not None:
        cara = float(base.t[2])
        movida = a_altura(cara)
        x, y, _ = base.inversa().aplicar(movida.aplicar(caja).mean(axis=0))
        if abs(x) < CAJA_BASE[1] and abs(y) < CAJA_BASE[3] + 10.0:
            junta = min(TipoJunta, key=lambda tipo: abs(y - Y_CORDON[tipo] - GROSOR_CHAPA / 2))
            return a_altura(cara + Z_CANTO_MOVIL[junta])
    return a_altura(0.0)


def estimar_pose_chapa(chapa: str, marcadores_a: dict, marcadores_b: dict, camaras: tuple[Camara, Camara],
                       en_mesa: bool | None = None, base: Pose | None = None) -> PoseChapa | None:
    """Pose de la `chapa` ("base" o "movil") con los ArUco detectados en las dos cámaras; None si no se ve.

    Móvil: se usa el juego de ids (principal o repuesto) con más detecciones; si solo la ve una cámara, la distancia
    se fija suponiendo que apoya en la `base` (si se da y cae encima) o en la mesa (`metodo = "1camara_apoyada"`).
    Base: si `en_mesa` (por defecto, si la pose 6D dice que está tumbada en la mesa) se reajusta con 3 GDL a la
    altura `GROSOR_CHAPA`.
    """
    if chapa == "base":
        ids = [ID_BASE]
    else:
        ids = list(max(PARES_MOVIL, key=lambda par: sum(i in m for i in par for m in (marcadores_a, marcadores_b))))
    obs = _observaciones(ids, [marcadores_a, marcadores_b], camaras)
    if not obs:
        return None
    caja = _vertices(CAJA_BASE if chapa == "base" else CAJA_MOVIL)

    def sobre_la_mesa(pose: Pose) -> bool:
        """Una chapa no atraviesa la mesa: descarta la solución espejo de IPPE con una sola cámara."""
        return float(pose.aplicar(caja)[:, 2].min()) > -MARGEN_MESA

    def inestabilidad(pose: Pose) -> float:
        """Grados que le faltan a la chapa para estar tumbada (normal vertical) o de pie (altura vertical)."""
        normal, alto = abs(pose.R[2, 1]), pose.R[2, 2]
        return float(np.degrees(np.arccos(np.clip(max(normal, alto), -1.0, 1.0))))

    una_camara = len({id(o.camara) for o in obs}) == 1
    pose, error = ajustar_pose(obs, valida=None if una_camara else sobre_la_mesa,
                               preferencia=inestabilidad if una_camara else None)
    metodo = "6gdl"
    if chapa == "base":
        inclinacion = np.degrees(np.arccos(np.clip(pose.R[2, 2], -1.0, 1.0)))
        if en_mesa or (en_mesa is None and inclinacion < 10.0 and abs(pose.t[2] - GROSOR_CHAPA) < 10.0):
            giro = np.degrees(np.arctan2(pose.R[1, 0], pose.R[0, 0]))
            plana = Pose(rot_z(giro), [pose.t[0], pose.t[1], GROSOR_CHAPA])
            pose, error = ajustar_pose(obs, plana, libres=(2, 3, 4))
            metodo = "plano_mesa"
    if error > ERROR_MAX_POSE_PX:
        log.debug("pose de %s descartada: error %.1f px", chapa, error)
        return None
    n_camaras = len({id(o.camara) for o in obs})
    if chapa == "movil" and n_camaras == 1:
        pose = _apoyar(pose, obs[0].camara, obs[0].plano.t, caja, base)
        metodo = "1camara_apoyada"
    vistos = sorted({i for i in ids for m in (marcadores_a, marcadores_b) if i in m})
    return PoseChapa(chapa, pose, vistos, n_camaras, error, metodo)


class FiltroPose:
    """Suaviza la pose de una chapa y decide cuándo se ha movido.

    - Pose nueva cerca de la vigente (< `dist_mov` mm y < `ang_mov` grados): media exponencial con `alfa`.
    - Lejos: no se acepta hasta que `confirmar` poses seguidas coinciden entre sí (un valor raro suelto se ignora);
      entonces se adopta la nueva y `actualizar` devuelve `movida = True`. La primera pose también cuenta como cambio.
    - Sin detección: se conserva la última pose con `vista = False` (una mano tapa el ArUco).
    """

    def __init__(self, alfa: float = 0.3, dist_mov: float = 4.0, ang_mov: float = 3.0, confirmar: int = 2):
        self.alfa, self.dist_mov, self.ang_mov, self.confirmar = alfa, dist_mov, ang_mov, confirmar
        self.reiniciar()

    def reiniciar(self):
        self.pose: PoseChapa | None = None
        self._candidata: PoseChapa | None = None
        self._n_candidata = 0

    def _cerca(self, a: PoseChapa, b: PoseChapa) -> bool:
        d, ang = a.pose.diferencia(b.pose)
        return d < self.dist_mov and ang < self.ang_mov

    def actualizar(self, nueva: PoseChapa | None) -> tuple[PoseChapa | None, bool]:
        if nueva is None:
            if self.pose is not None:
                self.pose.vista = False
            return self.pose, False
        if self.pose is None:
            self.pose = nueva
            return self.pose, True
        if self._cerca(self.pose, nueva):
            self._candidata, self._n_candidata = None, 0
            U, _, Vt = np.linalg.svd((1 - self.alfa) * self.pose.pose.R + self.alfa * nueva.pose.R)
            R = U @ np.diag([1.0, 1.0, np.linalg.det(U @ Vt)]) @ Vt
            t = (1 - self.alfa) * self.pose.pose.t + self.alfa * nueva.pose.t
            self.pose = PoseChapa(nueva.chapa, Pose(R, t), nueva.ids, nueva.n_camaras, nueva.error_px,
                                  nueva.metodo, True)
            return self.pose, False
        if self._candidata is not None and self._cerca(self._candidata, nueva):
            self._n_candidata += 1
        else:
            self._candidata, self._n_candidata = nueva, 1
        if self._n_candidata >= self.confirmar:
            self.pose, self._candidata, self._n_candidata = nueva, None, 0
            return self.pose, True
        self.pose.vista = True
        return self.pose, False


# --- seguidor ----------------------------------------------------------------------------------------------------
class SeguidorEstereo:
    """Une todo: par de imágenes → (`Muestra` en el marco del cordón o None, `Junta`).

    Las poses de las chapas se refrescan en el primer par y cada `cada_n`; entre medias solo se busca el LED (primero
    cerca de donde estaba). La `Muestra` lleva la punta en el marco del cordón de la junta (x a lo largo, y transversal,
    z = altura real sobre la cara de la base, para `apoyada`), filtrada con `FiltroTrazo`; `gatillo` y los ángulos los
    rellena quien fusiona con la antorcha. Atributos útiles: `junta`, `base` y `movil` (`PoseChapa`), `movimiento`
    (True en el par en que una chapa aparece o se mueve), `led` ({"a", "b"}: (u, v, brillo) o None), `punta` (LED
    triangulado en la mesa, sin filtrar) y `error_led_px`.
    """

    def __init__(self, estereo: CalibracionEstereo, color: str = COLOR_LED, cada_n: int = 15,
                 filtro: FiltroTrazo | None = None, alfa_pose: float = 0.3,
                 error_max_px: float = ERROR_MAX_LED_PX, radio_busqueda: int = 80):
        self.estereo = estereo
        self.camaras = estereo.camaras()
        self.color, self.cada_n, self.error_max_px, self.radio_busqueda = color, cada_n, error_max_px, radio_busqueda
        self.filtro = filtro if filtro is not None else FiltroTrazo()
        self.filtro_base, self.filtro_movil = FiltroPose(alfa_pose), FiltroPose(alfa_pose)
        self.reiniciar()

    def reiniciar(self):
        self.filtro_base.reiniciar()
        self.filtro_movil.reiniciar()
        self.filtro.reiniciar()
        self.base: PoseChapa | None = None
        self.movil: PoseChapa | None = None
        self.junta: Junta = reconocer_junta(None, None)
        self.movimiento = False
        self.led: dict[str, tuple[float, float, float] | None] = {"a": None, "b": None}
        self.punta: np.ndarray | None = None
        self.error_led_px: float | None = None
        self._n = 0

    def _sin_led(self, marcadores: dict, nombre: str) -> dict:
        """Quita los marcadores con el LED encima o al lado: su halo desplaza las esquinas."""
        led = self.led[nombre]
        if led is None:
            return marcadores
        m = MARGEN_LED_MARCADOR_PX
        return {i: e for i, e in marcadores.items()
                if not (e[:, 0].min() - m <= led[0] <= e[:, 0].max() + m
                        and e[:, 1].min() - m <= led[1] <= e[:, 1].max() + m)}

    def refrescar_poses(self, imagen_a: np.ndarray, imagen_b: np.ndarray) -> Junta:
        """Detecta los ArUco en las dos imágenes, actualiza las poses (suavizadas) y reconoce la junta.

        Una chapa que no se ve (tapada por la mano o por el halo del LED) conserva su última pose.
        """
        ma = self._sin_led(detectar_marcadores_v2(imagen_a), "a")
        mb = self._sin_led(detectar_marcadores_v2(imagen_b), "b")
        self.base, movida_base = self.filtro_base.actualizar(estimar_pose_chapa("base", ma, mb, self.camaras))
        movil = estimar_pose_chapa("movil", ma, mb, self.camaras, base=self.base.pose if self.base else None)
        self.movil, movida_movil = self.filtro_movil.actualizar(movil)
        self.movimiento = movida_base or movida_movil
        if self.movimiento:
            self.filtro.reiniciar()  # el trazo anterior ya no vale
        calidad = min(p.calidad for p in (self.base, self.movil) if p is not None) \
            if (self.base or self.movil) else 1.0
        una = self.movil is not None and self.movil.n_camaras == 1
        self.junta = reconocer_junta(self.base.pose if self.base else None,
                                     self.movil.pose if self.movil else None, calidad,
                                     TOLERANCIAS_UNA_CAMARA if una else None)
        if self.movimiento and self.junta.tipo is not EstadoJunta.SIN_BASE:
            log.info("junta: %s (%s)", self.junta.nombre, self.junta.motivo or "completa")
        return self.junta

    def _buscar_led(self, imagen: np.ndarray, nombre: str):
        previo = self.led[nombre]
        if previo is not None:
            r = self.radio_busqueda
            led = detectar_led(imagen, self.color, roi=(int(previo[0]) - r, int(previo[1]) - r, 2 * r, 2 * r))
            if led is not None:
                return led
        return detectar_led(imagen, self.color)

    def procesar(self, imagen_a: np.ndarray, imagen_b: np.ndarray, t: float) -> tuple[Muestra | None, Junta]:
        """Un par de imágenes → (Muestra o None si no hay LED en las dos, no casa o la junta no tiene cordón, Junta)."""
        self.movimiento = False
        self.led = {"a": self._buscar_led(imagen_a, "a"), "b": self._buscar_led(imagen_b, "b")}
        if self._n % self.cada_n == 0:
            self.refrescar_poses(imagen_a, imagen_b)
        self._n += 1
        resultado = triangular_led(self.camaras, self.led["a"], self.led["b"], self.error_max_px)
        if resultado is None:
            self.punta = self.error_led_px = None
            return None, self.junta
        self.punta, self.error_led_px = resultado
        if self.junta.cordon is None:
            return None, self.junta
        filtrado = self.filtro.filtrar(t, punta_en_cordon(self.punta, self.junta))
        if filtrado is None:
            return None, self.junta
        return Muestra(t=t, x=filtrado[0], y=filtrado[1], z=filtrado[2], gatillo=False), self.junta
