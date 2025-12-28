#!/usr/bin/env python3
"""
Fixed Founder Scraper - More reliable extraction
"""

import time
import sqlite3
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import json

class FixedFounderScraper:
    def __init__(self, db_path='yc_companies.db'):
        self.db_path = db_path
        self.setup_database()
        
    def setup_database(self):
        """Create founders table if it doesn't exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS founders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER,
                company_name TEXT,
                name TEXT NOT NULL,
                role TEXT,
                previous_company TEXT,
                linkedin_url TEXT,
                twitter_url TEXT,
                yc_profile_url TEXT,
                bio TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (company_id) REFERENCES companies(id),
                UNIQUE(company_name, name)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def setup_driver(self):
        """Setup Chrome WebDriver"""
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36')
        
        try:
            driver = webdriver.Chrome(options=chrome_options)
            return driver
        except Exception as e:
            print(f"Error setting up Chrome driver: {e}")
            raise
    
    def extract_founders_from_page(self, driver, company_url, company_name):
        """Extract founders using multiple reliable methods"""
        founders = []
        
        try:
            driver.get(company_url)
            time.sleep(6)  # Wait for page to fully load
            
            # Scroll to ensure all content is loaded
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)
            
            page_text = driver.find_element(By.TAG_NAME, "body").text.lower()
            
            # YC partners to exclude
            yc_partners = {'jared friedman', 'brad flora', 'gustaf alstromer', 
                          'harj taggar', 'aaron epstein', 'david lieb', 'paul graham',
                          'jessica livingston', 'trevor blackwell', 'robert morris'}
            
            # METHOD 1: Find ALL /people/ links and check context
            try:
                all_people_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/people/']")
                
                for link in all_people_links:
                    try:
                        href = link.get_attribute('href')
                        name = link.text.strip()
                        
                        if not name or len(name.split()) < 2 or len(name.split()) > 4:
                            continue
                        
                        if name.lower() in yc_partners:
                            continue
                        
                        # Check if this link is in an "Active Founders" section
                        is_founder = False
                        role = None
                        linkedin_url = None
                        twitter_url = None
                        
                        # Try to find the section containing this link
                        try:
                            # Look up the DOM tree for sections
                            for level in range(1, 15):
                                try:
                                    ancestor = link.find_element(By.XPATH, f"./ancestor::*[position()={level}]")
                                    ancestor_text = ancestor.text.lower()
                                    
                                    # Check if this ancestor is an "Active Founders" section
                                    if 'active founder' in ancestor_text or ('founder' in ancestor_text and 'yc partner' not in ancestor_text):
                                        is_founder = True
                                        
                                        # Try to extract role
                                        if 'ceo' in ancestor_text and 'founder' in ancestor_text:
                                            role = 'Founder, CEO'
                                        elif 'cto' in ancestor_text and 'founder' in ancestor_text:
                                            role = 'Founder, CTO'
                                        elif 'founder' in ancestor_text:
                                            role = 'Founder'
                                        
                                        # Try to find social links in this section
                                        try:
                                            section_links = ancestor.find_elements(By.TAG_NAME, "a")
                                            for l in section_links:
                                                l_href = l.get_attribute('href')
                                                if l_href:
                                                    if 'linkedin.com' in l_href:
                                                        linkedin_url = l_href
                                                    elif 'twitter.com' in l_href or 'x.com' in l_href:
                                                        twitter_url = l_href
                                        except:
                                            pass
                                        
                                        break
                                except:
                                    continue
                        except:
                            pass
                        
                        # If not found in section, check if name appears near "founder" text in page
                        if not is_founder:
                            name_pos = page_text.find(name.lower())
                            if name_pos != -1:
                                window_start = max(0, name_pos - 500)
                                window_end = min(len(page_text), name_pos + 500)
                                window_text = page_text[window_start:window_end]
                                
                                if 'founder' in window_text or 'co-founder' in window_text:
                                    is_founder = True
                                    role = 'Founder'
                        
                        if is_founder:
                            if not any(f['name'].lower() == name.lower() for f in founders):
                                founders.append({
                                    'name': name,
                                    'role': role or 'Founder',
                                    'yc_profile_url': href,
                                    'linkedin_url': linkedin_url,
                                    'twitter_url': twitter_url,
                                    'previous_company': None,
                                    'bio': None
                                })
                    except Exception as e:
                        continue
            except Exception as e:
                print(f"  Note: People links method error: {e}")
            
            # METHOD 2: Extract from JSON data
            try:
                json_data = driver.execute_script("""
                    if (window.__NEXT_DATA__) {
                        return JSON.stringify(window.__NEXT_DATA__);
                    }
                    return null;
                """)
                
                if json_data:
                    data = json.loads(json_data)
                    parsed_founders = self._parse_founders_from_json(data, company_name)
                    existing_names = {f['name'].lower() for f in founders}
                    for founder in parsed_founders:
                        if founder['name'].lower() not in existing_names:
                            founders.append(founder)
            except Exception as e:
                pass
            
            # METHOD 3: Text pattern matching
            try:
                patterns = [
                    r"(?:We're|We are|I'm|I am)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?(?:\s+and\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)*),?\s+(?:co-?founders?|founders?)",
                    r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?(?:\s+and\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)*)\s+(?:are|is)\s+(?:co-?founders?|founders?)",
                    r"Founded by\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?(?:\s+and\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)*)",
                ]
                
                false_positives = {'active founders', 'founder matching', 'back office', 'people', 
                                 'founders', 'founder directory', 'co-founder matching', 'find a co-founder',
                                 'the', 're the'}
                
                for pattern in patterns:
                    matches = re.finditer(pattern, page_text, re.IGNORECASE)
                    for match in matches:
                        names_str = match.group(1)
                        names = re.split(r'\s+and\s+|\s*,\s*', names_str)
                        for name in names:
                            name = name.strip()
                            if name.lower().startswith('and '):
                                name = name[4:].strip()
                            
                            if (name and 
                                len(name.split()) >= 2 and 
                                len(name.split()) <= 3 and
                                name.lower() not in false_positives and
                                name.lower() not in yc_partners and
                                not any(word.lower() in false_positives for word in name.split())):
                                
                                if not any(f['name'].lower() == name.lower() for f in founders):
                                    founders.append({
                                        'name': name,
                                        'role': 'Founder',
                                        'yc_profile_url': None,
                                        'linkedin_url': None,
                                        'twitter_url': None,
                                        'previous_company': None,
                                        'bio': None
                                    })
            except Exception as e:
                pass
            
            return founders
            
        except Exception as e:
            print(f"Error extracting founders: {e}")
            return []
    
    def _parse_founders_from_json(self, data, company_name):
        """Parse JSON data to extract founders"""
        founders = []
        
        def extract_founders(obj, path="", depth=0):
            if depth > 15:  # Limit depth
                return
                
            if isinstance(obj, dict):
                # Look for founder objects
                if 'name' in obj and isinstance(obj['name'], str):
                    name = obj['name'].strip()
                    if len(name.split()) >= 2 and len(name.split()) <= 4:
                        role = obj.get('role') or obj.get('title') or obj.get('position', '')
                        
                        # Check if it's a founder
                        is_founder = False
                        if 'founder' in str(role).lower():
                            is_founder = True
                        elif 'founder' in str(obj).lower():
                            is_founder = True
                        elif path and 'founder' in path.lower():
                            is_founder = True
                        
                        if is_founder:
                            founder = {
                                'name': name,
                                'role': role if role else 'Founder',
                                'previous_company': obj.get('previousCompany') or obj.get('previous_company'),
                                'linkedin_url': obj.get('linkedin') or obj.get('linkedinUrl'),
                                'twitter_url': obj.get('twitter') or obj.get('twitterUrl') or obj.get('x'),
                                'yc_profile_url': obj.get('ycUrl') or obj.get('yc_url') or obj.get('profileUrl'),
                                'bio': obj.get('bio') or obj.get('description')
                            }
                            founders.append(founder)
                
                # Look for arrays
                for key in ['founders', 'activeFounders', 'active_founders', 'team', 'people']:
                    if key in obj and isinstance(obj[key], list):
                        for item in obj[key]:
                            extract_founders(item, f"{path}.{key}", depth+1)
                
                # Recursively search
                for key, value in obj.items():
                    if key not in ['name', 'role', 'title']:
                        extract_founders(value, f"{path}.{key}", depth+1)
                        
            elif isinstance(obj, list):
                for item in obj:
                    extract_founders(item, f"{path}[]", depth+1)
        
        extract_founders(data)
        return founders
    
    def scrape_all_companies(self, limit=None, delay=2):
        """Scrape founders from all companies"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = '''
            SELECT id, name, yc_url 
            FROM companies 
            WHERE yc_url LIKE "%/companies/%" 
            AND yc_url NOT LIKE "%?%" 
            AND yc_url NOT LIKE "%industry=%" 
            AND yc_url NOT LIKE "%batch=%"
            ORDER BY name
        '''
        if limit:
            query += f" LIMIT {limit}"
        
        cursor.execute(query)
        companies = cursor.fetchall()
        conn.close()
        
        print(f"Found {len(companies)} companies to scrape")
        print(f"Delay between requests: {delay} seconds\n")
        
        driver = self.setup_driver()
        total_founders = 0
        
        try:
            for i, (company_id, company_name, yc_url) in enumerate(companies, 1):
                clean_company_name = company_name.split('\n')[0] if company_name else 'Unknown'
                
                print(f"[{i}/{len(companies)}] Scraping {clean_company_name}...")
                
                founders = self.extract_founders_from_page(driver, yc_url, clean_company_name)
                
                if founders:
                    self.save_founders(company_id, clean_company_name, founders)
                    total_founders += len(founders)
                    founder_names = ', '.join([f['name'] for f in founders])
                    print(f"  ✓ Found {len(founders)} founder(s): {founder_names}")
                else:
                    print(f"  - No founders found")
                
                if i < len(companies):
                    time.sleep(delay)
                    
        finally:
            driver.quit()
        
        print(f"\n{'='*80}")
        print(f"Scraping complete! Found {total_founders} total founders")
        print(f"{'='*80}")
    
    def save_founders(self, company_id, company_name, founders):
        """Save founders to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for founder in founders:
            try:
                cursor.execute('''
                    INSERT OR REPLACE INTO founders 
                    (company_id, company_name, name, role, previous_company, linkedin_url, twitter_url, yc_profile_url, bio)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    company_id,
                    company_name,
                    founder.get('name'),
                    founder.get('role'),
                    founder.get('previous_company'),
                    founder.get('linkedin_url'),
                    founder.get('twitter_url'),
                    founder.get('yc_profile_url'),
                    founder.get('bio')
                ))
            except Exception as e:
                print(f"  Error saving founder {founder.get('name')}: {e}")
        
        conn.commit()
        conn.close()

if __name__ == "__main__":
    import sys
    
    limit = None
    if len(sys.argv) > 1:
        limit = int(sys.argv[1])
    
    scraper = FixedFounderScraper()
    scraper.scrape_all_companies(limit=limit, delay=2)

