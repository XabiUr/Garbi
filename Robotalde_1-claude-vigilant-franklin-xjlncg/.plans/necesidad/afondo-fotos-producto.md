# A fondo · Estudio de fotos de producto con un SO-101

Fecha: 18-11-2026 · Método research-ops: [H] hecho con fuente (URL), [H·b] solo visto en el extracto del buscador,
[I] inferencia, [R] recomendación.

## Resumen

Un «ayudante de estudio» de sobremesa: la persona pone el objeto en la mesa y dirige por voz («ponlo de lado»,
«enséñame la parte de atrás», «acerca la luz por la izquierda»); el SO-101 recoloca el objeto en una peana, lo gira o
mueve un foco o reflector, y la cámara dispara sola. Al final el juez se lleva por QR las fotos de SU objeto.
- **A favor:** dolor real y medido (fotografiar y publicar es lo más difícil para 1 de cada 3 revendedores), un mercado
  enorme (5,6 M vendedores activos solo en Etsy), el robot es la herramienta tal cual (en un estudio la
  fotografía de producto ya se hace con robots) y el juez participa con un objeto suyo.
- **En contra:** las mesas giratorias baratas y las apps de IA ya resuelven el 80 % del caso «foto frontal más 360°»; el
  VLA solo se justifica en lo que no hacen (poses distintas, objetos que no se tienen de pie, luz dirigida), y los
  objetos del juez son por definición objetos que el modelo no ha visto: el riesgo de fallo es alto si no se acota.
- **Veredicto [R]:** viable solo con un alcance estrecho: objetos rígidos de 20-250 g en una peana en V, el robot
  nunca levanta el objeto más de unos 5 cm sobre una base blanda y una de las órdenes mueve la luz (gesto fiable).

## 1. Necesidad, con fuentes

- [H] El marketplace de Etsy tenía **5,6 M vendedores activos** y 86,5 M compradores activos a 31-12-2025; con Depop,
  8,76 M vendedores ([10-K de Etsy, FY2025](https://www.sec.gov/Archives/edgar/data/1370637/000137063726000019/etsy-20251231.htm)).
- [H·b] Vinted: 1.100 M€ de ingresos y 10.800 M€ de GMV en 2025 (+47 %), un crecimiento impulsado por los miembros
  ([FashionUnited](https://fashionunited.com/news/business/vinted-reaches-1-1-billion-euros-in-revenue-for-2025-accepting-a-strategic-drop-in-profits/2026040971654)).
  Wallapop: 19 M usuarios activos al mes en 2024 [H·b] ([Sacra](https://sacra.com/c/vinted)); es una fuente secundaria.
- [H] Encuesta de Fleek (339 revendedores, 22 países): **un tercio dice que fotografiar y publicar cada artículo es lo más
  difícil del trabajo** ([Retail Tech Innovation Hub](https://retailtechinnovationhub.com/home/2026/9/23/secondhand-clothes-selling-becomes-a-full-time-gig-for-many-with-vinted-the-most-popular-platform)).
- [H] Photoroom (encuesta de abril de 2026 a 1.356 suscriptores de pago): la mediana era de **15 min por imagen** antes de
  usar IA y es de menos de 5 min ahora; un estudio profesional cuesta **25-500 $ por imagen** o 150-300 $/h; los
  usuarios Pro ahorran una mediana de 12 h al mes. El sesgo es claro: es el propio fabricante y solo encuesta a sus
  clientes ([Photoroom](https://www.photoroom.com/industry-trends/product-photography-cost-for-smbs)).
- [H] Impacto en la demanda, con un estudio académico: en Airbnb, las fotos verificadas hechas por fotógrafos
  profesionales subieron la demanda alrededor de un **8,9 %**, unos 3.500 $ al año por alojamiento (Zhang et al.,
  *Management Science* 2022; [tesis de Zhang, CMU](https://www.cmu.edu/tepper/programs/phd/program/assets/dissertations/2019-business-technologies-zhang-dissertation.pdf)).
- [H·b] eBay: los anuncios con mejores fotos tienen un 4,5 % más de probabilidad de venderse (6,8 M anuncios). La cifra
  aparecía en el extracto, pero no en la página que abrí ([eBay Seller Center](https://www.ebay.com/sellercenter/listings/photo-tips)).
  eBay permite hasta 24 fotos por anuncio y pide mostrar ángulos, detalles y defectos [H] (misma URL).
- [H] Baymard: el **56 %** de los usuarios empieza explorando las imágenes al llegar a la ficha y el **42 %** intenta
  deducir el tamaño a partir de ellas ([Baymard](https://baymard.com/blog/ensure-sufficient-image-resolution-and-zoom),
  [Baymard, *in scale*](https://baymard.com/research-articles/human-model)).
- **Quejas concretas:** el tiempo de cada artículo (anécdota: 45 min para fotografiar uno de 12 $ [H·b],
  [flowlister](https://flowlister.com/blog/your-time-is-worth-more-how-to-save-time-as-a-reseller/)), los objetos que
  no se tienen de pie, los reflejos y las sombras, y la falta de una «tercera mano» para sostener el objeto, el reflector
  y el móvil a la vez [I].
- **Persona concreta [I]:** una revendedora de Vinted o Wallapop, o una artesana de Etsy, que publica entre 10 y 30
  artículos a la semana en la mesa del salón con una caja de luz.

## 2. Qué existe y precios

| Solución | Qué hace | Precio |
|---|---|---|
| Caja de luz y mesa giratoria de consumo | Fondo y giro de 360° | De decenas a pocos cientos de € [I] |
| Ortery PhotoCapture 360 (mesa giratoria) | 360° automático, 11 kg | 1.300 $; la 360S, 3.200 $ [H] ([Adorama](https://www.adorama.com/ORPC360.html)) |
| Mesa giratoria Iconasys/Pictomic Silver XL | 360° con software | 1.049-1.399 $ [H·b] ([Pictomic](https://pictomic.com/pages/pictomic-store)) |
| Orbitvu Alphashot (estudio completo) | Luz, giro y disparo automáticos | Compactos desde 270 €/mes en *leasing* y Pro G2 desde 445 €/mes; no publican precio de compra [H] ([PackshotCreator](https://www.packshot-creator.com/en/blog/budget-studio-photo-automatise)); desde 12.450 € [H·b]; 13.000 € de segunda mano [H·b] ([Exapro](https://www.exapro.com/orbitvu-alphashot-xl-pro-v2-234h11-p260824019/)) |
| PhotoRobot (Robotic Arm V8, MultiCam) | Brazo con la cámara y mesa giratoria, 3D en varias filas | Bajo presupuesto [H] ([PhotoRobot](https://www.photorobot.com/robots/robotic-arm)) |
| MRMC Orbital / Bolt Mini | Control de movimiento para grandes volúmenes | Bolt Mini desde 68.000 $ [H·b] ([ProVideo Coalition](https://www.provideocoalition.com/bolt-mini-model-mover-the-smallest-robotic-arm-from-mrmc/)) |
| Apps de IA (Photoroom, remove.bg) | Quitan el fondo y retocan | Photoroom Pro, unos 7,5-13 $/mes según la fuente [H·b] ([Photoroom](https://www.photoroom.com/en/pricing)) |

**Hueco [I]:** todos los robots existentes mueven **la cámara o la mesa**, no **el objeto**. Ninguno cambia la pose del
producto (de pie, de lado, abierto o boca abajo para enseñar la etiqueta), lo sostiene en el aire ni recoloca la luz
cuando se le pide; eso lo hace hoy una persona con las manos o un asistente de fotografía. La IA arregla el fondo, pero
no inventa la cara del objeto que nunca se fotografió (eBay pide mostrar los defectos reales). Un brazo de 3D abierto
cuesta un orden de magnitud menos que un Alphashot. No encontré proyectos de LeRobot o SO-101 dedicados a la fotografía
de producto [H·b], así que la idea es fresca.

## 3. Por qué necesita un VLA

- **Objetos nunca vistos:** cada artículo de segunda mano es distinto. Un cobot programado necesita puntos de agarre por
  referencia, y el VLA generaliza el agarre a partir de la imagen [I].
- **La frase cambia el criterio, no solo el objeto:** «ponlo de pie», «ponlo de lado» o «gíralo para que se vea la
  parte de atrás» exigen el mismo objeto con resultados distintos según la geometría de cada uno. «Acerca la luz por la
  izquierda» cambia el destino de otro objeto (el foco) [I].
- **Colaboración:** la persona corrige sobre la marcha («un poco más», «ahora la otra cara») y el robot actúa sobre lo
  que ve, no sobre una trayectoria grabada [I].
- **Límite honesto [I]:** «enséñame la etiqueta» requiere localizar la etiqueta, algo que un SmolVLA con 150 episodios
  difícilmente generaliza; no debe ir en la demo en vivo. El giro de 360° lo hace mejor una mesa giratoria de 30 €, y
  si se usa, hay que decirlo.

## 4. Demo propuesta

**Escena (60 × 40 cm):** fondo de cartulina blanca curvada, una **peana en V impresa en 3D** (abierta, de unos 90°,
forrada de goma EVA y con un tope) sobre una mesa giratoria motorizada (ESP32 y paso a paso) y un **foco LED en un
brazo de tres posiciones** (izquierda, centro, derecha) con un asa gruesa y un imán en cada posición. Una cámara fija
de fotos (webcam 4K o móvil) y la cámara de muñeca. Una tablet con la galería.

**Útil en la pinza:** dedos alargados de TPU con almohadilla de silicona para coger cuerpos de 20-60 mm sin rayar.

**Objetos:** rígidos, de 20 a 60 mm de grosor y de 30 a 250 g: carteras, fundas de gafas, tazas pequeñas,
figuras, mandos, zapatillas de bebé, botes y cajas. El juez trae su cartera o su funda de gafas; el **móvil del juez,
solo dentro de una funda rugosa** y sin subirlo [R]. Para entrenar, 25-30 objetos de mercadillo variados, con una
lista de «tipos admitidos» a la vista.

**Órdenes (4):**
1. «Ponlo en la peana de frente»: coger de la zona de entrega y dejar en la V.
2. «Ponlo de lado» o «túmbalo»: girar el objeto 90° y dejarlo en la V.
3. «Acerca la luz por la izquierda» o «por la derecha»: coger el asa del foco y llevarlo al imán indicado.
4. «Dale la vuelta para ver la parte de atrás»: la mesa giratoria (determinista) o el brazo girando 180° en la V
   (opcional).
Tras cada orden, el sistema dispara 3 fotos (con la mesa giratoria a 0, 45 y 90°); la persona dice «foto» para elegir.

**Episodios [I]:** unos 50 por orden de manipulación (1 a 3), unos 150 en total con 25-30 objetos y posiciones de
entrega variadas; SmolVLA afinado en la nube. La cadena voz → LLM → orden cerrada ya está hecha.

**Qué hace el juez:** deja su objeto en la bandeja de entrega, da 3 órdenes por voz y dice «foto»; en 90 s ve su
galería en la tablet y escanea un QR para llevárselas. **Momento:** un juez que se lleva en el móvil una foto de
producto de su propia cartera, lista para Wallapop (con el fondo quitado por IA como último paso).

**Plan B con ACT [R]:** un modelo ACT por orden (coger y dejar en la V, girar y dejar, mover el foco), elegidos por el
LLM a partir de la frase, y una mesa giratoria para los ángulos. Si incluso falla la manipulación del objeto ajeno, el
robot solo mueve la luz y la mesa gira: la foto sale igual.

**Riesgos y cómo acotarlos:**
- *Se cae el objeto del juez:* el robot nunca lo sube más de unos 5 cm, todo ocurre sobre EVA, no se aceptan objetos de
  vidrio ni pantallas sin funda y se avisa en la bandeja («tipos admitidos») [R].
- *Objeto fuera de distribución (fino, blando, brillante o pesado):* el LLM con la cámara lo filtra antes («este no lo
  puedo coger, lo pongo yo y muevo la luz») [R].
- *La V no recoge la pose:* una V muy abierta y con tope da una tolerancia de unos ±1 cm, la misma que se marca como
  fiable en el encargo [I].
- *Orden 2 (girar) poco fiable:* es la más difícil. Si no supera el 80 % en los ensayos, se sustituye por «ponlo de
  pie o tumbado» desde la entrega [R].
- *Luz y fondo de la sala:* la caja de luz propia aísla del ambiente [I].

## 5. Variantes y elección

| Variante | Necesidad | Demo con objeto del juez | Encaje con el SO-101 |
|---|---|---|---|
| **Vendedor de segunda mano (Vinted/Wallapop)** | Alta y masiva (1/3 lo cita como lo más difícil) | Perfecta: trae lo que lleva encima | Bueno con objetos rígidos pequeños |
| Artesano de Etsy | Alta; calidad estética | Peor: el juez no lleva artesanía | Bueno (joyas, demasiado pequeñas) |
| Catalogación industrial de repuestos | Real (B2B) | Débil: piezas que no son del juez | Malo: piezas metálicas lisas o pesadas, fuera de lo fiable |

**Elección [R]: vendedor de segunda mano**, con el artesano como segunda historia. Es la única que deja al juez usar
el sistema tal cual con algo suyo y llevarse un resultado útil. La industrial choca con las restricciones del encargo
(piezas metálicas lisas) y vuelve a la «maqueta de aplicación industrial» que el usuario rechazó.

## Notas (1-5)

| Criterio | Nota | Motivo |
|---|---|---|
| Valor real | 3,5 | Dolor medido y masivo, pero la mesa giratoria y la IA ya cubren gran parte del caso |
| VLA necesario | 3 | Lo justifican las poses según la frase y los objetos nuevos; el giro y el fondo no lo necesitan |
| Fiabilidad | 3 | Bien acotado (V, EVA, foco con imanes); los objetos del juez son el riesgo |
| Uso real tal cual | 4 | Un vendedor lo usaría en su mesa tal cual; el SO-101 es la herramienta |
| Momento | 4 | El juez se lleva por QR las fotos de su cartera |

## Fuentes

- https://www.sec.gov/Archives/edgar/data/1370637/000137063726000019/etsy-20251231.htm
- https://fashionunited.com/news/business/vinted-reaches-1-1-billion-euros-in-revenue-for-2025-accepting-a-strategic-drop-in-profits/2026040971654
- https://sacra.com/c/vinted
- https://retailtechinnovationhub.com/home/2026/9/23/secondhand-clothes-selling-becomes-a-full-time-gig-for-many-with-vinted-the-most-popular-platform
- https://www.photoroom.com/industry-trends/product-photography-cost-for-smbs
- https://www.cmu.edu/tepper/programs/phd/program/assets/dissertations/2019-business-technologies-zhang-dissertation.pdf
- https://econpapers.repec.org/RePEc:inm:ormnsc:v:68:y:2022:i:8:p:5644-5666
- https://www.ebay.com/sellercenter/listings/photo-tips
- https://baymard.com/blog/ensure-sufficient-image-resolution-and-zoom · https://baymard.com/research-articles/human-model
- https://flowlister.com/blog/your-time-is-worth-more-how-to-save-time-as-a-reseller/
- https://www.adorama.com/ORPC360.html · https://pictomic.com/pages/pictomic-store
- https://www.packshot-creator.com/en/blog/budget-studio-photo-automatise · https://www.exapro.com/orbitvu-alphashot-xl-pro-v2-234h11-p260824019/
- https://www.photorobot.com/robots/robotic-arm · https://www.provideocoalition.com/bolt-mini-model-mover-the-smallest-robotic-arm-from-mrmc/
- https://www.photoroom.com/en/pricing
