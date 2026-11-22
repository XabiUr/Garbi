"""Tests de las antorchas: parser serie, ángulos con tara, antorcha del robot y antorchas virtuales en pty."""
from __future__ import annotations

import json
import math
import time

import numpy as np
import pytest
import serial

from lewelder import antorcha as a
from lewelder import contrato as c
from lewelder.antorcha_virtual import AntorchaAlumnoVirtual, AntorchaRobotVirtual


# --- ayudas de rotación independientes del módulo bajo prueba ----------------------------------------------------
def rot_x(grados: float) -> np.ndarray:
    r = math.radians(grados)
    return np.array([[1, 0, 0], [0, math.cos(r), -math.sin(r)], [0, math.sin(r), math.cos(r)]])


def rot_y(grados: float) -> np.ndarray:
    r = math.radians(grados)
    return np.array([[math.cos(r), 0, math.sin(r)], [0, 1, 0], [-math.sin(r), 0, math.cos(r)]])


def rot_z(grados: float) -> np.ndarray:
    r = math.radians(grados)
    return np.array([[math.cos(r), -math.sin(r), 0], [math.sin(r), math.cos(r), 0], [0, 0, 1]])


def cuat(m: np.ndarray) -> tuple[float, float, float, float]:
    """Cuaternión [w, x, y, z] de una matriz de rotación (método de Shepperd, sin usar el módulo)."""
    traza = np.trace(m)
    if traza > 0:
        s = math.sqrt(traza + 1.0) * 2
        return (0.25 * s, (m[2, 1] - m[1, 2]) / s, (m[0, 2] - m[2, 0]) / s, (m[1, 0] - m[0, 1]) / s)
    i = int(np.argmax(np.diag(m)))
    if i == 0:
        s = math.sqrt(1.0 + m[0, 0] - m[1, 1] - m[2, 2]) * 2
        return ((m[2, 1] - m[1, 2]) / s, 0.25 * s, (m[0, 1] + m[1, 0]) / s, (m[0, 2] + m[2, 0]) / s)
    if i == 1:
        s = math.sqrt(1.0 + m[1, 1] - m[0, 0] - m[2, 2]) * 2
        return ((m[0, 2] - m[2, 0]) / s, (m[0, 1] + m[1, 0]) / s, 0.25 * s, (m[1, 2] + m[2, 1]) / s)
    s = math.sqrt(1.0 + m[2, 2] - m[0, 0] - m[1, 1]) * 2
    return ((m[1, 0] - m[0, 1]) / s, (m[0, 2] + m[2, 0]) / s, (m[1, 2] + m[2, 1]) / s, 0.25 * s)


# Postura de la tara en el marco de la pieza: eje de la antorcha (+X de la IMU) hacia abajo y la cara superior
# (+Z de la IMU) mirando al sentido de avance (+X de la pieza). Es un giro de +90° alrededor de Y.
TARA = rot_y(90)
# Marco "mundo" arbitrario de la IMU (rumbo e inclinación cualesquiera): la tara lo hace irrelevante.
MUNDO_RARO = rot_z(137) @ rot_x(-21) @ rot_y(8)


# --- parser ------------------------------------------------------------------------------------------------------
class TestLeerLinea:
    def test_linea_valida(self):
        lec = a.leer_linea('{"t": 1234, "g": 1, "q": [1, 0, 0, 0]}\n')
        assert lec is not None
        assert lec.t == pytest.approx(1.234)
        assert lec.gatillo is True
        assert lec.q == pytest.approx((1.0, 0.0, 0.0, 0.0))

    def test_acepta_bytes_y_retorno_de_carro(self):
        lec = a.leer_linea(b'{"t":10,"g":0,"q":[0.7071,0,0.7071,0]}\r\n')
        assert lec is not None and lec.gatillo is False
        assert lec.q == pytest.approx((math.sqrt(0.5), 0, math.sqrt(0.5), 0), abs=1e-4)

    def test_normaliza_el_cuaternion(self):
        lec = a.leer_linea('{"t":0,"g":0,"q":[2,0,0,0]}')
        assert lec.q == pytest.approx((1.0, 0.0, 0.0, 0.0))

    def test_sin_imu_q_nulo_o_cero(self):
        assert a.leer_linea('{"t":5,"g":1,"q":null}').q is None
        assert a.leer_linea('{"t":5,"g":1}').q is None
        # El BNO055 da ceros hasta que arranca la fusión: se trata como "sin orientación".
        lec = a.leer_linea('{"t":5,"g":1,"q":[0,0,0,0]}')
        assert lec is not None and lec.gatillo and lec.q is None

    @pytest.mark.parametrize(
        "texto",
        [
            "",
            "\n",
            '{"t": 12, "g": 1, "q": [0.9',  # cortada
            '0.01, 0.02]}',  # empieza a mitad de línea
            '{"t":1,"g":1,"q":[1,0,0,0]}{"t":2',  # dos pegadas
            "\x00\xff basura del arranque del ESP32",
            '{"t":"x","g":1,"q":[1,0,0,0]}',
            '{"t":1,"g":7,"q":[1,0,0,0]}',
            '{"t":1,"g":1,"q":[1,0,0]}',
            '{"t":1,"g":1,"q":[1,0,"a",0]}',
            '{"t":1,"g":1,"q":[nan,0,0,0]}',
            '{"t":1,"g":1,"q":[NaN,0,0,0]}',
            '{"id": "alumno"}',
            "[1, 2, 3]",
            b"\xc3\x28 bytes no utf8",
        ],
    )
    def test_lineas_corruptas_devuelven_none(self, texto):
        assert a.leer_linea(texto) is None

    def test_identificacion(self):
        assert a.leer_identificacion('{"id": "alumno"}\n') == "alumno"
        assert a.leer_identificacion(b'{"id":"robot"}\r\n') == "robot"
        assert a.leer_identificacion('{"t":1,"g":1,"q":[1,0,0,0]}') is None
        assert a.leer_identificacion('{"id": "rob') is None


# --- ángulos -----------------------------------------------------------------------------------------------------
def angulos_de(postura_pieza: np.ndarray, mundo: np.ndarray = np.eye(3), giro_tara: float = 0.0, giro: float = 0.0):
    """Ángulos de una postura dada en el marco de la pieza, con la tara hecha en un marco girado `giro_tara`."""
    q_tara = cuat(mundo @ rot_z(giro_tara) @ TARA)
    q = cuat(mundo @ rot_z(giro_tara + giro) @ postura_pieza)
    return a.angulos_antorcha(q, q_tara, giro_pieza_grados=giro)


class TestAngulos:
    def test_vertical(self):
        trabajo, avance = angulos_de(TARA)
        assert trabajo == pytest.approx(90.0, abs=1e-6)
        assert avance == pytest.approx(0.0, abs=1e-6)

    def test_inclinada_15_hacia_atras_en_xz_es_empuje(self):
        # Mango hacia -X, punta hacia +X: giro de -15° alrededor de Y de la pieza.
        trabajo, avance = angulos_de(rot_y(-15) @ TARA)
        assert avance == pytest.approx(15.0, abs=1e-6)
        assert trabajo == pytest.approx(90.0, abs=1e-6)

    def test_arrastre_es_negativo(self):
        _, avance = angulos_de(rot_y(10) @ TARA)
        assert avance == pytest.approx(-10.0, abs=1e-6)

    def test_inclinada_45_en_yz(self):
        # Punta hacia +Y (hacia el alma en la unión en T), mango hacia -Y.
        trabajo, avance = angulos_de(rot_x(45) @ TARA)
        assert trabajo == pytest.approx(45.0, abs=1e-6)
        assert avance == pytest.approx(0.0, abs=1e-6)

    def test_inclinada_al_otro_lado_supera_90(self):
        trabajo, _ = angulos_de(rot_x(-30) @ TARA)
        assert trabajo == pytest.approx(120.0, abs=1e-6)

    def test_combinada(self):
        # Eje deseado: trabajo 60, avance 12 → eje ∝ (tan 12, cot 60, -1).
        eje = np.array([math.tan(math.radians(12)), 1 / math.tan(math.radians(60)), -1.0])
        eje /= np.linalg.norm(eje)
        # Cualquier postura cuyo +X de la IMU sea ese eje (el giro sobre su propio eje no importa).
        x = eje
        y = np.cross([0, 0, 1.0], x)
        y /= np.linalg.norm(y)
        z = np.cross(x, y)
        postura = np.column_stack([x, y, z])
        trabajo, avance = angulos_de(postura)
        assert trabajo == pytest.approx(60.0, abs=1e-6)
        assert avance == pytest.approx(12.0, abs=1e-6)

    def test_girar_sobre_su_eje_no_cambia_los_angulos(self):
        for giro_propio in (0, 33, 90, 180, -120):
            trabajo, avance = angulos_de(rot_y(-15) @ TARA @ rot_x(giro_propio))
            assert avance == pytest.approx(15.0, abs=1e-6)
            assert trabajo == pytest.approx(90.0, abs=1e-6)

    def test_tara_no_trivial(self):
        # Marco de la IMU cualquiera y la tara hecha con otro rumbo: da lo mismo que en el caso ideal.
        trabajo, avance = angulos_de(rot_x(45) @ rot_y(-15) @ TARA, mundo=MUNDO_RARO, giro_tara=-64)
        ref = angulos_de(rot_x(45) @ rot_y(-15) @ TARA)
        assert (trabajo, avance) == pytest.approx(ref, abs=1e-6)
        trabajo, avance = angulos_de(rot_y(-15) @ TARA, mundo=MUNDO_RARO, giro_tara=200)
        assert avance == pytest.approx(15.0, abs=1e-6)
        assert trabajo == pytest.approx(90.0, abs=1e-6)

    def test_giro_de_pieza(self):
        # Tara con la pieza en un anclaje de giro 0; la pieza pasa a otro girado 90°. La antorcha empuja 15° a lo
        # largo del nuevo cordón: en el marco de la tara eso es una inclinación hacia +Y.
        q_tara = cuat(MUNDO_RARO @ TARA)
        q = cuat(MUNDO_RARO @ rot_z(90) @ rot_y(-15) @ TARA)
        trabajo, avance = a.angulos_antorcha(q, q_tara, giro_pieza_grados=90)
        assert avance == pytest.approx(15.0, abs=1e-6)
        assert trabajo == pytest.approx(90.0, abs=1e-6)
        # Sin indicar el giro, el empuje se confunde con ángulo de trabajo.
        trabajo, avance = a.angulos_antorcha(q, q_tara)
        assert avance == pytest.approx(0.0, abs=1e-6)
        assert trabajo == pytest.approx(75.0, abs=1e-6)

    def test_giro_entre_anclajes_del_contrato(self):
        giro = c.ANCLAJES["D"].giro - c.ANCLAJES["A"].giro
        q_tara = cuat(TARA)
        q = cuat(rot_z(giro) @ rot_x(45) @ TARA)
        trabajo, avance = a.angulos_antorcha(q, q_tara, giro_pieza_grados=giro)
        assert (trabajo, avance) == pytest.approx((45.0, 0.0), abs=1e-6)

    def test_sin_orientacion_o_sin_tara(self):
        assert a.angulos_antorcha(None, cuat(TARA)) == (None, None)
        assert a.angulos_antorcha(cuat(TARA), None) == (None, None)

    @pytest.mark.parametrize("trabajo,avance,giro", [(90, 0, 0), (45, 10, 0), (100, -5, 30), (70, 18, -90)])
    def test_cuaternion_desde_angulos_es_la_inversa(self, trabajo, avance, giro):
        q_tara = cuat(MUNDO_RARO @ TARA)
        q = a.cuaternion_desde_angulos(trabajo, avance, q_tara=q_tara, giro_pieza_grados=giro)
        assert np.linalg.norm(q) == pytest.approx(1.0)
        assert a.angulos_antorcha(q, q_tara, giro_pieza_grados=giro) == pytest.approx((trabajo, avance), abs=1e-6)

    def test_cuaternion_de_tara_por_defecto(self):
        assert np.allclose(a.matriz_desde_cuaternion(a.cuaternion_desde_angulos(90, 0)), TARA)


# --- antorcha del robot con loop:// ------------------------------------------------------------------------------
def leer_todo(ser, espera=0.05) -> bytes:
    time.sleep(espera)
    return ser.read(ser.in_waiting)


class TestAntorchaRobotLoop:
    def test_led_sin_reenviar_si_no_cambia(self):
        robot = a.AntorchaRobot("loop://", latido=10.0)
        try:
            robot.led(True)
            assert leer_todo(robot.serial) == b"L1\n"
            robot.led(True)
            robot.led(True)
            assert leer_todo(robot.serial) == b""
            robot.led(False)
            assert leer_todo(robot.serial) == b"L0\n"
            assert robot.encendido is False
        finally:
            robot.cerrar()

    def test_latido(self):
        robot = a.AntorchaRobot("loop://", latido=0.1)
        try:
            robot.led(True)
            datos = leer_todo(robot.serial, espera=0.45)
            assert datos.startswith(b"L1\n")
            assert 3 <= datos.count(b"L1\n") <= 6
            assert b"L0" not in datos
        finally:
            robot.cerrar()

    def test_cerrar_apaga_el_led(self):
        robot = a.AntorchaRobot("loop://", latido=10.0)
        robot.led(True)
        leer_todo(robot.serial)
        robot.cerrar()
        assert robot.encendido is False

    def test_acepta_fabrica_de_url(self):
        ser = a.abrir_puerto("loop://")
        assert isinstance(ser, serial.SerialBase)
        assert ser.baudrate == c.BAUDIOS
        ser.close()


# --- reconexión de la antorcha del alumno con una fábrica de puertos falsa --------------------------------------
class PuertoFalso:
    """Puerto que entrega cada trozo en una lectura distinta y luego "se desenchufa" (lanza SerialException)."""

    def __init__(self, trozos: list[bytes], desenchufar: bool):
        self.trozos = list(trozos)
        self.desenchufar = desenchufar
        self.escrito = b""
        self.is_open = True

    @property
    def in_waiting(self):
        return len(self.trozos[0]) if self.trozos else 0

    def read(self, n=1):
        if not self.trozos:
            if self.desenchufar:
                raise serial.SerialException("desenchufado")
            time.sleep(0.01)
            return b""
        trozo = self.trozos[0][:n]
        self.trozos[0] = self.trozos[0][n:]
        if not self.trozos[0]:
            self.trozos.pop(0)
        return trozo

    def write(self, datos):
        self.escrito += datos
        return len(datos)

    def reset_input_buffer(self):
        pass

    def close(self):
        self.is_open = False


def test_alumno_se_reconecta():
    linea = lambda t: json.dumps({"t": t, "g": 1, "q": [1, 0, 0, 0]}).encode() + b"\n"
    puertos = [
        PuertoFalso([linea(1), linea(2)], desenchufar=True),
        PuertoFalso([linea(3), linea(4)], desenchufar=False),
    ]
    intentos = []

    def abrir(puerto):
        intentos.append(puerto)
        if len(intentos) == 2:
            raise serial.SerialException("todavía no está")  # un intento fallido entre medias
        return puertos.pop(0)

    alumno = a.AntorchaAlumno("COM_FALSO", abrir=abrir, espera_reconexion=0.02)
    try:
        fin = time.monotonic() + 2
        while (alumno.ultima is None or alumno.ultima.t < 0.004) and time.monotonic() < fin:
            time.sleep(0.01)
        assert alumno.ultima is not None and alumno.ultima.t == pytest.approx(0.004)
        assert alumno.reconexiones == 1
        assert intentos == ["COM_FALSO"] * 3
        ts = [alumno.cola.get_nowait().t for _ in range(4)]
        assert ts == pytest.approx([0.001, 0.002, 0.003, 0.004])
    finally:
        alumno.cerrar()


def test_alumno_lineas_cortadas_entre_lecturas():
    # Una línea llega en dos trozos y hay basura al principio: se recompone sin perder la muestra.
    puerto = PuertoFalso([b'\x00basura}\n{"t":7,"g":0,', b'"q":null}\n'], desenchufar=False)
    alumno = a.AntorchaAlumno("X", abrir=lambda p: puerto)
    try:
        lec = alumno.esperar_lectura(timeout=1.0)
        assert lec is not None and lec.t == pytest.approx(0.007) and lec.q is None
        assert alumno.n_descartadas >= 1
    finally:
        alumno.cerrar()


# --- de punta a punta con las antorchas virtuales en pty ---------------------------------------------------------
def guion_prueba(t: float):
    """Trayectoria de prueba: vertical sin gatillo 0,5 s y luego empuje de 10° y trabajo 80° con gatillo."""
    if t < 0.5:
        return 90.0, 0.0, False
    return 80.0, 10.0, True


def test_punta_a_punta_alumno_virtual():
    with AntorchaAlumnoVirtual(trayectoria=guion_prueba, mundo=MUNDO_RARO) as virtual:
        assert virtual.ruta.startswith("/dev/")
        with a.AntorchaAlumno(virtual.ruta) as alumno:
            assert alumno.identificar(timeout=2.0) == "alumno"
            primera = alumno.esperar_lectura(timeout=2.0)
            assert primera is not None and primera.gatillo is False
            assert alumno.tara()
            # ~100 Hz; a los 0,5 s del arranque se pulsa el gatillo.
            time.sleep(0.8)
            lecturas = []
            while not alumno.cola.empty():
                lecturas.append(alumno.cola.get_nowait())
            ts = np.array([l.t for l in lecturas])
            assert len(ts) > 40
            frecuencia = (len(ts) - 1) / (ts[-1] - ts[0])
            assert frecuencia == pytest.approx(c.FRECUENCIA_ANTORCHA, rel=0.15)
            ultima = alumno.ultima
            assert ultima.gatillo is True
            trabajo, avance = alumno.angulos(ultima)
            assert trabajo == pytest.approx(80.0, abs=0.1)
            assert avance == pytest.approx(10.0, abs=0.1)


def test_punta_a_punta_alumno_sin_imu():
    with AntorchaAlumnoVirtual(trayectoria=guion_prueba, sin_imu=True) as virtual:
        with a.AntorchaAlumno(virtual.ruta) as alumno:
            lec = alumno.esperar_lectura(timeout=2.0)
            assert lec is not None and lec.q is None
            assert alumno.tara() is False
            assert alumno.angulos(lec) == (None, None)


def test_alumno_virtual_control_manual():
    with AntorchaAlumnoVirtual() as virtual:
        virtual.fijar(trabajo=45.0, avance=5.0, gatillo=True)
        with a.AntorchaAlumno(virtual.ruta) as alumno:
            time.sleep(0.2)
            q_tara = virtual.q_tara
            lec = alumno.ultima
            assert lec.gatillo is True
            assert a.angulos_antorcha(lec.q, q_tara) == pytest.approx((45.0, 5.0), abs=0.1)


def test_punta_a_punta_robot_virtual():
    with AntorchaRobotVirtual() as virtual:
        with a.AntorchaRobot(virtual.ruta, latido=0.2) as robot:
            assert robot.identificar(timeout=2.0) == "robot"
            robot.led(True)
            fin = time.monotonic() + 1
            while not virtual.encendido and time.monotonic() < fin:
                time.sleep(0.01)
            assert virtual.encendido
            time.sleep(0.5)  # el latido lo mantiene encendido
            assert virtual.encendido
            robot.led(False)
            time.sleep(0.1)
            assert not virtual.encendido
        estados = [e for _, e in virtual.registro]
        assert estados[0] is True and False in estados


def test_robot_virtual_se_apaga_sin_ordenes():
    with AntorchaRobotVirtual(tiempo_seguridad=0.3) as virtual:
        ser = serial.Serial(virtual.ruta, c.BAUDIOS, timeout=0.1)
        ser.write(b"L1\n")
        time.sleep(0.1)
        assert virtual.encendido
        time.sleep(0.4)
        assert not virtual.encendido
        ser.close()


def test_buscar_antorchas():
    with AntorchaAlumnoVirtual() as alumno, AntorchaRobotVirtual() as robot:
        encontradas = a.buscar_antorchas([robot.ruta, alumno.ruta, "/dev/no_existe"], timeout=2.0)
        assert encontradas == {"alumno": alumno.ruta, "robot": robot.ruta}
