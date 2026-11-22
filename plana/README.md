# Sistema de Control de Robot SO-101 con Seguimiento de Taladro

Sistema completo para detectar y seguir un taladro marcado con morado usando brazos robóticos SO-101.

## Inicio Rápido

Todos los archivos del proyecto están en este directorio. Para empezar:

```bash
cd /Users/xabier/Desktop/Hackathon/aspirador/plana
```

Luego sigue el workflow completo más abajo.

## Descripción General

Este proyecto implementa un sistema de control robótico que:
- Detecta un marcador morado en un taladro sostenido por una persona
- Sigue el taladro automáticamente usando control programado (CerebroZonas)
- Graba episodios de demostración automáticamente
- Entrena una política ACT con las demostraciones
- Ejecuta la política entrenada o usa control programado de respaldo

## Hardware Necesario

- 2× Brazos robóticos SO-101:
  - **Follower** (seguidor): `/dev/tty.usbmodem5A7A0589611`
  - **Leader** (líder): `/dev/tty.usbmodem5AB01797841`
- Webcam (índice 1 en macOS)
- Superficie azul (mantel) para contraste
- Taladro con marcador morado

## Dependencias

```bash
# LeRobot 0.7.0 ya debe estar instalado
pip install opencv-python numpy lerobot
```

## Workflow Completo

### Paso 1: Calibración de la Zona

Calibra la zona de trabajo (4 esquinas) y los valores HSV del morado:

```bash
# Con robot simulado (para probar)
python calibrar_zona.py --sin-robot

# Con robot real
python calibrar_zona.py --real
```

**Instrucciones:**
1. Haz clic en las 4 esquinas en orden: delante-izq, delante-der, detrás-der, detrás-izq
2. Ajusta los sliders HSV hasta que el marcador morado se detecte bien
3. Presiona 'G' para guardar → crea `zona.json` y actualiza `config.json`

**Salida:** `zona.json` con coordenadas de las esquinas

---

### Paso 2: Grabación de Posturas

Graba las 9 posturas de la cuadrícula 3×3 que el robot usará para interpolar:

```bash
# Modo teleoperación (mueves el líder, el seguidor imita)
python grabar_posturas.py --real

# Modo manual (desactiva torque, mueves el seguidor a mano)
python grabar_posturas.py --real --a-mano
```

**Cuadrícula de posturas:**
```
  7(0.0,1.0)  8(0.5,1.0)  9(1.0,1.0)
  4(0.0,0.5)  5(0.5,0.5)  6(1.0,0.5)
  1(0.0,0.0)  2(0.5,0.0)  3(1.0,0.0)
```

**Instrucciones:**
- Teclas **1-9**: Graba la postura en esa posición de la cuadrícula
- Tecla **R**: Graba postura de reposo (cuando no hay taladro)
- Tecla **Q**: Salir y guardar

**Salida:** `posturas.json` con las 9 posturas + reposo

---

### Paso 3: Test del Sistema Completo

Prueba el control automático con el supervisor:

```bash
# Con robot simulado
python supervisor.py --sin-robot --cerebro zonas

# Con robot real
python supervisor.py --real --cerebro zonas
```

**Controles del teclado:**
- **ESPACIO**: Parada de emergencia
- **C**: Continuar (desactiva parada)
- **Z**: Cambiar a CerebroZonas (programado)
- **A**: Cambiar a CerebroACT (política entrenada)
- **Q**: Salir

**Estados del robot:**
- `REPOSO`: Esperando taladro estable
- `ACTUANDO`: Siguiendo el taladro
- `VOLVIENDO`: Volviendo a reposo
- `PARADA`: Parada de emergencia activa

**Salida:** Logs CSV en `logs/supervisor_TIMESTAMP.csv`

---

### Paso 4: Grabación Automática del Dataset

Graba episodios de demostración automáticamente:

```bash
# Con robot real
python grabar_dataset_auto.py \
    --real \
    --nombre "TU_USUARIO/dataset-taladro" \
    --episodios 50

# Sin subir a Hugging Face (solo local)
python grabar_dataset_auto.py \
    --real \
    --nombre "TU_USUARIO/dataset-taladro" \
    --episodios 50 \
    --no-push
```

**Instrucciones:**
1. El script te pedirá que coloques el taladro en cada zona
2. Mueve el taladro lentamente cuando el robot lo siga
3. El robot grabará: reposo → aproximación → seguimiento → vuelta
4. Se graban automáticamente 50 episodios distribuidos uniformemente

**Estructura de cada episodio:**
- Reposo inicial (1s)
- Espera hasta detectar morado estable
- Aproximación y seguimiento (3s)
- Mantener objetivo (1.5s)
- Vuelta a reposo (2s)
- Reposo final (1s)

**Salida:** Dataset LeRobot en `data/dataset-taladro/` con estructura:
```
data/dataset-taladro/
├── meta/
│   └── info.json
├── videos/
│   ├── episode_000000_front.mp4
│   ├── episode_000000_gripper.mp4
│   └── ...
└── data/
    ├── episode_000000.parquet
    └── ...
```

---

### Paso 5: Entrenamiento de la Política ACT

Entrena la política ACT con el dataset grabado:

```bash
# Entrenar ACT (desde el directorio de LeRobot)
python lerobot/scripts/train.py \
    --dataset-repo-id TU_USUARIO/dataset-taladro \
    --policy act \
    --output-dir outputs/act-taladro \
    --num-epochs 1000 \
    --batch-size 8 \
    --learning-rate 1e-4 \
    --device mps  # 'mps' para Apple Silicon, 'cuda' para NVIDIA
```

**Parámetros recomendados:**
- `--num-epochs`: 500-1000 (depende del tamaño del dataset)
- `--batch-size`: 8 para Apple Silicon, 16-32 para NVIDIA
- `--device`: `mps` (Apple), `cuda` (NVIDIA), `cpu` (respaldo)

**Salida:** Modelo entrenado en `outputs/act-taladro/checkpoints/`

**Opcional:** Sube el modelo entrenado a Hugging Face:
```bash
huggingface-cli login  # Si no lo has hecho
python lerobot/scripts/push_to_hub.py \
    --repo-id TU_USUARIO/act-taladro \
    --local-dir outputs/act-taladro
```

---

### Paso 6: Ejecución con Política ACT

Ejecuta el supervisor con la política entrenada:

```bash
# Con modelo local
python supervisor.py \
    --real \
    --cerebro act \
    --modelo outputs/act-taladro

# Con modelo de Hugging Face
python supervisor.py \
    --real \
    --cerebro act \
    --modelo TU_USUARIO/act-taladro
```

**Cambio en tiempo real:**
- Presiona **Z** para cambiar a CerebroZonas (control programado)
- Presiona **A** para cambiar a CerebroACT (política entrenada)
- Útil para comparar rendimiento o respaldo si ACT falla

---

## Referencia de Comandos

### test_conexion.py
Verifica conexión con el robot y muestra video en vivo:

```bash
python test_conexion.py --sin-robot  # Simulado con webcam
python test_conexion.py --real       # Robot real
```

### calibrar_zona.py
Calibra zona de trabajo y HSV del morado:

```bash
python calibrar_zona.py --sin-robot
python calibrar_zona.py --real
```

### grabar_posturas.py
Graba 9 posturas + reposo:

```bash
python grabar_posturas.py --real           # Con teleoperación
python grabar_posturas.py --real --a-mano  # Modo manual
```

### supervisor.py
Control principal con estado y seguridad:

```bash
python supervisor.py --sin-robot --cerebro zonas
python supervisor.py --real --cerebro zonas
python supervisor.py --real --cerebro act --modelo PATH_O_REPO
```

### grabar_dataset_auto.py
Grabación automática de episodios:

```bash
python grabar_dataset_auto.py --real --nombre USER/dataset --episodios 50
python grabar_dataset_auto.py --real --nombre USER/dataset --episodios 50 --no-push
```

---

## Archivos de Configuración

### config.json
Configuración central del sistema:
- Puertos de robots (follower y leader)
- Índices y resolución de cámaras
- Valores HSV del morado
- Parámetros de seguridad (límites, paso máximo)
- Tiempos de espera y suavizado

### zona.json
Coordenadas de las 4 esquinas de la zona de trabajo (en píxeles).
Generado por `calibrar_zona.py`.

### posturas.json
9 posturas de la cuadrícula 3×3 + postura de reposo.
Generado por `grabar_posturas.py`.

Estructura:
```json
{
  "posturas": {
    "1": {"shoulder_pan.pos": ..., "shoulder_lift.pos": ..., ...},
    "2": {...},
    ...
    "9": {...}
  },
  "reposo": {"shoulder_pan.pos": ..., ...},
  "metadata": {
    "orden": "1-9 corresponden a cuadrícula 3x3 en (u,v)",
    "coordenadas": {
      "1": [0.0, 0.0],
      ...
    }
  }
}
```

---

## Arquitectura del Sistema

### Módulos Principales

**percepcion.py** - DetectorMorado
- Detecta marcador morado con HSV
- Transforma píxeles → (u,v) normalizado [0,1] con homografía
- Suavizado exponencial (alpha=0.3)
- Memoria de 1s (mantiene última posición)
- Detección de estabilidad (0.5s sin movimiento)

**cerebros.py** - Controladores
- `CerebroZonas`: Interpolación bilineal entre 9 posturas
- `CerebroACT`: Ejecuta política ACT entrenada
- Interfaz común: `reset()` y `paso(obs, percepcion) -> accion`

**seguridad.py** - SistemaSeguridad
- Límites por articulación (desde posturas + margen)
- Paso máximo por ciclo (5.0 por defecto)
- Parada de emergencia (congela todo)
- Validación de acciones antes de enviar al robot

**supervisor.py** - Orquestador Principal
- Máquina de estados: REPOSO, ACTUANDO, VOLVIENDO, PARADA
- Bucle de control a 30 Hz
- Logging CSV con todas las observaciones y acciones
- Controles de teclado en tiempo real
- Visualización con OpenCV

---

## Sistema de Seguridad

### Límites de Articulaciones
Calculados automáticamente desde las posturas grabadas + margen del 5%:
- Si una acción excede los límites, se recorta al rango válido
- Gripper: [0, 100]
- Otros motores: [-100, 100] (normalizados)

### Paso Máximo por Ciclo
Limita el cambio máximo de posición en cada ciclo (default: 5.0):
- Evita movimientos bruscos que puedan dañar el robot
- Si el cerebro pide un paso mayor, se limita gradualmente

### Parada de Emergencia
- **ESPACIO**: Activa parada (congela todas las articulaciones)
- **C**: Desactiva parada y continúa
- En estado PARADA, el robot mantiene la posición actual

---

## Troubleshooting

### Cámara no funciona / frames negros
1. Verifica el índice de cámara en `config.json`
   - En macOS, prueba índices 0, 1, 2
   - Cambia `"index_or_path": 1` si no funciona con 0
2. Aumenta tiempo de estabilización si las primeras frames son malas
3. En macOS, usa backend AVFoundation (ya configurado en el código)

### Detección de morado no funciona
1. Ejecuta `calibrar_zona.py` y ajusta sliders HSV
2. Asegúrate de tener buena iluminación
3. El morado debe contrastar bien con el fondo azul
4. Valores típicos: H[130-150], S[100-255], V[50-255]

### Robot no se mueve
1. Verifica conexiones USB y puertos en `config.json`
2. Comprueba que los archivos de calibración existen en `~/.cache/lerobot/calibration/`
3. Revisa logs de errores en la terminal
4. Presiona **C** si está en estado PARADA

### Movimientos bruscos
1. Reduce `paso_maximo_por_ciclo` en `config.json` (default: 5.0 → prueba 3.0)
2. Aumenta suavizado en percepción: `alpha` más bajo (0.3 → 0.2)
3. Verifica que las posturas grabadas estén bien distribuidas

### ACT policy no converge
1. Graba más episodios (mínimo 50, ideal 100-200)
2. Asegúrate de que los episodios cubren toda la zona uniformemente
3. Aumenta `--num-epochs` (1000-2000)
4. Reduce `--learning-rate` (1e-4 → 5e-5)

### Dataset corrupto o incompleto
1. Verifica que `posturas.json` y `zona.json` existen antes de grabar
2. Revisa que las cámaras funcionan con `test_conexion.py`
3. Usa `--no-push` para grabar localmente primero
4. Inspecciona videos en `data/DATASET_NAME/videos/`

---

## Formato del Dataset LeRobot

Cada frame contiene:

```python
{
    # Estado del robot (articulaciones)
    "observation.state.shoulder_pan.pos": float,
    "observation.state.shoulder_lift.pos": float,
    "observation.state.elbow_flex.pos": float,
    "observation.state.wrist_flex.pos": float,
    "observation.state.wrist_roll.pos": float,
    "observation.state.gripper.pos": float,

    # Imágenes (RGB, numpy arrays)
    "observation.images.front": np.ndarray,     # (H, W, 3)
    "observation.images.gripper": np.ndarray,   # (H, W, 3)

    # Acción (articulaciones objetivo)
    "action.shoulder_pan.pos": float,
    "action.shoulder_lift.pos": float,
    "action.elbow_flex.pos": float,
    "action.wrist_flex.pos": float,
    "action.wrist_roll.pos": float,
    "action.gripper.pos": float,
}
```

Frecuencia: 30 FPS

---

## Notas Técnicas

### Normalización de Motores
- Todos los motores usan `use_degrees=False` → rango normalizado [-100, 100]
- Gripper: [0, 100] (0=cerrado, 100=abierto)
- Esto facilita el entrenamiento de ACT

### Formato de Imágenes
- El robot devuelve imágenes en **RGB** (no BGR)
- Para mostrar con OpenCV, convertir: `cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)`
- Para ACT, normalizar a [0, 1]: `img_tensor = torch.from_numpy(img_rgb).float() / 255.0`

### Transformación de Perspectiva
- Homografía 4-puntos convierte píxeles → (u,v) ∈ [0,1]²
- (u,v) = (0,0): esquina delantera-izquierda
- (u,v) = (1,1): esquina trasera-derecha
- Permite interpolación bilineal en la cuadrícula 3×3

### Suavizado y Memoria
- Suavizado exponencial: `u_smooth = alpha * u_new + (1-alpha) * u_prev`
- Memoria: mantiene última posición válida por 1s
- Estabilidad: requiere 0.5s sin movimiento antes de cambiar a ACTUANDO

---

## Workflow Recomendado para el Hackathon

### Fase 1: Setup Inicial (30 min)
1. Conectar robots y verificar puertos
2. Conectar webcam y verificar índice
3. Ejecutar `test_conexion.py --real` para validar todo

### Fase 2: Calibración (20 min)
1. Colocar mantel azul
2. Ejecutar `calibrar_zona.py --real`
3. Marcar 4 esquinas de la zona
4. Ajustar HSV hasta detectar bien el morado

### Fase 3: Grabación de Posturas (30 min)
1. Ejecutar `grabar_posturas.py --real --a-mano`
2. Mover el brazo a las 9 posiciones
3. Presionar teclas 1-9 en cada posición
4. Grabar reposo con R

### Fase 4: Test del Sistema (20 min)
1. Ejecutar `supervisor.py --real --cerebro zonas`
2. Verificar que el robot sigue el taladro
3. Ajustar parámetros si es necesario

### Fase 5: Grabación del Dataset (1-2 horas)
1. Ejecutar `grabar_dataset_auto.py --real --nombre USER/dataset --episodios 50`
2. Seguir instrucciones para cada zona
3. Mover el taladro suavemente durante grabación

### Fase 6: Entrenamiento (2-4 horas)
1. Entrenar ACT en segundo plano
2. Monitorear pérdida y checkpoints
3. Usar tiempo para ajustes del sistema

### Fase 7: Evaluación (30 min)
1. Ejecutar `supervisor.py --real --cerebro act --modelo PATH`
2. Comparar con CerebroZonas (presionar Z/A)
3. Ajustar y re-entrenar si necesario

**Tiempo total estimado: 5-8 horas**

---

## Comandos Rápidos (Cheat Sheet)

```bash
# 1. Test conexión
python test_conexion.py --real

# 2. Calibrar zona
python calibrar_zona.py --real
# Clic en 4 esquinas, ajustar HSV, presionar 'G'

# 3. Grabar posturas (modo manual)
python grabar_posturas.py --real --a-mano
# Mover brazo, presionar 1-9 y R

# 4. Test supervisor
python supervisor.py --real --cerebro zonas
# ESPACIO=parada, C=continuar, Q=salir

# 5. Grabar dataset
python grabar_dataset_auto.py --real --nombre USER/dataset --episodios 50

# 6. Entrenar ACT
python lerobot/scripts/train.py \
    --dataset-repo-id USER/dataset \
    --policy act \
    --output-dir outputs/act \
    --num-epochs 1000 \
    --device mps

# 7. Ejecutar ACT
python supervisor.py --real --cerebro act --modelo outputs/act
```

---

## Contribuciones

Este proyecto fue desarrollado para un hackathon usando LeRobot 0.7.0.

---

## Licencia

MIT License

---

## Contacto

Para problemas o preguntas, abre un issue en el repositorio.
