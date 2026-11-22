# Directrices para la idea (18-11-2026, noche)

Destilado de toda la investigación del proyecto: análisis de concursos, 37 proyectos de referencia, lecturas de ACT
y VLA, cinco rondas de ideas rechazadas por el usuario, 44 empresas de physical AI y los criterios que el usuario
dio de palabra. **Objetivo: ganar el Hackathon LeRobot Bilbao II (20-22 nov 2026).** Este documento es la única
entrada de los generadores y evaluadores del proceso.

## 1. Lo que el usuario ha pedido (manda sobre todo lo demás)

| # | Directriz | Origen |
|---|---|---|
| U1 | **Valor real**, como el asistente de soldadura de MSN: una ayuda que alguien usaría porque le ayuda. | Palabra del usuario |
| U2 | **Requiere un VLA**: que quitarlo se note. | Palabra del usuario |
| U3 | **Baja probabilidad de fallo.** | Palabra del usuario |
| U4 | **Herramienta real tal cual**, no la miniatura de una aplicación robótica industrial. Lo que se enseña es el producto. | Palabra del usuario |
| U5 | **Asistente: colaboración humano-robot.** La persona trabaja con sus manos y el robot la ayuda. | Palabra del usuario |
| U6 | Ámbito **hobby o industria** (banco de trabajo), no doméstico ni asistencia a personas dependientes. | Palabra del usuario |
| U7 | La demo del hackathon es **la demo de una aplicación de physical AI real**, del tipo que ya venden startups. | Palabra del usuario |

Direcciones que el usuario eligió para profundizar: **tercera mano de taller** y **estudio de fotos de producto**.

## 2. Lo que el usuario ha rechazado y la lección de cada rechazo

| Rechazado | Lección |
|---|---|
| LeWelder (escuela de soldadura; aparcado) | Tema ya ganado por MSN; montaje poco fiable; el VLA no se veía. |
| Relevo (repuestos en una minimáquina) | El gesto no existe en la realidad; un robot no encaja componentes pequeños. |
| Machero (machos en molde): "tema, necesidad y demo, todo" | Proceso oscuro, necesidad prestada de un informe, demo quieta. |
| Coche a la carta, Línea parada, Pila Sabia, Repón, Pulsa: "estamos enfocando mal esto" | Son **maquetas**: partir de "coger y dejar" y ponerle una historia industrial encima no convence. |
| Cinco asistentes de banco (sin respuesta; pidió mirar startups) | Faltaba el anclaje en una aplicación que el mercado ya paga. |

Regla derivada: **se parte de una persona que trabaja con sus manos en un banco real y de una tarea que el mercado
ya paga; el robot se adapta a ellas.** Nunca al revés.

## 3. Lo que hace ganar (hechos de los concursos analizados)

1. **Funciona en vivo de principio a fin** y **se recupera a la vista** (MSN: 4 oclusiones resueltas; el camarero
   improvisó con un fallo). "Es más importante no perder que ganar."
2. **Se entiende en 5 segundos y hay un humano en el centro.** Ganó MSN con 54 episodios; perdieron una celda
   industrial de 692 episodios y un sembrador con 1.600.
3. **Dificultad percibida:** la tarea parece difícil a simple vista.
4. **Una capa de vida** (voz, LLM, personaje) que se puede quitar si falla.
5. **Algo físico propio** que da fiabilidad o sorpresa (pinzas impresas, útil, sensor).
6. **Híbrido:** lo difícil se aprende; la geometría y la orquestación se programan. Ningún ganador hace todo con un
   solo modelo.
7. **Estados visibles en la escena y tasa de aciertos medida y enseñada.**
8. **Los VLA ya ganan** (4 de 8 ganadores con política conocida) y la organización quiere VLA.
9. **Nadie validó la necesidad con usuarios reales.** Una cita, una foto o una carta de alguien real distingue.

**Rúbrica más probable (hallazgo del 18-11):** organiza **Bravo Robots, el mismo operador de Robotekin** (donde ganó
MSN). La rúbrica de Robotekin, anotada por un equipo participante (no es documento oficial; que Bilbao la repita es
una inferencia), es:

| Criterio | Qué se valora | Puntos |
|---|---|---|
| Demo en vivo | **5 intentos seguidos de la tarea completa sin tocar el robot; 6 puntos por acierto** | 30 |
| Datos y entrenamiento | Cantidad, variedad y coherencia de las demostraciones; cámaras y encuadre; cómo se iteró sobre los fallos | 20 |
| Dificultad de la tarea | Ambición realista para 48 h: de coger un objeto a varios pasos que aguantan cambios de posición o de luz | 15 |
| Utilidad e impacto | Que resuelva un problema real | 15 |
| Innovación e ingenio | Originalidad del enfoque y de la solución | 10 |
| Presentación y equipo | Cómo se cuenta y cómo se responde al jurado | 10 |
| Bonus | Dataset en Hugging Face (+3) y repositorio reproducible (+2) | +5 |

Consecuencias:

- **La «tarea completa» la declaramos nosotros y debe salir 5 de 5 sin tocar el robot.** Tiene que ser corta
  (≤ 30-40 s), autónoma de principio a fin y repetible sin recolocar nada a mano dentro del brazo. El rescate humano
  con el brazo guía **resta** en la demo puntuada: puede vivir en el relato de datos («así iteramos»), no en los 5
  intentos.
- **20 puntos son de datos y entrenamiento:** hay que enseñar el dataset, las cámaras, la variedad y **cómo se
  iteró sobre los fallos** (comparativa ACT frente a SmolVLA, tabla X/10 por modelo, ronda de corrección).
- **Jurado de industria, centros tecnológicos y universidad vascos** (en Robotekin: Ikerlan, Automach, EHU,
  Koniker); ningún ingeniero de Hugging Face ni inversor. Ya vieron ganar a MSN y quedarse sin premio a una celda
  industrial de 692 episodios.
- La web de 2026 pide «una tarea de verdad», «modelos VLA», «sin simulación», «el robot trabaja solo, delante de
  todos» y «comparación entre equipos»; el evento se llama ahora **Physical AI Hackathon Bilbao**. Premios: 1.500,
  900 y 600 €, sin categorías.
- Presentaciones de 5 minutos el domingo de 11:30 a 12:30; lo más probable es demo en la propia mesa. Llevar hecho un
  vídeo de 1 minuto. Preguntar el viernes a las 17:45 al mentor: rúbrica, hardware propio y dónde se hace la demo.

Detalle y fuentes en [evento-novedades.md](evento-novedades.md).

## 4. Lo que hace perder

Demo sin terminar · alcance demasiado grande · mover cámaras o cambiar la luz · hardware e infraestructura · modelo
demasiado pesado · elegir el modelo por la pérdida y no probando en el robot · proyecto correcto pero previsible
(clasificadores) · idea original mal ejecutada · necesidad falsa (cubos de colores disfrazados, cifras de mercado
genéricas, un robot que hace lo que una persona hace mejor).

Temas quemados: soldadura con linterna (MSN, 1.º en Vitoria hace un mes), camarero (Bilbao 2025, Zúrich 2026),
voltear paquetes (Flip & Ship, 1.º en París), paletizado (Team Zenith), ajedrez y juegos de mesa.

## 5. Lo que el mercado de physical AI paga hoy (44 empresas revisadas)

1. **Coger y dejar con mucha variedad, eligiendo qué coger según la orden:** kits y pedidos (Ultra con Physical
   Intelligence, Tutor), reposición (Telexistence, Galbot), carga de útiles (Figure en BMW, AgiBot).
2. **Órdenes habladas donde hay muchas variantes:** laboratorio (Medra con Genentech), recetas (Galbot).
3. **Humano en el bucle:** se cobra por hora o suscripción; una persona rescata los fallos; la métrica que convence
   es el **% de autonomía por turno** (Ultra: 96,4 % declarado).
4. **Hueco:** no hay ningún uso productivo documentado de un SO-101. Una demo que copie una tarea vendida sería la
   primera.
5. El aprendizaje se paga por la **variedad** de objetos y los cambios frecuentes, no por la destreza.

## 6. Lo que el SO-101 y los VLA pueden y no pueden (hechos técnicos)

- **Fiable:** coger y dejar objetos de 20-60 mm de ancho y < 300 g, con ±1 cm (embudos, imanes, alojamientos en V);
  sostener algo quieto; llevar algo a una zona. **No:** inserción de precisión, fuerza, roscar, piezas pequeñas o
  metálicas lisas, deformables, líquidos, entregar en la mano o cerca de la cara, seguir trayectorias a ±5 mm.
- **SmolVLA:** 50 episodios por orden (10 en cada una de 5 posiciones); 2 órdenes bien grabadas mejor que 3 a medias;
  frases cortas en inglés que empiezan por verbo; el LLM traduce la voz a la frase fija. **Riesgo conocido:** con la
  misma escena y solo la frase distinta, la red puede ignorar el texto. Mejor que la orden cambie **qué objeto**
  (distinto a la vista) o **adónde**. No tiene memoria: los estados deben verse en la escena.
- **ACT:** 80-96 % con 50 demostraciones; plan B natural (un ACT por orden y el LLM elige).
- **LeRobot 0.7:** `--interactive=true` y `/subtask` cambian la orden sin recargar el modelo; inferencia local con
  `--inference.type=rtc` (SmolVLA ~2 GB) o remota.
- **Entrenar:** SmolVLA en la nube (L4: 3-6 h); ACT cabe en la GTX 1660. Dos ciclos de grabar → entrenar como mucho.
- El servo puede ceder unos milímetros si se le empuja; el brazo extendido tiembla con cargas.

## 7. Restricciones del equipo y del evento

- 48 h (viernes tarde → domingo 11:00), pitch de 5 min y demo en vivo. Equipo de 3: dos de software e IA sin
  experiencia previa con LeRobot real, y Andoni (CAD, impresión 3D, electrónica).
- **No hay robot antes del evento.** Solo queda **el jueves 19** para imprimir y preparar. Tope: ~12 h de impresión,
  electrónica sencilla (ESP32, LED, pulsadores, sensores Hall o reed, imanes ya comprados).
- Material de la organización: un par de SO-101 (guía + seguidor), una cámara, un trípode. Tenemos una segunda
  webcam. Wifi no garantizada: voz e inferencia deben tener respaldo local.
- Software ya hecho y reutilizable: voz → LLM → orden cerrada, tablet con estética arcade y personaje con voz,
  firmware de ESP32, ArUco y visión, flujo de grabar → entrenar → evaluar, scripts de HF Jobs.
- Puertas ya pactadas: viernes 23:00 ≥ 50 episodios; sábado 12:00 primer modelo en el robot; sábado 20:00 si < 5/10,
  el plan B pasa a ser el relato principal.

## 8. Criterios de eliminación (uno basta para descartar un concepto)

1. Es una maqueta de un proceso más grande (U4).
2. Su gesto central necesita inserción a menos de 5 mm, fuerza o piezas que la pinza no coge (U3).
3. Quitar el VLA y poner un script no cambia nada (U2).
4. Se confunde con MSN (luz o linterna para soldar), el camarero o Flip & Ship.
5. La persona solo mira: no hay trabajo real de sus manos (U5).
6. Seguridad: calor, filo o líquido cerca de la persona sin un enclavamiento claro.
7. Necesita más de ~12 h de impresión, electrónica crítica nueva o más de 2 órdenes del VLA para su nivel mínimo.
8. La necesidad solo se sostiene con una cifra de un informe; no hay un usuario al que se pueda llamar o citar.

## 9. Rúbrica de evaluación de conceptos (100 puntos, la de Robotekin)

| Criterio | Puntos | Qué se mira en un concepto |
|---|---|---|
| Demo en vivo: 5 de 5 sin tocar | 30 | Probabilidad realista de 5 aciertos seguidos de la tarea declarada; tolerancia del gesto; que la escena se reponga sola o por la persona sin entrar en el brazo; plan B con ACT |
| Datos y entrenamiento | 20 | Qué historia de datos permite contar: variedad, cámaras, comparativa de modelos, iteración sobre fallos; episodios que caben en 48 h |
| Dificultad de la tarea | 15 | Varios pasos, cambios de posición, elegir por lenguaje; que un jurado de automatización no diga «eso es un script» |
| Utilidad e impacto | 15 | Usuario real, herramienta tal cual (U1, U4, U5), referencia de mercado; lo usaría alguien el lunes |
| Innovación e ingenio | 10 | Enfoque no visto en hackathons de LeRobot; algo físico propio |
| Presentación y equipo | 10 | Se entiende en 5 s, juez en el centro, momento memorable, pitch en una frase |

Los criterios del usuario (apartado 1) son condición previa: un concepto que incumpla U1-U7 no se puntúa.

## 10. Formato de la ficha de concepto

1. **Nombre y frase** (el pitch en una línea).
2. **Usuario real y su trabajo** (quién, qué hace con las manos, qué le estorba hoy; queja o cita con fuente si existe).
3. **Reparto:** qué hace la persona / qué hace el robot.
4. **Referencia de physical AI real:** qué empresa vende algo así, a quién, con qué métrica.
5. **La escena tal cual:** objetos reales (tamaño, peso, cuántos), qué se imprime, cámaras.
6. **Órdenes del VLA:** 2 para el nivel mínimo y 1-2 extra; qué cambia entre ellas; por qué un script no vale.
7. **Guion de 3 minutos con el juez:** paso a paso, momento memorable y recuperación planificada.
8. **Escalera de alcance:** N1 (sábado 12:00), N2 (sábado 20:00), N3 (domingo, si sobra).
9. **Fiabilidad:** el gesto más difícil y su tolerancia; plan B; qué se ve si el VLA falla.
10. **Preparación del jueves:** horas de impresión, electrónica, software que se reutiliza.
11. **Puntos débiles honestos** y parecidos con proyectos existentes.
12. **Autoevaluación** con la rúbrica del apartado 9.
