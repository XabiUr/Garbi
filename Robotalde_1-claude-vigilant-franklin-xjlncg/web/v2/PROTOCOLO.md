# Protocolo v2 · servidor ⇄ tablet arcade

La tablet v2 (`web/v2/index.html`) habla con el servidor por **WebSocket `/ws2`**: JSON, un objeto por mensaje (o una
lista de objetos, que la tablet procesa en orden). La tablet es "tonta": pinta lo que le llega y manda lo que toca el
juez. Quien decide la pantalla, los puntos y el resultado es el servidor (tarea 6b). La maqueta
(`?maqueta=1`, `web/v2/maqueta.js`) emite exactamente estos mensajes y sirve de referencia ejecutable.

Unidades: mm, s y grados. Marco del **cordón**: `x` de 0 a 120 en el sentido de avance (24 tramos de 5 mm, el tramo
`i` cubre `[5i, 5i+5)`), `y` desvío lateral (+ hacia la chapa móvil), `z` altura de la punta sobre la cara de la base.
Las medidas de las piezas están en `web/v2/contrato.js` (copia a mano de `lewelder/contrato.py`).

## Servidor → tablet (campo `tipo`)

| `tipo` | Campos | Qué hace la tablet |
|---|---|---|
| `pantalla` | `nombre`: `atraccion` \| `pedir` \| `montaje` \| `reconocer` \| `demostracion` \| `cuenta_atras` \| `ronda` \| `resultado` \| `iniciales` \| `ranking` \| `plan_b` | Cambia de pantalla (barrido de 380 ms). Al entrar en `ronda` pone a cero puntos, tramos y carrera. |
| `personaje` | `frase`, `emocion`: `alegre` \| `chulo` \| `picado` \| `sorprendido` \| `serio`, `nombre?` (por defecto "Chispas") | Bocadillo + cara de Chispas y la dice con `speechSynthesis` (es-ES, rate 1.12, pitch 1.35) si no hay silencio. En `ronda` y `cuenta_atras` el bocadillo se oculta a los 3,5 s. |
| `orden_propuesta` | `texto_oido`, `orden`, `pregunta`, `botones?` (`[{orden, etiqueta, pregunta}]` para aclarar) | Tarjeta "HE OÍDO «…» · ¿Monto una unión en esquina?" con SÍ / NO (o un botón por opción). Solo hace falta si la voz no pasa por `POST /api/voz` (ver abajo). |
| `robot` | `tarea`, `fase` (`buscando` \| `cogiendo` \| `girando` \| `encajando` \| `soldando`), `progreso` 0-1 **de toda la tarea**, `imagen_jpeg_base64?` | En `montaje`: lista de fases, barra y pose de la chapa en el gemelo (0-0,2 tumbada, 0,2-0,45 la levanta, 0,45-0,75 la gira, 0,75-1 la encaja); la imagen sale en "DETALLE A". En `demostracion`: la antorcha del robot recorre el cordón (`x = progreso · 120`) dejando el fantasma en discontinuo. A 5-10 Hz basta; la imagen, a 1-2 Hz. |
| `junta` | `junta`: `t` \| `esquina` \| `incompleta`, `posicion_soldeo` ("PB"), `confianza` 0-1, `motivo?`, `ficha`: `{titulo, para_que, donde_se_usa, angulo}` | Sello "UNIÓN EN ESQUINA · PB", símbolo ISO 2553 con la flecha al cordón del gemelo y la ficha de 3 líneas. **Ojo:** el tipo de junta va en el campo `junta` (no en `tipo`, que es el del mensaje). |
| `alcance` | `llega`, `texto?` ("gírala 90° hacia mí"), `giro_grados?` | `llega: false` → anotación roja con flecha de giro; `true` → "✓ Al alcance del robot". |
| `fantasma` | `tramos`: 24 × `{x0, velocidad, angulo}`, `duracion` | Se guarda: en la ronda el fantasma avanza con estas velocidades desde el **primer instante con gatillo + apoyo** del juez (reloj de la carrera en la tablet). |
| `muestra` | `t`, `x`, `y`, `z`, `apoyada`, `gatillo`, `calidad`: `bien` \| `regular` \| `quemado` \| `suelto` | ~30 Hz. Antorcha y arco en el gemelo, chispas si `gatillo && apoyada`, tramo `floor(x/5)` pintado con la **peor** calidad vista mientras se suelda (provisional), marca "TÚ" en la tira, zumbido del arco. Gatillo sin apoyo > 0,25 s → "¡APOYA LA ANTORCHA!". `suelto` = no deja cordón. |
| `puntos` | `total`, `combo`, `multiplicador`, `evento?`: `{texto, tipo: bueno \| malo \| epico}` | HUD. El evento sale como sello de revisión: `bueno` ("COMBO x4", ámbar + arpegio), `malo` ("¡QUEMADO!", rojo + zumbido + destello + temblor), `epico` ("¡ADELANTAS AL ROBOT!", grande + fanfarria corta). Mandar `puntos` cuando cambie algo, no a 30 Hz. |
| `fantasma_vivo` | `ventaja_mm` (= x_juez − x_fantasma), `ventaja_s`, `va_ganando`: `juez` \| `robot` | Panel "VA GANANDO". 4 Hz basta. La cota "Δ 12 mm" del gemelo la calcula la tablet con su reloj. |
| `resultado` | `puntos`, `nota` (0-10), `metricas`: `{cobertura 0-1, ritmo 0-1, quemados n, desvio mm, angulo °, apoyo 0-1}`, `tramos`: 24 × calidad \| null, `gana_al_robot`, `record`, `entra_en_ranking`, `insignia?`: `{nombre, nivel}` | Contador de puntos (1,6 s), tabla de tolerancias, tira final, tampón "HAS GANADO AL ROBOT" / "GANA EL ROBOT" (+ risa), "¡NUEVO RÉCORD!" con fanfarria, insignia en sello circular. Si una métrica viene como `{texto, ok, tolerancia}` se pinta tal cual; si es número, la tablet aplica las tolerancias del contrato (≥ 90 %, ≥ 70 %, 0, ≤ 5 mm, 45° ± 15°, ≥ 90 %). Si no se manda `pantalla`, `resultado` lleva a la pantalla de resultado. |
| `ranking` | `top`: `[{iniciales, puntos, junta}]` (hasta 10), `posicion_nueva?` (1-10) | Lista de piezas. En `atraccion` rota de 5 en 5; en `ranking`, la nueva fila parpadea. Mandarlo al conectar y cada vez que cambie. |

## Tablet → servidor (campo `orden`)

| `orden` | Campos | Cuándo |
|---|---|---|
| `jugar` | — | Toque en cualquier sitio de la atracción, o "JUGAR OTRA VEZ" en el ranking. |
| `voz` | `texto` | Solo si `POST /api/voz` falla: el servidor interpreta y responde con `orden_propuesta`. |
| `confirmar` | `si`, `orden_confirmada?` | SÍ / NO de la tarjeta. Con `si: true` va la orden del vocabulario (`ORDENES` del contrato). |
| `iniciales` | `texto` (3 letras A-Z, Ñ) | "FIRMAR ✓" en la pantalla de iniciales. |
| `monto_yo` | — | "LA MONTO YO" en el montaje (plan B): el servidor manda `pantalla: plan_b` y, cuando ve la junta montada, `junta` + `pantalla: reconocer`. |
| `reiniciar` | — | Volver a la atracción (reservado; la tablet aún no lo muestra). |

## Voz (tarea 3)

El micrófono usa la Web Speech API (es-ES) y la frase se interpreta con **`POST /api/voz`** (`lewelder/voz.py`), que
devuelve `{orden, pregunta, confirmable, aclaracion, botones, respuesta, personaje}`. La tablet dice la `respuesta`
como Chispas y, si es `confirmable`, abre la tarjeta; al tocar SÍ manda `confirmar`. Si `/api/voz` no responde, manda
`voz {texto}` por el WebSocket. Sin reconocimiento en el navegador, los dos ejemplos ("¡Móntame una T!",
"¡Móntame una esquina!") hacen lo mismo que hablar.

## Ritmo de una ronda (lo que hace la maqueta)

```
pantalla atraccion + ranking + personaje        (hasta que llega `jugar`)
pantalla pedir → (tablet: /api/voz) → `confirmar {si:true, orden_confirmada}`
pantalla montaje → robot {fase, progreso} a 10 Hz (+ imagen a 2 Hz) → personaje "¡Esquina servida!"
pantalla reconocer → junta → alcance → personaje
pantalla demostracion → robot {fase: soldando, progreso} → fantasma → personaje (reto)
pantalla cuenta_atras  (la tablet cuenta 3-2-1-¡SUELDA! sola en 3 s; mandar `ronda` a los ~3,6 s)
pantalla ronda → muestra 30 Hz + puntos al cerrar cada tramo + fantasma_vivo 4 Hz
resultado (con o sin `pantalla resultado`) → pantalla iniciales → `iniciales` → ranking {posicion_nueva} → pantalla ranking
```

Puntuación de la maqueta (orientativa para 6b): `bien` +100 × multiplicador y combo +1; `regular` +40 × mult.;
`quemado` −200 y combo a 0; `suelto` combo a 0; multiplicador = min(5, 1 + combo // 4); evento "COMBO xN" cada 4
tramos seguidos; +500 al terminar si gana al robot.
