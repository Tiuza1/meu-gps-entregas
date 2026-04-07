import json
import streamlit as st
import re
import os
import math

# =================================================================
# 1. CONFIGURAÇÃO DE TELA
# =================================================================
st.set_page_config(page_title="GPS Profissional - Logística", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    [data-testid="stHeader"], [data-testid="stToolbar"], footer { display: none !important; }
    .block-container { padding: 0 !important; max-width: 100% !important; margin: 0 !important; }
    iframe { width: 100vw; height: 100vh; border: none !important; }
    /* Estilização da Sidebar para caber no celular */
    [data-testid="stSidebar"] { background-color: #f8f9fa; min-width: 300px !important; }
    </style>
""", unsafe_allow_html=True)

# =================================================================
# 2. LOGICA DE DADOS
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
# 3. NOVO: FUNÇÃO DE ADIÇÃO EM MASSA
# =================================================================
with st.sidebar:
    st.title("📦 Gestão de Carga")
    
    with st.expander("➕ ADICIONAR EM MASSA", expanded=True):
        st.write("Cole o texto das entregas abaixo:")
        texto_bruto = st.text_area("Ex: Quadra 648, Quadra 361...", height=150)
        
        if texto_bruto:
            # Encontrar correspondências no banco de dados
            encontrados = []
            for nome_local in banco_total.keys():
                # Procura se o nome do local (ou número da quadra) está no texto colado
                if nome_local.lower() in texto_bruto.lower():
                    encontrados.append(nome_local)
            
            if encontrados:
                st.success(f"Encontrado {len(encontrados)} locais!")
                if st.button("✅ ADICIONAR TUDO AGORA"):
                    for item in encontrados:
                        nid = f"{item}_{len(st.session_state.lista_pacotes)}"
                        st.session_state.lista_pacotes.append({"id": nid, "nome": item})
                    salvar_progresso()
                    st.rerun()
            else:
                st.warning("Nenhum local reconhecido no texto.")

    st.divider()
    if st.button("🗑️ LIMPAR ROTA COMPLETA", use_container_width=True):
        if os.path.exists(FILE_SAVE): os.remove(FILE_SAVE)
        st.session_state.lista_pacotes, st.session_state.entregues_id, st.session_state.ultima_pos = [], [], None
        st.rerun()

# =================================================================
# 4. PROCESSAMENTO DE URL E MAPA (MANTIDO)
# =================================================================
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

# Lógica de agrupamento para o mapa
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
        "lat": coords[0], "lng": coords[1], "nome": nome, 
        "concluido": esta_concluido, "cor": cor, "txt": display_txt, "total": info['total']
    })

# HTML Gerado
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
        body {{ margin: 0; padding: 0; overflow: hidden; }}
        #map {{ height: 100vh; width: 100vw; }}
        .count-badge {{
            position: fixed; top: 15px; right: 15px; z-index: 1000;
            background: #333; color: white; padding: 8px 15px; border-radius: 20px; font-weight: bold;
        }}
        #sheet {{
            position: fixed; bottom: -300px; left: 0; right: 0; background: white; z-index: 2000;
            padding: 20px; border-radius: 20px 20px 0 0; transition: bottom 0.4s; box-shadow: 0 -5px 20px rgba(0,0,0,0.2);
        }}
        #sheet.active {{ bottom: 0; }}
        .btn {{ display: block; text-align: center; padding: 15px; border-radius: 10px; text-decoration: none; color: white; font-weight: bold; margin-top: 10px; }}
        .pin {{ min-width: 36px; height: 36px; padding: 0 6px; border-radius: 18px; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; border: 2px solid white; font-size: 13px; }}
    </style>
</head>
<body>
    <div class="count-badge">📍 {len(pendentes_total)} Pendentes</div>
    <div id="map"></div>
    <div id="sheet">
        <div id="s-nome" style="font-size:18px; font-weight:bold;"></div>
        <a id="s-gps" href="#" target="_blank" class="btn" style="background:#4285F4">🚀 INICIAR GPS</a>
        <a id="s-done" href="#" target="_self" class="btn" style="background:#28a745">✅ CONCLUIR</a>
        <button onclick="document.getElementById('sheet').classList.remove('active')" style="width:100%; border:none; background:none; color:gray; margin-top:10px;">FECHAR</button>
    </div>
    <script>
        var map = L.map('map', {{ zoomControl: false, attributionControl: false }}).setView([{centro[0]}, {centro[1]}], 15);
        L.tileLayer('https://mt1.google.com/vt/lyrs=m&x={{x}}&y={{y}}&z={{z}}').addTo(map);

        var pontos = {json.dumps(pontos_js)};
        pontos.forEach(function(p) {{
            var icon = L.divIcon({{ className: '', html: '<div class="pin" style="background:'+p.cor+'; opacity:'+(p.concluido?0.5:1)+'">'+p.txt+'</div>', iconSize: [null, 36] }});
            L.marker([p.lat, p.lng], {{icon: icon}}).addTo(map).on('click', function() {{
                document.getElementById('s-nome').innerText = p.nome + " (" + p.total + " pacotes)";
                document.getElementById('s-gps').href = "https://www.google.com/maps/dir/?api=1&destination="+p.lat+","+p.lng;
                var btn = document.getElementById('s-done');
                if(p.concluido) btn.style.display='none'; else {{ btn.style.display='block'; btn.href="?concluir="+p.id; }}
                document.getElementById('sheet').classList.add('active');
            }});
        }});
    </script>
</body>
</html>
"""
st.components.v1.html(mapa_html, height=800)
