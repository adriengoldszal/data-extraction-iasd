"""
Selenium Web Scraper with Click Interactions
============================================

This script demonstrates how to build a web scraper using Selenium that can:
- Handle dynamic content loading
- Click on buttons, links, and other interactive elements
- Wait for elements to load
- Extract data from multiple pages
- Handle common web scraping challenges

Example target: Vivino wine website
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
import time
import pandas as pd
import json
from typing import List, Dict, Optional
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class WebScraper:
    """
    A flexible web scraper using Selenium with click interaction capabilities
    """
    
    def __init__(self, headless: bool = False, wait_timeout: int = 10):
        """
        Initialize the scraper with Chrome WebDriver
        
        Args:
            headless: Run browser in headless mode (no GUI)
            wait_timeout: Default timeout for waiting for elements
        """
        self.wait_timeout = wait_timeout
        self.driver = self._setup_driver(headless)
        self.wait = WebDriverWait(self.driver, wait_timeout)
        
    def _setup_driver(self, headless: bool) -> webdriver.Chrome:
        """Set up Chrome WebDriver with optimal settings"""
        chrome_options = Options()
        
        if headless:
            chrome_options.add_argument("--headless")
        
        # Common options for better scraping
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Set user agent to avoid detection
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        driver = webdriver.Chrome(options=chrome_options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        return driver
    
    def safe_click(self, element_locator: tuple, scroll_to_element: bool = True) -> bool:
        """
        Safely click on an element with multiple fallback strategies
        
        Args:
            element_locator: Tuple of (By.METHOD, "selector")
            scroll_to_element: Whether to scroll to element before clicking
            
        Returns:
            bool: True if click was successful, False otherwise
        """
        try:
            # Wait for element to be clickable
            element = self.wait.until(EC.element_to_be_clickable(element_locator))
            
            if scroll_to_element:
                self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
                time.sleep(0.5)  # Brief pause after scrolling
            
            # Try regular click first
            try:
                element.click()
                return True
            except ElementClickInterceptedException:
                # If regular click fails, try JavaScript click
                logger.warning("Regular click intercepted, trying JavaScript click")
                self.driver.execute_script("arguments[0].click();", element)
                return True
                
        except TimeoutException:
            logger.error(f"Element not found or not clickable: {element_locator}")
            return False
        except Exception as e:
            logger.error(f"Error clicking element {element_locator}: {str(e)}")
            return False
    
    def wait_for_element(self, locator: tuple, timeout: Optional[int] = None) -> Optional[object]:
        """
        Wait for an element to be present and return it
        
        Args:
            locator: Tuple of (By.METHOD, "selector")
            timeout: Custom timeout (uses default if None)
            
        Returns:
            WebElement or None if not found
        """
        try:
            wait_time = timeout or self.wait_timeout
            element = WebDriverWait(self.driver, wait_time).until(
                EC.presence_of_element_located(locator)
            )
            return element
        except TimeoutException:
            logger.warning(f"Element not found within {wait_time} seconds: {locator}")
            return None
    
    def extract_text_safe(self, locator: tuple, default: str = "") -> str:
        """
        Safely extract text from an element
        
        Args:
            locator: Tuple of (By.METHOD, "selector")
            default: Default value if element not found
            
        Returns:
            str: Element text or default value
        """
        try:
            element = self.driver.find_element(*locator)
            return element.text.strip()
        except NoSuchElementException:
            return default
    
    def scroll_and_load_more(self, load_more_button_locator: tuple, max_clicks: int = 5) -> int:
        """
        Scroll down and click "Load More" buttons to load additional content
        
        Args:
            load_more_button_locator: Locator for the load more button
            max_clicks: Maximum number of times to click load more
            
        Returns:
            int: Number of successful clicks
        """
        clicks = 0
        
        for i in range(max_clicks):
            try:
                # Scroll to bottom first
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                
                # Try to find and click load more button
                if self.safe_click(load_more_button_locator):
                    clicks += 1
                    logger.info(f"Clicked 'Load More' button {clicks} times")
                    time.sleep(3)  # Wait for content to load
                else:
                    logger.info("No more 'Load More' button found or clickable")
                    break
                    
            except Exception as e:
                logger.error(f"Error during load more process: {str(e)}")
                break
                
        return clicks


class VivinoScraper(WebScraper):
    """
    Specific scraper for Vivino wine website
    Demonstrates practical clicking and data extraction
    """
    
    def __init__(self, headless: bool = False):
        super().__init__(headless)
        self.base_url = "https://www.vivino.com"
        
    def search_wines(self, search_term: str, max_results: int = 50) -> List[Dict]:
        """
        Search for wines and extract data by clicking through results
        
        Args:
            search_term: Wine name or type to search for
            max_results: Maximum number of wine results to collect
            
        Returns:
            List of wine data dictionaries
        """
        wines_data = []
        
        try:
            # Navigate to Vivino
            logger.info(f"Navigating to Vivino...")
            self.driver.get(self.base_url)
            
            # Accept cookies if popup appears
            cookie_button = (By.XPATH, "//button[contains(text(), 'Accept') or contains(text(), 'OK')]")
            if self.wait_for_element(cookie_button, timeout=3):
                self.safe_click(cookie_button)
                logger.info("Accepted cookies")
            
            # Find and use search box
            search_box = (By.CSS_SELECTOR, "input[placeholder*='Search']")
            search_element = self.wait_for_element(search_box)
            
            if search_element:
                search_element.clear()
                search_element.send_keys(search_term)
                
                # Click search button or press enter
                search_button = (By.CSS_SELECTOR, "button[type='submit']")
                if not self.safe_click(search_button):
                    # Fallback: press enter
                    from selenium.webdriver.common.keys import Keys
                    search_element.send_keys(Keys.RETURN)
                
                logger.info(f"Searched for: {search_term}")
                time.sleep(3)
                
                # Extract wine data from search results
                wines_data = self._extract_wine_cards(max_results)
                
            else:
                logger.error("Could not find search box")
                
        except Exception as e:
            logger.error(f"Error during wine search: {str(e)}")
            
        return wines_data
    
    def _extract_wine_cards(self, max_results: int) -> List[Dict]:
        """
        Extract data from wine cards on the search results page
        
        Args:
            max_results: Maximum number of wines to extract
            
        Returns:
            List of wine data dictionaries
        """
        wines_data = []
        
        try:
            # Wait for wine cards to load
            wine_cards_locator = (By.CSS_SELECTOR, "[class*='wine-card'], [class*='wineCard']")
            self.wait_for_element(wine_cards_locator, timeout=10)
            
            # Load more results if needed
            load_more_locator = (By.XPATH, "//button[contains(text(), 'Show more') or contains(text(), 'Load more')]")
            self.scroll_and_load_more(load_more_locator, max_clicks=3)
            
            # Find all wine cards
            wine_cards = self.driver.find_elements(*wine_cards_locator)
            logger.info(f"Found {len(wine_cards)} wine cards")
            
            for i, card in enumerate(wine_cards[:max_results]):
                try:
                    wine_data = self._extract_single_wine_data(card)
                    if wine_data:
                        wines_data.append(wine_data)
                        logger.info(f"Extracted wine {i+1}: {wine_data.get('name', 'Unknown')}")
                        
                except Exception as e:
                    logger.warning(f"Error extracting wine card {i}: {str(e)}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error extracting wine cards: {str(e)}")
            
        return wines_data
    
    def _extract_single_wine_data(self, card_element) -> Dict:
        """
        Extract data from a single wine card element
        
        Args:
            card_element: WebElement of the wine card
            
        Returns:
            Dictionary with wine data
        """
        wine_data = {}
        
        try:
            # Wine name
            name_selectors = [
                ".//a[contains(@class, 'wine-card__name')]",
                ".//h3//a",
                ".//a[contains(@href, '/w/')]"
            ]
            
            for selector in name_selectors:
                try:
                    name_element = card_element.find_element(By.XPATH, selector)
                    wine_data['name'] = name_element.text.strip()
                    wine_data['url'] = name_element.get_attribute('href')
                    break
                except NoSuchElementException:
                    continue
            
            # Rating
            rating_selectors = [
                ".//div[contains(@class, 'average__number')]",
                ".//span[contains(@class, 'rating')]"
            ]
            
            for selector in rating_selectors:
                try:
                    rating_element = card_element.find_element(By.XPATH, selector)
                    wine_data['rating'] = rating_element.text.strip()
                    break
                except NoSuchElementException:
                    continue
            
            # Price
            price_selectors = [
                ".//span[contains(@class, 'price')]",
                ".//div[contains(text(), '$')]"
            ]
            
            for selector in price_selectors:
                try:
                    price_element = card_element.find_element(By.XPATH, selector)
                    wine_data['price'] = price_element.text.strip()
                    break
                except NoSuchElementException:
                    continue
            
            # Winery
            winery_selectors = [
                ".//a[contains(@class, 'winery')]",
                ".//span[contains(@class, 'winery')]"
            ]
            
            for selector in winery_selectors:
                try:
                    winery_element = card_element.find_element(By.XPATH, selector)
                    wine_data['winery'] = winery_element.text.strip()
                    break
                except NoSuchElementException:
                    continue
            
        except Exception as e:
            logger.warning(f"Error extracting wine data: {str(e)}")
            
        return wine_data
    
    def get_wine_details(self, wine_url: str) -> Dict:
        """
        Navigate to a specific wine page and extract detailed information
        
        Args:
            wine_url: URL of the wine detail page
            
        Returns:
            Dictionary with detailed wine information
        """
        wine_details = {}
        
        try:
            logger.info(f"Navigating to wine details: {wine_url}")
            self.driver.get(wine_url)
            
            # Wait for page to load
            time.sleep(3)
            
            # Extract detailed information
            wine_details['name'] = self.extract_text_safe((By.CSS_SELECTOR, "h1"))
            wine_details['rating'] = self.extract_text_safe((By.CSS_SELECTOR, "[class*='rating'] [class*='average']"))
            wine_details['price'] = self.extract_text_safe((By.CSS_SELECTOR, "[class*='price']"))
            wine_details['description'] = self.extract_text_safe((By.CSS_SELECTOR, "[class*='description']"))
            
            # Click on "Show more" for additional details if available
            show_more_locator = (By.XPATH, "//button[contains(text(), 'Show more') or contains(text(), 'Read more')]")
            if self.safe_click(show_more_locator):
                time.sleep(2)
                wine_details['full_description'] = self.extract_text_safe((By.CSS_SELECTOR, "[class*='description']"))
            
        except Exception as e:
            logger.error(f"Error extracting wine details: {str(e)}")
            
        return wine_details
    
    def close(self):
        """Close the browser driver"""
        if self.driver:
            self.driver.quit()
            logger.info("Browser closed")


def main():
    """
    Example usage of the Vivino scraper
    """
    scraper = VivinoScraper(headless=False)  # Set to True for headless mode
    
    try:
        # Search for wines
        wines = scraper.search_wines("Bordeaux", max_results=20)
        
        # Save results to JSON
        with open('vivino_wines.json', 'w', encoding='utf-8') as f:
            json.dump(wines, f, indent=2, ensure_ascii=False)
        
        # Save to CSV
        if wines:
            df = pd.DataFrame(wines)
            df.to_csv('vivino_wines.csv', index=False)
            logger.info(f"Saved {len(wines)} wines to CSV and JSON files")
        
        # Example: Get detailed info for first wine
        if wines and wines[0].get('url'):
            details = scraper.get_wine_details(wines[0]['url'])
            logger.info(f"Wine details: {details}")
            
    except Exception as e:
        logger.error(f"Error in main execution: {str(e)}")
        
    finally:
        scraper.close()


if __name__ == "__main__":
    main()
