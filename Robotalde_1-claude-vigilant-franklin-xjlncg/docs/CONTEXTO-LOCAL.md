# Garbi · contexto para el Claude Code local (PC del equipo, 21-11-2026)

> **Lee esto entero antes de hacer nada.** Resume lo que se ha construido en la sesión en la nube, lo que el equipo
> tiene en este PC y cómo unirlo. Después lee `garbi/producto/README.md` (si existe), `.plans/aspira/producto.md` y
> `garbi/producto/garbi_producto.yaml`.

## 1. Situación

- **Hackathon LeRobot Bilbao II, equipo Robotalde.** Entrega el **domingo 22-11 a las 11:00**:
  - vídeo de 1 minuto;
  - presentación de 3 minutos;
  - demo en vivo de 5 intentos seguidos sin tocar el robot.
- **Rúbrica:** demo 30, datos y entrenamiento 20, dificultad 15, utilidad 15, innovación 10, presentación 10. Bonus:
  dataset en Hugging Face (+3) y repositorio reproducible (+2). Detalle en `docs/plan-entrega.md`.
- **Garbi:** un SO-101 con una boquilla de aspiradora atada a la pinza, con el tubo por el costado del brazo. Ayuda a
  quien taladra madera: se acerca a la broca y aspira mientras taladras, y al terminar barre la tabla y el tapete.
  Se vende como **producto con camino a la industrialización** (Garbi Taller y Garbi Fábrica). El equipo trabaja en
  fábricas y además es maker.
- **Rama de trabajo:** `claude/vigilant-franklin-xjlncg`. Haz `git pull` a menudo: la sesión de la nube puede seguir
  subiendo cosas.

## 2. Lo que tiene el equipo en ESTE PC (hecho por ellos, fuera del repo)

| Pieza | Estado | Qué hay que hacer con ella |
|---|---|---|
| Dataset de **200 pasadas** grabado en local | Terminándose | El robot va solo desde el reposo hasta la broca con un sistema aleatorio que dice dónde poner el taladro. Tiene variedad de velocidad; no tiene recuperaciones. Subirlo a Hugging Face al final (+3) |
| **ACT** entrenándose con ese dataset | En curso | Apuntar su checkpoint en `act.modelo` del yaml (§5) |
| **Detector OpenCV del círculo morado** (trasera del taladro, cámara de arriba) | Hecho | Enchufarlo en la visión del producto (§5) |
| **Matriz 5×3** sobre el tapete: postura del robot junto a la broca apoyada, marcada a mano | Hecha | Convertirla al formato que lee `garbi/producto/matriz.py` (§5). Es la base del respaldo y de los barridos |
| Postura de reposo, girado a la derecha | Conocida | Ponerla en `postura_reposo` del yaml |
| Arduino de la aspiradora | **Quizá no dé tiempo** | Sin Arduino: `aspiradora: null` y la aspiradora se enciende con el pie (la app avisa) |

Pregunta al usuario dónde está cada pieza (carpeta, nombre del archivo) si no lo encuentras.

## 3. Comportamiento acordado (manda sobre todo lo anterior)

Archivo `.plans/aspira/producto.md`; contratos en `garbi/producto/contrato.py`.

| Estado | Entra cuando | Qué hace | Aspiradora |
|---|---|---|---|
| REPOSO | Al encender, con «para» o al rearmar | Postura de reposo, girado a la derecha | No |
| ACERCAMIENTO | **Mano + taladro**, con el círculo morado quieto **1 s** (desde reposo) o **2 s** (desde despierto) | **La política** (ACT, o el respaldo círculo + matriz) despierta el brazo, lo despliega y lleva la boca a la punta de la broca | No |
| EN_BROCA | La política llega (deja de moverse) | Quieto junto a la broca | **Sí** |
| DESPIERTO | Mano + taladro se van más allá de un rango | Postura de espera; no vuelve a REPOSO hasta terminar los agujeros | No |
| LIMPIEZA_TABLA | Sin taladro en escena, tras ≥1 agujero y con tabla | Barrido completo de la tabla a altura fija | Sí |
| LIMPIEZA_TAPETE | Se retira la tabla, o se pide | Barrido fijo de todo el tapete (siempre el mismo) | Sí |
| APAGADO / EMERGENCIA | «Apágate» / seta (barra espaciadora) | Nada / quieto con par | No |

- **Una sola política ACT.** Se entrenó desde el reposo, así que para el 2.º agujero y siguientes Garbi vuelve
  primero a la postura de reposo y lanza ACT desde ahí (`act_desde: reposo`). Lo otro es `act_desde: despierto`.
- **Regla del usuario:** solo cuenta **mano + taladro juntos**. Ni la mano sola ni el taladro solo.
- **Respaldo plug-and-play:** si ACT va mal, `politica: circulo` en el yaml, o el selector de la app. Toma el centro
  del círculo morado, interpola la postura en la matriz y va con un movimiento suave. Puntúa menos, pero es fiable.

## 4. Código: qué es cada cosa

| Carpeta o archivo | Qué es | ¿Se usa en la demo? |
|---|---|---|
| `garbi/producto/` | **El producto final**: `config.py`, `matriz.py`, `politicas.py` (ACT y Círculo), `barridos.py`, `orquestador.py`, `vision.py`, `__main__.py` y `app/` (servidor aiohttp, página, LLM, seta) | **Sí** |
| `garbi/producto/garbi_producto.yaml` | **La única configuración que hay que tocar** | **Sí** |
| `garbi/real.py` | Robot real (`CuerpoReal`), cámaras con exposición fija y señal de la aspiradora | Sí (lo usa el producto) |
| `firmware/garbi_aspiradora/` | Arduino con relé y latido (`1`/`0` cada 200 ms; sin latido 1 s, se apaga) | Si hay Arduino |
| `garbi/ciclo_final.py`, `garbi/percepcion.py`, `garbi/acercamiento.py`… | Versión anterior, más completa y probada en simulación MuJoCo (5/5 con percepción) | No: es material de apoyo para el pitch (diseño, simulación) |
| `garbi/maqueta.py`, `garbi/ver.py` | Animación y visor 3D de la simulación | Para el vídeo o el pitch |
| `herramientas/` | Instalador de Windows, cámaras, colores, calibración, prueba del robot, teleoperación, entrenamiento | Algunas (§6) |
| `docs/plan-entrega.md` | Plan de entrega: vídeo, datos, Hub, repo, presentación, producto e industrialización | Sí |
| `entrega/` | Marca (logo, guía), guion y tomas del vídeo, y el montador automático `herramientas/montar_video.py` | Sí (si aún no está, haz `git pull`: la nube lo está terminando) |
| `docs/garbi-guia-hackathon.md` | Guía paso a paso del sitio | Sí |

## 5. Integración con lo del equipo (lo primero que hay que hacer)

1. **Configuración:** abre `garbi/producto/garbi_producto.yaml` y rellena lo marcado «MEDIR»:
   - **`puertos.follower`:** en Windows, `COMx` (`lerobot-find-port`).
   - **`camaras.top` y `camaras.wrist`:** índices (`python herramientas/garbi_camaras.py --listar`).
   - **`id_robot`:** el id con el que calibraron el follower.
   - **`postura_reposo`:** léela con el robot colocado (`python herramientas/garbi_probar_robot.py --puerto COMx --solo-leer`).
   - **`postura_despierto`:** una postura de espera segura.
2. **Matriz 5×3:** pide al usuario el archivo o la foto y conviértela al formato del docstring de
   `garbi/producto/matriz.py`:
   - **archivo:** CSV o JSON;
   - **posición:** columnas `u`, `v` (px de la cámara de arriba) **o** `x`, `y` (mm del tapete);
   - **articulaciones:** 6 columnas (`shoulder_pan`, `shoulder_lift`, `elbow_flex`, `wrist_flex`, `wrist_roll`,
     `gripper`; también se aceptan con `.pos` y otros alias), en grados de LeRobot.

   Ponla en `matriz.ruta`. Detecta sola la rejilla 5×3 e interpola por celdas. **Ojo:** aclara si la posición de la
   matriz es la del círculo morado o la de la punta de la broca, porque el círculo está en la trasera del taladro y
   hay paralaje. El respaldo usa el centro del círculo.
3. **Detector morado del equipo**, dos opciones:
   - **(a)** su clase o función, con `detectar(img) -> (uv, radio) | None`, en `vision.circulo.detector:
     "paquete.modulo:Nombre"` (con `orden_color: bgr` si espera BGR);
   - **(b)** sus valores HSV en `garbi/config_vision.yaml` → `parametros.morado`, o en el yaml del producto,
     `vision.circulo`.

   Compruébalo con `python -m garbi.producto.vision --camara N`.
4. **Tapete:**
   ```powershell
   python -m garbi.producto.vision --marcar-tapete --camara N
   ```
   4 clics y Enter; escribe `tapete_px` en el yaml.
5. **ACT:** pon en `act.modelo` la carpeta del checkpoint (`…/checkpoints/last/pretrained_model`).
   - Las cámaras del modelo se mapean solas a `top` y `wrist`; si no, `act.camaras: {nombre_dataset: top, ...}`.
   - **Comprueba en el dataset qué es `observation.state`.** Si grabaron con LeRobot, es la postura medida
     (`act.estado: medido`, el valor por defecto).
   - **Comprueba que la postura de reposo del yaml sea la misma desde la que empiezan los episodios.**
6. **Barridos:** ajusta `barridos.offset_tabla` y `offset_tapete`, que son la altura de barrido sumada a la postura de
   la matriz. Pruébalos primero con `--sin-robot` y luego despacio.

## 6. Comandos (PowerShell, en la raíz del repo, con `.venv\Scripts\activate`)

| Para qué | Comando |
|---|---|
| Instalar desde cero | `powershell -ExecutionPolicy Bypass -File herramientas\instalar_windows.ps1` |
| Ver la app sin robot (demo) | `python -m garbi.producto.app --demo` (http://localhost:8800) |
| Demo del orquestador sin app | `python -m garbi.producto --demo` |
| Visión en vivo (círculo, manos, tabla) | `python -m garbi.producto.vision --camara 0` |
| Marcar el tapete | `python -m garbi.producto.vision --marcar-tapete --camara 0` |
| Producto real (robot, visión, política, app) | `python -m garbi.producto` (y `garbi.bat` en Windows cuando llegue la integración) |
| Probar robot y aspiradora | `python herramientas/garbi_probar_robot.py --puerto COMx [--aspiradora COMy]` |
| Probar el Arduino | `python herramientas/probar_aspiradora.py COMy` |
| Tests del producto (sin hardware) | `python -m pytest -q tests/test_producto_*.py` |
| Montar el vídeo con los clips | Ver `entrega/video/` (README o GUION) |

La nube está terminando el arranque real completo con la app integrada:
- el modo `--sin-robot`, para ajustar sin mover nada;
- la herramienta para comprobar la matriz (`python -m garbi.producto.matriz --comprobar`);
- el cambio ACT ↔ Círculo desde la app.

Haz `git pull` antes de buscarlos.

## 7. App, LLM y seta

- **App:** `http://localhost:8800`. Con `--host 0.0.0.0` se abre desde una tablet.
  - estado grande con color, cámaras en vivo con detecciones y panel «Tecnologías funcionando»;
  - botones y chat, y aviso grande de aspiradora manual;
  - indicadores de sesión, exportación a CSV y modo Taller / Fábrica.
- **LLM:** Claude por la API, con la clave en la variable `ANTHROPIC_API_KEY`. **Nunca la pongas en el repo.** Sin
  clave o sin red, un respaldo por palabras clave entiende «enciéndete», «apágate», «limpia la tabla», «limpia el
  tapete» y «para». El chat nunca lanza la emergencia.
- **Seta = barra espaciadora** (la seta USB del equipo actúa como tecla espacio). Funciona en la página y fuera de
  ella con `pynput` (`pip install pynput`). Mientras se escribe en el chat, la seta física se ignora; queda el botón
  rojo.

## 8. Reglas

- Español siempre. Commits `tipo: descripción`, sin líneas de atribución, en la rama de arriba.
- No subir datasets, modelos, `.venv`, `capturas/`, fotos de `calib/` ni claves. Los datasets y modelos van a
  Hugging Face.
- **Seguridad con el robot real:**
  - avisa antes de cualquier comando que mueva el brazo y pide que no haya manos en la mesa;
  - la primera vez de cada movimiento, a poca velocidad;
  - Ctrl+C y la seta dejan el brazo quieto con par;
  - nunca quites el par con el brazo en alto.
- No cambies el comportamiento acordado (§3) sin preguntar. Si algo no funciona en el robot real, di qué y por qué,
  con datos.

## 9. Prioridades hasta la entrega (en este orden)

1. **Integración con lo del equipo (§5)** y `python -m garbi.producto` con `politica: circulo`. El respaldo tiene que
   funcionar SIEMPRE.
2. **ACT:** cargar el checkpoint, probar 10 acercamientos y apuntar **X/10** en `.plans/aspira/datos-sitio.md`, con
   episodios, descartes y pasos. Si va bien, ACT en la demo; si no, el círculo, y se dice.
3. **Ensayo de los 5 intentos** de la tarea completa: coger el taladro → acercamiento → taladrar → retirar → los
   agujeros que sean → limpieza de la tabla. Apunta los fallos y arregla el que más falla.
4. **Grabar las tomas del vídeo** (`entrega/video/TOMAS.md`) y montarlo con el montador.
5. **Subir el dataset a Hugging Face** con su ficha (+3), y el README del repo con los comandos que funcionan (+2).
6. Presentación de 3 minutos (`docs/plan-entrega.md`, secciones 3, 3 bis y 5).
