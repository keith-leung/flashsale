-- Variant A: Add Memory Allocation Configuration Fields
-- This migration adds fields to support adaptive 2-tier batching with memory preallocation
--
-- Strategy:
-- - Preallocate percentage of campaign items to service nodes (memory cache)
-- - Remaining percentage stays in Redis (fallback layer)
-- - Allocation distributed by service performance ratio (C#:Java:Python ≈ 20:13:1)
--
-- Database: orange315

USE orange315;

-- Add allocation configuration fields to flash_sale_campaigns table
ALTER TABLE flash_sale_campaigns
  -- Preallocation configuration
  ADD COLUMN IF NOT EXISTS preallocate_percentage DECIMAL(5,2) NOT NULL DEFAULT 60.00
    COMMENT 'Percentage of items preallocated to service nodes (0-100)',

  ADD COLUMN IF NOT EXISTS redis_percentage DECIMAL(5,2) NOT NULL DEFAULT 40.00
    COMMENT 'Percentage of items kept in Redis for fallback (0-100)',

  ADD COLUMN IF NOT EXISTS refill_lower_watermark_pct DECIMAL(5,2) NOT NULL DEFAULT 25.00
    COMMENT 'Percentage threshold to trigger async refill from Redis (0-100)',

  -- Service allocation ratios (based on /health benchmark performance)
  ADD COLUMN IF NOT EXISTS csharp_allocation_ratio INT NOT NULL DEFAULT 20
    COMMENT 'C# service allocation weight (fastest)',

  ADD COLUMN IF NOT EXISTS java_allocation_ratio INT NOT NULL DEFAULT 13
    COMMENT 'Java service allocation weight (medium)',

  ADD COLUMN IF NOT EXISTS python_allocation_ratio INT NOT NULL DEFAULT 1
    COMMENT 'Python service allocation weight (slowest)',

  -- Tracking fields
  ADD COLUMN IF NOT EXISTS preallocated_at TIMESTAMP NULL
    COMMENT 'When items were preallocated to service nodes',

  ADD COLUMN IF NOT EXISTS writeback_at TIMESTAMP NULL
    COMMENT 'When final results were written back to DB';

-- Add index for allocation queries
ALTER TABLE flash_sale_campaigns
  ADD INDEX IF NOT EXISTS idx_flash_campaign_preallocation (preallocate_percentage, status);

-- Create a view for easy allocation calculation
CREATE OR REPLACE VIEW flash_sale_campaign_allocation AS
SELECT
    c.id AS campaign_id,
    c.name AS campaign_name,
    c.total_sale_limit,
    c.sold_quantity,
    c.preallocate_percentage,
    c.redis_percentage,
    c.refill_lower_watermark_pct,

    -- Calculated preallocated amounts
    FLOOR(c.total_sale_limit * c.preallocate_percentage / 100) AS total_preallocated_items,
    FLOOR(c.total_sale_limit * c.redis_percentage / 100) AS total_redis_items,

    -- Service-specific allocations
    c.csharp_allocation_ratio,
    c.java_allocation_ratio,
    c.python_allocation_ratio,
    (c.csharp_allocation_ratio + c.java_allocation_ratio + c.python_allocation_ratio) AS total_ratio,

    -- Calculated per-service allocations
    FLOOR(
        (c.total_sale_limit * c.preallocate_percentage / 100) *
        c.csharp_allocation_ratio /
        (c.csharp_allocation_ratio + c.java_allocation_ratio + c.python_allocation_ratio)
    ) AS csharp_allocated_items,

    FLOOR(
        (c.total_sale_limit * c.preallocate_percentage / 100) *
        c.java_allocation_ratio /
        (c.csharp_allocation_ratio + c.java_allocation_ratio + c.python_allocation_ratio)
    ) AS java_allocated_items,

    FLOOR(
        (c.total_sale_limit * c.preallocate_percentage / 100) *
        c.python_allocation_ratio /
        (c.csharp_allocation_ratio + c.java_allocation_ratio + c.python_allocation_ratio)
    ) AS python_allocated_items,

    -- Refill watermark threshold
    FLOOR(
        (c.total_sale_limit * c.preallocate_percentage / 100) *
        c.csharp_allocation_ratio /
        (c.csharp_allocation_ratio + c.java_allocation_ratio + c.python_allocation_ratio) *
        c.refill_lower_watermark_pct / 100
    ) AS csharp_refill_watermark,

    FLOOR(
        (c.total_sale_limit * c.preallocate_percentage / 100) *
        c.java_allocation_ratio /
        (c.csharp_allocation_ratio + c.java_allocation_ratio + c.python_allocation_ratio) *
        c.refill_lower_watermark_pct / 100
    ) AS java_refill_watermark,

    FLOOR(
        (c.total_sale_limit * c.preallocate_percentage / 100) *
        c.python_allocation_ratio /
        (c.csharp_allocation_ratio + c.java_allocation_ratio + c.python_allocation_ratio) *
        c.refill_lower_watermark_pct / 100
    ) AS python_refill_watermark,

    c.status,
    c.start_time,
    c.end_time,
    c.preallocated_at,
    c.writeback_at
FROM flash_sale_campaigns c;

-- Example: Update existing campaigns with default allocation config
-- This sets 60% preallocated to services, 40% in Redis, with 20:13:1 ratio
UPDATE flash_sale_campaigns
SET
    preallocate_percentage = 60.00,
    redis_percentage = 40.00,
    refill_lower_watermark_pct = 25.00,
    csharp_allocation_ratio = 20,
    java_allocation_ratio = 13,
    python_allocation_ratio = 1
WHERE preallocate_percentage IS NULL OR preallocate_percentage = 0;

-- Example query to see allocation breakdown:
-- SELECT * FROM flash_sale_campaign_allocation WHERE status = 'active';
