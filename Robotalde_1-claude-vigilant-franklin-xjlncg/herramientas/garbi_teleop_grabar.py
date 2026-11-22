"""Teleoperación leader → follower de Garbi grabando episodios de ACERCAMIENTO en un LeRobotDataset (para ACT).

    python herramientas/garbi_teleop_grabar.py --puerto COM5 --leader COM6 --aspiradora COM7 --top 0 --wrist 1 \\
        --salida datos/garbi_acercamiento --repo-id USUARIO/garbi_acercamiento
    python herramientas/garbi_teleop_grabar.py ... --corte auto --tolerancia 2.0      # corte por la percepción
    python herramientas/garbi_teleop_grabar.py ... --reanudar                         # añadir a un dataset existente
    python herramientas/garbi_teleop_grabar.py ... --push                             # subir al Hub al terminar

Cada fotograma: `observation.images.top`, `observation.images.wrist`, `observation.state` (6), `action` (6) y la
tarea «Approach the drill bit.» (`garbi.tipos.TAREA_ACERCAMIENTO`), a 30 fps.
- `action`: lo que se manda al follower = el leader con el **montaje forzado** (muñeca `wrist_roll` a 0 y pinza
  cerrada), aunque el leader las mueva.
- `observation.state`: con `--estado orden` (por defecto), la orden del paso anterior, como en `garbi.grabador` y como
  la recibe ACT en el ciclo; con `--estado medido`, la postura leída del follower (como `lerobot-record`).
- La aspiradora se enciende durante el episodio (señal serie, `--aspiradora`) y se apaga al acabar.

Postura de partida (`--partida prudente`, por defecto salvo con `--sin-ventana`): ACT se ejecuta desde la **postura
prudente** (la cámara de la muñeca mira la punta de la broca sobre la madera desde 180 mm,
`garbi.acercamiento.postura_prudente`), así que los episodios deben empezar ahí. Cómo:
1. La persona coge el taladro y lo sostiene sobre el punto donde va a taladrar (sin clavar).
2. Tecla **p**: el follower va despacio a la postura prudente de esa broca y se queda quieto (ENGANCHE): la ventana
   dice cuántos grados separan el leader del follower; el operador mueve el leader hasta ponerlo igual (< 5° en todas
   las articulaciones) y entonces el follower vuelve a seguir al leader, sin saltos.
3. La persona clava la broca y el operador hace el acercamiento con el leader (con `--corte auto` el episodio empieza
   solo al clavarse).
Un episodio solo empieza si el follower está a menos de `--tolerancia-partida` grados (8) de la postura prudente de la
broca en ese momento; si no, no graba y lo dice (pulsa p). Con `--partida libre` no se comprueba (no recomendado:
ACT verá al ejecutar una postura de partida distinta). La postura prudente necesita la percepción (`calib/`).

Corte de los episodios:
- `--corte manual` (por defecto): espacio empieza / termina (y guarda), r descarta el episodio en curso (repetir),
  q sale.
- `--corte auto`: la percepción decide: empieza al clavarse la broca y termina al levantarla. Con `--tolerancia S`,
  si la broca vuelve a clavarse antes de S s (recuperación: moverla a otro punto a mitad del acercamiento) el
  episodio sigue; si no, se corta en el momento en que se levantó (lo grabado después se tira). Las teclas siguen
  valiendo (espacio fuerza empezar/terminar, r descarta, q sale). Necesita `calib/` y la percepción calibrada (tapete).
  Solo corta si la broca está clavada **con una mano en el taladro** (`Taladro.agarrado`, MediaPipe o color); si la
  mano no se detecta bien en el sitio, `--sin-agarre` no lo exige. Cuando la broca está apoyada pero no se corta, el
  motivo sale en la consola y en la ventana (p. ej. «no veo una mano en el taladro»).
- Se descartan solos los episodios de menos de `--min-segundos` y los de más de `--max-segundos`.

Contador de grabados/descartados en la ventana; los descartes y su motivo, en `episodios_garbi_acercamiento.json`
dentro del dataset. Antes de empezar, el follower va despacio a la postura del leader (pide Enter).
Ctrl+C: el brazo se queda quieto, la aspiradora se apaga y el episodio en curso se descarta; lo guardado se conserva.
"""
from __future__ import annotations

import argparse
import json
import shutil
import time
from pathlib import Path

import numpy as np

import garbi_comun as comun

from garbi.tipos import HZ_CONTROL, TAREA_ACERCAMIENTO, forzar_montaje  # noqa: E402

ARCHIVO_EPISODIOS = "episodios_garbi_acercamiento.json"
RESOLUCION = (640, 480)
TOLERANCIA_PARTIDA = 8.0  # ° (máx. de las 4 articulaciones) del follower a la postura prudente para empezar
TOLERANCIA_ENGANCHE = 5.0  # ° del leader al follower para soltar el enganche y volver a seguir al leader


def argumentos(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="python herramientas/garbi_teleop_grabar.py", description=__doc__,
                                formatter_class=comun.Ayuda)
    comun.anadir_robot(p)
    p.add_argument("--leader", required=True, help="puerto serie del leader (COM6, /dev/ttyACM1)")
    p.add_argument("--leader-id", default="garbi_leader", help="id de la calibración de LeRobot del leader")
    p.add_argument("--aspiradora", help="puerto serie del Arduino de la aspiradora")
    comun.anadir_camaras(p)
    p.add_argument("--salida", default="datos/garbi_acercamiento", help="carpeta local del LeRobotDataset")
    p.add_argument("--repo-id", default="local/garbi_acercamiento", help="repo del dataset (USUARIO/nombre)")
    p.add_argument("--reanudar", action="store_true", help="añadir episodios a un dataset que ya existe en --salida")
    p.add_argument("--sobrescribir", action="store_true", help="borrar --salida si existe y empezar de cero")
    p.add_argument("--push", action="store_true", help="subir el dataset al Hub al terminar (hf auth login antes)")
    p.add_argument("--corte", choices=("manual", "auto"), default="manual", help="quién corta los episodios")
    p.add_argument("--tolerancia", type=float, default=0.0,
                   help="(auto) s que puede estar levantada la broca sin cortar (recuperaciones)")
    p.add_argument("--min-segundos", type=float, default=1.0, help="episodios más cortos se descartan")
    p.add_argument("--max-segundos", type=float, default=40.0, help="episodios más largos se descartan")
    p.add_argument("--estado", choices=("orden", "medido"), default="orden", help="qué se graba en observation.state")
    p.add_argument("--resolucion", default="640x480", help="ANCHOxALTO de las imágenes del dataset")
    p.add_argument("--calibracion", default="calib", help="carpeta de calib/ (para --corte auto)")
    p.add_argument("--max-salto", type=float, default=10.0, help="max_relative_target del follower (° por paso)")
    p.add_argument("--sin-ventana", action="store_true", help="sin ventana (solo con --corte auto; salir con Ctrl+C)")
    p.add_argument("--sin-agarre", action="store_true",
                   help="(auto) cortar aunque no se vea una mano en el taladro (si MediaPipe/color fallan en el sitio)")
    p.add_argument("--partida", choices=("prudente", "libre"), default=None,
                   help="prudente (por defecto con ventana): los episodios empiezan desde la postura prudente (tecla p); "
                        "libre (por defecto con --sin-ventana): sin comprobar")
    p.add_argument("--tolerancia-partida", type=float, default=TOLERANCIA_PARTIDA,
                   help="° máximos del follower a la postura prudente para empezar un episodio")
    ns = p.parse_args(argv)
    if ns.sin_ventana and ns.corte == "manual":
        p.error("--sin-ventana necesita --corte auto (sin ventana no hay teclas)")
    if ns.partida is None:
        ns.partida = "libre" if ns.sin_ventana else "prudente"
    if ns.sin_ventana and ns.partida == "prudente":
        p.error("--sin-ventana necesita --partida libre (sin ventana no hay tecla p para ir a la postura prudente)")
    if ns.reanudar and ns.sobrescribir:
        p.error("--reanudar y --sobrescribir no van juntos")
    ancho, alto = ns.resolucion.lower().split("x")
    ns.resolucion = (int(ancho), int(alto))
    return ns


# --- dataset de acercamientos ------------------------------------------------------------------------------------
def _reducir(img, resolucion) -> np.ndarray:
    import cv2

    img = np.ascontiguousarray(img)
    if img.shape[1::-1] == tuple(resolucion):
        return img
    return cv2.resize(img, tuple(resolucion), interpolation=cv2.INTER_AREA)


def crear_dataset(salida: Path, repo_id: str, resolucion, reanudar: bool = False, sobrescribir: bool = False):
    """LeRobotDataset nuevo (o reanudado) con las features del SO-101 y las cámaras top y wrist."""
    from lerobot.datasets.lerobot_dataset import LeRobotDataset

    from garbi.demostraciones import ROBOT_TYPE, caracteristicas

    salida = Path(salida)
    if reanudar:
        return LeRobotDataset.resume(repo_id, root=salida, image_writer_threads=4)
    if salida.exists():
        if not sobrescribir:
            raise SystemExit(f"{salida} ya existe: usa --reanudar para añadir episodios o --sobrescribir para borrarlo")
        shutil.rmtree(salida)
    return LeRobotDataset.create(repo_id=repo_id, fps=int(HZ_CONTROL), features=caracteristicas(resolucion),
                                 root=salida, robot_type=ROBOT_TYPE, use_videos=True, image_writer_threads=4)


class GrabadorAcercamiento:
    """Episodios de acercamiento sobre un LeRobotDataset (`ds`: lo que devuelve `crear_dataset`, o un doble).

    `empezar()` → `fotograma(...)` × N → `terminar(guardar, motivo)`. Entre medias, `pausar()` deja los fotogramas en
    espera (broca levantada, quizá una recuperación): `reanudar()` los pasa al dataset y `terminar` los tira (el
    episodio acaba donde se levantó la broca)."""

    def __init__(self, ds, carpeta: Path | None, resolucion=RESOLUCION, min_segundos: float = 1.0,
                 max_segundos: float = 40.0, hz: float = HZ_CONTROL, tarea: str = TAREA_ACERCAMIENTO):
        self.ds = ds
        self.carpeta = None if carpeta is None else Path(carpeta)
        self.resolucion = tuple(resolucion)
        self.min_fotogramas = int(round(min_segundos * hz))
        self.max_fotogramas = int(round(max_segundos * hz))
        self.tarea = tarea
        self.episodios: list[dict] = self._previos()
        self._actual: dict | None = None
        self._espera: list[dict] = []
        self.pausado = False
        self._cerrado = False

    def _previos(self) -> list[dict]:
        if self.carpeta is None or not (self.carpeta / ARCHIVO_EPISODIOS).exists():
            return []
        return json.loads((self.carpeta / ARCHIVO_EPISODIOS).read_text(encoding="utf-8")).get("episodios", [])

    @property
    def grabando(self) -> bool:
        return self._actual is not None

    @property
    def guardados(self) -> int:
        return sum(1 for e in self.episodios if e["guardado"])

    @property
    def descartados(self) -> int:
        return sum(1 for e in self.episodios if not e["guardado"])

    @property
    def fotogramas(self) -> int:
        return 0 if self._actual is None else self._actual["fotogramas"]

    def empezar(self, **info) -> None:
        if self._actual is not None:
            self.terminar(False, motivo="sin terminar")
        self._actual = {"intento": len(self.episodios), "inicio": time.strftime("%H:%M:%S"), **info, "fotogramas": 0,
                        "pausas": 0}
        self._espera, self.pausado = [], False

    def fotograma(self, imagenes: dict, estado, accion) -> str | None:
        """Añade un fotograma. Devuelve "largo" si el episodio pasa de `max_segundos` (hay que terminarlo)."""
        if self._actual is None:
            return None
        frame = {"observation.state": np.asarray(estado, np.float32), "action": np.asarray(accion, np.float32),
                 "task": self.tarea}
        for cam in ("top", "wrist"):
            frame[f"observation.images.{cam}"] = _reducir(imagenes[cam], self.resolucion)
        if self.pausado:
            self._espera.append(frame)
        else:
            self.ds.add_frame(frame)
            self._actual["fotogramas"] += 1
        return "largo" if self._actual["fotogramas"] + len(self._espera) > self.max_fotogramas else None

    def pausar(self) -> None:
        if self._actual is not None and not self.pausado:
            self.pausado = True
            self._actual["pausas"] += 1

    def reanudar(self) -> None:
        for frame in self._espera:
            self.ds.add_frame(frame)
            self._actual["fotogramas"] += 1
        self._espera, self.pausado = [], False

    def terminar(self, guardar: bool, motivo: str = "") -> dict | None:
        if self._actual is None:
            return None
        self._espera, self.pausado = [], False
        ep = {**self._actual, "motivo": motivo, "episodio_dataset": None}
        n = ep["fotogramas"]
        if guardar and n < self.min_fotogramas:
            guardar, ep["motivo"] = False, f"demasiado corto ({n} fotogramas)"
        if guardar and n > self.max_fotogramas:
            guardar, ep["motivo"] = False, f"demasiado largo ({n} fotogramas)"
        ep["guardado"] = bool(guardar)
        if guardar:
            ep["episodio_dataset"] = int(self.ds.num_episodes)
            self.ds.save_episode()
        elif n > 0:
            self.ds.clear_episode_buffer()
        self.episodios.append(ep)
        self._actual = None
        self.escribir_json()
        return ep

    def resumen(self) -> dict:
        motivos: dict[str, int] = {}
        for e in self.episodios:
            if not e["guardado"]:
                m = str(e.get("motivo") or "descartado").split(" (")[0]
                motivos[m] = motivos.get(m, 0) + 1
        return {"tarea": self.tarea, "resolucion": list(self.resolucion), "intentos": len(self.episodios),
                "guardados": self.guardados, "descartados": self.descartados, "motivos_descarte": motivos,
                "episodios": self.episodios}

    def escribir_json(self) -> dict:
        r = self.resumen()
        if self.carpeta is not None and self.carpeta.exists():
            (self.carpeta / ARCHIVO_EPISODIOS).write_text(json.dumps(r, indent=2, ensure_ascii=False, default=float),
                                                          encoding="utf-8")
        return r

    def cerrar(self) -> dict:
        if self._cerrado:
            return self.resumen()
        if self._actual is not None:
            self.terminar(False, motivo="cortado al salir")
        self.ds.finalize()
        self._cerrado = True
        return self.escribir_json()


# --- corte de los episodios ----------------------------------------------------------------------------------------
EMPEZAR, TERMINAR, REPETIR, SALIR, PAUSAR, REANUDAR = "empezar", "terminar", "repetir", "salir", "pausar", "reanudar"


class CorteManual:
    """Teclas: espacio empieza/termina, r repite (descarta el episodio en curso), q o Esc sale."""

    def evento(self, tecla: int | None, grabando: bool) -> str | None:
        if tecla is None or tecla < 0:
            return None
        tecla &= 0xFF
        if tecla == ord(" "):
            return TERMINAR if grabando else EMPEZAR
        if tecla == ord("r"):
            return REPETIR if grabando else None
        if tecla in (ord("q"), 27):
            return SALIR
        return None


def broca_clavada(escena) -> bool | None:
    """¿Broca clavada en la madera? La percepción final puede dar `broca.clavada`; si no, `broca.apoyada` (ya con
    histéresis). None: no hay escena (percepción sin calibrar)."""
    if escena is None:
        return None
    broca = escena.broca
    return bool(getattr(broca, "clavada", broca.apoyada))


class CorteAcercamiento:
    """Corte automático por la percepción: empieza al clavarse la broca y termina al levantarla. Si se levanta, pausa
    (los fotogramas quedan en espera); si vuelve a clavarse antes de `tolerancia` s, reanuda; si no, termina."""

    def __init__(self, tolerancia: float = 0.0):
        self.tolerancia = float(tolerancia)
        self._levantada_desde: float | None = None
        self._anterior: bool | None = None

    def evento(self, t: float, escena, grabando: bool) -> str | None:
        clavada = broca_clavada(escena)
        if clavada is None:
            return None
        anterior, self._anterior = self._anterior, clavada
        if not grabando:
            self._levantada_desde = None
            # solo al clavarse (flanco): si se arranca con la broca ya clavada, se espera a que se levante y se clave
            return EMPEZAR if clavada and anterior is False else None
        if clavada:
            if self._levantada_desde is not None:
                self._levantada_desde = None
                return REANUDAR
            return None
        if self._levantada_desde is None:
            self._levantada_desde = t
            return TERMINAR if self.tolerancia <= 0 else PAUSAR
        if t - self._levantada_desde >= self.tolerancia:
            self._levantada_desde = None
            return TERMINAR
        return None


def cortador_automatico(tolerancia: float, exigir_agarre: bool = True):
    """El `CorteAcercamiento` de `garbi.grabador` (el mismo detector de clavada que el ciclo final; misma interfaz:
    `evento(t, escena, grabando)`); si no está, el de este script. `exigir_agarre=False` (`--sin-agarre`): corta
    aunque la percepción no vea una mano en el taladro."""
    try:
        from garbi.grabador import CorteAcercamiento as Externo

        return Externo(tolerancia=tolerancia, exigir_agarre=exigir_agarre)
    except (ImportError, TypeError):
        return CorteAcercamiento(tolerancia)


class PartidaPrudente:
    """Postura de partida de los episodios: la prudente de la broca que se ve (`garbi.acercamiento.postura_prudente`).
    `control`: `garbi.lateral.ControlLateral` (modelo cinemático del montaje lateral)."""

    def __init__(self, control, tolerancia: float = TOLERANCIA_PARTIDA):
        self.control = control
        self.tolerancia = float(tolerancia)
        self._q = None

    def postura(self, escena) -> np.ndarray | None:
        from garbi.acercamiento import postura_prudente, punta_de

        if escena is None or not escena.taladro.visible:
            return None
        P = punta_de(escena)
        if P is None:
            return None
        self._q = postura_prudente(self.control, P, self._q)
        return self._q

    def diferencia(self, escena, q) -> float | None:
        """° (máx. de las 4 articulaciones) de `q` a la postura prudente de la broca de `escena`; None si no hay."""
        from garbi.acercamiento import diferencia_a_prudente

        if q is None:
            return None
        return diferencia_a_prudente(self.control, escena, q)


# --- bucle de teleoperación --------------------------------------------------------------------------------------
class Teleop:
    """Un paso a 30 Hz: leader → montaje forzado → follower; imágenes; percepción (opcional); corte; grabación.

    `leader`: con `get_action()` (`SO101Leader` de LeRobot). `cuerpo`: `garbi.real.CuerpoReal` (o un doble con q,
    enviar, aspirar, imagenes). `percepcion(imagenes, q, t) -> Escena` (opcional, para el corte automático)."""

    def __init__(self, leader, cuerpo, grabador: GrabadorAcercamiento, corte_auto=None, percepcion=None,
                 estado: str = "orden", partida: PartidaPrudente | None = None, mover=None):
        from garbi.real import q_desde_lerobot

        self._q_lerobot = q_desde_lerobot
        self.leader = leader
        self.cuerpo = cuerpo
        self.grabador = grabador
        self.manual = CorteManual()
        self.auto = corte_auto
        self.percepcion = percepcion
        self.modo_estado = estado
        self.orden_previa: np.ndarray | None = None
        self.escena = None
        self.aviso = ""
        self.aviso_corte = ""  # por qué el corte automático no empieza aunque la broca esté apoyada
        self.aviso_partida = ""
        self.ultimo_evento: str | None = None
        self.partida = partida
        self.mover = mover or comun.mover_despacio
        self.enganche: np.ndarray | None = None  # postura en la que se sujeta el follower hasta que el leader llegue
        self.dif_enganche = 0.0

    def orden_leader(self) -> np.ndarray:
        return forzar_montaje(self._q_lerobot(self.leader.get_action()))

    def ir_a_prudente(self) -> bool:
        """Tecla p: el follower va despacio a la postura prudente de la broca que se ve y se queda ahí (enganche)
        hasta que el leader se ponga igual."""
        q = None if self.partida is None else self.partida.postura(self.escena)
        if q is None:
            self.aviso_partida = "p: no veo la broca (o no hay postura prudente para ella)"
            print(self.aviso_partida)
            return False
        if self.grabador.grabando:
            self.grabador.terminar(False, motivo="p durante el episodio")
            self.cuerpo.aspirar(False)
        self.mover(self.cuerpo, q)
        self.enganche = np.asarray(q, float).copy()
        self.orden_previa = None
        self.aviso_partida = "ENGANCHE: pon el leader igual que el follower"
        print("en la postura prudente: pon el leader igual que el follower (< %.0f°)" % TOLERANCIA_ENGANCHE)
        return True

    def _puede_empezar(self, q) -> bool:
        """Con `partida`: solo si no hay enganche y el follower está cerca de la postura prudente de la broca."""
        if self.partida is None:
            return True
        if self.enganche is not None:
            self.aviso_partida = "no grabo: el leader aún no está enganchado (ponlo igual que el follower)"
        else:
            dif = self.partida.diferencia(self.escena, q)
            if dif is not None and dif <= self.partida.tolerancia:
                self.aviso_partida = ""
                return True
            self.aviso_partida = ("no grabo: no veo la broca para comprobar la postura de partida" if dif is None else
                                  f"no grabo: el follower no parte de la postura prudente ({dif:.0f}° > "
                                  f"{self.partida.tolerancia:.0f}°): pulsa p")
        print(self.aviso_partida)
        return False

    def _aplicar(self, evento: str | None, t: float) -> bool:
        g = self.grabador
        if evento is None:
            return True
        self.ultimo_evento = evento
        if evento == SALIR:
            return False
        if evento == EMPEZAR and not g.grabando:
            q = self.cuerpo.q() if self.partida is not None else None
            if not self._puede_empezar(q):
                return True
            info = {} if self.partida is None else {"partida": "prudente",
                                                    "dif_partida": self.partida.diferencia(self.escena, q)}
            g.empezar(t=round(t, 2), corte="auto" if self.auto is not None else "manual", **info)
            self.cuerpo.aspirar(True)
        elif evento == TERMINAR and g.grabando:
            g.terminar(True, motivo="")
            self.cuerpo.aspirar(False)
        elif evento == REPETIR and g.grabando:
            g.terminar(False, motivo="repetido (r)")
            self.cuerpo.aspirar(False)
        elif evento == PAUSAR:
            g.pausar()
        elif evento == REANUDAR:
            g.reanudar()
        return True

    def paso(self, t: float, tecla: int | None = None) -> bool:
        """Devuelve False para salir."""
        orden = self.orden_leader()
        if self.enganche is not None:
            # el follower se queda en la postura prudente hasta que el leader está igual: así no salta
            self.dif_enganche = float(np.max(np.abs(orden[:4] - self.enganche[:4])))
            if self.dif_enganche <= TOLERANCIA_ENGANCHE:
                self.enganche, self.aviso_partida = None, ""
                print("leader enganchado: el follower vuelve a seguirlo")
            else:
                orden = self.enganche.copy()
        self.cuerpo.enviar(orden)
        imagenes = self.cuerpo.imagenes()
        q_medido = None
        if self.percepcion is not None:
            q_medido = self.cuerpo.q()
            try:
                self.escena, self.aviso = self.percepcion(imagenes, q_medido, t), ""
            except Exception as e:  # sin tapete a la vista la percepción no arranca: el corte manual sigue
                self.escena, self.aviso = None, f"percepcion: {e}"
        if tecla is not None and tecla >= 0 and (tecla & 0xFF) == ord("p") and self.partida is not None:
            self.ir_a_prudente()
            tecla = None
        seguir = self._aplicar(self.manual.evento(tecla, self.grabador.grabando), t)
        if seguir and self.auto is not None:
            seguir = self._aplicar(self.auto.evento(t, self.escena, self.grabador.grabando), t)
            aviso = getattr(self.auto, "aviso", "")
            if getattr(self.auto, "aviso_nuevo", False) and aviso:
                print("corte automático:", aviso)
            self.aviso_corte = aviso
        if self.grabador.grabando:
            if self.modo_estado == "medido":
                estado = self.cuerpo.q() if q_medido is None else q_medido
            else:
                estado = orden if self.orden_previa is None else self.orden_previa
            if self.grabador.fotograma(imagenes, estado, orden) == "largo":
                self.grabador.terminar(False, motivo="demasiado largo")
                self.cuerpo.aspirar(False)
        self.orden_previa = orden
        self._imagenes = imagenes
        return seguir

    def vista(self) -> np.ndarray:
        g = self.grabador
        imgs = [comun.a_bgr(self._imagenes[c]).copy() for c in ("top", "wrist") if c in self._imagenes]
        lineas = [("GRABANDO" + (" (pausa: broca levantada)" if g.pausado else "") + f" · {g.fotogramas / HZ_CONTROL:.1f} s")
                  if g.grabando else "esperando", f"guardados {g.guardados} · descartados {g.descartados}",
                  "espacio empezar/terminar · r repetir · q salir" + (" · p prudente" if self.partida else "")]
        if self.enganche is not None:
            lineas.append(f"ENGANCHE: pon el leader igual que el follower · faltan {self.dif_enganche:.0f} grados")
        elif self.aviso_partida:
            lineas.append(self.aviso_partida[:90])
        if self.aviso_corte:
            lineas.append(self.aviso_corte[:90])
        if self.auto is not None:
            clavada = broca_clavada(self.escena)
            lineas.append("corte AUTO · broca " + {None: "?", True: "CLAVADA", False: "levantada"}[clavada])
        if self.aviso:
            lineas.append(self.aviso[:90])
        vista = comun.mosaico(imgs)
        return comun.rotulo(vista, lineas, color=(80, 80, 255) if g.grabando else (255, 255, 255))


def crear_percepcion_auto(ns, mundo=None):
    """Percepción para el corte automático y la postura de partida: la de `garbi.correr` con las intrínsecas, la
    base de `calib/` y los umbrales de `garbi/config_vision.yaml`."""
    from garbi.correr import LectorEscena, crear_percepcion_real
    from garbi.mundo import MundoGarbi

    mundo = mundo or MundoGarbi(render=False, montaje="lateral")
    return LectorEscena(crear_percepcion_real(mundo.modelo, ns.calibracion))


def main(argv=None) -> None:
    import cv2
    from lerobot.teleoperators.so_leader import SO101Leader, SO101LeaderConfig

    from garbi.real import CuerpoReal, cargar_calibracion

    ns = argumentos(argv)
    if not ns.sin_ventana:
        comun.comprobar_ventanas()
    calib = cargar_calibracion(ns.calibracion)
    partida, percepcion = None, None
    if ns.corte == "auto" or ns.partida == "prudente":
        from garbi.lateral import ControlLateral
        from garbi.mundo import MundoGarbi

        mundo = MundoGarbi(render=False, montaje="lateral")
        percepcion = crear_percepcion_auto(ns, mundo)
        if ns.partida == "prudente":
            partida = PartidaPrudente(ControlLateral(mundo), ns.tolerancia_partida)
    ds = crear_dataset(Path(ns.salida), ns.repo_id, ns.resolucion, ns.reanudar, ns.sobrescribir)
    grabador = GrabadorAcercamiento(ds, Path(ns.salida), ns.resolucion, ns.min_segundos, ns.max_segundos)
    leader = SO101Leader(SO101LeaderConfig(port=ns.leader, id=ns.leader_id))
    cuerpo = CuerpoReal(ns.puerto, ns.id, comun.camaras_desde(ns), ns.aspiradora, max_relative_target=ns.max_salto,
                        ajustes=comun.ajustes_desde(ns), intrinsecas=calib.intrinsecas)
    leader.connect()
    cuerpo.conectar()
    teleop = Teleop(leader, cuerpo, grabador,
                    cortador_automatico(ns.tolerancia, not ns.sin_agarre) if ns.corte == "auto" else None,
                    percepcion, ns.estado, partida)
    ventana = "Garbi · teleop"
    try:
        if comun.confirmar("El follower irá despacio a la postura del leader. ¿Seguir?"):
            comun.mover_despacio(cuerpo, teleop.orden_leader())
        else:
            return
        if not ns.sin_ventana:
            cv2.namedWindow(ventana, cv2.WINDOW_NORMAL)
        print(__doc__.split("Corte de los episodios:")[1].split("Contador")[0])
        t0, periodo, tecla = time.perf_counter(), 1.0 / HZ_CONTROL, None
        while True:
            t_paso = time.perf_counter()
            n_antes, grabando_antes = len(grabador.episodios), grabador.grabando
            if not teleop.paso(t_paso - t0, tecla):
                break
            tecla = None
            if not ns.sin_ventana:
                cv2.imshow(ventana, teleop.vista())
                tecla = cv2.waitKey(1)
            if grabador.grabando and not grabando_antes:
                print(f"episodio {grabador.guardados + 1}: GRABANDO")
            if len(grabador.episodios) > n_antes:
                ultimo = grabador.episodios[-1]
                print(("GUARDADO" if ultimo["guardado"] else f"descartado ({ultimo['motivo']})") +
                      f" · guardados {grabador.guardados} · descartados {grabador.descartados}")
            time.sleep(max(0.0, periodo - (time.perf_counter() - t_paso)))
    except KeyboardInterrupt:
        print("\nCtrl+C: brazo quieto, aspiradora apagada; el episodio en curso se descarta")
    finally:
        cuerpo.aspirar(False)
        comun.parar_quieto(cuerpo)
        resumen = grabador.cerrar()
        cuerpo.cerrar()
        try:
            leader.disconnect()
        except Exception:
            pass
        if not ns.sin_ventana:
            cv2.destroyAllWindows()
        print(f"{resumen['guardados']} guardados, {resumen['descartados']} descartados → {ns.salida}")
    if ns.push and grabador.guardados:
        print("subiendo al Hub:", ns.repo_id)
        ds.push_to_hub(private=True)


if __name__ == "__main__":
    main()
