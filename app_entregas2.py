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

FILE_SAVE = "progresso_final.json"

if 'iniciado' not in st.session_state:
    st.session_state.iniciado = False
    st.session_state.lista_pacotes = []
    st.session_state.entregues_id = []
    st.session_state.ultima_pos = None
    st.session_state.map_key = 0

def salvar_progresso():
    dados = {
        "lista_pacotes": st.session_state.lista_pacotes, 
        "entregues_id": st.session_state.entregues_id, 
        "ultima_pos": st.session_state.ultima_pos
    }
    try:
        with open(FILE_SAVE, "w") as f: 
            json.dump(dados, f)
    except Exception as e:
        st.error(f"Erro salvar: {e}")

if not st.session_state.iniciado:
    st.session_state.iniciado = True
    if os.path.exists(FILE_SAVE):
        try:
            with open(FILE_SAVE, "r") as f:
                d = json.load(f)
                st.session_state.lista_pacotes = d.get("lista_pacotes", [])
                st.session_state.entregues_id = d.get("entregues_id", [])
                st.session_state.ultima_pos = d.get("ultima_pos", None)
        except:
            pass

@st.cache_data
def carregar_banco():
    try:
        with open('Lugares marcados.json', 'r', encoding='utf-8') as f:
            dados_j = json.load(f)
        return {str(l['properties'].get('title') or l['properties'].get('name')).strip():
                (l['geometry']['coordinates'][1], l['geometry']['coordinates'][0])
                for l in dados_j.get('features',[])}
    except:
        return {}

banco_total = carregar_banco()

# Processa ação do mapa
if 'concluir' in st.query_params:
    pacote_id = st.query_params['concluir']
    coords = None
    for p in st.session_state.lista_pacotes:
        if p['id'] == pacote_id:
            coords = banco_total.get(p['nome'])
            break
    if coords and pacote_id not in st.session_state.entregues_id:
        st.session_state.entregues_id.append(pacote_id)
        st.session_state.ultima_pos = coords
        salvar_progresso()
        st.session_state.map_key += 1
        st.rerun()

c1, c2 = st.columns([5, 1])
with c1:
    opcoes = ["(Adicionar...)"] + list(banco_total.keys())
    busca = st.selectbox("Busca", options=opcoes, label_visibility="collapsed")
with c2:
    if st.button("➕") and busca != "(Adicionar...)":
        nid = f"{busca}_{len(st.session_state.lista_pacotes)}"
        st.session_state.lista_pacotes.append({"id": nid, "nome": busca})
        st.session_state.ultima_pos = banco_total[busca]
        salvar_progresso()
        st.session_state.map_key += 1
        st.rerun()

# Calcula pontos
pontos_para_o_mapa = []
proximo_id = None

for p in st.session_state.lista_pacotes:
    if p['nome'] not in banco_total:
        continue
    coords = banco_total[p['nome']]
    concluido = p['id'] in st.session_state.entregues_id
    cor = "#28a745" if concluido else "#dc3545"
    pontos_para_o_mapa.append({
        "id": p['id'], "lat": coords[0], "lng": coords[1], 
        "nome": p['nome'], "concluido": concluido, "cor": cor
    })

pendentes = [p for p in pontos_para_o_mapa if not p['concluido']]
if st.session_state.ultima_pos and pendentes:
    m_dist = float('inf')
    for p in pendentes:
        d = math.sqrt((st.session_state.ultima_pos[0]-p['lat'])**2 + (st.session_state.ultima_pos[1]-p['lng'])**2)
        if d < m_dist:
            m_dist = d
            proximo_id = p['id']

for p in pontos_para_o_mapa:
    if p['id'] == proximo_id: 
        p['cor'] = "#fd7e14"
    num = re.findall(r'\d+', p['nome'])
    p['txt'] = "✔" if p['concluido'] else (num[0] if num else p['nome'][:2])

centro = st.session_state.ultima_pos or [-16.15, -47.96]

# MAPA SIMPLIFICADO (sem f-string complexa)
mapa_html = """
<!DOCTYPE html>
<html>
<head>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
#map { height: 100vh; width: 100%; background: #e5e3df; }
body { margin: 0; padding: 0; }
.pin {
    width: 38px; height: 38px; border-radius: 50%; display: flex; align-items: center; 
    justify-content: center; color: white; font-weight: bold; font-family: sans-serif;
    border: 2px solid white; box-shadow: 0 2px 5px rgba(0,0,0,0.3); cursor: pointer;
}
.leaflet-popup-content { margin: 10px 10px !important; font-family: Arial, sans-serif !important; }
.popup-btn {
    width: 100%; margin: 5px 0; padding: 12px; border: none; border-radius: 8px; 
    font-weight: bold; cursor: pointer; font-size: 15px;
}
.btn-gps { background: #4285F4; color: white; }
.btn-feito { background: #34A853; color: white; }
</style>
</head>
<body>
<div id="map"></div>
<script>
""" + f"""
var map = L.map("map", {{ zoomControl: false }}).setView([{centro[0]}, {centro[1]}], 16);
L.tileLayer("http://{{s}}.google.com/vt/lyrs=m&x={{x}}&y={{y}}&z={{z}}", {{
    maxZoom: 20, subdomains:["mt0","mt1","mt2","mt3"]
}}).addTo(map);

var pontos = {json.dumps(pontos_para_o_mapa)};
var userMarker;

pontos.forEach(function(p) {{
    var icon = L.divIcon({{
        className: "", 
        html: '<div class="pin" style="background:' + p.cor + '; opacity:' + (p.concluido ? 0.6 : 1) + '">' + p.txt + '</div>',
        iconSize: [38, 38], iconAnchor: [19, 19]
    }});
    
    var marker = L.marker([p.lat, p.lng], {{icon: icon}}).addTo(map);
    
    var nome = p.nome.replace(/'/g, "\\'");
    var popupContent = '<div style="min-width: 220px;"><h4 style="margin: 0 0 15px 0; color: #333; font-size: 16px;">📍 ' + nome + '</h4><button class="popup-btn btn-gps" onclick="window.open(\\'https://www.google.com/maps/dir/?api=1&destination=' + p.lat + ',' + p.lng + '\\', \\'_blank\\')">🚀 Abrir GPS</button>';
    
    if (!p.concluido) {{
        popupContent += '<button class="popup-btn btn-feito" onclick="concluir(\\'' + p.id + '\\', ' + p.lat + ', ' + p.lng + ')">✅ Concluir</button>';
    }} else {{
        popupContent += '<p style="color: #28a745; font-weight: bold; text-align: center; margin: 10px 0;">✔️ Concluído</p>';
    }}
    popupContent += '</div>';
    
    marker.bindPopup(popupContent, {{closeButton: false, autoClose: false, closeOnEscapeKey: true}});
}});

function concluir(pacote_id, lat, lng) {{
    var url = new URL(window.location);
    url.searchParams.set("concluir", pacote_id);
    window.top.location.href = url.toString();
}}

function onLocationFound(e) {{
    if (!userMarker) {{
        userMarker = L.circleMarker(e.latlng, {{
            radius: 9, fillColor: "#4285F4", color: "white", weight: 3, opacity: 1, fillOpacity: 1
        }}).addTo(map);
    }} else {{
        userMarker.setLatLng(e.latlng);
    }}
}}
map.on("locationfound", onLocationFound);
map.locate({{ watch: true, enableHighAccuracy: true, setView: false }});
""" + """
</script>
</body>
</html>
"""

st.components.v1.html(mapa_html, height=550)

st.write("---")

if pendentes:
    p_atual = next((p for p in pontos_para_o_mapa if p['id'] == proximo_id), pendentes[0])
    st.success(f"📍 **Próximo:** {p_atual['nome']}")
    st.info("👆 Clique na bolinha laranja no mapa!")

col_save, col_clear = st.columns(2)
with col_save:
    if st.session_state.lista_pacotes:
        texto_rota = "📋 ROTA DE ENTREGAS\n" + "="*30 + "\n\n"
        for i, p in enumerate(st.session_state.lista_pacotes, 1):
            status = "✅" if p['id'] in st.session_state.entregues_id else "⏳"
            texto_rota += f"{i:2d}. {status} {p['nome']}\n"
        st.download_button("💾 SALVAR ROTA", texto_rota, "rota.txt", "text/plain", use_container_width=True)

with col_clear:
    if st.button("🗑️ LIMPAR TUDO", use_container_width=True):
        if os.path.exists(FILE_SAVE): os.remove(FILE_SAVE)
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.session_state.iniciado = False
        st.rerun()
