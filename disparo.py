import streamlit as st
import pandas as pd
import urllib.parse
import os

# =================================================================
# 1. CONFIGURAÇÃO VISUAL (MODERNA E ULTRA-RÁPIDA)
# =================================================================
st.set_page_config(page_title="PAINEL J&T", layout="centered")

st.markdown("""
    <style>
    /* Fundo OLED e Scroll Suave */
    .stApp { background-color: #000000; }
    [data-testid="stHeader"], [data-testid="stToolbar"], footer { display: none !important; }
    .block-container { padding: 10px !important; }

    /* Barra de Pesquisa Estilizada */
    .stTextInput > div > div > input {
        background-color: #151515 !important;
        color: white !important;
        border: 1px solid #333 !important;
        height: 45px;
        border-radius: 10px;
    }

    /* CARD DO CLIENTE */
    .card {
        background-color: #111111;
        border: 1px solid #222;
        border-radius: 12px;
        padding: 12px;
        margin-bottom: 8px;
        border-left: 4px solid #333;
    }
    .prioridade-ap { border-left-color: #ff4b4b !important; background-color: #1a0505 !important; }
    
    .nome { color: #ffffff; font-size: 16px; font-weight: bold; margin-bottom: 2px; }
    .local { color: #4285f4; font-size: 14px; font-weight: bold; } /* Quadra em azul destaque */
    .pacote-id { color: #555555; font-size: 11px; font-family: monospace; }
    
    /* BOTÃO WHATSAPP (A ESTRELA DO APP) */
    div.stButton > button {
        width: 100%;
        height: 50px !important;
        background-color: #25D366 !important; /* Cor oficial WhatsApp */
        color: white !important;
        font-weight: bold !important;
        border-radius: 10px !important;
        border: none !important;
        margin-top: 5px;
    }
    
    /* Botão OK (Discreto) */
    .btn-ok > div.stButton > button {
        background-color: #151515 !important;
        color: #555 !important;
        height: 40px !important;
        border: 1px solid #222 !important;
    }
    </style>
""", unsafe_allow_html=True)

# =================================================================
# 2. FUNÇÕES DE APOIO
# =================================================================
if 'dados' not in st.session_state: st.session_state.dados = None
if 'feitos' not in st.session_state: st.session_state.feitos = set()

def limpar_numero(tel):
    num = ''.join(filter(str.isdigit, str(tel)))
    if not num.startswith('55'): num = '55' + num
    return num

# =================================================================
# 3. TELA DE CARREGAMENTO
# =================================================================
if st.session_state.dados is None:
    st.markdown("<h2 style='color:white; text-align:center;'>📦 Iniciar Rota</h2>", unsafe_allow_html=True)
    arquivo = st.file_uploader("Suba o CSV do computador", type=["csv"], label_visibility="collapsed")
    if arquivo:
        df = pd.read_csv(arquivo)
        # ORDENAR POR QUADRA/LOCAL ANTES DE SALVAR
        df = df.sort_values(by=['Local', 'Nome'], ascending=[True, True])
        st.session_state.dados = df.to_dict('records')
        st.rerun()
else:
    # --- BARRA DE PESQUISA (LUPA) ---
    col_lupa, col_reset = st.columns([4, 1])
    with col_lupa:
        busca = st.text_input("🔍 Buscar nome ou final do pacote...", placeholder="Ex: Jose ou 4082")
    with col_reset:
        if st.button("🗑️"):
            st.session_state.dados = None
            st.session_state.feitos = set()
            st.rerun()

    # --- FILTRAGEM ---
    lista_exibicao = [d for d in st.session_state.dados if d['Pacote'] not in st.session_state.feitos]
    
    if busca:
        lista_exibicao = [
            d for d in lista_exibicao 
            if busca.lower() in str(d['Nome']).lower() or busca in str(d['Pacote'])
        ]

    st.markdown(f"<div style='color:#555; font-size:12px;'>Exibindo {len(lista_exibicao)} entregas</div>", unsafe_allow_html=True)

    # --- LISTA DE CARDS ---
    for item in lista_exibicao:
        nome_full = str(item['Nome']).upper()
        p_nome = nome_full.split()[0]
        local = str(item.get('Local', 'Sem Quadra')).upper()
        id_pacote = str(item['Pacote'])
        tel = limpar_numero(item['Telefone'])
        
        # Identificação de APARTAMENTO
        eh_ap = any(x in (local + nome_full) for x in ['AP', 'APT', 'BL', 'BLO', 'CONDOMINIO'])
        card_class = "prioridade-ap" if eh_ap else ""

        # Layout do Card
        st.markdown(f"""
            <div class="card {card_class}">
                <div class="nome">{nome_full}</div>
                <div class="local">📍 {local}</div>
                <div class="pacote-id">ID: {id_pacote}</div>
            </div>
        """, unsafe_allow_html=True)

        # Botões de Ação lado a lado
        c_zap, c_ok = st.columns([4, 1.2])
        
        with c_zap:
            msg = urllib.parse.quote(f"Olá {p_nome}, sou da J&T. Seu pacote para a *{local}* está na rota de hoje. Terá alguém pra receber?")
            st.link_button("💬 WHATSAPP", f"https://wa.me/{tel}?text={msg}")
            
        with c_ok:
            st.markdown('<div class="btn-ok">', unsafe_allow_html=True)
            if st.button("FEITO", key=f"ok_{id_pacote}"):
                st.session_state.feitos.add(id_pacote)
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
