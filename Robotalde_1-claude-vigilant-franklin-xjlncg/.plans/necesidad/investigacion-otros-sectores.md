# Investigación de necesidades fuera del mantenimiento industrial

Fecha: 2026-11-18 · Método research-ops: **[H]** hecho con fuente · **[I]** inferencia propia · **[R]** recomendación.
Nivel de verificación: **(abierta)** = página leída directamente; **(buscador)** = cifra vista en el resumen del
buscador sin poder abrir la página (403/paywall o no leída). Las cifras **(buscador)** hay que comprobarlas antes de
ponerlas en una diapositiva.

Restricciones del SO-101 que filtran todo: coger y dejar objetos ≥ 20 mm, < 300 g, ±1 cm; nada de precisión, fuerza,
objetos pequeños o frágiles, líquidos ni cara. Precio de referencia del brazo: 100 $ el kit básico y hasta ~500 $
según proveedor [H, buscador, TechCrunch S1]; un kit líder+seguidor+cámara a 479,95 € [H, buscador, S2].

## 1. Necesidades candidatas

| # | Necesidad | Quién la sufre | Dolor cuantificado (fuente) | Qué se hace hoy | Por qué ahora | Demo factible y órdenes al VLA | Riesgos |
|---|---|---|---|---|---|---|---|
| A | **Separar pilas y baterías del RAEE pequeño antes de la trituradora** | Operario de la cinta de triaje en una planta de RAEE; gerente que no consigue seguro | Alemania (NRW): ~100 incendios/año en plantas de residuos, según el consejero de Medio Ambiente; un incendio en Swisttal (jul 2025) causó ≥ 2 M€ y se atribuyó a una batería de litio en la trituradora [H, abierta, S3]. Francia: incendios por baterías se duplicaron 2019-2023; Austria: 180-240/año [H, abierta, S4, fuentes sectoriales sin nombre]. Reino Unido: >1.200 incidentes en 2023/24, +71 % (ESA) [H, buscador, S5]. Las aseguradoras rechazan o encarecen pólizas [H, buscador, S5]. España: recogida de RAEE ~47 % frente al objetivo legal del 65 % [H, buscador, S6, S7] | Triaje manual en cinta; detección por rayos X o cámaras térmicas en plantas grandes; investigación en desmontaje robótico (RAISE, Fraunhofer iDEAR, que aprende por imitación) [H, buscador, S8, S9] | Incendios en aumento; el Reglamento UE de Baterías exige baterías portátiles extraíbles desde feb. 2027 [H, buscador, S9]; Austria, Alemania y Lituania pidieron acción a la UE en dic. 2025 [H, abierta, S4] | Bandeja mezclada con maquetas (mando a distancia, ratón, móvil viejo, powerbank, pila tipo C/D, cargador). Órdenes: «saca todo lo que lleve batería», «separa las pilas a la caja roja», «pon los móviles en la caja de reutilización», «deja los cables». El VLA cambia de criterio con la frase, sin reentrenar | Baterías reales = riesgo: usar maquetas o pilas descargadas con cinta. «¿Lleva batería?» no siempre se ve: el VLA clasifica por apariencia, decirlo con honestidad. Móviles finos y planos cuestan de agarrar (usar fundas gruesas o soporte) |
| B | **Alcanzar objetos de uso diario a una persona con movilidad reducida** (sin líquidos ni cara) | Persona con lesión medular, ELA o distrofia que pasa horas sola; su cuidadora (madre, 45-64 años) | España: 4,32 M de personas con discapacidad (EDAD 2020); 3,3 M reciben ayuda técnica o personal; 63,7 % de los cuidadores principales son mujeres [H, buscador, S10, S11]. Brazo asistivo comercial JACO: > 40.000 $ [H, buscador, S12]; robot Stretch: 20.000-25.000 $ [H, buscador, S13] | Ayuda humana; teleasistencia (14,7 %) y ayuda a domicilio (11,7 %) [H, buscador, S14]; brazos en silla de ruedas caros y poco cubiertos | Los VLA permiten pedir por voz o texto sin programar; un brazo de ~100-500 $ baja el precio en dos órdenes de magnitud [I] | Mesa de noche con mando de TV, gafas en estuche, móvil en funda gruesa, pastillero cerrado, libro. Órdenes: «acércame el mando», «trae el pastillero a la bandeja», «guarda las gafas en el cajón», «recoge la mesa». La persona solo pide; el brazo deja el objeto en una bandeja fija a su alcance, nunca en la mano | Seguridad cerca de personas (el jurado lo mirará con lupa): zona de entrega fija, velocidad baja. Riesgo de «demo de juguete» si no se cuenta bien. Hay muchos trabajos parecidos (Stretch, HAT) |
| C | **Montaje de bandejas/kits quirúrgicos** | Técnico de esterilización (central de esterilización) | 3.900 defectos de bandeja en 41.799 cirugías; 55 % en el montaje; afectan al 5 % de las cirugías; faltan instrumentos en el 17,6 % de los defectos (hospital de EE. UU., 2016-17) [H, abierta, S15]. El 88,6 % de los errores observados son de inspección visual [H, buscador, S16]. Escasez crónica de personal en esterilización [H, buscador, S17] | Montaje manual con lista de comprobación; doble verificación; trazabilidad por código | Presión en quirófanos; errores caros en minutos de quirófano [H, buscador, S16] | Bandeja con maquetas gruesas (mangos impresos en 3D); «prepara la bandeja de traumatología», «añade lo que falte», «retira las pinzas» | **Instrumental real fino y metálico: fuera de alcance del SO-101.** Demo con maquetas = poco creíble para el jurado. Mucha regulación sanitaria |
| D | **Clasificación de donaciones en un banco de alimentos** | Voluntario del Banco de Alimentos (la mayoría jubilados) en la Gran Recogida | FESBAL 2024: 115.563 t distribuidas a 1.036.890 personas, con 96.707 personas, 93,3 % voluntarias [H, buscador, S18]. Madrid: 92 % voluntarios [H, buscador, S19] | Clasificación manual por tipo y caducidad en mesas | La Gran Recogida es a finales de noviembre: coincide con el hackathon [I, comprobar fecha 2026] | Cajas de leche, latas, paquetes de pasta, legumbre: «separa las latas», «pon lo de desayuno en la caja azul», «aparta lo que sea para bebés» | Leer la caducidad no es realista con la cámara; un paquete de 1 kg pasa de 300 g (usar envases de 200-250 g). El impacto es real pero el robot ahorra poco frente a voluntarios |
| E | **Picking y preparación de pedidos mixtos (última milla, farmacia de barrio)** | Mozo de almacén; auxiliar de farmacia que prepara pedidos | Alemania: >60.000 puestos de logística de almacén sin cubrir en 2025 (IAB) [H, buscador, S20]. UE: «peones de fabricación» con tasa de vacantes del 7,3 % en 2024 [H, buscador, S21] | Picking manual; robots de picking caros (KNAPP, Brightpick) [H, buscador, S20] | Robots de picking que aprenden por imitación salen al mercado [H, buscador, S20] | Cajas de medicamentos vacías: «prepara el pedido de la señora García: ibuprofeno y vitamina C» | Muy trillado; empresas grandes ya lo hacen; poco «impacto social» |
| F | **Clasificar ropa usada por tipo para reutilización** | Trabajador de una entidad social de recogida de textil (inserción laboral) | El triaje de textil es ~85 % manual; el automático es 30-50 % más caro [H, buscador, S22]; ~25 kg/persona/hora (dato de proveedor) [H, buscador, S23] | Triaje manual en mesa; líneas automáticas en el norte de Europa (PICVISA) | La recogida separada de textil es obligatoria en la UE desde 2025 y llega la RAP textil [H, buscador, S24] | Prendas pequeñas: «separa los calcetines», «las camisetas a reutilizar», «lo roto a reciclaje» | La tela es blanda y se engancha; distinguir «roto» o fibra es imposible con la cámara. Demo poco fiable |
| G | **Laboratorio: ordenar tubos por color de tapón y gradillas** | Técnico superior de laboratorio clínico | La fase preanalítica concentra el 46-68 % de los errores de laboratorio (Plebani) [H, buscador, S25]; 46 % de los laboratorios citan la financiación como freno a la automatización [H, buscador, S26] | Automatización completa en hospitales grandes (cientos de miles de €) [H, buscador, S27] | Pocas: en España hay 5.755 titulados en paro, no hay escasez clara [H, buscador, S28] | Tubos gruesos impresos: «tubos de tapón morado a la gradilla de hematología» | Tubos de 13-16 mm: por debajo de 20 mm y precisión de gradilla < 1 cm. **No factible con fiabilidad** |

Educación técnica / FP: no la propongo como necesidad propia. La escasez de técnicos en robótica aparece sobre todo en
fuentes interesadas (p. ej. «93 % de empresas», de una consultora) [H, buscador, S29], y la demo sería el propio
SO-101 como recurso didáctico, que ya es lo que es. [I] Encaja mejor como argumento secundario («y además el kit
cuesta lo que un ordenador de aula»).

## 2. Top 2

**1.º · A. Separar baterías del RAEE antes de la trituradora** [R]
- Dolor con cifras recientes, europeas, verificables y con coste (incendios de millones de euros, aseguradoras que no
  cubren) y con un plazo normativo (baterías extraíbles en 2027). Encaja en impacto social y ambiental.
- El VLA se luce: los mismos objetos y la misma red, y el criterio cambia con la frase («saca lo que tenga batería» o
  «separa lo reutilizable»). Es justo lo que no hace una cinta con reglas fijas.
- Física favorable: mandos, ratones, powerbanks y pilas gruesas son objetos de 50-250 g y ≥ 20 mm, coger y dejar en
  cajas con ±1 cm de margen.
- Narrativa barata frente a cara: rayos X o líneas industriales frente a un brazo de ~500 € que podría estar en un
  punto limpio o en una pequeña planta [I: no he encontrado precios de detectores para comparar, falta fuente].
- Honestidad: decir que el robot hace el «pre-triaje» de lo visible, no detecta baterías ocultas.

**2.º · B. Alcanzar objetos a una persona con movilidad reducida** [R]
- Máximo encaje con el premio de Impacto Social y cifras españolas oficiales (INE EDAD 2020). Contraste de precio
  muy fuerte: > 40.000 $ (JACO) frente a cientos de euros.
- Órdenes en lenguaje natural muy distintas y naturales («acércame el mando», «guarda las gafas»), ideal para enseñar
  el VLA en vivo, y el público entiende el valor en 5 segundos.
- Riesgo principal: seguridad cerca de personas. Se gestiona con una zona de entrega fija (bandeja) y sin contacto,
  lo que además respeta las exclusiones ya decididas (sin líquidos ni cara).

Descartadas como principales: C (instrumental real fuera de alcance), G (tubos demasiado finos), F (tela), E (poco
diferencial), D (bonita pero el robot aporta poco; podría ser un «modo» extra de A o B).

[I] Opción combinada: una misma red con dos escenarios (punto limpio y mesa de noche) refuerza el mensaje de VLA
generalista, pero duplica las demostraciones a grabar (50-150 por tarea). Solo si sobra tiempo.

## 3. Fuentes

- S1 TechCrunch, SO-101 desde 100 $: https://techcrunch.com/2025/04/28/hugging-face-releases-a-3d-printed-robotic-arm-starting-at-100
- S2 OpenELAB, kit 479,95 €: https://openelab.io/de/blogs/learn/are-robotic-arm-kits-worth-the-money
- S3 Packaging Europe (8 jul 2025), incendios en plantas de triaje: https://www.packagingeurope.com/sorting-facility-fires-reignite-demands-for-battery-deposit-and-safety-laws/
- S4 SteelOrbis (31 ago 2026): https://www.steelorbis.com/steel-news/latest-news/lithium-ion-batteries-a-growing-threat-across-europes-scrap-and-recycling-chain-1473916.htm ; Recycling Magazine (18 dic 2025): https://www.recycling-magazine.com/2025/12/18/rising-lithium-battery-fires-in-waste-management-trigger-calls-for-urgent-eu-action/
- S5 Waste360, Reino Unido: https://www.waste360.com/waste-recycling/uk-recycling-centers-see-10-battery-fires-a-week-as-tossed-vapes-spark-1-3-billion-toll
- S6 ERP España (oct 2024), recogida 47 %: https://erp-recycling.org/es-es/news-and-events/2024/10/erp-espana-en-el-vi-congreso-nacional-de-gestion-de-raee/
- S7 MITECO, objetivos RAEE 2026: https://www.miteco.gob.es/content/dam/miteco/es/calidad-y-evaluacion-ambiental/sgecocir/raee%27s/objetivos-de-recogida-separada/Resolución%20y%20objetivos%20mínimos%20de%20recogida%20de%20RAEE%20estatales%20y%20autonómicos%202026.pdf
- S8 RAISE (arXiv 2509.23048): https://arxiv.org/abs/2509.23048
- S9 Wevolver, desmontaje de RAEE y Reglamento de Baterías: https://www.wevolver.com/article/engineering-smarter-e-waste-disassembly-with-robots-and-ai ; Electronica (Fraunhofer): https://electronica.de/en/industry-portal/detail/how-ai-and-automation-are-redefining-post-use-recycling.html
- S10 SID-INICO (USAL), EDAD 2020: https://sid-inico.usal.es/noticias/432-millones-de-personas-tienen-algun-tipo-de-discapacidad-en-espana-un-14-mas-que-en-2008/
- S11 INE, metodología EDAD 2020: https://www.ine.es/metodologia/t15/meto_edad_2020.pdf
- S12 NIBIB, R-ARM (> 40.000 $ JACO): https://www.nibib.nih.gov/sites/default/files/R-ARM.pdf
- S13 IEEE Spectrum, Stretch: https://spectrum.ieee.org/stretch-assistive-robot ; MedicalXpress 2024: https://medicalxpress.com/news/2024-02-home-robot-interface-person-quadriplegia.pdf
- S14 Fundación Caser: https://www.fundacioncaser.org/sites/default/files/adjuntos/fundacion_caser_revista_actas_n31_prestaciones_sanitarias_sociales_y_economicas.pdf
- S15 Alfred et al., BMJ Quality & Safety: https://pmc.ncbi.nlm.nih.gov/articles/PMC7979531
- S16 Infection Control Today (sep 2024): https://www.infectioncontroltoday.com/view/addressing-sterile-processing-instrument-errors-advanced-technology-data-insights
- S17 OR Manager (sep 2025): https://ormanager.com/briefs/report-warns-sterile-processing-staffing-crisis-threatens-surgical-safety
- S18 Memoria FESBAL 2024: https://www.globalgiving.org/pfil/59367/Memoria_FESBAL_2024_INGLS_2.pdf
- S19 Banco de Alimentos de Madrid, datos 2024: https://bamadrid.org/wp-content/uploads/2025/02/DATOS-BASICOS-FBAM-cierre-2024.pdf
- S20 Iceclog, robótica en logística europea: https://iceclog.com/from-manual-warehouses-to-ai-powered-operations/
- S21 Cyprus Mail (Eurostat, vacantes 2024): https://cyprus-mail.com/2025/12/11/sales-managers-top-eu-job-vacancy-rate
- S22 Performance Days (mar 2026): https://www.performancedays.com/loop/trends-forum/focus-topic/2026-03-textile-to-textile-the-role-of-collectors-and-sorters.html
- S23 Kings Research (proveedor): https://www.kingsresearch.com/blog/textile-recycling-ai-automation
- S24 Reconomy, RAP textil: https://www.reconomy.com/2026/03/03/textile-epr-europe-2028/
- S25 Westgard, Plebani: https://www.westgard.com/essay114.htm
- S26 Lab Manager, encuesta: https://www.labmanager.com/who-s-investing-in-lab-automation-and-why-18194
- S27 Hudson Robotics (proveedor): https://hudsonrobotics.com/?p=5809
- S28 SEPE, Técnico Superior en Laboratorio Clínico 2025: https://www.sepe.es/HomeSepe/en/que-es-observatorio/informacion-titulaciones/buscador-titulaciones/titulacion-detalle-anual~__titulaciones-fp__2025_517250022117-T-cnico-superior-en-laboratorio-cl-nico-y-biom-dico~.html
- S29 Ecosistema Startup, vacantes industria: https://ecosistemastartup.com/?p=97094

Pendiente de verificar antes de usar en el pitch: S5 (403), S18 (403), S6 (no se pudo abrir), y todas las marcadas
**(buscador)**. No he encontrado datos de España sobre incendios en plantas de RAEE: es un hueco a cubrir.
