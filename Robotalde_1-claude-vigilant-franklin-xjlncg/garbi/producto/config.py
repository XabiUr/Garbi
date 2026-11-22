"""Configuración del producto Garbi (`garbi/producto/garbi_producto.yaml`).

    from garbi.producto.config import cargar_config
    cfg = cargar_config()                          # garbi/producto/garbi_producto.yaml; lo que falte toma el valor por defecto de estas dataclasses
    cfg.tiempos.quieto_desde_reposo                # 1.0 s

Todo lo que pone «MEDIR» en el yaml es un valor de ejemplo: hay que medirlo en el sitio. Unidades: articulaciones en
grados de LeRobot (pinza 0-100), posiciones en píxeles de la cámara de arriba, tiempos en segundos.

El mismo yaml lo lee la visión del producto (`garbi.producto.vision.VisionProducto`): su sección `vision:` y la
clave de primer nivel `tapete_px` (la escribe `python -m garbi.producto.vision --marcar-tapete`). Este objeto
expone `.vision` y `.tapete_px`, así que se le puede pasar tal cual: `VisionProducto(cfg)`.
"""
from __future__ import annotations

import dataclasses
import logging
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

log = logging.getLogger("garbi.producto")

RUTA_DEFECTO = Path(__file__).with_name("garbi_producto.yaml")


@dataclass
class Puertos:
    follower: str = "/dev/ttyACM0"          # MEDIR: puerto del SO-101 seguidor
    aspiradora: str | None = None           # None = sin Arduino: modo manual (la aspiradora se enciende con el pie)


@dataclass
class Camaras:
    top: int | str = 0                      # MEDIR: índice o ruta de la cámara de arriba
    wrist: int | str = 1                    # MEDIR: índice o ruta de la cámara de la muñeca
    # (ancho, alto) por cámara; vacío = 640 × 480. El dataset del equipo: top 640 × 360, wrist 640 × 480
    resolucion: dict[str, list[int]] = field(default_factory=dict)


@dataclass
class ConfigACT:
    modelo: str = "salidas/garbi_act/checkpoints/last/pretrained_model"  # carpeta local o repo del Hub
    dispositivo: str = "cpu"
    # nombre de la cámara en el modelo → nombre en la observación de Garbi; vacío = automático (top/wrist y alias)
    camaras: dict[str, str] = field(default_factory=dict)
    estado: str = "medido"                  # "medido" (lerobot-record) o "orden" (la acción anterior)
    ensemble: float | None = None           # coeficiente del ensemble temporal de ACT (p. ej. 0.01); None = sin él
    umbral_llegada: float = 0.5             # grados: la acción ya no cambia más que esto...
    pasos_llegada: int = 15                 # ...durante estos pasos seguidos → ha llegado
    tiempo_max: float = 12.0                # s: si no converge, se da por llegado a los X s
    tarea: str = "Approach the drill bit."


@dataclass
class ConfigCirculo:
    postura_intermedia: list[float] | None = None  # postura segura de despliegue (6 grados) o None = directo
    velocidad: float = 60.0                 # °/s pico por articulación
    tolerancia: float = 1.0                 # grados para dar por alcanzado el destino
    actualizar_px: float = 4.0              # si el círculo se mueve más de esto (y menos que el rango), se re-apunta


@dataclass
class ConfigMatriz:
    ruta: str = "matriz.csv"                # MEDIR: el archivo que marcó el equipo (CSV o JSON)
    posicion: str = "auto"                  # "auto", "uv" (px de la cámara de arriba) o "xy" (mm del tapete)
    tapete_mm: list[float] = field(default_factory=lambda: [600.0, 400.0])  # ancho, alto del tapete si va en mm
    wrist_roll: float = 0.0                 # si la matriz no trae wrist_roll
    pinza: float = 0.0                      # si la matriz no trae la pinza (5 articulaciones)
    extrapolar_max_px: float = 80.0         # fuera de la rejilla: más allá de esto se avisa y se recorta


@dataclass
class Tiempos:
    quieto_desde_reposo: float = 1.0        # s de círculo quieto (con mano + taladro) para acercarse desde REPOSO
    quieto_desde_despierto: float = 2.0     # ídem desde DESPIERTO
    rango_salida_px: float = 60.0           # el círculo se aleja más que esto del punto de llegada → DESPIERTO
    perdido: float = 0.7                    # s sin mano + taladro antes de darlo por ido (EN_BROCA, ACERCAMIENTO)
    sin_taladro_limpiar: float = 5.0        # s sin taladro en escena (tras ≥1 agujero) → LIMPIEZA_TABLA
    sin_tabla: float = 1.5                  # s sin ver la tabla (tras haberla visto) → LIMPIEZA_TAPETE
    tolerancia_reposo: float = 3.0          # grados: «ya está en reposo»


@dataclass
class Barridos:
    paso_px: float = 30.0                   # separación entre pasadas del zigzag (px)
    margen_px: float = 10.0                 # margen hacia dentro desde el borde (px)
    offset_tabla: list[float] = field(default_factory=lambda: [0.0, -8.0, 4.0, 0.0, 0.0, 0.0])    # MEDIR
    offset_tapete: list[float] = field(default_factory=lambda: [0.0, -6.0, 3.0, 0.0, 0.0, 0.0])   # MEDIR
    velocidad: float = 40.0                 # °/s por articulación en los barridos
    aceleracion: float = 120.0              # °/s² (rampas de arranque y parada)


@dataclass
class ConfigProducto:
    puertos: Puertos = field(default_factory=Puertos)
    camaras: Camaras = field(default_factory=Camaras)
    id_robot: str = "garbi"
    # True = grados; False = unidades normalizadas de LeRobot (-100..100), como grabó el equipo su dataset y matriz
    use_degrees: bool = True
    # 6 grados (pan, lift, elbow, flex, roll, pinza). MEDIR: por defecto, girado a la derecha.
    postura_reposo: list[float] = field(default_factory=lambda: [-60.0, -100.0, 95.0, 60.0, 0.0, 0.0])
    postura_despierto: list[float] = field(default_factory=lambda: [0.0, -60.0, 60.0, 40.0, 0.0, 0.0])  # MEDIR
    politica: str = "act"                   # "act" o "circulo"
    act: ConfigACT = field(default_factory=ConfigACT)
    circulo: ConfigCirculo = field(default_factory=ConfigCirculo)
    matriz: ConfigMatriz = field(default_factory=ConfigMatriz)
    act_desde: str = "reposo"               # "reposo" (como en el entrenamiento) o "despierto"
    tiempos: Tiempos = field(default_factory=Tiempos)
    barridos: Barridos = field(default_factory=Barridos)
    velocidad_max: float | list[float] = 90.0   # °/s por articulación en TODAS las órdenes (o una lista de 6)
    movimiento_fijo: float = 60.0           # °/s pico de los movimientos fijos (a reposo, a despierto)
    wrist_roll_fijo: float | None = None    # None = como venga (dataset/matriz); un número = se fuerza
    pinza_fija: float | None = None         # ídem para la pinza
    hz: float = 30.0
    # esquinas del tapete en la cámara de arriba (px), compartidas con la visión. MEDIR (--marcar-tapete)
    tapete_px: list[list[float]] = field(default_factory=lambda: [[80, 60], [560, 60], [560, 420], [80, 420]])
    vision: dict = field(default_factory=dict)   # sección de la visión (garbi.producto.vision.POR_DEFECTO)

    # --- derivadas --------------------------------------------------------------------------------------------
    @property
    def q_reposo(self) -> np.ndarray:
        return _vec6(self.postura_reposo, "postura_reposo")

    @property
    def q_despierto(self) -> np.ndarray:
        return _vec6(self.postura_despierto, "postura_despierto")

    @property
    def vmax(self) -> np.ndarray:
        v = np.asarray(self.velocidad_max, float)
        return np.full(6, float(v)) if v.ndim == 0 else _vec6(v, "velocidad_max")

    @property
    def esquinas_tapete(self) -> np.ndarray:
        return np.asarray(self.tapete_px, float).reshape(4, 2)

    def validar(self) -> ConfigProducto:
        if self.politica not in ("act", "circulo"):
            raise ValueError(f"politica debe ser 'act' o 'circulo', no {self.politica!r}")
        if self.act_desde not in ("reposo", "despierto"):
            raise ValueError(f"act_desde debe ser 'reposo' o 'despierto', no {self.act_desde!r}")
        if self.act.estado not in ("medido", "orden"):
            raise ValueError(f"act.estado debe ser 'medido' u 'orden', no {self.act.estado!r}")
        if self.matriz.posicion not in ("auto", "uv", "xy"):
            raise ValueError(f"matriz.posicion debe ser 'auto', 'uv' o 'xy', no {self.matriz.posicion!r}")
        self.q_reposo, self.q_despierto, self.vmax, self.esquinas_tapete  # noqa: B018 (comprueba formas)
        return self


def _vec6(v, nombre: str) -> np.ndarray:
    a = np.asarray(v, float).reshape(-1)
    if a.shape != (6,):
        raise ValueError(f"{nombre} necesita 6 valores, tiene {a.size}")
    return a


def _rellenar(cls, datos: dict | None, ruta: str = ""):
    """Construye la dataclass `cls` con `datos` (anidado), avisando de las claves que no conoce."""
    datos = dict(datos or {})
    campos = {f.name: f for f in dataclasses.fields(cls)}
    kwargs = {}
    for k, v in datos.items():
        if k not in campos:
            log.warning("configuración: clave desconocida %s%s (se ignora)", ruta, k)
            continue
        tipo = campos[k].default_factory if campos[k].default_factory is not dataclasses.MISSING else None
        if tipo is not None and dataclasses.is_dataclass(tipo) and isinstance(v, dict):
            kwargs[k] = _rellenar(tipo, v, f"{ruta}{k}.")
        else:
            kwargs[k] = v
    return cls(**kwargs)


def config_desde_dict(datos: dict | None) -> ConfigProducto:
    datos = dict(datos or {})
    barridos = datos.get("barridos")
    if isinstance(barridos, dict) and "tapete_px" in barridos:   # sitio antiguo de la clave
        barridos = dict(barridos)
        datos.setdefault("tapete_px", barridos.pop("tapete_px"))
        datos["barridos"] = barridos
    if datos.get("tapete_px") is None:
        datos.pop("tapete_px", None)
    return _rellenar(ConfigProducto, datos).validar()


def cargar_config(ruta: str | Path | None = None) -> ConfigProducto:
    """Lee el yaml (por defecto `garbi/producto/garbi_producto.yaml`). Si no existe, los valores por defecto."""
    import yaml

    ruta = Path(ruta) if ruta is not None else RUTA_DEFECTO
    if not ruta.exists():
        log.warning("no existe %s: uso la configuración por defecto", ruta)
        return ConfigProducto().validar()
    return config_desde_dict(yaml.safe_load(ruta.read_text(encoding="utf-8")) or {})
