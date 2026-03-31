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

# --- CONFIGURAÇÃO DA CHAVE (Mantida do seu código) ---
API_KEY = 'AIzaSyCjmSTqrG7vnAkLiXVflhBffpuk_DwBWSY' 
try:
    gmaps = googlemaps.Client(key=API_KEY)
except:
    st.error("Chave de API inválida.")

# --- CONFIGURAÇÃO DE TELA ---
st.set_page_config(page_title="GPS Entregador Pro", layout="wide", initial_sidebar_state="collapsed")

# CSS para Mobile e Botões
st.markdown("""
    <style>
    [data-testid="stHeader"], footer {display: none !important;}
    .block-container {padding: 10px !important;}
    .stButton>button {width: 100% !important; height: 50px !important; border-radius: 12px !important; font-weight: bold !important;}
    .btn-gps {background-color: #1E1E1E !important; color: white !important;}
    .btn-feito {background-color: #28a745 !important; color: white !important;}
    .btn-excluir {background-color: #dc3545 !important; color: white !important;}
    </style>
""", unsafe_allow_html=True)

# --- MEMÓRIA DO APP ---
FILE_SAVE = "progresso_final.json"

if 'pontos_carregados' not in st.session_state: st.session_state.pontos_carregados = {}
if 'ultima_pos' not in st.session_state: st.session_state.ultima_pos = None
if 'ponto_clicado' not in st.session_state: st.session_state.ponto_clicado = None

def salvar_progresso():
    dados = {
        "pontos_carregados": st.session_state.pontos_carregados,
        "ultima_pos": st.session_state.ultima_pos
    }
    with open(FILE_SAVE, "w") as f: json.dump(dados, f)

def carregar_progresso():
    if os.path.exists(FILE_SAVE):
        try:
            with open(FILE_SAVE, "r") as f:
                d = json.load(f)
                st.session_state.pontos_carregados = d.get("pontos_carregados", {})
                st.session_state.ultima_pos = d.get("ultima_pos")
        except: pass

if not st.session_state.pontos_carregados:
    carregar_progresso()

# --- CARREGAR BANCO DE DADOS (JSON LOCAL) ---
try:
    with open('Lugares marcados.json', 'r', encoding='utf-8') as f:
        db = json.load(f)
    banco_total = {str(l['properties'].get('title') or l['properties'].get('name')).strip(): 
                  (l['geometry']['coordinates'][1], l['geometry']['coordinates'][0]) 
                  for l in db.get('features', [])}
except:
    banco_total = {}
    st.error("Erro ao carregar Lugares marcados.json")

# --- BARRA SUPERIOR DE BUSCA ---
c1, c2 = st.columns([4, 1])
with c1:
    busca = st.selectbox("Adicionar Quadra:", [""] + list(banco_total.keys()), label_visibility="collapsed")
with c2:
    if st.button("➕"):
        if busca and busca in banco_total:
            st.session_state.pontos_carregados[busca] = banco_total[busca]
            salvar_progresso()
            st.rerun()

# --- LÓGICA DE DISTÂNCIA (SUGESTÃO) ---
proximo_ideal = None
if st.session_state.ultima_pos and st.session_state.pontos_carregados:
    menor_dist = float('inf')
    upos = st.session_state.ultima_pos
    for nome, coords in st.session_state.pontos_carregados.items():
        d = math.sqrt((upos[0]-coords[0])**2 + (upos[1]-coords[1])**2)
        if d < menor_dist:
            menor_dist = d
            proximo_ideal = nome

# --- MAPA FOLIUM ---
# Centraliza no último ponto ou numa posição padrão
centro = st.session_state.ultima_pos if st.session_state.ultima_pos else [-16.15, -47.96]

m = folium.Map(location=centro, zoom_start=15, tiles="OpenStreetMap")
LocateControl(auto_start=False, fly_to=True).add_to(m)

for nome, coords in st.session_state.pontos_carregados.items():
    num = re.findall(r'\d+', nome)[0] if re.findall(r'\d+', nome) else nome[:2]
    cor = "#fd7e14" if nome == proximo_ideal else "#dc3545" # Laranja se for o próximo, Vermelho se não.
    
    icon_html = f'''<div style="background-color:{cor}; width:35px; height:35px; border-radius:50%; 
                    display:flex; align-items:center; justify-content:center; color:white; 
                    font-weight:bold; border:2px solid white; box-shadow: 2px 2px 5px rgba(0,0,0,0.3);">
                    {num}</div>'''
    
    folium.Marker(
        location=coords,
        popup=nome,
        icon=folium.DivIcon(html=icon_html)
    ).add_to(m)

# Renderiza o mapa e captura o clique
map_data = st_folium(
    m, 
    use_container_width=True, 
    height=450,
    key="mapa_estavel",
    returned_objects=["last_object_clicked_popup"]
)

# Atualiza ponto clicado
if map_data.get("last_object_clicked_popup"):
    if st.session_state.ponto_clicado != map_data["last_object_clicked_popup"]:
        st.session_state.ponto_clicado = map_data["last_object_clicked_popup"]
        st.rerun()

# --- PAINEL DE AÇÃO (APARECE AO CLICAR NO PONTO) ---
if st.session_state.ponto_clicado and st.session_state.ponto_clicado in st.session_state.pontos_carregados:
    nome_sel = st.session_state.ponto_clicado
    coords_sel = st.session_state.pontos_carregados[nome_sel]
    
    st.markdown(f"### 🎯 {nome_sel}")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.link_button("🚀 GPS", f"https://www.google.com/maps/dir/?api=1&destination={coords_sel[0]},{coords_sel[1]}")
    
    with col2:
        if st.button("✅ FEITO", key="btn_feito"):
            # 1. Salva como última posição para o cálculo da próxima
            st.session_state.ultima_pos = coords_sel
            # 2. REMOVE do dicionário para sumir do mapa
            del st.session_state.pontos_carregados[nome_sel]
            st.session_state.ponto_clicado = None
            salvar_progresso()
            st.rerun()
            
    with col3:
        if st.button("🗑️ EXCLUIR", key="btn_excluir"):
            # Apenas remove do dicionário
            del st.session_state.pontos_carregados[nome_sel]
            st.session_state.ponto_clicado = None
            salvar_progresso()
            st.rerun()

# --- RODAPÉ ---
with st.sidebar:
    st.header("Configurações")
    if st.button("🗑️ LIMPAR TODA LISTA"):
        st.session_state.pontos_carregados = {}
        st.session_state.ultima_pos = None
        salvar_progresso()
        st.rerun()

if proximo_ideal:
    st.info(f"💡 Sugestão: Vá para **{proximo_ideal}**")
