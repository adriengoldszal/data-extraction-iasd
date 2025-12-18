import json
import math
from pathlib import Path

import matplotlib.pyplot as plt

INPUT_PATH = Path("../data/places_with_dist.geojson")
GEOCODED_PATH = Path("../data/geocoded_locations.json")
OUTPUT_DIR = Path(__file__).parent  # Save images in the same folder as this script

def load_all_locations(path: Path):
    """Load all locations and categorize by verification status."""
    geo = json.loads(path.read_text(encoding="utf-8"))
    
    verified = []      # Successfully verified with Wikipedia
    failed = []        # Failed to verify (wiki_error)
    
    for feat in geo.get("features", []):
        props = feat.get("properties", {})
        place = props.get("place") or "unknown"
        
        if props.get("distance_m") is not None:
            try:
                d = float(props["distance_m"]) / 1000  # Convert to km
                verified.append((place, d))
            except:
                failed.append((place, props.get("wiki_error", "parse_error")))
        elif props.get("wiki_error"):
            failed.append((place, props["wiki_error"]))
        else:
            failed.append((place, "no_data"))
    
    return verified, failed

verified, failed = load_all_locations(INPUT_PATH)
rows = verified  # For backward compatibility with chart code

if not verified:
    raise SystemExit("No verified locations found. Did you run verify_locations.py first?")

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

print("\n All charts saved!")

# ============================================================
# TABLE 0: Full pipeline coverage
# ============================================================
print("\n" + "=" * 60)
print("GEOCODING PIPELINE COVERAGE")
print("=" * 60)

# Load original geocoded locations to see Nominatim failures
nominatim_success = 0
nominatim_failed = []
if GEOCODED_PATH.exists():
    geocoded_data = json.loads(GEOCODED_PATH.read_text(encoding="utf-8"))
    total_original = len(geocoded_data)
    for place, data in geocoded_data.items():
        if data.get("latitude") is not None:
            nominatim_success += 1
        else:
            nominatim_failed.append(place)
    
    print(f"\n{'Stage':<35} {'Count':<10} {'Rate':<12}")
    print("-" * 60)
    print(f"{'1. Original locations':<35} {total_original:<10}")
    print(f"{'2. Nominatim geocoded':<35} {nominatim_success:<10} {(nominatim_success/total_original)*100:>6.1f}%")
    print(f"{'   - Failed (null coordinates)':<35} {len(nominatim_failed):<10} {(len(nominatim_failed)/total_original)*100:>6.1f}%")
    print(f"{'3. Wikipedia verified':<35} {len(verified):<10} {(len(verified)/total_original)*100:>6.1f}%")
    print(f"{'   - Failed verification':<35} {len(failed):<10} {(len(failed)/total_original)*100:>6.1f}%")
    
    if nominatim_failed:
        print(f"\nLocations Nominatim couldn't geocode ({len(nominatim_failed)}):")
        for place in nominatim_failed[:10]:
            place_short = place[:50] + ".." if len(place) > 52 else place
            print(f"  - {place_short}")
        if len(nominatim_failed) > 10:
            print(f"  ... and {len(nominatim_failed) - 10} more")
else:
    print("(geocoded_locations.json not found - showing only Wikipedia verification)")

# ============================================================
# TABLE 1: Wikipedia verification details
# ============================================================
print("\n" + "=" * 60)
print("WIKIPEDIA VERIFICATION DETAILS")
print("=" * 60)

total_in_geojson = len(verified) + len(failed)
verified_count = len(verified)
failed_count = len(failed)

print(f"\n{'Status':<25} {'Count':<10} {'Percentage':<12}")
print("-" * 50)
print(f"{'Verified (Wikipedia)':<25} {verified_count:<10} {(verified_count/total_in_geojson)*100:>6.1f}%")
print(f"{'Failed verification':<25} {failed_count:<10} {(failed_count/total_in_geojson)*100:>6.1f}%")
print("-" * 50)
print(f"{'Total in GeoJSON':<25} {total_in_geojson:<10} {'100.0%':>7}")

if failed:
    # Group failures by error type
    error_types = {}
    for place, error in failed:
        error_types[error] = error_types.get(error, 0) + 1
    
    print(f"\nWikipedia failure breakdown:")
    for error, count in sorted(error_types.items(), key=lambda x: -x[1]):
        print(f"  - {error}: {count} ({(count/failed_count)*100:.1f}%)")
    
    print(f"\nLocations Wikipedia couldn't verify:")
    for place, error in failed[:10]:  # Show first 10
        place_short = place[:35] + ".." if len(place) > 37 else place
        print(f"  - {place_short:<40} [{error}]")
    if len(failed) > 10:
        print(f"  ... and {len(failed) - 10} more")

# ============================================================
# TABLE 1: Distance threshold statistics
# ============================================================
print("\n" + "=" * 60)
print("ACCURACY BY DISTANCE THRESHOLD")
print("=" * 60)

total = len(dists)
thresholds = [1, 5, 10, 25, 50, 100, 500, 1000]

print(f"\n{'Threshold':<15} {'Count':<10} {'Percentage':<12} {'Cumulative':<12}")
print("-" * 50)

cumulative = 0
for threshold in thresholds:
    count = sum(1 for d in dists if d <= threshold)
    pct = (count / total) * 100
    cumulative = pct
    print(f"≤ {threshold:>6} km     {count:<10} {pct:>6.1f}%      {cumulative:>6.1f}%")

# Also show how many are above the max threshold
above_max = sum(1 for d in dists if d > thresholds[-1])
if above_max > 0:
    print(f"> {thresholds[-1]:>6} km     {above_max:<10} {(above_max/total)*100:>6.1f}%")

print(f"\nTotal locations: {total}")
print(f"Mean distance: {sum(dists)/total:.1f} km")
print(f"Median distance: {sorted(dists)[total//2]:.1f} km")

# ============================================================
# TABLE 2: Top 10 errors
# ============================================================
print("\n" + "=" * 60)
print("TOP 10 LARGEST GEOCODING ERRORS")
print("=" * 60)

top10 = sorted(rows, key=lambda x: x[1], reverse=True)[:10]

print(f"\n{'Rank':<6} {'Location':<40} {'Error (km)':<12}")
print("-" * 60)
for i, (place, dist) in enumerate(top10, 1):
    # Truncate long place names
    place_short = place[:38] + ".." if len(place) > 40 else place
    print(f"{i:<6} {place_short:<40} {dist:>8.1f} km")
