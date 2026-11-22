# Paso 7 con ACT en la simulación: tubería de punta a punta (20-11)

Objetivo: validar la técnica de M5 (grabar → filtrar → entrenar → ejecutar como `Habilidad` → evaluar → segunda
vuelta) antes del hackathon, donde se entrenará en HF Jobs a 640 × 480. Todo en CPU (4 núcleos compartidos con otro
proceso de robustez del equipo), sin GPU. Datasets y modelos en el scratchpad, **no** en el repo ni en el Hub.

## Qué se ha construido

| Pieza | Archivo | Qué hace |
|---|---|---|
| Grabador común | `garbi/grabador.py` | `GrabadorLimpiezas`: un episodio por limpieza (top, wrist, state, action, tarea «Clean the hole.»), imágenes reducidas con `INTER_AREA` (como `HabilidadACT`), json de episodios y descartes con su motivo |
| Grabación dentro del ciclo | `garbi/grabador.py` (`GrabadorCiclo`), `garbi/correr.py --grabar RUTA [--grabar-resolucion 160x120]` | Cada LIMPIAR es un episodio; se guarda solo si al REVISAR la percepción da el agujero por limpio; si hay repaso, guardia/respaldo o se corta, se descarta y se apunta. En la simulación apunta también la viruta real. Las cámaras solo se leen en LIMPIAR (también con `--habilidad act`: antes se renderizaba todo el ciclo) |
| «Teleoperación» simulada | `garbi/persecucion.py` (`HabilidadPersecucion`) | Mira la cámara de arriba (calibrada con el tapete), proyecta los píxeles de serrín a la madera y lleva el punto apuntado hacia el montón más cercano a 75 mm/s; sin viruta a la vista, gira a 16 mm del agujero |
| Grabador de demostraciones | `herramientas/garbi_grabar.py` | `--habilidad espiral/persecucion`, `--zonas` (6 zonas: 320-370 y 370-420 mm × 3 sectores de ±20°), `--render 640x480 --resolucion 160x120`, `--radio-plantilla`, `--desplazamiento`, `--correccion MODELO --pasos-act N` (DAgger: ACT N pasos sin grabar y se graba la corrección) |
| Unir datasets | `herramientas/garbi_unir_datasets.py` | `aggregate_datasets` de LeRobot 0.7 + json de descartes |
| Evaluación | `herramientas/garbi_evaluar_paso7.py` | Mismos agujeros (semilla por agujero) para cada habilidad: % recogido, acierto (≤ 2 partículas), borde mínimo, saltos/bordes que cortaría la guardia, contactos, t hasta limpio y **adónde apunta la boca** |
| Entrenamiento en CPU | `herramientas/garbi_entrenar.sh cpu` | La receta de abajo |
| Ajustes | `garbi/habilidad.py` (`limpiar_en_simulacion(estado_orden=True)`) | «state» = la orden anterior, como en `Ciclo._limpiar` y en el dataset |

Decisión: `observation.state` del dataset es **la orden anterior** (lo que el ciclo pasa a la habilidad en LIMPIAR,
`Ciclo.q`), no la postura medida; así entrenamiento y ejecución en el ciclo ven lo mismo. En el robot real la
diferencia es el retraso del servo (~1 paso).

## Datos

Escenario de cada episodio: madera en pose aleatoria (x 350-370, y ±30, ±8°), agujero en una de las 6 zonas por
turnos, 1/3 taladrado (anillo de 36 partículas a 6-22 mm) y 2/3 serrín «con plantilla» (20-36 partículas en un disco
de 15-30 mm desplazado hasta 10 mm del agujero), partida con ruido ±5 mm y ±3°. Render 640 × 480 sin sombras,
dataset a 160 × 120 (vídeo).

| Vuelta | Fuente | Intentos | Guardados | Descartes (motivo) | Tiempo de grabación |
|---|---|---|---|---|---|
| 1 | Espiral, 7 por zona | 42 | 42 | 0 | 865 s (20,6 s/episodio) |
| 1 | Persecución, 4 por zona | 24 | 24 | 0 | 552 s (23 s/episodio) |
| 1 | **Total v1** | 66 | **66** (9 900 fotogramas, 22 MB) | 0 | 24 min |
| 2 | Espiral en las zonas de fallo (4 y 2) | 6 | 6 | 0 | 175 s |
| 2 | Correcciones DAgger (ACT v1 45 pasos → persecución), zonas 4, 2, 0 | 10 | 3 | 7 («ACT ya lo había dejado limpio»: el filtro exigía viruta al empezar) | 304 s |
| 2 | Correcciones DAgger (ACT v1 60 pasos), zonas 4, 2, 0, filtro corregido | 10 | 10 | 0 | 238 s |
| 2 | **Total v2** (v1 + 19) | 92 | **85** | 7 | +12 min |
| — | Ciclo completo `correr --sim --grabar` (2 agujeros, percepción) | 2 | 2 (149 fotogramas cada uno) | 0 | 10 min de simulación del ciclo entero |

Coste de render: 57 ms por paso las dos cámaras a 640 × 480 (33 ms a 160 × 120); un episodio de 5 s tarda ~15 s sin
carga y ~20 s con la máquina compartida. Ninguna demostración se descartó por sucia: en la simulación el cono de
captación (Ø ~49 mm a la altura de la madera) se lleva casi toda la viruta en el primer segundo.

## Entrenamiento

Receta (CPU, 2 hilos): `lerobot-train --policy.type=act`, backbone resnet18 **preentrenado** (ImageNet, se descarga),
`dim_model 256`, `dim_feedforward 1024` (19 M parámetros), `chunk_size 50`, `n_action_steps 25`, lr 1e-4 (backbone
1e-5), lote 8, aumentos de imagen activados, `num_workers 1`.

| Vuelta | Datos | Pasos | Tiempo | l1 (normalizado) al final | Notas |
|---|---|---|---|---|---|
| 1 | v1 (66) | 8 000 desde cero | 111 min (0,8 s/paso) | 0,51 (100) → 0,33 (1k) → 0,20 (2,4k) → 0,155 (4k) → **0,115** (8k) | Sigue bajando: corto de pasos |
| 2 | v2 (85) | +4 000 desde v1 (`--policy.path`: pesos de v1, estadísticas de v2, optimizador nuevo) | 71 min (1,07 s/paso, con la máquina más cargada) | 0,129 (1k) → **0,105-0,110** (4k) | Total 12 000 pasos en ~3 h |

**Problema encontrado (importante para el hackathon):** con `OMP_NUM_THREADS` sin fijar, `lerobot-train` iba a
10-45 s por paso (el modelo solo, 0,6-1,2 s): más hilos de OpenMP que núcleos libres (el dataloader y otro proceso
compitiendo) hacen que los hilos se esperen girando. Con `OMP_NUM_THREADS=2` bajó a 0,75 s/paso. En el portátil
del evento (inferencia) y en cualquier entrenamiento en CPU: fijar los hilos.

## Resultados

Evaluación: 10 agujeros nuevos (semillas 500-509, no grabadas), las mismas posiciones para cada habilidad, una por
zona y 4 repetidas; la habilidad sin guardias (para ver lo que pide), «state» = orden anterior, cámaras a 640 × 480.
«Apunta a»: distancia media del punto donde el eje de la boca corta la madera al agujero (la espiral va de 10 a
30 mm); «> 40 mm»: fracción de pasos apuntando fuera de la zona.

| Habilidad | Aciertos | Recogida media (mín) | t hasta limpio | Apunta a, media (máx) | Pasos > 40 mm | Borde mín | Salto máx por paso | Saltos > 15° / órdenes con borde < 3 mm | Contactos |
|---|---|---|---|---|---|---|---|---|---|
| Espiral programada | **10/10** | 100 % (100 %) | 0,43 s | 20 mm (33) | 0 % | 15,3 mm | 2,4° | 0 / 0 | 0 |
| Persecución («teleoperado») | 10/10 | 100 % (100 %) | — | ~16 mm (—) | 0 % | 12,9 mm | 2,4° | 0 / 0 | 0 |
| ACT v1, 4 000 pasos | 9/10 | 97,5 % (75 %) | 0,60 s | — | — | 9,1 mm | 6,7° | 0 / 0 | 0 |
| **ACT v1**, 8 000 pasos (chunk 50, ejecuta 25) | **9/10** | 98,9 % (88,9 %) | 0,74 s | 25 mm (64) | 13 % | **1,8 mm** | 5,0° | 0 / 0 | 0 |
| ACT v1 + ensemble temporal 0,01 | 8/10 | 98,0 % (88,9 %) | 0,84 s | 21 mm (53) | 6,5 % | 15,7 mm | 2,8° | 0 / 0 | 0 |
| **ACT v2** (+19 episodios, +4 000 pasos) | **9/10** | 95,0 % (50 %) | 0,78 s | 27 mm (74) | 17 % | 6,4 mm | 7,0° | 0 / 0 | 0 |
| ACT v2 + ensemble 0,01 | 9/10 | 94,4 % (47 %) | 0,90 s | 26 mm (77) | 15 % | 12,4 mm | 3,2° | 0 / 0 | 0 |
| ACT v2 en 6 agujeros **grabados** (semillas 0-5) | 6/6 | 100 % | 0,74 s | 23 mm (56) | 4 % | 6,3 mm | 7,7° | 0 / 0 | 0 |

Partículas que quedan por agujero (0-9): ACT v1 `0 0 0 0 4 0 0 0 0 0`; v1 + ensemble `0 0 0 0 4 0 0 0 0 3`;
v2 `0 0 0 0 18 0 0 0 0 0`; v2 + ensemble `0 0 0 0 19 0 0 0 0 1`. El agujero 4 (371, 8 mm, zona 4) falla siempre.

Ciclos completos `correr --sim --habilidad act` (percepción por imágenes, juez simulado, 5 agujeros de `SITIOS_JUEZ`
y pasada final):

| Paso 7 | Aciertos (juez) | Viruta que queda | Contactos | Borde mín | Saltos de la habilidad / pasos al respaldo | Inferencia |
|---|---|---|---|---|---|---|
| Programado (espiral, 5 agujeros) | 5/5 | 0, 0, 0, 0, 0 | 0 | 3,2 mm | — | — |
| ACT v1 (2 agujeros, `python -m garbi.correr --sim --agujeros 2 --habilidad act`) | 2/2 | 0, 1 | 0 | 3,2 mm | — | — |
| ACT v1 (5 agujeros) | **5/5** | 0, 1, 0, 0, 0 | 0 | 3,2 mm | 0 / 0 | 4,2 ms por paso (CPU, 160 × 120) |
| ACT v2 (5 agujeros) | 4/5 | 0, **3**, 0, 0, 0 | 0 | 3,2 mm | 0 / 0 | 4,1 ms por paso |

En el ciclo ACT nunca pidió un salto > 15° ni hizo saltar el respaldo. El fallo de v2 (3 partículas, el juez admite
2) lo dio por limpio la percepción (< 2 % del círculo), así que no repasó. El borde mínimo del ciclo (3,2 mm) es de
otra fase (es el mismo con la habilidad programada).

## Lecturas

1. **La tubería funciona de punta a punta**: grabar en el ciclo o con el grabador → filtrar → unir → entrenar →
   `HabilidadACT` dentro del ciclo con las guardias → evaluar → corregir (DAgger) → reentrenar.
2. **La simulación no discrimina por la viruta**: el cono de captación (14 mm + 0,3 · distancia) se lleva casi toda la
   viruta en el primer segundo desde la misma partida (t hasta limpio 0,4-0,9 s con cualquier habilidad). Por eso
   ACT «acierta» 9/10 aunque su trayectoria sea mucho peor que la espiral. La medida útil ha sido **adónde apunta la
   boca**: la espiral nunca sale de 33 mm; ACT pasa el 13-17 % del tiempo a más de 40 mm y llega a 64-77 mm.
3. **ACT no aprende mal: generaliza poco entre posiciones.** En agujeros grabados va bien (6/6, 4 % de pasos fuera);
   en agujeros nuevos se va de la zona donde los grabados más cercanos quedan a 11-21 mm (el 4: a 371 mm, entre
   ejemplos). La señal de la tarea es pequeña frente a la variación entre posiciones: la espiral entera son unos
   pocos grados de articulación y la desviación típica del estado en el dataset es de 10-13° (l1 final 0,11 ≈ 1,3°
   ≈ 8 mm en la boca: del orden del radio de la espiral). A 160 × 120 el agujero ocupa ~3 píxeles en la cámara de
   arriba, así que tampoco lo localiza por la imagen.
4. **La 2.ª vuelta no arregló el caso que falla** (v2: mismo 9/10, peor en el agujero 4, mejor borde mínimo, 6,4 frente
   a 1,8 mm). Las correcciones se grabaron cerca de los fallos pero no en el sitio exacto, y 4 000 pasos más con un 22 %
   de datos nuevos no bastan para mover una política infraentrenada (l1 de 0,115 a 0,105).
5. **Ensemble temporal**: suaviza (salto máximo 2,8-3,2° frente a 5-7°, el ciclo limita a 2,5°/paso) y aleja menos la
   boca en v1, sin cambiar los aciertos. Cuesta una inferencia por paso (en CPU a 160 × 120, sin problema).
6. **Seguridad**: ACT nunca pidió saltos > 15° ni órdenes con el borde bajo la guardia; sin las guardias, v1 llegó a
   1,8 mm de borde con la postura real (la guardia del ciclo lo habría frenado).

## Lecciones para el hackathon

- **Hilos**: en CPU, fijar `OMP_NUM_THREADS` a los núcleos libres (2 aquí). Sin ello, 10-50 veces más lento.
- **Resolución**: 160 × 120 basta para la tubería, pero desde la cámara de arriba el agujero son ~3 píxeles. En el
  evento, a 640 × 480 en GPU; si hubiera que reducir, recortar la cámara de arriba alrededor de la madera antes que
  escalar, o confiar en la muñeca.
- **Pasos**: con 66 episodios, 8 000 pasos de lote 8 (~6,5 épocas) dejan el l1 todavía bajando (0,115). La referencia
  de M5 (30 000 pasos, lote 8, en A10G) es lo mínimo; vigilar el l1 y evaluar a 10k/20k/30k.
- **Episodios**: más importa **cubrir las posiciones** que el número: ACT acierta donde hay ejemplos y se va entre
  ellos. Con la madera de verdad, agujeros en una rejilla de ~10 mm por toda la zona de taladro (o menos zona). En el
  hackathon (real) habrá además la variedad que no hay en la simulación.
- **Qué grabar en la 2.ª vuelta**: las correcciones **en el sitio exacto** donde falla ACT (DAgger, como
  `lerobot-rollout --strategy.type=dagger`), no «cerca»; y que el filtro admita la corrección aunque ACT ya hubiera
  limpiado (lo que enseña es a no alejarse).
- **Medir lo que importa**: en la simulación, adónde apunta la boca (y el borde mínimo); en el real, el % de viruta
  con la cámara y el tiempo. Un 9/10 de aciertos no basta para decir que ACT hace la tarea.
- **Chunk**: 50 con 25 ejecutadas fue estable; el ensemble temporal (0,01) suaviza y es gratis en tiempo en GPU.
- **Grabar dentro del ciclo** (`--grabar`) da los episodios con la misma partida y el mismo «state» que verá ACT y
  filtra con la percepción: es la forma de grabar en el evento (programado y teleoperado desde la partida del ciclo).
- **Tiempo**: grabar 60 episodios en la simulación ~25 min; en el real, ~20 s de preparar la viruta por episodio
  (M5) más 5 s: ~30 min para 60.
