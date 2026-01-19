"""Startup script for Variant Zeta - Redis-First Architecture - FIXED."""

import os
import sys
import asyncio
import signal
import logging

logger = logging.getLogger(__name__)


async def start_api():
    """Start FastAPI workers."""
    print("=" * 80)
    print("Starting Variant Zeta - Redis-First Architecture (API Workers)")
    print("=" * 80)
    print("Features:")
    print("  - 16 FastAPI workers")
    print("  - Redis connection pooling (500 max connections)")
    print("  - Atomic Lua script inventory reservation")
    print("  - Zero database reads during flash sale")
    print("  - FIXED: SPU campaign limit enforcement")
    print("  - FIXED: Database inventory decrements")
    print("  - FIXED: Cache synchronization (write-through)")
    print("  - FIXED: Design schema format (campaign:{spu_id}, sku:{id}:metadata, sku:{id}:stock)")
    print("=" * 80)
    
    # Import after logging is configured
    import uvicorn
    from app.main import app
    from app.core.config import settings
    
    # Start uvicorn
    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=8000,
        workers=16,
        loop="uvloop",
        http="httptools",
        access_log=True
    )
    server = uvicorn.Server(config)
    await server.serve()


async def start_workers():
    """Start background workers."""
    print("=" * 80)
    print("Starting Variant Zeta - Redis-First Architecture (Background Workers)")
    print("=" * 80)
    print("Features:")
    print("  - 5 background workers")
    print("  - Batch persistence (1000 orders/transaction)")
    print("  - FIXED: Database inventory decrements")
    print("  - FIXED: Campaign sold_quantity updates")
    print("  - FIXED: Cache synchronization (write-through)")
    print("  - FIXED: Worker method names (start())")
    print("=" * 80)
    
    # Import worker module
    from app.workers.order_persistence_worker import run_background_workers
    
    # Run workers
    await run_background_workers()


def signal_handler(sig, frame):
    """Handle shutdown signals."""
    print("Shutdown signal received")
    sys.exit(0)


if __name__ == '__main__':
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Determine mode from environment
    mode = os.environ.get('START_MODE', 'api')
    
    try:
        if mode == 'api':
            asyncio.run(start_api())
        elif mode == 'workers':
            asyncio.run(start_workers())
        else:
            print(f"Unknown START_MODE: {mode}")
            sys.exit(1)
    except Exception as e:
        print(f"Failed to start: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
