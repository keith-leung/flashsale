#!/usr/bin/env python3
"""
Initialize Redis Pools for Variant A (Adaptive Batching)

This script populates the Redis inventory pools based on the database configuration.
It implements the "Dual-Layer" initialization:
1. SPU Pool: fs:{campaign_id}:redis_pool:spu_counter
2. SKU Pools: fs:{campaign_id}:redis_pool:sku:{sku_id}

Usage:
    python init_redis_pools.py [--campaign_id UUID]
"""

import asyncio
import sys
import argparse
from sqlalchemy import text
from app.core.database import AsyncSessionLocal
from app.core.redis_cache import redis_cache

async def init_pools(campaign_id: str = None):
    print(f"Initializing Redis Pools for Variant A...")
    
    # Connect to Redis
    await redis_cache.connect()
    
    async with AsyncSessionLocal() as db:
        # 1. Fetch Campaign Config
        query = text("""
            SELECT 
                c.id, c.name, c.spu_id, 
                c.total_sale_limit, 
                c.redis_percentage,
                c.preallocate_percentage
            FROM flash_sale_campaigns c
            WHERE c.status = 'active'
            AND c.is_active = 1
        """)
        
        if campaign_id:
            query = text(query.text + " AND c.id = :cid")
            result = await db.execute(query, {"cid": campaign_id})
        else:
            result = await db.execute(query)
            
        campaigns = result.fetchall()
        
        if not campaigns:
            print("No active campaigns found.")
            return

        for camp in campaigns:
            print(f"\nProcessing Campaign: {camp.name} ({camp.id})")
            
            # Calculate Pool Size
            # Logic: The "Redis Pool" holds the stock available for async refills.
            # Ideally, this is total_limit * redis_percentage / 100.
            # However, for robustness in this benchmark, we might put ALL stock 
            # in the pool if pre-allocation logic implies "pulling" the first batch too.
            # Based on README: "Pre-allocate 60%... Redis pool 40%".
            # We will strictly follow the config.
            
            pool_size = int(camp.total_sale_limit * camp.redis_percentage / 100)
            preallocated_size = int(camp.total_sale_limit * camp.preallocate_percentage / 100)
            
            print(f"  - Total Limit: {camp.total_sale_limit}")
            print(f"  - Redis Pool ({camp.redis_percentage}%): {pool_size}")
            print(f"  - Service Pre-alloc ({camp.preallocate_percentage}%): {preallocated_size}")
            
            # 2. Set SPU Pool Key
            spu_key = f"fs:{camp.id}:redis_pool:spu_counter"
            await redis_cache.client.set(spu_key, pool_size)
            print(f"  - Set {spu_key} = {pool_size}")
            
            # 3. Fetch SKUs and Set SKU Pools
            sku_query = text("SELECT id, sku_code FROM skus WHERE spu_id = :spu_id")
            sku_result = await db.execute(sku_query, {"spu_id": camp.spu_id})
            skus = sku_result.fetchall()
            
            if not skus:
                print("  ! No SKUs found for this campaign SPU")
                continue
                
            # Distribute pool evenly across SKUs (simplification for benchmark)
            sku_pool_size = pool_size // len(skus)
            
            for sku in skus:
                sku_key = f"fs:{camp.id}:redis_pool:sku:{sku.id}"
                await redis_cache.client.set(sku_key, sku_pool_size)
                print(f"    - Set {sku_key} = {sku_pool_size}")
                
                # Also set metadata for routing (Variant X/A compatibility)
                meta_key = f"sku:{sku.id}:meta"
                await redis_cache.client.hset(meta_key, mapping={
                    "flash_sale_id": camp.id,
                    "status": "active"
                })

    print("\nRedis Pool Initialization Complete.")
    await redis_cache.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign_id", help="Specific campaign ID to init")
    args = parser.parse_args()
    
    asyncio.run(init_pools(args.campaign_id))
