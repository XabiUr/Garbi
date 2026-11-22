# Cómo ganan con una necesidad real (y cómo validarla en 2 días)

Fecha: 18-11-2026. Método research-ops: **[H]** hecho con fuente · **[I]** inferencia nuestra · **[R]** recomendación.
Base: los 37 proyectos de [investigacion/proyectos/](../../investigacion/proyectos/README.md) y
[analisis-concursos.md](../../investigacion/analisis-concursos.md), más búsqueda web del 18-11-2026.

## 1. Lo que dicen los datos

- **[H]** La única rúbrica oficial conocida (AMD) puntúa "creativity, difficulty, ease-of-use, and practicality" sobre
  100 y la misión libre pide "a creative solution to a real-world problem"; no exige usuario ni validación
  ([blog AMD](https://huggingface.co/blog/amd/openroboticshackathon)). Bases de Bilbao II y Robotekin 2026: no
  encontradas en la web.
- **[H]** En las 37 fichas del repo **ninguna documenta entrevistas, encuestas, cartas ni usuarios reales**
  (búsqueda de "entrevist|validac|carta|encuesta|testimonio" en `investigacion/proyectos/*.md`). La necesidad se
  cuenta siempre con **una escena reconocible**, no con datos:
  - MSN, 1.º Robotekin: "la tercera mano del soldador"; el jurado pone la mano y la luz la rodea
    ([ficha](../../investigacion/proyectos/hackathons-2026-europa.md), [repo](https://github.com/flipiflopi/Hackaton_Robotekin_SO-101_MSN)).
  - GreatAkihabara, 1.º AMD Tokio: pedidos de una tienda pequeña; el cliente solo pide
    ([ficha](../../investigacion/proyectos/hackathons-2026-mundo.md)).
  - Tubos, 1.º CCSF: "robots que ayudan a los científicos en las tareas más repetitivas"; el juez premió la
    dificultad, no la necesidad ([crónica](https://worldwidestudios.substack.com/p/ccsf-robotics-hack-recap-1-day-build)).
  - CaliKPR, 1.º Junfan #35 y "Mejor despliegue real": el tema del jurado fue la **confianza** (20/20 medido)
    [no verificado, fragmentos de redes] ([ficha](../../investigacion/proyectos/hackathons-2026-mundo.md)).
  - Baby Reachy (179 likes): "lo construí para mi hijo", historia personal
    ([ficha](../../investigacion/proyectos/top-huggingface.md)).
- **[H]** En nuestra rúbrica, la utilidad de los ganadores se queda en 5-7/10; ninguno pasa de 8
  ([README](../../investigacion/proyectos/README.md)). Un juez de hackathons generalistas: "validation gives you
  extra points", y recuerda a un equipo que ganó tras conseguir "a letter of interest" de decisores de grandes
  instituciones ([e27](https://e27.co/how-to-do-well-in-a-hackathon-a-mentor-and-judges-perspective-20190901/)).
  AngelHack: los equipos dedican ~5 % del pitch al problema; "the winning split is closer to 30 % problem and 70 %
  solution", y piden nombrar **a una persona concreta** con el problema ([AngelHack](https://angelhack.com/blog/hackathon-tips-for-winners/)).
- **[I]** En los hackathons de LeRobot la necesidad **no gana sola** (Rubí Automotive, celda industrial impecable,
  sin premio), pero es **el hueco donde nadie compite**: todos se quedan en 5-7 de utilidad porque nadie la
  demuestra. Validarla es barato y nos separa en 20 puntos de la rúbrica que el resto deja a medias.

## 2. Patrones que funcionan

| # | Patrón | Ejemplo con fuente | [R] Cómo aplicarlo |
|---|---|---|---|
| 1 | **Escena de 5 s** con un usuario concreto | MSN, Tokio, CCSF (arriba) | Una frase: "Iñaki, técnico de mantenimiento, con la línea parada" |
| 2 | **El jurado vive el dolor** | MSN: el juez tapa la luz | El juez provoca la avería y espera |
| 3 | **Cifra de dolor con fuente** | Ningún ganador lo hizo [H] | Una sola cifra en una diapositiva, con la fuente debajo |
| 4 | **Voz del usuario real** (cita, foto, carta) | Equipo de la carta de interés ([e27](https://e27.co/how-to-do-well-in-a-hackathon-a-mentor-and-judges-perspective-20190901/)) | 1 cita textual con permiso + foto del puesto real |
| 5 | **Fiabilidad medida = confianza** | CaliKPR 20/20; camisetas 90 % en 20 ensayos | Marcador X/10 en pantalla: "lo que un taller necesita es que no falle" |
| 6 | **Historia personal** | Baby Reachy | Si alguien del equipo vive el problema, contarlo |

## 3. Patrones de "necesidad falsa" que se penalizan

- **[H]** Utilidad baja en nuestra rúbrica: juegos y espectáculo (Conecta 4: 4; Robotticelli: 3; Armtender:
  4, "camarero-juego, idea repetida") ([fichas](../../investigacion/proyectos/README.md)).
- **[I]** La validación **no sustituye** a la demo: Rubí Automotive (celda industrial bien justificada, 692
  episodios) quedó sin premio en Robotekin ([analisis-concursos.md](../../investigacion/analisis-concursos.md)).
- **[I]** Señales de necesidad falsa que un jurado técnico detecta:
  1. **Disfraz:** clasificar cubos de colores y llamarlo "reciclaje" o "farmacia" sin que el objeto se parezca.
  2. **Cifra genérica** ("el mercado de la robótica vale X billones") en vez del dolor de una persona.
  3. **Usuario que no puede usarlo:** asistencia a discapacidad con objetos cerca de la cara y sin seguridad (el
     consejo descartó ManoLibre por eso: [decision.md](../brainstorming/decision.md)).
  4. **El robot hace lo que una persona hace mejor y más barato** sin explicar por qué (camarero, ya quemado).
  5. **Validación inventada o hipotética** ("a la gente le encantaría"): mejor ninguna que una floja.
  6. **Solución sin coste real comparado:** no decir qué cuesta hoy la alternativa (Kinova, Obi, un operario).

## 4. Guía de validación en 2 días (miércoles 18 y jueves 19)

**[R]** Método "Mom Test": preguntar por **lo que hicieron la última vez**, no por lo que harían; los cumplidos
no cuentan, los compromisos sí (tiempo, reputación, una carta)
([resumen](https://sachinrekhi.com/the-mom-test-rob-fitzpatrick), [reseña](https://mtlynch.io/book-reports/the-mom-test/)).

| Cuándo | Quién | Qué | Entregable |
|---|---|---|---|
| Mié tarde (1 h) | Uno | Lista de 10 contactos del usuario objetivo: 3 centros de FP de mantenimiento industrial, 3 talleres o plantas (conocidos, familia, LinkedIn), 2 profesores de la universidad, 2 asociaciones o clústeres | Hoja con nombre, vía y estado |
| Mié tarde-jue mañana | Los tres, ~4 llamadas cada uno | Llamada de 10 min con 5 preguntas (abajo). Pedir permiso para citar y una foto del puesto | ≥ 5 conversaciones anotadas |
| Jue mañana | Uno | Encuesta de 3 preguntas (Google Forms) al grupo del FP o del taller, solo si hay quien la mueva | ≥ 10 respuestas o se descarta |
| Jue tarde | Uno | Pedir **2-3 líneas por correo** a la persona más interesada ("nos parecería útil probarlo porque…"). Sin logotipo si no lo autoriza | Carta o correo con permiso |
| Jue noche | Todos | Una diapositiva: persona concreta + 1 cifra con fuente + 1 cita + foto. Si no hay validación, no se inventa: se cuenta como hipótesis | Diapositiva del problema (30 % del pitch) |

Las 5 preguntas (adaptar al hueco): (1) ¿Cuándo fue la última vez que pasó X? Cuéntamelo. (2) ¿Cuánto tiempo o
dinero costó? (3) ¿Qué hicisteis para resolverlo? ¿Qué habéis probado antes? (4) ¿Quién lo sufre más? (5) Si os
enseñamos un prototipo el domingo, ¿lo miraríais / nos dejaríais citaros?

Reglas: no mencionar el robot hasta la pregunta 5; anotar frases literales; guardar la fuente de cada cifra; no
usar nombres ni logos sin permiso escrito.

## 5. Huecos con necesidad real sin explotar (con brazo barato + VLA)

"Sin explotar" = no aparece en los 37 proyectos del repo ni en las búsquedas web del 18-11-2026 con SO-101/LeRobot
[I: ausencia de evidencia, no prueba de ausencia].

| # | Hueco | Dolor con fuente [H] | Encaje SO-101 (objetos gruesos, coger y dejar) [I] | Riesgo [I] |
|---|---|---|---|---|
| 1 | **Mantenimiento: traer el repuesto correcto y reponer la máquina** (es Relevo) | Paradas no planificadas: ~1,4 billones $ al año en la Fortune Global 500, 11 % de ingresos, encuesta a 181 profesionales ([Siemens TCOD 2024](https://assets.new.siemens.com/siemens/assets/api/uuid:1b43afb5-2d07-47f7-9eb7-893fe7d0bc59/TCOD-2024_original.pdf)). Euskadi: 1 entrada al mercado laboral por cada 4,5 jubilaciones (Orkestra, vía [Onda Vasca](https://www.ondavasca.com/los-jovenes-solo-cubriran-un-cuarto-de-las-jubilaciones-en-euskadi/)) | Alto: 3 módulos gruesos, una red elige por la frase, sensor confirma | Parecer "clasificar piezas" (Rubí, sin premio). La cifra es de grandes empresas: hablar de "el técnico que no está" |
| 2 | **Sacar baterías de litio del flujo de residuos** | >10.000 incendios al año en plantas de clasificación alemanas, ~80 % por baterías de litio (estudio BDE citado por [Fraunhofer IIS](https://www.iis.fraunhofer.de/en/pr/2025/pressrelease-battery-recycling.html)); hoy se detectan con rayos X y soplado ([Fraunhofer](https://www.iis.fraunhofer.de/en/pr/2025/pressrelease-battery-recycling.html)) | Alto: "coge la batería" entre basura variada es justo lo que un VLA hace mejor que un clasificador de color; power banks y pilas gruesas (maquetas, nunca reales dañadas) | Escala: el brazo no sigue una cinta real; venderlo como "puesto de rescate" tras la detección |
| 3 | **Acercar objetos a una persona dependiente** (vaso, mando, pastillero a un punto fijo) | Brazos asistivos: Kinova JACO ~35.000-40.000 $ ([Futurism](https://futurism.com/robot-arm-wheelchair), [NIBIB](https://www.nibib.nih.gov/sites/default/files/R-ARM.pdf)); Obi ~8.600-13.000 $ ([Rehab-store](https://www.rehab-store.com/p-obi-robotic-independent-feeding-device.html), [Especialneeds](https://especialneeds.com/products/obi-robotic-self-feeder)). España: 174.406 personas en lista de espera de dependencia y 1.575.682 con prestación (sep 2025, [La Moncloa](https://www.lamoncloa.gob.es/serviciosdeprensa/notasprensa/derechos-sociales-consumo-agenda-2030/paginas/2025/071025-aumento-prestacion-dependencia.aspx)) | Medio: coger y dejar en bandeja fija, por voz; Cornell validó con 13 usuarios ([Cornell](https://www.news.cornell.edu/stories/2024/05/robotic-system-feeds-people-severe-mobility-limitations)) | Seguridad e higiene (motivo del descarte de ManoLibre); necesidad emocional fuerte, pero la validación con usuarios reales no cabe en 2 días |
| 4 | **Laboratorio: carga de racks y tubos gruesos** | ~90 % de quienes pipetean >1 h seguida refieren molestias en mano o codo (David y Buckle 1997, n = 80, vía [Labcompare](https://www.labcompare.com/10-Featured-Articles/592969-Tips-for-Reducing-Pipetting-Strain/)) | Medio: tubos Falcon de 50 ml con pinzas impresas; pipetear queda fuera del SO-101 | Ya explotado a medias: tubos a la gradilla ganó CCSF; la cifra es de pipeteo, no de carga |

**[R] Recomendación.** El hueco 1 es el que mejor encaja con la decisión del equipo (Relevo) y con Bilbao; la
validación barata es llamar a **centros de FP de mantenimiento y a 2-3 talleres** y traer una cita, una foto del
cajón de repuestos real y una cifra local (tiempo medio que tarda en llegar el repuesto). El hueco 2 es la mejor
alternativa si se quiere un VLA más visible ("coge la batería" entre objetos variados) y una cifra de dolor más
fuerte; habría que validarlo con una planta de clasificación o un punto limpio. Los huecos 3 y 4 tienen necesidad
real pero chocan con seguridad (3) o con un precedente ganador (4).

## Pendiente / no verificado

- Bases y criterios oficiales de Bilbao II y Robotekin 2026: no encontrados en la web.
- La cifra de Orkestra (1 por 4,5) y la de David y Buckle vienen de fuentes secundarias; abrir el original antes de
  ponerlas en una diapositiva. La de Siemens es una extrapolación de 181 entrevistas en grandes empresas.
- Precios de Kinova y Obi: de prensa y tiendas, con fechas distintas; usar como orden de magnitud.
