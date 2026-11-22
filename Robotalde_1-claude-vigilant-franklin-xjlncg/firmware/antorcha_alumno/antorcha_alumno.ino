// LeWelder · antorcha del alumno (Arduino Nano/Uno o ESP32, mismo código).
//
// Gatillo (con antirrebote) + LED de la punta (se enciende con el gatillo) + IMU. Manda al PC por USB serie,
// a 115200 baudios y 100 Hz, una línea JSON por muestra (ver lewelder/contrato.py):
//
//   {"t":<ms>,"g":<0|1>,"q":[w,x,y,z]}      q = orientación de la IMU (cuaternión de Hamilton, IMU → mundo)
//   {"t":<ms>,"g":<0|1>,"q":null}           si no hay IMU (modo SIN_IMU, detectado al arrancar)
//
// y responde a "?" con {"id":"alumno"}. Nunca se bloquea: todo va por millis() y, si el búfer de salida no tiene
// sitio para una línea entera, esa muestra se salta.
//
// Montaje de la IMU: +X hacia la punta de la antorcha y +Z hacia la cara superior (la opuesta al gatillo).

// ---- Elige la IMU (o compila con -DIMU_MPU6050 / -DSIN_IMU) ----------------------------------------------------
#if !defined(IMU_BNO055) && !defined(IMU_MPU6050) && !defined(SIN_IMU)
#define IMU_BNO055
// #define IMU_MPU6050
// #define SIN_IMU        // sin IMU: no necesita librerías
#endif

// Si en la prueba con el monitor los ángulos se mueven al revés (ver firmware/README.md), pon esto a 1: manda el
// cuaternión conjugado (mundo → IMU en vez de IMU → mundo).
#define CONJUGAR_Q 0

#include <Wire.h>

#if defined(IMU_BNO055)
#include <Adafruit_Sensor.h>
#include <Adafruit_BNO055.h>
#elif defined(IMU_MPU6050)
#include <MPU6050_light.h>
#endif

// ---- Pines (contrato: PINES["nano"] y PINES["esp32"]) -------------------------------------------------------------
#if defined(ESP32)
const int PIN_GATILLO = 4;
const int PIN_LED = 2;
const int PIN_SDA = 21;
const int PIN_SCL = 22;
#else
const int PIN_GATILLO = 2;  // Nano/Uno: SDA = A4, SCL = A5 (fijos)
const int PIN_LED = 9;
#endif

const unsigned long BAUDIOS = 115200;
const unsigned long PERIODO_MS = 10;   // 100 Hz
const unsigned long ANTIRREBOTE_MS = 20;

// ---- Estado ------------------------------------------------------------------------------------------------------
bool hayImu = false;
float q[4] = {1, 0, 0, 0};  // w, x, y, z

bool gatilloPulsado = false;
bool lecturaAnterior = HIGH;
unsigned long cambioGatillo = 0;

unsigned long ultimoEnvio = 0;
char orden[16];
uint8_t largoOrden = 0;

#if defined(IMU_BNO055)
Adafruit_BNO055 bno28(55, 0x28, &Wire);
Adafruit_BNO055 bno29(55, 0x29, &Wire);
Adafruit_BNO055 *bno = nullptr;
#elif defined(IMU_MPU6050)
// La librería da aceleración (g) y giro (°/s) ya calibrados. Sus "ángulos" X/Y/Z son inclinaciones respecto a la
// gravedad que se degeneran con la antorcha vertical (justo la postura de soldar), así que la orientación se
// calcula aquí con un filtro de Mahony en cuaterniones: sin bloqueo de cardán, Z del mundo = vertical y rumbo
// relativo (la tara del PC lo fija).
MPU6050 mpu(Wire);
const float KP_MAHONY = 1.0;  // ganancia de corrección con el acelerómetro (sobre el error completo)
unsigned long ultimoMpuUs = 0;
#endif

// ---- IMU ---------------------------------------------------------------------------------------------------------
void iniciarI2C() {
#if defined(ESP32)
  Wire.begin(PIN_SDA, PIN_SCL);
#else
  Wire.begin();
#endif
#if defined(WIRE_HAS_TIMEOUT)
  Wire.setWireTimeout(3000, true);  // AVR: si la IMU se desconecta, el bus no se queda colgado
#endif
}

#if defined(IMU_MPU6050)
void cuaternionDesdeGravedad(float ax, float ay, float az) {
  // Giro mínimo que lleva la "arriba" medida por el acelerómetro (en la IMU) a +Z del mundo.
  float n = sqrt(ax * ax + ay * ay + az * az);
  if (n < 0.1) return;
  ax /= n; ay /= n; az /= n;
  float w = 1 + az;  // 1 + (a · z)
  if (w < 1e-4) {    // boca abajo: medio giro alrededor de X
    q[0] = 0; q[1] = 1; q[2] = 0; q[3] = 0;
    return;
  }
  // q = [1 + a·z, a × z] normalizado, con a × z = (ay, -ax, 0)
  float m = sqrt(w * w + ay * ay + ax * ax);
  q[0] = w / m; q[1] = ay / m; q[2] = -ax / m; q[3] = 0;
}

void actualizarMahony(float gx, float gy, float gz, float ax, float ay, float az, float dt) {
  // gx..gz en rad/s, ax..az en cualquier unidad. q = IMU → mundo (Hamilton).
  float n = sqrt(ax * ax + ay * ay + az * az);
  if (n > 0.1) {
    ax /= n; ay /= n; az /= n;
    // "Arriba" estimada en el marco de la IMU (tercera fila de R(q)).
    float vx = 2 * (q[1] * q[3] - q[0] * q[2]);
    float vy = 2 * (q[0] * q[1] + q[2] * q[3]);
    float vz = q[0] * q[0] - q[1] * q[1] - q[2] * q[2] + q[3] * q[3];
    // Error = medida × estimada
    gx += KP_MAHONY * (ay * vz - az * vy);
    gy += KP_MAHONY * (az * vx - ax * vz);
    gz += KP_MAHONY * (ax * vy - ay * vx);
  }
  gx *= 0.5 * dt; gy *= 0.5 * dt; gz *= 0.5 * dt;
  float qw = q[0], qx = q[1], qy = q[2], qz = q[3];
  q[0] += -qx * gx - qy * gy - qz * gz;
  q[1] += qw * gx + qy * gz - qz * gy;
  q[2] += qw * gy - qx * gz + qz * gx;
  q[3] += qw * gz + qx * gy - qy * gx;
  float m = sqrt(q[0] * q[0] + q[1] * q[1] + q[2] * q[2] + q[3] * q[3]);
  for (int i = 0; i < 4; i++) q[i] /= m;
}
#endif

void iniciarImu() {
#if defined(IMU_BNO055)
  iniciarI2C();
  // IMUPLUS = acelerómetro + giróscopo, sin magnetómetro: la base lleva imanes y el rumbo absoluto no sirve.
  if (bno28.begin(OPERATION_MODE_IMUPLUS)) {
    bno = &bno28;
  } else if (bno29.begin(OPERATION_MODE_IMUPLUS)) {
    bno = &bno29;
  }
  hayImu = (bno != nullptr);
  // Si tu placa del BNO055 lleva cristal de 32 kHz (la de Adafruit sí), puedes activar:
  // if (hayImu) bno->setExtCrystalUse(true);
#elif defined(IMU_MPU6050)
  iniciarI2C();
  hayImu = (mpu.begin() == 0);
  if (hayImu) {
    delay(200);
    mpu.calcOffsets();  // ~1 s: la antorcha tiene que estar quieta al enchufarla
    mpu.update();
    cuaternionDesdeGravedad(mpu.getAccX(), mpu.getAccY(), mpu.getAccZ());
    ultimoMpuUs = micros();
  }
#else
  hayImu = false;
#endif
}

void actualizarImu() {
  if (!hayImu) return;
#if defined(IMU_MPU6050)
  mpu.update();
  unsigned long ahora = micros();
  float dt = (ahora - ultimoMpuUs) * 1e-6;
  ultimoMpuUs = ahora;
  if (dt <= 0 || dt > 0.1) return;
  const float GRADOS_A_RAD = 0.01745329252;
  actualizarMahony(mpu.getGyroX() * GRADOS_A_RAD, mpu.getGyroY() * GRADOS_A_RAD, mpu.getGyroZ() * GRADOS_A_RAD,
                   mpu.getAccX(), mpu.getAccY(), mpu.getAccZ(), dt);
#endif
}

void leerCuaternionParaEnviar() {
#if defined(IMU_BNO055)
  if (hayImu) {
    imu::Quaternion c = bno->getQuat();
    q[0] = c.w(); q[1] = c.x(); q[2] = c.y(); q[3] = c.z();
  }
#endif
}

// ---- Gatillo -----------------------------------------------------------------------------------------------------
void leerGatillo(unsigned long ahora) {
  bool lectura = digitalRead(PIN_GATILLO);  // pull-up: LOW = pulsado
  if (lectura != lecturaAnterior) {
    lecturaAnterior = lectura;
    cambioGatillo = ahora;
  }
  if (ahora - cambioGatillo >= ANTIRREBOTE_MS) {
    gatilloPulsado = (lectura == LOW);
  }
  digitalWrite(PIN_LED, gatilloPulsado ? HIGH : LOW);
}

// ---- Salida ------------------------------------------------------------------------------------------------------
// Añade un número con 4 decimales (snprintf no tiene %f en AVR).
char *anadirDecimal(char *p, float v) {
  if (v < 0) {
    *p++ = '-';
    v = -v;
  }
  long entero = (long)v;
  long decimales = (long)((v - entero) * 10000.0 + 0.5);
  if (decimales >= 10000) {
    entero += 1;
    decimales -= 10000;
  }
  p += sprintf(p, "%ld.%04ld", entero, decimales);
  return p;
}

void enviarMuestra(unsigned long ahora) {
  char linea[80];
  char *p = linea;
  p += sprintf(p, "{\"t\":%lu,\"g\":%d,\"q\":", ahora, gatilloPulsado ? 1 : 0);
  bool qValido = hayImu;
  for (int i = 0; i < 4 && qValido; i++) qValido = !isnan(q[i]) && !isinf(q[i]);
  if (qValido) {
    float s = CONJUGAR_Q ? -1.0 : 1.0;
    *p++ = '[';
    p = anadirDecimal(p, q[0]);
    for (int i = 1; i < 4; i++) {
      *p++ = ',';
      p = anadirDecimal(p, s * q[i]);
    }
    *p++ = ']';
  } else {
    p += sprintf(p, "null");
  }
  *p++ = '}';
  *p++ = '\n';
  size_t largo = p - linea;
  if ((size_t)Serial.availableForWrite() >= largo) {
    Serial.write((const uint8_t *)linea, largo);
  }
}

// ---- Órdenes del PC ----------------------------------------------------------------------------------------------
void atenderOrden() {
  orden[largoOrden] = '\0';
  if (strcmp(orden, "?") == 0) {
    Serial.print("{\"id\":\"alumno\"}\n");
  }
}

void leerOrdenes() {
  while (Serial.available() > 0) {
    char ch = Serial.read();
    if (ch == '\r') continue;
    if (ch == '\n') {
      atenderOrden();
      largoOrden = 0;
    } else if (largoOrden < sizeof(orden) - 1) {
      orden[largoOrden++] = ch;
    } else {
      largoOrden = 0;  // orden demasiado larga: se descarta
    }
  }
}

// ---- Arduino -----------------------------------------------------------------------------------------------------
void setup() {
  pinMode(PIN_GATILLO, INPUT_PULLUP);
  pinMode(PIN_LED, OUTPUT);
  digitalWrite(PIN_LED, LOW);
  Serial.begin(BAUDIOS);
  iniciarImu();
  ultimoEnvio = millis();
}

void loop() {
  unsigned long ahora = millis();
  leerOrdenes();
  leerGatillo(ahora);
  actualizarImu();
  if (ahora - ultimoEnvio >= PERIODO_MS) {
    ultimoEnvio += PERIODO_MS;
    if (ahora - ultimoEnvio >= PERIODO_MS) ultimoEnvio = ahora;  // muy retrasado: se resincroniza
    leerCuaternionParaEnviar();
    enviarMuestra(ahora);
  }
}
