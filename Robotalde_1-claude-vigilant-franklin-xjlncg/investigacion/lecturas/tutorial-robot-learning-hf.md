# Robot Learning: A Tutorial (Capuano y otros, 2025) · notas de lectura

> Lectura completa de la versión HTML de arXiv (v1). Las referencias entre corchetes, como [§4.2], apuntan a la
> sección del tutorial de donde sale cada dato. Lo que es deducción nuestra va marcado como **(inferencia)**.

## 1. Ficha

| Campo | Valor |
|---|---|
| Título | *Robot Learning: A Tutorial* |
| Autores | Francesco Capuano, Caroline Pascal, Adil Zouitine, Thomas Wolf, Michel Aractingi |
| Fecha | Enviado a arXiv el 14 oct 2025 (v1, cs.RO). Era la única versión cuando lo leímos (18 nov 2026). |
| arXiv | https://arxiv.org/abs/2510.12403 · HTML: https://arxiv.org/html/2510.12403 |
| Página del proyecto | https://huggingface.co/spaces/lerobot/robot-learning-tutorial (no hemos podido leer su contenido, ver §7) |
| Código de los ejemplos | https://github.com/fracapuano/robot-learning-tutorial (carpeta `snippets/chN/`) |
| Biblioteca | https://github.com/huggingface/lerobot |
| Licencia del texto | CC BY-NC-SA 4.0 (en la página de arXiv y en el README del repositorio) |
| Licencia del código | El README dice que los ejemplos de `snippets/` son MIT; el archivo `LICENSE` del repositorio, en cambio, es CC BY-NC-ND 4.0 (ver §7). |

Estructura: 1 Introducción y LeRobotDataset · 2 Robótica clásica · 3 Aprendizaje por refuerzo (RL) · 4 Aprendizaje
por imitación (modelos generativos, ACT, Diffusion Policy, inferencia optimizada) · 5 Políticas generalistas (VLA, π0,
SmolVLA) · 6 Conclusiones. Cada capítulo trae ejemplos de código con `lerobot` (14 en total).

## 2. Resumen en 10 líneas

1. La robótica está pasando de modelos físicos hechos a mano a políticas aprendidas de datos, y `lerobot` es la
   biblioteca de Hugging Face para todo el proceso: hardware, datasets, entrenamiento e inferencia.
2. LeRobotDataset guarda tablas en parquet, vídeo en MP4 y metadatos en JSON, y permite *streaming* desde el Hub.
3. Los métodos clásicos (cinemática, IK, control) son frágiles en entornos cambiantes y no aprovechan los datos.
4. El RL aprende por ensayo y error, pero en un robot real cuesta caro: exploración peligrosa, reinicios manuales y
   recompensas difíciles de diseñar. HIL-SERL lo hace viable metiendo correcciones humanas durante el entrenamiento.
5. El aprendizaje por imitación (*behavioral cloning*, BC) aprende de demostraciones sin recompensa, pero una regresión
   simple sufre errores que se acumulan y promedia estrategias distintas.
6. Por eso las políticas modernas son modelos generativos (CVAE, difusión, *flow matching*) que predicen trozos de
   varias acciones de golpe (*action chunking*).
7. ACT (CVAE + transformer) y Diffusion Policy son políticas de una sola tarea que aprenden con decenas o pocos cientos
   de demostraciones.
8. La inferencia asíncrona separa el cálculo del trozo de acciones de su ejecución, y puede llevar la política a otra
   máquina con GPU.
9. Los VLA (π0, SmolVLA) parten de un modelo de visión y lenguaje preentrenado más un "experto de acción" entrenado con
   *flow matching*, y siguen órdenes en lenguaje natural para varias tareas.
10. SmolVLA (unos 450 M de parámetros) es la versión abierta y pequeña, preentrenada con datasets de la comunidad
    grabados con brazos SO-100/SO-101.

## 3. Conceptos clave (para alguien de software sin experiencia en robótica)

### 3.1 Política, observación y acción [§3.1, §4]
- **Política**: la función que, en cada instante, recibe lo que el robot "ve" y "siente" y devuelve qué hacer. En
  notación, π(a|o).
- **Observación** `o`: imágenes de las cámaras más el estado propioceptivo (las posiciones de las articulaciones del
  brazo; en el SO-100 son 6 grados de libertad, la pinza incluida) [§2.3, §4].
- **Acción** `a`: la orden que se manda al robot, normalmente una configuración de articulaciones objetivo. Cuando se
  teleopera con guía y seguidor, la acción grabada es la posición del brazo guía que mueve la persona [§4, fig. 19].
- **Episodio / trayectoria**: una demostración completa, una secuencia de pares (observación, acción). En BC no hay
  recompensa: solo se imita [§4].

### 3.2 Behavioral cloning y sus dos problemas [§4]
- En su forma más simple, BC es aprendizaje supervisado: dada `o`, predecir la `a` del experto.
- **Error acumulado (covariate shift)**: un pequeño error lleva al robot a un estado que no aparece en los datos, ahí la
  política se equivoca más, y así hasta fallar.
- **Multimodalidad**: si en las demostraciones el objeto se rodea a veces por la izquierda y a veces por la derecha, un
  regresor simple promedia y sale una acción indecisa o peligrosa (por el medio). La solución es aprender una
  **distribución** de acciones (un modelo generativo) en vez de una única acción.
- Las muestras no son independientes (vienen en trayectorias); barajar los fotogramas lo mitiga en parte. El tutorial
  menciona DAgger (alternar entrenamiento y nueva recogida de datos), pero lo deja fuera de su alcance.
- Ventajas de BC: entrenamiento offline sin riesgo para el robot, sin diseño de recompensa, y el criterio de éxito y el
  reinicio vienen implícitos en los datos. Límite: como mucho iguala al demostrador.

### 3.3 Action chunking (trozos de acciones) [§4.2, §4.4]
- En vez de predecir una sola acción por paso, la política predice un **trozo** de H_a acciones futuras a partir de una
  sola observación. Es como planear "los próximos dos segundos" en lugar de "el próximo milisegundo".
- Reduce el error acumulado y ayuda a "comprometerse" con una de las estrategias posibles. En el ablation de ACT:
  **1 % de éxito sin chunking frente a 44 % con chunking** [§4.2].
- ACT original vuelve a inferir en cada paso y mezcla los trozos solapados con una media móvil exponencial
  (*temporal ensembling*) para no actuar a ciegas durante todo el trozo [§4.2].

### 3.4 ACT y su CVAE [§4.1.1, §4.2]
- **VAE**: un codificador comprime el ejemplo en una variable latente `z` y un decodificador lo reconstruye. Se entrena
  con dos términos: error de reconstrucción + regularización (KL) que obliga a `z` a parecerse a una gaussiana estándar.
- **CVAE** (VAE condicional): modela p(acciones | observación) en lugar de la distribución conjunta. ACT es un
  **β-CVAE**: el peso β de la KL regula cuánta información cabe en `z`.
- Intuición de `z`: el "estilo" de la demostración (qué variante de la estrategia usó la persona).
- **En entrenamiento** el codificador del CVAE recibe el trozo de acciones real y el estado propioceptivo (sin
  imágenes, por eficiencia) y produce `z`. **En inferencia el codificador se tira**: se usa `z = 0` y el decodificador
  (un transformer codificador-decodificador que recibe las imágenes de todas las cámaras, pasadas por codificadores
  visuales preentrenados, y el estado) genera el trozo de acciones [§4.2, fig. 28-30].
- Dato muy relevante para nosotros: los autores de ACT vieron que **con demostraciones programadas (scripted) una
  regresión L1 simple rinde igual que el CVAE**; con demostraciones humanas, la regresión simple pierde **un 33,3 %** de
  éxito. La razón es que los datos humanos son multimodales y los programados no [§4.2].

### 3.5 Difusión y flow matching [§4.1.2, §4.1.3, §4.3]
- **Difusión**: en entrenamiento se ensucia el trozo de acciones con ruido gaussiano y la red aprende a predecir ese
  ruido. En inferencia se parte de ruido puro y se va limpiando paso a paso, condicionado a la observación.
- **Diffusion Policy** [§4.3]: condiciona en las últimas H_o observaciones y predice H_a acciones; usa una U-Net
  (o un transformer, mejor pero más sensible a hiperparámetros; los autores recomiendan empezar por la U-Net). Con DDIM
  bastan unos 10 pasos de limpieza (10 veces menos que DDPM).
- **Flow matching**: generalización continua y determinista de la difusión. Aprende un campo de velocidades que lleva
  ruido a datos por caminos casi rectos; se entrena con una regresión sencilla y en inferencia se integra con unos
  pocos pasos de Euler (decenas, o 10 en π0 y SmolVLA). Necesita menos cálculo en inferencia que la difusión
  clásica [§4.1.3, §5.3].

### 3.6 VLA: cómo entra el lenguaje [§5.2, §5.3, §5.4]
- Un **VLM** (modelo de visión y lenguaje) es un codificador de imágenes preentrenado unido a un LLM preentrenado. Ya
  "sabe" qué es un objeto, un color o una posición relativa gracias al preentrenamiento con internet.
- Un **VLA moderno** = VLM (procesa imágenes + instrucción de texto) + **experto de acción** (procesa el estado del
  robot y el trozo de acciones ruidoso y lo limpia con flow matching). Los dos comparten un único transformer con
  pesos separados y se comunican por atención. No hay tokens de acción discretos: las acciones son continuas [§5.2].
- Así la orden en lenguaje ("pon la chapa en T") condiciona la generación de acciones a través de la atención, y una
  sola política puede hacer varias tareas.
- Precedentes: RT-1/RT-2 y OpenVLA discretizaban cada articulación en 256 niveles y trataban las acciones como tokens
  de texto [§5.1].

### 3.7 π0 [§5.3]
- VLM PaliGemma (Gemma de 2,6 B) + experto de acción de 300 M, entrenado desde cero; 3,3 B parámetros en total.
- Máscara de atención por bloques: imagen+texto no ven el estado ni las acciones (para no "contaminar" al VLM con
  datos fuera de su distribución); esto permite cachear claves y valores entre pasos de limpieza.
- Muestrea el tiempo del flow con una Beta(1,5; 1) que favorece los niveles con más ruido.
- Preentrenado con más de 10 M de trayectorias (solo un 9,1 % abiertas), 7 configuraciones de robot y 68 tareas.
- Usa exactamente 3 vistas de cámara (con huecos enmascarados si hay menos) y rellena con ceros las acciones de
  robots con menos grados de libertad.

### 3.8 SmolVLA [§5.4]
- VLM SmolVLM-2 (codificador visual SigLIP + decodificador SmolLM2) + experto de acción de ~100 M. **Unos 450 M de
  parámetros en total**.
- Trucos de eficiencia: 64 tokens visuales por fotograma (*pixel shuffle*, sin teselado), solo usa la primera mitad
  de las capas del VLM (N = L/2), el experto tiene una dimensión del 75 % de la del VLM y alterna capas de
  autoatención y atención cruzada (dan más éxito y trozos más suaves).
- Preentrenado **solo con datos de la comunidad**: más de 450 datasets, más de 20 000 trayectorias, en brazos
  accesibles como SO-100/SO-101. Reetiquetaron las instrucciones con un VLM pequeño porque estaban vacías o eran
  ruidosas, y normalizaron las cámaras a un orden fijo top/wrist/side.
- En inferencia, 10 pasos de flow. Según el tutorial (que cita el artículo de SmolVLA), rinde parecido a π0 siendo
  ~40 % más rápido y gastando 6 veces menos memoria (en el pie de la fig. 39 dice 7 veces).

### 3.9 Preentrenamiento y ajuste fino [§5, §5.3]
- El paradigma es "preentrenar y adaptar": un modelo base general se ajusta con pocos datos de la tarea concreta.
- π0 preentrenado + ajuste fino supera a π0 entrenado desde cero en la tarea. La intuición de los autores: las
  demostraciones "de alta calidad" casi no contienen fallos, así que una política entrenada solo con ellas no sabe
  recuperarse; los datos masivos y diversos aportan esa capacidad de recuperación.
- Matiz citado: entrenar todo el VLM con los gradientes de BC (como hace π0) puede dañar su conocimiento; un trabajo
  posterior (Driess et al., 2025) muestra que aislarlo funciona mejor.

### 3.10 Inferencia síncrona y asíncrona [§4.4]
- **Síncrona**: se ejecuta el trozo entero y luego se calcula el siguiente; durante el cálculo el robot se queda
  quieto ("lag ciego").
- **Asíncrona**: un `RobotClient` (junto al robot) envía observaciones a un `PolicyServer` (que puede estar en otra
  máquina con GPU) y va consumiendo una cola de acciones. Cuando la cola baja de una fracción `g` del tamaño del
  trozo, manda una observación nueva; al llegar el trozo nuevo se mezcla con lo que queda en las partes solapadas.
- Filtro de similitud: si la observación nueva casi no difiere de la anterior en espacio articular, no se envía
  (salvo que la cola se haya vaciado).
- `g = 0` es el caso síncrono (robot parado esperando); `g = 1` es inferir en cada paso (como ACT, caro). Para no
  vaciar nunca la cola hace falta `g ≥ (latencia_media_de_inferencia / Δt) / H_a`, con Δt = 33 ms a 30 fps.
  **Ejemplo (inferencia nuestra, no del tutorial)**: con 200 ms de inferencia son ~6 ciclos; con H_a = 50, g ≥ 0,12.

### 3.11 RL (resumen corto) [§3]
- RL = aprender maximizando una recompensa por ensayo y error (MDP, funciones de valor, Q-learning, DDPG, SAC).
- Problemas en robots reales: exploración peligrosa, reinicios manuales, muchas muestras y recompensas difíciles de
  definir. La simulación con *domain randomization* ayuda pero exige modelar y deja un "salto a la realidad".
- **HIL-SERL** (en `lerobot`): SAC + datos previos (RLPD) + un clasificador de recompensa entrenado con imágenes de
  éxito y fracaso + intervenciones humanas durante el entrenamiento. Actor y aprendiz en procesos (o máquinas)
  separados. Cifra citada: más del 99 % de éxito en 1-2 horas de entrenamiento real [§3.2]. No es nuestro camino para
  el hackathon **(inferencia)**.

## 4. Datos y cifras prácticas

| Cifra | Contexto | Sección |
|---|---|---|
| Unos 80-100 it/s | Rendimiento del streaming de datasets desde el Hub (depende de la conexión) | §1.2 |
| 6 grados de libertad | SO-100 (5 articulaciones + pinza) | §2.3, §4 |
| Cientos de euros, impresión 3D en horas | Coste del SO-100 frente a decenas de miles de un Panda | §2.3 |
| 1 % frente a 44 % de éxito | ACT sin y con action chunking | §4.2 |
| −33,3 % de éxito | ACT con regresión L1 en vez de CVAE, solo con demos humanas; con demos programadas no hay diferencia | §4.2 |
| 50-150 demostraciones (15-60 min de teleoperación) | Suficiente para entrenar Diffusion Policy | §4.3 |
| ~10 pasos de limpieza | Diffusion Policy con DDIM (10 veces menos que DDPM) | §4.3 |
| Δt = 33 ms | Ciclo de control a 30 fps | §4.4 |
| `chunk_size_threshold=0.5`, `actions_per_chunk=50` | Valores del ejemplo de cliente asíncrono con SmolVLA | §4.4.1 |
| `batch_size = 32` | Ejemplos de entrenamiento de ACT y Diffusion (con `training_steps = 1`, solo como demostración) | §4.2.1, §4.3.1 |
| 30 fps, 640×480 | Cámaras en todos los ejemplos de grabación y despliegue | §1.3, §4-5 |
| 5 episodios de 60 s, 10 s de reinicio | Valores de ejemplo del script de grabación | §1.3 |
| 3,3 B parámetros (VLM 2,6 B + experto 300 M) | π0 | §5.3 |
| >10 M trayectorias, 9,1 % abiertas, 7 robots, 68 tareas | Datos de preentrenamiento de π0 | §5.3 |
| 10 pasos de flow | Inferencia de π0 y de SmolVLA | §5.3, §5.4 |
| ~450 M parámetros, experto ~100 M | SmolVLA | §5.4 |
| 64 tokens visuales por fotograma, mitad de capas del VLM | Eficiencia de SmolVLA | §5.4 |
| >450 datasets, >20 000 trayectorias | Preentrenamiento de SmolVLA | §5.4 |
| ~40 % más rápido, 6× menos memoria (7× en la fig. 39) | SmolVLA frente a π0 | §5.4 |
| 25 000+ (BC-Z), 130 000 (RT-1), 970 000+ (OpenVLA), 1,4 M (Open-X), 75 000+ (DROID) | Tamaños de datasets históricos | §5.1 |
| >99 % en 1-2 h | HIL-SERL en manipulación real | §3.2 |

**Lo que el tutorial NO da** (no lo inventamos): número de pasos de entrenamiento recomendados, tiempo de entrenamiento
de ACT o SmolVLA, VRAM necesaria, hardware de entrenamiento, ni tasas de éxito de SmolVLA en tareas SO-101 concretas.
Esas cifras hay que sacarlas de la documentación de LeRobot o del artículo de SmolVLA.

## 5. Recetas y comandos de LeRobot que aparecen

> **Aviso de versión**: el tutorial es de octubre de 2025 y no dice qué versión de `lerobot` usa. Nuestro proyecto usa
> **LeRobot 0.7**: hay que comprobar cada import y cada nombre de clase contra la 0.7 antes de usarlo. Por ejemplo, los
> ejemplos usan clases `SO100Follower` / `SO100Leader`; para el SO-101 habrá que mirar cómo se llaman en la 0.7.

### 5.1 Comandos de consola mencionados
- `lerobot-record --help` — grabar datasets desde la consola [§1.3].
- `lerobot-find-port` — encontrar los puertos serie de guía y seguidor [§1.3 y siguientes].
- `lerobot-find-cameras` — encontrar los índices de las cámaras [§4.4.1].
- El tutorial no muestra `lerobot-train` ni comandos de calibración: el entrenamiento aparece solo como bucle en Python.

### 5.2 Formato LeRobotDataset [§1.1]
- `meta/info.json`: esquema de features (`observation.state`, `action`, `observation.images.<cámara>`...), fps,
  versión de lerobot y plantillas de rutas.
- `meta/stats.json`: media, desviación, mínimo y máximo de cada feature; se usan para normalizar
  (`dataset.meta.stats`).
- `meta/tasks.jsonl`: correspondencia entre la descripción de la tarea en lenguaje natural y un índice entero
  (lo que usa una política condicionada a tarea, como SmolVLA).
- `meta/episodes/*`: longitud, tarea y punteros de cada episodio.
- `data/*`: parquet con varios episodios por archivo, en subcarpetas por trozos.
- `videos/*`: MP4 por cámara, varios episodios concatenados por archivo.
- `delta_timestamps` permite pedir ventanas temporales alrededor de cada fotograma (por ejemplo, las acciones
  futuras de un trozo); los huecos se rellenan y se devuelve una máscara.
- `StreamingLeRobotDataset` lee desde el Hub sin descargar todo.

### 5.3 Grabar con teleoperación (esqueleto del Code 2, §1.3)
1. Configurar cámaras (`OpenCVCameraConfig(index_or_path=0, width=640, height=480, fps=30)`), robot seguidor y
   teleoperador guía con su puerto y su `id` (el `id` carga el archivo de calibración).
2. Construir las features con `hw_to_dataset_features(robot.action_features, "action")` y lo mismo con las
   observaciones.
3. `LeRobotDataset.create(repo_id=..., fps=30, features=..., robot_type=robot.name, use_videos=True,
   image_writer_threads=4)`.
4. Bucle por episodio: `record_loop(robot, events, fps, teleop, dataset, control_time_s, single_task=TASK, ...)`,
   después un `record_loop` sin dataset para reiniciar la escena, y `dataset.save_episode()`; para repetir un
   episodio, `dataset.clear_episode_buffer()`. Teclado con `init_keyboard_listener()` y visualización con `init_rerun`.
5. Al final, `dataset.push_to_hub()`.
- **(Inferencia)** `single_task` es el texto de la orden que se guarda con el episodio; para SmolVLA multitarea cada
  episodio debe llevar la orden correcta ("junta en T", "junta en esquina", "señala el cordón"...).

### 5.4 Entrenar ACT o Diffusion en Python (Code 7 y 9, §4.2.1, §4.3.1)
- `LeRobotDatasetMetadata(dataset_id)` → `dataset_to_policy_features(...)` → separar features de entrada y de salida
  (`FeatureType.ACTION`).
- `ACTConfig(input_features=..., output_features=...)` y `ACTPolicy(cfg)` (o `DiffusionConfig`/`DiffusionPolicy`).
- `make_pre_post_processors(cfg, dataset_stats=metadata.stats)`: normalización a la entrada y desnormalización a la
  salida. **Se guardan y se suben al Hub junto con la política.**
- `delta_timestamps` de las acciones a partir de `cfg.action_delta_indices` (eso es lo que crea los trozos).
- Optimizador con `cfg.get_optimizer_preset().build(policy.parameters())`; bucle clásico `preprocessor(batch)` →
  `policy.forward(batch)` → `loss.backward()` → `optimizer.step()`.
- `policy.save_pretrained(...)`, `policy.push_to_hub(...)` y lo mismo con pre y postprocesador.

### 5.5 Desplegar una política (Code 8, 10, 13, 14)
- Bucle: `robot.get_observation()` → `build_inference_frame(obs, features, device, task=..., robot_type=...)` →
  `preprocess` → `policy.select_action(obs)` → `postprocess` → `make_robot_action(...)` → `robot.send_action(...)`.
- Para π0 y SmolVLA el frame lleva además `task` (la orden en texto) y `robot_type`.
- **Los nombres y resoluciones de las cámaras deben coincidir con los del entrenamiento** (se ven en el `info.json` o
  en el `config.json` del modelo en el Hub).
- Modelos base citados: `lerobot/smolvla_base`, `lerobot/pi0_base`. Dataset de ejemplo: `lerobot/svla_so101_pickplace`.
- Hay un `preprocessor_overrides={"device_processor": {"device": ...}}` para elegir el dispositivo.

### 5.6 Inferencia asíncrona (Code 11 y 12, §4.4.1)
- Servidor: `PolicyServerConfig(host, port)` y `serve(config)` (`lerobot.async_inference.policy_server`).
- Cliente: `RobotClientConfig(robot=robot_cfg, server_address="host:puerto", policy_device=...,
  policy_type="smolvla", pretrained_name_or_path=..., chunk_size_threshold=0.5, actions_per_chunk=50)`;
  `client.start()`, un hilo con `client.receive_actions`, y `client.control_loop(task)`.
- `actions_per_chunk` tiene que ser menor que el máximo de acciones de la política.
- `visualize_action_queue_size(client.action_queue_size)` dibuja la evolución de la cola (útil para ajustar `g`).

### 5.7 Lo que el tutorial no incluye
- No hay ejemplo de **entrenamiento o ajuste fino de SmolVLA**: en el índice del repositorio aparece como pendiente
  ("5.4.2 Code Example: Training SmolVLA", sin marcar).

## 6. Lecciones aplicables a LeWelder

Todo este apartado es **inferencia nuestra** a partir de lo leído, salvo las cifras, que llevan su sección.

1. **El recolector programado no basta por sí solo.** Las demos programadas son unimodales y "perfectas": el ablation de
   ACT muestra que ahí el CVAE no aporta nada frente a una regresión simple [§4.2], y π0 explica que los datos sin fallos
   no enseñan a recuperarse [§5.3]. Conviene meter variabilidad a propósito en el recolector (posición inicial del brazo,
   posición de la chapa, perturbaciones y correcciones a mitad de trayectoria) y mezclarlo con teleoperación humana.
2. **Ojo con la mezcla de demos programadas y humanas.** Si se mezclan dos estilos distintos de resolver la tarea, los
   datos serán multimodales; ACT (CVAE) y SmolVLA (flow matching) son generativos y deberían tolerarlo mejor que una
   regresión, pero conviene que el programado imite el estilo humano (velocidad, aproximación) o etiquetarlo con cuidado.
3. **Número de episodios.** La única cifra del tutorial es la de Diffusion Policy: 50-150 demos (15-60 min de
   teleoperación) [§4.3]. Como orden de magnitud, apuntar a ≥50 episodios por tarea; con tres órdenes, el total sube.
4. **Cámaras fijas desde el primer día.** Los nombres, la resolución (640×480 a 30 fps en los ejemplos) y la posición
   de las cámaras deben ser idénticos en grabación y despliegue [§4.2.1, §5.4.1]. SmolVLA se preentrenó con vistas
   ordenadas top/wrist/side [§5.4]: usar nombres y vistas parecidos puede ayudar al ajuste fino.
5. **Órdenes de texto consistentes.** SmolVLA tuvo que reetiquetar instrucciones ruidosas de la comunidad [§5.4]:
   definir una lista cerrada de frases por tarea y usarla siempre igual en `single_task` (`meta/tasks.jsonl`).
6. **ACT frente a SmolVLA.**
   - ACT: una tarea por modelo, sin lenguaje, ligero, entrenamiento rápido; probablemente entrenable en la GTX 1660 de
     6 GB (no verificado: el tutorial no da requisitos de VRAM). Si necesitamos tres tareas, son tres modelos o un
     único modelo sin forma de elegir la tarea por texto.
   - SmolVLA: un modelo para todas las tareas, elegidas con lenguaje; parte de un preentrenamiento hecho con SO-100/101,
     que es justo nuestro robot; ~450 M de parámetros, mejor entrenarlo en la nube (HF Jobs).
   - Ambos predicen trozos de acciones; el despliegue en Python es casi idéntico, salvo que SmolVLA necesita `task`.
7. **Despliegue con inferencia asíncrona.** Con SmolVLA en el portátil, o en un servidor remoto, usar `PolicyServer` +
   `RobotClient` para que el brazo no se quede quieto entre trozos. Empezar con `chunk_size_threshold=0.5` y
   `actions_per_chunk=50` (valores del ejemplo) y ajustar `g` con la latencia medida (fórmula de §3.10).
8. **Subir siempre pre y postprocesador** junto al modelo; sin las estadísticas de normalización la política no sirve.
9. **Datos al Hub y streaming.** Grabar directamente a un repo del Hub (`push_to_hub`) facilita que HF Jobs entrene sin
   copiar archivos a mano; `StreamingLeRobotDataset` evita descargar el dataset entero.
10. **Probar el código antes del evento** con el dataset público `lerobot/svla_so101_pickplace` (SO-101 pick-and-place)
    y el modelo `lerobot/smolvla_base`, sin robot, para validar imports de la 0.7, features y bucle de inferencia.

## 7. Lo que no está claro o no hemos podido verificar

- **Afiliación (Hugging Face + Oxford)**: la página de arXiv solo da los nombres de los autores; no hemos visto la
  afiliación a Oxford en el HTML. No verificado.
- **Fecha en el HTML**: la versión HTML pone "Date: August 24, 2026", que parece la fecha de generación del HTML, no de
  publicación. La fecha de envío a arXiv es el 14 oct 2025.
- **Licencia del código**: el README del repositorio dice MIT para `snippets/` y CC BY-NC-SA para el texto, pero el
  archivo `LICENSE` de la rama `main` es CC BY-NC-ND 4.0. Antes de copiar código, confirmarlo.
- **Página del Space de Hugging Face**: no hemos podido leer su contenido (se carga con JavaScript); nos hemos basado en
  arXiv y en el README del repositorio.
- **Versión de LeRobot**: el tutorial no la dice. Rutas como `lerobot.robots.so100_follower`,
  `lerobot.scripts.lerobot_record.record_loop` o `lerobot.async_inference` pueden haber cambiado en la 0.7.
- **Algunos símbolos de las fórmulas** (desigualdades "<") se perdieron al convertir el HTML; la condición del umbral
  de la cola (|A_t|/H_a < g) se ha reconstruido por el texto que la rodea.
- **SmolVLA, 6× o 7× menos memoria**: el texto dice 6× y el pie de la figura 39, 7×.
- **Cifras ausentes**: pasos de entrenamiento, tamaño de batch recomendado, tiempo en GPU, VRAM mínima y tasas de éxito
  de ACT/SmolVLA en SO-101 no aparecen en el tutorial. Hay que buscarlas en la documentación de LeRobot y en los
  artículos de ACT (Zhao et al., 2023) y SmolVLA (Shukor et al., 2025).
- **RL**: los ejemplos de código de HIL-SERL (Code 3-6) se han hojeado, no se han estudiado línea a línea.
