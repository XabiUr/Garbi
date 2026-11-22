# Ideas por paso de proceso concreto en cada sector (18-11-2026)

Lente: el **paso manual concreto** que sigue a mano en un sector real y cabe en una mesa con un SO-101.
Marcas: **[H]** página leída, **[H·b]** solo extracto del buscador (verificar antes del pitch), **[I]** inferencia,
«(fabricante)» = afirmación comercial. Descartados tras mirar (no caben en un SO-101 con honestidad): desmazarotado y
desbarbado de fundición (fuerza), retirada de coladas de inyección (ya automatizada a bajo coste: igus lo hace en
~1.000 inyectoras con pórticos y cepillos [H·b](https://www.all-about-industries.com/how-igus-production-and-logistics-cost-efficiently-automated-a-b6fd224f1e29b92ac109bfca9f9290a7/)),
carga de bobinas SMT (discos finos y planos), mazos de cables (deformable), herrajes de mueble (= kits E).

---

### 1 · Cuelga · el robot cuelga las piezas en el bastidor de pintura con el criterio que pide el proceso
- **Persona y dolor:** Maite, colgadora en la línea de pintura en polvo o cataforesis de un proveedor de
  electrodomésticos o automoción. Una línea manual necesita 3-4 personas y una se dedica solo a colgar; una automática
  sigue necesitando dos: una para colgar y otra para descolgar (PCI Magazine, 25-8-2024)
  [H](https://www.pcimag.com/articles/112692-when-is-it-worth-investing-in-painting-line-automation). Los robots
  mejoran todos los pasos de la línea **salvo la carga y descarga de piezas sueltas en bastidores**; en alta
  variedad el retorno de automatizar el colgado era de 10-15 años (Products Finishing)
  [H·b](https://pfonline.com/articles/racking-and-conveyor-automation-solutions). Un buen colgado puede subir la
  producción de la línea entre un 100 % y más de un 500 % (consultor, Products Finishing)
  [H·b](https://short.pfonline.com/goodrackdesign).
- **Lo real:** pintores industriales a terceros y líneas propias (electrodomésticos, mueble metálico, bastidores de
  automoción). El colgado decide la calidad: orientación para que drene y no haga bolsas de aire, separación según el
  acabado, qué pedido va en cada barra. Cambia con cada pedido: por eso no se automatiza [I].
- **La demo en mesa:** bastidor impreso tipo árbol (300 mm) sobre carro con 8 ganchos abiertos en V, punta de 8 mm;
  10 piezas impresas de 40-80 g (tapa, soporte en L, escuadra) con una anilla de Ø40 mm, en una caja. El juez dice el
  pedido; el robot cuelga; el carro entra en un túnel con LED naranja (horno, ESP32) y sale con las piezas
  «pintadas» (fundas de color que el equipo cambia, o luz de color sobre piezas blancas).
- **Órdenes del VLA:** «cuelga las tapas con el agujero de drenaje hacia abajo» (orientación = criterio) · «es
  metalizado: deja un gancho libre entre pieza y pieza» (densidad = criterio) · «solo el pedido azul, en la barra de
  arriba» (objeto y destino) · «descuelga lo pintado a la caja» (tarea inversa).
- **Por qué solo un VLA lo hace bien:** un cobot programado necesita un programa por pieza y por patrón de colgado; la
  regla («ganchos alternos», «drenaje abajo») cambia con el pedido y se dice en una frase. La visión clásica no decide
  el criterio de proceso.
- **Fiabilidad:** enganchar la anilla en el gancho: holgura de ~15 mm con anilla de Ø40 y gancho de 8 mm, dentro de la
  tolerancia. Lo difícil es la orientación (girar la muñeca 180° según la orden) y el balanceo de la pieza colgada.
  Plan B ACT: una sola orden, «cuelga todo en ganchos alternos».
- **Coste de preparación:** bastidor y carro (6 h de impresión), 10 piezas con anilla (8 h), túnel con tira LED y
  ESP32. ~60 episodios por orden con orientación, 150 en total.
- **Puntos débiles honestos:** las piezas reales pesan más y llegan aceitadas; en la línea real el gancho se mueve
  (cadena aérea) y aquí está quieto; «cuatro ganchos» se lee como juguete si no se cuida la estética industrial.
- **Nota 1-5:** necesidad 4 · VLA visible 5 · fiabilidad 3 · momento 4 · frescura 5.

### 2 · Tapa · el robot pone los capuchones de enmascarado según el tratamiento que va a recibir la pieza
- **Persona y dolor:** Ane, preparadora de enmascarado en un taller de tratamiento superficial que trabaja para la
  aeronáutica (anodizado, pintura, proyección térmica). En un caso de Products Finishing, enmascarar una bisagra
  aeronáutica llevaba ~120 min por pieza y se quedó en menos de 20 con máscaras moldeadas
  [H·b](https://pfonline.com/articles/custom-masking-helps-hixson-soar); cinta y papel «añaden varios minutos de
  trabajo manual por pieza» (Formlabs, fabricante)
  [H·b](https://formlabs.com/es/blog/guide-to-3d-printed-masking-tools-painting-coating-more/).
- **Lo real:** tapones de silicona en agujeros y roscas y capuchones sobre espárragos antes de pintar o anodizar; qué
  se tapa depende del proceso y del plano. Talleres proveedores de Aernnova o ITP Aero, también máquina-herramienta [I].
- **La demo en mesa:** pieza impresa de 150 × 100 mm con 5 espárragos verticales de Ø20 mm (roscados marcados con
  hexágono, lisos, uno con símbolo de toma de tierra); capuchones impresos con boca acampanada (Ø36 → Ø21, embudo) en
  una bandeja. El juez elige el tratamiento en la tablet; el robot tapa; se pasa un spray de color de verdad (o tiza en
  polvo) y al retirar los capuchones se ve qué quedó protegido.
- **Órdenes del VLA:** «va a anodizar: tapa solo los roscados» · «va a pintar: tapa todo menos la toma de tierra» ·
  «añade la máscara de la cara de apoyo» (pieza plana) · «desenmascara a la bandeja».
- **Por qué solo un VLA lo hace bien:** la misma pieza, distinto criterio según el proceso dicho en voz alta; un
  programa por combinación pieza × proceso es justo lo que hoy no compensa.
- **Fiabilidad:** dejar caer el capuchón recto sobre el espárrago con la boca acampanada: tolerancia ~±7 mm, pero el
  capuchón puede quedar torcido. Plan B ACT: una orden («tapa los roscados»).
- **Coste de preparación:** pieza base, 8 capuchones, bandeja (6 h). Spray o tiza. ~120 episodios.
- **Puntos débiles honestos:** el enmascarado real es a presión (tapones de silicona, roscas finas): la demo lo
  convierte en «dejar caer», que un experto verá; el sector aeronáutico exige trazabilidad que no enseñamos.
- **Nota 1-5:** necesidad 3 · VLA visible 5 · fiabilidad 3 · momento 4 (el spray) · frescura 4.

### 3 · Machero · el robot coloca los machos de arena en el molde de la referencia que toca y rechaza los rotos
- **Persona y dolor:** Josu, moldeador en una fundición de series cortas (válvulas, grifería, piezas de bomba). En
  Euskadi hay ~20 fundiciones con moldeo manual de series cortas, >1.600 trabajadores y >400 M€ de facturación
  [H·b, extracto sin fuente identificada: verificar]. Colocar machos a mano «puede dañar el macho y dejar arena suelta
  en el molde», lo que acaba en chatarra (Foundry Management & Technology)
  [H·b](https://www.foundrymag.com/molds-cores/article/21928035/robotic-core-setting-for-permanent-mold-casting); una
  célula de colocación con robot de 210 kg cuesta ~85.000 $ de robot + 10.000 $ de pinza + 20.000 $ de programación
  [H·b](https://www.foundrymag.com/feature/robotic-automation-permanent-mold-foundries). La metalurgia vasca perdió un
  9,8 % de ocupación en el 1.er trimestre de 2024 [H·b](https://www.deia.eus/economia/2024/08/06/ocupacion-sector-metal-euskadi-baja-8559673.html).
- **Lo real:** los machos (arena aglomerada, frágiles) forman los huecos interiores; se colocan en las portadas del
  molde antes de cerrarlo. En series largas lo hace un robot; en series cortas, una persona, porque cada referencia
  lleva machos distintos [I].
- **La demo en mesa:** medio molde impreso (caja de moldeo de 200 × 150 mm, aspecto arena) con portadas en V abiertas;
  6 machos impresos de 25-40 mm en una bandeja de machería (corto, largo, en codo), uno con un trozo partido visible.
  El juez dice la referencia, el robot pone los machos, el juez cierra la caja con la otra mitad (imanes) y le da la
  vuelta: sale una «pieza fundida» impresa con los huecos que dibujan esos machos.
- **Órdenes del VLA:** «molde de la válvula A: los dos machos cortos» · «referencia B: el macho en codo» · «ese macho
  está roto, al rechazo» (criterio de integridad) · «saca los machos, cambio de modelo».
- **Por qué solo un VLA lo hace bien:** cambio de referencia sin reprogramar y rechazo por un defecto visible en la
  misma red; un cobot por puntos necesita receta por molde y una visión aparte para el rechazo.
- **Fiabilidad:** dejar el macho en portadas en V: ±1 cm aceptable; el gesto suave es una virtud del SO-101 (el macho
  real es frágil). Lo difícil: distinguir el macho roto si el defecto es pequeño → defecto grande y de otro color.
  Plan B ACT: «pon los machos de la A».
- **Coste de preparación:** dos medios moldes, 6-8 machos, «pieza fundida» (10 h de impresión), imanes. ~120 episodios.
- **Puntos débiles honestos:** los machos reales pesan de cientos de gramos a kilos y hay arena y calor; la cifra de
  Euskadi no está verificada; el final «dar la vuelta al molde» lo hace el juez, no el robot.
- **Nota 1-5:** necesidad 3 · VLA visible 4 · fiabilidad 4 · momento 4 · frescura 5.

### 4 · Caja de cliente · el robot embala a pie de prensa con el patrón que pide cada cliente
- **Persona y dolor:** Leire, operaria de inyección que vigila dos prensas y embala lo que sale; o un centro de
  manipulados como Lantegi Batuak (Bizkaia), que ofrece packaging, gestión de cajas y montaje de kits con
  certificación IATF de automoción [H·b](https://www.lantegibatuak.eus/wp-content/uploads/2025/06/Catalogo-industrial-Lantegi-Batuak-cast.pdf).
  Colocar las piezas separadas en la caja y poner una hoja intermedia por capa «se hace normalmente a mano»; la célula
  automática que lo sustituyó usó dos robots FANUC (caso Kunststoff-Packungen, fabricante)
  [H·b](https://www.fanuc.eu/be/nl/klantcases/kunstoff-packungen). El 63 % de los centros de trabajo de la UE declara
  movimientos repetitivos de mano o brazo (ESENER 2024, ya en `investigacion-produccion.md`).
- **Lo real:** cada cliente pide un patrón: a granel, en rejilla, por capas con separador, por cavidad separada.
- **La demo en mesa:** tobogán impreso que deja tapones de 35 mm (de dos «cavidades», número grande en relieve y
  color); caja con rejilla de 3 × 3; separadores rígidos con asa. El juez elige cliente en la tablet.
- **Órdenes del VLA:** «cliente A: en rejilla y separador cada capa» · «cliente B: a granel» · «la cavidad 2 aparte,
  que hay reclamación» (criterio de trazabilidad) · «cierra la capa con el separador».
- **Por qué solo un VLA lo hace bien:** el patrón cambia por cliente sin reprogramar; la visión clásica no cambia de
  patrón por voz.
- **Fiabilidad:** pieza a alveolo con embudo, fácil; el separador es lo difícil (placa de 2 mm: hay que darle asa
  gruesa). Contar la capa es débil en un VLA → la rejilla hace de contador.
- **Coste de preparación:** tobogán, 20 tapones, rejilla, 3 separadores (8 h). ~100 episodios.
- **Puntos débiles honestos:** se parece mucho al estuche G y a los kits E; en la realidad el ritmo es de segundos por
  pieza; el momento final (caja llena) es poco memorable.
- **Nota 1-5:** necesidad 3 · VLA visible 3 · fiabilidad 4 · momento 2 · frescura 2.

### 5 · Puck · el robot carga los envases en los portaenvases de la línea de llenado cuando cambia el formato
- **Persona y dolor:** Nerea, operaria de alimentación en una planta de cosmética que hace tiradas cortas (muestras,
  ediciones limitadas). España facturó 11.800 M€ y exportó 10.124 M€ en cosmética y perfume en 2025, segunda
  exportadora mundial de perfume (Stanpa, vía Alimarket)
  [H·b](https://www.alimarket.es/nonfood/noticia_amp/425068/el-mercado-espanol-de-cosmetica--perfume-y-cuidado-personal-crecio-un-5-8--en-2025).
  En Chesebrough-Pond's, pasar a portaenvases («pucks») subió el rendimiento un 25 % y casi eliminó el cambio de
  formato; los operarios ganan peso justo en los cambios (Packaging World)
  [H·b](https://www.packworld.com/leaders-new/machinery/conveying-accumulation/article/13329275/pucks-combat-pack-proliferation-at-chesebroughponds).
- **Lo real:** envases inestables (roll-on, bomba, tarro) se meten a mano en pucks en la cabecera de la línea; en
  tiradas cortas no compensa un desordenador con visión.
- **La demo en mesa:** 3 formatos de frasco impresos (Ø30-45 mm, 40-90 g), pucks de color con alojamiento cónico,
  una tira de 6 pucks como «cinta». El juez vuelca frascos revueltos en una bandeja.
- **Órdenes del VLA:** «formato de 50 ml en los pucks blancos» · «los de bomba, con el pulsador hacia la
  etiquetadora» (orientación = criterio) · «aparta los que tengan el tapón puesto» (defecto grueso) · «vacía la línea».
- **Por qué solo un VLA lo hace bien:** formato, orientación y rechazo en una red y por voz.
- **Fiabilidad:** frasco a puck cónico: fácil. La orientación rotacional (±20°) con pinza de 2 dedos es el punto
  flojo; plan B ACT sin orientación.
- **Coste de preparación:** 12 frascos, 8 pucks, tira (8 h). ~100 episodios.
- **Puntos débiles honestos:** la línea real va a 60-200 envases/min y el robot a 1 cada 10 s: hay que contarlo
  como célula de tiradas cortas; la cifra del 25 % es de un caso antiguo; final poco espectacular.
- **Nota 1-5:** necesidad 3 · VLA visible 4 · fiabilidad 3 · momento 2 · frescura 4.

### 6 · Supermercado · el robot repone el kanban de dos cajas del puesto de montaje
- **Persona y dolor:** Iñaki, aprovisionador (mizusumashi) de un proveedor de automoción que recorre los puestos
  cambiando cajas vacías por llenas. En líneas de montaje, caminar es ~10-15 % del tiempo de trabajo del operario y
  colocar bien los contenedores lo baja un 20 % (Sedding, IISE Transactions 2020)
  [H·b](https://ideas.repec.org/a/taf/uiiexx/v52y2020i2p181-198.html).
- **Lo real:** estantería dinámica con dos cajas por referencia; la vacía vuelve por el carril de retorno con su
  tarjeta kanban. Lo hacen personas o AMR + persona.
- **La demo en mesa:** estantería dinámica impresa (2 niveles × 3 carriles), 8 cajitas de 60 × 40 × 30 mm (<150 g) con
  tarjeta de color, un «tren» con cajas llenas.
- **Órdenes del VLA:** «repón lo vacío» · «primero el puesto 2, que va a parar» (prioridad) · «el carril 3 pasa a la
  referencia verde» (cambio de referencia) · «la tarjeta roja es urgente».
- **Por qué solo un VLA lo hace bien:** prioridad y cambio de referencia por voz; pero un sistema de tarjetas + AMR
  ya lo resuelve sin brazo [I].
- **Fiabilidad:** cajas grandes en carriles con guías: fácil. Lo difícil: sacar la caja de un carril inclinado.
- **Coste de preparación:** estantería y cajas (12 h, mucha impresión). ~80 episodios.
- **Puntos débiles honestos:** un brazo fijo no viaja, que es lo que cuesta de verdad al aprovisionador; la cifra es
  de tiempo de caminar del montador, no del aprovisionador; poco memorable.
- **Nota 1-5:** necesidad 2 · VLA visible 3 · fiabilidad 4 · momento 2 · frescura 2.

---

## Top 2 [R]

1. **Cuelga (colgado en bastidor de pintura).** Es el hueco que las fuentes señalan («todo menos cargar y descargar
   bastidores»), la maqueta se entiende en 5 s (bastidor y ganchos) y las órdenes cambian un **criterio de proceso**
   (drenaje, densidad), no solo un objeto. Riesgo: la orientación al colgar. Se puede combinar con **Tapa**: «prepara
   para pintar» = enmascarar y colgar, con el spray de color como momento final.
2. **Machero (machos de arena en el molde).** Fundición vasca, gesto suave que el SO-101 sí hace bien, portadas en V
   que dan tolerancia y un final que el juez remata (cerrar el molde y ver la pieza). Antes del pitch hay que
   verificar la cifra de fundiciones de moldeo manual en Euskadi.
