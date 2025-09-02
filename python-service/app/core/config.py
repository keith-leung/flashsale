"""Application configuration."""

import os
from typing import Optional

from pydantic import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # Database
    database_url: str = "mysql+aiomysql://flashsale_user:flashsale_password@localhost:3306/flashsale_db"
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    
    # Application
    debug: bool = False
    secret_key: str = "change-me-in-production"
    
    # Celery
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/1"
    
    class Config:
        env_file = ".env"


settings = Settings()
