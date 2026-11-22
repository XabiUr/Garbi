"""Cámara sintética: pinta lo que vería la webcam de seguimiento, sin hardware.

Sustituye a la webcam real para probar el seguimiento en simulación (`FuenteSintetica.read()` se usa como
`cv2.VideoCapture.read()`). Es una cámara estenopeica (pinhole) sin distorsión que mira la mesa desde arriba e
inclinada. Pinta, de atrás hacia delante:

- la mesa (textura de madera) y la base de anclajes con la huella de cada anclaje;
- los ArUco de los 4 anclajes y el de la pieza, con su margen blanco, en perspectiva correcta (una homografía por
  plano, con el mismo convenio de esquinas que OpenCV);
- la pieza (recta o en T) como cajas sombreadas; el alma de la T tapa lo que queda detrás;
- el LED de la antorcha como un punto brillante con halo (núcleo saturado) y, si se pide, reflejos parásitos;
- luz no uniforme, exposición ("baja" como la webcam real con exposición manual, o "normal"), desenfoque y ruido.

Cada imagen va con su `Verdad` (pose de la pieza y píxel del LED) para medir el error del seguimiento.
Unidades: mm. Poses: `p_B = R @ p_A + t` para "A respecto a B".
"""
from __future__ import annotations

from dataclasses import dataclass, field

import cv2
import numpy as np

from lewelder.contrato import (
    ALMA_ALTO,
    ALMA_GROSOR,
    ALTURA_BASE_ANCLAJES,
    ANCLAJES,
    ARUCO_EN_ANCLAJE,
    ARUCO_EN_PIEZA,
    CHAPA_ANCHO,
    CHAPA_GROSOR,
    COLOR_LED,
    DICCIONARIO_ARUCO,
    HOLGURA_JUNTA,
    IDS_ANCLAJE,
    IDS_PIEZA,
    LADO_ARUCO_ANCLAJE,
    LADO_ARUCO_PIEZA,
    LONGITUD_CORDON,
    MARGEN_X,
    TipoPieza,
)
from lewelder.seguimiento import ALTURA_PLANO_PIEZA, CalibracionCamara, pose_anclaje, rot_z

COLORES_LED_BGR = {"verde": (0.35, 1.0, 0.25), "rojo": (0.25, 0.3, 1.0), "azul": (1.0, 0.45, 0.2)}
RADIO_LED = 2.5  # mm (LED de 5 mm)
MARGEN_BLANCO = 5.0  # mm de margen blanco alrededor de la parte negra de cada ArUco
GANANCIA = {"normal": 1.0, "baja": 0.16}  # exposición relativa
# LED: (amplitud del núcleo, amplitud del halo, radio del halo en radios del LED) por exposición.
PERFIL_LED = {"normal": (5.0, 0.7, 2.5), "baja": (5.0, 0.5, 2.0)}
# Base de anclajes (marco de la mesa): cubre las huellas de los 4 anclajes.
BASE_ANCLAJES = (85.0, 365.0, -200.0, 200.0, 0.0, ALTURA_BASE_ANCLAJES)
LUZ_DIR = np.array([0.3, 0.4, 1.0]) / np.linalg.norm([0.3, 0.4, 1.0])
# Albedos (BGR, 0-1) de PLA mate.
COLOR_BASE = (0.27, 0.27, 0.29)
COLOR_HUELLA = (0.21, 0.21, 0.23)
COLOR_PIEZA = (0.70, 0.64, 0.58)
CARAS = [([0, 3, 2, 1], (0, 0, -1)), ([4, 5, 6, 7], (0, 0, 1)), ([0, 1, 5, 4], (0, -1, 0)),
         ([2, 3, 7, 6], (0, 1, 0)), ([1, 2, 6, 5], (1, 0, 0)), ([3, 0, 4, 7], (-1, 0, 0))]


def cajas_pieza(tipo: TipoPieza) -> list[tuple[float, ...]]:
    """Cajas (xmin, xmax, ymin, ymax, zmin, zmax) de la pieza en su marco, en orden de dibujo."""
    x0, x1 = -MARGEN_X, LONGITUD_CORDON + MARGEN_X
    g = HOLGURA_JUNTA / 2
    if TipoPieza(tipo) is TipoPieza.RECTA:
        return [(x0, x1, g, g + CHAPA_ANCHO, -CHAPA_GROSOR, 0.0), (x0, x1, -g - CHAPA_ANCHO, -g, -CHAPA_GROSOR, 0.0)]
    return [(x0, x1, -CHAPA_ANCHO, CHAPA_ANCHO, -CHAPA_GROSOR, 0.0), (x0, x1, 0.0, ALMA_GROSOR, 0.0, ALMA_ALTO)]


def _vertices_caja(lim) -> np.ndarray:
    x0, x1, y0, y1, z0, z1 = lim
    return np.array([[x0, y0, z0], [x1, y0, z0], [x1, y1, z0], [x0, y1, z0],
                     [x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1]])


def _segmento_corta_caja(a, b, lim, eps=1e-6) -> bool:
    """¿El segmento a→b (sin sus extremos) atraviesa la caja? Método de las losas."""
    d = b - a
    s0, s1 = eps, 1 - eps
    for k in range(3):
        lo, hi = lim[2 * k], lim[2 * k + 1]
        if abs(d[k]) < 1e-12:
            if a[k] <= lo or a[k] >= hi:
                return False
            continue
        ta, tb = sorted(((lo - a[k]) / d[k], (hi - a[k]) / d[k]))
        s0, s1 = max(s0, ta), min(s1, tb)
        if s0 >= s1:
            return False
    return True


def textura_tablero(tablero: tuple[int, int] = (9, 6), px: int = 40) -> np.ndarray:
    """Textura BGR del tablero de ajedrez de `tablero` esquinas interiores, con un cuadro de margen blanco.

    Como la hoja impresa (`herramientas/generar_hardware.py`): el cuadro de arriba a la izquierda es negro.
    `px` píxeles por cuadro.
    """
    cols, filas = tablero[0] + 1, tablero[1] + 1
    cuadros = (np.indices((filas, cols)).sum(axis=0) % 2 * 255).astype(np.uint8)
    tex = cv2.resize(cuadros, (cols * px, filas * px), interpolation=cv2.INTER_NEAREST)
    tex = cv2.copyMakeBorder(tex, px, px, px, px, cv2.BORDER_CONSTANT, value=255)
    return cv2.GaussianBlur(cv2.cvtColor(tex, cv2.COLOR_GRAY2BGR), (0, 0), 1.5)


@dataclass
class PoseCamara:
    """Pose de la mesa respecto a la cámara: p_cam = R @ p_mesa + t (cámara: X derecha, Y abajo, Z delante)."""

    R: np.ndarray
    t: np.ndarray

    @classmethod
    def mirando(cls, origen, objetivo, arriba=(0.0, 0.0, 1.0)) -> PoseCamara:
        origen, objetivo, arriba = (np.asarray(v, dtype=float) for v in (origen, objetivo, arriba))
        z = objetivo - origen
        z /= np.linalg.norm(z)
        y = -arriba - np.dot(-arriba, z) * z  # "abajo" de la imagen = abajo del mundo
        y /= np.linalg.norm(y)
        x = np.cross(y, z)
        R = np.vstack([x, y, z])
        return cls(R, -R @ origen)

    @classmethod
    def por_defecto(cls, altura: float = 750.0, inclinacion: float = 25.0,
                    objetivo=(250.0, 0.0, ALTURA_PLANO_PIEZA), azimut: float = -50.0) -> PoseCamara:
        """Cámara a `altura` mm sobre la mesa, inclinada `inclinacion`° respecto a la vertical, mirando a
        `objetivo` desde el lado `azimut` (0 = desde +X de la mesa, enfrente del robot).

        Por defecto: la posición que ve la T entera y todos los ArUco en los 4 anclajes del contrato (el alma de la
        T del anclaje A, girado -90°, tapa el LED si la cámara mira desde +X; desde -50° no)."""
        objetivo = np.asarray(objetivo, dtype=float)
        d = (altura - objetivo[2]) * np.tan(np.radians(inclinacion))
        a = np.radians(azimut)
        origen = objetivo + [d * np.cos(a), d * np.sin(a), 0.0]
        origen[2] = altura
        return cls.mirando(origen, objetivo)

    @property
    def centro(self) -> np.ndarray:
        return -self.R.T @ self.t


@dataclass
class Reflejo:
    """Brillo parásito pequeño sobre la pieza (posición en el marco de la pieza)."""

    posicion: tuple[float, float, float]
    radio_mm: float = 0.6
    intensidad: float = 2.5
    color: tuple[float, float, float] = (1.0, 1.0, 1.0)  # BGR


@dataclass
class Verdad:
    tipo: TipoPieza
    anclaje: str
    id_aruco: int
    R_mesa_pieza: np.ndarray
    t_mesa_pieza: np.ndarray
    R_camara_pieza: np.ndarray
    t_camara_pieza: np.ndarray
    exposicion: str
    led: tuple[float, float, float] | None = None  # marco de la pieza
    pixel_led: tuple[float, float] | None = None  # None si no hay LED o no se ve
    led_visible: bool = False
    pixeles_reflejos: list[tuple[float, float]] = field(default_factory=list)


class CamaraSintetica:
    def __init__(self, K=None, pose: PoseCamara | None = None, ancho: int = 1280, alto: int = 720,
                 semilla: int = 0, ruido: float = 2.0, desenfoque: float = 0.6):
        self.ancho, self.alto = ancho, alto
        if K is None:
            f = 1000.0 * ancho / 1280
            K = [[f, 0, (ancho - 1) / 2], [0, f, (alto - 1) / 2], [0, 0, 1]]
        self.K = np.asarray(K, dtype=float)
        self.pose = pose if pose is not None else PoseCamara.por_defecto()
        self.rng = np.random.default_rng(semilla)
        self.sigma_ruido, self.desenfoque = ruido, desenfoque
        self._fondos: dict[bool, np.ndarray] = {}
        self._texturas: dict[int, np.ndarray] = {}
        self._luz = self._campo_luz()

    def calibracion(self) -> CalibracionCamara:
        return CalibracionCamara(self.K, np.zeros(5), self.ancho, self.alto)

    # --- proyección ------------------------------------------------------------------------------------------
    def proyectar(self, p_mesa) -> tuple[float, float]:
        u, v = self._proyectar(np.asarray(p_mesa, dtype=float).reshape(1, 3))[0]
        return float(u), float(v)

    def _proyectar(self, P: np.ndarray) -> np.ndarray:
        pc = P @ self.pose.R.T + self.pose.t
        uv = pc @ self.K.T
        return uv[:, :2] / uv[:, 2:3]

    # --- elementos de la escena ------------------------------------------------------------------------------
    def _campo_luz(self) -> np.ndarray:
        """Luz no uniforme: foco suave descentrado, viñeteo y degradado. Valores ~0,5-1."""
        v, u = np.mgrid[0:self.alto, 0:self.ancho].astype(np.float32)
        u, v = u / self.ancho, v / self.alto
        foco = np.exp(-((u - 0.35) ** 2 + (v - 0.3) ** 2) / (2 * 0.35 ** 2))
        vineteo = 1 - 0.35 * ((u - 0.5) ** 2 + (v - 0.5) ** 2)
        luz = (0.55 + 0.4 * foco + 0.08 * u) * vineteo
        return (luz / luz.max()).astype(np.float32)[..., None]

    def _pegar(self, img: np.ndarray, tex: np.ndarray, H: np.ndarray) -> None:
        """Pega `tex` en `img` con la homografía H (píxel de la textura → píxel de la imagen), solo en su recuadro."""
        ht, wt = tex.shape[:2]
        borde = np.array([[-0.5, -0.5], [wt - 0.5, -0.5], [wt - 0.5, ht - 0.5], [-0.5, ht - 0.5]], np.float64)
        p = cv2.perspectiveTransform(borde[None], H)[0]
        x0, y0 = np.maximum(np.floor(p.min(axis=0)).astype(int) - 1, 0)
        x1 = min(int(np.ceil(p[:, 0].max())) + 2, img.shape[1])
        y1 = min(int(np.ceil(p[:, 1].max())) + 2, img.shape[0])
        if x1 <= x0 or y1 <= y0:
            return
        Hr = np.array([[1, 0, -x0], [0, 1, -y0], [0, 0, 1]], np.float64) @ H
        tam = (x1 - x0, y1 - y0)
        pegado = cv2.warpPerspective(tex, Hr, tam, flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
        alfa = cv2.warpPerspective(np.full((ht, wt), 255, np.uint8), Hr, tam, flags=cv2.INTER_LINEAR,
                                   borderMode=cv2.BORDER_CONSTANT).astype(np.float32)[..., None] / 255
        roi = img[y0:y1, x0:x1]
        roi[:] = (roi * (1 - alfa) + pegado * alfa + 0.5).astype(np.uint8)

    def _pegar_plano(self, img, tex, origen, eje_x, eje_y, ancho_mm, alto_mm) -> None:
        """Pega `tex` en el rectángulo de `ancho_mm` x `alto_mm` centrado en `origen` (mesa) con esos ejes.

        La fila 0 de la textura queda en +eje_y (como la fila de arriba de un ArUco en +Y del marcador).
        """
        R, t = self.pose.R, self.pose.t
        Hp = self.K @ np.column_stack([R @ eje_x, R @ eje_y, R @ np.asarray(origen, dtype=float) + t])
        ht, wt = tex.shape[:2]
        sx, sy = ancho_mm / wt, alto_mm / ht
        A = np.array([[sx, 0, -ancho_mm / 2 + sx / 2], [0, -sy, alto_mm / 2 - sy / 2], [0, 0, 1]])
        self._pegar(img, tex, Hp @ A)

    def _textura_aruco(self, id_aruco: int, lado_mm: float) -> tuple[np.ndarray, float]:
        """Textura BGR del ArUco con su margen blanco y su tamaño total en mm."""
        celda = 16
        if id_aruco not in self._texturas:
            diccionario = cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, DICCIONARIO_ARUCO))
            negro = cv2.aruco.generateImageMarker(diccionario, id_aruco, 6 * celda, borderBits=1)
            margen = int(round(MARGEN_BLANCO * 6 * celda / lado_mm))
            tex = cv2.copyMakeBorder(negro, margen, margen, margen, margen, cv2.BORDER_CONSTANT, value=255)
            tex = (tex.astype(np.float32) * (0.9 - 0.06) / 255 + 0.06) * 255  # papel 0,9; tinta 0,06
            tex = cv2.GaussianBlur(tex, (0, 0), 1.0)  # antialias al reducir
            self._texturas[id_aruco] = cv2.cvtColor(tex.astype(np.uint8), cv2.COLOR_GRAY2BGR)
        tex = self._texturas[id_aruco]
        return tex, tex.shape[0] * lado_mm / (6 * celda)

    def _pegar_aruco(self, img, id_aruco, lado_mm, centro, R_mesa) -> None:
        tex, total = self._textura_aruco(id_aruco, lado_mm)
        self._pegar_plano(img, tex, centro, R_mesa[:, 0], R_mesa[:, 1], total, total)

    def _dibujar_caja(self, img, lim, R, t, color) -> None:
        """Caja `lim` de un marco con pose (R, t) respecto a la mesa: caras visibles, sombreado de Lambert."""
        V = _vertices_caja(lim) @ R.T + t
        uv = self._proyectar(V)
        c = self.pose.centro
        for idx, n_local in CARAS:
            n = R @ np.array(n_local, dtype=float)
            if np.dot(n, c - V[idx].mean(axis=0)) <= 0:
                continue  # cara de espaldas
            luz = 0.55 + 0.45 * max(0.0, float(np.dot(n, LUZ_DIR)))
            col = tuple(float(255 * k * luz) for k in color)
            pts = np.round(uv[idx] * 16).astype(np.int32)
            cv2.fillConvexPoly(img, pts, col, lineType=cv2.LINE_AA, shift=4)

    def _textura_mesa(self) -> np.ndarray:
        """Madera clara a 1 px/mm: vetas a lo largo de X y algo de ruido."""
        rng = np.random.default_rng(11)
        alto, ancho = 1000, 900
        y = np.arange(alto, dtype=np.float32)[:, None]
        x = np.arange(ancho, dtype=np.float32)[None, :]
        vetas = 0.5 + 0.5 * np.sin(y / 3.1 + 2.0 * np.sin(x / 90.0) + 1.5 * np.sin(y / 47.0))
        grano = cv2.GaussianBlur(rng.normal(0, 1, (alto, ancho)).astype(np.float32), (0, 0), 3)
        k = 0.85 + 0.08 * vetas + 0.05 * grano
        base = np.array([0.42, 0.56, 0.68], np.float32)  # BGR madera
        return np.clip(k[..., None] * base * 255, 0, 255).astype(np.uint8)

    def _fondo(self, dibujar_anclajes: bool) -> np.ndarray:
        """Mesa + base de anclajes + huellas + ArUco de los anclajes (no cambia entre fotogramas)."""
        if dibujar_anclajes not in self._fondos:
            img = np.full((self.alto, self.ancho, 3), 40, np.uint8)  # pared/suelo al fondo
            mesa = self._textura_mesa()
            self._pegar_plano(img, mesa, (250.0, 0.0, 0.0), np.array([1.0, 0, 0]), np.array([0, 1.0, 0]),
                              mesa.shape[1], mesa.shape[0])
            I = np.eye(3)
            self._dibujar_caja(img, BASE_ANCLAJES, I, np.zeros(3), COLOR_BASE)
            for nombre in ANCLAJES:
                R, t = pose_anclaje(nombre, ALTURA_BASE_ANCLAJES)
                huella = (-MARGEN_X - 1, LONGITUD_CORDON + MARGEN_X + 1, -CHAPA_ANCHO - 2, CHAPA_ANCHO + 2, 0, 0)
                V = _vertices_caja(huella)[[0, 1, 2, 3]] @ R.T + t
                pts = np.round(self._proyectar(V) * 16).astype(np.int32)
                cv2.fillConvexPoly(img, pts, tuple(255 * k for k in COLOR_HUELLA), cv2.LINE_AA, 4)
            if dibujar_anclajes:
                for id_aruco, nombre in IDS_ANCLAJE.items():
                    R, t = pose_anclaje(nombre, ALTURA_BASE_ANCLAJES)
                    self._pegar_aruco(img, id_aruco, LADO_ARUCO_ANCLAJE, R @ np.array(ARUCO_EN_ANCLAJE) + t, R)
            self._fondos[dibujar_anclajes] = img
        return self._fondos[dibujar_anclajes]

    def _anadir_punto(self, img, uv, z, radio_mm, a_nucleo, a_halo, k_halo, color) -> None:
        """Suma un punto de luz (núcleo + halo gaussiano) centrado en uv con subpíxel."""
        f = self.K[0, 0]
        r = max(f * radio_mm / z, 0.3)
        s = k_halo * r
        w = int(np.ceil(4 * s)) + 2
        u, v = uv
        x0, x1 = max(int(u) - w, 0), min(int(u) + w + 1, self.ancho)
        y0, y1 = max(int(v) - w, 0), min(int(v) + w + 1, self.alto)
        if x1 <= x0 or y1 <= y0:
            return
        ys, xs = np.mgrid[y0:y1, x0:x1].astype(np.float32)
        d = np.hypot(xs - u, ys - v)
        perfil = a_nucleo / (1 + np.exp((d - r) / 0.6)) + a_halo * np.exp(-d ** 2 / (2 * s ** 2))
        img[y0:y1, x0:x1] += perfil[..., None] * np.asarray(color, np.float32)

    # --- render ----------------------------------------------------------------------------------------------
    def renderizar(self, tipo: TipoPieza | str = TipoPieza.RECTA, anclaje: str = "A", led=None,
                   exposicion: str = "baja", reflejo: bool | list[Reflejo] = False, ruido: bool = True,
                   id_aruco: int | None = None, desfase=(0.0, 0.0, 0.0), color_led: str = COLOR_LED,
                   dibujar_anclajes: bool = True) -> tuple[np.ndarray, Verdad]:
        """Pinta la escena: pieza `tipo` en `anclaje` y LED en `led` (marco de la pieza, None = apagado/oculto).

        `desfase = (dx, dy, dgiro)` mueve la pieza dentro del anclaje (mm, mm, grados; holgura real).
        `reflejo`: True para dos reflejos por defecto (uno pequeño del color del LED, otro blanco) o una lista.
        Devuelve (imagen BGR uint8, Verdad).
        """
        tipo = TipoPieza(tipo)
        id_aruco = IDS_PIEZA[tipo][0] if id_aruco is None else id_aruco
        R_a, t_a = pose_anclaje(anclaje, ALTURA_PLANO_PIEZA)
        dx, dy, dg = desfase
        R_tp = R_a @ rot_z(dg)
        t_tp = t_a + R_a @ np.array([dx, dy, 0.0])
        R_cp = self.pose.R @ R_tp
        t_cp = self.pose.R @ t_tp + self.pose.t

        img = self._fondo(dibujar_anclajes).copy()
        cajas = cajas_pieza(tipo)
        self._dibujar_caja(img, cajas[0], R_tp, t_tp, COLOR_PIEZA)
        if tipo is TipoPieza.RECTA:
            self._dibujar_caja(img, cajas[1], R_tp, t_tp, COLOR_PIEZA)
        self._pegar_aruco(img, id_aruco, LADO_ARUCO_PIEZA, R_tp @ np.array(ARUCO_EN_PIEZA) + t_tp, R_tp)
        if tipo is TipoPieza.T:
            self._dibujar_caja(img, cajas[1], R_tp, t_tp, COLOR_PIEZA)  # el alma, encima de todo

        imagen = img.astype(np.float32) * (self._luz * (GANANCIA[exposicion] / 255.0))
        verdad = Verdad(tipo, anclaje, id_aruco, R_tp, t_tp, R_cp, t_cp, exposicion)
        a_nucleo, a_halo, k_halo = PERFIL_LED[exposicion]
        color = COLORES_LED_BGR[color_led]
        if led is not None:
            verdad.led = tuple(float(v) for v in led)
            p_mesa = R_tp @ np.asarray(led, dtype=float) + t_tp
            z = (self.pose.R @ p_mesa + self.pose.t)[2]
            uv = self._proyectar(p_mesa[None])[0]
            # Tapado por la pieza: el segmento cámara→LED, en el marco de la pieza, atraviesa alguna caja.
            cam_pieza = R_tp.T @ (self.pose.centro - t_tp)
            tapado = any(_segmento_corta_caja(cam_pieza, np.asarray(led, float), c) for c in cajas)
            dentro = 0 <= uv[0] <= self.ancho - 1 and 0 <= uv[1] <= self.alto - 1 and z > 0
            if dentro and not tapado:
                self._anadir_punto(imagen, uv, z, RADIO_LED, a_nucleo, a_halo, k_halo, color)
                verdad.pixel_led, verdad.led_visible = (float(uv[0]), float(uv[1])), True
        if reflejo is True:
            x, y = (led[0], led[1]) if led is not None else (60.0, 0.0)
            reflejo = [Reflejo((x + 25.0, y - 15.0, 0.0), 0.6, 2.5, color),
                       Reflejo((x - 20.0, y - 22.0, 0.0), 1.5, 3.0, (1.0, 1.0, 1.0))]
        for r in reflejo or []:
            p_mesa = R_tp @ np.asarray(r.posicion, dtype=float) + t_tp
            z = (self.pose.R @ p_mesa + self.pose.t)[2]
            uv = self._proyectar(p_mesa[None])[0]
            self._anadir_punto(imagen, uv, z, r.radio_mm, r.intensidad, 0.15 * r.intensidad, 1.5, r.color)
            verdad.pixeles_reflejos.append((float(uv[0]), float(uv[1])))

        if self.desenfoque > 0:
            imagen = cv2.GaussianBlur(imagen, (0, 0), self.desenfoque)
        if ruido and self.sigma_ruido > 0:
            imagen += self.rng.standard_normal(imagen.shape, dtype=np.float32) * (self.sigma_ruido / 255.0)
        return (np.clip(imagen, 0, 1) * 255 + 0.5).astype(np.uint8), verdad

    def renderizar_tablero(self, giro, posicion, tablero: tuple[int, int] = (9, 6), cuadro_mm: float = 25.0,
                           ruido: bool = True) -> np.ndarray:
        """Foto de un tablero de ajedrez (para probar la calibración) con pose respecto a la cámara.

        `giro`: vector de Rodrigues (rad) respecto a un tablero de frente; `posicion`: centro del tablero (mm) en
        el marco de la cámara.
        """
        cols, filas = tablero[0] + 1, tablero[1] + 1
        px = 40
        tex = textura_tablero(tablero, px)
        R = cv2.Rodrigues(np.asarray(giro, dtype=float))[0]
        Hp = self.K @ np.column_stack([R[:, 0], R[:, 1], np.asarray(posicion, dtype=float)])
        ancho_mm, alto_mm = (cols + 2) * cuadro_mm, (filas + 2) * cuadro_mm
        sx, sy = ancho_mm / tex.shape[1], alto_mm / tex.shape[0]
        A = np.array([[sx, 0, -ancho_mm / 2 + sx / 2], [0, sy, -alto_mm / 2 + sy / 2], [0, 0, 1]])
        img = np.full((self.alto, self.ancho, 3), 90, np.uint8)
        self._pegar(img, tex, Hp @ A)
        imagen = img.astype(np.float32) * (self._luz / 255.0)
        if self.desenfoque > 0:
            imagen = cv2.GaussianBlur(imagen, (0, 0), self.desenfoque)
        if ruido and self.sigma_ruido > 0:
            imagen += self.rng.standard_normal(imagen.shape, dtype=np.float32) * (self.sigma_ruido / 255.0)
        return (np.clip(imagen, 0, 1) * 255 + 0.5).astype(np.uint8)


class FuenteSintetica:
    """Fuente de vídeo simulada con la interfaz de `cv2.VideoCapture` (`read`, `isOpened`, `release`, `get`).

    `trayectoria(t)` da la posición del LED en el marco de la pieza en el instante t (s), o None si está apagado.
    El fotograma k es el instante t = k / fps. Tras cada `read`, `t` y `verdad` describen el fotograma leído.
    """

    def __init__(self, trayectoria, tipo: TipoPieza | str = TipoPieza.RECTA, anclaje: str = "B", fps: float = 30.0,
                 camara: CamaraSintetica | None = None, semilla: int = 0, **opciones):
        self.trayectoria, self.tipo, self.anclaje, self.fps = trayectoria, tipo, anclaje, fps
        self.camara = camara if camara is not None else CamaraSintetica(semilla=semilla)
        self.opciones = opciones
        self._k = 0
        self._abierta = True
        self.t: float | None = None
        self.verdad: Verdad | None = None

    def isOpened(self) -> bool:  # noqa: N802 (misma interfaz que cv2.VideoCapture)
        return self._abierta

    def read(self) -> tuple[bool, np.ndarray | None]:
        if not self._abierta:
            return False, None
        self.t = self._k / self.fps
        img, self.verdad = self.camara.renderizar(self.tipo, self.anclaje, led=self.trayectoria(self.t),
                                                  **self.opciones)
        self._k += 1
        return True, img

    def get(self, propiedad: int) -> float:
        return {cv2.CAP_PROP_FRAME_WIDTH: self.camara.ancho, cv2.CAP_PROP_FRAME_HEIGHT: self.camara.alto,
                cv2.CAP_PROP_FPS: self.fps}.get(propiedad, 0.0)

    def release(self) -> None:
        self._abierta = False
