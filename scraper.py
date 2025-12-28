#!/usr/bin/env python3
"""
Y Combinator Companies Scraper
Scrapes hiring companies from YC directory and stores in SQLite database
"""

import time
import sqlite3
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import json

class YCScraper:
    def __init__(self, db_path='yc_companies.db'):
        self.db_path = db_path
        self.companies = []
        self.setup_database()
        
    def setup_database(self):
        """Create database and table if they don't exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS companies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                batch TEXT,
                description TEXT,
                website TEXT,
                location TEXT,
                industry TEXT,
                is_hiring BOOLEAN DEFAULT 1,
                yc_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(name, batch)
            )
        ''')
        
        conn.commit()
        conn.close()
        print(f"Database initialized at {self.db_path}")
    
    def setup_driver(self):
        """Setup Chrome WebDriver with appropriate options"""
        chrome_options = Options()
        chrome_options.add_argument('--headless')  # Run in background
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        try:
            driver = webdriver.Chrome(options=chrome_options)
            return driver
        except Exception as e:
            print(f"Error setting up Chrome driver: {e}")
            print("Make sure ChromeDriver is installed and in PATH")
            raise
    
    def scrape_companies(self, url):
        """Scrape companies from YC directory"""
        driver = self.setup_driver()
        
        try:
            print(f"Navigating to {url}...")
            driver.get(url)
            
            # Wait for page to load
            time.sleep(5)
            
            # Scroll to load more companies (infinite scroll)
            print("Scrolling to load companies...")
            last_height = driver.execute_script("return document.body.scrollHeight")
            scroll_attempts = 0
            max_scrolls = 10  # Limit scrolling to avoid infinite loop
            
            while scroll_attempts < max_scrolls:
                # Scroll down
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)  # Wait for content to load
                
                # Check if new content loaded
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height
                scroll_attempts += 1
            
            # Try to find company cards/links
            # YC uses various selectors - let's try multiple approaches
            print("Extracting company data...")
            
            # Method 1: Look for company links
            company_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/companies/']")
            
            # Method 2: Look for company cards
            company_cards = driver.find_elements(By.CSS_SELECTOR, "[class*='company'], [class*='Company']")
            
            # Method 3: Try to find by data attributes
            company_elements = driver.find_elements(By.CSS_SELECTOR, "[data-company], [data-name]")
            
            print(f"Found {len(company_links)} company links")
            print(f"Found {len(company_cards)} company cards")
            print(f"Found {len(company_elements)} company elements")
            
            # Extract company information
            companies_data = []
            seen_companies = set()
            
            # Process company links
            for link in company_links:
                try:
                    href = link.get_attribute('href')
                    if not href or '/companies/' not in href:
                        continue
                    
                    # Extract company name from link or text
                    name = link.text.strip()
                    if not name:
                        # Try to get name from href
                        name = href.split('/companies/')[-1].split('?')[0].replace('-', ' ').title()
                    
                    if name and name not in seen_companies:
                        seen_companies.add(name)
                        companies_data.append({
                            'name': name,
                            'yc_url': href,
                            'website': None,
                            'batch': None,
                            'description': None,
                            'location': None,
                            'industry': None
                        })
                except Exception as e:
                    continue
            
            # Try to extract JSON data from Next.js page
            print("Trying to extract JSON data from page...")
            try:
                json_data = driver.execute_script("""
                    if (window.__NEXT_DATA__) {
                        return JSON.stringify(window.__NEXT_DATA__);
                    }
                    return null;
                """)
                
                if json_data:
                    data = json.loads(json_data)
                    parsed_companies = self._parse_json_data(data)
                    if parsed_companies:
                        # Merge with existing data, avoiding duplicates
                        existing_names = {c['name'] for c in companies_data}
                        for company in parsed_companies:
                            if company['name'] not in existing_names:
                                companies_data.append(company)
            except Exception as e:
                print(f"Error parsing JSON data: {e}")
            
            # Also try to extract from visible elements with better selectors
            try:
                # Wait for company list to be visible
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                
                # Try different selectors for company information
                all_links = driver.find_elements(By.TAG_NAME, "a")
                for link in all_links:
                    href = link.get_attribute('href')
                    if href and '/companies/' in href and href != url:
                        try:
                            # Get parent element to extract more info
                            parent = link.find_element(By.XPATH, "./..")
                            text_content = parent.text.strip()
                            
                            # Extract company name
                            name = link.text.strip()
                            if not name:
                                # Try to extract from href
                                name = href.split('/companies/')[-1].split('?')[0].replace('-', ' ').title()
                            
                            if name and name not in seen_companies:
                                seen_companies.add(name)
                                
                                # Try to extract batch, location, etc. from text
                                batch = None
                                location = None
                                description = None
                                
                                # Look for batch pattern (e.g., "S25", "W24", "F25")
                                batch_match = re.search(r'(S|W|F|Summer|Winter|Fall|Spring)\s*(\d{2,4})', text_content, re.IGNORECASE)
                                if batch_match:
                                    batch = batch_match.group(0)
                                
                                companies_data.append({
                                    'name': name,
                                    'yc_url': href,
                                    'website': None,
                                    'batch': batch,
                                    'description': description,
                                    'location': location,
                                    'industry': None
                                })
                        except:
                            continue
            except Exception as e:
                print(f"Error extracting from elements: {e}")
            
            self.companies = companies_data
            print(f"Extracted {len(self.companies)} companies")
            
            return companies_data
            
        except Exception as e:
            print(f"Error during scraping: {e}")
            import traceback
            traceback.print_exc()
            return []
        finally:
            driver.quit()
    
    def _parse_json_data(self, data):
        """Parse JSON data structure to extract company information"""
        companies = []
        
        def extract_companies(obj, path=""):
            """Recursively search for company data in JSON"""
            if isinstance(obj, dict):
                # Look for common patterns
                if 'name' in obj and ('batch' in obj or 'ycBatch' in obj):
                    company = {
                        'name': obj.get('name', ''),
                        'batch': obj.get('batch') or obj.get('ycBatch') or obj.get('batchName'),
                        'description': obj.get('description') or obj.get('oneLiner') or obj.get('tagline'),
                        'website': obj.get('website') or obj.get('url'),
                        'location': obj.get('location') or obj.get('hqLocation') or obj.get('city'),
                        'industry': obj.get('industry') or obj.get('category'),
                        'yc_url': obj.get('ycUrl') or obj.get('url')
                    }
                    if company['name']:
                        companies.append(company)
                
                # Look for arrays of companies
                if 'companies' in obj:
                    for item in obj['companies']:
                        extract_companies(item, path + ".companies")
                
                # Look for props/pageProps which Next.js uses
                if 'props' in obj:
                    extract_companies(obj['props'], path + ".props")
                if 'pageProps' in obj:
                    extract_companies(obj['pageProps'], path + ".pageProps")
                
                # Recursively search all values
                for key, value in obj.items():
                    if key not in ['name', 'batch', 'description', 'website', 'location', 'industry']:
                        extract_companies(value, path + f".{key}")
                        
            elif isinstance(obj, list):
                for item in obj:
                    extract_companies(item, path + "[]")
        
        extract_companies(data)
        return companies
    
    def save_to_database(self):
        """Save scraped companies to database"""
        if not self.companies:
            print("No companies to save")
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        saved_count = 0
        for company in self.companies:
            try:
                cursor.execute('''
                    INSERT OR REPLACE INTO companies 
                    (name, batch, description, website, location, industry, is_hiring, yc_url)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    company.get('name'),
                    company.get('batch'),
                    company.get('description'),
                    company.get('website'),
                    company.get('location'),
                    company.get('industry'),
                    company.get('is_hiring', True),
                    company.get('yc_url')
                ))
                saved_count += 1
            except Exception as e:
                print(f"Error saving company {company.get('name')}: {e}")
        
        conn.commit()
        conn.close()
        print(f"Saved {saved_count} companies to database")

if __name__ == "__main__":
    url = "https://www.ycombinator.com/companies/?batch=Fall%202025&batch=Summer%202025&batch=Spring%202025&batch=Winter%202025&batch=Fall%202024&batch=Winter%202026&batch=Spring%202026&isHiring=true"
    
    scraper = YCScraper()
    scraper.scrape_companies(url)
    scraper.save_to_database()
    
    print("\nScraping complete!")

