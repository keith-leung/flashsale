#!/usr/bin/env python3
"""Test health endpoint."""

import asyncio
import sys
from urllib.request import urlopen

def test_health():
    """Test health endpoint responds with 200 OK."""
    try:
        response = urlopen("http://localhost:8000/health", timeout=2)
        body = response.read().decode('utf-8')
        status = response.status
        print(f"Status: {status}")
        print(f"Body: {body}")
        return status == 200 and body == "200 OK"
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    import subprocess
    import time
    
    # Start server in background
    proc = subprocess.Popen([sys.executable, "-m", "app.main"])
    time.sleep(2)  # Wait for startup
    
    try:
        if test_health():
            print("✓ Health endpoint working!")
            proc.terminate()
            sys.exit(0)
        else:
            print("✗ Health endpoint failed!")
            proc.terminate()
            sys.exit(1)
    finally:
        proc.kill()
