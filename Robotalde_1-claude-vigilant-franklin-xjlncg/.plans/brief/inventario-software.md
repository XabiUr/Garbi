# Inventario del software reutilizable (18-11-2026)

Lectura completa del repositorio (369 tests en 24 archivos; no se ejecutaron). Pensado para una demo de tipo
«asistente de banco: la persona pide por voz, el robot coge y deja, sensores confirman, la pantalla muestra órdenes
y un marcador de autonomía».

## Lo que falta del todo (hay que escribirlo)

- **Controlador del SO-101 real:** `robot_remoto.py` no existe; todo el robot es MuJoCo o cinemático.
- **Despliegue con LeRobot 0.7:** nada para `lerobot-rollout` interactivo ni servidor de políticas; nada de grabación
  con el robot real.
- **Integración tablet v2 ↔ servidor real** (tarea 6b): solo funciona dentro de `lewelder/simulador.py`.

## Tabla de reutilización

| Reutilizable tal cual | Reutilizable con cambios | Específico de soldadura |
|---|---|---|
| `web/v2/cliente.js`, `sonido.js`, fuentes y CSS | `lewelder/voz.py` (26 tests): nuevo vocabulario en `contrato.ORDENES`, palabras clave, `PREGUNTAS`, `ETIQUETAS` | `metricas.py`, `fantasma.py`, `instructor.py` (avisos) |
| `web/voz.js`, `web/v2/voz.js` (micro, síntesis, Chispas) | `lewelder/personaje.py` (12 tests): nuevos eventos y frases | `juntas.py`, `alcance.py` |
| `instructor.crear_cliente_llm` (Anthropic, sin red devuelve None) | `lewelder/puntuacion.py` (22 tests): el `Ranking` vale; los puntos pasan a autonomía | `fusion.py`, `sintetico.py`, `fuentes.py` |
| `sim/cinematica.py`, `sim/entorno.py` (interfaz so101) | `web/v2/app.js`, `index.html`, `PROTOCOLO.md`: pantallas nuevas | `firmware/antorcha_*` (vale el patrón) |
| `robot/politica.py` (10 tests): carga ACT, SmolVLA, replay | `lewelder/simulador.py`: rehacer `ClaseSim` como máquina de estados del asistente | `hardware/planos`, `hardware/v2/cad` |
| `herramientas/entrenar_hf_jobs.sh`, `subir_hf.py` | `lewelder/guion_robot.py`: selector guion / aprendido / respaldo | `web/v2/gemelo.js` |
| `lewelder/antorcha.py` (31 tests): serie JSON, autodetección, puerto virtual | `lewelder/mesa_sim.py`, `sim/montaje.py`, `sim/demos_montaje.py`: coger → dejar en zona con objetos nuevos | `lewelder/servidor.py` (v1) |
| `seguimiento.py`, `estereo.py`: ArUco y calibración; `hardware/aruco/` | `robot/evaluar.py`: criterio X/10 «objeto en zona» | |

## Detalles útiles

- **Voz:** dos capas. Reglas sin red (palabras clave y sinónimos); LLM (`claude-opus-5-5`, salida JSON con enum, 2 s
  de tope) solo si la confianza baja de 0,8. Confirmación SÍ/NO antes de ejecutar. En el navegador, Web Speech API
  (necesita internet en Chrome); respaldo con campo de texto y botones.
- **Tablet v2:** «tonta», pinta mensajes JSON por WebSocket (`pantalla`, `personaje`, `orden_propuesta`, `robot`,
  `puntos`, `resultado`, `ranking`). Sonido sintetizado sin archivos. Fuentes locales.
- **Firmware:** Arduino/ESP32, 115200 baudios, JSON por líneas, `?` para identificarse, latido de seguridad.
- **Entrenamiento:** `robot/entrenar.md` (recetas de `lerobot-train` para ACT y SmolVLA con `--rename_map`),
  HF Jobs con L4 o A10G.

## Prioridades

1. Rehacer el vocabulario de voz (poco trabajo, probado).
2. Mantener tablet v2, sonido, personaje y ranking.
3. Boceto de ESP32 de sensores sobre el patrón de `antorcha.py`.
4. **Escribir lo que falta:** grabación y despliegue con el SO-101 real con las herramientas de LeRobot 0.7.
