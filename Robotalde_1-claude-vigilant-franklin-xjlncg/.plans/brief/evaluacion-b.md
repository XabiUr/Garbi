# Evaluación B de los 13 conceptos (evaluador independiente, 18-11-2026)

Entrada: `directrices.md`, `evento-novedades.md` y las cinco fichas `conceptos-g*.md`. No se han tenido en cuenta las
autoevaluaciones ni las recomendaciones de los autores. Nada está medido en un robot: toda probabilidad es una
estimación mía con ±0,15 de margen, así que **diferencias de menos de 5 puntos entre conceptos son ruido**.

**Cómo estimo p (acierto por intento).** Base del apartado 6: SmolVLA multitarea ~75 % en coger y dejar, 90 % en
posiciones vistas y 50 % en no vistas; ACT 80-96 % con posiciones grabadas. Con equipo novato, dos ciclos de
entrenamiento, objetos en posición libre y el mejor de los dos modelos: un movimiento tolerante con objeto fácil
0,75-0,80; con objeto irregular, pequeño o metálico 0,55-0,65; dos movimientos encadenados, el producto.
Demo = 30 × p; 5/5 = p⁵. Se puntúa la tarea **tal como la declara la ficha**; si no la declara (G1 y G2), tomo
«una orden = un intento», salvo que la escena no se reponga sin un segundo movimiento.

**Conclusión antes del detalle: ninguno pasa de 68.** Los 13 son variantes de «coger un objeto y dejarlo en una
zona». Ninguno tiene un usuario real citado sobre el gesto concreto que hace el robot, y ninguno llega al 30 % de
probabilidad de 5/5. El concepto ganador no está en la lista tal cual: sale de una fusión (apartado 4).

---

## 1. Ficha por concepto

Formato: criterios (solo se nombran los que no pasan limpio; el resto PASA) · p y demo · rúbrica
(demo/datos/dificultad/utilidad/innovación/presentación) · fallo en directo · reproche del jurado.

### G0 · Aprendiz — 68
- **Criterios.** U4 PASA (herramientas reales tal cual, el mejor en esto). U1 DUDOSO: acercar algo que está a 30 cm
  lo hace mejor la persona. Crit. 2 DUDOSO: destornillador tumbado y alicates son justo «metálico liso y pequeño».
  Crit. 7 DUDOSO: «5 veces con herramientas distintas» son 5 órdenes, no 2. Crit. 8 DUDOSO: la falta de aprendices
  es una cifra «por verificar», la lección de Machero. Crit. 4 PASA con reserva (mismo banco que MSN, sin luz).
- **p = 0,60** (1 movimiento; 0,75 con vaso o carrete, 0,45 con destornillador o alicates). Demo 18; 5/5 = 8 %.
- **Rúbrica.** Demo 18 · Datos 16 (la corrección del maestro es la mejor historia de «cómo iteramos») · Dificultad
  11 (5 objetos reales distintos, posición libre) · Utilidad 8 (usuario genérico, sin cita) · Innovación 6 ·
  Presentación 9 (la mejor frase de las 13). **Total 68.**
- **Fallo en directo:** el destornillador rueda o se escapa de la pinza. **Reproche:** «lo tengo a un palmo; ¿para
  qué quiero un brazo que tarda 25 s en dármelo?».

### G1-A · Tornillero — 66
- **Criterios.** U4 PASA (portátil real que arranca). Crit. 8 PASA (única queja leída: iFixit). U2 y crit. 3 DUDOSO:
  vasos de colores sobre esterilla se resuelven con segmentación de color y cinemática; la memoria del orden es del
  LLM. Lección «cubos de colores disfrazados» DUDOSO. U1 DUDOSO: una alfombrilla magnética hace lo mismo.
- **p = 0,78** (1 movimiento por orden, alternando guardar y traer; el vaso de Ø40 mm y 15 g es el objeto más fácil
  de todos). Demo 23; 5/5 = 29 %. Riesgo: vasos idénticos salvo el color, el caso en que la red ignora el texto.
- **Rúbrica.** Demo 23 · Datos 12 (un solo tipo de objeto: poca variedad que contar) · Dificultad 8 · Utilidad 10 ·
  Innovación 6 · Presentación 7 (desmontar un portátil no cabe en 5 minutos con 5 intentos dentro). **Total 66.**
- **Fallo en directo:** trae el vaso del color equivocado, o el juez tarda 2 minutos con un tornillo.
  **Reproche:** «eso es un ArUco y un script; y lo arregla una alfombrilla magnética de 8 €».

### G1-B · Recambista — 62
- **Criterios.** Crit. 8 DUDOSO grave: la ficha reconoce que no hay queja con fuente. Lección de Relevo DUDOSO
  (repuestos otra vez, aunque aquí encaja la persona). U1 DUDOSO («lo cojo yo antes»). Crit. 7 DUDOSO: depende de
  comprar un kit arcade el jueves. Crit. 3 DUDOSO en N1: botón rojo frente a amarillo solo difiere en el color.
- **p = 0,62** por pieza (botón de 30 mm que rueda, bola de Ø35 mm). Demo 19; 5/5 = 9 %. El guion real encadena
  dos piezas: 0,38.
- **Rúbrica.** Demo 19 · Datos 13 · Dificultad 10 · Utilidad 6 (nicho arcade, sin usuario) · Innovación 6 ·
  Presentación 8 (jugar con lo reparado es buen final). **Total 62.**
- **Fallo en directo:** la bola rueda fuera al cerrarse la pinza. **Reproche:** «es un juguete; en un taller los
  recambios están en cajones etiquetados».

### G1-C · Sondas libres — 62
- **Criterios.** U5 PASA (el más fuerte: manos de verdad ocupadas). Crit. 8 PASA (EEVblog leído). U4 DUDOSO: placas
  de prácticas hechas por nosotros en marcos impresos con mango; una placa real no trae mango. Crit. 4 DUDOSO: robot
  que asiste al operario sobre una placa, el banco de MSN. Crit. 2 DUDOSO: el comprobador con contactos de muelle y
  el empuje de las puntas son fuerza y precisión. Crit. 3 DUDOSO: volteo programado, el texto solo elige color.
- **p = 0,45** (2 movimientos: presentar a 30° en el tope 0,60 × llevar al comprobador 0,75; sin el segundo la
  escena no se repone). Demo 13,5; 5/5 = 2 %. Además el juez empuja una placa que sostiene el robot: «sin tocar el
  robot» queda en duda.
- **Rúbrica.** Demo 13 · Datos 12 · Dificultad 12 (la que más difícil parece a la vista) · Utilidad 10 · Innovación
  7 · Presentación 8. **Total 62.**
- **Fallo en directo:** la placa queda torcida en el tope y cede al apoyar las puntas. **Reproche:** «un soporte
  articulado de 30 € no se equivoca nunca».

### G2-1 · Pedido Listo — 63
- **Criterios.** Lección «maqueta / coger y dejar con historia» DUDOSO grave: cuatro cajas iguales de cuatro colores
  son cubos de colores. Crit. 3 DUDOSO (visión clásica de color). Crit. 8 DUDOSO grave: sin vendedora real. Crit. 4
  DUDOSO leve (paquetería, vecino de Flip & Ship). U1 DUDOSO (dos jabones se cogen en 3 s).
- **p = 0,70** por artículo (caja de cartón de 40 mm, depósito de varios cm; resta el stock de 12 pegadas). Demo
  21; 5/5 = 17 %. Como «pedido de dos»: 0,49.
- **Rúbrica.** Demo 21 · Datos 13 · Dificultad 8 · Utilidad 9 (Ultra es la referencia más citable) · Innovación 4 ·
  Presentación 8 (el juez se lleva el paquete). **Total 63.**
- **Fallo en directo:** coge el color equivocado. **Reproche:** «clasificador por color; lo hace una cámara y un
  PLC desde hace 20 años».

### G2-2 · Bancada — 58 · ELIMINADO
- **Criterios.** Crit. 3 FALLA en el nivel mínimo: gradillas con huecos fijos y secuencia fija traer/retirar; la
  ficha admite que el lenguaje sobra hasta N3. Crit. 2 DUDOSO grave: tubo de Ø30 mm y 115 mm de alto en un fondo de
  32 mm se acuña. Crit. 6 DUDOSO: la persona destapa líquido dentro del alcance. U6 DUDOSO (laboratorio).
- **p = 0,42** (traer 0,62 × retirar 0,68). Demo 13; 5/5 = 1 %.
- **Rúbrica.** Demo 13 · Datos 11 · Dificultad 11 · Utilidad 9 · Innovación 6 · Presentación 8. **Total 58.**
- **Fallo en directo:** tubo acuñado en el embudo. **Reproche:** «posiciones fijas: eso es un pick and place
  programado; ¿dónde está la IA?».

### G2-3 · Plantel — 58 · ELIMINADO
- **Criterios.** Crit. 2 / U3 FALLA: objeto orgánico y deformable, en la lista de «no» del apartado 6, sin probar y
  que se degrada tras 100 demostraciones. U6 DUDOSO (vivero). Parecido al sembrador que perdió. Crit. 8 DUDOSO.
- **p = 0,35.** Demo 10,5; 5/5 = 0,5 %.
- **Rúbrica.** Demo 10 · Datos 12 · Dificultad 13 · Utilidad 7 · Innovación 8 · Presentación 8. **Total 58.**
- **Fallo en directo:** roseta rota o volcada fuera del alvéolo. **Reproche:** «2.800 por hora frente a 3 por
  minuto».

### G3-1 · Tanda — 66
- **Criterios.** U2 DUDOSO: «el siguiente» no elige nada por lenguaje y las dos órdenes se distinguen por la
  escena; un ACT hace lo mismo. U1 y crit. 8 DUDOSO grave: la encuesta dice que fotografiar cuesta, no que cambiar
  el artículo estorbe; **un trípode de 15 € libera las dos manos** y deshace la premisa (la empuñadura a dos manos
  se imprime para forzarla). Apartado 4 DUDOSO: el reflector cambia la luz de la escena, causa conocida de derrota.
  Crit. 7 DUDOSO (10 h de impresión, al límite).
- **p = 0,50** (barrer 0,85 × coger objeto arbitrario y apoyarlo en el atril 0,60). Demo 15; 5/5 = 3 %.
- **Rúbrica.** Demo 15 · Datos 17 (la mejor: 20 objetos, 5 apartados, vistos frente a nuevos, cambio de luz) ·
  Dificultad 12 · Utilidad 6 · Innovación 8 · Presentación 8. **Total 66.**
- **Fallo en directo:** el artículo resbala del atril o queda de espaldas. **Reproche:** «ponga el móvil en un
  trípode y cambie el artículo con la mano: 3 segundos».

### G3-2 · Pedido — 62
- **Criterios.** Crit. 1 DUDOSO (la ficha lo admite) y lección de Repón y Pila Sabia: es el más cercano a lo ya
  rechazado. Crit. 7 DUDOSO: «pedidos elegidos por el jurado» exige 4 órdenes; con 2 el pedido es siempre el mismo.
  Crit. 2 DUDOSO: lata metálica de Ø55 mm y caja de 60 mm, en el borde de la pinza. Crit. 8 DUDOSO.
- **p = 0,46** declarado (dos referencias: 0,68²); recortado a una, 0,68. Demo 14; 5/5 = 2 %.
- **Rúbrica.** Demo 14 · Datos 16 (la matriz frase × objeto es la mejor prueba de que la red lee el texto) ·
  Dificultad 11 · Utilidad 8 · Innovación 5 (la rampa que saca el producto del brazo es la mejor idea mecánica de
  las 13) · Presentación 8. **Total 62.**
- **Fallo en directo:** la lata se escurre; segundo agarre fuera de tiempo. **Reproche:** «cuatro referencias
  conocidas: visión clásica y un script».

### G3-3 · Calibre — 56
- **Criterios.** U4 y crit. 1 DUDOSO: lote impreso por nosotros con defectos fabricados; es una celda de inspección
  en miniatura, la que este jurado dejó sin premio. U2 DUDOSO: no hay elección por lenguaje, el destino lo marca un
  LED. U1 DUDOSO: lo útil (apuntar por voz) no necesita robot. «Sin tocar» DUDOSO: la mano entra al plato.
- **p = 0,52** (granel 0,65 × plato a destino 0,80). Demo 16; 5/5 = 4 %.
- **Rúbrica.** Demo 16 · Datos 11 · Dificultad 10 · Utilidad 9 · Innovación 4 · Presentación 6. **Total 56.**
- **Fallo en directo:** dos piezas cogidas a la vez o atasco en el cajón. **Reproche:** «un pasa/no pasa o una
  cámara lo hacen sin operario; esto es más lento que hacerlo a mano».

### G4-A · Atrezzo — 65
- **Criterios.** U1 y crit. 8 DUDOSO grave: nadie pone una piña junto a lo que vende en Wallapop; necesidad
  inventada y, otra vez, el trípode. U7 DUDOSO: la ficha admite que no existe producto vendido que citar. U5 DUDOSO
  (disparar una foto es trabajo ligero). Crit. 3 DUDOSO: tres adornos conocidos.
- **p = 0,72** (1 movimiento alternando poner y despejar; resta la piña y el objeto no visto en el centro). Demo
  21,6; 5/5 = 19 %.
- **Rúbrica.** Demo 21 · Datos 15 · Dificultad 9 · Utilidad 5 · Innovación 7 · Presentación 8. **Total 65.**
- **Fallo en directo:** la maceta vuelca sobre el objeto del juez. **Reproche:** «¿qué problema industrial resuelve
  mover una piña?».

### G4-B · Kit de clase — 66
- **Criterios.** U4 PASA (piezas reales del kit, sin sustitutos impresos). Lección «coger y dejar con historia»
  DUDOSO grave. Crit. 3 DUDOSO. Crit. 8 DUDOSO (cita del foro vista solo en extracto). U1 DUDOSO: el robot pone 3
  de 15 referencias y la persona es más rápida. U6 DUDOSO leve (aula, no taller).
- **p = 0,70** (1 movimiento; objetos distintos en forma y color, el caso favorable para el texto; resta el motor
  de 22 mm pegado a otra pieza). Demo 21; 5/5 = 17 %. La escena se agota sola: 6 piezas, 5 intentos.
- **Rúbrica.** Demo 21 · Datos 15 · Dificultad 9 · Utilidad 10 · Innovación 4 · Presentación 7. **Total 66.**
- **Fallo en directo:** coge la pieza más cercana en vez de la pedida. **Reproche:** «bin picking de tres
  referencias; el profesor tarda menos que en dictar la orden».

### G4-C · Enséñamelo — 61 · ELIMINADO
- **Criterios.** Crit. 3 FALLA: un detector de objetos y cinemática lo hacen mejor, y ese es el plan B que la propia
  ficha propone. U7 FALLA: no hay ninguna empresa de physical AI que venda esto. Crit. 4 DUDOSO grave: brazo que
  apunta algo hacia donde trabaja el operario; el jurado dirá «MSN con cámara». Sin plan B con ACT.
- **p = 0,78** si la red obedece al texto (misma escena, solo cambia la frase: el riesgo conocido). Demo 23; 5/5 =
  29 %.
- **Rúbrica.** Demo 23 · Datos 13 · Dificultad 5 (no coge nada) · Utilidad 9 · Innovación 4 · Presentación 7.
  **Total 61.**
- **Fallo en directo:** va siempre al mismo aparato diga lo que diga la frase. **Reproche:** «es lo de Vitoria del
  mes pasado con una webcam».

---

## 2. Ranking

| # | Concepto | Total | p por intento | 5/5 | Movimientos por intento | Eliminación |
|---|---|---|---|---|---|---|
| 1 | G0 Aprendiz | 68 | 0,60 | 8 % | 1 | Pasa con dudas (crit. 2, 7, 8) |
| 2 | G1-A Tornillero | 66 | 0,78 | 29 % | 1 | Pasa con dudas (crit. 3) |
| 3 | G4-B Kit de clase | 66 | 0,70 | 17 % | 1 | Pasa con dudas (lección maqueta, crit. 3) |
| 4 | G3-1 Tanda | 66 | 0,50 | 3 % | 2 | Pasa con dudas (U1, U2, crit. 8) |
| 5 | G4-A Atrezzo | 65 | 0,72 | 19 % | 1 | Dudoso (U1, U7, crit. 8) |
| 6 | G2-1 Pedido Listo | 63 | 0,70 | 17 % | 1 | Dudoso (lección maqueta, crit. 3, 8) |
| 7 | G3-2 Pedido | 62 | 0,46 | 2 % | 2 | Dudoso (crit. 1, 7, 8) |
| 8 | G1-B Recambista | 62 | 0,62 | 9 % | 1 | Dudoso (crit. 8, Relevo) |
| 9 | G1-C Sondas libres | 62 | 0,45 | 2 % | 2 | Dudoso (U4, crit. 2, 4) |
| 10 | G4-C Enséñamelo | 61 | 0,78 | 29 % | 1 (sin agarre) | **Eliminado** (crit. 3, U7; crit. 4 dudoso) |
| 11 | G2-2 Bancada | 58 | 0,42 | 1 % | 2 | **Eliminado** (crit. 3; crit. 2 y 6 dudosos) |
| 12 | G2-3 Plantel | 58 | 0,35 | 0,5 % | 1 | **Eliminado** (crit. 2 / U3) |
| 13 | G3-3 Calibre | 56 | 0,52 | 4 % | 2 | Dudoso (U4, crit. 1, U2) |

Los empates a 66 se ordenan por probabilidad de 5/5 y por riesgo de rechazo del usuario.

## 3. Los tres mejores y lo que les exigiría

**Aprendiz (68).** (1) Quitar destornillador y alicates de la tarea puntuada: solo objetos de 30-50 mm y no
metálicos (vaso, carrete, bote); eso sube p a ~0,72. (2) Declarar 2 órdenes en N1, no 5. (3) Cambiar «acercar lo
que está a 30 cm» por un trabajo en el que la persona no pueda soltar: sin eso la utilidad no pasa de 8.
(4) Una cita de un técnico real el jueves; retirar la cifra del relevo generacional si no se verifica.

**Tornillero (66).** (1) Que la orden cambie el **tipo** de objeto, no solo el color (vaso frente a recambio en su
caja): sin eso es «cubos de colores» y la red puede ignorar el texto. (2) Portátil ya abierto y con 3 tornillos
como mucho: el desmontaje completo no cabe en 5 minutos. (3) Tener medida la respuesta a «alfombrilla magnética»
(el robot despeja la zona y devuelve en orden sin que el técnico mire) o quitar esa promesa. (4) Tabla de datos con
más variedad que tres vasos.

**Kit de clase (66).** (1) Llamada a una academia el jueves, con foto de su mesa. (2) Matriz frase × objeto cogido
como prueba central. (3) Rampa de salida de G3-2 para que la persona nunca entre en el brazo. (4) Decir el límite
(3 de 15 referencias) antes de que lo pregunten. Aun corregido, no lo elegiría (apartado 5).

## 4. Fusión que supera a los 13: «Aprendiz de reparación» (Aprendiz + Tornillero, con piezas de G3-2 y G4)

1. **Usuario y escena:** técnico de reparación con un portátil real ya abierto; manos dentro del aparato.
2. **Tarea completa declarada (≤ 25 s, 1 movimiento):** el técnico pide una de las cosas gruesas que están sueltas
   en la esterilla, donde las haya dejado el juez, y el robot la deja en el plato-embudo junto a su mano.
3. **Órdenes N1:** `Bring the screw cup.` y `Put the cup away.` (cambia adónde; la escena se repone sola).
4. **N2:** `Bring the spare part box.` (el SSD en su caja de 60 × 40 × 25 mm): la orden cambia **qué tipo de
   objeto**, distinto en forma y color, el caso favorable para que SmolVLA lea el texto.
5. **N3:** segundo vaso, devolución en orden inverso llevada por el LLM, y cambio de orden a mitad fuera de los 5.
6. **Los 5 intentos:** alternan traer y guardar con vaso y caja; nadie entra en el brazo; el plato queda en el
   borde del alcance y un LED marca «brazo aparcado» para que la mano entre solo entonces (preguntar al mentor).
7. **Demo:** p ≈ 0,78 → 23 puntos y 29 % de 5/5, porque vaso y caja son los objetos más fáciles de las 13 fichas
   y se eliminan destornillador, alicates y botones.
8. **Datos (16-17):** matriz frase × objeto (de G3-2), posiciones vistas frente a nuevas, ronda de corrección del
   «maestro» con el brazo guía (de G0), ACT frente a SmolVLA.
9. **Utilidad (11-12):** la única queja leída (iFixit), herramienta y aparato reales, y final que se ve: el
   portátil arranca. Frase de G0: «Faltan aprendices en los talleres. Hemos entrenado uno.»
10. **Total estimado 75-77** (demo 23, datos 16, dificultad 11, utilidad 11, innovación 6, presentación 9): 8-9
    puntos sobre el mejor concepto suelto. Sigue pendiente la cita de un técnico real y medir el viernes si la red
    obedece a la frase.

## 5. El que no elegiría aunque puntúe alto

**Kit de clase (3.º, 66)**, y con él toda la familia Pedido Listo / Pedido. Puntúa por fiabilidad, pero es
exactamente lo que el usuario ha rechazado cinco veces: partir de «coger y dejar» y ponerle una historia encima
(Repón, Pila Sabia). Tiene 4/10 en innovación ante un jurado que dejó sin premio a la celda de 692 episodios, y el
robot hace 3 de 15 referencias más despacio que la persona. Sirve como donante de mecánica (objetos distintos a la
vista, escena que se agota sola), no como proyecto.

**Enséñamelo** tiene la p más alta junto con Tornillero y tampoco: es «MSN con cámara» delante del mismo jurado, un
detector lo hace mejor y no tiene plan B con ACT.

## 6. Avisos que valen para cualquier elección

- **Las dos direcciones de fotos (Tanda y Atrezzo) dependen de que el móvil esté en las manos.** Un trípode las
  deja sin necesidad; hay que validarlo con una vendedora antes de invertir un minuto más.
- **Ninguna ficha tiene una cita de usuario sobre el gesto del robot.** El jueves hay que conseguir una, o los 15
  puntos de utilidad se quedan en 8-10 con cualquier concepto.
- **Preguntar al mentor el viernes:** si la mano de la persona puede entrar en la zona con el brazo aparcado, si la
  orden hablada cuenta como «sin tocar» y si un intento puede encadenar órdenes por programa.
- **Riesgo común sin medir:** que SmolVLA ignore la frase. Medirlo el viernes con dos objetos; si falla, todos pasan
  a «un ACT por orden y el LLM elige», y la dificultad percibida baja 2-3 puntos en todos.
