"""
Simple script to query the wines database.
"""

import sqlite3

def show_structure(cursor):
    """Show database structure"""
    print("=" * 50)
    print("DATABASE STRUCTURE")
    print("=" * 50)
    
    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    
    for (table_name,) in tables:
        print(f"{table_name}")
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        for col in columns:
            print(f"   - {col[1]} ({col[2]})")


def list_french_wines(cursor):
    """List all French wines"""
    print("\n" + "=" * 50)
    print("FRENCH WINES")
    print("=" * 50)
    
    cursor.execute('''
        SELECT w.vineyard, w.name, w.rating, w.price, p.place, w.grapes
        FROM wines w
        JOIN places p ON w.place_id = p.id
        WHERE p.country = 'France'
        ORDER BY w.rating DESC
        LIMIT 10
    ''')
    
    wines = cursor.fetchall()
    print(f"\nFound {len(wines)} French wines:\n")
    
    for vineyard, name, rating, price, place, grapes in wines:
        print(f"{vineyard} - {name}")
        print(f"   Rating: {rating} | Price: {price}")
        print(f"   Region: {place}")
        if grapes:
            print(f"   Grapes: {grapes}")
        print()


def main():
    conn = sqlite3.connect('../data/wines.db')
    cursor = conn.cursor()
    
    show_structure(cursor)
    list_french_wines(cursor)
    
    conn.close()


if __name__ == "__main__":
    main()

