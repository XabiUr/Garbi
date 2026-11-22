# Garbi · simulación completa

Compañero de escritorio que aspira mientras taladras: se acerca al taladro quieto sin chocar, se queda quieto con la
aspiradora encendida mientras taladras y, al retirar el taladro, limpia el agujero nuevo (aunque hayas movido la
tabla) o la viruta de la alfombrilla cuando se lo pides. Concepto en
[.plans/aspira/BRIEF-aspira.md](../.plans/aspira/BRIEF-aspira.md).

## Piezas

| Módulo | Qué hace |
|---|---|
| `contrato.py` | Medidas, posiciones, cámaras, órdenes del VLA. Todo en mm y grados de LeRobot. |
| `escena.py`, `mundo.py` | Escena MuJoCo (SO-101 con boca, alfombrilla y tabla con ArUco, taladro con bola naranja, viruta) e interfaz del robot y del «juez». |
| `control.py` | IK de la boca y gestos programados (aparcar, acercarse al taladro, zigzag, limpiar la tabla). |
| `robot_vivo.py` | Orquestador a 30 Hz: máquina de estados, órdenes de voz, seguridad. Percepción y habilidad intercambiables. |
| `arduino.py` | Protocolo con el Arduino de la aspiradora y latido de seguridad (versión virtual para simular). |
| `vision.py` | Visión clásica con la cámara fija: calibración, tabla, punta de la broca y viruta. |
| `escenario.py`, `video.py` | Demo completa con el juez simulado; vídeo con las dos cámaras y el estado. |
| `demostraciones.py` | Dataset LeRobot de limpieza (filtro «aprende del mejor»). |
| `politica.py` | Habilidad de limpieza con SmolVLA/ACT, envuelta por la supervisión programada. |

## Comandos

Render sin pantalla: `MUJOCO_GL=egl` (o `osmesa`). En la nube, `herramientas/setup_nube.sh` instala las librerías.

```bash
.venv/bin/python -m pytest -q tests/test_garbi.py tests/test_garbi_vision.py tests/test_garbi_vla.py
```

```bash
.venv/bin/python -m garbi.video --semilla 1 --vision --salida salidas/garbi_demo_vision.mp4
```

```bash
.venv/bin/python -m garbi.demostraciones --salida datos/garbi_sim --episodios 60
```

Vídeo de referencia de lo que tiene que aprender el VLA (demostraciones de las dos órdenes):

```bash
.venv/bin/python -m garbi.video --demostraciones 6 --semilla 10 --salida salidas/garbi_demostraciones_vla.mp4
```

**Cómo entrenarlo** (con el robot real, en el hackathon): [entrenar.md](entrenar.md). Aquí no se entrena.

Usar la política en el ciclo:

```python
from garbi.control import ControlBoca
from garbi.escenario import ejecutar
from garbi.mundo import MundoGarbi
from garbi.politica import HabilidadVLA
from garbi.vision import PercepcionVision

m = MundoGarbi(render=True)
informe = ejecutar(0, mundo=m, percepcion=PercepcionVision,
                   habilidad=HabilidadVLA("salidas/entreno_smolvla_garbi", ControlBoca(m.cin)))
```

## Resultados en simulación (19-11, boquilla a 30°)

Diseño y medidas en [.plans/aspira/montaje-boquilla.md](../.plans/aspira/montaje-boquilla.md):
- Boquilla recta de 110 mm a 30°.
- Llegada de lado, eligiendo el lado con holgura con el taladro.
- Cámara del robot al costado del tubo.

Resultados:
- **Apunto:** la cámara del robot da la punta con 1-2 mm de error, también con el taladro inclinado 8°, cuando la bola
  naranja engaña a la de arriba en 32-36 mm.
- **Ciclo completo con visión:** 12 semillas (vertical e inclinado 8°), 11 completas. La boca queda a 33-35 mm de la
  broca. La viruta del agujero queda a 0 (al taladrar ya se aspira casi toda) y la de la alfombrilla también. En la
  otra, el taladro queda fuera del alcance y Garbi lo avisa.
- **Visión de arriba:** cámara ~2 mm, tabla ≤ 2 mm y 3°.

Vídeos:

```bash
.venv/bin/python -m garbi.video --semilla 2 --vision --inclinacion 8 --salida salidas/garbi_demo_taladro_inclinado.mp4
```
