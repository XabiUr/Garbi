// LeWelder · antorcha del robot (Arduino Nano/Uno o ESP32, mismo código).
//
// Órdenes del PC por USB serie a 115200 baudios (ver lewelder/contrato.py), una por línea:
//   L1  → LED de la punta encendido
//   L0  → apagado
//   ?   → responde {"id":"robot"}
//
// Seguridad: si no llega ninguna orden válida en 2 s (PC colgado, cable suelto), el LED se apaga. El PC manda un
// latido (repite el estado) cada segundo para mantenerlo.

#if defined(ESP32)
const int PIN_LED = 2;
#else
const int PIN_LED = 9;
#endif

const unsigned long BAUDIOS = 115200;
const unsigned long TIEMPO_SEGURIDAD_MS = 2000;

bool encendido = false;
unsigned long ultimaOrden = 0;
char orden[16];
uint8_t largoOrden = 0;

void poner(bool valor) {
  encendido = valor;
  digitalWrite(PIN_LED, encendido ? HIGH : LOW);
}

void atenderOrden() {
  orden[largoOrden] = '\0';
  if (strcmp(orden, "L1") == 0) {
    poner(true);
  } else if (strcmp(orden, "L0") == 0) {
    poner(false);
  } else if (strcmp(orden, "?") == 0) {
    Serial.print("{\"id\":\"robot\"}\n");
  } else {
    return;  // orden desconocida: no cuenta como señal de vida
  }
  ultimaOrden = millis();
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
      largoOrden = 0;
    }
  }
}

void setup() {
  pinMode(PIN_LED, OUTPUT);
  poner(false);
  Serial.begin(BAUDIOS);
  ultimaOrden = millis();
}

void loop() {
  leerOrdenes();
  if (encendido && millis() - ultimaOrden > TIEMPO_SEGURIDAD_MS) {
    poner(false);
  }
}
