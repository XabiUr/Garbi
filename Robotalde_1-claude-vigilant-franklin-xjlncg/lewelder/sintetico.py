"""Pasadas de soldadura sintéticas y reproducibles.

Sirven para probar las métricas sin hardware y para alimentar los simuladores de las otras partes (servidor,
tablet, robot) con trazos que se parecen a los de una persona: se coloca un poco antes del cordón con el gatillo
suelto, aprieta, avanza a velocidad constante (con temblor, desvío, paradas o huecos si se le pide), suelta el
gatillo un poco después del final y se queda quieta un momento.

Todo en el marco de la pieza y en mm, s y grados (ver `lewelder.contrato`). Con la misma semilla sale siempre la
misma pasada.

Altura de la punta: en la v1 la punta va a `ALTURA_PUNTA` (3 mm, sin tocar); en las juntas v2 (`TipoJunta`, o el
texto "esquina") se suelda con la punta **apoyada** y va a `ALTURA_APOYADA` por defecto. `levantada` sube la punta a
`altura_levantada` en unos tramos sin soltar el gatillo (el fallo de "soldar al aire").
"""
from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from lewelder.contrato import ALTURA_APOYO, ALTURA_PUNTA, LONGITUD_CORDON, Muestra
from lewelder.metricas import clave_tipo, es_junta_v2

ALTURA_APOYADA = ALTURA_APOYO / 4  # mm: punta apoyada (el LED queda algo por encima del contacto)
ALTURA_LEVANTADA = 5.0  # mm: la distancia que el estéreo tiene que distinguir del apoyo (spec v2, 7)

# La persona empieza y termina unos milímetros fuera del cordón, y se queda quieta (gatillo suelto) un momento.
MARGEN_ANTES = 6.0  # mm
MARGEN_DESPUES = 6.0  # mm
TIEMPO_QUIETO = 0.5  # s, antes de apretar y después de soltar
# El temblor es ruido suavizado (la mano no tiembla a 60 Hz): media móvil de esta duración.
CORRELACION_TEMBLOR = 0.15  # s


def _temblor(rng: np.random.Generator, n: int, frecuencia: float, amplitud: float) -> np.ndarray:
    """Ruido gaussiano suavizado de n muestras con desviación típica `amplitud` (mm)."""
    if amplitud <= 0 or n == 0:
        return np.zeros(n)
    ancho = max(1, int(round(CORRELACION_TEMBLOR * frecuencia)))
    blanco = rng.standard_normal(n + ancho - 1)
    suave = np.convolve(blanco, np.ones(ancho) / ancho, mode="valid")
    suave -= suave.mean()
    std = suave.std()
    return suave * (amplitud / std) if std > 0 else suave


def pasada_sintetica(
    tipo,
    *,
    velocidad: float = 5.0,
    frecuencia: float = 60,
    huecos: Sequence[tuple[float, float]] = (),
    temblor_mm: float = 0.0,
    desvio_mm: float = 0.0,
    paradas: Sequence[tuple[float, float]] = (),
    angulo_trabajo: float | None = None,
    angulo_avance: float | None = None,
    ruido_angulo: float = 0.0,
    semilla: int = 0,
    altura_punta: float | None = None,
    levantada: Sequence[tuple[float, float]] = (),
    altura_levantada: float = ALTURA_LEVANTADA,
) -> list[Muestra]:
    """Genera una pasada sintética sobre una pieza (v1: `TipoPieza`) o una junta (v2: `TipoJunta`) de tipo `tipo`.

    - `velocidad`: avance en mm/s mientras se suelda.
    - `frecuencia`: muestras por segundo.
    - `huecos`: intervalos (inicio_mm, fin_mm) de X en los que el gatillo está suelto (la mano sigue avanzando).
    - `temblor_mm`: desviación típica del temblor de la punta en X e Y (en Z, la mitad).
    - `desvio_mm`: desplazamiento lateral constante en Y respecto al cordón.
    - `paradas`: (x_mm, segundos): al llegar a x_mm la punta se queda quieta ese tiempo con el gatillo apretado.
    - `angulo_trabajo`, `angulo_avance`: valor medio de los ángulos (grados), o None si no hay IMU.
    - `ruido_angulo`: desviación típica del ruido de los ángulos (grados).
    - `altura_punta`: altura media de la punta (mm); None = `ALTURA_PUNTA` en la v1 y `ALTURA_APOYADA` en la v2.
    - `levantada`: intervalos (inicio_mm, fin_mm) de X en los que la punta sube a `altura_levantada` (el gatillo
      sigue como diga `huecos`).
    """
    clave_tipo(tipo)  # valida el tipo (la trayectoria es la misma para todas las juntas)
    if altura_punta is None:
        altura_punta = ALTURA_APOYADA if es_junta_v2(tipo) else ALTURA_PUNTA
    rng = np.random.default_rng(semilla)
    dt = 1.0 / frecuencia
    x_ini, x_fin = -MARGEN_ANTES, LONGITUD_CORDON + MARGEN_DESPUES
    pendientes = sorted((float(x), float(s)) for x, s in paradas)

    # Trayectoria ideal: quieto, avance con paradas, quieto.
    xs: list[float] = []
    apretado: list[bool] = []
    alto: list[bool] = []
    n_quieto = int(round(TIEMPO_QUIETO * frecuencia))
    xs += [x_ini] * n_quieto
    apretado += [False] * n_quieto
    alto += [False] * n_quieto
    x, pausa = x_ini, 0.0
    while x < x_fin:
        xs.append(x)
        apretado.append(not any(a <= x < b for a, b in huecos))
        alto.append(any(a <= x < b for a, b in levantada))
        if pausa > 1e-9:
            pausa -= dt
            continue
        x_sig = x + velocidad * dt
        if pendientes and x_sig >= pendientes[0][0] > x:
            x_sig, pausa = pendientes.pop(0)
        x = x_sig
    xs += [x_fin] * n_quieto
    apretado += [False] * n_quieto
    alto += [False] * n_quieto

    n = len(xs)
    ruido_x = _temblor(rng, n, frecuencia, temblor_mm)
    ruido_y = _temblor(rng, n, frecuencia, temblor_mm)
    ruido_z = _temblor(rng, n, frecuencia, temblor_mm / 2)
    ang_t = ang_a = None
    if angulo_trabajo is not None:
        ang_t = angulo_trabajo + ruido_angulo * rng.standard_normal(n)
    if angulo_avance is not None:
        ang_a = angulo_avance + ruido_angulo * rng.standard_normal(n)

    return [
        Muestra(
            t=float(i * dt),
            x=float(xs[i] + ruido_x[i]),
            y=float(desvio_mm + ruido_y[i]),
            # la punta no se mete en la chapa
            z=float(max(0.0, (altura_levantada if alto[i] else altura_punta) + ruido_z[i])),
            gatillo=bool(apretado[i]),
            angulo_trabajo=None if ang_t is None else float(ang_t[i]),
            angulo_avance=None if ang_a is None else float(ang_a[i]),
        )
        for i in range(n)
    ]
