"""Main API router."""

from fastapi import APIRouter

from app.api.endpoints import spus, skus, inventory, orders, campaign_admin, campaign_debug

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(spus.router, prefix="/spus", tags=["SPUs"])
api_router.include_router(skus.router, prefix="/skus", tags=["SKUs"])
api_router.include_router(inventory.router, prefix="/inventory", tags=["Inventory"])
api_router.include_router(orders.router, prefix="/orders", tags=["Orders"])
api_router.include_router(campaign_admin.router, prefix="/admin", tags=["Campaign Admin"])
api_router.include_router(campaign_debug.router, prefix="/debug/campaigns", tags=["Campaign Debug"])
