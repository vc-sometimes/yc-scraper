#!/usr/bin/env python3
"""
View team members from the database
"""

import sqlite3
import sys
from tabulate import tabulate

def view_members(db_path='yc_companies.db', company_name=None, limit=None):
    """Display team members from database"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        if company_name:
            query = '''
                SELECT company_name, name, role, email, linkedin_url, twitter_url, yc_profile_url
                FROM team_members
                WHERE company_name LIKE ?
                ORDER BY company_name, name
            '''
            params = (f'%{company_name}%',)
        else:
            query = '''
                SELECT company_name, name, role, email, linkedin_url, twitter_url, yc_profile_url
                FROM team_members
                ORDER BY company_name, name
            '''
            params = ()
        
        if limit:
            query += f" LIMIT {limit}"
        
        cursor.execute(query, params)
        members = cursor.fetchall()
        
        # Get total count
        cursor.execute("SELECT COUNT(*) FROM team_members")
        total = cursor.fetchone()[0]
        
        if members:
            print(f"\n{'='*80}")
            print(f"Team Members - Total: {total} members")
            if company_name:
                print(f"Filtered by: {company_name}")
            print(f"{'='*80}\n")
            
            # Convert None to empty strings
            members_display = [[val if val is not None else '' for val in row] for row in members]
            
            headers = ["Company", "Name", "Role", "Email", "LinkedIn", "Twitter", "YC Profile"]
            try:
                print(tabulate(members_display, headers=headers, tablefmt="grid", maxcolwidths=[25, 20, 15, 25, 30, 30, 40]))
            except TypeError:
                print(tabulate(members_display, headers=headers, tablefmt="grid"))
        else:
            print("No team members found in database.")
            print("Run scrape_members.py first to scrape member data.")
        
        conn.close()
        
    except sqlite3.OperationalError as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"Error: {e}")

def get_statistics(db_path='yc_companies.db'):
    """Get statistics about team members"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM team_members")
    total_members = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(DISTINCT company_name) FROM team_members")
    companies_with_members = cursor.fetchone()[0]
    
    cursor.execute("SELECT company_name, COUNT(*) as count FROM team_members GROUP BY company_name ORDER BY count DESC LIMIT 10")
    top_companies = cursor.fetchall()
    
    print("="*80)
    print("TEAM MEMBERS STATISTICS")
    print("="*80)
    print(f"\nTotal Members: {total_members}")
    print(f"Companies with Members: {companies_with_members}")
    
    if top_companies:
        print("\nTop 10 Companies by Team Size:")
        for company, count in top_companies:
            print(f"  {company}: {count} member(s)")
    
    conn.close()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "stats":
            get_statistics()
        elif sys.argv[1] == "search" and len(sys.argv) > 2:
            view_members(company_name=sys.argv[2])
        elif sys.argv[1].isdigit():
            view_members(limit=int(sys.argv[1]))
        else:
            view_members(company_name=sys.argv[1])
    else:
        view_members()

