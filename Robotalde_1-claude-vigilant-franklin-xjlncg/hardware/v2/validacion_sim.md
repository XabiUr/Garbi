# Validación en simulación del CAD v2 (antes de imprimir)

Generado por `python -m sim.validar_montaje --n 10` · 16-11-2026 20:25 · MuJoCo con el SO-101 y las mallas de `hardware/v2/cad/stl/` (colisión con primitivas medidas sobre cada malla, ver `sim/piezas_cad.py`). Guion sin ruido salvo que se diga; poses de la chapa al azar en `ZONA_LIBRE`.

## Veredicto

| Pieza | Veredicto | Por qué |
|---|---|---|
| MOVIL-V2 (aleta) | **VALE** | pinza abierta 52.7 mm sobre una aleta de 5.5; la chapa gira como mucho 0.4° en la pinza; montaje 10/10 (T) y 10/10 (esquina) |
| BASE-V2 (ranura y tope) | **NO VALE** | imanes desde ±5 mm y ±5°: T 28/30, esquina 29/30; la chapa se hunde como mucho 0.39 mm en la base |
| SOPORTE-ANTORCHA-V2 | **VALE** | antorcha soltada a ±3 mm y ±3° sobre el tubo: 20/20 dentro; punta a Z 5.98–6.0 (mango a 115.8, contrato 116.0) |
| ANTORCHA-ROBOT-V2 (mango) | **VALE** | la pinza coge el mango de 12.0 mm (abierta 52.7), gira como mucho 0.4° en la pinza; coge, suelda y devuelve 10/10 |
| Brazo SO-101 | **VALE** | choques del brazo con mesa, base o soporte en el guion: ninguno (el detector sí ve un choque provocado: True) |

## Guion por orden

| Orden | Éxito | Duración (s simulados) | Inclinación al soltar / señalar | Nota soldadura | CPU por episodio |
|---|---|---|---|---|---|
| `monta una unión en T` | 10/10 | 21.5 | 9° | — | 1.4 s |
| `monta una unión en esquina` | 10/10 | 19.2 | 15° | — | 1.5 s |
| `señala el cordón` | 10/10 | 19.0 | 80° | — | 2.5 s |
| `coge la antorcha y suelda la junta` | 10/10 | 53.5 | — | 9.93 | 2.4 s |

## Medidas sobre las mallas (mm)

| Pieza | Volumen (mm³) | Ajuste de la colisión | Cotas medidas |
|---|---|---|---|
| BASE-V2 | 91940 | IoU 0.966, sobra 3235 mm³, falta 0 mm³ | ranura_y (-0.5, 6.5), ranura_suelo_z -2.0, tope_y (37.0, 40.0), tope_z 3.0, ranura_x (-75.0, 75.0), tope_x (-75.0, 75.0), chaflan_ranura 1.0, chaflan_tope 0.25 |
| MOVIL-V2 | 35640 | IoU 0.936, sobra 2412 mm³, falta 24 mm³ | aleta_x (-55.5, -14.5), aleta_y (3.0, 21.0), aleta_z (17.0, 23.0), chapa_y (-3.0, 3.0) |
| ANTORCHA-ROBOT-V2 | 18651 | IoU 0.858, sobra 2262 mm³, falta 715 mm³ | mango_z (95.0, 124.5), mango_x (-10.0, 10.0), mango_y (-6.0, 6.0), cuerpo_x (-7.0, 6.0), cuerpo_y (-7.0, 7.0) |
| SOPORTE-ANTORCHA-V2 | 45223 | IoU 0.955, sobra 1613 mm³, falta 507 mm³ | pie_z (0.0, 6.0), eje_hueco_desde_z 6.0, tubo_exterior_x (-12.0, 12.0), tubo_interior_x (-7.5, 6.5), tubo_interior_y (-7.5, 7.5) |

Lo que sobra en la base son los agujeros de los imanes, el hueco del ArUco y las patas (por debajo o por dentro: no tocan nada); en la antorcha, el plano de la chaveta y el cono de la punta.

## Pinza

- Hueco entre almohadillas: abierta (orden del guion, 0.55 rad) 52.7 mm; cerrada del todo 2.0 mm. Aleta 5.5 mm, mango 12.0 mm: entran los dos con más de 10 mm de margen y la pinza los aprieta antes de llegar al tope.
- La aleta se coge con la pinza vertical, a 8 mm de su extremo; la chapa se deja de pie con la pinza casi horizontal y los imanes la enderezan (15.0°, 9.0° de inclinación al soltarla).
- El mango se coge **de lado** (pinza horizontal, dedos en las caras planas de 12 mm), bajando en vertical desde arriba: así la antorcha queda atravesada en la pinza, como en la v1. Cogida desde arriba por el hombro (coaxial con la muñeca) un brazo de 5 ejes no puede soldar el cordón, que está en el lado lejano de la junta, con 45° y empuje: tendría que apuntar hacia el propio robot.

## Imanes (detalle)

La chapa se suelta (sin pinza) cerca de su sitio con un error al azar de ±5 mm y ±5° y se mira si los imanes la dejan a menos de 1.5 mm y 1.5° (criterio: 95%). Imanes: soldadura blanda con constante de tiempo 0.015 s (≈ 2 N a 10 mm), captura a < 10 mm y < 20°.

- t: {'n': 30, 'ok': 28, 'error_max_mm': 1.98, 'error_max_grados': 2.27, 'penetracion_max_mm': 0.17}
- esquina: {'n': 30, 'ok': 29, 'error_max_mm': 2.59, 'error_max_grados': 5.51, 'penetracion_max_mm': 0.39}
- t con `chaflan_ranura` = 1.5 mm (propuesta): {'n': 30, 'ok': 29, 'error_max_mm': 1.96, 'error_max_grados': 2.96, 'penetracion_max_mm': 0.1}
- esquina con `chaflan_tope` = 2 mm (propuesta): {'n': 30, 'ok': 30, 'error_max_mm': 0.05, 'error_max_grados': 0.07, 'penetracion_max_mm': 0.02}

## Soporte (detalle)

- {'n': 20, 'ok': 20, 'penetracion_max_mm': 0.03, 'punta_z_mm': (5.98, 6.0)}

## Mesa usada (contrato)

- `POSICION_BASE` = (280, 35, giro 0); `ZONA_LIBRE` = {'x': (110.0, 160.0), 'y': (160.0, 230.0), 'giro': (-60.0, 60.0)}; `SOPORTE_ANTORCHA` = {'x': 180.0, 'y': -180.0, 'z_mango': 116.0} (giro radial -45°, chaveta hacia fuera).

## Cambios de cota propuestos

- BASE-V2 (t): el chaflán de entrada de la ranura de la T mide ~1.0 mm en el CAD. Desde ±5 mm y ±5° la chapa encaja 28/30 veces con el del CAD y 29/30 con 1.5 mm: **hacer un chaflán de 45° × 1.5 en las dos aristas de la ranura** (los fallos son la chapa apoyada en el borde de la ranura, 2 mm arriba). Con lo que falla el robot al soltarla encaja siempre (guion 10/10).
- BASE-V2 (esquina): el chaflán de la arista interior (lado −Y) del tope de la esquina mide ~0.25 mm en el CAD. Desde ±5 mm y ±5° la chapa encaja 29/30 veces con el del CAD y 30/30 con 2 mm: **hacer un chaflán de 45° × 2 en la arista superior interior del tope** (los fallos son la chapa subida encima del tope). Con lo que falla el robot al soltarla encaja siempre (guion 10/10).
- Contrato: `SOPORTE_ANTORCHA` en (180, -180) (a r ≈ 255 mm, girado -45° con la chaveta hacia fuera): con el mango a 116 la pinza horizontal no llega más cerca. Cambia la posición en la mesa, no la pieza.
- Contrato: `ZONA_LIBRE` cerca y a la izquierda (x 110–160, y 160–230, sin pisar la base ni el robot): la pinza vertical solo coge la aleta y la levanta a r < ~250 mm; la zona de la derecha (y −260…−185) queda casi entera fuera de alcance. Cambia el tapete, no la pieza.
- Brief: la antorcha se coge de lado por el mango (no desde arriba apoyando en el hombro); el hombro no estorba y no hay que cambiar el CAD.

Tiempo de la validación: 99 s de CPU.

