# Garbi · guía del sitio (hackathon LeRobot Bilbao)

Paso a paso para hoy, con los comandos exactos y en orden. Manda [solucion-final.md](../.plans/aspira/solucion-final.md).
Todos los comandos se lanzan **desde la raíz del repositorio** con el entorno activado. Los ejemplos van en Windows
(`COM5`, cámaras por índice); en Linux cambia `COMx` por `/dev/ttyACMx` y los índices por `0`, `2` o `/dev/videoN`.

Todas las herramientas tienen `--help`. Ninguna mueve el brazo sin pedir Enter antes, y Ctrl+C deja siempre el brazo
quieto donde está (con par) y la aspiradora apagada.

| Paso | Comando | Tiempo |
|---|---|---|
| 0 | Instalar | 10 min |
| 1 | Puertos | 2 min |
| 2 | Cámaras | 10 min |
| 3 | Ajustar colores | 10 min |
| 4 | Calibrar (intrínsecas, arriba, robot) | 20 min |
| 5 | Probar el robot y la aspiradora | 5 min |
| 6 | Grabar episodios de acercamiento | 60-90 min |
| 7 | Subir a Hugging Face y entrenar en HF Jobs | 2-4 h (en la nube) |
| 8 | Bajar el modelo y ejecutar Garbi con ACT | 10 min |
| 9 | Ensayar los 5 intentos | 30 min |

---

## 0. Instalar

Desde cero en Windows, en PowerShell:

```powershell
winget install --id Git.Git -e
git clone -b claude/vigilant-franklin-xjlncg https://github.com/Izaguirre97/Robotalde_1.git D:\Garbi\Robotalde_1
cd D:\Garbi\Robotalde_1
powershell -ExecutionPolicy Bypass -File herramientas\instalar_windows.ps1
.venv\Scripts\activate
hf auth login                              # token con permiso de escritura (para --push y HF Jobs)
```

El instalador pone uv, ffmpeg, Python 3.12 en `.venv`, PyTorch (CUDA si hay NVIDIA), LeRobot 0.7, MuJoCo, OpenCV,
MediaPipe y su modelo de manos, y pasa una prueba rápida. Se puede repetir sin miedo.

En Linux, a mano:

```bash
uv venv --python 3.12 .venv && source .venv/bin/activate
uv pip install torch torchvision && uv pip install -e ".[dev,manos]"
```

Comprobación rápida: `python -m pytest -q tests/test_garbi_real.py tests/test_garbi_herramientas.py`.

**Si falla:**
- Las ventanas de OpenCV dicen «The function is not implemented»: está instalado `opencv-python-headless`.
  `pip uninstall -y opencv-python-headless opencv-python` y `pip install opencv-python`.
- En Linux, para fijar exposición y foco: `sudo apt install v4l-utils`; para los puertos serie:
  `sudo usermod -aG dialout $USER` (y cerrar sesión).

## 1. Puertos

```powershell
lerobot-find-port        # desenchufa el cable que te pida: dice el puerto de cada brazo
```

Apunta: follower = `COM5`, leader = `COM6`, Arduino de la aspiradora = `COM7` (en el Administrador de dispositivos de
Windows salen en «Puertos (COM y LPT)»). Los dos brazos ya están calibrados con LeRobot: usa los **mismos id** que en
la calibración (`--id` del follower, `--leader-id` del leader). Los archivos están en
`%USERPROFILE%\.cache\huggingface\lerobot\calibration\` (Linux: `~/.cache/huggingface/lerobot/calibration/`).

**Si falla:** «Permission denied» o puerto ocupado → cierra el Monitor Serie del IDE de Arduino, Cura, otro Python.
Si LeRobot pide calibrar al conectar, el id no coincide: pulsa Enter para usar el archivo o revisa `--id`.

## 2. Cámaras

```powershell
python herramientas/garbi_camaras.py --listar                  # índices y una foto de cada una en capturas/
python herramientas/garbi_camaras.py --top 0 --wrist 1         # en vivo con la percepción superpuesta
```

Coloca la cámara de arriba como en la simulación (M1): en diagonal desde el lado del robot, a ~0,8 m, viendo el
tapete entero. Flexo encendido, ninguna ventana detrás. En la ventana deben salir: el contorno azul del tapete
(«4 esquinas», «cámara: calibrada»), la madera, la bola naranja del taladro, las manos y la cruz verde del anillo de
la boquilla; en la muñeca, la punta de la broca.

Teclas: `s` captura (para el paso 3), `m` máscaras, `1-6` cada color, `p` percepción, `c` recalibrar el tapete,
`r` recargar colores, `q` salir.

**Si falla:**
- «Failed to open» → índice equivocado (repite `--listar`) o la cámara la tiene otra app (Teams, Zoom, Cámara).
- Imagen que parpadea o cambia de color → la exposición o el balance no se fijaron: prueba `--exposicion 10`
  o `--exposicion 30`; en Linux `v4l2-ctl -d /dev/video0 --list-ctrls` para ver los nombres de los controles.
- «tapete: NO» → ajusta `tapete_azul` (paso 3) o que el tapete entre entero en la imagen.

## 3. Ajustar los colores

Con las capturas de la luz de la demo (tecla `s` del paso 2) o en vivo:

```powershell
python herramientas/garbi_ajustar_color.py --imagen capturas/top_AAAAMMDD_HHMMSS_mmm.png
python herramientas/garbi_ajustar_color.py --camara 0 --color bola_naranja
```

Para cada color (`n`/`p` cambia): **pincha** el objeto con el ratón (centra el rango) y afina con los deslizadores
hasta que la máscara cubra el objeto entero y nada del fondo. `s` guarda `garbi/config_vision.yaml`. Colores:
`tapete_azul`, `madera`, `bola_naranja`, `anillo_verde`, `piel`, `pegatina`. Vuelve al paso 2 y pulsa `r` para verlo.

El yaml lo leen `python -m garbi.correr --real` (tapete, bola y anillo pasan a la percepción) y todas las
herramientas. Súbelo al repositorio cuando quede bien (`git add garbi/config_vision.yaml`).

## 4. Calibrar (todo va a `calib/`)

```powershell
# (a) intrínsecas: tablero de ajedrez 9 × 6 esquinas interiores, cuadros de 25 mm, bien plano
python herramientas/garbi_calibrar.py intrinsecas --camara top --indice 0
python herramientas/garbi_calibrar.py intrinsecas --camara wrist --indice 1
# (b) cámara de arriba con el tapete
python herramientas/garbi_calibrar.py arriba --top 0
# (c) robot respecto a la mesa: 9 posturas + 5 de comprobación con el anillo verde
python herramientas/garbi_calibrar.py robot --puerto COM5 --top 0
```

- (a) Espacio = foto (solo si ve el tablero), `a` = automático, `q` = terminar. 15 fotos por toda la imagen,
  inclinado y a distintas distancias. Objetivo: reproyección < 0,5 px.
- (b) Mira `calib/arriba.png`: el contorno debe ir por los bordes del tapete. Comprueba 4 puntos con regla (±2 mm).
- (c) Quita el taladro del tapete. Pide Enter antes de cada postura (velocidad baja, `--velocidad 15`).
  Criterio: **error < 4 mm en las 5 de comprobación**. Guarda `calib/robot.yaml`.

`calib/*.yaml` se puede subir al repositorio; las fotos (`calib/tablero_*`, `calib/robot/`) están en `.gitignore`.

**Si falla:**
- (a) reproyección alta → más fotos, el tablero sin doblar, sin reflejos del flexo.
- (b) «NO veo las 4 esquinas» → paso 3 (`tapete_azul`) o mueve la cámara.
- (c) «el anillo verde se vio en menos de 4 posturas» → `anillo_verde` en el paso 3 y mira `calib/robot/`;
  error > 4 mm → revisa que la base del robot no se mueva (sargentos), repite (b) y (c). Respaldo: la plantilla
  impresa (base en el origen): sin `calib/robot.yaml`, `garbi.correr` supone la base en (0, 0, 0°).

## 5. Probar el robot y la aspiradora

```powershell
python herramientas/garbi_probar_robot.py --puerto COM5 --solo-leer           # solo lee la postura
python herramientas/garbi_probar_robot.py --puerto COM5 --aspiradora COM7     # aparcado, 3 posturas, aspiradora 2 s
python herramientas/probar_aspiradora.py COM7                                 # el Arduino solo (latido de 1 s)
```

Error de llegada > 3° en alguna postura → cable suelto, servo sin par o el montaje de la boquilla rozando.
La aspiradora: [firmware/garbi_aspiradora/README.md](../firmware/garbi_aspiradora/README.md).

## 6. Grabar episodios de ACERCAMIENTO (teleoperación)

ACT aprende el acercamiento: **desde la postura prudente hasta la de aspirar**, y se queda ahí mientras taladras.
La postura prudente es la que Garbi usa para seguir al taladro: la cámara de la muñeca mira la punta de la broca
sobre la madera desde 180 mm (la boca queda alta y a un lado; holgura con el taladro ~70 mm). Al ejecutar, ACT
empieza siempre desde ella, así que **todos los episodios deben empezar ahí** (la herramienta lo comprueba). El episodio empieza al clavar la broca y termina al levantarla. Se graba **sobre la
madera en el tapete, con las cámaras y la luz de la demo**.

```powershell
python herramientas/garbi_teleop_grabar.py --puerto COM5 --leader COM6 --aspiradora COM7 --top 0 --wrist 1 `
    --salida datos/garbi_acercamiento --repo-id USUARIO/garbi_acercamiento
```

Dos personas: una con el taladro, otra con el leader. Por episodio:
1. Quien taladra coge el taladro y lo sostiene sobre el punto donde va a taladrar, sin clavar.
2. Tecla **p**: el follower va despacio a la postura prudente de esa broca y se queda quieto. La ventana dice
   «ENGANCHE · faltan N grados»: mueve el leader hasta ponerlo igual que el follower (< 5°); entonces el follower
   vuelve a seguir al leader sin saltar.
3. Quien taladra **clava la broca** → **espacio** (empieza; se enciende la aspiradora). Si el follower está a más de
   8° de la postura prudente de la broca (`--tolerancia-partida`), no empieza y dice «pulsa p».
4. Con el leader, acerca la boca a la posición de aspirar (de lado, sin tocar la broca ni el taladro) y mantenla
   mientras taladra. Como hace el programado: primero gira y baja a la boca a ~100 mm mirando la broca, después
   baja a la altura de trabajo y entra.
5. Cuando **levanta la broca** → **espacio** (termina y guarda). `r` descarta el episodio y se repite; `q` sale.

El leader puede mover la muñeca y la pinza: al follower y al dataset llegan siempre con la muñeca a 0 y la pinza
cerrada (montaje forzado). Para añadir episodios otro rato: `--reanudar`.

**Corte automático** (cuando la percepción ya va bien): `--corte auto --tolerancia 2.0`. Empieza al verse la broca
clavada y termina al levantarla; si se levanta menos de 2 s y se vuelve a clavar (recuperación), sigue. Las teclas
siguen valiendo para forzar o descartar. Solo corta si ve **una mano en el taladro** (MediaPipe o color): si la
broca está apoyada y no corta, la consola y la ventana dicen por qué (p. ej. «no veo una mano en el taladro»). Si
en el sitio la mano no se detecta bien, añade `--sin-agarre`. Con `--sin-ventana` no hay tecla p y la partida no se
comprueba (`--partida libre`): no lo uses para grabar el dataset de ACT.

**Qué grabar (≈ 50-80 episodios buenos):**
- 70 %: acercamientos normales, con la broca en sitios distintos de la madera y la madera en sitios y giros
  distintos dentro del tapete.
- 20 % **recuperaciones**: a mitad del acercamiento, quien taladra mueve la broca a otro punto (con `--corte auto`,
  dentro de la tolerancia) y el leader corrige; una mano que se cruza y el brazo espera o se aparta.
- 10 %: la broca se mueve un poco después de pulsar p (el follower queda algo desplazado, dentro de los 8°).
- Velocidad parecida a la de la demo; nada de golpes. Si toca la broca o el taladro: `r`.

La ventana cuenta guardados y descartados; los motivos van a `datos/garbi_acercamiento/episodios_garbi_acercamiento.json`.

**Si falla:** el follower no sigue al leader → `--leader-id` o `--id` no son los de la calibración, o los puertos
están cambiados. Vídeo que se atasca → baja a `--resolucion 320x240`. La aspiradora no se enciende → paso 5.

## 6 bis. Grabar episodios guiados por código (sin teleoperar)

La aplicación entera funciona con la visión y el **acercamiento programado**. Cada acercamiento, de la clavada a la
levantada, se graba solo como episodio de ACT:
- **acción:** la orden que manda el código;
- **cámaras:** `top` y `wrist`;
- **tarea:** «Approach the drill bit.».

Una persona solo tiene que taladrar.

```powershell
python -m garbi.correr --real --puerto COM5 --aspiradora COM7 --top 0 --wrist 1 --acercamiento programado --grabar datos/garbi_acercamiento_codigo --repo-id TU_USUARIO/garbi_acercamiento_codigo
```

- **Episodios que se descartan solos:**
  - una guardia frenó el brazo;
  - entró el respaldo;
  - no empezó en la postura prudente;
  - duró demasiado poco.

  Los motivos quedan en el json del dataset.
- **Variedad:** al menos 10 agujeros por zona de la madera, la madera en sitios distintos, la luz del sitio y algún
  caso de broca movida a mitad del acercamiento (el programado la sigue).
- **Combinar con teleoperados:** ACT aprende exactamente lo que hace el código. Para que haga algo más, junta este
  dataset con 15-20 episodios teleoperados (paso 6) de recuperaciones que el código no hace bien, y después `dagger`.
  Unir datasets: `python herramientas/garbi_unir_datasets.py`.

## 7. Subir a Hugging Face y entrenar en HF Jobs

```powershell
# subir (o graba con --push y se sube al terminar)
python -c "from lerobot.datasets.lerobot_dataset import LeRobotDataset as D; D('USUARIO/garbi_acercamiento', root='datos/garbi_acercamiento').push_to_hub(private=True)"
```

Entrenar (en Git Bash o WSL en Windows; en Linux tal cual):

```bash
HF_USUARIO=USUARIO DATASET=USUARIO/garbi_acercamiento POLITICA=USUARIO/garbi_act_acercamiento \
    herramientas/garbi_entrenar.sh hf          # A10G, 30k pasos, lote 8, checkpoints al Hub cada 5k
hf jobs ps                                     # estado; hf jobs logs <id> para ver el entrenamiento
```

Sin bash (PowerShell), el mismo trabajo:

```powershell
lerobot-train --policy.type=act --dataset.repo_id=USUARIO/garbi_acercamiento --dataset.image_transforms.enable=true `
  --batch_size=8 --steps=30000 --job_name=garbi_act_acercamiento --job.target=a10g-small --job.timeout=6h `
  --job.detach=true --policy.device=cuda --policy.repo_id=USUARIO/garbi_act_acercamiento --policy.push_to_hub=true `
  --policy.private=true --save_checkpoint_to_hub=true --save_freq=5000 --log_freq=100 --output_dir=/tmp/salida
```

Antes, una prueba de humo en local (2 pasos, minutos):
`DATASET=USUARIO/garbi_acercamiento DATASET_RAIZ=datos/garbi_acercamiento herramientas/garbi_entrenar.sh humo`.

**Si falla:** HF Jobs necesita cuenta con pago o créditos del hackathon y el token con escritura. Con una GPU
NVIDIA local: `herramientas/garbi_entrenar.sh local`. Con 10k pasos ya se puede probar en el robot.

## 8. Bajar el modelo y ejecutar Garbi con ACT

```powershell
hf download USUARIO/garbi_act_acercamiento --local-dir modelos/garbi_act   # opcional: --modelo acepta el repo
python -m garbi.correr --real --puerto COM5 --aspiradora COM7 --top 0 --wrist 1 --calibracion calib `
    --habilidad act --modelo modelos/garbi_act
```

`garbi.correr --real` lee `calib/` (intrínsecas, quita la distorsión y la base del robot) y
`garbi/config_vision.yaml`. Primero, sin ACT (respaldo programado): quita `--habilidad act --modelo ...`.
Registros por ciclo en `registros/AAAAMMDD.jsonl`; `--rerun` para la línea de tiempo.

**Si falla:** «No veo las 4 esquinas del tapete» → nada tapando el tapete al arrancar (brazo aparcado). ACT se acerca
de más → las guardias lo frenan y entra el respaldo; graba más episodios de ese caso y reentrena (o `dagger`).

## 9. Ensayar los 5 intentos

Cada intento, cronometrado y apuntado (acierto, contacto, tiempo):
1. Coges el taladro → Garbi se pone a la distancia prudente.
2. Clavas la broca → ACT se acerca y aspira.
3. Taladras, levantas la broca → Garbi se retira.
4. Sacas el taladro → Garbi limpia el agujero.
5. Garbi descansa.

Haz al menos 3 tandas de 5 seguidas antes de la demo. Si algo falla, apunta en qué paso y mira el registro del ciclo.
Plan B de la demo: `--habilidad programada` (el acercamiento programado) con la misma calibración.
