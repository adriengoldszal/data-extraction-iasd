from geopy.geocoders import Nominatim
from time import sleep

geolocator = Nominatim(user_agent="wine_test")

# Test with progressively simpler queries
test_queries = [
    "Cafayate Valley, Salta, Argentina",
    "Cafayate, Salta, Argentina",
    "Calchaqui Valley, Salta, Argentina",
    "Salta, Argentina",
]

for query in test_queries:
    print(f"\nTrying: {query}")
    try:
        location = geolocator.geocode(query, timeout=10)
        if location:
            print(f"✓ Found: {location.latitude}, {location.longitude}")
            print(f"  Address: {location.address}")
        else:
            print("✗ No results")
    except Exception as e:
        print(f"✗ Error: {e}")
    sleep(1.5)