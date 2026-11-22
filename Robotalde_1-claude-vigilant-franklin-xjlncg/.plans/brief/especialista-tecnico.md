# Especialista técnico · Aprendiz (concepto v3 + recortes de la versión 4) · LeRobot 0.7 + SO-101

18-11-2026. Código leído: `huggingface/lerobot` etiqueta `v0.7.0` (clon en el scratchpad, `git describe` = v0.7.0).
Rutas relativas a `src/lerobot/`. Lo que no está en el código va marcado **[sin verificar]**.
Alcance según la versión 4: fuera lectura de etiquetas, `/subtask` a mitad, tercer objeto, reed/LED; la voz es una
capa opcional sobre botones/teclado; `Put it away.` solo si el sábado a las 16:00 estamos en la rama A.

## Parte 1 · Lo verificado en el código

### 1.1 `lerobot-rollout --interactive=true`: cómo llegan las órdenes
- **Por stdin, línea a línea.** `rollout/interactive.py:112-160`: `InteractiveSession` usa `StdinCommandListener`
  (`utils/stdin_input.py`) y traduce cada línea que empieza por `/` en una llamada a `RolloutController`
  (`rollout/controller.py:130`): `start()` l.231, `reset()` l.246, `stop()` l.269, `set_task()` l.281. Son métodos
  seguros entre hilos, así que también hay una API de Python, pero exige construir el contexto a mano
  (`build_rollout_context(cfg, LinkedEvent(...))`, l.155): no compensa.
- **Funciona con tubería**: el docstring (l.119-122) da el ejemplo `(printf '/start\n'; sleep 60; printf '/stop\n') |
  lerobot-rollout ... --interactive=true`. **Si stdin se cierra (EOF), la sesión se para** (l.269 `_handle_eof`).
- **Solo `--strategy.type=base` o `sentry` admiten `--interactive`** (`rollout/configs.py:95,112,393-404`;
  `episodic`, `highlight` y `dagger` dan error). La guía no lo dice.
- `--duration` acota **cada segmento** de `/start`, no la sesión (`configs.py:307-308`). Cuando el segmento acaba,
  el robot **se queda quieto en su postura** («Rollout run ended. Robot is holding position», `interactive.py:191`).
- `/reset` para el movimiento, **lleva el brazo a la postura capturada al arrancar el proceso** y **devuelve la tarea
  a la del arranque** (`controller.py:246-267`). Hay que lanzar el rollout con el brazo en la postura de aparcado.
- `/subtask <texto>` vale con el robot parado o en marcha; se aplica en la siguiente inferencia (`controller.py:281`,
  `interactive.py:278-300`). Con ACT no hace nada útil (ACT no lee texto, 1.5).
- Los registros por debajo de ERROR se silencian en modo interactivo (`configs.py:312-316`); los mensajes de estado
  salen por `_print` (a qué flujo, stdout o stderr: **[sin verificar]**; leer los dos).

**Puente servidor → rollout (lo más simple y robusto):** el servidor lanza
`lerobot-rollout ... --strategy.type=base --interactive=true --duration=30` con `subprocess.Popen(stdin=PIPE,
stdout=PIPE, stderr=STDOUT, text=True, bufsize=1)` y lo mantiene vivo toda la demo. Por cada intento escribe
`/subtask Bring the screw cup.\n` y luego `/start\n`; el botón «hecho» o «fallo» del operador escribe `/reset\n`
(el brazo vuelve a aparcar; el cronómetro para ahí). Lee la salida buscando `Rollout running`, `Rollout run ended`,
`Robot reset` y `FAILED` para pintar el estado. Nunca cerrar stdin. Voz → LLM → frase fija es solo la forma de
elegir la línea que se escribe; los botones escriben la misma línea.
- **Rama B (un ACT por orden):** dos procesos no pueden abrir el mismo puerto serie. Opción barata: matar el rollout
  y relanzarlo con el otro checkpoint (medir el tiempo de arranque el jueves **[sin verificar]**, ACT carga rápido).
  Si pasa de ~15 s, script propio con `robot/politica.py` (ya carga ACT) y el `SO101Follower` con los dos ACT en
  memoria.

### 1.2 Estrategias `episodic` y `dagger`
- **episodic** (`configs.py:160-195`, `strategies/episodic.py`): como `lerobot-record` pero conduce la política;
  `num_episodes` × `episode_time_s` + `reset_time_s`; teclas → (terminar), ← (descartar y repetir), Esc. Sin brazo
  guía, entre episodios mantiene la postura inicial; con guía, lleva el seguidor a la postura del guía. Exige
  `--dataset.repo_id` y el nombre **debe empezar por `rollout_`** (`rollout/context.py:447`). No admite
  `--interactive`. Útil para las series X/10 grabadas (el vídeo sirve de prueba).
- **dagger** (`configs.py:197-243`, `strategies/dagger.py:1-30`): exige `--teleop.type` y dataset. Teclado (por
  defecto `space` pausa/reanuda, `tab` empieza/termina corrección, `enter` sube) o pedal evdev. Al pausar, el guía
  SO-101 **se mueve solo hasta la postura del seguidor** (el `SOLeader` tiene `send_feedback`,
  `teleoperators/so_leader/so_leader.py:136`) y el técnico toma el mando sin tirón. Con `record_autonomous=false`
  (defecto) **solo se graban las correcciones, una por episodio**, empezando en el estado del fallo. Añade la
  columna `intervention` (`configs.py:242`): **ese dataset no se puede fusionar con los normales** hasta quitarla
  (`lerobot-edit-dataset --operation.type remove_feature --operation.feature_names='["intervention"]'`), porque
  `merge` exige features idénticas (`datasets/aggregate.py:123-157`). Usa un oyente de teclado global
  (`utils/keyboard_input.py`); en Linux con Wayland o por SSH puede no recibir teclas **[sin verificar]**.
- **Decisión (versión 4):** el código existe y encaja, pero no está probado en nuestro hardware. Plan: demostraciones
  normales con `lerobot-record` desde las posiciones donde falló. `dagger` solo si el jueves funciona en seco en
  10 min (pausar, corregir 1 vez, ver el episodio).

### 1.3 Grabación multitarea
- `single_task` es un texto por sesión y se escribe en cada fotograma (`scripts/lerobot_record.py:372`). Al guardar
  un episodio, las tareas nuevas se añaden a `tasks` (`datasets/dataset_writer.py:283-294`,
  `dataset_metadata.py:543-568`). Por tanto **`--resume=true` con otra `single_task` sí funciona** (la guía lo daba
  como no verificado).
- `--resume=true` no vuelve a poner sello (`configs/dataset.py:78-90`, `lerobot_record.py:451-476`) y comprueba que
  robot y fps coinciden. `--dataset.no_stamp=true` deja el nombre exacto: **usarlo siempre**.
  `--dataset.num_episodes` al reanudar = episodios adicionales (doc) **[sin verificar en el código]**.
- `lerobot-record` rechaza nombres que empiezan por `eval_` (l.466).
- Fusión: `merge` exige mismo fps, `robot_type` y features (`aggregate.py:123`). Mismas cámaras, mismos nombres,
  misma resolución en todas las tandas.
- **Recomendación:** un dataset por orden (`aprendiz_vaso`, `aprendiz_caja`, luego `aprendiz_guardar`), cada uno
  ampliado con `--resume`; los ACT se entrenan con su dataset tal cual y SmolVLA con la fusión. Así no hay que
  buscar índices de episodios.

### 1.4 Inferencia: RTC local y servidor remoto
- RTC solo para políticas con `supports_rtc()`: SmolVLA sí (`policies/smolvla/modeling_smolvla.py:150`), ACT no
  (`inference/rtc.py:86-100`). Flags: `--inference.type=rtc --inference.rtc.execution_horizon=10
  --inference.rtc.max_guidance_weight=10.0` (defectos en `policies/rtc/configuration_rtc.py:58`;
  `queue_threshold=30`, `startup_timeout_s=120` en `inference/factory.py:80-91`).
- SmolVLA en la GTX 1660 de 6 GB: 450 M parámetros (~1,8 GB en fp32) más activaciones; probablemente cabe para
  inferencia **[sin verificar en esa GPU]**. Comprobación del jueves: `--device=cuda` con un checkpoint cualquiera de
  SmolVLA y `nvidia-smi`. La GTX 1660 no tiene TF32 (el flag `tf32` no estorba).
- Remoto: `lerobot-policy-server` (`scripts/lerobot_policy_server.py`, Zenoh) y cliente
  `--inference.type=remote --inference.endpoint=tcp/IP:7447` (`factory.py:102-133`); con remoto se prohíben
  `--policy`, `--device` (`configs.py:418-424`). No se reconecta sola. Solo si SmolVLA no cabe en la 1660.

### 1.5 ACT
- ACT no usa la instrucción (en `policies/act/modeling_act.py` no aparece `task`): **un ACT por orden**.
- Defectos: `chunk_size=100`, `n_action_steps=100`, `dim_model=512` (`configuration_act.py:85-103`).
  `--rename_map` en `lerobot-train` **exige política preentrenada** (`configs/train.py:322`): con ACT no se pasa.
- Episodios de ~20 s: 50 ep × 20 s × 30 fps = 30 000 fotogramas; con batch 8, 5-8 épocas ≈ 20 000-30 000 pasos.
  Para 30 episodios (viernes): 12 000-15 000 pasos. Medir `step_s` en los 100 primeros pasos: a 640 × 480 irá más
  lento que los 0,2 s/paso estimados a 256 × 192 en `robot/entrenar.md` **[sin verificar]**.
- SmolVLA: `chunk_size=50`, `freeze_vision_encoder=True`, `train_expert_only=True`, `empty_cameras=0`,
  imágenes a 512 × 512 con relleno (`configuration_smolvla.py:29-70`).

### 1.6 Diferencias guía ↔ código que pueden rompernos el viernes
1. `--interactive=true` **solo con `base` o `sentry`**; con `episodic`/`dagger` el comando falla al arrancar.
2. `/reset` devuelve la **tarea del arranque** y la **postura del arranque**: lanzar con el brazo aparcado y mandar
   siempre `/subtask` antes de `/start`.
3. Cerrar stdin para la sesión: el puente debe mantener el proceso y su tubería abiertos.
4. Dataset de `dagger` con columna `intervention` → no fusiona sin `remove_feature`.
5. `--resume` con otra tarea sí vale (la guía decía no verificado); sin `no_stamp` hay que arrastrar el sello.
6. `--rename_map` con `--policy.type=act` da error (solo con `--policy.path`).
7. HF Jobs usa `huggingface/lerobot-gpu:latest` por defecto (`configs/default.py:244-250`): fijar `--job.image` a una
   imagen 0.7.0 si existe **[sin verificar qué etiquetas hay]**; si no, ensayar el jueves que el checkpoint de la
   nube carga en nuestro 0.7.0 local.
8. `save_checkpoint_to_hub` exige `--policy.repo_id` (`configs/train.py:373`).

## Parte 2 · Plan operativo

### A. Software del jueves (priorizado; 2 personas, ~9 h)
| P | Pieza | Horas | Hecho cuando |
|---|---|---|---|
| 1 | `robot/comandos.sh` (o `.ps1`): calibrar, teleoperar, grabar, entrenar, rollout con IDs, puertos y cámaras fijos; probado en seco en los dos portátiles | 2 | Los 5 comandos arrancan sin robot hasta el error de puerto |
| 2 | `robot/grabar.py`: envuelve `lerobot-record --resume --no_stamp` y muestra en grande la siguiente posición de la lista (zona 1-5, giro de la caja, manos sí/no) y el contador de episodios válidos; registra los descartados | 1,5 | Lista de 50 posiciones barajada y reproducible (semilla) |
| 3 | `robot/puente.py`: rollout interactivo como subproceso (1.1) + botones «vaso», «caja», «hecho», «fallo», «parar» + cronómetro | 2 | Con un checkpoint público y sin robot llega hasta el error de puerto; con tubería falsa, la máquina de estados pasa los tests |
| 4 | Hoja X/10 y matriz frase × objeto: CSV + página que pinta las tablas (frase, objeto puesto, zona, objeto traído, tiempo) | 1 | Las tres tablas del apartado D salen del CSV |
| 5 | Pantalla «hoja de trabajo»: orden activa en inglés, contador «sin ayuda X de N», tiempo por orden (sin personaje ni ranking) | 1 | Se ve en la tablet por WebSocket o con recarga |
| 6 | Ensayo de la nube: `lerobot-train` de SmolVLA y ACT 200 pasos en HF Jobs con un dataset público de SO-101 (`lerobot/svla_so101_pickplace` **[sin verificar que existe y sus nombres de cámara]**) y carga local del checkpoint | 1 (+ espera) | Checkpoint descargado y `lerobot-rollout` lo carga sin robot |
| 7 | Voz (opcional): `lewelder/voz.py` con vocabulario nuevo → misma línea que el botón | 0,5 | Solo si 1-6 están verdes |
| — | Lectura de etiqueta | 0 | Fuera de alcance (versión 4) |

### B. Plan de datos
- **Escena:** tablero propio, almacén de 25 × 18 cm al fondo detrás del brazo, partido en 5 zonas (4 esquinas +
  centro) con marcas solo debajo del tablero o fuera de cámara; plato fijo junto a la mano del técnico. Flexo fijo.
  Foto de referencia de cada cámara pegada en el portátil.
- **Cámaras:** `top` (cenital, ve almacén y plato) y `wrist`, 640 × 480 a 30 fps, siempre los mismos índices o
  rutas `/dev/v4l/by-id` **[en Windows, índices: comprobar con `lerobot-find-cameras`]**.
- **Frases exactas** (una por orden, idénticas en grabación, entrenamiento y rollout): `Bring the screw cup.`,
  `Bring the memory box.`, `Put it away.` (si rama A).
- **Tandas** (en todos los episodios están los dos objetos en el almacén):

| Tanda | Cuándo | Orden | Episodios | Variedad |
|---|---|---|---|---|
| 1 | Vie 19:30-21:00 | vaso | 30 | 5 zonas × 6; la caja en otra zona, rotando parejas |
| 2 | Vie 21:00-22:45 | caja | 30 | 5 zonas × 6; giro 0°, +30°, −30° |
| 3 | Sáb 10:30-12:00 | vaso + caja | 20 + 20 | Las zonas y parejas que peor salieron en la matriz |
| 4 | Sáb 14:00-15:30 | lo que falle | 20-40 | Demostraciones normales que empiezan donde falló (cuaderno del aprendiz) |
| 5 | Sáb 16:15-17:30 | `Put it away.` | 30-50 | Solo en rama A |

- Duración: `--dataset.episode_time_s=25 --dataset.reset_time_s=8`; el operador corta con → al soltar en el plato
  (episodios de 12-20 s). Empezar y acabar en la misma postura de aparcado.
- Manos: en 1 de cada 5 episodios, la mano del técnico trabaja en el borde del plano (como en la demo); nunca dentro
  del almacén.
- Calidad (si no, ← y se repite): agarre al primer intento, sin chocar, objeto entero en el plato, cadencia ≥ 29 Hz
  en el informe del episodio, objeto visible en `top` al inicio. Mismo operador y mismo agarre (vaso por arriba,
  caja por el lado largo). Subir al Hub al final de cada tanda.

### C. Plan de entrenamiento
- **Ciclo 0 (vie 23:00):** ACT vaso y ACT caja en la GTX 1660, uno tras otro; SmolVLA en HF Jobs con la fusión.
```bash
lerobot-edit-dataset --new_repo_id $U/aprendiz_traer_v1 --operation.type merge \
  --operation.repo_ids "['$U/aprendiz_vaso', '$U/aprendiz_caja']" --push_to_hub true
lerobot-train --policy.path=lerobot/smolvla_base --dataset.repo_id=$U/aprendiz_traer_v1 \
  --policy.repo_id=$U/smolvla_aprendiz_c0 \
  --rename_map='{"observation.images.top": "observation.images.camera1", "observation.images.wrist": "observation.images.camera2"}' \
  --batch_size=32 --steps=12000 --save_freq=3000 --save_checkpoint_to_hub=true \
  --job.target=l4x1 --job.timeout=6h --output_dir=outputs/smolvla_c0 --job_name=smolvla_c0
lerobot-train --dataset.repo_id=$U/aprendiz_vaso --policy.type=act --policy.device=cuda \
  --policy.repo_id=$U/act_vaso_c0 --batch_size=8 --steps=15000 --save_freq=5000 \
  --output_dir=outputs/act_vaso_c0 --job_name=act_vaso_c0      # luego igual con aprendiz_caja
```
  Tiempos: SmolVLA 12 000 pasos a 0,5-0,7 s/paso en L4 ≈ 2-2,5 h (lista ~2:00); ACT ≈ 1 h cada uno si `step_s`
  ≈ 0,2 **[sin verificar a 640 × 480]**; si sale más lento, el segundo ACT a `t4-small` en HF Jobs. Si falta
  `camera3`: `--policy.empty_cameras=1`.
- **Ciclo 1 (sáb ~12:15):** fusión con tanda 3 → SmolVLA 15 000 pasos (l4x1, ~2,5-3 h, listo ~15:00) y los dos ACT
  ampliados en la 1660. **Ciclo 2 (sáb ~15:45):** + tanda 4 (y 5 si rama A); SmolVLA listo ~19:00; es el último.
- **Elección del checkpoint:** nunca por la pérdida. Serie de 10 en el robot (D) con 2-3 checkpoints
  (`--policy.pretrained_revision=009000` o la carpeta `checkpoints/NNNNNN`); gana el mayor X/10, a igualdad el más
  rápido.
- Rollout de SmolVLA: `lerobot-rollout --strategy.type=base --interactive=true --policy.path=$U/smolvla_aprendiz_c1
  --robot.type=so101_follower --robot.port=... --robot.id=seguidor_robotalde --robot.cameras="{...igual...}"
  --rename_map='{...igual...}' --task="Bring the screw cup." --duration=30 --device=cuda --inference.type=rtc
  --inference.rtc.execution_horizon=10`. ACT: igual sin `rename_map`, sin RTC.

### D. Protocolo de medida (una persona coloca, otra apunta; el CSV de A4)
- **Prueba de la frase (sáb 9:30-10:30):** SmolVLA c0; 10 intentos por frase, los dos objetos siempre en el almacén,
  zonas permutadas con la lista barajada; columnas vaso / caja / nada. ~2 min por intento → 40 min. Decisión a las
  10:30 con el árbol del equipo rojo (≥ 8/10 en las dos → A; 6-7 → 20 ep más y repetir 15:00; ≤ 5 → B).
- **Serie de 10 por orden (sáb 16:00):** con el mejor checkpoint de cada familia (ACT por orden, SmolVLA c1); éxito
  = objeto en el plato en < 25 s sin tocar nada. ~45 min.
- **Comparativa (sáb 19:30-20:45):** ACT por orden · SmolVLA c1 · SmolVLA c2 × traer vaso (X/10), traer caja (X/10),
  caja nunca vista (X/5), zona nueva (X/5). Sin flexo desplazado (recortado).
- **Con y sin robot (sáb 17:30-18:00, 30 min):** 5 cambios de memoria con robot y 5 sin él, alternando; mismo
  técnico; se mide tiempo total, viajes de la mano al almacén y veces que se levanta. Con el robot sin ayuda,
  cuenta como fallo.
- **Dom 10:00:** serie de 5 con cronómetro; declarar solo lo que salga (≤ 3/5 → zonas buenas; ≤ 1/5 → rama D).

### E. Cronograma (personas: **T** técnico/teleoperador, **E** entrenamiento y robot, **S** software y medida)
| Hora | T | E | S |
|---|---|---|---|
| Vie 17:00-18:30 | Montar tablero, flexo, almacén, plato | Calibrar guía y seguidor; cámaras y fotos de referencia | `comandos.sh` en el portátil del evento; puente sin robot |
| 18:30-19:30 | Teleoperar en libre; **19:30: 10 agarres por objeto** (caja < 8/10 → cambiar ancho u objeto) | Prueba de 2 episodios y subida al Hub | `grabar.py` con la lista en pantalla |
| 19:30-21:00 | Tanda 1 (vaso) | Revisar cadencia y vídeos de cada episodio | Lleva la lista y descartes. **21:00: < 30 válidos → solo vaso** |
| 21:00-22:45 | Tanda 2 (caja) | Revisa; 22:00 ACT de prueba 200 pasos | Hoja X/10 y pantalla |
| **23:00 puerta** | Cuenta ≥ 50 válidos | Lanza ciclo 0 (SmolVLA nube + ACT vaso → caja en la 1660) | < 50 → rama C: solo ACT del vaso |
| 23:30-07:30 | Dormir | Dormir (ACT encadenados en un script) | Dormir |
| Sáb 07:30-09:30 | Prepara escena | Descarga checkpoints, rollout en seco | Puente con el robot real, 3 intentos |
| **9:30-10:30 puerta** | Coloca | Opera el puente | Apunta: matriz frase × objeto → A / repetir / B |
| 10:30-12:00 | Tanda 3 | Serie corta de los ACT c0 | Matriz en pantalla |
| **12:00 puerta** | — | Ciclo 1 lanzado; primer modelo movido | Si nada se mueve → todo al ACT del vaso |
| 12:00-14:00 | Comer; ensaya el banco | ACT c1 en la 1660 | Cuaderno del aprendiz (fallos) |
| **14:00** | Tanda 4 (desde donde falló) | Algún modelo mueve el robot; si ninguno → rama C | Lista de posiciones de fallo |
| 15:45 | — | Ciclo 2 lanzado | — |
| **16:00** | Coloca | Serie de 10 por orden | Apunta → A / B / C; `Put it away.` solo en A (tanda 5) |
| 17:30-18:00 | Medida con y sin robot (5 + 5) | Cronometra | Apunta |
| 18:00-19:30 | Vídeo de 1 min con lo mejor | Graba vídeo | Monta vídeo |
| **19:30-20:45 · puerta 20:00** | Coloca | Comparativa | Tablas; < 5/10 → rama C o D |
| 20:45-23:00 | Ensayo de la serie de 5 con cronómetro | SmolVLA c2 si llega; 21:00 montaje congelado | Guion y pitch |
| Dom 07:30-10:00 | Ensayos | Elige modelo por la tabla | Pantallas finales |
| **10:00 puerta** | Serie de 5 completa | | ≤ 3/5 declarar solo lo que salió; ≤ 1/5 rama D |
| 10:00-11:00 | Escena fija, fotos | Congelar versión, todo al Hub | Repositorio y README |

### F. Riesgos técnicos (orden) y su comprobación más barata
1. **SmolVLA no lee la frase con ~60-100 episodios** (coge lo más cercano): matriz del sábado 9:30; jueves, mirar
   si el ensayo de la nube con el dataset público ya distingue tareas **[sin verificar que tenga varias]**. Respaldo:
   rama B lista desde el viernes.
2. **Cadencia de grabación < 30 Hz con dos cámaras 640 × 480** (movimiento acelerado en el dataset): grabar 2
   episodios el jueves en el portátil del evento y leer el informe; si baja, `--dataset.streaming_encoding=true` y, si no basta,
   bajar la resolución de las dos cámaras (el fps debe ser común).
3. **El checkpoint de HF Jobs (`lerobot-gpu:latest`) no carga en 0.7.0 local:** ensayo de la nube del jueves con
   200 pasos; fijar `--job.image` si hace falta.
4. **SmolVLA no cabe o va lento en la 1660 (RTC):** jueves, `lerobot-rollout` con cualquier SmolVLA y
   `nvidia-smi`; respaldo, servidor remoto en un portátil con más GPU o ACT.
5. **Puente frágil (stdin, EOF, postura de `/reset`, cambio de ACT):** test con tubería falsa y con el robot el
   sábado 7:30; medir el relanzamiento para la rama B.
6. Cámaras que cambian de índice al reconectar y luz distinta en el evento: fotos de referencia y rutas fijas.
7. Torch sin CUDA en Windows (`torch.cuda.is_available()`), jueves.
