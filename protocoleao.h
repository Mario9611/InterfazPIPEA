/*
  UCR | EIE | Electrizarte
  protocoleao.h - Librería para implementar el protocolo de comunicación por MQTT de PIPEA
  Escrita por Gustavo Núñez y Teodoro Willink en Septiembre de 2024
  Actualizada por Teodoro Willink en Agosto de 2026
  [Si la actualiza, por favor incluya y ajuste una línea de "Actualizada por X en Y"]
  Código abierto liberado al dominio público
*/

#ifndef protocoleao_h
#define protocoleao_h

// Librerías para WiFi y MQTT (no recuerdo si se ajustan al hardware :v)
#include <WiFi.h>
#include <PubSubClient.h>

// CONSTANTES

// Plataforma de hardware

// Puertos del ESP32
#define LED_PIN 2 // Pin del LED en el ESP32
// Esto se podría cambiar por definir una plataforma de hardware por completo.

// Red WiFi

// Credenciales de la red WiFi de PIPEA
#define WIFI_SSID "PIPEA"
#define WIFI_PASS "electrizartepipea"
//#define WIFI_PASS "usarpipea!"

// MQTT

// Parámetros MQTT para PIPEA
#define MQTT_REPARTIDOR_DIRECCION "192.168.0.100"
//#define MQTT_REPARTIDOR_DIRECCION "192.168.1.101"
#define MQTT_PUERTO 1883
#define MQTT_USUARIO "pipea"
#define MQTT_CONTRASENHA "electrizartepipea"
//#define MQTT_CONTRASENHA "usarpipea!"
#define MQTT_QOS 0

// Tópicos MQTT para PIPEA
#define MQTT_TOPICO_FIJO "pipea/eventos/"
#define MQTT_TOPICO_FIJO_LARGO 14
#define MQTT_TOPICO_LARGO_MAX 32
#define MQTT_ID_LARGO_MAX 16
#define NODOS_MAX 512

// Funciones de reacción
#define REACCION_FIRMA std::function<void(char*, char*)> reaccion
#define REACCION_ESPECS_FIRMA std::function<void(char*, char*, int*, int)> reaccion_especs

// Parámetros PIPEA
#define PERSONAJE_LARGO_MAX 16
#define ACCION_LARGO_MAX 32
#define ESPECS_CANTIDAD_MAX 8
#define ESPECS_LARGO_MAX 4 // Cantidad máxima de dígitos decimales en una especificación
#define PROBA_REVISAR_CONEXION 60000

class nodoPIPEA {
  public:
    char personaje[PERSONAJE_LARGO_MAX];
    char accion[ACCION_LARGO_MAX];
    int especs[ESPECS_CANTIDAD_MAX];
    bool evento = false;
    
    nodoPIPEA();

    void inicio();
    
    void proponer(char* _personaje, char* _accion);
    void proponer(char* _personaje, char* _accion, int* _especs, int _especs_cant);
    REACCION_FIRMA;
    REACCION_ESPECS_FIRMA;
    void atento(char* _personaje, REACCION_FIRMA);
    void atento(char* _personaje, REACCION_ESPECS_FIRMA);
    
    void actualizar();

  private:
    static constexpr char* _wifi_ssid = WIFI_SSID;
    static constexpr char* _wifi_pass = WIFI_PASS;
    
    static constexpr int _especs_cantidad_max = ESPECS_CANTIDAD_MAX;
    int _especs_cantidad;
    char _espec[ESPECS_LARGO_MAX+1]; // Se agrega un caracter adicional para preveer un posible signo '-' si el valor es negativo
    char* _espec_puntero;

    static constexpr char* _mqtt_repartidor_direccion = MQTT_REPARTIDOR_DIRECCION;        // Dirección IP del repartidor (broker) MQTT
    static constexpr int _mqtt_puerto = MQTT_PUERTO;              // Puerto del servicio MQTT
    static constexpr char* _mqtt_usuario = MQTT_USUARIO;          // Usuario del servicio MQTT
    static constexpr char* _mqtt_contrasenha = MQTT_CONTRASENHA;  // Contraseña del servicio MQTT
    
    static constexpr char* _mqtt_topico_fijo = MQTT_TOPICO_FIJO;
    static constexpr int _mqtt_topico_fijo_largo = MQTT_TOPICO_FIJO_LARGO;
    char _mqtt_topico[MQTT_TOPICO_LARGO_MAX];
    
    static constexpr int _mqtt_carga_max = ACCION_LARGO_MAX+ESPECS_CANTIDAD_MAX*(ESPECS_LARGO_MAX+1);
    char _mqtt_carga[_mqtt_carga_max];
    
    static constexpr int _mqtt_qos = MQTT_QOS;        // Calidad de servicio para suscripciones MQTT
    char _mqtt_id[MQTT_ID_LARGO_MAX];
    
    static constexpr unsigned int _proba_revisar_conexion = PROBA_REVISAR_CONEXION;
    
    WiFiClient _esp32_WiFi;
    PubSubClient _cliente_MQTT;

    void _prueba();
    
    void _conectar_WiFi();
    void _conectar_MQTT();
    
    void _reaccion(char* topico, byte* carga, unsigned int tamanho);
    
    void _revisar_conexion();
};

#endif

// Camino en calma
