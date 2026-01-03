package com.flashsale.api.entity;

import jakarta.persistence.*;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

/**
 * Stock Keeping Unit - represents a specific variant of a product (like Saleor's ProductVariant)
 */
@Entity
@Table(name = "skus", indexes = {
    @Index(name = "idx_sku_code", columnList = "skuCode", unique = true),
    @Index(name = "idx_sku_spu", columnList = "spuId")
})
public class Sku extends BaseEntity {

    @NotBlank
    @Size(max = 255)
    @Column(nullable = false, unique = true)
    private String skuCode;

    @Size(max = 255)
    private String name;

    @NotNull
    @Column(nullable = false, columnDefinition = "CHAR(36)")
    private UUID spuId;

    @NotNull
    @DecimalMin(value = "0.01")
    @Column(nullable = false, precision = 10, scale = 2)
    private BigDecimal price;

    @DecimalMin(value = "0.00")
    @Column(precision = 10, scale = 2)
    private BigDecimal costPrice;

    @DecimalMin(value = "0.000")
    @Column(precision = 8, scale = 3)
    private BigDecimal weight; // in kg

    @Column(nullable = false)
    private Boolean trackInventory = true;

    @Column(nullable = false)
    private Boolean isActive = true;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "spuId", insertable = false, updatable = false)
    private Spu spu;

    @OneToOne(mappedBy = "sku", cascade = CascadeType.ALL, orphanRemoval = true)
    private Inventory inventory;

    // Constructors
    public Sku() {}

    public Sku(String skuCode, UUID spuId, BigDecimal price) {
        this.skuCode = skuCode;
        this.spuId = spuId;
        this.price = price;
    }

    // Getters and Setters
    public String getSkuCode() {
        return skuCode;
    }

    public void setSkuCode(String skuCode) {
        this.skuCode = skuCode;
    }

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }

    public UUID getSpuId() {
        return spuId;
    }

    public void setSpuId(UUID spuId) {
        this.spuId = spuId;
    }

    public BigDecimal getPrice() {
        return price;
    }

    public void setPrice(BigDecimal price) {
        this.price = price;
    }

    public BigDecimal getCostPrice() {
        return costPrice;
    }

    public void setCostPrice(BigDecimal costPrice) {
        this.costPrice = costPrice;
    }

    public BigDecimal getWeight() {
        return weight;
    }

    public void setWeight(BigDecimal weight) {
        this.weight = weight;
    }

    public Boolean getTrackInventory() {
        return trackInventory;
    }

    public void setTrackInventory(Boolean trackInventory) {
        this.trackInventory = trackInventory;
    }

    public Boolean getIsActive() {
        return isActive;
    }

    public void setIsActive(Boolean isActive) {
        this.isActive = isActive;
    }

    public Spu getSpu() {
        return spu;
    }

    public void setSpu(Spu spu) {
        this.spu = spu;
    }

    public Inventory getInventory() {
        return inventory;
    }

    public void setInventory(Inventory inventory) {
        this.inventory = inventory;
    }

    @Override
    public String toString() {
        return skuCode != null ? skuCode : "SKU-" + getId();
    }
}
