import json
import math
from pathlib import Path

import matplotlib.pyplot as plt

INPUT_PATH = Path("places_with_dist.geojson")

def load_distances(path: Path):
    geo = json.loads(path.read_text(encoding="utf-8"))
    rows = []
    for feat in geo.get("features", []):
        props = feat.get("properties", {})
        d = props.get("distance_m")
        if d is None:
            continue
        try:
            d = float(d)
        except Exception:
            continue
        label = props.get("place") or props.get("wiki_page") or "unknown"
        rows.append((label, d))
    return rows

rows = load_distances(INPUT_PATH)
if not rows:
    raise SystemExit("No distance_m found. Did you run the enrichment script first?")

labels, dists = zip(*rows)

# 1) Histogram (meters)
plt.figure()
plt.hist(dists, bins=30)
plt.xlabel("Distance (meters)")
plt.ylabel("Count")
plt.title("Distance distribution (Nominatim vs Wikipedia)")
plt.tight_layout()
plt.show()

# 2) Histogram (log10 meters) — helpful if you have huge outliers
logd = [math.log10(d) for d in dists if d > 0]
plt.figure()
plt.hist(logd, bins=30)
plt.xlabel("log10(distance in meters)")
plt.ylabel("Count")
plt.title("Distance distribution (log scale)")
plt.tight_layout()
plt.show()

# 3) Top 15 outliers bar chart
top = sorted(rows, key=lambda x: x[1], reverse=True)[:15]
top_labels = [t[0] for t in top][::-1]
top_dists = [t[1] for t in top][::-1]

plt.figure()
plt.barh(top_labels, top_dists)
plt.xlabel("Distance (meters)")
plt.title("Top 15 largest distances")
plt.tight_layout()
plt.show()
