# Ideas · tareas industriales donde el LENGUAJE es imprescindible (18-11-2026)

Lente: la instrucción cambia a menudo (excepciones, reclamaciones, urgencias, sustituciones) y no compensa fijarla
en un programa. Marcas: [H] hecho con fuente, [V] cifra de proveedor o fuente secundaria (revisar con `santa-method`
antes del pitch), [I] inferencia, [sin fuente].

## Lo que SmolVLA puede y no puede hacer con 150 demos (vale para todas las fichas)

- **Frases fijas.** El dataset lleva 2-3 cadenas cortas en inglés que empiezan por verbo («Put the red part in box
  B»). El LLM traduce lo que diga el juez («oye, lo rojo hoy para Michelin») a una de ellas. No hay generalización
  libre: lo que se ve es una red que hace cosas distintas según la cadena, no una red que entiende cualquier frase.
- **Unas 50 demos por frase.** Con 150 episodios caben 3 frases; si no da tiempo, mejor 2 bien grabadas.
- **El caso difícil es justo el interesante.** Si la escena es la misma y solo cambia la frase (mismo objeto, otro
  destino), la red puede ignorar el texto y hacer «la media». SmolVLA no lo prueba en su artículo. Mitigación: grabar
  cada frase desde las mismas posiciones de partida (que la imagen no delate la orden) y evaluar cada frase aparte.
- **Contar y leer, poco.** Cantidades («tres de cada») y números pequeños impresos son débiles: se codifican con
  color o con un número muy grande, y una pieza por orden.
- **Plan B común con ACT:** ACT no recibe texto; el plan B es un modelo ACT por frase y el LLM elige cuál cargar. El
  público ve lo mismo; en el pitch se dice con honestidad.
- Contexto: el estudio sobre VLA en industria señala que los modelos preentrenados fallan al casar instrucciones de
  dominio con lo que ven, por falta de datos industriales [H, https://arxiv.org/html/2509.23121v1]. Por eso se
  ajusta con demos propias.

---

### 1 · Desvío de pedido · «Hoy la referencia roja va al cliente B»
- **Persona y dolor:** Iñaki, preparador de expediciones de un proveedor de componentes que sirve a 2-3 clientes. Cada
  mañana el jefe de turno le cambia destinos «solo por hoy». Un error de preparación cuesta 195 € (Federación Sueca
  de Comercio, citada por un proveedor) [V, https://www.scm.dk/how-picking-errors-steal-your-money]; otras
  estimaciones dan 22-100 $ por error [V, https://dmsiworks.com/blog/the-cost-of-a-mispick-improve-the-bottom-line-by-reducing-errors].
  Sin escáner, la tasa típica de error es del 1-2 % [V, https://www.cisco-eagle.com/blog/2014/11/05/order-picking-error-rates-whats-acceptable/].
- **Lo real:** hoy, hoja impresa, pick-to-light o el ERP reasigna el pedido; la persona sigue moviendo la caja. Lo
  harían los integradores de intralogística (Ulma Handling, Mecalux) [I]; no hay caso conocido con lenguaje.
- **La demo en mesa:** 2 referencias (cilindros de 40 mm, rojo y gris, con «ref.» grabada grande), 2 cajas de
  cliente con embudo y logotipo inventado («Cliente A», «Cliente B»). El juez hace de jefe de turno y cambia el
  destino de una referencia. Final: la misma pieza roja cae en cajas distintas según lo que dijo.
- **Órdenes del VLA:** «Put the red part in box A» / «Put the red part in box B» / «Put the grey part in box A».
  Cambia el **destino** con el mismo objeto (criterio de reparto), y el objeto en la tercera.
- **Por qué solo un VLA:** un cobot programado necesita un programa o una variable de destino que alguien edite en el
  HMI; aquí la excepción se dice. [I] Objeción honesta: un ERP + cobot con dos destinos lo hace sin IA si la
  excepción entra por pantalla; el valor es que la excepción llega hablada y en la jerga del jefe.
- **Fiabilidad:** coger cilindro grueso y soltar en embudo (±1 cm): alta. Riesgo: la red ignora la frase (mismo
  objeto, misma escena). ACT por frase como plan B.
- **Coste de preparación:** 6-8 cilindros y 2 cajas-embudo (~6 h de impresora); sin electrónica; 3 × 50 episodios.
- **Puntos débiles honestos:** visualmente es «poner un cubo en una caja»; la necesidad es real pero la escena es
  pobre; parecido a mil demos de clasificación.
- **Nota:** necesidad 3 · VLA visible 4 · fiabilidad 4 · momento 2 · frescura 2.

### 2 · Cuarentena por lote tras reclamación · «Saca todo el lote 12, el cliente ha reclamado»
- **Persona y dolor:** Nerea, técnica de calidad de una planta de envasado o de un proveedor de automoción. Llega una
  reclamación: hay que localizar y apartar el lote sospechoso del stock mezclado en 24-48 h (contención del 8D)
  [V, https://ifactoryapp.com/quality-control-management/quality-escape-prevention-stop-defects-reaching-customers].
  Una retirada de alimentos cuesta de media ~10 M$ en costes directos (FMI/GMA) [H·b, https://www.fooddive.com/news/more-than-money-what-a-recall-truly-costs/426855/];
  en Reino Unido, ~550.000 £ de media (encuesta 2026) [H·b, https://www.foodsafetynews.com/2026/09/uk-survey-puts-average-recall-cost-at-almost-550-000/].
  Los errores de etiqueta causaron el 45,5 % de las 422 retiradas de alimentos de la FDA en 2024 (Loftware) [V,
  https://www.newfoodmagazine.com/label-errors-dominate-2024-us-food-recalls-costing-industry-192-billion/837701.article].
- **Lo real:** hoy se bloquea el lote en el ERP y una persona revisa a mano palés y cajas, etiqueta por etiqueta; el
  coste de la mala calidad ronda el 15 % de las ventas (IISE) [H·b, https://iise.org/details.aspx?id=22118]. A
  escala: robot de almacén o célula de reacondicionamiento; no hay caso conocido con lenguaje [I].
- **La demo en mesa:** una bandeja de «stock» con 6-8 botes o cajitas gruesas (50 mm) con franja de color de lote y
  número grande (lote 11 azul, lote 12 naranja); una caja roja «CUARENTENA» con embudo y otra «EXPEDICIÓN». El juez
  recibe una llamada (tarjeta de reclamación) y la dicta. Final: la cuarentena con solo el lote 12 y un sello
  «LOTE 12 BLOQUEADO» en la tablet.
- **Órdenes del VLA:** «Move lot 12 to quarantine» / «Move lot 11 to quarantine» / «Ship lot 11». Cambia el
  **criterio** (qué lote es sospechoso), no el tipo de objeto: la misma bandeja se vacía de forma distinta.
- **Por qué solo un VLA:** visión clásica podría detectar el color, pero cada reclamación cambia la regla y el
  destino; el VLA recibe la regla con la frase y además coge y mueve. [I] Objeción: «un lector de códigos lo hace
  mejor» → respuesta: el lector no mueve, y en planta el stock mezclado lo aparta una persona.
- **Fiabilidad:** coger bote grueso de una bandeja con varios (separación ≥ 3 cm) y soltar en embudo: media-alta. La
  red ve la franja de color, no lee el número (el número es para el público). Plan B: ACT por frase.
- **Coste de preparación:** 8 botes con franja (~5 h), 2 cajas-embudo, tarjetas de reclamación; ESP32 opcional para
  una luz roja en la caja de cuarentena; 3 × 50 episodios con mezcla de lotes en posiciones variadas.
- **Puntos débiles honestos:** el «lote» se reconoce por un color, así que se puede leer como clasificación por
  color; hay que vender la regla cambiante (hoy el 12, mañana el 11). La cifra de 10 M$ es antigua (≈2011).
- **Nota:** necesidad 5 · VLA visible 5 · fiabilidad 4 · momento 4 · frescura 4.

### 3 · Sustitución condicional · «Si no queda la azul, pon la verde»
- **Persona y dolor:** Ainara, preparadora de pedidos de recambios en un distribuidor industrial. Los pedidos llegan
  con reglas de sustitución que el cliente acepta («vale la equivalente»). Un error de picking cuesta 22-100 $ [V,
  https://blog.unex.com/when-order-picking-goes-wrong-the-true-cost-of-mispicks] y en talleres de alta variedad la
  entrega a tiempo se queda en el 85-88 % (encuesta anual FMA) [H·b, https://www.thefabricator.com/thefabricator/article/shopmanagement/how-high-product-mix-manufacturers-deliver-on-time].
- **Lo real:** el ERP propone el sustituto y la persona decide mirando la estantería; lo haría un almacén de
  recambios (automoción, ferretería industrial) [I].
- **La demo en mesa:** 2 huecos de estantería (azul y verde, piezas de 40 mm) y una bandeja de pedido. El juez **quita
  la pieza azul con la mano** y repite la misma orden. Final: el robot pone la verde sin cambiar la frase.
- **Órdenes del VLA:** «Pick blue, else green» (una sola frase; las demos incluyen escenas con y sin azul) /
  «Pick green» / «Pick blue only». Cambia el **criterio** y el resultado depende de lo que hay en la escena.
- **Por qué solo un VLA:** un cobot programado necesita un sensor de presencia y una rama en el programa por cada
  regla; el VLA aprende la condición visual con las demos y la regla llega con la frase. [I]
- **Fiabilidad:** coger y dejar: alta. Riesgo: que la red no aprenda la condición con ~50 demos (25 con azul, 25 sin
  ella) y se quede quieta o vaya al hueco vacío. Plan B: el LLM mira la cámara (o un ArUco en el hueco) y elige
  la frase «Pick blue» o «Pick green»: la condición pasa al LLM.
- **Coste de preparación:** 2 alojamientos en V, 6 piezas, bandeja (~4 h); sin electrónica; 3 × 50 episodios.
- **Puntos débiles honestos:** se parece a los kits por variante (E); el final es una bandeja con una pieza; si el
  plan B se activa, la «inteligencia» la pone el LLM, no el VLA.
- **Nota:** necesidad 3 · VLA visible 5 · fiabilidad 3 · momento 5 · frescura 4.

### 4 · Devoluciones con el motivo dictado · «Este viene por garantía»
- **Persona y dolor:** Jon, operario del puesto de devoluciones (RMA) de un fabricante de pequeño electrodoméstico o
  herramienta. El motivo de la devolución no se ve en la pieza: viene en el papel o en la llamada. En 2025 se
  devolvieron en EE. UU. ~850.000 M$ de mercancía, el 15,8 % de las ventas (NRF) [H, https://nrf.com/media-center/press-releases/consumers-expected-to-return-nearly-850-billion-in-merchandise-in-2025];
  procesar una devolución en un operador logístico cuesta 3,5-6 $ por unidad, más 2-5 $ de inspección [V,
  https://www.speedcommerce.com/insights/how-to-handle-ecommerce-returns/].
- **Lo real:** una persona abre, lee el motivo, decide destino (stock, reparación, reacondicionado, chatarra) y lo
  mueve; lo harían centros de logística inversa y reacondicionadores [I].
- **La demo en mesa:** una zona de recepción con un aparato maqueta (taladro o mando grueso impreso) y 3 cajas con
  embudo: STOCK, REPARACIÓN, CHATARRA. El juez lee un «albarán de devolución» (tarjeta) y dice el motivo. Final:
  el mismo aparato acaba en tres sitios distintos según tres albaranes.
- **Órdenes del VLA:** «Send it to repair» / «Return it to stock» / «Scrap it». Cambia el **destino** y la
  información viene **solo** de la frase: es el caso más puro de lenguaje imprescindible.
- **Por qué solo un VLA:** la visión clásica no puede decidir, porque el dato no está en la imagen; un cobot
  necesitaría que alguien lo teclee. [I] Objeción: «basta un botón por destino» → cierto; el valor está en que el
  motivo llega en lenguaje natural («dice que hace ruido y tiene 8 meses») y el LLM lo convierte en destino.
- **Fiabilidad:** un solo objeto grueso en una posición conocida: alta. Riesgo máximo de «red que ignora el texto»
  (la escena es idéntica para las 3 frases). Plan B: ACT por frase.
- **Coste de preparación:** 2-3 aparatos maqueta, 3 cajas-embudo, tarjetas (~6 h); 3 × 50 episodios.
- **Puntos débiles honestos:** el razonamiento lo hace el LLM, el VLA solo lleva a tres sitios; un jurado técnico
  puede verlo como «tres trayectorias»; la cifra es de comercio minorista, no de fábrica.
- **Nota:** necesidad 4 · VLA visible 3 · fiabilidad 4 · momento 3 · frescura 4.

### 5 · Abastecimiento de línea a demanda · «El puesto 3 se queda sin tapas»
- **Persona y dolor:** Unai, el «water spider» (abastecedor) de una línea de montaje; los operarios le avisan a
  voces o con el andon. Una hora de parada en una gran planta de automoción: 2,3 M$ (Siemens 2024, ya en
  `diagnostico.md`) [H]. Siemens probó en 2026 en Erlangen un humanoide moviendo cajas: 60 movimientos/h y > 90 % de
  éxito en coger y dejar [H, https://thehumanoid.ai/siemens-and-humanoid-bring-physical-ai-to-the-factory-floor-deploying-humanoids-in-industrial-operations-with-nvidia/]
  (sin órdenes habladas).
- **Lo real:** abastecedor con carro, rutas fijas (milk run), AMR que llevan cajas; lo haría un integrador de
  intralogística o un AMR con brazo [I].
- **La demo en mesa:** almacén de 2 componentes (cajita de tapas, cajita de casquillos, 50 mm con asa) y 2 «puestos»
  (bandejas con embudo y cartel «P1», «P3»). El juez es el operario del puesto que pide. Final: el componente
  pedido llega al puesto que lo pidió.
- **Órdenes del VLA:** «Bring caps to station 1» / «Bring caps to station 3» / «Bring bushings to station 3».
  Cambian **objeto y destino** a la vez (composición).
- **Por qué solo un VLA:** una red para todas las combinaciones componente × puesto; prueba atractiva: entrenar 3 de
  las 4 combinaciones y pedir la cuarta. [I] Honesto: con 150 demos lo más probable es que la cuarta **falle**; no
  prometerlo en vivo.
- **Fiabilidad:** cajita con asa en embudo: alta. Plan B: ACT por frase.
- **Coste de preparación:** 4 cajitas, 2 bandejas-puesto, carteles (~5 h); ESP32 opcional con pulsador andon que
  dispara la frase; 3 × 50 episodios.
- **Puntos débiles honestos:** en una línea real el problema es la distancia (un brazo fijo no recorre la línea); se
  parece al pañol (A); el lenguaje aporta poco frente a un pulsador por puesto.
- **Nota:** necesidad 4 · VLA visible 3 · fiabilidad 4 · momento 3 · frescura 2.

### 6 · Interrupción por urgencia · «Para eso: primero el pedido urgente de Mercedes»
- **Persona y dolor:** Maite, jefa de turno de una pyme de series cortas que reordena prioridades varias veces al día.
  En talleres de alta variedad la entrega a tiempo se queda en el 85-88 % [H·b, https://www.thefabricator.com/thefabricator/article/shopmanagement/how-high-product-mix-manufacturers-deliver-on-time];
  cuántas órdenes son urgentes [sin fuente: las cifras de 10-50 % que circulan son de blogs de proveedor].
- **Lo real:** la jefa de turno grita o cambia el plan en el MES; la persona deja lo que hace. Un cobot programado
  no se reprograma a mitad de ciclo [I].
- **La demo en mesa:** el robot hace una tarea de rutina en bucle (pasar piezas grises de una bandeja a otra). El juez
  interrumpe con la urgencia; el robot cambia de tarea a mitad y pone una pieza roja en la caja «URGENTE»; luego
  «sigue con lo de antes». Se usa `/subtask` de `lerobot` para cambiar la frase sin recargar el modelo.
- **Órdenes del VLA:** «Move grey parts to tray» / «Put the red part in the urgent box» / «Resume». Cambia la
  **tarea y la prioridad** en caliente; una pieza por orden (contar «tres» no es fiable).
- **Por qué solo un VLA:** una sola red que cambia de comportamiento al oír la frase, a mitad de un movimiento; con un
  cobot sería otra rutina y una señal de E/S [I].
- **Fiabilidad:** el gesto difícil es el cambio a mitad de chunk (la red debe recuperarse desde una postura que no
  vio en las demos). Grabar demos que empiezan en posturas intermedias. Plan B: esperar a que termine el ciclo y
  luego cambiar de modelo ACT.
- **Coste de preparación:** 2 bandejas, caja URGENTE, 8 piezas (~4 h); 3 × 50 episodios + ~20 desde posturas
  intermedias.
- **Puntos débiles honestos:** la necesidad es de planificación (MES), no de manipulación; «Resume» es difícil para un
  VLA sin memoria; el momento depende de que el cambio en caliente salga bien.
- **Nota:** necesidad 3 · VLA visible 5 · fiabilidad 2 · momento 4 · frescura 4.

---

## Top 2 [R]

1. **2 · Cuarentena por lote tras reclamación.** Es la que mejor encaja con lo que pide el jurado: la frase cambia un
   **criterio** (qué lote es sospechoso), hay una persona concreta (la técnica de calidad), una cifra fuerte
   (retiradas de ~10 M$, errores de etiqueta en el 45,5 % de las retiradas de la FDA en 2024) y el juez participa
   haciendo de cliente que reclama. Fiable con objetos gruesos y franjas de color. Combina bien con F (fin de línea).
2. **3 · Sustitución condicional.** El mejor momento de la lista: el juez quita la pieza azul y el robot, con la misma
   frase, pone la verde. Enseña algo que un cobot programado no hace sin sensores ni ramas. Riesgo: que la condición
   no se aprenda con 50 demos; el plan B (el LLM decide) mantiene la demo en pie.

Combinación posible: una sola célula de expedición de pyme donde la técnica de calidad bloquea un lote («el 12 a
cuarentena») y el pedido sigue con sustituto («si no hay del 12, pon del 11»). Así la 3 queda dentro de la historia
de la 2 y comparten piezas y episodios.

Casos 2025-2026 de robots con lenguaje en fábrica: no encontré ningún despliegue verificado. Figure dice que Helix
clasifica paquetes (95 % de etiquetas bien orientadas, ~4 s por paquete), pero no está claro que lo haga con órdenes
habladas [H, https://www.figure.ai/news/helix-logistics]; lo de Figure en BMW con órdenes en lenguaje natural solo
aparece en fuentes secundarias [sin verificar]. Esto es un hueco que se puede contar en el pitch: «nadie lo hace aún
en planta».
