# A fondo · Tercera mano de taller (18-11-2026)

Leyenda: [H] hecho con fuente leída · [H·b] solo visto en el extracto del buscador · [I] inferencia · [R] recomendación.

## Resumen

**«Dale la vuelta»**: el SO-101 sostiene la placa mientras el juez suelda de verdad un componente de inserción. El
robot coge la placa en su marco de donde la dejen, la presenta por la cara que se le pide por voz (cara de
componentes para meter la pieza, cara de pistas inclinada hacia la persona para soldar), la sujeta quieta y, al
oír «terminado», la deja en la bandeja de acabadas, donde se enciende un LED. Sub-aplicación elegida: **montaje de
electrónica de inserción** (aficionado, taller de reparación, retrabajo y prototipado en industria). El ciclo real
«meter el componente arriba → dar la vuelta → soldar abajo» es justo donde las manos auxiliares fallan.
Nota global: **3,5/5**. Encaja con lo que pide el usuario (herramienta real, colaboración, poco riesgo de fallo).
Puntos débiles: se parece de tema a MSN y el VLA no es imprescindible.

## 1. Necesidad (con fuentes)

- **Cuánta gente.** No hay una cifra fiable de makers que suelden. Las que hay son parciales:
  - EE. UU.: unos 117.700 empleos de instaladores y reparadores eléctricos y electrónicos en 2025, 65.500 de ellos
    en equipos comerciales e industriales [H·b] (BLS OOH).
  - UE: unas 196.700 empresas en la división 95 (reparación de ordenadores y de artículos personales y del hogar)
    en 2021. El 25,2 % son del grupo 95.1 (ordenadores y comunicaciones) [H·b] (Eurostat), lo que da unas
    49.600 empresas [I].
  - Unos 3.800-4.000 Repair Cafés en el mundo [H·b] (Wikipedia, Back Market). La electrónica de consumo es la
    categoría que menos éxito de reparación tiene [H·b] (análisis secundario de Repair Monitor).
  - Joyería: en la encuesta de Dextera (UPenn), los joyeros dicen pasar casi media jornada soldando, y la mayor
    parte de ese tiempo «solo ajustando» la pieza [H·b].
- **Qué se usa hoy.** Manos auxiliares con pinzas de cocodrilo (SparkFun Third Hand, 38,50 $ [H·b]), brazos de
  manguera segmentada (QuadHands, Loc-Line), soportes de PCB (Panavise, Hakko Omnivise), masilla adhesiva o un
  compañero que sujeta [H] [H·b].
- **Quejas concretas.**
  - EEVblog, hilo «A better helping hands tool»:
    - [H] «hardly ever use them»: no ahorran tiempo, así que acaban fuera del banco para ganar sitio.
    - [H] Los Omnivise «can be a bit of a pain… if you need to reposition the board».
    - [H] Con placas grandes son «cumbersome to move and impossible to incline».
    - [H] La pinza de cocodrilo «doesn't seem to stay where I put it».
  - EEVblog 2012: «Helping hands are useless» [H·b].
  - IntoFPV: los brazos flexibles «spring back a few millimeters» [H·b].
  - Reseña Hobby Creek: las juntas se agarrotan y la pinza no gira [H·b].
  - Guías de compra: los cuellos de cisne ceden con una placa pesada y el cocodrilo no sujeta bien una PCB [H·b].
  - Reddit r/soldering: el buscador no devolvió hilos, así que no se cita.
- **Seguridad.** En 2018, NEISS estima 11.500 visitas a urgencias en EE. UU. con herramientas de soldar, soldadura
  fuerte y corte. El 16 % (unas 1.800) fueron quemaduras térmicas [H·b]. El riesgo es mayor cuando uno empieza
  [H·b] (Safety+Health).
- [I] El dolor real no es «sujetar»: es **reorientar**. Cada vuelta a la placa obliga a soltar el soldador, abrir
  la pinza, girar, volver a apretar y recolocar. La herramienta pasiva solo guarda una postura; la que se pide por
  voz sustituye a la mano humana que la gira.

## 2. Productos y robots que ya existen

| Qué | Tipo | Estado | Por qué no triunfó [I salvo nota] |
|---|---|---|---|
| Robotic Helping Hand (J. Belofsky) | 2 servos + Arduino, estabiliza la PCB | Kickstarter financiado: 3.489 $ de 350 $, 63 mecenas [H·b] | Nicho mínimo; posturas fijas por botón, sin percepción |
| Dextera (UPenn) | Brazo de 5 GDL con voz, para joyería | Proyecto universitario; no se encontró producto ni precio [H·b] | Comandos de posición «a ciegas»; caro de fabricar |
| Brazo de voz «lab helping hand» (Hackster) | Kit de eBay + voz | Proyecto de un aficionado [H·b] | Órdenes de articulación, no de tarea |
| Makerarm, Z-Arm | Brazos de sobremesa con cabezal de soldar | Kickstarter; Makerarm a 1.399 $ [H·b] | Automatizan la soldadura, no ayudan a la persona |
| Omnifixo, GRS, Panavise | Sujeción pasiva modular | En venta [H·b] | Triunfan porque son baratos y no fallan: son el listón |

[I] Patrón: los robóticos se manejan por articulaciones o posturas grabadas («sube 10°»). Mover a mano una manguera
segmentada es más rápido. Ninguno entiende «enséñame la cara de soldar» ni encuentra la placa donde la dejaste.

## 3. Por qué hace falta un VLA (sin exagerar)

- La placa no está siempre en el mismo sitio: el juez la suelta donde le viene bien, girada, y a veces con otra
  placa de otro tamaño al lado. El agarre tiene que salir de la imagen, no de una pose grabada [I].
- La frase cambia un **criterio de presentación**, no un objeto: «cara de componentes», «cara de soldar
  inclinada», «terminado». La misma red, con la misma placa, hace tres gestos distintos según el texto. Es lo que
  pide el jurado (encargo-ideas.md).
- Dar la vuelta a la placa dentro de la pinza y presentarla a una persona que se mueve es más fácil de enseñar con
  demostraciones que de programar [I].
- **Honestidad:** las posturas de presentación se podrían programar si la placa estuviera siempre en una cuna fija.
  Lo que aporta el aprendizaje es **coger la placa de donde esté y elegir el gesto por la frase**. Ajustes finos
  como «gíralo un poco» no se aprenden bien con 120 episodios. Se dejan como **pasos programados de ±15° en la
  muñeca**, después de la política (patrón ganador: habilidad aprendida + orquestación programada) [R].

## 4. En qué se diferencia de MSN (para que no parezca una copia)

| | MSN (Robotekin, 1.º) | Tercera mano |
|---|---|---|
| Qué sostiene | Una linterna: una ayuda periférica | **La pieza de trabajo**: el robot está dentro del proceso |
| Qué se aprende | Solo el agarre (ACT); apuntar y esquivar es IBVS clásico | Agarre + volteo + presentación, elegidos por la frase (SmolVLA multitarea) |
| Papel del lenguaje | Voz para lanzar acciones | La frase cambia el criterio («qué cara», «terminado») |
| Final | La luz rodea la mano | **Un producto funciona**: la placa que soldó el juez se enciende en la bandeja |
| Interacción | El juez tapa la luz | El juez **monta y suelda de verdad** y el robot es su segunda mano |

[R] No llevar ni luz ni lupa en la demo. Decir en el pitch, en 1 frase: «MSN te alumbra; nosotros te sujetamos y
te giramos la pieza». Es reconocer el precedente y que el jurado lo vea como evolución, no como copia.

## 5. Demo propuesta

**Escena (mesa de 80×60 cm).**
- Esterilla de silicona.
- 3 placas «insignia Robotalde» de 50×70 mm, cada una montada en un **marco impreso con mango** de 25×25×60 mm
  (unos 40 g) para la pinza; dos de ellas de colores distintos.
- Soldador en su soporte, con un microinterruptor que lee el ESP32.
- **Bandeja de acabadas** con dos contactos de muelle y una pila CR2032: al dejar la placa, cierra el circuito del
  LED.
- Cámara fija en diagonal + cámara de muñeca.

**Qué hace el juez:**
1. Mete un LED de inserción (patas largas) por la cara de componentes.
2. Suelda las dos patas por la otra cara.
3. Corta las patas (opcional).

Es un gesto de 1-2 minutos, real y fácil para cualquiera.

**Órdenes del VLA** (voz → LLM → orden cerrada; ya lo tenemos hecho):
1. «Tráeme la placa azul» → coge la placa por el mango, esté donde esté, y la presenta plana con los componentes
   hacia arriba, delante del juez.
2. «Dale la vuelta» / «enséñame la cara de soldar» → gira la muñeca 180° y la inclina unos 30° hacia la persona, a
   la altura de trabajo.
3. «Terminado» / «apártala» → la deja en la bandeja de acabadas → **el LED se enciende** (momento final).
4. Programado, sin aprendizaje: «un poco más cerca / gírala un poco» = paso fijo en una articulación.

**Episodios.** 3 tareas × 40 = 120 episodios teleoperados. La posición inicial varía por toda la mesa, y un 10-15 %
de los episodios son de recuperación (placa caída o mal cogida). Se graban en 2-3 rondas cortas donde falle.
SmolVLA multitarea en la GPU de la nube. [R] Al llegar a la pose de presentación, **congelar**: parar la
inferencia y mantener el último objetivo de las articulaciones, para que la placa no tiemble mientras se suelda.

**Plan B con ACT.** Tres ACT, uno por orden, y el selector de voz elige cuál ejecutar. Si el volteo en el aire
falla, el robot deja la placa en una **cuna impresa de dos caras** (V abierta, ±1 cm) en la cara pedida. Sigue
siendo útil y el riesgo de fallo es casi nulo.

**Momento memorable.**
- Al decir «dale la vuelta», el robot gira la placa con las patas del LED hacia el juez.
- Al decir «terminado», la placa se enciende en la bandeja.
- Recuperación visible: el juez se lleva la placa a otro sitio de la mesa y el robot la encuentra y vuelve a
  cogerla.

**Riesgos y cómo evitarlos.**
- **Soldador (unos 320-350 °C) cerca del PLA** (se ablanda hacia los 60 °C [I]):
  - El mango deja la zona de soldadura a ≥ 6 cm de la pinza.
  - El soporte del soldador tiene un enclavamiento: **el robot solo se mueve si el soldador está en su soporte**.
    Un LED verde y rojo en el soporte lo muestra.
  - Soldador regulado a 320 °C. Si se quiere más margen, estaño de baja temperatura.
- **Persona:**
  - El robot está quieto mientras el juez suelda: nunca se mueve con el soldador fuera del soporte.
  - Velocidad limitada cerca de la persona.
  - Seta de parada que **congela** el brazo (no quita el par, para que no caiga).
  - Gafas para el juez y un ventilador extractor de humos.
- **Rigidez al soldar:** la punta empuja poco, pero el servo cede unos milímetros. Probarlo el primer día. Si
  vibra, apoyar el borde del marco en un tope impreso o pasar a la cuna del plan B.
- **Fallo de agarre:** el mango grueso y sin brillo cumple el «fiable» del encargo (≥ 20 mm, < 300 g, ±1 cm).

**Coste de preparación.**
- Impresión: 3 marcos, bandeja y cuna, unas 6-8 h de impresora.
- 3 PCB de insignia: perforadas o fresadas, preparadas de antemano.
- ESP32 con microinterruptor y LED de estado.
- 120 episodios, unas 4-5 h de grabación.

## 6. Variantes y elección

| Variante | A favor | En contra | Nota |
|---|---|---|---|
| **Electrónica de inserción (elegida)** | El volteo es una necesidad real y conocida; el juez suelda de verdad; final con LED | Mismo tema que MSN; hay calor | **4** |
| Maquetismo y pintura de miniaturas | Sin calor; seguro; muy lejos de MSN | Quien pinta ya tiene el mango en una mano: necesidad débil | 3 |
| Reparación de móviles | Mercado claro | Tornillos y piezas diminutas, precisión: lo que el SO-101 no hace | 1,5 |
| Joyería | El dolor está medido (Dextera) | Soplete y metal: el PLA no aguanta | 1,5 |
| Cableado de arneses (retrabajo industrial) | Industrial | Cables finos y deformables: prohibidos por el encargo | 2 |

Electrónica de inserción porque es donde la queja documentada («reposicionar», «inclinar») coincide con lo que el
SO-101 hace bien (coger un mango grueso y girar la muñeca). Además, el juez sale con un objeto que funciona. Si el
equipo quiere alejarse más de MSN o no quiere calor en la mesa, la alternativa es maquetismo, aceptando una
necesidad más débil.

## 7. Notas (1-5)

| Criterio | Nota | Por qué |
|---|---|---|
| Valor real | 3,5 | El dolor de reorientar está documentado, pero las herramientas pasivas baratas «van tirando» |
| VLA necesario | 3 | El agarre en sitio variable y el gesto por frase son aprendidos; las posturas se podrían programar |
| Fiabilidad | 4 | Mango grueso, giro de muñeca, bandeja abierta; plan B con cuna |
| Uso real tal cual | 4 | Es la herramienta en el banco: soldadura real, componente real |
| Momento | 3,5 | «Dale la vuelta» + LED que se enciende; menos espectacular que la luz que esquiva |

## Fuentes

- EEVblog, «A better helping hands tool»: https://www.eevblog.com/forum/reviews/a-better-helping-hands-tool/msg910961 [H]
- EEVblog, «PCB holder; what are you using?»: https://eevblog.com/forum/beginners/pcb-board-holder-what-are-you-using/msg105446 [H·b]
- IntoFPV, manos auxiliares: https://intofpv.com/printthread.php?tid=2611 [H·b]
- SparkFun Third Hand: https://www.sparkfun.com/sparkfun-third-hand-kit.html [H·b]
- Guía de soportes de PCB: https://microcontrollerslab.com/best-pcb-holders-helping-hands-soldering-buying-guide/ [H·b]
- Dextera (UPenn): https://fisher.wharton.upenn.edu/wp-content/uploads/2019/06/Dextera.pdf [H·b]
- Robotic Helping Hand (Kicktraq): https://www.kicktraq.com/projects/voltge/robotic-helping-hand/ [H·b]
- Hackster, «Robotic Helping Hand Stabilizes Soldering Projects»: https://www.hackster.io/news/robotic-helping-hand-stabilizes-soldering-projects-97076012d4b5 [H·b]
- Hackster, brazo de laboratorio con voz: https://www.hackster.io/news/this-robotic-arm-acts-as-a-helping-hand-in-the-lab-16a5285e2f57 [H·b]
- Makerarm: https://www.mfgrobots.com/Article/iiot/embedded/4421.html [H·b]
- BLS OOH: https://www.bls.gov/ooh/installation-maintenance-and-repair/electrical-and-electronics-installers-and-repairers.htm [H·b]
- Eurostat, división 95: https://ec.europa.eu/eurostat/statistics-explained/SEPDF/cache/10097.pdf [H·b]
- Repair Café (Wikipedia): https://en.wikipedia.com/wiki/Repair_caf%C3%A9 [H·b]
- Back Market, Repair Cafés: https://www.backmarket.com/en-us/c/technology/women-leading-the-repair-revolution [H·b]
- Análisis de Repair Monitor: https://chokotto.pages.dev/posts/2026-04-15-tidytuesday/ [H·b]
- NEISS y trabajos en caliente: https://icwgroup.safetynow.com/by-the-numbers-hot-work/?print=pdf [H·b]
- Safety+Health, «Hobbies have hazards»: https://www.safetyandhealthmagazine.com/?p=48619 [H·b]
- MSN: ficha en investigacion/proyectos/hackathons-2026-europa.md
