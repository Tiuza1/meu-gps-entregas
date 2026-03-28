import json
import googlemaps
import streamlit as st
import folium
from streamlit_folium import st_folium
from folium.plugins import LocateControl
import math
import re

# --- CONFIGURAÇÃO DA CHAVE ---
API_KEY = 'AIzaSyCjmSTqrG7vnAkLiXVflhBffpuk_DwBWSY' 
gmaps = googlemaps.Client(key=API_KEY)

# --- CSS PARA TRANSFORMAR EM APP NATIVO (Mobile First) ---
st.set_page_config(page_title="GPS Entregas", layout="wide")

st.markdown("""
    <style>
    /* Remove espaços em branco e menus do Streamlit */
    .block-container {padding: 10px !important; margin: 0px !important;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Faz os botões ficarem grandes e fáceis de tocar */
    .stButton>button {
        width: 100% !important;
        height: 60px !important;
        font-size: 20px !important;
        font-weight: bold !important;
        border-radius: 15px !important;
        margin-bottom: 10px !important;
    }
    
    /* Ajusta o campo de seleção para telas pequenas */
    .stMultiSelect div div { font-size: 18px !important; }
    </style>
""", unsafe_allow_html=True)

# --- MEMÓRIA DO APP ---
if 'pontos_carregados' not in st.session_state: st.session_state.pontos_carregados = {}
if 'entregues' not in st.session_state: st.session_state.entregues = set()
if 'ultima_pos' not in st.session_state: st.session_state.ultima_pos = None
if 'ponto_clicado' not in st.session_state: st.session_state.ponto_clicado = None

def extrair_numero(texto):
    nums = re.findall(r'\d+', texto)
    return nums[0] if nums else "?"

def carregar_dados():
    try:
        with open('Lugares marcados.json', 'r', encoding='utf-8') as f:
            dados = json.load(f)
        mapa = {str(l['properties'].get('title') or l['properties'].get('name')).strip(): 
                (l['geometry']['coordinates'][1], l['geometry']['coordinates'][0]) 
                for l in dados.get('features', [])}
        return dict(sorted(mapa.items()))
    except: return {}

banco_total = carregar_dados()

# --- INTERFACE PRINCIPAL ---
st.title("🚚 Painel do Entregador")

# Painel de Configuração (Expander ajuda a economizar tela no celular)
with st.expander("⚙️ CONFIGURAR ENTREGAS DO DIA", expanded=not st.session_state.pontos_carregados):
    base_input = st.text_input("📍 Início (Sua Localização):", "Luziânia, GO")
    selecionados = st.multiselect("📦 Escolha as Quadras:", options=list(banco_total.keys()))
    
    if st.button("🗺️ INICIAR TRABALHO"):
        try:
            geo = gmaps.geocode(base_input)
            if geo:
                lat_b = geo[0]['geometry']['location']['lat']
                lng_b = geo[0]['geometry']['location']['lng']
                st.session_state.ultima_pos = (lat_b, lng_b)
                st.session_state.pontos_carregados = {s: banco_total[s] for s in selecionados}
                st.session_state.entregues = set()
                st.rerun()
        except: st.error("Endereço não encontrado.")

# --- LÓGICA DO MAPA ---
if st.session_state.pontos_carregados:
    # Cálculo matemático de sugestão
    proximo_ideal = None
    if st.session_state.ultima_pos and len(st.session_state.entregues) < len(st.session_state.pontos_carregados):
        menor_dist = float('inf')
        for n, c in st.session_state.pontos_carregados.items():
            if n not in st.session_state.entregues:
                d = math.sqrt((st.session_state.ultima_pos[0]-c[0])**2 + (st.session_state.ultima_pos[1]-c[1])**2)
                if d < menor_dist:
                    menor_dist = d
                    proximo_ideal = n

    # Mapa Interativo
    m = folium.Map(location=st.session_state.ultima_pos, zoom_start=16)
    LocateControl(auto_start=True, fly_to=True, keep_current_zoom_level=True).add_to(m)

    for nome, coords in st.session_state.pontos_carregados.items():
        num = extrair_numero(nome)
        status = nome in st.session_state.entregues
        sugerido = (nome == proximo_ideal)
        
        cor = "#28a745" if status else ("#fd7e14" if sugerido else "#dc3545")
        tamanho = "32px" if not sugerido else "45px"
        txt = "✔" if status else num

        icon_html = f"""<div style="background-color:{cor}; width:{tamanho}; height:{tamanho}; border-radius:50%; display:flex; 
                        align-items:center; justify-content:center; color:white; font-weight:bold; font-size:16px; 
                        border:2px solid white; box-shadow: 2px 2px 8px rgba(0,0,0,0.4);">{txt}</div>"""
        
        folium.Marker(location=coords, popup=nome, icon=folium.DivIcon(html=icon_html)).add_to(m)

    # Mapa em tela cheia no mobile
    st_fol_data = st_folium(m, use_container_width=True, height=450)

    if st_fol_data.get("last_object_clicked_popup"):
        st.session_state.ponto_clicado = st_fol_data["last_object_clicked_popup"]

    # --- BOTÕES DE AÇÃO (Grandes para o dedo) ---
    if st.session_state.ponto_clicado:
        nome_sel = st.session_state.ponto_clicado
        st.markdown(f"### 🎯 Quadra: {nome_sel}")
        
        lat_d, lon_d = st.session_state.pontos_carregados[nome_sel]
        col1, col2 = st.columns(2)
        
        with col1:
            url_g = f"https://www.google.com/maps/dir/?api=1&destination={lat_d},{lon_d}"
            st.link_button("🚀 GPS", url_g)
        with col2:
            if nome_sel not in st.session_state.entregues:
                if st.button("✅ FEITO"):
                    st.session_state.entregues.add(nome_sel)
                    st.session_state.ultima_pos = st.session_state.pontos_carregados[nome_sel]
                    st.session_state.ponto_clicado = None
                    st.rerun()
            else: st.success("Concluído!")

    if proximo_ideal:
        st.info(f"💡 Sugestão: Vá para a Quadra **{proximo_ideal}**")
    
    # Barra de Progresso
    feitos, total = len(st.session_state.entregues), len(st.session_state.pontos_carregados)
    st.progress(feitos/total)
    st.write(f"📊 {feitos} de {total} concluídas")
