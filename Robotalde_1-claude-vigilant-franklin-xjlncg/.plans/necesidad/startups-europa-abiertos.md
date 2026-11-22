# Physical AI real en Europa y en proyectos abiertos → demos con un SO-101

Fecha: 18-11-2026. Método research-ops: [H] hecho con fuente leída (URL) · [H·b] solo visto en el extracto del
buscador · [I] inferencia · [R] recomendación. Fuentes numeradas al final.

Pregunta: ¿qué tarea **vende, pilota o usa hoy** una startup o un proyecto de physical AI que quepa **a escala real**
en un SO-101 (pinza de 2 dedos, ~200-300 g, pocos mm de repetibilidad, ACT/SmolVLA con 50-150 demos), para que el
hackathon sea **la demo** de esa aplicación?

## 1. Tabla (19 casos)

Columna «SO-101»: ✅ cabe a escala real · ◐ cabe con objetos pequeños o una parte de la tarea · ❌ no cabe (maqueta).

| # | Quién | Tarea concreta | Cliente / piloto / usuario | Tracción | Por qué aprendizaje/VLA | SO-101 y demo de 3 min |
|---|---|---|---|---|---|---|
| A1 | **Sereact** (DE) | Coger, identificar y clasificar **devoluciones** de moda desordenadas | Zalando + CEVA en Greven y Świebodzin (oct-2026) [H][1]; Otto Group [H·b][2]; Arvato 3 sedes AutoStore [H·b][3] | Serie B ~110-116 M$ 2026, >200 sistemas (dato propio) [H·b][4] | «Si solo funciona con artículos que ha visto, no funciona en devoluciones» (CEO) [H][1] | ◐ Prendas ligeras pequeñas (calcetines, gorros, accesorios): el juez vacía una bolsa, el robot separa por tipo |
| A2 | **Sereact** (kitting) | Kitting de piezas variadas, metálicas y reflectantes | Daimler Truck [H·b][5] | ídem | Geometría y reflejos variables | ✅ Tornillería y piezas pequeñas en bandeja de kit |
| A3 | **Nomagic** (PL) | Picking y empaquetado de pedidos; turnos nocturnos sin personas; **VLA en producción** | Brack.Alltron (2.º e-commerce suizo), may-2026 [H][6]; Asos, Arvato, Fiege… [H·b][7] | 44 M$ (feb-2025), ARR +220 % (dato propio) [H·b][7] | Inventario cambiante, millones de referencias [H][6] | ◐ Picking de un pedido de 3 artículos pequeños a una caja |
| A4 | **Siemens** (GWE Erlangen) + autores | Coger una **bolsa transparente de accesorios** de un montón y meterla en el hueco de una caja de cartón | Fábrica real; π0.5 afinado con 2.535 episodios (~10 h) [H][8] | Caso publicado (arXiv 2605.27461) | Bolsa deformable y transparente, montón desordenado [H][8] | ✅ Bolsitas de tornillos en cajas pequeñas: tarea idéntica a escala real |
| A5 | **Humanoid** (UK) | De-stacking de cajas a cinta para operarios | Siemens Erlangen: 60 mov/h, >90 % éxito, >8 h [H][9]; Schaeffler contrato vinculante (may-2026) [H·b][10] | Bosch fabrica; 34.000 preórdenes (dato propio) [H·b][10] | Variación de pilas y cajas | ❌ Cajas de varios kg |
| A6 | **Agile Robots** (DE) | **Secuenciado de piezas**: coger de contenedores y ordenar según el montaje | Audi Ingolstadt, prueba de concepto oct-2026, sin métricas [H][11] | Serie F 500 M$ a 8.500 M$ (nov-2026) [H·b][12] | Formas, embalajes y posiciones variables [H][11] | ✅ Piezas pequeñas ordenadas en bandeja según la secuencia pedida |
| A7 | **RobCo** (DE) | Celdas modulares (machine tending, paletizado); humanoide Alfie para kitting | BMW, Rosenberger, T-Systems… [H·b][13] | Serie C 100 M$ (ene-2026), +40 M$ y >1.000 M$ de valoración (oct-2026) [H·b][13] | Hoy sobre todo programación sin código [I] | ◐ Cargar una pieza en un útil pequeño |
| A8 | **Micropsi Industries** (DE) | **Detección de fugas**: guiar una sonda olfateadora por tubos de cobre y uniones soldadas de frigoríficos | BSH Hausgeräte [H][14] (anuncio de 2021) | Serie B 30 M$ [H·b][15]; plantilla −32 % (Dealroom) [H·b][15] | Posición del tubo y luz variables; aprende de personas [H][14] | ✅ Seguir con una «sonda» las uniones de un tubo de cobre colocado al azar |
| A9 | **Wandelbots** (DE) | Plataforma NOVA (software de robots) | Schaeffler, red global [H·b][16] | Alianzas SCHUNK, EY, Tech Mahindra [H·b][16] | Capa de software, no tarea | ❌ No hay tarea propia |
| A10 | **Neura Robotics** (DE) | Cobot cognitivo MAiRA, humanoide 4NE-1 | Clientes declarados no verificados [H·b][17] | Serie C «hasta 1.400 M$» (jun-2026) [H·b][17] | — | ❌ Sin tarea con cliente verificada |
| A11 | **PAL Robotics** (ES) | TIAGo Pro en tareas de operario textil | CETRIKO (piloto CO-HAND, Horizon JARVIS) [H·b][18]; 3 pilotos AGIMUS [H·b][18] | Venta a investigación | Tareas manuales variables | ◐ Manipular tela ligera |
| A12 | **Theker** (ES) | Robots generalistas en el centro logístico de Mango (Lliçà d'Amunt) | Mango (jul-2026), Inditex inversor [H·b][19] | Serie A ~74 M€ (jun-2026) [H·b][19] | «Reciben un objetivo y deciden cómo» [H·b][19] | ◐ Doblar o clasificar prendas pequeñas (tarea exacta no publicada) |
| A13 | **Robovision + ISO Group** (BE/NL) | Reconocer, coger y **plantar esquejes** en macetas | Florensis (4.000 especies); hasta 2.800 esquejes/h; los propios plantadores reentrenan el modelo en 15 min [H][20] | Producción real | Cada esqueje es distinto (forma, orientación) [H][20] | ✅ Esquejes (pocos gramos) en bandeja de tacos: escala real |
| A14 | **Genesis AI** (FR) | Modelo GENE-26.5 multirobot, mano robótica | Negociaciones en FR, DE, IT, sin nombres [H·b][21] | 105 M$ [H·b][21] | Modelo generalista | ❌ Sin tarea concreta |
| A15 | **TramoIA** (Tecnalia, Euskadi) | Carga y descarga de camiones, estanterías | Mercado europeo previsto 2026 [H·b][22] | Spin-off de Tecnalia | Visión e IA | ❌ Cajas pesadas |
| B1 | **Dyna Robotics** (EE. UU.) | **Doblar servilletas** con dos brazos fijos | Din Tai Fung, de piloto (2025) a red de restaurantes; 1.590 servilletas/turno (dato propio) [H][23]; lavandería Monster Laundry [H·b][24] | DYNA-2.1 (sep-2026) [H·b][24] | Tela deformable | ◐ Dos SO-101 doblando una servilleta de cóctel: alto riesgo |
| B2 | **Weave** (EE. UU.) | Doblar ropa en casa (Isaac 0 fijo, Isaac 1 móvil) | Clientes del Área de la Bahía, 8.000 $ o 450 $/mes; >2.000 h de campo (dato propio) [H·b][25] | Isaac 1 se entrega en otoño-2026 [H·b][25] | Ropa deformable | ◐ Igual que B1 |
| B3 | **Verne / Remy AI** (EE. UU.) | Robots alquilados por horas para kitting y empaquetado | Verne: cajas de rollos de tela tras pocas horas de datos en el cliente [H·b][26] | RaaS, YC W2026 (Remy) [H·b][26] | Datos recogidos en el propio cliente | ✅ Kitting pequeño (como A2) |
| B4 | **Ecosistema SO-101/LeRobot, phosphobot, XLeRobot, Reachy Mini, Trossen** | Plataformas abiertas | phosphobot: >2.000 robots, usuarios aficionados y desarrolladores [H·b][27]; XLeRobot: kit de 579 $ (Wowrobo) y demos de tareas de casa [H·b][28]; Reachy Mini ~3.000 enviados a inicio de 2026 [H·b][29]; Trossen: clientes afinan π0, GR00T, SmolVLA [H·b][30] | Comunidad grande | — | No he encontrado **ningún uso comercial o productivo documentado de un SO-101** (ni pipeteo en laboratorio) [H·b][31]; los proyectos de laboratorio de bajo coste (tapado de viales, pipeta para pinzas de 2 dedos) existen pero no usan LeRobot [H·b][32] |

## 2. Patrones

1. **Lo que se vende con aprendizaje en Europa es manipulación de objetos variables en logística y fábrica**:
   devoluciones, picking, kitting, secuenciado, empaquetado (Sereact, Nomagic, Agile/Audi, Siemens) [H][1][6][8][11].
   El argumento de venta siempre es el mismo: «objetos nunca vistos, sin programar referencia a referencia» [H][1].
2. **Los humanoides tienen dinero pero no tareas a nuestra escala**: cajas de kilos (Humanoid, TramoIA) o ninguna
   tarea con cliente verificado (Neura, Genesis) [H·b][10][17][21]. No sirven de referencia.
3. **Los casos a escala del SO-101 existen y son reales**: bolsitas en cajas (Siemens), esquejes en bandejas
   (Florensis), piezas pequeñas en bandeja de kit (Daimler, Audi), sonda por uniones de tubo (BSH) [H][8][11][14][20].
4. **El caso Siemens es la prueba más cercana a nuestro método**: VLA preentrenado + afinado con demos teleoperadas
   en la propia fábrica, en bucles de grabar, curar, afinar, evaluar y grabar recuperaciones [H][8]. Es nuestro flujo
   con otra escala de datos (2.535 frente a 50-150 episodios) [I].
5. **El usuario reentrena al robot** (Florensis en 15 min, Verne en pocas horas en el cliente) [H][20][H·b][26]:
   la historia «el operario enseña al robot su tarea con 50 demos» es la que ya se vende [I].
6. **El ecosistema abierto no tiene todavía clientes**: SO-101, phosphobot y XLeRobot se usan para aprender y
   prototipar [H·b][27][28][31]. Una demo que copie una tarea vendida por una startup llena ese hueco [I].
7. **Tela y deformables (servilletas, ropa) son el caso estrella en EE. UU.**, pero exigen dos brazos y mucha
   destreza [H][23]: riesgo alto para nosotros [I].

## 3. Las 5 aplicaciones que mejor se demuestran con un SO-101

Todas cumplen: tarea vendida o pilotada hoy, a escala real del brazo, persona y robot trabajando juntos, órdenes
de lenguaje que cambian lo que hace una sola red.

### 3.1 Kitting y secuenciado asistido por voz («el robot te prepara las piezas»)
- **Referencia:** Agile Robots en Audi Ingolstadt (secuenciado) [H][11]; Sereact en Daimler Truck (kitting) [H·b][5].
- **Usuario real:** operario de montaje que pierde tiempo buscando piezas en cubetas.
- **Escena:** banco con 4 cubetas (tornillos, tuercas, arandelas, separadores o piezas de un kit real) y una bandeja
  de kit con huecos numerados; un operario monta algo mientras el robot prepara el siguiente kit.
- **Qué hace el juez:** pide un kit en voz alta («kit para la bisagra»), revuelve las cubetas, cambia su orden.
- **Órdenes del VLA:** «pon dos tornillos M4 en el hueco 1», «la arandela en el 2». **Final visible:** bandeja
  completa en el orden pedido; el operario la usa sin mirar.
- **Por qué VLA:** piezas sueltas en posición aleatoria, cubetas recolocables; una red, muchas órdenes [I].
- **Riesgo:** bajo-medio. Coger y dejar es lo que mejor hace el SO-101 [I]; piezas muy pequeñas (M3) fallan con la
  pinza de 2 dedos → usar piezas ≥ 1 cm [R].

### 3.2 Plantar esquejes en bandeja (vivero)
- **Referencia:** Robovision + ISO Group, cliente Florensis; los plantadores reentrenan el modelo [H][20].
- **Usuario real:** vivero o aficionado a la jardinería que multiplica plantas (geranio, poto, suculentas).
- **Escena:** montón de esquejes o tallos sobre la mesa, bandeja de tacos de turba o espuma floral.
- **Qué hace el juez:** echa esquejes de dos especies al montón y elige dónde plantarlos.
- **Órdenes del VLA:** «planta las suculentas en la fila de arriba», «el poto en el hueco libre». **Final visible:**
  bandeja plantada y ordenada por especie.
- **Por qué VLA:** cada esqueje tiene forma y orientación distintas; hay que cogerlo por el tallo, no por la hoja [H][20].
- **Riesgo:** medio. Insertar en el taco requiere orientación vertical: espuma blanda y agujero previo lo reducen [R].

### 3.3 Meter la bolsa de accesorios en la caja (fin de línea)
- **Referencia:** Siemens Erlangen, π0.5 afinado en fábrica [H][8].
- **Usuario real:** puesto de empaquetado: el operario arma la caja y el robot mete la bolsita de tornillería.
- **Escena:** montón de bolsitas zip transparentes (tornillos, tacos, llaves Allen) y cajas pequeñas abiertas.
- **Qué hace el juez:** revuelve el montón, coloca una caja donde quiera, pide un tipo de bolsa.
- **Órdenes del VLA:** «mete la bolsa de tacos en la caja». **Final visible:** la bolsa dentro y por debajo del borde.
- **Por qué VLA:** bolsa deformable, transparente y en montón [H][8].
- **Riesgo:** medio. Transparencias y aplastar la bolsa bajo el borde son los modos de fallo [I]; bolsas con
  etiqueta de color ayudan [R].

### 3.4 Clasificar devoluciones (o artículos revueltos)
- **Referencia:** Sereact con Zalando y CEVA [H][1]; Nomagic en Brack.Alltron [H][6].
- **Usuario real:** tienda online pequeña o taller que recibe devoluciones mezcladas.
- **Escena:** bolsa de devoluciones con artículos ligeros (calcetines, gorros, carcasas de móvil, cables) y 3 cajas.
- **Qué hace el juez:** vacía la bolsa y dicta el destino («lo textil a la caja azul»).
- **Final visible:** cajas ordenadas por categoría. **Por qué VLA:** objetos nunca vistos y categorías por lenguaje.
- **Riesgo:** bajo en coger; medio en generalizar a objetos nuevos con 50-150 demos [I]. Menos «valor en casa».

### 3.5 Inspección de uniones con sonda (fugas)
- **Referencia:** Micropsi MIRAI en BSH: el robot guía la sonda por tubos de cobre y uniones soldadas [H][14].
- **Usuario real:** frigorista o línea de climatización; enlaza con la soldadura del proyecto LeWelder [I].
- **Escena:** tramo de tubo de cobre con 3-4 uniones soldadas, colocado al azar; sonda de gas o micrófono en la pinza.
- **Qué hace el juez:** mueve el tubo y pide «revisa la unión del codo». **Final visible:** la sonda recorre la unión
  y la pantalla marca fuga u OK (fuga real con un poco de gas de mechero o simulada).
- **Por qué VLA:** posición del tubo variable, recorrido distinto según la unión pedida [H][14][I].
- **Riesgo:** medio. Recorrer a 1-2 cm de la unión sin chocar está dentro de la precisión del SO-101 [I]; el sensor
  es un componente más que puede fallar.

## 4. Top 2 [R]

1. **Kitting asistido por voz (3.1).** Es la tarea más vendida de la tabla (Sereact, Audi/Agile, Verne), cabe entera
   en el SO-101, es coger y dejar (bajo riesgo) y la colaboración es natural: tú montas, el robot te prepara las
   piezas. Encaja con «tercera mano de taller». Debilidad: visualmente sencillo; el lenguaje debe cambiar de verdad
   lo que hace (kits distintos por voz).
2. **Plantar esquejes (3.2).** Escala real exacta (un esqueje pesa gramos), cliente industrial verificado
   (Florensis), sirve a aficionados y viveros, y la historia «el plantador enseña al robot» es la que Robovision ya
   vende. Debilidad: inserción en el taco; probarlo antes del evento.

Alternativa si se quiere mantener la línea soldadura: 3.5 (inspección de uniones), con más riesgo de sensor.

## 5. Fuentes

1. Sereact, Zalando y CEVA: https://www.robotics247.com/article/ceva-logistics-deploys-sereacts-ai-powered-dual-arm-robotic-systems-for-zalando-returns-handling-at-sites-in-germany-and-poland/applications
2. Sereact y Otto: https://www.robotics247.com/article/sereact-otto-group-bring-nvidia-powered-physical-ai-to-returns-processing
3. Sereact y Arvato: https://www.robotics247.com/article/sereact-scales-ai-powered-robotics-deployment-with-arvato-across-three-sites-in-europe-and-u.s
4. Serie B de Sereact: https://tech.eu/2026/07/20/zalando-joins-sereacts-116m-series-b-to-accelerate-ai-powered-warehouse-automation/
5. Sereact Cortex y Daimler Truck: https://tech.eu/2025/09/29/meet-cortex-sereact-s-foundation-model-that-lets-robots-think-on-their-feet/
6. Nomagic y Brack.Alltron (VLA): https://nomagic.ai/news/nomagic-and-brack-alltron-expand-partnership-to-include-vision-language-action-systems-in-production
7. Nomagic 44 M$: https://techcrunch.com/2025/02/26/nomagic-picks-up-44m-for-its-ai-powered-robotic-arms
8. Siemens, caso VLA en fábrica: https://arxiv.org/abs/2605.27461
9. Humanoid en Siemens: https://www.therobotreport.com/humanoid-siemens-proof-of-concept-may-lead-more-industrial-deployments/
10. Humanoid y Schaeffler: https://thehumanoid.ai/humanoid-secures-landmark-deal-with-schaeffler-to-deploy-thousands-of-humanoid-robots/ · https://humanoid.guide/?p=17845
11. Audi y Agile Robots: https://interestingengineering.com/ai-robotics/audi-tests-humanoids-in-car-factory
12. Agile Robots Serie F: https://www.automate.org/robotics/news/physical-ai-leader-agile-robots-raises-500-million-series-f-at-8-5-billion-valuation-to-accelerate-global-growth
13. RobCo: https://www.businesswire.com/news/home/20260129479076/en/RobCo-Raises-100-Million-to-Scale-Its-Autonomous-Industrial-Robotics-Platform/ · https://www.channelinsider.com/channel-business/news-robco-1-billion-valuation-alfie-ai-robot-germany-emea/
14. Micropsi y BSH: https://www.verdict.co.uk/micropsi-industries-rolls-out-ai-powered-leakage-detection-robotic-system/
15. Micropsi Serie B y Dealroom: https://www.micropsi-industries.com/blog/micropsi-industries-secures-30m-in-series-b · https://dealroom.co/companies/micropsi-industries/
16. Wandelbots y Schaeffler: https://www.industrial-production.de/industrial-robots/physical-ai-in-manufacturing--schaeffler-and-wandelbots-partner-up.htm
17. Neura, balance 2026: https://theresarobotforthat.com/blog/neura-robotics/
18. PAL Robotics: https://ifr.org/case-studies/collaborative-robotics-in-textile-manufacturing · https://pal-robotics.com/news/pal-france-laas-cnrs-vivatech-2026/
19. Theker y Mango: https://ecosistemastartup.com/?p=94379 · https://sifted.eu/articles/theker-industrial-robotics-85m-series-a
20. Robovision, ISO y Florensis: https://robovision.ai/case-study/iso-group-case-study/
21. Genesis AI: https://www.dawn.com/news/1998261
22. TramoIA (Tecnalia): https://cms.tecnalia.com/uploads/2025/06/NPTECNALIA_TramoIA-Junio-2025.pdf
23. Dyna y Din Tai Fung: https://runtimewire.com/article/dyna-robotics-din-tai-fung-napkin-folding-rollout
24. Dyna, lavandería y DYNA-2.1: https://sacra.com/research/dyna-robotics · https://www.aiwiki.ai/wiki/dyna_robotics
25. Weave: https://newatlas.com/robotics/weave-robot-isaac1-laundry-bed/ · https://www.ktvu.com/news/san-francisco-tech-company-debuts-laundry-folding-robot
26. Verne y Remy: https://runtimewire.com/article/startup-spotlight-verne-robotics-rents-robot-labor-by-the-hour · https://www.startuphub.ai/ai-news/claudes-corner/2026/claudes-corner-remy-ai-yc-w2026
27. phosphobot: https://www.bestaitools.com/tool/phospho/ · https://www.ycombinator.com/companies/phospho
28. XLeRobot: https://xlerobot.readthedocs.io/en/latest/
29. Reachy Mini: https://www.seeedstudio.com/blog/2026/01/06/reachy-mini-an-open-journey-built-together-with-hugging-face-pollen-robotics-seeed-studio
30. Trossen Stationary AI: https://www.trossenrobotics.com/stationary-ai
31. Usos del SO-101 (sin despliegues con nombre): https://www.roboticscenter.ai/guides/robot-arms/so-101-applications
32. Laboratorios de bajo coste: https://arxiv.org/html/2603.20465v1 · https://pubs.rsc.org/en/content/articlehtml/2026/dd/d5dd00525f
