#include <pipea.h>

PIPEA boton_uno;

const int PIN_BOTON = 4;

int estadoAnterior = HIGH;

bool botonPresionado() {
  int estadoActual = digitalRead(PIN_BOTON);

  bool presionado = (estadoAnterior == HIGH && estadoActual == LOW);

  estadoAnterior = estadoActual;

  return presionado;
}

void config_completada() {
  digitalWrite(LED_BUILTIN, HIGH);
  delay(500);
  digitalWrite(LED_BUILTIN, LOW);
  delay(500);
  digitalWrite(LED_BUILTIN, HIGH);
  delay(500);
  digitalWrite(LED_BUILTIN, LOW);
  delay(500);
  digitalWrite(LED_BUILTIN, HIGH);
  delay(500);
  digitalWrite(LED_BUILTIN, LOW);
}

void setup() {

  pinMode(LED_BUILTIN, OUTPUT);
  pinMode(PIN_BOTON, INPUT);

  boton_uno.inicio();

  config_completada();
}

void loop() {

  boton_uno.actualizar();

  if (botonPresionado()) {
    boton_uno.proponer("banda", "solo_guitarra");
  }

  delay(11);
}