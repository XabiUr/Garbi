# Ganadores de hackathons europeos de robótica con aprendizaje (2026 y finales de 2025)

Fecha: 18-11-2026. Para: equipo Robotalde (LeWelder), Hackathon LeRobot Bilbao II (20-22 nov 2026).
Complementa [../analisis-concursos.md](../analisis-concursos.md); no repite su análisis de no premiados.

**Cómo leer este documento**

- Cada proyecto sigue la plantilla del equipo. Todo lo que no aparece en una fuente leída va marcado con
  **[no verificado]**. Las hipótesis van marcadas como tales.
- **Rúbrica** (supuesta para Bilbao): funciona en vivo y se recupera 30 %, dificultad técnica 20 %, utilidad
  práctica 20 %, creatividad y momento memorable 15 %, facilidad de uso y presentación 15 %.
  Total = Σ(nota × peso) / 10, sobre 100. Lo que no se puede comprobar con fuentes no pasa de 5. Los vídeos
  enlazados no se han revisado fotograma a fotograma: ninguno llega a 10 en "en vivo".
- **Alcance real de lo encontrado.** En 2026 hay muchos hackathons europeos de "Physical AI", pero pocos publican
  ganadores con repositorio. Se han encontrado ganadores con evidencia en Vitoria, Ámsterdam, Múnich, Zúrich y
  (finales de 2025) París y Bilbao. Varios eventos de 2026 con SO-101 no han publicado ganadores (lista al
  final). Se añade como referencia técnica la LeHome Challenge (ICRA 2026, Viena), que es una competición y no
  un hackathon, y dos premiados europeos del LeRobot Worldwide 2025.

---

## 1. Hackathons de 2026

### Asistente de soldadura con linterna · MSN (U. Málaga, 3 estudiantes) · Robotekin Hackathon LeRobot, Vitoria-Gasteiz, 23-25 oct 2026 · 1.º (1.500 €)
- **Fuentes:** [repo](https://github.com/flipiflopi/Hackaton_Robotekin_SO-101_MSN),
  [dataset](https://huggingface.co/datasets/FlipiFlopi007/so101_tumbada_full),
  [modelo](https://huggingface.co/FlipiFlopi007/act_tumbada),
  [crónica Robotekin](https://robotekin.com/robotekin-reune-en-alava-a-casi-80-jovenes-para-entrenar-robots-con-inteligencia-artificial/).
  17 equipos, 66 participantes.
- **Qué hace:** el SO-101 coge una linterna tumbada y alumbra el punto de una PCB que el operario marca con un
  boli. Si algo tapa el haz, busca otro ángulo y vuelve a iluminar. Se maneja por voz.
- **Análisis técnico:**
  - Robot: SO-101 leader + follower. Cámaras: muñeca 640×480 y Logitech C920 fija en diagonal. PC con Windows 11
    y RTX 3050 Laptop de 4 GB.
  - Política: **un solo ACT** para coger la linterna. 54 episodios, 20.770 frames, 2 cámaras. 20.000 pasos con
    batch 4 y aumentos de imagen; usan el checkpoint 18.000. Antes de entrenar recortan los tramos quietos.
  - Capas extra: fase 2 sin aprendizaje. Visión clásica detecta la PCB y la punta del boli. **IBVS** (control
    visual con jacobiana imagen↔efector corregida en línea con Broyden). Esquive con 3 parábolas y vuelta a la
    pose buena. Voz con Google SpeechRecognition y "pulsar M para hablar".
  - Aprendido: el agarre. Programado: apuntar, esquivar y recuperarse.
- **Aplicación:** el problema es la "tercera mano" del soldador de electrónica. El usuario es el técnico en el
  banco. En la demo se entiende al instante: el jurado pone la mano delante y la luz se mueve.
  **Momento memorable:** la luz rodea la mano. El log de la demo guardado registra 4 oclusiones, todas resueltas.
- **Por qué ganó:** la crónica no da palabras del jurado. Hipótesis: caso humano claro, recuperación demostrada,
  voz, y fiabilidad gracias a la división ACT + visión clásica.
- **Valoración:**

  | Criterio | Peso | Nota | Por qué |
  |---|---|---|---|
  | Funciona en vivo y se recupera | 30 % | 8 | Log público de una ejecución con 4 oclusiones resueltas y vídeo de 35 s. |
  | Dificultad técnica | 20 % | 7 | IBVS con Broyden y esquive en un SO-101; la parte aprendida es solo un agarre. |
  | Utilidad práctica | 20 % | 7 | Problema real de banco de electrónica, aunque el valor de una linterna es modesto. |
  | Creatividad y momento memorable | 15 % | 7 | La luz que esquiva la mano es fácil de recordar. |
  | Facilidad de uso y presentación | 15 % | 8 | Voz con frases naturales, README excelente, dataset y modelo publicados. |
  | **Total** | | **74,5** | |

- **Replicabilidad en 48 h con SO-101:** alta. Lo ha hecho un equipo de 3 en 48 h con una GPU de 4 GB.
- **Lección para LeWelder:** es el precedente más cercano y ya ganó. Hay que superarlo en dos cosas: que la parte
  aprendida sea más vistosa que un agarre (montar la junta) y que la recuperación sea igual de visible.

### Tareas domésticas con OpenArm bimanual · MURobot (Mondragon Unibertsitatea, 5) · Robotekin, Vitoria-Gasteiz, 23-25 oct 2026 · 2.º (900 €)
- **Fuentes:** [crónica Robotekin](https://robotekin.com/robotekin-reune-en-alava-a-casi-80-jovenes-para-entrenar-robots-con-inteligencia-artificial/).
  Sin repo público encontrado.
- **Qué hace:** un OpenArm de Enactic de dos brazos, traído por el equipo, aprende tareas de casa (limpiar un
  plato, hacer una tostada). Las demostraciones humanas se transfieren con un sistema de captura de movimiento
  externo.
- **Análisis técnico:** robot OpenArm bimanual; demostraciones por captura de movimiento (la crónica habla de
  "exoesqueleto"/captura). Política, cámaras, episodios y entrenamiento **[no verificado]**.
- **Aplicación:** asistencia doméstica. En la demo destaca el tamaño del robot frente a los SO-101 del resto.
- **Por qué ganó:** hipótesis: hardware propio claramente superior y bimanualidad, que parecen difíciles a simple
  vista.
- **Valoración:**

  | Criterio | Peso | Nota | Por qué |
  |---|---|---|---|
  | Funciona en vivo y se recupera | 30 % | 5 | Sin vídeo ni log públicos. |
  | Dificultad técnica | 20 % | 7 | Bimanual con captura de movimiento propia, según la crónica. |
  | Utilidad práctica | 20 % | 6 | Tareas domésticas reales, lejos de un producto. |
  | Creatividad y momento memorable | 15 % | 5 | Tarea esperable; lo que destaca es el robot, no la idea. |
  | Facilidad de uso y presentación | 15 % | 4 | Nada reproducible publicado. |
  | **Total** | | **54,5** | |

- **Replicabilidad en 48 h con SO-101:** baja. Depende de un robot y un sistema de captura que no tenemos.
- **Lección para LeWelder:** el hardware que destaca suma puntos ante este jurado. Nuestra antorcha con LED y las
  piezas impresas tienen que verse bien en la mesa, no esconderse.

### Robotticelli · equipo de 6 (Antoine, Daniel, Ilai, Lucas, Shaikha, Takako) · La Machine (Tech Makers), Ámsterdam, 2-4 oct 2026 [año inferido] · 1.º
- **Fuentes:** [repo](https://github.com/Danitell0/robotticelli) ("La Machine ... #1 winner"),
  [post de un miembro en LinkedIn](https://ch.linkedin.com/in/darrenhargan), [evento](https://luma.com/ni360mav).
  El año sale de otro repo del mismo evento, fechado el 3-10-2026 ([Handy](https://github.com/marinmarian/la-machine-benchbot)).
  Que Robotticelli sea de esa misma edición es **[no verificado]**.
- **Qué hace:** un SO-101 con un boli dibuja formas, palabras, imágenes, retratos sacados con la webcam o lo que
  le pidas a un LLM. Tiene además modos de baile y de "gato enfadado" que tira cosas de la mesa.
- **Análisis técnico:**
  - Robot: un SO-101 follower con un boli en la pinza y una webcam.
  - **Sin política aprendida y sin cinemática inversa.** Con el par desactivado se enseñan a mano 9 puntos del
    papel (rejilla 3×3) y una pose en el aire; cualquier punto se interpola entre las poses enseñadas.
  - Imagen → trazos: contorno con gpt-image-1 u OpenCV, esqueletizado a SVG, simplificación, orden de trazos y
    perfiles de velocidad suaves para que los servos no den tirones.
  - LLM: Claude u OpenAI dibujan a partir de un texto ("Try your luck").
  - Aprendido: nada en el robot. Programado: todo. Movimientos del "gato" grabados a mano.
- **Aplicación:** entretenimiento y arte. Se entiende en un segundo: te sacas una foto y el robot te dibuja.
  **Momento memorable:** el retrato del jurado y la "rabieta" del brazo.
- **Por qué ganó:** sin palabras del jurado. Hipótesis: espectáculo y participación del público; el post del
  equipo destaca lo suave que dibujaban unos servos baratos.
- **Valoración:**

  | Criterio | Peso | Nota | Por qué |
  |---|---|---|---|
  | Funciona en vivo y se recupera | 30 % | 5 | Solo hay relato del propio equipo; Ctrl+C devuelve el brazo a la pose inicial. |
  | Dificultad técnica | 20 % | 5 | Buena tubería de imagen a trazos, pero sin aprendizaje ni control en lazo cerrado. |
  | Utilidad práctica | 20 % | 3 | Puro entretenimiento. |
  | Creatividad y momento memorable | 15 % | 8 | Retrato en vivo, baile y rabieta: muy memorable. |
  | Facilidad de uso y presentación | 15 % | 8 | Menú, modo simulado y funciona sin claves de API. |
  | **Total** | | **55,0** | |

- **Replicabilidad en 48 h con SO-101:** alta. No hay que grabar ni entrenar.
- **Lección para LeWelder:** en un hackathon generalista gana el espectáculo con participación del público. En
  Bilbao (hackathon LeRobot) eso no basta: la parte aprendida tiene que estar, pero conviene copiar la idea de
  "el jurado se lleva algo hecho por el robot" (por ejemplo, su junta soldada con nota).

### RoBoost · equipo RoBoost · EUROPE EMBODIED 48h Hackathon (TUM, Múnich, jun 2026) · 1.º absoluto y ganador del reto de brazo industrial de Intel (2.000 € + 5.000 € en créditos de Claude)
- **Fuentes:** [repo](https://github.com/Thierryonre/RoBoost),
  [crónica TUM International](https://tum-international.com/europe-embodied-2026-48-hour-hackathon/)
  (350+ solicitudes, 108 seleccionados, 3 retos), [repo de otro equipo del mismo reto](https://github.com/M4RKUS28/Robo67)
  (describe el hardware del reto de Intel).
- **Qué hace:** da a un robot guiado por un modelo de visión y lenguaje (VLM) un sentido extra, el peso. Coge el
  objeto, lo pesa y decide dónde dejarlo: dos botellas iguales, una llena y otra vacía, acaban en sitios
  distintos.
- **Análisis técnico:**
  - Hardware: Intel RealSense con profundidad. El reto de Intel usaba un Franka Panda según el repo Robo67; que
    RoBoost usara ese mismo brazo es **[no verificado]**.
  - Visión: segmentación con Ultralytics (YOLO) y OpenVINO, centroide y profundidad del objeto más cercano.
  - En el repo público, la clase del brazo son funciones vacías y `calculateWeight()` devuelve siempre 200: el
    control real del brazo y la medida de peso no están publicados **[no verificado]**.
  - No hay política aprendida por imitación en el repo; lo "aprendido" es la percepción preentrenada.
- **Aplicación:** reciclaje o logística (lleno/vacío, pesado/ligero). Se entiende fácil: "ve igual, pesa distinto".
- **Por qué ganó:** la crónica destaca que amplía lo que puede percibir un robot guiado por VLM, que era
  exactamente la pregunta del reto de Intel. Hipótesis: encajar al 100 % con el enunciado del patrocinador.
- **Valoración:**

  | Criterio | Peso | Nota | Por qué |
  |---|---|---|---|
  | Funciona en vivo y se recupera | 30 % | 4 | Sin vídeo; el código público no mueve el brazo. |
  | Dificultad técnica | 20 % | 5 | Percepción con profundidad bien montada; el resto no se puede comprobar. |
  | Utilidad práctica | 20 % | 7 | Clasificar por peso es útil en reciclaje y almacén. |
  | Creatividad y momento memorable | 15 % | 7 | "Dar tacto a un VLM" es una idea clara y vendible. |
  | Facilidad de uso y presentación | 15 % | 5 | README claro, pero nada reproducible. |
  | **Total** | | **54,0** | |

- **Replicabilidad en 48 h con SO-101:** media. El par de los STS3215 da una estimación de carga, pero ruidosa.
- **Lección para LeWelder:** un mensaje de una frase que responde a la pregunta del jurado gana. Debemos tener la
  nuestra ("el robot prepara la junta, tú sueldas y la visión te pone nota") y decirla en los primeros 15 s.

### Talos (robot que trepa entre paredes) · Anna Polova, Heorhii Zolotarevskyi, Aarrav Anil, Leonardo Achá Boiano · ERH Physical AI Hackathon, DARE Campus, Zúrich, 16-18 oct 2026 · ganadores
- **Fuentes:** [repo](https://github.com/Annnnya/talos_hack) ("The team won the hackathon"),
  [anuncio en LinkedIn](https://www.linkedin.com/feed/update/urn:li:activity:7521900692014288898/).
  Unos 60 estudiantes y 3 retos patrocinados (Black Forest Labs, Daidai Labs, coprod). Si ganaron la general o
  un reto concreto es **[no verificado]**.
- **Qué hace:** robot en forma de V invertida con ruedas mecanum que, junto a dos paredes, abre la bisagra hasta
  apretarlas y sube entre ellas (limpieza de chimeneas o conductos).
- **Análisis técnico:** Raspberry Pi 5, servos Feetech STS (los mismos del SO-101) para 4 ruedas y bisagra, IMU
  MPU6050 con EKF, cámara de la Pi, ROS 2 Jazzy con ros2_control y web con joystick en el móvil. Construido desde
  cero con piezas impresas. **Sin aprendizaje**: máquina de estados (libre → alinear → apretar → trepar).
- **Aplicación:** inspección y limpieza de huecos verticales. Momento memorable: el robot subiendo entre dos
  tableros.
- **Por qué ganó:** hipótesis: hardware nuevo hecho en 36 h que hace algo físico sorprendente.
- **Valoración:**

  | Criterio | Peso | Nota | Por qué |
  |---|---|---|---|
  | Funciona en vivo y se recupera | 30 % | 5 | Solo una foto trepando; sin vídeo revisado. |
  | Dificultad técnica | 20 % | 7 | Mecanismo, electrónica y ROS 2 desde cero en 36 h. |
  | Utilidad práctica | 20 % | 6 | Inspección de conductos es real; prototipo muy inicial. |
  | Creatividad y momento memorable | 15 % | 8 | Ver trepar un robot entre paredes sorprende. |
  | Facilidad de uso y presentación | 15 % | 6 | Joystick web desde el móvil, buena documentación. |
  | **Total** | | **62,0** | |

- **Replicabilidad en 48 h con SO-101:** no aplica (no usa SO-101 ni aprendizaje).
- **Lección para LeWelder:** en los "Physical AI" generalistas de 2026 ganan proyectos sin aprendizaje. En el
  mismo evento, un equipo del reto de Daidai ([pour_skill](https://github.com/Nailec101/pour-skill)) hizo un
  barman con OpenArm que vierte M&M's en lazo cerrado por visión y par motor: otra vez el camarero, como en Bilbao
  2025. Hay que evitar parecernos a un camarero.

### LeHome Challenge, final real · Ilia Larchenko (en solitario) · ICRA 2026, Viena, jun 2026 · 2.º en la final real (865/1.080) y 1.º de 62 en simulación (referencia, no es un hackathon)
- **Fuentes:** [página del proyecto](https://ilialarchenko.com/projects/lehome2026/),
  [artículo](https://arxiv.org/html/2606.27163v2), 3.º real: [Aakash Arul Mozhi Nambi](https://aarvis.github.io/lehome2026/).
  El 1.º real tiene fuentes contradictorias (895 puntos) **[no verificado]**.
- **Qué hace:** dos SO-101 doblan prendas (camiseta de manga larga y corta, pantalón largo y corto) sin saber de
  antemano qué prenda es, con jurado en el sitio y robot de evaluación que los equipos no habían tocado.
- **Análisis técnico:**
  - Robot: SO-101 bimanual, acción de 12 dimensiones, 3 cámaras RGB.
  - Política: **π0.5** (VLA) única para las 4 prendas, con cabezas auxiliares (éxito, progreso, tipo de prenda).
  - Entrenamiento: RL asíncrono en simulación con una H200 que publica un checkpoint cada ~40 min en el Hub; ajuste
    real con 60 % datos de la organización, 30 % teleoperación y correcciones DAgger propias, 10 % simulación
    aumentada. Episodios totales **[no verificado]**.
  - Trucos de inferencia: replanificar cada ~5 pasos en vez de ejecutar el bloque de 30, elegir el mejor de 2-3
    muestras, guía sin clasificador alta.
  - El 3.º usó π0.5 con 4.180 demostraciones humanas, 1.000 de simulación y 500 reales, en 8×H100.
- **Aplicación:** doblar ropa en casa. Partes puntuadas por calidad del doblado; prendas no vistas valen +50 %.
- **Por qué quedó 2.º:** puntuación objetiva del jurado. Fallos que cita: poca destreza, se queda atascado cerca
  del éxito y se sobreajusta a la simulación.
- **Valoración:**

  | Criterio | Peso | Nota | Por qué |
  |---|---|---|---|
  | Funciona en vivo y se recupera | 30 % | 8 | Evaluado en vivo por jurado en un robot ajeno, con puntuación publicada. |
  | Dificultad técnica | 20 % | 10 | Prenda deformable, bimanual, VLA + RL + DAgger: lo más difícil de la lista. |
  | Utilidad práctica | 20 % | 7 | Doblar ropa es un deseo doméstico real. |
  | Creatividad y momento memorable | 15 % | 5 | Tarea fijada por la organización. |
  | Facilidad de uso y presentación | 15 % | 6 | Muy documentado para expertos; no hay experiencia de usuario. |
  | **Total** | | **74,5** | |

- **Replicabilidad en 48 h con SO-101:** baja. Exige semanas de cómputo con GPU grandes.
- **Lección para LeWelder:** dos trucos baratos que sí podemos copiar: **replanificar más a menudo** (menos
  `n_action_steps`) mejora la reacción, y **2-3 rondas cortas de corrección (DAgger)** grabando justo donde falla
  la política dan mejoras visibles en cada ronda.

---

## 2. Finales de 2025 (referencia)

### Flip & Ship · Inverse Kinema-tricks (Xiao Feng, Giacomo Randazzo, Nicolas Rodriguez) · AMD Open Robotics Hackathon, STATION F, París, 12-14 dic 2025 · 1.º de 25 equipos
- **Fuentes:** [repo](https://github.com/NRdrgz/AMD_Robotics_Hackathon_2025_InverseKinematricks),
  [vídeo](https://www.youtube.com/watch?v=QZKOs_gODcs),
  [crónica AMD con ganadores](https://www.amd.com/en/developer/resources/technical-articles/2025/amd-open-robotics-hackathon-recap.html),
  datasets: [coger](https://huggingface.co/datasets/giacomoran/hackathon_amd_mission2_blue_pick_cardboard),
  [voltear](https://huggingface.co/datasets/giacomoran/hackathon_amd_mission2_black_flip),
  [clasificar](https://huggingface.co/datasets/giacomoran/hackathon_amd_mission2_black_sort_fixed).
- **Qué hace:** minicentro logístico inspirado en el vídeo de Figure en Amazon. Un brazo deja paquetes en una cinta;
  al final, otro brazo **voltea** el paquete si el código no se ve, o lo **clasifica** por color si se ve.
- **Análisis técnico:**
  - Hardware: 2 SO-101, 3 cámaras de la organización, **cinta transportadora casera** con un motor paso a paso de
    una impresora 3D y cinta adhesiva.
  - Políticas: 3 SmolVLA (coger; voltear; clasificar). Primero ACT (10.000 pasos en 50 min en MI300X), después
    SmolVLA (80.000 pasos en 5 h). Datos en el Hub: 126, 150 y 145 episodios, cámaras top + muñeca, grabados de
    día y de noche.
  - Capas extra: visión clásica que detecta el paquete y decide la política; máquina de estados
    (RUNNING/FLIPPING/SORTING) en otro ordenador por WebSocket; 2 hilos por brazo con cola de acciones (inspirado
    en RTC) para **cambiar de política sin parar**; RTC para suavizar; web de seguimiento.
  - Inferencia de las 3 SmolVLA en el portátil (Radeon 890M, 8 GB de RAM usados).
  - Aprendido: coger, voltear, clasificar. Programado: qué política se activa y la cinta.
- **Aplicación:** centros de paquetería. Se entiende sin explicación porque el público conoce el vídeo de Figure.
  **Momento memorable:** el paquete llega boca abajo, el brazo lo voltea y luego lo clasifica.
- **Por qué ganó:** AMD dice de los ganadores de París: "strong system integration, thoughtful problem solving, and
  compelling demonstrations". Hipótesis: es el que más encadena (dos brazos, cinta, tres habilidades).
- **Valoración:**

  | Criterio | Peso | Nota | Por qué |
  |---|---|---|---|
  | Funciona en vivo y se recupera | 30 % | 7 | Vídeo público del sistema completo; el voltear es en sí una recuperación. |
  | Dificultad técnica | 20 % | 9 | Dos brazos, tres políticas, cambio sin latencia y cinta propia. |
  | Utilidad práctica | 20 % | 7 | Copia una tarea logística real. |
  | Creatividad y momento memorable | 15 % | 7 | Voltear paquetes nunca se había visto en estos hackathons, según el equipo. |
  | Facilidad de uso y presentación | 15 % | 7 | Web de seguimiento, README modélico, todo en el Hub. |
  | **Total** | | **74,0** | |

- **Replicabilidad en 48 h con SO-101:** media. Necesita dos brazos, ~420 episodios y GPU grande en la nube.
- **Lección para LeWelder:** **un selector programado que elige entre habilidades aprendidas** es el patrón
  ganador; es exactamente nuestro SmolVLA multitarea con la orden por voz. Y grabar con dos luces distintas
  (día/noche) protege la demo.

### Conecta 4 contra el robot · Bartolos Crew (Team 15: Josu Gorostegui, Jorge Lamperez) · AMD Open Robotics Hackathon, París, 12-14 dic 2025 · 3.º (empatado)
- **Fuentes:** [repo](https://github.com/jgorostegui/AMD_Robotics_Hackathon_Team15) (dice "3rd place"),
  [dataset](https://huggingface.co/datasets/jlamperez/mission2_smolvla_multitask_v2_120ep),
  [modelo](https://huggingface.co/jlamperez/mission2_smolvla_multitask_policy_30ksteps_120ep),
  [crónica AMD](https://www.amd.com/en/developer/resources/technical-articles/2025/amd-open-robotics-hackathon-recap.html).
- **Qué hace:** el robot juega a Conecta 4 (tablero de 5×5) contra una persona: mira el tablero, decide la
  jugada y coloca su ficha.
- **Análisis técnico:** SO-101; visión del tablero con calibración (HSV/Hough) servida por HTTP; motor de juego
  con minimax; **una SmolVLA multitarea** (120 episodios, 5 tareas = 5 columnas, 3 cámaras, 30.000 pasos en
  MI300X) a la que se le pasa la jugada como texto. Panel en Streamlit y modo simulado sin hardware.
  Aprendido: colocar la ficha en la columna pedida. Programado: visión, reglas y estrategia.
- **Aplicación:** juego con humano en el centro. Momento memorable: el robot gana o bloquea la jugada.
- **Por qué quedó 3.º:** hipótesis: integración limpia y uso correcto de la multitarea por lenguaje; utilidad
  baja frente al 1.º.
- **Valoración:**

  | Criterio | Peso | Nota | Por qué |
  |---|---|---|---|
  | Funciona en vivo y se recupera | 30 % | 5 | No hay vídeo ni tasa de éxito publicados. |
  | Dificultad técnica | 20 % | 7 | Visión + minimax + VLA multitarea con 3 cámaras. |
  | Utilidad práctica | 20 % | 4 | Juego. |
  | Creatividad y momento memorable | 15 % | 6 | Jugar contra la máquina implica al público; idea conocida (ajedrez, tres en raya). |
  | Facilidad de uso y presentación | 15 % | 7 | Panel único, calibración guiada, modo simulado. |
  | **Total** | | **56,5** | |

- **Replicabilidad en 48 h con SO-101:** alta. 120 episodios y una SmolVLA.
- **Lección para LeWelder:** su diseño es casi el nuestro: **una tarea por destino** ("columna 3" ↔ "junta en T")
  dentro de una SmolVLA y la orden como texto. 120 episodios para 5 tareas (~24 por tarea) les bastó para podio.

### Le Coup de Pouce (instrumentista por voz) · Team 11 IFT, ESILV (Lucas Jourdet, Fabien Pieretti, Léo Guérin, Victor Ranguin) · AMD Open Robotics Hackathon, París, 12-14 dic 2025 · 3.º empatado según ESILV [discrepancia]
- **Fuentes:** [repo](https://github.com/leogue/AMD_Robotics_Hackathon_2025_LeCoup_De_Pouce),
  [noticia ESILV](https://www.esilv.fr/robotique-et-ia-des-etudiants-de-lesilv-sur-le-podium-du-paris-open-robotics-hackathon/amp/).
  **Discrepancia:** ESILV dice que sus dos equipos quedaron 3.º empatados, pero la lista de AMD da como 3.º a los
  equipos 15, 13, 12 y 9, no al 11. El puesto es **[no verificado]**.
- **Qué hace:** el cirujano pide por voz guantes, pinzas o jeringa y el robot coge el instrumento de su
  compartimento y se lo da en la mano.
- **Análisis técnico:** SO-101; **SmolVLA** con una tarea por instrumento; objetos en compartimentos fijos y
  posiciones variadas; reconocimiento de palabra clave por micrófono; orden "stop", tiempo máximo de 30 s y una
  orden nueva sustituye a la anterior. Probaron también control por EEG con un Muse. Episodios y pasos
  **[no verificado]** (la plantilla del README no está rellenada del todo).
- **Aplicación:** quirófano o taller; el usuario no aparta la vista de lo que hace. Se entiende al instante.
- **Por qué premiado:** hipótesis: humano en el centro y entrega en mano.
- **Valoración:**

  | Criterio | Peso | Nota | Por qué |
  |---|---|---|---|
  | Funciona en vivo y se recupera | 30 % | 5 | Solo vídeo de teleoperación; inferencia sin pruebas. |
  | Dificultad técnica | 20 % | 5 | SmolVLA multitarea + palabra clave; nada fuera de lo habitual. |
  | Utilidad práctica | 20 % | 7 | Problema real y claro. |
  | Creatividad y momento memorable | 15 % | 6 | Entrega en mano; el EEG llama la atención pero no estaba en la demo final. |
  | Facilidad de uso y presentación | 15 % | 6 | Voz con orden de cancelar y sustituir; documentación incompleta. |
  | **Total** | | **57,0** | |

- **Replicabilidad en 48 h con SO-101:** alta.
- **Lección para LeWelder:** la voz necesita **"para" y "cambia de pedido"** desde el principio; el jurado lo
  probará. Y no dejar plantillas a medio rellenar en la entrega.

### AI Bartender · Megas XLR · Hackathon LeRobot Bilbao I, 21-23 nov 2025 · 1.º
- **Fuentes:** [crónica del equipo](https://www.elchinaslanli.com/projects/how-we-won-the-lerobot-hackathon-2025-meet-the-ai-bartender),
  [Bilbao Gazte](https://bilbaogazte.bilbao.eus/es/2025/11/19/bilbao-se-suma-a-la-semana-europea-de-la-robotica/).
  Sin repo público encontrado.
- **Qué hace:** pides una bebida hablando, un camarero con personalidad (Gemini) te contesta y el SO-101 "sirve"
  arena de color en un vaso.
- **Análisis técnico:** 2 SO-101 leader/follower con Phosphobot (obligatorio en el evento); **ACT**, 50 demos de
  "agua" (arena azul) y 30 de "Coca-Cola" (arena roja), 20.000 pasos con batch 4 en GPU de Brev (créditos de
  NVIDIA); inferencia local para evitar latencia (descartaron GR00T). Voz → Gemini → robot → voz (herramientas
  de voz **[no verificado]**). Cámaras **[no verificado]**.
- **Aplicación:** hostelería, muy relacionable. **Momento memorable:** con el público rodeando la mesa no
  pudieron cambiar el vaso, el robot echó las dos arenas en el mismo y lo vendieron como cóctel.
- **Por qué ganó:** según el equipo (no el jurado): tarea real y relacionable, el LLM atrae, y la improvisación
  pudo parecer más compleja. Problemas: reinstalaron Ubuntu el sábado; electrónica justo antes de la demo.
- **Valoración:**

  | Criterio | Peso | Nota | Por qué |
  |---|---|---|---|
  | Funciona en vivo y se recupera | 30 % | 6 | Funcionó ante el jurado y salvó un fallo con gracia; solo hay relato propio. |
  | Dificultad técnica | 20 % | 5 | Dos ACT sencillos más un LLM. |
  | Utilidad práctica | 20 % | 5 | Camarero con arena: idea real, demo simbólica. |
  | Creatividad y momento memorable | 15 % | 8 | El "cóctel" improvisado es lo más recordado. |
  | Facilidad de uso y presentación | 15 % | 7 | Conversación natural con personaje. |
  | **Total** | | **60,5** | |

- **Replicabilidad en 48 h con SO-101:** alta.
- **Lección para LeWelder:** el mismo jurado de Bilbao premió **personaje + voz + improvisar ante el fallo**.
  Ensayar qué dice el instructor virtual cuando una pieza cae.

### LeCyborg (tercer brazo por EMG) · Baptiste Lubrano Lavadera, Erwan Martin · LeRobot Worldwide Hackathon, 14-15 jun 2025 (sede europea [no verificado]) · 13.º de 30 premiados
- **Fuentes:** [repo](https://github.com/Mr-C4T/LeCyborg), [vídeo](https://youtu.be/OB96s5SZWGA),
  [ganadores](https://huggingface.co/spaces/LeRobot-worldwide-hackathon/all-winners).
- **Qué hace:** un SO-100 sujeto a una mochila actúa como tercer brazo y se activa con la señal muscular del
  usuario.
- **Análisis técnico:** SO-100 ponible con cámara de muñeca y de contexto; sensor EMG MyoWare con ESP32 por
  Bluetooth (caja impresa; luego PCB propia); **la señal EMG entra en la observación de un ACT**. Episodios y
  pasos **[no verificado]**.
- **Aplicación:** asistencia y prótesis. Momento memorable: el brazo responde al músculo del usuario.
- **Por qué premiado:** juicio por vídeo; hipótesis: originalidad absoluta y sensor propio integrado en el
  aprendizaje.
- **Valoración:**

  | Criterio | Peso | Nota | Por qué |
  |---|---|---|---|
  | Funciona en vivo y se recupera | 30 % | 6 | Vídeo público; juicio por vídeo, no en vivo. |
  | Dificultad técnica | 20 % | 7 | Sensor nuevo en el espacio de observación y robot ponible. |
  | Utilidad práctica | 20 % | 6 | Asistencia real, prototipo temprano. |
  | Creatividad y momento memorable | 15 % | 9 | "Cíborg con LeRobot" es único. |
  | Facilidad de uso y presentación | 15 % | 6 | Guía de montaje completa con STL y Gerber. |
  | **Total** | | **66,5** | |

- **Replicabilidad en 48 h con SO-101:** media (electrónica del sensor).
- **Lección para LeWelder:** meter **nuestro sensor en la observación** es diferencial: el LED de la antorcha
  podría ser también una entrada de la política o del evaluador, no solo un adorno.

### Doblar toallas y pick & place (informe de campo) · ML6 (Team 297) · LeRobot Worldwide Hackathon, jun 2025 (sede europea [no verificado]) · 3.º mundial
- **Fuentes:** [informe ML6](https://www.ml6.eu/en/blog/ai-robotics-a-field-report-on-imitation-learning-with-lerobot),
  [ganadores](https://huggingface.co/spaces/LeRobot-worldwide-hackathon/all-winners) (vídeo "3-297-ML6").
- **Qué hace:** dos SO-100 doblan y desdoblan una toalla; además experimentos de pick & place.
- **Análisis técnico:** 3 cámaras. ACT en pick & place: 20 episodios → 60 %; 100 → 90 % en distribución; 340 → 79 %
  con dos ejes de variación. GR00T-N1 nunca agarró el ladrillo, pero dobló toalla con 100 episodios al 80 %
  (desdoblar 60 %), con inferencia remota en Runpod; **las pausas por latencia se cortaron de los vídeos**.
  Trabajaron la inestabilidad de cámara con Gaussian splatting.
- **Aplicación:** tareas domésticas con tela. Se entiende al instante.
- **Por qué premiado:** votación de la comunidad tras pasar el top 10. Hipótesis: tela deformable y bimanual.
- **Valoración:**

  | Criterio | Peso | Nota | Por qué |
  |---|---|---|---|
  | Funciona en vivo y se recupera | 30 % | 5 | Vídeo editado sin las pausas: no muestra el sistema real. |
  | Dificultad técnica | 20 % | 8 | Bimanual con tela y comparación seria de políticas. |
  | Utilidad práctica | 20 % | 6 | Doblar ropa, demo parcial. |
  | Creatividad y momento memorable | 15 % | 5 | Tarea conocida. |
  | Facilidad de uso y presentación | 15 % | 6 | Informe muy honesto con números. |
  | **Total** | | **59,5** | |

- **Replicabilidad en 48 h con SO-101:** media.
- **Lección para LeWelder:** sus números son nuestra mejor guía de volumen: **~100 episodios por habilidad con poca
  variación da ~90 %**, y la pérdida no predice el éxito: elegir checkpoint probando en el robot.

---

## 3. Tabla resumen (ordenada por total)

| # | Proyecto | Hackathon | Puesto | Política | Episodios | Total |
|---|---|---|---|---|---|---|
| 1 | Asistente de soldadura con linterna (MSN) | Robotekin, Vitoria, oct 2026 | 1.º | ACT + IBVS clásico | 54 | 74,5 |
| 1 | LeHome, final real (Larchenko) | ICRA, Viena, jun 2026 (competición) | 2.º real / 1.º sim | π0.5 + RL + DAgger | [no verificado] | 74,5 |
| 3 | Flip & Ship (Inverse Kinema-tricks) | AMD, París, dic 2025 | 1.º | 3 × SmolVLA (antes ACT) | 126 + 150 + 145 | 74,0 |
| 4 | LeCyborg | LeRobot Worldwide, jun 2025 | 13.º | ACT con EMG | [no verificado] | 66,5 |
| 5 | Talos | ERH, Zúrich, oct 2026 | ganador | ninguna (ROS 2) | 0 | 62,0 |
| 6 | AI Bartender (Megas XLR) | Bilbao I, nov 2025 | 1.º | 2 × ACT + Gemini | 50 + 30 | 60,5 |
| 7 | Doblar toallas (ML6) | LeRobot Worldwide, jun 2025 | 3.º | ACT / GR00T-N1 | 20-340 por experimento | 59,5 |
| 8 | Le Coup de Pouce (ESILV) | AMD, París, dic 2025 | 3.º [discrepancia] | SmolVLA multitarea | [no verificado] | 57,0 |
| 9 | Conecta 4 (Bartolos Crew) | AMD, París, dic 2025 | 3.º | SmolVLA multitarea (5 tareas) | 120 | 56,5 |
| 10 | Robotticelli | La Machine, Ámsterdam, oct 2026 | 1.º | ninguna (poses enseñadas a mano) | 0 | 55,0 |
| 11 | Tareas domésticas OpenArm (MURobot) | Robotekin, Vitoria, oct 2026 | 2.º | [no verificado] | [no verificado] | 54,5 |
| 12 | RoBoost | Europe Embodied, Múnich, jun 2026 | 1.º absoluto | ninguna publicada (YOLO + profundidad) | 0 | 54,0 |

Nota: la nota mide lo que se puede comprobar, no el puesto. Los proyectos sin pruebas públicas bajan aunque
ganaran.

---

## 4. Patrones comunes de los ganadores

1. **Habilidad aprendida + orquestación programada.** MSN (ACT + IBVS), Flip & Ship (visión clásica elige entre 3
   SmolVLA), Conecta 4 (minimax elige la tarea de la SmolVLA). Nadie gana con una política de extremo a extremo
   que lo hace todo. Es el patrón de LeWelder.
2. **SmolVLA multitarea con una tarea por destino** es lo que usaron los premiados de París (1.º y dos 3.º).
   Volumen típico: 25-50 episodios por tarea para multitarea, 50-150 para una habilidad sola.
3. **Dos o tres cámaras fijas, una en la muñeca.** Todos los datasets premiados revisados tienen top + muñeca
   (Conecta 4 usa 3).
4. **Recuperación visible.** Luz que esquiva la mano (MSN), paquete que se voltea (Flip & Ship), cóctel
   improvisado (Bilbao). El jurado recuerda el fallo resuelto, no el éxito limpio.
5. **Algo físico propio.** Cinta con motor reciclado (Flip & Ship), sensor EMG con PCB (LeCyborg), OpenArm
   (MURobot), robot trepador (Talos). Distingue a primera vista.
6. **Humano en el centro y voz.** MSN, Bilbao, ESILV. En Bilbao y Vitoria, los dos ganadores locales llevaban voz.
7. **En los "Physical AI" generalistas de 2026 (Ámsterdam, Zúrich, Múnich) ganaron proyectos sin aprendizaje por
   imitación**: espectáculo, hardware y una idea de una frase. En los hackathons LeRobot (Vitoria, Bilbao,
   París) siempre hubo política aprendida en el ganador. Bilbao II es de este segundo tipo.
8. **El camarero está quemado.** Bilbao 2025, ERH 2026 (barman con OpenArm) y otros: evitar parecerse.
9. **Todo publicado y reproducible**: los ganadores con más nota tienen dataset, modelo y README con órdenes
   exactas. Los que no publican no se pueden valorar por encima de 5.

## 5. Qué significa para LeWelder (resumen)

- Nuestro precedente directo (MSN, soldadura, Vitoria) ganó hace un mes en el mismo circuito: el jurado puede
  compararnos. Diferenciarnos por **montar la junta con varias habilidades aprendidas** y por la **nota al alumno**.
- Copiar de Flip & Ship el selector programado que cambia de habilidad sin parar, y de Conecta 4 la tarea como
  texto con ~25-50 episodios por tipo de junta.
- Planificar la recuperación como parte del número (una pieza mal colocada que el robot recoloca).
- Replanificar más a menudo (menos `n_action_steps`) y hacer 2-3 rondas cortas de grabación donde falle.
- Voz con "para" y "cambia", y un personaje que sepa improvisar.

---

## 6. Eventos europeos de 2026 encontrados sin ganadores verificables

| Evento | Fecha y lugar | Robot | Estado |
|---|---|---|---|
| [Physical AI Hackathon by Robotics Nation](https://luma.com/0dn6im3g) | 27 feb - 1 mar 2026, Helsinki | 2 SO-101; SO-101 sobre LeKiwi | Sin ganadores publicados; datasets de participantes ([cl3mens](https://huggingface.co/cl3mens), 21-54 episodios) |
| [Physical AI x Manufacturing Hackathon](https://luma.com/physical-ai-hack) | 28 feb - 1 mar 2026, Zúrich | Robots industriales y cintas | Sin ganadores publicados; jurado Massimo Banzi |
| [MiniFactory](https://minifactorycopenhagen.com/) (Qualia + Atech + Hugging Face) | 6-7 jun 2026, Copenhague | SO-101 | Sin ganadores publicados |
| [Unaite x GOSIM Robotics Hackathon](https://luma.com/11cjioey) | 2026, STATION F, París | OpenArm, entre otros ([repo de un equipo](https://github.com/ppolack/gosim-hackathon-openarm), 25 episodios) | Sin ganadores publicados |
| [ERH Physical AI Hackathon](https://github.com/Nailec101/pour-skill), reto Daidai | 16-18 oct 2026, Zúrich | OpenArm | Ganador del reto sin verificar |
| Founders Hub × DNB Physical AI ([repo](https://github.com/nilsvselte/founders-hub-hackathon)) | 5 nov 2026, Trondheim | — | Sin ganadores publicados |
| [Intel Physical AI Challenge (ERH)](https://luma.com/d3pjvggt) | 4-6 dic 2026, Zúrich | — | Futuro |

---

## 7. Fuentes

- Robotekin 2026: [crónica](https://robotekin.com/robotekin-reune-en-alava-a-casi-80-jovenes-para-entrenar-robots-con-inteligencia-artificial/),
  [repo MSN](https://github.com/flipiflopi/Hackaton_Robotekin_SO-101_MSN),
  [dataset MSN](https://huggingface.co/datasets/FlipiFlopi007/so101_tumbada_full).
- La Machine 2026: [Robotticelli](https://github.com/Danitell0/robotticelli), [evento](https://luma.com/ni360mav),
  [Handy](https://github.com/marinmarian/la-machine-benchbot), [post LinkedIn](https://ch.linkedin.com/in/darrenhargan).
- Europe Embodied 2026: [crónica TUM](https://tum-international.com/europe-embodied-2026-48-hour-hackathon/),
  [RoBoost](https://github.com/Thierryonre/RoBoost), [Robo67](https://github.com/M4RKUS28/Robo67),
  [EUROPE-Embodied](https://github.com/doyun-gu/EUROPE-Embodied).
- ERH Zúrich 2026: [Talos](https://github.com/Annnnya/talos_hack),
  [anuncio](https://www.linkedin.com/feed/update/urn:li:activity:7521900692014288898/),
  [pour_skill](https://github.com/Nailec101/pour-skill).
- LeHome / ICRA 2026: [Larchenko](https://ilialarchenko.com/projects/lehome2026/),
  [artículo](https://arxiv.org/html/2606.27163v2), [3.º real](https://aarvis.github.io/lehome2026/).
- AMD París 2025: [crónica y ganadores](https://www.amd.com/en/developer/resources/technical-articles/2025/amd-open-robotics-hackathon-recap.html),
  [Flip & Ship](https://github.com/NRdrgz/AMD_Robotics_Hackathon_2025_InverseKinematricks),
  [vídeo Flip & Ship](https://www.youtube.com/watch?v=QZKOs_gODcs),
  [Conecta 4](https://github.com/jgorostegui/AMD_Robotics_Hackathon_Team15),
  [Le Coup de Pouce](https://github.com/leogue/AMD_Robotics_Hackathon_2025_LeCoup_De_Pouce),
  [ESILV](https://www.esilv.fr/robotique-et-ia-des-etudiants-de-lesilv-sur-le-podium-du-paris-open-robotics-hackathon/amp/),
  no premiados consultados: [RadSort](https://github.com/wilfred-dore/AMD_Robotics_Hackathon_2025_RobotROCmRadSort-main),
  [Préhistorique](https://github.com/kabylesystem/hackathon_amd_robotics).
- Bilbao I 2025: [crónica del ganador](https://www.elchinaslanli.com/projects/how-we-won-the-lerobot-hackathon-2025-meet-the-ai-bartender),
  [Bilbao Gazte](https://bilbaogazte.bilbao.eus/es/2025/11/19/bilbao-se-suma-a-la-semana-europea-de-la-robotica/).
- LeRobot Worldwide 2025: [ganadores](https://huggingface.co/spaces/LeRobot-worldwide-hackathon/all-winners),
  [LeCyborg](https://github.com/Mr-C4T/LeCyborg), [ML6](https://www.ml6.eu/en/blog/ai-robotics-a-field-report-on-imitation-learning-with-lerobot).
