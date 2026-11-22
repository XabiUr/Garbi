"""Pruebas de las herramientas del sitio (herramientas/garbi_*.py) con dobles: sin brazos, cámaras, ventanas ni serie."""
import json
import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "herramientas"))


def _mujoco_sin_render():
    """Estas pruebas no renderizan (solo usan la cinemática): si el backend de OpenGL que elige conftest (egl/osmesa)
    no se puede cargar en esta máquina, MuJoCo se importa con MUJOCO_GL=disable."""
    import os

    try:
        import mujoco  # noqa: F401
    except (AttributeError, ImportError, OSError):
        for nombre in [m for m in sys.modules if m.split(".")[0] in ("mujoco", "OpenGL")]:
            del sys.modules[nombre]
        os.environ["MUJOCO_GL"] = "disable"
        import mujoco  # noqa: F401


_mujoco_sin_render()

import garbi_ajustar_color as ajustar  # noqa: E402
import garbi_calibrar as calibrar  # noqa: E402
import garbi_camaras as camaras  # noqa: E402
import garbi_comun as comun  # noqa: E402
import garbi_probar_robot as probar  # noqa: E402
import garbi_teleop_grabar as teleop  # noqa: E402

from garbi import config_vision as cv  # noqa: E402
from garbi.tipos import ARTICULACIONES, Broca, Escena, TAREA_ACERCAMIENTO  # noqa: E402


# --- dobles --------------------------------------------------------------------------------------------------------
class CuerpoFalso:
    """Cuerpo que llega al instante a lo que se le manda (o con `retraso` grados de error)."""

    def __init__(self, q=None, retraso=0.0):
        self.posicion = np.array([0.0, -100.0, 60.0, -60.0, 0.0, 0.0]) if q is None else np.asarray(q, float)
        self.enviadas = []
        self.aspiradora = []
        self.retraso = retraso
        self.quietos = 0
        self.senal = object()
        self.cerrado = False

    def q(self):
        return self.posicion.copy()

    def enviar(self, q):
        q = np.asarray(q, float)
        self.enviadas.append(q.copy())
        self.posicion = q + self.retraso

    def aspirar(self, encendida):
        self.aspiradora.append(bool(encendida))

    def imagenes(self):
        return {"top": np.full((480, 640, 3), 100, np.uint8), "wrist": np.full((480, 640, 3), 50, np.uint8)}

    def quieto(self):
        self.quietos += 1

    def cerrar(self):
        self.cerrado = True


class LeaderFalso:
    """Imita `SO101Leader.get_action()`: muñeca girada y pinza abierta (el montaje forzado tiene que anularlas)."""

    def __init__(self):
        self.q = np.array([5.0, -20.0, 40.0, -30.0, 33.0, 60.0])

    def get_action(self):
        return {f"{n}.pos": float(v) for n, v in zip(ARTICULACIONES, self.q)}


class DatasetFalso:
    def __init__(self):
        self.buffer = []
        self.episodios = []
        self.limpiezas = 0
        self.finalizado = False

    @property
    def num_episodes(self):
        return len(self.episodios)

    def add_frame(self, frame):
        assert frame["task"] == TAREA_ACERCAMIENTO
        self.buffer.append(frame)

    def save_episode(self, *a, **k):
        self.episodios.append(self.buffer)
        self.buffer = []

    def clear_episode_buffer(self, *a, **k):
        self.limpiezas += 1
        self.buffer = []

    def finalize(self):
        self.finalizado = True


def escena(clavada):
    return None if clavada is None else Escena(t=0.0, broca=Broca(apoyada=clavada))


# --- argumentos ----------------------------------------------------------------------------------------------------
def test_argumentos_windows_y_linux():
    ns = teleop.argumentos(["--puerto", "COM5", "--leader", "COM6", "--top", "0", "--wrist", "2", "--repo-id", "u/d",
                            "--push", "--resolucion", "320x240"])
    assert (ns.puerto, ns.leader, ns.push, ns.resolucion, ns.corte) == ("COM5", "COM6", True, (320, 240), "manual")
    assert comun.camaras_desde(ns) == {"top": 0, "wrist": 2}
    ns = teleop.argumentos(["--puerto", "/dev/ttyACM0", "--leader", "/dev/ttyACM1", "--top", "/dev/video4",
                            "--wrist", "no", "--corte", "auto", "--tolerancia", "2", "--sin-ventana"])
    assert comun.camaras_desde(ns) == {"top": "/dev/video4"} and ns.tolerancia == 2.0
    with pytest.raises(SystemExit):
        teleop.argumentos(["--puerto", "COM5", "--leader", "COM6", "--sin-ventana"])  # manual sin teclas
    with pytest.raises(SystemExit):
        teleop.argumentos(["--puerto", "COM5", "--leader", "COM6", "--reanudar", "--sobrescribir"])

    ns = calibrar.argumentos(["--carpeta", "x", "robot", "--puerto", "COM5", "--top", "1", "--seguido"])
    assert (ns.paso, ns.carpeta, ns.puerto, ns.top, ns.seguido) == ("robot", "x", "COM5", "1", True)
    ns = calibrar.argumentos(["intrinsecas", "--camara", "wrist", "--indice", "1", "--tablero", "7x5"])
    assert calibrar._tablero(ns.tablero) == (7, 5) and ns.fotos == calibrar.FOTOS
    with pytest.raises(SystemExit):
        calibrar.argumentos(["robot"])  # falta --puerto

    ns = probar.argumentos(["--puerto", "COM5", "--solo-leer"])
    assert ns.solo_leer and ns.aspiradora is None and ns.id == "garbi"
    ns = camaras.argumentos(["--top", "1", "--wrist", "0", "--carpeta", "c"])
    assert comun.camaras_desde(ns) == {"top": 1, "wrist": 0}
    with pytest.raises(SystemExit):
        ajustar.argumentos([])  # hace falta --imagen o --camara
    ns = ajustar.argumentos(["--camara", "0", "--color", "piel"])
    assert ns.color == "piel"


def test_ayudas_en_los_scripts():
    for modulo in (teleop, calibrar, probar, camaras, ajustar):
        with pytest.raises(SystemExit) as e:
            modulo.argumentos(["--help"])
        assert e.value.code == 0


# --- config de la visión -------------------------------------------------------------------------------------------
def test_yaml_de_colores_ida_y_vuelta(tmp_path):
    ruta = tmp_path / "config_vision.yaml"
    assert set(cv.cargar_config_vision(ruta)) == set(cv.COLORES)  # sin archivo: valores de partida
    rangos = cv.cargar_config_vision(ruta)
    rangos["bola_naranja"] = cv.RangoHSV((3, 120, 90), (25, 255, 255), "probada")
    cv.guardar_config_vision(rangos, ruta)
    texto = ruta.read_text(encoding="utf-8")
    assert texto.startswith("# Umbrales") and "bola_naranja" in texto
    leidos = cv.cargar_config_vision(ruta)
    assert leidos["bola_naranja"].bajo == (3, 120, 90) and leidos["bola_naranja"].nota == "probada"
    # un color que falte toma el de partida; uno desconocido se ignora
    ruta.write_text("version: 1\ncolores:\n  piel: {bajo: [170, 30, 60], alto: [15, 170, 255]}\n  raro: {bajo: [0,0,0], "
                    "alto: [1,1,1]}\n", encoding="utf-8")
    leidos = cv.cargar_config_vision(ruta)
    assert leidos["piel"].da_la_vuelta and leidos["tapete_azul"].bajo == cv.POR_DEFECTO["tapete_azul"].bajo
    assert "raro" not in leidos


def test_el_yaml_del_repositorio_es_valido():
    rangos = cv.cargar_config_vision()
    assert set(rangos) == set(cv.COLORES)
    assert rangos["anillo_verde"].bajo == (40, 80, 25)


def test_mascara_con_vuelta_del_tono():
    hsv = np.array([[[175, 100, 100], [5, 100, 100], [90, 100, 100]]], np.uint8)
    m = cv.mascara_hsv(hsv, cv.RangoHSV((170, 50, 50), (10, 255, 255)))
    assert m.tolist() == [[255, 255, 0]]
    m = cv.mascara_hsv(hsv, cv.RangoHSV((80, 50, 50), (100, 255, 255)))
    assert m.tolist() == [[0, 0, 255]]


def test_rango_desde_muestra_circular():
    r = cv.rango_desde_muestra(np.array([[178, 150, 150], [2, 160, 160], [0, 140, 140]]))
    assert r.da_la_vuelta  # el rojo cruza 0
    hsv = np.array([[[179, 150, 150], [1, 150, 150], [90, 150, 150]]], np.uint8)
    assert cv.mascara_hsv(hsv, r).tolist() == [[255, 255, 0]]
    r = cv.rango_desde_muestra(np.array([[60, 200, 200]] * 5))
    assert r.bajo[0] < 60 < r.alto[0] and not r.da_la_vuelta


def test_aplicar_a_percepcion(monkeypatch):
    from garbi import calibracion, percepcion

    monkeypatch.setattr(percepcion, "NARANJA_BAJO", percepcion.NARANJA_BAJO)
    monkeypatch.setattr(percepcion, "NARANJA_ALTO", percepcion.NARANJA_ALTO)
    monkeypatch.setattr(percepcion, "AZUL_BAJO", percepcion.AZUL_BAJO)
    monkeypatch.setattr(percepcion, "AZUL_ALTO", percepcion.AZUL_ALTO)
    monkeypatch.setattr(calibracion, "VERDE_BAJO", calibracion.VERDE_BAJO)
    monkeypatch.setattr(calibracion, "VERDE_ALTO", calibracion.VERDE_ALTO)
    rangos = cv.copia_por_defecto()
    rangos["bola_naranja"] = cv.RangoHSV((1, 2, 3), (20, 250, 250))
    rangos["tapete_azul"] = cv.RangoHSV((170, 2, 3), (10, 250, 250))  # da la vuelta: no se aplica
    hechos = cv.aplicar_a_percepcion(rangos)
    assert percepcion.NARANJA_BAJO == (1, 2, 3) and "garbi.percepcion.NARANJA_BAJO" in hechos
    assert "garbi.percepcion.AZUL_BAJO" not in hechos
    assert "garbi.calibracion.VERDE_ALTO" in hechos


def test_ajuste_de_color_sin_ventanas(tmp_path):
    ruta = tmp_path / "c.yaml"
    a = ajustar.Ajuste(cv.cargar_config_vision(ruta), ruta, "bola_naranja")
    assert not a.poner_valores(a.valores())
    assert a.poner_valores((1, 30, 100, 255, 90, 255)) and a.sin_guardar
    assert a.rango.bajo == (1, 100, 90) and a.rango.alto == (30, 255, 255)
    hsv = np.zeros((20, 20, 3), np.uint8)
    hsv[...] = (60, 200, 200)
    a.cambiar_color(1)
    assert a.color == "anillo_verde"
    r = a.pinchar(hsv, 10, 10)
    assert r.bajo[0] < 60 < r.alto[0]
    a.guardar()
    assert not a.sin_guardar
    leidos = cv.cargar_config_vision(ruta)
    assert leidos["bola_naranja"].bajo == (1, 100, 90) and leidos["anillo_verde"].bajo == r.bajo
    a.deshacer()
    assert a.rango.bajo == cv.POR_DEFECTO["anillo_verde"].bajo
    assert a.vista(np.zeros((480, 640, 3), np.uint8)).shape == (480, 1280, 3)


# --- mover despacio y probar el robot ------------------------------------------------------------------------------
def test_rampa_lenta_y_montaje_forzado():
    pasos = comun.rampa([0, 0, 0, 0, 40, 80], [30, 0, 0, 0, -50, 10], velocidad=15.0, hz=30.0)
    assert len(pasos) == 60  # 30° a 0,5° por paso
    d = np.diff(np.array([np.zeros(6)] + pasos), axis=0)
    assert np.abs(d[:, :4]).max() <= 0.5 + 1e-9
    assert all(p[4] == 0 and p[5] == 0 for p in pasos)


def test_mover_despacio_llega_y_para_con_ctrl_c():
    c = CuerpoFalso()
    err = comun.mover_despacio(c, [10, -90, 60, -60, 0, 0], velocidad=30, dormir=lambda s: None)
    assert err < 1e-6 and np.allclose(c.q()[:2], [10, -90])

    class Interrumpe(CuerpoFalso):
        def enviar(self, q):
            super().enviar(q)
            if len(self.enviadas) == 3:
                raise KeyboardInterrupt

    c = Interrumpe()
    with pytest.raises(KeyboardInterrupt):
        comun.mover_despacio(c, [40, -90, 60, -60, 0, 0], dormir=lambda s: None)
    assert c.quietos == 1


def test_mover_despacio_avisa_si_no_llega():
    c = CuerpoFalso(retraso=5.0)
    reloj = iter(np.arange(0, 100, 0.5))
    err = comun.mover_despacio(c, [0, -100, 60, -60, 0, 0], dormir=lambda s: None, reloj=lambda: next(reloj))
    assert err == pytest.approx(5.0)


def test_probar_robot_con_dobles():
    c = CuerpoFalso()
    ns = probar.argumentos(["--puerto", "COM5", "--velocidad", "90"])
    errores = probar.probar(c, ns, entrada=lambda s: "", dormir=lambda s: None)
    assert list(errores) == ["APARCADO", "aparcado girado +20°", "aparcado girado −20°",
                             "boca a 60 mm sobre el centro del tapete", "APARCADO (vuelta)"]
    assert c.aspiradora == [True, False]
    assert all(e[4] == 0 and e[5] == 0 for e in c.enviadas)
    # «n» salta todo; --solo-leer no mueve
    c = CuerpoFalso()
    assert probar.probar(c, ns, entrada=lambda s: "n", dormir=lambda s: None) == {} and not c.enviadas
    ns = probar.argumentos(["--puerto", "COM5", "--solo-leer"])
    c = CuerpoFalso()
    probar.probar(c, ns, entrada=lambda s: "", dormir=lambda s: None)
    assert not c.enviadas


# --- teleoperación y corte de episodios ----------------------------------------------------------------------------
def nuevo_teleop(corte_auto=None, min_s=0.0, max_s=40.0, estado="orden"):
    ds = DatasetFalso()
    g = teleop.GrabadorAcercamiento(ds, None, (64, 48), min_segundos=min_s, max_segundos=max_s)
    c = CuerpoFalso()
    return teleop.Teleop(LeaderFalso(), c, g, corte_auto, None, estado), ds, c


def test_teleop_montaje_forzado_y_estado():
    t, ds, c = nuevo_teleop()
    t.paso(0.0)  # sin grabar: solo mueve
    assert np.allclose(c.enviadas[-1], [5, -20, 40, -30, 0, 0])
    t.paso(0.033, ord(" "))
    t.leader.q = t.leader.q + np.array([1.0, 0, 0, 0, 10, 10])
    t.paso(0.066)
    t.paso(0.1, ord(" "))
    assert len(ds.episodios) == 1
    ep = ds.episodios[0]
    acciones = np.array([f["action"] for f in ep])
    assert np.all(acciones[:, 4:] == 0)  # muñeca a 0 y pinza cerrada aunque el leader las mueva
    assert ep[0]["observation.images.top"].shape == (48, 64, 3)
    # state = orden anterior: el del 2.º fotograma es la acción del 1.º
    assert np.allclose(ep[1]["observation.state"], ep[0]["action"])
    assert np.allclose(ep[1]["action"][0], 6.0)
    assert c.aspiradora == [True, False]


def test_teleop_estado_medido():
    t, ds, c = nuevo_teleop(estado="medido")
    c.retraso = 1.0
    t.paso(0.0, ord(" "))
    t.paso(0.033, ord(" "))
    assert np.allclose(ds.episodios[0][0]["observation.state"], np.array([5, -20, 40, -30, 0, 0]) + 1.0)


def test_corte_manual_repetir_y_salir(tmp_path):
    ds = DatasetFalso()
    tmp_path.mkdir(exist_ok=True)
    g = teleop.GrabadorAcercamiento(ds, tmp_path, (64, 48), min_segundos=0.0)
    t = teleop.Teleop(LeaderFalso(), CuerpoFalso(), g)
    t.paso(0, ord(" "))
    t.paso(0.03)
    t.paso(0.06, ord("r"))  # descarta
    assert ds.limpiezas == 1 and not ds.episodios and not g.grabando
    t.paso(0.1, ord(" "))
    t.paso(0.13)
    t.paso(0.16, ord(" "))
    assert len(ds.episodios) == 1 and len(ds.episodios[0]) == 2
    assert t.paso(0.2, ord("q")) is False
    datos = json.loads((tmp_path / teleop.ARCHIVO_EPISODIOS).read_text(encoding="utf-8"))
    assert (datos["guardados"], datos["descartados"]) == (1, 1)
    assert datos["motivos_descarte"] == {"repetido": 1}
    # al reanudar se siguen contando los de antes
    g2 = teleop.GrabadorAcercamiento(DatasetFalso(), tmp_path, (64, 48))
    assert (g2.guardados, g2.descartados) == (1, 1)


def test_corte_manual_eventos():
    m = teleop.CorteManual()
    assert m.evento(ord(" "), False) == teleop.EMPEZAR
    assert m.evento(ord(" "), True) == teleop.TERMINAR
    assert m.evento(ord("r"), False) is None and m.evento(ord("r"), True) == teleop.REPETIR
    assert m.evento(27, False) == teleop.SALIR and m.evento(-1, False) is None and m.evento(None, True) is None


def test_corte_automatico_sin_tolerancia():
    corte = teleop.CorteAcercamiento(0.0)
    t, ds, c = nuevo_teleop(corte)
    secuencia = [None, False, False, True, True, True, False, False]
    for k, clavada in enumerate(secuencia):
        t.escena = escena(clavada)
        t.percepcion = None  # la escena la ponemos a mano
        ev = corte.evento(k / 30, t.escena, t.grabador.grabando)
        t._aplicar(ev, k / 30)
        if t.grabador.grabando:
            t.grabador.fotograma(c.imagenes(), np.zeros(6), np.zeros(6))
    assert len(ds.episodios) == 1 and len(ds.episodios[0]) == 3  # los 3 fotogramas con la broca clavada
    assert c.aspiradora == [True, False]


def test_corte_automatico_no_empieza_si_ya_estaba_clavada():
    corte = teleop.CorteAcercamiento()
    assert corte.evento(0.0, escena(True), False) is None
    assert corte.evento(0.1, escena(True), False) is None
    assert corte.evento(0.2, escena(False), False) is None
    assert corte.evento(0.3, escena(True), False) == teleop.EMPEZAR
    assert corte.evento(0.4, None, True) is None  # sin percepción no decide


def test_corte_automatico_con_recuperacion():
    """Broca levantada menos que la tolerancia (la mueven a otro punto): el episodio sigue con esos fotogramas. Al
    final, levantada más que la tolerancia: se corta donde se levantó y lo de después se tira."""
    corte = teleop.CorteAcercamiento(tolerancia=0.2)
    t, ds, c = nuevo_teleop(corte)

    def paso(k, clavada):
        tt = k / 30
        t._aplicar(corte.evento(tt, escena(clavada), t.grabador.grabando), tt)
        if t.grabador.grabando:
            t.grabador.fotograma(c.imagenes(), np.zeros(6), np.full(6, k, float))

    estados = [False] + [True] * 5 + [False] * 3 + [True] * 4 + [False] * 10
    for k, clavada in enumerate(estados):
        paso(k, clavada)
    assert len(ds.episodios) == 1
    acciones = [int(f["action"][0]) for f in ds.episodios[0]]
    assert acciones == list(range(1, 13))  # 5 clavada + 3 levantada (recuperación) + 4 clavada; nada después
    assert not t.grabador.grabando and c.aspiradora == [True, False]


class PartidaFalsa:
    """Postura prudente fija y diferencia con ella (sin percepción)."""

    tolerancia = 8.0

    def __init__(self, q):
        self.q = np.asarray(q, float)

    def postura(self, escena):
        return self.q

    def diferencia(self, escena, q):
        return float(np.max(np.abs(np.asarray(q, float)[:4] - self.q[:4])))


def test_teleop_partida_prudente_enganche_y_condicion():
    """p: el follower va a la prudente y se queda ahí hasta que el leader está igual (enganche); un episodio solo
    empieza si el follower está cerca de la postura prudente."""
    prudente = np.array([20.0, -10.0, 30.0, -20.0, 0.0, 0.0])
    ds = DatasetFalso()
    g = teleop.GrabadorAcercamiento(ds, None, (64, 48), min_segundos=0.0)
    c = CuerpoFalso()
    movidas = []

    def mover(cuerpo, q):
        movidas.append(q)
        cuerpo.enviar(q)

    t = teleop.Teleop(LeaderFalso(), c, g, None, None, "orden", PartidaFalsa(prudente), mover)
    t.paso(0.0, ord(" "))  # lejos de la prudente: no empieza
    assert not g.grabando and "postura prudente" in t.aviso_partida
    t.paso(0.03, ord("p"))
    assert movidas and t.enganche is not None
    assert np.allclose(c.enviadas[-1], prudente)  # el follower se queda en la prudente aunque el leader esté lejos
    t.paso(0.06, ord(" "))  # sin enganchar: no empieza
    assert not g.grabando
    t.leader.q = prudente + np.array([2.0, 0, 0, 0, 0, 0])  # el operador pone el leader igual
    t.paso(0.1)
    assert t.enganche is None and np.allclose(c.enviadas[-1][:4], t.leader.q[:4])
    t.paso(0.13, ord(" "))
    assert g.grabando


def test_teleop_sin_agarre():
    ns = teleop.argumentos(["--puerto", "COM5", "--leader", "COM6", "--corte", "auto", "--sin-agarre"])
    assert ns.sin_agarre and ns.partida == "prudente"
    corte = teleop.cortador_automatico(0.0, exigir_agarre=False)
    assert corte.exigir_agarre is False and teleop.cortador_automatico(0.0).exigir_agarre is True
    ns = teleop.argumentos(["--puerto", "COM5", "--leader", "COM6", "--corte", "auto", "--sin-ventana"])
    assert ns.partida == "libre"


def test_episodios_demasiado_cortos_o_largos():
    t, ds, c = nuevo_teleop(min_s=0.1, max_s=0.2)  # 3 y 6 fotogramas a 30 Hz
    t.paso(0, ord(" "))
    t.paso(0.03, ord(" "))
    assert not ds.episodios and t.grabador.episodios[-1]["motivo"].startswith("demasiado corto")
    t.paso(0.1, ord(" "))
    for k in range(10):
        t.paso(0.2 + k / 30)
    assert not t.grabador.grabando and t.grabador.episodios[-1]["motivo"] == "demasiado largo"
    assert c.aspiradora[-1] is False and not ds.episodios


def test_grabador_cerrar_descarta_el_episodio_en_curso():
    ds = DatasetFalso()
    g = teleop.GrabadorAcercamiento(ds, None, (64, 48), min_segundos=0)
    g.empezar()
    g.fotograma({"top": np.zeros((480, 640, 3), np.uint8), "wrist": np.zeros((480, 640, 3), np.uint8)},
                np.zeros(6), np.zeros(6))
    r = g.cerrar()
    assert ds.finalizado and r["descartados"] == 1 and r["episodios"][0]["motivo"] == "cortado al salir"


def test_grabador_con_lerobot_dataset_de_verdad(tmp_path):
    """Un episodio pequeño en un LeRobotDataset real (64 × 48) y reanudar para añadir otro."""
    salida = tmp_path / "ds"
    ds = teleop.crear_dataset(salida, "local/prueba_acercamiento", (64, 48))
    g = teleop.GrabadorAcercamiento(ds, salida, (64, 48), min_segundos=0)
    imgs = {"top": np.zeros((480, 640, 3), np.uint8), "wrist": np.full((480, 640, 3), 200, np.uint8)}
    g.empezar()
    for k in range(5):
        g.fotograma(imgs, np.zeros(6), np.full(6, k, float))
    assert g.terminar(True)["guardado"]
    g.cerrar()
    ds2 = teleop.crear_dataset(salida, "local/prueba_acercamiento", (64, 48), reanudar=True)
    g2 = teleop.GrabadorAcercamiento(ds2, salida, (64, 48), min_segundos=0)
    g2.empezar()
    for k in range(4):
        g2.fotograma(imgs, np.zeros(6), np.zeros(6))
    assert g2.terminar(True)["episodio_dataset"] == 1
    g2.cerrar()
    from lerobot.datasets.lerobot_dataset import LeRobotDataset

    leido = LeRobotDataset("local/prueba_acercamiento", root=salida)
    assert leido.num_episodes == 2 and leido.num_frames == 9
    assert leido[0]["task"] == TAREA_ACERCAMIENTO
    with pytest.raises(SystemExit):
        teleop.crear_dataset(salida, "local/prueba_acercamiento", (64, 48))  # ya existe


# --- calibración ---------------------------------------------------------------------------------------------------
def tablero_sintetico(tablero=(9, 6), lado_px=30):
    c, f = tablero[0] + 1, tablero[1] + 1
    img = np.full(((f + 2) * lado_px, (c + 2) * lado_px), 255, np.uint8)
    for i in range(f):
        for j in range(c):
            if (i + j) % 2 == 0:
                img[(i + 1) * lado_px:(i + 2) * lado_px, (j + 1) * lado_px:(j + 2) * lado_px] = 0
    return img


def test_intrinsecas_con_tablero_sintetico(tmp_path):
    """Fotos del tablero hechas con una cámara conocida (K, sin distorsión): la calibración la recupera."""
    K = np.array([[600.0, 0, 320], [0, 600.0, 240], [0, 0, 1]])
    plano = tablero_sintetico()
    alto, ancho = plano.shape
    lado = 25.0 / 30  # mm por píxel del tablero plano (cuadros de 25 mm)
    imgs = []
    rng = np.random.default_rng(0)
    for _ in range(12):
        rvec = rng.uniform(-0.35, 0.35, 3)
        R, _ = cv2.Rodrigues(rvec)
        centro = R @ np.array([150.0, 112.0, 0.0])  # el centro del tablero (300 × 225 mm) cerca del eje óptico
        t = np.array([rng.uniform(-40, 40), rng.uniform(-30, 30), rng.uniform(480, 620)]) - centro
        # homografía del plano (mm) a la imagen: K [r1 r2 t] · escala del tablero
        H = K @ np.column_stack([R[:, 0], R[:, 1], t]) @ np.diag([lado, lado, 1.0])
        g = cv2.warpPerspective(plano, H, (640, 480), borderValue=255)
        imgs.append(cv2.cvtColor(g, cv2.COLOR_GRAY2RGB))
        cv2.imwrite(str(tmp_path / f"t{len(imgs):02d}.png"), g)
    Kc, dist, rms, usadas = calibrar.calibrar_intrinsecas(calibrar.leer_carpeta(tmp_path))
    assert usadas >= 10 and rms < 0.5
    assert abs(Kc[0, 0] - 600) < 15 and abs(Kc[0, 2] - 320) < 15


def test_guardar_y_cargar_calibracion(tmp_path):
    from garbi.calibracion import PoseBase
    from garbi.real import CorrectorDistorsion, cargar_calibracion, guardar_base, guardar_intrinsecas

    K = np.array([[610.0, 0, 321], [0, 612.0, 239], [0, 0, 1]])
    guardar_intrinsecas(tmp_path / "top.yaml", K, np.zeros(5), (640, 480), 0.21, 15)
    guardar_base(tmp_path / "robot.yaml", PoseBase(3.0, -2.0, 1.25), [0.5, 1.0], [1.0, np.inf])
    cal = cargar_calibracion(tmp_path)
    assert np.allclose(cal.K("top"), K) and cal.K("wrist") is None
    assert (cal.base.x, cal.base.y, cal.base.giro) == (3.0, -2.0, 1.25)
    img = np.random.default_rng(0).integers(0, 255, (480, 640, 3), dtype=np.uint8)
    assert np.array_equal(CorrectorDistorsion(K, np.zeros(5))(img), img)  # sin distorsión no toca nada
    con = CorrectorDistorsion(K, np.array([-0.2, 0.05, 0, 0, 0]))(img)
    assert con.shape == img.shape and not np.array_equal(con, img)
    assert cargar_calibracion(tmp_path / "no_existe").intrinsecas == {}


def test_crear_percepcion_real_usa_calib(tmp_path):
    from garbi.correr import crear_percepcion_real
    from garbi.calibracion import PoseBase
    from garbi.mundo import MundoGarbi
    from garbi.real import guardar_base, guardar_intrinsecas

    K = np.array([[555.0, 0, 320], [0, 555.0, 240], [0, 0, 1]])
    guardar_intrinsecas(tmp_path / "wrist.yaml", K, np.zeros(5))
    guardar_base(tmp_path / "robot.yaml", PoseBase(4.0, 1.0, 0.5))
    per = crear_percepcion_real(MundoGarbi(render=False, montaje="lateral").modelo, tmp_path)
    assert np.allclose(per.K_wrist, K) and per.cin.base.x == 4.0


def camara_nominal():
    from garbi import contrato as g
    from garbi.percepcion import FOVY_TOP, CamaraMesa, intrinsecas

    pos = np.array(g.CAMARA_FIJA_POS, float)
    z = np.array([320.0, 0.0, 0.0]) - pos
    z /= np.linalg.norm(z)
    x = np.cross(z, [0.0, 0.0, 1.0])
    x /= np.linalg.norm(x)
    y = np.cross(z, x)
    R = np.vstack([x, y, z])
    return CamaraMesa(intrinsecas(FOVY_TOP), R, -R @ pos)


class CuerpoEscena(CuerpoFalso):
    """Cuerpo que «ve» con la cámara de arriba nominal: tapete azul y el anillo verde donde lo pone la cinemática con
    una base desplazada (la que la calibración tiene que encontrar)."""

    def __init__(self, base):
        from garbi.calibracion import CinematicaRobot
        from garbi.mundo import MundoGarbi

        super().__init__()
        self.cam = camara_nominal()
        self.cin = CinematicaRobot(MundoGarbi(render=False, montaje="lateral").modelo, base)

    def imagenes(self):
        from garbi.escena import ANILLO_DIAMETRO
        from garbi.percepcion import Z_TAPETE, _poligono, esquinas_tapete_mesa

        img = np.full((480, 640, 3), (150, 140, 120), np.uint8)
        poli = _poligono(self.cam, esquinas_tapete_mesa(), Z_TAPETE)
        cv2.fillPoly(img, [np.round(poli * 16).astype(np.int32)], (30, 77, 180), cv2.LINE_AA, shift=4)
        p = self.cin.sitio(self.posicion, "anillo")
        uv = self.cam.proyectar(p)[0]
        r = self.cam.K[0, 0] * ANILLO_DIAMETRO / 2 / np.linalg.norm(self.cam.R @ p + self.cam.t)
        cv2.circle(img, (int(round(uv[0] * 16)), int(round(uv[1] * 16))), int(round(r * 16)), (120, 220, 40), -1,
                   cv2.LINE_AA, shift=4)
        return {"top": img, "wrist": np.zeros((480, 640, 3), np.uint8)}


def test_calibrar_robot_con_dobles(tmp_path):
    from garbi.calibracion import PoseBase
    from garbi.real import cargar_base

    verdad = PoseBase(6.0, -4.0, 1.5)
    cuerpo = CuerpoEscena(verdad)
    ns = calibrar.argumentos(["--carpeta", str(tmp_path), "robot", "--puerto", "COM5", "--velocidad", "200"])
    preguntas = []

    def entrada(texto):
        preguntas.append(texto)
        return ""

    r = calibrar.paso_robot(ns, fabrica_cuerpo=lambda ns, calib: cuerpo, entrada=entrada, dormir=lambda s: None)
    assert r is not None and r.vistas == 9
    # el anillo sintético es un disco plano y `calibrar_robot` corrige el centro con el modelo del anillo (la parte
    # tapada por la boquilla): eso deja ~5 mm de sesgo en la base, aquí sin importancia (se prueba el flujo)
    assert abs(r.base.x - verdad.x) < 8 and abs(r.base.y - verdad.y) < 8 and abs(r.base.giro - verdad.giro) < 1.5
    assert r.ok
    assert len(r.errores) == 5 and np.all(np.isfinite(r.errores))
    assert sum("¿Ir a" in p for p in preguntas) == 14  # Enter antes de cada postura
    assert cuerpo.cerrado and all(e[4] == 0 and e[5] == 0 for e in cuerpo.enviadas)
    base = cargar_base(tmp_path / "robot.yaml")
    assert abs(base.x - r.base.x) < 1e-2
    assert len(list((tmp_path / "robot").glob("postura_*.png"))) == 14
    assert any("comprobación 5" in linea for linea in calibrar.informe_robot(r))


def test_calibrar_robot_ctrl_c_deja_el_brazo_quieto(tmp_path):
    from garbi.calibracion import PoseBase

    cuerpo = CuerpoEscena(PoseBase())
    ns = calibrar.argumentos(["--carpeta", str(tmp_path), "robot", "--puerto", "COM5"])
    respuestas = iter(["", "", KeyboardInterrupt])

    def entrada(texto):
        r = next(respuestas)
        if r is KeyboardInterrupt:
            raise KeyboardInterrupt
        return r

    assert calibrar.paso_robot(ns, fabrica_cuerpo=lambda ns, c: cuerpo, entrada=entrada,
                               dormir=lambda s: None) is None
    assert cuerpo.quietos >= 1 and cuerpo.cerrado and not (tmp_path / "robot.yaml").exists()


def test_calibrar_arriba_con_imagen_sintetica():
    cuerpo = CuerpoEscena(None)
    cam, informe = calibrar.calibrar_arriba(cuerpo.imagenes()["top"], None)
    assert cam is not None and informe["desvio_nominal_mm"] < 10


# --- ventana de las cámaras (sin ventana: solo los dibujos) --------------------------------------------------------
def test_anotar_top_y_wrist():
    cuerpo = CuerpoEscena(None)
    img = cuerpo.imagenes()["top"].copy()
    cv2.circle(img, (400, 300), 12, (255, 120, 0), -1)  # bola naranja (RGB)
    estado = camaras.Estado(cv.cargar_config_vision())
    vista, lineas = camaras.anotar_top(img, estado)
    assert vista.shape == (480, 640, 3)
    assert estado.cam is not None  # calibró con el tapete
    assert any(linea.startswith("bola: (400, 300)") for linea in lineas)
    assert any(linea.startswith("anillo: (") for linea in lineas)
    estado.alternar_color(0)
    assert not estado.visibles["tapete_azul"]
    vista, lineas = camaras.anotar_wrist(np.zeros((480, 640, 3), np.uint8), estado)
    assert lineas == ["broca: NO"]
    estado.percepcion = False
    _, lineas = camaras.anotar_top(img, estado)
    assert "percepcion: apagada" in lineas


def test_guardar_captura(tmp_path):
    rutas = camaras.guardar_captura(tmp_path, {"top": np.zeros((48, 64, 3), np.uint8)})
    assert len(rutas) == 1 and rutas[0].name.startswith("top_") and rutas[0].exists()


def test_abrir_camaras_con_dobles():
    from garbi.real import abrir_camaras, cerrar_camaras

    class CamFalsa:
        def __init__(self, cfg):
            self.config = cfg
            self.index_or_path = cfg.index_or_path
            self.videocapture = self
            self.conectada = False

        def connect(self):
            self.conectada = True

        def disconnect(self):
            self.conectada = False

        def set(self, *a):
            return True

    import garbi.real as real

    real_fijar = real.fijar_ajustes_camara
    try:
        real.fijar_ajustes_camara = lambda cam, aj: None
        cams = abrir_camaras({"top": "0", "wrist": 2}, fabrica=CamFalsa)
    finally:
        real.fijar_ajustes_camara = real_fijar
    assert cams["top"].index_or_path == 0 and cams["top"].config.width == 640 and cams["top"].conectada
    cerrar_camaras(cams)
    assert not cams["wrist"].conectada
