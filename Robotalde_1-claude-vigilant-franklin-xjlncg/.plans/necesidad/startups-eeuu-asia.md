# Startups de physical AI de EE. UU. y Asia con producto o piloto real (nov. 2026)

Frente: qué tareas venden o pilotan hoy las startups de robot learning / VLA de EE. UU. y Asia, y cuáles se pueden
demostrar **tal cual, a escala real** con un SO-101 (pinza de 2 dedos, 200-300 g, pocos mm de repetibilidad).

Leyenda: [H] hecho con fuente leída (URL abierta) · [H·b] solo visto en el extracto del buscador · [I] inferencia ·
[R] recomendación. Las cifras de tracción son casi siempre **declaradas por la propia empresa**; varias fuentes
secundarias se contradicen (se indica). Números entre corchetes = fuentes al final.

## 1. Tabla (25 empresas)

| # | Empresa (país) | Tarea concreta del robot | Cliente / piloto real | Tracción | Por qué aprendizaje / VLA | ¿Cabe en SO-101? Demo de 3 min |
|---|---|---|---|---|---|---|
| 1 | **Physical Intelligence** (EE. UU.) | Modelo π0.6 / π*0.6 (no vende robot): doblar ropa, empaquetar pedidos, montar y etiquetar cajas | Weave (doblado en negocios y lavandería) y Ultra (empaquetado e-commerce); 59 cajas de bombones montadas en una fábrica real [1][2] | Ultra: turno completo de empaquetado con 96,4 % de autonomía [2] [H·b] | Cola larga de objetos y situaciones; un solo modelo para muchos robots [I] | Sí, vía sus clientes (ver Ultra y Weave) |
| 2 | **Ultra** (EE. UU.) | Robot bimanual fijo OP1: empaquetar, clasificar y hacer kits de pedidos e-commerce | Highline Commerce (pick, pack, scan); >500.000 pedidos en almacenes de EE. UU. [3] | 62 M$ y alianza ampliada con PI [3] [H·b] | Miles de SKU distintos cada día, bolsas, cajas: imposible programar a mano [I] | **Sí**: pedido de 3-4 artículos pequeños de cubetas → caja/bolsa. Muy buena |
| 3 | **Tutor Intelligence** (EE. UU.) | Kitting, carga de cinta, paletizado, meter SKU en expositores y bandejas | Marcas de consumo y 3PL (sin nombres); 1/3 de nuevos despliegues son clientes que repiten [4] | Serie A 34 M$ (dic. 2025) y Serie B 75 M$ (a16z); cobro por hora (~14 $/h) [4] [H·b] | Mix alto de productos, cambios de formato frecuentes [I] | **Sí**: llenar una bandeja/expositor con piezas mezcladas según orden |
| 4 | **Dyna Robotics** (EE. UU.) | Brazos fijos que doblan servilletas (y otras tareas de servicio) | Piloto 2025 en restaurantes; titular liga a Din Tai Fung; 1.590 servilletas/turno (declarado) [5] | Seed 23,5 M$ + Serie A 120 M$ (2025); suscripción mensual por robot [6] [H·b] | Tela deformable; recuperación de errores [I] | Parcial: doblar tela con 1 brazo de 2 dedos es frágil [I]. Riesgo alto |
| 5 | **Weave Robotics** (EE. UU.) | Isaac 0: doblar ropa (fijo); Isaac 1: doblar, recoger y hacer camas | Hogares y negocios de California; >2.000 h de doblado, >450 kg/semana (post de la empresa) [7] | Isaac 1 a 7.999 $ o 449 $/mes; entregas desde otoño 2026; con teleoperación remota de apoyo [8] [H·b] | Ropa siempre distinta; usa π0.6 [1] | Parcial: prenda pequeña (calcetín, paño) sí; camiseta no [I] |
| 6 | **Generalist AI** (EE. UU.) | Modelos GEN-0/GEN-1 de manipulación; demo de montaje con 2 cobots UR (Teradyne) | Clientes no nombrados; una ficha no encuentra ningún despliegue verificado [9] | 400 M$ a 2.000 M$ de valoración (jun. 2026) + ext. a 3.000 M$ [9] [H·b] | Modelo general preentrenado con muchas horas de interacción [I] | Sí (tareas de montaje pequeñas), pero sin cliente que citar |
| 7 | **Skild AI** (EE. UU.) | "Skild Brain", cerebro para cualquier cuerpo de robot | >60 clientes de pago; Foxconn citado [10] | >100 M$ ARR (sep. 2026); Serie C 1.400 M$ (SoftBank) [10] [H·b] | Generalización entre cuerpos y tareas [I] | No da una tarea concreta demostrable |
| 8 | **Figure** (EE. UU.) | Humanoide F.02 cargando piezas de chapa en un útil de soldadura (5 mm en ~2 s) | BMW Spartanburg: 1.250 h, >90.000 piezas, >30.000 X3 (anunciado 19-11-2025) [11] | Despliegue de ~11 meses [11] [H] | Coger piezas de racks/cubetas variables y colocarlas con precisión [I] | **Sí, a escala**: piezas pequeñas al útil/plantilla de un banco de soldadura |
| 9 | **1X** (EE. UU./Noruega) | Humanoide NEO doméstico; tareas desconocidas guiadas por un "1X Expert" remoto | Preventa desde oct. 2025; envíos en EE. UU. en 2026 (fuentes contradictorias) [12] | 20.000 $ o 499 $/mes [12] [H·b] | Hogar no estructurado [I] | No (doméstico, cuerpo completo) |
| 10 | **Sunday Robotics** (EE. UU.) | Memo: cargar lavavajillas, recoger, café; datos con guantes de captura | Beta con 50 hogares a finales de 2026 [13] | Financiación 35-165 M$ (fuentes discrepan) [13] [H·b] | Aprende de rutinas reales de casa [I] | Parcial; doméstico y descartado por el usuario |
| 11 | **Chef Robotics** (EE. UU.) | Brazos que porcionan ingredientes en bandejas de comida preparada | Amy's Kitchen, Sunbasket, Chef Bombay, Cafe Spice; >44 M raciones [14] | Serie A 43,1 M$ (mar. 2025), RaaS [14] [H·b] | Ingredientes deformables y variables [I] | Sí técnicamente; descartado (cocina) |
| 12 | **Dexterity** (EE. UU.) | Mech: carga y descarga de camiones y paquetes pesados (hasta 60 kg) | FedEx, UPS, GXO [15] | 95 M$ a 1.650 M$ de valoración [15] [H·b] | Pilas de cajas siempre distintas [I] | No (fuerza y tamaño) |
| 13 | **Covariant** (EE. UU.) | RFM-1 para picking en almacén | "Docenas de clientes"; Amazon licencia el modelo y contrata a los fundadores (2024) [16] | Licencia ~400 M$ (no oficial) [16] [H·b] | Picking de cualquier artículo [I] | Sí (picking), pero empresa casi vaciada |
| 14 | **Standard Bots** (EE. UU.) | Brazo RO1: carga de máquinas, pick & place, empaquetado, lijado; aprende por demostración | Fabricantes (sin nombres) [17] | Serie B 63 M$ (2024) [17] [H·b] | "Enseñar mostrando" en vez de programar [I] | Sí: carga de máquina pequeña (impresora 3D, plantilla) |
| 15 | **Formic + Jacobi** (EE. UU.) | RaaS de paletizado y celdas de fábrica; software de movimiento de Jacobi | >100 plantas en 30 estados, 97 % renuevan (Formic) [18] | Formic 50 M$; Jacobi seed 5 M$ y acuerdo con ABB (abr. 2026) [18] [H·b] | Poco aprendizaje: sobre todo planificación clásica [I] | No (palés) |
| 16 | **Mbodi AI** (EE. UU.) | IA para enseñar tareas a robots industriales en alta variedad y bajo volumen (empaquetado) | Acuerdo de comercialización con ABB; ningún cliente nombrado [19] | Ganador ABB AI Startup Challenge 2024 [19] [H·b] | Cambios de producto frecuentes [I] | Sí (empaquetado pequeño), sin cliente citable |
| 17 | **Medra** (EE. UU.) | Brazos genéricos con modelo "visión-lenguaje-laboratorio-acción" que operan instrumentos (centrífugas, incubadoras, tubos, placas) por órdenes en lenguaje natural | 5 instalaciones de pago; Genentech, Addition Therapeutics, Cultivarium [20][21] | Serie A 52 M$ (dic. 2025); ~100 brazos en Medra Lab 001 [20][21] [H·b] | Muchos instrumentos y protocolos distintos; se cambia el flujo hablando [21] | **Sí**: tubos y gradillas pesan poco; demo de asistente de bancada |
| 18 | **Diligent** (EE. UU.) | Moxi: llevar medicamentos y muestras por el hospital | >30 hospitales; >1 M de entregas (feb. 2025) [22] | Serve Robotics anunció su compra (ene. 2026) [22] [H·b] | Navegación y puertas/ascensores [I] | No (móvil) |
| 19 | **Bear Robotics** (EE. UU./Corea) | Servi: robot camarero que lleva platos | Restaurantes en EE. UU., Corea, Japón; LG mayoritaria [23] | Serie C 60 M$ (LG) [23] [H·b] | Poco VLA (navegación) [I] | No |
| 20 | **The Bot Company** (EE. UU.) | Robot doméstico aún sin presentar | Sin clientes públicos [24] | 150 M$ a 2.000 M$; rumor a 4.000 M$ [24] [H·b] | — | No hay tarea |
| 21 | **Galbot** (China) | G1 semihumanoide sobre ruedas: farmacia 24 h (coger cajas de medicamento de estantería) y tiendas autónomas | Farmacia en Haidian (Pekín) desde 2026; con Meituan desde 2024; ~5.000 SKU, ~99,5 % de agarre (secundaria) [25] | >1.100 M$ acumulados, valoración 3.000 M$ [25] [H·b] | Miles de cajas distintas, pedidos por receta [I] | **Sí**: estante con 6-8 cajitas, coger las de la receta. Muy buena |
| 22 | **AgiBot** (China) | A2-W/G2: alimentar líneas (Fulin Precision, ~100 robots), carga/descarga de tablets (Longcheer, ~3.000 uds/turno) [26] | Fulin Precision, Longcheer [26] | 5.168 uds en 2025 (Omdia), 15.000.º robot jun. 2026 [26] [H·b] | Cambios de línea rápidos (integración en 36 h) [26] | Sí: carga/descarga de piezas pequeñas en bandeja-útil |
| 23 | **X Square Robot** (China) | Modelo WALL-OSS + robots: limpieza doméstica con 58.com, programa de convivencia en familias, logística | 58.com (Shenzhen, Pekín) [27] | Valoración >2.800 M$ (30-6-2026) [27] [H] | Hogares variados [I] | Parcial (doméstico) |
| 24 | **Telexistence** (Japón) | TX SCARA repone bebidas en neveras de tiendas; teleoperación si falla la IA | FamilyMart: 300 tiendas; hasta 1.000 latas/día por unidad [28] | RaaS [28] [H·b] | Huecos y productos variables; fallos los recoge un humano [28] | Parcial: lata real 330 ml ≈ 350 g, supera la carga; minibotellas sí [I] |
| 25 | **Mujin** (Japón) | MujinOS: picking de piezas, despaletizado | JD.com, UNIQLO, PALTAC, Fancl [29] | Serie D 233 M$ (dic. 2025) [29] [H·b] | Mezcla de visión 3D y planificación; poco VLA [I] | Sí (picking), poco "VLA" |
| — | RLWRLD (Corea), Sanctuary (Canadá, ref.) | Modelo para manos diestras RLDX-1 (may. 2026); inserción de cables >99,5 % en proveedor de automoción [30][31] | Sin clientes nombrados (RLWRLD) [30] | — | Destreza fina [I] | No: inserción de cables exige precisión sub-mm [I] |

No investigadas a fondo por tiempo: Unitree, Fourier, Field AI, Genesis AI, Matic, Labrador (hardware de locomoción,
navegación u hogar; ninguna con tarea de manipulación de banco que encaje) [I].

## 2. Patrones: qué pagan hoy los clientes

1. **Lo que se paga es coger-y-dejar con mucha variedad**, no destreza espectacular: kitting y empaquetado de pedidos
   (Ultra, Tutor, Covariant, Mujin), reposición de estanterías (Telexistence, Galbot), carga de útiles y máquinas
   (Figure/BMW, AgiBot, Standard Bots), porcionado (Chef) [H·b]. El aprendizaje se justifica por la **cola larga de
   SKU** y por los **cambios frecuentes de producto**, no por la dificultad de un movimiento aislado [I].
2. **Modelo de negocio RaaS / suscripción** casi universal: Tutor (~14 $/h), Chef, Formic, Dyna, Telexistence, Weave
   (449 $/mes) [H·b]. El cliente compra horas de trabajo, no un robot [I].
3. **El humano sigue en el bucle**: Telexistence pasa a teleoperación si falla, Weave y 1X tienen operador remoto, PI
   mide "96,4 % de autonomía" (o sea, intervenciones) [H·b]. La colaboración humano-robot es real, aunque no siempre
   se venda así [I].
4. **Las métricas que convencen** son tasa de éxito por turno, intervenciones por turno, unidades/turno y horas sin
   parar (BMW: >99 % de colocaciones, 0 intervenciones como objetivo) [H]. Una demo creíble debe mostrar una
   métrica de este tipo, no solo "funciona una vez" [R].
5. **Órdenes en lenguaje natural** aparecen donde hay muchas variantes de tarea: Medra (protocolos de laboratorio),
   Galbot (recetas), Covariant RFM-1 (órdenes en texto o imagen) [H·b]. Ese es el hueco donde un VLA aporta algo
   que ACT no da: **elegir qué coger según la orden** [I].
6. Lo que **no** cabe en un SO-101: carga pesada (Dexterity, Formic), locomoción (Diligent, Bear, 1X), tela grande
   bimanual (Dyna, Weave), inserción sub-mm (Sanctuary) [I].

## 3. Las 5 aplicaciones mejor demostrables con un SO-101

Criterios: valor real, necesita VLA, baja probabilidad de fallo, uso tal cual (hobby o industria), colaboración
humano-robot.

### A. Preparación de kits por pedido ("pick-to-kit" de banco)
- **Referencia:** Ultra (con π0.6 de Physical Intelligence) y Tutor Intelligence [2][3][4].
- **Cliente real:** Highline Commerce (Ultra); marcas de consumo y 3PL sin nombre (Tutor) [H·b].
- **Tarea real:** sacar de cubetas los artículos de una orden y dejarlos en la caja o bandeja del pedido.
- **Demo:** banco con 5-6 cubetas (tornillería grande, conectores, pilas, cinta, bridas, LED en blíster) y una bandeja
  de kit. El juez escribe o dice un pedido ("kit para montar un sensor: un Arduino, dos cables, una pila") o elige
  una tarjeta de orden. Órdenes del VLA por artículo: "coge la pila y déjala en la bandeja". Final visible: bandeja
  completa y el operador (persona) monta con ella; contador de artículos correctos/errores en pantalla.
- **Por qué VLA:** el mismo gesto con objetos distintos según la orden; con ACT habría que entrenar una política por
  artículo [I].
- **Riesgo de fallo:** bajo-medio. Objetos rígidos y ligeros; el riesgo está en confundir artículo si hay más de
  ~6 clases o en agarrar cosas planas pegadas al fondo [I].

### B. Dispensación por receta (farmacia o almacén de recambios)
- **Referencia:** Galbot G1 en farmacia 24 h de Haidian, Pekín; con Meituan desde 2024 [25].
- **Cliente real:** farmacia de Haidian / Meituan [H·b].
- **Tarea real:** coger de la estantería las cajas de medicamento de una receta y entregarlas en el mostrador.
- **Demo:** estante de 2 baldas con 6-8 cajitas reales de farmacia sin receta (ibuprofeno, tiritas, suero...) y una
  bandeja de entrega. El juez dicta una "receta" de 2-3 productos; el robot los coge uno a uno y los deja en la
  bandeja; el farmacéutico (miembro del equipo) valida y entrega. Final: bandeja con exactamente lo pedido.
- **Por qué VLA:** condicionar por texto qué caja coger entre varias muy parecidas [I].
- **Riesgo:** bajo si las cajas son rígidas y están de frente; medio por lectura de cajas similares (usar colores o
  formas distintas al principio) [I]. Nota: el usuario pide "uso real tal cual"; en Europa no es una farmacia real
  sin regulación → versión "almacén de recambios del taller" con la misma mecánica [R].

### C. Carga del útil de trabajo (tercera mano del banco de soldadura)
- **Referencia:** Figure F.02 en BMW Spartanburg (piezas de chapa al útil de soldadura) [11]; AgiBot en Longcheer
  (carga/descarga de tablets) [26]; Standard Bots (carga de máquinas) [17].
- **Cliente real:** BMW (Figure), Longcheer y Fulin Precision (AgiBot) [H] [H·b].
- **Tarea real:** coger piezas de una cubeta y colocarlas en el útil antes de que una persona o una máquina trabaje.
- **Demo:** banco de electrónica: el robot coge una placa o componente de una cubeta, lo deja en un soporte de PCB
  (o pinza de tercera mano) orientado; la persona suelda; al decir "listo" el robot retira la placa a "terminadas" y
  trae la siguiente. El juez suelda o pide "siguiente". Final: 3-4 placas terminadas en el ciclo.
- **Por qué VLA:** cambiar entre "trae la siguiente", "retira la soldada", "dame la de color X" según lo que diga la
  persona; con un solo ACT valdría para una secuencia fija [I].
- **Riesgo:** medio: colocar en un soporte exige pocos mm (en el límite del SO-101); se reduce con un útil con embudo
  o topes [I]. Encaja con la dirección "tercera mano de taller" ya elegida [criterios-usuario.md].

### D. Asistente de bancada de laboratorio
- **Referencia:** Medra (brazos genéricos que operan instrumentos por órdenes en lenguaje natural) [20][21].
- **Cliente real:** Genentech, Addition Therapeutics, Cultivarium [H·b].
- **Tarea real:** mover tubos y placas entre gradillas e instrumentos según el protocolo que dicta el científico.
- **Demo:** gradilla con tubos Falcon de colores, una mini centrífuga o vortex de sobremesa y una gradilla "hecho".
  El juez dice "pon los tubos rojos en la centrífuga" o "lleva el azul a la gradilla de salida". Final: tubos en su
  sitio según la orden.
- **Por qué VLA:** el protocolo cambia y se dicta hablando, que es exactamente la propuesta de valor de Medra [21].
- **Riesgo:** medio: los tubos son finos y cilíndricos (agarre bueno pero puede volcar); meterlos en el rotor exige
  precisión. Un laboratorio de hobby (biología DIY) es más raro que un banco de electrónica [I].

### E. Reposición de estantería frontal
- **Referencia:** Telexistence en FamilyMart (300 tiendas) [28]; Galbot Store [25].
- **Cliente real:** FamilyMart [H·b].
- **Tarea real:** detectar huecos en la estantería o nevera y reponer el producto que falta.
- **Demo:** estantería con 3 carriles de minibotellas o cajitas; el juez se lleva un producto ("compra"); el robot,
  ante "repón lo que falta", coge uno igual de la caja de reserva y lo coloca en el hueco. Final: estantería completa.
- **Por qué VLA:** decidir qué producto falta y dónde va, a partir de la imagen [I].
- **Riesgo:** medio: empujar el producto hasta el fondo del carril y el peso de las bebidas reales (superan la
  carga). Valor "en casa/hobby" bajo [I].

### Top 2 [R]
1. **A · Kits por pedido** (Ultra/PI, Tutor): el caso con más tracción pública (pedidos reales, 96,4 % de autonomía en
   un turno), objetos ligeros y rígidos, el VLA se justifica de verdad (qué coger según la orden) y tiene una versión
   de banco de taller/hobby real (preparar el kit de componentes para el que monta). Riesgo bajo-medio.
2. **C · Carga del útil / tercera mano de soldadura** (Figure/BMW, AgiBot): la referencia más citable (BMW, 30.000
   coches), conecta con el ganador de Robotekin (asistente de soldadura) y con la dirección "tercera mano" ya elegida,
   y es colaboración humano-robot pura (robot carga, persona suelda). Riesgo medio por precisión → mitigar con útil de
   embudo.
   Se pueden combinar: el robot prepara el kit (A) y luego va alimentando el soporte de soldadura (C) [R].

## Fuentes
1. AI Magazine, "Physical Intelligence: What are Robot Foundation Models?" https://aimagazine.com/news/physical-intelligence-what-are-robot-foundation-models · PI, π*0.6: https://pi.website/blog/pistar06 · PI, partners: https://www.pi.website/blog/partner (no se pudo abrir, 429)
2. Humanoids Daily, PI con Weave y Ultra: https://www.humanoidsdaily.com/news/the-api-fication-of-robotics-physical-intelligence-unveils-real-world-performance-data-with-weave-and-ultra
3. Ultra 62 M$ y PI: https://cryptobriefing.com/ultra-raises-62m-physical-intelligence-partnership/ · https://aiweekly.co/alerts/warehouse-robot-startup-ultra-raises-62m-partners-with-physical-intelligence-on
4. Tutor Serie B: https://cryptobriefing.com/tutor-intelligence-75m-series-b-a16z/ · Serie A: https://siliconangle.com/?p=722916 · https://www.automatedwarehouseonline.com/tutor-intelligence-raises-34m-scale-warehouse-robot-fleet/
5. RuntimeWire, Dyna y Din Tai Fung (27-8-2026, leída): https://runtimewire.com/article/dyna-robotics-din-tai-fung-napkin-folding-rollout
6. Dyna financiación: https://thelettertwo.com/2025/09/15/dyna-robotics-120m-funding-general-purpose-robots/ · https://siliconangle.com/2025/04/29/dyna-robotics-debuts-dyna-1-foundation-model-powering-robots
7. Weave (post de la empresa en LinkedIn, vía buscador): https://tr.linkedin.com/in/kaannarin
8. Weave Isaac 1: https://thenextweb.com/news/weave-robotics-isaac-1-home-robot · https://www.eweek.com/news/weave-8k-laundry-robot-needs-humans/
9. Generalist: https://www.robotics247.com/article/generalist-raises-400m-to-scale-physical-ai/nvidia · https://generalistai.com/blog/nov-04-2025-GEN-0 · https://machinedesign.com/automation-iiot/article/55391184/teradyne-the-ai-trainer-the-generalist-and-the-cable-inserter-walk-into-a-booth
10. Skild AI: https://aimagazine.com/news/skild-ai-omni-bodied-robot-brain-passes-us-100m-arr · https://pulse2.com/skild-ai-1-4-billion-funding/
11. Figure, "F.02 Contributed to the Production of 30,000 Cars at BMW" (leída): https://figure.ai/news/production-at-bmw
12. 1X NEO: https://www.businesswire.com/news/home/20251027434628/en/1X-Launches-NEO-The-Robot-Redefining-Life-at-Home · https://1x.tech/discover/neo-home-robot
13. Sunday Memo: https://www.sunday.ai/journal/series-b · https://www.eweek.com/news/sunday-memo-home-robot/
14. Chef Robotics: https://www.therobotreport.com/chef-robotics-brings-in-43m-to-deploy-more-food-assembly-robots/ · https://agfundernews.com/breaking-chef-robotics-raises-43m-series-a-to-scale-ai-enabled-robotics-in-meal-assembly
15. Dexterity: https://www.supplychain247.com/article/ai-powered-dexterity-valued-at-1.65-billion
16. Covariant: https://siliconangle.com/2024/09/02/amazon-hires-founders-ai-robotics-startup-covariant · https://en.wikipedia.org/wiki/Covariant_(company)
17. Standard Bots: https://siliconangle.com/2024/07/12/standard-bots-reels-63m-ai-powered-robotic-arms/
18. Formic y Jacobi: https://www.manufacturing.net/automation/news/22977055/formic-raises-50-million-to-scale-physical-ai-across-us-manufacturing · https://jacobirobotics.com/press
19. Mbodi: https://www.therobotreport.com/mbodi-ai-launches-y-combinator-developing-embodied-ai-industrial-robots/ · https://www.automate.org/news/abb-robotics-names-t-robotics-and-mbodi-as-ai-startup-challenge-winners
20. Medra Serie A: https://www.businesswire.com/news/home/20251211748411/en/Medra-Raises-%2452-Million-Series-A-to-Build-Physical-AI · https://www.mobihealthnews.com/news/medra-raises-52m-partners-genentech
21. Medra plataforma: https://www.businesswire.com/news/home/20250912829200/en · https://www.warpnews.org/p/086e0907-70e9-4204-b0a6-beec9fc84644/ · https://www.corememory.com/p/a-hundred-robots-are-running-a-bio-medra-michelle-lee
22. Diligent: https://www.diligentrobots.com/blog/not-a-pilot-not-a-prototypediligent-robotics-hits-1-million-humanoid-deliveriesnbspacross-fleetnbspsupportingnbsphealthcare-customers · https://www.therobotreport.com/diligent-robotics-completes-300000-pharmacy-deliveries-with-moxi/ · https://pymnts.com/healthcare/2026/robots-give-hospitals-more-capacity-without-adding-beds
23. Bear Robotics: https://techcrunch.com/2024/03/12/bear-robotics-a-robot-waiter-startup-just-picked-up-60m-from-lg · https://bearrobotics.ai/About
24. The Bot Company: https://www.therobotreport.com/the-bot-company-led-by-kyle-vogt-brings-in-another-150m/ · https://news.bloomberglaw.com/financial-accounting/cruise-founders-robot-startup-is-in-talks-for-4-billion-value
25. Galbot: https://cntechpost.com/2026/03/02/galbot-secures-major-state-backing · https://pulse2.com/galbot-over-300-million-funding/ · https://aiwiki.ai/wiki/galbot · https://amp.kr-asia.com/galbots-humanoid-robots-do-the-boring-stuff-and-thats-the-point
26. AgiBot: https://www.scmp.com/tech/tech-trends/article/3321456/chinese-robotics-start-agibot-lands-deal-deploy-100-robots-car-parts-factories · https://www.eweek.com/news/agibot-deployment-year-one-robots-ai-models-apac/ · https://english.shanghai.gov.cn/en-Latest-WhatsNew/20250814/fef52cacef5a4872a0678bc842dde446.html
27. X Square Robot (30-6-2026, leída): https://www.therobotreport.com/x-square-robot-brings-valuation-2-8b-four-consecutive-funding-rounds/
28. Telexistence y FamilyMart: https://tx-inc.com/?p=11737 · https://charonhub.deeplearning.ai/tx-scar-robot/
29. Mujin: https://www.robotics247.com/article/mujin_secures_233m_in_series_d_funding_round · https://thebridge.jp/en/2025/12/mujin-raises-%C2%A536-4-billion-in-initial-close-of-series-d-round-jointly-led-by-ntt-group-and-qatar-investment-authority
30. RLWRLD: https://www.therobotreport.com/rlwrld-releases-rldx-1-a-dexterity-first-foundation-model-for-robot-hands/ · https://aws.amazon.com/blogs/physical-ai/aws-rlwrld-building-the-workforce-of-tomorrow-with-physical-ai
31. Sanctuary, inserción de cables: https://mikekalil.com/blog/sanctuary-ai-wire-harness-assembly/ · https://humanoid.guide/?p=16324
