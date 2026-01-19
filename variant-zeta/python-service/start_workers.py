"""Background workers startup script - Variant Zeta."""

import asyncio
import signal
import sys
import logging

from app.workers.order_persistence_worker import run_background_workers
from app.core.config import settings

logger = logging.getLogger(__name__)


def signal_handler(sig, frame):
    """Handle shutdown signals."""
    logger.info("Shutdown signal received")
    sys.exit(0)


if __name__ == '__main__':
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO if not settings.debug else logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger("=" * 80)
    logger("Starting Variant Zeta - Background Workers (Redis-First)")
    logger("=" * 80)
    
    # Run background workers
    asyncio.run(run_background_workers())
