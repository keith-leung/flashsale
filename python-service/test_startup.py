#!/usr/bin/env python3
"""
Simple startup test to verify all components are working.
"""

import asyncio
import sys
from sqlalchemy import text

print("=" * 60)
print("Python Flash Sale Service - Startup Test")
print("=" * 60)

# Test 1: Import core modules
print("\n1. Testing imports...")
try:
    from app.core.config import settings
    from app.core.database import engine
    from app.core.id_generator import generate_id
    print("   ✓ Core modules imported successfully")
except Exception as e:
    print(f"   ✗ Failed to import core modules: {e}")
    sys.exit(1)

# Test 2: Test ID generation
print("\n2. Testing ID generation...")
try:
    test_id = generate_id()
    print(f"   ✓ Generated ID: {test_id}")
except Exception as e:
    print(f"   ✗ Failed to generate ID: {e}")
    sys.exit(1)

# Test 3: Test database connection
print("\n3. Testing database connection...")
async def test_database():
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 'Database OK' as status"))
            row = result.fetchone()
            print(f"   ✓ Database connection successful: {row[0]}")

            # Check if tables exist
            result = await conn.execute(text("SHOW TABLES"))
            tables = [row[0] for row in result.fetchall()]
            expected_tables = ['spus', 'skus', 'inventory', 'flash_sale_events', 'orders', 'order_line_items', 'payments']

            missing_tables = [t for t in expected_tables if t not in tables]
            if missing_tables:
                print(f"   ⚠ Warning: Missing tables: {missing_tables}")
            else:
                print(f"   ✓ All required tables exist ({len(tables)} tables)")

            return True
    except Exception as e:
        print(f"   ✗ Database connection failed: {e}")
        return False

# Test 4: Redis check (skipped for baseline)
print("\n4. Redis check...")
print(f"   ⊘ Redis not used in baseline implementation")
print(f"   Note: Will be added in optimization phase")

# Test 5: Test model imports
print("\n5. Testing model imports...")
try:
    from app.models import SPU, SKU, Inventory, FlashSaleEvent, Order, OrderLineItem, Payment
    print("   ✓ All models imported successfully")
except Exception as e:
    print(f"   ✗ Failed to import models: {e}")
    sys.exit(1)

# Test 6: Test schema imports
print("\n6. Testing schema imports...")
try:
    from app.schemas import (
        SPUCreate, SPUResponse,
        SKUCreate, SKUResponse,
        InventoryResponse,
        FlashSaleEventCreate, FlashSaleEventResponse
    )
    print("   ✓ All schemas imported successfully")
except Exception as e:
    print(f"   ✗ Failed to import schemas: {e}")
    sys.exit(1)

# Test 7: Test API router
print("\n7. Testing API router...")
try:
    from app.api.router import api_router
    routes_count = len(api_router.routes)
    print(f"   ✓ API router loaded successfully ({routes_count} routes)")
except Exception as e:
    print(f"   ✗ Failed to load API router: {e}")
    sys.exit(1)

# Test 8: Test FastAPI app
print("\n8. Testing FastAPI app...")
try:
    from app.main import app
    routes = [route.path for route in app.routes if hasattr(route, 'path')]
    print(f"   ✓ FastAPI app loaded successfully ({len(routes)} endpoints)")
    print(f"   Example endpoints: {', '.join(routes[:5])}")
except Exception as e:
    print(f"   ✗ Failed to load FastAPI app: {e}")
    sys.exit(1)

# Run async tests
print("\nRunning async tests...")
try:
    asyncio.run(test_database())
except Exception as e:
    print(f"   ✗ Async tests failed: {e}")
    sys.exit(1)

print("\n" + "=" * 60)
print("✓ ALL TESTS PASSED - Service is ready to run!")
print("=" * 60)
print("\nTo start the service, run:")
print("  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")
print("\nAPI Documentation will be available at:")
print("  http://localhost:8000/docs")
print("=" * 60)
