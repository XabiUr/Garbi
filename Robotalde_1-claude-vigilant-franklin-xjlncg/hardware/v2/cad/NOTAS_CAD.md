# LeWelder v2 · Notas del CAD (SolidWorks 2028)

Modelado a partir de `brief_solidworks.md` (16-11-2026). Archivos `.SLDPRT` en esta carpeta y un STL por pieza en
`stl/`.

## Piezas

| Archivo | Volumen (mm³) | Comprobación |
|---|---|---|
| BASE-V2 | 92 115 | Ranura, tope, 6 imanes, patas, ArUco y chaflanes: cada corte coincide con su volumen teórico |
| MOVIL-V2 | 36 145 | Aleta, 3 imanes Ø4,3 × 4,3, ArUco 40/41, marca ▼ |
| ANTORCHA-ROBOT-V2 (+ `_mitad-A/B.stl`) | 18 716 | Mitad A = lado −Y, mitad B = lado +Y; 9 358 cada una |
| SOPORTE-ANTORCHA-V2 | 45 392 | Tubo Ø24/Ø14,6, plano interior en +X, entrada Ø22, 4 avellanados Ø4,5 → Ø9 |
| PRUEBA-IMANES-V2 | ≈ 17 300 | Agujeros Ø10,2/10,4/10,6 × 3,2 y Ø4,1/4,3/4,5 × 4,3 con su medida grabada; ranura 7 × 2 con chaflán |

## Cambios respecto al brief (decididos con Andoni)

1. **Tope de la esquina dentro de la base** (el del brief quedaba en el aire fuera del canto y no se podía imprimir sin
   soportes). Ahora: tope en **Y +37 a +40**, Z 0 a +3; chapa móvil en esquina en **Y +31 a +37**; imanes de la línea
   de esquina en **Y = +34**; **cordón de la esquina en Y = +31** (antes +34).
   → En `lewelder/contrato.py`: `Y_CORDON[ESQUINA] = ANCHO_BASE/2 - TOPE (3) - GROSOR_CHAPA = 31`.
2. **Antorcha de 95 mm sin acortar.** Con la punta apoyada en el fondo del tubo (Z = 6 sobre el tablero), el centro
   del mango queda a **Z ≈ 116** (6 + 95 + 15), no a 60.
   → En el contrato: `SOPORTE_ANTORCHA["z_mango"] = 116`.
3. **Chaveta a lo largo de todo el cilindro** (Z 0 a 95, plano a 6,0 mm del eje). En el brief iba de Z 60 a 95 y
   quedaba fuera del tubo. El plano del tubo está a 6,3 mm del eje: 0,3 mm de holgura.
4. **Salida de los hilos del LED** por la cara −X del mango, a Z = 110 (Ø4).
5. **Pasadores Ø3** (agujeros Ø3,2): uno en el cuerpo en (X −4,5, Z 50), de 8 mm de largo, y otro en el mango en
   (X +6, Z 115), de 10 mm.
6. **Pieza de prueba de 60 × 40 × 8** (no 60 × 30), para grabar el diámetro junto a cada agujero.

## Avisos

- En la punta de la antorcha (Ø6) con el agujero del LED (Ø5,2) solo quedan 0,4 mm de pared, y la pestaña del LED de
  5 mm mide unos 5,8 mm. Puede salir frágil o que el LED no entre hasta el fondo: revisar al imprimir.
- Los STL salen con Y hacia arriba (convenio de SolidWorks). En el laminador, apoyar cada pieza sobre la cara que dice
  su propiedad "Imprimir".
- No hay material PLA en la biblioteca de SolidWorks: las piezas llevan ABS solo para verlas. Masa en PLA ≈ volumen ×
  1,24 g/cm³ (la base pesa unos 114 g con el 100 % de relleno).
- La pinza de tubo para la webcam no se ha modelado (no se pidió).
