/*
  UCR | EIE | Electrizarte
  chunchesDMX.cpp - Librería para modelar chunches DMX
  Escrita por Teodoro Willink y Gustavo Núñez en Agosto de 2026
  [Si la actualiza, por favor incluya y ajuste una línea de "Actualizada por X en Y"]
  Código abierto liberado al dominio público
*/

#include "chunchesdmx.h"


vEActor::vEActor() {

}

vEActor::vEActor(float posx, float posy, float posz) {
  x = posx;
  y = posy;
  z = posz;
}


CanalDMX::CanalDMX() {

}

void CanalDMX::asignarValorInicial() {
  valorInicial = valor;
}

void CanalDMX::asignarValorFinal() {
  valor = valorFinal;
}


ChuncheDMX::ChuncheDMX() {
  canal[0] = &dimmer;
  canal[1] = &strobe;
  canal[2] = &R;
  canal[3] = &G;
  canal[4] = &B;
  canal[5] = &W;
  canal[6] = &pan;
  canal[7] = &panFino;
  canal[8] = &tilt;
  canal[9] = &tiltFino;
  canal[10] = &velocidadPanTilt;
  canal[11] = &GOBO;

  dimmer.transiciona = true;
  R.transiciona = true;
  G.transiciona = true;
  B.transiciona = true;
  W.transiciona = true;
}

void ChuncheDMX::configurar(char modelo, int indice, float x, float y, float z) {
  //marca = "Patito";
  //modelo = "Básico";
  
  indiceInicial = indice;
  
  switch (modelo) {
    // Chunche DMX tipo PAR de las viejitas
    case 'v':
      tipo = 'p';
      
      dimmer.existe = true;
      strobe.existe = true;
      R.existe = true;
      G.existe = true;
      B.existe = true;

      canales = 5;
      
      dimmer.indice = 1;
      strobe.indice = 5;
      R.indice = 2;
      G.indice = 3;
      B.indice = 4;
      
      strobe.valor = 0;

      break;
      
    // PARes 'nuevos' en EA: ELIMINATOR MEGA PAR PROFILE EP, configurados en modo de 6 canales
    case 'p':
      tipo = 'p';
      
      dimmer.existe = true;
      //strobe.existe = true;
      R.existe = true;
      G.existe = true;
      B.existe = true;

      canales = 4;
      
      dimmer.indice = 5;
      //strobe.indice = 5;
      R.indice = 1;
      G.indice = 2;
      B.indice = 3;
      
      //strobe.valor = 255;

      break;

    // Cabezas móviles 'nuevas' en EA: HYUDJ 60W Mini Beam LED Movign Head, configurados en modo de 15 canales
    case 'c':
      tipo = 'c';
      
      dimmer.existe = true;
      strobe.existe = true;
      R.existe = true;
      G.existe = true;
      B.existe = true;
      W.existe = true;
      pan.existe = true;
      panFino.existe = true;
      tilt.existe = true;
      tiltFino.existe = true;
      //velocidadPanTilt.existe = true;

      canales = 10;
      
      dimmer.indice = 6;
      strobe.indice = 7;
      R.indice = 8;
      G.indice = 9;
      B.indice = 10;
      W.indice = 11;
      pan.indice = 1;
      panFino.indice = 2;
      tilt.indice = 3;
      tiltFino.indice = 4;
      velocidadPanTilt.indice = 5;
      
      velocidadPanTilt.valor = 0;
      
      break;

    default:

      break;
  }

  _ubicacion.x = x;
  _ubicacion.y = y;
  _ubicacion.z = z;
}

float ChuncheDMX::_aplicarCurva(float t, char curva) {
  if (t <= 0)
    return 0;
  if (t >= 1)
    return 1;

  switch (curva) {
    // Curva lineal
    case 'l':
      return t;
    // Curva cuadrática
    case 'c':
      return t * t;
    // Curva radical (raíz)
    case 'r':
      return 1 - (1-t) * (1-t);
    // Curva tipo S (smoothstep) [me la recomendó el chat :v]
    case 's':
      return t * t * (3 - 2*t);
    // Por defecto, curva lineal
    default:
      return t;
  }
}

void ChuncheDMX::asignarIntensidad(uint8_t valorByte) {
  dimmer.valorFinal = valorByte;
}

void ChuncheDMX::asignarFrecuencia(uint8_t valorByte) {
  strobe.valorFinal = valorByte;
}

void ChuncheDMX::asignarColor(const ColorEA& color) {
  uint8_t r, g, b, w;
  r = color.r;
  g = color.g;
  b = color.b;
  w = 0;
  
  // Si el chunche DMX tiene luces blancas, hay que aprovecharlas.
  if (W.existe) {
    // El valor del canal W es el mínimo de los componentes R, G y B.
    w = min({r, g, b});
    W.valorFinal = w;
    
    // Los canales R, G y B se ajustan para complementar el blanco base.
    r = r - w;
    g = g - w;
    b = b - w;
  }
  
  // Escribimos los valores para los canales R, G y B.
  R.valorFinal = r;
  G.valorFinal = g;
  B.valorFinal = b;
}

void ChuncheDMX::asignarObjetivo(const vEActor& objetivo) {
  vEActor rayo(0, 0, 0);
  
  // 1. Calculate relative 3D vector from lamp to target
  rayo.x = objetivo.x - _ubicacion.x;
  rayo.y = objetivo.y - _ubicacion.y;
  rayo.z = objetivo.z - _ubicacion.z;
  
  // Pan
  if (pan.existe) {
    // 2. Compute Target Pan (-180 to +180) and apply calibration offset
    //float panGrados = atan2f(rayo.y, rayo.x) * (180.0f / M_PI);
    float panGrados = atan2f(rayo.x, rayo.y) * (180.0f / M_PI);
    
    // Map Pan into the 540-degree space where 0 is center-stage
    // This allows tracking center stage at the middle of the fixture's mechanical travel
    float panGradosCentro = panGrados + (_panRangoGrados / 2.0f);
    
    // Wrap angle safely into the 0-540 window if it went out of bounds
    while (panGradosCentro < 0.0f) panGradosCentro += 360.0f;
    while (panGradosCentro > _panRangoGrados) panGradosCentro -= 360.0f;
    
    // 4. Safety Guard rails & Limit Checking
    panGradosCentro = constrain(panGradosCentro, 0.0f, _panRangoGrados);
    
    // 5. Convert to 16-Bit Integer (0 to 65535)
    pan16bit  = static_cast<uint16_t>((panGradosCentro / _panRangoGrados) * 65535.0f);

    // 6. Split into Coarse (MSB) and Fine (LSB) bytes for the DMX packet array
    //pan.valorFinal = static_cast<uint8_t>((pan16bit >> 8) & 0xFF);
    //panFino.valorFinal = static_cast<uint8_t>(pan16bit & 0xFF);
  }
  
  // Tilt
  if (tilt.existe) {
    // 3. Compute Target Tilt
    float distanciaHorizontal = sqrtf(rayo.x * rayo.x + rayo.y * rayo.y);
    
    // atan2f gives us angle relative to horizon. 
    // Looking straight down (-dz) means an angle of -90° relative to horizon.
    float tiltGrados = atan2f(rayo.z, distanciaHorizontal) * (180.0f / M_PI);
    
    // Shift the scale: -90° (Straight Down) becomes 90° (Mechanical Center for a 180° tilt fixture)
    float tiltGradosCentro = tiltGrados + (_tiltRangoGrados / 2.0f);
    
    // 4. Safety Guard rails & Limit Checking
    tiltGradosCentro = constrain(tiltGradosCentro, 0.0f, _tiltRangoGrados);
    //float tiltGradosCentro = constrain(tiltGrados, 0.0f, _tiltRangoGrados);
    
    // 5. Convert to 16-Bit Integer (0 to 65535)
    tilt16bit = static_cast<uint16_t>((tiltGradosCentro / _tiltRangoGrados) * 65535.0f);

    // 6. Split into Coarse (MSB) and Fine (LSB) bytes for the DMX packet array
    //tilt.valorFinal = static_cast<uint8_t>((tilt16bit >> 8) & 0xFF);
    //tiltFino.valorFinal = static_cast<uint8_t>(tilt16bit & 0xFF);
  }

  _actualizarPanTilt();
}

void ChuncheDMX::iniciarTransicion(uint32_t duracion, char curva) {
  _duracionTransicion = duracion;
  _curvaTransicion = curva;
  
  // Guardamos los valores del inicio de la transición.
  for (int i=0; i<canales; i++)
    if (canal[i]->existe)
      canal[i]->asignarValorInicial();
  _tiempoInicioTransicion = millis();

  // Aplicamos inmediatamente los valores a los canales para los que no usaremos transición.
  for (int i=0; i<canales; i++)
    if (canal[i]->existe && !canal[i]->transiciona)
      canal[i]->asignarValorFinal();

  enTransicion = true;
}

void ChuncheDMX::actualizar() {
  uint32_t _tiempoTransicion = millis() - _tiempoInicioTransicion;
  
  if (_tiempoTransicion > _duracionTransicion) {
    enTransicion = false;
    
    // Asignamos los parámetros por defecto para las transiciones.
    _duracionTransicion = 0;
    _curvaTransicion = 'l';
  }

  float _tiempoTransicionNormalizado = static_cast<float>(_tiempoTransicion) / _duracionTransicion;
  float _tiempoTransicionCurvo = _aplicarCurva(_tiempoTransicionNormalizado, _curvaTransicion); // Deformamos el tiempo según la curva seleccionada.

  // Usamos una simple interpolación lineal y = b + m*x (la deformación del tiempo de se encarga del resto).
  // No es recomendable usar transiciones suaves para canales como strobe o GOBO. Asignaremos los valores directamente, sin transición.
  // Hay que ver con cuidado si esto es necesario para pan y tilt y cómo implementarlo de modo que funcione bien. Por ahora vamos a asumir que simplemente es mejor asignar los valores directamente, sin transición.
  for (int i=0; i<canales; i++)
    if (canal[i]->existe && canal[i]->transiciona)
      canal[i]->valor = canal[i]->valorInicial + (canal[i]->valorFinal - canal[i]->valorInicial) * _tiempoTransicionCurvo;
}

void ChuncheDMX::_actualizarPanTilt() {
    // 6. Split into Coarse (MSB) and Fine (LSB) bytes for the DMX packet array
    pan.valorFinal = static_cast<uint8_t>((pan16bit >> 8) & 0xFF);
    panFino.valorFinal = static_cast<uint8_t>(pan16bit & 0xFF);

    // 6. Split into Coarse (MSB) and Fine (LSB) bytes for the DMX packet array
    tilt.valorFinal = static_cast<uint8_t>((tilt16bit >> 8) & 0xFF);
    tiltFino.valorFinal = static_cast<uint8_t>(tilt16bit & 0xFF);
}

// Camino en calma
