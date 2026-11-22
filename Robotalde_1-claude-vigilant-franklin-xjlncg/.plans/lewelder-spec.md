# LeWelder: spec

> **Sustituida en parte por la [spec v2](lewelder-spec-v2.md)** (16-11-2026): papel del robot, VLA y clase.

Equipo **Robotalde**. Proyecto **LeWelder**: escuela de soldadura aumentada con robot SO-101.
Hackathon LeRobot Bilbao II · vie 20 - dom 22 nov 2026 · La Perrera (Bilbao) · 48 h · demo en vivo + pitch de 5 min ·
entrega domingo 11:00: presentación, dataset y código.

Estado: **spec definitiva** (fase 2 cerrada el 15-11-2026, entrevista hecha a mano porque la skill
`/jmo-workflow:interview` no estaba instalada en la nube). Pendiente de aprobación: reparto, calendario y guion
(secciones 12-14), que son propuesta.

Referencias: [ideas](../investigacion/ideas-desarrolladas.md) (idea 1) ·
[análisis de concursos](../investigacion/analisis-concursos.md) (secciones 3-6: por qué se gana y se pierde).

---

## 1. Resultado final

Una escuela de soldadura física y segura. Se "suelda" con una antorcha impresa con LED sobre piezas impresas
que imitan uniones reales. Una tablet muestra en tiempo real el gemelo digital de la pieza con el cordón, la nota y
los fallos. Un SO-101 hace de soldador maestro, dirigido por un **VLA** que recibe la orden en texto desde la app:
suelda solo los tramos que el alumno se dejó. Un segundo SO-101 (si lo hay) coloca las piezas.

Relato: **"En esta escuela aprenden a soldar personas y robots."**

Ejemplos base: repositorio de MSN (ganador Robotekin 2026: SO-101 + linterna + IBVS + voz) y simuladores
comerciales de soldadura (Soldamatic de Seabery, Lincoln VRTEX).

## 2. Decisiones de la entrevista

| Tema | Decisión |
|---|---|
| Momento estrella | **Modo Repaso**: el juez suelda, recibe nota y el robot suelda solo sus huecos |
| Papel del brazo soldador | **Solo suelda** (Maestro y Repaso) |
| Si el juez no deja huecos | El robot **certifica** al juez y **suelda la unión en T** (siempre actúa) |
| Piezas | **Impresas** imitando uniones reales, **fijadas con imanes** |
| Colocación | **Base con 3-4 anclajes imantados** (posiciones y giros distintos) |
| Uniones | Nivel 1: **a tope recta**. Nivel 2: **en T** |
| Longitud del cordón | **12 cm** (20-30 s por pasada humana) |
| Antorchas | **Dos**: la del alumno (microcontrolador + IMU + gatillo + LED) y otra fija en la pinza del robot |
| Microcontroladores | **ESP32 o Arduino**, da igual: ambos van por **cable USB serie**. Si no hay ESP32, Arduino Nano/Uno |
| LED del robot | Microcontrolador por USB en la antorcha del robot; el servidor lo enciende solo en los huecos |
| Repaso (técnica) | La política **recorre siempre el cordón completo**; el LED se enciende solo en los huecos |
| IMU | **El ángulo puntúa** (ángulo de trabajo y de avance) |
| Cámaras | **3**: cenital de la organización (política), muñeca nuestra (política), **webcam de seguimiento aparte** con exposición manual fija |
| Cordón visible | **Solo en pantalla** |
| Dónde se ve | **Tablet junto a la pieza** |
| Instructor IA | Avisos cortos por **reglas** durante la pasada + **valoración hablada del LLM al final** (2 frases). Sin internet, la demo sigue |
| Métricas | **Simplificadas, en lenguaje de oficio**: cobertura, regularidad de velocidad, puntos quemados, desvío, ángulo |
| Tolerancia | **Por niveles**: aprendiz ±8 mm, **oficial ±5 mm (jurado)**, maestro ±3 mm |
| **Política principal** | **VLA multitarea (SmolVLA)**: una sola política para recta y T en todos los anclajes. **La app escribe la instrucción** ("suelda la unión en T del anclaje B"), elegida por el ArUco de la pieza. Motivo: la organización/jurado quiere VLA |
| Respaldo de política | **Un ACT por tipo de unión**, entrenado con el mismo dataset. Se usa en la demo si el VLA no llega al objetivo |
| VLA grandes | pi0.5 o GR00T N1.7 por servidor remoto de LeRobot: **solo si sobra GPU y la wifi es buena** (nivel 3) |
| Objetivo del robot (sábado 20:00) | **8 de 10 recorridos completos a ±5 mm en cada anclaje** |
| 2.º SO-101 | **Posicionador aprendido por la misma VLA**: "coloca la pieza en el anclaje C" (coger y dejar sobre imanes). Nivel 3 |
| "Aprende del mejor" | **Filtro de calidad del dataset**: la nota puntúa cada demostración del brazo guía y solo las buenas entran |
| Entrenamiento | **Nube para el VLA** (cuenta de GPU preparada y probada, 10-30 €) + **portátiles para ACT** |
| App | **Web: servidor Python + página three.js** que la tablet abre en el navegador |
| Preparación previa | **Todo lo que no sea el robot** (firmware, seguimiento, gemelo, app) + **simulación del robot** y el flujo grabar → entrenar ACT y SmolVLA → desplegar practicado. Datos y modelos del robot, allí |
| Experiencia del equipo | **Nadie ha usado LeRobot** → practicar el flujo completo esta semana |
| Soldador real | **No**; las demostraciones las graba el equipo |
| Cliente en el pitch | **Los dos**: centros de FP/formación y empresas industriales ("forma a la persona y al robot") |
| Plan B si falla la política | ACT de respaldo → si también falla, **reproducción grabada declarada** (replay, diciéndolo) |
| Nombres | Equipo **Robotalde**, proyecto **LeWelder** |

### Por qué un VLA aquí (argumento del pitch)

Seguir un cordón con precisión es trabajo de ACT. El VLA aporta otra cosa: **una sola política entiende varias
órdenes** (qué unión, en qué anclaje, soldar o colocar) y la escuela le habla en el mismo idioma que al alumno. En
el pitch se enseña la comparativa VLA frente a ACT con datos (tasa de éxito y error medio por anclaje).

## 3. Material

Confirmado por la organización (15-11-2026): por equipo, **un par de SO-101 (guía + seguidor), una cámara y un
trípode**; SO-101 extra si sobran; **se permite setup propio**; no ponen impresoras.

Inventario del equipo (15-11-2026):

| Material | Estado |
|---|---|
| Impresora 3D y PLA | Lo tenemos |
| Webcams (2) y tablet | Lo tenemos |
| LEDs, imanes, pulsador de gatillo | Lo tenemos |
| Arduinos | Lo tenemos |
| ESP32 (2) e IMU | **Sin confirmar: Andoni lo mira el 16-11** |

Lista de compra (pedir el **lunes 16** como tarde, entrega antes del jueves):

- **IMU** si no hay: BNO055 o BNO085 (dan el ángulo ya fusionado; MPU6050 vale como respaldo barato). Comprar 2.
- **Cables USB largos** (3 m) para la antorcha del alumno y la del robot, y un **hub USB con alimentación**.
- Imanes de neodimio de repuesto (10×3 mm o el tamaño que use la base), PLA de un color mate para las piezas.
- ESP32 solo si no hay Arduinos suficientes (hacen falta 2 microcontroladores + 1 de repuesto).

## 4. Arquitectura

```
Antorcha alumno (MCU: gatillo, IMU, LED) --USB--> Servidor Python
Webcam seguimiento (LED + ArUco)         ------> Servidor Python --WebSocket--> Tablet (three.js: gemelo, nota)
Servidor Python --USB--> Antorcha robot (MCU: LED encendido solo en huecos)
Servidor Python --instrucción de texto--> LeRobot: SmolVLA (respaldo ACT[unión]) en SO-101 soldador
                                          (cámaras cenital + muñeca)
Servidor Python --instrucción--> LeRobot: SmolVLA en SO-101 posicionador (nivel 3)
Servidor Python --> LLM: valoración hablada al final (opcional, sin bloquear)
```

- **Seguimiento:** LED como punto brillante con exposición baja; pose de la pieza por ArUco; trazo en coordenadas
  de la pieza.
- **Métricas por tramo del cordón:** cubierto (gatillo pulsado y punta a menos de la tolerancia), velocidad,
  tiempo parado (quemado), desvío, ángulo.
- **Instrucción:** el servidor compone el texto a partir del ArUco (tipo de unión), el anclaje detectado y el modo.
  Vocabulario cerrado y siempre igual al del dataset.
- **Repaso:** lista de tramos pendientes → la política recorre el cordón completo → el servidor enciende el LED del
  robot al entrar en cada tramo pendiente (posición de la punta medida por el mismo seguimiento).
- **Filtro de dataset:** cada demostración grabada con el brazo guía pasa por las métricas; solo entran las de
  nota alta. Las métricas de la punta del robot sirven también para evaluar VLA y ACT con el mismo criterio.
- **Selector de política:** la app puede cambiar entre VLA, ACT y replay sin reiniciar (plan B en segundos).

## 5. Modos (alcance)

| Modo | Estado |
|---|---|
| Examen (el alumno suelda y recibe nota) | Imprescindible |
| Repaso (el robot suelda solo los huecos) | **Estrella** |
| Maestro (el robot suelda solo; la T cuando no hay huecos) | Imprescindible (nivel 2 para la T) |
| Aprende del mejor (filtro de dataset) | Nivel 2 |
| Comparativa VLA frente a ACT | Nivel 2 (diapositiva con datos) |
| Posicionador con la misma VLA | Nivel 3 |

## 6. Escalera de alcance

1. **Sábado 12:00:** seguimiento del LED y tablet con trazo y cobertura sobre la recta en un anclaje. Dataset de la
   recta en 1-2 anclajes grabado y subido; ACT de la recta entrenado y recorriendo la recta en un anclaje.
   SmolVLA entrenando en la nube.
2. **Sábado 20:00:** 3-4 anclajes, métricas completas con ángulo, modo Repaso con LED del robot, filtro de dataset.
   **Puerta de decisión:** si SmolVLA cumple 8/10 a ±5 mm por anclaje, la demo va con VLA; si no, con ACT y el VLA
   queda como comparativa.
3. **Domingo 10:00:** unión en T (en la misma VLA), certificación, voz del LLM al final, reproducción de respaldo
   preparada. Si hay 2.º brazo y tiempo: posicionador.

## 7. Criterios de éxito

- Seguimiento: trazo en la tablet con latencia < 150 ms y error < 2 mm (medido con plantilla impresa).
- Robot: **8 de 10 recorridos completos a ±5 mm en cada anclaje el sábado a las 20:00**, medido con el seguimiento.
- Comparativa VLA frente a ACT con tasa de éxito y error medio por anclaje, en una diapositiva.
- La parte humana (seguimiento, nota, gemelo) funciona aunque el robot falle.
- Cambio a plan B (ACT o replay) en menos de 10 s desde la app.
- Entrega completa antes del domingo 11:00: presentación, dataset en Hugging Face, código en GitHub.
- Pitch ensayado 3 veces, < 5:00.

## 8. Riesgos principales

| Riesgo | Mitigación |
|---|---|
| Parecido temático con MSN (soldadura) | Dejar claro que es una **escuela con evaluación** y un VLA multitarea, no un asistente |
| VLA menos preciso que ACT en ±5 mm | ACT de respaldo con el mismo dataset; puerta de decisión el sábado 20:00 |
| Wifi mala para nube (entrenar o inferir) | SmolVLA corre en el portátil (inferencia); entrenar de noche; dataset subido en tandas |
| GPU de la nube sin probar | Cuenta creada y entrenamiento de prueba hecho antes del jueves |
| Luz de la sala y reflejos en el LED | Exposición fija, LED de color concreto, prueba previa con luz fuerte |
| Holguras del SO-101 frente a ±5 mm | Calibración cuidadosa; antorcha corta y rígida; medir la holgura el viernes |
| Equipo sin experiencia en LeRobot | Practicar el flujo completo esta semana en simulación |
| Impresión | Todo impreso antes del jueves 19, con repuestos y 2-3 tolerancias de imanes y anclajes |
| Posicionador come tiempo | Es nivel 3: no se toca hasta tener el nivel 2 |

## 9. Preparación antes del evento

- Firmware de ambas antorchas, seguimiento LED + ArUco, servidor de métricas y app three.js: preparados y probados.
- Simulación del SO-101 (`sim/`, MuJoCo) para practicar grabar → entrenar ACT y SmolVLA → desplegar, con
  instrucciones de texto.
- Cuenta de GPU en la nube probada con un entrenamiento corto de SmolVLA.
- Todas las piezas impresas.
- Declarar en el pitch qué se preparó antes y qué se hizo allí.

## 10. Pendiente

- Organización: wifi estable para nube y APIs; si se puede traer código o modelos preparados; si confirman 2.º
  SO-101 seguidor; criterios del jurado (confirmar el peso del VLA).
- Andoni (16-11): mirar si hay ESP32 e IMU y hacer el pedido.

## 11. Fuera de alcance

Soldadura real, cordón físico visible, voz del juez como orden al robot, VLA grandes sin GPU garantizada.

## 12. Reparto de tareas (propuesta)

| Persona | Responsable de |
|---|---|
| **Andoni** (producto, CAD, 3D, electrónica) | Antorchas (CAD, impresión, electrónica, firmware serie), base de anclajes con imanes, piezas recta y T con ArUco, soportes de cámara de muñeca y webcam, montaje de la antorcha en la pinza, presentación y pitch |
| **Software 1** (robot e IA) | Flujo LeRobot: simulación, grabar con instrucción, entrenar SmolVLA (nube) y ACT (portátil), desplegar, selector de política, evaluación VLA frente a ACT, posicionador |
| **Software 2** (visión y app) | Seguimiento LED + ArUco, métricas y nota, servidor Python con WebSocket, app three.js, control del LED del robot, filtro de dataset, instructor (reglas + LLM) |

Durante el evento: Andoni graba demostraciones con el brazo guía (el oficio es suyo); Software 1 entrena y
despliega; Software 2 integra y prueba la app con el robot.

## 13. Calendario de esta semana (propuesta)

| Día | Andoni | Software 1 | Software 2 |
|---|---|---|---|
| **Dom 15** | Spec y plan cerrados | — | — |
| **Lun 16** | Inventario y pedido; CAD de antorcha del alumno y base | Instalar LeRobot 0.7 + MuJoCo; escena de simulación | Seguimiento del LED con la webcam (exposición fija) |
| **Mar 17** | Imprimir antorcha y base; firmware serie (gatillo + LED) | Grabar demostraciones en simulación con instrucción; entrenar ACT | ArUco y trazo en coordenadas de la pieza; métricas |
| **Mié 18** | Piezas recta y T; antorcha del robot; soportes de cámara | Cuenta de GPU; entrenar SmolVLA en la nube; desplegar en simulación | Servidor + app three.js con gemelo y nota |
| **Jue 19** | IMU en la antorcha; repuestos; borrador del pitch | Selector de política y evaluación con métricas en simulación | LED del robot y modo Repaso con datos simulados; LLM |
| **Vie 20** | Montaje en el evento; medir holgura | Calibrar SO-101; primeras grabaciones | Integrar seguimiento con la mesa real |

Prueba integrada de todo lo que no es robot: **jueves 19 por la tarde**, en casa de uno, con la base y las antorchas
impresas.

## 14. Guion de demo (5 min, propuesta)

| Tiempo | Qué pasa |
|---|---|
| 0:00 | Problema: faltan soldadores; formarlos gasta material, tiempo y tutores |
| 0:40 | Un juez suelda la recta con la antorcha; la tablet pinta el cordón y da la nota con avisos de oficio |
| 1:40 | **Repaso:** la app escribe la orden ("repasa la recta del anclaje B") y el robot suelda solo los huecos; el LED se enciende donde faltaba |
| 2:30 | El juez mueve la pieza a otro anclaje (o el posicionador la coloca) y el robot se adapta |
| 3:10 | Una sola VLA para todo: la orden cambia a "suelda la T" y el mismo modelo la hace. Diapositiva VLA frente a ACT con datos |
| 3:40 | La escuela elige qué ejemplos aprende el robot (filtro de dataset): "aprende del mejor" |
| 4:15 | Negocio: centros de FP y empresas, "forma a la persona y al robot". Qué se hizo antes y qué aquí |
