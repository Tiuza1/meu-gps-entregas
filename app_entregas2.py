import json
import streamlit as st
import re
import os
import math
import time

# =================================================================
# 1. CONFIGURAÇÃO E PERSISTÊNCIA
# =================================================================
st.set_page_config(page_title="Painel do Entregador", layout="wide")

FILE_SAVE = "progresso_final.json"

if 'lista_pacotes' not in st.session_state: st.session_state.lista_pacotes = []
if 'entregues_id' not in st.session_state: st.session_state.entregues_id = []
if 'ultima_pos' not in st.session_state: st.session_state.ultima_pos = None

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

def salvar_progresso():
    dados = {
        "lista_pacotes": st.session_state.lista_pacotes, 
        "entregues_id": st.session_state.entregues_id, 
        "ultima_pos": st.session_state.ultima_pos
    }
    with open(FILE_SAVE, "w") as f: json.dump(dados, f)

# Carregar dados iniciais
if not st.session_state.lista_pacotes and os.path.exists(FILE_SAVE):
    try:
        with open(FILE_SAVE, "r") as f:
            d = json.load(f)
            st.session_state.lista_pacotes = d.get("lista_pacotes", [])
            st.session_state.entregues_id = d.get("entregues_id", [])
            st.session_state.ultima_pos = d.get("ultima_pos")
    except: pass

# =================================================================
# 2. FUNÇÃO MARCAR FEITO (CORRIGIDA PARA NÃO DAR ERRO)
# =================================================================
def marcar_feito(item_id):
    if item_id not in st.session_state.entregues_id:
        st.session_state.entregues_id.append(item_id)
        
        # Procura o ponto na lista
        ponto = next((p for p in st.session_state.lista_pacotes if p['id'] == item_id), None)
        
        if ponto:
            # Tenta pegar lat/lng do ponto, se não tiver, busca no banco_total
            lat = ponto.get('lat')
            lng = ponto.get('lng')
            
            if lat is None or lng is None:
                coords = banco_total.get(ponto['nome'])
                if coords:
                    lat, lng = coords
                else:
                    lat, lng = -16.15, -47.96 # Valor padrão se tudo falhar
            
            st.session_state.ultima_pos = (lat, lng)
        salvar_progresso()

# Captura cliques vindos do Mapa
params = st.query_params
if "action" in params:
    if params["action"] == "done":
        marcar_feito(params["id"])
    st.query_params.clear()
    st.rerun()

# =================================================================
# 3. ESTILIZAÇÃO E INTERFACE
# =================================================================
st.markdown("""
    <style>
    .stButton>button { border-radius: 10px; height: 3rem; font-weight: bold; width: 100%; }
    .btn-maps { 
        background-color: #4285F4 !important; color: white !important; 
        text-decoration: none; padding: 10px; border-radius: 8px; 
        display: block; text-align: center; font-weight: bold; font-size: 14px;
    }
    .card-entrega {
        background: #262730; border-left: 5px solid #dc3545;
        padding: 12px; border-radius: 8px; margin-bottom: 5px; color: white;
    }
    .concluido { border-left: 5px solid #28a745 !important; opacity: 0.6; }
    </style>
""", unsafe_allow_html=True)

st.title("🚚 Painel do Entregador")

with st.expander("⚙️ CONFIGURAR ROTA"):
    busca = st.selectbox("Buscar Local", options=[""] + list(banco_total.keys()))
    if st.button("➕ ADICIONAR"):
        if busca:
            coords = banco_total[busca]
            nid = f"{int(time.time() * 1000)}"
            st.session_state.lista_pacotes.append({
                "id": nid, "nome": busca, "lat": coords[0], "lng": coords[1]
            })
            salvar_progresso()
            st.rerun()
    
    if st.button("🗑️ LIMPAR TUDO"):
        st.session_state.lista_pacotes = []; st.session_state.entregues_id = []
        st.session_state.ultima_pos = None
        if os.path.exists(FILE_SAVE): os.remove(FILE_SAVE)
        st.rerun()

# =================================================================
# 4. PREPARAÇÃO DOS PONTOS
# =================================================================
pontos_mapa = []
for p in st.session_state.lista_pacotes:
    feito = p['id'] in st.session_state.entregues_id
    cor = "#28a745" if feito else "#dc3545"
    
    # Busca coordenadas se estiverem faltando (migração de dados antigos)
    lat = p.get('lat')
    lng = p.get('lng')
    if lat is None or lng is None:
        coords = banco_total.get(p['nome'], (-16.15, -47.96))
        lat, lng = coords

    num = re.findall(r'\d+', p['nome'])
    label = num[0] if num else p['nome'][:2]
    
    pontos_mapa.append({
        "id": p['id'], "lat": lat, "lng": lng, 
        "nome": p['nome'], "concluido": feito, "cor": cor, "label": label
    })

# =================================================================
# 5. MAPA
# =================================================================
centro = st.session_state.ultima_pos if st.session_state.ultima_pos else [-16.15, -47.96]

mapa_html = f"""
<!DOCTYPE html>
<html>
<head>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        #map {{ height: 400px; width: 100%; border-radius: 15px; }}
        body {{ margin: 0; }}
        .pin {{
            width: 30px; height: 30px; border-radius: 50%; border: 2px solid white;
            display: flex; align-items: center; justify-content: center;
            color: white; font-weight: bold; font-family: sans-serif; font-size: 12px;
        }}
    </style>
</head>
<body>
    <div id="map"></div>
    <script>
        var map = L.map('map', {{zoomControl: false}}).setView([{centro[0]}, {centro[1]}], 15);
        L.tileLayer('https://{{s}}.google.com/vt/lyrs=m&x={{x}}&y={{y}}&z={{z}}', {{
            maxZoom: 20, subdomains:['mt0','mt1','mt2','mt3']
        }}).addTo(map);

        var pontos = {json.dumps(pontos_mapa)};
        pontos.forEach(function(p) {{
            var icon = L.divIcon({{
                className: '',
                html: `<div class="pin" style="background:${{p.cor}}">${{p.concluido ? '✓' : p.label}}</div>`,
                iconSize: [30, 30], iconAnchor: [15, 15]
            }});

            var popupContent = `
                <div style="text-align:center; font-family:sans-serif;">
                    <b>${{p.nome}}</b><br><br>
                    <a href="?action=done&id=${{p.id}}" target="_self" 
                       style="background:#28a745; color:white; padding:8px 15px; border-radius:5px; text-decoration:none; display:block;">✅ CONCLUIR</a>
                </div>`;

            L.marker([p.lat, p.lng], {{icon: icon}}).addTo(map).bindPopup(popupContent);
        }});
        
        map.locate({{setView: false, watch: true, enableHighAccuracy: true}});
        map.on('locationfound', function(e) {{
            L.circleMarker(e.latlng, {{radius: 6, color: '#4285F4', fillOpacity: 1}}).addTo(map);
        }});
    </script>
</body>
</html>
"""

st.components.v1.html(mapa_html, height=410)

# =================================================================
# 6. LISTA ABAIXO DO MAPA
# =================================================================
st.subheader("📋 Roteiro")

for p in pontos_mapa:
    estilo = "concluido" if p['concluido'] else ""
    with st.container():
        st.markdown(f'<div class="card-entrega {estilo}"><strong>{p["nome"]}</strong></div>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        
        # Botão para abrir Google Maps oficial e ver bolinha azul
        maps_link = f"https://www.google.com/maps/search/?api=1&query={p['lat']},{p['lng']}"
        c1.markdown(f'<a href="{maps_link}" target="_blank" class="btn-maps">📍 VER NO MAPS</a>', unsafe_allow_html=True)
        
        if not p['concluido']:
            if c2.button("✅ OK", key=f"btn_{p['id']}"):
                marcar_feito(p['id'])
                st.rerun()
