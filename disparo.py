import streamlit as st
import pandas as pd
import urllib.parse
import os

# =================================================================
# 1. CONFIGURAÇÃO VISUAL (FOCO EM BATERIA E TOQUE RÁPIDO)
# =================================================================
st.set_page_config(page_title="DISPARO J&T", layout="centered")

st.markdown("""
    <style>
    /* Fundo Preto Absoluto para Telas OLED */
    .stApp { background-color: #000000; }
    
    /* Esconder menus do Streamlit */
    [data-testid="stHeader"], [data-testid="stToolbar"], footer { display: none !important; }
    .block-container { padding: 1rem !important; max-width: 100% !important; }

    /* Estilo do Card do Cliente */
    .card {
        background-color: #0d0d0d;
        padding: 15px;
        border-radius: 12px;
        margin-bottom: 10px;
        border-left: 6px solid #28a745; /* Verde para casas */
        border: 1px solid #222;
    }
    
    /* Estilo de Prioridade para Apartamentos */
    .card-ap {
        border-left: 10px solid #ff0000 !important; /* Vermelho para AP */
        background-color: #1a0000 !important;
    }

    .nome { color: #ffffff; font-size: 22px; font-weight: bold; text-transform: uppercase; }
    .local { color: #aaaaaa; font-size: 17px; margin-top: 4px; }
    .alerta { color: #ff4b4b; font-size: 14px; font-weight: bold; margin-top: 6px; }

    /* Botões Gigantes para clicar com luva ou em movimento */
    div.stButton > button {
        width: 100%;
        height: 70px !important;
        font-size: 20px !important;
        font-weight: bold !important;
        border-radius: 12px !important;
        background-color: #1a1a1a !important;
        color: white !important;
        border: 1px solid #333 !important;
    }
    
    /* Botão de Concluído (Verde Escuro) */
    .btn-ok > div.stButton > button {
        background-color: #0a2410 !important;
        color: #4ade80 !important;
        border: 1px solid #14532d !important;
    }
    </style>
""", unsafe_allow_html=True)

# =================================================================
# 2. LÓGICA DE DADOS
# =================================================================
if 'dados' not in st.session_state: st.session_state.dados = None
if 'feitos' not in st.session_state: st.session_state.feitos = set()

def limpar_numero(tel):
    num = ''.join(filter(str.isdigit, str(tel)))
    if not num.startswith('55'): num = '55' + num
    return num

# --- TELA DE CARREGAMENTO ---
if st.session_state.dados is None:
    st.markdown("<h1 style='color:white; text-align:center;'>📦 CARREGAR LISTA</h1>", unsafe_allow_html=True)
    arquivo = st.file_uploader("", type=["csv"])
    if arquivo:
        df = pd.read_csv(arquivo)
        st.session_state.dados = df.to_dict('records')
        st.rerun()
else:
    # --- CABEÇALHO ---
    pendentes = [d for d in st.session_state.dados if d['Pacote'] not in st.session_state.feitos]
    
    col_t1, col_t2 = st.columns([3, 1])
    with col_t1:
        st.markdown(f"<h2 style='color:white;'>🚚 Faltam: {len(pendentes)}</h2>", unsafe_allow_html=True)
    with col_t2:
        if st.button("🗑️ Reset"):
            st.session_state.dados = None
            st.session_state.feitos = set()
            st.rerun()

    # --- LISTA DE CARDS ---
    for item in pendentes:
        nome_full = str(item['Nome']).upper()
        p_nome = nome_full.split()[0]
        local = str(item.get('Local', 'Sem Quadra')).upper()
        tel = limpar_numero(item['Telefone'])
        
        # Identificação de APARTAMENTO / CONDOMÍNIO
        # Procura no local e no nome (às vezes o número do AP tá no nome)
        eh_ap = any(x in (local + nome_full) for x in ['AP', 'APT', 'BL', 'BLO', 'EDIF', 'CONDOMINIO', 'CONJ'])
        
        card_class = "card-ap" if eh_ap else ""
        
        # Renderiza o Card
        st.markdown(f"""
            <div class="card {card_class}">
                <div class="nome">{nome_full}</div>
                <div class="local">📍 {local}</div>
                {"<div class='alerta'>⚠️ PRIORIDADE: APARTAMENTO / BLOCO</div>" if eh_ap else ""}
            </div>
        """, unsafe_allow_html=True)

        # Botões de Ação
        c1, c2 = st.columns([3, 1])
        
        with c1:
            # Mensagem rápida solicitada
            msg = urllib.parse.quote(f"Olá {p_nome}, estou chegando no seu endereço ({local}). Tem alguém pra receber a entrega?")
            st.link_button("🚀 ESTOU CHEGANDO", f"https://wa.me/{tel}?text={msg}")
            
        with c2:
            st.markdown('<div class="btn-ok">', unsafe_allow_html=True)
            if st.button("✅", key=f"ok_{item['Pacote']}"):
                st.session_state.feitos.add(item['Pacote'])
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
            
        st.markdown("<div style='margin-bottom:20px;'></div>", unsafe_allow_html=True)
