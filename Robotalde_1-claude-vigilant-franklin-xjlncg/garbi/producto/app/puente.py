"""Puente entre la app y el orquestador de Garbi.

La app solo necesita tres cosas del orquestador (P1). Las tres se llaman desde el hilo del servidor web, nunca desde el
bucle de control a 30 Hz, así que tienen que ser rápidas y seguras entre hilos:

- `comando(Comando)`: encolar una orden (botón, chat o seta). No debe bloquear: el bucle la aplica en su siguiente paso.
- `estado_app() -> EstadoApp`: una copia del último estado que enseña la app.
- `imagenes_anotadas() -> {"top": ..., "wrist": ...}`: las últimas imágenes con las detecciones dibujadas. Cada valor
  puede ser un `np.ndarray` BGR (como lo da OpenCV), los bytes de un JPEG ya codificado, o `None` si esa cámara no hay.

Aspiradora sin Arduino: si `tecnologias["aspiradora"]` empieza por "manual", la app avisa en grande cuando Garbi quiere
aspirar (`EstadoApp.aspiradora` pasa a True) para que el usuario la encienda con el pie, y cuando hay que apagarla.

`OrquestadorFalso` cumple la interfaz sin hardware: recorre los estados de una sesión típica (acercamiento, broca,
limpiezas) con imágenes sintéticas, y responde a los comandos. Lo usa `python -m garbi.producto.app --demo`.
"""
from __future__ import annotations

import logging
import math
import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Callable, Protocol, runtime_checkable

import cv2
import numpy as np

from garbi.producto.app.indicadores import Indicadores
from garbi.producto.contrato import Comando, Estado, EstadoApp

Imagen = np.ndarray | bytes | None


@runtime_checkable
class Orquestador(Protocol):
    """Lo mínimo que la app necesita del orquestador. Seguro entre hilos y sin bloquear."""

    def comando(self, comando: Comando) -> None: ...

    def estado_app(self) -> EstadoApp: ...

    def imagenes_anotadas(self) -> dict[str, Imagen]: ...


def a_jpeg(imagen: Imagen, calidad: int = 80) -> bytes | None:
    """Pasa una imagen (BGR o JPEG ya hecho) a bytes JPEG. `None` si no hay imagen o no se puede codificar."""
    if imagen is None:
        return None
    if isinstance(imagen, (bytes, bytearray, memoryview)):
        return bytes(imagen)
    ok, buf = cv2.imencode(".jpg", imagen, [cv2.IMWRITE_JPEG_QUALITY, calidad])
    return buf.tobytes() if ok else None


# ---------------------------------------------------------------------------------------------------------------------
# Orquestador falso para el modo demo
# ---------------------------------------------------------------------------------------------------------------------

@dataclass
class _Tramo:
    estado: Estado
    duracion: float   # s
    detalle: str
    aspirar: bool
    evento: str


# Una sesión típica: dos agujeros y después las dos limpiezas. Luego vuelve a empezar.
GUION_DEMO: list[_Tramo] = [
    _Tramo(Estado.REPOSO, 4.0, "Esperando una mano con el taladro", False, "En reposo: esperando al taladro"),
    _Tramo(Estado.ACERCAMIENTO, 3.0, "Taladro quieto 1 s: me acerco a la broca", False,
           "Taladro quieto 1 s: me acerco"),
    _Tramo(Estado.EN_BROCA, 5.0, "Aspirando junto a la broca", True, "En la broca: aspiradora encendida"),
    _Tramo(Estado.DESPIERTO, 3.0, "Taladro retirado: espero al siguiente agujero", False,
           "Taladro retirado: espero despierto"),
    _Tramo(Estado.ACERCAMIENTO, 3.0, "Taladro quieto 2 s: vuelvo a la broca", False, "Taladro quieto 2 s: me acerco"),
    _Tramo(Estado.EN_BROCA, 5.0, "Aspirando junto a la broca", True, "En la broca: aspiradora encendida"),
    _Tramo(Estado.DESPIERTO, 2.0, "Taladro retirado: espero al siguiente agujero", False,
           "Taladro retirado: espero despierto"),
    _Tramo(Estado.LIMPIEZA_TABLA, 6.0, "Sin taladro en escena: barro la tabla", True, "Barrido de la tabla"),
    _Tramo(Estado.LIMPIEZA_TAPETE, 6.0, "Tabla retirada: barro el tapete", True, "Barrido del tapete"),
]

_TRAMO_TABLA = next(i for i, t in enumerate(GUION_DEMO) if t.estado is Estado.LIMPIEZA_TABLA)
_TRAMO_TAPETE = next(i for i, t in enumerate(GUION_DEMO) if t.estado is Estado.LIMPIEZA_TAPETE)


class OrquestadorFalso:
    """Simula a Garbi para enseñar la app sin robot. `reloj` se inyecta en las pruebas."""

    politica = "act"

    def __init__(self, reloj: Callable[[], float] = time.monotonic, ancho: int = 640, alto: int = 480,
                 automatico: bool = True, aspiradora_manual: bool = True):
        self._reloj = reloj
        self._aspiradora_manual = aspiradora_manual   # sin Arduino: el usuario la enciende con el pie
        self._cerrojo = threading.RLock()
        self._ancho, self._alto = ancho, alto
        self._automatico = automatico   # si False, se queda en el estado que le manden (pruebas)
        self._eventos: deque[str] = deque(maxlen=40)
        self._agujeros = 0
        self._estado_fijo: tuple[Estado, str, bool] | None = None   # APAGADO o EMERGENCIA: no avanza el guion
        self._i = 0
        self._t_tramo = reloj()
        self.comandos: list[Comando] = []   # historial, para las pruebas
        self._indicadores = Indicadores(hueco_max=math.inf)
        self._anotar("Garbi encendido (modo demo)")
        self._entrar(0)
        self._observar()

    # --- interfaz del puente ----------------------------------------------------------------------------------------

    def comando(self, comando: Comando) -> None:
        comando = Comando(comando)
        with self._cerrojo:
            self._avanzar()
            self._observar()
            try:
                self._aplicar(comando)
            finally:
                self._observar()

    def _aplicar(self, comando: Comando) -> None:
        """Aplica el comando (con el cerrojo ya tomado)."""
        self.comandos.append(comando)
        emergencia = self._estado_fijo is not None and self._estado_fijo[0] is Estado.EMERGENCIA
        if comando is Comando.EMERGENCIA:
            if not emergencia:
                self._estado_fijo = (Estado.EMERGENCIA, "Seta pulsada: quieto con par", False)
                self._anotar("¡EMERGENCIA! Quieto con par y aspiradora apagada")
            return
        if emergencia:
            if comando is Comando.REARMAR:
                self._estado_fijo = None
                self._anotar("Rearmado: vuelvo a reposo")
                self._entrar(0)
            else:
                self._anotar(f"Ignorado «{comando.value}»: estoy en emergencia, hay que rearmar")
            return
        if comando is Comando.APAGAR:
            self._estado_fijo = (Estado.APAGADO, "Apagado: no me muevo ni miro", False)
            self._anotar("Apagado")
        elif comando in (Comando.ENCENDER, Comando.PARAR, Comando.REARMAR):
            self._estado_fijo = None
            self._anotar({Comando.ENCENDER: "Encendido", Comando.PARAR: "Parado: vuelvo a reposo",
                          Comando.REARMAR: "Rearmar (no hacía falta)"}[comando])
            self._entrar(0)
        elif comando is Comando.LIMPIAR_TABLA:
            self._estado_fijo = None
            self._entrar(_TRAMO_TABLA, "Me lo has pedido: barro la tabla")
        elif comando is Comando.LIMPIAR_TAPETE:
            self._estado_fijo = None
            self._entrar(_TRAMO_TAPETE, "Me lo has pedido: barro el tapete")

    def estado_app(self) -> EstadoApp:
        with self._cerrojo:
            self._avanzar()
            self._observar()
            estado, detalle, aspirar = self._actual()
            indicadores = self._indicadores.como_dict()
            indicadores["agujeros"] = self._agujeros
            return EstadoApp(
                estado=estado, detalle=detalle, aspiradora=aspirar, politica=self.politica,
                tecnologias=self._tecnologias(estado), agujeros=self._agujeros, eventos=list(self._eventos),
                indicadores=indicadores)

    def imagenes_anotadas(self) -> dict[str, Imagen]:
        with self._cerrojo:
            self._avanzar()
            estado, _, aspirar = self._actual()
            fase = self._fase()
        t = self._reloj()
        return {"top": self._dibujar_top(estado, fase, t), "wrist": self._dibujar_wrist(estado, aspirar, fase, t)}

    # --- guion ------------------------------------------------------------------------------------------------------

    def _actual(self) -> tuple[Estado, str, bool]:
        if self._estado_fijo is not None:
            return self._estado_fijo
        tramo = GUION_DEMO[self._i]
        return tramo.estado, tramo.detalle, tramo.aspirar

    def _fase(self) -> float:
        """0..1 dentro del tramo actual."""
        if self._estado_fijo is not None:
            return 0.0
        return min(1.0, (self._reloj() - self._t_tramo) / GUION_DEMO[self._i].duracion)

    def _entrar(self, i: int, evento: str | None = None) -> None:
        self._i = i
        self._t_tramo = self._reloj()
        tramo = GUION_DEMO[i]
        if tramo.estado is Estado.EN_BROCA:
            self._agujeros += 1
        self._anotar(evento or tramo.evento)

    def _avanzar(self) -> None:
        if self._estado_fijo is not None or not self._automatico:
            return
        while self._reloj() - self._t_tramo >= GUION_DEMO[self._i].duracion:
            fin = self._t_tramo + GUION_DEMO[self._i].duracion
            self._observar(fin)
            self._entrar((self._i + 1) % len(GUION_DEMO))
            self._t_tramo = fin
            self._observar(fin)

    def _observar(self, t: float | None = None) -> None:
        estado, _, aspirar = self._actual()
        self._indicadores.observar(estado, aspirar, self._reloj() if t is None else t)

    def _anotar(self, texto: str) -> None:
        self._eventos.appendleft(f"{time.strftime('%H:%M:%S')} · {texto}")

    def _tecnologias(self, estado: Estado) -> dict[str, str]:
        apagado = estado in (Estado.APAGADO,)
        return {
            "vision": "aviso: apagada" if apagado else "ok",
            "manos": "aviso: apagadas" if apagado else "ok",
            "politica": "ok",
            "robot": "aviso: modo demo, sin robot",
            "aspiradora": "manual" if self._aspiradora_manual else "ok",
        }

    # --- imágenes sintéticas ----------------------------------------------------------------------------------------

    def _tapete(self) -> np.ndarray:
        img = np.empty((self._alto, self._ancho, 3), np.uint8)
        img[:] = (58, 92, 52)   # verde del tapete de corte (BGR)
        for x in range(0, self._ancho, 40):
            cv2.line(img, (x, 0), (x, self._alto), (78, 118, 70), 1)
        for y in range(0, self._alto, 40):
            cv2.line(img, (0, y), (self._ancho, y), (78, 118, 70), 1)
        ruido = np.random.default_rng(7).integers(0, 10, img.shape, dtype=np.uint8)
        return cv2.add(img, ruido)

    def _dibujar_top(self, estado: Estado, fase: float, t: float) -> np.ndarray:
        img = self._tapete()
        w, h = self._ancho, self._alto
        apagado = estado is Estado.APAGADO
        hay_tabla = estado is not Estado.LIMPIEZA_TAPETE
        tabla = np.array([[w * .22, h * .25], [w * .72, h * .22], [w * .75, h * .70], [w * .25, h * .74]], np.int32)
        if hay_tabla:
            cv2.fillPoly(img, [tabla], (120, 170, 205))   # madera
            for k in range(1, 9):   # vetas
                y0 = int(h * .25 + k * h * .05)
                cv2.line(img, (int(w * .23), y0), (int(w * .73), y0 - 6), (108, 155, 190), 1, cv2.LINE_AA)
            for k in range(min(self._agujeros, 6)):   # agujeros hechos
                cv2.circle(img, (int(w * (.35 + .07 * k)), int(h * .45)), 5, (40, 50, 60), -1, cv2.LINE_AA)
        if apagado:
            return (img * 0.45).astype(np.uint8)

        tapete = np.array([[8, 8], [w - 8, 8], [w - 8, h - 8], [8, h - 8]], np.int32)
        cv2.polylines(img, [tapete], True, (255, 200, 80), 1, cv2.LINE_AA)
        cv2.putText(img, "tapete", (14, h - 16), cv2.FONT_HERSHEY_SIMPLEX, .45, (255, 200, 80), 1, cv2.LINE_AA)
        if hay_tabla:
            cv2.polylines(img, [tabla], True, (60, 220, 255), 2, cv2.LINE_AA)
            _etiqueta(img, "tabla", tuple(tabla[0] + [0, -8]), (60, 220, 255))

        hay_taladro = estado in (Estado.REPOSO, Estado.ACERCAMIENTO, Estado.EN_BROCA, Estado.EMERGENCIA)
        if hay_taladro:
            # El taladro entra, se queda quieto sobre la tabla y la mano lo sujeta.
            cx = w * .5 + (40 * math.sin(t * 1.3) if estado is Estado.REPOSO else 0)
            cy = h * .45 + (12 * math.cos(t * 1.1) if estado is Estado.REPOSO else 0)
            c = (int(cx), int(cy))
            cv2.rectangle(img, (c[0] - 14, c[1] - 70), (c[0] + 14, c[1] - 10), (50, 50, 55), -1)   # cuerpo
            cv2.circle(img, c, 22, (150, 40, 140), -1, cv2.LINE_AA)    # círculo morado
            quieto = estado is not Estado.REPOSO
            color = (80, 255, 120) if quieto else (255, 120, 230)
            cv2.circle(img, c, 28, color, 2, cv2.LINE_AA)
            cv2.drawMarker(img, c, color, cv2.MARKER_CROSS, 14, 2)
            _etiqueta(img, "taladro · quieto" if quieto else "taladro · en movimiento", (c[0] + 34, c[1] - 6), color)
            mano = (c[0] + 18, c[1] - 92)
            cv2.circle(img, mano, 26, (150, 190, 230), -1, cv2.LINE_AA)
            for k in range(21):   # puntos de la mano (como MediaPipe)
                a = k / 21 * math.pi * 1.6 + 0.6
                p = (int(mano[0] + 30 * math.cos(a)), int(mano[1] + 30 * math.sin(a)))
                cv2.circle(img, p, 2, (255, 255, 255), -1, cv2.LINE_AA)
            cv2.rectangle(img, (mano[0] - 36, mano[1] - 36), (mano[0] + 36, mano[1] + 36), (255, 255, 255), 1)
            _etiqueta(img, "mano + taladro", (mano[0] + 42, mano[1] - 20), (255, 255, 255))

        # La boquilla del robot: en reposo a la derecha; luego hacia la broca o barriendo.
        reposo = np.array([w * .9, h * .85])
        broca = np.array([w * .5 + 34, h * .45 + 20])
        if estado is Estado.ACERCAMIENTO:
            s = 0.5 - 0.5 * math.cos(math.pi * fase)
            boca = reposo + (broca - reposo) * s
        elif estado is Estado.EN_BROCA:
            boca = broca
        elif estado is Estado.DESPIERTO:
            boca = np.array([w * .78, h * .6])
        elif estado in (Estado.LIMPIEZA_TABLA, Estado.LIMPIEZA_TAPETE):
            boca = self._barrido(img, estado, fase, tabla)
        else:
            boca = reposo
        b = tuple(int(v) for v in boca)
        cv2.circle(img, b, 16, (255, 180, 0), 2, cv2.LINE_AA)
        cv2.circle(img, b, 4, (255, 180, 0), -1, cv2.LINE_AA)
        _etiqueta(img, "boquilla", (b[0] - 30, b[1] + 32), (255, 180, 0))
        return img

    def _barrido(self, img: np.ndarray, estado: Estado, fase: float, tabla: np.ndarray) -> np.ndarray:
        """Dibuja el recorrido en zigzag y devuelve dónde va la boquilla."""
        w, h = self._ancho, self._alto
        if estado is Estado.LIMPIEZA_TABLA:
            x0, x1, y0, y1, filas = w * .27, w * .70, h * .30, h * .66, 5
        else:
            x0, x1, y0, y1, filas = w * .08, w * .92, h * .1, h * .9, 7
        puntos = []
        for k in range(filas):
            y = y0 + (y1 - y0) * k / (filas - 1)
            puntos += [(x0, y), (x1, y)] if k % 2 == 0 else [(x1, y), (x0, y)]
        pts = np.array(puntos)
        cv2.polylines(img, [pts.astype(np.int32)], False, (255, 255, 255), 1, cv2.LINE_AA)
        seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
        objetivo = fase * seg.sum()
        acum = 0.0
        for k, largo in enumerate(seg):
            if acum + largo >= objetivo:
                return pts[k] + (pts[k + 1] - pts[k]) * ((objetivo - acum) / max(largo, 1e-6))
            acum += largo
        return pts[-1]

    def _dibujar_wrist(self, estado: Estado, aspirar: bool, fase: float, t: float) -> np.ndarray:
        w, h = self._ancho, self._alto
        img = np.empty((h, w, 3), np.uint8)
        img[:] = (95, 135, 165)
        if estado is Estado.APAGADO:
            return (img * 0.35).astype(np.uint8)
        cerca = {Estado.ACERCAMIENTO: fase, Estado.EN_BROCA: 1.0}.get(estado, 0.0)
        if estado in (Estado.LIMPIEZA_TABLA, Estado.LIMPIEZA_TAPETE):   # superficie pasando por debajo
            desp = int((t * 120) % 40)
            base = (120, 170, 205) if estado is Estado.LIMPIEZA_TABLA else (58, 92, 52)
            img[:] = base
            for y in range(-40, h, 40):
                cv2.line(img, (0, y + desp), (w, y + desp), tuple(int(c * .85) for c in base), 2)
        elif cerca > 0:   # la broca crece al acercarse
            escala = 0.4 + 0.6 * cerca
            cx, cy = w // 2, int(h * .45)
            alto = int(h * .55 * escala)
            ancho = max(6, int(22 * escala))
            cv2.rectangle(img, (cx - ancho // 2, cy - alto // 2), (cx + ancho // 2, cy + alto // 2), (170, 175, 180), -1)
            for k in range(-alto // 2, alto // 2, max(6, int(14 * escala))):   # espiral de la broca
                cv2.line(img, (cx - ancho // 2, cy + k), (cx + ancho // 2, cy + k + 6), (110, 115, 120), 2,
                         cv2.LINE_AA)
            cv2.rectangle(img, (cx - ancho // 2 - 8, cy - alto // 2 - 6), (cx + ancho // 2 + 8, cy + alto // 2 + 6),
                          (80, 255, 120), 2)
            _etiqueta(img, f"broca · {int(cerca * 100)} %", (cx + ancho + 14, cy - alto // 2 + 10), (80, 255, 120))
        if aspirar:   # partículas de serrín absorbidas hacia el centro
            rng = np.random.default_rng(int(t * 10))
            for _ in range(40):
                a, r = rng.uniform(0, 2 * math.pi), rng.uniform(30, 200)
                p = (int(w / 2 + r * math.cos(a)), int(h * .8 + r * .4 * math.sin(a)))
                cv2.circle(img, p, int(rng.integers(1, 4)), (180, 215, 235), -1, cv2.LINE_AA)
        cv2.ellipse(img, (w // 2, h + 40), (int(w * .32), 110), 0, 180, 360, (40, 40, 45), -1, cv2.LINE_AA)  # boquilla
        cv2.drawMarker(img, (w // 2, int(h * .45)), (255, 255, 255), cv2.MARKER_CROSS, 22, 1)
        return img


def _etiqueta(img: np.ndarray, texto: str, origen: tuple, color: tuple) -> None:
    """Texto con fondo oscuro, legible sobre cualquier color."""
    x, y = int(origen[0]), int(origen[1])
    (tw, th), _ = cv2.getTextSize(texto, cv2.FONT_HERSHEY_SIMPLEX, .45, 1)
    cv2.rectangle(img, (x - 3, y - th - 4), (x + tw + 3, y + 4), (20, 20, 20), -1)
    cv2.putText(img, texto, (x, y), cv2.FONT_HERSHEY_SIMPLEX, .45, color, 1, cv2.LINE_AA)


# ---------------------------------------------------------------------------------------------------------------------
# Puente con el orquestador real (garbi.producto.orquestador.Orquestador)
# ---------------------------------------------------------------------------------------------------------------------

def eventos_nuevos(anteriores: list[str], actuales: list[str]) -> list[str]:
    """Los eventos de `actuales` que no estaban en `anteriores` (listas del más viejo al más nuevo, con tope)."""
    for k in range(min(len(anteriores), len(actuales)), 0, -1):
        if anteriores[-k:] == actuales[:k]:
            return actuales[k:]
    return list(actuales)


class PuenteOrquestador:
    """Hace seguro entre hilos al `Orquestador` real (que no lo es) y le da la interfaz de la app.

    El bucle de control (30 Hz) hace, en cada fotograma:

        with puente.cerrojo:
            orden = orquestador.paso(vista, obs)
        puente.publicar(imagenes, vista)

    y la app llama a `comando`, `estado_app` e `imagenes_anotadas` desde su hilo. El cerrojo solo se toma lo que dura
    un `paso` (milisegundos), así que una EMERGENCIA llega en el mismo fotograma. Los eventos del orquestador (del más
    viejo al más nuevo y sin hora) salen con hora y del más nuevo al más viejo, como los espera la app.
    `anotar(img_top, vista)` dibuja las detecciones (normalmente `VisionProducto.anotar`)."""

    def __init__(self, orquestador, anotar: Callable | None = None, reloj: Callable[[], float] = time.time):
        self.orquestador = orquestador
        self.anotar = anotar
        self.cerrojo = threading.RLock()
        self._reloj = reloj
        self._imagenes: dict = {}
        self._vista = None
        self._vistos: list[str] = []
        self._eventos: deque[str] = deque(maxlen=60)

    def publicar(self, imagenes: dict, vista) -> None:
        """Lo llama el bucle tras cada paso: últimas imágenes (sin anotar) y la Vista con la que se anotan."""
        self._imagenes, self._vista = imagenes, vista   # asignación atómica: la app lee la pareja que haya

    def comando(self, comando: Comando) -> None:
        with self.cerrojo:
            self.orquestador.comando(comando)

    def estado_app(self) -> EstadoApp:
        with self.cerrojo:
            e = self.orquestador.estado_app()
            actuales = list(e.eventos)
            hora = time.strftime("%H:%M:%S", time.localtime(self._reloj()))
            for ev in eventos_nuevos(self._vistos, actuales):
                self._eventos.appendleft(f"{hora} · {ev}")
            self._vistos = actuales
            e.eventos = list(self._eventos)
            return e

    def imagenes_anotadas(self) -> dict[str, Imagen]:
        imagenes, vista = self._imagenes, self._vista
        salida = dict(imagenes)
        top = imagenes.get("top")
        if self.anotar is not None and top is not None and vista is not None and isinstance(top, np.ndarray):
            try:
                salida["top"] = self.anotar(top.copy(), vista)
            except Exception:   # un fallo al dibujar no puede tumbar la app
                salida["top"] = top
        return salida


class DemoSistema(PuenteOrquestador):
    """La demo del producto con el orquestador real: `garbi.producto.__main__.crear_demo` (robot, cámaras y escena
    falsos) corriendo en su propio hilo a `hz`, y las detecciones dibujadas por `VisionProducto.anotar`."""

    def __init__(self, sistema, anotar: Callable | None = None):
        super().__init__(sistema.orquestador, anotar)
        self.sistema = sistema
        self._parar = threading.Event()
        self._hilo = threading.Thread(target=self._bucle, name="garbi-control-demo", daemon=True)

    @classmethod
    def crear(cls, cfg=None) -> "DemoSistema":
        from garbi.producto.__main__ import crear_demo
        from garbi.producto.config import cargar_config

        cfg = cfg or cargar_config()
        sistema = crear_demo(cfg)
        anotar = None
        try:
            from garbi.producto.vision import VisionProducto

            anotar = VisionProducto(cfg).anotar
        except Exception as e:   # sin visión: imágenes sin anotar
            logging.getLogger(__name__).warning("Sin VisionProducto para anotar (%s)", e)
        return cls(sistema, anotar)

    def arrancar(self) -> "DemoSistema":
        self._hilo.start()
        return self

    def parar(self) -> None:
        self._parar.set()
        self._hilo.join(timeout=2)

    def _bucle(self) -> None:
        periodo = 1.0 / self.sistema.hz
        while not self._parar.is_set():
            inicio = time.perf_counter()
            with self.cerrojo:
                self.sistema.paso()
            self.publicar(self.sistema.imagenes, self.sistema.vista)
            time.sleep(max(0.0, periodo - (time.perf_counter() - inicio)))
