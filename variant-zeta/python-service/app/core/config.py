"""Configuration settings for Variant Zeta (Redis-First)."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # Database
    database_url: str = "mysql+aiomysql://syracuse:Orange_315_Forever!@mariadb:3306/orange315"
    
    # Redis
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_db: int = 0
    
    # API
    debug: bool = False
    
    # Background Workers (ADDED)
    worker_count: int = 5
    batch_size: int = 1000
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
