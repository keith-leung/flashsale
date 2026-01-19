"""Load all data into Redis for Variant Zeta (Fixed)."""

import asyncio
import aiomysql
from typing import Dict, Any
from redis.asyncio import Redis


async def load_skus(redis: Redis):
    """Load SKU data into Redis."""
    print("=" * 80)
    print("[1/3] Loading SKUs...")
    print("=" * 80)
    
    db = await aiomysql.connect(
        host='flash-mariadb-zeta',
        port=3306,
        user='syracuse',
        password='Orange_315_Forever!',
        db='orange315'
    )
    
    try:
        async with db.cursor() as cursor:
            await cursor.execute("""
                SELECT id, sku_code, name, spu_id, price
                FROM skus
                WHERE is_active = TRUE AND sku_code LIKE 'STRESS-SKU%'
            """)
            skus = await cursor.fetchall()
            
            print(f"  Found {len(skus)} SKUs")
            
            for sku in skus:
                (sku_id, sku_code, name, spu_id, price) = sku
                
                await redis.hset(f'sku:{sku_id}', mapping={
                    'id': sku_id,
                    'sku_code': sku_code,
                    'name': name,
                    'spu_id': spu_id,
                    'price': str(price)
                })
            
            print(f"  ✓ Loaded {len(skus)} SKUs into Redis")
    
    finally:
        await db.close()


async def load_inventory(redis: Redis):
    """Load inventory data into Redis."""
    print("\n" + "=" * 80)
    print("[2/3] Loading Inventory...")
    print("=" * 80)
    
    db = await aiomysql.connect(
        host='flash-mariadb-zeta',
        port=3306,
        user='syracuse',
        password='Orange_315_Forever!',
        db='orange315'
    )
    
    try:
        async with db.cursor() as cursor:
            await cursor.execute("""
                SELECT sku_id, quantity
                FROM inventory
                WHERE sku_id IN (
                    SELECT id FROM skus WHERE sku_code LIKE 'STRESS-SKU%'
                )
            """)
            inventories = await cursor.fetchall()
            
            print(f"  Found {len(inventories)} inventory records")
            
            for inv in inventories:
                (sku_id, quantity) = inv
                
                await redis.hset(f'stock:{sku_id}', mapping={
                    'available': str(quantity),
                    'reserved': '0'
                })
            
            print(f"  ✓ Loaded {len(inventories)} inventory records into Redis")
    
    finally:
        await db.close()


async def load_campaigns(redis: Redis):
    """Load campaign data into Redis (FIXED)."""
    print("\n" + "=" * 80)
    print("[3/3] Loading Campaigns...")
    print("=" * 80)
    
    db = await aiomysql.connect(
        host='flash-mariadb-zeta',
        port=3306,
        user='syracuse',
        password='Orange_315_Forever!',
        db='orange315'
    )
    
    try:
        async with db.cursor() as cursor:
            await cursor.execute("""
                SELECT id, spu_id, name, description, total_sale_limit, sold_quantity, 
                       start_time, end_time, flash_price, max_quantity_per_customer,
                       status, is_active
                FROM flash_sale_campaigns
                WHERE is_active = TRUE AND status = 'active'
            """)
            campaigns = await cursor.fetchall()
            
            print(f"  Found {len(campaigns)} campaigns")
            
            for campaign in campaigns:
                (campaign_id, spu_id, name, description, total_limit, sold,
                 start_time, end_time, flash_price, max_qty, status, is_active) = campaign
                
                campaign_data = {
                    'id': campaign_id,
                    'spu_id': spu_id,
                    'name': name,
                    'description': description or '',
                    'total_sale_limit': str(total_limit),
                    'sold_quantity': str(sold),
                    'start_time': str(start_time),
                    'end_time': str(end_time),
                    'flash_price': str(flash_price) if flash_price else '',
                    'max_quantity_per_customer': str(max_qty),
                    'status': status,
                    'is_active': 'true' if is_active else 'false'
                }
                
                # FIXED: Create campaign:{spu_id} as HASH (correct format for API)
                await redis.hset(f'campaign:{spu_id}', mapping=campaign_data)
            
            print(f"  ✓ Loaded {len(campaigns)} campaigns into Redis")
    
    finally:
        await db.close()


async def verify_data(redis: Redis):
    """Verify Redis data was loaded correctly."""
    print("\n" + "=" * 80)
    print("Verifying Redis Data")
    print("=" * 80)
    
    # Check SKU
    sample_sku = await redis.hgetall('sku:e9d1807a-f22b-11f0-bbc4-9660160e28bc')
    print(f"  ✓ Sample SKU found: {sample_sku.get('name')}")
    
    # Check stock
    sample_stock = await redis.hgetall('stock:e9d1807a-f22b-11f0-bbc4-9660160e28bc')
    print(f"  ✓ Sample stock: {sample_stock.get('available')} available")
    
    # Check campaign
    spu_id = 'e9d181c3-f22b-11f0-bbc4-9660160e28bc'
    campaign = await redis.hgetall(f'campaign:{spu_id}')
    if campaign:
        print(f"  ✓ Sample campaign found: {campaign.get('name')}")
        print(f"  ✓ Campaign type: HASH (correct)")
    else:
        print(f"  ✗ Campaign not found: campaign:{spu_id}")


async def main():
    """Main function."""
    print("=" * 80)
    print("Loading all data into Redis for Variant Zeta (FIXED)")
    print("=" * 80)
    
    redis = Redis(host='flash-redis-zeta', port=6379, db=0, decode_responses=True)
    
    try:
        await load_skus(redis)
        await load_inventory(redis)
        await load_campaigns(redis)
        await verify_data(redis)
        
        print("\n" + "=" * 80)
        print("✓ Redis Setup Complete")
        print("=" * 80)
    finally:
        await redis.aclose()


if __name__ == '__main__':
    asyncio.run(main())
