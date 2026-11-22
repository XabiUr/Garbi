# Conceptos C · lente «el apaño que la gente ya compra o fabrica» (19-11-2026)

Generador C. Parto de productos y apaños que ya existen y de las quejas sobre ellos. Medidas y pesos de la escena
son de diseño o aproximados: hay que pesarlos y medirlos el viernes.

## Productos y quejas que miré (con URL)

| Apaño / producto | Precio | Queja o prueba de necesidad | URL |
|---|---|---|---|
| Manos auxiliares genéricas | — | «The generic "helping" hands need to die» (sneakypoo); «unstable at the worst of times» (Silis); «usually moves as you do that then you need to fine adjust» (ftkalcevic) | https://hackaday.com/2017/03/12/ask-hackaday-helping-hands |
| Manos auxiliares baratas | — | Según la búsqueda, se caen y «we tend to buy them and don't use them» | https://hackaday.com/2017/05/12/cheap-helping-hands-just-add-time |
| Manos auxiliares impresas (Soldering Helping Hands Remixed³) | gratis | Espejo de Thingiverse: 1.495 likes, 4.896 descargas (cifra del espejo, no verificada en Thingiverse) | https://harktech.co.uk/m/thingiverse/4763624 |
| Soporte cenital de móvil (artículo del fabricante Ulanzi) | — | «Arm slowly droops after you frame the shot»; «Suction base holds briefly, then releases» | https://www.ulanzi.com/blogs/knowledges/keep-overhead-phone-mount-from-falling |
| Lamicall cuello de cisne LS05-W | 55,59 $ | Un dueño: «shakes easily if touched» con el brazo extendido (resumen de búsqueda, una sola reseña) | https://www.desertcart.us/products/145646665-phone-holder-gooseneck-mount-compatible-with-4-7-smartphones-desktops.md · https://thewearify.com/best-gooseneck-cell-phone-holder/ |
| Pedir a otra persona que aguante la aspiradora al taladrar | gratis | «drilling becomes a two person job» (Marianne); «if you don't have a second person to hold the vacuum» (Sarah K) | https://www.younghouselove.com/tape-tricker/comment-page-2 |
| Ídem, guía de oficio | — | «it often requires a helper to hold the nozzle» | https://www.journeymanhq.com/?p=718962 |
| Pósit doblado bajo el agujero (apaño de cero euros) | gratis | Truco publicado por Make e Instructables | https://makezine.com/article/workshop/use-a-post-it-to-catch-drill-dust |
| Soporte magnético de manguera (Woodfan) / brazo Festool CT-ASA | 64,23 zł / 179 $ | Se venden soportes para que la boquilla «se quede» donde se taladra | https://woodfan.pl/en/workshop/dust-extraction-and-extraction/screwed-on-holder-for-extraction-hose-detail.html · https://www.woodcraft.com/products/festool-boom-arm-set-ct-asa-flx-w |
| Sujetar piezas mientras seca el pegamento (Robotime, fabricante de kits) | — | «Delicate DIY parts can shift easily while glue is drying»; propone cajas, gomas, botes de pintura como calzos | https://www.robotimeonline.com/pages/how-to-hold-small-parts-while-glue-dries |
| Pinzas de modelismo Expo 6 pc / Modelcraft PCL3000 | 2,95 £ / 9,89 £ | Producto barato que existe solo para «sujétame esto mientras seca» | https://modelrealm.co.uk/products/6pc-micro-clamp-set · https://www.scalemodelshop.co.uk/nylon-hobby-clamps-6-x-50mm-3-x-75mm-modelcraft-pcl3000-p16265 |
| Ayudante que sostiene el reflector (el «VAL», *voice-activated light stand*) | sueldo | «The photographer may ask you to move closer or angle the reflector differently» | https://www.slrlounge.com/5-responsibilities-of-photography-lighting-assistants/ · https://imaging-resource.com/news/2016/02/21/the-trick-to-wide-angle-photography-with-flash-is-a-voice-activated-light-s |
| Westcott 302 Reflector Holder | 59,90 $ | Producto que sustituye al ayudante | https://markertek.com/product/pb-302/westcott-302-reflector-holder-for-5-in-1-reflectors |
| Mango de pintura Citadel | 6,50 € | Más cómodo que corchos o botes; «minimize jitter» | https://www.chaosbunker.de/en/2018/01/29/review-citadel-painting-handle |
| QuadHands (manos con base magnética) | — | Reseñas positivas; quejas solo de las patas de goma | https://kk.org/cooltools/quadhands-helping-hands/ |

## Descartes tras pasar las cuatro pruebas con dureza

- **Sujetar la placa al soldar (manos auxiliares):** la queja más común de todas, pero es el banco de MSN; se confunde
  con él (eliminación 4).
- **Brazo con lupa:** suele llevar luz y pide precisión de mm al encuadrar; se acerca a MSN.
- **Girar la miniatura mientras se pinta:** el apaño es un mango de 6,50 €, no una segunda persona; nadie pide «sujétame
  la mini». Falla la prueba 4, y el temblor del brazo extendido se notaría en el pincel.
- **Posicionador de soldadura:** fuerza y peso fuera del SO-101.
- **Pinzas de sargento en carpintería:** el valor es la fuerza de apriete (eliminación 2).

---

## C1 · Aspira — «Aguántame la aspiradora mientras taladro»

1. **Frase:** cada vez que taladras necesitas a alguien que te ponga la boquilla debajo, o lo llenas todo de serrín.
2. **Pruebas:** (1) Todo el que ha colgado un cuadro lo ha vivido. (2) Taladrar con una mano en la pieza y otra en el
   taladro deja la aspiradora sin mano. (3) Apaño: «drilling becomes a two person job» (Young House Love) o un pósit
   doblado (Make, gratis); productos: soporte magnético Woodfan 64,23 zł, brazo Festool 179 $ (URL en la tabla).
   (4) El robot es literalmente la segunda persona de esos comentarios.
3. **Quién y dónde:** carpintero aficionado o técnico de mantenimiento, banco con tablero de pino o DM.
4. **Reparto:** la persona sujeta la tabla y taladra; el robot coloca la boquilla junto a la marca y la mantiene.
5. **Órdenes:** `Hold the nozzle at the red mark.` / `Hold the nozzle at the blue mark.` Cambia **adónde** (dos marcas
   de color en la tabla, que la persona coloca en un sitio distinto cada vez).
6. **Tarea (5 intentos):** el juez dice el color; el robot coge la boquilla de su soporte y la deja a 2-3 cm de la marca
   (≤ 20 s); la persona taladra; el robot devuelve la boquilla. Reponer: tabla nueva o girada, boquilla al soporte.
7. **Escena:** aspirador de taller real; boquilla impresa con mango de 40 mm (≈ 60 g, a pesar); el último metro de
   manguera colgado de un gancho alto para que el robot no cargue su peso; tablas de 30×20 cm con pegatinas de color;
   soporte en V para la boquilla. Imprimir: boquilla, mango, soporte en V, gancho (≈ 4 h).
8. **Fiabilidad:** gesto difícil, dejar la boquilla junto a la marca con ±1,5 cm (sobra: la aspiración tolera eso).
   Plan B: un ACT por color, el LLM elige.
9. **Momento memorable:** el juez taladra y no cae ni una viruta a la mesa. El juez hace de «la persona sola en casa».
10. **Puntos débiles:** el tirón de la manguera puede mover el brazo (probar el gancho el viernes); ruido del
    aspirador para la voz (pulsador o tablet de respaldo); taladro cerca de la pinza (la boquilla es de plástico).
    No se parece a MSN. Script frente a VLA: la marca cambia de sitio, así que un script fijo no llega.

## C2 · Mientras seca — «Sujétame esto mientras pega»

1. **Frase:** pegas dos piezas y te quedas un minuto con las manos atrapadas esperando a que agarre.
2. **Pruebas:** (1) Cualquiera que haya pegado una maqueta, una taza o un mueble. (2) No puedes soltar ni seguir.
   (3) Apaño: gomas, cajas y botes como calzos (Robotime); pinzas Expo 2,95 £ y Modelcraft 9,89 £; o «sujétamelo».
   (4) El robot aguanta y la persona sigue con la siguiente pieza.
3. **Quién y dónde:** modelista o maquetista (kits de madera, aviones, casas en miniatura), mesa de montaje.
4. **Reparto:** la persona pone el pegamento y encaja la pieza pequeña con precisión; el robot coge la pieza grande de la
   bandeja, la presenta a altura de trabajo y la mantiene quieta mientras seca.
5. **Órdenes:** `Hold the fuselage.` / `Hold the wall panel.` Cambia **qué objeto** (formas y colores distintos).
6. **Tarea:** el juez pide una pieza; el robot la coge de la bandeja y la deja en la pose de presentación (≤ 20 s);
   la persona pega; el robot aguanta 30 s y la deja en el secadero. Reponer: piezas de repuesto en la bandeja.
7. **Escena:** fuselaje de maqueta grande o pieza impresa de 40 mm de grueso (< 80 g); panel de casita de madera con
   listón de agarre de 30 mm; cola blanca rápida o cianoacrilato con gel. Imprimir: bandeja con alojamientos en V,
   secadero, piezas de repuesto (≈ 5 h).
8. **Fiabilidad:** coger de un alojamiento en V es lo más fiable del SO-101. Riesgo: al apretar la pieza contra la
   otra, el servo cede unos mm; se pega con poca presión y se usa gel. Plan B: ACT por pieza.
9. **Momento memorable:** la persona pega con las dos manos mientras el robot sostiene y, sin soltar, pide la siguiente.
   El juez elige qué pieza.
10. **Puntos débiles:** el tiempo de secado alarga la demo (usar gel rápido); «sujetar quieto» parece poco; la
    precisión del encaje queda en la persona (es lo correcto, pero hay que decirlo). Sin parecido con MSN.

## C3 · Encuadre — «Grábame las manos, que el soporte se cae»

1. **Frase:** quieres grabar lo que haces y el soporte del móvil se dobla, tiembla o apunta donde no es.
2. **Pruebas:** (1) Todo el que ha grabado un tutorial, documentado una reparación o enviado un vídeo al soporte técnico.
   (2) Tienes las manos en la pieza, no en el móvil. (3) Apaño: cuello de cisne Lamicall 55,59 $ («shakes easily if
   touched»), o el propio fabricante Ulanzi: «Arm slowly droops after you frame the shot»; o apoyar el móvil en una taza.
   (4) El robot es el compañero que graba y reencuadra cuando se lo pides, sin tocar el móvil con las manos sucias.
3. **Quién y dónde:** creador de tutoriales de bricolaje o técnico que documenta un procedimiento en el banco.
4. **Reparto:** la persona trabaja (monta, cablea, atornilla); el robot sostiene el móvil y apunta al objeto pedido.
5. **Órdenes:** `Point the camera at the green tray.` / `Point the camera at the orange tray.` Cambia **adónde**
   (bandejas que la persona mueve por la mesa).
6. **Tarea:** el juez pide una bandeja; el robot orienta el móvil hasta encuadrarla (≤ 15 s); la pantalla del móvil se
   proyecta para que todos vean el plano. Reponer: mover las bandejas a otra posición.
7. **Escena:** móvil real (≈ 180-200 g) en una funda impresa con mango de 40 mm; dos bandejas de 15×10 cm de colores;
   el brazo trabaja bajo y recogido para no temblar. Imprimir: funda-mango, bandejas (≈ 3 h).
8. **Fiabilidad:** el éxito se mide «la bandeja sale en el plano», tolerancia de varios cm. Riesgo: peso cerca del
   límite y vibración en el vídeo. Plan B: ACT por bandeja; móvil más ligero o webcam.
9. **Momento memorable:** el juez mueve la bandeja y el plano la sigue al decir la orden; todos lo ven en la pantalla.
10. **Puntos débiles:** un trípode fijo resuelve muchos casos (la ventaja real es reencuadrar sin tocar nada); el
    robot no ve por la cámara del móvil, encuadra por la de la escena; es un gesto de orientación, menos vistoso que
    coger. Ni luz ni soldadura: no se parece a MSN.

## C4 · Rebote — «Muévete el reflector un poco a la izquierda»

1. **Frase:** en fotos de producto alguien tiene que aguantar la cartulina blanca y moverla cuando se lo pides.
2. **Pruebas:** (1) Todo el que ha hecho fotos para vender algo ha apoyado una cartulina en un bote. (2) Una mano en la
   cámara y otra en el producto; el reflector se queda sin mano. (3) Apaño: el ayudante («VAL»: «The photographer may
   ask you to move closer or angle the reflector differently», SLR Lounge) o un soporte Westcott 302 de 59,90 $.
   (4) El robot es el ayudante que mueve el reflector a la orden.
3. **Quién y dónde:** artesano o tienda online que fotografía su producto en un banco con fondo blanco (enlaza con la
   dirección «estudio de fotos de producto» que eligió el usuario).
4. **Reparto:** la persona coloca el producto y dispara la cámara; el robot pone la cartulina en el lado pedido.
5. **Órdenes:** `Bounce light from the left.` / `Bounce light from the right.` Cambia **adónde**, relativo a un producto
   que cambia de sitio.
6. **Tarea:** el juez pide un lado; el robot coge la cartulina de su soporte y la deja de pie a ese lado del producto,
   a ~10 cm (≤ 20 s); la persona dispara. Reponer: cartulina al soporte, producto a otra posición.
7. **Escena:** cartulina pluma blanca 20×30 cm (≈ 40 g) con mango impreso de 40 mm; producto real (taza o caja);
   fondo de cartulina; un foco fijo de estudio (no lo mueve el robot). Imprimir: mango, soporte, peana (≈ 3 h).
8. **Fiabilidad:** tolerancia de varios cm y de ángulo; riesgo de que la cartulina, al ser grande, roce el producto.
   Plan B: ACT por lado.
9. **Momento memorable:** dos fotos en pantalla, con y sin rebote; la sombra desaparece al decir la orden.
10. **Puntos débiles:** **va de luz**: aunque no sea soldadura ni linterna, el jurado puede verlo cerca de MSN; el
    efecto depende de la iluminación de la sala; la persona trabaja con la cámara, menos «manos en la pieza» que C1-C2.
