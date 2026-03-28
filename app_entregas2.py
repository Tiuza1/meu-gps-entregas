import json
import googlemaps
import streamlit as st
import folium
from streamlit_folium import st_folium
from folium.plugins import LocateControl
import math
import re
import os
from datetime import datetime

# --- CONFIGURAÇÃO DA CHAVE ---
API_KEY = 'AIzaSyCjmSTqrG7vnAkLiXVflhBffpuk_DwBWSY' 
try:
    gmaps = googlemaps.Client(key=API_KEY)
except:
    st.error("Chave de API inválida.")

# --- INTERFACE E CSS DE CAMADAS (Z-INDEX) ---
st.set_page_config(page_title="GPS Entregador Pro", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    /* 1. MAPA EM TELA CHEIA TOTAL */
    .main .block-container {
        padding: 0 !important;
        max-width: 100% !important;
        height: 100vh !important;
    }
    iframe { width: 100% !important; height: 100vh !important; border: none; }

    /* 2. BARRA DE BUSCA FLUTUANTE (TOPO) */
    .floating-search {
        position: fixed;
        top: 10px;
        left: 50%;
        transform: translateX(-50%);
        width: 90%;
        z-index: 9999;
        background: rgba(255, 255, 255, 0.95);
        padding: 10px;
        border-radius: 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    }

    /* 3. CARD DE AÇÃO FLUTUANTE (BASE) */
    .floating-card {
        position: fixed;
        bottom: 20px;
        left: 50%;
        transform: translateX(-50%);
        width: 90%;
        z-index: 9999;
        background: white;
        padding: 20px;
        border-radius: 20px;
        box-shadow: 0 -4px 15px rgba(0,0,0,0.2);
    }

    /* Esconder elementos desnecessários do Streamlit */
    #MainMenu, footer, header {visibility: hidden;}
    div[data-baseweb="select"] [role="option"]:first-child { display: none !important; }
    
    /* Botões Grandes */
    .stButton>button {
        width: 100% !important;
        height: 55px !important;
        border-radius: 12px !important;
        font-weight: bold !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- MEMÓRIA DO APP ---
FILE_SAVE = "progresso_final.json"
if 'lista_pacotes' not in st.session_state: st.session_state.lista_pacotes = []
if 'entregues_id' not in st.session_state: st.session_state.entregues_id = []
if 'ultima_pos' not in st.session_state: st.session_state.ultima_pos = None
if 'ponto_clicado' not in st.session_state: st.session_state.ponto_clicado = None

def salvar_progresso():
    dados = {
        "lista_pacotes": st.session_state.lista_pacotes,
        "entregues_id": st.session_state.entregues_id,
        "ultima_pos": st.session_state.ultima_pos
    }
    with open(FILE_SAVE, "w") as f: json.dump(dados, f)

if not st.session_state.lista_pacotes:
    if os.path.exists(FILE_SAVE):
        with open(FILE_SAVE, "r") as f:
            d = json.load(f)
            st.session_state.lista_pacotes = d["lista_pacotes"]
            st.session_state.entregues_id = d["entregues_id"]
            st.session_state.ultima_pos = tuple(d["ultima_pos"]) if d["ultima_pos"] else None

# --- BANCO DE DADOS ---
@st.cache_data
def carregar_banco():
    with open('Lugares marcados.json', 'r', encoding='utf-8') as f:
        dados_j = json.load(f)
    return {str(l['properties'].get('title') or l['properties'].get('name')).strip(): 
            (l['geometry']['coordinates'][1], l['geometry']['coordinates'][0]) 
            for l in dados_j.get('features', [])}

banco_total = carregar_banco()

# --- CAMADA 1: BUSCA FLUTUANTE ---
with st.container():
    st.markdown('<div class="floating-search">', unsafe_allow_html=True)
    c1, c2 = st.columns([3, 1])
    with c1:
        busca = st.selectbox("Quadra:", options=[""] + list(banco_total.keys()), label_visibility="collapsed")
    with c2:
        if st.button("➕"):
            if busca:
                novo_id = f"{busca}_{len(st.session_state.lista_pacotes)}"
                st.session_state.lista_pacotes.append({"id": novo_id, "nome": busca})
                st.session_state.ultima_pos = banco_total[busca]
                salvar_progresso()
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# --- CAMADA 2: MAPA (FUNDO) ---
quadras_agrupadas = {}
for p in st.session_state.lista_pacotes:
    n = p['nome']
    if n not in quadras_agrupadas:
        quadras_agrupadas[n] = {"coords": banco_total[n], "pacotes": []}
    quadras_agrupadas[n]['pacotes'].append(p['id'])

# Sugestão Matemática
proximo_ideal = None
pendentes = [n for n, d in quadras_agrupadas.items() if not all(pid in st.session_state.entregues_id for pid in d['pacotes'])]
if st.session_state.ultima_pos and pendentes:
    menor_dist = float('inf')
    for n in pendentes:
        c = quadras_agrupadas[n]['coords']
        d = math.sqrt((st.session_state.ultima_pos[0]-c[0])**2 + (st.session_state.ultima_pos[1]-c[1])**2)
        if d < menor_dist:
            menor_dist = d
            proximo_ideal = n

# Renderização do Mapa
centro = st.session_state.ultima_pos if st.session_state.ultima_pos else [-16.15, -47.96]
m = folium.Map(location=centro, zoom_start=16, zoom_control=False)

# GPS REFORÇADO (Para evitar congelamento)
LocateControl(
    auto_start=False,
    fly_to=False,
    keep_current_zoom_level=True,
    locate_options={
        "enableHighAccuracy": True,
        "timeout": 10000,
        "maximumAge": 1000  # Força atualização a cada 1 segundo
    }
).add_to(m)

for nome, info in quadras_agrupadas.items():
    t_p = len(info['pacotes'])
    f_p = sum(1 for pid in info['pacotes'] if pid in st.session_state.entregues_id)
    concluido = (f_p == t_p)
    num = re.findall(r'\d+', nome)[0] if re.findall(r'\d+', nome) else nome[:2]
    
    cor = "#28a745" if concluido else ("#fd7e14" if nome == proximo_ideal else "#dc3545")
    borda = "4px solid #007bff" if (t_p > 1 and not concluido) else "2px solid white"
    txt = "✔" if concluido else (f"{num}<br><small>x{t_p}</small>" if t_p > 1 else num)
    
    icon_html = f"""<div style="background-color:{cor}; width:42px; height:42px; border-radius:50%; display:flex; 
                    flex-direction:column; align-items:center; justify-content:center; color:white; font-weight:bold; 
                    border:{borda}; box-shadow: 2px 2px 10px rgba(0,0,0,0.4); opacity:{'0.5' if concluido else '1.0'};">
                    {txt}</div>"""
    folium.Marker(location=info['coords'], popup=nome, icon=folium.DivIcon(html=icon_html)).add_to(m)

map_data = st_folium(m, use_container_width=True, height=1200, key="mapa_final", returned_objects=["last_object_clicked_popup"])

if map_data.get("last_object_clicked_popup"):
    st.session_state.ponto_clicado = map_data["last_object_clicked_popup"]

# --- CAMADA 3: CARD DE AÇÃO (FLUTUANTE BASE) ---
if st.session_state.ponto_clicado:
    nome_sel = st.session_state.ponto_clicado
    info_q = quadras_agrupadas[nome_sel]
    st.markdown(f'<div class="floating-card">', unsafe_allow_html=True)
    st.markdown(f"#### 📍 {nome_sel} ({sum(1 for pid in info_q['pacotes'] if pid in st.session_state.entregues_id)}/{len(info_q['pacotes'])})")
    
    col_gps, col_ok = st.columns(2)
    with col_gps:
        lat, lon = info_q['coords']
        st.link_button("🚀 GPS", f"https://www.google.com/maps/dir/?api=1&destination={lat},{lon}")
    with col_ok:
        # Pega o primeiro pacote pendente desta quadra
        id_pendente = next((pid for pid in info_q['pacotes'] if pid not in st.session_state.entregues_id), None)
        if id_pendente:
            if st.button("✅ ENTREGAR"):
                st.session_state.entregues_id.append(id_pendente)
                st.session_state.ultima_pos = info_q['coords']
                salvar_progresso()
                st.rerun()
        else:
            st.success("Tudo Concluído!")
    
    if st.button("✖️ Fechar", key="close"):
        st.session_state.ponto_clicado = None
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# Botão de Reset (No fundo da busca para não atrapalhar)
if st.sidebar.button("🗑️ LIMPAR TUDO"):
    if os.path.exists(FILE_SAVE): os.remove(FILE_SAVE)
    st.session_state.lista_pacotes = []
    st.session_state.entregues_id = []
    st.rerun()
