# =================================================================
# 4. BUSCA E ADICIONAR
# =================================================================
c1, c2 = st.columns([5, 1])
with c1:
    busca = st.selectbox("Busca", options=["(Adicionar...)"] + list(banco_total.keys()), label_visibility="collapsed")
with c2:
    if st.button("➕"):
        if busca and busca != "(Adicionar...)":
            nid = f"{busca}_{len(st.session_state.lista_pacotes)}"
            st.session_state.lista_pacotes.append({"id": nid, "nome": busca})
            st.session_state.ultima_pos = banco_total[busca]
            salvar_progresso(); st.rerun()

# =================================================================
# 5. LÓGICA DE PONTOS E SELEÇÃO (CORRIGIDO)
# =================================================================
id_selecionado_via_mapa = st.query_params.get("id")
proximo_id_automatico = None
pontos_para_o_mapa = []

# Monta a lista de pontos para o mapa
for p in st.session_state.lista_pacotes:
    coords = banco_total.get(p['nome'], (0,0))
    concluido = p['id'] in st.session_state.entregues_id
    cor = "#28a745" if concluido else "#dc3545" # Verde se ok, Vermelho se pendente
    pontos_para_o_mapa.append({
        "id": p['id'], "lat": coords[0], "lng": coords[1], 
        "nome": p['nome'], "concluido": concluido, "cor": cor
    })

# Descobre quem é o mais próximo (automático)
pendentes = [p for p in pontos_para_o_mapa if not p['concluido']]
if st.session_state.ultima_pos and pendentes:
    m_dist = float('inf')
    for p in pendentes:
        d = math.sqrt((st.session_state.ultima_pos[0]-p['lat'])**2 + (st.session_state.ultima_pos[1]-p['lng'])**2)
        if d < m_dist: 
            m_dist = d
            proximo_id_automatico = p['id']

# Define quem será destacado (id_foco)
id_foco = id_selecionado_via_mapa if id_selecionado_via_mapa else proximo_id_automatico

# Aplica cor laranja no ponto em foco e define o texto do PIN
for p in pontos_para_o_mapa:
    if p['id'] == id_foco: 
        p['cor'] = "#fd7e14"
    num = re.findall(r'\d+', p['nome'])[0] if re.findall(r'\d+', p['nome']) else p['nome'][:2]
    p['txt'] = "✔" if p['concluido'] else num

# =================================================================
# 6. O MAPA (COM CLIQUE)
# =================================================================
centro = st.session_state.ultima_pos if st.session_state.ultima_pos else [-16.15, -47.96]

mapa_html = f"""
<!DOCTYPE html>
<html>
<head>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        #map {{ height: 100vh; width: 100%; background: #e5e3df; }}
        body {{ margin: 0; padding: 0; }}
        .pin {{
            width: 38px; height: 38px; border-radius: 50%;
            display: flex; align-items: center; justify-content: center;
            color: white; font-weight: bold; font-family: sans-serif;
            border: 2px solid white; box-shadow: 0 2px 5px rgba(0,0,0,0.3);
        }}
    </style>
</head>
<body>
    <div id="map"></div>
    <script>
        var map = L.map('map', {{ zoomControl: false }}).setView([{centro[0]}, {centro[1]}], 16);
        L.tileLayer('http://{{s}}.google.com/vt/lyrs=m&x={{x}}&y={{y}}&z={{z}}', {{
            maxZoom: 20, subdomains:['mt0','mt1','mt2','mt3']
        }}).addTo(map);

        var pontos = {json.dumps(pontos_para_o_mapa)};
        var userMarker;

        pontos.forEach(function(p) {{
            var icon = L.divIcon({{
                className: '',
                html: '<div class="pin" style="background:'+p.cor+'; opacity:'+(p.concluido ? 0.6 : 1)+'">'+p.txt+'</div>',
                iconSize: [38, 38], iconAnchor: [19, 19]
            }});
            var m = L.marker([p.lat, p.lng], {{icon: icon}}).addTo(map);
            m.on('click', function() {{
                const url = new URL(window.parent.location.href);
                url.searchParams.set('id', p.id);
                window.parent.location.href = url.href;
            }});
        }});

        function onLocationFound(e) {{
            if (!userMarker) {{
                userMarker = L.circleMarker(e.latlng, {{ radius: 9, fillColor: "#4285F4", color: "white", weight: 3, opacity: 1, fillOpacity: 1 }}).addTo(map);
            }} else {{ userMarker.setLatLng(e.latlng); }}
        }}
        map.on('locationfound', onLocationFound);
        map.locate({{ watch: true, enableHighAccuracy: true, setView: false }});
    </script>
</body>
</html>
"""

st.components.v1.html(mapa_html, height=500)

# =================================================================
# 7. PAINEL DE CONTROLE (AGORA SEM REPETIÇÃO)
# =================================================================
if pendentes:
    # Pega o objeto do ponto em foco
    p_atual = next((p for p in pontos_para_o_mapa if p['id'] == id_foco), pendentes[0])
    
    st.write("---")
    tipo_txt = "📍 Selecionado:" if id_selecionado_via_mapa else "📍 Próximo:"
    st.info(f"**{tipo_txt}** {p_atual['nome']}")
    
    c1, c2 = st.columns(2)
    with c1:
        st.link_button("🚀 ABRIR GPS", f"https://www.google.com/maps/dir/?api=1&destination={p_atual['lat']},{p_atual['lng']}", use_container_width=True)
    with c2:
        if st.button("✅ CONCLUIR", use_container_width=True, type="primary"):
            st.session_state.entregues_id.append(p_atual['id'])
            st.session_state.ultima_pos = [p_atual['lat'], p_atual['lng']]
            st.query_params.clear()
            salvar_progresso(); st.rerun()

st.write("---")

# =================================================================
# 8. RODAPÉ (SALVAR E LIMPAR)
# =================================================================
col_s, col_l = st.columns(2)
with col_s:
    if st.session_state.lista_pacotes:
        rota_txt = "📋 ROTA\n" + "\n".join([f"{'✅' if p['id'] in st.session_state.entregues_id else '❌'} {p['nome']}" for p in st.session_state.lista_pacotes])
        st.download_button("💾 SALVAR TXT", rota_txt, file_name="rota.txt", use_container_width=True)
with col_l:
    if st.button("🗑️ LIMPAR MAPA", use_container_width=True):
        if os.path.exists(FILE_SAVE): os.remove(FILE_SAVE)
        st.session_state.lista_pacotes = []; st.session_state.entregues_id = []; st.session_state.ultima_pos = None; st.query_params.clear(); st.rerun()
