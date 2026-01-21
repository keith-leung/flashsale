package com.flashsale.entity;

import jakarta.persistence.*;
import lombok.Data;
import java.time.LocalDateTime;

@Entity
@Table(name = "audit_order_log")
@Data
public class AuditOrderLog {
    @Id
    @Column(name = "id", length = 36, nullable = false)
    private String id;
    
    @Column(name = "order_id", nullable = false, length = 36)
    private String orderId;
    
    @Column(name = "customer_email", nullable = false, length = 255)
    private String customerEmail;
    
    @Column(name = "sku_id", nullable = false, length = 36)
    private String skuId;
    
    @Column(name = "quantity", nullable = false)
    private Integer quantity;
    
    @Column(name = "unit_price", nullable = false, precision = 10, scale = 2)
    private java.math.BigDecimal unitPrice;
    
    @Column(name = "flash_sale_campaign_id", length = 36)
    private String flashSaleCampaignId;
    
    @Column(name = "status", nullable = false, length = 20)
    @Enumerated(EnumType.STRING)
    private AuditStatus status;
    
    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt = LocalDateTime.now();
    
    @Column(name = "updated_at")
    private LocalDateTime updatedAt;
    
    @PreUpdate
    protected void onUpdate() {
        this.updatedAt = LocalDateTime.now();
    }
    
    public enum AuditStatus {
        PENDING, CONFIRMED, FAILED
    }
}
