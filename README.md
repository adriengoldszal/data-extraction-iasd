# Vivino Wine Map
> **Contributors:** Adrien Goldszal • Barthélémy Charlier • Daniel Gagliardi

A project database showcasing wines and their locations.

## Installation

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Usage

### 1. Scraping

```bash
cd scraping

# Basic scrape (10 pages by default)
python vivino_web_scraper.py

# With detailed info (grapes, region, style, taste characteristics, food pairings)
python vivino_web_scraper.py --detailed

# With custom options
python vivino_web_scraper.py --detailed --max-pages 5
```

#### Options

| Option | Description |
|--------|-------------|
| `--detailed` | Fetch additional details from each wine's page |
| `--max-pages N` | Maximum number of pages to scrape (default: 10) |
| `--url URL` | Custom Vivino explore URL to start from |

#### Removing Duplicates

```bash
cd scraping
python filter_duplicates.py
```

Identifies and removes duplicate wines based on (vineyard, name, place).

### 2. Geocoding & Database

```bash
python get_nominatim_locations.py
```

This script:
1. Loads wine data from `data/vivino_wines_complete_details_final_no_duplicates.json`
2. Extracts unique locations and geocodes them via [Nominatim](https://nominatim.org/)
3. Creates a SQLite database (`data/wines.db`) with two tables:
   - **regions**: place, region, latitude, longitude, country
   - **wines**: vineyard, name, rating, price, grapes, wine_style, alcohol_content, allergens, description, url, taste characteristics, food pairings
4. Exports `data/wines_map.geojson` for mapping

#### Output Files

| File | Description |
|------|-------------|
| `data/geocoded_locations.json` | Cached geocoding results |
| `data/wines.db` | SQLite database with wines & regions |
| `data/wines_map.geojson` | GeoJSON for map visualization |

### 3. Querying the Database

```bash
python query_wines.py
```

Shows:
- Database structure (tables & columns)
- List of all French wines (sorted by rating)

## Data Quality Assessment

Scripts for validating geocoding accuracy are in the `data_quality_assessment/` folder.

### verify_locations.py

Cross-validates geocoded coordinates against Wikipedia's coordinates for the same place names:

```bash
cd data_quality_assessment
python verify_locations.py
```

This script:
1. Reads `data/wines_map.geojson` with Nominatim coordinates
2. Queries Wikipedia API for each place's coordinates
3. Calculates the distance (in km) between Nominatim and Wikipedia coordinates using the Haversine formula
4. Outputs `data/places_with_dist.geojson` with added fields: `wiki_lat`, `wiki_lon`, `wiki_page`, `distance_m`

### plot_location_errors.py

Visualizes the geocoding accuracy from the verification results:

```bash
cd data_quality_assessment
python plot_location_errors.py
```

Generates and saves three charts to the `data_quality_assessment/` folder:
1. **distance_histogram.png** - Distribution of distances between Nominatim and Wikipedia coordinates
2. **distance_histogram_log.png** - Same distribution on log scale (useful for identifying outliers)
3. **top_outliers.png** - Bar chart showing the 15 places with largest coordinate discrepancies

Large distances may indicate geocoding errors or ambiguous place names.

## Map Visualization

Generate an interactive map with `wine_map.py`:

```bash
python wine_map.py
```

Opens `wines_map.html` in your browser with:
- Clustered markers (zoom to expand)
- Color-coded by country
- Popups with wine details


## Project Structure

```
├── scraping/
│   ├── vivino_web_scraper.py   # Main scraper
│   └── filter_duplicates.py    # Remove duplicate wines
├── data/
│   ├── vivino_wines_complete_details_final.json
│   ├── vivino_wines_complete_details_final_no_duplicates.json
│   ├── geocoded_locations.json
│   ├── wines_map.geojson
│   ├── places_with_dist.geojson
│   └── wines.db
├── data_quality_assessment/
│   ├── verify_locations.py     # Cross-check coordinates with Wikipedia
│   ├── plot_location_errors.py # Visualize geocoding accuracy
│   ├── distance_histogram.png  # Output chart
│   ├── distance_histogram_log.png
│   └── top_outliers.png
├── get_nominatim_locations.py  # Geocoding & database creation
├── query_wines.py              # Database exploration
└── wine_map.py                 # Interactive map generation
```

## Note

The scraper opens a visible Chrome window (required to bypass bot detection).
