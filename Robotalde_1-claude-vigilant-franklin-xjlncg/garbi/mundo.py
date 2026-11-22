"""Mundo simulado de Garbi: robot, tabla, taladro, agujeros, viruta y aspiradora.

La interfaz del robot imita al SO-101 seguidor de LeRobot 0.7 (estado y acción en grados, pinza 0-100), igual que
`sim.entorno`. Lo que no es el robot (la tabla, el taladro, la viruta) lo maneja el «juez» simulado con métodos de
esta clase: colocar o mover la tabla, acercar y retirar el taladro, taladrar, tirar serrín en la alfombrilla.

Aspiración: regla, no física. En cada fotograma, si la aspiradora está encendida, toda partícula de viruta que
quede dentro del cono de captación de la boca (a lo largo de su eje, ver `contrato`) desaparece (la recoge la
aspiradora). Así se mide lo que importa: cuánta viruta queda.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import mujoco
import numpy as np

from garbi import contrato as g
from garbi import escena
from sim.cinematica import ARTICULACIONES, Cinematica
from sim.entorno import lerobot_a_rad, rad_a_lerobot

MM = escena.MM
SUBPASOS = 16
NOMBRES_MOTORES = [f"{n}.pos" for n in ARTICULACIONES]

# Postura de aparcado (grados de LeRobot): brazo recogido junto a la base, boca arriba y fuera de la zona.
APARCADO = np.array([0.0, -100.0, 60.0, -60.0, 0.0, 30.0])  # recogido y alto: la boquilla apunta arriba, lejos de la zona

# Dónde está cada partícula de viruta
FUERA, EN_TABLA, EN_ALFOMBRILLA = 0, 1, 2


@dataclass
class EstadoJuez:
    """Lo que no es el robot: tabla, taladro, agujeros y viruta."""
    tabla: g.PoseTabla | None = None
    taladro_visible: bool = False
    taladro_punta: np.ndarray = field(default_factory=lambda: np.zeros(3))  # mm, marco de la mesa
    taladro_eje: np.ndarray = field(default_factory=lambda: np.array([0.0, 0.0, 1.0]))  # de la punta hacia arriba
    agujeros: list = field(default_factory=list)  # posiciones (marco de la tabla, mm)
    viruta_donde: np.ndarray = field(default_factory=lambda: np.full(g.MAX_VIRUTA, FUERA))
    viruta_pos: np.ndarray = field(default_factory=lambda: np.zeros((g.MAX_VIRUTA, 2)))  # tabla o mesa, según dónde
    # Manos de la persona (solución final): la que sujeta el taladro (se puede soltar: taladro dejado sin mano) y la
    # libre (centro de la palma en la mesa, mm; None si no está en escena)
    mano_en_taladro: bool = True
    mano_libre: np.ndarray | None = None


def en_cono_captacion(pts_mm: np.ndarray, boca_mm: np.ndarray, eje: np.ndarray) -> np.ndarray:
    """Qué puntos (Nx3, mm) caen en el cono de captación de una boca en `boca_mm` que mira hacia `eje`."""
    v = np.asarray(pts_mm, float).reshape(-1, 3) - np.asarray(boca_mm, float)
    a = v @ eje
    lateral = np.linalg.norm(v - a[:, None] * eje[None, :], axis=1)
    return (a >= 0.0) & (a <= g.ALCANCE_CAPTACION) & (lateral <= g.RADIO_CAPTACION + g.PENDIENTE_CAPTACION * a)


class MundoGarbi:
    def __init__(self, render: bool = True, sombras: bool = True, resolucion_politica=g.RESOLUCION_POLITICA,
                 montaje: str | None = None):
        self.montaje = montaje or escena.MONTAJE
        self.modelo = escena.construir_modelo(montaje=self.montaje)
        self.datos = mujoco.MjData(self.modelo)
        self.cin = Cinematica(self.modelo, sitio_pose="boca")
        self.qadr = self.cin.qadr
        self.render = render
        self.sombras = sombras
        self.resolucion_politica = tuple(resolucion_politica)
        self._renderers: dict[tuple[int, int], mujoco.Renderer] = {}
        self.dt = 1.0 / g.FPS
        self.modelo.opt.timestep = self.dt / SUBPASOS
        self.t = 0.0
        self.aspiradora = False
        self.juez = EstadoJuez()
        self.rng = np.random.default_rng(0)
        self.sitio_boca = self.modelo.site("boca").id
        self._mocap = {n: self.modelo.body_mocapid[self.modelo.body(n).id] for n in ("tabla", "taladro", "mano_libre")}
        self._geoms_mano_taladro = [self.modelo.geom(n).id for n in escena.GEOMS_MANO_TALADRO]
        self._alfa_mano_taladro = self.modelo.geom_rgba[self._geoms_mano_taladro, 3].copy()
        self._mocap_agujero = [self.modelo.body_mocapid[self.modelo.body(f"agujero_{k}").id]
                               for k in range(g.MAX_AGUJEROS)]
        self._mocap_viruta = np.array([self.modelo.body_mocapid[self.modelo.body(f"viruta_{k}").id]
                                       for k in range(g.MAX_VIRUTA)])
        self.recogidas = 0  # partículas recogidas desde el último reset

    # --- ciclo -------------------------------------------------------------------------------------------------
    def reset(self, semilla: int | None = None, tabla: g.PoseTabla | None = None, q_inicial=None) -> dict:
        self.rng = np.random.default_rng(semilla)
        mujoco.mj_resetData(self.modelo, self.datos)
        self.juez = EstadoJuez()
        self.aspiradora = False
        self.recogidas = 0
        self.t = 0.0
        if tabla is None:
            tabla = self.pose_tabla_aleatoria()
        self.colocar_tabla(tabla)
        self.quitar_taladro()
        self.coger_taladro()
        self.reset_robot(APARCADO if q_inicial is None else q_inicial)
        return self.observacion()

    def reset_robot(self, q_lerobot) -> None:
        """Pone el brazo quieto en la postura `q_lerobot` sin tocar el resto de la escena."""
        q = lerobot_a_rad(np.asarray(q_lerobot, float))
        self.datos.qpos[self.qadr] = q
        self.datos.qvel[:] = 0.0
        self.datos.ctrl[:6] = q
        mujoco.mj_forward(self.modelo, self.datos)

    def step(self, accion, observar: bool = True) -> dict:
        """Un fotograma. Con `observar=False` no renderiza las cámaras (solo devuelve el estado): ahorra tiempo cuando
        nadie va a mirar las imágenes."""
        if isinstance(accion, dict):
            accion = [accion[n] for n in NOMBRES_MOTORES]
        q = lerobot_a_rad(np.asarray(accion, dtype=float))
        rangos = self.modelo.actuator_ctrlrange[:6]
        self.datos.ctrl[:6] = np.clip(q, rangos[:, 0], rangos[:, 1])
        mujoco.mj_step(self.modelo, self.datos, nstep=SUBPASOS)
        self.t += self.dt
        if self.aspiradora:
            self._aspirar()
        return self.observacion() if observar else {"observation.state": self.estado()}

    # --- robot ---------------------------------------------------------------------------------------------------
    def estado(self) -> np.ndarray:
        return rad_a_lerobot(self.datos.qpos[self.qadr]).astype(np.float32)

    def boca_en_mesa(self) -> np.ndarray:
        """Centro de la boca (mm, marco de la mesa)."""
        return self.datos.site_xpos[self.sitio_boca] / MM

    def eje_boca(self) -> np.ndarray:
        return self.datos.site_xmat[self.sitio_boca].reshape(3, 3)[:, 2].copy()

    def pose_camara(self, nombre: str) -> tuple[np.ndarray, np.ndarray]:
        """(R, t) de la cámara con el convenio de OpenCV: p_cam = R · p_mesa + t (mm). En el robot real, la de la
        cámara del robot sale de la cinemática directa y de la pieza del soporte (calibración mano-ojo)."""
        cid = self.modelo.camera(nombre).id
        Rc = self.datos.cam_xmat[cid].reshape(3, 3) @ np.diag([1.0, -1.0, -1.0])  # MuJoCo mira por -z con +y arriba
        R = Rc.T
        return R, -R @ (self.datos.cam_xpos[cid] / MM)

    def fovy(self, nombre: str) -> float:
        return float(self.modelo.cam_fovy[self.modelo.camera(nombre).id])

    # --- imágenes ------------------------------------------------------------------------------------------------
    def imagen(self, camara: str, resolucion=None) -> np.ndarray:
        ancho, alto = resolucion or self.resolucion_politica
        r = self._renderers.get((ancho, alto))
        if r is None:
            r = mujoco.Renderer(self.modelo, alto, ancho)
            self._renderers[(ancho, alto)] = r
        r.update_scene(self.datos, camara)
        r.scene.flags[mujoco.mjtRndFlag.mjRND_SHADOW] = self.sombras
        return r.render().copy()

    def observacion(self) -> dict:
        obs = {"observation.state": self.estado()}
        if self.render:
            for cam in g.CAMARAS_POLITICA:
                obs[f"observation.images.{cam}"] = self.imagen(cam)
        return obs

    # --- el «juez» -----------------------------------------------------------------------------------------------
    def pose_tabla_aleatoria(self) -> g.PoseTabla:
        zona_x = g.ZONA_TABLA_X if self.montaje == "lateral" else g.ZONA_TABLA_X_MORDAZAS
        return g.PoseTabla(float(self.rng.uniform(*zona_x)), float(self.rng.uniform(*g.ZONA_TABLA_Y)),
                           float(self.rng.uniform(*g.ZONA_TABLA_GIRO)))

    def colocar_tabla(self, pose: g.PoseTabla) -> None:
        """Pone la tabla en `pose`; lo que hay sobre ella (agujeros, viruta) se mueve con ella."""
        self.juez.tabla = pose
        i = self._mocap["tabla"]
        self.datos.mocap_pos[i] = [pose.x * MM, pose.y * MM, g.ALTURA_CARA_TABLA * MM]
        a = np.radians(pose.giro) / 2
        self.datos.mocap_quat[i] = [np.cos(a), 0, 0, np.sin(a)]
        self._actualizar_objetos()

    def mover_tabla(self, dx: float = 0.0, dy: float = 0.0, dgiro: float = 0.0) -> g.PoseTabla:
        t = self.juez.tabla
        nueva = g.PoseTabla(t.x + dx, t.y + dy, t.giro + dgiro)
        self.colocar_tabla(nueva)
        return nueva

    def poner_taladro(self, x: float, y: float, z: float | None = None, inclinacion: float = 0.0,
                      rumbo: float = 0.0) -> None:
        """Taladro con la punta de la broca en (x, y, z) mm (por defecto apoyada en la cara de la tabla), inclinado
        `inclinacion` grados respecto a la vertical, con la parte de arriba hacia el rumbo `rumbo` (grados en planta).
        Con el taladro inclinado, la bola se aparta de la vertical de la punta (230 mm · sen(inclinación))."""
        z = g.ALTURA_CARA_TABLA if z is None else z
        self.juez.taladro_visible = True
        self.juez.taladro_punta = np.array([x, y, z], dtype=float)
        i = self._mocap["taladro"]
        self.datos.mocap_pos[i] = [x * MM, y * MM, z * MM]
        # giro de `inclinacion` alrededor del eje horizontal perpendicular al rumbo
        eje = np.array([-np.sin(np.radians(rumbo)), np.cos(np.radians(rumbo)), 0.0])
        a = np.radians(inclinacion) / 2
        self.datos.mocap_quat[i] = [np.cos(a), *(np.sin(a) * eje)]
        i_r, r_r = np.radians(inclinacion), np.radians(rumbo)
        self.juez.taladro_eje = np.array([np.sin(i_r) * np.cos(r_r), np.sin(i_r) * np.sin(r_r), np.cos(i_r)])
        mujoco.mj_forward(self.modelo, self.datos)

    def soltar_taladro(self) -> None:
        """La persona suelta el taladro: se esconde la mano que lo sujeta (el taladro se queda donde está). Para probar
        que un taladro sin mano no cuenta como agarrado. El cuerpo del taladro no cambia (la holgura no cambia)."""
        self.juez.mano_en_taladro = False
        self.modelo.geom_rgba[self._geoms_mano_taladro, 3] = 0.0

    def coger_taladro(self) -> None:
        """Vuelve a poner la mano en el taladro (lo normal)."""
        self.juez.mano_en_taladro = True
        self.modelo.geom_rgba[self._geoms_mano_taladro, 3] = self._alfa_mano_taladro

    def mano_taladro_en_mesa(self) -> np.ndarray | None:
        """Centro de la palma de la mano que sujeta el taladro (mm, mesa), o None si no hay mano en el taladro."""
        if not (self.juez.taladro_visible and self.juez.mano_en_taladro):
            return None
        cuerpo = self.modelo.body("taladro").id
        R = self.datos.xmat[cuerpo].reshape(3, 3)
        return self.datos.xpos[cuerpo] / MM + R @ np.asarray(escena.MANO_TALADRO_EN_TALADRO, float)

    def poner_mano_libre(self, x: float, y: float, z: float = g.ALFOMBRILLA_GROSOR, rumbo: float = 0.0) -> None:
        """La otra mano de la persona con la palma en (x, y) mm, apoyada a altura z (por defecto, sobre el tapete); el
        antebrazo sale hacia el rumbo `rumbo` + 0° = +x (hacia la persona)."""
        self.juez.mano_libre = np.array([x, y, z], float)
        i = self._mocap["mano_libre"]
        self.datos.mocap_pos[i] = [x * MM, y * MM, z * MM]
        a = np.radians(rumbo) / 2
        self.datos.mocap_quat[i] = [np.cos(a), 0, 0, np.sin(a)]
        mujoco.mj_forward(self.modelo, self.datos)

    def quitar_mano_libre(self) -> None:
        self.juez.mano_libre = None
        self.datos.mocap_pos[self._mocap["mano_libre"]] = escena.ESCONDITE
        mujoco.mj_forward(self.modelo, self.datos)

    def quitar_taladro(self) -> None:
        self.juez.taladro_visible = False
        self.datos.mocap_pos[self._mocap["taladro"]] = escena.ESCONDITE
        mujoco.mj_forward(self.modelo, self.datos)

    def taladrar(self) -> np.ndarray | None:
        """Hace un agujero donde apoya la broca y deja un anillo de viruta alrededor. Devuelve el punto (tabla)."""
        tabla = self.juez.tabla
        if not self.juez.taladro_visible or tabla is None:
            return None
        p_mesa = self.juez.taladro_punta[:2]
        if not tabla.contiene(p_mesa, margen=g.RADIO_AGUJERO):
            return None
        p_tabla = tabla.a_tabla(p_mesa)
        if len(self.juez.agujeros) < g.MAX_AGUJEROS:
            self.juez.agujeros.append(p_tabla.copy())
        libres = np.flatnonzero(self.juez.viruta_donde == FUERA)[: g.VIRUTA_POR_AGUJERO]
        n = len(libres)
        ang = self.rng.uniform(0, 2 * np.pi, n)
        rad = self.rng.uniform(g.RADIO_VIRUTA_MIN, g.RADIO_VIRUTA_MAX, n) ** 1.0
        pts = p_tabla + np.stack([np.cos(ang) * rad, np.sin(ang) * rad], axis=1)
        largo, ancho = g.TABLA_TAMANO[0] / 2 - 1, g.TABLA_TAMANO[1] / 2 - 1
        pts[:, 0] = np.clip(pts[:, 0], -largo, largo)
        pts[:, 1] = np.clip(pts[:, 1], -ancho, ancho)
        self.juez.viruta_donde[libres] = EN_TABLA
        self.juez.viruta_pos[libres] = pts
        self._actualizar_objetos()
        return p_tabla

    def tirar_serrin(self, x: float, y: float, n: int = 30, radio: float = 18.0) -> int:
        """El juez tira un puñado de serrín en la alfombrilla alrededor de (x, y) mm (marco de la mesa)."""
        libres = np.flatnonzero(self.juez.viruta_donde == FUERA)[:n]
        ang = self.rng.uniform(0, 2 * np.pi, len(libres))
        rad = np.sqrt(self.rng.uniform(0, 1, len(libres))) * radio
        pts = np.array([x, y]) + np.stack([np.cos(ang) * rad, np.sin(ang) * rad], axis=1)
        tabla = self.juez.tabla
        for k, p in zip(libres, pts):
            if tabla is not None and tabla.contiene(p):
                self.juez.viruta_donde[k] = EN_TABLA
                self.juez.viruta_pos[k] = tabla.a_tabla(p)
            else:
                self.juez.viruta_donde[k] = EN_ALFOMBRILLA
                self.juez.viruta_pos[k] = p
        self._actualizar_objetos()
        return len(libres)

    # --- viruta -------------------------------------------------------------------------------------------------
    def viruta_en_mesa(self, donde: int | None = None) -> np.ndarray:
        """Posiciones (mm, marco de la mesa, Nx3) de la viruta visible (toda, o solo la de `donde`)."""
        sel = self.juez.viruta_donde != FUERA if donde is None else self.juez.viruta_donde == donde
        idx = np.flatnonzero(sel)
        out = np.zeros((len(idx), 3))
        for j, k in enumerate(idx):
            if self.juez.viruta_donde[k] == EN_TABLA:
                out[j, :2] = self.juez.tabla.a_mesa(self.juez.viruta_pos[k])
                out[j, 2] = g.ALTURA_CARA_TABLA
            else:
                out[j, :2] = self.juez.viruta_pos[k]
                out[j, 2] = g.ALFOMBRILLA_GROSOR
        return out

    def viruta_alrededor(self, p_tabla, radio: float = g.RADIO_VIRUTA_MAX + 6) -> int:
        """Partículas que quedan sobre la tabla a menos de `radio` del punto (marco de la tabla)."""
        sel = self.juez.viruta_donde == EN_TABLA
        d = np.linalg.norm(self.juez.viruta_pos[sel] - np.asarray(p_tabla)[None, :], axis=1)
        return int(np.sum(d <= radio))

    def _aspirar(self) -> None:
        idx = np.flatnonzero(self.juez.viruta_donde != FUERA)
        if len(idx) == 0:
            return
        recoge = en_cono_captacion(self.viruta_en_mesa(), self.boca_en_mesa(), self.eje_boca())
        if np.any(recoge):
            self.juez.viruta_donde[idx[recoge]] = FUERA
            self.recogidas += int(np.sum(recoge))
            self._actualizar_objetos()

    def _actualizar_objetos(self) -> None:
        tabla = self.juez.tabla
        for k, i in enumerate(self._mocap_agujero):
            if tabla is not None and k < len(self.juez.agujeros):
                p = tabla.a_mesa(self.juez.agujeros[k])
                self.datos.mocap_pos[i] = [p[0] * MM, p[1] * MM, (g.ALTURA_CARA_TABLA + 0.1) * MM]
            else:
                self.datos.mocap_pos[i] = escena.ESCONDITE
        visibles = self.juez.viruta_donde != FUERA
        pos = np.tile(np.asarray(escena.ESCONDITE), (g.MAX_VIRUTA, 1))
        if np.any(visibles):
            pos[visibles] = self.viruta_en_mesa() * MM
            pos[visibles, 2] += g.LADO_VIRUTA * 0.3 * MM
        self.datos.mocap_pos[self._mocap_viruta] = pos
        mujoco.mj_forward(self.modelo, self.datos)

    def cerrar(self) -> None:
        for r in self._renderers.values():
            r.close()
        self._renderers.clear()
