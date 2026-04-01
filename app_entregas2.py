import json
import streamlit as st
import re
import os
import math

# =================================================================
# 1. CONFIGURAÇÃO E MENU ESCURO (IGUAL VOCÊ PEDIU)
# =================================================================
st.markdown("""
    <style>
    /* 1. MOVE O MENU LATERAL PARA A DIREITA */
    [data-testid="stSidebar"] {
        right: 0;
        left: auto !important;
        border-left: 1px solid #333;
    }
    [data-testid="stSidebarNav"] { display: none; } /* Esconde lixo do menu */

    /* 2. POSICIONA O BOTÃO DE ABRIR NO CANTO SUPERIOR DIREITO */
    [data-testid="stSidebarCollapsedControl"] {
        background-color: #1E1E1E !important;
        color: white !important;
        border-radius: 10px !important;
        width: 45px !important;
        height: 45px !important;
        top: 10px !important;
        right: 10px !important; /* Move para a direita */
        left: auto !important;
        position: fixed !important;
        z-index: 1000000 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        box-shadow: 0px 4px 15px rgba(0,0,0,0.6) !important;
        border: 1px solid #444 !important;
    }

    /* 3. DEIXA O TOPO TRANSPARENTE */
    [data-testid="stHeader"] { background: rgba(0,0,0,0) !important; height: 0px !important; }
    
    /* Ajusta o mapa para ocupar a tela toda */
    .block-container { padding: 0rem !important; }
    [data-testid="stToolbar"], footer { display: none !important; }
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
# 3. MENU LATERAL DIREITO (GERENCIAMENTO COMPLETO)
# =================================================================
with st.sidebar:
    st.title("📍 Gerenciar Rota")
    st.write("---")

    # --- ADICIONAR QUADRAS (AGORA DENTRO DO MENU) ---
    st.subheader("➕ Adicionar Local")
    busca = st.selectbox("Selecione a Quadra", 
                         options=["(Escolha...)"] + list(banco_total.keys()), 
                         label_visibility="collapsed")
    
    if st.button("ADICIONAR À LISTA", use_container_width=True):
        if busca and busca != "(Escolha...)":
            nid = f"{busca}_{len(st.session_state.lista_pacotes)}"
            st.session_state.lista_pacotes.append({"id": nid, "nome": busca})
            st.session_state.ultima_pos = banco_total[busca]
            salvar_progresso()
            st.rerun()

    st.write("---")

    # --- SALVAR ROTA ---
    st.subheader("💾 Exportar")
    if st.session_state.lista_pacotes:
        texto_rota = "ROTA DE ENTREGAS\n" + "="*25 + "\n"
        for i, p in enumerate(st.session_state.lista_pacotes, 1):
            status = "[OK]" if p['id'] in st.session_state.entregues_id else "[ ]"
            texto_rota += f"{i}. {status} {p['nome']}\n"
        
        st.download_button(
            label="BAIXAR ROTA (.txt)",
            data=texto_rota,
            file_name="minha_rota.txt",
            mime="text/plain",
            use_container_width=True
        )
    
    st.write("")

    # --- LIMPAR TUDO ---
    if st.button("🗑️ LIMPAR MAPA", use_container_width=True, type="secondary"):
        if os.path.exists(FILE_SAVE): os.remove(FILE_SAVE)
        st.session_state.lista_pacotes = []
        st.session_state.entregues_id = []
        st.session_state.ultima_pos = None
        st.rerun()

    st.write("---")
    # Lista rápida de itens já adicionados para conferência
    if st.session_state.lista_pacotes:
        st.caption("Itens na fila:")
        for p in st.session_state.lista_pacotes[-5:]: # Mostra os últimos 5
            st.text(f"• {p['nome']}")


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
