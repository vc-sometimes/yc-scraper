# YC Clients

A web dashboard for viewing Y Combinator companies and their founders.

## Features

- View all YC companies in a searchable table
- See batch information for each company
- Browse founders with their roles and social links
- Filter and sort companies

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the API scraper to populate the database (recommended - much faster!):
```bash
python3 scraper_api.py
```

Or use the old Selenium-based scrapers:
```bash
python3 scrape_batch.py
python3 scrape_founders_final.py
```

3. Start the web server:
```bash
python3 start_server.py
```

4. Open http://localhost:5001 in your browser

## API Scraper

The `scraper_api.py` uses YC's public Algolia search API, which is:
- **Much faster** - No browser automation needed
- **More reliable** - No session crashes or timeouts
- **More efficient** - Direct API calls instead of page scraping
- **Gets all data** - Companies, founders, locations, etc. in one call

## Database Schema

The database contains:
- `companies` table: Company information including name, batch, description, website, location, industry
- `founders` table: Founder information including name, role, LinkedIn, Twitter, and YC profile links

## Deployment

This project is configured for Vercel deployment.
