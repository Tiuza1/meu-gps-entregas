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

# --- CSS AVANÇADO PARA OVERLAY (BUSCA E CARD) ---
st.set_page_config(page_title="GPS Entregador Pro", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    /* 1. MAPA DE FUNDO TOTAL */
    .main .block-container {
        padding: 0 !important;
        max-width: 100% !important;
    }
    .stApp { background-color: black; }

    /* 2. FORÇAR BARRA DE BUSCA A FLUTUAR NO TOPO */
    /* Localiza o primeiro bloco de widgets e fixa no topo */
    div[data-testid="stVerticalBlock"] > div:nth-child(2) {
        position: fixed !important;
        top: 15px !important;
        left: 5% !important;
        width: 90% !important;
        z-index: 10000 !important;
        background: white !important;
        padding: 10px !important;
        border-radius: 15px !important;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3) !important;
    }

    /* 3. CARD DE AÇÃO NA BASE */
    /* Localiza o último bloco de widgets e fixa embaixo */
    div[data-testid="stVerticalBlock"] > div:last-child {
        position: fixed !important;
        bottom: 25px !important;
        left: 5% !important;
        width: 90% !important;
        z-index: 10001 !important;
        background: white !important;
        padding: 15px !important;
        border-radius: 20px !important;
        box-shadow: 0 -4px 15px rgba(0,0,0,0.3) !important;
    }

    /* Esconder o lixo visual do Streamlit */
    #MainMenu, footer, header {visibility: hidden;}
    .stDeployButton {display:none;}
    
    /* Remover 'Select All' e ajustar fontes */
    div[data-baseweb="select"] [role="option"]:first-child { display: none !important; }
    .stSelectbox label { display: none !important; } /* Esconde o rótulo 'Quadra' */
    
    /* Botões Grandes Estilo Google */
    .stButton>button {
        width: 100% !important;
        height: 50px !important;
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

# =================================================================
# CAMADA 1: BUSCA (O CSS fixa este container no topo)
# =================================================================
search_container = st.container()
with search_container:
    col_search, col_add = st.columns([4, 1])
    with col_search:
        busca = st.selectbox("Busca", options=[""] + list(banco_total.keys()), label_visibility="collapsed")
    with col_add:
        if st.button("➕"):
            if busca:
                novo_id = f"{busca}_{len(st.session_state.lista_pacotes)}"
                st.session_state.lista_pacotes.append({"id": novo_id, "nome": busca})
                st.session_state.ultima_pos = banco_total[busca]
                salvar_progresso()
                st.rerun()

# =================================================================
# CAMADA 2: MAPA (FUNDO)
# =================================================================
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

centro = st.session_state.ultima_pos if st.session_state.ultima_pos else [-16.15, -47.96]
m = folium.Map(location=centro, zoom_start=16, zoom_control=False)

# GPS REFORÇADO
LocateControl(
    auto_start=False,
    fly_to=False,
    keep_current_zoom_level=True,
    locate_options={"enableHighAccuracy": True, "timeout": 10000, "maximumAge": 1000}
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

# O mapa deve vir DEPOIS da busca no código para não empurrar ela
st_folium(m, use_container_width=True, height=1000, key="mapa_final", returned_objects=["last_object_clicked_popup"])

if st.session_state.get("mapa_final") and st.session_state.mapa_final.get("last_object_clicked_popup"):
    st.session_state.ponto_clicado = st.session_state.mapa_final["last_object_clicked_popup"]

# =================================================================
# CAMADA 3: CARD DE AÇÃO (O CSS fixa este container na base)
# =================================================================
if st.session_state.ponto_clicado:
    nome_sel = st.session_state.ponto_clicado
    if nome_sel in quadras_agrupadas:
        info_q = quadras_agrupadas[nome_sel]
        action_card = st.container()
        with action_card:
            st.markdown(f"#### 📍 {nome_sel} ({sum(1 for pid in info_q['pacotes'] if pid in st.session_state.entregues_id)}/{len(info_q['pacotes'])})")
            col_gps, col_ok = st.columns(2)
            with col_gps:
                st.link_button("🚀 GPS", f"https://www.google.com/maps/dir/?api=1&destination={info_q['coords'][0]},{info_q['coords'][1]}")
            with col_ok:
                id_pendente = next((pid for pid in info_q['pacotes'] if pid not in st.session_state.entregues_id), None)
                if id_pendente:
                    if st.button("✅ ENTREGAR"):
                        st.session_state.entregues_id.append(id_pendente)
                        st.session_state.ultima_pos = info_q['coords']
                        salvar_progresso()
                        st.rerun()
                else: st.success("Concluído!")
            if st.button("✖️ Fechar"):
                st.session_state.ponto_clicado = None
                st.rerun()

# Botão de reset escondido na sidebar
if st.sidebar.button("🗑️ LIMPAR TUDO"):
    if os.path.exists(FILE_SAVE): os.remove(FILE_SAVE)
    st.session_state.lista_pacotes = []
    st.session_state.entregues_id = []
    st.rerun()
