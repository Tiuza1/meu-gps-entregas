import json
import streamlit as st
import re
import os
import math

# =================================================================
# 1. CONFIGURAÇÃO INICIAL
# =================================================================
st.set_page_config(
    page_title="GPS Profissional",
    layout="wide",
    initial_sidebar_state="collapsed"
)

FILE_SAVE = "progresso_final.json"

if "lista_pacotes" not in st.session_state:
    st.session_state.lista_pacotes = []

if "entregues_id" not in st.session_state:
    st.session_state.entregues_id = []

if "ultima_pos" not in st.session_state:
    st.session_state.ultima_pos = None


# =================================================================
# 2. FUNÇÕES DE PERSISTÊNCIA
# =================================================================
def salvar_progresso():
    dados = {
        "lista_pacotes": st.session_state.lista_pacotes,
        "entregues_id": st.session_state.entregues_id,
        "ultima_pos": st.session_state.ultima_pos
    }
    with open(FILE_SAVE, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)


def carregar_progresso():
    if os.path.exists(FILE_SAVE):
        try:
            with open(FILE_SAVE, "r", encoding="utf-8") as f:
                d = json.load(f)
                st.session_state.lista_pacotes = d.get("lista_pacotes", [])
                st.session_state.entregues_id = d.get("entregues_id", [])
                st.session_state.ultima_pos = d.get("ultima_pos")
        except Exception:
            pass


@st.cache_data
def carregar_banco():
    try:
        with open("Lugares marcados.json", "r", encoding="utf-8") as f:
            dados_j = json.load(f)

        return {
            str(l["properties"].get("title") or l["properties"].get("name")).strip():
            (l["geometry"]["coordinates"][1], l["geometry"]["coordinates"][0])
            for l in dados_j.get("features", [])
        }
    except Exception:
        return {}


def atualizar_ultima_pos_por_nome(nome_ponto):
    try:
        with open("Lugares marcados.json", "r", encoding="utf-8") as f:
            db = json.load(f)

        for l in db.get("features", []):
            nome_b = str(l["properties"].get("title") or l["properties"].get("name")).strip()
            if nome_b == nome_ponto:
                st.session_state.ultima_pos = (
                    l["geometry"]["coordinates"][1],
                    l["geometry"]["coordinates"][0]
                )
                return
    except Exception:
        pass


# =================================================================
# 3. CARREGAMENTO INICIAL
# =================================================================
if not st.session_state.lista_pacotes and os.path.exists(FILE_SAVE):
    carregar_progresso()

banco_total = carregar_banco()


# =================================================================
# 4. PROCESSAMENTO DE AÇÕES VIA QUERY PARAMS
# =================================================================
qp = st.query_params

if "action" in qp and "id" in qp:
    action = qp["action"]
    item_id = qp["id"]

    if action == "done":
        if item_id not in st.session_state.entregues_id:
            st.session_state.entregues_id.append(item_id)

            ponto = next(
                (p for p in st.session_state.lista_pacotes if p["id"] == item_id),
                None
            )

            if ponto:
                atualizar_ultima_pos_por_nome(ponto["nome"])

    elif action == "delete":
        st.session_state.lista_pacotes = [
            p for p in st.session_state.lista_pacotes
            if p["id"] != item_id
        ]

        st.session_state.entregues_id = [
            eid for eid in st.session_state.entregues_id
            if eid != item_id
        ]

    salvar_progresso()
    st.query_params.clear()
    st.rerun()


# =================================================================
# 5. CSS GLOBAL
# =================================================================
st.markdown("""
    <style>
    [data-testid="stHeader"], [data-testid="stToolbar"], footer {
        display: none !important;
    }

    [data-testid="stSidebarCollapsedControl"] {
        background-color: #1E1E1E !important;
        color: white !important;
        border-radius: 10px !important;
        width: 55px !important;
        height: 55px !important;
        top: 8px !important;
        left: 8px !important;
        z-index: 1000000 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        box-shadow: 0px 4px 10px rgba(0,0,0,0.4) !important;
    }

    [data-testid="stSidebarCollapsedControl"] svg {
        fill: white !important;
        width: 32px !important;
        height: 32px !important;
    }

    .block-container {
        padding: 4.5rem 0.5rem 0.5rem 0.5rem !important;
    }

    .stButton > button {
        width: 100% !important;
        height: 50px !important;
        border-radius: 12px !important;
        font-weight: bold !important;
    }

    iframe {
        border: none !important;
        border-radius: 15px !important;
    }
    </style>
""", unsafe_allow_html=True)


# =================================================================
# 6. MENU LATERAL
# =================================================================
with st.sidebar:
    st.header("⚙️ Opções")

    if st.button("🗑️ LIMPAR TUDO"):
        if os.path.exists(FILE_SAVE):
            os.remove(FILE_SAVE)

        st.session_state.lista_pacotes = []
        st.session_state.entregues_id = []
        st.session_state.ultima_pos = None
        st.rerun()


# =================================================================
# 7. BUSCA E ADIÇÃO DE NOVOS PONTOS
# =================================================================
c1, c2 = st.columns([5, 1])

with c1:
    busca = st.selectbox(
        "Busca",
        options=["(Adicionar...)"] + list(banco_total.keys()),
        label_visibility="collapsed"
    )

with c2:
    if st.button("➕"):
        if busca and busca != "(Adicionar...)":
            existente = any(
                p["nome"] == busca and p["id"] not in st.session_state.entregues_id
                for p in st.session_state.lista_pacotes
            )

            if not existente:
                nid = f"{busca}_{len(st.session_state.lista_pacotes)}"
                st.session_state.lista_pacotes.append({
                    "id": nid,
                    "nome": busca
                })
                st.session_state.ultima_pos = banco_total[busca]
                salvar_progresso()
                st.rerun()


# =================================================================
# 8. MONTAGEM DOS PONTOS DO MAPA
# =================================================================
proximo_id = None
pontos_para_o_mapa = []

for p in st.session_state.lista_pacotes:
    coords = banco_total.get(p["nome"], (0, 0))
    concluido = p["id"] in st.session_state.entregues_id

    if concluido:
        cor = "#28a745"
        txt = "V"
    else:
        cor = "#dc3545"
        numeros = re.findall(r"\d+", p["nome"])
        txt = numeros[0] if numeros else p["nome"][:2].upper()

    pontos_para_o_mapa.append({
        "id": p["id"],
        "lat": coords[0],
        "lng": coords[1],
        "nome": p["nome"],
        "concluido": concluido,
        "cor": cor,
        "txt": txt
    })

pendentes = [p for p in pontos_para_o_mapa if not p["concluido"]]

if st.session_state.ultima_pos and pendentes:
    menor_dist = float("inf")

    for p in pendentes:
        d = math.sqrt(
            (st.session_state.ultima_pos[0] - p["lat"]) ** 2 +
            (st.session_state.ultima_pos[1] - p["lng"]) ** 2
        )
        if d < menor_dist:
            menor_dist = d
            proximo_id = p["id"]

for p in pontos_para_o_mapa:
    if p["id"] == proximo_id:
        p["cor"] = "#fd7e14"


# =================================================================
# 9. MAPA HTML
# =================================================================
centro = st.session_state.ultima_pos if st.session_state.ultima_pos else [-16.15, -47.96]

mapa_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8" />
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        html, body {{
            margin: 0;
            padding: 0;
            width: 100%;
            height: 100%;
            font-family: sans-serif;
        }}

        #map {{
            height: 100vh;
            width: 100%;
            background: #e5e3df;
        }}

        .pin {{
            width: 38px;
            height: 38px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
            border: 2px solid white;
            box-shadow: 0 2px 5px rgba(0,0,0,0.30);
            font-size: 16px;
        }}

        .pin.done {{
            background: #28a745 !important;
            color: white;
            font-size: 18px;
        }}

        .leaflet-popup-content-wrapper {{
            background: rgba(255, 255, 255, 0.55) !important;
            backdrop-filter: blur(12px);
            border-radius: 15px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        }}

        .leaflet-popup-tip {{
            background: rgba(255, 255, 255, 0.55) !important;
        }}

        .popup-container {{
            display: flex;
            flex-direction: column;
            gap: 8px;
            padding: 5px;
            min-width: 150px;
        }}

        .popup-title {{
            font-weight: bold;
            text-align: center;
            margin-bottom: 5px;
            font-size: 14px;
            color: #1E1E1E;
        }}

        .btn {{
            text-decoration: none;
            border: none;
            border-radius: 8px;
            padding: 12px;
            color: white;
            font-weight: bold;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            transition: 0.2s;
            font-size: 13px;
        }}

        .btn:hover {{
            filter: brightness(0.95);
        }}

        .btn-gps {{
            background: #1E1E1E;
        }}

        .btn-done {{
            background: #28a745;
        }}

        .btn-del {{
            background: #dc3545;
        }}
    </style>
</head>
<body>
    <div id="map"></div>

    <script>
        var map = L.map('map', {{ zoomControl: false }}).setView([{centro[0]}, {centro[1]}], 16);

        L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
            maxZoom: 20,
            attribution: '&copy; OpenStreetMap'
        }}).addTo(map);

        var pontos = {json.dumps(pontos_para_o_mapa, ensure_ascii=False)};
        var userMarker;

        pontos.forEach(function(p) {{
            var classeExtra = p.concluido ? 'done' : '';

            var icon = L.divIcon({{
                className: '',
                html: '<div class="pin ' + classeExtra + '" style="background:' + p.cor + ';">' + p.txt + '</div>',
                iconSize: [38, 38],
                iconAnchor: [19, 19]
            }});

            var popupContent = `
                <div class="popup-container">
                    <div class="popup-title">${{p.nome}}</div>
                    <a href="https://www.google.com/maps/dir/?api=1&destination=${{p.lat}},${{p.lng}}" target="_blank" class="btn btn-gps">🚀 GPS</a>
                    <a href="#" onclick="window.parent.location.search='?action=done&id=${{encodeURIComponent(p.id)}}'; return false;" class="btn btn-done">✅ FEITO</a>
                    <a href="#" onclick="window.parent.location.search='?action=delete&id=${{encodeURIComponent(p.id)}}'; return false;" class="btn btn-del">🗑️ EXCLUIR</a>
                </div>
            `;

            L.marker([p.lat, p.lng], {{ icon: icon }})
                .addTo(map)
                .bindPopup(popupContent);
        }});

        function onLocationFound(e) {{
            if (!userMarker) {{
                userMarker = L.circleMarker(e.latlng, {{
                    radius: 9,
                    fillColor: "#4285F4",
                    color: "white",
                    weight: 3,
                    opacity: 1,
                    fillOpacity: 1
                }}).addTo(map);
            }} else {{
                userMarker.setLatLng(e.latlng);
            }}
        }}

        map.on('locationfound', onLocationFound);
        map.locate({{
            watch: true,
            enableHighAccuracy: true,
            setView: false
        }});
    </script>
</body>
</html>
"""

st.components.v1.html(mapa_html, height=600, scrolling=False)


# =================================================================
# 10. SUGESTÃO DO PRÓXIMO PONTO
# =================================================================
if pendentes:
    p_atual = next((p for p in pontos_para_o_mapa if p["id"] == proximo_id), pendentes[0])
    st.info(f"💡 Sugestão: **{p_atual['nome']}**")
else:
    st.success("✅ Todos os pontos da lista foram concluídos.")
