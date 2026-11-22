"""Cuerpo de Garbi (M1 y M6): el SO-101 real con LeRobot 0.7, o el mundo simulado, detrás del mismo contrato `Cuerpo`.

- `CuerpoReal`: `SO101Follower` (grados, `max_relative_target`), cámaras OpenCV `top` y `wrist` a 640 × 480 y 30 fps
  con exposición, balance de blancos y foco fijos, y la señal de la aspiradora por serie (`SenalAspiradora`).
- `CuerpoSim`: lo mismo sobre `MundoGarbi(montaje="lateral")`; cada `enviar` avanza un fotograma (1/30 s).

API de LeRobot 0.7 que se usa (comprobada en el código instalado):
- `lerobot.robots.so_follower.SO101FollowerConfig(port, id, cameras, max_relative_target, use_degrees,
  disable_torque_on_disconnect)`; `max_relative_target` tiene que ser `float` o `dict`: con un `int`,
  `ensure_safe_goal_position` lanza `TypeError`.
- `SO101Follower.send_action({"shoulder_pan.pos": ..., ...})` recorta el salto y devuelve lo que manda de verdad.
  Las 5 primeras articulaciones van en grados (`use_degrees=True`); la pinza va de 0 a 100.
- La postura se lee con `robot.bus.sync_read("Present_Position", num_retry=...)` (lo mismo que hace
  `get_observation`, sin leer además las cámaras); las imágenes con `camara.read_latest()` (RGB, sin bloquear).
- `OpenCVCameraConfig(index_or_path, fps, width, height, color_mode, rotation, warmup_s, fourcc, backend)` **no**
  tiene exposición, balance de blancos ni foco: se fijan aparte, después de conectar (`fijar_ajustes_camara`):
  en Linux con `v4l2-ctl` sobre `/dev/videoN`, en Windows con `cv2.CAP_PROP_*` sobre `camara.videocapture`
  (y el backend DirectShow, que es el que respeta esas propiedades).
"""
from __future__ import annotations

import atexit
import logging
import math
import platform
import re
import subprocess
import threading
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from garbi.tipos import ARTICULACIONES, forzar_montaje

log = logging.getLogger(__name__)

CAMARAS = ("top", "wrist")
ANCHO, ALTO = 640, 480
FPS_CAMARA = 30
MAX_SALTO = 10.0  # grados por envío (a 30 Hz, ~300 °/s como tope de seguridad; la guardia fina de 75 °/s es del ciclo)
PERIODO_SENAL = 0.2  # s entre latidos de la aspiradora
BAUDIOS_ASPIRADORA = 115200

CLAVES_ACCION = tuple(f"{n}.pos" for n in ARTICULACIONES)


# --- conversión entre el vector de Garbi y las claves de LeRobot ---------------------------------------------------
def accion_lerobot(q: np.ndarray) -> dict[str, float]:
    """6 articulaciones (orden de `ARTICULACIONES`) → acción de LeRobot `{"shoulder_pan.pos": ..., ...}`."""
    q = np.asarray(q, dtype=float).reshape(-1)
    if q.shape != (len(ARTICULACIONES),):
        raise ValueError(f"se esperaban {len(ARTICULACIONES)} articulaciones, llegan {q.shape}")
    return {clave: float(v) for clave, v in zip(CLAVES_ACCION, q)}


def q_desde_lerobot(datos: dict) -> np.ndarray:
    """Observación o acción de LeRobot (`"shoulder_pan.pos"` o `"shoulder_pan"`) → vector de 6 en el orden de Garbi."""
    q = np.empty(len(ARTICULACIONES))
    for i, n in enumerate(ARTICULACIONES):
        q[i] = float(datos[f"{n}.pos"] if f"{n}.pos" in datos else datos[n])
    return q


def limitar_salto(q: np.ndarray, q_actual: np.ndarray, max_salto: float | None) -> np.ndarray:
    """Lo mismo que `ensure_safe_goal_position` de LeRobot: cada articulación se mueve como mucho `max_salto`."""
    q = np.asarray(q, dtype=float)
    if max_salto is None:
        return q.copy()
    q_actual = np.asarray(q_actual, dtype=float)
    return q_actual + np.clip(q - q_actual, -max_salto, max_salto)


def _a_640x480(img: np.ndarray, resolucion: tuple[int, int] | None = None) -> np.ndarray:
    """A 640 × 480 (o a `resolucion` = (ancho, alto), p. ej. la cenital del equipo a 640 × 360)."""
    ancho, alto = resolucion or (ANCHO, ALTO)
    if img.shape[:2] == (alto, ancho):
        return img
    import cv2

    return cv2.resize(img, (ancho, alto), interpolation=cv2.INTER_AREA)


# --- ajustes fijos de las cámaras ----------------------------------------------------------------------------------
@dataclass
class AjustesCamara:
    """Exposición, balance de blancos y foco fijos (M1). Valores de partida para una C920 con el flexo LED: se
    ajustan en el sitio con `v4l2-ctl -d /dev/videoN --list-ctrls` y se apuntan aquí. `None` = no tocar ese ajuste
    (pero el automático se apaga igual)."""
    exposicion_ms: float | None = 15.6  # 156 en unidades de v4l2 (100 µs); en Windows, 2^-6 s
    balance_k: int | None = 4000  # temperatura de color (K)
    foco: int | None = 0  # focus_absolute (0 = infinito en la C920; la de arriba está a ~0,9 m)


# Nombres de los controles de v4l2: los kernels nuevos (≥ 5.x) y los viejos los llaman distinto.
_V4L2_EXPOSICION_AUTO = (("auto_exposure", "1"), ("exposure_auto", "1"))  # 1 = manual
_V4L2_EXPOSICION = ("exposure_time_absolute", "exposure_absolute")
_V4L2_BALANCE_AUTO = (("white_balance_automatic", "0"), ("white_balance_temperature_auto", "0"))
_V4L2_BALANCE = ("white_balance_temperature",)
_V4L2_FOCO_AUTO = (("focus_automatic_continuous", "0"), ("focus_auto", "0"))
_V4L2_FOCO = ("focus_absolute",)


def controles_v4l2(lista: str) -> set[str]:
    """Nombres de los controles que salen en `v4l2-ctl --list-ctrls`."""
    return set(re.findall(r"^\s*([a-z_0-9]+)\s+0x[0-9a-f]+", lista, flags=re.MULTILINE))


def ordenes_v4l2(disponibles: set[str], ajustes: AjustesCamara) -> list[str]:
    """`ctrl=valor` para `v4l2-ctl --set-ctrl`, en orden: primero se apaga cada automático y después se pone el valor
    (con el automático encendido, el valor manual no se acepta)."""
    def primero(opciones):
        return next((o for o in opciones if (o[0] if isinstance(o, tuple) else o) in disponibles), None)

    ordenes = []
    for auto, manual, valor in (
        (_V4L2_EXPOSICION_AUTO, _V4L2_EXPOSICION,
         None if ajustes.exposicion_ms is None else round(ajustes.exposicion_ms * 10)),
        (_V4L2_BALANCE_AUTO, _V4L2_BALANCE, ajustes.balance_k),
        (_V4L2_FOCO_AUTO, _V4L2_FOCO, ajustes.foco),
    ):
        a = primero(auto)
        if a is not None:
            ordenes.append(f"{a[0]}={a[1]}")
        m = primero(manual)
        if m is not None and valor is not None:
            ordenes.append(f"{m}={int(valor)}")
    return ordenes


def dispositivo_linux(index_or_path) -> str:
    return str(index_or_path) if isinstance(index_or_path, (str, Path)) else f"/dev/video{int(index_or_path)}"


def fijar_ajustes_linux(dispositivo: str, ajustes: AjustesCamara, ejecutar=subprocess.run) -> list[str]:
    """Fija los ajustes con `v4l2-ctl` (paquete `v4l-utils`). Devuelve las órdenes aplicadas."""
    try:
        lista = ejecutar(["v4l2-ctl", "-d", dispositivo, "--list-ctrls"], capture_output=True, text=True,
                         check=True).stdout
    except (FileNotFoundError, subprocess.CalledProcessError) as e:
        log.warning("no puedo fijar los ajustes de %s con v4l2-ctl (%s): ¿está instalado v4l-utils?", dispositivo, e)
        return []
    ordenes = ordenes_v4l2(controles_v4l2(lista), ajustes)
    for orden in ordenes:  # de una en una: así el automático ya está apagado cuando llega el valor
        r = ejecutar(["v4l2-ctl", "-d", dispositivo, f"--set-ctrl={orden}"], capture_output=True, text=True)
        if getattr(r, "returncode", 0) != 0:
            log.warning("v4l2-ctl %s %s: %s", dispositivo, orden, getattr(r, "stderr", ""))
    return ordenes


def fijar_ajustes_cv2(captura, ajustes: AjustesCamara) -> dict[str, bool]:
    """Fija los ajustes con `cv2.CAP_PROP_*` (Windows, DirectShow). Devuelve qué propiedad aceptó la cámara.
    Ojo: con DirectShow la exposición va en log2(segundos) (−6 ≈ 15,6 ms) y el modo manual de la exposición
    automática es 0,25 (convenio de OpenCV); compruébalo en el sitio con `captura.get(...)`."""
    import cv2

    hechos = {"auto_exposure": captura.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)}
    if ajustes.exposicion_ms is not None:
        hechos["exposure"] = captura.set(cv2.CAP_PROP_EXPOSURE, float(round(math.log2(ajustes.exposicion_ms / 1000))))
    hechos["auto_wb"] = captura.set(cv2.CAP_PROP_AUTO_WB, 0)
    if ajustes.balance_k is not None:
        hechos["wb_temperature"] = captura.set(cv2.CAP_PROP_WB_TEMPERATURE, float(ajustes.balance_k))
    hechos["autofocus"] = captura.set(cv2.CAP_PROP_AUTOFOCUS, 0)
    if ajustes.foco is not None:
        hechos["focus"] = captura.set(cv2.CAP_PROP_FOCUS, float(ajustes.foco))
    for nombre, ok in hechos.items():
        if not ok:
            log.warning("la cámara no acepta %s", nombre)
    return hechos


def fijar_ajustes_camara(camara, ajustes: AjustesCamara, sistema: str | None = None, ejecutar=subprocess.run):
    """Ajustes fijos de una `OpenCVCamera` de LeRobot ya conectada (después de `robot.connect()`, porque OpenCV
    abre el dispositivo y pone resolución y fps al conectar)."""
    sistema = sistema or platform.system()
    if sistema == "Linux":
        return fijar_ajustes_linux(dispositivo_linux(camara.index_or_path), ajustes, ejecutar)
    return fijar_ajustes_cv2(camara.videocapture, ajustes)


def config_camaras(camaras: dict[str, int | str | Path], sistema: str | None = None,
                   resoluciones: dict[str, tuple[int, int]] | None = None) -> dict:
    """`{"top": 0, "wrist": "/dev/video2"}` → `OpenCVCameraConfig` a 640 × 480 (o `resoluciones[nombre]`), 30 fps."""
    from lerobot.cameras.opencv import OpenCVCameraConfig
    from lerobot.cameras.configs import Cv2Backends

    sistema = sistema or platform.system()
    backend = Cv2Backends.DSHOW if sistema == "Windows" else Cv2Backends.ANY
    configs = {}
    for nombre, fuente in camaras.items():
        if isinstance(fuente, str) and fuente.isdigit():
            fuente = int(fuente)
        elif isinstance(fuente, str):
            fuente = Path(fuente)
        ancho, alto = (resoluciones or {}).get(nombre) or (ANCHO, ALTO)
        configs[nombre] = OpenCVCameraConfig(index_or_path=fuente, fps=FPS_CAMARA, width=int(ancho), height=int(alto),
                                             backend=backend)
    return configs


def abrir_camaras(camaras: dict[str, int | str | Path], ajustes: AjustesCamara | None = None,
                  fabrica=None) -> dict:
    """Cámaras sueltas (sin robot) para las herramientas del sitio: `OpenCVCamera` de LeRobot a 640 × 480 y 30 fps,
    conectadas y con los ajustes fijos. Cerrar con `cerrar_camaras`. `fabrica(config)`: para los tests."""
    if fabrica is None:
        from lerobot.cameras.opencv import OpenCVCamera as fabrica
    ajustes = ajustes or AjustesCamara()
    abiertas = {}
    try:
        for nombre, cfg in config_camaras(camaras).items():
            cam = fabrica(cfg)
            cam.connect()
            abiertas[nombre] = cam
            fijar_ajustes_camara(cam, ajustes)
    except Exception:
        cerrar_camaras(abiertas)
        raise
    return abiertas


def cerrar_camaras(camaras: dict) -> None:
    for cam in camaras.values():
        try:
            cam.disconnect()
        except Exception as e:
            log.warning("al cerrar la cámara %s: %s", cam, e)


# --- calibración del sitio (carpeta calib/) ------------------------------------------------------------------------
# calib/top.yaml y calib/wrist.yaml: intrínsecas (tablero de ajedrez); calib/robot.yaml: pose de la base del robot en
# la mesa (anillo verde, M2 paso 3). Las escribe herramientas/garbi_calibrar.py.
CARPETA_CALIBRACION = Path("calib")


def guardar_intrinsecas(ruta, K, dist, resolucion=(ANCHO, ALTO), error_rms: float | None = None,
                        fotos: int | None = None) -> Path:
    import yaml

    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    datos = {"K": np.asarray(K, float).round(6).tolist(), "dist": np.asarray(dist, float).reshape(-1).round(8).tolist(),
             "resolucion": [int(resolucion[0]), int(resolucion[1])],
             "error_rms_px": None if error_rms is None else round(float(error_rms), 4), "fotos": fotos}
    ruta.write_text("# Intrínsecas (cv2.calibrateCamera). K en píxeles a la resolución indicada (ancho, alto).\n"
                    + yaml.safe_dump(datos, sort_keys=False), encoding="utf-8")
    return ruta


def cargar_intrinsecas(ruta) -> tuple[np.ndarray, np.ndarray]:
    """(K 3×3, dist) de un yaml de `guardar_intrinsecas`."""
    import yaml

    datos = yaml.safe_load(Path(ruta).read_text(encoding="utf-8"))
    return np.array(datos["K"], float).reshape(3, 3), np.array(datos.get("dist") or [0.0] * 5, float)


def guardar_base(ruta, base, residuos=(), errores=()) -> Path:
    """Pose de la base del robot en la mesa (`garbi.calibracion.PoseBase`) con los residuos y errores en mm."""
    import yaml

    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    errores = [None if not np.isfinite(e) else round(float(e), 2) for e in np.asarray(errores, float).reshape(-1)]
    datos = {"x": round(float(base.x), 3), "y": round(float(base.y), 3), "giro": round(float(base.giro), 4),
             "residuos_mm": [round(float(r), 2) for r in np.asarray(residuos, float).reshape(-1)],
             "errores_comprobacion_mm": errores}
    ruta.write_text("# Base del robot en la mesa: p_mesa = Rz(giro) · p_robot + (x, y) (mm, grados).\n"
                    + yaml.safe_dump(datos, sort_keys=False), encoding="utf-8")
    return ruta


def cargar_base(ruta):
    import yaml

    from garbi.calibracion import PoseBase

    datos = yaml.safe_load(Path(ruta).read_text(encoding="utf-8"))
    return PoseBase(float(datos["x"]), float(datos["y"]), float(datos["giro"]))


@dataclass
class CalibracionSitio:
    """Lo que hay en la carpeta de calibración: intrínsecas por cámara ({"top": (K, dist)}) y la base del robot."""
    intrinsecas: dict
    base: object | None = None

    def K(self, camara: str) -> np.ndarray | None:
        return self.intrinsecas[camara][0] if camara in self.intrinsecas else None


def cargar_calibracion(carpeta=CARPETA_CALIBRACION) -> CalibracionSitio:
    """Lee lo que exista en la carpeta (nada es obligatorio: sin archivos, la percepción usa sus valores nominales)."""
    carpeta = Path(carpeta)
    intr = {cam: cargar_intrinsecas(carpeta / f"{cam}.yaml") for cam in CAMARAS if (carpeta / f"{cam}.yaml").exists()}
    base = cargar_base(carpeta / "robot.yaml") if (carpeta / "robot.yaml").exists() else None
    return CalibracionSitio(intr, base)


class CorrectorDistorsion:
    """Quita la distorsión de la lente con las intrínsecas de `calib/`; la imagen corregida sigue teniendo la misma K
    (así la percepción usa K tal cual). Mapas precalculados: un `cv2.remap` por imagen (~1-2 ms a 640 × 480)."""

    def __init__(self, K, dist, resolucion=(ANCHO, ALTO)):
        import cv2

        self.K = np.asarray(K, float)
        self.dist = np.asarray(dist, float)
        self.resolucion = tuple(resolucion)
        self.mapas = cv2.initUndistortRectifyMap(self.K, self.dist, None, self.K, self.resolucion, cv2.CV_16SC2)

    def __call__(self, img: np.ndarray) -> np.ndarray:
        import cv2

        if not np.any(self.dist) or img.shape[1::-1] != self.resolucion:
            return img
        return cv2.remap(img, self.mapas[0], self.mapas[1], cv2.INTER_LINEAR)


# --- señal de la aspiradora (M6) -----------------------------------------------------------------------------------
class SenalAspiradora:
    """Manda por serie la línea `1` (aspirar) o `0` cada `periodo` s; sirve de latido: si la aspiradora no oye nada en
    1 s, se apaga sola (lo hace el usuario en su lado). Un cambio se manda en el momento, sin esperar al latido.

    Al cerrar (o al salir el programa, con `atexit`) manda `0`. Si el proceso muere de golpe (kill -9, corte), el
    latido se para y la aspiradora se apaga por su cuenta al segundo.

    `serie`: un objeto con `write(bytes)` y `close()` (por defecto, `serial.Serial(puerto, 115200)`)."""

    def __init__(self, puerto: str | None = None, serie=None, periodo: float = PERIODO_SENAL,
                 baudios: int = BAUDIOS_ASPIRADORA):
        if serie is None:
            import serial

            serie = serial.Serial(puerto, baudrate=baudios, timeout=0, write_timeout=0.1)
        self.serie = serie
        self.periodo = periodo
        self._encendida = False
        self._cambio = threading.Event()
        self._parar = threading.Event()
        self._candado = threading.Lock()
        self._cerrada = False
        self._hilo = threading.Thread(target=self._latir, name="senal-aspiradora", daemon=True)
        self._hilo.start()
        atexit.register(self.cerrar)

    @property
    def encendida(self) -> bool:
        return self._encendida

    def poner(self, encendida: bool) -> None:
        encendida = bool(encendida)
        if encendida != self._encendida:
            self._encendida = encendida
            self._cambio.set()

    def _escribir(self, encendida: bool) -> None:
        with self._candado:
            try:
                self.serie.write(b"1\n" if encendida else b"0\n")
            except Exception as e:  # un fallo de escritura no puede tumbar el bucle de control
                log.warning("no puedo escribir en la aspiradora: %s", e)

    def _latir(self) -> None:
        while not self._parar.is_set():
            self._escribir(self._encendida)
            self._cambio.wait(self.periodo)  # despierta antes si cambia la orden
            self._cambio.clear()

    def cerrar(self) -> None:
        """Para el latido, manda `0` y cierra el puerto. Se puede llamar varias veces."""
        if self._cerrada:
            return
        self._cerrada = True
        self._encendida = False
        self._parar.set()
        self._cambio.set()
        if self._hilo is not threading.current_thread():
            self._hilo.join(timeout=1.0)
        self._escribir(False)
        try:
            self.serie.close()
        except Exception:
            pass
        atexit.unregister(self.cerrar)


# --- robot real ----------------------------------------------------------------------------------------------------
class CuerpoReal:
    """SO-101 real (cumple `garbi.tipos.Cuerpo`).

        cuerpo = CuerpoReal("/dev/ttyACM0", "garbi", {"top": 0, "wrist": 2}, puerto_aspiradora="/dev/ttyUSB0")
        cuerpo.conectar()
        ...
        cuerpo.cerrar()   # aspiradora a 0 y brazo quieto donde está

    `quedarse_con_par=True`: al cerrar, el brazo se queda rígido en su sitio (si se quitara el par, caería sobre la
    mesa, quizá junto a la mano o el taladro). Para soltarlo, apagar los servos.
    `fabrica_robot` y `senal` son para los tests (dobles sin hardware)."""

    def __init__(self, puerto: str, id: str = "garbi", camaras: dict | None = None,
                 puerto_aspiradora: str | None = None, max_relative_target: float | None = MAX_SALTO,
                 ajustes: AjustesCamara | None = None, quedarse_con_par: bool = True, fabrica_robot=None,
                 senal: SenalAspiradora | None = None, intrinsecas: dict | None = None,
                 use_degrees: bool = True, resoluciones: dict[str, tuple[int, int]] | None = None):
        self.puerto = puerto
        self.id = id
        self.camaras = dict(camaras if camaras is not None else {"top": 0, "wrist": 1})
        self.puerto_aspiradora = puerto_aspiradora
        self.max_relative_target = None if max_relative_target is None else float(max_relative_target)
        self.ajustes = ajustes or AjustesCamara()
        self.quedarse_con_par = quedarse_con_par
        self._fabrica_robot = fabrica_robot
        self.senal = senal
        # use_degrees=False: unidades normalizadas de LeRobot (-100..100), como el dataset del equipo
        self.use_degrees = bool(use_degrees)
        self.resoluciones = {k: tuple(int(x) for x in v) for k, v in (resoluciones or {}).items() if v}
        self.robot = None
        self.ultima_enviada: np.ndarray | None = None
        self._aspirando = False
        # {"top": (K, dist)} de calib/: si se dan, `imagenes` quita la distorsión de la lente
        self.correctores = {cam: CorrectorDistorsion(K, d) for cam, (K, d) in (intrinsecas or {}).items()}

    def config(self):
        from lerobot.robots.so_follower import SO101FollowerConfig

        return SO101FollowerConfig(port=self.puerto, id=self.id, cameras=config_camaras(self.camaras, resoluciones=self.resoluciones),
                                   max_relative_target=self.max_relative_target, use_degrees=self.use_degrees,
                                   disable_torque_on_disconnect=not self.quedarse_con_par)

    def conectar(self, calibrar: bool = True) -> CuerpoReal:
        if self._fabrica_robot is None:
            from lerobot.robots.so_follower import SO101Follower

            self.robot = SO101Follower(self.config())
        else:
            self.robot = self._fabrica_robot(self)
        self.robot.connect(calibrate=calibrar)
        for nombre, cam in getattr(self.robot, "cameras", {}).items():
            fijar_ajustes_camara(cam, self.ajustes)
        if self.senal is None and self.puerto_aspiradora:
            self.senal = SenalAspiradora(self.puerto_aspiradora)
        return self

    def __enter__(self):
        return self.conectar()

    def __exit__(self, *exc):
        self.cerrar()

    # --- contrato Cuerpo ---------------------------------------------------------------------------------------
    def q(self) -> np.ndarray:
        leido = self.robot.bus.sync_read("Present_Position", num_retry=getattr(self.robot.config, "num_read_retries", 2))
        return q_desde_lerobot(leido)

    def enviar(self, q: np.ndarray) -> None:
        """Muñeca fija y pinza cerrada siempre; LeRobot recorta el salto con `max_relative_target`."""
        enviada = self.robot.send_action(accion_lerobot(forzar_montaje(q)))
        self.ultima_enviada = q_desde_lerobot(enviada)

    def aspirar(self, encendida: bool) -> None:
        self._aspirando = bool(encendida)
        if self.senal is not None:
            self.senal.poner(encendida)

    def imagenes(self) -> dict[str, np.ndarray]:
        imgs = {nombre: _a_640x480(cam.read_latest(), self.resoluciones.get(nombre)) for nombre, cam in self.robot.cameras.items()}
        for nombre, corrector in self.correctores.items():
            if nombre in imgs:
                imgs[nombre] = corrector(imgs[nombre])
        return imgs

    # --- parada ------------------------------------------------------------------------------------------------
    def quieto(self) -> None:
        """Manda como objetivo la postura actual: el brazo se para donde está."""
        try:
            self.enviar(self.q())
        except Exception as e:
            log.warning("no he podido parar el brazo: %s", e)

    def cerrar(self) -> None:
        if self.senal is not None:
            self.senal.cerrar()
        if self.robot is not None:
            self.quieto()
            try:
                self.robot.disconnect()
            except Exception as e:
                log.warning("al desconectar el robot: %s", e)
            self.robot = None


# --- robot simulado ------------------------------------------------------------------------------------------------
class CuerpoSim:
    """`MundoGarbi(montaje="lateral")` visto como `Cuerpo`. Cada `enviar` avanza un fotograma del mundo (1/30 s).
    Las cámaras del mundo se llaman igual que las reales: `top` y `wrist`."""

    def __init__(self, mundo=None, max_relative_target: float | None = MAX_SALTO, resolucion=(ANCHO, ALTO)):
        if mundo is None:
            from garbi.mundo import MundoGarbi

            mundo = MundoGarbi(montaje="lateral")
            mundo.reset(semilla=0)
        self.mundo = mundo
        self.max_relative_target = max_relative_target
        self.resolucion = tuple(resolucion)
        self.ultima_enviada: np.ndarray | None = None

    def q(self) -> np.ndarray:
        return np.asarray(self.mundo.estado(), dtype=float)

    def enviar(self, q: np.ndarray) -> None:
        q = limitar_salto(forzar_montaje(q), self.q(), self.max_relative_target)
        self.ultima_enviada = q
        self.mundo.step(q, observar=False)

    def aspirar(self, encendida: bool) -> None:
        self.mundo.aspiradora = bool(encendida)

    def imagenes(self) -> dict[str, np.ndarray]:
        return {cam: self.mundo.imagen(cam, self.resolucion) for cam in CAMARAS}

    def quieto(self) -> None:
        self.mundo.step(self.q(), observar=False)

    def cerrar(self) -> None:
        self.mundo.aspiradora = False
        self.mundo.cerrar()

