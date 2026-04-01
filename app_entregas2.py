import json
import streamlit as st
import re
import os
import math

# =================================================================
# 1. CONFIGURAÇÃO E CSS
# =================================================================
st.set_page_config(page_title="GPS Profissional", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    [data-testid="stHeader"], [data-testid="stSidebar"], [data-testid="stToolbar"], footer { display: none !important; }
    .block-container { padding: 0rem !important; max-width: 100% !important; }
    iframe { border: none !important; }
    .stButton>button { border-radius: 10px !important; height: 45px !important; font-weight: bold !important; }
    </style>
""", unsafe_allow_html=True)

# =================================================================
# 2. MEMÓRIA DO SISTEMA
# =================================================================
FILE_SAVE = "progresso_final.json"

if 'lista_pacotes' not in st.session_state: st.session_state.lista_pacotes = []
if 'entregues_id' not in st.session_state: st.session_state.entregues_id = []
if 'ultima_pos' not in st.session_state: st.session_state.ultima_pos = None

def salvar_progresso():
    dados = {"lista_pacotes": st.session_state.lista_pacotes, "entregues_id": st.session_state.entregues_id, "ultima_pos": st.session_state.ultima_pos}
    with open(FILE_SAVE, "w") as f: json.dump(dados, f)

if not st.session_state.lista_pacotes and os.path.exists(FILE_SAVE):
    try:
        with open(FILE_SAVE, "r") as f:
            d = json.load(f)
            st.session_state.lista_pacotes = d.get("lista_pacotes", [])
            st.session_state.entregues_id = d.get("entregues_id", [])
            st.session_state.ultima_pos = d.get("ultima_pos")
    except: pass

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

# Processar ação de conclusão via URL
query_params = st.query_params
if "concluir" in query_params:
    id_para_concluir = query_params["concluir"]
    if id_para_concluir not in st.session_state.entregues_id:
        st.session_state.entregues_id.append(id_para_concluir)
        for p in st.session_state.lista_pacotes:
            if p['id'] == id_para_concluir:
                coords = banco_total.get(p['nome'])
                if coords: st.session_state.ultima_pos = coords
        salvar_progresso()
    st.query_params.clear()
    st.rerun()

# =================================================================
# 3. BUSCA E PONTOS
# =================================================================
# Container de busca superior
with st.container():
    c1, c2 = st.columns([5, 1])
    with c1:
        busca = st.selectbox("Busca", options=["(Adicionar...)"] + list(banco_total.keys()), label_visibility="collapsed")
    with c2:
        if st.button("➕"):
            if busca and busca != "(Adicionar...)":
                nid = f"{busca}_{len(st.session_state.lista_pacotes)}"
                st.session_state.lista_pacotes.append({"id": nid, "nome": busca})
                st.session_state.ultima_pos = banco_total[busca]
                salvar_progresso(); st.rerun()

pontos_para_o_mapa = []
proximo_id = None

for p in st.session_state.lista_pacotes:
    coords = banco_total.get(p['nome'], (0,0))
    concluido = p['id'] in st.session_state.entregues_id
    cor = "#28a745" if concluido else "#dc3545"
    pontos_para_o_mapa.append({"id": p['id'], "lat": coords[0], "lng": coords[1], "nome": p['nome'], "concluido": concluido, "cor": cor})

pendentes = [p for p in pontos_para_o_mapa if not p['concluido']]
if st.session_state.ultima_pos and pendentes:
    m_dist = float('inf')
    for p in pendentes:
        d = math.sqrt((st.session_state.ultima_pos[0]-p['lat'])**2 + (st.session_state.ultima_pos[1]-p['lng'])**2)
        if d < m_dist: 
            m_dist = d
            proximo_id = p['id']

for p in pontos_para_o_mapa:
    if p['id'] == proximo_id: p['cor'] = "#fd7e14"
    num = re.findall(r'\d+', p['nome'])[0] if re.findall(r'\d+', p['nome']) else p['nome'][:2]
    p['txt'] = "✔" if p['concluido'] else num

# =================================================================
# 4. MAPA COM MENU FIXO EMBAIXO
# =================================================================
centro = st.session_state.ultima_pos if st.session_state.ultima_pos else [-16.15, -47.96]

mapa_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        #map {{ height: 100vh; width: 100%; z-index: 1; }}
        body {{ margin: 0; padding: 0; font-family: sans-serif; overflow: hidden; }}
        
        .pin {{
            width: 38px; height: 38px; border-radius: 50%;
            display: flex; align-items: center; justify-content: center;
            color: white; font-weight: bold; border: 2px solid white; 
            box-shadow: 0 2px 5px rgba(0,0,0,0.3);
        }}

        /* Painel Fixo Inferior */
        #bottom-menu {{
            position: fixed; bottom: -200px; left: 0; right: 0;
            background: white; z-index: 1000;
            padding: 20px; border-top-left-radius: 20px; border-top-right-radius: 20px;
            box-shadow: 0 -5px 15px rgba(0,0,0,0.2);
            transition: bottom 0.3s ease-out;
        }}
        #bottom-menu.active {{ bottom: 0; }}
        
        .menu-title {{ font-size: 18px; font-weight: bold; margin-bottom: 15px; color: #333; }}
        .btn-group {{ display: flex; gap: 10px; }}
        .btn {{
            flex: 1; text-align: center; padding: 12px; border-radius: 10px;
            text-decoration: none; color: white; font-weight: bold; font-size: 14px;
        }}
        .btn-gps {{ background: #4285F4; }}
        .btn-check {{ background: #28a745; }}
        .btn-close {{ background: #eee; color: #666; margin-top: 10px; display: block; }}
    </style>
</head>
<body>
    <div id="map"></div>

    <div id="bottom-menu">
        <div id="m-nome" class="menu-title">Selecione um local</div>
        <div class="btn-group">
            <a id="lnk-gps" href="#" target="_blank" class="btn btn-gps">🚀 ABRIR GPS</a>
            <a id="lnk-concluir" href="#" target="_self" class="btn btn-check">✅ CONCLUIR</a>
        </div>
        <a href="javascript:void(0)" onclick="closeMenu()" class="btn btn-close">FECHAR</a>
    </div>

    <script>
        var map = L.map('map', {{ zoomControl: false }}).setView([{centro[0]}, {centro[1]}], 16);
        
        L.tileLayer('http://{{s}}.google.com/vt/lyrs=m&x={{x}}&y={{y}}&z={{z}}', {{
            maxZoom: 20, subdomains:['mt0','mt1','mt2','mt3']
        }}).addTo(map);

        var pontos = {json.dumps(pontos_para_o_mapa)};
        var menu = document.getElementById('bottom-menu');
        
        function closeMenu() {{ menu.classList.remove('active'); }}

        pontos.forEach(function(p) {{
            var icon = L.divIcon({{
                className: '',
                html: '<div class="pin" style="background:'+p.cor+'; opacity:'+(p.concluido ? 0.6 : 1)+'">'+p.txt+'</div>',
                iconSize: [38, 38], iconAnchor: [19, 19]
            }});

            var marker = L.marker([p.lat, p.lng], {{icon: icon}}).addTo(map);
            
            marker.on('click', function() {{
                document.getElementById('m-nome').innerText = p.nome;
                document.getElementById('lnk-gps').href = 'https://www.google.com/maps/dir/?api=1&destination='+p.lat+','+p.lng;
                
                var btnConcluir = document.getElementById('lnk-concluir');
                if (p.concluido) {{
                    btnConcluir.style.display = 'none';
                }} else {{
                    btnConcluir.style.display = 'block';
                    btnConcluir.href = '?concluir=' + p.id;
                }}
                
                menu.classList.add('active');
                map.panTo([p.lat, p.lng]);
            }});
        }});

        map.on('click', function() {{ closeMenu(); }});

        // GPS DO USUÁRIO
        var userMarker;
        map.on('locationfound', function(e) {{
            if (!userMarker) {{
                userMarker = L.circleMarker(e.latlng, {{
                    radius: 9, fillColor: "#4285F4", color: "white", weight: 3, opacity: 1, fillOpacity: 1
                }}).addTo(map);
            }} else {{
                userMarker.setLatLng(e.latlng);
            }}
        }});
        map.locate({{ watch: true, enableHighAccuracy: true }});
    </script>
</body>
</html>
"""

st.components.v1.html(mapa_html, height=600)

# =================================================================
# 5. RODAPÉ (GERENCIAMENTO)
# =================================================================
col_save, col_clear = st.columns(2)

with col_save:
    if st.session_state.lista_pacotes:
        texto_rota = "📋 ROTA DE ENTREGAS\n" + "="*25 + "\n"
        for i, p in enumerate(st.session_state.lista_pacotes, 1):
            status = "✅" if p['id'] in st.session_state.entregues_id else "❌"
            texto_rota += f"{i}. {status} {p['nome']}\n"
        st.download_button("💾 SALVAR TXT", data=texto_rota, file_name="minha_rota.txt", use_container_width=True)
    else:
        st.button("💾 SALVAR TXT", disabled=True, use_container_width=True)

with col_clear:
    if st.button("🗑️ LIMPAR TUDO", use_container_width=True):
        if os.path.exists(FILE_SAVE): os.remove(FILE_SAVE)
        st.session_state.lista_pacotes = []
        st.session_state.entregues_id = []
        st.session_state.ultima_pos = None
        st.rerun()
