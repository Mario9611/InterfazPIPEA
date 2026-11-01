/*
  UCR | EIE | Electrizarte
  colorEAs.h - Librería para definir colores
  Escrita por Teodoro Willink y Gustavo Núñez en Agosto de 2026
  [Si la actualiza, por favor incluya y ajuste una línea de "Actualizada por X en Y"]
  Código abierto liberado al dominio público
*/

#ifndef coloreas_h
#define coloreas_h

// Macros para despulgar
#define DESPULGAR 1

#if DESPULGAR
  #define INICIAR()                        Serial.begin(115200)
  #define IMPRIMIR(texto, variable)        Serial.print(texto); Serial.println(variable)
  #define VARIABLE(variable)               Serial.print(variable)
  #define VARIABLELN(variable)             Serial.println(variable)
  #define TEXTO(texto)                     Serial.print(texto)
  #define TEXTOLN(texto)                   Serial.println(texto)
  #define ARREGLO(arreglo, cantidad)       for (int i=0; i<cantidad; ++i) { Serial.print(arreglo[i]); Serial.print(" "); }
  #define COLOR(color)                     Serial.print(color.r); Serial.print(", "); Serial.print(color.g); Serial.print(", "); Serial.println(color.b)
  #define POSICION(posicion)               Serial.print(posicion.x); Serial.print(", "); Serial.print(posicion.y); Serial.print(", "); Serial.println(posicion.z)
#else
  #define INICIAR()
  #define IMPRIMIR(texto, variable)
  #define VARIABLE(variable)
  #define VARIABLELN(variable)
  #define TEXTO(texto)
  #define TEXTOLN(texto)
  #define ARREGLO(arreglo, cantidad)
  #define COLOR(color)
  #define POSICION(posicion)
#endif

#include <Arduino.h>

class ColorEA {
  public:
    uint8_t r = 0, g = 0, b = 0;
    int h = 0, s = 0, v = 0;

    ColorEA();
    ColorEA(uint8_t rojo, uint8_t verde, uint8_t azul);

    void hsv(); // Actualiza los valores de tono (hue, H), saturación (saturation, S) y brillo (value, V) con base en los valores de rojo (red, R), verde (green, G) y azul (blue, B).
    void rgb(); // Actualiza los valores de rojo (red, R), verde (green, G) y azul (blue, B) con base en los valores de tono (hue, H), saturación (saturation, S) y brillo (value, V).
};


// Definimos colores para EA
inline const ColorEA blanco(255, 255, 255);
inline const ColorEA negro(0, 0, 0);
inline const ColorEA calido(255, 234, 144);
inline const ColorEA rojo(255, 0, 0);
inline const ColorEA verde(0, 255, 0);
inline const ColorEA azul(0, 0, 255);

inline const ColorEA baseEA(31, 255, 255);
inline const ColorEA rojoEA(255, 31, 31);
inline const ColorEA verdeEA(31, 255, 31);
inline const ColorEA azulEA(31, 31, 255);
inline const ColorEA moradoEA(255, 31, 255);
inline const ColorEA amarilloEA(255, 245, 112);
inline const ColorEA rosaEA(255, 50, 217);
inline const ColorEA naranjaEA(255, 124, 16);

inline const ColorEA amarilloManhana(255, 199, 15);

#endif

// Camino en calma
