#!/usr/bin/env python3
"""
Real-time progress monitor for the founder scraper
"""

import sqlite3
import time
import os
import subprocess

def get_stats():
    """Get current database statistics"""
    conn = sqlite3.connect('yc_companies.db')
    cursor = conn.cursor()
    
    # Total founders
    cursor.execute('SELECT COUNT(*) FROM founders')
    total_founders = cursor.fetchone()[0]
    
    # Companies with founders
    cursor.execute('''
        SELECT COUNT(DISTINCT c.id) 
        FROM companies c
        INNER JOIN founders f ON c.id = f.company_id
        WHERE c.yc_url LIKE "%/companies/%" 
        AND c.yc_url NOT LIKE "%?%" 
        AND c.yc_url NOT LIKE "%industry=%"
        AND c.yc_url NOT LIKE "%batch=%"
    ''')
    companies_with_founders = cursor.fetchone()[0]
    
    # Total companies
    cursor.execute('''
        SELECT COUNT(*) 
        FROM companies
        WHERE yc_url LIKE "%/companies/%" 
        AND yc_url NOT LIKE "%?%" 
        AND yc_url NOT LIKE "%industry=%"
        AND yc_url NOT LIKE "%batch=%"
    ''')
    total_companies = cursor.fetchone()[0]
    
    # Companies without founders
    companies_without = total_companies - companies_with_founders
    
    # Recent founders (last 10)
    cursor.execute('''
        SELECT f.name, f.company_name, f.linkedin_url, f.twitter_url
        FROM founders f
        ORDER BY f.created_at DESC
        LIMIT 10
    ''')
    recent_founders = cursor.fetchall()
    
    conn.close()
    
    return {
        'total_founders': total_founders,
        'companies_with_founders': companies_with_founders,
        'total_companies': total_companies,
        'companies_without': companies_without,
        'recent_founders': recent_founders
    }

def get_scraper_log_tail(n=10):
    """Get last N lines from scraper log"""
    try:
        if os.path.exists('scraper_output.log'):
            with open('scraper_output.log', 'r') as f:
                lines = f.readlines()
                return lines[-n:] if len(lines) > n else lines
    except:
        pass
    return []

def is_scraper_running():
    """Check if scraper process is running"""
    try:
        result = subprocess.run(
            ['pgrep', '-f', 'scrape_founders_simple.py'],
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except:
        return False

def main():
    print("\033[2J\033[H")  # Clear screen
    print("=" * 80)
    print("YC FOUNDER SCRAPER - PROGRESS MONITOR")
    print("=" * 80)
    print()
    
    running = is_scraper_running()
    status = "🟢 RUNNING" if running else "🔴 STOPPED"
    print(f"Scraper Status: {status}")
    print()
    
    stats = get_stats()
    
    # Progress bar
    progress_pct = (stats['companies_with_founders'] / stats['total_companies'] * 100) if stats['total_companies'] > 0 else 0
    bar_width = 50
    filled = int(bar_width * progress_pct / 100)
    bar = "█" * filled + "░" * (bar_width - filled)
    
    print(f"Progress: {stats['companies_with_founders']}/{stats['total_companies']} companies ({progress_pct:.1f}%)")
    print(f"[{bar}]")
    print()
    
    print(f"📊 Statistics:")
    print(f"   • Total Founders Found: {stats['total_founders']}")
    print(f"   • Companies with Founders: {stats['companies_with_founders']}")
    print(f"   • Companies Remaining: {stats['companies_without']}")
    print()
    
    if stats['recent_founders']:
        print("🆕 Recent Founders Found:")
        for name, company, linkedin, twitter in stats['recent_founders'][:5]:
            company_clean = company.split('\n')[0] if company else 'Unknown'
            socials = []
            if linkedin:
                socials.append("LinkedIn")
            if twitter:
                socials.append("Twitter/X")
            social_str = f" ({', '.join(socials)})" if socials else ""
            print(f"   • {name} @ {company_clean}{social_str}")
        print()
    
    # Recent log activity
    log_lines = get_scraper_log_tail(5)
    if log_lines:
        print("📝 Recent Activity:")
        for line in log_lines[-5:]:
            line = line.strip()
            if line and not line.startswith('/Users'):
                # Clean up the line
                if '✅' in line or '⚠️' in line:
                    print(f"   {line}")
        print()
    
    print("=" * 80)
    print("Press Ctrl+C to exit | Updates every 3 seconds")
    print("=" * 80)

if __name__ == "__main__":
    try:
        while True:
            main()
            time.sleep(3)
    except KeyboardInterrupt:
        print("\n\nMonitoring stopped.")

