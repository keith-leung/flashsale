"""Application configuration."""

import os
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""
    
    model_config = SettingsConfigDict(env_file=".env")
    
    # Database
    database_url: str = "mysql+aiomysql://syracuse:Orange_315_Forever!@127.0.0.1:3306/orange315"

    # Redis (defined but not used in baseline)
    redis_url: str = "redis://127.0.0.1:6380/0"

    # Application
    debug: bool = False
    secret_key: str = "change-me-in-production"

    # Celery (defined but not used in baseline)
    celery_broker_url: str = "redis://127.0.0.1:6380/1"
    celery_result_backend: str = "redis://127.0.0.1:6380/1"


settings = Settings()
