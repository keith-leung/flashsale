-- Migration: Add Flash Sale Campaigns (SPU-Level)
-- Date: 2025-12-28
-- Purpose: Add support for flash sale campaigns at SPU level with dual inventory validation
--
-- This migration adds a new `flash_sale_campaigns` table for SPU-level campaigns (Variant X)
-- The existing `flash_sale_events` table (SKU-level) remains unchanged for backward compatibility
-- CRITICAL: Must match SACRED VERIFICATION schema from variant Y

USE orange315;

-- ============================================================
-- Step 1: Modify orders table to support new flash_sale_campaigns
-- ============================================================

-- Drop existing foreign key constraint to flash_sale_events
ALTER TABLE orders DROP FOREIGN KEY orders_ibfk_1;

-- flash_sale_id is now a generic reference (no FK constraint)
-- Application logic determines which table it references
-- (Note: In production, you might want a polymorphic association or separate columns)

-- ============================================================
-- Step 2: Create flash_sale_campaigns table (SPU-Level Campaigns)
-- CRITICAL: Must match SACRED VERIFICATION schema exactly
-- ============================================================

CREATE TABLE flash_sale_campaigns (
    id CHAR(36) NOT NULL PRIMARY KEY COMMENT 'UUID format',
    name VARCHAR(250) NOT NULL COMMENT 'Display name for the campaign',
    description TEXT COMMENT 'Campaign description',
    spu_id CHAR(36) NOT NULL COMMENT 'FK to SPU - campaign applies to ALL SKUs of this SPU',
    total_sale_limit INT NOT NULL COMMENT 'Total units available across ALL SKUs (e.g., 1000 units)',
    sold_quantity INT NOT NULL DEFAULT 0 COMMENT 'Total units sold across all SKUs',
    max_quantity_per_customer INT NOT NULL DEFAULT 1 COMMENT 'Max quantity per customer',
    flash_price DECIMAL(10,2) NOT NULL COMMENT 'Special flash sale price',
    start_time TIMESTAMP NOT NULL COMMENT 'Campaign start time',
    end_time TIMESTAMP NOT NULL COMMENT 'Campaign end time',
    status ENUM('scheduled', 'active', 'ended', 'cancelled') NOT NULL DEFAULT 'scheduled' COMMENT 'Campaign status',
    is_active BOOLEAN NOT NULL DEFAULT TRUE COMMENT 'Active flag',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (spu_id) REFERENCES spus(id) ON DELETE CASCADE,
    INDEX idx_flash_campaign_name (name),
    INDEX idx_flash_campaign_spu (spu_id),
    INDEX idx_flash_campaign_start (start_time),
    INDEX idx_flash_campaign_end (end_time),
    INDEX idx_flash_campaign_status (status),
    INDEX idx_flash_campaign_active (is_active),
    INDEX idx_flash_campaign_created (created_at)
) ENGINE=InnoDB COMMENT='Flash sale campaigns at SPU level - SACRED VERIFICATION schema';

-- ============================================================
-- Step 3: Add index on orders.flash_sale_id for performance
-- ============================================================

-- The index already exists from schema, but if not:
-- CREATE INDEX idx_order_flash_sale ON orders(flash_sale_id);

-- ============================================================
-- Rollback instructions (if needed):
-- ============================================================
-- DROP TABLE flash_sale_campaigns;
-- ALTER TABLE orders ADD FOREIGN KEY (flash_sale_id) REFERENCES flash_sale_events(id) ON DELETE SET NULL;
