# Aspira · competencia y diferenciación (19-11-2026)

Fuentes: [concepto-v2.md](concepto-v2.md), [analisis-ganar.md](analisis-ganar.md), ficha de MSN en
`investigacion/proyectos/hackathons-2026-europa.md`, patrones en `investigacion/proyectos/README.md`, catálogos de
vídeo en `.plans/brief2/` y `.plans/brief/evento-novedades.md`. Sin búsqueda web nueva: todo dato sale de esos
documentos. **[est.]** = juicio nuestro, no dato.

## 1. Frente a MSN (Robotekin, Vitoria, oct 2026, 1.º)

Mismo operador (Bravo Robots), mismos premios y, probablemente, un jurado parecido (industria, Ikerlan, EHU; el de
Bilbao no está publicado).

| Punto | MSN | Aspira | ¿Se parece? |
|---|---|---|---|
| Necesidad | «Tercera mano» del técnico de electrónica: luz donde suelda | «Segunda persona» que aguanta la aspiradora al taladrar madera pequeña | **Sí en el marco** (manos ocupadas en el banco); no en el problema |
| Qué cambia en el mundo | Nada: alumbra y se aparta | **Deja el banco limpio**: se ve y se pesa (foto cenital, báscula) | No |
| Banco | Banco de electrónica, PCB, boli | Alfombrilla oscura, tabla de pino, taladro que suena | Mismo formato de mesa |
| Seguimiento de herramienta | IBVS con Broyden sobre la punta del boli; esquiva la mano con parábolas | Marcador en el taladro + control visual; lado libre sin chocar con la mano | **Sí, casi idéntico** (es la fase «Acompañar») |
| Qué se aprende | Un ACT para **coger la linterna** (54 ep.); lo vistoso es programado | **SmolVLA que limpia** y obedece 4 frases; lo vistoso es aprendido | **Al revés**: el reparto ACT+programado es el mismo patrón, invertido |
| Voz | Google SpeechRecognition, «pulsar M» | Voz en castellano → LLM → frase fija a la red | Sí, parecido |
| Sensores/actuadores propios | Ninguno extra (linterna pasiva) | Aspiradora con Arduino, disparo por sonido del taladro | No |
| Memoria y fases | Un modo continuo (apuntar, esquivar, volver) | Ciclo de 6 fases; recuerda el agujero en coordenadas de la tabla | No |
| Momento | La luz rodea la mano del juez | El juez mueve la tabla o tira serrín, y lo limpia igual | Misma estructura: el juez interviene y el robot se adapta |

**Riesgo real de «es lo de Vitoria con una aspiradora»: alto si se abre con «Acompañar», bajo si se abre con
«Limpiar»** [est.]. La fase de acompañar el taladro *es* la demo de MSN con otra herramienta: un brazo que sigue una
punta y esquiva la mano. Si es lo primero que ve un juez que estuvo en Vitoria, ya ha clasificado el proyecto. Lo
que MSN no tenía: una parte aprendida vistosa, un resultado físico medible y un actuador propio. Eso hay que
enseñarlo antes.

**Cómo contarlo: citarlo en una frase y pasar a lo que no tenía.** Negarlo es peor: el jurado lo verá igual.
- Primeros 30 s, en este orden: (1) **sonido**: el juez aprieta el taladro, la aspiradora arranca sola y el brazo
  está quieto; (2) retira el taladro, **mueve la tabla con la mano**; (3) el brazo va al agujero nuevo y lo deja
  limpio. Nada de seguimiento todavía.
- Frase, hacia el segundo 30: «Hace un mes ganó aquí un robot que alumbra donde sueldas; nos gustó mucho. Ese robot
  aprendió a coger la linterna. El nuestro aprendió a limpiar, y le puedes decir qué.»
- Acompañar el taladro se enseña después, como «lo que ya sabemos que funciona» (el patrón premiado), sin venderlo
  como novedad. Si sale bien, suma fiabilidad; si falla, no tumba el relato.
- No usar la palabra «tercera mano» (es la de MSN). Decir «la segunda persona que te aguanta la manguera».

## 2. Frente a los otros ~20 equipos

Lo típico según los catálogos: pick-and-place y clasificar, doblar ropa (en casi todas las sedes), comida y bebida
en directo, ordenar y **limpiar la mesa** (ganador de Seeed China, XLeRobot, Spice Terminator frotando platos),
ajedrez y juegos, camarero (quemado: Bilbao 2025, Zúrich 2026).

| Destaca en la sala | Lo hace parecer uno más |
|---|---|
| Una herramienta de verdad que **suena**: atrae a quien pasa (encaja con «física, fricción» de la web) | Si se ve como «brazo que barre la mesa con un tubo»: es el género «limpiar la mesa», ya premiado y visto |
| Una persona **trabajando** al lado; el robot reacciona a ella, no a un botón | Una pantalla con una frase en inglés y un SmolVLA multitarea: lo hicieron Conecta 4 y GreatAkihabara |
| Necesidad evidente con apaños virales (pósit, botella, ~188 k visitas el más visto) y ningún robot en vídeo | Voz + LLM a secas: existe en demos de producto sin necesidad y ningún ganador la cita |
| Resultado medido en gramos y píxeles, mitad limpia frente a mitad sucia | Polvo y ruido mal gestionados: si la organización lo frena, quedamos sin herramienta |
| Hardware propio pequeño y visible (boca impresa, Arduino, aspiradora) | Un marcador en el taladro sin explicar puede leerse como truco |

Regla para la mesa [est.]: que **se oiga el taladro y se vea viruta** cada pocos minutos durante el sábado (cuando
se permita); el resto de mesas serán silenciosas.

## 3. El relato

**Frase de pitch (16 palabras):** «Aspira: el robot que te aguanta la aspiradora mientras taladras y limpia lo que
le pidas, donde esté.»
Alternativa más corta: «Tú taladras. Aspira espera, aspira y limpia lo que le digas, aunque muevas la tabla.»

**El nombre.** «Aspira» es bueno: se entiende en castellano sin explicar, es un verbo (lo que hace) y tiene el doble
sentido de «aspirar a». Contras: es genérico y difícil de buscar en internet. Alternativas:
- **Garbi** (euskera). Hasta donde sé, *garbi* significa «limpio» y *garbitu* «limpiar»; estoy razonablemente
  seguro, pero **conviene confirmarlo con alguien que hable euskera** antes de ponerlo en la diapositiva. Encaja con
  un jurado vasco y con Bilbao. Riesgo: puede existir ya como marca de limpieza; no lo he comprobado.
- **Viruta** (castellano): concreto, simpático, dice el oficio. Se olvida menos que «Aspira» [est.].
- Descartado *zerrauts* («serrín»): creo que es la palabra, **no estoy seguro**; no usarla sin verificar.

**La persona.** Recomiendo **el profesor de tecnología de un instituto** que prepara maquetas y piezas de madera en
su mesa: une utilidad («25 alumnos taladrando»), educación (lo que pidió Robotekin y el tono STEAM de la Semana) y un
escritorio pequeño, que es el banco de la demo. Segunda opción: el maquetista (más íntimo, menos impacto social).
**Si alguien del equipo hace maquetas o carpintería, usar su historia real**; si no, presentarlo como un perfil
(«pensad en un profe de tecno…»), nunca como una persona real inventada.

Historia en 4 frases: «Mikel [nombre de ejemplo] da tecnología. Cada tarde taladra piezas para la clase de mañana.
Para no llenarlo todo de polvo sujeta la manguera con la otra mano, o pega un pósit doblado bajo la broca, como
hacen miles en internet. Aspira le aguanta la manguera, espera mientras taladra y limpia cuando acaba.»

**Gancho del vídeo de 1 minuto:**
- 0-5 s: plano cenital, alguien taladra **con el pósit doblado** (recreado por nosotros, no metraje ajeno) y el
  polvo cae igual. Rótulo: «Así lo resuelve internet».
- 5-20 s: misma tabla con Aspira: arranca la aspiradora sola, el brazo quieto; se retira el taladro, alguien mueve
  la tabla y el brazo limpia el agujero nuevo.
- 20-40 s: voz «se me ha caído serrín en la alfombrilla» → pantalla con la frase → limpia la alfombrilla.
- 40-55 s: las dos mitades de la tabla y los números (gramos, «veces que soltaste la herramienta: 5 frente a 0»).
- 55-60 s: nombre, frase, «dataset y modelo en Hugging Face».

## 4. El momento memorable

| Candidato | A favor | En contra |
|---|---|---|
| A. Mitad limpia frente a mitad sucia, con contador | Utilidad visible y medible; foto final para el jurado | Es un resultado, no un momento: llega al final y es estático; lo programado también lo lograría |
| B. La aspiradora se enciende sola al taladrar | El sonido llama la atención de la sala; se entiende sin palabras | Programado (Arduino + sonido): no dice nada del VLA ni de los datos |
| C. El juez mueve la tabla y luego tira serrín donde quiera y dice «límpialo» | El juez interviene y el robot se adapta, como la mano en MSN, pero **con la parte aprendida**; prueba memoria (agujero) y visión + lenguaje (serrín) | Dos subsistemas encadenados; si el VLA falla, falla delante del jurado |

**Elegiría C**, en su forma mínima: **el juez mueve la tabla** (la acción ya es el intento puntuado, «limpiar el
agujero nuevo») y, si queda tiempo, el serrín en la alfombrilla como segundo intento. Es el equivalente directo de
«la luz rodea la mano», así que el jurado lo compara con MSN en nuestro terreno: allí el juez estorba y el robot se
aparta; aquí el juez desordena y el robot lo arregla. B va como apertura (sonido) y A como cierre (foto).

## 5. Hacer visible el VLA a un jurado no especialista (5 minutos)

Idea que hay que transmitir, sin la sigla: **«una sola red que mira la mesa, entiende una frase y decide el
movimiento; se la enseñamos con la mano, como a un aprendiz».**

**En pantalla (una sola vista, siempre visible):**
1. Lo que dijo el juez (castellano) → la frase fija que entra a la red (inglés), en grande.
2. Las dos cámaras (fija y muñeca) con la viruta clara sobre lo oscuro.
3. Un marcador **X/10 por orden** y la matriz frase × destino, con los fallos también.
4. Al lado, la **línea base programada** con su resultado en la misma escena.

**Prueba en vivo (60-90 s dentro de los 5 minutos):**
- **Misma escena, dos frases, dos gestos.** Con viruta en el agujero y en la alfombrilla a la vez, el juez dice
  primero «limpia el agujero» y luego «limpia la alfombrilla»: la misma red hace dos cosas distintas solo porque
  cambia la frase. Es lo más claro para quien no sabe qué es un VLA [est.].
- **Contra la línea base.** El juez pone el serrín donde quiera: la línea base va al punto guardado y falla; la red
  va a donde está la viruta. Un fallo visible del programado vale más que una explicación.
- **Datos en 15 s:** «N episodios grabados por un recolector automático + 20-30 por orden con la mano para enseñarle
  a corregirse; esto falló y así lo arreglamos». Es el criterio de 20 puntos y casi nadie lo cuenta bien.

No enseñar: arquitectura de SmolVLA, curvas de pérdida ni jerga. Si preguntan, mostrar el dataset en el Hub.

## Resumen para decidir

1. Abrir con sonido + mover la tabla + limpieza aprendida; acompañar el taladro va después.
2. Citar a MSN en una frase y marcar la diferencia: «aprendió a coger; el nuestro aprendió a limpiar y obedece».
3. Momento: el juez desordena y el robot arregla (C), con A como cierre y B como apertura.
4. Nombre: mantener Aspira; Garbi como alternativa solo tras confirmar el euskera.
