# Garbi · plan de construcción (fase 4, 19-11)

Sale de [especificacion-tecnica.md](especificacion-tecnica.md). Los contratos entre módulos están en
`garbi/tipos.py`: `Escena`, `Orden`, `Cuerpo` y `Habilidad`.

Cada tarea va en su rama y su worktree, con tests propios en simulación (MuJoCo, sin robot real).

| T | Tarea | Archivos | Depende de | Hecho cuando |
|---|---|---|---|---|
| 1 | **Percepción sin ArUco** (M2 y M3): tapete → cámara, madera, marcador, broca por su ancho, viruta, calibración del robot con el anillo verde | `garbi/percepcion.py`, `garbi/calibracion.py`; la escena pierde los ArUco y gana el anillo verde | `tipos.py` | Errores dentro de la especificación en la simulación, con tests |
| 2 | **Ciclo** (M4): máquina de estados de 7 estados, guardias, señal de la aspiradora, revisión y pasada final | `garbi/ciclo.py` | `tipos.py`, `lateral.py` | 5 ciclos seguidos en la simulación, sin contacto y con todos los agujeros limpios (con la verdad de la simulación como `Escena`) |
| 3 | **Paso 7: ACT** (M5): barrido en espiral programado, posición de partida con ruido, grabador de LeRobotDataset (`top` y `wrist` a 640×480), filtro, entrenamiento en HF Jobs y `HabilidadACT` | `garbi/habilidad.py`, `herramientas/garbi_grabar.py`, `herramientas/garbi_entrenar.sh` | `tipos.py` | Dataset grabado en la simulación que carga LeRobot 0.7; ACT entrenado unos pasos en CPU que se ejecuta como `Habilidad` |
| 4 | **Robot real** (M1 y M6): `CuerpoReal` con `SO101Follower`, cámaras OpenCV con exposición fija y la señal `1`/`0` por serie cada 200 ms; programa principal `python -m garbi.correr --sim/--real` | `garbi/real.py`, `garbi/correr.py` | `tipos.py` | Tests con dobles (sin hardware); `--sim` funciona de punta a punta cuando T1-T3 estén |
| 5 | **Maqueta** con 5 ciclos y la pasada final | `garbi/maqueta.py` | — | Se ve en el visor (Enter) |
| 6 | **Integración** | `garbi/correr.py` | 1-4 | 5 ciclos en la simulación con percepción real (imágenes renderizadas) y la habilidad programada |

**Orden:** las tareas 1 a 5 en paralelo; la 6, al terminar.

**Cosas que quedan fuera:** voz, app, sonidos y respetar la mano. Son extras del pitch, solo si sobra tiempo.

## Estado de la tarea 6 · integración (20-11)

**Hecha en la simulación**, rama `t6-integracion`. `python -m garbi.correr --sim` (sin `--verdad`): imágenes
renderizadas a 640 × 480 → `Percepcion` (cámara de arriba calibrada con el tapete; base del robot con el anillo verde,
error de comprobación ≤ 1,2 mm; cinemática para la muñeca) → `Ciclo` → `CuerpoSim`, con `HabilidadEspiral` y el juez
simulado (`JuezSim`, que mide con la verdad de la simulación).

**Resultado (5 ciclos en 5 sitios + pasada final, semilla 0):**

| Medida | Valor |
|---|---|
| Aciertos (agujero limpio con la verdad y sin contacto) | **5/5** (y 6/6 ciclos del registro, contando la pasada final) |
| Viruta restante (partículas a < 35 mm) | 0 en los 5 |
| Holgura mínima real con el taladro | 4,6 mm (la guardia de 10 mm va sobre la punta percibida; la percepción yerra unos mm al acompañar) |
| Borde mínimo de la boca | 3,2 mm |
| Duración por ciclo | 25,9-28,3 s (pasada final 32,9 s) |
| Fallos de percepción | 0 apoyos sin ver, 1 apoyo falso (broca a > 8 mm leída como apoyada) |
| Inclinaciones de partida | 60, 60, 55, 45, 55° (lejos del robot se baja hasta 45° y se registra en `Ciclo.inclinaciones_partida`) |

**Zona donde funciona el ciclo completo con la percepción** (rejilla de la madera, centro x = 360, 200 × 300):
15/15 aciertos en x local −40…+40 (a 320-420 mm del eje del robot) e y −130…+130, sin contactos, borde ≥ 4,1 mm,
holgura real 0,9-19 mm. En x local −80 (a 280-310 mm) solo funcionan las esquinas (y = ±130): en el centro el taladro
de la persona entra por donde está el brazo (contactos). Más allá de 433 mm del eje (x local +80) no hay partida.

**Arreglos de la integración:** `limitar_velocidad` sigue el camino (no recorta esquinas: el borde bajaba a −4 mm a
r ≈ 376-379 mm); partida a 60° cerca y hasta 45° lejos; «limpio» con la fracción de viruta de la percepción (< 2 %) y
no con 2 partículas; percepción: coherencia muñeca-arriba (también con el taladro vertical), altura de la broca por el
radio de la bola, viruta en los agujeros del ciclo; ciclo: mira la broca suponiéndola apoyada si la altura vista desde
arriba es baja (< 30 mm) y, al levantarse el taladro, se aparta subiendo en diagonal; `conftest.py` respeta
`MUJOCO_GL`. Tests: `tests/test_garbi_integracion.py` (lento, 2 ciclos con percepción real) y la espiral con borde
≥ 3 mm en toda la zona alcanzable.

**Problemas abiertos** (los tres primeros, resueltos en «Robustez del ciclo», abajo):
- Holgura real < 10 mm en algunos sitios (mín. 0,9 mm en (400, −65)): la guardia se aplica sobre la punta percibida.
  Añadir el error de la percepción al margen o acompañar a algo más de 30 mm.
- Cerca del robot (r < 300 mm) el brazo no se aparta cuando el taladro viene hacia él.
- Con la broca vista de lado (p. ej. en (310, 90), primer agujero, sin apoyo previo) la muñeca mide el eje torcido y la
  postura de mirar pasa a < 10 mm del taladro: el ciclo no llega a acompañar (en ese sitio pasa como 5.º agujero, cuando
  la altura por la bola ya se ha corregido con apoyos anteriores).
- La altura de la broca por el radio de la bola tiene un sesgo que depende de la posición (−10…+25 mm en la
  simulación); se corrige en cada apoyo.

## Robustez del ciclo (20-11)

Rama `robustez-ciclo` (sobre `t6-integracion`). Ciclo completo con percepción real (imágenes renderizadas a 640 × 480)
y una persona simulada con ruido realista: `garbi/robustez.py` (`JuezRobusto`) y
`herramientas/garbi_robustez_ciclo.py` (tabla); pruebas lentas en `tests/test_garbi_robustez.py`. En cada ciclo, con
su semilla: madera en su zona y girada ±8°, sitio al azar de la **zona de taladro** (`tipos.ZONA_TALADRO`, 320-420 mm
del eje del robot, a ≥ 40 mm del canto), taladro inclinado 0-8° con rumbo cualquiera, velocidad de entrada ×0,6-1,6,
broca quieta en el aire a 10-40 mm 2,5 s antes de apoyar (prueba «en el aire») y temblor de la mano de ±1-2 mm (3 y
5 Hz) mientras está apoyada. El juez mide la holgura con el taladro inclinado de verdad.

**Resultados (M8, simulación):**

| Prueba | Criterio | Resultado |
|---|---|---|
| 20 ciclos completos (1 agujero por sesión, el primero: sin apoyos previos) | ≥ 19/20, holgura real ≥ 10 mm, borde ≥ 3 mm | **20/20** aciertos, holgura real mín **12,4 mm**, borde mín **5,3 mm**, sin contactos |
| 20 apoyos | ≥ 18/20 detectados | **20/20** |
| 20 «en el aire» (10-40 mm) | sin apoyos falsos | **0/20** con apoyo falso (1 lectura «apoyada» con la broca a 9 mm al *levantarla*, ver abajo) |
| 5 seguidos + pasada final (con ruido, sin fase en el aire) | 5/5 y ≤ 3 min | **5/5**, 24,5-28,6 s por ciclo + pasada final 32,8 s = **164,4 s**; holgura mín 13,5 mm, borde mín 5,4 mm, sin contactos en la pasada |
| Integración (2 ciclos sin ruido) y primer agujero en (310, 90) | holgura real ≥ 10 mm (vuelve a ser el criterio del test), agujero a < 3 mm | 4/4 tests lentos de `test_garbi_integracion.py` |
| Antes de los arreglos (mismas 8 primeras semillas) | — | 4/8, holgura real mín −14,8 mm |

Duración por ciclo 27-32 s con la fase en el aire (24-29 s sin ella). En la simulación (osmesa, 4 núcleos) cada ciclo tarda 3-8 min de reloj; los 20, ~25 min
con 4 procesos.

**Causas encontradas y arreglos:**
- *Taladro inclinado.* La bola está 337 mm · sen(inclinación) al lado de la vertical de la punta (47 mm con 8°): la
  punta estimada desde arriba y la holgura (calculada con el taladro vertical) estaban 20-47 mm mal (holgura real
  negativa). Percepción: el **desfase** punta − bola se aprende de cada medida buena de la muñeca y da la punta desde
  arriba y el eje de la broca (`Broca.eje`); se olvida al salir el taladro; por debajo de 10 mm (~1,7°) se toma por
  vertical; la muñeca no se usa a más de 200 mm (a 220-280 mm daba 10-15 mm de error, que parecían inclinación).
  `ControlLateral.holgura(q4, P, eje)` acepta el eje. Ciclo: mientras no se sabe el eje, la holgura es la peor con el
  taladro inclinado 8° hacia 8 rumbos alrededor de la bola; se sigue a 100 mm (no 80) y la zona se mira con 47 mm de
  tolerancia.
- *Margen de la percepción.* La guardia suma a los 10 mm el error de la percepción (`MARGEN_PERCEPCION`, 5 mm).
- *Brazo que no se aparta.* Huida (`Ciclo._huir`): si la holgura con la orden o con la postura real baja de la guardia,
  el paso que más la aumenta (contando la duda de la punta si solo se ve desde arriba), o frenar donde está el brazo.
  Cerca del taladro, media velocidad (el brazo real se retrasa en el giro de la base 3-4° y su camino se aparta del de
  las órdenes). Al levantar la broca, se aparta del punto donde estaba apoyada y primero solo se aleja (sin subir ni
  picar: el tubo de la boca se encontraba con el portabrocas).
- *Zona de taladro.* Constante en `tipos.py`; solo se acompaña con la punta quieta dentro (±5 mm); se sigue a distancia
  hasta 30 mm fuera; con la punta a < 300 mm del eje se aparca (aparcado, la holgura es ≥ 50 mm aun con la punta a 150
  mm) y, al irse el taladro, se limpia lo pendiente desde el aparcado. Test `test_fuera_de_la_zona_de_taladro_no_acompana`.
- *Primer agujero con la broca vista de lado ((310, 90)).* La postura de mirar se elige con la holgura de la punta y de
  la punta ±15 mm (y, sin eje, con el taladro inclinado): sale a 150-180 mm y, al medir la muñeca, se recalcula a 120.
  De seguir a mirar, la recta en articulaciones cruzaba por delante del taladro: se pasa por la postura de mirar desde
  220 mm, y si la guardia frena el paso recto, se da un paso de lado (una o dos articulaciones) que sí la cumpla. De
  mirar a acompañar, primero atrás a su altura y después baja (la boca se quedaba a 114 mm encima, junto al
  portabrocas). Test `test_primer_agujero_con_la_broca_vista_de_lado`.
- *Temblor de la mano.* El taladro apoyado nunca se veía quieto (la recta de 0,3 s daba 5-10 mm/s): también quieto si
  todas las posiciones de la ventana están a < 3,5 mm de la mediana. En PREAPUNTO, «se ha movido» solo si se apartan la
  punta y el marcador (la punta estimada salta al cambiar su altura estimada; el marcador, al bajar la broca).
- *Brazo estirado.* El brazo real cae unos mm bajo la orden: la guardia del borde lo descuenta y ACOMPANAR trabaja esos
  mm más alto; además acompaña 2 mm más alta (`ALTURA_TRABAJO` 22 mm, borde de la orden ~7,5 mm): el borde
  real bajaba a 0,5-2 mm.
- *Fallo de la percepción.* `cv2.remap` con un perfil vacío (barra de la broca de < 2 px de ancho) tiraba la
  sesión.
- *Agujero apuntado.* Mediana de las puntas medidas por la muñeca en el último segundo antes de apoyar y el primero
  apoyada (con la primera lectura, desde lejos, iba a 3-6 mm).

**Problemas abiertos:**
- Mientras no se sabe el eje (antes de que la muñeca vea la broca) la holgura supone hasta 8° de inclinación: con más,
  no está cubierta. En el robot real conviene medir la inclinación también desde arriba (silueta del taladro).
- Una lectura «apoyada» con la broca a 9 mm al levantarla (un paso de retraso de la salida por el marcador, 6 mm) en
  algunas pasadas.
- Lento de probar: ~5 min de reloj por ciclo en osmesa.
- Los números son de la simulación (cámaras renderizadas, ruido de la persona simulado); falta repetirlos en el robot.

## Solución final (20-11)

Rama `final-ciclo`. Decisiones en [solucion-final.md](solucion-final.md). El programa principal (`python -m
garbi.correr --sim/--real`) usa el ciclo final (`--ciclo viejo` para el de M4).

| Pieza | Archivo | Qué hace |
|---|---|---|
| Ciclo final | `garbi/ciclo_final.py` (`CicloFinal`, hereda las guardias de `garbi.ciclo.Ciclo`) | DESCANSO, DESPIERTO, PRUDENTE, ACERCAMIENTO, RETIRADA, LIMPIEZA como la tabla. Solo mano + taladro (`Taladro.agarrado`) lleva a PRUDENTE; manos en el tapete despiertan; descanso tras 3 s sin manos ni tareas; agujero = clavada ≥ 2 s en el mismo sitio (`verificar_agujero`: gancho para la comprobación visual); LIMPIEZA fija (partida a 45-60° + espiral) en el marco de la madera; aspiradora en ACERCAMIENTO y LIMPIEZA. Guardias de siempre (velocidad, borde, holgura con huida) y nuevas con las manos libres (≥ 15 mm, huida; a < 40 mm el acercamiento se aparta a la prudente y vuelve) |
| Clavada / levantada | `garbi/acercamiento.py` (`DetectorClavada`) | Con la percepción final manda `Broca.clavada_desde`/`evento`; con la verdad, `apoyada` 0,3 s (levantada: 0,2 s o > 8 mm). La usan el ciclo (empieza y acaba el ACERCAMIENTO: ACT no decide el final) y el grabador |
| Acercamiento programado | `garbi/acercamiento.py` (`HabilidadAcercamientoProgramado`) | Respaldo y generador de demostraciones: de la prudente (100 mm, 45 mm, 25°) a aspirar (30 mm, centro a 26 mm, 15°): planta → inclinación → bajar → entrar, frenando al llegar (20 % de lo que falta) y ≤ 45 °/s en proporción. Sigue la broca si se desliza |
| ACT | `garbi/habilidad.py` (`HabilidadACT(..., tarea=TAREA_ACERCAMIENTO)`) | Entradas top, wrist y state (= la orden anterior, el mismo convenio que al grabar). Salto > 15° o frenada 10 pasos → respaldo; si el respaldo tampoco, RETIRADA y no se acerca hasta que se levante |
| Juez de la sesión | `garbi/sesion.py` (`JuezSesion`, `intentos_estandar`, `intentos_grabacion`) | Manos entran → coge → apunta → clava → taladra 4-6 s → levanta → (re-clava / apoyo < 2 s / broca deslizada / mano que se cruza) → sale → (mueve la madera) → manos fuera. Variantes taladro dejado sin mano y mano sola |
| Grabación | `garbi/grabador.py` (`CorteAcercamiento`, `GrabadorAcercamiento`), `herramientas/garbi_grabar_acercamiento.py --sim` | Episodios de la clavada a la levantada (corte automático), tarea «Approach the drill bit.», descarta cortos y con contacto. `CorteAcercamiento.evento(t, escena, grabando)` es la interfaz de `herramientas/garbi_teleop_grabar.py` (robot real) |
| Entrenamiento | `herramientas/garbi_entrenar.sh` (`QUE=acercamiento` por defecto) | `hf` (a10g-small, 30k pasos, checkpoints cada 10k), `cpu`, `humo` y `evaluar` (cada checkpoint en la sesión simulada) |
| Tests | `tests/test_garbi_ciclo_final.py` (17) | Sesión entera, estados y aspiradora, apoyo corto, madera movida, mano que se cruza, mano sola, taladro sin mano, agujero ≥ 2 s, ACT que se pasa (guardia + respaldo), salto, respaldo que tampoco puede, detector y corte |

**Resultados (simulación, verdad de la simulación, `python -m garbi.correr --sim --verdad`, 26 s de reloj):**

| Métrica | Criterio | Resultado |
|---|---|---|
| Intentos de la tarea (5: normal, re-clavada, apoyo corto + madera movida, mano que se cruza, broca deslizada + madera movida) | agujero limpio, sin contacto | **5/5** |
| Variantes taladro dejado sin mano / mano sola | no sigue | **2/2** (0 pasos siguiendo un taladro sin mano; la mano sola solo despierta) |
| Holgura mínima con el taladro (postura real) | ≥ 10 mm | **15,5 mm** |
| Holgura mínima con la mano libre | ≥ 10 mm | **25,6 mm** (2 apartadas por la mano que se cruza) |
| Borde mínimo de la boca | ≥ 3 mm | **9,4 mm** |
| Agujeros falsos / perdidos | 0 | **0 / 0** (6 agujeros; el apoyo de 1,1 s no cuenta) |
| Duración por intento (manos entran → descansa) | — | 26-39 s (13 y 10 s las variantes); de la clavada a aspirar 3,4-4,3 s |

Grabación en la simulación (`garbi_grabar_acercamiento.py --sim --intentos 4`, render 320×240, dataset 160×120): 5/5
acercamientos guardados (141-231 fotogramas), holgura mín 19,8 mm, borde mín 9,3 mm. Humo de ACT (20 pasos en CPU
con ese dataset): `HabilidadACT` carga (tarea «Approach the drill bit.», imágenes 160×120) y da acciones dentro del
ciclo; sin entrenar, la guardia del borde la frena y entra el respaldo (1 respaldo, 19 frenadas), y el intento acaba
en acierto (holgura 14,9 mm, borde 8,3 mm).

**Con la percepción por imágenes** (`python -m garbi.correr --sim --sin-manos-verdad`: percepción final con manos por
color, agarre y clavada de la percepción; ~10 min de reloj): desde la posición prudente la cámara de la muñeca no ve
la punta y solo desde arriba la broca nunca sale apoyada (0/5 sin más). Por eso PRUDENTE, con el taladro quieto
0,3 s y la punta vista solo desde arriba, va a la postura de mirar la broca (la de PREAPUNTO, con sus guardias). Con
eso: **3/5** intentos (las dos variantes bien, 0 agujeros falsos, holgura mín 11,7 mm con el taladro y 12,1 mm con la
mano libre); fallos: la segunda clavada de la re-clavada no se vio (un agujero sin limpiar, 17 partículas) y en el
apoyo corto el brazo bajó a -2,3 mm de borde (contacto) yendo directo a la postura de mirar. Arreglo aplicado: pasar
antes por la postura de mirar desde lejos (`_postura_paso`, como PREAPUNTO); en ese intento ya no hay contacto, pero
la primera clavada tampoco se vio.

### F4 · ciclo final con la percepción a 5/5 (rama `final-robusto`)

Qué cambia:

| Pieza | Cambio |
|---|---|
| Postura prudente (`garbi.acercamiento.postura_prudente`) | **Unifica PRUDENTE y «mirar»**: Garbi sigue al taladro con la cámara de la muñeca mirando la punta de la broca *sobre la madera* desde 180 mm (píxel (150, 120), 10° hacia abajo; IK en caliente, se recalcula si la punta se mueve > 2 mm). Medido en 10 sitios de la zona de taladro: la muñeca ve la punta apoyada, a 8 y a 50 mm (1-2 mm de error, 170-185 mm); holgura 69 mm con el taladro vertical, 35 mm con él inclinado 8° hacia cualquier lado; borde ≥ 56 mm. Desde la postura de antes (boca a 100 mm) la muñeca quedaba a 250-270 mm y la punta apoyada tapada por las mordazas; los junto_a más altos/cerca tampoco la veían (o daban holgura < 10 con el taladro inclinado). Si pasa a < 25 mm de una mano libre apoyada (el brazo queda 140-175 mm a un lado de la broca; en la grabación con la madera al azar pasaba sobre la mano y la guardia lo frenaba a 18° de la prudente), prueba los píxeles (150, 60) y (60, 120) (`UV_PRUDENTE`; ven la punta igual, holgura 99 y 57 mm). Si ninguna cumple las guardias (borde, holgura con la punta en duda ±15 mm, manos), la de entrada (`sin_prudente` cuenta los pasos; 0 en todas las medidas) |
| Acercamiento programado | Desde la prudente la boca está ~140 mm a un lado de la broca: fase 0 «entrada» en recta en articulaciones (60 °/s) a la boca mirando la broca a 45 mm de alto: con el eje medido, ya a 60 mm y 15° (holgura en la recta ≥ 28 mm), sin él a 100 mm (≥ 17 mm con el taladro quizá inclinado; la recta directa a bajar pasaba a 2 mm). Después baja y entra como antes. De la clavada a aspirar: 2,2-3,1 s (antes 3,4-4,3 desde la prudente vieja) |
| Percepción | Clavada aproximada **desde arriba** como respaldo de la muñeca (`Percepcion._apoyo_por_arriba`): la bola baja ≥ 25 mm en 2 s (o estaba apoyada hace < 2 s: deslizada), se para 0,4 s y la altura por su radio queda ≤ 22 mm; no si la muñeca acaba de ver la punta en el aire. La mano que sujeta el taladro se marca (`Mano.del_taladro`): proyectada a la mesa queda a ~270 mm del taladro y el ciclo la tomaba por una mano libre junto a la boca |
| Manos en el acercamiento | Solo se aparta por una mano libre que **se ha movido** (> 15 mm) y está a < 40 mm, o por una mano quieta que frena el camino 3 pasos (se aparta a la de entrada por `_junto` y vuelve). Antes la prudente y la mano apoyada (altura en duda 0-70 mm) daban < 40 mm y se apartaba en cada clavada |
| Postura de partida de ACT | La misma al grabar y al ejecutar: el ACERCAMIENTO empieza siempre en la prudente. `GrabadorAcercamiento(partida=...)` descarta episodios que empiezan a > 8° de ella (sim: `garbi.correr` lo pasa con `diferencia_a_prudente`); teleoperación: tecla **p** (el follower va a la prudente de la broca vista y se queda en ENGANCHE hasta que el leader esté a < 5°) y el episodio solo empieza a ≤ `--tolerancia-partida` (8°) |
| Corte sin agarre | `herramientas/garbi_teleop_grabar.py --sin-agarre` (`CorteAcercamiento(exigir_agarre=False)`); `CorteAcercamiento.aviso` dice por qué no corta con la broca apoyada («no veo una mano en el taladro… --sin-agarre», «fuera de la madera»…), en consola (al cambiar) y en la ventana |
| Deslizamiento | `DetectorClavada`: mientras la broca se desliza (< 0,4 s desde el último cambio y > 5 mm) el ancla va con ella; antes se quedaba a mitad del deslizamiento y en la grabación salía un agujero falso + uno perdido |
| Medida | `herramientas/garbi_medir_sesion.py [--semilla N] [--madera X,Y,G] [--verdad]`: la sesión con la percepción + clavadas vistas/perdidas y su retraso |
| Tests | `tests/test_garbi_ciclo_final.py`: prudente que mira (ve la punta, holgura > 30), acercamiento por la entrada, aviso y `--sin-agarre`, grabador que descarta sin partida prudente, y el lento `test_dos_intentos_con_la_percepcion` (normal + re-clavada con imágenes); `test_garbi_percepcion.py`: clavada desde arriba; `test_garbi_herramientas.py`: enganche y condición de partida, `--sin-agarre` |

**Resultados con la percepción por imágenes** (`python herramientas/garbi_medir_sesion.py --semilla N`, ≡ `python -m
garbi.correr --sim --sin-manos-verdad`; ~15 min de reloj cada una):

| Métrica | Criterio | Antes (F3) | Semillas 0, 1 y 2 | Madera (372, -12, 6°) |
|---|---|---|---|---|
| Intentos de la tarea | 5/5 | 3/5 | **5/5** las tres | **5/5** |
| Variantes (taladro sin mano, mano sola) | 2/2 | 2/2 | **2/2** | **2/2** |
| Holgura mín. con el taladro (postura real) | ≥ 10 mm | 11,0 | 15,5 | 19,5 |
| Holgura mín. con la mano libre | ≥ 10 mm | 43,7 | 35,0 | 35,3 |
| Borde mín. de la boca | ≥ 3 mm | 9,4 | 9,3 | 7,3 |
| Clavadas vistas / del juez (retraso desde que toca la madera) | todas | 5/7 | **7/7** (0,03-0,30 s) | **7/7** (0,03-0,37 s) |
| Agujeros falsos / perdidos | 0 / 0 | 0 / 2 | 0 / 0 | 0 / 0 |
| Contactos | 0 | 0 | 0 | 0 |
| Duración por intento (manos entran → descansa) | — | 25-33 s | 26-39 s (13 y 10 s las variantes) | 26-40 s |
| De la clavada a aspirar | — | no llegaba (`t_acercamiento` vacío) | 2,2-3,1 s; no llega con la mano que se cruza | 2,2-2,8 s (también con la mano que se cruza) |
| Pasos sin postura que mire la broca (`sin_prudente`) | — | — | 6 (0,2 s) | 28 (0,9 s) |

Grabación simulada con la partida comprobada (`garbi_grabar_acercamiento.py --sim --intentos 4`, madera al azar):
5/5 acercamientos guardados, todos a 0-0,4° de la postura prudente al empezar, 4/4 aciertos del juez, holgura mín 19,8
mm, borde 9,1 mm. Antes de los dos últimos arreglos: 1/3 guardados (2 empezaban a 18-19° porque la prudente pasaba
sobre la mano apoyada y la guardia frenaba el brazo) y un agujero falso + uno perdido con la broca deslizada.

Notas honestas: (1) la semilla solo cambia el serrín: las tres sesiones dan lo mismo (por eso la prueba con la madera
en otra pose). (2) En el taladro dejado (variante) la persona baja el taladro con la mano aún en él: el ciclo lo da por
clavado 0,3 s y se retira al soltarlo (no cuenta agujero; la variante es acierto). (3) Con la madera en (360, 0) y la
mano que se cruza, el acercamiento se aparta y no llega a la postura de aspirar antes de levantar (el agujero se
limpia en la LIMPIEZA). (4) La holgura mínima con el taladro (15,5 mm) es en ACERCAMIENTO junto a la broca, no en la
prudente (≥ 35 mm). (5) La prudente ya no es «boca a 100 mm de la broca» de `solucion-final.md`: la boca queda ~92 mm
sobre la madera y 140-175 mm a un lado; la holgura es mayor que antes, pero es un cambio de la decisión acordada. (6)
Todo es simulación: en el robot real falta comprobar que la cámara de la muñeca ve la broca desde la prudente con la
luz y la broca de verdad, el respaldo desde arriba con la bola real (el sesgo de la altura por el radio) y la IK de la
prudente a 30 Hz en el portátil.
