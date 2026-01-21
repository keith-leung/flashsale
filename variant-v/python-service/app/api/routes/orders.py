from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
import uuid
from ...services.audit_service import audit_service
from ...services.distributed_lock import distributed_lock, LockGuard
from ...services.redis_manager import redis_manager
import aiomysql

# Request/Response models
class OrderItem(BaseModel):
    sku_id: str = Field(..., description="SKU ID for the ordered item")
    quantity: int = Field(..., gt=0, description="Quantity ordered")
    unit_price: float = Field(..., gt=0, description="Unit price")

class OrderCreate(BaseModel):
    customer_email: EmailStr = Field(..., description="Customer email address")
    items: List[OrderItem] = Field(..., min_items=1, description="Order items")
    flash_sale_campaign_id: str = Field(..., description="Flash sale campaign ID")

class OrderResponse(BaseModel):
    audit_id: str = Field(..., description="Audit log ID for tracking")
    status: str = Field(..., description="Order status")
    message: str = Field(..., description="Status message")

router = APIRouter()

import logging
logger = logging.getLogger(__name__)

async def validate_campaign_limits(campaign_id: str, items: List[OrderItem]) -> bool:
    """Validate campaign limits and SKU availability."""
    # Check Redis for campaign limits
    total_sold_key = f"campaign:{campaign_id}:total_sold"
    total_limit_key = f"campaign:{campaign_id}:total_limit"
    
    # Campaign totals are stored on Redis node 0 (primary node)
    # This ensures totals are accessible regardless of which SKU node is being accessed
    redis_node_totals = redis_manager.nodes[0]
    
    # Check total campaign limit
    total_sold = int(redis_node_totals.get(total_sold_key) or 0)
    total_limit = int(redis_node_totals.get(total_limit_key) or 0)
    
    total_requested = sum(item.quantity for item in items)
    
    logger.info(f"[DEBUG] Validating campaign {campaign_id}: sold={total_sold}, limit={total_limit}, requested={total_requested}")
    
    if total_sold + total_requested > total_limit:
        logger.info(f"[DEBUG] Campaign limit exceeded")
        return False
    
    # Check per-SKU limits
    for item in items:
        sku_remaining_key = f"campaign:{campaign_id}:sku:{item.sku_id}:remaining"
        sku_node = redis_manager.get_node_for_sku(item.sku_id)
        
        remaining = int(sku_node.get(sku_remaining_key) or 0)
        logger.info(f"[DEBUG] SKU {item.sku_id}: remaining={remaining}, requested={item.quantity}, node={redis_manager.nodes.index(sku_node)}")
        
        if item.quantity > remaining:
            logger.info(f"[DEBUG] SKU {item.sku_id} insufficient stock")
            return False
    
    logger.info(f"[DEBUG] Validation passed")
    return True

async def decrement_campaign_limits(campaign_id: str, items: List[OrderItem]) -> bool:
    """Decrement campaign limits after successful audit.
    Returns True if successful, False if limit exceeded (rollback)
    """
    # First get the limits to verify
    total_limit_key = f"campaign:{campaign_id}:total_limit"
    total_limit = int(redis_manager.nodes[0].get(total_limit_key) or 0)
    
    # Atomic increment with result check for campaign limit
    total_sold_key = f"campaign:{campaign_id}:total_sold"
    total_requested = sum(item.quantity for item in items)
    
    new_total_sold = redis_manager.nodes[0].incrby(total_sold_key, total_requested)
    
    # Verify increment didn't exceed campaign limit - rollback if needed
    if new_total_sold > total_limit:
        # Rollback: restore counter to previous value
        redis_manager.nodes[0].incrby(total_sold_key, -total_requested)
        return False
    
    # Now verify and decrement SKU counters
    # Use multi-decrement and check for negative results
    decremented_skus = []
    try:
        for item in items:
            sku_remaining_key = f"campaign:{campaign_id}:sku:{item.sku_id}:remaining"
            sku_node = redis_manager.get_node_for_sku(item.sku_id)
            
            # Check current remaining before decrement
            current_remaining = int(sku_node.get(sku_remaining_key) or 0)
            if item.quantity > current_remaining:
                # SKU insufficient stock - rollback everything
                raise ValueError(f"SKU {item.sku_id} insufficient stock")
            
            # Decrement and track for rollback if needed
            new_remaining = sku_node.decrby(sku_remaining_key, item.quantity)
            logger.error(f"[DEBUG] SKU decrement: {item.sku_id} from {current_remaining} by {item.quantity} = {new_remaining}")
            decremented_skus.append((sku_node, sku_remaining_key, item.quantity))
            
            # Verify SKU didn't go negative
            if new_remaining < 0:
                # SKU went negative - rollback everything
                logger.error(f"[DEBUG] SKU {item.sku_id} went negative! Rolling back")
                raise ValueError(f"SKU {item.sku_id} went negative after decrement")
        
        # All checks passed
        return True
        
    except Exception as e:
        # Rollback all changes
        logger.error(f"Error during decrement, rolling back: {e}")
        
        # Rollback campaign counter
        redis_manager.nodes[0].incrby(total_sold_key, -total_requested)
        
        # Rollback all SKU decrements
        for sku_node, sku_key, quantity in decremented_skus:
            sku_node.incrby(sku_key, quantity)
        
        return False

@router.post("/", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(order_data: OrderCreate):
    """
    Create a new flash sale order with write-ahead audit and distributed locking.
    
    Flow:
    1. Write audit record (status='pending')
    2. Acquire distributed lock(s) for SKU(s)
    3. Validate campaign limits + SKU stock
    4. Confirm audit
    5. Decrement campaign counters
    6. Return HTTP 201 (order queued for batch processing)
    """
    try:
        # 1. Write audit record (status='pending')
        # Convert items to flat format for audit (single-SKU orders for now)
        if len(order_data.items) != 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only single-SKU orders supported in this version"
            )
        
        item = order_data.items[0]
        audit_data = {
            "customer_email": order_data.customer_email,
            "sku_id": item.sku_id,
            "quantity": item.quantity,
            "unit_price": item.unit_price,
            "flash_sale_campaign_id": order_data.flash_sale_campaign_id
        }
        
        audit_id = await audit_service.create_audit_record(audit_data)
        
        # 2. Acquire distributed lock for SKU
        lock_resource = f"sku:{item.sku_id}:campaign:{order_data.flash_sale_campaign_id}"
        
        async with LockGuard(distributed_lock, lock_resource, item.sku_id) as lock:
            if not lock:
                await audit_service.fail_audit(audit_id, "lock_acquisition_failed")
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Resource busy, please retry"
                )
            
            # 3. Validate campaign limits + SKU stock
            if not await validate_campaign_limits(order_data.flash_sale_campaign_id, order_data.items):
                await audit_service.fail_audit(audit_id, "campaign_limit_exceeded")
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Campaign sold out or SKU unavailable"
                )
            
            # 4. Confirm audit
            if not await audit_service.confirm_audit(audit_id):
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to confirm order"
                )
            
            # 5. Decrement campaign counters (optimistic - will be reconciled by batch processor)
            await decrement_campaign_limits(order_data.flash_sale_campaign_id, order_data.items)
        
        # Lock automatically released by context manager
        
        # 6. Return HTTP 201 (order queued for batch processing)
        return OrderResponse(
            audit_id=audit_id,
            status="confirmed",
            message="Order confirmed and queued for processing"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        # Fail the audit if it was created
        if 'audit_id' in locals():
            await audit_service.fail_audit(audit_id, str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

@router.get("/{audit_id}")
async def get_order_status(audit_id: str):
    """Get the status of an order by audit ID."""
    audit = await audit_service.get_audit_by_id(audit_id)
    
    if not audit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    return {
        "audit_id": audit['id'],
        "order_id": audit['order_id'],
        "status": audit['status'],
        "sku_id": audit['sku_id'],
        "quantity": audit['quantity'],
        "created_at": audit['created_at']
    }
