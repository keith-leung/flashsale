package com.flashsale.entity;

import jakarta.persistence.*;
import java.time.Instant;

/**
 * SKU entity - Variant Z.
 */
@Entity
@Table(name = "skus")
public class SKU {

    @Id
    @Column(name = "id", updatable = false, nullable = false)
    private String id;

    @Column(name = "spu_id", nullable = false)
    private String spuId;

    @Column(name = "sku_code", nullable = false, unique = true)
    private String skuCode;

    @Column(name = "name", nullable = false)
    private String name;

    @Column(name = "price", nullable = false)
    private Double price;

    @Column(name = "is_active", nullable = false)
    private Boolean isActive;

    @Column(name = "created_at", updatable = false)
    private Instant createdAt;

    @Column(name = "updated_at")
    private Instant updatedAt;

    // One-to-one relationship with Inventory
    @OneToOne(mappedBy = "sku", cascade = CascadeType.ALL, fetch = FetchType.LAZY)
    private Inventory inventory;

    // Default constructor
    public SKU() {
        this.createdAt = Instant.now();
        this.updatedAt = Instant.now();
        this.isActive = true;
    }

    // Getters and Setters
    public String getId() { return id; }
    public void setId(String id) { this.id = id; }
    public String getSpuId() { return spuId; }
    public void setSpuId(String spuId) { this.spuId = spuId; }
    public String getSkuCode() { return skuCode; }
    public void setSkuCode(String skuCode) { this.skuCode = skuCode; }
    public String getName() { return name; }
    public void setName(String name) { this.name = name; }
    public Double getPrice() { return price; }
    public void setPrice(Double price) { this.price = price; }
    public Boolean getIsActive() { return isActive; }
    public void setIsActive(Boolean isActive) { this.isActive = isActive; }
    public Instant getCreatedAt() { return createdAt; }
    public void setCreatedAt(Instant createdAt) { this.createdAt = createdAt; }
    public Instant getUpdatedAt() { return updatedAt; }
    public void setUpdatedAt(Instant updatedAt) { this.updatedAt = updatedAt; }
    public Inventory getInventory() { return inventory; }
    public void setInventory(Inventory inventory) { this.inventory = inventory; }

    @PreUpdate
    public void preUpdate() {
        this.updatedAt = Instant.now();
    }
}