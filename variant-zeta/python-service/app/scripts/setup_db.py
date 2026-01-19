"""Database setup for Variant Zeta (Redis-First)."""

import asyncio
import uuid
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy import text

# Database connection
DATABASE_URL = "mysql+aiomysql://syracuse:Orange_315_Forever!@mariadb:3306/orange315"

engine = create_async_engine(DATABASE_URL, echo=False)


async def setup_database():
    """Set up database tables and test data."""
    
    async with engine.begin() as conn:
        # Create tables
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS skus (
                id CHAR(36) PRIMARY KEY,
                sku_code VARCHAR(100) NOT NULL UNIQUE,
                name VARCHAR(255) NOT NULL,
                spu_id CHAR(36) NOT NULL,
                price DECIMAL(10,2) NOT NULL,
                cost_price DECIMAL(10,2),
                weight DECIMAL(10,3),
                track_inventory BOOLEAN DEFAULT TRUE,
                is_active BOOLEAN DEFAULT TRUE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_spu_id (spu_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """))
        
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS inventory (
                id CHAR(36) PRIMARY KEY,
                sku_id CHAR(36) NOT NULL UNIQUE,
                quantity INT NOT NULL DEFAULT 0,
                reserved_quantity INT NOT NULL DEFAULT 0,
                allow_negative_stock BOOLEAN DEFAULT FALSE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """))
        
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS flash_sale_campaigns (
                id CHAR(36) PRIMARY KEY,
                spu_id CHAR(36) NOT NULL,
                name VARCHAR(255) NOT NULL,
                description TEXT,
                start_time DATETIME NOT NULL,
                end_time DATETIME NOT NULL,
                total_sale_limit INT NOT NULL,
                sold_quantity INT NOT NULL DEFAULT 0,
                is_active TINYINT(1) DEFAULT 1,
                status VARCHAR(50) DEFAULT 'active',
                flash_price DECIMAL(10,2),
                max_quantity_per_customer INT DEFAULT 999,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_spu_id (spu_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """))
        
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS orders (
                id CHAR(36) PRIMARY KEY,
                order_number VARCHAR(100) NOT NULL UNIQUE,
                customer_email VARCHAR(255) NOT NULL,
                customer_name VARCHAR(255),
                subtotal DECIMAL(10,2) NOT NULL,
                tax_amount DECIMAL(10,2) NOT NULL DEFAULT 0,
                shipping_amount DECIMAL(10,2) NOT NULL DEFAULT 0,
                total_amount DECIMAL(10,2) NOT NULL,
                currency VARCHAR(10) NOT NULL DEFAULT 'USD',
                status VARCHAR(50) NOT NULL DEFAULT 'pending',
                flash_sale_campaign_id CHAR(36),
                notes TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """))
        
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS order_line_items (
                id CHAR(36) PRIMARY KEY,
                order_id CHAR(36) NOT NULL,
                sku_id CHAR(36) NOT NULL,
                quantity INT NOT NULL,
                unit_price DECIMAL(10,2) NOT NULL,
                total_price DECIMAL(10,2) NOT NULL,
                product_name VARCHAR(255),
                sku_code VARCHAR(100),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """))
        
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS payments (
                id CHAR(36) PRIMARY KEY,
                order_id CHAR(36) NOT NULL UNIQUE,
                amount DECIMAL(10,2) NOT NULL,
                currency VARCHAR(10) NOT NULL DEFAULT 'USD',
                payment_method VARCHAR(50) NOT NULL,
                gateway_transaction_id VARCHAR(255),
                gateway_response TEXT,
                status VARCHAR(50) NOT NULL DEFAULT 'authorized',
                reference_number VARCHAR(100),
                notes TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """))
        
        print("✓ Tables created")
        
        # Clean existing test data
        await conn.execute(text("DELETE FROM order_line_items"))
        await conn.execute(text("DELETE FROM payments"))
        await conn.execute(text("DELETE FROM orders WHERE customer_email LIKE 'stress-test%'"))
        await conn.execute(text("DELETE FROM inventory WHERE sku_id IN (SELECT id FROM skus WHERE sku_code LIKE 'STRESS-%')"))
        await conn.execute(text("DELETE FROM flash_sale_campaigns WHERE name LIKE 'Stress%'"))
        await conn.execute(text("DELETE FROM skus WHERE sku_code LIKE 'STRESS-%'"))
        await conn.commit()
        
        print("✓ Cleaned old test data")
        
        # Create 100 SKUs with 10,000 stock each for stress testing
        for i in range(100):
            sku_id = str(uuid.uuid4())
            spu_id = str(uuid.uuid4())
            inventory_id = str(uuid.uuid4())
            campaign_id = str(uuid.uuid4())
            
            # Create SKU
            await conn.execute(text("""
                INSERT INTO skus (id, sku_code, name, spu_id, price, cost_price, weight, track_inventory, is_active)
                VALUES (%s, %s, %s, %s, %s, %s, %s, TRUE, TRUE)
            """), (sku_id, f'STRESS-SKU-{i:03d}', f'Stress Test Product {i}', spu_id, 99.99, 50.00, 0.150))
            
            # Create inventory
            await conn.execute(text("""
                INSERT INTO inventory (id, sku_id, quantity, reserved_quantity, allow_negative_stock)
                VALUES (%s, %s, 10000, 0, FALSE)
            """), (inventory_id, sku_id))
            
            # Create flash sale campaign
            await conn.execute(text("""
                INSERT INTO flash_sale_campaigns (id, spu_id, name, description, start_time, end_time, total_sale_limit, sold_quantity, is_active, status, flash_price, max_quantity_per_customer)
                VALUES (%s, %s, %s, %s, NOW(), '2030-12-31 23:59:59', 10000, 0, TRUE, 'active', 99.99, 999)
            """), (campaign_id, spu_id, f'Stress Campaign {i}', f'Test campaign {i}'))
        
        await conn.commit()
        print("✓ Created 100 stress test SKUs with 10,000 stock each")


if __name__ == '__main__':
    asyncio.run(setup_database())
