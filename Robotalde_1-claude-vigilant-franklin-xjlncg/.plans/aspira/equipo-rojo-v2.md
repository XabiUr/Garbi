# Aspira v2 · equipo rojo técnico (jueves 19-11-2026)

Encargo: por qué no funcionará en 48 h y cómo arreglarlo. Entradas: `concepto-v2.md`, `tecnicas.md`,
`gestion-robot.md`, `hardware.md`, `procesos.md`, `equipo-rojo.md`, `../brief/especialista-tecnico.md`.
Lo que lleva ruta (`src/lerobot/...`) está leído en el clon v0.7.0; lo demás es aritmética o va marcado **[est.]**.

**Veredicto:** el concepto v2 tiene **dos productos** (un seguidor visual en tiempo real y un VLA de 4 órdenes)
encima de **un único puerto serie y una sola noche de datos**. Tal como está, el sábado a las 12:00 no hay N1. Con un
proceso propio, dos órdenes en el VLA, un sensor de vibración en vez de micrófono y el acompañamiento reducido a
«acercarse a un taladro quieto», sí [est.].

## 1. Los 8 riesgos técnicos, ordenados

| # | Riesgo | Por qué falla | Arreglo |
|---|---|---|---|
| 1 | **La aspiradora se oye a sí misma** | El micro enciende la aspiradora (74 dB(A), `hardware.md` §3) al oír el taladro; a partir de ahí el micro solo oye la aspiradora: no detecta el fin del taladro, «aspira 2 s más» no existe y la regla «el robot solo se mueve con el taladro callado» queda ciega. Además, taladros de otros equipos y aplausos dan falsos positivos | **Acelerómetro (MPU-6050) pegado al taladro** con cable fino al Arduino: RMS de vibración del motor, umbral con histéresis. El micro solo para la pantalla. 1,5 h |
| 2 | **Dos dueños para el puerto serie y las cámaras** | `lerobot-rollout` abre el `SO101Follower` y sus cámaras; el bucle visual también los necesita. Relanzar el rollout en cada cambio de fase = cargar SmolVLA, abrir cámaras y calentar la GPU (20-40 s [est.]) por intento | **Un solo proceso propio** dueño del puerto y de las cámaras (§2). `lerobot-rollout` queda como plan B solo para N1 |
| 3 | **4 órdenes en una noche** | Viernes 19:30-23:00 con teleoperadores novatos dan 60-100 episodios válidos en total [est.: ~2/min en el mejor caso, menos la primera hora de aprendizaje]. Repartidos en 4 órdenes son 15-25 por orden: SmolVLA ignora la frase con la misma escena (`tecnicas.md` §6) | **Dos órdenes en el VLA** con destinos distintos a la vista: `Clean around the new hole.` (sobre la tabla) y `Clean the chips on the mat.` (en la alfombrilla). `Wait by my side.` → postura programada. Canto → fuera |
| 4 | **El recolector programado no es autónomo** | Cada episodio con la aspiradora encendida se come la viruta: hay que reponerla a mano. Y necesita antes la calibración cámara-robot y el limpiador programado funcionando en el robot real: viernes 22:00 como pronto [est.] | Grabar el recolector **con la aspiradora apagada** (la viruta queda, solo se mueve la tabla entre episodios, 5 s) y **solo el sábado 08:00-10:00**. Si a las 10:00 no va, se borra: los datos del viernes son teleoperados |
| 5 | **La viruta clara cae sobre la tabla clara** | El agujero es ciego (tope a 12 mm en tabla de 18, `hardware.md` §5): la viruta se queda encima de la madera. «Viruta clara sobre lo oscuro» solo pasa en la alfombrilla. Y el contorno de la tabla clara se rompe con maquetas y la mano encima | **Cara superior de la tabla en vinilo negro mate + alfombrilla de corte verde.** Tabla = negro sobre verde; viruta = beige sobre los dos. Pose de la tabla con **2 ArUco pequeños en sus esquinas** (basta uno visible), no con el contorno |
| 6 | **Calibración: el modelo no es el robot** | La IK de `sim/cinematica.py` supone que el 0 de la calibración de LeRobot es el 0 del modelo (`sim/entorno.py` l.4-6). La calibración real la hace una persona moviendo a mano al centro: 2-4° de error por articulación [est.]; 3° en el hombro a 250 mm = 13 mm. Con la boca a 35 mm de la broca, eso es tocarla | **Corrección medida:** 9 puntos de la alfombrilla tocados con la boca (guía), la cámara ve la boca; ajuste afín xy (IK → real). Boca con **patines de fieltro**: z objetivo = superficie − 3 mm, desliza en vez de flotar |
| 7 | **Acompañar a un taladro que se mueve** | Latencia cámara 33 ms + ArUco 10-20 ms + IK + servo 150-250 ms ≈ 0,2-0,3 s [est.]; a 0,3 m/s de la mano son 6-9 cm de retraso. ArUco se pierde con desenfoque (6 mm en 20 ms de exposición [est.]) y con la mano encima | **Acercarse a un taladro quieto**: el robot entra solo si el marcador lleva 0,7 s quieto en la zona, siempre por el lado del robot (la persona está enfrente), a ≤ 5 cm/s; si el marcador se mueve > 1 cm entre fotogramas o se pierde, se para y sube 5 cm. Es N2, no N1 |
| 8 | **Inferencia y paso entre modos** | SmolVLA sin RTC en un bucle propio: cada 50 acciones (1,7 s a 30 Hz, `policies/smolvla/configuration_smolvla.py:29-30`) se para mientras infiere (0,15-0,4 s en la GTX 1660 [est.]). Y si arranca desde donde lo dejó el acompañamiento, ve una postura que no está en los datos | Aceptar la pausa (limpiar es lento) o inferir en un hilo cuando queden 15 acciones (1 h). **Regla: el VLA siempre arranca desde aparcado** (como las demos); fin por quietud 1 s (ya hay `DetectorFin` en `robot/politica.py`) o 20 s |

Menores: `max_relative_target` pasado como entero desde Python da `TypeError` (`robots/utils.py:142`, comprueba
`isinstance(..., float)`): pasar `4.0`. El SO-101 solo limita el par de la pinza (`so_follower.py:154-157`):
escribir `Max_Torque_Limit` más bajo en muñeca y codo para acompañar. Interbloqueo eléctrico: §5.

## 2. Arquitectura recomendada: un proceso dueño de todo

```
 tablet / voz ──HTTP/WebSocket──►  aspira/servidor.py (FastAPI, ya hay patrón en lewelder/servidor.py)
                                         │ cola de órdenes (hilo)
                                         ▼
 ┌──────────────── aspira/robot_vivo.py · UN proceso · bucle a 30 Hz ─────────────────┐
 │ SO101Follower (PUERTO SERIE del brazo) + cámaras top y wrist (las abre el robot)  │
 │ obs = robot.get_observation()  → misma imagen top para la visión y para el VLA    │
 │ visión: pose de la tabla (ArUco), viruta (color), taladro (marcador)              │
 │ estado: APARCADO · ACERCARSE (prog.) · CONGELADO · VLA(frase) · ZIGZAG · APARCAR   │
 │ VLA: PoliticaLeRobot (robot/politica.py) en modo síncrono                          │
 │ programado: IK (sim/cinematica.py) + corrección afín + límite de velocidad         │
 │ seguridad: si taladro vibra → CONGELADO; send_action con max_relative_target=4.0   │
 └────────────────────────────────────────────────────────────────────────────────────┘
                                         ▲ serie (OTRO puerto, sin conflicto)
 aspira/arduino.py ◄── Arduino: acelerómetro del taladro → «taladro on/off»; manda el relé / emisor 433 MHz
```

**Quién tiene el puerto:** solo `robot_vivo.py`, todo el rato. Grabar con `lerobot-record` y entrenar son sesiones
aparte (sin `robot_vivo.py` abierto). El Arduino va por su propio puerto: la aspiradora no compite con el brazo.

**Lo que hace falta, verificado en el código:**
- La inferencia ya está en `robot/politica.py` (`PoliticaLeRobot`), copia exacta de `SyncInferenceEngine.get_action`
  (`src/lerobot/inference/sync.py`): `prepare_observation_for_inference` → preprocesador del checkpoint (lleva la
  normalización con las estadísticas del dataset y el renombrado) → `select_action` (cola de 50) → posprocesador.
  No hay que reescribir normalización.
- **Cambiar en `politica.py`:** el `rename_map` está fijo a `cenital/muneca` (`lewelder/contrato.py:299`); pasarlo
  como parámetro con `top/wrist → camera1/camera2`. Adaptador obs del robot → `observation.state` (vector en el orden
  de los motores, `shoulder_pan.pos`…`gripper.pos`) + `observation.images.top/wrist` en HWC uint8 RGB (lo que
  devuelve `get_observation`, `so_follower.py:163-185`). Mismo fps (30), resolución y fourcc que en la grabación.
- **RTC no:** `RTCInferenceEngine` pide un `InferenceRobot` con hilo propio (`inference/factory.py`,
  `rollout/robot_wrapper.py`); montarlo fuera del rollout no compensa. Síncrono, y si la pausa molesta, hilo propio.
- Al salir: aparcar y luego `disconnect`; `disable_torque_on_disconnect=True` deja caer el brazo
  (`config_so_follower.py:31`). Si el proceso muere sin `disconnect`, los servos mantienen la última posición.
- **Estimación:** `robot_vivo.py` (bucle, estados, órdenes) 3 h + adaptador y prueba con un SmolVLA público y un
  robot simulado (`sim/entorno.py` ya imita la interfaz) 1,5 h = **4,5 h**, × 1,5 de integración [est.].
- **Plan B de N1** (si `robot_vivo.py` no mueve el robot el sábado a las 09:00): `lerobot-rollout --interactive`
  con `/subtask` + `/start` + `/reset` (puente del brief) y `aspira/arduino.py` aparte. N1 no necesita visión propia.

## 3. El VLA: cuántos episodios y en qué orden

| Tanda | Cuándo | Orden | Episodios [est.] | Cómo |
|---|---|---|---|---|
| 1 | Vie 19:30-22:30 | `Clean around the new hole.` | 50-60 | Teleop. Tablas con 10 agujeros ya hechos; **viruta de bote** (guardada de taladrar hoy) sobre uno distinto cada vez; tabla en 5 poses × giro; maquetas en 1 de cada 3 |
| C0 | Vie 23:00 | — | — | SmolVLA en HF Jobs (2-2,5 h, `especialista-tecnico.md` C) + ACT del agujero en la 1660 |
| 2 | Sáb 08:00-10:00 | recolector (si va) o teleop | 30-60 | Agujero y alfombrilla, aspiradora apagada |
| 3 | Sáb 10:00-12:00 | `Clean the chips on the mat.` | 40 | Teleop; viruta en 5 zonas de la alfombrilla, tabla siempre puesta |
| C1 | Sáb 12:15 | fusión | — | SmolVLA multitarea, listo ~15:00; matriz frase × destino a las 15:30 |

No grabar con el taladro girando: el VLA solo actúa con el taladro parado (regla 1 de `gestion-robot.md`).
**Si C1 cruza órdenes (≤ 6/10 en la matriz):** un ACT por orden y el proceso propio carga los dos en memoria
(cambiar de modelo = cambiar de objeto Python, 0 s). Se cuenta así en el pitch, sin decir «una sola red».
**Honestidad de la línea base:** si el recolector ya detecta viruta por color, la línea base programada también
puede hacerlo; comparar el VLA con «solo memoria» es hacer trampa. Línea base declarada = detector de color + IK.

## 4. Percepción: correcciones concretas

- **Viruta a 600 mm:** a 640 px sobre ~700 mm de campo, ~1,1 mm/píxel [est.]; SmolVLA reescala a 512 con relleno
  (`configuration_smolvla.py:45`): ~1,4 mm/píxel. Una viruta suelta de 1-3 mm son 1-2 píxeles; el **montón** de un
  agujero de 8 mm (~0,3 g, anillo de 20-30 mm [est.]) es una mancha de 15-20 píxeles: se ve **solo con contraste**
  (vinilo negro). La cámara de muñeca la ve de cerca en la pasada: es la que guía al VLA. Comprobar hoy con una foto.
- **Punto del agujero sin taladro marcado:** diferencia de imagen antes/después en coordenadas de la tabla (mancha
  beige nueva sobre negro). Sustituye a «punta de la broca en el instante del sonido» y no depende del marcador.
- **Marcador del taladro:** en la tapa trasera (mira hacia arriba al taladrar en vertical), bola o anillo de color
  saturado de 30-40 mm además del ArUco: el color aguanta desenfoque y oclusión parcial; la punta = marcador − L
  sobre la vertical, válido solo con el taladro quieto (5° de inclinación con L = 250 mm = 22 mm de error [aritmética]).
- **ArUco de la alfombrilla tapados:** la cámara es fija; se calibra una vez con los 4 visibles y la alfombrilla
  pegada con cinta. Durante la demo basta uno para vigilar que nada se ha movido.

## 5. Arduino, aspiradora y seguridad eléctrica

- Detección: acelerómetro en el taladro (riesgo 1). Retardo: 50-100 ms de ventana RMS [est.]; arranque de la
  aspiradora 0,5-1 s [est.]: la aspiradora llega tarde a los primeros 0,5 s de viruta, aceptable.
- **No cablear 230 V en un relé suelto en la mesa.** Enchufe comercial: radiocontrolado de 433 MHz con emisor en el
  Arduino (sin wifi) o Shelly Plug con su API local en la wifi propia del equipo. La aspiradora de 850-1000 W está
  dentro de lo que admiten (16 A [est.: mirar la etiqueta]). Interruptor manual de la aspiradora siempre accesible.
- Fallo seguro: si el Arduino deja de mandar latidos 1 s, `robot_vivo.py` pasa a CONGELADO y el enchufe a apagado.

## 6. Tiempo por intento y tarea puntuada

Cronometrado [est.]: taladrar 5-10 s + retirar 2 s + aspira 2 s + aparcado → VLA 15-20 s + aparcar 3 s ≈ **30-40 s**;
viruta en la alfombrilla: echarla 5 s + 15-20 s. Con el juez eligiendo entre 3 órdenes, un fallo de la frase cuesta el
intento: la tarea del concepto v2 apuesta la nota de demo (30 puntos) al riesgo 3.

**Tarea que declararía:** «El juez taladra donde quiera en la tabla (o elige uno de los agujeros con viruta de bote) y
**mueve la tabla a la pose que quiera**; al retirar el taladro, Aspira limpia la viruta del agujero nuevo en < 30 s sin
que nadie lo toque. Éxito = ≥ 80 % menos píxeles beige en un círculo de 4 cm (foto antes/después, sale en pantalla).»
Cinco intentos, cada uno en otro agujero: la escena se repone sola. **La alfombrilla** entra como sexto intento
anunciado («y ahora usted elige la orden») solo si la matriz del sábado da ≥ 8/10 en las dos.

## 7. Carga de trabajo: jueves (hoy), viernes y recorte

| P | Pieza (jueves, 2 personas, ~9 h c/u) | h [est.] | Hecho cuando |
|---|---|---|---|
| 1 | `aspira/robot_vivo.py`: bucle 30 Hz, estados, cola de órdenes, aparcar al salir | 3 | Con `sim/entorno.py` como robot falso pasa APARCADO → VLA → APARCAR |
| 2 | Adaptador obs + `rename_map` parámetro en `politica.py`; prueba con un SmolVLA público en la 1660 | 1,5 | Infiere y mide ms por llamada |
| 3 | Visión: pose de la tabla (2 ArUco), viruta por color y diferencia, en coordenadas de la alfombrilla (`lewelder/seguimiento.py`) | 2,5 | Con webcam, vinilo negro y viruta real da el punto en mm |
| 4 | IK + corrección afín de 9 puntos + trayecto con velocidad limitada + zigzag sobre la mancha, en MuJoCo | 2,5 | En simulación limpia una mancha en cualquier pose de la tabla |
| 5 | Arduino: acelerómetro + emisor/enchufe + latido; `aspira/arduino.py` | 1,5 | Taladro real on/off sin falsos con la aspiradora encendida |
| 6 | `comandos.sh` (calibrar, teleop, grabar, entrenar, rollout plan B) + ensayo de la nube | 2 | Arranca hasta el error de puerto; checkpoint de 200 pasos carga |
| 7 | Pantalla: frase, cámaras, estado, % de viruta (reutiliza `web/`) | 1 | Se ve en la tablet |
| | **Total** | **14** (× 1,3 = 18) | |

**Viernes (con robot):** 18:00-19:00 calibrar, cámaras con la misma configuración que en `robot_vivo.py`, corrección
de 9 puntos; 19:00-19:30 teleop libre; 19:30-22:30 tanda 1; en paralelo, la otra persona prueba `robot_vivo.py`
(aparcar, zigzag programado, congelado por vibración). **Sábado 09:00:** C0 en `robot_vivo.py` o en el plan B.
**Sábado 12:00, N1:** limpiar el agujero nuevo con el VLA + aspiradora por vibración.

**Recortes (por orden):** fuera `Clean along the edge.` y el lijado; fuera `Wait by my side.` del VLA (postura
programada); acompañar = acercarse a un taladro quieto, y solo el sábado tarde si N1 está ≥ 7/10; recolector solo
si va el sábado a las 10:00; grabador de episodios propios (LeRobotDataset desde `robot_vivo.py`, 2 h) el viernes
noche solo si sobra; voz → LLM al final (botones primero); cambio de cabezal y seguir el taco, solo en el pitch.
