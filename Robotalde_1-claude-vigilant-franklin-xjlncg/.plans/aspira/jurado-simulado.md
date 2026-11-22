# Aspira · jurado simulado (jueves 19-11-2026)

Encargo: simular al jurado sobre [concepto-v2.md](concepto-v2.md). Fuentes: `../brief/evento-novedades.md` (perfil del
jurado de Robotekin y rúbrica de 100 puntos) y `investigacion/analisis-concursos.md` §2.1. Riesgos tomados de
[equipo-rojo.md](equipo-rojo.md) y [tecnicas.md](tecnicas.md) §6. **Todo es simulación:** las notas, los
pensamientos y el resultado de los intentos son **[est.]**; no hay ningún dato nuevo. Jurados con roles, sin nombres.

## 0. La presentación imaginada (ejecución realista, no ideal)

Mesa con alfombrilla oscura, 4 ArUco, tabla clara, manguera colgando de un poste, portátil con la pantalla «lo que
dijo el juez → frase en inglés → cámaras». Equipo de 3 que conoce el SO-101 desde el viernes a las 18:00.

| Min | Qué pasa |
|---|---|
| 0:00-0:50 | Frase de entrada («Aguántame la aspiradora mientras taladro») y diapositiva del ciclo. Se alarga: van nerviosos |
| 0:50-1:40 | **Intento 1, agujero nuevo.** Acompaña al taladro (algo tembloroso), se congela, la aspiradora arranca por sonido, el robot espera, va al agujero y pasa. Queda un anillo de viruta en la tabla clara que solo se ve de cerca. **Acierto** |
| 1:40-2:20 | **Intento 2, alfombrilla.** El juez tira serrín y lo dice en castellano. El LLM tarda ~2 s; el VLA arranca con dudas y llega. **Acierto** |
| 2:20-2:55 | **Intento 3, agujero con la tabla movida.** El juez gira la tabla. El robot va al agujero, pero la pasada se queda corta de un lado. El equipo lo da por bueno; el juez duda. **Acierto discutido** |
| 2:55-3:30 | **Intento 4, canto.** El robot va hacia el agujero en vez de al canto (la red ignora la frase: el riesgo de §6). **Fallo** |
| 3:30-4:10 | **Intento 5, alfombrilla otra vez.** Se para a mitad durante unos segundos y alguien del equipo amaga con tocar; no toca; llega pasados los 30 s. **Fallo por tiempo** |
| 4:10-5:00 | Diapositiva de datos a toda prisa, preguntas recortadas por el tiempo |

Resultado: **3 de 5 = 18 sobre 30** (uno discutido). No caben bien 5 intentos *y* el relato en 5 minutos.

## 1. Los cuatro jurados

### J1 · Investigador de robótica de un centro tecnológico vasco
**Primeros 10 s:** «Un brazo con una manguera. Vale, otro asistente para el humano, como la linterna de octubre. A
ver si de verdad usa el VLA o es un ir al punto con visión.»
- **Le gusta:** una sola red con varias órdenes y una línea base programada al lado; la matriz frase × destino.
- **No le gusta:** el fallo del canto confirma que la red no siempre lee la frase; el agujero lo podría hacer la línea base.
- **Pregunta incómoda:** «En el intento 4 fue al agujero en vez de al canto. ¿Cuántas veces de 10 la red obedece la frase y cuántas va a lo que más ha visto?»

| Criterio | Nota | Por qué |
|---|---|---|
| Demo (30) | 18 | 3 de 5, uno dudoso |
| Datos (20) | 13 | Recolector programado + teleoperados, bien pensado; poca evidencia de iteración sobre fallos |
| Dificultad (15) | 11 | Varios pasos y tabla movida; ambicioso para 48 h |
| Utilidad (15) | 8 | Problema real pero menor |
| Innovación (10) | 6 | El multitarea con frase aporta; el esquema es el de MSN |
| Presentación (10) | 7 | Clara, corta de tiempo |
| **Total** | **63** | |

### J2 · Ingeniero de una ingeniería de automatización
**Primeros 10 s:** «Eso lo resuelve una boquilla de aspiración en el taladro por veinte euros. ¿Por qué un robot?»
- **Le gusta:** la regla «solo se mueve con el taladro callado», el Arduino para la aspiradora, la aspiradora por sonido.
- **No le gusta:** no ve cliente ni ahorro; en un taller de verdad aspira la herramienta. Ruido y polvo en la mesa.
- **Pregunta incómoda:** «¿Cuánta viruta recoge frente a un adaptador en el taladro? ¿Lo habéis pesado?»

| Criterio | Nota | Por qué |
|---|---|---|
| Demo (30) | 18 | Igual para todos |
| Datos (20) | 11 | No es su terreno; le valen las cifras si se enseñan |
| Dificultad (15) | 10 | Integración sólida (sonido, Arduino, ArUco) |
| Utilidad (15) | 7 | Existe una solución más barata para el caso principal |
| Innovación (10) | 5 | Para él, la linterna cambiada por una aspiradora |
| Presentación (10) | 7 | Se entiende enseguida |
| **Total** | **58** | |

### J3 · Profesor universitario de control y robótica
**Primeros 10 s:** «Control visual para acompañar la broca y luego aprendizaje para limpiar: buen reparto. ¿Saben
por qué han partido así o es casualidad?»
- **Le gusta:** lo rápido o seguro programado y lo variable aprendido; la línea base para comparar.
- **No le gusta:** el acompañamiento tiembla; la viruta clara sobre la tabla clara no se ve: ¿qué mira la red?
- **Pregunta incómoda:** «Si la viruta es clara y la tabla también, ¿la red ve la viruta o ve el agujero? ¿Qué pasa si limpio el agujero antes y le pido que limpie?»

| Criterio | Nota | Por qué |
|---|---|---|
| Demo (30) | 18 | Igual para todos |
| Datos (20) | 14 | Cámara fija y de muñeca, órdenes con destinos distintos, comparación con ACT |
| Dificultad (15) | 11 | Híbrido bien partido |
| Utilidad (15) | 8 | Correcta como prueba de concepto |
| Innovación (10) | 6 | Arquitectura razonada, no nueva |
| Presentación (10) | 6 | Respuestas técnicas algo inseguras |
| **Total** | **63** | |

### J4 · Técnico de vigilancia tecnológica de un fabricante de maquinaria (fue mentor)
**Primeros 10 s:** «Los he visto pelearse el sábado con la manguera. Han llegado más lejos de lo que pensaba.»
- **Le gusta:** el relato humano, la voz en castellano, que el juez desordena y el robot sigue; la evolución del equipo.
- **No le gusta:** que se parezca tanto al ganador de octubre; el intento 5 casi tocado.
- **Pregunta incómoda:** «¿Esto lo veis en una línea o en un taller? ¿Quién lo compraría?»

| Criterio | Nota | Por qué |
|---|---|---|
| Demo (30) | 18 | Igual para todos |
| Datos (20) | 14 | Vio el proceso de grabación y los cambios |
| Dificultad (15) | 12 | Sabe lo que costó |
| Utilidad (15) | 10 | Le encaja como asistente de puesto manual |
| Innovación (10) | 7 | Voz + varias órdenes |
| Presentación (10) | 8 | Equipo que responde con honestidad |
| **Total** | **69** | |

**Media: (63 + 58 + 63 + 69) / 4 ≈ 63 / 100.** Con el bonus completo (dataset en el Hub +3, repositorio
reproducible +2) ≈ 68. No conocemos las notas de los premiados de Robotekin, así que no se puede decir si da podio.

## 2. ¿Se percibe el VLA?

- **Momento que lo hace evidente:** el juez tira serrín en la alfombrilla, lo dice con sus palabras, la pantalla
  enseña `Clean the chips on the mat.` y el robot va allí; la línea base programada, en el mismo sitio, no sabe ir.
  Es el único momento en que la red hace algo que el programa no hace, delante del jurado.
- **Momento que lo hace dudoso:** el agujero nuevo, que es la tarea principal y la puntuada. La línea base también va
  al punto guardado, y la viruta clara apenas se ve sobre la tabla clara: un jurado de control piensa «va al agujero
  porque lo recuerda o porque el agujero oscuro se ve, no porque vea viruta». El fallo del canto (fue al agujero)
  refuerza la duda de que la red lee el texto. Las pausas y tirones de SmolVLA también se notan frente a lo programado.

## 3. ¿«Lo de Vitoria con una aspiradora»?

**Sí, en los primeros segundos, sobre todo J2 y J4** (el jurado de Robotekin premió a MSN hace un mes; si repite
jurado, lo recuerda). La estructura coincide: un humano trabaja con las manos, el robot sostiene una herramienta de
apoyo y la apunta a su punto de trabajo. **Lo que lo diferencia, si se enseña:** (a) dos fases (acompañar y luego
limpiar), (b) una red con varias órdenes dadas por el juez, (c) la tabla movida, que es el equivalente a la
oclusión resuelta de MSN, (d) suciedad real que se puede comprobar. **Lo que no lo diferencia:** si la parte que
funciona es solo «ir al agujero», a sus ojos es la linterna con otra herramienta y peor demo. Callarlo es peor que
decirlo: lo mejor es nombrar a MSN en la primera frase y decir qué se añade.

## 4. Qué recordarían una semana después

- «El de la aspiradora que se queda quieto mientras taladras y luego limpia.» (J2, J4)
- «El juez tiró serrín en la alfombrilla y fue a por él.» Si ese intento falla, desaparece el recuerdo bueno.
- «Se parecía a la linterna de Vitoria.» (J1, J2)
- «Ruido y una manguera colgando.» Ninguno recordaría cifras de datos si no hubo diapositiva clara.

## 5. Los 5 cambios que más subirían la media

| # | Cambio | Dónde suma | Puntos [est.] |
|---|---|---|---|
| 1 | **Tarea puntuada sin taladrar en cada intento:** agujeros ya hechos o serrín puesto por el juez, solo limpieza, ≤ 30 s; ensayada en series de 5 hasta ≥ 4/5. Taladrar se enseña una vez, fuera de los 5 | Demo +6 (de 3/5 a 4/5), presentación +1 al liberar tiempo | **+7** |
| 2 | **Hacer visible el resultado:** cara superior de la tabla oscura (equipo rojo, causa 1) y antes/después en pantalla, o viruta recogida pesada frente a la línea base y a un adaptador del taladro | Utilidad +2, dificultad +1 (pregunta de J2 y J3 contestada) | **+3** |
| 3 | **Momento VLA en vivo contra la línea base:** el juez desordena (alfombrilla, tabla girada durante la pasada) y la línea base falla al lado; si una orden no llega a ≥ 7/10 el sábado, quitarla de la demo (el canto) | Innovación +1, dificultad +1, demo (evita el fallo del canto) | **+3** |
| 4 | **Diapositiva de datos de 30 s:** episodios por orden (programados y teleoperados), matriz frase × destino X/10, VLA frente a ACT y línea base, lista «fallo → qué cambiamos»; dataset y repositorio subidos antes de las 11:00 | Datos +3; bonus +5 si no estaba | **+3 (+5 bonus)** |
| 5 | **Primera frase que desactiva «la linterna» y «el adaptador de 20 €»:** «MSN alumbraba un punto fijo; Aspira acompaña, espera y luego limpia lo que el adaptador no recoge, donde tú digas»; y un uso de puesto manual de taller como prueba de concepto | Innovación +1, utilidad +1, presentación +1 | **+3** |

Con los cinco, ≈ 63 → ~80 sin bonus [est.]; los puntos no son del todo sumables (el 1 y el 3 comparten la demo).

## 6. Las 5 preguntas que harán seguro y la mejor respuesta honesta

1. **«¿Por qué no un adaptador de aspiración en el taladro?»** — «Para taladrar en una tabla quieta, el adaptador
   basta. Aspira cubre lo que no lleva toma: la lija a mano, la viruta que cae a la mesa, la tabla que mueves. Es una
   prueba de concepto de asistente, no un sustituto del adaptador.» Dar la cifra solo si se ha medido.
2. **«¿Qué hace el VLA que no haga ir al punto guardado con visión?»** — «En el agujero, casi nada: la línea base
   también llega. El VLA aporta que una sola red cumple varias órdenes y destinos que no hemos programado uno a uno.
   Aquí está la tabla: VLA X/10, línea base Y/10 por orden.»
3. **«¿Cuántos episodios, de dónde salen y cómo iterasteis?»** — Cifras reales por orden; reconocer que los
   episodios del recolector programado enseñan la trayectoria del programa y que los teleoperados están para
   recuperarse; contar uno o dos fallos concretos y qué se cambió.
4. **«¿Por qué falló el intento 4 (o el que falle)?»** — «Con la escena casi igual, SmolVLA a veces ignora la frase;
   lo medimos el sábado y nos salió X/10 en esa orden. El plan B es un ACT por orden y que el LLM elija.» Sin
   excusas de luz si no es la causa; con gracia, como el cóctel de 2025.
5. **«¿Y la seguridad, con la mano al lado?»** — «Solo se mueve cuando el taladro está callado y va despacio. No
   detecta la mano durante la limpieza: en un puesto real haría falta un sensor o una zona vigilada.» No prometer lo
   que no está.
