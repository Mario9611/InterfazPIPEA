/*
  UCR | EIE | Electrizarte
  sofia.ino - Sketch de Arduino para implementar a Sofía en la obra 'No Podemos Soles'
  Escrita por Teodoro Willink en Septiembre de 2024
  Actualizada por X en Y
  Código abierto liberado al dominio público
*/

#include "pipea.h"
#include "sofiea.h"

PIPEA nodo;
SofiEA sofia;

void setup() {
  nodo.inicio();
  nodo.prueba();

  sofia.inicio();
  sofia.prueba();

  nodo.estar_atento("sofia", reaccionar);
  sofia.apagada();
}

void loop () {
  nodo.actualizar();

  sofia.actualizar();
}

//void reaccionar_especs(char* personaje, char* accion, int* especificaciones, int especificaciones_cantidad) {
void reaccionar(char* personaje, char* accion) {
  if ( !strcmp(personaje, "sofia") ) {
    if ( !strcmp(accion, "apagada") )
      sofia.apagada();
    if ( !strcmp(accion, "encendida") )
      sofia.encendida();
    if ( !strcmp(accion, "tranquila") )
      sofia.tranquila();
    if ( !strcmp(accion, "feliz") )
      sofia.feliz();
    if ( !strcmp(accion, "triste") )
      sofia.triste();
    if ( !strcmp(accion, "sorpresa") )
      sofia.sorpresa();
    if ( !strcmp(accion, "sospecha") )
      sofia.sospecha();
    if ( !strcmp(accion, "susto") )
      sofia.susto();
    if ( !strcmp(accion, "wacala") )
      sofia.wacala();
    if ( !strcmp(accion, "ok") )
      sofia.ok();
    if ( !strcmp(accion, "no_ok") )
      sofia.no_ok();
    if ( !strcmp(accion, "al_reves") )
      sofia.al_reves();
    if ( !strcmp(accion, "izquierda") )
      sofia.izquierda();
    if ( !strcmp(accion, "derecha") )
      sofia.derecha();
    if ( !strcmp(accion, "arriba") )
      sofia.arriba();
    if ( !strcmp(accion, "abajo") )
      sofia.abajo();
    if ( !strcmp(accion, "pregunta") )
      sofia.pregunta();
    if ( !strcmp(accion, "cuidado") )
      sofia.cuidado();
    if ( !strcmp(accion, "emergencia") )
      sofia.emergencia();
    if ( !strcmp(accion, "musica") )
      sofia.musica();
  }
}

// Camino en calma
