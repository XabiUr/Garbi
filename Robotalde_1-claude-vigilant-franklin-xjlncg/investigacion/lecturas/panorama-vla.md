# Panorama de los modelos Vision-Language-Action (VLA)

Lectura de referencia para LeWelder (hackathon LeRobot Bilbao II, 20-22 nov 2026). Fecha de redacción: 18 nov 2026.

Método: lectura de las versiones HTML de arXiv por partes (con un modelo auxiliar que resume cada fragmento) y de
los abstracts. No se ha leído ninguna survey entera: se ha priorizado taxonomía, retos, limitaciones y aplicaciones.
Las cifras que vienen solo de una survey (y no del artículo original) se marcan como **[cifra de survey]**; lo que
no se ha podido leer se marca como **[no verificado]**.

---

## 1. Fichas de las fuentes

### F1 · π0 — arXiv:2410.24164 (Physical Intelligence, oct. 2024)
- *π0: A Vision-Language-Action Flow Model for General Robot Control.*
- Primer VLA que une un VLM preentrenado (PaliGemma 3B) con un "experto de acción" que genera acciones continuas
  por *flow matching*. 3,3B parámetros. Más de 10.000 h de datos de manipulación, 7 configuraciones de robot.
- Leído: casi todo el texto HTML (las cifras exactas de resultados están en figuras y no se han leído).

### F2 · π0.5 — arXiv:2504.16054 (Physical Intelligence, abr. 2025)
- *π0.5: a Vision-Language-Action Model with Open-World Generalization.*
- Extiende π0 con co-entrenamiento heterogéneo (varios robots, datos web, predicción de subtareas en lenguaje,
  instrucciones verbales) y una inferencia en dos niveles: primero la subtarea en texto, luego las acciones.
  Demuestra tareas largas (limpiar cocina o dormitorio) en casas nunca vistas.
- Leído: abstract y la mayor parte del HTML.

### F3 · SmolVLA — arXiv:2506.01844 (Hugging Face, jun. 2025)
- *SmolVLA: A Vision-Language-Action Model for Affordable and Efficient Robotics.* No estaba en la lista, pero es
  el modelo que vamos a usar, así que se ha leído. ~450M parámetros, preentrenado con datos comunitarios de SO-100.
- Leído: abstract y la mayor parte del HTML.

### F4 · "An Anatomy of VLA Models: From Modules to Milestones and Challenges" — arXiv:2512.11362
- Xu, Zhang, Liu, ... Peters, Zafeiriou, Deng (dic. 2025, preprint cs.RO).
- Estructura: módulos (percepción, "cerebro", cabeza de acción) → hitos 2017-2025 → cinco retos con soluciones.
- Leído: los dos primeros tercios (módulos, hitos, retos IV-A a IV-E). No leídas: conclusión y apéndices.

### F5 · "VLA Models: Concepts, Progress, Applications and Challenges" — arXiv:2505.04769
- Sapkota, Cao, Roumeliotis, Karkee (may. 2025; publicada en *Information Fusion*; v2 de ene. 2026).
- Revisa más de 80 VLA; línea temporal en tres fases (2022-23 integración, 2024 especialización, 2025
  generalización y despliegue). Capítulos de aplicaciones y de retos con muchas cifras.
- Leído: partes 1 y 2 de 3 y la conclusión. **Ojo:** muchas cifras aparecen sin detalle de cómo se midieron.

### F6 · "Large VLM-based VLA Models for Robotic Manipulation: A Survey" — arXiv:2508.13073
- Shao, Li, Zhang, Zhang, Liu, Chen, Nie (Harbin Institute of Technology, Shenzhen; ago. 2025).
- La taxonomía más útil: monolíticos (un sistema / doble sistema) frente a jerárquicos; tipos de cabeza de acción.
- Leído: primera mitad aprox. No se ha encontrado lo que dice de Helix **[no verificado]**.

### F7 · "A Survey on VLA Models for Embodied AI" — arXiv:2405.14093
- Ma, Song, Zhuang, Hao, King (may. 2024; publicada en IEEE TNNLS). Se presenta como la primera survey de VLA.
- Taxonomía en tres bloques: componentes, políticas de control de bajo nivel, planificadores de alto nivel.
- Leído: taxonomía y sección de retos. La sección de datasets solo por encabezados.

---

## 2. Qué es un VLA (explicado para alguien de software)

**Definición mínima** (F7): un VLA es un modelo que recibe imágenes y una instrucción en lenguaje y devuelve
acciones del robot (posiciones articulares, desplazamientos de la pinza...). F7 llama "Large VLA" a los que están
construidos sobre un LLM/VLM grande, como RT-2.

**Analogía de software.** Piensa en una función `accion = politica(imagenes, estado_articular, orden_texto)`:

| | Política de imitación clásica (ACT, Diffusion Policy) | VLA (SmolVLA, π0, GR00T) |
|---|---|---|
| Entrada | Cámaras + estado del robot | Cámaras + estado + **texto** |
| Pesos de partida | Desde cero (o un ResNet preentrenado) | Un **VLM preentrenado** con imágenes y texto de internet, más (a menudo) preentrenamiento con muchos robots |
| Tareas | Una política por tarea, normalmente | **Una sola política** para muchas tareas; la orden de texto elige cuál |
| Cómo se adapta | Entrenas otra vez con 50-100 demos de esa tarea | Ajuste fino (*fine-tuning*) del modelo base con tus demos |
| Coste | Pequeño (decenas de M parámetros), rápido | De 0,45B (SmolVLA) a 7B (OpenVLA); más memoria y latencia |

La idea es la misma que en los LLM: un modelo base preentrenado a gran escala y luego un ajuste fino barato para tu
caso. El VLM aporta "sentido común" visual y semántico (qué es una pieza, qué significa "la de la izquierda"), y
el preentrenamiento con robots aporta habilidades motoras genéricas (agarrar, colocar). π0 lo formula como
preentrenamiento con datos diversos y de menor calidad, y luego *post-training* con datos curados y consistentes,
comparándolo explícitamente con la receta de los LLM (F1).

Lo que **no** cambia respecto a ACT: sigue siendo aprendizaje por imitación con demos teleoperadas (SmolVLA lo
reconoce como limitación: solo imitación, sin refuerzo; F3). Tampoco cambia que ambos predicen **trozos de acciones**
(*action chunks*): ACT ya lo hacía; π0 y SmolVLA predicen 50 pasos de golpe (F1, F3).

---

## 3. Taxonomía

### 3.1 Por arquitectura (F6, con matices de F4 y F7)

- **Monolíticos de un solo sistema:** un único modelo lee y decodifica acciones. Ejemplos: RT-2 (acciones como
  tokens de texto), OpenVLA.
- **Monolíticos de doble sistema:** un VLM lento ("Sistema 2", razona) más un experto de acción rápido ("Sistema 1",
  actúa). Subtipos: *cascada* (secuencial) y *paralelo* (acoplados en la inferencia). Ejemplos: π0, SmolVLA
  (F6 lo clasifica como paralelo, con atención cruzada al VLM), GR00T N1 (VLM Eagle-2 + DiT de flow matching,
  entrenados juntos de extremo a extremo).
- **Jerárquicos:** un planificador produce algo intermedio e interpretable (subtareas, puntos clave, código) y una
  política lo ejecuta. Ejemplo: Hi Robot (planificador PaliGemma-3B que da órdenes atómicas a π0). π0.5 queda a
  caballo: un solo modelo que primero genera la subtarea en texto y luego las acciones (F2, F6).
- F7 usa otro corte: **políticas de bajo nivel** (RT-1, ACT, Diffusion Policy, Octo, OpenVLA, π0, GR00T N1) frente a
  **planificadores de alto nivel** (SayCan, Inner Monologue, Code as Policies, PaLM-E).

**Lectura para nosotros:** nuestra arquitectura (voz → LLM → orden de vocabulario cerrado → SmolVLA) es de hecho
**jerárquica tipo planificador + política**, como SayCan o Hi Robot. Es un patrón reconocido en las surveys, no un apaño.

### 3.2 Por cómo se generan las acciones (cabeza de acción; F4, F6)

| Tipo | Idea | Ejemplos | Pros / contras |
|---|---|---|---|
| Tokenización autorregresiva | Cada dimensión se discretiza en 256 *bins* y se genera como un token | RT-2, OpenVLA | Reaprovecha el LLM tal cual; lento (~3-5 Hz **[cifra de survey F5]**), pierde precisión fina por la discretización (F5), mal encaje con *chunks* (F1) |
| Tokenización comprimida | Comprime la trayectoria (FAST) antes de tokenizar | π0-FAST, preentrenamiento de π0.5 | Hasta ~15× más rápido que difusión según F5 **[cifra de survey]** |
| Difusión | Elimina ruido iterativamente sobre la acción | Diffusion Policy, Octo, CogACT, RDT-1B | Acciones continuas y multimodales; ~3× más caro que un decodificador normal **[cifra de survey F5]** |
| Flow matching | Variante de difusión que aprende un campo vectorial; ~10 pasos | π0, π0.5, SmolVLA, GR00T N1 | Continuo, suave, rápido en pocos pasos; F4: más preciso pero más difícil de aprender |
| Regresión / VQ-VAE | MLP directo o códigos discretos aprendidos | VQ-VLA | MLP puede sufrir colapso de modos (F5) |

### 3.3 Por tamaño (fuentes indicadas)

| Modelo | Parámetros | Cabeza | Fuente |
|---|---|---|---|
| RT-2 | hasta 55B (RT-2-X) | tokens | F5 |
| OpenVLA | 7B (Llama 2 + DINOv2 + SigLIP), ~970k demos | tokens | F5, F6 |
| π0 | 3,3B (PaliGemma 3B + 300M experto) | flow matching | F1 |
| π0.5 | base π0 (tamaño exacto **[no verificado]**) | FAST + flow matching | F2 |
| GR00T N1 | **[no verificado]** | flow matching (DiT) | F6 |
| SmolVLA | ~0,45B (100M experto); variantes 0,24B y 2,25B | flow matching | F3 |
| Evo-1 | 77M | — | F4 |

F5 indica que un modelo de >7B necesita más de 28 GB de VRAM en su forma nativa **[cifra de survey]**. Con una
GTX 1660 de 6 GB, solo SmolVLA es realista en local (inferencia); el entrenamiento va a la nube.

---

## 4. π0 en detalle (F1, con π0.5 de F2)

**Arquitectura.**
- VLM **PaliGemma** (3B) + **experto de acción** de ~300M con pesos propios que procesa el estado del robot y las
  acciones. Total 3,3B.
- Acciones por **flow matching** condicional, con 10 pasos de integración de Euler en inferencia.
- *Chunks* de H = 50 acciones; control de hasta 50 Hz. Latencia ~73 ms en una RTX 4090 a bordo (~86 ms fuera del robot).
- Ejecutan los *chunks* en bucle abierto **sin** ensamblado temporal: los autores vieron que el ensamblado
  empeoraba el resultado. Esto contrasta con ACT, que sí lo usa.
- Variante de control **π0-small** (~470M, sin VLM preentrenado) para medir lo que aporta el VLM.

**Datos.**
- Más de 10.000 h: ~903M pasos propios (7 configuraciones de robot, 68 tareas) más un 9,1 % de datos abiertos
  (Open X-Embodiment, Bridge v2, DROID).
- Cada combinación tarea-robot se pondera por n^0,43 para no sobrerrepresentar las grandes.
- Todos los robots se rellenan hasta 18 dimensiones de acción, de modo que un mismo modelo sirve para brazos
  simples y dobles.

**Preentrenamiento y post-entrenamiento.**
- Preentrenamiento con mucha diversidad y calidad irregular, que enseña a recuperarse de errores. El
  post-entrenamiento usa datos curados: de ~5 h para tareas simples a más de 100 h para tareas complejas.
- Para tareas largas usan un VLM de alto nivel que descompone la orden en subtareas en lenguaje.

**Resultados (cualitativos; los números están en figuras que no se han leído).**
- Sin ajuste fino (doblar camisetas, recoger mesa, embolsar compra, tostadas): mejor que OpenVLA y Octo en todas;
  casi perfecto en doblar camisetas y recogida fácil. Atribuyen el fallo de OpenVLA a que su discretización
  autorregresiva no admite *chunks*.
- Seguimiento de lenguaje: π0 sigue las órdenes claramente mejor que π0-small, es decir, **el VLM preentrenado
  es lo que da la comprensión del lenguaje**. Las instrucciones intermedias (de un humano o de un VLM de alto nivel)
  mejoran el resultado.
- Tareas nuevas con ajuste fino (apilar cuencos, doblar toallas, cajón...): en general mejor que OpenVLA, Octo,
  **ACT** y Diffusion Policy. Las mejores líneas base son las entrenadas desde cero (ACT, DP). El preentrenamiento
  llega a duplicar el rendimiento en algunos casos.
- Tareas complejas (lavandería, montar cajas, huevos): más del 50 % de la puntuación máxima en todas.

**Limitaciones que reconocen.** No se sabe bien qué mezcla de preentrenamiento es la mejor, cuántos datos hacen falta
para un rendimiento casi perfecto, ni hasta dónde llega la transferencia. Algunas comparaciones no son justas: las
líneas base se entrenaron menos pasos.

**π0.5 (F2).**
- Un solo modelo primero **predice la subtarea en lenguaje** y luego genera el *chunk* de acciones condicionado a ella.
- Preentrenamiento con tokens FAST (280k pasos); el post-entrenamiento añade el experto de flow matching (80k pasos).
- Datos: ~400 h de robots móviles en ~100 casas, más brazos fijos en muchos entornos, datos de laboratorio de otros
  robots (OXE), datos web (descripción de imágenes, VQA, detección) e instrucciones verbales de supervisores. El
  97,6 % de los ejemplos de la primera fase no son de robots móviles en casas.
- Ablaciones: quitar los datos de otros entornos o de otros robots degrada mucho el resultado. Quitar los datos web
  apenas afecta en general, pero empeora con **objetos de categorías no vistas**. Como planificador de alto nivel,
  π0.5 supera a GPT-4 en *zero-shot*.
- Limitaciones: tiradores raros, observabilidad parcial, y un razonador de subtareas que se "distrae" (abre y cierra
  un cajón en bucle). Además, prompts simples y sin memoria larga.

---

## 5. Fortalezas y debilidades documentadas

### 5.1 Fortalezas

| Fortaleza | Evidencia | Fuente |
|---|---|---|
| **Seguir órdenes en lenguaje** gracias al VLM | π0 frente a π0-small: el VLM marca la diferencia en seguimiento de lenguaje | F1 |
| **Multitarea en un único modelo** | SmolVLA en SO-100 (multitarea): 78,3 % de media frente a 61,7 % de π0 y 48,3 % de ACT entrenado por tarea | F3 |
| **Mejor que ACT con pocos datos tras preentrenamiento** | π0 supera a ACT y DP en tareas nuevas; SmolVLA en SO-101 Pick-Place-Lego: 90 % frente a 70 % de ACT en distribución | F1, F3 |
| **Generalización fuera de distribución** (moderada) | SmolVLA en SO-101: 50 % fuera de distribución frente a 40 % de ACT. π0.5: casas nuevas, y los datos web ayudan con objetos nuevos | F3, F2 |
| **Transferencia entre robots** | π0 y π0.5 mezclan robots; quitar datos de otros robots degrada π0.5 | F1, F2 |
| **Adaptación barata** | OpenVLA con LoRA (~20M parámetros) en hardware de consumo; SmolVLA entrenable en una GPU, 6× menos memoria que π0 | F5, F6, F3 |
| **Razonamiento semántico** | RT-2 generaliza a objetos nuevos y hace razonamiento básico; F5: destacan en semántica y seguimiento de instrucciones en entornos estructurados | F6, F5 |

### 5.2 Debilidades

| Debilidad | Evidencia | Fuente |
|---|---|---|
| **Precisión fina** | Discretizar en 256 bins pierde precisión; la cuantización degrada tareas submilimétricas. Menos precisos que los pipelines analíticos en control crítico | F5 |
| **Latencia** | Autorregresivos ~3-5 Hz; un LLM en doble sistema ~800 ms frente a ms del control, lo que causa tirones **[cifras de survey]**. "highly sensitive to latency" | F5, F4 |
| **Acciones obsoletas** | Si la inferencia es lenta, el robot ejecuta acciones viejas | F7 |
| **Coste de cómputo** | >7B necesita >28 GB de VRAM; la difusión cuesta ~3× | F5 |
| **Alucinación / mala interpretación** | Riesgo por "misinterpretation of instructions"; acciones erróneas pero confiadas; propuestas: token de rechazo (RationalVLA), pedir aclaración | F4 |
| **Grounding de objetos** | OpenVLA ignora ~23 % de las referencias a objetos en entornos nuevos; falla con combinaciones raras ("caballo amarillo") **[cifra de survey]** | F5 |
| **Sensibilidad a la formulación** | Ninguna fuente leída lo mide directamente. F5: CoVLA empeora con lenguaje ambiguo o ruidoso. SmolVLA reescribe sus etiquetas de tarea con un VLM (Qwen2.5-VL-3B) para que sean más claras, lo que sugiere que la calidad del texto importa | F5, F3 |
| **Caída fuera de distribución** | Hasta −40 % en tareas o variaciones no vistas **[cifra de survey]** | F5 |
| **Tareas largas** | SmolVLA lo admite como reto; las jerarquías propagan errores sin corregirlos | F3, F6, F7 |
| **Dependencia del hardware y estáticos** | Los modelos siguen ligados al robot y no aprenden tras el despliegue | F4 |
| **Datos de SmolVLA** | Solo SO-100 y ~23k trayectorias (frente a ~1M de OpenVLA); sin refuerzo | F3 |

---

## 6. Aplicaciones y retos abiertos

### 6.1 Aplicaciones descritas
- **F5:** humanoides, vehículos autónomos, **robótica industrial** (CogACT: montaje de varios pasos, atornillado,
  clasificación de piezas, con más de un 28 % de éxito sobre OpenVLA en tareas reales **[cifra de survey]**; adaptable
  a brazos de 6 GDL), medicina, agricultura de precisión, navegación con realidad aumentada, robótica doméstica y
  asistencial. La parte industrial es cualitativa: no da cifras de ciclo, precisión ni coste.
- **F7:** la mayoría de los VLA se centran en **hogar e industria**; además, asistentes, conducción, agricultura,
  cuerpos especializados (manos diestras, drones, cuadrúpedos, humanoides) y salud (con humano en el bucle).
- **F1/F2:** tareas domésticas de destreza (ropa, mesa, cajas, limpieza de casas nuevas).
- Educación: no se ha encontrado como aplicación explícita en lo leído **[no verificado]**. SmolVLA sí se presenta
  como robótica asequible y comunitaria (F3).

### 6.2 Retos abiertos (síntesis)
1. **Alineación multimodal y modelo físico:** los VLA imitan la física sin entender la causalidad (F4).
2. **Tiempo real:** cuantización, poda de tokens, salida temprana, decodificación paralela (OpenVLA-OFT), FAST e
   inferencia asíncrona (SmolVLA) (F4, F5, F7).
3. **Generalización y adaptación continua:** sim-to-real, refuerzo en línea, modelos estáticos (F4, F7).
4. **Seguridad e interpretabilidad:** barreras externas (AutoRT, SafeVLA), razonamiento visible (ECoT), estimación de
   confianza que permita pausar o pedir ayuda (F4, F7).
5. **Datos y evaluación:** heterogeneidad entre robots, métricas más allá del éxito binario (márgenes de seguridad,
   recuperación, eficiencia) (F4, F5, F7).
6. **Arquitectura:** cascada sin realimentación frente a paralelo difícil de entrenar; tacto, audio y 3D sin
   preentrenamiento comparable (F6). Arquitecturas híbridas VLA + controlador clásico (F5).
7. **Ética:** privacidad, empleo, sesgos (F5, F7).

---

## 7. Ideas para nuestra demo (5 minutos, SO-101, SmolVLA)

El jurado quiere ver un VLA. La forma más convincente de enseñarlo es mostrar **lo que ACT no puede hacer**:
**una sola red que cambia de comportamiento según la frase**. Propuestas, con el porqué:

1. **Misma escena, órdenes distintas, mismo modelo.** Dejar varias piezas en la mesa y dar 2-3 órdenes seguidas
   ("coloca la placa izquierda", "coloca la placa derecha", "pon el separador"). Que el modelo cargado sea uno solo
   (mostrarlo en pantalla). Es la fortaleza mejor documentada: multitarea con condicionamiento por lenguaje (F1, F3).
2. **Mostrar la cadena jerárquica en pantalla:** voz → transcripción → LLM → orden canónica → acción. Así se ve el
   patrón planificador + política (SayCan, Hi Robot, π0.5 en F6 y F2) y se da interpretabilidad, que F4 y F7 piden.
   Muy recomendable: el texto de la orden canónica visible mientras el brazo se mueve.
3. **Variación ligera fuera de distribución:** mover una pieza unos centímetros o cambiar el orden de las órdenes
   respecto a las demos. SmolVLA ganó a ACT fuera de distribución en SO-101 (50 % frente a 40 %, F3), aunque el
   margen es modesto: probarlo antes y no improvisar.
4. **Rechazo de órdenes fuera de vocabulario:** si la persona pide algo que no está en el vocabulario, el LLM
   responde "no sé hacer eso" en vez de mandar al brazo. Esto responde a la alucinación de órdenes y al "token de
   rechazo" que propone F4 (RationalVLA). Se ve bien en la demo y transmite seguridad.
5. **Comparación con ACT en una diapositiva o un vídeo, no en vivo:** "con ACT harían falta N políticas; con
   SmolVLA, una". Así se refuerza el argumento sin arriesgar tiempo.
6. **Inferencia asíncrona activada** si la latencia lo exige: SmolVLA acaba la tarea ~30 % antes en modo asíncrono
   (9,7 s frente a 13,75 s) con éxito similar (F3). Contarlo como detalle técnico.
7. **Mencionar el preentrenamiento comunitario:** SmolVLA se preentrenó con 481 datasets comunitarios de SO-100
   (F3), así que nuestro brazo es casi su robot nativo. Subir nuestro dataset a Hugging Face cierra el círculo con
   la comunidad.

**Qué evitar**
- **Tareas de precisión submilimétrica** (encajes con holgura mínima): los VLA son débiles en precisión fina (F5).
  Diseñar la junta con chaflanes, guías o tolerancias generosas y mantener la soldadura en sí fuera del alcance
  del VLA.
- **Órdenes libres directamente al VLA:** la sensibilidad a la formulación y el grounding son débiles (F5). Nuestro
  vocabulario cerrado traducido por un LLM es la mitigación correcta; las órdenes canónicas deben ser **idénticas**
  a las etiquetas de tarea del dataset (SmolVLA reescribió sus etiquetas para que fueran claras, F3).
- **Secuencias largas de una sola orden** ("monta toda la junta"): las tareas largas son el punto débil reconocido
  de SmolVLA (F3). Mejor encadenar subtareas cortas desde el LLM, que es lo que hace π0.5 internamente (F2).
- **Prometer generalización a objetos totalmente nuevos:** SmolVLA no tiene co-entrenamiento con datos web (F3), y
  en π0.5 son justamente los datos web los que ayudan con objetos nuevos (F2).
- **Depender de la GPU local para entrenar:** 6 GB es justo. Inferencia de SmolVLA en local sí parece viable
  (F3 dice GPU de consumo o incluso CPU), pero **medir la latencia real en la GTX 1660 antes del evento**.
- **Cambiar la iluminación o el fondo entre la grabación de demos y la demo:** las surveys señalan la caída por
  variabilidad del entorno (F5) **[cifra de survey]**.

---

## 8. Lo que no está claro o no se ha podido verificar

- **Cifras de resultados de π0:** están en figuras que no se han leído; solo se tienen conclusiones cualitativas.
- **Muchas cifras de F5** (17 % de sesgos, 23 % de referencias ignoradas por OpenVLA, −40 % fuera de distribución,
  +17 % de GR00T N1, 800 ms, 2,52×, 28 GB...) vienen de la survey sin detalle de cómo se midieron. No se han
  contrastado con los artículos originales.
- **GR00T N1/N1.x:** no se ha leído el artículo de NVIDIA. Solo se sabe por F6 que usa Eagle-2 + DiT de flow
  matching para humanoides y por F5 que es de doble sistema. Tamaño, datos y la versión **N1.7** que soporta LeRobot
  0.7 **[no verificados]**.
- **OpenVLA:** solo por surveys (7B, ~970k demos, LoRA). No se ha leído el original.
- **Tamaño exacto de π0.5**, y si sus pesos están disponibles en LeRobot 0.7 **[no verificado]**.
- **Helix** (Figure) y la educación como aplicación: no encontrados en lo leído.
- **Sensibilidad a la formulación de la orden:** ninguna fuente leída la mide para SmolVLA. Hay que probarlo
  nosotros (por ejemplo, "coloca la placa" frente a "pon la placa") si alguna vez se pasa texto no canónico.
- **Latencia de SmolVLA en una GTX 1660:** sin dato. Los artículos hablan de GPU de consumo o CPU sin concretar
  modelos.
- Secciones no leídas: conclusión y apéndices de F4; la segunda mitad de F6; la sección de datasets de F7; la parte
  final de F5 (solo conclusión y bibliografía).
- Los resúmenes por fragmentos los hizo un modelo auxiliar al leer el HTML. Las cifras clave para la demo (las
  de SmolVLA en F3) conviene comprobarlas en la tabla original antes de citarlas ante el jurado.
