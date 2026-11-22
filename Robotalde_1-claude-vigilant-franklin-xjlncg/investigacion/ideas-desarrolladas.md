# Ideas desarrolladas para el Hackathon LeRobot Bilbao II

Fecha: 13-11-2026 (versión 2). Base: [analisis-concursos.md](analisis-concursos.md).
Las ideas anteriores (Jenga, rehabilitación, desayuno, entrenado por todos) quedan descartadas por decisión del equipo.

Premisa: el proyecto no se limita al robot. Se pueden sumar apps, pantallas, tablets, electrónica propia
(ESP32, Arduino, Raspberry Pi), sensores y piezas impresas.

**Confirmado por la organización (WhatsApp, 15-11-2026):**
- Cada equipo recibe **un par de SO-101 (guía + seguidor), una cámara y un trípode**.
- Habrá SO-101 extra en el evento; se pueden pedir si sobran.
- **Se permite llevar setup propio.**
- No ponen impresoras. En el espacio hay alguna, pero no está confirmado que se puedan usar.
- No respondieron explícitamente sobre IA (APIs, nube) ni sobre código preparado de antemano.

Equipo: **A** (datos y políticas), **B** (app, visión, LLM, panel), **tú** (producto, CAD, impresión 3D,
electrónica, guion y pitch; además grabas demostraciones).

---

## Idea 1 · Escuela de soldadura aumentada (idea del equipo)

**Concepto.** Un simulador de soldadura físico y seguro: la antorcha es una pieza impresa con un LED potente en
la punta. Se "suelda" sobre piezas reales (impresas o de chapa) y una pantalla muestra en tiempo real el gemelo
digital de la pieza con el cordón que vas dejando, como en un simulador profesional, pero con un robot que
enseña, sujeta y corrige.

**Relato:** "En esta escuela aprenden a soldar personas y robots." La misma técnica que mide al alumno sirve para
grabar demostraciones con las que aprende el robot.

### Modos

| Modo | Quién suelda | Qué hace el robot | Qué se ve en pantalla |
|---|---|---|---|
| **Maestro** | El robot | Coge la antorcha LED y suelda el cordón de la pieza, esté donde esté | El cordón perfecto, como referencia |
| **Posicionador** | El alumno | Sujeta y orienta la pieza en el ángulo más cómodo y la gira entre cordones | Línea de soldadura objetivo y trazo del alumno |
| **Examen** | El alumno | Nada; observa | Nota en directo: cobertura, velocidad, puntos donde se para demasiado, distancia y ángulo |
| **Repaso** | Alumno y robot | Repasa **solo los tramos que el alumno se dejó** | Mapa de cobertura: verde soldado, rojo pendiente, naranja quemado |
| **Aprende del mejor** | El mejor alumno | Graba su pasada como demostración y el robot la imita | Ranking y "el robot ya suelda como Ane" |

### Cómo funciona por dentro

- **Antorcha LED (tú):** impresa, con LED de alta potencia, ESP32, IMU para el ángulo y gatillo. Envía por wifi
  si el gatillo está pulsado y la orientación.
- **Seguimiento:** una cámara cenital con la exposición baja ve el LED como un punto brillante (muy fácil de
  detectar). Marcadores ArUco en la pieza dan su posición y orientación, así que el alumno puede poner la pieza
  donde quiera.
- **Gemelo digital (B):** app web con la pieza en 3D (three.js), la línea objetivo y el trazo en tiempo real
  coloreado por calidad. Métricas: % de línea cubierta, velocidad media y su regularidad, tiempo parado en un
  punto ("aquí quemarías la pieza"), desvío de la línea, ángulo de la antorcha.
- **Robot (A):**
  - Habilidad central aprendida: **seguir un cordón con la antorcha a distancia y velocidad constantes**, para
    piezas en distintas posiciones. Se aprende de demostraciones (60-80) grabadas con el brazo guía.
  - Agarre de la antorcha con un mango impreso a medida (siempre la coge igual).
  - Modo Repaso: la app manda al robot el tramo pendiente (híbrido: el tramo se calcula, el gesto se aprende).
- **LLM con voz:** el instructor que comenta la pasada ("vas demasiado deprisa en la esquina").

### Demo de 5 minutos

0:00 problema: faltan soldadores y formar uno cuesta material y tiempo · 0:40 un juez suelda con la antorcha
LED; su nota aparece en directo · 1:40 el robot repasa solo lo que el juez se dejó · 2:30 modo Maestro con la pieza
en otra posición · 3:20 perturbación: el juez mueve la pieza a mitad de cordón y el robot se adapta · 4:00 datos y
negocio (escuelas de FP, empresas de calderería).

### Filtro de 7 puntos

| Criterio | ¿Cumple? |
|---|---|
| Habilidad central al 80 % | ✓ seguir un cordón con una herramienta que siempre se coge igual |
| Parece difícil | ✓ soldar se percibe como oficio difícil |
| Humano en el centro | ✓ el juez suelda y recibe nota |
| Recuperación planificada | ✓ pieza movida a mitad de cordón; tramos pendientes repasados |
| Capa de vida quitable | ✓ instructor LLM con voz |
| Algo físico nuestro | ✓ antorcha LED con ESP32 e IMU, piezas con ArUco |
| Escalera de alcance | ✓ ver abajo |

### Escalera de alcance

1. **Sábado 12:00:** seguimiento del LED y pantalla con trazo y cobertura sobre una pieza fija. El robot sigue un
   cordón recto en posición fija.
2. **Sábado noche:** pieza en cualquier posición (ArUco), métricas completas, modo Repaso.
3. **Domingo:** IMU y ángulo, instructor LLM, modo "Aprende del mejor", ranking.

### Riesgos

- **Parecido con MSN** (ganador de Robotekin, asistente de soldadura con linterna): el tema coincide, el producto
  no (ellos alumbran un punto; esto es una escuela con evaluación). Hay que dejarlo claro en el pitch.
- Reflejos y luz de la sala en la detección del LED → exposición baja y LED de un color concreto.
- Ya existen simuladores comerciales (por ejemplo, de realidad virtual): nuestra diferencia es el robot que
  enseña, sujeta y corrige, y que aprende de los alumnos.

---

## Idea 2 · Lote 1: la fábrica de un solo cliente (se mantiene)

Cada juez diseña su figurita de SO-101 en miniatura desde el móvil (QR, LLM que propone el diseño), el pedido
aparece en la cola de fabricación de la pantalla, el robot encaja las piezas impresas con imanes, la cámara
comprueba el montaje y corrige, y se la entrega en mano. Habilidad central: encajar piezas. Detalle completo en la
versión 1 de este documento (historial) y en la conversación del 13-11-2026.

---

## Idea 3 · Médico de máquinas (nueva)

**Concepto.** Un robot que inspecciona una máquina como un médico: le "toma la temperatura", la "ausculta" y le
"mide el pulso", y diagnostica la avería.

**Montaje.** Una maqueta de máquina impresa (cinta transportadora o reductora) con motores y un Arduino/ESP32 que
puede provocar averías: un rodamiento que vibra, un motor que se calienta, una correa floja.

**Cómo se usa.**
1. El juez provoca una avería en secreto desde una tablet ("rompe la máquina").
2. El robot recorre los puntos de inspección y apoya su sonda (micrófono de contacto, sensor de vibración o
   cámara térmica en la pinza) en cada uno.
3. La pantalla muestra el gemelo digital de la máquina con el mapa de calor y vibraciones, y un LLM explica el
   diagnóstico: "el rodamiento 2 vibra a 120 Hz: desgaste".

**Qué aprende el robot.** Apoyar la sonda en cada punto con el contacto justo, aunque la máquina esté en otra
posición (60-80 demostraciones).

**Por qué gana.** Mantenimiento predictivo: utilidad industrial inmediata. Interacción: el juez la rompe y el robot
la cura. Recuperación: si la sonda no hace buen contacto (señal plana), la recoloca. Algo físico nuestro: maqueta
y sondas.

**Riesgos.** Que la avería provocada sea fiable y se note en el sensor; que la demo parezca lenta.

---

## Idea 4 · Desmontaje circular (nueva)

**Concepto.** El robot desmonta un aparato al final de su vida útil y separa sus materiales para reciclarlos.
Es la otra mitad de la fábrica: no fabricar, sino recuperar.

**Montaje.** Un aparato maqueta impreso (un "móvil" o mando grande) con tornillos de cabeza grande, tapa, placa y
batería simulada. Destornillador eléctrico como herramienta del robot, accionado por un ESP32.

**Cómo se usa.** El juez entrega "su aparato viejo"; el robot lo identifica con la cámara, lo desatornilla, quita
la tapa, saca la batería a su contenedor y la placa al suyo. La pantalla lleva la cuenta de materiales recuperados,
CO₂ evitado y valor recuperado.

**Qué aprende el robot.** Destornillar (alinear la punta con el tornillo, contacto y giro) y levantar la tapa.
Parece muy difícil.

**Por qué gana.** Economía circular y normativa europea de baterías: muy actual. Interacción y entrega por el juez.
Recuperación: tornillo que no sale → reintenta o cambia de estrategia.

**Riesgos.** Destornillar es lo más difícil de fiabilizar de las cuatro ideas.

---

## Comparación

| | 1. Escuela de soldadura | 2. Lote 1 | 3. Médico de máquinas | 4. Desmontaje circular |
|---|---|---|---|---|
| Riesgo en vivo | Medio-bajo | Medio-bajo | Medio | Alto |
| Dificultad percibida | Alta | Alta | Media-alta | Muy alta |
| Utilidad práctica | Muy alta (formación) | Alta | Muy alta | Alta |
| Interacción con el jurado | **Sueldan y reciben nota** | **Diseñan y se llevan la figura** | Rompen la máquina | Entregan el aparato |
| Elementos extra | Antorcha ESP32+IMU, app 3D en tiempo real, ArUco, LLM | App/QR, pantalla de cola, imanes, LLM | Maqueta con Arduino, sensores, tablet, gemelo | Destornillador con ESP32, pantalla de materiales |
| Parecido con ganadores | Tema parecido a MSN | Bajo | Bajo | Bajo |
| Aprovecha tu perfil | **Máximo** (electrónica + CAD) | **Máximo** (CAD + impresión) | Alto | Alto |
