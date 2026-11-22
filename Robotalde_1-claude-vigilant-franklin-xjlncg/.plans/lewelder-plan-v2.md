# Plan: LeWelder v2 (fase 3)

**Spec:** [lewelder-spec-v2.md](lewelder-spec-v2.md) · **Hecho con:** `/ecc:plan` (modo referencia) · **Complejidad:** grande

## Resumen

La v2 convierte LeWelder en una escuela-taller: el juez pide una junta por voz, el robot (SmolVLA multitarea) monta
la chapa móvil sobre la base fija, la escuela reconoce la junta en 3D con dos cámaras, el robot la señala y demuestra
la soldadura, y el alumno suelda con gatillo + apoyo frente al fantasma del maestro. Todo se prepara en simulación,
como en la v1, con la misma interfaz que el hardware real, y se reutiliza casi todo lo construido (métricas,
seguimiento, antorchas, servidor, tablet, simulación y flujo de entrenamiento).

## Requisitos (resumen de la spec v2)

1. Juntas **en T** y **en esquina**: base fija + chapa móvil con aleta, unidas con imanes; un ArUco por chapa.
2. **Reconocimiento 3D estéreo**: pose de cada chapa, tipo de junta, posición de soldeo y altura de la punta (apoyo).
3. **Vocabulario del robot**: montar T, montar esquina, señalar el cordón, coger la antorcha y soldar (núcleo);
   desmontar, acercar la antorcha (nivel 2); girar la junta (nivel 3).
4. **Voz → LLM → orden cerrada → confirmación en la tablet**.
5. **Clase en la tablet**: pedir → montar → reconocer → alcance ("gírala") → señalar → demostrar (fantasma) →
   soldar (gatillo + apoyo) → nota → insignias, niveles y certificado; ficha de teoría por junta; plan B "monto yo".
6. **Inferencia del VLA en un servidor remoto** (servidor de políticas de LeRobot en GPU de la nube).
7. Objetivo: **montaje 8/10 por junta** el sábado 20:00.

## Patrones que seguir

| Categoría | Fuente | Patrón |
|---|---|---|
| Contrato común | `lewelder/contrato.py` | Todas las medidas y nombres compartidos en un módulo; nada de números copiados |
| Nombres | `sim/cinematica.py:15-20`, `lewelder/seguimiento.py:256` | Español; constantes en MAYÚSCULAS; funciones verbo (`detectar_marcadores`, `estimar_pose_pieza`) |
| Errores en cálculo | `sim/cinematica.py:52-56`, `lewelder/seguimiento.py:356` | Devolver resultado + error medido, o `None` si no hay detección; sin excepciones en el bucle de tiempo real |
| Logging | `lewelder/servidor.py:91` | `log = logging.getLogger("lewelder.<módulo>")` |
| Servidor | `lewelder/servidor.py:135` (`Escuela`), `:658` (`orden`) | Máquina de estados en `Escuela`; órdenes de la tablet por `orden(dict)`; mensajes JSON por WebSocket |
| Robot | `lewelder/robot.py` (`Robot`), `lewelder/robot_mujoco.py:49` | Interfaz `Robot` común; implementaciones intercambiables (cinemático, MuJoCo, real) |
| Simulación | `sim/escena.py:343-407`, `sim/entorno.py:72` | Escena generada desde el contrato; entorno con `reset`/`step`/`observacion` |
| Tests | `tests/test_metricas.py:1-25` | pytest; datos sintéticos con semilla; un archivo `tests/test_<módulo>.py` por módulo |
| Fuentes simuladas | `lewelder/camara_sintetica.py:159`, `lewelder/antorcha_virtual.py` | Cada hardware tiene un sustituto con la misma interfaz |

## Archivos

| Ruta | Acción | Para qué |
|---|---|---|
| `lewelder/contrato.py` | UPDATE | `TipoJunta` (T, esquina), geometría base + chapa móvil + aleta, ArUco por chapa, poses de las 2 cámaras, zona libre, soporte de la antorcha, umbral de apoyo, posiciones de soldeo, vocabulario v2 |
| `lewelder/estereo.py` | CREATE | Calibración estéreo, triangulación del LED, pose 3D de cada chapa con las dos cámaras |
| `lewelder/juntas.py` | CREATE | Reconocer la junta (T, esquina, incompleta) y la posición de soldeo; marco del cordón en la junta montada |
| `lewelder/camara_sintetica.py` | UPDATE | Chapas en 3D (también verticales) con su ArUco, dos cámaras |
| `lewelder/metricas.py` | UPDATE | Criterio gatillo + apoyo; comparación con el fantasma; ángulos de la esquina |
| `lewelder/voz.py` | CREATE | Texto hablado → orden cerrada (LLM con respaldo por palabras clave) |
| `lewelder/alcance.py` | CREATE | ¿Llega el robot a esta junta? Si no, qué giro pedir |
| `lewelder/servidor.py`, `web/` | UPDATE | Clase v2 (máquina de estados), voz, ficha, fantasma, niveles, insignias, plan B |
| `lewelder/robot_mujoco.py`, `lewelder/robot_remoto.py` | UPDATE / CREATE | Vocabulario v2; cliente del servidor de políticas remoto |
| `sim/escena.py`, `sim/montaje.py`, `sim/demostraciones.py` | UPDATE / CREATE | Mesa de montaje con imanes, chapa en zona libre, antorcha en soporte; demostraciones de las órdenes del núcleo |
| `robot/evaluar.py`, `herramientas/entrenar_hf_jobs.sh` | UPDATE | Éxito de montaje (8/10), entrenamiento multitarea |
| `herramientas/generar_hardware.py`, `hardware/` | UPDATE | Base con imanes autocentrantes, chapa con aleta, ArUco por chapa, soporte de antorcha con mango, soportes estéreo |

## Tareas

Igual que en la v1: la **tarea 0** fija el contrato y después las tareas 1-5 van **en paralelo**, cada una con su
subagente y su worktree. Las tareas 6 y 7 integran y la 8 cierra.

### Tarea 0 · Contrato v2 (Claude, antes de lanzar nada)
- **Hacer:** ampliar `lewelder/contrato.py` sin romper la v1: `TipoJunta`, medidas de base y chapa móvil (aleta,
  imanes en cantos con guía), ids de ArUco por chapa, poses por defecto de las dos webcams, zona libre, soporte de la
  antorcha, `ALTURA_APOYO` (2 mm), posiciones de soldeo (PA, PB, PF…), vocabulario v2 con su nivel.
- **Validar:** `pytest -q` entero sigue en verde.

### Tarea 1 · Estéreo y reconocimiento 3D
- **Hacer:** `estereo.py` (calibración con el tablero ya generado, triangulación, pose por chapa fusionando las dos
  cámaras), `juntas.py` (T / esquina / incompleta, posición de soldeo, marco del cordón), cámara sintética con chapas
  3D y dos vistas.
- **Mirror:** `seguimiento.py` (detección, `None` si no hay), `camara_sintetica.py` (verdad devuelta con la imagen).
- **Validar:** `pytest tests/test_estereo.py tests/test_juntas.py`: pose de la base < 3 mm y < 2°; tipo de junta 10/10;
  apoyo (< 2 mm) distinguido de 5 mm en ≥ 95 % de los fotogramas.

### Tarea 2 · Montaje en simulación
- **Hacer:** escena MuJoCo con base fija, chapa móvil tumbada con aleta en la zona libre (posición y giro aleatorios),
  imanes (fuerza de atracción o restricción que se activa cerca), antorcha del robot en soporte con mango, cámaras
  cenital y de muñeca; demostraciones guionizadas de `monta una unión en T/esquina`, `señala el cordón` y `coge la
  antorcha y suelda la junta`; detector de éxito (junta cerrada); dataset LeRobot multitarea.
- **Mirror:** `sim/escena.py`, `sim/entorno.py`, `sim/demostraciones.py` (filtro por nota, reintento de semilla).
- **Validar:** guion sin ruido: montaje 10/10 por junta en posiciones aleatorias; dataset cargable; 2 pasos de
  SmolVLA sobre él.

### Tarea 3 · Voz → orden
- **Hacer:** `voz.py`: texto → orden del vocabulario (LLM rápido con salida estructurada y tiempo máximo; respaldo por
  palabras clave sin red; "no entendido" si no encaja); reconocimiento de voz en la tablet (Web Speech API, es-ES) con
  botón de micrófono.
- **Mirror:** `instructor.py` (LLM con tiempo máximo y respaldo por reglas; cliente simulado en tests).
- **Validar:** `pytest tests/test_voz.py` con 30 frases variadas ("móntame una esquina", "pon la T", "¿dónde se
  suelda?") → orden correcta sin red y con LLM simulado.

### Tarea 4 · Métricas v2 y alcance
- **Hacer:** en `metricas.py`, "soldando" = gatillo + apoyo; métricas frente al fantasma (desfase de velocidad y
  ángulo por tramo); ángulo objetivo de la esquina. `alcance.py`: con la pose 3D de la junta y la cinemática del
  SO-101, decir si llega y, si no, el giro a pedir.
- **Mirror:** TDD como `tests/test_metricas.py`; `sim/cinematica.py` para el alcance.
- **Validar:** `pytest tests/test_metricas.py tests/test_alcance.py`.

### Tarea 5 · Hardware v2 (Claude: generador y documento · Andoni: CAD e impresión)
- **Hacer:** `generar_hardware.py` v2: base fija con imanes y guías cónicas, chapa móvil con aleta para la pinza,
  ArUco por chapa (y por cara si hace falta), soporte de la antorcha del robot con mango, soportes de las dos webcams;
  lista de material (2.ª webcam).
- **Validar:** `pytest tests/test_hardware.py`; ArUco detectados a escala; Andoni imprime la base y una chapa.

### Tarea 6 · Servidor y tablet v2 (depende de 0, 1, 3, 4)
- **Hacer:** máquina de estados de la clase v2; mensajes nuevos (orden propuesta, junta reconocida, alcance, fantasma,
  insignias); tablet: micrófono y confirmación, gemelo de T y esquina, ficha de teoría, fantasma superpuesto,
  progreso y niveles, certificado con juntas dominadas, botón de plan B "monto yo".
- **Validar:** test de punta a punta con fuentes simuladas; capturas con Playwright revisadas.

### Tarea 7 · Robot y políticas v2 (depende de 2)
- **Hacer:** `RobotMuJoCo` con el vocabulario v2; `robot_remoto.py` (cliente del servidor de políticas de LeRobot);
  evaluación de montaje 8/10; entrenamiento multitarea en HF Jobs; replay como respaldo.
- **Validar:** `python -m robot.evaluar --politica replay --tareas montar_t montar_esquina` con 10/10; servidor
  remoto probado en local (servidor y cliente en esta máquina).

### Tarea 8 · Demo v2 y pitch
- **Hacer:** vídeo de la clase completa en simulación, página para el móvil actualizada, guion del pitch v2.
- **Validar:** vídeo revisado; guion < 5:00.

## Orden

| Cuándo | Qué |
|---|---|
| Lun 16 | Tarea 0; lanzar 1-5 en paralelo. Andoni: piezas v2 (base, chapa con aleta, soporte de antorcha) |
| Mar 17 | Fusionar 1-5; lanzar 6 y 7 |
| Mié 18 | Fusionar 6 y 7; entrenar SmolVLA multitarea (simulación) en HF Jobs |
| Jue 19 | Tarea 8; prueba de la clase completa en simulación; piezas impresas probadas |

## Validación

```bash
MUJOCO_GL=egl .venv/bin/python -m pytest -q -m "not lento"
MUJOCO_GL=egl .venv/bin/python -m lewelder.servidor --fuente simulada --robot mujoco --politica replay
MUJOCO_GL=egl .venv/bin/python -m robot.evaluar --politica replay
```

## Riesgos

| Riesgo | Prob. | Mitigación |
|---|---|---|
| Simular imanes y el agarre por la aleta en MuJoCo es delicado (contactos, deslizamiento) | Alta | Imán como restricción que se activa a < 1 cm; agarre con fricción alta; validar pronto (tarea 2 empieza por ahí) |
| El montaje real es la tarea más difícil y es la imprescindible | Alta | Piezas diseñadas para el robot (aleta, guías, imanes); dos puestos de grabación; plan B "monto yo" |
| Estéreo real: calibración y oclusiones | Media | Soportes fijos; pose de chapas guardada mientras no se mueven; calibración probada el miércoles con webcams reales si las hay |
| Inferencia remota y wifi | Media | Probar latencia el viernes; datos móviles; plan B |
| Sin crédito de HF no se entrena en GPU | Media | Recargar antes del miércoles; mientras, flujo probado en CPU |
| Alcance: 9 tareas para 4 días | Alta | Núcleo primero (1-4, 6-7); niveles 2-3 solo si sobra |

## Aceptación

- [ ] Todas las tareas completas
- [ ] `pytest` en verde
- [ ] Clase v2 completa en simulación, de la voz al certificado
- [ ] Montaje 10/10 con replay y flujo SmolVLA multitarea probado
- [ ] Patrones del repo seguidos, no reinventados
