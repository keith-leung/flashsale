"""Main FastAPI application."""

import asyncio
import logging
from contextlib import asynccontextmanager
import time

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

from app.api.router import api_router
from app.core.logging import setup_logging

# Setup structured logging
setup_logging()
logger = logging.getLogger(__name__)

# Global task holder
background_task = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global background_task

    # Startup
    logger.info("Starting Flash Sale Service", extra={"service": "flash-sale-python"})

    # Connect to Redis
    from app.core.redis_cache import redis_cache
    await redis_cache.connect()
    logger.info("Redis connection established")

    # Start campaign monitor background task
    from app.tasks.campaign_monitor import campaign_monitor_task
    background_task = asyncio.create_task(campaign_monitor_task())
    logger.info("Campaign monitor background task started")

    yield

    # Shutdown
    logger.info("Shutting down Flash Sale Service", extra={"service": "flash-sale-python"})

    # Close Redis connection
    await redis_cache.close()

    # Cancel background task
    if background_task:
        background_task.cancel()
        try:
            await background_task
        except asyncio.CancelledError:
            logger.info("Campaign monitor task cancelled")

    logger.info("Shutdown complete")


app = FastAPI(
    title="Flash Sale Microservice",
    description="A high-performance flash sale service inspired by Saleor",
    version="1.0.0",
    lifespan=lifespan,
)

# Exception handler for HTTPException
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    # Try to get request body for context
    request_body = None
    try:
        body_bytes = await request.body()
        if body_bytes:
            import json
            request_body = json.loads(body_bytes.decode())
    except:
        pass

    logger.error(
        f"Unhandled exception [{type(exc).__name__}]: {exc}",
        extra={
            "method": request.method,
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "request_body": request_body,
            "error_type": type(exc).__name__,
            "error_message": str(exc),
            "error_reason": f"Internal server error: {type(exc).__name__}",
        },
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error"},
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    # Try to get request body for context
    request_body = None
    try:
        body_bytes = await request.body()
        if body_bytes:
            import json
            request_body = json.loads(body_bytes.decode())
    except:
        pass

    logger.error(
        f"HTTP Exception [{exc.status_code}]: {exc.detail}",
        extra={
            "method": request.method,
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "request_body": request_body,
            "status_code": exc.status_code,
            "error_detail": exc.detail,
            "error_reason": f"HTTP {exc.status_code}",
            "error_type": "HTTPException",
        },
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

# Middleware to log requests with input/output
@app.middleware("http")
async def log_requests(request: Request, call_next):
    import uuid
    import json
    start_time = time.time()
    request_id = str(uuid.uuid4())[:8]

    # Read request body for logging (skip for /health to minimize overhead)
    request_body = None
    if request.method in ["POST", "PUT", "PATCH"] and request.url.path != "/health":
        try:
            body_bytes = await request.body()
            if body_bytes:
                request_body = json.loads(body_bytes.decode())
            # Re-create request with body for downstream
            async def receive():
                return {"type": "http.request", "body": body_bytes}
            request._receive = receive
        except:
            request_body = "<unable to parse>"

    # Log request with input (skip detailed logging for /health)
    if request.url.path != "/health":
        logger.info(
            f"[{request_id}] REQUEST: {request.method} {request.url.path}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "query_params": dict(request.query_params),
                "request_body": request_body,
                "client_ip": request.client.host if request.client else None,
            },
        )

    try:
        response = await call_next(request)
        duration = time.time() - start_time

        # Try to read response body for logging (skip for /health to avoid overhead)
        response_body = None
        if response.status_code in [200, 201] and request.url.path != "/health":
            try:
                body_bytes = b""
                async for chunk in response.body_iterator:
                    body_bytes += chunk
                if body_bytes:
                    response_body = json.loads(body_bytes.decode())
                # Re-create response with body
                from starlette.responses import Response
                response = Response(
                    content=body_bytes,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type=response.media_type
                )
            except:
                response_body = "<unable to parse>"

        # Log response with output (skip for /health)
        if request.url.path != "/health":
            logger.info(
                f"[{request_id}] RESPONSE: {response.status_code} ({duration:.4f}s)",
                extra={
                    "request_id": request_id,
                    "status_code": response.status_code,
                    "duration_sec": round(duration, 4),
                    "response_body": response_body,
                },
            )
        return response
    except Exception as e:
        duration = time.time() - start_time
        logger.error(
            f"[{request_id}] EXCEPTION: {type(e).__name__}: {str(e)}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "error_type": type(e).__name__,
                "error_message": str(e),
                "request_body": request_body,
                "duration_sec": round(duration, 4),
            },
            exc_info=True
        )
        raise

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure based on your needs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root(request: Request):
    """Root endpoint."""
    return {"message": "Flash Sale Microservice API", "version": "1.0.0"}


@app.get("/health")
@app.head("/health")
async def health_check():
    """Health check endpoint for load balancer.

    Returns plain text '200 OK' following BoA internal pattern.
    Supports both GET and HEAD methods.
    """
    from starlette.responses import PlainTextResponse
    return PlainTextResponse("200 OK", status_code=200)
