#!/usr/bin/env python3
"""
View YC Companies Database
Displays companies stored in the database
"""

import sqlite3
import sys
from tabulate import tabulate

def view_companies(db_path='yc_companies.db', limit=None):
    """Display companies from database"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get total count
        cursor.execute("SELECT COUNT(*) FROM companies")
        total = cursor.fetchone()[0]
        
        if total == 0:
            print("No companies found in database.")
            print("Run scraper.py first to scrape data.")
            return
        
        # Get companies
        query = "SELECT name, batch, location, industry, website, yc_url FROM companies ORDER BY name"
        if limit:
            query += f" LIMIT {limit}"
        
        cursor.execute(query)
        companies = cursor.fetchall()
        
        # Clean and format data for display
        companies_display = []
        for row in companies:
            name, batch, location, industry, website, yc_url = row
            # Clean name - take first line only if multiline
            if name:
                name = name.split('\n')[0].strip()
            # Convert None to empty string
            cleaned_row = [
                name or '',
                batch or '',
                location or '',
                industry or '',
                website or '',
                yc_url or ''
            ]
            companies_display.append(cleaned_row)
        
        # Display results
        print(f"\n{'='*80}")
        print(f"YC Companies Database - Total: {total} companies")
        print(f"{'='*80}\n")
        
        headers = ["Name", "Batch", "Location", "Industry", "Website", "YC URL"]
        try:
            print(tabulate(companies_display, headers=headers, tablefmt="grid", maxcolwidths=[30, 15, 20, 20, 30, 40]))
        except TypeError:
            # Fallback if maxcolwidths not supported
            print(tabulate(companies_display, headers=headers, tablefmt="grid"))
        
        conn.close()
        
    except sqlite3.OperationalError as e:
        print(f"Database error: {e}")
        print("Make sure the database exists. Run scraper.py first.")
    except Exception as e:
        print(f"Error: {e}")

def search_companies(db_path='yc_companies.db', search_term=None):
    """Search companies by name"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    if search_term:
        cursor.execute("""
            SELECT name, batch, location, industry, website, yc_url 
            FROM companies 
            WHERE name LIKE ? OR description LIKE ?
            ORDER BY name
        """, (f'%{search_term}%', f'%{search_term}%'))
    else:
        cursor.execute("SELECT name, batch, location, industry, website, yc_url FROM companies ORDER BY name")
    
    companies = cursor.fetchall()
    
    if companies:
        # Convert None values to empty strings for display
        companies_display = [[val if val is not None else '' for val in row] for row in companies]
        headers = ["Name", "Batch", "Location", "Industry", "Website", "YC URL"]
        try:
            print(tabulate(companies_display, headers=headers, tablefmt="grid", maxcolwidths=[30, 15, 20, 20, 30, 40]))
        except TypeError:
            # Fallback if maxcolwidths not supported
            print(tabulate(companies_display, headers=headers, tablefmt="grid"))
    else:
        print("No companies found matching your search.")
    
    conn.close()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "search" and len(sys.argv) > 2:
            search_companies(search_term=sys.argv[2])
        elif sys.argv[1].isdigit():
            view_companies(limit=int(sys.argv[1]))
        else:
            view_companies()
    else:
        view_companies()

