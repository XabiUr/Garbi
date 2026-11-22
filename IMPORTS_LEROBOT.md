# Imports de LeRobot 0.7.0

Basado en la inspección de los scripts oficiales (lerobot-record, lerobot-teleoperate, lerobot-rollout), estos son los imports que usaremos:

## Robot y Teleoperador

```python
from lerobot.robots import make_robot_from_config, Robot
from lerobot.robots.so_follower import SO100Follower, SO100FollowerConfig
from lerobot.teleoperators import make_teleoperator_from_config, Teleoperator
from lerobot.teleoperators.so_leader import SO100Leader, SO100LeaderConfig
```

## Tipos de datos

```python
from lerobot.lerobot_types import RobotAction, RobotObservation
```

**Nota:** `RobotObservation` y `RobotAction` son **dicts** con claves como:
- Motores: `"shoulder_pan.pos"`, `"shoulder_lift.pos"`, etc.
- Cámaras: `"front"`, `"gripper"`, etc. (imágenes en **RGB**, numpy arrays con shape (H, W, 3))

## Cámaras

```python
from lerobot.cameras import make_cameras_from_configs
from lerobot.cameras.opencv import OpenCVCameraConfig
```

## Datasets

```python
from lerobot.datasets import LeRobotDataset, VideoEncodingManager, create_initial_features
```

## Procesadores (para ACT)

```python
from lerobot.processor import RobotProcessorPipeline, make_default_processors
```

## Políticas (para ACT)

```python
from lerobot.policy import Policy
```

---

## Flujo de uso

### 1. Crear robot

```python
config = SO100FollowerConfig(
    robot_id="so100_follower",
    port="/dev/tty.usbmodem5A7A0589611",
    cameras={
        "front": OpenCVCameraConfig(
            index_or_path=0,
            width=640,
            height=480,
            fps=30
        ),
        "gripper": OpenCVCameraConfig(
            index_or_path=1,
            width=640,
            height=480,
            fps=30
        )
    },
    use_degrees=False  # Si True: grados, si False: normalizado [-100, 100]
)

robot = SO100Follower(config)
robot.connect(calibrate=False)  # calibrate=False usa calibración guardada
```

### 2. Leer observación

```python
obs = robot.get_observation()
# obs es un dict:
# {
#   "shoulder_pan.pos": float,
#   "shoulder_lift.pos": float,
#   "elbow_flex.pos": float,
#   "wrist_flex.pos": float,
#   "wrist_roll.pos": float,
#   "gripper.pos": float,
#   "front": numpy.ndarray shape (480, 640, 3), dtype uint8, RGB,
#   "gripper": numpy.ndarray shape (480, 640, 3), dtype uint8, RGB
# }
```

### 3. Enviar acción

```python
action = {
    "shoulder_pan.pos": float,
    "shoulder_lift.pos": float,
    "elbow_flex.pos": float,
    "wrist_flex.pos": float,
    "wrist_roll.pos": float,
    "gripper.pos": float
}
robot.send_action(action)
```

### 4. Desconectar

```python
robot.disconnect()
```

---

## Unidades

**IMPORTANTE:** Las unidades dependen de `use_degrees` en el config:
- `use_degrees=True`: Los valores de `.pos` están en **grados** (0-360)
- `use_degrees=False`: Los valores de `.pos` están **normalizados** en el rango [-100, 100]

La calibración de SenseCraft probablemente usa `use_degrees=False` (normalizado).

**Para el gripper:** Siempre normalizado [0, 100] independientemente de `use_degrees`.

---

## Cámaras

- Se abren **una sola vez** al hacer `robot.connect()`
- Las imágenes vienen en **RGB** (no BGR como OpenCV por defecto)
- Para mostrar con `cv2.imshow()`: convertir a BGR con `cv2.cvtColor(img, cv2.COLOR_RGB2BGR)`

---

## Dataset

```python
from lerobot.datasets import LeRobotDataset

# Crear dataset
dataset = LeRobotDataset.create(
    repo_id="Xaflas/nombre-dataset",
    root="data",
    robot_type="so_follower",
    fps=30,
    features={
        "shoulder_pan.pos": float,
        # ... otros motores
        "front": (480, 640, 3),
        "gripper": (480, 640, 3)
    }
)

# Añadir frame
dataset.add_frame({
    "observation.state": {"shoulder_pan.pos": 0.0, ...},
    "observation.images": {"front": img_rgb, "gripper": img_rgb},
    "action": {"shoulder_pan.pos": 0.0, ...}
})

# Terminar episodio
dataset.save_episode()

# Subir a Hub
dataset.push_to_hub()
```
