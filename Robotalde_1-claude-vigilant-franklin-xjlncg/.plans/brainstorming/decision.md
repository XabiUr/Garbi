# Brainstorming · fase 4: decisión (18-11-2026)

Proceso: contexto abstracto sin sesgo → 15 ideas de tres generadores independientes + LeWelder → filtro global →
consejo de tres voces (método `council` de ecc, aplicado a mano). Material en esta carpeta.

## Lo que dijo el consejo

| Voz | Elección | Confianza |
|---|---|---|
| Moderador (antes de leer al consejo) | Pañol | — |
| Pragmática | Pañol recortado (3 objetos, solo traer) | 7/10 |
| Crítica | Pañol + el juez cambia el módulo de una minimáquina | 7/10 |
| Escéptica | Relevo simplificado (sin contacto eléctrico, módulos distintos, sensores) | 6/10 |

**Coinciden las tres** en: descartar LeWelder (tema quemado, VLA invisible, montaje poco fiable) y ManoLibre
(seguridad e higiene, VLA casi invisible); un taller de **mantenimiento**; 3 objetos gruesos de forma y color
distintos; 2-3 órdenes de coger y dejar con tolerancia; verificación por sensor con reintento narrado; tasa de
aciertos medida; ACT de respaldo; voz e inferencia sin depender de la wifi.

**Discrepan** en quién mete el módulo en la máquina: el robot (más memorable, más riesgo) o el juez (más seguro).
Se resuelve con una prueba física el jueves (ver puerta 1).

## La solución: **Relevo**, taller de mantenimiento (nombre provisional)

> **"La máquina se para. Dile qué ha pasado y el robot trae el repuesto correcto y la vuelve a poner en marcha."**

### La demo

1. Una minimáquina impresa funciona: cinta o ventilador, LED verdes, sonido.
2. **El juez la avería:** arranca uno de sus tres módulos (fusible, relé o batería). La máquina se para, el hueco se
   pone en rojo.
3. El juez lo dice con sus palabras ("se ha parado la cinta", "ha saltado algo"). El personaje responde; el LLM
   traduce a una orden cerrada y la tablet la muestra: **"Coloca el relé"**.
4. **SmolVLA** coge el repuesto correcto de la bandeja (tres objetos distintos en la misma escena, elegidos por la
   frase) y lo deja en su hueco-embudo imantado.
5. El sensor del hueco lo confirma → **la máquina vuelve a arrancar**. Si no encaja, el robot lo reintenta y el
   personaje lo narra ("se me ha escurrido, otra vez").
6. Segundo juez, otra avería, el mismo modelo. En pantalla: la frase que recibe el VLA y la **tasa de aciertos medida**.

### Por qué esta y no las demás

- **VLA visible:** una sola red elige entre tres objetos distintos por lenguaje, lo que SmolVLA hace bien.
- **Final que se ve** (la máquina vuelve a funcionar) y **juez en el centro** (provoca la avería).
- **Fiable:** coger y dejar con embudos e imanes; sensores que dan estados, reintento y aciertos sin visión frágil.
- **Tema fresco e industrial** (Bilbao); lejos de la soldadura de MSN y del camarero.
- **Reutiliza el software hecho:** voz → LLM → vocabulario cerrado, tablet arcade, personaje, ESP32, flujo de LeRobot.

### Órdenes del VLA

| Nivel | Órdenes | Episodios |
|---|---|---|
| 1 (sábado 12:00) | `place the relay` con ACT o SmolVLA | ~50 |
| 2 (sábado 20:00) | `place the relay` · `place the fuse` · `place the battery` (SmolVLA) | ~150 + 20-30 de recuperación |
| 3 (domingo, si sobra) | `remove the broken module` (el robot también lo saca, a una caja de reciclaje) | ~50 |

Frases en inglés fijas en el dataset; el LLM traduce lo que diga el juez.

### Puertas de decisión

1. **Jueves (sin robot):** imprimir un hueco-embudo imantado y un módulo; soltarlo a mano 30 veces con desvíos de
   ±1-1,5 cm y algo de giro. **≥ 90 % encaja → el robot lo mete en la máquina.** Si no → el robot deja el repuesto en
   una bandeja de entrega y **el juez** lo mete (Pañol + cierre humano); mismas piezas, mismo flujo.
2. **Viernes 21:00:** calibrado, cámaras fijas, 50 episodios de la primera orden y entrenamiento lanzado.
3. **Sábado 12:00:** nivel 1 funcionando en el robot.
4. **Sábado 20:00:** SmolVLA ≥ 70 % en al menos 2 de 3 repuestos → plan A. Si no → plan B: un ACT por repuesto,
   elegido por el LLM. Plan C: un repuesto en vivo y el resto en vídeo con su tasa medida.

### Preparación miércoles-jueves

- **Andoni (CAD e impresión):** minimáquina con 3 huecos-embudo e imanes y sensor Hall o reed por hueco (ESP32),
  LED por hueco y motor o ventilador; 3 módulos de forma y color muy distintos con asa ≥ 20 mm; bandeja de
  repuestos con alojamientos-embudo; soportes fijos de cámaras; repuestos de todo.
- **Software (Claude y el equipo):** firmware del ESP32 (sensores, LED, motor, por USB); selector (LLM → orden →
  política → comprobar sensor → reintentar); pantallas de la tablet (máquina, avería, orden, aciertos) sobre el motor
  arcade; script de evaluación X/10; escena en MuJoCo para probar el selector en seco; recolector programado opcional.
- **Comprobar:** PyTorch con CUDA en el portátil y latencia de SmolVLA en la GTX 1660 (`--inference.type=rtc`).

### Qué pasa con LeWelder

Se aparca. Se reutiliza su software (tablet, voz, personaje, ESP32, flujo de entrenamiento) y lo aprendido. El CAD
de soldadura y la antorcha quedan fuera.

### Riesgos que quedan

- **Dificultad percibida media:** se compensa con el LLM que entiende la avería, la recuperación a la vista y los
  números medidos.
- **Tolerancia del embudo:** la puerta 1 lo resuelve antes del viernes.
- **Información del hackathon pendiente:** si los criterios cambian mucho, se revisa esta decisión.

Siguiente paso, con el sí del usuario: spec v3 corta y plan (fase 3), y encargar las piezas a Andoni hoy.
