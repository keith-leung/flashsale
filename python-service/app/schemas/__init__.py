"""Pydantic schemas for API serialization."""

from .spu import SPUCreate, SPUUpdate, SPUResponse
from .sku import SKUCreate, SKUUpdate, SKUResponse
from .flash_sale import FlashSaleEventCreate, FlashSaleEventUpdate, FlashSaleEventResponse
from .inventory import InventoryUpdate, InventoryResponse

__all__ = [
    "SPUCreate", "SPUUpdate", "SPUResponse",
    "SKUCreate", "SKUUpdate", "SKUResponse", 
    "FlashSaleEventCreate", "FlashSaleEventUpdate", "FlashSaleEventResponse",
    "InventoryUpdate", "InventoryResponse"
]
