package com.flashsale.api.dto;

import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;

import java.time.LocalDateTime;
import java.util.UUID;

public class InventoryDtos {

    public static class InventoryCreateDto {
        @NotNull(message = "SKU ID is required")
        private UUID skuId;

        @Min(value = 0, message = "Quantity must be non-negative")
        private Integer quantity = 0;

        @Min(value = 0, message = "Reserved quantity must be non-negative")
        private Integer reservedQuantity = 0;

        private Boolean allowNegativeStock = false;

        // Constructors
        public InventoryCreateDto() {}

        public InventoryCreateDto(UUID skuId, Integer quantity) {
            this.skuId = skuId;
            this.quantity = quantity;
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
    }

    public static class InventoryUpdateDto {
        @Min(value = 0, message = "Quantity must be non-negative")
        private Integer quantity;

        @Min(value = 0, message = "Reserved quantity must be non-negative")
        private Integer reservedQuantity;

        private Boolean allowNegativeStock;

        // Constructors
        public InventoryUpdateDto() {}

        // Getters and Setters
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
    }

    public static class InventoryResponseDto {
        private UUID id;
        private UUID skuId;
        private Integer quantity;
        private Integer reservedQuantity;
        private Integer availableQuantity;
        private Boolean allowNegativeStock;
        private String skuCode;
        private LocalDateTime createdAt;
        private LocalDateTime updatedAt;

        // Constructors
        public InventoryResponseDto() {}

        // Getters and Setters
        public UUID getId() {
            return id;
        }

        public void setId(UUID id) {
            this.id = id;
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
        }

        public Integer getReservedQuantity() {
            return reservedQuantity;
        }

        public void setReservedQuantity(Integer reservedQuantity) {
            this.reservedQuantity = reservedQuantity;
        }

        public Integer getAvailableQuantity() {
            return availableQuantity;
        }

        public void setAvailableQuantity(Integer availableQuantity) {
            this.availableQuantity = availableQuantity;
        }

        public Boolean getAllowNegativeStock() {
            return allowNegativeStock;
        }

        public void setAllowNegativeStock(Boolean allowNegativeStock) {
            this.allowNegativeStock = allowNegativeStock;
        }

        public String getSkuCode() {
            return skuCode;
        }

        public void setSkuCode(String skuCode) {
            this.skuCode = skuCode;
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
