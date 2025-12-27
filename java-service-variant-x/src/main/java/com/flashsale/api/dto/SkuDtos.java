package com.flashsale.api.dto;

import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.UUID;

public class SkuDtos {

    public static class SkuCreateDto {
        @NotBlank(message = "SKU code is required")
        @Size(max = 255, message = "SKU code must not exceed 255 characters")
        private String skuCode;

        @Size(max = 255, message = "Name must not exceed 255 characters")
        private String name;

        @NotNull(message = "SPU ID is required")
        private UUID spuId;

        @NotNull(message = "Price is required")
        @DecimalMin(value = "0.01", message = "Price must be at least 0.01")
        private BigDecimal price;

        @DecimalMin(value = "0.00", message = "Cost price must be non-negative")
        private BigDecimal costPrice;

        @DecimalMin(value = "0.000", message = "Weight must be non-negative")
        private BigDecimal weight;

        private Boolean trackInventory = true;
        private Boolean isActive = true;

        // Constructors
        public SkuCreateDto() {}

        public SkuCreateDto(String skuCode, UUID spuId, BigDecimal price) {
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
    }

    public static class SkuUpdateDto {
        @Size(max = 255, message = "SKU code must not exceed 255 characters")
        private String skuCode;

        @Size(max = 255, message = "Name must not exceed 255 characters")
        private String name;

        @DecimalMin(value = "0.01", message = "Price must be at least 0.01")
        private BigDecimal price;

        @DecimalMin(value = "0.00", message = "Cost price must be non-negative")
        private BigDecimal costPrice;

        @DecimalMin(value = "0.000", message = "Weight must be non-negative")
        private BigDecimal weight;

        private Boolean trackInventory;
        private Boolean isActive;

        // Constructors
        public SkuUpdateDto() {}

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
    }

    public static class SkuResponseDto {
        private UUID id;
        private String skuCode;
        private String name;
        private UUID spuId;
        private String spuName;
        private BigDecimal price;
        private BigDecimal costPrice;
        private BigDecimal weight;
        private Boolean trackInventory;
        private Boolean isActive;
        private Integer availableQuantity;
        private LocalDateTime createdAt;
        private LocalDateTime updatedAt;

        // Constructors
        public SkuResponseDto() {}

        // Getters and Setters
        public UUID getId() {
            return id;
        }

        public void setId(UUID id) {
            this.id = id;
        }

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

        public String getSpuName() {
            return spuName;
        }

        public void setSpuName(String spuName) {
            this.spuName = spuName;
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

        public Integer getAvailableQuantity() {
            return availableQuantity;
        }

        public void setAvailableQuantity(Integer availableQuantity) {
            this.availableQuantity = availableQuantity;
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
    }
}
