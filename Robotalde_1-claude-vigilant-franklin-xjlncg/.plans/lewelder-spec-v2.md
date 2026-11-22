# LeWelder v2: spec

Equipo **Robotalde**. Proyecto **LeWelder**: escuela-taller de soldadura con un robot SO-101 que entiende lo que
le piden y lo que ve. Hackathon LeRobot Bilbao II · vie 20 - dom 22 nov 2026 · La Perrera (Bilbao) · 48 h · demo
en vivo + pitch de 5 min · entrega domingo 11:00 (presentación, dataset y código).

Estado: **spec v2** (entrevista `/jmo-workflow:interview` del 16-11-2026). Sustituye a
[lewelder-spec.md](lewelder-spec.md) en todo lo que contradiga; lo no mencionado aquí sigue valiendo.

## 0. Por qué hay una v2

La v1 usaba el VLA como seguidor de trayectorias: 8 órdenes fijas, sin generalización ni razonamiento visual, en
la tarea (seguir una línea a ±5 mm) que más castiga a un VLA. Uso de rasgos VLA: 2-3/10. La organización y el
jurado quieren VLA. Además, el usuario quiere una aplicación **más escuela, más instructiva y más show**.

Cambio de fondo: el robot deja de ser "el soldador que repasa huecos" y pasa a ser **el ayudante del taller que
monta la junta que se le pide, la señala, demuestra cómo soldarla y entiende órdenes habladas**. El VLA hace lo que
solo un VLA hace bien: varias tareas con una política, órdenes en lenguaje y objetos en posiciones nuevas.

Relato: **"En esta escuela aprenden a soldar personas y robots"** pasa a **"Un taller donde el robot es tu
compañero: le pides la junta, te la monta, te enseña y luego sueldas tú"**.

## 0.1 Tono: arcade (decisión del 16-11)

LeWelder es una **demo interactiva y divertida con sensación de máquina arcade**, no un producto para vender a
escuelas. La "escuela" es la temática del juego. Consecuencias para todo el diseño:

- **Rondas cortas** (el juez juega en 60-90 s): pedir → montar → soldar → puntuación.
- **Puntuación arcade** además de la nota de oficio: puntos por tramo, **combos** por tramos seguidos bien soldados,
  multiplicador por ritmo constante, penalización visible por quemados, **récord y ranking** del día (iniciales de
  tres letras, como en las recreativas). La nota técnica (métricas de oficio) sigue debajo y alimenta los puntos.
- **Feedback inmediato y exagerado**: chispas y sonido de arco mientras se suelda bien, zumbido y temblor de pantalla
  al quemar, "¡COMBO x5!", cuenta atrás "3, 2, 1, ¡SUELDA!", fanfarria al batir el récord.
- **El robot es un personaje** (nombre y voz propios, frases cortas con humor de taller): presume al montar, reta al
  juez ("a ver si superas mi cordón"), se pica si le ganan. Su pasada es el **fantasma rival** que hay que batir.
- **Pantalla de atracción** cuando nadie juega: el robot monta y suelda solo en bucle con el ranking, como una
  recreativa en modo demo ("PULSA PARA JUGAR").
- La utilidad real se cuenta en el pitch en una frase (formación segura sin material ni riesgo), no se vende.
- **Estética: blueprint y 3D.** La interfaz es un plano técnico vivo: fondo azul de plano con rejilla, trazo técnico
  blanco/cian, cotas animadas, cajetín, símbolos de soldadura ISO 2553; el gemelo 3D en aristas tipo plano que se
  "construye" al montar; el cordón del juez es lo único con luz y color (arco naranja y chispas); los eventos arcade
  aparecen como sellos de revisión en rojo y el ranking como una lista de piezas. El ritmo, el sonido, los puntos y el
  personaje dan la sensación arcade.

## 1. La clase (recorrido del alumno y del jurado)

Estructura **taller completo + maestro-aprendiz**:

1. **Pedir la junta.** El alumno (o el juez) dice "móntame una unión en esquina". Voz → LLM → orden del
   vocabulario cerrado → la tablet la muestra ("¿Monto una unión en esquina?") → se confirma con un toque.
2. **El robot monta.** Busca la chapa móvil tumbada en la zona libre de la mesa, la coge por la aleta, la gira 90°
   y la deja sobre la base fija; los imanes cierran la junta.
3. **La escuela reconoce.** Dos webcams en estéreo calculan la pose 3D de cada chapa (ArUco por chapa) y la tablet
   nombra la junta y su posición de soldeo ("unión en esquina, posición PB"). Muestra la **ficha de teoría**: para
   qué sirve, dónde se ve en la industria y el ángulo de antorcha correcto.
4. **Comprobar el alcance.** Si la junta queda fuera del alcance del robot o mal orientada, el robot pide al alumno
   que la gire ("gírala 90° hacia mí") con voz y una flecha en la tablet. Nivel 3: la gira el propio robot.
5. **El robot señala y demuestra.** Señala con la punta la línea del cordón ("aquí va el cordón"). Luego coge su
   antorcha del soporte y suelda la junta: su velocidad y su ángulo quedan grabados como **fantasma del maestro**.
6. **El alumno suelda.** Con su antorcha: solo cuenta como soldado si **pulsa el gatillo y la punta está apoyada**
   en la chapa (altura medida en estéreo). En la tablet ve el fantasma del maestro contra su propia línea en vivo.
7. **Nota, progreso y certificado.** Nota por tramos (lo ya hecho), insignia por junta superada, niveles aprendiz →
   oficial → maestro, y certificado con las juntas dominadas.
8. **Recoger.** "Desmonta la junta": el robot quita la chapa móvil y la deja en la zona libre (nivel 2).

## 2. Decisiones de la entrevista

| Tema | Decisión |
|---|---|
| Estructura de clase | Taller completo (pedir → montar → reconocer → soldar → certificar) + maestro-aprendiz (el robot demuestra primero) |
| Habilidades VLA | Montar la junta pedida, señalar el cordón, ayudante que obedece (desmontar y recoger, acercar la antorcha, girar la junta) |
| Habilidad imprescindible | **Montar la junta** |
| Repaso de huecos | **Eliminado** |
| Juntas | **En T** y **en esquina** |
| Piezas | **Base fija + una chapa móvil** por junta, unidas con imanes |
| Chapas sueltas | **Tumbadas con aleta** en una **zona libre** de la mesa, en posiciones y giros variados; el robot las gira 90° al colocarlas |
| Reconocimiento | **Un ArUco por chapa** → pose 3D de cada chapa → tipo de junta y posición de soldeo por geometría |
| Cámaras de seguimiento | **Dos webcams en estéreo**: pose 3D de las chapas y altura real de la punta |
| Apoyo de la antorcha | La **cámara ve el apoyo** (punta a < 2 mm de la chapa, en estéreo); sin marca física ni electrónica en la pieza |
| Gatillo | **Gatillo + apoyo**: solo cuenta como soldado con las dos cosas |
| Fuera de alcance | **Por niveles**: primero pide al alumno que la gire; nivel 3, la gira el robot |
| Antorcha del robot | **La coge de un soporte** con mango (cambio de herramienta); la pinza queda libre para las chapas |
| Demostración del maestro | Técnica con **fantasma** + **errores típicos** (cómo se hacen los errores: **pendiente**, ver 9) |
| Tablet | **Ficha de teoría corta**, **fantasma del maestro**, **progreso y niveles** (sin test de preguntas) |
| Órdenes | **Voz + confirmación en la tablet** (LLM traduce a vocabulario cerrado) |
| Momento show | **El juez pide, el robot monta**: "móntame una esquina" → monta → la tablet la reconoce y la nombra → el robot la demuestra → el juez suelda y recibe nota |
| Inferencia del VLA en el evento | **Servidor remoto en la nube** (servidor de políticas de LeRobot en GPU), el robot en local |
| 2.º SO-101 | **Grabar en paralelo** (doble de demostraciones); después, repuesto calibrado |
| Objetivo el sábado 20:00 | **Montaje 8/10 por junta** (T y esquina), con la chapa en posiciones nuevas de la zona libre |
| Plan B si el VLA no monta | **El alumno monta** con ayuda de la tablet (reconocimiento 3D + ficha); el robot se queda en señalar y demostrar |
| Preparación esta semana | Montaje en simulación, reconocimiento 3D estéreo, voz → orden → tablet, piezas y soportes (Andoni) |
| Tono | **Arcade**: rondas cortas, puntos y combos, ranking del día, chispas y sonido, robot con personalidad que es el rival a batir, pantalla de atracción (ver 0.1) |

## 3. Vocabulario del robot (órdenes del VLA)

Una sola política SmolVLA multitarea. Vocabulario cerrado (el LLM traduce la voz a una de estas frases):

| Orden | Nivel |
|---|---|
| `monta una unión en T` | 1 (núcleo) |
| `monta una unión en esquina` | 1 (núcleo) |
| `señala el cordón` | 1 (núcleo) |
| `coge la antorcha y suelda la junta` | 1 (núcleo; ACT o replay de respaldo) |
| `desmonta la junta` | 2 |
| `acércame la antorcha` | 2 |
| `gira la junta hacia ti` | 3 |

## 4. Arquitectura

```
Voz (navegador / Whisper) → LLM → orden cerrada → tablet (confirmar) → servidor
Webcam A + Webcam B (estéreo) → ArUco por chapa → pose 3D de cada chapa → tipo de junta + posición de soldeo
                              → LED de la antorcha → punta 3D → apoyo (z < 2 mm) + trazo en coordenadas de la junta
Antorcha alumno (gatillo, IMU, LED) --USB--> servidor → métricas (lo ya hecho) → tablet (gemelo, fantasma, nota)
Servidor → alcance (IK con la pose 3D de la junta) → "gírala" si no llega
Servidor ⇄ servidor de políticas remoto (GPU nube): SmolVLA multitarea → SO-101 (cámaras cenital + muñeca)
```

- **Reconocer la junta:** con las poses de base y chapa móvil: perpendiculares y la móvil apoyada en el centro de la
  base → T; perpendiculares y unidas por los cantos → esquina; si no, "junta incompleta" (útil para saber si el
  montaje ha fallado). La posición de soldeo sale de la orientación del cordón respecto a la gravedad.
- **El cordón se define en la junta montada**, no en un anclaje fijo: el marco de la pieza (contrato) pasa a
  calcularse de la pose 3D de la base.
- **Fantasma:** la pasada del robot se mide con el mismo seguimiento estéreo (LED de su antorcha) y se guarda como
  referencia de velocidad y ángulo.

## 5. Qué reutilizamos de lo hecho

| Pieza existente | Uso en la v2 |
|---|---|
| `lewelder/metricas.py`, `sintetico.py` | Igual: nota por tramos, avisos, evaluador en vivo; se añade el criterio de apoyo |
| `lewelder/seguimiento.py`, `camara_sintetica.py` | Base del estéreo: se amplía a dos cámaras, ArUco por chapa y triangulación del LED |
| `lewelder/antorcha*.py`, `firmware/` | Igual (gatillo + IMU + LED); la antorcha del robot pasa a tener mango para el soporte |
| `lewelder/servidor.py`, `web/`, `instructor.py` | Se amplían: voz, nuevos modos (pedir, montar, reconocer, demostrar), ficha, fantasma, niveles |
| `sim/` (escena, entorno, cinemática) | Se amplía a la mesa de montaje con chapas imantadas y la antorcha en soporte; el seguimiento del cordón sirve para "demostrar" |
| `robot/` (política, evaluar, entrenar) | Igual flujo con el nuevo vocabulario; el servidor de políticas remoto pasa a ser el camino principal |
| `herramientas/subir_hf.py`, `entrenar_hf_jobs.sh`, `video_demo.py` | Igual |
| Dataset `lewelder_sim_160` | Sirve para la habilidad "suelda la junta" (demostrar) en simulación |
| Repaso, LED del robot solo en huecos, 4 anclajes fijos | **Se retiran** (el código se deja hasta que la v2 lo sustituya) |

## 6. Escalera de alcance

1. **Sábado 12:00:** estéreo calibrado en la mesa real; la tablet reconoce T y esquina montadas a mano; el alumno
   suelda con gatillo + apoyo y recibe nota. Demostraciones de "monta T/esquina" grabadas (dos puestos) y SmolVLA
   entrenando en la nube.
2. **Sábado 20:00:** montaje 8/10 por junta con el VLA; señalar; demostrar la soldadura (VLA, o ACT/replay de
   respaldo) con fantasma; voz → orden → confirmación; "gírala" por voz cuando no llega.
3. **Domingo 10:00:** desmontar y recoger, acercar la antorcha, niveles e insignias, errores típicos; nivel 3: el
   robot gira la junta.

## 7. Criterios de éxito

- Montaje: **8 de 10 por junta** (T y esquina) con la chapa en posiciones nuevas de la zona libre, el sábado 20:00.
- Reconocimiento: tipo de junta correcto en 10/10 montajes completos; pose de la base a < 3 mm y < 2°.
- Apoyo: la punta apoyada (< 2 mm) se distingue de la punta a 5 mm en el 95 % de los fotogramas.
- La parte humana (pedir, reconocer, soldar, nota, certificado) funciona aunque el robot falle (plan B).
- Entrega completa antes del domingo 11:00; pitch ensayado 3 veces, < 5:00.

## 8. Riesgos

| Riesgo | Mitigación |
|---|---|
| Montar es la habilidad más difícil (agarre + giro de 90° + encaje) y es la imprescindible | Imanes con guías que autocentran (el robot solo tiene que dejarla cerca); aleta diseñada para la pinza; dos puestos de grabación; plan B: el alumno monta |
| Inferencia remota: si la wifi falla, el robot se para | Probar la latencia el viernes; móvil con datos como segundo acceso; plan B sin robot listo |
| Muchas habilidades para 48 h de datos | Núcleo de 4 órdenes; el resto solo si el núcleo llega; simulación para tener el flujo practicado |
| Estéreo: calibración y oclusiones (la mano tapa el LED o un ArUco) | Soportes impresos fijos, calibración con el tablero ya generado, pose de las chapas guardada mientras no se mueven |
| Simulación ≠ realidad para el montaje | La simulación practica el flujo y el vocabulario; el dataset bueno se graba allí |
| Voz en una sala ruidosa | Confirmación en la tablet; botones de respaldo con las mismas órdenes |

## 9. Pendiente

- **Errores típicos de la demostración:** cómo los hace el robot (el VLA con la orden "suelda la T demasiado
  rápido", reproducción grabada o solo animación en la tablet). Recomendación: empezar con animación en la tablet y
  reproducción grabada; el VLA con estilos solo si sobra tiempo.
- Organización: wifi para el servidor remoto, 2.º SO-101, criterios del jurado.
- Qué portátiles traen los compañeros (para grabar y para un posible plan de inferencia local).
- Crédito en Hugging Face para entrenar (HF Jobs).
