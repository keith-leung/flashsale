-- Migration: Add Flash Sale Campaigns (SPU-Level)
-- Date: 2025-12-28
-- Purpose: Add support for flash sale campaigns at SPU level with dual inventory validation
--
-- This migration adds a new `flash_sales` table for SPU-level campaigns (Variant X)
-- The existing `flash_sale_events` table (SKU-level) remains unchanged for backward compatibility

USE orange315;

-- ============================================================
-- Step 1: Modify orders table to support new flash_sales
-- ============================================================

-- Drop existing foreign key constraint to flash_sale_events
ALTER TABLE orders DROP FOREIGN KEY orders_ibfk_1;

-- flash_sale_id is now a generic reference (no FK constraint)
-- Application logic determines which table it references
-- (Note: In production, you might want a polymorphic association or separate columns)

-- ============================================================
-- Step 2: Create flash_sales table (SPU-Level Campaigns)
-- ============================================================

CREATE TABLE flash_sales (
    id CHAR(36) NOT NULL PRIMARY KEY COMMENT 'UUID format',
    campaign_name VARCHAR(255) NOT NULL COMMENT 'Display name for the campaign',
    spu_id CHAR(36) NOT NULL COMMENT 'FK to SPU - campaign applies to ALL SKUs of this SPU',
    total_sale_limit INT NOT NULL COMMENT 'Total units available across ALL SKUs (e.g., 1000 units)',
    sold_count INT NOT NULL DEFAULT 0 COMMENT 'Total units sold (updated async from Redis)',
    start_time DATETIME NOT NULL COMMENT 'Campaign start time',
    end_time DATETIME NOT NULL COMMENT 'Campaign end time',
    status ENUM('pending', 'active', 'sold_out', 'ended') NOT NULL DEFAULT 'pending' COMMENT 'Campaign status',
    flash_sale_price DECIMAL(10,2) DEFAULT NULL COMMENT 'Special flash sale price (optional, NULL = use SKU price)',
    max_per_order INT NOT NULL DEFAULT 10 COMMENT 'Max quantity per order',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (spu_id) REFERENCES spus(id) ON DELETE CASCADE,
    INDEX idx_flash_sales_spu (spu_id),
    INDEX idx_flash_sales_status (status),
    INDEX idx_flash_sales_times (start_time, end_time),
    INDEX idx_flash_sales_created (created_at)
) ENGINE=InnoDB COMMENT='Flash sale campaigns at SPU level (Variant X implementation)';

-- ============================================================
-- Step 3: Add index on orders.flash_sale_id for performance
-- ============================================================

-- The index already exists from schema, but if not:
-- CREATE INDEX idx_order_flash_sale ON orders(flash_sale_id);

-- ============================================================
-- Rollback instructions (if needed):
-- ============================================================
-- DROP TABLE flash_sales;
-- ALTER TABLE orders ADD FOREIGN KEY (flash_sale_id) REFERENCES flash_sale_events(id) ON DELETE SET NULL;
