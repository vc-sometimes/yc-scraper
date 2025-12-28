# YC Companies Web Dashboard

A beautiful web interface to visualize and explore YC companies and their team members.

## Features

- 📊 **Dashboard** - Overview with statistics and charts
- 🏢 **Companies** - Browse all 248+ YC companies with search
- 👥 **Team Members** - View founders and team members
- 📈 **Charts** - Visualizations of company data
- 🔍 **Search** - Search companies and members

## Running the Web App

### Start the Server

```bash
python3 app.py
```

The server will start on `http://localhost:5001`
(Note: Port 5000 is used by macOS AirPlay, so we use 5001 instead)

Open your browser and navigate to:
- **Dashboard**: http://localhost:5001
- **Companies**: http://localhost:5001/companies
- **Team Members**: http://localhost:5001/members

### Access from Other Devices

The server runs on `0.0.0.0:5000`, so you can access it from other devices on your network:
- Find your local IP address: `ifconfig` (Mac/Linux) or `ipconfig` (Windows)
- Access via: `http://YOUR_IP:5000`

## API Endpoints

The app also provides a REST API:

- `GET /api/companies` - Get all companies (supports `?search=term&limit=10`)
- `GET /api/companies/<id>` - Get single company with members
- `GET /api/members` - Get all team members (supports `?search=term&company=name`)
- `GET /api/stats` - Get statistics

## Features

### Dashboard
- Total companies count
- Total team members
- Companies with members
- Top companies by team size (bar chart)
- Companies by batch (doughnut chart)
- Recent companies preview

### Companies Page
- Grid view of all companies
- Search functionality
- Company details (batch, location, industry)
- Direct links to YC profiles

### Team Members Page
- Grid view of all team members
- Search functionality
- Member details (role, company, links)
- Links to YC profiles, LinkedIn, Twitter

## Technology Stack

- **Backend**: Flask (Python)
- **Frontend**: HTML5, CSS3, JavaScript
- **Charts**: Chart.js
- **Database**: SQLite

## Notes

- Make sure you've run the scrapers first to populate the database
- The web app reads directly from `yc_companies.db`
- Charts require data - if you haven't scraped members yet, some charts may be empty

