import json
import streamlit as st
import re
import os
import math

# 1. CONFIGURAÇÃO (Deve ser a primeira coisa)
st.set_page_config(page_title="GPS Profissional", layout="wide", initial_sidebar_state="collapsed")

# 2. LIMPEZA DE UI (CSS)
st.markdown("""
    <style>
    [data-testid="stHeader"], [data-testid="stSidebar"], [data-testid="stToolbar"], footer { display: none !important; }
    .block-container { padding: 0.5rem !important; max-width: 100% !important; }
    .stButton>button { border-radius: 10px !important; height: 45px !important; font-weight: bold !important; }
    iframe { border-radius: 20px !important; border: 1px solid #333 !important; }
    
    /* Estilo do Popup */
    .leaflet-popup-content-wrapper { border-radius: 12px !important; background: #262730 !important; color: white !important; }
    .leaflet-popup-tip { background: #262730 !important; }
    .popup-btn {
        display: block; width: 100%; text-align: center;
        padding: 12px 0; margin-top: 10px; border-radius: 8px;
        text-decoration: none; color: white !important; font-family: sans-serif; font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

# 3. INICIALIZAÇÃO DE MEMÓRIA
FILE_SAVE = "progresso_final.json"

if 'lista_pacotes' not in st.session_state:
    if os.path.exists(FILE_SAVE):
        try:
            with open(FILE_SAVE, "r") as f:
                d = json.load(f)
                st.session_state.lista_pacotes = d.get("lista_pacotes", [])
                st.session_state.entregues_id = d.get("entregues_id", [])
                st.session_state.ultima_pos = d.get("ultima_pos")
        except:
            st.session_state.lista_pacotes = []
            st.session_state.entregues_id = []
            st.session_state.ultima_pos = None
    else:
        st.session_state.lista_pacotes = []
        st.session_state.entregues_id = []
        st.session_state.ultima_pos = None

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

# 4. LÓGICA DE CLIQUE NO MAPA (CONCLUIR)
# Processa o clique ANTES de desenhar qualquer coisa na tela
query = st.query_params
if "concluir" in query:
    id_alvo = query["concluir"]
    if id_alvo not in st.session_state.entregues_id:
        st.session_state.entregues_id.append(id_alvo)
        # Salva a posição do ponto concluído como última posição
        for p in st.session_state.lista_pacotes:
            if p['id'] == id_alvo:
                st.session_state.ultima_pos = banco_total.get(p['nome'])
        
        # Salva no arquivo
        dados = {"lista_pacotes": st.session_state.lista_pacotes, "entregues_id": st.session_state.entregues_id, "ultima_pos": st.session_state.ultima_pos}
        with open(FILE_SAVE, "w") as f: json.dump(dados, f)
        
    st.query_params.clear()
    st.rerun()

# =================================================================
# 5. DESENHO DA INTERFACE (AQUI COMEÇA A TELA)
# =================================================================

# --- BLOCO DE BUSCA ---
c1, c2 = st.columns([5, 1])
with c1:
    # Use uma key única para evitar duplicação interna
    busca = st.selectbox("Busca", options=["(Adicionar...)"] + list(banco_total.keys()), label_visibility="collapsed", key="main_search")
with c2:
    if st.button("➕", key="btn_add_principal"):
        if busca and busca != "(Adicionar...)":
            nid = f"{busca}_{len(st.session_state.lista_pacotes)}"
            st.session_state.lista_pacotes.append({"id": nid, "nome": busca})
            st.session_state.ultima_pos = banco_total[busca]
            # Salvar
            dados = {"lista_pacotes": st.session_state.lista_pacotes, "entregues_id": st.session_state.entregues_id, "ultima_pos": st.session_state.ultima_pos}
            with open(FILE_SAVE, "w") as f: json.dump(dados, f)
            st.rerun()

# --- PREPARAÇÃO DOS DADOS DO MAPA ---
pontos_mapa = []
proximo_id = None

for p in st.session_state.lista_pacotes:
    coords = banco_total.get(p['nome'], (0,0))
    concluido = p['id'] in st.session_state.entregues_id
    cor = "#28a745" if concluido else "#dc3545"
    pontos_mapa.append({"id": p['id'], "lat": coords[0], "lng": coords[1], "nome": p['nome'], "concluido": concluido, "cor": cor})

# Achar o laranja (mais próximo)
pendentes = [p for p in pontos_mapa if not p['concluido']]
if st.session_state.ultima_pos and pendentes:
    m_dist = float('inf')
    for p in pendentes:
        d = math.sqrt((st.session_state.ultima_pos[0]-p['lat'])**2 + (st.session_state.ultima_pos[1]-p['lng'])**2)
        if d < m_dist: 
            m_dist = d
            proximo_id = p['id']

for p in pontos_mapa:
    if p['id'] == proximo_id: p['cor'] = "#fd7e14"
    num = re.findall(r'\d+', p['nome'])[0] if re.findall(r'\d+', p['nome']) else p['nome'][:2]
    p['txt'] = "✔" if p['concluido'] else num

# --- DESENHO DO MAPA ---
centro = st.session_state.ultima_pos if st.session_state.ultima_pos else [-16.15, -47.96]
mapa_html = f"""
<!DOCTYPE html>
<html>
<head>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>#map {{ height: 100vh; width: 100%; background: #121212; }} body {{ margin: 0; }}
    .pin {{ width: 38px; height: 38px; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; border: 2px solid white; box-shadow: 0 2px 5px rgba(0,0,0,0.3); }}
    </style>
</head>
<body>
    <div id="map"></div>
    <script>
        var map = L.map('map', {{ zoomControl: false }}).setView([{centro[0]}, {centro[1]}], 16);
        L.tileLayer('http://{{s}}.google.com/vt/lyrs=m&x={{x}}&y={{y}}&z={{z}}', {{ maxZoom: 20, subdomains:['mt0','mt1','mt2','mt3'] }}).addTo(map);

        var pontos = {json.dumps(pontos_mapa)};
        pontos.forEach(function(p) {{
            var icon = L.divIcon({{ className: '', html: '<div class="pin" style="background:'+p.cor+'; opacity:'+(p.concluido ? 0.6 : 1)+'">'+p.txt+'</div>', iconSize: [38, 38], iconAnchor: [19, 19] }});
            var content = '<div style="min-width:160px;"><strong style="font-size:16px;">'+p.nome+'</strong>' +
                '<a href="https://www.google.com/maps/dir/?api=1&destination='+p.lat+','+p.lng+'" target="_blank" class="popup-btn" style="background:#4285F4;">🚀 ABRIR GPS</a>';
            if (!p.concluido) {{ content += '<a href="?concluir='+p.id+'" target="_self" class="popup-btn" style="background:#28a745;">✅ CONCLUIR</a>'; }}
            content += '</div>';
            L.marker([p.lat, p.lng], {{icon: icon}}).addTo(map).bindPopup(content);
        }});

        var userMarker;
        map.on('locationfound', function(e) {{
            if (!userMarker) {{ userMarker = L.circleMarker(e.latlng, {{ radius: 9, fillColor: "#4285F4", color: "white", weight: 3, opacity: 1, fillOpacity: 1 }}).addTo(map); }}
            else {{ userMarker.setLatLng(e.latlng); }}
        }});
        map.locate({{ watch: true, enableHighAccuracy: true }});
    </script>
</body>
</html>
"""
st.components.v1.html(mapa_html, height=500)

# --- RODAPÉ ---
st.write("---")
col_txt, col_limpar = st.columns(2)
with col_txt:
    if st.session_state.lista_pacotes:
        resumo = "ROTA:\\n" + "\\n".join([f"{'OK' if p['id'] in st.session_state.entregues_id else '..'} {p['nome']}" for p in st.session_state.lista_pacotes])
        st.download_button("💾 SALVAR TXT", resumo, file_name="rota.txt", use_container_width=True)
with col_limpar:
    if st.button("🗑️ LIMPAR TUDO", use_container_width=True):
        if os.path.exists(FILE_SAVE): os.remove(FILE_SAVE)
        st.session_state.lista_pacotes = []
        st.session_state.entregues_id = []
        st.session_state.ultima_pos = None
        st.rerun()
