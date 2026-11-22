# Lista de material de LeWelder

> Generada por `herramientas/generar_hardware.py` a partir de `lewelder/contrato.py`. Medidas en [contrato.md](contrato.md).

## Imprimir

Masas orientativas (PLA, 3-4 perímetros, 25 % de relleno). Tiempo: ≈ 12 g/h en una impresora clásica, ≈ 30-40 g/h en una rápida.

|  | Pieza | Cantidad | Masa (g) |
|---|---|---|---|
| ☐ | Piezas de prueba: imanes + encaje | 1 | ≈ 10 |
| ☐ | Pieza recta | 2 + 1 repuesto | ≈ 38 c/u |
| ☐ | Pieza en T | 2 + 1 repuesto | ≈ 57 c/u |
| ☐ | Base de anclajes única (~577 × 151) en 4 tramos de 149 × 127 con uniones de cola de milano | 4 tramos | ≈ 84 por tramo |
| ☐ | Antorcha del alumno (2 mitades + gatillo) | 1 + gatillo de repuesto | ≈ 60-90 |
| ☐ | Antorcha del robot + adaptador al dedo fijo | 1 + 1 repuesto | ≈ 20 c/u |
| ☐ | Soporte de cámara de muñeca | 1 | ≈ 15 |
| ☐ | Soporte / pinza de la webcam de seguimiento | 1 | ≈ 30 |
| ☐ | Cuna de reposo de la antorcha (opcional) | 1 | ≈ 20 |

## Comprar o confirmar

|  | Material | Cantidad | Nota |
|---|---|---|---|
| ☐ | IMU BNO055 o BNO085 (fusión en el chip); MPU6050 (GY-521) de respaldo barato | 2 | si no hay en casa |
| ☐ | Cable USB de 3 m (del tipo de tu placa: mini-USB Nano clásico, micro-USB o USB-C) | 2 + 1 |  |
| ☐ | Hub USB con alimentación propia (≥ 4 puertos) | 1 | antorchas + webcams |
| ☐ | Imanes de neodimio 10 × 3 mm (N35+) | 43 → pedir 60 | 4/pieza × 6 piezas + 4/loseta × 4 + prueba |
| ☐ | LED verde 5 mm alta luminosidad (difuso o para lijar) | 10 | 2 en uso + repuestos |
| ☐ | Resistencias 100 Ω y 150 Ω (1/4 W) | 10 de cada |  |
| ☐ | Transistor NPN BC547/2N2222 + resistencia 1 kΩ | 4 | solo si se usa ESP32 |
| ☐ | Pulsador / microinterruptor de palanca (gatillo) | 2 + 1 |  |
| ☐ | Microcontroladores (Nano o ESP32) | 2 + 1 repuesto | uno por antorcha |
| ☐ | Papel adhesivo A4 mate | 5 hojas | marcadores |
| ☐ | Tablero DM/contrachapado 10-15 mm, ≈ 450 × 650 | 1 | base común robot + base de anclajes |
| ☐ | Sargentos | 2 | tablero a la mesa |
| ☐ | Tornillos M4 o tirafondos 4 × 16 avellanados | 12 | losetas |
| ☐ | Tornillos M3 + insertos térmicos M3 | 10 + 10 | antorchas |
| ☐ | Cianoacrilato, bridas, termorretráctil, cable fino, funda espiral | — |  |
| ☐ | PLA mate gris oscuro o negro | 1 kg | total estimado ≈ 828 g |

## Orden de impresión (todo listo antes del jueves 19)

1. **Lun 16, noche — piezas de prueba** (imanes + encaje). Elegir agujero de imán y holgura de topes; imprimir la hoja de marcadores y medir la regla.
2. **Mar 17, mañana — un tramo de la base y una recta.** Validar: la pieza entra sin bailar, no entra girada, imanes, pegatina en su rebaje, medidas con calibre (±0,3). Si algo falla, corregir antes de seguir.
3. **Mar 17, tarde — antorcha del alumno** (lo que más se retrasa: electrónica dentro). Montar gatillo, LED e IMU y probar el firmware.
4. **Mar 17, noche — resto de tramos de la base** (impresiones largas, de noche); probar las uniones entre tramos.
5. **Mié 18 — piezas en T y recta de repuesto; antorcha del robot + adaptador; soportes de cámara.**
6. **Jue 19, mañana — repuestos** (T, antorcha del robot, gatillo) y montaje del tablero con el robot. **Jue 19, tarde — prueba integrada.**
