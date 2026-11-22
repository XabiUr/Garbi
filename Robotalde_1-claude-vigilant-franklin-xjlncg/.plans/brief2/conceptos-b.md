# Conceptos B · lente «manos sucias, enguantadas o en peligro» (19-11-2026)

Generador B. Entrada: [directrices-necesidad.md](directrices-necesidad.md) y apartados 1, 2, 6 y 8 de
[../brief/directrices.md](../brief/directrices.md). Idea común: **el robot es la segunda persona con las manos
limpias.** No se inventan cifras: donde falta un precio o un dato, se dice.

## Situaciones miradas y descartadas

| Situación | Motivo del descarte |
|---|---|
| Sujetar el clavo mientras se martillea | Impacto sobre la pinza y el servo; fuerza (elim. 2). |
| Pasar páginas del cuaderno o del manual con guantes | Papel deformable; gesto de mm (elim. 2). |
| Tocar la pantalla del móvil por la persona (contestar, pasar paso) | Precisión de mm; un script con coordenadas fijas hace lo mismo (elim. 2 y 3). |
| Sujetar el vaso de epoxi mientras se mezcla | Líquido en la pinza junto a la persona (elim. 6). |
| Grabado de PCB con cloruro férrico: que el robot sumerja la placa | Líquido corrosivo en un evento; peligro (elim. 6). |
| Sujetar la miniatura mientras se pinta a pincel | El pincel empuja y el servo cede milímetros; el pintor apoya las muñecas y lo hace mejor solo. |
| Torno de cerámica con manos de barro | Mismo gesto que el concepto 1, con agua y barro salpicando al robot; jurado vasco poco familiarizado (prueba 1 floja). |
| Dar un guante limpio, papel o tela de fibra de vidrio | Deformables (límites del SO-101). |
| Pigmentos de resina por color | Los botes se manchan igual al usarlos: el robot no evita la suciedad; necesidad floja (queda como variante del 1). |
| Cola caliente: sujetar mientras enfría | Es de la lente «sujétame esto», no de manos sucias; calor cerca. |
| Tatuaje, peluquería, cocina casera, quirófano | Servicio, doméstico o médico: fuera de U6. |

**Pruebas de necesidad encontradas (comunes a varios conceptos):**
- Normas de laboratorio universitarias: no tocar pomos, teléfonos, teclados ni ascensores con guantes; «política de
  un guante» (una mano enguantada para la muestra, la otra desnuda para lo común):
  [Berkeley EHS](https://ehs.berkeley.edu/node/1149), [Rochester](https://safety.rochester.edu/safetyinfo/gloveuse.html),
  [Cornell](https://ehs.cornell.edu/book/export/html/1027), [LCSB «no toques el móvil con guantes»](https://howto.lcsb.uni.lu/lab/gloves).
- Resina: «mantén el móvil lejos de los guantes pegajosos» y «cambia de guantes a menudo»
  ([ArtResin, móvil](https://www.artresin.com/blogs/artresin/3-ways-your-smartphone-can-help-you-resin),
  [ArtResin, taller](https://www.artresin.com/blogs/artresin/resin-art-workspace-set-up-how-to-stay-clean-organized-ready-to-pour)).
- Precedente de mercado e investigación del «pasador de herramienta por voz»: enfermera instrumentista robótica con
  VLA ([RoboNurse-VLA, arXiv 2409.19590](https://arxiv.org/html/2409.19590v1)) y cobot por voz
  ([CDBME 2021](https://www.degruyterbrill.com/document/doi/10.1515/cdbme-2021-1035/pdf)).

---

## 1 · «Pásame la del 10» — el ayudante limpio del mecánico

1. **Frase:** «Tengo las manos negras de grasa y la pieza a medio sacar: pásame la llave, no voy a ir al carro
   a pringarlo todo.»
2. **Pruebas.** *Vivido:* cualquiera que haya cambiado una cadena de bici o el aceite del coche. *Una frase:* la de
   arriba. *Apaño:* gritar «¡pásame la del 10!» a alguien, limpiarse en el trapo cada vez, dejar las herramientas
   desparramadas encima del motor o en una bandeja magnética (producto barato; precio no verificado). *Segunda
   persona:* es literalmente el ayudante del taller, el mismo papel que la instrumentista del quirófano
   (precedente RoboNurse-VLA, arriba).
3. **Quién y dónde:** mecánico de bicis o aficionado al coche, en un banco con un buje, un desviador o un carburador
   desmontado.
4. **Reparto:** la persona sujeta y desmonta con las dos manos sucias; el robot coge la herramienta pedida de la
   bandeja de herramientas limpias y la deja en la «bandeja de mano» junto a la pieza; al oír «llévatela», coge la
   usada de esa bandeja y la deja en la bandeja del trapo.
5. **Órdenes:** `Bring the wrench` / `Bring the screwdriver` (cambia **qué objeto**, distinto a la vista).
   Extra: `Take the tool away`.
6. **Tarea declarada (≤ 30 s):** «Bring the wrench» con las herramientas en posiciones distintas en la bandeja; acierto
   = la funda queda dentro de la bandeja de mano. Reposición: la persona devuelve la funda a la bandeja de
   origen en cualquier hueco libre (no entra en el brazo; la variación de posición es la que pide el VLA).
7. **Escena:** 3-4 herramientas reales (llave fija, destornillador, llave Allen en T, desmontables) metidas cada una
   en una **funda impresa** de 40×40 mm de sección con asa arriba (herramienta + funda < 250 g); bandeja de origen
   de 30×20 cm; bandeja de mano con embudo en V; pieza real sucia (buje o desviador). Impresión: fundas y bandejas,
   ~6-8 h.
8. **Fiabilidad:** gesto más difícil = coger la funda por el asa (±1 cm gracias al asa ancha) y soltarla en el
   embudo (±2 cm). Plan B: un ACT por herramienta y el LLM elige cuál ejecutar.
9. **Momento memorable:** el juez se pone un guante untado de grasa, desmonta algo y pide la herramienta en
   castellano; el robot se la deja al lado. El juez cambia de sitio las fundas antes de pedir.
10. **Débil:** con funda la herramienta ya no es «tal cual» del todo; un dispensador fijo con script podría hacer lo
    mismo si las posiciones fueran fijas (hay que defender la bandeja desordenada); RoboNurse-VLA ya existe como
    investigación (sirve de referencia, quita novedad). Sin relación con MSN más allá de «ayudante de banco».

---

## 2 · «Una mano limpia» — el que trae y lleva fuera de la cabina

1. **Frase:** «Con los guantes contaminados no puedo tocar el armario, la puerta ni el cuaderno; cada vez que me
   falta algo, me quito un guante.»
2. **Pruebas.** *Vivido:* todo el que ha hecho prácticas de laboratorio en la universidad (jurado de EHU y centros
   tecnológicos). *Una frase:* sí. *Apaño:* la **«política de un guante»** escrita en las normas de seguridad de
   varias universidades (Berkeley, Rochester, Cornell, enlaces arriba): quitarse un guante para tocar lo común,
   pedírselo a un compañero o cambiar de guantes cada vez. *Segunda persona:* el compañero que «te acerca el
   frasco» mientras trabajas en la cabina.
3. **Quién y dónde:** técnico de laboratorio o estudiante en una mesa de química o biología, trabajando dentro de una
   zona marcada (bandeja de trabajo o cabina).
4. **Reparto:** la persona pipetea, mezcla y anota dentro de la zona sucia; el robot, desde la zona limpia, trae el
   frasco cerrado o la gradilla pedida a la bandeja de paso y, terminado, lo devuelve a la estantería.
5. **Órdenes:** `Bring the blue cap bottle` / `Bring the tube rack` (objetos distintos). Extra: `Put the bottle back`.
6. **Tarea declarada:** traer el objeto nombrado, colocado en una posición distinta de la estantería en cada intento,
   hasta la bandeja de paso; acierto = dentro del alojamiento. Reposición: la persona deja el objeto en la estantería
   con la mano limpia, en otra posición.
7. **Escena:** frascos de laboratorio de 100 mL con tapón de color (Ø ~55 mm; llenos de agua o vacíos, siempre
   cerrados, < 250 g), gradilla de tubos con asa impresa, estantería baja de dos alturas y bandeja de paso con
   alojamientos en V, impresos (~6 h).
8. **Fiabilidad:** el Ø de un frasco de 100 mL roza el máximo de la pinza; usar frascos de 50 mL o un collarín impreso.
   Tolerancia ±1 cm en el alojamiento. Plan B: ACT por objeto.
9. **Momento memorable:** el juez se pone guantes «contaminados» (pintados con tinta UV o fluorescente); al final se
   ilumina la mesa: la tinta solo está en la zona sucia, nunca en la estantería.
10. **Débil:** se parece a Medra y a la reposición de laboratorio (mercado real, pero tema visto); en la vida real el
    frasco que se usa acaba tocado con guantes igualmente; líquidos (cerrados) cerca de la persona: enseñar siempre
    tapones a rosca. Lejos de MSN.

---

## 3 · «Sin huellas» — el que cambia las piezas recién pintadas

1. **Frase:** «Acabo de pintar la pieza y no puedo tocarla sin dejar la huella; y tengo los guantes llenos de
   pintura para coger la siguiente.»
2. **Pruebas.** *Vivido:* quien ha pintado una maqueta, una pieza impresa en 3D o un mueble pequeño. *Una frase:* sí.
   *Apaño:* brochetas clavadas en un bloque de espuma, pinzas de cocodrilo en palitos, colgar con alambre, plato
   giratorio para no tocar ([Van's Air Force](https://vansairforce.net/threads/spray-rack-for-priming.241002/),
   [Model Cars Mag](https://www.modelcarsmag.com/forums/topic/110914-painting-small-or-awkward-parts),
   [Finescale](https://forum.finescale.com/t/how-do-you-dry-your-painted-sprues-drying-racks/246032)); racks de
   secado comerciales (precio no verificado). *Segunda persona:* el que te va quitando las pintadas y acercando la
   siguiente en una tanda.
3. **Quién y dónde:** maquetista, *maker* que pinta piezas impresas o pequeño taller de acabados; banco con soporte de
   pintura y rack de secado.
4. **Reparto:** la persona pinta (pincel o aerógrafo) la pieza puesta en un soporte fijo; el robot **nunca sujeta
   mientras se pinta**: coge la pieza por su peana, la lleva al rack de secado y trae la siguiente que se le nombre.
5. **Órdenes:** `Put the part on the drying rack` / `Bring the wheel` (o `Bring the helmet`): una mueve a un sitio,
   la otra elige qué pieza.
6. **Tarea declarada:** «Bring the wheel» desde la bandeja de pendientes (piezas desordenadas) al soporte de pintura;
   acierto = peana en el soporte. Reposición: la persona devuelve la pieza a la bandeja, en otro sitio.
7. **Escena:** 3-4 piezas impresas distintas a la vista (rueda, casco, carcasa; 40-80 mm, < 100 g) cada una sobre una
   **peana impresa** de Ø 30 mm con cuello para la pinza; soporte de pintura y rack con alojamientos cónicos. ~7 h.
8. **Fiabilidad:** gesto difícil = encajar la peana en el cono del rack (±1 cm con cono). Plan B: ACT por orden.
9. **Momento memorable:** el juez pinta con rotulador acrílico una pieza; dice «a secar» y «tráeme el casco»; al
   final todas las piezas pintadas están en el rack sin una huella.
10. **Débil:** no se puede pintar con aerosol en el evento (se demuestra con pincel o rotulador acrílico); la peana es
    un útil propio que la persona ya tendría que usar; la prueba 4 es la más floja de los cuatro (en una tanda,
    mucha gente se apaña sola con brochetas). Sin parecido con MSN.

---

## 4 · «Foto sin soltar» — el que documenta mientras tienes las manos sucias

1. **Frase:** «Tengo que hacer foto antes de desmontar para acordarme de cómo iba, y tengo las manos llenas de grasa
   (o de resina).»
2. **Pruebas.** *Vivido:* «haz foto antes de desmontar» es el consejo de reparación por excelencia
   ([iFixit, buenas prácticas](https://ts.ifixit.com/Answers/View/576127/%22Best+practices%22+for+reassembly),
   [Inside my laptop](https://insidemylaptop.com/laptop-disassembly-tips-for-beginners)); la resina y el móvil no
   casan ([ArtResin](https://www.artresin.com/blogs/artresin/3-ways-your-smartphone-can-help-you-resin)).
   *Una frase:* sí. *Apaño:* limpiarse las manos, tocar con el nudillo o la nariz, móvil en bolsa, pedir a otro que
   haga la foto. *Segunda persona:* el compañero que sostiene el móvil y saca la foto donde le dices.
3. **Quién y dónde:** mecánico aficionado, reparador de electrodomésticos o artista de resina; banco con la pieza en
   una alfombrilla.
4. **Reparto:** la persona desmonta y deja piezas donde le cae bien; el robot lleva el móvil (en agarre impreso) o su
   cámara de muñeca hasta encuadrar lo pedido y dispara; la tablet guarda la foto con el paso.
5. **Órdenes:** `Photograph the screws` / `Photograph the part` (cambia **adónde** apunta; el objeto está en un sitio
   distinto cada vez).
6. **Tarea declarada:** encuadrar y fotografiar el objeto nombrado puesto en un sitio nuevo de la alfombrilla y volver
   a reposo; acierto = el objeto aparece entero y centrado en la foto (comprobable con un detector o a ojo del juez).
   Reposición: la persona mueve el objeto con la mano.
7. **Escena:** móvil ligero en agarre impreso con asa (si pasa de ~200 g, cámara de muñeca); bandeja de tornillos,
   pieza mecánica real, alfombrilla de 40×30 cm. Impresión ~3 h.
8. **Fiabilidad:** tolerancia de encuadre de varios cm (la más amplia de los cuatro); riesgo = temblor con el móvil en
   brazo extendido. Plan B: ACT por orden o cámara de muñeca.
9. **Momento memorable:** el juez desmonta algo con guantes sucios, pide fotos y al final la tablet muestra la
   secuencia de montaje con sus fotos, sin que nadie haya tocado el móvil.
10. **Débil:** dificultad percibida baja (apuntar no parece difícil); un script con marcadores podría apuntar igual si
    los objetos llevaran ArUco; roza la dirección «estudio de fotos de producto». Sin luz, así que no es MSN, pero
    «apuntar algo hacia la zona de trabajo» se le parece en el gesto: decirlo de frente.
