"""FastAPI application - Variant Zeta (Redis-First Architecture)."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager (Redis-First)."""
    
    # Startup
    logger.info("=" * 80)
    logger.info("Starting Variant Zeta - Redis-First Architecture")
    logger.info("=" * 80)
    logger.info("Architecture: Redis-First (No DB reads during order creation)")
    logger.info("Workers: 16 FastAPI workers + 5 background workers")
    logger.info("Key Features:")
    logger.info("  - Atomic Lua script inventory reservation")
    logger.info("  - Redis metadata caching (campaigns, SKUs)")
    logger.info("  - Async batch persistence to database")
    logger.info("  - Zero database reads during flash sale")
    logger.info("=" * 80)
    
    yield
    
    # Shutdown
    logger.info("Variant Zeta shutdown")


# Create FastAPI app
app = FastAPI(
    title="Flash Sale Microservice - Variant Zeta",
    description="Redis-First Architecture for Maximum Throughput",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "Flash Sale Microservice",
        "variant": "Zeta",
        "architecture": "Redis-First",
        "status": "operational",
        "workers": {
            "api_workers": 16,
            "background_workers": 5
        },
        "features": [
            "Redis-First architecture (zero DB reads during flash sale)",
            "Atomic Lua script inventory reservation",
            "Redis metadata caching (campaigns, SKUs)",
            "Async batch persistence to database (1000 orders/transaction)",
            "16 FastAPI workers for maximum concurrency"
        ]
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "variant": "zeta",
        "architecture": "redis-first",
        "workers": {
            "api_workers": 16,
            "background_workers": 5
        },
        "throughput_target": "> 10,000 req/s",
        "throughput_expected": "10x faster than Variant Y (1,390 req/s)"
    }


@app.head("/health")
async def health_head():
    """Health check endpoint (HEAD method)."""
    return {"status": "healthy", "variant": "zeta"}
