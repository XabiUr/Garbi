"""Orquestador del producto Garbi: la máquina de estados de `.plans/aspira/producto.md`.

    orq = Orquestador(cfg, politica, matriz)
    while True:
        orden = orq.paso(vista, {"top": img_top, "wrist": img_wrist, "state": q_medida})   # a 30 Hz
        robot.enviar(orden.q) if orden.q is not None else robot.quieto();  aspiradora.poner(orden.aspirar)
    orq.comando(Comando.EMERGENCIA)     # desde la app (botones, chat, seta)
    orq.estado_app()                    # → EstadoApp para la app

Estados y transiciones
----------------------
- REPOSO: postura de reposo (movimiento fijo). Mano + taladro con el círculo quieto ≥ `quieto_desde_reposo` (1 s)
  → ACERCAMIENTO.
- ACERCAMIENTO: si la política es ACT, `act_desde="reposo"` y el brazo no está en reposo, primero va a reposo con un
  movimiento fijo (la misma situación que en el entrenamiento); luego manda la política. Al llegar → EN_BROCA. Si
  mano + taladro se va (círculo desplazado > `rango_salida_px` o sin mano + taladro durante > `perdido`) → DESPIERTO.
- EN_BROCA: quieto en la postura de llegada (congelada), aspiradora encendida. Cuando mano + taladro se va → DESPIERTO.
- DESPIERTO: postura despierto, aspiradora apagada. Taladro quieto ≥ `quieto_desde_despierto` (2 s) → ACERCAMIENTO.
  Sin taladro en escena durante `sin_taladro_limpiar`, con ≥ 1 agujero sin limpiar y con tabla → LIMPIEZA_TABLA.
- LIMPIEZA_TABLA: zigzag de toda la tabla a altura fija (matriz + offset), aspirando. Al acabar → DESPIERTO (o
  REPOSO si no hay manos). Si aparece mano + taladro, para → DESPIERTO.
- LIMPIEZA_TAPETE: si se retira la tabla (la hubo y no se ve durante `sin_tabla`) desde REPOSO, DESPIERTO o
  LIMPIEZA_TABLA, o si se pide: zigzag de todo el tapete; al acabar → REPOSO.
- APAGADO (q=None). EMERGENCIA: q=None, aspiradora apagada, se ignora todo salvo REARMAR (→ REPOSO).

«Taladro en escena» = el círculo morado visible y agarrado, o suelto encima de la tabla (si está suelto fuera de la
tabla, se puede limpiar). Un tiempo de «quieto» solo cuenta desde que se entró en el estado actual.

Todas las órdenes pasan por el límite de velocidad por articulación (`velocidad_max`). La muñeca (wrist_roll) y la
pinza van como las da la política/matriz salvo que la configuración las fije (`wrist_roll_fijo`, `pinza_fija`).
"""
from __future__ import annotations

import logging
from collections import deque

import numpy as np

from garbi.producto.barridos import barrido_tabla, barrido_tapete, limitar_velocidad_paso, trayectoria_suave
from garbi.producto.contrato import Comando, Estado, EstadoApp, Orden, Vista

log = logging.getLogger("garbi.producto")

MAX_EVENTOS = 30

DETALLES = {
    Estado.APAGADO: "Apagado",
    Estado.REPOSO: "En reposo: esperando mano + taladro quieto",
    Estado.ACERCAMIENTO: "Me acerco a la broca",
    Estado.EN_BROCA: "Junto a la broca, aspirando",
    Estado.DESPIERTO: "Despierto: esperando el siguiente agujero",
    Estado.LIMPIEZA_TABLA: "Limpiando la tabla",
    Estado.LIMPIEZA_TAPETE: "Limpiando el tapete",
    Estado.EMERGENCIA: "EMERGENCIA: quieto, aspiradora apagada (rearmar para seguir)",
}


def _dentro(p, poligono) -> bool:
    import cv2

    return cv2.pointPolygonTest(np.asarray(poligono, np.float32).reshape(-1, 1, 2),
                                (float(p[0]), float(p[1])), False) >= 0


class Orquestador:
    def __init__(self, config, politica, matriz=None, estado_inicial: Estado = Estado.REPOSO):
        self.cfg = config
        self.politica = politica
        self.matriz = matriz
        self.estado = Estado(estado_inicial)
        self.detalle = DETALLES[self.estado]
        self.aspiradora = False
        self.agujeros = 0              # acercamientos completados en la sesión
        self.agujeros_pendientes = 0   # agujeros desde la última limpieza de la tabla
        self.eventos: deque[str] = deque(maxlen=MAX_EVENTOS)
        self.tecnologias: dict[str, str] = {
            "visión": "aviso: sin datos todavía",
            "círculo": "aviso: sin datos todavía",
            "manos": "aviso: sin datos todavía",
            "tabla": "aviso: sin datos todavía",
            "política": f"ok: {getattr(politica, 'nombre', '?')}",
            "matriz": (f"ok: {matriz.tipo} ({len(matriz)} puntos)" if matriz is not None
                       else "aviso: sin matriz (no hay barridos ni política del círculo)"),
            "robot": "aviso: sin datos todavía",
            "aspiradora": "manual (pedal)" if getattr(config.puertos, "aspiradora", None) is None else "ok",
        }
        self.t = 0.0
        self._t_estado = 0.0
        self._nuevo = True             # el estado acaba de empezar: el manejador prepara su plan
        self._q_orden: np.ndarray | None = None
        self._plan: np.ndarray | None = None
        self._i = 0
        self._sub = ""                 # ACERCAMIENTO: "a_reposo" o "politica"
        self._ancla: np.ndarray | None = None
        self._q_congelada: np.ndarray | None = None
        self._t_taladro_agarrado = -np.inf   # última vez con mano + taladro (círculo visible)
        self._t_taladro_escena = -np.inf     # última vez con taladro en escena (ver docstring)
        self._t_tabla = -np.inf
        self._hubo_tabla = False
        self._tabla: np.ndarray | None = None
        self._manos = 0
        self._evento(f"Garbi listo ({self.estado.value}, política {getattr(politica, 'nombre', '?')})")

    # --- utilidades ------------------------------------------------------------------------------------------------
    def _evento(self, texto: str) -> None:
        self.eventos.append(texto)
        log.info("garbi: %s", texto)

    def marcar_tecnologia(self, nombre: str, estado: str) -> None:
        """Para el programa principal: estado de una pieza («ok», «aviso: ...», «error: ...»)."""
        self.tecnologias[nombre] = estado

    def poner_politica(self, politica) -> bool:
        """Cambia la política (desde la app). No se cambia en mitad de un acercamiento."""
        if self.estado == Estado.ACERCAMIENTO:
            self._evento("No cambio de política en mitad de un acercamiento")
            return False
        self.politica = politica
        self.tecnologias["política"] = f"ok: {politica.nombre}"
        self._evento(f"Política: {politica.nombre}")
        return True

    def _entrar(self, estado: Estado, motivo: str = "") -> None:
        anterior = self.estado
        self.estado = estado
        self.detalle = DETALLES[estado]
        self._t_estado = self.t
        self._nuevo = True
        self._plan = None
        self._i = 0
        if estado in (Estado.APAGADO, Estado.EMERGENCIA):
            self._q_orden = None
            self.aspiradora = False
        if motivo:
            self._evento(motivo)
        log.debug("estado %s → %s", anterior.value, estado.value)

    def _q_actual(self, q_medida) -> np.ndarray:
        if self._q_orden is not None:
            return self._q_orden.copy()
        if q_medida is not None:
            return np.asarray(q_medida, float).copy()
        return self.cfg.q_reposo.copy()

    def _planear(self, destino, q_desde, velocidad=None) -> None:
        v = self.cfg.movimiento_fijo if velocidad is None else velocidad
        self._plan = trayectoria_suave(q_desde, destino, v, self.cfg.hz)
        self._i = 0

    def _seguir_plan(self) -> np.ndarray:
        q = self._plan[min(self._i, len(self._plan) - 1)]
        self._i += 1
        return q.copy()

    def _plan_acabado(self) -> bool:
        return self._plan is None or self._i >= len(self._plan)

    # --- percepción ------------------------------------------------------------------------------------------------
    def _actualizar_memoria(self, v: Vista) -> None:
        c = v.circulo
        if c is not None and v.taladro_agarrado:
            self._t_taladro_agarrado = v.t
            self._t_taladro_escena = v.t
        elif c is not None and v.tabla is not None and _dentro(c.uv, v.tabla):
            self._t_taladro_escena = v.t   # suelto encima de la tabla: no se puede barrer
        if v.tabla is not None:
            self._t_tabla = v.t
            self._tabla = np.asarray(v.tabla, float).reshape(4, 2)
            if not self._hubo_tabla:
                self._evento("Veo la tabla")
            self._hubo_tabla = True
        self._manos = len(v.manos)
        self.tecnologias["visión"] = "ok"
        self.tecnologias["círculo"] = "ok" if c is not None else "aviso: no veo el círculo morado"
        self.tecnologias["manos"] = f"ok: {len(v.manos)} mano(s)" + (" con taladro" if v.taladro_agarrado else "")
        self.tecnologias["tabla"] = "ok" if v.tabla is not None else "aviso: no veo la tabla"

    def _agarrado(self, v: Vista) -> bool:
        return v.circulo is not None and v.taladro_agarrado

    def _quieto(self, v: Vista, segundos: float) -> bool:
        """Mano + taladro con el círculo quieto al menos `segundos` (contando solo desde que empezó el estado)."""
        if not self._agarrado(v) or v.circulo.quieto_desde is None:
            return False
        return v.t - max(v.circulo.quieto_desde, self._t_estado) >= segundos - 1e-9

    def _se_ha_ido(self, v: Vista) -> str:
        """Motivo si mano + taladro se ha ido del punto de llegada; "" si sigue."""
        tm = self.cfg.tiempos
        if self._agarrado(v):
            if self._ancla is not None and np.linalg.norm(np.asarray(v.circulo.uv) - self._ancla) > tm.rango_salida_px:
                return "El taladro se ha alejado"
            return ""
        if v.t - self._t_taladro_agarrado > tm.perdido:
            return "Ya no veo mano + taladro"
        return ""

    def _tabla_retirada(self, v: Vista) -> bool:
        return self._hubo_tabla and v.tabla is None and v.t - self._t_tabla >= self.cfg.tiempos.sin_tabla

    # --- comandos de la app ----------------------------------------------------------------------------------------
    def comando(self, comando: Comando | str) -> bool:
        """Aplica un comando de la app. Devuelve si se ha aceptado. EMERGENCIA tiene prioridad absoluta."""
        c = Comando(comando)
        if c == Comando.EMERGENCIA:
            self._entrar(Estado.EMERGENCIA, "¡EMERGENCIA! Quieto y aspiradora apagada")
            return True
        if self.estado == Estado.EMERGENCIA:
            if c == Comando.REARMAR:
                self._entrar(Estado.REPOSO, "Rearmado: vuelvo a reposo")
                return True
            self._evento(f"En emergencia solo acepto «rearmar» (ignoro «{c.value}»)")
            return False
        if c == Comando.REARMAR:
            self._evento("No hay nada que rearmar")
            return False
        if c == Comando.APAGAR:
            self._entrar(Estado.APAGADO, "Me apago")
            return True
        if self.estado == Estado.APAGADO and c != Comando.ENCENDER:
            self._evento(f"Estoy apagado: ignoro «{c.value}» (dime «enciéndete»)")
            return False
        if c == Comando.ENCENDER:
            if self.estado != Estado.APAGADO:
                self._evento("Ya estoy encendido")
                return False
            self._entrar(Estado.REPOSO, "Me enciendo")
            return True
        if c == Comando.PARAR:
            self._entrar(Estado.REPOSO, "Paro y vuelvo a reposo")
            return True
        if c == Comando.LIMPIAR_TABLA:
            if self._tabla is None:
                self._evento("No veo ninguna tabla que limpiar")
                return False
            if self.matriz is None:
                self._evento("Sin matriz no puedo barrer la tabla")
                return False
            self._entrar(Estado.LIMPIEZA_TABLA, "Limpio la tabla (me lo has pedido)")
            return True
        if c == Comando.LIMPIAR_TAPETE:
            if self.matriz is None:
                self._evento("Sin matriz no puedo barrer el tapete")
                return False
            self._entrar(Estado.LIMPIEZA_TAPETE, "Limpio el tapete (me lo has pedido)")
            return True
        return False

    # --- el paso de control ----------------------------------------------------------------------------------------
    def paso(self, vista: Vista, obs: dict | None = None) -> Orden:
        obs = obs or {}
        self.t = float(vista.t)
        q_medida = obs.get("state")
        if q_medida is not None:
            self.tecnologias["robot"] = "ok"
        self._actualizar_memoria(vista)

        manejador = {
            Estado.APAGADO: self._apagado, Estado.EMERGENCIA: self._apagado,
            Estado.REPOSO: self._reposo, Estado.ACERCAMIENTO: self._acercamiento, Estado.EN_BROCA: self._en_broca,
            Estado.DESPIERTO: self._despierto, Estado.LIMPIEZA_TABLA: self._limpieza_tabla,
            Estado.LIMPIEZA_TAPETE: self._limpieza_tapete,
        }
        # Un cambio de estado dentro del manejador ejecuta el nuevo en el mismo paso (como mucho 3 veces).
        q, aspirar = None, False
        for _ in range(3):
            estado = self.estado
            q, aspirar = manejador[estado](vista, obs, q_medida)
            if self.estado == estado:
                break
        if q is not None:
            q = self._ordenar(q, q_medida)
        self.aspiradora = bool(aspirar) and self.estado not in (Estado.EMERGENCIA, Estado.APAGADO)
        return Orden(q=q, aspirar=self.aspiradora, estado=self.estado, detalle=self.detalle)

    def _ordenar(self, q, q_medida) -> np.ndarray:
        """Montaje (wrist_roll y pinza) y límite de velocidad por articulación."""
        q = np.asarray(q, float).copy()
        if self.cfg.wrist_roll_fijo is not None:
            q[4] = float(self.cfg.wrist_roll_fijo)
        if self.cfg.pinza_fija is not None:
            q[5] = float(self.cfg.pinza_fija)
        previa = self._q_orden if self._q_orden is not None else q_medida
        q = limitar_velocidad_paso(q, previa, self.cfg.vmax, self.cfg.hz)
        self._q_orden = q.copy()
        return q

    # --- manejadores (devuelven (q objetivo o None, aspirar)) -------------------------------------------------------
    def _apagado(self, v, obs, q_medida):
        return None, False

    def _reposo(self, v, obs, q_medida):
        if self._nuevo:
            self._nuevo = False
            self._planear(self.cfg.q_reposo, self._q_actual(q_medida))
        if self._tabla_retirada(v) and not self._agarrado(v):
            self._hubo_tabla = False
            self._entrar(Estado.LIMPIEZA_TAPETE, "Han retirado la tabla: limpio el tapete")
            return None, False
        t = self.cfg.tiempos.quieto_desde_reposo
        if self._quieto(v, t):
            self._entrar(Estado.ACERCAMIENTO, f"Taladro quieto {t:g} s: me acerco")
            return None, False
        return self._seguir_plan(), False

    def _acercamiento(self, v, obs, q_medida):
        if self._nuevo:
            self._nuevo = False
            self._ancla = None if v.circulo is None else np.asarray(v.circulo.uv, float).copy()
            self._q_congelada = None
            q = self._q_actual(q_medida)
            lejos = float(np.max(np.abs(q - self.cfg.q_reposo))) > self.cfg.tiempos.tolerancia_reposo
            if getattr(self.politica, "nombre", "") == "act" and self.cfg.act_desde == "reposo" and lejos:
                self._sub = "a_reposo"
                self._planear(self.cfg.q_reposo, q)
                self._evento("Vuelvo a reposo para lanzar ACT desde allí")
            else:
                self._sub = ""
        motivo = self._se_ha_ido(v)
        if motivo:
            self._entrar(Estado.DESPIERTO, f"{motivo}: dejo el acercamiento")
            return None, False
        if self._sub == "a_reposo":
            if not self._plan_acabado():
                return self._seguir_plan(), False
            self._sub = ""
        if self._sub == "":
            if v.circulo is None:   # parpadeo del círculo (aún dentro de `perdido`): espera quieto
                return self._q_actual(q_medida), False
            try:
                self.politica.reiniciar(v, self._q_actual(q_medida))
            except Exception as e:
                self.tecnologias["política"] = f"error: {e}"
                self._entrar(Estado.DESPIERTO, f"La política no arranca ({e})")
                return None, False
            self._sub = "politica"
        try:
            q = self.politica.accion(obs, v)
        except Exception as e:
            log.exception("la política ha fallado")
            self.tecnologias["política"] = f"error: {e}"
            self._entrar(Estado.DESPIERTO, f"La política ha fallado ({e})")
            return None, False
        if self.politica.llegado():
            self._q_congelada = np.asarray(q, float).copy()   # se queda aquí (la acción ya ha convergido)
            self._entrar(Estado.EN_BROCA, "He llegado a la broca: aspiro")
            self.agujeros += 1
            self.agujeros_pendientes += 1
            return q, True
        return q, False

    def _en_broca(self, v, obs, q_medida):
        if self._nuevo:
            self._nuevo = False
            if self._q_congelada is None:
                self._q_congelada = self._q_actual(q_medida)
            if v.circulo is not None:
                self._ancla = np.asarray(v.circulo.uv, float).copy()
        motivo = self._se_ha_ido(v)
        if motivo:
            self._entrar(Estado.DESPIERTO, f"{motivo}: apago la aspiradora y espero")
            return None, False
        return self._q_congelada.copy(), True

    def _despierto(self, v, obs, q_medida):
        tm = self.cfg.tiempos
        if self._nuevo:
            self._nuevo = False
            self._planear(self.cfg.q_despierto, self._q_actual(q_medida))
        if self._tabla_retirada(v) and not self._agarrado(v):
            self._hubo_tabla = False
            self._entrar(Estado.LIMPIEZA_TAPETE, "Han retirado la tabla: limpio el tapete")
            return None, False
        if self._quieto(v, tm.quieto_desde_despierto):
            self._entrar(Estado.ACERCAMIENTO, f"Taladro quieto {tm.quieto_desde_despierto:g} s: me acerco otra vez")
            return None, False
        sin_taladro = v.t - max(self._t_taladro_escena, self._t_estado) >= tm.sin_taladro_limpiar
        if sin_taladro and self.agujeros_pendientes >= 1 and v.tabla is not None and self.matriz is not None:
            self._entrar(Estado.LIMPIEZA_TABLA,
                         f"Sin taladro {tm.sin_taladro_limpiar:g} s y {self.agujeros_pendientes} agujero(s): "
                         "limpio la tabla")
            return None, False
        return self._seguir_plan(), False

    def _preparar_barrido(self, barrido, q_medida) -> None:
        b = self.cfg.barridos
        q = self._q_actual(q_medida)
        llegada = trayectoria_suave(q, barrido.posturas[0], b.velocidad, self.cfg.hz)
        self._plan = np.concatenate([llegada, barrido.posturas])
        self._i = 0

    def _limpieza_tabla(self, v, obs, q_medida):
        b = self.cfg.barridos
        if self._nuevo:
            self._nuevo = False
            tabla = v.tabla if v.tabla is not None else self._tabla
            try:
                barrido = barrido_tabla(tabla, self.matriz, b.offset_tabla, b.paso_px, b.margen_px, b.velocidad,
                                        b.aceleracion, self.cfg.hz)
            except Exception as e:
                self._entrar(Estado.DESPIERTO, f"No puedo planear el barrido de la tabla ({e})")
                return None, False
            self._preparar_barrido(barrido, q_medida)
        if self._agarrado(v):
            self._entrar(Estado.DESPIERTO, "Hay mano + taladro: paro la limpieza")
            return None, False
        if self._tabla_retirada(v):
            self._hubo_tabla = False
            self._entrar(Estado.LIMPIEZA_TAPETE, "Han retirado la tabla: limpio el tapete")
            return None, False
        if self._plan_acabado():
            self.agujeros_pendientes = 0
            if self._manos:
                self._entrar(Estado.DESPIERTO, "Tabla limpia")
            else:
                self._entrar(Estado.REPOSO, "Tabla limpia; no hay nadie: a reposo")
            return None, False
        return self._seguir_plan(), True

    def _limpieza_tapete(self, v, obs, q_medida):
        b = self.cfg.barridos
        if self._nuevo:
            self._nuevo = False
            self._hubo_tabla = False
            esquinas = v.tapete if v.tapete is not None else self.cfg.tapete_px
            try:
                barrido = barrido_tapete(esquinas, self.matriz, b.offset_tapete, b.paso_px, b.margen_px,
                                         b.velocidad, b.aceleracion, self.cfg.hz)
            except Exception as e:
                self._entrar(Estado.REPOSO, f"No puedo planear el barrido del tapete ({e})")
                return None, False
            self._preparar_barrido(barrido, q_medida)
        if self._agarrado(v):
            self._entrar(Estado.DESPIERTO, "Hay mano + taladro: paro la limpieza del tapete")
            return None, False
        if self._plan_acabado():
            self.agujeros_pendientes = 0
            self._entrar(Estado.REPOSO, "Tapete limpio: a reposo")
            return None, False
        return self._seguir_plan(), True

    # --- para la app -----------------------------------------------------------------------------------------------
    def estado_app(self) -> EstadoApp:
        return EstadoApp(estado=self.estado, detalle=self.detalle, aspiradora=self.aspiradora,
                         politica=getattr(self.politica, "nombre", "?"), tecnologias=dict(self.tecnologias),
                         agujeros=self.agujeros, eventos=list(self.eventos))
