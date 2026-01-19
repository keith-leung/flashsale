"""Order persistence worker - Variant Zeta (Redis-First)."""

import asyncio
import json
import logging
import uuid
from typing import Dict, Any
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, AsyncSessionLocal
from app.core.redis_pool import get_redis
from app.models.order import Order, OrderLineItem, Payment
from app.models.sku import SKU
from app.models.inventory import Inventory
from app.models.flash_sale import FlashSaleCampaign
from app.core.config import settings

logger = logging.getLogger(__name__)


class OrderPersistenceWorker:
    """Background worker for persisting orders to database."""
    
    def __init__(self, worker_id: int):
        self.worker_id = worker_id
        self.batch_size = getattr(settings, 'batch_size', 1000)
        self.running = False
    
    async def process_order(self, db: AsyncSession, order_data: Dict[str, Any]):
        """Persist a single order to database with correct inventory updates."""
        order_id = order_data['order_id']
        
        # Parse line items
        line_items = json.loads(order_data['line_items'])
        line_item = line_items[0]
        sku_id = line_item['sku_id']
        quantity = line_item['quantity']
        
        # Get SKU
        result = await db.execute(
            select(SKU).where(SKU.id == sku_id)
        )
        sku = result.scalar_one_or_none()
        
        if not sku:
            logger.error(f"SKU {sku_id} not found")
            return False
        
        # Get campaign (if exists)
        campaign = None
        if 'spu_id' in order_data:
            result = await db.execute(
                select(FlashSaleCampaign).where(
                    FlashSaleCampaign.spu_id == order_data['spu_id']
                )
            )
            campaign = result.scalar_one_or_none()
        
        # Create order
        order = Order(
            id=order_id,
            order_number=order_data['order_number'],
            customer_email=order_data['customer_email'],
            customer_name=order_data['customer_name'],
            subtotal=float(order_data['subtotal']),
            tax_amount=float(order_data['tax_amount']),
            shipping_amount=float(order_data['shipping_amount']),
            total_amount=float(order_data['total_amount']),
            currency='USD',
            status='persisted',
            flash_sale_campaign_id=campaign.id if campaign else None
        )
        db.add(order)
        
        # Create line item
        line_item = OrderLineItem(
            id=str(uuid.uuid4()),
            order_id=order_id,
            sku_id=sku_id,
            quantity=quantity,
            unit_price=float(sku.price),
            total_price=float(sku.price) * quantity,
            product_name=sku.name,
            sku_code=sku.sku_code
        )
        db.add(line_item)
        
        # Create payment
        payment = Payment(
            id=str(uuid.uuid4()),
            order_id=order_id,
            amount=float(order_data['total_amount']),
            currency='USD',
            payment_method='flash_sale',
            gateway_transaction_id=order_data.get('transaction_id', ''),
            gateway_response='',
            status='authorized'
        )
        db.add(payment)
        
        # FIXED: Update campaign sold_quantity
        if campaign:
            await db.execute(
                update(FlashSaleCampaign)
                .where(FlashSaleCampaign.id == campaign.id)
                .values(sold_quantity=FlashSaleCampaign.sold_quantity + quantity)
            )
        
        # FIXED: Update inventory (convert reserved to sold)
        await db.execute(
            update(Inventory)
            .where(Inventory.sku_id == sku_id)
            .values(
                quantity=Inventory.quantity - quantity,
                reserved_quantity=Inventory.reserved_quantity - quantity
            )
        )
        
        logger.info(f"Worker {self.worker_id}: Persisted order {order_id}")
        return True
    
    async def start(self):
        """Worker loop - pulls orders from Redis queue and persists to DB."""
        self.running = True
        logger.info(f"Worker {self.worker_id} started (batch_size={self.batch_size})")
        
        redis = await get_redis()
        batch = []
        
        while self.running:
            try:
                # Blocking pop from queue
                result = await redis.brpop('orders_queue', timeout=5)
                
                if not result:
                    # No orders, flush batch if any
                    if batch:
                        await self.flush_batch(batch)
                        batch = []
                    continue
                
                _, order_id = result
                
                # Get order data from Redis
                order_data = await redis.hgetall(f'order:{order_id}')
                
                if not order_data:
                    logger.error(f"Order {order_id} not found in Redis")
                    continue
                
                # Add to batch
                batch.append(order_data)
                
                # Flush batch if size reached
                if len(batch) >= self.batch_size:
                    await self.flush_batch(batch)
                    batch = []
                
            except Exception as e:
                logger.error(f"Worker {self.worker_id} error: {e}")
                await asyncio.sleep(1)
        
        # Flush remaining batch on shutdown
        if batch:
            await self.flush_batch(batch)
        
        await redis.aclose()
    
    async def flush_batch(self, batch: list[Dict[str, Any]]):
        """Persist a batch of orders to database."""
        if not batch:
            return
        
        async with AsyncSessionLocal() as db:
            try:
                # Persist all orders in batch
                for order_data in batch:
                    await self.process_order(db, order_data)
                
                await db.commit()
                logger.info(f"Worker {self.worker_id}: Persisted batch of {len(batch)} orders")
                
            except Exception as e:
                await db.rollback()
                logger.error(f"Worker {self.worker_id}: Batch persistence failed: {e}")
                # Re-add to queue for retry
                redis = await get_redis()
                for order_data in batch:
                    await redis.lpush('orders_queue', order_data['order_id'])
                await redis.aclose()
    
    def stop(self):
        """Stop the worker."""
        self.running = False
        logger.info(f"Worker {self.worker_id} stopped")


async def run_worker(worker_id: int):
    """Run a single background worker."""
    worker = OrderPersistenceWorker(worker_id)
    await worker.start()


async def run_background_workers():
    """Run all background workers."""
    worker_count = getattr(settings, 'worker_count', 5)
    
    logger.info(f"Starting {worker_count} background workers...")
    
    workers = []
    for worker_id in range(worker_count):
        task = asyncio.create_task(run_worker(worker_id))
        workers.append(task)
    
    # Wait for all workers
    await asyncio.gather(*workers)


if __name__ == '__main__':
    asyncio.run(run_background_workers())
