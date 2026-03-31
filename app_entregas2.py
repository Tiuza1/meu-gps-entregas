import json
import googlemaps
import streamlit as st
import folium
from streamlit_folium import st_folium
from folium.plugins import LocateControl
import math
import re
import os
from datetime import datetime

# =================================================================
# 1. CONFIGURAÇÃO DA CHAVE API
# =================================================================
API_KEY = 'AIzaSyCjmSTqrG7vnAkLiXVflhBffpuk_DwBWSY' 
try:
    gmaps = googlemaps.Client(key=API_KEY)
except:
    st.error("Chave de API inválida.")

# =================================================================
# 2. CSS ANTI-BUG E INTERFACE (MOBILE FIRST)
# =================================================================
st.set_page_config(page_title="GPQuadras Pro", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    [data-testid="stHeader"] { background-color: transparent !important; }
    [data-testid="stToolbar"] { display: none !important; }
    footer { display: none !important; }
    .stApp { background-color: #f0f2f6 !important; }
    .block-container { padding: 3rem 0.5rem 0.5rem 0.5rem !important; max-width: 100% !important; }
    div[data-baseweb="select"] [role="option"]:first-child { display: none !important; }
    .stSelectbox label { display: none !important; }
    .stButton>button {
        width: 100% !important; height: 55px !important; font-size: 16px !important; 
        font-weight: bold !important; border-radius: 12px !important;
    }
    .stDownloadButton>button {
        background-color: #28a745 !important; color: white !important;
        width: 100% !important; height: 55px !important; border-radius: 12px !important;
    }
    </style>
""", unsafe_allow_html=True)

# =================================================================
# 3. MEMÓRIA DO SISTEMA (AUTO-SAVE)
# =================================================================
FILE_SAVE = "progresso_final.json"

if 'lista_pacotes' not in st.session_state: st.session_state.lista_pacotes = []
if 'entregues_id' not in st.session_state: st.session_state.entregues_id = []
if 'ultima_pos' not in st.session_state: st.session_state.ultima_pos = None
if 'ponto_clicado' not in st.session_state: st.session_state.ponto_clicado = None
if 'pontos_extras' not in st.session_state: st.session_state.pontos_extras = {}

def salvar_progresso():
    dados = {
        "lista_pacotes": st.session_state.lista_pacotes,
        "entregues_id": st.session_state.entregues_id,
        "ultima_pos": st.session_state.ultima_pos,
        "pontos_extras": st.session_state.pontos_extras
    }
    with open(FILE_SAVE, "w") as f: json.dump(dados, f)

if not st.session_state.lista_pacotes:
    if os.path.exists(FILE_SAVE):
        try:
            with open(FILE_SAVE, "r") as f:
                d = json.load(f)
                st.session_state.lista_pacotes = d.get("lista_pacotes", [])
                st.session_state.entregues_id = d.get("entregues_id", [])
                st.session_state.ultima_pos = tuple(d["ultima_pos"]) if d.get("ultima_pos") else None
                st.session_state.pontos_extras = d.get("pontos_extras", {})
        except: pass

@st.cache_data
def carregar_banco():
    try:
        with open('Lugares marcados.json', 'r', encoding='utf-8') as f:
            dados_j = json.load(f)
        return {str(l['properties'].get('title') or l['properties'].get('name')).strip(): 
                (l['geometry']['coordinates'][1], l['geometry']['coordinates'][0]) 
                for l in dados_j.get('features',[])}
    except: return {}

banco_total = carregar_banco()

# =================================================================
# 4. MENU LATERAL E BUSCA
# =================================================================
with st.sidebar:
    st.title("⚙️ Configurações")
    base_input = st.text_input("📍 Início da Rota:", "Luziânia, GO")
    if st.button("🗺️ DEFINIR INÍCIO"):
        geo = gmaps.geocode(base_input)
        if geo:
            st.session_state.ultima_pos = (geo[0]['geometry']['location']['lat'], geo[0]['geometry']['location']['lng'])
            salvar_progresso()
            st.rerun()

    if st.button("🗑️ ZERAR TUDO"):
        if os.path.exists(FILE_SAVE): os.remove(FILE_SAVE)
        st.session_state.lista_pacotes = []; st.session_state.entregues_id = []
        st.session_state.pontos_extras = {}; st.session_state.ponto_clicado = None
        st.rerun()

    if st.session_state.entregues_id:
        st.markdown("---")
        data_h = datetime.now().strftime("%d/%m/%Y")
        resumo = f"RELATÓRIO: {data_h}\nPacotes Entregues: {len(st.session_state.entregues_id)}\n\n"
        st.download_button("📥 BAIXAR RELATÓRIO", data=resumo, file_name=f"entregas_{data_h}.txt")

c1, c2 = st.columns([4, 1])
with c1:
    busca = st.selectbox("Busca", options=["(Adicionar Quadra...)"] + list(banco_total.keys()), label_visibility="collapsed")
with c2:
    if st.button("➕"):
        if busca and busca != "(Adicionar Quadra...)":
            novo_id = f"{busca}_{len(st.session_state.lista_pacotes)}"
            st.session_state.lista_pacotes.append({"id": novo_id, "nome": busca})
            st.session_state.ultima_pos = banco_total[busca]
            st.session_state.forcar_centro = banco_total[busca]
            st.session_state.forcar_zoom = 16
            salvar_progresso(); st.rerun()

# =================================================================
# 5. LÓGICA DE AGRUPAMENTO E SUGESTÃO
# =================================================================
quadras_agrupadas = {}
for p in st.session_state.lista_pacotes:
    n = p['nome']
    if n not in quadras_agrupadas:
        coords = banco_total.get(n) or st.session_state.pontos_extras.get(n)
        quadras_agrupadas[n] = {"coords": coords, "pacotes": []}
    quadras_agrupadas[n]['pacotes'].append(p['id'])

proximo_ideal = None
pendentes = [n for n, d in quadras_agrupadas.items() if not all(pid in st.session_state.entregues_id for pid in d['pacotes'])]
if st.session_state.ultima_pos and pendentes:
    menor_dist = float('inf')
    for n in pendentes:
        c = quadras_agrupadas[n]['coords']
        dist = math.sqrt((st.session_state.ultima_pos[0]-c[0])**2 + (st.session_state.ultima_pos[1]-c[1])**2)
        if dist < menor_dist: menor_dist = dist; proximo_ideal = n

# =================================================================
# 6. MAPA (GOOGLE LIMPO + ALFINETE + GPS ALTO)
# =================================================================
centro = st.session_state.ultima_pos if st.session_state.ultima_pos else [-16.15, -47.96]

m = folium.Map(
    location=centro, zoom_start=16, zoom_control=False,
    tiles="https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}&apistyle=s.t:3|p.v:off,s.t:1|p.v:on",
    attr="Google Maps Limpo"
)

m.get_root().html.add_child(folium.Element("""
<style>
.leaflet-bottom.leaflet-left { margin-bottom: 160px !important; }
path.leaflet-interactive { transition: d 0.8s linear !important; }
</style>
"""))

LocateControl(
    position='bottomleft', fly_to=True, 
    locate_options={"enableHighAccuracy": True, "maximumAge": 500, "watch": True, "maxZoom": 16}
).add_to(m)

for nome, info in quadras_agrupadas.items():
    t_p = len(info['pacotes']); f_p = sum(1 for pid in info['pacotes'] if pid in st.session_state.entregues_id)
    concluido = (f_p == t_p); num = re.findall(r'\d+', nome)[0] if re.findall(r'\d+', nome) else nome[:2]
    cor = "#28a745" if concluido else ("#fd7e14" if nome == proximo_ideal else "#dc3545")
    borda = "4px solid #007bff" if (t_p > 1 and not concluido) else "2px solid white"
    txt = "✔" if concluido else (f"{num}<br><small>x{t_p}</small>" if t_p > 1 else num)
    icon_html = f"""<div style="background-color:{cor}; width:40px; height:40px; border-radius:50%; display:flex; 
                    flex-direction:column; align-items:center; justify-content:center; color:white; font-weight:bold; 
                    border:{borda}; box-shadow: 2px 2px 8px rgba(0,0,0,0.3); opacity:{'0.5' if concluido else '1.0'}; line-height:1;">{txt}</div>"""
    folium.Marker(location=info['coords'], popup=nome, icon=folium.DivIcon(html=icon_html)).add_to(m)

f_center = st.session_state.pop("forcar_centro", None)
f_zoom = st.session_state.pop("forcar_zoom", None)
map_data = st_folium(m, use_container_width=True, height=650, key="mapa_full", 
                     returned_objects=["last_object_clicked_popup", "last_clicked"], center=f_center, zoom=f_zoom)

# Lógica de Clique no Mapa (Novo Alfinete)
if map_data.get("last_clicked"):
    coords_clicadas = (map_data["last_clicked"]["lat"], map_data["last_clicked"]["lng"])
    st.subheader("📍 Novo Alfinete")
    novo_n = st.text_input("Número/Nome da Quadra:", key="input_novo")
    if st.button("➕ SALVAR QUADRA"):
        st.session_state.pontos_extras[novo_n] = coords_clicadas
        novo_id = f"{novo_n}_{len(st.session_state.lista_pacotes)}"
        st.session_state.lista_pacotes.append({"id": novo_id, "nome": novo_n})
        salvar_progresso(); st.rerun()

# Lógica de Clique no Marcador (Painel de Ação)
if map_data.get("last_object_clicked_popup"):
    nome_sel = map_data["last_object_clicked_popup"]
    if nome_sel in quadras_agrupadas:
        info_q = quadras_agrupadas[nome_sel]
        f_p = sum(1 for pid in info_q['pacotes'] if pid in st.session_state.entregues_id)
        st.info(f"**📍 {nome_sel}** ({f_p}/{len(info_q['pacotes'])} pacotes)")
        c_gps, c_done = st.columns(2)
        with c_gps:
            st.link_button("🚀 GPS", f"https://www.google.com/maps/dir/?api=1&destination={info_q['coords'][0]},{info_q['coords'][1]}")
        with c_done:
            id_p = next((pid for pid in info_q['pacotes'] if pid not in st.session_state.entregues_id), None)
            if id_p:
                if st.button("✅ FEITO"):
                    st.session_state.entregues_id.append(id_p)
                    st.session_state.ultima_pos = info_q['coords']
                    salvar_progresso(); st.rerun()
