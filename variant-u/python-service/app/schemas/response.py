"""
Generic response schema for all API endpoints.
"""
from typing import TypeVar, Generic, Optional, Any
from pydantic import BaseModel

T = TypeVar('T')

class ResponseDTO(BaseModel, Generic[T]):
    """
    A generic response wrapper for API endpoints.
    """
    status: int = 200
    message: str = "Success"
    data: Optional[T] = None
