/*
  UCR | EIE | Electrizarte
  luciea.cpp - Librería para implementar el sistema para controlar luces DMX llamado Lucía
  Escrita por Teodoro Willink y Gustavo Núñez en Agosto de 2026
  [Si la actualiza, por favor incluya y ajuste una línea de "Actualizada por X en Y"]
  Código abierto liberado al dominio público
*/

#include "luciea.h"

LuciEA::LuciEA() {
  _duracionCuadro = static_cast<uint32_t>(floor(1000.0/_cuadrosPorSegundo));
  
  // Aquí se inicializan todos los chunches
  _chunche[0].configurar('v', 1);
  _chunches = 1;
  /*
  _chunche[0].configurar('p', 1);
  _chunche[1].configurar('c', 9, 4.85, -2.6, 3);
  //_chunche[1].configurar('c', 9, -4.85, -2.6, 3);
  _chunche[2].configurar('p', 25);
  _chunche[3].configurar('p', 33);
  _chunche[4].configurar('c', 41, 4.85, -2.6, 3);
  //_chunche[4].configurar('c', 41, -4.85, -2.6, 3);
  _chunche[5].configurar('p', 57);
  _chunche[6].configurar('v', 65);
  _chunches = 7;
  */

  definirEscenas();

  definirSecuencias();
  
  pinMode(LED_PIN, OUTPUT);
  //pinMode(PIN_DMX_EN, OUTPUT);
  //digitalWrite(PIN_DMX_EN, HIGH);
  
  //_temporizadorDMX = nullptr;
  
  for (int i=0; i<DMX_PACKET_SIZE; i++)
    _datosDMX[i] = 0;
}

void LuciEA::inicio() {
  // Sólo para despulgar
  INICIAR();
  
  // Sólo para despulgar
  TEXTOLN("Iniciando cosas:");
  
  //_instancia = this; // Esto es para que el DMX funcione con un temporizador y su rutina ISR correspondiente
  
  // Sólo para despulgar
  TEXTO("Controlador DMX... ");
  
  dmx_driver_install(_puertoDMX, &_configuracionDMX, NULL, 0);
  dmx_set_pin(_puertoDMX, PIN_DMX_TX, PIN_DMX_RX, PIN_DMX_EN);
  
  // Sólo para despulgar
  IMPRIMIR("iniciado en el puerto ", _puertoDMX);
  
  // Sólo para despulgar
  //TEXTO("Temporizador DMX... ");
  
  // Esto funciona para el core 3+ de ESP32, pero parece que esp_dmx no está actualizada y tiene un problema en las llamadas a la UART 
  // Initialize ESP32 Core hardware timer (1 MHz base frequency)
  //_temporizadorDMX = timerBegin(1000000);
  // Connect our static callback to the timer system
  //timerAttachInterrupt(_temporizadorDMX, &LuciEA::aTiempoISR);
  // Set alarm to repeat every 25,000 microseconds (25ms = 40Hz DMX stream)
  //timerAlarm(_temporizadorDMX, 25000, true, 0);
  
  // Aquí levanto el temporizador para el core 2.0.17 de ESP32 mientras el compa de la librería esp_dmx decide actualizarla
  // 1. timerBegin(timer_num, prescaler, countUp)
  // Timer 0, Prescaler 80 (80MHz / 80 = 1MHz, meaning 1 tick = 1 microsecond), countUp = true
  // 2. timerAttachInterrupt(timer, &callback, edgeType)
  // Edge triggered interrupt = true
  // 3. timerAlarmWrite(timer, microseconds, autoreload)
  // Trigger every 25,000 microseconds (25ms), autoreload = true
  // 4. Manually enable the alarm in v2.x
  //_temporizadorDMX = timerBegin(0, 80, true);
  //timerAttachInterrupt(_temporizadorDMX, &LuciEA::aTiempoISR, true);
  //timerAlarmWrite(_temporizadorDMX, 25000, true);
  //timerAlarmEnable(_temporizadorDMX);

  // Parece que el temporizador no es una buena idea!

  
  // Sólo para despulgar
  //TEXTOLN("iniciado a 1 MHz y 25 ms");

  _prueba();

  _tiempoUltimoCuadro = millis();
  
  // Sólo para despulgar
  IMPRIMIR("Tiempo del primer cuadro [ms]: ", _tiempoUltimoCuadro);
}

// Esto no va a funcionar, hay que arreglarlo con un efecto que sea una secuencia de escenas
void LuciEA::_prueba() {
  // Sólo para despulgar
  TEXTOLN("Probando cosas:");
  
  delay(2000);
  
  // Sólo para despulgar
  TEXTOLN("Registros del controlador DMX:");
  
  // Para dos pares 'viejo' de prueba
  _datosDMX[1] = 255; // Canal de intensidad
  _datosDMX[3] = 255; // Canal del verde
  _datosDMX[4] = 255; // Canal del azul
  
  /*
  _datosDMX[9] = 255; // Canal de intensidad
  _datosDMX[11] = 255; // Canal del verde
  _datosDMX[12] = 255; // Canal del azul
  
  _datosDMX[33] = 255; // Canal de intensidad
  _datosDMX[35] = 255; // Canal del verde
  _datosDMX[36] = 255; // Canal del azul
  */
  
  // Para las luces de producción
  /*_datosDMX[2] = 255; // Canal del verde
  _datosDMX[3] = 255; // Canal del azul
  //_datosDMX[5] = 255; // Canal de strobe
  _datosDMX[5] = 255; // Canal de la intensidad*/
  
  _datosDMX[9] = 0; // Canal del pan
  _datosDMX[11] = 0; // Canal del tilt
  _datosDMX[14] = 255; // Canal de la intensidad
  _datosDMX[17] = 255; // Canal del verde
  _datosDMX[18] = 255; // Canal del azul
  
  _datosDMX[26] = 255; // Canal del verde
  _datosDMX[27] = 255; // Canal del azul
  _datosDMX[30] = 255; // Canal de la intensidad

  dmx_write(_puertoDMX, _datosDMX, DMX_PACKET_SIZE);
  dmx_send(_puertoDMX);
  
  // Sólo para despulgar
  TEXTOLN("Se ve verde azulado?");
  
  delay(2000);
  
  // Sólo para despulgar
  TEXTOLN("Apagada y encendida:");
  
  encendida();
  actualizar();
  
  delay(2000);
  
  apagada();
  actualizar();
  
  delay(500);
  
  encendida();
  actualizar();
  
  // Sólo para despulgar
  TEXTOLN("Se ve cálido?");
  
  delay(2000);
  
  /*
  // Sólo para despulgar
  TEXTOLN("Color fijo: ");
  
  // Sólo para despulgar
  TEXTO("Color: ");
  COLOR(rojoEA);
  
  color(rojoEA);
  actualizar();
  
  // Sólo para despulgar
  TEXTOLN("Se ve rojoso?");
  
  delay(2000);
  
  // Sólo para despulgar
  TEXTOLN("Paleta monocromática:");
  
  colores(azulEA, 'm', 2*VARIACION_COLORES);
  actualizar();
  
  // Sólo para despulgar
  TEXTOLN("Salieron colores monocromáticos?");
  
  delay(2000);
  
  // Sólo para despulgar
  TEXTOLN("Paleta análoga:");
  
  colores(azulEA, 'a', 0.5*VARIACION_COLORES);
  actualizar();
  
  // Sólo para despulgar
  TEXTOLN("Salieron colores análogos?");
  
  delay(2000);
  
  // Sólo para despulgar
  TEXTOLN("Transición de colores:");
  
  color(verdeEA, 2, 'l');
  for (int i=0; i<2*_cuadrosPorSegundo; i++) {
    actualizar();
    delay(_duracionCuadro);
  }
  
  // Sólo para despulgar
  TEXTOLN("Se ve verdoso?");
  
  delay(2000);
  
  // Sólo para despulgar
  TEXTOLN("Transición de intensidad y color:");
  
  intensidad(0.1);
  actualizar();
  
  delay(500);
  
  encendida(2, 'l');
  for (int i=0; i<2*_cuadrosPorSegundo; i++) {
    actualizar();
    delay(_duracionCuadro);
  }
  
  // Sólo para despulgar
  TEXTOLN("Se ve cálido?");
  
  delay(2000);
  
  // Sólo para despulgar
  TEXTOLN("Movimiento de las cabezas");
  
  posicion(derechaUno);
  actualizar();
  
  // Sólo para despulgar
  TEXTOLN("Apuntan a la derecha?");
  
  delay(2000);
  
  posicion(izquierdaUno);
  actualizar();
  
  // Sólo para despulgar
  TEXTOLN("Apuntan a la izquierda?");
  
  delay(2000);
  
  */

  // Sólo para despulgar
  TEXTOLN("Listas las pruebas. Ahora, ¡a actualizar cosas!");
}

void LuciEA::apagada(float duracion, char curva) {
  _haySecuenciaActiva = false;
  solo = false;
  circulos = 0;
  
  // Sólo para despulgar
  TEXTO("Estableciendo la intensidad en 0... ");
  
  _asignarIntensidad(0);
  
  // Sólo para despulgar
  TEXTOLN("listo");
  
  // Sólo para despulgar
  TEXTO("Asignando la transición... ");
  
  _asignarTransicion(duracion, curva);
  
  // Sólo para despulgar
  IMPRIMIR("listo, sucederá en [s]: ", duracion);
}

void LuciEA::encendida(float duracion, char curva) {
  _haySecuenciaActiva = false;
  solo = false;
  circulos = 0;

  // Sólo para despulgar
  TEXTO("Asignando un color cálido...");
  
  _asignarColor(calido);
  
  // Sólo para despulgar
  TEXTO("listo, quedó en: ");
  COLOR(calido);
  
  // Sólo para despulgar
  TEXTO("Estableciendo la intensidad en 1... ");
  
  _asignarIntensidad(1);
  
  // Sólo para despulgar
  TEXTOLN("listo");
  
  // Sólo para despulgar
  TEXTO("Asignando la transición... ");
  
  _asignarTransicion(duracion, curva);
  
  // Sólo para despulgar
  IMPRIMIR("listo, sucederá en [s]: ", duracion);
}

void LuciEA::intensidad(float valor, char tipoChunche, float duracion, char curva) {
  _haySecuenciaActiva = false;
  solo = false;
  circulos = 0;
  
  // Sólo para despulgar
  TEXTO("Asignando la intensidad... ");
  
  _asignarIntensidad(valor, tipoChunche);
  
  // Sólo para despulgar
  IMPRIMIR("listo, la del primer chunche DMX quedó en: ", _chunche[0].dimmer.valorFinal);
  
  // Sólo para despulgar
  TEXTO("Asignando la transición... ");
  
  _asignarTransicion(duracion, curva);
  
  // Sólo para despulgar
  IMPRIMIR("listo, sucederá en [s]: ", duracion);
}

void LuciEA::color(const ColorEA& color, char tipoChunche, float duracion, char curva) {
  colores(color, '1', 0, tipoChunche, duracion, curva);
}

void LuciEA::colores(const ColorEA& base, char tipoPaleta, float variacion, char tipoChunche, float duracion, char curva) {
  _haySecuenciaActiva = false;
  solo = false;
  circulos = 0;
  
  // Sólo para despulgar
  TEXTO("Color base: ");
  COLOR(base);
  
  // Sólo para despulgar
  TEXTOLN("Generando una paleta de colores:");
  
  int variacionTotal = static_cast<int>(round(variacion*100));
  _generarPaleta(base, tipoPaleta, variacionTotal);
  
  // Sólo para despulgar
  TEXTO("Primer color: ");
  COLOR(_paleta[0]);
  TEXTO("Color en el medio: ");
  COLOR(_paleta[_colores/2-1]);
  TEXTO("Último color: ");
  COLOR(_paleta[_colores-1]);
  
  // Sólo para despulgar
  TEXTO("Asignando los colores... ");
  
  _asignarColores(tipoChunche);
  
  // Sólo para despulgar
  TEXTO("listo, el del primer chunche DMX quedó en: ");
  COLOR(ColorEA(_chunche[0].R.valorFinal, _chunche[0].G.valorFinal, _chunche[0].B.valorFinal));
  
  // Sólo para despulgar
  TEXTO("Estableciendo la transición... ");
  
  _asignarTransicion(duracion, curva);
  
  // Sólo para despulgar
  IMPRIMIR("listo, sucederá en [s]: ", duracion);
}

void LuciEA::posicion(const vEActor& objetivo, float duracion, char curva) {
  _haySecuenciaActiva = false;
  solo = false;
  circulos = 0;
  
  // Sólo para despulgar
  TEXTO("Posición objetivo para apuntar: ");
  POSICION(objetivo);
  
  // Sólo para despulgar
  TEXTO("Asignando las posiciones... ");
  
  _asignarObjetivo(objetivo);
  
  // Sólo para despulgar
  TEXTO("listo, la del segundo chunche DMX quedó en: ");
  VARIABLE(_chunche[1].pan.valorFinal);
  TEXTO(", ");
  VARIABLELN(_chunche[1].tilt.valorFinal);
  
  // Sólo para despulgar
  TEXTO("Estableciendo la transición... ");
  
  _asignarTransicion(duracion, curva);
  
  // Sólo para despulgar
  IMPRIMIR("listo, sucederá en [s]: ", duracion);
}

void LuciEA::posiciones(float variacion, float duracion, char curva) {
  _haySecuenciaActiva = false;
  solo = false;
  circulos = 0;
  
  // Sólo para despulgar
  TEXTOLN("Generando una paleta de colores:");
  
  int variacionTotal = static_cast<int>(round(variacion*100));
  _generarObjetivos(variacionTotal);
  
  // Sólo para despulgar
  TEXTO("Posición objetivo para apuntar: ");
  //POSICION(objetivo);
  
  // Sólo para despulgar
  TEXTO("Asignando las posiciones... ");
  
  _asignarObjetivos();
  
  // Sólo para despulgar
  TEXTO("listo, la del segundo chunche DMX quedó en: ");
  VARIABLE(_chunche[1].pan.valorFinal);
  TEXTO(", ");
  VARIABLELN(_chunche[1].tilt.valorFinal);
  
  // Sólo para despulgar
  TEXTO("Estableciendo la transición... ");
  
  _asignarTransicion(duracion, curva);
  
  // Sólo para despulgar
  IMPRIMIR("listo, sucederá en [s]: ", duracion);
}

void LuciEA::postura(uint16_t pan, uint16_t tilt, float duracion, char curva) {
  _haySecuenciaActiva = false;
  solo = false;
  circulos = 0;
  
  // Sólo para despulgar
  TEXTO("Postura de las cabezas con pan y tilt: "); VARIABLE(pan); TEXTO(" "); VARIABLELN(tilt);
  
  // Sólo para despulgar
  TEXTO("Asignando los valores (correspondientes a ángulos)... ");
  
  _asignarPostura(pan, tilt);
  
  // Sólo para despulgar
  TEXTO("listo, la del segundo chunche DMX quedó en: ");
  VARIABLE(_chunche[1].pan.valorFinal);
  TEXTO(", ");
  VARIABLELN(_chunche[1].tilt.valorFinal);
  
  // Sólo para despulgar
  TEXTO("Estableciendo la transición... ");
  
  _asignarTransicion(duracion, curva);
  
  // Sólo para despulgar
  IMPRIMIR("listo, sucederá en [s]: ", duracion);
}

void LuciEA::escena(const EAscena& escena) {
  _haySecuenciaActiva = false;
  solo = false;
  circulos = 0;

  // Sólo para despulgar
  TEXTOLN("Presentando la escena actual:");
  TEXTO("Como referencia, el color base para los PARes es: ");
  //COLOR(escena.colorBasePARes);
  
  if (escena.intensidad.has_value())
    _asignarIntensidad(*escena.intensidad);
  
  if (escena.intensidadPARes.has_value())
    _asignarIntensidad(*escena.intensidadPARes, 'p');
  
  if (escena.intensidadCabezas.has_value())
    _asignarIntensidad(*escena.intensidadCabezas, 'c');

  //_asignarFrecuencia(escena->frecuenciaParpadeo);
  
  if (escena.colorBase.has_value()) {
    _generarPaleta(*escena.colorBase, *escena.tipoPaleta, *escena.variacion);
    _asignarColores();
  }

  if (escena.colorBasePARes.has_value()) {
    _generarPaleta(*escena.colorBasePARes, *escena.tipoPaletaPARes, *escena.variacionPARes);
    _asignarColores('p');
  }
  
  if (escena.colorBaseCabezas.has_value()) {
    _generarPaleta(*escena.colorBaseCabezas, *escena.tipoPaletaCabezas, *escena.variacionCabezas);
    _asignarColores('c');
  }

  if (escena.objetivoCabezas.has_value())
    _asignarObjetivo(*escena.objetivoCabezas);

  if (escena.objetivosCabezas.has_value())
    _asignarObjetivos();

  //_asignarGOBO();

  if (escena.duracionTransicion.has_value())
    _asignarTransicion(*escena.duracionTransicion, *escena.curvaTransicion);

  if (escena.duracionTransicionPARes.has_value())
    _asignarTransicion(*escena.duracionTransicionPARes, *escena.curvaTransicionPARes);

  if (escena.duracionTransicionCabezas.has_value())
    _asignarTransicion(*escena.duracionTransicionCabezas, *escena.curvaTransicionCabezas);
}

void LuciEA::secuencia(const SecuEAncia& secuencia, int indiceEscena) {
  _secuenciaActiva = secuencia;
  
  int actual = _secuenciaActiva.asignarEscena(indiceEscena);
  escena(_secuenciaActiva.escena[actual]);
  
  // Sólo para despulgar
  IMPRIMIR("Sigue la escena ", actual);
  TEXTO("Como referencia, el color es: ");
  //COLOR(_escenaActual.colorPARes);
  
  _haySecuenciaActiva = true;
}

void LuciEA::manhana() {
  //colores(color(255, 255, 127));
  //vivo();
}

void LuciEA::actualizar() {
  // Tiempos de los cuadros
  if (millis() - _tiempoUltimoCuadro >= _duracionCuadro) {
    // Sólo para despulgar
    TEXTO("dt: "); VARIABLE(millis() - _tiempoUltimoCuadro); TEXTO(" ms (de "); VARIABLE(_duracionCuadro); TEXTO(" ms)");

    // Secuencias
    if (_haySecuenciaActiva && _secuenciaActiva.escenaLista()) {
      // Sólo para despulgar
      TEXTO("Terminó una escena de la secuencia activa ");
      
      if (_secuenciaActiva.ultimaEscena()) {
        // Sólo para despulgar
        TEXTOLN("y era la última, entonces desactivamos la secuencia.");
        
        _haySecuenciaActiva = false;
      } else {
        // Sólo para despulgar
        TEXTOLN("pero hay más, entonces activamos la siguiente.");
        
        secuencia(_secuenciaActiva, _secuenciaActiva.siguienteEscena());
      }
    }

    // Efecto de mover las cabezas en círculo (digo yo)
    if (circulos > 0)
      for (int i=0; i<_chunches; i++)
        if (_chunche[i].tipo == 'c') {
          _chunche[i].pan16bit = 32767 + static_cast<uint16_t>(round(circulos*sin(2*M_PI*velocidad*millis())));
          _chunche[i].tilt16bit = 32767 + static_cast<uint8_t>(round(circulos*cos(2*M_PI*velocidad*millis())));

          _chunche[i]._actualizarPanTilt();
        }

    if (solo) {
      _asignarIntensidad(0.2, 'p');
    }

    _tiempoUltimoCuadro = millis();
  
    // Sólo para despulgar
    //IMPRIMIR("Tiempo del último cuadro [ms]: ", _tiempoUltimoCuadro);

  //}

  // Tiempos de las tramas DMX (~25 ms)
  //if (millis() - _tiempoUltimaTramaDMX >= _duracionTramaDMX) {
    //if (dmx_wait_sent(_puertoDMX, 0)) {
      // Sólo para despulgar
      TEXTO("dt: "); VARIABLE(millis() - _tiempoUltimaTramaDMX); TEXTO(" ms");

      _tiempoUltimaTramaDMX = millis();

      // Actualizo los valores de los chunches DMX según la transición de cada uno.
      for (int i=0; i<_chunches; i++)
        _chunche[i].actualizar();

      // Construimos la trama DMX por enviar
      for (int i=0; i<_chunches; i++)
        for (int j=0; j<_chunche[i].canales; j++)
          if (_chunche[i].canal[j]->existe)
            _datosDMX[(_chunche[i].indiceInicial-1) + _chunche[i].canal[j]->indice] = _chunche[i].canal[j]->valor;

      // Sólo para despulgar
      TEXTO(" | Trama: ["); ARREGLO(_datosDMX, 32); TEXTO(" ...]");

      // Enviamos la trama DMX actualizada
      dmx_wait_sent(_puertoDMX, DMX_TIMEOUT_TICK);
      dmx_write(_puertoDMX, _datosDMX, DMX_PACKET_SIZE);
      dmx_send(_puertoDMX);

      // Sólo para despulgar
      TEXTOLN(" | enviada!");
    }
  //}

    // Envío la trama DMX actualizada
    //dmx_write(_puertoDMX, _datosDMX, DMX_PACKET_SIZE);
    //dmx_send(_puertoDMX); // Esto no debería ser necesario con el temporizador
    
    // Sólo para despulgar
    //TEXTOLN("listo (las tramas se envían con el temporizador)");
}

void LuciEA::_asignarIntensidad(float valor, char tipo) {
  uint8_t valorByte = static_cast<uint8_t>(round(valor*255)); // static_cast<>() es necesario!

  for (int i=0; i<_chunches; i++)
    if (_chunche[i].tipo == tipo || tipo == 't')
      _chunche[i].asignarIntensidad(valorByte);
}

void LuciEA::_asignarFrecuencia(float valor, char tipo) {
  uint8_t valorByte = static_cast<uint8_t>(round(valor*255));
  
  for (int i=0; i<_chunches; i++)
    if (_chunche[i].tipo == tipo || tipo == 't')
      _chunche[i].asignarFrecuencia(valorByte);
}

void LuciEA::_asignarColor(const ColorEA& color, char tipo) {
  for (int i=0; i<_chunches; i++)
    if (_chunche[i].tipo == tipo || tipo == 't')
      _chunche[i].asignarColor(color);
}

void LuciEA::_asignarColores(char tipo) {
  for (int i=0; i<_chunches; i++)
    if (_chunche[i].tipo == tipo || tipo == 't')
      _chunche[i].asignarColor(_paleta[random(_colores)]);
}

void LuciEA::_asignarObjetivo(const vEActor& objetivo) {
  for (int i=0; i<_chunches; i++)
    if (_chunche[i].tipo == 'c')
      _chunche[i].asignarObjetivo(objetivo);    
}

void LuciEA::_generarObjetivos(int variacionTotal, int cantidad) {
  if (cantidad <= 0) return;

  for (int i=0; i<cantidad; i++) {
    vEActor nuevoObjetivo(random(-variacionTotal, variacionTotal), random(-variacionTotal, variacionTotal), random(-variacionTotal, variacionTotal));

    _objetivo[i] = nuevoObjetivo;
  }
}

void LuciEA::_asignarObjetivos() {
  for (int i=0; i<_chunches; i++)
    if (_chunche[i].tipo == 'c')
      _chunche[i].asignarObjetivo(_objetivo[random(_objetivos)]);
}

void LuciEA::_asignarPostura(uint16_t pan, uint16_t tilt) {
  for (int i=0; i<_chunches; i++)
    if (_chunche[i].tipo == 'c') {
      _chunche[i].pan16bit = pan;
      _chunche[i].tilt16bit = tilt;

      _chunche[i]._actualizarPanTilt();
    }
}

void LuciEA::_asignarTransicion(float duracion, char curva) {
  uint32_t duracionMiliSegundos = static_cast<uint32_t>(round(duracion*1000));
  
  for (int i=0; i<_chunches; i++)
    _chunche[i].iniciarTransicion(duracionMiliSegundos, curva);
}

// Saqué los tipos de paletas de aquí: https://www.figma.com/resource-library/types-of-color-palettes/
void LuciEA::_generarPaleta(ColorEA base, char tipo, int variacionTotal, int cantidad) {
  if (cantidad <= 0) return;

  base.hsv();

  switch (tipo) {
    // Todas las luces con el mismo color
    case '1':
      for (int i=0; i<cantidad; i++)
        _paleta[i] = base;
      break;
    
    // Paleta monocromática (varía el brillo)
    case 'm': {
      float variacionV = static_cast<float>(variacionTotal) / cantidad;

      for (int i=0; i<cantidad; i++) {
        ColorEA nuevoColor = base;

        // Distribución simétrica (i=1 aclara, i=2 oscurece, i=3 aclara más, etc.)
        int paso = (i + 1) / 2;
        int direccion = (i % 2 == 1) ? 1 : -1;
        
        // Calcular el nuevo brillo
        // std::clamp asegura que el brillo permanezca estrictamente entre 0 y 100%
        nuevoColor.v = constrain(base.v + (direccion * paso * variacionV), 0, 100);

        // Sincronizar los componentes RGB del nuevo color
        nuevoColor.rgb();
        _paleta[i] = nuevoColor;
      }

      break;
    }
    
    // Paleta pastel (varía la saturación)
    case 'p': {
      float variacionS = static_cast<float>(variacionTotal) / cantidad;

      for (int i=0; i<cantidad; i++) {
        ColorEA nuevoColor = base;

        // Distribución simétrica (i=1 aclara, i=2 oscurece, i=3 aclara más, etc.)
        int paso = (i + 1) / 2;
        int direccion = (i % 2 == 1) ? 1 : -1;
        
        // Calcular la nueva saturación
        // std::clamp asegura que la saturación permanezca estrictamente entre 0 y 100%
        nuevoColor.s = constrain(base.s + (direccion * paso * variacionS), 0, 100);

        // Sincronizar los componentes RGB del nuevo color
        nuevoColor.rgb();
        _paleta[i] = nuevoColor;
      }

      break;
    }
    
    // Paleta diversa (varían el brillo y la saturación)
    case 'd': {
      float variacionVS = static_cast<float>(variacionTotal) / cantidad;

      for (int i=0; i<cantidad; i++) {
        ColorEA nuevoColor = base;

        // Distribución simétrica (i=1 aclara, i=2 oscurece, i=3 aclara más, etc.)
        int paso = (i + 1) / 2;
        int direccion = (i % 2 == 1) ? 1 : -1;
        
        // Calcular los nuevos valores
        nuevoColor.v = constrain(base.v + (direccion * paso * variacionVS), 0, 100);
        nuevoColor.s = constrain(base.s + (direccion * paso * variacionVS), 0, 100);

        // Sincronizar los componentes RGB del nuevo color
        nuevoColor.rgb();
        _paleta[i] = nuevoColor;
      }

      break;
    }
    
    // Paleta análoga (varía el tono)
    case 'a': {
      float variacionAngulo = static_cast<float>(variacionTotal)/100*360 / cantidad;

      for (int i=0; i<cantidad; i++) {
        ColorEA nuevoColor = base;
        
        // Determina la dirección del paso (ej. +1, -1, +2, -2...)
        int paso = (i + 1) / 2; 
        int direccion = (i % 2 == 1) ? 1 : -1;

        // Calcular el nuevo tono
        nuevoColor.h = base.h + static_cast<int>(round(direccion * paso * variacionAngulo));

        // Sincronizar los componentes RGB del nuevo color
        nuevoColor.rgb();
        _paleta[i] = nuevoColor;
      }

      break;
    }
    
    // Paleta muy diversa (varían el tono, la saturación y el brillo)
    case 'D': {
      float variacionAngulo = static_cast<float>(variacionTotal)/100*360 / cantidad;
      float variacionVS = static_cast<float>(variacionTotal) / cantidad;

      for (int i=0; i<cantidad; i++) {
        ColorEA nuevoColor = base;
        
        // Determina la dirección del paso (ej. +1, -1, +2, -2...)
        int paso = (i + 1) / 2; 
        int direccion = (i % 2 == 1) ? 1 : -1;

        // Calcular los nuevos valores
        nuevoColor.v = constrain(base.v + (direccion * paso * variacionVS), 0, 100);
        nuevoColor.s = constrain(base.s + (direccion * paso * variacionVS), 0, 100);
        nuevoColor.h = base.h + static_cast<int>(round(direccion * paso * variacionAngulo));

        // Sincronizar los componentes RGB del nuevo color
        nuevoColor.rgb();
        _paleta[i] = nuevoColor;
      }

      break;
    }
    
    // Paleta complementaria
    case '2':
      // Hay que calcular colores complementarios
      break;
    
    // Paleta triádica
    case '3':
      // Hay que calcular colores triádicos
      break;
    
    // Paleta tetrádica
    case '4':
      // Hay que calcular colores tetrádicos
      break;
    
    default:
      // Todo negro
      break;
  }
}


/*
void LuciEA::_asignarIntensidad(float valor, ChuncheDMX* chunche) {
  uint8_t valorByte = static_cast<uint8_t>(round(valor*255)); // static_cast<>() es necesario!

  chunche.asignarIntensidad(valorByte);
}

void LuciEA::_asignarFrecuencia(float valor, ChuncheDMX* chunche) {
  uint8_t valorByte = static_cast<uint8_t>(round(valor*255)); // static_cast<>() es necesario!

  chunche.asignarFrecuencia(valorByte);
}

void LuciEA::_asignarColor(const ColorEA& color, ChuncheDMX* chunche) {
  chunche.asignarColor(color);
}

void LuciEA::_asignarPosicion(const vEActor& objetivo, ChuncheDMX* chunche) {
  chunche.asignarObjetivo(objetivo);
}

void LuciEA::_asignarTransicion(float duracion, char curva, ChuncheDMX* chunche) {
  uint32_t duracionMiliSegundos = static_cast<uint32_t>(round(duracion*1000));
  
  chunche.iniciarTransicion(duracionMiliSegundos, curva);
}
*/

// CRUCIAL: In C++, static members must be explicitly initialized outside the class definition
//LuciEA* LuciEA::_instancia = nullptr;

// The isolated hardware ISR routine
/*void IRAM_ATTR LuciEA::aTiempoISR() {
  if (_instancia != nullptr) {
    // Blasts the buffer to the hardware layer instantly (<1 microsecond)
    dmx_send(_instancia->_puertoDMX);
  }
}*/




// Camino en calma
