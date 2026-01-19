"""API router for Variant Z."""

from fastapi import APIRouter

from app.api.endpoints.orders import router as orders_router

# Main API router
api_router = APIRouter()

# Include sub-routers
api_router.include_router(orders_router, prefix="/orders", tags=["orders"])