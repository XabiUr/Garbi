# Ideas · copiar a escala los pilotos industriales de robots que aprenden (18-11-2026)

Lente: tareas que la industria eligió en 2024-2026 para robots con aprendizaje por demostración o VLA, en versión
honesta para un SO-101 y con un final que se ve. Marcas: [H] hecho con fuente, [I] inferencia, [E] cifra de la
propia empresa (sin verificación independiente: no va al pitch sin `santa-method`).

## Pilotos revisados y si caben en una mesa

| Piloto | Tarea elegida | Por qué (cifra) | ¿Cabe con SO-101? |
|---|---|---|---|
| Figure 02 · BMW Spartanburg | Coger chapas del rack y ponerlas en el útil de soldadura | 11 meses, 1.250 h, >90.000 piezas, 30.000 X3; objetivo 37 s de carga y 99 % por turno [E] ([Assembly](https://www.assemblymag.com/articles/99678-humanoid-robots-complete-trial-project-at-bmw-assembly-plant)) | Sí, con chapas gruesas y útil con embudos → ficha 2 |
| Figure Helix · logística | Girar el paquete para que el código mire al escáner | 4,05 s/paquete; de 10 a 60 h de demos el acierto del código sube del 88,2 al 94,4 % [E] ([Figure](https://www.figure.ai/news/scaling-helix-logistics)) | Sí, cajas rígidas → ficha 1 |
| Agility Digit · GXO | Cubetas del AMR a la cinta y apilado | >100.000 cubetas en servicio comercial (nov. 2025) [E] ([Agility](https://www.agilityrobotics.com/content/digit-moves-over-100k-totes)) | Sí, cubetas mini → ficha 3 |
| Humanoid · Siemens Erlangen | Logística de cubetas en planta electrónica | 60 cubetas/h, >8 h, >90 % de acierto [E] ([eWeek](https://www.eweek.com/news/siemens-nvidia-humanoid-factory-trial/)) | Ídem → ficha 3 |
| UR AI Trainer + Scale AI | Empaquetar un smartphone (líder-seguidor, VLA de Generalist) | Grabar demos en el hardware de producción (GTC 2026) [H] ([UR](https://www.universal-robots.com/news-and-media/news-center/universal-robots-scale-ai-launch-imitation-learning-system-accelerate-ai-training-lab-to-factory/)) | Sí, con piezas gruesas → ficha 4 |
| Foxconn (GR00T) · Intrinsic | Manipular cables y conectores en servidores de IA | Foxconn mostró «enchufar cables» con humanoides; reto de Intrinsic dedicado a cables y conectores [H] ([Assembly](https://www.assemblymag.com/articles/99628-foxconn-to-deploy-humanoid-robots-on-production-line-at-houston-ai-server-plant), [Intrinsic](https://www.intrinsic.ai/blog/posts/foxconn-and-intrinsic-launch-joint-venture-to-build-the-ai-factory-of-the-future)) | Solo con conectores magnéticos gruesos → ficha 5 |
| Hexagon AEON · BMW Leipzig | Montaje de baterías de alto voltaje y piezas exteriores | Primer humanoide en producción en Alemania; ~20 demos teleoperadas [E] ([Hexagon](https://robotics.hexagon.com/bmw-deploys-aeon-hexagon-robotics-humanoid/), [bmwblog](https://www.bmwblog.com/2026/03/03/bmw-hexagon-aeon-humanoid-robot-leipzig-pilot/)) | Sí, módulos-bloque con imanes → ficha 6 |
| Atlas · Hyundai Metaplant | Secuenciar piezas (bacas) para la línea | Centro de entrenamiento sept. 2026; secuenciado desde 2028 [H] ([Robot Report](https://www.therobotreport.com/boston-dynamics-opens-metaplant-application-center-train-atlas-humanoid-robots/)) | Ya investigado (JIS, producción #6) |
| Apptronik · Mercedes | Llevar piezas a línea y control de calidad | <10 robots en Berlín y Kecskemét [H] ([heise](https://heise.de/-10320691)) | Kitting: ya investigado (E) |
| Dyna (DYNA-1) | Doblar servilletas 24 h | >800 en 24 h, 99,4 % [E] ([Robotics Tomorrow](https://roboticstomorrow.com/news/2025/04/30/dyna-robotics-unveils-dyna-1-the-first-commercial-ready-robot-foundation-model-offering-fully-autonomous-round-the-clock-dexterity/24675)) | No: deformable |
| mimic · Audi | Montar juntas y piezas blandas con manos diestras | 30 min de demos frente a 30 h [E] ([Unite.AI](https://www.unite.ai/mimic-robotics-introduces-flux-mimic-to-bring-video-action-models-to-audis-factory-floor/)) | No: deformable y fuerza |
| Covariant · Otto | Recogida de prendas para pedidos | Hasta 1.600 cogidas/h [E] ([Robotics 24/7](https://www.robotics247.com/article/online_retailer_otto_group_partners_with_covariant_to_deploy_ai_robotics_systems_for_its_logistics_network/covariant)) | Sin tela no hay historia; parecido a kits |
| Physical Intelligence | API de ajuste fino de π0/π0.5 (oct. 2026); casos de socios (cargadora de Actor, Almond) [H] ([Unite.AI](https://unite.ai/physical-intelligence-opens-pi-api-beta-for-robot-foundation-models)) | Plataforma, no tarea | Marco del pitch, no demo |

Patrón [I]: las tareas piloto son **las de «coger, orientar y dejar» en el borde de un proceso automático** (útil de
soldadura, escáner, cinta, AMR): el humano está ahí solo porque las piezas llegan variadas. Es justo lo que el
SO-101 hace bien, y el «proceso automático» al lado da el final visible (pitido, contador, LED, segundo brazo).

---

### 1 · Al escáner · el robot gira cada paquete para que el código mire al lector, como Figure en logística
- **Persona y dolor:** Leire, operaria de inducción en un centro de paquetería: coloca a mano paquetes con la
  etiqueta hacia el túnel de lectura. Figure entrenó a su humanoide justo para esto: 4,05 s por paquete, y pasar
  de 10 a 60 h de demos subió el acierto de lectura del 88,2 al 94,4 % [E] (https://www.figure.ai/news/scaling-helix-logistics).
  Coste de un paquete no leído (va a rechazo y revisión manual) [sin fuente].
- **Lo real:** inducción manual a clasificadores (Correos, SEUR, Amazon); pilotos de Figure (Helix) y Covariant.
- **La demo en mesa:** 8 cajas rígidas impresas (40-60 mm, <80 g) con una etiqueta ArUco/QR en una sola cara;
  rampa con «lector» (webcam abajo, mirando por una ventana de metacrilato) que lee el código, pita y suma al
  contador de la tablet. El juez vuelca las cajas sobre la mesa como quiera. Final: pitidos seguidos y el
  contador «leídos 8/8, rechazos 0».
- **Órdenes del VLA:** «induce los paquetes» (código abajo) · «los frágiles (pegatina roja) a la bandeja lenta» ·
  «primero los exprés» · «este va a devoluciones, código arriba para el operario». Cambia el criterio y la cara.
- **Por qué solo un VLA:** la orientación es aleatoria en 6 caras: un cobot programado necesita visión de pose y
  un árbol de casos por cada cara; el VLA aprende el volteo de las demos y la frase cambia la regla.
- **Fiabilidad:** el volteo (cara lateral → abajo) es el gesto difícil; tolerancia de la rampa ±1,5 cm con
  guías. Plan B: ACT con dos subtareas (voltear sobre una cuña fija; dejar en rampa).
- **Coste:** 8 cajas, rampa con ventana, cuña de volteo; webcam extra (lector ya hecho con ArUco); 120-150 ep.
- **Puntos débiles:** Flip & Ship (AMD París, 1.º) ya volteó paquetes: hay que diferenciarse con el lector real y
  el criterio por voz; un paquete real pesa más que 300 g (se dice: «sobres y paquetes pequeños»).
- **Nota:** necesidad 4 · VLA visible 4 · fiabilidad 3 · momento 4 · frescura 2.

### 2 · El ayudante del soldador · el SO-101 carga las chapas en el útil y el segundo brazo «suelda», como Figure en BMW
- **Persona y dolor:** Asier, operario de una célula de soldadura en un proveedor de carrocería: alimenta el útil
  a mano para que el robot suelde. BMW lo eligió como primera tarea de un humanoide: >90.000 chapas cargadas en
  11 meses, objetivo 37 s por carga y 99 % de acierto por turno [E]
  (https://www.assemblymag.com/articles/99678-humanoid-robots-complete-trial-project-at-bmw-assembly-plant).
- **Lo real:** células de soldadura por puntos con carga manual (Gestamp, CIE Automotive en Euskadi [I]).
- **La demo en mesa:** rack con 3 tipos de «chapa» (placas impresas de 6 mm con asa o ceja de 20 mm, izquierda,
  derecha y refuerzo) y útil con pins cónicos y topes en V. Segunda estación: el brazo guía (o un servo con
  linterna LED) reproduce una trayectoria fija de «soldadura» con chispa de luz solo si el ESP32 detecta las
  piezas correctas (reed + imanes). El juez elige el modelo en la tablet. Final: el útil se llena, se enciende la
  «soldadura» y sale una pieza montada; contador «X3 n.º 3».
- **Órdenes del VLA:** «carga el lado izquierdo» · «ahora el derecho» (piezas espejo: el criterio es la simetría)
  · «falta el refuerzo, complétalo» · «descarga la pieza soldada a la caja».
- **Por qué solo un VLA:** piezas espejo y variantes en el mismo rack: un programa por punto exige una receta por
  variante; el VLA distingue izquierda/derecha y la frase elige la variante.
- **Fiabilidad:** dejar la placa sobre pins cónicos (±1 cm con chaflanes de 8 mm). Plan B: ACT por variante.
- **Coste:** rack, útil, 9 placas, linterna/servo; ESP32 con 3 reed; 50 ep. por variante (150).
- **Puntos débiles:** se parece a carga de máquina (D); chapas finas y metálicas reales no caben: la placa gruesa
  hay que justificarla; recupera la estética de LeWelder (punto a favor y riesgo de «volver a lo aparcado»).
- **Nota:** necesidad 4 · VLA visible 3 · fiabilidad 4 · momento 5 · frescura 4.

### 3 · Del AMR a la cinta · el robot pasa cubetas del carrito autónomo a una cinta que se mueve, como Digit en GXO
- **Persona y dolor:** Mikel, mozo de un centro logístico: pasa cubetas del robot móvil a la cinta todo el turno.
  Digit lleva >100.000 cubetas en GXO [E] (https://www.agilityrobotics.com/content/digit-moves-over-100k-totes);
  Siemens midió 60 cubetas/h y >90 % de acierto en Erlangen [E]
  (https://www.eweek.com/news/siemens-nvidia-humanoid-factory-trial/).
- **Lo real:** muelle entre AMR y transportador en almacenes de e-commerce y en intralogística de planta.
- **La demo en mesa:** «AMR» (carrito con ESP32 y dos motores, o plataforma giratoria) que trae 2-3 cubetas mini
  (70×50×40 mm, <150 g, con asa) de colores; minicinta impresa con motor que se lleva la cubeta. El juez pide un
  pedido en la tablet y el AMR llega. Final: la línea fluye; contador de cubetas por minuto en pantalla.
- **Órdenes del VLA:** «descarga el AMR a la cinta» · «solo las urgentes (rojas); las demás al palé» · «la vacía,
  apílala» · «devuelve la cubeta al AMR». Cambia criterio y destino.
- **Por qué solo un VLA:** la cubeta llega en posición distinta cada vez (el AMR para ±2 cm y girado); un cobot
  necesita localización y reglas; el VLA se adapta y la frase cambia el criterio.
- **Fiabilidad:** coger una cubeta con el AMR mal parado (asa ancha, ±2 cm); la cinta con embudo de entrada.
  Plan B: AMR sustituido por bandeja fija con tope.
- **Coste:** carrito o plataforma, minicinta con motor, 6 cubetas; ESP32 ×2; 100-120 ep.
- **Puntos débiles:** tarea sencilla para una persona (el dolor es volumen, no dificultad); un AMR casero añade
  riesgo de integración; tema muy logístico para un jurado de LeRobot.
- **Nota:** necesidad 3 · VLA visible 3 · fiabilidad 3 · momento 4 · frescura 3.

### 4 · Enséñale tú · el juez graba una demo con el brazo guía y el robot empaqueta un móvil, como el UR AI Trainer
- **Persona y dolor:** Ane, ingeniera de una pyme que empaqueta por encargo: cada producto nuevo pide reprogramar.
  UR y Scale AI lanzaron en 2026 un sistema líder-seguidor para grabar demos en producción con un ejemplo de
  empaquetado de smartphone (https://www.nasdaq.com/press-release/universal-robots-and-scale-ai-launch-imitation-learning-system-accelerate-ai-model).
  Criterio real: desde dic. 2024 la UE obliga a ofrecer el móvil **sin cargador** (Directiva (UE) 2022/2380,
  https://eur-lex.europa.eu/eli/dir/2022/2380/oj), así que la misma línea saca dos packs.
- **Lo real:** líneas de pack y retractilado manual en logística de electrónica (cos-packing).
- **La demo en mesa:** caja con alojamientos en V; «móvil» (150×75×20 mm), «cargador» (40 mm), «cable enrollado
  rígido» (disco de 50 mm). El juez coge el brazo guía y teleopera un episodio (no entrena en vivo: se enseña el
  flujo); luego pide un pack. Final: caja cerrada que pasa por el «lector» con el pack correcto.
- **Órdenes del VLA:** «pack completo» · «pack UE sin cargador» · «solo reposición de cables» · «saca el cargador
  que sobra». Cambia contenido y criterio legal.
- **Por qué solo un VLA:** el mismo puesto saca variantes por una frase; demo de 20 min en vez de integrador.
- **Fiabilidad:** el móvil en su alojamiento (±1 cm con chaflán). Plan B: ACT por pack.
- **Coste:** caja, 3 piezas ×4, tapa abatible; 50 ep. por pack.
- **Puntos débiles:** es un kit con otro disfraz (E); «enseñar en directo» es promesa a medias; tapa abatible =
  gesto con riesgo.
- **Nota:** necesidad 3 · VLA visible 4 · fiabilidad 4 · momento 4 (el juez teleopera) · frescura 3.

### 5 · Enchufa el servidor · el robot conecta el cable correcto y la máquina arranca, como Foxconn con GR00T
- **Persona y dolor:** Iñigo, técnico de montaje y prueba en una fábrica de servidores de IA: conecta y prueba
  cables de cada bandeja. Foxconn mostró humanoides enchufando cables para su planta de servidores de NVIDIA en
  Houston (https://www.assemblymag.com/articles/99628-foxconn-to-deploy-humanoid-robots-on-production-line-at-houston-ai-server-plant);
  Intrinsic dedicó su reto de IA industrial a cables y conectores
  (https://www.intrinsic.ai/blog/posts/foxconn-and-intrinsic-launch-joint-venture-to-build-the-ai-factory-of-the-future).
  Horas de prueba por bastidor [sin fuente].
- **Lo real:** montaje y prueba de racks (Foxconn, Quanta, Wistron); en Euskadi, cuadros eléctricos (Ormazabal,
  Arteche) [I, sin validar].
- **La demo en mesa:** «rack» de 3 bandejas con LED; conectores impresos de 25 mm con imán y pogo pins que se
  autocentran (±8 mm); cables cortos y rígidos (tubo) colgando de un soporte. El juez «rompe» una bandeja (quita
  un cable o pulsa avería). Final: la bandeja pasa de rojo a verde, ventilador que arranca y sonido de arranque.
- **Órdenes del VLA:** «conecta la bandeja 2» · «la que está en rojo, reconéctala» · «cambia el cable de red por
  el de fibra (azul)» · «desconecta la bandeja para mantenimiento».
- **Por qué solo un VLA:** el cable cuelga distinto cada vez (semideformable): ahí fallan las trayectorias
  grabadas; el VLA corrige con la imagen y la frase elige bandeja y cable.
- **Fiabilidad:** acercar el conector al puerto: lo resuelve el imán en el último cm. Plan B: ACT por bandeja.
- **Coste:** rack, 6 conectores con imán y pogo, 3 LED, ventilador 5 V; ESP32; 120-150 ep.
- **Puntos débiles:** roza la «inserción de precisión» prohibida: solo vale si el imán hace el trabajo y se dice;
  el cable puede engancharse; el «conector» magnético se ve de juguete si no se cuida el diseño.
- **Nota:** necesidad 3 · VLA visible 4 · fiabilidad 2 · momento 5 (la máquina arranca) · frescura 5.

### 6 · El pack del eléctrico · dos brazos montan los módulos de una batería y cambian el que falla, como AEON en BMW Leipzig
- **Persona y dolor:** Nerea, operaria de montaje de baterías de alto voltaje: coloca módulos pesados en la
  carcasa con riesgo eléctrico. BMW eligió esta tarea para el primer humanoide en producción en Alemania (verano
  2026), entrenado con ~20 demos teleoperadas [E]
  (https://robotics.hexagon.com/bmw-deploys-aeon-hexagon-robotics-humanoid/,
  https://www.bmwblog.com/2026/03/03/bmw-hexagon-aeon-humanoid-robot-leipzig-pilot/).
- **Lo real:** montaje de packs en plantas de baterías (BMW, CIC energiGUNE y proveedores vascos [I]).
- **La demo en mesa:** carcasa impresa con 4 huecos en V y 6 «módulos» (bloques 60×40×30 mm, <150 g, con imán);
  el ESP32 «mide» cada módulo (reed o resistencia en la base) y enciende verde/rojo en cada hueco. Segundo brazo
  (el guía en reproducción o con su propia política) pone la tapa. El juez cambia en secreto un módulo por uno
  «defectuoso». Final: 4 verdes, tapa puesta y «coche» de juguete que arranca.
- **Órdenes del VLA:** «monta el pack» · «cambia el módulo en rojo» · «pack de autonomía corta: solo 2 módulos» ·
  «desmonta para reciclar». Cambia cantidad y criterio (estado del LED).
- **Por qué solo un VLA:** el criterio depende de un estado visual (LED) que cambia en vivo; un cobot necesitaría
  integrar la señal y un programa por variante; el VLA lo ve y la frase decide.
- **Fiabilidad:** dejar el bloque en el hueco en V (±1 cm, imán de fondo). Plan B: ACT «colocar» + selector
  programado según el LED.
- **Coste:** carcasa, 6 módulos, tapa; ESP32 con 4 LED y 4 reed; 100-150 ep.
- **Puntos débiles:** el peso real (decenas de kg) queda muy lejos: maqueta honesta pero menos creíble; se
  acerca al tema batería (B) y a kits; la tapa por el segundo brazo duplica riesgo.
- **Nota:** necesidad 4 · VLA visible 4 · fiabilidad 4 · momento 4 · frescura 4.

## Top 2 [R]

1. **Ficha 2 · El ayudante del soldador.** Es la tarea piloto más documentada del mundo (BMW + Figure, con
   90.000 piezas y 37 s de ciclo), el gesto es nuestro punto fuerte (coger y dejar sobre pins cónicos), el
   criterio izquierda/derecha es un buen uso del VLA y el final es el más memorable: dos brazos en línea, el
   segundo «suelda» solo si el primero cargó bien. Frase: «lo que BMW probó con un humanoide de 100.000 $, en
   una mesa con 300 €». Reaprovecha la estética de LeWelder.
2. **Ficha 6 · El pack del eléctrico**, o la **5** si el equipo de CAD valida en el primer día un conector
   magnético que entra 9/10 veces. La 6 junta piloto europeo y reciente (Leipzig), criterio visible por LED que el
   juez manipula y cooperación de dos brazos; la 5 tiene el mejor momento («la máquina arranca») y la mayor
   frescura, pero la peor fiabilidad.

Pendiente: todas las cifras [E] son de las empresas; validar una con un proveedor vasco (carrocería o baterías)
antes del pitch.
