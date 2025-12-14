"""
Minimal Vivino Web Scraper
Extracts wine names, vineyards, and places from Vivino explore pages.
"""

import argparse
import json
import time
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException


def create_driver():
    """Create an undetected Chrome driver to bypass bot detection."""
    options = uc.ChromeOptions()
    # NOTE: No headless mode - undetected-chromedriver works better with visible browser
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    
    driver = uc.Chrome(options=options, use_subprocess=True)
    return driver


def parse_wine_cards(driver):
    """Parse wine information from all wine cards on the current page."""
    wines = []
    
    # Wait for wine cards to load
    try:
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='wineCard']"))
        )
    except TimeoutException:
        print("No wine cards found on this page")

        logs = driver.get_log('browser')
        print(f"  Browser console logs: {logs}")

        return wines
    
    cards = driver.find_elements(By.CSS_SELECTOR, "[data-testid='wineCard']")
    
    for card in cards:
        wine = {}
        
        # Extract vineyard/winery name (first truncate element)
        try:
            vineyard_elem = card.find_element(By.CSS_SELECTOR, ".wineInfoVintage__truncate--3QAtw")
            wine["vineyard"] = vineyard_elem.text.strip()
        except NoSuchElementException:
            wine["vineyard"] = None
        
        # Extract wine name with vintage
        try:
            name_elem = card.find_element(By.CSS_SELECTOR, ".wineInfoVintage__vintage--VvWlU")
            wine["name"] = name_elem.text.strip()
        except NoSuchElementException:
            wine["name"] = None
        
        # Extract region and country
        try:
            location_elem = card.find_element(By.CSS_SELECTOR, ".wineInfoLocation__regionAndCountry--1nEJz")
            wine["place"] = location_elem.text.strip()
        except NoSuchElementException:
            wine["place"] = None
        
        # Extract rating if available
        try:
            rating_elem = card.find_element(By.CSS_SELECTOR, ".vivinoRating__averageValue--3p6Wp")
            wine["rating"] = rating_elem.text.strip()
        except NoSuchElementException:
            wine["rating"] = None
        
        # Extract price if available
        try:
            price_elem = card.find_element(By.CSS_SELECTOR, ".addToCartButton__price--qJdh4")
            wine["price"] = price_elem.text.strip()
        except NoSuchElementException:
            wine["price"] = None
        
        # Extract wine detail URL
        try:
            link_elem = card.find_element(By.CSS_SELECTOR, "a[data-testid='vintagePageLink']")
            wine["url"] = link_elem.get_attribute("href")
        except NoSuchElementException:
            wine["url"] = None
        
        wines.append(wine)
    
    return wines


def parse_wine_details(driver, wine_url):
    """Parse detailed wine information from the wine's detail page."""
    details = {}
    
    try:
        driver.get(wine_url)
        time.sleep(2)
        
        # Wait for wine facts table
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".wineFacts__wineFacts--2Ih8B"))
            )
        except TimeoutException:
            return details
        
        # Parse each wine fact row
        rows = driver.find_elements(By.CSS_SELECTOR, "[data-testid='wineFactRow']")
        for row in rows:
            try:
                label = row.find_element(By.CSS_SELECTOR, ".wineFacts__headerLabel--14doB").text.strip()
                value = row.find_element(By.CSS_SELECTOR, ".wineFacts__fact--3BAsi").text.strip()
                
                # Map French labels to English keys
                label_map = {
                    "Domaine viticole": "winery",
                    "Cépages": "grapes",
                    "Région": "region",
                    "Style de vin": "wine_style",
                    "Allergènes": "allergens",
                    "Description du vin": "description",
                }
                
                key = label_map.get(label, label.lower().replace(" ", "_"))
                details[key] = value
            except NoSuchElementException:
                pass
                
    except Exception as e:
        print(f"    Error fetching details: {e}")
    
    return details


def dismiss_cookie_consent(driver):
    """Dismiss cookie consent overlay by actually accepting cookies."""
    try:
        # Wait briefly for consent banner to appear
        time.sleep(1)
        
        # Try various cookie consent buttons (Accept is better - sets proper cookies)
        selectors = [
            "#onetrust-accept-btn-handler",  # OneTrust Accept All
            "#onetrust-reject-all-handler",  # OneTrust Reject All  
            "button[title='Accept All']",
            "button[title='Reject All']",
            ".onetrust-close-btn-handler",
            "#accept-cookies",
            "[data-testid='acceptCookies']",
        ]
        
        for sel in selectors:
            try:
                btns = driver.find_elements(By.CSS_SELECTOR, sel)
                if btns:
                    print(f"  Found consent button: {sel}")
                    driver.execute_script("arguments[0].click();", btns[0])
                    time.sleep(2)  # Wait for cookies to be set
                    return True
            except:
                pass
        
        print("  No consent button found, removing overlay...")
        # Fallback: remove overlay (but cookies may not be set)
        driver.execute_script("""
            var blocker = document.getElementById('consent-blocker');
            if (blocker) blocker.remove();
            var onetrust = document.getElementById('onetrust-consent-sdk');
            if (onetrust) onetrust.remove();
        """)
    except Exception as e:
        print(f"  Consent error: {e}")
    return False


def go_to_next_page(driver):
    """Click the next page button. Returns True if successful, False if no next page."""
    try:
        dismiss_cookie_consent(driver)
        
        # Try multiple selectors for the Next button
        selectors = [
            ".searchPagination-module__next--1Lpry a",
            "a[href*='page=2']",
            "a[href*='page=']",
        ]
        
        next_button = None
        for sel in selectors:
            try:
                buttons = driver.find_elements(By.CSS_SELECTOR, sel)
                print(f"  DEBUG: Selector '{sel}' found {len(buttons)} elements")
                if buttons:
                    # For page= links, find the "next" one
                    for btn in buttons:
                        href = btn.get_attribute("href")
                        text = btn.text.strip()
                        print(f"    -> href: {href}, text: '{text}'")
                        if "Suivant" in text or (href and "page=" in href):
                            next_button = btn
                            break
                if next_button:
                    break
            except:
                pass
        
        if next_button:
            # Scroll to button and click (maintains session, avoids 405 error)
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_button)
            time.sleep(0.5)
            driver.execute_script("arguments[0].click();", next_button)
            time.sleep(3)
            dismiss_cookie_consent(driver)
            return True
            
    except (NoSuchElementException, TimeoutException) as e:
        print(f"  DEBUG: Exception: {e}")
        return False
    return False


def scrape_vivino(start_url, max_pages=None, detailed=False):
    """
    Scrape wine data from Vivino starting from the given URL.
    
    Args:
        start_url: The Vivino explore URL to start from
        max_pages: Maximum number of pages to scrape (None for all pages)
        detailed: If True, fetch additional details from each wine's page
    
    Returns:
        List of wine dictionaries
    """
    driver = create_driver()
    all_wines = []
    page_count = 0
    
    try:
        print(f"Starting scrape from: {start_url}")
        driver.get(start_url)
        time.sleep(3)  # Initial page load
        dismiss_cookie_consent(driver)  # Dismiss OneTrust consent modal
        
        while True:
            page_count += 1
            print(f"Scraping page {page_count}...")
            
            # Parse wines on current page
            wines = parse_wine_cards(driver)
            all_wines.extend(wines)
            print(f"  Found {len(wines)} wines (total: {len(all_wines)})")
            
            # Check if we've reached max pages
            if max_pages and page_count >= max_pages:
                print(f"Reached maximum pages limit ({max_pages})")
                break
            
            # Try to go to next page
            if not go_to_next_page(driver):
                print("No more pages available")
                break
        
        # Fetch detailed info for each wine if requested
        if detailed:
            print(f"\nFetching detailed info for {len(all_wines)} wines...")
            for i, wine in enumerate(all_wines):
                if wine.get("url"):
                    print(f"  [{i+1}/{len(all_wines)}] {wine.get('vineyard', '')} - {wine.get('name', '')}")
                    details = parse_wine_details(driver, wine["url"])
                    wine.update(details)
                    time.sleep(1)  # Be nice to the server
            
    except Exception as e:
        print(f"Error during scraping: {e}")
    finally:
        driver.quit()
    
    return all_wines


def main():
    parser = argparse.ArgumentParser(description="Scrape wine data from Vivino")
    parser.add_argument("--detailed", action="store_true", 
                        help="Fetch additional details (grapes, region, style, etc.) from each wine's page")
    parser.add_argument("--max-pages", type=int, default=10,
                        help="Maximum number of pages to scrape (default: 10)")
    parser.add_argument("--url", type=str,
                        default="https://www.vivino.com/fr/explore?e=eJxLKbBNS8wpTlXLLbI11rNQy83MszVXy02ssDUzUEu2dQ0NUiuwNVQrS7ZVyy9KsU1JLU5Wy0-qtE1KLS6JL8hMzi5WK7fNK83JUSsviY4FqgRTRgDfaRz2",
                        help="Vivino explore URL to start from")
    args = parser.parse_args()
    
    # Scrape wines
    wines = scrape_vivino(args.url, max_pages=args.max_pages, detailed=args.detailed)
    
    # Output as JSON
    result = {
        "total_wines": len(wines),
        "wines": wines
    }
    
    print("\n" + "="*50)
    print("RESULTS (JSON):")
    print("="*50)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    # Also save to file
    with open("vivino_wines.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"\nResults saved to vivino_wines.json")
    
    return result


if __name__ == "__main__":
    main()

