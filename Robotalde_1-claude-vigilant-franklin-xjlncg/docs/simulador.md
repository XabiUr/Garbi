# Simulador de la demo (LeWelder v2)

Para probar la demo **casi como si fuera real** antes de imprimir nada: el SO-101 (Chispas) en 3D moviéndose en
tiempo real con la física de MuJoCo, la tablet v2 funcionando con su protocolo de verdad (`/ws2`) y tú haciendo de juez
con el ratón. Todo en un solo proceso.

## Arrancar

```bash
export MUJOCO_GL=egl
PYTHONPATH=$PWD .venv/bin/python -m lewelder.simulador            # http://localhost:8080/
```

| Página | Qué es |
|---|---|
| `/` | **Vista combinada** (pensada para 1920×1080): la mesa 3D grande, la tablet (1280×800 al 50 %) y el panel del juez |
| `/sim` | La mesa 3D con el panel del juez (sin la tablet) |
| `/tablet` | La tablet v2 (`web/v2/`), para abrirla en la tablet de verdad o en otra ventana |
| `/?guion=jurado` | **Demo de jurado**: la secuencia del pitch sola, de principio a fin (añade `&bucle=1` para repetirla) |

Opciones útiles: `--puerto N` (o la variable `PORT`), `--guion jurado` (arranca ya reproduciéndola), `--sin-llm` (voz
y frases solo por reglas), `--manual` (tras montar no encadena señalar → demostrar → ronda: lo pides tú),
`--escala-robot 2` (robot del guion al doble de velocidad), `--partidas una|por_pestana` (ver abajo).

Robot: si se pasa `--checkpoint-vla`/`--checkpoint-act` o `--dataset` (LeRobotDataset **v2** con episodios cuya tarea
es la orden), cada orden la hace la política, el replay o, si no sabe hacerla, el **guion** (siempre disponible). La
mesa 3D dice cuál manda (cajetín, fila ROBOT).

## Cómo se juega

1. **Pedir.** Pulsa `▶ JUGAR` (o toca la tablet) y pide la junta: botón `🎙 HABLAR` (Web Speech, es-ES; en Chrome),
   escribe la orden («móntame una esquina») o usa un atajo (`MONTA T`, `MONTA ESQUINA`...). Con voz o texto sale la
   tarjeta «¿Monto una unión en esquina?»: SÍ en el panel o en la tablet.
2. **El robot monta** la chapa: la coge por la aleta en la zona libre, la gira, la deja sobre la base y los imanes la
   encajan. La tablet enseña las fases.
3. **Reconocer y alcance.** La junta se reconoce con `juntas.reconocer_junta` sobre las poses de la física (lo que
   daría el estéreo) y se comprueba si el robot llega (`alcance`). Si no llega, Chispas pide que la gires: mueve la
   base (herramienta BASE) hasta que la tablet diga «✓ Al alcance del robot».
4. **Señala y demuestra.** Señala el cordón, coge su antorcha del soporte, suelda (LED encendido) y la devuelve. Su
   pasada es el **fantasma** rival.
5. **Tu ronda.** Cuenta atrás y a soldar con la herramienta ANTORCHA (se elige sola). Al acabar: puntos, nota,
   iniciales (en la tablet o en el panel: `ABC` + FIRMAR) y ranking del día (`salidas/ranking.json`).

## Controles de la mesa 3D

Herramientas (botones del panel o teclas `1`-`4`):

| Herramienta | Ratón | Teclado |
|---|---|---|
| `1 · CÁMARA` | arrastrar: girar · mayús + arrastrar o botón central: desplazar · rueda: acercar | |
| `2 · ANTORCHA` | mover: la punta sigue la superficie de las chapas · **botón izquierdo mantenido = gatillo** · rueda: subir/bajar la punta · botón derecho: girar la cámara | `espacio` = gatillo · `Q`/`E` subir/bajar la punta · `W`/`S` ángulo de trabajo ±5° · `A`/`D` ángulo de avance ±5° |
| `3 · BASE` | arrastrar: mover la base · rueda: girarla 5° | `R`: girarla 90° |
| `4 · CHAPA` | clic: soltar la chapa móvil tumbada ahí · rueda: girarla 10° | |

Solo cuenta como soldado con **gatillo + punta apoyada** (< 2 mm de la chapa): la ayuda de abajo dice `APOYADA` o
`EN EL AIRE`. La punta empieza a 0,5 mm; con la rueda la levantas para probar el aviso «¡apoya la antorcha!». Para
soldar bien: ve a lo largo del cordón (línea discontinua cian) a 4-6 mm/s, con 45° de trabajo y 0-20° de empuje.

Perturbaciones (como en la competición): `GIRAR BASE 90°`, `BASE LEJOS` (fuera de alcance: «gírala»), `BASE A SU
SITIO`, `CHAPA AL AZAR` (en otra posición de la zona libre), `MONTO YO · T/ESQ.` (plan B: la junta aparece montada a
mano), `TERMINAR RONDA`, `REINICIAR`. `WEBCAM A/B` enseña lo que verían las dos webcams (render de
`escena_sintetica` con las poses actuales; no corre en el bucle).

## Varias partidas a la vez

- `--partidas una` (por defecto, la demo en el portátil): una sola partida compartida por todas las ventanas, así la
  tablet de verdad (`/tablet`) y la mesa del PC ven lo mismo. Todos mandan a la vez; la mesa lo dice («PARTIDA
  COMPARTIDA · N conectados»).
- `--partidas por_pestana` (el Space): **cada pestaña tiene su propia partida** (física, robot y puntuación), con su
  `?partida=ID` en la URL; la tablet incrustada va a la misma. Para la tablet en otro dispositivo, el enlace
  `/tablet?partida=ID` de la mesa. Como mucho `--max-partidas` (6) a la vez; con el aforo lleno, las nuevas entran en
  la partida principal compartida y la mesa lo avisa. Una partida sin nadie conectado se cierra a los 10 min. El
  ranking del día es común.

## Hugging Face Space

`herramientas/space/` tiene el `Dockerfile`, el `README.md` (cabecera de Spaces: docker, puerto 7860) y
`requirements-space.txt` (sin torch ni LeRobot). Construir y probar en local desde la raíz del repo:

```bash
docker build -f herramientas/space/Dockerfile -t lewelder-sim .
docker run --rm -p 7860:7860 lewelder-sim
```

Sin docker, con exactamente esas dependencias: `uv venv -p 3.12 .venv-space && VIRTUAL_ENV=.venv-space uv pip install
-r herramientas/space/requirements-space.txt && PORT=7860 PYTHONPATH=$PWD .venv-space/bin/python -m lewelder.simulador
--partidas por_pestana`.

## Cómo está hecho

| Pieza | Archivo |
|---|---|
| Física en tiempo real (480 Hz, hilo propio), piezas del CAD como mocap, agarre, imanes y soporte | `lewelder/mesa_sim.py` |
| Robot: guion (IK de pose de la pinza y de la punta), replay/política y respaldo | `lewelder/guion_robot.py` |
| Clase v2 por `/ws2` (protocolo de `web/v2/PROTOCOLO.md`), juez con el ratón, partidas, HTTP | `lewelder/simulador.py` |
| Mesa 3D y panel del juez (three.js, mallas que sirve el servidor) | `web/sim/` |
| Capturas con Playwright de la demo del jurado | `herramientas/captura_simulador.py` |

**La antorcha del juez entra por el mismo camino que la real:** el navegador manda la punta (punto de la mesa), el
gatillo y los ángulos; el servidor hace una lectura de IMU virtual (`cuaternion_desde_angulos`), da la posición solo
con el gatillo (el LED solo luce entonces), los une con `Fusion` (tara vertical), pasa la punta al marco del cordón de
la junta reconocida (`juntas.punta_en_cordon`) y la puntúa con `MarcadorEnVivo` contra el fantasma.

### Adaptadores para enchufar las otras tareas

- **Tarea 1 (estéreo):** `simulador.reconocer(mesa)` llama a `juntas.reconocer_junta` con las poses de la física
  (`poses_para_juntas`). Con las webcams de verdad, esas poses salen de `SeguidorEstereo.procesar`; la punta del juez
  también (hoy la da el ratón).
- **Tarea 2 (montaje en MuJoCo):** el robot del simulador es un **guion provisional**. Cuando su escena y sus
  demostraciones estén en main: (a) su dataset multitarea entra tal cual con `--dataset` (replay por orden) y sus
  políticas con `--checkpoint-*`; (b) si su escena trae el agarre por contacto y los imanes, `MesaSim` puede delegar
  en ella (la interfaz que usa el resto es `mandar(q)`, `poner_led`, `instantanea()`, `junta_montada()`,
  `punta_antorcha()`).
- **Tarea 6a/6b (tablet):** la tablet es `web/v2/` sin cambios salvo `cliente.js`, que pasa `?partida=` al WebSocket.
  `ClaseSim` es, de facto, la máquina de estados 6b de la ronda simulada.

### Limitaciones conocidas

- El SO-101 no llega con la pinza horizontal a la aleta de la chapa de pie (a ~25 mm de altura y ~230 mm del robot):
  el guion la deja inclinada 15-35° y los imanes la enderezan. **Ojo en la mesa real**: puede que el robot tenga que
  soltarla algo inclinada o desde más alto y confiar en las guías.
- Las piezas son cinemáticas (sin contactos): una chapa soltada lejos de su sitio cae tumbada donde esté.
- La vista 3D a 1920×1080 pide WebGL con GPU; con render por software (SwiftShader, sin GPU) va a 3-4 FPS.
