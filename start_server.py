#!/usr/bin/env python3
"""
Start the Flask web server
"""

import sys
import os

# Make sure we're in the right directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from app import app

if __name__ == '__main__':
    PORT = 5001  # Changed from 5000 because macOS AirPlay uses 5000
    
    print("="*60)
    print("🚀 Starting YC Companies Web Dashboard")
    print("="*60)
    print(f"\n📊 Dashboard: http://localhost:{PORT}")
    print(f"🏢 Companies: http://localhost:{PORT}/companies")
    print(f"👥 Members: http://localhost:{PORT}/members")
    print("\nPress Ctrl+C to stop the server\n")
    print("="*60 + "\n")
    
    try:
        app.run(debug=True, host='0.0.0.0', port=PORT, use_reloader=False)
    except KeyboardInterrupt:
        print("\n\nServer stopped. Goodbye!")
        sys.exit(0)

