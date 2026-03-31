import streamlit as st
import json
import os
import math

# --- CONFIGURAÇÕES INICIAIS ---
st.set_page_config(page_title="GPS Entrega", layout="wide", initial_sidebar_state="collapsed")
FILE_SAVE = "tarefas_ativas.json"
DATABASE_FILE = 'Lugares marcados.json'

# --- 1. CARREGAR BANCO DE DADOS FIXO ---
@st.cache_data
def carregar_banco_completo():
    if not os.path.exists(DATABASE_FILE):
        return {}
    try:
        with open(DATABASE_FILE, 'r', encoding='utf-8') as f:
            dados = json.load(f)
        banco = {}
        for feature in dados.get('features', []):
            nome = str(feature['properties'].get('title') or feature['properties'].get('name')).strip()
            coords = feature['geometry']['coordinates']
            banco[nome] = {"lat": coords[1], "lng": coords[0]}
        return banco
    except:
        return {}

BANCO_COORDS = carregar_banco_completo()

# --- 2. GERENCIAMENTO DE ESTADO (MEMÓRIA) ---
if 'pontos_ativos' not in st.session_state:
    if os.path.exists(FILE_SAVE):
        with open(FILE_SAVE, "r") as f:
            st.session_state.pontos_ativos = json.load(f)
    else:
        st.session_state.pontos_ativos = []

if 'ultima_pos' not in st.session_state:
    st.session_state.ultima_pos = [-16.15, -47.96] # Ponto padrão

def salvar():
    with open(FILE_SAVE, "w") as f:
        json.dump(st.session_state.pontos_ativos, f)

# --- 3. PROCESSAR AÇÕES DOS BOTÕES (VIA URL) ---
query_params = st.query_params
if "action" in query_params and "nome" in query_params:
    action = query_params["action"]
    nome_alvo = query_params["nome"]
    
    # Se clicar em FEITO, atualiza a última posição para cálculo de distância
    if action == "done":
        if nome_alvo in BANCO_COORDS:
            st.session_state.ultima_pos = [BANCO_COORDS[nome_alvo]['lat'], BANCO_COORDS[nome_alvo]['lng']]
    
    # EM AMBOS OS CASOS (FEITO OU EXCLUIR), O PONTO É REMOVIDO DA LISTA
    st.session_state.pontos_ativos = [p for p in st.session_state.pontos_ativos if p != nome_alvo]
    
    salvar()
    st.query_params.clear()
    st.rerun()

# --- 4. INTERFACE UI ---
st.markdown("""
    <style>
    [data-testid="stHeader"], footer { display: none !important; }
    .block-container { padding: 1rem !important; }
    iframe { border-radius: 15px; border: 2px solid #333; }
    </style>
""", unsafe_allow_html=True)

# Barra lateral para limpar tudo
with st.sidebar:
    if st.button("🗑️ LIMPAR TODA LISTA"):
        st.session_state.pontos_ativos = []
        salvar()
        st.rerun()

# Barra de busca e adição
c1, c2 = st.columns([4, 1])
with c1:
    opcao = st.selectbox("Buscar Quadra/Lugar", [""] + list(BANCO_COORDS.keys()), label_visibility="collapsed")
with c2:
    if st.button("➕"):
        if opcao and opcao not in st.session_state.pontos_ativos:
            st.session_state.pontos_ativos.append(opcao)
            salvar()
            st.rerun()

# --- 5. PREPARAR DADOS PARA O MAPA ---
map_data = []
proximo_nome = None
menor_dist = float('inf')

for nome in st.session_state.pontos_ativos:
    if nome in BANCO_COORDS:
        info = BANCO_COORDS[nome]
        # Cálculo básico de distância para achar o mais próximo
        d = math.sqrt((st.session_state.ultima_pos[0]-info['lat'])**2 + (st.session_state.ultima_pos[1]-info['lng'])**2)
        
        map_data.append({
            "nome": nome,
            "lat": info['lat'],
            "lng": info['lng'],
            "dist": d
        })
        
        if d < menor_dist:
            menor_dist = d
            proximo_nome = nome

# --- 6. MAPA HTML/JS ---
html_mapa = f"""
<!DOCTYPE html>
<html>
<head>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        #map {{ height: 100vh; width: 100%; border-radius: 15px; }}
        body {{ margin: 0; }}
        .pin {{
            width: 35px; height: 35px; border-radius: 50%;
            display: flex; align-items: center; justify-content: center;
            color: white; font-weight: bold; font-family: sans-serif;
            border: 2px solid white; box-shadow: 0 2px 5px rgba(0,0,0,0.4);
        }}
        .popup-card {{ font-family: sans-serif; text-align: center; padding: 5px; }}
        .btn {{
            display: block; padding: 10px; margin-top: 5px;
            color: white; text-decoration: none; border-radius: 5px; font-weight: bold;
        }}
    </style>
</head>
<body>
    <div id="map"></div>
    <script>
        var map = L.map('map', {{ zoomControl: false }}).setView([{st.session_state.ultima_pos[0]}, {st.session_state.ultima_pos[1]}], 15);
        
        L.tileLayer('http://{{s}}.google.com/vt/lyrs=m&x={{x}}&y={{y}}&z={{z}}', {{
            maxZoom: 20, subdomains:['mt0','mt1','mt2','mt3']
        }}).addTo(map);

        var pontos = {json.dumps(map_data)};
        var proximo = "{proximo_nome}";

        pontos.forEach(function(p) {{
            var cor = (p.nome === proximo) ? "#fd7e14" : "#dc3545";
            
            var icon = L.divIcon({{
                className: '',
                html: `<div class="pin" style="background: ${{cor}};">${{p.nome.substring(0,2)}}</div>`,
                iconSize: [35, 35], iconAnchor: [17, 17]
            }});

            var content = `
                <div class="popup-card">
                    <b>${{p.nome}}</b><br>
                    <a href="https://www.google.com/maps/dir/?api=1&destination=${{p.lat}},${{p.lng}}" target="_blank" class="btn" style="background:#1E1E1E;">🚀 GPS</a>
                    <a href="#" onclick="window.parent.location.search='?action=done&nome=${{p.nome}}'; return false;" class="btn" style="background:#28a745;">✅ FEITO</a>
                    <a href="#" onclick="window.parent.location.search='?action=delete&nome=${{p.nome}}'; return false;" class="btn" style="background:#dc3545;">🗑️ EXCLUIR</a>
                </div>
            `;

            L.marker([p.lat, p.lng], {{icon: icon}}).addTo(map).bindPopup(content);
        }});

        // Localização em tempo real do usuário
        map.locate({{watch: true, enableHighAccuracy: true}});
        map.on('locationfound', function(e) {{
            if (!window.userCircle) {{
                window.userCircle = L.circleMarker(e.latlng, {{radius: 8, color: 'white', fillColor: '#4285F4', fillOpacity: 1, weight: 3}}).addTo(map);
            }} else {{
                window.userCircle.setLatLng(e.latlng);
            }}
        }});
    </script>
</body>
</html>
"""

st.components.v1.html(html_mapa, height=600)

if proximo_nome:
    st.success(f"📍 Próximo objetivo: **{proximo_nome}**")
else:
    st.info("Nenhum ponto pendente. Adicione uma quadra acima 👆")
