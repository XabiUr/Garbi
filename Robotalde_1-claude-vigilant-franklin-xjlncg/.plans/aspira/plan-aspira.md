# Plan · Aspira (jueves 19 → domingo 22)

Entrada: [spec-aspira.md](spec-aspira.md). Personas: **A** = Andoni (hardware), **S1** y **S2** = software. Las
tareas de software vienen de [gestion-robot.md](gestion-robot.md) §8, adaptadas a la spec (un solo cabezal: sin
`Put the nozzle back.` ni cambio de boquilla; nueva tarea «línea base programada»). Puerta antes de empezar: **«sí»
explícito del usuario a la spec**.

## Jueves 19 (sin robot)

| Hora | A (hardware) | S1 (robot y datos) | S2 (orquestación y medida) |
|---|---|---|---|
| 08:45-10:00 | Modelar mango (atornillado a la pinza, toma Ø 32-40) y cabezal 80 × 15 con labio; lanzar impresión del mango | Instalar LeRobot 0.7 en los dos portátiles; `torch.cuda.is_available()`; `lerobot-find-cameras` y captura a 640 × 480 y 30 fps | Enviar el correo a la organización (5 preguntas de la spec §7) |
| 10:00-12:30 | Compra: aspiradora de red, manguera Ø 32-40 ligera, poste, polea, contrapeso, listón de pino, pintura negra mate, cartulinas, báscula de 0,01 g, gafas y FFP2 | `robot/comandos.sh` (1 h) y `aspira/grabar.py` (1,5 h) | `aspira/puente.py` con tubería falsa (3 h): máquina de estados N1, reintento, `/reset` como parada, nunca cerrar stdin |
| 12:30-13:30 | Imprimir cabezal (2 copias) y soporte de la cámara fija | Ensayo de la nube: 200 pasos de SmolVLA y ACT en HF Jobs, carga local, latencia con observaciones sintéticas | (sigue) |
| 13:30-16:00 | Pintar la tabla de negro; montar poste, polea y contrapeso; cortar 20 piezas de pino | Voz: vocabulario nuevo en `contrato.ORDENES` y botones (1 h) | `aspira/vigilante.py` (2,5 h): marca roja y cabezal azul en la cámara fija, 35 ± 10 mm, zona prohibida |
| 16:00-18:00 | **Pruebas físicas:** captación del cabezal con la aspiradora encendida a 25, 35 y 50 mm; fuerza del tubo con la aspiradora encendida; par en la pinza con el contrapeso | Línea base programada: color + cinemática inversa (`sim/cinematica.py`) que siempre se pone en el mismo lado (1,5 h) | Medida: CSV X/10, matriz frase × postura, % de polvo en la foto (1,5 h) |
| 18:00-20:00 | **Apaño honrado:** taladrar 5 agujeros en la mitad izquierda de una tabla negra recolocando un tubo fijo a mano; foto, pesada y contar las veces que se suelta la herramienta | Fin por sonido (opcional, 1 h) | Pantalla «hoja de proceso» en la tablet (orden activa, Listo, contador) |
| 20:00 | Empaquetar con la lista de hardware.md §7 | Revisar respuestas de la organización | Revisar |

**Puerta del jueves 20:00:** captación medida a 35 mm claramente mejor que a 150 mm (si no, rediseñar el cabezal);
tubo que no tira más de lo que aguanta el hombro (si no, más contrapeso o trabajar más cerca); respuesta de la
organización o plan B de polvo decidido (spec §7).

## Viernes 20 (agenda oficial 18:00-21:00; noche opcional)

| Hora | Hito | Puerta |
|---|---|---|
| 17:45 | Mentor: rúbrica, formato de los 5 intentos, permiso de polvo y ruido, hardware propio | Decide la tabla de la spec §7 |
| 18:00-19:30 | Montaje, calibración, cámaras, foto de referencia de cada cámara; `/reset` desde postura baja no barre la pieza; valor de `max_relative_target`; 10 colocaciones por teleoperación | < 8/10 colocaciones → mover la tabla más cerca del eje |
| 19:30-21:30 | Grabar `Help me drill at the mark.` (60) | 21:00 < 30 válidos → solo taladrar |
| 21:30 * | Ciclo 0: SmolVLA en HF Jobs + ACT de taladrar en la 1660 | — |

## Sábado 21 (9:30-21:00)

| Hora | Hito | Puerta |
|---|---|---|
| 9:30-10:30 | Prueba: X/10 de taladrar con marcas y manos en sitios nuevos; línea base programada al lado | SmolVLA ≥ 8/10 → rama A · ACT ≥ 8/10 → B · los dos < 6/10 → C |
| 10:30-12:30 | Grabar cantos (35 + 35) y atornillar (15-20) | — |
| 12:30 | Ciclo 1 (todas las órdenes) | — |
| 13:00-14:30 | Medida con y sin Aspira (tandas alternas de 5 agujeros); vídeo de 1 minuto | — |
| 14:30-15:45 | Grabar correcciones desde donde falló | — |
| 15:45 | Ciclo 2 (último) | — |
| 16:00-17:20 | Serie de 10 por orden y matriz frase × postura | Decide modelo y rama |
| 17:20-19:00 | Dos ensayos completos de la demo con cronómetro; N3 (seguir la lijadora) solo si todo lo anterior está verde | — |
| 19:00-20:40 | Comparativa con el ciclo 2; tabla de medidas y pantallas | Ciclo 2 sustituye al 1 solo si mide igual o mejor |
| 21:00 | **Montaje congelado** | — |

## Domingo 22

| Hora | Hito |
|---|---|
| 9:30-10:00 | Serie de 5 completa; declarar solo lo que salió (≤ 3/5 → zonas buenas; ≤ 1/5 → vídeo y medidas) |
| 10:00-11:00 | Dataset y modelo en el Hub, README reproducible, cinco diapositivas, vídeo de 1 minuto |
| 11:00 | Entrega |

## Lo que no se hace (recortado)

Cambio de cabezal y `Put the nozzle back.`; lijadora eléctrica en la nota; caladora, Dremel y fresadora;
`dagger`; electrónica nueva; personaje y estética arcade.
