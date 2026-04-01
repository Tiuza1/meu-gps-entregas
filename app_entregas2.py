import json
import streamlit as st
import re
import os
import math

# 1. CONFIGURAÇÃO (Sempre primeiro)
st.set_page_config(page_title="GPS Profissional", layout="wide", initial_sidebar_state="collapsed")

# 2. FUNÇÕES DE SUPORTE (Precisam ser definidas antes de serem usadas)
def salvar_progresso():
    dados = {"lista_pacotes": st.session_state.lista_pacotes, "entregues_id": st.session_state.entregues_id, "ultima_pos": st.session_state.ultima_pos}
    with open("progresso_final.json", "w") as f: json.dump(dados, f)

@st.cache_data
def carregar_banco():
    try:
        with open('Lugares marcados.json', 'r', encoding='utf-8') as f:
            dados_j = json.load(f)
        return {str(l['properties'].get('title') or l['properties'].get('name')).strip(): 
                (l['geometry']['coordinates'][1], l['geometry']['coordinates'][0]) 
                for l in dados_j.get('features',[])}
    except: return {}

# 3. CRIAR AS VARIÁVEIS BASE (Aqui resolvemos o erro banco_total)
banco_total = carregar_banco()

if 'lista_pacotes' not in st.session_state: st.session_state.lista_pacotes = []
if 'entregues_id' not in st.session_state: st.session_state.entregues_id = []
if 'ultima_pos' not in st.session_state: st.session_state.ultima_pos = None

# 4. LÓGICA DE URL (Resolve a duplicação: Limpa tudo antes de desenhar a tela)
qp = st.query_params
if "concluir" in qp:
    id_alvo = qp["concluir"]
    if id_alvo not in st.session_state.entregues_id:
        st.session_state.entregues_id.append(id_alvo)
        # Atualiza a posição para o local entregue
        for p in st.session_state.lista_pacotes:
            if p['id'] == id_alvo:
                st.session_state.ultima_pos = banco_total.get(p['nome'])
        salvar_progresso()
        st.query_params.clear()
        st.rerun() # Mata o processo atual e recomeça a página limpa

# 5. ESTILOS CSS
st.markdown("""<style>... seu css aqui ...</style>""", unsafe_allow_html=True)

# 6. BUSCA E ADICIONAR (Dentro de um container para travar a interface)
with st.container():
    c1, c2 = st.columns([5, 1])
    with c1:
        busca = st.selectbox(
            "Busca", 
            options=["(Adicionar...)"] + list(banco_total.keys()), 
            label_visibility="collapsed",
            key="busca_principal_v1"
        )
    with c2:
        if st.button("➕", key="btn_add_v1"):
            if busca and busca != "(Adicionar...)":
                nid = f"{busca}_{len(st.session_state.lista_pacotes)}"
                st.session_state.lista_pacotes.append({"id": nid, "nome": busca})
                st.session_state.ultima_pos = banco_total[busca]
                salvar_progresso()
                st.rerun()
# =================================================================
# 4. PREPARAÇÃO DOS PONTOS
# =================================================================
pontos_para_o_mapa = []
proximo_id = None

for p in st.session_state.lista_pacotes:
    coords = banco_total.get(p['nome'], (0,0))
    concluido = p['id'] in st.session_state.entregues_id
    cor = "#28a745" if concluido else "#dc3545"
    pontos_para_o_mapa.append({"id": p['id'], "lat": coords[0], "lng": coords[1], "nome": p['nome'], "concluido": concluido, "cor": cor})

# Achar o mais próximo para pintar de Laranja
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
# 5. O MAPA COM POPUP (NOVO)
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
        .popup-btn {{
            display: block; width: 100%; text-align: center;
            padding: 10px 0; margin-top: 8px; border-radius: 8px;
            text-decoration: none; color: white; font-family: sans-serif;
            font-weight: bold; font-size: 14px;
        }}
    </style>
</head>
<body>
    <div id="map"></div>
    <script>
        var map = L.map('map', {{ zoomControl: false }}).setView([{centro[0]}, {centro[1]}], 16);
        
        L.tileLayer('http://{{s}}.google.com/vt/lyrs=m&x={{x}}&y={{y}}&z={{z}}', {{
            maxZoom: 20, subdomains:['mt0','mt1','mt2','mt3']
        }}).addTo(map);

        var pontos = {json.dumps(pontos_para_o_mapa)};
        
        pontos.forEach(function(p) {{
            var icon = L.divIcon({{
                className: '',
                html: '<div class="pin" style="background:'+p.cor+'; opacity:'+(p.concluido ? 0.6 : 1)+'">'+p.txt+'</div>',
                iconSize: [38, 38], iconAnchor: [19, 19]
            }});

            // CONTEÚDO DO POPUP
            var popupContent = '<div style="min-width:160px;">' +
                '<strong style="font-size:16px;">'+p.nome+'</strong><br>' +
                '<a href="https://www.google.com/maps/dir/?api=1&destination='+p.lat+','+p.lng+'" target="_blank" class="popup-btn" style="background:#4285F4;">🚀 ABRIR GPS</a>';
            
            if (!p.concluido) {{
                // Esse link recarrega a página passando o ID para o Streamlit marcar como concluído
                popupContent += '<a href="?concluir='+p.id+'" target="_self" class="popup-btn" style="background:#28a745;">✅ CONCLUIR</a>';
            }}
            
            popupContent += '</div>';

            L.marker([p.lat, p.lng], {{icon: icon}}).addTo(map).bindPopup(popupContent);
        }});

        // GPS DO USUÁRIO
        var userMarker;
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

# =================================================================
# 6. RODAPÉ (SOMENTE GERENCIAMENTO)
# =================================================================
st.write("---")
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
