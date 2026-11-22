"""Fusión del seguimiento por cámara con la antorcha del alumno: una `Muestra` del contrato por fotograma.

Por qué así:
- **La cámara marca el ritmo.** La posición solo existe cuando la cámara ve el LED (30-60 Hz); la antorcha manda
  gatillo y cuaternión a 100 Hz. Por cada fotograma se toma la **última lectura de la antorcha anterior al instante
  de captura** (no la última que haya llegado cuando se termina de procesar la imagen): si el fotograma tardó
  20 ms en procesarse, el gatillo y el ángulo siguen siendo los del instante en que se tomó la foto.
- **Una lectura vieja no vale.** Si la última lectura tiene más de `EDAD_MAX_LECTURA` s (cable suelto, placa
  reiniciándose) la muestra sale con el gatillo suelto y sin ángulos: no se puntúa como soldado lo que no se sabe.
- **El LED solo luce con el gatillo** (firmware): al soltarlo la cámara deja de ver la punta. Para que el evaluador
  sepa que se soltó (aviso "has soltado el gatillo" y borde del hueco), en la transición se emite **una** muestra
  con el gatillo suelto en la última posición conocida, si es reciente.
- **Ángulos con tara y giro de la pieza.** `angulos_antorcha(q, q_tara, giro)` necesita el giro de la pieza
  respecto a la que había durante la tara: se guarda el giro de la pieza en el momento de la tara y se resta del
  giro actual (el del anclaje detectado por el ArUco, o el medido sobre la mesa si se tiene).
"""
from __future__ import annotations

from collections import deque
from dataclasses import replace

from lewelder.antorcha import LecturaAntorcha, angulos_antorcha
from lewelder.contrato import ANCLAJES, Muestra

EDAD_MAX_LECTURA = 0.25  # s: lectura de la antorcha más vieja que esto = antorcha desconectada
EDAD_MAX_POSICION = 0.3  # s: la muestra de "gatillo soltado" solo se emite si la última posición es reciente
TAM_BUFFER = 64  # lecturas guardadas (0,64 s a 100 Hz)


def giro_de_pieza(anclaje: str | None, en_mesa: tuple[float, float, float] | None = None) -> float:
    """Giro (grados) de la pieza alrededor de la vertical: el medido sobre la mesa si se tiene; si no, el del
    anclaje del contrato; 0 si no se sabe dónde está."""
    if en_mesa is not None:
        return float(en_mesa[2])
    if anclaje in ANCLAJES:
        return ANCLAJES[anclaje].giro
    return 0.0


def _diferencia_angular(a: float, b: float) -> float:
    return (a - b + 180.0) % 360.0 - 180.0


class Fusion:
    """Une posiciones de la cámara (`Muestra` con gatillo False y sin ángulos, como las da `Seguidor.procesar`) con
    lecturas de la antorcha (`LecturaAntorcha`).

    Uso: `anadir_lectura` con cada lectura de la antorcha (o `anadir_lecturas` con las de la cola) y `fusionar` con
    cada fotograma. Los instantes (`instante`, `LecturaAntorcha.recibido`) son del mismo reloj (`time.monotonic`).
    """

    def __init__(self, edad_max: float = EDAD_MAX_LECTURA):
        self.edad_max = edad_max
        self.lecturas: deque[LecturaAntorcha] = deque(maxlen=TAM_BUFFER)
        self.q_tara = None
        self.giro_tara: float | None = None  # giro de la pieza durante la tara
        self._gatillo_anterior = False
        self._ultima_posicion: Muestra | None = None

    # --- antorcha --------------------------------------------------------------------------------------------
    def anadir_lectura(self, lectura: LecturaAntorcha) -> None:
        self.lecturas.append(lectura)

    def anadir_lecturas(self, lecturas) -> None:
        for lectura in lecturas:
            self.anadir_lectura(lectura)

    def lectura_en(self, instante: float | None) -> LecturaAntorcha | None:
        """La última lectura recibida no después de `instante` (None = la última que haya). Si todas son
        posteriores (el fotograma es más viejo que el buffer), la más antigua."""
        if not self.lecturas:
            return None
        if instante is None:
            return self.lecturas[-1]
        for lectura in reversed(self.lecturas):
            if lectura.recibido <= instante:
                return lectura
        return self.lecturas[0]

    def tara(self, giro_pieza: float = 0.0, lectura: LecturaAntorcha | None = None) -> bool:
        """Guarda la orientación actual (o la de `lectura`) como tara, junto con el giro de la pieza en ese momento.
        False si no hay lectura con IMU."""
        lectura = lectura or (self.lecturas[-1] if self.lecturas else None)
        if lectura is None or lectura.q is None:
            return False
        self.q_tara = lectura.q
        self.giro_tara = giro_pieza
        return True

    def angulos(self, lectura: LecturaAntorcha | None, giro_pieza: float = 0.0) -> tuple[float | None, float | None]:
        if lectura is None or self.q_tara is None:
            return None, None
        giro = _diferencia_angular(giro_pieza, self.giro_tara or 0.0)
        return angulos_antorcha(lectura.q, self.q_tara, giro)

    # --- fusión ----------------------------------------------------------------------------------------------
    def fusionar(self, posicion: Muestra | None, t: float, instante: float | None = None,
                 giro_pieza: float = 0.0) -> Muestra | None:
        """Muestra fusionada del fotograma de tiempo `t` (s, reloj de la fuente) capturado en `instante`
        (monotónico, o None para usar la última lectura).

        `posicion` es lo que dio el seguimiento (None si no se vio el LED). Devuelve None si no hay nada que
        emitir; una muestra con el gatillo suelto en la última posición si justo se acaba de soltar el gatillo.
        """
        lectura = self.lectura_en(instante)
        if lectura is not None and instante is not None and instante - lectura.recibido > self.edad_max:
            lectura = None  # antorcha callada: no sabemos si aprieta
        gatillo = bool(lectura.gatillo) if lectura is not None else False
        trabajo, avance = self.angulos(lectura, giro_pieza)
        soltado = self._gatillo_anterior and not gatillo
        self._gatillo_anterior = gatillo

        if posicion is not None:
            muestra = Muestra(t=t, x=posicion.x, y=posicion.y, z=posicion.z, gatillo=gatillo,
                              angulo_trabajo=trabajo, angulo_avance=avance)
            self._ultima_posicion = muestra
            return muestra
        ultima = self._ultima_posicion
        if soltado and ultima is not None and t - ultima.t <= EDAD_MAX_POSICION:
            muestra = replace(ultima, t=t, gatillo=False)
            self._ultima_posicion = muestra
            return muestra
        return None

    def reiniciar_trazo(self) -> None:
        """Olvida la última posición (p. ej. al empezar una pasada nueva)."""
        self._ultima_posicion = None
        self._gatillo_anterior = False
