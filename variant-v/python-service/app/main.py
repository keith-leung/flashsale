"""Main FastAPI application for Variant V."""

import logging
from contextlib import asynccontextmanager
import time

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import PlainTextResponse, JSONResponse

from starlette.responses import PlainTextResponse, JSONResponse

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting Flash Sale Service (Variant V - Campaign-Aware Distributed Locking)")
    yield
    logger.info("Shutting down Flash Sale Service")


app = FastAPI(
    title="Flash Sale Microservice - Variant V",
    description="Campaign-Aware Distributed Locking + Write-Ahead Audit",
    version="1.0.0",
    lifespan=lifespan,
)

# Import and include API routes
from .api.router import api_router
app.include_router(api_router, prefix="/api/v1")

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

@app.get("/health")
@app.head("/health")
async def health_check():
    """Health check endpoint for load balancer.

    Returns plain text '200 OK' following BoA internal pattern.
    Supports both GET and HEAD methods.
    """
    return PlainTextResponse("200 OK", status_code=200)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
