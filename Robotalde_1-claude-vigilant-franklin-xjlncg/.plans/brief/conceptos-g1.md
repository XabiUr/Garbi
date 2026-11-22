# Conceptos G1 · lente: banco de electrónica y de reparación (18-11-2026)

Leyenda: [H] fuente leída y [H·b] extracto de buscador (ambas heredadas de `.plans/necesidad/`) · [I] inferencia ·
[sin fuente] no respaldado: verificar antes de decirlo en el pitch. No se ha buscado nada nuevo en la web. Las medidas
marcadas [medir] y las horas de impresión son estimaciones propias. Ningún concepto lleva luz ni linterna, y ninguno
lleva soldador (no hay calor en la mesa).

Descartados antes de escribir (criterio de eliminación entre paréntesis): pasar herramientas de mano (2: pinzas y
destornilladores finos) · clasificar fracciones de un despiece de RAEE (5 y «clasificador previsible») · ordenar el
banco al acabar (5: la persona solo mira) · alimentar componentes para montaje de inserción con soldador (4 y 6:
demasiado cerca de MSN y calor) · llavero de tecla mecánica a la carta (1 y 2: quiosco, piezas de 14-18 mm).

---

## A · Tornillero

1. **Nombre y frase.** *Tornillero: tú desmontas el portátil; el robot te guarda los tornillos por grupos y te los
   devuelve en el orden inverso, sin que levantes la vista.*
2. **Usuario real y su trabajo.** Técnico de reparación de portátiles y móviles, voluntario de Repair Café, alumno
   de FP de microinformática. Con las manos: desatornilla, levanta tapas, cambia la pieza y vuelve a montar. Qué le
   estorba: iFixit pone entre los diez fallos más probables suponer que los tornillos se quedarán en su sitio en la
   mesa y que solo hay un par de longitudes, y avisa de que un tornillo en el agujero equivocado puede perforar un
   componente [H] (ifixit.com/News/the-10-things-likely-to-go-wrong-when-fixing-a-phone-or-laptop). Hoy se usan
   vasitos, cinta de doble cara o un dibujo en papel [H·b] (Technibble). Horas perdidas por esto: [sin fuente].
3. **Reparto.** Persona: todo el trabajo fino (desatornillar, cambiar el SSD, atornillar) y decir «hecho, tapa» o
   «siguiente». Robot: retira el vaso lleno de la zona de trabajo, lo aparca y trae el vaso pedido. El LLM lleva el
   registro (qué vaso es qué grupo) y lo pinta en la tablet como hoja de despiece.
4. **Referencia de physical AI real.** No lo vende nadie: es un hueco, y hay que decirlo así. La mecánica sí se paga:
   coger y dejar eligiendo el objeto según la orden, con una persona que rescata los fallos (Ultra con Physical
   Intelligence: kits por pedido, 96,4 % de autonomía declarada en un turno [H·b]). Métrica que copiamos: % de
   órdenes sin intervención en la sesión.
5. **La escena tal cual.** Un portátil viejo real de 14-15" boca abajo (el producto que se repara, no una carcasa
   impresa) · destornillador de precisión real · 3-4 vasos impresos mate de Ø40×30 mm, pared de 3 mm, imán en la base
   para que los tornillos no salten (~15 g; rojo, azul, amarillo) · plato de entrega impreso con cono Ø60→42 mm
   (±1 cm) junto al portátil · zona de aparcamiento libre de 20×15 cm en la esterilla, sin huecos fijos · un SSD M.2
   2280 (22×80 mm) de recambio o el mismo que se saca y se vuelve a poner. Cámaras: fija en diagonal y de muñeca.
6. **Órdenes del VLA.** Nivel mínimo: `Put the cup away.` (del plato a cualquier hueco libre del aparcamiento) y
   `Bring the red cup.` (del aparcamiento al plato). Extra: `Bring the blue cup.` y `Bring the yellow cup.` Cambia
   **qué objeto** (color) y **adónde**. Por qué no vale un script: los vasos no tienen sitio fijo, los aparca el
   propio robot donde cabe y el juez puede moverlos; hay vasos distractores. Honestidad: un jurado técnico puede
   decir «ArUco y cinemática inversa»; la respuesta es que no hay marcas ni huecos, y que el orden lo decide la voz.
7. **Guion de 3 minutos.** 0:00 frase del pitch; el juez se sienta con el destornillador. 0:15 quita los tornillos
   de la tapa y los echa al vaso rojo del plato; dice «hecho, tapa» → el robot aparca el rojo mientras el juez
   levanta la tapa (trabajo en paralelo). 0:55 el juez pone el vaso azul en el plato, quita el tornillo del SSD,
   «hecho, disco» → el robot aparca el azul. 1:20 cambia el SSD y dice «siguiente» → llega el azul (último en
   entrar, primero en salir); atornilla. 1:50 «siguiente» → un compañero ha movido el vaso rojo de sitio a la vista
   del juez; el robot lo encuentra y lo trae (**recuperación planificada**). 2:30 cierra la tapa, da la vuelta al
   portátil y lo enciende: arranca (**final que se ve**). La tablet muestra «0 tornillos sobrantes · autonomía de
   la sesión X %». Momento memorable: pedir «siguiente» sin mirar y que llegue el vaso correcto.
8. **Escalera de alcance.** N1 (sáb. 12:00): las 2 órdenes con el vaso rojo y un distractor; ciclo de un grupo.
   N2 (sáb. 20:00): `Bring the blue cup.`, dos grupos en orden inverso, voz y hoja de despiece en la tablet.
   N3 (dom.): tercer vaso, petición por nombre («dame los de las bisagras»), autonomía medida en 20 ciclos.
9. **Fiabilidad.** Gesto más difícil: coger un vaso de Ø40 mm en posición libre sin volcarlo y dejarlo en el cono
   (±1 cm): es el gesto más fiable del SO-101 según las directrices. Fallo barato: el imán retiene los tornillos
   aunque el vaso vuelque; se endereza y se repite la orden (cuenta como intervención, como en Ultra). Plan B: un
   ACT por orden y el LLM elige. Plan C: aparcamiento con huecos cónicos fijos (más fiable, pero ya programable: si
   se llega aquí, el relato pasa a ser el registro por voz). El arranque del portátil no depende del robot.
10. **Preparación del jueves.** Impresión ~6 h (4 vasos, plato, marco del aparcamiento). Electrónica: ninguna
    crítica; opcional, un reed bajo el plato con el firmware de ESP32 que ya existe. Software reutilizado: voz → LLM
    → orden cerrada, tablet, flujo de grabar y entrenar. Elegir un portátil de alguien del equipo con dos longitudes
    de tornillo, dejarlo arrancando rápido y ensayar el desmontaje con cronómetro. No hay que comprar nada.
11. **Puntos débiles honestos.** El VLA elige entre vasos de colores: es el punto que más se parece a «cubos de
    colores». La memoria del orden es del LLM, no del VLA. Una alfombrilla magnética barata resuelve buena parte
    del problema (precio: [sin fuente]). El robot es más lento que la mano. El juez puede perder un tornillo
    diminuto o tardar más de lo ensayado. Parecidos: la idea 2 de `ideas-asistentes-banco.md` (misma raíz, aquí con
    portátil real y vasos sin sitio fijo); ningún ganador conocido.
12. **Autoevaluación.** En vivo 27/30 · VLA 12/20 · valor 16/20 · momento 10/15 · viabilidad 13/15 → **78/100**.
    Eliminación: pasa los 8 (el 3 es el más justo).

---

## B · Recambista

1. **Nombre y frase.** *Recambista: dices la avería y, mientras abres el aparato, el robot te prepara en la bandeja
   los recambios de esa reparación y se lleva la pieza rota.*
2. **Usuario real y su trabajo.** Técnico de taller de reparación, voluntario de Repair Café, aficionado que
   mantiene mandos y máquinas arcade. Con las manos: abre, desconecta, saca la pieza rota y encaja la nueva. Qué le
   estorba: parar con el aparato abierto para buscar el recambio entre cajas. Queja con fuente sobre ese paso:
   [sin fuente] (es el punto más flojo; habría que conseguir una frase de un taller de Bilbao el jueves). Dato de
   contexto: hay unos 3.800-4.000 Repair Cafés en el mundo y la electrónica es su categoría con menos éxito [H·b].
3. **Reparto.** Persona: abre el mando, quita los terminales faston, saca el botón roto, encaja el nuevo y enrosca
   la bola (inserción y fuerza: justo lo que el robot no hace). Robot: busca cada recambio entre piezas sueltas, lo
   deja en la bandeja y retira la pieza rota al cubo de averiados.
4. **Referencia de physical AI real.** Kits por pedido de Ultra (Highline Commerce, más de 500.000 pedidos, 96,4 %
   de autonomía declarada [H·b]) y dispensación por receta de Galbot en una farmacia de Pekín [H·b]. Aquí la
   «receta» es la orden de reparación. Métrica: artículos correctos y % de autonomía por turno de pedidos.
5. **La escena tal cual.** Un mando arcade USB real (caja con 6 botones de 30 mm y palanca, codificador USB
   comercial) conectado al juego de la tablet del equipo · recambios reales sueltos en la esterilla, en cualquier
   postura estable: 3 botones de 30 mm (rojo, amarillo, azul; corona de ~33 mm, ~20 g [medir]), 1 bola de palanca
   de Ø35 mm, y como distractores una pila de 9 V (48,5×26,5×17,5 mm, ~45 g) y un rollo de cinta aislante · bandeja
   de kit impresa de 120×80 mm con borde en embudo · cubo de averiados de Ø100 mm. Cámaras: fija y de muñeca.
6. **Órdenes del VLA.** Nivel mínimo: `Put the red button in the tray.` y `Put the ball top in the tray.` Extra:
   `Put the yellow button in the tray.` y `Put the broken part in the bin.` Cambia **qué objeto**, distinto en
   forma y color, entre distractores. Por qué no vale un script: las piezas están sueltas, donde caigan y como
   caigan; un recambio nuevo se añade con episodios, no con código (el argumento de la cola larga de Ultra).
7. **Guion de 3 minutos.** 0:00 el juez pulsa el botón rojo del mando: el personaje de la tablet no reacciona.
   0:15 dice «el rojo no va y falta la bola» → el LLM encola dos órdenes. 0:20-1:00 el robot prepara el kit mientras
   el juez abre la tapa y saca el botón muerto (**en paralelo: ahí está el valor**). 1:00 el juez coge el botón de
   la bandeja (nunca de la pinza), lo encaja, conecta los dos faston y enrosca la bola. 1:45 deja el botón roto en
   la esterilla y dice «llévate lo roto» → al cubo. 2:10 pulsa el rojo: el personaje responde y el juez juega 20 s
   con lo que acaba de reparar (**momento memorable**). Recuperación planificada: se pide a propósito con el botón
   amarillo pegado al rojo; si el robot coge el que no es, «ese no» → el LLM repite la orden y sube el contador.
8. **Escalera de alcance.** N1 (sáb. 12:00): las 2 órdenes con 2 distractores. N2 (sáb. 20:00): tercer recambio,
   retirar lo roto, pedido de varios artículos por voz. N3 (dom.): el LLM deduce el kit desde el síntoma («el rojo
   no va») y turno medido de 20 pedidos en pantalla.
9. **Fiabilidad.** Gesto más difícil: coger un botón cilíndrico de 30 mm en postura libre (rueda si se empuja).
   Tolerancia: esterilla de silicona, botones apoyados boca abajo, bandeja con embudo de ±2 cm. Fallo barato: pieza
   caída → se repite la orden. Plan B: un ACT por recambio y el LLM elige. Si el VLA falla del todo, el juez coge
   la pieza él mismo y la reparación termina igual; la demo no se queda a medias.
10. **Preparación del jueves.** Hay que **comprar el jueves** un kit de mando arcade (botones, palanca y
    codificador USB): riesgo de no encontrarlo en tienda en un día. Respaldo: leer los botones con el ESP32 y el
    firmware que ya existe. Impresión ~9 h (caja del mando en dos mitades, bandeja y cubo), o caja de madera y
    solo ~2 h. Software reutilizado: voz → LLM → orden, tablet arcade y personaje.
11. **Puntos débiles honestos.** «Lo cojo yo antes»: en un banco pequeño, alcanzar un recambio cuesta 3 segundos;
    el valor solo se sostiene por el trabajo en paralelo y por la variedad. El arcade es un nicho y puede parecer un
    juguete. Se parece de tema a **Relevo** (repuestos), ya rechazado; la diferencia es que aquí encaja la persona
    y el aparato es real, pero el parecido existe. Depende de una compra de última hora.
12. **Autoevaluación.** En vivo 23/30 · VLA 16/20 · valor 12/20 · momento 13/15 · viabilidad 9/15 → **73/100**.
    Eliminación: pasa, con el 8 en el límite (no hay todavía un usuario citado) y el 7 pendiente de la compra.

---

## C · Sondas libres

1. **Nombre y frase.** *Sondas libres: tú tienes las dos manos en las puntas del polímetro; el robot te trae la
   placa averiada que pides, te la sujeta inclinada, le da la vuelta y la lleva al comprobador.*
2. **Usuario real y su trabajo.** Técnico de reparación de electrónica, alumno y profesor de FP en prácticas de
   localización de averías, voluntario de Repair Café. Con las manos: una punta de prueba en cada una; busca el
   punto que no da continuidad y cambia la pieza. Qué le estorba: la placa se desliza y no puede girarla sin soltar
   las puntas. Quejas leídas sobre los soportes: reposicionar la placa en un Omnivise es «a bit of a pain», las
   placas grandes son «impossible to incline», la pinza de cocodrilo «doesn't seem to stay where I put it» [H]
   (EEVblog, «A better helping hands tool»). Que en FP se practique con averías provocadas: [sin fuente].
3. **Reparto.** Persona: mide con las dos puntas, decide dónde está el fallo, cambia el fusible con los dedos.
   Robot: coge la placa pedida de la cola de entrada, la presenta apoyada en un tope, le da la vuelta cuando se le
   pide y la lleva al comprobador o al cajón de «sin arreglo».
4. **Referencia de physical AI real.** Carga de útiles y de puestos de prueba: Figure en BMW Spartanburg (más de
   90.000 piezas cargadas en el útil [H]) y AgiBot en Longcheer (carga y descarga de tablets, ~3.000 por turno
   [H·b]). El robot presenta la pieza y la persona, o la máquina, hace el trabajo. Métrica: placas atendidas por
   sesión y % sin intervención.
5. **La escena tal cual.** 3 placas reales de 70×50 mm con portafusibles de 5×20 mm, LED, zumbador y anillas de
   test, cada una en un marco impreso con mango de 25×25×60 mm (~40 g en total; marcos rojo, azul y verde). Averías
   reales: un fusible fundido de verdad, un puente abierto · polímetro real en modo continuidad · tope de
   presentación impreso donde apoya el canto del marco (absorbe el empuje de las puntas) · comprobador impreso con
   boca en V (±1 cm), dos contactos de muelle y 5 V: si la placa está reparada, se enciende y suena · cajón de
   «sin arreglo». Cámaras: fija y de muñeca.
6. **Órdenes del VLA.** Nivel mínimo: `Hold up the red board.` y `Hold up the blue board.` (coger por el mango,
   esté donde esté, y presentarla a 30° apoyada en el tope). Extra: `Put the board in the tester.` y `Put the board
   in the scrap bin.` Programado, sin aprendizaje (híbrido): dar la vuelta (giro de muñeca de 180°), pasos de ±15°
   y congelar la pose mientras se mide. Cambia **qué objeto** y, en las extra, **adónde**. Por qué no vale un
   script: las placas esperan sueltas, giradas y con otras al lado; el agarre sale de la imagen.
7. **Guion de 3 minutos.** 0:00 frase del pitch; el juez coge las dos puntas. 0:15 «dame la roja» → el robot la
   coge y la presenta. 0:40 el juez mide: el fusible no pita. 1:00 «dale la vuelta» → comprueba las pistas (pita).
   1:20 cambia el fusible con los dedos, con el robot quieto. 1:40 «pruébala» → al comprobador: LED, melodía y
   «Reparada 1/3» en la tablet (**final que se ve**). 2:00 «dame la azul»: un compañero la ha movido y girado; el
   robot la encuentra (**recuperación planificada**). 2:40 el juez se lleva una etiqueta «Reparado por ___» con el
   fusible fundido pegado (**lo que se lleva a casa**).
8. **Escalera de alcance.** N1 (sáb. 12:00): las 2 órdenes; la entrega al comprobador se hace con trayectoria
   grabada desde el tope. N2 (sáb. 20:00): `Put the board in the tester.` aprendida, volteo por voz y contador.
   N3 (dom.): tercera placa, cajón de «sin arreglo» y sesión medida.
9. **Fiabilidad.** Gesto más difícil: llevar la placa cogida por el mango hasta el tope con la inclinación buena
   (±1 cm; el tope tiene forma de V). El servo cede unos milímetros al empujar: por eso apoya en el tope y se
   congela. Plan B: un ACT por placa. Plan C: el robot deja la placa en una cuna de dos caras en vez de sostenerla;
   se sigue pudiendo medir. Si falla el agarre, la placa cae 5 cm sobre la esterilla y se repite.
10. **Preparación del jueves.** Impresión ~8 h (3 marcos, tope, comprobador, cajón). Andoni monta las 3 placas
    (~2 h) y el comprobador (contactos de muelle y un LED; lectura con el ESP32 opcional). Hacen falta fusibles de
    5×20 mm y un polímetro. Software reutilizado: voz → LLM → orden, tablet, firmware.
11. **Puntos débiles honestos.** Es de la familia de «Dale la vuelta» (`afondo-tercera-mano.md`) y del mismo banco
    que MSN, aunque sin luz y sin soldador; el pitch debe decir la diferencia en una frase. Un soporte pasivo
    barato hace gran parte del trabajo. En N1 el lenguaje solo distingue el color del marco, y el volteo es
    programado. Las placas son de prácticas, preparadas por nosotros: un juez puede verlas como atrezo; se mitiga
    usando módulos comerciales con la avería provocada.
12. **Autoevaluación.** En vivo 23/30 · VLA 13/20 · valor 15/20 · momento 12/15 · viabilidad 11/15 → **74/100**.
    Eliminación: pasa los 8; el 4 hay que vigilarlo en el pitch.

---

## Cuál defendería

**A · Tornillero.** Es el único con un portátil real encima de la mesa, una queja con fuente leída (iFixit), el
gesto más tolerante del SO-101, ninguna compra y ninguna electrónica crítica. Su punto flojo es el VLA (vasos de
colores). Para subirlo, el N3 puede tomar prestada una orden de B: `Bring the new part.` (el recambio en su caja),
de modo que la orden cambie también el tipo de objeto. Si el equipo prioriza que el VLA se vea por encima de la
fiabilidad, la alternativa es B, y antes hay que conseguir una cita de un taller real.
