package com.flashsale.entity;

import jakarta.persistence.*;

/**
 * Inventory entity - Variant Z.
 */
@Entity
@Table(name = "inventory")
public class Inventory {

    @Id
    @Column(name = "id", updatable = false, nullable = false)
    private String id;

    @Column(name = "sku_id", nullable = false, unique = true)
    private String skuId;

    @Column(name = "quantity", nullable = false)
    private Integer quantity;

    @Column(name = "reserved_quantity", nullable = false)
    private Integer reservedQuantity;

    @Column(name = "created_at", updatable = false)
    private java.time.Instant createdAt;

    @Column(name = "updated_at")
    private java.time.Instant updatedAt;

    // Many-to-one relationship with SKU
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "sku_id", insertable = false, updatable = false)
    private SKU sku;

    // Default constructor
    public Inventory() {
        this.createdAt = java.time.Instant.now();
        this.updatedAt = java.time.Instant.now();
        this.quantity = 0;
        this.reservedQuantity = 0;
    }

    // Getters and Setters
    public String getId() { return id; }
    public void setId(String id) { this.id = id; }
    public String getSkuId() { return skuId; }
    public void setSkuId(String skuId) { this.skuId = skuId; }
    public Integer getQuantity() { return quantity; }
    public void setQuantity(Integer quantity) { this.quantity = quantity; }
    public Integer getReservedQuantity() { return reservedQuantity; }
    public void setReservedQuantity(Integer reservedQuantity) { this.reservedQuantity = reservedQuantity; }
    public java.time.Instant getCreatedAt() { return createdAt; }
    public void setCreatedAt(java.time.Instant createdAt) { this.createdAt = createdAt; }
    public java.time.Instant getUpdatedAt() { return updatedAt; }
    public void setUpdatedAt(java.time.Instant updatedAt) { this.updatedAt = updatedAt; }
    public SKU getSku() { return sku; }
    public void setSku(SKU sku) { this.sku = sku; }

    @PreUpdate
    public void preUpdate() {
        this.updatedAt = java.time.Instant.now();
    }
}