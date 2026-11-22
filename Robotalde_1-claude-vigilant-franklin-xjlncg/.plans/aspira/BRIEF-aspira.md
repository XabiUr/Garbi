# Brief · Aspira

**Robotalde · Physical AI Hackathon Bilbao II (20-22 de noviembre de 2026, La Perrera)** · versión 1.1 · 19-11-2026 (con las decisiones del usuario)
Concepto elegido y acotado con el usuario; adaptado tras tres evaluaciones independientes: jurado simulado
([jurado-simulado.md](jurado-simulado.md)), equipo rojo técnico ([equipo-rojo-v2.md](equipo-rojo-v2.md)) y
diferenciación ([diferenciacion.md](diferenciacion.md)). Base: [concepto-v2.md](concepto-v2.md),
[tecnicas.md](tecnicas.md), [procesos.md](procesos.md), [hardware.md](hardware.md).

Marcas: [H] leído en la fuente · [H·b] extracto del buscador · [est.] estimación sin medir · [medir] pendiente.
Ninguna tasa de acierto está medida: el robot llega el viernes.

---

## 0. Resumen

1. **Qué es.** Un compañero de escritorio para quien trabaja madera pequeña y maquetas: mientras taladras, aguanta
   la boca de la aspiradora; la aspiradora se enciende sola; cuando retiras el taladro, limpia el agujero nuevo aunque
   hayas movido la tabla, y limpia lo que le pidas.
2. **Necesidad evidente.** Todo el que ha taladrado ha llenado la mesa de polvo. Hoy: otra persona con el tubo, el
   pósit doblado, la botella cortada (más de 10 apaños en YouTube, uno con ~188.000 visitas [H·b]). La aspiración
   solo capta con la boca cerca: a un diámetro de distancia ya capta menos del 10 % [H].
3. **El VLA hace la limpieza:** una sola red que, según la frase, limpia el agujero nuevo o la viruta de la
   alfombrilla, esté donde esté. Lo programado (rápido y seguro) acerca la boca al taladro, congela el brazo y maneja
   la aspiradora.
4. **Tarea puntuada:** el juez taladra y mueve la tabla donde quiera; Aspira limpia el agujero nuevo en menos de
   30 s. Éxito medido por foto.
5. **Análisis para ganar:** jurado simulado 63/100 con el concepto anterior; ~75-80 con las adaptaciones [est.].
   Podio 20-30 % [est.].
6. **Decisiones que necesito del usuario:** apartado 11.

## 1. Análisis para ganar: lo que dijeron las tres evaluaciones

**Jurado simulado (4 perfiles como los de Robotekin): media 63/100** con una demo realista de 3 aciertos de 5.

| | Hallazgo | Fuente |
|---|---|---|
| Fuerte | Necesidad evidente, hueco real (ningún robot lo hace), compañero que reacciona, resultado visible, material propio | Las tres |
| Fuerte | El VLA **se nota** cuando el juez tira serrín y el robot va a por él: la versión programada no sabe ir allí | Jurado |
| Débil | El VLA **no se nota** en el agujero si la viruta clara cae sobre madera clara: no se ve qué mira la red | Jurado y rojo |
| Débil | La fase de acompañar **es la demo de MSN** (seguir la punta de una herramienta esquivando la mano) | Diferenciación |
| Grave | **El micrófono solo oye la aspiradora** en cuanto arranca: no detecta cuándo para el taladro y la regla de seguridad se queda sin sensor | Rojo |
| Grave | Seguimiento programado y VLA dentro de `lerobot-rollout` **no pueden tener el puerto del robot a la vez** | Rojo |
| Débil | Con 60-100 episodios el viernes [est.], **cuatro órdenes del VLA son demasiadas** | Rojo |
| Débil | **Seguir un taladro que se mueve** con 0,2-0,3 s de latencia [est.] no es seguro ni fluido | Rojo |
| Débil | El cero del robot real no coincide con el del modelo: 3° de error son ~13 mm [est.] | Rojo |

**Los cinco cambios que más suben la nota según el jurado (de ~63 a ~80 [est.]):** tarea puntuada corta y ensayada
hasta ≥ 4/5 (+7) · resultado visible con tabla oscura y antes/después (+3) · VLA frente a la versión programada en vivo,
quitando las órdenes por debajo de 7/10 (+3) · diapositiva de datos de 30 s y dataset y repositorio publicados (+3 y
+5 de bonus) · una primera frase que responda a «es la linterna de MSN» y a «basta con un adaptador de 20 €» (+3).

## 2. Adaptaciones (qué cambia respecto al concepto v2)

| # | Cambio | Por qué |
|---|---|---|
| 1 | **Sin acelerómetro (decisión del usuario).** La seguridad y la aspiradora dependen del **estado y de la visión**, no del sonido: el robot se congela desde que se coloca hasta que el taladro sale de la zona; la aspiradora está encendida mientras el robot está colocado o limpiando, y 2 s más. El sonido (Arduino con micrófono, filtrado) queda como efecto opcional para encender antes | El micrófono se queda sordo cuando arranca la aspiradora; así la regla de seguridad no depende de oír |
| 2 | **Un solo proceso dueño del robot** (`aspira/robot_vivo.py`, bucle a 30 Hz): visión, IK programada y el VLA en el mismo programa con `robot/politica.py`. Plan B: `lerobot-rollout --interactive` para el N1 | El puerto serie no se comparte; cambiar de habilidad debe costar 0 s |
| 3 | **Dos órdenes del VLA, no cuatro:** `Clean around the new hole.` y `Clean the chips on the mat.` | Destinos distintos a la vista y datos que caben en 48 h |
| 4 | **Contraste:** vinilo negro mate en la cara de la tabla y alfombrilla de corte **azul** (decisión del usuario) | La viruta clara sobre negro se ve: la red y el jurado ven lo mismo |
| 5 | **Agujero nuevo por diferencia de imagen** (mancha nueva sobre negro, en coordenadas de la tabla) y **pose de la tabla con 2 ArUco** | No depende del marcador del taladro ni del contorno con maquetas encima |
| 6 | **Acercarse a un taladro quieto** (a ≤ 5 cm/s), no seguirlo mientras se mueve: cuando paras el taladro sobre el punto, se coloca | Seguro y fluido con la latencia real; y se separa de la demo de MSN |
| 7 | **Abrir la demo con la limpieza**, no con el acompañamiento | La parte aprendida es lo vistoso; diferencia con MSN en 30 s |
| 8 | **Aspiradora con enchufe comercial** (433 MHz o Shelly) y latido: si el Arduino calla 1 s, el robot se congela y la aspiradora se apaga | Nada de relés sueltos a 230 V |
| 9 | **Corrección con 9 puntos de la alfombrilla** y patines de fieltro en la boca | Error del cero del robot real |
| 10 | Lijado con taco, «Wait by my side», cambio de cabezal y seguir el taco: **N3 o solo en el pitch** | Tiempo y riesgo |

## 3. La aplicación

**Persona:** quien trabaja madera pequeña o maquetas en su mesa (aficionado, profesor de tecnología de instituto o
alguien del equipo con su historia real).

**El ciclo de trabajo:**

| Fase | La persona | Aspira | Técnica |
|---|---|---|---|
| Reposo | — | Aparcado; aspiradora apagada | Programada |
| Acercarse (N2) | Para el taladro sobre el punto | Lleva la boca a ~35 mm de la punta, en el lado libre, a ≤ 5 cm/s | Programada (marcador en el taladro + IK) |
| Taladrar | Taladra | Congelado desde que se colocó; la aspiradora se encendió al colocarse | Programada (estado + Arduino) |
| Acabar | Retira el taladro | Cuando la cámara ve que el taladro sale de la zona, aspira 2 s más | Programada (visión) |
| **Limpiar el agujero** | Puede mover la tabla | Va a la mancha nueva y la limpia | **Aprendida (VLA)** |
| Comprobar | — | ¿Queda mancha? Otra pasada (reintento visible) | Clásica (color) |
| Aparcar | — | Vuelve; aspiradora apagada | Programada |
| **Limpiar la alfombrilla** (a petición) | «Se me ha caído serrín» | Va a la viruta fuera de la tabla y la limpia | **Aprendida (VLA)** |
| Limpiar la tabla entera (a petición) | «Limpia la tabla» | Zigzag sobre la tabla | Programada |

**Seguridad:** el robot no se mueve mientras el taladro está en la zona de trabajo (visión) y se acerca solo a un taladro quieto; límite de paso por servo; boca con
fieltro; parada por aparcado, nunca quitando el par (el brazo caería); gafas para quien taladra.

## 4. El VLA, visible

- **Pantalla siempre:** lo que dijo el juez, la frase en inglés que entra a la red, las dos cámaras y X/10 por orden.
- **Prueba en vivo:** el juez mueve la tabla y tira serrín donde quiera; la misma red limpia el agujero o la
  alfombrilla según la frase. Al lado, la **línea base programada declarada** (detector de color + IK): se mide
  cuándo acierta cada una (honestidad: la línea base no es «solo memoria», también ve el color).
- **Datos en 30 s:** matriz frase × destino, VLA frente a línea base y un ACT por orden, y la lista «fallo → qué
  cambiamos → antes → después».
- **Si la red cruza órdenes** (≤ 6/10 en la matriz): un ACT por orden cargados a la vez en el proceso propio
  (cambiar = 0 s) y se cuenta así, sin decir «una sola red».

## 5. La demo

**Tarea declarada para los 5 intentos:** «el juez taladra un agujero (ráfaga de 3 s) y mueve la tabla donde quiera;
Aspira limpia el agujero nuevo en menos de 30 s sin que nadie lo toque. Éxito: la mancha beige baja al menos un 80 %
en la foto de antes y después.» La limpieza de la alfombrilla, como sexto intento solo si la matriz da ≥ 8/10.

**Primeros 30 segundos (diferencia con MSN):** suena el taladro y la aspiradora arranca sola; el juez mueve la tabla;
Aspira limpia el agujero nuevo. Frase: **«En Vitoria ganó un robot que aprendió a coger una linterna. El nuestro
aprendió a limpiar, y le puedes decir qué.»** No usar «tercera mano».

**Frase de pitch:** «Aspira: te aguanta la aspiradora mientras taladras y limpia lo que le pidas, donde esté.»

**Momento memorable:** el juez mueve la tabla o tira serrín y el robot lo arregla. Cierre: tabla con una mitad
taladrada sin Aspira y otra con Aspira, con la viruta pesada o medida en píxeles.

**Respuestas preparadas:** «basta con un adaptador de 20 €» → el adaptador va en la broca y no limpia después ni lo
que cae fuera; se enseña la medida con ambos. «Es la linterna de MSN» → la frase de arriba.

## 6. Arquitectura de software

```
tablet / voz ──► aspira/servidor.py ──cola──► aspira/robot_vivo.py (UN proceso, bucle 30 Hz)
                                               · SO101Follower (puerto del brazo) + cámaras top y wrist
                                               · visión: pose de la tabla (2 ArUco), mancha nueva, marcador del taladro
                                               · estados: APARCADO · ACERCARSE · CONGELADO · VLA(frase) · ZIGZAG · APARCAR
                                               · VLA: robot/politica.py (síncrono); IK con corrección de 9 puntos
Arduino (otro puerto) ◄──► aspira/arduino.py: enchufe de la aspiradora, latido (micrófono opcional)
```

Verificado en el código de LeRobot v0.7.0: `robot/politica.py` repite la inferencia de `SyncInferenceEngine` con la
normalización del preprocesador; falta hacer configurable el `rename_map` (`top`/`wrist` → `camera1`/`camera2`).

## 7. Datos y entrenamiento

| Tanda | Cuándo | Orden | Episodios [est.] | Cómo |
|---|---|---|---|---|
| 1 | Vie 19:30-22:30 | `Clean around the new hole.` | 50-60 | Teleoperación; tablas con agujeros ya hechos y **viruta guardada de hoy** sobre uno distinto cada vez; tabla en 5 poses × giro; maquetas en 1 de cada 3 |
| C0 | Vie 23:00 * | — | — | SmolVLA en HF Jobs + ACT del agujero en la GTX 1660 |
| 2 | Sáb 9:30-10:30 | recolector programado (si va) o teleoperación | 30-60 | Aspiradora apagada (si no, se come la viruta) |
| 3 | Sáb 10:30-12:00 | `Clean the chips on the mat.` | 40 | Viruta en 5 zonas de la alfombrilla, tabla siempre puesta |
| C1 | Sáb 12:15 | fusión | — | SmolVLA multitarea, listo ~15:00; matriz a las 15:30 |

Nunca se graba con el taladro girando. El modelo se elige por X/10 en el robot, nunca por la pérdida. * = solo si
la organización permite la noche.

## 8. Hardware

Material del usuario: aspiradora, taladro a batería, tablas, manguera corrugada flexible. **Imprimir hoy:** mango
atornillado a la pinza con la boca (fieltro en la base), soporte rígido de la cámara fija, soporte de la cámara de
muñeca (STL en `assets/so101/assets/`), pieza para colgar la manguera. **Comprar o traer:** vinilo negro mate,
alfombrilla de corte verde, marcador ArUco y bola de color para el taladro, enchufe de 433 MHz o Shelly, báscula de 0,01 g, gafas. **Pruebas físicas hoy:** foto desde 600 mm de un montón de viruta sobre vinilo negro
(¿se ve?); la cámara detecta que el taladro entra y sale de la zona; captación de la boca a
25, 35 y 50 mm.

## 9. Plan

**Hoy jueves (dos personas de software, ~14 h + margen; Andoni, hardware):** `robot_vivo.py` con robot simulado (3 h)
· adaptador y `rename_map` con un SmolVLA público (1,5 h) · visión: tabla, mancha nueva y viruta (2,5 h) · IK con
corrección de 9 puntos y zigzag en MuJoCo (2,5 h) · Arduino con enchufe y latido (1 h) · comandos de LeRobot
y ensayo de la nube (2 h) · pantalla (1 h). Correo a la organización (taladro, aspiradora, superficie, formato de la
demo, material propio). Guardar la viruta de los agujeros de prueba para grabar el viernes.

**Viernes:** 18:00-19:00 calibrar, cámaras y corrección de 9 puntos · 19:00-19:30 teleoperación libre · 19:30-22:30
tanda 1; en paralelo, `robot_vivo.py` con el robot (aparcar, zigzag, congelado mientras el taladro está en la zona).

**Sábado:** 9:00 C0 en `robot_vivo.py` o en el plan B · tandas 2 y 3 · 12:00 **N1: limpiar el agujero con el VLA y
aspiradora encendida por el estado del robot** · 15:30 matriz · tarde: acercarse al taladro quieto (N2) solo si N1 ≥ 7/10 · ensayos de la
serie de 5 · vídeo de 1 minuto · 21:00 montaje congelado.

**Domingo:** 10:00 serie de 5 · 11:00 entrega (dataset y modelo en el Hub, repositorio reproducible, vídeo, cinco
diapositivas).

**Ramas:** A (SmolVLA lee la frase, ≥ 8/10) · B (un ACT por orden en el mismo proceso) · C (solo el agujero) · D (lo
programado y el vídeo, y se dice).

## 10. Riesgos principales

| Riesgo | Comprobación | Si sale mal |
|---|---|---|
| La viruta no se ve desde la cámara fija | Foto de hoy sobre vinilo negro | La cámara de muñeca guía la pasada; montón más grande (broca mayor) |
| La organización no deja taladrar | Correo hoy | Viruta guardada que echa el juez; taladro solo en el vídeo |
| `robot_vivo.py` no mueve el robot el sábado 9:00 | Prueba del viernes | Plan B con `lerobot-rollout --interactive` |
| La red cruza las dos órdenes | Matriz del sábado 15:30 | Un ACT por orden |
| Error de calibración del brazo real | Corrección de 9 puntos el viernes | Patines de fieltro y boca más ancha |

## 11. Decisiones del usuario (19-11-2026)

1. **Acelerómetro: no.** Se resuelve con estado y visión (adaptación 1).
2. **Acercarse a un taladro quieto** (no seguirlo en movimiento): **sí**.
3. **Lijado con taco al nivel 3:** sí.
4. **Vinilo negro en la tabla:** sí; **alfombrilla azul**.
5. **Nombre:** pendiente de aclarar («sí»: ¿Aspira o Garbi?).
