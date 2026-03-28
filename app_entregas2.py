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
from collections import Counter

# --- CONFIGURAÇÃO DA CHAVE ---
API_KEY = 'AIzaSyCjmSTqrG7vnAkLiXVflhBffpuk_DwBWSY' 
try:
    gmaps = googlemaps.Client(key=API_KEY)
except:
    st.error("Chave de API inválida.")

st.set_page_config(page_title="GPS Entregador Pro", layout="wide")

# --- CSS PARA TELA CHEIA, BOTÕES E REMOVER "SELECT ALL" ---
st.markdown("""
    <style>
    .block-container {padding: 10px !important;}
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    
    /* Esconde o 'Select All' do multiselect e selectbox */
    div[data-baseweb="select"] [role="option"]:first-child { display: none !important; }
    
    .stButton>button {width: 100% !important; height: 50px !important; font-size: 18px !important; font-weight: bold !important; border-radius: 12px !important;}
    </style>
""", unsafe_allow_html=True)

# --- MEMÓRIA DO APP ---
FILE_SAVE = "progresso_entrega.json"

if 'lista_pacotes' not in st.session_state: st.session_state.lista_pacotes = [] # Lista de nomes (pode repetir)
if 'entregues_id' not in st.session_state: st.session_state.entregues_id = [] # IDs dos pacotes concluídos
if 'ultima_pos' not in st.session_state: st.session_state.ultima_pos = None
if 'ponto_clicado' not in st.session_state: st.session_state.ponto_clicado = None
if 'centro_mapa' not in st.session_state: st.session_state.centro_mapa = None

def salvar_progresso():
    dados = {
        "lista_pacotes": st.session_state.lista_pacotes,
        "entregues_id": st.session_state.entregues_id,
        "ultima_pos": st.session_state.ultima_pos,
        "centro_mapa": st.session_state.centro_mapa
    }
    with open(FILE_SAVE, "w") as f: json.dump(dados, f)

def carregar_progresso():
    if os.path.exists(FILE_SAVE):
        try:
            with open(FILE_SAVE, "r") as f:
                d = json.load(f)
                st.session_state.lista_pacotes = d["lista_pacotes"]
                st.session_state.entregues_id = d["entregues_id"]
                st.session_state.ultima_pos = tuple(d["ultima_pos"]) if d["ultima_pos"] else None
                st.session_state.centro_mapa = d.get("centro_mapa")
                return True
        except: return False
    return False

if not st.session_state.lista_pacotes:
    carregar_progresso()

# --- BANCO DE DADOS ---
@st.cache_data
def carregar_banco():
    try:
        with open('Lugares marcados.json', 'r', encoding='utf-8') as f:
            dados_j = json.load(f)
        return {str(l['properties'].get('title') or l['properties'].get('name')).strip(): 
                (l['geometry']['coordinates'][1], l['geometry']['coordinates'][0]) 
                for l in dados_j.get('features', [])}
    except: return {}

banco_total = carregar_banco()

# --- INTERFACE ---
st.title("🚚 GPS Multi-Pacotes")

with st.expander("⚙️ CONFIGURAR CARGA", expanded=not st.session_state.lista_pacotes):
    base_input = st.text_input("📍 Início da Rota:", "Luziânia, GO")
    
    # BUSCADOR QUE NÃO EXCLUI
    quadra_busca = st.selectbox("🔍 Buscar Quadra (Pode repetir):", options=[""] + list(banco_total.keys()))
    if st.button("➕ ADICIONAR PACOTE"):
        if quadra_busca:
            # Adicionamos como um dicionário com ID único para diferenciar pacotes na mesma quadra
            novo_id = len(st.session_state.lista_pacotes)
            st.session_state.lista_pacotes.append({"id": novo_id, "nome": quadra_busca})
            st.toast(f"Pacote na {quadra_busca} adicionado!")

    st.write(f"📦 Pacotes na lista: {len(st.session_state.lista_pacotes)}")
    
    col_a, col_b = st.columns(2)
    if col_a.button("🗺️ MONTAR MAPA"):
        geo = gmaps.geocode(base_input)
        if geo:
            pos = (geo[0]['geometry']['location']['lat'], geo[0]['geometry']['location']['lng'])
            st.session_state.ultima_pos = pos
            st.session_state.centro_mapa = pos
            salvar_progresso()
            st.rerun()

    if col_b.button("🗑️ LIMPAR TUDO"):
        if os.path.exists(FILE_SAVE): os.remove(FILE_SAVE)
        st.session_state.lista_pacotes = []
        st.session_state.entregues_id = []
        st.session_state.centro_mapa = None
        st.rerun()

# --- LÓGICA DE SUGESTÃO ---
# Agrupar pacotes por quadra para o mapa
quadras_agrupadas = {}
for p in st.session_state.lista_pacotes:
    nome = p['nome']
    if nome not in quadras_agrupadas:
        quadras_agrupadas[nome] = {"coords": banco_total[nome], "pacotes": []}
    quadras_agrupadas[nome]['pacotes'].append(p['id'])

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

# --- MAPA ---
if st.session_state.lista_pacotes:
    centro = st.session_state.centro_mapa if st.session_state.centro_mapa else st.session_state.ultima_pos
    m = folium.Map(location=centro if centro else [0,0], zoom_start=16)
    LocateControl(auto_start=False, fly_to=False).add_to(m)

    for nome, info in quadras_agrupadas.items():
        total_p = len(info['pacotes'])
        feitos_p = sum(1 for pid in info['pacotes'] if pid in st.session_state.entregues_id)
        status_final = feitos_p == total_p # Tudo entregue nesta quadra?
        
        num_label = re.findall(r'\d+', nome)[0] if re.findall(r'\d+', nome) else nome[:2]
        if total_p > 1:
            num_label = f"{num_label}<br><small>x{total_p}</small>"
            
        sugerido = (nome == proximo_ideal)
        cor = "#28a745" if status_final else ("#fd7e14" if sugerido else "#dc3545")
        
        # BORDA ESPECIAL PARA MULTI-ENTREGA
        borda = "4px solid #007bff" if (total_p > 1 and not status_final) else "2px solid white"
        
        icon_html = f"""<div style="background-color:{cor}; width:40px; height:40px; border-radius:50%; display:flex; 
                        flex-direction:column; align-items:center; justify-content:center; color:white; font-weight:bold; 
                        font-size:13px; border:{borda}; box-shadow: 2px 2px 8px rgba(0,0,0,0.4); 
                        opacity:{'0.5' if status_final else '1.0'}; line-height: 1;">
                        {'✔' if status_final else num_label}</div>"""
        
        folium.Marker(location=info['coords'], popup=nome, icon=folium.DivIcon(html=icon_html)).add_to(m)

    map_data = st_folium(m, use_container_width=True, height=450, key="mapa_multi", returned_objects=["last_object_clicked_popup"])

    if map_data.get("last_object_clicked_popup"):
        st.session_state.ponto_clicado = map_data["last_object_clicked_popup"]

    # --- PAINEL DE AÇÃO MULTI-PACOTE ---
    if st.session_state.ponto_clicado:
        nome_sel = st.session_state.ponto_clicado
        info_q = quadras_agrupadas[nome_sel]
        st.markdown(f"### 🎯 Quadra: {nome_sel}")
        
        # Botões de ação
        c1, c2 = st.columns(2)
        with c1:
            lat_d, lon_d = info_q['coords']
            st.link_button("🚀 GPS", f"https://www.google.com/maps/dir/?api=1&destination={lat_d},{lon_d}")
        with c2:
            st.write(f"📦 Pacotes: {sum(1 for pid in info_q['pacotes'] if pid in st.session_state.entregues_id)}/{len(info_q['pacotes'])}")

        # LISTA DE PACOTES DESTA QUADRA
        for i, pid in enumerate(info_q['pacotes']):
            if pid not in st.session_state.entregues_id:
                if st.button(f"📦 Entregar Pacote {i+1}", key=f"btn_{pid}"):
                    st.session_state.entregues_id.append(pid)
                    st.session_state.ultima_pos = info_q['coords']
                    st.session_state.centro_mapa = info_q['coords']
                    salvar_progresso()
                    st.rerun()
            else:
                st.write(f"✅ Pacote {i+1} entregue")

    if proximo_ideal: st.warning(f"💡 Próxima sugerida: **{proximo_ideal}**")
