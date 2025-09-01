-- Flash Sale Microservices - Shared MySQL 8+ Schema
-- This schema is used by all three services (Python, C#, Java)

CREATE DATABASE IF NOT EXISTS flashsale_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE flashsale_db;

-- SPU (Standard Product Unit) Table  
CREATE TABLE spus (
    id BIGINT NOT NULL PRIMARY KEY,           -- Timestamp-readable ID: 20250523143045001
    name VARCHAR(250) NOT NULL,
    slug VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_spu_name (name),
    INDEX idx_spu_slug (slug),
    INDEX idx_spu_active (is_active),
    INDEX idx_spu_id_time (id),               -- Natural time-based ordering
    INDEX idx_spu_created (created_at)
) ENGINE=InnoDB;

-- SKU (Stock Keeping Unit) Table
CREATE TABLE skus (
    id BIGINT NOT NULL PRIMARY KEY,           -- Timestamp-readable ID: 20250523143045002
    sku_code VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(255),
    spu_id BIGINT NOT NULL,                   -- Foreign key to SPU timestamp ID
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
    INDEX idx_sku_id_time (id),               -- Natural time-based ordering
    INDEX idx_sku_created (created_at)
) ENGINE=InnoDB;

-- Inventory Table
CREATE TABLE inventory (
    id BIGINT NOT NULL PRIMARY KEY,           -- Timestamp-readable ID: 20250523143045003
    sku_id BIGINT NOT NULL UNIQUE,            -- Foreign key to SKU timestamp ID
    quantity INT NOT NULL DEFAULT 0,
    reserved_quantity INT NOT NULL DEFAULT 0,
    allow_negative_stock BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (sku_id) REFERENCES skus(id) ON DELETE CASCADE,
    INDEX idx_inventory_sku (sku_id),
    INDEX idx_inventory_id_time (id),         -- Natural time-based ordering
    INDEX idx_inventory_updated (updated_at)
) ENGINE=InnoDB;

-- Flash Sale Events Table
CREATE TABLE flash_sale_events (
    id BIGINT NOT NULL PRIMARY KEY,           -- Timestamp-readable ID: 20250523143045004
    name VARCHAR(250) NOT NULL,
    description TEXT,
    sku_id BIGINT NOT NULL,                   -- Foreign key to SKU timestamp ID
    total_sale_limit INT NOT NULL,
    sold_quantity INT NOT NULL DEFAULT 0,
    max_quantity_per_customer INT NOT NULL DEFAULT 1,
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
    INDEX idx_flash_sale_status (status),
    INDEX idx_flash_sale_active (is_active),
    INDEX idx_flash_sale_id_time (id),        -- Natural time-based ordering for campaigns
    INDEX idx_flash_sale_created (created_at)
) ENGINE=InnoDB;

-- Orders Table
CREATE TABLE orders (
    id BIGINT NOT NULL PRIMARY KEY,           -- Timestamp-readable ID: 20250523143045005
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
    flash_sale_id BIGINT,                     -- Foreign key to flash sale timestamp ID (optional)
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (flash_sale_id) REFERENCES flash_sale_events(id) ON DELETE SET NULL,
    INDEX idx_order_number (order_number),
    INDEX idx_order_customer (customer_email),
    INDEX idx_order_status (status),
    INDEX idx_order_flash_sale (flash_sale_id),
    INDEX idx_order_id_time (id),            -- Natural time-based ordering for orders
    INDEX idx_order_created (created_at)
) ENGINE=InnoDB;

-- Order Line Items Table
CREATE TABLE order_line_items (
    id BIGINT NOT NULL PRIMARY KEY,           -- Timestamp-readable ID: 20250523143045006
    order_id BIGINT NOT NULL,                 -- Foreign key to order timestamp ID
    sku_id BIGINT NOT NULL,                   -- Foreign key to SKU timestamp ID
    quantity INT NOT NULL,
    unit_price DECIMAL(10,2) NOT NULL,
    total_price DECIMAL(10,2) NOT NULL,
    product_name VARCHAR(255) NOT NULL,
    sku_code VARCHAR(255) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY (sku_id) REFERENCES skus(id) ON DELETE CASCADE,
    INDEX idx_line_item_order (order_id),
    INDEX idx_line_item_sku (sku_id),
    INDEX idx_line_item_id_time (id),        -- Natural time-based ordering
    INDEX idx_line_item_created (created_at)
) ENGINE=InnoDB;

-- Payments Table
CREATE TABLE payments (
    id BIGINT NOT NULL PRIMARY KEY,           -- Timestamp-readable ID: 20250523143045007
    order_id BIGINT NOT NULL,                 -- Foreign key to order timestamp ID
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
    INDEX idx_payment_id_time (id),          -- Natural time-based ordering for payments
    INDEX idx_payment_created (created_at)
) ENGINE=InnoDB;

-- Add triggers for automatic timestamp updates (MySQL 8+)
-- SPU trigger
DELIMITER //
CREATE TRIGGER spu_updated_at_trigger
    BEFORE UPDATE ON spus
    FOR EACH ROW
BEGIN
    SET NEW.updated_at = CURRENT_TIMESTAMP;
END//
DELIMITER ;

-- SKU trigger
DELIMITER //
CREATE TRIGGER sku_updated_at_trigger
    BEFORE UPDATE ON skus
    FOR EACH ROW
BEGIN
    SET NEW.updated_at = CURRENT_TIMESTAMP;
END//
DELIMITER ;

-- Inventory trigger
DELIMITER //
CREATE TRIGGER inventory_updated_at_trigger
    BEFORE UPDATE ON inventory
    FOR EACH ROW
BEGIN
    SET NEW.updated_at = CURRENT_TIMESTAMP;
END//
DELIMITER ;

-- Flash Sale trigger
DELIMITER //
CREATE TRIGGER flash_sale_updated_at_trigger
    BEFORE UPDATE ON flash_sale_events
    FOR EACH ROW
BEGIN
    SET NEW.updated_at = CURRENT_TIMESTAMP;
END//
DELIMITER ;

-- Order trigger
DELIMITER //
CREATE TRIGGER order_updated_at_trigger
    BEFORE UPDATE ON orders
    FOR EACH ROW
BEGIN
    SET NEW.updated_at = CURRENT_TIMESTAMP;
END//
DELIMITER ;

-- Order Line Item trigger
DELIMITER //
CREATE TRIGGER order_line_item_updated_at_trigger
    BEFORE UPDATE ON order_line_items
    FOR EACH ROW
BEGIN
    SET NEW.updated_at = CURRENT_TIMESTAMP;
END//
DELIMITER ;

-- Payment trigger
DELIMITER //
CREATE TRIGGER payment_updated_at_trigger
    BEFORE UPDATE ON payments
    FOR EACH ROW
BEGIN
    SET NEW.updated_at = CURRENT_TIMESTAMP;
END//
DELIMITER ;
