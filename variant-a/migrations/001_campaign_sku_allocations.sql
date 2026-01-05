-- Migration: Campaign SKU Allocations for Variant A
-- Purpose: Pre-allocate campaign inventory to service instances
-- Design: Product Manager creates allocation units, services claim them dynamically

CREATE TABLE IF NOT EXISTS campaign_sku_allocations (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    campaign_id VARCHAR(36) NOT NULL,
    sku_id VARCHAR(36) NOT NULL,

    -- Business Configuration (Product Manager sets)
    allocated_quantity INT NOT NULL COMMENT 'Base allocation per unit (e.g., 500)',
    refill_batch_size INT NOT NULL COMMENT 'Amount to refill each time (e.g., 50)',
    low_water_mark_pct DECIMAL(5,2) NOT NULL COMMENT 'Trigger refill threshold % (e.g., 30.00)',

    -- Runtime Tracking (System manages)
    claimed_by VARCHAR(100) NULL COMMENT 'Service instance ID (e.g., csharp-pod-3)',
    claimed_at TIMESTAMP NULL,
    status ENUM('available', 'claimed', 'depleted') DEFAULT 'available',

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    INDEX idx_campaign_status (campaign_id, status),
    INDEX idx_campaign_sku (campaign_id, sku_id),
    INDEX idx_claimed_by (claimed_by)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Campaign inventory pre-allocations for adaptive batching';

-- Example: Product Manager creates 10 allocation units for campaign
-- Total stock: 5000 items split into 10 units of 500 each
-- Services will claim units based on their capacity (C#: 5, Java: 3, Python: 2)

-- For testing/benchmarking: Insert sample allocations
INSERT INTO campaign_sku_allocations
    (campaign_id, sku_id, allocated_quantity, refill_batch_size, low_water_mark_pct)
SELECT
    '750e8400-e29b-41d4-a716-446655440000',
    '650e8400-e29b-41d4-a716-446655440001',
    500,   -- allocated_quantity
    50,    -- refill_batch_size
    30.00  -- low_water_mark_pct
FROM
    (SELECT 1 AS n UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5
     UNION SELECT 6 UNION SELECT 7 UNION SELECT 8 UNION SELECT 9 UNION SELECT 10) numbers
ON DUPLICATE KEY UPDATE allocated_quantity=allocated_quantity;
