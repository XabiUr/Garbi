# Necesidad real · diagnóstico de producto (18-11-2026)

Método: `product-lens` modo 1 de ecc (aplicado a mano), sobre tres investigaciones con fuentes (método
`research-ops`):

- [investigacion-mantenimiento-euskadi.md](investigacion-mantenimiento-euskadi.md)
- [investigacion-otros-sectores.md](investigacion-otros-sectores.md)
- [como-ganan-con-necesidad-real.md](como-ganan-con-necesidad-real.md)

Marcas: [H] hecho con fuente (ver informes), [I] inferencia, [R] recomendación. **Las cifras marcadas «sin
verificar» en los informes no van al pitch hasta pasar `santa-method`** (dos revisores independientes).

## Lo que dice la investigación en tres frases

1. **Relevo tal cual no existe en la realidad** [H]: en planta, los módulos los cambia una persona con la máquina
   consignada; no hay robots que lo hagan. El dolor de fondo (paradas, falta de técnicos) es real, pero el gesto no.
2. **Ningún proyecto ganador validó la necesidad con usuarios** [H, 37 fichas]: ganan con una escena de 5 s y una
   cifra. Validarla de verdad (llamadas, una cita, una carta) es un hueco barato que nos distingue [I].
3. **Se penaliza la necesidad falsa** [H]: cubos de colores disfrazados, cifras de mercado genéricas, un robot que
   hace lo que una persona hace mejor y no compararse con lo que cuesta la alternativa actual.

## Las tres candidatas con necesidad real

### A · Pañol de mantenimiento: el robot prepara el kit de la orden de trabajo (Relevo reencuadrado)

| Pregunta | Respuesta |
|---|---|
| Para quién | El técnico de mantenimiento de turno en una planta (máquina-herramienta, automoción) |
| Dolor | Una hora de parada en una gran planta de automoción: 2,3 M$ (Siemens 2024) [H]. El técnico hace trabajo directo solo el 18-30 % del turno [H]; ~23 % del tiempo buscando piezas [sin verificar]. Euskadi: ~11.000 puestos de relevo solo en máquina-herramienta hasta 2036 [H] |
| Qué hacen hoy | El técnico va al almacén, busca y vuelve; o armarios dispensadores (vending industrial) |
| Por qué ahora | Relevo generacional: no hay técnicos; los VLA permiten pedir kits nuevos con una frase, sin programar |
| Demo | Estantería con 4-6 repuestos con asa; «kit para cambiar el filtro de la prensa 2» → el robot llena la bandeja del kit |
| VLA visible | Bueno: la misma estantería, kits distintos según la frase |
| Riesgos | Parecido a «pásame herramientas» (MSN ganó con la tercera mano) [I]; el robot hace algo que una persona hace bien; final poco espectacular (una bandeja llena) |

### B · Triaje de baterías: el robot saca lo que lleva batería antes de la trituradora

| Pregunta | Respuesta |
|---|---|
| Para quién | El operario de la cinta de entrada de una planta de reciclaje de aparatos eléctricos (RAEE) |
| Dolor | Incendios en plantas de residuos por baterías de litio: >10.000 al año en Alemania, ~80 % por baterías (Fraunhofer IIS) [H, revisar el alcance de la cifra]; Swisttal, julio de 2025, ≥ 2 M€ [H]; en Francia se duplicaron entre 2019 y 2023 [buscador]; las aseguradoras encarecen o rechazan pólizas [buscador]. España recoge ~47 % de RAEE frente al 65 % legal [buscador] |
| Qué hacen hoy | Triaje manual en cinta (trabajo duro, con riesgo), detectores de rayos X caros [precio sin datos] |
| Por qué ahora | Reglamento UE de Baterías: baterías portátiles extraíbles a partir de febrero de 2027 [H]; más volumen de aparatos con litio |
| Demo | Bandeja revuelta de aparatos (maquetas sin baterías cargadas: mando, ratón, powerbank, pila gruesa, cable, móvil viejo). «Saca todo lo que lleve batería» / «separa los móviles para reutilizar» / «deja los cables» |
| VLA visible | El mejor: la misma escena y criterios distintos según la frase |
| Riesgos | Pre-triaje solo por apariencia (no ve baterías ocultas: se dice abiertamente); variedad de objetos = más episodios; no hay cifras de incendios en España [hueco] |

### C · Acercar objetos de uso diario a una persona con movilidad reducida

| Pregunta | Respuesta |
|---|---|
| Para quién | Persona con movilidad reducida en casa, y quien la cuida |
| Dolor | 4,32 M de personas con discapacidad en España (INE) [H]; 174.406 en lista de espera de dependencia, sept. 2025 [H]; brazos asistivos de 8.600-40.000 $ [orden de magnitud] |
| Qué hacen hoy | Depender de un cuidador o de brazos asistivos caros |
| Demo | «Acércame el mando» / «trae el pastillero» / «guarda las gafas» → siempre a una bandeja fija, nunca a la mano |
| VLA visible | Bueno |
| Riesgos | Seguridad cerca de personas (ya descartamos ManoLibre por esto); dificultad percibida baja; tema muy visto en asistencia |

## Comparación

| Criterio | A · Pañol | B · Baterías | C · Asistencia |
|---|---|---|---|
| Necesidad real y medida | Alta | **Alta, con fecha legal** | Alta |
| El robot hace algo que hoy se hace mal o con riesgo | Media (una persona lo hace bien) | **Alta (trabajo peligroso)** | Alta |
| Escena de 5 s | Media | **Alta («esta pila quema una planta»)** | Alta |
| VLA visible | Buena | **La mejor** | Buena |
| Fiable en vivo (coger y dejar) | Alta | Media-alta (más objetos) | Alta, con riesgo de seguridad |
| Tema fresco | Bajo (parecido a MSN) | **Alto** | Bajo |
| Encaje con el jurado de Bilbao | Industria | Industria + medio ambiente (Impacto Social) | Impacto Social |
| Reutiliza lo hecho | Tablet, voz, personaje | Tablet, voz, personaje, ArUco | Tablet, voz, personaje |

## Recomendación [R]

**B · Triaje de baterías**, con A como alternativa si la validación falla.

- Es la única con dolor medido, una fecha que lo hace urgente (2027) y un trabajo que hoy es peligroso para una
  persona: el robot no sustituye algo que se hace bien, sino algo que quema plantas.
- El VLA se luce justo donde es fuerte: una escena revuelta y criterios distintos según la frase.
- Tema fresco e industrial, y apto tanto para Mejor Proyecto como para Impacto Social.
- Lo que se aprovecha de Relevo: la cadena juez → frase → LLM → orden cerrada → VLA → comprobación y reintento.

**Validación antes del viernes** (método «Mom Test»: preguntar qué pasó la última vez, no qué harían):
llamar a 2-3 plantas de reciclaje de RAEE o gestores de residuos de Bizkaia y Gipuzkoa y a un centro de FP de medio
ambiente; 5 preguntas, 10 minutos; objetivo: una cita con permiso, una cifra local (incendios o conatos al año) y
una foto de la cinta de triaje. Sin validación, se presenta como hipótesis, nunca inventada.

## Ampliación (18-11, noche): producción y automatización industrial

A petición del usuario, dos investigaciones más centradas en producción, no en mantenimiento:
[investigacion-produccion.md](investigacion-produccion.md) e
[investigacion-industria-vasca.md](investigacion-industria-vasca.md).

### La tesis que las une [H + I]

**«Una referencia nueva no debería costar una integración.»** En pymes de series cortas, integrar una célula cuesta
el 40-60 % del total y reprogramar en cada cambio de referencia es la barrera más citada [fuentes de integradores];
para el 50,4 % de las industrias españolas los operarios son el perfil más difícil de cubrir y el 27,3 % no encuentra
ingenieros de automatización (Easyfairs, 2024) [H]. **Aval local:** IKASprod (ELKARTEK; Tecnalia, Tekniker, Orai,
IMH Campus, junio de 2026): robots que aprenden por voz y demostración para series cortas, «los trabajadores dejan de
ser programadores y pasan a ser entrenadores» [H]. En 2026 Siemens, UR con Scale AI (brazo guía + seguidor, como
LeRobot) y mimic con Audi ya enseñan robots por demostración [H].

Matiz honesto [I]: con el SO-101 enseñar una tarea nueva cuesta 30-50 demostraciones y horas de entrenamiento; lo
inmediato es **cambiar por voz entre tareas ya enseñadas**. La tesis se cuenta; en vivo se ve el cambio por voz.

### Candidatas de producción

| | Idea | Para quién | Demo y órdenes del VLA | Riesgos |
|---|---|---|---|---|
| D | **Carga de máquina multirreferencia** (máquina-herramienta, el sector más vasco) | Operario de una pyme de series cortas | Maqueta de máquina con alojamientos en V; «carga la referencia A», «cambia a la B» | El VLA se ve poco (los cobots ya cargan máquinas); parece inserción si el alojamiento no es muy abierto |
| E | **Kits de montaje por variante** (absorbe la A · pañol) | Preparador de kits en montaje de alta variedad | Misma mesa, kits distintos por frase: «kit de la variante A», «la B sin la tapa», «complétalo» | Final poco espectacular (una bandeja llena); parecido a «pásame herramientas» |
| F | **Fin de línea: buenas, malas y retrabajo con un criterio que se cambia hablando** | Inspector de fin de línea | «Las manchadas a retrabajo, las rotas a chatarra»; luego cambiar el criterio con otra frase | El VLA tiene que ver el defecto: solo defectos gruesos y visibles (pieza rota, mancha grande); cifra de acierto humano ~80 % sin verificar |
| G | **Estuche mixto de conservas** | Trabajadoras de empaque en conserveras (> 2.100, CCOO) | «Dos de bonito y una de anchoa» | Recuento y orden menos fiables en vivo; depende de que una conservera lo valide |

Descartadas en producción: secuenciado para automoción (orden y recuento poco fiables), montaje repetitivo por
ergonomía (las lesiones vienen de fuerza y carga, lo que el SO-101 no hace).

### Comparación de finalistas

| Criterio | B · Baterías | E · Kits por variante | F · Fin de línea | D · Carga de máquina |
|---|---|---|---|---|
| Necesidad medida | Alta, con fecha legal (2027) | Alta (operarios, integración) | Media-alta | Alta |
| Industria y producción | Reciclaje industrial | **Producción pura** | **Producción pura** | **Producción, muy vasca** |
| VLA visible (criterio por frase) | La mejor | Buena | **La mejor de producción** | Baja |
| Fiable en vivo | Media-alta | **Alta** | Media (percepción del defecto) | Media (alojamiento) |
| Escena de 5 s | Alta | Media | **Alta** | Media |
| Tema fresco | Alto | Medio | Alto | Medio |
| Aval local | Plantas de RAEE (por validar) | IKASprod, AFM, clústeres | IKASprod | IKASprod, AFM, BIEMH |

### Recomendación actualizada [R]

Si el foco es **producción industrial**, la mejor pareja es **F + E en una sola célula de pyme**: el mismo brazo y la
misma red hacen el kit de la variante pedida y, al final, separan buenas, malas y retrabajo con un criterio que se
cambia hablando. Contado con la tesis de IKASprod. Si hay que elegir una sola: **F** por el VLA y la escena, **E** por
fiabilidad. **B** sigue siendo la necesidad más urgente si se acepta salir de la producción pura.

Siguiente paso propuesto: `council` sobre B, E, F (y la pareja E+F) y las llamadas de validación (AFM, IMH Campus,
Tknika, Tecnalia/Tekniker para IKASprod) deciden.

## Pendiente de decidir con el usuario

1. ¿B, A o C? (o el `council` sobre estas tres antes de decidir).
2. Si B: ¿quién hace las llamadas de validación y cuándo?
3. Después: `santa-method` sobre las cifras del pitch y `interview` para la spec v3.
