#!/usr/bin/env python3
import asyncio
import os
import sys
from datetime import datetime, timedelta
from uuid import uuid4
from sqlalchemy import text
from app.core.database import AsyncSessionLocal, engine

async def clean_flash_sale_data():
    async with AsyncSessionLocal() as session:
        await session.execute(text("DELETE FROM flash_sale_campaigns WHERE name LIKE 'Campaign-%'"))
        await session.execute(text("DELETE FROM inventory WHERE sku_id IN (SELECT id FROM skus WHERE sku_code LIKE 'FS-%')"))
        await session.execute(text("DELETE FROM skus WHERE sku_code LIKE 'FS-%'"))
        await session.execute(text("DELETE FROM spus WHERE slug LIKE 'flash-sale-test-%'"))
        await session.commit()
        print("✓ Cleaned existing flash sale test data")

async def create_flash_sale_campaigns(num_campaigns: int, inventory_per_campaign: int):
    print(f"\nGenerating {num_campaigns:,} flash sale campaigns...")
    batch_size = 100
    start_time = datetime.utcnow()
    end_time = start_time + timedelta(hours=24)

    async with AsyncSessionLocal() as session:
        for batch_start in range(0, num_campaigns, batch_size):
            batch_end = min(batch_start + batch_size, num_campaigns)
            spu_values = []
            sku_values = []
            inventory_values = []
            campaign_values = []

            for i in range(batch_start, batch_end):
                spu_id = str(uuid4())
                spu_slug = f"flash-sale-test-{i:08d}"
                spu_name = f"Flash Sale Product {i:08d}"
                spu_values.append(f"('{spu_id}', '{spu_name}', '{spu_slug}', 'Test product', 1, NOW(), NOW())")

                sku_id = str(uuid4())
                sku_code = f"FS-{i:08d}"
                sku_values.append(f"('{sku_id}', '{sku_code}', 'Default', '{spu_id}', 99.99, 50.00, 1.0, 1, 1, NOW(), NOW())")

                inv_id = str(uuid4())
                inventory_values.append(f"('{inv_id}', '{sku_id}', {inventory_per_campaign}, 0, 0, NOW(), NOW())")

                campaign_id = str(uuid4())
                campaign_name = f"Campaign-{i:08d}"
                campaign_values.append(
                    f"('{campaign_id}', '{campaign_name}', 'Test description', '{spu_id}', {inventory_per_campaign}, 0, 10, 79.99, "
                    f"'{start_time.strftime('%Y-%m-%d %H:%M:%S')}', '{end_time.strftime('%Y-%m-%d %H:%M:%S')}', "
                    f"'active', 1, 60.0, 40.0, 25.0, 20, 13, 1, NULL, NULL, NOW(), NOW())"
                )

            await session.execute(text(f"INSERT INTO spus (id, name, slug, description, is_active, created_at, updated_at) VALUES {','.join(spu_values)}"))
            await session.execute(text(f"INSERT INTO skus (id, sku_code, name, spu_id, price, cost_price, weight, track_inventory, is_active, created_at, updated_at) VALUES {','.join(sku_values)}"))
            await session.execute(text(f"INSERT INTO inventory (id, sku_id, quantity, reserved_quantity, allow_negative_stock, created_at, updated_at) VALUES {','.join(inventory_values)}"))
            await session.execute(text(f"INSERT INTO flash_sale_campaigns (id, name, description, spu_id, total_sale_limit, sold_quantity, max_quantity_per_customer, flash_price, start_time, end_time, status, is_active, preallocate_percentage, redis_percentage, refill_lower_watermark_pct, csharp_allocation_ratio, java_allocation_ratio, python_allocation_ratio, preallocated_at, writeback_at, created_at, updated_at) VALUES {','.join(campaign_values)}"))
            await session.commit()
            print(f"  Progress: {batch_end:,} / {num_campaigns:,}")

async def main():
    num_campaigns = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    inventory_per_campaign = int(sys.argv[2]) if len(sys.argv) > 2 else 1000
    await clean_flash_sale_data()
    await create_flash_sale_campaigns(num_campaigns, inventory_per_campaign)
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
