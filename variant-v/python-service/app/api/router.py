from fastapi import APIRouter
from .routes.orders import router as orders_router

api_router = APIRouter()

# Include orders router with prefix and tags
api_router.include_router(
    orders_router, 
    prefix="/orders", 
    tags=["orders"]
)
