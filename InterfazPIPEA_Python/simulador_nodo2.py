# ==============================================================================
# PIPEA - Simulador de Nodos Virtuales (Separando Tipo de Dispositivo y Rol)
# ==============================================================================
import json
import signal
import sys
import threading
import time
import paho.mqtt.client as mqtt

MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
MQTT_USER = None
MQTT_PASSWORD = None

# --- Broker real PIPEA / Mosquitto (descomentar cuando corresponda) ---
# MQTT_BROKER = "192.168.1.50"
# MQTT_PORT = 1883
# MQTT_USER = "PIPEA"
# MQTT_PASSWORD = "electrizartepipea"

INTERVALO_HEARTBEAT_SEG = 5.0
detener_evento = threading.Event()

# ==============================================================================
# Definición de nodos virtuales:
#   - "rol": "propone" | "reacciona" | "ambos"
#   - "tipo": clase física/lógica del nodo ("teclado", "pulsador", "sofiea", "luminaria_dmx")
# ==============================================================================
NODOS_SIMULADOS = [
    # 1. Nodos con rol "propone"
    {
        "node_id": "tecladopc_01",
        "nombre": "Teclado USB (tecladopc)",
        "rol": "propone",
        "tipo": "teclado",
        "multiples_activadores": True,
        "personajes": ["sofia", "chispanuria", "chispafidel"],
        "disparadores_disponibles": [
            "a", "e", "q", "f", "t", "o", "s", "u", "w", "y",
            "n", "r", "j", "l", "i", "k", "p", "c", "g", "m",
            "1", "2", "3", "4", "5", "6", "7", "8", "9", "0"
        ],
        "mapeos_actuales": [
            {"disparador": "e", "evento": "encendida"},
            {"disparador": "f", "evento": "feliz"},
            {"disparador": "o", "evento": "sorpresa"},
            {"disparador": "g", "evento": "emergencia"}
        ]
    },
    {
        "node_id": "boton_01",
        "nombre": "Pulsador Escenario (BotonEA)",
        "rol": "propone",
        "tipo": "pulsador",
        "multiples_activadores": False,
        "personajes": ["banda"],
        "mapeos_actuales": [
            {"disparador": "", "evento": "soloGuitarra"}
        ]
    },

    # 2. Nodos con rol "reacciona"
    {
        "node_id": "sofia_01",
        "nombre": "Pantalla SofíEA (sofia)",
        "rol": "reacciona",
        "tipo": "sofiea",
        "personajes": ["sofia"],
        "parametros_disponibles": [
            {
                "id": "reaccion_sofia",
                "nombre": "Reacción de SofíEA",
                "tipo": "lista",
                "opciones": [
                    "apagada", "encendida", "tranquila", "feliz", "triste",
                    "sorpresa", "sospecha", "susto", "wacala", "ok",
                    "no_ok", "al_reves", "izquierda", "derecha", "arriba",
                    "abajo", "pregunta", "cuidado", "emergencia", "musica"
                ]
            }
        ],
        "acciones_actuales": [
            {
                "evento": "encendida",
                "accion": "encendida",
                "parametros": {"reaccion_sofia": "encendida"}
            },
            {
                "evento": "feliz",
                "accion": "feliz",
                "parametros": {"reaccion_sofia": "feliz"}
            }
        ]
    },
    {
        "node_id": "lucia_segura_01",
        "nombre": "Luces DMX (Lucía Segura)",
        "rol": "reacciona",
        "tipo": "luminaria_dmx",
        "personajes": ["banda"],
        "parametros_disponibles": [
            {
                "id": "escena_secuencia",
                "nombre": "Escena / Secuencia / Acción",
                "tipo": "lista",
                "opciones": [
                    "oscura", "coloresFrios", "coloresCalidos", "coloresVivos",
                    "introOscura", "frioSuave", "frioFuerte",
                    "calidoSuave", "calidoFuerte", "cumbiaSuave", "cumbiaFuerte",
                    "soloGuitarra", "soloBajo", "soloBateria",
                    "cero", "derecha", "izquierda", "circulos"
                ]
            },
            {
                "id": "intensidad",
                "nombre": "Intensidad (0-255)",
                "tipo": "int",
                "min": 0,
                "max": 255
            },
            {
                "id": "duracion",
                "nombre": "Duración transición (s)",
                "tipo": "int",
                "min": 0,
                "max": 30
            },
            {
                "id": "paleta",
                "nombre": "Paleta (LuciEA)",
                "tipo": "lista",
                "opciones": ["1", "m", "p", "d", "a", "D"]
            },
            {
                "id": "curva",
                "nombre": "Curva (ChuncheDMX)",
                "tipo": "lista",
                "opciones": ["l", "c", "r", "s"]
            }
        ],
        "acciones_actuales": [
            {
                "evento": "soloGuitarra",
                "accion": "soloGuitarra",
                "parametros": {
                    "escena_secuencia": "soloGuitarra",
                    "intensidad": 255,
                    "duracion": 1,
                    "paleta": "1",
                    "curva": "l"
                }
            }
        ]
    }
]

estado_local_nodos = {n["node_id"]: json.loads(json.dumps(n)) for n in NODOS_SIMULADOS}


def on_connect(client, userdata, flags, rc, properties=None):
    print(f"[SIMULADOR] Conectado al broker MQTT (rc={rc})")
    for nodo in NODOS_SIMULADOS:
        topico_cfg = f"pipea/config/{nodo['nombre']}"
        client.subscribe(topico_cfg)
        print(f"[SIMULADOR] Suscrito a: {topico_cfg}")
    client.subscribe("pipea/evento/+")
    print("[SIMULADOR] Suscrito a: pipea/evento/+")


def on_message(client, userdata, msg):
    topico = msg.topic
    texto = msg.payload.decode("utf-8", errors="replace")

    if topico.startswith("pipea/config/"):
        try:
            data = json.loads(texto)
            nid = data.get("node_id")
            if nid and nid in estado_local_nodos:
                if "acciones_actuales" in data:
                    estado_local_nodos[nid]["acciones_actuales"] = data["acciones_actuales"]
                if "mapeos_actuales" in data:
                    estado_local_nodos[nid]["mapeos_actuales"] = data["mapeos_actuales"]
                print(f"\n[CONFIG RECIBIDA] {topico} -> {json.dumps(data, ensure_ascii=False)}")
        except Exception as e:
            print(f"[ERROR CONFIG] {e}")

    elif topico.startswith("pipea/evento/"):
        evento_recibido = topico.replace("pipea/evento/", "", 1).strip()
        print(f"\n[EVENTO EN ESCENA] Tópico: {topico} | Payload: {texto}")
        for nid, nodo in estado_local_nodos.items():
            if nodo.get("rol") in ("reacciona", "ambos"):
                for acc in nodo.get("acciones_actuales", []):
                    if (acc.get("evento") or "").strip() == evento_recibido:
                        print(
                            f"   -> {nodo['nombre']} ({nid} · {nodo['tipo']}) REACCIONA | "
                            f"acción='{acc.get('accion') or evento_recibido}' | "
                            f"params={json.dumps(acc.get('parametros', {}), ensure_ascii=False)}"
                        )


def ciclo_heartbeat(client):
    while not detener_evento.is_set():
        for nid, nodo in estado_local_nodos.items():
            topico_reg = f"pipea/registro/{nid}"
            payload = json.dumps(nodo, ensure_ascii=False)
            client.publish(topico_reg, payload)
        detener_evento.wait(INTERVALO_HEARTBEAT_SEG)


def manejar_salida(sig, frame):
    print("\n[SIMULADOR] Deteniendo simulación...")
    detener_evento.set()


def main():
    signal.signal(signal.SIGINT, manejar_salida)
    signal.signal(signal.SIGTERM, manejar_salida)

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    if MQTT_USER and MQTT_PASSWORD:
        client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_start()

    hilo_hb = threading.Thread(target=ciclo_heartbeat, args=(client,), daemon=True)
    hilo_hb.start()

    print("=================================================================")
    print(" Simulador PIPEA activo (Ctrl+C para salir)")
    print(" Escribe el nombre de un evento y presiona Enter para publicarlo")
    print(" en pipea/evento/<evento> (ej. encendida, feliz, soloGuitarra)")
    print("=================================================================")

    try:
        while not detener_evento.is_set():
            try:
                linea = input().strip()
            except EOFError:
                break
            if not linea:
                continue
            topico_ev = f"pipea/evento/{linea}"
            payload_ev = json.dumps({"evento": linea}, ensure_ascii=False)
            client.publish(topico_ev, payload_ev)
            print(f"[SIMULADOR PUB] {topico_ev} -> {payload_ev}")
    except KeyboardInterrupt:
        detener_evento.set()
    finally:
        detener_evento.set()
        client.loop_stop()
        client.disconnect()
        print("[SIMULADOR] Desconectado limpiamente.")
        sys.exit(0)


if __name__ == "__main__":
    main()
