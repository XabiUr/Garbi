# Conceptos G4 · lente «lo que solo un VLA hace bien y un script no» (18-11-2026)

Marcas: **[H·b]** visto solo en el extracto del buscador · **[I]** inferencia · **[E]** estimación propia, sin medir ·
**[sin fuente]** no respaldado. Cifras de SmolVLA: `investigacion/lecturas/smolvla.md`. Rúbrica: apartado 9 (Robotekin).

## Lo que es verdad para los tres (límites de SmolVLA con 100-150 demostraciones)

- **Lo que sí:** un gesto corto (15-25 s) con **2-3 objetos que se distinguen a simple vista**, colocados en cualquier
  punto de una zona de ~30 × 20 cm, 50 episodios por orden (10 × 5 posiciones). Referencia: coger y dejar 75 % (SO-100
  multitarea), Lego en SO-101 90 % en posiciones vistas y 50 % en no vistas; ACT 70 % / 40 %.
- **Lo que no:** «muchos objetos» (son 3, no 30), leer etiquetas, objetos que solo difieren en el texto, secuencias
  largas en una orden. Objeto nuevo de categoría conocida: ~50 % [E]; va **fuera** de los 5 intentos puntuados.
- **Cambio de orden a mitad (`/subtask`):** hay parada breve y el brazo arranca desde una pose que no vio al grabar.
  Se graban 15-20 episodios «de redirección» (empiezan con la pinza sobre el objeto equivocado). Éxito ~50 % [E]:
  es el momento de «no es un script», también fuera de los 5 puntuados. `torch.compile` desactivado; RTC con
  horizonte 10.
- **Prueba ante jurado técnico (igual en los tres):** (1) el juez recoloca los objetos con su mano; (2) el juez elige
  la orden; (3) la pantalla muestra `modelo: 1 · orden: "<frase>"`; (4) una vez, cambia de idea a mitad; (5) se enseña
  la tabla X/10 por modelo.
- **Historia de datos (20 puntos), igual en los tres:** ronda 1 (viernes-sábado mañana) → X/10 por orden con
  `--strategy.type=episodic` → fallos clasificados (agarre, objeto equivocado, destino) → ronda 2 con correcciones
  `--strategy.type=dagger` [mecánica de la toma de control sin verificar] → X/10 otra vez; ACT por orden como
  comparativa y plan B. Cenital = `camera1`, muñeca = `camera2`. Dataset y repositorio públicos (+5). **El rescate
  con el brazo guía se cuenta aquí, no se hace en la demo puntuada.**

---

## A · ATREZZO

1. **Frase.** «Tú encuadras con las dos manos en el móvil; dices qué quieres en el plano y el robot te lo pone, te lo
   quita o te lo cambia, sin que pierdas el encuadre.»
2. **Usuario real.** Quien vende lo que hace o lo que le sobra (Etsy, Wallapop, Vinted) y hace las fotos solo en una
   mesa. Con el móvil en las manos mira la composición; para mover un adorno suelta el móvil, lo mueve, vuelve a
   encuadrar y repite. Un tercio de 339 revendedores dice que fotografiar y publicar es lo más difícil del trabajo
   (encuesta Fleek; fuente leída en `.plans/necesidad/afondo-fotos-producto.md`); mediana de 15 min por imagen antes
   de usar IA (Photoroom, encuesta de parte). En estudio ese trabajo lo hace un estilista mientras el fotógrafo mira
   la pantalla [H·b, guías de Tether Tools]. Falta la frase de una vendedora real: pedirla el jueves.
3. **Reparto.** Persona: coloca su producto en el centro, encuadra, dirige de palabra, dispara. Robot: trae el adorno
   nombrado desde la bandeja al plató, lo retira y sale de plano.
4. **Referencia real.** Fotografía de producto automatizada (Orbitvu, PhotoRobot: mesas y brazos que mueven cámara y
   luz) [sin fuente comprobada, verificar]; el hueco es el estilismo, que sigue siendo manual. Familia de mercado:
   «elegir qué coger según la orden» (Ultra, Tutor; directrices §5). **No hay un producto de estilismo robótico
   vendido que yo pueda citar**: es el anclaje más flojo de los tres.
5. **Escena.** Fondo de cartulina blanca curvada de 50 × 70 cm y 2 paneles LED fijos (la luz es nuestra y no
   cambia). Plató: 3 marcas (izquierda, centro, derecha), el centro para el producto del juez. Bandeja lateral de
   250 × 150 mm con fieltro. Adornos reales [medir el jueves]: suculenta artificial en maceta (Ø ~50 × 60 mm, ~60 g),
   piña de pino (Ø ~45 × 60 mm, ~15 g), taco de madera (40 × 40 × 40 mm, ~35 g). Se imprime: bandeja, marcas con
   reborde de 3 mm, almohadillas de pinza de TPU. Cámaras: cenital en trípode y muñeca; la foto la hace el móvil del
   juez.
6. **Órdenes.** Mínimo: `Put the plant on the set` / `Put the pine cone on the set`. Extra: `Clear the set` (lo
   que haya vuelve a la bandeja; el estado se ve en la escena), `Put the wood block on the set`. Cambia **qué
   objeto** y, en N3, **dónde** (`on the left` / `on the right`). El LLM compone: «bodegón de otoño» → piña + taco.
   Script no vale: los adornos están donde los deje el juez en la bandeja, el producto del centro es distinto cada
   vez y la orden la decide una persona que cambia de idea mirando la pantalla.
   **Tarea completa (≤ 25 s):** desde reposo, llevar el adorno nombrado de la bandeja al plató y volver a reposo.
   Se repite 5 veces sin entrar en el brazo alternando poner y `Clear the set`: la escena se repone sola.
7. **Guion (3 min).** 0:00 frase; en pantalla, tabla X/10 y «modelo 1». 0:15 el juez deja **su** reloj, cartera o
   llaves en el centro y revuelve la bandeja. 0:30 con su móvil en las manos dice «pon la planta»; el robot la pone
   y sale de plano; foto. 1:00 «quítala»; 1:20 «pon la piña»; foto. 1:45 **cambio a mitad:** pide el taco y, con el
   brazo en el aire, «no, mejor la planta» (`/subtask`). 2:10 «bodegón de otoño»: el LLM encadena dos órdenes.
   2:40 **momento:** el juez enseña en su móvil tres fotos distintas de su objeto, hechas sin soltar el encuadre.
   **Recuperación:** si un adorno cae tumbado, «quítalo» lo recoge igual (se graba así); si falla dos veces, el
   compañero pulsa «ACT» y sigue. Los 5 intentos puntuados se hacen aparte, antes del cambio a mitad.
8. **Escalera.** N1 (sáb 12:00): planta y piña al centro del plató, orden por teclado, sin producto. N2 (sáb 20:00):
   `Clear the set`, producto del juez en el centro, voz, pantalla con la orden. N3 (dom): tercer adorno,
   izquierda/derecha, composición por LLM, cambio a mitad.
9. **Fiabilidad.** Gesto difícil: coger la piña (irregular) sin volcarla; tolerancia de agarre ±1 cm, de depósito
   ±3 cm. Riesgo propio: el producto del juez es un objeto no visto en el centro de la imagen; se graba con 15-20
   objetos distintos en el centro (y eso es variedad que contar). Espero **70-75 % por intento con SmolVLA [E]**
   (3,5 de 5) y 85 % con un ACT por orden [E, rango 80-96 % de las directrices]. Si el VLA ignora el texto se ve
   (pone el adorno equivocado) → plan B: ACT por orden y el LLM elige.
10. **Jueves.** ~4 h de impresión [E]. Sin electrónica. Compras: cartulina, 2 paneles LED, adornos. Se reutiliza:
    voz → LLM → orden cerrada, tablet (pantalla de orden y marcador), flujo grabar → entrenar → evaluar, HF Jobs.
11. **Puntos débiles.** (a) Utilidad discutible para un jurado de industria: «fotos para Wallapop» puede sonar
    menor; contarlo como catálogo de artesano o pyme. (b) Disparar una foto es trabajo de manos, pero ligero: U5
    se cumple justo. (c) Una persona mueve una maceta en 2 s: el valor es no soltar el encuadre, hay que enseñarlo.
    (d) Tres adornos son pocos; decir el límite antes de que lo pregunten. (e) Parecidos: ninguno entre los
    ganadores revisados; cerca del estudio de fotos ya investigado, pero aquí el robot no toca el producto ajeno.
12. **Autoevaluación.** Demo 20/30 · datos 16/20 · dificultad 11/15 · utilidad 9/15 · innovación 8/10 ·
    presentación 9/10 = **73/100**.

---

## B · KIT DE CLASE

1. **Frase.** «Antes de cada clase de robótica alguien cuenta piezas en 12 cajas: tú embolsas la tornillería y los
   cables, el robot pone en cada caja las piezas gordas que le nombras, estén donde estén.»
2. **Usuario real.** Profesor o monitora de extraescolar de robótica, o quien vende kits maker. Prepara y repone
   kits a mano. En el foro de VEX un profesor describe reordenar los kits a final de curso como mucho trabajo y otro
   habla de más de 40 horas [H·b: vexforum.com/t/classroom-setup-and-spare-parts/2368, página no abierta]; hay
   artículos de extensión universitaria sobre bandejas para inventariar kits [H·b, archives.joe.org]. Usuarios a los
   que llamar el jueves: academias de robótica educativa de Bilbao y quien organiza campamentos tecnológicos [I];
   sin esa llamada, el criterio 8 queda en ámbar.
3. **Reparto.** Persona: cuenta tornillos y cables en bolsas, comprueba la pila con el polímetro, cierra y etiqueta.
   Robot: lleva a la caja abierta las piezas rígidas del kit que se le nombran.
4. **Referencia real.** Ultra con Physical Intelligence (kits y pedidos; 96,4 % de autonomía declarado en un turno)
   y Tutor Intelligence (kitting cobrado por hora), según `.plans/necesidad/startups-eeuu-asia.md` [H·b].
5. **Escena.** Kit real de «coche robot 2WD» [medidas a confirmar con calibre]: motorreductor TT amarillo
   (~70 × 22 × 19 mm, ~30 g), módulo driver L298N rojo con disipador negro (~43 × 43 × 27 mm, ~26 g), pila de 9 V
   (48,5 × 26,5 × 17,5 mm, ~45 g). 2 motores, 2 drivers y 2 pilas sueltos en un tapete de fieltro de 300 × 200 mm.
   Caja de kit real de ~180 × 120 × 50 mm en una base con tope en L. Ruedas, Arduino, cables y tornillos los pone
   la persona (planos, pequeños o deformables: la pinza no los coge). Se imprime: marco del tapete, base de la
   caja, almohadillas de pinza. Cámaras: cenital y muñeca.
6. **Órdenes.** Mínimo: `Put the yellow motor in the box` / `Put the red driver in the box`. Extra:
   `Put the battery in the box`. Cambia **qué objeto**; forma y color distintos a la vista. El LLM compone desde la
   ficha de la clase: «mañana, seguidor de líneas» → 2 motores + driver. Script no vale: piezas sueltas y giradas
   en cualquier punto del tapete, y una pieza nueva del kit son 50 demostraciones, no programación.
   **Tarea completa (≤ 25 s):** con el tapete revuelto por el juez, coger la pieza nombrada y dejarla en la caja.
   Se repite 5 veces sin tocar: hay 6 piezas en el tapete y cada intento gasta una.
7. **Guion (3 min).** 0:00 frase y tabla X/10. 0:15 el juez revuelve las 6 piezas y elige en la tablet la clase de
   mañana. 0:30 el juez mete en bolsa 4 tornillos y 2 cables mientras el robot lleva el primer motor. 1:00 segundo
   motor; el juez comprueba la pila con el polímetro. 1:30 **cambio a mitad:** con el brazo hacia el driver, «no,
   primero la pila». 2:00 **prueba de categoría:** un compañero deja una pila de 9 V de otra marca y otro color; se
   avisa de que es ~50 %. 2:30 **momento:** el juez cierra la caja, pega la etiqueta «Kit 7 · completo» y la pantalla
   marca el kit en verde. **Recuperación:** pieza caída fuera de la caja → queda en el tapete o en la mesa y se
   repite la orden; segunda vez → botón «ACT».
8. **Escalera.** N1 (sáb 12:00): motor y driver, caja fija, teclado. N2 (sáb 20:00): pila, voz, lista de la clase en
   pantalla, tabla X/10. N3 (dom): composición por LLM, cambio a mitad, y la vuelta: `Put the yellow motor in the
   bin` para recoger los kits después de clase.
9. **Fiabilidad.** Gesto difícil: motor tumbado, 22 mm de ancho, que puede estar pegado a otra pieza; tolerancia
   ±1 cm al coger, ±4 cm al dejar. Sesgo conocido: coger la pieza más cercana aunque se pida otra; se graba con
   posiciones intercambiadas. Espero **70 % por intento con SmolVLA [E]** (3,5 de 5) y 85 % con ACT por pieza [E].
   Si el VLA falla, se ve la pieza equivocada en la caja: la persona la saca al cerrar.
10. **Jueves.** ~3 h de impresión [E]. Electrónica: ninguna crítica. Compras: 2 kits de coche robot, cajas,
    etiquetas. Se reutiliza: voz, tablet, flujo de entrenamiento, criterio «objeto en zona» de `robot/evaluar.py`.
11. **Puntos débiles.** (a) A la vista es coger y dejar por colores: lo más cercano a «clasificador previsible» y a
    los conceptos rechazados por maqueta; solo lo salva la mesa real de un profesor real. (b) Una persona mete un
    motor en una caja más rápido. (c) Se parece a «Pedido Listo» de G2: mismo gesto, otro usuario. (d) El robot solo
    hace 3 de las ~15 referencias del kit.
12. **Autoevaluación.** Demo 20/30 · datos 16/20 · dificultad 10/15 · utilidad 11/15 · innovación 4/10 ·
    presentación 7/10 = **68/100**.

---

## C · ENSÉÑAMELO

1. **Frase.** «Tienes las dos manos en las puntas del polímetro y al otro lado alguien te dice "enséñame el
   contactor": la cámara va sola a lo que se nombra, esté donde esté en el carril.»
2. **Usuario real.** Técnico de mantenimiento o montador de cuadros que comprueba un cuadro en el banco con un
   experto en remoto, y el profesor de FP que enseña una práctica a 20 alumnos. Hoy sujeta el móvil con una mano o
   lo apoya y lo recoloca. El Tec de Monterrey usa tres cámaras para enseñar microelectrónica y los fabricantes de
   soportes reconocen que hay que repetir tomas [H·b, `.plans/necesidad/ideas-asistentes-banco.md`]. Sin cifra de
   horas [sin fuente]. Llamar el jueves a un profesor de FP de electricidad.
3. **Reparto.** Persona: mide continuidad con las dos puntas, cambia módulos de sitio en el carril, explica. Robot:
   lleva la cámara de muñeca a ~20 cm del elemento nombrado y la deja quieta. No coge nada.
4. **Referencia real.** Asistencia remota en mantenimiento (TeamViewer Frontline, Dynamics 365 Remote Assist): se
   paga, pero es software con gafas o móvil, no un brazo [sin fuente comprobada]. **No conozco una startup de
   physical AI que venda esto**: U7 se cumple a medias y hay que decirlo.
5. **Escena.** Carril DIN real de 35 mm y 300 mm de largo, tumbado, con 4 aparatos reales sin tensión [medir]:
   magnetotérmico (18 mm de ancho), contactor (~45 mm), fuente de alimentación DIN (~50 mm), relé con capuchón
   transparente (~25 mm). Se sueltan y se cambian de orden con la mano. Polímetro real y un puente ya cableado para
   que pite. Se imprime: base inclinada del carril, tope que impide a la pinza bajar de 12 cm. Cámaras: cenital y
   muñeca (la de muñeca es el producto: su imagen sale en la pantalla grande).
6. **Órdenes.** Mínimo: `Look at the contactor` / `Look at the power supply`. Extra: `Look at the breaker`,
   `Show the whole panel`. Cambia **a qué elemento** va la cámara. Script no vale si el juez cambia el orden de los
   aparatos en el carril: con posiciones fijas **sí** valdría, y por eso el cambio de orden es obligatorio en la demo.
   **Tarea completa (≤ 12 s):** desde reposo, encuadrar el aparato nombrado (centrado en la imagen de muñeca) y
   mantenerlo 3 s. Se repite 5 veces sin tocar: no hay nada que reponer.
7. **Guion (3 min).** 0:00 frase; pantalla grande con la imagen de muñeca. 0:15 el juez A suelta dos aparatos y los
   cambia de sitio. 0:35 el juez B, a dos metros con la tablet, hace de experto: «enséñame la fuente»; la cámara va.
   1:00 el juez A pone las puntas y pita. 1:20 «ahora el contactor». 1:45 **cambio a mitad:** «el magneto... no, el
   contactor otra vez». 2:10 el juez A vuelve a cambiar el orden y el B elige. 2:40 **momento:** el juez B ha
   dirigido una comprobación a distancia solo hablando y el A no ha soltado las puntas. **Recuperación:** encuadre
   malo → se repite la frase (8 s, no hay nada caído).
8. **Escalera.** N1 (sáb 12:00): 2 aparatos, teclado. N2 (sáb 20:00): 4 aparatos, voz, pantalla, comprobación
   automática del centrado con un detector sencillo. N3 (dom): `Show the whole panel` y cambio a mitad.
9. **Fiabilidad.** No hay agarre: tolerancia de ±3 cm en el encuadre. Episodios de ~8 s: caben 150-200 en una tarde
   con muchas permutaciones del carril. Espero **85 % por intento con SmolVLA [E]** (4,25 de 5; 5 de 5 en ~44 % de
   las veces). Riesgo real: dos aparatos grises parecidos desde arriba → elegirlos distintos de forma y color. Plan
   B honesto: con ACT no hay elección por nombre; el respaldo es detección clásica más cinemática, y entonces deja
   de ser un VLA.
10. **Jueves.** ~3 h de impresión [E]. Electrónica: ninguna. Compras: carril y 4 aparatos (ferretería eléctrica).
    Se reutiliza: voz, tablet, ArUco y visión para la comprobación del centrado.
11. **Puntos débiles.** (a) **Criterio 4 con reserva:** un brazo que apunta algo hacia donde trabaja un operario
    es la familia de MSN, y este jurado lo vio ganar hace un mes; no hay luz ni soldadura, pero se dirá. (b)
    Dificultad baja en la escala de la rúbrica: no coge ni un objeto. (c) Sin referencia de physical AI vendida.
    (d) El brazo trabaja a 15-20 cm de las manos: tope físico y velocidad limitada. (e) El temblor del servo se ve
    en la imagen. (f) Retoma «Cámara de banco», que el usuario dejó sin respuesta.
12. **Autoevaluación.** Demo 25/30 · datos 15/20 · dificultad 6/15 · utilidad 10/15 · innovación 4/10 ·
    presentación 8/10 = **68/100**.

---

## Cuál defendería

**A · Atrezzo.** Es el único de los tres en el que el cambio de orden a mitad es el uso normal y no un truco para el
jurado (quien compone una foto cambia de idea mirando la pantalla), la escena se repone sola para los 5 intentos, la
luz es nuestra y el juez se va con fotos de su objeto en su móvil. Su riesgo no es técnico: es que un jurado de
industria vea poca utilidad y que no exista un producto de physical AI igual que citar.

B es el más fácil de explicar a ese jurado y el que tiene queja con fuente, pero es el más previsible y el más
cercano a lo ya rechazado. C es el que más aciertos dará (no coge nada) y el que peor puntúa en dificultad e
innovación ante un jurado que ya premió a MSN.

Pendiente común antes de decidir: una frase de un usuario real por concepto (jueves), y medir en el robot el viernes
si SmolVLA obedece a la frase con dos objetos; si no, los tres pasan a «ACT por orden + LLM» (C no puede).
