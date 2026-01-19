#!/usr/bin/env python3
"""Startup script for Variant Zeta - Single worker mode (for testing)."""

import asyncio
import sys
import signal
from app.workers.order_persistence_worker import OrderPersistenceWorker
from app.core.config import settings

logger = print


async def run_background_workers():
    """Run background workers."""
    logger("=" * 80)
    logger("Starting Variant Zeta Background Workers")
    logger("=" * 80)
    
    # Get settings with defaults
    worker_count = getattr(settings, 'worker_count', 5)
    batch_size = getattr(settings, 'batch_size', 1000)
    
    logger(f"Background Workers: {worker_count}")
    logger(f"Batch Size: {batch_size}")
    logger("=" * 80)
    
    # Spawn workers
    worker_instances = []
    
    for worker_id in range(worker_count):
        worker = OrderPersistenceWorker(worker_id)
        worker_instances.append(worker)
        logger(f"✓ Worker {worker_id} initialized (batch size: {batch_size})")
    
    logger("=" * 80)
    logger("Starting background workers...")
    logger("=" * 80)
    
    # Start all workers
    worker_tasks = []
    for worker in worker_instances:
        task = asyncio.create_task(worker.start())
        worker_tasks.append(task)
    
    # Wait for workers to start
    await asyncio.sleep(2)
    logger("✓ All background workers started and operational")
    logger("=" * 80)
    
    # Signal handler
    def signal_handler(sig, frame):
        logger("Shutdown signal received")
        for worker in worker_instances:
            asyncio.create_task(worker.stop())
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Keep workers running
    try:
        await asyncio.gather(*worker_tasks)
    except asyncio.CancelledError:
        logger("Workers shutdown")
        for worker in worker_instances:
            await worker.stop()


async def run_api_server():
    """Run FastAPI server (single worker)."""
    import uvicorn
    from app.main import app
    
    logger("=" * 80)
    logger("Starting FastAPI Server (single worker)")
    logger("=" * 80)
    
    # Run with single worker (no workers flag)
    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=8000,
        workers=1,  # Single worker to avoid routing issues
        log_level="info"
    )
    server = uvicorn.Server(config)
    
    await server.serve()


async def main():
    """Run both workers and API concurrently."""
    # Start both in parallel
    worker_task = asyncio.create_task(run_background_workers())
    api_task = asyncio.create_task(run_api_server())
    
    # Wait for both (will run forever)
    await asyncio.gather(worker_task, api_task)


if __name__ == "__main__":
    asyncio.run(main())
