#!/usr/bin/env python3
"""
Setup 100K flash sale campaigns for stress testing.

Usage:
    python setup_flash_sale_campaigns.py [num_campaigns] [inventory_per_campaign]

Example:
    python setup_flash_sale_campaigns.py 100000 10000
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta
from uuid import uuid4

# Override database URL to use IP if hostname doesn't resolve
# This is for running in containers without proper DNS
os.environ.setdefault('DATABASE_URL', 'mysql+aiomysql://root:root@10.88.0.2:3306/orange315')

from sqlalchemy import text
from app.core.database import AsyncSessionLocal, engine


async def clean_flash_sale_data():
    """Clean existing flash sale test data."""
    async with AsyncSessionLocal() as session:
        # Delete flash sales for test SPUs
        await session.execute(text("DELETE FROM flash_sales WHERE campaign_name LIKE 'Campaign-%'"))
        # Delete test SPUs and SKUs (cascades to inventory)
        await session.execute(text("DELETE FROM inventory WHERE sku_id IN (SELECT id FROM skus WHERE sku_code LIKE 'FS-%')"))
        await session.execute(text("DELETE FROM skus WHERE sku_code LIKE 'FS-%'"))
        await session.execute(text("DELETE FROM spus WHERE slug LIKE 'flash-sale-test-%'"))
        await session.commit()
        print("✓ Cleaned existing flash sale test data")


async def create_flash_sale_campaigns(num_campaigns: int, inventory_per_campaign: int):
    """Create flash sale campaigns with SPUs and SKUs."""

    print(f"\nGenerating {num_campaigns:,} flash sale campaigns...")
    print(f"  Inventory per campaign: {inventory_per_campaign:,}")
    print(f"  Total inventory: {num_campaigns * inventory_per_campaign:,}\n")

    batch_size = 1000
    start_time = datetime.utcnow()
    end_time = start_time + timedelta(hours=24)  # 24-hour flash sale

    async with AsyncSessionLocal() as session:
        for batch_start in range(0, num_campaigns, batch_size):
            batch_end = min(batch_start + batch_size, num_campaigns)

            spu_values = []
            sku_values = []
            inventory_values = []
            campaign_values = []

            for i in range(batch_start, batch_end):
                # Generate SPU
                spu_id = str(uuid4())
                spu_slug = f"flash-sale-test-{i:08d}"
                spu_name = f"Flash Sale Product {i:08d}"

                spu_values.append(
                    f"('{spu_id}', '{spu_name}', '{spu_slug}', 'Flash sale test product', 1, "
                    f"'{start_time.strftime('%Y-%m-%d %H:%M:%S')}', '{start_time.strftime('%Y-%m-%d %H:%M:%S')}')"
                )

                # Generate SKU for this SPU
                sku_id = str(uuid4())
                sku_code = f"FS-{i:08d}"
                price = 99.99
                cost_price = 50.00

                sku_values.append(
                    f"('{sku_id}', '{sku_code}', 'Default', '{spu_id}', {price}, {cost_price}, 1.0, 1, 1, "
                    f"'{start_time.strftime('%Y-%m-%d %H:%M:%S')}', '{start_time.strftime('%Y-%m-%d %H:%M:%S')}')"
                )

                # Generate inventory for this SKU
                inv_id = str(uuid4())
                inventory_values.append(
                    f"('{inv_id}', '{sku_id}', {inventory_per_campaign}, 0, 0, "
                    f"'{start_time.strftime('%Y-%m-%d %H:%M:%S')}', '{start_time.strftime('%Y-%m-%d %H:%M:%S')}')"
                )

                # Generate flash sale campaign
                campaign_id = str(uuid4())
                campaign_name = f"Campaign-{i:08d}"
                flash_price = 79.99  # Discounted price
                max_per_order = 10

                campaign_values.append(
                    f"('{campaign_id}', '{campaign_name}', '{spu_id}', {inventory_per_campaign}, 0, "
                    f"'{start_time.strftime('%Y-%m-%d %H:%M:%S')}', '{end_time.strftime('%Y-%m-%d %H:%M:%S')}', "
                    f"'active', {flash_price}, {max_per_order}, '{start_time.strftime('%Y-%m-%d %H:%M:%S')}', "
                    f"'{start_time.strftime('%Y-%m-%d %H:%M:%S')}')"
                )

            # Bulk insert SPUs
            if spu_values:
                spu_sql = f"""
                    INSERT INTO spus (id, name, slug, description, is_active, created_at, updated_at)
                    VALUES {','.join(spu_values)}
                """
                await session.execute(text(spu_sql))

            # Bulk insert SKUs
            if sku_values:
                sku_sql = f"""
                    INSERT INTO skus (id, sku_code, name, spu_id, price, cost_price, weight, track_inventory, is_active, created_at, updated_at)
                    VALUES {','.join(sku_values)}
                """
                await session.execute(text(sku_sql))

            # Bulk insert inventory
            if inventory_values:
                inv_sql = f"""
                    INSERT INTO inventory (id, sku_id, quantity, reserved_quantity, allow_negative_stock, created_at, updated_at)
                    VALUES {','.join(inventory_values)}
                """
                await session.execute(text(inv_sql))

            # Bulk insert flash sale campaigns
            if campaign_values:
                campaign_sql = f"""
                    INSERT INTO flash_sales (id, campaign_name, spu_id, total_sale_limit, sold_count,
                                            start_time, end_time, status, flash_sale_price, max_per_order,
                                            created_at, updated_at)
                    VALUES {','.join(campaign_values)}
                """
                await session.execute(text(campaign_sql))

            await session.commit()

            progress = ((batch_end) / num_campaigns) * 100
            print(f"  Progress: {batch_end:,} / {num_campaigns:,} ({progress:.1f}%)")

    print(f"\n✓ Successfully created {num_campaigns:,} flash sale campaigns")
    print(f"✓ Total inventory available: {num_campaigns * inventory_per_campaign:,} units\n")


async def verify_data(num_campaigns: int):
    """Verify the generated data."""
    async with AsyncSessionLocal() as session:
        # Count campaigns
        result = await session.execute(text("SELECT COUNT(*) FROM flash_sales WHERE campaign_name LIKE 'Campaign-%'"))
        campaign_count = result.scalar()

        # Count SPUs
        result = await session.execute(text("SELECT COUNT(*) FROM spus WHERE slug LIKE 'flash-sale-test-%'"))
        spu_count = result.scalar()

        # Count SKUs
        result = await session.execute(text("SELECT COUNT(*) FROM skus WHERE sku_code LIKE 'FS-%'"))
        sku_count = result.scalar()

        # Count inventory
        result = await session.execute(text("""
            SELECT COUNT(*), SUM(quantity)
            FROM inventory
            WHERE sku_id IN (SELECT id FROM skus WHERE sku_code LIKE 'FS-%')
        """))
        inv_count, total_inventory = result.fetchone()
        total_inventory = total_inventory or 0

        # Get a sample campaign ID for testing
        result = await session.execute(text("""
            SELECT id FROM flash_sales
            WHERE campaign_name LIKE 'Campaign-%'
            LIMIT 1
        """))
        sample_campaign_id = result.scalar()

        print("Verification:")
        print(f"  Flash Sale Campaigns: {campaign_count:,}")
        print(f"  SPUs: {spu_count:,}")
        print(f"  SKUs: {sku_count:,}")
        print(f"  Inventory records: {inv_count:,}")
        print(f"  Total inventory: {total_inventory:,} units")
        if sample_campaign_id:
            print(f"\n  Sample Campaign ID: {sample_campaign_id}")
            print(f"  Test with: curl http://localhost:8000/api/v1/flash-sale-campaigns/{sample_campaign_id}/status")
        print()


async def main():
    num_campaigns = int(sys.argv[1]) if len(sys.argv) > 1 else 100000
    inventory_per_campaign = int(sys.argv[2]) if len(sys.argv) > 2 else 10000

    print("=" * 80)
    print("Flash Sale Campaign Setup - Variant X")
    print("=" * 80)

    # Clean existing test data
    await clean_flash_sale_data()

    # Create campaigns
    await create_flash_sale_campaigns(num_campaigns, inventory_per_campaign)

    # Verify
    await verify_data(num_campaigns)

    print("=" * 80)
    print("Setup complete!")
    print("=" * 80)
    print("\nNext steps:")
    print("  1. Load campaigns into Redis (if using Variant X)")
    print("  2. Run stress test: wrk -t4 -c50 -d10s http://localhost:8000/...")
    print()

    # Cleanup
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
