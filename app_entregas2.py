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
# 1. CONFIGURAÇÃO DA PÁGINA
# =================================================================
st.set_page_config(page_title="GPS Multi-Pacotes", layout="wide", initial_sidebar_state="collapsed")

API_KEY = 'AIzaSyCjmSTqrG7vnAkLiXVflhBffpuk_DwBWSY' 
try:
    gmaps = googlemaps.Client(key=API_KEY)
except:
    st.error("Chave de API inválida.")

# =================================================================
# 2. CSS PARA SEPARAR OS ÍCONES
# =================================================================
st.markdown("""
    <style>
    /* ÍCONE DO MENU (STREAMLIT) - FIXO NO TOPO ESQUERDO */
    [data-testid="stSidebarCollapsedControl"] {
        background-color: #1E1E1E !important; /* Fundo escuro */
        color: white !important;
        border-radius: 8px !important;
        width: 50px !important;
        height: 50px !important;
        top: 10px !important;
        left: 10px !important;
        z-index: 999999 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        box-shadow: 0px 4px 10px rgba(0,0,0,0.3) !important;
    }
    [data-testid="stSidebarCollapsedControl"] svg {
        fill: white !important;
        width: 28px !important;
        height: 28px !important;
    }

    /* Ajuste para o conteúdo não subir demais */
    .block-container { padding-top: 4.5rem !important; }
    
    /* Esconder elementos desnecessários */
    [data-testid="stHeader"] { background-color: transparent !important; }
    [data-testid="stToolbar"] { display: none !important; }
    footer { display: none !important; }
    
    /* Estilo dos botões */
    .stButton>button { width: 100% !important; height: 50px !important; border-radius: 10px !important; font-weight: bold !important; }
    .stDownloadButton>button { background-color: #28a745 !important; color: white !important; width: 100% !important; }
    </style>
""", unsafe_allow_html=True)

# =================================================================
# 3. MEMÓRIA E FUNÇÕES
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
# 4. MENU LATERAL (CONFIGURAÇÕES)
# =================================================================
with st.sidebar:
    st.header("⚙️ Configurações")
    base_input = st.text_input("📍 Início da Rota:", "Luziânia, GO")
    if st.button("Definir Início"):
        geo = gmaps.geocode(base_input)
        if geo:
            st.session_state.ultima_pos = (geo[0]['geometry']['location']['lat'], geo[0]['geometry']['location']['lng'])
            salvar_progresso(); st.rerun()
    
    st.markdown("---")
    if st.session_state.entregues_id:
        data_h = datetime.now().strftime("%d-%m-%Y")
        nomes = [p['nome'] for p in st.session_state.lista_pacotes if p['id'] in st.session_state.entregues_id]
        txt = f"RELATÓRIO - {data_h}\nTotal: {len(st.session_state.entregues_id)}\n\n" + "\n".join([f"- {n}" for n in sorted(list(set(nomes)))])
        st.download_button("💾 Salvar Rota (TXT)", data=txt, file_name=f"rota_{data_h}.txt")

    if st.button("🗑️ Zerar Rota Atual"):
        if os.path.exists(FILE_SAVE): os.remove(FILE_SAVE)
        st.session_state.lista_pacotes = []; st.session_state.entregues_id = []; st.session_state.ultima_pos = None; st.session_state.ponto_clicado = None
        st.rerun()

# =================================================================
# 5. BUSCA E AÇÕES
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
            st.session_state.forcar_centro = banco_total[busca]; st.session_state.forcar_zoom = 16
            salvar_progresso(); st.rerun()

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
        col1, col2, col3 = st.columns([2,2,1])
        with col1: st.link_button("🚀 GPS", f"https://www.google.com/maps/dir/?api=1&destination={info['coords'][0]},{info['coords'][1]}")
        with col2:
            id_p = next((pid for pid in info['pacotes'] if pid not in st.session_state.entregues_id), None)
            if id_p and st.button("✅ FEITO"):
                st.session_state.entregues_id.append(id_p); st.session_state.ultima_pos = info['coords']; salvar_progresso(); st.rerun()
        with col3:
            if st.button("✖️"): st.session_state.ponto_clicado = None; st.rerun()

# =================================================================
# 6. MAPA (GPS MOVIDO PARA O CANTO INFERIOR DIREITO)
# =================================================================
proximo = None
pendentes = [n for n, d in quadras.items() if not all(pid in st.session_state.entregues_id for pid in d['pacotes'])]
if st.session_state.ultima_pos and pendentes:
    m_dist = float('inf')
    for n in pendentes:
        c = quadras[n]['coords']
        d = math.sqrt((st.session_state.ultima_pos[0]-c[0])**2 + (st.session_state.ultima_pos[1]-c[1])**2)
        if d < m_dist: m_dist = d; proximo = n

centro = st.session_state.ultima_pos if st.session_state.ultima_pos else [-16.15, -47.96]
m = folium.Map(location=centro, zoom_start=16, tiles="https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}", attr="Google Maps")

# --- SOLUÇÃO: GPS NO CANTO INFERIOR DIREITO ---
LocateControl(position='bottomright', fly_to=True, locate_options={"enableHighAccuracy": True}).add_to(m)

for nome, info in quadras.items():
    t_p = len(info['pacotes']); f_p = sum(1 for pid in info['pacotes'] if pid in st.session_state.entregues_id)
    concluido = (f_p == t_p); num = re.findall(r'\d+', nome)[0] if re.findall(r'\d+', nome) else nome[:2]
    cor = "#28a745" if concluido else ("#fd7e14" if nome == proximo else "#dc3545")
    borda = "4px solid #007bff" if (t_p > 1 and not concluido) else "2px solid white"
    txt = "✔" if concluido else (f"{num}<br><small>x{t_p}</small>" if t_p > 1 else num)
    icon_html = f"""<div style="background-color:{cor}; width:42px; height:42px; border-radius:50%; display:flex; flex-direction:column; align-items:center; justify-content:center; color:white; font-weight:bold; border:{borda}; box-shadow: 2px 2px 8px rgba(0,0,0,0.3); opacity:{'0.5' if concluido else '1.0'}; line-height:1;">{txt}</div>"""
    folium.Marker(location=info['coords'], popup=nome, icon=folium.DivIcon(html=icon_html)).add_to(m)

f_center = st.session_state.pop("forcar_centro", None)
f_zoom = st.session_state.pop("forcar_zoom", None)
map_data = st_folium(m, use_container_width=True, height=600, key="mapa_full", returned_objects=["last_object_clicked_popup"], center=f_center, zoom=f_zoom)

if map_data.get("last_object_clicked_popup"):
    if st.session_state.ponto_clicado != map_data["last_object_clicked_popup"]:
        st.session_state.ponto_clicado = map_data["last_object_clicked_popup"]; st.rerun()

if st.session_state.lista_pacotes and proximo and not st.session_state.ponto_clicado:
    st.info(f"💡 Sugestão: **{proximo}**")
