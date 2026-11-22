// Garbi · aspiradora. Un relé en paralelo con el botón de la aspiradora.
//
// El PC (garbi/real.py, SenalAspiradora) manda por USB, a 115200 baudios, la línea "1" (aspirar) o "0" (no aspirar)
// cada 200 ms. Si pasa 1 s sin recibir nada (programa cerrado, cable suelto, cuelgue), la aspiradora se apaga sola.
//
// Dos modos, según el botón de la aspiradora (comprobar con la aspiradora DESENCHUFADA o sin batería):
//   MODO_MANTENER  : interruptor que se queda en su posición (o el relé sustituye a un botón que hay que mantener).
//                    El relé está cerrado todo el tiempo que Garbi aspira. El interruptor de la aspiradora, en OFF.
//   MODO_PULSADOR  : botón que enciende con un toque y apaga con otro toque. El relé da un pulso de PULSO_MS
//                    para cambiar de estado. El Arduino recuerda el estado: empezar con la aspiradora APAGADA.
//                    Si se desincroniza (alguien la tocó a mano), mandar "S" por el monitor serie para corregirlo.
//
// Pruebas a mano desde el Monitor Serie del IDE (115200, «Nueva línea»): escribir 1, 0 o ?.

// ----- Configuración ------------------------------------------------------------------------------------------------
#define MODO_MANTENER 1
#define MODO_PULSADOR 2
#define MODO MODO_MANTENER        // <-- cambiar a MODO_PULSADOR si el botón es de toque

const int PIN_RELE = 7;           // IN del módulo de relé
const bool RELE_ACTIVO_BAJO = true;  // la mayoría de módulos de 1 canal se activan con LOW; si va al revés, false
const unsigned long LATIDO_MS = 1000;   // sin mensajes durante este tiempo -> apagar
const unsigned long PULSO_MS = 250;     // duración del toque en MODO_PULSADOR
const unsigned long ENTRE_PULSOS_MS = 800;  // tiempo mínimo entre toques (que la aspiradora no lea dos)

// ----- Estado -------------------------------------------------------------------------------------------------------
bool pedida = false;        // lo que pide el PC
bool encendida = false;     // lo que creemos que hace la aspiradora
unsigned long ultimoMensaje = 0;
unsigned long ultimoPulso = 0;
bool hayPC = false;         // hasta el primer mensaje no hace falta latido
char linea[8];
byte largo = 0;

void rele(bool cerrado) {
  digitalWrite(PIN_RELE, (cerrado != RELE_ACTIVO_BAJO) ? HIGH : LOW);
}

void informar() {
  Serial.print(F("{\"asp\":"));
  Serial.print(encendida ? 1 : 0);
  Serial.print(F(",\"pc\":"));
  Serial.print(hayPC ? 1 : 0);
  Serial.println(F("}"));
}

void aplicar(unsigned long ahora) {
  if (pedida == encendida) return;
#if MODO == MODO_MANTENER
  rele(pedida);
  encendida = pedida;
  digitalWrite(LED_BUILTIN, encendida);
  informar();
#else
  if (ahora - ultimoPulso < ENTRE_PULSOS_MS) return;  // se reintenta en la siguiente vuelta
  rele(true);
  delay(PULSO_MS);
  rele(false);
  ultimoPulso = millis();
  encendida = !encendida;
  digitalWrite(LED_BUILTIN, encendida);
  informar();
#endif
}

void procesar(const char* l, unsigned long ahora) {
  if (l[0] == '1') { pedida = true; }
  else if (l[0] == '0') { pedida = false; }
  else if (l[0] == '?') { Serial.println(F("{\"id\":\"garbi_aspiradora\"}")); informar(); }
  else if (l[0] == 'S' || l[0] == 's') { encendida = !encendida; digitalWrite(LED_BUILTIN, encendida); informar(); }
  else return;
  ultimoMensaje = ahora;
  hayPC = true;
}

void setup() {
  rele(false);                 // primero el pin en reposo, luego como salida: sin pulso al arrancar
  pinMode(PIN_RELE, OUTPUT);
  rele(false);
  pinMode(LED_BUILTIN, OUTPUT);
  digitalWrite(LED_BUILTIN, LOW);
  Serial.begin(115200);
  Serial.println(F("{\"id\":\"garbi_aspiradora\"}"));
}

void loop() {
  unsigned long ahora = millis();

  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') {
      if (largo > 0) { linea[largo] = 0; procesar(linea, ahora); largo = 0; }
    } else if (largo < sizeof(linea) - 1) {
      linea[largo++] = c;
    }
  }

  // Seguridad: sin latido, apagar.
  if (hayPC && ahora - ultimoMensaje > LATIDO_MS) {
    pedida = false;
    hayPC = false;
    informar();
  }

  aplicar(ahora);
}
