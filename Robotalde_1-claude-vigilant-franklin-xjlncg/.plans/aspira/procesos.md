# Aspira · procesos de taller y extracción de polvo (19-11-2026)

Especialista de procesos y extracción. Etiquetas: **[H]** leído en la fuente (URL), **[H·b]** visto solo en el
extracto del buscador o en una ficha de tienda, **[est.]** estimación propia (razonada, sin fuente).

## 0. La física que manda: la captura cae con el cuadrado de la distancia

- Una boquilla aspira de todas direcciones, no «dispara» aire como un soplador. Ecuación de la toma libre:
  `vc = q / (A + 10·x²)` (q caudal, A área de la boca, x distancia); con brida o pared, ×1,33 **[H]**
  ([Engineering Toolbox](https://www.engineeringtoolbox.com/exhaust-outlet-d_1008.html)).
- **Regla de los diámetros:** a un diámetro de la boca la velocidad es menos del 10 % de la de la boca **[H]**
  (misma fuente). El Manual Técnico de OSHA: a 1 diámetro, 300 fpm; a 2 diámetros cae otra vez un factor 10;
  **la fuente no debe estar a más de 1,5 diámetros** y la velocidad de captación mínima es 50 fpm (0,25 m/s) **[H]**
  ([OSHA OTM III-3](https://www.osha.gov/otm/section-3-health-hazards/chapter-3)).
- Velocidades de captación de la tabla ACGIH: 0,5–1 m/s para emisión a baja velocidad; 2,5–10 m/s para amolado y
  chorro abrasivo **[H·b]** ([tabla PSU según ACGIH 2001](https://www.me.psu.edu/cimbala/me405/Links/Chapter_06_Tables_and_figures.pdf)).
- Cálculo para Aspira **[est.]**: boca redonda de 35 mm y ~25 l/s reales en la boca (aspiradora tipo WD 3 de 45 l/s
  máx. menos pérdidas) → 1,9 m/s a 35 mm; 0,5 m/s a 70 mm; 0,25 m/s a 100 mm. **Conclusión: la boca debe estar a
  30–60 mm del punto donde nace el polvo.** A 10 cm ya no capta casi nada, salvo que el chorro vaya hacia ella.
- Consecuencia para el robot: con ±1 cm de precisión del SO-101 basta, porque la ventana útil es de varios cm; lo
  que no se puede es quedarse lejos «por seguridad». Hay que ponerse **a favor del chorro** (donde el polvo ya viaja).

## 1–3. Proceso por proceso

### P1 · Taladrar en horizontal (pieza en la mesa, broca vertical)
- **Polvo:** nace en el filo; las estrías suben viruta y polvo, que se amontonan en anillo alrededor del agujero y
  parte salta lateralmente; al pasante sale además un tapón por debajo **[est.]**. Pino/contrachapado dan viruta
  gruesa (poca fracción respirable) **[est.]**. Duración: 5–20 s por agujero de 6–10 mm en 18 mm **[est.]**.
  Punto **fijo** (la marca), lo conoce la persona antes de empezar: ideal para el VLA.
- **Boquilla:** a ras de la mesa, boca a 20–40 mm del eje de la broca, inclinada 30–45° hacia el agujero, del lado
  contrario a la mano que sujeta la pieza **[est. con §0]**. Forma: redonda pequeña (Ø 25–35 mm) con pico plano o
  media campana abierta por un lado para que la broca entre. Referencia comercial: la boquilla de taladrado de
  Festool se coloca sobre el punto, para agujeros de hasta 12 mm, manguera de 27 mm **[H·b]**
  ([Highland Woodworking](https://www.highlandwoodworking.com/products/festool-drilling-dust-nozzle.oembed)).
  Los accesorios Bosch GDE 16 Plus y Makita DX06 son para martillos SDS y hormigón, no para taladro en madera
  **[H·b]** ([Bosch](https://www.bosch-professional.com/ae/en/products/gde-16-plus-1600A0015Z),
  [Makita DX06](https://makitatools.com/products/details/DX06)); Kreg resuelve el caso en su plantilla con toma de
  1¼" (31 mm) **[H·b]** ([Kreg](https://www.kregtool.com/store/c22/kreg-jigreg-accessories/p57/dust-collection-attachment)).
- **Riesgos:** broca girando a <2 cm de la boquilla impresa; enganche si la broca muerde el borde de la boquilla
  (PLA arrancado) **[est.]**. Calor y chispas: nulos en madera **[est.]**. Distancia mínima propuesta: borde de la
  boquilla a ≥15 mm del filo, objetivo 30 mm del eje **[est.]**.

### P2 · Taladrar en pared o pieza vertical (broca horizontal)
- **Polvo:** sale por las estrías hacia la persona y **cae por gravedad** pegado a la pared **[est.]**. Punto fijo.
- **Boquilla:** **debajo** del agujero, 20–40 mm, boca mirando hacia arriba (recoge lo que cae) **[est.]**; es justo
  el apaño del pósit doblado o del vaso de `concepto-base.md`.
- **Robot:** exige pieza vertical fija (tablero en un soporte) y alcance a altura; el SO-101 trabaja mejor desde arriba
  a 120–285 mm del eje (`.plans/brief/especialista-hardware.md`). Variante útil como **segundo nivel**.

### P3 · Lijar con lijadora orbital o de palma
- **Polvo:** el más fino y abundante de los procesos de madera. Ojima (2016): lijadora Makita de 130 W, haya y
  ciprés, MMAD ~9–10 µm con grano 240; fracción respirable 0,4–5 % de la masa, sube con grano más fino **[H]**
  ([J Occup Health](https://pmc.ncbi.nlm.nih.gov/articles/PMC5373914/)). El polvo escapa por la **periferia del
  plato** (NIOSH: el polvo de las orbitales «a menudo mal controlado»; extracción extra en el borde → −90 %) **[H]**
  ([NIOSH](https://www.cdc.gov/niosh/engcontrols/ecd/detail46.html)). Con aspiradora conectada, las pruebas de
  revistas dan 75–90 % de captación **[H·b]** ([FWW](https://www.finewoodworking.com/2008/12/02/tool-test-6-in-random-orbit-sanders)).
  MDF genera más polvo que la madera maciza al lijar **[H·b]** ([WorkSafe Vic](https://www.worksafe.vic.gov.au/wood-dust-health-hazards-and-control)).
  Duración: minutos. Punto **móvil** (la lijadora barre la superficie).
- **Boquilla:** plana y ancha (p. ej. 15×100 mm) a 20–50 mm del borde del plato, a ras de la pieza, del lado hacia
  donde va el polvo (la dirección de giro y del avance) **[est.]**. Alternativa sin seguimiento: boquilla plana fija
  en el **borde de la pieza** hacia donde se lija («lijo el borde izquierdo»), que caza lo que barre el plato **[est.]**.
- **Riesgos:** vibración (Bosch GEX 125-1 A: 5,0 m/s²) y ruido (GEX 125-1 AE: 77 dB(A) de presión, 88 de potencia)
  **[H·b]** ([ficha Bosch](https://media.wickes.co.uk/is/content/wickes/GPID_1100096002_TECH_1),
  [manual](https://manualslib.mx/manual/440906/Bosch-Professional-Gex-125-1-A.html?page=14)); choque plato–boquilla
  si la persona se acerca; el plato no corta, riesgo bajo para la persona **[est.]**.
- **Ojo:** la orbital ya trae su propia toma; la utilidad real de Aspira está en la **palma sin toma** o con bolsita,
  y en lijar a mano **[est.]**.

### P4 · Lijar a mano con taco
- **Polvo:** poco caudal, fino, se queda en la superficie y cae por los bordes; el taco empuja el polvo en el sentido
  del trazo **[est.]**. Ruido nulo. Punto móvil pero lento y acotado.
- **Boquilla:** plana, al final del recorrido del trazo o en el canto de la pieza, 20–40 mm **[est.]**.
- **Riesgos:** ninguno de herramienta; la mano de la persona pasa cerca → robot lento y con par limitado **[est.]**.
- **Demo:** el más seguro y silencioso; poco espectacular pero muy entendible.

### P5 · Cortar con caladora
- **Polvo:** la hoja corta en la carrera hacia arriba; el soplador de virutas despeja la línea de corte; los manuales
  Bosch piden apagar el soplador al conectar aspiración y dan para la toma Ø 35 mm, ≥230 mbar y ≥36 l/s **[H·b]**
  ([manual Bosch](https://www.bosch-pt.com.au/manuals/professional/au/en/online-manual/200555456/en-GB/517584759989378827.html)).
  Polvo sale delante de la hoja (soplado) y por debajo de la pieza **[est.]**. Punto **móvil** a lo largo de la línea.
- **Boquilla:** detrás y debajo del corte es inaccesible; delante de la hoja a 30–50 mm siguiendo la línea **[est.]**.
- **Riesgos:** hoja alternativa expuesta por debajo de la pieza; vibración; el robot no debe estar bajo la pieza
  **[est.]**. Ruido alto. **No apto** para la demo en sala.

### P6 · Cortar o grabar con multiherramienta (Dremel)
- **Polvo:** el disco o la fresa lanzan el polvo **tangencialmente** a alta velocidad, en un abanico; Dremel solo
  ofrece soplador (490) y pantalla (550), que **desvían**, no captan **[H·b]**
  ([Dremel 490](https://www.dremel.com/us/en/p/490-26150490aa), [Dremel 550](https://www.dremel.com/au/en/p/rotary-shield-2615a550ab)).
  Partícula fina; con disco de corte en metal hay **chispas** **[est.]**. Punto móvil, lento (grabado).
- **Boquilla:** en la salida tangencial del abanico, 30–50 mm; velocidad de captación de tipo amolado (2,5–10 m/s),
  difícil con aspiradora pequeña salvo que el chorro apunte a la boca **[est. con §0]**.
- **Riesgos:** chispas sobre PLA y manguera; disco que estalla; **no apto** salvo grabado suave en madera.

### P7 · Fresar con fresadora de mano
- **Polvo:** de los más sucios: el perfilado de canto lanza viruta y polvo lateralmente fuera de la toma **[H·b]**
  ([TSO](https://tsoproducts.com/blog/router-dust-collection/)); con extractor se retira 80–90 % **[H·b]**
  ([Canadian Woodworking](https://canadianwoodworking.com/?p=103258)); Festool vende deflector y campana para
  canto **[H·b]** ([Festool AH-OF 1000](https://www.festool.com/accessory/routing/machine-accessories/dust-extraction/484453---ah-of-1000)).
- **Riesgos:** fresa a 20–30 000 rpm, retroceso; **no apto** para la demo ni para un brazo de 300 g cerca **[est.]**.

### P8 · Atornillar (control negativo)
- No hace polvo (solo algo si se avellana o pretaladra) **[est.]**. Sirve para que el VLA aprenda **a no ir**:
  «voy a atornillar aquí» → el robot se queda en reposo. Barato y muestra que entiende el proceso.

## 4. Encaje en la demo de hackathon (sala con ~140 personas)

**Material.** Pino macizo o contrachapado de pino/abedul. **Evitar MDF y maderas duras (haya, roble).**
- Directiva (UE) 2017/2398, anexo III de la 2004/37/CE: polvo de madera dura, **2 mg/m³** (fracción inhalable),
  3 mg/m³ hasta el 17-01-2023; si se mezcla con otras maderas, el límite se aplica a todo el polvo **[H·b]**
  ([texto](https://legislation.gov.uk/eudr/2017/2398/annex/paragraph/1?view=plain)).
- En España el polvo de madera dura es cancerígeno a efectos del RD 665/1997 **[H·b]**
  ([INSST Basequim](https://www.insst.es/stp/basequim/017-rectificado-superficial-de-piezas-de-madera-mediante-lijado-en-carpinterias-y-ebanisterias-exposicion-a-polvo-de-madera-2014));
  IARC clasifica el polvo de madera en Grupo 1 **[H]** ([INSST Infocarquim](https://www.insst.es/agentes-quimicos-infocarquim/procedimientos/trabajos-que-supongan-exposicion-a-polvo-de-maderas-duras)).
  No verifiqué la ficha LEP vigente del INSST (la URL de la ficha 2023 dio 404).
- MDF: el HSE pide extracción siempre que se mecanice o lije, y tablero sin formaldehído añadido si es posible
  **[H·b]** ([HSE MDF](https://hse.gov.uk/woodworking/faq-mdf.htm)).
- Además: el pino es blando y da viruta gruesa → polvo visible en la cartulina, poco respirable **[est.]**.

**Ruido y polvo en sala.** Taladro sin percusión en pino: unos segundos por agujero, tolerable **[est.]**. Orbital:
77 dB(A) a 1 m del operario, durante minutos **[H·b]** → solo ráfagas cortas. Lija a mano: silenciosa. Caladora,
Dremel con disco y fresadora: fuera. Llevar mascarilla FFP2 para el operador y el público a ≥2 m **[est.]**.

**Aspiradora.** Tres opciones:
| Modelo | Caudal máx. | Depresión | Ruido | Peso | Fuente |
|---|---|---|---|---|---|
| Kärcher WD 3 (red, 1000 W, 17 l, accesorios Ø 35 mm) | 45 l/s | 230 mbar | ¿? | ~6 kg [est.] | [H·b] [Kärcher](https://www.kaercher.com/es/home-garden/aspiradoras-para-suciedad-solida-y-liquida/wd-3-v-17-6-20-car-16281150.html) |
| Festool CTLC MINI (batería 2×18 V, clase L) | 51,7 l/s | 190 mbar | 67 dB(A) | 10 kg | [H·b] [digitec](https://www.digitec.ch/en/s1/product/festool-ctlc-mini-i-cordless-mobile-dust-extractor-36v-2x-18v-dust-class-l-2x-batteries-40-ah-extrac-42872317) |
| Bosch GAS 12V (de mano) | 15 l/s | 45 mbar | ¿? | ~1,2 kg | [H·b] [ficha](https://www.anserjo.com/pdf/3358410/06019E3000) |

Recomendación **[est.]**: aspiradora de taller tipo WD 3 o la que haya en el local, con filtro de cartucho y bolsa;
la de mano de 15 l/s solo vale a ≤30 mm. **Manguera de Ø 27–35 mm colgada del pescante con contrapeso** (decisión 2
del moderador) y los últimos 40–60 cm en tubo fino y flexible (Ø 20–25 mm, ~50–80 g) hasta la boquilla impresa
(20–40 g en PETG, no PLA) **[est.]**. Boquilla sujeta por la pinza con una aleta plana o, mejor, fijada a la
muñeca; cambio de boquilla con un soporte en la mesa si se eligen varias.

## 5. La necesidad, con fuentes
- **Cáncer y asma:** IARC Grupo 1 (fosas nasales, senos, nasofaringe); asma ocupacional, dermatitis, irritación,
  pérdida de capacidad pulmonar **[H]** ([CCOHS](https://ccohs.ca/oshanswers/chemicals/wood_dust.html)). En Europa
  hay valor límite vinculante de 2 mg/m³ para madera dura **[H·b]**; para cancerígenos no hay umbral seguro **[H·b]**
  ([CCOO](https://habitat.ccoo.es/19846edf2c9c2eaf5170a3c238a47eac000072.pdf)).
- **Qué funciona:** CCOHS recomienda extracción en la herramienta y aspirar con HEPA, no barrer ni soplar **[H]**; el
  lijado y la limpieza con aire comprimido dan las exposiciones más altas en planta (2430 muestras) **[H·b]**.
- **Bricolaje doméstico:** no encontré mediciones en talleres caseros; las normas (COSHH, OSHA) no obligan al
  aficionado **[H·b]** ([Highland](https://info.highlandwoodworking.com/dustcollection/workshopdustcontrol.html)).
  Es un hueco: la persona en casa no tiene LEV ni obligación, solo una aspiradora doméstica.
- **Por qué el apaño no basta:** (1) el tubo sujetado por otra persona o apoyado se queda a >1,5 diámetros, donde
  la captación ya es <10 % (§0) **[H]**; (2) la toma propia de la orbital deja escapar el polvo del borde **[H]**
  (NIOSH); (3) la Dremel y la caladora no tienen captación, solo soplan **[H·b]**; (4) taladrar con taladro normal
  no tiene accesorio de extracción para madera salvo la boquilla Festool o plantillas **[H·b]**.

## (a) Tabla resumen

| Proceso | Polvo | Dónde va la boquilla | Boquilla | Punto | Dificultad robot | ¿Demo? |
|---|---|---|---|---|---|---|
| P1 Taladrar horizontal | medio, viruta gruesa | a ras, 20–40 mm del eje, 30–45° | redonda pequeña / media campana | fijo | baja | **sí, nivel 1** |
| P2 Taladrar vertical | medio, cae | debajo, 20–40 mm, boca arriba | redonda / cuchara | fijo | media (altura) | sí, nivel 3 |
| P3 Lijar orbital/palma | alto, fino | borde del plato o canto de la pieza, 20–50 mm | plana ancha | móvil | alta (seguir) / media (canto) | **sí, nivel 2 (canto fijo)** |
| P4 Lijar a mano | bajo, fino | final del trazo, 20–40 mm | plana | móvil lento | media | sí, alternativa silenciosa |
| P5 Caladora | alto | delante de la hoja | cepillo/plana | móvil | alta | no (ruido, hoja) |
| P6 Dremel | medio, tangencial, chispas | salida del abanico | redonda | móvil | alta | no |
| P7 Fresadora | muy alto, lateral | campana en el canto | campana | móvil | muy alta | no (riesgo) |
| P8 Atornillar | nulo | ninguna (reposo) | — | — | nula | **sí, control** |

## (b) Procesos recomendados y orden
1. **Nivel mínimo: P1 taladrar en una marca en horizontal** (pino de 18 mm, broca de 6–8 mm, taladro sin percusión).
   Objetivo estático, polvo visible, segundos de ruido; puntuable 5 de 5.
2. **Segundo: P3 lijar el canto con la palma**, boquilla plana fija en el canto que se nombra («lijo el borde
   izquierdo»); cambia la boquilla y la postura con la frase, sin seguir la lijadora. P8 entra aquí como control
   negativo («voy a atornillar» → reposo).
3. **Tercero (si sobra tiempo): P2 taladrar en un tablero vertical** con boquilla debajo, o seguimiento de la
   lijadora (fuera de la nota, como en MSN).

## (c) Protocolo para medir en la demo (con y sin Aspira)
- **Montaje:** cartulina negra A3 bajo la pieza y otra A3 en el suelo/mesa a 30 cm a cada lado; pieza de pino con
  marcas idénticas; misma broca, mismo taladro, misma persona; 5 agujeros por condición **[est.]**.
- **Orden:** A = sin robot (aspiradora apagada o tubo a 15 cm, «el apaño»), B = con Aspira. Alternar A-B-A-B para no
  sesgar por cansancio o broca. Cartulinas nuevas en cada tanda.
- **Foto:** cámara cenital fija en trípode, misma luz, misma exposición; foto antes y después. Fuera de la sala,
  `% de píxeles claros` sobre la cartulina con un umbral fijo (script de 10 líneas con OpenCV) **[est.]**.
- **Pesada:** báscula de joyería 0,01 g. Masa esperada: agujero Ø 8 × 18 mm en pino (~0,5 g/cm³) ≈ 0,45 g; 5
  agujeros ≈ 2,3 g **[est.]**, medible. Captación = 1 − (polvo en cartulinas con B / con A). Pesar también la pieza
  antes y después para conocer el polvo total generado (balance de masas).
- **Partículas (opcional):** contador láser barato (PM2.5/PM10) a 50 cm, a la altura de la cara, 60 s antes, durante y
  después; mostrar el pico A frente a B. Con pino y taladro el pico será pequeño: decirlo, no exagerar **[est.]**.
- **Honestidad:** mismo número de agujeros, enseñar las dos cartulinas a la vez, publicar los números brutos de las
  tandas, y declarar que la referencia «A» es el apaño concreto (tubo fijo a 15 cm), no «nada».
