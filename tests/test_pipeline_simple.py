"""Simple backend pipeline test using the web server API directly."""

import requests
import time
import json
from pathlib import Path

def test_health():
    """Test health endpoint."""
    r = requests.get("http://localhost:5000/api/health")
    print(f"Health: {r.status_code}")
    print(json.dumps(r.json(), indent=2))

def test_library():
    """Test library endpoints."""
    r = requests.get("http://localhost:5000/api/library")
    print(f"\nLibrary: {r.status_code}")
    data = r.json()
    print(f"Novels: {len(data)}")
    for novel in data:
        print(f"  - {novel['title']} ({novel['chapter_count']} chapters)")
    return data

def main():
    print("=" * 60)
    print("SIMPLE PIPELINE TEST")
    print("=" * 60)
    
    try:
        test_health()
        novels = test_library()
        print(f"\n✓ Backend is running with {len(novels)} novels")
    except requests.exceptions.ConnectionError:
        print("\n✗ Could not connect to backend.")
        print("  Make sure the server is running: python -m src.web.web_server")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
