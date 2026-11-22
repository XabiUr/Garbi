# Garbi · montaje de la boquilla y «apunto» a la broca (19-11)

## Lo que pide el usuario

- Boquilla atornillada al robot.
- Mientras se taladra, la boquilla aspira casi en horizontal, inclinada unos **30°**.
- Para limpiar, la boquilla va a **90°** (vertical).
- La posición de la broca se encuentra «como el apunto de MSN»: la cámara de arriba más una cámara horizontal en el
  robot que mira a la broca.

## Por qué hace falta la cámara horizontal

Ahora la punta se deduce de la bola naranja suponiendo el taladro vertical. La bola está 230 mm por encima de la punta,
así que con el taladro inclinado 5° la estimación se va unos 20 mm. La cámara del robot ve la broca directamente y
saca su punta en el plano de la tabla, sin depender de la inclinación del taladro.

## Alcance del SO-101 (MuJoCo, IK de 5 articulaciones con giro de muñeca)

Se probaron 15 puntos de la zona de trabajo (radio 130-240 mm, ±30°) y 8 direcciones de llegada alrededor de la
broca.

1. **Boquilla en línea con la pinza (montaje 0°):**
   - 30° sí sale en toda la zona, pero solo con la boquilla mirando **hacia el robot o de lado**.
   - Mirando **hacia fuera** (entre el robot y la broca) es imposible: la broca tendría que estar a más de 260 mm.
2. **Limpieza a 90° a 7 mm de la superficie:** como mucho 6 de 15 puntos, con cualquier montaje probado (0-90°) y
   largo de 45 o 60 mm. El tope de la muñeca (±95°) lo impide en el centro y en los bordes de la zona.

| Montaje (largo 45 mm) | 30° de lado | Limpiar a 90° | a 75° | a 60° |
|---|---|---|---|---|
| 20° | 15/15 | 6/15 | 9/15 | 15/15 |
| **25°** | **15/15** | 6/15 | **12/15** | **15/15** |

## Propuesta (pendiente de decisión del usuario)

**Boquilla y montaje:**
- Boquilla de 45 mm, atornillada a la pinza con un **codo de 25°**.
- **Al taladrar:** la boquilla, a 30°, llega a la broca **por un costado**. El lado lo elige Garbi según dónde alcanza
  mejor, y «otro lado» lo cambia.
- **Al limpiar:** a **75°** donde se alcanza y a 60° en el resto, siempre a la altura de limpieza.

**Apunto:**
1. La cámara de arriba da la posición aproximada con la bola.
2. Garbi se coloca a unos 60 mm de la broca, de lado.
3. La cámara del robot, montada junto a la boquilla, queda horizontal en esa postura y mira a la broca. Detecta la
   broca, cuyo punto más bajo es la punta sobre la tabla, y corrige la posición.
4. Garbi se queda quieto a 35 mm mientras se taladra.

## Limpiar también a 30° (idea del usuario, 19-11)

Centro de la boca a 18 mm sobre la superficie (borde de abajo a ~3 mm), boquilla en línea con la pinza (sin codo),
largo de 45 mm:

| Dónde | Alguna dirección | Mirando hacia el robot | En diagonal hacia el robot (izq / der) | De lado (izq / der) | Mirando hacia fuera |
|---|---|---|---|---|---|
| Tabla (15 puntos) | 15/15 | 15/15 | 15/15 · 15/15 | 10/15 · 10/15 | 0/15 |
| Alfombrilla (12 puntos) | 12/12 | 12/12 | 12/12 · 12/12 | 6/12 · 6/12 | 0/12 |

**Conclusión:** limpiar a 30° funciona en toda la zona, sin codo y sin cambiar de postura entre acompañar y limpiar.
La dirección buena es **en diagonal hacia el robot**: la boquilla queda al otro lado de la broca, mirando hacia el
robot, desviada a la izquierda o a la derecha. Ese lado lo elige Garbi y lo cambia la orden «otro lado».

La cámara del robot, montada en el soporte de la boquilla, ve el agujero de lado tanto al acompañar como al limpiar.
Así el agujero se ve siempre desde dos ángulos: la cámara de arriba y la del robot.

## Diseño final aplicado en la simulación (19-11)

Al construirlo en la simulación aparecieron dos problemas que cambiaron el diseño:

1. **Choque con el taladro.** Con la boquilla de 45 mm, la muñeca y la pinza quedaban encima de la broca, dentro del
   cuerpo del taladro (14-32 mm de interferencia). En el SO-101, la dirección de las mordazas no coincide con el eje
   largo de la pinza.
2. **Alcance del preapunto.** Retroceder a lo largo del eje de la boca la saca del alcance en el borde de la zona, y
   subir acerca el brazo al cuerpo del taladro.

Diseño resultante:
- **Boquilla recta de 110 mm**, atornillada en la dirección de las mordazas. Siempre a **30°** bajo la horizontal, al
  acompañar y al limpiar.
- **Llegada de lado**, con la boca mirando 110° respecto a la radial del robot. Hay holgura de 18-22 mm con el cuerpo
  del taladro en toda la zona. Garbi elige el lado según la holgura de toda la trayectoria (mínimo 12 mm) y «otro
  lado» lo cambia.
- **Aparcado alto y recogido**, con la boquilla hacia arriba, por encima del taladro: no invade la zona.
- **Cámara del robot a un costado del tubo**, a 50 mm de su eje y 20 mm por detrás de la boca, mirando la broca casi
  en horizontal. Encima del tubo quedaba dentro del taladro y el borde de la boca le tapaba la punta.
- **Apunto en tres pasos:**
  1. La cámara de arriba da la posición aproximada con la bola naranja.
  2. Garbi va a un punto de espera de lado y entra en horizontal hasta el preapunto, 20 mm más alto y 30 mm más atrás
     que el sitio de acompañar (holgura ≥ 27 mm).
  3. La cámara del robot ve la broca; su extremo de abajo, proyectado en el plano de la tabla, da la punta. Garbi baja
     hasta acompañar.

  Si no ve la broca, la mira desde el otro lado. Si sigue sin verla, no se acerca a ciegas y pide enderezar el taladro.
- **Zona del taladro:** radio de 120 a 220 mm. Limpiar llega a 240 mm.

Resultados con visión (escenario completo, 6 semillas por caso):

| Caso | Error de la cámara de arriba | Error tras el apunto | Boca-broca en planta | Viruta del agujero | Alfombrilla |
|---|---|---|---|---|---|
| Taladro vertical | 2-11 mm | 1,0-1,7 mm | 33,2-34,0 mm (objetivo 34,6) | 36 → 2-9 al taladrar → 0 | 25 → 0 |
| Taladro inclinado 8° | 32-36 mm | 1,1-1,8 mm | 33,2-34,7 mm, en 5/6 | ídem, en 5/6 | 25 → 0 |

En el caso que falla con 8°, la estimación de arriba cae fuera del alcance (227 mm) y Garbi avisa sin acercarse. Con
15° de inclinación, Garbi no se acerca o pide enderezar el taladro, que es lo seguro.

Mientras se taladra, la boquilla a 30° ya aspira la mayor parte de la viruta (de 36 virutas quedan 2-9).
