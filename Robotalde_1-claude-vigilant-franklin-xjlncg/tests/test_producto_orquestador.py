"""Producto Garbi (P1): orquestador, matriz, barridos, políticas y configuración. Todo con dobles, sin hardware."""
import json
import logging

import numpy as np
import pytest

from garbi.producto.barridos import barrido_tabla, barrido_tapete, ordenar_esquinas, trayectoria_suave
from garbi.producto.config import ConfigProducto, cargar_config, config_desde_dict
from garbi.producto.contrato import Circulo, Comando, Estado, Vista
from garbi.producto.matriz import Matriz, cargar_matriz, detectar_rejilla
from garbi.producto.orquestador import Orquestador
from garbi.producto.politicas import PoliticaACT, PoliticaCirculo, crear_politica, mapear_camaras

HZ = 30.0
TABLA = np.array([[200, 150], [440, 150], [440, 330], [200, 330]], float)
UV_A = np.array([300.0, 240.0])


# --- dobles ----------------------------------------------------------------------------------------------------------
def rejilla_5x3(funcion=None, torcida=0.05):
    """15 puntos (5 columnas × 3 filas) algo torcidos, con posturas = funcion(u, v)."""
    funcion = funcion or (lambda u, v: [u / 10 - 30, -v / 10, 20 + u * v / 1e4, 10.0, 0.0, 0.0])
    P, Q = [], []
    for v in np.linspace(80, 400, 3):
        for u in np.linspace(80, 560, 5):
            P.append([u + torcida * v, v])
            Q.append(funcion(u + torcida * v, v))
    return np.array(P), np.array(Q)


def matriz_prueba():
    return Matriz(*rejilla_5x3())


class PoliticaDoble:
    """Va hacia un destino fijo a pasos de 2° y llega cuando está a menos de 0,5°."""

    def __init__(self, nombre="circulo", destino=None):
        self.nombre = nombre
        self.destino = np.array([10.0, -40.0, 50.0, 30.0, 5.0, 20.0]) if destino is None else destino
        self.reinicios = []
        self.q = None

    def reiniciar(self, vista, q):
        self.reinicios.append(np.asarray(q, float).copy())
        self.q = np.asarray(q, float).copy()

    def accion(self, obs, vista):
        self.q = self.q + np.clip(self.destino - self.q, -2, 2)
        return self.q.copy()

    def llegado(self):
        return np.max(np.abs(self.q - self.destino)) < 0.5


def config(**cambios):
    cfg = ConfigProducto()
    cfg.puertos.aspiradora = None
    for k, v in cambios.items():
        setattr(cfg, k, v)
    return cfg.validar()


class Mundo:
    """Robot doble (la postura sigue a la orden) y un bucle a 30 Hz con una escena dada por una función de t."""

    def __init__(self, orq, q0=None):
        self.orq = orq
        self.q = (orq.cfg.q_reposo if q0 is None else np.asarray(q0, float)).copy()
        self.t = 0.0
        self.ordenes = []

    def correr(self, escena, hasta: float):
        while self.t < hasta - 1e-9:
            v = escena(self.t)
            o = self.orq.paso(v, {"top": None, "wrist": None, "state": self.q.copy()})
            if o.q is not None:
                self.q = o.q.copy()
            self.ordenes.append(o)
            self.t += 1.0 / HZ
        return self.ordenes[-1]

    def estados(self):
        return [o.estado for o in self.ordenes]


def escena_taladro(uv=UV_A, quieto_desde=0.0, tabla=True, agarrado=True, manos=True):
    def f(t):
        c = Circulo(uv=np.asarray(uv, float), radio=10, quieto_desde=quieto_desde if quieto_desde is not None and t >= quieto_desde else None)
        return Vista(t=t, circulo=c, manos=[np.asarray(uv) + 20] if manos else [], taladro_agarrado=agarrado,
                     tabla=TABLA.copy() if tabla else None)
    return f


def escena_vacia(tabla=True, manos=False):
    return lambda t: Vista(t=t, tabla=TABLA.copy() if tabla else None, manos=[np.array([100.0, 100.0])] if manos else [])


def llevar_a_en_broca(cfg=None, politica=None):
    cfg = cfg or config()
    orq = Orquestador(cfg, politica or PoliticaDoble(), matriz_prueba())
    m = Mundo(orq)
    m.correr(escena_taladro(quieto_desde=0.0), 8.0)
    assert orq.estado == Estado.EN_BROCA
    return orq, m


# --- transiciones ------------------------------------------------------------------------------------------------------
def test_reposo_a_acercamiento_tras_1_s_quieto():
    orq = Orquestador(config(), PoliticaDoble(), matriz_prueba())
    m = Mundo(orq)
    m.correr(escena_taladro(quieto_desde=0.5), 1.45)
    assert orq.estado == Estado.REPOSO  # 0,95 s quieto: aún no
    m.correr(escena_taladro(quieto_desde=0.5), 1.6)
    assert orq.estado == Estado.ACERCAMIENTO
    assert any("quieto 1 s" in e for e in orq.eventos)


def test_mano_sola_o_taladro_suelto_no_despiertan():
    orq = Orquestador(config(), PoliticaDoble(), matriz_prueba())
    m = Mundo(orq)
    m.correr(escena_taladro(quieto_desde=0.0, agarrado=False), 4.0)
    assert set(m.estados()) == {Estado.REPOSO}


def test_en_broca_aspira_y_congela():
    orq, m = llevar_a_en_broca()
    o = m.ordenes[-1]
    assert o.aspirar and orq.aspiradora
    assert np.allclose(o.q[:4], orq.politica.destino[:4], atol=0.6)
    q_antes = o.q.copy()
    m.correr(escena_taladro(quieto_desde=0.0), 10.0)
    assert np.allclose(m.ordenes[-1].q, q_antes)
    assert orq.agujeros == 1 and orq.estado_app().agujeros == 1


def test_salida_por_rango_a_despierto():
    cfg = config()
    orq, m = llevar_a_en_broca(cfg)
    lejos = UV_A + np.array([cfg.tiempos.rango_salida_px * 0.8, 0.0])
    m.correr(escena_taladro(uv=lejos), 8.5)
    assert orq.estado == Estado.EN_BROCA  # dentro del rango sigue
    lejos = UV_A + np.array([cfg.tiempos.rango_salida_px * 1.3, 0.0])
    o = m.correr(escena_taladro(uv=lejos), 8.6)
    assert orq.estado == Estado.DESPIERTO and not o.aspirar


def test_salida_por_desaparicion_y_parpadeo():
    cfg = config()
    orq, m = llevar_a_en_broca(cfg)
    m.correr(escena_vacia(), 8.0 + cfg.tiempos.perdido * 0.5)
    assert orq.estado == Estado.EN_BROCA  # un parpadeo corto no lo saca
    m.correr(escena_taladro(quieto_desde=0.0), 9.0)
    m.correr(escena_vacia(), 9.0 + cfg.tiempos.perdido + 0.1)
    assert orq.estado == Estado.DESPIERTO


def test_desde_despierto_hacen_falta_2_s():
    cfg = config()
    orq, m = llevar_a_en_broca(cfg)
    m.correr(escena_vacia(), 10.0)
    assert orq.estado == Estado.DESPIERTO
    # vuelve el taladro, quieto desde 10,0: a 11,5 s (1,5 s) sigue despierto; a 12,1 s ya se acerca
    m.correr(escena_taladro(uv=UV_A + 30, quieto_desde=10.0), 11.5)
    assert orq.estado == Estado.DESPIERTO
    m.correr(escena_taladro(uv=UV_A + 30, quieto_desde=10.0), 12.1)
    assert orq.estado == Estado.ACERCAMIENTO
    assert any("2 s" in e for e in orq.eventos)


def test_despierto_va_a_su_postura_sin_aspirar():
    cfg = config()
    orq, m = llevar_a_en_broca(cfg)
    o = m.correr(escena_vacia(), 12.0)
    assert orq.estado == Estado.DESPIERTO and not o.aspirar
    assert np.allclose(o.q, cfg.q_despierto, atol=1e-6)


def test_act_desde_reposo_vuelve_a_reposo_primero():
    cfg = config(act_desde="reposo")
    pol = PoliticaDoble(nombre="act")
    orq, m = llevar_a_en_broca(cfg, pol)
    m.correr(escena_vacia(), 12.0)   # despierto, lejos del reposo
    m.correr(escena_taladro(uv=UV_A, quieto_desde=12.0), 14.1)
    assert orq.estado == Estado.ACERCAMIENTO
    assert any("reposo para lanzar ACT" in e for e in orq.eventos)
    m.correr(escena_taladro(uv=UV_A, quieto_desde=12.0), 25.0)
    assert len(pol.reinicios) == 2
    assert np.allclose(pol.reinicios[1], cfg.q_reposo, atol=cfg.tiempos.tolerancia_reposo)


def test_act_desde_despierto_lanza_directo():
    cfg = config(act_desde="despierto")
    pol = PoliticaDoble(nombre="act")
    orq, m = llevar_a_en_broca(cfg, pol)
    m.correr(escena_vacia(), 12.0)
    m.correr(escena_taladro(uv=UV_A, quieto_desde=12.0), 14.1)
    assert len(pol.reinicios) == 2
    assert np.allclose(pol.reinicios[1], cfg.q_despierto, atol=1e-6)


def test_acercamiento_abortado_si_se_va():
    cfg = config()
    pol = PoliticaDoble(destino=np.array([60.0, 0, 0, 0, 0, 0]))
    orq = Orquestador(cfg, pol, matriz_prueba())
    m = Mundo(orq)
    m.correr(escena_taladro(quieto_desde=0.0), 1.2)
    assert orq.estado == Estado.ACERCAMIENTO
    m.correr(escena_vacia(), 1.2 + cfg.tiempos.perdido + 0.1)
    assert orq.estado == Estado.DESPIERTO


def test_limpieza_tabla_tras_agujeros_y_vuelta_a_reposo_sin_manos():
    cfg = config()
    orq, m = llevar_a_en_broca(cfg)
    T = cfg.tiempos.sin_taladro_limpiar
    m.correr(escena_vacia(), 9.0)
    assert orq.estado == Estado.DESPIERTO
    m.correr(escena_vacia(), 9.0 + T - 0.5)
    assert orq.estado == Estado.DESPIERTO
    m.correr(escena_vacia(), 9.0 + T + 0.5)
    assert orq.estado == Estado.LIMPIEZA_TABLA and m.ordenes[-1].aspirar
    m.correr(escena_vacia(), 200.0)
    assert orq.estado == Estado.REPOSO and orq.agujeros_pendientes == 0
    i0 = m.estados().index(Estado.LIMPIEZA_TABLA)
    i1 = len(m.estados()) - m.estados()[::-1].index(Estado.LIMPIEZA_TABLA)
    assert all(o.aspirar for o in m.ordenes[i0:i1])
    assert any("Tabla limpia" in e for e in orq.eventos)


def test_limpieza_tabla_acaba_en_despierto_con_manos():
    orq, m = llevar_a_en_broca()
    m.correr(escena_vacia(manos=True), 200.0)
    assert Estado.LIMPIEZA_TABLA in m.estados() and orq.estado == Estado.DESPIERTO


def test_sin_agujeros_o_sin_tabla_no_limpia():
    # sin agujeros: de reposo no pasa
    orq = Orquestador(config(), PoliticaDoble(), matriz_prueba())
    m = Mundo(orq)
    m.correr(escena_vacia(), 20.0)
    assert set(m.estados()) == {Estado.REPOSO}
    # con agujero pero sin tabla nunca vista: despierto
    orq, m = llevar_a_en_broca()
    orq._hubo_tabla = False
    m.correr(escena_vacia(tabla=False), 30.0)
    assert Estado.LIMPIEZA_TABLA not in m.estados()


def test_taladro_suelto_encima_de_la_tabla_bloquea_la_limpieza():
    orq, m = llevar_a_en_broca()
    m.correr(escena_vacia(), 9.0)
    m.correr(escena_taladro(uv=UV_A, agarrado=False, manos=False), 30.0)
    assert orq.estado == Estado.DESPIERTO
    m.correr(escena_taladro(uv=[600.0, 50.0], agarrado=False, manos=False), 40.0)  # suelto fuera de la tabla
    assert Estado.LIMPIEZA_TABLA in m.estados()


def test_mano_y_taladro_interrumpen_la_limpieza():
    orq, m = llevar_a_en_broca()
    m.correr(escena_vacia(), 15.0)
    assert orq.estado == Estado.LIMPIEZA_TABLA
    m.correr(escena_taladro(uv=UV_A, quieto_desde=None), 15.1)
    assert orq.estado == Estado.DESPIERTO


def test_retirar_la_tabla_limpia_el_tapete_y_vuelve_a_reposo():
    cfg = config()
    orq = Orquestador(cfg, PoliticaDoble(), matriz_prueba())
    m = Mundo(orq)
    m.correr(escena_vacia(tabla=True), 2.0)
    m.correr(escena_vacia(tabla=False), 2.0 + cfg.tiempos.sin_tabla - 0.2)
    assert orq.estado == Estado.REPOSO
    m.correr(escena_vacia(tabla=False), 2.0 + cfg.tiempos.sin_tabla + 0.2)
    assert orq.estado == Estado.LIMPIEZA_TAPETE and m.ordenes[-1].aspirar
    m.correr(escena_vacia(tabla=False), 300.0)
    assert orq.estado == Estado.REPOSO
    assert m.estados().count(Estado.LIMPIEZA_TAPETE) > 30 * 10   # un barrido de verdad, no un instante
    assert any("tapete" in e.lower() for e in orq.eventos)


# --- comandos y emergencia ---------------------------------------------------------------------------------------------
def test_comandos_de_la_app():
    orq = Orquestador(config(), PoliticaDoble(), matriz_prueba())
    m = Mundo(orq)
    assert not orq.comando(Comando.LIMPIAR_TABLA)    # aún no ha visto la tabla
    m.correr(escena_vacia(), 1.0)
    assert orq.comando(Comando.APAGAR)
    o = m.correr(escena_taladro(quieto_desde=0.0), 3.0)
    assert orq.estado == Estado.APAGADO and o.q is None and not o.aspirar
    assert not orq.comando(Comando.LIMPIAR_TAPETE)
    assert orq.comando("encender") and orq.estado == Estado.REPOSO
    assert orq.comando(Comando.LIMPIAR_TABLA)
    m.correr(escena_vacia(), 4.0)
    assert orq.estado == Estado.LIMPIEZA_TABLA
    assert orq.comando(Comando.PARAR)
    o = m.correr(escena_vacia(), 4.1)
    assert orq.estado == Estado.REPOSO and not o.aspirar
    assert orq.comando(Comando.LIMPIAR_TAPETE)
    m.correr(escena_vacia(), 4.5)
    assert orq.estado == Estado.LIMPIEZA_TAPETE


def test_emergencia_tiene_prioridad_absoluta():
    orq, m = llevar_a_en_broca()
    assert orq.comando(Comando.EMERGENCIA)
    o = m.correr(escena_taladro(quieto_desde=0.0), 9.0)
    assert orq.estado == Estado.EMERGENCIA and o.q is None and not o.aspirar
    assert all(o.q is None and not o.aspirar for o in m.ordenes[-25:])
    for c in (Comando.ENCENDER, Comando.PARAR, Comando.LIMPIAR_TABLA, Comando.LIMPIAR_TAPETE, Comando.APAGAR):
        assert not orq.comando(c)
        assert orq.estado == Estado.EMERGENCIA
    m.correr(escena_vacia(tabla=False), 20.0)   # ni la tabla retirada ni nada lo saca
    assert orq.estado == Estado.EMERGENCIA
    assert orq.comando(Comando.REARMAR)
    o = m.correr(escena_vacia(tabla=False), 20.1)
    assert orq.estado in (Estado.REPOSO, Estado.LIMPIEZA_TAPETE) and o.q is not None
    assert orq.estado_app().estado == orq.estado


def test_rearmar_sin_emergencia_no_hace_nada():
    orq = Orquestador(config(), PoliticaDoble(), matriz_prueba())
    assert not orq.comando(Comando.REARMAR)


# --- límites y montaje -------------------------------------------------------------------------------------------------
def _saltos(m):
    qs = [o.q for o in m.ordenes if o.q is not None]
    return np.abs(np.diff(np.array(qs), axis=0))


def test_limite_de_velocidad_en_todas_las_ordenes():
    cfg = config(velocidad_max=45.0)
    pol = PoliticaDoble(destino=np.array([80.0, 30.0, -40.0, 90.0, 0.0, 0.0]))
    pol.accion = lambda obs, vista: pol.destino.copy()   # salta de golpe al destino
    pol.llegado = lambda: False
    orq = Orquestador(cfg, pol, matriz_prueba())
    m = Mundo(orq)
    m.correr(escena_taladro(quieto_desde=0.0), 4.0)
    assert np.max(_saltos(m)) <= 45.0 / HZ + 1e-9
    # también por articulación
    cfg = config(velocidad_max=[10, 20, 30, 40, 50, 60])
    orq = Orquestador(cfg, pol, matriz_prueba())
    m = Mundo(orq, q0=np.zeros(6))
    m.correr(escena_taladro(quieto_desde=0.0), 4.0)
    assert np.all(_saltos(m).max(axis=0) <= np.array([10, 20, 30, 40, 50, 60]) / HZ + 1e-9)


def test_wrist_roll_y_pinza_como_vienen_o_fijadas():
    orq, m = llevar_a_en_broca()
    assert m.ordenes[-1].q[4] == pytest.approx(5.0, abs=0.6) and m.ordenes[-1].q[5] == pytest.approx(20.0, abs=0.6)
    cfg = config(wrist_roll_fijo=0.0, pinza_fija=3.0)
    orq, m = llevar_a_en_broca(cfg)
    assert m.ordenes[-1].q[4] == pytest.approx(0.0, abs=0.5)
    assert m.ordenes[-1].q[5] == pytest.approx(3.0, abs=0.5)


def test_estado_app_y_tecnologias():
    orq, m = llevar_a_en_broca()
    e = orq.estado_app()
    assert e.estado == Estado.EN_BROCA and e.aspiradora and e.politica == "circulo"
    assert e.tecnologias["aspiradora"].startswith("manual")
    assert e.tecnologias["robot"] == "ok" and e.tecnologias["círculo"] == "ok"
    assert e.tecnologias["matriz"].startswith("ok: rejilla")
    assert "con taladro" in e.tecnologias["manos"]
    assert e.eventos and all(isinstance(x, str) for x in e.eventos)
    cfg = config()
    cfg.puertos.aspiradora = "/dev/ttyUSB0"
    assert Orquestador(cfg, PoliticaDoble()).estado_app().tecnologias["aspiradora"] == "ok"


def test_politica_que_falla_va_a_despierto():
    pol = PoliticaDoble()

    def falla(obs, vista):
        raise RuntimeError("sin cámara")
    pol.accion = falla
    orq = Orquestador(config(), pol, matriz_prueba())
    m = Mundo(orq)
    m.correr(escena_taladro(quieto_desde=0.0), 2.0)
    assert orq.estado == Estado.DESPIERTO and orq.tecnologias["política"].startswith("error")


def test_cambiar_de_politica_desde_la_app():
    orq = Orquestador(config(), PoliticaDoble("act"), matriz_prueba())
    assert orq.poner_politica(PoliticaDoble("circulo"))
    assert orq.estado_app().politica == "circulo"


# --- matriz ------------------------------------------------------------------------------------------------------------
def _escribir_csv(ruta, P, Q, cabecera=("u", "v", "shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex",
                                         "wrist_roll", "gripper"), sep=",", columnas_q=6):
    filas = [sep.join(cabecera)]
    for p, q in zip(P, Q):
        filas.append(sep.join(f"{x:.6f}" for x in list(p) + list(q[:columnas_q])))
    ruta.write_text("\n".join(filas) + "\n", encoding="utf-8")
    return ruta


def test_matriz_csv_rejilla_bilineal(tmp_path):
    P, Q = rejilla_5x3()
    m = cargar_matriz(_escribir_csv(tmp_path / "m.csv", P, Q))
    assert m.rejilla is not None and m.rejilla.size == 15 and m.unidades == "px"
    # dentro: la función es bilineal en (u, v) salvo la torsión → en los puntos marcados, exacta
    for p, q in zip(P, Q):
        assert np.allclose(m.postura_px(p), q, atol=1e-6)
    # un punto en medio de una celda (función lineal en u y v → exacta)
    lineal = lambda u, v: [u / 10, -v / 10, 2 * u - v, 0, 0, 0]  # noqa: E731
    P2, Q2 = rejilla_5x3(lineal)
    m2 = Matriz(P2, Q2)
    assert np.allclose(m2.postura_px((333.0, 222.0)), lineal(333.0, 222.0), atol=1e-6) and not m2.fuera


def test_matriz_csv_con_alias_punto_y_coma_y_5_articulaciones(tmp_path):
    P, Q = rejilla_5x3()
    cab = ("Pixel_X", "Pixel_Y", "pan.pos", "Lift", "Codo", "Muñeca", "roll")
    ruta = _escribir_csv(tmp_path / "m.csv", P, Q, cab, sep=";", columnas_q=5)
    m = cargar_matriz(ruta, pinza=7.0)
    assert np.allclose(m.posturas[:, 5], 7.0)
    assert np.allclose(m.posturas[:, :5], Q[:, :5])


def test_matriz_json_variantes(tmp_path):
    P, Q = rejilla_5x3()
    (tmp_path / "a.json").write_text(json.dumps([{"uv": list(p), "q": list(q)} for p, q in zip(P, Q)]))
    (tmp_path / "b.json").write_text(json.dumps({"puntos": [
        {"u": p[0], "v": p[1], **{f"{n}.pos": x for n, x in zip(
            ("shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"), q)}}
        for p, q in zip(P, Q)]}))
    for nombre in ("a.json", "b.json"):
        m = cargar_matriz(tmp_path / nombre)
        assert np.allclose(m.postura_px(P[7]), Q[7]) and m.rejilla is not None


def test_matriz_en_mm_con_homografia(tmp_path):
    tapete_px = [[100, 100], [500, 100], [500, 400], [100, 400]]   # 400 × 300 px para 600 × 450 mm
    xs, ys = np.meshgrid(np.linspace(50, 550, 5), np.linspace(50, 400, 3))
    P = np.stack([xs.ravel(), ys.ravel()], 1)
    Q = np.array([[x / 10, y / 10, 0, 0, 0, 0] for x, y in P])
    ruta = _escribir_csv(tmp_path / "mm.csv", P, Q, ("x_mm", "y_mm", "j1", "j2", "j3", "j4", "j5", "j6"))
    m = cargar_matriz(ruta, esquinas_tapete_px=tapete_px, tapete_mm=(600, 450))
    assert m.unidades == "mm"
    q = m.postura_px((300, 250))   # centro del tapete → (300, 225) mm
    assert np.allclose(q[:2], [30.0, 22.5], atol=1e-6)


def test_matriz_fuera_extrapola_limitado_y_avisa(caplog):
    m = matriz_prueba()
    with caplog.at_level(logging.WARNING, logger="garbi.producto"):
        q_borde = m.postura_px((80 + 0.05 * 240, 240))
        q_fuera = m.postura_px((80 + 0.05 * 240 - 40, 240))      # 40 px fuera: extrapola
        q_lejos = m.postura_px((80 + 0.05 * 240 - 500, 240))     # muy lejos: recortado a 80 px
    assert m.fuera and "fuera" in caplog.text
    assert q_fuera[0] < q_borde[0]                                # sigue la tendencia (pan = u/10 - 30)
    assert q_lejos[0] == pytest.approx(q_borde[0] - 80 / 10, abs=0.5)


def test_matriz_delaunay_general():
    rng = np.random.default_rng(0)
    P = rng.uniform(0, 400, (20, 2))
    lineal = lambda p: [p[0] / 5, p[1] / 7, p[0] - p[1], 0, 0, 0]  # noqa: E731
    m = Matriz(P, np.array([lineal(p) for p in P]))
    assert m.rejilla is None and len(m.triangulos) > 10
    centro = P.mean(axis=0)
    assert np.allclose(m.postura_px(centro), lineal(centro), atol=1e-6) and not m.fuera
    m.postura_px((-200, -200))
    assert m.fuera


def test_detectar_rejilla_rechaza_puntos_sueltos():
    assert detectar_rejilla(np.random.default_rng(1).uniform(0, 100, (15, 2))) is None
    P, _ = rejilla_5x3()
    r = detectar_rejilla(P[np.random.default_rng(2).permutation(15)])
    assert r is not None and sorted(r.shape) == [3, 5]


def test_offset_de_altura():
    m = matriz_prueba()
    off = np.array([0, -8, 4, 0, 0, 0.0])
    assert np.allclose(m.postura_px(UV_A, off) - m.postura_px(UV_A), off)


# --- barridos ----------------------------------------------------------------------------------------------------------
def _cubre(esquinas, camino, paso, margen):
    """Cada punto del interior (menos el margen) está a menos de paso/2 (+ holgura) del camino."""
    import cv2

    e = ordenar_esquinas(esquinas).astype(np.float32)
    lo, hi = e.min(0), e.max(0)
    us, vs = np.meshgrid(np.arange(lo[0], hi[0], 4), np.arange(lo[1], hi[1], 4))
    peor = 0.0
    for u, v in zip(us.ravel(), vs.ravel()):
        if cv2.pointPolygonTest(e.reshape(-1, 1, 2), (float(u), float(v)), True) < margen + 1:
            continue
        peor = max(peor, float(np.min(np.linalg.norm(camino - [u, v], axis=1))))
    return peor


def test_barrido_tabla_cubre_toda_la_tabla_y_respeta_la_velocidad():
    m = matriz_prueba()
    off = np.array([0, -8, 4, 0, 0, 0.0])
    b = barrido_tabla(TABLA, m, off, paso_px=30, margen_px=10, velocidad=40, aceleracion=120)
    assert _cubre(TABLA, b.puntos_px, 30, 10) <= 15 + 3
    vel = np.abs(np.diff(b.posturas, axis=0)) * HZ
    assert vel.max() <= 40 + 1e-6
    assert vel[0].max() < 8 and vel[-1].max() < 8   # arranca y para suave (rampa de 120 °/s²)
    # las posturas son las de la matriz + el offset en el punto barrido
    k = len(b) // 2
    assert np.allclose(b.posturas[k], m.postura_px(b.puntos_px[k], off), atol=0.5)


def test_barrido_tabla_girada():
    m = matriz_prueba()
    c, a = np.array([320.0, 240.0]), np.radians(25)
    R = np.array([[np.cos(a), -np.sin(a)], [np.sin(a), np.cos(a)]])
    tabla = (TABLA - TABLA.mean(0)) @ R.T + c
    b = barrido_tabla(tabla[[2, 0, 3, 1]], m, paso_px=25, margen_px=8)
    assert _cubre(tabla, b.puntos_px, 25, 8) <= 12.5 + 3


def test_barrido_tapete_cubre_todo_el_tapete():
    cfg = config()
    m = matriz_prueba()
    b = barrido_tapete(cfg.tapete_px, m, cfg.barridos.offset_tapete, paso_px=40, margen_px=10)
    assert _cubre(cfg.tapete_px, b.puntos_px, 40, 10) <= 20 + 3
    assert np.abs(np.diff(b.posturas, axis=0)).max() * HZ <= cfg.barridos.velocidad + 1e-6


def test_trayectoria_suave():
    q0, q1 = np.zeros(6), np.array([60.0, -30, 10, 0, 0, 0])
    tr = trayectoria_suave(q0, q1, 60.0)
    assert np.allclose(tr[-1], q1)
    vel = np.abs(np.diff(np.vstack([q0, tr]), axis=0)) * HZ
    assert vel.max() <= 60.0 + 1e-6 and vel[0].max() < 2 and vel[-1].max() < 2


# --- políticas ---------------------------------------------------------------------------------------------------------
def _vista(uv, t=0.0):
    return Vista(t=t, circulo=Circulo(uv=np.asarray(uv, float), radio=10, quieto_desde=0.0), taladro_agarrado=True)


def test_politica_circulo_llega_suave():
    m = matriz_prueba()
    p = PoliticaCirculo(m, velocidad=60.0, tolerancia=0.5)
    q = np.array([-60.0, -100, 95, 60, 0, 0])
    p.reiniciar(_vista(UV_A), q)
    qs = [q]
    for _ in range(400):
        qs.append(p.accion({"state": qs[-1]}, _vista(UV_A)))
        if p.llegado():
            break
    assert p.llegado()
    assert np.allclose(qs[-1], m.postura_px(UV_A), atol=0.5)
    assert np.abs(np.diff(qs, axis=0)).max() * HZ <= 60.0 + 1e-6


def test_politica_circulo_pasa_por_la_intermedia_y_reapunta():
    m = matriz_prueba()
    intermedia = np.array([0.0, -70, 70, 40, 0, 0])
    p = PoliticaCirculo(m, postura_intermedia=intermedia, velocidad=90.0, actualizar_px=3.0, rango_px=60)
    q = np.array([-60.0, -100, 95, 60, 0, 0])
    p.reiniciar(_vista(UV_A), q)
    qs = []
    nuevo = UV_A + np.array([20.0, 0.0])
    for k in range(600):
        uv = UV_A if k < 40 else nuevo
        qs.append(p.accion({}, _vista(uv)))
        if p.llegado():
            break
    assert min(np.max(np.abs(np.array(qs) - intermedia), axis=1)) < 1e-6
    assert np.allclose(qs[-1], m.postura_px(nuevo), atol=1.0)
    # un salto mayor que el rango no se sigue (eso lo decide el orquestador)
    p.reiniciar(_vista(UV_A), q)
    p.accion({}, _vista(UV_A + 200))
    assert np.allclose(p.uv, UV_A)


def test_mapear_camaras():
    assert mapear_camaras(["observation.images.top", "observation.images.wrist"], ["top", "wrist"]) == {
        "observation.images.top": "top", "observation.images.wrist": "wrist"}
    assert mapear_camaras(["observation.images.front", "observation.images.hand"], ["top", "wrist"]) == {
        "observation.images.front": "top", "observation.images.hand": "wrist"}
    assert mapear_camaras(["observation.images.cam_x"], ["top"]) == {"observation.images.cam_x": "top"}
    assert mapear_camaras(["observation.images.a", "observation.images.b"], ["top", "wrist"],
                          {"a": "wrist", "b": "top"}) == {"observation.images.a": "wrist", "observation.images.b": "top"}
    with pytest.raises(ValueError):
        mapear_camaras(["observation.images.a", "observation.images.b"], ["top", "wrist"])


@pytest.fixture(scope="module")
def act_diminuto(tmp_path_factory):
    """Un ACT diminuto entrenado 3 pasos en CPU con datos aleatorios, guardado como lo deja lerobot-train
    (`checkpoints/last/pretrained_model`), con cámaras llamadas «front» y «hand» para probar el mapeo."""
    import torch
    from lerobot.configs.types import FeatureType, PolicyFeature
    from lerobot.policies.act.configuration_act import ACTConfig
    from lerobot.policies.act.modeling_act import ACTPolicy
    from lerobot.policies.factory import make_pre_post_processors

    torch.manual_seed(0)
    salida = tmp_path_factory.mktemp("act") / "salida"
    destino = salida / "checkpoints" / "last" / "pretrained_model"
    imagenes = ("observation.images.front", "observation.images.hand")
    cfg = ACTConfig(
        input_features={**{k: PolicyFeature(FeatureType.VISUAL, (3, 48, 64)) for k in imagenes},
                        "observation.state": PolicyFeature(FeatureType.STATE, (6,))},
        output_features={"action": PolicyFeature(FeatureType.ACTION, (6,))},
        chunk_size=5, n_action_steps=5, dim_model=32, dim_feedforward=64, n_heads=2, n_encoder_layers=1,
        n_decoder_layers=1, latent_dim=8, pretrained_backbone_weights=None, device="cpu")
    pol = ACTPolicy(cfg)
    uno, cero = torch.ones(6), torch.zeros(6)
    stats = {k: {"mean": cero, "std": uno * 30, "min": -uno * 90, "max": uno * 90}
             for k in ("observation.state", "action")}
    for k in imagenes:
        stats[k] = {"mean": torch.full((3, 1, 1), 0.5), "std": torch.full((3, 1, 1), 0.2),
                    "min": torch.zeros(3, 1, 1), "max": torch.ones(3, 1, 1)}
    pre, post = make_pre_post_processors(cfg, dataset_stats=stats)
    opt = torch.optim.AdamW(pol.parameters(), lr=1e-3)
    pol.train()
    for _ in range(3):
        lote = {**{k: torch.rand(2, 3, 48, 64) for k in imagenes}, "observation.state": torch.randn(2, 6),
                "action": torch.randn(2, 5, 6), "action_is_pad": torch.zeros(2, 5, dtype=torch.bool)}
        perdida, _ = pol.forward(lote)
        opt.zero_grad()
        perdida.backward()
        opt.step()
    pol.save_pretrained(destino)
    pre.save_pretrained(destino)
    post.save_pretrained(destino)
    return salida


def _obs(q=None):
    return {"top": np.zeros((480, 640, 3), np.uint8), "wrist": np.full((480, 640, 3), 128, np.uint8),
            "state": np.zeros(6) if q is None else q}


def test_politica_act_mapea_features_y_da_acciones(act_diminuto):
    p = PoliticaACT(act_diminuto, tiempo_max=0.2, hz=30)   # carpeta de salida: usa checkpoints/last
    assert p.camaras == {"observation.images.front": "top", "observation.images.hand": "wrist"}
    assert p.dim_estado == 6 and p.formas["observation.images.front"] == (48, 64)
    p.reiniciar(_vista(UV_A), np.zeros(6))
    entrada = p.observacion(_obs())
    assert entrada["observation.images.front"].shape == (48, 64, 3)
    assert entrada["observation.state"].dtype == np.float32
    for _ in range(6):
        a = p.accion(_obs(), _vista(UV_A))
        assert a.shape == (6,) and np.all(np.isfinite(a))
    assert p.llegado()   # por tiempo máximo (0,2 s = 6 pasos)


def test_politica_act_estado_orden_y_ensemble(act_diminuto):
    p = PoliticaACT(act_diminuto / "checkpoints" / "last" / "pretrained_model", estado="orden", ensemble=0.01)
    assert p.config.temporal_ensemble_coeff == 0.01 and p.config.n_action_steps == 1
    q0 = np.full(6, 3.0)
    p.reiniciar(_vista(UV_A), q0)
    assert np.allclose(p.observacion(_obs(np.zeros(6)))["observation.state"], q0)   # la orden, no la medida
    a = p.accion(_obs(), _vista(UV_A))
    assert np.allclose(p.observacion(_obs())["observation.state"], a.astype(np.float32))


def test_politica_act_converge_con_doble():
    """llegado() por convergencia: la acción deja de cambiar durante N pasos."""
    from types import SimpleNamespace

    feats = {"observation.images.top": SimpleNamespace(shape=(3, 24, 32)),
             "observation.state": SimpleNamespace(shape=(6,))}
    cfg = SimpleNamespace(input_features=feats, output_features={"action": SimpleNamespace(shape=(6,))})
    p = PoliticaACT(politica=object(), config=cfg, umbral_llegada=0.5, pasos_llegada=5, tiempo_max=100,
                    camaras_disponibles=("top", "wrist"))
    salidas = iter([np.full(6, x) for x in (0, 10, 20, 25, 25.1, 25.2, 25.2, 25.3, 25.3, 25.3)])
    p._inferir = lambda entrada: next(salidas)
    p.reiniciar(_vista(UV_A), np.zeros(6))
    llegados = []
    for _ in range(10):
        p.accion(_obs(), _vista(UV_A))
        llegados.append(p.llegado())
    assert not any(llegados[:8]) and llegados[-1]


def test_crear_politica_por_configuracion(act_diminuto):
    m = matriz_prueba()
    cfg = config(politica="circulo")
    assert isinstance(crear_politica(cfg, m), PoliticaCirculo)
    cfg = config(politica="act")
    cfg.act.modelo = str(act_diminuto)
    p = crear_politica(cfg, m)
    assert isinstance(p, PoliticaACT) and p.nombre == "act"
    # y el orquestador lo usa igual (ACT con las cámaras reales a 640 × 480)
    orq = Orquestador(config(politica="act", act_desde="despierto"), p, m)
    v = _vista(UV_A, t=2.0)
    v.tabla = TABLA
    orq.paso(Vista(t=0.0, tabla=TABLA), _obs(orq.cfg.q_reposo))
    o = orq.paso(v, _obs(orq.cfg.q_reposo))
    assert orq.estado == Estado.ACERCAMIENTO and o.q.shape == (6,)


# --- configuración y demo ------------------------------------------------------------------------------------------------
def test_config_yaml_de_la_raiz():
    cfg = cargar_config()
    assert cfg.politica in ("act", "circulo") and cfg.act_desde == "reposo"
    assert cfg.puertos.aspiradora is None
    assert cfg.tiempos.quieto_desde_reposo == 1.0 and cfg.tiempos.quieto_desde_despierto == 2.0
    assert cfg.q_reposo.shape == (6,) and abs(cfg.q_reposo[0]) > 30   # girado a un lado (el signo depende de la calibración)
    assert cfg.esquinas_tapete.shape == (4, 2) and isinstance(cfg.vision, dict)


def test_config_valida_y_avisa(caplog):
    with pytest.raises(ValueError):
        config_desde_dict({"politica": "magia"})
    with pytest.raises(ValueError):
        config_desde_dict({"postura_reposo": [1, 2, 3]})
    with caplog.at_level(logging.WARNING, logger="garbi.producto"):
        cfg = config_desde_dict({"tiempos": {"quieto_desde_reposo": 1.5, "desconocida": 3}})
    assert cfg.tiempos.quieto_desde_reposo == 1.5 and "desconocida" in caplog.text


def test_demo_sin_hardware_recorre_los_estados():
    from garbi.producto.__main__ import crear_demo

    s = crear_demo()
    estados = set()
    for _ in range(int(45 * s.hz)):
        o = s.paso()
        estados.add(o.estado)
    assert {Estado.REPOSO, Estado.ACERCAMIENTO, Estado.EN_BROCA, Estado.DESPIERTO,
            Estado.LIMPIEZA_TABLA} <= estados
    assert s.imagenes["top"].shape == (480, 640, 3)
    assert s.orquestador.agujeros == 2


def test_la_vision_lee_la_misma_configuracion():
    from garbi.producto.vision import VisionProducto, cargar_config_vision_producto

    cfg = config()
    cfg.tapete_px = [[10, 20], [600, 20], [600, 460], [10, 460]]
    cfg.vision = {"circulo": {"tol_quieto_px": 9.0}}
    datos = cargar_config_vision_producto(cfg)
    assert datos["tapete_px"] == cfg.tapete_px and datos["circulo"]["tol_quieto_px"] == 9.0
    v = VisionProducto(cfg, detector_manos="ninguno")
    vista = v.leer({"top": np.zeros((480, 640, 3), np.uint8)}, 0.0)
    assert isinstance(vista, Vista)
