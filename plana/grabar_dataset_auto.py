#!/usr/bin/env python3
"""
grabar_dataset_auto.py - Graba dataset automáticamente usando CerebroZonas.

Genera episodios de demostración programados en formato LeRobot:
1. Reposo inicial (1s)
2. Esperar morado estable
3. Aproximación: subir → vertical → bajar
4. Quieto en objetivo (1.5s)
5. Volver a reposo
6. Reposo final (1s)

Dataset compatible con ACT:
- observation.state: posiciones articulaciones
- observation.images: front + gripper (RGB)
- action: postura objetivo enviada cada ciclo
- fps: 30

Modo automático (por defecto): la pantalla indica en qué ZONA colocar el taladro;
colócalo a mano (no se graba) y con 'OK' pulsa N: empieza a grabar (1 s de reposo
y la trayectoria). Se guarda solo al terminar.
Plan de zonas equilibrado (bloques de 15 con todas las zonas).

Teclas tras cada episodio (antes de guardar):
- R: Descartar (no se guarda; se repite la misma zona)
- G / ENTER: Guardar ya
- P: Pausar antes del siguiente
- Q: Guardar y terminar
Esperando taladro: Q termina. Con --manual: N antes de cada episodio.

Uso:
    python grabar_dataset_auto.py --nombre taladro_demo --episodios 10 --sin-robot --no-push
    python grabar_dataset_auto.py --nombre taladro_demo --episodios 20 --real
    python grabar_dataset_auto.py --nombre taladro_fijo --episodios 200 --real --no-push
"""

import argparse
import json
import cv2
import numpy as np
import time
from typing import Optional
from pathlib import Path
import trayectoria


def cargar_config():
    """Carga config.json"""
    with open('config.json', 'r') as f:
        return json.load(f)


def cargar_zona():
    """Carga zona.json"""
    with open('zona.json', 'r') as f:
        zona = json.load(f)
    return np.array(zona["esquinas_px"], dtype=np.float32)


def cargar_posturas():
    """Carga posturas.json"""
    with open('posturas.json', 'r') as f:
        return json.load(f)


class GrabadorDatasetAuto:
    """Grabador automático de dataset con CerebroZonas"""

    MOTOR_NAMES = [
        "shoulder_pan", "shoulder_lift", "elbow_flex",
        "wrist_flex", "wrist_roll", "gripper"
    ]

    def __init__(self, robot, config, nombre_dataset, no_push, modo_seguir=False, continuar=False):
        self.robot = robot
        self.config = config
        self.nombre_dataset = nombre_dataset
        self.no_push = no_push
        self.modo_seguir = modo_seguir  # True: seguimiento continuo, False: posición fija
        self.continuar = continuar  # True: añadir episodios a un dataset ya existente

        # Componentes
        from percepcion import DetectorMorado
        from cerebros import CerebroZonas
        from seguridad import SistemaSeguridad

        self.detector = DetectorMorado(config)
        self.detector.configurar_zona(cargar_zona())

        self.cerebro = CerebroZonas(config)

        self.seguridad = SistemaSeguridad(config)
        self.seguridad.configurar_limites(cargar_posturas())

        # Parámetros
        self.fps = config["dataset"]["fps"]
        self.dt = 1.0 / self.fps

        cfg_ds = config["dataset"]
        self.duracion_reposo_inicial = cfg_ds["duracion_reposo_inicial_s"]
        self.duracion_reposo_final = cfg_ds["duracion_reposo_final_s"]
        self.duracion_quieto = cfg_ds["duracion_quieto_en_objetivo_s"]
        # Guiado por zonas y confirmación
        self.tolerancia_objetivo = cfg_ds.get("tolerancia_objetivo", 0.10)   # dist (u,v) máx al objetivo
        self.dispersion_objetivo = cfg_ds.get("dispersion_objetivo", 0.08)   # desplazamiento aleatorio
        self.ventana_confirmacion_s = cfg_ds.get("ventana_confirmacion_s", 3.0)
        self.H_inv = None
        self.num_objetivo = 0

        # Umbral de movimiento del taladro
        self.umbral_movimiento_taladro = config["supervisor"].get("umbral_movimiento_taladro", 0.05)

        # Postura de reposo
        posturas_data = cargar_posturas()
        self.postura_reposo = posturas_data["reposo"]

        # Dataset
        self.dataset = None
        self.episodio_actual = []
        self.num_episodios_grabados = 0
        self.contador_por_zona = {str(i): 0 for i in range(3, 18)}  # Zonas 3-17 (grid 5x3)

        # Estado
        self.pausado = False
        self.taladro_movido = False  # Detecta si el taladro se movió durante el episodio

        print("[GrabadorDatasetAuto] Inicializado")
        print(f"  Dataset: {nombre_dataset}")
        print(f"  Modo seguimiento: {'CONTINUO' if self.modo_seguir else 'POSICIÓN FIJA'}")
        print(f"  FPS: {self.fps}")

    TAREA = "Acercar la boca de aspiracion a la broca del taladro"

    def crear_dataset(self):
        """Crea el dataset LeRobot (formato estándar 0.7: observation.state / action / images)"""
        from lerobot.datasets import LeRobotDataset
        from lerobot.utils.feature_utils import hw_to_dataset_features

        # Features del hardware a partir de una observación real
        obs_ejemplo = self.robot.get_observation()
        self.motores = [k for k in obs_ejemplo if k.endswith(".pos")]
        hw_obs = {k: float for k in self.motores}
        for cam in ["front", "gripper"]:
            if cam in obs_ejemplo:
                hw_obs[cam] = tuple(obs_ejemplo[cam].shape)
        hw_act = {k: float for k in self.motores}

        features = {
            **hw_to_dataset_features(hw_act, "action", use_video=True),
            **hw_to_dataset_features(hw_obs, "observation", use_video=True),
        }
        self.features = features

        # Repo ID: acepta "usuario/nombre" o solo "nombre"
        if "/" in self.nombre_dataset:
            repo_id = self.nombre_dataset
        else:
            repo_id = f"{self.config['huggingface']['user']}/{self.nombre_dataset}"

        print(f"[GrabadorDatasetAuto] Creando dataset: {repo_id}")
        print(f"  Features: {list(features.keys())}")

        if self.continuar:
            # Reanudar un dataset existente: los episodios nuevos se añaden al final
            from lerobot.utils.constants import HF_LEROBOT_HOME
            root = HF_LEROBOT_HOME / repo_id
            if not root.exists():
                raise FileNotFoundError(f"No existe el dataset a continuar: {root}")
            self.dataset = LeRobotDataset.resume(repo_id, root=root)
            previos = self.dataset.meta.total_episodes
            if set(self.dataset.features) - {"timestamp", "frame_index", "episode_index", "index", "task_index"} != set(features):
                raise ValueError("Las features del dataset existente no coinciden con las del robot actual")
            self.num_episodios_grabados = previos
            print(f"[GrabadorDatasetAuto] Continuando dataset en {root}: {previos} episodios ya guardados")
        else:
            self.dataset = LeRobotDataset.create(
                repo_id=repo_id,
                fps=self.fps,
                robot_type="so_follower",
                features=features,
                use_videos=True,
            )
            print(f"[GrabadorDatasetAuto] Dataset creado ✓ en {self.dataset.root}")

    # ------------------------------------------------------------------
    # Plan de objetivos: dónde colocar el taladro en cada episodio
    # ------------------------------------------------------------------
    # Zona -> (columna, fila) de la cuadrícula de posturas 5×3
    ZONAS_GRID = {
        '3': (0, 0), '4': (1, 0), '5': (2, 0), '6': (3, 0), '7': (4, 0),
        '8': (0, 1), '9': (1, 1), '10': (2, 1), '11': (3, 1), '12': (4, 1),
        '13': (0, 2), '14': (1, 2), '15': (2, 2), '16': (3, 2), '17': (4, 2),
    }

    def generar_plan(self, n: int, semilla: Optional[int] = None):
        """
        Genera n objetivos (zona, u, v) repartidos por igual entre las 15 zonas.

        Se generan en bloques de 15 (cada bloque pasa por todas las zonas en orden
        aleatorio), así el reparto queda equilibrado aunque se pare a mitad.
        Cada objetivo se desplaza al azar alrededor del punto de la zona para que
        ACT aprenda posiciones intermedias, no solo los 15 puntos exactos.
        """
        rng = np.random.default_rng(semilla)
        disp = self.dispersion_objetivo
        plan = []
        while len(plan) < n:
            zonas = list(self.ZONAS_GRID.keys())
            rng.shuffle(zonas)
            for z in zonas:
                col, fila = self.ZONAS_GRID[z]
                u = float(np.clip(col / 4.0 + rng.uniform(-disp, disp), 0.03, 0.97))
                v = float(np.clip(fila / 2.0 + rng.uniform(-disp, disp), 0.03, 0.97))
                plan.append((z, u, v))
        return plan[:n]

    def uv_a_px(self, u: float, v: float):
        """Convierte (u,v) normalizado a píxeles de la cámara frontal."""
        if self.H_inv is None:
            self.H_inv = np.linalg.inv(self.detector.matriz_homografia)
        pt = np.array([[[u, v]]], dtype=np.float32)
        px = cv2.perspectiveTransform(pt, self.H_inv)[0][0]
        return int(px[0]), int(px[1])

    def dibujar_objetivo(self, img, objetivo, percepcion=None, cabecera=None):
        """Dibuja el objetivo (dónde colocar el taladro) y la distancia actual."""
        z, u_obj, v_obj = objetivo
        h, w = img.shape[:2]
        cx, cy = self.uv_a_px(u_obj, v_obj)
        # Radio en px equivalente a la tolerancia (aprox.)
        rx, _ = self.uv_a_px(min(u_obj + self.tolerancia_objetivo, 1.2), v_obj)
        radio = max(8, abs(rx - cx))

        dist = None
        if percepcion is not None and percepcion.get("hay_taladro") and percepcion.get("u") is not None:
            dist = float(np.hypot(percepcion["u"] - u_obj, percepcion["v"] - v_obj))
        ok = dist is not None and dist <= self.tolerancia_objetivo
        color = (0, 255, 0) if ok else (0, 0, 255)

        cv2.circle(img, (cx, cy), radio, color, 2)
        cv2.line(img, (cx - 12, cy), (cx + 12, cy), color, 2)
        cv2.line(img, (cx, cy - 12), (cx, cy + 12), color, 2)
        cv2.putText(img, f"Z{z}", (cx + radio + 4, cy + 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        if dist is not None and percepcion.get("centro_px") is not None:
            cv2.line(img, percepcion["centro_px"], (cx, cy), color, 1)

        # Cabecera
        cv2.rectangle(img, (0, 0), (w, 34), (0, 0, 0), -1)
        texto = cabecera or f"Coloca el taladro en ZONA {z}"
        cv2.putText(img, texto, (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 255), 2)
        if dist is not None:
            estado = "Dentro del circulo - no lo toques" if ok else f"Acercalo al circulo (dist {dist:.2f})"
            cv2.putText(img, estado, (8, h - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        return img

    # ------------------------------------------------------------------
    # Episodio
    # ------------------------------------------------------------------
    def grabar_episodio(self, objetivo):
        """
        Graba un episodio completo para el objetivo dado (zona, u, v).

        Returns:
            True si se grabó, False si el usuario pidió salir (Q).
        """
        z_obj, u_obj, v_obj = objetivo
        print("\n" + "="*60)
        print(f"EPISODIO {self.num_episodios_grabados + 1} -> ZONA {z_obj} (u={u_obj:.2f}, v={v_obj:.2f})")
        print("="*60)

        self.episodio_actual = []
        frames_grabados = 0
        self.taladro_movido = False  # Resetear detector de movimiento
        posicion_inicial_taladro = None

        # FASE 1: Colocar el taladro a mano (NO se graba).
        # Se puede ajustar la posición con calma; cuando está estable dentro del
        # círculo aparece "OK" y la grabación empieza al pulsar N.
        print(f"Fase 1: Coloca el taladro en ZONA {z_obj} y pulsa N para empezar a grabar...")
        n_reposo = max(1, int(self.duracion_reposo_inicial * self.fps))

        while True:
            obs = self.robot.get_observation()
            percepcion = self.detector.detectar(obs["front"])
            self.robot.send_action(self.postura_reposo.copy())

            # ¿Taladro listo? (estable, dentro de zona y cerca del objetivo)
            listo = False
            u_est = v_est = None
            if percepcion["hay_taladro"] and percepcion["estable"] and percepcion["dentro_zona"]:
                u_est = percepcion.get("u_estable") if percepcion.get("u_estable") is not None else percepcion["u"]
                v_est = percepcion.get("v_estable") if percepcion.get("v_estable") is not None else percepcion["v"]
                listo = np.hypot(u_est - u_obj, v_est - v_obj) <= self.tolerancia_objetivo

            img_debug = self.detector.dibujar_debug(
                cv2.cvtColor(obs["front"], cv2.COLOR_RGB2BGR), percepcion)
            n_txt = f"[{self.num_episodios_grabados + 1}/{self.num_objetivo}]"
            if listo:
                cab = f"{n_txt} ZONA {z_obj} OK - pulsa N para grabar"
            else:
                cab = f"{n_txt} Coloca el taladro en ZONA {z_obj}"
            self.dibujar_objetivo(img_debug, objetivo, percepcion, cabecera=cab)
            cv2.imshow("Grabar Dataset", img_debug)

            tecla = cv2.waitKey(1) & 0xFF
            if tecla in (ord('q'), ord('Q')):
                print("Grabación detenida por usuario")
                return False

            time.sleep(self.dt)

            if tecla in (ord('n'), ord('N')):
                if listo:
                    posicion_inicial_taladro = (u_est, v_est)
                    print(f"✓ Taladro en ZONA {z_obj}: (u={u_est:.3f}, v={v_est:.3f}) - GRABANDO")
                    break
                print("  N ignorada: el taladro aún no está estable dentro del círculo")

        # FASE 2: Reposo inicial GRABADO (desde que se pulsa N)
        for _ in range(n_reposo):
            obs = self.robot.get_observation()
            accion = self.postura_reposo.copy()
            self.robot.send_action(accion)
            self.episodio_actual.append((obs, accion))
            frames_grabados += 1
            img = cv2.cvtColor(obs["front"], cv2.COLOR_RGB2BGR)
            cv2.putText(img, "GRABANDO", (10, img.shape[0] - 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            cv2.imshow("Grabar Dataset", img)
            cv2.waitKey(1)
            time.sleep(self.dt)

        # FASE 3: Actuación con trayectoria planificada (igual que supervisor)
        print("Fase 3: Reproduciendo trayectoria...")

        # Planificar trayectoria UNA VEZ usando el mismo planificador que el supervisor
        obs_actual = self.robot.get_observation()
        posturas_data = cargar_posturas()

        # Planificar trayectoria de ida
        traj = trayectoria.planificar(
            obs_actual, posicion_inicial_taladro, self.config,
            posturas_data, self.cerebro, tipo='ida'
        )

        # VARIAR velocidad ±15% entre episodios
        factor_velocidad = np.random.uniform(0.85, 1.15)
        duracion_traj = traj.duracion * factor_velocidad
        print(f"  Duración trayectoria: {duracion_traj:.2f}s (factor: {factor_velocidad:.2f}x)")

        # Reproducir trayectoria
        tiempo_traj = 0.0
        while tiempo_traj < duracion_traj:
            obs = self.robot.get_observation()
            percepcion = self.detector.detectar(obs["front"])

            # Detectar movimiento del taladro (modo sin seguir)
            if not self.modo_seguir and posicion_inicial_taladro is not None and percepcion["hay_taladro"]:
                dist = np.sqrt((percepcion["u"] - posicion_inicial_taladro[0])**2 +
                              (percepcion["v"] - posicion_inicial_taladro[1])**2)
                if dist > self.umbral_movimiento_taladro:
                    self.taladro_movido = True

            # Muestrear trayectoria (ajustando tiempo según factor de velocidad)
            t_ajustado = tiempo_traj / factor_velocidad  # Tiempo en la trayectoria original
            accion_traj = traj.muestrear(t_ajustado)

            # Seguridad
            accion_segura, _ = self.seguridad.verificar_accion(accion_traj, obs)

            # Enviar
            self.robot.send_action(accion_segura)

            self.episodio_actual.append((obs, accion_segura))
            frames_grabados += 1

            # Visualizar
            img_debug = self.detector.dibujar_debug(
                cv2.cvtColor(obs["front"], cv2.COLOR_RGB2BGR),
                percepcion
            )
            progreso = (tiempo_traj / duracion_traj) * 100
            cv2.putText(img_debug, f"TRAYECTORIA {progreso:.0f}%", (10, img_debug.shape[0] - 40),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            # Avisar si el taladro se movió
            if self.taladro_movido:
                cv2.putText(img_debug, "TALADRO MOVIDO - Pulsa R para descartar", (10, img_debug.shape[0] - 15),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            cv2.imshow("Grabar Dataset", img_debug)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("Episodio cancelado por usuario")
                return False

            tiempo_traj += self.dt
            time.sleep(self.dt)

        # FASE 4: Quieto en objetivo
        # VARIAR duración para que ACT aprenda por presencia visual, no por tiempo
        duracion_quieto_episodio = np.random.uniform(0.5, 1.0)  # 0.5-1 s (aleatorio): lo justo para aprender a pararse
        print(f"Fase 4: Quieto en objetivo ({duracion_quieto_episodio:.1f}s)...")
        if self.modo_seguir:
            print("  TIP: Puedes mover el taladro durante esta fase para enseñar reactividad")
        else:
            print("  IMPORTANTE: NO muevas el taladro (modo posición fija)")
        for _ in range(int(duracion_quieto_episodio * self.fps)):
            obs = self.robot.get_observation()
            percepcion = self.detector.detectar(obs["front"])

            # Detectar movimiento del taladro (modo sin seguir)
            if not self.modo_seguir and posicion_inicial_taladro is not None and percepcion["hay_taladro"]:
                dist = np.sqrt((percepcion["u"] - posicion_inicial_taladro[0])**2 +
                              (percepcion["v"] - posicion_inicial_taladro[1])**2)
                if dist > self.umbral_movimiento_taladro:
                    self.taladro_movido = True

            # Mantener última acción
            accion = accion_segura.copy()
            self.robot.send_action(accion)

            self.episodio_actual.append((obs, accion))
            frames_grabados += 1

            # Visualizar
            img_debug = self.detector.dibujar_debug(
                cv2.cvtColor(obs["front"], cv2.COLOR_RGB2BGR),
                percepcion
            )
            cv2.putText(img_debug, "QUIETO", (10, img_debug.shape[0] - 40),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
            # Avisar si el taladro se movió
            if self.taladro_movido:
                cv2.putText(img_debug, "TALADRO MOVIDO - Pulsa R para descartar", (10, img_debug.shape[0] - 15),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            cv2.imshow("Grabar Dataset", img_debug)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("Episodio cancelado por usuario")
                return False

            time.sleep(self.dt)

        # Fin de grabación: el episodio termina aquí
        print(f"✓ Episodio grabado: {frames_grabados} frames ({frames_grabados/self.fps:.1f}s)")
        print(f"  Brazo quieto en posición de aspirado ~{duracion_quieto_episodio:.1f}s")

        # FASE 5: Volver a reposo con trayectoria (NO SE GRABA)
        print("Fase 5: Volviendo a reposo con trayectoria (no se graba)...")
        obs_actual = self.robot.get_observation()
        traj_vuelta = trayectoria.planificar(
            obs_actual, posicion_inicial_taladro, self.config,
            posturas_data, self.cerebro, tipo='vuelta'
        )
        print(f"  Duración trayectoria vuelta: {traj_vuelta.duracion:.2f}s")

        tiempo_vuelta = 0.0
        while tiempo_vuelta < traj_vuelta.duracion:
            obs = self.robot.get_observation()
            accion_traj = traj_vuelta.muestrear(tiempo_vuelta)
            accion_segura, _ = self.seguridad.verificar_accion(accion_traj, obs)
            self.robot.send_action(accion_segura)
            # NO añadir a episodio_actual
            tiempo_vuelta += self.dt
            time.sleep(self.dt)

        # FASE 6: Reposo final (NO SE GRABA)
        print("Fase 6: Reposo final (no se graba)...")
        for _ in range(int(self.duracion_reposo_final * self.fps)):
            obs = self.robot.get_observation()
            accion = self.postura_reposo.copy()
            self.robot.send_action(accion)
            # NO añadir a episodio_actual
            time.sleep(self.dt)

        print("✓ Vuelta a reposo completada (no grabada)")
        if self.taladro_movido:
            print("⚠️  ADVERTENCIA: El taladro se movió durante el episodio")
            print("   Considera descartarlo presionando 'R' si no estás en modo --seguir")
        return True

    def guardar_episodio(self):
        """Guarda el episodio actual en el dataset"""
        from lerobot.utils.feature_utils import build_dataset_frame

        if not self.episodio_actual:
            print("⚠️  No hay episodio para guardar")
            return

        print(f"Guardando episodio {self.num_episodios_grabados + 1}...")

        for obs, accion in self.episodio_actual:
            frame = {
                **build_dataset_frame(self.features, obs, prefix="observation"),
                **build_dataset_frame(self.features, accion, prefix="action"),
                "task": self.TAREA,
            }
            self.dataset.add_frame(frame)

        self.dataset.save_episode()
        self.episodio_actual = []

        self.num_episodios_grabados += 1
        print(f"✓ Episodio {self.num_episodios_grabados} guardado")

    def finalizar(self):
        """Finaliza el dataset y lo sube al Hub"""
        print("\n" + "="*60)
        print("FINALIZANDO DATASET")
        print("="*60)

        if self.dataset is not None:
            # Cierra escritores y codifica vídeos pendientes (imprescindible en 0.7)
            self.dataset.finalize()

        if self.num_episodios_grabados == 0:
            print("⚠️  No hay episodios grabados")
            return

        print(f"Episodios totales: {self.num_episodios_grabados}")
        print("Distribución por zona:")
        for zona, count in sorted(self.contador_por_zona.items()):
            print(f"  Zona {zona}: {count} episodios")

        if not self.no_push:
            print("\nSubiendo a Hugging Face Hub...")
            try:
                self.dataset.push_to_hub()
                print("✓ Dataset subido correctamente")
            except Exception as e:
                print(f"⚠️  Error al subir: {e}")
                print(f"   El dataset está guardado localmente en {self.dataset.root}")
        else:
            print("\n⚠️  --no-push activado, NO se sube al Hub")
            print(f"   Dataset guardado localmente en {self.dataset.root}")

        print("="*60)

    def mostrar_vivo(self, texto_cabecera, texto_pie=None, objetivo=None):
        """Muestra la cámara en vivo con textos (y el siguiente objetivo si se da)."""
        obs = self.robot.get_observation()
        percepcion = self.detector.detectar(obs["front"])
        img = cv2.cvtColor(obs["front"], cv2.COLOR_RGB2BGR)
        if objetivo is not None:
            self.dibujar_objetivo(img, objetivo, percepcion, cabecera=texto_cabecera)
        else:
            cv2.rectangle(img, (0, 0), (img.shape[1], 34), (0, 0, 0), -1)
            cv2.putText(img, texto_cabecera, (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 255), 2)
        if texto_pie:
            cv2.putText(img, texto_pie, (8, img.shape[0] - 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)
        cv2.imshow("Grabar Dataset", img)
        return cv2.waitKey(30) & 0xFF

    def confirmar_episodio(self, siguiente_objetivo):
        """
        Ventana tras cada episodio, ANTES de guardarlo.

        - Si todo fue bien: cuenta atrás de `ventana_confirmacion_s` y se guarda solo.
        - Si el taladro se movió: espera a que elijas G (guardar) o R (descartar).
        Teclas: R descartar, G/ENTER guardar ya, P pausar después, Q guardar y terminar.

        Returns:
            (guardar: bool, salir: bool)
        """
        t0 = time.time()
        while True:
            restante = self.ventana_confirmacion_s - (time.time() - t0)
            if self.taladro_movido:
                cab = "TALADRO MOVIDO: G guardar / R descartar"
                pie = "Q = guardar y terminar"
            else:
                cab = f"Guardando en {max(restante, 0):.0f}s... R descartar"
                pie = f"G guardar ya | P pausa | Q terminar   (siguiente: ZONA {siguiente_objetivo[0]})" \
                    if siguiente_objetivo else "G guardar ya | Q terminar"
            tecla = self.mostrar_vivo(cab, pie, siguiente_objetivo)

            if tecla in (ord('r'), ord('R')):
                return False, False
            if tecla in (ord('g'), ord('G'), 13):
                return True, False
            if tecla in (ord('p'), ord('P')):
                self.pausado = not self.pausado
                print(f"Pausa {'ACTIVADA (tras guardar)' if self.pausado else 'desactivada'}")
            if tecla in (ord('q'), ord('Q')):
                return True, True
            if not self.taladro_movido and restante <= 0:
                return True, False

    def run(self, num_episodios_objetivo: int, manual: bool = False,
            semilla: Optional[int] = None):
        """
        Bucle principal.

        Modo automático (por defecto): tras cada episodio se guarda solo y el
        siguiente empieza en cuanto colocas el taladro en la zona que indica la
        pantalla. Modo manual (--manual): hay que pulsar N antes de cada episodio.
        """
        self.num_objetivo = num_episodios_objetivo
        print("\n" + "="*60)
        print("GRABACIÓN AUTOMÁTICA DE DATASET")
        print("="*60)
        print(f"Objetivo: {num_episodios_objetivo} episodios ({'MANUAL: N para cada uno' if manual else 'AUTOMÁTICO'})")
        print("\nCada episodio:")
        print("  1. La pantalla indica la ZONA: coloca el taladro a mano dentro del círculo")
        print("     (no se graba). Cuando ponga 'OK' pulsa N: empieza a grabar y el robot va")
        print("  2. El robot va solo, se para y vuelve (la vuelta no se graba)")
        print("  3. Tras volver: R descarta, G guarda ya, P pausa, Q termina")
        print("     (si no pulsas nada se guarda solo en unos segundos)")
        print("  Durante la espera del taladro: Q termina")
        print("="*60 + "\n")

        # Conectar
        self.robot.connect(calibrate=False)

        # Crear dataset
        self.crear_dataset()

        plan = self.generar_plan(num_episodios_objetivo, semilla)
        salir = False
        try:
            self._bucle(plan, num_episodios_objetivo, manual)
        finally:
            # Aunque haya Ctrl+C o un error, se cierran bien los episodios ya guardados
            if self.num_episodios_grabados >= num_episodios_objetivo:
                print(f"\n✅ Objetivo alcanzado: {num_episodios_objetivo} episodios")
            self.finalizar()
            self.robot.disconnect()
            cv2.destroyAllWindows()

    def _bucle(self, plan, num_episodios_objetivo, manual):
        """Bucle de episodios (ver run)."""
        salir = False

        while self.num_episodios_grabados < num_episodios_objetivo and not salir:
            objetivo = plan[self.num_episodios_grabados]  # si se descarta, se repite el mismo
            cab = f"[{self.num_episodios_grabados + 1}/{num_episodios_objetivo}] Siguiente: ZONA {objetivo[0]}"

            # Pausa o modo manual: esperar tecla
            if self.pausado or manual:
                pie = "PAUSA - P para seguir, Q terminar" if self.pausado else "N = grabar, Q = terminar"
                while True:
                    tecla = self.mostrar_vivo(cab, pie, objetivo)
                    if tecla in (ord('q'), ord('Q')):
                        salir = True
                        break
                    if self.pausado and tecla in (ord('p'), ord('P')):
                        self.pausado = False
                        break
                    if not self.pausado and tecla in (ord('n'), ord('N')):
                        break
                if salir:
                    break

            if not self.grabar_episodio(objetivo):
                break

            siguiente = plan[self.num_episodios_grabados + 1] \
                if self.num_episodios_grabados + 1 < num_episodios_objetivo else None
            guardar, salir = self.confirmar_episodio(siguiente)
            if guardar:
                self.guardar_episodio()
                self.contador_por_zona[objetivo[0]] += 1
            else:
                print(f"✗ Episodio descartado (no se guarda). Se repite ZONA {objetivo[0]}")
                self.episodio_actual = []


def main():
    parser = argparse.ArgumentParser(description='Grabar dataset automáticamente')
    parser.add_argument('--nombre', type=str, required=True,
                       help='Nombre del dataset (ej: taladro_demo)')
    parser.add_argument('--episodios', type=int, default=10,
                       help='Número de episodios a grabar')
    parser.add_argument('--sin-robot', action='store_true', help='Modo simulado')
    parser.add_argument('--real', action='store_true', help='Robot real')
    parser.add_argument('--no-push', action='store_true',
                       help='No subir al Hub (solo guardar local)')
    parser.add_argument('--manual', action='store_true',
                       help='Pulsar N antes de cada episodio (por defecto: automático)')
    parser.add_argument('--continuar', action='store_true',
                       help='Añadir episodios a un dataset existente (--episodios = total final)')
    parser.add_argument('--semilla', type=int, default=None,
                       help='Semilla del plan de zonas (para repetir el mismo orden)')
    parser.add_argument('--seguir', action='store_true',
                       help='Modo seguimiento continuo (default: posición fija)')
    args = parser.parse_args()

    if not args.sin_robot and not args.real:
        print("❌ Debes especificar --sin-robot o --real")
        return

    # Cargar config
    config = cargar_config()

    # Crear robot
    if args.sin_robot:
        from robot_falso import RobotFalso
        robot = RobotFalso(camera_index_front=config["robot"]["cameras"]["front"]["index_or_path"])
    else:
        from lerobot.robots.so_follower import SO101Follower, SO101FollowerConfig
        from lerobot.cameras.opencv import OpenCVCameraConfig
        robot_config = SO101FollowerConfig(
            port=config["robot"]["port"],
            use_degrees=config["robot"]["use_degrees"],
            cameras={
                name: OpenCVCameraConfig(
                    index_or_path=cam_cfg["index_or_path"],
                    width=cam_cfg["width"],
                    height=cam_cfg["height"],
                    fps=cam_cfg["fps"]
                )
                for name, cam_cfg in config["robot"]["cameras"].items()
            },
            id=config["robot"]["id"]
        )
        robot = SO101Follower(robot_config)

    # Crear y ejecutar grabador
    grabador = GrabadorDatasetAuto(
        robot=robot,
        config=config,
        nombre_dataset=args.nombre,
        no_push=args.no_push,
        modo_seguir=args.seguir,
        continuar=args.continuar
    )

    grabador.run(num_episodios_objetivo=args.episodios, manual=args.manual, semilla=args.semilla)


if __name__ == "__main__":
    main()
