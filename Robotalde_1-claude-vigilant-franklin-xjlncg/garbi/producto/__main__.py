"""Programa principal del producto Garbi (mínimo: el integrador le añade la app y la visión definitiva).

    python -m garbi.producto                      # robot real con garbi/producto/garbi_producto.yaml
    python -m garbi.producto --config otro.yaml --demo   # sin hardware: robot, cámaras y escena falsos
    python -m garbi.producto --demo --segundos 90 --rapido           # la demo sin esperar al reloj (para probar)

Bucle a `cfg.hz` (30 Hz): imágenes → visión (`Vista`) → `Orquestador.paso` → robot + aspiradora. Ctrl+C para limpio
(aspiradora a 0 y el brazo quieto con par).

Para la app: `crear_demo(cfg)` devuelve un `Sistema` con el orquestador, el robot falso, las cámaras falsas y la
escena guionizada; `Sistema.paso()` avanza un fotograma y deja las imágenes en `Sistema.imagenes`.
"""
from __future__ import annotations

import argparse
import logging
import signal
import time
from dataclasses import dataclass, field

import numpy as np

from garbi.producto.config import ConfigProducto, cargar_config
from garbi.producto.contrato import Circulo, Comando, Estado, Vista
from garbi.producto.matriz import Matriz, matriz_desde_config
from garbi.producto.orquestador import Orquestador
from garbi.producto.politicas import PoliticaCirculo, crear_politica

log = logging.getLogger("garbi.producto")


# --- dobles para la demo -------------------------------------------------------------------------------------------
class RobotFalso:
    """Un SO-101 imaginario: la postura sigue a la orden con un poco de retraso; la aspiradora es un booleano."""

    def __init__(self, q0, retraso: float = 0.35):
        self._q = np.asarray(q0, float).copy()
        self.retraso = retraso
        self.aspirando = False

    def q(self) -> np.ndarray:
        return self._q.copy()

    def enviar(self, q) -> None:
        self._q = self._q + (1 - self.retraso) * (np.asarray(q, float) - self._q)

    def aspirar(self, encendida: bool) -> None:
        self.aspirando = bool(encendida)

    def quieto(self) -> None:
        pass

    def cerrar(self) -> None:
        self.aspirando = False


def matriz_demo(tapete_px) -> Matriz:
    """Rejilla de 5 × 3 sobre el tapete con posturas inventadas pero suaves (para la demo y los tests)."""
    from garbi.producto.barridos import _bilineal_esquinas, ordenar_esquinas

    e = ordenar_esquinas(tapete_px)
    puntos, posturas = [], []
    for t in np.linspace(0.1, 0.9, 3):
        for s in np.linspace(0.1, 0.9, 5):
            p = _bilineal_esquinas(e, np.array(s), np.array(t))
            puntos.append(p)
            posturas.append([-40 + 80 * s, -20 - 30 * t, 30 + 40 * t, 50 - 10 * t, 0.0, 0.0])
    return Matriz(np.array(puntos), np.array(posturas))


@dataclass
class GuionDemo:
    """Escena guionizada que se repite cada `periodo` s: dos agujeros, limpieza de la tabla y retirada de la tabla."""
    tabla: np.ndarray = field(default_factory=lambda: np.array([[200, 150], [440, 150], [440, 330], [200, 330]], float))
    tapete: np.ndarray | None = None
    periodo: float = 120.0

    def __call__(self, t: float) -> Vista:
        tc = t % self.periodo
        v = Vista(t=t, tapete=self.tapete)
        v.tabla = self.tabla.copy() if tc < 95 else None   # a los 95 s se retira la tabla
        sitios = ((3.0, 12.0, np.array([280.0, 220.0])), (16.0, 25.0, np.array([370.0, 270.0])))
        base = t - tc
        for t0, t1, uv in sitios:
            if t0 <= tc < t1:
                llegando = tc < t0 + 0.5
                pos = uv + (np.array([0.0, 40.0]) * (t0 + 0.5 - tc) if llegando else 0.0)
                v.circulo = Circulo(uv=pos, radio=12.0, quieto_desde=None if llegando else base + t0 + 0.5)
                v.manos = [pos + np.array([30.0, 20.0])]
                v.taladro_agarrado = True
            elif t1 <= tc < t1 + 1.0:   # se va: el círculo se aleja deprisa
                pos = uv + np.array([150.0, 0.0]) * (tc - t1)
                v.circulo = Circulo(uv=pos, radio=12.0)
                v.manos = [pos + np.array([30.0, 20.0])]
                v.taladro_agarrado = True
        return v


def dibujar(vista: Vista, ancho: int = 640, alto: int = 480) -> dict[str, np.ndarray]:
    """Cámaras falsas: tapete azul, tabla de madera, círculo morado y manos."""
    import cv2

    top = np.full((alto, ancho, 3), 40, np.uint8)
    if vista.tapete is not None:
        cv2.fillPoly(top, [np.asarray(vista.tapete, np.int32)], (40, 70, 150))
    if vista.tabla is not None:
        cv2.fillPoly(top, [np.asarray(vista.tabla, np.int32)], (200, 160, 110))
    for m in vista.manos:
        cv2.circle(top, (int(m[0]), int(m[1])), 22, (230, 180, 150), -1)
    if vista.circulo is not None:
        c = vista.circulo
        cv2.circle(top, (int(c.uv[0]), int(c.uv[1])), int(c.radio), (140, 40, 170), -1)
    wrist = np.full((alto, ancho, 3), 90, np.uint8)
    return {"top": top, "wrist": wrist}


@dataclass
class Sistema:
    orquestador: Orquestador
    robot: object
    leer_vista: object            # t → Vista (demo) o imágenes → Vista (real)
    hz: float = 30.0
    t: float = 0.0
    imagenes: dict = field(default_factory=dict)
    vista: Vista | None = None

    def paso(self):
        self.vista = self.leer_vista(self.t)
        self.imagenes = dibujar(self.vista)
        obs = {**self.imagenes, "state": self.robot.q()}
        orden = self.orquestador.paso(self.vista, obs)
        if orden.q is not None:
            self.robot.enviar(orden.q)
        self.robot.aspirar(orden.aspirar)
        self.t += 1.0 / self.hz
        return orden


def crear_demo(cfg: ConfigProducto | None = None, politica: str = "circulo") -> Sistema:
    """Todo falso: matriz de demo (5 × 3 sobre el tapete), política del círculo y la escena guionizada."""
    cfg = cfg or ConfigProducto().validar()
    matriz = matriz_demo(cfg.tapete_px)
    if politica == "circulo":
        c = cfg.circulo
        pol = PoliticaCirculo(matriz, c.postura_intermedia, c.velocidad, c.tolerancia, c.actualizar_px,
                              cfg.tiempos.rango_salida_px, cfg.hz)
    else:
        pol = crear_politica(cfg, matriz)
    orq = Orquestador(cfg, pol, matriz)
    orq.marcar_tecnologia("robot", "aviso: demo (robot falso)")
    return Sistema(orq, RobotFalso(cfg.q_reposo), GuionDemo(tapete=cfg.esquinas_tapete), cfg.hz)


# --- robot real ----------------------------------------------------------------------------------------------------
def crear_cuerpo_real(cfg: ConfigProducto):
    """`CuerpoReal` sin forzar la muñeca ni la pinza (el orquestador ya aplica `wrist_roll_fijo`/`pinza_fija`)."""
    from garbi.real import CuerpoReal, accion_lerobot, q_desde_lerobot

    class CuerpoProducto(CuerpoReal):
        def enviar(self, q):
            self.ultima_enviada = q_desde_lerobot(self.robot.send_action(accion_lerobot(q)))

    camaras = {"top": cfg.camaras.top, "wrist": cfg.camaras.wrist}
    return CuerpoProducto(cfg.puertos.follower, cfg.id_robot, camaras, puerto_aspiradora=cfg.puertos.aspiradora,
                          use_degrees=cfg.use_degrees, resoluciones=cfg.camaras.resolucion)


def crear_vision(cfg: ConfigProducto):
    """La visión del producto (P2): lee `cfg.vision` y `cfg.tapete_px` del mismo yaml."""
    from garbi.producto.vision import VisionProducto

    return VisionProducto(cfg)


def correr_real(cfg: ConfigProducto, segundos: float | None = None) -> None:
    matriz = None
    try:
        matriz = matriz_desde_config(cfg)
    except Exception as e:
        log.warning("sin matriz (%s): no habrá barridos ni política del círculo", e)
    politica = crear_politica(cfg, matriz)
    orq = Orquestador(cfg, politica, matriz)
    vision = crear_vision(cfg)
    cuerpo = crear_cuerpo_real(cfg).conectar()
    parar = {"ya": False}
    signal.signal(signal.SIGTERM, lambda *_: parar.update(ya=True))
    periodo, t0 = 1.0 / cfg.hz, time.perf_counter()
    try:
        while not parar["ya"]:
            inicio = time.perf_counter()
            t = inicio - t0
            if segundos is not None and t > segundos:
                break
            imagenes = cuerpo.imagenes()
            vista = vision.leer(imagenes, t)
            orden = orq.paso(vista, {**imagenes, "state": cuerpo.q()})
            if orden.q is not None:
                cuerpo.enviar(orden.q)
            elif orq.estado == Estado.EMERGENCIA:
                cuerpo.quieto()   # objetivo = postura actual: quieto con par
            cuerpo.aspirar(orden.aspirar)
            time.sleep(max(0.0, periodo - (time.perf_counter() - inicio)))
    except KeyboardInterrupt:
        pass
    finally:
        orq.comando(Comando.EMERGENCIA)
        cuerpo.cerrar()


def correr_demo(cfg: ConfigProducto, segundos: float, rapido: bool) -> Sistema:
    sistema = crear_demo(cfg)
    vistos: list[str] = []
    anterior = None
    for _ in range(int(segundos * sistema.hz)):
        inicio = time.perf_counter()
        orden = sistema.paso()
        eventos = list(sistema.orquestador.eventos)
        if orden.estado != anterior or eventos[-1:] != vistos:
            print(f"{sistema.t:6.1f} s  {orden.estado.value:16s} aspira={int(orden.aspirar)}  "
                  f"{eventos[-1] if eventos else ''}")
            anterior, vistos = orden.estado, eventos[-1:]
        if not rapido:
            time.sleep(max(0.0, 1.0 / sistema.hz - (time.perf_counter() - inicio)))
    return sistema


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="Garbi, producto final")
    ap.add_argument("--config", default=None, help="yaml del producto (por defecto garbi/producto/garbi_producto.yaml)")
    ap.add_argument("--demo", action="store_true", help="sin hardware: robot, cámaras y escena falsos")
    ap.add_argument("--segundos", type=float, default=None, help="parar a los X s")
    ap.add_argument("--rapido", action="store_true", help="demo sin esperar al reloj")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    cfg = cargar_config(args.config)
    if args.demo:
        correr_demo(cfg, args.segundos or 120.0, args.rapido)
    else:
        correr_real(cfg, args.segundos)


if __name__ == "__main__":
    main()
