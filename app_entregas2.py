import json
import streamlit as st
import re
import os
import math

=================================================================
1. CONFIGURAÇÃO E MENU ESCURO (IGUAL VOCÊ PEDIU)
=================================================================
st.set_page_config(page_title="GPS Profissional", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""
<style>
/* ESCONDE O HEADER E O MENU LATERAL */
[data-testid="stHeader"], [data-testid="stSidebar"], [data-testid="stToolbar"], footer { display: none !important; }
code Code
downloadcontent_copy
expand_less
/* AJUSTA O ESPAÇAMENTO DA TELA */
.block-container { 
    padding: 0.5rem !important; 
    max-width: 100% !important;
}

/* ESTILO DOS BOTÕES LADO A LADO */
.stButton>button {
    border-radius: 10px !important;
    height: 45px !important;
    font-weight: bold !important;
}

/* ESTILO DA BARRA DE BUSCA */
.stSelectbox { margin-bottom: -15px !important; }

/* DEIXA O MAPA COM BORDAS ARREDONDADAS */
iframe { border-radius: 20px !important; border: 1px solid #333 !important; }
</style>
""", unsafe_allow_html=True)

=================================================================
2. MEMÓRIA DO SISTEMA
=================================================================
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

=================================================================
4. BUSCA E ADICIONAR
=================================================================
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

=================================================================
5. LÓGICA DE QUAIS PONTOS MOSTRAR (VISUAL LIMPO)
=================================================================
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

=================================================================
6. O MAPA COM POPUP (NOVO SISTEMA)
=================================================================
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
    cursor: pointer !important;
}}
/* ESTILO DO POPUP */
.leaflet-popup-content {{
    margin: 10px 10px !important;
    font-family: Arial, sans-serif !important;
}}
.popup-btn {{
    width: 100%; margin: 5px 0; padding: 10px;
    border: none; border-radius: 8px; font-weight: bold;
    cursor: pointer; font-size: 14px;
}}
.btn-gps {{ background: #4285F4; color: white; }}
.btn-feito {{ background: #34A853; color: white; }}
.btn-feito:disabled {{ background: #ccc; cursor: not-allowed; }}
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

// Desenha APENAS os pontos que você adicionou COM POPUP
pontos.forEach(function(p) {{
    var icon = L.divIcon({{
        className: '',
        html: '<div class="pin" style="background:'+p.cor+'; opacity:'+(p.concluido ? 0.6 : 1)+'">'+p.txt+'</div>',
        iconSize: [38, 38], iconAnchor: [19, 19]
    }});
    
    var marker = L.marker([p.lat, p.lng], {{icon: icon}}).addTo(map);
    
    // POPUP COM BOTÕES GPS E FEITO
    var popupContent = `
        <div style="min-width: 200px;">
            <h4 style="margin: 0 0 10px 0; color: #333;">📍 ${p.nome}</h4>
            <button class="popup-btn btn-gps" onclick="window.open('https://www.google.com/maps/dir/?api=1&destination=${p.lat},${p.lng}', '_blank')">🚀 Abrir GPS</button>
            ${!p.concluido ? `
                <button class="popup-btn btn-feito" id="feito-${p.id}">✅ Concluir</button>
            ` : '<p style="color: #28a745; font-weight: bold;">✔️ Concluído</p>'}
        </div>
    `;
    
    marker.bindPopup(popupContent, {{closeButton: false, autoClose: false, closeOnEscapeKey: true}});
    
    // EVENTO DO BOTÃO "FEITO" (atualiza via streamlit)
    document.getElementById('feito-' + p.id)?.addEventListener('click', function() {{
        window.parent.document.querySelector('iframe').contentWindow.postMessage({{
            action: 'concluir',
            pacote_id: p.id,
            lat: p.lat,
            lng: p.lng
        }}, '*');
        marker.closePopup();
    }});
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

// Recebe mensagens do mapa para marcar como concluído
window.addEventListener('message', function(event) {{
    if (event.data.action === 'concluir') {{
        window.parent.postMessage(event.data, '*');
    }}
}});
</script>
</body>
</html>
"""

# Componente HTML com listener para ações do popup
def mapa_component():
    st.components.v1.html(mapa_html, height=550, key="mapa_interativo")

# Listener para ações do popup (marca como concluído)
def handle_map_actions():
    if 'map_message' not in st.session_state:
        st.session_state.map_message = None
    
    # Simula recebimento da mensagem do mapa
    for msg in st.session_state.get('messages', []):
        if msg.get('type') == 'map_action' and msg.get('action') == 'concluir':
            pacote_id = msg['pacote_id']
            if pacote_id not in st.session_state.entregues_id:
                st.session_state.entregues_id.append(pacote_id)
                st.session_state.ultima_pos = [msg['lat'], msg['lng']]
                salvar_progresso()
                st.rerun()
                break

handle_map_actions()
mapa_component()

=================================================================
PAINEL DE GERENCIAMENTO (APENAS SALVAR/LIMPAR)
=================================================================
st.write("---")

# Info do próximo (sem botões)
if pendentes:
    p_atual = next(p for p in pontos_para_o_mapa if p['id'] == proximo_id) if proximo_id else pendentes[0]
    st.info(f"📍 **Próximo:** {p_atual['nome']}\n👆 *Clique na bolinha laranja para abrir GPS ou marcar como feito!*")

# LINHA DE GERENCIAMENTO (SALVAR E LIMPAR)
col_save, col_clear = st.columns(2)
with col_save:
    # AÇÃO: SALVAR ROTA .TXT
    if st.session_state.lista_pacotes:
        texto_rota = "📋 ROTA DE ENTREGAS\n" + "="*25 + "\n"
        for i, p in enumerate(st.session_state.lista_pacotes, 1):
            status = "✅" if p['id'] in st.session_state.entregues_id else "❌"
            texto_rota += f"{i}. {status} {p['nome']}\n"
        
        st.download_button(
            label="💾 SALVAR TXT",
            data=texto_rota,
            file_name="minha_rota.txt",
            mime="text/plain",
            use_container_width=True
        )
    else:
        st.button("💾 SALVAR TXT", disabled=True, use_container_width=True)

with col_clear:
    # AÇÃO: LIMPAR TUDO
    if st.button("🗑️ LIMPAR MAPA", use_container_width=True, help="Apaga todos os dados"):
        if os.path.exists(FILE_SAVE): os.remove(FILE_SAVE)
        st.session_state.lista_pacotes = []
        st.session_state.entregues_id = []
        st.session_state.ultima_pos = None
        st.rerun()
