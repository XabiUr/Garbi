# Contexto abstracto para generar ideas (sin sesgo hacia ninguna idea previa)

## El evento

- Hackathon de LeRobot en Bilbao · 20-22 nov 2026 · 48 h (viernes tarde → domingo 11:00) · ~140 participantes de
  18-35 años.
- Entrega: presentación, dataset en Hugging Face y código. Pitch de 5 min + demo en vivo ante jurado.
- Premios del año pasado: Mejor Proyecto, Más Innovador, Impacto Social. La organización y el jurado quieren ver un
  modelo VLA (visión-lenguaje-acción).
- Material por equipo: 1 par de brazos SO-101 (guía para teleoperar + seguidor), 1 cámara, 1 trípode. Brazos extra
  solo si sobran. Se puede traer material propio. Wifi compartida (poco fiable).

## El equipo y sus capacidades

- 3 personas: dos de software/IA (Python, web, LLM, visión por computador) sin experiencia previa en LeRobot; una de
  producto con CAD (SolidWorks), impresión 3D y electrónica (ESP32, sensores, LED, IMU).
- Pueden traer impreso todo lo que diseñen antes del jueves 19 (piezas, soportes, objetos, pinzas, tableros).
- Ya tienen, reutilizable para cualquier tema: motor de interfaz web para tablet con estética de juego arcade
  (puntos, combos, ranking, sonido, personaje con voz); voz → LLM → orden de un vocabulario cerrado; visión con
  marcadores ArUco y estéreo con dos webcams; periféricos con ESP32 por USB; simulación MuJoCo del SO-101 y flujo
  grabar → entrenar → evaluar practicado.
- Sin robot real hasta el viernes. Portátil con GPU modesta (6 GB); entrenamiento en la nube (GPU L4). No trabajan de
  noche.

## Lo que se sabe de las políticas (aprendizaje por imitación)

- El robot aprende copiando demostraciones grabadas (teleoperando con el brazo guía o con un recolector programado
  que mueve el brazo solo con aleatoriedad).
- ACT: un modelo por tarea, sin lenguaje, ligero, preciso. VLA (SmolVLA): recibe una frase, un modelo para varias
  tareas, preentrenado con datos de brazos como el SO-101; ~50 episodios por tarea; se entrena en la nube en 3-6 h.
- Lo que los VLA hacen bien: varias tareas con un solo modelo elegidas por una frase; objetos y posiciones algo
  distintos; coger y dejar. Lo que hacen mal: precisión milimétrica, tareas largas con una sola orden, distinguir
  tareas que solo cambian en la frase con la misma escena.
- Tiempo realista: 1-2 ciclos de grabar → entrenar → probar durante el sábado.

## Lo que gana (37 proyectos de hackathons 2025-2026 analizados)

- En hackathons de LeRobot el ganador siempre tuvo una política aprendida; la mitad de los recientes usa VLA.
- Arquitectura ganadora: un selector programado (a menudo un LLM con voz) que lanza varias habilidades aprendidas
  cortas.
- Puntúa: funciona en vivo y se recupera a la vista del jurado; tasa de aciertos medida; se entiende en 5 segundos;
  un humano en el centro; algo físico propio pequeño (pinzas impresas, un sensor); una capa de vida (voz,
  personaje); estados visibles en la escena (cada paso se distingue en cámara).
- La emoción da la atención; la evidencia da la nota.
- **Temas ya usados (evitar o diferenciar mucho):** camarero/cócteles (dos veces), asistente de soldadura que
  alumbra con linterna (ganador del hackathon vecino hace un mes), ajedrez, doblar ropa/toallas, sándwich, tienda de
  donuts, Conecta 4, clasificar por colores, tubos de ensayo, paquetería con cinta, matcha, recoger el escritorio,
  maquillaje, quitar el móvil.

## Rúbrica de trabajo

Funciona en vivo y se recupera 30 % · Dificultad técnica 20 % · Utilidad práctica 20 % · Creatividad y momento
memorable 15 % · Facilidad de uso y presentación 15 %.

Filtro: (1) una habilidad central al 80 % con 50-80 episodios; (2) parece difícil; (3) se entiende en 5 s con un
humano en el centro; (4) recuperación planificada; (5) capa de vida que se puede quitar; (6) algo físico propio;
(7) escalera de alcance (nivel 1 el sábado a mediodía).

Principio: **es más importante no perder que ganar.**
