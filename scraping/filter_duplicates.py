"""
Check for duplicate wines in vivino JSON data and optionally filter them out.
Duplicates are identified by (vineyard, name, place) combination.
"""

import json
from collections import Counter

def check_duplicates(filepath="../data/vivino_wines_complete_details_final.json", remove_duplicates=True):
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    wines = data.get("wines", data) if isinstance(data, dict) else data
    
    # Create keys from (vineyard, name, place)
    keys = [
        (w.get("vineyard"), w.get("name"), w.get("place"))
        for w in wines
    ]
    
    # Find duplicates
    counts = Counter(keys)
    duplicates = {k: v for k, v in counts.items() if v > 1}
    
    print(f"Total wines: {len(wines)}")
    print(f"Unique wines: {len(counts)}")
    print(f"Duplicate entries: {len(duplicates)}")
    
    if duplicates:
        print("\nDuplicates found:")
        for (vineyard, name, place), count in sorted(duplicates.items(), key=lambda x: -x[1]):
            print(f"  [{count}x] {vineyard} - {name} ({place})")
    else:
        print("\nNo duplicates found!")
    
    # Remove duplicates and save to new file
    if remove_duplicates:
        seen = set()
        unique_wines = []
        for wine in wines:
            key = (wine.get("vineyard"), wine.get("name"), wine.get("place"))
            if key not in seen:
                seen.add(key)
                unique_wines.append(wine)
        
        # Create output filename
        output_path = filepath.replace(".json", "_no_duplicates.json")
        
        # Save with same structure as original
        output_data = {"total_wines": len(unique_wines), "wines": unique_wines}
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        print(f"\nSaved {len(unique_wines)} unique wines to: {output_path}")
    
    return duplicates

if __name__ == "__main__":
    check_duplicates()
