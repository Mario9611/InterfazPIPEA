/*
  UCR | EIE | Electrizarte
  eambientes.cpp - Librería para definir ambientes
  Escrita por Teodoro Willink y Gustavo Núñez en Agosto de 2026
  [Si la actualiza, por favor incluya y ajuste una línea de "Actualizada por X en Y"]
  Código abierto liberado al dominio público
*/

#include "eambientes.h"

EAscena::EAscena() {

}

SecuEAncia::SecuEAncia() {

}

int SecuEAncia::asignarEscena(int indice) {
  _actual = indice;
  
  if (aleatoria)
    _actual = random(escenas);

  _tiempoInicioEscena = millis();
  
  return _actual;
}

bool SecuEAncia::escenaLista() {
  uint32_t tiempoTranscurrido = millis() - _tiempoInicioEscena;
  uint32_t duracionTotal = static_cast<uint32_t>(1000.0 * *escena[_actual].duracionTransicion) + static_cast<uint32_t>(1000.0 * duracionEscena[_actual]);
  //uint32_t duracionTotal = static_cast<uint32_t>(1000.0 * duracionEscena[_actual]);

  if (tiempoTranscurrido >= duracionTotal)
    return true;
  else
    return false;
}

bool SecuEAncia::ultimaEscena() {
  if (!repite && !aleatoria && _actual >= (escenas-1))
    return true;
  else
    return false;
}

int SecuEAncia::siguienteEscena() {
  _actual++;
  
  if (_actual >= escenas && repite)
    _actual = 0;

  return _actual;
}

EAfecto::EAfecto() {

}


void definirEscenas() {
  oscura.intensidadPARes = 0;
  oscura.intensidadCabezas = 1;
  oscura.colorBase = azulEA;
  oscura.tipoPaleta = '1';
  oscura.variacion = 0;
  oscura.duracionTransicion = 2;
  oscura.curvaTransicion = 'l';

  coloresFrios.intensidad = 1;
  coloresFrios.colorBase = azulEA;
  coloresFrios.tipoPaleta = 'a';
  coloresFrios.variacion = 0.5;
  coloresFrios.objetivosCabezas = true;
  coloresFrios.duracionTransicion = 2;
  coloresFrios.curvaTransicion = 'l';

  coloresCalidos.intensidad = 1;
  coloresCalidos.colorBase = amarilloEA;
  coloresCalidos.tipoPaleta = 'a';
  coloresCalidos.variacion = 0.5;
  coloresCalidos.objetivosCabezas = true;
  coloresCalidos.duracionTransicion = 1;
  coloresCalidos.curvaTransicion = 'l';
  
  coloresVivos.intensidad = 1;
  coloresVivos.colorBase = rojo;
  coloresVivos.tipoPaleta = 'a';
  coloresVivos.variacion = 0.7;
  coloresVivos.objetivosCabezas = true;
  coloresVivos.duracionTransicion = 0.5;
  coloresVivos.curvaTransicion = 'l';
}


void definirSecuencias() {
  introOscura.repite = true;
  introOscura.escena[0] = oscura;
  introOscura.duracionEscena[0] = 2;
  introOscura.escena[1] = coloresFrios;
  introOscura.duracionEscena[1] = 2;
  introOscura.escenas = 2;

  frioSuave.repite = true;
  frioSuave.escena[0] = coloresFrios;
  frioSuave.duracionEscena[0] = 2;
  frioSuave.escenas = 1;

  frioFuerte.repite = true;
  frioFuerte.escena[0] = coloresFrios;
  frioFuerte.escena[0].duracionTransicion = 0;
  frioFuerte.duracionEscena[0] = 1;
  frioFuerte.escenas = 1;

  calidoSuave.repite = true;
  calidoSuave.escena[0] = coloresCalidos;
  calidoSuave.duracionEscena[0] = 2;
  calidoSuave.escenas = 1;

  calidoFuerte.repite = true;
  calidoFuerte.escena[0] = coloresCalidos;
  calidoFuerte.escena[0].duracionTransicion = 0;
  calidoFuerte.duracionEscena[0] = 1;
  calidoFuerte.escenas = 1;

  cumbiaSuave.repite = true;
  cumbiaSuave.escena[0] = coloresVivos;
  cumbiaSuave.duracionEscena[0] = 1;
  cumbiaSuave.escenas = 1;

  cumbiaFuerte.repite = true;
  cumbiaFuerte.escena[0] = coloresVivos;
  cumbiaFuerte.escena[0].duracionTransicion = 0.5;
  cumbiaFuerte.escena[1] = coloresVivos;
  cumbiaFuerte.escena[1].duracionTransicion = 0.5;
  cumbiaFuerte.escena[2] = coloresVivos;
  cumbiaFuerte.escena[2].duracionTransicion = 0.5;
  cumbiaFuerte.duracionEscena[0] = 0.5;
  cumbiaFuerte.escenas = 3;
}

// Camino en calma
