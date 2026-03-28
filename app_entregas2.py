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
gmaps = googlemaps.Client(key=API_KEY)

# --- CSS MOBILE ---
st.set_page_config(page_title="GPS Entregador Pro", layout="wide")
st.markdown("""
    <style>
    .block-container {padding: 10px !important;}
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    .stButton>button {width: 100% !important; height: 60px !important; font-size: 20px !important; border-radius: 15px !important;}
    </style>
""", unsafe_allow_html=True)

# --- MEMÓRIA DO APP ---
FILE_SAVE = "progresso_entrega.json"

# Inicializa estados de memória
if 'pontos_carregados' not in st.session_state: st.session_state.pontos_carregados = {}
if 'entregues' not in st.session_state: st.session_state.entregues = set()
if 'ultima_pos' not in st.session_state: st.session_state.ultima_pos = None
if 'ponto_clicado' not in st.session_state: st.session_state.ponto_clicado = None

# --- NOVA MEMÓRIA DE VISUALIZAÇÃO (PARA O MAPA NÃO PULAR) ---
if 'map_center' not in st.session_state: st.session_state.map_center = None
if 'map_zoom' not in st.session_state: st.session_state.map_zoom = 16

def salvar_progresso():
    dados = {
        "pontos_carregados": st.session_state.pontos_carregados,
        "entregues": list(st.session_state.entregues),
        "ultima_pos": st.session_state.ultima_pos,
        "map_center": st.session_state.map_center,
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
                st.session_state.map_center = d.get("map_center")
                st.session_state.map_zoom = d.get("map_zoom", 16)
                return True
        except: return False
    return False

carregar_progresso()

# --- INTERFACE ---
st.title("🚚 GPS Profissional")

with st.expander("⚙️ CONFIGURAR / ENCERRAR", expanded=not st.session_state.pontos_carregados):
    base_input = st.text_input("📍 Início:", "Luziânia, GO")
    # Carregar banco de dados
    try:
        with open('Lugares marcados.json', 'r', encoding='utf-8') as f:
            dados_json = json.load(f)
        banco_total = {str(l['properties'].get('title') or l['properties'].get('name')).strip(): 
                      (l['geometry']['coordinates'][1], l['geometry']['coordinates'][0]) 
                      for l in dados_json.get('features', [])}
    except: banco_total = {}

    selecionados = st.multiselect("📦 Escolha as Quadras:", options=list(banco_total.keys()))
    
    col_a, col_b = st.columns(2)
    if col_a.button("🗺️ INICIAR"):
        geo = gmaps.geocode(base_input)
        if geo:
            pos = (geo[0]['geometry']['location']['lat'], geo[0]['geometry']['location']['lng'])
            st.session_state.ultima_pos = pos
            st.session_state.map_center = pos
            st.session_state.pontos_carregados = {s: banco_total[s] for s in selecionados}
            st.session_state.entregues = set()
            salvar_progresso()
            st.rerun()

    if col_b.button("🗑️ LIMPAR TUDO"):
        if os.path.exists(FILE_SAVE): os.remove(FILE_SAVE)
        st.session_state.pontos_carregados = {}
        st.session_state.entregues = set()
        st.rerun()

# --- MAPA ---
if st.session_state.pontos_carregados:
    # Define onde o mapa deve abrir (Usa a memória de onde você parou de mexer)
    posicao_abertura = st.session_state.map_center if st.session_state.map_center else st.session_state.ultima_pos

    m = folium.Map(
        location=posicao_abertura, 
        zoom_start=st.session_state.map_zoom,
        tiles="OpenStreetMap"
    )

    # GPS (auto_start=False para não pular sozinho!)
    LocateControl(auto_start=False, fly_to=False).add_to(m)

    for nome, coords in st.session_state.pontos_carregados.items():
        num = re.findall(r'\d+', nome)[0] if re.findall(r'\d+', nome) else "?"
        status = nome in st.session_state.entregues
        cor = "#28a745" if status else "#dc3545"
        
        icon_html = f"""<div style="background-color:{cor}; width:30px; height:30px; border-radius:50%; display:flex; 
                        align-items:center; justify-content:center; color:white; font-weight:bold; font-size:14px; 
                        border:2px solid white; box-shadow: 2px 2px 8px rgba(0,0,0,0.4); opacity:{'0.5' if status else '1.0'};">
                        {'✔' if status else num}</div>"""
        folium.Marker(location=coords, popup=nome, icon=folium.DivIcon(html=icon_html)).add_to(m)

    # Captura o mapa e os movimentos que você faz nele
    map_data = st_folium(m, use_container_width=True, height=450)

    # SALVA O ZOOM E A POSIÇÃO QUE VOCÊ MEXEU NO CELULAR
    if map_data.get("center"):
        st.session_state.map_center = [map_data["center"]["lat"], map_data["center"]["lng"]]
    if map_data.get("zoom"):
        st.session_state.map_zoom = map_data["zoom"]

    # Lógica de Clique
    if map_data.get("last_object_clicked_popup"):
        st.session_state.ponto_clicado = map_data["last_object_clicked_popup"]

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
                    salvar_progresso()
                    st.session_state.ponto_clicado = None
                    st.rerun() # Ao recarregar, ele usará o map_center salvo acima!
            else: st.success("Concluído!")

    st.write(f"📊 {len(st.session_state.entregues)} de {len(st.session_state.pontos_carregados)} concluídas")
