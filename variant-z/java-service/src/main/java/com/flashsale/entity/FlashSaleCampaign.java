package com.flashsale.entity;

import jakarta.persistence.*;

import java.time.Instant;

/**
 * Flash sale campaign entity - Variant Z.
 */
@Entity
@Table(name = "flash_sale_campaigns")
public class FlashSaleCampaign {

    @Id
    @Column(name = "id", updatable = false, nullable = false)
    private String id;

    @Column(name = "spu_id", nullable = false)
    private String spuId;

    @Column(name = "name", nullable = false)
    private String name;

    @Column(name = "description", columnDefinition = "TEXT")
    private String description;

    @Column(name = "start_time", nullable = false)
    private Instant startTime;

    @Column(name = "end_time", nullable = false)
    private Instant endTime;

    @Column(name = "total_sale_limit", nullable = false)
    private Integer totalSaleLimit;

    @Column(name = "sold_quantity", nullable = false)
    private Integer soldQuantity;

    @Column(name = "is_active", nullable = false)
    private Boolean isActive;

    @Column(name = "status", nullable = false, length = 20)
    private String status;

    @Column(name = "created_at", updatable = false)
    private Instant createdAt;

    @Column(name = "updated_at")
    private Instant updatedAt;

    // Default constructor
    public FlashSaleCampaign() {
        this.createdAt = Instant.now();
        this.updatedAt = Instant.now();
        this.soldQuantity = 0;
        this.isActive = true;
    }

    // Getters and Setters
    public String getId() { return id; }
    public void setId(String id) { this.id = id; }
    public String getSpuId() { return spuId; }
    public void setSpuId(String spuId) { this.spuId = spuId; }
    public String getName() { return name; }
    public void setName(String name) { this.name = name; }
    public String getDescription() { return description; }
    public void setDescription(String description) { this.description = description; }
    public Instant getStartTime() { return startTime; }
    public void setStartTime(Instant startTime) { this.startTime = startTime; }
    public Instant getEndTime() { return endTime; }
    public void setEndTime(Instant endTime) { this.endTime = endTime; }
    public Integer getTotalSaleLimit() { return totalSaleLimit; }
    public void setTotalSaleLimit(Integer totalSaleLimit) { this.totalSaleLimit = totalSaleLimit; }
    public Integer getSoldQuantity() { return soldQuantity; }
    public void setSoldQuantity(Integer soldQuantity) { this.soldQuantity = soldQuantity; }
    public Boolean getIsActive() { return isActive; }
    public void setIsActive(Boolean isActive) { this.isActive = isActive; }
    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }
    public Instant getCreatedAt() { return createdAt; }
    public void setCreatedAt(Instant createdAt) { this.createdAt = createdAt; }
    public Instant getUpdatedAt() { return updatedAt; }
    public void setUpdatedAt(Instant updatedAt) { this.updatedAt = updatedAt; }

    @PreUpdate
    public void preUpdate() {
        this.updatedAt = Instant.now();
    }
}