-- Flash Sale Microservices - Shared Database Schema
-- This schema is used by all three services (Python, C#, Java)
-- Optimized for flash sale performance with MariaDB InnoDB storage engine
--
-- Database: orange315
-- MariaDB Version: 10.6.22+ (compatible with MySQL 8+)
-- Redis Version: 6.0.16+
--
-- Connection Info:
--   Host: 127.0.0.1
--   Port: 3306
--   Database: orange315
--   User: syracuse
--   Password: Orange_315_Forever!

CREATE DATABASE IF NOT EXISTS orange315 CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE orange315;

-- SPU (Standard Product Unit) Table  
CREATE TABLE spus (
    id CHAR(36) NOT NULL PRIMARY KEY,           -- UUID format for distributed systems
    name VARCHAR(250) NOT NULL,
    slug VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_spu_name (name),
    INDEX idx_spu_slug (slug),
    INDEX idx_spu_active (is_active),
    INDEX idx_spu_created (created_at)
) ENGINE=InnoDB;

-- SKU (Stock Keeping Unit) Table
CREATE TABLE skus (
    id CHAR(36) NOT NULL PRIMARY KEY,           -- UUID format
    sku_code VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(255),
    spu_id CHAR(36) NOT NULL,                   -- Foreign key to SPU
    price DECIMAL(10,2) NOT NULL,
    cost_price DECIMAL(10,2),
    weight DECIMAL(8,3),
    track_inventory BOOLEAN NOT NULL DEFAULT TRUE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (spu_id) REFERENCES spus(id) ON DELETE CASCADE,
    INDEX idx_sku_code (sku_code),
    INDEX idx_sku_spu (spu_id),
    INDEX idx_sku_active (is_active),
    INDEX idx_sku_created (created_at)
) ENGINE=InnoDB;

-- Inventory Table - Critical for flash sale performance
CREATE TABLE inventory (
    id CHAR(36) NOT NULL PRIMARY KEY,           -- UUID format
    sku_id CHAR(36) NOT NULL UNIQUE,            -- Foreign key to SKU
    quantity INT NOT NULL DEFAULT 0,
    reserved_quantity INT NOT NULL DEFAULT 0,   -- Critical for preventing overselling
    allow_negative_stock BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (sku_id) REFERENCES skus(id) ON DELETE CASCADE,
    INDEX idx_inventory_sku (sku_id),
    INDEX idx_inventory_updated (updated_at)
) ENGINE=InnoDB;

-- Flash Sale Events Table - Optimized for high-concurrency flash sales
CREATE TABLE flash_sale_events (
    id CHAR(36) NOT NULL PRIMARY KEY,           -- UUID format
    name VARCHAR(250) NOT NULL,
    description TEXT,
    sku_id CHAR(36) NOT NULL,                   -- Foreign key to SKU
    total_sale_limit INT NOT NULL,              -- Total units available for flash sale
    sold_quantity INT NOT NULL DEFAULT 0,      -- Current sold quantity (prevents overselling)
    max_quantity_per_customer INT NOT NULL DEFAULT 1, -- Per-customer limit
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP NOT NULL,
    status ENUM('scheduled', 'active', 'ended', 'cancelled') NOT NULL DEFAULT 'scheduled',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (sku_id) REFERENCES skus(id) ON DELETE CASCADE,
    INDEX idx_flash_sale_name (name),
    INDEX idx_flash_sale_sku (sku_id),
    INDEX idx_flash_sale_start (start_time),
    INDEX idx_flash_sale_end (end_time),
    INDEX idx_flash_sale_status (status),        -- Critical for filtering active sales
    INDEX idx_flash_sale_active (is_active),
    INDEX idx_flash_sale_created (created_at)
) ENGINE=InnoDB;

-- Orders Table
CREATE TABLE orders (
    id CHAR(36) NOT NULL PRIMARY KEY,           -- UUID format
    order_number VARCHAR(50) NOT NULL UNIQUE,
    customer_email VARCHAR(255) NOT NULL,
    customer_name VARCHAR(255),
    subtotal DECIMAL(10,2) NOT NULL,
    tax_amount DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    shipping_amount DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    total_amount DECIMAL(10,2) NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    status ENUM('pending', 'confirmed', 'processing', 'shipped', 'delivered', 'cancelled', 'refunded') NOT NULL DEFAULT 'pending',
    notes TEXT,
    flash_sale_id CHAR(36),                     -- Foreign key to flash sale (optional)
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (flash_sale_id) REFERENCES flash_sale_events(id) ON DELETE SET NULL,
    INDEX idx_order_number (order_number),
    INDEX idx_order_customer (customer_email),
    INDEX idx_order_status (status),
    INDEX idx_order_flash_sale (flash_sale_id),
    INDEX idx_order_created (created_at)
) ENGINE=InnoDB;

-- Order Line Items Table
CREATE TABLE order_line_items (
    id CHAR(36) NOT NULL PRIMARY KEY,           -- UUID format
    order_id CHAR(36) NOT NULL,                 -- Foreign key to order
    sku_id CHAR(36) NOT NULL,                   -- Foreign key to SKU
    quantity INT NOT NULL,
    unit_price DECIMAL(10,2) NOT NULL,
    total_price DECIMAL(10,2) NOT NULL,
    product_name VARCHAR(255) NOT NULL,
    sku_code VARCHAR(255) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY (sku_id) REFERENCES skus(id) ON DELETE RESTRICT,
    INDEX idx_line_item_order (order_id),
    INDEX idx_line_item_sku (sku_id),
    INDEX idx_line_item_created (created_at)
) ENGINE=InnoDB;

-- Payments Table
CREATE TABLE payments (
    id CHAR(36) NOT NULL PRIMARY KEY,           -- UUID format
    order_id CHAR(36) NOT NULL,                 -- Foreign key to order
    amount DECIMAL(10,2) NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    payment_method VARCHAR(50) NOT NULL,
    gateway_transaction_id VARCHAR(255),
    gateway_response TEXT,
    status ENUM('pending', 'authorized', 'captured', 'failed', 'cancelled', 'refunded') NOT NULL DEFAULT 'pending',
    reference_number VARCHAR(100),
    notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    INDEX idx_payment_order (order_id),
    INDEX idx_payment_gateway (gateway_transaction_id),
    INDEX idx_payment_status (status),
    INDEX idx_payment_created (created_at)
) ENGINE=InnoDB;

-- Sample data for testing
INSERT INTO spus (id, name, slug, description) VALUES 
    ('550e8400-e29b-41d4-a716-446655440001', 'iPhone 15 Pro', 'iphone-15-pro', 'Latest iPhone with Pro features'),
    ('550e8400-e29b-41d4-a716-446655440002', 'Samsung Galaxy S24', 'samsung-galaxy-s24', 'Latest Samsung flagship phone')
ON DUPLICATE KEY UPDATE name=VALUES(name);

INSERT INTO skus (id, spu_id, sku_code, name, price, cost_price, weight) VALUES 
    ('650e8400-e29b-41d4-a716-446655440001', '550e8400-e29b-41d4-a716-446655440001', 'IP15P-128-BLK', 'iPhone 15 Pro 128GB Black', 999.00, 700.00, 0.187),
    ('650e8400-e29b-41d4-a716-446655440002', '550e8400-e29b-41d4-a716-446655440001', 'IP15P-256-BLK', 'iPhone 15 Pro 256GB Black', 1199.00, 850.00, 0.187),
    ('650e8400-e29b-41d4-a716-446655440003', '550e8400-e29b-41d4-a716-446655440002', 'SGS24-128-BLK', 'Samsung Galaxy S24 128GB Black', 799.00, 550.00, 0.168)
ON DUPLICATE KEY UPDATE name=VALUES(name);

INSERT INTO inventory (id, sku_id, quantity, reserved_quantity) VALUES 
    ('750e8400-e29b-41d4-a716-446655440001', '650e8400-e29b-41d4-a716-446655440001', 100, 0),
    ('750e8400-e29b-41d4-a716-446655440002', '650e8400-e29b-41d4-a716-446655440002', 50, 0),
    ('750e8400-e29b-41d4-a716-446655440003', '650e8400-e29b-41d4-a716-446655440003', 75, 0)
ON DUPLICATE KEY UPDATE quantity=VALUES(quantity);

-- Sample flash sale (starts in 1 hour, runs for 24 hours)
INSERT INTO flash_sale_events (id, name, description, sku_id, total_sale_limit, max_quantity_per_customer, start_time, end_time) VALUES 
    ('850e8400-e29b-41d4-a716-446655440001', 'iPhone 15 Pro Flash Sale', 'Limited time flash sale on iPhone 15 Pro', '650e8400-e29b-41d4-a716-446655440001', 20, 2, DATE_ADD(NOW(), INTERVAL 1 HOUR), DATE_ADD(NOW(), INTERVAL 25 HOUR))
ON DUPLICATE KEY UPDATE name=VALUES(name);