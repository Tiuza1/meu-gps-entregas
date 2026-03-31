import streamlit as st
import json
import os

# CONFIGURAÇÃO
st.set_page_config(page_title="GPS Profissional", layout="wide")
API_KEY = 'AIzaSyCjmSTqrG7vnAkLiXVflhBffpuk_DwBWSY' # Use a mesma chave que já tem

# CSS para esconder o menu do Streamlit e focar no mapa
st.markdown("""
    <style>
    [data-testid="stHeader"], footer {display: none !important;}
    .block-container {padding: 0 !important;}
    iframe {border: none;}
    </style>
""", unsafe_allow_html=True)

# CARREGAR DADOS DAS QUADRAS
def carregar_pontos():
    try:
        with open('Lugares marcados.json', 'r', encoding='utf-8') as f:
            dados = json.load(f)
        pontos = []
        for feat in dados.get('features', []):
            pontos.append({
                "nome": feat['properties'].get('title') or feat['properties'].get('name'),
                "lat": feat['geometry']['coordinates'][1],
                "lng": feat['geometry']['coordinates'][0]
            })
        return pontos
    except: return []

pontos_quadras = carregar_pontos()

# HTML + JAVASCRIPT (O segredo da bolinha lisa)
# Esse código roda 100% no navegador do celular, sem travar
mapa_html = f"""
<!DOCTYPE html>
<html>
<head>
    <script src="https://maps.googleapis.com/maps/api/js?key={API_KEY}&libraries=geometry"></script>
    <style>
        #map {{ height: 100vh; width: 100%; }}
        body {{ margin: 0; padding: 0; }}
    </style>
</head>
<body>
    <div id="map"></div>
    <script>
        let map;
        let userMarker;
        const quadras = {json.dumps(pontos_quadras)};

        function initMap() {{
            // Inicia o mapa (Visão de cima)
            map = new google.maps.Map(document.getElementById("map"), {{
                zoom: 16,
                center: {{ lat: -16.15, lng: -47.96 }},
                mapTypeId: 'roadmap',
                disableDefaultUI: false,
                zoomControl: true,
                gestureHandling: "greedy"
            }});

            // Desenha suas bolinhas (Quadras)
            quadras.forEach(q => {{
                new google.maps.Marker({{
                    position: {{ lat: q.lat, lng: q.lng }},
                    map: map,
                    title: q.nome,
                    icon: {{
                        path: google.maps.SymbolPath.CIRCLE,
                        fillColor: '#dc3545',
                        fillOpacity: 0.9,
                        strokeColor: '#fff',
                        strokeWeight: 2,
                        scale: 10
                    }}
                }});
            }});

            // ATIVA O GPS REAL (O que roda liso)
            if (navigator.geolocation) {{
                navigator.geolocation.watchPosition(
                    (position) => {{
                        const pos = {{
                            lat: position.coords.latitude,
                            lng: position.coords.longitude
                        }};
                        
                        if (!userMarker) {{
                            // Cria a bolinha azul estilo Google Maps
                            userMarker = new google.maps.Marker({{
                                position: pos,
                                map: map,
                                icon: {{
                                    path: google.maps.SymbolPath.CIRCLE,
                                    fillColor: '#4285F4',
                                    fillOpacity: 1,
                                    strokeColor: 'white',
                                    strokeWeight: 2,
                                    scale: 8
                                }}
                            }});
                        }} else {{
                            userMarker.setPosition(pos);
                        }}
                    }},
                    () => {{ console.log("Erro no GPS"); }},
                    {{ enableHighAccuracy: true, maximumAge: 0 }}
                );
            }}
        }}
        initMap();
    </script>
</body>
</html>
"""

# Renderiza o mapa ocupando a tela toda
st.components.v1.html(mapa_html, height=800)
