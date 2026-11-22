# Garbi · solución final (acordada con el usuario, 20-11)

Este documento sustituye a M4 y M5 de [especificacion-tecnica.md](especificacion-tecnica.md) donde se contradigan. La
percepción (M1-M3), la calibración y el montaje se mantienen.

## Decisiones

| Tema | Decisión |
|---|---|
| Cámaras | Solo RGB (`top` y `wrist`), sin cámara de profundidad |
| Manos | MediaPipe Hands en la cámara de arriba (lo hace el compañero). En la simulación, color de piel. Las dos opciones van detrás de la misma interfaz |
| Taladro | **Solo cuenta mano + taladro juntos**: ni la mano sola ni el taladro solo. El taladro se detecta por la bola naranja y una mano a < 120 mm |
| Orientación del taladro | Sin función: siempre que haya un taladro agarrado en escena, Garbi va a la distancia prudente |
| Despertar y descanso | Despierta con manos en el tapete. Descansa si no hay manos en el tapete ni tareas pendientes |
| ACT | Hace el **acercamiento**: desde la posición prudente hasta la de aspirar, y se mantiene ahí mientras taladras. Se entrena **sobre la madera en el tapete**, con las cámaras y la luz de la demo |
| Fin de ACT | Lo decide la percepción: la broca levantada para ACT y empieza la retirada fija. Los episodios grabados terminan en ese momento |
| Recuperaciones | Se graban: mover la broca a otro punto a mitad del acercamiento, una mano que se cruza. Más tarde, `dagger` |
| Aspiradora | Encendida durante el acercamiento (ACT) y la limpieza; apagada en el resto. Sin activación por ruido |
| ¿Agujero hecho? | Supletorio, para el final. De momento cuenta como agujero si la broca ha estado clavada ≥ `T_AGUJERO` s (2 s) |
| Madera | **Clara**, sin vinilo, con una pegatina de color en una esquina (resuelve el giro de 180°). Se puede mover dentro del tapete; los agujeros van en su marco |
| Limpieza | Fija, con la boca bien picada, en cada agujero en su sitio actual, cuando el taladro ya no está |

## Estados

| Estado | Entra | Hace | Aspiradora | Mueve |
|---|---|---|---|---|
| DESCANSO | Sin manos en el tapete y sin tareas, durante 3 s | Aparcado, respira | No | Fijo |
| DESPIERTO | Manos en el tapete | Postura de espera, sin estorbar | No | Fijo |
| PRUDENTE | Taladro agarrado en escena | Sigue al taladro con la cámara de la muñeca mirando la punta de la broca desde ~180 mm (la boca queda ~90 mm sobre la madera y a un lado; holgura ≥ 35 mm aunque el taladro se incline 8°). Es la postura de partida de ACT, igual al grabar y al ejecutar (cambio del 20-11, a confirmar por el usuario) | No | Fijo |
| ACERCAMIENTO | Broca clavada en la madera, dentro de la zona de taladro | Se acerca a aspirar y se mantiene | **Sí** | **ACT** (respaldo: el acercamiento programado) |
| RETIRADA | Broca levantada | Vuelve a la distancia prudente | No | Fijo |
| LIMPIEZA | Ni taladro agarrado ni manos y quedan agujeros pendientes | Cada agujero con la boca picada (45-60°) | Sí | Fijo |

Guardias por encima de todo, también de ACT: holgura ≥ 10 mm (+ margen de la percepción), borde de la boca ≥ 3 mm y
velocidad máxima. Si ACT se acerca de más, se le frena y, si insiste, entra el respaldo.

## Tarea de los 5 intentos

1. Coges el taladro y Garbi se pone a la distancia prudente.
2. Clavas la broca y ACT se acerca y aspira.
3. Taladras, levantas la broca y Garbi se retira.
4. Sacas el taladro y Garbi limpia el agujero.
5. Garbi descansa.
