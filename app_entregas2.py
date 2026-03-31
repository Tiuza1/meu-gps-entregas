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

# =================================================================
# 1. CONFIGURAÇÃO E CSS (MENU ESCURO NO TOPO ESQUERDO)
# =================================================================
st.set_page_config(page_title="GPS Entregas", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    /* OCULTA O HEADER PADRÃO */
    [data-testid="stHeader"], [data-testid="stToolbar"], footer { display: none !important; }

    /* BOTÃO DO MENU ESCURO - CANTO SUPERIOR ESQUERDO */
    [data-testid="stSidebarCollapsedControl"] {
        background-color: #1E1E1E !important;
        color: white !important;
        border-radius: 8px !important;
        width: 55px !important;
        height: 55px !important;
        top: 10px !important;
        left: 10px !important;
        z-index: 1000000 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        box-shadow: 0px 4px 10px rgba(0,0,0,0.3) !important;
    }
    [data-testid="stSidebarCollapsedControl"] svg { fill: white !important; width: 30px !important; height: 30px !important; }

    /* AJUSTE DE ESPAÇAMENTO */
    .block-container { padding: 4.5rem 0.5rem 0.5rem 0.5rem !important; }
    
    /* BOTÕES LARGOS PARA CELULAR */
    .stButton>button { width: 100% !important; height: 55px !important; border-radius: 12px !important; font-weight: bold !important; }
    .stDownloadButton>button { background-color: #28a745 !important; color: white !important; width: 100% !important; }
    </style>
""", unsafe_allow_html=True)

# =================================================================
# 2. MEMÓRIA DO SISTEMA
# =================================================================
FILE_SAVE = "progresso_final.json"

if 'lista_pacotes' not in st.session_state: st.session_state.lista_pacotes = []
if 'entregues_id' not in st.session_state: st.session_state.entregues_id = []
if 'ultima_pos' not in st.session_state: st.session_state.ultima_pos = None
if 'ponto_clicado' not in st.session_state: st.session_state.ponto_clicado = None

def salvar_progresso():
    dados = {"lista_pacotes": st.session_state.lista_pacotes, "entregues_id": st.session_state.entregues_id, "ultima_pos": st.session_state.ultima_pos}
    with open(FILE_SAVE, "w") as f: json.dump(dados, f)

if not st.session_state.lista_pacotes and os.path.exists(FILE_SAVE):
    try:
        with open(FILE_SAVE, "r") as f:
            d = json.load(f)
            st.session_state.lista_pacotes = d.get("lista_pacotes", [])
            st.session_state.entregues_id = d.get("entregues_id", [])
            st.session_state.ultima_pos = tuple(d["ultima_pos"]) if d.get("ultima_pos") else None
    except: pass

@st.cache_data
def carregar_banco():
    try:
        with open('Lugares marcados.json', 'r', encoding='utf-8') as f:
            dados_j = json.load(f)
        return {str(l['properties'].get('title') or l['properties'].get('name')).strip(): (l['geometry']['coordinates'][1], l['geometry']['coordinates'][0]) for l in dados_j.get('features',[])}
    except: return {}

banco_total = carregar_banco()

# =================================================================
# 3. MENU LATERAL (SIDEBAR)
# =================================================================
with st.sidebar:
    st.header("⚙️ Configurações")
    if st.button("🗑️ LIMPAR ROTA ATUAL"):
        if os.path.exists(FILE_SAVE): os.remove(FILE_SAVE)
        st.session_state.lista_pacotes = []; st.session_state.entregues_id = []; st.session_state.ultima_pos = None; st.session_state.ponto_clicado = None
        st.rerun()
    
    st.markdown("---")
    if st.session_state.entregues_id:
        data_h = datetime.now().strftime("%d-%m-%Y")
        nomes = [p['nome'] for p in st.session_state.lista_pacotes if p['id'] in st.session_state.entregues_id]
        txt = f"RELATÓRIO {data_h}\nTotal: {len(st.session_state.entregues_id)}\n\n" + "\n".join([f"- {n}" for n in sorted(list(set(nomes)))])
        st.download_button("💾 SALVAR RELATÓRIO (TXT)", data=txt, file_name=f"rota_{data_h}.txt")

# =================================================================
# 4. BUSCA E PAINEL DE AÇÃO
# =================================================================
c1, c2 = st.columns([4, 1])
with c1:
    busca = st.selectbox("Busca", options=["(Adicionar Quadra...)"] + list(banco_total.keys()), label_visibility="collapsed")
with c2:
    if st.button("➕"):
        if busca and busca != "(Adicionar Quadra...)":
            nid = f"{busca}_{len(st.session_state.lista_pacotes)}"
            st.session_state.lista_pacotes.append({"id": nid, "nome": busca})
            st.session_state.ultima_pos = banco_total[busca]
            st.session_state.forcar_centro = banco_total[busca]
            salvar_progresso(); st.rerun()

# Lógica de agrupamento (para mostrar o número de pacotes na bolinha)
quadras = {}
for p in st.session_state.lista_pacotes:
    n = p['nome']
    if n not in quadras: quadras[n] = {"coords": banco_total.get(n, (0,0)), "pacotes": []}
    quadras[n]['pacotes'].append(p['id'])

if st.session_state.ponto_clicado:
    n_sel = st.session_state.ponto_clicado
    if n_sel in quadras:
        info = quadras[n_sel]; f_p = sum(1 for pid in info['pacotes'] if pid in st.session_state.entregues_id); t_p = len(info['pacotes'])
        st.info(f"📍 **{n_sel}** ({f_p}/{t_p})")
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1: st.link_button("🚀 GPS", f"https://www.google.com/maps/dir/?api=1&destination={info['coords'][0]},{info['coords'][1]}")
        with col2:
            id_p = next((pid for pid in info['pacotes'] if pid not in st.session_state.entregues_id), None)
            if id_p and st.button("✅ FEITO"):
                st.session_state.entregues_id.append(id_p); st.session_state.ultima_pos = info['coords']; salvar_progresso(); st.rerun()
        with col3:
            if st.button("✖️"): st.session_state.ponto_clicado = None; st.rerun()

# =================================================================
# 5. MAPA (VISUAL LIMPO E GPS LISO)
# =================================================================
# Lógica do próximo ponto
proximo = None
pendentes = [n for n, d in quadras.items() if not all(pid in st.session_state.entregues_id for pid in d['pacotes'])]
if st.session_state.ultima_pos and pendentes:
    m_dist = float('inf')
    for n in pendentes:
        c = quadras[n]['coords']; d = math.sqrt((st.session_state.ultima_pos[0]-c[0])**2 + (st.session_state.ultima_pos[1]-c[1])**2)
        if d < m_dist: m_dist = d; proximo = n

centro = st.session_state.ultima_pos if st.session_state.ultima_pos else [-16.15, -47.96]
m = folium.Map(location=centro, zoom_start=16, tiles="https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}", attr="Google Maps")

# GPS NO CANTO INFERIOR DIREITO
LocateControl(position='bottomright', fly_to=True, locate_options={"enableHighAccuracy": True, "watch": True}).add_to(m)

# DESENHA APENAS OS PONTOS DA ROTA (ESTILO IGUAL AO SEU PRINT)
for nome, info in quadras.items():
    t_p = len(info['pacotes']); f_p = sum(1 for pid in info['pacotes'] if pid in st.session_state.entregues_id)
    concluido = (f_p == t_p)
    
    # Define a cor e o ícone (Exatamente como no print)
    cor = "#28a745" if concluido else ("#fd7e14" if nome == proximo else "#dc3545")
    num_txt = "✔" if concluido else re.findall(r'\d+', nome)[0] if re.findall(r'\d+', nome) else nome[:2]
    
    icon_html = f"""
    <div style="
        background-color: {cor}; 
        width: 40px; height: 40px; 
        border-radius: 50%; 
        border: 2px solid white; 
        display: flex; align-items: center; justify-content: center; 
        color: white; font-weight: bold; font-size: 14px;
        box-shadow: 0px 2px 5px rgba(0,0,0,0.4);
        opacity: {0.6 if concluido else 1};">
        {num_txt}
    </div>"""
    
    folium.Marker(location=info['coords'], popup=nome, icon=folium.DivIcon(html=icon_html)).add_to(m)

# Renderiza o mapa (Otimizado para não travar o GPS)
map_data = st_folium(
    m, 
    use_container_width=True, 
    height=600, 
    key="mapa_limpo",
    returned_objects=["last_object_clicked_popup"], # Não sincroniza GPS para não dar lag
    center=st.session_state.get("forcar_centro"),
    zoom=16
)

if map_data.get("last_object_clicked_popup"):
    if st.session_state.ponto_clicado != map_data["last_object_clicked_popup"]:
        st.session_state.ponto_clicado = map_data["last_object_clicked_popup"]; st.rerun()

if st.session_state.lista_pacotes and proximo and not st.session_state.ponto_clicado:
    st.info(f"💡 Sugestão Próxima: **{proximo}**")
