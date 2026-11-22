# Brief · Aprendiz

**Robotalde · Physical AI Hackathon Bilbao II (20-22 de noviembre de 2026, La Perrera)**
Versión 4.5 · 18-11-2026, noche · corregida tras cinco rondas de revisión `santa-method` (registro en [revision-santa.md](revision-santa.md)) (dos revisores independientes
por ronda). **No hay SO-101 hasta el viernes:** todo lo del jueves se hace sin robot.
Documento de entrada para la spec v3 y el plan.

Marcas: **[H]** hecho leído en la fuente · **[H·b]** visto solo en el extracto del buscador · **[est.]** estimación
sin medir en un robot · **[sáb.]** dato que se mide el sábado · **[jue.]** dato o cita que se consigue el jueves ·
**[medir]** medida física pendiente. Ninguna tasa de acierto de este documento está medida: ningún gesto se ha
probado todavía en un SO-101.

---

## 0. Resumen en diez líneas

1. **La idea.** Quien reacondiciona portátiles trabaja con las manos dentro del equipo. Su aprendiz es un SO-101 que
   le deja junto a la mano lo que nombra, sacándolo de un almacén al fondo del banco al que el técnico solo llega
   estirándose por encima del portátil y del brazo. Aprendió mirando al maestro y, cuando falla, el maestro le corrige.
2. **El VLA.** Una sola red (SmolVLA) recibe la frase y dos cámaras; según la frase, coge un objeto u otro, puestos
   donde el jurado quiera.
3. **La demo puntuada.** Cinco intentos independientes de «el jurado coloca los objetos y elige uno; el aprendiz lo
   deja en el plato en menos de 25 s». Al final, el portátil arranca con la memoria nueva.
4. **Anclaje de mercado, por analogía.** Preparar kits y pedidos es una de las tareas que el mercado de physical AI
   ya paga (Ultra con Physical Intelligence, Tutor [H·b]), pero en almacén, no en un banco. **Nadie vende esto en un
   banco: U7 sigue sin resolverse.**
5. **Datos (20 puntos).** 120-140 episodios de «traer» en cuatro tandas, matriz frase × objeto, comparativa ACT
   frente a SmolVLA, caja nunca vista y «cuaderno del aprendiz» con los fallos corregidos.
6. **Planes B a D** con disparadores numéricos: la demo nunca se queda sin historia.
7. **Jueves:** imprimir y montar un tablero propio (~10,7 h de impresión en una impresora clásica), conseguir un
   portátil con trampilla, escribir ~9 h de software y, sobre todo, **hablar con un técnico real y medir el banco
   sin robot**.
8. **Lo débil:** ningún técnico ha escrito que este gesto le ayude; la analogía con kits es de almacén, no de banco;
   el usuario dejó sin respuesta cinco asistentes de banco por falta de anclaje en una aplicación que ya se vende, y
   rechazó cinco maquetas por ser «coger y dejar con una historia».
   La utilidad depende de la cita del jueves y de la medida con y sin robot del sábado; si el robot no mejora nada,
   se dice.
9. **Probabilidad de podio [est. del equipo rojo]:** 15 % (8-25 %); 25-30 % si el sábado se mide ≥ 8/10; por debajo
   del 8 % si se acaba en la rama C.
10. **Decisión que necesito del usuario:** «sí» a este concepto antes de imprimir, o «no» y por qué.

---

## 1. La idea

**Frase de pitch.** «Mientras reparo el portátil, mi aprendiz me trae lo que nombro desde el fondo del banco.
Aprendió mirándome, y cuando falla le corrijo.»

**Lo que se ve en 5 segundos.** Un portátil abierto boca abajo con dos manos dentro; detrás, un brazo que coge una
caja del fondo del banco y la deja en un plato junto a esas manos. Esa imagen está en el cartel, en el vídeo y en la
versión de 90 s; en los 5 intentos puntuados el técnico no repara. Cartel de mesa: **«Lo nombro. Me lo trae.»**

**Nombre.** *Aprendiz*. Lleva dentro el relato de datos (aprende mirando, el maestro corrige) y cualquier persona de
taller entiende la figura. Variante local para el cartel: «Aprendiz · Ikastuna» (el usuario confirma la palabra).

**Diferencia con MSN** (ganador de Robotekin hace un mes, con el mismo operador técnico, Bravo Robots): «MSN
alumbraba donde el soldador señalaba. Aquí no hay luz, ni soldador, ni placa: hay un brazo que coge por su nombre
cosas distintas y un portátil que al final arranca.»

## 2. Usuario y necesidad

**Usuario.** Técnico que da una segunda vida a portátiles retirados de empresas: taller de reacondicionado, entidad
de reutilización o aula de FP de microinformática. Repite la misma operación (memoria, disco, batería) equipo tras
equipo.

**Lo que está documentado [H]:**
- iFixit pone entre los diez fallos más probables al reparar suponer que los tornillos se quedarán en su sitio sobre
  la mesa, y avisa de que uno en el agujero equivocado puede perforar un componente
  (ifixit.com/News/the-10-things-likely-to-go-wrong-when-fixing-a-phone-or-laptop).
- En Technibble un técnico escribe: «Getting the laptop apart isnt the problem, but knowing which type of screw went
  where when putting it back together is», y un lector: «I repaired a laptop last week and had 5 screws left».
- Directiva (UE) 2024/1799 de derecho a reparar, transposición hasta el 31-7-2026. **Los portátiles no están en su
  anexo II** (móviles y tabletas sí): se usa como respuesta preparada, no como argumento.
- Residuos electrónicos: 62 millones de toneladas en 2022, un 22,3 % recogido y reciclado de forma documentada (UNITAR).
- Repair Cafés: «over 2,500» en el mundo (repaircafe.org).

**Lo que NO está documentado:** que acercar el vaso o el recambio sea una molestia para un técnico. No se encontró
ninguna queja escrita sobre ese gesto. Por eso el valor se apoya en dos verificaciones antes del domingo:

1. **La cita del jueves [jue.].**
   - Visita en persona a dos tiendas de reparación de informática de Bilbao, a ser posible adheridas a Bizkaia
     Repara (bonos de reparación de la Diputación, coorganizadora del hackathon; que la edición de 2026 siga
     incluyendo la informática está sin comprobar [H·b]).
   - Llamada a Reciclanet (Erandio, 688 66 22 89; actividad en pausa hasta 2027, puede no haber banco que
     fotografiar), a Koopera y a un profesor de FP de Sistemas Microinformáticos y Redes.
   - Presentación de 30 s: «Participamos en el hackathon de robótica de Bilbao. Estamos haciendo un ayudante para
     quien repara portátiles y no queremos inventarnos el problema. ¿Cinco minutos para seis preguntas?»
   - **Las preguntas:** (1) ¿Cuántos equipos abre en un día bueno y cuántos son la misma operación? (2) ¿Qué hace
     con los tornillos y con la pieza que saca? ¿Le ha sobrado o faltado algo este mes? (3) ¿En qué momento tiene las
     dos manos ocupadas y le falta algo? (4) Si un ayudante le trajera lo que nombra, a unos 25 s por viaje, ¿le
     serviría o le estorbaría? (5) ¿Puedo citarle con nombre y hacer una foto de su banco? (6, del equipo rojo)
     ¿En qué momento tiene algo en la mano que no puede dejar en la mesa?
   - Si nadie contesta o dicen «me estorbaría», se dice así en el pitch, con nombre si lo autorizan.
2. **La medida con y sin robot.** El jueves, **5 cambios de memoria seguidos a mano**, cronometrados y grabados en
   vídeo (después de conseguir el portátil), anotando en cada uno el tiempo total, las veces que las manos salen del
   equipo, los estirones al almacén y los errores. El sábado, **5 cambios con el aprendiz y 5 sin él**, alternando,
   con las mismas cuentas más los segundos de espera al brazo. **Umbrales que obligan a cambiar el relato** (del equipo rojo):
   - Si el jueves el cambio completo a mano dura menos de 50 s (dos viajes del brazo), la reparación suelta no puede
     ser la demo de valor: se cuenta la tanda.
   - Si el sábado el tiempo con robot es peor **y** la espera al brazo pasa del 20 % del total: prohibido decir
     «ayuda»; el relato pasa a «cuánto cuesta enseñar una referencia nueva».
   - Si las veces que las manos salen del equipo no bajan al menos a la mitad, se retira «no suelta el equipo» del
     pitch.
   - Si mejora en algo, ese número es el titular, y solo ese.

**Dónde estaría el valor.** No en la velocidad: el brazo tarda hasta 25 s y la mano tarda 3. Estaría en que **el
almacén queda en el fondo del banco, donde el técnico sentado solo llega estirándose por encima del equipo, y el
aprendiz trabaja mientras él tiene las manos dentro** (abrir, quitar la batería, soltar clips).

## 3. Por qué esta idea

Proceso seguido (documentos en `.plans/necesidad/` y `.plans/brief/`):

1. Directrices destiladas de toda la investigación: criterios del usuario, lecciones de cinco rondas rechazadas,
   rúbrica probable, límites del SO-101 y del VLA, y lo que el mercado de physical AI paga hoy.
2. Cinco generadores independientes → 13 conceptos.
3. Dos evaluadores estrictos y un jurado simulado de cuatro perfiles, sin verse entre sí. Ninguno pasó de 70 de media.
4. Dos finalistas refinados (banco de reparación y plató de catálogo), consejo de cuatro voces y equipo rojo.
5. Brief revisado en cuatro rondas por dos revisores independientes cada una (`santa-method`).

**Por qué no el plató de catálogo** (la otra finalista, 77 ± 5 en autoevaluación): su valor es que la tanda salga
sola sin la persona, lo que choca con la colaboración (U5) y repite el patrón «coger por tipo» ya rechazado; además
necesita un barrido programado que no se puede probar sin robot.

**Cómo cumple los criterios del usuario** (con el veredicto del equipo rojo):

| Criterio | Estado |
|---|---|
| U1 Valor real | **Sin resolver** (el equipo rojo: «falla hoy» en la versión 3). Hipótesis razonada; depende de la cita y de la medida |
| U2 Necesita un VLA | **Dudoso.** Sí si la matriz del sábado demuestra que la red lee la frase; en la rama B no, y se dice |
| U3 Bajo fallo | **Dudoso.** El gesto es el más fiable del SO-101 y los intentos son independientes, pero nada está probado y el equipo no ha grabado nunca |
| U4 Herramienta real tal cual | A medias. Portátil, memoria y operación reales; vaso, plato y almacén son útiles de banco |
| U5 Colaboración | **Dudoso.** En los 5 intentos puntuados nadie repara (es un examen del aprendiz); la colaboración se ve en el vídeo y en la medida |
| U6 Hobby o industria | Sí: banco de reacondicionado y reparación |
| U7 Aplicación que ya se vende | **Sin resolver** (el equipo rojo: «falla» en la versión 3). Analogía con kits y pedidos (Ultra, Tutor [H·b]), que se hacen en almacén, no en un banco |

## 4. Cómo funciona

**Reparto.** Técnico: todo lo fino (trampilla, batería, clips, módulo, encender) y dar la orden. Aprendiz (SO-101 +
SmolVLA): trae al plato el objeto nombrado. Software: traduce el botón (o la voz, si hay red) a la frase fija, lanza
la orden, cronometra y lleva el contador de órdenes sin ayuda.

**Objetos (N1):**

| Objeto | Medidas | Peso | Agarre |
|---|---|---|---|
| Vaso de tornillos (impreso, mate, imán Ø 10 × 3 en la base) | cilindro Ø 40 × 30 mm | ~13 g [est.] | por arriba |
| Caja del módulo de memoria (cartulina kraft 300 g, SO-DIMM dentro y arandela M10 en el fondo) | 95 × 40 × 25 mm; plantillas de repuesto de 35 y 30 mm de ancho | ~25-35 g [medir] | por el lado de 40 mm |
| Caja «nunca vista» (otro color y medida) | 90 × 45 × 20 mm | — | solo para la prueba de generalización |

Fuera: el tercer objeto (rollo de cinta Kapton, ~40 g [medir]), el cambio de orden a mitad y la lectura de etiquetas
(recortes de la versión 4). **Cambio de la versión 4.2:** también sale `Put it away.` (guardar), que la versión 4 dejaba
para la rama A a las 16:00: sus episodios se grabarían después del último ciclo de entrenamiento y nunca se
entrenarían a tiempo. **Otros cambios declarados:** en la rama B ya no elige el LLM (versión 4, cambio 7), sino el
botón o la voz a través del puente (el LLM queda solo en la capa de voz); `dagger` sigue fuera, como en la versión 4;
se mantienen tres ciclos de SmolVLA (el equipo rojo pedía dos) porque la prueba de la frase de las 9:30 necesita el
ciclo 0; y el cambio 2 de la versión 4 (la hoja del equipo pide el kit, una orden por portátil que el LLM encadena)
queda **fuera de la demo puntuada**: en los 5 intentos el técnico nombra cada objeto. La preparación en paralelo solo
se enseña en el vídeo y en la medida con y sin robot («contar la tanda» es eso: cinco cambios seguidos con el
aprendiz preparando mientras el técnico trabaja). La analogía con los kits queda más débil, y se dice.

**Órdenes del VLA** (frases fijas en inglés, idénticas al grabar, entrenar y ejecutar): `Bring the screw cup.` y
`Bring the memory box.` Cambia **qué objeto**, con los dos siempre en el almacén.

**Por qué no es un script:** los objetos no tienen sitio fijo, los coloca el jurado, no llevan marcas y la caja puede
llegar girada. Con dos objetos conocidos, un detector y cinemática inversa también lo harían: se reconoce, y la
respuesta es medida (matriz frase × objeto y caja nunca vista).

**Despliegue (verificado en el código de LeRobot v0.7.0, `especialista-tecnico.md`):**
- `lerobot-rollout --strategy.type=base --interactive=true`, lanzado como subproceso por nuestro puente con el brazo
  aparcado. El modo interactivo solo admite las estrategias `base` y `sentry`.
- Las órdenes entran por la entrada estándar, una por línea (`rollout/interactive.py`). Por intento se escribe
  `/subtask <frase>` y `/start`; `/reset` devuelve el brazo a la postura de arranque y vuelve a la tarea del arranque.
  Usar `/subtask` **antes** de `/start` para elegir la orden no es el «cambio de orden a mitad» que se recortó.
- **Nunca cerrar la entrada estándar:** si se cierra, la sesión se para.
- SmolVLA con `--inference.type=rtc`. ACT sin RTC y sin `--rename_map`, y **no lee la frase**: en la rama B cada
  cambio de orden obliga a parar y relanzar el rollout con el otro modelo (dos procesos no pueden abrir el mismo
  puerto serie; tiempo de relanzamiento sin medir). Si relanzar pasa de ~15 s, salida del especialista técnico: un
  script propio con los dos ACT cargados en memoria con `robot/politica.py`.

## 5. La demo

**Tarea completa declarada:** «el jurado coloca el vaso y la caja donde quiera dentro del marco del almacén, con el
brazo aparcado, y elige uno; el aprendiz lo deja en el plato en menos de 25 s, sin que nadie toque el robot».
**Cinco intentos independientes**: ninguno depende del anterior; entre intentos el jurado recoloca.

**Estimación por intento [est.; error de al menos ± 0,15 según la ficha del finalista]:** traer vaso 0,80, traer caja 0,75 → 5/5 en torno al 24-33 % (equipo rojo)
y ≥ 4/5 en torno al 65 % (aritmética propia). Se planifica para 4 de 5.

**Formato de 5 minutos (en la mesa; tiempos [est.], se cronometran el sábado):**

| Tiempo | Qué pasa |
|---|---|
| 0:00-0:30 | Persona y problema: foto del banco del técnico entrevistado y su frase [jue.] |
| 0:30-0:40 | La tarea que declaramos, en una frase |
| 0:40-3:40 | Cinco intentos (~36 s cada uno: el jurado coloca y elige, ≤ 25 s de brazo, `/reset`). El narrador cuenta los datos mientras el brazo se mueve |
| 3:40-4:10 | Cuaderno del aprendiz: un fallo y el mismo caso corregido (vídeo de 8 s) |
| 4:10-4:35 | El técnico enciende el portátil, reparado antes; muestra la memoria nueva |
| 4:35-5:00 | Cierre: «X de 5 sin ayuda, un aprendiz que se enseña y no se reprograma; dataset, modelo y código publicados» |

**En la rama B** los intentos se agrupan por objeto (el jurado elige antes de cada bloque) para relanzar el ACT una
sola vez; si relanzar pasa de ~15 s, se usa el script con los dos ACT en memoria.

**Versión de 90 segundos** (si el jurado pasa mesa por mesa): un «traer» elegido por el jurado, la matriz en pantalla
y el portátil arrancando. Hoja de datos impresa en A4 para entregar.

**Vídeo de 1 minuto:** la reparación completa con el aprendiz trabajando en paralelo (lo que no cabe en la mesa), la
frase en pantalla, la matriz, un fallo corregido y el arranque.

**Pantallas (tono de taller sobrio, sin personaje ni estética arcade):** P1 hoja de trabajo en la tablet (orden
activa en inglés, casillas de los 5 intentos con su tiempo, «sin ayuda: X de N»); P2 datos (cámaras en vivo, tabla de
episodios); P3 matriz frase × objeto; P4 comparativa de modelos; P5 cuaderno del aprendiz.

**Fuera de nota**, solo si se ha medido el sábado y anunciando antes la tasa: que el jurado dicte la orden y que
pruebe la caja nunca vista. Frase fija: «Esto ya no puntúa; con esta caja acierta X de 5. Si falla, la coge el
técnico: para eso hay una persona al lado.»

## 6. Datos y entrenamiento

**Grabación** (`lerobot-record --resume=true --dataset.no_stamp=true`, un dataset por orden; cámaras `top` y `wrist`
a 640 × 480 y 30 fps; episodios de 12-20 s con `--dataset.episode_time_s=25 --dataset.reset_time_s=8`; mismo
operador y mismo agarre; empezar y acabar en la postura de aparcado):

| Tanda | Cuándo | Orden | Episodios | Variedad |
|---|---|---|---|---|
| 1 | Vie. 19:30-21:00 | vaso | 30 | 5 zonas × 6; la caja en otra zona |
| 2 | Vie. 21:00-22:45 (solo con noche abierta) | caja | 30 | 5 zonas × 6; giro 0°, +30°, −30° |
| 3 | Sáb. 10:30-12:00 | vaso + caja | 20 + 20 | Las zonas y parejas que peor salieron |
| 4 | Sáb. 14:00-15:30 | lo que falle | 20-40 | Demostraciones que empiezan donde falló |

**Total: 120-140 episodios.** Zonas: las de la plantilla de hardware (Z1-Z3 delante, Z4-Z5 detrás, dentro del marco;
`grabar.py` usa la misma numeración). En uno de cada cinco episodios la mano del técnico trabaja en el borde del
plano. Descarte: agarre al segundo intento, choque, objeto fuera del plato, cadencia < 29 Hz. Subida al Hub tras
cada tanda (bonus +3).

**Entrenamiento:**
- Ciclo 0 (vie. ~23:00): SmolVLA en HF Jobs (L4, 12 000 pasos, ~2-2,5 h [est.]) con la fusión de vaso y caja; un
  ACT por orden en la GTX 1660, encadenados por la noche. Opciones obligatorias: `--policy.repo_id` (lo exige
  `--save_checkpoint_to_hub`) y `--policy.empty_cameras=1` si el modelo pide una `camera3`.
- Ciclo 1 (lanzado sáb. ~12:15) con la tanda 3: SmolVLA en HF Jobs (listo ~15:00 [est.]) y los dos ACT en HF Jobs
  (`t4-small`), para que la GTX 1660 quede libre para la inferencia. Ciclo 2 (sáb. ~15:45, listo ~19:00 [est.]) con
  la tanda 4: **solo SmolVLA**, porque ninguna serie posterior mediría un ACT nuevo. Es el último.
- **El modelo se elige por series de 10 en el robot, nunca por la pérdida.** El SmolVLA del ciclo 2 solo sustituye
  al del ciclo 1 si en la comparativa saca al menos lo mismo en vaso y caja.

**Medidas que se enseñan (P3-P5):**
- Prueba de la frase (sáb. 9:30-10:30): 10 intentos por frase con zonas permutadas; columnas vaso / caja / nada.
- Serie de 10 por orden (sáb. 15:30-16:50) con el mejor modelo de cada familia: 40 intentos a ~2 min.
- Con y sin robot (sáb. 16:50-18:20, 5 + 5 cambios; la franja se ajusta con lo cronometrado el jueves).
- Comparativa (sáb. 19:20-20:40): SmolVLA del ciclo 2 en vaso y caja a X/10 (20 intentos), y el mejor SmolVLA y el
  mejor ACT en caja nunca vista y zona nueva a X/5 (20 intentos); 40 intentos a ~2 min. Las filas de ACT y SmolVLA
  del ciclo 1 en vaso y caja salen de la serie de 10 de las 15:30.
- Cuaderno del aprendiz: «fallo → qué cambiamos → antes → después».

**La corrección «del maestro»:** demostraciones normales que empiezan donde falló (tanda 4). La estrategia `dagger`
de `lerobot-rollout` existe en el código, pero añade una columna `intervention` que hay que quitar antes de fusionar
y no se ha probado en nuestro hardware: **queda fuera**, como decidió la versión 4.

## 7. Banco y hardware

Detalle, medidas y planta acotada: [especialista-hardware.md](especialista-hardware.md) y
[banco-planta.svg](banco-planta.svg).

- **Mesa de 120 × 80 cm (mínimo 76 de fondo).** Con 60 cm de fondo el técnico llega al almacén estirándose un
  poco; con 80 cm tiene que estirarse por encima del portátil y del brazo. Pedirla a la organización o juntar dos
  mesas. Sin ella, alternativa del especialista: almacén a la izquierda del robot, a ~52-55 cm del técnico,
  alcanzable estirando, y se dice.
- **Tablero propio de DM 530 × 600 mm** que viaja con almacén, plato y mástil de cámara atornillados, y con los
  taladros y la plantilla de la base del robot. El SO-101 es de la organización: se fija el viernes si lo permiten
  (pregunta al mentor); si no, se marca su posición con la plantilla. Nada se mueve desde el viernes.
- **Alcance del SO-101** (calculado con el modelo MuJoCo del repositorio): coger desde arriba con la pinza casi
  vertical va de 48 a 287 mm del eje; banda de trabajo 120-285 mm. Apertura en la punta 71-111 mm.
- **Disposición** (origen en el eje del robot, base girada 43°): almacén de x −125…125 e y 100…280, con los centros de
  objeto a 120-280 mm del eje en cualquier punto donde el objeto quepa apoyado dentro del marco (comprobado en 35
  puntos); plato en (190, −140), a 236 mm; cámara `top` detrás a la derecha a 600 mm de altura y 59° hacia abajo.
- **Alcance del técnico:** el almacén queda a ~694 mm de su hombro, más allá del alcance cómodo sentado (35-45 cm) y
  dentro del máximo (61-76 cm [H·b]): para llegar hay que estirarse por encima del portátil y del brazo. El plato
  queda a ~446 mm. **Prueba del jueves (sin robot, con el tablero en plantilla):** dos personas de distinta altura,
  sentadas, intentan llegar al almacén.
- **Piezas imprescindibles** (≈ 10,7 h en una impresora clásica, ≈ 4,3 h en una rápida): plato-embudo de boca
  150 × 100 mm y fondo 110 × 64 mm; 3 vasos; soporte rígido de la cámara `top`; soporte de la cámara de muñeca (STL ya
  en `assets/so101/assets/`); marco bajo del almacén sin alojamientos. Andoni modela en SolidWorks los vasos, el
  plato, el soporte `top` y el marco a primera hora (solo existe el STL de la muñeca). Sustitutos en cartón pluma si falta
  tiempo.
- **Electrónica: ninguna** (recortada en la versión 4). El plato conserva el cajeado por si se recupera más adelante.
- **Portátil** con trampilla de memoria sin tornillos o con pocos: HP EliteBook 8460p y 840 G1, HP ProBook 640 G1
  (comprobados en iFixit) o ThinkPad T430 (dos tornillos, fuente secundaria). Dos módulos SO-DIMM DDR3L: uno pequeño
  («viejo») y uno de 8 GB («nuevo»). Dónde: Wallapop con entrega en mano, CeX y Cash Converters de Bilbao, o prestado
  en la cita [sin verificar existencias]. Si no se consigue (ni prestado), la demo puntuada no lo necesita y el arranque desaparece de la demo y del vídeo.

**Lista de la compra del jueves** (precios aproximados sin verificar):

| Compra | Cant. | ≈ € |
|---|---|---|
| Portátil de empresa con trampilla + cargador | 1 | 60-150 |
| SO-DIMM DDR3L (2-4 GB y 8 GB) | 2 | 10-25 |
| Cámara de muñeca: módulo USB UVC de 32 × 32 mm (el que admite el soporte del STL) | 1 | [sin verificar] |
| Tablero DM 10-15 mm cortado a 530 × 600 | 1 | 8 |
| Tubo de aluminio 20 × 20 × 1000 | 1 | 6 |
| Sargentos | 2-3 | 12 |
| Cartón pluma 5 mm A3 | 2 | 6 |
| Cartulina kraft 300 g A4 + cinta de pintor mate 10 mm | 5 + 1 | 6 |
| Goma EVA 2 mm o cinta antideslizante | 1 | 3 |
| Tirafondos 4 × 16, tornillo 1/4"-20, fieltros | — | 5 |
| Cianoacrilato y termofusible | — | 5 |

## 8. Software

Inventario completo: [inventario-software.md](inventario-software.md); plan: [especialista-tecnico.md](especialista-tecnico.md).

| Prioridad | Pieza (jueves) | Horas |
|---|---|---|
| 1 | Comandos fijos de calibrar, teleoperar, grabar, entrenar y ejecutar, probados en seco en los dos portátiles | 2 |
| 2 | `robot/grabar.py`: muestra la siguiente posición de la lista (zona, giro, manos) y cuenta episodios válidos | 1,5 |
| 3 | `robot/puente.py`: el rollout interactivo como subproceso, botones «vaso», «caja», «hecho», «fallo», cronómetro y relanzamiento con otro modelo (rama B); probado sin robot hasta el error de puerto, midiendo cuánto tarda en cargar | 2 |
| 4 | Hoja X/10 y matriz frase × objeto: CSV y página con las tablas | 1 |
| 5 | Pantalla «hoja de trabajo» en la tablet (reutiliza cliente y sonido de la tablet v2) | 1 |
| 6 | Ensayo de la nube: 200 pasos de SmolVLA y ACT en HF Jobs con un dataset público y carga local del modelo | 1 + espera |
| 7 | Voz (opcional): `lewelder/voz.py` con el vocabulario nuevo, misma salida que los botones | 0,5 |

Comandos de referencia (exactos en `especialista-tecnico.md`, apartado C): `lerobot-record` con `--resume` y
`--dataset.no_stamp`; fusión con `lerobot-edit-dataset --operation.type merge`; `lerobot-train` de SmolVLA con
`--policy.path=lerobot/smolvla_base`, `--rename_map` de `top`/`wrist` a `camera1`/`camera2` y `--job.target=l4x1`;
`lerobot-train` de ACT con `--policy.type=act`; `lerobot-rollout` interactivo.

Se reutiliza: cadena de voz con reglas y LLM, cliente y sonido de la tablet, recetas de entrenamiento y scripts de HF
Jobs. Se deja fuera: personaje, ranking, gemelo 3D, lectura de etiquetas, firmware.

## 9. Plan del jueves al domingo

**Jueves 19 (sin robot):**
- **Andoni:** modelar en SolidWorks e imprimir (vasos, plato, soportes, marco); taladrar el tablero con dos juegos
  de agujeros, para la disposición principal y para la alternativa de mesa de 60 cm, porque la respuesta del mentor
  llega el viernes; cortar las cajas (40, 35 y 30 mm de ancho); comprar y probar el portátil y la memoria (13:30).
  Comprobaciones sin robot: alcance con regla y dos personas sentadas intentando llegar al almacén; la caja y el vaso
  en el plato con una maqueta de la pinza (apertura 71-111 mm calculada del modelo); imagen de la cámara `top`.
- **Software (~9 h):** las piezas del apartado 8; instalar LeRobot 0.7 en los dos portátiles y comprobar
  `torch.cuda.is_available()`; `lerobot-find-cameras` y una captura de las dos cámaras a 640 × 480 y 30 fps; que un
  modelo de la nube carga en local; cuánto tarda en cargar el rollout hasta el error de puerto (la política se carga
  antes que el robot, así que mide la carga y si cabe en la GPU); latencia de SmolVLA con observaciones sintéticas
  mediante `robot/politica.py`. Lo que necesita el robot (episodios de prueba, cadencia real) pasa al viernes.
- **10:00-12:00, visitas y llamadas para la cita:** Andoni (con la impresora trabajando) y una persona de software;
  la otra sigue con el software.
- **Hacia las 17:00, con el portátil comprado y el tablero montado** (el almacén marcado con cinta o cartón pluma si
  el marco aún no está impreso): los 5 cambios de memoria a mano, cronometrados y grabados. El técnico de esta medida será el mismo el sábado.
- **Escribir a la organización** (gazteria@bilbao.eus, 944 654 775): rúbrica y formato de los 5 intentos, mesa de
  80 cm de fondo, tablero y hardware propios, si se puede fijar el SO-101 al tablero, si el kit incluye brazo guía,
  si se puede trabajar el viernes y el sábado por la noche y entrar el sábado antes de las 9:30, y si el jurado
  puede colocar los objetos con el brazo aparcado.

**Viernes a domingo.** La agenda oficial da el viernes de 18:00 a 21:00 (presentación a las 17:00, mentores a las
17:45, noche opcional) y el sábado de 9:30 a 21:00. **Las franjas con * solo valen si la organización confirma la
noche abierta o el acceso temprano.** Plan con noche abierta:

| Hora | Hito | Puerta |
|---|---|---|
| Vie. 17:45 | Mentor: preguntas del apartado 12 | — |
| Vie. 18:00-19:30 | Montaje, calibración, cámaras, 2 episodios de prueba (cadencia), 10 agarres por objeto | Caja < 8/10 → caja de 35 o 30 mm |
| Vie. 19:30-21:00 | Tanda 1 (vaso) | 21:00 < 30 válidos → solo vaso |
| Vie. 21:00-22:45 * | Tanda 2 (caja) | — |
| **Vie. ~23:00 *** | Ciclo 0 (SmolVLA en la nube + ACT por orden en la GTX 1660) | < 50 válidos → rama C |
| Sáb. 7:30-9:30 * | Puente con el robot real | — |
| **Sáb. 9:30-10:30** | Prueba de la frase (SmolVLA ciclo 0) | ≥ 8/10 en las dos → A · 6-7 → 20 episodios más por orden con posiciones cruzadas en la tanda 3, y se repite dentro de la serie de 10 · ≤ 5 → B |
| Sáb. 10:30-12:00 | Tanda 3 | — |
| Sáb. ~12:15 | Ciclo 1 lanzado (SmolVLA listo ~15:00) | — |
| **Sáb. 14:00-15:30** | Tanda 4; algún modelo debe mover ya el robot | Ninguno → rama C |
| **Sáb. 15:30-16:50** | Serie de 10 por orden: ACT y SmolVLA del ciclo 1 (con columna «nada» para la prueba de la frase) | SmolVLA ≥ 8/10 → A · ACT ≥ 8/10 y SmolVLA < 7/10 → B · los dos < 6/10 → C · casos intermedios → B, con el modelo que mejor midió en cada orden |
| Sáb. ~15:45 | Ciclo 2 lanzado (solo SmolVLA, HF Jobs; listo ~19:00 [est.]) | — |
| Sáb. 16:50-18:20 | Medida con y sin robot (5 + 5); una persona graba el vídeo a la vez | Umbrales del apartado 2 |
| Sáb. 18:20-19:20 | **Dos series de 5 completas con cronómetro** (ensayo de la demo) | — |
| **Sáb. 19:20-20:40** | Comparativa (apartado 6); montaje del vídeo en paralelo, sin robot | Un objeto < 5/10 con el modelo elegido → C con el objeto que supera 5/10 · D solo si ninguna serie supera 1/5 |
| Sáb. 21:00 | **Montaje congelado** | — |
| Sáb. 21:00-23:00 * | Más ensayos de la serie de 5. Después, dormir | — |
| **Dom. 10:00** | Serie de 5 completa | ≤ 3/5 → declarar solo las zonas y el objeto que salieron · ≤ 1/5 → rama D |
| Dom. 11:00 | Entrega: presentación, dataset y repositorio | — |

**Plan sin noche abierta** (el más probable mientras no se confirme). Tiempos de entrenamiento [est.]:

| Hora | Hito | Puerta |
|---|---|---|
| Vie. 21:00 | Ciclo 0: solo el ACT del vaso (GTX 1660, fuera del local) | < 30 válidos del vaso → rama C |
| Sáb. 9:30-9:50 | Prueba del puente con el ACT del vaso (3 intentos) | — |
| Sáb. 9:50-11:15 | Tanda 2 (caja) | — |
| Sáb. 11:15 | Ciclo 1 de este plan: SmolVLA con vaso y caja y ACT de la caja, los dos en HF Jobs (listos ~13:45) | — |
| Sáb. 11:15-13:45 | Tanda 3 (vaso + caja, posiciones repartidas) | — |
| **Sáb. 13:45-14:45** | Prueba de la frase con el SmolVLA del ciclo 1 | ≥ 8/10 → A · 6-7 → 20 episodios más por orden en la tanda 4 y se repite en la comparativa con el ciclo 2 · ≤ 5 → B |
| Sáb. 14:45-16:00 | Tanda 4; a las 16:00, ciclo 2 (solo SmolVLA, listo ~18:30) | Ningún modelo se mueve → C |
| **Sáb. 16:00-17:20** | Serie de 10 por orden: ACT del vaso (ciclo 0), ACT de la caja y SmolVLA (ciclo 1) | Mismas puertas que el plan con noche |
| Sáb. 17:20-18:50 | Medida con y sin robot (5 + 5) | Umbrales del apartado 2 |
| Sáb. 18:50-19:50 | Dos series de 5 con cronómetro | — |
| **Sáb. 19:50-20:40** | Comparativa recortada: SmolVLA del ciclo 2 en vaso y caja a X/10 (se sustituye la columna de caja nunca vista: en este plan no hay dato de objeto nuevo y no se presume en el pitch) | Mismas puertas |
| Sáb. 21:00 · Dom. | Montaje congelado y domingo igual que el plan con noche | — |

En este plan, la rama B tiene el ACT de la caja desde el sábado a las 13:45, no desde el viernes.

**Puertas: cambios declarados sobre el árbol del equipo rojo** (la versión 4 lo adoptó tal cual):
1. La repetición tras un 6-7/10 se hace dentro de la serie de 10 (o en la comparativa sin noche), porque a las 15:00
   el robot está ocupado con la tanda 4.
2. La rama D se define como «ninguna serie supera 1/5» en todos los sitios.
3. Los casos intermedios de la serie de 10 que el equipo rojo no cubría (por ejemplo, SmolVLA a 7/10) van a la rama B
   con el modelo que mejor midió en cada orden.
4. La puerta de la comparativa decide por objeto (rama C con el objeto que supera 5/10).

## 10. Ramas

| Rama | Cuándo | Tarea declarada | Qué se cuenta |
|---|---|---|---|
| **A** | Una red lee la frase (≥ 8/10) | Vaso o caja elegido por el jurado | Una sola red, dos órdenes, la matriz y la caja nunca vista |
| **B** | La red ignora la frase, o casos intermedios de la serie de 10 | La misma, con un modelo por orden (un ACT, o el que mejor midió); el puente relanza el que toca | «Probamos una red que lee la frase: X de 10. Hoy elige el software entre dos especialistas, y esta tabla dice por qué» |
| **C** | Pocos episodios, nada se mueve a las 14:00, los dos modelos < 6/10 o un objeto < 5/10 en la comparativa | Solo el objeto que mejor sale (normalmente el vaso), en cualquier zona | «Primera semana del aprendiz: sabe una cosa. Esto costó enseñársela» |
| **D** | Ninguna serie supera 1/5 | La versión más corta que salga | Vídeo del mejor intento, cuaderno de fallos y medida con y sin robot |

En todas: vídeo de 1 minuto, dataset en el Hub y repositorio reproducible (+5).

## 11. Riesgos y supuestos sin probar

| # | Riesgo o supuesto | Comprobación más barata | Si sale mal |
|---|---|---|---|
| 1 | SmolVLA ignora la frase con 60-100 episodios | Sáb. 9:30 (sin noche, 13:45), matriz | Rama B, con los ACT entrenados desde el viernes (sin noche: el de la caja, desde el sábado a las 13:45) |
| 2 | La rúbrica no es la de Robotekin o no hay 5 intentos | Correo a la organización el jueves; mentor el viernes 17:45 | Formato de 90 s como principal |
| 3 | El técnico real dice que le estorba | Visitas del jueves | Se cita igual; el valor se defiende solo con la medida |
| 4 | La pinza no coge la caja o no llega al plato | Jueves: maqueta de la pinza en el plato; vie. 18:30: 10 agarres | Caja de 35 o 30 mm, o acercar el plato |
| 5 | Tres personas sin experiencia no graban 50 episodios el viernes | Viernes: cronometrar los 5 primeros episodios | Plan «sin noche abierta» del apartado 9 |
| 6 | Cadencia de grabación < 30 Hz con dos cámaras | Jueves: captura de las dos cámaras sin robot; viernes: 2 episodios | Codificación en streaming o menos resolución |
| 7 | El modelo de HF Jobs no carga en nuestro 0.7.0 | Jueves: ensayo de 200 pasos | Fijar la imagen del job |
| 8 | SmolVLA no cabe o va lento en la GTX 1660 | Jueves: carga del rollout y latencia con observaciones sintéticas | Servidor remoto de políticas o ACT |
| 9 | No hay noche ni acceso temprano | Correo a la organización el jueves | Plan «sin noche abierta» del apartado 9 |
| 10 | Se mueve el montaje entre grabar y la demo | Tablero propio y fotos de referencia de cada cámara | Recalibrar y comparar con la foto cada mañana |
| 11 | Sin wifi o voz que falla con ruido | Botones como entrada principal | La voz se quita sin romper nada |
| 12 | El usuario lo ve como otro «coger y dejar con una historia» | Su «sí» esta noche | No se imprime |

## 12. Pitch y preguntas del jurado

**Las cinco preguntas más dañinas y su respuesta honesta:**
1. **«Eso lo cojo yo en 3 segundos.»** «Desde aquí, solo estirándose por encima del equipo. Y no compite en
   velocidad: trabaja mientras usted tiene las manos dentro. Lo medimos: con aprendiz [sáb.], sin aprendiz [sáb.].»
2. **«¿Y una alfombrilla magnética?»** «Para un portátil suelto, gana la alfombrilla. No le trae lo que está en el
   fondo del banco. [Cita del técnico, jue.].»
3. **«Es un detector y un script.»** «Con dos objetos conocidos, podría. Con uno nuevo el script se reprograma y
   aquí se enseña: esta columna es la caja que nunca vio, X de 5 [sáb.].»
4. **«Es lo de Vitoria.»** La frase del apartado 1.
5. **«¿Por qué VLA y no ACT?»** «Entrenamos los dos y están en la tabla. ACT necesita un modelo por orden y algo que
   elija; el VLA es uno solo que lee la frase.» Si la demo corre con ACT: «hoy corre ACT porque midió mejor».

Regla: primero se concede lo que es verdad, luego el número; si no está medido, se dice.

**Entrega del domingo:** README con qué hace y qué no, las tablas con fecha y número de pruebas, comandos para
reproducir y fotos del montaje; fichas del dataset y del modelo en el Hub; cinco diapositivas como máximo (persona y
problema, cómo funciona, datos, resultados e iteración, límites y siguiente paso).

**Preguntas para el mentor (vie. 17:45):** rúbrica y formato de los 5 intentos (¿seguidos o repartidos en los 5
minutos?); si la orden por voz o por botón cuenta como «sin tocar»; si el jurado puede colocar los objetos con el
brazo aparcado; hardware propio, mesa de 80 cm y si se puede fijar el SO-101 al tablero; si el kit incluye brazo
guía; si se pide vídeo y cómo se entrega; si hay noche abierta.

## 13. Lo que sigue sin resolver

1. **Necesidad (U1):** ningún técnico ha confirmado este gesto. Es la debilidad principal y la cubren la cita del
   jueves y la medida del sábado.
2. **Anclaje de mercado (U7):** la analogía con kits y pedidos es de almacén, no de banco. El usuario dejó sin
   respuesta cinco asistentes de banco por falta de anclaje, y rechazó cinco maquetas por ser «coger y dejar con una
   historia».
3. **Que la red lea la frase (U2):** no se sabrá hasta el sábado a las 9:30.
4. **Formato del evento:** la rúbrica de Robotekin es de segunda mano y su repetición en Bilbao es una inferencia;
   el jurado de 2026 no está publicado; la noche abierta no está confirmada.
5. **Geometría:** que el técnico sentado no llegue al almacén sin estirarse depende de la mesa de 80 cm y se
   comprueba el jueves.
6. **Portátil y memoria** hay que conseguirlos el jueves.
7. **Probabilidades y tiempos** de este documento son estimaciones; se sustituyen por medidas el sábado.

## 14. Lo que necesito del usuario

1. **«Sí» o «no» al concepto** esta noche, sabiendo lo del apartado 13. Las cinco rondas anteriores enseñan que sin
   su «sí» no se imprime.
2. Si es «sí»: quién va el jueves a las tiendas de reparación y quién escribe a la organización.
3. Confirmar el nombre («Aprendiz · Ikastuna») y que Andoni tiene impresora libre el jueves.

---

**Documentos del proceso** (`.plans/brief/`): directrices · 13 conceptos (`conceptos-g0` a `g4`) · evaluaciones A y
B · jurado simulado · síntesis de la ronda 1 · finalistas F1 y F2 · consejo final (versiones 3 y 4) · equipo rojo ·
especialistas técnico, de hardware y de demo · novedades del evento · inventario de software.
