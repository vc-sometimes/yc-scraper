#!/usr/bin/env python3
"""
SIMPLE founder scraper - just gets what's under "Active Founders"
"""

import time
import sqlite3
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import re
import json
import os

# Debug logging setup
DEBUG_LOG_PATH = '/Users/vc/yc scraper/.cursor/debug.log'

def debug_log(session_id, run_id, hypothesis_id, location, message, data):
    """Write debug log entry"""
    try:
        log_entry = {
            'sessionId': session_id,
            'runId': run_id,
            'hypothesisId': hypothesis_id,
            'location': location,
            'message': message,
            'data': data,
            'timestamp': int(time.time() * 1000)
        }
        with open(DEBUG_LOG_PATH, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
    except:
        pass

class SimpleFounderScraper:
    def __init__(self, db_path='yc_companies.db'):
        self.db_path = db_path
        self.setup_database()
        
    def setup_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS founders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER,
                company_name TEXT,
                name TEXT NOT NULL,
                role TEXT,
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
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        driver = webdriver.Chrome(options=chrome_options)
        return driver
    
    def extract_founders_simple(self, driver, company_url, company_name):
        """Just get what's under Active Founders - SIMPLE"""
        founders = []
        session_id = 'debug-session'
        run_id = 'run1'
        
        # #region agent log
        debug_log(session_id, run_id, 'A', 'extract_founders_simple:entry', 'Starting extraction', {'url': company_url, 'company': company_name})
        # #endregion
        
        try:
            driver.get(company_url)
            time.sleep(5)
            
            # #region agent log
            debug_log(session_id, run_id, 'A', 'extract_founders_simple:after_load', 'Page loaded', {'url': company_url})
            # #endregion
            
            # Find "Active Founders" heading
            try:
                # #region agent log
                debug_log(session_id, run_id, 'B', 'extract_founders_simple:searching_heading', 'Searching for Active Founders heading', {'url': company_url})
                # #endregion
                
                heading = driver.find_element(By.XPATH, "//*[contains(text(), 'Active Founders')]")
                
                # #region agent log
                debug_log(session_id, run_id, 'B', 'extract_founders_simple:found_heading', 'Found Active Founders heading', {'tag': heading.tag_name, 'text': heading.text[:100]})
                # #endregion
                
                # Get the parent container
                container = heading.find_element(By.XPATH, "./parent::*")
                
                # Get the actual section container - find the RIGHT level
                # We want a section that has "Active Founders" but NOT the entire page header
                section = None
                best_section = None
                best_score = 0
        
                for level in range(1, 6):
                    try:
                        candidate = heading.find_element(By.XPATH, f"./ancestor::*[position()={level}]")
                        candidate_text = candidate.text
                        lines = candidate_text.split('\n')
                        line_count = len(lines)
                        
                        # Score: prefer sections with "Active Founders" early and reasonable size
                        # Penalize sections that start with company name/page header
                        score = 0
                        active_founders_idx = None
                        for i, line in enumerate(lines):
                            if 'Active Founders' in line:
                                active_founders_idx = i
                                break
                        
                        if active_founders_idx is not None:
                            # Prefer sections where "Active Founders" appears early (first 3 lines)
                            if active_founders_idx < 3:
                                score += 20
                            elif active_founders_idx < 5:
                                score += 10
                            # Prefer sections with reasonable size (3-30 lines is ideal)
                            # Allow smaller sections (3-4 lines) if they have founder names
                            if 3 <= line_count <= 30:
                                score += 15
                            elif 30 < line_count <= 50:
                                score += 5
                            # CRITICAL: Check if section actually contains founder names (capitalized 2-word names)
                            # This is more important than size
                            has_founder_names = False
                            for line in lines[active_founders_idx+1:active_founders_idx+10]:
                                words = line.split()
                                if len(words) >= 2 and len(words) <= 4:
                                    if all(w and w[0].isupper() for w in words):
                                        # Check if next line has "Founder"
                                        line_idx = lines.index(line) if line in lines else -1
                                        if line_idx >= 0 and line_idx + 1 < len(lines):
                                            next_line = lines[line_idx + 1].lower()
                                            if 'founder' in next_line:
                                                has_founder_names = True
                                                break
                            if has_founder_names:
                                score += 30  # HUGE bonus for sections with actual founder names
                            # STRONG penalty if section starts with company name or page header markers
                            first_lines = ' '.join(lines[:3]).lower()
                            if any(marker in first_lines for marker in ['fall 202', 'winter 202', 'spring 202', 'summer 202', 'home', 'companies', 'company', 'jobs']):
                                score -= 50  # Strong penalty
                            # Prefer sections that have "Founder" text after "Active Founders"
                            if 'founder' in candidate_text.lower():
                                score += 10
                        
                        # #region agent log
                        debug_log(session_id, run_id, 'C', f'extract_founders_simple:check_level_{level}', 'Checking ancestor level', {
                            'level': level, 
                            'line_count': line_count, 
                            'active_idx': active_founders_idx,
                            'score': score,
                            'first_lines': ' '.join(lines[:3])[:100]
                        })
                        # #endregion
                        
                        if score > best_score:
                            best_section = candidate
                            best_score = score
                    except Exception as e:
                        # #region agent log
                        debug_log(session_id, run_id, 'C', f'extract_founders_simple:level_error', 'Error checking level', {'level': level, 'error': str(e)})
                        # #endregion
                        continue
                
                if best_section and best_score > 0:
                    section = best_section
                    # #region agent log
                    debug_log(session_id, run_id, 'C', 'extract_founders_simple:selected_best_section', 'Selected best section', {'score': best_score})
                    # #endregion
                else:
                    section = container
                    # #region agent log
                    debug_log(session_id, run_id, 'C', 'extract_founders_simple:using_container', 'Using default container', {'best_score': best_score})
                    # #endregion
                
                # Get ALL text from this section
                section_text = section.text
                
                # #region agent log
                debug_log(session_id, run_id, 'D', 'extract_founders_simple:got_section_text', 'Got section text', {'text_length': len(section_text), 'first_200_chars': section_text[:200]})
                # #endregion
                
                # Split into lines
                lines = [l.strip() for l in section_text.split('\n') if l.strip()]
                
                # #region agent log
                debug_log(session_id, run_id, 'D', 'extract_founders_simple:split_lines', 'Split into lines', {'line_count': len(lines), 'first_10_lines': lines[:10]})
                # #endregion
                
                # Find where "Active Founders" is
                active_idx = None
                for i, line in enumerate(lines):
                    if 'Active Founders' in line:
                        active_idx = i
                        break
                
                # #region agent log
                debug_log(session_id, run_id, 'D', 'extract_founders_simple:found_active_idx', 'Found Active Founders index', {'active_idx': active_idx})
                # #endregion
                
                if active_idx is not None:
                    # Get next lines after "Active Founders"
                    yc_partners = {'pete koomen', 'harj taggar', 'aaron epstein', 'jared friedman'}
                    
                    i = active_idx + 1
                    while i < len(lines) and i < active_idx + 30:
                        line = lines[i]
                        
                        # Stop if we hit a major section
                        if any(marker in line.lower() for marker in ['latest news', 'company launches', 'tl;dr', 'problem:', 'solution:', 'ask:']):
                            break
                        
                        # Check if this line is a name (2-4 words, all capitalized first letters)
                        words = line.split()
                        word_count_valid = len(words) >= 2 and len(words) <= 4
                        all_capitalized = all(w and w[0].isupper() for w in words) if words else False
                        not_yc_partner = line.lower() not in yc_partners
                        is_name_format = word_count_valid and all_capitalized and not_yc_partner
                        
                        # #region agent log
                        debug_log(session_id, run_id, 'E', f'extract_founders_simple:check_line_{i}', 'Checking line for name', {
                            'line': line, 
                            'is_name_format': is_name_format, 
                            'word_count': len(words),
                            'word_count_valid': word_count_valid,
                            'all_capitalized': all_capitalized,
                            'not_yc_partner': not_yc_partner,
                            'is_yc_partner': line.lower() in yc_partners
                        })
                        # #endregion
                        
                        if is_name_format:
                            
                            # Check if next line says "Founder"
                            if i + 1 < len(lines):
                                next_line = lines[i + 1].lower()
                                has_founder = 'founder' in next_line
                                
                                # #region agent log
                                debug_log(session_id, run_id, 'E', f'extract_founders_simple:check_next_line_{i}', 'Checking next line for Founder', {'next_line': lines[i+1], 'has_founder': has_founder})
                                # #endregion
                                
                                if has_founder:
                                    name = line
                                    role = 'Founder'
                                    
                                    # Determine role
                                    if 'co-founder' in next_line or 'cofounder' in next_line:
                                        role = 'Co-founder'
                                    elif 'ceo' in next_line:
                                        role = 'Founder, CEO'
                                    elif 'cto' in next_line:
                                        role = 'Founder, CTO'
                                    
                                    # Try to find links
                                    yc_profile_url = None
                                    linkedin_url = None
                                    twitter_url = None
                                    
                                    try:
                                        # Find element with this name
                                        name_elem = section.find_element(By.XPATH, f".//*[contains(text(), '{name}')]")
                                        parent = name_elem.find_element(By.XPATH, "./ancestor::*[position()<=5]")
                                        links = parent.find_elements(By.TAG_NAME, "a")
                                        
                                        # #region agent log
                                        debug_log(session_id, run_id, 'F', f'extract_founders_simple:found_links_{name}', 'Found links for name', {'name': name, 'link_count': len(links)})
                                        # #endregion
                                        
                                        for link in links:
                                            href = link.get_attribute('href')
                                            if href:
                                                if '/people/' in href:
                                                    yc_profile_url = href
                                                    # #region agent log
                                                    debug_log(session_id, run_id, 'F', f'extract_founders_simple:found_yc_link', 'Found YC profile link', {'name': name, 'url': href})
                                                    # #endregion
                                                elif 'linkedin.com/in/' in href.lower() and 'company' not in href.lower():
                                                    linkedin_url = href
                                                    # #region agent log
                                                    debug_log(session_id, run_id, 'F', f'extract_founders_simple:found_linkedin', 'Found LinkedIn link', {'name': name, 'url': href})
                                                    # #endregion
                                                elif ('twitter.com/' in href.lower() or 'x.com/' in href.lower()) and 'ycombinator' not in href.lower():
                                                    twitter_url = href
                                                    # #region agent log
                                                    debug_log(session_id, run_id, 'F', f'extract_founders_simple:found_twitter', 'Found Twitter/X link', {'name': name, 'url': href})
                                                    # #endregion
                                    except Exception as e:
                                        # #region agent log
                                        debug_log(session_id, run_id, 'F', f'extract_founders_simple:link_error', 'Error finding links', {'name': name, 'error': str(e)})
                                        # #endregion
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
                                        # #region agent log
                                        debug_log(session_id, run_id, 'E', f'extract_founders_simple:added_founder', 'Added founder', {'name': name, 'role': role, 'has_yc': yc_profile_url is not None, 'has_linkedin': linkedin_url is not None, 'has_twitter': twitter_url is not None})
                                        # #endregion
                                    
                                    i += 2  # Skip the "Founder" line and move to next name
                                    continue
                            
                        i += 1
                            
            except Exception as e:
                # #region agent log
                error_type = type(e).__name__
                page_has_founder_text = 'founder' in driver.find_element(By.TAG_NAME, 'body').text.lower()
                debug_log(session_id, run_id, 'B', 'extract_founders_simple:heading_error', 'Error finding Active Founders', {
                    'error': str(e), 
                    'error_type': error_type,
                    'page_has_founder_text': page_has_founder_text,
                    'page_text_sample': driver.find_element(By.TAG_NAME, 'body').text[:500]
                })
                # #endregion
                pass
            
            # #region agent log
            debug_log(session_id, run_id, 'A', 'extract_founders_simple:exit', 'Returning founders', {'founder_count': len(founders), 'founder_names': [f['name'] for f in founders]})
            # #endregion
            
            return founders
            
        except Exception as e:
            # #region agent log
            debug_log(session_id, run_id, 'A', 'extract_founders_simple:exception', 'Exception in extraction', {'error': str(e), 'error_type': type(e).__name__})
            # #endregion
            return []
    
    def scrape_all(self, limit=None):
        import sys
        # Force unbuffered output
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT DISTINCT c.id, c.name, c.yc_url 
            FROM companies c
            LEFT JOIN founders f ON c.id = f.company_id
            WHERE c.yc_url LIKE "%/companies/%" 
            AND c.yc_url NOT LIKE "%?%" 
            AND c.yc_url NOT LIKE "%industry=%" 
            AND c.yc_url NOT LIKE "%batch=%"
            AND f.id IS NULL
            ORDER BY c.name
        ''')
        if limit:
            companies = cursor.fetchall()[:limit]
        else:
            companies = cursor.fetchall()
        conn.close()
        
        print(f"Processing {len(companies)} companies...\n", flush=True)
        
        driver = self.setup_driver()
        total = 0
        
        try:
            for i, (company_id, company_name, yc_url) in enumerate(companies, 1):
                clean_name = company_name.split('\n')[0]
                print(f"[{i}/{len(companies)}] {clean_name}")
                
                founders = self.extract_founders_simple(driver, yc_url, clean_name)
                
                # #region agent log
                debug_log('debug-session', 'run1', 'G', f'scrape_all:company_{i}', 'Processing company', {'company_id': company_id, 'company_name': clean_name, 'founder_count': len(founders), 'founder_names': [f['name'] for f in founders]})
                # #endregion
                
                if founders:
                    self.save_founders(company_id, clean_name, founders)
                    # #region agent log
                    debug_log('debug-session', 'run1', 'G', f'scrape_all:saved_{i}', 'Saved founders', {'company_id': company_id, 'saved_count': len(founders)})
                    # #endregion
                    total += len(founders)
                    names = ', '.join([f['name'] for f in founders])
                    print(f"  ✅ Found {len(founders)}: {names}", flush=True)
                else:
                    print(f"  ⚠️  No founders", flush=True)
                
                time.sleep(2)
        finally:
            driver.quit()
        
        print(f"\n✅ Done! Found {total} founders total", flush=True)
    
    def save_founders(self, company_id, company_name, founders):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        saved_count = 0
        for f in founders:
            try:
                cursor.execute('''
                    INSERT OR REPLACE INTO founders 
                    (company_id, company_name, name, role, linkedin_url, twitter_url, yc_profile_url, bio)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (company_id, company_name, f['name'], f['role'], 
                      f.get('linkedin_url'), f.get('twitter_url'), f.get('yc_profile_url'), None))
                saved_count += 1
                # #region agent log
                debug_log('debug-session', 'run1', 'H', 'save_founders:inserted', 'Inserted founder', {'company_id': company_id, 'name': f['name'], 'has_linkedin': f.get('linkedin_url') is not None, 'has_twitter': f.get('twitter_url') is not None})
                # #endregion
            except Exception as e:
                # #region agent log
                debug_log('debug-session', 'run1', 'H', 'save_founders:error', 'Error saving founder', {'company_id': company_id, 'name': f['name'], 'error': str(e)})
                # #endregion
                pass
        conn.commit()
        conn.close()
        
        # #region agent log
        debug_log('debug-session', 'run1', 'H', 'save_founders:complete', 'Save complete', {'company_id': company_id, 'attempted': len(founders), 'saved': saved_count})
        # #endregion

if __name__ == "__main__":
    import sys
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    scraper = SimpleFounderScraper()
    scraper.scrape_all(limit=limit)

