# Ideas: asistente colaborativo real en un banco de trabajo (18-11-2026)

Método research-ops: **[H]** hecho con fuente leída (URL) · **[H·b]** solo visto en el extracto del buscador ·
**[I]** inferencia. No se dan cifras sin fuente. Excluidas por encargo: tercera mano de taller, estudio de fotos de
producto, asistencia, cocina, soldadura al arco, camarero y maquetas de procesos industriales.

Hallazgo transversal: en los foros de reparación, pintura y relojería la queja de fondo no es "me falta fuerza", sino
**"tengo las dos manos ocupadas y necesito que algo se mueva a donde yo diga"** (girar la pieza, acercar el vaso,
encuadrar la cámara). Eso encaja con lo que el SO-101 hace bien: coger y dejar objetos gruesos y sostenerlos en una pose.

## Tabla de candidatas

| # | Nombre | La persona hace… / el robot hace… | Encaje SO-101 | Solape |
|---|---|---|---|---|
| 1 | **Cámara de banco** | trabaja con las manos / sostiene una cámara ligera y encuadra según la voz ("plano cenital", "sigue la punta") | Alto (cámara de 30-60 g) | Algo con fotos de producto |
| 2 | **Despiece** | desmonta un móvil o un portátil / acerca un vaso, lo aparca en orden y lo devuelve al montar | Alto (vasos de 35 mm, alojamientos) | Ninguno |
| 3 | **Peana de aerografía** | pinta con el aerógrafo / sostiene la miniatura por su mango y la orienta | Medio (temblor del servo) | Roza la tercera mano |
| 4 | **Lupa de calidad** | inspecciona con lupa y dice el veredicto / presenta cada pieza, la gira y la separa | Alto | Roza la idea F (fin de línea) |
| 5 | **Luz rasante** | busca defectos o pinta / orienta un foco ligero según la orden ("rasante desde la izquierda") | Alto | MSN y fotos de producto |
| 6 | Instrumentista de banco | repara una placa o un dron / pasa y recoge herramientas ("dame el multímetro") | Medio (herramientas finas) | Fuerte con la tercera mano |
| 7 | Secadero de pintura | pinta capas / retira la pieza pintada al secadero y trae la siguiente | Alto | Débil, poco valor |
| 8 | Bandeja de granja 3D | desbarba / saca piezas del cajón de salida y se las presenta | Medio (piezas variadas) | Maqueta industrial |
| 9 | Ayudante de laboratorio de FP | el profesor hace la práctica / reparte y recoge material por puesto | Medio | Instrumentista |
| 10 | Pony de costura de cuero | cose a punto de silla / sujeta y avanza la pieza | Bajo (deformable, fuerza) | Descartada |

## Fichas

### 1. Cámara de banco · un cámara que encuadra tus manos mientras trabajas, a la voz
- **Qué hace la persona / qué hace el robot:** la persona suelda, pinta o repara con las dos manos; el robot sostiene una
  cámara ligera (cámara USB o ESP32-CAM, no un móvil) y cambia el plano según lo que diga: cenital, lateral, primer plano
  del punto de trabajo, seguir la punta de la herramienta.
- **Persona y dolor:** creador de tutoriales de manualidades que graba solo, y profesor de FP que demuestra una práctica
  pequeña a 20 alumnos. Los propios fabricantes de soportes reconocen el problema: hay que mantener el soporte "fuera del
  recorrido de las manos" y repetir la toma hasta que las manos y la pieza se vean durante todo el gesto
  [H·b] (https://www.ulanzi.com/blogs/knowledges/craft-phone-rig-setup-tutorial). En docencia, el Tec de Monterrey
  usa **tres cámaras** para enseñar microelectrónica y soldadura, con una fija en la punta del soldador, para que se vea
  la técnica del profesor [H·b] (https://observatory.tec.mx/edu-bits/three-cameras-for-teaching-microelectronics-and-welding/).
  Sin cifra de horas perdidas [sin fuente].
- **Lo real:** hoy son brazos articulados fijos, trípodes cenitales y cámaras de documentos (proyectan lo que hay debajo,
  con zoom manual) [H·b] (https://www.benq.com/en-in/knowledge-center/knowledge/bring-your-lessons-to-life-with-the-ideacam.html).
  Ninguno cambia de plano solo. El producto real: un brazo de escritorio para aulas de FP, creadores y técnicos que
  documentan reparaciones [I].
- **La demo en mesa:** el juez se sienta en el banco con una placa y un soldador frío (o un pincel y una miniatura); la
  pantalla grande muestra lo que ve la cámara del robot. El juez dice "enséñame la soldadura de cerca" y el plano cambia.
  Final visible: la pantalla con un primer plano bien encuadrado de lo que hace el juez.
- **Órdenes del VLA:** "plano cenital de todo el banco" · "primer plano de la punta" · "mira desde la izquierda, que no
  se ve" · "sigue mi mano". Cambia el **criterio de encuadre** (qué importa ver), no un objeto.
- **Por qué no se puede hacer sin VLA:** cada frase pide una pose distinta que depende de dónde están ahora las manos y
  la pieza; un cobot programado tendría poses fijas. Seguir la mano sí se hace con visión clásica (MediaPipe) [I]: el
  valor del VLA es una sola red que interpreta "de cerca", "desde la izquierda" o "que se vea la soldadura" sobre la
  escena real.
- **Fiabilidad:** no hay agarre durante la demo (la cámara va atornillada a la pinza); el gesto difícil es acabar en un
  encuadre útil, con tolerancia amplia (un encuadre de ±3 cm sigue sirviendo) [I]. Plan B: ACT con 4 planos
  discretos elegidos por voz → LLM.
- **Coste de preparación:** soporte de cámara para la pinza, pantalla, 30-40 episodios por plano (4 planos ≈ 150).
- **Puntos débiles honestos:** el robot se mueve cerca de la cara y las manos (hay que limitar la zona); el temblor del
  servo se nota en el vídeo; "sigue mi mano" en tiempo real puede ir lento con SmolVLA.
- **Nota:** necesidad 3 · VLA visible 4 · fiabilidad 5 · momento 5 (el juez se ve en pantalla) · frescura 4.

### 2. Despiece · el ayudante que guarda los tornillos en orden y te los devuelve al revés
- **Qué hace la persona / qué hace el robot:** la persona desatornilla un móvil o un portátil; el robot le acerca un
  vaso vacío junto a la mano, y cuando dice "hecho, tapa trasera" lo aparca en la siguiente posición de una rejilla. Al
  montar, el robot devuelve los vasos en orden inverso o el que se le pida.
- **Persona y dolor:** técnico de reparación de móviles y portátiles, y aficionado al "hazlo tú mismo". iFixit pone
  entre los diez fallos más probables suponer que los tornillos se quedarán en su sitio en una superficie cercana y
  suponer que solo hay un par de longitudes, y avisa de que un tornillo en el agujero equivocado puede perforar un
  componente de debajo [H] (https://www.ifixit.com/News/the-10-things-likely-to-go-wrong-when-fixing-a-phone-or-laptop).
  Los técnicos de los foros usan vasitos, cinta de doble cara en el orden de la guía o un papel con el dibujo del equipo
  [H·b] (https://technibble.com/forums/threads/how-do-you-guys-keep-your-screws-organized-when-disassembling.20999).
  En relojería se colocan las piezas "en el orden en que se sacan" para invertir la secuencia al montar
  [H·b] (https://rotatewatches.com/blogs/blog/how-to-handle-tiny-watch-parts).
- **Lo real:** alfombrillas magnéticas con cuadrícula, bandejas de compartimentos y fotos con el móvil
  [H] (iFixit, misma URL). Nadie lo automatiza; el producto sería un brazo de banco para talleres de reparación [I].
- **La demo en mesa:** una carcasa impresa de portátil con 4 grupos de tornillos reales (M2-M3) y un destornillador;
  6 vasos impresos de 35 mm con base magnética; rejilla de 6 alojamientos numerados. El juez desmonta un grupo, el robot
  le pone el vaso al lado, él echa los tornillos y dice "hecho, bisagras". Al final dice "dame los de las bisagras" o
  "ahora al revés" y el robot trae el vaso correcto.
- **Órdenes del VLA:** "acércame un vaso" (destino = donde esté la mano) · "guárdalo" (siguiente hueco libre) ·
  "devuélveme el último" · "dame el vaso de la tapa" (vaso con etiqueta de color o tapa que el juez eligió). Cambian el
  **destino** y el **criterio de elección** (orden frente a etiqueta).
- **Por qué no se puede hacer sin VLA:** la mano y la pieza cambian de sitio en cada paso, y "el último", "el siguiente
  hueco libre" o "el de la tapa" se resuelven mirando la rejilla, no con coordenadas fijas. Una sola red cubre acercar,
  aparcar y devolver. La memoria de qué vaso es cuál la lleva el sistema (voz → LLM con el registro del orden) o una
  etiqueta visible en el vaso [I].
- **Fiabilidad:** coger vasos de 35 mm con asa o borde grueso y dejarlos en alojamientos cónicos (±1 cm): el gesto más
  fiable del SO-101. Lo difícil es dejar el vaso "junto a la mano" sin tocarla: se resuelve con una zona de entrega
  marcada a 15 cm de la pieza. Plan B: ACT con 3 tareas (entregar, aparcar en hueco N, devolver hueco N).
- **Coste de preparación:** carcasa, 6 vasos y rejilla impresos (~6 h de impresora); sin electrónica; ~120 episodios.
- **Puntos débiles honestos:** un vasito en un tapete parece poco "robot"; la memoria del orden la hace el LLM, no el VLA;
  el juez puede preguntar por qué no basta una alfombrilla magnética (respuesta: entrega en la mano y orden inverso sin
  mirar).
- **Nota:** necesidad 4 · VLA visible 3 · fiabilidad 5 · momento 3 · frescura 5.

### 3. Peana de aerografía · el robot gira la miniatura mientras pintas
- **Qué hace la persona / qué hace el robot:** la persona sostiene el aerógrafo (o el pincel); el robot sostiene la
  miniatura por su mango impreso y la orienta según la orden ("enséñame la espalda", "inclínala para el brillo").
- **Persona y dolor:** aficionado a la pintura de miniaturas o maquetas. Make: "sostener la propia miniatura puede
  acalambrarte la mano" [H] (https://makezine.com/article/craft/hobby-ergonomics-for-painting-miniatures-and-other-small-objects/).
  En aerografía una mano está siempre en el aerógrafo; para girar la pieza se usan mangos, tornos tipo "lazy Susan" o se
  toca con los dedos (y la grasa estropea la pintura) [H·b] (https://forum.finescale.com/t/how-do-you-guys-hold-it-when-you-p/148668),
  [H·b] (https://archive.kitmaker.net/forums/158597/index.htm). Hay hilos de pintores con lesión nerviosa o temblor que
  buscan cómo sujetar la pieza [H·b] (https://bolterandchainsword.com/topic/292838-tips-for-painting-and-assembly-with-nerve-damage/).
- **Lo real:** mangos de pintura, tornos giratorios y brazos con pinzas de cocodrilo; ninguno se orienta solo.
- **La demo en mesa:** una miniatura impresa de 50-70 mm en un mango cilíndrico de 25 mm; aerógrafo con agua o un pincel
  seco. El juez pide ángulos mientras "pinta".
- **Órdenes del VLA:** "enséñame la espalda" · "boca abajo, para pintar los bajos" · "inclínala 45° hacia la luz" ·
  "déjala en el secadero". Cambia la **pose objetivo** respecto a la figura (frente, espalda) y el destino.
- **Por qué no se puede hacer sin VLA:** "la espalda" depende de cómo esté la figura en el mango, que cambia cada vez; hay
  que mirar la miniatura para saber hacia dónde girar [I].
- **Fiabilidad:** el agarre del mango es fácil; el riesgo es el temblor del servo con el brazo extendido, que con pincel
  fino se nota. Con aerógrafo (gesto grueso) se tolera [I]. Plan B: ACT con 4 poses fijas.
- **Coste de preparación:** mangos, figuras y secadero impresos; ~120 episodios.
- **Puntos débiles honestos:** el pintor experto quiere girar la pieza con su propia mano y sentirla; el robot recibe
  pintura pulverizada; se parece a la tercera mano.
- **Nota:** necesidad 3 · VLA visible 4 · fiabilidad 3 · momento 4 · frescura 4.

### 4. Lupa de calidad · el robot presenta cada pieza bajo la lupa y la aparta según tu veredicto
- **Qué hace la persona / qué hace el robot:** el inspector mira por la lupa o el microscopio y habla; el robot coloca la
  pieza bajo la lente, la gira cuando se le pide ("enséñame el otro lado") y la deja en buena, mala o duda según lo dicho.
- **Persona y dolor:** inspector de calidad en un puesto con lupa (pequeño taller, electrónica, piezas impresas). Un
  fabricante de microscopios afirma que el operario "debe sentarse en una postura incómoda, a menudo durante periodos
  prolongados", con riesgo de error por fatiga [H·b] (https://www.visioneng.com/resources/articles/the-role-of-optical-inspection-in-todays-demanding-electronics-industry/)
  (fuente comercial). Quality Magazine: la inspección visual más difícil es la del 100 % de cientos de piezas
  [H·b] (https://www.qualitymag.com/articles/90406-seeing-is-not-believing). No he encontrado una cifra fiable de
  error frente a tiempo [sin fuente].
- **Lo real:** el inspector coge, gira y separa a mano; la visión artificial sustituye al humano solo en series largas.
  Aquí el humano juzga y el robot manipula [I].
- **La demo en mesa:** 10 piezas impresas de 30-40 mm (algunas con defecto visible), lupa con cámara a la pantalla,
  3 cajas. El juez inspecciona y decide.
- **Órdenes del VLA:** "siguiente" · "dale la vuelta" · "esta, a rechazo" · "las que tengan rebaba, todas a retrabajo".
  Cambian la acción y el destino; la última cambia el criterio.
- **Por qué no se puede hacer sin VLA:** las piezas llegan revueltas y "dale la vuelta" depende de cómo esté ahora [I].
- **Fiabilidad:** coger y dejar piezas gruesas en alojamientos: alta. Plan B: ACT.
- **Coste de preparación:** piezas, soporte de lupa, cajas; ~120 episodios.
- **Puntos débiles honestos:** muy parecido a la idea F ya investigada; el juez puede ver "un clasificador con pasos".
- **Nota:** necesidad 3 · VLA visible 3 · fiabilidad 5 · momento 3 · frescura 2.

### 5. Luz rasante · un foco que se coloca donde dices para que aparezcan los defectos
- **Qué hace la persona / qué hace el robot:** la persona revisa una superficie (pintura, carrocería de maqueta, pieza
  impresa, chapa) o pinta; el robot sostiene una linterna LED ligera y la coloca según la orden.
- **Persona y dolor:** la luz rasante (incidencia muy baja) revela relieves y defectos y se usa en conservación de arte
  [H·b] (https://en.wikipedia.org/wiki/Raking_light); en pintura, la "piel de naranja" es casi invisible con luz frontal
  y solo aparece con luz baja, por eso los inspectores inclinan los paneles [H·b]
  (https://ifactoryapp.com/industries/manufacturing-plant/ai-vision-surface-defect-detection-paint-coating). El
  inspector necesita las dos manos para la pieza y el rotulador [I].
- **Lo real:** lámparas fijas, linternas de mano y túneles de luz en automoción.
- **La demo en mesa:** una placa pintada con defectos sutiles; el juez pide la luz y los defectos aparecen en pantalla.
- **Órdenes del VLA:** "rasante desde la izquierda" · "más baja" · "ilumina donde señalo" · "luz frontal".
- **Por qué no se puede hacer sin VLA:** "donde señalo" y "rasante respecto a esta pieza" dependen de la escena [I].
- **Fiabilidad:** sin agarres; tolerancia amplia. Plan B: ACT con poses discretas.
- **Coste de preparación:** soporte de linterna, placas pintadas; ~100 episodios.
- **Puntos débiles honestos:** es casi el mismo gesto que MSN (sostener la luz) y que el estudio de fotos; frescura baja.
- **Nota:** necesidad 3 · VLA visible 3 · fiabilidad 5 · momento 4 · frescura 2.

## Mi top 2

1. **Cámara de banco.** Es lo más cercano a "el robot ES la herramienta tal cual": cualquiera que grabe tutoriales o
   enseñe en un aula de FP lo usaría mañana. No hay agarres arriesgados en vivo (la cámara va fija a la pinza), el juez
   se ve a sí mismo en la pantalla y cada frase cambia un criterio de encuadre, que es el uso del VLA que más luce. Punto
   débil: seguir la mano también se hace con visión clásica; hay que vender la parte de lenguaje.
2. **Despiece.** La necesidad con mejor fuente (iFixit la cita entre los diez fallos más probables) y el gesto más fiable
   del SO-101 (vasos gruesos en alojamientos). Menos espectacular, pero muy creíble para un jurado técnico. Se puede
   combinar con la 1: el mismo brazo graba y documenta el despiece.

Pendiente de verificar: horas reales perdidas por tornillos mezclados o por grabación en solitario (no hay cifra con
fuente); probar el temblor del SO-101 sujetando una cámara de 50 g con el brazo extendido.
