import json
import streamlit as st
import re
import os
import math
import time

# =================================================================
# 1. CONFIGURAÇÃO DE TELA (UI LIMPA)
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
            # ID único usando timestamp para permitir duplicatas de nome
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

# --- LÓGICA DE PROXIMIDADE E AGRUPAMENTO ---
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
    if p['id'] not in st.session_state.entregues_id: 
        agrupado[nome]["pendentes_ids"].append(p['id'])

pontos_js = []
for nome, info in agrupado.items():
    coords = banco_total.get(nome, (0,0))
    p_ids = info["pendentes_ids"]
    esta_concluido = len(p_ids) == 0
    
    # Define a cor: Verde se concluído, Laranja se for o próximo mais perto, Vermelho se pendente
    cor = "#28a745" if esta_concluido else ("#fd7e14" if any(pid == proximo_id for pid in p_ids) else "#dc3545")
    
    # Texto do marcador: Se tiver mais de 1, mostra "Nome xQtd"
    num_match = re.findall(r'\d+', nome)
    base_txt = num_match[0] if num_match else nome[:3]
    
    if esta_concluido:
        display_txt = "✔"
    else:
        # Se houver múltiplas entregas no mesmo lugar, mostra ex: "31 x2"
        display_txt = f"{base_txt} x{len(p_ids)}" if len(p_ids) > 1 else base_txt

    pontos_js.append({
        "id": p_ids[0] if not esta_concluido else "done", 
        "lat": coords[0], "lng": coords[1], 
        "nome": nome, 
        "total_orig": info['total'],
        "restantes": len(p_ids),
        "concluido": esta_concluido, 
        "cor": cor, 
        "txt": display_txt
    })

total_bolinhas = len(pontos_js)
bolinhas_pendentes = len([p for p in pontos_js if not p['concluido']])

# =================================================================
# 4. HTML/JS
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
        body {{ margin: 0; padding: 0; font-family: sans-serif; overflow: hidden; background: #eee; }}
        #map {{ height: 100vh; width: 100vw; z-index: 1; }}

        .search-container {{
            position: fixed; top: 10px; left: 10px; right: 10px; z-index: 1000;
            background: white; padding: 8px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        }}
        .search-row {{ display: flex; gap: 5px; }}
        #input-busca {{ flex: 1; border: 1px solid #ddd; padding: 12px; border-radius: 8px; font-size: 16px; outline: none; }}
        .btn-add {{ background: #007bff; color: white; border: none; padding: 0 20px; border-radius: 8px; font-size: 20px; }}

        #batch-list {{ 
            display: none; flex-wrap: wrap; gap: 5px; margin-top: 8px; padding-top: 8px; border-top: 1px solid #eee;
        }}
        .batch-item {{ 
            background: #f8f9fa; padding: 4px 10px; border-radius: 15px; font-size: 12px; 
            display: flex; align-items: center; gap: 5px; border: 1px solid #007bff;
        }}
        .batch-item b {{ color: #d33; cursor: pointer; padding: 0 4px; }}
        .btn-confirm {{ 
            display: none; width: 100%; background: #28a745; color: white; border: none; 
            padding: 12px; border-radius: 8px; font-weight: bold; margin-top: 8px; cursor: pointer;
        }}

        .count-badge {{
            position: fixed; top: 85px; left: 10px; z-index: 999;
            background: #333; color: white; padding: 6px 12px;
            border-radius: 20px; font-size: 13px; font-weight: bold;
        }}
        .btn-clear {{
            position: fixed; top: 85px; right: 10px; z-index: 999;
            background: rgba(255,255,255,0.9); border: none; padding: 8px 12px;
            border-radius: 8px; font-size: 12px; font-weight: bold; color: #d33;
        }}

        #sheet {{
            position: fixed; bottom: -300px; left: 0; right: 0;
            background: white; z-index: 2000; padding: 20px;
            border-radius: 20px 20px 0 0; box-shadow: 0 -5px 25px rgba(0,0,0,0.3);
            transition: bottom 0.4s ease;
        }}
        #sheet.active {{ bottom: 0; }}
        .btn-row {{ display: flex; gap: 10px; margin-top: 15px; }}
        .btn {{ flex: 1; text-align: center; padding: 16px; border-radius: 12px; text-decoration: none; color: white; font-weight: bold; font-size: 14px; }}
        
        .pin {{
            min-width: 38px; height: 38px; padding: 0 8px; border-radius: 19px;
            display: flex; align-items: center; justify-content: center;
            color: white; font-weight: bold; border: 2px solid white; font-size: 13px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.3);
            white-space: nowrap;
        }}
    </style>
</head>
<body>

    <div class="search-container">
        <div class="search-row">
            <input type="text" id="input-busca" list="lugares" placeholder="Adicionar quadra...">
            <datalist id="lugares">{lista_opcoes_html}</datalist>
            <button class="btn-add" onclick="addToQueue()">➕</button>
        </div>
        <div id="batch-list"></div>
        <button id="btn-confirm-all" class="btn-confirm" onclick="sendBatch()">CONFIRMAR PEDIDOS</button>
    </div>

    <div class="count-badge">📍 {bolinhas_pendentes} locais restantes</div>
    <button class="btn-clear" onclick="if(confirm('Limpar tudo?')) window.location.href='?limpar=1'">🗑️</button>

    <div id="map"></div>

    <div id="sheet">
        <div id="s-nome" style="font-size:18px; font-weight:bold;">Local</div>
        <div id="s-info" style="font-size:14px; color: #666; margin-top: 4px;"></div>
        <div class="btn-row">
            <a id="s-gps" href="#" target="_blank" class="btn" style="background:#4285F4">🚀 GOOGLE MAPS</a>
            <a id="s-done" href="#" target="_self" class="btn" style="background:#28a745">✅ CONCLUIR 1</a>
        </div>
        <button onclick="closeSheet()" style="width:100%; margin-top:15px; background:none; border:none; color:#999; font-size: 14px;">FECHAR</button>
    </div>

    <script>
        var map = L.map('map', {{ zoomControl: false, attributionControl: false }}).setView([{centro[0]}, {centro[1]}], 16);
        L.tileLayer('https://mt1.google.com/vt/lyrs=m&x={{x}}&y={{y}}&z={{z}}').addTo(map);

        var queue = [];

        function addToQueue() {{
            var input = document.getElementById('input-busca');
            var val = input.value.trim();
            // Removido a trava de duplicados: pode adicionar a mesma quadra várias vezes
            if(val) {{
                queue.push(val);
                renderQueue();
                input.value = "";
                input.focus();
            }}
        }}

        function removeFromQueue(idx) {{
            queue.splice(idx, 1);
            renderQueue();
        }}

        function renderQueue() {{
            var container = document.getElementById('batch-list');
            var btn = document.getElementById('btn-confirm-all');
            if(queue.length > 0) {{
                container.style.display = "flex";
                btn.style.display = "block";
                container.innerHTML = queue.map((item, i) => 
                    '<div class="batch-item">' + item + '<b onclick="removeFromQueue('+i+')">✕</b></div>'
                ).join('');
            }} else {{
                container.style.display = "none";
                btn.style.display = "none";
            }}
        }}

        function sendBatch() {{
            if(queue.length > 0) {{
                var param = queue.map(encodeURIComponent).join('|');
                window.location.href = "?add_batch=" + param;
            }}
        }}

        // --- RENDERIZAR PONTOS ---
        var pontos = {json.dumps(pontos_js)};
        function closeSheet() {{ document.getElementById('sheet').classList.remove('active'); }}

        pontos.forEach(function(p) {{
            var icon = L.divIcon({{
                className: '',
                html: '<div class="pin" style="background:'+p.cor+'; opacity:'+(p.concluido ? 0.6 : 1)+'">'+p.txt+'</div>',
                iconSize: [null, 38], iconAnchor: [19, 19]
            }});

            var marker = L.marker([p.lat, p.lng], {{icon: icon}}).addTo(map);
            marker.on('click', function(e) {{
                L.DomEvent.stopPropagation(e);
                document.getElementById('s-nome').innerText = p.nome;
                
                var infoTxt = p.concluido ? "Todas entregues" : (p.restantes + " pendente(s) neste local");
                document.getElementById('s-info').innerText = infoTxt;
                
                document.getElementById('s-gps').href = "https://www.google.com/maps/dir/?api=1&destination="+p.lat+","+p.lng;
                
                var btnDone = document.getElementById('s-done');
                btnDone.style.display = p.concluido ? 'none' : 'block';
                btnDone.href = "?concluir=" + p.id;
                btnDone.innerText = p.restantes > 1 ? "✅ CONCLUIR 1 DE " + p.restantes : "✅ CONCLUIR";
                
                document.getElementById('sheet').classList.add('active');
                map.panTo([p.lat, p.lng]);
            }});
        }});

        map.on('click', closeSheet);
        
        // Localização do usuário
        map.locate({{watch: true, enableHighAccuracy: true}});
        var userMarker;
        map.on('locationfound', function(e) {{
            if (!userMarker) {{
                userMarker = L.circleMarker(e.latlng, {{radius: 8, color: 'white', fillColor: '#4285F4', fillOpacity: 1, weight: 3}}).addTo(map);
            }} else {{ userMarker.setLatLng(e.latlng); }}
        }});
    </script>
</body>
</html>
"""

st.components.v1.html(mapa_html, height=700)
