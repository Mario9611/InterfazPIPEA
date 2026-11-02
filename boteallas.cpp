/*
  UCR | EIE | Electrizarte
  boteallas.cpp - Librería para implementar la pantalla de botellas de Electrizarte
  Escrita por Teodoro Willink en Agosto de 2024
  Actualizada por Teodoro Willink en Agosto de 2026
  [Si la actualiza, por favor incluya y ajuste una línea de "Actualizada por X en Y"]
  Código abierto liberado al dominio público
*/

#include "boteallas.h"

botEAllas::botEAllas(int Nx, int Ny, int pin) {
  ancho = Nx;
  alto = Ny;
  _pin = pin;
}

void botEAllas::inicio() {
  borrar_matriz();
  
  FastLED.addLeds<TIPO_LED, TIRA_PIN, ORDEN_COLOR>(_tira, ancho*alto);
  // Lo ideal sería que el pin pueda ser una variable, no una constante, pero parece que la librería sólo soporta una constante
  
  FastLED.clear(1);
}

void botEAllas::prueba() {
  FastLED.clear(1);
  
  _tira[1] = CRGB::Aquamarine;
  _tira[4] = CRGB::Coral;
  _tira[7] = CRGB::Teal;
  _tira[11] = CRGB::Maroon;
  
  FastLED.show();
}

void botEAllas::mostrar() {
  FastLED.clear(1);


  // Cuando escribí este algoritmo, sólo Dios y yo sabíamos cómo funciona
  for(int x=0; x<ancho; x++)
    for(int y=0; y<alto; y++)
      if ( y % 2 == 0 )
        _tira[y*ancho+x] = CRGB(matriz[ancho-1-x][alto-1-y][0],matriz[ancho-1-x][alto-1-y][1],matriz[ancho-1-x][alto-1-y][2]);
      else
        _tira[y*ancho+ancho-x-1] = CRGB(matriz[ancho-1-x][alto-1-y][0],matriz[ancho-1-x][alto-1-y][1],matriz[ancho-1-x][alto-1-y][2]);

  FastLED.show();
}

void botEAllas::borrar_matriz() {
  for(int x=0; x<ancho; x++)
    for(int y=0; y<alto; y++)
      for(int c=0; c<3; c++)
        matriz[x][y][c] = 0;
}
