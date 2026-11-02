/*
  UCR | EIE | Electrizarte
  sofiea.cpp - Librería para implementar a SofíEA a partir de la pantalla de botellas de Electrizarte
  Escrita por Teodoro Willink y Gustavo Núñez en Septiembre de 2024
  Actualizada por Teodoro Willink en Agosto de 2026
  [Si la actualiza, por favor incluya y ajuste una línea de "Actualizada por X en Y"]
  Código abierto liberado al dominio público
*/

#include "sofiea.h"

SofiEA::SofiEA() : pantalla(_ancho, _alto, _pin) {
  _parpadeo_cuadros = round(_parpadeo_tiempo*_cuadros_por_segundo);
  _parpadeo_cuadro = 0;
  _esperar_cuadros = round(1000.0/_cuadros_por_segundo);
  
  apagada();
  
  pinMode(LED_PIN, OUTPUT);
}

void SofiEA::inicio() {
  _borrar_dibujo();
  _dibujar();

  pantalla.inicio();
}

void SofiEA::prueba() {
  _estado = 'p';
  _cuadro = 0;

  _chispa = 0;
  _parpadear = 0;
  _calcular_cuadros();
  
  // Prueba de la pantalla establecida en BotEAllas
  pantalla.prueba();
  
  delay(1000);
  
  // Prueba de escritura en la matriz
  pantalla.matriz[2][2][0] = 255;
  pantalla.matriz[2][2][2] = 255;
  pantalla.mostrar();
  
  delay(1000);

  // Prueba de dibujo pixel por pixel
  _borrar_dibujo();
  
  _dibujar_pixel(0,0, 255,255,0);
  _dibujar_pixel(2,0, 255,255,0);
  _dibujar_pixel(4,0, 255,255,0);
  _dibujar_pixel(1,1, 0,255,255);
  _dibujar_pixel(3,1, 0,255,255);
  _dibujar_pixel(5,1, 0,255,255);
  
  _dibujar();
  pantalla.mostrar();
  
  delay(1000);
}

void SofiEA::apagada() {
  _estado = 'a';
  _cuadro = 0;

  _chispa = 0;
  _parpadear = 0;
  _calcular_cuadros();

  _borrar_dibujo();
}

void SofiEA::encendida() {
  _estado = 'e';
  _cuadro = 0;

  _chispa = 0;
  _parpadear = 0;
  _calcular_cuadros();

  _borrar_dibujo();

  for (int x=0; x<_ancho; x++)
    for (int y=0; y<_alto; y++)
      _dibujar_pixel(x,y, 255,255,255);
}

void SofiEA::tranquila() {
  _estado = 'q';
  _cuadro = 0;

  _chispa = 2;
  _parpadear = 2;
  _calcular_cuadros();

  _borrar_dibujo();

  // Ojos
  _dibujar_pixel(1,2, 255,0,255);
  _dibujar_pixel(1,3, 255,0,255);
  _dibujar_pixel(4,2, 255,0,255);
  _dibujar_pixel(4,3, 255,0,255);

  // Boca
  _dibujar_pixel(0,5, 255,0,255);
  _dibujar_pixel(1,6, 255,0,255);
  _dibujar_pixel(2,6, 255,0,255);
  _dibujar_pixel(3,6, 255,0,255);
  _dibujar_pixel(4,6, 255,0,255);
  _dibujar_pixel(5,5, 255,0,255);
}

void SofiEA::feliz() {
  _estado = 'f';
  _cuadro = 0;

  _chispa = 3;
  _parpadear = 2;
  _calcular_cuadros();

  _borrar_dibujo();

  // Ojos
  _dibujar_pixel(1,2, 255,255,0);
  _dibujar_pixel(1,3, 255,255,0);
  _dibujar_pixel(4,2, 255,255,0);
  _dibujar_pixel(4,3, 255,255,0);

  // Boca
  _dibujar_pixel(0,5, 255,255,0);
  _dibujar_pixel(1,5, 255,255,0);
  _dibujar_pixel(2,5, 255,255,0);
  _dibujar_pixel(3,5, 255,255,0);
  _dibujar_pixel(4,5, 255,255,0);
  _dibujar_pixel(5,5, 255,255,0);
  _dibujar_pixel(0,6, 255,255,0);
  _dibujar_pixel(5,6, 255,255,0);
  _dibujar_pixel(1,7, 255,255,0);
  _dibujar_pixel(2,7, 255,255,0);
  _dibujar_pixel(3,7, 255,255,0);
  _dibujar_pixel(4,7, 255,255,0);
}

void SofiEA::triste() {
  _estado = 't';
  _cuadro = 0;

  _chispa = 1;
  _parpadear = 2;
  _calcular_cuadros();

  _borrar_dibujo();

  // Ojos
  _dibujar_pixel(1,2, 0,255,255);
  _dibujar_pixel(1,3, 0,255,255);
  _dibujar_pixel(4,2, 0,255,255);
  _dibujar_pixel(4,3, 0,255,255);

  // Boca
  _dibujar_pixel(0,6, 0,255,255);
  _dibujar_pixel(1,5, 0,255,255);
  _dibujar_pixel(2,5, 0,255,255);
  _dibujar_pixel(3,5, 0,255,255);
  _dibujar_pixel(4,5, 0,255,255);
  _dibujar_pixel(5,6, 0,255,255);
}

void SofiEA::sorpresa() {
  _estado = 'o';
  _cuadro = 0;

  _chispa = 2;
  _parpadear = 2;
  _calcular_cuadros();

  _borrar_dibujo();

  // Cejas
  _dibujar_pixel(0,1, 255,0,255);
  _dibujar_pixel(1,0, 255,0,255);
  _dibujar_pixel(5,1, 255,0,255);
  _dibujar_pixel(4,0, 255,0,255);

  // Ojos
  _dibujar_pixel(1,2, 255,0,255);
  _dibujar_pixel(4,2, 255,0,255);

  // Boca
  _dibujar_pixel(2,4, 255,0,255);
  _dibujar_pixel(3,4, 255,0,255);
  _dibujar_pixel(1,5, 255,0,255);
  _dibujar_pixel(4,5, 255,0,255);
  _dibujar_pixel(1,6, 255,0,255);
  _dibujar_pixel(4,6, 255,0,255);
  _dibujar_pixel(2,7, 255,0,255);
  _dibujar_pixel(3,7, 255,0,255);
}

void SofiEA::sospecha() {
  _estado = 's';
  _cuadro = 0;

  _chispa = 2;
  _parpadear = 2;
  _calcular_cuadros();

  _borrar_dibujo();
  
  // Ojos
  _dibujar_pixel(1,3, 255,0,255);
  _dibujar_pixel(2,3, 255,0,255);
  _dibujar_pixel(4,3, 255,0,255);
  _dibujar_pixel(5,3, 255,0,255);

  // Boca
  _dibujar_pixel(1,5, 255,0,255);
  _dibujar_pixel(2,5, 255,0,255);
  _dibujar_pixel(3,5, 255,0,255);
  _dibujar_pixel(4,5, 255,0,255);
  _dibujar_pixel(5,5, 255,0,255);
}

void SofiEA::susto() {
  _estado = 'u';
  _cuadro = 0;

  _chispa = 1;
  _parpadear = 1;
  _calcular_cuadros();

  _borrar_dibujo();
  
  // Cejas
  _dibujar_pixel(0,1, 0,255,255);
  _dibujar_pixel(1,0, 0,255,255);
  _dibujar_pixel(5,1, 0,255,255);
  _dibujar_pixel(4,0, 0,255,255);

  // Ojos
  _dibujar_pixel(1,2, 0,255,255);
  _dibujar_pixel(4,2, 0,255,255);

  // Boca
  _dibujar_pixel(1,4, 0,255,255);
  _dibujar_pixel(2,4, 0,255,255);
  _dibujar_pixel(3,4, 0,255,255);
  _dibujar_pixel(4,4, 0,255,255);
  _dibujar_pixel(0,5, 0,255,255);
  _dibujar_pixel(5,5, 0,255,255);
  _dibujar_pixel(0,6, 0,255,255);
  _dibujar_pixel(1,6, 0,255,255);
  _dibujar_pixel(2,6, 0,255,255);
  _dibujar_pixel(3,6, 0,255,255);
  _dibujar_pixel(4,6, 0,255,255);
  _dibujar_pixel(5,6, 0,255,255);
}

void SofiEA::wacala() {
  _estado = 'w';
  _cuadro = 0;

  _chispa = 2;
  _parpadear = 1;
  _calcular_cuadros();

  _borrar_dibujo();

  // Ojos
  _dibujar_pixel(1,2, 0,255,0);
  _dibujar_pixel(2,2, 0,255,0);
  _dibujar_pixel(4,2, 0,255,0);
  _dibujar_pixel(5,2, 0,255,0);
  _dibujar_pixel(2,3, 0,255,0);
  _dibujar_pixel(5,3, 0,255,0);

  // Boca
  _dibujar_pixel(2,6, 0,255,0);
  _dibujar_pixel(3,5, 0,255,0);
  _dibujar_pixel(4,5, 0,255,0);
  _dibujar_pixel(5,5, 0,255,0);
}

void SofiEA::ok() {
  _estado = 'y';
  _cuadro = 0;

  _chispa = 2;
  _parpadear = 0;
  _calcular_cuadros();

  _borrar_dibujo();
  
  _dibujar_pixel(0,4, 0,255,0);
  _dibujar_pixel(1,5, 0,255,0);
  _dibujar_pixel(2,4, 0,255,0);
  _dibujar_pixel(3,3, 0,255,0);
  _dibujar_pixel(4,2, 0,255,0);
  _dibujar_pixel(5,1, 0,255,0);
}

void SofiEA::no_ok() {
  _estado = 'n';
  _cuadro = 0;

  _chispa = 2;
  _parpadear = 0;
  _calcular_cuadros();

  _borrar_dibujo();
  
  _dibujar_pixel(0,1, 255,0,0);
  _dibujar_pixel(5,1, 255,0,0);
  _dibujar_pixel(1,2, 255,0,0);
  _dibujar_pixel(4,2, 255,0,0);
  _dibujar_pixel(2,3, 255,0,0);
  _dibujar_pixel(3,3, 255,0,0);
  _dibujar_pixel(2,4, 255,0,0);
  _dibujar_pixel(3,4, 255,0,0);
  _dibujar_pixel(1,5, 255,0,0);
  _dibujar_pixel(4,5, 255,0,0);
  _dibujar_pixel(0,6, 255,0,0);
  _dibujar_pixel(5,6, 255,0,0);
}

void SofiEA::al_reves() {
  _estado = 'r';
  _cuadro = 0;

  _chispa = 2;
  _parpadear = 2;
  _calcular_cuadros();

  _borrar_dibujo();

  // Ojos
  _dibujar_pixel(1,5, 255,0,255);
  _dibujar_pixel(1,6, 255,0,255);
  _dibujar_pixel(4,5, 255,0,255);
  _dibujar_pixel(4,6, 255,0,255);

  // Boca
  _dibujar_pixel(0,3, 255,0,255);
  _dibujar_pixel(1,2, 255,0,255);
  _dibujar_pixel(2,2, 255,0,255);
  _dibujar_pixel(3,2, 255,0,255);
  _dibujar_pixel(4,2, 255,0,255);
  _dibujar_pixel(5,3, 255,0,255);
}

void SofiEA::izquierda() {
  _estado = 'j';
  _cuadro = 0;

  _chispa = 2;
  _parpadear = 0;
  _calcular_cuadros();

  _borrar_dibujo();
  
  _dibujar_pixel(2,1, 255,0,255);
  _dibujar_pixel(2,2, 255,0,255);
  _dibujar_pixel(1,2, 255,0,255);
  _dibujar_pixel(0,3, 255,0,255);
  _dibujar_pixel(1,3, 255,0,255);
  _dibujar_pixel(2,3, 255,0,255);
  _dibujar_pixel(3,3, 255,0,255);
  _dibujar_pixel(4,3, 255,0,255);
  _dibujar_pixel(5,3, 255,0,255);
  _dibujar_pixel(0,4, 255,0,255);
  _dibujar_pixel(1,4, 255,0,255);
  _dibujar_pixel(2,4, 255,0,255);
  _dibujar_pixel(3,4, 255,0,255);
  _dibujar_pixel(4,4, 255,0,255);
  _dibujar_pixel(5,4, 255,0,255);
  _dibujar_pixel(2,5, 255,0,255);
  _dibujar_pixel(1,5, 255,0,255);
  _dibujar_pixel(2,6, 255,0,255);
}

void SofiEA::derecha() {
  _estado = 'l';
  _cuadro = 0;

  _chispa = 2;
  _parpadear = 0;
  _calcular_cuadros();

  _borrar_dibujo();
  
  _dibujar_pixel(3,1, 255,0,255);
  _dibujar_pixel(3,2, 255,0,255);
  _dibujar_pixel(4,2, 255,0,255);
  _dibujar_pixel(0,3, 255,0,255);
  _dibujar_pixel(1,3, 255,0,255);
  _dibujar_pixel(2,3, 255,0,255);
  _dibujar_pixel(3,3, 255,0,255);
  _dibujar_pixel(4,3, 255,0,255);
  _dibujar_pixel(5,3, 255,0,255);
  _dibujar_pixel(0,4, 255,0,255);
  _dibujar_pixel(1,4, 255,0,255);
  _dibujar_pixel(2,4, 255,0,255);
  _dibujar_pixel(3,4, 255,0,255);
  _dibujar_pixel(4,4, 255,0,255);
  _dibujar_pixel(5,4, 255,0,255);
  _dibujar_pixel(3,5, 255,0,255);
  _dibujar_pixel(4,5, 255,0,255);
  _dibujar_pixel(3,6, 255,0,255);
}

void SofiEA::arriba() {
  _estado = 'i';
  _cuadro = 0;

  _chispa = 2;
  _parpadear = 0;
  _calcular_cuadros();

  _borrar_dibujo();
  
  _dibujar_pixel(2,1, 255,0,255);
  _dibujar_pixel(3,1, 255,0,255);
  _dibujar_pixel(1,2, 255,0,255);
  _dibujar_pixel(2,2, 255,0,255);
  _dibujar_pixel(3,2, 255,0,255);
  _dibujar_pixel(4,2, 255,0,255);
  _dibujar_pixel(0,3, 255,0,255);
  _dibujar_pixel(1,3, 255,0,255);
  _dibujar_pixel(2,3, 255,0,255);
  _dibujar_pixel(3,3, 255,0,255);
  _dibujar_pixel(4,3, 255,0,255);
  _dibujar_pixel(5,3, 255,0,255);
  _dibujar_pixel(2,4, 255,0,255);
  _dibujar_pixel(3,4, 255,0,255);
  _dibujar_pixel(2,5, 255,0,255);
  _dibujar_pixel(3,5, 255,0,255);
  _dibujar_pixel(2,6, 255,0,255);
  _dibujar_pixel(3,6, 255,0,255);
}

void SofiEA::abajo() {
  _estado = 'k';
  _cuadro = 0;

  _chispa = 2;
  _parpadear = 0;
  _calcular_cuadros();

  _borrar_dibujo();
  
  _dibujar_pixel(2,1, 255,0,255);
  _dibujar_pixel(3,1, 255,0,255);
  _dibujar_pixel(2,2, 255,0,255);
  _dibujar_pixel(3,2, 255,0,255);
  _dibujar_pixel(2,3, 255,0,255);
  _dibujar_pixel(3,3, 255,0,255);
  _dibujar_pixel(0,4, 255,0,255);
  _dibujar_pixel(1,4, 255,0,255);
  _dibujar_pixel(2,4, 255,0,255);
  _dibujar_pixel(3,4, 255,0,255);
  _dibujar_pixel(4,4, 255,0,255);
  _dibujar_pixel(5,4, 255,0,255);
  _dibujar_pixel(1,5, 255,0,255);
  _dibujar_pixel(2,5, 255,0,255);
  _dibujar_pixel(3,5, 255,0,255);
  _dibujar_pixel(4,5, 255,0,255);
  _dibujar_pixel(2,6, 255,0,255);
  _dibujar_pixel(3,6, 255,0,255);
}

void SofiEA::pregunta() {
  _estado = 'p';
  _cuadro = 0;

  _chispa = 2;
  _parpadear = 0;
  _calcular_cuadros();

  _borrar_dibujo();

  _dibujar_pixel(2,0, 255,255,0);
  _dibujar_pixel(3,0, 255,255,0);
  _dibujar_pixel(1,1, 255,255,0);
  _dibujar_pixel(4,1, 255,255,0);
  _dibujar_pixel(4,2, 255,255,0);
  _dibujar_pixel(3,3, 255,255,0);
  _dibujar_pixel(2,4, 255,255,0);
  _dibujar_pixel(2,5, 255,255,0);
  _dibujar_pixel(2,7, 255,255,0);
}

void SofiEA::cuidado() {
  _estado = 'c';
  _cuadro = 0;

  _chispa = 2;
  _parpadear = 0;
  _calcular_cuadros();

  _borrar_dibujo();

  _dibujar_pixel(2,0, 255,255,0);
  _dibujar_pixel(3,0, 255,255,0);
  _dibujar_pixel(2,1, 255,255,0);
  _dibujar_pixel(3,1, 255,255,0);
  _dibujar_pixel(2,2, 255,255,0);
  _dibujar_pixel(3,2, 255,255,0);
  _dibujar_pixel(2,3, 255,255,0);
  _dibujar_pixel(3,3, 255,255,0);
  _dibujar_pixel(2,4, 255,255,0);
  _dibujar_pixel(3,4, 255,255,0);
  _dibujar_pixel(2,6, 255,255,0);
  _dibujar_pixel(3,6, 255,255,0);
  _dibujar_pixel(2,7, 255,255,0);
  _dibujar_pixel(3,7, 255,255,0);
}

void SofiEA::emergencia() {
  _estado = 'g';
  _cuadro = 0;

  _chispa = 2;
  _parpadear = 0;
  _calcular_cuadros();

  _borrar_dibujo();

  _dibujar_pixel(2,0, 255,0,0);
  _dibujar_pixel(3,0, 255,0,0);
  _dibujar_pixel(2,1, 255,0,0);
  _dibujar_pixel(3,1, 255,0,0);
  _dibujar_pixel(2,2, 255,0,0);
  _dibujar_pixel(3,2, 255,0,0);
  _dibujar_pixel(2,3, 255,0,0);
  _dibujar_pixel(3,3, 255,0,0);
  _dibujar_pixel(2,4, 255,0,0);
  _dibujar_pixel(3,4, 255,0,0);
  _dibujar_pixel(2,6, 255,0,0);
  _dibujar_pixel(3,6, 255,0,0);
  _dibujar_pixel(2,7, 255,0,0);
  _dibujar_pixel(3,7, 255,0,0);
}

void SofiEA::musica() {
  _estado = 'm';
  _cuadro = 0;

  _chispa = 2;
  _parpadear = 0;
  _calcular_cuadros();

  _borrar_dibujo();

  _dibujar_pixel(2,0, 255,255,0);
  _dibujar_pixel(2,1, 255,255,0);
  _dibujar_pixel(3,1, 255,255,0);
  _dibujar_pixel(2,2, 255,255,0);
  _dibujar_pixel(4,2, 255,255,0);
  _dibujar_pixel(2,3, 255,255,0);
  _dibujar_pixel(5,2, 255,255,0);
  _dibujar_pixel(2,4, 255,255,0);
  _dibujar_pixel(0,5, 255,255,0);
  _dibujar_pixel(1,5, 255,255,0);
  _dibujar_pixel(2,5, 255,255,0);
  _dibujar_pixel(0,6, 255,255,0);
  _dibujar_pixel(1,6, 255,255,0);
  _dibujar_pixel(2,6, 255,255,0);
  _dibujar_pixel(1,7, 255,255,0);
  _dibujar_pixel(2,7, 255,255,0);
}

void SofiEA::actualizar() {
  _cuadro++;

  _dibujar();

  // Efectos
  
  // Chispa
  if (_chispa) {
    if ( _cuadro % _chispa_cuadros == 0 )
      for (int x=0; x<2*_chispa; x++)
        for (int y=0; y<2*_chispa; y++) {
          _chispa_amarillo = random(_chispa*15,255);
          _chispa_azul = random(15);
          _dibujar_pixel(_ancho/2-_chispa+x,3*_alto/4-_chispa+y, _chispa_amarillo,_chispa_amarillo,_chispa_azul);
      }
      /*_dibujar_pixel(_ancho/2-_chispa, 3*_alto/4-_chispa, 0,0,0);
      _dibujar_pixel(_ancho/2-_chispa, 3*_alto/4+1+_chispa, 0,0,0);
      _dibujar_pixel(_ancho/2+1+_chispa, 3*_alto/4-_chispa, 0,0,0);
      _dibujar_pixel(_ancho/2+1+_chispa, 3*_alto/4+1+_chispa, 0,0,0);*/
  }

  // Parpadear
  if (_parpadear) {
    if ( random(_parpadear_cuadros) == 0 ) {
      //_parpadeo_cuadro = _cuadro + random(_parpadeo_cuadros,2*_parpadeo_cuadros);
      _parpadeo_cuadro = _cuadro + _parpadeo_cuadros;

      // Cerrar los ojos
      for (int x=0; x<_ancho; x++)
        for (int y=_ojos_ymin; y<=_ojos_ymax; y++)
          for (int c=0; c<3; c++)
            pantalla.matriz[x][y][c] = 0;
    }

    if ( _cuadro == _parpadeo_cuadro ) {
      // Abrir los ojos
      for (int x=0; x<_ancho; x++)
        for (int y=_ojos_ymin; y<_ojos_ymax; y++)
          for (int c=0; c<3; c++)
            pantalla.matriz[x][y][c] = dibujo[x][y][c];
    }
  }

  pantalla.mostrar();
  
  delay(_esperar_cuadros);
}

void SofiEA::_dibujar() {
  for (int x=0; x<_ancho; x++)
    for (int y=0; y<_alto; y++)
      for (int c=0; c<3; c++)
        pantalla.matriz[x][y][c] = dibujo[x][y][c];
}

void SofiEA::_borrar_dibujo() {
  for (int x=0; x<_ancho; x++)
    for (int y=0; y<_alto; y++)
      for (int c=0; c<3; c++)
        dibujo[x][y][c] = 0;
}

void SofiEA::_dibujar_pixel(int x, int y, int r, int g, int b) {
  dibujo[x][y][0] = r;
  dibujo[x][y][1] = g;
  dibujo[x][y][2] = b;
}

void SofiEA::_calcular_cuadros() {
  _chispa_cuadros = round((_chispa_max-_chispa+1)*(_chispa_tiempo)*_cuadros_por_segundo);
  _parpadear_cuadros = round(_parpadear*_cuadros_por_segundo);
}

/*

Para dibujar:

   0 1 2 3 4 5
0  . . . . . .
1  . . . . . .
2  . 0 . . 0 .
3  ._0_._._0_.
4  . . . . . .
5  0 0 0 0 0 0
6  0 . . . . 0
7  ._0_0_0_0_.
8  . . . . . .
9  . . . . . .
10 . . . . . .
11 ._._._._._.
12 . . . . . .
13 . . . . . .
14 . . . . . .
15 ._._._._._.

*/

// Camino en calma
