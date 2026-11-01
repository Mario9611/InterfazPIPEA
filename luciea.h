/*
  UCR | EIE | Electrizarte
  luciea.h - Librería para implementar el sistema para controlar luces DMX llamado Lucía
  Escrita por Teodoro Willink y Gustavo Núñez en Agosto de 2026
  [Si la actualiza, por favor incluya y ajuste una línea de "Actualizada por X en Y"]
  Código abierto liberado al dominio público
*/

#ifndef luciea_h
#define luciea_h

#include <Arduino.h>
#include <esp_dmx.h>

#include "coloreas.h"
#include "chunchesdmx.h"
#include "eambientes.h"

// Macros para despulgar
#define DESPULGAR 0

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

#define LED_PIN 2

// Parámetros del controlador DMX
#define PIN_DMX_TX 17
#define PIN_DMX_RX 16
#define PIN_DMX_EN 4
#define DURACION_TRAMA_DMX 25

#define CHUNCHES_MAX 8

#define CUADROS_POR_SEGUNDO 40 // El tiempo de un cuadro (1/CUADROS_POR_SEGUNDO) DEBE ser mayor que el tiempo asumido que toma enviar una trama DMX (y este valor, a su vez, DEBE ser mayor a la duración real). Después de indicar que se envíe una trama DMX, se debe esperar este tiempo como mínimo para volver a enviar otra trama DMX (de forma que le alcance a la UART para enviar todos los datos y no hacer una escritura asincrónica).


class LuciEA {
  public:
    LuciEA();
    // El nombre de cualquier instancia de LucíEA es Lucía, y para diferenciarlas se establece un apellido distinto para cada una.
    // Así, por ejemplo, instancias de LucíEA podrían ser Segura (Lucía Segura), Fallas (Lucía Fallas), Flores (Lucía Flores), etc.
    
    // Protocolo? https://posistage.net/#about
    // Mapa? https://www.vectorworks.net/en-US/newsroom/whats-a-light-plot-how-to-draw-guide

    void inicio();

    // EAscenas
    void apagada(float duracion = 0, char curva = 'l');
    void encendida(float duracion = 0, char curva = 'l');

    void intensidad(float valor, char tipoChunche = 't', float duracion = 0, char curva = 'l');
    void color(const ColorEA& color, char tipoChunche = 't', float duracion = 0, char curva = 'l');
    void colores(const ColorEA& base, char paleta, float variacion, char tipoChunche = 't', float duracion = 0, char curva = 'l');

    void posicion(const vEActor& objetivo, float duracion = 0, char curva = 'l');
    void posiciones(float variacion, float duracion = 0, char curva = 'l');
    void postura(uint16_t pan, uint16_t tilt, float duracion = 0, char curva = 'l');

    void escena(const EAscena& escena);
    void secuencia(const SecuEAncia& secuencia, int indiceEscena = 0);

    // EAfectos
    int circulos = 0;
    float velocidad = 1;
    bool solo = false;
    
    // EAmbientes
    void manhana();
    void noche();
    void lluvia();
    void especial();
    
    void actualizar();

  private:
    // Atributos sobre el controlador DMX
    static constexpr dmx_port_t _puertoDMX = DMX_NUM_1;
    uint8_t _datosDMX[DMX_PACKET_SIZE];
    static constexpr dmx_config_t _configuracionDMX = DMX_CONFIG_DEFAULT; // Mejor directamente en la función de inicio, porque no lo vamos a manipular.
    uint32_t _tiempoUltimaTramaDMX = 0;
    static constexpr uint32_t _duracionTramaDMX = DURACION_TRAMA_DMX;
    //hw_timer_t* _temporizadorDMX; // Le estoy poniendo un temporizador por hardware para no bloquear el loop pero que las tramas DMX se envíen a tiempo
    //static LuciEA* _instancia;
    
    // The isolated hardware ISR routine
    //static void IRAM_ATTR aTiempoISR();

    // Atributos sobre chunches DMX
    // Tal vez esto puede servir: https://gdtf-share.com/
    ChuncheDMX _chunche[CHUNCHES_MAX];
    int _chunches = 0; // Cantidad de chunches DMX en la instancia de LucíEA
    
    // Secuencia activa
    SecuEAncia _secuenciaActiva;
    bool _haySecuenciaActiva = false;
    
    // Efectos
    EAfecto _efecto[EFECTOS_MAX];
    int _efectos = 1;

    // Círculos
    int sentido = 1; // '1' es aumentar los valores, '-1' es reducir los valores.

    // Atributos sobre los cuadros?
    static constexpr int _cuadrosPorSegundo = CUADROS_POR_SEGUNDO;
    uint32_t _duracionCuadro = 0;
    uint32_t _tiempoUltimoCuadro = 0;

    static constexpr int _colores = CHUNCHES_MAX;
    ColorEA _paleta[CHUNCHES_MAX];
    
    static constexpr int _objetivos = CHUNCHES_MAX;
    vEActor _objetivo[CHUNCHES_MAX];

    void _prueba();

    void _asignarIntensidad(float valor, char tipoChunche = 't'); // Qué tal asignar intensidades distintas?
    void _asignarFrecuencia(float valor, char tipoChunche = 't'); // Qué tal asignar frecuencias distintas?
    void _asignarColor(const ColorEA& color, char tipoChunche = 't');
    void _generarPaleta(ColorEA base, char tipoPaleta, int variacionTotal = VARIACION_COLORES, int cantidad = _colores);
    void _asignarColores(char tipoChunche = 't');
    void _asignarObjetivo(const vEActor& objetivo);
    void _generarObjetivos(int variacionTotal = VARIACION_COLORES, int cantidad = _objetivos);
    void _asignarObjetivos();
    void _asignarPostura(uint16_t pan, uint16_t tilt);
    //void _asignarGOBO(int indice); // Qué tal asignar transiciones distintas?
    void _asignarTransicion(float duracion, char curva); // Qué tal asignar transiciones distintas?
    
    // Funciones para cambiar un chunche a la vez.
    /*void _asignarIntensidad(float valor, ChuncheDMX* chunche);
    void _asignarFrecuencia(float valor, ChuncheDMX* chunche);
    void _asignarColor(const ColorEA& color, ChuncheDMX* chunche);
    void _asignarPosicion(const vEActor& objetivo, ChuncheDMX* chunche);
    void _asignarGOBO(int indice, ChuncheDMX* chunche);
    void _asignarTransicion(float duracion, char curva, ChuncheDMX* chunche);*/
};

#endif

// Camino en calma
