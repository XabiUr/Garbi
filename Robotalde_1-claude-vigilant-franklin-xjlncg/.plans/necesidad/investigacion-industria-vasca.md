# Industria vasca y adopción de robots · investigación (18-11-2026)

Método `research-ops`: **[H]** hecho con fuente (URL), **[I]** inferencia, **[R]** recomendación. «(buscador)» =
solo lo vi en el extracto del buscador, no abrí la página. Cifras de proveedores o integradores = orientación, no
prueba. No repito mantenimiento, baterías ni asistencia (ver `diagnostico.md`).

## 1. Peso de la industria en Euskadi

- [H] La industria genera el **23,7 % del valor añadido** vasco (2023) y el **20,1 % del empleo**, frente al 11,3 %
  en España y el 15,4 % en la UE-27 (Eustat, *Panorama de la Industria Vasca 2025*) (buscador):
  https://es.eustat.eus/elem/ele0024700/not0024790_c.pdf
- [H] La ingeniería mecánica (incluye máquina-herramienta) es la rama manufacturera con más empleo, 8,1 % (Eustat,
  Encuesta Industrial 2023) (buscador), misma fuente.
- [H] Máquina-herramienta: 575 establecimientos, >23.600 empleos y ~11.000 puestos de relevo hasta 2036 (ya citado
  en `investigacion-mantenimiento-euskadi.md`, sección 0).
- [H] BIEMH 2026 (2-6 marzo, BEC) tuvo área propia de automatización y robótica; Yaskawa, Kuka y ABB llevaron
  robots con IA y Taiwán cobots con visión **para carga y descarga de piezas** (buscador):
  https://www.interempresas.net/Informatica_Industrial/621326-Yaskawa-muestra-BIEMH-2026-plataforma-Motoman-Next-generacion-automatizacion-robotica.html
  · https://www.interempresas.net/MetalMecanica/625367-Taiwan-refuerza-su-apuesta-industrial-en-Europa-desde-BIEMH-2026.html

### Fases que siguen siendo manuales (por sector)

| Sector | Fase manual | Por qué sigue manual | Fuente |
|---|---|---|---|
| Máquina-herramienta y mecanizado (pymes, talleres) | Carga y descarga de piezas en máquina, cambio de referencia | Lotes pequeños: el coste está en rehacer la célula cada vez que entra una referencia nueva (YK Robotics) [H, buscador] | https://emprendedores.es/innovacion/yk-robotics/ |
| Conserva de pescado | Empaque en lata de formato grande, colocar y empujar latas, retoques a mano | La máquina mete el pescado pero «siempre hay mujeres que tienen que empujar las latas» (CCOO); empaque manual en formatos grandes (AZTI) [H, buscador] | https://www.izquierdadiario.es/Huelgas-tenidas-de-violeta-las-trabajadoras-de-conservas-de-Bizkaia · https://www.azti.es/wp-content/uploads/2020/11/Guia_AZTI_tres_barreras.pdf |
| Conserva (empleo) | — | >2.100 trabajadoras y ~100 hombres en el sector conservero vasco (CCOO) [H, buscador] | https://www.ccoo.es/92b3e86c4f2bbf20ed5a9f7014b97dd9000001.pdf |
| Automoción (proveedores) | Paletizado y traspaso de piezas entre contenedores | Tekniker lo resolvió con visión 3D para Cikautxo: el problema existía y era manual [H, buscador] | https://parke.eus/en/3d-vision-to-help-palletise-parts-with-precision-in-the-automotive-industry/ |
| Electrodomésticos y componentes (Orkli, Copreci, Fagor Ederlan), aeronáutica (ITP Aero, Aernnova), ascensores (Orona), forja, mueble | **Sin datos públicos encontrados** sobre fases manuales concretas | — | [hueco: validar con llamadas] |

## 2. Densidad de robots y adopción

- [H] IFR (nota de prensa 8-4-2026, datos 2024): Europa Occidental **267 robots/10.000 empleados** en manufactura,
  Norteamérica 204, Asia 131: https://ifr.org/ifr-press-releases/robot-density-surges-in-europe-asia-and-americas
- [H] UE-27: 231; Corea 1.220; Alemania 449; España está en el top 20 mundial (buscador):
  https://ifr.org/img/worldrobotics/Foreword_WR_2025_Industrial_Robots.pdf
- [H, buscador, no IFR directo] España **183**/10.000 en 2024, puesto 19 (Visual Capitalist sobre IFR):
  https://www.visualcapitalist.com/ranked-countries-most-industrial-robots-per-worker-2024-v2/ — otras fuentes
  dan 174 o 200 para 2023; **no usar sin abrir el informe IFR**. [I] España queda por debajo de la UE-27 (231).
- [H] Euskadi: **no encontré densidad de robots regional** (ni IFR ni Eustat). [hueco]
- [H] España 2024: 5.160 robots instalados (+2,1 %); automoción 44 %, metal 16,5 % (−17 %), alimentación 12 %
  (+25,3 %) (IFR y AER, Interempresas 13-5-2025):
  https://www.interempresas.net/Robotica/597021-La-robotica-industrial-se-consolida-en-Espana-con-5160-instalaciones-anuales.html
- [H] 40 % de las pymes españolas dice haber incorporado robótica colaborativa (Europa Press, oct. 2025) (buscador):
  https://www.bolsamania.com/noticias_print/economia/economia--el-40-de-las-pymes-incorpora-la-robotica-colaborativa-para-mejorar-la-seguridad-y-la-ergonomia-en-el-trabajo--21091032.html

### Barreras de adopción

1. **Integración más cara que el robot** [H, fuentes de integradores, buscador]: integración del 40-60 % del coste de
   una célula industrial; 50-100 % del precio del hardware en la primera célula; el brazo es ~25-40 % del proyecto.
   https://lanpdt.com/tech-talk-episode-19/ · https://grabarobot.com/blog/robot-integration-cost-guide-2026/
2. **Lotes pequeños y mucha variedad** [H, buscador]: las pymes chocan con alta variedad/bajo volumen, poca
   capacidad de ingeniería y riesgo de caja (A3/automate.org); con lotes <50 piezas y cambios semanales, el
   re-aprendizaje se come la ventaja (regla práctica, no medida):
   https://www.automate.org/robotics/industry-insights/small-manufacturers-are-supposed-to-be-automations-next-big-market-what-s-stopping-them
   · reprogramar en cada cambio es la barrera más citada (revisión de Patsnap):
   https://www.patsnap.com/resources/blog/rd-blog/scaling-cobots-in-high-mix-low-volume-manufacturing-patsnap-eureka/
3. **No hay quien programe ni quien opere** [H]: 80 % de las asociadas a Confebask con dificultades para contratar
   (encuesta bienal, vía Noticias de Navarra, dic. 2024):
   https://www.noticiasdenavarra.com/economia/2024/12/22/rostro-desempleo-euskadi-mujer-mayor-9081852.html
   · ~140.000 personas a atraer esta década para relevo y crecimiento (Confebask, vía Orain/Deia):
   https://orain.eus/es/actualidad/economia/2024/05/20/la-cav-necesitara-aumentar-poblacion-laboral-en-mas-de-400-000-personas-en-tres-decadas-segun-confebask/
   · industria = sector con más puestos difíciles de cubrir (24,6 %); soldadores y chapistas (41,7 % de expertos) y
   mecánicos/ajustadores (33,3 %) (Deia, 2023):
   https://www.deia.eus/economia/2023/08/19/cuatro-puestos-trabajo-cuesta-cubrir-7162792.html
4. **Retorno de inversión**: no encontré cifras fiables de amortización para pymes vascas. [hueco]

## 3. Qué dicen las instituciones vascas sobre robots que aprenden

- [H] **IKASprod** (ELKARTEK, Gobierno Vasco; Tecnalia, Tekniker, Orai, IMH Campus; nota 29-6-2026): robots que
  aprenden de las personas por **voz, gestos y demostración**, sin código, en local y en planta ruidosa;
  sectores: máquina-herramienta, logística, fabricación flexible y **series cortas**, pymes. Lema: «los
  trabajadores dejan de ser programadores y pasan a ser entrenadores»:
  https://www.tecnalia.com/en/news/intelligent-systems-capable-of-learning-directly-from-people
  → [I] Es exactamente nuestra tesis, validada por la propia red BRTA: el jurado la reconocerá. Ellos usan gemelo
  digital y árboles de comportamiento; nosotros, imitación directa con un brazo de 300 €.
- [H] **Tekniker · Hartu** (Horizon Europe, jul. 2026): manipulación flexible con IA y visión en agroalimentación e
  intralogística, aún antes de implantación en planta (buscador):
  https://www.interempresas.net/Robotica/651522-Hartu-inteligencia-vision-artificial-optimizar-manipulacion-robotica-Industria-50.html
- [H] **Primus Robotics** (Fagor Arrasate + Funditec, 24-3-2026, Arrasate): humanoide industrial europeo, 200
  unidades/año al inicio, prototipo a finales de 2027, para «tareas pesadas, repetitivas y peligrosas»:
  https://forbes.es/economia/895211/fagor-arrasate-y-funditec-crean-primus-robotics-para-fabricar-robots-humanoides-industriales/
- [H] **Zedarriak**, 9.º informe «La próxima revolución: IA con cuerpo»: Euskadi como laboratorio europeo de robótica
  «humanista»; valor en integración y *know-how*, renting y pago por uso para pymes; faltan integradores con
  experiencia sectorial (alimentación, etc.) (buscador; no abrí el original):
  https://ecosistemastartup.com/zedarriak-impulsa-a-euskadi-como-polo-de-robotica-humanista/
- [H] **SPRI · Renove Smart Industry**: subvención a pymes industriales para equipos 4.0, con robótica colaborativa
  como partida elegible (convocatoria 2025 cerrada el 7-11-2025; bases 2026 en el BOPV) (buscador):
  https://www.cecobi.es/wp-content/uploads/2025/07/CIRCULAR-89-RENOVE-SMART-INDUSTRY-2025.pdf
  · https://www.euskadi.eus/web01-bopv/es/bopv2/datos/2026/03/2600935a.epub
- [H] **BDIH** (Basque Digital Innovation Hub): nodo de robótica flexible y colaborativa, coordinado por Tecnalia;
  Tekniker ofrece célula de montaje flexible y *pick & place*; Ideko, célula de mecanizado robotizado (buscador):
  https://www.spri.eus/en/blog/digitalisation-news/4-0-solutions-in-robotics-for-manufacturing-and-assembly/
- [H] **BAIC**: adopción de IA en Euskadi +42 % en un año (2.º diagnóstico BAIC, 2025) (buscador):
  https://www.euskadi.eus/gobierno-vasco/-/noticia/2025/la-adopcion-inteligencia-artificial-euskadi-crece-42-ano-segundo-diagnostico-baic/
  No encontré nada de BAIC específico sobre IA física. [hueco]

## 4. Pilotos reales 2025-2026 de robots que aprenden por demostración

- [H] **BMW Leipzig + Hexagon AEON**: humanoide para baterías y componentes; ~20 demostraciones teleoperadas para
  entrenar; piloto desde dic. 2025, piloto permanente previsto en verano de 2026 (prensa, cifra de la empresa):
  https://www.bmwblog.com/2026/03/03/bmw-hexagon-aeon-humanoid-robot-leipzig-pilot/
- [H] **Universal Robots + Scale AI · UR AI Trainer** (GTC, marzo 2026): maestro-esclavo (UR3e/UR7e) que graba
  demostraciones para entrenar VLA en el mismo hardware de producción; demo de empaquetado de móviles; solo EE. UU.:
  https://www.nasdaq.com/press-release/universal-robots-and-scale-ai-launch-imitation-learning-system-accelerate-ai-model
  → [I] Es el mismo flujo que LeRobot con SO-101 (líder-seguidor), a 1/100 del precio. Argumento fuerte.
- [H] Validación en fábrica de control híbrido con imitación para inserción de cables y soldadura (arXiv 2604.22235;
  no comprobé afiliación ni país): https://www.alphaxiv.org/abs/2604.22235.md

## 5. Conclusión

[I] El problema reconocible por un jurado vasco no es «no hay robots», sino **«el robot no compensa porque cada
referencia nueva cuesta una integración»** en pymes de series cortas (mecanizado, componentes, alimentación),
justo cuando faltan operarios. IKASprod, UR AI Trainer y BMW confirman que la industria apuesta por enseñar con
demostración y voz. Honestidad obligatoria: con SO-101, «enseñar en minutos» = grabar 30-50 demos (~20-30 min) +
entrenar (horas de GPU); lo que sí es inmediato es **cambiar de tarea con la voz entre tareas ya enseñadas**.

### Tres escenas de demo con SO-101

| # | Escena | Órdenes al VLA | Necesidad | Riesgo |
|---|---|---|---|---|
| 1 | **Carga de máquina multirreferencia**: bandeja de piezas en bruto (2-3 referencias impresas en 3D, gruesas) → útil/plantilla de una «máquina» maqueta → pieza acabada a la caja | «Carga la referencia A» / «cambia a la B» / «saca la pieza y déjala en la caja de terminadas» | Lotes cortos donde no compensa integrar; falta de operarios de mecanizado; BIEMH mostró justo esto con cobots | Encaje en el útil necesita ±1 cm con chaflanes generosos; parecer «pick and place» si no se ve el cambio de referencia |
| 2 | **Estuche mixto de conservas** (pequeña conservera): latas grandes y tarros en una mesa → caja regalo según pedido | «Prepara un estuche con dos de bonito y una de anchoa» / «ahora solo bonito» | Empaque y retoque manual feminizado y mal pagado; pedidos variados de campaña (Navidad) que no justifican una encajadora | Hay que leer etiquetas (colores/formas claras); latas reales pesan: usar vacías o tarros ligeros |
| 3 | **Kit de montaje por pedido** en línea de bajo volumen (componentes de electrodoméstico o ascensor): cajones con 4-5 piezas gruesas → bandeja del kit | «Kit para el modelo 2» / «añade otra junta» | Preparar kits es tiempo de operario sin valor; cambia con cada modelo | Se solapa con la candidata A del diagnóstico (pañol); sin datos de Orkli/Orona |

**Top 1 [R]: escena 1, carga de máquina multirreferencia.** Es el sector más vasco (máquina-herramienta, 8,1 % del
empleo manufacturero, BIEMH en Bilbao), el dolor tiene cifra (integración 40-60 % del coste de la célula) y la voz
hace visible el valor del VLA: misma célula, otra referencia, sin integrador. Frase de pitch: «una referencia
nueva no debería costar una integración». Mostrar en vivo el cambio A→B por voz y, en vídeo acelerado, que
enseñar la referencia C costó N demos y M minutos (medido por nosotros).
Alternativa con más emoción y menos tópico: escena 2 (conservas), si se valida con una conservera.

## 6. Contactos posibles para validar (organizaciones públicas)

- Clústeres: **AFM Cluster** (máquina-herramienta, organiza BIEMH), **ACICAE** (automoción), **HEGAN** (aeronáutica),
  **Clúster de Alimentación de Euskadi**, **Habic** (mueble), **SIEA/GAIA** (electrónica).
- Centros: **IMH Campus** (Elgoibar, socio de IKASprod, FP de mecanizado), **Tecnalia** y **Tekniker** (IKASprod,
  BDIH), **Ideko** (Elgoibar), **AZTI** (conservas), **BAIC**, **BRTA**.
- FP: **Tknika**, **Mondragon Unibertsitatea**, **Centro San Viator** o **Don Bosco** (Errenteria) con ciclos de
  mecatrónica/mecanizado (verificar oferta antes de llamar).
- Empresas: **Fagor Arrasate / Primus Robotics**, **Orkli**, **Copreci**, **Orona**, **ITP Aero**, **Aernnova**,
  **Gestamp**, **CIE Automotive**, **Batz**; conserveras de Bermeo, Ondarroa o Getaria.
- Instituciones: **SPRI** (Renove Smart Industry), **Confebask**, **Orkestra** (Informe de Competitividad 2025:
  https://www.orkestra.deusto.es/images/investigacion/publicaciones/informes/informe-competitividad-pais-vasco/250068-informe-competitividad-pais-vasco-2025.pdf ).

## 7. Huecos y cifras a verificar antes del pitch

- Densidad de robots de España 2024 (183 sin confirmar en IFR) y de Euskadi (no existe dato encontrado).
- Fases manuales concretas en Orkli, Copreci, Orona, ITP Aero, Aernnova: solo por llamadas.
- Porcentajes de integración: vienen de integradores; usar como «según integradores».
- Zedarriak y Eustat: abrir los originales.
