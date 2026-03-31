import streamlit as st
import json

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="GPS Profissional", layout="wide", initial_sidebar_state="collapsed")

# CSS para tela cheia e performance
st.markdown("""
    <style>
    [data-testid="stHeader"], [data-testid="stToolbar"], footer {display: none !important;}
    .block-container {padding: 0 !important;}
    iframe {border: none; width: 100%; height: 100vh;}
    </style>
""", unsafe_allow_html=True)

# 2. CARREGAR SEUS DADOS
def carregar_banco():
    try:
        with open('Lugares marcados.json', 'r', encoding='utf-8') as f:
            dados_j = json.load(f)
        return [{"nome": l['properties'].get('title', 'Sem nome'), 
                 "lat": l['geometry']['coordinates'][1], 
                 "lng": l['geometry']['coordinates'][0]} 
                for l in dados_j.get('features',[])]
    except: return []

banco_total = carregar_banco()

# 3. O MAPA "LISO" (SEM ERRO DE API)
# Usamos Leaflet para a lógica e o Servidor do Google para o visual
mapa_html = f"""
<!DOCTYPE html>
<html>
<head>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        #map {{ height: 100vh; width: 100%; background: #e5e3df; }}
        body {{ margin: 0; padding: 0; }}
        #info {{
            position: absolute; top: 10px; right: 10px; z-index: 1000;
            background: white; padding: 10px; border-radius: 8px;
            font-family: Arial; box-shadow: 0 2px 5px rgba(0,0,0,0.3);
        }}
    </style>
</head>
<body>
    <div id="info"><b>MODO GPS LISO</b><br>Clique no mapa para simular movimento</div>
    <div id="map"></div>

    <script>
        // Inicia o mapa
        var map = L.map('map').setView([-16.25, -47.95], 16);

        // ADICIONA O VISUAL DO GOOGLE MAPS (Sem precisar de Chave de API de Mapa)
        var googleRoads = L.tileLayer('http://{{s}}.google.com/vt/lyrs=m&x={{x}}&y={{y}}&z={{z}}', {{
            maxZoom: 20,
            subdomains:['mt0','mt1','mt2','mt3']
        }}).addTo(map);

        var userMarker;
        var pontos = {json.dumps(banco_total)};

        // DESENHA SUAS QUADRAS
        pontos.forEach(function(p) {{
            L.circleMarker([p.lat, p.lng], {{
                radius: 8,
                fillColor: "#dc3545",
                color: "#fff",
                weight: 2,
                opacity: 1,
                fillOpacity: 0.9
            }}).addTo(map).bindPopup(p.nome);
        }});

        // FUNÇÃO PARA MOVER A BOLINHA AZUL (GPS)
        function atualizarGPS(lat, lng) {{
            var pos = [lat, lng];
            if (!userMarker) {{
                userMarker = L.circleMarker(pos, {{
                    radius: 10,
                    fillColor: "#4285F4",
                    color: "#fff",
                    weight: 3,
                    opacity: 1,
                    fillOpacity: 1
                }}).addTo(map);
            }} else {{
                userMarker.setLatLng(pos); // Move de forma instantânea e lisa
            }}
        }}

        // TESTE: CLIQUE PARA MOVER
        map.on('click', function(e) {{
            atualizarGPS(e.latlng.lat, e.latlng.lng);
        }});

        // GPS REAL DO CELULAR
        if (navigator.geolocation) {{
            navigator.geolocation.watchPosition(function(position) {{
                atualizarGPS(position.coords.latitude, position.coords.longitude);
            }}, function(err) {{
                console.log("Aguardando sinal ou clique...");
            }}, {{
                enableHighAccuracy: true,
                maximumAge: 0
            }});
        }}
    </script>
</body>
</html>
"""

# Renderiza
st.components.v1.html(mapa_html, height=2000) # Altura grande para garantir que cubra a tela
