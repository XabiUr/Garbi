# Garbi · situaciones, tareas y postura exacta en cada una (borrador para acordar, 20-11)

Simulación forzada, sin aprendizaje: en cada situación se coloca la escena (madera, taladro, viruta) y la postura que
toca. Se generan así:

```bash
python -m garbi.situaciones
```

```bash
python -m garbi.guion
```

La primera da las imágenes (`situaciones/NN_*.jpg`); la segunda, el vídeo de una sesión completa. En 3D, en el visor
(`herramientas/ver_garbi.bat`): → ← recorren las situaciones y G reproduce el guion.

## Montaje (decisiones del usuario, 20-11)

- **Boquilla:** rígida, Ø30 × 40, al final de un tubo corrugado de desagüe. Va por el costado derecho de la pinza,
  con la boca algo por delante de las puntas de las mordazas, a 70 mm del eje de la pinza y abierta 15° hacia fuera.
- **Tubo:** baja por el costado derecho del brazo pasando por el eje de cada articulación y sale por detrás de la
  base. Sin pértiga.
- **Muñeca:** fija (`wrist_roll` = 0), para que el tubo no se retuerza. La mordaza móvil va cerrada.
- **Cámara de la muñeca:** la oficial, en su soporte, a la izquierda. A 70 mm la cámara ve la boca y la broca por
  fuera de las mordazas; a 52 mm las mordazas tapaban la broca.
- **Ataque:** la boca siempre casi horizontal, un poco picada (10-25°; en la práctica 15°), nunca en perpendicular.

## Área de trabajo

- **Mesa:** 1200 × 600 × 750 mm.
- **Robot:** en el borde de atrás, de frente a la persona.
- **Tapete:** 450 × 400, desde 110 mm delante del robot.
- **Madera:** 300 × 200 × 18, lejos del robot, centrada a ~360 mm (de 260 a 460).
- **Alcance:** con la boca a 10-25°, Garbi acompaña al taladro **desde ~290 mm del robot hasta al menos 440 mm, en
  todo el ancho de la madera**, con 22 mm de holgura con el taladro. Más cerca no puede atacar casi en horizontal.

## Comportamiento interactivo (petición del usuario, 20-11)

Garbi reacciona al taladro en cada fotograma; no es una secuencia cerrada (`garbi/interactivo.py`).

| Lo que haces | Lo que hace Garbi |
|---|---|
| Entra el taladro en escena | Sale del aparcado y lo sigue a ~80 mm de la broca y 45 mm sobre la madera, sin estorbar |
| Mueves el taladro con la broca en el aire | Lo sigue, con la velocidad de cada articulación limitada (movimiento suave) |
| Apoyas la broca y la dejas quieta 0,3 s | Se acerca a 30 mm, casi horizontal (15°), y enciende la aspiradora |
| Taladras (broca apoyada ≥ 1 s) | Aspira y apunta el agujero en el marco de la madera |
| Levantas la broca o te mueves | Se separa a la distancia de espera y te sigue |
| Sacas el taladro de escena | Espera 1,5 s aspirando, limpia **todos** los agujeros con la boca picada (45-60°) y aparca |
| Mueves la madera antes de que limpie | Los agujeros van con la madera: los limpia en su sitio nuevo |

Guion de prueba (`python -m garbi.guion`, o Enter en el visor):
1. Entras con el taladro.
2. Buscas el punto con la broca en el aire.
3. Taladras tres agujeros, levantando la broca y moviéndote entre uno y otro.
4. Te vas.

Resultado en la simulación: 108 virutas recogidas, ninguna en la madera, 37 s de sesión.

## Situaciones

| S | Situación | Qué hace Garbi |
|---|---|---|
| 1 | Reposo | Aparcado alto y recogido |
| 2 | Entra el taladro | Lo sigue a distancia sin estorbar |
| 3 | Apoyas la broca | Se acerca a 30 mm y aspira |
| 4 | Taladrando | Junto a la broca, aspirando; apunta el agujero |
| 5 | Levantas la broca y te mueves | Se separa y te sigue |
| 6 | Taladro fuera de su alcance (< ~280 mm del robot) | Aparcado y aviso |
| 7 | Sale el taladro | Limpia todos los agujeros, más picado, y aparca |
| 8 | Mueves la madera antes de que limpie | Limpia cada agujero en su sitio nuevo |
| 9 | «Limpia el tapete» | Barre el montón de serrín a su alcance |
| 10 | «Limpia la madera» | Barrido en zigzag con la boca picada |
| 11 | «Retírate» | Se separa y aparca; apaga la aspiradora |
| 12 | No ve la broca | Se queda a la distancia de espera y pide enderezar el taladro |
| 13 | Emergencia | Quieto, aspiradora apagada |

## Postura exacta en cada situación (calculada en la simulación)

| S | Situación | Estado | Aspiradora | Articulaciones (pan, lift, elbow, flex) ° | Boca (x, y, z) mm | Inclinación | Holgura | Cámara ve boca / broca |
|---|---|---|---|---|---|---|---|---|
| 1 | Reposo | aparcado | no | 0, -100, 60, -60 | — | — | — | — / — |
| 2 | Entra el taladro: lo sigue a distancia | seguir | no | -24, -69, 84, 10 | (261, 30, 65) | 25° | 70 mm | sí / sí |
| 3 | Apoyas la broca: se acerca y aspira | acompanar | sí | -21, 9, 70, -65 | (310, 37, 35) | 15° | 22 mm | sí / sí |
| 4 | Taladrando | acompanar | sí | -21, 9, 70, -65 | (310, 37, 35) | 15° | 22 mm | sí / sí |
| 5 | Levantas la broca y te mueves: te sigue | seguir | no | -10, -21, 78, -42 | (300, -22, 65) | 15° | 72 mm | sí / no |
| 6 | Taladro fuera de su alcance | aparcado | no | 0, -100, 60, -60 | — | — | 148 mm | — / — |
| 7 | Sale el taladro: limpia todos los agujeros | limpiar | sí | -21, 15, -9, 56 | (323, 41, 35) | 60° | — | sí / — |
| 8 | Mueves la madera antes de que limpie | limpiar | sí | -15, 24, -21, 60 | (340, 15, 35) | 60° | — | sí / — |
| 9 | "Limpia el tapete" | limpiar | sí | 20, 21, 4, 21 | (319, -185, 17) | 45° | — | sí / — |
| 10 | "Limpia la madera" | limpiar | sí | -3, 22, -18, 59 | (332, -56, 35) | 60° | — | sí / — |
| 11 | "Retirate" | aparcar | no | 0, -100, 60, -60 | — | — | 200 mm | — / — |
| 12 | No ve la broca | seguir (esperando) | no | -24, -69, 84, 10 | (261, 30, 65) | 25° | 51 mm | sí / no |
| 13 | Emergencia o fallo del Arduino | congelado | no | -21, 9, 70, -65 | (310, 37, 35) | 15° | 22 mm | sí / sí |

## Pendiente

1. **Broca apoyada en el robot real:** en la simulación se sabe la altura de la punta; con cámaras hay que detectarla
   con la cámara de la muñeca (punta tocando la madera) o por el tamaño de la bola en la cámara de arriba.
2. **Siguiendo a distancia:** en algunos puntos la cámara de la muñeca no ve la broca; al acercarse sí.
3. **Orquestador autónomo:** `robot_vivo`, el escenario y las demostraciones siguen con el montaje anterior; hay que
   portarlos al lateral cuando cerremos las situaciones.
4. **Decisiones abiertas:**
   - Taladrar o esperar: ¿Garbi tiene que distinguirlos?
   - Lijado a mano: ¿hay situación de lijado?
   - Avisos: ¿voz, luz, pantalla o sonido?

## Experiencia de uso (decisiones del usuario, 20-11)

| Mejora | Decisión | En la maqueta |
|---|---|---|
| Luz de estado | En la app, no en la boquilla | Panel con un círculo de color: gris reposo, azul te sigue, verde aspira o limpia, ámbar te deja sitio, cian revisa |
| Mirada anticipatoria | No | — |
| Respeta tu espacio | Sí | Tu otra mano entra a recolocar la madera: Garbi se aparta, dice «te dejo sitio» y vuelve cuando te vas |
| Pantalla de resultado | No | — |
| Órdenes por voz y sonidos | Sí | «Garbi, limpia aquí»; sonidos al seguir, acercarse, ceder, entender y terminar (en Windows suenan en el visor) |
| Micro-movimiento en reposo | Sí | Garbi «respira» mientras espera |
| Gesto de «hecho» | Sí: revisa los agujeros y la limpieza | Pasa por encima de cada agujero y asiente dos veces: «todo limpio» |
| Señalar con la broca | Sí | Mantienes la broca encima del serrín, se lo pides y lo barre |
| Modos | No | Siempre limpia todos los agujeros al sacar el taladro de la cámara de arriba |
