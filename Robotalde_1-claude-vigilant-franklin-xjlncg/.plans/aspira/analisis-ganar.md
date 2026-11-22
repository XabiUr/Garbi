# Aspira · análisis para ganar el hackathon (19-11-2026)

Concepto acotado con el usuario: compañero de escritorio híbrido. Acompaña el taladro antes de taladrar (sin
chocar), se congela mientras suena, la aspiradora se enciende sola (Arduino + sonido), y al retirar el taladro limpia
la zona aunque se haya movido la tabla. Lija a mano con taco. Madera pequeña y maquetas. Taladro a batería.

## 1. Contra la rúbrica probable (Robotekin, mismo operador)

| Criterio | Puntos | Estimación [est.] | Qué lo sube | Qué lo baja |
|---|---|---|---|---|
| Demo 5 de 5 sin tocar | 30 | 18-24 | Tarea puntuada estática (limpiar el agujero) y control programado donde hace falta exactitud | Demasiados subsistemas encadenados en un intento (visión, sonido, Arduino, VLA) |
| Datos y entrenamiento | 20 | 12-16 | Historia clara de qué se aprende y por qué; matriz de pruebas; corrección de fallos | Si casi todo es programado, poco que contar |
| Dificultad | 15 | 11-13 | Ciclo completo con fases, seguimiento reactivo, memoria de agujeros | — |
| Utilidad | 15 | 12-14 | Necesidad evidente, física de la captación, comparativa visible con y sin | Ruido y polvo en la sala si no dejan |
| Innovación | 10 | 7-9 | Nadie lo ha hecho; sensores y actuador propios (sonido, aspiradora) | Parecido con MSN |
| Presentación | 10 | 7-9 | Se entiende en 5 s; el juez taladra; mesa limpia al final | — |
| **Total** | 100 | **67-85** | | |

Referencia: en la ronda anterior ningún concepto pasó de 70 con evaluadores estrictos. Aspira entra por arriba en
utilidad y dificultad; el riesgo está en la demo y en la parte aprendida.

## 2. Puntos fuertes

1. **Necesidad evidente** que el jurado ha vivido (polvo al taladrar) y apaño reconocible.
2. **Hueco real:** ningún vídeo de un robot que lo haga (ni SO-101 ni otros brazos).
3. **Se siente un compañero:** reacciona a lo que haces, no espera órdenes. Es lo que más premia este jurado
   (humano en el centro, como MSN).
4. **Física que respalda el valor:** la captación cae con la distancia; el apaño falla por eso, el robot no.
5. **Resultado visible y medible:** mesa limpia frente a mesa sucia, aspiradora que se enciende sola.
6. **Híbrido inteligente**, el patrón que ya ganó en Vitoria.
7. **Material del equipo:** aspiradora, taladro, tablas; sin compras críticas.

## 3. Puntos débiles

| # | Debilidad | Gravedad | Mejora propuesta |
|---|---|---|---|
| 1 | **«Es lo de Vitoria con una aspiradora»**: mismo banco, mismo seguimiento de herramienta, mismo híbrido | Alta | Enseñar el **ciclo de trabajo completo con memoria** (acompaña, se congela, aspira, recuerda el agujero, limpia aunque muevas la tabla) frente a una sola acción; y un actuador y un sensor propios (aspiradora, sonido). Frase: «MSN alumbra; Aspira entiende el proceso» |
| 2 | **VLA poco visible** si el seguimiento y la limpieza se programan | Alta | Dar al VLA lo que depende del aspecto: **limpiar el montón de viruta** (forma y sitio cambian) y **qué hacer según la herramienta que ve** (taladro, taco, destornillador). Medirlo frente a una línea base programada |
| 3 | **Muchos subsistemas** para un equipo que nunca ha usado un SO-101 | Alta | Escalera estricta: N1 limpieza (puntuada) sola funciona; acompañar y Arduino se suman encima. Cada capa se puede apagar sin romper la demo |
| 4 | **Permiso de ruido y polvo** en la sala | Media | Correo hoy; madera blanda, ráfagas cortas, aspiradora siempre encendida durante el taladrado; plan con polvo de prueba |
| 5 | **Contraste** viruta-tabla para ver el agujero y la viruta | Media | Alfombrilla oscura y tablas de pino claro: la viruta clara cae sobre lo oscuro alrededor de la tabla; o cara de la tabla tintada para la demo |
| 6 | **Duración de cada intento** (acompañar + taladrar + limpiar) | Media | La tarea puntuada es solo la limpieza (~20-30 s); taladrar lo hace la persona entre intentos |
| 7 | **Seguridad** del brazo junto al taladro | Media | El robot solo se mueve con el taladro callado; distancia mínima; `/reset` como parada |
| 8 | **Marcador en el taladro** puede parecer trampa | Baja | Se dice: «el taladro lleva una etiqueta, como las herramientas conectadas de taller»; un modelo de detección es el siguiente paso |

## 4. Lo que haría ganar (prioridades)

1. **Que el ciclo completo salga fluido delante del jurado**, con el juez taladrando.
2. **Que la parte aprendida se vea y se mida**: limpieza de la viruta donde esté, con matriz y línea base.
3. **Que la diferencia con MSN se entienda en 5 segundos**: ciclo con memoria y actuador propio.
4. **La comparativa visual** con y sin Aspira (mitad de la tabla).
5. **5 de 5 en la tarea puntuada**, que sea corta y estática.

Probabilidad de podio [est.]: 25-35 % si la limpieza aprendida llega a ≥ 8/10 y el ciclo sale fluido; 10-15 % si
solo funciona la parte programada.
