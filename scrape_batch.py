#!/usr/bin/env python3
"""
Scrape batch information from YC company pages
"""

import time
import sqlite3
import re
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

class BatchScraper:
    def __init__(self, db_path='yc_companies.db'):
        self.db_path = db_path
        
    def setup_driver(self):
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        driver = webdriver.Chrome(options=chrome_options)
        return driver
    
    def extract_batch(self, driver, company_url=None):
        """Extract batch information from company page (assumes page is already loaded if company_url is None)"""
        try:
            if company_url:
                driver.get(company_url)
                time.sleep(3)
            
            page_text = driver.find_element(By.TAG_NAME, 'body').text
            
            # Pattern 1: "WINTER 2025", "SPRING 2024", etc.
            batch_patterns = [
                r'(WINTER|SPRING|SUMMER|FALL)\s+(\d{4})',
                r'(W|S|F)\s*(\d{2,4})',  # W25, S24, etc.
            ]
            
            for pattern in batch_patterns:
                matches = re.findall(pattern, page_text, re.IGNORECASE)
                if matches:
                    # Take the first match and format it
                    match = matches[0]
                    if isinstance(match, tuple):
                        season, year = match
                        # Format as "WINTER 2025" or "W25"
                        if len(year) == 4:
                            return f"{season.upper()} {year}"
                        elif len(year) == 2:
                            # Convert 2-digit year to 4-digit
                            year_int = int(year)
                            if year_int < 50:
                                year = f"20{year}"
                            else:
                                year = f"19{year}"
                            return f"{season.upper()} {year}"
                    else:
                        return match.upper()
            
            return None
        except Exception as e:
            error_msg = str(e)
            # Check if it's a session error
            if 'invalid session id' in error_msg.lower() or 'session deleted' in error_msg.lower():
                raise RuntimeError("Browser session crashed - need to restart driver")
            print(f"    Error extracting batch: {e}")
            return None
    
    def extract_location(self, driver, company_url=None):
        """Extract location information from company page (assumes page is already loaded if company_url is None)"""
        try:
            if company_url:
                driver.get(company_url)
                time.sleep(3)
            
            # Common false positives to filter out
            false_positives = {
                'jobs', 'job', 'hiring', 'remote', 'full-time', 'part-time', 'contract',
                'founder', 'co-founder', 'ceo', 'cto', 'engineer', 'developer', 'designer',
                'software', 'product', 'marketing', 'sales', 'business', 'operations',
                'apply', 'application', 'resume', 'cv', 'linkedin', 'email', 'contact',
                'about', 'team', 'careers', 'blog', 'news', 'press', 'media', 'privacy',
                'terms', 'cookie', 'policy', 'legal', 'support', 'help', 'faq', 'docs',
                'api', 'pricing', 'features', 'solutions', 'products', 'services',
                'winter', 'spring', 'summer', 'fall', 'batch', 'yc', 'ycombinator'
            }
            
            # Valid location patterns - must match these formats
            valid_location_pattern = re.compile(
                r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?),\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?(?:\s+[A-Z][a-z]+)?)$'
            )
            
            def is_valid_location(text):
                """Validate that text is actually a location"""
                if not text or len(text) < 3 or len(text) > 100:
                    return False
                
                # Must match location pattern (City, State/Country)
                if not valid_location_pattern.match(text):
                    return False
                
                # Split into parts
                parts = [p.strip() for p in text.split(',')]
                if len(parts) != 2:
                    return False
                
                city, state_country = parts[0], parts[1]
                
                # City should be 2-4 words max
                city_words = city.split()
                if len(city_words) < 1 or len(city_words) > 4:
                    return False
                
                # State/Country should be 1-3 words max
                state_words = state_country.split()
                if len(state_words) < 1 or len(state_words) > 3:
                    return False
                
                # Check for false positives in any part
                text_lower = text.lower()
                for fp in false_positives:
                    if fp in text_lower:
                        return False
                
                # Must not start with numbers
                if re.match(r'^\d', text):
                    return False
                
                # Must contain at least one comma (City, State format)
                if ',' not in text:
                    return False
                
                # Common valid location indicators
                valid_indicators = ['usa', 'united states', 'uk', 'united kingdom', 'canada', 
                                  'germany', 'france', 'spain', 'italy', 'netherlands', 
                                  'belgium', 'switzerland', 'austria', 'sweden', 'norway',
                                  'denmark', 'finland', 'poland', 'australia', 'new zealand',
                                  'japan', 'south korea', 'china', 'india', 'singapore',
                                  'israel', 'brazil', 'mexico', 'argentina', 'chile',
                                  'ca', 'ny', 'nyc', 'tx', 'wa', 'ma', 'il', 'fl', 'co',
                                  'pa', 'ga', 'nc', 'va', 'tn', 'az', 'or', 'nv', 'mn',
                                  'wi', 'mo', 'md', 'in', 'la', 'ky', 'sc', 'al', 'ok',
                                  'ct', 'ia', 'ut', 'ar', 'ms', 'ks', 'nm', 'ne', 'wv',
                                  'id', 'hi', 'nh', 'me', 'mt', 'ri', 'de', 'sd', 'nd',
                                  'ak', 'vt', 'wy', 'dc']
                
                # Check if state/country part contains valid indicators
                state_country_lower = state_country.lower()
                has_valid_indicator = any(indicator in state_country_lower for indicator in valid_indicators)
                
                # Also check for common city names
                common_cities = ['san francisco', 'new york', 'los angeles', 'boston', 
                               'seattle', 'austin', 'chicago', 'denver', 'miami', 
                               'portland', 'atlanta', 'dallas', 'houston', 'phoenix',
                               'philadelphia', 'san diego', 'detroit', 'minneapolis',
                               'tampa', 'orlando', 'sacramento', 'raleigh', 'nashville',
                               'indianapolis', 'columbus', 'charlotte', 'memphis',
                               'baltimore', 'kansas city', 'milwaukee', 'albuquerque',
                               'tucson', 'fresno', 'mesa', 'sacramento', 'atlanta',
                               'omaha', 'oklahoma city', 'tulsa', 'oakland', 'minneapolis',
                               'wichita', 'arlington', 'bakersfield', 'new orleans',
                               'honolulu', 'anaheim', 'santa ana', 'st. louis', 'riverside',
                               'corpus christi', 'lexington', 'stockton', 'henderson',
                               'saint paul', 'st. paul', 'santa clarita', 'fort wayne',
                               'birmingham', 'fayetteville', 'richmond', 'rochester',
                               'spokane', 'grand rapids', 'tacoma', 'irvine', 'fontana',
                               'fremont', 'boise', 'richmond', 'baton rouge', 'san bernardino',
                               'london', 'berlin', 'paris', 'amsterdam', 'stockholm',
                               'copenhagen', 'zurich', 'dublin', 'madrid', 'barcelona',
                               'milan', 'rome', 'vienna', 'prague', 'warsaw', 'helsinki',
                               'oslo', 'brussels', 'lisbon', 'athens', 'dubai', 'hong kong',
                               'singapore', 'tokyo', 'sydney', 'melbourne', 'toronto',
                               'vancouver', 'montreal', 'calgary', 'ottawa', 'edmonton',
                               'tel aviv', 'bangalore', 'mumbai', 'delhi', 'hyderabad',
                               'chennai', 'pune', 'kolkata', 'jakarta', 'manila', 'bangkok',
                               'hanoi', 'seoul', 'taipei', 'kuala lumpur', 'mexico city',
                               'são paulo', 'rio de janeiro', 'buenos aires', 'santiago',
                               'lima', 'bogotá', 'caracas', 'montevideo']
                
                city_lower = city.lower()
                has_common_city = any(c in city_lower for c in common_cities)
                
                # Must have either valid indicator or common city name
                return has_valid_indicator or has_common_city
            
            # Method 1: Try to find location in structured data/metadata
            try:
                # Look for location in JSON data
                json_data = driver.execute_script("""
                    if (window.__NEXT_DATA__) {
                        return JSON.stringify(window.__NEXT_DATA__);
                    }
                    return null;
                """)
                
                if json_data:
                    data = json.loads(json_data)
                    
                    # Recursively search for location
                    def find_location(obj, depth=0):
                        if depth > 15:
                            return None
                        if isinstance(obj, dict):
                            # Check common location keys
                            for key in ['location', 'city', 'cityName', 'city_name', 'headquarters', 'hq', 'hqLocation']:
                                if key in obj and obj[key]:
                                    loc = str(obj[key]).strip()
                                    if is_valid_location(loc):
                                        return loc
                            # Recursively search
                            for key, value in obj.items():
                                result = find_location(value, depth+1)
                                if result:
                                    return result
                        elif isinstance(obj, list):
                            for item in obj:
                                result = find_location(item, depth+1)
                                if result:
                                    return result
                        return None
                    
                    location = find_location(data)
                    if location:
                        return location
            except:
                pass
            
            # Method 2: Extract from page text with strict validation
            try:
                page_text = driver.find_element(By.TAG_NAME, 'body').text
                
                # Look for location patterns in text - strict format only
                # Pattern: "City, State" or "City, Country" - must be exact match
                location_patterns = [
                    r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?),\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?(?:\s+[A-Z][a-z]+)?)\b',  # City, State/Country
                ]
                
                for pattern in location_patterns:
                    matches = re.finditer(pattern, page_text)
                    for match in matches:
                        location = match.group(0).strip()
                        if is_valid_location(location):
                            return location
            except:
                pass
            
            # Method 3: Look for location in specific DOM elements
            try:
                # Common selectors for location
                location_selectors = [
                    "[class*='location']",
                    "[class*='Location']",
                    "[class*='city']",
                    "[class*='City']",
                    "[data-location]",
                    "[data-city]",
                ]
                
                for selector in location_selectors:
                    try:
                        elements = driver.find_elements(By.CSS_SELECTOR, selector)
                        for elem in elements:
                            text = elem.text.strip()
                            if is_valid_location(text):
                                return text
                    except:
                        continue
            except:
                pass
            
            return None
        except Exception as e:
            error_msg = str(e)
            # Check if it's a session error
            if 'invalid session id' in error_msg.lower() or 'session deleted' in error_msg.lower():
                raise RuntimeError("Browser session crashed - need to restart driver")
            print(f"    Error extracting location: {e}")
            return None
    
    def scrape_all(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get companies without batch data or location
        cursor.execute('''
            SELECT id, name, yc_url 
            FROM companies
            WHERE yc_url LIKE "%/companies/%" 
            AND yc_url NOT LIKE "%?%" 
            AND yc_url NOT LIKE "%industry=%"
            AND yc_url NOT LIKE "%batch=%"
            AND (batch IS NULL OR batch = "" OR location IS NULL OR location = "")
            ORDER BY name
        ''')
        companies = cursor.fetchall()
        conn.close()
        
        print(f"Found {len(companies)} companies without batch or location data\n")
        
        if not companies:
            print("All companies already have batch and location data!")
            return
        
        driver = self.setup_driver()
        updated_count = 0
        
        try:
            for i, (company_id, company_name, yc_url) in enumerate(companies, 1):
                clean_name = company_name.split('\n')[0]
                print(f"[{i}/{len(companies)}] {clean_name}")
                
                batch = None
                location = None
                
                try:
                    batch = self.extract_batch(driver, yc_url)
                except RuntimeError as e:
                    if "Browser session crashed" in str(e):
                        print(f"  ⚠️  Browser session crashed, restarting driver...")
                        try:
                            driver.quit()
                        except:
                            pass
                        driver = self.setup_driver()
                        print(f"  ✓ Driver restarted, retrying...")
                        try:
                            batch = self.extract_batch(driver, yc_url)
                        except Exception as retry_e:
                            print(f"    Error on retry: {retry_e}")
                            batch = None
                    else:
                        raise
                
                # Extract location (reuse the same page load - pass None to skip reloading)
                location = None
                try:
                    if batch is not None:
                        # Page already loaded, reuse it
                        location = self.extract_location(driver, None)
                    else:
                        # Batch extraction failed, try location extraction with fresh page load
                        location = self.extract_location(driver, yc_url)
                except RuntimeError as e:
                    if "Browser session crashed" in str(e):
                        print(f"  ⚠️  Browser session crashed during location extraction, restarting driver...")
                        try:
                            driver.quit()
                        except:
                            pass
                        driver = self.setup_driver()
                        print(f"  ✓ Driver restarted, retrying location...")
                        try:
                            location = self.extract_location(driver, yc_url)
                        except Exception as retry_e:
                            print(f"    Error on retry: {retry_e}")
                            location = None
                    else:
                        raise
                
                # Update database with batch and/or location
                if batch or location:
                    conn = sqlite3.connect(self.db_path)
                    cursor = conn.cursor()
                    
                    # Check what needs updating
                    cursor.execute('SELECT batch, location FROM companies WHERE id = ?', (company_id,))
                    existing = cursor.fetchone()
                    existing_batch, existing_location = existing if existing else (None, None)
                    
                    # Only update if we have new data
                    if batch and batch != existing_batch:
                        cursor.execute('''
                            UPDATE companies 
                            SET batch = ? 
                            WHERE id = ?
                        ''', (batch, company_id))
                        print(f"  ✅ Batch: {batch}")
                        updated_count += 1
                    
                    if location and location != existing_location:
                        cursor.execute('''
                            UPDATE companies 
                            SET location = ? 
                            WHERE id = ?
                        ''', (location, company_id))
                        print(f"  ✅ Location: {location}")
                        if not batch:
                            updated_count += 1
                    elif not location:
                        print(f"  ⚠️  No location found")
                    
                    conn.commit()
                    conn.close()
                else:
                    print(f"  ⚠️  No batch or location found")
                
                time.sleep(2)  # Be respectful
        finally:
            try:
                driver.quit()
            except:
                pass
        
        print(f"\n✅ Done! Updated {updated_count}/{len(companies)} companies with batch and/or location data")

if __name__ == "__main__":
    scraper = BatchScraper()
    scraper.scrape_all()

