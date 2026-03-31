import json
import googlemaps
import streamlit as st
import folium
from streamlit_folium import st_folium
from folium.plugins import Locate "perfeita"** que discutimos, notei que faltam 3 detalhes que você tinha pedido antes e que nãoControl
import math
import re
import os
from datetime import datetime

# =================================================================
# 1. CONFIGURAÇÃO DA CHAVE API
# =================================================================
API_KEY = 'AIzaSyCjmSTqrG7vnAkLiXVflhBffpuk_DwBWSY' estão nesse bloco que você enviou:

1.  **Limpeza de Comércios:** O link do mapa (`tiles 
try:
    gmaps = googlemaps.Client(key=API_KEY)
except:
    st.error("Chave de API inválida.")

# =================================================================
# 2. CSS ANTI-BUG E POSICIONAMENTO
# =================================================================
st.set_page_config(page_title="GPS`) ainda está mostrando padarias, lojas e poluição visual.
2.  **Tocar e Marcar (Al Multi-Pacotes", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    [data-testid="stHeader"] { background-color: transparent !important; }
    [data-testid="stToolbar"] { display: none !important; }
    footer { display: none !important; }
    .stApp { background-color: #f0f2f6 !important;finete):** Esta versão só permite adicionar quadras pelo buscador de texto, não permite tocar no mapa para criar uma }
    .block-container { padding: 3rem 0.5rem 0.5rem  quadra nova.
3.  **Relatório de Download:** O botão de baixar o arquivo `.txt` não0.5rem !important; max-width: 100% !important; }
    div[data-baseweb="select"] [role="option"]:first-child { display: none !important; }
    .stSelectbox label { display: none !important; }
    .stButton>button {
 está aparecendo.

Aqui está o código **revisado, com a sua API**, o mapa **limpo (sem        width: 100% !important; height: 55px !important; font-size: 16px !important; 
        font-weight: bold !important; border-radius: 1 comércios)**, o sistema de **tocar no mapa para marcar**, o **relatório restaurado** e a2px !important;
    }
    </style>
""", unsafe_allow_html=True)

# =================================================================
# 3. MEMÓRIA DO SISTEMA
# =================================================================
FILE_SAVE = "progresso_final.json"

if 'lista_pacotes' not in st **bolinha de GPS no lugar alto** que você pediu.

### Código Completo (Versão Final Consolidada):

```python
import.session_state: st.session_state.lista_pacotes =[]
if 'entregues_ json
import googlemaps
import streamlit as st
import folium
from streamlit_folium import st_folid' not in st.session_state: st.session_state.entregues_id =[]
ium
from folium.plugins import LocateControl
import math
import re
import os
from datetime import datetimeif 'ultima_pos' not in st.session_state: st.session_state.ultima_pos = None
if 'ponto_clicado' not in st.session_state: st.session_state.

# =================================================================
# 1. CONFIGURAÇÃO DA CHAVE API
# =================================================================
ponto_clicado = None

def salvar_progresso():
    dados = {
        "lista_pacotes": st.API_KEY = 'AIzaSyCjmSTqrG7vnAkLiXVflhBffpuksession_state.lista_pacotes,
        "entregues_id": st.session_state._DwBWSY' 
try:
    gmaps = googlemaps.Client(key=API_entregues_id,
        "ultima_pos": st.session_state.ultima_pos
    KEY)
except:
    st.error("Chave de API inválida.")

# =================================================================
# }
    with open(FILE_SAVE, "w") as f: json.dump(dados, f)

if not st.session_state.lista_pacotes:
    if os.path.exists(FILE_2. CSS ANTI-BUG E INTERFACE (MOBILE FIRST)
# =================================================================
st.set_page_SAVE):
        try:
            with open(FILE_SAVE, "r") as f:
                dconfig(page_title="GPQuadras Pro", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    < = json.load(f)
                st.session_state.lista_pacotes = d["lista_style>
    [data-testid="stHeader"] { background-color: transparent !important; }
    pacotes"]
                st.session_state.entregues_id = d["entregues_id"]
                st.session_state.ultima_pos = tuple(d["ultima_pos"]) if d["[data-testid="stToolbar"] { display: none !important; }
    footer { display: none !ultima_pos"] else None
        except: pass

@st.cache_data
def carregar_bimportant; }
    .stApp { background-color: #f0f2f6 !important; }anco():
    try:
        with open('Lugares marcados.json', 'r', encoding='utf
    .block-container { padding: 3rem 0.5rem 0.5rem 0-8', errors='ignore') as f:
            dados_j = json.load(f)
        return {str(l.5rem !important; max-width: 100% !important; }
    div[data-baseweb="select['properties'].get('title') or l['properties'].get('name')).strip(): 
                (l['"] [role="option"]:first-child { display: none !important; }
    .stSelectbox labelgeometry']['coordinates'][1], l['geometry']['coordinates'][0]) 
                for l in dados_j. { display: none !important; }
    .stButton>button {
        width: 100get('features',[])}
    except: return {}

banco_total = carregar_banco()% !important; height: 55px !important; font-size: 16px !important;

# =================================================================
# 4. MENU LATERAL E BUSCA
# ================================================================= 
        font-weight: bold !important; border-radius: 12px !important;
    
with st.sidebar:
    st.title("⚙️ Configurações")
    base_input =}
    .stDownloadButton>button {
        background-color: #28a745 !important; color: st.text_input("📍 Início da Rota:", "Luziânia, GO")
    if st.button("🗺️ DEFINIR INÍCIO"):
        geo = gmaps.geocode(base_input)
        if geo:
             white !important;
        width: 100% !important; height: 55px !important; border-radius:st.session_state.ultima_pos = (geo[0]['geometry']['location']['lat'], geo[0]['geometry']['location']['lng'])
            salvar_progresso()
            st.rerun()
             12px !important;
    }
    </style>
""", unsafe_allow_html=True)

# =================================================
    st.markdown("---")
    if st.button("🗑️ ZERAR TUDO (================
# 3. MEMÓRIA DO SISTEMA (AUTO-SAVE)
# =================================================================
FILE_SAVE =Novo Dia)"):
        if os.path.exists(FILE_SAVE): os.remove(FILE_SAVE) "progresso_final.json"

if 'lista_pacotes' not in st.session_state:
        st.session_state.lista_pacotes =[]
        st.session_state.entregues_id =[]
 st.session_state.lista_pacotes = []
if 'entregues_id' not in st.session_state        st.session_state.ponto_clicado = None
        st.rerun()

c1, c2 = st.columns: st.session_state.entregues_id = []
if 'ultima_pos' not in st([4, 1])
with c1:
    busca = st.selectbox("Busca", options=["(Adicionar Quad.session_state: st.session_state.ultima_pos = None
if 'ponto_clicadora...)"] + list(banco_total.keys()), label_visibility="collapsed")
with c2:
    if st.button("➕"):
        if busca and busca != "(Adicionar Quadra...)":
' not in st.session_state: st.session_state.ponto_clicado = None

def            novo_id = f"{busca}_{len(st.session_state.lista_pacotes)}"
             salvar_progresso():
    dados = {
        "lista_pacotes": st.session_state.lista_pacotes,
        "entregues_id": st.session_state.entregues_st.session_state.lista_pacotes.append({"id": novo_id, "nome": busca})
            st.session_state.ultima_pos = banco_total[busca]
            st.session_id,
        "ultima_pos": st.session_state.ultima_pos
    }
    withstate.forcar_centro = banco_total[busca]; st.session_state.forcar_zoom = open(FILE_SAVE, "w") as f: json.dump(dados, f)

if not st 16
            salvar_progresso(); st.rerun()

# =================================================================
.session_state.lista_pacotes:
    if os.path.exists(FILE_SAVE):
# 5. PAINEL DE AÇÃO
# =================================================================
quadras_agrupadas = {}
for p in st.session_state.lista_pacotes:
    n = p['nome        try:
            with open(FILE_SAVE, "r") as f:
                d = json.load(f)
']
    if n not in quadras_agrupadas:
        quadras_agrupadas[n                st.session_state.lista_pacotes = d["lista_pacotes"]
                st.session] = {"coords": banco_total[n], "pacotes": []}
    quadras_agrup_state.entregues_id = d["entregues_id"]
                st.session_stateadas[n]['pacotes'].append(p['id'])

if st.session_state.ponto_.ultima_pos = tuple(d["ultima_pos"]) if d["ultima_pos"] else None
        clicado:
    nome_sel = st.session_state.ponto_clicado
    if nomeexcept: pass

@st.cache_data
def carregar_banco():
    try:
        _sel in quadras_agrupadas:
        info_q = quadras_agrupadas[nome_sel]
        f_p = sum(1 for pid in info_q['pacotes'] if pidwith open('Lugares marcados.json', 'r', encoding='utf-8') as f:
             in st.session_state.entregues_id)
        t_p = len(info_qdados_j = json.load(f)
        return {str(l['properties'].get('title')['pacotes'])
        st.info(f"**📍 {nome_sel}** — ({f_ or l['properties'].get('name')).strip(): 
                (l['geometry']['coordinates'][1], lp}/{t_p} pacotes)")
        c_gps, c_done, c_close = st['geometry']['coordinates'][0]) 
                for l in dados_j.get('features',[])}
.columns([2, 2, 1])
        with c_gps:
            st.link_    except: return {}

banco_total = carregar_banco()

# =================================================================button("🚀 GPS", f"https://www.google.com/maps/dir/?api=1&destination={info_q['coords'][0]},{info_q['coords'][1]}")
        with c_done:
# 4. MENU LATERAL (CONFIGURAÇÕES E RELATÓRIO)
# =================================================================
with st.
            id_p = next((pid for pid in info_q['pacotes'] if pid not in stsidebar:
    st.title("⚙️ Configurações")
    base_input = st.text_input("📍 Início da.session_state.entregues_id), None)
            if id_p:
                if st Rota:", "Luziânia, GO")
    
    if st.button("🗺️ DEFINIR IN.button("✅ FEITO"):
                    st.session_state.entregues_id.append(idÍCIO"):
        geo = gmaps.geocode(base_input)
        if geo:
            st_p)
                    st.session_state.ultima_pos = info_q['coords']
                    if.session_state.ultima_pos = (geo[0]['geometry']['location']['lat'], geo[0][' sum(1 for pid in info_q['pacotes'] if pid in st.session_state.entreggeometry']['location']['lng'])
            salvar_progresso()
            st.rerun()

    ifues_id) == t_p:
                        st.session_state.ponto_clicado = None 
                    salvar_progresso(); st.session_state.forcar_centro = info_q[' st.button("🗑️ ZERAR TUDO"):
        if os.path.exists(FILE_SAVE): os.removecoords']; st.session_state.forcar_zoom = 16; st.rerun()
        (FILE_SAVE)
        st.session_state.lista_pacotes = []; st.session_state.entregwith c_close:
            if st.button("✖️"): st.session_state.ponto_ues_id = []; st.session_state.ponto_clicado = None
        st.rerun()

    if st.session_state.entregues_id:
        st.markdown("---")clicado = None; st.rerun()

# =================================================================
# 6. MAPA (GOOGLE MAPS LIMPO + GPS MAIS ALTO)
# =================================================================
proximo_ideal = None
pendentes =[
        data_h = datetime.now().strftime("%d/%m/%Y")
        resumo = f"RELATÓRIO:n for n, d in quadras_agrupadas.items() if not all(pid in st.session_state.entregues_id for pid in d['pacotes'])]
if st.session_state. {data_h}\nPacotes Entregues: {len(st.session_state.entregues_id)}\n\n"ultima_pos and pendentes:
    menor_dist = float('inf')
    for n in pend
        st.download_button("📥 BAIXAR RELATÓRIO", data=resumo, file_name=fentes:
        c = quadras_agrupadas[n]['coords']
        dist = math.sqrt"entregas_{data_h}.txt")

# =================================================================
# 5. BAR((st.session_state.ultima_pos[0]-c[0])**2 + (st.sessionRA DE BUSCA
# =================================================================
c1, c2 = st.columns([4, 1])_state.ultima_pos[1]-c[1])**2)
        if dist < menor_dist: menor_dist = dist; proximo_ideal = n

centro = st.session_state.ultima_pos if st.session
with c1:
    busca = st.selectbox("Busca", options=["(Adicionar Quadra...)"] + list(banco_state.ultima_pos else [-16.15, -47.96]

# MAP_total.keys()), label_visibility="collapsed")
with c2:
    if st.button("➕"):
        if busca and busca != "(Adicionar Quadra...)":
            novo_id = f"{buscaA COM ESTILO QUE MANTÉM RUAS MAS TIRA ÍCONES DE COMÉRCIO (A}_{len(st.session_state.lista_pacotes)}"
            st.session_state.lista_pacotes.append({"id": novo_id, "nome": busca})
            st.session_state.justado)
m = folium.Map(
    location=centro, zoom_start=16, zoom_control=True,
    tiles="https://mt1.google.com/vt/lyrs=m&x={xultima_pos = banco_total[busca]
            st.session_state.forcar_centro = banco_total[busca];}&y={y}&z={z}&apistyle=s.t:3|p.v:off,s.t:1 st.session_state.forcar_zoom = 16
            salvar_progresso(); st.rerun()

# =|p.v:on",
    attr="Google Maps Limpo"
)

# CSS PARA SUBIR================================================================
# 6. LÓGICA DE AGRUPAMENTO E SUGESTÃO
# ================================================= O BOTÃO DO GPS E SUAVIZAR MOVIMENTO
m.get_root().html.add_child(folium================
quadras_agrupadas = {}
for p in st.session_state.lista_pacotes.Element("""
<style>
.leaflet-bottom.leaflet-left { margin-bottom: 16:
    n = p['nome']
    if n not in quadras_agrupadas:
        0px !important; }
path.leaflet-interactive { transition: d 0.8s linear !important; }
</style>
"""))

LocateControl(
    position='bottomleft', fly_toquadras_agrupadas[n] = {"coords": banco_total.get(n, (0,0)),=True, 
    locate_options={"enableHighAccuracy": True, "maximumAge": 500, "watch": True, "maxZoom": 16}
).add_to(m)

for nome, info in quadras "pacotes": []}
        # Caso o ponto tenha sido adicionado manualmente (clique no mapa)
        if n in_agrupadas.items():
    t_p = len(info['pacotes']); f_p = sum(1 for pid in info['pacotes'] if pid in st.session_state.entregues_ st.session_state.get('pontos_extras', {}):
            quadras_agrupadas[nid)
    concluido = (f_p == t_p); num = re.findall(r'\d+', nome)[0] if re.findall(r'\d+', nome) else nome[:2]
]["coords"] = st.session_state.pontos_extras[n]
    quadras_agrupadas[n]['    cor = "#28a745" if concluido else ("#fd7e14" ifpacotes'].append(p['id'])

proximo_ideal = None
pendentes = [n for n nome == proximo_ideal else "#dc3545")
    borda = "4px solid #, d in quadras_agrupadas.items() if not all(pid in st.session_state.007bff" if (t_p > 1 and not concluido) else "2px solid whiteentregues_id for pid in d['pacotes'])]
if st.session_state.ultima_pos and pendentes:
    "
    txt = "✔" if concluido else (f"{num}<br><small>x{tmenor_dist = float('inf')
    for n in pendentes:
        c = quadras__p}</small>" if t_p > 1 else num)
    icon_html = f"""<agrupadas[n]['coords']
        dist = math.sqrt((st.session_state.ultima_pos[0div style="background-color:{cor}; width:42px; height:42px; border-radius:50%; display:flex; 
                    flex-direction:column; align-items:center; justify-content:center;]-c[0])**2 + (st.session_state.ultima_pos[1]-c[1])**2)
 color:white; font-weight:bold; 
                    border:{borda}; box-shadow: 2        if dist < menor_dist: menor_dist = dist; proximo_ideal = n

# =================================================================
# px 2px 8px rgba(0,0,0,0.3); opacity:{'0.5' if concluido else '1.0'}; line-height:1;">{txt}</div>"""
    folium.Marker(location=7. MAPA (GOOGLE LIMPO + ALFINETE + GPS ALTO)
# =================================================================
centro = st.session_info['coords'], popup=nome, icon=folium.DivIcon(html=icon_html)).add_state.ultima_pos if st.session_state.ultima_pos else [-16.15, -to(m)

f_center = st.session_state.pop("forcar_centro", None)
f_zoom = st.session_state.pop("forcar_zoom", None)
map_data = st_folium(m, use_container_width=True, height=650, key="47.96]

# MAPA COM TILES DO GOOGLE SEM COMÉRCIOS (apistyle smapa_full", returned_objects=["last_object_clicked_popup"], center=f_center, zoom.t:3|p.v:off)
m = folium.Map(
    location=centro=f_zoom)

if map_data.get("last_object_clicked_popup"):
    if, zoom_start=16, zoom_control=False,
    tiles="https://mt1.google. st.session_state.ponto_clicado != map_data["last_object_clicked_popup"]:com/vt/lyrs=m&x={x}&y={y}&z={z}&apistyle
        st.session_state.ponto_clicado = map_data["last_object_clicked_=s.t:3|p.v:off,s.t:1|p.v:on",
    attr="popup"]; st.rerun()

if st.session_state.lista_pacotes and proximo_ideal and not st.session_state.ponto_clicado:
    st.info(f"💡 SugGoogle Maps Limpo"
)

# Estilos de Transição e Posição do GPS
m.getestão Próxima: **{proximo_ideal}**")
