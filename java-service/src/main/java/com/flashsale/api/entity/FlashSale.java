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
@Table(name = "flash_sales", indexes = {
    @Index(name = "idx_flash_sale_spu", columnList = "spu_id"),
    @Index(name = "idx_flash_sale_status", columnList = "status"),
    @Index(name = "idx_flash_sale_start", columnList = "start_time"),
    @Index(name = "idx_flash_sale_end", columnList = "end_time")
})
public class FlashSale extends BaseEntity {

    @NotBlank
    @Size(max = 255)
    @Column(name = "campaign_name", nullable = false)
    private String campaignName;

    @NotNull
    @Column(name = "spu_id", nullable = false, columnDefinition = "CHAR(36)")
    private UUID spuId;

    @NotNull
    @Min(1)
    @Column(name = "total_sale_limit", nullable = false)
    private Integer totalSaleLimit;

    @Column(name = "sold_count", nullable = false)
    private Integer soldCount = 0;

    @NotNull
    @Column(name = "start_time", nullable = false)
    private LocalDateTime startTime;

    @NotNull
    @Column(name = "end_time", nullable = false)
    private LocalDateTime endTime;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    private FlashSaleCampaignStatus status = FlashSaleCampaignStatus.pending;

    @Column(name = "flash_sale_price", precision = 10, scale = 2)
    private BigDecimal flashSalePrice;

    @Min(1)
    @Column(name = "max_per_order", nullable = false)
    private Integer maxPerOrder = 10;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "spu_id", insertable = false, updatable = false)
    private Spu spu;

    // Constructors
    public FlashSale() {}

    public FlashSale(String campaignName, UUID spuId, Integer totalSaleLimit,
                     LocalDateTime startTime, LocalDateTime endTime) {
        this.campaignName = campaignName;
        this.spuId = spuId;
        this.totalSaleLimit = totalSaleLimit;
        this.startTime = startTime;
        this.endTime = endTime;
    }

    // Business logic methods
    public Integer getRemainingQuantity() {
        return Math.max(0, totalSaleLimit - soldCount);
    }

    public boolean isTimeActive() {
        LocalDateTime now = LocalDateTime.now();
        return !startTime.isAfter(now) && !endTime.isBefore(now);
    }

    public boolean isAvailable() {
        return status == FlashSaleCampaignStatus.active && isTimeActive() && getRemainingQuantity() > 0;
    }

    public Double getPercentageSold() {
        if (totalSaleLimit == 0) return 0.0;
        return (soldCount * 100.0) / totalSaleLimit;
    }

    // Getters and Setters
    public String getCampaignName() {
        return campaignName;
    }

    public void setCampaignName(String campaignName) {
        this.campaignName = campaignName;
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

    public Integer getSoldCount() {
        return soldCount;
    }

    public void setSoldCount(Integer soldCount) {
        this.soldCount = soldCount;
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

    public FlashSaleCampaignStatus getStatus() {
        return status;
    }

    public void setStatus(FlashSaleCampaignStatus status) {
        this.status = status;
    }

    public BigDecimal getFlashSalePrice() {
        return flashSalePrice;
    }

    public void setFlashSalePrice(BigDecimal flashSalePrice) {
        this.flashSalePrice = flashSalePrice;
    }

    public Integer getMaxPerOrder() {
        return maxPerOrder;
    }

    public void setMaxPerOrder(Integer maxPerOrder) {
        this.maxPerOrder = maxPerOrder;
    }

    public Spu getSpu() {
        return spu;
    }

    public void setSpu(Spu spu) {
        this.spu = spu;
    }

    @Override
    public String toString() {
        return campaignName + " (" + status + ")";
    }
}
