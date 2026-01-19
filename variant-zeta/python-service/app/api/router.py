"""API router - Variant Zeta (Redis-First)."""

from fastapi import APIRouter
from app.api.endpoints.orders import router as orders_router

api_router = APIRouter()

# Include orders router
api_router.include_router(orders_router, prefix="/orders", tags=["orders"])
