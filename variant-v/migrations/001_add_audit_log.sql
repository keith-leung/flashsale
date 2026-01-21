-- Write-ahead audit log table
CREATE TABLE audit_order_log (
    id CHAR(36) PRIMARY KEY,
    order_id CHAR(36) NOT NULL,
    customer_email VARCHAR(255) NOT NULL,
    sku_id CHAR(36) NOT NULL,
    quantity INT NOT NULL,
    unit_price DECIMAL(10,2) NOT NULL,
    flash_sale_campaign_id CHAR(36),
    status ENUM('pending','confirmed','failed') NOT NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    INDEX idx_audit_lookup (order_id, status),
    INDEX idx_campaign_audit (flash_sale_campaign_id, created_at)
) ENGINE=InnoDB;
