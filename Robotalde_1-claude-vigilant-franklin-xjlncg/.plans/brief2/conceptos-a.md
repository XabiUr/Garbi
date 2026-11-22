# Conceptos A · lente «me falta una mano» (19-11-2026)

Generador A. Entrada: [directrices-necesidad.md](directrices-necesidad.md) y apartados 1, 2, 6 y 8 de
[../brief/directrices.md](../brief/directrices.md). Medidas y pesos marcados «medir» se comprueban el jueves: no
se inventan. Los precios y citas llevan su URL; lo que viene de un extracto de buscador se dice.

## Situaciones miradas y descartadas

| Situación «me falta una mano» | Apaño de hoy | Motivo del descarte |
|---|---|---|
| Soldar dos cables en empalme | Manos auxiliares con cocodrilos | Soldadura: se confunde con MSN (crit. 4); cables finos y deformables; calor cerca. |
| Placa en soporte para medir con dos puntas | Pinza, punta en la boca | Ya evaluado (Sondas libres): «un soporte de 20 € no se cae»; vecino de MSN. |
| Atornillar una escuadra o bisagra presentada | Sargento, otra persona | Empuje axial del destornillador: fuerza (crit. 2). |
| Aguantar un lateral de mueble | Otra persona, sargentos | Peso y tamaño fuera del SO-101. |
| Lijar o desbarbar una pieza pequeña | Tornillo de banco | Fuerza y el servo cede; un tornillo de banco lo hace mejor. |
| Termorretráctil con pistola de calor | Pinzas, tornillo de banco | Calor junto al PLA del robot; cable fino. |
| Coser cuero a punto de silla | Caballete de costura («stitching pony») | Pieza fina y deformable; un caballete pasivo basta. |
| Bolsa abierta para echar tornillería | Meter la bolsa en un vaso | Bolsa deformable; truco gratuito que ya funciona. |
| Cerrar caja con cinta | Rodilla, pistola de cinta | Presionar solapas es fuerza; vecino de Flip & Ship. |
| Móvil con el tutorial donde miras | Soporte de cuello de cisne, apoyarlo en una taza | Mismo patrón que MSN (llevar algo a donde trabajas): el jurado vería un clon. |
| Foto de producto: sujetar el objeto y la cámara | Masilla de museo, plastilina, hilo | Con trípode las manos quedan libres (prueba 4 floja) y la pinza sale en la foto. La masilla resuelve el caso estático ([Ganoksin](https://orchid.ganoksin.com/t/jewelry-holder-for-photos/17526)). |
| Esmaltar cerámica por inmersión | Pinzas de esmaltar | Líquido (crit. 6 y límites del SO-101). |
| Tensar el cable de freno de la bici | «Cuarta mano» de taller | Fuerza. |
| Medir y marcar un listón largo | Gancho de la cinta, un clavo | El gancho ya lo resuelve; alcance del brazo corto. |
| Tela en bastidor para bordar | Bastidor | Bastidor pasivo barato; tela deformable. |

Patrón de lo que sobrevive: **no basta con sujetar quieto** (un apaño pasivo lo hace igual de bien); el robot entra
cuando hay que **cambiar lo que se sujeta o cómo se presenta sin que la persona suelte lo que tiene en las manos**, o
cuando tocar la pieza es justo lo que no se puede hacer (pintura fresca, cola, un cable plano tirante).

---

## A1 · Mango · «Para pintar la otra cara tengo que tocarla, y está fresca»

1. **Frase:** «Pinto con aerógrafo o spray; para girar la pieza o la cojo con los dedos y me pringo, o espero a que
   seque.»
2. **Pruebas.** *Vivida:* cualquiera que haya pintado con spray una pieza pequeña ha acabado con los dedos pintados o
   la pieza pegada al cartón. *Una frase:* la de arriba. *Apaño:* pegar la pieza a un palillo con masilla, cocodrilos
   en brochetas, cinta de doble cara, pinzas de la ropa ([FineScale](https://forum.finescale.com/t/holding-small-parts-for-airbrushing/234228));
   mango comercial Citadel Painting Handle, 6-8 £ ([Gigante](https://gigante.co.uk/products/citadel-colour-painting-handle));
   plato giratorio para spray ([Make:](https://makezine.com/article/workshop/skill-builder-spray-paint-techniques/)).
   *Segunda persona:* la que sujeta la pieza por el palo y la gira cuando se lo pides, mientras tú no sueltas el
   aerógrafo.
3. **Quién y dónde:** modelismo y miniaturas, piezas impresas en 3D; retoque de pintura en taller. Mesa con cabina de
   cartón.
4. **Reparto:** la persona pinta (aerógrafo en una mano, la otra en el compresor o la máscara). El robot coge la pieza
   montada en su mango de un soporte, la presenta en la cabina, la voltea cuando se pide (giro de muñeca
   programado) y la deja secando.
5. **Órdenes:** `Bring an unpainted part` (coge del soporte una pieza gris, la que sea, y la lleva a la cabina) ·
   `Put the part on the drying rack` (de la cabina al secadero). Cambia **qué** coge (gris frente a pintada, se ve) y
   **adónde** va.
6. **Tarea declarada:** «trae una pieza sin pintar a la cabina y, tras pintarla, déjala en el secadero» (≤ 30 s de
   robot). Se repone sola: hay 5 piezas grises en el soporte y el secadero tiene 5 huecos.
7. **Escena:** 5-6 piezas reales (miniaturas o piezas impresas) pegadas en mangos cilíndricos Ø 30-40 mm (imprimir,
   ~1 h); soporte de entrada y secadero con huecos en embudo (imprimir, ~3 h); cabina de cartón con filtro. Peso del
   conjunto mango + pieza: medir (objetivo < 150 g).
8. **Fiabilidad:** el gesto difícil es meter el mango en el hueco del secadero (embudo, ±1 cm). Coger un cilindro de
   30-40 mm es de lo más fiable del catálogo. Plan B: un ACT por orden y el LLM elige.
9. **Momento memorable:** el juez pinta con el aerógrafo, dice «dale la vuelta» y la pieza gira sin que nadie la
   toque; al final, una fila de piezas de colores secando que antes eran grises.
10. **Débiles:** pintar en la sala del evento (pedir permiso; si no, acrílico al agua de baja presión o pintura de
    tiza lavable); hay que tapar el robot con plástico; el giro es script (honesto: híbrido). Si el jurado piensa
    «un palillo en un corcho hace lo mismo», la respuesta es el giro sin tocar y el secadero. No se parece a MSN.

---

## A2 · Aguanta mientras pega · «Pegar un asa rota necesita tres manos»

1. **Frase:** «Una mano pone la cola, otra el trozo, y la taza se me va rodando; luego hay que aguantar quieto.»
2. **Pruebas.** *Vivida:* todos han pegado algo roto y han terminado con los dedos pegados o la pieza caída. *Una
   frase:* sí. *Apaño:* cinta de carrocero alrededor del asa, caja con arena para que la gravedad sostenga
   ([iFixit](https://www.ifixit.com/Guide/Repairing+a+Broken+Coffee+Mug+Handle/40151),
   [Loctite](https://www.loctite-consumer.com.au/ideas/repair-diy-projects/how-to-fix-a-broken-mug-save-that-mug-from-the-rubbish-bin.html));
   una guía de Lepage pide aguantar las piezas «al menos 10 minutos» ([Lepage](https://lepage.ca/en/know-how/glue/how-to-fix-broken-ceramics-guide-to-ceramic-repairs.html)).
   *Segunda persona:* la que te sujeta la taza con la rotura hacia arriba mientras pones cola y trozo.
3. **Quién y dónde:** reparación (repair café, taller de restauración, cualquiera en casa); también pegado de piezas
   de plástico en taller. Banco con esterilla.
4. **Reparto:** la persona aplica la cola y coloca el trozo, y lo ajusta. El robot coge la taza por el borde (un dedo
   dentro, otro fuera), la orienta con la rotura arriba y la mantiene quieta; luego la deja en el secadero.
5. **Órdenes:** `Hold the cup with the break up` · `Put the cup on the drying stand`. Cambia la postura final y el
   destino. Extra (N2): `Hold the plate` con un segundo objeto roto distinto (cambia **qué** coge).
6. **Tarea declarada:** «coge la taza y preséntala con la rotura arriba en la zona de trabajo» y después «déjala en el
   secadero» (≤ 30 s de robot; el tiempo de fraguado no cuenta, se usa cola rápida). Se repone: 5 tazas iguales
   rotas en una bandeja, el secadero tiene 5 cunas en V.
7. **Escena:** tazas de café reales (taza pequeña, peso a medir; si pasan de ~300 g, tazas de espresso) con el asa
   cortada; cianoacrilato en gel; zona de trabajo marcada; secadero de cunas en V (imprimir, ~3 h).
8. **Fiabilidad:** pinza en el borde de una taza de cerámica lisa: riesgo de que resbale al girarla 90°. Dedos
   impresos con goma (Andoni) y tolerancia de cm en la postura. Plan B: ACT; plan C: la taza ya va en un aro impreso
   con asa que la pinza coge (pierde algo de «tal cual»).
9. **Momento memorable:** el juez pega el asa con las dos manos mientras el robot sostiene la taza; al final se bebe de
   ella (agua, cuando fragüe).
10. **Débiles:** la prueba 4 es la más floja del lote: la arena hace la parte de «aguantar quieto»; el robot solo gana
    en el momento de las tres manos y al girar para ver el encaje. Tazas idénticas = poca variedad de datos. Sin
    parecido con MSN.

---

## A3 · Tira de aquí · «Para encintar el mazo, alguien tiene que aguantar el otro extremo»

1. **Frase:** «Encinto un mazo de cables: con una mano doy vueltas a la cinta y con la otra lo sujeto, pero el
   ramal suelto se me escapa.»
2. **Pruebas.** *Vivida:* quien ha cableado un coche, una moto, un cuadro eléctrico o una máquina. En la industria de
   automoción vasca el mazo se monta a mano sobre tableros. *Una frase:* sí. *Apaño:* tablero de clavos y horquillas
   (formboard), pinzas de cocodrilo, tornillo de banco por el conector, pedir a alguien que tire. En foros de
   restauración se cuenta que las operarias sujetaban el mazo con la mano izquierda para darle tensión cuando el ramal
   no estaba fijado (extracto del buscador, foro NCRS:
   [hilo](https://www.forums.ncrs.org/forum/technical-discussion-archives/5822-wiring-harness-wrapping); la página
   devuelve 403 y no se ha podido leer entera). Otro foro recomienda una «tercera mano» que sujete los cables
   ([DFK](https://dfkitcar.com/forum/threads/wiring-harness-tools.1688/)).
   *Segunda persona:* la que coge el conector del ramal que le dices y lo mantiene estirado.
3. **Quién y dónde:** cableado de mazos (prototipos, series cortas, restauración de vehículos, cuadros). Mesa de
   cableado.
4. **Reparto:** la persona encinta o pone bridas con las dos manos. El robot coge el conector del ramal pedido, lo
   lleva a su posición y lo mantiene; al terminar lo deja en su sitio.
5. **Órdenes:** `Hold the white connector` · `Hold the black connector`. Cambia **qué** coge: carcasas distintas a la
   vista, en posiciones que varían porque el mazo cae cada vez distinto (aquí un script con posiciones fijas no vale).
6. **Tarea declarada:** «coge el conector nombrado y llévalo a la marca de tensión» (≤ 20 s). Se repone: la persona
   suelta el mazo sobre la mesa de nuevo.
7. **Escena:** un mazo real de 3 ramales (cable de 0,5-1 mm² con cinta, conectores de automoción de carcasa gruesa,
   medidas a comprobar, objetivo 20-40 mm de ancho); cinta de tela; marcas de tensión en la mesa; peines impresos que
   guían el tronco (imprimir, ~2 h).
8. **Fiabilidad:** coger una carcasa de 20-40 mm que yace en posición variable: dentro de lo fiable. El riesgo es la
   **fuerza**: al encintar se tira del mazo y el servo cede unos mm. Mitigación: la marca de tensión es un tope impreso
   donde el robot apoya el conector, y bridas en vez de cinta si hace falta. Plan B: ACT por orden.
9. **Momento memorable:** el juez encinta mientras pide «ahora el negro» y el robot suelta uno y busca el otro entre el
   lío de cables.
10. **Débiles:** cables = objeto deformable; si el mazo se enreda, el conector puede quedar tapado; la tensión real de
    un operario es mayor que la que da el SO-101 (hay que decirlo). Parecido: kitting de cables en startups; no con
    MSN.

---

## A4 · Aguanta la tapa · «Al abrir el aparato, la tapa cuelga del cable plano y no tengo mano para ella»

1. **Frase:** «Abro el mando o el portátil y la tapa queda colgando del cable; con una mano la sujeto y con la otra no
   llego a soltar el conector.»
2. **Pruebas.** *Vivida:* cualquiera que haya abierto un portátil, un mando o un móvil. *Una frase:* sí. *Apaño:*
   apoyar la tapa «contra algo firme para no tener que sujetarla», o una goma elástica para que no tire del cable
   (guías de iFixit, recogidas en un espejo:
   [MacBook](https://wikipedia.jakami.de/content/ifixit_en_all_2023-04/Guide/Retina%2BMacBook%2B2016%2BLower%2BCase%2BAssembly%2BRemoval/97063);
   la frase de la goma viene de un extracto del buscador sobre otra guía, sin verificar). *Segunda persona:* la que te
   sostiene la tapa quieta mientras haces palanca con el spudger y las pinzas.
3. **Quién y dónde:** técnico de reparación de electrónica, repair café, mantenimiento de equipos. Banco antiestático.
4. **Reparto:** la persona abre el aparato, desconecta el cable con dos herramientas. El robot coge la tapa por el
   borde, la mantiene levantada cerca de la base sin tensar el cable, y al acabar la deja en la bandeja de piezas.
5. **Órdenes:** `Hold the cover up` · `Put the cover in the tray`. Cambia la postura y el destino; con tapas de varios
   aparatos (N2) cambia también qué coge.
6. **Tarea declarada:** «sostén la tapa levantada» y, tras desconectar, «déjala en la bandeja» (≤ 30 s de robot). Se
   repone: la persona vuelve a cerrar el aparato (el conector se reconecta en segundos).
7. **Escena:** un aparato real con cable entre mitades (mando de consola, altavoz, router; elegir el jueves uno que
   tengamos y medir tapa y cable); bandeja de piezas impresa (~2 h); calzo impreso que fija la base del aparato.
8. **Fiabilidad:** el gesto difícil es levantar la tapa sin pasar la longitud del cable: tolerancia de pocos cm según
   el aparato. Mitigación: elegir un aparato con cable holgado; si no, un cable de prácticas que se pueda romper sin
   drama. Plan B: ACT.
9. **Momento memorable:** el juez desconecta el cable con las dos manos y dice «ya»; la tapa se va a la bandeja.
10. **Débiles:** si el robot tira, rompe el cable delante del jurado; la tapa está a centímetros de las manos del juez
    (manos dentro del alcance del brazo, igual que en Sondas libres); el apaño de la caja o la goma es gratis. Sin luz:
    no se confunde con MSN, pero es del mismo banco de electrónica.

---

## Lectura rápida

- **Más fuerte en necesidad:** A1 (pringarse los dedos de pintura lo ha vivido todo el mundo) y A3 (industria vasca).
- **Más fiable:** A1 (cilindros y embudos). **Más arriesgado:** A4 (cable que se rompe) y A3 (fuerza de tensión).
- **Prueba 4 más floja:** A2 (la arena hace casi todo).
