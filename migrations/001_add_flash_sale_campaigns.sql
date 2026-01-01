-- Migration: Add Flash Sale Campaigns (SPU-Level)
-- Updated to match Python FlashSaleCampaign model
-- Date: 2025-12-31

USE orange315;

-- ============================================================
-- Step 1: Create flash_sale_campaigns table
-- ============================================================

CREATE TABLE flash_sale_campaigns (
    id CHAR(36) NOT NULL PRIMARY KEY,
    name VARCHAR(250) NOT NULL,
    description TEXT,
    spu_id CHAR(36) NOT NULL,
    
    -- Sale constraints
    total_sale_limit INT NOT NULL,
    sold_quantity INT NOT NULL DEFAULT 0,
    max_quantity_per_customer INT NOT NULL DEFAULT 1,
    
    -- Time constraints
    start_time DATETIME NOT NULL,
    end_time DATETIME NOT NULL,
    
    -- Status
    status ENUM('scheduled', 'active', 'ended', 'cancelled') NOT NULL DEFAULT 'scheduled',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    
    -- Timestamps
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (spu_id) REFERENCES spus(id),
    INDEX idx_fsc_spu (spu_id),
    INDEX idx_fsc_status (status),
    INDEX idx_fsc_times (start_time, end_time)
) ENGINE=InnoDB;

-- ============================================================
-- Step 2: Modify orders table
-- ============================================================

-- Rename flash_sale_id to flash_sale_campaign_id if it exists, or add it
-- First check if we need to drop old FK
-- ALTER TABLE orders DROP FOREIGN KEY orders_ibfk_1; -- Only if it exists

-- Rename column (MariaDB 10.5+)
ALTER TABLE orders CHANGE COLUMN flash_sale_id flash_sale_campaign_id CHAR(36) DEFAULT NULL;

-- Add FK to new table
ALTER TABLE orders ADD CONSTRAINT fk_orders_flash_sale_campaign 
    FOREIGN KEY (flash_sale_campaign_id) REFERENCES flash_sale_campaigns(id) ON DELETE SET NULL;

CREATE INDEX idx_order_flash_sale_campaign ON orders(flash_sale_campaign_id);