# Aprendizaje por imitación: ACT, Diffusion Policy y fundamentos

Lectura de referencia para LeWelder (hackathon LeRobot Bilbao II). Resumen propio de cuatro fuentes, con las cifras
copiadas de los artículos. Lo que no he leído directamente va marcado como **[no verificado]**.

Fecha de la lectura: 18-11-2026.

---

## 1. Fichas de las fuentes

| # | Título | Autores | Fecha | Enlace | Qué he leído |
|---|--------|---------|-------|--------|--------------|
| A | *Learning Fine-Grained Bimanual Manipulation with Low-Cost Hardware* (ACT / ALOHA) | Tony Z. Zhao, Vikash Kumar, Sergey Levine, Chelsea Finn (Stanford, Berkeley, Meta) | arXiv v1, 23-04-2023 (identificador **2304.13705 verificado**). Se presentó en RSS 2023 **[venue no verificado: la página de arXiv no lo indica]** | https://arxiv.org/abs/2304.13705 · proyecto: https://tonyzhaozh.github.io/aloha | Artículo completo con apéndices (PDF v1), README del repositorio `tonyzhaozh/act` y el documento "ACT tuning tips" del autor |
| B | *Diffusion Policy: Visuomotor Policy Learning via Action Diffusion* | Cheng Chi, Zhenjia Xu, Siyuan Feng, Eric Cousineau, Yilun Du, Benjamin Burchfiel, Russ Tedrake, Shuran Song | arXiv v1 07-03-2023; v5 14-03-2024 (versión de revista ampliada del artículo de RSS 2023) | https://arxiv.org/abs/2303.04137 · https://diffusion-policy.cs.columbia.edu | PDF v5 completo, incluidas las tablas de hiperparámetros del apéndice |
| C | *Underactuated Robotics*, cap. 21 "Imitation Learning" | Russ Tedrake (MIT) | Notas del curso de primavera 2024, © 2024; varias secciones están sin terminar | https://underactuated.csail.mit.edu/imitation.html | Página completa (resumida con WebFetch, no línea a línea) |
| D | *An Algorithmic Perspective on Imitation Learning* | Takayuki Osa, Joni Pajarinen, Gerhard Neumann, J. Andrew Bagnell, Pieter Abbeel, Jan Peters | arXiv 16-11-2018; publicado en *Foundations and Trends in Robotics* (DOI 10.1561/2300000053) | https://arxiv.org/abs/1811.06711 | Solo §1.3-1.4 (relación con aprendizaje supervisado), §3.4.1 y §3.4.3 (BC, errores en cascada, DAgger) y §5.1-5.2 (BC frente a IRL, preguntas abiertas) |

Fuentes secundarias consultadas para contrastar con LeRobot:
- `src/lerobot/policies/act/configuration_act.py` de la rama `main` de LeRobot (valores por defecto de ACT). **No he
  comprobado que coincidan con la versión 0.7**, aunque es lo más probable.
- `imitate_episodes.py` del repositorio original de ACT (coeficiente del temporal ensembling).

---

## 2. Imitación en general (para alguien que viene del software)

### 2.1 Qué es el behavioral cloning (BC)

- Imitación = aprender una política (observación → acción) a partir de demostraciones, sin función de recompensa.
  Hay dos familias (D §5.1, C):
  - **Behavioral cloning (BC)**: aprendizaje supervisado puro. Pares (observación, acción) del experto; se entrena una
    red para predecir la acción. Es lo que hacen ACT, Diffusion Policy y los VLA como SmolVLA.
  - **Inverse RL (IRL)**: se infiere la función de coste/recompensa que explica las demostraciones y luego se
    obtiene la política con control óptimo o RL. Es más complejo; compensa cuando la recompensa es una descripción más
    compacta y generalizable que la política (ejemplo de Osa: elegir pisadas estables de un cuadrúpedo en terrenos
    nuevos).
- Para manipulación, Osa dice que recuperar la recompensa suele ser difícil porque no es obvio qué rasgos de la escena
  importan, mientras que la distribución de trayectorias demostradas sí se puede aprender directamente. Es decir,
  **para nuestro caso, BC es la elección natural**.
- Tedrake (C) llama a BC "the shortest path" hacia políticas generalistas y lo describe como regresión (si hay estado
  completo) o modelado de secuencias (si solo hay observaciones parciales, como imágenes), igual que un LLM predice el
  siguiente token.

### 2.2 El problema de fondo: desplazamiento de distribución y errores en cascada

Analogía de software: entrenas un clasificador con datos de producción "limpios", pero en producción sus propias
salidas cambian los datos de entrada del día siguiente. Si se equivoca un poco, mañana verá entradas que nunca vio en el
entrenamiento, se equivocará más, y así sucesivamente.

- El aprendizaje supervisado supone datos i.i.d. En imitación esto se rompe: los estados que ve la política dependen
  de sus propias acciones anteriores (D §3.4.3). En ML se llama *covariate shift* (D §1.4).
- Un error pequeño al principio lleva al robot a un estado que el experto nunca visitó; ahí la política no sabe qué
  hacer, comete más errores y deriva ("small error may cascade", D §3.4.3). ACT lo llama *compounding error* y lo
  identifica como el principal problema en tareas de precisión (A §I, §IV).
- Ejemplo clásico (ALVINN, Pomerleau 1988, citado en D): un coche que aprendió a conducir con imágenes y ángulos de
  volante se salía de la carretera enseguida. Pomerleau ya decía que la red debe ver no solo conducción correcta, sino
  también **cómo recuperarse** (volver al centro del carril) tras un error.
- En tareas de precisión milimétrica el efecto es peor: en el Thread Velcro de ACT, unos pocos milímetros de error en
  el primer agarre se convierten en más de 10 mm de desviación en la inserción (A §V-A).
- El resultado teórico clásico (Ross y Bagnell) dice que el error de BC puede crecer con el cuadrado del horizonte y el
  de DAgger linealmente. **[no verificado: no aparece en las partes leídas; Osa solo cita "una prueba de bajo error en
  DAgger"]**.

### 2.3 Soluciones clásicas: DAgger y datos de recuperación

- **DAgger** (Ross et al. 2011, explicado en D §3.4.3.3): bucle iterativo.
  1. Entrena una política con las demostraciones (BC normal).
  2. Ejecuta la política (o una mezcla experto/política) y registra los estados que visita.
  3. El experto etiqueta **esos** estados con la acción correcta.
  4. Añade los datos al conjunto y reentrena. Repite.

  Así la política aprende justo en los estados donde se equivoca. Según Osa, reduce mucho los datos necesarios y suele
  dar mejores resultados incluso a largo plazo.
- Límites prácticos: hace falta un experto disponible para corregir en línea, y en el mundo físico reiniciar el estado
  es caro. ACT lo descarta porque con teleoperación anotar correcciones es lento y poco natural (A §II).
- Otra opción es **inyectar ruido** al grabar para obtener datos con correcciones. ACT advierte que en manipulación fina
  ese ruido puede hacer fallar la tarea directamente (A §II).
- Variante "por confianza" (Chernova y Veloso, en D §3.4.3.2): pedir una demostración solo cuando la política tiene
  poca confianza o el experto ve un error.

### 2.4 Por qué ayuda el *chunking* de acciones

- En lugar de predecir una acción por paso, la política predice las **k siguientes** (un "chunk") a partir de la
  observación actual: πθ(a_t:t+k | s_t) en vez de πθ(a_t | s_t) (A §IV-A).
- Efectos:
  1. **Reduce el horizonte efectivo k veces**: con 500 pasos y k = 100, la política solo "decide" 5 veces, así que hay
     menos ocasiones de acumular error.
  2. **Absorbe comportamiento no markoviano** de los humanos, como pausas a mitad de demostración: una política de un
     paso no sabe si "ahora toca quedarse quieto" porque eso depende del tiempo, no del estado. Si la pausa cae dentro
     de un chunk, se modela bien (A §IV-A; B §4.3 "robustness to idle actions").
  3. **Coherencia temporal**: si hay dos maneras válidas de hacer algo (rodear un objeto por la izquierda o por la
     derecha), predecir paso a paso puede saltar entre ambas y dar movimientos erráticos; una secuencia completa se
     compromete con una (B §4.3).
- El coste es reaccionar peor: con el chunk entero en bucle abierto, el robot no corrige hasta el siguiente chunk. ACT
  lo compensa con *temporal ensembling* y Diffusion Policy ejecutando solo una parte del chunk (*receding horizon*).
- Tedrake (C) lo resume como que ACT y Diffusion Policy predicen secuencias "como un control predictivo (MPC)" y que
  eso da ejecuciones más estables.

---

## 3. ACT en detalle

### 3.1 Hardware ALOHA (contexto)

- Dos brazos ViperX 6-DoF seguidores (~5.600 $ cada uno; precisión 5-8 mm, repetibilidad 1 mm) y dos WidowX guía
  (~3.300 $). Coste total < 20.000 $. Pinzas impresas en 3D, "transparentes", con cinta de agarre (A §III).
- **Teleoperación por mapeo en espacio articular** (guía → seguidor articulación a articulación), igual que nuestro
  SO-101 guía/seguidor. Ventajas según los autores: la cinemática inversa falla cerca de singularidades, y el mapeo
  articular no; el peso del brazo guía impide moverse demasiado rápido y amortigua vibraciones. Rindieron mejor así que
  con un mando de realidad virtual en tareas precisas.
- Ayudas para el operador: mecanismo de "asa y tijera" impreso que reduce la fuerza necesaria y permite controlar la
  pinza de forma continua; gomas que compensan parte de la gravedad del guía y permiten sesiones de más de 30 min.
- **Cámaras**: 4 webcams Logitech C922x a 480×640 (y 30 fps): una en cada muñeca, una frontal y una cenital. Foco fijo
  y exposición automática. La frontal está girada 90° para cubrir más altura (A §III, apéndice B).
- **Frecuencia**: teleoperación y grabación a **50 Hz**.

### 3.2 Arquitectura

- **Acciones** = posiciones articulares objetivo absolutas de ambos brazos (14 dimensiones). Detalle importante: se
  graba como acción la posición del **brazo guía**, no la del seguidor, porque la diferencia entre ambos es lo que
  define implícitamente la fuerza a través del PID del motor (A §IV).
- **Observaciones** = 4 imágenes RGB + posiciones articulares del seguidor (14).
- Se entrena como **CVAE** (autoencoder variacional condicional):
  - *Codificador del CVAE* (solo en entrenamiento): transformer tipo BERT que recibe [CLS] + articulaciones + la
    secuencia de acciones real (k pasos) y produce media y varianza de una variable latente z de 32 dimensiones, el
    "estilo". Por velocidad, no ve las imágenes. **Se descarta en inferencia.**
  - *Decodificador del CVAE* (= la política): una ResNet18 por cámara convierte cada imagen 480×640 en un mapa
    15×20×512 → 300 tokens con embedding posicional 2D; 4 cámaras → 1.200 tokens, más un token de articulaciones y
    otro de z. Un encoder transformer los fusiona y un decoder transformer con k consultas posicionales fijas genera
    k×512, que una MLP proyecta a k×14.
  - En inferencia **z = 0** (la media del prior), así que la política es determinista.
- **Pérdida**: L1 de reconstrucción + β·KL. Usaron **L1 en vez de L2** porque daba acciones más precisas. Las
  acciones **delta** (incrementos articulares) rendían peor que las posiciones absolutas.
- Tamaño: unos **80 M de parámetros**, entrenado desde cero para cada tarea; unas **5 h en una RTX 2080 Ti** (11 GB);
  inferencia de ~0,01 s.

### 3.3 Temporal ensembling

- Se consulta la política **en cada paso**; cada paso t recibe varias predicciones (de los chunks lanzados en t, t-1,
  t-2...). Se promedian con pesos w_i = exp(−m·i), donde w_0 corresponde a la predicción **más antigua**; una m menor
  incorpora antes las observaciones nuevas (A, algoritmo 2).
- No es un suavizado normal (que mezclaría acciones de pasos vecinos y sesgaría el resultado): promedia predicciones
  **del mismo paso**. No cuesta nada en entrenamiento, solo más inferencia.
- El artículo no da el valor de m. En el código original es **0,01** (`k = 0.01` en `imitate_episodes.py`), y LeRobot
  lo menciona en `temporal_ensemble_coeff` (por defecto `None` = desactivado; si se activa, `n_action_steps` debe ser 1).

### 3.4 Hiperparámetros del artículo (tabla III)

| Parámetro | Valor | En LeRobot (`main`) |
|-----------|-------|---------------------|
| learning rate | 1e-5 | `optimizer_lr = 1e-5` (backbone 1e-5, weight decay 1e-4) |
| batch size | 8 | se fija al entrenar |
| capas del encoder | 4 | `n_encoder_layers = 4` |
| capas del decoder | 7 | `n_decoder_layers = 1` (por un error del código original solo se usaba la primera capa; LeRobot reproduce ese comportamiento) |
| feedforward | 3200 | 3200 |
| dimensión oculta | 512 | `dim_model = 512` |
| cabezas | 8 | 8 |
| **chunk size** | **100** | `chunk_size = 100`, `n_action_steps = 100` |
| **β (kl weight)** | **10** | `kl_weight = 10` |
| dropout | 0,1 | 0,1 |
| latente z | 32 | `latent_dim = 32` |
| backbone | ResNet18 | ResNet18 con pesos de ImageNet |

El README original propone para simulación `--num_epochs 2000` (éxito de ~90 % en transfer cube y ~50 % en inserción),
y para datos reales **al menos 5.000 épocas o 3-4 veces lo que tarda la pérdida en estabilizarse**.

### 3.5 Datos

- 6 tareas reales bimanuales (abrir una bolsa zip, meter una pila, abrir un vasito de salsa, enhebrar una brida de
  velcro, preparar cinta adhesiva, poner un zapato) y 2 simuladas (pasar un cubo, inserción bimanual).
- **50 demostraciones por tarea** (100 en Thread Velcro). Cada episodio dura **8-14 s → 400-700 pasos a 50 Hz**.
  Total: 10-20 min de datos por tarea, pero **30-60 min de reloj** por los reinicios y los errores del operador.
- La posición inicial del objeto varía a lo largo de una línea de **15 cm** (reales) o en regiones 2D (simulación).
- Todas las demostraciones reales las grabó una sola persona, y aun así son estocásticas: por ejemplo, el punto de
  entrega de la cinta en el aire cambia en cada episodio.
- En simulación grabaron 50 demos "scripted" (deterministas) y 50 humanas, todas con éxito.

### 3.6 Resultados

Éxito final (%), con 25 evaluaciones por tarea real y 3 semillas × 50 en simulación (tablas I y II):

| Tarea | ACT | Mejor línea base |
|-------|-----|------------------|
| Cube Transfer (sim) programada / humana | 86 / 50 | BeT 27 / 1 |
| Bimanual Insertion (sim) programada / humana | 32 / 20 | BeT 3 / 0 |
| Slide Ziploc (real) | 88 | 0 |
| Slot Battery (real) | 96 | 0 |
| Open Cup (real) | 84 | 0 (BeT) |
| Thread Velcro (real) | 20 | 0 (BeT) |
| Prep Tape (real) | 64 | 0 (BeT) |
| Put On Shoe (real) | 92 | 0 (BeT) |

- Las líneas base (BC-ConvMLP, BeT, RT-1, VINN) avanzan en las primeras subtareas, pero se quedan por debajo del 30 %
  al final. Los autores lo atribuyen al error acumulado y al comportamiento no markoviano: el comportamiento empeora hacia
  el final del episodio y el robot "puede quedarse parado indefinidamente" en ciertos estados.
- Todos los métodos empeoran al pasar de datos programados a datos humanos, que son más estocásticos y multimodales.
- **Por qué falla Thread Velcro** (20 %): la pinza se cierra antes de tiempo, o la inserción no es lo bastante
  precisa. En ambos casos la causa es la **percepción**: brida negra sobre mesa negra, con poco contraste y ocupando poca
  área en la imagen.
- Tareas que ACT **no** aprendió (apéndice F): desenvolver caramelos (coge 10/10, tira de los extremos 8/10, desenvuelve
  0/10, por la percepción y la falta de datos) y abrir una bolsa zip tumbada (pequeñas diferencias al cogerla cambian
  mucho la deformación). Los autores proponen como soluciones preentrenamiento, más datos y mejor percepción.

### 3.7 Ablaciones: qué importa

1. **Chunking** (fig. 8a, sin temporal ensembling): el éxito medio en 4 configuraciones pasa del **1 % con k = 1 al
   44 % con k = 100**, y baja ligeramente con k = 200 y 400 (casi bucle abierto). Añadir chunking a BC-ConvMLP y a VINN
   también los mejora: es una técnica general.
2. **Temporal ensembling** (fig. 8b): **+3,3 %** para ACT y +4 % para BC-ConvMLP; **empeora** VINN, que es no
   paramétrico. Según los autores, ayuda a suavizar errores de modelado. La mejora es modesta.
3. **CVAE** (fig. 8c): con datos programados casi no cambia nada; con **datos humanos, quitar el CVAE hace caer el
   éxito del 35,3 % al 2 %**. Es imprescindible con demostraciones humanas ruidosas.
4. **Frecuencia** (estudio con 6 personas): teleoperar a 5 Hz en vez de 50 Hz hace las tareas un **62 % más lentas**
   (enhebrar brida: 33 s frente a 20 s; separar vasos: 16 s frente a 10 s; p < 0,001).
5. Además (§IV-C): L1 mejor que L2; posiciones absolutas mejor que deltas.

### 3.8 Consejos prácticos del autor ("ACT tuning tips" y README)

- "Si tu política ACT da tirones o se para a mitad de episodio, **entrena más**": el éxito y la suavidad mejoran
  mucho después de que la pérdida se estabilice.
- **El chunk size es el parámetro más importante**: un chunk debería corresponder a **~1 s de movimiento real**.
  (Ojo: en el artículo, 100 pasos a 50 Hz = 2 s.)
- KL weight alto (10 o 100), o entrenar sin el codificador del CVAE.
- Probar a **quitar el temporal ensembling** y ejecutar el chunk entero.
- Batch lo más grande posible, subiendo el learning rate en proporción (p. ej. batch 64 con lr 5e-5 frente a batch 8
  con lr 1e-5).
- Backbones separados por cámara (requiere cambiar el código).
- L1 > L2; posición absoluta > delta/velocidad ("más difícil recuperarse").
- **Probar varios checkpoints**.
- En el robot real: entrenar todavía más (**"5k-8k steps"**, sobre todo con varias cámaras; el README habla de
  épocas, así que la unidad no está clara). Si la inferencia es lenta y el robot se mueve despacio, desactivar el
  temporal ensembling y consultar con menos frecuencia (llegaron a cada 20 pasos).

---

## 4. Diffusion Policy

### 4.1 Idea

- La política es un **modelo de difusión condicional** (DDPM): parte de una secuencia de acciones con ruido gaussiano
  y la "limpia" en K iteraciones con una red que predice el ruido, condicionada a la observación. Cada iteración
  equivale a un paso de descenso por gradiente sobre una energía aprendida (B §2).
- Se entrena con un MSE entre el ruido añadido y el predicho; no hay que estimar constantes de normalización, y por
  eso es **estable** (a diferencia de Implicit BC / modelos de energía).
- Tres horizontes (B §2.3): observa los últimos **To** pasos (típicamente 2), predice **Tp** (16) y ejecuta **Ta**
  (8) antes de volver a planificar (*receding horizon*). Un Ta de 8 fue óptimo en la mayoría de tareas: más largo
  reacciona tarde, más corto pierde coherencia.
- La imagen es **condición**, no parte de lo que se genera: el codificador visual se ejecuta una vez por inferencia,
  no en cada iteración.
- Dos redes: **CNN 1D con FiLM** (recomendada para empezar: funciona casi sin ajustar) y **transformer** (mejor cuando
  las acciones cambian rápido, pero más sensible a los hiperparámetros).
- Visión: una ResNet18 por cámara **sin preentrenar**, con *spatial softmax* y GroupNorm, entrenada de extremo a
  extremo. Con codificadores congelados (ImageNet, R3M) rinde peor; ajustar uno preentrenado con un learning rate 10
  veces menor da lo mejor (ViT-B/16 de CLIP: 98 % en Square).

### 4.2 Ventajas frente a ACT y otros

- **Multimodalidad real**: si hay dos maneras válidas (empujar la T por la izquierda o por la derecha), aprende las
  dos y **se compromete con una en cada ejecución**. LSTM-GMM e IBC se sesgan hacia un lado y BeT no se compromete
  (B §4.1, fig. 3). ACT trata la variabilidad con el CVAE, pero en inferencia usa z = 0, es decir, una sola salida
  determinista "media". **[Inferencia mía, no una comparación directa de las fuentes: los artículos no se comparan
  entre sí]**.
- **Control de posición** mejor que de velocidad (como en ACT), y robusto a una **latencia** de hasta 4 pasos.
- Robusto a **pausas** en las demostraciones: no hace falta filtrarlas.
- Hiperparámetros **estables entre tareas**: las tareas reales de salsa usaron los mismos parámetros que Push-T y
  funcionaron "al primer intento"; las bimanuales funcionaron sin ajustar.

### 4.3 Coste de inferencia

- 100 iteraciones de difusión en entrenamiento; con **DDIM, 10 iteraciones en inferencia → 0,1 s de latencia en una
  RTX 3080** (B §3.4). En las tareas reales usaron 16 iteraciones.
- Los autores reconocen como limitación un coste y una latencia mayores que los de métodos simples, que el chunking
  compensa solo en parte; "puede no bastar" para control a alta frecuencia (B §9).
- Comparación: ACT ~0,01 s por inferencia en una 2080 Ti. **No hay datos de CPU en ninguna de las dos fuentes.**

### 4.4 Resultados reales

| Tarea (robot) | Demos | Diffusion Policy | Línea base |
|---------------|-------|------------------|------------|
| Push-T real (UR5) | 136 | 95 % éxito, IoU 0,80 (humano 0,84) | LSTM-GMM 20 %, IBC 0 % |
| Girar taza 6-DoF | 250 | 90 % (20 pruebas) | LSTM-GMM 0 % |
| Verter salsa / extender salsa (Franka) | 90 / 90 | cobertura 0,74 / 0,77 (humano 0,79) | LSTM-GMM 0 % |
| Batidora bimanual | 210 | 55 % | — |
| Desenrollar esterilla bimanual | 162 | 75 % | — |
| Doblar camiseta bimanual | 284 | 75 % | — |

- Simulación: mejora media del **46,9 %** sobre el estado del arte en 15 tareas de 4 benchmarks.
- Control a **10 Hz**, interpolado a 125 Hz en el robot. Demostraciones con SpaceMouse (Push-T), realidad virtual o
  dispositivos hápticos (bimanual). En la batidora, sin retroalimentación háptica el experto no completó **ninguna** de
  10 demostraciones; con ella, 10 de 10.
- Fallos típicos: agarres fallidos de los que la política no se recupera y se queda repitiendo; posiciones iniciales
  fuera de la distribución; no saber cuándo parar de ajustar.

### 4.5 Cuándo elegir cada uno (síntesis mía a partir de A y B)

- **ACT**: comportamiento unimodal y repetible (siempre la misma estrategia), muchas cámaras, alta frecuencia (50 Hz) y
  poca capacidad de cálculo en inferencia. Está muy probado en brazos baratos con guía y seguidor, como el nuestro.
- **Diffusion Policy**: demostraciones con varias estrategias válidas (varios operadores o varias formas de agarrar),
  tareas con fases ambiguas, y cuando se quiere poco ajuste de hiperparámetros. Requiere GPU para ir rápido y suele
  usarse a frecuencias más bajas (10 Hz).

---

## 5. Tabla comparativa

| Aspecto | ACT (A) | Diffusion Policy (B) | VLA (RT-1/RT-2/OpenVLA según A y C; SmolVLA no está en estas fuentes) |
|---------|---------|----------------------|------------------------------------------------------------------------------|
| Tipo de salida | Chunk continuo de k acciones (CVAE, z = 0 en inferencia) | Secuencia continua obtenida eliminando ruido | RT-1/RT-2/OpenVLA: **acciones discretizadas** en 256 bins por dimensión (C); RT-1 predice una sola acción a partir de un historial (A) |
| Multimodalidad | Parcial (el CVAE absorbe el ruido humano; salida determinista) | Sí, explícita | Sí, por la discretización, a costa de perder la estructura continua (C) |
| Condicionado por lenguaje | No (una política por tarea) | No en el artículo | Sí (es su razón de ser) |
| Frecuencia en los artículos | 50 Hz | 10 Hz | RT-1 ~5 Hz según ACT ("frecuencia similar a trabajos recientes") **[no verificado en la fuente original]** |
| Inferencia | ~0,01 s (RTX 2080 Ti) | ~0,1 s con DDIM a 10 pasos (RTX 3080) | No medido en estas fuentes |
| Datos por tarea | 50 demos (10-20 min) | 90-284 demos en las tareas reales | No cubierto aquí |
| Entrenamiento | ~5 h por tarea en una GPU, desde cero | 3.000 épocas (imagen); recomiendan empezar con la CNN | Preentrenamiento masivo + ajuste fino **[no verificado aquí]** |
| Precisión fina | Su punto fuerte (80-96 % en 4 de las 6 tareas reales) | Alta en Push-T, con IoU cercano al humano | En ACT, RT-1 se queda en 0 % en las tareas reales finas |
| Visión | ResNet18 (ImageNet en LeRobot), 4 cámaras | ResNet18 sin preentrenar, de extremo a extremo; ajustar uno preentrenado es lo mejor | ViT preentrenados (C) |

---

## 6. Lecciones concretas para LeWelder

### 6.1 Cuántas demostraciones

- Referencia del artículo: **50 demos por tarea** bastan para tareas finas con un 80-96 % de éxito, si el operador es
  bueno y la variación inicial es limitada (15 cm en una línea). Para la tarea más difícil usaron 100 y aun así
  obtuvieron un 20 %. Diffusion Policy usó entre 90 y 284 en tareas reales.
- Presupuesto de tiempo: 10-20 min de datos útiles costaron **30-60 min de reloj**. En 48 h es asumible grabar
  50-100 demos por tarea si un operador se especializa.
- Nuestro dato de simulación (160 demos y 6.000 pasos en CPU → 10-14 mm de error) indica que **el número de demos
  probablemente no es el cuello de botella**. Mirar antes el entrenamiento (pocos pasos) y la percepción (ver 6.4).

### 6.2 Cómo grabar

- **Grabar la posición del brazo guía como acción**: LeRobot lo hace con guía y seguidor; conviene confirmar que el
  dataset guarda `action` = guía y `observation.state` = seguidor **[no verificado en LeRobot 0.7]**.
- **Posiciones articulares absolutas**, no deltas (A y tuning tips).
- **Cámaras**: al menos una en la muñeca y una fija. ACT usó 4. Foco fijo; la luz y el contraste importan mucho (el
  fallo de Thread Velcro fue un objeto negro sobre mesa negra). **Nuestra chapa y la base deben contrastar con la mesa.**
  Para el cordón de soldadura: marcarlo con buen contraste o iluminarlo.
- **Frecuencia alta** de teleoperación: a 50 Hz se teleopera un 62 % más rápido que a 5 Hz. La frecuencia por defecto
  de grabación de LeRobot con el SO-101 suele ser 30 fps **[no verificado en estas fuentes]**; el chunk debe medirse
  en pasos a esa frecuencia (~1 s → ~30 pasos si se sigue el consejo del autor; 100 pasos ≈ 3,3 s).
- Sesiones largas cansan: ALOHA añadió compensación de gravedad para aguantar más de 30 min. Turnos de operador.
- Usar las mismas condiciones de cámara y luz en la grabación y en la demo final.

### 6.3 Consistencia

- **Un solo operador por tarea** si es posible: la imitación funciona mejor con un experto que con varios (D §5.2,
  citando a Camacho y Michie 1995).
- Misma estrategia siempre (misma aleta, mismo sentido de giro de 90°, misma secuencia). ACT es determinista en
  inferencia: con dos estrategias mezcladas tenderá a promediarlas, y el CVAE solo amortigua ese efecto. Si hubiera
  que mezclar estrategias, eso favorecería a Diffusion Policy.
- **Variar la posición inicial** de forma controlada (en ACT, a lo largo de 15 cm) para cubrir la zona de la demo en
  vivo, pero sin salir de ella en la evaluación: los fallos de Diffusion Policy en la batidora venían de posiciones
  iniciales fuera de la distribución.
- Las pausas a mitad de episodio no son graves con chunking, pero es mejor evitarlas.

### 6.4 Por qué falla en precisión (nuestros 10-14 mm frente al objetivo de ±5 mm)

Hipótesis ordenadas según las fuentes:
1. **Entrenamiento corto**. 6.000 pasos en CPU está por debajo de lo que recomienda el autor para datos reales y muy
   por debajo de las 2.000-5.000 épocas del README. "Train for very long": la precisión y la suavidad mejoran después de
   que la pérdida se estabilice. **Es lo primero que hay que probar, con GPU.**
2. **Chunk size mal ajustado** a la frecuencia: con 100 pasos a 30 fps, el robot ejecuta ~3 s en bucle abierto. Probar
   ~30 pasos (≈ 1 s) y/o activar el temporal ensembling (`temporal_ensemble_coeff = 0.01`, `n_action_steps = 1`).
3. **Percepción**: el cordón de 12 cm a ±5 mm es una tarea de seguimiento visual fino; si la cámara no ve bien la línea
   (contraste, resolución, oclusión por la pinza), ninguna arquitectura lo arreglará (lección de Thread Velcro). Cámara
   de muñeca orientada hacia la punta.
4. **Precisión del hardware**: ALOHA tiene 5-8 mm de precisión absoluta y aun así hace tareas milimétricas **gracias a
   la realimentación visual en bucle cerrado**. La precisión no viene de la cinemática, sino de cerrar el bucle con la
   imagen.
5. **Checkpoint**: probar varios, no solo el último ni solo el de menor pérdida de validación.
6. Batch más grande con el learning rate escalado (64 / 5e-5).

Para el cordón, el **replay** de una trayectoria grabada (o generada por cinemática) es más fiable si la pieza está
siempre en la misma posición: ninguna de las fuentes da evidencia de que BC alcance ±5 mm de forma repetible en
seguimiento de trayectorias. **[Recomendación mía.]**

### 6.5 Recuperaciones y el recolector programado

- **Lección clave de la ablación del CVAE**: con datos *programados* (deterministas), ACT funciona igual con o sin
  CVAE, y el éxito con datos programados es **mucho mayor** que con datos humanos (cubo: 86 % frente a 50 %; inserción:
  32 % frente a 20 %). Nuestro recolector programado (cinemática + ArUco) debería dar datos muy consistentes y, por
  tanto, fáciles de imitar.
- Riesgo: los datos programados son demasiado "perfectos" y no muestran **recuperaciones**. Pomerleau ya lo advertía:
  hay que enseñar cómo volver al centro del carril. Qué probar con el recolector:
  1. **Aleatoriedad en la posición inicial** de la pieza y del brazo (ya prevista).
  2. **Perturbaciones deliberadas con corrección**: el script se desvía unos milímetros a mitad de trayectoria y
     corrige guiándose por ArUco. Así se generan estados "fuera de la trayectoria ideal" etiquetados con la acción
     correcta. Es una versión offline de la idea de DAgger. ACT avisa de que el ruido puede romper las tareas finas:
     inyectarlo en fases de aproximación, no en el momento del agarre o de la inserción.
  3. **DAgger ligero**: tras un primer entrenamiento, ejecutar la política, ver dónde se desvía, y que el recolector
     programado (que "sabe" la respuesta correcta gracias a ArUco) grabe demostraciones que empiecen desde esos
     estados. Es justo el bucle de DAgger con un experto automático, sin el coste de la anotación humana.
  4. Mezclar demos programadas y teleoperadas con cuidado: los datos humanos son más multimodales, y en ACT empeoraron
     todos los métodos. Medir por separado (solo programadas, solo humanas, mezcla).
- Mantener el **mismo espacio de acciones** (posiciones articulares absolutas a la misma frecuencia) en ambos tipos de
  demostración, y que el recolector programado produzca movimientos de velocidad parecida a los humanos.

### 6.6 Para los dos miembros que no han usado LeRobot

- Las ideas mínimas: (1) BC = aprendizaje supervisado de observación → acción; (2) el enemigo es el error acumulado;
  (3) el chunking lo reduce; (4) los datos (consistencia, cámaras, contraste) importan más que la arquitectura; (5) hay
  que entrenar mucho y probar varios checkpoints en el robot.

---

## 7. Lo que no está claro o no he podido verificar

- **Venue de ACT** (RSS 2023): no aparece en la página de arXiv; no verificado.
- **Valores por defecto de LeRobot 0.7**: he leído `configuration_act.py` de la rama `main`, no la etiqueta 0.7.
- **Bucle "5k-8k steps"** del documento de consejos: el README habla de épocas ("at least 5000 epochs"); no está claro
  si se refieren a pasos de optimización o a épocas. Con 50 episodios de 500 pasos y batch 8, una época son unos 3.000
  pasos, así que la diferencia es enorme. **Para LeRobot, que cuenta pasos, no tengo una cifra verificada.**
- **Chunk de ~1 s (consejo) frente a 2 s (artículo, 100 pasos a 50 Hz)**: no hay ablación en segundos; la ablación de k
  se hizo en simulación sin temporal ensembling.
- **Cota de error O(T²) de BC frente a O(T) de DAgger**: conocida, pero no aparece en las partes de Osa que he leído.
- **Frecuencia de RT-1 (~5 Hz)**: ACT lo insinúa al citar [7]; no lo he comprobado en el artículo de RT-1.
- **SmolVLA**: no aparece en ninguna de estas fuentes; nada de este documento lo compara directamente con ACT.
- **Tiempos en CPU**: ninguna fuente los da. Nuestro dato (6.000 pasos en CPU) no se puede contrastar con los
  artículos, que usan GPU (ACT ~5 h en una 2080 Ti).
- **Comparación directa ACT frente a Diffusion Policy**: ninguno de los dos artículos compara con el otro (son
  casi simultáneos). Las recomendaciones de "cuándo usar cada uno" son síntesis mía.
- **Capítulo de Tedrake**: las secciones de distribución, multimodalidad, chunking e IRL son esbozos sin contenido; no
  da números de demostraciones ni consejos de recogida de datos.
- **Osa**: solo he leído las secciones indicadas arriba, no las 179 páginas.
- La página del proyecto ALOHA y su tutorial de hardware no los he leído (solo el artículo, el README y el documento de
  consejos).
