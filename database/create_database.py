"""
Create SQLite database from geocoded wine data.
Run this after get_nominatim_locations.py has generated the geocoded data.
"""

import json
import sqlite3


def load_wine_data(filepath):
    """Load wine data from JSON file"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_geocoded_locations(filepath):
    """Load geocoded locations from JSON file"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def extract_country(place):
    """Extract country from place string"""
    if place:
        parts = place.split(',')
        return parts[-1].strip() if parts else None
    return None


def create_database(db_path='../data/wines.db'):
    """Create SQLite database with tables"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Drop existing tables to recreate
    cursor.execute('DROP TABLE IF EXISTS wines')
    cursor.execute('DROP TABLE IF EXISTS places')
    
    # Create places table
    cursor.execute('''
    CREATE TABLE places (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        place TEXT UNIQUE NOT NULL,
        region TEXT,
        latitude REAL,
        longitude REAL,
        country TEXT,
        source TEXT,
        nominatim_lat REAL,
        nominatim_lon REAL,
        wikipedia_lat REAL,
        wikipedia_lon REAL,
        distance_km REAL
    )
    ''')
    
    # Create wines table
    cursor.execute('''
    CREATE TABLE wines (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        vineyard TEXT,
        name TEXT NOT NULL,
        rating REAL,
        price TEXT,
        place_id INTEGER,
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
        FOREIGN KEY (place_id) REFERENCES places(id)
    )
    ''')
    
    conn.commit()
    print(f"Database created: {db_path}")
    return conn


def populate_places(conn, geocoded_locations):
    """Populate places table"""
    cursor = conn.cursor()
    place_ids = {}
    
    for place, data in geocoded_locations.items():
        cursor.execute('''
        INSERT INTO places (
            place, region, latitude, longitude, country,
            source, nominatim_lat, nominatim_lon, 
            wikipedia_lat, wikipedia_lon, distance_km
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            place,
            data.get('region'),
            data.get('chosen_lat'),
            data.get('chosen_lon'),
            extract_country(place),
            data.get('chosen_source'),
            data.get('nominatim_lat'),
            data.get('nominatim_lon'),
            data.get('wikipedia_lat'),
            data.get('wikipedia_lon'),
            data.get('distance_km'),
        ))
        
        place_ids[place] = cursor.lastrowid
    
    conn.commit()
    return place_ids


def populate_wines(conn, wines, place_ids):
    """Populate wines table"""
    cursor = conn.cursor()
    
    for wine in wines:
        place = wine.get('place', '')
        place_id = place_ids.get(place)
        
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
            vineyard, name, rating, price, place_id, 
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
            place_id,
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


def print_database_summary(conn):
    """Print summary of database contents"""
    cursor = conn.cursor()
    
    print(f"\n{'='*60}")
    print("DATABASE SUMMARY")
    print(f"{'='*60}")
    
    # Count places
    cursor.execute('SELECT COUNT(*) FROM places')
    total_places = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM places WHERE latitude IS NOT NULL')
    geocoded_places = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM places WHERE source = "nominatim"')
    nominatim_places = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM places WHERE source = "wikipedia"')
    wikipedia_places = cursor.fetchone()[0]
    
    # Count wines
    cursor.execute('SELECT COUNT(*) FROM wines')
    total_wines = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(DISTINCT place_id) FROM wines WHERE place_id IS NOT NULL')
    wines_with_place = cursor.fetchone()[0]
    
    # Count by country
    cursor.execute('''
        SELECT country, COUNT(*) as cnt 
        FROM places 
        WHERE country IS NOT NULL 
        GROUP BY country 
        ORDER BY cnt DESC
    ''')
    countries = cursor.fetchall()
    
    print(f"\nPlaces table:")
    print(f"  Total places:           {total_places}")
    print(f"  With coordinates:       {geocoded_places}")
    print(f"  Source: Nominatim:      {nominatim_places}")
    print(f"  Source: Wikipedia:      {wikipedia_places}")
    
    print(f"\nWines table:")
    print(f"  Total wines:            {total_wines}")
    print(f"  Linked to places:       {wines_with_place}")
    
    print(f"\nPlaces by country:")
    for country, count in countries[:5]:
        print(f"  {country}: {count}")
    
    # Sample queries
    print(f"\nSample data (top 5 wines by rating):")
    cursor.execute('''
        SELECT w.name, w.vineyard, w.rating, p.place
        FROM wines w
        JOIN places p ON w.place_id = p.id
        WHERE w.rating IS NOT NULL
        ORDER BY w.rating DESC
        LIMIT 5
    ''')
    for row in cursor.fetchall():
        name, vineyard, rating, place = row
        print(f"  {rating:.1f} - {name} ({vineyard}) - {place}")
    
    print(f"{'='*60}")


def main():
    print("Loading data...")
    
    # Load wine data
    wine_data = load_wine_data('../data/vivino_wines_complete_details_final_no_duplicates.json')
    wines = wine_data['wines']
    print(f"  Loaded {len(wines)} wines")
    
    # Load geocoded locations
    geocoded = load_geocoded_locations('../data/geocoded_locations.json')
    print(f"  Loaded {len(geocoded)} geocoded locations")
    
    # Create database
    print("\nCreating database...")
    conn = create_database()
    
    # Populate tables
    print("Populating places...")
    place_ids = populate_places(conn, geocoded)
    print(f"  Inserted {len(place_ids)} places")
    
    print("Populating wines...")
    populate_wines(conn, wines, place_ids)
    print(f"  Inserted {len(wines)} wines")
    
    # Print summary
    print_database_summary(conn)
    
    conn.close()
    print("\nDatabase saved to: ../data/wines.db")


if __name__ == "__main__":
    main()
