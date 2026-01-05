package com.flashsale.api.entity;

import jakarta.persistence.*;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.UUID;

/**
 * Flash Sale Campaign (SPU-level) with total sale limit across all SKU variants
 */
@Entity
@Table(name = "flash_sale_campaigns", indexes = {
    @Index(name = "idx_flash_sale_name", columnList = "name"),
    @Index(name = "idx_flash_sale_spu", columnList = "spu_id"),
    @Index(name = "idx_flash_sale_status", columnList = "status"),
    @Index(name = "idx_flash_sale_start", columnList = "start_time"),
    @Index(name = "idx_flash_sale_end", columnList = "end_time"),
    @Index(name = "idx_flash_sale_active", columnList = "is_active"),
    @Index(name = "idx_flash_sale_created", columnList = "created_at")
})
public class FlashSale extends BaseEntity {

    @NotBlank
    @Size(max = 250)
    @Column(name = "name", nullable = false)
    private String name;

    @Column(name = "description", columnDefinition = "TEXT")
    private String description;

    @NotNull
    @Column(name = "spu_id", nullable = false, columnDefinition = "CHAR(36)")
    private UUID spuId;

    @NotNull
    @Min(1)
    @Column(name = "total_sale_limit", nullable = false)
    private Integer totalSaleLimit;

    @Column(name = "sold_quantity", nullable = false)
    private Integer soldQuantity = 0;

    @Min(1)
    @Column(name = "max_quantity_per_customer", nullable = false)
    private Integer maxQuantityPerCustomer = 1;

    @NotNull
    @Column(name = "flash_price", precision = 10, scale = 2, nullable = false)
    private BigDecimal flashPrice;

    @NotNull
    @Column(name = "start_time", nullable = false)
    private LocalDateTime startTime;

    @NotNull
    @Column(name = "end_time", nullable = false)
    private LocalDateTime endTime;

    @Size(max = 20)
    @Column(name = "status", nullable = false, length = 20)
    private String status = "scheduled";

    @Column(name = "is_active", nullable = false)
    private Boolean isActive = true;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "spu_id", insertable = false, updatable = false)
    private Spu spu;

    // Constructors
    public FlashSale() {}

    public FlashSale(String name, UUID spuId, Integer totalSaleLimit,
                     BigDecimal flashPrice, LocalDateTime startTime, LocalDateTime endTime) {
        this.name = name;
        this.spuId = spuId;
        this.totalSaleLimit = totalSaleLimit;
        this.flashPrice = flashPrice;
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
        return isActive && "active".equals(status) && isTimeActive() && getRemainingQuantity() > 0;
    }

    public Double getPercentageSold() {
        if (totalSaleLimit == 0) return 0.0;
        return (soldQuantity * 100.0) / totalSaleLimit;
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

    public BigDecimal getFlashPrice() {
        return flashPrice;
    }

    public void setFlashPrice(BigDecimal flashPrice) {
        this.flashPrice = flashPrice;
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

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
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

    @Override
    public String toString() {
        return name + " (" + status + ")";
    }
}
