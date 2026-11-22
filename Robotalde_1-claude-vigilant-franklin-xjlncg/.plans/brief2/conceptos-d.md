# Conceptos D · lente «lo que el propio jurado ha vivido» (19-11-2026)

Generador D. Entrada: [directrices-necesidad.md](directrices-necesidad.md) y [../brief/directrices.md](../brief/directrices.md).
Pregunta de partida: ¿qué le ha pasado con las manos a un ingeniero de automatización, a un investigador de Ikerlan, a
un profesor de la EHU o a un técnico de Automach, en el taller, el laboratorio o su afición?
Las cifras de precio vienen de listados de tiendas (ver fuentes al final); no hay ninguna otra cifra externa.

## Situaciones miradas y descartadas

| Situación vivida | Por qué se descarta |
|---|---|
| Purgar los frenos del coche («pisa el pedal») | Fuerza y fuera del banco. El apaño (kit de purga para una persona) ya lo resuelve. |
| Apretar la maneta del freno de la bici mientras se ajusta la pinza | Fuerza; una goma o una brida en la maneta lo resuelve mejor que el robot. |
| Encolar dos piezas en escuadra y aguantar mientras seca | Fuerza y alineación de mm; sargentos y escuadras magnéticas hacen de segunda persona (falla la prueba 4). |
| Atornillar un perfil o un carril DIN que alguien sujeta | El destornillador empuja: el servo cede mm. Falla U3. |
| Soldar un cable a un pad (cable, soldador, estaño: tres manos) | Calor cerca de la mano, precisión de mm y es terreno de MSN. |
| Sujetar la punta negra del polímetro en masa | Precisión de mm; una pinza de cocodrilo de céntimos lo resuelve del todo. |
| Pintar con aerógrafo una figura de maqueta y girarla | Pieza fina; la otra mano ya está libre para sujetarla (no hay necesidad de segunda persona). |
| Barnizar una pieza entera sin saber de dónde cogerla | Las pirámides de pintar resuelven; el robot se mancha; ningún VLA hace falta. |
| «Sujétame el metro» al medir un tablero | Un script vale (U2) y el gancho del flexómetro ya lo resuelve. |
| Pasar un cable por un perfil o una canaleta (uno tira, otro mete) | Cable deformable: la pinza no lo maneja de forma fiable. |
| Desmontar un aparato y guardar los tornillos en orden | Piezas pequeñas y metálicas: la pinza no las coge. |
| «Pásame la llave del 10» en el banco | La herramienta suele estar al alcance (mismo fallo que Aprendiz) y entregar en la mano es un «no» del SO-101. |
| Profesor que señala un componente a la clase | Es apuntar a un punto: se confunde con MSN. |
| Mirar el móvil con la foto de «cómo estaba montado» con las manos con grasa | Un soporte flexible de móvil lo resuelve; el robot no aporta movimiento con sentido. |
| Apuntar medidas del calibre con las manos ocupadas | Lo resuelve una nota de voz; no hay robot que valga. |

Pasan las cuatro pruebas: **Tapa abierta**, **Dale la vuelta**, **¡Dale! (prueba de señales)** y **Graba mis manos**.

---

## 1. Tapa abierta · «Sujétame la tapa, que los cables no llegan»

1. **Frase:** cierras una caja de electrónica o un cuadro pequeño, la tapa lleva botones y pantalla con cables cortos
   y no tienes con qué sujetarla abierta mientras conectas.
2. **Pruebas:** (1) Todo el que ha cerrado una caja impresa, un cuadro de mando o una botonera lo ha vivido.
   (2) «La tapa cuelga de cables cortos y necesito las dos manos para los conectores.» (3) Apaño: sujetarla con la
   barbilla o el antebrazo, apoyarla contra la taza, cinta de carrocero, o «¿me aguantas esto?»; ningún producto, de ahí
   el apaño. (4) El robot hace de compañero que sostiene la tapa en el aire, donde tú la quieres.
3. **Quién y dónde:** maker o técnico de prototipos cerrando una caja impresa; electricista con una botonera; banco de
   electrónica.
4. **Reparto:** la persona sujeta la base y enchufa los conectores (JST, Dupont, bornas) con las dos manos. El robot coge
   la tapa de donde esté y la mantiene quieta e inclinada junto a la base, con los cables flojos.
5. **Órdenes:** `hold the lid` (coge la tapa de la mesa y la sostiene abierta junto a la base) · `close the lid`
   (la posa encima de la base). Cambia el destino y el gesto; la posición de la tapa en la mesa varía, así que un script
   de posiciones fijas no vale.
6. **Tarea declarada (≤ 25 s):** con la tapa en una zona de la mesa marcada (5 posiciones), «hold the lid» → el robot la
   coge y la sostiene en la zona de trabajo 10 s sin moverse. Reposición: la persona vuelve a dejar la tapa en la mesa.
7. **Escena:** caja impresa de ~120 × 80 × 40 mm; tapa de ~120 × 80 × 3 mm con un **asa impresa de 25 mm** en el lado
   (lo que coge la pinza), pantalla OLED y dos pulsadores con cables Dupont de 10-15 cm a una placa ESP32 en la base.
   Peso de la tapa < 100 g. Se imprimen caja, tapa con asa y un soporte en V para la base (~5 h).
8. **Fiabilidad:** gesto difícil: coger el asa y no tirar de los cables (tolerancia ±1 cm; los cables con 5 cm de
   holgura). Sostener quieto es lo más fiable del SO-101. Plan B: ACT por orden; el LLM elige.
9. **Momento memorable:** el juez conecta él mismo los dos conectores mientras el robot sostiene la tapa; dice «close
   the lid» y la pantalla se enciende con su nombre al cerrar.
10. **Débiles:** la demo es en gran parte «sostener quieto» (dificultad percibida baja); los cables pueden tirar de la
    tapa al cogerla; un soporte de pinza articulado también valdría para quien lo tenga. Sin parecido con MSN salvo el
    banco de electrónica.

---

## 2. Dale la vuelta · «Mido con las dos puntas y la placa se me escapa»

1. **Frase:** compruebas una placa con las dos puntas del polímetro, la placa se mueve, y cuando hay que mirar la otra
   cara tienes que soltarlo todo.
2. **Pruebas:** (1) Cualquiera que haya reparado o probado una placa: profesores de laboratorio de electrónica, técnicos
   de I+D. (2) «Tengo las dos manos en las puntas y nadie sujeta ni gira la placa.» (3) Apaño: Blu-Tack, un dedo libre,
   sujeta-placas giratorio (de ~5 £ a ~90 $ según el modelo), o pedírselo al compañero. (4) El robot es el compañero que
   sostiene la placa de cara a ti y la gira cuando se lo pides, sin soltar tú las puntas.
3. **Quién y dónde:** técnico de reparación o de prototipos, alumno de laboratorio de electrónica; banco de medida.
4. **Reparto:** la persona mide continuidad o tensiones con las dos puntas. El robot sostiene la placa (en un marco
   impreso) inclinada hacia la persona y la gira 180° para enseñar la cara pedida.
5. **Órdenes:** `show me the top` · `show me the bottom`. Cambia la cara visible (componentes frente a pistas: muy distinto
   a la vista); la placa parte de cualquier posición en la mesa.
6. **Tarea declarada (≤ 30 s):** placa en su marco sobre la mesa (5 posiciones, cara aleatoria), «show me the bottom» →
   el robot coge el marco y lo sostiene con las pistas de cara a la persona. Reposición: la persona deja el marco en la mesa.
7. **Escena:** placa real de ~100 × 70 mm (p. ej. una placa de pruebas ya soldada) atornillada a un **marco impreso con un
   asa de 25 mm**; peso total < 150 g. Las dos caras pintadas de distinto color en el marco ayudan a la cámara. Se
   imprime el marco y un apoyo inclinado (~3 h).
8. **Fiabilidad:** gesto difícil: la rotación de muñeca con la placa en el aire y aguantar la presión de las puntas
   (tolerancia de posición ±1-2 cm; la presión es baja, pero el servo cede unos mm: hay que probarlo). Plan B: ACT por
   orden; si la presión mueve la placa, el marco apoya un canto en un tope impreso.
9. **Momento memorable:** el juez mide con las puntas, dice «show me the bottom» sin soltarlas y sigue midiendo por
   detrás. El LED de continuidad del polímetro pita.
10. **Débiles:** el sujeta-placas barato resuelve la mitad del problema (sujetar), el robot añade el giro; mismo banco de
    electrónica que MSN aunque el gesto es otro; las puntas empujan y el brazo extendido tiembla.

---

## 3. ¡Dale! · prueba de señales sin compañero

1. **Frase:** en una puesta en marcha, uno activa el sensor y otro mira si la entrada se enciende en el cuadro:
   «¡dale!»… «¿ahora?»… y si estás solo, vas y vienes cien veces.
2. **Pruebas:** (1) Cualquier ingeniero de automatización o técnico de montaje de maquinaria (el perfil Automach,
   Ikerlan) ha hecho la prueba de entradas y salidas a gritos o por walkie. (2) «Necesito que alguien active el sensor
   mientras yo miro el LED de la entrada.» (3) Apaño: el compañero, el walkie, ir y volver, o forzar la entrada en el PLC
   (que no prueba el cableado real). (4) El robot es el compañero que activa el sensor que le pides mientras tú
   miras y mides en el cuadro.
3. **Quién y dónde:** técnico de puesta en marcha, profesor de FP o grado de automatización; banco de pruebas de un cuadro
   antes de montarlo en la máquina (se hace así de verdad: sensores sueltos sobre la mesa, cableados al cuadro).
4. **Reparto:** la persona mira los LED de entrada, mide con el polímetro en la borna y anota. El robot coge la varita de
   prueba (asa con imán) y la acerca al sensor que se le nombra; los sensores están sueltos en la mesa.
5. **Órdenes:** `trigger the blue sensor` · `trigger the yellow sensor` (dos sensores magnéticos con carcasas impresas de
   colores distintos, en posiciones que cambian). Cambia el objetivo, distinto a la vista; script fijo no vale porque
   los sensores se mueven.
6. **Tarea declarada (≤ 30 s):** «trigger the blue sensor» → el robot coge la varita de su soporte, la lleva sobre el
   sensor azul, se enciende el LED de la entrada 2 s y la devuelve al soporte. Reposición: nada (la varita vuelve sola);
   la persona mueve los sensores entre intentos.
7. **Escena:** dos sensores Hall o reed (ya comprados) en carcasas impresas de ~40 × 40 × 25 mm con base pesada; varita
   impresa de 25 mm de diámetro con imán de neodimio en la punta (< 50 g); una «regleta de entradas» con ESP32 y dos LED
   grandes (firmware ya hecho). Impresión ~4 h. El sensor detecta a 1-2 cm del imán según el modelo (hay que medirlo):
   tolerancia de centímetros, no de mm.
8. **Fiabilidad:** gesto difícil: acercar la punta a menos de ~1,5 cm del sensor; se agranda la zona con una carcasa en
   embudo. Plan B: ACT por orden. Si la electrónica falla, se ve igual el gesto; los LED son un extra.
9. **Momento memorable:** el juez hace de técnico: mira la regleta, dice «trigger the yellow sensor», el LED se enciende y
   él marca la casilla en una hoja de prueba de E/S real. Una frase al jurado de automatización: «esto lo habéis hecho a
   gritos».
10. **Débiles:** riesgo de «maqueta» (U4): hay que contarlo como el banco de pruebas real del cuadro, no como una
    máquina en miniatura; con sensores inductivos de verdad la distancia baja a mm (por eso magnéticos); en una planta
    real los sensores están lejos del cuadro, fuera del alcance de un brazo de mesa. Nada parecido a MSN.

---

## 4. Graba mis manos · el compañero que sujeta la cámara

1. **Frase:** quieres grabar cómo haces un procedimiento (para una clase, una instrucción de trabajo o el proveedor) y
   no tienes a nadie que sujete el móvil donde hace falta.
2. **Pruebas:** (1) Profesores que graban prácticas, técnicos que documentan un montaje, cualquiera que ha grabado un
   tutorial. (2) «Tengo las manos ocupadas y la cámara nunca está donde miro.» (3) Apaño: soporte cenital de móvil
   (de ~17 $ a ~150 $), móvil apoyado en una taza, cámara en la cabeza, o «grábame tú». (4) El robot es el compañero que
   mueve la cámara al plano que pides, cosa que el soporte fijo no hace.
3. **Quién y dónde:** profesor de laboratorio, técnico de calidad o mantenimiento, maker que hace tutoriales; cualquier banco.
4. **Reparto:** la persona hace el procedimiento real (montar un conector, cablear una borna, medir). El robot sostiene
   la cámara y cambia de plano según la orden.
5. **Órdenes:** `film my hands` (plano cenital de la zona de trabajo) · `film the meter` (primer plano del polímetro, que
   se mueve por la mesa). Cambia qué se encuadra; el polímetro cambia de sitio, así que un script de dos poses no vale.
6. **Tarea declarada (≤ 20 s):** cámara en su soporte, «film the meter» → el robot coge la cámara y la deja quieta
   encuadrando el polímetro 5 s. Reposición: la persona mueve el polímetro; la cámara vuelve al soporte.
7. **Escena:** nuestra segunda webcam (ligera, con cable USB) en una **carcasa impresa con asa de 25 mm**; el móvil es
   opción si pesado con funda queda < 300 g (pesarlo). Polímetro real. Soporte impreso para la cámara (~3 h).
8. **Fiabilidad:** gesto difícil: dejar la cámara quieta con el encuadre correcto (tolerancia de varios cm; se verifica
   en pantalla). El cable de la webcam debe ir por el brazo. Plan B: ACT por orden.
9. **Momento memorable:** la pantalla grande proyecta lo que graba el robot; el juez cablea una borna y dice «film the
   meter»: el plano salta a la lectura. Al final se le da el vídeo de su propio procedimiento.
10. **Débiles:** **es el más parecido a MSN** (apuntar algo a un punto); hay que decirlo y defender que aquí el robot
    coge y lleva un objeto, y la orden decide qué mirar; el soporte fijo resuelve gran parte; la necesidad es más de
    documentación que de «segunda mano».

---

## Fuentes de precios

- Sujeta-placas: [Maplin](https://pro.maplin.co.uk/products/pcb-rotating-clamp-holder) (4,89 £),
  [Fruugo](https://www.fruugo.us/adjustable-pcb-holder-with-clamps-360%25C2%25B0-rotation-soldering-helping-hands-for-electronics/p-454036816)
  y [guía de microcontrollerslab](https://microcontrollerslab.com/best-pcb-holders-helping-hands-soldering-buying-guide/).
  El techo de ~90 $ es de un listado de Fruugo visto en el buscador.
- Soporte cenital de móvil: [NEEWER DS034](https://neewer.com/products/neewer-basics-ds034-camera-desk-mount-stand-with-c-clamp-phone-holder-66610105)
  (29,99 $), [SmallRig 4324](https://www.jbhifi.com.au/products/smallrig-desk-overhead-photography-live-streaming-bracket-4324).
  El rango 17-150 $ sale del extracto del buscador, sin verificar cada tienda.
