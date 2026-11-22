# Firmware

**Garbi:** `garbi_aspiradora/` enciende la aspiradora con un relé cuando Garbi aspira (ver su README).

## Antorchas (LeWelder, proyecto anterior)

Dos bocetos de Arduino. Cada uno compila igual para **Arduino Nano/Uno** y para **ESP32**: los pines cambian solos
según la placa (`#if defined(ESP32)`). El protocolo y los pines salen de `lewelder/contrato.py`.

| Boceto | Qué hace |
|---|---|
| `antorcha_alumno/` | Gatillo con antirrebote, LED de la punta encendido mientras se pulsa, IMU (BNO055 o MPU6050) y una línea JSON a 100 Hz por USB |
| `antorcha_robot/` | LED de la punta que enciende el PC con `L1` y apaga con `L0`; se apaga solo si pasan 2 s sin órdenes |

## Protocolo (115200 baudios, una línea por mensaje, `\n` al final)

| Sentido | Mensaje |
|---|---|
| Alumno → PC, 100 Hz | `{"t":12345,"g":1,"q":[0.7071,0.0000,0.7071,0.0000]}`: `t` = ms desde el arranque, `g` = gatillo, `q` = cuaternión `[w,x,y,z]` de la IMU (IMU → mundo) |
| Alumno sin IMU | `{"t":12345,"g":1,"q":null}` (se detecta al arrancar; el PC puntúa sin ángulo) |
| PC → robot | `L1` (encender), `L0` (apagar). El PC repite el estado cada segundo como latido |
| PC → cualquiera | `?` → `{"id":"alumno"}` o `{"id":"robot"}` |

## Conexiones

| Señal | Arduino Nano/Uno | ESP32 (DevKit) | Notas |
|---|---|---|---|
| Gatillo | D2 | GPIO 4 | Pulsador entre el pin y **GND**. Sin resistencia: se usa el pull-up interno |
| LED de la punta | D9 | GPIO 2 | Pin → resistencia → ánodo (pata larga) del LED; cátodo → GND. En el ESP32, GPIO 2 es también el LED azul de la placa |
| IMU SDA | A4 | GPIO 21 | |
| IMU SCL | A5 | GPIO 22 | |
| IMU VIN | 5V | 3V3 | Las placas de BNO055 y MPU6050 habituales llevan regulador y aceptan 3,3-5 V |
| IMU GND | GND | GND | |

La antorcha del robot solo usa el LED (D9 o GPIO 2) y GND.

### Resistencia del LED (verde)

| Placa | LED verde "normal" (≈2,1 V) | LED verde brillante (≈3,0 V) |
|---|---|---|
| Nano/Uno (5 V) | 330 Ω (≈9 mA) | 220 Ω (≈9 mA) |
| ESP32 (3,3 V) | 120 Ω (≈10 mA) | 33 Ω (≈9 mA); queda justo de tensión |

El LED de la punta es lo que sigue la webcam, así que interesa que brille. Si con el ESP32 se ve flojo, alimenta
el LED desde 5 V (pin VIN/5V de la placa) con un transistor NPN (BC547, 2N2222): pin → 1 kΩ → base; emisor → GND;
5 V → resistencia de la columna de 5 V → LED → colector. La lógica no cambia.

## Montaje de la IMU

- **+X de la IMU hacia la punta** de la antorcha (los ejes vienen serigrafiados en la placa), paralelo al eje.
- **+Z hacia la cara superior** de la antorcha, la opuesta al gatillo (placa plana con los componentes hacia
  arriba). Así queda +Y hacia la izquierda mirando hacia la punta.
- Bien fija (sin holgura) y lejos de los imanes.

El PC no necesita rumbo absoluto: usa una **tara**. Con la antorcha **vertical, punta abajo y la cara superior
mirando en el sentido de avance del cordón**, se pulsa "tara"; desde ahí calcula el ángulo de trabajo y el de
avance en el marco de la pieza (convención completa en `lewelder/antorcha.py`).

## Elegir la IMU

Arriba de `antorcha_alumno.ino`:

```cpp
#define IMU_BNO055      // por defecto
// #define IMU_MPU6050
// #define SIN_IMU      // sin IMU (no necesita librerías)
```

- **BNO055**: da el cuaternión ya fusionado. Se usa en modo IMUPLUS (sin magnetómetro, porque los imanes de la base
  lo engañarían). Prueba las direcciones 0x28 y 0x29.
- **MPU6050**: la librería `MPU6050_light` da aceleración y giro calibrados y el firmware calcula el cuaternión con
  un filtro de Mahony. **Al enchufarla, la antorcha tiene que estar quieta ~1 s** (calibra el giróscopo).
- Si la IMU elegida no responde al arrancar, la antorcha manda `"q":null` y todo lo demás sigue funcionando.

## Cargar desde Arduino IDE (Windows)

1. Instala [Arduino IDE 2](https://www.arduino.cc/en/software). Si la placa es un clon con chip CH340 y Windows no
   le da puerto COM, instala el driver CH340 (para ESP32 con CP2102, el driver CP210x de Silicon Labs).
2. **Solo ESP32:** *Archivo → Preferencias → URLs adicionales de gestor de placas*:
   `https://espressif.github.io/arduino-esp32/package_esp32_index.json`; luego *Herramientas → Placa → Gestor de
   placas*, busca **esp32** (de Espressif) e instálalo.
3. *Herramientas → Gestionar bibliotecas*: instala **Adafruit BNO055** (acepta instalar también sus dependencias,
   Adafruit Unified Sensor y Adafruit BusIO) y/o **MPU6050_light**. Para `SIN_IMU` no hace falta ninguna.
4. Abre `firmware\antorcha_alumno\antorcha_alumno.ino` (o el del robot).
5. *Herramientas → Placa*: **Arduino Nano** (o Uno) o **ESP32 Dev Module**. En el Nano, si la carga falla, cambia
   *Procesador* a **ATmega328P (Old Bootloader)** (la mayoría de los clones).
6. *Herramientas → Puerto*: el COM que aparece al enchufar la placa.
7. Pulsa **Subir** (flecha). En algunos ESP32 hay que mantener el botón BOOT mientras pone "Connecting...".

## Probar con el monitor serie

*Herramientas → Monitor serie*, **115200 baudios** y fin de línea **Nueva línea**.

- **Alumno:** salen 100 líneas por segundo. Al pulsar el gatillo, `"g"` pasa a 1 y se enciende el LED. Al mover la
  antorcha cambian los números de `"q"`. Escribe `?` y Enter: aparece `{"id":"alumno"}` entre las muestras.
- **Robot:** escribe `L1` → el LED se enciende y **se apaga solo a los 2 s** (falta el latido del PC: es lo
  esperado). `L0` lo apaga. `?` → `{"id":"robot"}`.

(Cierra el monitor serie antes de usar la placa desde Python: el puerto solo lo puede tener abierto un programa.)

## Comprobar los signos de la IMU desde Python

```bat
.venv\Scripts\python.exe herramientas\probar_antorcha.py
```

Busca las dos antorchas, hace parpadear el LED del robot y muestra gatillo y ángulos del alumno.

1. Antorcha vertical, punta abajo, cara superior hacia el avance → **Intro** (tara): trabajo ≈ 90°, avance ≈ 0°.
2. Inclina la punta hacia delante en el sentido de avance (empuje): **el avance sube** (positivo).
3. Inclina la punta hacia la izquierda mirando en el sentido de avance: **el trabajo baja** de 90°.

Si los ángulos cambian al revés o se mezclan, revisa el montaje (+X a la punta, +Z arriba). Si el montaje está
bien y aun así salen al revés, pon `#define CONJUGAR_Q 1` en `antorcha_alumno.ino` (manda el cuaternión
conjugado) y vuelve a cargar.

## Compilar sin el IDE

```bash
firmware/compilar.sh
```

Compila con `arduino-cli` los dos bocetos para `arduino:avr:nano` y `esp32:esp32:esp32`, y el del alumno con cada
opción de IMU (`-DIMU_BNO055`, `-DIMU_MPU6050`, `-DSIN_IMU`). Necesita los núcleos `arduino:avr` y `esp32:esp32` y
las librerías de arriba (`herramientas/setup_nube.sh` lo instala todo).

## Sin placas

`herramientas/antorcha_virtual.py` crea antorchas virtuales en pseudo-terminales que se comportan igual que este
firmware (Linux/macOS), para ensayar toda la demo en simulación.
