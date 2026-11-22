# Garbi · cómo hay que entrenarlo

La simulación (`python -m garbi.video --vision`) enseña cómo debe comportarse Garbi. Esta guía explica cómo
conseguir lo mismo con el SO-101 real. **Aquí no se entrena nada.** Se entrena en el hackathon, con el robot y una GPU.

Vídeo de referencia de lo que tiene que aprender el VLA (6 demostraciones, las dos órdenes):

```bash
.venv/bin/python -m garbi.video --demostraciones 6 --semilla 10 --salida salidas/garbi_demostraciones_vla.mp4
```

## 1. Qué aprende el VLA y qué no

El sistema es híbrido. El VLA solo aprende **el gesto de limpiar**; todo lo demás es programado y no se entrena.

| Parte | Quién lo hace | Por qué |
|---|---|---|
| Ver la tabla, el taladro y la alfombrilla | Visión clásica (ArUco + color) | Precisa (2-5 mm) y sin datos |
| Acercarse al taladro quieto y quedarse quieto | Programado (IK + máquina de estados) | Tiene que ser seguro y repetible: está la mano al lado |
| Encender y apagar la aspiradora | Programado (Arduino con latido) | Seguridad |
| **Limpiar el agujero nuevo** | **VLA** («Clean around the new hole.») | Tiene que encontrar la viruta en la imagen, distinguirla de agujeros viejos y barrerla |
| **Limpiar la alfombrilla** | **VLA** («Clean the chips on the mat.») | La misma red, otra frase: se ve que lee la orden |
| Decidir cuándo ha terminado y vigilarle | Supervisión programada (`garbi/politica.py`) | Límite de velocidad, de altura y fin por visión |

## 2. Qué tiene que hacer cada demostración

Lo que se graba es exactamente lo que muestra el vídeo de referencia:

**«Clean around the new hole.»**
- **Empieza** con la boca donde la deja el ciclo: junto al agujero, a ~35 mm en planta, de lado, a 30° y con la
  aspiradora encendida. Se taladra de verdad, se retira el taladro y, en la mitad de los episodios, se mueve un poco la tabla
  (±15 mm, ±10°).
- **Hace** esto: con la boquilla siempre a 30° (el borde de abajo a ~3 mm de la cara), barre en zigzag lo que queda
  de viruta alrededor del agujero (radio 10-30 mm) a velocidad tranquila (≤ 120 mm/s) y se queda quieto medio segundo
  al acabar. No vuelve a aparcar: eso es programado.
- **Varía** entre episodios:
  - la pose de la tabla;
  - el sitio del agujero (que sea alcanzable);
  - de 0 a 3 agujeros viejos ya limpios: el VLA tiene que ir al que tiene viruta;
  - la cantidad de viruta.

**«Clean the chips on the mat.»**
- **Empieza** aparcado.
- **Hace** esto: va al montón de serrín de la alfombrilla (fuera de la tabla), lo barre en zigzag con la boquilla a 30°
  y se queda quieto medio segundo al acabar.
- **Varía** el sitio del montón (por toda la zona alcanzable), su tamaño y la pose de la tabla.

Reglas de grabación:
- Unos **3-6 s por episodio**.
- Movimiento **siempre igual de estilo**: mismo zigzag, misma altura y misma velocidad. Una red aprende mejor un solo
  estilo que varios mezclados.
- **«Aprende del mejor»**: se descarta (`←` en `lerobot-record`) cualquier episodio que deje viruta, choque o dude.
  Tras cada episodio se mira la viruta que queda; en simulación el filtro exige ≥ 95 % recogida.
- Las cámaras tienen los mismos nombres que en la simulación:
  - `top`: la cenital fija, la misma que usa la visión;
  - `wrist`: la del robot, al costado de la boquilla, mirando por donde aspira, que ve el agujero de lado.

  Así el agujero se ve desde dos ángulos.
- La aspiradora tiene que estar **encendida** durante la grabación. Se ve en la imagen que la viruta desaparece, y así
  es como funcionará.
- Regla práctica: tú mismo tienes que poder hacer la tarea mirando solo las dos cámaras.

## 3. Cuántas

| Orden | Episodios | Reparto |
|---|---|---|
| Limpiar agujero | 50 | ~10 por cada zona de la tabla (5 zonas); la mitad con la tabla movida; agujeros viejos en la mitad |
| Limpiar alfombrilla | 50 | ~10 por cada zona de la alfombrilla (5 zonas) |

En el paper de SmolVLA, 50 episodios por tarea funcionaron y 25 dieron malos resultados. Si falta tiempo, se mantienen
los 50 de una orden antes que 25 de cada una.

## 4. Grabar con el robot real (teleoperación con el brazo guía)

Un dataset por orden y luego se fusionan (`single_task` es una por sesión):

```bash
lerobot-record \
  --robot.type=so101_follower --robot.port=/dev/ttyACM0 --robot.id=seguidor_robotalde \
  --robot.cameras="{ top: {type: opencv, index_or_path: 0, width: 640, height: 480, fps: 30}, wrist: {type: opencv, index_or_path: 2, width: 640, height: 480, fps: 30}}" \
  --teleop.type=so101_leader --teleop.port=/dev/ttyACM1 --teleop.id=guia_robotalde \
  --display_data=true --dataset.no_stamp=true \
  --dataset.repo_id=${HF_USER}/garbi_agujero \
  --dataset.single_task="Clean around the new hole." \
  --dataset.num_episodes=50 --dataset.episode_time_s=8 --dataset.reset_time_s=20
```

Lo mismo con `garbi_alfombrilla` y `"Clean the chips on the mat."`.

- En el tiempo de *reset* se prepara la siguiente escena: taladrar o tirar serrín, y mover la tabla. Para «limpiar
  agujero», la boca se lleva a mano (con el guía) a su sitio de partida junto al agujero.
- Se mira el informe de cadencia: si baja de 30 Hz, el dataset queda acelerado.
- Las frases tienen que ser **exactamente** las de `garbi/contrato.py` (`ORDEN_AGUJERO`, `ORDEN_ALFOMBRILLA`).

El dataset simulado (`python -m garbi.demostraciones`) sirve para **ensayar el flujo** (grabar, entrenar, evaluar) y
probar los comandos antes del evento. No se mezcla con el real: las imágenes simuladas son demasiado distintas.

## 5. Entrenar (en GPU)

**SmolVLA, la red principal: una sola red para las dos órdenes.** Las cámaras se renombran a las del modelo base y la
tercera va vacía:

```bash
lerobot-train \
  --dataset.repo_id=${HF_USER}/garbi_real \
  --policy.path=lerobot/smolvla_base --policy.device=cuda --policy.repo_id=${HF_USER}/smolvla_garbi \
  --rename_map='{"observation.images.top": "observation.images.camera1", "observation.images.wrist": "observation.images.camera2"}' \
  --policy.empty_cameras=1 \
  --batch_size=32 --steps=20000 --num_workers=6 --save_freq=5000 --log_freq=100 \
  --output_dir=outputs/smolvla_garbi --job_name=smolvla_garbi
```

**ACT de respaldo**: uno por orden con `--dataset.episodes=[...]`, porque no lee la frase.

```bash
lerobot-train \
  --dataset.repo_id=${HF_USER}/garbi_agujero \
  --policy.type=act --policy.device=cuda --policy.repo_id=${HF_USER}/act_garbi_agujero \
  --batch_size=8 --steps=40000 --num_workers=6 --save_freq=10000 \
  --output_dir=outputs/act_garbi_agujero --job_name=act_garbi_agujero
```

Comprobado en este entorno: el dataset de Garbi carga en los dos y la inferencia de SmolVLA va a ~32 ms por fotograma
en CPU. Antes de lanzar uno largo conviene hacer siempre una prueba de 2 pasos (`--steps=2`).

## 6. Evaluar antes de enseñarlo

Se evalúa en el ciclo completo, no a ciegas. `HabilidadVLA` se mete en `RobotVivo` con la supervisión:

```python
from garbi.politica import HabilidadVLA
habilidad = HabilidadVLA("outputs/smolvla_garbi", ControlBoca(mundo.cin))
```

Protocolo: 10 intentos por orden en posiciones nuevas, que no se hayan grabado. Para cada intento se apunta:
- el % de viruta recogida;
- el tiempo;
- si la supervisión tuvo que corregir (`descartadas`) o cortar por tiempo.

Se compara con la línea base programada (`LineaBase`: zigzag sobre lo que ve la visión), que en simulación limpia el
100 %.

| Resultado del VLA | Qué se enseña en la demo |
|---|---|
| ≥ 8/10 por orden | El VLA limpia en directo, con las dos frases |
| 5-7/10 | El VLA en la orden que mejor va; la otra con la línea base, y se dice así |
| < 5/10 | La línea base en directo y el VLA en vídeo, declarado |

## 7. Lo que se puede hacer ya, sin robot

- Ensayar el flujo completo con el dataset simulado: grabar, `--steps=2`, cargar en `HabilidadVLA` y ver que el
  ciclo corre.
- Preparar las escenas de grabación:
  - tablas con vinilo negro y ArUco 20 y 21;
  - la alfombrilla azul con los 4 ArUco;
  - la bola naranja del taladro **sobre un vástago, por encima del cuerpo**: si el cuerpo la tapa, la punta sale
    desplazada 6 mm.
- Imprimir el soporte de la boquilla:
  - boquilla recta de 110 mm en la dirección de las mordazas;
  - la cámara a un costado, a 50 mm del eje y 20 mm por detrás de la boca.

  Además, ajustar el umbral de brillo de la broca (`BROCA_V_MAX` en `garbi/vision.py`) con fotos de la broca real.
- Ensayar la teleoperación del zigzag con el brazo guía para que salga siempre igual.
