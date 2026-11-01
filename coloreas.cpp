/*
  UCR | EIE | Electrizarte
  colorEAs.cpp - Librería para definir colores
  Escrita por Teodoro Willink y Gustavo Núñez en Agosto de 2026
  [Si la actualiza, por favor incluya y ajuste una línea de "Actualizada por X en Y"]
  Código abierto liberado al dominio público
*/

#include "coloreas.h"

ColorEA::ColorEA() {

}

ColorEA::ColorEA(uint8_t rojo, uint8_t verde, uint8_t azul) {
  r = rojo;
  g = verde;
  b = azul;
  
  h = 0;
  s = 0;
  v = 0;

  hsv();
}

void ColorEA::hsv() { // Esta función la hizo el chat, espero que funcione.
  // 1. Scale RGB values to the range [0, 1]
  float r_norm = r / 255.0;
  float g_norm = g / 255.0;
  float b_norm = b / 255.0;

  // 2. Find the minimum and maximum values among R, G, B
  float min_val = min({r_norm, g_norm, b_norm});
  float max_val = max({r_norm, g_norm, b_norm});
  float delta = max_val - min_val;

  // 3. Calculate Value (V)
  v = static_cast<int>(max_val * 100.0 + 0.5); // Round to nearest integer

  // 4. Calculate Saturation (S)
  if (max_val == 0.0) {
    s = 0;
  } else {
    s = static_cast<int>((delta / max_val) * 100.0 + 0.5);
  }

  // 5. Calculate Hue (H)
  if (delta == 0.0) {
    h = 0; // Achromatic case (gray, white, or black)
  } else {
    float h_deg = 0.0;

    if (max_val == r_norm) {
      h_deg = 60.0 * ((g_norm - b_norm) / delta);
    } else if (max_val == g_norm) {
      h_deg = 60.0 * ((b_norm - r_norm) / delta) + 120.0;
    } else if (max_val == b_norm) {
      h_deg = 60.0 * ((r_norm - g_norm) / delta) + 240.0;
    }

    // Ensure hue is positive
    if (h_deg < 0.0)
      h_deg += 360.0;

    h = static_cast<int>(h_deg + 0.5); // Round to nearest integer
  }
}

void ColorEA::rgb() { // Esta función la hizo el chat, espero que funcione.
  float s_norm = s / 100.0;
  float v_norm = v / 100.0;
  float c = v_norm * s_norm;
  float x = c * (1.0 - abs(fmod(h / 60.0, 2) - 1.0));
  float m = v_norm - c;

  float r_norm = 0, g_norm = 0, b_norm = 0;

  if (h >= 0 && h < 60)       { r_norm = c; g_norm = x; b_norm = 0; }
  else if (h >= 60 && h < 120)  { r_norm = x; g_norm = c; b_norm = 0; }
  else if (h >= 120 && h < 180) { r_norm = 0; g_norm = c; b_norm = x; }
  else if (h >= 180 && h < 240) { r_norm = 0; g_norm = x; b_norm = c; }
  else if (h >= 240 && h < 300) { r_norm = x; g_norm = 0; b_norm = c; }
  else if (h >= 300 && h <= 360){ r_norm = c; g_norm = 0; b_norm = x; }

  r = static_cast<uint8_t>((r_norm + m) * 255);
  g = static_cast<uint8_t>((g_norm + m) * 255);
  b = static_cast<uint8_t>((b_norm + m) * 255);
}

// Camino en calma
