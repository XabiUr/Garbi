# Garbi · desglose técnico de la solución (v2, 19-11)

Versión corta y ordenada por la demo. El detalle de cada módulo (números, interfaces y pruebas) está en
[especificacion-tecnica.md](especificacion-tecnica.md). La anterior (más larga, con voz, app y aspiradora detalladas) está en el
historial de git (commit df46fca).

Fuente de la rúbrica: `investigacion/guia_so101/RESUMEN.md` (rama `main-9d41os`), guía oficial del 17-11.

## 0. Decisiones cerradas

| Decisión | Valor |
|---|---|
| Tarea de los 5 intentos | El ciclo completo de un agujero (§1), 5 veces seguidas, en 5 sitios de la madera |
| Cierre | Una pasada de limpieza por toda la madera, después del 5.º intento (no puntúa: si falla no cuesta) |
| Qué hace el modelo | Limpiar la zona del agujero cuando el taladro se ha ido |
| Qué modelo | **ACT**. Sin VLA (decisión del usuario, 19-11): los ganadores de Vitoria y Bilbao I usaron ACT |
| Entrenamiento | Todo en la nube (HF Jobs) |
| Ejecución | En el portátil, sin depender de internet |
| Aspiradora | **La lleva el usuario.** Garbi solo da la señal «aspirar sí/no» (§2) |
| Marcadores | Sin ArUco |

## 1. La tarea de la demo: el ciclo de un agujero

| # | Lo que haces | Lo que hace Garbi | Cómo lo sabe | Cómo se mueve |
|---|---|---|---|---|
| 1 | Entras con el taladro | Sale del aparcado y te sigue a ~80 mm, 45 mm por encima | Cámara de arriba: marcador naranja del taladro dentro de la zona | Fijo (cinemática) |
| 2 | Buscas el punto | Te sigue sin estorbar | Ídem, filtrado | Fijo |
| 3 | Apoyas la broca | Se acerca a 30 mm, boca a 15° | Marcador quieto 0,3 s y punta en la cara de la madera (cámara de la muñeca) | Fijo, en dos fases: baja y entra |
| 4 | Taladras | Aspira junto a la broca; guarda el sitio del agujero | Sigue apoyada | Quieto, corrige si la broca se mueve |
| 5 | Levantas la broca | Se separa a la distancia de espera | La punta deja la cara de la madera | Fijo |
| 6 | Sales con el taladro | Espera 1 s y va a la posición de partida sobre el agujero | Marcador fuera de la zona 1 s | Fijo |
| 7 | — | **Limpia la zona del agujero** | — | **ACT**, ~5 s |
| 8 | — | Revisa: si queda viruta, repasa una vez; si no, asiente y aparca | Recuento de viruta (cámara de arriba) | Fijo |

**Acierto:** sin tocar el taladro ni la mano, y la viruta en la zona del agujero por debajo de un umbral.
**Duración:** ~30 s por ciclo; los 5 y el cierre caben en ~3 min.
**Reinicio:** ninguno; el siguiente agujero va en otro sitio de la madera.

**No hace falta saber si estás taladrando:** Garbi aspira mientras la broca esté apoyada. Por eso se quita el micrófono.

**A confirmar el viernes con los mentores:**
- que vale una tarea con partes programadas y una aprendida;
- si la segunda pasada de la revisión cuenta como acierto.

## 2. Arquitectura

```
 cámara de arriba ──┐                                 ┌─> SO-101 (LeRobot 0.7, 30 Hz)
                    ├─> percepción ─> máquina de ─────┤
 cámara de muñeca ──┘   (15 Hz)       estados         ├─> señal «aspirar sí/no» ─> aspiradora (usuario)
                                          │           └─> registro (Rerun) y grabación de episodios
                                          └─> ACT (paso 7)
```

- Un solo proceso en el portátil, dueño del puerto del robot.
- Las dos cámaras son las estándar de la guía: `top` y `wrist` a 640 × 480 y 30 fps.
- **Interfaz con la aspiradora:** Garbi solo emite «encender» y «apagar»; el usuario decide cómo llega (serie al
  Arduino, enchufe inteligente…). Hay que acordar el formato.
- La simulación MuJoCo sigue como gemelo: posturas, alcance, holgura y la maqueta.

## 3. Percepción: técnica y prueba de cada pieza

| Pieza | Técnica | Precisión objetivo | Prueba antes del domingo |
|---|---|---|---|
| Mesa respecto a la cámara de arriba | Esquinas del tapete azul (máscara de color) → homografía con sus medidas 450 × 400 | ±2 mm | Medir 4 puntos con regla |
| Robot respecto a la mesa | La boca del robot va a 9 posturas conocidas; la cámara de arriba la detecta → `solvePnP` | ±3 mm | 5 puntos nuevos con error < 4 mm |
| Madera | Rectángulo más grande dentro del tapete → `minAreaRect`; la ambigüedad de 180° se resuelve por continuidad | ±2 mm, ±1° | Moverla 10 veces |
| Taladro | Marcador naranja fluorescente en la trasera → color, centroide; filtro de mediana 0,3 s | ±10 mm (basta para seguir) | 20 entradas a distintas velocidades |
| Broca (colocarse a 30 mm) | Cámara de la muñeca: barra gris larga vertical, punta en el último tramo de ancho constante; lazo cerrado broca–boca (ya hecho en simulación) | ±2 mm | 20 apoyos con luces distintas, ≥ 18 bien |
| Broca apoyada / levantada | Punta sobre la línea de la cara de la madera (muñeca) y marcador quieto (arriba) | — | 20 apoyos y 20 «en el aire», sin falsos apoyos |
| Agujero | Lo da el paso 4: el punto donde estaba apoyada la broca, guardado en el marco de la madera | ±3 mm | — |
| Viruta | Máscara del serrín claro sobre la madera y el tapete; píxeles en un círculo alrededor del agujero | — | Antes y después en 10 agujeros |

**Luz:** un flexo LED propio, y exposición y balance de blancos fijos en las dos cámaras. Es lo que más rompe la
visión por color.

## 4. Movimiento fijo

- Cinemática inversa del montaje lateral (4 articulaciones + inclinación de la boca), arrancando de la postura
  anterior. Ya hecha en simulación (`garbi/lateral.py`).
- Máquina de estados con filtro e histéresis (`garbi/interactivo.py`): aparcado, seguir, acercarse, acompañar,
  esperar, limpiar, revisar, aparcar.
- **Guardias en cada paso:**
  - holgura ≥ 10 mm con el taladro;
  - borde de la boca por encima de la superficie;
  - velocidad máxima por articulación (75 °/s) y `max_relative_target` de LeRobot.
- La muñeca va fija a 0 y la pinza cerrada: se fuerzan siempre, también sobre la salida de ACT.
- **Pasada final:** zigzag con la boca picada (45-60°) sobre toda la madera.

## 5. El modelo (paso 7)

### 5.1 Qué aprende

- **Entrada:** las cámaras `top` y `wrist` y el estado de las 6 articulaciones.
- **Salida:** posiciones de las articulaciones (chunk de 100 a 30 Hz).
- **Empieza siempre igual:** lo fijo deja la boca en la misma posición respecto al agujero, así que cada episodio es
  corto (3-5 s) y parecido. Es el caso en el que ACT acierta casi siempre.
- **Lo que gana frente al barrido programado:** mira dónde ha quedado la viruta y barre ahí. El barrido programado es
  ciego.

### 5.2 Datos

| Fuente | Cuántos | Para qué |
|---|---|---|
| Barrido programado grabado solo, desde la posición de partida | ~40 | Base consistente; se graba sin nadie al mando |
| Teleoperados con el brazo guía, persiguiendo la viruta que queda | ~20 | Que aprenda a mirar, no solo a copiar el barrido |
| Segunda vuelta tras el primer entrenamiento: casos que falla | ~10-20 | Historia de iteración, la que pregunta el jurado |

- La grabación es automática con el formato LeRobotDataset.
- **Filtro:** solo se quedan los episodios que dejan la zona limpia, según el recuento de viruta.
- Se apunta cuántos episodios se graban, cuántos se descartan y qué se cambia en cada vuelta.
- Se reparten por 6 zonas de la madera (≥ 10 por zona, como pide la guía).
- **Dataset y modelo publicados en Hugging Face**, con su ficha: +3 de bonus.

### 5.3 Entrenamiento (nube) y ejecución (local)

- **Entrenamiento:** `lerobot-train` en **HF Jobs** (`--job.target=a10g-small`), de pago. ACT tarda ~2 h por vuelta.
  El modelo se baja al portátil.
- **Ejecución:** `lerobot-rollout --strategy.type=base` con ACT en el portátil.
- **Evaluación automática:** 10 agujeros con ACT y 10 con el barrido programado; se miden la viruta que queda y el
  tiempo. La tabla sale sola para la presentación.

## 6. Fuera de los 5 intentos (solo si sobra tiempo)

Por orden de valor para el pitch:
1. Respetar tu espacio: si entra la otra mano, se aparta (MediaPipe Hands).
2. «Garbi, limpia aquí» señalando con la broca.
3. Voz, sonidos y app con la luz de estado.

## 7. Qué está hecho y qué falta

| Pieza | Estado |
|---|---|
| Simulación, montaje lateral, posturas, maqueta y visor | Hecho |
| Máquina de estados y cinemática | Hecho en simulación; sin verificar con ruido real |
| Detección de la broca con la cámara de la muñeca | Hecho en simulación |
| Grabador de episodios y ejecución del modelo | Hechos en simulación con el montaje anterior; hay que portarlos |
| Visión sin ArUco (tapete, madera, marcador, viruta) | **Por hacer** |
| Adaptador del robot real | **Por hacer** |
| Boquilla y soporte impresos, tubo por el brazo | **Por hacer** (montaje) |
| Aspiradora | El usuario |

## 8. Calendario con puertas

| Cuándo | Qué | Puerta |
|---|---|---|
| Hoy (19) | Visión sin ArUco con webcam y en simulación; adaptador real; maqueta con el ciclo × 5 + cierre | — |
| Vie tarde | Montar boquilla y tubo; calibrar brazo y cámaras | Par del hombro 60 s < 55 °C; visión con la luz del sitio |
| Vie noche | Ciclo completo con el paso 7 programado en el robot real | 5/5 ciclos sin contacto |
| Sáb mañana | Grabar ~60 episodios, subir a HF, entrenar ACT en HF Jobs | Dataset ≥ 50 a las 12:00 |
| Sáb tarde | Evaluar; segunda vuelta de datos y entrenamiento | ACT ≥ 8/10 a las 20:00; si no, el paso 7 programado y se declara |
| Dom mañana | Ensayos cronometrados de 5 seguidos; vídeo de 1 min | 5/5 en ensayo |

## 9. Riesgos

| Riesgo | Plan |
|---|---|
| Un paso fijo falla y tira el intento | Pocos estados, 20 ciclos de prueba contando fallos, arreglar el que más falla |
| Par del hombro con el tubo | Tubo sin tirón y sujeto a la base, boquilla ≤ 100 g, vigilar temperatura |
| La luz del sitio rompe la visión por color | Flexo propio y exposición fija; umbrales ajustados allí |
| ACT no llega a 8/10 | Más datos teleoperados en los fallos; si no, barrido programado declarado |
| Sin internet en el sitio | Solo el entrenamiento usa la nube; se puede entrenar fuera y traer el modelo |
