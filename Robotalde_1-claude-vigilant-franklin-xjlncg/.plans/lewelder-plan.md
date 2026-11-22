# Plan: LeWelder (fase 3)

**Spec:** [.plans/lewelder-spec.md](lewelder-spec.md) · **Complejidad:** grande · **Hecho con:** el método de
`/ecc:plan` aplicado a mano (el plugin está instalado pero esta sesión no lo carga).

**Quién construye:** Andoni (hardware: CAD, impresión, electrónica) y Claude (todo el software), a toda velocidad,
con una **demo completa en simulación antes del jueves 19**. Los compañeros se suman en el evento.

## Resumen

Software en un paquete Python `lewelder/` que funciona **sin hardware**: fuentes simuladas de antorcha, cámara y
robot sustituyen a las reales con la misma interfaz. Así cada parte se prueba sola y la demo se ensaya en el
navegador antes de tener nada impreso. El robot se practica en MuJoCo: demostraciones guionizadas con nuestra
cinemática inversa → dataset LeRobot con instrucción de texto → ACT y SmolVLA → evaluación con las mismas métricas
que puntúan al alumno.

## Requisitos (resumen de la spec)

1. Puntuar una pasada de soldadura: cobertura, velocidad, quemados, desvío y ángulo; nota y huecos, con tolerancia
   por niveles (±8/±5/±3 mm).
2. Seguir la punta de la antorcha (LED) y la pieza (ArUco) con una webcam, en coordenadas de la pieza.
3. Leer la antorcha del alumno (gatillo + IMU) y encender el LED de la del robot por USB.
4. Tablet: gemelo three.js con el cordón en tiempo real, nota, avisos y modos Examen, Repaso y Maestro.
5. Robot: política VLA (SmolVLA) con instrucción de texto y respaldo ACT o replay; LED solo en los huecos.
6. Filtro de dataset por nota; comparativa VLA frente a ACT; instructor por reglas + valoración final del LLM.

## Contrato común (lo fija la tarea 1; el resto lo usa sin esperar)

- **Unidades:** milímetros y segundos. Ángulos en grados.
- **Marco de la pieza:** origen al inicio del cordón, X a lo largo del cordón (0-120 mm), Y transversal, Z hacia
  arriba desde la superficie. El ArUco de cada pieza fija este marco (offset conocido por tipo de pieza).
- **Cordón:** 120 mm en **24 tramos de 5 mm**. Tipos de pieza: `recta` (ArUco 10-19) y `t` (ArUco 20-29).
  Anclajes de la base: ArUco 0-3.
- **Muestra** (fusionada a ~60 Hz): `t, x, y, z, gatillo, angulo_trabajo, angulo_avance`.
- **Serie antorcha alumno → PC** (115200, una línea JSON a 100 Hz): `{"t":ms,"g":0|1,"q":[w,x,y,z]}`.
- **Serie PC → antorcha robot:** `L1\n` / `L0\n`. Ambas responden `{"id":"alumno"|"robot"}` a `?\n`.
- **Instrucciones del robot** (vocabulario cerrado): `suelda la unión {recta|en T} del anclaje {A|B|C|D}` y
  `coloca la pieza en el anclaje {A|B|C|D}`.

## Patrones que seguir

| Categoría | Fuente | Patrón |
|---|---|---|
| Nombres | `sim/cinematica.py:15-20` | Español; constantes en MAYÚSCULAS; clases `Cinematica`; métodos `directa`/`inversa` |
| Docstrings | `sim/cinematica.py:1-9` | Docstring de módulo que explica el porqué; comentarios cortos en español |
| Errores | `sim/cinematica.py:52-56` | Devolver resultado + error medido (`(q, error)`) en vez de excepciones en cálculo numérico |
| Rutas | `herramientas/explorar_modelo.py:5` | `pathlib.Path` relativo a la raíz del repo |
| Tests | — | **No hay tests todavía**: se crea `tests/` con pytest |

## Archivos

| Ruta | Acción | Para qué |
|---|---|---|
| `pyproject.toml`, `tests/` | CREAR | Paquete `lewelder`, dependencias, pytest |
| `lewelder/cordon.py`, `lewelder/metricas.py` | CREAR | Contrato, tramos, métricas, nota, huecos |
| `lewelder/seguimiento.py` | CREAR | LED + ArUco → coordenadas de la pieza |
| `lewelder/antorcha.py` | CREAR | Lectura serie, orientación de la IMU → ángulos, LED del robot, simuladores |
| `firmware/antorcha_alumno/`, `firmware/antorcha_robot/` | CREAR | Arduino/ESP32 (mismo código, PlatformIO o IDE) |
| `lewelder/servidor.py`, `web/` | CREAR | Servidor WebSocket + app three.js para la tablet |
| `lewelder/instructor.py` | CREAR | Avisos por reglas + valoración final del LLM (con salida sin red) |
| `sim/escena.py`, `sim/demostraciones.py` | CREAR | Escena MuJoCo (mesa, base, pieza, antorcha, 2 cámaras) y demostraciones guionizadas |
| `robot/` (`dataset.py`, `entrenar.md`, `evaluar.py`, `politica.py`) | CREAR | LeRobotDataset con instrucción, recetas ACT/SmolVLA, evaluación, selector VLA/ACT/replay |
| `hardware/contrato.md`, `hardware/aruco/` | CREAR | Medidas que CAD y software comparten; marcadores ArUco imprimibles |

## Tareas

Las tareas 1-5 son **independientes** gracias al contrato: van en paralelo, cada una con su subagente en su
worktree. La 6 y la 7 integran.

### Tarea 1 · Núcleo: cordón y métricas (TDD)
- **Hacer:** tipos `Pieza`, `Muestra`, `Pasada`; tramos; cobertura por tramo (gatillo y |desvío| < tolerancia),
  velocidad y regularidad, quemado (parado > 0,6 s con gatillo), desvío medio, ángulo fuera de rango; nota 0-10 y
  lista de huecos; filtro de dataset (`nota >= umbral`).
- **Validar:** `pytest tests/test_metricas.py` con pasadas sintéticas (perfecta, con hueco, temblorosa, quemada).

### Tarea 2 · Seguimiento por cámara
- **Hacer:** LED por umbral de brillo y color con exposición baja (centro del blob con precisión de subpíxel);
  pose de la pieza por ArUco (`cv2.aruco`, calibración de cámara); proyección al plano de la pieza; filtro de
  saltos; fuente simulada que pinta imágenes sintéticas.
- **Validar:** `pytest tests/test_seguimiento.py` con imágenes renderizadas: error < 2 mm en el plano.

### Tarea 3 · Antorchas: firmware y lectura
- **Hacer:** firmware del alumno (gatillo con antirrebote, IMU BNO055/MPU6050 → cuaternión, LED, JSON a 100 Hz) y
  del robot (`L1`/`L0`); `lewelder/antorcha.py` con autodetección del puerto por `?`, cuaternión → ángulos de
  trabajo y avance en el marco de la pieza, simulador.
- **Validar:** `pytest tests/test_antorcha.py` (parser, ángulos, puerto falso con `serial.serial_for_url("loop://")`);
  firmware compilado con `arduino-cli` si está disponible.

### Tarea 4 · Robot en simulación y dataset
- **Hacer:** escena MuJoCo con base de 4 anclajes, piezas recta y T, antorcha fija en la pinza, cámara cenital y de
  muñeca; demostraciones por cinemática inversa con ruido humano; grabado a `LeRobotDataset` (LeRobot 0.7) con la
  instrucción como tarea; solo entran las demostraciones con nota alta (usa la tarea 1).
- **Validar:** el dataset se carga con `LeRobotDataset`; recorrido guionizado con error < 2 mm en los 4 anclajes.

### Tarea 5 · Contrato de hardware (Claude) + CAD e impresión (Andoni)
- **Claude:** `hardware/contrato.md` (cordón 120 mm, tamaño y posición del ArUco en cada pieza y anclaje, imanes,
  holguras de impresión, punta de la antorcha → LED) y PDF de marcadores a escala real.
- **Andoni:** antorchas, base, piezas, soportes; inventario y pedido del lunes 16.
- **Validar:** una pieza impresa medida con calibre coincide con el contrato a ±0,3 mm.

### Tarea 6 · Servidor, app de la tablet e instructor (depende de 1-3)
- **Hacer:** servidor asyncio con WebSocket; modos Examen, Repaso, Maestro; fuentes reales o simuladas por
  parámetro; página three.js (pieza, cordón coloreado por calidad, nota grande, avisos, panel VLA/ACT/replay);
  instructor por reglas en vivo y valoración final del LLM (2 frases, tiempo máximo de espera, sin red continúa).
- **Validar:** `python -m lewelder.servidor --simulado` y captura de la tablet con Playwright; tests de los modos.

### Tarea 7 · Políticas: entrenar, evaluar, desplegar (depende de 1 y 4)
- **Hacer:** recetas `lerobot-train` para ACT y SmolVLA (portátil y nube); entrenamiento corto en CPU aquí para
  probar el flujo; `robot/evaluar.py` (10 recorridos por anclaje, éxito si cobertura completa a ±5 mm); selector de
  política en caliente; Repaso: LED encendido al entrar en tramos pendientes; replay grabado como último respaldo.
- **Validar:** evaluación en simulación genera la tabla VLA frente a ACT; el Repaso de punta a punta funciona en
  simulación desde la tablet.

### Hito final · Demo en simulación (jueves 19)
Juez simulado (o ratón en la tablet) suelda → nota → Repaso con el robot de MuJoCo en pantalla → cambio de anclaje
→ "suelda la T". Se graba en vídeo como respaldo para el pitch.

## Orden

| Cuándo | Qué |
|---|---|
| **Dom 15 - lun 16** | Tareas 1, 2, 3, 4 y 5 en paralelo (subagentes en worktrees). Andoni: inventario, pedido, CAD |
| **Mar 17** | Tarea 6 y tarea 7 (primer entrenamiento corto). Andoni imprime antorchas y base |
| **Mié 18** | Entrenamiento SmolVLA en la nube (necesita cuenta de GPU); prueba con webcam y antorcha reales en casa de Andoni |
| **Jue 19** | Hito final, prueba integrada con hardware real, vídeo de respaldo |

## Validación

```bash
pip install -e ".[dev]"
pytest -q
python -m lewelder.servidor --simulado        # tablet en http://localhost:8000
python -m robot.evaluar --sim --politica act  # tabla de éxito por anclaje
```

## Riesgos

| Riesgo | Prob. | Mitigación |
|---|---|---|
| Aquí no hay GPU: no se puede entrenar SmolVLA de verdad en la nube de Claude | Alta | Flujo probado en CPU con pocos pasos; entrenamiento real en la nube de GPU o en el portátil de Andoni |
| LeRobot 0.7 cambia formatos o comandos respecto a lo esperado | Media | Fijar versión; tarea 4 empieza leyendo la documentación y ejemplos de 0.7 |
| El salto de simulación a robot real no sirve para la política | Alta | La simulación es para practicar el flujo; el dataset real se graba allí con el brazo guía |
| Sin hardware en la nube para probar serie y cámara | Media | Simuladores con la misma interfaz; prueba real el miércoles en casa de Andoni |
| IMU sin confirmar | Media | El ángulo es nivel 2: sin IMU, la nota sale sin ángulo |
| Tiempo | Alta | Imprescindibles primero: tareas 1, 2, 6 (parte humana) y 4-7 con ACT; VLA después |

## Aceptación

- [ ] `pytest` en verde
- [ ] Demo en simulación de punta a punta desde la tablet
- [ ] Tabla VLA frente a ACT generada en simulación
- [ ] Firmware y contrato de hardware listos para el hardware de Andoni
- [ ] Patrones del repo respetados (español, `pathlib`, resultado + error)
