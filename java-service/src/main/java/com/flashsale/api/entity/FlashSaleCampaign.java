package com.flashsale.api.entity;

import jakarta.persistence.*;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

/**
 * Flash Sale Campaign - SPU-level (product family) with time-based controls and sale limits.
 *
 * CRITICAL: Campaigns are SPU-level, NOT SKU-level!
 * Example: Campaign for "iPhone 16" (SPU) with 100K total_sale_limit
 *          Customers order "iPhone 16 Black 512GB" or "iPhone 16 Silver 128GB" (SKUs)
 *          Campaign tracks total across ALL SKUs under the SPU
 */
@Entity
@Table(name = "flash_sale_campaigns", indexes = {
    @Index(name = "idx_flash_sale_start_time", columnList = "startTime"),
    @Index(name = "idx_flash_sale_end_time", columnList = "endTime"),
    @Index(name = "idx_flash_sale_status", columnList = "status"),
    @Index(name = "idx_flash_sale_spu", columnList = "spuId")
})
public class FlashSaleCampaign extends BaseEntity {

    @NotBlank
    @Size(max = 250)
    @Column(nullable = false)
    private String name;

    @Column(columnDefinition = "TEXT")
    private String description;

    @NotNull
    @Column(nullable = false, columnDefinition = "CHAR(36)")
    private UUID spuId;  // Links to product family (SPU), NOT variant (SKU)!

    @NotNull
    @Min(1)
    @Column(nullable = false)
    private Integer totalSaleLimit; // Total units across ALL SKUs under this SPU

    @Column(nullable = false)
    private Integer soldQuantity = 0; // Incremented when ANY SKU under this SPU is ordered

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
    private FlashSaleStatus status = FlashSaleStatus.scheduled;

    @Column(nullable = false)
    private Boolean isActive = true;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "spuId", insertable = false, updatable = false)
    private Spu spu;  // Links to product family

    @OneToMany(mappedBy = "flashSaleCampaign", fetch = FetchType.LAZY)
    private List<Order> orders = new ArrayList<>();

    // Constructors
    public FlashSaleCampaign() {}

    public FlashSaleCampaign(String name, UUID spuId, Integer totalSaleLimit, LocalDateTime startTime, LocalDateTime endTime) {
        this.name = name;
        this.spuId = spuId;
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
        return isActive && status == FlashSaleStatus.active && isTimeActive() && getRemainingQuantity() > 0;
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
            status = FlashSaleStatus.ended;
        }

        return true;
    }

    public void updateStatus() {
        LocalDateTime now = LocalDateTime.now();

        if (status == FlashSaleStatus.cancelled) return; // Don't change cancelled status

        if (now.isBefore(startTime)) {
            status = FlashSaleStatus.scheduled;
        } else if (now.isAfter(endTime) || getRemainingQuantity() == 0) {
            status = FlashSaleStatus.ended;
        } else {
            status = FlashSaleStatus.active;
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

    public UUID getSpuId() {
        return spuId;
    }

    public void setSpuId(UUID spuId) {
        this.spuId = spuId;
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

    public Spu getSpu() {
        return spu;
    }

    public void setSpu(Spu spu) {
        this.spu = spu;
    }

    public List<Order> getOrders() {
        return orders;
    }

    public void setOrders(List<Order> orders) {
        this.orders = orders;
    }

    @Override
    public String toString() {
        return name + " (" + status + ")";
    }
}
