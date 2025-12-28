#!/usr/bin/env python3
"""
Improved Y Combinator Companies Scraper
Better extraction of company data from YC directory
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

class ImprovedYCScraper:
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
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        try:
            driver = webdriver.Chrome(options=chrome_options)
            return driver
        except Exception as e:
            print(f"Error setting up Chrome driver: {e}")
            raise
    
    def is_valid_company_url(self, url):
        """Check if URL is a valid company page (not filter/search page)"""
        if not url or '/companies/' not in url:
            return False
        # Exclude filter/search URLs
        if '?' in url and ('batch=' in url or 'industry=' in url or 'isHiring=' in url):
            return False
        # Exclude if it's just /companies/ with no company name
        parts = url.split('/companies/')
        if len(parts) < 2:
            return False
        company_part = parts[1].split('?')[0].strip()
        if not company_part or len(company_part) < 2:
            return False
        return True
    
    def extract_company_info(self, element, href):
        """Extract company information from an element"""
        try:
            # Get text content
            text = element.text.strip()
            if not text:
                return None
            
            # Extract company name (first line, before location)
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            if not lines:
                return None
            
            name = lines[0]
            
            # Skip if it looks like a filter/header
            if name.upper() == name and len(name.split()) <= 2:
                return None
            
            # Extract location (look for patterns like "City, State, Country")
            location = None
            for line in lines:
                if re.search(r'[A-Z][a-z]+,?\s+[A-Z]{2},?\s+[A-Z]{2,}', line):
                    location = line
                    break
            
            # Extract batch (look for patterns like "WINTER 2026", "S25", etc.)
            batch = None
            batch_patterns = [
                r'(WINTER|SUMMER|SPRING|FALL)\s+(\d{4})',
                r'(W|S|F)\s*(\d{2,4})',
            ]
            for line in lines:
                for pattern in batch_patterns:
                    match = re.search(pattern, line, re.IGNORECASE)
                    if match:
                        batch = match.group(0).upper()
                        break
                if batch:
                    break
            
            # Extract description (usually the second line if not location/batch)
            description = None
            for line in lines[1:]:
                if line != location and not re.search(batch_patterns[0], line, re.IGNORECASE):
                    if len(line) > 20:  # Likely a description
                        description = line
                        break
            
            # Extract industry (look for common industry keywords)
            industry = None
            industries = ['CONSUMER', 'B2B', 'FINTECH', 'HEALTHCARE', 'EDUCATION', 
                         'ENTERPRISE', 'SAAS', 'AI', 'ML', 'GAMING']
            for line in lines:
                for ind in industries:
                    if ind in line.upper():
                        industry = ind
                        break
                if industry:
                    break
            
            return {
                'name': name,
                'yc_url': href,
                'website': None,
                'batch': batch,
                'description': description,
                'location': location,
                'industry': industry
            }
        except Exception as e:
            return None
    
    def scrape_companies(self, url):
        """Scrape companies from YC directory"""
        driver = self.setup_driver()
        
        try:
            print(f"Navigating to {url}...")
            driver.get(url)
            
            # Wait for page to load
            time.sleep(5)
            
            # Scroll to load more companies
            print("Scrolling to load companies...")
            last_height = driver.execute_script("return document.body.scrollHeight")
            scroll_attempts = 0
            max_scrolls = 15
            
            while scroll_attempts < max_scrolls:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height
                scroll_attempts += 1
            
            print("Extracting company data...")
            
            # Find all company links
            all_links = driver.find_elements(By.TAG_NAME, "a")
            companies_data = []
            seen_urls = set()
            
            for link in all_links:
                try:
                    href = link.get_attribute('href')
                    if not href or not self.is_valid_company_url(href):
                        continue
                    
                    if href in seen_urls:
                        continue
                    seen_urls.add(href)
                    
                    # Try to get parent element for more context
                    try:
                        parent = link.find_element(By.XPATH, "./ancestor::*[contains(@class, 'company') or contains(@class, 'card')][1]")
                        company_info = self.extract_company_info(parent, href)
                    except:
                        company_info = self.extract_company_info(link, href)
                    
                    if company_info and company_info['name']:
                        companies_data.append(company_info)
                except:
                    continue
            
            # Try to extract from JSON data
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
                    # Merge avoiding duplicates
                    existing_urls = {c['yc_url'] for c in companies_data}
                    for company in parsed_companies:
                        if company.get('yc_url') and company['yc_url'] not in existing_urls:
                            companies_data.append(company)
            except Exception as e:
                print(f"Note: Could not parse JSON data: {e}")
            
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
            if isinstance(obj, dict):
                if 'name' in obj and ('batch' in obj or 'ycBatch' in obj or 'slug' in obj):
                    company = {
                        'name': obj.get('name', ''),
                        'batch': obj.get('batch') or obj.get('ycBatch') or obj.get('batchName'),
                        'description': obj.get('description') or obj.get('oneLiner') or obj.get('tagline'),
                        'website': obj.get('website') or obj.get('url'),
                        'location': obj.get('location') or obj.get('hqLocation') or obj.get('city'),
                        'industry': obj.get('industry') or obj.get('category'),
                        'yc_url': f"https://www.ycombinator.com/companies/{obj.get('slug', '')}" if obj.get('slug') else None
                    }
                    if company['name'] and company['yc_url']:
                        companies.append(company)
                
                if 'companies' in obj:
                    for item in obj['companies']:
                        extract_companies(item, path + ".companies")
                
                if 'props' in obj:
                    extract_companies(obj['props'], path + ".props")
                if 'pageProps' in obj:
                    extract_companies(obj['pageProps'], path + ".pageProps")
                
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
    
    scraper = ImprovedYCScraper()
    scraper.scrape_companies(url)
    scraper.save_to_database()
    
    print("\nScraping complete!")

