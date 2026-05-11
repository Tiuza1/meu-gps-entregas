import io
import json
import math
import os
import re
import threading
import time

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="GPS Entregas", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""
<style>
[data-testid="stHeader"],[data-testid="stSidebar"],[data-testid="stToolbar"],footer{display:none!important}
.block-container{padding:0!important;max-width:100%!important;margin:0!important}
iframe{width:100vw;height:100vh;border:none!important}
</style>
""", unsafe_allow_html=True)

FILE_SAVE  = "progresso_final.json"
DEFAULT_CENTER = [-16.15, -47.96]
DEFAULT_ZOOM   = 16

# ── session state ──────────────────────────────────────────────────────────
def _init_state():
    defaults = {
        "lista_pacotes": [],
        "entregues_id":  [],
        "ultima_pos":    None,
        "map_center":    DEFAULT_CENTER,
        "map_zoom":      DEFAULT_ZOOM,
        "_proximo_id":       None,
        "_ultima_pos_prev":  "__unset__",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init_state()


# ── persistência assíncrona ────────────────────────────────────────────────
def salvar_progresso():
    dados = {
        "lista_pacotes": st.session_state.lista_pacotes,
        "entregues_id":  st.session_state.entregues_id,
        "ultima_pos":    st.session_state.ultima_pos,
        "map_center":    st.session_state.map_center,
        "map_zoom":      st.session_state.map_zoom,
    }
    def _write(d):
        with open(FILE_SAVE, "w", encoding="utf-8") as f:
            json.dump(d, f)
    threading.Thread(target=_write, args=(dados,), daemon=True).start()


# ── carga inicial do JSON ──────────────────────────────────────────────────
if not st.session_state.lista_pacotes and os.path.exists(FILE_SAVE):
    try:
        with open(FILE_SAVE, "r", encoding="utf-8") as f:
            d = json.load(f)
        st.session_state.lista_pacotes = d.get("lista_pacotes", [])
        st.session_state.entregues_id  = d.get("entregues_id",  [])
        st.session_state.ultima_pos    = d.get("ultima_pos")
        st.session_state.map_center    = d.get("map_center", DEFAULT_CENTER)
        st.session_state.map_zoom      = d.get("map_zoom",   DEFAULT_ZOOM)
    except Exception:
        pass


# ── banco de quadras (cached por mtime) ───────────────────────────────────
@st.cache_data
def carregar_banco(mtime):
    for arq in ("Lugares marcados.json", "Lugares-marcados.json"):
        if not os.path.exists(arq):
            continue
        try:
            with open(arq, "r", encoding="utf-8") as f:
                raw = json.load(f)
            banco = {
                str(l["properties"].get("title") or l["properties"].get("name")).strip():
                (l["geometry"]["coordinates"][1], l["geometry"]["coordinates"][0])
                for l in raw.get("features", [])
            }
            return dict(sorted(banco.items()))
        except Exception:
            pass
    return {}

_arq = "Lugares marcados.json" if os.path.exists("Lugares marcados.json") else "Lugares-marcados.json"
_mtime = os.path.getmtime(_arq) if os.path.exists(_arq) else 0
banco_total = carregar_banco(_mtime)


# ── processamento de CSV (cached por conteúdo) ────────────────────────────
def limpar_numero(num):
    num = re.sub(r"\D", "", str(num))
    if not num:
        return ""
    return num if num.startswith("55") else "55" + num

@st.cache_data(show_spinner=False)
def processar_csv(csv_bytes: bytes, banco_mtime: float):
    banco = carregar_banco(banco_mtime)
    df    = pd.read_csv(io.BytesIO(csv_bytes))
    ok, nao_enc, sem_num, cep_inv = [], [], [], []

    if "Local" not in df.columns or "CEP" not in df.columns:
        return None, [], [], []

    for _, row in df.iterrows():
        local  = str(row["Local"]).strip()
        cep    = str(row["CEP"]).strip()
        nome   = str(row.get("Nome",    "CLIENTE")).strip()
        tel    = limpar_numero(row.get("Telefone", ""))
        pacote = str(row.get("Pacote",  "SEM ID")).strip()

        m_num = re.search(r"(?:QUADRA|QD|Q|QR)\s*(\d+)", local, re.IGNORECASE)
        m_cep = re.search(r"(\d{5})[-.\s]?(\d{3})", cep)

        if not (m_num and m_cep):
            (sem_num if not m_num else cep_inv).append(local)
            continue

        numero     = str(int(m_num.group(1)))
        prefixo    = m_cep.group(1)
        sufixo     = int(m_cep.group(2))

        if prefixo in ("72853", "72856"):
            padrao, amig = r"p[\.\s]*i*x+", "Parque 9 ou 10"
        elif prefixo == "72859":
            if sufixo <= 500:
                padrao, amig = r"(p[\.\s]*8|p[\.\s]*v\s*i{3})", "Mansões Parque 8"
            else:
                padrao, amig = r"(p[\.\s]*7|p[\.\s]*v\s*i{2})", "Mansões Parque 7"
        else:
            cep_inv.append(f"{local} - CEP: {cep}")
            continue

        regex = rf"^Q\s*0*{numero}\s+{padrao}$"
        chave = next((k for k in banco if re.match(regex, k, re.IGNORECASE)), "")

        if chave:
            ok.append({"quadra_mapa": chave, "nome_cli": nome,
                        "tel_cli": tel, "pacote_cli": pacote, "quadra_original": local})
        else:
            nao_enc.append(f"{local} (CEP indica {amig})")

    return ok, nao_enc, sem_num, cep_inv


# ── query params (mutations → full rerun inevitável) ──────────────────────
q = st.query_params

if "map_lat" in q and "map_lng" in q:
    try:
        st.session_state.map_center = [float(q["map_lat"]), float(q["map_lng"])]
    except Exception:
        pass
if "map_zoom" in q:
    try:
        st.session_state.map_zoom = int(float(q["map_zoom"]))
    except Exception:
        pass

if "add_batch" in q:
    for nome in q["add_batch"].split("|"):
        if nome in banco_total:
            nid = f"{nome}_{time.time_ns()}"
            st.session_state.lista_pacotes.append({
                "id": nid, "nome": nome,
                "cliente": "Adicionado Manualmente",
                "telefone": "", "pacote": "Manual", "quadra_original": nome,
            })
            st.session_state.ultima_pos = banco_total[nome]
    salvar_progresso()
    st.query_params.clear()
    st.rerun()

if "concluir" in q:
    id_p = q["concluir"]
    if id_p not in st.session_state.entregues_id:
        st.session_state.entregues_id.append(id_p)
        for p in st.session_state.lista_pacotes:
            if p["id"] == id_p:
                st.session_state.ultima_pos = banco_total.get(p["nome"])
                break
        salvar_progresso()
    st.query_params.clear()
    st.rerun()

if "desfazer" in q:
    id_p = q["desfazer"]
    if id_p in st.session_state.entregues_id:
        st.session_state.entregues_id = [x for x in st.session_state.entregues_id if x != id_p]
        salvar_progresso()
    st.query_params.clear()
    st.rerun()

if "limpar" in q:
    if os.path.exists(FILE_SAVE):
        os.remove(FILE_SAVE)
    st.session_state.lista_pacotes = []
    st.session_state.entregues_id  = []
    st.session_state.ultima_pos    = None
    st.session_state.map_center    = DEFAULT_CENTER
    st.session_state.map_zoom      = DEFAULT_ZOOM
    st.session_state._proximo_id      = None
    st.session_state._ultima_pos_prev = "__unset__"
    st.query_params.clear()
    st.rerun()


# ── CSV import isolado (fragment evita re-render do mapa ao fazer upload) ──
def csv_section():
    with st.expander("📦 Importar Planilha de Entregas (CSV)", expanded=False):
        arquivo = st.file_uploader("CSV do Extrator Pro", type=["csv"])
        if arquivo is None:
            return

        ok, nao_enc, sem_num, cep_inv = processar_csv(arquivo.getvalue(), _mtime)

        if ok is None:
            st.error("O CSV precisa ter colunas 'Local' e 'CEP'.")
            return

        if ok:
            st.success(f"✅ {len(ok)} locais validados por CEP!")
            if st.button("🗺️ Adicionar ao Mapa"):
                for item in ok:
                    nid = f"{item['quadra_mapa']}_{time.time_ns()}"
                    st.session_state.lista_pacotes.append({
                        "id": nid,
                        "nome":            item["quadra_mapa"],
                        "cliente":         item["nome_cli"],
                        "telefone":        item["tel_cli"],
                        "pacote":          item["pacote_cli"],
                        "quadra_original": item["quadra_original"],
                    })
                salvar_progresso()
                st.rerun()  # full rerun para atualizar o mapa

        if nao_enc or sem_num or cep_inv:
            st.warning("⚠️ Endereços não mapeados:")
            for a in nao_enc + sem_num + cep_inv:
                st.write(f"- {a}")

csv_section()


# ── cálculo de proximo_id (cache em session_state) ─────────────────────────
entregues_set  = set(st.session_state.entregues_id)
pendentes_total = [p for p in st.session_state.lista_pacotes if p["id"] not in entregues_set]
_pos_str = str(st.session_state.ultima_pos)

if _pos_str != st.session_state._ultima_pos_prev:
    proximo_id = None
    if st.session_state.ultima_pos and pendentes_total:
        ux, uy = st.session_state.ultima_pos
        dist_min = float("inf")
        for p in pendentes_total:
            cx, cy = banco_total.get(p["nome"], (0, 0))
            d = (ux - cx) ** 2 + (uy - cy) ** 2  # sqrt desnecessário para comparação
            if d < dist_min:
                dist_min = d
                proximo_id = p["id"]
    st.session_state._proximo_id      = proximo_id
    st.session_state._ultima_pos_prev = _pos_str
else:
    proximo_id = st.session_state._proximo_id


# ── montar pontos para o JS ───────────────────────────────────────────────
agrupado: dict = {}
for p in st.session_state.lista_pacotes:
    nome = p["nome"]
    if nome not in agrupado:
        agrupado[nome] = {"total": 0, "pendentes": [], "concluidos": []}
    agrupado[nome]["total"] += 1
    (agrupado[nome]["concluidos"] if p["id"] in entregues_set else agrupado[nome]["pendentes"]).append(p)

pontos_js = []
for nome, info in agrupado.items():
    coords    = banco_total.get(nome, (0, 0))
    pend_list = info["pendentes"]
    done_list = info["concluidos"]
    p_ids     = [p["id"] for p in pend_list]
    concluido = len(p_ids) == 0

    if concluido:
        cor = "#00cc66"
    elif any(pid == proximo_id for pid in p_ids):
        cor = "#fd7e14"
    elif len(p_ids) > 1:
        cor = "#0066ff"
    else:
        cor = "#dc3545"

    nums = re.findall(r"\d+", nome)
    base = nums[0] if nums else nome[:3]
    txt  = "✔" if concluido else (f"{base}×{len(p_ids)}" if len(p_ids) > 1 else base)

    ponto: dict = {
        "lat": coords[0], "lng": coords[1],
        "nome": nome, "cor": cor, "txt": txt,
        "concluido": concluido,
        "restantes": len(p_ids),
        "concluidos_count": len(done_list),
        "is_next": any(pid == proximo_id for pid in p_ids),
        "lista_done": [
            {"id_pacote": p["id"], "cliente": p.get("cliente", ""), "telefone": p.get("telefone", ""),
             "pacote": p.get("pacote", "Manual"), "quadra_real": p.get("quadra_original", nome)}
            for p in done_list
        ],
    }
    # lista_wpp só para pontos com pendências (reduz payload para concluídos)
    if not concluido:
        ponto["lista_wpp"] = [
            {"id_pacote": p["id"], "cliente": p.get("cliente", ""), "telefone": p.get("telefone", ""),
             "pacote": p.get("pacote", "Manual"), "quadra_real": p.get("quadra_original", nome)}
            for p in pend_list
        ]
    pontos_js.append(ponto)

bolinhas_pendentes = sum(1 for p in pontos_js if not p["concluido"])
concluidos_total   = len(st.session_state.entregues_id)
lista_opcoes_html  = "".join(f'<option value="{n}">' for n in banco_total)
centro = st.session_state.map_center or st.session_state.ultima_pos or DEFAULT_CENTER
zoom   = st.session_state.map_zoom   or DEFAULT_ZOOM

# ── HTML do mapa ──────────────────────────────────────────────────────────
mapa_html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.4.1/dist/MarkerCluster.css">
<link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.4.1/dist/MarkerCluster.Default.css">
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script src="https://unpkg.com/leaflet.markercluster@1.4.1/dist/leaflet.markercluster.js"></script>
<style>
*{{box-sizing:border-box}}
body{{margin:0;padding:0;font-family:-apple-system,BlinkMacSystemFont,'Inter','Segoe UI',sans-serif;overflow:hidden;background:#1a1a2e;-webkit-font-smoothing:antialiased}}
#map{{height:100vh;width:100vw;z-index:1}}

/* cluster escuro */
.marker-cluster-small,.marker-cluster-medium,.marker-cluster-large{{background:rgba(0,102,255,.25)!important}}
.marker-cluster-small div,.marker-cluster-medium div,.marker-cluster-large div{{background:#0066ff!important;color:#fff;font-weight:800;font-size:13px}}

/* search */
.search-container{{position:fixed;top:10px;left:10px;right:10px;z-index:1200;background:#16213e;border:1px solid #2d2d44;padding:10px;border-radius:16px;box-shadow:0 4px 24px rgba(0,0,0,.5)}}
.search-row{{display:flex;gap:6px}}
#input-busca{{flex:1;border:1px solid #2d2d44;padding:12px 14px;border-radius:12px;font-size:16px;outline:none;background:#1a1a2e;color:#fff}}
#input-busca::placeholder{{color:#8a8a9a}}
.btn-add{{background:#0066ff;color:#fff;padding:0 18px;font-size:20px;border:none;border-radius:12px;font-weight:700}}
.btn-confirm{{display:none;width:100%;background:#00cc66;color:#fff;padding:12px;margin-top:8px;border:none;border-radius:12px;font-weight:700;font-size:15px;letter-spacing:.3px}}
#batch-list{{display:none;flex-wrap:wrap;gap:6px;margin-top:8px;padding-top:8px;border-top:1px solid #2d2d44}}
.batch-item{{background:#1a1a2e;padding:5px 10px;border-radius:999px;font-size:12px;display:flex;align-items:center;gap:6px;border:1px solid #2d2d44;color:#fff}}
.batch-item b{{color:#ff6b6b;cursor:pointer;font-weight:700}}

/* stats */
.top-stats{{position:fixed;top:88px;left:10px;display:flex;gap:8px;z-index:1100}}
.badge{{background:#16213e;border:1px solid #2d2d44;color:#fff;padding:8px 14px;border-radius:999px;font-size:13px;font-weight:700}}
.badge.green{{background:#0a2416;border-color:#00cc66;color:#00cc66}}
.btn-clear{{position:fixed;top:88px;right:10px;z-index:1101;background:#16213e;border:1px solid #2d2d44;padding:9px 14px;border-radius:12px;font-size:13px;font-weight:700;color:#ff6b6b}}

/* sheet */
#sheet{{position:fixed;bottom:-100%;left:0;right:0;background:#16213e;color:#fff;z-index:2000;padding:20px 18px 24px;border-radius:24px 24px 0 0;border-top:1px solid #2d2d44;box-shadow:0 -6px 32px rgba(0,0,0,.55);transition:bottom .22s ease;max-height:86vh;display:flex;flex-direction:column}}
#sheet.active{{bottom:0}}
.sheet-head{{display:flex;align-items:flex-start;justify-content:space-between;gap:10px;margin-bottom:10px}}
.s-header{{font-size:18px;font-weight:700;color:#fff}}
.s-sub{{font-size:12px;color:#8a8a9a;margin-top:4px}}

/* quick */
.quick-actions{{display:flex;gap:8px;flex-wrap:wrap;margin:8px 0 12px}}
.quick-btn{{background:#0066ff;color:#fff;text-decoration:none;padding:10px 14px;border-radius:12px;font-weight:700;font-size:13px;border:none;cursor:pointer}}
.quick-btn.secondary{{background:#2d2d44}}
.quick-btn.success{{background:#0a2416;border:1px solid #00cc66;color:#00cc66}}

/* tabs */
#tabs{{display:flex;gap:8px;margin-bottom:12px}}
.tab-btn{{flex:1;background:#1a1a2e;color:#8a8a9a;border:1px solid #2d2d44;padding:11px 10px;border-radius:12px;font-weight:700;font-size:13px}}
.tab-btn.active{{background:#0066ff;color:#fff;border-color:#0066ff}}
.tab-panel{{display:none;overflow-y:auto;flex:1;padding-right:4px}}
.tab-panel.active{{display:block}}

/* cards */
.client-card{{background:#1a1a2e;border:1px solid #2d2d44;padding:14px;border-radius:16px;margin-bottom:10px}}
.client-card.done{{background:#0a1a0f;border-color:#1a4a2a}}
.client-name{{color:#fff;font-size:14px;font-weight:700;margin-bottom:4px}}
.client-pkg{{color:#8a8a9a;font-size:11px;margin-bottom:10px;font-family:monospace}}
.client-actions-row{{display:flex;gap:8px;margin-bottom:8px}}
.client-link{{flex:1;text-align:center;text-decoration:none;padding:10px 8px;border-radius:12px;font-size:12px;font-weight:800}}
.client-link.zap{{background:#0a1a0f;color:#25d366;border:1px solid #25d366}}
.client-link.arrive{{background:#00cc66;color:#fff}}
.client-link.route{{display:block;text-align:center;text-decoration:none;background:#2d2d44;color:#fff;padding:10px 8px;border-radius:12px;font-size:12px;font-weight:800}}
.client-link.undo{{display:block;text-align:center;text-decoration:none;background:#2d1a00;color:#ffd700;border:1px solid #ffd700;padding:10px 8px;border-radius:12px;font-size:12px;font-weight:800}}
.client-link.donebtn{{display:block;text-align:center;text-decoration:none;background:#00cc66;color:#fff;padding:13px 8px;border-radius:12px;font-size:14px;font-weight:900;margin-top:8px;letter-spacing:.3px}}

/* pin minimalista */
.pin{{min-width:26px;height:26px;padding:0 6px;border-radius:999px;display:flex;align-items:center;justify-content:center;background:rgba(255,255,255,.93);color:#1a1a2e;font-weight:800;border:2px solid #ccc;font-size:11px;white-space:nowrap;letter-spacing:-.3px}}
.leaflet-marker-icon.marker-hidden,.leaflet-marker-shadow.marker-hidden{{opacity:0!important;transform:scale(.35)!important;pointer-events:none}}
</style>
</head>
<body>
<div class="search-container">
  <div class="search-row">
    <input type="text" id="input-busca" list="lugares" placeholder="Adicionar manualmente...">
    <datalist id="lugares">{lista_opcoes_html}</datalist>
    <button class="btn-add" onclick="addToQueue()">+</button>
  </div>
  <div id="batch-list"></div>
  <button id="btn-confirm-all" class="btn-confirm" onclick="sendBatch()">CONFIRMAR PEDIDOS</button>
</div>
<div class="top-stats">
  <div class="badge">📍 {bolinhas_pendentes} pendentes</div>
  <div class="badge green">✓ {concluidos_total} concluídos</div>
</div>
<button class="btn-clear" onclick="if(confirm('Limpar todas as entregas?'))navigateWithMap('?limpar=1')">🗑 LIMPAR</button>
<div id="map"></div>
<div id="sheet">
  <div class="sheet-head">
    <div>
      <div class="s-header" id="s-nome">Local</div>
      <div class="s-sub"   id="s-info"></div>
    </div>
    <button onclick="closeSheet()" style="background:#2d2d44;color:#8a8a9a;border:none;border-radius:12px;padding:10px 14px;font-weight:700;font-size:16px">✕</button>
  </div>
  <div class="quick-actions">
    <a id="s-gps" href="#" target="_blank" class="quick-btn">🧭 Google Maps</a>
    <button class="quick-btn secondary" onclick="openTab('pendentes')">Pendentes</button>
    <button class="quick-btn success"   onclick="openTab('concluidos')">Concluídos</button>
  </div>
  <div id="tabs">
    <button id="tabbtn-pendentes" class="tab-btn active" onclick="openTab('pendentes')">Pendentes</button>
    <button id="tabbtn-concluidos" class="tab-btn"      onclick="openTab('concluidos')">Concluídos</button>
  </div>
  <div id="panel-pendentes"  class="tab-panel active"></div>
  <div id="panel-concluidos" class="tab-panel"></div>
</div>
<script>
// ── dados ─────────────────────────────────────────────────────────────────
const pontos = {json.dumps(pontos_js, ensure_ascii=False)};

// ── mapa ──────────────────────────────────────────────────────────────────
const map = L.map('map', {{zoomControl:false, attributionControl:false}})
             .setView([{centro[0]}, {centro[1]}], {zoom});

L.tileLayer('https://{{s}}.basemaps.cartocdn.com/rastertiles/voyager/{{z}}/{{x}}/{{y}}{{r}}.png', {{
  subdomains: ['a','b','c','d'], maxZoom: 19
}}).addTo(map);

setTimeout(() => map.invalidateSize(), 300);

// ── cluster (agrupa automaticamente abaixo do zoom 14) ────────────────────
const cluster = L.markerClusterGroup({{
  disableClusteringAtZoom: 14,
  spiderfyOnMaxZoom: true,
  showCoverageOnHover: false,
  maxClusterRadius: 60,
  iconCreateFunction: function(c) {{
    const n = c.getChildCount();
    return L.divIcon({{
      className: '',
      html: '<div style="width:32px;height:32px;border-radius:50%;background:#0066ff;color:#fff;display:flex;align-items:center;justify-content:center;font-weight:800;font-size:13px;border:2px solid rgba(255,255,255,.3)">' + n + '</div>',
      iconSize: [32,32], iconAnchor: [16,16]
    }});
  }}
}});

// ── estado JS ─────────────────────────────────────────────────────────────
let queue = [];
const markerByPackage = {{}};
const pointByName     = {{}};
pontos.forEach(p => pointByName[p.nome] = p);

// ── navegação preservando posição do mapa ─────────────────────────────────
function currentMapState() {{
  const c = map.getCenter();
  return `map_lat=${{c.lat}}&map_lng=${{c.lng}}&map_zoom=${{map.getZoom()}}`;
}}
function navigateWithMap(base) {{
  window.location.href = base + (base.includes('?') ? '&' : '?') + currentMapState();
}}

// ── tabs ──────────────────────────────────────────────────────────────────
function openTab(tab) {{
  ['pendentes','concluidos'].forEach(t => {{
    document.getElementById('panel-' + t).classList.toggle('active', t === tab);
    document.getElementById('tabbtn-' + t).classList.toggle('active', t === tab);
  }});
}}

// ── fila de adição manual ─────────────────────────────────────────────────
function addToQueue() {{
  const inp = document.getElementById('input-busca');
  const val = inp.value.trim();
  if (val) {{ queue.push(val); renderQueue(); inp.value=''; inp.focus(); }}
}}
function removeFromQueue(i) {{ queue.splice(i,1); renderQueue(); }}
function renderQueue() {{
  const c = document.getElementById('batch-list');
  const b = document.getElementById('btn-confirm-all');
  if (queue.length) {{
    c.style.display = 'flex'; b.style.display = 'block';
    c.innerHTML = queue.map((v,i) =>
      '<div class="batch-item">' + v + '<b onclick="removeFromQueue(' + i + ')">✕</b></div>'
    ).join('');
  }} else {{
    c.style.display = 'none'; b.style.display = 'none';
  }}
}}
function sendBatch() {{
  if (queue.length)
    navigateWithMap('?add_batch=' + queue.map(encodeURIComponent).join('|'));
}}

// ── sheet ─────────────────────────────────────────────────────────────────
function closeSheet() {{ document.getElementById('sheet').classList.remove('active'); }}
function hidePackageMarker(id) {{
  const m = markerByPackage[id];
  if (m && m._icon) m._icon.classList.add('marker-hidden');
}}

// ── card HTML (lazy: só monta quando o sheet abre) ────────────────────────
function clientCardHtml(cli, isDone) {{
  const nome     = (cli.cliente || 'Cliente').toUpperCase();
  const primeiro = (cli.cliente || 'Cliente').split(' ')[0] || 'Cliente';
  let h = '<div class="client-card' + (isDone ? ' done' : '') + '">';
  h += '<div class="client-name">👤 ' + nome + '</div>';
  h += '<div class="client-pkg">📦 ' + (cli.pacote || 'Manual') + '</div>';
  if (!isDone) {{
    if (cli.telefone && cli.cliente !== 'Adicionado Manualmente') {{
      const mc = encodeURIComponent('Olá ' + primeiro + ', Estou chegando no seu endereço (' + cli.quadra_real + '). Tem alguém pra receber agora?');
      const mr = encodeURIComponent('Oi ' + primeiro + ', Seu pacote para a *' + cli.quadra_real + '* está na rota de hoje. Passo até às 17h Ok?');
      h += '<div class="client-actions-row">';
      h += '<a href="https://wa.me/' + cli.telefone + '" target="_blank" class="client-link zap">💬 ZAP</a>';
      h += '<a href="https://wa.me/' + cli.telefone + '?text=' + mc + '" target="_blank" class="client-link arrive">🚀 CHEGANDO</a>';
      h += '</div>';
      h += '<a href="https://wa.me/' + cli.telefone + '?text=' + mr + '" target="_blank" class="client-link route">📅 AVISAR ROTA</a>';
    }} else if (cli.cliente !== 'Adicionado Manualmente') {{
      h += '<div style="color:#ff6b6b;font-size:12px;margin-bottom:8px">⚠️ Sem número</div>';
    }}
    h += '<a href="#" onclick="concluirEntrega(\\'' + cli.id_pacote + '\\');return false" class="client-link donebtn">✅ CONCLUIR ENTREGA</a>';
  }} else {{
    h += '<a href="#" onclick="desfazerEntrega(\\'' + cli.id_pacote + '\\');return false" class="client-link undo">↩ DESFAZER</a>';
  }}
  h += '</div>';
  return h;
}}

// ── render sheet (lazy: HTML só aqui, não pré-renderizado) ────────────────
function renderSheet(point) {{
  document.getElementById('s-nome').innerText = point.nome;
  document.getElementById('s-info').innerText = point.concluido
    ? 'Todas concluídas'
    : `${{point.restantes}} pendente(s) · ${{point.concluidos_count}} concluída(s)` + (point.is_next ? ' · próxima' : '');
  document.getElementById('s-gps').href =
    'https://www.google.com/maps/dir/?api=1&destination=' + point.lat + ',' + point.lng;

  const wpp  = point.lista_wpp  || [];
  const done = point.lista_done || [];
  document.getElementById('panel-pendentes').innerHTML = wpp.length
    ? wpp.map(c => clientCardHtml(c, false)).join('')
    : '<div class="client-card"><div class="client-name" style="color:#8a8a9a">Nenhum pendente</div></div>';
  document.getElementById('panel-concluidos').innerHTML = done.length
    ? done.map(c => clientCardHtml(c, true)).join('')
    : '<div class="client-card done"><div class="client-name" style="color:#8a8a9a">Nenhuma concluída</div></div>';

  openTab(wpp.length ? 'pendentes' : 'concluidos');
  document.getElementById('sheet').classList.add('active');
  map.panTo([point.lat, point.lng]);
}}

function concluirEntrega(id) {{
  hidePackageMarker(id);
  navigateWithMap('?concluir=' + encodeURIComponent(id));
}}
function desfazerEntrega(id) {{
  navigateWithMap('?desfazer=' + encodeURIComponent(id));
}}

// ── marcadores ────────────────────────────────────────────────────────────
pontos.forEach(function(p) {{
  const icon = L.divIcon({{
    className: '',
    html: '<div class="pin" style="border-color:' + p.cor + ';opacity:' + (p.concluido ? 0.55 : 1) + '">' + p.txt + '</div>',
    iconSize: [null, 26], iconAnchor: [13, 13]
  }});
  const m = L.marker([p.lat, p.lng], {{icon}});
  m.on('click', e => {{ L.DomEvent.stopPropagation(e); renderSheet(p); }});
  cluster.addLayer(m);
  (p.lista_wpp || []).forEach(c => markerByPackage[c.id_pacote] = m);
}});
map.addLayer(cluster);

// ── localização do entregador ─────────────────────────────────────────────
map.on('click', closeSheet);
map.locate({{watch: true, enableHighAccuracy: true}});
let userDot;
map.on('locationfound', e => {{
  if (!userDot)
    userDot = L.circleMarker(e.latlng, {{radius:7, color:'#fff', fillColor:'#4285F4', fillOpacity:1, weight:2.5}}).addTo(map);
  else
    userDot.setLatLng(e.latlng);
}});
</script>
</body>
</html>"""

components.html(mapa_html, height=900)
