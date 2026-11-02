/*
  UCR | EIE | Electrizarte
  boteallas.h - Librería para implementar la pantalla de botellas de Electrizarte
  Escrita por Teodoro Willink en Agosto de 2024
  Actualizada por Teodoro Willink en Agosto de 2026
  [Si la actualiza, por favor incluya y ajuste una línea de "Actualizada por X en Y"]
  Código abierto liberado al dominio público
*/

#ifndef boteallas_h
#define boteallas_h

#include <FastLED.h>
//#include <Adafruit_NeoPixel.h>

#define MATRIZ_ANCHO_MAX 24
#define MATRIZ_ALTO_MAX 24

#define TIRA_PIN 13 // Elegido para utilizar un ESP32

#define ORDEN_COLOR RGB
#define TIPO_LED WS2812

class botEAllas {
  public:
    //botEAllas();
    //botEAllas(int pin);
    //botEAllas(int Nx, int Ny);
    botEAllas(int Nx, int Ny, int pin);

    int ancho = MATRIZ_ANCHO_MAX;
    int alto = MATRIZ_ALTO_MAX;

    int matriz[MATRIZ_ANCHO_MAX][MATRIZ_ALTO_MAX][3];
    
    void inicio();
    void prueba();
    
    void mostrar();
    void borrar_matriz();

  private:
    int _pin = TIRA_PIN;

    //Adafruit_NeoPixel _tira;
    CRGB _tira[MATRIZ_ANCHO_MAX*MATRIZ_ALTO_MAX];
};

#endif
