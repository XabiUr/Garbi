# Conceptos G2 · lente «trasplantar tal cual una aplicación de physical AI que ya se vende»

Fecha: 18-11-2026. Entrada única: `directrices.md`. Referencias de mercado tomadas de
`../necesidad/startups-eeuu-asia.md` (EA) y `../necesidad/startups-europa-abiertos.md` (EU); sus cifras son casi
todas declaradas por la empresa y vistas en extracto de buscador. Todo lo que no sale de ahí va marcado
**[sin fuente]** o **[estimación]**. Ningún gesto se ha probado en un SO-101: no hay robot antes del evento.

**Descartados por los criterios de eliminación antes de escribir:** clasificar devoluciones (Sereact; proyecto
previsible, «clasificador»); carga de útil de test o flasheo de placas (AgiBot; inserción < 5 mm y electrónica
crítica nueva, crit. 2 y 7); carga de útil en banco de soldadura (Figure; calor y parecido con MSN, crit. 4 y 6);
reposición de bebidas (Telexistence; peso, y la persona solo mira, crit. 5); esquejes de tallo fino en taco
(Robovision; tallo < 20 mm e inserción, crit. 2) → sustituido por rosetas posadas (concepto 3).

---

## Concepto 1 · PEDIDO LISTO

1. **Frase.** «Lo mismo que Ultra vende a Highline Commerce, en un brazo de 300 € y en la mesa de envíos de una
   artesana: el robot reúne el pedido mientras ella monta la caja, y la pantalla enseña el % de autonomía.»
2. **Usuario real y su trabajo.** Artesana o tienda online pequeña (jabón, cosmética sólida, velas) que prepara
   5-30 envíos al día en su mesa: lee el pedido, busca las variedades, monta la caja, pone viruta, tarjeta y
   etiqueta. Le estorba el ir y venir pedido → estantería y los errores de variedad [sin fuente: hay que conseguir
   el jueves una frase y una foto de la mesa de una vendedora real de Bizkaia; sin eso, el crit. 8 queda en rojo].
3. **Reparto.** Persona: monta la caja de cartón, pone la viruta, cierra, pega la etiqueta, rescata si algo cae.
   Robot: coge del stock las pastillas del pedido y las deja dentro de la caja abierta.
4. **Referencia real.** Ultra (con π0.6 de Physical Intelligence): empaquetado y kits de pedidos para Highline
   Commerce, > 500.000 pedidos y un turno con 96,4 % de autonomía (declarado) [EA 2, 3]. Tutor Intelligence: kitting
   cobrado por hora (~14 $/h) [EA 4]. Nomagic: VLA en producción en Brack.Alltron [EU 6].
5. **Escena tal cual.** 12 pastillas de jabón reales en su caja de cartón, de 4 variedades con color de caja muy
   distinto (morado lavanda, negro carbón, naranja, verde); formato «invitado» ~60 × 40 × 25 mm y ~50 g [medidas
   a confirmar con el producto que se compre]. Tumbadas y sueltas en una bandeja de stock de 300 × 200 mm con
   fondo de fieltro. Caja de envío real de 150 × 100 × 70 mm (boca mucho mayor que la pastilla: tolerancia de
   varios cm). Se imprime: marco de la bandeja de stock, base con tope en L para la caja, soporte de tablet y
   caja del pulsador «rescate». Cámaras: cenital fija (organización) + webcam lateral nuestra.
6. **Órdenes del VLA.** Mínimo: `Pick the purple soap and place it in the box.` /
   `Pick the black soap and place it in the box.` Extra: `Pick the orange soap…`, `Pick the green soap…`.
   Cambia **qué objeto** (color de caja visible), no la escena. Por qué no un script: las pastillas están sueltas,
   giradas y en sitio distinto en cada pedido, y la caja la deja la persona donde le viene bien; añadir una
   variedad nueva son 50 demostraciones, no programación (el argumento de venta de Ultra y Sereact).
7. **Guion de 3 min con el juez.**
   - 0:00-0:20 · Pitch en una frase; en la tablet, «Autonomía del fin de semana: NN % (n/m artículos)».
   - 0:20-0:40 · El juez hace un pedido en la tablet como cliente: 2 variedades a su gusto, y revuelve el stock.
   - 0:40-1:50 · El juez pasa a ser la artesana: pliega la caja plana y pone la viruta mientras el robot trae la
     primera pastilla; deja la caja en la base y entra la segunda. El contador sube en directo.
   - 1:50-2:20 · **Recuperación planificada:** un compañero hace un pedido con una variedad agotada o cae una
     pastilla fuera; el juez la mete a mano y pulsa «rescate»: el % baja a la vista. «Así cobra Ultra: por turno,
     con una persona que rescata.»
   - 2:20-3:00 · El juez cierra, pega la etiqueta impresa con su nombre y **se lleva el paquete**. Momento
     memorable: el jurado sale con el producto de la demo en la mano.
8. **Escalera.** N1 (sáb. 12:00): 2 variedades, caja en posición fija, orden desde teclado. N2 (sáb. 20:00):
   4 variedades, pedido desde tablet, contador de autonomía y pulsador de rescate. N3 (dom.): voz, la cámara
   cenital comprueba el contenido antes de cerrar, caja en posición libre.
9. **Fiabilidad.** Gesto difícil: pinza cenital sobre una caja de 40 mm de ancho tumbada entre otras; tolerancia de
   agarre ~±1 cm, de depósito > ±3 cm. Fallo barato: se repite la orden o rescata la persona (es parte del
   producto). Plan B: un ACT por variedad y el orquestador elige. Si el VLA ignora el texto: se ve que coge la
   variedad equivocada → se pasa a plan B; por eso los colores son muy distintos.
10. **Jueves.** ~5 h de impresión [estimación]; electrónica: 1 pulsador en ESP32 (firmware ya hecho). Se reutiliza:
    tablet arcade (ahora «tienda»), voz → LLM → orden cerrada, flujo grabar/entrenar/evaluar, HF Jobs. Compras:
    jabones, cajas de envío, viruta, etiquetas.
11. **Puntos débiles.** (a) A la vista es coger y dejar por colores: un jurado técnico puede decir «visión clásica
    + script lo hace»; la defensa es el stock revuelto y la variedad nueva sin programar. (b) Una persona coge dos
    pastillas más rápido que el brazo: el valor solo se sostiene si trabaja en paralelo. (c) Parecidos: familia
    de Flip & Ship (paquetería), aunque aquí no se voltea nada; y los «clasificadores» de la lista de perdedores.
    (d) Sin la cita de una vendedora real es otra historia puesta encima.
12. **Autoevaluación.** Vivo 26/30 · VLA y dificultad 12/20 · valor real 15/20 · memorable 12/15 · viable 14/15
    = **79/100**.

---

## Concepto 2 · BANCADA

1. **Frase.** «Lo mismo que Medra vende a Genentech, en un brazo de 300 € junto a un técnico de laboratorio: con
   la pipeta en la mano dice "siguiente" y el robot le trae y le retira los tubos.»
2. **Usuario real y su trabajo.** Técnico de laboratorio de instituto de FP, de universidad o de control de calidad
   de una empresa pequeña (cervecera, cosmética, aguas): hace series de diluciones y preparación de muestras con
   guantes y pipeta. Cada cambio de tubo le obliga a soltar la pipeta, coger, destapar, dejar; con guantes no puede
   tocar pantallas [sin fuente: falta la queja de un técnico real; se puede pedir el jueves a un laboratorio de
   FP o de la UPV/EHU].
3. **Reparto.** Persona: destapa, pipetea, tapa, rotula. Robot: trae el tubo que toca al puesto de trabajo y lleva
   el terminado a la gradilla de salida; solo mueve tubos tapados y solo tras una orden hablada.
4. **Referencia real.** Medra: brazos genéricos que operan instrumentos y mueven tubos y placas por órdenes en
   lenguaje natural; 5 instalaciones de pago (Genentech, Addition Therapeutics, Cultivarium), Serie A de 52 M$
   [EA 20, 21]. Hueco: no hay uso de laboratorio documentado con SO-101/LeRobot [EU 31, 32].
5. **Escena tal cual.** 6 tubos Falcon de 50 ml reales (Ø 30 mm, 115 mm de alto, ~13 g vacíos, ~35 g con 20 ml
   de agua), tapas de dos colores (azul y naranja). Gradilla de entrada y gradilla de salida impresas, de 6
   huecos a 60 mm entre centros, con boca en embudo de 50 → 32 mm (el fondo cónico del tubo se autocentra).
   Puesto de trabajo: un alojamiento con el mismo embudo, delante de la persona. Pipetas Pasteur de plástico,
   agua con colorante alimentario, rotulador, guantes. Cámaras: cenital + webcam lateral.
6. **Órdenes del VLA.** Mínimo: `Bring a tube from the input rack to the work stand.` /
   `Move the tube from the work stand to the output rack.` Extra: `Bring the orange-cap tube to the work stand.`
   (elige por tapa), `Move the tube from the work stand to the waste bin.` Cambia **de dónde, adónde y qué tubo**;
   el estado (puesto ocupado o vacío, huecos libres) se ve en la escena. Por qué no un script: el número y la
   posición de los tubos en la gradilla cambian en cada serie, el hueco libre de salida también, y el protocolo
   lo dicta la persona sobre la marcha, que es justo lo que vende Medra.
7. **Guion de 3 min con el juez.**
   - 0:00-0:20 · Pitch; pantalla: «Autonomía: NN % de movimientos sin tocar» y el protocolo «dilución seriada 1:2».
   - 0:20-0:40 · El juez se pone guantes y coge la pipeta; un compañero le explica el único gesto: pasar una
     pipeta de colorante al tubo que tenga delante.
   - 0:40-2:10 · El juez dice «next sample»; el robot trae un tubo; el juez destapa, pipetea, tapa y dice «done»;
     el robot lo lleva a la salida y trae el siguiente. Tres o cuatro tubos, sin soltar la pipeta.
   - 2:10-2:30 · **Recuperación planificada:** el juez dice «discard this one» (burbuja, error): el tubo va al
     descarte y el contador lo anota. Si un tubo queda torcido en el embudo, el juez lo endereza con la mano
     libre y dice «rescued».
   - 2:30-3:00 · **Momento memorable:** la gradilla de salida muestra el degradado de color de la serie, hecho
     por el juez sin soltar la pipeta. «Medra lo hace con 100 brazos; esto cabe en la bancada de un instituto.»
8. **Escalera.** N1 (sáb. 12:00): las 2 órdenes con tubos tapados y vacíos, orden por teclado. N2 (sáb. 20:00):
   voz, tubos con agua, contador de autonomía, serie completa de 4 tubos. N3 (dom.): elegir por color de tapa y
   descarte.
9. **Fiabilidad.** Gesto difícil: dejar el tubo vertical en el alojamiento; tolerancia ±9 mm por el embudo, pero
   una inclinación del tubo en la pinza puede acuñarlo [riesgo no probado]. Se coge por la tapa estriada
   (Ø ~35 mm), que sobresale 60 mm de la gradilla. Plan B: un ACT por orden (la secuencia es casi fija y el
   orquestador alterna). Si el VLA falla: tubo tumbado y tapado, sin derrame; la persona lo recoloca.
10. **Jueves.** ~8 h de impresión (2 gradillas, puesto de trabajo, descarte, almohadillas de pinza) [estimación].
    Electrónica: ninguna crítica (LED de estado opcional). Se reutiliza: voz → LLM → orden cerrada (es el centro
    del concepto y ya está hecho), tablet, flujo de entrenamiento. Compras: tubos Falcon, pipetas, guantes.
11. **Puntos débiles.** (a) Líquido cerca de la persona: el enclavamiento es «solo tubos tapados y solo tras
    orden», más agua con colorante; si el jurado ve un tubo abierto moverse, se pierde. (b) El laboratorio es
    menos «taller/hobby» que un banco de electrónica. (c) La voz depende del ruido de la sala: hace falta pulsador
    de respaldo. (d) La secuencia traer/retirar es casi fija: un jurado puede decir que el lenguaje sobra hasta
    que se llega a N3. (e) Sin técnico real citado, necesidad prestada de Medra.
12. **Autoevaluación.** Vivo 22/30 · VLA y dificultad 15/20 · valor real 14/20 · memorable 13/15 · viable 12/15
    = **76/100**.

---

## Concepto 3 · PLANTEL

1. **Frase.** «Lo mismo que Robovision e ISO Group venden a Florensis, en un brazo de 300 € y en la mesa de un
   vivero pequeño: tú separas los hijuelos de la planta madre y el robot los coloca en la bandeja, por variedad.»
2. **Usuario real y su trabajo.** Vivero pequeño o coleccionista que multiplica suculentas y vende plantel: separa
   a mano los hijuelos (rosetas) de la planta madre, los limpia y los posa uno a uno en bandejas de alvéolos,
   por variedad. Le estorba el trabajo repetitivo de colocar y no mezclar variedades [sin fuente: falta la cita
   de un vivero de Bizkaia; práctica de posar la roseta sobre el sustrato sin enterrarla, a confirmar con él].
3. **Reparto.** Persona: separa hijuelos con los dedos (sin tijera), quita hojas secas, los deja en el montón y
   rellena bandejas. Robot: coge cada roseta del montón y la posa en un alvéolo libre de la fila de su variedad.
4. **Referencia real.** Robovision + ISO Group en Florensis: reconocer, coger y plantar esquejes de 4.000
   especies, hasta 2.800/h; los propios plantadores reentrenan el modelo en 15 min [EU 20].
5. **Escena tal cual.** 12-16 rosetas reales de dos géneros que se distinguen a simple vista: Sempervivum
   rojizo y Echeveria verde azulada, de 30-45 mm de diámetro y pocos gramos [pesos y tamaños a confirmar con la
   planta comprada]. Bandeja de vivero real de 3 × 4 alvéolos de ~50 mm con sustrato. Las rosetas se echan sobre
   una estera de fieltro de 250 × 200 mm. Se imprime: marco de la bandeja, borde de la estera, yemas anchas y
   blandas para la pinza (con espuma). Cámaras: cenital + lateral.
6. **Órdenes del VLA.** Mínimo: `Place a red rosette in the top row of the tray.` /
   `Place a green rosette in the bottom row of the tray.` Extra: `Place the rosette in the empty cell.`,
   `Move the damaged rosette to the discard bowl.` Cambia **qué objeto y adónde**. Por qué no un script: cada
   roseta tiene forma, tamaño y postura distintos y cae donde cae; es el caso de la tabla en que quitar el
   aprendizaje se nota más.
7. **Guion de 3 min con el juez.**
   - 0:00-0:20 · Pitch con la foto de la línea de Florensis; pantalla: «Rosetas colocadas sin ayuda: NN %».
   - 0:20-1:00 · El juez separa con los dedos 3-4 hijuelos de una planta madre y los echa al montón, mezclados.
   - 1:00-2:10 · El juez pide «rojas arriba»; el robot coloca dos; pide «verdes abajo»; coloca otras dos,
     mientras el juez sigue separando hijuelos.
   - 2:10-2:30 · **Recuperación planificada:** una roseta queda de lado o cae fuera del alvéolo; el juez la
     endereza y pulsa «rescate»; el robot sigue con la siguiente.
   - 2:30-3:00 · **Momento memorable:** bandeja bicolor plantada entre los dos; el juez se lleva una maceta con
     «su» hijuelo. Nadie espera plantas vivas en un hackathon de robótica.
8. **Escalera.** N1 (sáb. 12:00): una variedad, cualquier alvéolo libre. N2 (sáb. 20:00): dos variedades por
   filas y contador de autonomía. N3 (dom.): voz, descarte de la roseta dañada, bandeja completa de 12.
9. **Fiabilidad.** Gesto difícil: coger una roseta irregular sin romper hojas ni dejarla volcada; depósito con
   ±1 cm en alvéolo de 50 mm. **Es el concepto con más incertidumbre: ni el agarre ni la respuesta de SmolVLA
   con objetos orgánicos están probados.** Plan B: ACT por variedad; plan C con el mismo relato: bulbos de otoño
   (rígidos, 30-40 mm), con la pega de que el robot no los orienta. Si el VLA falla: roseta fuera del alvéolo,
   sin daño ni riesgo; la persona la coloca.
10. **Jueves.** ~4 h de impresión [estimación]; electrónica: el pulsador de rescate ya hecho. Se reutiliza:
    tablet, voz, flujo de entrenamiento. Compras: 4-6 plantas madre con hijuelos, bandeja de alvéolos, sustrato,
    macetas pequeñas. Riesgo logístico: tierra en la mesa y plantas que se estropean tras 100 demostraciones
    (hay que traer el doble).
11. **Puntos débiles.** (a) Sin robot antes del evento no se puede comprobar el agarre: si falla el viernes, se
    cae el concepto entero (choca con U3). (b) Las hojas rotas cambian el aspecto del objeto entre episodios.
    (c) Un vivero es «banco de trabajo» pero se aleja del taller que el usuario tenía en mente. (d) Parecido con
    el sembrador de 1.600 episodios que perdió (tema agrícola, sin humano en el centro); aquí la diferencia es
    que el juez trabaja. (e) La referencia hace 2.800/h; el SO-101 hará unas pocas por minuto [estimación].
12. **Autoevaluación.** Vivo 17/30 · VLA y dificultad 18/20 · valor real 13/20 · memorable 13/15 · viable 10/15
    = **71/100**.

---

## Comparación y recomendación

| | Pedido Listo | Bancada | Plantel |
|---|---|---|---|
| Referencia que se trasplanta | Ultra / Tutor / Nomagic | Medra | Robovision + ISO |
| Lo que cambia la orden | qué variedad | de dónde, adónde, qué tubo | qué roseta y qué fila |
| Mayor riesgo | «es un script con visión» | tubo acuñado; líquido | agarre sin probar |
| Puntuación propia | 79 | 76 | 71 |

**Defendería Pedido Listo:** es el de gesto más tolerante, el que tiene la referencia con la métrica más citable
(96,4 % de autonomía por turno) y el único cuyo rescate humano es parte del producto y no un fallo. Su punto
flojo es la dificultad percibida; se puede reforzar con la capa de voz de Bancada sin añadir órdenes. Si el
jurado valora más ver el VLA que la fiabilidad, la alternativa es Bancada. Los tres dependen de conseguir el
jueves una cita y una foto de un usuario real: hoy ninguno la tiene.
