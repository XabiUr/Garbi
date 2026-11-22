# CLAUDE.md - Historial de Decisiones Técnicas

## 📅 2026-11-21: Cambio de Seguimiento Continuo a Posición Fija

### Contexto

El sistema original implementaba **seguimiento continuo** del taladro marcado con círculo morado:
- CerebroZonas actualizaba objetivo (u,v) en cada ciclo
- Supervisor en estado EN_OBJETIVO detectaba movimiento y volvía a aproximar
- Útil para demostrar capacidades reactivas

### Problema Identificado

**Para grabación de dataset**:
1. Difícil mantener el taladro perfectamente estático durante ~10s
2. Movimientos accidentales generan episodios "sucios"
3. Variabilidad innecesaria dificulta entrenamiento ACT
4. En uso real, el taladro estará mayormente estático

### Decisión: Posición Fija por Defecto

**Cambios implementados**:

1. **CerebroZonas**: Congela objetivo (u,v) al inicio
   - Variable `objetivo_congelado`: None → se fija en primer `paso()`
   - `reset()` limpia objetivo congelado
   - Toda la trayectoria usa el mismo objetivo

2. **Supervisor**: Nuevo estado FIJO
   - Detecta estabilización en ACTUANDO (cambio < 0.5° durante 1s)
   - Transiciona ACTUANDO → FIJO
   - En FIJO: mantiene postura sin consultar cerebro
   - Sale de FIJO si taladro desaparece 1.5s

3. **Grabación**: Detecta movimiento no deseado
   - Guarda posición inicial (u,v) al detectar morado estable
   - Durante actuación: compara con posición inicial
   - Si dist > 0.05 → avisa en pantalla "TALADRO MOVIDO - Pulsa R"
   - Al finalizar: aviso en consola para considerar descarte

4. **Flag --seguir**: Mantiene comportamiento antiguo
   - Sin flag (default): Posición fija, objetivo congelado, aviso si mueve
   - Con flag: Seguimiento continuo, reactivo a movimiento, sin avisos

### Impacto

**Ventajas posición fija**:
- ✅ Grabación más fácil y rápida
- ✅ Dataset más limpio y consistente
- ✅ Entrenamiento ACT más robusto
- ✅ Comportamiento más realista

**Desventajas**:
- ❌ No aprende reactividad a movimiento (pero no es necesario en uso real)
- ❌ Requiere dos datasets separados si se quieren ambos comportamientos

### Configuración Añadida

```json
{
  "supervisor": {
    "seguir": false,                      // Control del modo
    "umbral_estabilizacion": 0.5,         // Grados para considerar estable
    "tiempo_estabilizacion_s": 1.0,       // Duración para pasar a FIJO
    "umbral_movimiento_taladro": 0.05     // Distancia (u,v) para detectar movimiento
  }
}
```

---

## 📅 2026-11-21: Offsets Adaptativos por Zona

### Contexto

Posturas de la cuadrícula 5×3 tienen valores muy diferentes según la fila:

| Fila | Zonas | elbow_flex promedio | Descripción |
|------|-------|-------------------|-------------|
| Frontal (v=0) | 3-7 | -54° a -48° | Muy doblado hacia atrás |
| Media (v=1) | 8-12 | -40° a -34° | Moderadamente doblado |
| Trasera (v=2) | 13-17 | -34° a -21° | Casi recto |

### Problema

Al añadir `offset_distancia_aproximacion = 16.0` durante aproximación:
- Zonas frontales: -54° + 16° = -38° ✅ (alcanzable)
- Zonas traseras: -23° + 16° = -7° ❌ (demasiado lejos, no puede bajar)

**Usuario reportó**: "En las zonas 17, 16, 15, 14 y 13 no baja como debería el brazo"

### Decisión: Offset Adaptativo según V

**Implementación**:

```python
# En supervisor.py, estados APROXIMANDO y ACTUANDO:
v = percepcion.get("v", 0.5) if percepcion["hay_taladro"] else 0.5
if v > 0.6:  # Fila trasera (zonas 13-17)
    offset_distancia = self.offset_distancia_aproximacion * 0.4  # 40% del offset
else:
    offset_distancia = self.offset_distancia_aproximacion
accion["elbow_flex.pos"] += offset_distancia
```

**Resultado**:
- Zonas frontales: -54° + 16° = -38° ✅
- Zonas traseras: -23° + 6.4° = -17° ✅

### Umbral v > 0.6

**¿Por qué 0.6?**
- Fila frontal: v ≈ 0.0
- Fila media: v ≈ 0.5
- Fila trasera: v ≈ 1.0
- Con margen_zona = 0.15, valores pueden variar ligeramente
- 0.6 asegura que solo fila trasera use offset reducido

### Alternativas Consideradas

1. **Offset fijo menor**: 8.0 en vez de 16.0
   - ❌ Insuficiente seguridad en zonas frontales

2. **Offset progresivo**: Interpolación lineal con v
   - ✅ Más suave
   - ❌ Más complejo sin beneficio claro

3. **Offsets por zona individual**: 15 valores distintos
   - ❌ Demasiado complejo de calibrar

---

## 📅 2026-11-21: Posición Intermedia Fija

### Contexto

El sistema original aproximaba directamente desde reposo:
- REPOSO → APROXIMANDO → ACTUANDO
- El cerebro interpolaba desde posturas base diferentes según zona
- Resultaba en alturas y posiciones iniciales inconsistentes

### Problema

**Usuario reportó**: "Cuando está más cerca del brazo, el movimiento empieza estando mucho más abajo"

**Causa raíz**:
- Cada postura base en grid 5×3 tiene altura diferente
- Al añadir `offset_aproximacion_altura = -55°`, algunas quedaban demasiado bajas
- Zonas cercanas al brazo (traseras) no tenían espacio para retroceder

### Decisión: Estado YENDO_A_INTERMEDIA

**Implementación**:
1. Nuevo estado entre REPOSO y APROXIMANDO
2. Posición intermedia fija guardada en config.json
3. Duración: 2 segundos de movimiento gradual
4. Script para guardar: `guardar_posicion_intermedia.py --real`
5. Script para probar: `probar_posicion_intermedia.py --real`

**Flujo nuevo**:
```
REPOSO → YENDO_A_INTERMEDIA → APROXIMANDO → ACTUANDO → ...
```

**Ventajas**:
- ✅ Altura inicial consistente
- ✅ Espacio garantizado para retroceder
- ✅ Trayectorias más seguras y predecibles
- ✅ Facilita calibración manual

---

## 📅 2026-11-21: Cuadrícula 3×3 → 5×3

### Contexto

Grid original: 3×3 (9 posturas)
```
7(0.0,1.0)  8(0.5,1.0)  9(1.0,1.0)
4(0.0,0.5)  5(0.5,0.5)  6(1.0,0.5)
1(0.0,0.0)  2(0.5,0.0)  3(1.0,0.0)
```

### Problema

**Usuario reportó**: "Ahora hemos hecho un poco más grande la zona para que detecte bien el taladro, igual sería conveniente que tuviera 5x3"

**Motivación**:
- Zona de trabajo más ancha horizontalmente que profunda
- Interpolación 3×3 generaba movimientos grandes entre columnas
- Necesidad de más resolución en eje U (horizontal)

### Decisión: Grid 5×3

**Nuevo grid**: 15 posturas (3-17)
```
13(0,2)  14(1,2)  15(2,2)  16(3,2)  17(4,2)   <- Trasera
 8(0,1)   9(1,1)  10(2,1)  11(3,1)  12(4,1)   <- Media
 3(0,0)   4(1,0)   5(2,0)   6(3,0)   7(4,0)   <- Frontal
```

**Cambios**:
- Numeración empieza en 3 (mantiene compatibilidad con posturas anteriores si existen)
- Mapeo teclado: 3-9 directo, A(10), B(11), C(12), D(13), E(14), F(15), G(16), H(17)
- Interpolación: u: [0,1] → [0,4], v: [0,1] → [0,2]

**Impacto**:
- ✅ Movimientos más suaves horizontalmente
- ✅ Mejor cobertura de zona amplia
- ⚠️ 6 posturas adicionales para grabar

---

## 📅 2026-11-21: Calibración con Marca Elevada

### Contexto

Calibración original: clic manual en 4 esquinas
- Asume que marca morada está en la mesa
- Vista cenital perpendicular

### Problema

**Usuario reportó**: "Problema: la marca morada está ~20 cm por encima de la mesa y con la cámara inclinada se sale de la zona calibrada"

**Causa**:
- Marca morada en punta del taladro, no en mesa
- Cámara no está perfectamente cenital
- Paralaje causa desplazamiento significativo

### Decisión: Calibración con Detección Automática

**Nuevo modo --con-marca (default)**:
1. Colocar taladro en cada esquina
2. Presionar ESPACIO
3. Detecta círculo morado automáticamente
4. Promedia 15 frames para estabilidad
5. Repite para 4 esquinas

**Ventajas**:
- ✅ Calibración más precisa (usa posición real de marca)
- ✅ Corrige automáticamente paralaje de cámara
- ✅ Más rápido (no hay que hacer clic exacto)
- ✅ Más robusto (promedio de 15 frames)

**Modo alternativo --con-clic**: Mantiene comportamiento original

---

## 📅 2026-11-21: Velocidades Reducidas

### Contexto

Velocidades originales:
- paso_maximo_por_ciclo: 2.5°
- velocidad_reposo: 1.5°
- Duración levantamiento: 1.0s
- Duración volver: 3.0s

### Problema

**Usuario reportó**: "Retroceder y el despertar más lento"

**Motivación**:
- Movimientos demasiado rápidos
- Riesgo de colisiones
- Necesidad de más tiempo de reacción

### Decisión: Reducir Velocidades

**Nuevos valores**:
```json
{
  "seguridad": {
    "paso_maximo_por_ciclo": 1.5,  // 2.5 → 1.5
    "velocidad_reposo": 0.8         // 1.5 → 0.8
  }
}
```

**Tiempos de transición**:
- Levantamiento: 1.0s → 2.0s
- Volver a reposo: 3.0s → 5.0s
- Startup a reposo: añadido 2.0s gradual

---

## 🎓 Lecciones Aprendidas

### 1. Configurabilidad es Clave

**Decisión correcta**: Parametrizar todo en config.json
- Facilita ajustes sin recompilar
- Permite experimentación rápida
- Usuario puede tune según hardware específico

### 2. Scripts de Utilidad Valiosos

**Scripts creados**:
- `guardar_posicion_intermedia.py`: Captura posición actual
- `probar_posicion_intermedia.py`: Valida antes de usar
- `diagnostico_motores.py`: Debug de conexiones

**Valor**: Reduce fricción en calibración y debug

### 3. Modos de Operación Explícitos

**Flags añadidos**:
- `--seguir` / sin flag: Comportamiento explícito y claro
- `--con-marca` / `--con-clic`: Alternativas claras
- `--sin-robot` / `--real`: Simulación vs producción

**Ventaja**: Usuario sabe exactamente qué esperar

### 4. Adaptabilidad a Hardware

**Offsets adaptativos** son necesarios porque:
- Cada robot tiene pequeñas diferencias
- Posturas bases varían según zona física
- Una solución "one-size-fits-all" no funciona

**Solución**: Lógica adaptativa basada en contexto (posición, zona, etc.)

### 5. Validación Incremental

**Proceso exitoso**:
1. Test conexión → `test_conexion.py`
2. Calibrar zona → `calibrar_zona.py`
3. Grabar posturas → `grabar_posturas.py`
4. Probar intermedia → `probar_posicion_intermedia.py`
5. Test supervisor → `supervisor.py --cerebro zonas`
6. Grabar dataset → `grabar_dataset_auto.py`

**Cada paso valida el anterior** antes de avanzar

---

## 🔮 Decisiones Futuras a Considerar

### 1. Limpieza Local Automática

**Propuesto**: Al salir de FIJO, activar aspiradora brevemente
- Requiere integración con sistema de limpieza
- Config: `limpieza_local_activada: bool`
- Duración: `duracion_limpieza_s: float`

### 2. Múltiples Zonas de Trabajo

**Propuesto**: Calibrar varias zonas independientes
- zona_1.json, zona_2.json, etc.
- Selector en interfaz o comando
- Permitiría trabajar en áreas grandes

### 3. Visualización Mejorada

**Propuesto**: Dashboard con métricas en tiempo real
- Gráficos de posición (u,v) vs tiempo
- Historial de estados
- Visualización 3D del brazo

### 4. Auto-calibración de Offsets

**Propuesto**: Algoritmo que ajusta offsets automáticamente
- Grabar episodio de test por zona
- Detectar si alcanza objetivo
- Ajustar offsets iterativamente

---

**Última actualización**: 2026-11-21
