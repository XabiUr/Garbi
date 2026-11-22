# Proyectos top de la comunidad Hugging Face / LeRobot

Fecha: 18-11-2026. Objetivo: aprender de los proyectos de robótica más destacados del ecosistema LeRobot
(no de hackathons) para el proyecto LeWelder (Hackathon LeRobot Bilbao II, 20-22 nov 2026, SO-101, demo en vivo,
pitch de 5 min).

## Método

- **Métricas** sacadas el 18-11-2026 de la API pública de Hugging Face (`/api/spaces`, `/api/models`,
  `/api/datasets`, orden `likes`, `downloads` y `trendingScore`). Las estrellas de GitHub se leyeron en la página de
  cada repositorio el mismo día (la API de GitHub estaba bloqueada en este entorno), así que son aproximadas.
- **Selección**: 12 aplicaciones o demostraciones con robot, más 3 referencias (modelo, dataset y simulador) que son
  la base de muchos proyectos. Se descartaron los Spaces de visualización o de organización de hackathons, aunque
  tengan muchos likes (p. ej. `lerobot/visualize_dataset`, 763 likes; `LeRobot-worldwide-hackathon/*`).
- **Valoración**: rúbrica del hackathon. Total = Σ(nota × peso) × 10. Lo que no he podido comprobar en una fuente no
  pasa de 5. Anclas: 10 = vídeo sin cortes con evidencia pública y excepcional; 7 = bueno y documentado; 5 = correcto o
  sin pruebas; 3 = flojo; 1 = nada.
- No he visto los vídeos: me baso en READMEs, entradas de blog y fichas. Donde algo viene solo de prensa o de terceros
  lo marco como [no verificado].

---

## 1. Aplicaciones y demostraciones

### Unfolding Robotics (doblado de camisetas) · Hugging Face (equipo LeRobot) · Space-blog + datasets + modelos · 162 likes, 2026 (Space creado el 11-02-2026)

- **Fuentes:** <https://huggingface.co/spaces/lerobot/robot-folding> (artículo interactivo en
  <https://lerobot-robot-folding.hf.space/>); el README de github.com/huggingface/lerobot lo cita como "T-Shirt Folding
  Experiment".
- **Qué hace:** una receta abierta de principio a fin (hardware, datos, entrenamiento, evaluación y despliegue) para que
  un robot bimanual doble camisetas. Publican los datos, los modelos y lo que salió mal.
- **Análisis técnico:**
  - Robot: dos OpenArm (Enactic) con el bíceps alargado 5 cm y pinzas propias. La teleoperación es con **OpenArm Mini**,
    brazos líderes impresos en 3D basados en el diseño del SO-101 (unos 120 € por brazo), que funcionaron mejor que los
    líderes caros de tamaño real.
  - Cámaras: tres, una de base gran angular y dos de muñeca. Solo encoders de articulación: sin fuerza, profundidad ni
    audio.
  - Datos: 5.688 episodios (unas 131 h, 14,1 M de frames) en 8 puestos en paralelo, con más de 25 camisetas y 8 fondos.
    Hay un subconjunto de alta calidad de 1.200 episodios (unas 30 h). Grabado a 30 fps.
  - Políticas: π0 y π0.5 ajustados desde checkpoints preentrenados. Técnicas: acciones relativas (como UMI), RTC
    (real-time chunking, que acelera la ejecución al menos 2x), modelo de recompensa SARM para puntuar y filtrar
    episodios, entrenamiento ponderado por recompensa (RABC) y DAgger con correcciones humanas.
  - Cómputo: 8 H100, más de 5.000 horas de GPU en decenas de entrenamientos, y unas 1.900 horas de ingeniería en total.
  - Todo lo motor es aprendido. Lo programado es la infraestructura: interpolación de 30 a 90 Hz, RTC, curación de datos
    y protocolo de evaluación.
- **Análisis de la aplicación:** doblar ropa es una tarea doméstica que todo el mundo entiende y que hoy no resuelve
  ningún producto barato. Se ve en un segundo. Momento memorable: un vídeo sin cortes de **15 minutos doblando sin
  intervención humana**.
- **Por qué destaca:** es el tercer Space con más likes de la búsqueda "lerobot" y el README de LeRobot lo destaca.
  El rigor es raro en la comunidad: 20 ejecuciones por experimento con intervalos de confianza de Clopper-Pearson.
  Pasaron del 40 % al **90 %** de éxito (100 % en el nivel 1 y 80 % en el nivel 2).
- **Valoración:**

  | Criterio | Peso | Nota | Por qué |
  |---|---|---|---|
  | Funciona en vivo y se recupera | 30 % | 9 | 15 min de vídeo sin cortes y un 90 % de éxito medido con intervalos de confianza. |
  | Dificultad técnica | 20 % | 10 | Bimanual con tela deformable, 131 h de datos, modelo de recompensa, RTC y DAgger. |
  | Utilidad práctica | 20 % | 8 | Problema doméstico real, aunque con hardware de unos miles de euros. |
  | Creatividad y momento memorable | 15 % | 7 | Doblar ropa es un clásico; lo memorable es la duración sin intervención. |
  | Facilidad de uso y presentación | 15 % | 8 | Blog interactivo con tablas claras y lecciones honestas. |
  | **Total** | | **85,5** | |

- **Replicabilidad en 48 h con SO-101:** baja. Requiere bimanual, cientos de horas de datos y miles de horas de GPU. Lo
  que sí se puede copiar en 48 h es el método: acciones relativas, curar datos y RTC.
- **Lección para LeWelder:** la calidad de los datos movió el éxito 50 puntos y los cambios de algoritmo solo entre 5 y
  20. Que todos los operadores graben con **la misma estrategia**, descartar los episodios malos, y grabar en vídeo cada
  evaluación.

### Prompting Robots with LeRobot (rollout interactivo y planificador externo) · Hugging Face · Space-blog · 9 likes, actualizado el 30-10-2026

- **Fuentes:** <https://huggingface.co/spaces/lerobot/language-conditioned-policies>,
  <https://lerobot-language-conditioned-policies.hf.space/>; Space hermano sobre anotación de lenguaje:
  <https://huggingface.co/spaces/lerobot/robots-that-talk> (11 likes).
- **Qué hace:** explica y demuestra cómo **dirigir un VLA con lenguaje en tiempo real** desde LeRobot. Con
  `lerobot-rollout --interactive=true` se cambian las instrucciones sin recargar el modelo ni reconectar el robot. Un
  VLM externo hace de planificador ("Sistema 2") y le dicta subtareas al VLA ("Sistema 1").
- **Análisis técnico:**
  - Comandos del modo interactivo: `/start`, `/subtask <texto>`, `/vqa <pregunta>`, `/autosteer <objetivo>`, `/reset`
    y `/stop`.
  - Grabaciones reales (28-09-2026) con π0.5 DROID: meter la manzana en el bol sin tocar el yogur, y redirigir **a
    mitad de movimiento** un bloque azul del rojo al amarillo. También hay una ejecución con DeepSeek Flash como
    planificador que recibe las cámaras exterior y de muñeca, e incluso un intento fallido de agarre y replanificación
    que publican tal cual.
  - Herramientas de entrenamiento: `lerobot-annotate` añade subtareas, planes, memoria y cajas a un dataset (171
    episodios en una hora en un portátil con RTX 3080). Las anotaciones van en las columnas `language_persistent` y
    `language_events`. G0.5 se ajustó con LoRA (10k pasos, una A100). En el artículo de FineART, entrenar con subtareas
    subió una tarea de desambiguación espacial del 32 % al 100 %.
  - Es aprendido el VLA y el planificador VLM preentrenado. Es programado el bucle planificador → VLA y la interfaz.
- **Análisis de la aplicación:** el usuario habla y el robot cambia de plan sin reiniciar. Momento memorable: corregir
  la instrucción **a mitad de movimiento** y que el brazo cambie de destino.
- **Por qué destaca:** es la guía oficial del equipo LeRobot (12 autores, entre ellos Thomas Wolf) sobre la función
  nueva más relevante para demos de VLA. Pocos likes porque es reciente.
- **Valoración:**

  | Criterio | Peso | Nota | Por qué |
  |---|---|---|---|
  | Funciona en vivo y se recupera | 30 % | 6 | Vídeos reales a tiempo real, pero sin tasa de éxito y con fallos mostrados. |
  | Dificultad técnica | 20 % | 8 | Planificador VLM, VLA, anotación automática y recetas de entrenamiento. |
  | Utilidad práctica | 20 % | 7 | Hace usable un VLA para alguien que no programa. |
  | Creatividad y momento memorable | 15 % | 7 | La redirección a mitad de movimiento es muy visual. |
  | Facilidad de uso y presentación | 15 % | 7 | Comandos simples y guía ilustrada. |
  | **Total** | | **69** | |

- **Replicabilidad en 48 h con SO-101:** alta para la parte de interfaz: `lerobot-rollout --interactive` ya existe en
  LeRobot y sirve con SmolVLA multitarea. Media si además se quiere un planificador VLM.
- **Lección para LeWelder:** nuestro "voz → tarea" es exactamente este patrón. Usar `/subtask` o el rollout
  interactivo en vez de un bucle hecho a mano. Ojo con el sesgo de datos: el artículo vio que el robot coge **el cubo
  más cercano aunque le pidas otro**, así que hay que grabar las juntas en órdenes y posiciones variadas.

### Steer a robot with words · Hugging Face (lerobot, clonado de SteeringStuff) · Space Gradio · 31 likes, creado el 15-10-2026

- **Fuentes:** <https://huggingface.co/spaces/lerobot/steer-a-robot> (README y DEVELOPMENT.md).
- **Qué hace:** demo en el navegador. Escribes un objetivo libre, Qwen3-VL (servido con vLLM) lo traduce a
  instrucciones del repertorio de MolmoAct2, y MolmoAct2 mueve un robot en una cocina simulada LIBERO.
- **Análisis técnico:** simulación LIBERO controlada por `lerobot-rollout`. El VLA es MolmoAct2-LIBERO-LeRobot y el
  planificador es Qwen3-VL-30B-A3B en un Inference Endpoint (A100, mínimo 1 réplica para que nadie espere un arranque
  en frío). La interfaz tiene un registro del razonamiento de la tarea, preguntas sobre la escena (VQA), una
  "biblioteca de habilidades" que resalta la instrucción activa, un botón de parada y 21 tests de regresión de la
  interfaz. Es aprendido el VLA y el VLM. Es programado la traducción de objetivo a habilidades y la interfaz.
- **Análisis de la aplicación:** cualquiera ve cómo una frase libre se convierte en pasos que el robot sabe hacer.
  Momento memorable: ver resaltarse en directo la habilidad que el planificador ha elegido.
- **Por qué destaca:** Space oficial reciente con *trending score* positivo. Es la vitrina del modo interactivo.
- **Valoración:**

  | Criterio | Peso | Nota | Por qué |
  |---|---|---|---|
  | Funciona en vivo y se recupera | 30 % | 5 | Es público, pero no lo he ejecutado y es simulación. |
  | Dificultad técnica | 20 % | 7 | Planificador VLM, VLA y despliegue con escalado. |
  | Utilidad práctica | 20 % | 5 | Cocina simulada: es didáctica, no resuelve una tarea real. |
  | Creatividad y momento memorable | 15 % | 7 | La biblioteca de habilidades visible explica bien el sistema. |
  | Facilidad de uso y presentación | 15 % | 8 | Navegador, ejemplos de objetivos y estados de color claros. |
  | **Total** | | **61,5** | |

- **Replicabilidad en 48 h con SO-101:** media. La interfaz es copiable. El planificador grande necesita GPU o
  endpoint, y con SmolVLA multitarea basta un LLM pequeño que elija entre 3 o 4 tareas.
- **Lección para LeWelder:** mostrar en pantalla **qué tarea ha entendido el sistema** (la habilidad resaltada) antes de
  que el brazo se mueva. Hace legible la voz para el jurado y para el alumno.

### XLeRobot · Vector-Wangel (Gaotian Wang) · repo GitHub · ~5,8k estrellas, 632 forks (desde 2025)

- **Fuentes:** <https://github.com/Vector-Wangel/XLeRobot>, <https://xlerobot.readthedocs.io>; artículo en Hackaday
  (03-11-2025):
  <https://hackaday.com/2025/11/03/dual-arm-mobile-bot-built-on-ikea-cart-costs-hundreds-not-thousands>.
- **Qué hace:** robot doméstico móvil de dos brazos y bajo coste, montado sobre un carrito de IKEA con dos brazos
  SO-100/SO-101. Cuesta desde unos 660 $ y se monta en menos de 4 horas.
- **Análisis técnico:**
  - Hardware: se basa en LeRobot, SO-100/101, LeKiwi y Bambot. La base diferencial salió el 02-12-2025. La cámara de
    cabeza es RGB y se puede cambiar por estéreo (+30 $) o RealSense RGB-D (+220 $); opcionalmente una Raspberry Pi.
  - Control: teclado, mando Xbox, Joy-Con de Switch por Bluetooth y Quest 3 (VR).
  - Inteligencia: tutorial provisional de VLA (11-11-2025), RL sim-to-real y demo de MuJoCo/3DGS en el navegador
    (29-01-2026). La página no menciona ni LLM ni voz.
  - La mayor parte de las demos de tareas domésticas son teleoperadas [no verificado cuánta autonomía hay en cada GIF].
- **Análisis de la aplicación:** un "mayordomo" de bajo coste. Momento memorable: un carrito de IKEA con dos brazos
  haciendo tareas de casa.
- **Por qué destaca:** es el proyecto comunitario sobre LeRobot con más estrellas que he encontrado (unas 5,8k). Tiene
  kit comercial con Wowrobo (579 $), artículo en arXiv y fue mentor en un hackathon de SEEED, NVIDIA y Hugging Face.
- **Valoración:**

  | Criterio | Peso | Nota | Por qué |
  |---|---|---|---|
  | Funciona en vivo y se recupera | 30 % | 7 | Muchas demos en vídeo y GIF, pero sobre todo teleoperadas. |
  | Dificultad técnica | 20 % | 8 | Integra base móvil, dos brazos, VR, simulación y RL. |
  | Utilidad práctica | 20 % | 8 | Plataforma doméstica asequible que se usa en investigación. |
  | Creatividad y momento memorable | 15 % | 7 | La estética "carrito de IKEA" se recuerda. |
  | Facilidad de uso y presentación | 15 % | 7 | Documentación, kit y vídeo de montaje. |
  | **Total** | | **74** | |

- **Replicabilidad en 48 h con SO-101:** baja. El montaje de hardware solo ya come buena parte del tiempo, y la
  autonomía es limitada.
- **Lección para LeWelder:** el coste y la claridad del montaje venden. En el pitch, dar **el precio total del puesto**
  (SO-101 + antorcha LED + cámara) frente a un simulador de soldadura comercial [precio a verificar].

### LeKiwi · SIGRobotics-UIUC · repo GitHub (robot con soporte oficial en LeRobot) · ~1,5k estrellas, 167 forks

- **Fuentes:** <https://github.com/SIGRobotics-UIUC/LeKiwi>; soporte en la lista de hardware del README de
  <https://github.com/huggingface/lerobot>.
- **Qué hace:** manipulador móvil de bajo coste: un brazo SO-101 sobre una base holonómica de tres ruedas omni.
- **Análisis técnico:** Raspberry Pi 5 que envía datos al portátil, una cámara de escena y una de muñeca, batería de 12 V
  o *power bank* de 5 V. Se teleopera con brazo líder más WASD o mando, y tiene canal de captura de datos para
  imitación. Las políticas son las estándar de LeRobot (ACT, SmolVLA...). Hay variante Dynamixel con Koch.
- **Análisis de la aplicación:** acerca la manipulación a la casa: el brazo va adonde está el objeto. Momento
  memorable: el robot cruza la mesa y recoge algo.
- **Por qué destaca:** robot oficial de LeRobot, base de XLeRobot y de muchos proyectos, y uno de los robots de
  Bilbao I según `analisis-concursos.md`.
- **Valoración:**

  | Criterio | Peso | Nota | Por qué |
  |---|---|---|---|
  | Funciona en vivo y se recupera | 30 % | 6 | Soporte oficial y muy usado; no he visto demos autónomas largas documentadas. |
  | Dificultad técnica | 20 % | 6 | La integración de base y brazo es moderada. |
  | Utilidad práctica | 20 % | 7 | La movilidad abre tareas reales. |
  | Creatividad y momento memorable | 15 % | 5 | Es plataforma, no aplicación. |
  | Facilidad de uso y presentación | 15 % | 7 | Lista de materiales y guía oficial de LeRobot. |
  | **Total** | | **62** | |

- **Replicabilidad en 48 h con SO-101:** media si se lleva montado. No aplica a nuestra mesa fija.
- **Lección para LeWelder:** la movilidad no hace falta. Mejor una mesa fija y bien iluminada, que es justo donde
  SmolVLA es fiable.

### Reachy Mini Conversation App · Pollen Robotics / Hugging Face · Space (app de Reachy Mini) · 193 likes, creado el 16-10-2025

- **Fuentes:** <https://huggingface.co/spaces/pollen-robotics/reachy_mini_conversation_app>; blog
  <https://huggingface.co/blog/reachy-mini>; tienda de apps (mayo de 2026): Axios
  <https://axios.com/2026/05/06/hugging-face-consumer-robot-app-store>, VentureBeat.
- **Qué hace:** convierte el Reachy Mini en un compañero que conversa con voz en tiempo real, ve con la cámara, tiene
  personalidades, memoria y herramientas, y acompaña el habla con baile, emociones y movimientos.
- **Análisis técnico:**
  - Backend de voz en tiempo real de Hugging Face (o local con `speech-to-speech`). VAD local con Silero y
    *barge-in*, es decir, poder interrumpirle.
  - Sistema de movimiento en capas: los movimientos principales (bailes, emociones, poses, respiración) van en cola, y
    encima se mezcla un balanceo que reacciona al habla.
  - Herramientas asíncronas: mover, capturar cámara y llamar a herramientas MCP en Spaces. Interfaz web opcional con
    transcripción y latencias por turno. Memoria a largo plazo con `remember` y `forget`.
  - No hay política aprendida de manipulación. Es aprendido el LLM, el STT, el TTS y la visión. Es programado todo el
    movimiento (coreografías y mezcla).
- **Análisis de la aplicación:** robot de escritorio con el que hablar y que reacciona con gestos. Momento memorable:
  el robot baila y gesticula mientras te contesta, y le puedes interrumpir.
- **Por qué destaca:** es la app de referencia del Reachy Mini. La tienda abrió con más de 200 apps y unas 10.000
  unidades vendidas [no verificado, cifra de prensa citando a Clément Delangue].
- **Valoración:**

  | Criterio | Peso | Nota | Por qué |
  |---|---|---|---|
  | Funciona en vivo y se recupera | 30 % | 7 | Producto oficial en miles de unidades, con *barge-in* y modo sueño. |
  | Dificultad técnica | 20 % | 7 | Voz en tiempo real, mezcla de movimientos, herramientas y memoria. |
  | Utilidad práctica | 20 % | 6 | Compañía y entretenimiento, sin tarea física. |
  | Creatividad y momento memorable | 15 % | 8 | Personalidad y baile que encantan al público. |
  | Facilidad de uso y presentación | 15 % | 9 | Sin clave de API por defecto, interfaz web y app móvil. |
  | **Total** | | **72,5** | |

- **Replicabilidad en 48 h con SO-101:** media para la capa de voz (`speech-to-speech` o un STT y TTS local). La parte
  de movimiento expresivo no aplica igual a un brazo.
- **Lección para LeWelder:** la voz debe **dejarse interrumpir** y el robot debe "dar señales de vida" mientras
  escucha (pequeño movimiento o LED). Un brazo quieto mientras procesa parece colgado.

### Reachy Phone Home · itsMarco-G · Space (app de Reachy Mini) · 372 likes, creado el 03-02-2026

- **Fuentes:** <https://huggingface.co/spaces/itsMarco-G/reachy_phone_home>.
- **Qué hace:** un compañero para concentrarte. Reachy vigila si coges el móvil y te anima o te riñe con movimientos y
  frases para que vuelvas al trabajo.
- **Análisis técnico:** cámara del Reachy Mini con detección YOLO26 de teléfono y persona. Hay contadores de "latidos"
  que disparan movimientos y audios pregrabados (`angry_reachy.mp3`, `happy_reachy.mp3`...), con ElevenLabs para la voz
  [no verificado en el código, lo dice una ficha secundaria]. Interfaz web en el puerto 8088 accesible desde el móvil.
  Todo es programado salvo el detector.
- **Análisis de la aplicación:** problema universal (la distracción con el móvil), usuario cualquiera. Momento
  memorable: el robot se enfada cuando coges el móvil.
- **Por qué destaca:** es **el Space con más likes de las búsquedas "reachy" y "lerobot"** si excluimos los de
  visualización y tutorial (372 likes). Ha inspirado clones ("Judgy Reachy No Phone", 37 likes; "Focus Guardian").
- **Valoración:**

  | Criterio | Peso | Nota | Por qué |
  |---|---|---|---|
  | Funciona en vivo y se recupera | 30 % | 5 | GIF de detección; no he visto un vídeo largo. |
  | Dificultad técnica | 20 % | 4 | YOLO, temporizadores y movimientos programados. |
  | Utilidad práctica | 20 % | 5 | Útil para hábitos, pero no imprescindible. |
  | Creatividad y momento memorable | 15 % | 8 | Un robot que te riñe por el móvil se entiende y hace reír. |
  | Facilidad de uso y presentación | 15 % | 8 | Instalación de un clic y control desde el móvil. |
  | **Total** | | **57** | |

- **Replicabilidad en 48 h con SO-101:** alta (YOLO y respuestas programadas), pero la idea no encaja con un brazo.
- **Lección para LeWelder:** la popularidad la da una **reacción emocional simple y legible**, no la complejidad. El
  "momento memorable" puede ser una reacción del robot al resultado del alumno (celebrar una buena soldadura).

### Baby Reachy-Mini Companion · ravediamond · Space Gradio (app de Reachy Mini) · 179 likes, creado el 05-02-2026

- **Fuentes:** <https://huggingface.co/spaces/ravediamond/baby-reachy-mini-companion> y su repo de GitHub enlazado.
- **Qué hace:** compañero 100 % local para bebés y niños. Si el bebé llora, el robot lo calma meciéndose y hablando y
  envía una foto a los padres por Signal. También avisa de objetos peligrosos, cuenta cuentos y enseña.
- **Análisis técnico:** 7 modelos en local:
  - Silero VAD, Faster-Whisper (STT), Kokoro (TTS) y YAMNet para detectar el llanto.
  - YOLO v26n para peligros y seguimiento de caras.
  - Ministral 3B o Qwen 3B para razonar con llamadas a herramientas, y Qwen3-VL 4B para preguntas visuales.

  Corre en un Mac con Ollama o en una Jetson Orin NX de 700 $ (unos 3 s de extremo a extremo frente a 6 s en el Mac).
  Decisión clave: **las alertas de seguridad no pasan por el LLM**, se envían en código, porque "los modelos pequeños no
  encadenan bien 3 o más llamadas a herramientas". Tiene CI con tests, ruff y comprobación de tipos.
- **Análisis de la aplicación:** necesidad emocional fuerte (padres), privacidad como argumento. Momento memorable:
  llora el bebé, el robot lo calma y al móvil del padre llega la foto.
- **Por qué destaca:** 179 likes, cuarto entre las apps de Reachy. La historia personal ("lo construí para mi hijo")
  está muy bien contada.
- **Valoración:**

  | Criterio | Peso | Nota | Por qué |
  |---|---|---|---|
  | Funciona en vivo y se recupera | 30 % | 5 | Hay GIFs de cada función, pero no lo he podido comprobar sin cortes. |
  | Dificultad técnica | 20 % | 8 | 7 modelos locales orquestados con herramientas y Jetson. |
  | Utilidad práctica | 20 % | 7 | Problema real para familias, con privacidad. |
  | Creatividad y momento memorable | 15 % | 8 | La cadena llanto → calma → foto es muy narrativa. |
  | Facilidad de uso y presentación | 15 % | 7 | README ejemplar, aunque la instalación es larga. |
  | **Total** | | **67,5** | |

- **Replicabilidad en 48 h con SO-101:** media. La pila de voz local se puede copiar tal cual.
- **Lección para LeWelder:** separar lo que decide el LLM (qué decir, qué tarea elegir) de lo que **tiene que pasar
  siempre** (paradas de seguridad, puntuación), que debe ir en código determinista. Es nuestra arquitectura voz → tarea
  con una red de seguridad.

### FLUX 3 Action SO-101 · Black Forest Labs (y demo de multimodalart) · modelo + Space · 65 likes y 999 descargas (modelo SO-101), base con 172 likes; lanzado el 23-09-2026

- **Fuentes:** <https://huggingface.co/black-forest-labs/flux-3-action-so101> (con acceso restringido),
  <https://huggingface.co/spaces/multimodalart/flux-3-action-so101-sim>; prensa: DeepLearning.AI The Batch
  (<https://www.deeplearning.ai/the-batch/video-models-steer-robots>), VentureBeat; el README de LeRobot lo lista como
  "world model".
- **Qué hace:** "world action model" abierto de 7.000 M de parámetros, procedente de un modelo de vídeo. Con una versión
  específica para SO-101, recibe imágenes, estado e instrucción y devuelve trozos de acciones. El Space lo prueba en
  bucle cerrado con un SO-101 simulado en MuJoCo.
- **Análisis técnico:**
  - Según la prensa: predice 42 acciones, ejecuta 32 a 30 Hz y replanifica. Entrenado con episodios SO-101 del
    LeRobot Community Dataset v3. El pick-and-place salió con unas 200 demostraciones [no verificado en la ficha, que
    está restringida].
  - El Space corrige la normalización: usa la mediana de cuantiles de los datasets SO-10x con calibración nueva, y dice
    que así predice episodios reales unas 2 veces mejor offline. Usa kernels AoTI en ZeroGPU.
  - Aviso de seguridad: la salida no está recortada, hay que imponer límites de articulación en el robot.
- **Análisis de la aplicación:** modelo base, no aplicación. Su valor es que el SO-101 tenga un modelo grande dedicado.
- **Por qué destaca:** de los modelos LeRobot más recientes es el que tiene más likes, después de SmolVLA y π0, y tuvo
  mucha prensa.
- **Valoración:**

  | Criterio | Peso | Nota | Por qué |
  |---|---|---|---|
  | Funciona en vivo y se recupera | 30 % | 5 | Demo en simulación; los resultados reales solo los he visto en prensa. |
  | Dificultad técnica | 20 % | 9 | Modelo de 7B que viene de vídeo, con kernels optimizados. |
  | Utilidad práctica | 20 % | 6 | Base potente, pero necesita GPU grande y la licencia es dudosa. |
  | Creatividad y momento memorable | 15 % | 6 | La idea de un modelo de vídeo que pasa a mover robots es llamativa. |
  | Facilidad de uso y presentación | 15 % | 6 | Acceso restringido y pesado; el Space ayuda. |
  | **Total** | | **63** | |

- **Replicabilidad en 48 h con SO-101:** baja. Un modelo de 7B no es realista en una GPU de hackathon y la licencia no
  está clara. Seguimos con SmolVLA.
- **Lección para LeWelder:** **los cuantiles de normalización** deben salir de nuestros datos con la calibración
  actual. Un error ahí degrada mucho la política. Y siempre límites de articulación por software.

### GR00T N1.5 en SO-101 ("table cleanup") · NVIDIA (youliangtan y otros) · blog + dataset · blog del 11-06-2025

- **Fuentes:** <https://huggingface.co/blog/nvidia/gr00t-n1-5-so101-tuning>; dataset
  <https://huggingface.co/datasets/youliangtan/so101-table-cleanup> (32 likes); integración posterior:
  <https://huggingface.co/blog/nvidia/nvidia-isaac-gr00t-in-lerobot> y
  <https://huggingface.co/blog/nvidia/nvidia-isaac-teleop-and-gr00t17-in-lerobot>.
- **Qué hace:** tutorial para ajustar el VLA GR00T N1.5 con datos teleoperados de un único SO-101 que recoge la mesa
  ("Grab pens and place into pen holder").
- **Análisis técnico:**
  - SO-101 con dos cámaras (muñeca y frontal). El blog cita 80 episodios; la ficha actual del dataset muestra
    `total_episodes: 1` en su `info.json`, una discrepancia que no he podido aclarar.
  - SO-101 no estaba en el preentrenamiento, así que se entrena como `new_embodiment` con un `modality.json`. 10.000
    pasos en una GPU con unos 25 GB de VRAM.
  - Inferencia como servidor (4 pasos de difusión) con un cliente en el robot. El blog no da tasas de éxito, solo un GIF.
  - En los comentarios del blog, usuarios cuentan movimiento a tirones (se recomiendan 16 pasos de difusión y
    horizonte 16) y que con 30 episodios el modelo **ignoraba el texto**.
- **Análisis de la aplicación:** recoger la mesa es fácil de entender, pero la tarea es genérica. Momento memorable: no
  hay uno claro.
- **Por qué destaca:** blog oficial de NVIDIA en Hugging Face. Fue la puerta de entrada de GR00T a la comunidad SO-101,
  y ahora GR00T N1.7 está en LeRobot.
- **Valoración:**

  | Criterio | Peso | Nota | Por qué |
  |---|---|---|---|
  | Funciona en vivo y se recupera | 30 % | 5 | GIF sin métricas, y usuarios con movimiento a tirones. |
  | Dificultad técnica | 20 % | 7 | Ajustar un VLA de 3B a una morfología nueva. |
  | Utilidad práctica | 20 % | 6 | Receta reutilizable, tarea de ejemplo. |
  | Creatividad y momento memorable | 15 % | 4 | Recoger la mesa es la demo de siempre. |
  | Facilidad de uso y presentación | 15 % | 6 | Pasos claros, con fallos de instalación según los comentarios. |
  | **Total** | | **56** | |

- **Replicabilidad en 48 h con SO-101:** media. Necesita 25 GB de VRAM y datos propios.
- **Lección para LeWelder:** con pocos episodios **el VLA ignora la instrucción**. Para que SmolVLA multitarea obedezca
  a la voz, cada tarea necesita suficientes episodios y escenas que solo se distingan por el texto.

### robot_MCP · Ilia Larchenko · repo GitHub + vídeo de YouTube · ~89 estrellas, 20 forks

- **Fuentes:** <https://github.com/IliaLarchenko/robot_MCP>; vídeo: <https://youtu.be/EmpQQd7jRqs>.
- **Qué hace:** servidor MCP para que un LLM (Claude, Gemini o GPT) controle un SO-100/101, o un LeKiwi solo el brazo,
  desde un chat o un agente de terminal, viendo por las cámaras.
- **Análisis técnico:** transportes stdio, SSE y HTTP, cámaras en `config.py` y tres modos (MCP, teclado y agente
  CLI). Es programado el control cartesiano o articular expuesto como herramientas; el razonamiento lo pone el LLM.
  Según el autor: Claude va mejor, Gemini en medio y **GPT mal**. Las imágenes salen caras en tokens. Una actualización
  de LeRobot rompió la compatibilidad (el vídeo necesita la v0.0.1). Hay que reajustar la calibración en `config.py`.
- **Análisis de la aplicación:** "hablarle" a un brazo sin entrenar nada. Momento memorable: Claude mueve el brazo a
  partir de una frase.
- **Por qué destaca:** es el ejemplo más citado de LLM + MCP + SO-101 y viene con un tutorial completo en vídeo. Su
  autor es conocido en la comunidad LeRobot [no verificado: sus premios previos].
- **Valoración:**

  | Criterio | Peso | Nota | Por qué |
  |---|---|---|---|
  | Funciona en vivo y se recupera | 30 % | 6 | Hay vídeo, pero es frágil (versiones, calibración, según el LLM). |
  | Dificultad técnica | 20 % | 5 | Integración MCP sencilla, sin aprendizaje motor. |
  | Utilidad práctica | 20 % | 5 | Control lento y caro en tokens para tareas reales. |
  | Creatividad y momento memorable | 15 % | 7 | Ver al LLM "pensar" y mover el brazo impresiona. |
  | Facilidad de uso y presentación | 15 % | 7 | Tres modos y tutorial en vídeo. |
  | **Total** | | **59** | |

- **Replicabilidad en 48 h con SO-101:** alta.
- **Lección para LeWelder:** el LLM controlando articulaciones es lento y frágil. Mejor que el LLM solo **elija la
  tarea** y que SmolVLA ejecute el movimiento, que es lo que ya prevé nuestra spec.

### Dum-E · aaronsu11 · repo GitHub · ~27 estrellas (incluido por relevancia, no por popularidad)

- **Fuentes:** <https://github.com/aaronsu11/dum-e>.
- **Qué hace:** agente con voz y visión que controla un SO-100/101. Conversas con él y lanza tareas de manipulación.
- **Análisis técnico:** voz con Pipecat (Deepgram para STT, ElevenLabs para TTS), agente con Strands Agents y modelos de
  Anthropic, un servidor MCP (gestor de flota, de tareas y bus de mensajes) y **GR00T N1.7 como servidor de política**
  en Docker. MoveIt va como controlador clásico complementario. SO-101 con cámara de muñeca y webcam frontal. Vídeo de
  demo en el repo (no visto).
- **Análisis de la aplicación:** asistente de taller (el nombre viene del robot de Tony Stark). Momento memorable: le
  pides algo hablando y el brazo lo hace.
- **Por qué destaca:** poca popularidad, pero es la arquitectura más parecida a la nuestra (voz → agente → VLA).
- **Valoración:**

  | Criterio | Peso | Nota | Por qué |
  |---|---|---|---|
  | Funciona en vivo y se recupera | 30 % | 5 | Hay un vídeo, pero no lo he visto ni hay métricas. |
  | Dificultad técnica | 20 % | 8 | Voz, agente, MCP, VLA y MoveIt. |
  | Utilidad práctica | 20 % | 6 | Asistente genérico. |
  | Creatividad y momento memorable | 15 % | 6 | Concepto conocido, bien ejecutado. |
  | Facilidad de uso y presentación | 15 % | 5 | Muchas piezas y claves de API. |
  | **Total** | | **59,5** | |

- **Replicabilidad en 48 h con SO-101:** media. La capa de voz y agente se puede copiar; GR00T es pesado.
- **Lección para LeWelder:** con muchas piezas en la nube (STT, TTS, LLM) hay muchos puntos de fallo en vivo. Tener un
  **modo sin red** (STT local o botones de respaldo) para la demo.

### phosphobot · phospho (phospho-app) · repo GitHub + app · ~394 estrellas, 85 forks

- **Fuentes:** <https://github.com/phospho-app/phosphobot>.
- **Qué hace:** software para controlar robots, grabar datos y entrenar y usar VLA (ACT, SmolVLA, π0.5, GR00T N1.5),
  centrado en SO-100/SO-101, con app de Meta Quest para teleoperar.
- **Análisis técnico:** interfaz web y API, soporte beta de Koch, WX-250, Piper y Unitree Go2, tutorial de ajuste de
  GR00T y entrenamiento en la nube. Es una herramienta, no una tarea.
- **Análisis de la aplicación:** baja la barrera para quien no quiere usar la línea de comandos. Momento memorable:
  teleoperar el SO-101 con las gafas de VR.
- **Por qué destaca:** muy usado en hackathons de 2025 [no verificado], unas 394 estrellas y más de 2.000 commits.
- **Valoración:**

  | Criterio | Peso | Nota | Por qué |
  |---|---|---|---|
  | Funciona en vivo y se recupera | 30 % | 5 | Producto activo, sin demo autónoma propia comprobada. |
  | Dificultad técnica | 20 % | 6 | Integra muchas políticas y robots. |
  | Utilidad práctica | 20 % | 7 | Ahorra tiempo de grabación y entrenamiento. |
  | Creatividad y momento memorable | 15 % | 4 | Es una herramienta. |
  | Facilidad de uso y presentación | 15 % | 7 | Interfaz gráfica y VR. |
  | **Total** | | **57,5** | |

- **Replicabilidad en 48 h con SO-101:** alta como herramienta. El oficial y equivalente es LeLab
  (<https://huggingface.co/spaces/lerobot/LeLab>, 22 likes), la interfaz web de LeRobot.
- **Lección para LeWelder:** no programar herramientas de grabación propias. LeRobot 0.7 (o LeLab) ya graba, entrena y
  despliega; las 48 h van a datos y demo.

---

## 2. Referencias base (no son aplicaciones, pero sostienen muchos proyectos)

### [Referencia] SmolVLA base · Hugging Face (lerobot) · modelo · 497 likes, 139.740 descargas (el modelo LeRobot con más likes y descargas), 01-06-2025

- **Fuentes:** <https://huggingface.co/lerobot/smolvla_base>, <https://huggingface.co/blog/smolvla> (03-06-2025).
- **Qué hace:** VLA compacto (unos 450 M de parámetros) preentrenado con **487 datasets comunitarios** de SO-100
  (unos 10 M de frames, menos de 30k episodios). Se ajusta en una GPU de consumo.
- **Análisis técnico:** inferencia asíncrona: misma tasa de éxito que la síncrona (unos 78 %), pero tareas un 30 % más
  rápidas (9,7 s frente a 13,75 s), y 19 cubos frente a 9 en el mismo tiempo. Ajuste de ejemplo: lote de 64 y 20.000
  pasos. Hay más detalle en `investigacion/lecturas/smolvla.md`.
- **Análisis de la aplicación:** es la base práctica de casi todos los proyectos SO-101 con lenguaje.
- **Por qué destaca:** el modelo más descargado de la librería LeRobot, con muchas variantes (`smolvla_libero` tiene
  47.920 descargas).
- **Valoración:**

  | Criterio | Peso | Nota | Por qué |
  |---|---|---|---|
  | Funciona en vivo y se recupera | 30 % | 6 | Tasas publicadas y uso masivo; depende de los datos de cada uno. |
  | Dificultad técnica | 20 % | 9 | VLA preentrenado en datos comunitarios con inferencia asíncrona. |
  | Utilidad práctica | 20 % | 9 | Cabe en hardware de hackathon. |
  | Creatividad y momento memorable | 15 % | 5 | Es un modelo, no una demo. |
  | Facilidad de uso y presentación | 15 % | 7 | Integrado en LeRobot, con un comando de ajuste. |
  | **Total** | | **72** | |

- **Replicabilidad en 48 h con SO-101:** alta.
- **Lección para LeWelder:** activar la **inferencia asíncrona** en la demo: es un 30 % más rápida sin perder éxito, y
  un brazo fluido parece más competente.

### [Referencia] svla_so101_pickplace · Hugging Face (lerobot) · dataset · 60 likes, 27.143 descargas, 23-05-2025

- **Fuentes:** <https://huggingface.co/datasets/lerobot/svla_so101_pickplace>.
- **Qué hace:** el dataset de ejemplo para ajustar SmolVLA: 50 episodios, 11.939 frames a 30 fps, una tarea.
- **Análisis técnico:** formato LeRobotDataset v3.0. Curiosidad: su `info.json` declara `robot_type: so100_follower`
  pese al nombre. Da una idea de escala: con unos 50 episodios por tarea se obtiene una política de pick-and-place
  utilizable.
- **Análisis de la aplicación y por qué destaca:** es el dataset SO-101 con más likes, y es el que usan los tutoriales.
- **Valoración:**

  | Criterio | Peso | Nota | Por qué |
  |---|---|---|---|
  | Funciona en vivo y se recupera | 30 % | 5 | Es un dataset; el resultado depende del entrenamiento. |
  | Dificultad técnica | 20 % | 3 | Una tarea sencilla. |
  | Utilidad práctica | 20 % | 7 | Sirve de referencia de formato y escala. |
  | Creatividad y momento memorable | 15 % | 2 | Ninguna. |
  | Facilidad de uso y presentación | 15 % | 8 | Listo para entrenar. |
  | **Total** | | **50** | |

- **Replicabilidad en 48 h:** alta.
- **Lección para LeWelder:** presupuesto mínimo de unos 50 episodios por tarea. Copiar su estructura de cámaras y de
  nombres de *features* para no pelear con `--rename_map`.

### [Referencia] SO-101 tabletop MuJoCo (EnvHub) · Hugging Face (lerobot) · Space + modelo · 13 likes (modelo), creado el 13-11-2026

- **Fuentes:** <https://huggingface.co/spaces/lerobot/so101-tabletop-mujoco>.
- **Qué hace:** entorno EnvHub oficial de LeRobot con un SO-101, cuatro cubos de colores y una caja ("Put all the cubes
  in the green box"), con cámara frontal y de muñeca y recompensa por fracción de cubos.
- **Análisis técnico:** MuJoCo 4.0.1 a 30 fps, acciones en grados (las mismas unidades que `so101_follower` con
  `use_degrees=True`) y reinicios aleatorizados. Funciona con `lerobot-rollout --robot.type=sim` y `lerobot-eval` con
  la misma política que el robot real.
- **Por qué destaca:** es la novedad de la semana (*trending*) y permite evaluar políticas SO-101 sin el robot.
- **Valoración:**

  | Criterio | Peso | Nota | Por qué |
  |---|---|---|---|
  | Funciona en vivo y se recupera | 30 % | 5 | Recién publicado, sin pruebas propias. |
  | Dificultad técnica | 20 % | 6 | Entorno bien hecho con servidor y Docker. |
  | Utilidad práctica | 20 % | 7 | Permite probar el bucle completo antes de tener el brazo. |
  | Creatividad y momento memorable | 15 % | 4 | Tarea estándar. |
  | Facilidad de uso y presentación | 15 % | 7 | Comandos documentados. |
  | **Total** | | **57,5** | |

- **Replicabilidad en 48 h:** alta, pero la simulación no sustituye a los datos reales de nuestras juntas.
- **Lección para LeWelder:** útil **antes** del hackathon para probar la tubería voz → tarea → `lerobot-rollout` sin el
  brazo. Durante las 48 h, solo robot real.

---

## 3. Tabla resumen (ordenada por total)

| # | Proyecto | Tipo | Métrica clave | Vivo (30) | Dific. (20) | Util. (20) | Creat. (15) | Present. (15) | Total |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Unfolding Robotics (doblado de camisetas) | Space-blog | 162 likes; 90 % de éxito; 15 min sin cortes | 9 | 10 | 8 | 7 | 8 | **85,5** |
| 2 | XLeRobot | repo | ~5,8k estrellas | 7 | 8 | 8 | 7 | 7 | **74** |
| 3 | Reachy Mini Conversation App | Space/app | 193 likes | 7 | 7 | 6 | 8 | 9 | **72,5** |
| – | [Ref.] SmolVLA base | modelo | 497 likes, 139.740 descargas | 6 | 9 | 9 | 5 | 7 | **72** |
| 4 | Prompting Robots (rollout interactivo) | Space-blog | 9 likes (oficial, reciente) | 6 | 8 | 7 | 7 | 7 | **69** |
| 5 | Baby Reachy-Mini Companion | Space/app | 179 likes | 5 | 8 | 7 | 8 | 7 | **67,5** |
| 6 | FLUX 3 Action SO-101 | modelo + Space | 65 likes (base: 172) | 5 | 9 | 6 | 6 | 6 | **63** |
| 7 | LeKiwi | repo | ~1,5k estrellas | 6 | 6 | 7 | 5 | 7 | **62** |
| 8 | Steer a robot with words | Space | 31 likes | 5 | 7 | 5 | 7 | 8 | **61,5** |
| 9 | Dum-E | repo | ~27 estrellas | 5 | 8 | 6 | 6 | 5 | **59,5** |
| 10 | robot_MCP | repo + vídeo | ~89 estrellas | 6 | 5 | 5 | 7 | 7 | **59** |
| 11 | phosphobot | repo/app | ~394 estrellas | 5 | 6 | 7 | 4 | 7 | **57,5** |
| – | [Ref.] SO-101 tabletop MuJoCo | Space/entorno | 13 likes | 5 | 6 | 7 | 4 | 7 | **57,5** |
| 12 | Reachy Phone Home | Space/app | 372 likes | 5 | 4 | 5 | 8 | 8 | **57** |
| 13 | GR00T N1.5 en SO-101 | blog + dataset | blog de NVIDIA; dataset con 32 likes | 5 | 7 | 6 | 4 | 6 | **56** |
| – | [Ref.] svla_so101_pickplace | dataset | 60 likes, 27.143 descargas | 5 | 3 | 7 | 2 | 8 | **50** |

Nota: la popularidad (likes y estrellas) y la nota del hackathon no coinciden. Reachy Phone Home tiene más likes que
nadie con una técnica sencilla, porque lo que puntúa en la comunidad es la reacción emocional. En un jurado en vivo pesa
más que funcione, y ahí gana quien tiene evidencia sin cortes y métricas.

---

## 4. Patrones comunes

1. **La evidencia sin cortes manda.** El proyecto mejor valorado lo es por un vídeo de 15 min sin intervención y por
   tasas con intervalos de confianza. La mayoría solo tiene GIFs y por eso no pasa de 5 en "funciona en vivo".
2. **Datos > algoritmo.** En el doblado, curar datos dio +50 puntos frente a +5-20 de las mejoras de algoritmo. En
   GR00T, con pocos episodios el modelo ignoraba el texto. SmolVLA sirve con unos 50 episodios por tarea si son
   consistentes.
3. **Arquitectura en dos niveles para el lenguaje.** Un LLM o VLM elige *qué* hacer (subtarea o habilidad) y un VLA o
   código hace el *cómo*. Lo hacen el blog oficial (planificador → π0.5), Steer a robot (Qwen3-VL → MolmoAct2), Dum-E
   (agente → GR00T) y Baby Reachy (LLM con herramientas). Cuando el LLM mueve articulaciones directamente (robot_MCP)
   es lento y frágil.
4. **Lo crítico va en código determinista.** Baby Reachy envía las alertas sin LLM. El orquestador de Carmelo's
   Cucina (MakerMods 2026, hackathon, solo como ejemplo) usa una máquina de estados con antirrebote y un *watchdog*.
   FLUX 3 Action exige límites de articulación externos.
5. **Las apps de Reachy Mini enseñan a presentar.** Tienen personalidad, voz que se puede interrumpir, movimiento
   mientras escuchan y una historia humana ("para mi hijo", "deja el móvil"). Los likes vienen de la emoción, no de la
   técnica.
6. **Precio y apertura como argumento.** XLeRobot (660 $), OpenArm Mini (120 € por brazo), LeKiwi y Baby Reachy (todo
   local) ponen el coste y la privacidad en el titular.

### Cómo se demuestra un VLA (lo que hacen los mejores)

- **Varias instrucciones con la misma escena.** El VLA solo prueba que entiende lenguaje si, con los mismos objetos,
  hace cosas distintas según la frase ("la manzana, no el yogur"). Si no, el jurado puede pensar que es un movimiento
  grabado.
- **Redirección a mitad de movimiento** (`/subtask` en `lerobot-rollout --interactive`): el momento más convincente.
- **Mostrar en pantalla la instrucción activa** (la habilidad resaltada de Steer a robot, los subtítulos con las
  instrucciones del blog oficial).
- **Vídeo a velocidad real y con fallos documentados** (el blog oficial publica un fallo de agarre); da credibilidad.
- **Tasa de éxito con N ensayos** (20 ensayos por condición en el doblado). En un pitch de 5 min basta con "8/10 en
  ensayos de ayer" más un vídeo de respaldo.
- **Inferencia asíncrona o RTC** para que el brazo no se pare entre trozos de acciones.

---

## 5. Lecciones aplicadas a LeWelder (resumen)

1. Grabar las juntas en **posiciones y órdenes variados** y con una única estrategia de operador. Si no, SmolVLA hará
   la tarea más frecuente o la más cercana aunque la voz pida otra.
2. La voz elige la tarea (`/subtask` o un LLM pequeño con 3-4 opciones) y SmolVLA ejecuta. Mostrar en pantalla la tarea
   entendida antes de mover.
3. Seguridad, puntuación y paradas en código determinista. Modo sin red como respaldo de la voz.
4. Inferencia asíncrona activada. Límites de articulación por software. Cuantiles de normalización sacados de nuestros
   propios datos.
5. Momento memorable emocional y simple: el robot reacciona a la soldadura del alumno, y el sistema "da señales de
   vida" mientras escucha.
6. Llevar un vídeo sin cortes de la demo completa y una tasa "X/10" medida la víspera.

---

## 6. Fuentes

Hugging Face (API y páginas, consultadas el 18-11-2026):
- API: `https://huggingface.co/api/spaces?search=lerobot&sort=likes`, `...&sort=trendingScore`,
  `.../api/spaces?search=reachy&sort=likes`, `.../api/spaces?search=so101&sort=likes`,
  `.../api/models?filter=lerobot&sort=likes|downloads|trendingScore`,
  `.../api/datasets?filter=LeRobot&sort=likes|downloads|trendingScore`.
- https://huggingface.co/spaces/lerobot/robot-folding · https://lerobot-robot-folding.hf.space/
- https://huggingface.co/spaces/lerobot/language-conditioned-policies · https://lerobot-language-conditioned-policies.hf.space/
- https://huggingface.co/spaces/lerobot/robots-that-talk
- https://huggingface.co/spaces/lerobot/steer-a-robot
- https://huggingface.co/spaces/lerobot/LeLab
- https://huggingface.co/spaces/lerobot/so101-tabletop-mujoco
- https://huggingface.co/spaces/pollen-robotics/reachy_mini_conversation_app
- https://huggingface.co/spaces/itsMarco-G/reachy_phone_home
- https://huggingface.co/spaces/ravediamond/baby-reachy-mini-companion
- https://huggingface.co/spaces/multimodalart/flux-3-action-so101-sim · https://huggingface.co/black-forest-labs/flux-3-action-so101
- https://huggingface.co/lerobot/smolvla_base · https://huggingface.co/blog/smolvla
- https://huggingface.co/datasets/lerobot/svla_so101_pickplace
- https://huggingface.co/datasets/youliangtan/so101-table-cleanup
- https://huggingface.co/blog/nvidia/gr00t-n1-5-so101-tuning · https://huggingface.co/blog/nvidia/nvidia-isaac-gr00t-in-lerobot · https://huggingface.co/blog/nvidia/nvidia-isaac-teleop-and-gr00t17-in-lerobot
- https://huggingface.co/blog/reachy-mini

GitHub (páginas consultadas el 18-11-2026):
- https://github.com/huggingface/lerobot (~29k estrellas)
- https://github.com/Vector-Wangel/XLeRobot · https://xlerobot.readthedocs.io
- https://github.com/SIGRobotics-UIUC/LeKiwi
- https://github.com/IliaLarchenko/robot_MCP · https://youtu.be/EmpQQd7jRqs
- https://github.com/aaronsu11/dum-e
- https://github.com/phospho-app/phosphobot
- https://github.com/pollen-robotics/AmazingHand (~2,6k estrellas; mano de 8 GDL por menos de 200 €; descartada de la lista
  por no ser aplicación ni estar integrada en LeRobot según su README)

Prensa y terceros (cifras marcadas como [no verificado] cuando solo vienen de aquí):
- https://hackaday.com/2025/11/03/dual-arm-mobile-bot-built-on-ikea-cart-costs-hundreds-not-thousands
- https://axios.com/2026/05/06/hugging-face-consumer-robot-app-store
- https://venturebeat.com/technology/the-app-store-for-robots-has-arrived-hugging-face-launches-open-source-reachy-mini-app-store-with-200-apps
- https://www.deeplearning.ai/the-batch/video-models-steer-robots
- https://venturebeat.com/infrastructure/black-forest-labs-debuts-flux-3-action-an-open-weights-ai-robotics-model-that-tops-the-leaderboard-at-half-the-size-of-its-competition
- https://alisoncossette.github.io/carmelos-cucina/ (hackathon; solo como ejemplo de orquestador en los patrones)
- https://techcrunch.com/2025/05/29/hugging-face-unveils-two-new-humanoid-robots/ (HopeJR y Reachy Mini; HopeJR descartado por
  ser hardware sin aplicación documentada)
