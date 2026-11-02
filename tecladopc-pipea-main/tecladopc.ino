#include <pipea.h>
#include <hidboot.h>
#include <usbhub.h>
// #include <SPI.h>
// #include <Keyboard.h> // Incluye la librería Keyboard si es necesario

// Variables de lectura del teclado QWERTY
char keyasc;
int keycode;
boolean iskeypressed;


PIPEA teclado;
// char personaje1[] = "sofia";
// char accion1[] = "volar";

struct Propuesta {
  char* topico;
  char* accion;
};

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

/*void reaccionar(char* personaje, char* accion) {
  if ( !strcmp(nodo.personaje, "tecladopc") ) {
    if ( !strcmp(nodo.accion, "tranquila") ) {
      sofia.tranquila();
    }
    if ( !strcmp(nodo.accion, "feliz") ) {
      sofia.feliz();
    }
  }
}
*/

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


// Definir una estructura para almacenar el tópico y la acción


// Función para obtener el tópico y la acción basados en la tecla presionada
Propuesta obtenerPropuesta(char key) {
  switch (key) {
    case 'a':
      return {"sofia", "apagada"};
    case 'e':
      return {"sofia", "encendida"};
    case 'q':
      return {"sofia", "tranquila"};
    case 'f':
      return {"sofia", "feliz"};   
    case 't':
      return {"sofia", "triste"};
    case 'o':
      return {"sofia", "sorpresa"};
    case 's':
      return {"sofia", "sospecha"};
    case 'u':
      return {"sofia", "susto"};
    case 'w':
      return {"sofia", "wacala"};
    case 'y':
      return {"sofia", "ok"};
    case 'n':
      return {"sofia", "no_ok"};
    case 'r':
      return {"sofia", "al_reves"};
    case 'j':
      return {"sofia", "izquierda"};
    case 'l':
      return {"sofia", "derecha"};
    case 'i':
      return {"sofia", "arriba"};
    case 'k':
      return {"sofia", "abajo"};
    case 'p':
      return {"sofia", "pregunta"};
    case 'c':
      return {"sofia", "cuidado"};
    case 'g':
      return {"sofia", "emergencia"};
    case 'm':
      return {"sofia", "musica"};

    // Agregar casos para las teclas F1 a F10
    case 0x3A: // F1
      return {"chispanuria", "nuno"};
    case 0x3B: // F2
      return {"chispanuria", "ndos"};
    case 0x3C: // F3
      return {"chispanuria", "ntres"};
    case 0x3D: // F4
      return {"chispanuria", "ncuatro"};
    case 0x3E: // F5
      return {"chispanuria", "ncinco"};
    case 0x3F: // F6
      return {"chispanuria", "euno"};
    case 0x40: // F7
      return {"chispanuria", "edos"};
    case 0x41: // F8
      return {"chispanuria", "etres"};
    case 0x42: // F9
      return {"chispanuria", "ecuatro"};
    case 0x43: // F10
      return {"chispanuria", "apagado"};
    case 0x52: // Up Arrow
      return {"chispanuria", "arriba"};
    case 0x51: // Down Arrow
      return {"chispanuria", "abajo"};
    /*case 0x44: // F11
      return {"chispanuria", "funcion_11"};
    case 0x45: // F12
      return {"chispanuria", "funcion_12"};
    */
    // Agregar casos para teclas numéricas
    case '1':
      return {"chispafidel", "nuno"};
    case '2':
      return {"chispafidel", "ndos"};
    case '3':
      return {"chispafidel", "ntres"};
    case '4':
      return {"chispafidel", "ncuatro"};
    case '5':
      return {"chispafidel", "ncinco"};
    case '6':
      return {"chispafidel", "euno"};
    case '7':
      return {"chispafidel", "edos"};
    case '8':
      return {"chispafidel", "etres"};
    case '9':
      return {"chispafidel", "ecuatro"};
    case '0':
      return {"chispafidel", "apagado"};
    case 0x4B: // Page Up
      return {"chispafidel", "arriba"};
    case 0x4E: // Page Down
      return {"chispafidel", "abajo"};
    default:
      return {"", ""}; // Devuelve cadenas vacías si la tecla no está definida
  }
}

void setup() {
  
  pinMode(LED_BUILTIN, OUTPUT);
  teclado.inicio();
  // teclado.estar_atento("tecladopc");
    
  if (Usb.Init() == -1) {
    Serial.println("OSC did not start.");
    digitalWrite(LED_BUILTIN, HIGH);
  }

  delay(200);
  HidKeyboard.SetReportParser(0, &Prs);  
  config_completada();
}

void loop() {
  
  teclado.actualizar();
  
  Usb.Task();
  if (iskeypressed) {
    // String mensaje = "Tecla presionada: ";
    Propuesta propuesta = obtenerPropuesta(keycode);
    
    // Si tanto el tópico como la acción no están vacíos, proponer la acción
    if (propuesta.topico[0] != '\0' && propuesta.accion[0] != '\0') {
      teclado.proponer(propuesta.topico, propuesta.accion);
    }
    
    iskeypressed = false;  // Resetear la variable después de publicar
  }

  delay(11);

}