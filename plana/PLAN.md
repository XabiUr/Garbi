# PLAN - Arquitectura del Sistema de Control de Robot SO-101

## 🎯 Objetivo

Sistema de control robótico para aspirar/limpiar cerca de un taladro marcado con un círculo morado, usando detección visual y control programado (CerebroZonas) o aprendido (CerebroACT).

## 📐 Arquitectura General

```
┌─────────────────────────────────────────────────────────────┐
│                       SUPERVISOR                             │
│  ┌─────────────┐  ┌──────────┐  ┌─────────────┐           │
│  │  Percepción │→│  Cerebro  │→│  Seguridad  │→ Robot     │
│  │  (Detector) │  │  (Zonas/  │  │  (Límites) │           │
│  │             │  │   ACT)    │  │            │           │
│  └─────────────┘  └──────────┘  └─────────────┘           │
│          ↓              ↓              ↓                     │
│      Percepción     Acción        Acción segura             │
│      (u,v,...)    objetivo       + validada                 │
└─────────────────────────────────────────────────────────────┘
```

## 🔄 Máquina de Estados del Supervisor

### Estados

1. **REPOSO**: Esperando morado estable y dentro de zona
2. **YENDO_A_INTERMEDIA**: Va a posición intermedia fija (segura, alta)
3. **APROXIMANDO**: Aproximación con altura segura, siguiendo X-Y del taladro
4. **ACTUANDO**: Bajada gradual desde aproximación a posición de trabajo
5. **FIJO** (nuevo, modo sin --seguir): Mantiene postura fija sin consultar cerebro
6. **EN_OBJETIVO** (modo --seguir): Seguimiento continuo cerca del taladro
7. **LEVANTANDO**: Levanta antes de volver a reposo
8. **VOLVIENDO**: Volver a reposo suavemente
9. **PARADA**: Parada de emergencia (ESPACIO)

### Flujos

#### Modo **Sin --seguir** (default, posición fija):
```
REPOSO → YENDO_A_INTERMEDIA → APROXIMANDO → ACTUANDO → FIJO → LEVANTANDO → VOLVIENDO → REPOSO
```

#### Modo **Con --seguir** (seguimiento continuo):
```
REPOSO → YENDO_A_INTERMEDIA → APROXIMANDO → ACTUANDO → EN_OBJETIVO → LEVANTANDO → VOLVIENDO → REPOSO
                                                            ↓
                                                      (detecta movimiento)
                                                            ↓
                                                       APROXIMANDO
```

### Transiciones Clave

#### Modo sin --seguir:
- **ACTUANDO → FIJO**: Cuando la acción se estabiliza (cambio < umbral durante ~1s)
- **FIJO → LEVANTANDO**: Si el taladro desaparece por más de 1.5s

#### Modo con --seguir:
- **ACTUANDO → EN_OBJETIVO**: Después de completar bajada gradual
- **EN_OBJETIVO → APROXIMANDO**: Si el taladro se mueve significativamente
- **EN_OBJETIVO → LEVANTANDO**: Si el taladro desaparece por más de 1.5s

## 🧠 Cerebros (Controladores)

### CerebroZonas (Programado)

**Estrategia**: Interpolación bilineal entre posturas de cuadrícula 5×3

**Comportamiento nuevo**:
- **Congela objetivo (u,v)** al primer paso del episodio
- No actualiza el objetivo durante aproximación/actuación
- El objetivo congelado se usa para toda la trayectoria
- Reset resetea el objetivo congelado

**Grid 5×3**:
```
13(0,2)  14(1,2)  15(2,2)  16(3,2)  17(4,2)   <- Fila trasera (v=2)
 8(0,1)   9(1,1)  10(2,1)  11(3,1)  12(4,1)   <- Fila media (v=1)
 3(0,0)   4(1,0)   5(2,0)   6(3,0)   7(4,0)   <- Fila frontal (v=0)
 ^                                        ^
izq (u=0)                             der (u=4)
```

**Offsets adaptativos**:
- Zonas traseras (v > 0.6, 13-17): offset_distancia = 40% del configurado
- Otras zonas: offset_distancia = 100%

### CerebroACT (Aprendido)

- Carga modelo ACT entrenado
- Recibe imágenes (cenital + gripper) + estado articulaciones
- Genera acciones directamente desde la política
- **Debe aprender implícitamente** la estrategia de posición fija o seguimiento según los datos de entrenamiento

## 🔍 Percepción

### DetectorMorado

**Entrada**: Imagen RGB de cámara cenital

**Salida**:
```python
{
    "hay_taladro": bool,          # Detectado círculo morado
    "estable": bool,              # Sin movimiento por 0.5s
    "u": float,                   # Coordenada horizontal [0,1]
    "v": float,                   # Coordenada profundidad [0,1]
    "dentro_zona": bool,          # Está en zona calibrada (con margen)
    "cx_px": int,                 # Centro X en píxeles
    "cy_px": int                  # Centro Y en píxeles
}
```

**Características**:
- Detección HSV configurable
- Transformación homográfica 4-puntos (píxeles → (u,v))
- Suavizado exponencial (alpha=0.3)
- Margen de zona: acepta (u,v) entre [-0.15, 1.15]
- Memoria: mantiene última posición por 1s

## 🛡️ Seguridad

### SistemaSeguridad

**Funciones**:
1. **Límites por articulación**: Calculados desde posturas + margen 5%
2. **Paso máximo**: Límite de cambio por ciclo (1.5°/ciclo)
3. **Parada de emergencia**: Congela todas las articulaciones
4. **Validación**: Recorta acciones fuera de límites

## 📊 Configuración

### config.json (nuevos parámetros)

```json
{
  "supervisor": {
    "seguir": false,                      // Modo seguimiento (false = posición fija)
    "umbral_estabilizacion": 0.5,         // Cambio máximo para considerar estable (grados)
    "tiempo_estabilizacion_s": 1.0,       // Tiempo estable antes de FIJO
    "umbral_movimiento_taladro": 0.05,    // Distancia (u,v) para detectar movimiento
    "posicion_intermedia": { ... }        // Posición fija previa a aproximación
  },
  "seguridad": {
    "paso_maximo_por_ciclo": 1.5,
    "velocidad_reposo": 0.8,
    "offset_distancia_aproximacion": 16.0,
    "offset_aproximacion_altura": -55.0,
    // ... otros offsets
  }
}
```

## 📹 Grabación de Dataset

### Comportamiento Nuevo (modo sin --seguir)

**Proceso**:
1. Espera morado estable → **guarda posición inicial (u,v)**
2. Reset cerebro → congela objetivo en primer paso
3. Durante actuación y quieto: **detecta movimiento** respecto a posición inicial
4. Si movimiento > umbral → **aviso en pantalla**: "TALADRO MOVIDO - Pulsa R para descartar"
5. Al finalizar episodio → aviso en consola si se detectó movimiento

**Teclas**:
- **N**: Siguiente episodio
- **R**: Descartar último episodio (usar si el taladro se movió accidentalmente)
- **Q**: Terminar y guardar

### Comportamiento Antiguo (modo con --seguir)

- No congela objetivo, actualiza continuamente
- Permite movimiento del taladro (para enseñar reactividad)
- No detecta ni avisa de movimiento

## 🎓 Entrenamiento ACT

### Recomendaciones

**Para modo posición fija (sin --seguir)**:
- Grabar 50-100 episodios sin mover el taladro
- Dataset debe cubrir las 15 zonas uniformemente
- ACT aprenderá a ir a posición fija según (u,v) detectado

**Para modo seguimiento (con --seguir)**:
- Grabar 50-100 episodios moviendo el taladro durante fase 4
- ACT aprenderá a seguir el movimiento del taladro
- Requiere más episodios para robustez (100-200)

## 🔧 Uso

### Supervisor

```bash
# Modo posición fija (default)
python supervisor.py --cerebro zonas --real

# Modo seguimiento continuo
python supervisor.py --cerebro zonas --real --seguir

# Con ACT entrenado
python supervisor.py --cerebro act --modelo outputs/act-taladro --real
```

### Grabación de Dataset

```bash
# Modo posición fija (default)
python grabar_dataset_auto.py --nombre taladro-fijo --episodios 50 --real

# Modo seguimiento continuo
python grabar_dataset_auto.py --nombre taladro-seguir --episodios 50 --real --seguir
```

## 🗂️ Archivos Principales

```
plana/
├── config.json              # Configuración central (con nuevos parámetros)
├── supervisor.py            # Orquestador principal (+ estado FIJO)
├── cerebros.py              # Controladores (Zonas con congelación, ACT)
├── percepcion.py            # Detector de círculo morado
├── seguridad.py             # Validación y límites
├── grabar_dataset_auto.py   # Grabación automática (+ detección movimiento)
├── calibrar_zona.py         # Calibración de zona
├── grabar_posturas.py       # Grabación de posturas 5×3
├── posturas.json            # 15 posturas + reposo
└── zona.json                # 4 esquinas de calibración
```

## 📈 Próximos Pasos

1. ✅ Grabar 15 posturas con `grabar_posturas.py --real --a-mano`
2. ✅ Probar posición intermedia con `probar_posicion_intermedia.py --real`
3. ⏳ Grabar dataset (50+ episodios) con `grabar_dataset_auto.py`
4. ⏳ Entrenar ACT con dataset
5. ⏳ Evaluar rendimiento ACT vs CerebroZonas

## 📝 Notas de Diseño

### ¿Por qué Posición Fija por Defecto?

1. **Simplicidad**: Más fácil de grabar (no hay que seguir moviendo el taladro)
2. **Robustez**: Menos variabilidad en los datos de entrenamiento
3. **Realismo**: En uso real, el taladro estará mayormente estático
4. **Calidad**: Evita episodios con movimientos accidentales

### ¿Cuándo Usar Seguimiento?

- Si el taladro se mueve frecuentemente en la aplicación real
- Para demostrar capacidades reactivas
- Para investigación de políticas adaptativas

### Offsets Adaptativos

**Problema**: Posturas traseras (13-17) tienen elbow_flex menos negativo
- Frontal: -54° (muy doblado)
- Trasera: -23° (casi recto)

**Solución**: Reducir offset_distancia al 40% en zonas v > 0.6
- Permite alcanzar objetivo sin exceder límites físicos
- Mantiene seguridad en zonas frontales

---

**Última actualización**: 2026-11-21
