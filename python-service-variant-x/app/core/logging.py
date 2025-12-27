"""Logging configuration for the application."""

import logging
import sys
import os
from pathlib import Path
from logging.handlers import TimedRotatingFileHandler, RotatingFileHandler

# Use absolute path from project root
PROJECT_ROOT = Path(__file__).parent.parent.parent
LOG_DIR = PROJECT_ROOT / "logs"
LOG_FILE = LOG_DIR / "flash-sale.log"
ERROR_LOG_FILE = LOG_DIR / "flash-sale-error.log"

def setup_logging():
    """Sets up rolling text-based logging to console and files."""
    log_level = logging.INFO
    logger = logging.getLogger()
    logger.setLevel(log_level)

    # Prevent duplicate handlers
    if logger.handlers:
        logger.handlers.clear()

    # Formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Skip file handlers during testing
    if "pytest" not in sys.modules:
        # Create logs directory if it doesn't exist
        LOG_DIR.mkdir(exist_ok=True)

        # Timed Rotating File Handler (for all logs)
        # Rotates daily, keeps 7 days of backups
        timed_handler = TimedRotatingFileHandler(
            str(LOG_FILE), when="midnight", interval=1, backupCount=7
        )
        timed_handler.setFormatter(formatter)
        logger.addHandler(timed_handler)

        # Rotating File Handler (for errors and warnings)
        # Rotates when file reaches 5MB, keeps 5 backups
        error_handler = RotatingFileHandler(
            str(ERROR_LOG_FILE), maxBytes=5 * 1024 * 1024, backupCount=5
        )
        error_handler.setLevel(logging.WARNING)
        error_handler.setFormatter(formatter)
        logger.addHandler(error_handler)

class EndpointFilter(logging.Filter):
    """
    Filter to exclude logs from specified endpoints.
    
    Example:
    uvicorn.access: INFO     127.0.0.1:36828 - "GET /health HTTP/1.1" 200 OK
    """
    
    def __init__(self, path: str):
        super().__init__()
        self.path = path
        
    def filter(self, record: logging.LogRecord) -> bool:
        # Check if "GET" and the specified path are in the log message
        return "GET" in record.getMessage() and self.path in record.getMessage()

# Exclude health check logs from uvicorn.access
logging.getLogger("uvicorn.access").addFilter(EndpointFilter(path="/health"))
logging.getLogger("uvicorn.access").addFilter(EndpointFilter(path="/"))
