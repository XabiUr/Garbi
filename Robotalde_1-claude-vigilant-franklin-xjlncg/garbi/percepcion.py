"""Percepción de Garbi sin ArUco (especificación técnica, M2 paso 2 y M3).

Entra: las imágenes {"top", "wrist"} (RGB, 640 × 480), la postura del robot y el tiempo. Sale: una `garbi.tipos.Escena`.
Funciona igual con imágenes de la simulación que de las webcams reales: solo cambian las intrínsecas (en la
simulación salen del campo de visión de la cámara de MuJoCo; en el robot real, de `cv2.calibrateCamera`). Nada se lee
de la verdad de la simulación.

1. **Cámara de arriba ↔ mesa** (`calibrar_camara_arriba`): máscara azul del tapete, una recta por borde (con los bordes
   refinados por debajo del píxel) y sus cortes dan las 4 esquinas; `solvePnP` con sus medidas (400 × 450).
2. **Madera** (`detectar_madera`): madera clara sin vinilo (solución final). Las manchas de color madera dentro del
   tapete dan una primera pose (`minAreaRect` en la mesa, y candidatas por si un lado está tapado); el borde
   madera/tapete (en lo azul que es cada píxel respecto a su brillo; en los lados cuyo canto ve la cámara, la arista de
   abajo), refinado por debajo del píxel, se ajusta a un rectángulo de 200 × 300 con pesos robustos (lo tapado por las
   manos, el brazo o el taladro no cuenta). Solo se cambia la pose con buena evidencia; si no, se queda la anterior.
   El giro de 180° lo resuelve la pegatina magenta de la esquina (+x, +y); si está tapada, la pose anterior.
3. **Taladro** (`detectar_bola`, `SeguidorTaladro`): bola naranja; su rayo cortado con el plano a la altura típica de
   la bola (broca apoyada en la madera). Mediana de 0,3 s, velocidad por recta ajustada en 0,3 s y quieto si < 5 mm/s.
4. **Broca de cerca** (`medir_broca`): cámara de la muñeca. Los dos bordes de la broca (Ø8) son las rectas tangentes
   del cilindro: el ángulo entre sus planos da la distancia de la cámara al eje y su corte da la dirección del eje; la
   punta es donde la barra deja de tener el color de la broca. Con la pose de la cámara (cinemática) sale la punta en
   la mesa. Si la broca acaba tapada por las mordazas, no se da punta.
   Ojo: con las posturas de preapunto y acompañar de `garbi.lateral` la broca queda a ~220-250 mm y, apoyada, detrás
   de las mordazas. `postura_mirar_broca` da una postura que la ve de cerca (60-120 mm) y fuera de las mordazas.
5. **Viruta** (`contar_viruta`): píxeles color serrín (más saturado que la cara de la madera clara) en un círculo de
   35 mm alrededor de cada agujero conocido. Con madera clara de verdad apenas se distingue: la limpieza es fija.
6. **Manos** (`garbi.manos`: MediaPipe en el robot real, color de piel en la simulación) y **taladro agarrado**: bola
   naranja y una mano a < DIST_MANO_TALADRO del cuerpo del taladro (medido en la imagen).
7. **Broca clavada / levantada**: `apoyada` con histéresis y la punta sobre la madera; `Broca.evento` marca el instante.

Umbrales de color y parámetros: `garbi/config_vision.yaml` (`Percepcion(config=...)`).

Unidades: mm, grados y segundos; marco de la mesa (origen en la base del robot, x hacia la persona, z arriba).
"""
from __future__ import annotations

import warnings
from collections import deque
from dataclasses import dataclass

import cv2
import numpy as np

from garbi import contrato as g
from garbi.calibracion import CinematicaRobot, PoseBase  # noqa: F401  (PoseBase se reexporta)
from garbi.config_vision import ConfigVision, cargar_config, config_por_defecto
from garbi.contrato import PoseTabla
from garbi.tipos import DIST_MANO_TALADRO, Broca, Escena, Mano, Taladro

RESOLUCION = (640, 480)
FOVY_TOP, FOVY_WRIST = g.FOVY_FIJA, 75.0  # campos verticales de las cámaras de la simulación

# Tapete y madera
Z_TAPETE = g.ALFOMBRILLA_GROSOR
Z_CARA = g.ALTURA_CARA_TABLA  # cara de la madera (tapete + 18)
# Los umbrales de color están en `garbi/config_vision.yaml` (editable en el sitio); estos son los mismos valores, para
# quien los importe
AZUL_BAJO, AZUL_ALTO = (100, 100, 35), (130, 255, 255)
# Taladro: bola naranja
NARANJA_BAJO, NARANJA_ALTO = (5, 150, 110), (22, 255, 255)
AREA_BOLA = (30, 6000)  # px a 640 × 480
Z_BOLA = Z_CARA + g.ALTURA_BOLA_SOBRE_PUNTA  # altura típica de la bola: broca apoyada en la madera
VENTANA_TALADRO = 0.3  # s: mediana y velocidad
VELOCIDAD_QUIETO = 5.0  # mm/s
# También quieto si todas las posiciones de la ventana caen a menos de QUIETO_RADIO de su mediana: con el temblor de la
# mano (±1-2 mm a 3-5 Hz) la recta de 0,3 s daba 5-10 mm/s y el taladro apoyado nunca se veía quieto (robustez del ciclo)
QUIETO_RADIO = 3.5  # mm
MARGEN_ZONA = 40.0  # mm: la zona de trabajo es la madera más este margen
# Broca
DIAMETRO_BROCA = g.DIAMETRO_BROCA
BROCA_SAT_MAX, BROCA_V_MIN, BROCA_V_MAX = 60, 70, 240  # (config: broca)
ROBOT_BAJO, ROBOT_ALTO = (15, 100, 60), (35, 255, 255)  # amarillo del SO-101 (HSV; config: robot)
INCLINACION_MAX = 15.0  # grados: más que esto respecto a la vertical no se cree el eje medido
APOYO_ENTRA, APOYO_SALE, APOYO_DURACION = 3.0, 8.0, 0.2  # mm, mm, s (histéresis)
# Coherencia con la cámara de arriba: la bola debe verse donde la pone la punta medida por la muñeca (punta + eje de la
# broca · ALTURA_BOLA_SOBRE_PUNTA). Con la integración (T6) se vio que, mientras el brazo va hacia la postura de mirar,
# la muñeca a veces mide una barra que no es la broca o la mide de lado (punta 30-50 mm desviada): sin esta
# comprobación el ciclo creía que el taladro se había movido o levantado y nunca llegaba a acompañar.
COHERENCIA_BOLA_PX = 12.0
# Con la broca apoyada (y vertical), el marcador visto desde arriba da la punta en planta a ~1-3 mm; la muñeca, a
# ~1 mm quieta en la postura de mirar pero a 4-7 mm mientras el brazo va hacia ella (integración, T6): si las dos
# están a menos de FUSION_MM, la punta en planta es su media.
FUSION_MM = 10.0
# Una medida de la muñeca solo vale si la anterior (de hace ≤ CONFIRMAR_S) cae a menos de CONFIRMAR_MM en planta (al
# apoyar, la punta baja pero no se mueve en planta): una lectura
# suelta desviada (una barra que no es la broca, vista de lado) hacía creer al ciclo que el taladro se había movido.
CONFIRMAR_MM, CONFIRMAR_S = 6.0, 0.2
# Broca en el aire sin la muñeca: la altura sale del radio aparente de la bola (distancia = f · R / r). Medido en la
# simulación: ±25 mm en absoluto (como dice M3), pero los cambios de altura se miden bien; por eso se le resta lo que
# daba con la broca apoyada (`_desvio_altura`, aprendido en cada apoyo). Sin esto la punta se suponía en la madera y,
# con la broca a 50-110 mm, se estimaba 50-130 mm desplazada en planta: SEGUIR se acercaba al taladro de verdad.
VENTANA_ALTURA = 0.14  # s: mediana de la altura estimada (3 lecturas a 15 Hz; con 0,3 s se quedaba 30 mm atrás al levantar)
DESVIO_ALTURA_INICIAL = 10.0  # mm: sesgo típico de la altura por el radio antes del primer apoyo
SALE_ARRIBA_MM = 6.0  # sin la muñeca: si el marcador se aparta esto de donde estaba al apoyar, ya no está apoyada
# Clavada aproximada solo desde arriba (F4, respaldo de la muñeca: con el brazo en la postura prudente la muñeca ve la
# punta casi siempre, pero hay lecturas que no se confirman): la bola baja ≥ BAJADA_ARRIBA_MM en VENTANA_BAJADA s, se
# para T_APOYO_ARRIBA s y la altura por el radio queda ≤ APOYO_ARRIBA_MM. En la simulación la altura por el radio va
# con +10-20 mm de sesgo antes del primer apoyo (luego se corrige) y ±3 mm de ruido; con la broca a 50 mm da 60-70.
APOYO_ARRIBA_MM, BAJADA_ARRIBA_MM, VENTANA_BAJADA, T_APOYO_ARRIBA = 22.0, 25.0, 2.0, 0.4
# Taladro inclinado: la bola está ALTURA_BOLA_SOBRE_PUNTA · sen(inclinación) al lado de la vertical de la punta (47 mm
# con 8°). Cada medida buena de la muñeca da ese desfase en planta (punta − bola proyectada a su altura); se promedia
# (DESFASE_PESO) y se usa para estimar la punta solo desde arriba, centrar la búsqueda de la muñeca y dar el eje de la
# broca (`Broca.eje`), con el que el ciclo calcula la holgura con el taladro inclinado. Se olvida al salir el taladro
# (la persona puede cogerlo de otra forma). Robustez del ciclo: sin esto, con 8° la punta estimada desde arriba caía
# a ~47 mm de la de verdad.
DESFASE_PESO = 0.3
# Por debajo de esto (~2°) el desfase no se distingue del todo del error de la muñeca (2-4 mm): se toma el taladro por vertical
# (eje conocido, desfase 0) y la punta apoyada en planta sigue siendo la media de la muñeca y de arriba (si no, el agujero
# apuntado heredaba el sesgo de la muñeca: 4-5 mm, integración).
DESFASE_MIN = 12.0
DESFASE_MIN0 = 6.0  # entre DESFASE_MIN0 y DESFASE_MIN el desfase entra poco a poco (sin saltos de la punta estimada)
# Fusión de la punta apoyada en planta: la muñeca pesa la mitad a ≤ MUNECA_CERCA mm del eje de la broca y menos cuanto
# más lejos ((MUNECA_CERCA / d)²): desde la postura de mirar lejana (150-180 mm, cuando aún no se sabe el eje) la
# muñeca iba 5-8 mm desviada y la bola apoyada vista desde arriba a 1-3 mm (robustez del ciclo: agujero apuntado a 5-6
# mm del de verdad).
MUNECA_CERCA = 110.0
# Más lejos que esto (cámara de la muñeca al eje de la broca) la medida de la muñeca no se usa: a 220-280 mm (postura de
# paso hacia la de mirar, o acompañando) la punta salía 10-15 mm desviada y ese «desfase» falso se tomaba por un
# taladro inclinado 2-3° (robustez del ciclo). A ≤ 180 mm el error es de 1-5 mm.
DISTANCIA_MUNECA_MAX = 200.0
DESFASE_MAX = g.ALTURA_BOLA_SOBRE_PUNTA * np.sin(np.radians(INCLINACION_MAX))
# Viruta: serrín más saturado que la cara de madera clara (config: serrin). Con madera clara de verdad apenas se
# distingue: la limpieza de la solución final es fija y no depende de esto
SERRIN_BAJO, SERRIN_ALTO = (16, 95, 90), (32, 200, 255)
RADIO_VIRUTA = 35.0
# Taladro agarrado (mano + taladro): se mantiene AGARRE_MANTENER s después de dejar de ver la mano cerca (la detección
# de la mano parpadea, sobre todo con MediaPipe y la mano de lado)
AGARRE_MANTENER = 0.3
DISTANCIA_AGUJERO_NUEVO = 6.0  # mm: más cerca de uno conocido es el mismo agujero


def intrinsecas(fovy: float, resolucion=RESOLUCION) -> np.ndarray:
    """K de una cámara de píxeles cuadrados con ese campo vertical y el centro en el centro (como MuJoCo)."""
    ancho, alto = resolucion
    f = (alto / 2) / np.tan(np.radians(fovy) / 2)
    return np.array([[f, 0.0, ancho / 2], [0.0, f, alto / 2], [0.0, 0.0, 1.0]])


# --- cámara con pose en la mesa ---------------------------------------------------------------------------------
@dataclass
class CamaraMesa:
    """Cámara estenopeica: p_cam = R · p_mesa + t (mm), K en píxeles."""
    K: np.ndarray
    R: np.ndarray
    t: np.ndarray

    @property
    def centro(self) -> np.ndarray:
        return -self.R.T @ self.t

    def proyectar(self, p_mesa) -> np.ndarray:
        p = np.atleast_2d(np.asarray(p_mesa, float))
        uvw = self.K @ (self.R @ p.T + self.t[:, None])
        return (uvw[:2] / uvw[2]).T

    def rayo(self, uv) -> np.ndarray:
        """Direcciones unitarias (Nx3, mesa) de los rayos de los píxeles."""
        uv = np.atleast_2d(np.asarray(uv, float))
        d = self.R.T @ (np.linalg.inv(self.K) @ np.vstack([uv.T, np.ones(len(uv))]))
        return (d / np.linalg.norm(d, axis=0)).T

    def a_plano(self, uv, z: float) -> np.ndarray:
        """(x, y) donde el rayo de cada píxel corta el plano horizontal de altura z."""
        d = self.rayo(uv)
        c = self.centro
        s = (z - c[2]) / d[:, 2]
        return (c[None, :] + d * s[:, None])[:, :2]


def _poligono(cam: CamaraMesa, esquinas_xy, z) -> np.ndarray:
    return cam.proyectar(np.column_stack([np.asarray(esquinas_xy, float), np.full(len(esquinas_xy), z)]))


def esquinas_tapete_mesa(margen: float = 0.0) -> np.ndarray:
    """Esquinas del tapete (4x2, mm) en orden: (cerca, derecha), (lejos, derecha), (lejos, izquierda), (cerca, izq.)."""
    cx, cy = g.ALFOMBRILLA_CENTRO
    hx, hy = g.ALFOMBRILLA_TAMANO[0] / 2 - margen, g.ALFOMBRILLA_TAMANO[1] / 2 - margen
    return np.array([[cx - hx, cy - hy], [cx + hx, cy - hy], [cx + hx, cy + hy], [cx - hx, cy + hy]])


# --- bordes por debajo del píxel --------------------------------------------------------------------------------
def _perfiles(escalar: np.ndarray, pts: np.ndarray, normales: np.ndarray, offs: np.ndarray) -> np.ndarray:
    """Valores (bilineales) de `escalar` en pts + o · normal para cada o de `offs` (N × len(offs))."""
    mx = (pts[:, 0:1] + normales[:, 0:1] * offs[None, :]).astype(np.float32)
    my = (pts[:, 1:2] + normales[:, 1:2] * offs[None, :]).astype(np.float32)
    return cv2.remap(escalar, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=np.nan)


def refinar_bordes(escalar: np.ndarray, pts, normales, alcance: float = 4.0, contraste_min: float = 20.0,
                   dentro_rango=None, fuera_rango=None) -> tuple[np.ndarray, np.ndarray]:
    """Lleva cada punto de un borde, a lo largo de su normal (de dentro a fuera), al cruce del nivel medio entre el
    valor de dentro y el de fuera de `escalar`. Devuelve (puntos refinados, válidos). Un punto no vale si el contraste
    es pequeño o si el nivel de dentro/fuera no cae en su rango (algo tapa el borde)."""
    pts = np.asarray(pts, float).reshape(-1, 2)
    normales = np.asarray(normales, float).reshape(-1, 2)
    offs = np.arange(-alcance, alcance + 1e-9, 0.25)
    prof = _perfiles(escalar, pts, normales, offs)
    n_lado = max(2, int(round(1.5 / 0.25)))
    with warnings.catch_warnings():  # perfiles fuera de la imagen: todo NaN, no válidos (sin aviso)
        warnings.simplefilter("ignore", RuntimeWarning)
        dentro = np.nanmedian(prof[:, :n_lado], axis=1)
        fuera = np.nanmedian(prof[:, -n_lado:], axis=1)
    valido = np.isfinite(dentro) & np.isfinite(fuera) & (np.abs(dentro - fuera) >= contraste_min)
    if dentro_rango is not None:
        valido &= (dentro >= dentro_rango[0]) & (dentro <= dentro_rango[1])
    if fuera_rango is not None:
        valido &= (fuera >= fuera_rango[0]) & (fuera <= fuera_rango[1])
    medio = (dentro + fuera) / 2
    signo = np.sign(fuera - dentro)
    rel = (prof - medio[:, None]) * signo[:, None]  # crece de dentro (<0) a fuera (>0)
    salida = pts.copy()
    for i in np.flatnonzero(valido):
        r = rel[i]
        cruces = np.flatnonzero((r[:-1] < 0) & (r[1:] >= 0))
        if len(cruces) == 0:
            valido[i] = False
            continue
        k = cruces[np.argmin(np.abs(offs[cruces]))]
        o = offs[k] + (0 - r[k]) / (r[k + 1] - r[k]) * (offs[k + 1] - offs[k])
        salida[i] = pts[i] + normales[i] * o
    return salida, valido


def refinar_por_gradiente(escalar, pts, normales, alcance: float = 4.0, salto_min: float = 15.0,
                          pendiente_min: float = 10.0) -> tuple[np.ndarray, np.ndarray]:
    """Lleva cada punto de un borde, a lo largo de su normal, al salto más fuerte (centroide de la derivada alrededor de
    su máximo). Mejor que el nivel medio cuando un lado del borde está en sombra (el nivel de dentro cambia).

    `escalar`: una imagen o una lista de canales (p. ej. V y S): entonces cuenta el módulo del salto en todos, y un
    borde gris sobre un fondo del mismo brillo pero más saturado también se ve. No vale si el salto (a ±1,5 px del
    borde) es menor que `salto_min` o si la pendiente máxima (por píxel) es menor que `pendiente_min`."""
    canales = escalar if isinstance(escalar, (list, tuple)) else [escalar]
    pts = np.asarray(pts, float).reshape(-1, 2)
    normales = np.asarray(normales, float).reshape(-1, 2)
    paso = 0.25
    offs = np.arange(-alcance, alcance + 1e-9, paso)
    profs = [_perfiles(c, pts, normales, offs) for c in canales]
    der = np.sqrt(sum(np.diff(p, axis=1) ** 2 for p in profs))
    medios = (offs[:-1] + offs[1:]) / 2
    salida, valido = pts.copy(), np.zeros(len(pts), bool)
    n15 = int(round(1.5 / paso))
    for i in range(len(pts)):
        d = der[i]
        if not np.all(np.isfinite(d)):
            continue
        k = int(np.argmax(d))
        if d[k] <= 0:
            continue
        lo, hi = max(0, k - n15), min(len(d), k + n15 + 1)
        ventana = d[lo:hi]
        w = np.where(ventana >= 0.5 * d[k], ventana, 0.0)
        o = float((w * medios[lo:hi]).sum() / w.sum())
        salto = np.sqrt(sum((np.interp(o + 1.5, offs, p[i]) - np.interp(o - 1.5, offs, p[i])) ** 2 for p in profs))
        if salto < salto_min or d[k] / paso < pendiente_min or abs(o) > alcance - 1.5:
            continue  # sin salto, o una rampa suave (sombreado del propio cilindro), o en el límite de la ventana
        salida[i] = pts[i] + normales[i] * o
        valido[i] = True
    return salida, valido


def ajustar_recta(pts: np.ndarray, iteraciones: int = 3, tolerancia: float = 1.0):
    """Recta (punto, dirección unitaria) por mínimos cuadrados totales, quitando los puntos lejanos. None si < 5."""
    pts = np.asarray(pts, float)
    usar = np.ones(len(pts), bool)
    for _ in range(iteraciones + 1):
        if usar.sum() < 5:
            return None
        c = pts[usar].mean(axis=0)
        _, _, vt = np.linalg.svd(pts[usar] - c, full_matrices=False)
        d = vt[0]
        n = np.array([-d[1], d[0]])
        dist = np.abs((pts - c) @ n)
        lim = max(tolerancia, 3.0 * 1.4826 * np.median(dist[usar]))
        nuevo = dist <= lim
        if np.array_equal(nuevo, usar):
            break
        usar = nuevo
    return c, d


def _corte(r1, r2) -> np.ndarray:
    (p1, d1), (p2, d2) = r1, r2
    A = np.column_stack([d1, -d2])
    s = np.linalg.solve(A, p2 - p1)
    return p1 + d1 * s[0]


# --- 1. cámara de arriba con las esquinas del tapete ------------------------------------------------------------
def _mascara_azul(img_rgb, cfg: ConfigVision | None = None) -> np.ndarray:
    hsv = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2HSV)
    return (cfg or config_por_defecto()).mascara(hsv, "tapete")


def _escalar_azul(img_rgb) -> np.ndarray:
    """Cuánto más azul que rojo/verde es cada píxel: alto en el tapete, bajo en la mesa, el vinilo y el robot."""
    f = img_rgb.astype(np.float32)
    return f[..., 2] - np.maximum(f[..., 0], f[..., 1])


def esquinas_tapete(img_rgb, iteraciones: int = 2, cfg: ConfigVision | None = None) -> np.ndarray | None:
    """Las 4 esquinas del tapete en la imagen (4x2, píxeles, en el orden del contorno), o None.

    Primero, el cuadrilátero de la envolvente convexa de la mancha azul; después, a lo largo de cada lado, el borde
    refinado por debajo del píxel y una recta robusta (lo que tapa el brazo se descarta); las esquinas son los cortes
    de rectas vecinas."""
    azul = _mascara_azul(img_rgb, cfg)
    azul = cv2.morphologyEx(azul, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    contornos, _ = cv2.findContours(azul, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    if not contornos:
        return None
    mayor = max(contornos, key=cv2.contourArea)
    if cv2.contourArea(mayor) < 0.02 * azul.size:
        return None
    casco = cv2.convexHull(mayor)
    quad = None
    for eps in np.linspace(0.005, 0.08, 40):
        aprox = cv2.approxPolyDP(casco, eps * cv2.arcLength(casco, True), True)
        if len(aprox) == 4:
            quad = aprox.reshape(4, 2).astype(float)
            break
    if quad is None:
        return None
    escalar = _escalar_azul(img_rgb)
    nivel_tapete = float(np.median(escalar[azul > 0]))
    for _ in range(iteraciones):
        centro = quad.mean(axis=0)
        rectas = []
        for i in range(4):
            a, b = quad[i], quad[(i + 1) % 4]
            largo = np.linalg.norm(b - a)
            d = (b - a) / largo
            n = np.array([-d[1], d[0]])
            if (a - centro) @ n < 0:
                n = -n  # hacia fuera
            s = np.arange(0.06 * largo, 0.94 * largo, 1.5)
            pts = a[None, :] + s[:, None] * d[None, :]
            ref, ok = refinar_bordes(escalar, pts, np.tile(n, (len(pts), 1)), alcance=5.0,
                                     contraste_min=0.35 * nivel_tapete, dentro_rango=(0.6 * nivel_tapete, 1e9))
            recta = ajustar_recta(ref[ok], tolerancia=0.7)
            if recta is None:
                return None
            rectas.append(recta)
        quad = np.array([_corte(rectas[(i - 1) % 4], rectas[i]) for i in range(4)])
    return quad


def calibrar_camara_arriba(img_rgb, K: np.ndarray | None = None,
                           centro_nominal=g.CAMARA_FIJA_POS, cfg: ConfigVision | None = None) -> CamaraMesa | None:
    """Pose de la cámara de arriba en la mesa a partir de las esquinas del tapete (`solvePnP`, plano).

    Qué esquina de la imagen es cuál se decide con la posición nominal del soporte de la cámara (M1): de las 8
    correspondencias posibles se queda la que pone la cámara más cerca de ella."""
    K = intrinsecas(FOVY_TOP, (img_rgb.shape[1], img_rgb.shape[0])) if K is None else K
    quad = esquinas_tapete(img_rgb, cfg=cfg)
    if quad is None:
        return None
    obj = np.column_stack([esquinas_tapete_mesa(), np.full(4, Z_TAPETE)])
    mejor = None
    for sentido in (quad, quad[::-1]):
        for k in range(4):
            img = np.roll(sentido, k, axis=0)
            ok, rvec, tvec = cv2.solvePnP(obj, img, K, None, flags=cv2.SOLVEPNP_IPPE)
            if not ok:
                continue
            R, _ = cv2.Rodrigues(rvec)
            t = tvec.reshape(3)
            cam = CamaraMesa(K, R, t)
            err = np.linalg.norm(cam.proyectar(obj) - img, axis=1).max()
            d = np.linalg.norm(cam.centro - np.asarray(centro_nominal, float))
            if err < 3.0 and (mejor is None or d < mejor[0]):
                mejor = (d, cam)
    return None if mejor is None else mejor[1]


# --- 2. madera ---------------------------------------------------------------------------------------------------
def _esquinas_tabla(x, y, giro) -> np.ndarray:
    hx, hy = g.TABLA_TAMANO[0] / 2, g.TABLA_TAMANO[1] / 2
    return PoseTabla(x, y, giro).a_mesa(np.array([[-hx, -hy], [hx, -hy], [hx, hy], [-hx, hy]]))


def _giro_cercano(giro: float, referencia: float) -> float:
    """El de giro y giro + 180 más cercano a la referencia, en (-180, 180]."""
    mejor = None
    for cand in (giro, giro + 180.0):
        c = (cand + 180.0) % 360.0 - 180.0
        d = abs((c - referencia + 180.0) % 360.0 - 180.0)
        if mejor is None or d < mejor[0]:
            mejor = (d, c)
    return mejor[1]


def _ajustar_rectangulo(pts: np.ndarray, x0: np.ndarray, iteraciones: int = 15) -> tuple[np.ndarray, np.ndarray]:
    """Ajusta (x, y, giro°) de un rectángulo de las medidas de la madera a puntos de su borde (mesa), con pesos de
    Huber. Cada punto cuenta contra el lado más cercano. Devuelve los parámetros y los residuos (mm)."""
    hx, hy = g.TABLA_TAMANO[0] / 2, g.TABLA_TAMANO[1] / 2
    p = np.asarray(x0, float).copy()

    def residuos(par):
        a = np.radians(par[2])
        c, s = np.cos(a), np.sin(a)
        d = pts - par[:2]
        lx, ly = d @ np.array([c, s]), d @ np.array([-s, c])
        rx, ry = np.abs(lx) - hx, np.abs(ly) - hy
        # lado más cercano: el de x si el punto queda más cerca de él que del de y
        return np.where(np.abs(rx) < np.abs(ry), rx, ry)

    for it in range(iteraciones):
        r = residuos(p)
        w = np.minimum(1.0, 1.0 / np.maximum(np.abs(r), 1e-9))  # Huber con k = 1 mm
        if it >= 3:  # después, fuera lo que no es borde de la madera (el portabrocas, la mano...)
            w[np.abs(r) > max(1.5, 3.0 * 1.4826 * np.median(np.abs(r)))] = 0.0
        J = np.zeros((len(pts), 3))
        for j, h in enumerate((1e-3, 1e-3, 1e-4)):
            dp = np.zeros(3)
            dp[j] = h
            J[:, j] = (residuos(p + dp) - r) / h
        JW = J * w[:, None]
        paso = -np.linalg.solve(JW.T @ J + 1e-6 * np.eye(3), JW.T @ r)
        p += paso
        if np.abs(paso[:2]).max() < 1e-3 and abs(paso[2]) < 1e-4:
            break
    return p, residuos(p)


def _mascara_madera(hsv, cfg: ConfigVision) -> np.ndarray:
    """Madera natural clara (sin vinilo): tono de madera, poco saturada; también en la sombra del taladro."""
    return cfg.mascara(hsv, "madera")


def _posicion_por_bordes(pts: np.ndarray, giro: float, referencia_xy=None) -> np.ndarray:
    """Centro de la madera con el giro dado a partir de puntos de su silueta (mesa): en cada eje de la madera se busca
    el par de bordes separados por su medida que más puntos tiene cerca (lo que añade o quita un objeto encima no
    forma ese par). Devuelve (x, y)."""
    a = np.radians(giro)
    ex, ey = np.array([np.cos(a), np.sin(a)]), np.array([-np.sin(a), np.cos(a)])
    centro = np.zeros(2)
    for eje, medida in ((ex, g.TABLA_TAMANO[0]), (ey, g.TABLA_TAMANO[1])):
        u = pts @ eje
        lo, hi = np.floor(u.min()) - 2, np.ceil(u.max()) + 2
        hist, bordes = np.histogram(u, bins=np.arange(lo, hi + 1.0, 1.0))
        suave = np.convolve(hist, np.ones(5), mode="same")
        k = int(round(medida))
        if len(suave) <= k:
            centro += eje * (u.mean())
            continue
        par = suave[:-k] + suave[k:]
        if referencia_xy is not None:  # a igualdad, la más cercana a la anterior
            c_ref = np.asarray(referencia_xy) @ eje - medida / 2
            par = par - 1e-3 * np.abs(bordes[:-1 - k] + 0.5 - c_ref)
        i = int(np.argmax(par))
        centro += eje * (bordes[i] + 0.5 + medida / 2)
    return centro


def _altura_silueta(cam: CamaraMesa, p_mesa: np.ndarray, n_mesa: np.ndarray) -> float:
    """z del borde que separa la madera del tapete en la imagen, en un lado de normal hacia fuera `n_mesa`: si la cámara
    ve el canto de ese lado, la silueta es la arista de abajo (sobre el tapete); si no, la de la cara."""
    hacia_camara = cam.centro[:2] - p_mesa
    return Z_TAPETE if float(hacia_camara @ n_mesa) > 0 else Z_CARA


def _croma_azul(img_rgb) -> np.ndarray:
    """Lo azul que es cada píxel, relativo a su brillo (0-255): la sombra sobre el tapete sigue siendo tan azul como el
    tapete; la madera y la piel dan negativo; la manga azul de la persona, bastante menos que el tapete."""
    f = img_rgb.astype(np.float32)
    return 255.0 * (f[..., 2] - np.maximum(f[..., 0], f[..., 1])) / (f.max(axis=2) + 20.0)


def _candidatas_extremos(pts: np.ndarray, giro: float) -> list[np.ndarray]:
    """Centros posibles de la madera con el giro dado si alguno de sus lados está tapado: en cada eje, el borde visible
    más lejano de cada lado más (o menos) la medida. Devuelve (x, y) para las 4 combinaciones."""
    a = np.radians(giro)
    ex, ey = np.array([np.cos(a), np.sin(a)]), np.array([-np.sin(a), np.cos(a)])
    opciones = []
    for eje, medida in ((ex, g.TABLA_TAMANO[0]), (ey, g.TABLA_TAMANO[1])):
        u = pts @ eje
        lo, hi = np.percentile(u, 0.5), np.percentile(u, 99.5)
        opciones.append([lo + medida / 2, hi - medida / 2])
    return [ex * cx + ey * cy for cx in opciones[0] for cy in opciones[1]]


def _soporte_y_refinado(escalar, nivel_tapete, cam, par, cfg: ConfigVision, iteraciones=3):
    """Refina la pose con el borde madera/tapete de la imagen por debajo del píxel (en `escalar`, lo azul que es cada
    píxel). Devuelve (pose, puntos de borde válidos). Lo que tapa el borde (una mano, el taladro, el brazo o la manga
    azul de la persona) no cuenta: el lado de dentro debe ser poco azul y el de fuera tan azul como el tapete."""
    n_ok = 0
    fuera_min = float(cfg["tapete"]["fuera_min"]) * nivel_tapete
    for it in range(iteraciones):
        esq = _esquinas_tabla(*par)
        pts_img, normales, zs = [], [], []
        for i in range(4):
            a, b = esq[i], esq[(i + 1) % 4]
            largo = np.linalg.norm(b - a)
            d = (b - a) / largo
            s = np.arange(10.0, largo - 10.0, 2.0)
            p_mesa = a[None, :] + s[:, None] * d[None, :]
            n_mesa = np.array([d[1], -d[0]])
            if (p_mesa.mean(axis=0) - par[:2]) @ n_mesa < 0:
                n_mesa = -n_mesa
            z = _altura_silueta(cam, p_mesa.mean(axis=0), n_mesa)
            uv0 = _poligono(cam, p_mesa, z)
            uv1 = _poligono(cam, p_mesa + n_mesa * 3.0, z)
            nn = uv1 - uv0
            nn /= np.linalg.norm(nn, axis=1, keepdims=True)
            pts_img.append(uv0)
            normales.append(nn)
            zs.append(np.full(len(uv0), z))
        pts_img, normales, zs = np.vstack(pts_img), np.vstack(normales), np.concatenate(zs)
        ref, ok = refinar_bordes(escalar, pts_img, normales, alcance=6.0 if it == 0 else 4.0,
                                 contraste_min=0.35 * nivel_tapete, dentro_rango=(-1e9, 0.5 * fuera_min),
                                 fuera_rango=(fuera_min, 1e9))
        n_ok = int(ok.sum())
        if n_ok < 30:
            break
        en_mesa = np.vstack([cam.a_plano(ref[ok & (zs == z)], z) for z in (Z_TAPETE, Z_CARA) if np.any(ok & (zs == z))])
        par, _ = _ajustar_rectangulo(en_mesa, par)
    return par, n_ok


def _giro_por_pegatina(hsv, cam: CamaraMesa, par, cfg: ConfigVision) -> tuple[float | None, np.ndarray | None]:
    """El giro (par[2] o par[2] + 180) que pone la pegatina donde se ve, y dónde se ve (mesa); (None, None) si no se
    ve (tapada) o no cuadra con ninguna de las dos orientaciones."""
    alto, ancho = hsv.shape[:2]
    cara = np.zeros((alto, ancho), np.uint8)
    cv2.fillPoly(cara, [np.round(_poligono(cam, _esquinas_tabla(*par), Z_CARA)).astype(np.int32)], 255)
    cara = cv2.dilate(cara, np.ones((9, 9), np.uint8))
    m = cfg.mascara(hsv, "pegatina") & cara
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    n, etiquetas, stats, centros = cv2.connectedComponentsWithStats(m)
    if n <= 1:
        return None, None
    k = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    if stats[k, cv2.CC_STAT_AREA] < cfg["pegatina"]["area_min"]:
        return None, None
    xy = cam.a_plano(centros[k], Z_CARA)[0]
    mejor = None
    for giro in (par[2], par[2] + 180.0):
        esperado = PoseTabla(par[0], par[1], giro).a_mesa(np.array(g.PEGATINA_EN_TABLA))
        d = float(np.linalg.norm(esperado - xy))
        if mejor is None or d < mejor[0]:
            mejor = (d, giro)
    if mejor[0] > cfg["pegatina"]["distancia_max"]:
        return None, xy
    return (mejor[1] + 180.0) % 360.0 - 180.0, xy


@dataclass
class LecturaMadera:
    """Detalle de la última detección de la madera (para depurar y para los tests)."""
    pose: PoseTabla | None = None
    bordes: int = 0  # puntos de borde válidos
    pegatina: np.ndarray | None = None  # dónde se vio la pegatina (mesa), o None
    giro_por_pegatina: bool = False  # el giro de 180° lo resolvió la pegatina (si no, continuidad)
    mantenida: bool = False  # se devolvió la pose anterior por falta de evidencia


def detectar_madera(img_rgb, cam: CamaraMesa, previa: PoseTabla | None = None, cfg: ConfigVision | None = None,
                    lectura: LecturaMadera | None = None) -> PoseTabla | None:
    """Pose de la madera clara en la mesa, o la anterior (`previa`) si no hay evidencia suficiente; None si no se ve
    y no había anterior.

    1. Mancha de color madera mayor dentro del tapete, llevada al plano de media altura de la madera; `minAreaRect` da
       el giro (módulo 180°).
    2. Con ese giro, el centro sale del par de bordes de cada eje (robusto a lo que tape o añada un objeto encima).
    3. Refinado con el borde madera/tapete por debajo del píxel (en lo azul que es cada píxel; en los lados cuyo canto
       ve la cámara, la arista de abajo) y ajuste robusto del rectángulo de 200 × 300. Si hay pose anterior, también se
       prueba a partir de ella y se queda la que más borde ve.
    4. Solo se acepta con buena evidencia: al menos `madera.bordes_min` puntos de borde, y `madera.bordes_min_salto` si
       la pose salta más de `madera.salto_mm` (mm o grados) respecto a la anterior. Si no, la anterior (la madera tapada
       por las manos o el brazo no se mueve).
    5. Giro de 180°: la pegatina de la esquina (+x, +y) decide; si no se ve, el más cercano al anterior (o a 0°).
    `lectura`: si se da, se rellena con el detalle."""
    cfg = cfg or config_por_defecto()
    lectura = lectura if lectura is not None else LecturaMadera()
    lectura.pose, lectura.bordes, lectura.pegatina, lectura.giro_por_pegatina, lectura.mantenida = \
        previa, 0, None, False, previa is not None

    hsv = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2HSV)
    alto, ancho = hsv.shape[:2]
    tapete = np.zeros((alto, ancho), np.uint8)
    cv2.fillPoly(tapete, [np.round(_poligono(cam, esquinas_tapete_mesa(3.0), Z_TAPETE)).astype(np.int32)], 255)
    madera = _mascara_madera(hsv, cfg) & tapete
    madera = cv2.morphologyEx(madera, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    contornos, _ = cv2.findContours(madera, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    z_medio = (Z_TAPETE + Z_CARA) / 2
    referencia = previa.giro if previa is not None else 0.0
    candidatas = []
    area_esperada = cv2.contourArea(np.round(_poligono(cam, _esquinas_tabla(*g.ALFOMBRILLA_CENTRO, 0.0), Z_CARA))
                                    .astype(np.float32))
    # Todas las manchas de madera de un tamaño razonable: un brazo que cruza la madera la parte en dos
    trozos = [k for k in contornos if cv2.contourArea(k) >= 0.03 * area_esperada]
    if trozos and sum(cv2.contourArea(k) for k in trozos) >= 0.25 * area_esperada:
        en_mesa = cam.a_plano(np.vstack([k.reshape(-1, 2) for k in trozos]).astype(float), z_medio)
        (_, _), (w, h), ang = cv2.minAreaRect(en_mesa.astype(np.float32))
        giro = ang if w <= h else ang + 90.0  # el lado corto (200) es el x de la madera
        giro = _giro_cercano(giro, referencia)
        ref_xy = None if previa is None else np.array([previa.x, previa.y])
        candidatas.append(np.array([*_posicion_por_bordes(en_mesa, giro, ref_xy), giro]))
        candidatas += [np.array([*c, giro]) for c in _candidatas_extremos(en_mesa, giro)]
    if previa is not None:
        candidatas.append(np.array([previa.x, previa.y, previa.giro]))
    if not candidatas:
        return previa
    escalar = _croma_azul(img_rgb)
    azul = cfg.mascara(hsv, "tapete") & tapete
    nivel_tapete = float(np.median(escalar[azul > 0])) if np.any(azul) else 80.0
    mejor = None
    for par0 in candidatas:
        par, n_ok = _soporte_y_refinado(escalar, nivel_tapete, cam, par0, cfg)
        if mejor is None or n_ok > mejor[1]:
            mejor = (par, n_ok)
    par, n_ok = mejor
    lectura.bordes = n_ok
    if n_ok < cfg["madera"]["bordes_min"]:
        return previa
    if previa is not None:
        salto = max(float(np.hypot(par[0] - previa.x, par[1] - previa.y)),
                    abs((_giro_cercano(par[2], previa.giro) - previa.giro + 180.0) % 360.0 - 180.0))
        if salto > cfg["madera"]["salto_mm"] and n_ok < cfg["madera"]["bordes_min_salto"]:
            return previa
    giro_peg, xy_peg = _giro_por_pegatina(hsv, cam, par, cfg)
    lectura.pegatina = xy_peg
    if giro_peg is not None:
        par[2] = giro_peg
        lectura.giro_por_pegatina = True
    else:
        par[2] = _giro_cercano(par[2], referencia)
    pose = PoseTabla(float(par[0]), float(par[1]), float(par[2]))
    lectura.pose, lectura.mantenida = pose, False
    return pose


# --- 3. taladro ---------------------------------------------------------------------------------------------------
def detectar_bola(img_rgb, cfg: ConfigVision | None = None) -> tuple[np.ndarray, float] | None:
    """Centro (u, v) y radio (px) de la bola naranja del taladro, o None."""
    cfg = cfg or config_por_defecto()
    hsv = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2HSV)
    naranja = cfg.mascara(hsv, "bola")
    area_bola = cfg["bola"]["area"]
    naranja = cv2.morphologyEx(naranja, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    contornos, _ = cv2.findContours(naranja, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    mejor = None
    for k in contornos:
        area = cv2.contourArea(k)
        if not area_bola[0] <= area <= area_bola[1]:
            continue
        (u, v), r = cv2.minEnclosingCircle(k)
        redondez = area / (np.pi * r * r)
        if redondez < 0.5:
            continue
        if mejor is None or area > mejor[0]:
            mejor = (area, np.array([u, v]), float(r))
    return None if mejor is None else (mejor[1], mejor[2])


class SeguidorTaladro:
    """Posición filtrada (mediana de 0,3 s), velocidad (recta en 0,3 s), quieto y en zona del marcador del taladro."""

    def __init__(self, ventana: float = VENTANA_TALADRO):
        self.ventana = ventana
        self.historia: deque = deque()
        self.quieto_desde: float | None = None

    def reiniciar(self) -> None:
        self.historia.clear()
        self.quieto_desde = None

    def actualizar(self, t: float, xy: np.ndarray | None, madera: PoseTabla | None) -> Taladro:
        if xy is None:
            self.reiniciar()
            return Taladro(visible=False)
        self.historia.append((t, np.asarray(xy, float)))
        while self.historia and t - self.historia[0][0] > self.ventana + 1e-6:
            self.historia.popleft()
        ts = np.array([h[0] for h in self.historia])
        ps = np.array([h[1] for h in self.historia])
        xy_f = np.median(ps, axis=0)
        velocidad = 0.0
        if len(ts) >= 2 and ts[-1] - ts[0] > 1e-6:
            tc = ts - ts.mean()
            v = (tc[:, None] * (ps - ps.mean(axis=0))).sum(axis=0) / (tc ** 2).sum()
            velocidad = float(np.linalg.norm(v))
        lleno = len(ts) >= 2 and ts[-1] - ts[0] >= self.ventana * 0.6
        tiembla = bool(np.max(np.linalg.norm(ps - xy_f, axis=1)) < QUIETO_RADIO)
        if (velocidad < VELOCIDAD_QUIETO or tiembla) and lleno:
            if self.quieto_desde is None:
                self.quieto_desde = float(ts[0])  # lleva quieto toda la ventana
        else:
            self.quieto_desde = None
        en_zona = madera is not None and madera.contiene(xy_f, margen=-MARGEN_ZONA)
        return Taladro(visible=True, xy=xy_f, velocidad=velocidad, quieto_desde=self.quieto_desde,
                       en_zona=bool(en_zona))


# --- 4. broca con la cámara de la muñeca --------------------------------------------------------------------------
@dataclass
class MedidaBroca:
    punta_cam: np.ndarray  # mm, marco de la cámara (OpenCV)
    eje_cam: np.ndarray  # dirección del eje de la broca hacia la punta (cámara)
    distancia_eje: float  # mm de la cámara al eje de la broca
    ancho_px: float  # ancho aparente medio
    uv_punta: np.ndarray
    punta: np.ndarray | None = None  # mm, mesa (si se dio la pose de la cámara)


def _abajo_en_imagen(K, R, uv, distancia=150.0) -> np.ndarray | None:
    """Dirección (unitaria, imagen) en la que se ve la vertical del mundo hacia abajo en el píxel uv."""
    if R is None:
        return None
    r = np.linalg.inv(K) @ np.array([uv[0], uv[1], 1.0])
    X = r / np.linalg.norm(r) * distancia
    Y = X + R @ np.array([0.0, 0.0, -10.0])
    a, b = K @ X, K @ Y
    d = b[:2] / b[2] - a[:2] / a[2]
    return d / (np.linalg.norm(d) or 1.0)


def _plano_de_recta(Kinv, p, d) -> np.ndarray:
    """Normal unitaria del plano que pasa por el centro de la cámara y la recta de la imagen (p, d)."""
    a = Kinv @ np.array([p[0], p[1], 1.0])
    b = Kinv @ np.array([p[0] + 50 * d[0], p[1] + 50 * d[1], 1.0])
    n = np.cross(a, b)
    return n / np.linalg.norm(n)


def _unir_colineales(segs: list, angulo: float = 3.0, separacion: float = 1.5) -> list:
    """Une los segmentos de Hough que están sobre la misma recta (el borde de la broca sale a trozos)."""
    segs = list(segs)
    unido = True
    while unido:
        unido = False
        for i in range(len(segs)):
            for j in range(i + 1, len(segs)):
                p1, q1, d1 = segs[i]
                p2, q2, d2 = segs[j]
                if abs(d1 @ d2) < np.cos(np.radians(angulo)):
                    continue
                n = np.array([-d1[1], d1[0]])
                if abs((p2 - p1) @ n) > separacion or abs((q2 - p1) @ n) > separacion:
                    continue
                a = [0.0, (q1 - p1) @ d1, (p2 - p1) @ d1, (q2 - p1) @ d1]
                lo, hi = min(a), max(a)
                segs[i] = (p1 + lo * d1, p1 + hi * d1, d1)
                del segs[j]
                unido = True
                break
            if unido:
                break
    return segs


def _candidatas_barra(img_rgb, abajo: np.ndarray | None, ancho_px=(6.0, 70.0), cfg: ConfigVision | None = None
                      ) -> list:
    """Barras rectas candidatas a broca: pares de segmentos de borde (Canny + Hough) casi paralelos, separados por un
    ancho plausible, con el interior gris (poca saturación) y, si se conoce, a lo largo de la vertical del mundo vista
    en la imagen. No depende del color del fondo. Devuelve [(c, e, w, a_lo, a_hi, solape)] con c un punto de la línea
    central, e su dirección (hacia la punta si se conoce `abajo`), w el ancho y [a_lo, a_hi] el tramo visto a lo largo
    de e (a_hi: el final del lado de la punta)."""
    br = (cfg or config_por_defecto())["broca"]
    hsv = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2HSV)
    bordes = (cv2.Canny(cv2.GaussianBlur(hsv[..., 2], (3, 3), 0), 25, 75)
              | cv2.Canny(cv2.GaussianBlur(hsv[..., 1], (3, 3), 0), 25, 75))  # gris sobre fondo del mismo brillo
    lineas = cv2.HoughLinesP(bordes, 1, np.pi / 360, threshold=25, minLineLength=25, maxLineGap=5)
    if lineas is None:
        return []
    segs = []
    for x1, y1, x2, y2 in lineas.reshape(-1, 4).astype(float):
        d = np.array([x2 - x1, y2 - y1])
        d /= np.linalg.norm(d)
        if abajo is not None:
            if abs(d @ abajo) < np.cos(np.radians(20)):
                continue
            if d @ abajo < 0:
                d = -d
        segs.append((np.array([x1, y1]), np.array([x2, y2]), d))
    segs = _unir_colineales(segs)
    sat, val = hsv[..., 1], hsv[..., 2]
    alto, ancho = sat.shape
    out = []
    for i in range(len(segs)):
        for j in range(i + 1, len(segs)):
            p1, q1, d1 = segs[i]
            p2, q2, d2 = segs[j]
            if d1 @ d2 < 0:
                d2 = -d2
            if d1 @ d2 < np.cos(np.radians(5)):
                continue
            e = d1 + d2
            e /= np.linalg.norm(e)
            n = np.array([-e[1], e[0]])
            c1, c2 = (p1 + q1) / 2, (p2 + q2) / 2
            w = abs((c2 - c1) @ n)
            if not ancho_px[0] <= w <= ancho_px[1]:
                continue
            c = (c1 + c2) / 2
            a1 = sorted([(p1 - c) @ e, (q1 - c) @ e])
            a2 = sorted([(p2 - c) @ e, (q2 - c) @ e])
            lo, hi = max(a1[0], a2[0]), min(a1[1], a2[1])
            if hi - lo < max(15.0, 0.6 * w):
                continue
            # interior gris: muestras en la línea central
            c_lin = c + n * (((c1 - c) @ n + (c2 - c) @ n) / 2)
            ss = np.linspace(lo, hi, 15)
            pts = c_lin[None, :] + ss[:, None] * e[None, :]
            u = np.clip(pts[:, 0].round().astype(int), 0, ancho - 1)
            v = np.clip(pts[:, 1].round().astype(int), 0, alto - 1)
            if np.median(sat[v, u]) > br["sat_max"] or not br["v_min"] <= np.median(val[v, u]) <= br["v_max"]:
                continue
            a_hi = min(a1[1], a2[1]) if abajo is not None else hi
            out.append((c_lin, e, w, lo, a_hi, hi - lo))
    out.sort(key=lambda x: -x[5])
    return out


def mascara_robot(img_rgb, cfg: ConfigVision | None = None) -> np.ndarray:
    """Lo que la cámara de la muñeca ve del propio robot (las mordazas, amarillas en la simulación y en nuestro brazo),
    algo engordado. Si la punta de la broca acaba ahí, está tapada y su final no es la punta."""
    hsv = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2HSV)
    m = (cfg or config_por_defecto()).mascara(hsv, "robot")
    return cv2.dilate(m, np.ones((7, 7), np.uint8))


def medir_broca(img_rgb, K: np.ndarray, R: np.ndarray | None = None, t: np.ndarray | None = None,
                aprox_mesa: np.ndarray | None = None, radio_busqueda: float = 40.0,
                mascara_propia: np.ndarray | None = None, cfg: ConfigVision | None = None) -> MedidaBroca | None:
    """Punta de la broca vista de cerca por la cámara de la muñeca, o None si no se ve.

    - Candidatas: pares de bordes rectos casi paralelos (Canny en brillo y saturación + Hough) con el interior gris
      y, si se da la pose (R, t) de la cámara en la mesa, a lo largo de la vertical del mundo vista en la imagen.
    - Los dos bordes, refinados por debajo del píxel (salto más fuerte en brillo y saturación), son rectas: cada una
      con el centro de la cámara define un plano tangente al cilindro de la broca. El ángulo φ entre esos planos da
      la distancia al eje, ρ = r / sen(φ/2): es medir el ancho aparente de la broca de 8 mm con todo el tramo visto.
      Su corte da la dirección del eje (con el taladro algo inclinado también); si se aparta más de
      `INCLINACION_MAX` de la vertical, se usa la vertical.
    - La punta es el final de la barra (donde la línea central deja de tener el color de la broca). Su rayo corta el
      eje a ρ / sen(γ) de la cámara (γ: ángulo entre el rayo y el eje).
    - `aprox_mesa`: dónde la ve la cámara de arriba (x, y): se descartan las candidatas a más de `radio_busqueda`.
    - `mascara_propia`: lo que la cámara ve del robot (por defecto, `mascara_robot`); si la punta acaba ahí, está
      tapada y no se da."""
    Kinv = np.linalg.inv(K)
    propia = mascara_robot(img_rgb, cfg) if mascara_propia is None else mascara_propia
    alto, ancho = propia.shape
    hsv = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2HSV)
    V = hsv[..., 2].astype(np.float32)
    centro_img = K[:2, 2]
    abajo = _abajo_en_imagen(K, R, centro_img)
    eje_vertical = None if R is None else R @ np.array([0.0, 0.0, -1.0])
    mejor = None
    for c, e, w, a_lo, a_hi, solape in _candidatas_barra(img_rgb, abajo, cfg=cfg)[:12]:
        medida = _medir_barra(V, hsv, Kinv, c, e, w, a_lo, a_hi, eje_vertical)
        if medida is None:
            continue
        mas_alla = medida.uv_punta + 4.0 * e
        u, v = int(round(mas_alla[0])), int(round(mas_alla[1]))
        if not (0 <= u < ancho and 0 <= v < alto) or propia[v, u]:
            continue  # la barra sigue tapada por el robot o fuera de la imagen: su final no es la punta
        if R is not None and t is not None:
            medida.punta = R.T @ (medida.punta_cam - t)
            if aprox_mesa is not None and np.linalg.norm(medida.punta[:2] - np.asarray(aprox_mesa)[:2]) > radio_busqueda:
                continue
        coste = -solape
        if aprox_mesa is not None and medida.punta is not None:
            coste = float(np.linalg.norm(medida.punta[:2] - np.asarray(aprox_mesa)[:2]))
        if mejor is None or coste < mejor[0]:
            mejor = (coste, medida)
    return None if mejor is None else mejor[1]


def _distancia_color(hsv: np.ndarray, c, e, a_lo, a_hi) -> np.ndarray:
    """Cuánto se aparta cada píxel del gris de la broca (el de la línea central en [a_lo, a_hi]): más saturado, o mucho
    más oscuro o más claro. Una sombra sobre la broca (hasta la mitad de brillo) no cuenta. 0 = como la broca."""
    ss = np.arange(a_lo, a_hi, 1.0)
    pts = c[None, :] + ss[:, None] * e[None, :]
    u = np.clip(pts[:, 0].round().astype(int), 0, hsv.shape[1] - 1)
    v = np.clip(pts[:, 1].round().astype(int), 0, hsv.shape[0] - 1)
    s_ref = float(np.median(hsv[v, u, 1]))
    v_ref = float(np.median(hsv[v, u, 2]))
    S = hsv[..., 1].astype(np.float32)
    V = hsv[..., 2].astype(np.float32)
    return (2.0 * np.maximum(S - s_ref - 8.0, 0.0) + 2.0 * np.maximum(0.5 * v_ref - V, 0.0)
            + 2.0 * np.maximum(V - 1.6 * v_ref, 0.0)).astype(np.float32)


def _extender_barra(D: np.ndarray, c, e, w, a_lo, a_hi, maximo: float = 500.0, umbral: float = 20.0
                    ) -> tuple[float, float]:
    """Alarga el tramo [a_lo, a_hi] de la barra a lo largo de e mientras su línea central siga teniendo el color de
    la broca (`D`, de `_distancia_color`, menor que `umbral`). Los segmentos de Hough salen cortados a menudo y el
    fondo puede tener el mismo brillo: la saturación los separa."""
    perp = np.array([-e[1], e[0]])

    def vale(a):
        d = _perfiles(D, (c + a * e)[None, :], perp[None, :], np.array([0.0]))[0, 0]
        return bool(np.isfinite(d) and d < umbral)

    limites = []
    for paso, a0 in ((1.0, a_hi), (-1.0, a_lo)):
        a, fallos, ultimo = a0, 0, a0
        while fallos < 4 and abs(a - a0) < maximo:
            if vale(a):
                ultimo, fallos = a, 0
            else:
                fallos += 1
            a += paso
        limites.append(ultimo)
    return limites[1], limites[0] + 0.5


def _bordes_barra(canales, c, e, w, a_ini, a_fin, alcance):
    """Rectas de los dos bordes de la barra (refinados por gradiente en `canales`) entre a_ini y a_fin, o None."""
    perp = np.array([-e[1], e[0]])
    s = np.arange(a_ini, a_fin, 1.0)
    if len(s) < 12 or alcance < 0.5:  # barra de < 2 px de ancho: no se puede (y cv2.remap falla con el perfil vacío;
        return None                   # robustez del ciclo: una sesión de las 20 se cayó así)
    rectas = []
    for lado in (1.0, -1.0):
        p0 = c[None, :] + s[:, None] * e[None, :] + lado * w / 2 * perp[None, :]
        ref, ok = refinar_por_gradiente(canales, p0, np.tile(lado * perp, (len(p0), 1)), alcance=alcance,
                                        salto_min=15.0)
        if ok.sum() < 12:
            return None
        recta = ajustar_recta(ref[ok], tolerancia=0.5)
        if recta is None:
            return None
        rectas.append(recta)
    return rectas


def _interior_liso(V, c, e, w, a_ini, a_fin, pendiente_max: float = 12.0) -> bool:
    """¿El interior de la barra (sin 2,5 px junto a cada borde) no tiene saltos fuertes? (como una broca)."""
    perp = np.array([-e[1], e[0]])
    if w < 8:
        return True
    aa = np.linspace(a_ini, a_fin, 10)
    offs = np.arange(-w / 2 + 2.5, w / 2 - 2.5 + 1e-9, 0.5)
    pts = c[None, :] + aa[:, None] * e[None, :]
    prof = _perfiles(V, pts, np.tile(perp, (len(aa), 1)), offs)
    pendiente = np.nanmax(np.abs(np.diff(prof, axis=1)), axis=1) / 0.5
    return bool(np.mean(pendiente > pendiente_max) < 0.5)


def _medir_barra(V: np.ndarray, hsv: np.ndarray, Kinv: np.ndarray, c: np.ndarray, e: np.ndarray, w: float, a_lo: float,
                 a_hi: float, eje_vertical: np.ndarray | None) -> MedidaBroca | None:
    """Mide una barra candidata (línea central por c, dirección e hacia la punta, ancho w, tramo [a_lo, a_hi])."""
    VS = [V, hsv[..., 1].astype(np.float32)]  # brillo y saturación
    # 1. bordes en el tramo de Hough → línea central y ancho buenos
    rectas = _bordes_barra(VS, c, e, w, a_lo, a_hi, alcance=min(6.0, w / 2 - 0.5))
    if rectas is None:
        return None
    (p1, d1), (p2, d2) = rectas
    d = d1 if d1 @ e > 0 else -d1
    c_nuevo = (p1 + p2) / 2
    a_lo, a_hi = (c + a_lo * e - c_nuevo) @ d, (c + a_hi * e - c_nuevo) @ d
    c, e = c_nuevo, d
    w = float(abs((p2 - p1) @ np.array([-d1[1], d1[0]])))
    perp = np.array([-e[1], e[0]])
    # 2. hasta dónde llega la barra, y 3. bordes en todo el tramo
    D = _distancia_color(hsv, c, e, a_lo, a_hi)
    a_lo, a_hi = _extender_barra(D, c, e, w, a_lo, a_hi)
    a_ini = a_lo + 2.0
    a_fin = a_hi - max(3.0, 0.5 * w)
    if a_fin - a_ini < 15:
        return None
    rectas = _bordes_barra(VS, c, e, w, a_ini, a_fin, alcance=min(5.0, w / 2 - 0.5))
    if rectas is None:
        return None
    (p1, d1), (p2, d2) = rectas
    if not _interior_liso(V, (p1 + p2) / 2, d1 if d1 @ e > 0 else -d1, abs((p2 - p1) @ np.array([-d1[1], d1[0]])),
                          a_ini - ((p1 + p2) / 2 - c) @ e, a_fin - ((p1 + p2) / 2 - c) @ e):
        return None  # entre los dos bordes hay otro borde: no es una broca (dos objetos distintos)
    n1, n2 = _plano_de_recta(Kinv, p1, d1), _plano_de_recta(Kinv, p2, d2)
    medio_img = c + (a_ini + a_fin) / 2 * e
    medio = Kinv @ np.array([medio_img[0], medio_img[1], 1.0])
    if n1 @ medio > 0:
        n1 = -n1
    if n2 @ medio > 0:
        n2 = -n2
    phi = np.pi - np.arccos(np.clip(n1 @ n2, -1.0, 1.0))
    if not 1e-3 < phi < 1.0:
        return None
    rho = (DIAMETRO_BROCA / 2) / np.sin(phi / 2)
    # eje: el corte de los dos planos (sirve con el taladro algo inclinado); si sale lejos de la vertical (mal
    # condicionado), la vertical
    eje = np.cross(n1, n2)
    eje /= np.linalg.norm(eje)
    X = medio / np.linalg.norm(medio) * rho
    Y = X + eje
    if (Y[:2] / Y[2] - X[:2] / X[2]) @ (Kinv[:2, :2] @ e) < 0:
        eje = -eje
    if eje_vertical is not None:
        vertical = eje_vertical / np.linalg.norm(eje_vertical)
        if eje @ vertical < np.cos(np.radians(INCLINACION_MAX)):
            eje = vertical
    # línea central (entre las dos rectas) y punta: donde deja de tener el color de la broca
    d_med = d1 if d1 @ e > 0 else -d1
    p_med = (p1 + p2) / 2
    base = p_med + ((c + a_hi * e - p_med) @ d_med) * d_med
    w_med = float(abs((p2 - p1) @ np.array([-d1[1], d1[0]])))
    offs_b = np.array([-w_med / 5, 0.0, w_med / 5])
    pts_c = base[None, :] + offs_b[:, None] * perp[None, :]
    ref, ok = refinar_bordes(D, pts_c, np.tile(d_med, (3, 1)), alcance=6.0, contraste_min=15.0)
    if not ok.any():
        return None
    uv_punta = ref[ok].mean(axis=0)
    uv_punta = p_med + ((uv_punta - p_med) @ d_med) * d_med
    r = Kinv @ np.array([uv_punta[0], uv_punta[1], 1.0])
    r /= np.linalg.norm(r)
    sen_g = np.linalg.norm(np.cross(r, eje))
    if sen_g < 0.2:
        return None
    return MedidaBroca(r * rho / sen_g, eje, float(rho), w_med, uv_punta)


# --- 5. viruta ---------------------------------------------------------------------------------------------------
def contar_viruta(img_rgb, cam: CamaraMesa, madera: PoseTabla, agujeros_madera, radio: float = RADIO_VIRUTA,
                  cfg: ConfigVision | None = None) -> tuple[dict[int, int], dict[int, float]]:
    """Píxeles color serrín sobre la cara de la madera en un círculo de `radio` mm alrededor de cada agujero (marco de
    la madera). Devuelve ({índice: píxeles}, {índice: fracción del círculo visible})."""
    hsv = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2HSV)
    serrin = (cfg or config_por_defecto()).mascara(hsv, "serrin")
    alto, ancho = serrin.shape
    cara = np.zeros((alto, ancho), np.uint8)
    cv2.fillPoly(cara, [np.round(_poligono(cam, _esquinas_tabla(madera.x, madera.y, madera.giro), Z_CARA))
                        .astype(np.int32)], 255)
    pixeles, fracciones = {}, {}
    ang = np.linspace(0, 2 * np.pi, 48, endpoint=False)
    for i, p in enumerate(agujeros_madera):
        circ_madera = np.asarray(p, float)[None, :] + radio * np.column_stack([np.cos(ang), np.sin(ang)])
        poli = _poligono(cam, madera.a_mesa(circ_madera), Z_CARA)
        circ = np.zeros((alto, ancho), np.uint8)
        cv2.fillPoly(circ, [np.round(poli).astype(np.int32)], 255)
        circ &= cara
        total = int(np.count_nonzero(circ))
        n = int(np.count_nonzero(serrin & circ))
        pixeles[i] = n
        fracciones[i] = n / total if total else 0.0
    return pixeles, fracciones


# --- percepción completa -----------------------------------------------------------------------------------------
class Percepcion:
    """De imágenes {"top", "wrist"} + postura + tiempo a `Escena`.

    - `K_top`, `K_wrist`: intrínsecas (por defecto, las de la simulación a 640 × 480).
    - `cinematica`: `CinematicaRobot` (modelo del brazo y pose de la base) para la pose de la cámara de la muñeca; sin
      ella, la broca solo se estima desde arriba.
    - La cámara de arriba se calibra con la primera imagen (o con `calibrar`).
    - Los agujeros se apuntan solos al apoyar la broca (marco de la madera); `agujeros` los guarda.
    - `config`: umbrales de color (ruta a un YAML, dict o `ConfigVision`; por defecto `garbi/config_vision.yaml`).
    - `manos`: detector de manos (`garbi.manos.DetectorManos`) o su nombre: "color" (simulación, por defecto),
      "mediapipe" (robot real) o "auto"; None para no buscar manos.
    - Solución final: rellena `Escena.manos` y `Taladro.agarrado` (bola + una mano a < DIST_MANO_TALADRO) y marca en
      `Broca` el instante de clavado y de levantado (`clavada_desde`, `levantada_en`, `evento`).
    """

    def __init__(self, K_top: np.ndarray | None = None, K_wrist: np.ndarray | None = None,
                 cinematica: CinematicaRobot | None = None, resolucion=RESOLUCION, config=None, manos="color"):
        from garbi.manos import crear_detector

        self.cfg = cargar_config(config) if config is not None else config_por_defecto()
        self.detector_manos = crear_detector(manos, self.cfg) if isinstance(manos, str) else manos
        self.lectura_madera = LecturaMadera()
        self.manos: list[Mano] = []
        self._agarre_hasta: float | None = None
        self._clavada = False
        self._clavada_desde: float | None = None
        self._levantada_en: float | None = None
        self.K_top = intrinsecas(FOVY_TOP, resolucion) if K_top is None else K_top
        self.K_wrist = intrinsecas(FOVY_WRIST, resolucion) if K_wrist is None else K_wrist
        self.cin = cinematica
        self.cam: CamaraMesa | None = None
        self.madera: PoseTabla | None = None
        self.agujeros: list[np.ndarray] = []
        self.seguidor = SeguidorTaladro()
        self.apoyada = False
        self._apoyo_desde: float | None = None
        self.fraccion_viruta: dict[int, float] = {}
        self.ultima_broca: MedidaBroca | None = None
        self._bola_uv: np.ndarray | None = None
        self._xy_apoyo: np.ndarray | None = None
        self._xy_bola: np.ndarray | None = None  # marcador en el plano de la bola apoyada, sin filtrar
        self._radio_bola: float | None = None
        self._alturas: deque = deque()  # (t, altura de la punta por el radio de la bola, sin corregir)
        self._desvio_altura = DESVIO_ALTURA_INICIAL  # marcador (arriba) cuando se apoyó la broca
        self.desvio_bola_px = np.nan  # de la última comprobación de coherencia
        self._previa_muneca: tuple[float, np.ndarray] | None = None
        self.sin_confirmar = 0  # medidas de la muñeca sin otra parecida justo antes
        self.incoherentes = 0  # medidas de la muñeca descartadas por no cuadrar con la bola vista desde arriba
        self.desfase: np.ndarray | None = None  # punta − bola en planta (taladro inclinado); None: no se sabe
        self.lejanas = 0  # medidas de la muñeca descartadas por estar a más de DISTANCIA_MUNECA_MAX
        self.apoyos_arriba = 0  # clavadas dadas solo desde arriba (`_apoyo_por_arriba`)
        self._h_arriba: deque = deque()  # (t, altura de la punta por el radio de la bola)
        self._ultimo_apoyo: float | None = None
        self._aire_muneca: float | None = None  # t de la última punta en el aire medida por la muñeca

    def calibrar(self, img_top) -> bool:
        self.cam = calibrar_camara_arriba(img_top, self.K_top, cfg=self.cfg)
        return self.cam is not None

    def agregar_agujero(self, p_mesa) -> int:
        """Apunta un agujero (x, y en la mesa) en el marco de la madera; devuelve su índice."""
        p = self.madera.a_tabla(np.asarray(p_mesa, float)[:2])
        for i, a in enumerate(self.agujeros):
            if np.linalg.norm(a - p) < DISTANCIA_AGUJERO_NUEVO:
                return i
        self.agujeros.append(p)
        return len(self.agujeros) - 1

    def leer(self, imagenes: dict, q=None, t: float = 0.0, agujeros=None) -> Escena:
        """`agujeros`: los agujeros (marco de la madera) cuya viruta se cuenta, p. ej. `Ciclo.agujeros`, para que los
        índices de `Escena.viruta` sean los del ciclo; si no se dan, los que apunta la propia percepción al apoyar."""
        top = imagenes["top"]
        if self.cam is None and not self.calibrar(top):
            raise RuntimeError("No veo las 4 esquinas del tapete: no puedo calibrar la cámara de arriba")
        cam = self.cam
        madera = detectar_madera(top, cam, self.madera, self.cfg, self.lectura_madera)
        if madera is not None:
            self.madera = madera
        bola = detectar_bola(top, self.cfg)
        self._bola_uv = None if bola is None else bola[0]
        self._radio_bola = None if bola is None else bola[1]
        xy = None if bola is None else cam.a_plano(bola[0], Z_BOLA)[0]
        self._xy_bola = xy
        taladro = self.seguidor.actualizar(t, xy, self.madera)
        if not taladro.visible:
            self.desfase = None
        self.manos = [] if self.detector_manos is None else list(self.detector_manos.detectar(top, cam))
        self._agarrado(taladro, t)
        broca = self._broca(imagenes.get("wrist"), q, taladro, t)
        self._clavado(broca, t)
        viruta, self.fraccion_viruta = {}, {}
        lista = self.agujeros if agujeros is None else list(agujeros)
        if self.madera is not None and lista:
            viruta, self.fraccion_viruta = contar_viruta(top, cam, self.madera, lista, cfg=self.cfg)
        return Escena(t=t, madera=self.madera, taladro=taladro, broca=broca, viruta=viruta,
                      viruta_fraccion=dict(self.fraccion_viruta), manos=list(self.manos))

    def _agarrado(self, taladro: Taladro, t: float) -> None:
        """Regla del usuario: solo hay taladro si hay MANO + TALADRO juntos (una mano a < DIST_MANO_TALADRO del
        cuerpo del taladro). Ni la mano sola (sin bola) ni el taladro solo (sin mano cerca) cuentan."""
        from garbi.manos import ALTURA_AGARRE_MIN, distancia_mano_taladro

        if not taladro.visible:
            self._agarre_hasta = None
            return
        xy = taladro.xy + self._desfase()
        ds = [distancia_mano_taladro(m, self.cam, xy, Z_BOLA, Z_CARA + ALTURA_AGARRE_MIN) for m in self.manos]
        d = min(ds) if ds else None
        if d is not None and d < DIST_MANO_TALADRO:
            # la que sujeta el taladro: proyectada a la mesa queda lejos de él (está alta), así que el ciclo no la
            # puede reconocer por la distancia en planta; se marca aquí (si no, la tomaba por una mano libre cerca
            # de la boca y el acercamiento se apartaba al empezar)
            self.manos[int(np.argmin(ds))].del_taladro = True
        taladro.distancia_mano = d
        if d is not None and d < DIST_MANO_TALADRO:
            self._agarre_hasta = t + AGARRE_MANTENER
        taladro.agarrado = self._agarre_hasta is not None and t <= self._agarre_hasta + 1e-6

    def _clavado(self, broca: Broca, t: float) -> None:
        """Clavada = broca apoyada (con histéresis) con la punta sobre la madera; marca el instante en que se clava y
        en que se levanta, para que el ciclo y el grabador corten los episodios (fin de ACT = broca levantada)."""
        clavada = bool(broca.apoyada and broca.punta is not None and
                       (self.madera is None or self.madera.contiene(broca.punta[:2])))
        if clavada and not self._clavada:
            self._clavada_desde, broca.evento = t, "clavada"
        elif self._clavada and not clavada:
            self._levantada_en, self._clavada_desde, broca.evento = t, None, "levantada"
        self._clavada = clavada
        broca.clavada_desde = self._clavada_desde if clavada else None
        broca.levantada_en = self._levantada_en

    def _altura_por_bola(self, t: float) -> float | None:
        """Altura (mm) de la punta sobre la madera por el radio aparente de la bola (mediana de VENTANA_ALTURA s),
        corregida con lo que daba apoyada; aprende esa corrección mientras está apoyada."""
        if self._bola_uv is None or self._radio_bola is None or self.cam is None:
            self._alturas.clear()
            return None
        d = self.cam.K[0, 0] * g.RADIO_BOLA / self._radio_bola
        bola = self.cam.centro + self.cam.rayo(np.asarray(self._bola_uv)[None])[0] * d
        self._alturas.append((t, float(bola[2] - Z_BOLA)))
        while self._alturas and t - self._alturas[0][0] > VENTANA_ALTURA + 1e-6:
            self._alturas.popleft()
        h = float(np.median([a for _, a in self._alturas]))
        if self.apoyada:
            self._desvio_altura = h
            return 0.0
        return max(0.0, h - self._desvio_altura)

    def _coherente(self, medida: MedidaBroca, R: np.ndarray) -> bool:
        """¿La bola vista desde arriba está donde la pone la punta medida por la muñeca? (sin bola, no se puede
        comprobar: vale)"""
        if self._bola_uv is None or self.cam is None or medida.punta is None:
            return True
        arriba = -(R.T @ np.asarray(medida.eje_cam, float))  # eje de la broca en la mesa, de la punta hacia la bola
        arriba = arriba / (np.linalg.norm(arriba) or 1.0)
        if arriba[2] < 0:
            arriba = -arriba
        bola = medida.punta + arriba * g.ALTURA_BOLA_SOBRE_PUNTA
        # También con el taladro vertical y la punta no por debajo de la madera: con la broca vista de lado (lejos
        # del robot o a un costado) el eje medido se tuerce unos grados y, con 337 mm de brazo de palanca, la bola
        # caía a 16-45 px aunque la punta en planta estuviera a < 10 mm (integración, T6: en (310, 90) se descartaban
        # 11 de 15 medidas y la broca nunca se veía apoyada)
        punta = np.asarray(medida.punta, float).copy()
        punta[2] = max(punta[2], Z_CARA)
        vertical = punta + np.array([0.0, 0.0, g.ALTURA_BOLA_SOBRE_PUNTA])
        desvios = np.linalg.norm(self.cam.proyectar([bola, vertical]) - self._bola_uv, axis=1)
        self.desvio_bola_px = float(np.min(desvios))
        return self.desvio_bola_px <= COHERENCIA_BOLA_PX

    def _apoyo_por_arriba(self, t: float, h: float | None, taladro: Taladro) -> bool:
        """Clavada aproximada solo desde arriba (respaldo de la muñeca, F4): la bola ha bajado ≥ BAJADA_ARRIBA_MM en
        los últimos VENTANA_BAJADA s (o la broca estaba apoyada hace < VENTANA_BAJADA s: se ha deslizado), la altura
        estimada por su radio es ≤ APOYO_ARRIBA_MM y el taladro lleva T_APOYO_ARRIBA s quieto. No si la muñeca acaba
        de medir la punta en el aire."""
        if h is None:
            return False
        while self._h_arriba and t - self._h_arriba[0][0] > VENTANA_BAJADA + 1e-6:
            self._h_arriba.popleft()
        bajada = max((x for _, x in self._h_arriba), default=h) - h
        self._h_arriba.append((t, h))
        reciente = self._ultimo_apoyo is not None and t - self._ultimo_apoyo <= VENTANA_BAJADA
        quieto = taladro.quieto_desde is not None and t - taladro.quieto_desde >= T_APOYO_ARRIBA - 1e-6
        aire = self._aire_muneca is not None and t - self._aire_muneca <= T_APOYO_ARRIBA
        return h <= APOYO_ARRIBA_MM and quieto and not aire and (bajada >= BAJADA_ARRIBA_MM or reciente)

    def _broca(self, wrist, q, taladro: Taladro, t: float) -> Broca:
        if self.apoyada:
            self._ultimo_apoyo = t
        if not taladro.visible:
            self.apoyada, self._apoyo_desde = False, None
            self._h_arriba.clear()
        h_bola = self._altura_por_bola(t) if taladro.visible else None
        medida = None
        if wrist is not None and q is not None and self.cin is not None:
            R, tc = self.cin.pose_camara(q, "wrist")
            aprox = None if taladro.xy is None else taladro.xy + self._desfase()
            medida = medir_broca(wrist, self.K_wrist, R, tc, aprox, radio_busqueda=50.0)
            if medida is not None and medida.distancia_eje > DISTANCIA_MUNECA_MAX:
                self.lejanas += 1
                medida = None
            if medida is not None and not self._coherente(medida, R):
                self.incoherentes += 1
                medida = None
            if medida is not None:
                previa, self._previa_muneca = self._previa_muneca, (t, medida.punta.copy())
                if previa is None or t - previa[0] > CONFIRMAR_S + 1e-6 or \
                        np.linalg.norm(medida.punta[:2] - previa[1][:2]) > CONFIRMAR_MM:
                    self.sin_confirmar += 1
                    medida = None
            if medida is not None:
                self._aprender_desfase(medida.punta)
        self.ultima_broca = medida
        if medida is None:
            if not taladro.visible:
                return Broca()
            # Solo desde arriba: x, y del marcador; la altura no se mide. Sigue «apoyada» mientras el marcador no se
            # aparte de donde estaba al apoyar (al levantar el taladro, su proyección en el plano de la bola apoyada se
            # desplaza: ~0,5 mm por mm de subida con esta cámara).
            if self.apoyada and self._xy_bola is not None:  # el marcador sin filtrar: reacciona antes al levantar
                if self._xy_apoyo is None:
                    self._xy_apoyo = self._xy_bola.copy()
                elif np.linalg.norm(self._xy_bola - self._xy_apoyo) > SALE_ARRIBA_MM:
                    self.apoyada, self._apoyo_desde, self._xy_apoyo = False, None, None
            h = h_bola
            if not self.apoyada and self._apoyo_por_arriba(t, h, taladro):
                self.apoyada, self._apoyo_desde = True, t
                self._xy_apoyo = None if self._xy_bola is None else self._xy_bola.copy()
                self.apoyos_arriba += 1
            if self.apoyada or h is None:
                xy = taladro.xy + self._desfase()
                return Broca(punta=np.array([xy[0], xy[1], Z_CARA]), apoyada=self.apoyada, fuente="arriba",
                             eje=self._eje())
            xy = self.cam.a_plano(self._bola_uv, Z_BOLA + h)[0] + self._desfase()
            return Broca(punta=np.array([xy[0], xy[1], Z_CARA + h]), apoyada=False, fuente="arriba", eje=self._eje())
        altura = float(medida.punta[2] - Z_CARA)
        if altura > APOYO_SALE:
            self._aire_muneca = t
        if self.apoyada:
            if altura > APOYO_SALE:
                self.apoyada, self._apoyo_desde = False, None
        elif altura <= APOYO_ENTRA:
            if self._apoyo_desde is None:
                self._apoyo_desde = t
            if t - self._apoyo_desde >= APOYO_DURACION - 1e-6:
                self.apoyada = True
                self._xy_apoyo = None if self._xy_bola is None else self._xy_bola.copy()
                if self.madera is not None and self.madera.contiene(medida.punta[:2]):
                    self.agregar_agujero(self._en_planta(medida.punta, taladro, medida.distancia_eje)[:2])
        else:
            self._apoyo_desde = None
        punta = self._en_planta(medida.punta, taladro, medida.distancia_eje) if self.apoyada else medida.punta.copy()
        return Broca(punta=punta, apoyada=self.apoyada, fuente="muneca", eje=self._eje())

    def _desfase(self) -> np.ndarray:
        if self.desfase is None:
            return np.zeros(2)
        n = float(np.linalg.norm(self.desfase))
        return self.desfase * float(np.clip((n - DESFASE_MIN0) / (DESFASE_MIN - DESFASE_MIN0), 0.0, 1.0))

    def _eje(self) -> np.ndarray | None:
        """Eje de la broca (de la punta hacia la bola) por el desfase aprendido; None si no se sabe."""
        if self.desfase is None:
            return None
        e = -self._desfase() / g.ALTURA_BOLA_SOBRE_PUNTA
        return np.array([e[0], e[1], np.sqrt(max(0.0, 1.0 - float(e @ e)))])

    def _aprender_desfase(self, punta) -> None:
        """Desfase en planta entre la punta medida por la muñeca y la bola (proyectada a la altura que le toca)."""
        if self._bola_uv is None or self.cam is None:
            return
        bola = self.cam.a_plano(self._bola_uv, float(punta[2]) + g.ALTURA_BOLA_SOBRE_PUNTA)[0]
        d = np.asarray(punta, float)[:2] - bola
        if np.linalg.norm(d) > DESFASE_MAX + 5.0:
            return
        self.desfase = d if self.desfase is None else (1 - DESFASE_PESO) * self.desfase + DESFASE_PESO * d

    def _en_planta(self, punta, taladro: Taladro, distancia: float = MUNECA_CERCA) -> np.ndarray:
        """Broca apoyada: la punta en planta, media de la de la muñeca (a `distancia` mm de su cámara) y la de arriba
        (con el desfase del taladro inclinado) si cuadran (ver FUSION_MM y MUNECA_CERCA)."""
        punta = np.asarray(punta, float).copy()
        if taladro.xy is not None:
            arriba = taladro.xy + self._desfase()
            if np.linalg.norm(punta[:2] - arriba) < FUSION_MM:
                w = 0.5 * min(1.0, (MUNECA_CERCA / max(float(distancia), 1.0)) ** 2)
                punta[:2] = w * punta[:2] + (1.0 - w) * arriba
        return punta


# --- ayuda para la simulación y el ciclo: postura para mirar la broca de cerca ------------------------------------
def postura_mirar_broca(control, punta, distancia: float = 80.0, uv=(250.0, 120.0), bajada: float = 10.0,
                        q0=None):
    """Postura (grados de LeRobot) del montaje lateral en la que la cámara de la muñeca ve la punta `punta` (mm, mesa)
    a `distancia` mm, en el píxel `uv` (fuera de las mordazas, que tapan el centro y abajo de la imagen) y mirando
    `bajada` grados hacia abajo. `control`: `garbi.lateral.ControlLateral`. None si no la encuentra. `q0` (4
    articulaciones, rad): se prueba antes en caliente desde ahí (seguir la broca paso a paso sin cambiar de rama).

    Con las posturas de preapunto y acompañar de `garbi.lateral` la broca queda a ~220-250 mm de la cámara y, apoyada,
    tapada por las mordazas: para medirla de cerca hace falta esta postura (o una parecida)."""
    import mujoco

    M, d = control.M, control.d
    cid = M.camera("wrist").id
    K = intrinsecas(FOVY_WRIST)
    un, vn = (np.array(uv) - K[:2, 2]) / K[0, 0]
    P = np.asarray(punta, float)

    def residuo(q4):
        control._poner(q4)
        mujoco.mj_camlight(M, d)
        R = (d.cam_xmat[cid].reshape(3, 3) @ np.diag([1.0, -1.0, -1.0])).T
        pc = R @ (P - d.cam_xpos[cid] / 1e-3)
        return np.array([(pc[0] / pc[2] - un) * distancia, (pc[1] / pc[2] - vn) * distancia, pc[2] - distancia,
                         30.0 * (np.arcsin(-R[2, 2]) - np.radians(bajada))])

    mejor = None
    if q0 is not None:
        q, err = control._resolver(residuo, np.asarray(q0, float), iteraciones=30)
        if np.isfinite(err) and err < 1.0:
            mejor = q
    for semilla in ([] if mejor is not None else control.semillas):
        q, err = control._resolver(residuo, semilla)
        if np.isfinite(err) and err < 1.0:
            mejor = q
            break
    return None if mejor is None else control.a_lerobot(mejor)
