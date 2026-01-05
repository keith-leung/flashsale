"""
Order Logger Service for Flash Sale Variant A

Provides async logging of all order attempts with customer account info
Logs are written to local text files for audit and reconciliation
"""

import asyncio
import aiofiles
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, List


class OrderLogger:
    """
    Async order logger for audit trails

    Logs format: Structured text (pipe-delimited) for easy grep/analysis
    Log location: /var/log/flashsale/variant-a/orders_{YYYYMMDD}.log
    """

    LOG_DIR = "/var/log/flashsale/variant-a"
    BUFFER_SIZE = 100  # Number of log entries to buffer before flushing

    def __init__(self):
        """Initialize the order logger"""
        self._log_buffer: List[str] = []
        self._buffer_lock = asyncio.Lock()
        self._ensure_log_dir()

    def _ensure_log_dir(self):
        """Ensure log directory exists"""
        Path(self.LOG_DIR).mkdir(parents=True, exist_ok=True)

    def _get_log_file_path(self) -> str:
        """Get current log file path based on date"""
        date_str = datetime.now().strftime("%Y%m%d")
        return f"{self.LOG_DIR}/orders_{date_str}.log"

    async def log_order_attempt(
        self,
        order_number: str,
        customer_email: str,
        customer_name: str,
        sku_ids: List[str],
        quantities: List[int],
        campaign_id: str,
        status: str,
        mode: str,
        duration_ms: float,
        account_id: Optional[str] = None,
        error_message: Optional[str] = None
    ):
        """
        Log an order attempt (async, non-blocking)

        Args:
            order_number: Unique order number
            customer_email: Customer email address
            customer_name: Customer name
            sku_ids: List of SKU IDs in the order
            quantities: List of quantities for each SKU
            campaign_id: Flash sale campaign ID
            status: Order status (SUCCESS, FAILED, SOLD_OUT, ERROR)
            mode: Inventory mode used (BATCH, DIRECT)
            duration_ms: Order processing duration in milliseconds
            account_id: Optional customer account ID
            error_message: Optional error message for failed orders
        """
        timestamp = datetime.now().isoformat()
        sku_list = ",".join(sku_ids)
        qty_list = ",".join(str(q) for q in quantities)

        # Build log entry
        log_parts = [
            f"[{timestamp}]",
            "ORDER_ATTEMPT",
            f"order_number={order_number}",
            f"customer_email={customer_email}",
            f"customer_name={customer_name}",
            f"account_id={account_id or 'N/A'}",
            f"sku_ids=[{sku_list}]",
            f"quantities=[{qty_list}]",
            f"campaign_id={campaign_id}",
            f"status={status}",
            f"mode={mode}",
            f"duration_ms={duration_ms:.2f}"
        ]

        if error_message:
            # Sanitize error message (remove pipes and newlines)
            sanitized_error = error_message.replace("|", "/").replace("\n", " ")
            log_parts.append(f"error={sanitized_error}")

        log_entry = " | ".join(log_parts)

        # Add to buffer and flush if needed
        async with self._buffer_lock:
            self._log_buffer.append(log_entry)
            if len(self._log_buffer) >= self.BUFFER_SIZE:
                await self._flush_buffer()

    async def log_order_success(
        self,
        order_number: str,
        customer_email: str,
        customer_name: str,
        sku_ids: List[str],
        quantities: List[int],
        campaign_id: str,
        mode: str,
        duration_ms: float,
        account_id: Optional[str] = None
    ):
        """Log a successful order (convenience method)"""
        await self.log_order_attempt(
            order_number=order_number,
            customer_email=customer_email,
            customer_name=customer_name,
            sku_ids=sku_ids,
            quantities=quantities,
            campaign_id=campaign_id,
            status="SUCCESS",
            mode=mode,
            duration_ms=duration_ms,
            account_id=account_id
        )

    async def log_order_failure(
        self,
        order_number: str,
        customer_email: str,
        customer_name: str,
        sku_ids: List[str],
        quantities: List[int],
        campaign_id: str,
        mode: str,
        duration_ms: float,
        reason: str,
        account_id: Optional[str] = None
    ):
        """Log a failed order (convenience method)"""
        await self.log_order_attempt(
            order_number=order_number,
            customer_email=customer_email,
            customer_name=customer_name,
            sku_ids=sku_ids,
            quantities=quantities,
            campaign_id=campaign_id,
            status="FAILED",
            mode=mode,
            duration_ms=duration_ms,
            account_id=account_id,
            error_message=reason
        )

    async def _flush_buffer(self):
        """Flush buffered log entries to disk (async)"""
        if not self._log_buffer:
            return

        # Get entries to write and clear buffer
        entries_to_write = self._log_buffer.copy()
        self._log_buffer.clear()

        # Write to file (async)
        log_file_path = self._get_log_file_path()
        try:
            async with aiofiles.open(log_file_path, mode='a') as f:
                await f.write('\n'.join(entries_to_write) + '\n')
        except Exception as e:
            # Log to stderr if file write fails
            print(f"[ORDER_LOGGER] Failed to write to {log_file_path}: {e}", flush=True)

    async def flush(self):
        """Manually flush buffer (useful for shutdown)"""
        async with self._buffer_lock:
            await self._flush_buffer()


# Global singleton instance
_order_logger: Optional[OrderLogger] = None


def get_order_logger() -> OrderLogger:
    """Get global order logger instance (singleton)"""
    global _order_logger
    if _order_logger is None:
        _order_logger = OrderLogger()
    return _order_logger
