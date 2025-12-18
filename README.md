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

## Pipeline Overview

```
1. Scraping          → vivino_wines.json
2. Deduplication     → vivino_wines_..._no_duplicates.json
3. Geocoding         → geocoded_locations.json + wines_map.geojson
4. Database          → wines.db
5. Visualization     → wines_map.html
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

### 2. Geocoding (Nominatim + Wikipedia)

```bash
cd locations
python get_locations.py
```

This script geocodes all wine locations using **two sources** for quality assurance:

1. **Nominatim** (OpenStreetMap) - primary geocoding
2. **Wikipedia** - secondary verification

For each location:
- If both sources agree (< 50km apart) → uses Nominatim coordinates
- If sources diverge (> 50km apart) → uses Wikipedia coordinates (more reliable for named regions)
- If only one source available → uses that source
- Prints detailed statistics and quality metrics

#### Output Files

| File | Description |
|------|-------------|
| `data/geocoded_locations.json` | All geocoding results (both sources + chosen coordinates) |
| `data/wines_map.geojson` | GeoJSON for map visualization |

#### Geocoding Quality Assessment

```bash
cd locations
python plot_location_errors.py
```

Generates charts and statistics:
- **distance_histogram.png** - Distribution of Nominatim vs Wikipedia distances
- **distance_histogram_log.png** - Same on log scale (shows outliers better)
- **top_outliers.png** - Top 15 largest coordinate discrepancies

### 3. Database Creation

```bash
cd database
python create_database.py
```

Creates a SQLite database from the geocoded data:

- **places** table: place, coordinates, country, source used, both source coordinates
- **wines** table: vineyard, name, rating, price, grapes, wine_style, taste characteristics, food pairings

### 4. Database Quality Assessment

```bash
cd database
python data_assessment.py
```

Analyzes the database for data quality:
- Missing/null values per column (with fill rates)
- Foreign key integrity
- Rating, price, geocoding coverage statistics
- Breakdown by country

### 5. Querying the Database

```bash
cd database
python query_wines.py
```

Shows database structure and sample queries.

### 6. Map Visualization

```bash
cd map
python wine_map.py
```

Opens `wines_map.html` in your browser with:
- Clustered markers (zoom to expand)
- Color-coded by country
- Popups with wine details

## Data Storage Justification

We chose **SQLite** as our relational DBMS because:

- **Zero configuration** - no server to install or manage
- **Portable** - single `wines.db` file can be shared/moved easily
- **Built into Python** - no external dependencies needed
- **Relational model** - wines linked to regions via foreign keys, enables SQL queries
- **Appropriate scale** - SQLite handles up to ~140TB, our ~1500 wines dataset is tiny
- **Query capability** - complex queries (wines by country, by rating, joins, aggregations)

## Project Structure

```
├── scraping/
│   ├── vivino_web_scraper.py   # Web scraper with bot detection bypass
│   └── filter_duplicates.py    # Remove duplicate wines
├── locations/
│   ├── get_locations.py        # Geocoding (Nominatim + Wikipedia)
│   ├── plot_location_errors.py # Analyze geocoding quality
│   ├── distance_histogram.png
│   ├── distance_histogram_log.png
│   └── top_outliers.png
├── database/
│   ├── create_database.py      # SQLite database creation
│   ├── data_assessment.py      # Data quality assessment
│   └── query_wines.py          # Database exploration
├── data/
│   ├── vivino_wines_complete_details_final.json
│   ├── vivino_wines_complete_details_final_no_duplicates.json
│   ├── geocoded_locations.json
│   ├── wines_map.geojson
│   └── wines.db
└── map/
    ├── wine_map.py             # Interactive map generation
    └── wines_map.html          # Generated map output
```
