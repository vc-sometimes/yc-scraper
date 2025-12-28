#!/usr/bin/env python3
"""
Summary view of YC Companies Database
"""

import sqlite3
import re

def clean_name(name):
    """Clean company name - remove location if concatenated"""
    if not name:
        return ''
    # Remove location patterns
    name = re.sub(r'[A-Z][a-z]+[A-Z][a-z]+,?\s+[A-Z]{2},?\s+[A-Z]{2,}', '', name)
    # Take first line only
    name = name.split('\n')[0].strip()
    return name

def get_summary(db_path='yc_companies.db'):
    """Get database summary"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Total companies
    cursor.execute('''
        SELECT COUNT(*) FROM companies 
        WHERE yc_url LIKE "%/companies/%" 
        AND yc_url NOT LIKE "%?%" 
        AND yc_url NOT LIKE "%industry=%" 
        AND yc_url NOT LIKE "%batch=%"
    ''')
    total_companies = cursor.fetchone()[0]
    
    # Companies with batch info
    cursor.execute('''
        SELECT COUNT(*) FROM companies 
        WHERE batch IS NOT NULL AND batch != ''
        AND yc_url LIKE "%/companies/%" 
        AND yc_url NOT LIKE "%?%"
    ''')
    with_batch = cursor.fetchone()[0]
    
    # Companies with location
    cursor.execute('''
        SELECT COUNT(*) FROM companies 
        WHERE location IS NOT NULL AND location != ''
        AND yc_url LIKE "%/companies/%" 
        AND yc_url NOT LIKE "%?%"
    ''')
    with_location = cursor.fetchone()[0]
    
    # Sample companies
    cursor.execute('''
        SELECT name, batch, location, yc_url 
        FROM companies 
        WHERE yc_url LIKE "%/companies/%" 
        AND yc_url NOT LIKE "%?%" 
        AND yc_url NOT LIKE "%industry=%" 
        AND yc_url NOT LIKE "%batch=%"
        ORDER BY name
        LIMIT 50
    ''')
    companies = cursor.fetchall()
    
    conn.close()
    
    return {
        'total': total_companies,
        'with_batch': with_batch,
        'with_location': with_location,
        'companies': companies
    }

def display_summary():
    """Display database summary"""
    summary = get_summary()
    
    print("="*80)
    print("YC COMPANIES DATABASE - SUMMARY")
    print("="*80)
    print(f"\nTotal Companies: {summary['total']}")
    print(f"Companies with Batch Info: {summary['with_batch']}")
    print(f"Companies with Location Info: {summary['with_location']}")
    print("\n" + "="*80)
    print("SAMPLE COMPANIES (50 shown)")
    print("="*80 + "\n")
    
    for i, (name, batch, location, yc_url) in enumerate(summary['companies'], 1):
        clean = clean_name(name)
        batch_str = batch if batch else 'N/A'
        location_str = location if location else 'N/A'
        
        print(f"{i:3}. {clean:<45} | Batch: {batch_str:<15} | {location_str}")
        if yc_url:
            print(f"     {yc_url}")
        print()

if __name__ == "__main__":
    display_summary()

