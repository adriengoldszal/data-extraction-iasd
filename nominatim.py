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
    for idx, (place, data) in enumerate(locations.items(), 1):
        print(f"Geocoding {idx}/{total}: {place}")
        
        lat, lon = geocode_location(geolocator, place)
        data['latitude'] = lat
        data['longitude'] = lon
        
        # Respect Nominatim rate limit (1 request per second)
        time.sleep(1.1)
    
    return locations

def create_database():
    """Create SQLite database with two tables"""
    conn = sqlite3.connect('wines.db')
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
        
        cursor.execute('''
        INSERT INTO wines (
            vineyard, name, rating, price, region_id, 
            grapes, wine_style, alcohol_content, allergens, 
            description, url
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            wine.get('url')
        ))
    
    conn.commit()

def export_geojson(conn, output_file='wines_map.geojson'):
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
    data = load_wine_data('vivino_wines_complete_details_final_no_duplicates.json')
    wines = data['wines']
    
    # Extract unique locations
    print("\nExtracting unique locations...")
    locations = extract_unique_locations(wines)
    print(f"Found {len(locations)} unique locations")
    
    # Geocode locations
    print("\nGeocoding locations (this may take a while)...")
    geocoded = geocode_all_locations(locations)
    
    # Save geocoded results
    with open('geocoded_locations.json', 'w', encoding='utf-8') as f:
        json.dump(geocoded, f, indent=2, ensure_ascii=False)
    print("\nGeocoded data saved to geocoded_locations.json")
    
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
    print("\n✓ Complete! Database created at wines.db")

if __name__ == "__main__":
    main()