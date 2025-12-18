import json
import time
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import sqlite3

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
                'latitude': None,
                'longitude': None
            }
    return locations

def geocode_location(geolocator, location_name, retry=3):
    """Geocode a single location with retry logic"""
    for attempt in range(retry):
        try:
            location = geolocator.geocode(location_name, timeout=10)
            if location:
                return location.latitude, location.longitude
            return None, None
        except (GeocoderTimedOut, GeocoderServiceError) as e:
            if attempt == retry - 1:
                print(f"Failed to geocode {location_name}: {e}")
                return None, None
            time.sleep(2)
    return None, None

def geocode_all_locations(locations):
    """Geocode all unique locations"""
    geolocator = Nominatim(user_agent="wine_mapper_v1")
    
    total = len(locations)
    success_count = 0
    failed_locations = []
    
    for idx, (place, data) in enumerate(locations.items(), 1):
        lat, lon = geocode_location(geolocator, place)
        data['latitude'] = lat
        data['longitude'] = lon
        
        # Print status for each location
        if lat is not None:
            success_count += 1
            status = f"OK ({lat:.4f}, {lon:.4f})"
        else:
            failed_locations.append(place)
            status = "FAILED"
        
        print(f"[{idx:3}/{total}] {status:<30} {place}")
        
        # Respect Nominatim rate limit (1 request per second)
        time.sleep(1.1)
    
    # Print summary table
    print_geocoding_summary(total, success_count, failed_locations)
    
    return locations


def print_geocoding_summary(total, success_count, failed_locations):
    """Print a summary table of geocoding results"""
    failed_count = len(failed_locations)
    success_pct = (success_count / total) * 100 if total > 0 else 0
    failed_pct = (failed_count / total) * 100 if total > 0 else 0
    
    print("\n" + "=" * 60)
    print("NOMINATIM GEOCODING SUMMARY")
    print("=" * 60)
    
    print(f"\n{'Status':<25} {'Count':<10} {'Percentage':<12}")
    print("-" * 50)
    print(f"{'Successfully geocoded':<25} {success_count:<10} {success_pct:>6.1f}%")
    print(f"{'Failed to geocode':<25} {failed_count:<10} {failed_pct:>6.1f}%")
    print("-" * 50)
    print(f"{'Total locations':<25} {total:<10} {'100.0%':>7}")
    
    if failed_locations:
        print(f"\nLocations that failed geocoding ({failed_count}):")
        for place in failed_locations[:15]:
            place_short = place[:55] + ".." if len(place) > 57 else place
            print(f"  - {place_short}")
        if len(failed_locations) > 15:
            print(f"  ... and {len(failed_locations) - 15} more")
    
    print("=" * 60)

def create_database():
    """Create SQLite database with two tables"""
    conn = sqlite3.connect('data/wines.db')
    cursor = conn.cursor()
    
    # Create regions table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS regions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        place TEXT UNIQUE NOT NULL,
        region TEXT,
        latitude REAL,
        longitude REAL,
        country TEXT
    )
    ''')
    
    # Create wines table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS wines (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        vineyard TEXT,
        name TEXT NOT NULL,
        rating REAL,
        price TEXT,
        region_id INTEGER,
        grapes TEXT,
        wine_style TEXT,
        alcohol_content TEXT,
        allergens TEXT,
        description TEXT,
        url TEXT,
        taste_light_bold REAL,
        taste_smooth_tannic REAL,
        taste_dry_sweet REAL,
        taste_soft_acidic REAL,
        food_pairings TEXT,
        FOREIGN KEY (region_id) REFERENCES regions(id)
    )
    ''')
    
    conn.commit()
    return conn

def extract_country(place):
    """Extract country from place string"""
    if place:
        parts = place.split(',')
        return parts[-1].strip() if parts else None
    return None

def populate_database(conn, wines, geocoded_locations):
    """Populate database with wines and regions"""
    cursor = conn.cursor()
    
    # Insert regions
    region_ids = {}
    for place, data in geocoded_locations.items():
        cursor.execute('''
        INSERT OR IGNORE INTO regions (place, region, latitude, longitude, country)
        VALUES (?, ?, ?, ?, ?)
        ''', (
            place,
            data['region'],
            data['latitude'],
            data['longitude'],
            extract_country(place)
        ))
        
        # Get the region_id
        cursor.execute('SELECT id FROM regions WHERE place = ?', (place,))
        region_ids[place] = cursor.fetchone()[0]
    
    # Insert wines
    for wine in wines:
        place = wine.get('place', '')
        region_id = region_ids.get(place)
        
        # Extract rating as float
        rating_str = wine.get('rating', '0').replace(',', '.')
        try:
            rating = float(rating_str)
        except ValueError:
            rating = None
        
        # Extract taste characteristics
        taste = wine.get('taste_characteristics', {})
        taste_light_bold = taste.get('light_bold', {}).get('percentage')
        taste_smooth_tannic = taste.get('smooth_tannic', {}).get('percentage')
        taste_dry_sweet = taste.get('dry_sweet', {}).get('percentage')
        taste_soft_acidic = taste.get('soft_acidic', {}).get('percentage')
        
        # Extract food pairings as comma-separated string
        food_pairings = wine.get('food_pairings', [])
        food_pairings_str = ', '.join(food_pairings) if food_pairings else None
        
        cursor.execute('''
        INSERT INTO wines (
            vineyard, name, rating, price, region_id, 
            grapes, wine_style, alcohol_content, allergens, 
            description, url, taste_light_bold, 
            taste_smooth_tannic, taste_dry_sweet, taste_soft_acidic,
            food_pairings
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            wine.get('vineyard'),
            wine.get('name'),
            rating,
            wine.get('price'),
            region_id,
            wine.get('grapes'),
            wine.get('wine_style'),
            wine.get('teneur_en_alcool'),
            wine.get('allergens'),
            wine.get('description'),
            wine.get('url'),
            taste_light_bold,
            taste_smooth_tannic,
            taste_dry_sweet,
            taste_soft_acidic,
            food_pairings_str
        ))
    
    conn.commit()

def export_geojson(conn, output_file='data/wines_map.geojson'):
    """Export data as GeoJSON for mapping"""
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT 
        r.place, r.latitude, r.longitude, r.country,
        COUNT(w.id) as wine_count,
        GROUP_CONCAT(w.name || ' (' || w.vineyard || ')', '; ') as wines
    FROM regions r
    LEFT JOIN wines w ON r.id = w.region_id
    WHERE r.latitude IS NOT NULL AND r.longitude IS NOT NULL
    GROUP BY r.id
    ''')
    
    features = []
    for row in cursor.fetchall():
        place, lat, lon, country, count, wines = row
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [lon, lat]
            },
            "properties": {
                "place": place,
                "country": country,
                "wine_count": count,
                "wines": wines
            }
        })
    
    geojson = {
        "type": "FeatureCollection",
        "features": features
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(geojson, f, indent=2, ensure_ascii=False)
    
    print(f"GeoJSON exported to {output_file}")

def main():
    # Load data
    print("Loading wine data...")
    data = load_wine_data('data/vivino_wines_complete_details_final_no_duplicates.json')
    wines = data['wines']
    
    # Extract unique locations
    print("\nExtracting unique locations...")
    locations = extract_unique_locations(wines)
    print(f"Found {len(locations)} unique locations")
    
    # Geocode locations
    print("\nGeocoding locations (this may take a while)...")
    geocoded = geocode_all_locations(locations)
    
    # Save geocoded results
    with open('data/geocoded_locations.json', 'w', encoding='utf-8') as f:
        json.dump(geocoded, f, indent=2, ensure_ascii=False)
    print("\nGeocoded data saved to data/geocoded_locations.json")
    
    # Create database
    print("\nCreating database...")
    conn = create_database()
    
    # Populate database
    print("Populating database...")
    populate_database(conn, wines, geocoded)
    
    # Export GeoJSON for mapping
    print("\nExporting GeoJSON...")
    export_geojson(conn)
    
    conn.close()
    
    # Final summary
    success = sum(1 for v in geocoded.values() if v['latitude'] is not None)
    print("\n" + "=" * 60)
    print("PIPELINE COMPLETE")
    print("=" * 60)
    print(f"  Wines processed:        {len(wines)}")
    print(f"  Unique locations:       {len(geocoded)}")
    print(f"  Successfully geocoded:  {success} ({(success/len(geocoded))*100:.1f}%)")
    print(f"  Database:               data/wines.db")
    print(f"  GeoJSON:                data/wines_map.geojson")
    print("=" * 60)

if __name__ == "__main__":
    main()