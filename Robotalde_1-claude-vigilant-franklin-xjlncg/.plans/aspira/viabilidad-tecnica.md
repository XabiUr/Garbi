# Garbi · viabilidad técnica real de entrenarlo y ejecutarlo (19-11)

Pregunta del usuario: ¿se puede entrenar y ejecutar de verdad en el SO-101, en el hackathon (20-22 nov)?

Fuentes:
- **[M]** medido en nuestra simulación o en esta máquina; reproducible con `herramientas/garbi_viabilidad.py` y con
  los tests.
- **[V]** dato externo verificado, con URL.
- **[E]** estimación.

## Veredicto

| Parte | Viabilidad | Condición |
|---|---|---|
| Núcleo programado: acercarse, apuntar, acompañar, aspirar, limpiar con visión | **Alta** | Las mitigaciones 1-3 de abajo, que son de hardware y de poco código |
| Recoger datos para el VLA | **Alta** | Autodemostraciones: el propio Garbi limpia con la línea base y graba |
| Entrenar | **Media** | ACT en local (1-2 h); SmolVLA solo en GPU de nube (3-6 h), una iteración como mucho |
| Ejecutar el VLA en directo | **Media-baja para SmolVLA**, **alta para ACT** | SmolVLA necesita ≤ 0,8 s por chunk (GPU) o ir a media velocidad |
| Que el VLA limpie bien a la primera | **Incierta** | La comunidad da un 30-60 % de éxito en coger y dejar con 50 episodios; no hay precedentes de aspirar |

**Conclusión:** la demo es viable si el núcleo programado es la base que funciona siempre y el VLA es la parte
visible, supervisada y con respaldo:
- el VLA se encarga de las dos órdenes de limpieza;
- ACT es el respaldo realista;
- la línea base cubre lo demás.

Los tres riesgos que pueden tumbar la demo no son de aprendizaje:
1. el par del hombro con la manguera;
2. la calibración del brazo;
3. la latencia de SmolVLA.

Los tres tienen solución conocida y medida.

## 1. Par de los servos: el riesgo número uno

**Servos:** el seguidor del SO-101 lleva 6 STS3215 de 7,4 V con reductora 1/345 [V]
(https://github.com/TheRobotStudio/SO-ARM100). Según la hoja de datos de Feetech [V]
(https://core-electronics.com.au/attachments/uploads/sts3215-smart-servo-datasheet-translated.pdf):
- **Par de bloqueo:** 19,5 kg·cm a 7,4 V, ≈ 1,9 N·m (16,5 kg·cm a 6 V).
- **Par nominal continuo:** solo **5 kg·cm, ≈ 0,49 N·m**.
- **Protección térmica:** el servo apaga el par a 70 °C.
- **Versión de 12 V** (ST3215, misma carcasa): 30 kg·cm de bloqueo y 10 kg·cm (≈ 0,98 N·m) continuos [V]
  (https://www.dfrobot.com/product-2962.html).

**Fallos documentados:** hay STS3215 rotos por sobrecarga sostenida, que acaban bloqueando el bus [V]
(https://github.com/huggingface/lerobot/issues/2819).

**Par estático del hombro** (`shoulder_lift`, la articulación más cargada; el codo va justo detrás), en las posturas de
trabajo de toda la zona [M]:

| Carga | Acompañar | Preapunto | Limpiar tabla | Limpiar alfombrilla | Aparcado |
|---|---|---|---|---|---|
| Brazo sin herramienta | 0,54 | 0,65 | 0,53 | 0,59 | 0,19 |
| Boquilla + soporte + cámara, 100 g | 0,71 | 0,84 | 0,70 | 0,78 | 0,13 |
| 100 g + manguera tirando 1,5 N | 1,08 | 1,24 | 1,07 | 1,17 | 0,19 |
| 100 g + manguera tirando 3 N | — | 1,65 (máximo) | — | — | — |

En N·m. Las masas del modelo son las del SO-101 de la simulación; la manguera tira en vertical en la unión con la
boquilla.

**Lectura:**
- **Sin herramienta,** el brazo ya pasa del par continuo nominal en estas posturas. Se sostienen porque son ratos
  cortos, como en cualquier teleoperación.
- **Con la boquilla (100 g),** el hombro trabaja al 45 % del bloqueo, 1,7 veces el nominal. Es tolerable en ciclos de
  ~20 s si descansa aparcado (0,13-0,19 N·m).
- **Con la manguera colgando,** el par llega al 65-85 % del bloqueo: calentamiento, protección a 70 °C y riesgo de
  romper el servo.

**Mitigaciones (obligatorias):**
1. **La manguera no puede colgar del robot.** Hay que suspenderla desde arriba con un brazo o pértiga y una goma o un
   muelle, de modo que en la boquilla solo llegue un tramo corto y flojo. Objetivo: menos de 0,5 N en la boquilla. Se
   mide con un dinamómetro o una báscula de cocina.
2. **Boquilla ≤ 100 g en total** (tubo de PLA de pared fina, soporte y una cámara pequeña sin carcasa). Hay que pesarla.
3. **Descanso aparcado** entre ciclos: el aparcado alto ya está en la simulación.
4. **Vigilar temperatura y carga** de los servos (los STS3215 dan temperatura, carga y corriente, que `rustypot` lee) y
   aparcar solo a 60 °C. Es poco código en el orquestador.
5. **Si se puede, hombro y codo con la versión de 12 V** (C018/C047, misma carcasa): el caso con boquilla queda por
   debajo de su nominal. Ojo: no se pueden mezclar 7,4 V y 12 V en la misma alimentación sin separar el bus.

**Puerta G1, viernes:** con la boquilla y la manguera montadas, sostener la postura de preapunto 60 s; la temperatura
debe quedar por debajo de 55 °C y sin errores de sobrecarga. Si falla, reducir la zona hacia el robot (menos brazo
de palanca) o cambiar los servos.

## 2. Calibración del brazo: el apunto tiene que ser en lazo cerrado

**Datos externos:**
- Holgura real del STS3215: ~1° (1,8-2,6° bajo carga) [V] (https://github.com/TheRobotStudio/SO-ARM100/issues/134).
- Repetibilidad del brazo: ±2-4 mm [V-débil].
- Error conocido de 4096 cuentas tras calibrar, que se arregla apagando y encendiendo el servo [V]
  (https://github.com/huggingface/lerobot/issues/5324).

Monte Carlo con un error de calibración aleatorio σ por articulación (150 casos por σ) [M]:

| σ por articulación | Boca sin apunto (absoluto) | Tras el apunto actual (rayo + cinemática) | **Apunto en lazo cerrado (3 iteraciones)** | Altura del borde al limpiar (p5…p95) |
|---|---|---|---|---|
| 0,5° | 2,9 (p95 6,3) mm | 2,2 (6,2) mm | **1,4 (2,8) mm** | −2,9 … +3,1 mm |
| 1° | 5,6 (12,3) mm | 4,9 (13,5) mm | **1,5 (2,6) mm** | −4,8 … +6,3 mm |
| 2° | 11,1 (23,3) mm | 8,6 (28,5) mm | **1,6 (2,7) mm** | −11,1 … +12,2 mm |
| 3° | 18,0 (37,6) mm | 15,0 (40,9) mm | **1,6 (2,9) mm** | −14,3 … +21,9 mm |

(Mediana y, entre paréntesis, p95.)

**Lectura:**
- **El apunto actual no compensa la calibración.** Proyecta el píxel con la cinemática, que es justo lo que está mal.
- **Con 1° de error, la boca puede acabar a 13 mm de su sitio.** El margen entre el borde de la boca y la broca es de
  ~13 mm, así que podría tocarla.
- **El apunto en lazo cerrado lo deja en ~1,5 mm con cualquier calibración.** Funciona así: la cámara va rígida con la
  boquilla, mide la broca *respecto a la boca*, corrige y vuelve a medir.
- **La altura al limpiar no tiene realimentación.** Con 1°, el borde varía ±5-6 mm, y la tolerancia de la aspiración
  es de −3 (tocando) a +6 mm (apartado 3).

**Mitigaciones:**
1. **Apunto relativo en lazo cerrado** (por implementar, ~2 h):
   - La cámara del robot ve un ArUco de la tabla (18 mm, grande a esa distancia) y `solvePnP` da el plano de la
     tabla *respecto a la cámara*.
   - Con eso, la punta queda en coordenadas de la cámara, y la boca está en coordenadas de la cámara por diseño
     (CAD del soporte): el vector boca→punta no depende de la cinemática.
   - Se corrige 2-3 veces.
   - Si no ve ningún ArUco, se usa el apunto actual.
2. **Falda de cepillo o fieltro en el borde de la boca:** puede tocar la superficie, y la altura nominal baja a
   «rozando». Absorbe ±10 mm sin perder succión. Es lo mismo que llevan los cepillos de aspiradora.
3. **Calibrar bien:**
   - `lerobot-calibrate` y apagar y encender los servos después (problema de las 4096 cuentas);
   - comprobar el error con la cámara de arriba llevando la boca a 3-4 marcas conocidas de la alfombrilla.
4. **Base del robot fija a la alfombrilla** con una plantilla impresa: la cámara de arriba trabaja en el marco de la
   alfombrilla y el robot en el suyo.

## 3. Tolerancia de la limpieza (lo que exige a la teleoperación y a la política)

Viruta recogida por la línea base con errores puestos a propósito (2 órdenes × 6 semillas) [M]:

| Caso | Recogida media | Peor caso |
|---|---|---|
| Nominal (borde a 3 mm, 30°) | 100 % | 100 % |
| Altura +6 mm | 98 % | 90 % |
| Altura +12 mm | 74 % | 43 % |
| Altura +20 mm | 36 % | 0 % |
| Inclinación 40° | 100 % | 100 % |
| Inclinación 20° | 87 % | 0 % |
| Barrido desplazado 8 mm | 99,7 % | 97 % |
| Barrido desplazado 15 mm | 98,6 % | 83 % |

**Lectura:**
- Lo crítico es **no ir alto** (más de 6 mm sobre lo nominal) y **no ir más tumbado de 30°**. Más inclinado (40°) no
  pasa nada.
- La posición tolera ±10-15 mm, así que localizar la viruta no exige precisión fina: es una tarea adecuada para un
  VLA.
- **Ojo:** el cono de captación es un modelo, no una medida. Hay que medirlo con la aspiradora del usuario
  (**puerta G2, viernes**): boquilla a 30° y serrín a 10, 20, 30, 40 y 50 mm por delante y a los lados; se apunta qué
  recoge. Si el alcance real es menor, se baja la boca o se acerca el barrido.

## 4. Datos: autodemostraciones en vez de teleoperación

**Teleoperar el barrido es difícil:**
- con el brazo guía hay que mantener la boquilla a 30° y a 3 mm de la superficie mientras se barre;
- la tolerancia (apartado 3) es estrecha en altura;
- el guía no lleva boquilla.

**Propuesta: el propio Garbi genera las demostraciones.**
- El ciclo real con la línea base programada (visión de arriba + zigzag, apunto en lazo cerrado y falda de cepillo)
  limpia y graba cada limpieza como un episodio de `LeRobotDataset`, con las dos cámaras, el estado, la acción y la
  frase.
- El filtro «aprende del mejor» se queda solo con los episodios que dejan la zona limpia.
- Es el mismo flujo que `garbi/demostraciones.py`, con el robot real.
- Las personas solo preparan la escena: taladrar, tirar serrín y mover la tabla.
- La teleoperación queda para 10-20 episodios de casos que la línea base hace mal, como viruta muy esparcida o
  pegada al canto.

**Tiempo estimado [E]:**

| Orden | Episodios | Por episodio | Total |
|---|---|---|---|
| Limpiar agujero | 50 | ~45 s (taladrar, acompañar, limpiar ~5 s, aparcar) | ~40 min, con 4-5 tablas de 12 agujeros |
| Limpiar alfombrilla | 50 | ~20 s (tirar serrín, limpiar, aparcar) | ~17 min |
| **Total** | 100 | | **~1 h**, más el serrín guardado de taladrar |

**Precedentes de la comunidad [V]** (detalle en el informe del agente):
- con 20 episodios SmolVLA no funcionó;
- con 50 episodios, SmolVLA logró un 30 % y ACT un 40 %;
- ACT llegó al 90 % tras iterar con 25 episodios por zona;
- con ~100 episodios SmolVLA colapsó a acciones constantes (issue
  https://github.com/huggingface/lerobot/issues/5082).

Regla: unos 10 episodios por zona de trabajo. Con 50 por orden hay 5 zonas de tabla y 5 de alfombrilla: cuadra.

**Ventaja clave de los datos reales:** la política aprende en el espacio articular del propio robot, con sus errores
de calibración incluidos. Lo que aprende ya los lleva compensados, igual que el apunto en lazo cerrado. Los datos
simulados (`datos/garbi_sim`) sirven solo para ensayar el flujo.

## 5. Entrenamiento

| Política | Dónde | Tiempo | Fuente |
|---|---|---|---|
| ACT, 50 ep., 5 épocas, batch 8 | RTX 3090/4090 | 30-60 min | Guía de hardware de LeRobot [V] |
| ACT | L4/A10G | 1-2 h | ídem [V] |
| ACT | GTX 1660 (6 GB) | ~2-4 h para ~10k pasos | [E]: cabe en 2-6 GB, sin medir |
| SmolVLA, 20k pasos | A100 | ~4 h (receta) / 1-2 h (5 épocas, batch 16) | [V] |
| SmolVLA | L4/A10G | 3-6 h | [V] |
| SmolVLA | GTX 1660 o T4 | no viable (10-16 GB) | [V] |

Fuente de la guía: https://huggingface.co/docs/lerobot/en/hardware_guide.

- Nuestras imágenes son de 256×192, más pequeñas que las de la guía (640×480): los tiempos reales serán algo menores.
- **Comprobado aquí [M]:** el dataset de Garbi carga en SmolVLA y en ACT, y los dos entrenan (2 s/paso y 1,7 s/paso en
  CPU).
- **Plan:** el sábado a mediodía, ACT (uno por orden, o uno con las dos, que se distinguen por la postura inicial) en
  local, y SmolVLA en la nube (L4/A100 en HF Jobs, que necesita créditos) con 10-20k pasos. Solo cabe **una iteración**
  de SmolVLA.

## 6. Ejecución en directo: latencia

Latencia medida por chunk en CPU (4 núcleos) con los checkpoints de 1 paso [M]:

| Política | Chunk | Por chunk | Duración del chunk a 30 Hz |
|---|---|---|---|
| ACT | 100 acciones | ~70 ms | 3,3 s |
| SmolVLA | 50 acciones | ~1,2 s | 1,67 s |

Datos externos para comparar [V] (https://github.com/huggingface/lerobot/issues/4633):
- SmolVLA tarda 190-200 ms por chunk en una RTX 4090 en modo *eager*, y 40-49 ms compilado, con 22-65 s de compilado.
- En la GTX 1660 no hay medidas; se estiman 0,3-1 s [E].

**Ejecución asíncrona** (implementada en `garbi/politica.py`, `HabilidadVLA(asincrona=True)`): calcula el siguiente
chunk mientras se ejecuta el actual.

Límite medido con tests: con un solo cálculo en marcha, cada chunk nuevo aporta (n − latencia) acciones útiles, así que
**solo es fluida si la latencia ≤ la mitad de lo que dura el chunk: 0,83 s** a 30 Hz [M].

| Caso | Resultado [M] |
|---|---|
| Latencia 0,7 s | Solo espera al primer chunk; limpia igual |
| Latencia 1,2 s (SmolVLA en CPU) | El robot espera más del 40 % del tiempo |
| 1,2 s con `factor_tiempo=2` (cada acción dura 2 fotogramas, movimiento a mitad de velocidad) | Fluido; límite 1,67 s |

**Lectura:**
- **ACT va bien hasta en CPU.**
- **SmolVLA necesita:** la GTX 1660 a ≤ 0,8 s por chunk (**puerta G5, viernes: medirla**, con el compilado hecho
  antes), o ir a mitad de velocidad, o un servidor de inferencia en la nube con async (LeRobot 0.7 tiene
  `lerobot-policy-server`), con riesgo de wifi.

## 7. Integración con el robot real: lo que falta

| Pieza | Estado | Esfuerzo [E] |
|---|---|---|
| Orquestador, estados, órdenes, seguridad | Hecho y probado en simulación | — |
| Visión de arriba (ArUco, tabla, bola, viruta) | Hecha; umbrales de simulación | 1 h ajustando con la webcam real |
| Apunto con la cámara del robot | Hecho (rayo + cinemática) | — |
| **Apunto relativo en lazo cerrado** (PnP con ArUco de la tabla) | Simulado con Monte Carlo, sin implementar | ~2 h |
| **Adaptador real** (`MundoReal`: SO101Follower de LeRobot, 2 webcams, pose de la cámara por cinemática + CAD, bucle de 30 Hz) | Sin hacer | ~3 h |
| **Arduino real** (serie + enchufe de 433 MHz o Shelly, firmware con latido) | Protocolo hecho y virtual; sin firmware | ~2 h |
| **Vigilancia de temperatura y carga** | Sin hacer | ~1 h |
| Grabador de autodemostraciones en el robot real | Reutiliza `demostraciones.py` con `MundoReal` | ~1 h |
| VLA asíncrono | Hecho y probado | — |
| Soporte de la boquilla (110 mm, cámara al costado, falda) y pértiga de la manguera | Sin diseñar | CAD ~2 h + impresión ~3 h: **hoy** |

## 8. Plan con puertas de decisión

**Hoy (jueves):**
- imprimir el soporte de la boquilla;
- preparar la pértiga de la manguera;
- implementar el adaptador real, el apunto relativo y la vigilancia de temperatura.

**Viernes por la tarde** (primeras horas del evento):

| Puerta | Comprobación | Si falla |
|---|---|---|
| G1 · par | Preapunto 60 s con boquilla y manguera: < 55 °C, sin sobrecarga | Zona más cerca, manguera mejor suspendida, servos de 12 V |
| G2 · succión | Medir el cono de captación real a 30° | Bajar la boca o barrer más denso |
| G3 · visión | Detectar los ArUco y la bola con la webcam real y la luz del sitio | Marcadores más grandes, 1280×720, luz propia |
| G4 · ciclo programado | 5/5 ciclos (acercarse, apuntar, acompañar, limpiar) sin tocar el taladro | Es la demo mínima: no se sigue sin esto |
| G5 · latencia | SmolVLA en la GTX 1660, en ms por chunk | ≤ 0,8 s: normal; ≤ 1,6 s: media velocidad; peor: servidor o solo ACT |

**Sábado:**

| Hora | Paso |
|---|---|
| 9-11 h | Autodemostraciones (100 episodios) |
| 11 h | ACT en local y SmolVLA en la nube |
| 17 h | Evaluación: 10 intentos por orden, en posiciones nuevas, con la supervisión |

Qué se enseña según la evaluación:
- **≥ 8/10:** VLA en directo.
- **5-7/10:** VLA en la orden que mejor funcione.
- **< 5/10:** línea base en directo y el VLA declarado en vídeo.

**Domingo:** ensayo del guion y respaldo de cada paso.

## Lo que no se ha podido medir aquí

- **La succión real:** el cono es un modelo; G2.
- **El par real:** las masas del modelo pueden diferir; G1.
- **La latencia en la GTX 1660:** G5.
- **La tasa de éxito real del VLA:** no hay precedentes de aspirar con SO-101; solo se sabe tras el sábado.
- **La luz y las sombras del sitio** para la visión por color: G3.

Reproducir:

```bash
python herramientas/garbi_viabilidad.py par
python herramientas/garbi_viabilidad.py calibracion
python herramientas/garbi_viabilidad.py tolerancia
pytest tests/test_garbi_vla.py
```
