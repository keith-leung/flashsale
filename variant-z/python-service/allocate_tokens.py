#!/usr/bin/env python3
"""Allocate tokens for benchmark campaign."""
import asyncio
import sys
import os

# Add app directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.token_manager import token_manager
from app.core.redis import redis_client
from app.core.database import async_session_maker

async def main():
    # Allocate tokens for campaign
    campaign_id = '67ca0e1e-0a59-473e-a04d-23fd26accd1b'
    spu_id = '20d904dd-f41a-4570-92cb-21acb55e9481'
    sku_id = '5fe42b9b-6eb7-4fac-ac9b-a74a8209a2fc'
    
    # Get database session
    async with async_session_maker() as db:
        # Allocate 9,999 tokens (campaign limit is 10,000, 1 already sold)
        result = await token_manager.allocate_campaign_tokens(
            db=db,
            campaign_id=campaign_id,
            spu_id=spu_id,
            total_limit=9999
        )
        print(f'Token allocation result: {result} tokens allocated')
    
    # Cache SKU inventory (using the correct method)
    await redis_client.cache_sku_inventory(sku_id, 10000, ttl=None)
    print(f'Cached inventory for SKU {sku_id}: 10000')
    
    # Verify
    token_count = await redis_client.get_remaining_tokens(campaign_id)
    print(f'Tokens in Redis: {token_count}')

if __name__ == '__main__':
    asyncio.run(main())