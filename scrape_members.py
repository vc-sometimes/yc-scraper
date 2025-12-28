#!/usr/bin/env python3
"""
Scrape team members/founders from YC company pages
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

class MemberScraper:
    def __init__(self, db_path='yc_companies.db'):
        self.db_path = db_path
        self.setup_database()
        
    def setup_database(self):
        """Create team members table if it doesn't exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create team members table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS team_members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER,
                company_name TEXT,
                name TEXT NOT NULL,
                role TEXT,
                email TEXT,
                linkedin_url TEXT,
                twitter_url TEXT,
                bio TEXT,
                yc_profile_url TEXT,
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
    
    def extract_members_from_page(self, driver, company_url, company_name):
        """Extract team members from a company page"""
        members = []
        
        try:
            driver.get(company_url)
            time.sleep(3)  # Wait for page to load
            
            # Method 1: Look for founder/team member links
            founder_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/people/'], a[href*='/founders/']")
            
            # Filter out common false positives
            false_positives = {
                'active founders', 'founder matching', 'back office', 'people', 
                'founders', 'founder directory', 'co-founder matching', 'find a co-founder'
            }
            
            for link in founder_links:
                try:
                    href = link.get_attribute('href')
                    name = link.text.strip()
                    # Filter out false positives
                    if (name and '/people/' in href and 
                        name.lower() not in false_positives and
                        len(name.split()) >= 2 and  # At least first and last name
                        len(name.split()) <= 4):   # Max 4 words (e.g., "John Michael Smith Jr")
                        members.append({
                            'name': name,
                            'yc_profile_url': href,
                            'role': None,
                            'email': None,
                            'linkedin_url': None,
                            'twitter_url': None,
                            'bio': None
                        })
                except:
                    continue
            
            # Method 2: Extract from JSON data
            try:
                json_data = driver.execute_script("""
                    if (window.__NEXT_DATA__) {
                        return JSON.stringify(window.__NEXT_DATA__);
                    }
                    return null;
                """)
                
                if json_data:
                    data = json.loads(json_data)
                    parsed_members = self._parse_members_from_json(data, company_name)
                    # Merge avoiding duplicates
                    existing_names = {m['name'] for m in members}
                    for member in parsed_members:
                        if member['name'] not in existing_names:
                            members.append(member)
            except Exception as e:
                pass
            
            # Method 3: Look for founder mentions in text (e.g., "We're John, Jane, and Bob, co-founders")
            try:
                page_text = driver.find_element(By.TAG_NAME, "body").text
                # Pattern: "We're [names], co-founders"
                founder_patterns = [
                    r"(?:We're|We are|Founded by|Co-founded by)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?(?:\s+and\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)*),?\s+(?:co-?founders?|founders?)",
                    r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?(?:\s+and\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)*),?\s+(?:co-?founders?|founders?)\s+of",
                ]
                
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
                            if (name and 
                                len(name.split()) >= 2 and  # At least first and last name
                                len(name.split()) <= 3 and  # Max 3 words
                                name.lower() not in false_positives and
                                not any(word.lower() in false_positives for word in name.split()) and
                                not name.lower().startswith('and ')):  # Extra check
                                # Check if not already added
                                if not any(m['name'].lower() == name.lower() for m in members):
                                    members.append({
                                        'name': name,
                                        'yc_profile_url': None,
                                        'role': 'Founder',
                                        'email': None,
                                        'linkedin_url': None,
                                        'twitter_url': None,
                                        'bio': None
                                    })
            except:
                pass
            
            # Method 4: Look for structured founder sections
            try:
                # Look for elements with "founder" in class or text
                founder_elements = driver.find_elements(By.XPATH, 
                    "//*[contains(@class, 'founder') or contains(@class, 'team') or contains(text(), 'Founder')]")
                
                for elem in founder_elements[:20]:  # Limit to avoid too many false positives
                    try:
                        text = elem.text.strip()
                        # Look for name patterns
                        name_match = re.search(r'\b([A-Z][a-z]+\s+[A-Z][a-z]+)\b', text)
                        if name_match:
                            name = name_match.group(1)
                            # Check if it looks like a name, not a false positive, and not already added
                            if (len(name.split()) == 2 and 
                                name.lower() not in false_positives and
                                not any(m['name'].lower() == name.lower() for m in members)):
                                # Try to find role
                                role = 'Founder' if 'founder' in text.lower() else None
                                members.append({
                                    'name': name,
                                    'yc_profile_url': None,
                                    'role': role,
                                    'email': None,
                                    'linkedin_url': None,
                                    'twitter_url': None,
                                    'bio': None
                                })
                    except:
                        continue
            except:
                pass
            
            return members
            
        except Exception as e:
            print(f"Error extracting members from {company_url}: {e}")
            return []
    
    def _parse_members_from_json(self, data, company_name):
        """Parse JSON data to extract team members"""
        members = []
        
        def extract_members(obj, path=""):
            if isinstance(obj, dict):
                # Look for founder/team member objects
                if 'name' in obj and ('role' in obj or 'title' in obj or 'founder' in str(obj).lower()):
                    name = obj.get('name', '')
                    if name and len(name.split()) <= 4:  # Reasonable name
                        member = {
                            'name': name,
                            'role': obj.get('role') or obj.get('title') or obj.get('position'),
                            'email': obj.get('email'),
                            'linkedin_url': obj.get('linkedin') or obj.get('linkedinUrl'),
                            'twitter_url': obj.get('twitter') or obj.get('twitterUrl'),
                            'bio': obj.get('bio') or obj.get('description'),
                            'yc_profile_url': obj.get('ycUrl') or obj.get('profileUrl')
                        }
                        members.append(member)
                
                # Look for founders array
                if 'founders' in obj:
                    for founder in obj['founders']:
                        extract_members(founder, path + ".founders")
                
                if 'team' in obj:
                    for member in obj['team']:
                        extract_members(member, path + ".team")
                
                # Recursively search
                if 'props' in obj:
                    extract_members(obj['props'], path + ".props")
                if 'pageProps' in obj:
                    extract_members(obj['pageProps'], path + ".pageProps")
                    
            elif isinstance(obj, list):
                for item in obj:
                    extract_members(item, path + "[]")
        
        extract_members(data)
        return members
    
    def scrape_all_companies(self, limit=None, delay=2):
        """Scrape members from all companies"""
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
        
        driver = self.setup_driver()
        total_members = 0
        
        try:
            for i, (company_id, company_name, yc_url) in enumerate(companies, 1):
                # Clean company name
                clean_company_name = company_name.split('\n')[0] if company_name else 'Unknown'
                
                print(f"[{i}/{len(companies)}] Scraping {clean_company_name}...")
                
                members = self.extract_members_from_page(driver, yc_url, clean_company_name)
                
                if members:
                    self.save_members(company_id, clean_company_name, members)
                    total_members += len(members)
                    print(f"  ✓ Found {len(members)} member(s): {', '.join([m['name'] for m in members])}")
                else:
                    print(f"  - No members found")
                
                # Delay between requests to avoid rate limiting
                if i < len(companies):
                    time.sleep(delay)
                    
        finally:
            driver.quit()
        
        print(f"\n{'='*80}")
        print(f"Scraping complete! Found {total_members} total team members")
        print(f"{'='*80}")
    
    def save_members(self, company_id, company_name, members):
        """Save members to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for member in members:
            try:
                cursor.execute('''
                    INSERT OR REPLACE INTO team_members 
                    (company_id, company_name, name, role, email, linkedin_url, twitter_url, bio, yc_profile_url)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    company_id,
                    company_name,
                    member.get('name'),
                    member.get('role'),
                    member.get('email'),
                    member.get('linkedin_url'),
                    member.get('twitter_url'),
                    member.get('bio'),
                    member.get('yc_profile_url')
                ))
            except Exception as e:
                print(f"  Error saving member {member.get('name')}: {e}")
        
        conn.commit()
        conn.close()

if __name__ == "__main__":
    import sys
    
    limit = None
    if len(sys.argv) > 1:
        limit = int(sys.argv[1])
    
    scraper = MemberScraper()
    scraper.scrape_all_companies(limit=limit, delay=2)

