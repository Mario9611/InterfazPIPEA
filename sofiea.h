/*
  UCR | EIE | Electrizarte
  sofiea.h - Librería para implementar a SofíEA a partir de la pantalla de botellas de Electrizarte
  Escrita por Teodoro Willink y Gustavo Núñez en Septiembre de 2024
  Actualizada por Teodoro Willink en Agosto de 2026
  [Si la actualiza, por favor incluya y ajuste una línea de "Actualizada por X en Y"]
  Código abierto liberado al dominio público
*/

#ifndef sofiea_h
#define sofiea_h

#include "boteallas.h"

#define LED_PIN 2

#define SOFIA_ANCHO 6
#define SOFIA_ALTO 16
#define SOFIA_PIN 13 // Esto no se debe cambiar por la librería FastLED usada por BotEAllas

#define CHISPA_MAX 3
#define CHISPA_TIEMPO 0.1
#define OJOS_YMIN 2
#define OJOS_YMAX 3
#define PARPADEO_TIEMPO 10

#define CUADROS_POR_SEGUNDO 60

class SofiEA {
  public:
    SofiEA();

    int dibujo[SOFIA_ANCHO][SOFIA_ALTO][3];
    botEAllas pantalla;

    void inicio();
    void prueba();
    
    void apagada();    // estado 'a'
    void encendida();  // estado 'e'
    void tranquila();  // estado 'q'
    void feliz();      // estado 'f'
    void triste();     // estado 't'
    void sorpresa();   // estado 'o'
    void sospecha();   // estado 's'
    void susto();      // estado 'u'
    void wacala();     // estado 'w'
    void ok();         // estado 'y'
    void no_ok();      // estado 'n'
    void al_reves();   // estado 'r'
    void izquierda();  // estado 'j'
    void derecha();    // estado 'l'
    void arriba();     // estado 'i'
    void abajo();      // estado 'k'
    void pregunta();   // estado 'p'
    void cuidado();    // estado 'c'
    void emergencia(); // estado 'g'
    void musica();     // estado 'm'

    void actualizar();

  private:
    static constexpr int _ancho = SOFIA_ANCHO;
    static constexpr int _alto = SOFIA_ALTO;
    static constexpr int _pin = SOFIA_PIN;
    static constexpr int _cuadros_por_segundo = CUADROS_POR_SEGUNDO;

    static constexpr int _chispa_max = CHISPA_MAX;
    static constexpr float _chispa_tiempo = CHISPA_TIEMPO;
    static constexpr int _ojos_ymin = OJOS_YMIN;
    static constexpr int _ojos_ymax = OJOS_YMAX;
    static constexpr float _parpadeo_tiempo = PARPADEO_TIEMPO;

    char _estado;
    int _cuadro;

    int _chispa; // intensidad de la chispa de Sofía (de 0 a CHISPA_MAX)
    float _parpadear; // tiempo promedio de parpadeo, en segundos

    int _chispa_amarillo;
    int _chispa_azul;
    int _chispa_cuadros;
    int _esperar_cuadros;

    void _dibujar();
    void _borrar_dibujo();
    void _dibujar_pixel(int x, int y, int r, int g, int b);
    void _calcular_cuadros();
};

#endif

// Camino en calma
