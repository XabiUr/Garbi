# Análisis de concursos comparables: por qué se gana y por qué se pierde

Fecha: 13-11-2026. Objetivo: Hackathon LeRobot Bilbao II (20-22 nov 2026, 48 h, SO-101, demo en vivo, pitch 5 min).

Principio rector: **es más importante no perder que ganar**. Casi todos los equipos que pierden lo hacen por
ejecución (la demo no está lista o falla), no por la idea.

---

## 1. Concursos analizados

| Concurso | Formato | Juicio | Qué datos hay |
|---|---|---|---|
| Robotekin Hackathon LeRobot (Vitoria, 23-25 oct 2026) | 48 h, 17 equipos, SO-101 | Jurado en vivo | 3 premiados, repos del 1.º y de 3 no premiados |
| Hackathon LeRobot Bilbao I (21-23 nov 2025) | 48 h, +20 equipos, SO-101 + LeKiwi + MobilX | Jurado en vivo | Ganador (camarero IA) y un no premiado (PUCRA) |
| LeRobot Worldwide Hackathon (14-15 jun 2025) | 2 días, +100 sedes, 250+ entregas | Vídeo, jurado de Hugging Face | 30 premiados; datasets de 115 equipos (15 premiados) |
| CCSF Robotics Hack (6 nov 2026) | 1 día, 8 equipos, SO-101 | Juez de NVIDIA en vivo | Fallo de cada equipo documentado |
| AMD Open Robotics (Tokio/París/San José, dic 2025) | 2 días + extra, 36-40 equipos | En vivo, **rúbrica oficial de 100 puntos** | Rúbrica, nombres de ganadores, 2 crónicas de equipos |

---

## 2. Lo que dicen los datos

### 2.1 Robotekin 2026 (el más parecido)

| Puesto | Equipo | Proyecto | Datos | Claves |
|---|---|---|---|---|
| 1.º | MSN (U. Málaga, 3 estudiantes) | Asistente de soldadura: coge una linterna y alumbra el punto que marcas en una PCB; si algo tapa la luz, busca otro ángulo | 54 episodios, 1 ACT, RTX 3050 4 GB | Caso humano claro, voz, híbrido ACT + visión clásica, **recuperación demostrada (4 oclusiones resueltas en el log de la demo)** |
| 2.º | MURobot (Mondragon, 5 doctorandos) | Tareas domésticas con OpenArm bimanual traído por ellos + exoesqueleto de teleoperación | — | **Hardware propio más grande que el resto**: destaca visualmente |
| 3.º | Law Le Baguette (EHU Vitoria, 4) | Robot que juega al ajedrez contra una persona | — | Interacción con el público |
| — | Equipo Rubí Automotive (profesionales) | Celda industrial: coger soporte, clasificador de pin, caja buena/mala, órdenes por voz en 3 idiomas y Telegram | **692 episodios, 3 ACT, 1 clasificador** | Muy completo y bien documentado, **sin premio** |
| — | BraboRobots (SmartSeed) | Sembrar semillas en bandeja diseñada en web | 187 episodios reales + 1.400 simulados, ACT, OWLv2, Depth Anything, IK, MuJoCo | Técnicamente sofisticado, **sin premio** |
| — | muulti | Web app cliente → SO-101 con servidor de políticas | — | Sin premio |

Lectura:
- **Ni el volumen de datos ni la sofisticación técnica ganaron.** Los dos proyectos más trabajados (692 y 1.600
  episodios) quedaron fuera; ganó el de 54 episodios.
- Ganó lo que se entiende en 5 segundos, tiene un humano en el centro y **demuestra en vivo que se recupera**.
- La tarea industrial "clasificar piezas" parece correcta pero previsible para este jurado (hipótesis: no
  conocemos la puntuación de los no premiados).

### 2.2 Bilbao 2025 (nuestro evento)

- **Ganador, AI Bartender (Megas XLR):** voz → Gemini con personaje → ACT (50 + 30 demos, 20k pasos, GPU en la
  nube de Brev) → voz. Arena de colores en vez de líquidos. En la demo el robot echó dos "bebidas" en el mismo
  vaso y lo vendieron como cóctel: **improvisar con gracia ante un fallo sumó**.
- **PUCRA (UPC, sin premio conocido):** LeKiwi autónomo que detecta, coge y deposita balizas, con ROS 2, odometría
  por ArUco y navegación. Mucha integración de robótica clásica; el aprendizaje por imitación solo para el agarre.
- Lecciones del ganador: tarea real y relacionable; el LLM atrae atención; sustitutos seguros; dormir.
  Problemas: plataforma que falló el sábado (reinstalaron Ubuntu), electrónica justo antes de la demo.

### 2.3 LeRobot Worldwide 2025 (volumen: premiados frente a no premiados)

Comparación de los datasets públicos de 115 equipos (15 premiados, 100 no premiados):

| Métrica | Premiados | No premiados |
|---|---|---|
| Episodios por equipo (mediana) | 59,5 | 52 |
| Episodios por equipo (media) | 89 | 87 |
| Datasets por equipo | 1,87 | 1,41 |
| Cámaras (media) | **2,07** | 1,74 |
| Tareas distintas (media) | 1,67 | 1,47 |
| % con objeto genérico (cubo, bloque, bola, caja) | 38 % | 39 % |

Lectura:
- **La cantidad de datos no separa a ganadores de perdedores.** Tampoco el tipo de objeto.
- Ligeramente más cámaras y algo más de una tarea en los premiados.
- Había ideas muy originales sin premio: cubiletes y bola, piedra-papel-tijera, tres en raya, dar de comer con
  un palo, servir agua, galleta de la fortuna. **La originalidad sola no gana**: decide la ejecución y cómo se
  enseña (aquí, el vídeo).
- Premiados notables: sándwich (1.º), doblar ropa y medicinas (2.º), meter pilas y pinzas (4.º), Juego del
  Calamar (8.º), cazar polilla (9.º), refuerzo en robot real (10.º), térmica (12.º), tercer brazo por EMG (13.º),
  platos por lenguaje (15.º, luego 1.º en AMD Tokio), quitar el móvil (16.º).
- Lecciones de un equipo top 30 (Artur Habuda): empezar a grabar el primer día, cámara que vea todo (prueba:
  ¿podrías teleoperar mirando solo las cámaras?), fondo uniforme, no mover cámaras, imitación antes que
  cinemática a mano, ajustar hiperparámetros, SmolVLA rindió mejor con pocos episodios que modelos grandes.

### 2.4 CCSF 2026 (manual de cómo se pierde)

| Equipo | Resultado | Por qué |
|---|---|---|
| Tubos de ensayo a gradilla | **Ganó** | ACT al ~75 %, pinzas impresas en 3D para objetos redondos, demo repetida hasta que salió. Juez: "resuelve un problema realmente difícil" |
| Cámara que sigue al orador | "El más emocionante", no ganó | Enfoque distinto, pero sin aprendizaje (Claude + visión) |
| Clasificador de colores | Perdió | Movieron el montaje durante la presentación |
| Clasificador de cubos | Perdió | Solo 6 episodios y sin GPU |
| Apilador de bloques | Perdió | La política seguía entrenando durante la demo |
| Ajedrez → tres en raya | Perdió | Alcance demasiado grande; recortaron y no terminaron |
| Robot con sentimientos | Perdió | Voz y avatar hechos, pero sin conectar al brazo |
| Tres motores quemados | Perdió | Una hora perdida por hardware |

### 2.5 AMD 2025 (la única rúbrica oficial)

- Criterios oficiales: **creatividad, dificultad, facilidad de uso y utilidad práctica**, sobre 100 puntos.
  Requisito previo: completar la misión guiada.
- Ganador de Tokio: GreatAkihabara (platos con órdenes en lenguaje natural, "dame dos platos").
- Fallos documentados por equipos: servos sin ID, portátil prestado que falla, errores de decodificación de
  vídeo, cámara que ignora la exposición con objetos brillantes, modelo de 2B demasiado lento para entrenar
  (2 h por 1.000 pasos) → volvieron a SmolVLA. "Done is better than perfect".
- Un equipo no premiado público (RoboTAI) estructuró su entrega exactamente con la rúbrica: descripción,
  creatividad, implementación técnica, ejecución completa, recuperación por fases, generalización a la luz,
  reintentos, facilidad de uso, reproducibilidad.

---

## 3. Por qué se pierde (ordenado por frecuencia en las fuentes)

| # | Causa | Evidencias | Contramedida para nosotros |
|---|---|---|---|
| 1 | **La demo no está lista**: política entrenando, piezas sin conectar, pocos episodios | CCSF ×3, AMD | Habilidad central entrenada y probada el sábado a mediodía; todo lo demás es extra |
| 2 | **Alcance demasiado grande** | CCSF (ajedrez), Artur | Escalera de alcance: nivel mínimo demostrable primero |
| 3 | **Cambios en el entorno**: mover cámaras o montaje, luz, reflejos, fondo | CCSF, Artur, AMD, MSN | Soportes de cámara impresos y fijos, fondo uniforme, montaje congelado el sábado noche |
| 4 | **Hardware e infraestructura**: motores, servos sin ID, portátil, SO, vídeo | CCSF, AMD, Bilbao 2025 | Revisión a los 30 min, dos portátiles preparados, copia del dataset al Hub tras cada sesión |
| 5 | **Modelo demasiado pesado para el tiempo** | Artur (GR00T), AMD (VLA-0 2B), Bilbao (GR00T descartado) | ACT para lo que no puede fallar; VLA pequeño solo como extra y en la nube |
| 6 | **Programar a mano lo que se puede aprender** | Artur, CCSF | Imitación para manipular; cálculo clásico solo para geometría simple |
| 7 | **Elegir el checkpoint por la pérdida** | MSN, Artur | Elegir probando en el robot real |
| 8 | **Proyecto correcto pero previsible** | Rubí (692 episodios, sin premio), clasificadores | La idea necesita un momento que se recuerde |
| 9 | **Idea original mal ejecutada** | Worldwide: cubiletes, piedra-papel-tijera... sin premio | La originalidad no compensa una demo floja |

## 4. Por qué se gana

| # | Factor | Evidencias |
|---|---|---|
| 1 | **Funciona en vivo de principio a fin** (aunque no sea al 100 %) | CCSF, MSN, todos los ganadores |
| 2 | **Dificultad percibida**: la tarea parece difícil a simple vista | CCSF (tubos), Electrify, doblar ropa, sándwich |
| 3 | **Se entiende en 5 segundos y hay un humano en el centro** | Sándwich, camarero, soldadura, quitar el móvil |
| 4 | **Recuperación demostrada en directo** | MSN (oclusiones), RoboTAI (fases), camarero (improvisación) |
| 5 | **Una capa que da vida**: voz, LLM, personaje | Camarero, MSN, platos por lenguaje, Gordy (RoboHacks) |
| 6 | **Algo físico propio que destaca o hace fiable**: hardware, pinzas impresas, sensor | OpenArm (2.º Robotekin), pinzas 3D (CCSF), térmica, EMG |
| 7 | **Híbrido**: lo difícil se aprende, la geometría se calcula | MSN, SmartSeed, Rubí (necesario, no suficiente) |
| 8 | Más de una cámara bien colocada | Worldwide (2,07 frente a 1,74) |

## 5. Rúbrica de trabajo para Bilbao (supuesto)

Basada en la rúbrica oficial de AMD y en lo observado. Pendiente de confirmar con la organización.

| Criterio | Peso | Qué lo puntúa |
|---|---|---|
| Funciona en vivo y se recupera | 30 % | Ejecución completa, reintentos, perturbación resuelta |
| Dificultad técnica | 20 % | Tarea que parece difícil; aprendizaje real, no movimientos grabados |
| Utilidad práctica | 20 % | Problema real, se entiende al instante |
| Creatividad y momento memorable | 15 % | Sorpresa, interacción con el jurado |
| Facilidad de uso y presentación | 15 % | Se usa sin técnico al lado; pitch claro; dataset y código reproducibles |

## 6. Filtro para elegir la idea

Una idea pasa si cumple todo esto:

1. Tiene **una habilidad central** que puede llegar al 80 % de éxito con ~50-80 episodios en un montaje fijo.
2. La tarea **parece difícil** (no es mover un cubo).
3. Se entiende en 5 segundos y tiene **un humano en el centro**.
4. Incluye un **momento de recuperación** planificado para la demo.
5. Lleva una **capa de vida** (voz, LLM o personaje) que se puede quitar si falla sin romper la demo.
6. Aprovecha **algo físico nuestro** (impresión 3D, sensor) que aumenta la fiabilidad y la sorpresa.
7. Tiene una **escalera de alcance**: nivel 1 demostrable el sábado a mediodía, niveles 2 y 3 opcionales.

## 7. Candidatas pasadas por el filtro (13-11-2026)

✓ cumple · ~ a medias · ✗ no cumple

| Criterio | 1. Rehabilitación jugando | 4. Mago (cubiletes) | Desayuno |
|---|---|---|---|
| 1. Habilidad central al 80 % | ~ presentar la bola se puede programar; aprender solo recogerla | ~ mover cubiletes rápido y fiable es difícil | ✗ 3-5 habilidades, cada una con su dataset |
| 2. Parece difícil | ✗ mover una bola parece fácil | ~ solo si es rápido; ACT es lento | ✓ cocinar en secuencia parece difícil (el sándwich fue 1.º mundial) |
| 3. Humano en el centro | ✓ | ✓ | ✓ |
| 4. Recuperación planificada | ✓ la bola cae y la recoge | ~ si un cubilete se vuelca, lo endereza como parte del número | ~ reintentar si la palanca no baja |
| 5. Capa de vida quitable | ✓ entrenador por voz | ✓ personaje de mago | ✓ nutricionista LLM |
| 6. Algo físico nuestro | ✓ bola con ESP32 y sensor | ✓ cubiletes trucados | ~ soportes impresos; electrodomésticos ajenos |
| 7. Escalera de alcance | ✓ | ✓ | ✓ |
| **Total** | **5 ✓, 1 ~, 1 ✗** | **3 ✓, 4 ~** | **4 ✓, 2 ~, 1 ✗** |
| Riesgo extra | Poca dificultad percibida | "Cups and ball" ya estuvo en el mundial sin premio | Parecido al camarero (Bilbao 2025) y al sándwich; alcance del brazo; calor y líquidos |

Ninguna pasa las 7 tal cual. Arreglos propuestos:

- **Rehabilitación (pasa a 7/7):** la habilidad central deja de ser "mover la bola" y pasa a ser **recoger la bola
  de donde caiga y entregarla en la mano del paciente**, que se mueve. La entrega en mano a una persona es
  difícil de verdad y se aprende por imitación. El recorrido de ejercicio se aprende de demostraciones de un
  fisioterapeuta, no se programa.
- **Desayuno (pasa a 6/7):** reducir a **una habilidad estrella** (café de cápsula de principio a fin: cápsula,
  palanca, botón, taza) + una sencilla (monodosis y fruta a la bandeja), en una minicocina con soportes impresos.
  Diferenciarse del camarero con el menú personalizado de cada juez. Sigue el riesgo de parecido.
- **Mago:** queda por detrás; su punto débil (velocidad y fiabilidad del juego de manos) es el más difícil de arreglar.

---

## Fuentes

- Robotekin: [crónica](https://robotekin.com/robotekin-reune-en-alava-a-casi-80-jovenes-para-entrenar-robots-con-inteligencia-artificial/),
  [repo MSN](https://github.com/flipiflopi/Hackaton_Robotekin_SO-101_MSN),
  [SmartSeed](https://github.com/alvaromoli13/Robotluces),
  [Pin sorting](https://huggingface.co/spaces/MikelRubi/robotekin-so101-pin-sorting),
  [muulti](https://github.com/muulti/Hackathon_Robotekin_Lerobot)
- Bilbao 2025: [ganador](https://www.elchinaslanli.com/projects/how-we-won-the-lerobot-hackathon-2025-meet-the-ai-bartender),
  [PUCRA](https://www.youtube.com/watch?v=r8AYFELDHG0),
  [Bilbao Gazte](https://bilbaogazte.bilbao.eus/es/2025/11/19/bilbao-se-suma-a-la-semana-europea-de-la-robotica/)
- Worldwide: [ganadores](https://huggingface.co/spaces/LeRobot-worldwide-hackathon/all-winners),
  [datasets](https://huggingface.co/LeRobot-worldwide-hackathon),
  [lecciones top 30](https://arturhabuda.com/2025/06/29/lerobot-worldwide-hackathon-how-we-got-into-the-top-30-worldwide/),
  [LeCyborg](https://github.com/Mr-C4T/LeCyborg)
- CCSF: [crónica](https://worldwidestudios.substack.com/p/ccsf-robotics-hack-recap-1-day-build)
- AMD: [bases y rúbrica](https://huggingface.co/blog/amd/openroboticshackathon),
  [crónica](https://www.amd.com/en/developer/resources/technical-articles/2025/amd-open-robotics-hackathon-recap.html),
  [equipo Tokio](https://zenn.dev/mkj/articles/317e39955e1343),
  [RoboTAI](https://github.com/Robotawi/RoboTAI_AMD_Robotics_Hackathon_2025)
