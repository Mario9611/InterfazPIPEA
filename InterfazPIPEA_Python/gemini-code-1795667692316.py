import ast

with open("app.py", "r", encoding="utf-8") as f:
    src = f.read()

ast.parse(src)

# 1. Confirmación (Aceptar / Cancelar) antes de aplicar configuración en Modo Normal y Dramaturgia
old_norm_apply = '''                    async aplicarConfiguracionNormal() {
                        const errTecla = this.validarTeclasRepetidasNormal(this.nodoSelected);
                        if (errTecla) {
                            alert(errTecla);
                            return;
                        }
                        let res = await fetch(`/api/configurar/${this.nodoSelected.node_id}`, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify(this.nodoSelected)
                        });
                        let data = await res.json();
                        await this.cargarNodos();
                        this.seleccionarNodo(this.nodoSelected);
                        alert("¡Configuración de Modo Normal guardada y publicada en " + data.topico_publicado + "!");
                    },'''

new_norm_apply = '''                    async aplicarConfiguracionNormal() {
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
                    },'''

assert old_norm_apply in src, "old_norm_apply not found"
src = src.replace(old_norm_apply, new_norm_apply, 1)

old_dram_node_apply = '''                    async aplicarConfigNodoIndividualDramaturgia(nodeId) {
                        const msgError = this.mensajeValidacionDramaturgia();
                        if (msgError) {
                            alert(msgError);
                            return;
                        }
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
                    },'''

new_dram_node_apply = '''                    async aplicarConfigNodoIndividualDramaturgia(nodeId) {
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
                    },'''

assert old_dram_node_apply in src, "old_dram_node_apply not found"
src = src.replace(old_dram_node_apply, new_dram_node_apply, 1)

old_dram_esc_apply = '''                    async aplicarConfiguracionEscenica() {
                        const msgError = this.mensajeValidacionDramaturgia();
                        if (msgError) {
                            alert(msgError);
                            return;
                        }
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
                    },'''

new_dram_esc_apply = '''                    async aplicarConfiguracionEscenica() {
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
                    },'''

assert old_dram_esc_apply in src, "old_dram_esc_apply not found"
src = src.replace(old_dram_esc_apply, new_dram_esc_apply, 1)

# 2. Aislamiento de eventos en Prueba de Eventos entre Modo Normal y Modo Dramaturgia
old_ev_normal = '''                    obtenerEventosModoNormal() {
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
                    },'''

new_ev_normal = '''                    obtenerEventosModoNormal() {
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
                    },'''

assert old_ev_normal in src, "old_ev_normal not found"
src = src.replace(old_ev_normal, new_ev_normal, 1)

# 3. Evitar que on_message duplique en historial_mqtt cada vez que se suscribe o reconecta al broker
old_on_msg_cfg = '''        if msg.topic.startswith("pipea/config/"):
            registrar_en_historial_mqtt(msg.topic, payload)
            print(f"[MQTT RX CONFIG] {msg.topic} -> {json.dumps(payload, ensure_ascii=False)}")
            return'''

new_on_msg_cfg = '''        if msg.topic.startswith("pipea/config/"):
            print(f"[MQTT RX CONFIG] {msg.topic} -> {json.dumps(payload, ensure_ascii=False)}")
            return'''

assert old_on_msg_cfg in src, "old_on_msg_cfg not found"
src = src.replace(old_on_msg_cfg, new_on_msg_cfg, 1)

ast.parse(src)
with open("app.py", "w", encoding="utf-8") as f:
    f.write(src)

print("Cambios aplicados correctamente en app.py.")