"""Visión clásica de Garbi con la cámara fija: alfombrilla, tabla, taladro y viruta.

**Obsoleta:** la escena ya no tiene ArUco (especificación técnica del 19-11), así que `Camara.calibrar`, `analizar` y
`PercepcionVision` ya no funcionan con ella. La percepción sin ArUco está en `garbi.percepcion`. Se deja como
referencia.

Funciona igual con la imagen simulada que con la webcam real; solo cambian las intrínsecas de la cámara.

1. **Cámara ↔ mesa**: los centros de los 4 ArUco de la alfombrilla (posición conocida) dan la pose de la cámara con
   `solvePnP`. Se calibra una vez (la cámara no se mueve) y se vigila con un marcador.
2. **Tabla**: los centros de sus 2 ArUco, proyectados sobre el plano de la cara de la tabla, dan (x, y, giro).
3. **Taladro**: la bola naranja de la tapa; su centro, proyectado sobre el plano a la altura de la bola cuando la
   broca apoya en la tabla, da la punta de la broca.
4. **Viruta**: píxeles color serrín. Los que caen dentro de la cara de la tabla son viruta «tabla»; los que caen sobre
   la alfombrilla y lejos de la tabla son «alfombrilla» (el canto de la tabla, de color parecido, queda fuera).

5. **Apunto con la cámara del robot** (`punta_desde_robot`): la broca es una barra fina, gris metálica y casi vertical;
   su punto más bajo en la imagen es donde toca la tabla. Ese píxel, proyectado sobre el plano de la cara de la tabla
   con la pose de la cámara (cinemática del robot), da la punta sin depender de la inclinación del taladro (la bola
   naranja de arriba se aparta 20 mm de la vertical de la punta con solo 5° de inclinación).

Todas las posiciones en mm, marco de la mesa.
"""
from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from garbi import contrato as g

DICCIONARIO = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
_PARAMETROS = cv2.aruco.DetectorParameters()
_PARAMETROS.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX  # los marcadores ocupan pocos píxeles
_PARAMETROS.cornerRefinementWinSize = 3
_DETECTOR = cv2.aruco.ArucoDetector(DICCIONARIO, _PARAMETROS)
ALTURA_PEGATINA = 0.4  # mm: las pegatinas sobresalen un poco de su superficie

# Colores (HSV de OpenCV: H 0-179)
NARANJA_BAJO, NARANJA_ALTO = (5, 150, 120), (20, 255, 255)
SERRIN_BAJO, SERRIN_ALTO = (12, 40, 140), (32, 170, 255)


def intrinsecas_sim(resolucion=g.RESOLUCION_VISION, fovy=g.FOVY_FIJA) -> np.ndarray:
    """Matriz K de una cámara de MuJoCo con ese campo vertical (píxeles cuadrados, centro en el centro)."""
    ancho, alto = resolucion
    f = (alto / 2) / np.tan(np.radians(fovy) / 2)
    return np.array([[f, 0, ancho / 2], [0, f, alto / 2], [0, 0, 1.0]])


def detectar_marcadores(img_rgb) -> dict[int, np.ndarray]:
    """{id: esquinas (4x2, píxeles)} de los ArUco visibles, en el orden de OpenCV."""
    gris = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY)
    esquinas, ids, _ = _DETECTOR.detectMarkers(gris)
    if ids is None:
        return {}
    return {int(i): c.reshape(4, 2).astype(np.float64) for i, c in zip(ids.flatten(), esquinas)}


def esquinas_locales(centro, lado: float) -> np.ndarray:
    """Esquinas de un ArUco pegado recto (en su propio plano), en el orden en que las devuelve OpenCV: la 0 arriba a
    la izquierda (−x, +y) y la arista 0→1 hacia +x. Así se pegan las pegatinas (y así salen en la simulación)."""
    h = lado / 2
    return np.asarray(centro, float)[:2] + np.array([[-h, h], [h, h], [h, -h], [-h, -h]])


def ajuste_rigido_2d(locales: np.ndarray, mesa: np.ndarray) -> tuple[np.ndarray, float]:
    """Traslación y giro (grados) que mejor llevan `locales` a `mesa` (mínimos cuadrados, Kabsch en el plano)."""
    ml, mm = locales.mean(axis=0), mesa.mean(axis=0)
    a, b = locales - ml, mesa - mm
    giro = np.arctan2((a[:, 0] * b[:, 1] - a[:, 1] * b[:, 0]).sum(), (a * b).sum())
    c, s_ = np.cos(giro), np.sin(giro)
    t = mm - np.array([[c, -s_], [s_, c]]) @ ml
    return t, float(np.degrees(giro))


@dataclass
class Camara:
    K: np.ndarray
    R: np.ndarray  # mesa → cámara
    t: np.ndarray

    @classmethod
    def calibrar(cls, img_rgb, K: np.ndarray) -> "Camara | None":
        """Pose de la cámara con las esquinas de los ArUco de la alfombrilla (bastan 2 de los 4: 8 puntos)."""
        vistos = detectar_marcadores(img_rgb)
        conocidos = g.esquinas_aruco_alfombrilla()
        ids = [i for i in conocidos if i in vistos]
        if len(ids) < 2:
            return None
        z = g.ALFOMBRILLA_GROSOR + ALTURA_PEGATINA
        obj = np.vstack([np.column_stack([esquinas_locales(conocidos[i], g.LADO_ARUCO_ALFOMBRILLA), np.full(4, z)])
                         for i in ids])
        img = np.vstack([vistos[i] for i in ids])
        ok, rvec, tvec = cv2.solvePnP(obj, img, K, None, flags=cv2.SOLVEPNP_ITERATIVE)
        if not ok:
            return None
        R, _ = cv2.Rodrigues(rvec)
        return cls(K, R, tvec.reshape(3))

    def a_plano(self, uv, z: float) -> np.ndarray:
        """Punto de la mesa (x, y) donde el rayo del píxel `uv` corta el plano horizontal de altura z (mm)."""
        uv = np.atleast_2d(np.asarray(uv, dtype=float))
        rayos_cam = np.linalg.inv(self.K) @ np.vstack([uv.T, np.ones(len(uv))])
        centro = -self.R.T @ self.t
        rayos = self.R.T @ rayos_cam
        s = (z - centro[2]) / rayos[2]
        pts = centro[:, None] + rayos * s
        return pts[:2].T

    def mascara_alfombrilla(self, forma, margen: float = 5.0) -> np.ndarray:
        """Máscara (uint8 0/255) de los píxeles que caen sobre la alfombrilla (menos `margen` mm del borde)."""
        if getattr(self, "_mascara", None) is None or self._mascara.shape != tuple(forma):
            cx, cy = g.ALFOMBRILLA_CENTRO
            hx, hy = g.ALFOMBRILLA_TAMANO[0] / 2 - margen, g.ALFOMBRILLA_TAMANO[1] / 2 - margen
            esquinas = np.array([[cx - hx, cy - hy], [cx + hx, cy - hy], [cx + hx, cy + hy], [cx - hx, cy + hy]])
            poli = self.proyectar(np.column_stack([esquinas, np.full(4, g.ALFOMBRILLA_GROSOR)]))
            self._mascara = np.zeros(forma, np.uint8)
            cv2.fillPoly(self._mascara, [np.round(poli).astype(np.int32)], 255)
        return self._mascara

    def proyectar(self, p_mesa) -> np.ndarray:
        p = np.atleast_2d(np.asarray(p_mesa, dtype=float))
        uvw = self.K @ (self.R @ p.T + self.t[:, None])
        return (uvw[:2] / uvw[2]).T


# Broca vista por la cámara del robot: gris metálico (poca saturación; en sombra puede ser bastante oscura) y una barra
# fina y alargada en cualquier orientación de la imagen (la cámara gira con la muñeca)
BROCA_SAT_MAX, BROCA_V_MIN, BROCA_V_MAX = 50, 40, 150  # por debajo del blanco de las pegatinas, aun en sombra (ajustar con la broca real)
BROCA_LARGO_MIN_PX, BROCA_ESBELTEZ_MIN = 25, 3.0


BROCA_LEJOS_MAX = 50.0  # mm: más lejos de la estimación de la cámara de arriba no es la broca (8° → ~35 mm)
BROCA_COBERTURA_MIN = 0.7  # fracción del segmento proyectado de la broca que tiene que caer sobre la mancha gris


def _es_una_broca_en(punta, cam: "Camara", mascara: np.ndarray, z_cara: float, alto: float = 45.0) -> bool:
    """¿Hay una barra gris donde se vería una broca vertical con la punta en `punta`? Proyecta el segmento de la broca
    (de la punta a `alto` mm por encima) y mira qué fracción cae sobre la máscara."""
    zs = np.linspace(z_cara + 3, z_cara + alto, 20)
    uv = cam.proyectar(np.column_stack([np.full(20, punta[0]), np.full(20, punta[1]), zs]))
    h, w = mascara.shape
    dentro = (uv[:, 0] >= 0) & (uv[:, 0] < w) & (uv[:, 1] >= 0) & (uv[:, 1] < h)
    if dentro.sum() < 10:
        return False
    u, v = uv[dentro, 0].astype(int), uv[dentro, 1].astype(int)
    return float(np.mean(mascara[v, u] > 0)) >= BROCA_COBERTURA_MIN


def _extremo_de_ancho_constante(pts: np.ndarray, centro: np.ndarray, eje_img: np.ndarray) -> np.ndarray:
    """Extremo de abajo de la broca: el último corte (a lo largo de su eje en la imagen) cuyo ancho sigue siendo el de
    la broca. Lo que se le pega por abajo con otro ancho (el borde de una pegatina, una sombra, viruta) se descarta."""
    a = (pts - centro) @ eje_img  # posición a lo largo del eje (crece hacia abajo en el mundo)
    perp = np.array([-eje_img[1], eje_img[0]])
    b = (pts - centro) @ perp
    cortes = np.floor(a / 2.0).astype(int)  # cortes de 2 px
    idx = np.unique(cortes)
    anchos = np.array([np.ptp(b[cortes == k]) + 1 for k in idx])
    ancho_broca = np.median(anchos)
    bueno = (anchos >= 0.6 * ancho_broca) & (anchos <= 1.4 * ancho_broca)
    # desde el centro hacia abajo, hasta el primer corte que deja de tener el ancho de la broca
    ultimo = idx[0]
    for k, ok in zip(idx, bueno):
        if k < 0:
            continue
        if not ok:
            break
        ultimo = k
    sel = cortes == ultimo
    return np.array([pts[sel, 0].mean(), pts[sel, 1].mean()])


def punta_desde_robot(img_rgb, cam: "Camara", aprox=None, z_cara: float = g.ALTURA_CARA_TABLA,
                      radio_broca: float = 4.0) -> np.ndarray | None:
    """Punta de la broca (x, y, z en mm, mesa) vista por la cámara del robot, o None si no se ve.

    Candidatas: barras grises (tras quitar con una apertura morfológica las líneas finas, como los bordes de las
    pegatinas) que en la imagen siguen la vertical del mundo en su sitio: los bordes que están tumbados en la mesa no
    la siguen. Con `aprox` (la punta que da la cámara de arriba) se prefiere la más cercana. La punta es el extremo de
    abajo de la barra, donde entra en la tabla."""
    hsv = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2HSV)
    gris = ((hsv[..., 1] <= BROCA_SAT_MAX) & (hsv[..., 2] >= BROCA_V_MIN) & (hsv[..., 2] <= BROCA_V_MAX))
    gris = cv2.morphologyEx(gris.astype(np.uint8), cv2.MORPH_OPEN, np.ones((7, 7), np.uint8))  # la broca mide ~20 px
    n, etiquetas, stats, _ = cv2.connectedComponentsWithStats(gris, connectivity=8)
    gris_ancho = cv2.dilate(gris, np.ones((11, 11), np.uint8))  # tolera ~8° de inclinación del taladro
    centro_cam = -cam.R.T @ cam.t
    mejor = None
    for k in range(1, n):
        if stats[k, cv2.CC_STAT_AREA] < 40:
            continue
        vs, us = np.nonzero(etiquetas == k)
        pts = np.column_stack([us, vs]).astype(np.float64)
        centro = pts.mean(axis=0)
        _, sv, vt = np.linalg.svd(pts - centro, full_matrices=False)
        largo = np.sqrt(12) * sv[0] / np.sqrt(len(pts))  # longitud de una barra uniforme con esa dispersión
        ancho = len(pts) / max(largo, 1.0)  # ancho medio (aguanta pegotes pequeños en los extremos)
        if largo < BROCA_LARGO_MIN_PX or largo / ancho < BROCA_ESBELTEZ_MIN:
            continue
        eje_img = vt[0]
        # La vertical del mundo vista en la imagen, en el sitio de la barra
        p_medio = cam.a_plano(centro, z_cara + g.LARGO_BROCA / 2)[0]
        a, b = cam.proyectar([[*p_medio, z_cara + g.LARGO_BROCA / 2], [*p_medio, z_cara]])
        abajo = (b - a) / (np.linalg.norm(b - a) or 1.0)
        if abs(eje_img @ abajo) < np.cos(np.radians(20)):
            continue
        if eje_img @ abajo < 0:
            eje_img = -eje_img
        extremo = _extremo_de_ancho_constante(pts, centro, eje_img)
        punta = cam.a_plano(extremo, z_cara)[0]
        hacia = punta - centro_cam[:2]
        punta = punta + hacia / (np.linalg.norm(hacia) or 1.0) * radio_broca  # el eje está detrás de la cara vista
        if aprox is not None and np.linalg.norm(punta - np.asarray(aprox)[:2]) > BROCA_LEJOS_MAX:
            continue  # demasiado lejos de donde la cámara de arriba ve el taladro
        if not _es_una_broca_en(punta, cam, gris_ancho, z_cara):
            continue  # la barra vista no está donde estaría una broca vertical con esa punta
        coste = -largo if aprox is None else float(np.linalg.norm(punta - np.asarray(aprox)[:2]))
        if mejor is None or coste < mejor[0]:
            mejor = (coste, punta)
    if mejor is None:
        return None
    return np.array([mejor[1][0], mejor[1][1], z_cara])


@dataclass
class Vista:
    """Lo que la visión ha entendido de una imagen."""
    tabla: g.PoseTabla | None
    taladro: np.ndarray | None  # punta de la broca (mm, mesa) o None
    viruta_tabla: np.ndarray  # Nx2 (mm, mesa)
    viruta_alfombrilla: np.ndarray


def analizar(img_rgb, cam: Camara, tabla_previa: g.PoseTabla | None = None) -> Vista:
    """Lo que hay en la imagen. Si no se ve ningún ArUco de la tabla (la mano, el brazo o la viruta sobre la pegatina
    los tapan), se usa `tabla_previa`: la tabla no se mueve sola y en cuanto reaparece un marcador se corrige."""
    hsv = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2HSV)
    marcas = detectar_marcadores(img_rgb)

    # Tabla: ajuste rígido de las esquinas de sus ArUco visibles (basta uno: la mano o la boca pueden tapar el otro)
    tabla = None
    vistos = [(i, c) for i, c in zip(g.IDS_ARUCO_TABLA, g.ARUCO_TABLA_EN_TABLA) if i in marcas]
    if vistos:
        z = g.ALTURA_CARA_TABLA + ALTURA_PEGATINA
        locales = np.vstack([esquinas_locales(c, g.LADO_ARUCO_TABLA) for _, c in vistos])
        en_mesa = np.vstack([cam.a_plano(marcas[i], z) for i, _ in vistos])
        centro, giro = ajuste_rigido_2d(locales, en_mesa)
        tabla = g.PoseTabla(float(centro[0]), float(centro[1]), float(giro))
    elif tabla_previa is not None:
        tabla = tabla_previa

    # Taladro: bola naranja; centro del círculo mínimo que envuelve la mancha mayor (aguanta la cara en sombra)
    taladro = None
    naranja = cv2.inRange(hsv, NARANJA_BAJO, NARANJA_ALTO)
    contornos, _ = cv2.findContours(naranja, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    contornos = [k for k in contornos if cv2.contourArea(k) >= 30]
    if contornos:
        (u, v_), _ = cv2.minEnclosingCircle(max(contornos, key=cv2.contourArea))
        z_bola = g.ALTURA_CARA_TABLA + g.ALTURA_BOLA_SOBRE_PUNTA
        taladro = cam.a_plano((u, v_), z_bola)[0]

    # Viruta: píxeles color serrín dentro de la alfombrilla (fuera de ella la mesa de madera es del mismo color),
    # repartidos entre la cara de la tabla y la alfombrilla
    serrin = cv2.inRange(hsv, SERRIN_BAJO, SERRIN_ALTO)
    serrin &= cam.mascara_alfombrilla(serrin.shape)
    vs, us = np.nonzero(serrin)
    uv = np.stack([us, vs], axis=1).astype(float)
    v_tabla, v_alf = np.zeros((0, 2)), np.zeros((0, 2))
    if len(uv):
        en_cara = cam.a_plano(uv, g.ALTURA_CARA_TABLA)
        en_alf = cam.a_plano(uv, g.ALFOMBRILLA_GROSOR)
        if tabla is not None:
            dentro = tabla.contiene_varios(en_cara, margen=2.0)
            lejos = ~tabla.contiene_varios(en_alf, margen=-22.0)
        else:
            dentro = np.zeros(len(uv), bool)
            lejos = np.ones(len(uv), bool)
        v_tabla = en_cara[dentro]
        v_alf = en_alf[lejos & ~dentro]
        v_alf = v_alf[_dentro_alfombrilla(v_alf)]
    return Vista(tabla, taladro, v_tabla, v_alf)


def _dentro_alfombrilla(pts) -> np.ndarray:
    if len(pts) == 0:
        return np.zeros(0, bool)
    cx, cy = g.ALFOMBRILLA_CENTRO
    hx, hy = g.ALFOMBRILLA_TAMANO[0] / 2 - 5, g.ALFOMBRILLA_TAMANO[1] / 2 - 5
    return (np.abs(pts[:, 0] - cx) <= hx) & (np.abs(pts[:, 1] - cy) <= hy)


class PercepcionVision:
    """Percepción por cámara para el orquestador (misma interfaz que `PercepcionOraculo`)."""

    def __init__(self, mundo, K: np.ndarray | None = None, hz: float = 10.0):
        from garbi.robot_vivo import VistaTaladro  # evita import circular

        self._VistaTaladro = VistaTaladro
        self.m = mundo
        self.K = intrinsecas_sim() if K is None else K
        self.cam: Camara | None = None
        self._vista: Vista | None = None
        self._ultima_tabla: g.PoseTabla | None = None  # memoria de la tabla para cuando se tapan sus marcadores
        self._t = -1.0
        self.periodo = 1.0 / hz  # la visión analiza a `hz` (como la webcam real con el bucle a 30 Hz)

    def _actualizar(self) -> Vista:
        if self._vista is None or self.m.t - self._t >= self.periodo - 1e-6 or self.m.t < self._t:
            img = self.m.imagen("top", g.RESOLUCION_VISION)
            if self.cam is None:
                self.cam = Camara.calibrar(img, self.K)
                if self.cam is None:
                    raise RuntimeError("No veo los 4 ArUco de la alfombrilla: no puedo calibrar la cámara")
            previa = self._vista.tabla if self._vista is not None else self._ultima_tabla
            self._vista = analizar(img, self.cam, previa)
            self._ultima_tabla = self._vista.tabla
            self._t = self.m.t
        return self._vista

    def refrescar(self) -> None:
        """Olvida la última vista: el siguiente acceso analiza una imagen nueva."""
        if self._vista is not None:
            self._ultima_tabla = self._vista.tabla
        self._vista = None

    def broca_robot(self, aprox=None):
        """Punta de la broca con la cámara del robot (el «apunto»), o None si no la ve. `aprox`: la de arriba."""
        R, t = self.m.pose_camara("wrist")
        ancho, alto = g.RESOLUCION_VISION
        K = intrinsecas_sim(g.RESOLUCION_VISION, self.m.fovy("wrist"))
        img = self.m.imagen("wrist", g.RESOLUCION_VISION)
        return punta_desde_robot(img, Camara(K, R, t), aprox)

    def tabla(self):
        return self._actualizar().tabla

    def taladro(self):
        p = self._actualizar().taladro
        if p is None:
            return self._VistaTaladro(False, None)
        return self._VistaTaladro(True, np.array([p[0], p[1], g.ALTURA_CARA_TABLA]))

    def viruta(self, donde: str):
        v = self._actualizar()
        return v.viruta_tabla if donde == "tabla" else v.viruta_alfombrilla
