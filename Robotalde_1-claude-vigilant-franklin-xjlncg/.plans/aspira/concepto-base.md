# Aspira · concepto base (19-11-2026)

Elegido por el usuario entre los 16 conceptos de la ronda 2 (`.plans/brief2/`). Petición: «trabaja el proyecto
entero, especialmente la parte de diferentes procesos como taladrar o lijar y su gestión del robot para la
aplicación». Este documento es la entrada común de los especialistas.

## La necesidad (las cuatro pruebas)

1. **Se ha vivido:** cualquiera que haya taladrado o lijado en casa o en un taller ha llenado de polvo la mesa, el
   suelo y los pulmones.
2. **Se entiende en una frase:** «Aguántame la aspiradora mientras taladro.»
3. **Hoy se resuelve con un apaño:** otra persona con el tubo de la aspiradora, el pósit doblado bajo la marca, la
   botella cortada, el vaso de plástico, el adaptador «para taladrar solo», la boquilla de Festool. En YouTube hay
   más de 10 apaños distintos, uno con unas 188.000 visitas (`.plans/brief2/videos-aplicaciones-similares.md`).
4. **El robot hace de segunda persona:** con una mano en la taladradora o la lijadora y la otra sujetando la pieza,
   nadie sostiene la boquilla donde nace el polvo.

Evidencia en vídeo: nota 5 de necesidad y **ningún robot que ya lo haga**.

## Decisiones de partida del moderador (los especialistas pueden discutirlas)

1. **Varios procesos, una sola red.** La persona dice qué va a hacer y dónde («voy a taladrar aquí», «voy a lijar
   el borde izquierdo»). El VLA decide qué boquilla usar y dónde colocarla. Ese es el uso del lenguaje: cada proceso
   genera el polvo de una forma distinta y pide una boquilla y una postura distintas.
2. **El robot no carga con la aspiradora.** Solo lleva una boquilla ligera impresa; la manguera va colgada de un
   brazo o pescante con contrapeso, de modo que el SO-101 mueve decenas de gramos, no la manguera.
3. **Cambio de boquilla por proceso** (a decidir): boquilla redonda junto a la broca para taladrar, boquilla plana
   y ancha para lijar, cepillo para cortar. Si el VLA elige la boquilla de un soporte según la frase, la orden
   cambia **qué objeto**, que es lo que mejor hace un VLA.
4. **Tarea puntuada fiable:** objetivos estáticos (taladrar en una marca). Seguir una lijadora que se mueve es más
   difícil (MSN lo resolvió con control visual programado, no aprendido): se decide si entra en la nota o queda fuera.
5. **El valor se mide y se ve:** cartulina negra bajo la pieza; foto del polvo con y sin Aspira, o polvo pesado. Es
   el momento memorable: el jurado ve la mesa limpia.
6. **Seguridad primero:** nada del robot cerca de la broca, el disco o la lijadora en marcha más allá de lo
   necesario; distancias mínimas y parada.

## Restricciones que no cambian

Las de `.plans/brief/directrices.md` (apartados 6 y 7) y `.plans/brief2/directrices-necesidad.md`: SO-101
(carga ~200-300 g, pinza de 2 dedos, ±1 cm, servos que ceden), SmolVLA y ACT con 50-150 demostraciones por orden,
equipo de 3, **hoy jueves 19 es el único día de preparación y el robot llega el viernes**, rúbrica probable de
Robotekin (demo 5 de 5 sin tocar el robot 30 · datos 20 · dificultad 15 · utilidad 15 · innovación 10 ·
presentación 10). Software y planes reutilizables de la ronda anterior: `.plans/brief/especialista-tecnico.md`
(verificado en el código de LeRobot v0.7.0), `.plans/brief/especialista-hardware.md` (alcance del SO-101 calculado en
MuJoCo: coger desde arriba a 120-285 mm del eje) e `.plans/brief/inventario-software.md`.
