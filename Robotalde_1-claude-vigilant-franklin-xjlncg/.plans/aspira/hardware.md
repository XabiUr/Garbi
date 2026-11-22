# Aspira · hardware (para Andoni, jueves 19-11-2026; el SO-101 llega el viernes)

Leyenda: **[H]** leído en la fuente (URL) · **[H·b]** extracto del buscador o ficha de tienda · **[est.]** estimación
propia · **[medir]** pendiente de medir hoy · **[modelo]** MuJoCo, de `.plans/brief/especialista-hardware.md`.
Plano: [banco-aspira.svg](banco-aspira.svg). Entradas: `concepto-base.md`, `procesos.md`, `gestion-robot.md`.

## 0. La decisión de diseño: un mango fijo en la pinza y cabezales intercambiables

Problema: si cada boquilla lleva su manguera, hay que conectar y desconectar la aspiración con una pinza de 2 dedos y
±1 cm. Solución: **la pinza coge siempre el mismo «mango»** (el extremo del tubo ligero, con asa), y el cambio de
boquilla es un **cambio de cabezal** en el soporte con movimientos solo de traslación (bajar, deslizar, subir).
Para el VLA es lo mismo que «coger la boquilla adecuada»: va al módulo del color que pide la frase (naranja =
taladrar, azul = lijar), encaja y sale. Encaja con `gestion-robot.md` (aparcado con la boquilla en la pinza,
«Put the nozzle back», imán como fusible mecánico). **Plan B (rama C' de `gestion-robot.md`):** un solo cabezal fijo
en el mango, sin cambio; la frase solo cambia la postura. Se decide el viernes a las 19:30.

## 1. Piezas impresas (PETG si hay; si no, PLA · 0,2 mm, 3 perímetros, 15 % giroide)

**Mango (M).** Tubo Ø int. 32 / ext. 36 en codo de 45°: el tramo de abajo vertical (al cabezal) y el de arriba
inclinado **hacia fuera del robot** (el tubo no roza la muñeca ni tapa la cámara de muñeca [medir]).
- Abajo: **cono macho** Ø 40 → 30 en 14 mm (centrado) con 2 imanes de neodimio Ø 8 × 3 en el escalón, bajo 0,6 mm
  de plástico, polaridad marcada.
- Arriba: espiga para el tubo extensible de 40 mm (cotas 39,4 / 39,8 / 40,2 en anillos de prueba [medir]).
- **Asa para la pinza** en el lado del robot: aleta vertical de **30 mm de grueso × 40 de alto** (hueca, pared 2),
  con un canal de 19 mm en cada cara (dedo de 17 mm [modelo] + 2) entre dos nervios de 3 mm achaflanados a 45° por
  arriba (embudo de 25 → 19 mm) y un tope superior: el dedo cae en su sitio en altura y de lado. Pinza a ~29-46°
  para bajar (hueco 37-80 mm [modelo]) y cierra sobre 30 mm. Goma EVA de 2 mm en los dedos.
- Masa ≈ 28 g con imanes [est.].

**Cabezal común (interfaz).** De arriba abajo: embudo de entrada Ø 60 (capta ±15 mm), copa hembra Ø ext. 44 con cono
41 → 31 y **2 arandelas M6 de acero** frente a los imanes; **collar Ø 60 × 4**; cuello Ø ≤ 40; cuerpo de la
boquilla. Altura collar → boca ≈ 50 mm. Fuerza de sujeción objetivo 1,5-3 N (el cabezal pesa 0,3 N) [medir];
la aspiración también lo aprieta contra el mango. Si alguien lo golpea, se suelta (fusible).

| Cabezal | Boca y forma | Postura (de `procesos.md`) | Masa · color |
|---|---|---|---|
| **C1 taladrar** | media luna: boca 60 × 15 mm con arco cóncavo de R 25 hacia la broca, cortada a 40° (aspira hacia el agujero); 3 patas de 8 mm que apoyan en la tabla (altura fija); cuerpo ≤ 22 mm de alto cerca del arco | centro a 35 mm del eje de la broca, borde ≥ 15 mm del filo, a ras | ≈ 25 g · naranja |
| **C2 lijar** | ranura 100 × 15 mm (15 cm², ~2 veces el área del tubo), labio inferior a 5 mm de la mesa, cortada a 30° | fija en el canto nombrado, a ras, a 20-50 mm del plato | ≈ 30 g · azul |
| C3 cortar (no se imprime hoy) | campana Ø 70 con faldón de cepillo o flecos de EVA | delante de la hoja; caladora y Dremel fuera de la demo (`procesos.md`) | reserva |

Peso que carga la pinza: **mango 28 + cabezal 25-30 + resto de tubo no equilibrado ≤ 20 = ≤ 80 g** [est.].

**Soporte de boquillas (S).** Tres módulos iguales atornillados al DM (2 tirafondos 4 × 16), uno por cabezal:
- Pilar trasero (lado lejano del robot) y **dos horquillas abiertas hacia el robot**: inferior (apoya el collar,
  cara superior a z 62, ranura 44 para el cuello) y superior (labio, cara inferior a z 68, ranura 47 para la copa).
  Entrada en embudo 80 → 47 mm y chaflanes de 5 mm arriba y abajo: capta ±10 mm de lado y ±5 mm de alto.
- Debajo de las horquillas, hueco libre de 130 × 55 mm: el cabezal **cuelga con la boca al aire** (si la boca
  apoyase en algo, el vacío lo pegaría: 85-220 mbar × 9 cm² = 8-20 N).
- **Coger:** bajar el mango sobre la copa (encaja) → deslizar hacia el robot (el collar sale por la boca de la
  horquilla). **Dejar:** entrar deslizando → **inclinar la muñeca 15°** y subir: el labio retiene el collar y los
  imanes se despegan uno a uno (menos fuerza que tirar recto). Aparcado: dejar el cabezal y **abrir la pinza** sin
  subir; el mango queda encajado y el contrapeso lo sostiene.
- Pegatina ArUco o de color en la tapa de cada módulo para el vigilante de `gestion-robot.md`.

**Otras piezas:** adaptador manguera Kärcher Ø 35 → tubo de 40 (dos versiones, macho y hembra, porque no sé cuál
lleva la empuñadura [medir con calibre]); pie del poste (cuadradillo 20 × 20, 4 tirafondos) y escuadra del brazo;
2 poleas Ø 30 con rodamiento 608 si no se compran; 3 topes en L de 30 × 30 para la pieza; soporte de la cámara de
muñeca (`assets/so101/assets/wrist_camera_mount_so101_v1.stl`) y soporte de la cámara `top` (P3 del brief anterior).

## 2. Gestión de la manguera: pescante con contrapeso

- **Tramo fijo:** la manguera de la aspiradora (Ø 35, 1,8 m) sube por un poste de aluminio 20 × 20 × 1050 en
  (-330, -200) y sigue por un brazo de 350 mm hasta una polea a **z 1000 sobre (-80, 60)**, encima del centro de la
  zona de trabajo (distancia en planta a cualquier objetivo: 120-270 mm). Bridas cada 20 cm.
- **Tramo móvil:** de la polea al mango cuelgan **0,7-0,8 m de tubo extensible de desagüe de 40 mm** (fuelle de PP o
  PVC, muy ligero y flexible): tubo extensible 32 × 40 a 1,99 € **[H·b]**
  ([Leroy Merlin PT](https://www.leroymerlin.pt/produtos/tubo-extensivel-32x40-mm-branco-84410659.html)); el de
  Cofan alarga de 300 a 720 mm **[H·b]** ([ficha](https://www.cofan.es/images/content/FichasTecnicas/ftpFichaTecnica8689.pdf)).
  Masa 60-100 g/m [est., medir]. Su rigidez de fuelle hace de muelle: medirla.
- **Contrapeso:** cordel de 2 mm atado al codo del mango → polea de la punta → polea en lo alto del poste → botella
  de 0,5 l con agua o arena (se ajusta a gramos). Ajuste: que la báscula marque **0 a +20 g** con el mango a 20, 100 y
  200 mm de la mesa. La masa del contrapeso añade inercia: ~0,3 N a 1 m/s² [est.], aceptable.
- **Tirón lateral** del cordel: con la polea a ~850 mm sobre el mango y 270 mm de desvío, sen ≈ 0,31; con T ≈ 1,2 N,
  **≈ 0,4 N de lado** → 0,1 N·m en el giro [est.].
- **Par en el SO-101.** Servo STS3215: versión 12 V **30 kg·cm (2,94 N·m) de bloqueo y 10 kg·cm (0,98 N·m)
  nominal** **[H·b]** ([RobotShop](https://robotshop.com/products/feetech-12v-30kgcm-magnetic-encoding-servo-sts3215),
  [ficha Seeed vía Kamami](https://download.kamami.pl/p1203183-17bcda86-6ebc-4dc5-b704-7e06e8de6af9.pdf)); versión
  7,4 V (C001) **19,5 kg·cm (1,91 N·m) de bloqueo y 5 kg·cm (0,49 N·m) nominal** **[H·b]**
  ([OpenELAB](https://openelab.com/products/feetech-sts3215-c001-servo-7)). **Mirar el viernes la etiqueta de los
  servos del seguidor** [medir]. Cuentas [est.], brazo horizontal, carga a 0,33 m del hombro y a 0,12 m de la muñeca:

| Caso | Carga | Hombro (con 0,6 N·m de peso propio [modelo]) | Muñeca (flexión) |
|---|---|---|---|
| Con contrapeso | 80 g | 0,26 + 0,6 = **0,86 N·m** (45 % del bloqueo a 7,4 V; 29 % a 12 V) | 0,09 N·m |
| Sin contrapeso (tubo colgando) | 140 g | 0,45 + 0,6 = 1,05 N·m | 0,16 N·m |
| Manguera Kärcher directa al mango | 250-400 g + rigidez | > 1,4 N·m: **no** | > 0,3 N·m: no |

El hombro estirado supera el par nominal a 7,4 V: trabajar a r ≤ 270 mm y con la pinza alta solo lo justo.
- **Alternativa** si el tubo de desagüe no aparece: tubo flexible de recambio de aspiradora de mano o de la propia
  Kärcher colgado igual, con el contrapeso subido; o goma elástica (peor: la fuerza cambia con la altura).

## 3. Aspiradora y adaptadores

| Modelo | Caudal · vacío | Ruido | Manguera / accesorios | Peso | Nota |
|---|---|---|---|---|---|
| **Kärcher WD 1 Classic** (red, 850 W, 12 l) | 42 l/s · 220 mbar | 74 dB(A) | 1,8 m · Ø 35 | 3,6 kg | **recomendada** **[H]** ([Kärcher ES](https://www.kaercher.com/es/home-garden/aspiradoras-para-suciedad-solida-y-liquida/wd-1-classic-16284110.html)); precio no hallado, 60-90 € [est.] |
| Kärcher WD 2 Plus V-12/4/18 (red, 1000 W) | 43 l/s | — | Ø 35 | — | **[H·b]** 98,14 € la de 15 l ([Intermáquinas](https://intermaquinas.es/en/multifunctional-vacuum-cleaners/solid-liquid-vacuum-cleaner-karcher-wd-2-plus-15-liters-imq-258587)) |
| Kärcher WD 1 Compact Battery (18 V, 7 l) | 22 l/s · 85 mbar | 64 dB(A) | 1,2 m · Ø 35 | 3,1 kg | **[H]** ficha 1.198-300.0; solo 10-20 min por batería: **no** para grabar |
| Einhell TE-VC 18/10 Li (18 V, 10 l) | — | — | 2 m · Ø 36 | — | **[H·b]** ~66 € sin batería ([aio.lv](https://aio.lv/en/product--einhell-2347160--3059564.md)); batería: misma pega |

`procesos.md` pide ≥ 25 l/s reales en la boca: la de red. Bolsa de papel además del cartucho (el cartucho de
celulosa deja pasar el polvo fino) [est.]. **Dónde hoy:** MediaMarkt Barakaldo (Megapark, Av. de la Ribera 5)
**[H·b]** ([tienda](https://www.mediamarkt.es/es/store/barakaldo-971)) y Leroy Merlin (5 puntos de venta en Bizkaia
**[H·b]**, [Alimarket](https://www.alimarket.es/construccion/noticia/397525/leroy-merlin-estrena-en-bilbao-su-tercer-showroom-de-carpinteria)):
**mirar existencias en la web y reservar con recogida antes de salir**; o pedir la del local. Adaptadores: Kärcher
Ø 35 → tubo de 40 impreso (apartado 1); si la aspiradora es otra, medir y reimprimir (20 min).

## 4. Banco de trabajo (planta en el SVG; mm desde el eje de giro, +x derecha, +y hacia la persona)

| Elemento | Posición | Comprobación |
|---|---|---|
| Eje del SO-101 | (0, 0); **pan 0° apuntando a 142°** (delante-izquierda) | objetivos entre 58° y 226°: ±84° de pan |
| Tablero DM 15 mm | x -380…320, y -250…420 (700 × 670) | robot, soporte, poste, topes y cámara atornillados |
| Pieza pino 240 × 120 × 18 | x -120…120, y 160…280; 2-3 topes en L + antideslizante; la mano libre la sujeta | — |
| Zona de marcas | x -80…80, y 180…260 | boquilla a 35 mm: r 145-237 ✓ |
| Boquilla de lijar | cantos x = ±140, y 220 (centro) | r 261 ✓ |
| Cartulina negra | x -200…200, y 100…400, pegada con cinta de pintor | no entra en el soporte |
| Soporte S1-S3 | r 215 a 160°, 193°, 226°: (-202, 74), (-209, -48), (-149, -155) | dentro de 120-285 ✓ |
| Poste y polea | poste (-330, -200), r 386 (fuera del alcance); polea z 1000 en (-80, 60) | — |
| Aspiradora | taburete fuera de la mesa, detrás a la izquierda (manguera de 1,8 m justa: si no llega, alargo) | — |
| Cámara `top` | (250, -120), z 650, mirando a (-30, 150) | ve soporte, pieza, marca; ajustar con foto |
| Cámara de muñeca | soporte oficial en la pinza | que el mango no la tape [medir el viernes] |
| Persona | de pie frente al robot, y ≈ 680; herramientas apoyadas en (380…540, 380…490) | — |
| Parada | regleta con interruptor (12 V del robot) en (290, 490), a mano de la persona | — |
| Límite del robot | y ≤ 300 (programado en el vigilante) | — |

Alcance a la altura del mango (pinza a ~100 mm de la mesa, no a 10-30): **[est.]** no peor que desde arriba; recalcular
en MuJoCo si sobra tiempo o comprobar el viernes con el robot apagado moviéndolo a mano.

## 5. Piezas de trabajo, herramientas y brocas

- **Tablas:** pino macizo de 18 mm (`procesos.md`: nada de MDF ni maderas duras). Listón o tablero de pino de 120 ×
  18 mm cortado en tienda a **240 mm** (10 piezas por listón de 2,4 m). Cuenta [est.]: ~150 episodios de taladrar,
  la mitad con broca girando (~75 agujeros) + evaluación 40 + medida A/B 20 + demo 30 ≈ 165 agujeros; 10-12 por pieza
  → **16 piezas; comprar 2 listones (20 piezas)** y 4 piezas extra para lijar.
- **Plantilla de marcas:** hoja A4 impresa a 1:1 con la pieza y una rejilla de 15 puntos (paso 40 mm) dentro de la
  zona de marcas; marcar con punzón y pegatina naranja Ø 8 (la marca que ve la cámara). Barajar las posiciones.
- **Taladro:** Bosch EasyDrill 1200 (12 V, 0,94 kg con batería, 18/30 N·m) **[H·b]**; 89,99 € con 2 baterías y 34
  accesorios en Leroy Merlin **[H·b]** ([LM](https://www.leroymerlin.es/productos/atornillador-a-bateria-bosch-12v-2-baterias-y-xline-34-easydrill-1200-84499574.html)).
- **Lijadora:** Bosch EasySander 12 (12 V, 0,7 kg sin batería, misma batería que el taladro) **[H·b]**; 73,99 € sin
  batería en Bosch España **[H·b]** ([Bosch](https://www.bosch-diy.com/es/es/p/easysander-12-060397690b)). Sin su
  caja de polvo en las tandas de medida [est.]. Lijas de grano 120.
- **Brocas:** madera con punta de centrado de 6, 8 y 10 mm (la de 8 la principal) + **tope de profundidad de 8 mm**
  a 12 mm: agujero ciego en la tabla de 18, nunca atraviesa la cartulina ni el DM. Broca fuera del portabrocas
  ≥ 50 mm, para que el portabrocas quede por encima de la boquilla (cuerpo ≤ 22 mm de alto).

## 6. Seguridad física

1. **El robot no se mueve con la herramienta en marcha** (`gestion-robot.md`); llega, queda quieto y se retira.
2. **Distancias:** centro del cabezal C1 a 35 mm del eje de la broca; borde del arco a ≥ 15 mm del filo; zona
   prohibida de r 15 mm en la marca. Con ±10 mm del robot quedan ≥ 5 mm en el peor caso: por eso el **tope**:
   - **tope de profundidad** en la broca (no baja el portabrocas hasta la boquilla);
   - **patas del cabezal** que fijan la altura y el arco de R 25 de PETG como pared; si la broca roza, muerde
     plástico y el cabezal se suelta del mango (imanes): nada tira del brazo ni de la mano;
   - opcional **«diana-tope»**: disco impreso Ø 50 × 12 con agujero de 9 mm que la persona pone en la marca; el arco
     del cabezal apoya contra él y no puede acercarse a menos de 25 mm del eje [est.].
3. **Persona:** gafas EN 166 siempre que taladre o lije; mascarilla FFP2 para el operador y para el juez si se
   acerca a < 2 m; el juez mira desde el lado de la cámara, no delante de la broca.
4. **Polvo en la sala:** solo pino; taladro en ráfagas de segundos, lijadora ≤ 30 s por tanda; la aspiradora siempre
   encendida antes de la herramienta; cartulinas a una bolsa cerrada tras la foto; al final aspirar la mesa
   (no soplar ni barrer); bolsa de papel dentro de la aspiradora.
5. **Eléctrico:** cables de la aspiradora y del robot por detrás del poste, sin cruzar el paso de la persona.

## 7. Compra de hoy, impresión, horario y comprobaciones

| Compra | Cant. | ≈ € |
|---|---|---|
| Aspiradora de red Kärcher WD 1 Classic o similar (o la del local) + bolsas | 1 | 60-90 [est.] |
| Bosch EasyDrill 1200 con 2 baterías | 1 | 90 [H·b] |
| Bosch EasySander 12 sin batería + lijas 120 | 1 | 74 + 5 [H·b] / [est.] |
| Brocas madera 6/8/10 + tope de profundidad 8 mm | 1 + 2 | 12 [est.] |
| Listón/tablero de pino 120 × 18 × 2400 cortado a 240 | 2 | 20 [est.] |
| Tubo extensible de desagüe 40 mm (fuelle) | 2 | 4-10 [H·b]/[est.] |
| Cuadradillo de aluminio 20 × 20 × 1000 (poste y brazo) | 2 | 12 [est.] |
| Tablero DM 15 mm cortado a 700 × 670 | 1 | 10 [est.] |
| Cordel 2 mm 10 m + 2 poleas pequeñas (o rodamientos 608) + bridas | — | 8 [est.] |
| Imanes de neodimio Ø 8 × 3 (10) + arandelas M6 de acero (10) | — | 7 [est.] |
| Cartulina negra 50 × 65 | 10 | 8 [est.] |
| Gafas EN 166 (4) + FFP2 (20) | — | 22 [est.] |
| Goma EVA 2 mm, antideslizante, cinta de pintor, pegatinas Ø 8 naranjas | — | 10 [est.] |
| Báscula de cocina 1 g (si no hay) y de joyería 0,01 g (`procesos.md`) | 1 + 1 | 22 [est.] |
| Tirafondos 4 × 16, cianoacrilato, filamento PETG 1 kg si falta | — | 25 [est.] |
| **Total** | | **≈ 390-440 €** (sin aspiradora si la presta el local) |

**Impresión (tiempos clásica · rápida [est.]; orden = prioridad):** 1) anillos de prueba de la espiga y del cono
(20 · 10 min) → 2) mango M (2 h · 50 min) → 3) C1 taladrar (1,5 h · 40 min) → 4) adaptador Kärcher (1 h · 25 min)
→ 5) módulos S × 3 (4 h · 1,5 h) → 6) C2 lijar (2 h · 50 min) → 7) soporte cámara `top` (3 h · 1,2 h) → 8) soporte
de muñeca (45 · 20 min) → 9) pie del poste, escuadra, poleas (2,5 h · 1 h) → 10) topes en L y diana-tope (1 h ·
25 min) → noche: mango y C1 de repuesto. **Total ≈ 18 h clásica / 7,5 h rápida**: con impresora clásica, lo 7-10
de noche. **Sustitutos:** mango → tubo PVC de 40 + asa de contrachapado pegada; C2 → la boquilla de ranuras de la
Kärcher; módulos S → taco de madera con ranura de sierra; poste → palo de escoba con sargento al canto de la mesa;
poleas → arandela lisa o mosquetón; contrapeso → botella.

**Horario de Andoni (hoy):**

| Hora | Tarea |
|---|---|
| 08:45-09:30 | SolidWorks: anillos de prueba e interfaz cono/copa/collar; lanzar impresión 1. Reservar en web aspiradora, taladro, lijadora |
| 09:30-10:15 | Modelar el mango (asa con canal de 19, codo 45°); lanzar 2 |
| 10:15-12:45 | Compras: MediaMarkt Barakaldo y Leroy Merlin (pino y DM cortados, aluminio, tubo, cordel, imanes, EPI) |
| 12:45-13:30 | Medir con calibre la empuñadura Kärcher y el tubo de fuelle; ajustar la espiga; lanzar 3 (C1) |
| 13:30-14:15 | Comer. Modelar el adaptador; lanzar 4 |
| 14:15-16:00 | Modelar el módulo S; montar tablero, poste y brazo, polea y contrapeso; lanzar 5 |
| 16:00-17:30 | Pegar imanes y arandelas; probar encaje y suelta a mano (comprobación 2); modelar C2 |
| 17:30-19:00 | Lanzar 6; montar aspiradora y tubo; comprobación 1 (contrapeso) y 3 (captación) |
| 19:00-20:30 | Lanzar 7; plantilla de marcas, 3 piezas marcadas, cartulina, topes; foto de la planta 1:1 al equipo |
| 20:30-21:00 | Lanzar 8-10 (noche) y empaquetar: banco, aspiradora, herramientas, EPI, repuestos, calibre, báscula |

**Tres comprobaciones sin robot:**
1. **Contrapeso con báscula de cocina:** colgar mango + C1 del pescante con el tubo; apoyar el mango en la báscula a
   20, 100 y 200 mm de altura → **0 a +20 g** en las tres (ajustar agua). Tirón lateral: llevar el mango 270 mm de
   lado sujeto con un hilo que pasa a un vaso con monedas sobre la báscula → **≤ 40 g** (0,4 N).
2. **Encaje y suelta con báscula:** el cabezal colgado del mango aguanta un vaso con **≥ 120 g** de monedas sin
   caerse; en el módulo S, tirar del mango hacia arriba con un hilo a la báscula: suelta recta **≤ 300 g** e
   inclinado 15° **≤ 150 g**; con la aspiradora encendida, repetir (no debe subir más de ~100 g).
3. **Captación y holgura con regla:** aspiradora encendida, C1 en su postura a mano; taladrar 5 agujeros con y 5 sin
   sobre cartulina negra (foto cenital, `procesos.md` §c); con la regla, arco a ≥ 15 mm del filo y portabrocas por
   encima del cabezal al tope de profundidad. Repetir con C2 en el canto y 20 s de lijadora.
