#!/usr/bin/env python3
"""
Setup test data for order API stress testing.

This script:
1. Generates SPUs (products)
2. Generates SKUs (product variants) for each SPU
3. Creates inventory records with HIGH stock levels to ensure successful orders
4. Outputs SKU IDs to a file for wrk to use

Usage:
    python setup_test_data.py [num_spus] [skus_per_spu] [stock_per_sku]

Example:
    python setup_test_data.py 100 5 10000
    (Creates 100 SPUs, 5 SKUs each = 500 total SKUs, each with 10,000 stock)
"""

import asyncio
import sys
from datetime import datetime
from uuid import uuid4

from sqlalchemy import text
from app.core.database import AsyncSessionLocal, engine


async def clean_test_data():
    """Clean existing test data."""
    async with AsyncSessionLocal() as session:
        # Delete in reverse order of dependencies
        await session.execute(text("DELETE FROM order_line_items WHERE order_id IN (SELECT id FROM orders WHERE customer_email LIKE 'stress-test%')"))
        await session.execute(text("DELETE FROM orders WHERE customer_email LIKE 'stress-test%'"))
        await session.execute(text("DELETE FROM inventory WHERE sku_id IN (SELECT id FROM skus WHERE sku_code LIKE 'STRESS-%')"))
        await session.execute(text("DELETE FROM skus WHERE sku_code LIKE 'STRESS-%'"))
        await session.execute(text("DELETE FROM spus WHERE slug LIKE 'stress-test-%'"))
        await session.commit()
        print("✓ Cleaned existing test data")


async def generate_test_data(num_spus: int, skus_per_spu: int, stock_per_sku: int):
    """Generate test data for stress testing."""

    print(f"\nGenerating test data:")
    print(f"  SPUs: {num_spus}")
    print(f"  SKUs per SPU: {skus_per_spu}")
    print(f"  Stock per SKU: {stock_per_sku}")
    print(f"  Total SKUs: {num_spus * skus_per_spu}")
    print()

    sku_ids = []

    async with AsyncSessionLocal() as session:
        # Generate SPUs and SKUs in batches for better performance
        batch_size = 50

        for batch_start in range(0, num_spus, batch_size):
            batch_end = min(batch_start + batch_size, num_spus)

            spu_values = []
            sku_values = []
            inventory_values = []

            for i in range(batch_start, batch_end):
                # Generate SPU
                spu_id = str(uuid4())
                spu_slug = f"stress-test-product-{i:06d}"
                spu_name = f"Stress Test Product {i:06d}"

                spu_values.append(f"('{spu_id}', '{spu_name}', '{spu_slug}', 'Test product for stress testing', 1)")

                # Generate SKUs for this SPU
                for j in range(skus_per_spu):
                    sku_id = str(uuid4())
                    sku_code = f"STRESS-{i:06d}-{j:03d}"
                    sku_name = f"Variant {j:03d}"
                    price = 99.99
                    cost_price = 50.00
                    weight = 1.5

                    sku_values.append(
                        f"('{sku_id}', '{sku_code}', '{sku_name}', '{spu_id}', {price}, {cost_price}, {weight}, 1, 1)"
                    )

                    # Generate inventory for this SKU
                    inventory_id = str(uuid4())
                    inventory_values.append(
                        f"('{inventory_id}', '{sku_id}', {stock_per_sku}, 0, 0)"
                    )

                    sku_ids.append(sku_id)

            # Bulk insert SPUs
            if spu_values:
                spu_sql = f"""
                    INSERT INTO spus (id, name, slug, description, is_active)
                    VALUES {','.join(spu_values)}
                """
                await session.execute(text(spu_sql))

            # Bulk insert SKUs
            if sku_values:
                sku_sql = f"""
                    INSERT INTO skus (id, sku_code, name, spu_id, price, cost_price, weight, track_inventory, is_active)
                    VALUES {','.join(sku_values)}
                """
                await session.execute(text(sku_sql))

            # Bulk insert inventory
            if inventory_values:
                inventory_sql = f"""
                    INSERT INTO inventory (id, sku_id, quantity, reserved_quantity, allow_negative_stock)
                    VALUES {','.join(inventory_values)}
                """
                await session.execute(text(inventory_sql))

            await session.commit()

            print(f"  Created batch {batch_start//batch_size + 1}/{(num_spus + batch_size - 1)//batch_size}: SPUs {batch_start}-{batch_end-1}")

    # Write SKU IDs to file for wrk to use
    with open('/tmp/stress_test_sku_ids.txt', 'w') as f:
        for sku_id in sku_ids:
            f.write(f"{sku_id}\n")

    print(f"\n✓ Successfully created {len(sku_ids)} SKUs")
    print(f"✓ SKU IDs written to /tmp/stress_test_sku_ids.txt")
    print(f"✓ Total available stock: {len(sku_ids) * stock_per_sku:,} units\n")

    return sku_ids


async def verify_data():
    """Verify the generated data."""
    async with AsyncSessionLocal() as session:
        # Count SPUs
        result = await session.execute(text("SELECT COUNT(*) FROM spus WHERE slug LIKE 'stress-test-%'"))
        spu_count = result.scalar()

        # Count SKUs
        result = await session.execute(text("SELECT COUNT(*) FROM skus WHERE sku_code LIKE 'STRESS-%'"))
        sku_count = result.scalar()

        # Count inventory
        result = await session.execute(text("""
            SELECT COUNT(*), SUM(quantity)
            FROM inventory
            WHERE sku_id IN (SELECT id FROM skus WHERE sku_code LIKE 'STRESS-%')
        """))
        inv_count, total_stock = result.fetchone()
        total_stock = total_stock or 0  # Handle None when no records exist

        print(f"Verification:")
        print(f"  SPUs: {spu_count}")
        print(f"  SKUs: {sku_count}")
        print(f"  Inventory records: {inv_count}")
        print(f"  Total stock: {total_stock:,}")
        print()


async def main():
    # Parse arguments
    num_spus = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    skus_per_spu = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    stock_per_sku = int(sys.argv[3]) if len(sys.argv) > 3 else 10000

    print("=" * 60)
    print("Order API Stress Test - Data Setup")
    print("=" * 60)

    # Clean existing test data
    await clean_test_data()

    # Generate new test data
    await generate_test_data(num_spus, skus_per_spu, stock_per_sku)

    # Verify
    await verify_data()

    print("=" * 60)
    print("Setup complete! You can now run: ./benchmark_orders.sh")
    print("=" * 60)

    # Properly close database engine to avoid event loop warning
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
