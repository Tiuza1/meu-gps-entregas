import streamlit as st
import json

# 1. CONFIGURAÇÃO BÁSICA
st.set_page_config(page_title="GPS Multi-Pacotes", layout="wide", initial_sidebar_state="collapsed")

# Substitua pela sua chave real
API_KEY = 'AIzaSyCjmSTqrG7vnAkLiXVflhBffpuk_DwBWSY' 

# CSS para esconder o menu do Streamlit e focar no mapa
st.markdown("""
    <style>
    [data-testid="stHeader"], [data-testid="stToolbar"], footer {display: none !important;}
    .block-container {padding: 0 !important;}
    iframe {border: none;}
    </style>
""", unsafe_allow_html=True)

# 2. CARREGAR DADOS DO SEU JSON
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

# 3. O MAPA (GOOGLE MAPS JAVASCRIPT API)
# Este código roda 100% no navegador, por isso é liso.
mapa_html = f"""
<!DOCTYPE html>
<html>
<head>
    <script src="https://maps.googleapis.com/maps/api/js?key={API_KEY}"></script>
    <style>
        #map {{ height: 100vh; width: 100%; }}
        body {{ margin: 0; padding: 0; }}
        #info-box {{
            position: absolute; top: 10px; right: 10px;
            background: rgba(0,0,0,0.8); color: white;
            padding: 10px; border-radius: 5px; z-index: 1000;
            font-family: sans-serif; font-size: 12px;
        }}
    </style>
</head>
<body>
    <div id="info-box"><b>MODO TESTE:</b><br>Clique no mapa para mover a bolinha azul.</div>
    <div id="map"></div>

    <script>
        let map;
        let userMarker;
        const pontos = {json.dumps(banco_total)};

        function initMap() {{
            // Inicia o mapa centralizado em Luziânia
            map = new google.maps.Map(document.getElementById("map"), {{
                zoom: 16,
                center: {{ lat: -16.25, lng: -47.95 }},
                mapTypeId: 'roadmap',
                gestureHandling: "greedy",
                disableDefaultUI: false
            }});

            // DESENHA AS QUADRAS (Bolinhas Vermelhas)
            pontos.forEach(p => {{
                new google.maps.Marker({{
                    position: {{ lat: p.lat, lng: p.lng }},
                    map: map,
                    icon: {{
                        path: google.maps.SymbolPath.CIRCLE,
                        fillColor: '#dc3545',
                        fillOpacity: 1,
                        strokeColor: 'white',
                        strokeWeight: 1,
                        scale: 8
                    }}
                }});
            }});

            // FUNÇÃO PARA ATUALIZAR A BOLINHA AZUL (GPS)
            function atualizarGPS(pos) {{
                if (!userMarker) {{
                    userMarker = new google.maps.Marker({{
                        position: pos,
                        map: map,
                        title: "Sua localização",
                        icon: {{
                            path: google.maps.SymbolPath.CIRCLE,
                            fillColor: '#4285F4',
                            fillOpacity: 1,
                            strokeColor: 'white',
                            strokeWeight: 2,
                            scale: 10
                        }}
                    }});
                }} else {{
                    userMarker.setPosition(pos); // Move a bolinha de forma lisa
                }}
            }}

            // TESTE: Clique no mapa e a bolinha azul vai para lá
            map.addListener("click", (e) => {{
                atualizarGPS(e.latLng);
            }});

            // GPS REAL: Ativa o rastreamento real se o navegador permitir
            if (navigator.geolocation) {{
                navigator.geolocation.watchPosition(
                    (p) => {{
                        atualizarGPS({{ lat: p.coords.latitude, lng: p.coords.longitude }});
                    }},
                    (err) => console.log("GPS Real aguardando clique ou sinal..."),
                    {{ enableHighAccuracy: true, maximumAge: 0 }}
                );
            }}
        }}
        initMap();
    </script>
</body>
</html>
"""

# Renderiza o mapa ocupando a tela
st.components.v1.html(mapa_html, height=800)
