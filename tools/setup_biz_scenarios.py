import mysql.connector
import os
import uuid
from datetime import datetime, timedelta

# Configuration
DB_HOST = "127.0.0.1"
DB_PORT = 3307
DB_USER = "user"
DB_PASS = "password"
DB_NAME = "flashsale"

def get_connection():
    return mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME
    )

def setup_scenarios():
    conn = get_connection()
    cursor = conn.cursor()

    print("Setting up 'Small Biz' and 'Big Biz' scenarios...")

    # ==========================================
    # 1. Scenario A: Small Business (ID 100)
    # ==========================================
    # 5,000 Items, 100% Pre-allocated, No Refill Thrashing
    campaign_id_small = 100
    spu_id_small = str(uuid.uuid4())
    sku_id_small = str(uuid.uuid4())
    
    # Clean up existing
    cursor.execute(f"DELETE FROM flash_sale_campaigns WHERE id={campaign_id_small}")
    cursor.execute(f"DELETE FROM skus WHERE sku_code='SMALL_BIZ_SKU'")
    cursor.execute(f"DELETE FROM spus WHERE name='Small Biz Product'")

    # Insert SPU
    cursor.execute("""
        INSERT INTO spus (id, name, description, created_at, updated_at)
        VALUES (%s, %s, %s, NOW(), NOW())
    """, (spu_id_small, "Small Biz Product", "Low inventory high contention"))

    # Insert SKU (5000 items)
    cursor.execute("""
        INSERT INTO skus (id, spu_id, sku_code, price, inventory_id, created_at, updated_at)
        VALUES (%s, %s, %s, 10.00, NULL, NOW(), NOW())
    """, (sku_id_small, spu_id_small, "SMALL_BIZ_SKU"))

    # Insert Campaign (100% Pre-allocation)
    cursor.execute("""
        INSERT INTO flash_sale_campaigns (
            id, name, spu_id, total_sale_limit, sold_quantity, 
            flash_price, start_time, end_time, status, is_active,
            preallocate_percentage, redis_percentage, refill_lower_watermark_pct,
            csharp_allocation_ratio, java_allocation_ratio, python_allocation_ratio,
            created_at, updated_at
        ) VALUES (
            %s, %s, %s, %s, 0,
            5.00, NOW(), DATE_ADD(NOW(), INTERVAL 7 DAY), 'active', 1,
            100.00, 0.00, 0.00,
            0, 100, 0,
            NOW(), NOW()
        )
    """, (campaign_id_small, "Small Biz Sale", spu_id_small, 5000))

    # ==========================================
    # 2. Scenario B: Big Business (ID 101)
    # ==========================================
    # 1,000,000 Items, 50k RPS target, Refill Logic Test
    campaign_id_big = 101
    spu_id_big = str(uuid.uuid4())
    sku_id_big = str(uuid.uuid4())

    # Clean up existing
    cursor.execute(f"DELETE FROM flash_sale_campaigns WHERE id={campaign_id_big}")
    cursor.execute(f"DELETE FROM skus WHERE sku_code='BIG_BIZ_SKU'")
    cursor.execute(f"DELETE FROM spus WHERE name='Big Biz Product'")

    # Insert SPU
    cursor.execute("""
        INSERT INTO spus (id, name, description, created_at, updated_at)
        VALUES (%s, %s, %s, NOW(), NOW())
    """, (spu_id_big, "Big Biz Product", "Massive inventory sustained load"))

    # Insert SKU (1M items)
    cursor.execute("""
        INSERT INTO skus (id, spu_id, sku_code, price, inventory_id, created_at, updated_at)
        VALUES (%s, %s, %s, 100.00, NULL, NOW(), NOW())
    """, (sku_id_big, spu_id_big, "BIG_BIZ_SKU"))

    # Insert Campaign (Active Refill: 10% pre-alloc to force early refills)
    # We set preallocate=10% so it starts with 100k items.
    # It will hit the refill logic quickly under load.
    cursor.execute("""
        INSERT INTO flash_sale_campaigns (
            id, name, spu_id, total_sale_limit, sold_quantity, 
            flash_price, start_time, end_time, status, is_active,
            preallocate_percentage, redis_percentage, refill_lower_watermark_pct,
            csharp_allocation_ratio, java_allocation_ratio, python_allocation_ratio,
            created_at, updated_at
        ) VALUES (
            %s, %s, %s, %s, 0,
            50.00, NOW(), DATE_ADD(NOW(), INTERVAL 7 DAY), 'active', 1,
            10.00, 90.00, 20.00,
            0, 100, 0,
            NOW(), NOW()
        )
    """, (campaign_id_big, "Big Biz Sale", spu_id_big, 1000000))

    conn.commit()
    print("✓ Successfully inserted Scenario A (Small Biz, ID 100) and Scenario B (Big Biz, ID 101)")
    print(f"  Small Biz SKU ID: {sku_id_small}")
    print(f"  Big Biz SKU ID: {sku_id_big}")
    
    # Save IDs to a temp file for shell script to read
    with open("/tmp/biz_scenario_ids.env", "w") as f:
        f.write(f"SMALL_SKU={sku_id_small}\n")
        f.write(f"BIG_SKU={sku_id_big}\n")

    cursor.close()
    conn.close()

if __name__ == "__main__":
    setup_scenarios()
