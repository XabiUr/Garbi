"""Antorchas por USB serie: lectura de la del alumno, LED de la del robot y ángulos de la IMU.

El protocolo está en `lewelder.contrato` (115200 baudios, una línea JSON por muestra a 100 Hz, `L1`/`L0`, `?`).
Todo funciona igual con un puerto real (`COM3`, `/dev/ttyUSB0`), un pseudo-terminal de las antorchas virtuales
(`/dev/pts/N`) o una URL de pyserial (`loop://`, `socket://host:puerto`), así que se prueba sin placas.

Cuaternión
----------
`q = [w, x, y, z]` (Hamilton) es la orientación de la IMU: `R(q)` lleva vectores del marco de la IMU al marco
"mundo" de la propia IMU. Ese mundo no nos sirve tal cual: el rumbo del BNO055 sin magnetómetro (modo IMUPLUS,
el que usamos porque la base lleva imanes) y el de la fusión del MPU6050 son arbitrarios y derivan. Por eso se usa
una **tara**.

Tara
----
El alumno coloca la antorcha **vertical, con la punta hacia abajo y la cara superior (la opuesta al gatillo, +Z de
la IMU) mirando en el sentido de avance del cordón (+X de la pieza)** y se guarda `q_tara`. En esa postura, el marco
de la IMU respecto a la pieza es fijo y conocido (`ORIENTACION_TARA`, un giro de +90° alrededor de Y):

    +X de la IMU (eje de la antorcha, hacia la punta) → -Z de la pieza (abajo)
    +Y de la IMU                                       → +Y de la pieza
    +Z de la IMU (cara superior)                       → +X de la pieza (avance)

A partir de ahí, para cualquier `q`:

    R_pieza←imu = Rz(-giro_pieza) · ORIENTACION_TARA · R(q_tara)ᵀ · R(q)

Solo cuenta el giro relativo desde la tara, así que da igual el marco "mundo" de la IMU (y su deriva lenta se
corrige repitiendo la tara). `giro_pieza_grados` es el giro de la pieza alrededor de la vertical respecto a la
dirección de avance que tenía la antorcha en la tara (antihorario visto desde arriba positivo). Si la tara se hizo
sobre la pieza en el anclaje A y luego se suelda en el D: `giro_pieza_grados = ANCLAJES["D"].giro - ANCLAJES["A"].giro`.

Ángulos (definición del contrato)
---------------------------------
Con `a = (ax, ay, az)` el eje de la antorcha (mango → punta) en el marco de la pieza:

- **Avance** = `atan2(ax, -az)`: inclinación respecto a la vertical en el plano XZ. Positivo = empuje (la punta va
  por delante del mango en +X). Vertical = 0.
- **Trabajo** = `atan2(-az, ay)`: ángulo con la chapa base en el plano YZ, entre 0 y 180. Vertical = 90; **menos de
  90 = la punta se inclina hacia +Y** (hacia el alma en la unión en T, que está en Y >= 0); más de 90 = hacia -Y.
  Así el error respecto al objetivo (90 en la recta, 45 en la T) es simplemente `|trabajo - objetivo|`.

Girar la antorcha sobre su propio eje no cambia ninguno de los dos.
"""
from __future__ import annotations

import json
import math
import queue
import threading
import time
from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

import numpy as np
import serial
from serial.tools import list_ports

from lewelder import contrato as c

Cuaternion = tuple[float, float, float, float]

# Postura de la IMU respecto a la pieza durante la tara (columnas: ejes X, Y, Z de la IMU en la pieza).
ORIENTACION_TARA = np.array([[0.0, 0.0, 1.0], [0.0, 1.0, 0.0], [-1.0, 0.0, 0.0]])
EJE_ANTORCHA = np.array(c.EJE_ANTORCHA_EN_IMU, dtype=float)

TIMEOUT_LECTURA = 0.1  # s, lo que espera cada `read` del hilo
MAX_LINEA = 512  # bytes; una línea más larga es basura


# --- cuaterniones ------------------------------------------------------------------------------------------------
def matriz_desde_cuaternion(q: Iterable[float]) -> np.ndarray:
    """Matriz de rotación 3x3 de un cuaternión [w, x, y, z] (se normaliza)."""
    w, x, y, z = np.asarray(q, dtype=float) / np.linalg.norm(q)
    return np.array(
        [
            [1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
            [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
            [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)],
        ]
    )


def cuaternion_desde_matriz(m: np.ndarray) -> Cuaternion:
    """Cuaternión [w, x, y, z] con w >= 0 de una matriz de rotación."""
    traza = m[0, 0] + m[1, 1] + m[2, 2]
    if traza > 0:
        s = 2 * math.sqrt(traza + 1)
        q = (s / 4, (m[2, 1] - m[1, 2]) / s, (m[0, 2] - m[2, 0]) / s, (m[1, 0] - m[0, 1]) / s)
    elif m[0, 0] > m[1, 1] and m[0, 0] > m[2, 2]:
        s = 2 * math.sqrt(1 + m[0, 0] - m[1, 1] - m[2, 2])
        q = ((m[2, 1] - m[1, 2]) / s, s / 4, (m[0, 1] + m[1, 0]) / s, (m[0, 2] + m[2, 0]) / s)
    elif m[1, 1] > m[2, 2]:
        s = 2 * math.sqrt(1 + m[1, 1] - m[0, 0] - m[2, 2])
        q = ((m[0, 2] - m[2, 0]) / s, (m[0, 1] + m[1, 0]) / s, s / 4, (m[1, 2] + m[2, 1]) / s)
    else:
        s = 2 * math.sqrt(1 + m[2, 2] - m[0, 0] - m[1, 1])
        q = ((m[1, 0] - m[0, 1]) / s, (m[0, 2] + m[2, 0]) / s, (m[1, 2] + m[2, 1]) / s, s / 4)
    q = np.array(q) / np.linalg.norm(q)
    if q[0] < 0:
        q = -q
    return tuple(float(v) for v in q)


def _giro_z(grados: float) -> np.ndarray:
    r = math.radians(grados)
    return np.array([[math.cos(r), -math.sin(r), 0.0], [math.sin(r), math.cos(r), 0.0], [0.0, 0.0, 1.0]])


def _giro_eje(eje: np.ndarray, angulo: float) -> np.ndarray:
    """Matriz de giro de `angulo` radianes alrededor de `eje` (Rodrigues)."""
    k = eje / np.linalg.norm(eje)
    kx = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    return np.eye(3) + math.sin(angulo) * kx + (1 - math.cos(angulo)) * kx @ kx


# --- ángulos -----------------------------------------------------------------------------------------------------
def eje_en_pieza(q: Iterable[float], q_tara: Iterable[float], giro_pieza_grados: float = 0.0) -> np.ndarray:
    """Eje de la antorcha (mango → punta, unitario) en el marco de la pieza. Ver la tara en el docstring."""
    r_pieza = _giro_z(-giro_pieza_grados) @ ORIENTACION_TARA @ matriz_desde_cuaternion(q_tara).T
    return r_pieza @ matriz_desde_cuaternion(q) @ EJE_ANTORCHA


def angulos_antorcha(
    q: Iterable[float] | None, q_tara: Iterable[float] | None, giro_pieza_grados: float = 0.0
) -> tuple[float | None, float | None]:
    """(ángulo de trabajo, ángulo de avance) en grados; (None, None) si falta la orientación o la tara."""
    if q is None or q_tara is None:
        return None, None
    ax, ay, az = eje_en_pieza(q, q_tara, giro_pieza_grados)
    trabajo = math.degrees(math.atan2(-az, ay))
    avance = math.degrees(math.atan2(ax, -az))
    return trabajo, avance


def cuaternion_desde_angulos(
    trabajo: float,
    avance: float,
    q_tara: Iterable[float] | None = None,
    giro_pieza_grados: float = 0.0,
) -> Cuaternion:
    """Inversa de `angulos_antorcha`: un cuaternión de la IMU que da esos ángulos con esa tara.

    El giro de la antorcha sobre su propio eje es el mínimo desde la postura de la tara. Sin `q_tara`, el marco
    "mundo" de la IMU coincide con el de la tara (entonces la tara es `ORIENTACION_TARA`). Lo usan las antorchas
    virtuales y los tests. Trabajo se limita a (1, 179) y avance a (-89, 89).
    """
    t = math.radians(min(max(trabajo, 1.0), 179.0))
    v = math.radians(min(max(avance, -89.0), 89.0))
    eje = np.array([math.tan(v), 1 / math.tan(t), -1.0])
    eje /= np.linalg.norm(eje)
    abajo = np.array([0.0, 0.0, -1.0])
    giro = np.cross(abajo, eje)
    angulo = math.acos(max(-1.0, min(1.0, float(abajo @ eje))))
    minimo = _giro_eje(giro, angulo) if np.linalg.norm(giro) > 1e-12 else np.eye(3)
    postura_pieza = minimo @ ORIENTACION_TARA
    r_tara = ORIENTACION_TARA if q_tara is None else matriz_desde_cuaternion(q_tara)
    r_mundo = r_tara @ ORIENTACION_TARA.T @ _giro_z(giro_pieza_grados) @ postura_pieza
    return cuaternion_desde_matriz(r_mundo)


# --- parser ------------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class LecturaAntorcha:
    """Una muestra de la antorcha del alumno."""

    t: float  # s, reloj de la placa (millis / 1000)
    gatillo: bool
    q: Cuaternion | None  # [w, x, y, z] normalizado; None si no hay IMU
    recibido: float = 0.0  # s, time.monotonic() del PC al recibirla (0 si no viene de un puerto)


def _decodificar(texto: str | bytes) -> dict | None:
    if isinstance(texto, bytes):
        try:
            texto = texto.decode("utf-8")
        except UnicodeDecodeError:
            return None
    texto = texto.strip()
    if not texto.startswith("{") or not texto.endswith("}"):
        return None
    try:
        datos = json.loads(texto, parse_constant=lambda _: None)  # NaN/Infinity → None
    except ValueError:
        return None
    return datos if isinstance(datos, dict) else None


def _es_numero(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def leer_linea(texto: str | bytes, recibido: float = 0.0) -> LecturaAntorcha | None:
    """Convierte una línea del firmware en una lectura; None si está corrupta, cortada o no es una muestra.

    `q` nulo, ausente o de norma ~0 (el BNO055 da ceros hasta que arranca) → lectura válida con `q = None`.
    """
    datos = _decodificar(texto)
    if datos is None or not _es_numero(datos.get("t")) or datos.get("g") not in (0, 1):
        return None
    q = datos.get("q")
    if q is not None:
        if not isinstance(q, list) or len(q) != 4 or not all(_es_numero(v) for v in q):
            return None
        norma = math.sqrt(sum(v * v for v in q))
        q = tuple(float(v) / norma for v in q) if norma > 1e-6 else None
    return LecturaAntorcha(t=datos["t"] / 1000.0, gatillo=bool(datos["g"]), q=q, recibido=recibido)


def leer_identificacion(texto: str | bytes) -> str | None:
    """`"alumno"` o `"robot"` si la línea es la respuesta a `?`; None si no."""
    datos = _decodificar(texto)
    if datos is None or not isinstance(datos.get("id"), str):
        return None
    return datos["id"]


# --- puertos -----------------------------------------------------------------------------------------------------
def abrir_puerto(puerto: str, timeout: float = TIMEOUT_LECTURA) -> serial.SerialBase:
    """Abre un puerto serie real, un pty o una URL de pyserial (`loop://`, `socket://...`) a `BAUDIOS`."""
    return serial.serial_for_url(puerto, baudrate=c.BAUDIOS, timeout=timeout, write_timeout=1.0)


class _Lineas:
    """Recompone líneas a partir de trozos de bytes (una lectura puede cortar una línea por la mitad)."""

    def __init__(self):
        self.resto = b""

    def trocear(self, datos: bytes) -> list[bytes]:
        self.resto += datos
        *lineas, self.resto = self.resto.split(b"\n")
        if len(self.resto) > MAX_LINEA:
            self.resto = b""
        return lineas


ERRORES_PUERTO = (serial.SerialException, OSError, ValueError, TypeError, AttributeError)


# --- antorcha del alumno -----------------------------------------------------------------------------------------
class AntorchaAlumno:
    """Lee la antorcha del alumno en un hilo: guarda la última lectura y las mete en una cola.

    Si el puerto se cae, lo reabre cada `espera_reconexion` segundos. `abrir` permite inyectar otra fábrica de
    puertos (tests). Uso:

        with AntorchaAlumno("COM5") as alumno:
            alumno.tara()                     # antorcha vertical, cara superior hacia el avance
            trabajo, avance = alumno.angulos()
    """

    def __init__(
        self,
        puerto: str,
        *,
        abrir: Callable[[str], serial.SerialBase] = abrir_puerto,
        espera_reconexion: float = 1.0,
        tam_cola: int = 1000,
    ):
        self.puerto = puerto
        self.abrir = abrir
        self.espera_reconexion = espera_reconexion
        self.cola: queue.Queue[LecturaAntorcha] = queue.Queue(maxsize=tam_cola)
        self.ultima: LecturaAntorcha | None = None
        self.q_tara: Cuaternion | None = None
        self.identidad: str | None = None
        self.reconexiones = 0
        self.n_lecturas = 0
        self.n_descartadas = 0  # líneas que no eran ni muestra ni identificación
        self.serial: serial.SerialBase | None = None
        self._cerrojo = threading.Lock()
        self._hay_id = threading.Event()
        self._parar = threading.Event()
        self._hilo = threading.Thread(target=self._bucle, name=f"antorcha-alumno-{puerto}", daemon=True)
        self._hilo.start()

    @property
    def conectado(self) -> bool:
        return self.serial is not None

    # -- hilo --
    def _bucle(self):
        lineas = _Lineas()
        se_cayo = False
        while not self._parar.is_set():
            if self.serial is None:
                try:
                    ser = self.abrir(self.puerto)
                    ser.reset_input_buffer()
                except ERRORES_PUERTO:
                    self._parar.wait(self.espera_reconexion)
                    continue
                with self._cerrojo:
                    self.serial = ser
                if se_cayo:
                    self.reconexiones += 1
                lineas = _Lineas()
            try:
                datos = self.serial.read(max(1, self.serial.in_waiting))
            except ERRORES_PUERTO:
                self._soltar_puerto()
                se_cayo = True
                continue
            if datos:
                ahora = time.monotonic()
                for linea in lineas.trocear(datos):
                    self._procesar(linea, ahora)

    def _procesar(self, linea: bytes, ahora: float):
        lectura = leer_linea(linea, recibido=ahora)
        if lectura is not None:
            self.ultima = lectura
            self.n_lecturas += 1
            if self.cola.full():
                try:
                    self.cola.get_nowait()  # se pierde la más vieja, nunca se bloquea el hilo
                except queue.Empty:
                    pass
            self.cola.put_nowait(lectura)
            return
        identidad = leer_identificacion(linea)
        if identidad is not None:
            self.identidad = identidad
            self._hay_id.set()
        elif linea.strip():
            self.n_descartadas += 1

    def _soltar_puerto(self):
        with self._cerrojo:
            ser, self.serial = self.serial, None
        if ser is not None:
            try:
                ser.close()
            except ERRORES_PUERTO:
                pass

    # -- API --
    def esperar_lectura(self, timeout: float | None = None) -> LecturaAntorcha | None:
        """Saca la siguiente lectura de la cola (espera hasta `timeout`); None si no llega."""
        try:
            return self.cola.get(timeout=timeout)
        except queue.Empty:
            return None

    def tara(self) -> bool:
        """Guarda la orientación actual como tara. False si no hay lectura con IMU."""
        if self.ultima is None or self.ultima.q is None:
            return False
        self.q_tara = self.ultima.q
        return True

    def angulos(
        self, lectura: LecturaAntorcha | None = None, giro_pieza_grados: float = 0.0
    ) -> tuple[float | None, float | None]:
        """(trabajo, avance) de `lectura` (por defecto la última) con la tara guardada."""
        lectura = lectura or self.ultima
        if lectura is None:
            return None, None
        return angulos_antorcha(lectura.q, self.q_tara, giro_pieza_grados)

    def identificar(self, timeout: float = 1.0) -> str | None:
        """Manda `?` (repetido cada 0,25 s) y espera la respuesta `{"id": ...}`."""
        self._hay_id.clear()
        fin = time.monotonic() + timeout
        while time.monotonic() < fin:
            with self._cerrojo:
                if self.serial is not None:
                    try:
                        self.serial.write(c.ORDEN_IDENTIFICAR.encode())
                    except ERRORES_PUERTO:
                        pass
            if self._hay_id.wait(min(0.25, max(0.0, fin - time.monotonic()))):
                return self.identidad
        return None

    def cerrar(self):
        self._parar.set()
        self._hilo.join(timeout=2)
        self._soltar_puerto()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.cerrar()


# --- antorcha del robot ------------------------------------------------------------------------------------------
class AntorchaRobot:
    """LED de la antorcha del robot. `led(True/False)` solo escribe si cambia; un latido reenvía el estado cada
    `latido` segundos sin otras órdenes para que el firmware (que apaga a los 2 s de silencio) no lo apague.

    Si el puerto se cae, el hilo del latido lo reabre y reenvía el estado actual.
    """

    def __init__(
        self,
        puerto: str,
        *,
        abrir: Callable[[str], serial.SerialBase] = abrir_puerto,
        latido: float = c.LATIDO_LED,
        espera_reconexion: float = 1.0,
    ):
        self.puerto = puerto
        self.abrir = abrir
        self.latido = latido
        self.espera_reconexion = espera_reconexion
        self.encendido = False
        self.n_envios = 0
        self.serial: serial.SerialBase | None = None
        self._ultimo_envio = 0.0
        self._cerrojo = threading.RLock()
        self._parar = threading.Event()
        try:
            self._conectar(primera=True)
        except ERRORES_PUERTO:
            pass
        self._hilo = threading.Thread(target=self._bucle, name=f"antorcha-robot-{puerto}", daemon=True)
        self._hilo.start()

    def _conectar(self, primera: bool = False):
        ser = self.abrir(self.puerto)
        with self._cerrojo:
            self.serial = ser
            # Al reconectar se reenvía el estado enseguida; al abrir por primera vez no se manda nada hasta que
            # haya una orden o venza el latido (el firmware arranca con el LED apagado).
            self._ultimo_envio = time.monotonic() if primera else 0.0

    def _enviar(self, orden: str) -> bool:
        with self._cerrojo:
            if self.serial is None:
                return False
            try:
                self.serial.write(orden.encode())
                self.serial.flush()
            except ERRORES_PUERTO:
                try:
                    self.serial.close()
                except ERRORES_PUERTO:
                    pass
                self.serial = None
                return False
            self._ultimo_envio = time.monotonic()
            self.n_envios += 1
            return True

    def _orden_estado(self) -> str:
        return c.ORDEN_LED_ON if self.encendido else c.ORDEN_LED_OFF

    def _bucle(self):
        while not self._parar.is_set():
            if self.serial is None:
                try:
                    self._conectar()
                except ERRORES_PUERTO:
                    self._parar.wait(self.espera_reconexion)
                    continue
            with self._cerrojo:
                vencido = time.monotonic() - self._ultimo_envio >= self.latido
                if vencido:
                    self._enviar(self._orden_estado())
            self._parar.wait(min(0.05, self.latido / 4))

    def led(self, encendido: bool) -> None:
        encendido = bool(encendido)
        with self._cerrojo:
            if encendido == self.encendido:
                return
            self.encendido = encendido
            self._enviar(self._orden_estado())

    def identificar(self, timeout: float = 1.0) -> str | None:
        """Manda `?` y espera `{"id": ...}`. Pensado para usarse antes de empezar a mandar órdenes."""
        fin = time.monotonic() + timeout
        lineas = _Lineas()
        with self._cerrojo:
            if self.serial is None:
                return None
            ultimo_pregunta = 0.0
            while time.monotonic() < fin:
                try:
                    if time.monotonic() - ultimo_pregunta > 0.25:
                        self.serial.write(c.ORDEN_IDENTIFICAR.encode())
                        ultimo_pregunta = time.monotonic()
                    datos = self.serial.read(max(1, self.serial.in_waiting))
                except ERRORES_PUERTO:
                    return None
                for linea in lineas.trocear(datos):
                    identidad = leer_identificacion(linea)
                    if identidad is not None:
                        return identidad
        return None

    def cerrar(self):
        """Apaga el LED (seguridad) y cierra el puerto."""
        self._parar.set()
        self._hilo.join(timeout=2)
        with self._cerrojo:
            self.encendido = False
            self._enviar(c.ORDEN_LED_OFF)
            if self.serial is not None:
                try:
                    self.serial.close()
                except ERRORES_PUERTO:
                    pass
                self.serial = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.cerrar()


# --- autodetección -----------------------------------------------------------------------------------------------
def _preguntar_id(puerto: str, timeout: float, abrir: Callable[[str], serial.SerialBase]) -> str | None:
    """Abre `puerto`, manda `?` cada 0,3 s y devuelve el id que conteste. El Arduino Nano (y muchos ESP32) se
    reinician al abrir el puerto y tardan ~1,5 s en contestar: por eso el `timeout` por defecto es de 3 s."""
    try:
        ser = abrir(puerto)
    except ERRORES_PUERTO:
        return None
    lineas = _Lineas()
    fin = time.monotonic() + timeout
    ultimo_pregunta = 0.0
    try:
        while time.monotonic() < fin:
            if time.monotonic() - ultimo_pregunta > 0.3:
                ser.write(c.ORDEN_IDENTIFICAR.encode())
                ultimo_pregunta = time.monotonic()
            for linea in lineas.trocear(ser.read(max(1, ser.in_waiting))):
                identidad = leer_identificacion(linea)
                if identidad is not None:
                    return identidad
    except ERRORES_PUERTO:
        return None
    finally:
        try:
            ser.close()
        except ERRORES_PUERTO:
            pass
    return None


def buscar_antorchas(
    puertos: Iterable[str] | None = None,
    timeout: float = 3.0,
    abrir: Callable[[str], serial.SerialBase] = abrir_puerto,
) -> dict[str, str]:
    """Pregunta `?` a cada puerto (por defecto, todos los del sistema, en paralelo) y devuelve
    `{"alumno": puerto, "robot": puerto}` con los que contesten."""
    if puertos is None:
        puertos = [p.device for p in list_ports.comports()]
    puertos = list(puertos)
    if not puertos:
        return {}
    with ThreadPoolExecutor(max_workers=len(puertos)) as hilos:
        ids = list(hilos.map(lambda p: _preguntar_id(p, timeout, abrir), puertos))
    return {identidad: puerto for puerto, identidad in zip(puertos, ids) if identidad is not None}
