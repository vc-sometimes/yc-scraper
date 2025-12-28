#!/usr/bin/env python3
"""
Browser-based founder scraper - manually visits each page and extracts founders
"""

import time
import sqlite3
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import re

class BrowserFounderScraper:
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
        """Setup Chrome WebDriver with visible browser"""
        chrome_options = Options()
        # Don't use headless so we can see what's happening
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36')
        
        try:
            driver = webdriver.Chrome(options=chrome_options)
            driver.set_window_size(1200, 800)
            return driver
        except Exception as e:
            print(f"Error setting up Chrome driver: {e}")
            raise
    
    def extract_founders_from_page(self, driver, company_url, company_name):
        """Extract founders by manually inspecting the page"""
        founders = []
        
        try:
            print(f"  Visiting: {company_url}")
            driver.get(company_url)
            time.sleep(5)  # Wait for page to load
            
            # Scroll to load all content
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)
            
            page_text = driver.find_element(By.TAG_NAME, "body").text
            page_text_lower = page_text.lower()
            
            yc_partners = {'jared friedman', 'brad flora', 'gustaf alstromer', 
                          'harj taggar', 'aaron epstein', 'david lieb', 'paul graham',
                          'jessica livingston', 'trevor blackwell', 'robert morris',
                          'pete koomen'}
            
            # METHOD 1: Find "Active Founders" section and extract names
            try:
                active_founders_headings = driver.find_elements(By.XPATH, "//*[contains(text(), 'Active Founders')]")
                
                for heading in active_founders_headings:
                    try:
                        # Get the container section
                        for level in range(1, 8):
                            try:
                                container = heading.find_element(By.XPATH, f"./ancestor::*[position()={level}]")
                                container_text = container.text
                                
                                # Find where "Active Founders" appears
                                lines = container_text.split('\n')
                                active_idx = None
                                for i, line in enumerate(lines):
                                    if 'Active Founders' in line:
                                        active_idx = i
                                        break
                                
                                if active_idx is None:
                                    continue
                                
                                # Extract names from lines after "Active Founders"
                                # Stop at next major section
                                end_markers = ['latest news', 'company launches', 'tl;dr', 'problem:', 'solution:', 'ask:', 'team:']
                                
                                for i in range(active_idx + 1, len(lines)):
                                    line = lines[i].strip()
                                    if not line:
                                        continue
                                    
                                    # Check if we hit an end marker
                                    line_lower = line.lower()
                                    if any(marker in line_lower for marker in end_markers):
                                        break
                                    
                                    # Check if this line is a name (2-4 words, capitalized)
                                    words = line.split()
                                    if (len(words) >= 2 and len(words) <= 4 and
                                        all(w and w[0].isupper() for w in words) and
                                        line.lower() not in yc_partners):
                                        
                                        # Check if next line(s) contain "Founder"
                                        is_founder = False
                                        role = 'Founder'
                                        
                                        for j in range(i+1, min(i+4, len(lines))):
                                            next_line = lines[j].strip().lower()
                                            if 'founder' in next_line:
                                                is_founder = True
                                                if 'co-founder' in next_line or 'cofounder' in next_line:
                                                    role = 'Co-founder'
                                                elif 'ceo' in next_line:
                                                    role = 'Founder, CEO'
                                                elif 'cto' in next_line:
                                                    role = 'Founder, CTO'
                                                elif 'coo' in next_line:
                                                    role = 'Founder, COO'
                                                break
                                        
                                        if is_founder:
                                            name = line
                                            
                                            # Try to find /people/ link for this name
                                            yc_profile_url = None
                                            linkedin_url = None
                                            twitter_url = None
                                            
                                            try:
                                                name_elem = container.find_element(By.XPATH, f".//*[contains(text(), '{name}')]")
                                                # Look for links near this element
                                                parent = name_elem.find_element(By.XPATH, "./ancestor::*[position()<=5]")
                                                links = parent.find_elements(By.TAG_NAME, "a")
                                                
                                                for link in links:
                                                    href = link.get_attribute('href')
                                                    if not href:
                                                        continue
                                                    
                                                    if '/people/' in href:
                                                        yc_profile_url = href
                                                    elif 'linkedin.com/in/' in href.lower() and 'company' not in href.lower():
                                                        linkedin_url = href
                                                    elif ('twitter.com/' in href.lower() or 'x.com/' in href.lower()) and 'ycombinator' not in href.lower():
                                                        twitter_url = href
                                            except:
                                                pass
                                            
                                            if not any(f['name'].lower() == name.lower() for f in founders):
                                                founders.append({
                                                    'name': name,
                                                    'role': role,
                                                    'yc_profile_url': yc_profile_url,
                                                    'linkedin_url': linkedin_url,
                                                    'twitter_url': twitter_url,
                                                    'previous_company': None,
                                                    'bio': None
                                                })
                                
                                break
                            except:
                                continue
                    except:
                        continue
            except Exception as e:
                pass
            
            # METHOD 2: Extract from text patterns if no founders found
            if len(founders) == 0:
                # Look for patterns like "we're X and Y" or "@X and @Y"
                patterns = [
                    r"(?:we're|we are|hi yc|hi!|founded by)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+and\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
                    r"@([A-Z][a-zA-Z0-9_]+)\s+and\s+@([A-Z][a-zA-Z0-9_]+)",
                    r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+and\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(?:are|were|is|was)\s+(?:the\s+)?(?:co-?)?founders?",
                ]
                
                for pattern in patterns:
                    matches = re.finditer(pattern, page_text, re.IGNORECASE)
                    for match in matches:
                        if len(match.groups()) == 2:
                            name1 = match.group(1).strip()
                            name2 = match.group(2).strip()
                            
                            for name in [name1, name2]:
                                # Clean up name
                                if name.startswith('@'):
                                    name = name[1:]
                                name = name.replace('_', ' ').replace('-', ' ')
                                words = name.split()
                                name = ' '.join([w.capitalize() for w in words])
                                
                                if (name and len(name.split()) >= 2 and len(name.split()) <= 4 and
                                    name.lower() not in yc_partners):
                                    
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
            
            # METHOD 3: Visit /people/ page if no founders found
            if len(founders) == 0:
                try:
                    people_url = company_url.rstrip('/') + '/people'
                    driver.get(people_url)
                    time.sleep(4)
                    
                    # Get all /people/ links
                    people_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/people/']")
                    
                    # Visit first few profiles to check if they're founders
                    for link in people_links[:5]:
                        try:
                            href = link.get_attribute('href')
                            name = link.text.strip()
                            
                            if (name and len(name.split()) >= 2 and len(name.split()) <= 4 and
                                name.lower() not in yc_partners):
                                
                                # Visit profile
                                driver.get(href)
                                time.sleep(2)
                                
                                profile_text = driver.find_element(By.TAG_NAME, "body").text.lower()
                                
                                # Check if they're a founder
                                if 'founder' in profile_text or company_name.lower().split('\n')[0].lower() in profile_text:
                                    linkedin_url, twitter_url = self._find_social_links(driver)
                                    
                                    if not any(f['name'].lower() == name.lower() for f in founders):
                                        founders.append({
                                            'name': name,
                                            'role': 'Founder',
                                            'yc_profile_url': href,
                                            'linkedin_url': linkedin_url,
                                            'twitter_url': twitter_url,
                                            'previous_company': None,
                                            'bio': None
                                        })
                                
                                # Go back to people page
                                driver.get(people_url)
                                time.sleep(1)
                        except:
                            continue
                    
                    # Go back to company page
                    driver.get(company_url)
                    time.sleep(2)
                except:
                    pass
            
            return founders
            
        except Exception as e:
            print(f"  Error extracting founders: {e}")
            return []
    
    def _find_social_links(self, driver):
        """Find LinkedIn and Twitter links on current page"""
        linkedin_url = None
        twitter_url = None
        
        try:
            links = driver.find_elements(By.TAG_NAME, "a")
            for link in links:
                href = link.get_attribute('href')
                if href:
                    if 'linkedin.com/in/' in href.lower() and 'company' not in href.lower():
                        linkedin_url = href
                    elif ('twitter.com/' in href.lower() or 'x.com/' in href.lower()) and 'ycombinator' not in href.lower():
                        twitter_url = href
        except:
            pass
        
        return linkedin_url, twitter_url
    
    def scrape_all_companies(self, limit=None, delay=3):
        """Scrape founders from all companies without founders"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = '''
            SELECT DISTINCT c.id, c.name, c.yc_url 
            FROM companies c
            LEFT JOIN founders f ON c.id = f.company_id
            WHERE c.yc_url LIKE "%/companies/%" 
            AND c.yc_url NOT LIKE "%?%" 
            AND c.yc_url NOT LIKE "%industry=%" 
            AND c.yc_url NOT LIKE "%batch=%"
            AND f.id IS NULL
            ORDER BY c.name
        '''
        if limit:
            query += f" LIMIT {limit}"
        
        cursor.execute(query)
        companies = cursor.fetchall()
        conn.close()
        
        print(f"Found {len(companies)} companies without founders to scrape")
        print(f"Using browser automation to visit each page...\n")
        
        driver = self.setup_driver()
        total_founders = 0
        
        try:
            for i, (company_id, company_name, yc_url) in enumerate(companies, 1):
                clean_company_name = company_name.split('\n')[0] if company_name else 'Unknown'
                
                print(f"[{i}/{len(companies)}] Processing {clean_company_name}...")
                
                founders = self.extract_founders_from_page(driver, yc_url, clean_company_name)
                
                if founders:
                    self.save_founders(company_id, clean_company_name, founders)
                    total_founders += len(founders)
                    founder_names = ', '.join([f['name'] for f in founders])
                    print(f"  ✅ Found {len(founders)} founder(s): {founder_names}")
                else:
                    print(f"  ⚠️  No founders found")
                
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
    
    scraper = BrowserFounderScraper()
    scraper.scrape_all_companies(limit=limit, delay=3)

