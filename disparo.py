import streamlit as st
import pandas as pd
import urllib.parse
import os
import unicodedata

# =================================================================
# 1. CONFIGURAÇÃO VISUAL E PERSISTÊNCIA
# =================================================================
st.set_page_config(page_title="PAINEL J&T PRO", layout="centered")

# Nome do arquivo que ficará guardado no servidor
ARQUIVO_SALVO = "banco_rota.csv"

st.markdown("""
    <style>
    .stApp { background-color: #000000; }
    [data-testid="stHeader"], [data-testid="stToolbar"], footer { display: none !important; }
    .block-container { padding: 10px !important; }

    /* Lupa de Pesquisa */
    .stTextInput > div > div > input {
        background-color: #151515 !important;
        color: white !important;
        border: 1px solid #333 !important;
        height: 50px;
        border-radius: 12px;
        font-size: 18px;
    }

    /* CARD DO CLIENTE */
    .card {
        background-color: #111111;
        border: 1px solid #222;
        border-radius: 15px;
        padding: 15px;
        margin-bottom: 10px;
        border-left: 6px solid #333;
    }
    .prioridade-ap { border-left-color: #ff4b4b !important; background-color: #1a0505 !important; }
    
    .nome { color: #ffffff; font-size: 18px; font-weight: bold; }
    .local { color: #4285f4; font-size: 16px; font-weight: bold; margin-top: 2px; }
    .pacote-id { color: #666; font-size: 12px; font-family: monospace; margin-top: 4px; }
    
    /* BOTÃO ABRIR WHATSAPP (VERDE - TOPO) */
    .btn-wpp > a {
        display: flex; align-items: center; justify-content: center;
        background-color: #25D366 !important;
        color: white !important;
        height: 55px;
        border-radius: 12px;
        text-decoration: none;
        font-weight: bold;
        font-size: 18px;
        margin-top: 10px;
    }

    /* BOTÃO ESTOU CHEGANDO (AZUL - MEIO) */
    .btn-chegando > a {
        display: flex; align-items: center; justify-content: center;
        background-color: #007bff !important;
        color: white !important;
        height: 45px;
        border-radius: 12px;
        text-decoration: none;
        font-weight: bold;
        font-size: 16px;
        margin-top: 8px;
    }

    /* BOTÃO AVISAR ROTA (VERMELHO - FIM) */
    .btn-rota > a {
        display: flex; align-items: center; justify-content: center;
        background-color: #ff4b4b !important;
        color: white !important;
        height: 45px;
        border-radius: 12px;
        text-decoration: none;
        font-weight: bold;
        font-size: 16px;
        margin-top: 8px;
    }
    </style>
""", unsafe_allow_html=True)

# =================================================================
# 2. FUNÇÕES DE LIMPEZA E PERSISTÊNCIA
# =================================================================

def limpar_numero(tel):
    # Remove tudo que não for número e protege contra valores nulos
    num = ''.join(filter(str.isdigit, str(tel)))
    if not num: 
        return ""
    if not num.startswith('55'): 
        num = '55' + num
    return num

def remover_acentos(texto):
    """Remove acentos do texto para facilitar a busca."""
    texto = str(texto)
    # Normaliza a string, separando os caracteres dos acentos, e filtra removendo a marcação de acento (Mn)
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')

# Tenta carregar o arquivo que já está no servidor
def carregar_dados_salvos():
    if os.path.exists(ARQUIVO_SALVO):
        try:
            return pd.read_csv(ARQUIVO_SALVO).to_dict('records')
        except:
            return None
    return None

if 'dados' not in st.session_state:
    st.session_state.dados = carregar_dados_salvos()

# =================================================================
# 3. INTERFACE
# =================================================================

if st.session_state.dados is None:
    st.markdown("<h2 style='color:white; text-align:center;'>📦 Iniciar Nova Rota</h2>", unsafe_allow_html=True)
    arquivo = st.file_uploader("Suba o CSV do computador", type=["csv"], label_visibility="collapsed")
    
    if arquivo:
        df = pd.read_csv(arquivo)
        
        # 1. Limpeza de espaços nos nomes das colunas
        df.columns = df.columns.str.strip()
        
        # 2. Preenchimento de dados faltantes (evita erros de valor vazio)
        if 'Nome' in df.columns:
            df['Nome'] = df['Nome'].fillna('').astype(str).str.strip()
        if 'Local' in df.columns:
            df['Local'] = df['Local'].fillna('Sem Quadra').astype(str).str.strip()
        if 'Pacote' in df.columns:
            df['Pacote'] = df['Pacote'].fillna('SEM ID').astype(str).str.strip()
        if 'Telefone' in df.columns:
            df['Telefone'] = df['Telefone'].fillna('').astype(str).str.strip()
            
        # 3. Ordenar por Quadra/Local se existirem as colunas
        ordem = [c for c in ['Local', 'Nome'] if c in df.columns]
        if ordem:
            df = df.sort_values(by=ordem, ascending=[True]*len(ordem))
            
        # 4. Salva o arquivo no disco do servidor para persistência
        df.to_csv(ARQUIVO_SALVO, index=False)
        st.session_state.dados = df.to_dict('records')
        st.rerun()
else:
    # --- BARRA DE PESQUISA ---
    col_lupa, col_reset = st.columns([5, 1])
    with col_lupa:
        busca = st.text_input("🔍 Buscar nome, quadra, pacote ou telefone...", placeholder="Ex: flavia, 4082, qd 10...")
    with col_reset:
        if st.button("🗑️", help="Apagar arquivo salvo"):
            if os.path.exists(ARQUIVO_SALVO):
                os.remove(ARQUIVO_SALVO)
            st.session_state.dados = None
            st.rerun()

    # --- FILTRAGEM AVANÇADA ---
    lista_exibicao = st.session_state.dados
    if busca:
        busca_norm = remover_acentos(busca).lower() # Tira acentos e deixa minúsculo
        lista_filtrada = []
        
        for d in lista_exibicao:
            # Pega os 4 campos, junta em uma frase só, tira acentos e deixa minúsculo
            texto_unido = f"{d.get('Nome', '')} {d.get('Local', '')} {d.get('Pacote', '')} {d.get('Telefone', '')}"
            texto_unido_norm = remover_acentos(texto_unido).lower()
            
            # Se a busca estiver em qualquer parte dessa frase, a entrega aparece
            if busca_norm in texto_unido_norm:
                lista_filtrada.append(d)
                
        lista_exibicao = lista_filtrada

    st.markdown(f"<div style='color:#555; font-size:12px; margin-bottom:10px;'>{len(lista_exibicao)} entregas na lista</div>", unsafe_allow_html=True)

    # --- LISTA DE CARDS ---
    for item in lista_exibicao:
        # Extração segura das variáveis
        nome_raw = str(item.get('Nome', '')).strip()
        nome_full = nome_raw.upper() if nome_raw else "SEM NOME"
        p_nome = nome_raw.split()[0] if nome_raw else "CLIENTE"
        
        local_raw = str(item.get('Local', 'Sem Quadra')).strip()
        local = local_raw.upper() if local_raw else "SEM QUADRA"
        
        id_pacote = str(item.get('Pacote', 'SEM ID')).strip()
        tel = limpar_numero(item.get('Telefone', ''))
        
        # Identifica se é condomínio ou AP para colorir o card
        eh_ap = any(x in (local + nome_full) for x in ['AP', 'APT', 'BL', 'BLO', 'CONDOMINIO'])
        card_class = "prioridade-ap" if eh_ap else ""

        # Renderização do Card de dados
        st.markdown(f"""
            <div class="card {card_class}">
                <div class="nome">{nome_full}</div>
                <div class="local">📍 {local}</div>
                <div class="pacote-id">ID: {id_pacote}</div>
            </div>
        """, unsafe_allow_html=True)

        # Se houver telefone válido, exibe os botões do WhatsApp
        if tel:
            msg_chegando = urllib.parse.quote(f"Olá {p_nome}, Estou chegando no seu endereço ({local}). Tem alguém pra receber a entrega agora?")
            msg_rota = urllib.parse.quote(f"Oi {p_nome}, Seu pacote para a *{local}* está na rota de hoje. Passo até às 17h Ok?")

            st.markdown(f"""
                <div class="btn-wpp">
                    <a href="https://wa.me/{tel}" target="_blank">💬 ABRIR WHATSAPP</a>
                </div>
                <div class="btn-chegando">
                    <a href="https://wa.me/{tel}?text={msg_chegando}" target="_blank">🚀 ESTOU CHEGANDO</a>
                </div>
                <div class="btn-rota">
                    <a href="https://wa.me/{tel}?text={msg_rota}" target="_blank">📅 AVISAR ROTA</a>
                </div>
                <div style="margin-bottom: 25px;"></div>
            """, unsafe_allow_html=True)
        else:
            # Caso não tenha telefone, exibe um alerta para não quebrar o layout
            st.markdown("""
                <div style='color:#ff4b4b; font-size:14px; font-weight:bold; margin-bottom: 25px; padding-left: 5px;'>
                    ⚠️ Cliente sem número de telefone no sistema
                </div>
            """, unsafe_allow_html=True)
