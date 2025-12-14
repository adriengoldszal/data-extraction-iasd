# Vivino Wine Scraper

A minimal web scraper that extracts wine data from Vivino's explore pages.

## Installation

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Usage

```bash
# Basic scrape (10 pages by default)
python vivino_web_scraper.py

# With detailed info (grapes, region, style, allergens, description)
python vivino_web_scraper.py --detailed

# With custom options
python vivino_web_scraper.py --detailed --max-pages 5
```

### Options

| Option | Description |
|--------|-------------|
| `--detailed` | Fetch additional details from each wine's page |
| `--max-pages N` | Maximum number of pages to scrape (default: 10) |
| `--url URL` | Custom Vivino explore URL to start from |

## Output

Results are saved to `vivino_wines.json` with the following fields:

- `vineyard`, `name`, `place`, `rating`, `price`, `url`
- With `--detailed`: `winery`, `grapes`, `region`, `wine_style`, `allergens`, `description`

## Geocoding & Database

After scraping, use `nominatim.py` to geocode wine regions and create a database:

```bash
python nominatim.py
```

This script:
1. Loads wine data from `vivino_wines_detailed.json`
2. Extracts unique locations and geocodes them via [Nominatim](https://nominatim.org/)
3. Creates a SQLite database (`wines.db`) with two tables:
   - **regions**: place, coordinates, country
   - **wines**: all wine details linked to regions
4. Exports `wines_map.geojson` for mapping

### Output Files

| File | Description |
|------|-------------|
| `geocoded_locations.json` | Cached geocoding results |
| `wines.db` | SQLite database with wines & regions |
| `wines_map.geojson` | GeoJSON for map visualization |

## Querying the Database

Use `query_wines.py` to explore the database:

```bash
python query_wines.py
```

This shows:
- Database structure (tables & columns)
- List of all French wines (sorted by rating)

## Note

The scraper opens a visible Chrome window (required to bypass bot detection).

