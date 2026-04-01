import json
import streamlit as st
import re
import os
import math

# =================================================================
# 1. CONFIGURAÇÃO E CSS
# =================================================================
st.set_page_config(page_title="GPS Profissional", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    [data-testid="stHeader"], [data-testid="stSidebar"], [data-testid="stToolbar"], footer { display: none !important; }
    .block-container { padding: 0.5rem !important; max-width: 100% !important; }
    .stButton>button { border-radius: 12px !important; height: 50px !important; font-weight: bold !important; }
    iframe { border-radius: 20px !important; border: 1px solid #333 !important; margin-bottom: 10px !important; }
    
    /* Estilo do Painel de Ação Inferior */
    .action-panel {
        background-color: #1E1E26;
        padding: 15px;
        border-radius: 15px;
        border: 1px solid #333;
        margin-top: 10px;
    }
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
    dados = {
        "lista_pacotes": st.session_state.lista_pacotes, 
        "entregues_id": st.session_state.entregues_id, 
        "ultima_pos": st.session_state.ultima_pos
    }
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
# 3. BUSCA E ADICIONAR
# =================================================================
c1, c2 = st.columns([5, 1])
with c1:
    busca = st.selectbox("Busca", options=["(Adicionar...)"] + list(banco_total.keys()), label_visibility="collapsed", key="search")
with c2:
    if st.button("➕", key="add_btn"):
        if busca and busca != "(Adicionar...)":
            nid = f"P_{len(st.session_state.lista_pacotes)}_{int(math.fmod(math.pow(len(st.session_state.lista_pacotes),2),100))}"
            st.session_state.lista_pacotes.append({"id": nid, "nome": busca})
            st.session_state.ultima_pos = banco_total[busca]
            salvar_progresso()
            st.rerun()

# =================================================================
# 4. PREPARAÇÃO DO MAPA
# =================================================================
pontos_para_o_mapa = []
pendentes = []

for p in st.session_state.lista_pacotes:
    coords = banco_total.get(p['nome'], (0,0))
    concluido = p['id'] in st.session_state.entregues_id
    item = {"id": p['id'], "lat": coords[0], "lng": coords[1], "nome": p['nome'], "concluido": concluido}
    pontos_para_o_mapa.append(item)
    if not concluido: pendentes.append(item)

# Lógica de proximidade para cor Laranja
proximo_id = None
if st.session_state.ultima_pos and pendentes:
    m_dist = float('inf')
    for p in pendentes:
        d = math.sqrt((st.session_state.ultima_pos[0]-p['lat'])**2 + (st.session_state.ultima_pos[1]-p['lng'])**2)
        if d < m_dist: 
            m_dist = d
            proximo_id = p['id']

for p in pontos_para_o_mapa:
    if p['concluido']: p['cor'] = "#28a745"
    elif p['id'] == proximo_id: p['cor'] = "#fd7e14"
    else: p['cor'] = "#dc3545"
    
    num = re.findall(r'\d+', p['nome'])[0] if re.findall(r'\d+', p['nome']) else p['nome'][:2]
    p['txt'] = "✔" if p['concluido'] else num

centro = st.session_state.ultima_pos if st.session_state.ultima_pos else [-16.15, -47.96]

# Gerar HTML do Mapa (Sem Popups internos)
mapa_html = f"""
<!DOCTYPE html>
<html>
<head>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        #map {{ height: 100vh; width: 100%; background: #222; }}
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
        L.tileLayer('http://{{s}}.google.com/vt/lyrs=m&x={{x}}&y={{y}}&z={{z}}', {{ subdomains:['mt0','mt1','mt2','mt3'] }}).addTo(map);

        var pontos = {json.dumps(pontos_para_o_mapa)};
        pontos.forEach(function(p) {{
            var icon = L.divIcon({{
                className: '',
                html: '<div class="pin" style="background:'+p.cor+'; opacity:'+(p.concluido ? 0.6 : 1)+'">'+p.txt+'</div>',
                iconSize: [38, 38], iconAnchor: [19, 19]
            }});
            var marker = L.marker([p.lat, p.lng], {{icon: icon}}).addTo(map);
            
            // AO CLICAR: Atualiza a URL do navegador principal
            marker.on('click', function() {{
                window.top.location.href = '?selecionado=' + p.id;
            }});
        }});
    </script>
</body>
</html>
"""

st.components.v1.html(mapa_html, height=450)

# =================================================================
# 5. PAINEL DE AÇÃO FIXO (O "POPUP" DE BAIXO)
# =================================================================
id_selecionado = st.query_params.get("selecionado")

if id_selecionado:
    # Encontrar os dados do ponto clicado
    ponto_atual = next((p for p in pontos_para_o_mapa if p['id'] == id_selecionado), None)
    
    if ponto_atual:
        with st.container():
            st.markdown(f"""
                <div class="action-panel">
                    <div style="color:white; font-size:18px; font-weight:bold; margin-bottom:10px;">
                        📍 {ponto_atual['nome']}
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            col_gps, col_done = st.columns(2)
            
            with col_gps:
                link_gps = f"https://www.google.com/maps/dir/?api=1&destination={ponto_atual['lat']},{ponto_atual['lng']}"
                st.link_button("🚀 ABRIR GPS", link_gps, use_container_width=True)
            
            with col_done:
                if not ponto_atual['concluido']:
                    if st.button("✅ CONCLUIR", type="primary", use_container_width=True):
                        st.session_state.entregues_id.append(ponto_atual['id'])
                        st.session_state.ultima_pos = (ponto_atual['lat'], ponto_atual['lng'])
                        salvar_progresso()
                        # Limpa seleção e recarrega
                        st.query_params.clear()
                        st.rerun()
                else:
                    st.button("✔ ENTREGUE", disabled=True, use_container_width=True)
            
            if st.button("✖ FECHAR PAINEL", use_container_width=True):
                st.query_params.clear()
                st.rerun()

# =================================================================
# 6. RODAPÉ (GERENCIAMENTO)
# =================================================================
st.write("---")
if st.button("🗑️ LIMPAR TODA A ROTA", use_container_width=True):
    if os.path.exists(FILE_SAVE): os.remove(FILE_SAVE)
    st.session_state.lista_pacotes = []
    st.session_state.entregues_id = []
    st.session_state.ultima_pos = None
    st.query_params.clear()
    st.rerun()
