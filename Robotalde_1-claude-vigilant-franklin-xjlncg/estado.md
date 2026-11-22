# Estado del proyecto (para retomar)

Última actualización: 19-11-2026. Equipo **Robotalde** · proyecto **LeWelder** · Hackathon LeRobot Bilbao II
(20-22 nov 2026, La Perrera, Bilbao).

**PLAN DE ENTREGA (20-11, viernes noche, en el evento).** Todo lo que no es la demo (vídeo de 1 min, 3 min de
presentación, dataset y modelo públicos, repo reproducible, registro de datos con dos iteraciones, preguntas del
jurado) con la rúbrica oficial y calendario hasta el domingo: [docs/plan-entrega.md](docs/plan-entrega.md).
Pendiente: preguntar a la organización si los 5 intentos van dentro de los 3 min y dónde se entrega.

## Dónde estamos

| Fase | Estado | Entregable |
|---|---|---|
| 0 · Retomar | — | este archivo |
| 1 · Resultado final | **Hecha** | Escuela de soldadura aumentada (LeWelder). Ver [ideas](investigacion/ideas-desarrolladas.md), idea 1 |
| 2 · Spec (entrevista a mano: la skill no está en la nube) | **Hecha** (falta aprobar reparto, calendario y guion) | [.plans/lewelder-spec.md](.plans/lewelder-spec.md) |
| 3 · Plan (método `/ecc:plan` a mano) | **Escrito**, espera confirmación para construir | [.plans/lewelder-plan.md](.plans/lewelder-plan.md) |
| 4 · Construir y verificar | **Software completo en simulación**: tareas 1-7 fusionadas (266 tests). Falta entrenar políticas de verdad (GPU) | `lewelder/`, `sim/`, `web/`, `firmware/`, `hardware/` |

**Spec v2 (16-11):** [.plans/lewelder-spec-v2.md](.plans/lewelder-spec-v2.md) redefine el producto: escuela-taller
donde el robot (SmolVLA multitarea por voz) monta la junta pedida (T y esquina, base fija + chapa móvil imantada),
la señala y demuestra la soldadura; reconocimiento 3D estéreo por ArUco por chapa; el alumno suelda con gatillo +
apoyo; sin repaso de huecos. Plan v2 aprobado ([.plans/lewelder-plan-v2.md](.plans/lewelder-plan-v2.md)); contrato v2 hecho; tareas 1-5 en marcha en paralelo. **Tono arcade** (spec v2, 0.1): demo divertida, puntos, combos, ranking, robot con personalidad.

**Análisis de viabilidad (16-11, noche) · demo en espera de adaptar:**
- No habrá SO-101 real antes del evento: todo lo entrenado esta semana sirve para practicar el flujo, no da un
  modelo. El dataset y el modelo reales se hacen allí (1-2 vueltas de grabar → entrenar como mucho).
- Estimación: la parte humana (pedir, reconocer, soldar, nota, tablet) es muy viable; el montaje con SmolVLA a 8/10
  el sábado a las 20:00, poco probable; "coge la antorcha y suelda" con el VLA, muy improbable (anunciarlo como replay).
- Enfoque aceptado por el usuario: al VLA, órdenes fáciles de teleopear y aprender (coger y dejar con 2-3 variantes
  elegidas por voz) donde se vea que una sola red hace cosas distintas según la frase; lo que necesita precisión
  (soldar), con replay o ACT. Inferencia local en la GTX 1660 como principal (medirla), nube de respaldo; la voz con
  Web Speech necesita internet (botones de respaldo). Puntos de decisión con números (vie 23:00 dataset ≥ 50
  episodios; sáb 12:00 primer modelo; sáb 20:00 si < 5/10, el plan B pasa a relato principal).
- Riesgos abiertos: segundo puesto de grabación (hace falta otra pareja guía + seguidor), wifi del evento, apoyo
  < 2 mm medido con el estéreo real, integración (tarea 6b) sin hacer, `robot_remoto.py` sin hacer.
- **Se espera a que la organización publique más información del hackathon** (criterios, material, wifi) para
  rediseñar la demo y hacerla espectacular.
- Orden pendiente: `main` en GitHub está atrasada (el trabajo está en `main-9d41os`); anular el token de HF.

**Lecturas (18-11):** conocimiento extraído del tutorial de Hugging Face, ACT, SmolVLA, surveys de VLA y la doc de
LeRobot 0.7 en [investigacion/lecturas/](investigacion/lecturas/README.md), con las conclusiones que afectan al plan.

**Proyectos de referencia (18-11):** 37 proyectos (ganadores de hackathons 2025-2026 y top de Hugging Face) con
análisis y nota con nuestra rúbrica en [investigacion/proyectos/](investigacion/proyectos/README.md).

**ELEGIDO: ASPIRA (19-11).** Compañero de escritorio que aspira mientras taladras madera pequeña o maquetas:
acerca la boca al taladro quieto, se congela mientras taladras, la aspiradora se enciende sola (acelerómetro +
Arduino) y, al retirar el taladro, el VLA limpia el agujero nuevo aunque se mueva la tabla, o la viruta de la
alfombrilla. **Brief v1:** [.plans/aspira/BRIEF-aspira.md](.plans/aspira/BRIEF-aspira.md) (incluye el análisis para
ganar: jurado simulado 63 → ~75-80 con adaptaciones). Material del usuario: aspiradora, taladro a batería, tablas,
manguera corrugada. **Pendiente: respuestas del usuario a las 5 decisiones del apartado 11 del Brief.** La spec
anterior (`spec-aspira.md`) queda superada por el Brief.

**ÁREA DE TRABAJO REAL Y SITUACIONES (19-11, noche).** Medidas del usuario:
- mesa 1200 × 600 × 750;
- tapete 450 × 400;
- madera 300 × 200 × 18;
- robot en el borde de atrás, de frente a la persona.

Hechos:
- escena realista: taladro de batería con mano, cámaras y pértiga;
- mapa de alcance: acompaña hasta ~220 mm, limpia la madera hasta ~290;
- catálogo de 16 situaciones con la postura exacta de cada una: [.plans/aspira/situaciones.md](.plans/aspira/situaciones.md),
  pendiente de acordar con el usuario (6 decisiones abiertas);
- visor 3D en el PC del usuario: `herramientas/ver_garbi.bat` trae lo último de GitHub y abre `python -m garbi.ver`.

Tests de visión por adaptar a la nueva cámara y madera.

**GARBI · SIMULACIÓN COMPLETA (19-11).** Aspira pasa a llamarse **Garbi**. Decisiones del usuario: sin
acelerómetro (la aspiradora la enciende Garbi con un Arduino y un enchufe), se acerca solo al taladro quieto, lijado
a mano en nivel 3, vinilo negro en la tabla y alfombrilla azul, híbrido y con el VLA visible. Hecho en `garbi/`
(tests: `tests/test_garbi*.py`, 30 en verde; render sin pantalla con `MUJOCO_GL=egl` u `osmesa`):
- `escena`/`mundo`: SO-101 con boca de aspiración en la pinza, alfombrilla con 4 ArUco, tabla mocap con 2 ArUco,
  agujeros, viruta, taladro con bola naranja; aspiración simulada (radio 24 mm, altura ≤ 30 mm).
- `control`: IK propia con prioridad de posición, gestos (aparcar, acercarse al taladro, zigzag, limpiar la tabla).
- `robot_vivo`: orquestador (aparcado → acercarse → acompañar → esperar → limpiar → aparcar, congelado si el
  Arduino calla); órdenes «ven», «retírate», «otro lado», las 2 del VLA y «limpia la tabla». `arduino`: protocolo y
  latido de seguridad.
- `vision`: calibración con los ArUco de la alfombrilla, tabla por ajuste rígido de las esquinas (con memoria si se
  tapan), punta de la broca por la bola naranja, viruta por color solo dentro de la alfombrilla. Error: cámara ~2 mm,
  tabla ≤ 2 mm/3°, broca 2-5 mm.
- `escenario` + `video`: ciclo completo con el «juez» simulado. **Con percepción por cámara, 6/6 semillas: boca a
  30-38 mm de la broca, agujero y alfombrilla limpios del todo, ~18 s.** Vídeo: `python -m garbi.video --vision`.
- `demostraciones`: dataset LeRobot de limpieza (2 órdenes, agujeros viejos limpios como distractores, filtro «aprende
  del mejor»). `politica`: habilidad VLA supervisada (límite de velocidad y altura, fin por viruta vista o política
  quieta).
- El usuario **no quiere entrenar ahora**: la simulación es para ver cómo debe comportarse. Cómo entrenarlo con el
  robot real (qué aprende el VLA, cómo grabar, cuántos episodios, comandos, evaluación): [garbi/entrenar.md](garbi/entrenar.md).
  Vídeos: `python -m garbi.video --vision` (ciclo) y `--demostraciones 6` (lo que aprende el VLA).
- **Boquilla a 30° (19-11, decisión del usuario):** recta, de 110 mm, aspira a 30° al acompañar y al limpiar.
  Llega de lado, con holgura comprobada con el taladro. El «apunto» lo hace la cámara del robot, al costado de la
  boquilla: ve la broca y corrige la estimación de arriba (1-2 mm de error, también con el taladro inclinado 8°).
  Análisis y resultados: [.plans/aspira/montaje-boquilla.md](.plans/aspira/montaje-boquilla.md). Vídeos:
  `--vision` y `--vision --inclinacion 8`.
- **Viabilidad técnica real (19-11):** [.plans/aspira/viabilidad-tecnica.md](.plans/aspira/viabilidad-tecnica.md).
  Núcleo programado: alta, con mitigaciones. Datos: alta, con autodemostraciones (Garbi limpia con la línea base y
  graba). Entrenar: media (ACT en local, SmolVLA solo en la nube, una iteración). SmolVLA en directo: media-baja.
  Tres riesgos con solución medida:
  - **par del hombro:** manguera suspendida, boquilla ≤ 100 g, vigilar temperatura, servos de 12 V si se puede;
  - **calibración:** apunto relativo en lazo cerrado (~1,5 mm con cualquier error) y falda de cepillo;
  - **latencia de SmolVLA:** ~1,2 s/chunk en CPU, el límite asíncrono es 0,83 s; GPU o media velocidad.

  La ejecución asíncrona ya está hecha. Puertas G1-G5 el viernes.
- Siguiente (hoy): imprimir el soporte de la boquilla y preparar la pértiga de la manguera; implementar el adaptador
  real (`MundoReal`), el apunto relativo y la vigilancia de temperatura; firmware del Arduino. Después, guion de la
  demo.

**BRIEF COMPLETO (18-11, noche) · pendiente del «sí» del usuario:** el usuario dejó a Claude al mando para destilar
toda la investigación y entregar un Brief. Proceso: directrices → 5 generadores (13 conceptos) → 2 evaluadores y
jurado simulado → 2 finalistas → consejo de 4 voces → equipo rojo → 3 especialistas (técnico verificado en el código
de LeRobot v0.7.0, hardware con alcance calculado en MuJoCo, demo y pitch) → 5 rondas de `santa-method`. Resultado:
**Aprendiz**, el aprendiz de un banco de reacondicionado de portátiles (SO-101 + SmolVLA trae al plato el objeto
que se nombra desde un almacén al fondo del banco). Brief: [.plans/brief/BRIEF-aprendiz.md](.plans/brief/BRIEF-aprendiz.md)
(v4.5); página visual: https://claude.ai/artifact/7jyaHNL641B2JCUKPYde52 ; registro de revisión y sugerencias
pendientes: [.plans/brief/revision-santa.md](.plans/brief/revision-santa.md). Debilidades declaradas: U1 y U7 sin
resolver (necesidad sin confirmar; analogía con kits de almacén). Siguiente paso con el «sí»: cita real y medida a
mano el jueves, spec v3 con `interview` y plan.

**Consejo de industria (18-11, noche):** a petición del usuario se buscaron ideas de producción e industria (24 ideas,
filtro y consejo en `.plans/necesidad/`). Veredicto: **Machero** (colocar machos de arena de la referencia pedida en
un molde de fundición y apartar los rotos), con validación antes del viernes y **Calidad (cuarentena por lote)** de
plan B. Ver [.plans/necesidad/consejo-veredicto.md](.plans/necesidad/consejo-veredicto.md). **El usuario rechazó Machero** (18-11): se buscan ideas nuevas de industria derivando los mecanismos de los 37 proyectos de referencia (`.plans/necesidad/ideas-desde-*.md`).

**Necesidad real (18-11, noche):** el usuario ve que a Relevo le falta una necesidad real. Tres investigaciones
con fuentes y diagnóstico `product-lens` en [.plans/necesidad/diagnostico.md](.plans/necesidad/diagnostico.md).
Relevo tal cual no existe en planta. Candidatas: **B · triaje de baterías en reciclaje de RAEE** (recomendada),
A · pañol que prepara el kit de la orden de trabajo, C · acercar objetos a personas con movilidad reducida.
Pendiente: elección del usuario, validación con llamadas antes del viernes, `santa-method` sobre cifras e `interview`.
Plugins: la instalación con `claude plugin` la bloquea el sistema de permisos de la nube; las skills se aplican a mano
leyendo los repos clonados.

**PARA RETOMAR EN LA SESIÓN NUEVA (18-11, tarde):**
- Rama de trabajo: `claude/vigilant-franklin-xjlncg` (contiene `main-9d41os` + todo lo del 17-18; `main` está atrasada).
- Plugins: `.claude/settings.json` activa `jmo-workflow` y `ecc`. Si no aparecen sus skills, instalarlos con
  `claude plugin marketplace add 23jmo/jmo-skills`, `claude plugin marketplace add affaan-m/everything-claude-code`,
  `claude plugin install jmo-workflow@jmo-skills --scope project` y `claude plugin install ecc@ecc --scope project`.
- En curso: **trabajar más a fondo la idea Relevo** antes de decidir (el usuario no quiere cambiar de idea todavía sin
  analizar bien la práctica). Siguiente paso: `/jmo-workflow:interview` sobre Relevo. Preguntas pendientes:
  (1) tipo de repuesto: objetos industriales grandes reales o réplicas 1:1 (módulos DIN, fusibles NH, baterías de
  herramienta, cartuchos) frente a bloques simbólicos; los componentes reales pequeños (condensador) son inviables
  para el robot; (2) qué máquina se avería (cuadro eléctrico, minicinta, herramienta a baterías, ventilador);
  (3) quién retira el módulo averiado (juez, robot, nivel 3); (4) material que tiene Andoni (ESP32, reed/Hall,
  imanes, motor/LED). Duda del usuario: credibilidad y practicidad de "encajar componentes".
- Material del brainstorming: `.plans/brainstorming/` (contexto abstracto, 15 ideas, filtro, consejo, decisión).

**Brainstorming de la demo (18-11):** proceso sin sesgo (15 ideas nuevas + LeWelder, filtro, consejo de tres voces).
Propuesta: **Relevo**, taller de mantenimiento (el juez avería una minimáquina; SmolVLA coloca el repuesto correcto y
la máquina arranca). LeWelder se aparca. **Pendiente del sí del usuario.** Ver
[.plans/brainstorming/decision.md](.plans/brainstorming/decision.md).

**Siguiente paso (antes del análisis):** dataset grande (~160 demostraciones filtradas), entrenar ACT (GTX 1660) y SmolVLA (nube con GPU),
evaluar VLA frente a ACT y grabar el vídeo de la demo en simulación. Ver `robot/entrenar.md`.

**Datos en Hugging Face (privados, usuario Izaguirre97):** `lewelder_sim_8` (8 demostraciones, pruebas) y
`lewelder_sim_160` (158 demostraciones filtradas con nota >= 9: 20 por anclaje y tipo salvo la recta de A con 18;
el filtro descartó las 16 malas a propósito y 2 buenas que el brazo ejecutó mal). Pendiente: anular el token de HF
que se pegó en el chat el 16-11.

**Fallo abierto:** el planificador de `sim/demostraciones.py` da por buenos algunos planes que al ejecutarse se
desvían ~190 mm (recta en A, semillas 59 y 77): probablemente un salto de la muñeca. El filtro los descarta.

**Entrenamiento de respaldo en CPU (16-11):** ACT con `lewelder_sim_160`, ~6000 pasos en ~3 h (`salidas/act_cpu_160`,
no subido). Evaluado en B y C: ya llega al cordón pero con 10-14 mm de error, 0 % de éxito. Hace falta GPU (HF Jobs:
falta recargar crédito; script `herramientas/entrenar_hf_jobs.sh`). Demo en vídeo para el móvil publicada como
artifact privado (https://claude.ai/artifact/9KXcbqUXQVJmnaU73CadRB).

**16-11 noche:** CAD v2 en SolidWorks subido por Andoni (`hardware/v2/cad/`, con STL); el contrato se alineó con
él (esquina en Y 31, mango del soporte a 116). Entrenamiento en GPU de HF Jobs probado: ACT 200 pasos en una L4 en
2 min 18 s (~0,14 s/paso, batch 16), modelo subido a `Izaguirre97/act_lewelder_prueba`. Tareas v2 hechas: 3 (voz y
Chispas), 4 (apoyo, fantasma, puntuación arcade, alcance), 5 (hardware). En marcha: 1 (estéreo), 2 (montaje en
simulación), 6a (interfaz blueprint).

**Para retomar (16-11, noche):**
- Regla del usuario: **no se imprime nada hasta validarlo en simulación con las piezas reales del CAD** (salvo, si
  quiere, la pieza de prueba de imanes).
- El usuario quiere un **simulador de la demo completa en el navegador** (`python -m lewelder.simulador`, puerto
  8080): mesa 3D con el SO-101 en tiempo real y las piezas del CAD, el juez con el ratón (antorcha, gatillo, apoyo,
  órdenes a Chispas, mover la base) y la tablet al lado; modo "demo de jurado". Lo verá en su PC con Windows
  (correrlo en local con `http://localhost:8080`).
- Subagentes lanzados el 16-11 en worktrees de la nube (su trabajo solo llega al repo al fusionarlos; si la sesión
  se pierde, hay que relanzarlos con los mismos encargos del plan v2): tarea 1 (estéreo + `validacion_vision.md`),
  tarea 2 (montaje en MuJoCo con los STL reales + `validacion_sim.md`), tarea 6a (interfaz blueprint en `web/v2/`) y
  el simulador. Pendiente después: tarea 6b (servidor v2 + tablet integrados), tarea 7 (robot/políticas v2,
  servidor de políticas remoto, entrenamiento SmolVLA multitarea en HF Jobs), tarea 8 (vídeo y pitch).
- HF Jobs probado y con crédito (`herramientas/entrenar_hf_jobs.sh`). Token de HF pegado en el chat: anularlo al
  terminar los entrenamientos.
- Compras: imanes Ø4×4 N52 (20) y Ø10×3 (20); 2.ª webcam igual que la primera, FOV horizontal ≥ 78°.

**Demo en simulación:** `PYTHONPATH=$PWD MUJOCO_GL=egl HF_HUB_OFFLINE=1 .venv/bin/python -m lewelder.servidor --fuente
simulada --robot mujoco --politica replay --dataset datos/lewelder_sim` y abrir `http://<ip>:8000/`. Hoy solo replay
suelda bien (100 % en los 4 anclajes); ACT (600 pasos) y SmolVLA (200 pasos) entrenados en CPU no llegan al cordón.

**Decisiones de la fase 4:** anclajes definitivos en fila (A girado -90°, B-D a 0°) validados en simulación; losetas
unidas en una base de ~570 x 145 mm impresa por tramos; webcam de seguimiento a 750 mm, 25° de inclinación y azimut
-50° (ve la T en los 4 anclajes); antorcha del robot atravesada en la pinza y cámara de muñeca delante de los dedos;
LLM del instructor `claude-opus-5-5` con esfuerzo bajo (cambiable con `LEWELDER_MODELO_LLM`). Construyen Andoni (hardware) y Claude
(software); demo completa en simulación antes del jueves 19.

**Cambios de la última sesión (15-11):** política principal = **SmolVLA multitarea** con la instrucción escrita por la
app (la organización/jurado quiere VLA); ACT por unión como respaldo; objetivo 8/10 a ±5 mm por anclaje el sábado
20:00; 2.º SO-101 = posicionador aprendido por la misma VLA (nivel 3); microcontroladores ESP32 o Arduino por USB.
Andoni mira el 16-11 si hay ESP32 e IMU y hace el pedido.

**Plugins:** `jmo-workflow` (23jmo/jmo-skills) y `ecc` (affaan-m/everything-claude-code) instalados a nivel de proyecto
en `.claude/settings.json`; se cargan al empezar una sesión nueva.

**Entorno de simulación (nube, 15-11):** `.venv` con Python 3.12, LeRobot 0.7.0 (ACT y SmolVLA probados: 2 pasos de
entrenamiento en CPU cada uno), PyTorch 2.15 CPU, MuJoCo 4.0.1 con render EGL sin pantalla, OpenCV 4.13 con ArUco,
Playwright (usar `executable_path='/opt/pw-browsers/chromium'`), `arduino-cli` con AVR, ESP32 y librerías BNO055 y
MPU6050. Reinstalar: `./instalar.sh` (Python) y `herramientas/setup_nube.sh` (todo). **Todo el desarrollo y la demo
previa son en simulación** (Andoni no tiene tiempo de ejecutar en físico antes del evento).

## Contexto clave

- **Equipo:** 3 personas. Dos de software + IA (sin experiencia previa en LeRobot) y Andoni (producto, CAD con
  SolidWorks, impresión 3D, electrónica).
- **Hackathon:** 48 h, 140 plazas, 18-35 años. Entrega domingo 11:00 (presentación, dataset, código), pitch de 5 min y
  demo en vivo ante jurado. Premios y criterios no publicados. En 2025 hubo premios a Mejor Proyecto (1.250 €),
  Más Innovador (875 €) e Impacto Social (875 €) + 3.000 € en productos NVIDIA.
- **Material confirmado por la organización (15-11):** por equipo un par de SO-101 (guía + seguidor), una cámara y un
  trípode; SO-101 extra si sobran; se permite setup propio; no ponen impresoras.
- **Principio:** "es más importante no perder que ganar". Las causas de derrota y la rúbrica supuesta están en
  [análisis de concursos](investigacion/analisis-concursos.md).

## Investigación hecha

- [investigacion/analisis-concursos.md](investigacion/analisis-concursos.md): Robotekin 2026, Bilbao 2025, LeRobot
  Worldwide 2025 (comparación de 115 equipos), CCSF 2026 y AMD 2025. Por qué se gana, por qué se pierde, rúbrica
  supuesta y filtro de 7 puntos.
- [investigacion/ideas-desarrolladas.md](investigacion/ideas-desarrolladas.md): ideas finalistas (soldadura, Lote 1,
  médico de máquinas, desmontaje circular) y condiciones confirmadas por la organización.
- Ganador Bilbao 2025: camarero con IA (voz → Gemini con personaje → ACT, tablet con app). Ganador Robotekin 2026:
  MSN (linterna para soldadura, ACT + IBVS + voz).

## Código y entorno

- `assets/so101/`: modelo MuJoCo oficial del SO-101 (TheRobotStudio/SO-ARM100, Apache-2.0).
- `sim/cinematica.py`: cinemática inversa cenital del SO-101 (probada: error < 1 mm en la mesa).
- `herramientas/`: scripts de exploración del modelo (`explorar_modelo.py`, `explorar_pinza.py`, `medir_dedos.py`).
  `medir_dedos.py` calcula almohadillas de colisión de la pinza; su última versión no llegó a ejecutarse.
- Simulación pendiente: escena con mesa, piezas y cámaras; demostraciones; entrenar ACT; evaluar.
- Entorno local de Andoni (no se sube): `.venv` con Python 3.12 y PyTorch CUDA 12.8 (GTX 1660 6 GB). LeRobot 0.7.0 y
  MuJoCo aún sin instalar en ese `.venv`.
- LeRobot 0.7.0 (5-11-2026): ACT, SmolVLA, pi0.5, GR00T N1.7; `lerobot-record`, `lerobot-train`, `lerobot-rollout`;
  servidor de políticas remoto; sesiones de rollout con control programático.

## Pendiente con la organización

- Wifi estable para nube y APIs; si se puede traer código o modelos preparados de antes.

**PLAN TÉCNICO v2 (19-11, noche).** [.plans/aspira/plan-tecnico.md](.plans/aspira/plan-tecnico.md), reescrito
corto y por la demo:
- tarea de los 5 intentos: el ciclo completo de un agujero, y al final una pasada por toda la madera que no puntúa;
- todo fijo salvo limpiar la zona del agujero, que hace **ACT**; sin VLA (decisión del usuario);
- entrenamiento en HF Jobs y ejecución en el portátil;
- la aspiradora la lleva el usuario: Garbi solo da la señal «aspirar sí/no».

Especificación por módulo: [.plans/aspira/especificacion-tecnica.md](.plans/aspira/especificacion-tecnica.md) (decisiones cerradas).
Siguiente: visión sin ArUco, adaptador del robot real y maqueta con 5 ciclos y el cierre.

**CONSTRUCCIÓN EN SIMULACIÓN (20-11).** Tareas 1-6 de [.plans/aspira/plan-construccion.md](.plans/aspira/plan-construccion.md)
fusionadas:
- percepción sin ArUco, ciclo, habilidad de limpieza y grabador ACT, cuerpo real y simulado, maqueta, integración;
- `python -m garbi.correr --sim`: 5/5 aciertos con percepción real (imágenes renderizadas), 26-28 s por ciclo;
- zona donde funciona el ciclo completo: 320-420 mm del eje del robot.

Abierto:
- holgura real con el taladro de 0,9-4,6 mm en algunos sitios (la especificación pide 10): falta sumar el error de
  la percepción al margen;
- probar en el robot real.

**AMARRE DE LA BOCA Y BRIDAS (20-11 y 21-11).** [hardware/garbi/README.md](hardware/garbi/README.md):
- CAD paramétrico (`hardware/garbi/amarre_boca.py`, STEP + STL), con la geometría de la simulación:
  - placa atornillada a la cara -y de la caja del servo de la pinza con los 2 M2 del servo, 5 mm más largos;
  - brazo por debajo del tubo, abrazadera partida con 2 M3, anillo verde y 4 sillas para las bridas.
- 21-11: el tubo atravesaba el brazo de la primera versión; corregido.
- Estudio de visibilidad con la cámara de la muñeca: sacar la boca más adelante o bajarla empeora.
- Elegido: boca a 7° (antes 15°), anillo de 35,4 mm y abrazadera separada: el anillo se ve 2,4 veces más.
- `BORDE_LIMPIEZA` sube de 6 a 7,5 mm (`garbi/ciclo.py`).
- Tests de Garbi: 176 pasan, 12 fallan y 5 dan error. Son los mismos fallos que con el diseño anterior (falta LeRobot
  en la nube y ciclos de robustez), ninguno nuevo.
- Pendiente: medir el diámetro exterior del tubo (por defecto 29 mm) y regenerar con `--tubo`.

**SOLUCIÓN FINAL CONSTRUIDA (20-11).** [.plans/aspira/solucion-final.md](.plans/aspira/solucion-final.md):
- **Percepción final:** madera clara con pegatina, manos (color y MediaPipe), taladro agarrado (mano + taladro) y
  eventos de clavado y levantado.
- **Ciclo final** (`garbi/ciclo_final.py`): descanso, despierto, prudente, acercamiento (ACT, con respaldo
  programado), retirada y limpieza.
- **Herramientas del sitio** (cámaras, color, calibración, prueba del robot, teleoperación con grabación) y guía en
  `docs/garbi-guia-hackathon.md`.

Resultado en simulación:
- con la verdad de la simulación, 5/5;
- con la percepción, 3/5: falta que la clavada se vea siempre y que la postura de partida de ACT sea la misma al
  grabar y al ejecutar.

Falta entrenar ACT con datos reales.
- **20-11, tarde:** con la percepción por imágenes, el ciclo final da 5/5 intentos y 2/2 variantes (3 semillas y la
  madera movida). La postura prudente pasa a mirar la broca con la cámara de la muñeca desde ~180 mm; es la partida
  de ACT.

**PRODUCTO FINAL (21-11).** Comportamiento acordado con el usuario en [.plans/aspira/producto.md](.plans/aspira/producto.md):
- círculo morado, una sola política (ACT o círculo + matriz 5×3) y barridos de la tabla y del tapete;
- app con LLM y seta.

Código en `garbi/producto/`. **Contexto para el Claude Code del PC del equipo:**
[docs/CONTEXTO-LOCAL.md](docs/CONTEXTO-LOCAL.md).
