# Ideas desde el top de Hugging Face (18-11-2026)

Fuente: [top-huggingface.md](../../investigacion/proyectos/top-huggingface.md) y [README](../../investigacion/proyectos/README.md).
Restricciones y formato: [encargo-ideas.md](encargo-ideas.md). Fuera: Machero, Relevo, soldadura, camarero, baterías,
Cuelga, asistencia. Filtros añadidos tras el rechazo de Machero: **tema que se reconoce al instante**, **necesidad
evidente sin explicarla**, **demo viva con movimiento y final que se ve**.

## Proyecto → mecanismo → idea industrial derivada

| Proyecto | Mecanismo de éxito | Idea industrial derivada (SO-101) |
|---|---|---|
| Unfolding Robotics (camisetas) | Datos curados (+50 pts), DAgger con correcciones humanas, RTC, 90 % en 20 ensayos, vídeo de 15 min sin cortes | **Rescate**: robot autónomo que, cuando duda, pasa el mando a un operador remoto (el juez con el brazo guía); cada rescate es un episodio DAgger |
| Prompting Robots (`/subtask`) | Cambiar la orden **a mitad de movimiento**; restricciones en lenguaje ("la manzana sin tocar el yogur"); `/vqa` | **Desvío** (cambio de ruta de un paquete en el aire) y **Paletizado con criterio** ("lo frágil arriba") |
| Steer a robot with words | Planificador VLM → biblioteca de habilidades resaltada en pantalla | Reconfigurar un útil modular por referencia (SMED). Descartada: proceso oscuro, parecido a Relevo |
| XLeRobot | Precio (660 $), dos brazos, teleoperación con mando/VR | Teleoperación remota como respaldo (se funde en Rescate). Bimanual imposible: solo hay un seguidor |
| LeKiwi | Movilidad barata, robot oficial | Brazo que va a la máquina (AMR). Fuera: mesa fija, ya estudiado (P3) |
| Reachy Mini Conversation | Voz interrumpible (*barge-in*), señales de vida, personalidad | "¡Para, esa no!" como corrección por voz: se suma a Desvío y Paletizado |
| Reachy Phone Home | Reacción emocional simple a un error humano detectado (372 likes) | **Ojo**: el juez monta a mano, el robot pilla el fallo, lo corrige y el personaje reacciona |
| Baby Reachy-Mini | Evento → acción + foto al móvil; lo crítico en código | Andon: una máquina para (ESP32) y el robot desvía + avisa al jefe de turno (se suma a Desvío) |
| FLUX 3 Action SO-101 | Modelo grande dedicado, normalización y límites rigurosos | Ensayo en gemelo digital antes de mover. Fuera: sin escena física, no cabe en 48 h |
| GR00T N1.5 "table cleanup" | Tarea universal de recoger la mesa; con pocos episodios ignora el texto | **Sombra**: el robot deja el panel de herramientas del puesto (5S) listo según el turno |
| robot_MCP | Un LLM manda al brazo por chat | Célula que se reconfigura desde el texto del pedido. Floja: el LLM razona, el VLA no se ve |
| Dum-E | Voz → agente → VLA, ayudante de taller | Pañol que entrega la herramienta pedida en una bandeja (se suma a Sombra) |
| phosphobot | Herramienta de teleoperación (VR) y entrenamiento | Teleoperación remota (se suma a Rescate) |
| [Ref.] SmolVLA base | Inferencia asíncrona: +30 % de velocidad sin perder éxito | Ritmo medido en pantalla (piezas/min): sirve para cualquier ficha |
| [Ref.] svla_so101_pickplace | 50 episodios bastan para un pick-and-place | Referencia nueva en 50 demos. Fuera: ya descartada como P4 (entrenar en vivo no cabe) |
| [Ref.] SO-101 MuJoCo | Recompensa por fracción completada, evaluación sin robot | Marcador "X/10" medido; probar la tubería antes del hackathon |

## Las 5 fichas (ordenadas con los tres filtros)

### 1. Pila Sabia · el robot monta el palé del pedido y obedece reglas dichas en voz alta ("lo frágil arriba")
**Mecanismo tomado de:** Prompting Robots (restricción en lenguaje + `/subtask` a mitad de movimiento).
- **Persona y dolor:** preparador de pedidos de un almacén; levanta cajas todo el turno. El 52,4 % de los trabajadores
  de la UE declara dolor de espalda (EWCS 2024, vía OSHwiki: https://oshwiki.osha.europa.eu/en/themes/health).
- **Lo real:** paletizado mixto que hoy se hace a mano en almacenes de distribución; a escala lo hacen Mujin o Symbotic
  con reglas programadas por referencia.
- **La demo en mesa:** 6-8 cajas impresas de 40-60 mm (pesada con lastre, "frágil" con icono de copa, grande, pequeña)
  y un palé de 12 × 10 cm con esquinero en V. El juez dicta la regla; el robot apila; al final, torre estable y el
  juez la "precinta" con film (o la sopla para ver que no cae).
- **Órdenes del VLA:** "pesadas abajo" · "lo frágil siempre arriba" · "pedido pequeño: solo dos alturas" · a mitad
  de movimiento: "¡esa no, es frágil, déjala para el final!". Cambia el **criterio de orden**, no el objeto.
- **Por qué solo un VLA:** un cobot necesita la secuencia por referencia; aquí la misma escena da torres distintas según
  la frase, y la corrección en el aire no se programa.
- **Fiabilidad:** dejar una caja encima de otra (±1 cm); cajas con chaflanes y tapas con reborde que centran. Plan B:
  ACT por regla (3 modelos) y selector por voz.
- **Coste:** 8 cajas, palé con esquinero, film decorativo; sin electrónica. ~50 episodios × 3 reglas = 150.
- **Puntos débiles:** se parece a G (estuche mixto); el VLA puede aprender un orden fijo si no se varían las posiciones;
  una torre que cae en vivo es muy visible.
- **Nota 1-5:** necesidad 4 · VLA visible 5 · fiabilidad 3 · momento 5 · frescura 4.

### 2. Rescate · el robot trabaja solo y, cuando duda, el juez lo rescata a distancia con el brazo guía
**Mecanismo tomado de:** Unfolding Robotics (DAgger con correcciones humanas, tasa medida) + XLeRobot/phosphobot (teleoperación).
- **Persona y dolor:** "jefe de tripulación remoto" que vigila varios robots de picking; una persona puede supervisar
  10-50 robots e intervenir unos 6 s por caso (Plus One Robotics: https://www.robotics247.com/article/how-supervised-autonomy-keeps-robot-arms-moving).
- **Lo real:** Plus One Robotics (Yonder) en centros de paquetería; el robot pide ayuda cuando su confianza baja.
- **La demo en mesa:** cubeta con 8 productos revueltos (40-60 mm) y cinta/tolva de salida. Pantalla: "autónomo 7/8".
  Una pieza tumbada en mala postura: el robot se para, la pantalla pide ayuda y el juez coge el brazo guía y la saca él;
  el contador suma "correcciones aprendidas: 1" y se ve el siguiente agarre autónomo.
- **Órdenes del VLA:** "saca solo los azules" · "todo menos los frágiles" · "primero los del pedido urgente" (criterio).
- **Por qué solo un VLA:** el traspaso de mando fluido y aprender de la corrección son de una política aprendida; un
  cobot programado no mejora con el rescate.
- **Fiabilidad:** el cambio política → teleoperación → política sin saltos (bajar velocidad, mismo origen); fallo
  forzado con una pieza preparada. Plan B: ACT y el rescate solo como teleoperación, sin reentrenar.
- **Coste:** cubeta, 8 productos, tolva; un botón ESP32 "pido ayuda". ~120 episodios + script de intervención.
- **Puntos débiles:** reentrenar en vivo no cabe (se enseña el episodio guardado y un modelo de la víspera); el fallo
  debe parecer espontáneo sin serlo.
- **Nota 1-5:** necesidad 4 · VLA visible 4 · fiabilidad 4 · momento 5 · frescura 5.

### 3. Desvío · el paquete cambia de camión en el aire cuando el jefe de muelle lo dice
**Mecanismo tomado de:** Prompting Robots (`/subtask` a mitad de movimiento) + Baby Reachy (evento → acción + aviso).
- **Persona y dolor:** jefe de muelle de un centro de paquetería en campaña; en 2022 se enviaron 161.000 millones de
  paquetes, 5.102 por segundo (Pitney Bowes: https://www.sdcexec.com/transportation/press-release/21198471/pitney-bowes-inc-pitney-bowes-study-global-parcel-volume-exceeds-100b-for-first-time-ever).
- **Lo real:** clasificación por rutas en centros de Amazon, Correos o SEUR; hoy reasignar una ruta llena es manual.
- **La demo en mesa:** 6 paquetes con etiqueta grande de ciudad, 3 "camiones" impresos con embudo. El juez, de jefe de
  muelle, pulsa "camión lleno" (ESP32, la luz se pone roja) o dice "Bilbao va lleno, a Vitoria": el brazo cambia de
  destino con el paquete en la mano; al móvil llega la foto del cambio.
- **Órdenes del VLA:** "cada paquete a su ciudad" · "lo urgente al primer camión" · "Bilbao lleno: a Vitoria" ·
  "¡para, ese vuelve!".
- **Por qué solo un VLA:** leer la etiqueta y cambiar el plan en mitad del gesto sin reiniciar.
- **Fiabilidad:** soltar en un embudo de 8 cm (fácil); el riesgo es la redirección (RTC/asíncrona). Plan B: ACT por
  destino, el cambio solo entre paquetes.
- **Coste:** 6 paquetes, 3 camiones, luz y botón ESP32. ~40 episodios × 3 destinos + 30 de redirección.
- **Puntos débiles:** en el fondo cambia el destino, no un criterio; recuerda a Flip & Ship (paquetería).
- **Nota 1-5:** necesidad 4 · VLA visible 4 · fiabilidad 4 · momento 4 · frescura 3.

### 4. Sombra · el robot deja el panel de herramientas listo para el turno que le digas
**Mecanismo tomado de:** GR00T N1.5 "table cleanup" (recoger la mesa) + Dum-E (ayudante de taller por voz).
- **Persona y dolor:** técnico de mantenimiento; se pierden entre 10 y 60 min al día buscando herramientas (Abax,
  https://www.abax.com/blog/did-you-know-construction-workers-spend-38-hours-annually-looking-for-their-tools; cifras de
  fabricantes de seguimiento, construcción, no fábrica).
- **Lo real:** paneles de siluetas 5S en todo taller; hoy cada operario recoge (o no) al acabar.
- **La demo en mesa:** 5 herramientas impresas gruesas (llave, martillo, calibre, destornillador, mazo) tiradas por el
  juez; panel inclinado con siluetas en V. El robot cuelga cada una en su silueta; el panel se ilumina en verde.
- **Órdenes del VLA:** "recoge el puesto" · "prepara para mantenimiento eléctrico: deja fuera destornillador y
  calibre" · "dame la llave" (a una bandeja) · "¿qué falta?" (`/vqa`).
- **Por qué solo un VLA:** objetos en cualquier postura y la frase decide qué se guarda y qué se deja fuera.
- **Fiabilidad:** colgar en silueta (±1 cm con V abierta). Plan B: ACT de "recoger" y bandeja en vez de panel.
- **Coste:** 5 herramientas, panel con siluetas, LED con ESP32 e interruptores. ~120 episodios.
- **Puntos débiles:** necesidad poco espectacular; cifra de construcción; puede parecer "recoger juguetes".
- **Nota 1-5:** necesidad 3 · VLA visible 4 · fiabilidad 4 · momento 3 · frescura 4.

### 5. Ojo · el juez monta el coche del cliente y el robot le pilla el fallo y lo corrige
**Mecanismo tomado de:** Reachy Phone Home (reacción emocional a un error humano detectado).
- **Persona y dolor:** operario de una línea de automoción con modelos mezclados; los errores humanos causan el 23 % de
  las paradas no planificadas [fuente secundaria sin estudio citado: https://atlascopco.com/ro-ro/itba/expert-hub/articles/top-5-mistake-proofing-techniques-to-achieve-first-time-quality-in-your-manufacturing-facility].
- **Lo real:** poka-yokes y verificación por visión en líneas como Mercedes Vitoria; hoy marcan el error, no lo corrigen.
- **La demo en mesa:** coche de juguete de 3 piezas gruesas (chasis, techo, alerón de colores) en un nido. Pantalla con
  el pedido del cliente. El juez monta (y se equivoca de techo); el robot quita el techo malo, pone el bueno y el
  personaje le pica ("¡ese techo era para el de ayer!").
- **Órdenes del VLA:** "el cliente quiere techo rojo" · "versión deportiva: con alerón" · "versión básica: sin alerón".
- **Por qué solo un VLA:** el error es distinto cada vez y la frase define qué es correcto.
- **Fiabilidad:** quitar y poner el techo con encaje cónico (±1 cm). Plan B: ACT y el robot solo retira lo malo.
- **Coste:** 3 coches, 6 techos/alerones, nido. ~120 episodios.
- **Puntos débiles:** cercano a F (fin de línea) y a kits por variante; necesidad con cifra floja.
- **Nota 1-5:** necesidad 3 · VLA visible 4 · fiabilidad 3 · momento 4 · frescura 3.

## Top 2

1. **Pila Sabia.** Tema que todos reconocen (un palé de almacén), necesidad evidente (la espalda) y final que se ve
   (una torre que no cae). Es la única en la que la frase cambia un **criterio** de verdad, y la corrección a mitad de
   movimiento da el momento. Riesgo: la estabilidad de la torre; se mitiga con cajas que encajan.
2. **Rescate.** Lo más fresco: nadie ha llevado un "jefe remoto" a un hackathon, el juez toma el mando con el brazo guía
   y el fallo deja de ser un riesgo para ser parte del guion. Se puede **sumar a Pila Sabia** como capa de recuperación
   (si una caja queda mal, el juez la rescata), lo que juntaría lo mejor de los dos.
