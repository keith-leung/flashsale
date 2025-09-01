package com.flashsale.api.entity;

import jakarta.persistence.*;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

import java.time.LocalDateTime;
import java.util.UUID;

/**
 * Flash Sale Event with time-based controls and sale limits
 */
@Entity
@Table(name = "flash_sale_events", indexes = {
    @Index(name = "idx_flash_sale_start_time", columnList = "startTime"),
    @Index(name = "idx_flash_sale_end_time", columnList = "endTime"),
    @Index(name = "idx_flash_sale_status", columnList = "status"),
    @Index(name = "idx_flash_sale_sku", columnList = "skuId")
})
public class FlashSaleEvent extends BaseEntity {

    @NotBlank
    @Size(max = 250)
    @Column(nullable = false)
    private String name;

    @Column(columnDefinition = "TEXT")
    private String description;

    @NotNull
    @Column(nullable = false)
    private UUID skuId;

    @NotNull
    @Min(1)
    @Column(nullable = false)
    private Integer totalSaleLimit; // Total units available for this flash sale

    @Column(nullable = false)
    private Integer soldQuantity = 0; // Units sold so far

    @Min(1)
    @Column(nullable = false)
    private Integer maxQuantityPerCustomer = 1; // Max per customer

    @NotNull
    @Column(nullable = false)
    private LocalDateTime startTime;

    @NotNull
    @Column(nullable = false)
    private LocalDateTime endTime;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    private FlashSaleStatus status = FlashSaleStatus.SCHEDULED;

    @Column(nullable = false)
    private Boolean isActive = true;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "skuId", insertable = false, updatable = false)
    private Sku sku;

    // Constructors
    public FlashSaleEvent() {}

    public FlashSaleEvent(String name, UUID skuId, Integer totalSaleLimit, LocalDateTime startTime, LocalDateTime endTime) {
        this.name = name;
        this.skuId = skuId;
        this.totalSaleLimit = totalSaleLimit;
        this.startTime = startTime;
        this.endTime = endTime;
    }

    // Business logic methods
    public Integer getRemainingQuantity() {
        return Math.max(0, totalSaleLimit - soldQuantity);
    }

    public boolean isTimeActive() {
        LocalDateTime now = LocalDateTime.now();
        return !startTime.isAfter(now) && !endTime.isBefore(now);
    }

    public boolean isAvailable() {
        return isActive && status == FlashSaleStatus.ACTIVE && isTimeActive() && getRemainingQuantity() > 0;
    }

    public boolean canPurchaseQuantity(int quantity) {
        if (!isAvailable()) return false;
        if (quantity > maxQuantityPerCustomer) return false;
        return getRemainingQuantity() >= quantity;
    }

    public boolean purchaseQuantity(int quantity) {
        if (!canPurchaseQuantity(quantity)) return false;

        soldQuantity += quantity;

        // Update status if sold out
        if (getRemainingQuantity() == 0) {
            status = FlashSaleStatus.ENDED;
        }

        return true;
    }

    public void updateStatus() {
        LocalDateTime now = LocalDateTime.now();

        if (status == FlashSaleStatus.CANCELLED) return; // Don't change cancelled status

        if (now.isBefore(startTime)) {
            status = FlashSaleStatus.SCHEDULED;
        } else if (now.isAfter(endTime) || getRemainingQuantity() == 0) {
            status = FlashSaleStatus.ENDED;
        } else {
            status = FlashSaleStatus.ACTIVE;
        }
    }

    // Getters and Setters
    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }

    public String getDescription() {
        return description;
    }

    public void setDescription(String description) {
        this.description = description;
    }

    public UUID getSkuId() {
        return skuId;
    }

    public void setSkuId(UUID skuId) {
        this.skuId = skuId;
    }

    public Integer getTotalSaleLimit() {
        return totalSaleLimit;
    }

    public void setTotalSaleLimit(Integer totalSaleLimit) {
        this.totalSaleLimit = totalSaleLimit;
    }

    public Integer getSoldQuantity() {
        return soldQuantity;
    }

    public void setSoldQuantity(Integer soldQuantity) {
        this.soldQuantity = soldQuantity;
    }

    public Integer getMaxQuantityPerCustomer() {
        return maxQuantityPerCustomer;
    }

    public void setMaxQuantityPerCustomer(Integer maxQuantityPerCustomer) {
        this.maxQuantityPerCustomer = maxQuantityPerCustomer;
    }

    public LocalDateTime getStartTime() {
        return startTime;
    }

    public void setStartTime(LocalDateTime startTime) {
        this.startTime = startTime;
    }

    public LocalDateTime getEndTime() {
        return endTime;
    }

    public void setEndTime(LocalDateTime endTime) {
        this.endTime = endTime;
    }

    public FlashSaleStatus getStatus() {
        return status;
    }

    public void setStatus(FlashSaleStatus status) {
        this.status = status;
    }

    public Boolean getIsActive() {
        return isActive;
    }

    public void setIsActive(Boolean isActive) {
        this.isActive = isActive;
    }

    public Sku getSku() {
        return sku;
    }

    public void setSku(Sku sku) {
        this.sku = sku;
    }

    @Override
    public String toString() {
        return name + " (" + status + ")";
    }
}

enum FlashSaleStatus {
    SCHEDULED,
    ACTIVE,
    ENDED,
    CANCELLED
}
