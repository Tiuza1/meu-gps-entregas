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

# --- CSS MOBILE FIRST ---
st.set_page_config(page_title="GPS Entregador Pro", layout="wide")
st.markdown("""
    <style>
    .block-container {padding: 10px !important;}
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    .stButton>button {width: 100% !important; height: 60px !important; font-size: 20px !important; border-radius: 15px !important;}
    </style>
""", unsafe_allow_html=True)

# --- SISTEMA DE ARQUIVOS ---
FILE_SAVE = "progresso_entrega.json"

def salvar_historico_em_txt():
    # Só gera histórico se houver entregas feitas
    if st.session_state.entregues:
        data_hoje = datetime.now().strftime("%Y-%m-%d")
        hora_agora = datetime.now().strftime("%H:%M:%S")
        nome_arquivo = f"{data_hoje}.txt"
        
        relatorio = f"\n--- RELATÓRIO DE ENTREGAS: {data_hoje} ---\n"
        relatorio += f"Finalizado em: {hora_agora}\n"
        relatorio += f"Total Concluído: {len(st.session_state.entregues)} de {len(st.session_state.pontos_carregados)}\n"
        relatorio += "LISTA DE QUADRAS:\n"
        for q in sorted(list(st.session_state.entregues)):
            relatorio += f"- {q}\n"
        relatorio += "-"*40 + "\n"

        # Salva (modo 'a' de append: ele acrescenta no fim do arquivo se já existir)
        with open(nome_arquivo, "a", encoding="utf-8") as f:
            f.write(relatorio)
        return nome_arquivo
    return None

def salvar_progresso():
    dados = {
        "pontos_carregados": st.session_state.pontos_carregados,
        "entregues": list(st.session_state.entregues),
        "ultima_pos": st.session_state.ultima_pos
    }
    with open(FILE_SAVE, "w") as f:
        json.dump(dados, f)

def carregar_progresso():
    if os.path.exists(FILE_SAVE):
        try:
            with open(FILE_SAVE, "r") as f:
                dados = json.load(f)
                st.session_state.pontos_carregados = dados["pontos_carregados"]
                st.session_state.entregues = set(dados["entregues"])
                st.session_state.ultima_pos = tuple(dados["ultima_pos"]) if dados["ultima_pos"] else None
                return True
        except: return False
    return False

def resetar_tudo():
    # 1. Antes de apagar, salva o histórico txt
    arquivo_log = salvar_historico_em_txt()
    
    # 2. Apaga o arquivo de progresso temporário
    if os.path.exists(FILE_SAVE):
        os.remove(FILE_SAVE)
    
    # 3. Limpa a memória da tela
    st.session_state.pontos_carregados = {}
    st.session_state.entregues = set()
    st.session_state.ultima_pos = None
    st.session_state.ponto_clicado = None
    
    if arquivo_log:
        st.sidebar.success(f"Histórico salvo em: {arquivo_log}")
    st.rerun()

# --- INICIALIZAÇÃO DA MEMÓRIA ---
if 'pontos_carregados' not in st.session_state:
    if not carregar_progresso():
        st.session_state.pontos_carregados = {}
        st.session_state.entregues = set()
        st.session_state.ultima_pos = None
if 'ponto_clicado' not in st.session_state: st.session_state.ponto_clicado = None

# --- BANCO DE DADOS ---
def carregar_banco():
    try:
        with open('Lugares marcados.json', 'r', encoding='utf-8') as f:
            dados = json.load(f)
        return {str(l['properties'].get('title') or l['properties'].get('name')).strip(): 
                (l['geometry']['coordinates'][1], l['geometry']['coordinates'][0]) 
                for l in dados.get('features', [])}
    except: return {}

banco_total = carregar_banco()

# --- INTERFACE ---
st.title("🚚 GPS Profissional")

with st.expander("⚙️ CONFIGURAR / RELATÓRIOS", expanded=not st.session_state.pontos_carregados):
    base_input = st.text_input("📍 Início:", "Luziânia, GO")
    selecionados = st.multiselect("📦 Escolha as Quadras:", options=list(banco_total.keys()))
    
    col_a, col_b = st.columns(2)
    if col_a.button("🗺️ INICIAR"):
        try:
            geo = gmaps.geocode(base_input)
            if geo:
                st.session_state.ultima_pos = (geo[0]['geometry']['location']['lat'], geo[0]['geometry']['location']['lng'])
                st.session_state.pontos_carregados = {s: banco_total[s] for s in selecionados}
                st.session_state.entregues = set()
                salvar_progresso()
                st.rerun()
        except: st.error("Erro ao localizar.")
    
    if col_b.button("🗑️ ENCERRAR E SALVAR"):
        resetar_tudo()

# --- MAPA E LÓGICA ---
if st.session_state.pontos_carregados:
    # Sugestão Matemática
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

    # Mapa
    m = folium.Map(location=st.session_state.ultima_pos, zoom_start=16)
    LocateControl(auto_start=True, fly_to=True).add_to(m)

    for nome, coords in st.session_state.pontos_carregados.items():
        num = re.findall(r'\d+', nome)[0] if re.findall(r'\d+', nome) else "?"
        status = nome in st.session_state.entregues
        sugerido = (nome == proximo_ideal)
        cor = "#28a745" if status else ("#fd7e14" if sugerido else "#dc3545")
        tamanho = "32px" if not sugerido else "45px"
        
        icon_html = f"""<div style="background-color:{cor}; width:{tamanho}; height:{tamanho}; border-radius:50%; display:flex; 
                        align-items:center; justify-content:center; color:white; font-weight:bold; font-size:16px; 
                        border:2px solid white; box-shadow: 2px 2px 8px rgba(0,0,0,0.4); opacity:{'0.5' if status else '1.0'};">
                        {'✔' if status else num}</div>"""
        folium.Marker(location=coords, popup=nome, icon=folium.DivIcon(html=icon_html)).add_to(m)

    map_data = st_folium(m, use_container_width=True, height=450)
    
    if map_data.get("last_object_clicked_popup"):
        st.session_state.ponto_clicado = map_data["last_object_clicked_popup"]

    if st.session_state.ponto_clicado:
        nome_sel = st.session_state.ponto_clicado
        st.markdown(f"### 🎯 Quadra: {nome_sel}")
        col1, col2 = st.columns(2)
        with col1:
            lat_d, lon_d = st.session_state.pontos_carregados[nome_sel]
            st.link_button("🚀 GPS", f"https://www.google.com/maps/dir/?api=1&destination={lat_d},{lon_d}")
        with col2:
            if nome_sel not in st.session_state.entregues:
                if st.button("✅ FEITO"):
                    st.session_state.entregues.add(nome_sel)
                    st.session_state.ultima_pos = st.session_state.pontos_carregados[nome_sel]
                    salvar_progresso()
                    st.session_state.ponto_clicado = None
                    st.rerun()
            else: st.success("Concluído!")

    if proximo_ideal: st.info(f"💡 Sugestão: Quadra {proximo_ideal}")
    
    feitos, total = len(st.session_state.entregues), len(st.session_state.pontos_carregados)
    st.progress(feitos/total if total > 0 else 0)
    st.write(f"📊 {feitos} de {total} concluídas")
