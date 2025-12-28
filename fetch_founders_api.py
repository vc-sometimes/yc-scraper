#!/usr/bin/env python3
"""
Fetch founders from YC company pages using their JSON data
Much faster than Selenium scraping
"""

import requests
import sqlite3
import json
import re
import time
from typing import List, Dict, Optional

class FounderApiFetcher:
    def __init__(self, db_path='yc_companies.db'):
        self.db_path = db_path
        
    def get_company_page_json(self, company_slug: str) -> Optional[Dict]:
        """Get JSON data from a company page"""
        url = f"https://www.ycombinator.com/companies/{company_slug}"
        
        try:
            response = requests.get(url, headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            })
            response.raise_for_status()
            
            # Extract __NEXT_DATA__ JSON
            match = re.search(r'window\.__NEXT_DATA__\s*=\s*({.+?});', response.text, re.DOTALL)
            if match:
                return json.loads(match.group(1))
        except Exception as e:
            print(f"    Error fetching {company_slug}: {e}")
        
        return None
    
    def extract_founders_from_json(self, json_data: Dict) -> List[Dict]:
        """Extract founders from Next.js JSON data"""
        founders = []
        
        def search_for_founders(obj, depth=0):
            if depth > 15:
                return
            
            if isinstance(obj, dict):
                # Look for founder objects
                if 'name' in obj and ('founder' in str(obj).lower() or 'role' in obj):
                    name = obj.get('name', '').strip()
                    if name and len(name.split()) >= 2:
                        founder = {
                            'name': name,
                            'role': obj.get('role') or obj.get('title') or '',
                            'previous_company': obj.get('previousCompany') or obj.get('previous_company') or '',
                            'linkedin_url': obj.get('linkedin') or obj.get('linkedinUrl') or obj.get('linkedin_url') or '',
                            'twitter_url': obj.get('twitter') or obj.get('twitterUrl') or obj.get('twitter_url') or obj.get('x') or '',
                            'yc_profile_url': obj.get('ycUrl') or obj.get('yc_url') or obj.get('profileUrl') or '',
                            'bio': obj.get('bio') or obj.get('description') or ''
                        }
                        if not any(f['name'].lower() == founder['name'].lower() for f in founders):
                            founders.append(founder)
                
                # Look for founders array
                if 'founders' in obj and isinstance(obj['founders'], list):
                    for founder_obj in obj['founders']:
                        if isinstance(founder_obj, dict) and founder_obj.get('name'):
                            founder = {
                                'name': founder_obj.get('name', '').strip(),
                                'role': founder_obj.get('role') or founder_obj.get('title') or 'Founder',
                                'previous_company': founder_obj.get('previousCompany') or founder_obj.get('previous_company') or '',
                                'linkedin_url': founder_obj.get('linkedin') or founder_obj.get('linkedinUrl') or founder_obj.get('linkedin_url') or '',
                                'twitter_url': founder_obj.get('twitter') or founder_obj.get('twitterUrl') or founder_obj.get('twitter_url') or founder_obj.get('x') or '',
                                'yc_profile_url': founder_obj.get('ycUrl') or founder_obj.get('yc_url') or founder_obj.get('profileUrl') or '',
                                'bio': founder_obj.get('bio') or founder_obj.get('description') or ''
                            }
                            if founder['name'] and not any(f['name'].lower() == founder['name'].lower() for f in founders):
                                founders.append(founder)
                
                # Recursively search
                for value in obj.values():
                    search_for_founders(value, depth + 1)
            
            elif isinstance(obj, list):
                for item in obj:
                    search_for_founders(item, depth + 1)
        
        search_for_founders(json_data)
        return founders
    
    def fetch_founders_for_company(self, company_id: int, company_name: str, yc_url: str) -> int:
        """Fetch founders for a single company"""
        if not yc_url:
            return 0
        
        # Extract slug from URL
        slug_match = re.search(r'/companies/([^/?]+)', yc_url)
        if not slug_match:
            return 0
        
        slug = slug_match.group(1)
        
        # Get JSON data
        json_data = self.get_company_page_json(slug)
        if not json_data:
            return 0
        
        # Extract founders
        founders = self.extract_founders_from_json(json_data)
        
        if not founders:
            return 0
        
        # Save founders
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        saved = 0
        for founder in founders:
            try:
                cursor.execute('''
                    INSERT OR REPLACE INTO founders 
                    (company_id, company_name, name, role, previous_company, 
                     linkedin_url, twitter_url, yc_profile_url, bio)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    company_id,
                    company_name,
                    founder['name'],
                    founder['role'],
                    founder['previous_company'],
                    founder['linkedin_url'],
                    founder['twitter_url'],
                    founder['yc_profile_url'],
                    founder['bio']
                ))
                saved += 1
            except Exception as e:
                print(f"    Error saving founder {founder['name']}: {e}")
        
        conn.commit()
        conn.close()
        
        return saved
    
    def fetch_all_founders(self, limit: Optional[int] = None, delay: float = 0.5):
        """Fetch founders for all companies"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get companies without founders
        query = '''
            SELECT DISTINCT c.id, c.name, c.yc_url 
            FROM companies c
            LEFT JOIN founders f ON c.id = f.company_id
            WHERE c.yc_url LIKE "%/companies/%" 
            AND c.yc_url NOT LIKE "%?%"
            AND f.id IS NULL
            ORDER BY c.name
        '''
        if limit:
            query += f" LIMIT {limit}"
        
        cursor.execute(query)
        companies = cursor.fetchall()
        conn.close()
        
        print(f"Found {len(companies)} companies without founders\n")
        
        if not companies:
            print("All companies already have founders!")
            return
        
        total_founders = 0
        
        for i, (company_id, company_name, yc_url) in enumerate(companies, 1):
            clean_name = company_name.split('\n')[0] if company_name else 'Unknown'
            print(f"[{i}/{len(companies)}] Fetching founders for {clean_name}...")
            
            count = self.fetch_founders_for_company(company_id, clean_name, yc_url)
            
            if count > 0:
                total_founders += count
                print(f"  ✅ Found {count} founder(s)")
            else:
                print(f"  ⚠️  No founders found")
            
            if i < len(companies):
                time.sleep(delay)
        
        print(f"\n✅ Done! Fetched {total_founders} total founders")

if __name__ == "__main__":
    import sys
    
    limit = None
    if len(sys.argv) > 1:
        limit = int(sys.argv[1])
    
    fetcher = FounderApiFetcher()
    fetcher.fetch_all_founders(limit=limit, delay=0.5)

