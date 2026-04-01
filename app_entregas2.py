import json
import streamlit as st
import re
import os
import math

# 1. CONFIGURAÇÃO INICIAL (Sempre a primeira coisa)
st.set_page_config(page_title="GPS Profissional", layout="wide", initial_sidebar_state="collapsed")

# 2. CARREGAMENTO DE DADOS
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

# 3. INICIALIZAÇÃO DO ESTADO
if 'lista_pacotes' not in st.session_state: st.session_state.lista_pacotes = []
if 'entregues_id' not in st.session_state: st.session_state.entregues_id = []
if 'ultima_pos' not in st.session_state: st.session_state.ultima_pos = None

def salvar_progresso():
    dados = {"lista_pacotes": st.session_state.lista_pacotes, 
             "entregues_id": st.session_state.entregues_id, 
             "ultima_pos": st.session_state.ultima_pos}
    with open(FILE_SAVE, "w") as f: json.dump(dados, f)

# Carregar progresso do arquivo se o estado estiver vazio
if not st.session_state.lista_pacotes and os.path.exists(FILE_SAVE):
    try:
        with open(FILE_SAVE, "r") as f:
            d = json.load(f)
            st.session_state.lista_pacotes = d.get("lista_pacotes", [])
            st.session_state.entregues_id = d.get("entregues_id", [])
            st.session_state.ultima_pos = d.get("ultima_pos")
    except: pass

# 4. LÓGICA DE INTERRUPÇÃO (Resolve a Duplicação)
# Se o link do mapa foi clicado, processamos aqui e PARAMOS a execução com rerun
if "concluir" in st.query_params:
    id_c = st.query_params["concluir"]
    if id_c not in st.session_state.entregues_id:
        st.session_state.entregues_id.append(id_c)
        for p in st.session_state.lista_pacotes:
            if p['id'] == id_c:
                st.session_state.ultima_pos = banco_total.get(p['nome'])
        salvar_progresso()
    
    # Limpa a URL e força o recarregamento da página do zero
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

# 6. INTERFACE DE BUSCA (Usando Container e Keys fixas)
with st.container():
    c1, c2 = st.columns([5, 1])
    with c1:
        busca = st.selectbox("Busca", options=["(Adicionar...)"] + list(banco_total.keys()), 
                             label_visibility="collapsed", key="main_search_input")
    with c2:
        if st.button("➕", key="btn_add_main"):
            if busca and busca != "(Adicionar...)":
                nid = f"{busca}_{len(st.session_state.lista_pacotes)}"
                st.session_state.lista_pacotes.append({"id": nid, "nome": busca})
                st.session_state.ultima_pos = banco_total[busca]
                salvar_progresso()
                st.rerun()

# 7. PREPARAÇÃO DO MAPA
pontos_mapa = []
pendentes = []
for p in st.session_state.lista_pacotes:
    coords = banco_total.get(p['nome'], (0,0))
    is_done = p['id'] in st.session_state.entregues_id
    item = {"id": p['id'], "lat": coords[0], "lng": coords[1], "nome": p['nome'], "done": is_done, "cor": "#28a745" if is_done else "#dc3545"}
    pontos_mapa.append(item)
    if not is_done: pendentes.append(item)

# Lógica do próximo ponto (Laranja)
proximo_id = None
if st.session_state.ultima_pos and pendentes:
    dist_min = float('inf')
    for p in pendentes:
        d = math.sqrt((st.session_state.ultima_pos[0]-p['lat'])**2 + (st.session_state.ultima_pos[1]-p['lng'])**2)
        if d < dist_min:
            dist_min = d
            proximo_id = p['id']

for p in pontos_mapa:
    if p['id'] == proximo_id: p['cor'] = "#fd7e14"
    num = re.findall(r'\d+', p['nome'])[0] if re.findall(r'\d+', p['nome']) else p['nome'][:2]
    p['txt'] = "✔" if p['done'] else num

centro = st.session_state.ultima_pos if st.session_state.ultima_pos else [-16.15, -47.96]

# 8. HTML DO MAPA (O segredo está no target="_top")
map_html = f"""
<!DOCTYPE html>
<html>
<head>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        #map {{ height: 100vh; width: 100%; }}
        body {{ margin: 0; }}
        .pin {{ width: 38px; height: 38px; border-radius: 50%; display: flex; align-items: center; 
               justify-content: center; color: white; font-weight: bold; border: 2px solid white; }}
        .btn {{ display: block; width: 100%; text-align: center; padding: 10px 0; margin-top: 8px; 
               border-radius: 8px; text-decoration: none; color: white; font-weight: bold; font-family: sans-serif; }}
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
            
            var pop = '<div style="min-width:160px;"><strong>'+p.nome+'</strong>' +
                      '<a href="https://www.google.com/maps/dir/?api=1&destination='+p.lat+','+p.lng+'" target="_blank" class="btn" style="background:#4285F4;">🚀 GPS</a>';
            
            if (!p.done) {{
                // AQUI ESTÁ A CHAVE: target="_top" faz a página inteira atualizar, matando o iframe interno
                pop += '<a href="?concluir='+p.id+'" target="_top" class="btn" style="background:#28a745;">✅ CONCLUIR</a>';
            }}
            pop += '</div>';
            L.marker([p.lat, p.lng], {{icon: icon}}).addTo(map).bindPopup(pop);
        }});
    </script>
</body>
</html>
"""

st.components.v1.html(map_html, height=500)

# 9. RODAPÉ
st.write("---")
c_save, c_del = st.columns(2)
with c_save:
    if st.session_state.lista_pacotes:
        txt = "📋 ROTA\\n" + "\\n".join([f"{'✅' if p['id'] in st.session_state.entregues_id else '❌'} {p['nome']}" for p in st.session_state.lista_pacotes])
        st.download_button("💾 SALVAR", data=txt, file_name="rota.txt", use_container_width=True, key="btn_save_rota")
with c_del:
    if st.button("🗑️ LIMPAR TUDO", use_container_width=True, key="btn_clear_all"):
        if os.path.exists(FILE_SAVE): os.remove(FILE_SAVE)
        st.session_state.clear()
        st.rerun()
