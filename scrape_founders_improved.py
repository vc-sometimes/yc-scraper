#!/usr/bin/env python3
"""
Improved Founder Scraper - More aggressive extraction
"""

import time
import sqlite3
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import json

class ImprovedFounderScraper:
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
        """Extract founders using multiple aggressive methods"""
        founders = []
        
        try:
            driver.get(company_url)
            time.sleep(5)  # Wait longer for page to fully load
            
            # Method 1: Extract ALL /people/ links and check if they're founders
            try:
                all_people_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/people/']")
                page_text = driver.find_element(By.TAG_NAME, "body").text.lower()
                
                yc_partners = {'jared friedman', 'brad flora', 'gustaf alstromer', 
                              'harj taggar', 'aaron epstein', 'david lieb', 'paul graham',
                              'jessica livingston', 'trevor blackwell', 'robert morris'}
                
                for link in all_people_links:
                    try:
                        href = link.get_attribute('href')
                        name = link.text.strip()
                        
                        if not name or len(name.split()) < 2 or len(name.split()) > 4:
                            continue
                        
                        if name.lower() in yc_partners:
                            continue
                        
                        # Get the section this link is in
                        try:
                            # Try to find a section/container
                            section = link.find_element(By.XPATH, "./ancestor::*[contains(@class, 'section') or contains(@class, 'founder') or contains(@class, 'team') or contains(@class, 'people')][1]")
                            section_text = section.text.lower()
                            
                            # If section mentions founders or this is clearly a founder section
                            if ('founder' in section_text or 
                                'active founder' in section_text or
                                'co-founder' in section_text):
                                
                                # Extract role if available
                                role = None
                                if 'founder' in section_text:
                                    role = 'Founder'
                                if 'ceo' in section_text:
                                    role = 'Founder, CEO'
                                if 'cto' in section_text:
                                    role = 'Founder, CTO'
                                
                                # Extract links
                                linkedin_url = None
                                twitter_url = None
                                
                                try:
                                    links_in_section = section.find_elements(By.TAG_NAME, "a")
                                    for l in links_in_section:
                                        href_l = l.get_attribute('href')
                                        if href_l:
                                            if 'linkedin.com' in href_l:
                                                linkedin_url = href_l
                                            elif 'twitter.com' in href_l or 'x.com' in href_l:
                                                twitter_url = href_l
                                except:
                                    pass
                                
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
                        except:
                            # If we can't find a section, check if name appears near founder text
                            try:
                                # Get parent element
                                parent = link.find_element(By.XPATH, "./ancestor::*[position()<=10]")
                                parent_text = parent.text.lower()
                                
                                # Check if founder is mentioned nearby
                                name_pos = parent_text.find(name.lower())
                                if name_pos != -1:
                                    # Look in a window around the name
                                    window_start = max(0, name_pos - 200)
                                    window_end = min(len(parent_text), name_pos + 200)
                                    window_text = parent_text[window_start:window_end]
                                    
                                    if 'founder' in window_text or 'co-founder' in window_text:
                                        if not any(f['name'].lower() == name.lower() for f in founders):
                                            founders.append({
                                                'name': name,
                                                'role': 'Founder',
                                                'yc_profile_url': href,
                                                'linkedin_url': None,
                                                'twitter_url': None,
                                                'previous_company': None,
                                                'bio': None
                                            })
                            except:
                                pass
                    except Exception as e:
                        continue
            except Exception as e:
                print(f"  Note: People links method error: {e}")
            
            # Method 2: Extract from JSON data (most reliable)
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
            
            # Method 3: Text pattern matching for founder mentions
            try:
                page_text = driver.find_element(By.TAG_NAME, "body").text
                
                # Pattern: "We're X and Y, founders" or "X and Y are founders"
                patterns = [
                    r"(?:We're|We are|I'm|I am)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?(?:\s+and\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)*),?\s+(?:co-?founders?|founders?)",
                    r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?(?:\s+and\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)*)\s+(?:are|is)\s+(?:co-?founders?|founders?)",
                    r"Founded by\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?(?:\s+and\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)*)",
                ]
                
                false_positives = {'active founders', 'founder matching', 'back office', 'people', 
                                 'founders', 'founder directory', 'co-founder matching', 'find a co-founder',
                                 'the', 're the'}
                
                yc_partners = {'jared friedman', 'brad flora', 'gustaf alstromer', 
                              'harj taggar', 'aaron epstein', 'david lieb'}
                
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
        """Parse JSON data more thoroughly"""
        founders = []
        
        def extract_founders(obj, path=""):
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
                                'previous_company': obj.get('previousCompany') or obj.get('previous_company') or obj.get('prevCompany'),
                                'linkedin_url': obj.get('linkedin') or obj.get('linkedinUrl') or obj.get('linkedin_url'),
                                'twitter_url': obj.get('twitter') or obj.get('twitterUrl') or obj.get('twitter_url') or obj.get('x') or obj.get('xUrl'),
                                'yc_profile_url': obj.get('ycUrl') or obj.get('yc_url') or obj.get('profileUrl') or obj.get('url'),
                                'bio': obj.get('bio') or obj.get('description') or obj.get('about')
                            }
                            founders.append(founder)
                
                # Look for arrays of founders
                for key in ['founders', 'activeFounders', 'active_founders', 'team', 'people']:
                    if key in obj and isinstance(obj[key], list):
                        for item in obj[key]:
                            extract_founders(item, f"{path}.{key}")
                
                # Recursively search
                for key, value in obj.items():
                    if key not in ['name', 'role', 'title']:
                        extract_founders(value, f"{path}.{key}")
                        
            elif isinstance(obj, list):
                for item in obj:
                    extract_founders(item, f"{path}[]")
        
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
    
    scraper = ImprovedFounderScraper()
    scraper.scrape_all_companies(limit=limit, delay=2)

