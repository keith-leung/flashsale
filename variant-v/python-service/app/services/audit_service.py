# Audit service for write-ahead logging of orders

import aiomysql
import uuid
from typing import Dict, Optional
from ..core.config import settings

class AuditService:
    """Service for managing write-ahead audit logs."""
    
    def __init__(self):
        self.pool = None
    
    async def initialize(self):
        """Initialize the database connection pool."""
        if self.pool is None:
            self.pool = await aiomysql.create_pool(
                host='10.92.0.2',
                port=3306,
                user='syracuse',
                password='Orange_315_Forever!',
                db='orange315',
                minsize=5,
                maxsize=20,
                autocommit=True
            )
    
    async def create_audit_record(self, order_data: Dict) -> str:
        """
        Create a write-ahead audit record with status='pending'.
        
        Args:
            order_data: Dictionary containing order information
            
        Returns:
            audit_id: The UUID of the created audit record
        """
        audit_id = str(uuid.uuid4())
        order_id = str(uuid.uuid4())
        
        sql = f"""
        INSERT INTO {settings.audit_table} (
            id, order_id, customer_email, sku_id, quantity, unit_price, 
            flash_sale_campaign_id, status
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, 'pending')
        """
        
        await self.initialize()
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    sql,
                    (
                        audit_id,
                        order_id,
                        order_data['customer_email'],
                        order_data['sku_id'],
                        order_data['quantity'],
                        order_data['unit_price'],
                        order_data['flash_sale_campaign_id']
                    )
                )
        
        return audit_id
    
    async def confirm_audit(self, audit_id: str) -> bool:
        """
        Update audit record status to 'confirmed'.
        
        Args:
            audit_id: The UUID of the audit record to confirm
            
        Returns:
            bool: True if successfully confirmed, False if not found
        """
        sql = f"""
        UPDATE {settings.audit_table} 
        SET status = 'confirmed' 
        WHERE id = %s AND status = 'pending'
        """
        
        await self.initialize()
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(sql, (audit_id,))
                return cursor.rowcount > 0
    
    async def fail_audit(self, audit_id: str, reason: str) -> bool:
        """
        Update audit record status to 'failed'.
        
        Args:
            audit_id: The UUID of the audit record to fail
            reason: Reason for failure
            
        Returns:
            bool: True if successfully failed, False if not found
        """
        sql = f"""
        UPDATE {settings.audit_table} 
        SET status = 'failed' 
        WHERE id = %s AND status = 'pending'
        """
        
        await self.initialize()
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(sql, (audit_id,))
                return cursor.rowcount > 0
    
    async def get_pending_audits(self, limit: int = 1000) -> list:
        """
        Fetch pending audit records for batch processing.
        
        Args:
            limit: Maximum number of records to fetch
            
        Returns:
            list: List of pending audit records
        """
        sql = f"""
        SELECT id, order_id, customer_email, sku_id, quantity, unit_price, 
               flash_sale_campaign_id, created_at 
        FROM {settings.audit_table} 
        WHERE status = 'pending' 
        ORDER BY created_at ASC 
        LIMIT %s
        """
        
        await self.initialize()
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(sql, (limit,))
                return await cursor.fetchall()
    
    async def get_audit_by_id(self, audit_id: str) -> Optional[dict]:
        """Get audit record by ID."""
        sql = f"""
        SELECT * FROM {settings.audit_table} 
        WHERE id = %s
        """
        
        await self.initialize()
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(sql, (audit_id,))
                return await cursor.fetchone()

# Global audit service instance
audit_service = AuditService()
