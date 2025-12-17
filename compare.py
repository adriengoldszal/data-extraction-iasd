import json
import math
import re
import time
import requests

USER_AGENT = "CoordCompare/0.1 (contact: you@domain.com)"  # change this

WIKI_API = "https://en.wikipedia.org/w/api.php"


def clean_place_label(place: str) -> str:
    main = place.split(",")[0].strip()
    main = re.sub(r"\s*\(.*?\)\s*", " ", main).strip()
    return re.sub(r"\s+", " ", main)


def haversine_m(lon1, lat1, lon2, lat2):
    R = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = (math.sin(dp / 2) ** 2 +
         math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2)
    return 2 * R * math.asin(math.sqrt(a))


def get_wikipedia_coords(session, title):
    params = {
        "action": "query",
        "format": "json",
        "formatversion": 2,
        "prop": "coordinates",
        "titles": title,
        "colimit": 1,
        "coprimary": "primary",
    }
    r = session.get(WIKI_API, params=params, timeout=20)
    r.raise_for_status()
    data = r.json()

    page = data["query"]["pages"][0]
    if page.get("missing"):
        return None

    coords = page.get("coordinates")
    if not coords:
        return None

    return {
        "title": page["title"],
        "lat": coords[0]["lat"],
        "lon": coords[0]["lon"],
        "precision": coords[0].get("precision"),
    }


def main():
    input_path = "wines_map.geojson"      # your original file
    output_path = "places_with_dist.geojson"

    with open(input_path, "r", encoding="utf-8") as f:
        geo = json.load(f)

    session = requests.Session()
    session.headers.update({
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
    })

    for feature in geo["features"]:
        props = feature["properties"]
        lon, lat = feature["geometry"]["coordinates"]

        place = props.get("place")
        canonical = clean_place_label(place)

        try:
            wiki = get_wikipedia_coords(session, canonical)
            if wiki:
                dist = haversine_m(lon, lat, wiki["lon"], wiki["lat"])
                props["wiki_lat"] = wiki["lat"]
                props["wiki_lon"] = wiki["lon"]
                props["wiki_page"] = wiki["title"]
                props["distance_m"] = round(dist, 1)
            else:
                props["wiki_error"] = "no_coordinates"
        except Exception as e:
            props["wiki_error"] = str(e)

        # be polite to Wikipedia
        time.sleep(0.2)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(geo, f, ensure_ascii=False, indent=2)

    print(f"✅ Written: {output_path}")


if __name__ == "__main__":
    main()
