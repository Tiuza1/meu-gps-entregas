import json
import streamlit as st
import re
import os
import math

# =================================================================
# 1. CONFIGURAÇÃO E MENU ESCURO (IGUAL VOCÊ PEDIU)
# =================================================================
st.set_page_config(page_title="GPS Profissional", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    /* ESCONDE TUDO O QUE NÃO PRECISA */
    [data-testid="stHeader"], [data-testid="stToolbar"], footer { display: none !important; }

    /* ÍCONE DO MENU ESCURO E NO TOPO ESQUERDO */
    [data-testid="stSidebarCollapsedControl"] {
        background-color: #1E1E1E !important;
        color: white !important;
        border-radius: 10px !important;
        width: 55px !important;
        height: 55px !important;
        top: 8px !important;
        left: 8px !important;
        z-index: 1000000 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        box-shadow: 0px 4px 10px rgba(0,0,0,0.4) !important;
    }
    [data-testid="stSidebarCollapsedControl"] svg { fill: white !important; width: 32px !important; height: 32px !important; }

    .block-container { padding: 4.5rem 0.5rem 0.5rem 0.5rem !important; }
    .stButton>button { width: 100% !important; height: 50px !important; border-radius: 12px !important; font-weight: bold !important; }
    iframe { border: none !important; border-radius: 15px !important; }
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

# =================================================================
# 3. MENU LATERAL (AÇÕES)
# =================================================================
with st.sidebar:
    st.header("⚙️ Menu de Controle")
    st.markdown("---")

    # --- AÇÃO 1: SALVAR ROTA (.txt) ---
    if st.session_state.lista_pacotes:
        # Criar o conteúdo do arquivo TXT
        conteudo_txt = "📋 ROTA DE ENTREGAS\n"
        conteudo_txt += "="*30 + "\n"
        for i, p in enumerate(st.session_state.lista_pacotes, 1):
            status = "[CONCLUÍDO]" if p['id'] in st.session_state.entregues_id else "[PENDENTE]"
            conteudo_txt += f"{i}. {status} - {p['nome']}\n"
        
        st.download_button(
            label="💾 SALVAR ROTA (.txt)",
            data=conteudo_txt,
            file_name="rota_entregas.txt",
            mime="text/plain"
        )
    else:
        st.info("Adicione pontos para salvar uma rota.")

    st.markdown("---")

    # --- AÇÃO 2: LIMPAR MAPA ---
    if st.button("🗑️ LIMPAR TUDO", help="Apaga todos os pontos e o progresso salvo"):
        # Remove o arquivo físico
        if os.path.exists(FILE_SAVE):
            os.remove(FILE_SAVE)
        
        # Reseta o estado da sessão
        st.session_state.lista_pacotes = []
        st.session_state.entregues_id = []
        st.session_state.ultima_pos = None
        
        st.toast("Mapa limpo com sucesso!")
        st.rerun()

    st.markdown("---")
    st.write(f"📍 Total de pontos: {len(st.session_state.lista_pacotes)}")
    st.write(f"✅ Concluídos: {len(st.session_state.entregues_id)}")

# =================================================================
# 4. BUSCA E ADICIONAR
# =================================================================
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

# =================================================================
# 5. LÓGICA DE QUAIS PONTOS MOSTRAR (VISUAL LIMPO)
# =================================================================
proximo_id = None
pontos_para_o_mapa = []

# Filtramos apenas os que você adicionou
for p in st.session_state.lista_pacotes:
    coords = banco_total.get(p['nome'], (0,0))
    concluido = p['id'] in st.session_state.entregues_id
    
    # Lógica da cor (Verde, Laranja ou Vermelho)
    cor = "#28a745" if concluido else "#dc3545" # Padrão
    pontos_para_o_mapa.append({"id": p['id'], "lat": coords[0], "lng": coords[1], "nome": p['nome'], "concluido": concluido, "cor": cor})

# Achar o mais próximo (Laranja)
pendentes = [p for p in pontos_para_o_mapa if not p['concluido']]
if st.session_state.ultima_pos and pendentes:
    m_dist = float('inf')
    for p in pendentes:
        d = math.sqrt((st.session_state.ultima_pos[0]-p['lat'])**2 + (st.session_state.ultima_pos[1]-p['lng'])**2)
        if d < m_dist: 
            m_dist = d
            proximo_id = p['id']

# Atualiza a cor do próximo para Laranja e define texto
for p in pontos_para_o_mapa:
    if p['id'] == proximo_id: p['cor'] = "#fd7e14"
    num = re.findall(r'\d+', p['nome'])[0] if re.findall(r'\d+', p['nome']) else p['nome'][:2]
    p['txt'] = "✔" if p['concluido'] else num

# =================================================================
# 6. O MAPA RÁPIDO (IGUAL AO DAS BOLINHAS VERMELHAS)
# =================================================================
centro = st.session_state.ultima_pos if st.session_state.ultima_pos else [-16.15, -47.96]

mapa_html = f"""
<!DOCTYPE html>
<html>
<head>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        #map {{ height: 100vh; width: 100%; background: #e5e3df; }}
        body {{ margin: 0; padding: 0; }}
        .pin {{
            width: 38px; height: 38px; border-radius: 50%;
            display: flex; align-items: center; justify-content: center;
            color: white; font-weight: bold; font-family: sans-serif;
            border: 2px solid white; box-shadow: 0 2px 5px rgba(0,0,0,0.3);
        }}
    </style>
</head>
<body>
    <div id="map"></div>
    <script>
        var map = L.map('map', {{ zoomControl: false }}).setView([{centro[0]}, {centro[1]}], 16);
        
        // Camada do Google Maps
        L.tileLayer('http://{{s}}.google.com/vt/lyrs=m&x={{x}}&y={{y}}&z={{z}}', {{
            maxZoom: 20, subdomains:['mt0','mt1','mt2','mt3']
        }}).addTo(map);

        var pontos = {json.dumps(pontos_para_o_mapa)};
        var userMarker;

        // Desenha APENAS os pontos que você adicionou
        pontos.forEach(function(p) {{
            var icon = L.divIcon({{
                className: '',
                html: '<div class="pin" style="background:'+p.cor+'; opacity:'+(p.concluido ? 0.6 : 1)+'">'+p.txt+'</div>',
                iconSize: [38, 38], iconAnchor: [19, 19]
            }});
            L.marker([p.lat, p.lng], {{icon: icon}}).addTo(map);
        }});

        // GPS LISO (Igual ao código que você gostou)
        function onLocationFound(e) {{
            if (!userMarker) {{
                userMarker = L.circleMarker(e.latlng, {{
                    radius: 9, fillColor: "#4285F4", color: "white", weight: 3, opacity: 1, fillOpacity: 1
                }}).addTo(map);
            }} else {{
                userMarker.setLatLng(e.latlng);
            }}
        }}
        map.on('locationfound', onLocationFound);
        map.locate({{ watch: true, enableHighAccuracy: true, setView: false }});
    </script>
</body>
</html>
"""

st.components.v1.html(mapa_html, height=550)

# Painel de Controle (Abaixo do mapa)
if pendentes:
    p_atual = next(p for p in pontos_para_o_mapa if p['id'] == proximo_id) if proximo_id else pendentes[0]
    st.info(f"📍 **Próximo:** {p_atual['nome']}")
    c_gps, c_ok = st.columns(2)
    with c_gps:
        st.link_button("🚀 GPS", f"https://www.google.com/maps/dir/?api=1&destination={p_atual['lat']},{p_atual['lng']}")
    with c_ok:
        if st.button("✅ FEITO"):
            st.session_state.entregues_id.append(p_atual['id'])
            st.session_state.ultima_pos = [p_atual['lat'], p_atual['lng']]
            salvar_progresso(); st.rerun()
