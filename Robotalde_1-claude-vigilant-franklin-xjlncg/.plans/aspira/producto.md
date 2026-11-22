# Garbi · producto final (plan, 21-11)

Sustituye a [solucion-final.md](solucion-final.md) para el robot real. Contratos: `garbi/producto/contrato.py`.

## Lo que ya tiene el equipo (en el PC del compañero)

- Detector OpenCV de un **círculo morado** en la trasera del taladro (cámara de arriba).
- Una **matriz** sobre el tapete: puntos marcados a mano con la postura del robot junto a la broca apoyada.
- Dataset de **200 pasadas** grabado de forma automática: un sistema dice dónde poner el taladro y el robot va desde el
  reposo hasta la broca. Tiene variedad de velocidad y no tiene recuperaciones.
- ACT entrenándose con ese dataset.

## Comportamiento

| Estado | Entra | Hace | Aspiradora | Quién mueve |
|---|---|---|---|---|
| APAGADO | «Apágate» | Nada | No | — |
| REPOSO | «Enciéndete», «para» o rearmar | Postura de reposo, girado a la derecha | No | Fijo |
| ACERCAMIENTO | Mano + taladro, con el círculo quieto 1 s (desde REPOSO) o 2 s (desde DESPIERTO) | Despierta, se despliega y acerca la boca a la punta de la broca | No (se enciende al llegar) | **La política: ACT o círculo + matriz** |
| EN_BROCA | La política llega | Quieto junto a la broca | **Sí** | — |
| DESPIERTO | Mano + taladro se van más allá de un rango | Postura de espera, sin volver a REPOSO hasta terminar | No | Fijo |
| LIMPIEZA_TABLA | No hay taladro en escena, ha habido agujeros y hay tabla | Barrido completo de la tabla a altura fija | Sí | Fijo (matriz) |
| LIMPIEZA_TAPETE | Se retira la tabla, o se pide | Barrido fijo de todo el tapete | Sí | Fijo |
| EMERGENCIA | Seta (barra espaciadora) | Quieto con par | No | — |

**Una sola política.** ACT está entrenado desde el reposo, así que para el segundo agujero y siguientes Garbi vuelve a
la postura de reposo con un movimiento fijo rápido y lanza ACT desde ahí. Es la misma situación que en el
entrenamiento. Se puede cambiar a «lanzar desde despierto» en la configuración.

**Respaldo plug-and-play.** La política «círculo» toma el centro del círculo morado, interpola la postura en la matriz
y va con una trayectoria suave. Se elige en la configuración o en la app, sin tocar código.

## Módulos

| P | Módulo | Archivos |
|---|---|---|
| 1 | Orquestador, las dos políticas, los barridos y la configuración | `garbi/producto/orquestador.py`, `politicas.py`, `matriz.py`, `barridos.py`, `config.py`, `garbi_producto.yaml` |
| 2 | Visión del producto: círculo morado y si está quieto, manos (MediaPipe) con la regla mano + taladro, tabla sobre el tapete, tapete fijo y dibujo de las detecciones | `garbi/producto/vision.py` |
| 3 | App: cámaras en vivo con las detecciones, estado y tecnologías, botones, chat con LLM (Claude, con respaldo sin conexión), seta en la barra espaciadora (navegador y global) | `garbi/producto/app/` |
| 4 | Programa principal y modo demo sin hardware | `python -m garbi.producto` |

## Pendiente del equipo

1. **Formato de la matriz:** columnas y unidades. ¿Es (u, v) en píxeles de la cámara de arriba, o (x, y) en mm del
   tapete? ¿Corresponde al círculo morado o a la punta de la broca?
2. **Dataset:** `repo_id`, nombres de las cámaras, y si `observation.state` es la postura medida (lo normal en LeRobot).
3. **Postura de reposo** (6 ángulos), índices de las cámaras y puertos.
4. **Código del detector morado,** o al menos sus valores HSV.
