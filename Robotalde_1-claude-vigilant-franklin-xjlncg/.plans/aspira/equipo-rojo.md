# Aspira · equipo rojo (jueves 19-11-2026)

Encargo: demostrar cómo pierde Aspira y qué cambiar. Fuentes: `concepto-base.md`, `procesos.md`, `gestion-robot.md`,
`hardware.md`, `../brief2/directrices-necesidad.md`, `../brief/evento-novedades.md` y `../brief/equipo-rojo.md`.
No hay ningún dato nuevo: lo que no sale de esos documentos es aritmética sobre ellos o va marcado **[est.]**.

**Las cinco grietas que ningún informe ha escrito:**

1. **La cartulina negra no va a enseñar nada al taladrar.** Va *debajo* de la pieza, y el agujero es ciego (tope a
   12 mm en tabla de 18, `hardware.md` §5). La viruta de pino sale por las estrías y se queda *encima de la tabla*,
   en anillo (`procesos.md` P1). Con Aspira y sin Aspira, la cartulina queda casi igual de limpia [est.]. El
   «momento memorable» de la decisión 5 no ocurre.
2. **El propio concepto nombra el apaño que mata la prueba 4:** «el adaptador "para taladrar solo"» y la boquilla
   Festool van montados en la herramienta: no necesitan una segunda persona. La orbital ya trae su toma
   (`procesos.md` P3). Y el plan de medida quita la caja de polvo de la EasySander (`hardware.md` §5): un jurado de
   industria lo verá como empeorar el apaño a propósito.
3. **Un intento no cabe en el tiempo.** Orden → Ready 20 s + taladrar 10 s + retirada 5 s + `Put the nozzle back` 18
   s + `/reset` 5 s + reponer escena (tabla, marca, cartulina) ≤ 60 s ≈ **2 min por intento, 10 min los cinco**
   [aritmética sobre `gestion-robot.md` §6]. El slot es de 5 minutos por equipo, con presentación incluida.
4. **El fuelle de desagüe bajo vacío es un pistón.** Un tubo extensible cerrado por fuera y con depresión dentro se
   acorta: fuerza axial ≈ ΔP × área. Con Ø 40 mm (12,6 cm²) y solo 20 mbar de depresión en ese tramo ya son ~2,5 N;
   con 100 mbar, ~12 N [est., aritmética]. El hombro sostiene ~9 N en la punta antes de bloquear (2,94 N·m / 0,33 m,
   versión de 12 V). La comprobación 1 de `hardware.md` se hace **con la aspiradora apagada**: no lo vería.
5. **Las piezas de hardware duplican el riesgo de agarre:** coger un mango del soporte, encajar un cono con imanes,
   soltar inclinando 15° y volver a cogerlo, con una pinza de 2 dedos, ±1 cm y un equipo que nunca ha teleoperado.
   Es la parte más difícil del plan y no da puntos por sí misma.

## 1. Contradicciones entre los tres informes, y la versión buena

| Tema | `procesos.md` | `gestion-robot.md` | `hardware.md` | **Versión buena** |
|---|---|---|---|---|
| Qué coge la pinza | Boquilla con aleta o, «mejor, fijada a la muñeca» | Varias boquillas con asa común y su propio tubo fino; las coge del soporte | Un mango fijo con cabezales intercambiables por imanes; aparcado = mango encajado y pinza abierta | **Rama C' ya hoy:** mango atornillado a la pinza, un cabezal, sin soporte. Cambio de cabezal *a mano* entre procesos, fuera de la nota |
| Aparcado | — | `/reset` vuelve «con la boquilla en la pinza»; `Put the nozzle back` sale de aparcado | Aparcar exige dejar el cabezal y soltar el mango: otra habilidad | Aparcado = `/reset` con el mango puesto. Se borra `Put the nozzle back` (30 episodios menos) |
| Tubo final | Ø 20-25 mm, 50-80 g | Ø 20-25 mm, ≤ 150 g | Fuelle Ø 40, ≤ 80 g | **Ø 32-40.** Con Ø 20 y 25 l/s el aire iría a ~80 m/s [aritmética]: la pérdida de carga se come el caudal que `procesos.md` §0 da por supuesto |
| Distancia | §0: 30-60 mm; P1: 20-40 mm del eje | 30-60 mm en el texto; 20-40 en la tabla; vigilante 15-40 mm de la marca | Centro a 35 mm del eje, arco R 25 | **Una sola cota:** centro de la boca a 35 ± 10 mm del eje; ninguna pieza a < 15 mm del eje. El vigilante acepta 25-45 mm (hoy rechazaría aciertos de 40-45) |
| Órdenes | «voy a taladrar aquí», «lijar el borde izquierdo» | 5-6 frases en inglés + voz con LLM | — | `drill at the mark` · `sand the left edge` · `sand the right edge`. Entrada principal: **pedal y botones**; la voz encima |
| Niveles | N1 P1, N2 canto, N3 P2 o seguir | N1, N2 + atornillar, N3 seguir/P2 | sin niveles | N1 taladrar, N2 un canto (lija a mano), N3 solo vídeo |
| Color | — | Marca roja de 2 cm; boquilla redonda naranja | Marca naranja Ø 8; **C1 naranja** | Marca y boquilla de colores opuestos (marca verde o azul, cabezal naranja): hoy el vigilante confundiría ambas |
| Grabar con broca girando | — | Nunca; 5 episodios solo para validar | ~75 agujeros con broca girando en grabación | Lo de `gestion-robot.md`. Con eso bastan 8-10 tablas, no 20 |
| Impresión | — | — | 18 h clásica «en un día», con lanzamientos solapados (S a las 14:15 dura 4 h y C2 sale a las 17:30) | Imposible con una impresora. Sin soporte S ni C2: mango + C1 + adaptador + soporte de cámara ≈ 7,5 h clásica [suma de §7]. Lo demás, sustitutos de madera |
| Software | — | 15,5 h para 2 × 9 h; 1-7 = 11,5 h | — | 11,5 h sin integración es optimista ×1,5 [est.]. Quitar 8 y 9, recortar 3 (ver §6) |
| Compra | 3 aspiradoras | — | 390-440 € (la suma da 389-425 €, aspiradora incluida) | Sin lijadora eléctrica (−79 €) y con la aspiradora y el taladro del local o del equipo: ≈ 150-200 € [aritmética] |

## 2. Autopsia anticipada: domingo 13:00, sin podio

| # | Causa | Señal temprana | Cuándo | Medida más barata |
|---|---|---|---|---|
| 1 | **El valor no se ve:** cartulina igual de limpia con y sin robot; viruta gruesa a 25-35 mm de una boca que solo capta a 1,5 diámetros | Comprobación 3 de hoy: anillo de viruta igual en A y B | **Hoy 17:30** | Cara superior de la tabla **negra** (vinilo o spray mate): la viruta clara se ve en la propia pieza. Medir hoy A/B; si no hay diferencia clara, cambiar de proceso (lija a mano o P2 vertical, donde la viruta cae por gravedad a la boca) |
| 2 | **No caben 5 intentos en 5 min** | Ensayo cronometrado del sábado > 60 s por intento | Sáb 18:00 | Tarea declarada sin devolver boquilla ni reponer: 5 marcas pegadas a la vez por el juez en una tabla; aparcado → Ready → taladro 3 s → pedal → aparcado ≈ 40 s [est.] |
| 3 | **El agarre del mango y el cambio de cabezal fallan** (imanes, inclinar 15°, volver a coger) | < 8/10 cambios por teleoperación | Vie 19:30 | Rama C' hoy, no el viernes: mango fijo a la pinza |
| 4 | **Par del hombro:** 0,86 N·m con contrapeso, por encima del nominal de 7,4 V (0,49) y sostenido minutos; el servo se calienta, cede o se protege | El brazo baja durante «mantener»; temperatura del servo | Vie 18:30 | Cabezal con **patas apoyadas** en la tabla: la mesa carga el peso al mantener. Trabajar a r ≤ 230 mm. Mirar la etiqueta del servo a las 18:00 |
| 5 | **El fuelle tira del mango al encender la aspiradora** (grieta 4) o se aplasta | El mango se desplaza al encender | **Hoy** | Repetir la comprobación 1 con la aspiradora **encendida**. Si tira: manguera de aspiradora de mano (pared rígida) o tramo de tubo PVC liso con un codo |
| 6 | **La boca se pega a la mesa:** 8-20 N de vacío (`hardware.md` §1) contra 1,5-3 N de imanes; al retirarse, el cabezal se queda | El cabezal queda pegado en la prueba de hoy | Hoy | Patas de 5-8 mm y **ranura de alivio** lateral en el cabezal; sin imanes si el cabezal va fijo |
| 7 | **La organización no deja hacer polvo ni ruido** (140 personas, aspiradora de 74 dB(A) continua, detectores de humo [est.]) o la mesa no admite 1,2 × 1,5 m y un poste de 1 m | Sin respuesta al correo; el viernes 17:45 el mentor dice «aquí no» | Hoy / vie 17:45 | Correo hoy (§5) y versión de la demo sin polvo real preparada |
| 8 | **El viernes no se graba** (3 h; montar banco, pescante, contrapeso, cámaras y aprender a teleoperar) | 19:30 sin un episodio válido | Vie 19:30 | Banco montado y probado hoy; ensayo de `lerobot-record` en seco; solo `drill` hasta 50 |
| 9 | **«Visión + IK» y «el adaptador del taladro hace lo mismo»** en las preguntas | Ensayo del pitch con alguien de fuera hoy por la noche | Hoy noche | §3 y §4: respuesta medida, no retórica |
| 10 | **Ruido y voz:** la aspiradora enmascara el fin por sonido y la voz; el interbloqueo por micro no distingue taladro de aspiradora | RMS del micro saturado con la aspiradora sola | Vie 20:00 | Pedal USB como entrada única en los 5 intentos; quitar el fin por sonido |

Menores: tubo colgante que tapa la cámara `top` y oscila al moverse el brazo (distractor para la política); `/reset`
arrastrando las patas sobre la pieza; Andoni solo con CAD, compras en Barakaldo, impresión y montaje en el mismo día.

## 3. ¿Sigue siendo una necesidad evidente cuando se ve la demo?

| Prueba | En el papel | En la mesa, como está planeado |
|---|---|---|
| 1 Se ha vivido | Pasa | Pasa |
| 2 Una frase | Pasa («aguántame la aspiradora») | Pasa |
| 3 Apaño | Pasa: tubo sujeto por otro, pósit, adaptador | **Se vuelve en contra:** el adaptador y la toma de la orbital ya resuelven sin segunda persona |
| 4 Segunda persona | Pasa en el relato | **Dudosa:** el jurado ve un brazo que en 20 s deja un tubo quieto junto a una marca. Un brazo articulado con base magnética o un sargento con la boquilla hacen lo mismo para *un* agujero, y la mano lo coloca en ~5 s [est.]: es el «lo cojo yo en 3 s» de Aprendiz |

**Dónde está lo que solo hace el robot:** no en sujetar quieto (eso lo hace un soporte), sino en (a) **moverse solo al
siguiente punto** mientras las dos manos siguen en la herramienta y la pieza; (b) **servir a cualquier herramienta**,
incluidas las que no tienen toma (lija a mano, palma sin toma, multiherramienta); (c) **elegir el lado libre** según
dónde está la mano o el sargento. Ninguna de las tres está hoy en la tarea puntuada.

**Los 3 cambios que más refuerzan el valor visible sin subir el riesgo:**

1. **Hacer visible el polvo donde cae:** tabla con cara superior negra mate y la mitad izquierda taladrada sin Aspira
   (el apaño de verdad: tubo apoyado a 15 cm) antes de los intentos; los cinco agujeros puntuados en la mitad derecha.
   El jurado ve las dos mitades a la vez. Coste: un vinilo; ningún gesto nuevo del robot.
2. **Serie de marcas sin soltar la herramienta:** el juez pega varias marcas; con el pedal, el robot pasa a la
   siguiente. Medir hoy, sin robot, cuántas veces suelta la herramienta alguien que reposiciona un brazo articulado o
   un sargento en 5 agujeros, y el tiempo. Titular: «0 veces frente a N». Es el mismo gesto aprendido.
3. **Comparar con el apaño honrado, no con un apaño saboteado:** no quitar la caja de polvo de ninguna lijadora; el
   proceso de lijado de la demo es **lija a mano con taco** (no tiene accesorio, es silencioso, el polvo fino se ve
   sobre la tabla negra). Decir en voz alta: «para el taladro existe un adaptador; Aspira es para las herramientas y
   los puntos que no lo tienen».

## 4. ¿Hace falta de verdad un VLA?

Con un solo cabezal y frases que eligen entre «marca», «canto izquierdo» y «canto derecho», **no**: una pegatina de
color + IK lo hace, y `gestion-robot.md` §4 ya lo reconoce (rama C). Un jurado de Ikerlan o de la EHU lo dirá en 10 s.

**Lo único que el aprendizaje aporta de verdad**, y que cuesta programar: **colocar con contacto y en el lado libre**
según la escena: la mano que sujeta la pieza, un sargento, el taladro apoyado, el canto girado. Eso sí cambia la
postura de forma que una regla de color no captura sin un detector de manos y casos especiales.

**Cómo se demuestra en 5 minutos:**
- En uno de los intentos, el juez pone **su mano o un sargento** donde quiera junto a la marca; el robot coloca la
  boquilla al otro lado. Grabar el 50 % de los episodios con mano o sargento a izquierda y a derecha (ya está previsto
  para la mano en `gestion-robot.md` §7: ampliarlo al lado).
- Una diapositiva con la **rama C medida como línea base** (color + IK, que se escribe hoy sin robot reutilizando
  `seguimiento.py` y `sim/cinematica.py`): X/10 de cada una con mano y sargento. Si el VLA no gana en algo, la
  rama C es la demo y el VLA se cuenta como experimento; mentir aquí cuesta más que perder 10 puntos de innovación.
- Un clip de 20 s: «canto derecho, 35 demostraciones, 40 minutos, ninguna línea de código nueva».

## 5. Seguridad y permiso de la organización

**Correo hoy** a `gazteria@bilbao.eus` y a Bravo Robots (copiar a ambos), cinco preguntas cerradas:
1. ¿Podemos usar en la mesa un taladro a batería (ráfagas de 3-5 s en pino, sin percusión) y lijar a mano?
2. ¿Y una aspiradora de taller de red (850 W, ~74 dB(A)) encendida durante la demo? ¿Hay enchufe propio?
3. ¿Qué superficie tiene cada equipo, y podemos traer un tablero de 70 × 67 cm con un poste de 1 m?
4. ¿Cómo se hace la demo: mesa por mesa o escenario, y cuántos minutos por equipo?
5. ¿Material y piezas propias permitidos? ¿Requisitos de EPI o seguro?

**Plan si no dejan polvo o ruido (decidir el viernes 17:45, no después):**

| Respuesta | Demo |
|---|---|
| Sí a todo | Tabla negra, taladro real en ráfagas de 3 s, aspiradora encendida, gafas y FFP2 al alcance |
| Taladro no, aspiradora sí | **Lija a mano** como tarea puntuada (silenciosa); el taladro, en vídeo |
| Nada de polvo | **Fuente de polvo de prueba:** embudo impreso que deja caer 2 g de serrín tamizado en la marca a ritmo fijo; A/B medible y repetible. Taladro real solo en el rincón que asignen, o en vídeo |
| Sin aspiradora | La tarea puntuada es la colocación (sin flujo); la captación se enseña en el vídeo del jueves y viernes |

Siempre: solo pino; nada de MDF ni madera dura; gafas EN 166 para quien taladra; el juez mira desde el lado de la
cámara; aspirar la mesa al final; la parada es `/reset`, nunca `/stop` (el brazo cae).

## 6. Alcance

**Quitar hoy:**
- Cabezales intercambiables, soporte S × 3, imanes, `Put the nozzle back` y aparcar soltando el mango (rama C' ya).
- La lijadora eléctrica y su compra; seguir la lijadora (`seguir.py`, 3 h) y P2 vertical como nivel.
- Fin por sonido, interbloqueo por micro y LLM de voz: pedal y botones (reglas de voz solo si sobra).
- «Atornillar» como control negativo (15-20 episodios el sábado que compiten con lo que puntúa).
- Contador de partículas, báscula de 0,01 g y balance de masas: la foto de la tabla negra basta.
- Vigilante con detección de herramienta y distancias: dejar solo «boquilla dentro de la plantilla → Ready».

**No quitar nunca:**
- **Hoy, sin robot:** prueba A/B de captación con la aspiradora real, la tabla negra y el cabezal C1 sujeto a mano; la
  comprobación del contrapeso **con la aspiradora encendida**; la prueba del vacío pegando la boca a la mesa.
- El correo a la organización hoy.
- Banco propio atornillado con cámaras fijas y foto de referencia; comandos de LeRobot 0.7 probados en seco.
- La rama C (color + IK) escrita hoy: es el seguro de los 30 puntos y la línea base del §4.
- ACT de `drill` entrenando el viernes por la noche; checkpoints por X/10, nunca por la pérdida.
- Serie de 5 completa y cronometrada desde el sábado 18:00; dataset al Hub; dormir.

## 7. Veredicto

**Probabilidad de podio: 15 % (rango 8-25 %) [est.]; primer puesto ~5 %.** Base: más de 20 equipos y 3 premios
(8-15 %). A favor: necesidad mucho más evidente que Aprendiz, herramienta real que arranca delante del jurado (encaja
con «física, fricción»), física citada. En contra: equipo sin SO-101, la parte más difícil del hardware (cambio de
cabezal) no puntúa, el valor no se ve con el montaje actual y el slot no da tiempo. Con los cambios de §1, §3 y §6, y
un A/B claro hoy, subo a **20-30 %** [est.].

Los tres factores que más la mueven:
1. **La prueba A/B de esta tarde.** Si la tabla negra no muestra diferencia clara, no hay momento memorable ni
   utilidad visible: o cambia el proceso hoy, o el concepto cae a la mitad baja.
2. **Aciertos del domingo, que dependen de quitar el cambio de cabezal.** De 3/5 a 5/5 son 12 puntos; con mango fijo
   y patas apoyadas el gesto queda en «llegar y apoyar», el más fiable del SO-101.
3. **La respuesta a «un soporte o el adaptador hace lo mismo» y a «visión + IK»:** serie de marcas sin soltar la
   herramienta, lado libre según la mano, y la rama C medida al lado. Sin eso, utilidad 8-9 de 15 e innovación baja.

**Recomendación:** antes de imprimir el mango, pasar hoy a la rama C', hacer la prueba A/B con tabla negra y la del
fuelle con vacío, mandar el correo y pedir al usuario el «sí» explícito con las cinco grietas a la vista.
