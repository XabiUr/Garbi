# Garbi · especificación técnica por módulo (19-11)

Detalle de [plan-tecnico.md](plan-tecnico.md).

**Decisiones de partida:**
- sin VLA: el único modelo es ACT, en el paso 7 (limpiar la zona del agujero);
- la aspiradora la lleva el usuario;
- sin ArUco.

**Marco de la mesa:** origen en la base del robot, x hacia la persona, y a la izquierda del robot, z hacia arriba; en
mm. Es el mismo que en la simulación.

## M1. Montaje de cámaras, marcador y luz

| Elemento | Especificación |
|---|---|
| Cámara de arriba (`top`) | Webcam (tipo C920) a 640 × 480 y 30 fps. Va en diagonal desde el lado del robot, como en la simulación: en (260, -420, 780), apuntando a (320, 0, 0). Ve el tapete entero sin que la cabeza de la persona lo tape. Unos 0,9 mm por píxel en la madera |
| Cámara de la muñeca (`wrist`) | La oficial, en su soporte, a la izquierda de la pinza. A 640 × 480 y 30 fps |
| Ajustes de las dos cámaras | Exposición, balance de blancos y foco **fijos**, puestos al arrancar (`v4l2-ctl`, o `CAP_PROP_*` en Windows) |
| Marcador del taladro | Bola naranja fluorescente de Ø35 en un vástago de 25 mm en la trasera del taladro (como en la simulación) |
| Marca de la boca | Anillo de color (verde) en la punta de la boquilla, para calibrar el robot con la cámara de arriba |
| Luz | Flexo LED propio sobre la mesa; ninguna ventana detrás de la cámara |
| Cara de la madera | Vinilo negro mate, para que la viruta clara destaque |

## M2. Calibración (una vez por sesión, < 2 min)

| Paso | Técnica | Salida | Comprobación |
|---|---|---|---|
| 1. Intrínsecas de cada cámara (una vez en casa) | Tablero de ajedrez 9 × 6 de 25 mm, 15 fotos, `cv2.calibrateCamera` | `calib/top.yaml`, `calib/wrist.yaml` | Reproyección < 0,5 px |
| 2. Cámara de arriba respecto a la mesa | Máscara azul del tapete; se ajusta una recta a cada borde y se cortan entre sí para sacar las 4 esquinas; `solvePnP` con sus medidas (450 × 400) | Pose de la cámara de arriba en el marco de la mesa | Medir 4 puntos con regla: ±2 mm |
| 3. Robot respecto a la mesa | El robot lleva la boca a 9 posturas conocidas sobre el tapete; la cámara de arriba detecta el anillo verde y se ajustan (x, y, giro) de la base por mínimos cuadrados | Pose de la base del robot | 5 posturas nuevas: error < 4 mm |
| 4. Brazo | `lerobot-calibrate`; después apagar y encender los servos | — | El aparcado se repite |
| Respaldo del paso 3 | Plantilla impresa que fija la base del robot y la esquina del tapete | — | ±5 mm |

## M3. Percepción (hilo a 15 Hz)

Cada lectura publica un objeto `Escena` con estos campos:

```
t
madera: (x, y, giro) en la mesa | None
taladro: visible, (x, y) del marcador, velocidad, quieto_desde
broca: punta (x, y, z) en la mesa | None, apoyada (sí/no), fuente (arriba | muñeca)
viruta: píxeles de viruta por agujero conocido
```

| Señal | Técnica | Umbral | Por qué así |
|---|---|---|---|
| **Madera** | Dentro de la máscara del tapete, la mancha negra más grande → `minAreaRect`. La ambigüedad de 180° se resuelve quedándose con la orientación más cercana a la anterior | ±2 mm, ±1° | — |
| **Taladro visible** | Máscara naranja (HSV), apertura 5 × 5, la mancha redonda más grande con área en rango | Fuera de la zona de trabajo ≥ 1 s = «ha salido» | — |
| **Posición del taladro** | Rayo de la cámara por el centro de la bola, cortado con un plano a la altura típica de la bola; mediana de 0,3 s | ±15 mm | Basta para seguir a 80 mm |
| **Taladro quieto** | Velocidad del marcador < 5 mm/s durante 0,3 s | — | — |
| **Punta de la broca (de cerca)** | Cámara de la muñeca: barra gris vertical, la punta en el último tramo de ancho constante (ya hecho). **La distancia sale del ancho aparente de la broca de 8 mm**: a 60 mm ocupa ~40 px, así que 1 px ≈ 1,5 mm. Con la pose de la cámara (cinemática del brazo) se obtiene la punta en 3D | ±2 mm | Desde arriba no se puede medir la altura: con una sola cámara el tamaño de la bola da ±25 mm |
| **Broca apoyada** | Punta a ≤ 3 mm de la cara de la madera (z conocida: tapete + 18), durante 0,2 s | Entrar ≤ 3 mm; salir > 8 mm (histéresis) | — |
| **Agujero** | Punta (x, y) al apoyar, guardada en el marco de la madera | ±3 mm | Si se mueve la madera, el agujero va con ella |
| **Viruta** | Máscara de lo claro sobre el vinilo negro, en un círculo de 35 mm de radio alrededor del agujero (imagen de arriba) | Limpio: < 2 % del círculo (umbral a ajustar allí) | — |

## M4. Control fijo (bucle a 30 Hz)

**Envío al robot:** `SO101Follower.send_action` con las 6 articulaciones en grados.
- `wrist_roll` siempre a 0 y la pinza siempre cerrada, también sobre lo que salga de ACT.
- `max_relative_target` activado.

**Estados y transiciones:**

| Estado | Postura | Entra cuando | Sale cuando |
|---|---|---|---|
| APARCADO (respira) | Alto y recogido | Arranque, o fin de la revisión | Taladro visible dentro de la zona → SEGUIR |
| SEGUIR | Boca a 80 mm del marcador, 45 mm sobre la madera, 25° | — | Quieto 0,3 s → PREAPUNTO · fuera 1 s → IR A LIMPIAR (si hay agujeros) o APARCADO |
| PREAPUNTO | 30 mm atrás y 20 mm arriba de la punta estimada, 15° | — | Apoyada → ACOMPAÑAR · se mueve > 12 mm → SEGUIR |
| ACOMPAÑAR | Boca a 30 mm de la broca, 15°; corrige si la broca se desplaza ≤ 5 mm | Apoyada | Punta > 8 mm sobre la madera → SEGUIR |
| IR A LIMPIAR | Posición de partida sobre el agujero: boca a 60°, 35 mm del centro, 30 mm de altura | El taladro salió hace 1 s | Llega → LIMPIAR |
| LIMPIAR | **ACT** durante 5 s | — | Fin de los 5 s → REVISAR |
| REVISAR | Boca alta sobre el agujero | — | Limpio → asiente, siguiente agujero o APARCADO · sucio (1.ª vez) → LIMPIAR · sucio (2.ª vez) → siguiente agujero |

**Señal de la aspiradora:** encendida en ACOMPAÑAR, LIMPIAR y la pasada final; apagada en los demás estados.

**Guardias en cada ciclo del bucle** (si falla una, el robot se queda quieto y vuelve a SEGUIR o se aparca):
- holgura ≥ 10 mm con el taladro, contando el cuerpo y el portabrocas;
- borde de la boca ≥ 3 mm sobre la superficie;
- ≤ 75 °/s por articulación.

**Movimiento:** cinemática inversa del montaje lateral (`garbi/lateral.py`) desde la postura anterior.

**Pasada final:** zigzag de 4 carriles sobre la madera con la boca a 45-60°, a 40 mm/s.

## M5. Paso 7: ACT

| Aspecto | Valor |
|---|---|
| Episodio | Empieza en la posición de partida (M4) y dura **5 s fijos** (150 pasos): no hace falta que el modelo sepa cuándo acabar |
| Entradas | `observation.images.top`, `observation.images.wrist` (640 × 480) y `observation.state` (6) |
| Salida | `action` (6 articulaciones); `wrist_roll` y la pinza se sobrescriben |
| Tarea (texto del dataset) | «Clean the hole.» |
| Variedad al grabar | Posición de partida con ruido de ±5 mm y ±3°: aprende a corregir lo que falle lo fijo |
| Barrido programado (demostraciones automáticas) | Espiral de 3 vueltas de 10 a 30 mm de radio alrededor del agujero, boca a 60°, en 5 s |
| Teleoperados | Con el brazo guía, persiguiendo la viruta que queda; desde la misma posición de partida |
| Viruta para grabar | 1/3 de agujeros taladrados de verdad; 2/3 con serrín guardado, esparcido con una plantilla alrededor de un agujero ya hecho (~20 s por episodio) |
| Volumen | ~40 automáticos + ~20 teleoperados en la 1.ª vuelta; ~10-20 de los fallos en la 2.ª. ≥ 10 por cada una de 6 zonas de la madera |
| Correcciones (2.ª vuelta) | `lerobot-rollout --strategy.type=dagger`: se pausa ACT cuando falla, se corrige con el brazo guía y la corrección se graba (lo recomienda la guía oficial) |
| Filtro | Solo se quedan los episodios que dejan la zona limpia según M3; se apuntan los descartes |
| Entrenamiento | `lerobot-train --policy.type=act` en HF Jobs (`a10g-small`), con aumentos de imagen y ~30k pasos con lote 8 (como referencia: MSN ganó con 20k pasos y lote 4) |
| Ejecución | `lerobot-rollout` en el portátil; ACT calcula un chunk de 100 pasos (~70 ms en CPU) |
| Seguridad | Las guardias de M4 se aplican también a ACT; si salta una, se para el modelo y se pasa al barrido programado |
| Evaluación | 10 agujeros con ACT y 10 con el barrido programado: viruta que queda y tiempo |
| Publicación | Dataset y modelo en Hugging Face con su ficha y las órdenes exactas (+3 y +2 de bonus) |

## M6. Señal de la aspiradora (interfaz con el usuario)

- **Garbi** emite un booleano «aspirar», con los cambios de estado de M4.
- **Formato acordado:** por serie, la línea `1` o `0` cada 200 ms (sirve de latido); sin mensaje durante 1 s, se
  apaga.
- **El usuario** decide el lado de la aspiradora.

## M7. Registro y evidencias

- **Rerun:** las dos cámaras, la `Escena`, el estado y las órdenes en una línea de tiempo.
- **Por ciclo:** un resumen en `registros/AAAAMMDD.jsonl` (acierto, viruta antes y después, duración, por qué falló).
- **Para el jurado:** esos registros son la prueba de fiabilidad. MSN publicó el registro de su demo, y sale en
  nuestra investigación como una de las razones por las que ganó.

## M8. Pruebas mínimas antes de la demo

| Prueba | Criterio |
|---|---|
| Calibración (M2) | Error < 4 mm en 5 puntos |
| 20 apoyos y 20 «en el aire» | Sin falsos apoyos; ≥ 18/20 detectados |
| 20 ciclos completos con el paso 7 programado | Sin contactos; ≥ 19/20 |
| ACT en 10 agujeros | ≥ 8/10 limpios |
| 5 seguidos cronometrados | 5/5 y ≤ 3 min con la pasada final |

## Decisiones del usuario (19-11)

1. **Cara de la madera:** vinilo negro mate (o pintada de oscuro) para contar la viruta.
2. **Anillo verde en la boca** para calibrar el robot con la cámara de arriba.
3. **Soporte de la cámara de arriba:** el que mejor fije la posición de la simulación (flexo, trípode o brazo a la
   mesa).
4. **Señal de la aspiradora:** `1` o `0` por serie cada 200 ms; sin mensaje 1 s, se apaga.
