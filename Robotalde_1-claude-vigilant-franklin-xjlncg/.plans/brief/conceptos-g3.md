# Conceptos G3 · lente «la experiencia del juez primero» (18-11-2026, rev. 2 con la rúbrica de Robotekin)

Método: se parte de lo que la persona hace con sus manos, de lo que se lleva y del instante en que el robot le
ayuda con las manos ocupadas. Rev. 2: cada ficha declara la **tarea completa** (≤ 40 s, el robot solo, 5 veces
seguidas sin que nadie entre en el brazo) y su **historia de datos**; el rescate humano sale de la demo puntuada y
queda como dato del entrenamiento. Marcas: **[H]** hecho del repo con fuente · **[I]** inferencia · **[sin
fuente]** hay que validarlo el jueves. Medidas y pesos aproximados. Las notas son autoevaluación con §9.

Común a los tres: (a) dos cámaras de política fijas (trípode y muñeca) y luz propia; (b) tabla en la tablet
«modelo × X/10» (ACT frente a SmolVLA, antes y después de la ronda de corrección) y dataset en Hugging Face (+3) con
repo reproducible (+2); (c) la persona trabaja siempre fuera del alcance del brazo.

Descartados con §8: «pásame el bote» de pintura (crit. 3; la persona lo alcanza sola) · sujetar al pegar (un
sargento lo hace mejor) · cuero con troqueles (crit. 2) · tubos de laboratorio (crit. 2 y 6; precedente CCSF) ·
esquejes (crit. 3; el sembrador perdió) · galletas (crit. 4) · banco de test con puntas (crit. 3).

---

## Concepto 1 · TANDA, el ayudante de plató

**1. Frase.** «Tú no sueltas la cámara: el robot te cambia el artículo y te mueve el reflector cuando se lo pides.»

**2. Usuario real.** Revendedora de Vinted/Wallapop o artesana de Etsy que fotografía tandas de 10-30 artículos por
semana. Manos: las dos en el móvil; cada cambio de artículo o de reflector obliga a soltarlo y reencuadrar. Un
tercio de 339 revendedores dice que fotografiar y publicar es lo más difícil [H, Fleek]; mediana de 15 min por
imagen antes de usar IA [H, Photoroom, sesgo de fabricante]. Que el cambio de artículo sea el estorbo concreto:
[sin fuente], validar el jueves con una vendedora (cita y foto de su mesa).

**3. Reparto.** Persona: encuadra, dispara y pide la luz. Robot: retira el artículo fotografiado, trae el
siguiente y mueve el reflector. Programado: disparo, galería, borrador de anuncio, encadenado de órdenes.

**4. Referencia de physical AI.** Los estudios ya pagan automatización (Orbitvu desde 270 €/mes; PhotoRobot), pero
esos equipos mueven la cámara o la mesa, nunca el objeto [H/I, afondo §2]. Del mercado se copia «coger y dejar con
mucha variedad» y la métrica de autonomía (Ultra, 96,4 % declarado) [H]. Ninguna empresa vende un ayudante de plató
con brazo [sin fuente]: es hueco, no categoría probada.

**5. Escena tal cual (60 × 40 cm).** Cartulina blanca curvada y **un foco LED fijo** a la izquierda. **Atril
impreso** de 120 mm, respaldo a 25°, labio de 15 mm, EVA, abierto por la derecha hacia la **caja de hechos** (25 ×
20 cm, fondo blando, más baja). **Cola:** bandeja de EVA de 25 × 18 cm con 5-6 artículos sueltos. **Reflector:**
cartón pluma de 150 × 200 × 5 mm sobre pie con asa de 30 mm e imán; dos posiciones con arandela. Artículos: 25-30
rígidos de mercadillo, 20-60 mm de agarre y 30-250 g (fundas de gafas, carteras, figuras, mandos, botes). El móvil
de fotos (con empuñadura impresa a dos manos) no entra en la política.

**6. Órdenes del VLA.** Mínimo: (A) `Put the next item on the stand.` · (B) `Sweep the item off the stand into the
box.` (empujar es más tolerante que coger [I]). Extra: (C) `Place the white card next to the stand.` · (D) `Take
the white card back to its base.` Cambia qué objeto y adónde. Un script no vale porque cada artículo es distinto y
está suelto en cualquier pose. Arreglo de los dos puntos débiles: *VLA poco necesario* → se deja el giro de 360° a
la mesa de 30 € y se hace lo que esa mesa no hace; *objetos nunca vistos* → pasan de riesgo de la demo a
experimento del dataset (punto 9) y el objeto del juez lo coloca el juez salvo que la medida diga otra cosa.

**7. Tarea completa y guion.** **Tarea declarada: «siguiente»** = B + A encadenadas (≤ 40 s): el artículo
fotografiado sale a la caja y el siguiente queda en el atril. Se repite 5 veces con 6 artículos vistos cargados
antes de empezar; la escena se repone sola (la cola se vacía, la caja se llena) y nadie entra en el brazo.
- 0:00 Frase. Un juez coge el móvil a dos manos, a 40 cm fuera del alcance.
- 0:15-3:15 Cinco «siguiente». Entre uno y otro el juez dispara: es trabajo real y da tiempo al ciclo.
- En el 2.º dice «rellena la sombra» (C): **momento**, ve abrirse la sombra en su visor sin bajar el móvil.
- Recuperación: la política reintenta el agarre sola (se graban reagarres); el sistema mira si el atril quedó
  ocupado y repite la orden dentro de los 40 s. Sin manos.
- Fuera de los 5 intentos: su objeto lo pone él, lo fotografía y se lleva por QR fotos y borrador de anuncio.

**8. Escalera.** N1 (sáb 12:00): A con 12 objetos, ≥ 5/10. N2 (sáb 20:00): tarea «siguiente» 4/5 en ensayo, C y D,
voz, tabla de modelos. N3 (dom): objeto del juez en autónomo si «nuevos» ≥ 8/10; fondo quitado por IA.

**9. Fiabilidad y datos.** Gesto más difícil: coger de la bandeja una forma arbitraria; dejar con ±3 cm. Diez
movimientos para 5/5: si el sábado a las 20:00 no sale, se declara como tarea solo A (un movimiento) y B la hace
un ACT. Plan B: un ACT por orden. **Historia de datos (20 pt):** ~150 episodios; 20 objetos de entrenamiento y **5
apartados**; tabla vistos/nuevos × ACT/SmolVLA; episodios con el reflector en las dos posiciones para enseñar que
aguanta el cambio de luz que el propio trabajo provoca; ronda de corrección regrabando solo los objetos que
fallaron. Para los 5 intentos se eligen los 6 objetos con mejor medida.

**10. Jueves.** Impresión ~10 h: atril (3), dos pies de reflector (2), empuñadura (2), almohadillas TPU (2),
soporte de webcam (1). Electrónica: ESP32 + tira LED (hecho). Comprar: cartón pluma, EVA, cartulina, foco.
Reutiliza voz → LLM → orden, tablet, grabar/entrenar, HF Jobs.

**11. Puntos débiles.** Una persona cambia un artículo en 3 s: el valor solo existe en tanda y con las manos en la
cámara, y está sin validar. Un jurado de automatización puede verlo poco industrial. Dos movimientos por intento
bajan la probabilidad de 5/5. A y B se distinguen también por la escena: el texto pesa poco en el mínimo. El
reflector exige luz dura bien puesta (probar el jueves con el móvil). Sin precedentes en LeRobot [H·b].

**12. Autoevaluación (§9).** Demo 19/30 · datos 16/20 · dificultad 11/15 · utilidad 10/15 · innovación 8/10 ·
presentación 9/10 = **73**. Pasa los ocho criterios; el 3 pasa por la variedad de objetos, no por el texto.

---

## Concepto 2 · PEDIDO, el mozo de la tienda de una sola persona

**1. Frase.** «Mientras tú sellas la caja y escribes la nota, el robot te prepara el pedido.»

**2. Usuario real.** Artesana con tienda en Etsy o web propia (jabones, velas, té) que empaqueta sola 10-30 pedidos
al día: monta la caja, la sella con su logo, envuelve, escribe la nota y entre medias va a por cada producto. Etsy:
5,6 M de vendedores activos [H, 10-K]. Tiempo por pedido y errores de artículo: [sin fuente]; llamar el jueves a
una tienda local.

**3. Reparto.** Persona: monta la caja, estampa el logo (dedos con tinta: mejor no tocar el producto), envuelve,
escribe, cierra y etiqueta. Robot: saca de la cubeta los productos del pedido y los suelta en la rampa.

**4. Referencia de physical AI.** Kits y pedidos con variedad: Ultra con Physical Intelligence y Tutor; se cobra
por hora y se enseña el % de autonomía (96,4 % declarado) [H, directrices §5]. Precedente: GreatAkihabara ganó AMD
Tokio con SmolVLA multitarea por texto y 120 episodios [H]. Sin uso productivo documentado de un SO-101 [H].

**5. Escena tal cual (70 × 40 cm).** **Cubeta** baja de 30 × 20 × 4 cm con EVA, una capa, 12 unidades mezcladas.
Cuatro referencias reales: jabón en caja ~90 × 60 × 30 mm, ~110 g; vela en lata con faja ~Ø55 × 45 mm, ~120 g;
bote PET ~Ø50 × 60 mm, ~100 g; caja de té ~55 mm, ~50 g. **Rampa de pedido impresa:** boca de 15 × 15 cm junto a
la cubeta y tobogán de 30 cm hasta la zona de la persona, fuera del brazo; un sensor reed o una barrera cuenta lo
que pasa. Zona de la persona: cajas kraft de ~15 × 10 × 5 cm, papel de seda, tampón y tinta, tarjetas, etiquetas.

**6. Órdenes del VLA.** Mínimo: `Pick the soap box and drop it in the chute.` · `Pick the tea box and drop it in
the chute.` Extra: `Pick the candle tin and drop it in the chute.` · `Pick the white jar and drop it in the chute.`
Cambia **qué objeto**, distinto a la vista: el caso favorable para que la red lea el texto. Un script no vale
porque la cubeta está mezclada, cada unidad cae en una pose y hay que elegir por la frase.

**7. Tarea completa y guion.** **Tarea declarada: «un pedido de dos referencias»** (≤ 40 s), de la cubeta a la
rampa. Cinco pedidos seguidos, **elegidos por el jurado**; la rampa saca el producto del área del brazo, así que la
escena se repone sola y la persona empaqueta sin entrar.
- 0:00 Frase. Un juez dice su nombre y elige: «jabón y té». Entra «Pedido #1 · [nombre]».
- 0:10 Monta la caja y estampa el logo. A la vez el robot coge y suelta las dos referencias.
- 0:50 **Momento:** levanta la vista con tinta en los dedos y su pedido le ha llegado rodando a la mano.
- 1:00-3:30 Pedidos 2 a 5, dictados por otros jueces; el primero cierra y etiqueta su paquete y **se lo lleva**.
- Recuperación: reagarre autónomo; si el contador de la rampa no suma, se repite la orden dentro del tiempo. Un
  producto equivocado es un fallo que se cuenta y se enseña en la matriz de confusión del punto 9.

**8. Escalera.** N1 (sáb 12:00): 2 referencias desde cubeta mezclada, ≥ 5/10. N2 (sáb 20:00): 4 referencias, voz,
contador de rampa, 4/5 pedidos en ensayo. N3 (dom): pedidos de tres, distractores nunca vistos en la cubeta.

**9. Fiabilidad y datos.** Gesto más difícil: coger la referencia pedida cuando otra la toca; soltar con ±5 cm.
Diez agarres para 5/5: si el sábado a las 20:00 el agarre suelto no llega a 9/10, la tarea declarada pasa a
«pedido de una referencia». Plan B: un ACT por referencia y el LLM elige. **Historia de datos (20 pt):** ~200
episodios (50 por referencia, 5 posiciones); **matriz de confusión frase × objeto cogido**, que prueba que la red
lee el texto; SmolVLA multitarea frente a cuatro ACT; ronda de corrección con las oclusiones que fallaron.

**10. Jueves.** Impresión ~9 h: rampa en dos tramos (6), almohadillas TPU (2), sello de logo en TPU (1).
Electrónica: ESP32 + reed o barrera + LED (hecho o sencillo). Comprar: ~12 cajas, papel, tinta, ~25 unidades de
producto, etiquetas. Reutiliza todo el software.

**11. Puntos débiles.** Con cuatro referencias conocidas, un jurado de Ikerlan o Automach puede decir «eso es
visión clásica y un script»: la respuesta es la cubeta mezclada y los distractores, y hay que tenerla medida. Dos
productos los coge una persona en 5 s: el valor es el tiempo en paralelo. Es el más cercano a lo rechazado (Repón,
Pila Sabia) y a GreatAkihabara; tema de envíos vecino de Flip & Ship. El criterio 1 es discutible.

**12. Autoevaluación (§9).** Demo 21/30 · datos 15/20 · dificultad 11/15 · utilidad 10/15 · innovación 5/10 ·
presentación 8/10 = **70**.

---

## Concepto 3 · CALIBRE, el mozo del puesto de verificación

**1. Frase.** «Tú mides y decides; el robot te pone la pieza, apunta la medida y aparta la mala.»

**2. Usuario real.** Quien verifica un lote en un taller pequeño de mecanizado o impresión 3D: calibre en una
mano, pieza en la otra, y suelta algo para apuntar y para separar rechazos. Andoni lo hace con sus piezas. Queja y
tiempos: [sin fuente]; llamar el jueves a un taller de Bizkaia o a un centro de FP. Es el mundo del jurado.

**3. Reparto.** Persona: mide dos cotas con calibre digital y las dicta. Robot: trae la pieza del cajón a granel
al plato y, tras el veredicto, la lleva a la bandeja verde o a la caja roja. Programado: voz → número, tolerancia.

**4. Referencia de physical AI.** Carga de útiles y atención de puestos (Figure en BMW, AgiBot) y coger a granel
con variedad [H, directrices §5]. Atención robotizada de máquinas de medir: [sin fuente; sin métrica].

**5. Escena tal cual (60 × 40 cm).** Cajón de 25 × 18 cm con 12 piezas impresas de 3 referencias (escuadra ~40 ×
30 × 25 mm, casquillo ~Ø30 × 30 mm, carcasa ~50 × 40 × 30 mm; 15-40 g), sueltas. Tres van un 2 % grandes: iguales
a la vista, solo el calibre las caza. Plato de medida Ø120 mm en el borde del alcance, con aro de LED verde o rojo.
Bandeja verde de 20 × 15 cm y caja roja de 15 × 15 cm con embudo. Calibre digital de 150 mm.

**6. Órdenes del VLA.** Mínimo: `Put the next part on the measuring plate.` · `Move the part from the plate to the
green tray.` Extra: `Move the part from the plate to the red box.` Cambia origen y destino; el aro de LED hace
visible el destino. Un script no vale porque hay que coger a granel tres formas mezcladas.

**7. Tarea completa y guion.** **Tarea declarada: «pieza verificada»** = del granel al plato y, con el veredicto,
del plato a su destino (≤ 40 s de robot). Cinco piezas seguidas. La mano de la persona solo entra al plato con el
brazo aparcado y el aro en blanco: **hay que preguntar al mentor si eso cuenta como «sin tocar»**.
- 0:00 Frase. Un juez coge el calibre. 0:15 Pieza al plato; mide, dicta «forty point one»; aro verde; a la bandeja.
- 1:30 **Momento:** dicta «forty point nine», aro rojo, y el robot aparta la pieza mala que no podía ver.
- 3:00 Informe con su nombre por QR. Recuperación: se repite la orden si el plato sigue ocupado.

**8. Escalera.** N1: granel → plato → bandeja verde, ≥ 5/10. N2: caja roja con aro, voz, informe. N3: lote de 20.

**9. Fiabilidad y datos.** Gesto más difícil: coger a granel sin atascos (pocas piezas, EVA). Plan B: un ACT por
orden. Riesgo: números por voz sin wifi. **Datos:** ~150 episodios; curva de acierto según piezas en el cajón;
ACT frente a SmolVLA; prueba con una cuarta pieza no vista. Historia correcta pero corta.

**10. Jueves.** Impresión ~11 h: 12 piezas (6), plato con LED (2), embudo (1), almohadillas (2). ESP32 + aro LED.

**11. Puntos débiles.** Lo más útil (apuntar por voz) no necesita robot. Parece un clasificador y recuerda a la
celda industrial que el mismo jurado dejó sin premio. La persona mete la mano en el plato. Momento pequeño.

**12. Autoevaluación (§9).** Demo 18/30 · datos 12/20 · dificultad 9/15 · utilidad 10/15 · innovación 5/10 ·
presentación 6/10 = **60**.

---

## Comparación y recomendación

| | TANDA | PEDIDO | CALIBRE |
|---|---|---|---|
| Tarea completa declarada | «Siguiente»: sale uno, entra otro | Pedido de dos referencias | Pieza verificada |
| Movimientos aprendidos para 5/5 | 10 (repliegue: 5) | 10 (repliegue: 5) | 10 |
| Quién repone la escena | Nadie: cola y caja | Nadie: la rampa lo saca | La persona, en el plato |
| Historia de datos | Vistos frente a nuevos; cambio de luz | Matriz frase × objeto | Densidad del cajón |
| Qué se lleva el juez | Fotos y anuncio de su objeto | Un paquete con producto real | Un informe |
| Nota (§9) | 73 | 70 | 60 |

**Defendería TANDA**, con PEDIDO como repliegue. Razones: es la dirección elegida por el usuario; es la única con
las manos de verdad bloqueadas; ante un jurado de automatización que ya vio ganar a MSN, la variedad de objetos y
la tabla «vistos frente a nuevos» responden mejor a «eso es un script» que cuatro referencias conocidas; y el
cambio de luz forma parte del trabajo, justo lo que la rúbrica nombra como dificultad. PEDIDO puntúa más en los
30 de la demo y comparte usuaria, pinza y software. Antes de decidir: una llamada a una vendedora real, diez
minutos de prueba del reflector con el móvil, y preguntar al mentor el viernes si las órdenes pueden encadenarse
por programa dentro de un intento y si la persona puede dictar por voz durante los 5 intentos.
