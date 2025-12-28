#!/bin/bash
# Quick monitoring script for the scraper

echo "📊 Scraper Status"
echo "=================="
echo ""

# Check if scraper is running
if ps aux | grep -v grep | grep -q "scrape_founders_final"; then
    echo "✅ Scraper is RUNNING"
else
    echo "❌ Scraper is NOT running"
fi

echo ""

# Check database progress
python3 << 'PYTHON'
import sqlite3
conn = sqlite3.connect('yc_companies.db')
cursor = conn.cursor()

cursor.execute('SELECT COUNT(*) FROM founders')
total_founders = cursor.fetchone()[0]

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

cursor.execute('''
    SELECT COUNT(*) 
    FROM companies c
    LEFT JOIN founders f ON c.id = f.company_id
    WHERE c.yc_url LIKE "%/companies/%" 
    AND c.yc_url NOT LIKE "%?%"
    AND c.yc_url NOT LIKE "%industry=%"
    AND c.yc_url NOT LIKE "%batch=%"
    AND f.id IS NULL
''')
companies_remaining = cursor.fetchone()[0]

total_companies = companies_with_founders + companies_remaining
progress = (companies_with_founders / total_companies * 100) if total_companies > 0 else 0

print(f"Total founders found: {total_founders}")
print(f"Companies with founders: {companies_with_founders}")
print(f"Companies remaining: {companies_remaining}")
print(f"Progress: {progress:.1f}%")
print("")

# Show recent activity
cursor.execute('''
    SELECT company_name, COUNT(*) as count
    FROM founders
    GROUP BY company_name
    ORDER BY MAX(created_at) DESC
    LIMIT 5
''')
print("Most recently processed:")
for company, count in cursor.fetchall():
    clean_name = company.split(chr(10))[0] if company else "Unknown"
    print(f"  • {clean_name}: {count} founder(s)")

conn.close()
PYTHON

echo ""
echo "📝 Recent log output (last 10 lines):"
echo "--------------------------------------"
tail -10 scraper_output.log 2>/dev/null || echo "No log file found"

echo ""
echo "💡 To watch live progress, run: tail -f scraper_output.log"

