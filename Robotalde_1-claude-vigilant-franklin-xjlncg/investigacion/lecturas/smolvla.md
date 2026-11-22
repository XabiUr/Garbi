# SmolVLA: lectura a fondo (artículo, blog, docs de LeRobot e inferencia asíncrona)

Lectura hecha el 18-11-2026 para el equipo Robotalde (LeWelder). Fuentes leídas directamente; lo que no se ha leído
en una fuente va marcado como **[no verificado]**. Abreviaturas de fuente:

- **[P]** artículo, versión HTML de arXiv: <https://arxiv.org/html/2506.01844> (v1).
- **[B]** blog de Hugging Face sobre SmolVLA: <https://huggingface.co/blog/smolvla>.
- **[BA]** blog de inferencia asíncrona (10-07-2025): <https://huggingface.co/blog/async-robot-inference>.
- **[D]** docs de LeRobot v0.7.0, página SmolVLA: <https://huggingface.co/docs/lerobot/v0.7.0/en/smolvla>.
- **[DA]** docs de LeRobot (rama main) "Asynchronous Inference": <https://huggingface.co/docs/lerobot/main/en/async>
  (en v0.7.0 esa página **ya no existe**: redirige y avisa).
- **[DR]** docs de LeRobot v0.7.0 "Remote Inference": <https://huggingface.co/docs/lerobot/v0.7.0/en/remote_inference>.
- **[DI]** docs de LeRobot "Policy Deployment (lerobot-rollout)": <https://huggingface.co/docs/lerobot/inference>.
- **[MC]** ficha del modelo <https://huggingface.co/lerobot/smolvla_base> y su `config.json`.
- **[R]** nuestro propio repositorio (`robot/entrenar.md`), medido por nosotros, no por Hugging Face.

---

## 1. Ficha

| Campo | Valor |
|---|---|
| Título | *SmolVLA: A vision-language-action model for affordable and efficient robotics* [P] |
| Autores | Mustafa Shukor, Dana Aubakirova, Francesco Capuano, Pepijn Kooijmans, Steven Palma, Adil Zouitine, Michel Aractingi, Caroline Pascal, Martino Russi, Andres Marafioti, Simon Alibert, Matthieu Cord, Thomas Wolf, Remi Cadene (Hugging Face, Sorbonne, valeo.ai, ENS Paris-Saclay) [P] |
| Fecha | Enviado a arXiv el 2-06-2025; identificador **arXiv:2506.01844** (comprobado, coincide) [P] |
| Modelo base | `lerobot/smolvla_base`, ~450 M parámetros (~100 M en el experto de acciones) [P][D] |
| VLM de partida | `HuggingFaceTB/SmolVLM2-500M-Video-Instruct` [MC config] |
| Licencia del modelo | **Apache-2.0** [MC] |
| Código | LeRobot (`pip install -e ".[smolvla]"`) [D] |
| Datasets del artículo | p. ej. `lerobot/svla_so100_pickplace`, `lerobot/svla_so100_stacking` [B][D] |

## 2. Resumen en 10 líneas

1. SmolVLA es un modelo visión-lenguaje-acción pequeño (~0,45 B) pensado para entrenarse en una GPU y ejecutarse en
   GPU de consumo o incluso CPU [P].
2. Recorta un VLM pequeño (SmolVLM2): usa solo la mitad inferior de las capas del modelo de lenguaje y 64 tokens por
   imagen [P].
3. Encima pone un "experto de acciones" (transformer de ~100 M) que genera trozos (*chunks*) de 50 acciones con
   *flow matching* [P].
4. El VLM se congela; en el ajuste fino solo se entrena el experto (y la proyección del estado) [P][MC].
5. Se preentrena con solo ~23 k episodios de 481 datasets de la comunidad (casi todos SO-100) [P].
6. En simulación iguala o supera a π0 (3,3 B): LIBERO 87,3 % frente a 86,0 % [P].
7. En robot real SO-100, multitarea, saca 78,3 % de media frente a 61,7 % de π0 y 48,3 % de ACT [P].
8. Preentrenar con datos de la comunidad sube de 51,7 % a 78,3 % en el SO-100; el multitarea por sí solo sube de 40 %
   a 51,7 % [P].
9. Introduce la inferencia asíncrona (el robot sigue moviéndose mientras se calcula el siguiente chunk): ~30 % menos
   tiempo por tarea con éxito parecido [P].
10. Limitaciones: datos de un solo tipo de robot, pocos datos, tareas largas difíciles, solo aprendizaje por
    imitación [P].

## 3. Arquitectura explicada para alguien de software

Piensa en un *pipeline* de dos bloques: un **codificador** (el VLM) que convierte imágenes + texto + estado en una
secuencia de vectores, y un **generador de acciones** (el experto) que, mirando esos vectores, produce 50 acciones
futuras de golpe.

**Entradas** [P][D]:
- Varias cámaras (en el modelo base: `observation.images.camera1`, `camera2`, `camera3`) [MC config].
- El estado del robot (`observation.state`, 6 valores en el SO-100/101; se rellena hasta `max_state_dim=32`) [MC].
- Una instrucción en lenguaje natural (la "tarea" del dataset, `--task` al ejecutar) [D].

**El VLM (SmolVLM2)** [P]:
- Codificador de visión SigLIP + decodificador de lenguaje SmolLM2.
- **Tokens visuales:** solo la imagen global (sin dividirla en teselas) y un *pixel shuffle* que deja **64 tokens por
  imagen**. Las imágenes se redimensionan a 512×512 con relleno (`resize_imgs_with_padding: [512, 512]`) [P][MC].
- **Capas que se saltan:** de las L capas del modelo de lenguaje solo se usan las N primeras, con N = L/2; el modelo
  publicado usa **16 capas** (`num_vlm_layers: 16`). Leer características de capas intermedias funciona casi igual y
  cuesta la mitad [P][MC].
- **Estado:** una capa lineal lo proyecta a **un único token**, que se concatena con los de imagen y texto [P].
- **Texto de la tarea:** se tokeniza y entra como tokens de lenguaje en el mismo prefijo que las imágenes y el estado.
  En la configuración se rellena a longitud fija, **`tokenizer_max_length: 48` tokens** (`pad_language_to:
  max_length`) [MC]. No hay nada especial para "órdenes": la frase condiciona al VLM, y el VLM condiciona al experto.
- El VLM está **congelado** (`freeze_vision_encoder: true`, `train_expert_only: true`, `train_state_proj: true`) [MC].

**El experto de acciones** [P][MC]:
- Transformer con anchura 0,75 × la del VLM (`expert_width_multiplier: 0.75`), ~100 M parámetros.
- **Atención intercalada:** alterna capas de atención cruzada (las acciones "miran" las claves/valores del VLM) con
  capas de autoatención causal entre los tokens de acción (`self_attn_every_n_layers: 2`). En la ablación esta mezcla
  gana: 85,5 % frente a 79,0 % (solo cruzada) y 74,5 % (solo autoatención) en LIBERO [P].
- **Flow matching:** en entrenamiento se toma el chunk real de acciones, se le mezcla ruido en un tiempo τ (sacado de
  una distribución Beta) y la red aprende el campo de velocidad que lleva del ruido a las acciones. En inferencia se
  parte de ruido y se integran **10 pasos** (`num_steps: 10`). Ablación: flow matching 80,25 % frente a regresión L1
  75,25 % [P][MC].
- **Chunk de acciones:** n = 50 (`chunk_size: 50`); por defecto se ejecutan las 50 antes de volver a observar
  (`n_action_steps: 50`) [P][MC]. A 30 fps, 50 acciones son ~1,67 s de movimiento.
- Normalización: estado y acción con media/desviación del dataset; imágenes sin normalizar (`IDENTITY`) [MC].

**Ablaciones útiles (todas en LIBERO, % de éxito)** [P]:
- Tamaño de chunk: 1 → 50,0; 10 → 84,0; 30 → 78,5; 50 → 80,3; 100 → 74,5. El texto dice que 10-50 va bien.
- Acciones ejecutadas antes de reobservar: 1 → 80,3; 10 → 82,8; 30 → 70,8; 50 → 51,8. **Reobservar más a menudo
  ayuda mucho.** (Ojo: el modelo publicado ejecuta 50 por defecto.)
- Capas del VLM: N=8 → 75,0; 16 → 78,5; 24 → 79,5; 32 → 80,3.
- Estado en el prefijo del VLM con atención cruzada: 80,3 frente a 73,3 si va al experto.
- Máscara causal en las acciones (74,5) mejor que bidireccional (67,5).
- Incoherencias del propio artículo: recomienda anchura 0,75 pero en la tabla 0,50 puntúa más (80,3 frente a 77,5);
  y el chunk por defecto es 50 aunque 10 puntúa más.

## 4. Preentrenamiento

- **Datos:** 481 datasets de la comunidad en el Hub, ~22,9 k episodios y 10,6 M de fotogramas; el artículo habla de
  "menos de 30 k episodios" [P]. El blog dice **487** datasets, ~10 M de fotogramas, todos a 30 fps [B] (discrepancia
  481/487 sin resolver). Casi todos son del brazo SO-100 [P][B].
- **Selección:** filtrados por tipo de robot, número de episodios, calidad y cobertura de fotogramas, con revisión
  manual [P][B].
- **Limpieza de instrucciones:** muchas descripciones eran basura ("task desc", "Hold", "Up"). Se regeneraron con
  **Qwen2.5-VL-3B-Instruct** a partir de fotogramas representativos. El *prompt* pide una frase muy corta, completa,
  de **30 caracteres como máximo** y que **empiece por un verbo** ("Pick", "Place", "Open"…) [P apéndice][B].
- **Normalización de cámaras:** se asignaron a mano las vistas a tipos y se renombraron: **OBS_IMAGE_1 = cenital
  (top)**, **OBS_IMAGE_2 = muñeca (wrist)**, OBS_IMAGE_3 = lateral (side); las vistas sobrantes se descartaron [P][B].
  En el modelo publicado se llaman `camera1/2/3` [MC][D].
- **Entrenamiento:** 200 000 pasos, batch global 256, *warmup* 100 pasos, coseno de 1e-4 a 2,5e-6, AdamW (β1 0,9,
  β2 0,95), bf16, `torch.compile`, Accelerate, **4 GPU**; ~30 k horas de GPU en todo el proyecto [P].

## 5. Ajuste fino: hiperparámetros, tiempo y memoria

| Dato | Valor | Fuente |
|---|---|---|
| Receta oficial de la doc | `--policy.path=lerobot/smolvla_base --batch_size=64 --steps=20000` | [D][B] |
| Tiempo de esa receta | **~4 h en una A100** para 20 000 pasos | [D] |
| 20 000 pasos = "10 % del presupuesto" | el entrenamiento desde cero son 200 000 | [B] |
| Ajuste fino en el artículo (real) | **200 000 pasos** (batch no indicado) | [P] |
| Ajuste fino en el artículo (simulación) | 100 000 pasos, batch 64 | [P] |
| lr y planificador del `config.json` | lr 1e-4, betas (0,9, 0,95), *warmup* **1000**, decaimiento coseno en **30 000** pasos hasta 2,5e-6, *clip* de gradiente 10, *weight decay* 1e-10 | [MC] |
| Ejemplo de la ficha del modelo | `--batch_size=4 --steps=100000 --policy.dtype=bfloat16` | [MC] |
| Consejo de batch | empezar pequeño y subir mientras la GPU aguante y la carga de datos sea rápida | [D] |
| Cámaras | `--rename_map` obligatorio a `camera1/2/3`; sin él, error de *features* | [D] |
| Cámara que falta | `--policy.empty_cameras=1` (lo usamos y funciona en LeRobot 0.7 en CPU) | [R]; el campo `empty_cameras` existe en [MC] |
| Memoria en entrenamiento | "~6× menos memoria que π0" y "~40 % más rápido de entrenar"; "se entrena fácilmente en una GPU" | [P] |
| Memoria en inferencia | **~2 GB** (frente a 14 GB de π0) | [DA] |
| GPU concreta para ajuste fino / VRAM mínima | **no indicado** en ninguna fuente oficial | — |

Notas:
- El *warmup* del artículo (100) y el del `config.json` (1000) no coinciden; manda el `config.json` al cargar con
  `--policy.path` **[no verificado** si `lerobot-train` lo sobreescribe con otros valores por defecto**]**.
- El planificador decae en 30 000 pasos: si entrenamos 15 000-20 000 pasos, el lr no llega al mínimo. No es grave, pero
  conviene saberlo [MC; consecuencia deducida por nosotros].
- Nuestras cifras propias [R]: en CPU, 3,6-3,8 s/paso con batch 4; checkpoint de 1,3 GB; inferencia en CPU ~1,5 s
  por chunk de 50 acciones. La estimación de 0,5-0,7 s/paso en L4 con batch 32 de `robot/entrenar.md` es **nuestra
  estimación, no medida** para SmolVLA (lo medido en L4 fue ACT).

## 6. Resultados en robot real (SO-100 / SO-101)

**Tareas** [P, sección 4.1]:
- *Pick-Place* (SO-100): "coge el cubo y déjalo en la caja"; caja fija, cubo en 5 posiciones de partida. Nota: 0,5 por
  coger + 0,5 por dejar.
- *Stacking* (SO-100): "coge el cubo rojo y ponlo encima del azul"; varían las dos posiciones.
- *Sorting* (SO-100, la más larga): "rojo a la caja derecha, azul a la izquierda"; 4 hitos de 0,25.
- *Pick-Place-Lego* (SO-101): "mete el ladrillo de lego rosa en la caja transparente"; objeto pequeño y caja
  transparente.

**Episodios:** **50 demostraciones por tarea = 10 por cada una de 5 posiciones de partida** (en sorting, 5 por
configuración de colores) [P]. La doc añade: con 25 episodios "no fue suficiente" y el rendimiento fue malo [D].
**Cámaras:** SO-100 cenital + muñeca; SO-101 cenital + lateral [P].
**Número de intentos de evaluación por tarea:** **no indicado** en el artículo (solo el estudio de tiempos usa 10) [P].

**Tasas de éxito SO-100 (%)** [P]:

| Política | Entrenamiento | Pick-Place | Stacking | Sorting | Media |
|---|---|---|---|---|---|
| ACT | una tarea | 70 | 50 | 25 | 48,3 |
| π0 (3,5 B) | multitarea | 100 | 40 | 45 | 61,7 |
| SmolVLA (0,45 B) | multitarea | 75 | 90 | 70 | **78,3** |

**Efecto del multitarea y del preentrenamiento (SmolVLA, SO-100, %)** [P]:

| Configuración | Pick-Place | Stacking | Sorting | Media |
|---|---|---|---|---|
| Una tarea, sin preentrenar | 55 | 45 | 20 | 40,0 |
| Multitarea, sin preentrenar | 80 | 40 | 35 | 51,7 |
| Multitarea, con preentrenamiento comunitario | 75 | 90 | 70 | 78,3 |

Lectura: el multitarea ayuda (+11,7 puntos) y el preentrenamiento ayuda mucho más (+26,6). Ojo: el multitarea del
artículo mezcla **tareas visualmente distintas**; no dice nada de tareas casi iguales que solo se distinguen por la
frase.

**SO-101 Pick-Place-Lego (%)** [P]: SmolVLA 90 en distribución / 50 fuera de distribución (posiciones no vistas);
ACT 70 / 40. El texto dice que se entrenó con "una combinación de tres datasets", pero la tabla pone "una tarea"
(incoherencia del artículo).

**Simulación** [P]: LIBERO media 87,3 % (π0 86,0 %); Meta-World 57,3 % (π0 47,9 %).

## 7. Inferencia asíncrona

### 7.1 La idea (artículo y blog)

- **Síncrona:** el robot ejecuta el chunk, se para, manda la observación, espera a la red y vuelve a moverse. Hay
  "fotogramas parados" de duración ≈ latencia de inferencia [P][DA].
- **Asíncrona:** dos procesos (pueden ir en máquinas distintas): un **RobotClient** junto al robot, que captura
  observaciones y ejecuta acciones de una cola, y un **PolicyServer** con GPU que calcula chunks. Cuando la cola baja
  de una fracción **g** del chunk (|cola|/n < g), el cliente manda una observación nueva y **sigue ejecutando** lo que
  le queda; el nuevo chunk se **fusiona** con lo pendiente en los pasos que se solapan [P].
  - g = 0: secuencial (equivale a síncrono). g = 0,7: se pide el siguiente tras consumir ~30 % del chunk. g = 1: una
    inferencia por paso de control (caro) [P].
  - Condición para no vaciar la cola: g ≥ (E[ℓ_S]/Δt)/n, con Δt = 33 ms a 30 fps [P].
  - Filtro de observaciones parecidas en espacio articular (umbral ε) para no recalcular en vano; si la cola se
    vacía, se procesa la última sí o sí [P][BA].
- **Resultados** [P]: éxito parecido (síncrono 78,3 %, asíncrono 73,3 %; sorting baja de 70 a 50); *pick-place* en
  9,7 s frente a 13,75 s (~30 % más rápido); en una ventana fija, 19 cubos frente a 9.
- **Latencias** [BA]: SmolVLA ida y vuelta "por debajo de 100 ms" en red local con el servidor en una **RTX 4090**;
  comunicación por gRPC. El artículo no da latencias de inferencia en ms ni hardware de inferencia [P].

### 7.2 Cómo se usaba en LeRobot (antes de 0.7) [DA]

`pip install -e ".[async]"`, servidor `python -m lerobot.async_inference.policy_server --host=127.0.0.1
--port=8080` y cliente `python -m lerobot.async_inference.robot_client` con `--actions_per_chunk=50`
(típico 10-50), `--chunk_size_threshold` (en la tabla de la doc, por defecto 0,7; recomiendan 0,5-0,6) y
`--aggregate_fn_name=weighted_average`. Servidor y cliente podían ir en la misma máquina (localhost) o en red.

### 7.3 Lo que hay en LeRobot 0.7 (importante para nosotros)

- **`lerobot[async]` y `lerobot.async_inference` están retirados** en 0.7. Los sustituyen [DR]:
  - **`--inference.type=rtc`** (*Real-Time Chunking*) local: un hilo en segundo plano calcula el siguiente chunk
    mientras el bucle de control ejecuta el actual, **en la misma máquina y sin servidor**. Compatible con SmolVLA,
    Pi0 y Pi0.5. La doc de SmolVLA lo recomienda "cuando la inferencia es lenta, p. ej. en hardware modesto":
    `--inference.type=rtc --inference.rtc.execution_horizon=10 --inference.rtc.max_guidance_weight=10.0` [D][DI].
  - **`--inference.type=remote`**: servidor `lerobot-policy-server --config_path=server.yaml` (transporte Zenoh,
    extra `remote`) y cliente `lerobot-rollout --inference.type=remote --inference.endpoint=tcp/IP:7447 ...`. Sirve en
    la misma máquina (127.0.0.1) o en una LAN de confianza; SmolVLA está entre las políticas probadas en robot real
    por esta vía [DR].
- Parámetros nuevos del remoto [DR]: `refill_seconds` (0,5 s de reproducción restante por defecto; el efectivo es
  `max(refill_seconds, latencia máxima reciente + 1/fps)`), `chunk_merge` (`aligned` por defecto, `append`),
  mezcla opcional (`blend_steps`, `blend_weight`, `blend_components` sin la pinza), `action_starvation_grace_s` (1 s),
  `max_observation_age_s` (5 s). Los umbrales antiguos **no** son equivalentes: hay que reajustar.
- **Pérdida de conexión** [DR]: no se recupera sola; el robot agota la cola, espera hasta 1 s y da fallo terminal; hay
  que relanzar el *rollout*. Por eso la nube por wifi es frágil para una demo.
- El SO-101 *follower* declara soporte de "mantener posición" mientras espera, requisito del remoto y del RTC con
  espera [DR][DI].
- Ejecución síncrona simple en 0.7: `lerobot-rollout --strategy.type=base --policy.path=... --rename_map=...
  --task="..."`; `--device=cuda|cpu`; `--interactive=true` permite `/start`, `/reset` y `/subtask <texto>` para
  cambiar la orden sin recargar el modelo [D][DI].
- Aviso [DI]: cambiar la orden con `/subtask` provoca una parada breve; con `--use_torch_compile=true` un cambio de
  frase que cambie la forma de los tensores puede recompilar y fallar. **Dejar la compilación desactivada** si vamos a
  cambiar órdenes en caliente.

## 8. Lecciones concretas para LeWelder

1. **Episodios por orden.** La referencia oficial es **50 por tarea, 10 por variación** (posición de partida), y 25
   fue insuficiente [P][D]. Con 3 órdenes, el mínimo razonable es **~150 episodios** (50 × 3), repartidos en ~5
   posiciones de la chapa con ~10 cada una. Nuestro umbral de "≥ 50 episodios el viernes" vale para **una** orden, no
   para tres. Si no da tiempo, mejor 2 órdenes bien grabadas que 3 cojas.
2. **Formato de la instrucción.** El preentrenamiento vio frases **cortas, en inglés, que empiezan por verbo y de ≤ 30
   caracteres** [P]. El VLM es SmolVLM2 (entrenado sobre todo en inglés **[no verificado** qué tal entiende
   español**]**). Recomendación: guardar en el dataset la tarea en inglés corto y fijo ("Build a T joint", "Build a
   corner joint", "Point at the seam") y traducir la orden de voz a esa cadena exacta; usar **siempre la misma
   cadena** al grabar y en `--task` [D]. Caben de sobra en los 48 tokens [MC].
3. **Órdenes que se parecen.** "T" y "esquina" se distinguen sobre todo por la frase (misma chapa, misma escena). El
   artículo no prueba este caso; su multitarea son tareas visualmente distintas [P]. Riesgo: que la red ignore el
   texto y haga la media de las dos. Mitigación: que la escena también difiera (base distinta para T y esquina, si la
   spec lo permite) y evaluar por separado cada orden.
4. **Cámaras.** Nuestro mapeo (cenital → `camera1`, muñeca → `camera2`, `empty_cameras=1`) coincide con la convención
   del preentrenamiento (OBS_IMAGE_1 cenital, OBS_IMAGE_2 muñeca) [P][B]: es la elección correcta. Mismo nombre,
   resolución y posición de cámara al grabar y al ejecutar [D]; el `--rename_map` debe ser el mismo en entrenar y
   ejecutar [D].
5. **Ajuste fino en HF Jobs.** Partir de la receta oficial (batch 64, 20 000 pasos ≈ 4 h en A100 [D]). En una L4
   será más lento **[no verificado** cuánto**]**; para el sábado conviene un primer modelo corto (p. ej. 5 000-8 000
   pasos) para probar el flujo y otro largo después. Medir s/paso en los primeros minutos del Job y decidir.
6. **Inferencia en la GTX 1660 (6 GB, sin bf16).** Memoria: ~2 GB en inferencia [DA] → cabe en 6 GB en fp32.
   Velocidad: **no hay cifras oficiales para esta GPU**; en nuestra CPU tarda ~1,5 s por chunk [R], y un chunk de 50
   acciones dura ~1,67 s a 30 fps, así que en GPU debería sobrar margen **[no verificado:** medirlo el jueves con
   `lerobot-rollout` y el informe de cadencia, línea `infer`**]**. Opciones en orden: (a) síncrono en la 1660
   (`--device=cuda`), con paradas breves entre chunks; (b) `--inference.type=rtc` local para no pararse; (c) remoto
   en la nube solo de respaldo. No pasar `--policy.dtype=bfloat16` en la 1660.
7. **Reobservar más a menudo.** La ablación dice que ejecutar 10 acciones antes de reobservar (82,8 %) es mucho mejor
   que 50 (51,8 %) [P]. Para una tarea de precisión (dejar la chapa en los imanes) merece la pena probar
   `n_action_steps` menor (p. ej. 10-25) si la 1660 da la latencia, o RTC **[no verificado** el flag exacto para
   cambiar `n_action_steps` en `lerobot-rollout`**]**.
8. **Tarea de montar.** Coger por la aleta, girar 90° y dejar sobre imanes es parecida en dificultad a *pick-place*
   (75 %) pero con orientación; el giro de muñeca añade dificultad. Expectativa realista con 50 episodios por orden y
   un solo ciclo grabar-entrenar: éxito parcial; contar con el plan B (replay/ACT) como ya dice `estado.md`.
9. **Recolector programado.** Las trayectorias programadas son muy regulares; el modelo aprenderá esa regularidad.
   Mezclar con teleoperación y variar posiciones de partida como en el artículo (5 posiciones × 10) [P].
10. **Cambio de orden en la demo.** Usar `--interactive=true` y `/subtask "<orden>"` para cambiar la frase sin recargar
    el modelo; esperar una parada breve [DI]. Sin `torch.compile`.

**Riesgos principales:** pocas demostraciones para tres órdenes; órdenes indistinguibles visualmente; idioma de la
instrucción; latencia real en la 1660 sin medir; cualquier inferencia por red cae ante un corte de wifi sin
recuperación automática [DR].

## 9. Lo que no está claro o no he podido verificar

- Número de intentos de evaluación por tarea en robot real: el artículo no lo da.
- Batch del ajuste fino real (200 000 pasos) en el artículo: no se indica.
- 481 (artículo) frente a 487 (blog) datasets de preentrenamiento.
- SO-101: "combinación de tres datasets" en el texto frente a "una tarea" en la tabla.
- VRAM necesaria para **entrenar** SmolVLA con un batch dado: ninguna fuente oficial la da. Una cifra de 0,9 GB y
  18 ms/paso aparece en un comentario de la página del artículo en HF, sin GPU indicada: no fiable.
- Latencia de inferencia en GTX 1660 (o cualquier GPU sin núcleos tensor): no publicada.
- Si SmolVLA funciona en fp16 en la 1660 y si aporta algo frente a fp32: no verificado.
- Comportamiento con instrucciones en español: no verificado (todo el preentrenamiento es en inglés).
- Forma exacta de la función de agregación del artículo (solo "fusionar" los chunks solapados).
- Si `lerobot-train` respeta el *warmup* 1000 / decaimiento 30 000 del `config.json` o los recalcula.
- Equivalencia entre el `g` del artículo y los parámetros `refill_seconds`/RTC de LeRobot 0.7: la doc dice que no
  son intercambiables.
- No he leído la página de RTC (`/docs/lerobot/rtc`) en detalle ni la tabla de soporte de políticas del README de
  `remote_inference`.
