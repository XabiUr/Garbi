# Necesidades reales: mantenimiento industrial y la industria vasca

Investigación del 18-11-2026 (método research-ops). Etiquetas: **[H]** hecho con fuente (número entre corchetes, ver §4),
**[I]** inferencia mía, **[R]** recomendación. Las cifras de proveedores se marcan como tales (sirven como orientación).

## 0. Contexto con cifras

- **[H]** Siemens estima que las paradas no planificadas cuestan a las 500 mayores empresas del mundo unos 1,4 billones de
  dólares al año (11 % de sus ingresos), y que una hora parada en una gran planta de automoción cuesta 2,3 M$ [1].
- **[H]** Euskadi: la industria es el 23,7 % del valor añadido (2023), frente al 14,7 % de España y el 18,2 % de la UE-27 [2].
- **[H]** El Gobierno Vasco prevé 625.907 oportunidades de empleo hasta 2036, el 83 % por relevo generacional. En
  máquina-herramienta (575 establecimientos y más de 23.600 empleos directos) prevé unas 15.500, de las que unas 11.000
  son por jubilaciones [3]. Confebask ya avisó en 2022 de que 1 de cada 4 trabajadores vascos se jubilará en una década [4].
- **[H]** Cedefop (LSSI, enero de 2025) señala escasez futura en los oficios manuales cualificados. España es uno de los
  países con escasez en todos los niveles de cualificación [5].
- **[H]** Tiempo productivo del técnico de mantenimiento: lo normal es entre el 18 y el 30 %, y entre el 55 y el 65 % en
  las mejores plantas. Ir a por piezas, buscar herramientas e instrucciones no cuenta como tiempo productivo [6]. Una
  medición atribuida a Ricky Smith (GPAllied) da 29 % de trabajo directo, 23 % obteniendo piezas, 17 % esperando y
  17 % desplazándose [7]. *(La fuente [7] devolvió 403. La cifra viene del extracto del buscador y no está verificada en
  el original.)*
- **[H]** Según EU-OSHA, entre el 10 y el 15 % de los accidentes mortales están ligados a operaciones de mantenimiento [8].

## 1. Necesidades candidatas

| # | Necesidad | Quién la sufre | Dolor cuantificado | Qué hacen hoy | Por qué ahora | Demo con SO-101 | Cómo se ve el VLA |
|---|---|---|---|---|---|---|---|
| A | **Kitting de la orden de trabajo**: preparar repuestos y herramientas antes de la intervención | Oficial electromecánico del turno de noche en una planta de estampación o forja que deja la máquina para ir al pañol | Obtener piezas: 23 % del tiempo [7]. Tiempo productivo típico: 18-30 % [6]. Esperar piezas: 8-12 % del turno, según una revista del sector [9] | Pañolero humano (si lo hay), armarios dispensadores (con un 20 % menos de consumo, según el proveedor [10][11]) o el propio técnico | Relevo generacional [3]. Menos técnicos, así que cada hora de técnico vale más. Las órdenes de trabajo ya salen de un GMAO | Estantería de repuestos de tamaño real con asa (filtro de cartucho, cartucho de fusible NH, relé enchufable en su caja, rodillo, llave) y una bandeja con huecos-embudo. El robot llena la bandeja | "Kit para cambiar el filtro de la prensa 2" frente a "kit de fusibles del cuadro B" frente a "añade una llave del 17". Misma estantería, kits distintos según la frase |
| B | **Carga de herramientas en el almacén de la máquina-herramienta** (cambio de herramienta gastada o preparación de un lote) | Preparador u operario de un taller de mecanizado vasco (Goierri, Debagoiena) | Cambio manual: 45-120 s, frente a 6-12 s automático (cifras de proveedor [12]). Errores de herramienta equivocada causan chatarra [12] | A mano. Los grandes fabricantes ya lo automatizan: DMG MORI vende robots y AMR que llevan hasta 24 herramientas del almacén central a la máquina, con corrección por visión [13] | 15.500 vacantes previstas en máquina-herramienta vasca hasta 2036 [3]. Hay interés por la máquina autónoma (Tecnalia con Ibarmia, Shuton y MYL [14]; Tecnalia en BIEMH 2026 [15]) | Maqueta de almacén de herramientas (4-6 alojamientos en V o embudo) y un carro con conos portaherramientas impresos en 3D con asa (< 200 g) | "Pon la fresa de 10 en la posición 3" frente a "retira la broca gastada al carro" frente a "prepara las herramientas del programa de la brida" |
| C | **Cambio de batería de flotas** (AMR, drones de inspección, herramientas a batería) | Responsable de intralogística o de inspección, y el técnico que hoy cambia baterías entre turnos | Ocado dice que su estación cambia la batería en menos de 60 s y que los robots están en servicio más del 99 % de las horas (cifra de proveedor) [16]. Las bases de dron cambian la batería en menos de 2-3 min (proveedor) [17] | Carga en base o cambio manual entre turnos [18]. Hay cambio robotizado en Ocado y en bases de drones [16][17] | Las flotas de AMR y drones crecen, y una batería que se cambia sola permite trabajar 24 horas sin parar | Maqueta de AMR o dron con hueco de batería guiado por imanes. Batería de réplica con asa. Base de carga | "Cambia la batería del AMR 1" frente a "pon a cargar la gastada" frente a "dame una batería para la atornilladora" |
| D | **Ayudante del técnico senior** ("pásame...", el papel de la enfermera instrumentista) | Técnico de 58 años, con lesiones, que no tiene aprendiz porque nadie lo releva | Relevo generacional [3][4]. No encontré una cifra directa de ergonomía | Aprendiz, o nadie. Tecnalia ya mostró un asistente de voz que responde dudas de mantenimiento con la documentación [15] | Se jubila mucha gente y su conocimiento se pierde [3] | Bandeja de herramientas grandes. El robot entrega en una zona marcada de la mano | "Pásame el polímetro" frente a "deja la llave de vaso en la bandeja" frente a "recoge lo que he usado" |
| E | **Cambio del consumible de proceso** (puntas de electrodo de soldadura, boquillas, filtros) | Mantenimiento de la línea de chapa en automoción (Mercedes Vitoria, proveedores) | Una hora de parada de automoción cuesta 2,3 M$ [1] | **Ya está automatizado** con cambiadores dedicados a los que el robot de soldadura acerca la pinza [19] | Poca novedad | Poco creíble: el cambio de punta real es de precisión y se hace en el propio robot | El VLA aporta poco: es una sola tarea |
| F | **Sustituir un módulo averiado en un cuadro o una máquina** (Relevo) | Electricista de mantenimiento | Del 10 al 15 % de los accidentes mortales está ligado al mantenimiento [8]. El coste de parada se explica en [1] | Lo hace un humano, con bloqueo y consignación de la máquina. **No encontré casos de robots que sustituyan módulos en cuadros o máquinas** | El relevo generacional [3] | Ya diseñado (cartucho con imanes) | "Cambia el módulo de la bomba" frente a "el del ventilador" |

**[I]** A, B y C ya existen hoy a escala industrial (pañoles automáticos y kitting, cargadores de herramientas, cambio de
baterías por robot). Por eso la maqueta se entiende como "la versión pequeña de algo real". En estos tres casos la
interfaz está pensada para el robot (alojamientos, conos, guías), igual que nuestros embudos e imanes. E está
resuelta y F no tiene un precedente robótico.

## 2. Valoración de Relevo

- **[H]/[I]** El problema de fondo existe: parar cuesta mucho [1] y faltan técnicos [3][5]. Pero el gesto de la demo, un
  brazo fijo que mete un repuesto en una máquina averiada, **no se parece a nada que se haga hoy en planta**. En la
  realidad, la sustitución de módulos la hace un humano, con la máquina bloqueada y desconectada [8], y no encontré
  ningún producto que la robotice.
- **[I]** Al jurado le costará reconocer "la versión pequeña de X" porque X no existe. Además, el juez que "avería" la
  minimáquina deja ver que es un montaje. La duda del usuario sobre "encajar componentes" está justificada.
- **[I]** Lo que sí vale de Relevo es la cadena **diagnóstico → repuesto correcto**, porque obliga al VLA a elegir
  entre varias opciones. Esa cadena se conserva entera en A (el kit depende de la orden de trabajo) y en C (el cambio
  de módulo pasa a ser cambio de batería, algo que sí hacen robots [16][17]).
- **[R]** No tirar Relevo: **reencuadrarlo**. Lo que la máquina "pide" pasa a ser una orden de trabajo o una batería
  baja, y el robot prepara el kit o cambia el módulo diseñado para robot. Así se aprovechan el hardware y los imanes
  previstos.

## 3. Mi top 2

**1. A · Kitting de la orden de trabajo ("el pañol que prepara tu orden").**
- Es el dolor mejor cuantificado y con fuentes neutrales [6][7]. Lo sufre una persona concreta (el técnico que pierde
  el 23 % de su tiempo yendo a por piezas) y conecta directamente con el relevo generacional vasco [3].
- Es la tarea en la que el SO-101 es fiable: coger y dejar objetos con asa en huecos-embudo. No hay inserción.
- Es el uso más natural del VLA: misma escena y kits distintos según la frase. Se puede encadenar con la orden del GMAO
  ("orden 4512: cambio de filtro de la prensa 2").
- Se entiende en 5 s: "el robot prepara el kit de repuestos para que el técnico no deje la máquina".
- Riesgo **[I]**: que parezca un simple "coger y dejar". Se compensa con repuestos reales grandes (cartucho de filtro,
  fusible NH, relé) y con varias órdenes distintas en vivo, incluida una que el jurado proponga.

**2. B · Carga de herramientas en el almacén de la máquina-herramienta.**
- Es la identidad vasca: máquina-herramienta, la BIEMH en Bilbao, 15.500 vacantes previstas [3]. Existe la versión
  grande (DMG MORI [13]), así que la maqueta es honesta.
- Es factible con conos impresos con asa y alojamientos en V (± 1 cm). El lenguaje elige herramienta y posición.
- Riesgo **[I]**: el cono en el alojamiento se parece a una inserción. Hay que diseñar alojamientos muy abiertos y
  probarlos pronto.

**[R] Alternativa: A + B en una sola historia**: "Orden 4512 → prepara las herramientas del lote y cárgalas en la
máquina". C (baterías) es el mejor reencuadre si se quiere conservar lo ya diseñado para Relevo.

**Huecos sin cubrir:** no encontré el porcentaje vasco de la máquina-herramienta española ni la cifra de empleo
industrial vasco de 2025. Tampoco hay datos independientes (no de proveedor) sobre el tiempo de cambio de herramienta
ni sobre la mejora del kitting.

## 4. Fuentes

1. Siemens, *The True Cost of Downtime 2024*: https://assets.new.siemens.com/siemens/assets/api/uuid:1b43afb5-2d07-47f7-9eb7-893fe7d0bc59/TCOD-2024_original.pdf
2. Eustat, nota de prensa de julio de 2025 (peso de la industria del 23,7 %, citada a través del buscador): https://es.eustat.eus/elem/ele0024700/not0024790_c.pdf
3. Gobierno Vasco (2026), 625.000 oportunidades de empleo: https://www.euskadi.eus/gobierno-vasco/-/noticia/2026/no-podemos-permitirnos-desaprovechar-talento-euskadi-activa-su-estrategia-625-000-oportunidades-empleo/
4. Deia (2022), Confebask: https://www.deia.eus/economia/2022/10/25/cuatro-trabajadores-jubilara-proxima-decada-6153996.html
5. Cedefop, nota informativa sobre el LSSI (enero de 2025): https://www.cedefop.europa.eu/files/9202_en.pdf
6. Reliable Plant, *Facts about maintenance wrench time*: https://www.reliableplant.com/Read/32402/facts-about-maintenance-wrench-time
7. Equipment World (Ricky Smith, GPAllied): https://www.equipmentworld.com/maintenance-25/ (403; cifra no verificada en el original)
8. EU-OSHA, *Maintenance and OSH, a statistical picture*: https://osha.europa.eu/it/themes/dangerous-substances/practical-tools-dangerous-substances/maintenance-and-occupational-safety-and-health-statistical-picture
9. Reliamag, kitting: https://reliamag.com/?p=265236
10. SupplyPoint, caso SMIMEC (proveedor): https://supplypoint.com/sites/default/files/2026-04/Case-Study-SMIMEC-0326.pdf
11. Kiosk Marketplace, caso Autocrib (proveedor): https://www.kioskmarketplace.com/articles/tool-management-kiosk-makes-missouri-job-shop-more-efficient
12. Proveedor sobre cambiadores automáticos de herramienta: https://simplytechnologies.xyz/what-an-automatic-tool-changer-really-saves-you-in-time-and-cost/
13. DMG MORI, *Tool handling*: https://us.dmgmori.com/products/automation/tool-handling
14. Tecnalia con Ibarmia, Shuton y MYL (2021): https://tecnalia.com/en/news/tecnalia-creates-autonomous-smart-machine-tools-in-collaboration-with-basque-companies-ibarmia-shuton-and-talleres-myl
15. Tecnalia en la BIEMH 2026: https://cms.tecnalia.com/uploads/2026/03/NP-Tecnalia-Bienal-2026.pdf · BIEMH 2024: https://cms.tecnalia.com/uploads/2024/06/NP_TECNALIA_Bienal_2024_JUN2024.pdf
16. Ocado, *Battery swap* (proveedor): https://ocadointelligentautomation.com/systems/battery-swap
17. Unmanned Systems Technology, *Swap not stop*: https://www.unmannedsystemstechnology.com/feature/swap-not-stop-rethinking-continuous-drone-operations/
18. Automated Warehouse, gestión de energía de AMR: https://www.automatedwarehouseonline.com/power-management-for-autonomous-mobile-robots/
19. Patente US5073692A, cambiador automático de puntas de electrodo: https://patents.google.com/patent/US5073692
20. Deia (2023), 1 de cada 4 puestos difíciles de cubrir es industrial: https://www.deia.eus/economia/2023/08/19/cuatro-puestos-trabajo-cuesta-cubrir-7162792.amp.html
