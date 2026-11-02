#include <UHS2-MIDI.h>
#include <Arduino.h>
#include <pipea.h>
#include <hidboot.h>
#include <usbhub.h>


#ifndef LED_BUILTIN
#define LED_BUILTIN 2
#endif





PIPEA teclado;
struct Propuesta {
  char* topico;
  char* accion;
};
// Variables de lectura del teclado QWERTY
char keyasc;
int keycode;
boolean iskeypressed;



byte pressed = 0x101;
byte released = 0x102;
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

void tecla_presionada() {
  digitalWrite(LED_BUILTIN, HIGH);
  delay(100);
  digitalWrite(LED_BUILTIN, LOW);
}
class KeyboardInput : public KeyboardReportParser {
protected:
  void OnKeyDown(uint8_t mod, uint8_t key);
  void OnKeyPressed(uint8_t key);
};
void KeyboardInput::OnKeyDown(uint8_t mod, uint8_t key) {
  uint8_t c = OemToAscii(mod, key);
  if (c) {
    OnKeyPressed(c);
  } else {
    // Si no es un caracter ASCII, almacenar el código de escaneo
    keycode = key;
    iskeypressed = true;
  }
  tecla_presionada();
}
void KeyboardInput::OnKeyPressed(uint8_t key) {
  keyasc = (char)key;
  keycode = (int)key;
  iskeypressed = true;
}


USB Usb;

HIDBoot<USB_HID_PROTOCOL_KEYBOARD> HidKeyboard(&Usb);
KeyboardInput Prs;

UHS2MIDI_CREATE_DEFAULT_INSTANCE(&Usb);






void handleNoteOn(byte channel, byte pitch, byte velocity)
{
  digitalWrite(LED_BUILTIN, HIGH);
  Serial.print("Nota presionada: ");
  Serial.println(pitch, DEC);
  Serial.println(velocity, DEC);
  Propuesta propuesta = obtenerPropuesta(pitch);
    
  // Si tanto el tópico como la acción no están vacíos, proponer la acción
  if (propuesta.topico[0] != '\0' && propuesta.accion[0] != '\0') {
    teclado.proponer(propuesta.topico, propuesta.accion);
  }

}

void handleNoteOff(byte channel, byte pitch, byte velocity)
{
  digitalWrite(LED_BUILTIN, LOW);
  Serial.print("Nota soltada: ");
  Serial.println(pitch, DEC);
  Serial.println(velocity, DEC);
}


/*
C  48 60 72 84

*/
Propuesta obtenerPropuestaQWERTY(char key){
  Serial.println("key:");
  Serial.print(key);
  switch(key){
    case 'r':
      return {"DMX", "red"};
    case 'g':
      return {"DMX", "green"};
    case 'b':
      return {"DMX", "blue"};
    case 'o':
      return {"DMX", "OFF"};
    case 'e':
      return {"DMX", "electricity"};
    case 'n':
      return {"DMX", "RAN"};
    case '0':
      return {"chispanuria", "nuno"};
    case '1':
      return {"chispanuria", "ndos"};
    case '2':
      return {"chispanuria", "ntres"};
    case '3':
      return {"chispanuria", "ncuatro"};
    case '4':
      return {"chispanuria", "ncinco"};
  }

  return {"", ""}; // Devuelve cadenas vacías si la tecla no está definida
}
Propuesta obtenerPropuesta(char key) {
  if (key == 48 || key == 60 || key == 72 ){
    return {"DMX", "red"};
  }
  if (key == 50 || key == 62 || key == 74){
    return {"DMX", "green"};
  }
  if (key == 52 || key == 64 || key == 76){
    return {"DMX", "blue"};
  }
  if (key == 49 || key == 61 || key == 73){
    return {"DMX", "OFF"};
  }
  if (key == 54 || key == 63 || key == 78){
    return {"DMX", "electricity"};
  }
  if (key == 56 || key == 68 || key == 80){
    return {"DMX", "RAN"};
  }
  if (key == 77){
    return {"chispanuria", "nuno"};
  }
  if (key == 79){
    return {"chispanuria", "ndos"};
  }
  if (key == 81){
    return {"chispanuria", "ntres"};
  }
  if (key == 83){
    return {"chispanuria", "ncuatro"};
  }
  if (key == 84){
    return {"chispanuria", "ncinco"};
  }

  return {"", ""}; // Devuelve cadenas vacías si la tecla no está definida
}


// -----------------------------------------------------------------------------

void setup()
{
  pinMode(LED_BUILTIN, OUTPUT);
  Serial.begin(115200);

  //Initiate MIDI communications, listen to all channels
  MIDI.begin(MIDI_CHANNEL_OMNI);
  MIDI.setHandleNoteOn(handleNoteOn);  

  // Do the same for NoteOffs
  MIDI.setHandleNoteOff(handleNoteOff);
  
  if (Usb.Init() == -1) {
    while (1); //halt
  }//if (Usb.Init() == -1...
  delay( 200 );


  teclado.inicio();


  delay(200);
  HidKeyboard.SetReportParser(0, &Prs);  
  config_completada();

}

void loop()
{
  Usb.Task();

  MIDI.read();

  teclado.actualizar();

  if (iskeypressed) {
    Serial.println("qwertyuiop");
    // String mensaje = "Tecla presionada: ";
    Propuesta propuesta = obtenerPropuestaQWERTY(keycode);
    
    // Si tanto el tópico como la acción no están vacíos, proponer la acción
    if (propuesta.topico[0] != '\0' && propuesta.accion[0] != '\0') {
      teclado.proponer(propuesta.topico, propuesta.accion);
    }
    
    iskeypressed = false;  // Resetear la variable después de publicar
  }


}

