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

# --- CSS DEFINITIVO (TELA CHEIA TOTAL + COMPONENTES FLUTUANTES) ---
st.set_page_config(page_title="GPS Logística Pro", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    /* Remove tudo que sobra do Streamlit */
    #MainMenu, footer, header, .stDeployButton {visibility: hidden;}
    .block-container {padding: 0 !important; max-width: 100% !important; height: 100vh !important;}
    .stApp {background-color: white;}
    
    /* BARRA DE BUSCA (TOP) */
    [data-testid="stVerticalBlock"] > div:first-child {
        position: fixed !important;
        top: 20px !important;
        left: 5% !important;
        width: 90% !important;
        z-index: 999999 !important;
        background: white !important;
        padding: 10px !important;
        border-radius: 15px !important;
        box-shadow: 0 4px 20px rgba(0,0,0,0.2) !important;
    }

    /* CARD DE AÇÃO (BOTTOM) */
    [data-testid="stVerticalBlock"] > div:last-child {
        position: fixed !important;
        bottom: 30px !important;
        left: 5% !important;
        width: 90% !important;
        z-index: 999999 !important;
        background: white !important;
        padding: 15px !important;
        border-radius: 20px !important;
        box-shadow: 0 -4px 20px rgba(0,0,0,0.2) !important;
    }

    /* Botões Grandes para o dedo */
    .stButton>button {
        width: 100% !important;
        height: 55px !important;
        border-radius: 12px !important;
        font-weight: bold !important;
        font-size: 18px !important;
    }
    
    /* Esconde o Select All */
    div[data-baseweb="select"] [role="option"]:first-child { display: none !important; }
    </style>
""", unsafe_allow_html=True)

# --- MEMÓRIA DO SISTEMA ---
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
        try:
            with open(FILE_SAVE, "r") as f:
                d = json.load(f)
                st.session_state.lista_pacotes = d["lista_pacotes"]
                st.session_state.entregues_id = d["entregues_id"]
                st.session_state.ultima_pos = tuple(d["ultima_pos"]) if d["ultima_pos"] else None
        except: pass

# --- CARREGAR DADOS ---
@st.cache_data
def carregar_banco():
    with open('Lugares marcados.json', 'r', encoding='utf-8') as f:
        dados_j = json.load(f)
    return {str(l['properties'].get('title') or l['properties'].get('name')).strip(): 
            (l['geometry']['coordinates'][1], l['geometry']['coordinates'][0]) 
            for l in dados_j.get('features', [])}

banco_total = carregar_banco()

# =================================================================
# BLOCO 1: BUSCA FLUTUANTE (TOP)
# =================================================================
with st.container():
    c_search, c_add = st.columns([4, 1])
    with c_search:
        escolha = st.selectbox("Quadra", options=["Pesquisar Quadra..."] + list(banco_total.keys()), label_visibility="collapsed")
    with c_add:
        if st.button("➕"):
            if escolha and escolha != "Pesquisar Quadra...":
                novo_id = f"{escolha}_{len(st.session_state.lista_pacotes)}"
                st.session_state.lista_pacotes.append({"id": novo_id, "nome": escolha})
                st.session_state.ultima_pos = banco_total[escolha]
                salvar_progresso()
                st.rerun()

# =================================================================
# BLOCO 2: MAPA (FUNDO)
# =================================================================
quadras_agrupadas = {}
for p in st.session_state.lista_pacotes:
    n = p['nome']
    if n not in quadras_agrupadas:
        quadras_agrupadas[n] = {"coords": banco_total[n], "pacotes": []}
    quadras_agrupadas[n]['pacotes'].append(p['id'])

# Sugestão Próxima
proximo_ideal = None
pendentes = [n for n, d in quadras_agrupadas.items() if not all(pid in st.session_state.entregues_id for pid in d['pacotes'])]
if st.session_state.ultima_pos and pendentes:
    menor_dist = float('inf')
    for n in pendentes:
        c = quadras_agrupadas[n]['coords']
        dist = math.sqrt((st.session_state.ultima_pos[0]-c[0])**2 + (st.session_state.ultima_pos[1]-c[1])**2)
        if dist < menor_dist:
            menor_dist = dist
            proximo_ideal = n

# Configuração do Mapa
centro = st.session_state.ultima_pos if st.session_state.ultima_pos else [-16.15, -47.96]
m = folium.Map(location=centro, zoom_start=16, zoom_control=False, tiles="OpenStreetMap")

LocateControl(
    auto_start=False,
    fly_to=True,
    locate_options={"enableHighAccuracy": True, "maximumAge": 1000}
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
                    border:{borda}; box-shadow: 2px 2px 10px rgba(0,0,0,0.3); opacity:{'0.5' if concluido else '1.0'};">
                    {txt}</div>"""
    folium.Marker(location=info['coords'], popup=nome, icon=folium.DivIcon(html=icon_html)).add_to(m)

# Mapa ocupa a tela toda (1000px de altura garantem preenchimento no celular)
map_data = st_folium(m, use_container_width=True, height=1000, key="mapa_full", returned_objects=["last_object_clicked_popup"])

if map_data.get("last_object_clicked_popup"):
    st.session_state.ponto_clicado = map_data["last_object_clicked_popup"]

# =================================================================
# BLOCO 3: CARD DE AÇÃO (BOTTOM)
# =================================================================
with st.container():
    if st.session_state.ponto_clicado:
        nome_sel = st.session_state.ponto_clicado
        if nome_sel in quadras_agrupadas:
            info_q = quadras_agrupadas[nome_sel]
            f_p = sum(1 for pid in info_q['pacotes'] if pid in st.session_state.entregues_id)
            t_p = len(info_q['pacotes'])
            
            st.markdown(f"**📍 {nome_sel}** ({f_p}/{t_p} pacotes)")
            c_gps, c_done = st.columns(2)
            with c_gps:
                st.link_button("🚀 GPS", f"https://www.google.com/maps/dir/?api=1&destination={info_q['coords'][0]},{info_q['coords'][1]}")
            with c_done:
                id_p = next((pid for pid in info_q['pacotes'] if pid not in st.session_state.entregues_id), None)
                if id_p:
                    if st.button("✅ FEITO"):
                        st.session_state.entregues_id.append(id_p)
                        st.session_state.ultima_pos = info_q['coords']
                        salvar_progresso()
                        st.rerun()
                else: st.success("Concluído!")
            if st.button("✖️"):
                st.session_state.ponto_clicado = None
                st.rerun()
    elif proximo_ideal:
        st.info(f"💡 Sugestão: Quadra **{proximo_ideal}**")
    else:
        st.write("Aguardando seleção...")

# Botão de reset na sidebar (escondida)
if st.sidebar.button("🗑️ LIMPAR TUDO"):
    if os.path.exists(FILE_SAVE): os.remove(FILE_SAVE)
    st.session_state.lista_pacotes = []
    st.session_state.entregues_id = []
    st.rerun()
