# Lista de material de LeWelder v2

> Generada por `herramientas/generar_hardware_v2.py` a partir de `lewelder/contrato.py`. Medidas en [contrato.md](contrato.md); modelado en [brief_solidworks.md](brief_solidworks.md). La v1 sigue en [`../lista_material.md`](../lista_material.md).

## Imprimir

Masas orientativas (PLA, 3 perímetros, 20 %). ≈ 12 g/h en una impresora clásica, ≈ 30-40 g/h en una rápida.

|  | Pieza | Cantidad | Masa (g) |
|---|---|---|---|
| ☐ | Pieza de prueba v2: bloque + tramo de chapa | 1 | ≈ 25 |
| ☐ | BASE-V2 | 2 (una por puesto; la 2.ª es repuesto) | ≈ 56 c/u |
| ☐ | MOVIL-V2 (chapa móvil con aleta) | 3 (2 + 1 repuesto) | ≈ 25 c/u |
| ☐ | ANTORCHA-ROBOT-V2 (dos mitades + pasadores Ø3) | 1 + 1 repuesto | ≈ 20 c/u |
| ☐ | SOPORTE-ANTORCHA-V2 | 1 (+1 para el 2.º puesto si graba «coge la antorcha») | ≈ 45 |
| ☐ | Pinza de tubo Ø20 con rosca 1/4" para webcam (solo si el brazo no la trae) | 2 | ≈ 15 c/u |

## Comprar o confirmar

|  | Material | Cantidad | Nota |
|---|---|---|---|
| ☐ | 2.ª webcam **igual que la primera**, 1080p, FOV horizontal ≥ 51,1° | 1 | si la primera no llega, dos nuevas iguales |
| ☐ | Brazo articulado con pinza de mesa o trípode, rosca 1/4", que llegue a 750 mm | 2 | uno por webcam |
| ☐ | Cable alargador USB activo (las webcams quedan a ~0,6 m del robot) | 2 |  |
| ☐ | Imanes Ø10 × 3 N52 | 17 → pedir 20 | 6 por base × 2 + prueba |
| ☐ | Imanes Ø4 × 4 N52 | 14 → pedir 20 | 3 por chapa × 3 + prueba |
| ☐ | Tacos de goma adhesivos Ø10 × 1-2 mm | 12 | patas de la base |
| ☐ | Tapete antideslizante de silicona o goma EVA 2-3 mm, ≈ 300 × 300 | 1 + 1 | zona libre |
| ☐ | Papel adhesivo A4 mate | 3 hojas | marcadores v2 |
| ☐ | LED verde 5 mm alta luminosidad + resistencia 220 Ω | 2 + 2 | antorcha del robot |
| ☐ | Tornillos 4 × 16 avellanados | 4 + 4 | soporte de la antorcha al tablero |
| ☐ | Pasadores Ø3 (o filamento de 1,75 cortado) | 4 | mitades de la antorcha |
| ☐ | Cianoacrilato, rotulador permanente, imán de referencia marcado N o brújula | — | polaridad |
| ☐ | Cinta de carrocero y cinta métrica | — | replanteo de la mesa |

## Orden de impresión (todo listo antes del jueves 19)

1. **Lun 16, noche — pieza de prueba v2** (bloque + tramo de chapa, ~1 h) e imprimir la hoja `aruco/marcadores_v2_a4.pdf` (medir la regla). Pedir imanes Ø4 × 4 si no hay.
2. **Mar 17, mañana — probar con el SO-101 real**: diámetros de los imanes, caída en la ranura desde ±5 mm, polaridad (girada se repele) y agarre de la aleta. Corregir el CAD.
3. **Mar 17, tarde — BASE-V2 n.º 1 y MOVIL-V2 n.º 1** (lo que necesita la grabación de demostraciones). Comprobar con el calibre (sección 11 del contrato) y montar imanes y pegatinas.
4. **Mar 17, noche — ANTORCHA-ROBOT-V2 y SOPORTE-ANTORCHA-V2**; probar que la pinza la coge y la devuelve.
5. **Mié 18 — MOVIL-V2 n.º 2 y 3, BASE-V2 n.º 2** (segundo puesto de grabación) y soportes de las webcams; replantear la mesa (base en (250, 0), zona libre de y 160 a 230 si se acepta la propuesta, soporte) y calibrar el estéreo.
6. **Jue 19, mañana — repuestos** (antorcha, chapa) y **tarde — prueba integrada**: montar T y esquina 10 veces a mano y con el robot, y comprobar que la tablet reconoce la junta.
