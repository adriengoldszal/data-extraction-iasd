# Selenium Web Scraper with Click Interactions

A comprehensive Selenium-based web scraper that demonstrates how to handle dynamic websites requiring user interactions like clicking buttons, loading more content, and navigating through pages.

## Features

- **Click Interactions**: Safe clicking with fallback strategies (regular click → JavaScript click)
- **Dynamic Content Loading**: Handle "Load More" buttons and infinite scroll
- **Robust Element Waiting**: Wait for elements to be present and clickable
- **Error Handling**: Comprehensive exception handling and logging
- **Anti-Detection**: Browser settings to avoid bot detection
- **Data Export**: Save results to JSON and CSV formats

## Installation

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Install ChromeDriver:
   - **Option A**: Download from [ChromeDriver](https://chromedriver.chromium.org/) and add to PATH
   - **Option B**: Use webdriver-manager (recommended):
```python
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)
```

## Usage

### Basic Example

```python
from vivino_scaper import VivinoScraper

# Create scraper instance
scraper = VivinoScraper(headless=False)  # Set True for headless mode

try:
    # Search for wines
    wines = scraper.search_wines("Bordeaux", max_results=20)
    print(f"Found {len(wines)} wines")
    
    # Get detailed info for a specific wine
    if wines and wines[0].get('url'):
        details = scraper.get_wine_details(wines[0]['url'])
        print(details)
        
finally:
    scraper.close()
```

### Key Scraping Techniques Demonstrated

#### 1. Safe Clicking with Fallbacks
```python
def safe_click(self, element_locator: tuple, scroll_to_element: bool = True) -> bool:
    try:
        element = self.wait.until(EC.element_to_be_clickable(element_locator))
        
        if scroll_to_element:
            self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
        
        # Try regular click first
        element.click()
        return True
    except ElementClickInterceptedException:
        # Fallback to JavaScript click
        self.driver.execute_script("arguments[0].click();", element)
        return True
```

#### 2. Loading More Content
```python
def scroll_and_load_more(self, load_more_button_locator: tuple, max_clicks: int = 5):
    for i in range(max_clicks):
        # Scroll to bottom
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        
        # Click load more button
        if self.safe_click(load_more_button_locator):
            time.sleep(3)  # Wait for content to load
        else:
            break
```

#### 3. Robust Element Finding
```python
def wait_for_element(self, locator: tuple, timeout: Optional[int] = None):
    try:
        wait_time = timeout or self.wait_timeout
        element = WebDriverWait(self.driver, wait_time).until(
            EC.presence_of_element_located(locator)
        )
        return element
    except TimeoutException:
        return None
```

## Common Selenium Patterns for Clicking

### 1. Basic Element Interaction
```python
# Find and click a button
button = driver.find_element(By.CSS_SELECTOR, "button.submit")
button.click()

# Click with explicit wait
button = WebDriverWait(driver, 10).until(
    EC.element_to_be_clickable((By.ID, "submit-btn"))
)
button.click()
```

### 2. Handling Dynamic Content
```python
# Wait for element to appear after AJAX call
element = WebDriverWait(driver, 10).until(
    EC.presence_of_element_located((By.CLASS_NAME, "dynamic-content"))
)

# Handle elements that appear/disappear
try:
    popup_close = driver.find_element(By.CSS_SELECTOR, ".popup .close")
    popup_close.click()
except NoSuchElementException:
    pass  # Popup not present, continue
```

### 3. Advanced Interactions
```python
from selenium.webdriver.common.action_chains import ActionChains

# Hover over element before clicking
element = driver.find_element(By.CSS_SELECTOR, ".dropdown-trigger")
ActionChains(driver).move_to_element(element).click().perform()

# Double click
ActionChains(driver).double_click(element).perform()

# Right click (context menu)
ActionChains(driver).context_click(element).perform()
```

### 4. JavaScript Execution
```python
# Click via JavaScript (when regular click fails)
element = driver.find_element(By.ID, "stubborn-button")
driver.execute_script("arguments[0].click();", element)

# Scroll to element
driver.execute_script("arguments[0].scrollIntoView(true);", element)

# Execute custom JavaScript
driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
```

## Troubleshooting

### Common Issues and Solutions

1. **Element not clickable**: Element is covered by another element
   - Solution: Scroll to element, wait longer, or use JavaScript click

2. **Stale element reference**: Element was found but DOM changed
   - Solution: Re-find the element before interacting

3. **Timeout exceptions**: Element takes too long to load
   - Solution: Increase wait timeout or add explicit waits

4. **Bot detection**: Website blocks automated browsers
   - Solution: Use stealth settings, rotate user agents, add delays

### Browser Configuration Tips

```python
chrome_options = Options()

# Stealth settings
chrome_options.add_argument("--disable-blink-features=AutomationControlled")
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
chrome_options.add_experimental_option('useAutomationExtension', False)

# Performance settings
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-gpu")

# Custom user agent
chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")
```

## File Structure

```
data-extraction-iasd/
├── vivino_scaper.py      # Main scraper implementation
├── requirements.txt      # Python dependencies
├── README.md            # This file
├── vivino_wines.json    # Output: scraped data in JSON format
└── vivino_wines.csv     # Output: scraped data in CSV format
```

## Extending the Scraper

To adapt this scraper for other websites:

1. **Inherit from WebScraper class**:
```python
class MyCustomScraper(WebScraper):
    def __init__(self):
        super().__init__()
        self.base_url = "https://example.com"
```

2. **Update selectors**: Modify CSS selectors and XPath expressions for target website

3. **Customize extraction logic**: Implement site-specific data extraction methods

4. **Handle site-specific interactions**: Add methods for site-specific clicking patterns

## Legal and Ethical Considerations

- Always check the website's `robots.txt` and terms of service
- Respect rate limits and add appropriate delays
- Don't overload servers with too many concurrent requests
- Consider using official APIs when available