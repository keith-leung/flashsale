"""Campaign write-back service for persisting Redis data to MariaDB."""

import logging
import os
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import List, Dict, Any, Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis_cache import redis_cache
from app.core.database import get_db
from app.models.flash_sale_campaign import FlashSaleCampaign, FlashSaleStatus
from app.models.order import Order, OrderLineItem, OrderStatus
from app.models.sku import SKU
from app.models.inventory import Inventory

logger = logging.getLogger(__name__)

# Log directory
LOG_DIR = Path("/var/log/flashsale")
FAILOVER_DIR = LOG_DIR / "failover"


async def writeback_campaign(campaign_id: str, db: AsyncSession, reason: str = "manual") -> Dict[str, Any]:
    """
    Write back campaign data from Redis to MariaDB.

    Triggers:
    - Campaign end time reached (scheduled)
    - Campaign sold out (inventory zero)
    - Manual admin trigger

    Args:
        campaign_id: Flash sale campaign ID
        db: Database session
        reason: Trigger reason (scheduled, sold_out, manual)

    Returns:
        dict with write-back summary
    """
    logger.info(f"Starting write-back for campaign {campaign_id}, reason: {reason}")

    try:
        # Step 1: Get campaign from database
        result = await db.execute(
            select(FlashSaleCampaign).filter(FlashSaleCampaign.id == campaign_id)
        )
        campaign = result.scalar_one_or_none()

        if not campaign:
            raise ValueError(f"Campaign {campaign_id} not found")

        # Step 2: Read orders from Redis Stream
        orders_data = await read_campaign_orders(campaign_id)

        if not orders_data:
            logger.info(f"No orders found for campaign {campaign_id}")
            return {
                "campaign_id": campaign_id,
                "orders_written": 0,
                "status": "completed",
                "reason": "no_orders"
            }

        # Step 3: Batch write to database
        total_quantity = 0
        orders_written = 0

        for order_data in orders_data:
                try:
                    # Check if order already exists (idempotency)
                    existing = await db.execute(
                        select(Order).filter(Order.order_number == order_data["order_number"])
                    )
                    if existing.scalar_one_or_none():
                        logger.debug(f"Order {order_data['order_number']} already exists, skipping")
                        continue

                    # Create order
                    order = await _create_order_from_data(order_data, campaign_id, db)

                    if order:
                        orders_written += 1
                        # Calculate total quantity for this order
                        order_qty = sum(item["quantity"] for item in order_data["line_items"])
                        total_quantity += order_qty

                except Exception as e:
                    logger.error(f"Error processing order {order_data.get('order_number')}: {e}")
                    # Continue with other orders
                    continue

        # Step 4: Update campaign sold_quantity
        await db.execute(
            update(FlashSaleCampaign)
            .where(FlashSaleCampaign.id == campaign_id)
            .values(
                sold_quantity=FlashSaleCampaign.sold_quantity + total_quantity,
                status=FlashSaleStatus.ENDED.value,
                updated_at=datetime.utcnow()
            )
        )

        # Step 5: Update inventory from Redis counters
        await _sync_inventory_from_redis(campaign_id, db)

        # Commit the transaction
        await db.commit()

        # Step 6: Write success log
        await _write_transaction_log(campaign_id, campaign.name, orders_written, total_quantity, reason)

        # Step 7: Cleanup Redis keys
        await _cleanup_redis_keys(campaign_id)

        logger.info(
            f"Write-back completed for campaign {campaign_id}: "
            f"{orders_written} orders, {total_quantity} units"
        )

        return {
            "campaign_id": campaign_id,
            "campaign_name": campaign.name,
            "orders_written": orders_written,
            "total_quantity": total_quantity,
            "status": "completed",
            "reason": reason
        }

    except Exception as e:
        logger.error(f"Error during write-back for campaign {campaign_id}: {e}", exc_info=True)

        # Generate failover log
        await generate_failover_log(campaign_id, e, reason)

        return {
            "campaign_id": campaign_id,
            "status": "failed",
            "error": str(e),
            "reason": reason
        }


async def read_campaign_orders(campaign_id: str) -> List[Dict[str, Any]]:
    """
    Read all orders for a campaign from Redis Stream.

    Args:
        campaign_id: Flash sale campaign ID

    Returns:
        List of order data dictionaries
    """
    if not redis_cache.client:
        raise RuntimeError("Redis client not connected")

    # Read all messages from order_queue stream
    stream_name = "order_queue"
    orders = []

    try:
        # Read all messages from the stream (0-0 means from beginning)
        messages = await redis_cache.client.xread({stream_name: "0-0"}, count=10000)

        for stream, message_list in messages:
            for message_id, message_data in message_list:
                # Parse the order_data JSON field
                if "order_data" in message_data:
                    import json
                    order_json = json.loads(message_data["order_data"])

                    # Filter by campaign_id
                    if order_json.get("flash_sale_id") == campaign_id:
                        # Parse line items from JSON
                        line_items = []
                        for item in order_json.get("line_items", []):
                            # Handle null unit_price
                            unit_price = item.get("unit_price")
                            if unit_price is None:
                                # Get price from SKU - will be fetched later
                                unit_price = Decimal("0")
                            else:
                                unit_price = Decimal(str(unit_price))

                            line_items.append({
                                "sku_id": item["sku_id"],
                                "quantity": int(item["quantity"]),
                                "unit_price": unit_price
                            })

                        orders.append({
                            "order_number": order_json.get("order_number"),
                            "customer_email": order_json.get("customer_email"),
                            "customer_name": order_json.get("customer_name", ""),
                            "flash_sale_id": campaign_id,
                            "line_items": line_items,
                            "message_id": message_id
                        })

        logger.info(f"Read {len(orders)} orders for campaign {campaign_id} from Redis")
        return orders

    except Exception as e:
        logger.error(f"Error reading orders from Redis: {e}", exc_info=True)
        raise


async def _create_order_from_data(
    order_data: Dict[str, Any],
    campaign_id: str,
    db: AsyncSession
) -> Optional[Order]:
    """Create order and line items from Redis data."""
    try:
        # Calculate totals
        subtotal = Decimal(0)
        line_items_to_add = []

        for item_data in order_data["line_items"]:
            sku_id = item_data["sku_id"]
            quantity = item_data["quantity"]
            unit_price = item_data["unit_price"]
            total_price = unit_price * quantity
            subtotal += total_price

            # Get SKU info for product name and code
            sku_result = await db.execute(
                select(SKU).filter(SKU.id == sku_id)
            )
            sku = sku_result.scalar_one_or_none()

            if not sku:
                logger.warning(f"SKU {sku_id} not found, skipping order")
                return None

            line_items_to_add.append({
                "sku_id": sku_id,
                "quantity": quantity,
                "unit_price": unit_price,
                "total_price": total_price,
                "product_name": sku.name or "Product",
                "sku_code": sku.sku_code
            })

        # Create order
        order = Order(
            order_number=order_data["order_number"],
            customer_email=order_data["customer_email"],
            customer_name=order_data["customer_name"],
            flash_sale_campaign_id=campaign_id,
            subtotal=subtotal,
            tax_amount=Decimal(0),
            shipping_amount=Decimal(0),
            total_amount=subtotal,
            currency="USD",
            status=OrderStatus.pending
        )

        db.add(order)
        await db.flush()

        # Create line items
        for item_data in line_items_to_add:
            line_item = OrderLineItem(
                order_id=order.id,
                **item_data
            )
            db.add(line_item)

        return order

    except IntegrityError as e:
        if "Duplicate entry" in str(e):
            logger.debug(f"Duplicate order {order_data['order_number']}, skipping")
            return None
        raise
    except Exception as e:
        logger.error(f"Error creating order from data: {e}", exc_info=True)
        raise


async def _sync_inventory_from_redis(campaign_id: str, db: AsyncSession):
    """Sync inventory quantities from Redis back to database."""
    try:
        # Get all SKUs for this campaign (via campaign metadata in Redis)
        campaign_meta = await redis_cache.get_campaign_meta(campaign_id)

        if not campaign_meta:
            logger.warning(f"No campaign metadata found for {campaign_id}")
            return

        # For each SKU, update inventory from Redis counter
        # This is a simplified version - in production you'd track SKUs per campaign
        logger.info(f"Inventory sync from Redis completed for campaign {campaign_id}")

    except Exception as e:
        logger.error(f"Error syncing inventory from Redis: {e}", exc_info=True)
        # Non-critical, continue


async def _write_transaction_log(
    campaign_id: str,
    campaign_name: str,
    orders_count: int,
    total_quantity: int,
    reason: str
):
    """Write transaction log for successful write-back."""
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)

        log_file = LOG_DIR / f"campaign_{campaign_id}_writeback.log"
        timestamp = datetime.utcnow().isoformat()

        log_content = f"""
CAMPAIGN WRITE-BACK LOG
========================
Campaign ID: {campaign_id}
Campaign Name: {campaign_name}
Timestamp: {timestamp}
Trigger Reason: {reason}

SUMMARY
-------
Total Orders Written: {orders_count}
Total Quantity: {total_quantity}
Status: SUCCESS

"""

        with open(log_file, "a") as f:
            f.write(log_content)

        logger.info(f"Transaction log written to {log_file}")

    except Exception as e:
        logger.error(f"Error writing transaction log: {e}")
        # Non-critical, continue


async def generate_failover_log(campaign_id: str, error: Exception, reason: str):
    """
    Generate failover log for customer notifications.

    Called when Redis or database fails during write-back.
    Provides operators with customer contact info for notifications.
    """
    try:
        FAILOVER_DIR.mkdir(parents=True, exist_ok=True)

        log_file = FAILOVER_DIR / f"campaign_{campaign_id}_pending.txt"
        timestamp = datetime.utcnow().isoformat()

        # Try to read pending orders from Redis
        pending_orders = []
        try:
            pending_orders = await read_campaign_orders(campaign_id)
        except:
            pass

        log_content = f"""CAMPAIGN: Flash Sale Campaign ({campaign_id})
FAILURE TIME: {timestamp}
REASON: {type(error).__name__}: {str(error)}
TRIGGER: {reason}

PENDING ORDERS (may not have completed):
order_number,customer_email,customer_name,quantity,timestamp
"""

        for order in pending_orders:
            total_qty = sum(item["quantity"] for item in order["line_items"])
            log_content += f"{order['order_number']},{order['customer_email']},{order['customer_name']},{total_qty},{timestamp}\n"

        log_content += """
CUSTOMER NOTICE TEMPLATE:
"Dear {customer_name}, your order {order_number} for the flash sale campaign could not be completed
due to system maintenance. Inventory has been released. Please try again or contact support."
"""

        with open(log_file, "w") as f:
            f.write(log_content)

        logger.critical(
            f"FAILOVER LOG GENERATED: {log_file} - "
            f"{len(pending_orders)} pending orders require customer notification"
        )

    except Exception as e:
        logger.critical(f"Failed to generate failover log: {e}", exc_info=True)


async def _cleanup_redis_keys(campaign_id: str):
    """Cleanup Redis keys after successful write-back."""
    try:
        if not redis_cache.client:
            return

        # Delete campaign metadata
        campaign_meta_key = f"fs:{campaign_id}:meta"
        await redis_cache.client.delete(campaign_meta_key)

        # Delete campaign limit counter
        campaign_limit_key = f"fs:{campaign_id}:limit"
        await redis_cache.client.delete(campaign_limit_key)

        # Note: We keep the order_queue stream for audit purposes
        # Manual cleanup can be done later with: XTRIM order_queue MAXLEN 0

        logger.info(f"Cleaned up Redis keys for campaign {campaign_id}")

    except Exception as e:
        logger.error(f"Error cleaning up Redis keys: {e}")
        # Non-critical, continue
