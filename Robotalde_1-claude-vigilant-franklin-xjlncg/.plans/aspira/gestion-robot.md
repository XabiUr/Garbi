# Aspira · cómo gestiona el robot cada proceso (control y aprendizaje)

19-11-2026 · especialista de control y aprendizaje · LeRobot v0.7.0 + SO-101. Lo comprobado en el código del clon
v0.7.0 lleva ruta (`src/lerobot/...`); lo demás es diseño o va marcado **[sin verificar]**. Procesos y distancias
según `procesos.md`: **P1 taladrar en una marca** (nivel 1), **P3 lijar el canto con lijadora de palma o P4 a mano**
(nivel 2), **P8 atornillar como control negativo** («no ir»), y la caladora **descartada para la sala** (P5: hoja
expuesta bajo la pieza, ruido). Regla física que fija las tolerancias: la boca debe quedar a **30-60 mm** de donde
nace el polvo (a 10 cm ya casi no capta), así que ±1 cm del SO-101 basta y alejarse «por seguridad» no vale.

## 0. Las tres reglas que lo ordenan todo

1. **El robot coloca y se queda quieto; la persona trabaja.** En N1 y N2 el robot **nunca se mueve con la
   herramienta en marcha**: se coloca antes y se retira después. Por eso la política aprendida no tiene que ver nunca
   una broca girando ni polvo en el aire (clave para grabar con la herramienta apagada, apartado 7).
2. **Se aprende lo que depende de lo que se ve y de la frase** (qué boquilla, dónde está la marca, cómo agarrar);
   **se programa lo que tiene que ser exacto o seguro** (mantener, retirar, vigilar, parar, seguir algo que se mueve).
   Es el patrón de MSN (ACT para coger la linterna, IBVS programado para apuntar y esquivar; 1.º en Vitoria) y de los
   ganadores de París (habilidades troceadas + selector programado).
3. **Seguir una lijadora en marcha queda fuera de los 5 intentos** (N3, en el pitch). Ver apartado 3.

## 1. Arquitectura por capas

| Capa | Qué hace | Aprendido / programado | Dónde corre |
|---|---|---|---|
| 0 · Seguridad | Límite de paso por servo, zona prohibida, vigilante visual, «el robot no se mueve con la herramienta en marcha», retirada | Programado | `--robot.max_relative_target` (campo de `robots/so_follower/config_so_follower.py:36`, aplicado en `so_follower.py:206`) + `aspira/vigilante.py` |
| 1 · Orquestador | Máquina de estados por proceso; elige la frase, lanza y corta segmentos, detecta inicio y fin | Programado | `aspira/puente.py` (subproceso `lerobot-rollout --interactive`) |
| 2 · Habilidades | «Coger la boquilla adecuada y dejarla junto a la marca o el borde»; «devolver la boquilla» | **Aprendido** (SmolVLA multitarea; ACT por orden de respaldo) | Dentro de `lerobot-rollout` |
| 3 · Lenguaje | Voz en español → frase canónica en inglés (enum cerrado) | Reglas + LLM (inventario: `lewelder/voz.py`) | `aspira/voz.py` |
| 4 · Seguimiento (N3) | Mantener la boquilla detrás de la lijadora | Programado (PBVS en el plano de la mesa) | Bucle propio `aspira/seguir.py`, fuera del rollout |

**Por qué así.** Un VLA con 50 demos por orden coloca bien un objeto respecto a algo que ve (es lo que hace
SmolVLA en SO-101: 90 % en Pick-Place-Lego, `panorama-vla.md`), y la frase cambia **qué objeto** coge, que es lo que
mejor hace. En cambio, mantener sin deriva, retirarse por un camino conocido y parar ante la mano no admiten un 80 %:
se programan. **Limitación verificada:** `lerobot-rollout` es dueño del puerto serie, así que las capas programadas
que mueven el brazo solo pueden ser las que da el propio rollout (fin de segmento = «Robot is holding position»,
`rollout/interactive.py:191`; `/reset` = vuelta interpolada en articulaciones a la postura de arranque,
`rollout/configs.py:347-350`). El seguimiento (capa 4) exige un bucle propio con `SO101Follower` y
`robot/politica.py` (`PoliticaLeRobot` ya hace la inferencia de 0.7): por eso es N3.

**Mapa fase → mecanismo (ruta del rollout, N1/N2):**

| Fase | Mecanismo | Quién decide el fin |
|---|---|---|
| Aparcado | Postura de arranque del rollout (lanzar con el brazo aparcado) | — |
| Coger boquilla + acercarse + colocarse | `/subtask <frase>` + `/start`; segmento aprendido de `--duration=18` | Fin del segmento (las demos acaban con 3 s quietas) |
| Mantener | El rollout se queda en su postura al acabar el segmento (verificado) | Fin del proceso (apartado 2.4) |
| Retirarse | `/reset`: vuelve interpolando a aparcado **con la boquilla en la pinza** | Rollout |
| Devolver boquilla | `/subtask Put the nozzle back.` + `/start` (sale siempre de aparcado: fácil de aprender) | Fin del segmento |
| Aparcar | `/reset` | Rollout |

`--duration` es único por lanzamiento (`configs.py:307`): 18 s vale para las dos habilidades si las demos de colocar
duran ≤ 15 s y las de devolver acaban quietas en aparcado. El camino de `/reset` en articulaciones desde una postura
baja **[sin verificar que no barra la pieza]**: probarlo el viernes 18:30; si barre, aparcado más alto.

## 2. Por proceso

### 2.1 Plantilla común (soporte de boquillas fijo a la izquierda del brazo, zona de trabajo A4 delante)
Boquillas impresas en PETG con **asa común** (mismo agarre para la pinza de 2 dedos) y color distinto (redonda
naranja, plana azul) para que la cámara las distinga. Tramo final de tubo fino (Ø 20-25 mm) para que la boquilla
más el tubo sigan por debajo de ~150 g en la pinza **[est., procesos.md §4]**. Las dos cámaras: `top` (fija, ve soporte, zona y marca)
y `wrist` (ve la marca y el borde en el acercamiento). Manguera colgada del pescante: el SO-101 solo carga la
boquilla (decenas de gramos).

### 2.2 Tabla de procesos

| | Taladrar en una marca (N1) | Lijar un borde (N2) | Lijar una zona (N3) | Atornillar (P8, control negativo, N2) |
|---|---|---|---|---|
| Frase (inglés, ≤ 30 car.) | `Help me drill at the mark.` | `Help me sand the left edge.` / `Help me sand the right edge.` | `Help me sand the center.` (+ seguir) | `I will drive a screw.` |
| Boquilla (la elige la política) | Redonda | Plana ancha (15 × 100 mm) | Plana | Ninguna: se queda aparcado |
| Postura objetivo | A ras de la tabla, boca a 20-40 mm del eje de la broca (borde ≥ 15 mm del filo), inclinada 30-45°, lado opuesto a la mano; **nunca encima del eje** | Fija en el canto nombrado, a ras, 20-50 mm del borde del plato: con boquilla de 10 cm y pieza estrecha (≤ 12 cm de canto) **el canto entero queda cubierto sin moverse** | A 20-50 mm del borde del plato, del lado al que va el polvo | Postura de aparcado (demos de 8 s «quieto») |
| Percepción | Marca (pegatina roja de 2 cm) en `top`; `wrist` en el último tramo | Borde de la pieza en `top` y `wrist` | ArUco en el costado de la lijadora, cámara `top` | Destornillador en la mano, marca en la tabla |
| Tolerancia | ±1 cm (ventana útil 20-40 mm, `procesos.md` §0 [est.]; medir el jueves con la aspiradora) | ±1,5 cm a lo largo, ±1 cm al canto | Retraso ≤ 1 s; borde del plato a 20-50 mm | No sale del aparcado |
| Fase «mantener» | Quieto (fin de segmento) | Quieto | **Seguir** (bucle propio) | — |
| Polvo esperado | Anillo alrededor del agujero, viruta gruesa en pino | Fino, escapa por la periferia del plato y cae por el canto | Fino, abanico en la periferia | Nulo |

### 2.3 Fases y órdenes del caso N1 (taladrar)
1. Persona: «voy a taladrar aquí» (la marca ya está pegada; «aquí» lo resuelve la visión, no la voz).
2. Voz → `Help me drill at the mark.` → pantalla y voz: «Drilling: round nozzle». Interbloqueo: si el micro oye la
   herramienta en marcha, no se lanza `/start`.
3. Segmento aprendido (~15 s): coge la redonda, se acerca, se coloca, se queda quieto 3 s.
4. Comprobación programada (vigilante, `top`): boquilla naranja a 1,5-4 cm de la marca y fuera del círculo de 1,5 cm
   alrededor de ella → pantalla verde + pitido «Ready». Si falla: `/reset` y un reintento automático; al segundo
   fallo, «Not ready» y se avisa.
5. La persona taladra. El robot mantiene.
6. Fin → `/reset` (retira) → `Put the nozzle back.` → `/reset`.

### 2.4 Cómo sabe que el proceso empieza y termina
| Señal | Uso | Fiabilidad |
|---|---|---|
| **Botón grande en la tablet / pedal USB** («Done») | Primario en los 5 intentos: no toca el robot | Alta |
| Voz «done», «listo», «ya» | Igual que el botón | Media (ruido del pabellón) |
| Sonido de la herramienta (RMS del micro, umbral calibrado in situ; on → off durante 1,5 s = fin) | Automático y vistoso; además interbloqueo «no moverse con la herramienta en marcha» | Media **[sin verificar el ruido del evento]**: confirmar con el botón |
| Visión (la herramienta con ArUco sale de la zona) | Respaldo del fin y del vigilante | Media |

## 3. El caso difícil: seguir una lijadora que se mueve

| | (a) VLA aprendido con demos de seguimiento | (b) Zonas discretas por orden | (c) Control visual programado + agarre aprendido |
|---|---|---|---|
| Qué es | Teleoperar el seguimiento de una lijadora movida por otra persona | `left edge`, `right edge`, `center`: cada una es una colocación estática aprendida; la persona cambia de zona con la voz (`/subtask`) | ArUco en la lijadora; `top` + pose de la mesa (`lewelder/seguimiento.py`: `detectar_marcadores`, `estimar_pose_mesa`) → objetivo en el plano detrás de la lijadora → IK (`sim/cinematica.py`) a ≤ 3 cm/s con zona muerta de 2 cm |
| Datos | Muchos y malos: el movimiento humano no se repite; la demo varía en cada episodio | 30-40 por zona, como taladrar | El agarre de la boquilla (el mismo de N1) |
| Reacción | ACT ejecuta 100 acciones (3,3 s) en lazo abierto por defecto (`configuration_act.py:85-103`); SmolVLA, trozos de 50 con RTC: llega tarde | Segundos tras la orden; no sigue, salta | 10-30 Hz, determinista |
| Probable en 48 h | Bajo (nadie en los hackathons revisados lo ha hecho) | Alto (igual que N1) | Medio-alto: MSN lo hizo en 48 h con IBVS; nosotros tenemos calibración y ArUco ya escritos (PBVS, más sencillo que IBVS con Broyden) |
| Riesgo | Movimiento brusco junto a la lija en marcha | Ninguno nuevo | Requiere bucle propio, que no se puede probar con el robot hasta el viernes |

**Recomendación:** (b) entra en N2 y en la nota (la frase cambia boquilla y zona, el robot nunca se mueve con la
lijadora en marcha: la persona dice «now the right edge» con la lijadora parada). (c) es N3, fuera de los 5
intentos, enseñado en el pitch con la lijadora encendida, velocidad limitada y la regla de distancia del apartado 5.
(a) se descarta: más datos, peor reacción y más peligro. Argumento clave: con una boquilla plana de 10 cm y una pieza
pequeña, **lijar un borde ya no exige seguir**: convertimos el caso difícil en uno estático por diseño.

## 4. Lenguaje y VLA

**Frases canónicas** (idénticas en grabación, entrenamiento y rollout; SmolVLA se preentrenó con frases cortas en
inglés que empiezan por verbo, `smolvla.md`): `Help me drill at the mark.` · `Help me sand the left edge.` ·
`Help me sand the right edge.` · `I will drive a screw.` · `Put the nozzle back.` · (N3) `Help me sand the center.`
La frase nombra **el proceso, no la boquilla**: la política aprende que «drill» = redonda, «sand» = plana y «screw»
= no moverse. Eso es el uso del lenguaje que se mide (matriz frase × boquilla). El control negativo solo prueba
algo si pasa por la política (15-20 demos de quedarse quieto con el destornillador en mano); si lo filtrara el
orquestador por regla, se dice.

**Voz → frase** (`lewelder/voz.py`, 26 tests, cambiando `contrato.ORDENES`): reglas sin red primero
(«taladr|agujer» → drill; «lij» + «izquierd|derech|centro» → sand …; «atornill|tornillo» → screw;
«guarda|devuelve» → put back; «para|stop» → parada; «calador|cort|fres|dremel» → «ese proceso no lo hago»), LLM (`instructor.crear_cliente_llm`, JSON con enum de las frases, tope 2 s) solo si
la confianza baja de 0,8. Sin confirmación SÍ/NO en N1 (gasta segundos): la pantalla muestra la frase y la boquilla
esperada y la palabra «para» la anula. Respaldo: botones con la misma línea.

**Por qué un script no basta, y cómo se demuestra:** (1) el juez pega la marca donde quiera dentro de la zona A4: no
hay postura fija que grabar; (2) el proceso que elige el juez cambia la boquilla; (3) en N2 la misma escena admite
tres órdenes distintas. Demostración: el juez elige proceso y sitio en cada intento; la pantalla muestra en vivo
`top`, la frase en inglés y la boquilla escogida; tabla publicada de la matriz y de posiciones nunca grabadas.
**Honestidad:** una tubería clásica (detectar la pegatina por color + IK + boquilla por regla) también lo haría; es la
rama C y lo decimos. El valor del VLA es una sola red para todos los procesos y posiciones nuevas sin reprogramar.

Nota: el rollout 0.7 tiene `/vqa`, `/autosteer` y `--planner.model_id` (`rollout/interactive.py:304-365`) para
políticas con cabeza de texto o un planificador externo; SmolVLA no genera texto **[sin verificar que no lo admita]**.
No se usan.

## 5. Seguridad (sin electrónica crítica)

1. **Regla de oro programada:** el orquestador solo manda `/start` con la herramienta parada (micro + botón) y nunca
   durante «mantener». En N3, velocidad ≤ 3 cm/s y objetivo siempre a ≥ 8 cm del centro de la lijadora.
2. **Límite por servo:** `--robot.max_relative_target=4` (grados por orden, `so_follower.py:206`) **[sin verificar el
   valor en el robot: probar 3-6]**. Recorta saltos de la política.
3. **Zona prohibida:** cilindro de 1,5 cm de radio alrededor de la marca (eje de la broca; borde de la boquilla
   ≥ 15 mm del filo, `procesos.md` P1) y el plato de la lijadora más 2 cm. El vigilante comprueba en `top` la boquilla (color o ArUco en su tapa) antes de dar «Ready»; si
   entra, `/reset`.
4. **La persona acerca la herramienta al brazo:** ArUco en el cuerpo de la herramienta; si su punta estimada queda a
   < 6 cm de la boquilla o la pinza mientras el robot se mueve → `/reset` (retirada a aparcado). Mientras mantiene, la
   persona manda: la boquilla va sujeta a la pinza con **imán o clip que se suelta** (fusible mecánico) y los servos
   ceden; la manguera no tira del brazo.
5. **Parada:** palabra «para/stop», botón rojo de la tablet o barra espaciadora → `/reset`. **No usar `/stop`** como
   parada: cierra la sesión y con `disable_torque_on_disconnect=True` (`config_so_follower.py:31`) el brazo cae
   sobre la pieza. Parada física de último recurso: el interruptor de la fuente del robot (también cae: la zona bajo
   el brazo debe quedar libre).
6. Gafas para quien taladra; broca y lija nunca en el campo de la teleoperación al grabar.

## 6. Tarea declarada para los 5 intentos y escalera

**Declaración (N1):** «El juez pega la marca donde quiera en la zona A4 y dice “voy a taladrar aquí”. Sin tocar el
robot, en ≤ 30 s Aspira coge la boquilla redonda y la deja quieta junto a la marca (dentro de la plantilla de 1,5-4 cm);
la persona taladra; al pulsar “Done”, el robot se retira y devuelve la boquilla al soporte.» Tiempo puntuado: orden →
«Ready» (objetivo 20 s). Éxito: boquilla dentro de la plantilla, sin contacto con la broca, devuelta al soporte.
Escena que se repone: tabla nueva o desplazada, marca nueva, cartulina negra limpia (≤ 1 min).

| Nivel | Contenido | Entra en los 5 intentos si |
|---|---|---|
| **N1** | Taladrar en cualquier punto de la zona; devolver la boquilla | Siempre (es lo declarado) |
| **N2** | + lijar canto izquierdo/derecho (palma o a mano) y «atornillar» (no va): el juez elige proceso → cambia la boquilla o no se mueve | Sáb 16:00 ≥ 8/10 en cada frase y matriz sin cruces |
| **N3** | Lijar zona con seguimiento (PBVS) o taladrar en tablero vertical (P2, boquilla debajo) | Nunca: pitch y vídeo |

## 7. Datos y entrenamiento

**¿Grabar con la herramienta apagada?** Sí, y generaliza **por diseño**: la política solo actúa antes de que la
herramienta arranque (regla 1), así que en rollout ve lo mismo que en la grabación. Variedad que sí hay que meter:
mano con la taladradora (apagada) junto a la marca en la mitad de los episodios, sin taladradora en la otra mitad,
agujeros y restos de polvo en la cartulina en 1 de cada 4 (en la demo se acumulan). Nunca teleoperar con la
herramienta en marcha. 5 episodios con la taladradora encendida **solo para validar**, no para entrenar.

| Frase | Episodios | Posiciones | Cuándo |
|---|---|---|---|
| `Help me drill at the mark.` | 50 | Marca en 5 zonas × 10 (+ giro de la tabla) | Vie 19:30-21:30 |
| `Put the nozzle back.` | 30 (15 redonda + 15 plana) | Siempre desde aparcado | Vie 21:30-22:30 |
| `Help me sand the left edge.` / `right edge` | 35 + 35 | Pieza en 3 posiciones × giro | Sáb 10:30-12:30 |
| `I will drive a screw.` | 15-20 | Destornillador en 5 posiciones; el robot no sale | Sáb 12:30 |
| `Help me sand the center.` | 30 | Solo si N3 | Sáb tarde |
| Lo que falle | 20-40 | Desde donde falló (o `dagger` si va en seco, `.plans/brief/especialista-tecnico.md` 1.2) | Sáb 14:00 |

Reglas de grabación (heredadas del brief, verificadas): un dataset por frase con `--resume --dataset.no_stamp=true`,
`merge` para SmolVLA (mismas cámaras, fps y resolución), `top` + `wrist` 640 × 480 a 30 fps, empezar y acabar en
aparcado, colocar en ≤ 15 s y **3 s quietos al final**, agarre siempre por el asa, ← para descartar.

**Ciclos:** C0 vie 23:00 (SmolVLA fusión en HF Jobs L4 + ACT drill en la 1660); C1 sáb 12:30 (+ bordes); C2 sáb
15:45 (+ correcciones). ACT: probar `--policy.n_action_steps` más bajo o `temporal_ensemble_coeff=0.01` con
`n_action_steps=1` (`configuration_act.py:119,139`) para reaccionar mejor **[sin verificar que el rollout acepte
sobrescribirlo]**. Checkpoint por X/10 en el robot, nunca por la pérdida.

**Medidas:** X/10 por frase con marca en posiciones barajadas (5 grabadas + 5 nuevas); matriz frase × boquilla
(drill / left / right / screw × redonda / plana / nada); error de colocación en mm (foto cenital con regla); tiempo orden →
Ready; **polvo**: foto cenital de la cartulina negra, % de píxeles claros, 5 agujeros con Aspira y 5 sin (y pesada si
hay báscula de 0,01 g).

**Ramas y disparadores:**
| Rama | Qué | Disparador |
|---|---|---|
| A | SmolVLA multitarea con las frases de proceso | Matriz sáb 9:30 ≥ 8/10 en drill y en bordes |
| B | Un ACT por frase; la voz elige el checkpoint (relanzar rollout, medir el tiempo el viernes) | SmolVLA ≤ 5/10, cruces en la matriz o no cabe en la 1660 |
| C | Clásica: pegatina por color en `top` + IK + boquilla por regla; aprendido solo el agarre (ACT) o nada | Sáb 14:00 ningún modelo ≥ 5/10 en drill |
| C' | Si lo que falla es coger la boquilla del soporte: una boquilla fija a la muñeca; la frase solo cambia la postura | Vie 19:30: < 8/10 agarres de boquilla por teleoperación |

## 8. Software del jueves (priorizado; 2 personas, ~9 h cada una)

| P | Pieza | Reutiliza | Horas | Hecho cuando |
|---|---|---|---|---|
| 1 | `robot/comandos.sh` (calibrar, teleoperar, grabar, entrenar, rollout con `max_relative_target`, IDs y cámaras fijos) | Brief técnico A1 | 1 | Arranca sin robot hasta el error de puerto |
| 2 | `aspira/puente.py`: máquina de estados por proceso sobre `lerobot-rollout --interactive` (tabla del apartado 1), reintento, cronómetro, nunca cerrar stdin | `guion_robot.py` (selector), patrón del brief 1.1 | 3 | Tests con tubería falsa: N1 completo, reintento, parada, «herramienta en marcha → no start» |
| 3 | `aspira/vigilante.py`: boquilla, marca y herramienta en `top`; plantilla «Ready», zona prohibida, distancia herramienta-pinza → evento a `puente` | `seguimiento.py` (ArUco, pose de mesa, filtros), `hardware/aruco/` | 2,5 | Con webcam y piezas impresas o de papel, da Ready/No y la alarma de distancia |
| 4 | `aspira/grabar.py`: lista barajada de posiciones de marca y piezas por frase, contador de válidos | Brief A2 | 1,5 | Lista reproducible con semilla |
| 5 | Voz: frases nuevas en `contrato.ORDENES`, reglas, LLM con enum; botones | `voz.py`, `web/voz.js`, tablet v2 | 1 | Tests de voz verdes con el vocabulario nuevo |
| 6 | Medida: CSV X/10, matriz frase × boquilla, script de % de polvo en la foto | `robot/evaluar.py` | 1,5 | Las tablas y el % salen de datos de prueba |
| 7 | Ensayo de la nube (SmolVLA y ACT 200 pasos) y carga local | `herramientas/entrenar_hf_jobs.sh` | 1 (+ espera) | Checkpoint cargado por `lerobot-rollout` sin robot |
| 8 | Fin por sonido (RMS del micro, umbral calibrable) | `web/v2/sonido.js` (patrón) | 1 | Distingue taladradora on/off en una grabación |
| 9 | `aspira/seguir.py` (N3): PBVS en el plano con `SO101Follower` + IK, probado en MuJoCo | `sim/cinematica.py`, `sim/entorno.py`, `seguimiento.py` | 3 | En simulación sigue un ArUco movido a mano a 3 cm/s sin entrar en 8 cm |

Total ~15,5 h: 1-7 son obligatorias (11,5 h); 8 y 9 solo si 1-7 están verdes a las 18:00. Pruebas que no se pueden
hacer hasta el viernes con el robot: camino de `/reset`, valor de `max_relative_target`, radio de captura real de la
aspiración con cada boquilla, tiempo de relanzar el rollout (rama B).
