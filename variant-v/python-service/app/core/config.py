# Configuration management for Variant V Flash Sale Service

import os
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    # Database configuration
    database_url: str = "mysql://syracuse:Orange_315_Forever!@10.92.0.2:3306/orange315"
    
    # Redis node configuration (3-node cluster)
    redis_node1_url: str = "redis://10.92.0.3:6379"
    redis_node2_url: str = "redis://10.92.0.4:6379"
    redis_node3_url: str = "redis://10.92.0.5:6379"
    
    # Audit configuration
    audit_table: str = "audit_order_log"
    
    # Application configuration
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    
    # Lock configuration
    default_lock_ttl_ms: int = 100  # 100ms lock TTL (order processing is fast)
    lock_retry_count: int = 5
    
    # Batch processing
    batch_size: int = 1000
    batch_interval_seconds: int = 5
    
    # Environment
    environment: str = "production"
    debug: bool = False
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# Global settings instance
settings = Settings()
