# ==============================================================================
# PIPEA - Servidor Backend (FastAPI + MQTT) e Interfaz Web (Modo Normal y Dramaturgia)
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
personajes_catalogo = {}
relaciones_dramaturgia = {}
pies_dramaturgia = []

historial_mqtt = []  # Hasta los últimos 10 mensajes enviados/recibidos

def registrar_en_historial_mqtt(topico: str, payload):
    global historial_mqtt
    item = {
        "topico": topico,
        "payload": payload,
        "timestamp": datetime.now().strftime("%H:%M:%S")
    }
    historial_mqtt.insert(0, item)
    historial_mqtt = historial_mqtt[:10]


def normalizar_rol(ndata: dict) -> str:
    """Determina el rol del nodo ('propone', 'reacciona' o 'ambos')."""
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


def normalizar_tipo_dispositivo(ndata: dict) -> str:
    """Determina el tipo físico/lógico del nodo ('teclado', 'pulsador', 'luminaria_dmx', 'sofiea', etc.)."""
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
    """Determina si un nodo proponente tiene múltiples activadores (teclado) o único (pulsador)."""
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
    """Devuelve pipea/config/[nombre_nodo]."""
    nombre = str(ndata.get("nombre") or ndata.get("node_id") or "nodo").strip()
    return f"pipea/config/{nombre}"


def normalizar_estructura_nodo(ndata: dict) -> dict:
    """Normaliza los campos base de cada nodo registrado."""
    rol = normalizar_rol(ndata)
    ndata["rol"] = rol
    ndata["tipo"] = normalizar_tipo_dispositivo(ndata)

    if not isinstance(ndata.get("personajes"), list):
        ndata["personajes"] = []

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
    """Actualiza 'conectado' sin ocultar nodos previamente registrados."""
    ahora = time.time()
    for ndata in nodos_registrados.values():
        normalizar_estructura_nodo(ndata)
        ultimo = ndata.get("ultimo_visto")
        ndata["conectado"] = bool(ultimo is not None and (ahora - ultimo) <= TIMEOUT_CONEXION_SEG)


def registrar_personajes_de_nodo(lista_pers):
    """Agrega personajes reportados por un nodo al catálogo de Dramaturgia si aún no existen."""
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
# Carga inicial de estado persistente (separando Modo Normal y Modo Dramaturgia)
# ------------------------------------------------------------------------------
if os.path.exists(ARCHIVO_ESTADO):
    try:
        with open(ARCHIVO_ESTADO, "r", encoding="utf-8") as f:
            data_guardada = json.load(f)

            bloque_normal = data_guardada.get("modo_normal", data_guardada)
            nodos_cargados = bloque_normal.get("nodos", {})
            for nid, ndata in nodos_cargados.items():
                ndata["conectado"] = False
                ndata["ultimo_visto"] = None
                normalizar_estructura_nodo(ndata)
            nodos_registrados = nodos_cargados
            nodos_configurados_manualmente = set(bloque_normal.get("configurados", []))

            bloque_dram = data_guardada.get("modo_dramaturgia", {})
            pers_guardados = bloque_dram.get("personajes", data_guardada.get("personajes", {}))
            if isinstance(pers_guardados, dict):
                for pname, pdata in pers_guardados.items():
                    if isinstance(pdata, dict):
                        personajes_catalogo[pname] = {
                            "nombre": pdata.get("nombre", pname),
                            "descripcion": pdata.get("descripcion", ""),
                            "origen": pdata.get("origen", "usuario"),
                        }

            rel_guardadas = bloque_dram.get("relaciones_nodo_personaje", {})
            if isinstance(rel_guardadas, dict):
                relaciones_dramaturgia = rel_guardadas
            else:
                for nid, ndata in nodos_registrados.items():
                    if ndata.get("personajes") or ndata.get("comentarios"):
                        relaciones_dramaturgia[nid] = {
                            "personajes": list(ndata.get("personajes", [])),
                            "comentarios": str(ndata.get("comentarios", "") or ""),
                        }

            pies_guardados = bloque_dram.get("pies", [])
            if isinstance(pies_guardados, list):
                pies_dramaturgia = pies_guardados
    except Exception as e:
        print("No se pudo cargar estado previo:", e)


def guardar_estado():
    """Guarda en estado_nodos.json manteniendo separados Modo Normal y Modo Dramaturgia."""
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
                    "modo_normal": {
                        "nodos": nodos_a_guardar,
                        "configurados": list(nodos_configurados_manualmente),
                    },
                    "modo_dramaturgia": {
                        "personajes": personajes_catalogo,
                        "relaciones_nodo_personaje": relaciones_dramaturgia,
                        "pies": pies_dramaturgia,
                    },
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
    print("Conectado al broker MQTT con código:", rc)
    client.subscribe("pipea/registro/+")
    client.subscribe("pipea/config/+")
    client.subscribe("pipea/config/nodo/#")
    for ndata in nodos_registrados.values():
        client.subscribe(topico_config_de_nodo(ndata))


def on_message(client, userdata, msg):
    try:
        texto_raw = msg.payload.decode().strip()
        if not texto_raw:
            return
        payload = json.loads(texto_raw)

        if msg.topic.startswith("pipea/config/"):
            print(f"[MQTT RX CONFIG] {msg.topic} -> {json.dumps(payload, ensure_ascii=False)}")
            return

        node_id = payload.get("node_id")
        if not node_id:
            return

        if node_id in nodos_registrados and node_id in nodos_configurados_manualmente:
            existente = nodos_registrados[node_id]
            for clave in ["nombre", "rol", "tipo", "parametros_disponibles", "disparadores_disponibles", "multiples_activadores", "activador_unico", "personajes"]:
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

        if node_id not in relaciones_dramaturgia:
            pers_iniciales = list(payload.get("personajes") or [])
            if normalizar_rol(payload) == "reacciona" and len(pers_iniciales) > 1:
                pers_iniciales = [pers_iniciales[0]]
            relaciones_dramaturgia[node_id] = {
                "personajes": pers_iniciales,
                "comentarios": "",
            }

        mqtt_client.subscribe(topico_config_de_nodo(nodos_registrados[node_id]))
        registrar_personajes_de_nodo(payload.get("personajes"))
        guardar_estado()
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
# Endpoints Comunes y de Modo Normal
# ------------------------------------------------------------------------------
@app.get("/api/nodos")
def obtener_nodos():
    refrescar_estados_conexion()
    return list(nodos_registrados.values())


@app.get("/api/historial-mqtt")
def obtener_historial_mqtt():
    return historial_mqtt


@app.post("/api/configurar/{node_id}")
def configurar_nodo_normal(node_id: str, data: dict):
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
    print(f"\n[MQTT OUT NORMAL RETAIN] Tópico: {topico}\n{payload_json}\n")
    mqtt_client.publish(topico, payload_json, retain=True)

    registrar_en_historial_mqtt(topico, payload_config)

    return {"status": "success", "topico_publicado": topico, "payload": payload_config}


@app.post("/api/probar-evento")
def probar_evento(data: dict):
    evento = str(data.get("evento") or "").strip()
    if not evento:
        raise HTTPException(status_code=400, detail="Debes indicar el nombre del evento a probar.")

    topico = f"pipea/evento/{evento}"
    payload_evento = {"evento": evento}
    payload_json = json.dumps(payload_evento, ensure_ascii=False)
    print(f"\n[MQTT TEST EVENTO] Tópico: {topico}\n{payload_json}\n")
    mqtt_client.publish(topico, payload_json)

    registrar_en_historial_mqtt(topico, payload_evento)

    return {"status": "ok", "topico_publicado": topico, "payload": payload_evento}


@app.post("/api/reiniciar-normal")
def reiniciar_modo_normal():
    global nodos_registrados, nodos_configurados_manualmente, historial_mqtt

    for ndata in nodos_registrados.values():
        try:
            mqtt_client.publish(topico_config_de_nodo(ndata), "", retain=True)
        except Exception:
            pass

    nodos_registrados = {}
    nodos_configurados_manualmente = set()
    historial_mqtt = []
    guardar_estado()
    return {"status": "reiniciado_normal"}


# ------------------------------------------------------------------------------
# Endpoints Exclusivos de Modo Dramaturgia
# ------------------------------------------------------------------------------
@app.get("/api/dramaturgia/estado")
def obtener_estado_dramaturgia():
    refrescar_estados_conexion()
    return {
        "personajes": list(personajes_catalogo.values()),
        "relaciones": relaciones_dramaturgia,
        "pies": pies_dramaturgia,
    }


@app.post("/api/dramaturgia/personajes")
def guardar_personaje_dramaturgia(data: dict):
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


@app.delete("/api/dramaturgia/personajes/{nombre}")
def eliminar_personaje_dramaturgia(nombre: str):
    nombre_limpio = nombre.strip()
    if nombre_limpio not in personajes_catalogo:
        raise HTTPException(status_code=404, detail="Personaje no encontrado.")
    if personajes_catalogo[nombre_limpio].get("origen", "usuario") == "nodo":
        raise HTTPException(status_code=400, detail="No se puede eliminar un personaje definido por un nodo.")

    del personajes_catalogo[nombre_limpio]
    for nid, rel in relaciones_dramaturgia.items():
        pers_list = rel.get("personajes", [])
        if nombre_limpio in pers_list:
            rel["personajes"] = [p for p in pers_list if p != nombre_limpio]

    guardar_estado()
    return {"status": "eliminado", "nombre": nombre_limpio}


@app.post("/api/dramaturgia/relaciones")
def guardar_relaciones_dramaturgia(data: dict):
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
        pers_recibidos = item.get("personajes", [])
        if not isinstance(pers_recibidos, list):
            pers_recibidos = []

        pers_limpios = []
        for p in pers_recibidos:
            if isinstance(p, str):
                nombre_p = p.strip()
                if nombre_p and nombre_p in personajes_catalogo and nombre_p not in pers_limpios:
                    pers_limpios.append(nombre_p)

        if nodo_actual.get("rol") == "reacciona" and len(pers_limpios) > 1:
            pers_limpios = [pers_limpios[0]]

        relaciones_dramaturgia[node_id] = {
            "personajes": pers_limpios,
            "comentarios": str(item.get("comentarios", "") or "").strip(),
        }

    guardar_estado()
    return {"status": "success"}


def validar_pies_dramaturgia(pies_lista: list, nodo_objetivo: str = None):
    """
    Valida reglas en la matriz de Puesta en escena:
    1) No puede haber dos Pies con el mismo nombre de evento.
    2) Para un mismo nodo proponente con múltiples activadores, no puede repetirse la misma tecla (char).
    """
    eventos_vistos = {}
    teclas_por_nodo = {}

    for idx, p in enumerate(pies_lista):
        if not isinstance(p, dict):
            continue
        etiqueta_pie = str(p.get("pie") or f"Pie #{idx + 1}").strip()
        ev = str(p.get("evento") or "").strip()

        if ev:
            ev_key = ev.lower()
            if ev_key in eventos_vistos:
                raise HTTPException(
                    status_code=400,
                    detail=f"Evento repetido: '{ev}' ya fue usado en '{eventos_vistos[ev_key]}' y en '{etiqueta_pie}'. Cada pie debe tener un evento distinto."
                )
            eventos_vistos[ev_key] = etiqueta_pie

        proponentes = p.get("proponentes", [])
        if isinstance(proponentes, list):
            for prop in proponentes:
                if not isinstance(prop, dict) or not prop.get("seleccionado"):
                    continue
                nid = str(prop.get("node_id") or "").strip()
                if not nid or nid not in nodos_registrados:
                    continue
                nodo_meta = nodos_registrados[nid]
                if inferir_multiples_activadores(nodo_meta):
                    tecla = str(prop.get("disparador") or "").strip()[:1]
                    if tecla:
                        teclas_por_nodo.setdefault(nid, {})
                        if tecla in teclas_por_nodo[nid]:
                            raise HTTPException(
                                status_code=400,
                                detail=f"Advertencia: la tecla '{tecla}' está repetida para '{nodo_meta.get('nombre', nid)}' entre '{teclas_por_nodo[nid][tecla]}' y '{etiqueta_pie}'."
                            )
                        teclas_por_nodo[nid][tecla] = etiqueta_pie


def construir_payloads_desde_pies(pies_lista: list) -> dict:
    """Consolida por node_id la configuración escénica completa a partir de la lista de Pies."""
    configs_por_nodo = {}

    for p in pies_lista:
        if not isinstance(p, dict):
            continue
        ev = str(p.get("evento") or "").strip()
        if not ev:
            continue

        for prop in p.get("proponentes", []):
            if not isinstance(prop, dict) or not prop.get("seleccionado"):
                continue
            nid = str(prop.get("node_id") or "").strip()
            if nid not in nodos_registrados:
                continue
            nodo_meta = nodos_registrados[nid]
            multi = inferir_multiples_activadores(nodo_meta)
            entry = configs_por_nodo.setdefault(nid, {
                "node_id": nid,
                "nombre": nodo_meta.get("nombre"),
                "rol": nodo_meta.get("rol"),
                "tipo": nodo_meta.get("tipo"),
                "multiples_activadores": multi,
                "mapeos_actuales": [],
                "acciones_actuales": [],
            })
            disp = "" if not multi else str(prop.get("disparador") or "").strip()[:1]
            entry["mapeos_actuales"].append({
                "disparador": disp,
                "evento": ev,
                "topico_evento": f"pipea/evento/{ev}",
            })

        for reac in p.get("reactivos", []):
            if not isinstance(reac, dict) or not reac.get("seleccionado"):
                continue
            nid = str(reac.get("node_id") or "").strip()
            if nid not in nodos_registrados:
                continue
            nodo_meta = nodos_registrados[nid]
            multi = inferir_multiples_activadores(nodo_meta)
            entry = configs_por_nodo.setdefault(nid, {
                "node_id": nid,
                "nombre": nodo_meta.get("nombre"),
                "rol": nodo_meta.get("rol"),
                "tipo": nodo_meta.get("tipo"),
                "multiples_activadores": multi,
                "mapeos_actuales": [],
                "acciones_actuales": [],
            })
            accion_txt = str(reac.get("accion") or "").strip()
            params = reac.get("parametros", {}) if isinstance(reac.get("parametros"), dict) else {}
            entry["acciones_actuales"].append({
                "evento": ev,
                "topico_evento": f"pipea/evento/{ev}",
                "accion": accion_txt,
                "parametros": params,
            })

    resultado_limpio = {}
    for nid, cfg in configs_por_nodo.items():
        nodo_meta = nodos_registrados[nid]
        if not nodo_puede_proponer(nodo_meta):
            cfg.pop("mapeos_actuales", None)
        if not nodo_puede_reaccionar(nodo_meta):
            cfg.pop("acciones_actuales", None)
        resultado_limpio[nid] = cfg

    return resultado_limpio


@app.post("/api/dramaturgia/pies/guardar")
def guardar_pies_dramaturgia(data: dict):
    global pies_dramaturgia
    pies = data.get("pies", [])
    if not isinstance(pies, list):
        raise HTTPException(status_code=400, detail="Formato inválido de Pies.")
    pies_dramaturgia = pies
    guardar_estado()
    return {"status": "guardado"}


@app.post("/api/dramaturgia/aplicar-escenica")
def aplicar_configuracion_escenica(data: dict):
    global pies_dramaturgia
    pies = data.get("pies", [])
    if not isinstance(pies, list):
        raise HTTPException(status_code=400, detail="Formato inválido de Pies.")

    validar_pies_dramaturgia(pies)
    pies_dramaturgia = pies
    guardar_estado()

    payloads = construir_payloads_desde_pies(pies)
    if not payloads:
        raise HTTPException(status_code=400, detail="No hay nodos seleccionados con evento válido en la matriz de puesta en escena.")

    publicados = []
    for nid, payload_cfg in payloads.items():
        nodo_meta = nodos_registrados[nid]
        topico = topico_config_de_nodo(nodo_meta)
        payload_json = json.dumps(payload_cfg, indent=2, ensure_ascii=False)
        print(f"\n[MQTT OUT DRAMATURGIA ESCÉNICA RETAIN] Tópico: {topico}\n{payload_json}\n")
        mqtt_client.publish(topico, payload_json, retain=True)
        publicados.append(topico)
        registrar_en_historial_mqtt(topico, payload_cfg)

    return {"status": "success", "topicos_publicados": publicados, "total_nodos": len(publicados)}


@app.post("/api/dramaturgia/aplicar-nodo/{node_id}")
def aplicar_config_nodo_dramaturgia(node_id: str, data: dict):
    global pies_dramaturgia
    if node_id not in nodos_registrados:
        raise HTTPException(status_code=404, detail="Nodo no encontrado.")

    pies = data.get("pies", [])
    if not isinstance(pies, list):
        raise HTTPException(status_code=400, detail="Formato inválido de Pies.")

    validar_pies_dramaturgia(pies, nodo_objetivo=node_id)
    pies_dramaturgia = pies
    guardar_estado()

    payloads = construir_payloads_desde_pies(pies)
    nodo_meta = nodos_registrados[node_id]
    topico = topico_config_de_nodo(nodo_meta)

    payload_cfg = payloads.get(node_id)
    if not payload_cfg:
        raise HTTPException(
            status_code=400,
            detail=f"El nodo '{nodo_meta.get('nombre', node_id)}' no tiene un evento válido asignado todavía en la puesta en escena."
        )

    payload_json = json.dumps(payload_cfg, indent=2, ensure_ascii=False)
    print(f"\n[MQTT OUT DRAMATURGIA NODO RETAIN] Tópico: {topico}\n{payload_json}\n")
    mqtt_client.publish(topico, payload_json, retain=True)

    registrar_en_historial_mqtt(topico, payload_cfg)

    return {"status": "success", "topico_publicado": topico, "payload": payload_cfg}


@app.post("/api/reiniciar-dramaturgia")
def reiniciar_modo_dramaturgia():
    global personajes_catalogo, relaciones_dramaturgia, pies_dramaturgia, historial_mqtt

    pers_nodos = {}
    for pname, pdata in personajes_catalogo.items():
        if pdata.get("origen") == "nodo":
            pers_nodos[pname] = pdata
    personajes_catalogo = pers_nodos
    relaciones_dramaturgia = {}
    pies_dramaturgia = []
    ultimo_config_mqtt = {"topico": None, "payload": None, "timestamp": None}
    guardar_estado()
    return {"status": "reiniciado_dramaturgia"}


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
            * { box-sizing: border-box; }
            body { margin: 0; font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f1f5f9; color: #0f172a; }

            .pipea-header {
                background: linear-gradient(90deg, #1e3a8a 0%, #3730a3 55%, #0f766e 100%);
                color: #ffffff;
                padding: 12px 24px;
                display: flex;
                justify-content: space-between;
                align-items: center;
                gap: 12px;
            }
            .pill-modo {
                background-color: rgba(255, 255, 255, 0.18);
                color: #ffffff;
                border: 1px solid rgba(255, 255, 255, 0.35);
                font-size: 12px;
                font-weight: 700;
                padding: 2px 10px;
                border-radius: 999px;
            }
            .btn-info-top {
                background-color: #facc15;
                color: #1e293b;
                border: 1px solid #eab308;
                padding: 4px 12px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: 700;
                cursor: pointer;
            }
            .btn-info-top:hover { background-color: #fde047; }

            .btn-cambiar-modo {
                background-color: rgba(255, 255, 255, 0.16);
                color: #ffffff;
                border: 1px solid rgba(255, 255, 255, 0.45);
                padding: 4px 12px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: 600;
                cursor: pointer;
            }
            .btn-cambiar-modo:hover { background-color: rgba(255, 255, 255, 0.28); }

            .btn-borrar-top {
                background-color: #b91c1c;
                color: #ffffff;
                border: 1px solid #fca5a5;
                padding: 6px 14px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: 700;
                cursor: pointer;
            }
            .btn-borrar-top:hover { background-color: #991b1b; }

            /* Pantalla de inicio limpia con dos botones cuadrados/redondeados lado a lado */
            .pantalla-inicio {
                min-height: calc(100vh - 68px);
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                padding: 32px 20px;
                background: linear-gradient(135deg, #eef2ff 0%, #f8fafc 50%, #f0fdfa 100%);
            }
            .caja-bienvenida {
                max-width: 780px;
                width: 100%;
                background: #ffffff;
                border: 1px solid #cbd5e1;
                border-radius: 16px;
                padding: 36px 28px;
                text-align: center;
                box-shadow: 0 10px 25px rgba(15, 23, 42, 0.08);
            }
            .fila-botones-modo {
                margin-top: 28px;
                display: flex;
                flex-wrap: wrap;
                justify-content: center;
                align-items: center;
                gap: 28px;
            }
            .boton-cuadrado-modo {
                width: 210px;
                height: 210px;
                border-radius: 20px;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                padding: 18px;
                cursor: pointer;
                border: none;
                color: #ffffff;
                transition: transform 0.15s ease, box-shadow 0.15s ease;
                box-shadow: 0 8px 18px rgba(15, 23, 42, 0.14);
            }
            .boton-cuadrado-modo:hover {
                transform: translateY(-3px);
                box-shadow: 0 12px 24px rgba(15, 23, 42, 0.2);
            }
            .btn-modo-normal {
                background: linear-gradient(145deg, #2563eb, #1d4ed8);
            }
            .btn-modo-dramaturgia {
                background: linear-gradient(145deg, #0f766e, #115e59);
            }

            /* Layout de trabajo de 2 columnas en CSS explícito (sin depender de clases nuevas de Tailwind) */
            .layout-trabajo {
                width: 100%;
                padding: 18px 20px;
                display: flex;
                gap: 18px;
                align-items: flex-start;
            }
            .panel-nodos-izq {
                width: 260px;
                min-width: 260px;
                background: #ffffff;
                border-radius: 8px;
                padding: 14px;
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
            }
            .panel-contenido-der {
                flex: 1;
                min-width: 0;
                background: #ffffff;
                border-radius: 8px;
                padding: 20px;
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
            }

            .sec-proponen {
                background-color: #fef3c7;
                color: #78350f;
                border: 1px solid #f59e0b;
                padding: 4px 10px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: 700;
                display: flex;
                justify-content: space-between;
                margin-bottom: 8px;
            }
            .sec-reaccionan {
                background-color: #e0f2fe;
                color: #0c4a6e;
                border: 1px solid #0284c7;
                padding: 4px 10px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: 700;
                display: flex;
                justify-content: space-between;
                margin-bottom: 8px;
            }
            .card-proponen {
                background-color: #fffbeb;
                border: 1px solid #fcd34d;
                border-left: 4px solid #d97706;
                padding: 10px;
                border-radius: 6px;
                margin-bottom: 8px;
            }
            .card-proponen-activa {
                background-color: #fef3c7;
                border: 1px solid #b45309;
                border-left: 4px solid #b45309;
                padding: 10px;
                border-radius: 6px;
                margin-bottom: 8px;
            }
            .card-reaccionan {
                background-color: #f0f9ff;
                border: 1px solid #bae6fd;
                border-left: 4px solid #0284c7;
                padding: 10px;
                border-radius: 6px;
                margin-bottom: 8px;
            }
            .card-reaccionan-activa {
                background-color: #e0f2fe;
                border: 1px solid #1d4ed8;
                border-left: 4px solid #1d4ed8;
                padding: 10px;
                border-radius: 6px;
                margin-bottom: 8px;
            }
            .estado-online {
                background-color: #dcfce7;
                color: #166534;
                border: 1px solid #86efac;
                font-size: 10px;
                font-weight: 700;
                padding: 2px 7px;
                border-radius: 999px;
                white-space: nowrap;
            }
            .estado-offline {
                background-color: #f1f5f9;
                color: #475569;
                border: 1px solid #cbd5e1;
                font-size: 10px;
                font-weight: 700;
                padding: 2px 7px;
                border-radius: 999px;
                white-space: nowrap;
            }
            .aviso-offline {
                background-color: #fffbeb;
                color: #92400e;
                border: 1px solid #fcd34d;
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 12px;
                margin-bottom: 14px;
            }
            .tab-indigo {
                background-color: #eef2ff;
                color: #312e81;
                border: 1px solid #a5b4fc;
                padding: 8px 14px;
                border-radius: 8px;
                font-size: 13px;
                font-weight: 700;
                cursor: pointer;
            }
            .tab-indigo-activa {
                background-color: #4338ca;
                color: #ffffff;
                border: 1px solid #3730a3;
                padding: 8px 14px;
                border-radius: 8px;
                font-size: 13px;
                font-weight: 700;
                cursor: pointer;
            }
            .tab-ambar {
                background-color: #fffbeb;
                color: #78350f;
                border: 1px solid #fcd34d;
                padding: 8px 14px;
                border-radius: 8px;
                font-size: 13px;
                font-weight: 700;
                cursor: pointer;
            }
            .tab-ambar-activa {
                background-color: #b45309;
                color: #ffffff;
                border: 1px solid #92400e;
                padding: 8px 14px;
                border-radius: 8px;
                font-size: 13px;
                font-weight: 700;
                cursor: pointer;
            }
            .tab-teal {
                background-color: #f0fdfa;
                color: #134e4a;
                border: 1px solid #5eead4;
                padding: 8px 14px;
                border-radius: 8px;
                font-size: 13px;
                font-weight: 700;
                cursor: pointer;
            }
            .tab-teal-activa {
                background-color: #0f766e;
                color: #ffffff;
                border: 1px solid #115e59;
                padding: 8px 14px;
                border-radius: 8px;
                font-size: 13px;
                font-weight: 700;
                cursor: pointer;
            }
            .btn-azul {
                background-color: #2563eb;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                font-weight: 700;
                cursor: pointer;
            }
            .btn-azul:hover { background-color: #1d4ed8; }

            .btn-verde {
                background-color: #16a34a;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                font-weight: 700;
                cursor: pointer;
            }
            .btn-verde:hover { background-color: #15803d; }

            .btn-teal {
                background-color: #0f766e;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                font-weight: 700;
                cursor: pointer;
            }
            .btn-teal:hover { background-color: #115e59; }

            .badge-proponen {
                background-color: #fef3c7;
                color: #78350f;
                border: 1px solid #f59e0b;
                font-size: 11px;
                font-weight: 700;
                padding: 3px 10px;
                border-radius: 999px;
            }
            .badge-reaccionan {
                background-color: #e0f2fe;
                color: #0c4a6e;
                border: 1px solid #0284c7;
                font-size: 11px;
                font-weight: 700;
                padding: 3px 10px;
                border-radius: 999px;
            }
            .panel-prueba-evento {
                background-color: #f8fafc;
                border: 1px solid #cbd5e1;
                border-left: 4px solid #0f766e;
                border-radius: 8px;
                padding: 14px 16px;
            }
            .monitor-mqtt {
                background-color: #0f172a;
                color: #f1f5f9;
                border-radius: 8px;
                padding: 14px 16px;
            }
            .tabla-pipea {
                width: 100%;
                border-collapse: collapse;
                font-size: 13px;
                background: #ffffff;
            }
            .tabla-pipea th, .tabla-pipea td {
                border: 1px solid #cbd5e1;
                padding: 8px 10px;
                text-align: left;
                vertical-align: top;
            }
            .tabla-pipea thead th {
                background: #f1f5f9;
                color: #1e293b;
                font-weight: 700;
            }
            .tecla-input {
                width: 42px;
                height: 32px;
                text-align: center;
                font-family: monospace;
                font-weight: 800;
                border: 1px solid #94a3b8;
                border-radius: 4px;
                background: #ffffff;
            }
        </style>
    </head>
    <body x-data="appData()">

        <!-- =================================================================== -->
        <!-- PANTALLA DE INICIO: DOS BOTONES CUADRADOS REDONDEADOS LADO A LADO   -->
        <!-- =================================================================== -->
        <template x-if="modoActual === 'inicio'">
            <div>
                <header class="pipea-header">
                    <div style="display:flex; align-items:center; gap:10px;">
                        <h1 style="margin:0; font-size:22px; font-weight:900; letter-spacing:1px;">PIPEA</h1>
                        <span class="pill-modo">Plataforma de Configuración de Nodos</span>
                    </div>
                    <button @click="showInfo = true" class="btn-info-top">Info...</button>
                </header>

                <div class="pantalla-inicio">
                    <div class="caja-bienvenida">
                        <h2 style="margin:0 0 10px 0; font-size:22px; font-weight:800; color:#0f172a;">
                            Bienvenido a la plataforma para configuración de nodos inalámbricos de expresiones artísticas PIPEA
                        </h2>
                        <p style="margin:0; font-size:14px; color:#475569; line-height:1.55;">
                            Esta plataforma tiene dos modos: un <b>Modo Normal</b> que permite configurar los nodos uno por uno, y un <b>Modo Dramaturgia</b> que permite configurar los nodos describiendo lo que pasa en el escenario.
                        </p>

                        <div class="fila-botones-modo">
                            <button @click="entrarModo('normal')" class="boton-cuadrado-modo btn-modo-normal">
                                <span style="font-size:17px; font-weight:900; margin-bottom:6px;">Modo Normal</span>
                                <span style="font-size:12px; opacity:0.92; line-height:1.35;">Configura los nodos uno por uno</span>
                            </button>

                            <button @click="entrarModo('dramaturgia')" class="boton-cuadrado-modo btn-modo-dramaturgia">
                                <span style="font-size:17px; font-weight:900; margin-bottom:6px;">Modo Dramaturgia</span>
                                <span style="font-size:12px; opacity:0.92; line-height:1.35;">Configura describiendo lo que pasa en el escenario</span>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </template>

        <!-- =================================================================== -->
        <!-- VISTA DE TRABAJO (MODO NORMAL O MODO DRAMATURGIA)                   -->
        <!-- =================================================================== -->
        <template x-if="modoActual !== 'inicio'">
            <div>
                <header class="pipea-header">
                    <div style="display:flex; flex-direction:column; gap:6px;">
                        <div style="display:flex; align-items:center; gap:10px;">
                            <h1 style="margin:0; font-size:22px; font-weight:900; letter-spacing:1px;">PIPEA</h1>
                            <span class="pill-modo" x-text="modoActual === 'normal' ? 'Modo Normal' : 'Modo Dramaturgia'"></span>
                        </div>
                        <div style="display:flex; align-items:center; gap:8px;">
                            <button @click="showInfo = true" class="btn-info-top">Info...</button>
                            <button @click="modoActual = 'inicio'" class="btn-cambiar-modo">Cambiar modo</button>
                        </div>
                    </div>

                    <div>
                        <button x-show="modoActual === 'normal'" @click="borrarConfiguracionNormal()" class="btn-borrar-top">
                            Borrar configuración
                        </button>
                        <button x-show="modoActual === 'dramaturgia'" @click="borrarConfiguracionDramaturgia()" class="btn-borrar-top">
                            Borrar configuración
                        </button>
                    </div>
                </header>

                <div class="layout-trabajo">
                    <!-- PANEL IZQUIERDO: NODOS REGISTRADOS -->
                    <aside class="panel-nodos-izq">
                        <div style="border-bottom:1px solid #e2e8f0; padding-bottom:8px; margin-bottom:12px;">
                            <h2 style="margin:0; font-size:16px; font-weight:700; color:#0f172a;">Nodos Registrados</h2>
                            <p x-show="modoActual === 'dramaturgia'" style="margin:2px 0 0 0; font-size:11px; color:#64748b;">
                                Solo visualización
                            </p>
                        </div>

                        <div style="max-height:62vh; overflow-y:auto; padding-right:4px;">
                            <!-- Proponen -->
                            <div style="margin-bottom:14px;">
                                <div class="sec-proponen">
                                    <span>Nodos que proponen</span>
                                    <span x-text="nodosProponen().length"></span>
                                </div>
                                <template x-for="nodo in nodosProponen()" :key="nodo.node_id">
                                    <div @click="modoActual === 'normal' ? seleccionarNodo(nodo) : null"
                                         :style="modoActual === 'normal' ? 'cursor:pointer;' : 'cursor:default;'"
                                         :class="(modoActual === 'normal' && nodoSelected?.node_id === nodo.node_id) ? 'card-proponen-activa' : 'card-proponen'">
                                        <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:6px;">
                                            <div style="font-weight:700; font-size:13px; color:#0f172a;" x-text="nodo.nombre"></div>
                                            <span :class="nodo.conectado ? 'estado-online' : 'estado-offline'"
                                                  x-text="nodo.conectado ? '● Conectado' : '○ Desconectado'"></span>
                                        </div>
                                        <div style="font-size:11px; color:#64748b; margin-top:4px;" x-text="'Tipo: ' + (nodo.tipo || 'nodo')"></div>
                                        <div style="font-size:11px; font-weight:600; color:#92400e; margin-top:2px;" x-text="'Rol: ' + textoRol(nodo)"></div>
                                    </div>
                                </template>
                                <p x-show="nodosProponen().length === 0" style="font-size:12px; color:#94a3b8; font-style:italic; text-align:center;">
                                    Sin nodos que propongan...
                                </p>
                            </div>

                            <!-- Reaccionan -->
                            <div>
                                <div class="sec-reaccionan">
                                    <span>Nodos que reaccionan</span>
                                    <span x-text="nodosReaccionan().length"></span>
                                </div>
                                <template x-for="nodo in nodosReaccionan()" :key="nodo.node_id">
                                    <div @click="modoActual === 'normal' ? seleccionarNodo(nodo) : null"
                                         :style="modoActual === 'normal' ? 'cursor:pointer;' : 'cursor:default;'"
                                         :class="(modoActual === 'normal' && nodoSelected?.node_id === nodo.node_id) ? 'card-reaccionan-activa' : 'card-reaccionan'">
                                        <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:6px;">
                                            <div style="font-weight:700; font-size:13px; color:#0f172a;" x-text="nodo.nombre"></div>
                                            <span :class="nodo.conectado ? 'estado-online' : 'estado-offline'"
                                                  x-text="nodo.conectado ? '● Conectado' : '○ Desconectado'"></span>
                                        </div>
                                        <div style="font-size:11px; color:#64748b; margin-top:4px;" x-text="'Tipo: ' + (nodo.tipo || 'nodo')"></div>
                                        <div style="font-size:11px; font-weight:600; color:#075985; margin-top:2px;" x-text="'Rol: ' + textoRol(nodo)"></div>
                                    </div>
                                </template>
                                <p x-show="nodosReaccionan().length === 0" style="font-size:12px; color:#94a3b8; font-style:italic; text-align:center;">
                                    Sin nodos que reaccionen...
                                </p>
                            </div>
                        </div>

                        <div style="margin-top:12px; padding-top:10px; border-top:1px solid #e2e8f0; font-size:12px; color:#64748b; display:flex; justify-content:space-between;">
                            <span>Conectados:</span>
                            <span style="font-weight:700; color:#15803d;" x-text="nodosConectados().length + ' / ' + nodos.length"></span>
                        </div>
                    </aside>

                    <!-- PANEL DERECHO: MODO NORMAL -->
                    <section x-show="modoActual === 'normal'" class="panel-contenido-der">
                        <template x-if="nodoSelected">
                            <div>
                                <div style="display:flex; flex-wrap:wrap; justify-content:space-between; align-items:center; border-bottom:1px solid #e2e8f0; padding-bottom:12px; margin-bottom:14px; gap:8px;">
                                    <div>
                                        <h2 style="margin:0; font-size:19px; font-weight:800; color:#0f172a;" x-text="'Configuración de Nodos — ' + nodoSelected.nombre"></h2>
                                        <p style="margin:2px 0 0 0; font-size:12px; color:#64748b;"
                                           x-text="'ID: ' + nodoSelected.node_id + ' | Tipo: ' + (nodoSelected.tipo || 'nodo') + ' | Rol: ' + textoRol(nodoSelected)"></p>
                                    </div>
                                    <div style="display:flex; align-items:center; gap:8px;">
                                        <span :class="esNodoConectadoActual(nodoSelected) ? 'estado-online' : 'estado-offline'"
                                              x-text="esNodoConectadoActual(nodoSelected) ? '● Conectado' : '○ Desconectado'"></span>
                                        <span :class="puedeProponer(nodoSelected) ? 'badge-proponen' : 'badge-reaccionan'"
                                              x-text="'Rol: ' + textoRol(nodoSelected)"></span>
                                    </div>
                                </div>

                                <div x-show="!esNodoConectadoActual(nodoSelected)" class="aviso-offline">
                                    Este nodo está actualmente <b>desconectado</b>, pero puedes seguir editando y aplicando su configuración; queda guardada y retenida en el broker para cuando se vuelva a conectar.
                                </div>

                                <!-- Rol Proponer -->
                                <template x-if="puedeProponer(nodoSelected)">
                                    <div style="margin-bottom:18px;">
                                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px; gap:8px;">
                                            <div>
                                                <h3 style="margin:0; font-size:13px; font-weight:800; color:#334155; text-transform:uppercase;"
                                                    x-text="tieneMultiplesActivadores(nodoSelected) ? 'Rol Proponer — Asignación de Tecla a Evento' : 'Rol Proponer — Evento a Publicar al Activarse'"></h3>
                                                <p style="margin:2px 0 0 0; font-size:12px; color:#64748b;"
                                                   x-text="tieneMultiplesActivadores(nodoSelected)
                                                        ? 'Asigna una tecla (1 carácter) a un evento; al presionarla publicará en pipea/evento/[evento].'
                                                        : 'Este nodo es de activador único: indica el evento que publicará en pipea/evento/[evento] al activarse.'"></p>
                                            </div>
                                            <button x-show="tieneMultiplesActivadores(nodoSelected)" @click="agregarFilaPublica()" class="btn-verde" style="padding:6px 12px; font-size:12px;">
                                                + Agregar fila
                                            </button>
                                        </div>

                                        <div style="overflow-x:auto;">
                                            <table class="tabla-pipea">
                                                <thead>
                                                    <tr>
                                                        <th x-show="tieneMultiplesActivadores(nodoSelected)" style="width:95px;">Tecla (char)</th>
                                                        <th>Evento</th>
                                                        <th x-show="tieneMultiplesActivadores(nodoSelected)" style="width:60px; text-align:center;">Quitar</th>
                                                    </tr>
                                                </thead>
                                                <tbody>
                                                    <template x-for="(fila, idx) in nodoSelected.mapeos_actuales" :key="idx">
                                                        <tr>
                                                            <td x-show="tieneMultiplesActivadores(nodoSelected)">
                                                                <input type="text" maxlength="1" x-model="fila.disparador" placeholder="A" class="tecla-input">
                                                            </td>
                                                            <td>
                                                                <input type="text" x-model="fila.evento" placeholder="Ej. encendida o soloGuitarra"
                                                                       style="width:100%; padding:6px 10px; border:1px solid #cbd5e1; border-radius:4px; font-size:13px;">
                                                            </td>
                                                            <td x-show="tieneMultiplesActivadores(nodoSelected)" style="text-align:center;">
                                                                <button @click="eliminarFilaPublica(idx)" style="color:#dc2626; background:none; border:none; font-weight:700; cursor:pointer;">✕</button>
                                                            </td>
                                                        </tr>
                                                    </template>
                                                </tbody>
                                            </table>
                                        </div>
                                    </div>
                                </template>

                                <!-- Rol Reaccionar -->
                                <template x-if="puedeReaccionar(nodoSelected)">
                                    <div>
                                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px; gap:8px;">
                                            <div>
                                                <h3 style="margin:0; font-size:13px; font-weight:800; color:#334155; text-transform:uppercase;">Rol Reaccionar — Eventos, Reacciones y Parámetros</h3>
                                                <p style="margin:2px 0 0 0; font-size:12px; color:#64748b;">Selecciona un evento ya creado, define la reacción (opcional) y ajusta los parámetros del nodo.</p>
                                            </div>
                                            <button @click="agregarFilaReaccion()" class="btn-verde" style="padding:6px 12px; font-size:12px;">
                                                + Agregar fila
                                            </button>
                                        </div>

                                        <div style="overflow-x:auto;">
                                            <table class="tabla-pipea">
                                                <thead>
                                                    <tr>
                                                        <th>Evento</th>
                                                        <th>Reacción / Acción (opcional)</th>
                                                        <template x-for="param in (nodoSelected.parametros_disponibles || [])" :key="param.id">
                                                            <th>
                                                                <div x-text="param.nombre"></div>
                                                                <div style="font-size:10px; font-weight:400; color:#64748b;"
                                                                     x-text="param.tipo === 'int' ? ('Rango: ' + (param.min ?? 0) + ' a ' + (param.max ?? 255)) : 'Lista'"></div>
                                                            </th>
                                                        </template>
                                                        <th style="width:60px; text-align:center;">Quitar</th>
                                                    </tr>
                                                </thead>
                                                <tbody>
                                                    <template x-for="(fila, idx) in nodoSelected.acciones_actuales" :key="idx">
                                                        <tr>
                                                            <td>
                                                                <select x-model="fila.evento" style="padding:6px 8px; border:1px solid #cbd5e1; border-radius:4px; background:#fff; min-width:150px;">
                                                                    <option value="">-- Seleccionar evento --</option>
                                                                    <template x-for="ev in obtenerEventosPropuestos()" :key="ev">
                                                                        <option :value="ev" x-text="ev"></option>
                                                                    </template>
                                                                    <template x-if="fila.evento && !obtenerEventosPropuestos().includes(fila.evento)">
                                                                        <option :value="fila.evento" x-text="fila.evento"></option>
                                                                    </template>
                                                                </select>
                                                            </td>
                                                            <td>
                                                                <input type="text" x-model="fila.accion" placeholder="Opcional si coincide..."
                                                                       style="padding:6px 8px; border:1px solid #cbd5e1; border-radius:4px; min-width:155px;">
                                                            </td>
                                                            <template x-for="param in (nodoSelected.parametros_disponibles || [])" :key="param.id">
                                                                <td>
                                                                    <template x-if="param.tipo === 'int'">
                                                                        <input type="number" :min="param.min ?? 0" :max="param.max ?? 255"
                                                                               x-model.number="fila.parametros[param.id]"
                                                                               style="padding:6px 8px; border:1px solid #cbd5e1; border-radius:4px; width:90px;">
                                                                    </template>
                                                                    <template x-if="param.tipo === 'lista'">
                                                                        <select x-model="fila.parametros[param.id]"
                                                                                style="padding:6px 8px; border:1px solid #cbd5e1; border-radius:4px; background:#fff; min-width:130px;">
                                                                            <template x-for="op in (param.opciones || [])" :key="op">
                                                                                <option :value="op" x-text="op"></option>
                                                                            </template>
                                                                        </select>
                                                                    </template>
                                                                </td>
                                                            </template>
                                                            <td style="text-align:center;">
                                                                <button @click="eliminarFilaReaccion(idx)" style="color:#dc2626; background:none; border:none; font-weight:700; cursor:pointer;">✕</button>
                                                            </td>
                                                        </tr>
                                                    </template>
                                                </tbody>
                                            </table>
                                        </div>
                                    </div>
                                </template>

                                <div style="margin-top:18px; padding-top:12px; border-top:1px solid #e2e8f0; display:flex; justify-content:flex-end;">
                                    <button @click="aplicarConfiguracionNormal()" class="btn-azul" style="padding:10px 22px; font-size:13px;">
                                        Aplicar Configuración
                                    </button>
                                </div>
                            </div>
                        </template>

                        <template x-if="!nodoSelected">
                            <div style="padding:60px 20px; text-align:center; color:#94a3b8; font-style:italic;">
                                Selecciona un nodo en "Nodos Registrados" para configurar sus parámetros.
                            </div>
                        </template>
                    </section>

                    <!-- PANEL DERECHO: MODO DRAMATURGIA -->
                    <section x-show="modoActual === 'dramaturgia'" class="panel-contenido-der">
                        <div style="display:flex; flex-wrap:wrap; gap:10px; border-bottom:1px solid #e2e8f0; padding-bottom:12px; margin-bottom:16px;">
                            <button @click="pestanaDramaturgia = 'personajes'; cargarDramaturgia()"
                                    :class="pestanaDramaturgia === 'personajes' ? 'tab-ambar-activa' : 'tab-ambar'">
                                1. Personajes
                            </button>
                            <button @click="pestanaDramaturgia = 'nodoPersonaje'; prepararRelacionesUI()"
                                    :class="pestanaDramaturgia === 'nodoPersonaje' ? 'tab-teal-activa' : 'tab-teal'">
                                2. Nodo-Personaje
                            </button>
                            <button @click="pestanaDramaturgia = 'puestaEscena'"
                                    :class="pestanaDramaturgia === 'puestaEscena' ? 'tab-indigo-activa' : 'tab-indigo'">
                                3. Puesta en escena
                            </button>
                        </div>

                        <!-- Pestaña 1: Personajes -->
                        <div x-show="pestanaDramaturgia === 'personajes'">
                            <h2 style="margin:0 0 4px 0; font-size:18px; font-weight:800;">Catálogo de Personajes</h2>
                            <p style="margin:0 0 14px 0; font-size:12px; color:#64748b;">
                                Define los personajes de la obra o montaje.
                            </p>

                            <div style="background:#f8fafc; border:1px solid #cbd5e1; border-radius:8px; padding:14px; margin-bottom:16px;">
                                <div style="margin-bottom:10px;">
                                    <label style="display:block; font-size:12px; font-weight:700; margin-bottom:4px;">Nombre del Personaje</label>
                                    <input type="text" x-model="nuevoPersonaje.nombre" placeholder="Ej. sofia, banda, ambiente"
                                           style="width:100%; padding:8px 10px; border:1px solid #cbd5e1; border-radius:4px; background:#fff;">
                                </div>
                                <div style="margin-bottom:10px;">
                                    <label style="display:block; font-size:12px; font-weight:700; margin-bottom:4px;">Descripción</label>
                                    <textarea rows="2" x-model="nuevoPersonaje.descripcion" placeholder="Descripción escénica..."
                                              style="width:100%; padding:8px 10px; border:1px solid #cbd5e1; border-radius:4px; background:#fff;"></textarea>
                                </div>
                                <div style="display:flex; justify-content:flex-end;">
                                    <button @click="guardarPersonaje()" class="btn-verde" style="padding:8px 16px; font-size:12px;">
                                        + Guardar Personaje
                                    </button>
                                </div>
                            </div>

                            <table class="tabla-pipea">
                                <thead>
                                    <tr>
                                        <th>Personaje</th>
                                        <th>Descripción</th>
                                        <th style="width:100px;">Origen</th>
                                        <th style="width:100px; text-align:center;">Acción</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <template x-for="pers in personajes" :key="pers.nombre">
                                        <tr>
                                            <td style="font-weight:700;" x-text="pers.nombre"></td>
                                            <td x-text="pers.descripcion || '—'"></td>
                                            <td x-text="pers.origen === 'nodo' ? 'Nodo' : 'Usuario'"></td>
                                            <td style="text-align:center;">
                                                <button x-show="pers.origen !== 'nodo'" @click="eliminarPersonaje(pers.nombre)"
                                                        style="color:#dc2626; background:none; border:none; font-weight:700; cursor:pointer;">Eliminar</button>
                                                <span x-show="pers.origen === 'nodo'" style="color:#94a3b8; font-size:11px;">Fijo</span>
                                            </td>
                                        </tr>
                                    </template>
                                    <tr x-show="personajes.length === 0">
                                        <td colspan="4" style="text-align:center; color:#94a3b8; font-style:italic;">No hay personajes registrados todavía.</td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>

                        <!-- Pestaña 2: Nodo-Personaje -->
                        <div x-show="pestanaDramaturgia === 'nodoPersonaje'">
                            <h2 style="margin:0 0 4px 0; font-size:18px; font-weight:800;">Relación Nodo — Personaje</h2>
                            <p style="margin:0 0 14px 0; font-size:12px; color:#64748b;">
                                Asocia nodos y personajes para filtrar los nodos de cada personaje en Puesta en escena.
                            </p>

                            <table class="tabla-pipea">
                                <thead>
                                    <tr>
                                        <th style="width:200px;">Nodo / Tipo</th>
                                        <th style="width:210px;">Personaje(s)</th>
                                        <th style="width:110px;">Rol</th>
                                        <th>Comentarios</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <template x-for="fila in relacionesNodoPersonaje" :key="fila.node_id">
                                        <tr>
                                            <td>
                                                <div style="font-weight:700;" x-text="fila.nombre"></div>
                                                <div style="font-size:11px; color:#64748b;" x-text="fila.node_id + ' · ' + fila.tipo"></div>
                                            </td>
                                            <td>
                                                <template x-if="fila.rol === 'reacciona'">
                                                    <select x-model="fila.personajeUnico" style="width:100%; padding:6px; border:1px solid #cbd5e1; border-radius:4px; background:#fff;">
                                                        <option value="">-- Sin personaje --</option>
                                                        <template x-for="pers in personajes" :key="pers.nombre">
                                                            <option :value="pers.nombre" x-text="pers.nombre"></option>
                                                        </template>
                                                    </select>
                                                </template>
                                                <template x-if="fila.rol !== 'reacciona'">
                                                    <div style="display:flex; flex-direction:column; gap:4px;">
                                                        <template x-for="pers in personajes" :key="pers.nombre">
                                                            <label style="display:flex; align-items:center; gap:6px; font-size:12px;">
                                                                <input type="checkbox" :value="pers.nombre" x-model="fila.personajes">
                                                                <span x-text="pers.nombre"></span>
                                                            </label>
                                                        </template>
                                                    </div>
                                                </template>
                                            </td>
                                            <td x-text="fila.rol === 'propone' ? 'Propone' : (fila.rol === 'ambos' ? 'Ambos' : 'Reacciona')"></td>
                                            <td>
                                                <textarea rows="2" x-model="fila.comentarios" placeholder="Notas..."
                                                          style="width:100%; padding:6px; border:1px solid #cbd5e1; border-radius:4px;"></textarea>
                                            </td>
                                        </tr>
                                    </template>
                                </tbody>
                            </table>

                            <div style="margin-top:14px; display:flex; justify-content:flex-end;" x-show="relacionesNodoPersonaje.length > 0">
                                <button @click="guardarTodasRelaciones()" class="btn-teal" style="padding:8px 18px; font-size:13px;">
                                    Guardar Relaciones
                                </button>
                            </div>
                        </div>

                        <!-- Pestaña 3: Puesta en escena -->
                        <div x-show="pestanaDramaturgia === 'puestaEscena'">
                            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px; gap:8px;">
                                <div>
                                    <h2 style="margin:0; font-size:18px; font-weight:800;">Puesta en escena</h2>
                                    <p style="margin:2px 0 0 0; font-size:12px; color:#64748b;">
                                        De izquierda a derecha: Pie, Personaje en escena y nodos proponentes, Evento, Personajes/nodos que reaccionan y especificaciones.
                                    </p>
                                </div>
                                <button @click="agregarPie()" class="btn-verde" style="padding:8px 14px; font-size:12px;">
                                    + Agregar Pie
                                </button>
                            </div>

                            <div x-show="mensajeValidacionDramaturgia()"
                                 style="background:#fef2f2; color:#991b1b; border:1px solid #f87171; border-radius:6px; padding:8px 12px; font-size:12px; font-weight:700; margin-bottom:12px;"
                                 x-text="mensajeValidacionDramaturgia()"></div>

                            <div style="overflow-x:auto;">
                                <table class="tabla-pipea">
                                    <thead>
                                        <tr>
                                            <th style="min-width:170px;">Pie</th>
                                            <th style="min-width:220px;">Personaje en escena / Nodos que proponen</th>
                                            <th style="min-width:150px;">Evento</th>
                                            <th style="min-width:220px;">Personajes / Nodos que reaccionan</th>
                                            <th style="min-width:380px;">Especificaciones y Aplicar config</th>
                                            <th style="width:65px; text-align:center;">Quitar</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        <template x-for="(pieItem, pIdx) in piesDramaturgia" :key="pieItem.id">
                                            <tr>
                                                <td>
                                                    <div style="font-size:10px; font-weight:800; color:#3730a3; margin-bottom:4px;" x-text="'Pie #' + (pIdx + 1)"></div>
                                                    <textarea rows="4" x-model="pieItem.pie" placeholder="Guía de escena..."
                                                              style="width:100%; padding:6px; border:1px solid #cbd5e1; border-radius:4px;"></textarea>
                                                </td>

                                                <td>
                                                    <select x-model="pieItem.personajeEscena" @change="actualizarProponentesDePie(pieItem)"
                                                            style="width:100%; padding:6px; border:1px solid #cbd5e1; border-radius:4px; background:#fff; margin-bottom:8px;">
                                                        <option value="">-- Personaje en escena --</option>
                                                        <template x-for="pers in personajes" :key="pers.nombre">
                                                            <option :value="pers.nombre" x-text="pers.nombre"></option>
                                                        </template>
                                                    </select>

                                                    <template x-for="prop in pieItem.proponentes" :key="prop.node_id">
                                                        <div style="background:#fffbeb; border:1px solid #fcd34d; border-radius:6px; padding:8px; margin-bottom:6px;">
                                                            <label style="display:flex; align-items:center; gap:6px; font-weight:700; margin-bottom:6px;">
                                                                <input type="checkbox" x-model="prop.seleccionado">
                                                                <span x-text="prop.nombre"></span>
                                                            </label>

                                                            <div x-show="prop.seleccionado && prop.multiples_activadores" style="display:flex; align-items:center; gap:6px; margin-bottom:6px;">
                                                                <span style="font-size:11px;">Tecla:</span>
                                                                <input type="text"
                                                                       maxlength="1"
                                                                       :value="prop.disparador"
                                                                       @input="prop.disparador = $event.target.value.slice(-1)"
                                                                       placeholder="a"
                                                                       class="tecla-input">
                                                            </div>


                                                        </div>
                                                    </template>
                                                </td>

                                                <td>
                                                    <input type="text" x-model="pieItem.evento" placeholder="Ej. soloBajo"
                                                           style="width:100%; padding:6px 8px; border:1px solid #cbd5e1; border-radius:4px; font-family:monospace;">
                                                </td>

                                                <td>
                                                    <div style="border:1px solid #bae6fd; background:#f0f9ff; border-radius:6px; padding:6px; margin-bottom:8px; max-height:110px; overflow-y:auto;">
                                                        <template x-for="pers in personajes" :key="pers.nombre">
                                                            <label style="display:flex; align-items:center; gap:6px; font-size:12px; margin-bottom:3px;">
                                                                <input type="checkbox" :value="pers.nombre" x-model="pieItem.personajesReaccionan" @change="sincronizarReactivosDePie(pieItem)">
                                                                <span x-text="pers.nombre"></span>
                                                            </label>
                                                        </template>
                                                    </div>

                                                    <template x-for="reac in pieItem.reactivos" :key="reac.node_id">
                                                        <label style="display:flex; align-items:center; gap:6px; background:#fff; border:1px solid #cbd5e1; border-radius:4px; padding:5px 8px; margin-bottom:4px; font-size:12px;">
                                                            <input type="checkbox" x-model="reac.seleccionado">
                                                            <span style="font-weight:700;" x-text="reac.nombre"></span>
                                                            <span style="font-size:10px; color:#0369a1;" x-text="'(' + reac.personaje + ')'"></span>
                                                        </label>
                                                    </template>
                                                </td>

                                                <td>
                                                    <template x-for="reac in pieItem.reactivos.filter(r => r.seleccionado)" :key="reac.node_id">
                                                        <div style="background:#f8fafc; border:1px solid #cbd5e1; border-radius:6px; padding:8px; margin-bottom:8px;">
                                                            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px; gap:8px;">
                                                                <span style="font-weight:700;" x-text="reac.nombre + ' [' + reac.personaje + ']'"></span>
                                                                <button @click="aplicarConfigNodoIndividualDramaturgia(reac.node_id)"
                                                                        class="btn-azul" style="padding:4px 10px; font-size:11px;">
                                                                    Aplicar config
                                                                </button>
                                                            </div>

                                                            <div style="display:flex; flex-wrap:wrap; gap:8px; align-items:flex-end;">
                                                                <div>
                                                                    <label style="display:block; font-size:10px; font-weight:700; margin-bottom:2px;">Reacción (opc.)</label>
                                                                    <input type="text" x-model="reac.accion" placeholder="Igual al evento"
                                                                           style="padding:4px 8px; border:1px solid #cbd5e1; border-radius:4px; width:125px;">
                                                                </div>
                                                                <template x-for="param in (reac.parametros_disponibles || [])" :key="param.id">
                                                                    <div>
                                                                        <label style="display:block; font-size:10px; font-weight:700; margin-bottom:2px;" x-text="param.nombre"></label>
                                                                        <template x-if="param.tipo === 'int'">
                                                                            <input type="number" :min="param.min ?? 0" :max="param.max ?? 255"
                                                                                   x-model.number="reac.parametros[param.id]"
                                                                                   style="padding:4px 6px; border:1px solid #cbd5e1; border-radius:4px; width:75px;">
                                                                        </template>
                                                                        <template x-if="param.tipo === 'lista'">
                                                                            <select x-model="reac.parametros[param.id]"
                                                                                    style="padding:4px 6px; border:1px solid #cbd5e1; border-radius:4px; background:#fff;">
                                                                                <template x-for="op in (param.opciones || [])" :key="op">
                                                                                    <option :value="op" x-text="op"></option>
                                                                                </template>
                                                                            </select>
                                                                        </template>
                                                                    </div>
                                                                </template>
                                                            </div>
                                                        </div>
                                                    </template>
                                                </td>

                                                <td style="text-align:center;">
                                                    <button @click="eliminarPie(pIdx)" style="color:#dc2626; background:none; border:none; font-weight:700; cursor:pointer;">✕</button>
                                                </td>
                                            </tr>
                                        </template>
                                        <tr x-show="piesDramaturgia.length === 0">
                                            <td colspan="6" style="text-align:center; color:#94a3b8; font-style:italic; padding:24px;">
                                                No hay Pies agregados. Pulsa <b>+ Agregar Pie</b> para comenzar.
                                            </td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>

                            <div style="margin-top:16px; padding-top:12px; border-top:1px solid #e2e8f0; display:flex; justify-content:space-between; align-items:center; gap:10px;">
                                <button @click="guardarBorradorPies()" style="padding:8px 14px; border:1px solid #cbd5e1; border-radius:6px; background:#f8fafc; font-weight:700; font-size:12px; cursor:pointer;">
                                    Guardar borrador
                                </button>
                                <button @click="aplicarConfiguracionEscenica()" class="btn-teal" style="padding:10px 20px; font-size:13px;">
                                    Aplicar configuración escénica
                                </button>
                            </div>
                        </div>
                    </section>
                </div>

                <!-- PRUEBA DE EVENTOS INDEPENDIENTE POR MODO Y MONITOR MQTT (ÚLTIMOS 10) -->
                <div style="padding:0 20px 24px 20px;">
                    <!-- Probador exclusivo de Modo Normal -->
                    <div x-show="modoActual === 'normal'" class="panel-prueba-evento" style="margin-bottom:14px; display:flex; flex-wrap:wrap; justify-content:space-between; align-items:center; gap:10px;">
                        <div>
                            <div style="font-size:13px; font-weight:800; text-transform:uppercase;">Prueba de Eventos — Modo Normal</div>
                            <div style="font-size:12px; color:#475569;">Selecciona un evento ya creado en Modo Normal y publícalo en <code>pipea/evento/[evento]</code>.</div>
                        </div>
                        <div style="display:flex; flex-wrap:wrap; align-items:center; gap:8px;">
                            <select x-model="eventoPruebaNormal" style="padding:6px 10px; border:1px solid #cbd5e1; border-radius:4px; background:#fff; min-width:200px;">
                                <option value="">-- Seleccionar evento creado --</option>
                                <template x-for="ev in obtenerEventosModoNormal()" :key="ev">
                                    <option :value="ev" x-text="ev"></option>
                                </template>
                            </select>
                            <button @click="emitirEventoModo('normal')" class="btn-teal" style="padding:7px 14px; font-size:13px;">
                                Emitir Evento
                            </button>
                        </div>
                    </div>

                    <!-- Probador exclusivo de Modo Dramaturgia -->
                    <div x-show="modoActual === 'dramaturgia'" class="panel-prueba-evento" style="margin-bottom:14px; display:flex; flex-wrap:wrap; justify-content:space-between; align-items:center; gap:10px;">
                        <div>
                            <div style="font-size:13px; font-weight:800; text-transform:uppercase;">Prueba de Eventos — Modo Dramaturgia</div>
                            <div style="font-size:12px; color:#475569;">Selecciona un evento definido en los Pies de Puesta en escena y publícalo en <code>pipea/evento/[evento]</code>.</div>
                        </div>
                        <div style="display:flex; flex-wrap:wrap; align-items:center; gap:8px;">
                            <select x-model="eventoPruebaDramaturgia" style="padding:6px 10px; border:1px solid #cbd5e1; border-radius:4px; background:#fff; min-width:200px;">
                                <option value="">-- Seleccionar evento de Pie --</option>
                                <template x-for="ev in obtenerEventosModoDramaturgia()" :key="ev">
                                    <option :value="ev" x-text="ev"></option>
                                </template>
                            </select>
                            <button @click="emitirEventoModo('dramaturgia')" class="btn-teal" style="padding:7px 14px; font-size:13px;">
                                Emitir Evento
                            </button>
                        </div>
                    </div>

                    <div class="monitor-mqtt">
                        <div style="display:flex; justify-content:space-between; border-bottom:1px solid #334155; padding-bottom:8px; margin-bottom:10px; font-size:12px;">
                            <span style="font-weight:700; color:#34d399;">MONITOR MQTT — ÚLTIMOS MENSAJES ENVIADOS / RECIBIDOS (MÁX. 10)</span>
                            <span style="font-family:monospace; color:#94a3b8;"
                                  x-text="(historialMqtt?.length || 0) + ' / 10 mensajes'"></span>
                        </div>

                        <div style="max-height:340px; overflow-y:auto; display:flex; flex-direction:column; gap:10px;">
                            <template x-for="(msgItem, mIdx) in (historialMqtt || [])" :key="mIdx">
                                <div style="background:#1e293b; border:1px solid #334155; border-radius:6px; padding:10px 12px;">
                                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px; font-size:11px; gap:8px;">
                                        <span style="font-family:monospace; font-weight:700; color:#6ee7b7;"
                                              x-text="'#' + (mIdx + 1) + ' · ' + msgItem.topico"></span>
                                        <span style="font-family:monospace; color:#94a3b8;"
                                              x-text="msgItem.timestamp"></span>
                                    </div>
                                    <pre style="margin:0; font-size:11px; color:#e2e8f0; white-space:pre-wrap;"
                                         x-text="JSON.stringify(msgItem.payload, null, 2)"></pre>
                                </div>
                            </template>

                            <p x-show="!historialMqtt || historialMqtt.length === 0"
                               style="margin:0; font-size:12px; color:#94a3b8; font-style:italic;">
                                Pulsa Aplicar Configuración o Emitir Evento para ver los últimos mensajes publicados.
                            </p>
                        </div>
                    </div>
                </div>
            </div>
        </template>

        <!-- MODAL DE AYUDA -->
        <div x-show="showInfo" style="display:none; position:fixed; inset:0; background:rgba(0,0,0,0.5); z-index:999; align-items:center; justify-content:center; padding:16px;">
            <div style="background:#fff; border-radius:10px; max-width:640px; width:100%; padding:22px; max-height:85vh; overflow-y:auto;">
                <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid #e2e8f0; padding-bottom:10px; margin-bottom:14px;">
                    <h3 style="margin:0; font-size:18px; font-weight:800;">Información General y Guía de Uso — PIPEA</h3>
                    <button @click="showInfo = false" style="background:none; border:none; font-size:18px; font-weight:700; cursor:pointer; color:#64748b;">✕</button>
                </div>
                <p style="font-size:13px; color:#334155; line-height:1.55;">
                    <b>PIPEA</b> permite configurar los nodos inalámbricos sin modificar su firmware. Cuenta con <b>Modo Normal</b> (uno por uno) y <b>Modo Dramaturgia</b> (por personajes y pies escénicos).
                </p>
                <ol style="font-size:13px; color:#334155; line-height:1.6; padding-left:20px;">
                    <li>En <b>Modo Normal</b>, selecciona un nodo a la izquierda, ajusta sus eventos o parámetros y pulsa <b>Aplicar Configuración</b>.</li>
                    <li>En <b>Modo Dramaturgia</b>, define personajes, asócialos a nodos en <b>Nodo-Personaje</b> y arma los pies en <b>Puesta en escena</b>.</li>
                    <li>Usa <b>Prueba de Eventos</b> abajo para disparar eventos en <code>pipea/evento/[evento]</code> y revisar el JSON en el <b>Monitor MQTT</b>.</li>
                </ol>
                <div style="display:flex; justify-content:flex-end; margin-top:16px;">
                    <button @click="showInfo = false" class="btn-azul" style="padding:8px 18px; font-size:13px;">Entendido</button>
                </div>
            </div>
        </div>

        <script>
            function appData() {
                return {
                    modoActual: 'inicio',
                    pestanaDramaturgia: 'personajes',
                    nodos: [],
                    nodoSelected: null,
                    historialMqtt: [],
                    showInfo: false,
                    eventoPruebaNormal: '',
                    eventoPruebaDramaturgia: '',

                    personajes: [],
                    nuevoPersonaje: { nombre: '', descripcion: '' },
                    relacionesMap: {},
                    relacionesNodoPersonaje: [],
                    piesDramaturgia: [],

                    async init() {
                        await this.cargarNodos();
                        await this.cargarDramaturgia();
                        const ordenados = this.nodosOrdenados();
                        if (ordenados.length > 0 && !this.nodoSelected) {
                            this.seleccionarNodo(ordenados[0]);
                        }
                        if (!this.eventoPruebaNormal && this.obtenerEventosModoNormal().length > 0) {
                            this.eventoPruebaNormal = this.obtenerEventosModoNormal()[0];
                        }
                        if (!this.eventoPruebaDramaturgia && this.obtenerEventosModoDramaturgia().length > 0) {
                            this.eventoPruebaDramaturgia = this.obtenerEventosModoDramaturgia()[0];
                        }
                        setInterval(() => {
                            this.cargarNodos();
                        }, 4000);
                    },

                    async entrarModo(modo) {
                        this.modoActual = modo;
                        await this.cargarNodos();
                        if (modo === 'normal') {
                            const ordenados = this.nodosOrdenados();
                            if (ordenados.length > 0 && !this.nodoSelected) {
                                this.seleccionarNodo(ordenados[0]);
                            }
                        } else if (modo === 'dramaturgia') {
                            await this.cargarDramaturgia();
                            this.prepararRelacionesUI();
                        }
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

                        if (this.modoActual === 'dramaturgia' && this.pestanaDramaturgia === 'nodoPersonaje') {
                            this.prepararRelacionesUI();
                        }

                        let rCfg = await fetch('/api/historial-mqtt');
                        this.historialMqtt = await rCfg.json();
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

                    obtenerEventosModoNormal() {
                        const eventosDramaturgia = new Set(this.obtenerEventosModoDramaturgia());
                        const eventos = new Set(this.obtenerEventosPropuestos());
                        (this.nodos || []).forEach(n => {
                            if (this.puedeReaccionar(n)) {
                                (n.acciones_actuales || []).forEach(a => {
                                    const ev = (a.evento || '').trim();
                                    if (ev && !eventosDramaturgia.has(ev)) eventos.add(ev);
                                });
                            }
                        });
                        return Array.from(eventos);
                    },

                    obtenerEventosModoDramaturgia() {
                        const eventos = new Set();
                        (this.piesDramaturgia || []).forEach(p => {
                            const ev = (p.evento || '').trim();
                            if (ev) eventos.add(ev);
                        });
                        return Array.from(eventos);
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

                    validarTeclasRepetidasNormal(nodo) {
                        if (!nodo || !this.puedeProponer(nodo) || !this.tieneMultiplesActivadores(nodo)) {
                            return '';
                        }
                        const vistas = new Set();
                        for (const m of (nodo.mapeos_actuales || [])) {
                            const t = String(m.disparador || '').trim();
                            if (!t) continue;
                            if (vistas.has(t)) {
                                return `Advertencia: la tecla "${t}" está repetida en este nodo. Asigna una tecla distinta antes de aplicar la configuración.`;
                            }
                            vistas.add(t);
                        }
                        return '';
                    },

                    async aplicarConfiguracionNormal() {
                        const errTecla = this.validarTeclasRepetidasNormal(this.nodoSelected);
                        if (errTecla) {
                            alert(errTecla);
                            return;
                        }
                        const confirmar = confirm(
                            '¿Deseas aplicar y publicar esta configuración para ' + (this.nodoSelected?.nombre || 'el nodo') + ' en MQTT?'
                        );
                        if (!confirmar) return;

                        let res = await fetch(`/api/configurar/${this.nodoSelected.node_id}`, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify(this.nodoSelected)
                        });
                        let data = await res.json();
                        await this.cargarNodos();
                        this.seleccionarNodo(this.nodoSelected);
                        alert("¡Configuración de Modo Normal guardada y publicada en " + data.topico_publicado + "!");
                    },

                    async borrarConfiguracionNormal() {
                        const seguro = confirm(
                            '¿Borrar únicamente la configuración de Modo Normal? (Los datos de Modo Dramaturgia no se verán afectados).'
                        );
                        if (!seguro) return;

                        const res = await fetch('/api/reiniciar-normal', { method: 'POST' });
                        if (!res.ok) {
                            alert('No se pudo borrar la configuración de Modo Normal.');
                            return;
                        }
                        this.nodoSelected = null;
                        await this.cargarNodos();
                        alert('Configuración de Modo Normal borrada.');
                    },

                    async cargarDramaturgia() {
                        const res = await fetch('/api/dramaturgia/estado');
                        const data = await res.json();
                        this.personajes = data.personajes || [];
                        this.relacionesMap = data.relaciones || {};
                        this.piesDramaturgia = (data.pies || []).map((p, i) => ({
                            id: p.id || ('pie_' + Date.now() + '_' + i),
                            pie: p.pie || '',
                            personajeEscena: p.personajeEscena || '',
                            proponentes: Array.isArray(p.proponentes) ? p.proponentes : [],
                            evento: p.evento || '',
                            personajesReaccionan: Array.isArray(p.personajesReaccionan) ? p.personajesReaccionan : [],
                            reactivos: Array.isArray(p.reactivos) ? p.reactivos : []
                        }));
                    },

                    prepararRelacionesUI() {
                        const existentesPorId = {};
                        (this.relacionesNodoPersonaje || []).forEach(r => {
                            existentesPorId[r.node_id] = r;
                        });

                        this.relacionesNodoPersonaje = this.nodosOrdenados().map(n => {
                            const previo = existentesPorId[n.node_id];
                            const guardado = this.relacionesMap[n.node_id] || { personajes: [], comentarios: '' };
                            const listaPers = previo ? [...(previo.personajes || [])] : [...(guardado.personajes || [])];
                            const persUnico = previo ? (previo.personajeUnico || '') : (listaPers[0] || '');

                            return {
                                node_id: n.node_id,
                                nombre: n.nombre,
                                tipo: n.tipo || 'nodo',
                                rol: this.rolDeNodo(n),
                                conectado: Boolean(n.conectado),
                                personajeUnico: persUnico,
                                personajes: listaPers,
                                comentarios: previo ? (previo.comentarios || '') : (guardado.comentarios || '')
                            };
                        });
                    },

                    async guardarPersonaje() {
                        const nombre = (this.nuevoPersonaje.nombre || '').trim();
                        const descripcion = (this.nuevoPersonaje.descripcion || '').trim();
                        if (!nombre) {
                            alert('Escribe un nombre para el personaje.');
                            return;
                        }
                        const res = await fetch('/api/dramaturgia/personajes', {
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
                        await this.cargarDramaturgia();
                    },

                    async eliminarPersonaje(nombre) {
                        const res = await fetch(`/api/dramaturgia/personajes/${encodeURIComponent(nombre)}`, {
                            method: 'DELETE'
                        });
                        if (!res.ok) {
                            const err = await res.json();
                            alert(err.detail || 'No se pudo eliminar el personaje.');
                            return;
                        }
                        await this.cargarDramaturgia();
                        this.prepararRelacionesUI();
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

                        const res = await fetch('/api/dramaturgia/relaciones', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ relaciones: payloadRelaciones })
                        });
                        if (!res.ok) {
                            const err = await res.json();
                            alert(err.detail || 'No se pudieron guardar las relaciones.');
                            return;
                        }
                        await this.cargarDramaturgia();
                        this.prepararRelacionesUI();
                        alert('¡Relaciones Nodo-Personaje guardadas en Modo Dramaturgia!');
                    },

                    agregarPie() {
                        this.piesDramaturgia.push({
                            id: 'pie_' + Date.now() + '_' + Math.random().toString(36).slice(2, 6),
                            pie: '',
                            personajeEscena: '',
                            proponentes: [],
                            evento: '',
                            personajesReaccionan: [],
                            reactivos: []
                        });
                    },

                    eliminarPie(idx) {
                        this.piesDramaturgia.splice(idx, 1);
                    },

                    personajesDeNodo(nodeId) {
                        const rel = this.relacionesMap[nodeId];
                        if (rel && Array.isArray(rel.personajes) && rel.personajes.length > 0) {
                            return rel.personajes;
                        }
                        const n = (this.nodos || []).find(item => item.node_id === nodeId);
                        return (n && Array.isArray(n.personajes)) ? n.personajes : [];
                    },

                    actualizarProponentesDePie(pieItem) {
                        const pers = (pieItem.personajeEscena || '').trim();
                        if (!pers) {
                            pieItem.proponentes = [];
                            return;
                        }
                        const previosPorId = {};
                        (pieItem.proponentes || []).forEach(p => {
                            previosPorId[p.node_id] = p;
                        });

                        pieItem.proponentes = this.nodosProponen()
                            .filter(n => this.personajesDeNodo(n.node_id).includes(pers))
                            .map(n => {
                                const prev = previosPorId[n.node_id];
                                return {
                                    node_id: n.node_id,
                                    nombre: n.nombre,
                                    multiples_activadores: this.tieneMultiplesActivadores(n),
                                    seleccionado: prev ? Boolean(prev.seleccionado) : false,
                                    disparador: prev ? (prev.disparador || '') : ''
                                };
                            });
                    },

                    sincronizarReactivosDePie(pieItem) {
                        const seleccionadosPers = pieItem.personajesReaccionan || [];
                        if (seleccionadosPers.length === 0) {
                            pieItem.reactivos = [];
                            return;
                        }
                        const previosPorId = {};
                        (pieItem.reactivos || []).forEach(r => {
                            previosPorId[r.node_id] = r;
                        });

                        const listaNueva = [];
                        (this.nodos || []).forEach(n => {
                            if (!this.puedeReaccionar(n)) return;
                            const persNodo = this.personajesDeNodo(n.node_id);
                            const coincidencia = seleccionadosPers.find(p => persNodo.includes(p));
                            if (!coincidencia) return;

                            const prev = previosPorId[n.node_id];
                            const paramsDefault = {};
                            (n.parametros_disponibles || []).forEach(pm => {
                                if (pm.tipo === 'int') {
                                    paramsDefault[pm.id] = pm.min ?? 0;
                                } else if (pm.tipo === 'lista') {
                                    paramsDefault[pm.id] = (pm.opciones && pm.opciones[0]) || '';
                                }
                            });

                            listaNueva.push({
                                node_id: n.node_id,
                                nombre: n.nombre,
                                personaje: coincidencia,
                                seleccionado: prev ? Boolean(prev.seleccionado) : false,
                                accion: prev ? (prev.accion || '') : '',
                                parametros_disponibles: n.parametros_disponibles || [],
                                parametros: prev ? { ...paramsDefault, ...(prev.parametros || {}) } : paramsDefault
                            });
                        });

                        pieItem.reactivos = listaNueva;
                    },

                    mensajeValidacionDramaturgia() {
                        const eventosVistos = {};
                        const teclasPorNodo = {};

                        for (let i = 0; i < (this.piesDramaturgia || []).length; i++) {
                            const p = this.piesDramaturgia[i];
                            const nombrePie = (p.pie || '').trim() || ('Pie #' + (i + 1));
                            const ev = (p.evento || '').trim();

                            if (ev) {
                                const key = ev.toLowerCase();
                                if (eventosVistos[key]) {
                                    return `Evento repetido: "${ev}" ya está usado en "${eventosVistos[key]}" y en "${nombrePie}".`;
                                }
                                eventosVistos[key] = nombrePie;
                            }

                            for (const prop of (p.proponentes || [])) {
                                if (!prop.seleccionado || !prop.multiples_activadores) continue;
                                const tecla = (prop.disparador || '').trim().slice(0, 1);
                                if (!tecla) continue;
                                if (!teclasPorNodo[prop.node_id]) teclasPorNodo[prop.node_id] = {};
                                if (teclasPorNodo[prop.node_id][tecla]) {
                                    return `Advertencia: la tecla "${tecla}" está repetida para "${prop.nombre}" entre "${teclasPorNodo[prop.node_id][tecla]}" y "${nombrePie}".`;
                                }
                                teclasPorNodo[prop.node_id][tecla] = nombrePie;
                            }
                        }
                        return '';
                    },

                    async guardarBorradorPies() {
                        const res = await fetch('/api/dramaturgia/pies/guardar', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ pies: this.piesDramaturgia })
                        });
                        if (res.ok) {
                            alert('Borrador de Puesta en escena guardado localmente.');
                        }
                    },

                    async aplicarConfigNodoIndividualDramaturgia(nodeId) {
                        const msgError = this.mensajeValidacionDramaturgia();
                        if (msgError) {
                            alert(msgError);
                            return;
                        }
                        const nodoObj = (this.nodos || []).find(n => n.node_id === nodeId);
                        const nombreNodo = nodoObj?.nombre || nodeId;
                        const confirmar = confirm(
                            '¿Deseas aplicar y publicar la configuración de "' + nombreNodo + '" en MQTT?'
                        );
                        if (!confirmar) return;

                        const res = await fetch(`/api/dramaturgia/aplicar-nodo/${encodeURIComponent(nodeId)}`, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ pies: this.piesDramaturgia })
                        });
                        const data = await res.json();
                        if (!res.ok) {
                            alert(data.detail || 'No se pudo enviar la configuración del nodo.');
                            return;
                        }
                        await this.cargarNodos();
                        alert('¡Configuración enviada para ' + data.topico_publicado + '!');
                    },

                    async aplicarConfiguracionEscenica() {
                        const msgError = this.mensajeValidacionDramaturgia();
                        if (msgError) {
                            alert(msgError);
                            return;
                        }
                        const confirmar = confirm(
                            '¿Deseas aplicar y publicar toda la configuración escénica (todos los Pies y nodos involucrados) en MQTT?'
                        );
                        if (!confirmar) return;

                        const res = await fetch('/api/dramaturgia/aplicar-escenica', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ pies: this.piesDramaturgia })
                        });
                        const data = await res.json();
                        if (!res.ok) {
                            alert(data.detail || 'No se pudo aplicar la configuración escénica.');
                            return;
                        }
                        await this.cargarNodos();
                        alert(`¡Configuración escénica aplicada! Se publicaron ${data.total_nodos} tópicos de nodo.`);
                    },

                    async borrarConfiguracionDramaturgia() {
                        const seguro = confirm(
                            '¿Borrar únicamente la configuración de Modo Dramaturgia (personajes creados, relaciones y Pies)? La configuración de Modo Normal permanecerá intacta.'
                        );
                        if (!seguro) return;

                        const res = await fetch('/api/reiniciar-dramaturgia', { method: 'POST' });
                        if (!res.ok) {
                            alert('No se pudo borrar la configuración de Modo Dramaturgia.');
                            return;
                        }
                        await this.cargarDramaturgia();
                        this.prepararRelacionesUI();
                        alert('Configuración de Modo Dramaturgia borrada.');
                    },

                    async emitirEventoModo(modo) {
                        const ev = (modo === 'dramaturgia' ? this.eventoPruebaDramaturgia : this.eventoPruebaNormal || '').trim();
                        if (!ev) {
                            alert('Selecciona un evento ya creado para probar.');
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
                        await this.cargarNodos();
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