"""Registro y evidencias de Garbi (M7).

- **Por ciclo**: una línea JSON en `registros/AAAAMMDD.jsonl` con el acierto, la viruta antes y después, la duración y
  por qué falló. Es la prueba de fiabilidad para el jurado.
- **Rerun** (opcional): las dos cámaras, la escena, el estado y las órdenes en una línea de tiempo. Solo si `rerun`
  está instalado (no es una dependencia obligatoria); si no, no hace nada.

Qué es un ciclo (`DetectorCiclos`): desde que Garbi sale de APARCADO hasta que vuelve a él (seguir, acompañar,
limpiar los agujeros, revisar y aparcar). La viruta se mide con `Escena.viruta` (píxeles alrededor de cada agujero):
«antes» es el máximo de la suma durante el ciclo (justo después de taladrar) y «después», la suma al volver a
APARCADO. Acierto: en ningún agujero queda viruta; si la escena trae `viruta_fraccion` (percepción por píxeles),
fracción del círculo < `umbral_fraccion` (2 %, como el ciclo); si no, `viruta` ≤ `umbral_limpio`.

Si el `Ciclo` (T2) sabe más (por qué abandonó un agujero, contactos), puede publicar resúmenes propios con
`RegistroCiclos.anotar(ResumenCiclo(...))` o con el campo `motivo_fallo`.
"""
from __future__ import annotations

import json
import logging
import time
import unicodedata
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

import numpy as np

log = logging.getLogger(__name__)

CARPETA = Path("registros")
UMBRAL_LIMPIO = 20  # píxeles de viruta por agujero que se aceptan como «limpio» (ruido de la máscara)


@dataclass
class ResumenCiclo:
    acierto: bool
    viruta_antes: int
    viruta_despues: int
    duracion: float  # s
    motivo_fallo: str | None = None
    agujeros: int = 0
    modo: str = ""  # "sim" o "real"
    inicio: str = ""  # hora local ISO del principio del ciclo
    estados: list[str] = field(default_factory=list)  # estados por los que pasó, en orden y sin repetir seguidos
    extra: dict = field(default_factory=dict)


class RegistroCiclos:
    """Añade cada `ResumenCiclo` como una línea JSON al archivo del día."""

    def __init__(self, carpeta: str | Path = CARPETA, reloj=datetime.now):
        self.carpeta = Path(carpeta)
        self.reloj = reloj

    def archivo(self) -> Path:
        return self.carpeta / f"{self.reloj():%Y%m%d}.jsonl"

    def anotar(self, resumen: ResumenCiclo | dict) -> Path:
        datos = asdict(resumen) if isinstance(resumen, ResumenCiclo) else dict(resumen)
        datos.setdefault("hora", self.reloj().isoformat(timespec="seconds"))
        ruta = self.archivo()
        ruta.parent.mkdir(parents=True, exist_ok=True)
        with ruta.open("a", encoding="utf-8") as f:
            f.write(json.dumps(datos, ensure_ascii=False, default=_a_json) + "\n")
        return ruta


def _a_json(v):
    if isinstance(v, np.generic):
        return v.item()
    if isinstance(v, np.ndarray):
        return v.tolist()
    return str(v)


def normalizar_estado(estado) -> str:
    """«ACOMPAÑAR», «Ir a limpiar», `Estado.IR_A_LIMPIAR` → «acompanar», «ir_a_limpiar»."""
    texto = str(getattr(estado, "value", estado)).strip().lower().replace(" ", "_")
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()


class DetectorCiclos:
    """Mira el par (escena, orden) de cada paso del bucle y, al cerrarse un ciclo, devuelve su `ResumenCiclo` (y lo
    anota en el registro, si hay)."""

    def __init__(self, registro: RegistroCiclos | None = None, modo: str = "", estado_reposo: str = "aparcado",
                 umbral_limpio: int = UMBRAL_LIMPIO, reloj=time.monotonic, umbral_fraccion: float | None = None):
        from garbi.tipos import UMBRAL_FRACCION_VIRUTA

        self.registro = registro
        self.modo = modo
        self.reposo = normalizar_estado(estado_reposo)
        self.umbral_limpio = umbral_limpio
        self.umbral_fraccion = UMBRAL_FRACCION_VIRUTA if umbral_fraccion is None else umbral_fraccion
        self.reloj = reloj
        self.resumenes: list[ResumenCiclo] = []
        self._en_ciclo = False

    @property
    def en_ciclo(self) -> bool:
        return self._en_ciclo

    def _empezar(self, escena) -> None:
        self._en_ciclo = True
        self._t0 = self.reloj()
        self._inicio = datetime.now().isoformat(timespec="seconds")
        self._estados: list[str] = []
        self._pico = 0
        self._agujeros: set[int] = set()
        self._motivo: str | None = None

    def paso(self, escena, orden) -> ResumenCiclo | None:
        estado = normalizar_estado(orden.estado)
        if not self._en_ciclo:
            if estado == self.reposo:
                return None
            self._empezar(escena)
        if not self._estados or self._estados[-1] != estado:
            self._estados.append(estado)
        viruta = dict(getattr(escena, "viruta", {}) or {})
        self._agujeros.update(viruta)
        self._pico = max(self._pico, int(sum(viruta.values())))
        detalle = getattr(orden, "detalle", "") or ""
        if any(p in detalle.lower() for p in ("guardia", "falla", "fallo", "abandona", "contacto")):
            self._motivo = detalle
        if estado != self.reposo:
            return None
        # vuelta al reposo: se cierra el ciclo
        self._en_ciclo = False
        fraccion = dict(getattr(escena, "viruta_fraccion", {}) or {})
        sucios = {k: v for k, v in viruta.items()
                  if (fraccion[k] >= self.umbral_fraccion if k in fraccion else v > self.umbral_limpio)}
        despues = int(sum(viruta.values()))
        motivo = self._motivo
        if sucios and motivo is None:
            motivo = "queda viruta en " + ", ".join(f"agujero {k} ({v} px)" for k, v in sorted(sucios.items()))
        resumen = ResumenCiclo(acierto=not sucios and self._motivo is None, viruta_antes=max(self._pico, despues),
                               viruta_despues=despues, duracion=round(self.reloj() - self._t0, 2),
                               motivo_fallo=motivo, agujeros=len(self._agujeros), modo=self.modo,
                               inicio=self._inicio, estados=self._estados)
        self.resumenes.append(resumen)
        if self.registro is not None:
            self.registro.anotar(resumen)
        return resumen


class RerunOpcional:
    """Línea de tiempo en Rerun si está instalado y se pide; si no, todos los métodos no hacen nada."""

    def __init__(self, activo: bool = True, nombre: str = "garbi", abrir_visor: bool = True):
        self.rr = None
        if not activo:
            return
        try:
            import rerun as rr
        except ImportError:
            log.info("rerun no está instalado: sin línea de tiempo (pip install rerun-sdk)")
            return
        rr.init(nombre, spawn=abrir_visor)
        self.rr = rr

    @property
    def activo(self) -> bool:
        return self.rr is not None

    def paso(self, t: float, imagenes: dict | None = None, escena=None, orden=None, q=None) -> None:
        rr = self.rr
        if rr is None:
            return
        rr.set_time("t", duration=float(t))
        for nombre, img in (imagenes or {}).items():
            rr.log(f"camaras/{nombre}", rr.Image(img))
        if q is not None:
            rr.log("q", rr.Scalars(np.asarray(q, dtype=float)))
        if orden is not None:
            rr.log("orden/q", rr.Scalars(np.asarray(orden.q, dtype=float)))
            rr.log("orden/aspirar", rr.Scalars(float(orden.aspirar)))
            rr.log("orden/estado", rr.TextLog(f"{orden.estado} {orden.detalle}".strip()))
        if escena is not None:
            if escena.viruta:
                rr.log("escena/viruta", rr.Scalars(float(sum(escena.viruta.values()))))
            rr.log("escena/taladro_visible", rr.Scalars(float(escena.taladro.visible)))
