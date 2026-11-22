# Ganadores de hackathons de aprendizaje de robots fuera de Europa (2026 y finales de 2025)

Fecha: 18-11-2026. Objetivo: aprender de los ganadores para el Hackathon LeRobot Bilbao II (20-22 nov 2026).
Ámbito: Estados Unidos, Asia y eventos online o globales; brazos de bajo coste (SO-100/SO-101, XLeRobot) y
políticas aprendidas. Como referencia se incluyen eventos de octubre a diciembre de 2025.

Convenciones:
- **[no verificado]**: dato que no he leído en una fuente primaria (solo en un resumen de buscador, un
  fragmento de red social o una inferencia mía).
- **[hipótesis]**: interpretación propia sin palabras del jurado que la respalden.
- Rúbrica de trabajo (de `investigacion/analisis-concursos.md`): Funciona en vivo y se recupera 30 %,
  Dificultad técnica 20 %, Utilidad práctica 20 %, Creatividad y momento memorable 15 %, Facilidad de uso y
  presentación 15 %. Total = suma de nota × peso × 10. Lo que no se puede comprobar con fuentes no pasa de 5.

## 0. Qué se buscó y qué no apareció

Se buscaron resultados de 2026 en Devpost, Luma, Hackster, blogs de organizadores, prensa, LinkedIn, X, GitHub
y Hugging Face. Muchos eventos de 2026 con SO-101 **no han publicado ganadores** (o no están indexados):

| Evento 2026 | Dónde y cuándo | Qué se sabe | Por qué no entra |
|---|---|---|---|
| LeRobot Worldwide Hackathon 2026 | — | **No hay evidencia de que se celebrara**; todas las páginas son de la edición de junio de 2025 | No existe (o no hay datos) |
| Physical AI Hacks | San Francisco (Founders Inc), 31 ene - 1 feb 2026 | G1, SO-101, LeKiwi, Open Duck Mini | Sin ganadores publicados |
| Physical AI Hack World Tour (MakerMods) | Shenzhen 28-29 mar; San Francisco 9-10 may 2026 | XLeRobot, OpenClaw, LeRobot; criterios: creatividad técnica, aplicabilidad real, **demo que funciona en el escenario** | Sin ganadores publicados |
| Physical AI × OpenClaw | Shenzhen, ~abr 2026 | 25 XLeRobot; pi0.5, GR00T N1, SmolVLA, ACT | Sin ganadores publicados |
| Seeed Embodied AI Hackathon 2026 | Santa Clara, 21-22 mar 2026 (tras GTC) | Reachy Mini + Jetson | Sin ganadores publicados |
| StarkHacks (Purdue) | 17-19 abr 2026, +750 personas | Premio de Viam: SO-101 montado | Sin ganadores de robótica aprendida localizados |
| NVIDIA Cosmos Cookoff | Online, ene-mar 2026 | 1.º Team Zenith (paletizado con razonamiento visual explicable) | Visión/simulación, no brazo de bajo coste |
| AMD AI DevMaster (pista Physical AI) | Online, 2026 | 2.º KINESYS (humanoide saca vajilla del lavavajillas) | Humanoide/simulación; recap no accesible |
| RoboHacks '26 (YC) | San Francisco, 2026 | Robot MARS de Innate (brazo 7 GDL) | Solo se conoce un premio de simulación |
| Robotics Pizza Hackathon | 30 oct - 1 nov 2026, ciudad sin publicar | SO-101 + ElRobot, rúbrica de 100 puntos | Bases en borrador, sin resultados |
| Robotics Hackathon at Cal | Berkeley, ago 2026 | Entrega de cacahuete con ACT (29-57 episodios) y voz con ElevenLabs sin terminar | Sin puesto conocido |
| Arduino Physical AI Challenge India | Bengaluru, ago 2026 | Arduino UNO Q | No es aprendizaje de robots |

Conclusión del barrido: en 2026 hay muchos hackathons con SO-101, pero **pocos publican ganadores con detalle
técnico**. Los mejor documentados siguen siendo los de finales de 2025 (Seeed/NVIDIA, AMD, Hack Club).

---

## 1. Proyectos

### Automated Donuts Order Assistant · Team 9 GreatAkihabara (Masato Kawamura, Kazuki Murata, Yuji Fujima, Shota Yoshikai) · AMD Open Robotics Hackathon, Tokio (Akihabara), 5-7 dic 2025 · 1.º puesto (36 equipos)

- Fuentes: [repo del equipo](https://github.com/masato-ka/GreateAkihabra_9_AMDOpenRoboticsHackathon),
  [dataset de donuts (120 episodios)](https://huggingface.co/datasets/masato-ka/donuts-shop-dataset-v0),
  [dataset de cerrar la caja](https://huggingface.co/datasets/masato-ka/donuts-shop-close-box-dataset-v0),
  [modelo SmolVLA](https://huggingface.co/masato-ka/smolvla-donuts-shop-v1-100k),
  [crónica de AMD con el puesto](https://www.amd.com/en/developer/resources/technical-articles/2025/amd-open-robotics-hackathon-recap.html),
  [bases y rúbrica](https://huggingface.co/blog/amd/openroboticshackathon). Proyecto previo del mismo equipo:
  [platos por lenguaje, 15.º en el LeRobot Worldwide 2025](https://huggingface.co/datasets/LeRobot-worldwide-hackathon/164-great-akihabara-plate-inst).
- Qué hace: un cliente pide donuts a un chatbot; dos brazos guiados por un VLA meten los donuts de chocolate y de
  fresa en una caja, la cierran y tocan una campana para avisar de que el pedido está listo.
- Análisis técnico:
  - Robot: bimanual SO-101 (`bi_so101_follower` en los metadatos del dataset). Dos cámaras (frontal y trasera).
  - Política: **SmolVLA multitarea condicionado por texto** ("Please take the chocolate donuts and into the box",
    "Pick up the strawberry donut and place it in the box"). Cerrar la tapa se entrenó **como modelo aparte**
    porque el modelo combinado no la terminaba. En inferencia usan **Real-Time Action Chunking** de LeRobot para
    tolerar cambios de forma de cajas y donuts.
  - Datos: 120 episodios planificados (más de 180 grabados contando fallos y reintentos) en 3 tareas + 30 episodios
    de cerrar la caja. Misión 1 (guiada): 10 + 30 episodios con ACT y SmolVLA.
  - Entrenamiento: 2 GPU AMD MI300X; versiones de 40k, 60k, 80k y 100k pasos con lote 32 (según los
    `train_config.json` publicados).
  - Capas extra: chatbot de pedidos → cola de mensajes → gestor de estado que lanza el VLA; campana USB que el
    robot golpea como señal de fin. No dicen qué LLM ni si hay voz.
  - Aprendido: toda la manipulación. Programado: la orquestación (chatbot, cola, estados).
- Análisis de la aplicación: problema real (preparar pedidos para llevar en una tienda pequeña); usuario: el
  dependiente y el cliente; se entiende en un vistazo (donuts → caja → campana). Momento memorable: el robot toca
  la campana al terminar. El equipo plantea explícitamente tres retos de los VLA: tareas largas, coordinación de
  dos brazos y **saber cuándo se ha terminado** (resuelto con la campana).
- Por qué ganó: no hay palabras del jurado. La rúbrica oficial (100 puntos) valora creatividad, dificultad,
  facilidad de uso y utilidad práctica, y exige publicar código, datos, modelos y vídeo. [hipótesis] Cumple los
  cuatro criterios a la vez: bimanual y de horizonte largo (dificultad), tienda real (utilidad), chatbot + campana
  (creatividad y uso) y entrega completa. Además el equipo ya llegaba con experiencia (15.º mundial en junio 2025
  con un VLA de platos por lenguaje: "dame dos platos").
- Valoración:

  | Criterio | Peso | Nota | Por qué |
  |---|---|---|---|
  | Funciona en vivo y se recupera | 30 % | 6 | Ganó en vivo y hay vídeo final en el repo, pero no publican tasa de éxito y RTC es su única medida de robustez |
  | Dificultad técnica | 20 % | 8 | Bimanual, tres subtareas, VLA multitarea con lenguaje y RTC: lo más difícil de la lista con datos públicos |
  | Utilidad práctica | 20 % | 7 | Empaquetar pedidos en tienda es un caso real y claro |
  | Creatividad y momento memorable | 15 % | 7 | Chatbot de pedidos y campana de fin; tema de tienda con gracia |
  | Facilidad de uso y presentación | 15 % | 8 | Repo, datasets y modelos públicos; el cliente solo pide |
  | **Total** | | **71** | |

- Replicabilidad en 48 h con SO-101: **media**. Un solo SO-101 y SmolVLA con 2-3 tareas por texto es viable; lo
  bimanual y 180 episodios piden un equipo rodado y GPU grande.
- Lección para LeWelder: es casi nuestra arquitectura (pedido → gestor de estado → SmolVLA multitarea por texto).
  Copiar dos cosas: **separar en un modelo aparte la subtarea que el multitarea no termina** y dar una **señal
  física de "terminado"** (campana o LED) que el público vea.

### Matcha Making ("Performative") · UIUC SIGRobotics (Leo Lin, Himank Handa, Keshav Badrinath, Aarsh Mittal, Filip Kujawa, Sanjit Kumar, Stephen Zhu, Hasan Al Saeedi) · Seeed Studio × NVIDIA × Hugging Face Embodied AI Hackathon, sesión EE. UU. (Bahía de San Francisco), oct 2025 · 1.º puesto

- Fuentes: [crónica de Seeed](https://seeed.cc/post/2025-embodied-ai-hackathon-recap),
  [artículo en Hackster](https://www.hackster.io/sigrobotics/matcha-bot-sigrobotics-embodied-ai-hackathon-1st-place-f0e520)
  (no accesible directamente; datos tomados de su resumen en el buscador [no verificado]),
  [organización en GitHub](https://github.com/SIGRobotics-UIUC).
- Qué hace: prepara té matcha en tres pasos: echa el polvo, vierte el agua y bate.
- Análisis técnico:
  - Robot: XLeRobot bimanual modificado. Tres cámaras USB; en el evento se quemó una y pasaron a dos
    [no verificado].
  - Política: **GR00T N1.5** ajustado con NVIDIA Brev; inferencia en Jetson Thor.
  - Datos: unos 30 episodios por subtarea (3 subtareas) [no verificado].
  - Diseño clave (crónica de Seeed): como GR00T no tiene memoria, **hicieron distintos visualmente el inicio y el
    final de cada subtarea**: dejan caer el recipiente del agua al acabar y marcan el cuenco como vacío o lleno.
  - Aprendido: manipulación de cada subtarea. Programado: la secuencia.
- Análisis de la aplicación: tarea doméstica de cocina (tema del concurso); se entiende al instante; el batido
  del matcha es un gesto fino y vistoso. Momento memorable: el batido.
- Por qué ganó: sin palabras del jurado. [hipótesis] Encaja de lleno con el tema (cocina en casa) y con la pila
  del patrocinador (GR00T + Jetson Thor); bimanual con líquidos y polvo parece difícil.
- Valoración:

  | Criterio | Peso | Nota | Por qué |
  |---|---|---|---|
  | Funciona en vivo y se recupera | 30 % | 6 | Ganó en vivo y se adaptó a una cámara quemada; sin vídeo ni tasa publicados que haya podido ver |
  | Dificultad técnica | 20 % | 8 | Bimanual, polvo, agua y batido con un VLA de 3B ajustado |
  | Utilidad práctica | 20 % | 5 | Bonito pero de nicho |
  | Creatividad y momento memorable | 15 % | 7 | Ceremonia del té robótica, gesto memorable |
  | Facilidad de uso y presentación | 15 % | 6 | Escrito en Hackster; sin repo del proyecto localizado |
  | **Total** | | **64** | |

- Replicabilidad en 48 h con SO-101: **media**. Con un brazo y ACT/SmolVLA en lugar de GR00T bimanual es
  factible a 30 episodios por subtarea.
- Lección para LeWelder: con un VLA sin memoria, **cada subtarea debe empezar y terminar en un estado que se vea
  distinto** en la cámara (pieza colocada, marca de color, objeto retirado).

### Tubos de ensayo a la gradilla · equipo sin nombre publicado · CCSF Robotics Hack, San Francisco, 6 nov 2026 · 1.º puesto (8 equipos)

- Fuentes: [crónica](https://worldwidestudios.substack.com/p/ccsf-robotics-hack-recap-1-day-build); análisis
  previo en `investigacion/analisis-concursos.md`.
- Qué hace: un SO-101 coge tubos de ensayo y los coloca en una gradilla, como ayudante de laboratorio.
- Análisis técnico: SO-101 con brazo líder; una cámara (todos los equipos tenían una); **ACT**; perdieron unas
  veinte grabaciones y las repitieron; éxito aproximado del 75 %; **pinzas impresas en 3D para objetos
  redondos**. Episodios totales, GPU y pasos: no publicados. Todo aprendido salvo el diseño de la pinza.
- Análisis de la aplicación: tareas repetitivas de laboratorio; el equipo: "robots que ayudan a los científicos en
  las tareas más repetitivas". Se entiende al instante. Momento memorable: el tubo entra en la gradilla.
- Por qué ganó: juez de NVIDIA: "técnicamente el mejor" porque "es un problema realmente difícil de resolver".
  Los demás equipos fallaron por ejecución (montaje movido, 6 episodios, política aún entrenando, alcance excesivo).
- Valoración:

  | Criterio | Peso | Nota | Por qué |
  |---|---|---|---|
  | Funciona en vivo y se recupera | 30 % | 6 | Funcionó en vivo al ~75 %, pero repitieron la demo hasta que salió |
  | Dificultad técnica | 20 % | 7 | Objetos redondos y estrechos; el juez lo destacó como difícil |
  | Utilidad práctica | 20 % | 7 | Automatización de laboratorio, caso real |
  | Creatividad y momento memorable | 15 % | 5 | Correcto, sin sorpresa |
  | Facilidad de uso y presentación | 15 % | 5 | Sin repo ni dataset públicos |
  | **Total** | | **61** | |

- Replicabilidad en 48 h con SO-101: **alta**. ACT, una tarea y una pinza impresa.
- Lección para LeWelder: una **pinza impresa a medida de nuestras piezas** puede valer más que muchos episodios;
  y a igualdad, gana el que llega con la política entrenada y el montaje sin tocar.

### Desk cleanup con GR00T N1.5 · equipo de Lee-LEO-H · Seeed Studio × NVIDIA × Hugging Face Embodied AI Hackathon, sesión China (Shenzhen), oct 2025 · 1.º puesto

- Fuentes: [repo](https://github.com/Lee-LEO-H/Lerobot-GR00TN1.5),
  [crónica de Seeed](https://seeed.cc/post/2025-embodied-ai-hackathon-recap),
  [referencia de NVIDIA para GR00T en SO-101](https://huggingface.co/blog/nvidia/gr00t-n1-5-so101-tuning).
- Qué hace: un SO-101 recoge bolígrafos y gomas de la mesa, los mete en un recipiente y después limpia la mesa con
  un trapo.
- Análisis técnico:
  - Robot: SO-101; inferencia en Jetson Thor en el evento y en RTX 4090 en el laboratorio. Cámaras: no indicadas.
  - Política: **GR00T N1.5** ajustado con LeRobot.
  - Datos: **300 episodios**: ~70 % teleoperados en su laboratorio antes del evento, ~20 % en el evento y ~10 %
    simulados (MuJoCo), con aleatorización de posición, tipo y forma de bolígrafo y de la cesta.
  - Evaluación: MSE en lazo abierto de 7,17 frente a 10,42 de la referencia publicada de NVIDIA en el mismo
    conjunto de validación; vídeos en laboratorio, en el hackathon y en simulación.
  - Aprendido: todo. Programado: nada relevante.
- Análisis de la aplicación: ordenar y limpiar un escritorio; usuario doméstico; se entiende al instante.
  Momento memorable: pasar del agarre a limpiar con el trapo en la misma secuencia.
- Por qué ganó: sin palabras del jurado. La crónica destaca la generalización (300 episodios, 10 % simulados,
  aleatorización). [hipótesis] Pesó la robustez demostrada y el uso de toda la pila del patrocinador.
- Valoración:

  | Criterio | Peso | Nota | Por qué |
  |---|---|---|---|
  | Funciona en vivo y se recupera | 30 % | 6 | Vídeo en el evento con Jetson Thor y pruebas con varias luces; sin tasa de éxito |
  | Dificultad técnica | 20 % | 7 | Horizonte largo, VLA de 3B, mezcla real-simulado |
  | Utilidad práctica | 20 % | 6 | Limpieza doméstica, útil pero genérica |
  | Creatividad y momento memorable | 15 % | 4 | Recoger y limpiar es previsible |
  | Facilidad de uso y presentación | 15 % | 7 | Repo con instalación, uso y vídeos; licencia Apache |
  | **Total** | | **61** | |

- Replicabilidad en 48 h con SO-101: **baja**. El 70 % de los datos se grabó antes del evento y GR00T pide GPU grande.
- Lección para LeWelder: **medir y enseñar una cifra** frente a una referencia convence; y grabar parte de los
  datos con variación deliberada (posición y tipo de pieza) para que la generalización se vea en la demo.

### CaliKPR · Aswinkumar y Jeeva Sukumar · Junfan Labs Silicon Valley Robotics Hardware Hackathon #35 (con Abaka AI), Mountain View, ~25 oct 2026 · 1.º puesto, Premio del Público y Mejor Despliegue Real

- Fuentes: [publicación del organizador en X](https://x.com/junfanzhu98/status/2114237384921678080) (fecha
  deducida del identificador; contenido leído solo en fragmentos de buscador [no verificado]),
  [perfil de LinkedIn con la publicación](https://hk.linkedin.com/in/sibeichen) (no accesible directamente).
  No hay repo localizado.
- Qué hace: un agente de Claude controla un SO-101 mediante **28 herramientas MCP**, sin ninguna demostración, y
  resuelve las dos tareas del concurso [no verificado].
- Análisis técnico: SO-101; LLM con herramientas (MCP) en vez de política aprendida; según la publicación,
  **20/20 en las dos tareas**, mientras que ACT, SmolVLA y pi0.5 entrenados con **384 episodios** de
  teleoperación se quedaron en 15,5 en la tarea 2 [no verificado]. Probablemente visión + primitivas programadas
  (IK, agarres) expuestas como herramientas [hipótesis]. Aprendido: nada del control motor. Programado: todo,
  orquestado por el LLM.
- Análisis de la aplicación: el tema que emergió según el organizador fue la **confianza**; los jueces (Google
  DeepMind, Rhoda AI, Maxinsights, Abaka AI, Junfan Labs) premiaron fiabilidad medible. Momento memorable: el
  marcador 20/20 frente a los VLA.
- Por qué ganó: tasa de éxito perfecta y medida en tareas puntuadas, y premio del público [no verificado: solo
  fragmentos de las publicaciones].
- Valoración:

  | Criterio | Peso | Nota | Por qué |
  |---|---|---|---|
  | Funciona en vivo y se recupera | 30 % | 6 | 20/20 declarado en tareas puntuadas por el jurado, sin vídeo ni repo |
  | Dificultad técnica | 20 % | 5 | Integración de herramientas sin aprendizaje; difícil de valorar sin código |
  | Utilidad práctica | 20 % | 6 | "Mejor despliegue real" según el jurado |
  | Creatividad y momento memorable | 15 % | 6 | Ir contra corriente y ganar a los VLA es memorable |
  | Facilidad de uso y presentación | 15 % | 6 | Premio del público |
  | **Total** | | **58** | |

- Replicabilidad en 48 h con SO-101: **media**. Las herramientas son programables, pero la fiabilidad 20/20
  exige mucha ingeniería de agarres.
- Lección para LeWelder: los jueces de 2026 premian **fiabilidad medida**; conviene llevar un marcador visible
  (intentos y aciertos de la sesión) y tener las primitivas críticas (por ejemplo, volver a casa o soltar) como
  herramientas fiables al lado del VLA.

### Sprinkle · Bruce Kim, Joon Kim, Peiqing Xia y equipo (CMU MRSD) · Seeed Embodied AI Hackathon, sesión EE. UU., oct 2025 · 2.º puesto

- Fuentes: [crónica de Seeed](https://seeed.cc/post/2025-embodied-ai-hackathon-recap),
  [noticia de CMU](https://labs.ri.cmu.edu/mrsd-news/mrsds-winning-the-2025-embodied-ai-hackathon/),
  [diapositivas](https://docs.google.com/presentation/d/1bRnheEqD9aH5jIuS7tgGcSSRzrt0URkmdUyN-hR_tDQ/edit).
- Qué hace: coge un azucarero, espolvorea azúcar sobre galletas, pulsa un botón con forma de calabaza que gira el
  plato, espolvorea la otra mitad y devuelve el azucarero.
- Análisis técnico: brazo de bajo coste con la pinza de serie y una tira de velcro; **SmolVLA ajustado con 170
  episodios, dividido en 4 modelos** (coger, inclinar, pulsar, dejar); Jetson Thor y luego Jetson Orin Nano;
  **LED rojo que se enciende por proximidad en el botón** como señal de pulsación correcta; el giro del plato
  sirve de pista visual. Aprendido: las 4 habilidades. Programado: encadenarlas.
- Análisis de la aplicación: ayudante de repostería con tema de Halloween; se entiende al instante.
  Momento memorable: el plato que gira al pulsar la calabaza.
- Por qué ganó: sin palabras del jurado. [hipótesis] Tarea de varios pasos fiable gracias a dividirla y a
  señales visuales construidas a propósito.
- Valoración:

  | Criterio | Peso | Nota | Por qué |
  |---|---|---|---|
  | Funciona en vivo y se recupera | 30 % | 5 | 2.º en vivo; no he visto vídeo ni tasa |
  | Dificultad técnica | 20 % | 7 | 4 SmolVLA encadenados y despliegue en Orin Nano |
  | Utilidad práctica | 20 % | 5 | Cocina casera, limitado |
  | Creatividad y momento memorable | 15 % | 6 | Botón calabaza con LED y plato giratorio |
  | Facilidad de uso y presentación | 15 % | 6 | Diapositivas públicas y noticia de la universidad |
  | **Total** | | **57** | |

- Replicabilidad en 48 h con SO-101: **alta**. 170 episodios en 4 trozos y SmolVLA es asumible para 4 personas.
- Lección para LeWelder: **añadir al montaje elementos que den pistas visuales al VLA** (LED que confirma, pieza
  que cambia de estado) es barato y hace la secuencia más fiable.

### Armtender · Team 16 "Remphia" (Emme McDonald, Ruzanna Gaboyan, Afia Ava) · Hack Club Prototype (con AMD), Bahía de San Francisco, 19-21 dic 2025; expuesto en CES 2026 · 1.º puesto

- Fuentes: [repo](https://github.com/afia-ava/Armtender) y su `TRAINING.md`,
  [AMD en X sobre los ganadores en CES 2026](https://x.com/AMD/status/2010027341154791713),
  [crónica de WebProNews](https://www.webpronews.com/teen-barista-bot-how-a-chapel-hill-high-schoolers-ai-arm-snagged-20000-and-ces-spotlight)
  (beca de 20.000 $ por persona e invitación a CES; leído solo en el resumen del buscador [no verificado]),
  [bases del evento](https://blueprint.hackclub.com/prototype).
- Qué hace: el jugador pulsa un botón, gira una ruleta de la suerte y el brazo coge la lata de bebida del color en
  el que se para la flecha y la entrega por una ventanilla.
- Análisis técnico: brazo LeRobot (SO-101 entregado por la organización), piezas impresas en PLA, ESP32-C3 con
  motor de corriente continua y MOSFET para la ruleta, botón y 4 LED; 3 cámaras (cenital, lateral y muñeca);
  **ACT**, un solo modelo; ~120 episodios + ~50 de ajuste fino centrados en los movimientos que fallaban (el README
  dice 100 episodios, lote 128 y 10k pasos; `TRAINING.md` dice lote 96: hay discrepancia). Aprendido: elegir la
  lata según el color de la flecha y cogerla. Programado: la ruleta.
- Análisis de la aplicación: servicio de bebidas y juego de azar sin sesgo del crupier; equipo de estudiantes de
  secundaria. Momento memorable: la ruleta decide y el robot obedece.
- Por qué ganó: sin palabras del jurado. [hipótesis] Hardware propio (ruleta motorizada) que convierte una
  recogida simple en un juego, y una entrega muy bien documentada.
- Valoración:

  | Criterio | Peso | Nota | Por qué |
  |---|---|---|---|
  | Funciona en vivo y se recupera | 30 % | 5 | Ganó, pero el vídeo público es de teleoperación |
  | Dificultad técnica | 20 % | 5 | Una recogida condicionada por color; ruleta electrónica propia |
  | Utilidad práctica | 20 % | 4 | Camarero-juego, idea repetida |
  | Creatividad y momento memorable | 15 % | 7 | La ruleta de la suerte engancha al público |
  | Facilidad de uso y presentación | 15 % | 7 | README con lista de materiales, cableado y entrenamiento |
  | **Total** | | **54** | |

- Replicabilidad en 48 h con SO-101: **alta**.
- Lección para LeWelder: **ajuste fino con ~50 episodios centrados en los fallos observados** tras la primera
  prueba es una táctica barata; y un elemento electrónico propio (nuestra antorcha con LED) convierte la demo en juego.

### Iron Bestie · Luo Yuqing (CityU) y Zeng Yitao (SUSTech), equipo de seis · Physical AI Hackathon 2026 (Brizan Ventures, SpacemiT, alloop.ai), Hong Kong y Shenzhen, 2-5 ago 2026 · premio principal

- Fuentes: [Silicon UK](https://www.silicon.co.uk/ai-2/hong-kong-make-up-robot-631068),
  [China Daily HK, 5 ago](https://www.chinadailyhk.com/article/637499),
  [China Daily HK, 10 ago](https://www.chinadailyhk.com/hk/article/637715),
  [SCMP](https://www.scmp.com/tech/tech-trends/article/3363197/coded-glamour-and-glory-ai-make-arm-steals-show-hong-kong-hackathon)
  (no accesible; título y resumen del buscador).
- Qué hace: un brazo robótico que recibe órdenes por voz, identifica los cosméticos y maquilla a una persona
  según su rutina diaria (demo con pintalabios); también seca el pelo y ordena el tocador según China Daily.
- Análisis técnico: modelo de brazo, cámaras, política y episodios **no publicados**. El propio equipo dijo que
  el algoritmo es "relativamente básico". Voz + reconocimiento de objetos. Que el ganador sea el "Team 23 Grand
  MVP" de China Daily es probable pero no está confirmado [no verificado]. Premio MVP de 100.000 HK$ [no verificado].
- Análisis de la aplicación: asistente de belleza personal y de compañía (también útil para personas con
  movilidad reducida [hipótesis]). Momento memorable: el robot pintando los labios a una persona en el escenario.
- Por qué ganó: la prensa resalta la demo del pintalabios ("se llevó el espectáculo"); fundadora sin experiencia
  previa en programación. [hipótesis] Contacto con la cara de una persona = riesgo percibido + emoción.
- Valoración:

  | Criterio | Peso | Nota | Por qué |
  |---|---|---|---|
  | Funciona en vivo y se recupera | 30 % | 5 | Demo en vivo citada por la prensa, sin vídeo localizado |
  | Dificultad técnica | 20 % | 4 | El equipo admite un algoritmo básico |
  | Utilidad práctica | 20 % | 5 | Asistencia personal, mercado claro pero sin pruebas |
  | Creatividad y momento memorable | 15 % | 7 | Maquillar a una persona en directo es inolvidable y salió en tres medios |
  | Facilidad de uso y presentación | 15 % | 6 | Voz y relato fuerte; sin código |
  | **Total** | | **53** | |

- Replicabilidad en 48 h con SO-101: **media** (seguridad junto a la cara).
- Lección para LeWelder: el momento más fuerte es **el robot interactuando con el cuerpo o la herramienta de una
  persona**; nuestro equivalente es el robot sujetando la junta mientras el alumno suelda a su lado.

### Mochi-pounding · BLACK AI · Humanoid Hack Tokyo (Orboh, GMO Humanoid Lab), Tokio, 30-31 may 2026 · 1.º puesto

- Fuentes: [resumen de la nota de prensa](https://aeo.idaeo.ai/ai/robotmate-hub-com/en/news/2026-06-02-%E9%96%8B%E5%82%AC%E3%83%AC%E3%83%9D%E3%83%BC%E3%83%88-humanoid-hack-tokyo-%E4%BA%8B%E5%89%8D%E7%99%BB%E9%8C%B2100%E5%90%8D%E8%B6%85-uni)
  (original en PR TIMES).
- Qué hace: un humanoide Unitree G1 golpea mochi (pastel de arroz) con el gesto tradicional.
- Análisis técnico: Unitree G1; método de control y aprendizaje no publicados. Contexto del mismo evento: el 2.º
  (GOI) enseñó gestos de sushi al G1 **con un VLA**; un 3.º ex aequo (Aun) hizo la cadena completa
  teleoperación → aprendizaje → robot y fue "elogiado por la dificultad técnica". Es referencia, no brazo de bajo coste.
- Análisis de la aplicación: preservar oficios tradicionales enseñándoselos a robots. Momento memorable: el
  golpe del mazo.
- Por qué ganó: según la nota, "obtuvo la puntuación más alta en **completitud y originalidad**" y se valoró
  "enseñar a los robots los movimientos de oficios tradicionales y preservar la cultura".
- Valoración:

  | Criterio | Peso | Nota | Por qué |
  |---|---|---|---|
  | Funciona en vivo y se recupera | 30 % | 5 | "Completitud" máxima según el jurado, sin vídeo localizado |
  | Dificultad técnica | 20 % | 5 | Humanoide, pero sin saber si es aprendido |
  | Utilidad práctica | 20 % | 4 | Valor cultural más que práctico |
  | Creatividad y momento memorable | 15 % | 7 | Originalidad máxima según el jurado |
  | Facilidad de uso y presentación | 15 % | 5 | Solo nota de prensa |
  | **Total** | | **51** | |

- Replicabilidad en 48 h con SO-101: **baja** (otro robot).
- Lección para LeWelder: un **oficio tradicional enseñado por imitación** puntúa en originalidad; la soldadura
  como oficio que el robot aprende de un maestro es un relato del mismo tipo.

### BluPe · Andrew Lyubovsky · Junfan Labs Hackathon #35, Mountain View, ~25 oct 2026 · 3.º puesto, Mejor Hack de Hardware y Premio Abaka AI

- Fuentes: fragmentos de la [publicación del organizador](https://x.com/junfanzhu98/status/2114237384921678080)
  [no verificado]; sobre el modelo usado, [Dream-1 de Dream Labs](https://zeli.app/story/50223785).
- Qué hace: permite dar órdenes a brazos robóticos reales desde el navegador, con Dream-1 (modelo de acción
  generalista de Dream Labs) como "cerebro" [no verificado].
- Análisis técnico: brazos reales (modelo no publicado), interfaz web, modelo fundacional de terceros sin
  entrenamiento propio [hipótesis]. Sin repo localizado.
- Análisis de la aplicación: acceso remoto y sin código a robots; usuario: cualquiera con un navegador.
- Por qué ganó: tres premios, incluido el de hardware [no verificado]; sin detalle del jurado.
- Valoración:

  | Criterio | Peso | Nota | Por qué |
  |---|---|---|---|
  | Funciona en vivo y se recupera | 30 % | 5 | Finalista con premio, sin pruebas públicas |
  | Dificultad técnica | 20 % | 5 | Integración de un modelo externo; sin código |
  | Utilidad práctica | 20 % | 5 | Teleoperación por lenguaje desde web, sin datos |
  | Creatividad y momento memorable | 15 % | 5 | Sin evidencia del momento |
  | Facilidad de uso y presentación | 15 % | 5 | Navegador como interfaz, sin pruebas |
  | **Total** | | **50** | |

- Replicabilidad en 48 h con SO-101: **media** (depende del acceso a la API de Dream-1).
- Lección para LeWelder: una **interfaz que el jurado pueda usar él mismo** (web o voz) suma en facilidad de uso.

### Tactile-FLORA · Triton Droids · Junfan Labs Hackathon #35, Mountain View, ~25 oct 2026 · 2.º puesto y Mejor Logro Técnico

- Fuentes: fragmentos de la [publicación del organizador](https://x.com/junfanzhu98/status/2114237384921678080)
  [no verificado]. Sin repo localizado.
- Qué hace: ataca un cuello de botella del aprendizaje de robots: **etiquetar si cada demostración o ejecución
  tuvo éxito**, con sensado táctil [no verificado].
- Análisis técnico: sensor táctil + clasificador de éxito (detalles no publicados).
- Análisis de la aplicación: herramienta para quien entrena robots (limpiar datasets, evaluar políticas).
- Por qué ganó: "mejor logro técnico" [no verificado]; sin más datos.
- Valoración:

  | Criterio | Peso | Nota | Por qué |
  |---|---|---|---|
  | Funciona en vivo y se recupera | 30 % | 4 | Sin ninguna prueba pública |
  | Dificultad técnica | 20 % | 5 | Premiada como la mejor, pero sin pruebas |
  | Utilidad práctica | 20 % | 5 | Útil para investigadores, no para el público |
  | Creatividad y momento memorable | 15 % | 5 | Idea original, sin evidencia del momento |
  | Facilidad de uso y presentación | 15 % | 4 | Nada publicado |
  | **Total** | | **46** | |

- Replicabilidad en 48 h con SO-101: **baja** (sensores táctiles).
- Lección para LeWelder: **detectar automáticamente si la tarea salió bien** (aunque sea con visión clásica)
  permite reintentar solo y mostrar el marcador de aciertos.

### Cloth Folding Robot · equipo sin nombre publicado · Seeed Embodied AI Hackathon, sesión EE. UU., oct 2025 · 3.º puesto

- Fuentes: [crónica de Seeed](https://seeed.cc/post/2025-embodied-ai-hackathon-recap). Sin repo ni vídeo.
- Qué hace: dos SO-101 doblan una camiseta.
- Análisis técnico: bimanual SO-101; **ACT** ajustado en ~día y medio; Isaac Sim para generar escenarios y una
  **función de recompensa aprendida para refuerzo** que recupera errores no vistos (según la crónica, sin más
  detalle). Episodios y cámaras: no publicados.
- Análisis de la aplicación: tarea doméstica clásica; se entiende sin explicar.
- Por qué ganó: sin palabras del jurado. [hipótesis] Ambición técnica (ACT + simulación + refuerzo) en una tarea
  de tela, que es difícil.
- Valoración:

  | Criterio | Peso | Nota | Por qué |
  |---|---|---|---|
  | Funciona en vivo y se recupera | 30 % | 4 | Sin pruebas de la ejecución |
  | Dificultad técnica | 20 % | 5 | Muy ambicioso según la crónica, no comprobable |
  | Utilidad práctica | 20 % | 5 | Doblar ropa es útil, sin pruebas |
  | Creatividad y momento memorable | 15 % | 4 | Doblar ropa ya ganó en 2025 |
  | Facilidad de uso y presentación | 15 % | 3 | Nada publicado |
  | **Total** | | **43** | |

- Replicabilidad en 48 h con SO-101: **baja** (bimanual y tela; el refuerzo en 48 h es improbable).
- Lección para LeWelder: la recuperación ante errores **se anuncia en la crónica**: si la tenemos, hay que
  enseñarla en vivo y contarla en el pitch.

---

## 2. Tabla resumen (ordenada por total)

| # | Proyecto | Hackathon | Puesto | Política | Episodios | Total |
|---|---|---|---|---|---|---|
| 1 | Donuts Order Assistant (GreatAkihabara) | AMD Open Robotics, Tokio, dic 2025 | 1.º | SmolVLA multitarea por texto + modelo aparte + RTC | 120 (180 grabados) + 30 | **71** |
| 2 | Matcha Making (UIUC SIGRobotics) | Seeed/NVIDIA/HF, EE. UU., oct 2025 | 1.º | GR00T N1.5 | ~30 por subtarea × 3 [no verificado] | **64** |
| 3 | Tubos de ensayo | CCSF Robotics Hack, SF, nov 2026 | 1.º | ACT + pinzas impresas | no publicado | **61** |
| 4 | Desk cleanup GR00T | Seeed/NVIDIA/HF, Shenzhen, oct 2025 | 1.º | GR00T N1.5 | 300 (10 % sim) | **61** |
| 5 | CaliKPR | Junfan Labs #35, Mountain View, oct 2026 | 1.º | Ninguna: Claude + 28 herramientas MCP | 0 | **58** |
| 6 | Sprinkle (CMU) | Seeed/NVIDIA/HF, EE. UU., oct 2025 | 2.º | 4 × SmolVLA | 170 | **57** |
| 7 | Armtender | Hack Club Prototype, dic 2025 (CES 2026) | 1.º | ACT | ~120 + 50 | **54** |
| 8 | Iron Bestie | Physical AI Hackathon, Hong Kong, ago 2026 | Premio principal | no publicada | no publicado | **53** |
| 9 | Mochi-pounding (BLACK AI) | Humanoid Hack Tokyo, may 2026 | 1.º | no publicada (G1) | no publicado | **51** |
| 10 | BluPe | Junfan Labs #35, oct 2026 | 3.º | Dream-1 (modelo externo) | 0 [hipótesis] | **50** |
| 11 | Tactile-FLORA (Triton Droids) | Junfan Labs #35, oct 2026 | 2.º | clasificador táctil | no publicado | **46** |
| 12 | Cloth Folding | Seeed/NVIDIA/HF, EE. UU., oct 2025 | 3.º | ACT + Isaac Sim + RL | no publicado | **43** |

Nota: los proyectos de 2026 puntúan más bajo sobre todo porque **publican mucho menos** (sin repo ni vídeo); no
es necesariamente que sean peores.

---

## 3. Patrones comunes de los ganadores

1. **Los VLA ya ganan, pero troceados.** De los 8 ganadores con política conocida, 4 usan VLA (SmolVLA ×2,
   GR00T ×2) y 3 usan ACT. Ningún VLA ganador hace la tarea entera con un solo modelo y una sola instrucción:
   GreatAkihabara separa "cerrar la caja"; Sprinkle usa 4 modelos; Matcha, 3 subtareas.
2. **Cómo demuestran que es un VLA**: variando la instrucción en vivo (GreatAkihabara: "chocolate" frente a
   "fresa"; antes, "un plato" frente a "dos platos"), con un chatbot o voz delante y con generalización visible
   (Desk cleanup: varias luces y objetos, 10 % de datos simulados con aleatorización).
3. **Sin memoria, estados visibles.** Los VLA no recuerdan; los ganadores **diseñan el escenario** para que cada
   paso se distinga: recipiente que se deja caer, cuenco marcado como vacío o lleno, LED que confirma la
   pulsación, plato que gira, campana de fin.
4. **Señal física de "terminado"**: campana (GreatAkihabara), LED (Sprinkle), ventanilla de entrega (Armtender).
   El público ve que la tarea acabó sin que nadie lo diga.
5. **Hardware propio pequeño y decisivo**: pinzas impresas (CCSF), ruleta con ESP32 (Armtender), botón calabaza
   con sensor (Sprinkle), campana USB (GreatAkihabara).
6. **Un humano y un servicio en el centro**: pedido de donuts, bebida, matcha, maquillaje, laboratorio.
7. **Volumen moderado**: 30 episodios por subtarea a 180 en total; solo un ganador pasa de 300, y grabó el 70 %
   antes del evento. Ajuste fino con ~50 episodios centrados en los fallos (Armtender).
8. **Alineación con el patrocinador**: GR00T + Jetson Thor en el evento de NVIDIA; MI300X en el de AMD; Claude/MCP
   y fiabilidad en el de Junfan Labs.
9. **2026 premia la fiabilidad medida**: el ganador de Junfan #35 venció a ACT, SmolVLA y pi0.5 (384 episodios)
   con 20/20 y el tema del jurado fue la "confianza"; en CCSF ganó el que llegó con la política lista.
   Los criterios publicados por MakerMods incluyen literalmente "la demo funciona en el escenario".
10. **Originalidad cultural**: en Tokio ganaron el mochi y el sushi (oficios tradicionales enseñados a un robot);
    el jurado citó "completitud y originalidad".

### Qué significa para LeWelder

- Nuestra arquitectura (voz → gestor de estado → SmolVLA multitarea) es la del ganador mejor documentado
  (GreatAkihabara). Planificar desde el principio un **modelo aparte para la subtarea que falle** en el multitarea.
- Diseñar el banco para que **cada junta montada se vea distinta** de la anterior y añadir una **señal de fin**
  (luz o sonido) cuando el robot termina de montar y cuando el alumno termina de soldar.
- Llevar un **marcador de aciertos medido** (intentos y éxitos durante el evento) para el jurado: es lo que
  premiaron los ganadores de 2026.
- Contar la soldadura como **oficio que el robot aprende de un maestro**: puntúa en originalidad como el mochi.

---

## 4. Fuentes

Proyectos:
- GreatAkihabara: https://github.com/masato-ka/GreateAkihabra_9_AMDOpenRoboticsHackathon ·
  https://huggingface.co/datasets/masato-ka/donuts-shop-dataset-v0 ·
  https://huggingface.co/datasets/masato-ka/donuts-shop-close-box-dataset-v0 ·
  https://huggingface.co/masato-ka/smolvla-donuts-shop-v1-100k ·
  https://huggingface.co/datasets/LeRobot-worldwide-hackathon/164-great-akihabara-plate-inst
- AMD Open Robotics: https://www.amd.com/en/developer/resources/technical-articles/2025/amd-open-robotics-hackathon-recap.html ·
  https://huggingface.co/blog/amd/openroboticshackathon · https://zenn.dev/mkj/articles/317e39955e1343 ·
  https://www.datamonsters.com/post/amd-and-data-monsters-building-the-ai-developer-community-in-2025
- Seeed/NVIDIA/HF 2025: https://seeed.cc/post/2025-embodied-ai-hackathon-recap ·
  https://www.hackster.io/sigrobotics/matcha-bot-sigrobotics-embodied-ai-hackathon-1st-place-f0e520 ·
  https://labs.ri.cmu.edu/mrsd-news/mrsds-winning-the-2025-embodied-ai-hackathon/ ·
  https://github.com/Lee-LEO-H/Lerobot-GR00TN1.5
- CCSF: https://worldwidestudios.substack.com/p/ccsf-robotics-hack-recap-1-day-build
- Junfan Labs #35: https://x.com/junfanzhu98/status/2114237384921678080 · https://hk.linkedin.com/in/sibeichen
- Armtender: https://github.com/afia-ava/Armtender · https://x.com/AMD/status/2010027341154791713 ·
  https://www.webpronews.com/teen-barista-bot-how-a-chapel-hill-high-schoolers-ai-arm-snagged-20000-and-ces-spotlight ·
  https://blueprint.hackclub.com/prototype
- Hong Kong: https://www.silicon.co.uk/ai-2/hong-kong-make-up-robot-631068 ·
  https://www.chinadailyhk.com/article/637499 · https://www.chinadailyhk.com/hk/article/637715 ·
  https://www.scmp.com/tech/tech-trends/article/3363197/coded-glamour-and-glory-ai-make-arm-steals-show-hong-kong-hackathon
- Humanoid Hack Tokyo: https://aeo.idaeo.ai/ai/robotmate-hub-com/en/news/2026-06-02-%E9%96%8B%E5%82%AC%E3%83%AC%E3%83%9D%E3%83%BC%E3%83%88-humanoid-hack-tokyo-%E4%BA%8B%E5%89%8D%E7%99%BB%E9%8C%B2100%E5%90%8D%E8%B6%85-uni

Eventos sin ganadores aprovechables:
- https://physical-ai-hack.pages.dev/ · https://physical-ai-hack-world-tour-82m.pages.dev/ep02-sf ·
  https://clawspiral.pages.dev/news/2026-05-04-physical-ai-openclaw-hackathon-shenzhen ·
  https://luma.com/zsaa3r3d ·
  https://engineering.purdue.edu/Engr/AboutUs/News/Spotlights/2026/2026-0519-purdue-starkhacks-hardware-hackathon ·
  https://forums.developer.nvidia.com/t/the-results-are-in-meet-the-nvidia-cosmos-cookoff-winners-see-them-live-on-april-16/366130 ·
  https://www.amd.com/en/developer/resources/technical-articles/2026/lessons-from-the-amd-devmaster-hackathon.html ·
  https://micxael.github.io/robohacks/ · https://github.com/FunRobots/robot-pizza-cup ·
  https://github.com/MaxBingham/RoboticsHackCal · https://sagar-os.vercel.app/blog/physical-ai-hackathon ·
  https://www.electronicsforu.com/news/ai-breaks-the-fourth-wall-inside-arduinos-physical-ai-challenge-india-2026

Fuentes que no se pudieron leer directamente (403, 503 o inicio de sesión): Hackster (Matcha), SCMP, LinkedIn,
X, la crónica de AMD de 2025 en esta sesión (se usa lo ya extraído en `analisis-concursos.md`) y lablab.ai
(redirige a otro dominio).
