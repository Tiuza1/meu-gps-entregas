import json
import streamlit as st
import re
import os
import math
import time

# 1. CONFIGURAÇÃO BÁSICA
st.set_page_config(page_title="GPS Profissional", layout="wide", initial_sidebar_state="collapsed")

# 2. CARREGAMENTO E BANCO (Executa uma vez)
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

# 3. ESTADO DO SISTEMA
if 'lista_pacotes' not in st.session_state: st.session_state.lista_pacotes = []
if 'entregues_id' not in st.session_state: st.session_state.entregues_id = []
if 'ultima_pos' not in st.session_state: st.session_state.ultima_pos = None

def salvar():
    dados = {"lista_pacotes": st.session_state.lista_pacotes, 
             "entregues_id": st.session_state.entregues_id, 
             "ultima_pos": st.session_state.ultima_pos}
    with open(FILE_SAVE, "w") as f: json.dump(dados, f)

# Carregar do disco apenas no primeiro início
if not st.session_state.lista_pacotes and os.path.exists(FILE_SAVE):
    try:
        with open(FILE_SAVE, "r") as f:
            d = json.load(f)
            st.session_state.lista_pacotes = d.get("lista_pacotes", [])
            st.session_state.entregues_id = d.get("entregues_id", [])
            st.session_state.ultima_pos = d.get("ultima_pos")
    except: pass

# 4. ESTILOS CSS
st.markdown("""
    <style>
    [data-testid="stHeader"], [data-testid="stSidebar"], [data-testid="stToolbar"], footer { display: none !important; }
    .block-container { padding: 0.5rem !important; max-width: 100% !important; }
    .stButton>button { border-radius: 12px !important; height: 50px !important; font-weight: bold !important; font-size: 18px !important; }
    iframe { border-radius: 20px !important; border: 1px solid #333 !important; }
    </style>
""", unsafe_allow_html=True)

# 5. INTERFACE DE BUSCA
c1, c2 = st.columns([5, 1])
with c1:
    busca = st.selectbox("Busca", options=["(Adicionar...)"] + list(banco_total.keys()), 
                         label_visibility="collapsed", key="search_bar")
with c2:
    if st.button("➕", key="btn_add"):
        if busca and busca != "(Adicionar...)":
            # Usamos timestamp para o ID ser sempre único e evitar duplicação
            uid = f"ID_{int(time.time() * 1000)}"
            st.session_state.lista_pacotes.append({"id": uid, "nome": busca})
            st.session_state.ultima_pos = banco_total[busca]
            salvar()
            st.rerun()

# 6. LÓGICA DE PONTOS E PROXIMIDADE
pontos_mapa = []
pendentes = []
for p in st.session_state.lista_pacotes:
    coords = banco_total.get(p['nome'], (0,0))
    is_done = p['id'] in st.session_state.entregues_id
    item = {"id": p['id'], "lat": coords[0], "lng": coords[1], "nome": p['nome'], "done": is_done}
    pontos_mapa.append(item)
    if not is_done: pendentes.append(item)

# Encontrar o mais próximo para o botão de ação rápida
proximo_ponto = None
if st.session_state.ultima_pos and pendentes:
    dist_min = float('inf')
    for p in pendentes:
        d = math.sqrt((st.session_state.ultima_pos[0]-p['lat'])**2 + (st.session_state.ultima_pos[1]-p['lng'])**2)
        if d < dist_min:
            dist_min = d
            proximo_ponto = p

# =================================================================
# 7. BOTÃO DE CONCLUIR (AQUI É O SEGREDO)
# =================================================================
if proximo_ponto:
    st.write(f"📍 Próximo: **{proximo_ponto['nome']}**")
    if st.button(f"✅ CONCLUIR ENTREGA EM {proximo_ponto['nome'].upper()}", type="primary", use_container_width=True):
        st.session_state.entregues_id.append(proximo_ponto['id'])
        st.session_state.ultima_pos = (proximo_ponto['lat'], proximo_ponto['lng'])
        salvar()
        st.rerun()
else:
    st.info("Nenhuma entrega pendente na lista.")

# 8. HTML DO MAPA (Simples, só para visualização e GPS)
centro = st.session_state.ultima_pos if st.session_state.ultima_pos else [-16.15, -47.96]
for p in pontos_mapa:
    p['cor'] = "#28a745" if p['done'] else ("#fd7e14" if proximo_ponto and p['id'] == proximo_ponto['id'] else "#dc3545")
    num = re.findall(r'\d+', p['nome'])[0] if re.findall(r'\d+', p['nome']) else p['nome'][:2]
    p['txt'] = "✔" if p['done'] else num

map_html = f"""
<!DOCTYPE html>
<html>
<head>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style> #map {{ height: 100vh; width: 100%; }} body {{ margin: 0; }} 
    .pin {{ width: 36px; height: 36px; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; border: 2px solid white; font-family: sans-serif; }}
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
                html: '<div class="pin" style="background:'+p.cor+'; opacity:'+(p.done ? 0.5 : 1)+'">'+p.txt+'</div>',
                iconSize: [36, 36], iconAnchor: [18, 18]
            }});
            var pop = '<strong>'+p.nome+'</strong><br><br>' + 
                      '<a href="https://www.google.com/maps/dir/?api=1&destination='+p.lat+','+p.lng+'" target="_blank" style="display:block; background:#4285F4; color:white; text-align:center; padding:8px; border-radius:5px; text-decoration:none; font-family:sans-serif; font-weight:bold;">🚀 ABRIR GPS</a>';
            L.marker([p.lat, p.lng], {{icon: icon}}).addTo(map).bindPopup(pop);
        }});
    </script>
</body>
</html>
"""

st.components.v1.html(map_html, height=450)

# 9. GERENCIAMENTO
if st.button("🗑️ LIMPAR TODA A ROTA", use_container_width=True):
    if os.path.exists(FILE_SAVE): os.remove(FILE_SAVE)
    st.session_state.lista_pacotes = []
    st.session_state.entregues_id = []
    st.session_state.ultima_pos = None
    st.rerun()
