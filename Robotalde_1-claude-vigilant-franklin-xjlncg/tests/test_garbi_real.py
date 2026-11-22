"""Pruebas de T4 (robot real, simulado, registro y programa principal) con dobles: sin brazo, cámaras ni serie."""
import json
import threading
import time
from datetime import datetime

import numpy as np
import pytest

from garbi import contrato as g
from garbi import real
from garbi.correr import JuezSim, argumentos, bucle
from garbi.real import (CLAVES_ACCION, AjustesCamara, CuerpoReal, CuerpoSim, SenalAspiradora, accion_lerobot,
                        controles_v4l2, fijar_ajustes_cv2, limitar_salto, ordenes_v4l2, q_desde_lerobot)
from garbi.registro import DetectorCiclos, RegistroCiclos, ResumenCiclo, normalizar_estado
from garbi.tipos import ARTICULACIONES, Cuerpo, Escena, Orden, Taladro


# --- dobles --------------------------------------------------------------------------------------------------------
class SerieFalsa:
    def __init__(self):
        self.escrito: list[tuple[float, bytes]] = []
        self.cerrada = False
        self._candado = threading.Lock()

    def write(self, datos: bytes):
        assert not self.cerrada, "escritura con el puerto cerrado"
        with self._candado:
            self.escrito.append((time.monotonic(), datos))

    def close(self):
        self.cerrada = True

    def lineas(self):
        with self._candado:
            return [d for _, d in self.escrito]


class BusFalso:
    def __init__(self, robot):
        self.robot = robot

    def sync_read(self, registro, num_retry=0):
        assert registro == "Present_Position"
        return dict(zip(ARTICULACIONES, self.robot.posicion))


class CamaraFalsa:
    def __init__(self, indice, alto=480, ancho=640):
        self.index_or_path = indice
        self.forma = (alto, ancho, 3)

    def read_latest(self, max_age_ms=500):
        return np.zeros(self.forma, np.uint8)


class RobotFalso:
    """Imita `SO101Follower`: send_action con claves `<motor>.pos` y recorte por max_relative_target."""

    def __init__(self, config):
        self.config = config
        self.posicion = np.array([10.0, -90.0, 50.0, -40.0, 0.0, 0.0])
        self.bus = BusFalso(self)
        self.cameras = {"top": CamaraFalsa(0), "wrist": CamaraFalsa(2, 720, 1280)}
        self.acciones: list[dict] = []
        self.conectado = False

    def connect(self, calibrate=True):
        self.conectado = True

    def disconnect(self):
        self.conectado = False

    def send_action(self, accion):
        from lerobot.robots.utils import ensure_safe_goal_position

        objetivo = {k.removesuffix(".pos"): v for k, v in accion.items()}
        if self.config.max_relative_target is not None:
            actual = dict(zip(ARTICULACIONES, self.posicion))
            objetivo = ensure_safe_goal_position({k: (v, actual[k]) for k, v in objetivo.items()},
                                                 self.config.max_relative_target)
        self.acciones.append(dict(accion))
        return {f"{k}.pos": v for k, v in objetivo.items()}


@pytest.fixture
def cuerpo_real(monkeypatch):
    ajustes = []
    monkeypatch.setattr(real, "fijar_ajustes_camara", lambda cam, aj: ajustes.append(cam.index_or_path))
    serie = SerieFalsa()
    senal = SenalAspiradora(serie=serie, periodo=0.05)
    c = CuerpoReal("/dev/falso", "garbi", {"top": 0, "wrist": 2}, max_relative_target=5,
                   fabrica_robot=lambda cuerpo: RobotFalso(cuerpo.config()), senal=senal)
    c.conectar()
    c.ajustes_aplicados = ajustes
    c.serie = serie
    yield c
    c.cerrar()


# --- señal de la aspiradora ----------------------------------------------------------------------------------------
def test_latido_cada_200_ms_y_cero_al_cerrar():
    serie = SerieFalsa()
    s = SenalAspiradora(serie=serie)  # periodo por defecto: 0,2 s
    assert s.periodo == pytest.approx(0.2)
    time.sleep(0.5)
    s.poner(True)
    time.sleep(0.65)
    s.cerrar()
    tiempos = [t for t, _ in serie.escrito]
    lineas = serie.lineas()
    assert set(lineas) <= {b"0\n", b"1\n"}
    assert lineas[0] == b"0\n" and b"1\n" in lineas
    assert lineas[-1] == b"0\n" and serie.cerrada
    # latidos a ritmo de 200 ms mientras está encendida (entre el primer 1 y el cierre)
    i1 = lineas.index(b"1\n")
    unos = [t for (t, d) in serie.escrito[i1:] if d == b"1\n"]
    assert len(unos) >= 3
    assert np.allclose(np.diff(unos), 0.2, atol=0.06)
    # y antes, los ceros también a 200 ms
    ceros = tiempos[:i1]
    assert len(ceros) >= 2 and np.allclose(np.diff(ceros), 0.2, atol=0.06)
    # nada después de cerrar
    n = len(serie.escrito)
    time.sleep(0.3)
    assert len(serie.escrito) == n


def test_cambio_se_manda_en_el_momento():
    serie = SerieFalsa()
    s = SenalAspiradora(serie=serie, periodo=10.0)
    time.sleep(0.05)
    t = time.monotonic()
    s.poner(True)
    time.sleep(0.1)
    s.cerrar()
    unos = [ti for ti, d in serie.escrito if d == b"1\n"]
    assert unos and unos[0] - t < 0.05
    assert serie.lineas()[-1] == b"0\n"


def test_cerrar_dos_veces_no_falla():
    serie = SerieFalsa()
    s = SenalAspiradora(serie=serie, periodo=0.05)
    s.cerrar()
    s.cerrar()
    assert serie.lineas()[-1] == b"0\n"


# --- conversión con LeRobot ----------------------------------------------------------------------------------------
def test_claves_de_accion_de_lerobot():
    from lerobot.robots.so_follower import SO101Follower, SO101FollowerConfig

    robot = SO101Follower(SO101FollowerConfig(port="/dev/falso", id="prueba"))  # no conecta: sin hardware
    assert tuple(robot.action_features) == CLAVES_ACCION
    q = np.arange(6, dtype=float)
    a = accion_lerobot(q)
    assert list(a) == list(CLAVES_ACCION) and a["elbow_flex.pos"] == 2.0
    assert np.array_equal(q_desde_lerobot(a), q)
    assert np.array_equal(q_desde_lerobot(dict(zip(ARTICULACIONES, q))), q)  # salida de bus.sync_read
    with pytest.raises(ValueError):
        accion_lerobot(np.zeros(5))


def test_config_de_lerobot():
    c = CuerpoReal("/dev/ttyACM0", "garbi", {"top": "0", "wrist": "/dev/video2"}, max_relative_target=8).config()
    assert c.port == "/dev/ttyACM0" and c.id == "garbi" and c.use_degrees
    assert isinstance(c.max_relative_target, float)  # con int, ensure_safe_goal_position lanza TypeError
    assert not c.disable_torque_on_disconnect  # el brazo no se cae al parar
    top, wrist = c.cameras["top"], c.cameras["wrist"]
    assert (top.width, top.height, top.fps) == (640, 480, 30) and top.index_or_path == 0
    assert str(wrist.index_or_path) == "/dev/video2"
    assert top.color_mode.value == "rgb"


def test_limitar_salto_igual_que_lerobot():
    from lerobot.robots.utils import ensure_safe_goal_position

    q_actual = np.array([0.0, 10, -10, 5, 0, 0])
    q = np.array([30.0, 9, -40, 5.5, 3, 50])
    nuestro = limitar_salto(q, q_actual, 10.0)
    suyo = ensure_safe_goal_position({n: (a, b) for n, a, b in zip(ARTICULACIONES, q, q_actual)}, 10.0)
    assert np.allclose(nuestro, [suyo[n] for n in ARTICULACIONES])


# --- CuerpoReal con dobles -----------------------------------------------------------------------------------------
def test_enviar_fuerza_montaje_y_recorta(cuerpo_real):
    c = cuerpo_real
    c.enviar(np.array([12.0, -88.0, 52.0, -41.0, 45.0, 80.0]))
    enviada = c.robot.acciones[-1]
    assert set(enviada) == set(CLAVES_ACCION)
    assert enviada["wrist_roll.pos"] == 0.0 and enviada["gripper.pos"] == 0.0
    assert enviada["shoulder_pan.pos"] == 12.0
    c.enviar(np.array([60.0, -90.0, 50.0, -40.0, 0.0, 0.0]))  # salto de 50°: LeRobot lo deja en 5
    assert c.ultima_enviada[0] == pytest.approx(15.0)


def test_q_imagenes_y_ajustes(cuerpo_real):
    c = cuerpo_real
    assert np.allclose(c.q(), [10.0, -90.0, 50.0, -40.0, 0.0, 0.0])
    imgs = c.imagenes()
    assert set(imgs) == {"top", "wrist"}
    assert all(i.shape == (480, 640, 3) for i in imgs.values())  # la de 1280×720 se reduce
    assert sorted(c.ajustes_aplicados) == [0, 2]


def test_aspirar_y_cerrar(cuerpo_real):
    c = cuerpo_real
    c.aspirar(True)
    time.sleep(0.12)
    assert b"1\n" in c.serie.lineas()
    robot = c.robot
    c.cerrar()
    assert c.serie.lineas()[-1] == b"0\n" and c.serie.cerrada
    assert q_desde_lerobot(robot.acciones[-1])[0] == pytest.approx(10.0)  # quieto: objetivo = postura actual
    assert not robot.conectado


# --- ajustes de cámara ---------------------------------------------------------------------------------------------
LISTA_NUEVA = """
User Controls
                     brightness 0x00980900 (int)    : min=0 max=255 step=1 default=128 value=128
        white_balance_automatic 0x0098090c (bool)   : default=1 value=1
      white_balance_temperature 0x0098091a (int)    : min=2000 max=6500 step=1 default=4000 value=4000 flags=inactive
Camera Controls
                  auto_exposure 0x009a0901 (menu)   : min=0 max=3 default=3 value=3 (Aperture Priority Mode)
         exposure_time_absolute 0x009a0902 (int)    : min=3 max=2047 step=1 default=250 value=250 flags=inactive
                 focus_absolute 0x009a090a (int)    : min=0 max=250 step=5 default=0 value=0 flags=inactive
     focus_automatic_continuous 0x009a090c (bool)   : default=1 value=1
"""
LISTA_VIEJA = """
 white_balance_temperature_auto 0x0098090c (bool)   : default=1 value=1
      white_balance_temperature 0x0098091a (int)    : min=2000 max=6500 step=1 default=4000 value=4000
                  exposure_auto 0x009a0901 (menu)   : min=0 max=3 default=3 value=3
              exposure_absolute 0x009a0902 (int)    : min=3 max=2047 step=1 default=250 value=250
"""


def test_ordenes_v4l2():
    aj = AjustesCamara(exposicion_ms=15.6, balance_k=4500, foco=10)
    nuevas = ordenes_v4l2(controles_v4l2(LISTA_NUEVA), aj)
    assert nuevas == ["auto_exposure=1", "exposure_time_absolute=156", "white_balance_automatic=0",
                      "white_balance_temperature=4500", "focus_automatic_continuous=0", "focus_absolute=10"]
    viejas = ordenes_v4l2(controles_v4l2(LISTA_VIEJA), aj)  # sin foco: la cámara no lo tiene
    assert viejas == ["exposure_auto=1", "exposure_absolute=156", "white_balance_temperature_auto=0",
                      "white_balance_temperature=4500"]


def test_fijar_ajustes_linux_con_v4l2ctl_falso():
    llamadas = []

    class R:
        stdout, returncode, stderr = LISTA_NUEVA, 0, ""

    def ejecutar(cmd, **kw):
        llamadas.append(cmd)
        return R()

    hechas = real.fijar_ajustes_linux("/dev/video0", AjustesCamara(), ejecutar)
    assert llamadas[0] == ["v4l2-ctl", "-d", "/dev/video0", "--list-ctrls"]
    assert [c[-1] for c in llamadas[1:]] == [f"--set-ctrl={h}" for h in hechas]
    assert real.dispositivo_linux(3) == "/dev/video3"


def test_fijar_ajustes_cv2():
    import cv2

    class Captura:
        def __init__(self):
            self.props = {}

        def set(self, p, v):
            self.props[p] = v
            return True

    cap = Captura()
    hechos = fijar_ajustes_cv2(cap, AjustesCamara(exposicion_ms=15.6, balance_k=4000, foco=0))
    assert all(hechos.values())
    assert cap.props[cv2.CAP_PROP_AUTO_WB] == 0 and cap.props[cv2.CAP_PROP_AUTOFOCUS] == 0
    assert cap.props[cv2.CAP_PROP_EXPOSURE] == -6.0 and cap.props[cv2.CAP_PROP_WB_TEMPERATURE] == 4000


# --- CuerpoSim -----------------------------------------------------------------------------------------------------
@pytest.fixture(scope="module")
def mundo_lateral():
    try:
        from garbi.mundo import MundoGarbi
    except Exception as e:  # MuJoCo sin la plataforma OpenGL pedida (p. ej. MUJOCO_GL=egl sin EGL)
        pytest.skip(f"MuJoCo no carga aquí: {e}")

    m = MundoGarbi(render=False, montaje="lateral")
    m.reset(semilla=0)
    return m


def test_cuerpo_sim_cumple_el_contrato(mundo_lateral, monkeypatch):
    m = mundo_lateral
    monkeypatch.setattr(m, "imagen", lambda cam, res: np.zeros((res[1], res[0], 3), np.uint8) + len(cam))
    c = CuerpoSim(m, max_relative_target=5.0)
    for metodo in ("q", "enviar", "aspirar", "imagenes"):
        assert callable(getattr(c, metodo)) and hasattr(Cuerpo, metodo)
    q0 = c.q()
    assert q0.shape == (6,)
    imgs = c.imagenes()
    assert set(imgs) == {"top", "wrist"} and all(i.shape == (480, 640, 3) for i in imgs.values())
    t0 = m.t
    c.enviar(q0 + np.array([20.0, 0, 0, 0, 30, 30]))
    assert m.t == pytest.approx(t0 + 1 / 30)
    assert c.ultima_enviada[0] == pytest.approx(q0[0] + 5.0)  # recortado
    assert c.ultima_enviada[4] == 0.0 and c.ultima_enviada[5] == pytest.approx(max(0.0, q0[5] - 5.0))
    c.aspirar(True)
    assert m.aspiradora
    c.aspirar(False)
    assert not m.aspiradora


class CicloAparcado:
    """Doble del ciclo para el juez: siempre aparcado (el juez no espera)."""

    def __init__(self):
        from garbi.ciclo import Estado

        self.estado = Estado.APARCADO
        self.agujeros = []
        self.control = None
        self.pasadas = 0

    def pasada_final(self):
        self.pasadas += 1


def test_juez_sim_y_escena_verdad(mundo_lateral):
    from garbi.ciclo import escena_verdad

    m = mundo_lateral
    m.reset(semilla=1, tabla=g.PoseTabla(360.0, 0.0, 0.0))
    ciclo = CicloAparcado()
    juez = JuezSim(m, ciclo, sitios=[(-20.0, 40.0)])
    vistas = []
    for k in range(int(20 * 30)):
        t = k / 30
        juez.paso(t)
        vistas.append(escena_verdad(m, t))
    assert any(e.taladro.visible and not e.broca.apoyada for e in vistas)  # buscando en el aire
    assert any(e.broca.apoyada and e.taladro.quieto_desde is not None and e.taladro.en_zona for e in vistas)
    assert len(m.juez.agujeros) == 1 and vistas[-1].viruta[0] > 0
    assert not vistas[-1].taladro.visible  # retirado tras taladrar
    assert len(juez.resultados) == 1 and ciclo.pasadas == 1  # cerró el agujero y pidió la pasada final


# --- registro ------------------------------------------------------------------------------------------------------
def test_registro_escribe_jsonl(tmp_path):
    reg = RegistroCiclos(tmp_path / "registros", reloj=lambda: datetime(2026, 11, 19, 10, 30))
    reg.anotar(ResumenCiclo(acierto=True, viruta_antes=np.int64(400), viruta_despues=3, duracion=21.5))
    ruta = reg.anotar({"acierto": False, "viruta_antes": 300, "viruta_despues": 90, "duracion": 30.0,
                       "motivo_fallo": "queda viruta"})
    assert ruta.name == "20261119.jsonl"
    filas = [json.loads(linea) for linea in ruta.read_text(encoding="utf-8").splitlines()]
    assert len(filas) == 2 and filas[0]["acierto"] and filas[0]["viruta_antes"] == 400
    assert filas[1]["motivo_fallo"] == "queda viruta" and filas[1]["hora"] == "2026-11-19T10:30:00"


def test_detector_de_ciclos(tmp_path):
    reloj = iter(range(100)).__next__
    reg = RegistroCiclos(tmp_path, reloj=lambda: datetime(2026, 11, 19))
    det = DetectorCiclos(reg, modo="sim", reloj=lambda: float(reloj()))
    q = np.zeros(6)
    pasos = [("APARCADO", {}), ("SEGUIR", {}), ("ACOMPAÑAR", {0: 0}), ("LIMPIAR", {0: 500}), ("REVISAR", {0: 5}),
             ("APARCADO", {0: 5}),
             ("SEGUIR", {0: 5}), ("LIMPIAR", {0: 5, 1: 300}), ("APARCADO", {0: 5, 1: 80})]
    cerrados = [det.paso(Escena(t=0, viruta=v), Orden(q, False, e)) for e, v in pasos]
    r1, r2 = cerrados[5], cerrados[8]
    assert r1.acierto and r1.viruta_antes == 500 and r1.viruta_despues == 5 and r1.motivo_fallo is None
    assert r1.estados == ["seguir", "acompanar", "limpiar", "revisar", "aparcado"]
    assert not r2.acierto and "agujero 1" in r2.motivo_fallo and r2.agujeros == 2
    assert len((tmp_path / "20261119.jsonl").read_text().splitlines()) == 2
    assert normalizar_estado("Ir a limpiar") == "ir_a_limpiar"


# --- bucle y argumentos --------------------------------------------------------------------------------------------
class CuerpoDoble:
    def __init__(self):
        self.aspira, self.enviadas, self.quietos = [], [], 0

    def q(self):
        return np.zeros(6)

    def enviar(self, q):
        self.enviadas.append(np.asarray(q))

    def aspirar(self, b):
        self.aspira.append(b)

    def imagenes(self):
        return {"top": np.zeros((480, 640, 3), np.uint8), "wrist": np.zeros((480, 640, 3), np.uint8)}

    def quieto(self):
        self.quietos += 1


class CicloDoble:
    def __init__(self, cortar_en=None):
        self.n, self.cortar_en, self.obs = 0, cortar_en, None

    def paso(self, escena, obs):
        self.n += 1
        self.obs = obs
        if self.n == self.cortar_en:
            raise KeyboardInterrupt
        return Orden(np.ones(6), True, "acompañar")


def test_bucle_ctrl_c_para_limpio():
    cuerpo, ciclo = CuerpoDoble(), CicloDoble(cortar_en=4)
    reloj = iter(np.arange(0, 100, 1 / 30)).__next__
    pasos = bucle(cuerpo, lambda imgs, q, t: Escena(t=t), ciclo, reloj=reloj, dormir=lambda s: None)
    assert pasos == 3 and cuerpo.aspira[-1] is False and cuerpo.quietos == 1
    assert set(ciclo.obs) == {"top", "wrist", "state"}


def test_bucle_a_30_hz():
    cuerpo, ciclo = CuerpoDoble(), CicloDoble()
    ahora = [0.0]
    dormido = []

    def dormir(s):
        dormido.append(s)
        ahora[0] += s

    pasos = bucle(cuerpo, lambda imgs, q, t: Escena(t=t, taladro=Taladro(False)), ciclo, segundos=1.0,
                  reloj=lambda: ahora[0], dormir=dormir)
    assert pasos == 30 and np.allclose(dormido, 1 / 30)
    assert cuerpo.aspira[-1] is False and len(cuerpo.enviadas) == 30


def test_argumentos():
    ns = argumentos(["--real", "--puerto", "COM5", "--aspiradora", "COM7"])
    assert ns.real and ns.puerto == "COM5" and ns.aspiradora == "COM7"
    assert argumentos(["--sim", "--verdad"]).verdad
    with pytest.raises(SystemExit):
        argumentos(["--real"])
    with pytest.raises(SystemExit):
        argumentos([])
