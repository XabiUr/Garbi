# Contexto para decidir la dirección de la demo (18-11-2026)

Resumen de todo lo que sabemos. Es la única entrada de las voces del consejo.

## El evento

- Hackathon LeRobot Bilbao II · 20-22 nov 2026 (viernes tarde → domingo 11:00) · 48 h · ~140 participantes.
- Entrega: presentación, dataset (Hugging Face) y código. Pitch de 5 min + demo en vivo ante jurado.
- Premios 2025: Mejor Proyecto, Más Innovador, Impacto Social. Criterios 2026 no publicados; la organización y el
  jurado quieren ver un VLA. Más información pendiente.
- Material por equipo: 1 par SO-101 (guía + seguidor), 1 cámara, 1 trípode. SO-101 extra solo si sobran. Setup propio
  permitido. No hay impresoras. Wifi compartida (riesgo).

## El equipo

- 3 personas: dos de software/IA sin experiencia en LeRobot; Andoni (producto, CAD SolidWorks, impresión 3D,
  electrónica). **No hay robot real antes del viernes.** No se trabaja de noche.
- Portátil con GTX 1660 6 GB (Windows). Nube: HF Jobs con GPU L4 probada.

## Lo que ya existe (hecho en simulación, 369 tests)

- Escuela de soldadura "arcade": tablet con estética de plano (blueprint), gemelo 3D, puntos, combos, ranking,
  sonido, personaje del robot ("Chispas") con voz; voz → LLM → orden de vocabulario cerrado con respaldo por reglas.
- Métricas de soldadura del alumno: cobertura, velocidad, desvío, ángulo (IMU), "gatillo + apoyo"; fantasma del maestro.
- Antorcha del alumno: ESP32 + gatillo + IMU + LED, seguida por 2 webcams en estéreo (no probado con cámaras reales;
  riesgos: exposición manual, LED tapado, apoyo < 2 mm por visión → propuesta de punta con muelle).
- Reconocimiento 3D de juntas (T, esquina) por ArUco en cada chapa.
- CAD v2 validado en MuJoCo: base fija + chapa móvil con aleta e imanes (T y esquina), antorcha del robot con mango y
  soporte. Montaje programado 10/10 en simulación.
- Simulador web de la demo completa; flujo grabar → entrenar → evaluar practicado en simulación.
- Políticas: ninguna funciona aún (ACT y SmolVLA entrenados poco en CPU); solo replay.

## Lo que sabemos de las políticas (lecturas)

- Política aprendida = red que imita demostraciones. ACT: sin lenguaje, un modelo por tarea, ligero, buena
  precisión. VLA (SmolVLA): recibe una frase, un modelo para varias tareas, preentrenado con datos de SO-100/101.
- SmolVLA: ~50 episodios por tarea (25 fue malo); frases cortas en inglés con verbo; entrenar pide 10-16 GB → nube
  (batch 64, 20k pasos, 3-6 h en L4); inferencia ~2 GB (cabe en la 1660, latencia sin medir). Cambiar de orden en
  vivo sin recargar (`lerobot-rollout --interactive`, `/subtask`).
- Debilidades VLA: precisión fina, tareas largas de una orden, órdenes que solo se distinguen por la frase con la
  misma escena (no probado en la literatura).
- Imitación no demuestra ±5 mm repetibles siguiendo trayectorias → soldar con el robot = replay o programado.
- Recolector programado (cinemática + ArUco + aleatoriedad, ejemplo oficial `record_grab.py`) puede grabar solo;
  sus demos son fáciles de imitar pero no enseñan recuperaciones → añadir perturbaciones y algo de teleoperación.
  Exige calibración cámara-robot, detección de fallos y vigilar la temperatura de los motores.
- Plan temporal realista: viernes calibrar y grabar; sábado de día recoger + entrenar (1-2 vueltas); sábado 20:00
  decidir; domingo ensayar.

## Lo que sabemos de los ganadores (37 proyectos analizados)

- En hackathons LeRobot el ganador siempre tuvo una política aprendida; la mitad de los recientes usa VLA.
- Arquitectura ganadora: selector programado + varias habilidades aprendidas cortas (Flip & Ship: 3 SmolVLA;
  GreatAkihabara: chatbot → SmolVLA multitarea por texto → empaquetar donuts; Conecta 4: SmolVLA con 5 tareas).
- Lo que puntúa: funciona en vivo y **se recupera a la vista**; tasa de aciertos medida (X/10); se entiende en 5 s;
  humano en el centro; algo físico propio pequeño; capa de vida (voz, personaje); estados visibles en la escena.
- Ganó Robotekin (Vitoria, hace un mes) MSN: asistente de soldadura que alumbra con una linterna y esquiva la mano
  (54 episodios, 1 ACT + control visual programado). **Precedente directo de tema.** El camarero está quemado.
- La emoción da los likes; la evidencia da la nota. Curar datos > cambiar algoritmo.

## Rúbrica de trabajo (supuesta)

Funciona en vivo y se recupera 30 % · Dificultad técnica 20 % · Utilidad práctica 20 % · Creatividad y momento
memorable 15 % · Facilidad de uso y presentación 15 %.

Filtro de 7 puntos: (1) una habilidad central al 80 % con 50-80 episodios en montaje fijo; (2) parece difícil;
(3) se entiende en 5 s con humano en el centro; (4) recuperación planificada; (5) capa de vida quitable;
(6) algo físico propio; (7) escalera de alcance.

Principio del equipo: **es más importante no perder que ganar.**
