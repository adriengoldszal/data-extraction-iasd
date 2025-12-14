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

## Note

The scraper opens a visible Chrome window (required to bypass bot detection).

