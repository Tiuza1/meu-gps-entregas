import json
import streamlit as st
import re
import os
import math

# =================================================================
# 1. INICIALIZAÇÃO DE MEMÓRIA
# =================================================================
FILE_SAVE = "progresso_final.json"

if 'lista_pacotes' not in st.session_state: st.session_state.lista_pacotes = []
if 'entregues_id' not in st.session_state: st.session_state.entregues_id = []
if 'ultima_pos' not in st.session_state: st.session_state.ultima_pos = None

# Função para carregar o banco de dados (colocada antes para ser usada no processamento)
def carregar_banco():
    try:
        with open('Lugares marcados.json', 'r', encoding='utf-8') as f:
            dados_j = json.load(f)
        return {str(l['properties'].get('title') or l['properties'].get('name')).strip(): 
                (l['geometry']['coordinates'][1], l['geometry']['coordinates'][0]) 
                for l in dados_j.get('features',[])}
    except: return {}

banco_total = carregar_banco()

if not st.session_state.lista_pacotes and os.path.exists(FILE_SAVE):
    try:
        with open(FILE_SAVE, "r") as f:
            d = json.load(f)
            st.session_state.lista_pacotes = d.get("lista_pacotes", [])
            st.session_state.entregues_id = d.get("entregues_id", [])
            st.session_state.ultima_pos = d.get("ultima_pos")
    except: pass

def salvar_progresso():
    dados = {
        "lista_pacotes": st.session_state.lista_pacotes, 
        "entregues_id": st.session_state.entregues_id, 
        "ultima_pos": st.session_state.ultima_pos
    }
    with open(FILE_SAVE, "w") as f: json.dump(dados, f)

# =================================================================
# 2. PROCESSAMENTO DE AÇÕES (FEITO / EXCLUIR) -> AGORA APAGAM DO MAPA
# =================================================================
qp = st.query_params
if "action" in qp and "id" in qp:
    action = qp["action"]
    item_id = qp["id"]
    
    # Busca o ponto antes de qualquer alteração
    ponto_atual = next((p for p in st.session_state.lista_pacotes if p['id'] == item_id), None)
    
    if action == "done":
        if ponto_atual:
            # 1. Atualiza a última posição para o cálculo do próximo destino
            coords = banco_total.get(ponto_atual['nome'])
            if coords:
                st.session_state.ultima_pos = coords
            
            # 2. Adiciona ao histórico de entregues
            if item_id not in st.session_state.entregues_id:
                st.session_state.entregues_id.append(item_id)
            
            # 3. REMOVE da lista principal (isso faz sumir do mapa)
            st.session_state.lista_pacotes = [p for p in st.session_state.lista_pacotes if p['id'] != item_id]

    elif action == "delete":
        # Apenas remove da lista principal e do histórico
        st.session_state.lista_pacotes = [p for p in st.session_state.lista_pacotes if p['id'] != item_id]
        if item_id in st.session_state.entregues_id:
            st.session_state.entregues_id.remove(item_id)
            
    salvar_progresso()
    st.query_params.clear()
    st.rerun()

# =================================================================
# 3. CONFIGURAÇÃO DE TELA E CSS
# =================================================================
st.set_page_config(page_title="GPS Profissional", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    [data-testid="stHeader"],[data-testid="stToolbar"], footer { display: none !important; }
    [data-testid="stSidebarCollapsedControl"] {
        background-color: #1E1E1E !important; color: white !important; border-radius: 10px !important;
        width: 55px !important; height: 55px !important; top: 8px !important; left: 8px !important;
        z-index: 1000000 !important; display: flex !important; align-items: center !important; justify-content: center !important;
        box-shadow: 0px 4px 10px rgba(0,0,0,0.4) !important;
    }
    [data-testid="stSidebarCollapsedControl"] svg { fill: white !important; width: 32px !important; height: 32px !important; }
    .block-container { padding: 4.5rem 0.5rem 0.5rem 0.5rem !important; }
    iframe { border: none !important; border-radius: 15px !important; }
    </style>
""", unsafe_allow_html=True)

# =================================================================
# 4. MENU LATERAL E BUSCA
# =================================================================
with st.sidebar:
    st.header("⚙️ Opções")
    if st.button("🗑️ LIMPAR TUDO"):
        if os.path.exists(FILE_SAVE): os.remove(FILE_SAVE)
        st.session_state.lista_pacotes = []; st.session_state.entregues_id = []; st.session_state.ultima_pos = None
        st.rerun()

c1, c2 = st.columns([5, 1])
with c1:
    busca = st.selectbox("Busca", options=["(Adicionar...)"] + list(banco_total.keys()), label_visibility="collapsed")
with c2:
    if st.button("➕"):
        if busca and busca != "(Adicionar...)":
            nid = f"{busca}_{len(st.session_state.lista_pacotes)}_{math.floor(st.session_state.ultima_pos[0] if st.session_state.ultima_pos else 0)}"
            st.session_state.lista_pacotes.append({"id": nid, "nome": busca})
            salvar_progresso(); st.rerun()

# =================================================================
# 5. LÓGICA DE PONTOS (CÁLCULO DO MAIS PRÓXIMO)
# =================================================================
pontos_para_o_mapa = []
for p in st.session_state.lista_pacotes:
    coords = banco_total.get(p['nome'], (0,0))
    # Como agora removemos os feitos, todos aqui são Pendentes (Vermelhos)
    pontos_para_o_mapa.append({
        "id": p['id'], "lat": coords[0], "lng": coords[1], 
        "nome": p['nome'], "cor": "#dc3545"
    })

proximo_id = None
if st.session_state.ultima_pos and pontos_para_o_mapa:
    m_dist = float('inf')
    for p in pontos_para_o_mapa:
        d = math.sqrt((st.session_state.ultima_pos[0]-p['lat'])**2 + (st.session_state.ultima_pos[1]-p['lng'])**2)
        if d < m_dist: 
            m_dist = d
            proximo_id = p['id']

for p in pontos_para_o_mapa:
    if p['id'] == proximo_id: p['cor'] = "#fd7e14" # Laranja para o próximo
    num = re.findall(r'\d+', p['nome'])[0] if re.findall(r'\d+', p['nome']) else p['nome'][:2]
    p['txt'] = num

# =================================================================
# 6. MAPA
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
            font-size: 16px;
        }}
        .leaflet-popup-content-wrapper {{
            background: rgba(255, 255, 255, 0.7) !important;
            backdrop-filter: blur(12px); border-radius: 15px;
        }}
        .popup-container {{ display: flex; flex-direction: column; gap: 8px; padding: 5px; min-width: 140px; }}
        .popup-title {{ font-weight: bold; text-align: center; font-size: 14px; font-family: sans-serif; }}
        .btn {{
            text-decoration: none; border-radius: 8px; padding: 12px; color: white;
            font-weight: bold; cursor: pointer; display: flex; align-items: center; justify-content: center;
            font-size: 13px; font-family: sans-serif;
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
        pontos.forEach(function(p) {{
            var icon = L.divIcon({{
                className: '',
                html: '<div class="pin" style="background:'+p.cor+'">'+p.txt+'</div>',
                iconSize: [38, 38], iconAnchor: [19, 19]
            }});

            var popupContent = `
                <div class="popup-container">
                    <div class="popup-title">${{p.nome}}</div>
                    <a href="https://www.google.com/maps/dir/?api=1&destination=${{p.lat}},${{p.lng}}" target="_blank" class="btn btn-gps">🚀 GPS</a>
                    <a href="#" onclick="window.parent.location.search='?action=done&id=${{p.id}}'; return false;" class="btn btn-done">✅ FEITO</a>
                    <a href="#" onclick="window.parent.location.search='?action=delete&id=${{p.id}}'; return false;" class="btn btn-del">🗑️ EXCLUIR</a>
                </div>
            `;

            L.marker([p.lat, p.lng], {{icon: icon}}).addTo(map).bindPopup(popupContent);
        }});

        map.locate({{ watch: true, enableHighAccuracy: true, setView: false }});
        map.on('locationfound', function(e) {{
            L.circleMarker(e.latlng, {{ radius: 8, fillColor: "#4285F4", color: "white", fillOpacity: 1 }}).addTo(map);
        }});
    </script>
</body>
</html>
"""

st.components.v1.html(mapa_html, height=600)

if pontos_para_o_mapa:
    p_atual = next((p for p in pontos_para_o_mapa if p['id'] == proximo_id), pontos_para_o_mapa[0])
    st.info(f"💡 Próxima parada sugerida: **{p_atual['nome']}**")
