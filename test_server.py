#!/usr/bin/env python3
"""Test if the Flask server is working"""

import requests
import time
import sys

def test_server():
    base_url = "http://localhost:5001"  # Changed from 5000
    
    print("Testing Flask server...")
    print("="*60)
    
    # Test stats endpoint
    try:
        print("\n1. Testing /api/stats...")
        response = requests.get(f"{base_url}/api/stats", timeout=5)
        if response.status_code == 200:
            stats = response.json()
            print(f"   ✅ Success! Found {stats['total_companies']} companies")
        else:
            print(f"   ❌ Failed with status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("   ❌ Connection failed - Is the server running?")
        print("   Run: python3 start_server.py")
        return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    
    # Test companies endpoint
    try:
        print("\n2. Testing /api/companies...")
        response = requests.get(f"{base_url}/api/companies?limit=5", timeout=5)
        if response.status_code == 200:
            companies = response.json()
            print(f"   ✅ Success! Retrieved {len(companies)} companies")
        else:
            print(f"   ❌ Failed with status {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    
    # Test main page
    try:
        print("\n3. Testing / (main page)...")
        response = requests.get(base_url, timeout=5)
        if response.status_code == 200:
            print(f"   ✅ Success! Page loaded ({len(response.text)} bytes)")
        else:
            print(f"   ❌ Failed with status {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    
    print("\n" + "="*60)
    print("✅ All tests passed! Server is working correctly.")
    print(f"\nOpen your browser and go to: {base_url}")
    return True

if __name__ == "__main__":
    if not test_server():
        sys.exit(1)

