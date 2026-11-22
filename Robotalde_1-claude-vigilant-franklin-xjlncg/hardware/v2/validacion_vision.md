# LeWelder v2 · Validación de la visión con el CAD (antes de imprimir)

Tarea 1 del plan v2 · 16-11-2026, repetida con la mesa de montaje nueva (base en (280, 35) con giro 0, zona libre a
la izquierda del robot en x 110-160, y 160-230; soporte de la antorcha en (180, −180)). Herramienta:
`herramientas/validar_vision_cad.py` (tablas completas en `salidas/estereo/validacion_tablas_720p_fov78.md` y
`..._1080p_fov78.md`, imágenes `salidas/estereo/cad_*.png`).

## Veredicto

- **El CAD vale tal cual para la visión**: no hace falta mover ni agrandar ninguna pegatina. Los ArUco 30, 40 y 41 se
  detectan siempre que se ven a menos de ~75° de canto, y la junta se reconoce en 76/76 casos a 1080p (T y esquina
  con la base girada de −60° a 180°, y chapa tumbada en las esquinas y el centro de la zona libre nueva).
- **Nuevas poses de las webcams, ya en el contrato (`CAMARAS_ESTEREO`)**: 450 mm de alto, 45° de la vertical, a ±25°
  del eje X de la mesa, mirando a (240, 70, 16), entre la base y la zona libre. Ven la base y todo el barrido de la
  zona libre con un 5 % de margen con solo 53-54° de FOV horizontal (cualquier webcam de 60° o más vale).
- **Webcams a 1080p**: la móvil sale con 0,3 mm y 0,25° (máx. 0,64°), siempre vista por las dos cámaras. A 720p
  también funciona, pero con la junta girada 90° la móvil a veces solo la ve bien una cámara.

## Cómo se ha validado

- **Geometría real**: las mallas STL de `cad/stl/BASE-V2.STL` y `MOVIL-V2.STL` (ranura, tope interior, aleta,
  chaflanes, agujeros de imanes) con las pegatinas de 35 mm (25 mm de negro) en el fondo de sus rebajes de
  35,4 × 35,4 × 0,3. Mapeo STL → marco de la pieza: base (X, Y, Z)_stl = (X_b + 100, Z_b + 6, 40 − Y_b); móvil
  (X, Y, Z)_stl = (X_m + 70, Z_m, 21 − Y_m). Comprobado contra el STL: hueco del 30 centrado en (82, −20); huecos del
  40 y el 41 en X = 35, Z = 20; aleta en X −55..−15, Z 17,5..22,5, sobresale 18; tope en Y 37..40, Z 0..3; ranura en
  Y −0,5..6,5, 2 de profundidad.
- **Oclusión real**: z-buffer por triángulo (la chapa de pie, la aleta y el tope tapan lo que tienen detrás). El robot
  no se pinta.
- **Cámaras**: webcam de 78° de FOV horizontal, a 1280×720 y 1920×1080, exposición baja (la del seguimiento del LED),
  ruido y desenfoque; 4 realizaciones de ruido por escena.
- **Detección**: el detector de `lewelder/estereo.py` (OpenCV, perímetro mínimo 0,03 y refinado de esquinas por
  bordes) y el `SeguidorEstereo` completo para reconocer la junta.
- **Escenas**: T y esquina con la base en `POSICION_BASE` girada 0°, ±30°, ±60°, 90° y 180°; chapa tumbada (aleta
  arriba) con su centro en las cuatro esquinas y el centro de `ZONA_LIBRE`, con giros de −60° a 60°. Precisión: T y
  esquina rectas y volcadas 8°, giros 0° y ±30°.

## Resultados

Detección = veces que OpenCV encuentra el marcador cuando se ve (sin tapar y de cara a la cámara). "Anteriores" son
las poses del contrato con la mesa antigua (500 mm, ±35°, objetivo (230, −80)).

| Cámaras | Resolución | ArUco 30 | ArUco 40 | ArUco 41 | Juntas reconocidas | Pose de la móvil (media / máx) | Estado con volcadas 8° | FOV mínimo A / B |
|---|---|---|---|---|---|---|---|---|
| **Nuevas (contrato)** | 720p | 144/144 | 60/64 | 72/76 | 74/76 | 1,0 mm / 1,0° (máx 2,9°) | 23/24 | 54° / 53° |
| **Nuevas (contrato)** | **1080p** | 144/144 | 64/64 | 72/72 | **76/76** | **0,3 mm / 0,25° (máx 0,64°)** | **24/24** | 54° / 53° |
| Anteriores | 1080p | 140/140 | 65/72 | 65/72 | 76/76 | 0,4 mm / 0,48° (máx 1,2°) | 24/24 | 60° / 73° |

Con las poses nuevas, los únicos fallos de detección (a 720p) son marcadores vistos a 76-82° de canto (la base girada
60-90° deja la cara de la móvil casi de perfil para una cámara); la otra cámara lo ve. Las anteriores aún reconocen
las juntas, pero miran a donde ya no hay nada (el objetivo queda en la zona del soporte de la antorcha), necesitan
73° de FOV en la cámara B y ven la móvil con una sola cámara en 8 de 24 casos.

Cómo se ve cada ArUco con las poses nuevas a 1080p (lado más corto del cuadro negro y ángulo con la normal):

| Escena | Cámara A | Cámara B |
|---|---|---|
| 30, base (giro 0) | 42 px, 42° | 42 px, 39° |
| 41, móvil en T (giro 0) | 35 px, 53° | 35 px, 53° |
| 41, móvil en esquina (giro 0) | 35 px, 50° | 35 px, 50° |
| 40, junta girada 180° (se ve en vez del 41) | 35 px, 52° | 35 px, 55° |
| 40, móvil tumbada en la zona libre | 25-31 px, 51-53° | 31-40 px, 46-48° |

## Respuestas

- **¿Se ven y se detectan 30, 40 y 41 en T y esquina desde las dos webcams?** Sí: con la junta en giro 0 las dos
  cámaras ven el 30 (a ~40°) y el 41 (a 50-53°); con la junta girada 90-180° ven el 40 de la cara de la aleta. La
  chapa de pie en T tapa el 30 en una cámara con la base girada 90° o 180°: la otra lo ve y, además, la base no se
  mueve y su pose se guarda.
- **¿Y en la zona libre, tumbada?** Sí, en las cuatro esquinas y el centro de la zona libre nueva, desde las dos
  cámaras (el 40 a 46-53°). Ojo: en el evento el brazo del SO-101 puede tapar la zona libre (está junto al robot);
  la chapa tumbada solo hace falta para saber que la junta aún no está montada.
- **Oclusiones del CAD**: ni la aleta ni el tope tapan ningún ArUco desde las webcams. El rebaje de 0,3 mm no molesta.
- **Si el 41 no se ve** (mano, LED encima, chapa muy girada): la junta se reconoce con la pose de la base (30) más el
  40 o el 41 de una sola cámara (la distancia se fija suponiendo que la chapa apoya en su guía; tolerancias de
  posición ampliadas), y la última pose buena se conserva mientras la chapa no se mueve.

## Cambios

1. **Contrato (`CAMARAS_ESTEREO`), ya cambiado**:

   | Cámara | Altura | Inclinación | Azimut | Objetivo | Centro óptico (mesa) | Distancia al objetivo | FOV horizontal mínimo |
   |---|---|---|---|---|---|---|---|
   | A | 450 | 45° | −25° | (240, 70, 16) | (633, −113, 450) | 614 | 54° |
   | B | 450 | 45° | +25° | (240, 70, 16) | (633, 253, 450) | 614 | 53° |

   Las dos quedan al otro lado de la base respecto al robot, a 633 mm de él en X (fuera del tablero común: trípode o
   brazo con pinza), separadas 366 mm entre sí. La §7 de `contrato.md` sale de `generar_hardware.py --v2`.
2. **Webcams a 1920×1080**, iguales las dos, con FOV horizontal de 60° o más.
3. **CAD: sin cambios.** No hay sitio para pegatinas más grandes en la móvil (40 mm de alto, con la T 2 mm dentro de la
   ranura) y no hacen falta.
4. **El tablero de calibración** se pone tumbado con el centro de sus esquinas interiores en `POSICION_BASE` (quitando
   la base), columnas hacia +Y de la mesa (`estereo.TABLERO_EN_MESA`).
