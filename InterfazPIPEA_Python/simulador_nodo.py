# ==============================================================================
# PIPEA - Simulador Ampliado de Nodos ESP32 para Pruebas de Interfaz
# ==============================================================================
# Publica periódicamente el registro de varios nodos en "pipea/registro/parametros"
# usando el broker público HiveMQ (broker.hivemq.com).
# ==============================================================================

import paho.mqtt.client as mqtt
import json
import time

# Cliente MQTT (API v2) conectado al broker de pruebas
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.connect("broker.hivemq.com", 1883, 60)

# ------------------------------------------------------------------------------
# NODO 1: Luces Escenario 1 (Reacciona - personajes: banda, ambienteEA)
# ------------------------------------------------------------------------------
nodo_luces_1 = {
    "node_id": "lucia_01",
    "nombre": "Luces Escenario 1",
    "tipo": "reacciona",
    "personajes": ["banda", "ambienteEA"],
    "parametros_disponibles": [
        {"id": "intensidad", "nombre": "Intensidad", "tipo": "int", "min": 0, "max": 255},
        {"id": "duracion_seg", "nombre": "Duración (s)", "tipo": "int", "min": 0, "max": 30},
        {"id": "posicion", "nombre": "Posición", "tipo": "lista", "opciones": ["cero", "derechaUno", "izquierdaUno", "guitarra", "bajo"]},
        {"id": "paleta", "nombre": "Paleta", "tipo": "lista", "opciones": ["coloresCalidos", "coloresFrios", "oscura", "coloresVivos"]},
        {"id": "curva", "nombre": "Curva", "tipo": "lista", "opciones": ["l", "e", "s"]}
    ],
    "acciones_actuales": [
        {
            "personaje": "banda",
            "accion": "soloGuitarra",
            "parametros": {
                "intensidad": 255,
                "duracion_seg": 5,
                "posicion": "guitarra",
                "paleta": "coloresFrios",
                "curva": "l"
            }
        },
        {
            "personaje": "ambienteEA",
            "accion": "Amanece",
            "parametros": {
                "intensidad": 180,
                "duracion_seg": 10,
                "posicion": "cero",
                "paleta": "coloresCalidos",
                "curva": "s"
            }
        }
    ]
}

# ------------------------------------------------------------------------------
# NODO 2: Luces Efectos / Humo (Reacciona - compartido por ambiente y banda)
# ------------------------------------------------------------------------------
nodo_luces_2 = {
    "node_id": "lucia_02",
    "nombre": "Luces y Efectos Lateral",
    "tipo": "reacciona",
    "personajes": ["ambiente", "banda"],
    "parametros_disponibles": [
        {"id": "intensidad", "nombre": "Intensidad", "tipo": "int", "min": 0, "max": 255},
        {"id": "rafaga_ms", "nombre": "Ráfaga (ms)", "tipo": "int", "min": 100, "max": 5000},
        {"id": "color_base", "nombre": "Color Base", "tipo": "lista", "opciones": ["ambar", "azulProfundo", "magenta", "blancoFrio", "apagado"]}
    ],
    "acciones_actuales": [
        {
            "personaje": "ambiente",
            "accion": "brumaEscena",
            "parametros": {"intensidad": 140, "rafaga_ms": 1200, "color_base": "azulProfundo"}
        }
    ]
}

# ------------------------------------------------------------------------------
# NODO 3: Pantalla SofíEA (Reacciona - personaje: sofia)
# ------------------------------------------------------------------------------
nodo_sofia = {
    "node_id": "sofia_01",
    "nombre": "Pantalla SofíEA",
    "tipo": "reacciona",
    "personajes": ["sofia"],
    "parametros_disponibles": [
        {"id": "chispa", "nombre": "Chispa", "tipo": "int", "min": 0, "max": 3},
        {"id": "parpadeo_s", "nombre": "Parpadeo (s)", "tipo": "int", "min": 0, "max": 10},
        {"id": "expresion", "nombre": "Expresión", "tipo": "lista", "opciones": ["tranquila", "feliz", "triste", "sorpresa", "sospecha", "susto", "emergencia", "musica"]}
    ],
    "acciones_actuales": [
        {
            "personaje": "sofia",
            "accion": "saludo",
            "parametros": {"chispa": 3, "parpadeo_s": 2, "expresion": "feliz"}
        },
        {
            "personaje": "sofia",
            "accion": "alerta",
            "parametros": {"chispa": 1, "parpadeo_s": 1, "expresion": "emergencia"}
        }
    ]
}

# ------------------------------------------------------------------------------
# NODO 4: Teclado USB 1 (Publica - mapeo de teclas a acciones de otros nodos)
# ------------------------------------------------------------------------------
nodo_teclado = {
    "node_id": "teclado_01",
    "nombre": "Teclado USB 1",
    "tipo": "publica",
    "mapeos_actuales": [
        {
            "disparador": "e",
            "destinos": [
                {"personaje": "ambienteEA", "node_id": "lucia_01", "accion": "Amanece"}
            ]
        },
        {
            "disparador": "f",
            "destinos": [
                {"personaje": "sofia", "node_id": "sofia_01", "accion": "saludo"}
            ]
        }
    ]
}

# ------------------------------------------------------------------------------
# NODO 5: Pulsador Escenario A (Publica - disparador simple de un botón)
# ------------------------------------------------------------------------------
nodo_boton = {
    "node_id": "boton_01",
    "nombre": "Pulsador Escenario A",
    "tipo": "publica",
    "mapeos_actuales": [
        {
            "disparador": "1",
            "destinos": [
                {"personaje": "ambiente", "node_id": "lucia_02", "accion": "brumaEscena"}
            ]
        }
    ]
}

nodos = [nodo_luces_1, nodo_luces_2, nodo_sofia, nodo_teclado, nodo_boton]

print("Publicando 5 nodos de prueba a HiveMQ...")
while True:
    for nodo in nodos:
        client.publish("pipea/registro/parametros", json.dumps(nodo, ensure_ascii=False))
    time.sleep(4)
