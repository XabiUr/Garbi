# Entrenar, evaluar y desplegar las políticas del robot soldador (SmolVLA, ACT y replay)

Recetas para LeRobot 0.7 con el dataset de demostraciones simuladas (`sim/demostraciones.py`) o con el grabado con
el brazo guía. Los dos datasets tienen el mismo formato: `robot_type = so101_follower`, `observation.state` y `action`
con `shoulder_pan.pos … gripper.pos` (grados; pinza 0-100), cámaras `observation.images.cenital` y
`observation.images.muneca`, 30 fps y la instrucción del contrato como `task`
(`suelda la unión recta del anclaje B`, `suelda la unión en T del anclaje D`…).

Todos los comandos se lanzan desde la raíz del repositorio con el entorno del proyecto:

```bash
export PYTHONPATH=$PWD MUJOCO_GL=egl     # MUJOCO_GL=egl para renderizar sin pantalla
```

Flujo completo: **grabar (con filtro de calidad) → entrenar ACT y SmolVLA → evaluar (tabla VLA/ACT/replay) →
desplegar en el servidor con `--robot mujoco`**. Todo probado de punta a punta en CPU el 16-11-2026.

## 0. v2 · dataset multitarea de la mesa de montaje (una sola política para las 4 órdenes del núcleo)

Escena: `sim/montaje.py` con las piezas reales del CAD (`hardware/v2/cad/stl/`), imanes que cierran la junta y la
antorcha en su soporte. Demostraciones guionizadas: `sim/demos_montaje.py`. Mismo formato que la v1 (`so101_follower`,
`observation.state`/`action` en grados y pinza 0-100, cámaras `cenital` y `muneca`, 30 fps); el `task` es la orden
exacta del vocabulario (`monta una unión en T`, `monta una unión en esquina`, `señala el cordón`,
`coge la antorcha y suelda la junta`). Solo entran los episodios que terminan con `exito` (la junta cerrada, el
cordón señalado al 80 % a < 15 mm, o soldado entero a ±5 mm con la antorcha devuelta al soporte); si la IK no llega
se reintenta con otra semilla. Registro en `<salida>/exitos.json` (todas) y `notas.json` (nota de las soldaduras).

```bash
# pequeño de validación: 4 por orden (16 episodios, ~25 min en CPU con render 256x192)
.venv/bin/python -m sim.demostraciones montaje --por-orden 4 \
    --salida datos/lewelder_v2 --repo-id local/lewelder_v2 --sobrescribir
# grande para entrenar en la nube: 50 por orden (200 episodios; en tandas paralelas con --semilla distinta)
.venv/bin/python -m sim.demostraciones montaje --por-orden 50 --semilla 1000 \
    --salida datos/lewelder_v2_200 --repo-id Izaguirre97/lewelder_v2_200
# solo algunas órdenes: --ordenes "monta una unión en T|monta una unión en esquina"; --ruido 0 = guion exacto
```

Duración de cada episodio (16-11-2026): simulada, montar la T 21,5 s, la esquina 19 s, señalar 19 s, coger la
antorcha y soldar 53,5 s; en CPU con el render de 256x192, 33 s, 30 s, 33 s y 86 s (sin render, 1,5-2,5 s). El
pequeño de 4 por orden tarda unos 13 min. Con ruido (por defecto) ~1 de cada 6 intentos no tiene IK o no cierra la
junta y se reintenta con otra semilla.

Entrenar, 2 pasos para probar el flujo (probado aquí con batch 2: SmolVLA 2,5 s/paso y ACT 0,7 s/paso en CPU, más
la carga; el checkpoint de SmolVLA ocupa 1,3 GB: quita `--save_checkpoint=false` solo si quieres guardarlo). SmolVLA
lee la orden y ACT no:

```bash
HF_HUB_OFFLINE=1 .venv/bin/lerobot-train \
    --dataset.repo_id=local/lewelder_v2 --dataset.root=datos/lewelder_v2 \
    --policy.path=lerobot/smolvla_base --policy.device=cpu --policy.push_to_hub=false \
    --rename_map='{"observation.images.cenital": "observation.images.camera1", "observation.images.muneca": "observation.images.camera2"}' \
    --policy.empty_cameras=1 \
    --batch_size=2 --steps=2 --num_workers=0 --log_freq=1 --save_checkpoint=false \
    --output_dir=salidas/entreno_v2_smolvla --job_name=smolvla_v2_prueba
.venv/bin/lerobot-train \
    --dataset.repo_id=local/lewelder_v2 --dataset.root=datos/lewelder_v2 \
    --policy.type=act --policy.device=cpu --policy.push_to_hub=false \
    --batch_size=2 --steps=2 --num_workers=0 --log_freq=1 --save_checkpoint=false \
    --output_dir=salidas/entreno_v2_act --job_name=act_v2_prueba
```

En GPU: las de la sección 3 con `--dataset.repo_id=Izaguirre97/lewelder_v2_200` (SmolVLA multitarea es la principal;
ACT, sin lenguaje, sirve de respaldo entrenado solo con los episodios de una orden: `--dataset.episodes=[...]`).
Antes de imprimir piezas: `python -m sim.validar_montaje` (informe en `hardware/v2/validacion_sim.md`).

## 1. Grabar el dataset simulado con el filtro "aprende del mejor"

Cada demostración se puntúa con `evaluar_pasada` (las mismas métricas que al alumno, nivel oficial ±5 mm) sobre la
punta de la antorcha con el gatillo apretado durante el cordón. Con `--umbral-nota` solo entran las que llegan; la
nota de todas (también las descartadas) queda en `<salida>/notas.json`. `--incluir-malas N` graba además N
demostraciones malas a propósito (temblorosa, con dos paradas, desviada 7,5 mm, demasiado rápida) para que el
filtro tenga algo que descartar.

```bash
# 8 buenas (4 anclajes x 2 tipos) + 4 malas, solo entran las de nota >= 9 (256x192, ~70 s por demostración en CPU)
.venv/bin/python -m sim.demostraciones --episodios 8 --incluir-malas 4 --umbral-nota 9 \
    --salida datos/lewelder_sim --repo-id local/lewelder_sim --sobrescribir
# al final: "filtro (nota >= 9.0): N guardadas, M descartadas (k de 4 malas a propósito, j buenas)"
```

Opciones útiles: `--anclajes A,B`, `--tipos recta`, `--velocidad 5` (mm/s), `--ruido 0` (guion exacto),
`--resolucion 320x240`, `--sin-sombras` (render el doble de rápido; las imágenes cambian, no mezclar con un dataset
con sombras), `--nivel maestro` (puntuar a ±3 mm).

Notas medidas en simulación: las buenas sacan **9,8**; las malas, temblorosa 6,8-7,2, con paradas 8,1, desviada 6,0
(hueco de 40 a 80 mm) y rápida 8,4. Por eso el umbral recomendado es **9** (`UMBRAL_NOTA`). Con el brazo guía real
las notas serán más bajas: mira `notas.json` de una primera tanda y pon el umbral para quedarte con el mejor ~70 %.

### Dataset grande para entrenar de verdad

- **15-20 demostraciones buenas por anclaje y tipo** → 4 x 2 x 20 = **160 episodios** (más variedad, no más pasos).
  Con el robot real: 10-15 por combinación es el mínimo razonable; empieza por la recta en 1-2 anclajes (escalera de
  alcance de la spec) y sube.
- En simulación: 160 episodios x ~70 s = ~3 h de CPU en un solo proceso. Se puede grabar en tandas paralelas con
  `--semilla` y `--salida` distintas (una por núcleo) y entrenar con cada una o unirlas con
  `lerobot-edit-dataset --operation.type merge` (no probado aquí).
- Con más resolución (`--resolucion 320x240`) las cámaras se parecen más a las reales, pero el render y el
  entrenamiento cuestan más.

```bash
.venv/bin/python -m sim.demostraciones --episodios 160 --incluir-malas 16 --umbral-nota 9 \
    --salida datos/lewelder_sim_160 --repo-id Izaguirre97/lewelder_sim_160 --semilla 1000
```

## 2. Probado aquí en CPU (4 núcleos, sin GPU): entrenamientos cortos de punta a punta

Medido el 16-11-2026 con el dataset de 8 episodios (9 248 fotogramas). **Un solo trabajo pesado a la vez**: con
otro proceso de PyTorch o MuJoCo en paralelo los hilos se pisan y un paso pasa de 3,7 s a 20-40 s.

| Política | batch | pasos | s/paso (CPU) | tiempo total | loss inicial → final | parámetros entrenables |
|---|---|---|---|---|---|---|
| ACT (desde cero, ResNet18 ImageNet) | 8 | 600 | **1,55-1,7** | 28 min (con otras pruebas a la vez; solo, ~17 min) | 5,1 → 2,1 | 52 M |
| SmolVLA (desde `lerobot/smolvla_base`) | 4 | 200 | **3,6-3,8** | 16,5 min | 0,50 → 0,07 | 100 M de 450 M |

ACT:

```bash
.venv/bin/lerobot-train \
    --dataset.repo_id=local/lewelder_sim --dataset.root=datos/lewelder_sim \
    --policy.type=act --policy.device=cpu --policy.push_to_hub=false \
    --batch_size=8 --steps=600 --num_workers=2 --log_freq=10 --save_freq=300 \
    --output_dir=salidas/entreno_act --job_name=act_lewelder_cpu
```

SmolVLA (el modelo base ya está en la caché de Hugging Face; `HF_HUB_OFFLINE=1` evita llamadas a la red). Las
cámaras se renombran a las del modelo base (`RENOMBRE_SMOLVLA` del contrato) y la tercera va vacía:

```bash
HF_HUB_OFFLINE=1 .venv/bin/lerobot-train \
    --dataset.repo_id=local/lewelder_sim --dataset.root=datos/lewelder_sim \
    --policy.path=lerobot/smolvla_base --policy.device=cpu --policy.push_to_hub=false \
    --rename_map='{"observation.images.cenital": "observation.images.camera1", "observation.images.muneca": "observation.images.camera2"}' \
    --policy.empty_cameras=1 \
    --batch_size=4 --steps=200 --num_workers=2 --log_freq=10 --save_freq=200 \
    --output_dir=salidas/entreno_smolvla --job_name=smolvla_lewelder_cpu
```

Notas:
- `--output_dir` no debe existir (bórralo antes de repetir) o añade `--resume=true`.
- El checkpoint queda en `<output_dir>/checkpoints/last/pretrained_model` (config, pesos y pre/postprocesador con
  las estadísticas del dataset y, en SmolVLA, el `rename_map`). Las herramientas de abajo aceptan la carpeta de
  salida, la del checkpoint o la de `pretrained_model`.
- No existe `--wandb.enable`; sin más opciones no se usa Weights & Biases.
- Los vídeos van en AV1 (por defecto en LeRobot 0.7); se decodifican con pyav sin GPU.
- Inferencia en CPU: ACT ~0,1 s por paso de media (un chunk de 100 acciones cada 100 pasos); SmolVLA ~1,5 s por
  chunk de 50 acciones (~0,03 s por paso de media). Un recorrido de ~40 s simulados tarda 1-2 min con render.
- Con tan pocos pasos las políticas **no** sueldan bien (ver la tabla de la sección 5): solo prueban el flujo.

## 3. Recetas con GPU (portátil de Andoni y nube)

Cambia `--policy.device=cuda`, sube `--num_workers` y, si quieres el modelo en el Hub, quita
`--policy.push_to_hub=false` y pon `--policy.repo_id=Izaguirre97/<nombre>`. **Mide los primeros 100 pasos**
(`step_s` en el log) y ajusta `--steps` al tiempo que tengas; guarda checkpoints a menudo (`--save_freq`) para
poder evaluar uno intermedio si se acaba el tiempo.

| Política | GPU | batch | pasos | tiempo estimado | Notas |
|---|---|---|---|---|---|
| **ACT** | **GTX 1660 6 GB (portátil de Andoni)** | 8 | 30 000-50 000 | ~0,2 s/paso → **2-3 h** | 52 M parámetros, cabe de sobra en 6 GB con batch 8 a 256x192; sin AMP (la 1660 no tiene núcleos tensor); dejarlo entrenando de noche |
| ACT | nube 24 GB (L4/A10) | 16-32 | 30 000 | 1-2 h | |
| **SmolVLA** | **nube L4 / A10G 24 GB** | 32 | 15 000-20 000 | ~0,5-0,7 s/paso → **3-4 h** | 3-6 € por entrenamiento en GPU por horas |
| SmolVLA | nube A100 40-80 GB | 64 | 20 000 | ~4 h | receta oficial de SmolVLA (batch 64, 20 000 pasos) |
| SmolVLA | GTX 1660 6 GB | — | — | — | no: 450 M parámetros y el VLM no caben con un batch útil; solo inferencia |

ACT en la GTX 1660 (un ACT para todas las tareas: ve en la cámara qué pieza hay):

```bash
.venv/bin/lerobot-train \
    --dataset.repo_id=Izaguirre97/lewelder_sim_160 \
    --policy.type=act --policy.device=cuda --policy.repo_id=Izaguirre97/act_lewelder \
    --batch_size=8 --steps=40000 --num_workers=6 --save_freq=5000 --log_freq=100 \
    --output_dir=outputs/act_lewelder --job_name=act_lewelder
```

SmolVLA en la nube:

```bash
.venv/bin/lerobot-train \
    --dataset.repo_id=Izaguirre97/lewelder_sim_160 \
    --policy.path=lerobot/smolvla_base --policy.device=cuda --policy.repo_id=Izaguirre97/smolvla_lewelder \
    --rename_map='{"observation.images.cenital": "observation.images.camera1", "observation.images.muneca": "observation.images.camera2"}' \
    --policy.empty_cameras=1 \
    --batch_size=32 --steps=20000 --num_workers=8 --save_freq=2500 --log_freq=100 \
    --output_dir=outputs/smolvla_lewelder --job_name=smolvla_lewelder
```

### ACT de respaldo por tipo de unión

ACT no lee la instrucción. Si el ACT único confunde recta y T, se entrena **un ACT por tipo de unión** solo con
sus episodios (índices con `--dataset.episodes`). El orden de los episodios lo da el dataset:

```bash
.venv/bin/python -c "
from lerobot.datasets.lerobot_dataset import LeRobotDataset
ds = LeRobotDataset('local/lewelder_sim', root='datos/lewelder_sim')
eps = ds.meta.episodes
print([i for i in range(ds.num_episodes) if 'recta' in eps[i]['tasks'][0]])"
# → p. ej. [0, 2, 4, 6]
.venv/bin/lerobot-train ... --policy.type=act --dataset.episodes='[0, 2, 4, 6]' --job_name=act_recta
```

(El robot MuJoCo del servidor carga un solo checkpoint de ACT: con dos, arranca el servidor con el de la unión que
se vaya a enseñar.)

## 4. Subir el dataset a Hugging Face (cuando toque; aquí no se sube nada)

```bash
huggingface-cli login
.venv/bin/python -c "
from lerobot.datasets.lerobot_dataset import LeRobotDataset
LeRobotDataset('Izaguirre97/lewelder_sim_160', root='datos/lewelder_sim_160').push_to_hub()"
```

Con el dataset en el Hub se quita `--dataset.root` y se usa `--dataset.repo_id=Izaguirre97/lewelder_sim_160`.
`notas.json` va dentro de la carpeta del dataset y se sube con él (el registro del filtro de calidad).

## 5. Evaluar: la tabla VLA frente a ACT frente a replay

`robot/evaluar.py` hace N recorridos por anclaje y tipo en bucle cerrado sobre `EntornoSoldadura` (cada uno desde
una postura de reposo algo distinta) y los puntúa con `evaluar_pasada`; el "gatillo" del robot es que su LED luciría
(punta encima del cordón a la altura de soldar). **Éxito = cobertura completa a ±5 mm** (spec, sección 7; objetivo
8 de 10 por anclaje). Escribe `salidas/evaluacion/<politica>.{json,md}` y `comparativa.{md,json}` (la diapositiva).

```bash
.venv/bin/python -m robot.evaluar --politica replay --dataset datos/lewelder_sim --repeticiones 3
.venv/bin/python -m robot.evaluar --politica act --checkpoint salidas/entreno_act --repeticiones 10
HF_HUB_OFFLINE=1 .venv/bin/python -m robot.evaluar --politica vla --checkpoint salidas/entreno_smolvla --repeticiones 10
# o las tres seguidas:
.venv/bin/python -m robot.evaluar --politica vla act replay --checkpoint-vla ... --checkpoint-act ... --dataset ...
```

Opciones: `--anclajes A B C D`, `--tipos recta t`, `--nivel aprendiz|oficial|maestro`, `--max-pasos 1500`,
`--dispositivo cuda`. Coste en CPU: replay ~1 s por recorrido (sin render); ACT y SmolVLA 1-2 min por recorrido.

Resultado con los entrenamientos cortos de la sección 2 (16-11-2026; 1 recorrido por anclaje y tipo para ACT y
SmolVLA, 3 para replay). Como se esperaba, las políticas de unos cientos de pasos no sueldan; el replay sí:

| Anclaje | VLA (SmolVLA, 200 pasos) | ACT (600 pasos) | Replay (grabado) |
|---|---|---|---|
| A | 0 % (—) | 0 % (—) | 100 % (0,5 mm) |
| B | 0 % (10,8 mm) | 0 % (—) | 100 % (0,5 mm) |
| C | 0 % (—) | 0 % (—) | 100 % (0,5 mm) |
| D | 0 % (9,7 mm) | 0 % (—) | 100 % (0,5 mm) |
| **Total** | 0 % · nota media 0,1 | 0 % · nota 0 | **100 %** · nota media 9,1 |

Tasa de éxito (error medio lateral mientras luce el LED; "—" = la punta no llegó a bajar al cordón). El SmolVLA
corto ya se acerca a la pieza en B y D (llega a soldar el 17 % de la T del anclaje B); el ACT corto no baja. Tiempo
de evaluación en CPU: replay 8 s (24 recorridos), ACT 8 min (8 recorridos), SmolVLA 13 min (8 recorridos).

## 6. Desplegar en el servidor (robot MuJoCo)

```bash
HF_HUB_OFFLINE=1 .venv/bin/python -m lewelder.servidor --fuente simulada --robot mujoco --politica vla \
    --checkpoint-vla salidas/entreno_smolvla --checkpoint-act salidas/entreno_act --dataset datos/lewelder_sim
# tablet en http://<ip>:8000/ · --escala-robot 2 para ensayar al doble de velocidad · --dispositivo cuda con GPU
```

- La política se elige en la tablet (VLA / ACT / Replay) y se puede cambiar a mitad del Repaso.
- Si la elegida no está (sin checkpoint, no carga) o falla a mitad, el robot cae a la siguiente
  (vla → act → replay) y la tablet lo marca en ámbar ("Respaldo: usa ACT").
- Las políticas se cargan en segundo plano al arrancar (SmolVLA ~10 s en CPU).
- Durante el Repaso la tablet enseña la cámara cenital de la simulación (~8 imágenes por segundo).

## 7. Consejos

- Más variedad que pasos: mejor 15-20 demostraciones por anclaje y tipo que el doble de pasos con 5.
- Para el robot real, graba con el brazo guía con la misma resolución y las mismas claves de cámara; el filtro de
  calidad (`nota >= umbral`) decide qué episodios entran.
- Evalúa con las mismas métricas que al alumno: `EntornoSoldadura.muestra()` da la punta en el marco de la pieza.
- Puerta del sábado 20:00 (spec): si SmolVLA llega a 8/10 por anclaje en la evaluación, la demo va con VLA; si
  no, con ACT, y el VLA queda en la comparativa.
