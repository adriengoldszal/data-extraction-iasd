"""
Geocode wine locations using both Nominatim and Wikipedia.
Compares both sources and chooses the best coordinates.
Generates GeoJSON for mapping and quality assessment statistics.
"""

import json
import math
import re
import time
import requests
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

# Configuration
DIVERGENCE_THRESHOLD_KM = 50  # Use Wikipedia if sources diverge more than this
WIKI_API = "https://en.wikipedia.org/w/api.php"
USER_AGENT = "WineMapper/1.0"


def load_wine_data(filepath):
    """Load wine data from JSON file"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def extract_unique_locations(wines):
    """Extract unique locations from wine data"""
    locations = {}
    for wine in wines:
        place = wine.get('place', '')
        region = wine.get('region', '')
        
        if place and place not in locations:
            locations[place] = {
                'place': place,
                'region': region,
            }
    return locations


def clean_place_label(place: str) -> str:
    """Clean place name for Wikipedia search"""
    main = place.split(",")[0].strip()
    main = re.sub(r"\s*\(.*?\)\s*", " ", main).strip()
    return re.sub(r"\s+", " ", main)


def haversine_km(lon1, lat1, lon2, lat2):
    """Calculate distance between two points in kilometers"""
    R = 6371.0  # Earth radius in km
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = (math.sin(dp / 2) ** 2 +
         math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2)
    return 2 * R * math.asin(math.sqrt(a))


def get_nominatim_coords(geolocator, location_name, retry=3):
    """Get coordinates from Nominatim"""
    for attempt in range(retry):
        try:
            location = geolocator.geocode(location_name, timeout=10)
            if location:
                return location.latitude, location.longitude
            return None, None
        except (GeocoderTimedOut, GeocoderServiceError) as e:
            if attempt == retry - 1:
                return None, None
            time.sleep(2)
    return None, None


def get_wikipedia_coords(session, place):
    """Get coordinates from Wikipedia"""
    canonical = clean_place_label(place)
    try:
        params = {
            "action": "query",
            "format": "json",
            "formatversion": 2,
            "prop": "coordinates",
            "titles": canonical,
            "colimit": 1,
            "coprimary": "primary",
        }
        r = session.get(WIKI_API, params=params, timeout=20)
        r.raise_for_status()
        data = r.json()

        page = data["query"]["pages"][0]
        if page.get("missing") or not page.get("coordinates"):
            return None, None, None

        coords = page["coordinates"][0]
        return coords["lat"], coords["lon"], page["title"]
    except Exception:
        return None, None, None


def geocode_all_locations(locations):
    """Geocode all locations using both Nominatim and Wikipedia"""
    geolocator = Nominatim(user_agent=USER_AGENT)
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json"})
    
    total = len(locations)
    results = {}
    
    # Statistics
    stats = {
        'nominatim_success': 0,
        'nominatim_failed': 0,
        'wikipedia_success': 0,
        'wikipedia_failed': 0,
        'both_agree': 0,
        'diverged_used_wikipedia': 0,
        'only_nominatim': 0,
        'only_wikipedia': 0,
        'both_failed': 0,
    }
    
    print(f"\n{'='*70}")
    print(f"{'#':<5} {'Status':<20} {'Nom':<8} {'Wiki':<8} {'Dist':<10} {'Location'}")
    print(f"{'='*70}")
    
    for idx, (place, data) in enumerate(locations.items(), 1):
        # Get Nominatim coordinates
        nom_lat, nom_lon = get_nominatim_coords(geolocator, place)
        time.sleep(1.1)  # Rate limit
        
        # Get Wikipedia coordinates
        wiki_lat, wiki_lon, wiki_page = get_wikipedia_coords(session, place)
        time.sleep(0.2)  # Rate limit
        
        # Determine which coordinates to use
        result = {
            'place': place,
            'region': data['region'],
            'nominatim_lat': nom_lat,
            'nominatim_lon': nom_lon,
            'wikipedia_lat': wiki_lat,
            'wikipedia_lon': wiki_lon,
            'wikipedia_page': wiki_page,
            'chosen_source': None,
            'chosen_lat': None,
            'chosen_lon': None,
            'distance_km': None,
        }
        
        has_nom = nom_lat is not None
        has_wiki = wiki_lat is not None
        
        # Update stats
        if has_nom:
            stats['nominatim_success'] += 1
        else:
            stats['nominatim_failed'] += 1
        if has_wiki:
            stats['wikipedia_success'] += 1
        else:
            stats['wikipedia_failed'] += 1
        
        # Decide which source to use
        if has_nom and has_wiki:
            distance = haversine_km(nom_lon, nom_lat, wiki_lon, wiki_lat)
            result['distance_km'] = round(distance, 2)
            
            if distance <= DIVERGENCE_THRESHOLD_KM:
                # Both agree - use Nominatim (usually more precise)
                result['chosen_source'] = 'nominatim'
                result['chosen_lat'] = nom_lat
                result['chosen_lon'] = nom_lon
                stats['both_agree'] += 1
                status = "BOTH OK"
            else:
                # Diverged - prefer Wikipedia (more reliable for named places)
                result['chosen_source'] = 'wikipedia'
                result['chosen_lat'] = wiki_lat
                result['chosen_lon'] = wiki_lon
                stats['diverged_used_wikipedia'] += 1
                status = f"DIVERGED ({distance:.0f}km)"
        elif has_nom:
            result['chosen_source'] = 'nominatim'
            result['chosen_lat'] = nom_lat
            result['chosen_lon'] = nom_lon
            stats['only_nominatim'] += 1
            status = "NOM ONLY"
        elif has_wiki:
            result['chosen_source'] = 'wikipedia'
            result['chosen_lat'] = wiki_lat
            result['chosen_lon'] = wiki_lon
            stats['only_wikipedia'] += 1
            status = "WIKI ONLY"
        else:
            stats['both_failed'] += 1
            status = "FAILED"
        
        # Print progress
        nom_status = "OK" if has_nom else "--"
        wiki_status = "OK" if has_wiki else "--"
        dist_str = f"{result['distance_km']:.1f}km" if result['distance_km'] else "--"
        place_short = place[:30] + ".." if len(place) > 32 else place
        print(f"{idx:<5} {status:<20} {nom_status:<8} {wiki_status:<8} {dist_str:<10} {place_short}")
        
        results[place] = result
    
    # Print summary
    print_summary(stats, total)
    
    return results, stats


def print_summary(stats, total):
    """Print geocoding summary statistics"""
    print(f"\n{'='*70}")
    print("GEOCODING SUMMARY")
    print(f"{'='*70}")
    
    print(f"\n{'Source':<30} {'Success':<12} {'Failed':<12} {'Rate'}")
    print("-" * 60)
    print(f"{'Nominatim':<30} {stats['nominatim_success']:<12} {stats['nominatim_failed']:<12} {stats['nominatim_success']/total*100:.1f}%")
    print(f"{'Wikipedia':<30} {stats['wikipedia_success']:<12} {stats['wikipedia_failed']:<12} {stats['wikipedia_success']/total*100:.1f}%")
    
    print(f"\n{'Outcome':<30} {'Count':<12} {'Percentage'}")
    print("-" * 60)
    print(f"{'Both agree (< {0}km)'.format(DIVERGENCE_THRESHOLD_KM):<30} {stats['both_agree']:<12} {stats['both_agree']/total*100:.1f}%")
    print(f"{'Diverged -> used Wikipedia':<30} {stats['diverged_used_wikipedia']:<12} {stats['diverged_used_wikipedia']/total*100:.1f}%")
    print(f"{'Only Nominatim available':<30} {stats['only_nominatim']:<12} {stats['only_nominatim']/total*100:.1f}%")
    print(f"{'Only Wikipedia available':<30} {stats['only_wikipedia']:<12} {stats['only_wikipedia']/total*100:.1f}%")
    print(f"{'Both failed':<30} {stats['both_failed']:<12} {stats['both_failed']/total*100:.1f}%")
    
    geocoded = total - stats['both_failed']
    print(f"\n{'Total locations:':<30} {total}")
    print(f"{'Successfully geocoded:':<30} {geocoded} ({geocoded/total*100:.1f}%)")
    print(f"{'='*70}")


def extract_country(place):
    """Extract country from place string"""
    if place:
        parts = place.split(',')
        return parts[-1].strip() if parts else None
    return None


def export_geojson(geocoded, wines, output_file='../data/wines_map.geojson'):
    """Export data as GeoJSON for mapping"""
    # Count wines per location
    wine_counts = {}
    wine_lists = {}
    for wine in wines:
        place = wine.get('place', '')
        if place:
            wine_counts[place] = wine_counts.get(place, 0) + 1
            if place not in wine_lists:
                wine_lists[place] = []
            wine_lists[place].append(f"{wine.get('name', '')} ({wine.get('vineyard', '')})")
    
    features = []
    for place, data in geocoded.items():
        if data['chosen_lat'] is None:
            continue
        
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [data['chosen_lon'], data['chosen_lat']]
            },
            "properties": {
                "place": place,
                "country": extract_country(place),
                "wine_count": wine_counts.get(place, 0),
                "wines": "; ".join(wine_lists.get(place, [])[:10]),  # Limit to 10 wines
                "source": data['chosen_source'],
                "nominatim_lat": data['nominatim_lat'],
                "nominatim_lon": data['nominatim_lon'],
                "wikipedia_lat": data['wikipedia_lat'],
                "wikipedia_lon": data['wikipedia_lon'],
                "distance_km": data['distance_km'],
            }
        })
    
    geojson = {
        "type": "FeatureCollection",
        "features": features
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(geojson, f, indent=2, ensure_ascii=False)
    
    print(f"\nGeoJSON exported to {output_file} ({len(features)} locations)")
    return len(features)


def main():
    # Load data
    print("Loading wine data...")
    data = load_wine_data('../data/vivino_wines_complete_details_final_no_duplicates.json')
    wines = data['wines']
    print(f"Loaded {len(wines)} wines")
    
    # Extract unique locations
    print("\nExtracting unique locations...")
    locations = extract_unique_locations(wines)
    print(f"Found {len(locations)} unique locations")
    
    # Geocode locations with both sources
    print(f"\nGeocoding locations (Nominatim + Wikipedia)...")
    print(f"Divergence threshold: {DIVERGENCE_THRESHOLD_KM}km")
    geocoded, stats = geocode_all_locations(locations)
    
    # Save geocoded results
    with open('../data/geocoded_locations.json', 'w', encoding='utf-8') as f:
        json.dump(geocoded, f, indent=2, ensure_ascii=False)
    print(f"\nGeocoded data saved to ../data/geocoded_locations.json")
    
    # Export GeoJSON for mapping
    print("\nExporting GeoJSON...")
    num_features = export_geojson(geocoded, wines)
    
    # Final summary
    print(f"\n{'='*70}")
    print("COMPLETE")
    print(f"{'='*70}")
    print(f"  Wines processed:        {len(wines)}")
    print(f"  Unique locations:       {len(locations)}")
    print(f"  Successfully geocoded:  {num_features}")
    print(f"  Output files:")
    print(f"    - ../data/geocoded_locations.json")
    print(f"    - ../data/wines_map.geojson")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
