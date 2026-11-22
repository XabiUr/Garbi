# Proyectos de referencia: ganadores de hackathons y top de Hugging Face

Extracción del 18-11-2026. 37 proyectos con la misma ficha: fuentes, qué hace, análisis técnico y de la aplicación,
por qué ganó, nota con nuestra rúbrica, replicabilidad en 48 h con SO-101 y lección para LeWelder.

| Documento | Qué cubre |
|---|---|
| [hackathons-2026-europa.md](hackathons-2026-europa.md) | 12 proyectos: Robotekin, Bilbao I, AMD París, Ámsterdam, Múnich, Zúrich, LeHome (ICRA), Worldwide 2025 |
| [hackathons-2026-mundo.md](hackathons-2026-mundo.md) | 12 proyectos: AMD Tokio, Seeed/NVIDIA (EE. UU. y Shenzhen), CCSF, Junfan Labs, Hong Kong, Tokio, Hack Club |
| [top-huggingface.md](top-huggingface.md) | 13 proyectos de la comunidad + 3 referencias base, por likes, descargas y menciones en el blog |

**Cómo leer las notas.** Rúbrica de trabajo ([analisis-concursos.md](../analisis-concursos.md), sección 5): funciona en
vivo y se recupera 30 %, dificultad 20 %, utilidad 20 %, creatividad 15 %, presentación 15 %. Anclas estrictas
(10 = excepcional y demostrado, 5 = correcto o sin pruebas) y **lo que no se puede comprobar con fuentes no pasa de
5**. Por eso la nota mide la evidencia pública, no el puesto: varios ganadores de 2026 puntúan bajo porque no
publicaron repo ni vídeo. Las notas de los tres documentos las pusieron revisores distintos: compararlas entre
documentos es orientativo.

## Ranking conjunto (los 15 mejores)

| # | Proyecto | Dónde | Puesto / métrica | Política | Episodios | Nota |
|---|---|---|---|---|---|---|
| 1 | Doblado de camisetas (Unfolding Robotics) | Hugging Face | 162 likes; 90 % en 20 ensayos | VLA ajustado | — | 85,5 |
| 2 | Asistente de soldadura con linterna (MSN) | Robotekin, Vitoria, oct 2026 | 1.º | ACT + control visual programado | 54 | 74,5 |
| 2 | LeHome, final real | ICRA, Viena, jun 2026 (competición) | 2.º real / 1.º sim | π0.5 + RL + DAgger | — | 74,5 |
| 4 | Flip & Ship | AMD, París, dic 2025 | 1.º | 3 × SmolVLA | 126 + 150 + 145 | 74,0 |
| 4 | XLeRobot | GitHub | ~5,8k estrellas | varias | — | 74,0 |
| 6 | Reachy Mini Conversation App | Hugging Face | 193 likes | LLM + movimientos | — | 72,5 |
| 7 | Donuts Order Assistant (GreatAkihabara) | AMD, Tokio, dic 2025 | 1.º | SmolVLA multitarea por texto + RTC | 120 (+30) | 71,0 |
| 8 | Prompting Robots (rollout interactivo) | Blog de Hugging Face | oficial | SmolVLA con `/subtask` | — | 69,0 |
| 9 | Baby Reachy-Mini Companion | Hugging Face | 179 likes | — | — | 67,5 |
| 10 | LeCyborg | Worldwide, jun 2025 | 13.º | ACT con EMG | — | 66,5 |
| 11 | Matcha Making (UIUC) | Seeed/NVIDIA, EE. UU., oct 2025 | 1.º | GR00T N1.5 | ~30 por subtarea | 64,0 |
| 12 | FLUX 3 Action SO-101 | Hugging Face | 65 likes | VLA | — | 63,0 |
| 13 | Talos | ERH, Zúrich, oct 2026 | ganador | ninguna (ROS 2) | 0 | 62,0 |
| 14 | LeKiwi | GitHub | ~1,5k estrellas | — | — | 62,0 |
| 15 | Tubos de ensayo | CCSF, San Francisco, nov 2026 | 1.º | ACT + pinzas impresas | — | 61,0 |

Fuera del top, pero importantes: AI Bartender (Bilbao I, 1.º, 60,5), Conecta 4 (AMD París, 3.º, SmolVLA con 5
tareas, 56,5), CaliKPR (Junfan #35, 1.º sin demostraciones: agente de Claude con 28 herramientas MCP, 58 [parte no
verificada]) y Reachy Phone Home (la app con más likes, 372, técnicamente simple: 57).

## Patrones de los ganadores

1. **Habilidades aprendidas troceadas y un selector programado.** Ningún ganador hace la tarea entera con un solo
   modelo: Flip & Ship (3 SmolVLA), Sprinkle (4 SmolVLA), GreatAkihabara (SmolVLA multitarea + un modelo aparte para
   la subtarea que fallaba). Es la arquitectura de LeWelder.
2. **Los VLA ya ganan.** De 8 ganadores con política conocida fuera de Europa, 4 usan VLA. En los hackathons de
   LeRobot (Vitoria, Bilbao, París, Tokio) el ganador siempre tuvo una política aprendida.
3. **Recuperación visible y fiabilidad medida.** La luz que esquiva la mano (MSN), el paquete que se voltea (Flip &
   Ship), el cóctel improvisado (Bilbao), el 90 % en 20 ensayos (camisetas), el 20/20 (CaliKPR).
4. **Estados visibles en la escena**, porque los VLA no tienen memoria: cuenco marcado, LED que confirma, campana de
   fin. Cada paso debe distinguirse en cámara.
5. **Humano en el centro y algo físico propio pequeño:** pinzas impresas, ruleta con ESP32, botón con sensor.
6. **La emoción da los likes; la evidencia da la nota.** Curar los datos mejoró el doblado de camisetas 50 puntos;
   cambiar de algoritmo, entre 5 y 20.
7. **Volumen:** ~50 episodios por habilidad con poca variación; ~100-150 para llegar a ~90 %. Elegir el modelo
   probando en el robot.

## LeWelder frente a ellos (estimación nuestra, con la misma rúbrica)

| Escenario | Vivo (30) | Dific. (20) | Util. (20) | Creat. (15) | Present. (15) | Nota |
|---|---|---|---|---|---|---|
| Plan A: el VLA monta ≥ 5/10 en directo, nota al alumno, marcador medido | 6 | 8 | 7 | 8 | 7 | ~70 |
| Plan B: el alumno monta; el robot señala y demuestra con replay | 7 | 4 | 7 | 7 | 7 | ~64 |

Lectura: con el plan A estaríamos a la altura de los ganadores de AMD; el plan B sigue siendo competitivo, pero
pierde la dificultad. Lo que más subiría la nota: **recuperación visible** (reintentar el agarre) y **tasa de
aciertos medida y mostrada** (X/10).

## Avisos

- **Precedente directo:** MSN ganó Robotekin hace un mes con un asistente de soldadura. Nos diferencia que el robot
  monte la junta con varias habilidades aprendidas y que la escuela ponga nota al alumno.
- **El camarero está quemado:** lo hicieron Bilbao 2025 y otro equipo en Zúrich en 2026.
- **Dudas abiertas:** ESILV dice haber quedado 3.º en París, pero no figura en la lista oficial; el repo de RoBoost
  tiene el código del brazo vacío; los datos de Junfan Labs vienen de fragmentos de redes sociales. No hay pruebas de
  que se celebrara un LeRobot Worldwide 2026.
