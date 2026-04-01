import json
import streamlit as st
import re
import os
import math
import time

# 1. CONFIGURAÇÃO (Sempre a primeira linha)
st.set_page_config(page_title="GPS Profissional", layout="wide", initial_sidebar_state="collapsed")

# 2. FUNÇÕES DE APOIO
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
FILE_SAVE = "progresso_final.json"

def salvar_progresso():
    dados = {"lista_pacotes": st.session_state.lista_pacotes, 
             "entregues_id": st.session_state.entregues_id, 
             "ultima_pos": st.session_state.ultima_pos}
    with open(FILE_SAVE, "w") as f: json.dump(dados, f)

# 3. INICIALIZAÇÃO DO ESTADO
if 'lista_pacotes' not in st.session_state: st.session_state.lista_pacotes = []
if 'entregues_id' not in st.session_state: st.session_state.entregues_id = []
if 'ultima_pos' not in st.session_state: st.session_state.ultima_pos = None

# Carregar do arquivo se estiver vazio
if not st.session_state.lista_pacotes and os.path.exists(FILE_SAVE):
    try:
        with open(FILE_SAVE, "r") as f:
            d = json.load(f)
            st.session_state.lista_pacotes = d.get("lista_pacotes", [])
            st.session_state.entregues_id = d.get("entregues_id", [])
            st.session_state.ultima_pos = d.get("ultima_pos")
    except: pass

# =================================================================
# 4. LÓGICA DE CLIQUE NO MAPA (RESOLVE DUPLICAÇÃO E ALEATORIEDADE)
# =================================================================
# Verificamos a URL antes de desenhar qualquer menu na tela
if "concluir" in st.query_params:
    id_clicado = st.query_params["concluir"]
    if id_clicado not in st.session_state.entregues_id:
        st.session_state.entregues_id.append(id_clicado)
        # Atualiza a última posição para onde foi o clique
        for p in st.session_state.lista_pacotes:
            if p['id'] == id_clicado:
                st.session_state.ultima_pos = banco_total.get(p['nome'])
        salvar_progresso()
    
    # LIMPA A URL E RECOMEÇA (Evita o "Inception" e a duplicação)
    st.query_params.clear()
    st.rerun()

# 5. ESTILO CSS
st.markdown("""
    <style>
    [data-testid="stHeader"], [data-testid="stSidebar"], [data-testid="stToolbar"], footer { display: none !important; }
    .block-container { padding: 0.5rem !important; max-width: 100% !important; }
    .stButton>button { border-radius: 10px !important; height: 45px !important; font-weight: bold !important; }
    iframe { border-radius: 20px !important; border: 1px solid #333 !important; }
    </style>
""", unsafe_allow_html=True)

# 6. INTERFACE DE BUSCA (Chaves únicas para evitar fantasmas)
with st.container():
    c1, c2 = st.columns([5, 1])
    with c1:
        busca = st.selectbox("Busca", options=["(Adicionar...)"] + list(banco_total.keys()), 
                             label_visibility="collapsed", key="v3_busca")
    with c2:
        if st.button("➕", key="v3_btn_add"):
            if busca and busca != "(Adicionar...)":
                uid = f"P_{int(time.time() * 1000)}" # ID Único temporal
                st.session_state.lista_pacotes.append({"id": uid, "nome": busca})
                st.session_state.ultima_pos = banco_total[busca]
                salvar_progresso()
                st.rerun()

# 7. PREPARAÇÃO DOS PONTOS
pontos_mapa = []
pendentes = []
for p in st.session_state.lista_pacotes:
    coords = banco_total.get(p['nome'], (0,0))
    is_done = p['id'] in st.session_state.entregues_id
    item = {"id": p['id'], "lat": coords[0], "lng": coords[1], "nome": p['nome'], "done": is_done}
    pontos_mapa.append(item)
    if not is_done: pendentes.append(item)

# Identificar o mais próximo apenas para a cor Laranja (Opcional)
proximo_id = None
if st.session_state.ultima_pos and pendentes:
    d_min = float('inf')
    for p in pendentes:
        dist = math.sqrt((st.session_state.ultima_pos[0]-p['lat'])**2 + (st.session_state.ultima_pos[1]-p['lng'])**2)
        if dist < d_min:
            d_min = dist
            proximo_id = p['id']

for p in pontos_mapa:
    p['cor'] = "#28a745" if p['done'] else ("#fd7e14" if p['id'] == proximo_id else "#dc3545")
    num = re.findall(r'\d+', p['nome'])[0] if re.findall(r'\d+', p['nome']) else p['nome'][:2]
    p['txt'] = "✔" if p['done'] else num

# 8. HTML DO MAPA
centro = st.session_state.ultima_pos if st.session_state.ultima_pos else [-16.15, -47.96]
map_html = f"""
<!DOCTYPE html>
<html>
<head>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        #map {{ height: 100vh; width: 100%; background: #e5e3df; }}
        body {{ margin: 0; padding: 0; }}
        .pin {{ width: 38px; height: 38px; border-radius: 50%; display: flex; align-items: center; 
               justify-content: center; color: white; font-weight: bold; border: 2px solid white; font-family: sans-serif; }}
        .btn {{ display: block; width: 100%; text-align: center; padding: 12px 0; margin-top: 8px; 
               border-radius: 8px; text-decoration: none; color: white; font-weight: bold; font-family: sans-serif; font-size: 14px; }}
    </style>
</head>
<body>
    <div id="map"></div>
    <script>
        var map = L.map('map', {{ zoomControl: false }}).setView([{centro[0]}, {centro[1]}], 16);
        L.tileLayer('http://{{s}}.google.com/vt/lyrs=m&x={{x}}&y={{y}}&z={{z}}', {{ subdomains:['mt0','mt1','mt2','mt3'] }}).addTo(map);
        
        var pts = {json.dumps(pontos_mapa)};
        pts.forEach(function(p) {{
            var icon = L.divIcon({{
                className: '',
                html: '<div class="pin" style="background:'+p.cor+'; opacity:'+(p.done ? 0.6 : 1)+'">'+p.txt+'</div>',
                iconSize: [38, 38], iconAnchor: [19, 19]
            }});
            
            var pop = '<div style="min-width:170px;"><strong style="font-size:15px;">'+p.nome+'</strong>' +
                      '<a href="https://www.google.com/maps/dir/?api=1&destination='+p.lat+','+p.lng+'" target="_blank" class="btn" style="background:#4285F4;">🚀 ABRIR GPS</a>';
            
            if (!p.done) {{
                // O TARGET="_TOP" É O QUE IMPEDE A DUPLICAÇÃO DOS MENUS
                pop += '<a href="?concluir='+p.id+'" target="_top" class="btn" style="background:#28a745;">✅ CONCLUIR</a>';
            }}
            pop += '</div>';
            L.marker([p.lat, p.lng], {{icon: icon}}).addTo(map).bindPopup(pop);
        }});
    </script>
</body>
</html>
"""

st.components.v1.html(map_html, height=550)

# 9. RODAPÉ
if st.button("🗑️ LIMPAR TUDO", use_container_width=True, key="btn_clear"):
    if os.path.exists(FILE_SAVE): os.remove(FILE_SAVE)
    st.session_state.lista_pacotes = []
    st.session_state.entregues_id = []
    st.session_state.ultima_pos = None
    st.rerun()
