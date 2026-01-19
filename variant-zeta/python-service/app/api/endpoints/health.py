"""Health check endpoint."""

from fastapi import APIRouter


router = APIRouter()


@router.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "variant": "zeta"}


@router.head("/health")
async def health_head():
    """Health check endpoint (HEAD method)."""
    return {"status": "healthy", "variant": "zeta"}
