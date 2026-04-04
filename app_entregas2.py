import json
import streamlit as st
import re
import os
import math
from collections import Counter

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
        # Criar dicionário e ordenar chaves para busca mais fácil
        banco = {str(l['properties'].get('title') or l['properties'].get('name')).strip(): 
                (l['geometry']['coordinates'][1], l['geometry']['coordinates'][0]) 
                for l in dados_j.get('features',[])}
        return dict(sorted(banco.items()))
    except: return {}

banco_total = carregar_banco()

# AÇÕES VIA URL
q = st.query_params
if "add" in q:
    nome = q["add"]
    if nome in banco_total:
        nid = f"{nome}_{len(st.session_state.lista_pacotes)}_{math.floor(st.time.time())}" if 'time' in dir(st) else f"{nome}_{len(st.session_state.lista_pacotes)}"
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

# --- LÓGICA DE AGRUPAMENTO PARA O MAPA ---
pendentes = [p for p in st.session_state.lista_pacotes if p['id'] not in st.session_state.entregues_id]

# Encontrar o ID mais próximo para destacar (Lógica do GPS)
proximo_id = None
if st.session_state.ultima_pos and pendentes:
    dist_min = float('inf')
    for p in pendentes:
        coords = banco_total.get(p['nome'], (0,0))
        d = math.sqrt((st.session_state.ultima_pos[0]-coords[0])**2 + (st.session_state.ultima_pos[1]-coords[1])**2)
        if d < dist_min:
            dist_min = d
            proximo_id = p['id']

# Agrupar pacotes por nome para mostrar "x2", "x3"
agrupado = {}
for p in st.session_state.lista_pacotes:
    nome = p['nome']
    if nome not in agrupado:
        agrupado[nome] = {"total": 0, "pendentes_ids": [], "concluidos_count": 0}
    
    agrupado[nome]["total"] += 1
    if p['id'] in st.session_state.entregues_id:
        agrupado[nome]["concluidos_count"] += 1
    else:
        agrupado[nome]["pendentes_ids"].append(p['id'])

pontos_js = []
for nome, info in agrupado.items():
    coords = banco_total.get(nome, (0,0))
    total = info["total"]
    p_ids = info["pendentes_ids"]
    esta_concluido = len(p_ids) == 0
    
    # Define a cor
    if esta_concluido:
        cor = "#28a745" # Verde
    elif any(pid == proximo_id for pid in p_ids):
        cor = "#fd7e14" # Laranja (Próximo)
    else:
        cor = "#dc3545" # Vermelho
    
    # Texto da bolinha (Ex: 30 x2)
    num_match = re.findall(r'\d+', nome)
    base_txt = num_match[0] if num_match else nome[:3]
    
    if esta_concluido:
        display_txt = "✔"
    else:
        display_txt = f"{base_txt} x{total}" if total > 1 else base_txt

    pontos_js.append({
        "id": p_ids[0] if not esta_concluido else "done",
        "lat": coords[0], "lng": coords[1], 
        "nome": f"{nome} ({total} pacotes)" if total > 1 else nome,
        "concluido": esta_concluido, 
        "cor": cor, 
        "txt": display_txt
    })

# =================================================================
# 4. HTML/JS (INTERFACE COMPLETA)
# =================================================================
centro = st.session_state.ultima_pos if st.session_state.ultima_pos else [-16.15, -47.96]
# Lista de opções ordenada para facilitar a busca exata
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
            display: flex; gap: 5px; background: white; padding: 8px;
            border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        }}
        #input-busca {{
            flex: 1; border: 1px solid #ddd; padding: 10px; 
            border-radius: 8px; font-size: 16px; outline: none;
        }}
        .btn-add {{
            background: #28a745; color: white; border: none; 
            padding: 0 15px; border-radius: 8px; font-size: 20px; font-weight: bold;
        }}

        #sheet {{
            position: fixed; bottom: -300px; left: 0; right: 0;
            background: white; z-index: 2000; padding: 20px;
            border-radius: 20px 20px 0 0; box-shadow: 0 -5px 25px rgba(0,0,0,0.3);
            transition: bottom 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        }}
        #sheet.active {{ bottom: 0; }}
        .sheet-title {{ font-size: 18px; font-weight: bold; margin-bottom: 15px; color: #333; }}
        .btn-row {{ display: flex; gap: 10px; }}
        .btn {{
            flex: 1; text-align: center; padding: 16px; border-radius: 12px;
            text-decoration: none; color: white; font-weight: bold; font-size: 14px;
        }}

        .pin {{
            min-width: 36px; height: 36px; padding: 0 5px; border-radius: 18px;
            display: flex; align-items: center; justify-content: center;
            color: white; font-weight: bold; border: 2px solid white; 
            box-shadow: 0 2px 5px rgba(0,0,0,0.3); white-space: nowrap; font-size: 13px;
        }}

        .btn-clear {{
            position: fixed; top: 75px; right: 10px; z-index: 1000;
            background: rgba(255,255,255,0.9); border: none; padding: 8px 12px;
            border-radius: 8px; font-size: 12px; font-weight: bold; color: #d33;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }}
    </style>
</head>
<body>

    <div class="search-container">
        <input type="text" id="input-busca" list="lugares" placeholder="Ex: Q 4 Pix...">
        <datalist id="lugares">{lista_opcoes_html}</datalist>
        <button class="btn-add" onclick="adicionar()">➕</button>
    </div>

    <button class="btn-clear" onclick="if(confirm('Limpar lista de entregas?')) window.location.href='?limpar=1'">🗑️ LIMPAR</button>

    <div id="map"></div>

    <div id="sheet">
        <div id="s-nome" class="sheet-title">Local</div>
        <div class="btn-row">
            <a id="s-gps" href="#" target="_blank" class="btn" style="background:#4285F4">🚀 GPS</a>
            <a id="s-done" href="#" target="_self" class="btn" style="background:#28a745">✅ CONCLUIR</a>
        </div>
        <button onclick="closeSheet()" style="width:100%; margin-top:15px; background:none; border:none; color:#999;">FECHAR</button>
    </div>

    <script>
        var map = L.map('map', {{ zoomControl: false, attributionControl: false }}).setView([{centro[0]}, {centro[1]}], 16);
        L.tileLayer('https://mt1.google.com/vt/lyrs=m&x={{x}}&y={{y}}&z={{z}}').addTo(map);

        var pontos = {json.dumps(pontos_js)};
        
        function adicionar() {{
            var val = document.getElementById('input-busca').value;
            if(val) window.location.href = "?add=" + encodeURIComponent(val);
        }}

        function closeSheet() {{ document.getElementById('sheet').classList.remove('active'); }}

        pontos.forEach(function(p) {{
            var icon = L.divIcon({{
                className: '',
                html: '<div class="pin" style="background:'+p.cor+'; opacity:'+(p.concluido ? 0.6 : 1)+'">'+p.txt+'</div>',
                iconSize: [null, 36], iconAnchor: [18, 18]
            }});

            var marker = L.marker([p.lat, p.lng], {{icon: icon}}).addTo(map);
            
            marker.on('click', function(e) {{
                L.DomEvent.stopPropagation(e);
                document.getElementById('s-nome').innerText = p.nome;
                document.getElementById('s-gps').href = "https://www.google.com/maps/dir/?api=1&destination="+p.lat+","+p.lng;
                
                var btnDone = document.getElementById('s-done');
                if(p.concluido) {{
                    btnDone.style.display = 'none';
                }} else {{
                    btnDone.style.display = 'block';
                    btnDone.href = "?concluir=" + p.id;
                }}
                
                document.getElementById('sheet').classList.add('active');
                map.panTo([p.lat, p.lng]);
            }});
        }});

        map.on('click', closeSheet);

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
