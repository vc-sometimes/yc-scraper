#!/usr/bin/env python3
"""
YC Companies Scraper using Algolia API
Uses YC's public Algolia search API instead of web scraping
"""

import requests
import sqlite3
import json
from typing import List, Dict, Optional

class YCApiScraper:
    def __init__(self, db_path='yc_companies.db'):
        self.db_path = db_path
        self.algolia_app_id = "45BWZJ1SGC"
        self.algolia_api_key = "MjBjYjRiMzY0NzdhZWY0NjExY2NhZjYxMGIxYjc2MTAwNWFkNTkwNTc4NjgxYjU0YzFhYTY2ZGQ5OGY5NDMxZnJlc3RyaWN0SW5kaWNlcz0lNUIlMjJZQ0NvbXBhbnlfcHJvZHVjdGlvbiUyMiUyQyUyMllDQ29tcGFueV9CeV9MYXVuY2hfRGF0ZV9wcm9kdWN0aW9uJTIyJTVEJnRhZ0ZpbHRlcnM9JTVCJTIyeWNkY19wdWJsaWMlMjIlNUQmYW5hbHl0aWNzVGFncz0lNUIlMjJ5Y2RjJTIyJTVE"
        self.algolia_index = "YCCompany_production"
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
        print(f"Database initialized at {self.db_path}")
    
    def search_companies(self, query: str = "", filters: Optional[str] = None, hits_per_page: int = 1000, page: int = 0) -> List[Dict]:
        """
        Search YC companies using Algolia API
        
        Args:
            query: Search query string
            filters: Algolia filter string (e.g., "batch:W25")
            hits_per_page: Number of results per page (max 1000)
            page: Page number (0-indexed)
        
        Returns:
            List of company dictionaries
        """
        url = f"https://{self.algolia_app_id}-dsn.algolia.net/1/indexes/{self.algolia_index}/query"
        
        headers = {
            "X-Algolia-Application-Id": self.algolia_app_id,
            "X-Algolia-API-Key": self.algolia_api_key,
            "Content-Type": "application/json"
        }
        
        # Build params string for Algolia
        params_str = f"query={query}&hitsPerPage={hits_per_page}&page={page}"
        params_str += "&attributesToRetrieve=%5B%22name%22%2C%22batch%22%2C%22description%22%2C%22website%22%2C%22location%22%2C%22all_locations%22%2C%22industry%22%2C%22isHiring%22%2C%22slug%22%2C%22launchDate%22%2C%22tagline%22%2C%22oneLiner%22%2C%22long_description%22%2C%22founded%22%2C%22teamSize%22%2C%22founders%22%5D"
        
        if filters:
            params_str += f"&filters={filters}"
        
        try:
            response = requests.post(url, headers=headers, json={"params": params_str})
            response.raise_for_status()
            data = response.json()
            return data.get("hits", [])
        except Exception as e:
            print(f"Error searching companies: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response: {e.response.text[:500]}")
            return []
    
    def get_all_companies(self) -> List[Dict]:
        """Get all YC companies using pagination"""
        print("Fetching all companies from YC API...")
        all_companies = []
        page = 0
        hits_per_page = 1000
        
        while True:
            companies = self.search_companies(hits_per_page=hits_per_page, page=page)
            if not companies:
                break
            
            all_companies.extend(companies)
            print(f"Fetched page {page + 1}: {len(companies)} companies (total: {len(all_companies)})")
            
            if len(companies) < hits_per_page:
                break  # Last page
            
            page += 1
        
        print(f"\nFound {len(all_companies)} total companies")
        return all_companies
    
    def normalize_company_data(self, company: Dict) -> Dict:
        """Normalize company data from Algolia response"""
        return {
            'name': company.get('name', ''),
            'batch': company.get('batch', ''),
            'description': company.get('long_description') or company.get('description') or company.get('tagline') or company.get('oneLiner', ''),
            'website': company.get('website', ''),
            'location': company.get('all_locations') or company.get('location', ''),
            'industry': company.get('industry', ''),
            'is_hiring': company.get('isHiring', False),
            'yc_url': f"https://www.ycombinator.com/companies/{company.get('slug', '')}" if company.get('slug') else None,
            'founders': company.get('founders', [])
        }
    
    def save_companies(self, companies: List[Dict]):
        """Save companies to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        saved_count = 0
        updated_count = 0
        
        for company_data in companies:
            company = self.normalize_company_data(company_data)
            
            if not company['name']:
                continue
            
            try:
                # Check if company exists
                cursor.execute('SELECT id FROM companies WHERE name = ? AND (batch = ? OR (batch IS NULL AND ? IS NULL))', 
                             (company['name'], company['batch'], company['batch']))
                existing = cursor.fetchone()
                
                if existing:
                    # Update existing
                    cursor.execute('''
                        UPDATE companies 
                        SET batch = ?, description = ?, website = ?, location = ?, 
                            industry = ?, is_hiring = ?, yc_url = ?
                        WHERE id = ?
                    ''', (
                        company['batch'], company['description'], company['website'],
                        company['location'], company['industry'], company['is_hiring'],
                        company['yc_url'], existing[0]
                    ))
                    company_id = existing[0]
                    updated_count += 1
                else:
                    # Insert new
                    cursor.execute('''
                        INSERT INTO companies 
                        (name, batch, description, website, location, industry, is_hiring, yc_url)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        company['name'], company['batch'], company['description'],
                        company['website'], company['location'], company['industry'],
                        company['is_hiring'], company['yc_url']
                    ))
                    company_id = cursor.lastrowid
                    saved_count += 1
                
                # Save founders if available
                if company.get('founders') and isinstance(company['founders'], list):
                    self.save_founders(cursor, company_id, company['name'], company['founders'])
                
            except Exception as e:
                print(f"Error saving company {company['name']}: {e}")
        
        conn.commit()
        conn.close()
        print(f"\n✅ Saved {saved_count} new companies, updated {updated_count} existing companies")
    
    def save_founders(self, cursor, company_id: int, company_name: str, founders: List[Dict]):
        """Save founders to database"""
        for founder in founders:
            if not isinstance(founder, dict) or not founder.get('name'):
                continue
            
            try:
                cursor.execute('''
                    INSERT OR REPLACE INTO founders 
                    (company_id, company_name, name, role, previous_company, 
                     linkedin_url, twitter_url, yc_profile_url, bio)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    company_id,
                    company_name,
                    founder.get('name', ''),
                    founder.get('role', ''),
                    founder.get('previousCompany', '') or founder.get('previous_company', ''),
                    founder.get('linkedin', '') or founder.get('linkedinUrl', ''),
                    founder.get('twitter', '') or founder.get('twitterUrl', '') or founder.get('x', ''),
                    founder.get('ycUrl', '') or founder.get('yc_url', '') or founder.get('profileUrl', ''),
                    founder.get('bio', '') or founder.get('description', '')
                ))
            except Exception as e:
                print(f"  Error saving founder {founder.get('name')}: {e}")
    
    def scrape_all(self):
        """Scrape all companies from YC API"""
        companies = self.get_all_companies()
        if companies:
            self.save_companies(companies)
            print(f"\n✅ Successfully scraped {len(companies)} companies using YC API!")
        else:
            print("❌ No companies found")

if __name__ == "__main__":
    scraper = YCApiScraper()
    scraper.scrape_all()

