# Necesidad real · frente PRODUCCIÓN Y AUTOMATIZACIÓN (18-11-2026)

Método `research-ops`. Marcas: **[H]** hecho con fuente (página leída), **[H·b]** hecho visto solo en el extracto del
buscador (sin abrir la página: verificar antes del pitch), **[I]** inferencia, **[R]** recomendación. Las cifras de
fabricantes y consultoras se marcan «(fabricante)»: son afirmaciones comerciales, no datos independientes.
Fuera de este frente: mantenimiento, baterías y asistencia (ver [diagnostico.md](diagnostico.md)).

## 0. Contexto en cifras (vale para todas las necesidades)

- España instaló 5.100 robots industriales en 2024, tercera de Europa, sobre todo por la automoción [H, F1]. En la UE
  la proporción de empresas que usan robots bajó del 6,7 % (2018) al 6,3 % (2022); en manufactura, algo más del 16 %
  usa robots industriales; uno de cada cinco grandes frente a muy pocas pymes [H·b, F2]. Es decir: **los robots se
  concentran en las grandes y en las series largas** [I].
- 60,2 % de las empresas industriales españolas dicen que encontrar mano de obra cualificada es su principal reto;
  **50,4 % señalan a operarios y soldadores como los perfiles más difíciles** y 27,3 % a los ingenieros de
  automatización (Easyfairs, 1.er estudio del sector manufacturero, oct. 2024; tamaño de muestra no publicado) [H, F3].
  Euskadi: 79 % de las empresas industriales tuvieron dificultades para contratar (Confebask, 2024) [H·b, F4].
  UE: el 19 % de las empresas industriales citaba la falta de mano de obra como freno a la producción en el 1.er
  trimestre de 2025 (22,3 % un año antes) [H·b, F5]. Matiz honesto: la tasa de vacantes de España en industria es
  baja (0,5 % frente a 1,8 % UE): **escasez selectiva de perfiles, no general** [H·b, F6].
- Ergonomía, España 2024: 156.898 accidentes con baja por sobreesfuerzos, el 29 % de todos; los trastornos
  musculoesqueléticos (TME) fueron el 78 % de las enfermedades profesionales (INSST) [H, F7]. UE: el 63 % de los centros
  de trabajo declara movimientos repetitivos de mano o brazo y el 52 % manipulación de cargas pesadas (ESENER 2024,
  41.000 centros) [H, F8]; en la encuesta a trabajadores, el dolor de miembro superior (52,6 %) es el problema de salud
  más citado (EWCS 2024) [H·b, F9]. **No encontré el desglose solo de manufactura** [hueco].
- Coste de reprogramar: el robot suele ser solo el 25-50 % del coste de una célula; integración y programación,
  200-800 horas de ingeniería en pymes (blogs de integradores, cifras dispares) [H·b, F10, fabricante]. No encontré
  ninguna encuesta independiente 2024-2026 que mida el coste de un cambio de referencia [hueco].
- Por qué ahora: en 2026 los grandes enseñan por demostración en vez de programar: Siemens mostró en Hannover Messe
  2026 un VLA entrenado con teleoperación («personas repiten la misma tarea cientos de veces») [H, F11]; Universal
  Robots/Teradyne con Scale AI y Generalist, en Automate 2026: cobots guiados a mano cuyos datos entrenan un VLA «sin
  programación tradicional» (el modelo de Generalist: «cientos de horas» de demostraciones) [H, F12]; mimic (ETH) dice
  que pasa de 30 h de demostraciones a ~30 min en pruebas con Audi [H, F13, fabricante]; Figure 02 en BMW cargó
  >90.000 piezas de chapa en 11 meses [H·b, F14, fabricante]. **Ninguna fuente independiente mide tasas de éxito en
  producción** [I]: el estado real es «piloto», que es justo el hueco de una demo honesta.

## 1. Necesidades (6)

| # | Necesidad y persona | Dolor cuantificado | Qué hacen hoy y por qué no basta | Por qué ahora (VLA) | Demo con SO-101 y órdenes | Riesgos |
|---|---|---|---|---|---|---|
| 1 | **Kitting de montaje en alta variedad**: Ainhoa, preparadora de kits de un proveedor de automoción o de bienes de equipo; cada variante de producto pide un kit distinto | Operarios: el perfil más difícil de cubrir (50,4 %) [H, F3]; un kit erróneo para la línea, por eso se exige ≥ 99,9 % de acierto (guía sectorial) [H·b, F15]; movimientos repetitivos en el 63 % de centros [H, F8] | A mano con hoja o pick-to-light; carruseles y AutoStore (caros, solo almacenan) [H·b, F16]; un cobot programado por puntos exige reprogramar cada variante: no compensa con lotes pequeños [I] | Mismo robot, kit distinto según la frase; variante nueva = enseñar 50 demos, no programar [R] | 4-5 cubetas con piezas gruesas impresas en 3D (casquillo, tapa, soporte, tuerca grande) → bandeja de kit con alojamientos en V. «Kit de la variante A» / «kit de la B, sin la tapa» / «falta un casquillo, complétalo» | Muy parecido al pañol (candidata A) y a la «tercera mano» de MSN; final poco espectacular (bandeja llena); contar piezas y orden es débil en un VLA [I] |
| 2 | **Fin de línea: separar buenas, malas y retrabajo**: Jon, inspector de calidad al final de una línea de inyección o mecanizado | Los inspectores humanos aciertan en torno al 80 % (estudio Sandia con 82 inspectores, 2015) [H·b, F17]; tarea repetitiva [H, F8] | Inspección visual humana (fatiga) o visión clásica con reglas por referencia: cada referencia nueva = reconfigurar [I]; visión con IA solo clasifica, no separa [I] | El criterio cambia con la frase sin reprogramar: «hoy las rayadas van a retrabajo» [R] | Piezas gruesas con defectos GRUESOS y visibles (sin agujero, mancha de color, rebaba grande) → 3 cajas con embudo. «Separa las defectuosas» / «las manchadas a retrabajo, las rotas a chatarra» / «deja solo las de la referencia azul» | Un VLA no ve defectos finos: solo defectos de demo; se puede objetar «una cámara + clasificador lo hace mejor» → mostrar la ventaja: separar Y cambiar el criterio hablando [I] |
| 3 | **Alimentar máquinas en lotes cortos (machine tending)**: Iker, operario que carga y descarga 2-3 CNC o inyectoras y no puede irse de la máquina | Células de cobot para una CNC: 40.000-75.000 $ [H·b, F18, fabricante]; integración 200-800 h [H·b, F10]; las máquinas paran por cargas manuales y cambios de serie en alta variedad [H·b, F19] | Cobots programados por punto: rentables con series largas; cada pieza nueva pide pinza, útil y programa [I] | «Carga la pieza redonda» / «ahora la cuadrada»: una red para todas las referencias [R] | Maqueta de máquina (caja con puerta abierta y alojamiento en V) + bandeja de brutos + bandeja de acabadas. «Carga una pieza en bruto» / «descarga y deja en acabadas» / «cambia a la referencia B» | Es la aplicación de cobot ya más resuelta comercialmente: el VLA se ve poco; la escena es lenta; abrir puertas reales queda fuera [I] |
| 4 | **Reprogramar la célula en cada cambio de referencia (alta variedad, bajo volumen)**: Maite, la única ingeniera de procesos de una pyme de 40 personas, que no sabe programar robots | El 27,3 % no encuentra ingenieros de automatización [H, F3]; programación de aplicación: 15.000-80.000 $ y 200-800 h [H·b, F10, fabricante]; pocas pymes usan robots [H·b, F2] | Integrador externo (semanas, caro) o no automatizar; arrastrar al robot (programación por guiado) solo copia trayectorias, no generaliza [I] | Es la promesa explícita de Siemens y UR en 2026 [H, F11, F12]; un VLA abierto (SmolVLA) lo pone al alcance de una pyme [I] | Es un **marco**, no una tarea: sobre la demo 1 o 2, mostrar en el escenario una referencia NUEVA enseñada con demos grabadas en el hackathon y el contador «X demos, 0 líneas de código» | Entrenar en directo no cabe (horas en la nube): hay que enseñarlo grabado; riesgo de prometer de más [I] |
| 5 | **Montaje manual repetitivo y lesiones**: Rosa, operaria de premontaje que coloca miles de piezas al día en un útil | 156.898 accidentes por sobreesfuerzos (29 %) y TME = 78 % de las enfermedades profesionales en 2024 [H, F7]; 63 % de centros con movimientos repetitivos [H, F8] | Rotación de puestos, exoesqueletos, ayudas de manipulación; automatizar el montaje fino es caro [I] | Quitar al humano la parte repetitiva de colocar [R] | Colocar piezas gruesas en un útil con embudos (premontaje sin apriete). «Coloca los casquillos en el útil» / «ahora las tapas» | Las lesiones vienen de fuerza, carga y precisión: justo lo que un SO-101 NO hace; promesa poco creíble ante un jurado industrial [I] |
| 6 | **Secuenciar piezas (JIS) para la línea de automoción**: Unai, carretillero o preparador de secuencias en un proveedor junto a la planta | La automoción produce en secuencia (JIS) y exige proximidad y procesos muy eficientes [H·b, F20]; la investigación europea busca robots móviles para el kitting y la secuenciación por coste y errores de la recogida manual [H·b, F21] | Pick-to-light y lanzaderas (caras, solo indican); la colocación sigue siendo manual [H·b, F16] | «Prepara la secuencia: rojo, azul, rojo» [R] | Rack de 4 huecos con embudo; piezas de 3 colores. «Pon la secuencia del pedido 12» | El orden y el recuento son débiles en un VLA de una sola red; si falla una posición, la secuencia entera falla [I] |

## 2. Top 2 [R]

**1.º · Kitting de montaje con cambio de variante por frase (necesidad 1 + marco 4).**
- Es lo que el SO-101 hace bien (coger y dejar piezas gruesas en alojamientos) y lo que el VLA hace mejor: la
  misma mesa, kits distintos según la frase; y una variante nueva se «enseña» en vez de programarse.
- El dolor está medido en España (operarios, perfil más difícil para el 50,4 %; ingenieros de automatización para el
  27,3 %) y el «por qué ahora» tiene nombres de 2026 (Siemens, UR/Teradyne, mimic con Audi).
- Encaja con el jurado industrial de Bilbao (proveedores de automoción y bienes de equipo).
- Pero es casi la candidata A (pañol) con otro cliente: si se elige, decir por qué es mejor que A (en producción el
  cambio de variante es diario; en mantenimiento, ocasional) [I]. Validar con 2-3 llamadas a proveedores de
  automoción de Bizkaia/Gipuzkoa: cuántas variantes, cuántos kits por turno, cuántos errores el último mes.

**2.º · Clasificación al final de línea: buenas / malas / retrabajo con criterio hablado (necesidad 2).**
- Escena de 5 s fuerte: el robot aparta una pieza mala que un humano cansado deja pasar; y el criterio cambia con
  una frase («hoy las manchadas a retrabajo»).
- Cifra de impacto citable (inspectores ~80 % de acierto), aunque viene del extracto: verificarla en la fuente.
- Riesgo principal: solo defectos gruesos. Decirlo abiertamente y posicionarlo como «clasificar y separar con
  criterios que se cambian hablando», no como «visión de defectos mejor que la industria».

Descartadas para el pitch: 3 (VLA poco visible; ya resuelto con cobots), 5 (el SO-101 no aborda la causa real de las
lesiones), 6 (secuencia y recuento poco fiables en vivo). La 4 no es una demo sino el argumento que sostiene la 1 y la 2.

## 3. Fuentes

- F1 · IFR, World Robotics 2025 (nota de prensa, 25-09-2025): https://ifr.org/ifr-press-releases/news/global-robot-demand-in-factories-doubles-over-10-years
- F2 · Eurofound, uso de robots en empresas UE 2018-2022 (buscador): https://www.eurofound.europa.eu/en/data-catalogue/share-enterprises-using-industrial-or-service-robots-eu-2018-2022 y https://www.portfolio.hu/en/economy/20240825/hungary-among-the-leaders-in-robotisation-in-the-eu-705409
- F3 · Easyfairs / Advanced Manufacturing Madrid, 1.er estudio del sector manufacturero (17-10-2024): https://www.advancedmanufacturingmadrid.com/en/?p=399513
- F4 · Confebask 2024, vía Deia (buscador): https://www.deia.eus/economia/2024/04/26/empresas-vascas-realizaran-ano-44-contratacion-confebask-8164560.html
- F5 · Comisión Europea, revisión anual del mercado laboral 2025 (buscador): https://op.europa.eu/webpub/empl/lmwd-annual-review-report-2025/chapter1/labour-market-developments-in-the-eu.html y WIFO BCS oct. 2025: https://www.wifo.ac.at/wp-content/uploads/upload-5432/bcs_2025_10_en.pdf
- F6 · Interempresas / Finanzauto (buscador): https://www.interempresas.net/ObrasPublicas/614162-La-industria-espanola-acumula-mas-de-100000-empleos-sin-cubrir.html
- F7 · INSST, «Los sobreesfuerzos físicos… primera causa de baja» (16-04-2025): https://www.insst.es/noticias-insst/los-sobreesfuerzos-fisicos-en-el-trabajo-son-la-primera-causa-de-baja-laboral-en-nuestro-pais
- F8 · EU-OSHA, ESENER 2024 (07-02-2025): https://osha.europa.eu/en/about-eu-osha/press-room/prolonged-sitting-psychosocial-risks-and-digitalisation-top-workplace-safety-and-health-concerns-new-eu-survey-reveals
- F9 · OSHwiki, introducción a los TME (EWCS 2024) (buscador): https://oshwiki.osha.europa.eu/mt/themes/introduction-musculoskeletal-disorders
- F10 · Costes de integración (blogs de integradores, buscador): https://grabarobot.com/blog/robot-integration-cost-guide-2026/ , https://blog.unchainedrobotics.de/en/how-much-does-a-turnkey-robotics-solution-cost , https://lanpdt.com/tech-talk-episode-19/
- F11 · Machine Design, Siemens en Hannover Messe 2026 (20-05-2026): https://www.machinedesign.com/markets/robotics/article/55378521/siemens-flexible-robots-messy-worlds-inside-siemens-push-for-practical-industrial-ai
- F12 · Machine Design, Teradyne/UR en Automate 2026 (15-07-2026): https://machinedesign.com/automation-iiot/article/55391184/teradyne-the-ai-trainer-the-generalist-and-the-cable-inserter-walk-into-a-booth
- F13 · Unite.AI, mimic FLUX-mimic y Audi (23-07-2026): https://www.unite.ai/mimic-robotics-introduces-flux-mimic-to-bring-video-action-models-to-audis-factory-floor/
- F14 · Figure en BMW (buscador): https://figure.ai/news/f-03-at-bmw y https://www.iiot-world.com/artificial-intelligence-ml/robotics/physical-ai-deployment-roi-humanoid-robots
- F15 · Racklify, precisión de kitting (buscador): https://racklify.com/encyclopedia/what-is-kitting-accuracy-definition-measurement-and-benchmarks/ ; tipos de error de kit en automoción, Chalmers: https://research.chalmers.se/publication/521355/file/521355_Fulltext.pdf
- F16 · Kardex, automoción (buscador): https://www.kardex.com/en/industry-segments/automotive-transportation
- F17 · Sandia, fiabilidad de la inspección visual (Human Factors, 2015) (buscador): https://www.osti.gov/pages/biblio/1236203-visual-inspection-reliability-precision-manufactured-parts
- F18 · Standard Bots, machine tending 2025 (buscador, fabricante): https://standardbots.com/blog/automated-machine-tending-scaling-up-productivity
- F19 · The Machine Maker, escasez de mano de obra (buscador): https://themachinemaker.com/technology/labour-shortage-is-a-production-bottleneck/
- F20 · thyssenkrupp, producción al segundo (JIS) (buscador): https://www.thyssenkrupp.com/en/stories/automotive-production-down-to-the-second
- F21 · I4MS, robot móvil de kitting y secuenciación (buscador): https://i4ms.eu/?p=1944

Huecos: coste medido de un cambio de referencia en una pyme española; TME solo en manufactura; tasa real de error
del kitting manual. Son las preguntas para las llamadas de validación.
