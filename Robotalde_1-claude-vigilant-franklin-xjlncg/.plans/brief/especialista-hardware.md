# Especialista de hardware · banco del aprendiz (versión 4) · para Andoni, jueves 19-11-2026

Leyenda: [modelo] = calculado con MuJoCo 3 sobre `assets/so101/so101_new_calib.xml` (barrido de 400 000 posturas,
márgenes de 10° en las articulaciones) · [H] = leído en la fuente · [H·b] = buscador o fuente secundaria ·
[sin verificar] = no confirmado · [estimación] = criterio propio. Plano: [banco-planta.svg](banco-planta.svg).

## 1. Datos del SO-101 que mandan en el diseño

| Dato | Valor | Fuente |
|---|---|---|
| Eje de giro (pan) respecto al origen de la base | 38,8 mm hacia delante de la base; hombro a 116 mm de altura | [modelo] |
| Eslabones | brazo 116 mm (112,6 + 28 desplazado) · antebrazo 135 mm · muñeca → punta de pinza 159 mm | [modelo] |
| Huella de la base | de −70 a +26 mm y ±55 mm respecto al eje de giro | [modelo] |
| **Coger desde arriba en la mesa** (punta a 10-30 mm, pinza ≤ 10° de la vertical) | radio **48-287 mm** desde el eje de giro | [modelo] |
| Ídem con pinza ≤ 20° / ≤ 30° | hasta 323 / 350 mm | [modelo] |
| **Banda útil que uso** (sin rozar la base, con margen) | **120-285 mm** | [estimación sobre modelo] |
| Giro (pan) | ±110° (uso ±90° para dejar margen) | [modelo] |
| Apertura entre dedos en la punta | 0° → 16-19 mm · 29° → 37-59 mm · 46° → 49-80 mm · 100° (máx.) → 71-111 mm (el hueco crece hacia la punta) | [modelo, almohadillas de `medir_dedos.py`] |
| Objeto máximo cómodo | 60-70 mm de ancho; **vaso de 40 y caja de 40 sobrados** | [modelo] |
| Zona de contacto de cada dedo | 17 mm de ancho × 39-40 mm de largo | [modelo, `medir_dedos.py`] |
| Carga | par por articulación 3,35 N·m (límite del modelo). Peso propio del brazo estirado ≈ 0,6 N·m en el hombro; 200 g en la punta añaden 0,63 N·m. Uso ≤ 150 g; los objetos pesan 15-40 g | [modelo] · par real del STS3215 [sin verificar] |

## 2. Plano del banco (versión 4: almacén al fondo)

**Conclusión de alcance.** Para que el técnico sentado no llegue al almacén sin levantarse y el robot sí, el almacén
tiene que quedar a ≥ 0,69 m del hombro del técnico y a ≤ 0,285 m del eje del robot. El alcance cómodo de una persona
sentada es de 35-45 cm y el máximo de 61-76 cm desde el hombro [H·b: guías de ergonomía; la tabla primaria es
Sengupta y Das, *Ergonomics* 43(9), 2000, no leída]. **Con 60 cm de fondo no se puede**: el fondo del almacén queda
a 45-60 cm del borde, dentro del alcance estirando. **Hace falta un fondo de 80 cm** (mínimo 76): pedir mesa de
120 × 80 o juntar dos de 120 × 60 (una detrás, se usa 20 cm de la segunda).

Con la solución de abajo: almacén a **694 mm** del hombro izquierdo (zona máxima, hay que estirarse por encima del
portátil y del brazo: en la práctica, levantarse); plato a **446 mm** (zona cómoda).

Ejes: mesa con origen en la esquina delantera izquierda (x hacia la derecha del técnico, y hacia el fondo).
**Robot: origen en el eje de giro del hombro sobre la mesa = mesa (330, 460)**; mismos ejes. Cotas en mm.

| Elemento | Mesa (x, y, z) | Robot (x, y) | Notas |
|---|---|---|---|
| Eje de giro del SO-101 | (330, 460) | (0, 0) | base girada: pan 0° apunta a 43° (atrás-derecha); así almacén y plato quedan en ±90° de pan |
| Tablero DM 10-15 mm (módulo del aprendiz) | x 150-680, y 200-800 | x −180…350, y −260…340 | robot, almacén, plato y mástil van atornillados aquí: la geometría viaja montada |
| Almacén 250 × 180 (interior), 5 zonas | x 205-455, y 560-740 | x −125…125, y 100…280 | centros de objeto a 120-280 mm del eje (comprobado en 35 puntos) |
| Zonas | Z1-Z3 delante (3 × 83 × 90), Z4-Z5 detrás (2 × 125 × 90) | | solo para el cuaderno; el jurado pone donde quiera |
| Plato-embudo (boca 150 × 100) | centro (520, 320), eje largo girado 54° (perpendicular al radio) | (190, −140), r = 236 | lado izquierdo del portátil, junto a la mano izquierda |
| Portátil 14" boca abajo (≈ 340 × 235) | x 680-1020, y 40-275 | x 350…690, y −420…−185 | 75 mm libres hasta el plato |
| Técnico sentado | pecho (850, −100); hombros (670, −100) y (1030, −100) | (520, −560) | |
| Cámara fija `top` | (660, 680, z 600) mirando a (360, 480, 0) | (330, 220) | 59° hacia abajo, giro hacia delante-izquierda. Ve almacén, plato y robot; la esquina trasera izquierda del portátil y la mano del técnico entran solo por el borde derecho de la imagen (cálculo con 70° × 43° de campo [sin verificar: medir la webcam]) |
| Cámara de muñeca | en la pinza | | soporte oficial de 32 × 32 (apartado 3) |
| Flexo | pinza en (60, 780), cabeza ≥ 60 cm sobre el almacén | (−270, 320) | luz fija, LED (sin infrarrojo); fuera de plano de `top`: comprobar con la imagen |
| Tablet en atril | x 1040-1190, y 60-240 | | de cara al jurado |
| Brazo guía (grabación) | x 1000-1180, y 470-730 | | el teleoperador de pie en el lado derecho; se retira en la demo |
| ESP32 (extra) | (95, 325) | (−235, −135) | junto al plato, cable corto |
| PC del equipo | mesa auxiliar a la derecha | | |

Si el jueves solo hay 60 cm de fondo y no se consigue otra mesa: almacén al lado izquierdo del robot (x 30-280) y
técnico desplazado a la derecha; el almacén queda a ~52-55 cm del hombro, **alcanzable estirando**: decirlo.

## 3. Piezas a imprimir (PLA mate, 0,2 mm, 3 perímetros, 20 % relleno; tiempos para impresora clásica · rápida)

| # | Pieza | Medidas y tolerancias | Orientación | Masa · tiempo | Prio. |
|---|---|---|---|---|---|
| P1 | **Plato-embudo** | boca 150 × 100, fondo 110 × 64, altura 20, paredes a ~45° y 2 mm; borde redondeado. Bajo el centro del fondo: cajeado Ø 10,4 × 3,4 (reed o imán) y ranura 6 × 3 hasta el borde para el cable; 4 patas de fieltro. Fondo de 64 mm: los dedos caben a los lados de la caja de 40 a 12 mm de altura (hueco ≈ 88 mm) | boca arriba, sin soportes | ≈ 45 g · 3,5 h · 1,3 h | 1 |
| P2 | **Vasos de tornillos** × 3 (2 + repuesto) | Ø 40 × 30 exterior, pared 2, fondo **5 mm** con alojamiento de imán Ø 10,2 × 3,2 por debajo (+0,2 de holgura, pegar con cianoacrilato); chaflán de 0,6 en la base. Centro de gravedad bajo: vuelca a > 50° | de pie | 13 g c/u · 2 h los 3 · 50 min | 1 |
| P3 | **Soporte rígido de la cámara `top`** | pie atornillado al tablero (4 tirafondos 4 × 16) + tubo de aluminio 20 × 20 × 600 + cabezal con ángulo fijo de 59° y tornillo 1/4"-20 (o pinza de la webcam). Sin rótulas: no se mueve desde el viernes | pie y cabezal planos | 60 g · 3 h · 1,2 h | 1 |
| P4 | **Soporte de cámara de muñeca** | STL del repositorio `assets/so101/assets/wrist_camera_mount_so101_v1.stl` (módulo UVC de 32 × 32, tuerca hexagonal). Comprobar que la cámara comprada es de 32 × 32 [sin verificar] | según STL | 15 g · 45 min · 20 min | 1 |
| P5 | **Marco bajo del almacén** | interior 250 × 180, listón de 8 × 4 mm (no estorba a los dedos: agarran a 10-15 mm). En 4 esquinas en L con espiga, pegadas sobre cartón pluma gris claro de 5 mm. Zonas con líneas de 1 mm de cinta mate, no en relieve. **Sin alojamientos** | plano | 25 g · 1,5 h · 40 min | 2 |
| P6 | Almohadillas de pinza | 17 × 38 × 1,5 mm en TPU 95A con estrías, o **goma EVA 2 mm / cinta antideslizante** recortada (preferible). Ponerlas antes de grabar y no tocarlas después | plano | 3 g · 20 min | 3 |
| P7 | Caja de memoria impresa (variante) | 95 × 40 × 25 caja con tapa, pared 1,2 | tapa abajo | 20 g · 1 h | 3 |

**Total P1-P5 ≈ 10,7 h clásica / ≈ 4,3 h rápida.** Orden: P4 (corta, prueba la impresora) → P2 → P1 → P3 → P5 →
P6/P7. Lo largo (P1 + P3) de noche si la impresora es clásica. **Sustitutos:** marco y zonas → cinta de pintor mate
sobre cartón pluma; plato → bandeja de cartón pluma con paredes inclinadas pegadas con termofusible; vasos → tapón de
bote Ø 40 con imán pegado; soporte `top` → brazo articulado de cámara con pinza (bloquear rótulas con cinta).

## 4. Caja del módulo de memoria y tercer objeto

- **Cartón**, no impresa: más creíble. Caja kraft o cartulina de 300 g de **95 × 40 × 25** (plantilla impresa,
  3 copias iguales). Dentro, el módulo SO-DIMM (≈ 67,6 × 30) en su bolsa antiestática y una arandela M10 pegada al
  fondo: **≈ 35 g** y centro de gravedad bajo. La pinza la coge por el lado de 40 (abre a ~46°, 50-80 mm).
- Etiqueta mate «SO-DIMM DDR3L 8 GB» en la tapa; sin brillos (la cámara).
- **Antideslizante:** debajo de la caja no (el jurado la deja donde quiera y debe asentarse plana); sí en los dedos
  (P6). Si la caja patina en la mesa al cerrar la pinza, dos puntos de silicona transparente en las esquinas.
- **Variante «nunca vista»:** otra caja de otro color y medida (**90 × 45 × 20**, negra o roja) o una caja comercial
  real de memoria o SSD que entre en 45 mm de ancho; nunca aparece en los episodios.
- **Tercer objeto más creíble:** rollo de **cinta Kapton** (anillo Ø 50-55 × 19, ≈ 40 g [medir]): se usa en todo
  reacondicionado (aislar, fijar cables). Se coge por la pared del anillo. Queda fuera del alcance de la versión 4.

## 5. Electrónica no crítica (todo «extra» en la versión 4)

- **Objeto en el plato:** **reed encapsulado (normalmente abierto) bajo el centro del plato + imán Ø 10 × 3 en el
  fondo del vaso (ya previsto) y otro pegado en el centro del fondo de la caja.** El embudo deja el objeto a ≤ 15 mm
  del centro; alcance del reed con ese imán 10-15 mm [sin verificar: probar el jueves]. Insensible a la luz, una
  entrada digital. Alternativa si falla: célula de carga de 1 kg + HX711 (pesa: además distingue vaso de caja); la
  óptica TCRT5000 se descarta por el flexo.
- **LED «brazo aparcado»:** LED verde 5 mm + 220 Ω en el GPIO 2 del ESP32 (el del LED de la placa).
- **Pulsador de inicio:** pulsador a GPIO 4 con `INPUT_PULLUP`, antirrebote de 30 ms por `millis()`.
- **Conexiones ESP32:** reed GPIO 5 ↔ GND (pull-up interno); pulsador GPIO 4 ↔ GND; LED GPIO 2 → 220 Ω → LED → GND.
- **Firmware:** copia de `firmware/antorcha_robot` (mismo patrón: 115200, una orden por línea, latido de 2 s) con
  identidad `banco`:
  - PC → ESP32: `?` → `{"id":"banco"}` · `L1` / `L0` LED aparcado (el PC repite cada segundo; si calla 2 s, se apaga).
  - ESP32 → PC, al cambiar y cada segundo: `{"t":<ms>,"plato":<0|1>,"inicio":<0|1>}`; el cambio de `plato` a 1 da la
    hora de llegada para el cronómetro de 25 s. Python: reutilizar la autodetección de `lewelder/antorcha.py`.

## 6. El portátil

**Requisitos:** trampilla de memoria con 0-3 tornillos o pestillo; memoria en zócalo SO-DIMM bajo la trampilla (no
bajo el teclado); SSD para arrancar en < 30 s; ver la memoria en la BIOS (más rápido que el sistema); síntoma
visible: con 2-4 GB «va lento» y la BIOS enseña la cifra vieja, o sin módulo no da imagen (ensayar en el equipo).

| Modelo | Acceso a la memoria | Estado |
|---|---|---|
| HP EliteBook 8460p | pestillo, sin tornillos; iFixit «fácil, 10 min» | [H] (finalista-f1) |
| HP EliteBook 840 G1 | pestillo deslizante, sin tornillos; quitar la batería con dos pestillos; iFixit «moderado, 8 min» | [H] ifixit.com/Guide/50551 |
| HP ProBook 640 G1 | la tapa se desliza y se levanta (sin tornillos en la guía); iFixit «moderado, 25 min» | [H] ifixit.com/Guide/200986 |
| Lenovo ThinkPad T430 | trampilla de memoria con 2 tornillos; un zócalo ahí y otro bajo el teclado (usar el de la trampilla) | [H·b] globalnerdy.com, manual HMM de Lenovo |
| HP EliteBook 8470p / 8570p | misma familia que el 8460p, pestillo | [sin verificar] |
| HP EliteBook 840 G2 / 820 G2 | misma tapa de servicio que el G1 | [sin verificar] |

Descartados: Dell Latitude E6530 (tapa de 4 tornillos, iFixit [H]) y ThinkPad T480 (6 tornillos y clips que se
rompen [H]). **Precio** de segunda mano: 60-150 € según modelo y SSD [estimación sin verificar]. **Dónde el
jueves en Bilbao:** Wallapop (filtro Bilbao, entrega en mano el mismo día), CeX y Cash Converters de Bilbao, tiendas
de reacondicionado; y pedirlo prestado en la cita (Reciclanet, tiendas de Bizkaia Repara) [sin verificar existencias].
**Memoria:** SO-DIMM DDR3L-1600 de 204 contactos (vale en 840 G1, T430 y, a 1,35/1,5 V, en el 8460p [sin verificar
por modelo]); dos módulos: uno de 2-4 GB (el «viejo») y uno de 8 GB (el «nuevo»), 5-15 € usados [estimación].
**Plan si no se consigue:** cualquier portátil del equipo con trampilla; si ninguno, un mini PC con SO-DIMM; en último
caso la demo puntuada (5 intentos) no lo necesita y el arranque va en el vídeo.

## 7. Lista de la compra del jueves y lista para el evento

| Compra | Cant. | ≈ € |
|---|---|---|
| Portátil de empresa del apartado 6 (+ cargador) | 1 | 60-150 |
| SO-DIMM DDR3L (2-4 GB y 8 GB) | 2 | 10-25 |
| Tablero DM 10-15 mm cortado a 530 × 600 (bricolaje con corte) | 1 | 8 |
| Tubo de aluminio 20 × 20 × 1000 | 1 | 6 |
| Sargentos | 2-3 | 12 |
| Cartón pluma 5 mm A3 gris o blanco | 2 | 6 |
| Cartulina kraft 300 g A4 + cinta de pintor mate 10 mm | 5 + 1 | 6 |
| Goma EVA 2 mm o cinta antideslizante | 1 | 3 |
| Tirafondos 4 × 16, tornillo 1/4"-20, fieltros adhesivos | — | 5 |
| Cianoacrilato y termofusible | — | 5 |
| (extra) reed encapsulado × 3, LED, 220 Ω, pulsador, ESP32 si no hay | — | 10 |

**Llevar al evento:** módulo del aprendiz montado (tablero + robot + almacén + plato + mástil), los dos SO-101 y sus
fuentes, 2 cámaras y cables USB de 3 m, hub USB alimentado, flexo, portátil a reparar con los dos módulos y su
cargador, destornillador PH0/PH1, pulsera antiestática, 3 vasos + 3 cajas + caja «nunca vista», sargentos, regleta,
cinta de pintor, cianoacrilato, repuestos impresos (vaso, soporte de muñeca), metro y calibre, plantillas en papel
del almacén y del plato (para recolocar si se desmonta), ESP32 montado (extra).

## 8. Orden de trabajo del jueves (Andoni)

| Hora | Tarea |
|---|---|
| 08:30 | Lanzar P4 (muñeca) y medir la cámara de 32 × 32 y la webcam (campo de visión: foto a una regla a 50 cm) |
| 09:15 | Lanzar P2 (3 vasos). Encargar el corte del DM; comprar aluminio, sargentos y cartón pluma |
| 10:00-12:00 | Cita del equipo (si va Andoni, preguntar por el portátil prestado); Wallapop/tiendas: portátil y memorias |
| 12:00 | Lanzar P1 (plato). Pegar imanes en los vasos. Cortar y plegar 3 cajas de cartón |
| 13:30 | Comer. Probar el portátil: trampilla, memoria vieja/nueva, BIOS y arranque cronometrados |
| 14:30 | Lanzar P3 (soporte `top`). Montar el tablero: plantilla 1:1 del plano, robot, almacén, plato |
| 17:30 | Lanzar P5 (marco). Montar mástil y cámara; foto de `top` y ajustar el ángulo con el criterio del apartado 2 |
| 19:00 | Almohadillas (P6) y caja «nunca vista»; (extra) reed + ESP32 y firmware `banco` |
| 20:30 | Comprobaciones físicas y foto del banco para el equipo; empaquetar con la lista del apartado 7 |
| Noche | P7 y repuestos si sobra impresora |

**Tres comprobaciones sin robot:**
1. **Alcance con regla:** desde el eje de giro marcado en el tablero, todas las esquinas interiores del almacén
   menos 20 mm y el fondo del plato a 120-285 mm; y una persona sentada a la mesa **no llega** al almacén sin
   levantarse (que lo intenten dos personas de distinta altura).
2. **Pinza con la mano:** abrir la pinza del SO-101 apagado a mano (~46°) y meterla en el plato con la caja de 40 en
   el fondo: los dedos bajan hasta 12 mm sin tocar las paredes; el vaso con imán no vuelca al inclinarlo 45°.
3. **Imagen de `top`:** foto desde la cámara montada con los objetos en las 5 zonas, en el plato y con la mano del
   técnico junto al plato: almacén y plato enteros, portátil y mano solo en el borde, sin reflejos del flexo.
