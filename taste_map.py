"""
Wine taste geography map (Europe)
Single HTML with switchable taste layers (only one active at a time)
"""
import json
import folium
import branca.colormap as cm

# ----------------------------
# Files
# ----------------------------
WINES_FILE = "data/vivino_wines_complete_details_final_no_duplicates.json"
LOCATIONS_FILE = "data/geocoded_locations.json"
OUTPUT_FILE = "wine_taste_map.html"

# ----------------------------
# Map config
# ----------------------------
EUROPE_CENTER = [45, 5]
ZOOM_START = 5
TASTE_DIMENSIONS = {
    "light_bold": {
        "label": "Light → Bold",
        "colors": ["#f7fcf5", "#00441b"],
    },
    "smooth_tannic": {
        "label": "Smooth → Tannic",
        "colors": ["#fff5eb", "#7f2704"],
    },
    "dry_sweet": {
        "label": "Dry → Sweet",
        "colors": ["#f7fbff", "#08306b"],
    },
    "soft_acidic": {
        "label": "Soft → Acidic",
        "colors": ["#fff7ec", "#7f0000"],
    },
}

# ----------------------------
# Load data
# ----------------------------
with open(WINES_FILE, encoding="utf-8") as f:
    wines = json.load(f)["wines"]
with open(LOCATIONS_FILE, encoding="utf-8") as f:
    locations = json.load(f)

# ----------------------------
# Join wines with coordinates
# ----------------------------
enriched = []
for w in wines:
    loc = locations.get(w.get("place"))
    if not loc:
        continue
    lat = loc.get("latitude")
    lon = loc.get("longitude")
    if lat is None or lon is None:
        continue
    w["lat"] = lat
    w["lon"] = lon
    enriched.append(w)

# ----------------------------
# Base map
# ----------------------------
m = folium.Map(
    location=EUROPE_CENTER,
    zoom_start=ZOOM_START,
    tiles="CartoDB positron",
    control_scale=True,
)

# ----------------------------
# Taste layers (only first one shown initially)
# ----------------------------
colormaps = {}
colormap_ids = {}
layer_names = []

for idx, (taste, cfg) in enumerate(TASTE_DIMENSIONS.items()):
    # Only show the first layer by default, keep as overlay
    layer = folium.FeatureGroup(name=cfg["label"], show=(idx == 0))
    layer_names.append(cfg["label"])
    
    colormap = cm.LinearColormap(
        cfg["colors"],
        vmin=0,
        vmax=100,
        caption=cfg["label"],
    )
    colormaps[taste] = colormap
    
    for w in enriched:
        tc = w["taste_characteristics"].get(taste)
        if not tc:
            continue
        value = tc["percentage"]/0.85
        folium.CircleMarker(
            location=[w["lat"], w["lon"]],
            radius=6,
            color=colormap(value),
            fill=True,
            fill_opacity=0.75,
            popup=(
                f"<b>{w['name']}</b><br>"
                f"{w['place']}<br>"
                f"{cfg['label']}: {value:.1f}%"
            ),
        ).add_to(layer)
    
    layer.add_to(m)

# ----------------------------
# Custom layer control (overlays only, no base layers)
# ----------------------------
# Create a custom control that only shows overlay layers
custom_control_html = """
<style>
.custom-layer-control {
    position: absolute;
    top: 10px;
    right: 10px;
    background: white;
    padding: 10px;
    border-radius: 5px;
    box-shadow: 0 2px 6px rgba(0,0,0,0.3);
    z-index: 1000;
}
.custom-layer-control label {
    display: block;
    margin: 5px 0;
    cursor: pointer;
}
</style>
"""

m.get_root().html.add_child(folium.Element(custom_control_html))

# Add LayerControl but hide the base layers section with CSS
folium.LayerControl(collapsed=False).add_to(m)

# Add CSS to hide the base layers section
hide_base_layers_css = """
<style>
.leaflet-control-layers-base {
    display: none !important;
}
.leaflet-control-layers-separator {
    display: none !important;
}
</style>
"""

m.get_root().html.add_child(folium.Element(hide_base_layers_css))

# Add all colormaps with unique IDs in a fixed position container
colormap_container = """
<div id="colormap-container" style="
    position: fixed;
    bottom: 30px;
    right: 30px;
    z-index: 9999;
    background: white;
    padding: 10px;
    border-radius: 5px;
    box-shadow: 0 2px 6px rgba(0,0,0,0.3);
">
"""

for idx, (taste, cm_) in enumerate(colormaps.items()):
    # Add a unique ID to each colormap
    colormap_id = f"colormap_{taste}"
    colormap_ids[taste] = colormap_id
    
    # Add the colormap to the container
    colormap_container += f'<div id="{colormap_id}" style="display: {"block" if idx == 0 else "none"};">{cm_._repr_html_()}</div>'

colormap_container += "</div>"

m.get_root().html.add_child(folium.Element(colormap_container))

# ----------------------------
# Add custom JavaScript to make layers mutually exclusive and toggle colormaps
# ----------------------------
colormap_mapping = {cfg["label"]: colormap_ids[taste] for taste, cfg in TASTE_DIMENSIONS.items()}
colormap_mapping_json = json.dumps(colormap_mapping)

js_code = f"""
<script>
var colormapMapping = {colormap_mapping_json};

document.addEventListener('DOMContentLoaded', function() {{
    // Wait for map to be ready
    setTimeout(function() {{
        var checkboxes = document.querySelectorAll('.leaflet-control-layers-overlays input[type="checkbox"]');
        
        checkboxes.forEach(function(checkbox) {{
            checkbox.addEventListener('change', function() {{
                var label = this.nextSibling.textContent.trim();
                
                if (this.checked) {{
                    // Uncheck all other checkboxes
                    checkboxes.forEach(function(other) {{
                        if (other !== checkbox && other.checked) {{
                            other.click();
                        }}
                    }});
                    
                    // Hide all colormaps
                    Object.values(colormapMapping).forEach(function(id) {{
                        var elem = document.getElementById(id);
                        if (elem) elem.style.display = 'none';
                    }});
                    
                    // Show the colormap for this layer
                    var colormapId = colormapMapping[label];
                    if (colormapId) {{
                        var elem = document.getElementById(colormapId);
                        if (elem) elem.style.display = 'block';
                    }}
                }} else {{
                    // If unchecking, hide its colormap
                    var colormapId = colormapMapping[label];
                    if (colormapId) {{
                        var elem = document.getElementById(colormapId);
                        if (elem) elem.style.display = 'none';
                    }}
                }}
            }});
        }});
    }}, 500);
}});
</script>
"""

# Add the custom JavaScript
m.get_root().html.add_child(folium.Element(js_code))

# ----------------------------
# Save
# ----------------------------
m.save(OUTPUT_FILE)
print(f"Saved {OUTPUT_FILE}")