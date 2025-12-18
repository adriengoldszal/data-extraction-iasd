"""Minimal wine map viewer with Folium."""
import folium
from folium.plugins import MarkerCluster
import json
import webbrowser

# Country colors
COLORS = {
    'France': 'blue', 'Italie': 'green', 'Espagne': 'orange',
    'Portugal': 'red', 'États-Unis': 'purple', 'Argentine': 'pink',
    'Allemagne': 'gray', 'Australie': 'beige', 'Afrique du Sud': 'black',
}

# Load GeoJSON
with open('../data/wines_map.geojson') as f:
    data = json.load(f)

# Create map
m = folium.Map(location=[46, 2], zoom_start=4, tiles='CartoDB positron')
cluster = MarkerCluster().add_to(m)

# Add markers
for feature in data['features']:
    coords = feature['geometry']['coordinates']
    props = feature['properties']
    country = props.get('country', '')
    color = COLORS.get(country, 'gray')
    
    # Build popup with wine list
    wines = props.get('wines', '').split('; ')[:5]  # Show max 5 wines
    wine_list = '<br>'.join(f"• {w}" for w in wines if w)
    popup_html = f"""
    <div style="width:250px">
        <h4 style="margin:0;color:#722F37">🍷 {props['place']}</h4>
        <p><b>{props['wine_count']}</b> wines from <b>{country}</b></p>
        <hr style="margin:5px 0">
        <small>{wine_list}</small>
    </div>
    """
    
    folium.Marker(
        location=[coords[1], coords[0]],
        popup=folium.Popup(popup_html, max_width=300),
        icon=folium.Icon(color=color, icon='glass', prefix='fa'),
    ).add_to(cluster)

# Save and open
m.save('wines_map.html')
webbrowser.open('wines_map.html')
print(" Map saved to wines_map.html and opened in browser!")