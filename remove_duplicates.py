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
    
    # Find duplicates
    cursor.execute('''
        SELECT name, COUNT(*) as count 
        FROM companies 
        GROUP BY name 
        HAVING count > 1
        ORDER BY count DESC
    ''')
    duplicates = cursor.fetchall()
    
    if not duplicates:
        print("No duplicates found!")
        conn.close()
        return
    
    print(f"Found {len(duplicates)} companies with duplicates")
    print(f"Total duplicate entries: {sum(count - 1 for _, count in duplicates)}\n")
    
    removed_count = 0
    
    for company_name, count in duplicates:
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

