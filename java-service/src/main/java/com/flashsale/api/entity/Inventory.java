package com.flashsale.api.entity;

import jakarta.persistence.*;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;

import java.util.UUID;

/**
 * Inventory tracking for SKUs
 */
@Entity
@Table(name = "inventory", indexes = {
    @Index(name = "idx_inventory_sku", columnList = "skuId", unique = true)
})
public class Inventory extends BaseEntity {

    @NotNull
    @Column(nullable = false, unique = true)
    private UUID skuId;

    @Min(0)
    @Column(nullable = false)
    private Integer quantity = 0;

    @Min(0)
    @Column(nullable = false)
    private Integer reservedQuantity = 0; // Items in pending orders

    @Column(nullable = false)
    private Boolean allowNegativeStock = false;

    @OneToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "skuId", insertable = false, updatable = false)
    private Sku sku;

    // Constructors
    public Inventory() {}

    public Inventory(UUID skuId, Integer quantity) {
        this.skuId = skuId;
        this.quantity = quantity;
    }

    // Business logic methods
    public Integer getAvailableQuantity() {
        return Math.max(0, quantity - reservedQuantity);
    }

    public boolean canFulfillQuantity(int requestedQuantity) {
        if (allowNegativeStock) return true;
        return getAvailableQuantity() >= requestedQuantity;
    }

    public boolean reserveQuantity(int quantity) {
        if (!canFulfillQuantity(quantity)) return false;
        reservedQuantity += quantity;
        return true;
    }

    public void releaseQuantity(int quantity) {
        reservedQuantity = Math.max(0, reservedQuantity - quantity);
    }

    public boolean fulfillQuantity(int quantity) {
        if (reservedQuantity < quantity) return false;
        reservedQuantity -= quantity;
        this.quantity -= quantity;
        return true;
    }

    // Getters and Setters
    public UUID getSkuId() {
        return skuId;
    }

    public void setSkuId(UUID skuId) {
        this.skuId = skuId;
    }

    public Integer getQuantity() {
        return quantity;
    }

    public void setQuantity(Integer quantity) {
        this.quantity = quantity;
    }

    public Integer getReservedQuantity() {
        return reservedQuantity;
    }

    public void setReservedQuantity(Integer reservedQuantity) {
        this.reservedQuantity = reservedQuantity;
    }

    public Boolean getAllowNegativeStock() {
        return allowNegativeStock;
    }

    public void setAllowNegativeStock(Boolean allowNegativeStock) {
        this.allowNegativeStock = allowNegativeStock;
    }

    public Sku getSku() {
        return sku;
    }

    public void setSku(Sku sku) {
        this.sku = sku;
    }

    @Override
    public String toString() {
        return "Inventory for " + (sku != null ? sku.getSkuCode() : skuId) + ": " + getAvailableQuantity() + "/" + quantity;
    }
}
