"""Background worker for order persistence using Redis Streams (WAL pattern)."""

import asyncio
import logging
import random
import time
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import async_session_maker
from app.core.redis import redis_client
from app.models.sku import SKU
from app.models.inventory import Inventory
from app.models.flash_sale import FlashSaleCampaign
from app.models.order import Order
from app.models.order_line_item import OrderLineItem
from app.models.payment import Payment

logger = logging.getLogger(__name__)

# Configuration
STREAM_KEY = "orders_stream"
CONSUMER_GROUP = "order_persisters"
BATCH_SIZE = 100
READ_TIMEOUT_MS = 5000  # 5 seconds
POLL_INTERVAL = 1  # seconds


class OrderPersistenceWorker:
    """Background worker that consumes orders from Redis Stream and persists to database."""
    
    def __init__(self):
        self.running = False
        self.consumer_name = f"worker-{self._get_hostname()}"
        self.processed_count = 0
        self.failed_count = 0
        self.last_stream_id = "0"
        
    def _get_hostname(self) -> str:
        """Get hostname for consumer identification."""
        import socket
        try:
            return socket.gethostname()[:20]  # Truncate for brevity
        except:
            return f"worker-{random.randint(1000, 9999)}"
    
    async def start(self):
        """Start the background worker."""
        if self.running:
            logger.warning("Worker already running")
            return
        
        self.running = True
        logger.info(f"Starting order persistence worker: {self.consumer_name}")
        
        # Ensure Redis is connected
        await redis_client._ensure_connected()
        
        # Create consumer group if it doesn't exist
        await self._ensure_consumer_group()
        
        # Start the worker loop
        asyncio.create_task(self._worker_loop())
    
    async def stop(self):
        """Stop the background worker gracefully."""
        logger.info("Stopping order persistence worker...")
        self.running = False
        
        # Give the worker loop time to finish
        await asyncio.sleep(2)
        
        logger.info(
            f"Worker stopped. Processed: {self.processed_count}, Failed: {self.failed_count}"
        )
    
    async def _ensure_consumer_group(self):
        """Ensure consumer group exists for the stream."""
        try:
            # Try to create consumer group (XGROUP CREATE)
            await redis_client.client.execute_command(
                "XGROUP",
                "CREATE",
                STREAM_KEY,
                CONSUMER_GROUP,
                "0",
                "MKSTREAM"
            )
            logger.info(f"Created consumer group: {CONSUMER_GROUP}")
        except Exception as e:
            # Group might already exist, which is fine
            if "BUSYGROUP" in str(e) or "already exists" in str(e).lower():
                logger.debug(f"Consumer group {CONSUMER_GROUP} already exists")
            else:
                logger.error(f"Error creating consumer group: {e}")
    
    async def _worker_loop(self):
        """Main worker loop that reads and processes orders from the stream."""
        logger.info("Worker loop started")
        
        while self.running:
            try:
                # Read messages from stream using consumer group
                messages = await self._read_messages()
                
                if messages:
                    # Process messages in batch
                    await self._process_batch(messages)
                else:
                    # No messages, sleep briefly
                    await asyncio.sleep(POLL_INTERVAL)
                    
            except Exception as e:
                logger.error(f"Error in worker loop: {e}", exc_info=True)
                await asyncio.sleep(5)  # Backoff on error
    
    async def _read_messages(self) -> list:
        """
        Read messages from Redis Stream using XREADGROUP.
        
        Returns:
            List of (stream_name, message_id, fields) tuples
        """
        try:
            # Read new messages (count >)
            result = await redis_client.client.xreadgroup(
                groupname=CONSUMER_GROUP,
                consumername=self.consumer_name,
                streams={STREAM_KEY: ">"},
                count=BATCH_SIZE,
                block=READ_TIMEOUT_MS
            )
            
            # Parse result: [(stream_name, [(message_id, {fields}), ...])]
            messages = []
            if result:
                for stream_name, stream_messages in result:
                    for message_id, fields in stream_messages:
                        messages.append((stream_name, message_id, fields))
            
            return messages
            
        except Exception as e:
            logger.error(f"Error reading from stream: {e}")
            return []
    
    async def _process_batch(self, messages: list):
        """
        Process a batch of order messages.
        
        Args:
            messages: List of (stream_name, message_id, fields) tuples
        """
        if not messages:
            return
        
        logger.info(f"Processing batch of {len(messages)} orders")
        
        # Create database session for batch processing
        async with async_session_maker() as db:
            try:
                # Process each order in the batch
                for stream_name, message_id, fields in messages:
                    try:
                        await self._persist_order(db, fields, message_id)
                        self.processed_count += 1
                    except Exception as e:
                        logger.error(f"Error processing order {message_id}: {e}")
                        self.failed_count += 1
                        # Continue processing other orders in batch
                
                # Commit transaction
                await db.commit()
                
                # Acknowledge all processed messages
                for stream_name, message_id, _ in messages:
                    try:
                        await redis_client.client.xack(
                            STREAM_KEY,
                            CONSUMER_GROUP,
                            message_id
                        )
                    except Exception as e:
                        logger.error(f"Error acknowledging message {message_id}: {e}")
                
                logger.info(
                    f"Batch processed: {len(messages)} orders, "
                    f"stream length: {await redis_client.client.xlen(STREAM_KEY)}"
                )
                
            except Exception as e:
                await db.rollback()
                logger.error(f"Error in batch processing transaction: {e}", exc_info=True)
    
    async def _persist_order(
        self,
        db: AsyncSession,
        fields: dict,
        message_id: str
    ):
        """
        Persist a single order to the database.
        
        Args:
            db: Database session
            fields: Order data from Redis Stream
            message_id: Redis Stream message ID
        """
        # Parse order data
        order_id = fields.get("order_id")
        order_number = fields.get("order_number")
        customer_email = fields.get("customer_email")
        customer_name = fields.get("customer_name")
        sku_id = fields.get("sku_id")
        quantity = int(fields.get("quantity", "1"))
        unit_price = float(fields.get("unit_price", "0"))
        campaign_id = fields.get("campaign_id")
        timestamp = fields.get("timestamp")
        
        # Check if order already exists (idempotency)
        existing_order = await db.execute(
            select(Order).where(Order.id == order_id)
        )
        if existing_order.scalar_one_or_none():
            logger.debug(f"Order {order_id} already exists, skipping")
            return
        
        # Calculate totals
        subtotal = quantity * unit_price
        total_amount = subtotal  # No tax/shipping for flash sales
        
        # Create order
        order = Order(
            id=order_id,
            order_number=order_number,
            customer_email=customer_email,
            customer_name=customer_name,
            subtotal=subtotal,
            tax_amount=0.0,
            shipping_amount=0.0,
            total_amount=total_amount,
            currency="USD",
            status="pending",
            flash_sale_campaign_id=campaign_id if campaign_id != "None" else None
        )
        
        db.add(order)
        
        # Get SKU details
        sku_result = await db.execute(select(SKU).where(SKU.id == sku_id))
        sku = sku_result.scalar_one_or_none()
        
        if not sku:
            raise ValueError(f"SKU {sku_id} not found")
        
        # Create order line item
        line_item = OrderLineItem(
            id=str(uuid.uuid4()),
            order_id=order_id,
            sku_id=sku_id,
            quantity=quantity,
            unit_price=unit_price,
            total_price=subtotal,
            product_name=sku.name,
            sku_code=sku.sku_code
        )
        
        db.add(line_item)
        
        # Create payment record
        payment = Payment(
            id=str(uuid.uuid4()),
            order_id=order_id,
            amount=total_amount,
            currency="USD",
            payment_method="flash_sale",
            gateway_transaction_id=f"TXN-{int(time.time_ns() // 1_000_000)}",
            gateway_response="",
            status="authorized"
        )
        
        db.add(payment)
        
        # Update inventory
        inventory_result = await db.execute(
            select(Inventory).where(Inventory.sku_id == sku_id)
        )
        inventory = inventory_result.scalar_one_or_none()
        
        if inventory:
            inventory.quantity -= quantity
            inventory.reserved_quantity += quantity
        
        # Update campaign sold quantity (if flash sale)
        if campaign_id and campaign_id != "None":
            campaign_result = await db.execute(
                select(FlashSaleCampaign).where(FlashSaleCampaign.id == campaign_id)
            )
            campaign = campaign_result.scalar_one_or_none()
            
            if campaign:
                campaign.sold_quantity += quantity
                campaign.updated_at = datetime.utcnow()
        
        logger.debug(f"Persisted order {order_id} from stream message {message_id}")


# Global worker instance
order_persistence_worker = OrderPersistenceWorker()