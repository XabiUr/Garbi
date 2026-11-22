# Garbi · plan de todo lo que no es la demo (vie 20 noche → dom 22, 11:00)

Equipo Robotalde · Hackathon LeRobot Bilbao II. Escrito el viernes 20-11 por la noche.

> **Regla de oro:** la entrega se fabrica **mientras** se construye. Cada hito deja una foto, un clip o un número.
> El domingo por la mañana solo se monta lo que ya existe.

## 0. Cómo se puntúa (rúbrica oficial, guía SO-101 del 17-11)

Fuente: https://hackathonbilbao.eus/guia-so-101, resumida en `investigacion/guia_so101/RESUMEN.md` (rama `main-9d41os`).

| Criterio | Pts | ¿Depende de la demo? | Qué hacemos fuera de la demo para sacarlo entero |
|---|---|---|---|
| Demo en vivo (5 intentos × 6) | 30 | Sí | Guion de 3 min, checklist, montaje congelado (sección 7) |
| **Datos y entrenamiento** | **20** | **No** | Registro de episodios y descartes, **dos iteraciones** documentadas, variedad, cámaras (sección 2) |
| Dificultad de la tarea | 15 | En parte | Enseñar que tolera cambios: madera movida, luz, recuperaciones (prueba grabada) |
| Utilidad e impacto | 15 | No | Problema real con dato: el polvo de madera (sección 3) |
| Innovación e ingenio | 10 | No | Contarlo bien: robot que **colabora** con una persona y su herramienta, híbrido percepción + ACT con guardias |
| Presentación y equipo | 10 | No | Pitch ensayado + preguntas preparadas |
| **Bonus** dataset en HF | +3 | No | Dataset **público** con ficha. Gratis: no dejarlo escapar |
| **Bonus** repo reproducible | +2 | No | README con comandos que funcionan; `garbi.correr --sim` sin robot |

**70 de los 105 puntos no son la demo.** De esos, 20 + 5 son casi mecánicos si se hace el trabajo de registro.

**Entregables oficiales:** (1) **vídeo de 1 minuto**; (2) **presentación en vivo de 3 minutos** ante el jurado; y,
según la web, al cierre de las 11:00: presentación, dataset y código.

**Preguntar esta noche a los mentores de Bravo Robots / organización (WhatsApp del evento):**
1. La web dice "5 minutos por equipo" y la guía "3 minutos": ¿cuál vale? ¿**Los 5 intentos van dentro** de ese tiempo
   o la demo de 5 intentos es aparte, en la mesa?
2. ¿Dónde se entregan vídeo, presentación, dataset y repo (formulario, enlace)? ¿Formato del vídeo?
3. ¿El jurado viene a nuestra mesa o llevamos el robot a un escenario? (cambia luz y calibración: crítico)
4. ¿Proyector/pantalla para el vídeo o diapositivas durante los 3 min?
5. ¿Hay créditos de HF Jobs del hackathon?

## 1. Entregables

| # | Entregable | Dónde | Dueño | Listo |
|---|---|---|---|---|
| E1 | **Vídeo de 1 min** (oficial) | YouTube no listado + archivo local | Comunicación | Sáb 23:59 v1 · dom 09:30 final |
| E2 | **Dataset real público** con ficha (+3) | `Izaguirre97/garbi_acercamiento` | Robot | Tras cada sesión de grabación; ficha final dom 09:00 |
| E3 | **Modelo(s) ACT** públicos con ficha y tabla de evaluación | `Izaguirre97/act_garbi_v1`, `_v2` | Robot | Sáb noche |
| E4 | **Repo reproducible** (+2): README de escaparate, `main` al día | GitHub | Claude + Comunicación | Dom 10:00 |
| E5 | **Registro de datos y entrenamiento** (para los 20 pts) | `docs/datos-y-entrenamiento.md` + diapositiva | Robot + Claude | Se rellena en vivo |
| E6 | Presentación (5-6 diapositivas o pantalla de apoyo) + PDF | Repo + entrega | Comunicación | Dom 09:00 |
| E7 | Guion de los 3 min + 12 preguntas con respuesta | `docs/pitch.md` | Todos | Sáb 23:00 |
| E8 | Checklist y guion de la demo en vivo, planes B y C | `docs/demo-en-vivo.md` | Andoni + Robot | Sáb 23:00 |

Entregar a las **10:30**, no a las 10:59. Código congelado a las 10:00.

## 2. Datos y entrenamiento (20 pts): lo que hay que FORZAR

El jurado **va a preguntar** cuántos episodios grabasteis, cuántos descartasteis y qué cambiasteis tras el primer
entrenamiento. Hay que tener la respuesta en una diapositiva y en el README, con números.

1. **Dos iteraciones de verdad, aunque la primera sea pequeña.** Primer entrenamiento corto lo antes posible
   (sábado ~11:00, con 20-30 episodios y 10k pasos), probarlo, **apuntar cómo falla**, grabar esos casos y entrenar
   la v2. Sin v1 no hay historia de "qué cambiamos". Es lo que más puntos da por hora de trabajo.
2. **Registro automático de episodios.** El grabador ya guarda guardados, descartados y motivos en
   `datos/garbi_acercamiento/episodios_garbi_acercamiento.json`. Claude hace un script que lo convierte en la tabla
   de E5 (episodios por sesión, descartes por motivo, posiciones, luz, recuperaciones).
3. **Variedad planificada y contada:** posiciones del agujero repartidas por la zona (cuadrícula marcada con cinta),
   madera girada y movida, dos luces (con y sin flexo), recuperaciones (broca que cambia de sitio a mitad, mano que se
   cruza). Una línea por tanda en la bitácora.
4. **Cámaras y encuadre:** foto de cada cámara (`top`, `wrist`) y de su soporte, fijo y marcado con cinta. Va al
   README y a la ficha: lo valoran explícitamente.
5. **Curva de evaluación:** misma prueba de 10 ciclos con v1 y con v2 (`lerobot-rollout --strategy.type=episodic` o
   el contador de `garbi.correr`), con vídeo. Tabla: aciertos, toques, tiempo por ciclo. ACT frente al respaldo
   programado también entra (honestidad = credibilidad).
6. **DAgger si sobra tiempo** (`--strategy.type=dagger`): una tanda de correcciones el sábado por la noche o el
   domingo temprano es una frase muy potente para este criterio ("corregimos sus fallos en vivo con el leader").
7. **Simulación como iteración previa:** el dataset y el ACT entrenados en simulación cuentan como trabajo de
   preparación (subirlos marcados como `sim`): enseñan método.

## 3. Utilidad (15) e innovación (10): el relato

- **Problema:** taladrar y lijar madera genera polvo fino que se respira; el polvo de madera está clasificado como
  cancerígeno para humanos (IARC, grupo 1) y la normativa europea limita la exposición en el trabajo. Las aspiradoras
  de taller se quedan lejos de la broca porque estorban. Usuarios: maquetistas, talleres escolares, carpintería
  pequeña, makers. (Verificar la cifra exacta antes de ponerla en la diapositiva.)
- **Solución en una frase:** "Garbi es un compañero de banco que acerca la aspiración a tu broca cuando taladras, se
  aparta cuando terminas y limpia lo que queda."
- **Lo innovador:** el robot no repite una tarea sola: **reacciona a una persona con una herramienta en la mano**
  (colaboración humano-robot), con percepción de manos y taladro, ACT para el acercamiento fino y guardias de
  seguridad por encima del modelo.
- **Dificultad:** tarea de varios pasos, con una persona moviéndose, la madera en posiciones nuevas y recuperaciones.

## 3 bis. Producto e industrialización (enfoque del equipo, 21-11)

**Mensaje:** Garbi no es una demo de laboratorio. Es un **producto**: un módulo de extracción de polvo colaborativo
que se pone junto a cualquier puesto de taladrado manual. Ya funciona con un brazo de 200 €, y el mismo software
escala a un cobot industrial. **El equipo trabaja en fábricas y entornos industriales**, y además es maker en casa:
conocemos los dos usuarios.

| | Garbi Taller (hogar, maker, escuela) | Garbi Fábrica (puesto de trabajo industrial) |
|---|---|---|
| Problema | Polvo en casa o en el aula; la aspiradora estorba y nadie la acerca a la broca | Exposición al polvo de madera en puestos manuales; el polvo de maderas duras es cancerígeno y tiene límite legal de exposición en la UE (verificar la cifra antes de la diapositiva) |
| Qué hace | Acompaña al taladro, aspira en la broca y limpia la tabla y el tapete al terminar | Lo mismo, con trazabilidad: indicadores por turno y registro exportable |
| Hardware | SO-101, una webcam, un relé y la aspiradora que ya tienes | Cobot industrial y extracción centralizada; la misma lógica y la misma política re-entrenada |
| Interfaz | App sencilla, órdenes por chat o voz, seta | Igual, en modo Fábrica: indicadores primero y registro tipo MES |
| Seguridad | Guardias de distancia a la mano y al taladro, seta | Además, monitorización de velocidad y separación como en las normas de robots colaborativos (ISO/TS 15066) |

**Camino a la industrialización (diapositiva final):**
1. **Hoy:** prototipo funcional con varias tecnologías trabajando juntas:
   - visión clásica (círculo morado, tabla, tapete);
   - MediaPipe para las manos;
   - ACT entrenado con un dataset propio de 200 pasadas;
   - máquina de estados con guardias;
   - app con LLM;
   - seta y Arduino.
2. **Piloto:** un puesto de taladrado real en una de nuestras fábricas, midiendo polvo antes y después con un
   medidor de partículas.
3. **Producto:** kit de montaje para cobots comerciales, entrenamiento por puesto en una hora (el propio robot graba
   su dataset, como hemos hecho aquí) y licencia del software.

**Frase de cierre:** «Garbi lleva la aspiración a la broca, no la broca a la aspiración. Hoy en un banco de taller;
mañana en cada puesto manual de una fábrica».

## 4. Vídeo de 1 minuto (E1, oficial)

Guion (60 s, con subtítulos: el jurado puede verlo sin sonido):

| s | Plano | Texto en pantalla |
|---|---|---|
| 0-4 | Broca entrando con Garbi aspirando al lado, plano cerrado | "Taladras. Garbi aspira." |
| 4-10 | Nube de polvo sin Garbi (contraplano) | "El polvo de madera es cancerígeno (IARC grupo 1)" |
| 10-35 | Ciclo completo en plano general: coge taladro → prudente → acercamiento ACT → retirada → limpieza | Rótulos cortos de cada estado |
| 35-43 | Recuperación: la madera se mueve / la broca cambia de sitio y Garbi se adapta | "Se adapta en tiempo real" |
| 43-53 | Teleoperación grabando + visor del dataset + tabla v1 → v2 | "N episodios · 2 iteraciones · X/10" |
| 53-60 | Equipo + logos LeRobot/HF + QR al repo | "Garbi · Robotalde" |

Tomas que hay que conseguir (ir tachando en la carpeta compartida):
- [ ] **Timelapse de todo el fin de semana** (móvil en trípode con cargador, desde esta noche)
- [ ] Plano cerrado de la boca junto a la broca, con polvo visible (luz lateral)
- [ ] Plano general del ciclo completo, desde el ángulo del jurado
- [ ] Contraplano: taladrar sin Garbi y la nube de polvo
- [ ] Recuperación (madera movida, broca que cambia de punto)
- [ ] Teleoperación con el leader grabando
- [ ] Capturas de pantalla: percepción (manos, taladro), visor del dataset, curva de entrenamiento de HF Jobs
- [ ] Hardware propio: CAD de la boquilla → pieza impresa → montada; Arduino con el relé
- [ ] Un fallo gracioso para el cierre o las redes

Montaje: Claude hace un primer corte con `ffmpeg` (cortes, rótulos, velocidad, subtítulos) a partir de los clips y de
`python -m garbi.video --vision` para planos de simulación si falta algo; el retoque final, en CapCut o DaVinci.
Exportar 1080p, < 100 MB.

## 5. Presentación de 3 minutos (E6, E7)

Si los 5 intentos van dentro de los 3 min: **se habla mientras Garbi trabaja**. Cada ciclo dura ~30 s, así que el
discurso se reparte por ciclos:

| Ciclo | Mientras Garbi trabaja, quien presenta dice |
|---|---|
| Antes (15 s) | Gancho + problema: polvo de madera, cancerígeno, la aspiración siempre lejos |
| 1 | Qué hace Garbi y por qué es colaboración: reacciona a ti y a tu taladro |
| 2 | Cómo: percepción de manos y taladro (fijo) + **ACT** para el acercamiento + guardias |
| 3 | **Datos:** N episodios, M descartados y por qué, qué cambiamos de v1 a v2, X/10 medido |
| 4 | Dificultad: la madera se mueve, otra posición, recuperación (si el jurado quiere, que mueva la madera) |
| 5 | Impacto y siguiente paso; dataset y repo abiertos (bonus) |
| Cierre (10 s) | Frase final + QR |

Si la demo va aparte, el mismo contenido en 5-6 diapositivas con el número clave en grande. Ensayar **tres veces
con cronómetro** (sáb 23:00, dom 08:30, dom 11:00); quien habla no opera el robot ni taladra.

**Preguntas probables (respuesta de 20 s cada una, en `docs/pitch.md`):**
1. ¿Cuántos episodios grabasteis y cuántos descartasteis? ¿Por qué?
2. ¿Qué cambiasteis después del primer entrenamiento?
3. ¿Qué parte es aprendida (ACT) y qué parte programada? ¿Por qué así?
4. ¿Por qué ACT y no SmolVLA?
5. ¿Cuántos pasos, cuánto tiempo y en qué GPU entrenasteis?
6. ¿Qué pasa si cambia la luz o mueves la madera?
7. ¿Cómo garantizáis que no golpea la mano ni el taladro? (guardias, holgura, velocidad)
8. ¿Qué tasa de acierto tenéis medida y cómo la medisteis?
9. ¿Qué hicisteis antes del hackathon y qué aquí? (simulación, CAD y software antes; dataset y modelo reales aquí)
10. ¿Quién lo usaría y cuánto costaría?
11. ¿Lo más difícil que resolvisteis?
12. ¿Qué haríais con una semana más?

## 6. Hub y repo (E2, E3, E4: bonus +5)

- **Dataset público** `Izaguirre97/garbi_acercamiento`: ficha con tarea, nº de episodios y descartes, cámaras y
  resolución, fps, cómo se grabó (dos personas: taladro + leader), variedad (posiciones, luz, recuperaciones),
  licencia Apache-2.0, enlace al visor `lerobot/visualize_dataset` y al repo. Etiquetas `LeRobot`, `so101`.
  **Subir después de cada sesión** (copia de seguridad).
- **Modelos** públicos con ficha: dataset, pasos, lote, GPU, tiempo, tabla de evaluación, limitaciones, comando de
  `lerobot-rollout`.
- **README raíz de escaparate** (hoy no hay README en la raíz): título + frase + GIF de 5 s + enlaces (vídeo,
  dataset, modelo); qué hace; resultados; arquitectura (percepción → estados → ACT → guardias → Arduino); hardware
  (boquilla, soporte de manguera, Arduino con relé, fotos y STL); **reproducir** en tres niveles: (a) simulación sin
  robot `python -m garbi.correr --sim`, (b) grabar/entrenar/ejecutar con la guía `docs/garbi-guia-hackathon.md`,
  (c) evaluar; lo hecho antes y durante; equipo y licencias.
- Limpieza: `main` al día con esta rama; `CLAUDE.md` todavía dice LeWelder (actualizar a Garbi); repo público si lo
  piden; **anular el token de HF** pegado en el chat el 16-11; revisar que no haya secretos en el historial.
- Probar el README en limpio: clonar en otra carpeta, instalar y lanzar la simulación. Si funciona, el +2 es seguro.

## 7. Demo en vivo (E8, resumen)

- Montaje congelado el sábado a las 22:00: cámaras y tapete con cinta, luz fija (flexo propio), cables etiquetados
  (5 V leader, 12 V follower).
- Checklist de 10 min antes: robot calibrado, cámaras en su sitio, `calib/` cargada, modelo bueno descargado en local
  (sin internet), aspiradora y Arduino probados, una prueba en seco, vídeo de reserva abierto.
- Plan B: el respaldo programado del acercamiento (ya existe). Plan C: vídeo de la toma buena con la tabla medida.
- "Fallo ajeno al modelo se puede repetir una vez": saber decirlo con calma si se suelta un cable.
- Ensayar los 5 intentos seguidos **tres veces** el sábado por la noche y apuntar X/5 en la bitácora.

## 8. Calendario

Sigue el plan de la organización: viernes, flujo de punta a punta; sábado, dataset bueno y entrenar pronto;
domingo, probar y grabar los fallos.

| Cuándo | Robot | Entrega (lo que sale de ahí) |
|---|---|---|
| **Vie hasta 01:00** | Calibrar, cámaras fijas, prueba del robot y la aspiradora, 5-10 episodios de prueba y subida al Hub | **Timelapse puesto** · carpeta de fotos · `docs/bitacora.md` empezada · preguntas a la organización · token anulado |
| **Sáb 09:30-11:00** | 20-30 episodios buenos → **entrenar v1** (10k pasos) | Dataset al Hub · fotos de cámaras y soportes · README esqueleto y script de la tabla de datos (Claude) |
| **Sáb 11:00-14:00** | Más episodios con variedad y recuperaciones mientras v1 entrena | Planos de teleoperación y de hardware para el vídeo |
| **Sáb 14:00-16:00** | **Probar v1, 10 ciclos grabados**, apuntar fallos | Tabla v1 · lista de "qué cambiamos" |
| **Sáb 16:00-20:00** | Grabar los casos que fallan → **entrenar v2** (30k pasos) | Fichas del dataset y del modelo · borrador del pitch y preguntas |
| **Sáb 20:00-23:00** | Probar v2, **10 ciclos grabados**, prueba de luz y madera movida, **toma buena** del vídeo, 3 ensayos de 5 intentos | Tabla v1 → v2 · ensayo 1 del pitch |
| **Sáb 23:00-01:00** | (DAgger opcional) | **Vídeo v1** · README con resultados · dormir al menos 6 h en turnos |
| **Dom 08:00-10:00** | Prueba en frío, grabar los fallos que salgan | Ensayo 2 · vídeo final · diapositivas finales |
| **Dom 10:00** | **Congelar** | Solo README y PDF |
| **Dom 10:30** | — | **Entregar** y abrir todos los enlaces en una ventana de incógnito |
| **Dom 11:00** | Montaje listo, checklist | Ensayo 3 |

## 9. Reparto

- **Robot** (software 1): grabar, entrenar, evaluar. Dueño de E2, E3, E5.
- **Comunicación** (software 2): fotos, vídeo, presentación, README; desde el sábado a las 14:00, a tiempo completo.
  Presenta. Dueño de E1, E4, E6.
- **Andoni:** montaje, fiabilidad, Arduino y aspiradora, fotos del hardware; taladra en la demo. Dueño de E8.
- **Claude:** README, fichas del Hub, script de la tabla de datos desde el JSON del grabador, bitácora → "48 h en
  números", guion y preguntas, primer corte del vídeo con `ffmpeg`, prueba del README en limpio.

## 10. Comprobación final (domingo 10:30)

- [ ] Vídeo de 1 min entregado y en local en el portátil
- [ ] Dataset **público** con ficha y abre en el visor
- [ ] Modelo público con ficha y tabla de evaluación
- [ ] README: GIF, resultados, datos (episodios, descartes, v1 → v2), cómo reproducir; probado en limpio
- [ ] `main` al día; repo accesible para el jurado; ningún secreto; token de HF anulado
- [ ] Respuestas a las 12 preguntas ensayadas; presentación < 3:00 en el último ensayo
- [ ] Entrega con el nombre de equipo exacto
