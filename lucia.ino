/*
  UCR | EIE | Electrizarte
  lucia.ino - Sketch de Arduino para implementar el sistema para controlar luces DMX llamado Lucía con PIPEA
  Escrita por Teodoro Willink y Gustavo Núñez en Agosto de 2026
  [Si la actualiza, por favor incluya y ajuste una línea de "Actualizada por X en Y"]
  Código abierto liberado al dominio público
*/

#include "pipea.h"

nodoPIPEA nodo;
LuciEA segura;

EAscena escenaAnterior;

void setup() {
  nodo.inicio();
  segura.inicio();

  nodo.atento("banda", reaccion);
}

void loop () {
  nodo.actualizar();

  segura.actualizar();
}

//void reaccionar_especs(char* personaje, char* accion, int* especificaciones, int especificaciones_cantidad) {
void reaccion(char* personaje, char* accion) {
  if ( !strcmp(personaje, "banda") ) {
    if ( !strcmp(accion, "soloGuitarra") ) {
      if (!segura.solo) {
        //segura.posicion(guitarra);
        segura.postura(32767+8440, 7980);
        segura.color(blanco, 'c');
        segura.solo = true;
      } else {
        segura.escena(coloresCalidos);
        segura.solo = false;
      }
    }
    if ( !strcmp(accion, "soloBajo") ) {
      if (!segura.solo) {
        //segura.posicion(bajo);
        segura.postura(32767+9550, 4640);
        segura.color(naranjaEA, 'c');
        segura.solo = true;
      } else {
        segura.escena(coloresCalidos);
        segura.solo = false;
      }
    }
    if ( !strcmp(accion, "soloBateria") ) {
      if (!segura.solo) {
        //segura.posicion(bateria);
        segura.postura(32767+5220, 5720);
        segura.color(rosaEA, 'c');
        segura.solo = true;
      } else {
        segura.escena(coloresCalidos);
        segura.solo = false;
      }
    }
    if ( !strcmp(accion, "intro") ) {
      segura.secuencia(introOscura);
      segura.circulos = 10000;
    }
    if ( !strcmp(accion, "furiaIntro") ) {
      //segura.colores(azulEA, 'm', 0.5);
      segura.escena(coloresFrios);
      //segura.secuencia(frioSuave);
    }
    if ( !strcmp(accion, "furiaVerso") ) {
      //segura.colores(azulEA, 'm', 0.5);
      segura.secuencia(frioSuave);
    }
    if ( !strcmp(accion, "furiaCoro") ) {
      //segura.colores(moradoEA, 'a', 0.5);
      segura.secuencia(frioFuerte);
    }
    if ( !strcmp(accion, "oyeIntro") ) {
      //segura.colores(amarilloEA, 'a', 0.1);
      segura.escena(coloresCalidos);
      //segura.secuencia(frioFuerte);
    }
    if ( !strcmp(accion, "oyeVerso") ) {
      //segura.colores(naranjaEA, 'm', 0.5);
      segura.secuencia(calidoFuerte);
    }
    if ( !strcmp(accion, "oyeCoro") ) {
      //segura.colores(rojoEA, 'a', 0.1);
      segura.secuencia(calidoFuerte);
      segura.circulos = 15000;
    }
    if ( !strcmp(accion, "cumbiaVerso") ) {
      //segura.colores(amarilloEA, 'a', 0.5);
      segura.secuencia(cumbiaSuave);
    }
    if ( !strcmp(accion, "cumbiaCoro") ) {
      //segura.colores(naranjaEA, 'a', 0.5);
      segura.secuencia(cumbiaFuerte);
      segura.circulos = 20000;
    }





    if ( !strcmp(accion, "colores") ) {
      segura.intensidad(1);
      segura.colores(naranjaEA, 'a', 0.5);
    }
    if ( !strcmp(accion, "color") ) {
      segura.intensidad(1);
      segura.color(naranjaEA);
    }
    if ( !strcmp(accion, "cero") ) {
      segura.color(verdeEA);
      segura.posicion(cero);
    }
    if ( !strcmp(accion, "derecha") ) {
      segura.color(verdeEA);
      segura.posicion(derechaUno);
    }
    if ( !strcmp(accion, "izquierda") ) {
      segura.color(verdeEA);
      segura.posicion(izquierdaUno);
    }
    if ( !strcmp(accion, "solo") ) {
      segura.color(verdeEA);
      segura.solo = true;
    }
    if ( !strcmp(accion, "circulos") ) {
      segura.color(rosaEA);
      segura.circulos = 10000;
    }
    if ( !strcmp(accion, "secuencia") ) {
      segura.secuencia(introOscura);
    }
  }
}

// Camino en calma
