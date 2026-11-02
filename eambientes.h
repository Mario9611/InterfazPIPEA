/*
  UCR | EIE | Electrizarte
  EAmbientes.h - Librería para definir ambientes
  Escrita por Teodoro Willink y Gustavo Núñez en Agosto de 2026
  [Si la actualiza, por favor incluya y ajuste una línea de "Actualizada por X en Y"]
  Código abierto liberado al dominio público
*/

#ifndef eambientes_h
#define eambientes_h

#include <optional>

#include "coloreas.h"
#include "chunchesdmx.h"

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

#define VARIACION_COLORES 0.2 // 0 a 1

#define ESCENAS_MAX 8
#define EFECTOS_MAX 16
#define SECUENCIAS_MAX 16
#define EAMBIENTES_MAX 8

class EAscena {
  public:
    std::optional<float> intensidad = std::nullopt;
    std::optional<float> intensidadPARes = std::nullopt;
    std::optional<float> intensidadCabezas = std::nullopt;
    std::optional<ColorEA> colorBase= std::nullopt;
    std::optional<ColorEA> colorBasePARes = std::nullopt;
    std::optional<ColorEA> colorBaseCabezas = std::nullopt;
    std::optional<char> tipoPaleta = std::nullopt;
    std::optional<char> tipoPaletaPARes = std::nullopt;
    std::optional<char> tipoPaletaCabezas = std::nullopt;
    std::optional<int> variacion = std::nullopt;
    std::optional<int> variacionPARes = std::nullopt;
    std::optional<int> variacionCabezas = std::nullopt;
    std::optional<vEActor> objetivoCabezas = std::nullopt;
    std::optional<bool> objetivosCabezas = std::nullopt;
    std::optional<float> duracionTransicion = std::nullopt;
    std::optional<float> duracionTransicionPARes = std::nullopt;
    std::optional<float> duracionTransicionCabezas = std::nullopt;
    std::optional<char> curvaTransicion = std::nullopt;
    std::optional<char> curvaTransicionPARes = std::nullopt;
    std::optional<char> curvaTransicionCabezas = std::nullopt;
    
    EAscena();

  private:

};

class SecuEAncia {
  public:
    bool repite = false;
    bool aleatoria = false;

    EAscena escena[ESCENAS_MAX];
    float duracionEscena[ESCENAS_MAX];
    int escenas = 0;
    
    SecuEAncia();
    
    int asignarEscena(int indice = 0);
    bool escenaLista();
    bool ultimaEscena();
    int siguienteEscena();

  private:
    int _actual = 0;
    uint32_t _tiempoInicioEscena = 0;
};

class EAfecto {
  public:
    bool activo = false;
    
    EAfecto();
};

// Definimos escenas para EA
inline EAscena oscura;
inline EAscena coloresFrios;
inline EAscena coloresCalidos;
inline EAscena coloresVivos;

void definirEscenas();

// Definimos secuencias para EA
inline SecuEAncia introOscura;
inline SecuEAncia frioSuave;
inline SecuEAncia frioFuerte;
inline SecuEAncia calidoSuave;
inline SecuEAncia calidoFuerte;
inline SecuEAncia cumbiaSuave;
inline SecuEAncia cumbiaFuerte;

void definirSecuencias();

#endif

// Camino en calma
