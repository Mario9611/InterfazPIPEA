# ==============================================================================
# PIPEA - Servidor Backend (FastAPI + MQTT) e Interfaz Web Dinámica (Alpine.js)
# ==============================================================================
import json
import os
import sys
import threading
import time
import webbrowser
from contextlib import asynccontextmanager
from datetime import datetime

import paho.mqtt.client as mqtt
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

TIMEOUT_CONEXION_SEG = 15


def ruta_recurso(relativa: str) -> str:
    """Obtiene la ruta de archivos incluidos en el paquete (como static/)."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, relativa)


def ruta_persistente(nombre_archivo: str) -> str:
    """Obtiene la ruta junto al .exe (o junto a app.py) para guardar datos."""
    if getattr(sys, "frozen", False):
        base_dir = os.path.dirname(sys.executable)
        os.chdir(base_dir)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, nombre_archivo)


ARCHIVO_ESTADO = ruta_persistente("estado_nodos.json")
nodos_registrados = {}
nodos_configurados_manualmente = set()
ultimo_config_mqtt = {
    "topico": None,
    "payload": None,
    "timestamp": None
}

personajes_catalogo = {}


def normalizar_rol(ndata: dict) -> str:
    """
    Determina el rol del nodo ('propone', 'reacciona' o 'ambos').
    Mantiene retrocompatibilidad con JSONs antiguos que enviaban 'publica'/'reacciona' en 'tipo'.
    """
    rol_raw = str(ndata.get("rol") or "").strip().lower()
    if rol_raw in ("propone", "publica"):
        return "propone"
    if rol_raw in ("reacciona", "escucha"):
        return "reacciona"
    if rol_raw in ("ambos", "dual", "propone_y_reacciona"):
        return "ambos"

    tipo_raw = str(ndata.get("tipo") or "").strip().lower()
    if tipo_raw in ("publica", "propone"):
        return "propone"
    if tipo_raw == "reacciona":
        return "reacciona"
    if tipo_raw in ("ambos", "dual"):
        return "ambos"

    tiene_prop = bool(ndata.get("mapeos_actuales") or ndata.get("disparadores_disponibles"))
    tiene_reac = bool(ndata.get("acciones_actuales") or ndata.get("parametros_disponibles"))
    if tiene_prop and tiene_reac:
        return "ambos"
    if tiene_prop:
        return "propone"
    return "reacciona"


def normalizar_tipo_dispositivo(ndata: dict, rol: str) -> str:
    """
    Determina el tipo físico/lógico del nodo (ej. 'teclado', 'pulsador', 'luminaria_dmx', 'sofiea').
    Si el JSON antiguo traía 'publica'/'reacciona' en 'tipo', infiere un tipo descriptivo.
    """
    tipo_raw = str(ndata.get("tipo") or "").strip()
    if tipo_raw and tipo_raw.lower() not in ("publica", "propone", "reacciona", "ambos", "dual"):
        return tipo_raw

    texto = f"{ndata.get('node_id', '')} {ndata.get('nombre', '')}".lower()
    if "teclado" in texto or "keypad" in texto:
        return "teclado"
    if any(k in texto for k in ["boton", "pulsador", "switch"]):
        return "pulsador"
    if any(k in texto for k in ["sensor", "pir", "ultrasonido"]):
        return "sensor"
    if any(k in texto for k in ["lucia", "luz", "luces", "dmx", "bombillo"]):
        return "luminaria_dmx"
    if "sofia" in texto or "sofiea" in texto:
        return "sofiea"
    return "nodo_generico"


def nodo_puede_proponer(ndata: dict) -> bool:
    return normalizar_rol(ndata) in ("propone", "ambos")


def nodo_puede_reaccionar(ndata: dict) -> bool:
    return normalizar_rol(ndata) in ("reacciona", "ambos")


def inferir_multiples_activadores(ndata: dict) -> bool:
    """
    Determina si un nodo que propone tiene múltiples activadores (ej. teclado)
    o un único activador (ej. pulsador/botón/sensor).
    """
    if isinstance(ndata.get("multiples_activadores"), bool):
        return ndata["multiples_activadores"]
    if isinstance(ndata.get("activador_unico"), bool):
        return not ndata["activador_unico"]

    disparadores = ndata.get("disparadores_disponibles")
    if isinstance(disparadores, list) and len(disparadores) > 1:
        return True

    texto = f"{ndata.get('node_id', '')} {ndata.get('nombre', '')} {ndata.get('tipo', '')}".lower()
    if any(k in texto for k in ["boton", "pulsador", "sensor", "switch", "pir", "ultrasonido"]):
        return False
    if any(k in texto for k in ["teclado", "keypad", "key", "matriz", "controlador"]):
        return True

    return True


def topico_config_de_nodo(ndata: dict) -> str:
    """Devuelve el tópico pipea/config/[nombre_nodo] usando el nombre del nodo."""
    nombre = str(ndata.get("nombre") or ndata.get("node_id") or "nodo").strip()
    return f"pipea/config/{nombre}"


def normalizar_estructura_nodo(ndata: dict) -> dict:
    """Garantiza campos base para rol, tipo de dispositivo, relaciones, eventos y acciones."""
    rol = normalizar_rol(ndata)
    ndata["rol"] = rol
    ndata["tipo"] = normalizar_tipo_dispositivo(ndata, rol)

    if not isinstance(ndata.get("personajes"), list):
        ndata["personajes"] = []
    if not isinstance(ndata.get("comentarios"), str):
        ndata["comentarios"] = ""

    if nodo_puede_reaccionar(ndata):
        if not isinstance(ndata.get("acciones_actuales"), list):
            ndata["acciones_actuales"] = []
        for acc in ndata["acciones_actuales"]:
            if isinstance(acc, dict):
                ev = str(acc.get("evento") or "").strip()
                acc["evento"] = ev
                acc["topico_evento"] = f"pipea/evento/{ev}" if ev else ""
                if not isinstance(acc.get("parametros"), dict):
                    acc["parametros"] = {}

    if nodo_puede_proponer(ndata):
        multi = inferir_multiples_activadores(ndata)
        ndata["multiples_activadores"] = multi
        if not isinstance(ndata.get("mapeos_actuales"), list):
            ndata["mapeos_actuales"] = []
        if not multi and len(ndata["mapeos_actuales"]) == 0:
            ndata["mapeos_actuales"] = [{"disparador": "", "evento": "", "topico_evento": ""}]
        for m in ndata["mapeos_actuales"]:
            if isinstance(m, dict):
                disp = "" if not multi else (m.get("disparador") or "")[:1]
                ev = str(m.get("evento") or "").strip()
                m["disparador"] = disp
                m["evento"] = ev
                m["topico_evento"] = f"pipea/evento/{ev}" if ev else ""
        if not multi and len(ndata["mapeos_actuales"]) > 1:
            ndata["mapeos_actuales"] = [ndata["mapeos_actuales"][0]]

    return ndata


def refrescar_estados_conexion():
    """Actualiza 'conectado' como indicador de presencia sin ocultar nodos registrados."""
    ahora = time.time()
    for ndata in nodos_registrados.values():
        normalizar_estructura_nodo(ndata)
        ultimo = ndata.get("ultimo_visto")
        ndata["conectado"] = bool(ultimo is not None and (ahora - ultimo) <= TIMEOUT_CONEXION_SEG)


def registrar_personajes_de_nodo(lista_pers):
    """Agrega al catálogo persistente los personajes reportados por un nodo si aún no existen."""
    if not isinstance(lista_pers, list):
        return
    for p in lista_pers:
        if not isinstance(p, str):
            continue
        nombre_limpio = p.strip()
        if not nombre_limpio:
            continue
        if nombre_limpio not in personajes_catalogo:
            personajes_catalogo[nombre_limpio] = {
                "nombre": nombre_limpio,
                "descripcion": "",
                "origen": "nodo",
            }


# ------------------------------------------------------------------------------
# Carga inicial de estado persistente (nodos permanecen configurables al arrancar)
# ------------------------------------------------------------------------------
if os.path.exists(ARCHIVO_ESTADO):
    try:
        with open(ARCHIVO_ESTADO, "r", encoding="utf-8") as f:
            data_guardada = json.load(f)
            nodos_cargados = data_guardada.get("nodos", {})
            for nid, ndata in nodos_cargados.items():
                ndata["conectado"] = False
                ndata["ultimo_visto"] = None
                normalizar_estructura_nodo(ndata)
            nodos_registrados = nodos_cargados
            nodos_configurados_manualmente = set(data_guardada.get("configurados", []))

            pers_guardados = data_guardada.get("personajes", {})
            if isinstance(pers_guardados, dict):
                for pname, pdata in pers_guardados.items():
                    if isinstance(pdata, dict):
                        personajes_catalogo[pname] = {
                            "nombre": pdata.get("nombre", pname),
                            "descripcion": pdata.get("descripcion", ""),
                            "origen": pdata.get("origen", "usuario"),
                        }
    except Exception as e:
        print("No se pudo cargar estado previo:", e)


def guardar_estado():
    """Guarda en disco la configuración de los nodos y el catálogo de personajes."""
    try:
        nodos_a_guardar = {}
        for nid, ndata in nodos_registrados.items():
            copia = dict(ndata)
            normalizar_estructura_nodo(copia)
            copia["conectado"] = False
            copia["ultimo_visto"] = None
            nodos_a_guardar[nid] = copia

        with open(ARCHIVO_ESTADO, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "nodos": nodos_a_guardar,
                    "configurados": list(nodos_configurados_manualmente),
                    "personajes": personajes_catalogo,
                },
                f,
                indent=2,
                ensure_ascii=False,
            )
    except Exception as e:
        print("Error guardando estado:", e)


# ------------------------------------------------------------------------------
# Configuración y Callbacks del Cliente MQTT
# ------------------------------------------------------------------------------
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
MQTT_USER = None
MQTT_PASSWORD = None

# --- Broker real PIPEA / Mosquitto (descomentar y ajustar cuando corresponda) ---
# MQTT_BROKER = "192.168.1.50"
# MQTT_PORT = 1883
# MQTT_USER = "PIPEA"
# MQTT_PASSWORD = "electrizartepipea"


def on_connect(client, userdata, flags, rc, properties=None):
    """Se ejecuta automáticamente al conectarse con éxito al broker MQTT."""
    print("Conectado al broker MQTT con código:", rc)
    client.subscribe("pipea/registro/+")
    client.subscribe("pipea/config/+")
    client.subscribe("pipea/config/nodo/#")
    for ndata in nodos_registrados.values():
        client.subscribe(topico_config_de_nodo(ndata))


def on_message(client, userdata, msg):
    """Se ejecuta cada vez que llega un mensaje en un tópico suscrito."""
    try:
        texto_raw = msg.payload.decode().strip()
        if not texto_raw:
            return
        payload = json.loads(texto_raw)

        if msg.topic.startswith("pipea/config/"):
            ultimo_config_mqtt["topico"] = msg.topic
            ultimo_config_mqtt["payload"] = payload
            ultimo_config_mqtt["timestamp"] = datetime.now().strftime("%H:%M:%S")
            print(f"[MQTT RX CONFIG] {msg.topic} -> {json.dumps(payload, ensure_ascii=False)}")
            return

        node_id = payload.get("node_id")
        if not node_id:
            return

        if node_id in nodos_registrados and node_id in nodos_configurados_manualmente:
            existente = nodos_registrados[node_id]
            for clave in ["nombre", "rol", "tipo", "parametros_disponibles", "disparadores_disponibles", "multiples_activadores", "activador_unico"]:
                if clave in payload:
                    existente[clave] = payload[clave]
            normalizar_estructura_nodo(existente)
            existente["conectado"] = True
            existente["ultimo_visto"] = time.time()
            nodos_registrados[node_id] = existente
        else:
            normalizar_estructura_nodo(payload)
            payload["conectado"] = True
            payload["ultimo_visto"] = time.time()
            nodos_registrados[node_id] = payload

        mqtt_client.subscribe(topico_config_de_nodo(nodos_registrados[node_id]))
        registrar_personajes_de_nodo(payload.get("personajes"))
        guardar_estado()
        print(f"Nodo registrado/sincronizado: {node_id}")
    except Exception as e:
        print("Error al procesar mensaje MQTT:", e)


mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
if MQTT_USER and MQTT_PASSWORD:
    mqtt_client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
        mqtt_client.loop_start()
    except Exception as e:
        print("Error conectando al broker MQTT al iniciar:", e)
    yield
    try:
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
        print("Cliente MQTT detenido limpiamente.")
    except Exception as e:
        print("Error al detener cliente MQTT:", e)


app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory=ruta_recurso("static")), name="static")


# ------------------------------------------------------------------------------
# Endpoints REST de la API (consumidos por el navegador web)
# ------------------------------------------------------------------------------
@app.get("/api/nodos")
def obtener_nodos():
    """Devuelve todos los nodos registrados (conectados o desconectados) en JSON."""
    refrescar_estados_conexion()
    return list(nodos_registrados.values())


@app.get("/api/ultimo-config")
def obtener_ultimo_config():
    """Devuelve el último mensaje recibido/emitido en el monitor."""
    return ultimo_config_mqtt


@app.post("/api/configurar/{node_id}")
def configurar_nodo(node_id: str, data: dict):
    """
    Recibe la configuración editada desde la interfaz web para un nodo registrado
    (esté conectado o desconectado en ese momento), la guarda localmente en
    estado_nodos.json y la publica con retain=True en pipea/config/[nombre_nodo].
    """
    if node_id not in nodos_registrados:
        raise HTTPException(status_code=404, detail="Nodo no encontrado")

    nodo_actual = nodos_registrados[node_id]
    normalizar_estructura_nodo(nodo_actual)
    multi = inferir_multiples_activadores(nodo_actual)
    nodo_actual["multiples_activadores"] = multi

    if "acciones_actuales" in data and isinstance(data["acciones_actuales"], list):
        acciones_por_evento = {}
        for acc in data["acciones_actuales"]:
            if not isinstance(acc, dict):
                continue
            ev = str(acc.get("evento") or "").strip()
            accion_txt = str(acc.get("accion") or "").strip()
            params = acc.get("parametros", {}) if isinstance(acc.get("parametros"), dict) else {}
            clave = ev if ev else f"__sin_evento_{len(acciones_por_evento)}"
            if clave in acciones_por_evento:
                if accion_txt:
                    acciones_por_evento[clave]["accion"] = accion_txt
                acciones_por_evento[clave]["parametros"].update(params)
            else:
                acciones_por_evento[clave] = {
                    "evento": ev,
                    "topico_evento": f"pipea/evento/{ev}" if ev else "",
                    "accion": accion_txt,
                    "parametros": params,
                }
        nodo_actual["acciones_actuales"] = list(acciones_por_evento.values())

    if "mapeos_actuales" in data and isinstance(data["mapeos_actuales"], list):
        mapeos_limpios = []
        filas_fuente = data["mapeos_actuales"][:1] if not multi else data["mapeos_actuales"]
        for m in filas_fuente:
            if not isinstance(m, dict):
                continue
            disp = "" if not multi else (m.get("disparador") or "")[:1]
            ev = str(m.get("evento") or "").strip()
            mapeos_limpios.append({
                "disparador": disp,
                "evento": ev,
                "topico_evento": f"pipea/evento/{ev}" if ev else "",
            })
        nodo_actual["mapeos_actuales"] = mapeos_limpios

    nodos_registrados[node_id] = nodo_actual
    nodos_configurados_manualmente.add(node_id)
    guardar_estado()

    topico = topico_config_de_nodo(nodo_actual)
    payload_config = {
        "node_id": nodo_actual.get("node_id"),
        "nombre": nodo_actual.get("nombre"),
        "rol": nodo_actual.get("rol"),
        "tipo": nodo_actual.get("tipo"),
        "multiples_activadores": multi,
        "acciones_actuales": nodo_actual.get("acciones_actuales", []) if nodo_puede_reaccionar(nodo_actual) else None,
        "mapeos_actuales": nodo_actual.get("mapeos_actuales", []) if nodo_puede_proponer(nodo_actual) else None,
    }
    payload_config = {k: v for k, v in payload_config.items() if v is not None}

    payload_json = json.dumps(payload_config, indent=2, ensure_ascii=False)
    print(f"\n[MQTT OUT RETAIN] Tópico: {topico}\n{payload_json}\n")
    mqtt_client.publish(topico, payload_json, retain=True)

    ultimo_config_mqtt["topico"] = topico
    ultimo_config_mqtt["payload"] = payload_config
    ultimo_config_mqtt["timestamp"] = datetime.now().strftime("%H:%M:%S")

    return {"status": "success", "topico_publicado": topico, "payload": payload_config}


@app.post("/api/probar-evento")
def probar_evento(data: dict):
    """Publica un evento de prueba simple en pipea/evento/[nombre_evento]."""
    evento = str(data.get("evento") or "").strip()
    if not evento:
        raise HTTPException(status_code=400, detail="Debes indicar el nombre del evento a probar.")

    topico = f"pipea/evento/{evento}"
    payload_evento = {"evento": evento}
    payload_json = json.dumps(payload_evento, ensure_ascii=False)
    print(f"\n[MQTT TEST EVENTO] Tópico: {topico}\n{payload_json}\n")
    mqtt_client.publish(topico, payload_json)

    ultimo_config_mqtt["topico"] = topico
    ultimo_config_mqtt["payload"] = payload_evento
    ultimo_config_mqtt["timestamp"] = datetime.now().strftime("%H:%M:%S")

    return {"status": "ok", "topico_publicado": topico, "payload": payload_evento}


@app.post("/api/reiniciar-configuracion")
def reiniciar_configuracion():
    """Borra toda la configuración guardada y limpia los mensajes retenidos en el broker."""
    global nodos_registrados, nodos_configurados_manualmente, personajes_catalogo, ultimo_config_mqtt

    for ndata in nodos_registrados.values():
        try:
            mqtt_client.publish(topico_config_de_nodo(ndata), "", retain=True)
        except Exception:
            pass

    nodos_registrados = {}
    nodos_configurados_manualmente = set()
    personajes_catalogo = {}
    ultimo_config_mqtt = {
        "topico": None,
        "payload": None,
        "timestamp": None,
    }
    guardar_estado()
    return {"status": "reiniciado"}


@app.post("/api/relaciones-nodo-personaje")
def guardar_todas_relaciones_nodo_personaje(data: dict):
    """Guarda en lote las asignaciones de personajes y comentarios de los nodos."""
    relaciones = data.get("relaciones", [])
    if not isinstance(relaciones, list):
        raise HTTPException(status_code=400, detail="Formato inválido de relaciones.")

    for item in relaciones:
        if not isinstance(item, dict):
            continue
        node_id = item.get("node_id")
        if not node_id or node_id not in nodos_registrados:
            continue

        nodo_actual = nodos_registrados[node_id]
        normalizar_estructura_nodo(nodo_actual)

        personajes_recibidos = item.get("personajes", [])
        if not isinstance(personajes_recibidos, list):
            personajes_recibidos = []

        personajes_limpios = []
        for p in personajes_recibidos:
            if isinstance(p, str):
                nombre_p = p.strip()
                if nombre_p and nombre_p in personajes_catalogo and nombre_p not in personajes_limpios:
                    personajes_limpios.append(nombre_p)

        if nodo_actual.get("rol") == "reacciona" and len(personajes_limpios) > 1:
            personajes_limpios = [personajes_limpios[0]]

        comentarios_limpios = str(item.get("comentarios", "") or "").strip()

        nodo_actual["personajes"] = personajes_limpios
        nodo_actual["comentarios"] = comentarios_limpios
        nodos_registrados[node_id] = nodo_actual
        nodos_configurados_manualmente.add(node_id)

    guardar_estado()
    return {"status": "success"}


@app.get("/api/personajes")
def obtener_personajes():
    """Devuelve el catálogo persistente de personajes."""
    return list(personajes_catalogo.values())


@app.post("/api/personajes")
def guardar_personaje(data: dict):
    """Crea un personaje nuevo o actualiza la descripción de uno existente."""
    nombre = str(data.get("nombre", "")).strip()
    descripcion = str(data.get("descripcion", "")).strip()

    if not nombre:
        raise HTTPException(status_code=400, detail="El nombre del personaje es obligatorio.")

    if nombre in personajes_catalogo:
        personajes_catalogo[nombre]["descripcion"] = descripcion
    else:
        personajes_catalogo[nombre] = {
            "nombre": nombre,
            "descripcion": descripcion,
            "origen": "usuario",
        }

    guardar_estado()
    return personajes_catalogo[nombre]


@app.delete("/api/personajes/{nombre}")
def eliminar_personaje(nombre: str):
    """Elimina un personaje creado por el usuario y limpia referencias en nodos."""
    nombre_limpio = nombre.strip()
    if nombre_limpio not in personajes_catalogo:
        raise HTTPException(status_code=404, detail="Personaje no encontrado.")

    if personajes_catalogo[nombre_limpio].get("origen", "usuario") == "nodo":
        raise HTTPException(
            status_code=400,
            detail="No se puede eliminar un personaje definido por un nodo.",
        )

    del personajes_catalogo[nombre_limpio]

    for ndata in nodos_registrados.values():
        pers_nodo = ndata.get("personajes")
        if isinstance(pers_nodo, list) and nombre_limpio in pers_nodo:
            ndata["personajes"] = [p for p in pers_nodo if p != nombre_limpio]

    guardar_estado()
    return {"status": "eliminado", "nombre": nombre_limpio}


# ------------------------------------------------------------------------------
# Interfaz Web (HTML + TailwindCSS + Alpine.js)
# ------------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <title>PIPEA - Configuración de Nodos</title>
        <link rel="stylesheet" href="/static/tailwind.css">
        <script src="/static/alpine.min.js" defer></script>
        <style>
            .pipea-header {
                background: linear-gradient(90deg, #1e3a8a 0%, #3730a3 55%, #0f766e 100%);
                color: #ffffff;
            }
            .pill-modo {
                background-color: rgba(255, 255, 255, 0.18);
                color: #ffffff;
                border: 1px solid rgba(255, 255, 255, 0.35);
            }
            .btn-info-top {
                background-color: #facc15;
                color: #1e293b;
                border: 1px solid #eab308;
            }
            .btn-info-top:hover {
                background-color: #fde047;
            }
            .btn-borrar-top {
                background-color: #b91c1c;
                color: #ffffff;
                border: 1px solid #fca5a5;
            }
            .btn-borrar-top:hover {
                background-color: #991b1b;
            }
            .sec-proponen {
                background-color: #fef3c7;
                color: #78350f;
                border: 1px solid #f59e0b;
            }
            .sec-reaccionan {
                background-color: #e0f2fe;
                color: #0c4a6e;
                border: 1px solid #0284c7;
            }
            .card-proponen {
                background-color: #fffbeb;
                border: 1px solid #fcd34d;
                border-left: 4px solid #d97706;
            }
            .card-proponen:hover {
                background-color: #fef3c7;
            }
            .card-proponen-activa {
                background-color: #fef3c7;
                border: 1px solid #b45309;
                border-left: 4px solid #b45309;
            }
            .card-reaccionan {
                background-color: #f0f9ff;
                border: 1px solid #bae6fd;
                border-left: 4px solid #0284c7;
            }
            .card-reaccionan:hover {
                background-color: #e0f2fe;
            }
            .card-reaccionan-activa {
                background-color: #e0f2fe;
                border: 1px solid #1d4ed8;
                border-left: 4px solid #1d4ed8;
            }
            .estado-online {
                background-color: #dcfce7;
                color: #166534;
                border: 1px solid #86efac;
            }
            .estado-offline {
                background-color: #f1f5f9;
                color: #475569;
                border: 1px solid #cbd5e1;
            }
            .aviso-offline {
                background-color: #fffbeb;
                color: #92400e;
                border: 1px solid #fcd34d;
            }
            .tab-indigo {
                background-color: #eef2ff;
                color: #312e81;
                border: 1px solid #a5b4fc;
            }
            .tab-indigo-activa {
                background-color: #4338ca;
                color: #ffffff;
                border: 1px solid #3730a3;
            }
            .tab-ambar {
                background-color: #fffbeb;
                color: #78350f;
                border: 1px solid #fcd34d;
            }
            .tab-ambar-activa {
                background-color: #b45309;
                color: #ffffff;
                border: 1px solid #92400e;
            }
            .tab-teal {
                background-color: #f0fdfa;
                color: #134e4a;
                border: 1px solid #5eead4;
            }
            .tab-teal-activa {
                background-color: #0f766e;
                color: #ffffff;
                border: 1px solid #115e59;
            }
            .btn-azul {
                background-color: #2563eb;
                color: #ffffff;
            }
            .btn-azul:hover {
                background-color: #1d4ed8;
            }
            .btn-verde {
                background-color: #16a34a;
                color: #ffffff;
            }
            .btn-verde:hover {
                background-color: #15803d;
            }
            .btn-teal {
                background-color: #0f766e;
                color: #ffffff;
            }
            .btn-teal:hover {
                background-color: #115e59;
            }
            .badge-proponen {
                background-color: #fef3c7;
                color: #78350f;
                border: 1px solid #f59e0b;
            }
            .badge-reaccionan {
                background-color: #e0f2fe;
                color: #0c4a6e;
                border: 1px solid #0284c7;
            }
            .panel-prueba-evento {
                background-color: #f8fafc;
                border: 1px solid #cbd5e1;
                border-left: 4px solid #0f766e;
            }
            .monitor-mqtt {
                background-color: #0f172a;
                color: #f1f5f9;
            }
        </style>
    </head>
    <body class="bg-gray-100 min-h-screen flex flex-col" x-data="appData()">

        <!-- BARRA SUPERIOR -->
        <header class="pipea-header shadow-md px-6 py-3 flex justify-between items-center gap-3">
            <div class="flex flex-col items-start gap-1.5">
                <div class="flex items-center gap-3">
                    <h1 class="text-2xl font-black tracking-wider leading-none">PIPEA</h1>
                    <span class="pill-modo text-xs font-semibold px-2.5 py-0.5 rounded-full">
                        Modo Normal
                    </span>
                </div>
                <button @click="showInfo = true" class="btn-info-top px-3 py-1 rounded text-xs font-bold transition cursor-pointer">
                    Info...
                </button>
            </div>
            <div>
                <button @click="borrarTodaConfiguracion()"
                        class="btn-borrar-top px-3.5 py-1.5 rounded text-xs font-bold transition cursor-pointer">
                    Borrar configuración
                </button>
            </div>
        </header>

        <!-- CONTENEDOR PRINCIPAL -->
        <main class="flex-1 max-w-7xl w-full mx-auto p-6 grid grid-cols-12 gap-6">

            <!-- PANEL IZQUIERDO: Nodos Registrados -->
            <aside class="col-span-3 bg-white p-4 rounded-lg shadow flex flex-col justify-between">
                <div>
                    <h2 class="text-lg font-bold mb-3 text-gray-800 border-b pb-2">Nodos Registrados</h2>

                    <div class="space-y-4 max-h-[65vh] overflow-y-auto pr-1">
                        <!-- 1. NODOS CON ROL PROPONER -->
                        <div>
                            <div class="sec-proponen flex items-center justify-between px-2.5 py-1 rounded text-xs font-bold mb-2">
                                <span>Nodos que proponen</span>
                                <span x-text="nodosProponen().length"></span>
                            </div>
                            <div class="space-y-2">
                                <template x-for="nodo in nodosProponen()" :key="nodo.node_id">
                                    <div @click="seleccionarNodo(nodo)"
                                         class="p-3 rounded cursor-pointer transition"
                                         :class="nodoSelected?.node_id === nodo.node_id ? 'card-proponen-activa' : 'card-proponen'">
                                        <div class="flex items-start justify-between gap-2">
                                            <p class="font-bold text-gray-800 text-sm" x-text="nodo.nombre"></p>
                                            <span class="text-[10px] font-bold px-2 py-0.5 rounded-full shrink-0"
                                                  :class="nodo.conectado ? 'estado-online' : 'estado-offline'"
                                                  x-text="nodo.conectado ? '● Conectado' : '○ Desconectado'"></span>
                                        </div>
                                        <p class="text-[11px] text-gray-500 mt-1" x-text="'Tipo: ' + (nodo.tipo || 'nodo')"></p>
                                        <p class="text-xs font-semibold mt-0.5" style="color: #92400e;" x-text="'Rol: ' + textoRol(nodo)"></p>
                                    </div>
                                </template>
                                <p x-show="nodosProponen().length === 0" class="text-xs text-gray-400 italic py-2 text-center">
                                    Sin nodos que propongan...
                                </p>
                            </div>
                        </div>

                        <!-- 2. NODOS CON ROL REACCIONAR -->
                        <div>
                            <div class="sec-reaccionan flex items-center justify-between px-2.5 py-1 rounded text-xs font-bold mb-2">
                                <span>Nodos que reaccionan</span>
                                <span x-text="nodosReaccionan().length"></span>
                            </div>
                            <div class="space-y-2">
                                <template x-for="nodo in nodosReaccionan()" :key="nodo.node_id">
                                    <div @click="seleccionarNodo(nodo)"
                                         class="p-3 rounded cursor-pointer transition"
                                         :class="nodoSelected?.node_id === nodo.node_id ? 'card-reaccionan-activa' : 'card-reaccionan'">
                                        <div class="flex items-start justify-between gap-2">
                                            <p class="font-bold text-gray-800 text-sm" x-text="nodo.nombre"></p>
                                            <span class="text-[10px] font-bold px-2 py-0.5 rounded-full shrink-0"
                                                  :class="nodo.conectado ? 'estado-online' : 'estado-offline'"
                                                  x-text="nodo.conectado ? '● Conectado' : '○ Desconectado'"></span>
                                        </div>
                                        <p class="text-[11px] text-gray-500 mt-1" x-text="'Tipo: ' + (nodo.tipo || 'nodo')"></p>
                                        <p class="text-xs font-semibold mt-0.5" style="color: #075985;" x-text="'Rol: ' + textoRol(nodo)"></p>
                                    </div>
                                </template>
                                <p x-show="nodosReaccionan().length === 0" class="text-xs text-gray-400 italic py-2 text-center">
                                    Sin nodos que reaccionen...
                                </p>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="mt-4 pt-3 border-t text-xs text-gray-500 space-y-1">
                    <div class="flex justify-between">
                        <span>Conectados ahora:</span>
                        <span class="font-bold text-green-700" x-text="nodosConectados().length + ' / ' + nodos.length"></span>
                    </div>
                </div>
            </aside>

            <!-- PANEL DERECHO: Pestañas -->
            <section class="col-span-9 bg-white p-6 rounded-lg shadow flex flex-col justify-between">
                <div>
                    <div class="flex flex-wrap items-center justify-between border-b pb-3 mb-5 gap-3">
                        <div class="flex flex-wrap items-center gap-2.5">
                            <button @click="pestanaActiva = 'nodo'"
                                    class="px-4 py-2 rounded-lg text-sm font-bold transition cursor-pointer"
                                    :class="pestanaActiva === 'nodo' ? 'tab-indigo-activa' : 'tab-indigo'">
                                <span>Configuración de Nodo</span>
                            </button>

                            <button @click="pestanaActiva = 'personajes'; cargarPersonajes()"
                                    class="px-4 py-2 rounded-lg text-sm font-bold transition cursor-pointer"
                                    :class="pestanaActiva === 'personajes' ? 'tab-ambar-activa' : 'tab-ambar'">
                                <span>Personajes</span>
                            </button>

                            <button @click="pestanaActiva = 'nodoPersonaje'; prepararRelacionesUI()"
                                    class="px-4 py-2 rounded-lg text-sm font-bold transition cursor-pointer"
                                    :class="pestanaActiva === 'nodoPersonaje' ? 'tab-teal-activa' : 'tab-teal'">
                                <span>Nodo-Personaje</span>
                            </button>
                        </div>
                    </div>

                    <!-- PESTAÑA 1: Configuración de Nodo -->
                    <div x-show="pestanaActiva === 'nodo'" class="flex-1 flex flex-col justify-between">
                        <template x-if="nodoSelected">
                            <div class="flex flex-col h-full justify-between space-y-5">
                                <div>
                                    <div class="flex flex-wrap justify-between items-center border-b pb-3 mb-4 gap-2">
                                        <div>
                                            <h2 class="text-xl font-bold text-gray-800" x-text="'Configuración de Nodos — ' + nodoSelected.nombre"></h2>
                                            <p class="text-xs text-gray-500"
                                               x-text="'ID: ' + nodoSelected.node_id + ' | Tipo: ' + (nodoSelected.tipo || 'nodo') + ' | Rol: ' + textoRol(nodoSelected)"></p>
                                        </div>
                                        <div class="flex items-center gap-2">
                                            <span class="text-xs font-bold px-3 py-1 rounded-full"
                                                  :class="esNodoConectadoActual(nodoSelected) ? 'estado-online' : 'estado-offline'"
                                                  x-text="esNodoConectadoActual(nodoSelected) ? '● Conectado' : '○ Desconectado'"></span>
                                            <span class="text-xs font-bold px-3 py-1 rounded-full"
                                                  :class="puedeProponer(nodoSelected) ? 'badge-proponen' : 'badge-reaccionan'"
                                                  x-text="'Rol: ' + textoRol(nodoSelected)"></span>
                                        </div>
                                    </div>

                                    <!-- Aviso informativo si el nodo está desconectado -->
                                    <div x-show="!esNodoConectadoActual(nodoSelected)"
                                         class="aviso-offline rounded-lg px-3.5 py-2 text-xs mb-4">
                                        Este nodo está actualmente <b>desconectado</b>, pero puedes seguir editando y aplicando su configuración; queda guardada y retenida en el broker para cuando se vuelva a conectar.
                                    </div>

                                    <!-- SECCIÓN ROL PROPONER -->
                                    <template x-if="puedeProponer(nodoSelected)">
                                        <div class="mb-5">
                                            <div class="flex justify-between items-center mb-2">
                                                <div>
                                                    <h3 class="text-sm font-bold text-gray-700 uppercase tracking-wide"
                                                        x-text="tieneMultiplesActivadores(nodoSelected) ? 'Rol Proponer — Asignación de Tecla a Evento' : 'Rol Proponer — Evento a Publicar al Activarse'"></h3>
                                                    <p class="text-xs text-gray-500"
                                                       x-text="tieneMultiplesActivadores(nodoSelected)
                                                            ? 'Asigna una tecla (1 carácter) a un evento; al presionarla publicará en pipea/evento/[evento].'
                                                            : 'Este nodo es de activador único: indica el evento que publicará en pipea/evento/[evento] al activarse.'"></p>
                                                </div>
                                                <button x-show="tieneMultiplesActivadores(nodoSelected)"
                                                        @click="agregarFilaPublica()"
                                                        class="btn-verde text-xs font-bold px-3 py-1.5 rounded shadow-sm transition cursor-pointer">
                                                    + Agregar fila
                                                </button>
                                            </div>

                                            <div class="overflow-x-auto border rounded-lg max-h-[42vh] overflow-y-auto">
                                                <table class="min-w-full divide-y divide-gray-200 text-sm">
                                                    <thead class="bg-gray-100 text-gray-700 sticky top-0 z-10">
                                                        <tr>
                                                            <th x-show="tieneMultiplesActivadores(nodoSelected)"
                                                                class="px-3 py-2.5 text-left font-bold border-r w-28">Tecla (char)</th>
                                                            <th class="px-3 py-2.5 text-left font-bold border-r">Evento</th>
                                                            <th x-show="tieneMultiplesActivadores(nodoSelected)"
                                                                class="px-2 py-2.5 text-center font-bold w-14">Quitar</th>
                                                        </tr>
                                                    </thead>
                                                    <tbody class="divide-y divide-gray-200 bg-white">
                                                        <template x-for="(fila, idx) in nodoSelected.mapeos_actuales" :key="idx">
                                                            <tr class="hover:bg-gray-50">
                                                                <td x-show="tieneMultiplesActivadores(nodoSelected)" class="p-2 border-r">
                                                                    <input type="text"
                                                                           maxlength="1"
                                                                           x-model="fila.disparador"
                                                                           placeholder="A"
                                                                           class="border rounded px-2 py-1.5 text-sm bg-white w-20 text-center font-mono font-bold focus:outline-none focus:border-blue-500">
                                                                </td>

                                                                <td class="p-2 border-r">
                                                                    <input type="text"
                                                                           x-model="fila.evento"
                                                                           placeholder="Ej. encendida o soloGuitarra"
                                                                           style="width: 100%; box-sizing: border-box;"
                                                                           class="border rounded px-3 py-1.5 text-sm bg-white focus:outline-none focus:border-blue-500">
                                                                </td>

                                                                <td x-show="tieneMultiplesActivadores(nodoSelected)" class="p-2 text-center">
                                                                    <button @click="eliminarFilaPublica(idx)"
                                                                            class="text-red-600 hover:bg-red-50 px-2 py-1 rounded font-bold text-xs cursor-pointer"
                                                                            title="Eliminar fila">
                                                                        ✕
                                                                    </button>
                                                                </td>
                                                            </tr>
                                                        </template>
                                                    </tbody>
                                                </table>
                                            </div>
                                        </div>
                                    </template>

                                    <!-- SECCIÓN ROL REACCIONAR -->
                                    <template x-if="puedeReaccionar(nodoSelected)">
                                        <div>
                                            <div class="flex justify-between items-center mb-2">
                                                <div>
                                                    <h3 class="text-sm font-bold text-gray-700 uppercase tracking-wide">Rol Reaccionar — Eventos, Reacciones y Parámetros</h3>
                                                    <p class="text-xs text-gray-500">Selecciona un evento ya creado, define la reacción (opcional) y ajusta los parámetros del nodo.</p>
                                                </div>
                                                <button @click="agregarFilaReaccion()"
                                                        class="btn-verde text-xs font-bold px-3 py-1.5 rounded shadow-sm transition cursor-pointer">
                                                    + Agregar fila
                                                </button>
                                            </div>

                                            <div class="overflow-x-auto border rounded-lg max-h-[48vh] overflow-y-auto">
                                                <table class="min-w-full divide-y divide-gray-200 text-sm">
                                                    <thead class="bg-gray-100 text-gray-700 sticky top-0 z-10">
                                                        <tr>
                                                            <th class="px-3 py-2.5 text-left font-bold border-r">Evento</th>
                                                            <th class="px-3 py-2.5 text-left font-bold border-r">Reacción / Acción (opcional)</th>
                                                            <template x-for="param in (nodoSelected.parametros_disponibles || [])" :key="param.id">
                                                                <th class="px-3 py-2.5 text-left font-bold border-r">
                                                                    <span x-text="param.nombre"></span>
                                                                    <span class="block text-[10px] font-normal text-gray-500"
                                                                          x-text="param.tipo === 'int' ? ('Rango: ' + (param.min ?? 0) + ' a ' + (param.max ?? 255)) : 'Lista'"></span>
                                                                </th>
                                                            </template>
                                                            <th class="px-2 py-2.5 text-center font-bold w-14">Quitar</th>
                                                        </tr>
                                                    </thead>
                                                    <tbody class="divide-y divide-gray-200 bg-white">
                                                        <template x-for="(fila, idx) in nodoSelected.acciones_actuales" :key="idx">
                                                            <tr class="hover:bg-gray-50">
                                                                <td class="p-2 border-r">
                                                                    <select x-model="fila.evento"
                                                                            class="border rounded px-2.5 py-1.5 text-sm bg-white w-44 focus:outline-none focus:border-blue-500">
                                                                        <option value="">-- Seleccionar evento --</option>
                                                                        <template x-for="ev in obtenerEventosPropuestos()" :key="ev">
                                                                            <option :value="ev" x-text="ev"></option>
                                                                        </template>
                                                                        <template x-if="fila.evento && !obtenerEventosPropuestos().includes(fila.evento)">
                                                                            <option :value="fila.evento" x-text="fila.evento"></option>
                                                                        </template>
                                                                    </select>
                                                                </td>

                                                                <td class="p-2 border-r">
                                                                    <input type="text" x-model="fila.accion" placeholder="Opcional si coincide con evento..."
                                                                           class="border rounded px-2 py-1.5 text-sm w-48 focus:outline-none focus:border-blue-500">
                                                                </td>

                                                                <template x-for="param in (nodoSelected.parametros_disponibles || [])" :key="param.id">
                                                                    <td class="p-2 border-r">
                                                                        <template x-if="param.tipo === 'int'">
                                                                            <input type="number"
                                                                                   :min="param.min ?? 0"
                                                                                   :max="param.max ?? 255"
                                                                                   x-model.number="fila.parametros[param.id]"
                                                                                   class="border rounded px-2 py-1.5 text-sm w-28">
                                                                        </template>

                                                                        <template x-if="param.tipo === 'lista'">
                                                                            <select x-model="fila.parametros[param.id]"
                                                                                    class="border rounded px-2 py-1.5 text-sm bg-white w-40">
                                                                                <template x-for="op in (param.opciones || [])" :key="op">
                                                                                    <option :value="op" x-text="op"></option>
                                                                                </template>
                                                                            </select>
                                                                        </template>
                                                                    </td>
                                                                </template>

                                                                <td class="p-2 text-center">
                                                                    <button @click="eliminarFilaReaccion(idx)"
                                                                            class="text-red-600 hover:bg-red-50 px-2 py-1 rounded font-bold text-xs cursor-pointer"
                                                                            title="Eliminar fila">
                                                                        ✕
                                                                    </button>
                                                                </td>
                                                            </tr>
                                                        </template>
                                                    </tbody>
                                                </table>
                                            </div>
                                        </div>
                                    </template>
                                </div>

                                <div class="pt-3 border-t flex justify-end">
                                    <button @click="aplicarConfiguracion()"
                                            class="btn-azul px-6 py-2.5 rounded font-semibold shadow transition cursor-pointer">
                                        Aplicar Configuración
                                    </button>
                                </div>
                            </div>
                        </template>

                        <template x-if="!nodoSelected">
                            <div class="flex items-center justify-center h-72 text-gray-400 italic">
                                Selecciona un nodo en "Nodos Registrados" para configurar sus parámetros.
                            </div>
                        </template>
                    </div>

                    <!-- PESTAÑA 2: Personajes -->
                    <div x-show="pestanaActiva === 'personajes'" class="space-y-4" style="display: none;">
                        <div>
                            <h2 class="text-xl font-bold text-gray-800">Catálogo de Personajes</h2>
                            <p class="text-xs text-gray-500">
                                Crea personajes nuevos o edita descripciones. Todos los personajes quedan guardados en el catálogo.
                            </p>
                        </div>

                        <div class="bg-gray-50 p-4 rounded-lg border space-y-3 w-full">
                            <div class="w-full">
                                <label class="block text-xs font-bold text-gray-700 mb-1">Nombre del Personaje</label>
                                <input type="text"
                                       x-model="nuevoPersonaje.nombre"
                                       :title="nuevoPersonaje.nombre"
                                       placeholder="Ej. sofia"
                                       style="width: 100%; box-sizing: border-box;"
                                       class="border border-gray-300 rounded px-3 py-2 text-sm bg-white focus:outline-none focus:border-blue-500">
                            </div>
                            <div class="w-full">
                                <label class="block text-xs font-bold text-gray-700 mb-1">Descripción</label>
                                <textarea rows="2"
                                          x-model="nuevoPersonaje.descripcion"
                                          :title="nuevoPersonaje.descripcion"
                                          placeholder="Describe el rol, atmósfera o nodos que participan en este personaje..."
                                          style="width: 100%; box-sizing: border-box;"
                                          class="border border-gray-300 rounded px-3 py-2 text-sm bg-white focus:outline-none focus:border-blue-500"></textarea>
                            </div>
                            <div class="flex justify-end pt-1">
                                <button @click="guardarPersonaje()"
                                        class="btn-verde text-sm font-bold py-2 px-5 rounded shadow-sm transition cursor-pointer">
                                    + Guardar Personaje
                                </button>
                            </div>
                        </div>

                        <div class="overflow-x-auto border rounded-lg max-h-[50vh] overflow-y-auto w-full">
                            <table class="min-w-full divide-y divide-gray-200 text-sm">
                                <thead class="bg-gray-100 text-gray-700 sticky top-0">
                                    <tr>
                                        <th class="px-3 py-2 text-left font-bold border-r">Personaje</th>
                                        <th class="px-3 py-2 text-left font-bold border-r">Descripción</th>
                                        <th class="px-3 py-2 text-left font-bold border-r w-28">Origen</th>
                                        <th class="px-2 py-2 text-center font-bold w-24">Acción</th>
                                    </tr>
                                </thead>
                                <tbody class="divide-y divide-gray-200 bg-white">
                                    <template x-for="pers in personajes" :key="pers.nombre">
                                        <tr class="hover:bg-gray-50">
                                            <td class="px-3 py-2 border-r font-semibold text-gray-800 break-words" x-text="pers.nombre"></td>
                                            <td class="px-3 py-2 border-r text-gray-600 break-words" x-text="pers.descripcion || '—'"></td>
                                            <td class="px-3 py-2 border-r text-xs">
                                                <span class="px-2 py-0.5 rounded font-semibold"
                                                      :class="pers.origen === 'nodo' ? 'badge-proponen' : 'badge-reaccionan'"
                                                      x-text="pers.origen === 'nodo' ? 'Nodo' : 'Usuario'"></span>
                                            </td>
                                            <td class="px-2 py-2 text-center">
                                                <button x-show="pers.origen !== 'nodo'"
                                                        @click="eliminarPersonaje(pers.nombre)"
                                                        class="text-red-600 hover:bg-red-50 px-2 py-1 rounded text-xs font-bold cursor-pointer">
                                                    Eliminar
                                                </button>
                                                <span x-show="pers.origen === 'nodo'" class="text-xs text-gray-400">Fijo</span>
                                            </td>
                                        </tr>
                                    </template>
                                    <tr x-show="personajes.length === 0">
                                        <td colspan="4" class="px-4 py-6 text-center text-gray-400 italic">
                                            No hay personajes registrados todavía.
                                        </td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>

                    <!-- PESTAÑA 3: Nodo-Personaje -->
                    <div x-show="pestanaActiva === 'nodoPersonaje'" class="space-y-4" style="display: none;">
                        <div>
                            <h2 class="text-xl font-bold text-gray-800">Relación Nodo — Personaje</h2>
                            <p class="text-xs text-gray-500">
                                Los nodos con rol de reaccionar pertenecen a un personaje; los nodos que proponen (o con rol dual) pueden asociarse a varios.
                            </p>
                        </div>

                        <div class="overflow-x-auto border rounded-lg max-h-[54vh] overflow-y-auto w-full">
                            <table class="min-w-full divide-y divide-gray-200 text-sm">
                                <thead class="bg-gray-100 text-gray-700 sticky top-0 z-10">
                                    <tr>
                                        <th class="px-3 py-2.5 text-left font-bold border-r w-48">Nodo / Tipo</th>
                                        <th class="px-3 py-2.5 text-left font-bold border-r w-52">Personaje(s)</th>
                                        <th class="px-3 py-2.5 text-left font-bold border-r w-28">Rol</th>
                                        <th class="px-3 py-2.5 text-left font-bold">Comentarios</th>
                                    </tr>
                                </thead>
                                <tbody class="divide-y divide-gray-200 bg-white">
                                    <template x-for="fila in relacionesNodoPersonaje" :key="fila.node_id">
                                        <tr class="hover:bg-gray-50 align-top">
                                            <td class="px-3 py-2.5 border-r">
                                                <p class="font-bold text-gray-800" x-text="fila.nombre"></p>
                                                <p class="text-[11px] text-gray-400 font-mono" x-text="fila.node_id + ' · ' + fila.tipo"></p>
                                                <span class="block text-[10px] font-semibold mt-0.5"
                                                      :style="fila.conectado ? 'color: #059669;' : 'color: #64748b;'"
                                                      x-text="fila.conectado ? '● Conectado' : '○ Desconectado'"></span>
                                            </td>

                                            <td class="px-3 py-2.5 border-r">
                                                <template x-if="fila.rol === 'reacciona'">
                                                    <select x-model="fila.personajeUnico"
                                                            style="width: 100%; box-sizing: border-box;"
                                                            class="border border-gray-300 rounded px-2.5 py-1.5 text-xs bg-white focus:outline-none focus:border-blue-500">
                                                        <option value="">-- Sin personaje --</option>
                                                        <template x-for="pers in personajes" :key="pers.nombre">
                                                            <option :value="pers.nombre" x-text="pers.nombre"></option>
                                                        </template>
                                                    </select>
                                                </template>

                                                <template x-if="fila.rol !== 'reacciona'">
                                                    <div class="flex flex-col gap-1.5 max-h-32 overflow-y-auto pr-1">
                                                        <template x-for="pers in personajes" :key="pers.nombre">
                                                            <label class="flex items-center gap-2 text-xs bg-gray-50 border rounded px-2 py-1 cursor-pointer hover:bg-gray-100">
                                                                <input type="checkbox"
                                                                       :value="pers.nombre"
                                                                       x-model="fila.personajes"
                                                                       class="rounded border-gray-300">
                                                                <span x-text="pers.nombre"></span>
                                                            </label>
                                                        </template>
                                                        <span x-show="personajes.length === 0" class="text-xs text-gray-400 italic">
                                                            Crea personajes primero en Personajes.
                                                        </span>
                                                    </div>
                                                </template>
                                            </td>

                                            <td class="px-3 py-2.5 border-r text-xs">
                                                <span class="px-2 py-1 rounded font-semibold"
                                                      :class="fila.rol !== 'reacciona' ? 'badge-proponen' : 'badge-reaccionan'"
                                                      x-text="fila.rol === 'propone' ? 'Propone' : (fila.rol === 'ambos' ? 'Ambos' : 'Reacciona')"></span>
                                            </td>

                                            <td class="px-3 py-2.5">
                                                <textarea rows="2"
                                                          x-model="fila.comentarios"
                                                          :title="fila.comentarios"
                                                          placeholder="Notas del nodo para el montaje..."
                                                          style="width: 100%; box-sizing: border-box;"
                                                          class="border border-gray-300 rounded px-2.5 py-1.5 text-xs bg-white focus:outline-none focus:border-blue-500"></textarea>
                                            </td>
                                        </tr>
                                    </template>
                                    <tr x-show="relacionesNodoPersonaje.length === 0">
                                        <td colspan="4" class="px-4 py-6 text-center text-gray-400 italic">
                                            No hay nodos registrados todavía.
                                        </td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>

                        <div class="pt-2 border-t flex justify-end" x-show="relacionesNodoPersonaje.length > 0">
                            <button @click="guardarTodasRelaciones()"
                                    class="btn-teal px-6 py-2 rounded text-sm font-semibold shadow transition cursor-pointer">
                                Guardar Relaciones
                            </button>
                        </div>
                    </div>
                </div>
            </section>
        </main>

        <!-- PRUEBA DE EVENTOS Y MONITOR MQTT -->
        <section class="max-w-7xl w-full mx-auto px-6 pb-8 space-y-4">
            <div class="panel-prueba-evento p-4 rounded-lg shadow flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                <div>
                    <h3 class="text-sm font-bold text-gray-800 uppercase tracking-wide">
                        Prueba de Eventos (Pre-presentación)
                    </h3>
                    <p class="text-xs text-gray-600">
                        Publica un evento en <code class="font-mono">pipea/evento/[evento]</code> para verificar cómo reaccionan los nodos configurados antes de la función.
                    </p>
                </div>
                <div class="flex flex-wrap items-center gap-2">
                    <select x-model="eventoPrueba"
                            class="border border-gray-300 rounded px-3 py-1.5 text-sm bg-white focus:outline-none focus:border-blue-500">
                        <option value="">-- Seleccionar evento --</option>
                        <template x-for="ev in obtenerTodosLosEventos()" :key="ev">
                            <option :value="ev" x-text="ev"></option>
                        </template>
                    </select>
                    <input type="text"
                           x-model="eventoPrueba"
                           placeholder="O escribe un evento..."
                           class="border border-gray-300 rounded px-3 py-1.5 text-sm bg-white w-44 focus:outline-none focus:border-blue-500">
                    <button @click="emitirEventoPrueba()"
                            class="btn-teal px-4 py-1.5 rounded text-sm font-semibold shadow transition cursor-pointer">
                        Emitir Evento
                    </button>
                </div>
            </div>

            <div class="monitor-mqtt p-4 rounded-lg shadow">
                <div class="flex justify-between items-center border-b pb-2 mb-2" style="border-color: #334155;">
                    <span class="text-xs font-bold uppercase tracking-wider" style="color: #34d399;">
                        Monitor MQTT — Última Configuración o Evento
                    </span>
                    <span class="text-xs font-mono" style="color: #94a3b8;"
                          x-text="ultimoConfig?.topico ? (ultimoConfig.topico + ' (' + ultimoConfig.timestamp + ')') : 'Sin mensajes aún'">
                    </span>
                </div>
                <pre class="text-xs font-mono overflow-x-auto max-h-56 whitespace-pre-wrap"
                     style="color: #e2e8f0;"
                     x-text="ultimoConfig?.payload ? JSON.stringify(ultimoConfig.payload, null, 2) : 'Pulsa Aplicar Configuración o Emitir Evento para ver el JSON publicado.'"></pre>
            </div>
        </section>

        <!-- MODAL DE AYUDA (INFORMACIÓN GENERAL + GUÍA DE USO) -->
        <div x-show="showInfo" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50" style="display: none;">
            <div class="bg-white rounded-lg max-w-2xl w-full p-6 shadow-xl max-h-[85vh] overflow-y-auto space-y-5">
                <div class="flex justify-between items-center border-b pb-3">
                    <h3 class="text-xl font-bold text-gray-800">Información General y Guía de Uso — PIPEA</h3>
                    <button @click="showInfo = false" class="text-gray-400 hover:text-gray-700 font-bold text-lg cursor-pointer">✕</button>
                </div>

                <div class="space-y-2">
                    <h4 class="text-sm font-bold text-indigo-900 uppercase tracking-wide">Información General</h4>
                    <p class="text-sm text-gray-600 leading-relaxed">
                        <b>PIPEA</b> es una herramienta web local (FastAPI + MQTT) para configurar dinámicamente los nodos de la plataforma de expresiones artísticas sin editar el código base de cada nodo cada vez que cambia el montaje.
                    </p>
                    <ul class="text-sm text-gray-600 space-y-1.5 list-disc pl-5">
                        <li><b>Tipo vs. Rol:</b> El <i>tipo</i> indica la clase de dispositivo (por ejemplo: <code>teclado</code>, <code>pulsador</code>, <code>luminaria_dmx</code>, <code>sofiea</code>); el <i>rol</i> indica su comportamiento MQTT (<code>propone</code>, <code>reacciona</code> o <code>ambos</code>).</li>
                        <li><b>Configuración sin conexión y retención:</b> Una vez registrado un nodo, puedes seguir editando y aplicando su configuración aunque esté desconectado. El mensaje queda guardado en disco y retenido en el broker (<code>pipea/config/[nombre_nodo]</code>) para entregarse al reconectarse.</li>
                    </ul>
                </div>

                <div class="space-y-2 border-t pt-4">
                    <h4 class="text-sm font-bold text-teal-800 uppercase tracking-wide">Guía Rápida de Uso</h4>
                    <ol class="text-sm text-gray-600 space-y-2 list-decimal pl-5">
                        <li><b>Revisa los nodos registrados:</b> En el panel izquierdo aparecen los nodos que proponen y los que reaccionan, con su estado (<code>● Conectado</code> o <code>○ Desconectado</code>).</li>
                        <li><b>Configura nodos que proponen:</b> Selecciona un nodo con rol <i>Propone</i> y asigna el evento (y tecla si tiene múltiples activadores) que se publicará en <code>pipea/evento/[evento]</code>.</li>
                        <li><b>Configura nodos que reaccionan:</b> Selecciona un nodo con rol <i>Reacciona</i>, elige un evento ya creado, define su reacción (opcional) y ajusta sus parámetros y rangos.</li>
                        <li><b>Aplica la configuración:</b> Haz clic en <b>Aplicar Configuración</b> para guardar localmente y publicar en el tópico de configuración del nodo.</li>
                        <li><b>Prueba antes de escena:</b> Usa <b>Prueba de Eventos</b> para emitir un evento y revisar en el <b>Monitor MQTT</b> la última publicación.</li>
                        <li><b>Reiniciar en limpio:</b> Usa <b>Borrar configuración</b> solo cuando quieras limpiar los datos guardados y los mensajes retenidos en el broker.</li>
                    </ol>
                </div>

                <div class="flex justify-end border-t pt-3">
                    <button @click="showInfo = false" class="btn-azul px-5 py-2 rounded text-sm font-semibold cursor-pointer">
                        Entendido
                    </button>
                </div>
            </div>
        </div>

        <!-- LÓGICA DE INTERFAZ EN JAVASCRIPT (Alpine.js) -->
        <script>
            function appData() {
                return {
                    nodos: [],
                    nodoSelected: null,
                    ultimoConfig: null,
                    showInfo: false,
                    pestanaActiva: 'nodo',
                    personajes: [],
                    nuevoPersonaje: { nombre: '', descripcion: '' },
                    relacionesNodoPersonaje: [],
                    eventoPrueba: '',

                    async init() {
                        await this.cargarPersonajes();
                        await this.cargarNodos();
                        const ordenados = this.nodosOrdenados();
                        if (ordenados.length > 0 && !this.nodoSelected) {
                            this.seleccionarNodo(ordenados[0]);
                        }
                        if (!this.eventoPrueba && this.obtenerTodosLosEventos().length > 0) {
                            this.eventoPrueba = this.obtenerTodosLosEventos()[0];
                        }
                        setInterval(() => {
                            this.cargarNodos();
                            if (this.pestanaActiva === 'personajes') {
                                this.cargarPersonajes();
                            }
                        }, 4000);
                    },

                    rolDeNodo(nodo) {
                        if (!nodo) return 'reacciona';
                        const r = String(nodo.rol || '').toLowerCase();
                        if (r === 'propone' || r === 'publica') return 'propone';
                        if (r === 'reacciona') return 'reacciona';
                        if (r === 'ambos' || r === 'dual') return 'ambos';
                        const t = String(nodo.tipo || '').toLowerCase();
                        if (t === 'publica' || t === 'propone') return 'propone';
                        if (t === 'ambos' || t === 'dual') return 'ambos';
                        return 'reacciona';
                    },

                    textoRol(nodo) {
                        const r = this.rolDeNodo(nodo);
                        if (r === 'propone') return 'Propone';
                        if (r === 'ambos') return 'Propone y Reacciona';
                        return 'Reacciona';
                    },

                    puedeProponer(nodo) {
                        const r = this.rolDeNodo(nodo);
                        return r === 'propone' || r === 'ambos';
                    },

                    puedeReaccionar(nodo) {
                        const r = this.rolDeNodo(nodo);
                        return r === 'reacciona' || r === 'ambos';
                    },

                    nodosConectados() {
                        return (this.nodos || []).filter(n => Boolean(n.conectado));
                    },

                    esNodoConectadoActual(nodo) {
                        if (!nodo) return false;
                        const fresco = (this.nodos || []).find(n => n.node_id === nodo.node_id);
                        return fresco ? Boolean(fresco.conectado) : Boolean(nodo.conectado);
                    },

                    nodosProponen() {
                        return (this.nodos || []).filter(n => this.puedeProponer(n));
                    },

                    nodosReaccionan() {
                        return (this.nodos || []).filter(n => !this.puedeProponer(n) && this.puedeReaccionar(n));
                    },

                    nodosOrdenados() {
                        return [...this.nodosProponen(), ...this.nodosReaccionan()];
                    },

                    tieneMultiplesActivadores(nodo) {
                        if (!nodo) return true;
                        if (typeof nodo.multiples_activadores === 'boolean') {
                            return nodo.multiples_activadores;
                        }
                        if (typeof nodo.activador_unico === 'boolean') {
                            return !nodo.activador_unico;
                        }
                        const txt = `${nodo.node_id || ''} ${nodo.nombre || ''} ${nodo.tipo || ''}`.toLowerCase();
                        if (['boton', 'pulsador', 'sensor', 'switch', 'pir', 'ultrasonido'].some(k => txt.includes(k))) {
                            return false;
                        }
                        return true;
                    },

                    prepararRelacionesUI() {
                        const existentesPorId = {};
                        (this.relacionesNodoPersonaje || []).forEach(r => {
                            existentesPorId[r.node_id] = r;
                        });

                        this.relacionesNodoPersonaje = this.nodosOrdenados().map(n => {
                            const previo = existentesPorId[n.node_id];
                            const listaPers = previo ? [...(previo.personajes || [])] : [...(n.personajes || [])];
                            const persUnico = previo
                                ? (previo.personajeUnico || '')
                                : (listaPers[0] || '');

                            return {
                                node_id: n.node_id,
                                nombre: n.nombre,
                                tipo: n.tipo || 'nodo',
                                rol: this.rolDeNodo(n),
                                conectado: Boolean(n.conectado),
                                personajeUnico: persUnico,
                                personajes: listaPers,
                                comentarios: previo ? (previo.comentarios || '') : (n.comentarios || '')
                            };
                        });
                    },

                    async cargarNodos() {
                        let res = await fetch('/api/nodos');
                        this.nodos = await res.json();

                        if (this.nodoSelected) {
                            const sigueRegistrado = this.nodos.find(
                                n => n.node_id === this.nodoSelected.node_id
                            );
                            if (!sigueRegistrado) {
                                this.nodoSelected = null;
                            } else {
                                this.nodoSelected.conectado = Boolean(sigueRegistrado.conectado);
                            }
                        }

                        if (this.pestanaActiva === 'nodoPersonaje') {
                            this.prepararRelacionesUI();
                        }

                        let rCfg = await fetch('/api/ultimo-config');
                        this.ultimoConfig = await rCfg.json();
                    },

                    async cargarPersonajes() {
                        let res = await fetch('/api/personajes');
                        this.personajes = await res.json();
                    },

                    async guardarPersonaje() {
                        const nombre = (this.nuevoPersonaje.nombre || '').trim();
                        const descripcion = (this.nuevoPersonaje.descripcion || '').trim();
                        if (!nombre) {
                            alert('Escribe un nombre para el personaje.');
                            return;
                        }
                        const res = await fetch('/api/personajes', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ nombre, descripcion })
                        });
                        if (!res.ok) {
                            const err = await res.json();
                            alert(err.detail || 'No se pudo guardar el personaje.');
                            return;
                        }
                        this.nuevoPersonaje = { nombre: '', descripcion: '' };
                        await this.cargarPersonajes();
                    },

                    async eliminarPersonaje(nombre) {
                        const res = await fetch(`/api/personajes/${encodeURIComponent(nombre)}`, {
                            method: 'DELETE'
                        });
                        if (!res.ok) {
                            const err = await res.json();
                            alert(err.detail || 'No se pudo eliminar el personaje.');
                            return;
                        }
                        await this.cargarPersonajes();
                        await this.cargarNodos();
                    },

                    async borrarTodaConfiguracion() {
                        const seguro = confirm(
                            '¿Borrar toda la configuración guardada de nodos, relaciones y personajes para trabajar en limpio?'
                        );
                        if (!seguro) return;

                        const res = await fetch('/api/reiniciar-configuracion', {
                            method: 'POST'
                        });
                        if (!res.ok) {
                            alert('No se pudo borrar la configuración.');
                            return;
                        }
                        this.nodoSelected = null;
                        this.relacionesNodoPersonaje = [];
                        this.personajes = [];
                        this.eventoPrueba = '';
                        await this.cargarNodos();
                        await this.cargarPersonajes();
                        alert('Configuración borrada. Listo para trabajar en limpio.');
                    },

                    async guardarTodasRelaciones() {
                        const payloadRelaciones = this.relacionesNodoPersonaje.map(fila => {
                            const persFinal = fila.rol === 'reacciona'
                                ? (fila.personajeUnico ? [fila.personajeUnico] : [])
                                : (fila.personajes || []);
                            return {
                                node_id: fila.node_id,
                                personajes: persFinal,
                                comentarios: fila.comentarios || ''
                            };
                        });

                        const res = await fetch('/api/relaciones-nodo-personaje', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ relaciones: payloadRelaciones })
                        });
                        if (!res.ok) {
                            const err = await res.json();
                            alert(err.detail || 'No se pudieron guardar las relaciones.');
                            return;
                        }
                        await this.cargarNodos();
                        this.prepararRelacionesUI();
                        alert('¡Relaciones Nodo-Personaje guardadas!');
                    },

                    obtenerEventosPropuestos() {
                        const eventos = new Set();
                        (this.nodos || []).forEach(n => {
                            if (this.puedeProponer(n)) {
                                (n.mapeos_actuales || []).forEach(m => {
                                    const ev = (m.evento || '').trim();
                                    if (ev) eventos.add(ev);
                                });
                            }
                        });
                        return Array.from(eventos);
                    },

                    obtenerTodosLosEventos() {
                        const eventos = new Set(this.obtenerEventosPropuestos());
                        (this.nodos || []).forEach(n => {
                            if (this.puedeReaccionar(n)) {
                                (n.acciones_actuales || []).forEach(a => {
                                    const ev = (a.evento || '').trim();
                                    if (ev) eventos.add(ev);
                                });
                            }
                        });
                        return Array.from(eventos);
                    },

                    async emitirEventoPrueba() {
                        const ev = (this.eventoPrueba || '').trim();
                        if (!ev) {
                            alert('Selecciona o escribe un evento para probar.');
                            return;
                        }
                        const res = await fetch('/api/probar-evento', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ evento: ev })
                        });
                        if (!res.ok) {
                            const err = await res.json();
                            alert(err.detail || 'No se pudo emitir el evento de prueba.');
                            return;
                        }
                        const data = await res.json();
                        this.ultimoConfig = {
                            topico: data.topico_publicado,
                            payload: data.payload,
                            timestamp: new Date().toLocaleTimeString('es-CR', { hour12: false })
                        };
                    },

                    prepararCopiaNodo(nodo) {
                        const copia = JSON.parse(JSON.stringify(nodo));
                        copia.rol = this.rolDeNodo(copia);
                        if (this.puedeReaccionar(copia)) {
                            copia.acciones_actuales = (copia.acciones_actuales || []).map(acc => ({
                                ...acc,
                                evento: (acc.evento || '').trim(),
                                accion: acc.accion || '',
                                parametros: acc.parametros || {}
                            }));
                        }
                        if (this.puedeProponer(copia)) {
                            const multi = this.tieneMultiplesActivadores(copia);
                            copia.multiples_activadores = multi;
                            let mapeos = (copia.mapeos_actuales || []).map(m => ({
                                disparador: multi ? (m.disparador || '').slice(0, 1) : '',
                                evento: (m.evento || '').trim()
                            }));
                            if (!multi) {
                                mapeos = mapeos.length > 0 ? [mapeos[0]] : [{ disparador: '', evento: '' }];
                            }
                            copia.mapeos_actuales = mapeos;
                        }
                        return copia;
                    },

                    seleccionarNodo(nodo) {
                        const fresco = this.nodos.find(n => n.node_id === nodo.node_id) || nodo;
                        this.nodoSelected = this.prepararCopiaNodo(fresco);
                    },

                    agregarFilaReaccion() {
                        const paramsObj = {};
                        (this.nodoSelected.parametros_disponibles || []).forEach(p => {
                            if (p.tipo === 'int') {
                                paramsObj[p.id] = p.min ?? 0;
                            } else if (p.tipo === 'lista') {
                                paramsObj[p.id] = (p.opciones && p.opciones[0]) || '';
                            }
                        });
                        if (!this.nodoSelected.acciones_actuales) {
                            this.nodoSelected.acciones_actuales = [];
                        }
                        const primerEvento = this.obtenerEventosPropuestos()[0] || '';
                        this.nodoSelected.acciones_actuales.push({
                            evento: primerEvento,
                            accion: '',
                            parametros: paramsObj
                        });
                    },

                    eliminarFilaReaccion(index) {
                        this.nodoSelected.acciones_actuales.splice(index, 1);
                    },

                    agregarFilaPublica() {
                        if (!this.tieneMultiplesActivadores(this.nodoSelected)) return;
                        if (!this.nodoSelected.mapeos_actuales) {
                            this.nodoSelected.mapeos_actuales = [];
                        }
                        this.nodoSelected.mapeos_actuales.push({
                            disparador: '',
                            evento: ''
                        });
                    },

                    eliminarFilaPublica(index) {
                        if (!this.tieneMultiplesActivadores(this.nodoSelected)) return;
                        this.nodoSelected.mapeos_actuales.splice(index, 1);
                    },

                    async aplicarConfiguracion() {
                        let res = await fetch(`/api/configurar/${this.nodoSelected.node_id}`, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify(this.nodoSelected)
                        });
                        let data = await res.json();
                        this.ultimoConfig = {
                            topico: data.topico_publicado,
                            payload: data.payload,
                            timestamp: new Date().toLocaleTimeString('es-CR', { hour12: false })
                        };
                        await this.cargarNodos();
                        this.seleccionarNodo(this.nodoSelected);
                        alert("¡Configuración guardada y publicada (retenida) en " + data.topico_publicado + "!");
                    }
                }
            }
        </script>
    </body>
    </html>
    """


def _abrir_navegador():
    time.sleep(1.5)
    webbrowser.open("http://127.0.0.1:8000")


if __name__ == "__main__":
    threading.Thread(target=_abrir_navegador, daemon=True).start()
    try:
        uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
    except KeyboardInterrupt:
        print("\nCerrando servidor PIPEA...")
    finally:
        try:
            mqtt_client.loop_stop()
            mqtt_client.disconnect()
        except Exception:
            pass
        os._exit(0)
