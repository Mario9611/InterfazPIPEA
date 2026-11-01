/*
  UCR | EIE | Electrizarte
  protocoleao.cpp - Librería para implementar el protocolo de comunicación por MQTT de PIPEA
  Escrita por Gustavo Núñez y Teodoro Willink en Septiembre de 2024
  Actualizada por Teodoro Willink en Agosto de 2026
  [Si la actualiza, por favor incluya y ajuste una línea de "Actualizada por X en Y"]
  Código abierto liberado al dominio público
*/

#include "protocoleao.h"

nodoPIPEA::nodoPIPEA() : _cliente_MQTT(_mqtt_repartidor_direccion, _mqtt_puerto, _esp32_WiFi) {

}

void nodoPIPEA::inicio() {
  _conectar_WiFi();
  
  _conectar_MQTT();
  
  pinMode(LED_PIN, OUTPUT);
  
  digitalWrite(LED_PIN, HIGH);
  delay(500);
  digitalWrite(LED_PIN, LOW);
  delay(500);
  digitalWrite(LED_PIN, HIGH);
  delay(500);
  digitalWrite(LED_PIN, LOW);
  delay(500);
  digitalWrite(LED_PIN, HIGH);
  delay(500);
  digitalWrite(LED_PIN, LOW);
  delay(500);

  _prueba();
}

void nodoPIPEA::_prueba() {
  digitalWrite(LED_PIN, HIGH);
  delay(100);
  digitalWrite(LED_PIN, LOW);
  delay(100);
  digitalWrite(LED_PIN, HIGH);
  delay(100);
  digitalWrite(LED_PIN, LOW);
  delay(100);
  digitalWrite(LED_PIN, HIGH);
  delay(100);
  digitalWrite(LED_PIN, LOW);
  delay(100);
  
  proponer("pruebas", "parpadeo");
  
  delay(2000);
  
  int _especs_prueba[] = {4,2,1000};
  proponer("pruebas", "apagadeo", _especs_prueba, 3);
}

void nodoPIPEA::proponer(char* _personaje, char* _accion) {
  strcpy(_mqtt_topico, _mqtt_topico_fijo);
  strcat(_mqtt_topico, _personaje);
  
  //memset(_mqtt_carga, 0, _mqtt_carga_max);
  strcpy(_mqtt_carga, _accion);
  strcat(_mqtt_carga, ":");
  
  _cliente_MQTT.publish(_mqtt_topico, _mqtt_carga);
}

void nodoPIPEA::proponer(char* _personaje, char* _accion, int* _especs, int _especs_cant) {
  strcpy(_mqtt_topico, _mqtt_topico_fijo);
  strcat(_mqtt_topico, _personaje);
  
  strcpy(_mqtt_carga, _accion);
  strcat(_mqtt_carga, ":");
  
  for (int i=0; i<_especs_cant; i++) {
    itoa(_especs[i], _espec, 10);
    strcat(_mqtt_carga, _espec);
    strcat(_mqtt_carga, ",");
  }
  
  _cliente_MQTT.publish(_mqtt_topico, _mqtt_carga);
}

void nodoPIPEA::atento(char* _personaje, REACCION_FIRMA) {
  strcpy(_mqtt_topico, _mqtt_topico_fijo);
  strcat(_mqtt_topico, _personaje);
  
  _cliente_MQTT.subscribe(_mqtt_topico, _mqtt_qos);
  
  this->reaccion = reaccion;
  
  _cliente_MQTT.setCallback([this](char* topico, byte* carga, unsigned int tamanho) {
    _reaccion(topico, carga, tamanho);
  });
}

void nodoPIPEA::atento(char* _personaje, REACCION_ESPECS_FIRMA) {
  strcpy(_mqtt_topico, _mqtt_topico_fijo);
  strcat(_mqtt_topico, _personaje);
  
  _cliente_MQTT.subscribe(_mqtt_topico, _mqtt_qos);
  
  this->reaccion_especs = reaccion_especs;
  
  _cliente_MQTT.setCallback([this](char* topico, byte* carga, unsigned int tamanho) {
    _reaccion(topico, carga, tamanho);
  });
}

void nodoPIPEA::actualizar() {
  _revisar_conexion();
  
  _cliente_MQTT.loop();
}

void nodoPIPEA::_conectar_WiFi() {
  WiFi.begin(_wifi_ssid, _wifi_pass);
  
  delay(2000);
  
  while (WiFi.status() != WL_CONNECTED)
    delay(500);
  
  WiFi.setSleep(false);
}

void nodoPIPEA::_conectar_MQTT() {
  sprintf(_mqtt_id, "nodo_pipea_%d", random(NODOS_MAX));
  
  _cliente_MQTT.setBufferSize(_mqtt_carga_max);
  
  while (!_cliente_MQTT.connect(_mqtt_id, _mqtt_usuario, _mqtt_contrasenha))
    delay(500);
}

void nodoPIPEA::_reaccion(char* topico, byte* carga, unsigned int tamanho) {
  // Cuando escribí esta función, sólo Dios y yo sabíamos cómo funciona
  strcpy(personaje, &topico[_mqtt_topico_fijo_largo]);
  
  strncpy(_mqtt_carga, (char*)carga, tamanho);
  _mqtt_carga[tamanho] = 0;
  
  strcpy(accion, strtok(_mqtt_carga,":"));
  
  if (reaccion)
    reaccion(personaje, accion);
  
  if (reaccion_especs) {
    for (int i=0; i<_especs_cantidad_max; i++)
      especs[i] = 0;
    
    _especs_cantidad = 0;
    _espec_puntero = strtok(NULL,",");
    while (_espec_puntero) {
      especs[_especs_cantidad] = atoi(_espec_puntero);
      _especs_cantidad++;
      _espec_puntero = strtok(NULL,",");
    }

    reaccion_especs(personaje, accion, especs, _especs_cantidad);
  }
}

void nodoPIPEA::_revisar_conexion() {
  if (random(_proba_revisar_conexion) == 0) {
    if (WiFi.status() != WL_CONNECTED)
      WiFi.reconnect();
      
    if (!_cliente_MQTT.connected())
      _cliente_MQTT.connect(_mqtt_id, _mqtt_usuario, _mqtt_contrasenha);
  }
}

// Camino en calma
