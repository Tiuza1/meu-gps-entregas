import json
import googlemaps
import streamlit as st
import folium
from streamlit_folium import st_folium
from folium.plugins import LocateControl
import math
import re

# =================================================================
# 1. COLOQUE SUA API KEY AQUI
# =================================================================
API_KEY = 'AIzaSyCjmSTqrG7vnAkLiXVflhBffpuk_DwBWSY' 
gmaps = googlemaps.Client(key=API_KEY)

# --- FUNÇÕES DE APOIO ---

def calcular_distancia(p1, p2):
    # Cálculo de Pitágoras para proximidade real (linha reta)
    return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

def extrair_apenas_numero(texto):
    numeros = re.findall(r'\d+', texto)
    return numeros[0] if numeros else "?"

# --- CONFIGURAÇÃO DA INTERFACE ---
st.set_page_config(page_title="GPS Quadras Pro", layout="wide")

st.markdown("""
    <style>
    .block-container {padding: 0px !important;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stButton>button {width: 100%; border-radius: 10px; height: 3.5em; font-weight: bold; background-color: #007bff; color: white;}
    </style>
""", unsafe_allow_html=True)

# --- ESTADO DE SESSÃO (MEMÓRIA) ---
if 'pontos_carregados' not in st.session_state: st.session_state.pontos_carregados = {}
if 'entregues' not in st.session_state: st.session_state.entregues = set()
if 'ultima_pos' not in st.session_state: st.session_state.ultima_pos = None
if 'ponto_clicado' not in st.session_state: st.session_state.ponto_clicado = None

# --- CARREGAMENTO DE DADOS ---
def carregar_banco_dados():
    try:
        with open('Lugares marcados.json', 'r', encoding='utf-8') as f:
            dados = json.load(f)
        mapa = {}
        for local in dados.get('features', []):
            nome = str(local['properties'].get('title') or local['properties'].get('name')).strip()
            coords = local['geometry']['coordinates']
            mapa[nome] = (coords[1], coords[0])
        return dict(sorted(mapa.items()))
    except: return {}

banco_total = carregar_banco_dados()

# --- BARRA LATERAL (MENU) ---
st.sidebar.title("🚚 Configurar Entregas")
base_input = st.sidebar.text_input("📍 Endereço de Início:", "Luziânia, GO")
selecionados = st.sidebar.multiselect("Escolha as Quadras:", options=list(banco_total.keys()))

if st.sidebar.button("📍 GERAR MAPA DE TRABALHO"):
    # Usa a API do Google para descobrir a coordenada da sua BASE (casa/loja)
    try:
        geocode_result = gmaps.geocode(base_input)
        if geocode_result:
            lat_base = geocode_result[0]['geometry']['location']['lat']
            lng_base = geocode_result[0]['geometry']['location']['lng']
            st.session_state.ultima_pos = (lat_base, lng_base)
            
            st.session_state.pontos_carregados = {s: banco_total[s] for s in selecionados}
            st.session_state.entregues = set()
            st.session_state.ponto_clicado = None
            st.rerun()
    except Exception as e:
        st.sidebar.error(f"Erro ao localizar endereço: {e}")

# --- LÓGICA DE SUGESTÃO (MATEMÁTICA) ---
proximo_ideal = None
if st.session_state.ultima_pos and len(st.session_state.entregues) < len(st.session_state.pontos_carregados):
    menor_dist = float('inf')
    for nome, coords in st.session_state.pontos_carregados.items():
        if nome not in st.session_state.entregues:
            d = calcular_distancia(st.session_state.ultima_pos, coords)
            if d < menor_dist:
                menor_dist = d
                proximo_ideal = nome

# --- MAPA PRINCIPAL ---
st.title("📍 Painel de Entregas")

if st.session_state.pontos_carregados:
    # Centraliza o mapa na última posição conhecida
    m = folium.Map(location=st.session_state.ultima_pos, zoom_start=16)
    LocateControl(auto_start=False, fly_to=True).add_to(m)

    for nome, coords in st.session_state.pontos_carregados.items():
        num = extrair_apenas_numero(nome)
        status = nome in st.session_state.entregues
        sugerido = (nome == proximo_ideal)

        # Cores dos ícones numerados
        cor = "#28a745" if status else ("#fd7e14" if sugerido else "#dc3545")
        tamanho = "30px" if not sugerido else "42px"
        txt = "✔" if status else num

        icon_html = f"""<div style="background-color:{cor}; width:{tamanho}; height:{tamanho}; border-radius:50%; display:flex; 
                        align-items:center; justify-content:center; color:white; font-weight:bold; font-size:14px; 
                        border:2px solid white; box-shadow: 2px 2px 5px rgba(0,0,0,0.3);">{txt}</div>"""

        folium.Marker(location=coords, popup=nome, icon=folium.DivIcon(html=icon_html)).add_to(m)

    # Renderiza mapa e captura clique
    st_fol_data = st_folium(m, use_container_width=True, height=450, key="mapa_final")

    if st_fol_data.get("last_object_clicked_popup"):
        st.session_state.ponto_clicado = st_fol_data["last_object_clicked_popup"]

    # --- PAINEL DE AÇÃO ---
    if st.session_state.ponto_clicado:
        nome_sel = st.session_state.ponto_clicado
        st.write(f"### 🎯 Quadra: {nome_sel}")
        
        col1, col2 = st.columns(2)
        with col1:
            lat_d, lon_d = st.session_state.pontos_carregados[nome_sel]
            url_google = f"https://www.google.com/maps/dir/?api=1&destination={lat_d},{lon_d}"
            st.link_button("🚀 ABRIR GPS", url_google)
        with col2:
            if nome_sel not in st.session_state.entregues:
                if st.button("✅ CONCLUIR"):
                    st.session_state.entregues.add(nome_sel)
                    st.session_state.ultima_pos = st.session_state.pontos_carregados[nome_sel]
                    st.session_state.ponto_clicado = None
                    st.rerun()
            else: st.success("Entregue! ✔️")

    if proximo_ideal:
        st.warning(f"💡 Sugestão Próxima: **{proximo_ideal}**")
    
    feitos, total = len(st.session_state.entregues), len(st.session_state.pontos_carregados)
    st.write(f"📊 Progresso: {feitos} de {total}")
    st.progress(feitos/total if total > 0 else 0)
else:
    st.info("Configure as quadras ao lado e clique em 'Gerar Mapa'.")