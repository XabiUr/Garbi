# Ideas industriales desde el mecanismo de los ganadores europeos (18-11-2026)

Fuente: [hackathons-2026-europa.md](../../investigacion/proyectos/hackathons-2026-europa.md), patrones de
[README.md](../../investigacion/proyectos/README.md), restricciones y formato de [encargo-ideas.md](encargo-ideas.md).
Excluidas: Machero, Relevo, LeWelder, camarero, baterías, Cuelga, asistencia y sus variantes cercanas.
Filtro añadido por el usuario tras rechazar Machero: **(1)** tema que el jurado reconoce al instante, **(2)** necesidad
evidente sin explicarla, **(3)** demo viva con movimiento y final visible (no "dejar en una caja y esperar a un sensor").

## 1. Proyecto → mecanismo → idea derivada

| Proyecto | Mecanismo ganador | Idea industrial derivada | Filtro (1-2-3) |
|---|---|---|---|
| MSN, linterna (Vitoria) | Habilidad aprendida corta + control programado que reacciona al humano; el juez interrumpe (mano) y el robot se recupera a la vista | Tercera mano que sujeta un soporte donde el operario marca | Fuera: contacto con personas y demasiado cerca de MSN/LeWelder |
| MURobot, OpenArm | Hardware llamativo y bimanual; demostraciones por captura | Cambio de formato enseñado por el operario | Fuera: enseñar en vivo no cabe (P4) y no tenemos ese hardware |
| Robotticelli (Ámsterdam) | El público pide algo personal y **se lleva lo que hace el robot**; sin espera | **Tu figura: personalización en masa** (el juez configura un juguete por voz y se lo lleva) | Pasa (1, 3); necesidad media |
| RoBoost (Múnich) | Un sentido extra en una frase: "ve igual, pesa distinto" | **Sopesa: ¿falta algo en el pedido?** (cajas iguales, una con un artículo olvidado) | Pasa a medias: poco movimiento |
| Talos (Zúrich) | Hardware propio que hace algo físico sorprendente; máquina de estados | Un brazo para tres máquinas sobre raíl impreso | Fuera: proceso oscuro (carga de máquina, D) y caro |
| LeHome (Viena) | Generaliza a objetos no vistos; cabeza de éxito que detecta el fallo y reintenta | Devoluciones de e-commerce con objetos que trae el juez | Fuera: agarre de objetos desconocidos poco fiable |
| Flip & Ship (París) | **Cinta casera** + selector programado entre habilidades + un gesto que arregla el objeto (voltear) | **Endereza: botellas tumbadas en la línea de envasado** | Pasa (1, 2, 3) |
| Conecta 4 (París) | **Turnos con el humano**: el juez mueve, un planificador decide y la VLA ejecuta "columna N" | **Repón: el lineal del supermercado** (el juez compra, el robot repone) | Pasa (1, 2, 3) |
| Le Coup de Pouce (París) | Voz con "para" y "cambia"; una tarea por objeto pedido | Consumibles a la línea por voz | Fuera: es Relevo/asistencia |
| AI Bartender (Bilbao I) | Personaje con voz + improvisar ante el fallo | Mezcla de color de granza por receta | Fuera: es el camarero |
| LeCyborg (Worldwide) | **Sensor propio dentro de la observación** del ACT | **Dedo de prueba: test de mandos y botoneras** (la luz del aparato guía a la VLA) | Pasa (1, 3) |
| ML6, toallas | Volumen medido y honestidad con números | Ninguna industrial: la tela está prohibida | Solo lección de volumen |

## 2. Las 5 fichas (ordenadas por los tres filtros)

### Endereza · el robot levanta en marcha las botellas que se caen en la cinta
- **Mecanismo tomado de:** Flip & Ship (cinta casera + selector + gesto que arregla el objeto en lugar de tirarlo).
- **Persona y dolor:** operador de línea de envasado de bebidas. Una botella tumbada atasca la cinta y para la
  llenadora o la etiquetadora un minuto; nadie lo apunta. Las paradas cortas suman el 15-45 % del tiempo perdido en
  líneas de envasado y la OEE media de llenado es del 55-65 %
  ([oxmaint](https://oxmaint.com/blog/post/beverage-filling-packaging-line-maintenance-oee),
  [fabrico](https://www.fabrico.io/blog/packaging-line-downtime-causes/),
  [ifactory](https://ifactoryapp.com/industries/food-manufacturing/micro-stop-capture-food-plants-below-60-seconds));
  fuentes de fabricantes de software, cifras orientativas.
- **Lo real:** hoy un expulsor neumático tira la botella caída (se pierde producto) o el operario corre a levantarla.
  A escala: cualquier embotelladora (agua, cerveza, refrescos); un cobot junto a la cinta con visión.
- **La demo en mesa:** cinta casera de 60 cm (paso a paso reciclado, como Flip & Ship) con 6 "botellas" impresas de
  45 mm × 110 mm y ~120 g, tapón de color y etiqueta. El juez tumba la que quiera de un golpe; la cinta se detiene sola
  al verla, el robot la coge tumbada, gira la muñeca, la deja de pie y la cinta arranca. Final: las 6 llegan de pie
  al "palé" y la tablet cuenta "paradas evitadas".
- **Órdenes del VLA:** "levanta las botellas caídas" · "retira las caídas sin tapón" (criterio: se aparta a la
  bandeja de rechazo en vez de levantarla) · "deja pasar solo las de etiqueta roja; aparta las azules" (cambio de
  formato) · "levanta las caídas y apártame una para el laboratorio" (cantidad).
- **Por qué solo un VLA lo hace bien:** la botella cae en cualquier orientación y sitio; un cobot programado
  necesita una trayectoria por caso y el criterio de qué se salva cambia con el producto que se envase ese día.
- **Fiabilidad:** el gesto difícil es coger un cilindro tumbado y dejarlo de pie (±1 cm en una cuna en V
  junto a la cinta que la centra antes de devolverla). La cinta se para durante el agarre (programado). Plan B: ACT de
  una sola habilidad "levantar" y el criterio en visión clásica.
- **Coste de preparación:** cinta (rodillos y bastidor impresos, motor paso a paso, ESP32), 8 botellas, cuna en V.
  ~150 episodios (100 levantar en varias orientaciones, 50 retirar).
- **Puntos débiles honestos:** se parece a Flip & Ship (cinta + gesto que arregla); botella de pie puede volcar al
  soltarla; la cifra de paradas viene de blogs de proveedores.
- **Nota 1-5:** necesidad 4 · VLA visible 4 · fiabilidad 3 · momento 5 · frescura 3.

### Repón · el juez "compra" del lineal y el robot repone el hueco con lo que toca
- **Mecanismo tomado de:** Conecta 4 (turnos: el humano mueve, un planificador decide, la VLA ejecuta "hueco N").
- **Persona y dolor:** reponedor de supermercado y jefe de tienda. El 8,3 % de los productos está agotado en el
  lineal en un momento dado (8,6 % en Europa); ante un hueco, ~31 % de los clientes compra en otra tienda y ~9 % no
  compra ([estudio Gruen-Corsten resumido por Pygmalios](https://www.pygmalios.com/reports/state-of-retail-2026),
  [SAS Rebotics](https://www.sasretail.com/wp-content/uploads/2022/02/SAS-Rebotics-Platform-Case-Study-Nov-2019.pdf));
  datos de 2002, citados en fuentes secundarias.
- **Lo real:** hoy se repone a mano por rondas; hay robots que solo detectan huecos (Simbe Tally, Rebotics).
  Reponer con brazo es lo que buscan las tiendas automáticas y los minimercados sin personal.
- **La demo en mesa:** estantería impresa de 2 baldas × 4 frentes, con tope trasero que centra; "productos" de
  50 × 50 × 80 mm (cajas de cereal, latas grandes) con fecha grande en el frontal; carro de reposición al lado. El juez
  coge lo que quiera "para comprar"; el robot repone solo los huecos. Final: el lineal vuelve a estar completo y la
  tablet muestra "0 huecos".
- **Órdenes del VLA:** "repón los huecos" · "repón con la marca blanca si no queda la original" (criterio de
  sustitución) · "pon lo que caduca antes delante" (criterio FIFO: coge el viejo del carro primero) · "deja libre la
  balda de arriba para la promoción" (destino).
- **Por qué solo un VLA lo hace bien:** el hueco lo crea el juez, cambia cada vez, y la regla (sustituir, FIFO,
  promoción) cambia con la frase; un cobot programado sirve para un planograma fijo.
- **Fiabilidad:** dejar una caja en un frente con tope trasero y separadores en V (±1 cm). Plan B: ACT con una
  tarea por frente (8 tareas, como las 5 columnas de Conecta 4) y el planificador eligiendo.
- **Coste de preparación:** estantería, 16 productos, carro; ArUco por frente. ~150 episodios (8 frentes × ~15
  + FIFO).
- **Puntos débiles honestos:** es comercio, no fábrica (logística de tienda); se acerca a "kits/sustitución
  condicional" ya estudiadas, aunque el turno con el juez lo hace más vivo; FIFO exige leer la fecha.
- **Nota 1-5:** necesidad 4 · VLA visible 5 · fiabilidad 4 · momento 4 · frescura 4.

### Tu figura · el juez diseña su muñeco por voz y se lo lleva montado
- **Mecanismo tomado de:** Robotticelli (el público pide algo personal y se lleva lo que hace el robot).
- **Persona y dolor:** jefe de producción de una fábrica de juguetes o regalos que quiere vender "lote de uno".
  El 36 % de los consumidores quiere productos personalizados y el 71 % de ellos pagaría más, pero solo 1 de cada 6
  los ha comprado: falta fabricarlos barato ([Deloitte UK, 2015](https://www2.deloitte.com/uk/en/pages/press-releases/articles/one-in-three-consumers-wants-personalised-products.html)).
- **Lo real:** personalización en masa (LEGO Minifigure Factory en tiendas, Nike By You); hoy se monta a mano en
  la tienda o en una célula con operario.
- **La demo en mesa:** tres cargadores de piezas impresas de 30-40 mm con imán (5 cabezas, 5 torsos, 5 piernas de
  colores); base en embudo. El juez dice "un pirata con piernas azules"; el LLM lo convierte en tres piezas, el robot
  apila las tres y entrega la figura en una bandeja. Final: el juez se lleva su figura.
- **Órdenes del VLA:** "pon la cabeza de pirata" · "torso rojo" · "como la del anterior pero con piernas verdes"
  (memoria de pedido en el LLM) · "desmonta y cambia la cabeza" (recuperación: cambio de pedido a media figura).
- **Por qué solo un VLA lo hace bien:** cada pieza tiene otra forma y cada figura otro orden; con 125
  combinaciones no se programan trayectorias, se aprenden 3 gestos parametrizados por la frase.
- **Fiabilidad:** apilar con imán sobre embudo (±1 cm se corrige solo). Plan B: ACT de "coger del cargador N" con
  la selección programada.
- **Coste de preparación:** 15 piezas + repuestos para regalar (muchas impresiones), imanes, cargadores. ~120 episodios.
- **Puntos débiles honestos:** necesidad discutible (capricho, no dolor); parece un juguete, no industria; ya hay
  muchas demos de "apilar bloques".
- **Nota 1-5:** necesidad 2 · VLA visible 4 · fiabilidad 5 · momento 5 · frescura 3.

### Dedo de prueba · el robot prueba cada botón de un mando y aparta el que falla
- **Mecanismo tomado de:** LeCyborg (sensor propio dentro de la observación de la política).
- **Persona y dolor:** técnico de pruebas de fin de línea de electrónica de consumo; pulsa cada botón de cada
  aparato y se cansa y se equivoca a partir de la cuarta hora ([Sabotap](https://www.saboit.de/blog/sabotap-are-we-building-robots-now));
  [sin fuente con cifra de coste].
- **Lo real:** probadores con dedo robótico de SPEA, Tapster o SGBI para móviles y botoneras
  ([SPEA](https://www.spea.com/?p=5525), [SGBI](https://sgbi.us/robotic-test-automation/)).
- **La demo en mesa:** "mando" impreso de 150 × 80 mm con 6 botones grandes de 25 mm (microrruptores + LED por
  botón + zumbador, ESP32). El robot coge el mando de la cola, lo deja en el útil, pulsa los 6 botones: cada uno
  pita y se enciende. El juez desconecta un botón con un puente oculto; el LED no se enciende, el robot repite y lo
  lleva a "reparación". Final: secuencia de luces y pitidos tipo piano y el malo apartado.
- **Órdenes del VLA:** "prueba todos los botones" · "prueba solo los de volumen" · "repite el que no se
  encendió antes de rechazar" (criterio de reintento) · "los fallos a reparación, no a chatarra" (destino).
- **Por qué solo un VLA lo hace bien:** ve el LED del aparato en la cámara (estado visible) y decide el siguiente
  gesto; cambia de modelo de mando con una frase sin recalibrar coordenadas.
- **Fiabilidad:** pulsar un botón de 25 mm con dedo de goma impreso (±1 cm vale); llevar el mando al útil con
  embudo. Plan B: ACT para coger/dejar y pulsaciones con poses enseñadas (como Robotticelli).
- **Coste de preparación:** 3 mandos con electrónica, útil, dedo. ~150 episodios.
- **Puntos débiles honestos:** cerca de "fin de línea buenas/malas" ya estudiado; el juez puede creer que la
  decisión la toma el ESP32 y no la VLA.
- **Nota 1-5:** necesidad 3 · VLA visible 3 · fiabilidad 4 · momento 4 · frescura 4.

### Sopesa · el robot nota que a una caja de pedido le falta un artículo
- **Mecanismo tomado de:** RoBoost ("ve igual, pesa distinto").
- **Persona y dolor:** responsable de expedición de un almacén de e-commerce. Entre el 1 y el 3 % de las líneas
  preparadas tienen error y cada error cuesta 22-75 $ entre devolución, reenvío y cliente perdido
  ([Cisco-Eagle](https://www.cisco-eagle.com/blog/2014/11/05/order-picking-error-rates-whats-acceptable/),
  [DMSi](https://dmsiworks.com/blog/the-cost-of-a-mispick-improve-the-bottom-line-by-reducing-errors));
  fuentes de proveedores.
- **Lo real:** controladoras de peso en la cinta de expedición; el robot lo integra en el gesto de mover la caja.
- **La demo en mesa:** 5 cajas cerradas de 60 mm iguales; el juez esconde un artículo (o no) en alguna. El robot
  levanta cada una, el par de los servos estima el peso y va a "envío" o a "revisión". Final: la que el juez vació
  sale en rojo.
- **Órdenes del VLA:** "manda a envío las completas" · "pedido de 2 artículos" (cambia el peso esperado) · "aparta
  también las que pesen de más".
- **Por qué solo un VLA lo hace bien:** poco: la decisión es del peso; el VLA solo aporta el agarre y el destino.
- **Fiabilidad:** el par de los STS3215 es ruidoso con diferencias < 100 g. Plan B: báscula ESP32 bajo la caja.
- **Coste de preparación:** cajas y lastres, 80 episodios.
- **Puntos débiles honestos:** demo quieta (se parece a "esperar a un sensor"); una báscula lo hace mejor y más
  barato.
- **Nota 1-5:** necesidad 4 · VLA visible 2 · fiabilidad 2 · momento 2 · frescura 3.

## 3. Top 2

1. **Endereza.** Pasa los tres filtros mejor que ninguna: todos han visto una línea de botellas, una botella caída
   que para la línea se entiende sin cifra, y el juez la tira y ve cómo el robot la levanta con la cinta en marcha.
   La frase cambia el criterio (levantar o retirar). Riesgo: compararnos con Flip & Ship; la respuesta es que aquí
   el juez provoca el fallo y el robot lo arregla, no clasifica.
2. **Repón.** El tema más reconocible (el supermercado), el juez juega de cliente con turnos reales como en Conecta 4
   y la frase cambia la regla (sustituir, FIFO, promoción). Es la que más se presta a una VLA visible con un gesto
   fiable. Riesgo: es tienda, no fábrica, y roza "kits/sustitución condicional".
