import json
import math
from pathlib import Path

import matplotlib.pyplot as plt

INPUT_PATH = Path("../data/places_with_dist.geojson")
OUTPUT_DIR = Path(__file__).parent  # Save images in the same folder as this script

def load_distances(path: Path):
    geo = json.loads(path.read_text(encoding="utf-8"))
    rows = []
    for feat in geo.get("features", []):
        props = feat.get("properties", {})
        d = props.get("distance_m")
        if d is None:
            continue
        try:
            d = float(d) / 1000  # Convert meters to km
        except Exception:
            continue
        label = props.get("place") or props.get("wiki_page") or "unknown"
        rows.append((label, d))
    return rows

rows = load_distances(INPUT_PATH)
if not rows:
    raise SystemExit("No distance_m found. Did you run the enrichment script first?")

labels, dists = zip(*rows)

# 1) Histogram (km)
plt.figure()
plt.hist(dists, bins=30)
plt.xlabel("Distance (km)")
plt.ylabel("Count")
plt.title("Distance distribution (Nominatim vs Wikipedia)")
plt.tight_layout()
plt.savefig(OUTPUT_DIR / "distance_histogram.png", dpi=150)
plt.close()
print(f"Saved: {OUTPUT_DIR / 'distance_histogram.png'}")

# 2) Histogram (log10 km) — helpful if you have huge outliers
logd = [math.log10(d) for d in dists if d > 0]
plt.figure()
plt.hist(logd, bins=30)
plt.xlabel("log10(distance in km)")
plt.ylabel("Count")
plt.title("Distance distribution (log scale)")
plt.tight_layout()
plt.savefig(OUTPUT_DIR / "distance_histogram_log.png", dpi=150)
plt.close()
print(f"Saved: {OUTPUT_DIR / 'distance_histogram_log.png'}")

# 3) Top 15 outliers bar chart
top = sorted(rows, key=lambda x: x[1], reverse=True)[:15]
top_labels = [t[0] for t in top][::-1]
top_dists = [t[1] for t in top][::-1]

plt.figure()
plt.barh(top_labels, top_dists)
plt.xlabel("Distance (km)")
plt.title("Top 15 largest distances")
plt.tight_layout()
plt.savefig(OUTPUT_DIR / "top_outliers.png", dpi=150)
plt.close()
print(f"Saved: {OUTPUT_DIR / 'top_outliers.png'}")

print("\n✅ All charts saved!")
