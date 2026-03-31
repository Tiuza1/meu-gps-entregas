import json
import streamlit as st
import re
import os
import math

# =================================================================
# 0. PROCESSAMENTO DE AÇÕES DO POPUP (COMUNICAÇÃO JS -> PYTHON)
# =================================================================
# Captura cliques feitos dentro do HTML do mapa
query_params = st.query_params
if "action" in query_params and "id" in query_params:
    action = query_params["action"]
    item_id = query_params["id"]
    
    if action == "done":
        if item_id not in st.session_state.entregues_id:
            st.session_state.entregues_id.append(item_id)
    elif action == "delete":
        st.session_state.lista_pacotes = [p for p in st.session_state.lista_pacotes if p['id'] != item_id]
        if item_id in st.session_state.entregues_id:
            st.session_state.entregues_id.remove(item_id)
            
    # Limpa a URL e reinicia para atualizar o mapa e focar no GPS
    st.query_params.clear()
    st.rerun()

# =================================================================
# 1. CONFIGURAÇÃO E MENU ESCURO
# =================================================================
st.set_page_config(page_title="GPS Profissional", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    [data-testid="stHeader"], [data-testid="stToolbar"], footer { display: none !important; }

    [data-testid="stSidebarCollapsedControl"] {
        background-color: #1E1E1E !important;
        color: white !important;
        border-radius: 10px !important;
        width: 55px !important;
        height: 55px !important;
        top: 8px !important;
        left: 8px !important;
        z-index: 1000000 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        box-shadow: 0px 4px 10px rgba(0,0,0,0.4) !important;
    }
    [data-testid="stSidebarCollapsedControl"] svg { fill: white !important; width: 32px !important; height: 32px !important; }

    .block-container { padding: 4.5rem 0.5rem 0.5rem 0.5rem !important; }
    .stButton>button { width: 100% !important; height: 50px !important; border-radius: 12px !important; font-weight: bold !important; }
    iframe { border: none !important; border-radius: 15px !important; }
    </style>
""", unsafe_allow_html=True)

# =================================================================
# 2. MEMÓRIA DO SISTEMA
# =================================================================
FILE_SAVE = "progresso_final.json"

if 'lista_pacotes' not in st.session_state: st.session_state.lista_pacotes = []
if 'entregues_id' not in st.session_state: st.session_state.entregues_id = []
if 'ultima_pos' not in st.session_state: st.session_state.ultima_pos = None

def salvar_progresso():
    dados = {"lista_pacotes": st.session_state.lista_pacotes, "entregues_id": st.session_state.entregues_id, "ultima_pos": st.session_state.ultima_pos}
    with open(FILE_SAVE, "w") as f: json.dump(dados, f)

if not st.session_state.lista_pacotes and os.path.exists(FILE_SAVE):
    try:
        with open(FILE_SAVE, "r") as f:
            d = json.load(f)
            st.session_state.lista_pacotes = d.get("lista_pacotes", [])
            st.session_state.entregues_id = d.get("entregues_id", [])
            st.session_state.ultima_pos = d.get("ultima_pos")
    except: pass

@st.cache_data
def carregar_banco():
    try:
        with open('Lugares marcados.json', 'r', encoding='utf-8') as f:
            dados_j = json.load(f)
        return {str(l['properties'].get('title') or l['properties'].get('name')).strip(): 
                (l['geometry']['coordinates'][1], l['geometry']['coordinates'][0]) 
                for l in dados_j.get('features',[])}
    except: return {}

banco_total = carregar_banco()

# =================================================================
# 3. MENU LATERAL (CONFIGURAÇÕES)
# =================================================================
with st.sidebar:
    st.header("⚙️ Opções")
    if st.button("🗑️ LIMPAR TUDO"):
        if os.path.exists(FILE_SAVE): os.remove(FILE_SAVE)
        st.session_state.lista_pacotes = []; st.session_state.entregues_id = []; st.session_state.ultima_pos = None
        st.rerun()

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
# 5. LÓGICA DE QUAIS PONTOS MOSTRAR
# =================================================================
proximo_id = None
pontos_para_o_mapa = []

for p in st.session_state.lista_pacotes:
    coords = banco_total.get(p['nome'], (0,0))
    concluido = p['id'] in st.session_state.entregues_id
    cor = "#28a745" if concluido else "#dc3545"
    pontos_para_o_mapa.append({"id": p['id'], "lat": coords[0], "lng": coords[1], "nome": p['nome'], "concluido": concluido, "cor": cor})

pendentes = [p for p in pontos_para_o_mapa if not p['concluido']]
if st.session_state.ultima_pos and pendentes:
    m_dist = float('inf')
    for p in pendentes:
        d = math.sqrt((st.session_state.ultima_pos[0]-p['lat'])**2 + (st.session_state.ultima_pos[1]-p['lng'])**2)
        if d < m_dist: 
            m_dist = d
            proximo_id = p['id']

for p in pontos_para_o_mapa:
    if p['id'] == proximo_id: p['cor'] = "#fd7e14"
    num = re.findall(r'\d+', p['nome'])[0] if re.findall(r'\d+', p['nome']) else p['nome'][:2]
    p['txt'] = "✔" if p['concluido'] else num

# =================================================================
# 6. O MAPA RÁPIDO COM POPUP TRANSPARENTE
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
        /* Estilo do Popup Transparente */
        .leaflet-popup-content-wrapper {{
            background: rgba(255, 255, 255, 0.4) !important;
            backdrop-filter: blur(10px);
            border-radius: 15px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
            color: #000;
        }}
        .leaflet-popup-tip {{ background: rgba(255, 255, 255, 0.4) !important; }}
        .popup-container {{
            display: flex; flex-direction: column; gap: 8px; padding: 5px; min-width: 120px;
        }}
        .popup-title {{ font-weight: bold; text-align: center; margin-bottom: 5px; font-size: 14px; color: #1E1E1E; }}
        .btn {{
            border: none; border-radius: 8px; padding: 10px; color: white;
            font-weight: bold; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 8px;
            transition: 0.2s; font-size: 12px;
        }}
        .btn-gps {{ background: #1E1E1E; }}
        .btn-done {{ background: #28a745; }}
        .btn-del {{ background: #dc3545; }}
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

        function sendAction(action, id) {{
            const url = new URL(window.parent.location.href);
            url.searchParams.set("action", action);
            url.searchParams.set("id", id);
            window.parent.location.href = url.href;
        }}

        pontos.forEach(function(p) {{
            var icon = L.divIcon({{
                className: '',
                html: '<div class="pin" style="background:'+p.cor+'; opacity:'+(p.concluido ? 0.6 : 1)+'">'+p.txt+'</div>',
                iconSize: [38, 38], iconAnchor: [19, 19]
            }});

            var popupContent = `
                <div class="popup-container">
                    <div class="popup-title">${{p.nome}}</div>
                    <button class="btn btn-gps" onclick="window.open('https://www.google.com/maps/dir/?api=1&destination=${{p.lat}},${{p.lng}}')">🚀 GPS</button>
                    <button class="btn btn-done" onclick="sendAction('done', '${{p.id}}')">✅ FEITO</button>
                    <button class="btn btn-del" onclick="sendAction('delete', '${{p.id}}')">🗑️ EXCLUIR</button>
                </div>
            `;

            L.marker([p.lat, p.lng], {{icon: icon}})
             .addTo(map)
             .bindPopup(popupContent);
        }});

        function onLocationFound(e) {{
            if (!userMarker) {{
                userMarker = L.circleMarker(e.latlng, {{
                    radius: 9, fillColor: "#4285F4", color: "white", weight: 3, opacity: 1, fillOpacity: 1
                }}).addTo(map);
                // No início ou após rerun, foca no GPS com zoom médio
                map.setView(e.latlng, 16);
            }} else {{
                userMarker.setLatLng(e.latlng);
            }}
        }}
        map.on('locationfound', onLocationFound);
        map.locate({{ watch: true, enableHighAccuracy: true, setView: false }});
    </script>
</body>
</html>
"""

st.components.v1.html(mapa_html, height=600)

# Painel Informativo (Opcional, agora que temos Popup)
if pendentes:
    p_atual = next(p for p in pontos_para_o_mapa if p['id'] == proximo_id) if proximo_id else pendentes[0]
    st.info(f"💡 Sugestão: **{p_atual['nome']}**")

salvar_progresso()
