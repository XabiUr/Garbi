# Spec · Aspira

**Robotalde · Physical AI Hackathon Bilbao II (20-22 de noviembre de 2026)** · versión 1 · 19-11-2026
Elegida por el usuario. Integra el concepto base, los tres especialistas (procesos, gestión del robot, hardware) y
las correcciones del equipo rojo. Documentos de detalle en esta carpeta: [procesos.md](procesos.md),
[gestion-robot.md](gestion-robot.md), [hardware.md](hardware.md), [equipo-rojo.md](equipo-rojo.md).

Marcas: [H] leído en la fuente · [H·b] extracto del buscador · [est.] estimación sin medir · [medir] pendiente.
Ningún gesto se ha probado todavía en un SO-101.

---

## 1. La idea

> **«Aguántame la aspiradora mientras taladro.»** Con una mano en la herramienta y la otra en la pieza, nadie
> sostiene la boquilla donde nace el polvo. Aspira lo hace: escucha qué vas a hacer y dónde, y deja la boca de
> aspiración pegada al punto, en el lado que no te estorba.

**Necesidad evidente (las cuatro pruebas):** todo el que ha taladrado o lijado ha llenado la mesa de polvo · se
entiende en una frase · hoy se resuelve con apaños (otra persona con el tubo, el pósit doblado, la botella cortada, el
adaptador para taladrar solo; más de 10 apaños en YouTube, uno con ~188.000 visitas [H·b]) · el robot hace de segunda
persona. Además, el polvo de madera es un riesgo reconocido: Grupo 1 de la IARC [H]; el de madera dura tiene límite de
2 mg/m³ en la Directiva (UE) 2017/2398 [H·b].

**Por qué funciona la física:** la captación cae muy deprisa con la distancia; a un diámetro de la boca ya es
inferior al 10 % [H, procesos §0]. El apaño falla porque deja la boca lejos; una boca de ~35 mm debe estar a
30-60 mm de donde nace el polvo [est.]. La precisión del SO-101 (±1 cm) basta.

**Hueco:** no hay ningún vídeo de un robot que lo haga, ni con SO-101 ni con otros brazos
(`.plans/brief2/videos-*.md`).

## 2. Decisiones de diseño (resuelven las contradicciones entre informes)

| Tema | Decisión | Por qué |
|---|---|---|
| Boquilla | **Mango atornillado a la pinza con un cabezal único** (rama C' de gestión del robot). Sin cambio de cabezal en la nota | El cambio de cabezal era lo más difícil y no puntuaba (equipo rojo). Un cabezal menos = un fallo menos |
| Cabezal | Boca alargada de **80 × 15 mm** con labio en media luna, PETG, ~25 g [est.] | Sirve junto a la broca (captura el anillo de viruta) y a lo largo de un canto |
| Tubo | Último tramo **Ø 32-40 mm, ligero y que no se aplaste** (manguera de aspiradora, no fuelle de desagüe) | Con Ø 20 el aire va a ~80 m/s y se pierde caudal; el fuelle se acorta con el vacío y tira del brazo (equipo rojo) |
| Manguera | Colgada de un pescante con polea a ~1 m y contrapeso; el robot solo carga mango, cabezal y el último tramo | Par del hombro: trabajar a r ≤ 270 mm del eje (hardware §2) |
| Aspiradora | Kärcher WD 1 Classic o similar de red (42 l/s [H]) | Las de batería duran 10-20 min |
| Distancia | **Una sola cota:** centro de la boca a **35 ± 10 mm** del eje de la broca o del canto; nada a menos de 15 mm del filo | Unifica 20-40, 30-60 y 35 mm de los tres informes |
| Colores | Marca de taladro **roja**; cabezal **azul** | Que el vigilante no los confunda |
| Grabación | Siempre con la herramienta **apagada** | El robot nunca se mueve con la herramienta en marcha; la política no ve la broca girar |
| Material | Solo pino; cara superior de la tabla **pintada de negro mate** | El polvo se ve encima, que es donde queda en un agujero ciego |
| Lijado | **A mano con taco** en la nota; lijadora eléctrica fuera | Silencioso para la sala, sin quitar la caja de polvo de ninguna lijadora (comparación honrada) |

## 3. Los procesos y cómo los gestiona el robot

### 3.1 Tabla de procesos

| Proceso | Nivel | Dónde nace el polvo | Qué hace el robot | Orden (inglés, fija) | Mantener | Riesgo |
|---|---|---|---|---|---|---|
| **Taladrar en una marca** (broca vertical, pieza en la mesa) | **N1, nota** | Anillo de viruta alrededor de la broca; punto fijo | Deja la boca a 35 ± 10 mm de la marca, **en el lado libre** (lejos de la mano y del sargento), a ras, inclinada 30-45° | `Help me drill at the mark.` | Quieto | Bajo |
| **Lijar un canto a mano** (taco) | **N2, nota** | Polvo fino que cae por el canto | Deja la boca a lo largo del canto nombrado | `Help me sand the left edge.` / `Help me sand the right edge.` | Quieto | Bajo |
| **Atornillar** (control negativo) | N2 | No hay polvo | **No se mueve**; aprendido, no filtrado por regla | `I will drive a screw.` | — | Nulo |
| Retirarse | Todos | — | Vuelve a aparcado (programado) | `/reset` | — | Bajo |
| Seguir una lijadora orbital en marcha | N3, fuera de nota | Abanico fino en el borde del plato; punto móvil | Sigue la lijadora con control visual programado (ArUco en la lijadora, plano de la mesa calibrado) a ≤ 3 cm/s | Programado | Seguir | Medio |
| Taladrar en vertical (pared) | N3, fuera de nota | Cae por gravedad bajo el agujero | Boca debajo del punto | — | Quieto | Medio |
| Caladora, Dremel, fresadora | **Fuera** | — | — | — | — | Ruido, chispas, filo expuesto |

### 3.2 Arquitectura por capas

| Capa | Qué hace | Cómo |
|---|---|---|
| 0 · Seguridad | El robot no se mueve con la herramienta en marcha; límite de paso por servo; zona prohibida alrededor del filo | Programado: `--robot.max_relative_target` (verificado en el código), `vigilante.py` con la cámara fija, interbloqueo por sonido (micrófono) |
| 1 · Orquestador | Máquina de estados por proceso: aparcado → colocar → comprobar → mantener → retirar | Programado: `puente.py` lanza `lerobot-rollout --interactive` y le escribe por la entrada estándar `/subtask <frase>`, `/start`, `/reset` |
| 2 · Habilidad | **Colocar la boca en el sitio que pide la frase, según dónde estén la marca, la mano y el sargento** | **Aprendido:** SmolVLA multitarea (un ACT por orden de respaldo) |
| 3 · Lenguaje | Voz en español → frase canónica en inglés | Reglas + LLM del inventario (`lewelder/voz.py`); botones como entrada principal |
| 4 · Seguimiento (N3) | Mantener la boca detrás de una lijadora en movimiento | Programado (control visual), bucle propio fuera del rollout |

**Lo que hace que el VLA sea necesario (respuesta a «eso es visión + IK»):** la colocación depende a la vez de la
frase (proceso y canto) y de la escena: dónde pegó el juez la marca, en qué lado tiene la mano, dónde está el sargento
o el cable de la herramienta. Un script necesita una regla para cada combinación; la red aprende «el lado libre» de
las demostraciones. Se demuestra con dos cosas: la matriz frase × postura y una **línea base programada** (color +
cinemática inversa, que siempre se pone en el mismo lado) medida al lado, con la mano del juez en sitios distintos.

### 3.3 Fases de un proceso (taladrar, N1)

1. La persona dice «voy a taladrar aquí» (la marca ya está pegada donde quiso el juez) o pulsa el botón «Taladrar».
2. El orquestador comprueba que el micrófono no oye la herramienta y lanza `/subtask Help me drill at the mark.` +
   `/start`.
3. Segmento aprendido (~15 s): el brazo baja desde aparcado y deja la boca junto a la marca, en el lado libre; las
   demostraciones acaban con 3 s quietas.
4. El vigilante (cámara fija) comprueba la distancia boca-marca (35 ± 10 mm) y la zona prohibida: pantalla verde y
   pitido «Listo». Si falla: `/reset` y un reintento; al segundo, «No listo».
5. La persona taladra (3-5 s, agujero ciego con tope). El robot se queda quieto: el rollout mantiene la postura al
   acabar el segmento (verificado).
6. Fin por botón «Hecho» (o voz, o el sonido que se apaga 1,5 s): `/reset`, el brazo vuelve a aparcado.

**Parada de emergencia: `/reset`, nunca `/stop`**: `/stop` quita el par a los servos y el brazo cae (verificado).

### 3.4 Cómo sabe que empieza y termina

Botón grande en la tablet o pedal USB (principal) · voz «listo» (secundaria) · sonido de la herramienta (interbloqueo
y fin automático, umbral calibrado en la sala) · visión (respaldo).

## 4. La demo

**Tarea declarada para los 5 intentos:** «el juez pega la marca donde quiera dentro de la zona y pone su mano donde
quiera; el robot deja la boca a 35 ± 10 mm de la marca, en el lado libre, en menos de 30 s, sin que nadie lo toque».
Cinco marcas en serie sobre la misma tabla: la escena se repone sola (la persona taladra, el robot se retira, el juez
pega la siguiente). ~40-50 s por intento [est.]: ~4 min.

**El momento memorable:** la tabla con la cara de arriba negra y **dos mitades**. En la izquierda, cinco agujeros
taladrados antes con el apaño honrado (un tubo fijo que la persona tiene que recolocar a mano en cada agujero); en la
derecha, los cinco de la demo con Aspira. El jurado ve una mitad blanca de polvo y la otra limpia, y un contador:
**«veces que soltaste la herramienta: 5 frente a 0»**.

**Medida (protocolo de procesos §c):** tandas alternas con y sin Aspira; foto cenital fija con umbral de píxeles y
báscula de 0,01 g; se publican los números brutos.

**Formato de 5 minutos:** 0:00-0:30 la necesidad (la frase y la mitad sucia de la tabla) · 0:30-4:30 los cinco
intentos; mientras el brazo se mueve, se cuentan los datos · 4:30-5:00 la mitad limpia, el contador y la tabla de
medidas. **Versión de 90 segundos:** un intento con el juez eligiendo marca y mano, y las dos mitades.

**Fuera de nota:** lijar un canto, el control negativo de atornillar, seguir la lijadora (N3) y la línea base
programada al lado.

## 5. Datos y entrenamiento

| Orden | Episodios | Variedad |
|---|---|---|
| `Help me drill at the mark.` | 60 | Marca en 5 zonas × 2 lados de la mano × con y sin sargento; la mano de quien graba en la escena |
| `Help me sand the left edge.` / `right edge.` | 35 + 35 | Pieza en 3 posiciones |
| `I will drive a screw.` | 15-20 | Quedarse quieto con el destornillador en la mano |

Todas con la herramienta apagada; 3 s quietas al final; cámaras `top` y `wrist` a 640 × 480 y 30 fps; un dataset por
orden (`lerobot-record --resume=true --dataset.no_stamp=true`) y fusión para SmolVLA. **Medidas que se enseñan:** X/10
por orden, matriz frase × postura, línea base programada frente a la red con la mano en sitios distintos, y el
cuaderno de fallos corregidos. **Ramas:** A (SmolVLA lee la frase y el lado libre) · B (un ACT por orden y el botón
elige) · C (solo taladrar, el lado fijo) · C'' (sin aprendizaje: la línea base programada, y se dice).

## 6. Hardware

Detalle en [hardware.md](hardware.md) y [banco-aspira.svg](banco-aspira.svg), con estas correcciones del equipo
rojo: un solo cabezal; tubo final de Ø 32-40 mm no plegable; marca roja y cabezal azul; tabla de pino pintada de negro
por arriba. **Imprimir hoy (~7 h [est.]):** mango con atornillado a la pinza, cabezal (2 copias), soporte de la cámara
fija y pieza de la polea. **Comprar:** aspiradora de red, manguera ligera de Ø 32-40, poste y polea, contrapeso,
listón de pino, pintura negra mate, cartulinas negras, báscula de 0,01 g, taladro a batería con tope de profundidad,
gafas y mascarillas FFP2. Presupuesto ~150-250 € [est.] si el taladro lo pone el equipo.

**Pruebas físicas de hoy (sin robot):** (1) captación real del cabezal con la aspiradora encendida a 25, 35 y 50 mm
de un agujero, con la tabla negra; (2) fuerza del tubo con la aspiradora **encendida** (báscula en el extremo); (3) par
en la pinza con el contrapeso (báscula y regla).

## 7. Riesgos principales

| Riesgo | Comprobación | Si sale mal |
|---|---|---|
| La organización no deja polvo ni ruido | Correo hoy (5 preguntas, abajo) | Lija a mano en la nota; taladro en vídeo; o fuente de polvo de prueba (embudo con serrín) |
| El tubo tira del brazo con la aspiradora encendida | Prueba de hoy | Contrapeso mayor, tubo más corto, trabajar más cerca del eje |
| La red no aprende «el lado libre» | Matriz del sábado | Rama B o C; el lado se fija y se dice |
| Captación peor de lo esperado | Prueba de hoy | Boca más cerca (25 mm) o cabezal con faldón |
| Los cinco intentos no caben | Ensayo del sábado | Tarea declarada solo como colocación; taladrar en dos de ellos |
| SmolVLA no cabe o es lento en la GTX 1660 | Jueves: carga y latencia | Servidor remoto o ACT |

**Correo de hoy** a gazteria@bilbao.eus y a Bravo Robots: (1) ¿taladro a batería en ráfagas de 3-5 s en pino y lijado
a mano en la mesa? (2) ¿aspiradora de taller de red encendida, con enchufe? (3) ¿superficie por equipo y se puede
traer un tablero con un poste de 1 m? (4) ¿demo en la mesa o en escenario, y cuántos minutos? (5) ¿material propio y
requisitos de EPI?

## 8. Probabilidad y lo que la mueve

Podio [est. del equipo rojo]: 15 % (8-25 %) con el plan inicial; **20-30 % con estos cambios**. Lo que más la mueve:
la prueba de captación de hoy, quitar el cambio de cabezal (de 3 a 5 aciertos son 12 puntos) y tener medida la
respuesta a «un soporte lo hace igual» (contador 5 frente a 0) y a «visión + IK» (línea base al lado).
