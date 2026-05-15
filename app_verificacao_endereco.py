import streamlit as st
import pandas as pd
import urllib.parse
import re
import requests
import base64
import io
from datetime import datetime

st.set_page_config(page_title="Endereços Incompletos", layout="centered", initial_sidebar_state="collapsed")

st.markdown("""
<style>
[data-testid="stHeader"],[data-testid="stToolbar"],footer{display:none!important}
body,.stApp{background-color:#1a1a2e!important;color:#fff!important}
.block-container{padding:16px!important;max-width:600px!important}
input,textarea{background-color:#16213e!important;color:#fff!important;border:1px solid #2d2d44!important;border-radius:10px!important}
.stButton button{border-radius:12px!important;font-weight:700!important}
div[data-testid="stFileUploader"]{background:#16213e;border:1px solid #2d2d44;border-radius:16px;padding:12px}
</style>
""", unsafe_allow_html=True)

# ── GitHub config ─────────────────────────────────────────────────────────
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
GITHUB_REPO  = st.secrets["GITHUB_REPO"]
CSV_PATH     = "enderecos_resolvidos.csv"
BRANCH       = "main"
GH_HEADERS   = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json",
}

# ── Detecção de ambiente ──────────────────────────────────────────────────
import os
LOCAL_CSV = CSV_PATH  # mesmo nome, lido do diretório de trabalho

def _modo_local():
    """Retorna True apenas se não houver token do GitHub configurado."""
    try:
        _ = st.secrets["GITHUB_TOKEN"]
        return False  # token disponível → sempre usa GitHub API
    except Exception:
        return os.path.exists(LOCAL_CSV)  # sem token → usa arquivo local

# ── Leitura do CSV ────────────────────────────────────────────────────────
@st.cache_data(ttl=60)
def carregar_resolvidos():
    if _modo_local():
        df = pd.read_csv(LOCAL_CSV, dtype=str).fillna("")
        return df, "local"
    # Streamlit Cloud: busca via GitHub API
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{CSV_PATH}"
    try:
        r = requests.get(url, headers=GH_HEADERS, timeout=10)
    except Exception as e:
        st.error(f"Sem acesso ao GitHub: {e}")
        return pd.DataFrame(columns=["telefone_e164","telefone_digits","nome",
                                      "endereco_resolvido","observacoes","data_adicionado"]), None
    if r.status_code == 200:
        conteudo = base64.b64decode(r.json()["content"]).decode("utf-8")
        sha = r.json()["sha"]
        df = pd.read_csv(io.StringIO(conteudo), dtype=str).fillna("")
        return df, sha
    return pd.DataFrame(columns=["telefone_e164","telefone_digits","nome",
                                  "endereco_resolvido","observacoes","data_adicionado"]), None

# ── Gravação de novo registro ─────────────────────────────────────────────
def salvar_resolvido(df, sha, tel_e164, tel_digits, nome):
    nova_linha = {
        "telefone_e164":  tel_e164,
        "telefone_digits": tel_digits,
        "nome":           nome,
        "endereco_resolvido": "",
        "observacoes":    "",
        "data_adicionado": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    df_novo = pd.concat([df, pd.DataFrame([nova_linha])], ignore_index=True)

    if sha == "local":
        try:
            df_novo.to_csv(LOCAL_CSV, index=False, encoding="utf-8")
        except PermissionError:
            return False, df
        return True, df_novo

    # Modo cloud: GitHub API
    csv_bytes = base64.b64encode(df_novo.to_csv(index=False).encode("utf-8")).decode("utf-8")
    url  = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{CSV_PATH}"
    body = {"message": f"update: resolvido {tel_e164}", "content": csv_bytes, "branch": BRANCH}
    if sha:
        body["sha"] = sha
    r = requests.put(url, headers=GH_HEADERS, json=body, timeout=10)
    return r.status_code in (200, 201), df_novo

# ── Normalização de telefone ──────────────────────────────────────────────
def _ultimos7(tel):
    """Retorna os últimos 7 dígitos do telefone para cruzamento flexível."""
    digits = re.sub(r"\D", "", str(tel))
    return digits[-7:] if len(digits) >= 7 else digits

def normalizar_tel(tel):
    digits = re.sub(r"\D", "", str(tel))
    if not digits:
        return "", ""
    if digits.startswith("55") and len(digits) >= 12:
        return f"+{digits}", digits
    if len(digits) in (10, 11):
        return f"+55{digits}", f"55{digits}"
    return f"+{digits}", digits

# ── Detecção de endereço incompleto ──────────────────────────────────────
def is_incompleto(end_completo):
    s = str(end_completo).strip().upper()
    if not s or s in ("NAN", "-", ""):
        return True
    # Tem LOTE ou CASA com número → completo
    if re.search(r'\bLOTE\s+\d+', s):
        return False
    if re.search(r'\bCASA\s+\d+', s):
        return False
    # LT sem número
    if re.search(r'\bLT\s*$', s):
        return True
    if re.search(r'\bLT\s+[_\-]+\b', s):
        return True
    if re.search(r'\bLT\s+S/?N\b', s):
        return True
    if re.search(r'\bLT\s+0+\b', s):
        return True
    # Nº / NUM sem número
    if re.search(r'\bN[°º]\s*$', s):
        return True
    if re.search(r'\bNUM(ERO)?\s*$', s):
        return True
    if re.search(r'S/?N\b', s):
        return True
    # QD sem LT ou LOTE
    if re.search(r'\bQ[DR]?\s*\d+\b', s) and not re.search(r'\b(LT|LOTE)\s*\d+', s):
        return True
    return False

CSV_DIA = "temp_csv_dia.csv"

# ── Session state ─────────────────────────────────────────────────────────
if "resolvidos_df" not in st.session_state:
    st.session_state.resolvidos_df, st.session_state.resolvidos_sha = carregar_resolvidos()
if "marcados_sessao" not in st.session_state:
    st.session_state.marcados_sessao = set()
if "confirmar_exclusao" not in st.session_state:
    st.session_state.confirmar_exclusao = False

df_res = st.session_state.resolvidos_df
sha    = st.session_state.resolvidos_sha

# conjunto de telefones já resolvidos (digits)
tel_resolvidos = set(_ultimos7(t) for t in df_res["telefone_digits"].tolist() if str(t).strip())

# ── Interface ─────────────────────────────────────────────────────────────
st.markdown("<h2 style='color:#fff;margin-bottom:4px'>📋 Endereços Incompletos</h2>", unsafe_allow_html=True)
st.markdown(f"<div style='color:#8a8a9a;font-size:13px;margin-bottom:16px'>Banco: {len(df_res)} resolvidos · Sessão: {len(st.session_state.marcados_sessao)} marcados agora</div>", unsafe_allow_html=True)

# ── CSV do dia com persistência ───────────────────────────────────────────
if os.path.exists(CSV_DIA):
    col_info, col_lixo = st.columns([5, 1])
    with col_info:
        st.markdown("<div style='color:#4caf50;font-size:13px;padding:6px 0'>📄 CSV do dia carregado</div>", unsafe_allow_html=True)
    with col_lixo:
        if st.button("🗑️", help="Excluir CSV do dia"):
            st.session_state.confirmar_exclusao = True

    if st.session_state.confirmar_exclusao:
        st.warning("⚠️ Tem certeza que quer excluir o CSV do dia?")
        col_sim, col_nao = st.columns(2)
        with col_sim:
            if st.button("✅ Sim, excluir", type="primary"):
                os.remove(CSV_DIA)
                st.session_state.confirmar_exclusao = False
                st.rerun()
        with col_nao:
            if st.button("❌ Cancelar"):
                st.session_state.confirmar_exclusao = False
                st.rerun()

    df = pd.read_csv(CSV_DIA)
else:
    arquivo = st.file_uploader("📂 Suba o CSV do dia", type=["csv"], label_visibility="collapsed")
    if arquivo is None:
        st.markdown("<div style='color:#8a8a9a;text-align:center;padding:40px'>Faça upload do CSV do dia para começar.</div>", unsafe_allow_html=True)
        st.stop()
    df = pd.read_csv(arquivo)
    df.to_csv(CSV_DIA, index=False)

# ── Processar CSV ─────────────────────────────────────────────────────────
df.columns = df.columns.str.strip()

# Colunas fixas do CSV
COL_RUA  = "Rua"
COL_LOTE = "Lote/Casa"
COL_APTO = "Apartamento"

col_tel  = next((c for c in df.columns if re.search(r'tel|fone|celular|whats', c, re.I)), None)
col_nome = next((c for c in df.columns if re.search(r'nome|client', c, re.I)), None)
col_pac  = next((c for c in df.columns if re.search(r'pacote|id|cod', c, re.I)), None)

# Valida se as colunas de endereço existem
cols_faltando = [c for c in [COL_RUA, COL_LOTE, COL_APTO] if c not in df.columns]
if cols_faltando:
    st.warning(f"⚠️ Colunas não encontradas: {cols_faltando}. Colunas do CSV: {list(df.columns)}")
    # Fallback: usa detecção automática se faltar coluna
    col_rua  = next((c for c in df.columns if re.search(r'rua|local|end|quadra', c, re.I)), None)
    col_lote = next((c for c in df.columns if re.search(r'lote|casa|compl|num', c, re.I)), None)
    col_apto = next((c for c in df.columns if re.search(r'apt|apto|ap\b', c, re.I)), None)
else:
    col_rua, col_lote, col_apto = COL_RUA, COL_LOTE, COL_APTO

if not col_rua:
    st.error("❌ Coluna de endereço não encontrada. Colunas: " + ", ".join(df.columns))
    st.stop()

def vazio(val):
    return str(val).strip().upper() in ("", "NAN", "NONE", "-", "N/A")

df["_rua"]     = df[col_rua].fillna("").astype(str).str.strip()
df["_lote"]    = df[col_lote].fillna("").astype(str).str.strip() if col_lote else ""
df["_apto"]    = df[col_apto].fillna("").astype(str).str.strip() if col_apto else ""
df["_end_full"] = (df["_rua"] + " " + df["_lote"] + " " + df["_apto"]).str.strip()
df["_tel_raw"] = df[col_tel].fillna("").astype(str).str.strip() if col_tel else ""
df["_nome"]    = df[col_nome].fillna("CLIENTE").astype(str).str.strip() if col_nome else "CLIENTE"
df["_pac"]     = df[col_pac].fillna("SEM ID").astype(str).str.strip() if col_pac else "SEM ID"

# Incompleto = Lote/Casa vazio (AP sozinho não basta — o AP fica dentro de um lote)
df["_incompleto"] = df["_lote"].apply(vazio)
df_inc = df[df["_incompleto"]].copy()

if df_inc.empty:
    st.success("✅ Nenhum endereço incompleto encontrado no CSV!")
    st.stop()

# Classificar cada incompleto
def classificar(row):
    e164, digits = normalizar_tel(row["_tel_raw"])
    ja_resolvido = _ultimos7(digits) in tel_resolvidos or _ultimos7(digits) in st.session_state.marcados_sessao
    return pd.Series({"_e164": e164, "_digits": digits, "_resolvido": ja_resolvido})

df_inc[["_e164","_digits","_resolvido"]] = df_inc.apply(classificar, axis=1)

pendentes   = df_inc[~df_inc["_resolvido"]]
ja_tratados = df_inc[df_inc["_resolvido"]]

# ── Stats ─────────────────────────────────────────────────────────────────
c1, c2, c3 = st.columns(3)
c1.metric("Total incompletos", len(df_inc))
c2.metric("✅ Já tratados", len(ja_tratados))
c3.metric("⏳ Pendentes", len(pendentes))

st.markdown("---")

# ── Lista de pendentes ────────────────────────────────────────────────────
if pendentes.empty:
    st.success("🎉 Todos os incompletos já foram tratados!")
else:
    st.markdown(f"<h4 style='color:#ff6b6b'>⏳ Pendentes ({len(pendentes)})</h4>", unsafe_allow_html=True)
    for _, row in pendentes.iterrows():
        nome    = row["_nome"].upper()
        rua     = row["_rua"].upper()
        lote    = row["_lote"].upper()
        apto    = row["_apto"].upper()
        pacote  = row["_pac"]
        e164    = row["_e164"]
        digits  = row["_digits"]
        p_nome  = row["_nome"].split()[0].capitalize() if row["_nome"] else "Cliente"
        end_msg = row["_end_full"].upper()

        msg = urllib.parse.quote(
            f"Olá {p_nome}, tudo bem?\n"
            f"Aqui é da J&T Express!\n"
            f"Identificamos que o endereço do seu pacote *{pacote}* está incompleto.\n"
            f"Pode me confirmar o endereço completo? (quadra, rua, lote/casa) Obrigado! 🙏🏽"
        )
        tel_wpp = re.sub(r"\D", "", e164) if e164 else ""
        wpp_url = f"https://wa.me/{tel_wpp}?text={msg}" if tel_wpp else "#"

        lote_html  = f'<div style="color:#ff6b6b;font-size:12px;margin-top:4px">🏠 <b>Lote/Casa:</b> {lote if lote else "—  ⚠️ vazio"}</div>'
        apto_html  = f'<div style="color:#aaa;font-size:12px">🚪 <b>Apto:</b> {apto if apto else "—"}</div>' if apto else ""

        st.markdown(f"""
        <div style="background:#16213e;border:1px solid #2d2d44;border-left:4px solid #ff6b6b;
                    border-radius:14px;padding:14px;margin-bottom:10px">
          <div style="color:#fff;font-size:15px;font-weight:700">{nome}</div>
          <div style="color:#4285f4;font-size:13px;margin:3px 0">📍 <b>Rua/Quadra:</b> {rua or '—'}</div>
          {lote_html}
          {apto_html}
          <div style="color:#8a8a9a;font-size:11px;font-family:monospace;margin-top:6px">📦 {pacote} · 📞 {e164 or '—'}</div>
        </div>
        """, unsafe_allow_html=True)

        col_wpp, col_ok = st.columns([2, 1])
        with col_wpp:
            st.markdown(f'<a href="{wpp_url}" target="_blank" style="display:block;text-align:center;background:#25d366;color:#fff;padding:11px;border-radius:12px;font-weight:700;text-decoration:none;font-size:14px">💬 Pedir endereço</a>', unsafe_allow_html=True)
        with col_ok:
            if st.button("✅ Resolvido", key=f"res_{digits}_{pacote}"):
                ok, df_novo = salvar_resolvido(df_res, sha, e164, digits, row["_nome"])
                if ok:
                    st.session_state.resolvidos_df = df_novo
                    st.session_state.marcados_sessao.add(_ultimos7(digits))
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("❌ Erro ao salvar. Se estiver rodando local, feche o arquivo enderecos_resolvidos.csv no Excel antes de marcar como resolvido.")

# ── Já tratados ───────────────────────────────────────────────────────────
if not ja_tratados.empty:
    with st.expander(f"✅ Já tratados ({len(ja_tratados)})", expanded=False):
        for _, row in ja_tratados.iterrows():
            st.markdown(f"""
            <div style="background:#0a2416;border:1px solid #1a4a2a;border-radius:12px;
                        padding:10px 14px;margin-bottom:8px">
              <div style="color:#00cc66;font-size:13px;font-weight:700">{row['_nome'].upper()}</div>
              <div style="color:#8a8a9a;font-size:12px">📍 {row['_rua'].upper()} · 📞 {row['_e164'] or '—'}</div>
            </div>
            """, unsafe_allow_html=True)
