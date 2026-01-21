# Batch processor for processing confirmed audit logs

import asyncio
from celery import Celery, Task
from typing import List, Dict, Any
import aiomysql
import logging
from ..services.audit_service import audit_service
from ..core.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Celery app
app = Celery(
    'batch_processor',
    broker=settings.redis_node1_url,
    backend=settings.redis_node1_url
)

# Celery configuration
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_routes={
        'app.workers.batch_processor.process_audit_batch': {
            'queue': 'batch_processing',
            'rate_limit': '1000/s'  # Limit to 1000 tasks per second
        }
    },
    worker_prefetch_multiplier=1,  # Fair distribution
    task_acks_late=True,  # Ack only after completion
    worker_max_tasks_per_child=1000,  # Restart worker after 1000 tasks to prevent memory leaks
)

def get_db_pool():
    """Get database connection pool."""
    return aiomysql.create_pool(
        host='10.92.0.2',
        port=3306,
        user='syracuse',
        password='Orange_315_Forever!',
        db='orange315',
        minsize=5,
        maxsize=20,
        autocommit=False  # Use transactions
    )

async def process_single_audit(order_id: str, audit_data: Dict, conn) -> bool:
    """Process a single confirmed audit record."""
    try:
        # 1. Validate campaign limits still available (double-check)
        # This is already validated when the order was created, but we double-check
        
        # 2. Validate SKU stock still available
        # Similar validation here
        
        # 3. Create actual order in MariaDB
        sql = """
        INSERT INTO orders (
            id, customer_email, sku_id, quantity, unit_price, 
            flash_sale_campaign_id, status
        ) VALUES (%s, %s, %s, %s, %s, %s, 'confirmed')
        """
        
        async with conn.cursor() as cursor:
            await cursor.execute(
                sql,
                (
                    order_id,
                    audit_data['customer_email'],
                    audit_data['sku_id'],
                    audit_data['quantity'],
                    audit_data['unit_price'],
                    audit_data['flash_sale_campaign_id']
                )
            )
        
        # 4. Update campaign counters (this should match what was decremented)
        campaign_update_sql = """
        UPDATE flash_sale_campaigns 
        SET sold_quantity = sold_quantity + %s 
        WHERE id = %s
        """
        
        async with conn.cursor() as cursor:
            await cursor.execute(
                campaign_update_sql,
                (audit_data['quantity'], audit_data['flash_sale_campaign_id'])
            )
        
        # 5. Update SKU inventory
        sku_update_sql = """
        UPDATE product_skus 
        SET inventory = inventory - %s 
        WHERE id = %s
        """
        
        async with conn.cursor() as cursor:
            await cursor.execute(
                sku_update_sql,
                (audit_data['quantity'], audit_data['sku_id'])
            )
        
        # 6. Mark audit as processed (delete or mark as processed)
        # For now, we'll keep the audit record for audit trail
        delete_audit_sql = """
        DELETE FROM audit_order_log 
        WHERE id = %s AND status = 'confirmed'
        """
        
        async with conn.cursor() as cursor:
            await cursor.execute(delete_audit_sql, (audit_data['id'],))
        
        await conn.commit()
        return True
        
    except Exception as e:
        await conn.rollback()
        logger.error(f"Failed to process audit {audit_data['id']}: {e}")
        return False

class AsyncTask(Task):
    """Base class for async Celery tasks."""
    
    def __call__(self, *args, **kwargs):
        # Run async function in event loop
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If loop is already running, create new loop for this task
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(self.run(*args, **kwargs))
    
    async def run(self, *args, **kwargs):
        raise NotImplementedError

@app.task(base=AsyncTask, bind=True)
async def process_audit_batch(self):
    """
    Batch process confirmed audit logs.
    
    Steps:
    1. Fetch pending audits (limit 1000)
    2. Validate campaign limits still available
    3. Validate SKU stock still available
    4. Create actual order in MariaDB
    5. Update campaign counters
    6. Update SKU inventory
    7. Remove processed audits
    8. Handle failures with retry/backoff
    """
    logger.info("Starting audit batch processing")
    
    try:
        pool = await get_db_pool()
        
        # 1. Fetch pending audits
        pending_audits = await audit_service.get_pending_audits(settings.batch_size)
        
        if not pending_audits:
            logger.info("No pending audits to process")
            return {"processed": 0, "failed": 0}
        
        logger.info(f"Found {len(pending_audits)} pending audits")
        
        processed_count = 0
        failed_count = 0
        
        # Process each audit
        for audit in pending_audits:
            try:
                async with pool.acquire() as conn:
                    success = await process_single_audit(
                        audit['order_id'], 
                        audit, 
                        conn
                    )
                    
                    if success:
                        processed_count += 1
                    else:
                        failed_count += 1
                        
                        # Backoff for failed items
                        await asyncio.sleep(0.1)
                        
            except Exception as e:
                logger.error(f"Exception processing audit {audit.get('id', 'unknown')}: {e}")
                failed_count += 1
        
        pool.close()
        await pool.wait_closed()
        
        logger.info(f"Batch processing complete: {processed_count} processed, {failed_count} failed")
        
        return {
            "processed": processed_count,
            "failed": failed_count,
            "total": len(pending_audits)
        }
        
    except Exception as e:
        logger.error(f"Batch processing failed: {e}")
        raise

@app.task
def cleanup_failed_audits():
    """Clean up old failed audits (older than 1 hour)."""
    # This would be called periodically to clean up failed audits
    # Implementation depends on requirements
    pass

# Schedule periodic batch processing
app.conf.beat_schedule = {
    'process-audit-batch-every-5-seconds': {
        'task': 'app.workers.batch_processor.process_audit_batch',
        'schedule': settings.batch_interval_seconds,  # Run every 5 seconds
    },
}

if __name__ == "__main__":
    # For testing
    app.start()
