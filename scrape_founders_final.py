#!/usr/bin/env python3
"""
Final, comprehensive Founder Scraper
Extracts founders using multiple methods including Twitter handles, JSON, and DOM structure
"""

import time
import sqlite3
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import json

class FinalFounderScraper:
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
        """Extract founders using comprehensive methods"""
        founders = []
        
        try:
            driver.get(company_url)
            time.sleep(6)  # Wait for page to fully load
            
            # Scroll to ensure all content loads
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)
            
            page_text = driver.find_element(By.TAG_NAME, "body").text
            page_text_lower = page_text.lower()
            
            yc_partners = {'jared friedman', 'brad flora', 'gustaf alstromer', 
                          'harj taggar', 'aaron epstein', 'david lieb', 'paul graham',
                          'jessica livingston', 'trevor blackwell', 'robert morris'}
            
            # METHOD 0: Look for "Active Founders" section explicitly - AGGRESSIVE VERSION
            try:
                active_founders_heading = driver.find_elements(By.XPATH, "//*[contains(text(), 'Active Founders')]")
                for heading in active_founders_heading:
                    try:
                        # Get the section that contains founders
                        # Try multiple approaches to get the right container
                        section = None
                        for level in range(1, 8):
                            try:
                                candidate = heading.find_element(By.XPATH, f"./ancestor::*[position()={level}]")
                                candidate_text = candidate.text
                                # Check if this section has names and "Founder" text
                                if 'founder' in candidate_text.lower() and len(candidate_text) < 5000:
                                    section = candidate
                                    break
                            except:
                                continue
                        
                        if not section:
                            section = heading.find_element(By.XPATH, "./following-sibling::*[1] | ./parent::*")
                        
                        # Get ALL text from the section
                        section_text = section.text
                        
                        # Split into lines and extract names
                        all_lines = section_text.split('\n')
                        lines = [l.strip() for l in all_lines if l.strip()]
                        
                        # Find where "Active Founders" appears
                        active_founders_idx = None
                        for i, line in enumerate(all_lines):
                            if 'Active Founders' in line:
                                active_founders_idx = i
                                break
                        
                        false_positives = {'company launches', 'egress health', 'active founders', 
                                         'founder directory', 'find a co-founder', 'co-founder matching',
                                         'home', 'companies', 'jobs', 'news', 'company', 'active',
                                         'latest news', 'why the next', 'see original', 'tl;dr',
                                         'pete koomen', 'harj taggar', 'aaron epstein'}  # Known YC partners
                        
                        # Extract names from lines AFTER "Active Founders" 
                        # Stop when we hit a major section like "Latest News" or "Company Launches"
                        start_idx = active_founders_idx + 1 if active_founders_idx else 0
                        end_markers = ['latest news', 'company launches', 'tl;dr', 'problem', 'solution', 'ask']
                        end_idx = len(all_lines)
                        
                        # Find where to stop (next major section)
                        for i in range(start_idx, len(all_lines)):
                            line_lower = all_lines[i].strip().lower()
                            if any(marker in line_lower for marker in end_markers):
                                end_idx = i
                                break
                        
                        # Now extract names from this range
                        for i in range(start_idx, end_idx):
                            line = all_lines[i].strip()
                            if not line:
                                continue
                            
                            # Check if this line looks like a name (2-4 words, capitalized)
                            words = line.split()
                            if (len(words) >= 2 and len(words) <= 4 and
                                all(w and w[0].isupper() for w in words) and
                                line.lower() not in yc_partners and
                                line.lower() not in false_positives and
                                not any(w.lower() in false_positives for w in words)):
                                
                                # Check if next line contains "Founder" - this confirms it's a founder name
                                is_founder = False
                                role = 'Founder'
                                
                                # Check next 2 lines for "Founder"
                                for j in range(i+1, min(i+3, len(all_lines))):
                                    next_line = all_lines[j].strip().lower()
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
                                    yc_profile_url = None
                                    linkedin_url = None
                                    twitter_url = None
                                
                                # Try to find /people/ link for this name
                                try:
                                    name_link = section.find_element(By.XPATH, f".//a[contains(text(), '{name}')]")
                                    href = name_link.get_attribute('href')
                                    if href and '/people/' in href:
                                        yc_profile_url = href
                                except:
                                    # Try to find any /people/ link near this name
                                    try:
                                        name_elem = section.find_element(By.XPATH, f".//*[contains(text(), '{name}')]")
                                        nearby_links = name_elem.find_elements(By.XPATH, ".//a[contains(@href, '/people/')] | ./ancestor::a[contains(@href, '/people/')]")
                                        if nearby_links:
                                            yc_profile_url = nearby_links[0].get_attribute('href')
                                    except:
                                        pass
                                
                                # Find social links
                                try:
                                    name_elem = section.find_element(By.XPATH, f".//*[contains(text(), '{name}')]")
                                    parent = name_elem.find_element(By.XPATH, "./ancestor::*[position()<=5]")
                                    links = parent.find_elements(By.TAG_NAME, "a")
                                    for link in links:
                                        href = link.get_attribute('href')
                                        if href:
                                            if 'linkedin.com/in/' in href.lower() and 'company' not in href.lower():
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
                            
                            i += 1
                    except Exception as e:
                        continue
            except Exception as e:
                pass
            
            # METHOD 1: Extract from JSON (most reliable)
            try:
                json_data = driver.execute_script("""
                    if (window.__NEXT_DATA__) {
                        return JSON.stringify(window.__NEXT_DATA__);
                    }
                    return null;
                """)
                
                if json_data:
                    data = json.loads(json_data)
                    parsed_founders = self._parse_founders_from_json_comprehensive(data)
                    for founder in parsed_founders:
                        if founder['name'].lower() not in yc_partners:
                            if not any(f['name'].lower() == founder['name'].lower() for f in founders):
                                founders.append(founder)
            except Exception as e:
                pass
            
            # METHOD 2: Find ALL /people/ links and check context thoroughly
            # Also visit each profile to check if they're founders
            try:
                all_people_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/people/']")
                
                # If we have people links, visit each one to check if they're founders
                for link in all_people_links:
                    try:
                        href = link.get_attribute('href')
                        name = link.text.strip()
                        
                        if not name or len(name.split()) < 2 or len(name.split()) > 4:
                            continue
                        
                        if name.lower() in yc_partners:
                            continue
                        
                        # Visit the profile page to check if they're a founder
                        is_founder = False
                        role = None
                        linkedin_url = None
                        twitter_url = None
                        
                        try:
                            driver.get(href)
                            time.sleep(2)
                            profile_text = driver.find_element(By.TAG_NAME, "body").text.lower()
                            
                            # Check if this person is a founder
                            if 'founder' in profile_text or 'co-founder' in profile_text:
                                is_founder = True
                                
                                # Extract role from profile
                                if 'ceo' in profile_text and 'founder' in profile_text:
                                    role = 'Founder, CEO'
                                elif 'cto' in profile_text and 'founder' in profile_text:
                                    role = 'Founder, CTO'
                                elif 'coo' in profile_text and 'founder' in profile_text:
                                    role = 'Founder, COO'
                                else:
                                    role = 'Founder'
                                
                                # Find social links on profile page
                                profile_links = driver.find_elements(By.TAG_NAME, "a")
                                for l in profile_links:
                                    l_href = l.get_attribute('href')
                                    if not l_href:
                                        continue
                                    
                                    if 'linkedin.com/in/' in l_href.lower():
                                        if ('company' not in l_href.lower() and 
                                            'school' not in l_href.lower() and 
                                            '/admin/' not in l_href.lower()):
                                            linkedin_url = l_href
                                    
                                    elif ('twitter.com/' in l_href.lower() or 'x.com/' in l_href.lower()):
                                        if 'ycombinator' not in l_href.lower():
                                            twitter_url = l_href
                            
                            # Go back to company page
                            driver.get(company_url)
                            time.sleep(2)
                        except:
                            # If profile visit fails, check context on main page
                            driver.get(company_url)
                            time.sleep(2)
                            
                            # Check if name appears near "founder" in page text
                            name_pos = page_text_lower.find(name.lower())
                            if name_pos != -1:
                                window_start = max(0, name_pos - 800)
                                window_end = min(len(page_text_lower), name_pos + 800)
                                window_text = page_text_lower[window_start:window_end]
                                
                                if ('founder' in window_text or 'co-founder' in window_text) and 'yc partner' not in window_text:
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
                        # Make sure we're back on company page
                        try:
                            driver.get(company_url)
                            time.sleep(1)
                        except:
                            pass
                        continue
            except Exception as e:
                pass
            
            # METHOD 3: Extract from text patterns (including Twitter handles) and find their social links
            try:
                patterns = [
                    # Pattern for "@Username and @Username" (Twitter handles) - extract the handle parts as names
                    r"(?:we're|we are|hi yc[—\-]?we're|hi yc[—\-]?we're)\s+@([A-Z][a-zA-Z0-9_]+(?:\s+[A-Z][a-zA-Z0-9_]+)?)\s+and\s+@([A-Z][a-zA-Z0-9_]+(?:\s+[A-Z][a-zA-Z0-9_]+)?)",
                    # Pattern for "@Username and @Username, founders"
                    r"@([A-Z][a-zA-Z0-9_]+(?:\s+[A-Z][a-zA-Z0-9_]+)?)\s+and\s+@([A-Z][a-zA-Z0-9_]+(?:\s+[A-Z][a-zA-Z0-9_]+)?),?\s*(?:co-?founders?|founders?|former)",
                    # Pattern for "we're X and Y, founders" (with proper names)
                    r"(?:we're|we are|hi yc[—\-]?we're)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+and\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?),?\s+(?:co-?founders?|founders?|former)",
                    # Standard patterns
                    r"(?:we're|we are)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?(?:\s+and\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)*),?\s+(?:co-?founders?|founders?)",
                    r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?(?:\s+and\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)*)\s+(?:are|is)\s+(?:co-?founders?|founders?)",
                    r"Founded by\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?(?:\s+and\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)*)",
                ]
                
                false_positives = {'active founders', 'founder matching', 'back office', 'people', 
                                 'founders', 'founder directory', 'co-founder matching', 'find a co-founder',
                                 'the', 're the', 'yc partner', 'aaron epstein'}
                
                def find_social_links_for_name(name, driver):
                    """Find LinkedIn and Twitter links associated with a founder name"""
                    linkedin_url = None
                    twitter_url = None
                    
                    try:
                        # Find elements containing the name
                        name_elements = driver.find_elements(By.XPATH, f"//*[contains(text(), '{name}')]")
                        
                        for elem in name_elements[:5]:  # Check first few matches
                            try:
                                # Look in ancestor containers (parent sections)
                                for level in range(1, 10):
                                    try:
                                        ancestor = elem.find_element(By.XPATH, f"./ancestor::*[position()={level}]")
                                        
                                        # Find all links in this section
                                        links = ancestor.find_elements(By.TAG_NAME, "a")
                                        
                                        for link in links:
                                            href = link.get_attribute('href')
                                            if not href:
                                                continue
                                            
                                            # Check if this is a LinkedIn link - prioritize personal profiles
                                            if 'linkedin.com/in/' in href.lower():
                                                # Exclude company, school, and admin pages
                                                if ('company' not in href.lower() and 
                                                    'school' not in href.lower() and 
                                                    '/admin/' not in href.lower() and
                                                    '/dashboard' not in href.lower()):
                                                    # Check if link text or nearby text matches the name
                                                    link_text = link.text.strip().lower()
                                                    name_lower = name.lower()
                                                    
                                                    # Simple check: if name words appear in link context
                                                    name_words = name_lower.split()
                                                    if any(word in link_text or word in href.lower() for word in name_words if len(word) > 3):
                                                        # Prefer links that match the name better
                                                        if not linkedin_url or name_lower in href.lower():
                                                            linkedin_url = href
                                            
                                            # Check if this is a Twitter/X link
                                            elif ('twitter.com/' in href.lower() or 'x.com/' in href.lower()) and 'ycombinator' not in href.lower():
                                                link_text = link.text.strip().lower()
                                                name_lower = name.lower()
                                                name_words = name_lower.split()
                                                if any(word in link_text or word in href.lower() for word in name_words if len(word) > 3):
                                                    twitter_url = href
                                            
                                            if linkedin_url and twitter_url:
                                                break
                                        
                                        if linkedin_url or twitter_url:
                                            break
                                    except:
                                        continue
                                
                                if linkedin_url or twitter_url:
                                    break
                            except:
                                continue
                    except Exception as e:
                        pass
                    
                    return linkedin_url, twitter_url
                
                # Use the helper method
                find_social_links_for_name = lambda name, driver: self._find_social_links_for_name(name, driver)
                
                for pattern in patterns:
                    matches = re.finditer(pattern, page_text, re.IGNORECASE)
                    for match in matches:
                        # Handle patterns with 2 capture groups (for "X and Y")
                        if len(match.groups()) == 2:
                            name1 = match.group(1).strip()
                            name2 = match.group(2).strip()
                            
                            # Process both names
                            for name in [name1, name2]:
                                if not name:
                                    continue
                                
                                # Handle Twitter handles - convert to proper name format
                                if name.startswith('@'):
                                    name = name[1:]  # Remove @
                                
                                # Convert underscore/hyphen separated handles to space-separated names
                                # e.g., "Cinnamon_Sipper" -> "Cinnamon Sipper"
                                name = name.replace('_', ' ').replace('-', ' ')
                                
                                # Capitalize properly
                                words = name.split()
                                name = ' '.join([w.capitalize() for w in words])
                                
                                if (name and 
                                    len(name.split()) >= 2 and 
                                    len(name.split()) <= 4 and
                                    name.lower() not in false_positives and
                                    name.lower() not in yc_partners and
                                    not any(word.lower() in false_positives for word in name.split())):
                                    
                                    if not any(f['name'].lower() == name.lower() for f in founders):
                                        # Find social links for this founder
                                        linkedin_url, twitter_url = find_social_links_for_name(name, driver)
                                        
                                        founders.append({
                                            'name': name,
                                            'role': 'Founder',
                                            'yc_profile_url': None,
                                            'linkedin_url': linkedin_url,
                                            'twitter_url': twitter_url,
                                            'previous_company': None,
                                            'bio': None
                                        })
                        else:
                            # Single capture group pattern
                            names_str = match.group(1)
                            names = re.split(r'\s+and\s+|\s*,\s*', names_str)
                            for name in names:
                                name = name.strip()
                                if name.lower().startswith('and '):
                                    name = name[4:].strip()
                                
                                # Handle Twitter handles
                                if name.startswith('@'):
                                    name = name[1:]
                                name = name.replace('_', ' ').replace('-', ' ')
                                words = name.split()
                                name = ' '.join([w.capitalize() for w in words])
                                
                                if (name and 
                                    len(name.split()) >= 2 and 
                                    len(name.split()) <= 3 and
                                    name.lower() not in false_positives and
                                    name.lower() not in yc_partners and
                                    not any(word.lower() in false_positives for word in name.split())):
                                    
                                    if not any(f['name'].lower() == name.lower() for f in founders):
                                        # Find social links for this founder
                                        linkedin_url, twitter_url = find_social_links_for_name(name, driver)
                                        
                                        founders.append({
                                            'name': name,
                                            'role': 'Founder',
                                            'yc_profile_url': None,
                                            'linkedin_url': linkedin_url,
                                            'twitter_url': twitter_url,
                                            'previous_company': None,
                                            'bio': None
                                        })
            except Exception as e:
                pass
            
            # METHOD 4: Look for founder cards/sections by class names
            try:
                # Look for elements with founder-related classes
                founder_elements = driver.find_elements(By.CSS_SELECTOR, 
                    "[class*='founder'], [class*='Founder'], [class*='team-member'], [class*='person-card']")
                
                for elem in founder_elements[:20]:  # Limit to avoid too many
                    try:
                        text = elem.text.strip()
                        if not text or len(text) < 5:
                            continue
                        
                        # Look for name pattern
                        lines = [l.strip() for l in text.split('\n') if l.strip()]
                        if len(lines) >= 2:
                            # First line is usually name
                            name = lines[0]
                            if len(name.split()) >= 2 and len(name.split()) <= 4:
                                if name.lower() not in yc_partners:
                                    # Check if this element is in a founder section
                                    try:
                                        parent = elem.find_element(By.XPATH, "./ancestor::*[position()<=5]")
                                        parent_text = parent.text.lower()
                                        if 'founder' in parent_text:
                                            role = None
                                            for line in lines[1:]:
                                                if 'founder' in line.lower():
                                                    role = line
                                                    break
                                            
                                            if not any(f['name'].lower() == name.lower() for f in founders):
                                                founders.append({
                                                    'name': name,
                                                    'role': role or 'Founder',
                                                    'yc_profile_url': None,
                                                    'linkedin_url': None,
                                                    'twitter_url': None,
                                                    'previous_company': None,
                                                    'bio': None
                                                })
                                    except:
                                        pass
                    except:
                        continue
            except Exception as e:
                pass
            
            # FALLBACK: If no founders found, try more aggressive methods
            if len(founders) == 0:
                print(f"  ⚠️  No founders found with standard methods, trying aggressive fallback...")
                founders = self._aggressive_founder_search(driver, company_url, company_name, page_text)
            
            # FINAL FALLBACK: If STILL no founders, visit /people/ page and check ALL people
            if len(founders) == 0:
                print(f"  ⚠️  Still no founders, checking /people/ page for ALL people...")
                try:
                    people_url = company_url.rstrip('/') + '/people'
                    driver.get(people_url)
                    time.sleep(4)
                    
                    people_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/people/']")
                    print(f"    Found {len(people_links)} people links on /people/ page")
                    
                    # If there are people links, assume first few are founders
                    for link in people_links[:5]:  # Check first 5 people
                        try:
                            href = link.get_attribute('href')
                            name = link.text.strip()
                            
                            if (name and len(name.split()) >= 2 and len(name.split()) <= 4 and
                                name.lower() not in yc_partners):
                                
                                # Visit profile to confirm
                                try:
                                    driver.get(href)
                                    time.sleep(2)
                                    profile_text = driver.find_element(By.TAG_NAME, "body").text.lower()
                                    
                                    # If profile mentions company name or founder, include them
                                    if company_name.lower().split('\n')[0].lower() in profile_text or 'founder' in profile_text:
                                        linkedin_url, twitter_url = self._find_social_links_for_name(name, driver)
                                        
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
                                except:
                                    # If we can't visit profile, still add them as potential founder
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
                                
                                driver.get(people_url)
                                time.sleep(1)
                        except:
                            continue
                    
                    driver.get(company_url)
                    time.sleep(2)
                except Exception as e:
                    print(f"    Error checking /people/ page: {e}")
                    try:
                        driver.get(company_url)
                        time.sleep(2)
                    except:
                        pass
            
            return founders
            
        except Exception as e:
            error_msg = str(e)
            # Check if it's a session error
            if 'invalid session id' in error_msg.lower() or 'session deleted' in error_msg.lower():
                raise RuntimeError("Browser session crashed - need to restart driver")
            print(f"Error extracting founders: {e}")
            return []
    
    def _aggressive_founder_search(self, driver, company_url, company_name, page_text):
        """Aggressive fallback methods when no founders are found"""
        founders = []
        yc_partners = {'jared friedman', 'brad flora', 'gustaf alstromer', 
                      'harj taggar', 'aaron epstein', 'david lieb', 'paul graham',
                      'jessica livingston', 'trevor blackwell', 'robert morris'}
        
        try:
            # FALLBACK 1: Try visiting /people/ page if it exists
            try:
                people_url = company_url.rstrip('/') + '/people'
                driver.get(people_url)
                time.sleep(4)
                
                # Look for all /people/ links on the people page
                people_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/people/']")
                for link in people_links:
                    try:
                        href = link.get_attribute('href')
                        name = link.text.strip()
                        
                        if (name and len(name.split()) >= 2 and len(name.split()) <= 4 and
                            name.lower() not in yc_partners):
                            
                            # Check if this person is a founder by looking at their profile page
                            try:
                                driver.get(href)
                                time.sleep(3)
                                profile_text = driver.find_element(By.TAG_NAME, "body").text.lower()
                                
                                if 'founder' in profile_text or 'co-founder' in profile_text:
                                    # Find social links
                                    linkedin_url, twitter_url = self._find_social_links_for_name(name, driver)
                                    
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
                            except:
                                pass
                            
                            # Go back to people page
                            driver.get(people_url)
                            time.sleep(2)
                    except:
                        continue
                
                # Go back to company page
                driver.get(company_url)
                time.sleep(3)
            except Exception as e:
                pass
            
            # FALLBACK 2: Extract ALL names from /people/ links and check context more carefully
            if len(founders) == 0:
                try:
                    driver.get(company_url)
                    time.sleep(4)
                    
                    all_people_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/people/']")
                    for link in all_people_links:
                        try:
                            href = link.get_attribute('href')
                            name = link.text.strip()
                            
                            if not name or len(name.split()) < 2 or len(name.split()) > 4:
                                continue
                            
                            if name.lower() in yc_partners:
                                continue
                            
                            # Check if name appears in founder context anywhere on page
                            if 'founder' in page_text.lower() or 'co-founder' in page_text.lower():
                                # Get surrounding context
                                try:
                                    parent = link.find_element(By.XPATH, "./ancestor::*[position()<=10]")
                                    context = parent.text.lower()
                                    
                                    # If context mentions founder or this person, include them
                                    if ('founder' in context or name.lower() in context):
                                        linkedin_url, twitter_url = self._find_social_links_for_name(name, driver)
                                        
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
                                except:
                                    pass
                        except:
                            continue
                except Exception as e:
                    pass
            
            # FALLBACK 3: Extract names from launch post or description text
            if len(founders) == 0:
                try:
                    # Look for patterns like "Hi YC, we're X and Y"
                    patterns = [
                        r"(?:hi yc|hello yc|we're|we are)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+and\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
                        r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+and\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(?:are|were|is|was)\s+(?:the\s+)?(?:co-?)?founders?",
                        r"founded by\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+and\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
                        r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+&\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(?:are|were|is|was)\s+(?:the\s+)?(?:co-?)?founders?",
                    ]
                    
                    for pattern in patterns:
                        matches = re.finditer(pattern, page_text, re.IGNORECASE)
                        for match in matches:
                            if len(match.groups()) == 2:
                                name1 = match.group(1).strip()
                                name2 = match.group(2).strip()
                                
                                for name in [name1, name2]:
                                    if (name and len(name.split()) >= 2 and len(name.split()) <= 4 and
                                        name.lower() not in yc_partners):
                                        
                                        linkedin_url, twitter_url = self._find_social_links_for_name(name, driver)
                                        
                                        if not any(f['name'].lower() == name.lower() for f in founders):
                                            founders.append({
                                                'name': name,
                                                'role': 'Founder',
                                                'yc_profile_url': None,
                                                'linkedin_url': linkedin_url,
                                                'twitter_url': twitter_url,
                                                'previous_company': None,
                                                'bio': None
                                            })
                except Exception as e:
                    pass
            
            # FALLBACK 4: Look for any names mentioned with "founder" nearby in text
            if len(founders) == 0:
                try:
                    # Find all text nodes that contain "founder"
                    founder_mentions = driver.find_elements(By.XPATH, "//*[contains(text(), 'founder') or contains(text(), 'Founder')]")
                    
                    for elem in founder_mentions[:20]:
                        try:
                            # Get parent container
                            parent = elem.find_element(By.XPATH, "./ancestor::*[position()<=5]")
                            text = parent.text
                            
                            # Extract names from this section
                            # Look for patterns like "Name Name, Founder" or "Founder: Name Name"
                            name_patterns = [
                                r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?),?\s+(?:co-?)?founder",
                                r"(?:co-?)?founder[s]?:?\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
                            ]
                            
                            for pattern in name_patterns:
                                matches = re.finditer(pattern, text, re.IGNORECASE)
                                for match in matches:
                                    name = match.group(1).strip()
                                    if (name and len(name.split()) >= 2 and len(name.split()) <= 4 and
                                        name.lower() not in yc_partners):
                                        
                                        # Check if there's a /people/ link for this name
                                        try:
                                            people_link = parent.find_element(By.XPATH, f".//a[contains(text(), '{name}')]")
                                            href = people_link.get_attribute('href')
                                            if '/people/' in href:
                                                linkedin_url, twitter_url = self._find_social_links_for_name(name, driver)
                                                
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
                                        except:
                                            pass
                        except:
                            continue
                except Exception as e:
                    pass
            
            return founders
            
        except Exception as e:
            print(f"  Error in aggressive search: {e}")
            return []
    
    def _find_social_links_for_name(self, name, driver):
        """Helper to find social links for a founder name"""
        linkedin_url = None
        twitter_url = None
        
        try:
            # Find elements containing the name
            name_elements = driver.find_elements(By.XPATH, f"//*[contains(text(), '{name}')]")
            
            for elem in name_elements[:5]:
                try:
                    # Look in ancestor containers
                    for level in range(1, 10):
                        try:
                            ancestor = elem.find_element(By.XPATH, f"./ancestor::*[position()={level}]")
                            links = ancestor.find_elements(By.TAG_NAME, "a")
                            
                            for link in links:
                                href = link.get_attribute('href')
                                if not href:
                                    continue
                                
                                if 'linkedin.com/in/' in href.lower():
                                    if ('company' not in href.lower() and 'school' not in href.lower() and 
                                        '/admin/' not in href.lower() and '/dashboard' not in href.lower()):
                                        if not linkedin_url or name.lower() in href.lower():
                                            linkedin_url = href
                                
                                elif ('twitter.com/' in href.lower() or 'x.com/' in href.lower()):
                                    if 'ycombinator' not in href.lower():
                                        if not twitter_url or name.lower() in href.lower():
                                            twitter_url = href
                            
                            if linkedin_url or twitter_url:
                                break
                        except:
                            continue
                    
                    if linkedin_url or twitter_url:
                        break
                except:
                    continue
        except:
            pass
        
        return linkedin_url, twitter_url
    
    def _parse_founders_from_json_comprehensive(self, data):
        """Comprehensive JSON parsing"""
        founders = []
        
        def extract_founders(obj, path="", depth=0):
            if depth > 20:
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
                for key in ['founders', 'activeFounders', 'active_founders', 'team', 'people', 'members']:
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
        """Scrape founders from all companies that don't have founders yet"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get ONLY companies without founders
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
        
        print(f"Found {len(companies)} companies WITHOUT founders to scrape")
        print(f"Delay between requests: {delay} seconds")
        print(f"⚠️  If no founders are found, scraper will try aggressive fallback methods\n")
        
        driver = self.setup_driver()
        total_founders = 0
        
        try:
            for i, (company_id, company_name, yc_url) in enumerate(companies, 1):
                clean_company_name = company_name.split('\n')[0] if company_name else 'Unknown'
                
                print(f"[{i}/{len(companies)}] Scraping {clean_company_name}...")
                
                try:
                    founders = self.extract_founders_from_page(driver, yc_url, clean_company_name)
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
                            founders = self.extract_founders_from_page(driver, yc_url, clean_company_name)
                        except Exception as retry_e:
                            print(f"    Error on retry: {retry_e}")
                            founders = []
                    else:
                        raise
                
                if founders:
                    self.save_founders(company_id, clean_company_name, founders)
                    total_founders += len(founders)
                    founder_names = ', '.join([f['name'] for f in founders])
                    print(f"  ✓ Found {len(founders)} founder(s): {founder_names}")
                else:
                    print(f"  ❌ WARNING: No founders found for {clean_company_name}")
                    print(f"     This is unusual - all companies should have founders. Check manually if needed.")
                
                if i < len(companies):
                    time.sleep(delay)
                    
        finally:
            try:
                driver.quit()
            except:
                pass
        
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
    
    scraper = FinalFounderScraper()
    scraper.scrape_all_companies(limit=limit, delay=2)

