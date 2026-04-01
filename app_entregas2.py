import json
import streamlit as st
import re
import os
import math

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

# INICIALIZAÇÃO SEGURA
if 'dados_app' not in st.session_state:
    st.session_state.dados_app = {
        'lista_pacotes': [],
        'entregues_id': [],
        'ultima_pos': None,
        'map_key': 0
    }

dados = st.session_state.dados_app

def salvar_progresso():
    try:
        with open("progresso_final.json", "w") as f:
            json.dump(dados, f)
    except:
        pass

# Carrega dados salvos
try:
    if os.path.exists("progresso_final.json"):
        with open("progresso_final.json", "r") as f:
            dados_salvos = json.load(f)
            dados['lista_pacotes'] = dados_salvos.get('lista_pacotes', [])
            dados['entregues_id'] = dados_salvos.get('entregues_id', [])
            dados['ultima_pos'] = dados_salvos.get('ultima_pos', None)
except:
    pass

@st.cache_data
def carregar_banco():
    try:
        with open('Lugares marcados.json', 'r', encoding='utf-8') as f:
            dados_j = json.load(f)['features']
        banco = {}
        for l in dados_j:
            nome = str(l['properties'].get('title') or l['properties'].get('name') or '').strip()
            if nome:
                coords = l['geometry']['coordinates']
                banco[nome] = (coords[1], coords[0])
        return banco
    except:
        return {}

banco_total = carregar_banco()

# Processa query params
query_params = st.query_params
if 'concluir' in query_params:
    pacote_id = query_params['concluir']
    for pacote in dados['lista_pacotes']:
        if pacote['id'] == pacote_id and pacote_id not in dados['entregues_id']:
            coords = banco_total.get(pacote['nome'])
            if coords:
                dados['entregues_id'].append(pacote_id)
                dados['ultima_pos'] = coords
                salvar_progresso()
                dados['map_key'] += 1
                st.session_state.dados_app = dados
                st.rerun()
            break

# Interface de busca
c1, c2 = st.columns([5, 1])
with c1:
    opcoes = ["(Adicionar...)"] + list(banco_total.keys())
    busca = st.selectbox("", options=opcoes, label_visibility="collapsed")
with c2:
    if st.button("➕") and busca != "(Adicionar...)":
        nid = f"{busca}_{len(dados['lista_pacotes'])}"
        dados['lista_pacotes'].append({"id": nid, "nome": busca})
        dados['ultima_pos'] = banco_total[busca]
        salvar_progresso()
        dados['map_key'] += 1
        st.session_state.dados_app = dados
        st.rerun()

# Prepara pontos para mapa
pontos_para_o_mapa = []
for pacote in dados['lista_pacotes']:
    nome = pacote['nome']
    if nome in banco_total:
        coords = banco_total[nome]
        concluido = pacote['id'] in dados['entregues_id']
        cor = "#28a745" if concluido else "#dc3545"
        pontos_para_o_mapa.append({
            "id": pacote['id'],
            "lat": coords[0],
            "lng": coords[1],
            "nome": nome,
            "concluido": concluido,
            "cor": cor
        })

# Calcula próximo
pendentes = [p for p in pontos_para_o_mapa if not p['concluido']]
proximo_id = None
if dados['ultima_pos'] and pendentes:
    min_dist = float('inf')
    for p in pendentes:
        dist = math.hypot(dados['ultima_pos'][0] - p['lat'], dados['ultima_pos'][1] - p['lng'])
        if dist < min_dist:
            min_dist = dist
            proximo_id = p['id']

for p in pontos_para_o_mapa:
    if p['id'] == proximo_id:
        p['cor'] = "#fd7e14"
    nums = re.findall(r'\d+', p['nome'])
    p['txt'] = "✔" if p['concluido'] else (nums[0] if nums else p['nome'][:2])

centro = dados['ultima_pos'] or [-16.15, -47.96]

# MAPA - HTML PURO SEM F-STRINGS
html_map = f'''
<!DOCTYPE html>
<html>
<head>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
#map{{height:100vh;width:100%;background:#e5e3df;}}
body{{margin:0;padding:0;}}
.pin{{width:38px;height:38px;border-radius:50%;display:flex;align-items:center;justify-content:center;color:white;font-weight:bold;font-family:sans-serif;border:2px solid white;box-shadow:0 2px 5px rgba(0,0,0,0.3);cursor:pointer;}}
.leaflet-popup-content{{margin:10px 10px !important;font-family:Arial,sans-serif !important;}}
.popup-btn{{width:100%;margin:5px 0;padding:12px;border:none;border-radius:8px;font-weight:bold;cursor:pointer;font-size:15px;}}
.btn-gps{{background:#4285F4;color:white;}}
.btn-feito{{background:#34A853;color:white;}}
</style>
</head>
<body>
<div id="map"></div>
<script>
var map=L.map("map",{{zoomControl:false}}).setView([{centro[0]},{centro[1]}],16);
L.tileLayer("http://{{s}}.google.com/vt/lyrs=m&x={{x}}&y={{y}}&z={{z}}",{{maxZoom:20,subdomains:["mt0","mt1","mt2","mt3"]}}).addTo(map);
var pontos={json.dumps(pontos_para_o_mapa)};
var userMarker;
pontos.forEach(function(p){{
var icon=L.divIcon({{className:"",html:'<div class="pin" style="background:'+p.cor+';opacity:'+(p.concluido?0.6:1)+'" >'+p.txt+'</div>',iconSize:[38,38],iconAnchor:[19,19]}});
var marker=L.marker([p.lat,p.lng],{{icon:icon}}).addTo(map);
var nome=p.nome.replace(/'/g,"&#39;");
var popupContent='<div style="min-width:220px;"><h4 style="margin:0 0 15px 0;color:#333;font-size:16px;">📍 '+nome+'</h4><button class="popup-btn btn-gps" onclick="window.open(\'https://www.google.com/maps/dir/?api=1&destination=\'+p.lat+\',\'+p.lng+\'','_blank')">🚀 Abrir GPS</button>';
if(!p.concluido){{popupContent+='<button class="popup-btn btn-feito" onclick="concluir(\''+p.id+'\',\''+p.lat+'\',\''+p.lng+'\')">✅ Concluir</button>';}}else{{popupContent+='<p style="color:#28a745;font-weight:bold;text-align:center;margin:10px 0;">✔️ Concluído</p>';}}
popupContent+='</div>';
marker.bindPopup(popupContent,{{closeButton:false,autoClose:false,closeOnEscapeKey:true}});
}});
function concluir(id,lat,lng){{var url=new URL(window.location);url.searchParams.set("concluir",id);window.top.location.href=url.toString();}}
function onLocationFound(e){{if(!userMarker){{userMarker=L.circleMarker(e.latlng,{{radius:9,fillColor:"#4285F4",color:"white",weight:3,opacity:1,fillOpacity:1}}).addTo(map);}}else{{userMarker.setLatLng(e.latlng);}}}}
map.on("locationfound",onLocationFound);
map.locate({{watch:true,enableHighAccuracy:true,setView:false}});
</script>
</body>
</html>
'''

st.components.v1.html(html_map, height=550)

# Painel inferior
st.markdown("---")

if pendentes:
    for p in pontos_para_o_mapa:
        if p['id'] == proximo_id:
            st.success(f"📍 **Próximo:** {p['nome']}")
            st.info("👆 Clique na bolinha **laranja** no mapa!")
            break

col1, col2 = st.columns(2)
with col1:
    if dados['lista_pacotes']:
        texto = "📋 ROTA DE ENTREGAS\n" + "="*30 + "\n\n"
        for i, pacote in enumerate(dados['lista_pacotes'], 1):
            status = "✅" if pacote['id'] in dados['entregues_id'] else "⏳"
            texto += f"{i}. {status} {pacote['nome']}\n"
        st.download_button("💾 SALVAR", texto, "rota.txt", "text/plain")

with col2:
    if st.button("🗑️ LIMPAR"):
        dados['lista_pacotes'] = []
        dados['entregues_id'] = []
        dados['ultima_pos'] = None
        salvar_progresso()
        st.session_state.dados_app = dados
        st.rerun()
