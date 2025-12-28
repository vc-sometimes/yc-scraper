# Quick Start Guide

## The 403 Error Fix

If you're getting a **403 Forbidden** error, it's likely because:

1. **You're accessing port 5000 instead of 5001**
   - macOS AirPlay uses port 5000
   - Our server runs on port **5001**

## Start the Server

```bash
cd "/Users/vc/yc scraper"
python3 start_server.py
```

You should see:
```
🚀 Starting YC Companies Web Dashboard
📊 Dashboard: http://localhost:5001
```

## Access the Dashboard

**IMPORTANT: Use port 5001, not 5000!**

Open your browser and go to:
- ✅ **http://localhost:5001** (CORRECT)
- ❌ **http://localhost:5000** (WRONG - this is AirPlay)

## If You Still Get 403

1. **Check the URL** - Make sure it says `:5001` not `:5000`

2. **Check if server is running**:
   ```bash
   lsof -i :5001
   ```
   Should show a Python process

3. **Restart the server**:
   ```bash
   # Kill any existing server
   lsof -ti:5001 | xargs kill -9
   
   # Start fresh
   python3 start_server.py
   ```

4. **Check browser console** (F12):
   - Look for which URL is failing
   - Make sure all requests go to `:5001`

5. **Test the API directly**:
   ```bash
   curl http://localhost:5001/api/stats
   ```
   Should return JSON data

## Troubleshooting

### Server won't start
- Make sure Flask is installed: `pip install flask flask-cors`
- Check if port 5001 is free: `lsof -i :5001`

### Blank page
- Open browser console (F12) and check for errors
- Make sure you're using `http://localhost:5001` not `http://localhost:5000`

### Charts not showing
- Check browser console for JavaScript errors
- Make sure Chart.js CDN is loading (check Network tab)

