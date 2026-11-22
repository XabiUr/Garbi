# Equipo rojo · «Aprendiz» versión 3 (18-11-2026, noche)

Encargo: demostrar que este plan pierde y que el usuario lo rechazará, y decir qué cambiar. Fuentes: los documentos
de `.plans/brief/`, `investigacion/analisis-concursos.md` y el inventario de software. **[est.]** = estimación mía sin
medir. No hay ningún dato nuevo: todo lo que afirmo sale de esos documentos o es aritmética sobre ellos.

**Las cuatro grietas que nadie ha escrito todavía:**

1. **La tarea puntuada no contiene el portátil.** Los 5 intentos de la versión 3 son cinco «traer» sueltos. Si se
   quita el portátil de la mesa, la demo con nota no cambia. Eso es, literalmente, «coger y dejar con una historia».
2. **Entre intentos el técnico devuelve la cosa al estante con su mano** (corrección 2 del consejo). El jurado ve a
   la persona hacer en 3 s, y en sentido contrario, el mismo viaje que el robot acaba de hacer en 25 s. La demo
   enseña ella misma que la mano gana, y además la mano entra en la zona del brazo cinco veces.
3. **No cabe en 5 minutos.** 5 × 25 s = 125 s de brazo, más reponer y dictar (~10 s por intento [est.]) ≈ 3 min.
   Quedan 2 min para problema, datos y preguntas. La reparación de 3 minutos no entra en la misma presentación.
4. **El viernes hay 3 horas de trabajo (18:00-21:00; la noche es «opcional»)** y el plan pide 100 episodios con un
   equipo que nunca ha teleoperado, sin controlador del robot real ni guion de grabación escritos (inventario).

## 1. Autopsia anticipada: domingo, 13:00, sin podio

Ordenadas por probabilidad × daño [est.]. «Cuándo» es el primer momento en que se podría ver.

| # | Causa | Señal temprana | Cuándo | Medida más barata |
|---|---|---|---|---|
| 1 | **3 de 5 o menos en la demo.** Con p ≈ 0,75-0,80 [est. de las fichas], el 5/5 sale un 24-33 % de las veces; y el jurado simulado da 18 puntos (3/5) al agarre no probado | Series de 10 el sábado por debajo de 8/10; fallos concentrados en la caja girada | Sáb. 16:00 | Declarar la tarea con las zonas y el giro que salieron ≥ 8/10, no con los grabados. Ensayar series de 5 completas, con dictado y reposición, desde el sábado a las 18:00 |
| 2 | **El viernes no se graba.** Tres horas para montar, calibrar, fijar cámaras, aprender a teleoperar y grabar; falta todo el software del robot real | A las 19:30 no hay un episodio válido en disco; errores de puerto, de vídeo o de cámara | Vie. 19:30 | Jueves: instalar LeRobot 0.7 en dos portátiles y dejar en una hoja los comandos de `lerobot-record`, `lerobot-train` y `lerobot-rollout` copiables. Viernes: una sola orden (vaso) hasta tener 50 |
| 3 | **SmolVLA ignora la frase** (riesgo conocido, apartado 6 de las directrices) y se descubre el sábado a las 9:30 con el concepto cerrado | El ciclo 0 coge siempre el objeto más cercano o siempre el mismo | Sáb. 9:30-10:30 | Vaso y caja muy distintos a la vista (forma, color y brillo), datos equilibrados, y el ACT por orden entrenando desde el viernes por la noche, no desde el sábado a las 20:00 |
| 4 | **«Lo cojo yo en 3 segundos»** (J2, y los dos evaluadores) y el propio guion lo confirma con la mano que repone | En el ensayo del jueves sin robot, el cambio de memoria completo dura menos que los viajes del brazo | Jue. tarde | Apartado 3: medir el jueves el banco sin robot. Apartado 2: quitar la reposición a mano y alejar el estante |
| 5 | **Rúbrica distinta de la de Robotekin** (es una inferencia; en 2025 había categorías y el jurado se acercó a la mesa) | El mentor no menciona «5 intentos» ni «tarea declarada» | Vie. 17:45 | Llamar o escribir el jueves a la organización (teléfono y correo en `evento-novedades.md`). Tener el formato de 90 s ensayado como formato principal, no de reserva |
| 6 | **Se confunde con las otras mesas y con MSN.** El jurado simulado deja a «Aprendiz» 10.º de 13 («acercar a 30 cm», «otro ayudante de banco de electrónica como el del mes pasado») | Viernes: varias mesas con coger y dejar por voz | Vie. 21:00 | Lo único que nadie más tendrá: un aparato real que arranca y una tabla medida. Deben verse en los primeros 10 s, no al final |
| 7 | **Sin cita de usuario.** Reciclanet está en pausa hasta 2027; Bizkaia Repara 2026 no está comprobada; la pregunta 4 puede salir «me estorba» | A las 12:00 del jueves nadie ha cogido el teléfono | Jue. 12:00 | Ir en persona a dos tiendas de reparación con el plato impreso y un vídeo de 20 s; una foto del banco y una frase firmada valen más que la Directiva |
| 8 | **El agarre o el alcance fallan en el robot real.** Ningún gesto está probado; el plato está «en el borde del alcance» y el brazo extendido tiembla | En teleoperación, la caja se escapa o el plato no se alcanza sin estirar del todo | Vie. 18:30 | Jueves: imprimir vaso y caja en tres anchos (30, 35 y 40 mm) y medir la apertura de la pinza en el CAD público del SO-101. Viernes: 10 agarres de cada uno por teleoperación antes de grabar nada |
| 9 | **Infraestructura:** inferencia en la GTX 1660 sin medir, wifi no garantizada, voz con Web Speech (necesita internet) en una sala con 140 personas, nube para entrenar | El ciclo tarda más de 25 s; el reconocimiento de voz falla con ruido | Vie. 20:00 / sáb. 12:00 | Teclado o botones como entrada principal y la voz como capa que se quita. Medir la latencia el viernes con un modelo sin ajustar. Un móvil con datos reservado para subir y entrenar |
| 10 | **Alcance:** dos formatos de demo, versión de 90 s, lectura de etiquetas, `/subtask`, `dagger`, tercer objeto, reed, LED, tablet, personaje, tres ciclos | El sábado a las 12:00 alguien programa la tablet en vez de grabar | Sáb. 12:00 | Apartado 6: quitarlo hoy. Regla: hasta 8/10 en el robot, nadie toca nada que no sea datos, entrenamiento y evaluación |
| 11 | **Se mueve el montaje.** Cámara, flexo o mesa cambian entre la grabación y la demo (lo primero de la lista de «lo que hace perder»); la mesa es de la organización | La imagen `top` del domingo no coincide con la del viernes | Sáb. noche | Todo atornillado a un tablero propio que se lleva montado; foto de referencia de cada cámara y comparación cada mañana. Quitar la columna «flexo desplazado» de la tabla |
| 12 | **El usuario lo rechaza el jueves a mediodía** (apartado 2) y se pierde el único día de preparación | No hay un «sí» explícito esta noche | Hoy | Pedir el «sí» hoy con las cuatro grietas de arriba a la vista. El jueves, empezar por lo que sirve con cualquier concepto: soportes de cámara, tablero, comandos de LeRobot |

Causas menores que no entran en las 12: el portátil no se consigue o tarda en arrancar (solo afecta al relato); cansancio
(el ganador de 2025 lo cita: dormir); elegir el modelo por la pérdida; el guardado descoloca el estante.

## 2. Por qué el usuario podría rechazarlo

**Contra cada criterio.**

| Criterio | Veredicto | Razón |
|---|---|---|
| U1 valor real | **Falla hoy** | La ficha lo dice: «no encontré ninguna queja» sobre tener que soltar para coger algo. MSN alumbra donde la mano no puede; Aprendiz acerca lo que la mano alcanza. El valor que queda (registro, hoja del equipo) es de la tablet |
| U2 requiere VLA | Dudoso | La ficha admite que con dos objetos conocidos valen un detector y cinemática inversa. En el plan B (un ACT por orden) el VLA desaparece. Solo se salva con la matriz medida y un objeto nunca visto |
| U3 bajo fallo | Dudoso | Una orden de cada cuatro o cinco falla [est. de las fichas]. Nada probado en un SO-101. Equipo sin experiencia |
| U4 herramienta real | Pasa a medias | El portátil es real. El vaso, el plato y el estante son útiles nuestros: la mitad de lo que toca el robot es decorado |
| U5 colaboración | Dudoso | En los 5 intentos nadie trabaja: es un examen. La colaboración vive en la reparación de 3 min, que no cabe; y en ella la persona espera (ver apartado 3) |
| U6 banco de trabajo | Pasa | |
| U7 aplicación que ya se vende | **Falla** | La ficha: «nadie vende un aprendiz de banco: es un hueco». La referencia que se cita (Ultra) es preparación de pedidos en almacén, no un banco |

**Contra cada rechazo anterior.**

- **Cinco asistentes de banco sin respuesta** («faltaba el anclaje en una aplicación que el mercado ya paga»):
  Aprendiz es el sexto asistente de banco, y sigue sin ese anclaje. Es el parecido más peligroso.
- **Maquetas («estamos enfocando mal esto»):** el concepto nació de fusionar las mecánicas más fiables de 13 fichas,
  no de un técnico. La regla del usuario es «se parte de una persona… nunca al revés», y la persona todavía no existe.
- **Relevo («el gesto no existe en la realidad»):** nadie en un taller tiene a alguien que le acerque el vaso de
  tornillos. No hay fuente de ese gesto.
- **Machero («necesidad prestada de un informe»):** la Directiva 2024/1799 no cubre portátiles, las toneladas de
  residuos son contexto y los anclajes locales no están comprobados. Hoy la necesidad es prestada.
- **LeWelder («el VLA no se veía», tema de MSN):** banco de electrónica ante el mismo operador un mes después.

**Dónde sigue siendo coger y dejar con una historia:** en la tarea puntuada entera. La historia (portátil, registro,
maestro y aprendiz) ocurre alrededor y la sostienen la persona y la tablet.

**Reparto honesto del valor.** Tablet y LLM: hoja de trabajo, registro, traducción de la voz, lectura de la
etiqueta. Persona: toda la reparación. Brazo: llevar 30 cm dos objetos que la persona alcanza.

**Los 3 cambios que más lo alejan del patrón sin subir el riesgo técnico** (el gesto aprendido no cambia):

1. **El estante sale del alcance de la persona sentada.** El brazo queda entre el técnico y el recambio: el almacén
   está al fondo del banco, donde el técnico tendría que levantarse o apartar el equipo. Así «lo cojo yo en 3 s»
   deja de ser verdad física. Coste: geometría de la mesa. Límite: el alcance real del SO-101 se mide el viernes.
2. **Una orden por equipo, no por objeto.** El técnico dice «siguiente equipo»; el LLM lee la hoja (este lleva tal
   módulo) y pide al brazo el vaso y la caja correcta **mientras** la persona saca la batería y abre la trampilla.
   El valor pasa de la velocidad al trabajo en paralelo y a no equivocarse de recambio. Los dos «traer» son los
   mismos; el encadenado es del LLM y va fuera de nota. La tarea puntuada sigue siendo un «traer».
3. **Quitar la mano que repone y decir la verdad sobre la tablet.** En los 5 intentos, quien coloca los objetos es
   el **juez**, donde quiera dentro del estante: deja de ser teatro y pasa a ser una prueba que él controla (lo que
   más premió el jurado simulado). En el pitch: «el registro lo hace la tablet; del brazo medimos una cosa: viajes
   que el técnico no hizo y órdenes cumplidas sin ayuda». La lectura de etiquetas se quita.

Con los tres cambios, U1 y U5 pasan a depender de una medida (apartado 3) y U7 sigue sin resolverse: hay que decírselo
al usuario tal cual y pedirle el «sí» antes de imprimir.

## 3. Prueba del «¿y si quito el robot?»

**El banco sin robot:** alfombrilla magnética (8-10 € según las fichas), la caja del módulo a un palmo y la mano.

| | Sin robot | Con Aprendiz v3 |
|---|---|---|
| Tiempo por cosa acercada | ~3 s (cifra de las fichas) | hasta 25 s |
| Un cambio de memoria (2 «traer» + 2 «guardar») | ~12 s de manos fuera del equipo [aritmética] | ~100 s de brazo; el trabajo de manos que debería solaparse dura segundos (pestillo, dos clips) |
| Errores | Tornillo sobrante o mal puesto (iFixit, Technibble), con 0-3 tornillos en este portátil | Una orden fallida de cada 4-5 [est.]; cada fallo acaba en la mano igualmente |
| Manos fuera del equipo | Alcanza a 30 cm | Alcanza al plato, a 10 cm: el brazo ahorra 20 cm de recorrido |
| Registro | No hay | Lo hace la tablet, y lo haría igual sin brazo |

Lectura honesta: en un cambio de memoria con trampilla, **el robot es más lento, falla más y no ahorra manos**. La
operación elegida (0-3 tornillos, 10 minutos según iFixit) es demasiado corta para que un ayudante lento compense.

**Qué medir, y cuándo.**

- **Jueves, sin robot (gratis):** 5 cambios de memoria seguidos grabados en vídeo. Contar el tiempo total, las veces
  que las manos salen del equipo, lo que se hace mientras tanto y los errores. Es el denominador de todo.
- **Sábado, 30 min de robot:** 5 cambios con el aprendiz, misma persona, alternando el orden con los de sin robot.
  Mismas cuatro cuentas, más segundos de espera al brazo y órdenes que acabaron en la mano.

**Resultados que obligan a cambiar el relato:**

- Si el jueves el cambio completo a mano dura menos que dos viajes del brazo (50 s): la reparación suelta no puede
  ser la demo de valor. Se pasa a tanda con estante lejano (cambios 1 y 2) o a una operación más larga.
- Si el sábado el tiempo con robot es peor **y** la espera al brazo supera el 20 % del total: prohibido decir
  «ayuda». El relato pasa a «prueba de concepto: cuánto cuesta enseñar una referencia nueva», apoyado en datos.
- Si las salidas de manos no bajan al menos a la mitad: se retira «no suelta el equipo» del pitch.
- Si sale mejor en algo, ese número es el titular, y solo ese.

## 4. Los 5 supuestos sin probar

| # | Supuesto | Experimento más barato | Si sale mal |
|---|---|---|---|
| 1 | **SmolVLA obedece a la frase** con los dos objetos en la escena | Sáb. 9:30: 10 pruebas por frase con posiciones permutadas. No se puede adelantar sin robot; sí se puede tener el ACT de cada orden entrenado esa misma noche para comparar | Rama B del apartado 5 a las 10:30, sin esperar a las 20:00. Decir al usuario hoy que en esa rama U2 no se cumple |
| 2 | **La rúbrica es la de Robotekin** y la mano puede entrar en la zona entre intentos | Jueves: llamada o correo a la organización con tres preguntas (rúbrica, material propio, quién repone). Viernes 17:45: al mentor | Demo de 90 s como principal. Jueves: imprimir una rampa de salida para que la mano nunca entre en la zona |
| 3 | **La pinza coge el vaso y la caja y llega al plato** sin estirar del todo | Jueves: apertura de la pinza en el CAD público. Viernes 18:30: 10 agarres por objeto y tamaño | Usar el ancho que salió 10/10; acercar el plato; si la caja no sale, segundo objeto con otra forma impresa |
| 4 | **Tres personas sin experiencia graban 50 episodios buenos en 3 h** | Jueves: teleoperar en el simulador que ya existe para fijar el ritual (quién repone, quién teclea, quién descarta). Viernes: cronometrar los 5 primeros episodios | Si a las 20:00 el ritmo es menor de 20 por hora: una sola orden hasta 50, quedarse a la noche opcional, y la segunda orden el sábado a las 9:30 |
| 5 | **Un técnico real dice que le sirve** | Jueves 10:00-13:00: dos visitas en persona con las 5 preguntas, más una sexta: «¿en qué momento tiene algo en la mano que no puede dejar en la mesa?» | El pitch dice «nos dijeron que estorba, y por eso…» y la utilidad se defiende con la medida del apartado 3 o no se defiende |

## 5. Árbol de planes B y C

Las puertas ya pactadas (vie. 23:00 ≥ 50 episodios; sáb. 12:00 primer modelo; sáb. 20:00 < 5/10) se mantienen. Se
añaden disparadores anteriores, porque el sábado a las 20:00 ya no queda ciclo de entrenamiento útil.

| Hora | Medida | Resultado | Decisión |
|---|---|---|---|
| Vie. 19:30 | 10 agarres por objeto en teleoperación | Caja < 8/10 | Cambiar de ancho o de objeto antes de grabar |
| Vie. 21:00 | Episodios válidos | < 30 | Solo el vaso hasta 50; la caja pasa al sábado |
| Vie. 23:00 | Episodios válidos | < 50 | Rama C directa; por la noche se entrena solo ACT |
| Sáb. 10:30 | Matriz frase × objeto, 10 por frase | ≥ 8/10 en las dos | Rama A |
| | | 6-7/10 | 20 episodios más por orden con posiciones cruzadas y repetir a las 15:00 |
| | | ≤ 5/10 | Rama B ya |
| Sáb. 14:00 | Algún modelo moviendo el robot | Ninguno | Rama C: todo el equipo al ACT del vaso |
| Sáb. 16:00 | Serie de 10 por orden | SmolVLA ≥ 8/10 | Rama A · ACT ≥ 8/10 y SmolVLA < 7/10: rama B · los dos < 6/10: rama C |
| Sáb. 18:00 | — | — | Grabar el vídeo de 1 min con lo mejor que haya. Montaje congelado a las 21:00 |
| Dom. 10:00 | Serie de 5 completa | ≤ 3/5 | Declarar solo las zonas y el objeto que salieron; si ≤ 1/5, rama D |

| Rama | Tarea que se declara | Lo que se cuenta |
|---|---|---|
| **A** · una red lee la frase | «El juez coloca vaso y caja en el estante y nombra uno; el aprendiz lo deja en el plato en menos de 25 s» | Una sola red, dos órdenes, la matriz y la columna del objeto nunca visto |
| **B** · un ACT por orden y el LLM elige | La misma | «Probamos una red que lee la frase: obedeció X de 10. Hoy elige el LLM entre dos especialistas, y esta tabla dice por qué.» El experimento fallido es la historia de datos |
| **C** · solo el vaso | «El juez coloca el vaso en cualquier zona; el aprendiz lo trae» | «Primera semana del aprendiz: sabe una cosa. Esto costó enseñársela (N episodios, de X a Y).» La caja la coge la persona |
| **D** · nada llega a 3/5 | La versión más corta que salga: un objeto y las zonas buenas | Vídeo del mejor intento del sábado, cuaderno de fallos y la medida con y sin robot. Sin promesas |

En todas las ramas existen el vídeo de 1 minuto, el dataset en el Hub y el repositorio (+5).

## 6. Alcance

**Lo que quitaría hoy:**

- Lectura de la etiqueta del módulo: es software nuevo, no es del brazo y no puntúa.
- `Put it away.` como compromiso del sábado por la mañana: 50 episodios que compiten con la prueba de la frase. Solo
  si a las 16:00 se está en la rama A.
- Tercer objeto y cambio de orden a mitad con `/subtask`.
- `dagger` con `lerobot-rollout` (sin probar): se sustituye por demostraciones normales desde donde falló.
- El ciclo 0 como tercer ciclo de SmolVLA; quedan dos, más los ACT, que caben en la GTX 1660.
- Reed, ESP32 y LED: electrónica nueva que no da puntos. El acierto lo cuenta una persona en una hoja.
- Personaje, estética arcade, ranking e integración de la tablet v2 con el servidor real. Una página que muestre
  la orden activa y el contador basta.
- La voz como entrada principal: teclado o botones, y la voz encima si hay red.
- La reparación de 3 minutos en directo: va al vídeo. En la mesa, 5 intentos y el portátil encendiéndose.
- La columna «flexo desplazado», la Directiva y las toneladas de residuos del pitch.

**Lo que no quitaría de ninguna manera:**

- La visita del jueves a un técnico, con foto y frase, y la medida del banco sin robot.
- Los comandos de grabar, entrenar y ejecutar con LeRobot 0.7 escritos y probados en seco el jueves, en dos portátiles.
- Tablero propio con cámaras y flexo fijos, y la foto de referencia de cada cámara.
- El ACT por orden desde el viernes por la noche.
- La matriz frase × objeto y las series de 10 medidas en el robot (el modelo se elige por la tabla).
- Ensayos de la serie de 5 completa con cronómetro desde el sábado a las 18:00.
- Dataset al Hub tras cada tanda, y dormir.
- El portátil real que arranca: es lo único de la mesa que no tendrá nadie más.

## 7. Veredicto

**Probabilidad de podio: 15 % (rango 8-25 %) [est.].** Primer puesto: en torno al 5 %.

Cómo llego: en 2025 hubo más de 20 equipos y este año hay 140 plazas, así que la tasa base de tres premios está
entre el 8 y el 15 %. A favor: preparación, relato de datos y un aparato real. En contra: equipo que no ha tocado un
SO-101, concepto que el jurado simulado coloca en la mitad baja por parecido y por «lo cojo yo», y ninguna
evaluación independiente por encima de 70 (el 71-78 es autoevaluación del finalista).

Los tres factores que más la mueven:

1. **Aciertos del domingo.** De 3/5 a 5/5 hay 12 puntos, más que toda la distancia entre conceptos. Con ≥ 8/10
   medido el sábado a las 16:00, subo al 25-30 %; en rama C, por debajo del 8 %.
2. **Que la frase mande** (sábado 10:30). Decide U2, la dificultad percibida y si hay algo que distinga la mesa.
3. **La respuesta a «lo cojo yo»:** cita real del jueves, estante fuera del alcance y medida con y sin robot. Sin
   las tres, la utilidad se queda en 8-9 de 15 y el usuario tiene motivos para rechazarlo antes del viernes.

**Recomendación:** no construir todavía. Enseñar al usuario esta noche las cuatro grietas y los tres cambios del
apartado 2, decirle que U7 sigue sin cumplirse, y esperar su «sí» explícito.
