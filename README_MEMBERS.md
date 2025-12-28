# YC Companies Team Members Scraper

This script scrapes team members and founders from individual YC company pages.

## Features

- Extracts team members/founders from each company's YC page
- Multiple extraction methods:
  1. Links to `/people/` profiles (most reliable)
  2. JSON data parsing
  3. Text pattern matching (e.g., "We're John, Jane, and Bob, co-founders")
  4. Structured founder sections
- Stores data in `team_members` table
- Filters out false positives (navigation elements, etc.)

## Usage

### Scrape Members from All Companies

```bash
python3 scrape_members.py
```

**Note:** This will take a while (248 companies × 2 seconds delay ≈ 8+ minutes)

### Scrape Members from First N Companies (for testing)

```bash
python3 scrape_members.py 10  # Scrape first 10 companies
```

### View Scraped Members

View all members:
```bash
python3 view_members.py
```

View members for a specific company:
```bash
python3 view_members.py "Absurd"
```

View statistics:
```bash
python3 view_members.py stats
```

## Database Schema

The `team_members` table includes:
- `id`: Primary key
- `company_id`: Foreign key to companies table
- `company_name`: Company name
- `name`: Team member/founder name
- `role`: Role (e.g., "Founder", "Co-Founder")
- `email`: Email address (if available)
- `linkedin_url`: LinkedIn profile URL
- `twitter_url`: Twitter profile URL
- `bio`: Bio/description
- `yc_profile_url`: YC people directory URL
- `created_at`: Timestamp

## Notes

- The scraper includes a 2-second delay between requests to avoid rate limiting
- Some companies may not have publicly listed founders/team members
- The scraper uses multiple methods to maximize data extraction
- False positives are filtered out (navigation elements, etc.)

## Example Output

```
[1/5] Scraping Absurd...
  ✓ Found 2 member(s): Aaron Epstein, Daniel Smith
[2/5] Scraping Adam...
  ✓ Found 1 member(s): Brad Flora
```

