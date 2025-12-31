package com.flashsale.api.entity;

import jakarta.persistence.*;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;

import java.math.BigDecimal;
import java.util.UUID;

/**
 * Individual items within an order
 */
@Entity
@Table(name = "order_line_items", indexes = {
    @Index(name = "idx_line_items_order", columnList = "orderId"),
    @Index(name = "idx_line_items_sku", columnList = "skuId")
})
public class OrderLineItem extends BaseEntity {

    @NotNull
    @Column(nullable = false, columnDefinition = "CHAR(36)")
    private UUID orderId;

    @NotNull
    @Column(nullable = false, columnDefinition = "CHAR(36)")
    private UUID skuId;

    // Item details
    @Min(1)
    @Column(nullable = false)
    private Integer quantity;

    @NotNull
    @Column(nullable = false, precision = 10, scale = 2)
    private BigDecimal unitPrice;

    @NotNull
    @Column(nullable = false, precision = 10, scale = 2)
    private BigDecimal totalPrice;

    // Product snapshot (in case SKU details change)
    @NotBlank
    @Column(nullable = false, length = 255)
    private String productName;

    @NotBlank
    @Column(nullable = false, length = 255)
    private String skuCode;

    // Navigation properties
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "orderId", insertable = false, updatable = false)
    private Order order;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "skuId", insertable = false, updatable = false)
    private Sku sku;

    // Constructors
    public OrderLineItem() {}

    public OrderLineItem(UUID orderId, UUID skuId, Integer quantity, BigDecimal unitPrice, String productName, String skuCode) {
        this.orderId = orderId;
        this.skuId = skuId;
        this.quantity = quantity;
        this.unitPrice = unitPrice;
        this.totalPrice = unitPrice.multiply(BigDecimal.valueOf(quantity));
        this.productName = productName;
        this.skuCode = skuCode;
    }

    // Getters and Setters
    public UUID getOrderId() {
        return orderId;
    }

    public void setOrderId(UUID orderId) {
        this.orderId = orderId;
    }

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
        if (this.unitPrice != null) {
            this.totalPrice = this.unitPrice.multiply(BigDecimal.valueOf(quantity));
        }
    }

    public BigDecimal getUnitPrice() {
        return unitPrice;
    }

    public void setUnitPrice(BigDecimal unitPrice) {
        this.unitPrice = unitPrice;
        if (this.quantity != null) {
            this.totalPrice = unitPrice.multiply(BigDecimal.valueOf(this.quantity));
        }
    }

    public BigDecimal getTotalPrice() {
        return totalPrice;
    }

    public void setTotalPrice(BigDecimal totalPrice) {
        this.totalPrice = totalPrice;
    }

    public String getProductName() {
        return productName;
    }

    public void setProductName(String productName) {
        this.productName = productName;
    }

    public String getSkuCode() {
        return skuCode;
    }

    public void setSkuCode(String skuCode) {
        this.skuCode = skuCode;
    }

    public Order getOrder() {
        return order;
    }

    public void setOrder(Order order) {
        this.order = order;
    }

    public Sku getSku() {
        return sku;
    }

    public void setSku(Sku sku) {
        this.sku = sku;
    }

    @Override
    public String toString() {
        return quantity + "x " + productName;
    }
}
