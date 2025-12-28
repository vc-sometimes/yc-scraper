# Troubleshooting Guide

## Server Not Showing Anything

### Step 1: Check if Server is Running

```bash
# Check if port 5000 is in use
lsof -i :5000

# Or check processes
ps aux | grep "python.*app.py"
```

### Step 2: Start the Server

```bash
cd "/Users/vc/yc scraper"
python3 start_server.py
```

You should see:
```
🚀 Starting YC Companies Web Dashboard
📊 Dashboard: http://localhost:5000
```

### Step 3: Test the Server

Open a new terminal and run:
```bash
cd "/Users/vc/yc scraper"
python3 test_server.py
```

### Step 4: Check Browser Console

1. Open http://localhost:5000 in your browser
2. Press F12 (or Cmd+Option+I on Mac) to open Developer Tools
3. Go to the "Console" tab
4. Look for any JavaScript errors (red text)

### Step 5: Check Network Tab

1. In Developer Tools, go to "Network" tab
2. Refresh the page
3. Check if `/api/stats` and other API calls are successful (status 200)

### Common Issues

#### Issue: "Connection refused"
- **Solution**: Make sure the server is running (`python3 start_server.py`)

#### Issue: "Template not found"
- **Solution**: Make sure you're running from the project directory

#### Issue: Blank page / No data
- **Solution**: 
  1. Check browser console for JavaScript errors
  2. Verify database exists: `ls -la yc_companies.db`
  3. Check if data exists: `python3 -c "import sqlite3; conn = sqlite3.connect('yc_companies.db'); print(conn.execute('SELECT COUNT(*) FROM companies').fetchone()[0])"`

#### Issue: Charts not showing
- **Solution**: Check if Chart.js is loading (Network tab in DevTools)

### Manual Test

Test the API directly:
```bash
curl http://localhost:5000/api/stats
```

Should return JSON with statistics.

### Reset Everything

```bash
# Kill any running servers
lsof -ti:5000 | xargs kill -9

# Start fresh
python3 start_server.py
```

