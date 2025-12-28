#!/usr/bin/env python3
"""
Scrape Active Founders from YC company pages
Specifically targets the "Active Founders" section on each company page
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

class FounderScraper:
    def __init__(self, db_path='yc_companies.db'):
        self.db_path = db_path
        self.setup_database()
        
    def setup_database(self):
        """Create founders table if it doesn't exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create founders table (separate from team_members)
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
        print(f"Database tables initialized")
    
    def setup_driver(self):
        """Setup Chrome WebDriver"""
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
    
    def extract_founders_from_page(self, driver, company_url, company_name):
        """Extract Active Founders from a company page"""
        founders = []
        
        try:
            driver.get(company_url)
            time.sleep(5)  # Wait for page to load
            
            # Scroll to load any lazy-loaded content
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)
            
            # Method 1: Look for "Active Founders" section
            try:
                # Try to find section with "Active Founders" text
                active_founders_section = None
                
                # Look for heading containing "Active Founders"
                headings = driver.find_elements(By.XPATH, "//*[contains(text(), 'Active Founders') or contains(text(), 'Founders')]")
                for heading in headings:
                    try:
                        # Get parent container
                        parent = heading.find_element(By.XPATH, "./ancestor::*[contains(@class, 'section') or contains(@class, 'container') or contains(@class, 'founder')][1]")
                        active_founders_section = parent
                        break
                    except:
                        continue
                
                if active_founders_section:
                    # Find all founder cards/items within this section
                    founder_elements = active_founders_section.find_elements(By.XPATH, ".//*[contains(@class, 'founder') or contains(@class, 'person') or contains(@class, 'card')]")
                    
                    for elem in founder_elements:
                        try:
                            founder_data = self._extract_founder_from_element(elem, company_name)
                            if founder_data:
                                founders.append(founder_data)
                        except Exception as e:
                            continue
            except Exception as e:
                print(f"  Note: Could not find Active Founders section: {e}")
            
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
                    # Merge avoiding duplicates
                    existing_names = {f['name'] for f in founders}
                    for founder in parsed_founders:
                        if founder['name'] not in existing_names:
                            founders.append(founder)
            except Exception as e:
                print(f"  Note: JSON parsing error: {e}")
            
            # Method 2.5: Look for ALL people links and check context more carefully
            try:
                people_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/people/']")
                page_text = driver.find_element(By.TAG_NAME, "body").text.lower()
                
                yc_partners = {'jared friedman', 'brad flora', 'gustaf alstromer', 
                              'harj taggar', 'aaron epstein', 'david lieb', 'paul graham',
                              'jessica livingston', 'trevor blackwell', 'robert morris'}
                
                # If page mentions founders, check all people links
                if 'founder' in page_text or 'co-founder' in page_text:
                    for link in people_links:
                        try:
                            href = link.get_attribute('href')
                            name = link.text.strip()
                            
                            if not name or len(name.split()) < 2 or len(name.split()) > 4:
                                continue
                            
                            if name.lower() in yc_partners:
                                continue
                            
                            # Try multiple ways to get context
                            found_founder_context = False
                            
                            # Method A: Check parent sections
                            try:
                                for level in range(1, 8):
                                    try:
                                        parent = link.find_element(By.XPATH, f"./ancestor::*[position()={level}]")
                                        parent_text = parent.text.lower()
                                        
                                        # Check if this section is about founders
                                        if ('founder' in parent_text or 'active founder' in parent_text) and 'yc partner' not in parent_text:
                                            # Extract role if available
                                            role = None
                                            if 'ceo' in parent_text and 'founder' in parent_text:
                                                role = 'Founder, CEO'
                                            elif 'cto' in parent_text and 'founder' in parent_text:
                                                role = 'Founder, CTO'
                                            elif 'founder' in parent_text:
                                                role = 'Founder'
                                            
                                            # Try to get social links from this section
                                            linkedin_url = None
                                            twitter_url = None
                                            try:
                                                section_links = parent.find_elements(By.TAG_NAME, "a")
                                                for l in section_links:
                                                    l_href = l.get_attribute('href')
                                                    if l_href:
                                                        if 'linkedin.com' in l_href:
                                                            linkedin_url = l_href
                                                        elif 'twitter.com' in l_href or 'x.com' in l_href:
                                                            twitter_url = l_href
                                            except:
                                                pass
                                            
                                            if not any(f['name'].lower() == name.lower() for f in founders):
                                                founders.append({
                                                    'name': name,
                                                    'yc_profile_url': href,
                                                    'role': role or 'Founder',
                                                    'previous_company': None,
                                                    'linkedin_url': linkedin_url,
                                                    'twitter_url': twitter_url,
                                                    'bio': None
                                                })
                                                found_founder_context = True
                                                break
                                    except:
                                        continue
                            except:
                                pass
                            
                            # Method B: If no section context, check if name appears near founder text in page
                            if not found_founder_context:
                                try:
                                    name_pos = page_text.find(name.lower())
                                    if name_pos != -1:
                                        # Look in window around name
                                        window_start = max(0, name_pos - 300)
                                        window_end = min(len(page_text), name_pos + 300)
                                        window_text = page_text[window_start:window_end]
                                        
                                        if 'founder' in window_text or 'co-founder' in window_text:
                                            if not any(f['name'].lower() == name.lower() for f in founders):
                                                founders.append({
                                                    'name': name,
                                                    'yc_profile_url': href,
                                                    'role': 'Founder',
                                                    'previous_company': None,
                                                    'linkedin_url': None,
                                                    'twitter_url': None,
                                                    'bio': None
                                                })
                                except:
                                    pass
                        except:
                            continue
            except Exception as e:
                print(f"  Note: People links method error: {e}")
            
            # Method 3: Extract founders from text patterns (e.g., "We're X and Y, founders")
            try:
                page_text = driver.find_element(By.TAG_NAME, "body").text
                # Pattern: "We're [names], founders" or "We're [names], co-founders"
                founder_patterns = [
                    r"(?:We're|We are|Founded by|Co-founded by)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?(?:\s+and\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)*),?\s+(?:co-?founders?|founders?)",
                    r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?(?:\s+and\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)*),?\s+(?:co-?founders?|founders?)\s+of",
                ]
                
                false_positives = {'active founders', 'founder matching', 'back office', 'people', 
                                 'founders', 'founder directory', 'co-founder matching', 'find a co-founder'}
                
                for pattern in founder_patterns:
                    matches = re.finditer(pattern, page_text, re.IGNORECASE)
                    for match in matches:
                        names_str = match.group(1)
                        # Split names
                        names = re.split(r'\s+and\s+|\s*,\s*', names_str)
                        for name in names:
                            name = name.strip()
                            # Skip if name starts with "and" (partial match)
                            if name.lower().startswith('and '):
                                name = name[4:].strip()
                            # Filter out false positives and validate name
                            yc_partners = {'jared friedman', 'brad flora', 'gustaf alstromer', 
                                          'harj taggar', 'aaron epstein', 'david lieb'}
                            
                            if (name and 
                                len(name.split()) >= 2 and  # At least first and last name
                                len(name.split()) <= 3 and  # Max 3 words
                                name.lower() not in false_positives and
                                name.lower() not in yc_partners and
                                not any(word.lower() in false_positives for word in name.split()) and
                                not name.lower().startswith('and ') and
                                not name.lower().startswith('re ') and  # Filter "re the" false positives
                                name.lower() != 'the'):  # Filter "the" false positives
                                # Check if not already added
                                if not any(f['name'].lower() == name.lower() for f in founders):
                                    founders.append({
                                        'name': name,
                                        'yc_profile_url': None,
                                        'role': 'Founder',
                                        'previous_company': None,
                                        'linkedin_url': None,
                                        'twitter_url': None,
                                        'bio': None
                                    })
            except Exception as e:
                pass
            
            # Method 4: Look for founder cards by structure
            try:
                # Look for elements that contain name + role + company info
                all_cards = driver.find_elements(By.CSS_SELECTOR, "[class*='card'], [class*='founder'], [class*='person'], [class*='team']")
                
                for card in all_cards:
                    try:
                        card_text = card.text
                        # Check if it looks like a founder card (has name, role, company)
                        if ('Founder' in card_text or 'CEO' in card_text or 'CTO' in card_text) and len(card_text.split('\n')) >= 3:
                            # Try to extract founder info
                            founder_data = self._extract_founder_from_element(card, company_name)
                            if founder_data and founder_data['name']:
                                # Check if not already added
                                if not any(f['name'].lower() == founder_data['name'].lower() for f in founders):
                                    founders.append(founder_data)
                    except:
                        continue
            except Exception as e:
                pass
            
            return founders
            
        except Exception as e:
            print(f"Error extracting founders from {company_url}: {e}")
            return []
    
    def _extract_founder_from_element(self, element, company_name):
        """Extract founder information from a DOM element"""
        try:
            text = element.text.strip()
            if not text or len(text) < 5:
                return None
            
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            if len(lines) < 2:
                return None
            
            # First line is usually the name
            name = lines[0]
            
            # Skip if it's not a name (too short, all caps, etc.)
            if len(name.split()) < 2 or name.upper() == name:
                return None
            
            # Look for role (Founder, CEO, CTO, etc.)
            role = None
            previous_company = None
            
            for line in lines[1:]:
                line_lower = line.lower()
                if 'founder' in line_lower or 'ceo' in line_lower or 'cto' in line_lower or 'coo' in line_lower:
                    role = line
                    # Check for previous company (e.g., "prev. Meta", "prev. NVIDIA")
                    if 'prev' in line_lower:
                        prev_match = re.search(r'prev\.?\s+([A-Z][A-Za-z0-9\s]+)', line, re.IGNORECASE)
                        if prev_match:
                            previous_company = prev_match.group(1).strip()
                            # Remove previous company from role
                            role = re.sub(r'\s*\|\s*prev\.?\s+[A-Z][A-Za-z0-9\s]+', '', role, flags=re.IGNORECASE).strip()
                    break
            
            # Extract links
            linkedin_url = None
            twitter_url = None
            yc_profile_url = None
            
            try:
                links = element.find_elements(By.TAG_NAME, "a")
                for link in links:
                    href = link.get_attribute('href')
                    if not href:
                        continue
                    if 'linkedin.com' in href:
                        linkedin_url = href
                    elif 'twitter.com' in href or 'x.com' in href:
                        twitter_url = href
                    elif '/people/' in href:
                        yc_profile_url = href
            except:
                pass
            
            return {
                'name': name,
                'role': role,
                'previous_company': previous_company,
                'linkedin_url': linkedin_url,
                'twitter_url': twitter_url,
                'yc_profile_url': yc_profile_url,
                'bio': None
            }
        except Exception as e:
            return None
    
    def _parse_founders_from_json(self, data, company_name):
        """Parse JSON data to extract founders"""
        founders = []
        
        def extract_founders(obj, path=""):
            if isinstance(obj, dict):
                # Look for founder objects
                if 'name' in obj:
                    # Check if it's a founder (has role with "founder" or is in founders array)
                    is_founder = False
                    role = obj.get('role') or obj.get('title') or obj.get('position', '')
                    
                    if 'founder' in str(role).lower() or 'founder' in str(obj).lower():
                        is_founder = True
                    
                    if is_founder and len(obj.get('name', '').split()) >= 2:
                        founder = {
                            'name': obj.get('name', ''),
                            'role': role,
                            'previous_company': obj.get('previousCompany') or obj.get('previous_company') or obj.get('prevCompany'),
                            'linkedin_url': obj.get('linkedin') or obj.get('linkedinUrl') or obj.get('linkedin_url'),
                            'twitter_url': obj.get('twitter') or obj.get('twitterUrl') or obj.get('twitter_url') or obj.get('x') or obj.get('xUrl'),
                            'yc_profile_url': obj.get('ycUrl') or obj.get('yc_url') or obj.get('profileUrl'),
                            'bio': obj.get('bio') or obj.get('description') or obj.get('about')
                        }
                        founders.append(founder)
                
                # Look for founders array
                if 'founders' in obj:
                    for founder in obj['founders']:
                        extract_founders(founder, path + ".founders")
                
                if 'activeFounders' in obj:
                    for founder in obj['activeFounders']:
                        extract_founders(founder, path + ".activeFounders")
                
                # Look for people array that might contain founders
                if 'people' in obj and isinstance(obj['people'], list):
                    for person in obj['people']:
                        if isinstance(person, dict) and person.get('name'):
                            # Check if they're a founder based on context
                            role = person.get('role') or person.get('title') or ''
                            if 'founder' in role.lower():
                                extract_founders(person, path + ".people")
                
                # Recursively search
                if 'props' in obj:
                    extract_founders(obj['props'], path + ".props")
                if 'pageProps' in obj:
                    extract_founders(obj['pageProps'], path + ".pageProps")
                if 'company' in obj:
                    extract_founders(obj['company'], path + ".company")
                if 'query' in obj:
                    extract_founders(obj['query'], path + ".query")
                    
            elif isinstance(obj, list):
                for item in obj:
                    extract_founders(item, path + "[]")
        
        extract_founders(data)
        return founders
    
    def scrape_all_companies(self, limit=None, delay=2):
        """Scrape founders from all companies"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get all companies
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
        print(f"Delay between requests: {delay} seconds")
        print()
        
        driver = None
        total_founders = 0
        
        try:
            driver = self.setup_driver()
            for i, (company_id, company_name, yc_url) in enumerate(companies, 1):
                # Clean company name
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
                
                # Delay between requests to avoid rate limiting
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
    
    scraper = FounderScraper()
    scraper.scrape_all_companies(limit=limit, delay=2)

