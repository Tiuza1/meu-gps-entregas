import json
import streamlit as st
import re
import os
import math
import time

# =================================================================
# 1. CONFIGURAÇÃO DE TELA
# =================================================================
st.set_page_config(page_title="GPS Profissional", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    [data-testid="stHeader"], [data-testid="stSidebar"], [data-testid="stToolbar"], footer { display: none !important; }
    .block-container { padding: 0 !important; max-width: 100% !important; margin: 0 !important; }
    iframe { width: 100vw; height: 100vh; border: none !important; }
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
    dados = {
        "lista_pacotes": st.session_state.lista_pacotes, 
        "entregues_id": st.session_state.entregues_id, 
        "ultima_pos": st.session_state.ultima_pos
    }
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

# --- AÇÕES VIA URL ---
q = st.query_params
if "add_batch" in q:
    nomes = q["add_batch"].split("|")
    for nome in nomes:
        if nome in banco_total:
            nid = f"{nome}_{time.time_ns()}"
            st.session_state.lista_pacotes.append({"id": nid, "nome": nome})
            st.session_state.ultima_pos = banco_total[nome]
    salvar_progresso()
    st.query_params.clear()
    st.rerun()

if "concluir" in q:
    id_p = q["concluir"]
    if id_p not in st.session_state.entregues_id:
        st.session_state.entregues_id.append(id_p)
        for p in st.session_state.lista_pacotes:
            if p['id'] == id_p: st.session_state.ultima_pos = banco_total.get(p['nome'])
        salvar_progresso()
    st.query_params.clear()
    st.rerun()

if "limpar" in q:
    if os.path.exists(FILE_SAVE): os.remove(FILE_SAVE)
    st.session_state.lista_pacotes, st.session_state.entregues_id, st.session_state.ultima_pos = [], [], None
    st.query_params.clear()
    st.rerun()

# --- AGRUPAMENTO E PONTOS ---
pendentes_total = [p for p in st.session_state.lista_pacotes if p['id'] not in st.session_state.entregues_id]
proximo_id = None
if st.session_state.ultima_pos and pendentes_total:
    dist_min = float('inf')
    for p in pendentes_total:
        coords = banco_total.get(p['nome'], (0,0))
        d = math.sqrt((st.session_state.ultima_pos[0]-coords[0])**2 + (st.session_state.ultima_pos[1]-coords[1])**2)
        if d < dist_min: dist_min = d; proximo_id = p['id']

agrupado = {}
for p in st.session_state.lista_pacotes:
    nome = p['nome']
    if nome not in agrupado: agrupado[nome] = {"total": 0, "pendentes_ids": []}
    agrupado[nome]["total"] += 1
    if p['id'] not in st.session_state.entregues_id: 
        agrupado[nome]["pendentes_ids"].append(p['id'])

pontos_js = []
for nome, info in agrupado.items():
    coords = banco_total.get(nome, (0,0))
    p_ids = info["pendentes_ids"]
    esta_concluido = len(p_ids) == 0
    cor = "#28a745" if esta_concluido else ("#fd7e14" if any(pid == proximo_id for pid in p_ids) else "#dc3545")
    
    num_match = re.findall(r'\d+', nome)
    base_txt = num_match[0] if num_match else nome[:3]
    display_txt = "✔" if esta_concluido else (f"{base_txt} x{len(p_ids)}" if len(p_ids) > 1 else base_txt)
    
    pontos_js.append({
        "id_marcador": f"m_{nome.replace(' ', '_')}",
        "id_item": p_ids[0] if not esta_concluido else "done",
        "lat": coords[0], "lng": coords[1], "nome": nome,
        "restantes": len(p_ids), "concluido": esta_concluido, "cor": cor, "txt": display_txt
    })

# =================================================================
# 3. HTML/JS
# =================================================================
centro = st.session_state.ultima_pos if st.session_state.ultima_pos else [-16.15, -47.96]
lista_opcoes_html = "".join([f'<option value="{n}">' for n in banco_total.keys()])

mapa_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        body {{ margin: 0; padding: 0; font-family: sans-serif; overflow: hidden; }}
        #map {{ height: 100vh; width: 100vw; z-index: 1; }}

        .search-container {{
            position: fixed; top: 10px; left: 10px; right: 10px; z-index: 1000;
            background: white; padding: 8px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        }}
        .search-row {{ display: flex; gap: 5px; }}
        #input-busca {{ flex: 1; border: 1px solid #ddd; padding: 12px; border-radius: 8px; font-size: 16px; outline: none; }}
        .btn-add {{ background: #007bff; color: white; border: none; padding: 0 20px; border-radius: 8px; font-size: 20px; }}

        #batch-list {{ display: none; flex-wrap: wrap; gap: 5px; margin-top: 8px; padding-top: 8px; border-top: 1px solid #eee; }}
        .batch-item {{ background: #f8f9fa; padding: 4px 10px; border-radius: 15px; font-size: 12px; border: 1px solid #007bff; }}
        .btn-confirm {{ display: none; width: 100%; background: #28a745; color: white; border: none; padding: 12px; border-radius: 8px; font-weight: bold; margin-top: 8px; }}

        #sheet {{
            position: fixed; bottom: -300px; left: 0; right: 0;
            background: white; z-index: 2000; padding: 20px;
            border-radius: 20px 20px 0 0; box-shadow: 0 -5px 25px rgba(0,0,0,0.3);
            transition: bottom 0.3s ease;
        }}
        #sheet.active {{ bottom: 0; }}
        .btn-row {{ display: flex; gap: 10px; margin-top: 15px; }}
        .btn {{ flex: 1; text-align: center; padding: 16px; border-radius: 12px; text-decoration: none; color: white; font-weight: bold; font-size: 14px; border:none; }}
        
        .pin {{
            min-width: 38px; height: 38px; padding: 0 8px; border-radius: 19px;
            display: flex; align-items: center; justify-content: center;
            color: white; font-weight: bold; border: 2px solid white; font-size: 13px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.2); transition: all 0.3s;
        }}
    </style>
</head>
<body>

    <div class="search-container">
        <div class="search-row">
            <input type="text" id="input-busca" list="lugares" placeholder="Quadra...">
            <datalist id="lugares">{lista_opcoes_html}</datalist>
            <button class="btn-add" onclick="addToQueue()">➕</button>
        </div>
        <div id="batch-list"></div>
        <button id="btn-confirm-all" class="btn-confirm" onclick="sendBatch()">CONFIRMAR PEDIDOS</button>
    </div>

    <div id="map"></div>

    <div id="sheet">
        <div id="s-nome" style="font-size:18px; font-weight:bold;">Local</div>
        <div id="s-info" style="font-size:14px; color: #666; margin-top:4px;"></div>
        <div class="btn-row">
            <a id="s-gps" href="#" target="_blank" class="btn" style="background:#4285F4">🚀 GPS</a>
            <button id="s-done-btn" onclick="confirmarEntrega()" class="btn" style="background:#28a745">✅ CONCLUIR</button>
        </div>
        <button onclick="closeSheet()" style="width:100%; margin-top:15px; background:none; border:none; color:#ccc;">FECHAR</button>
    </div>

    <script>
        // Memória do mapa
        var lastLat = localStorage.getItem('lat') || {centro[0]};
        var lastLng = localStorage.getItem('lng') || {centro[1]};
        var lastZoom = localStorage.getItem('zoom') || 16;

        var map = L.map('map', {{ zoomControl: false, attributionControl: false }}).setView([lastLat, lastLng], lastZoom);
        L.tileLayer('https://mt1.google.com/vt/lyrs=m&x={{x}}&y={{y}}&z={{z}}').addTo(map);

        map.on('moveend', function() {{
            localStorage.setItem('lat', map.getCenter().lat);
            localStorage.setItem('lng', map.getCenter().lng);
            localStorage.setItem('zoom', map.getZoom());
        }});

        // Fila de adição
        var queue = [];
        function addToQueue() {{
            var inp = document.getElementById('input-busca');
            if(inp.value) {{ queue.push(inp.value); renderQueue(); inp.value=""; inp.focus(); }}
        }}
        function renderQueue() {{
            var c = document.getElementById('batch-list');
            var b = document.getElementById('btn-confirm-all');
            c.style.display = queue.length ? "flex" : "none";
            b.style.display = queue.length ? "block" : "none";
            c.innerHTML = queue.map(i => '<div class="batch-item">'+i+'</div>').join('');
        }}
        function sendBatch() {{ window.location.href = "?add_batch=" + queue.map(encodeURIComponent).join('|'); }}

        // Marcadores
        var pontos = {json.dumps(pontos_js)};
        var itemSelecionado = null;

        function closeSheet() {{ document.getElementById('sheet').classList.remove('active'); }}

        pontos.forEach(function(p) {{
            var icon = L.divIcon({{
                className: '',
                html: '<div id="'+p.id_marcador+'" class="pin" style="background:'+p.cor+'; opacity:'+(p.concluido ? 0.6 : 1)+'">'+p.txt+'</div>',
                iconSize: [null, 38], iconAnchor: [19, 19]
            }});

            var m = L.marker([p.lat, p.lng], {{icon: icon}}).addTo(map);
            m.on('click', function(e) {{
                L.DomEvent.stopPropagation(e);
                itemSelecionado = p;
                document.getElementById('s-nome').innerText = p.nome;
                document.getElementById('s-info').innerText = p.restantes + " pendentes";
                document.getElementById('s-gps').href = "https://www.google.com/maps/dir/?api=1&destination="+p.lat+","+p.lng;
                var btn = document.getElementById('s-done-btn');
                btn.style.display = p.concluido ? 'none' : 'block';
                document.getElementById('sheet').classList.add('active');
            }});
        }});

        function confirmarEntrega() {{
            if(!itemSelecionado) return;
            // FEEDBACK INSTANTÂNEO NO MAPA
            var el = document.getElementById(itemSelecionado.id_marcador);
            if(el) {{
                if(itemSelecionado.restantes > 1) {{
                    el.innerText = itemSelecionado.txt.split(' ')[0] + " x" + (itemSelecionado.restantes - 1);
                }} else {{
                    el.innerText = "✔";
                    el.style.background = "#28a745";
                    el.style.opacity = "0.6";
                }}
            }}
            closeSheet();
            // Salva no Python logo em seguida
            setTimeout(() => {{ window.location.href = "?concluir=" + itemSelecionado.id_item; }}, 100);
        }}

        map.on('click', closeSheet);
        map.locate({{watch: true, enableHighAccuracy: true}});
        var userM;
        map.on('locationfound', function(e) {{
            if (!userM) userM = L.circleMarker(e.latlng, {{radius: 8, color: 'white', fillColor: '#4285F4', fillOpacity: 1, weight: 3}}).addTo(map);
            else userM.setLatLng(e.latlng);
        }});
    </script>
</body>
</html>
"""

st.components.v1.html(mapa_html, height=700)
