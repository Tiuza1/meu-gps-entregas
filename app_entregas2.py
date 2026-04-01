import streamlit as st
import json
import math
import re
import os

st.set_page_config(page_title="GPS Profissional", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""
<style>
[data-testid="stHeader"], [data-testid="stSidebar"], [data-testid="stToolbar"], footer { display: none !important; }
.block-container { padding: 0.5rem !important; max-width: 100% !important; }
.stButton>button { border-radius: 10px !important; height: 45px !important; font-weight: bold !important; }
.stSelectbox { margin-bottom: -15px !important; }
iframe { border-radius: 20px !important; border: 1px solid #333 !important; }
</style>
""", unsafe_allow_html=True)

# Estado simplificado
if 'app_state' not in st.session_state:
    st.session_state.app_state = {'pacotes': [], 'entregues': [], 'posicao': None}

state = st.session_state.app_state

def save_state():
    try:
        with open('state.json', 'w') as f:
            json.dump(state, f)
    except:
        pass

# Carrega estado
if os.path.exists('state.json'):
    try:
        with open('state.json', 'r') as f:
            saved = json.load(f)
            state['pacotes'] = saved.get('pacotes', [])
            state['entregues'] = saved.get('entregues', [])
            state['posicao'] = saved.get('posicao', None)
    except:
        pass

# Banco de dados locais
banco = {}
try:
    with open('Lugares marcados.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
        for feature in data.get('features', []):
            props = feature['properties']
            nome = (props.get('title') or props.get('name') or '').strip()
            if nome:
                coords = feature['geometry']['coordinates']
                banco[nome] = (coords[1], coords[0])
except:
    st.error("❌ Arquivo 'Lugares marcados.json' não encontrado!")
    st.stop()

# Busca e adicionar
col1, col2 = st.columns([5, 1])
with col1:
    lugares = list(banco.keys())
    selected = st.selectbox('', ['Adicionar...'] + lugares, label_visibility='collapsed')
with col2:
    if st.button('➕') and selected != 'Adicionar...':
        id_pacote = f"{selected}_{len(state['pacotes'])}"
        state['pacotes'].append({'id': id_pacote, 'nome': selected})
        state['posicao'] = banco[selected]
        save_state()
        st.rerun()

# Processa clique no mapa
if 'concluir' in st.query_params:
    id_pacote = st.query_params['concluir']
    if id_pacote not in state['entregues']:
        for pacote in state['pacotes']:
            if pacote['id'] == id_pacote:
                state['entregues'].append(id_pacote)
                state['posicao'] = banco[pacote['nome']]
                save_state()
                st.rerun()
                break

# Prepara marcadores do mapa
marcadores = []
for pacote in state['pacotes']:
    nome = pacote['nome']
    if nome in banco:
        lat, lng = banco[nome]
        done = pacote['id'] in state['entregues']
        cor = '#28a745' if done else '#dc3545'
        numero = re.findall(r'\d+', nome)
        texto = '✔' if done else (numero[0] if numero else nome[:2])
        marcadores.append({
            'id': pacote['id'],
            'lat': lat,
            'lng': lng,
            'nome': nome,
            'done': done,
            'cor': cor,
            'texto': texto
        })

# Próximo mais próximo
pendentes = [m for m in marcadores if not m['done']]
proximo_id = None
if state['posicao'] and pendentes:
    menor_dist = float('inf')
    for m in pendentes:
        dist = math.hypot(state['posicao'][0] - m['lat'], state['posicao'][1] - m['lng'])
        if dist < menor_dist:
            menor_dist = dist
            proximo_id = m['id']

for m in marcadores:
    if m['id'] == proximo_id:
        m['cor'] = '#fd7e14'

centro_mapa = state['posicao'] or [-16.15, -47.96]

# HTML DO MAPA (testado e funcional)
map_html = f'''
<!DOCTYPE html>
<html>
<head>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        #map {{height: 70vh; width: 100%; border-radius: 20px;}}
        .pin {{width: 35px; height: 35px; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; font-size: 14px; border: 3px solid white; box-shadow: 0 4px 8px rgba(0,0,0,0.3); cursor: pointer;}}
        .popup-btn {{width: 100%; padding: 12px; margin: 5px 0; border: none; border-radius: 8px; font-weight: bold; font-size: 14px; cursor: pointer;}}
        .gps-btn {{background: #4285f4; color: white;}}
        .done-btn {{background: #34a853; color: white;}}
    </style>
</head>
<body style="margin:0; padding:0;">
    <div id="map"></div>
    <script>
        var map = L.map('map').setView([{centro_mapa[0]}, {centro_mapa[1]}], 15);
        L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
            attribution: '&copy; OpenStreetMap',
            maxZoom: 19
        }}).addTo(map);
        
        var markers = {json.dumps(marcadores)};
        
        markers.forEach(function(markerData) {{
            var pinColor = markerData.done ? 'opacity: 0.6' : 'opacity: 1';
            var pinHtml = '<div class="pin" style="background: ' + markerData.cor + '; ' + pinColor + '">' + markerData.texto + '</div>';
            
            var icon = L.divIcon({{
                html: pinHtml,
                iconSize: [35, 35],
                iconAnchor: [17, 17],
                className: ''
            }});
            
            var marker = L.marker([markerData.lat, markerData.lng], {{icon: icon}}).addTo(map);
            
            var nomeSafe = markerData.nome.replace(/'/g, "&#39;");
            var popup = '<div style="min-width: 220px; font-family: Arial;">' +
                '<div style="font-size: 16px; font-weight: bold; margin-bottom: 10px; color: #333;">📍 ' + nomeSafe + '</div>' +
                '<button class="popup-btn gps-btn" onclick="window.open(\'https://www.google.com/maps/dir/?api=1&destination=' + 
                markerData.lat + ',' + markerData.lng + '\', \'_blank\')">🚀 Abrir GPS</button>';
            
            if (!markerData.done) {{
                popup += '<button class="popup-btn done-btn" onclick="marcarConcluido(\'' + 
                         markerData.id + '\', ' + markerData.lat + ', ' + markerData.lng + ')">✅ Concluir</button>';
            }} else {{
                popup += '<div style="text-align: center; color: #34a853; font-weight: bold; margin-top: 10px;">✔️ Concluído</div>';
            }}
            popup += '</div>';
            
            marker.bindPopup(popup, {{closeButton: false, autoClose: true}});
        }});
        
        function marcarConcluido(id, lat, lng) {{
            var url = new URL(window.location.href);
            url.searchParams.set('concluir', id);
            window.location.href = url.toString();
        }}
        
        if (navigator.geolocation) {{
            navigator.geolocation.watchPosition(function(position) {{
                var pos = [position.coords.latitude, position.coords.longitude];
                if (!window.userMarker) {{
                    window.userMarker = L.circleMarker(pos, {{
                        radius: 10,
                        fillColor: "#1a73e8",
                        color: "#ffffff",
                        weight: 3,
                        fillOpacity: 0.9
                    }}).addTo(map);
                }} else {{
                    window.userMarker.setLatLng(pos);
                }}
            }}, function() {{}}, {{enableHighAccuracy: true}});
        }}
    </script>
</body>
</html>
'''

st.components.v1.html(map_html, height=600)

# Painel inferior
st.markdown("---")
if pendentes:
    for m in marcadores:
        if m['id'] == proximo_id:
            st.success(f"**📍 Próximo:** {m['nome']}")
            break

cols = st.columns(2)
with cols[0]:
    if state['pacotes']:
        rota_txt = "📦 ROTA DE ENTREGAS\n" + "═" * 40 + "\n\n"
        for i, p in enumerate(state['pacotes'], 1):
            status = "✅" if p['id'] in state['entregues'] else "🔄"
            rota_txt += f"{i:2d}. {status} {p['nome']}\n"
        st.download_button("💾 Exportar Rota", rota_txt, "rota_entregas.txt")

with cols[1]:
    if st.button("🗑️ Limpar Tudo"):
        state['pacotes'] = []
        state['entregues'] = []
        state['posicao'] = None
        save_state()
        st.rerun()
