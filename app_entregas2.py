import json
import streamlit as st
import re
import os
import math
import time

# =================================================================
# 1. INICIALIZAÇÃO E PERSISTÊNCIA
# =================================================================
FILE_SAVE = "progresso_final.json"

if 'lista_pacotes' not in st.session_state: st.session_state.lista_pacotes = []
if 'entregues_id' not in st.session_state: st.session_state.entregues_id = []
if 'ultima_pos' not in st.session_state: st.session_state.ultima_pos = None

# Carregar do arquivo JSON
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
# 2. PROCESSAMENTO DE AÇÕES (VIA BOTÕES OU URL)
# =================================================================
def marcar_feito(item_id):
    if item_id not in st.session_state.entregues_id:
        st.session_state.entregues_id.append(item_id)
        # Atualiza última posição para o próximo cálculo
        ponto = next((p for p in st.session_state.lista_pacotes if p['id'] == item_id), None)
        if ponto:
            st.session_state.ultima_pos = (ponto['lat'], ponto['lng'])
        salvar_progresso()

def excluir_ponto(item_id):
    st.session_state.lista_pacotes = [p for p in st.session_state.lista_pacotes if p['id'] != item_id]
    if item_id in st.session_state.entregues_id:
        st.session_state.entregues_id.remove(item_id)
    salvar_progresso()

# Captura ação via URL (vinda do mapa)
params = st.query_params
if "action" in params:
    if params["action"] == "done": marcar_feito(params["id"])
    elif params["action"] == "delete": excluir_ponto(params["id"])
    st.query_params.clear()
    st.rerun()

# =================================================================
# 3. CONFIGURAÇÃO VISUAL
# =================================================================
st.set_page_config(page_title="Painel do Entregador", layout="wide")

st.markdown("""
    <style>
    .block-container { padding: 1rem !important; }
    .stButton>button { border-radius: 10px; height: 3.5rem; font-weight: bold; }
    .btn-maps { background-color: #4285F4 !important; color: white !important; text-decoration: none; padding: 10px; border-radius: 8px; display: block; text-align: center; }
    </style>
""", unsafe_allow_html=True)

@st.cache_data
def carregar_banco():
    try:
        with open('Lugares marcados.json', 'r', encoding='utf-8') as f:
            db = json.load(f)
        return {str(l['properties'].get('title') or l['properties'].get('name')).strip(): 
                (l['geometry']['coordinates'][1], l['geometry']['coordinates'][0]) 
                for l in db.get('features',[])}
    except: return {}

banco_total = carregar_banco()

# =================================================================
# 4. BUSCA E ADICIONAR
# =================================================================
st.title("🚚 Painel do Entregador")

with st.expander("⚙️ CONFIGURAR ENTREGAS"):
    busca = st.selectbox("Buscar Local", options=[""] + list(banco_total.keys()))
    if st.button("ADICIONAR À ROTA"):
        if busca:
            lat_lng = banco_total[busca]
            # ID único usando timestamp para evitar bugs
            nid = f"{int(time.time())}" 
            st.session_state.lista_pacotes.append({"id": nid, "nome": busca, "lat": lat_lng[0], "lng": lat_lng[1]})
            salvar_progresso()
            st.rerun()
    
    if st.button("🗑️ LIMPAR TODA A ROTA"):
        st.session_state.lista_pacotes = []; st.session_state.entregues_id = []
        salvar_progresso(); st.rerun()

# =================================================================
# 5. MONTAGEM DOS PONTOS PARA O MAPA (COM CORREÇÃO DE ERRO)
# =================================================================
pontos_mapa = []
for p in st.session_state.lista_pacotes:
    status_feito = p['id'] in st.session_state.entregues_id
    cor = "#28a745" if status_feito else "#dc3545"
    
    # --- CORREÇÃO DO ERRO AQUI ---
    # Se lat/lng não existir no pacote salvo, busca no banco_total
    lat = p.get('lat')
    lng = p.get('lng')
    
    if lat is None or lng is None:
        if p['nome'] in banco_total:
            lat, lng = banco_total[p['nome']]
        else:
            lat, lng = 0, 0 # Valor padrão caso não encontre em lugar nenhum
    # -----------------------------

    num = re.findall(r'\d+', p['nome'])
    label = num[0] if num else p['nome'][:2]
    
    pontos_mapa.append({
        "id": p['id'], "lat": lat, "lng": lng, 
        "nome": p['nome'], "concluido": status_feito, "cor": cor, "label": label
    })

# =================================================================
# 6. MAPA LEAFLET
# =================================================================
# Usa o centro da primeira entrega caso não tenha última posição
if st.session_state.ultima_pos:
    centro = st.session_state.ultima_pos
elif pontos_mapa:
    centro = [pontos_mapa[0]['lat'], pontos_mapa[0]['lng']]
else:
    centro = [-16.15, -47.96] # Coordenada padrão (Brasília)

mapa_html = f"""
<!DOCTYPE html>
<html>
<head>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        #map {{ height: 450px; width: 100%; border-radius: 15px; }}
        body {{ margin: 0; }}
        .pin {{
            width: 32px; height: 32px; border-radius: 50%; border: 2px solid white;
            display: flex; align-items: center; justify-content: center;
            color: white; font-weight: bold; font-family: sans-serif; box-shadow: 0 2px 5px rgba(0,0,0,0.3);
        }}
    </style>
</head>
<body>
    <div id="map"></div>
    <script>
        var map = L.map('map', {{zoomControl: false}}).setView([{centro[0]}, {centro[1]}], 15);
        L.tileLayer('http://{{s}}.google.com/vt/lyrs=m&x={{x}}&y={{y}}&z={{z}}', {{
            maxZoom: 20, subdomains:['mt0','mt1','mt2','mt3']
        }}).addTo(map);

        var pontos = {json.dumps(pontos_mapa)};
        pontos.forEach(function(p) {{
            var icon = L.divIcon({{
                className: '',
                html: `<div class="pin" style="background:${{p.cor}}">${{p.concluido ? '✓' : p.label}}</div>`,
                iconSize: [32, 32], iconAnchor: [16, 16]
            }});

            var popupContent = `
                <div style="font-family: sans-serif; text-align:center;">
                    <b>${{p.nome}}</b><br><br>
                    <a href="https://www.google.com/maps/dir/?api=1&destination=${{p.lat}},${{p.lng}}" target="_blank" 
                       style="background:#1E1E1E; color:white; padding:8px; border-radius:5px; text-decoration:none; display:block; margin-bottom:5px;">🚀 GPS</a>
                    <a href="?action=done&id=${{p.id}}" target="_self" 
                       style="background:#28a745; color:white; padding:8px; border-radius:5px; text-decoration:none; display:block;">✅ FEITO</a>
                </div>`;

            L.marker([p.lat, p.lng], {{icon: icon}}).addTo(map).bindPopup(popupContent);
        }});
        
        map.locate({{setView: false, watch: true, enableHighAccuracy: true}});
        map.on('locationfound', function(e) {{
            L.circleMarker(e.latlng, {{radius: 7, color: '#4285F4', fillOpacity: 1}}).addTo(map);
        }});
    </script>
</body>
</html>
"""

st.components.v1.html(mapa_html, height=460)

# =================================================================
# 7. LISTA DE AÇÕES ABAIXO DO MAPA (MAIS CONFIÁVEL)
# =================================================================
st.subheader("📍 Próximas Entregas")

for p in pontos_mapa:
    if not p['concluido']:
        with st.container():
            col1, col2, col3 = st.columns([2, 1, 1])
            col1.write(f"**{p['nome']}**")
            
            # Botão que abre o Google Maps nativo
            maps_link = f"https://www.google.com/maps/dir/?api=1&destination={p['lat']},{p['lng']}"
            col2.markdown(f'<a href="{maps_link}" target="_blank" class="btn-maps">🗺️ MAPS</a>', unsafe_allow_html=True)
            
            if col3.button("✅ OK", key=f"btn_{p['id']}"):
                marcar_feito(p['id'])
                st.rerun()
            st.divider()
