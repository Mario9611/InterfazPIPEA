/*
  UCR | EIE | Electrizarte
  chunchesDMX.h - Librería para modelar chunches DMX
  Escrita por Teodoro Willink y Gustavo Núñez en Agosto de 2026
  [Si la actualiza, por favor incluya y ajuste una línea de "Actualizada por X en Y"]
  Código abierto liberado al dominio público
*/

#ifndef chunchesdmx_h
#define chunchesdmx_h

#include <cmath>
#include <algorithm>

#include "coloreas.h"

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

// Parámetros de los chunches DMX
#define CANALES_MAX 16
#define RANGO_GRADOS_PAN 540
#define RANGO_GRADOS_TILT 180

class vEActor {
  public:
    float x = 0;
    float y = 0;
    float z = 0 ;
    
    vEActor();
    vEActor(float posx, float posy, float posz);
};

class CanalDMX {
  public:
    bool existe = false;
    bool transiciona = false;

    int indice = 0;

    uint8_t valor = 0;
    uint8_t valorInicial = 0;
    uint8_t valorFinal = 0;

    CanalDMX();

    void asignarValorInicial();
    void asignarValorFinal();
};

class ChuncheDMX {
  public:
    ChuncheDMX();

    // Características del chunche DMX
    //char* marca[TEXTO_LARGO_MAX] = "Patito";
    //char* modelo[TEXTO_LARGO_MAX] = "Básico";
    
    // Atributos sobre los canales DMX
    int indiceInicial = 1; // Índice del primer canal para enviar instrucciones al chunche DMX
    char tipo = 'p'; // Tipo de lámpara (PAR: 'p', cabeza móvil: 'c', Otro?)

    CanalDMX dimmer;
    CanalDMX strobe;
    CanalDMX R, G, B, W;
    CanalDMX pan, panFino, tilt, tiltFino;
    CanalDMX velocidadPanTilt;
    CanalDMX GOBO;
    CanalDMX* canal[CANALES_MAX];
    uint16_t pan16bit = 0, tilt16bit = 0;
    int canales = 0; // Cantidad de canales en el chunche DMX
    
    bool enTransicion = false;
    
    void asignarIntensidad(uint8_t valorByte);
    void asignarFrecuencia(uint8_t valorByte);
    void asignarColor(const ColorEA& color);
    void asignarObjetivo(const vEActor& objetivo);
    void iniciarTransicion(uint32_t duracion, char curva);
    
    void actualizar();
    
    void configurar(char modelo, int indice = 1, float x = 0, float y = 0, float z = 0);
    void _actualizarPanTilt();

  private:
    // Posición y orientación del chunche DMX
    // Esto con suerte sirve después para automatizar el reastreo de movimiento y así.
    // La convención que usaríamos sería esta: https://help.malighting.com/grandMA3/2.5/HTML/patch_position_fixtures.html
    vEActor _ubicacion{0, 0, 0};
    vEActor _orientacion{0, 1, 0}; // Se asume que las lámparas están viendo hacia el escenario.
    float _panRangoGrados = RANGO_GRADOS_PAN;
    float _tiltRangoGrados = RANGO_GRADOS_TILT;
    
    // Variables para implementar transiciones
    uint32_t _duracionTransicion = 0;
    uint32_t _tiempoInicioTransicion = 0;
    char _curvaTransicion = 'l';
    
    float _aplicarCurva(float t, char curva);
    //void _actualizarPanTilt();
};

inline const vEActor cero(0, 0, 0);
inline const vEActor uno(1, 1, 0);
inline const vEActor menosUno(-1, -1, 0);
inline const vEActor derechaUno(1, 0, 0);
inline const vEActor izquierdaUno(-1, 0, 0);

inline const vEActor guitarra(-1.65, -1.3, 1.5);
inline const vEActor bajo(1.65, -1.3, 1.5);
inline const vEActor bateria(0, 2.6, 1);

#endif

// Camino en calma
