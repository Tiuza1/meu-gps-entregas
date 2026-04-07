import json
import streamlit as st
import re
import os
import math

# =================================================================
# 1. CONFIGURAÇÃO DE TELA (UI LIMPA)
# =================================================================
st.set_page_config(page_title="GPS Profissional", layout="wide", initial_sidebar_state="collapsed")

# CSS Ajustado para permitir ver a barra lateral quando necessário
st.markdown("""
    <style>
    [data-testid="stHeader"], [data-testid="stToolbar"], footer { display: none !important; }
    .block-container { padding: 0 !important; max-width: 100% !important; margin: 0 !important; }
    iframe { width: 100vw; height: 100vh; border: none !important; }
    
    /* Estilo para a área de controles flutuante ou sidebar */
    .stSelectbox, .stMultiSelect { background: white; border-radius: 10px; }
    </style>
""", unsafe_allow_html=True)

# =================================================================
# 2. LOGICA DE DADOS (PYTHON)
# =================================================================
FILE_SAVE = "progresso_final.json"

if 'lista_pacotes' not in st.session_state: st.session_state.lista_pacotes = []
if 'entregues_id' not in st.session_state: st.session_state.entregues_id = []
if 'ultima_pos' not in st.session_state: st.session_state.ultima_pos = None

def salvar_progresso():
    dados = {"lista_pacotes": st.session_state.lista_pacotes, "entregues_id": st.session_state.entregues_id, "ultima_pos": st.session_state.ultima_pos}
    with open(FILE_SAVE, "w") as f: json.dump(dados, f)

if not st.session_state.lista_pacotes and os.path.exists(FILE_SAVE):
    try:
        with open(FILE_SAVE, "r") as f:
            d = json.load(f)
            st.session_state.lista_pacotes = d.get("lista_pacotes", [])
            st.session_state.entregues_id = d.get("entregues_id", [])
            st.session_state.ultima_pos = d.get("ultima_pos")
    except: pass

@st.cache_data
def carregar_banco():
    try:
        with open('Lugares marcados.json', 'r', encoding='utf-8') as f:
            dados_j = json.load(f)
        banco = {str(l['properties'].get('title') or l['properties'].get('name')).strip(): 
                (l['geometry']['coordinates'][1], l['geometry']['coordinates'][0]) 
                for l in dados_j.get('features',[])}
        return dict(sorted(banco.items()))
    except: return {}

banco_total = carregar_banco()

# =================================================================
# 3. INTERFACE DE ADIÇÃO (SIDEBAR)
# =================================================================
with st.sidebar:
    st.header("⚙️ Gestão de Entregas")
    
    # SELEÇÃO EM MASSA
    st.subheader("Adicionar Quadras")
    selecionados = st.multiselect("Selecione as quadras da rota:", options=list(banco_total.keys()))
    
    if st.button("➕ ADICIONAR SELECIONADOS", use_container_width=True):
        if selecionados:
            for nome in selecionados:
                nid = f"{nome}_{len(st.session_state.lista_pacotes)}"
                st.session_state.lista_pacotes.append({"id": nid, "nome": nome})
                st.session_state.ultima_pos = banco_total[nome]
            salvar_progresso()
            st.success(f"{len(selecionados)} locais adicionados!")
            st.rerun()

    st.divider()
    if st.button("🗑️ LIMPAR TUDO", type="primary", use_container_width=True):
        if os.path.exists(FILE_SAVE): os.remove(FILE_SAVE)
        st.session_state.lista_pacotes, st.session_state.entregues_id, st.session_state.ultima_pos = [], [], None
        st.rerun()

# =================================================================
# 4. PROCESSAMENTO PARA O MAPA
# =================================================================
# AÇÕES VIA URL (Mantido para o botão de concluir no mapa)
q = st.query_params
if "concluir" in q:
    id_p = q["concluir"]
    if id_p not in st.session_state.entregues_id:
        st.session_state.entregues_id.append(id_p)
        for p in st.session_state.lista_pacotes:
            if p['id'] == id_p: st.session_state.ultima_pos = banco_total.get(p['nome'])
        salvar_progresso()
    st.query_params.clear()
    st.rerun()

# Lógica de agrupamento (igual ao seu original)
pendentes_total = [p for p in st.session_state.lista_pacotes if p['id'] not in st.session_state.entregues_id]
proximo_id = None
if st.session_state.ultima_pos and pendentes_total:
    dist_min = float('inf')
    for p in pendentes_total:
        coords = banco_total.get(p['nome'], (0,0))
        d = math.sqrt((st.session_state.ultima_pos[0]-coords[0])**2 + (st.session_state.ultima_pos[1]-coords[1])**2)
        if d < dist_min:
            dist_min = d
            proximo_id = p['id']

agrupado = {}
for p in st.session_state.lista_pacotes:
    nome = p['nome']
    if nome not in agrupado: agrupado[nome] = {"total": 0, "pendentes_ids": []}
    agrupado[nome]["total"] += 1
    if p['id'] not in st.session_state.entregues_id: agrupado[nome]["pendentes_ids"].append(p['id'])

pontos_js = []
for nome, info in agrupado.items():
    coords = banco_total.get(nome, (0,0))
    p_ids = info["pendentes_ids"]
    esta_concluido = len(p_ids) == 0
    cor = "#28a745" if esta_concluido else ("#fd7e14" if any(pid == proximo_id for pid in p_ids) else "#dc3545")
    num_match = re.findall(r'\d+', nome)
    base_txt = num_match[0] if num_match else nome[:3]
    display_txt = "✔" if esta_concluido else (f"{base_txt} x{info['total']}" if info['total'] > 1 else base_txt)

    pontos_js.append({
        "id": p_ids[0] if not esta_concluido else "done",
        "lat": coords[0], "lng": coords[1], "nome": nome, "total": info["total"],
        "concluido": esta_concluido, "cor": cor, "txt": display_txt
    })

# =================================================================
# 5. RENDERIZAÇÃO DO MAPA
# =================================================================
centro = st.session_state.ultima_pos if st.session_state.ultima_pos else [-16.15, -47.96]

mapa_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        body {{ margin: 0; padding: 0; font-family: sans-serif; overflow: hidden; background: #eee; }}
        #map {{ height: 100vh; width: 100vw; z-index: 1; }}
        .count-badge {{
            position: fixed; top: 15px; left: 15px; z-index: 1000;
            background: #333; color: white; padding: 10px 15px;
            border-radius: 20px; font-size: 14px; font-weight: bold; box-shadow: 0 2px 8px rgba(0,0,0,0.3);
        }}
        #sheet {{
            position: fixed; bottom: -300px; left: 0; right: 0;
            background: white; z-index: 2000; padding: 20px;
            border-radius: 20px 20px 0 0; box-shadow: 0 -5px 25px rgba(0,0,0,0.3);
            transition: bottom 0.4s ease;
        }}
        #sheet.active {{ bottom: 0; }}
        .btn {{ display: block; width: 100%; text-align: center; padding: 16px; border-radius: 12px; text-decoration: none; color: white; font-weight: bold; margin-top: 10px; }}
        .pin {{
            min-width: 36px; height: 36px; padding: 0 6px; border-radius: 18px;
            display: flex; align-items: center; justify-content: center;
            color: white; font-weight: bold; border: 2px solid white; 
            box-shadow: 0 2px 5px rgba(0,0,0,0.3); font-size: 13px;
        }}
    </style>
</head>
<body>
    <div class="count-badge">📍 {len([p for p in pontos_js if not p['concluido']])} Paradas Restantes</div>
    <div id="map"></div>
    <div id="sheet">
        <div id="s-nome" style="font-size:18px; font-weight:bold;"></div>
        <div id="s-info" style="font-size:14px; color: #666;"></div>
        <a id="s-gps" href="#" target="_blank" class="btn" style="background:#4285F4">🚀 INICIAR GPS</a>
        <a id="s-done" href="#" target="_self" class="btn" style="background:#28a745">✅ CONCLUIR ENTREGA</a>
        <button onclick="document.getElementById('sheet').classList.remove('active')" style="width:100%; margin-top:15px; background:none; border:none; color:#999;">FECHAR</button>
    </div>

    <script>
        var map = L.map('map', {{ zoomControl: false, attributionControl: false }}).setView([{centro[0]}, {centro[1]}], 16);
        L.tileLayer('https://mt1.google.com/vt/lyrs=m&x={{x}}&y={{y}}&z={{z}}').addTo(map);

        var pontos = {json.dumps(pontos_js)};
        
        pontos.forEach(function(p) {{
            var icon = L.divIcon({{
                className: '',
                html: '<div class="pin" style="background:'+p.cor+'; opacity:'+(p.concluido ? 0.6 : 1)+'">'+p.txt+'</div>',
                iconSize: [null, 36], iconAnchor: [18, 18]
            }});

            L.marker([p.lat, p.lng], {{icon: icon}}).addTo(map).on('click', function(e) {{
                document.getElementById('s-nome').innerText = p.nome;
                document.getElementById('s-info').innerText = p.total + (p.total > 1 ? " entregas aqui" : " entrega aqui");
                document.getElementById('s-gps').href = "https://www.google.com/maps/dir/?api=1&destination="+p.lat+","+p.lng;
                var btnDone = document.getElementById('s-done');
                if(p.concluido) btnDone.style.display = 'none';
                else {{ btnDone.style.display = 'block'; btnDone.href = "?concluir=" + p.id; }}
                document.getElementById('sheet').classList.add('active');
            }});
        }});
    </script>
</body>
</html>
"""

st.components.v1.html(mapa_html, height=750)
