"""Campaign cache loader - Variant Zeta (Redis-First Architecture) - FIXED."""

import asyncio
import aiomysql
from redis.asyncio import Redis
from typing import Dict, Any

from app.core.config import settings


async def preload_campaign_cache(redis: Redis):
    """Preload campaign data into Redis using design schema format."""
    
    print("=" * 80)
    print("Loading Campaign Cache (Design Schema Format)")
    print("=" * 80)
    
    # Connect to database
    db = await aiomysql.connect(
        host='flash-mariadb-zeta',
        port=3306,
        user='syracuse',
        password='Orange_315_Forever!',
        db='orange315'
    )
    
    try:
        # Load campaigns
        async with db.cursor() as cursor:
            await cursor.execute("""
                SELECT id, spu_id, name, description, total_sale_limit, sold_quantity, 
                       start_time, end_time, flash_price, max_quantity_per_customer,
                       status, is_active
                FROM flash_sale_campaigns
                WHERE is_active = TRUE AND status = 'active'
            """)
            campaigns = await cursor.fetchall()
            
            print(f"  Found {len(campaigns)} active campaigns")
            
            for campaign in campaigns:
                (campaign_id, spu_id, name, description, total_limit, sold,
                 start_time, end_time, flash_price, max_qty, status, is_active) = campaign
                
                # FIXED: Use design schema: campaign:{spu_id}:HASH
                campaign_key = f'campaign:{spu_id}'
                
                await redis.hset(campaign_key, mapping={
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
                })
                
                # Set TTL (60 seconds as per design)
                await redis.expire(campaign_key, 60)
                
                if len(str(spu_id)) % 10 == 0:
                    print(f"  Loaded campaign {spu_id}")
            
            print(f"  ✓ Loaded {len(campaigns)} campaigns to Redis")
    
    finally:
        await db.close()


async def preload_sku_cache(redis: Redis):
    """Preload SKU data into Redis using design schema format."""
    
    print("\n" + "=" * 80)
    print("Loading SKU Cache (Design Schema Format)")
    print("=" * 80)
    
    # Connect to database
    db = await aiomysql.connect(
        host='flash-mariadb-zeta',
        port=3306,
        user='syracuse',
        password='Orange_315_Forever!',
        db='orange315'
    )
    
    try:
        # Load SKUs
        async with db.cursor() as cursor:
            await cursor.execute("""
                SELECT id, sku_code, name, spu_id, price, is_active
                FROM skus
                WHERE is_active = TRUE AND sku_code LIKE 'STRESS-SKU%'
            """)
            skus = await cursor.fetchall()
            
            print(f"  Found {len(skus)} active SKUs")
            
            for sku in skus:
                (sku_id, sku_code, name, spu_id, price, is_active) = sku
                
                # FIXED: Use design schema: sku:{id}:metadata
                sku_key = f'sku:{sku_id}:metadata'
                
                await redis.hset(sku_key, mapping={
                    'id': sku_id,
                    'sku_code': sku_code,
                    'name': name,
                    'spu_id': spu_id,
                    'price': str(price),
                    'is_active': 'true' if is_active else 'false'
                })
                
                # Set TTL (60 seconds as per design)
                await redis.expire(sku_key, 60)
                
                if len(str(sku_id)) % 10 == 0:
                    print(f"  Loaded SKU {sku_code}")
            
            print(f"  ✓ Loaded {len(skus)} SKUs to Redis")
    
    finally:
        await db.close()


async def preload_stock_cache(redis: Redis):
    """Preload stock data into Redis using design schema format."""
    
    print("\n" + "=" * 80)
    print("Loading Stock Cache (Design Schema Format)")
    print("=" * 80)
    
    # Connect to database
    db = await aiomysql.connect(
        host='flash-mariadb-zeta',
        port=3306,
        user='syracuse',
        password='Orange_315_Forever!',
        db='orange315'
    )
    
    try:
        # Load inventory
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
                
                # FIXED: Use design schema: sku:{id}:stock:INTEGER
                stock_key = f'sku:{sku_id}:stock'
                
                await redis.set(stock_key, quantity)
                # No TTL for stock (as per design)
                
                if len(str(sku_id)) % 10 == 0:
                    print(f"  Loaded stock for SKU {sku_id}: {quantity}")
            
            print(f"  ✓ Loaded {len(inventories)} stock records to Redis")
    
    finally:
        await db.close()


async def load_all_caches():
    """Load all caches into Redis."""
    from redis.asyncio import Redis
    from app.core.config import settings
    
    redis = Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        db=settings.redis_db,
        decode_responses=True
    )
    
    try:
        await preload_campaign_cache(redis)
        await preload_sku_cache(redis)
        await preload_stock_cache(redis)
        
        print("\n" + "=" * 80)
        print("✓ All caches loaded successfully")
        print("=" * 80)
        
        # Print Redis stats
        dbsize = await redis.dbsize()
        print(f"  Total Redis keys: {dbsize}")
        
    finally:
        await redis.aclose()


if __name__ == '__main__':
    asyncio.run(load_all_caches())
