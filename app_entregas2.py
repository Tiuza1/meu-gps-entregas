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
</style>
""", unsafe_allow_html=True)

# ESTADO
if 'state' not in st.session_state:
    st.session_state.state = {'pacotes': [], 'entregues': [], 'posicao': [-16.15, -47.96]}

state = st.session_state.state

def save():
    try:
        with open('state.json', 'w') as f:
            json.dump(state, f)
    except: pass

if os.path.exists('state.json'):
    try:
        with open('state.json') as f:
            saved = json.load(f)
            state.update(saved)
    except: pass

# BANCO
banco = {}
try:
    with open('Lugares marcados.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
        for f in data['features']:
            nome = str(f['properties'].get('title') or f['properties'].get('name') or '').strip()
            if nome:
                coords = f['geometry']['coordinates']
                banco[nome] = [coords[1], coords[0]]
except:
    banco = {}

# SELECTBOX + BOTÃO
c1, c2 = st.columns([4, 1])
with c1:
    lugares = list(banco.keys())
    selected = st.selectbox("Selecione o endereço", [''] + lugares)
with c2:
    if st.button('➕') and selected:
        pid = f"{selected}_{len(state['pacotes'])}"
        state['pacotes'].append({'id': pid, 'nome': selected})
        state['posicao'] = banco[selected]
        save()
        st.rerun()

# CONCLUI PACOTE
if st.query_params.get('concluir'):
    pid = st.query_params['concluir']
    if pid not in state['entregues']:
        for p in state['pacotes']:
            if p['id'] == pid:
                state['entregues'].append(pid)
                state['posicao'] = banco[p['nome']]
                save()
                st.rerun()
                break

# MARCADORES
markers = []
for p in state['pacotes']:
    if p['nome'] in banco:
        lat, lng = banco[p['nome']]
        done = p['id'] in state['entregues']
        color = '#28a745' if done else '#dc3545'
        num = re.findall('\\d+', p['nome'])
        label = '✔' if done else (num[0] if num else p['nome'][:3])
        markers.append({'id': p['id'], 'lat': lat, 'lng': lng, 'nome': p['nome'], 'done': done, 'color': color, 'label': label})

# PRÓXIMO
pendentes = [m for m in markers if not m['done']]
next_id = None
if state['posicao'] and pendentes:
    min_d = float('inf')
    for m in pendentes:
        d = math.hypot(state['posicao'][0] - m['lat'], state['posicao'][1] - m['lng'])
        if d < min_d:
            min_d = d
            next_id = m['id']

if next_id:
    for m in markers:
        if m['id'] == next_id:
            m['color'] = '#ff9800'
            break

# MAPA GOOGLE (COMO ORIGINAL)
map_html = f'''
<!DOCTYPE html>
<html>
<head>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
#map{{height:600px;width:100%;}}
.pin{{width:40px;height:40px;border-radius:50%;display:flex;align-items:center;justify-content:center;color:white;font-weight:bold;border:3px solid white;box-shadow:0 4px 12px rgba(0,0,0,0.4);cursor:pointer;}}
.btn-gps{{width:100%;padding:12px;margin:5px 0;border:none;border-radius:8px;background:#4285f4;color:white;font-weight:bold;cursor:pointer;}}
.btn-ok{{width:100%;padding:12px;margin:5px 0;border:none;border-radius:8px;background:#34a853;color:white;font-weight:bold;cursor:pointer;}}
</style>
</head>
<body>
<div id="map"></div>
<script>
var map = L.map("map").setView([{state['posicao'][0]}, {state['posicao'][1]}], 15);
L.tileLayer("https://mt{{Math.round(Math.random()*3)}}.google.com/vt/lyrs=m&x={{x}}&y={{y}}&z={{z}}", {{maxZoom:20}}).addTo(map);
var points = {json.dumps(markers)};
points.forEach(function(pt){{
var icon = L.divIcon({{
className: "",
html: '<div class="pin" style="background:'+pt.color+';'+(pt.done?'opacity:0.6;':'')+'">'+pt.label+'</div>',
iconSize: [40,40], iconAnchor: [20,20]
}});
var marker = L.marker([pt.lat, pt.lng], {{icon: icon}}).addTo(map);
var nome = pt.nome.replace(/'/g,"&apos;");
var popup = '<div style="width:240px;font-family:Arial;">'+
'<div style="font-size:18px;font-weight:bold;margin-bottom:12px;">📍 '+nome+'</div>'+
'<button class="btn-gps" onclick="window.open(&apos;https://www.google.com/maps/dir/?api=1&destination='+pt.lat+','+pt.lng+'&apos;, &apos;_blank&apos;)">🚀 Google Maps</button>';
if(!pt.done){{
popup += '<button class="btn-ok" onclick="done(&apos;'+pt.id+'&apos;)">✅ Feito</button>';
}} else {{
popup += '<div style="text-align:center;color:#34a853;font-size:16px;font-weight:bold;margin-top:10px;">✔️ Concluído</div>';
}}
popup += '</div>';
marker.bindPopup(popup, {{closeButton:false,autoClose:false}});
}});
function done(id){{
var url = new URL(window.location);
url.searchParams.set("concluir", id);
window.location.href = url.toString();
}}
map.locate({{watch:true,setView:false,enableHighAccuracy:true}});
map.on("locationfound", function(e){{
if(!window.gpsMarker){{
window.gpsMarker = L.circleMarker(e.latlng, {{radius:12,fillColor:"#1e88e5",color:"white",weight:3,fillOpacity:0.9}}).addTo(map);
}} else {{
window.gpsMarker.setLatLng(e.latlng);
}}
}});
</script>
</body>
</html>
'''

st.components.v1.html(map_html, height=600)

# INFO E BOTÕES
st.markdown("---")
pendentes = [m for m in markers if not m['done']]
if pendentes and next_id:
    for m in markers:
        if m['id'] == next_id:
            st.info(f"**Próximo destino:** {m['nome']}")
            st.caption("👆 Clique na bolinha **laranja** para abrir GPS ou marcar como feito!")
            break

col1, col2 = st.columns(2)
with col1:
    if state['pacotes']:
        txt = "ROTA DE ENTREGAS\\n" + "="*50 + "\\n\\n"
        for i, p in enumerate(state['pacotes'], 1):
            s = "✅" if p['id'] in state['entregues'] else "⏳"
            txt += f"{i:2}. {s} {p['nome']}\\n"
        st.download_button("💾 Salvar rota", txt, "entregas.txt", "text/plain")

with col2:
    if st.button("🗑️ Resetar"):
        state['pacotes'] = []
        state['entregues'] = []
        save()
        st.rerun()
