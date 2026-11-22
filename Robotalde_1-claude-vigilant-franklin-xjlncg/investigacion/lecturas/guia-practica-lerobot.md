# Guía práctica de LeRobot 0.7 con un SO-101

Guía para seguir en el hackathon (Bilbao, 20-22 nov 2026), desde montar el robot hasta desplegar la política.
Está hecha a partir de la documentación oficial **en la etiqueta `v0.7.0`** del repositorio (5-11-2026), leída en su
fuente (`docs/source/*.mdx`) y contrastada con el código de esa misma etiqueta.

Leyenda: **[doc]** aparece en la documentación oficial · **[código]** no está en la doc, pero se ha comprobado en
el código fuente de v0.7.0 · **[NO VERIFICADO]** es una deducción nuestra que hay que probar el viernes.

---

## 1. Fuentes consultadas

| Fuente | Versión | Qué se ha sacado |
|---|---|---|
| `github.com/huggingface/lerobot`, etiqueta `v0.7.0` (commit 410c095, 5-11-2026) | 0.7.0 | Todos los `.mdx` citados abajo y el código de `robots/so_follower`, `motors`, `datasets`, `configs` y `examples/` |
| `github.com/huggingface/lerobot`, rama `main` (18-11-2026, `pyproject` dice 0.7.1) | 0.7.1-dev | Comparación: las páginas usadas (so101, il_robots, smolvla, act, cameras, inference, remote_inference, hardware_guide, cheat-sheet, installation) son **idénticas** a las de v0.7.0 |
| `docs/source/installation.mdx` | v0.7.0 | Instalación y extras |
| `docs/source/so101.mdx` | v0.7.0 | Montaje, puertos, IDs, calibración |
| `docs/source/il_robots.mdx` | v0.7.0 | Teleoperación, grabación, Hub, visualización, replay, entrenamiento, HF Jobs, rollout |
| `docs/source/cameras.mdx`, `cheat-sheet.mdx`, `hardware_guide.mdx` | v0.7.0 | Cámaras, chuleta de comandos, VRAM y tiempos |
| `docs/source/smolvla.mdx`, `act.mdx`, `rename_map.mdx` | v0.7.0 | Ajuste fino de SmolVLA, ACT y cambio de nombre de las cámaras |
| `docs/source/inference.mdx`, `remote_inference.mdx` | v0.7.0 | `lerobot-rollout`, RTC, modo interactivo, servidor de políticas |
| `docs/source/using_dataset_tools.mdx`, `lerobot-dataset-v3.mdx` | v0.7.0 | Visualizar, fusionar y editar datasets; `finalize()` |
| `docs/source/feetech.mdx`, `backwardcomp.mdx` | v0.7.0 | Firmware Feetech; cambios de calibración |
| `examples/omx/record_grab.py`, `examples/so100_to_so100_EE/record.py` | v0.7.0 | Grabar sin teleoperar; cinemática con URDF |
| Curso de robótica de HF: `huggingface.co/learn/robotics-course` (unidades 0, 1.1 y 1.4) | web, nov 2026 | Solo hay práctica de carga de datasets (unidad 1.4). Las unidades de aprendizaje por imitación y modelos fundacionales siguen como "Coming soon" |
| `rustypot` 1.14.0 (archivo de tipos `.pyi`) | 1.14.0 | Registros de temperatura, carga y corriente del STS3215 |

Las páginas web `huggingface.co/docs/lerobot` muestran `main` por defecto. Si se consultan allí, conviene elegir la
versión v0.7.0 en el selector, porque en otras versiones cambian los nombres de los comandos.

---

## 2. Lista de comprobación de material y software

**Hardware (antes del viernes)**
- [ ] SO-101 seguidor (6 motores STS3215 1/345) y guía (motores con reductoras 1/191, 1/345, 1/191, 1/147, 1/147, 1/147 en las articulaciones 1 a 6) **[doc]**.
- [ ] 2 placas controladoras de bus (una por brazo), 2 fuentes de alimentación y 2 cables USB de datos (no solo de carga).
- [ ] Cables de 3 pines de repuesto, destornilladores, tornillos M2x6 y M3x6 de repuesto **[doc: montaje]**.
- [ ] 2 sargentos (C-clamp) para fijar los brazos a la mesa (el diagrama de homing del código los dibuja).
- [ ] Cámara cenital y cámara de muñeca, con soportes rígidos. Un hub USB con alimentación propia **[NO VERIFICADO: recomendación nuestra]**.
- [ ] Iluminación difusa y constante (flexo o panel LED) **[doc: cameras.mdx]**.
- [ ] Los objetos de la tarea y algo de cinta para marcar sus posiciones en la mesa.

**Software (instalar y probar ya en el portátil Windows)**
- [ ] Python 3.12 (LeRobot 0.7 pide `>=3.12`) y conda (miniforge) o uv.
- [ ] `ffmpeg` (con conda: `conda install ffmpeg -c conda-forge`).
- [ ] LeRobot 0.7.0 con los extras `core_scripts,feetech,smolvla,training` (y `kinematics` para la cinemática inversa).
- [ ] PyTorch **con CUDA** en Windows (ver la sección 7: la doc dice que Windows usa las ruedas por defecto de PyPI, que en Windows suelen ser solo CPU).
- [ ] Token de Hugging Face con permiso de escritura y `hf auth login` hecho en el portátil.
- [ ] Probar HF Jobs con `hf jobs hardware` (lista de tipos de máquina y precios).
- [ ] URDF del SO-101: `so101_new_calib.urdf` del repositorio `TheRobotStudio/SO-ARM100` (`Simulation/SO101/`) **[doc: comentario en el ejemplo EE]**.
- [ ] Opcional: software Feetech FD (solo Windows) para actualizar firmware y diagnosticar motores **[doc]**.

---

## 3. Paso a paso con comandos

> Los ejemplos de la doc usan puertos de Linux o macOS (`/dev/ttyACM0`, `/dev/tty.usbmodem...`). En Windows serán
> `COM3`, `COM4`... (`lerobot-find-port` usa `pyserial` para listar los COM en Windows **[código]**). Los comandos
> multilínea de la doc usan `\` (bash). En PowerShell la continuación de línea es el acento grave `` ` ``, o se
> escribe el comando en una sola línea. La variable `${HF_USER}` es sintaxis bash: en PowerShell, usar `$env:HF_USER`
> o escribir el usuario a mano.

### 3.1 Instalación [doc]
```bash
conda create -y -n lerobot python=3.12
conda activate lerobot
conda install ffmpeg -c conda-forge
pip install 'lerobot[core_scripts,feetech,smolvla,training]'   # desde PyPI
# o desde el código fuente, fijando la versión:
git clone https://github.com/huggingface/lerobot.git && cd lerobot && git checkout v0.7.0
pip install -e ".[core_scripts,feetech,smolvla,training]"
```
- Extras: `core_scripts` = dataset + hardware + viz (para record, replay y calibrate); `training` = dataset + accelerate + trackio; `feetech` = motores del SO-101 (a través de `rustypot`).
- Cinemática inversa: extra `kinematics` (instala `placo`) **[código: pyproject]**.
- Si hay errores de compilación en Linux, la doc da la lista de paquetes `apt` necesarios (cmake, build-essential, libav*).

### 3.2 Puertos e IDs de los motores [doc: so101.mdx]
1. Conectar cada placa por USB y a la corriente, y ejecutar `lerobot-find-port`. El script pide desconectar el cable y pulsar Enter, y así identifica el puerto de cada brazo. Hay que apuntar cuál es el del seguidor y cuál el de la guía.
2. En Linux puede hacer falta `sudo chmod 666 /dev/ttyACM0`.
3. Asignar IDs y baudrate (se graba en la EEPROM: basta hacerlo una vez por motor):
```bash
lerobot-setup-motors --robot.type=so101_follower --robot.port=COM3
lerobot-setup-motors --teleop.type=so101_leader  --teleop.port=COM4
```
El script pide conectar **un solo motor cada vez**, empezando por la pinza (`gripper`, id 6) y acabando en `shoulder_pan` (id 1).
Si falla, revisar la alimentación, el USB y el cable de 3 pines. En una placa Waveshare, los dos jumpers deben estar en el canal `B` (USB).
4. Al acabar, encadenar los motores y conectar el cable del motor 1 a la placa.

Nombres de las articulaciones (claves de acción y estado): `shoulder_pan`, `shoulder_lift`, `elbow_flex`,
`wrist_flex`, `wrist_roll`, `gripper` (cada una con el sufijo `.pos`) **[código]**.

### 3.3 Calibración [doc]
```bash
lerobot-calibrate --robot.type=so101_follower --robot.port=COM3 --robot.id=seguidor_robotalde
lerobot-calibrate --teleop.type=so101_leader --teleop.port=COM4 --teleop.id=guia_robotalde
```
- Primero se ponen todas las articulaciones **a mitad de su recorrido** y se pulsa Enter. Después se mueve cada articulación por todo su rango. `wrist_roll` se trata como un motor de vuelta completa **[código]**.
- El `id` da nombre al archivo de calibración. **Hay que usar siempre el mismo `id`** al teleoperar, grabar y evaluar.
- La calibración es lo que permite que una red entrenada en un robot funcione en otro.
- En 0.7, el seguidor y la guía usan por defecto `use_degrees=True`: las articulaciones en grados y la pinza en 0..100 **[código]**.

### 3.4 Teleoperación [doc]
```bash
lerobot-teleoperate \
  --robot.type=so101_follower --robot.port=COM3 --robot.id=seguidor_robotalde \
  --teleop.type=so101_leader --teleop.port=COM4 --teleop.id=guia_robotalde
```
Si falta alguna calibración, el comando la lanza automáticamente.

### 3.5 Cámaras [doc: cameras.mdx]
```bash
lerobot-find-cameras opencv
```
Lista los índices y guarda fotos de prueba en `outputs/captured_images`. Los índices pueden cambiar al reiniciar o
al cambiar el USB de sitio, así que hay que comprobarlos cada vez que se monta el puesto.
Teleoperación con cámaras y visualización en Rerun:
```bash
lerobot-teleoperate \
  --robot.type=so101_follower --robot.port=COM3 --robot.id=seguidor_robotalde \
  --robot.cameras="{ top: {type: opencv, index_or_path: 0, width: 640, height: 480, fps: 30}, wrist: {type: opencv, index_or_path: 1, width: 640, height: 480, fps: 30}}" \
  --teleop.type=so101_leader --teleop.port=COM4 --teleop.id=guia_robotalde \
  --display_data=true
```
Consejos de la doc:
- Luz difusa y constante, sin sol directo, reflejos ni sombras que se muevan.
- Cámaras fijadas de forma rígida, sin moverlas entre sesiones ni entre la grabación y el despliegue.
- El objeto, la pinza y el destino deben verse al menos en una cámara.
- 640×480 a 30 fps basta.
- `OpenCVCameraConfig` acepta `fourcc` (por ejemplo `MJPG`) y `backend`. El ejemplo de OMX usa `fourcc: MJPG` con dos cámaras. En Windows con DSHOW, LeRobot fija el FOURCC después de la resolución **[código]**.
- **Los nombres de las cámaras (`top`, `wrist`) se convierten en `observation.images.top` y `observation.images.wrist`.** Hay que usar los mismos nombres y resoluciones en la grabación, el entrenamiento y el despliegue.

### 3.6 Grabación con tarea en lenguaje natural [doc: il_robots.mdx]
```bash
hf auth login --token ${HUGGINGFACE_TOKEN} --add-to-git-credential
HF_USER=$(NO_COLOR=1 hf auth whoami | awk -F': *' 'NR==1 {print $2}')

lerobot-record \
  --robot.type=so101_follower --robot.port=COM3 --robot.id=seguidor_robotalde \
  --robot.cameras="{ top: {type: opencv, index_or_path: 0, width: 640, height: 480, fps: 30}, wrist: {type: opencv, index_or_path: 1, width: 640, height: 480, fps: 30}}" \
  --teleop.type=so101_leader --teleop.port=COM4 --teleop.id=guia_robotalde \
  --display_data=true \
  --dataset.repo_id=${HF_USER}/robotalde_tarea1 \
  --dataset.num_episodes=10 \
  --dataset.single_task="Pick the red cube and place it in the box" \
  --dataset.episode_time_s=30 --dataset.reset_time_s=15 \
  --dataset.streaming_encoding=true --dataset.encoder_threads=2
```
- **Sello de tiempo**: `lerobot-record` añade `_YYYYMMDD_HHMMSS` al `repo_id`, de modo que `robotalde_tarea1` se guarda como `robotalde_tarea1_20261121_103000`. Para conservar el nombre exacto: `--dataset.no_stamp=true`.
- Valores por defecto: `episode_time_s=60`, `reset_time_s=60`, `num_episodes=50`, `fps=30`, `push_to_hub=true`, `video=true` **[doc y código]**.
- Teclado durante la grabación: `→` o `n` termina el episodio (o el reset) y pasa al siguiente; `←` o `r` descarta el episodio y lo repite; `Esc` o `q` termina, codifica y sube. Si no hay backend de teclado global, lee las teclas del terminal: lanzar el comando desde un terminal interactivo y con el foco puesto.
- Copia local en `~/.cache/huggingface/lerobot/{repo_id}`.
- **Reanudar o añadir episodios**: repetir el mismo comando con `--resume=true`, el `repo_id` completo **con su sello** y `--dataset.root=<ruta local>` (obligatorio). En ese caso `--dataset.num_episodes` es el número de **episodios adicionales**, no el total. Sin `--resume`, se crea un dataset nuevo con otro sello.
- **Informe de cadencia**: al acabar cada episodio se imprime la frecuencia real. Si baja de 30 Hz, el dataset sigue diciendo 30 Hz y el movimiento grabado queda acelerado. Hay que revisarlo antes de entrenar: si `observe` se come el presupuesto, el cuello de botella son las cámaras.
- **Varias tareas (para SmolVLA multitarea)**: `single_task` es una por sesión. Propuesta: un dataset por tarea y fusionarlos después (3.7). La alternativa es reanudar con otra `single_task` **[NO VERIFICADO]**.

Consejos de grabación de la doc (il_robots y smolvla):
- Empezar con una tarea sencilla: coger el objeto en distintas posiciones y dejarlo en un recipiente.
- **Al menos 50 episodios, 10 por posición.** En el paper de SmolVLA usaron 50 episodios con 5 posiciones del cubo; con 25 episodios el resultado fue malo.
- Cámaras fijas y forma de agarrar consistente. El objeto debe verse siempre.
- Regla práctica: tienes que poder hacer la tarea tú mismo mirando solo las imágenes de las cámaras.
- Añadir variación (posiciones nuevas, otra forma de agarrar) solo cuando el agarre básico funcione. Mucha variación de golpe empeora el resultado.

### 3.7 Subida al Hub, fusión y edición [doc]
- La subida es automática al final de la grabación. Para subir a mano: `hf upload ${HF_USER}/<repo_con_sello> ~/.cache/huggingface/lerobot/${HF_USER}/<repo_con_sello> --repo-type dataset`.
- Para grabar sin subir: `--dataset.push_to_hub=false`. Etiquetas: `--dataset.tags='["robotalde"]'`. Privado: `--dataset.private=true` **[código]**.
- Si se crea el dataset desde Python, hay que llamar a `dataset.finalize()` **antes** de `push_to_hub()`. Sin eso, los parquet quedan incompletos y el dataset no carga.
- Fusionar tandas o tareas (deben tener las mismas *features*: mismas cámaras, resoluciones y fps):
```bash
lerobot-edit-dataset --new_repo_id ${HF_USER}/robotalde_multitarea \
  --operation.type merge \
  --operation.repo_ids "['${HF_USER}/robotalde_tarea1_...', '${HF_USER}/robotalde_tarea2_...']" \
  --push_to_hub true
```
- Borrar episodios malos: `--operation.type delete_episodes --operation.episode_indices "[0, 2, 5]"` (con `--new_repo_id` se conserva el original).
- Cambiar las tareas: `--operation.type modify_tasks` con `new_task`, `episode_tasks` o `task_replacements`.
- Al entrenar, también se puede excluir episodios sin editar nada: `--dataset.exclude_episodes="[3,7]"` **[código]**.

### 3.8 Visualización [doc]
- En el navegador: `https://huggingface.co/spaces/lerobot/visualize_dataset?path=/${HF_USER}/<repo_con_sello>/episode_0` (para un dataset privado, hay que iniciar sesión).
- En local, con Rerun: `lerobot-dataset-viz --repo-id ${HF_USER}/<repo> --episode-index 0`. Desde una carpeta: añadir `--root <carpeta> --mode local`.
- Reproducir un episodio en el robot: `lerobot-replay --robot.type=so101_follower --robot.port=COM3 --robot.id=seguidor_robotalde --dataset.repo_id=${HF_USER}/<repo> --dataset.episode=0`.

### 3.9 Entrenamiento de ACT [doc: il_robots, act, hardware_guide]
```bash
lerobot-train \
  --dataset.repo_id=${HF_USER}/robotalde_tarea1_YYYYMMDD_HHMMSS \
  --policy.type=act \
  --output_dir=outputs/train/act_robotalde --job_name=act_robotalde \
  --policy.device=cuda --trackio.enable=true \
  --policy.repo_id=${HF_USER}/act_robotalde \
  --steps=20000
```
- Sin `--steps` se hacen 100 000 pasos. La doc dice que suele bastar con 5-10 épocas: `pasos ≈ épocas × frames_totales / batch_size`. Ejemplo: 50 ep × 30 s × 30 fps ≈ 45 000 frames; con batch 8, 5 épocas son unos 28 000 pasos.
- Si se acortan los pasos, ajustar también `--policy.scheduler_decay_steps` (≈ `--steps`) y `--save_freq`.
- ACT tiene unos 80 M de parámetros y necesita unos 2-6 GB de VRAM con batch 8. **Cabe en la GTX 1660 de 6 GB, justo** **[NO VERIFICADO en esa GPU]**. En una L4, 5 épocas de 50 episodios tardan unas 1-2 h.
- Reanudar: `lerobot-train --config_path=outputs/train/act_robotalde/checkpoints/last/pretrained_model/train_config.json --resume=true`.
- Para que el modelo sea privado: `--policy.private=true`. Para no subirlo: `--policy.push_to_hub=false`.

### 3.10 Entrenamiento de SmolVLA (ajuste fino de `smolvla_base`) [doc: smolvla.mdx, rename_map.mdx]
```bash
lerobot-train \
  --policy.path=lerobot/smolvla_base \
  --dataset.repo_id=${HF_USER}/robotalde_multitarea \
  --policy.repo_id=${HF_USER}/smolvla_robotalde \
  --rename_map='{"observation.images.top": "observation.images.camera1", "observation.images.wrist": "observation.images.camera2"}' \
  --batch_size=64 --steps=20000 \
  --output_dir=outputs/train/smolvla_robotalde --job_name=smolvla_robotalde \
  --policy.device=cuda --trackio.enable=true
```
- `--policy.path` hace ajuste fino de un modelo existente. `--policy.type` entrenaría desde cero.
- **`--rename_map` es obligatorio**: `smolvla_base` espera las cámaras `camera1`, `camera2` y `camera3`. Sin él, el entrenamiento se para con un error de *feature mismatch*. Solo renombra observaciones, nunca acciones.
- Si hay menos cámaras que las que espera la política, existe `--policy.empty_cameras=N`. El ejemplo oficial usa solo 2 cámaras sin esa opción.
- Referencias: 20 000 pasos son unas 4 h en una A100. En una L4 o A10G, unas 3-6 h con batch 4 para 5 épocas de 50 episodios. SmolVLA necesita unos 10-16 GB de VRAM con batch 8: **no cabe en la GTX 1660, así que hay que entrenar en la nube**.
- Si falta memoria: bajar `--batch_size` y dejar `freeze_vision_encoder=True` (valor por defecto, igual que `train_expert_only=True`) **[doc y código]**.
- `chunk_size=50` y `n_action_steps=50` por defecto **[código]**.

### 3.11 Entrenamiento en la nube con HF Jobs [doc]
Basta con añadir `--job.target=<tipo>` a cualquier `lerobot-train`:
```bash
lerobot-train --policy.path=lerobot/smolvla_base --dataset.repo_id=${HF_USER}/robotalde_multitarea \
  --policy.repo_id=${HF_USER}/smolvla_robotalde --rename_map='{...}' --steps=20000 --batch_size=32 \
  --job.target=l4x1 --job.timeout=8h --save_checkpoint_to_hub=true \
  --trackio.enable=true --trackio.space_id=${HF_USER}/robotalde-trackio
```
- Tipos de máquina: `t4-small` y `t4-medium` (solo ACT), `l4x1` y `l4x4` (L4 de 24 GB), `a10g-small/large/largex2/largex4`, `a100-large`. El catálogo actual se consulta con `hf jobs hardware`.
- Los logs se emiten en directo. Con Ctrl-C se suelta el terminal, pero el job sigue corriendo. `hf jobs logs <id>` vuelve a mostrarlos y `hf jobs cancel <id>` lo cancela.
- Un dataset que solo existe en local se sube a un repo **privado** automáticamente. El modelo se sube al final del entrenamiento. `--save_checkpoint_to_hub=true` sube además cada checkpoint, etiquetado con su paso (por ejemplo `010000`).
- El tiempo máximo por defecto es `2d`. Sin `--trackio.space_id`, las métricas se pierden al acabar el job.
- Reanudar en la nube: `lerobot-train --config_path=${HF_USER}/smolvla_robotalde --resume=true --job.target=l4x1`.
- Si el job falla, el repo del modelo queda creado y vacío. Se borra con `hf repos delete <repo>`.
- La imagen por defecto es `huggingface/lerobot-gpu:latest` (`--job.image`) **[código]**. Ver la sección 7.

### 3.12 Evaluación en el robot: `lerobot-rollout` [doc: il_robots, inference, smolvla]
```bash
lerobot-rollout --strategy.type=base \
  --policy.path=${HF_USER}/smolvla_robotalde \
  --robot.type=so101_follower --robot.port=COM3 --robot.id=seguidor_robotalde \
  --robot.cameras="{ top: {...igual que al grabar...}, wrist: {...} }" \
  --rename_map='{"observation.images.top": "observation.images.camera1", "observation.images.wrist": "observation.images.camera2"}' \
  --task="Pick the red cube and place it in the box" --duration=60 --display_data=true
```
- Hay que usar el mismo `--robot.id`, las mismas cámaras, la misma `--task` que al grabar y el mismo `--rename_map` que al entrenar.
- Estrategias:
  - `base`: sin grabar.
  - `sentry`: graba siempre y sube cada N episodios.
  - `highlight`: guarda lo interesante al pulsar una tecla.
  - `dagger`: un humano corrige mientras se graba.
  - `episodic`: como `lerobot-record`, pero conduce la política. La guía es opcional para recolocar la escena.
- Los datasets de rollout deben empezar por `rollout_`.
- Para medir la tasa de éxito: `--strategy.type=episodic --dataset.repo_id=${HF_USER}/rollout_eval --dataset.num_episodes=20 --dataset.episode_time_s=30 --dataset.reset_time_s=10 --dataset.single_task="..."`.
- `--interactive=true`: el robot no se mueve hasta escribir `/start`. Con `/subtask <texto>` se cambia la instrucción (útil para demostrar SmolVLA multitarea en vivo), `/reset` vuelve a la posición inicial y `/stop` termina.
- `--device=cpu|cuda` fuerza el dispositivo. Para cargar un checkpoint concreto: `--policy.pretrained_revision=010000`.
- Para ACT, la `--task` se puede omitir.
- **RTC local** (movimiento más suave con modelos lentos como SmolVLA): `--inference.type=rtc --inference.rtc.execution_horizon=10 --inference.rtc.max_guidance_weight=10.0`.
- Antes de 0.6, este comando no existía y se usaba `lerobot-record` con `--policy.path` (la chuleta lo dice para la v0.5.x).

### 3.13 Inferencia remota o asíncrona (servidor de políticas) [doc: remote_inference.mdx]
**Ha cambiado en 0.7**: ya no existe `lerobot.async_inference` (el antiguo `policy_server` + `robot_client` con gRPC).
Ahora hay un **servidor de políticas con Zenoh** (`lerobot-policy-server`) y el cliente es el propio `lerobot-rollout`
con `--inference.type=remote`. ACT necesita desactivar el *temporal ensembling*. ACT y SmolVLA ya se han probado en
robots reales por esta vía. El seguidor SO declara soporte de mantener posición.
```bash
# en los dos equipos (extra 'remote'; con pip sería 'lerobot[remote]' [NO VERIFICADO con pip])
uv sync --locked --extra remote --extra core_scripts --extra feetech
# servidor (GPU): copiar y editar examples/remote_inference/server.yaml
#   model.repo_or_path, model.device, features (con los nombres de cámara que espera el checkpoint), action_fps
lerobot-policy-server --config_path=server.yaml --zenoh.listen_endpoints='[tcp/IP_DEL_SERVIDOR:7447]'
# cliente (portátil con el robot)
lerobot-rollout --inference.type=remote --inference.endpoint=tcp/IP_DEL_SERVIDOR:7447 \
  --inference.deployment=manipulation --inference.mode=chunk --inference.chunk_merge=aligned \
  --inference.semantics=so101-degrees-gripper-percent-v1 \
  --robot.type=so101_follower --robot.port=COM3 --robot.use_degrees=true \
  --robot.cameras='{...}' --fps=30 --task="..." --interactive=true
```
- Al cliente no se le pasa `--policy.path`. Para renombrar cámaras en el cliente: `--rename_map`.
- Ajustes principales:
  - `refill_seconds` (0.5): cuándo se pide el siguiente trozo de acciones.
  - `blend_steps` (0): suavizado entre trozos.
  - `--inference.encoding=jpeg --inference.jpeg_quality=90`: reduce el ancho de banda.
- Si se pierde la conexión con el servidor, **no se recupera sola**: hay que reiniciar el rollout.
- El TCP sin TLS no autentica a nadie. En la red del evento, mejor usar el router con TLS o una LAN de confianza.
- Para nuestro caso, la alternativa más sencilla con la GTX 1660 es el RTC local (3.12) si SmolVLA cabe en la GPU **[NO VERIFICADO]**. Si no cabe, el servidor puede ir en otra máquina con GPU de la red.

---

## 4. Grabar sin teleoperar (recolector programado)

### 4.1 APIs que intervienen [doc y código v0.7.0]
- Robot: `from lerobot.robots.so_follower import SO101Follower, SO101FollowerConfig`. Métodos: `connect()`, `get_observation()` (posiciones `"<motor>.pos"` e imágenes con el nombre de cada cámara) y `send_action(dict)`, que devuelve la acción que se envió de verdad (puede ir recortada por `max_relative_target`). Después `disconnect()`.
- Unidades (`use_degrees=True`, el valor por defecto): las 5 articulaciones en **grados** y la pinza en **0..100** **[código]**.
- Dataset: `LeRobotDataset.create(repo_id, fps, features=..., robot_type=..., use_videos=True, root=...)`, después `add_frame({...obs, ...action, "task": str})` por cada frame y `save_episode()` por cada episodio. Para terminar, `finalize()` y `push_to_hub()`.
- Para continuar un dataset existente: `LeRobotDataset.resume(repo_id, root=...)`. Para descartar el episodio en curso: `clear_episode_buffer()`.
- Utilidades: `hw_to_dataset_features(robot.action_features, "action")` y `hw_to_dataset_features(robot.observation_features, "observation")` en `lerobot.utils.feature_utils` **[doc]**; `build_dataset_frame(dataset.features, valores, prefix="action" | "observation")` **[código: ejemplo OMX]**; `precise_sleep` en `lerobot.utils.robot_utils`.
- **La `task` va en cada frame**, así que un mismo dataset puede tener episodios de tareas distintas, que es lo que necesita el multitarea **[código: ejemplo OMX]**.
- Ejemplo oficial de recolección automática **sin guía**: `examples/omx/record_grab.py`. Interpola con *splines* entre poses articulares, añade *jitter* aleatorio y episodios de "recuperación" que empiezan en poses de agarre fallido. En cada paso hace `send_action`, luego `get_observation`, luego `add_frame` y luego `precise_sleep(1/fps)`. Usa `VideoEncodingManager(dataset)` y, en un `finally`, llama a `finalize()`.

### 4.2 Esqueleto mínimo (adaptado del ejemplo de replay de la doc y de `record_grab.py`)
```python
import numpy as np
from lerobot.cameras.opencv import OpenCVCameraConfig
from lerobot.datasets import LeRobotDataset, VideoEncodingManager
from lerobot.robots.so_follower import SO101Follower, SO101FollowerConfig
from lerobot.utils.feature_utils import build_dataset_frame, hw_to_dataset_features
from lerobot.utils.robot_utils import precise_sleep

FPS = 30
camaras = {
    "top": OpenCVCameraConfig(index_or_path=0, width=640, height=480, fps=FPS),
    "wrist": OpenCVCameraConfig(index_or_path=1, width=640, height=480, fps=FPS),
}
robot = SO101Follower(SO101FollowerConfig(port="COM3", id="seguidor_robotalde", cameras=camaras,
                                          max_relative_target=10.0))  # limita el salto por orden (grados)
features = {**hw_to_dataset_features(robot.action_features, "action"),
            **hw_to_dataset_features(robot.observation_features, "observation")}
dataset = LeRobotDataset.create("usuario/robotalde_programado", FPS, features=features,
                                robot_type=robot.name, use_videos=True)
robot.connect()
try:
    with VideoEncodingManager(dataset):
        for pasos, tarea in mis_trayectorias():          # lista de poses articulares (dict) + texto de la tarea
            for accion in pasos:                          # ya interpoladas a 30 Hz
                enviada = robot.send_action(accion)
                obs = robot.get_observation()
                dataset.add_frame({**build_dataset_frame(dataset.features, obs, prefix="observation"),
                                   **build_dataset_frame(dataset.features, enviada, prefix="action"),
                                   "task": tarea})
                precise_sleep(1 / FPS)                    # mejor: descontar el tiempo de trabajo, como en replay
            dataset.save_episode()
finally:
    dataset.finalize()
    robot.disconnect()
dataset.push_to_hub()
```
**[NO VERIFICADO tal cual: está montado con piezas verificadas, pero hay que probarlo con el robot]**.

Aviso: `lerobot-record` (`record_loop`) lee la observación **antes** de mandar la acción, y el ejemplo OMX lo hace
**después**. Hay que decidir un orden y mantenerlo en todo el dataset. Si se va a mezclar con datos teleoperados,
conviene imitar `record_loop`: observar, calcular la acción, enviarla y grabar **[NO VERIFICADO: criterio nuestro]**.

### 4.3 Cinemática inversa [código y comentarios de ejemplos]
- `from lerobot.model.kinematics import RobotKinematics` (necesita el extra `kinematics`, que instala `placo`).
- `RobotKinematics(urdf_path="SO101/so101_new_calib.urdf", target_frame_name="gripper_frame_link", joint_names=list(robot.bus.motors.keys()))`.
- `forward_kinematics(q_grados)` devuelve una matriz 4×4. `inverse_kinematics(q_actual_grados, T_deseada_4x4, position_weight=1.0, orientation_weight=0.01, max_iters=8)` devuelve los grados y conserva la pinza.
- La doc recomienda el URDF `so101_new_calib.urdf` del repositorio SO-ARM100.
- En `examples/so100_to_so100_EE/` también hay *processors* listos (`ForwardKinematicsJointsToEE`, `InverseKinematicsEEToJoints`).
- `lerobot-find-joint-limits` (con la guía y el URDF) mide los límites articulares y del efector final teleoperando durante unos segundos: sirve para acotar el espacio de trabajo del recolector.
- Las ruedas de `placo` para Windows **[NO VERIFICADO]**: comprobar `pip install 'lerobot[kinematics]'` en el portátil cuanto antes. Si no instala, usar WSL o una IK analítica propia.

---

## 5. Seguridad del hardware

**Lo que hace LeRobot 0.7 por defecto [código]**
- Al conectar: modo posición, PID P=16, I=0, D=32. En la **pinza**: `Max_Torque_Limit=500` (50 %), `Protection_Current=250` (50 %) y `Overload_Torque=25`, todo "para evitar que se queme".
- `disable_torque_on_disconnect=True`: al desconectar se libera el par y **el brazo cae**. Antes de cerrar un script hay que dejarlo en reposo o sujetarlo.
- `max_relative_target` (desactivado por defecto) limita cuánto puede alejarse cada orden de la posición actual: es la red de seguridad del recolector programado y de las primeras pruebas de una política. Con un número vale el mismo límite para todos los motores; con un diccionario se fija por motor. Cuesta algo de frecuencia, porque lee la posición en cada orden. Desde la línea de comandos: `--robot.max_relative_target=5.0` (sintaxis de la doc de otro brazo; aplicable al SO **[código]**).
- `num_read_retries=2`: reintenta las lecturas fallidas por "Incorrect status packet!", que es frecuente cuando se mueven varias articulaciones a la vez.

**Leer temperatura, carga, corriente y tensión [código: `rustypot` tiene `present_temperature`, `present_load`, `present_current` y `present_voltage` para el STS3215. El bus acepta el nombre del registro sin distinguir mayúsculas]**
```python
temps = robot.bus.sync_read("Present_Temperature")   # {motor: °C}
carga = robot.bus.sync_read("Present_Load")
volt  = robot.bus.sync_read("Present_Voltage")
```
**[NO VERIFICADO en el robot]**: las unidades exactas (la tensión suele venir en décimas de voltio) y el límite de
temperatura de fábrica (registro `temperature_limit`) hay que comprobarlos el viernes. Propuesta: el recolector
debería imprimir la temperatura cada N episodios y pararse si pasa de un umbral (unos 60 °C) **[NO VERIFICADO]**.

**Buenas prácticas** (las que salen de la doc más nuestro criterio):
- Comprobar todos los cables (alimentación, USB y 3 pines) antes de cada Enter en `setup-motors`; la fuente puede soltarse al manipular la placa **[doc]**.
- No forzar la pinza contra objetos rígidos durante mucho rato: es el motor que más se calienta, y por eso LeRobot le limita el par.
- Hacer pausas entre tandas de grabación si los motores están calientes al tacto.
- El primer rollout de cada política, con `--duration` corto y una mano cerca del interruptor de la fuente.
- **Si un motor falla**:
  1. Revisar la cadena de cables (un 3 pines suelto deja sin comunicación a todos los motores que hay detrás).
  2. Volver a lanzar `lerobot-setup-motors` solo con ese motor, porque un motor de repuesto viene con id 1.
  3. Recalibrar con el mismo `id`.
  4. Comprobar el firmware con el software Feetech FD (solo Windows): *Search* para ver los IDs, *Upgrade* > *Online* > *Upgrade*. **No cortar la corriente durante la actualización**, porque puede inutilizar el motor **[doc]**. En Linux o macOS existe `FT_SCServo_Debug_Qt` para diagnóstico, pero no para firmware.

---

## 6. Problemas típicos y soluciones (de la doc)

| Síntoma | Solución |
|---|---|
| Error al fijar el ID de un motor | Revisar la fuente, el USB y el cable de 3 pines. En una placa Waveshare, jumpers en `B` (USB) |
| Sin permiso para abrir el puerto (Linux) | `sudo chmod 666 /dev/ttyACM0` |
| Pide calibrar otra vez | Se ha usado otro `--robot.id` o `--teleop.id`. Usar siempre el mismo |
| "Mismatch between calibration values" al conectar | Los valores del motor no coinciden con el archivo: recalibrar **[código]** |
| Las teclas no hacen nada al grabar | Terminal interactivo y con el foco. Usar `n`, `r` y `q` |
| La política falla con un error de *features* | Los nombres o resoluciones de las cámaras no coinciden. Usar `--rename_map` (SmolVLA: `camera1`, `camera2`, `camera3`) |
| No encuentra el dataset recién grabado | Falta el sello `_YYYYMMDD_HHMMSS` en el nombre. Mirar `ls ~/.cache/huggingface/lerobot/$HF_USER` |
| `--resume` en la grabación no funciona | Pasar el nombre con sello, `--dataset.root` y `num_episodes` = episodios **adicionales** |
| El dataset no carga tras crearlo desde Python | Faltó `dataset.finalize()` antes de `push_to_hub()` |
| Faltan frames, frecuencia < 30 Hz | La CPU va saturada o las cámaras son lentas: bajar la resolución, usar `--dataset.streaming_encoding=true` y `--dataset.encoder_threads`, o un códec por GPU (`--dataset.rgb_encoder.vcodec=h264_nvenc`, NVIDIA en Linux o Windows). Hasta un 2 % de frames perdidos es normal |
| `libsvtav1` no aparece en `ffmpeg -encoders` | `conda install ffmpeg=7.1.1 -c conda-forge` |
| La cámara virtual OBS da una resolución incorrecta | Borrar y volver a crear la fuente a 640×480 |
| El LR no baja con pocos pasos | Poner `--policy.scheduler_decay_steps` ≈ `--steps` |
| Falta VRAM | Bajar el batch. SmolVLA: dejar el codificador de visión congelado. Si no, entrenar en HF Jobs |
| Movimiento a tirones con SmolVLA | `--inference.type=rtc`, o inferencia remota en otra GPU |
| Inferencia remota: `BUSY` al reconectar | Esperar a que el servidor libere al cliente anterior (`idle_timeout_s`) |

---

## 7. Diferencias y dudas respecto a LeRobot 0.7

1. **Versión de la doc**: todo lo anterior sale de la etiqueta `v0.7.0`. `main` (0.7.1-dev, 18-11-2026) no cambia las páginas usadas. Las guías de internet anteriores a 2026 suelen usar otros comandos.
2. **Comandos que han cambiado entre versiones**:
   - `lerobot-rollout` sustituye a `lerobot-record --policy.path=...` para evaluar (existe desde la 0.6; en la 0.5.x no).
   - En 0.7 ya no está `python -m lerobot.async_inference.policy_server/robot_client`: se usa `lerobot-policy-server` con Zenoh y `lerobot-rollout --inference.type=remote`.
   - `lerobot-dataset-viz` sustituye a `visualize_dataset.py`.
   - `hf auth login` sustituye a `huggingface-cli login`.
   - Las métricas van con `--trackio.enable` (antes, `--wandb.enable`).
3. **Sello de tiempo en `repo_id`**: es nuevo y se olvida con facilidad. Hay que apuntar el nombre completo de cada tanda o usar `--dataset.no_stamp=true`.
4. **Motores con `rustypot`**: en 0.7 el bus es `SerialMotorsBus` sobre `rustypot`. El antiguo `FeetechMotorsBus` sigue existiendo como subclase. Los ejemplos de internet que importan `scservo_sdk` o `lerobot.common.*` están desfasados.
5. **Error en la doc de v0.7.0**: el ejemplo de grabación por API importa `init_keyboard_listener` de `lerobot.common.control_utils`, pero en 0.7.0 esa función está en `lerobot.utils.keyboard_input` **[código]**.
6. **PyTorch en Windows**: la doc dice que Windows "usa las ruedas por defecto de PyPI". En Windows suelen ser solo CPU. Hay que comprobar `torch.cuda.is_available()`, y si da `False`, instalar torch desde el índice de pytorch.org con CUDA. La GTX 1660 es Turing (sm_75) **[NO VERIFICADO]**. No hay instrucciones oficiales de Windows nativo para LeRobot. Solo se menciona WSL (instalar `evdev`).
7. **Imagen de HF Jobs**: por defecto es `huggingface/lerobot-gpu:latest`, que puede llevar una versión más nueva que nuestra 0.7.0 local. Si aparecen incompatibilidades (formato de checkpoint, flags), fijar `--job.image` a una etiqueta concreta **[NO VERIFICADO: no sabemos qué etiquetas existen]**.
8. **Varios datasets en `lerobot-train`**: el comentario del código dice que se puede pasar una lista, pero `repo_id` está tipado como `str`. Lo seguro es fusionar con `lerobot-edit-dataset` **[NO VERIFICADO pasar una lista]**.
9. **SmolVLA con 2 cámaras**: el ejemplo oficial renombra 2 cámaras sin `empty_cameras`. Si se queja de `camera3`, probar `--policy.empty_cameras=1`.
10. **Extra `remote` con pip**: la doc solo da la orden con `uv sync --locked --extra remote`. `pip install 'lerobot[remote]'` debería valer, porque el extra existe en `pyproject` **[código]**.
11. **Curso de robótica**: en noviembre de 2026 solo tiene publicadas las unidades 0-2 (introducción, LeRobotDataset y robótica clásica). Lo práctico es cargar datasets con `LeRobotDataset("lerobot/svla_so101_pickplace", delta_timestamps=...)` y `StreamingLeRobotDataset` (importados de `lerobot.datasets...`, que siguen existiendo en 0.7.0). Las unidades de aprendizaje por imitación y modelos fundacionales aún no están publicadas.
