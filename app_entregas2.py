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

# --- CSS MOBILE ---
st.set_page_config(page_title="GPS Entregador Pro", layout="wide")
st.markdown("""
    <style>
    .block-container {padding: 10px !important;}
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    .stButton>button {width: 100% !important; height: 60px !important; font-size: 20px !important; border-radius: 15px !important;}
    .stDownloadButton>button {background-color: #28a745 !important; color: white !important; width: 100% !important; height: 60px !important; border-radius: 15px !important;}
    </style>
""", unsafe_allow_html=True)

# --- MEMÓRIA DO APP ---
FILE_SAVE = "progresso_entrega.json"

if 'pontos_carregados' not in st.session_state: st.session_state.pontos_carregados = {}
if 'entregues' not in st.session_state: st.session_state.entregues = set()
if 'ultima_pos' not in st.session_state: st.session_state.ultima_pos = None
if 'ponto_clicado' not in st.session_state: st.session_state.ponto_clicado = None
if 'centro_mapa' not in st.session_state: st.session_state.centro_mapa = None

def salvar_progresso():
    dados = {
        "pontos_carregados": st.session_state.pontos_carregados,
        "entregues": list(st.session_state.entregues),
        "ultima_pos": st.session_state.ultima_pos,
        "centro_mapa": st.session_state.centro_mapa
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
                st.session_state.centro_mapa = d.get("centro_mapa")
                return True
        except: return False
    return False

if not st.session_state.pontos_carregados:
    carregar_progresso()

# --- INTERFACE ---
st.title("🚚 GPS Profissional")

with st.expander("⚙️ CONFIGURAR / RELATÓRIO", expanded=not st.session_state.pontos_carregados):
    base_input = st.text_input("📍 Início:", "Luziânia, GO")
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
            st.session_state.centro_mapa = pos
            st.session_state.pontos_carregados = {s: banco_total[s] for s in selecionados}
            st.session_state.entregues = set()
            salvar_progresso()
            st.rerun()

    if col_b.button("🗑️ LIMPAR TUDO"):
        if os.path.exists(FILE_SAVE): os.remove(FILE_SAVE)
        st.session_state.pontos_carregados = {}
        st.session_state.entregues = set()
        st.session_state.centro_mapa = None
        st.rerun()

    if st.session_state.entregues:
        st.markdown("---")
        data_hoje = datetime.now().strftime("%d/%m/%Y")
        relat = f"RELATÓRIO DE ENTREGAS - {data_hoje}\nTotal: {len(st.session_state.entregues)}\n\n"
        for q in sorted(list(st.session_state.entregues)): relat += f"- {q}\n"
        st.download_button(label="📥 BAIXAR RELATÓRIO", data=relat, file_name=f"entregas_{datetime.now().strftime('%Y-%m-%d')}.txt")

# --- LÓGICA DE SUGESTÃO ---
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

# --- MAPA (VERSÃO SEM PISCA-PISCA) ---
if st.session_state.pontos_carregados:
    # Define o local onde o mapa vai abrir. 
    # Ele SÓ muda se você clicar em INICIAR ou FEITO.
    posicao_focal = st.session_state.centro_mapa if st.session_state.centro_mapa else st.session_state.ultima_pos

    m = folium.Map(location=posicao_focal, zoom_start=16)
    LocateControl(auto_start=False, fly_to=False).add_to(m)

    for nome, coords in st.session_state.pontos_carregados.items():
        num = re.findall(r'\d+', nome)[0] if re.findall(r'\d+', nome) else "?"
        status = nome in st.session_state.entregues
        sugerido = (nome == proximo_ideal)
        cor = "#28a745" if status else ("#fd7e14" if sugerido else "#dc3545")
        
        icon_html = f"""<div style="background-color:{cor}; width:30px; height:30px; border-radius:50%; display:flex; 
                        align-items:center; justify-content:center; color:white; font-weight:bold; font-size:14px; 
                        border:2px solid white; box-shadow: 2px 2px 8px rgba(0,0,0,0.4); opacity:{'0.5' if status else '1.0'};">
                        {'✔' if status else num}</div>"""
        folium.Marker(location=coords, popup=nome, icon=folium.DivIcon(html=icon_html)).add_to(m)

    # O SEGREDO: returned_objects vazio impede o mapa de ficar mandando dados de movimento pro Python.
    # Ele só vai mandar o dado de quando você CLICAR no marcador.
    map_data = st_folium(
        m, 
        use_container_width=True, 
        height=450,
        key="mapa_estavel",
        returned_objects=["last_object_clicked_popup"]
    )

    if map_data.get("last_object_clicked_popup"):
        if st.session_state.ponto_clicado != map_data["last_object_clicked_popup"]:
            st.session_state.ponto_clicado = map_data["last_object_clicked_popup"]
            st.rerun()

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
                    # Atualiza o centro para a próxima entrega para o mapa não pular pra longe
                    st.session_state.centro_mapa = st.session_state.pontos_carregados[nome_sel]
                    st.session_state.ponto_clicado = None
                    salvar_progresso()
                    st.rerun()
            else: st.success("Concluído!")

    if proximo_ideal:
        st.warning(f"💡 Sugestão Próxima: **{proximo_ideal}**")
    st.write(f"📊 {len(st.session_state.entregues)} de {len(st.session_state.pontos_carregados)} concluídas")
