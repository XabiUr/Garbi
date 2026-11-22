# Aspira · concepto v2, cerrado con el usuario (19-11-2026)

Fuentes de las decisiones: [ideas-tareas.md](ideas-tareas.md) (decisiones del usuario), [tecnicas.md](tecnicas.md)
(técnica por tarea y papel del VLA, apartado 6), [analisis-ganar.md](analisis-ganar.md) (primer análisis). Detalle
técnico previo: [procesos.md](procesos.md), [gestion-robot.md](gestion-robot.md), [hardware.md](hardware.md),
[equipo-rojo.md](equipo-rojo.md).

## Qué es

**Compañero de escritorio** que aspira el polvo mientras trabajas con madera pequeña y maquetas. Un SO-101 con una
boca de aspiración (mango fijo en la pinza, manguera corrugada flexible del usuario) y una aspiradora del usuario
que enciende y apaga un Arduino.

> «Aguántame la aspiradora mientras taladro.» Aspira te acompaña antes de taladrar, se queda quieto mientras
> taladras, aspira solo cuando hace falta y, cuando retiras el taladro, limpia la zona aunque hayas movido la tabla.

Material del usuario: aspiradora, taladro a batería, tablas, herramientas. Lija a mano con taco. Nada de paredes.

## El ciclo de trabajo

| Fase | La persona | Aspira | Técnica |
|---|---|---|---|
| Reposo | — | Aparcado, aspiradora apagada | Programada |
| **Acompañar** | Acerca el taladro y busca el punto | Boca a ~35 mm de la punta de la broca, en el lado libre, sin chocar con la mano ni el taladro | **Programada:** marcador en el taladro + control visual |
| Taladrar | Taladra | Se congela; la aspiradora se enciende por el sonido | Programada (Arduino + sonido) |
| Acabar | Para y retira el taladro | Aspira 2 s más y espera a que el taladro salga de la zona | Programada |
| **Limpiar** | Puede mover la tabla | Va a la viruta del agujero nuevo y hace la pasada | **Aprendida (VLA)** |
| Volver | — | Aparca; aspiradora apagada | Programada |

Regla de seguridad: el robot solo se mueve cuando el taladro está callado.

## El VLA: una sola red, varias órdenes

| Frase fija (inglés) | Qué hace | Cuándo |
|---|---|---|
| `Clean around the new hole.` | Pasada sobre la viruta del agujero nuevo, esté donde esté la tabla | Automática al retirar el taladro |
| `Clean the chips on the mat.` | Va a la viruta suelta en la alfombrilla oscura, fuera de la tabla | El juez: «se me ha caído serrín en la alfombrilla» |
| `Clean along the edge.` | Pasada a lo largo del canto lijado | Automática al retirar el taco, o por voz |
| `Wait by my side.` | Se coloca junto a la zona de trabajo sin estorbar | «Quédate cerca» |

Voz en castellano → LLM → frase fija. La pantalla enseña lo que dijo el juez, la frase que entra a la red y las
cámaras. Línea base programada al lado (solo sabe ir al punto guardado en memoria).

## Percepción

Alfombrilla oscura con 4 ArUco (coordenadas fijas) · contorno de la tabla clara (tamaño, pose; limpiar la tabla
entera con un zigzag programado a petición) · marcador en el taladro (punta de la broca) · sonido · **punto del
agujero guardado en coordenadas de la tabla en el instante del sonido** (resuelve «muchos agujeros» y «tabla movida»)
· viruta clara sobre lo oscuro (la ve el VLA).

## Entrenamiento

Recolector programado que graba episodios de limpieza sobre agujeros reales (memoria + contorno + recorrido) más
20-30 teleoperados por orden para enseñar a recuperarse; cámaras fija y de muñeca; SmolVLA multitarea y un ACT por
orden de respaldo. Medidas: matriz frase × destino, VLA frente a línea base programada, X/10 por orden.

## Tarea puntuada (propuesta)

«El juez elige qué limpiar y dónde (agujero nuevo, viruta en la alfombrilla o canto) y Aspira lo hace en menos de
30 s sin que nadie lo toque.» Cinco intentos independientes.

## Niveles

N1: limpiar el agujero nuevo (VLA) + aspiradora por sonido. N2: acompañar el taladro (programado), las otras órdenes
del VLA, voz. N3: cambio de cabezal en una estación fija (programado), seguir el taco, reconocer la herramienta.

## Restricciones

SO-101 (carga ~150 g recomendada, ±1 cm, banda útil 120-285 mm del eje); equipo de 3 que nunca ha usado un SO-101;
hoy jueves 19 único día de preparación, robot desde el viernes 18:00; rúbrica probable de Robotekin (demo 5 de 5
sin tocar 30 · datos 20 · dificultad 15 · utilidad 15 · innovación 10 · presentación 10); jurado de industria,
centros tecnológicos y universidad vascos que premió a MSN (asistente de soldadura con linterna) hace un mes.
