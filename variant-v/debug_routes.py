#!/usr/bin/env python3
"""Debug script to list all registered routes."""

import sys
sys.path.insert(0, '/home/syracuse/flashsale/variant-v/python-service')

from app.main import app

print("=== Registered Routes ===")
for route in app.routes:
    print(f"Path: {route.path}, Name: {route.name}, Methods: {getattr(route, 'methods', 'N/A')}")
    
print("\n=== Route Info ===")
print(f"Total routes: {len(app.routes)}")
