# LeWelder v2 · Brief para CAD (SolidWorks)

Instrucciones para modelar en SolidWorks las 5 piezas de la v2. **Unidades: mm. Material: PLA, capa 0,2, 3 perímetros,
20 % relleno** (salvo que se diga). Todas las medidas salen de `lewelder/contrato.py` (sección v2); si algo cambia
allí, manda el contrato.

Convenio de cada pieza: **origen y planos indicados en su tabla**. "Arriba" = +Z con la pieza en su posición de uso.

Planos acotados, comprobaciones (choques, fuerza de los imanes, cámaras) y lista de comprobación con calibre:
[`contrato.md`](contrato.md) (generado con `python herramientas/generar_hardware.py --v2`). Las filas marcadas
**(corregido)** cambiaron tras esa comprobación; el porqué está en los avisos de `contrato.md`.

---

## Pieza 1 · BASE-V2 (chapa base, 1 ud + 1 repuesto)

**Croquis base en Planta, origen en el centro de la cara superior, X a lo largo, Y transversal, Z arriba.**

| Elemento | Medidas |
|---|---|
| Cuerpo | Prisma **200 (X) × 80 (Y) × 6 (Z)**, de Z = −6 a Z = 0. Chaflán 0,5 en las aristas de la cara inferior |
| Ranura de la T | Corte a lo largo de X, de **X −75 a +75**, centrada en **Y = +3**, **ancho 7,0**, **profundidad 2,0** (suelo en Z = −2). Chaflán de entrada **45° × 1,5** en sus dos aristas superiores |
| Tope de la esquina **(corregido)** | Nervio pegado al canto +Y: de **X −75 a +75**, **Y +40 a +43** (sobresale 3 mm del canto), **macizo de Z −6 (apoya en la mesa) a Z +3** (alto 3 sobre la cara). Chaflán 45° × 1 en su arista superior interior (lado −Y). Solo de Z 0 a +3 quedaría flotando fuera de la placa y los agujeros de los imanes de la esquina (Ø10,4 en Y = 37, hasta Y = 42,2) saldrían por el canto |
| Imanes línea T **(corregido)** | 3 agujeros ciegos **desde la cara inferior** en **X = −56, 0, +56; Y = +3**. Ø según la pieza de prueba (nominal **10,4**), **profundidad 3,2** → quedan 0,8 de piel bajo el suelo de la ranura |
| Imanes línea esquina **(corregido)** | 3 agujeros ciegos desde la cara inferior en **X = −56, 0, +56; Y = +37**, Ø nominal **10,4**, **profundidad 4,5** (piel 1,5; quedan 0,8 de pared hasta la cara exterior del tope) |
| Hueco del ArUco 30 | Rebaje **35,4 × 35,4 × 0,3** en la cara superior, centrado en **X = +82, Y = −20** (pegatina de 35 × 35: marcador de 25 + 5 de borde blanco) |
| Patas | 4 rebajes **Ø10 × 1** en la cara inferior en (±90, ±32) para tacos de goma antideslizante (la base no se atornilla: el alumno la gira) |
| Marcas | Grabado 0,4 de profundidad en la cara superior: flecha "+X" junto a X = −95 y texto "T" junto a la ranura, "ESQ" junto al tope |
| Imprimir | Cara inferior en la cama. Sin soportes |

Cordón de referencia (no se modela): T → línea X −60…+60 en Y = 0, Z = 0. Esquina → X −60…+60 en Y = +34, Z = 0.

---

## Pieza 2 · MOVIL-V2 (chapa móvil con aleta, 2 uds + 1 repuesto)

**Croquis en Alzado. Origen en el centro del canto inferior (el que apoya en la base), X a lo largo (140), Z = altura
cuando está de pie (40), Y = grosor (6). Cara −Y = "cara lisa" (lado del cordón). Cara +Y = "cara de la aleta".**

| Elemento | Medidas |
|---|---|
| Cuerpo | Prisma **140 (X) × 6 (Y) × 40 (Z)**, de X −70 a +70, Y −3 a +3, Z 0 a 40. Chaflán 0,5 en todas las aristas |
| Aleta | Saliente en la **cara +Y**: **40 (X) × 18 (sobresale en +Y) × 5 (Z)**, centrada en **X = −35, Z = 20**. Chaflán **45° × 1,5** en las 4 aristas de su extremo libre (entrada de la pinza). Redondeo R2 en la unión con la chapa |
| Imanes del canto **(corregido)** | 3 agujeros ciegos en el canto inferior (Z = 0) hacia +Z en **X = −56, 0, +56; Y = 0**: **Ø 4,3 × 4,3 de profundidad** para imanes **Ø4 × 4 mm N52** (pared de 0,85 a cada lado). En X = +50 el agujero quedaba bajo el hueco del ArUco (X 17,3 a 52,7) con solo 0,55 de pared |
| Hueco ArUco 41 (cara lisa, −Y) | Rebaje **35,4 × 35,4 × 0,3** centrado en **X = +35, Z = 20** |
| Hueco ArUco 40 (cara aleta, +Y) | Rebaje **35,4 × 35,4 × 0,3** centrado en **X = +35, Z = 20** |
| Marca | Grabado "▼" de 0,4 en la cara de la aleta junto al canto inferior (qué canto apoya) |
| Imprimir | Tumbada sobre la **cara lisa** (aleta hacia arriba), sin soportes. **100 % relleno en los 8 mm inferiores** (modificador) para que los imanes no se arranquen |

**Polaridad (corregido):** con todos iguales, la chapa girada 180° (aleta hacia el cordón) también se pegaría. Por
eso es asimétrica:

| X | −56 | 0 | +56 |
|---|---|---|---|
| Base (las dos líneas), cara que mira **arriba** | N | N | S |
| Chapa móvil, cara que mira **abajo** | S | S | N |

En su orientación se atraen los tres; girada 180° se repelen los dos de los extremos y la chapa no se queda.
Marca la cara N de cada imán con rotulador (con un imán de referencia) antes de pegar, y comprueba la chapa girada
antes de que seque el pegamento. Pega todos con una gota de cianoacrilato.

---

## Pieza 3 · ANTORCHA-ROBOT-V2 (1 ud)

El robot ya no la lleva fija: la coge de su soporte por el mango.

**Croquis en Alzado, origen en la punta (LED), eje de la antorcha = +Z hacia el mango.**

| Elemento | Medidas |
|---|---|
| Cuerpo **(corregido)** | Cilindro **Ø14**, de Z 0 a **93,7**, punta cónica de Z 0 a 12 (de Ø6 a Ø14). 93,7 = 100 − 6,3: las puntas de los dedos apoyan en el hombro del mango y `gripperframe` (6,3 por detrás del extremo del dedo) queda a los 100 mm de la punta que dice el contrato |
| LED | Agujero **Ø5,2 × 8** en la punta para LED verde de 5 mm; canal **Ø4** a lo largo del eje para los 2 hilos, que salen por el lateral del mango |
| Mango (para la pinza) **(corregido)** | Bloque de **Z 93,7 a 123,7**: **20 (X) × 12 (Y)**, caras planas paralelas en ±Y (las que aprieta la pinza). Chaflán 45° × 2 en el extremo superior |
| Chaveta **(corregido)** | Plano de 1 mm en el cilindro en el lado +X, de **Z 15 a 93,7** (de Z 60 a 95 quedaba por encima del tubo del soporte y no encajaba) |
| Imprimir | Tumbada, partida en dos mitades por el plano XZ, unidas con 2 pasadores Ø3 y pegamento |

---

## Pieza 4 · SOPORTE-ANTORCHA-V2 (1 ud)

**Origen en el centro de la base del soporte, Z arriba.** Va atornillado al tablero en la posición del contrato
(`SOPORTE_ANTORCHA`: x = 150, y = 170 en el marco de la mesa).

| Elemento | Medidas |
|---|---|
| Pie | Placa **70 × 70 × 6** con 4 agujeros Ø4,5 avellanados en (±27, ±27) |
| Columna | Tubo **exterior Ø24, interior Ø14,6**, de Z 6 a 66, con plano interior de 1 mm en +X (para la chaveta de la antorcha; arista de entrada del plano achaflanada) |
| Entrada | Avellanado cónico de **Ø22 a Ø14,6** en los 8 mm superiores (la antorcha cae sola a su sitio) |
| Asiento **(corregido)** | Macizo de Z 6 a 14 con agujero **Ø10**; de Z 14 a 20,9, **asiento cónico de Ø10 a Ø14,6** (mismo ángulo que la punta, 18,4°). El cono de la punta apoya en él (no el LED): **punta a Z 8** |
| Altura del mango **(corregido)** | Con la antorcha dentro, **gripperframe a Z 108 y centro del mango a Z ≈ 117** sobre el tablero. El contrato dice `z_mango` = 60, que no es posible con una antorcha de 124 de pie (la punta quedaría ~57 mm bajo el tablero): propuesta `z_mango` = 117 en el contrato |
| Imprimir | De pie, sin soportes |

---

## Pieza 5 · SOPORTES DE WEBCAM (2 uds) y tablero

Las webcams van en brazo articulado o trípode con rosca 1/4". Solo hay que imprimir, si hace falta, una pinza de
tubo Ø20 con rosca 1/4". Posición (marco de la mesa, origen = centro de la base del robot, X hacia delante, Y a la
izquierda, Z arriba; cámaras mirando a **(250, 0, 16)**):

| Cámara | Altura | Inclinación respecto a la vertical | Azimut (0 = desde +X, enfrente del robot) |
|---|---|---|---|
| A | 750 | 25° | −50° (lado derecho del robot) |
| B | 750 | 30° | +35° (lado izquierdo) |

**Tablero (corregido)** (DM o contrachapado 12-15 mm, **460 (X) × 610 (Y)**, de x −70 a 390 e y −370 a 240 en el
marco de la mesa): robot atornillado; centro de la BASE-V2 en **(280, 35)** con su X a lo largo de **+Y de la mesa**
(de derecha a izquierda); **zona libre** (dónde puede quedar el **centro** de la chapa tumbada) marcada con cinta
de x 110-160, **y 160 a 230** (lado izquierdo del robot), con tapete antideslizante; soporte de antorcha en
(180, −180) girado −45° (chaveta hacia fuera). **(corregido por la simulación, `hardware/v2/validacion_sim.md`)**: con
la base en (250, 0), la zona a la derecha (y −260 a −185) y el soporte en (150, 170) el SO-101 no llega a coger la
aleta en vertical (r > 250), ni a dejar la chapa casi de pie, ni a coger el mango a 116 de altura. Las medidas del
tablero de abajo se recalculan con `python herramientas/generar_hardware.py --v2`. Las webcams quedan fuera del
tablero (brazo o trípode).

---

## Pieza de prueba (imprimir PRIMERO)

**(corregido: en 60 × 30 no caben las dos filas de agujeros y la ranura con sus chaflanes; y hace falta probar la
polaridad y la aleta con el robot.)** Plano: `planos/prueba_v2.png`.

- **Bloque 70 × 40 × 8**: fila de agujeros Ø10,2 / 10,4 / 10,6 × 3,2 (imanes de la base) en Y = 8; fila Ø4,1 / 4,3 /
  4,5 × 4,3 (imanes de la chapa) en Y = 18,5; ranura de 7,0 × 2 con chaflán 45° × 1,5 centrada en Y = 30, a todo lo
  largo, con 2 imanes Ø10 × 3 desde abajo bajo la ranura (piel 0,8) en X = ±15 del centro: **N arriba en −15, S
  arriba en +15**.
- **Tramo de chapa 60 × 6 × 40** con la aleta completa (40 × 18 × 5 a Z = 20, centrada) y 2 imanes Ø4 × 4 en el canto
  en X = ±15: **S abajo en −15, N abajo en +15**.
- Comprueba: los imanes entran a presión con el pulgar; la chapa entra en la ranura y, soltada desde 5-10 mm de altura
  y ±5 mm de lado, se centra sola; girada 180° se repele; con el SO-101 real, la pinza abre, abraza la aleta, la
  levanta sin que gire, y el dedo de abajo no toca la ranura al dejarla de pie. Elige los diámetros y actualiza las
  piezas.

## Compra

- Imanes **Ø10 × 3 N52**: 12 (2 bases) + 5 de la prueba → pedir 20. Imanes **Ø4 × 4 N52**: 9 (3 chapas) + 5 de la
  prueba → pedir 20.
- LED verde 5 mm alta luminosidad + resistencia 220 Ω; tacos de goma Ø10; tapete antideslizante; 2.ª webcam igual que
  la primera (**FOV horizontal ≥ 75°**, recomendado 78°: la cámara A lo necesita para ver la base y toda la zona
  libre); cianoacrilato.
- Pegatinas ArUco: imprimir `hardware/v2/aruco/` a escala 100 % en papel adhesivo mate.
