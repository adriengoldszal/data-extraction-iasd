"""
Data Quality Assessment for the wines database.
Checks for missing/null entries across all tables and columns.
"""

import sqlite3
from pathlib import Path

DB_PATH = Path("../data/wines.db")


def get_table_info(cursor, table_name):
    """Get column information for a table."""
    cursor.execute(f"PRAGMA table_info({table_name})")
    return cursor.fetchall()


def count_nulls(cursor, table_name, column_name):
    """Count null/empty values in a column."""
    cursor.execute(f"""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN {column_name} IS NULL OR {column_name} = '' THEN 1 ELSE 0 END) as missing
        FROM {table_name}
    """)
    return cursor.fetchone()


def analyze_table(cursor, table_name):
    """Analyze all columns in a table for missing values."""
    columns = get_table_info(cursor, table_name)
    
    # Get total row count
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    total_rows = cursor.fetchone()[0]
    
    results = {
        'table': table_name,
        'total_rows': total_rows,
        'columns': []
    }
    
    for col in columns:
        col_id, col_name, col_type, not_null, default, pk = col
        total, missing = count_nulls(cursor, table_name, col_name)
        
        results['columns'].append({
            'name': col_name,
            'type': col_type,
            'total': total,
            'missing': missing,
            'filled': total - missing,
            'fill_rate': ((total - missing) / total * 100) if total > 0 else 0,
            'is_pk': pk == 1,
        })
    
    return results


def print_table_report(results):
    """Print a formatted report for a table."""
    print(f"\n{'='*70}")
    print(f"TABLE: {results['table']}")
    print(f"Total rows: {results['total_rows']}")
    print(f"{'='*70}")
    
    print(f"\n{'Column':<25} {'Type':<12} {'Filled':<10} {'Missing':<10} {'Fill Rate'}")
    print("-" * 70)
    
    for col in results['columns']:
        fill_bar = "█" * int(col['fill_rate'] / 10) + "░" * (10 - int(col['fill_rate'] / 10))
        status = "✓" if col['fill_rate'] == 100 else ("⚠" if col['fill_rate'] >= 80 else "✗")
        
        print(f"{col['name']:<25} {col['type']:<12} {col['filled']:<10} {col['missing']:<10} {col['fill_rate']:>5.1f}% {fill_bar} {status}")


def analyze_foreign_keys(cursor):
    """Check foreign key integrity."""
    print(f"\n{'='*70}")
    print("FOREIGN KEY INTEGRITY")
    print(f"{'='*70}")
    
    # Check wines without valid region_id
    cursor.execute("""
        SELECT COUNT(*) FROM wines 
        WHERE region_id IS NULL OR region_id NOT IN (SELECT id FROM regions)
    """)
    orphan_wines = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM wines")
    total_wines = cursor.fetchone()[0]
    
    print(f"\nWines without valid region: {orphan_wines} / {total_wines} ({orphan_wines/total_wines*100:.1f}%)")


def analyze_data_quality(cursor):
    """Additional data quality checks."""
    print(f"\n{'='*70}")
    print("DATA QUALITY CHECKS")
    print(f"{'='*70}")
    
    # Rating distribution
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN rating IS NULL THEN 1 ELSE 0 END) as no_rating,
            AVG(rating) as avg_rating,
            MIN(rating) as min_rating,
            MAX(rating) as max_rating
        FROM wines
    """)
    row = cursor.fetchone()
    print(f"\nRatings:")
    print(f"  Total wines: {row[0]}")
    print(f"  Without rating: {row[1]} ({row[1]/row[0]*100:.1f}%)")
    print(f"  Average rating: {row[2]:.2f}" if row[2] else "  Average rating: N/A")
    print(f"  Range: {row[3]:.1f} - {row[4]:.1f}" if row[3] else "  Range: N/A")
    
    # Price coverage
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN price IS NULL OR price = '' THEN 1 ELSE 0 END) as no_price
        FROM wines
    """)
    row = cursor.fetchone()
    print(f"\nPrices:")
    print(f"  Without price: {row[1]} / {row[0]} ({row[1]/row[0]*100:.1f}%)")
    
    # Geocoding coverage
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN latitude IS NULL THEN 1 ELSE 0 END) as no_coords,
            SUM(CASE WHEN source = 'nominatim' THEN 1 ELSE 0 END) as nominatim,
            SUM(CASE WHEN source = 'wikipedia' THEN 1 ELSE 0 END) as wikipedia
        FROM regions
    """)
    row = cursor.fetchone()
    print(f"\nGeocoding:")
    print(f"  Total regions: {row[0]}")
    print(f"  Without coordinates: {row[1]} ({row[1]/row[0]*100:.1f}%)")
    print(f"  Source - Nominatim: {row[2]} ({row[2]/row[0]*100:.1f}%)")
    print(f"  Source - Wikipedia: {row[3]} ({row[3]/row[0]*100:.1f}%)")
    
    # Taste characteristics coverage
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN taste_light_bold IS NOT NULL THEN 1 ELSE 0 END) as has_taste
        FROM wines
    """)
    row = cursor.fetchone()
    print(f"\nTaste characteristics:")
    print(f"  With taste data: {row[1]} / {row[0]} ({row[1]/row[0]*100:.1f}%)")
    
    # Food pairings coverage
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN food_pairings IS NOT NULL AND food_pairings != '' THEN 1 ELSE 0 END) as has_food
        FROM wines
    """)
    row = cursor.fetchone()
    print(f"\nFood pairings:")
    print(f"  With food pairings: {row[1]} / {row[0]} ({row[1]/row[0]*100:.1f}%)")


def analyze_by_country(cursor):
    """Breakdown by country."""
    print(f"\n{'='*70}")
    print("BREAKDOWN BY COUNTRY")
    print(f"{'='*70}")
    
    cursor.execute("""
        SELECT 
            r.country,
            COUNT(DISTINCT r.id) as regions,
            COUNT(w.id) as wines,
            AVG(w.rating) as avg_rating
        FROM regions r
        LEFT JOIN wines w ON r.id = w.region_id
        GROUP BY r.country
        ORDER BY wines DESC
    """)
    
    print(f"\n{'Country':<20} {'Regions':<10} {'Wines':<10} {'Avg Rating'}")
    print("-" * 55)
    for row in cursor.fetchall():
        country = row[0] or "Unknown"
        avg_rating = f"{row[3]:.2f}" if row[3] else "N/A"
        print(f"{country:<20} {row[1]:<10} {row[2]:<10} {avg_rating}")


def main():
    if not DB_PATH.exists():
        raise SystemExit(f"Database not found: {DB_PATH}\nRun create_database.py first.")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("="*70)
    print("DATA QUALITY ASSESSMENT")
    print(f"Database: {DB_PATH}")
    print("="*70)
    
    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    
    # Analyze each table
    for table in tables:
        results = analyze_table(cursor, table)
        print_table_report(results)
    
    # Additional analyses
    analyze_foreign_keys(cursor)
    analyze_data_quality(cursor)
    analyze_by_country(cursor)
    
    # Summary
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    
    cursor.execute("SELECT COUNT(*) FROM wines")
    total_wines = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM regions")
    total_regions = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM regions WHERE latitude IS NOT NULL")
    geocoded_regions = cursor.fetchone()[0]
    
    print(f"\n  Total wines:            {total_wines}")
    print(f"  Total regions:          {total_regions}")
    print(f"  Geocoded regions:       {geocoded_regions} ({geocoded_regions/total_regions*100:.1f}%)")
    print(f"\n{'='*70}")
    
    conn.close()


if __name__ == "__main__":
    main()
