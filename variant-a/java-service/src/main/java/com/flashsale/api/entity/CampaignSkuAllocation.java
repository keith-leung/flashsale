package com.flashsale.api.entity;

import jakarta.persistence.*;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.UUID;

/**
 * Pre-allocated inventory units for flash sale campaigns
 * Each unit represents a chunk of inventory (e.g., 500 items) that can be claimed by a service instance
 */
@Entity
@Table(name = "campaign_sku_allocations", indexes = {
    @Index(name = "idx_campaign_sku", columnList = "campaignId, skuId"),
    @Index(name = "idx_status", columnList = "status")
})
public class CampaignSkuAllocation {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @NotNull
    @Column(nullable = false, length = 36)
    private UUID campaignId;

    @NotNull
    @Column(nullable = false, length = 36)
    private UUID skuId;

    @Min(1)
    @Column(nullable = false)
    private Integer allocatedQuantity; // e.g., 500

    @Min(1)
    @Column(nullable = false)
    private Integer refillBatchSize; // e.g., 50

    @NotNull
    @Column(nullable = false, precision = 5, scale = 2)
    private BigDecimal lowWaterMarkPct; // e.g., 30.00

    @Column(length = 100)
    private String claimedBy; // Service instance ID

    @Column
    private LocalDateTime claimedAt;

    @NotNull
    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    private AllocationStatus status = AllocationStatus.available;

    @Column(nullable = false, updatable = false)
    private LocalDateTime createdAt;

    @Column(nullable = false)
    private LocalDateTime updatedAt;

    // Constructors
    public CampaignSkuAllocation() {
        this.createdAt = LocalDateTime.now();
        this.updatedAt = LocalDateTime.now();
    }

    public CampaignSkuAllocation(UUID campaignId, UUID skuId, Integer allocatedQuantity,
                                 Integer refillBatchSize, BigDecimal lowWaterMarkPct) {
        this.campaignId = campaignId;
        this.skuId = skuId;
        this.allocatedQuantity = allocatedQuantity;
        this.refillBatchSize = refillBatchSize;
        this.lowWaterMarkPct = lowWaterMarkPct;
        this.createdAt = LocalDateTime.now();
        this.updatedAt = LocalDateTime.now();
    }

    @PreUpdate
    protected void onUpdate() {
        this.updatedAt = LocalDateTime.now();
    }

    // Getters and Setters
    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public UUID getCampaignId() {
        return campaignId;
    }

    public void setCampaignId(UUID campaignId) {
        this.campaignId = campaignId;
    }

    public UUID getSkuId() {
        return skuId;
    }

    public void setSkuId(UUID skuId) {
        this.skuId = skuId;
    }

    public Integer getAllocatedQuantity() {
        return allocatedQuantity;
    }

    public void setAllocatedQuantity(Integer allocatedQuantity) {
        this.allocatedQuantity = allocatedQuantity;
    }

    public Integer getRefillBatchSize() {
        return refillBatchSize;
    }

    public void setRefillBatchSize(Integer refillBatchSize) {
        this.refillBatchSize = refillBatchSize;
    }

    public BigDecimal getLowWaterMarkPct() {
        return lowWaterMarkPct;
    }

    public void setLowWaterMarkPct(BigDecimal lowWaterMarkPct) {
        this.lowWaterMarkPct = lowWaterMarkPct;
    }

    public String getClaimedBy() {
        return claimedBy;
    }

    public void setClaimedBy(String claimedBy) {
        this.claimedBy = claimedBy;
    }

    public LocalDateTime getClaimedAt() {
        return claimedAt;
    }

    public void setClaimedAt(LocalDateTime claimedAt) {
        this.claimedAt = claimedAt;
    }

    public AllocationStatus getStatus() {
        return status;
    }

    public void setStatus(AllocationStatus status) {
        this.status = status;
    }

    public LocalDateTime getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(LocalDateTime createdAt) {
        this.createdAt = createdAt;
    }

    public LocalDateTime getUpdatedAt() {
        return updatedAt;
    }

    public void setUpdatedAt(LocalDateTime updatedAt) {
        this.updatedAt = updatedAt;
    }

    @Override
    public String toString() {
        return "CampaignSkuAllocation{" +
                "id=" + id +
                ", campaignId=" + campaignId +
                ", skuId=" + skuId +
                ", allocatedQuantity=" + allocatedQuantity +
                ", claimedBy='" + claimedBy + '\'' +
                ", status=" + status +
                '}';
    }
}
