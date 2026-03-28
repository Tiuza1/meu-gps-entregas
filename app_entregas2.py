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
# 1. CONFIGURAÇÃO - COLOQUE SUA CHAVE ABAIXO
# =================================================================
API_KEY = 'AIzaSyCjmSTqrG7vnAkLiXVflhBffpuk_DwBWSY' 
try:
    gmaps = googlemaps.Client(key=API_KEY)
except:
    st.error("Erro na Chave de API.")

# --- CSS MOBILE ---
st.set_page_config(page_title="GPS Entregador Pro", layout="wide")
st.markdown("""
    <style>
    .block-container {padding: 0px !important;}
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    .stButton>button {width: 100% !important; height: 60px !important; font-size: 18px !important; font-weight: bold !important; border-radius: 12px !important;}
    </style>
""", unsafe_allow_html=True)

# =================================================================
# 2. MEMÓRIA DO SISTEMA
# =================================================================
FILE_SAVE = "progresso_entrega.json"

if 'pontos_carregados' not in st.session_state: st.session_state.pontos_carregados = {}
if 'entregues' not in st.session_state: st.session_state.entregues = set()
if 'ultima_pos' not in st.session_state: st.session_state.ultima_pos = None
if 'ponto_clicado' not in st.session_state: st.session_state.ponto_clicado = None
# Memória de Câmera
if 'map_lat' not in st.session_state: st.session_state.map_lat = None
if 'map_lon' not in st.session_state: st.session_state.map_lon = None
if 'map_zoom' not in st.session_state: st.session_state.map_zoom = 16

def salvar_progresso():
    dados = {
        "pontos_carregados": st.session_state.pontos_carregados,
        "entregues": list(st.session_state.entregues),
        "ultima_pos": st.session_state.ultima_pos,
        "map_lat": st.session_state.map_lat,
        "map_lon": st.session_state.map_lon,
        "map_zoom": st.session_state.map_zoom
    }
    with open(FILE_SAVE, "w") as f: json.dump(dados, f)

def carregar_progresso():
    if os.path.exists(FILE_SAVE):
        try:
            with open(FILE_SAVE, "r") as f:
                d = json.load(f)
                st.session_state.pontos_carregados = d["pontos_carregados"]
                st.session_state.entregues = set(d["entregues"])
                st.session_state.ultima_pos = tuple(d["ultima_pos"]) if d["ultima_pos"] else None
                st.session_state.map_lat = d.get("map_lat")
                st.session_state.map_lon = d.get("map_lon")
                st.session_state.map_zoom = d.get("map_zoom", 16)
                return True
        except: return False
    return False

if not st.session_state.pontos_carregados:
    carregar_progresso()

# =================================================================
# 3. INTERFACE
# =================================================================
st.title("🚚 GPS Entregador Pro")

with st.expander("⚙️ CONFIGURAR / RELATÓRIO", expanded=not st.session_state.pontos_carregados):
    try:
        with open('Lugares marcados.json', 'r', encoding='utf-8') as f:
            dados_json = json.load(f)
        banco_total = {str(l['properties'].get('title') or l['properties'].get('name')).strip(): 
                      (l['geometry']['coordinates'][1], l['geometry']['coordinates'][0]) 
                      for l in dados_json.get('features', [])}
    except: banco_total = {}

    base_input = st.text_input("📍 Início:", "Luziânia, GO")
    selecionados = st.multiselect("📦 Escolha as Quadras:", options=list(banco_total.keys()))
    
    col_a, col_b = st.columns(2)
    if col_a.button("🗺️ INICIAR ROTA"):
        geo = gmaps.geocode(base_input)
        if geo:
            pos = (geo[0]['geometry']['location']['lat'], geo[0]['geometry']['location']['lng'])
            st.session_state.ultima_pos = pos
            st.session_state.map_lat, st.session_state.map_lon = pos[0], pos[1]
            st.session_state.pontos_carregados = {s: banco_total[s] for s in selecionados}
            st.session_state.entregues = set()
            salvar_progresso()
            st.rerun()

    if col_b.button("🗑️ LIMPAR TUDO"):
        if os.path.exists(FILE_SAVE): os.remove(FILE_SAVE)
        st.session_state.pontos_carregados = {}
        st.session_state.entregues = set()
        st.session_state.map_lat = None
        st.rerun()

# =================================================================
# 4. MAPA (ESTABILIZADO)
# =================================================================
if st.session_state.pontos_carregados:
    # Lógica de Sugestão
    proximo_ideal = None
    faltam = [n for n in st.session_state.pontos_carregados if n not in st.session_state.entregues]
    if st.session_state.ultima_pos and faltam:
        menor_dist = float('inf')
        for n in faltam:
            c = st.session_state.pontos_carregados[n]
            d = math.sqrt((st.session_state.ultima_pos[0]-c[0])**2 + (st.session_state.ultima_pos[1]-c[1])**2)
            if d < menor_dist:
                menor_dist = d
                proximo_ideal = n

    # Define a VISUALIZAÇÃO (Onde o mapa está agora)
    # Se já mexemos no mapa, mantém onde o dedo parou. Se não, centraliza na próxima entrega.
    if st.session_state.map_lat is not None:
        centro_view = [st.session_state.map_lat, st.session_state.map_lon]
    elif proximo_ideal:
        centro_view = st.session_state.pontos_carregados[proximo_ideal]
    else:
        centro_view = st.session_state.ultima_pos

    m = folium.Map(location=centro_view, zoom_start=st.session_state.map_zoom)
    LocateControl(auto_start=False, fly_to=False).add_to(m)

    for nome, coords in st.session_state.pontos_carregados.items():
        num = re.findall(r'\d+', nome)[0] if re.findall(r'\d+', nome) else "?"
        status = nome in st.session_state.entregues
        sugerido = (nome == proximo_ideal)
        cor = "#28a745" if status else ("#fd7e14" if sugerido else "#dc3545")
        icon_html = f"""<div style="background-color:{cor}; width:30px; height:30px; border-radius:50%; display:flex; 
                        align-items:center; justify-content:center; color:white; font-weight:bold; font-size:14px; 
                        border:2px solid white; opacity:{'0.4' if status else '1.0'};">{'✔' if status else num}</div>"""
        folium.Marker(location=coords, popup=nome, icon=folium.DivIcon(html=icon_html)).add_to(m)

    # CAPTURA TUDO: Centro, Zoom e Clique
    map_data = st_folium(
        m, 
        use_container_width=True, 
        height=450, 
        returned_objects=["last_object_clicked_popup", "center", "zoom"]
    )

    # SALVAMENTO SILENCIOSO DA CÂMERA (Sem rerun para não bugar)
    if map_data.get("center"):
        st.session_state.map_lat = map_data["center"]["lat"]
        st.session_state.map_lon = map_data["center"]["lng"]
    if map_data.get("zoom"):
        st.session_state.map_zoom = map_data["zoom"]

    # Só dá rerun se clicou em algo novo
    if map_data.get("last_object_clicked_popup"):
        if st.session_state.ponto_clicado != map_data["last_object_clicked_popup"]:
            st.session_state.ponto_clicado = map_data["last_object_clicked_popup"]
            st.rerun()

    # --- PAINEL DE AÇÃO ---
    if st.session_state.ponto_clicado:
        nome_sel = st.session_state.ponto_clicado
        st.markdown(f"### 🎯 Quadra: {nome_sel}")
        c1, c2 = st.columns(2)
        with c1:
            lat_d, lon_d = st.session_state.pontos_carregados[nome_sel]
            st.link_button("🚀 GPS", f"https://www.google.com/maps/dir/?api=1&destination={lat_d},{lon_d}")
        with c2:
            if nome_sel not in st.session_state.entregues:
                if st.button("✅ FEITO"):
                    st.session_state.entregues.add(nome_sel)
                    st.session_state.ultima_pos = st.session_state.pontos_carregados[nome_sel]
                    st.session_state.ponto_clicado = None
                    salvar_progresso()
                    st.rerun() # Aqui o mapa voltará para st.session_state.map_lat (onde estava seu dedo)
            else: st.success("Entregue! ✔️")

    if proximo_ideal: st.warning(f"💡 Sugestão Próxima: **{proximo_ideal}**")
