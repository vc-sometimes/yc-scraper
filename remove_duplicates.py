#!/usr/bin/env python3
"""
Remove duplicate companies from the database
Keeps the most complete entry (most non-null fields)
"""

import sqlite3

def remove_duplicates(db_path='yc_companies.db'):
    """Remove duplicate companies, keeping the best entry for each"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    removed_count = 0
    
    # First, remove duplicates by URL (more reliable than name)
    print("Checking for duplicates by URL...")
    cursor.execute('''
        SELECT yc_url, COUNT(*) as count 
        FROM companies 
        WHERE yc_url IS NOT NULL AND yc_url != ''
        GROUP BY yc_url 
        HAVING count > 1
        ORDER BY count DESC
    ''')
    url_duplicates = cursor.fetchall()
    
    if url_duplicates:
        print(f"Found {len(url_duplicates)} companies with duplicate URLs")
        print(f"Total duplicate entries by URL: {sum(count - 1 for _, count in url_duplicates)}\n")
        
        for yc_url, count in url_duplicates:
            # Get all entries for this URL
            cursor.execute('''
                SELECT id, name, batch, description, website, location, industry, 
                       is_hiring, yc_url, created_at
                FROM companies 
                WHERE yc_url = ?
                ORDER BY created_at DESC
            ''', (yc_url,))
            
            entries = cursor.fetchall()
            
            # Score each entry (more fields filled = better)
            scored_entries = []
            for entry in entries:
                entry_id = entry[0]
                # Count non-null fields
                score = sum(1 for field in entry[1:] if field is not None and field != '')
                # Prefer entries with batch
                if entry[2]:  # batch
                    score += 5
                # Prefer entries with description
                if entry[3]:  # description
                    score += 3
                scored_entries.append((score, entry_id, entry))
            
            # Sort by score (highest first), then by created_at (newest first)
            scored_entries.sort(key=lambda x: (-x[0], entries.index(x[2])))
            
            # Keep the best entry, remove the rest
            best_entry = scored_entries[0]
            entries_to_remove = [entry_id for _, entry_id, _ in scored_entries[1:]]
            
            if entries_to_remove:
                # Update founders to point to the kept entry
                best_id = best_entry[1]
                for dup_id in entries_to_remove:
                    cursor.execute('''
                        UPDATE founders 
                        SET company_id = ? 
                        WHERE company_id = ?
                    ''', (best_id, dup_id))
                
                # Remove duplicate companies
                placeholders = ','.join(['?'] * len(entries_to_remove))
                cursor.execute(f'''
                    DELETE FROM companies 
                    WHERE id IN ({placeholders})
                ''', entries_to_remove)
                
                removed_count += len(entries_to_remove)
                best_name = best_entry[2][1]  # name field
                print(f"  {best_name[:50]}: Kept entry {best_id}, removed {len(entries_to_remove)} duplicate(s) by URL")
        
        conn.commit()
        print()
    
    # Then, remove duplicates by name (for entries without URLs)
    print("Checking for duplicates by name...")
    cursor.execute('''
        SELECT name, COUNT(*) as count 
        FROM companies 
        GROUP BY name 
        HAVING count > 1
        ORDER BY count DESC
    ''')
    name_duplicates = cursor.fetchall()
    
    if not name_duplicates:
        print("No duplicates by name found!")
    else:
        print(f"Found {len(name_duplicates)} companies with duplicate names")
        print(f"Total duplicate entries by name: {sum(count - 1 for _, count in name_duplicates)}\n")
        
        for company_name, count in name_duplicates:
            # Get all entries for this company
            cursor.execute('''
                SELECT id, name, batch, description, website, location, industry, 
                       is_hiring, yc_url, created_at
                FROM companies 
                WHERE name = ?
                ORDER BY created_at DESC
            ''', (company_name,))
            
            entries = cursor.fetchall()
            
            # Score each entry (more fields filled = better)
            scored_entries = []
            for entry in entries:
                entry_id = entry[0]
                # Count non-null fields
                score = sum(1 for field in entry[1:] if field is not None and field != '')
                # Prefer entries with yc_url
                if entry[8]:  # yc_url
                    score += 10
                # Prefer entries with batch
                if entry[2]:  # batch
                    score += 5
                scored_entries.append((score, entry_id, entry))
            
            # Sort by score (highest first), then by created_at (newest first)
            scored_entries.sort(key=lambda x: (-x[0], entries.index(x[2])))
            
            # Keep the best entry, remove the rest
            best_entry = scored_entries[0]
            entries_to_remove = [entry_id for _, entry_id, _ in scored_entries[1:]]
            
            if entries_to_remove:
                # Update founders to point to the kept entry
                best_id = best_entry[1]
                for dup_id in entries_to_remove:
                    cursor.execute('''
                        UPDATE founders 
                        SET company_id = ? 
                        WHERE company_id = ?
                    ''', (best_id, dup_id))
                
                # Remove duplicate companies
                placeholders = ','.join(['?'] * len(entries_to_remove))
                cursor.execute(f'''
                    DELETE FROM companies 
                    WHERE id IN ({placeholders})
                ''', entries_to_remove)
                
                removed_count += len(entries_to_remove)
                print(f"  {company_name[:50]}: Kept entry {best_id}, removed {len(entries_to_remove)} duplicate(s)")
    
    conn.commit()
    
    # Verify
    cursor.execute('SELECT COUNT(*) FROM companies')
    remaining = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(DISTINCT name) FROM companies')
    unique = cursor.fetchone()[0]
    
    print(f"\n✅ Removed {removed_count} duplicate entries")
    print(f"   Remaining companies: {remaining}")
    print(f"   Unique company names: {unique}")
    
    conn.close()

if __name__ == "__main__":
    remove_duplicates()

