# Ideas industriales desde los mecanismos de los ganadores del mundo (18-11-2026)

Fuente: [hackathons-2026-mundo.md](../../investigacion/proyectos/hackathons-2026-mundo.md) (12 proyectos) y
[README de proyectos](../../investigacion/proyectos/README.md). Restricciones y formato: [encargo-ideas.md](encargo-ideas.md).
Excluido: Machero, Relevo, soldadura, camarero, baterías, Cuelga, asistencia. Filtros añadidos tras el rechazo
de Machero: (1) tema que el jurado reconoce al instante, (2) necesidad evidente sin depender de una cifra,
(3) demo viva con movimiento y un final que se ve (no "piezas a una caja y esperar a un sensor").

## 1. Proyecto → mecanismo → idea derivada

| Proyecto | Mecanismo ganador | Idea industrial derivada | ¿Pasa los 3 filtros? |
|---|---|---|---|
| Donuts (AMD Tokio, 1.º) | Pedido por chat → gestor de estado → VLA multitarea por texto; subtarea difícil en modelo aparte; campana de fin | **Palé a la carta**: cada cliente pide su mosaico de palé por voz; campana al cerrar el palé | Sí |
| Donuts | Ídem, con cierre de caja | Pedido de recambios con cierre y timbre a expedición | No: caja y espera (≈ kits) |
| Matcha (Seeed EE. UU., 1.º) | Pasos que empiezan y acaban en estados distintos a la vista (cuenco vacío/lleno, recipiente tirado) | Dosificación de colorante (masterbatch) por receta con vasos que quedan boca abajo | No: proceso oscuro, granza suelta |
| Matcha | Ídem | **Coche a la carta** (cada pieza montada cambia el estado visible del coche) | Sí |
| Tubos (CCSF, 1.º) | Pinza impresa a medida de un objeto redondo; tarea repetitiva de laboratorio | Carga de bobinas en fileta textil según patrón de urdido | No: textil, poco reconocible |
| Tubos | Ídem | **Línea parada**: pinza en V para botellas tumbadas | Sí |
| Desk cleanup (Shenzhen, 1.º) | Horizonte largo (recoger + limpiar), aleatorización, cifra frente a referencia | **Sombra**: 5S de fin de turno, herramientas a su silueta en el panel | Sí (justa en espectáculo) |
| CaliKPR (Junfan #35, 1.º) | Primitivas fiables como herramientas + marcador 20/20: "confianza" | Toma de muestras para metrología pedida por el MES con marcador | No: sin final visible |
| Sprinkle (Seeed EE. UU., 2.º) | 4 habilidades encadenadas; botón con LED que confirma la pulsación; plato que gira como pista | **Pulsa**: el robot prueba el panel de un horno o microondas en fin de línea | Sí |
| Sprinkle | Ídem | Carga de mesa giratoria indexadora en célula de montaje | No: ≈ carga de máquina (D) |
| Armtender (Hack Club, 1.º) | Hardware propio (ruleta ESP32) decide y el robot obedece; el público juega | Auditoría aleatoria AQL: un dado electrónico elige qué caja y pieza auditar | No: ≈ cuarentena por lote, final pobre |
| Armtender | El juez provoca el caso | Sabotaje del juez en Línea parada y Coche a la carta | Se incorpora |
| Iron Bestie (Hong Kong) | Voz + interacción con la persona y su rutina | Puesto que se adapta al operario que ficha | No: contacto/asistencia |
| Mochi (Humanoid Tokio, 1.º) | Oficio tradicional enseñado por imitación; originalidad y completitud | Volteo de quesos Idiazabal en la cava | No: deformable/pesado, poco industrial |
| BluPe (Junfan #35, 3.º) | Interfaz web que el juez usa él mismo | Configurador en tablet para Coche a la carta | Se incorpora |
| Tactile-FLORA (Junfan #35, 2.º) | Sensor que etiqueta si la ejecución salió bien | Báscula que verifica el recuento de la caja y repone | No: "caja y sensor" |
| Cloth folding (Seeed EE. UU., 3.º) | Recuperación de errores no vistos, anunciada en la crónica | **Línea parada**: botella caída → la línea se para → el robot la levanta → sigue | Sí |

## 2. Las cinco fichas

### Línea parada · el robot rescata la línea de embotellado cuando una botella se cae
- **Mecanismo tomado de:** Cloth folding (recuperación anunciada) + Tubos de ensayo (pinza impresa para redondos) + Armtender (el juez provoca el caso).
- **Persona y dolor:** operario de línea de envasado (agua, cerveza, conservas). Las botellas tumbadas y atascos son la parada corta más frecuente: 50 de 71 paradas en un ejemplo de línea de agua (ejemplo ilustrativo de un proveedor, [Fabrico](https://www.fabrico.io/blog/bottled-water-line-camera-oee/)); la enfardadora no admite botellas caídas y el operario debe quitarlas y rearrancar ([Gebo Cermex en BeverageDaily](https://www.beveragedaily.com/Article/2014/11/05/Bottle-down!-Gebo-Cermex-debuts-robotic-removal-system/), [Sidel](https://www.sidel.com/about/media/press-releases/securflow-meets-the-challenge-of-bottles-lying-down/)). La necesidad se entiende sin cifra: todos han visto una línea de botellas.
- **Lo real:** hoy lo resuelve un operario que vigila o guías mecánicas que expulsan la botella (se pierde). Gebo Cermex vende un sistema robótico de retirada; nadie la levanta y la devuelve.
- **La demo en mesa:** mini cinta motorizada (ESP32) de 60 cm con 6-8 botellas de PET de 50 cl vacías con lastre (~150 g, Ø 65 mm); sensor de barrera detecta la caída, para la cinta y enciende la baliza roja. El juez tumba una botella o pone una sin tapón. El robot la levanta y la devuelve al carril (o la retira a rechazo); baliza verde, la cinta arranca y el marcador sube "rescates 7/8".
- **Órdenes del VLA:** «levanta la caída y devuélvela» · «retira las que no tengan tapón» · «retira las abolladas al cajón de rechazo» · «deja pasar todas, solo endereza». Cambia el criterio (enderezar o rechazar) y el destino.
- **Por qué solo un VLA:** la botella cae en cualquier posición y orientación; un cobot programado necesita localizarla y planificar el giro; la frase cambia qué se considera defecto sin reprogramar.
- **Fiabilidad:** el gesto difícil es pasar de tumbada a de pie (giro de 90°); ayuda una rampa en V donde el robot la apoya y la empuja hasta ponerla de pie (±1 cm). Plan B: ACT con una sola habilidad («levántala») y el rechazo programado.
- **Coste:** cinta (perfil + correa + motor DC), carril de guías, rampa en V, pinza en V; sensor de barrera y baliza con ESP32. 3 habilidades × 50 episodios.
- **Puntos débiles:** el giro sobre la rampa puede fallar si la botella rueda; la cinta debe estar parada (no se coge en movimiento); que parezca "recoger y dejar" si no se ve la línea parar.
- **Nota:** necesidad 4 · VLA visible 4 · fiabilidad 3 · momento 5 · frescura 5.

### Coche a la carta · el juez configura su coche en la tablet y el robot lo monta y se lo envía rodando
- **Mecanismo tomado de:** Matcha (cada paso deja un estado distinto a la vista) + BluPe (el juez manda desde la interfaz) + Donuts (pedido → VLA multitarea → señal de fin).
- **Persona y dolor:** jefe de línea de montaje final. En una misma línea salen modelos y versiones distintos coche a coche: Mercedes-Benz Vitoria monta VLE, Clase V, Vito y eVito, eléctricas y de combustión, en la misma línea, ~132.000 al año ([Vozpópuli](https://www.vozpopuli.com/motor/mercedes-benz-vitoria-menor-produccion-de-la-esperada-este-ano-y-subida-del-12-en-2026.html)). La necesidad (cada coche distinto, sin errores) es evidente.
- **Lo real:** montaje "en secuencia" con operarios y hojas de ruta por bastidor; un error de variante obliga a retrabajo al final de línea. Fabricantes de automóvil (Mercedes Vitoria) y proveedores de módulos.
- **La demo en mesa:** chasis de juguete grande (25 cm) sobre una plataforma; 3 opciones por puesto: 2 carrocerías (furgoneta/monovolumen, distinto color), 2 techos (normal/elevado), 2 paragolpes. Piezas de 60-120 mm con conos de centrado e imanes. El juez elige en la tablet o por voz; el robot monta las 3 piezas; al terminar, la plataforma se inclina y el coche baja rodando por una rampa hasta el juez con bocina.
- **Órdenes del VLA:** «furgoneta roja con techo alto» · «monovolumen azul, techo normal» · «la misma que la anterior pero con paragolpes deportivo» · «cambia el techo, el cliente se ha equivocado» (desmontar y sustituir). Cambian el objeto, la combinación y la acción (montar o corregir).
- **Por qué solo un VLA:** la secuencia depende del pedido y del estado del coche (lo que ya está puesto); el VLA lee ambos de la imagen; un cobot necesita un programa por variante.
- **Fiabilidad:** el gesto difícil es asentar la carrocería sobre el chasis: conos de 15 mm de entrada e imanes dan ±1 cm. Plan B: ACT por pieza, con la secuencia en el gestor de estado.
- **Coste:** chasis con ruedas, 6 piezas, plataforma basculante con servo, rampa; ESP32 para servo y bocina. ~4 habilidades × 40-50 episodios.
- **Puntos débiles:** se parece a "kits por variante" (la diferencia es que se monta un producto que sale rodando); es un juguete, hay que contarlo como maqueta de la línea de Vitoria.
- **Nota:** necesidad 4 · VLA visible 5 · fiabilidad 4 · momento 5 · frescura 4.

### Pulsa · el robot prueba el panel de mandos del horno antes de que salga de fábrica
- **Mecanismo tomado de:** Sprinkle (habilidades encadenadas + botón con LED que confirma la pulsación como estado visible).
- **Persona y dolor:** técnico de pruebas de fin de línea de electrodomésticos. Cada panel se prueba botón a botón; V-Zug lo hace con un cobot de FANUC porque aplica una fuerza constante que una persona no repite ([FANUC, caso V-Zug](https://fanuc.eu/be/nl/klantcases/v-zug)); Dobot prueba teclados de neveras ([Dobot](https://www.dobot-robots.com/insights/news/dobot-advances-the-home-appliance-industry-with-automation.html)).
- **Lo real:** operarios que pulsan secuencias o bancos fijos por modelo. BSH, Fagor/Copreci y V-Zug.
- **La demo en mesa:** panel impreso de "horno" (30×12 cm) con 5 pulsadores de 25 mm, un mando giratorio grande y una pantalla de LED; ESP32 registra cada pulsación y la ilumina. El juez esconde un fallo (interruptor oculto que anula un botón). El robot ejecuta el plan; el panel muestra "OK" con pitido o "FALLO 3" en rojo, y el robot lo aparta a la bandeja de rechazo.
- **Órdenes del VLA:** «prueba completa» · «prueba solo el modo grill» (otra secuencia) · «comprueba el bloqueo infantil: mantén el candado» · «modelo B», que tiene otra distribución de botones.
- **Por qué solo un VLA:** el plan de prueba cambia con la frase y con el modelo de panel; los LED encendidos hacen de memoria (como en Sprinkle).
- **Fiabilidad:** pulsar un botón de 25 mm es el gesto más fácil de toda la lista; el mando giratorio, el más difícil (girar 90° con pinza abierta en horquilla). Plan B: ACT por botón y secuencia programada.
- **Coste:** 2 paneles impresos, pulsadores, ESP32, tira de LED, zumbador. ~4 habilidades × 40 episodios.
- **Puntos débiles:** poco movimiento (el brazo pulsa); un juez puede decir "eso lo hace un programa fijo".
- **Nota:** necesidad 4 · VLA visible 4 · fiabilidad 5 · momento 3 · frescura 4.

### Palé a la carta · cada cliente quiere su palé montado a su manera, y se lo dice al robot
- **Mecanismo tomado de:** Donuts (pedido por voz → VLA multitarea por texto → campana de fin) + Matcha (cada capa es un estado visible).
- **Persona y dolor:** mozo de expedición. Paletizar a mano es carga repetitiva: la espalda es el 37 % de los trastornos musculoesqueléticos según datos de BLS citados por un compilador (fuente secundaria, [Voxel](https://www.voxelai.com/industry-insights/manual-lifting-injury-statistics)); solo en paletizado de sacos en minería, 217 lesiones y 10.047 días perdidos ([NIOSH](https://stacks.cdc.gov/view/cdc/228122/cdc_228122_DS1.pdf)).
- **Lo real:** los paletizadores robóticos hacen un patrón por referencia; los palés mixtos por cliente se montan a mano en distribución (alimentación, logística).
- **La demo en mesa:** palé impreso de 20×15 cm; 8-10 cajas de 40-60 mm de dos tamaños y colores (~50 g). El juez dicta el cliente o el mosaico. El robot apila 2 capas; al cerrar, coloca la "esquinera" y suena la campana; el palé se mueve sobre una mesa giratoria (envolvedora simulada con una tira de LED que gira).
- **Órdenes del VLA:** «palé en columnas» · «palé cruzado» · «las grandes abajo y las pequeñas arriba» · «solo una altura, que es para Canarias en avión». Cambia el criterio de colocación y la cantidad.
- **Por qué solo un VLA:** el patrón depende de la frase y de lo que ya hay en el palé; reprogramar un paletizador por cliente es lo que hoy no compensa.
- **Fiabilidad:** colocar la caja junto a otra con ±1 cm; un marco con esquina de tope ayuda a la primera capa. Plan B: ACT por patrón.
- **Coste:** palé, cajas, mesa giratoria con motor, campana. ~3 patrones × 50 episodios.
- **Puntos débiles:** Team Zenith (Cosmos) ya hizo paletizado; la caída de una torre en vivo es posible; parece "apilar cubos".
- **Nota:** necesidad 4 · VLA visible 4 · fiabilidad 4 · momento 3 · frescura 3.

### Sombra · al acabar el turno, el robot devuelve cada herramienta a su silueta
- **Mecanismo tomado de:** Desk cleanup (horizonte largo de recoger y ordenar, con variación deliberada de posiciones).
- **Persona y dolor:** operario de mantenimiento o de taller. Buscar herramientas se lleva cerca del 10 % de la jornada según un proveedor que no cita el estudio ([Fleetrabbit](https://fleetrabbit.com/industry/construction-management-system/construction-fleet-reducing-time-lost-misplaced-equipment)) [cifra no verificada]. El panel de sombras (5S) lo reconoce cualquiera que haya pisado un taller.
- **Lo real:** el orden 5S lo hace el operario al final del turno, cuando hay prisa; se pierden herramientas y se paran máquinas buscándolas.
- **La demo en mesa:** panel vertical inclinado con 6 siluetas en V (llave, martillo, destornillador, alicates, calibre, cinta) y LED bajo cada hueco que se enciende al ocuparlo; herramientas maqueta impresas con mango de 25 mm (< 150 g). El juez las deja tiradas en el banco; el robot las cuelga; panel completo en verde y "turno cerrado".
- **Órdenes del VLA:** «recoge todo» · «guarda solo las de apriete» · «falta el calibre: déjalo en la bandeja de calibración» · «la llave está en el sitio del martillo: corrígelo».
- **Por qué solo un VLA:** las herramientas aparecen en cualquier sitio y postura, y la frase define qué se guarda y dónde.
- **Fiabilidad:** colgar en una V inclinada es tolerante; el difícil es coger una herramienta plana del banco (alicates). Plan B: ACT con herramientas de mango grueso.
- **Coste:** panel, 6 herramientas maqueta, ESP32 con interruptores o sensores bajo cada hueco. ~3 habilidades × 50 episodios.
- **Puntos débiles:** cifra floja; final menos espectacular que Línea parada o Coche a la carta; herramientas planas.
- **Nota:** necesidad 3 · VLA visible 4 · fiabilidad 3 · momento 3 · frescura 4.

## 3. Top 2

1. **Coche a la carta**: tema que se reconoce en un segundo (la línea de Vitoria, cada coche distinto), el juez
   configura y recibe su coche rodando, la frase cambia la combinación de verdad y el gesto (asentar con conos e
   imanes) es fiable. Mejora claramente "kits por variante": se monta un producto que sale de la línea.
2. **Línea parada**: la recuperación es la demo (como en Cloth folding, pero visible): el juez sabotea, la línea se
   para con baliza roja, el robot la arregla y la cinta vuelve a correr. Riesgo: el giro de tumbada a de pie;
   probarlo el primer día y, si no llega, quedarse con «retira a rechazo».

Pulsa es la más fiable y queda de reserva si se prima no fallar sobre el espectáculo.
