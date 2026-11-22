# Aspira · qué técnica para cada punto (19-11-2026, borrador para discutir)

Principio: **cada tarea con la técnica que la hace mejor.** Geometría exacta y repetible → programada. Aspecto que
cambia (viruta, herramienta, mano) → aprendida. Lo programado alimenta y vigila a lo aprendido.

## 1. Percepción (la base de todo)

| Qué | Cómo | Técnica | Para qué |
|---|---|---|---|
| **Alfombrilla de trabajo** | Alfombrilla oscura con 4 ArUco en las esquinas | Visión clásica (código ya hecho: `lewelder/seguimiento.py`) | Sistema de coordenadas fijo mesa ↔ robot ↔ cámara; calibración en 1 minuto si algo se mueve |
| **Tabla** | Contorno de la madera clara sobre la alfombrilla oscura → tamaño, posición y giro | Visión clásica (umbral + contorno) | Saber dónde está la tabla aunque la muevan; limpiar la tabla entera |
| **Taladro y punta de la broca** | Banda de color o ArUco en el cuerpo del taladro; desplazamiento hasta la punta calibrado una vez por broca | Visión clásica | Acompañar sin chocar, 20-30 veces por segundo |
| **Sonido del taladro** | Micrófono (Arduino o portátil), umbral calibrado en la sala | Señal | Congelar el robot, encender y apagar la aspiradora, marcar el instante del agujero |
| **Punto del agujero** | Posición de la punta en el instante en que suena el taladro, **guardada en coordenadas de la tabla** | Programada (memoria) | Saber cuál es el agujero nuevo aunque haya muchos y aunque muevan la tabla |
| **Viruta** | Manchas claras sobre lo oscuro alrededor del agujero | Aprendida (lo ve el VLA) + clásica para comprobar | Limpiar donde de verdad hay viruta; comprobar que quedó limpio |
| **Herramienta en la mano** | Taladro, taco o destornillador | Aprendida (VLA) | Qué comportamiento toca sin decir nada |

### Muchos agujeros ya hechos
No hace falta distinguirlos por la imagen: **el agujero nuevo es el que se acaba de taladrar**, y su posición quedó
guardada en coordenadas de la tabla en el instante del sonido. Si la tabla se mueve, su contorno da la nueva pose y
el punto se transforma. Además, los agujeros viejos ya están limpios: **la viruta solo está alrededor del nuevo**, y
eso es lo que ve el VLA. Dos pruebas independientes (memoria y viruta) que se confirman entre sí.

### Detectar la broca sin entrenar nada
El marcador en el taladro evita entrenar un detector. Si se quiere quitar después: **autoetiquetado**. Durante la
grabación, el marcador da la posición exacta de la punta en cada imagen; con esas etiquetas gratis se entrena un
detector pequeño que luego funciona sin marcador. Es un paso de después del hackathon, contado en el pitch.

## 2. Comportamiento por fase

| Fase | Técnica | Detalle |
|---|---|---|
| Reposo | Programada | Aparcado; aspiradora apagada |
| **Acompañar** (taladro callado y dentro de la zona) | **Programada**: control visual | Boca a 35 mm de la punta, en el lado libre (lejos de la mano: se ve por el lado del taladro por el que entra), velocidad limitada; si el taladro se acerca demasiado, se aparta |
| Congelar (taladro suena) | Programada | El robot no se mueve; aspiradora encendida; se guarda el punto del agujero |
| Esperar retirada | Programada | Aspiradora 2 s más; espera a que el taladro salga de la zona |
| **Limpiar el agujero** | **Aprendida (VLA)** | Ir a la viruta del agujero nuevo, esté donde esté la tabla, y hacer la pasada que pide el montón |
| Comprobar | Clásica | ¿Quedan manchas claras en la zona? Si sí, otra pasada (reintento visible) |
| Limpiar la tabla entera (a petición: «limpia la tabla») | **Programada**: recorrido en zigzag sobre el contorno | Cubre la tabla completa a 1 cm de altura |
| Lijar con taco | Aprendida (reconocer el taco) + programada (ponerse en el canto por donde cae) | Mismo ciclo |
| Voz | Programada | «Ven», «retírate», «más cerca», «al otro lado», «limpia la tabla» mandan sobre el ciclo |

## 3. Cómo se entrena el VLA de limpieza de forma inteligente

| Opción | Cómo | Ventaja | Riesgo |
|---|---|---|---|
| a. Solo teleoperación | 60-80 demostraciones limpiando agujeros reales en tablas en posiciones distintas | Movimientos humanos naturales | Lento de grabar; menos variedad |
| **b. Recolector programado + teleoperación** (recomendada) | El limpiador programado (memoria + contorno + recorrido) **graba sus propios episodios** sobre agujeros reales; se completan con 20-30 teleoperados, que enseñan a recuperarse | Cientos de episodios sin cansar a nadie; el VLA aprende a hacerlo **solo con imágenes**, sin marcador ni memoria | El programado no enseña a recuperarse (por eso se mezcla con teleoperación) |

Lo que aporta el VLA frente al programado, y se mide: funciona **sin memoria ni marcador** (por ejemplo, si se reinicia
el sistema, si alguien taladra a mano sin el taladro marcado, o con varios montones de viruta), y adapta la pasada a
cómo ha caído la viruta. Línea base programada y VLA, medidos uno al lado del otro.

## 4. Tarea puntuada (5 intentos)

«Retiro el taladro, el juez mueve la tabla donde quiera y el robot limpia la viruta del agujero nuevo en menos de 30 s,
sin que nadie lo toque.» Cada intento es un agujero nuevo en otra zona de la tabla, así que la escena se repone sola.

## 5. Puntos abiertos

1. Contraste: alfombrilla oscura + madera clara (la viruta cae alrededor sobre lo oscuro), o tabla tintada.
2. Marcador del taladro: banda de color (más simple) o ArUco (pose completa).
3. Micrófono en el Arduino o en el portátil; relé en caja o enchufe con relé para la aspiradora.
4. Altura y forma de la boca para limpiar (a 5-10 mm de la madera sin tocarla).
5. Si la cámara de muñeca ve la viruta de cerca en la pasada (mejor precisión del VLA).
6. Zona de trabajo: tamaño de la alfombrilla dentro del alcance (120-285 mm del eje en la banda útil).

## 6. El papel del VLA, revisado (el usuario no lo veía claro)

**Idea:** el VLA es el **cuerpo que entiende frases**. Todas las acciones de aspirar y limpiar son una sola red que
recibe una frase y las cámaras. Las frases las pone el ciclo automático (después de taladrar, «limpia el agujero
nuevo») o las dice el juez con sus palabras, y el LLM las traduce. Lo programado queda para lo que tiene que ser
rápido o seguro: acompañar el taladro, congelarse, la aspiradora, la memoria y la parada.

**Habilidades de la red (una frase cada una; destinos que se distinguen a la vista):**

| Frase fija | Qué hace | Cuándo |
|---|---|---|
| `Clean around the new hole.` | Pasada sobre la viruta alrededor del agujero, esté donde esté la tabla | Automática al retirar el taladro (y puntuada) |
| `Clean the chips on the mat.` | Va a la viruta caída en la alfombrilla, fuera de la tabla | El juez: «se me ha caído serrín en la alfombrilla» |
| `Clean along the edge.` | Pasada a lo largo del canto lijado | Automática al retirar el taco, o por voz |
| `Wait by my side.` | Se coloca junto a la zona de trabajo, sin estorbar | «Quédate cerca» |

**Cómo se ve que usa el VLA:**
1. En pantalla, siempre: lo que dijo el juez en castellano, la frase en inglés que entra a la red, y las dos cámaras.
   «Una sola red, cuatro órdenes.»
2. **El juez manda con sus palabras** y el mismo modelo hace cosas distintas: el agujero, la alfombrilla, el canto.
3. **El juez desordena:** mueve la tabla, tira serrín donde quiera, cambia de tabla o de maqueta. Nadie reprograma
   nada.
4. **Línea base al lado:** el limpiador programado solo sabe ir al punto guardado en memoria; cuando el juez pide «la
   alfombrilla» o cambia la escena, no sabe. La red sí. Se mide en una tabla.
5. **Matriz frase × destino** (X/10) y comparativa con un ACT por orden: prueba de que la red lee la frase.

**Riesgo conocido:** con la misma escena y solo la frase distinta, SmolVLA puede ignorar el texto. Por eso los
destinos se eligen distintos a la vista (montón alrededor de un agujero, viruta suelta en la alfombrilla oscura,
canto de la tabla) y se mide el sábado a primera hora; plan B: un ACT por frase y el LLM elige.
