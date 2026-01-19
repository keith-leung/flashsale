"""Token pre-allocation manager for Variant Z."""

import logging
import uuid
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.redis import redis_client
from app.models.sku import SKU
from app.models.inventory import Inventory

logger = logging.getLogger(__name__)


class TokenManager:
    """Manages token pre-allocation for flash sale campaigns."""
    
    @staticmethod
    async def allocate_campaign_tokens(
        db: AsyncSession,
        campaign_id: str,
        spu_id: str,
        total_limit: int
    ) -> int:
        """
        Pre-allocate tokens for a campaign.
        
        Args:
            db: Database session
            campaign_id: Campaign UUID
            spu_id: SPU UUID
            total_limit: Total tokens to allocate (campaign.total_sale_limit)
        
        Returns:
            Number of tokens allocated
        """
        # Get all SKUs for this SPU
        result = await db.execute(
            select(SKU, Inventory)
            .join(Inventory, SKU.id == Inventory.sku_id)
            .where(SKU.spu_id == spu_id)
            .where(SKU.is_active == True)
        )
        sku_inventories = result.all()
        
        if not sku_inventories:
            logger.warning(f"No active SKUs found for SPU {spu_id}")
            return 0
        
        # Calculate total inventory across all SKUs
        total_inventory = sum(inv.quantity for (sku, inv) in sku_inventories)
        
        if total_inventory == 0:
            logger.warning(f"No inventory available for SPU {spu_id}")
            return 0
        
        # Distribute tokens proportionally to SKU inventory ratios
        tokens = []
        for sku, inventory in sku_inventories:
            # Proportional allocation
            sku_token_count = min(
                inventory.quantity,
                int(total_limit * (inventory.quantity / total_inventory))
            )
            
            # Create tokens for this SKU
            for _ in range(sku_token_count):
                token_id = f"token_{uuid.uuid4()}_{sku.id}"
                tokens.append(token_id)
            
            # Cache SKU inventory in Redis (no TTL - inventory updated synchronously)
            await redis_client.cache_sku_inventory(
                sku.id,
                inventory.quantity,
                ttl=None  # No expiration - inventory is source of truth in DB
            )
            
            logger.info(
                f"Allocated {sku_token_count} tokens for SKU {sku.sku_code} "
                f"(inventory: {inventory.quantity})"
            )
        
        # Store tokens in Redis sorted set
        await redis_client.allocate_campaign_tokens(
            campaign_id,
            tokens,
            total_limit
        )
        
        logger.info(
            f"Pre-allocated {len(tokens)} tokens for campaign {campaign_id} "
            f"(SPU: {spu_id}, limit: {total_limit})"
        )
        
        return len(tokens)
    
    @staticmethod
    async def acquire_token(
        campaign_id: str,
        sku_id: str,
        quantity: int = 1
    ) -> dict:
        """
        Acquire a token atomically using Lua script.
        
        The Lua script uses ZPOPMIN to pop the first available token from the
        campaign's sorted set (FIFO ordering).
        
        Args:
            campaign_id: Campaign UUID
            sku_id: SKU UUID
            quantity: Quantity to purchase
        
        Returns:
            Dict with 'ok' or 'err' key
        """
        keys = [
            f"campaign:{campaign_id}:tokens",
            f"sku:{sku_id}:inventory",
            f"campaign:{campaign_id}:metadata"
        ]
        # Lua script expects: quantity, campaign_id
        args = [str(quantity), campaign_id]
        
        result = await redis_client.execute_lua_script(
            "/app/acquire_order_token.lua",
            keys,
            args
        )
        
        return result
    
    @staticmethod
    async def get_campaign_remaining_tokens(campaign_id: str) -> int:
        """Get remaining token count for a campaign."""
        return await redis_client.get_remaining_tokens(campaign_id)
    
    @staticmethod
    async def is_campaign_sold_out(campaign_id: str) -> bool:
        """Check if campaign has no remaining tokens."""
        remaining = await redis_client.get_remaining_tokens(campaign_id)
        return remaining == 0


token_manager = TokenManager()