package com.flashsale.api.dto;

import com.flashsale.api.entity.FlashSaleStatus;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

import java.time.LocalDateTime;
import java.util.UUID;

public class FlashSaleDtos {

    public static class FlashSaleCampaignCreateDto {
        @NotBlank(message = "Name is required")
        @Size(max = 250, message = "Name must not exceed 250 characters")
        private String name;

        private String description;

        @NotNull(message = "SKU ID is required")
        private UUID spuId;

        @NotNull(message = "Total sale limit is required")
        @Min(value = 1, message = "Total sale limit must be at least 1")
        private Integer totalSaleLimit;

        @Min(value = 1, message = "Max quantity per customer must be at least 1")
        private Integer maxQuantityPerCustomer = 1;

        @NotNull(message = "Start time is required")
        private LocalDateTime startTime;

        @NotNull(message = "End time is required")
        private LocalDateTime endTime;

        private Boolean isActive = true;

        // Constructors
        public FlashSaleCampaignCreateDto() {}

        public FlashSaleCampaignCreateDto(String name, UUID spuId, Integer totalSaleLimit, LocalDateTime startTime, LocalDateTime endTime) {
            this.name = name;
            this.spuId = spuId;
            this.totalSaleLimit = totalSaleLimit;
            this.startTime = startTime;
            this.endTime = endTime;
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

        public Boolean getIsActive() {
            return isActive;
        }

        public void setIsActive(Boolean isActive) {
            this.isActive = isActive;
        }
    }

    public static class FlashSaleCampaignUpdateDto {
        @Size(max = 250, message = "Name must not exceed 250 characters")
        private String name;

        private String description;

        @Min(value = 1, message = "Total sale limit must be at least 1")
        private Integer totalSaleLimit;

        @Min(value = 1, message = "Max quantity per customer must be at least 1")
        private Integer maxQuantityPerCustomer;

        private LocalDateTime startTime;

        private LocalDateTime endTime;

        private FlashSaleStatus status;

        private Boolean isActive;

        // Constructors
        public FlashSaleCampaignUpdateDto() {}

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

        public Integer getTotalSaleLimit() {
            return totalSaleLimit;
        }

        public void setTotalSaleLimit(Integer totalSaleLimit) {
            this.totalSaleLimit = totalSaleLimit;
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
    }

    public static class FlashSaleCampaignResponseDto {
        private UUID id;
        private String name;
        private String description;
        private UUID spuId;
        private String skuCode;
        private Integer totalSaleLimit;
        private Integer soldQuantity;
        private Integer remainingQuantity;
        private Integer maxQuantityPerCustomer;
        private LocalDateTime startTime;
        private LocalDateTime endTime;
        private FlashSaleStatus status;
        private Boolean isActive;
        private Boolean isAvailable;
        private LocalDateTime createdAt;
        private LocalDateTime updatedAt;

        // Constructors
        public FlashSaleCampaignResponseDto() {}

        // Getters and Setters
        public UUID getId() {
            return id;
        }

        public void setId(UUID id) {
            this.id = id;
        }

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

        public String getSkuCode() {
            return skuCode;
        }

        public void setSkuCode(String skuCode) {
            this.skuCode = skuCode;
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

        public Integer getRemainingQuantity() {
            return remainingQuantity;
        }

        public void setRemainingQuantity(Integer remainingQuantity) {
            this.remainingQuantity = remainingQuantity;
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

        public Boolean getIsAvailable() {
            return isAvailable;
        }

        public void setIsAvailable(Boolean isAvailable) {
            this.isAvailable = isAvailable;
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

    public static class PurchaseRequestDto {
        @NotNull(message = "Quantity is required")
        @Min(value = 1, message = "Quantity must be at least 1")
        private Integer quantity;

        @NotBlank(message = "Customer email is required")
        private String customerEmail;

        private String customerName;

        // Constructors
        public PurchaseRequestDto() {}

        public PurchaseRequestDto(Integer quantity, String customerEmail) {
            this.quantity = quantity;
            this.customerEmail = customerEmail;
        }

        // Getters and Setters
        public Integer getQuantity() {
            return quantity;
        }

        public void setQuantity(Integer quantity) {
            this.quantity = quantity;
        }

        public String getCustomerEmail() {
            return customerEmail;
        }

        public void setCustomerEmail(String customerEmail) {
            this.customerEmail = customerEmail;
        }

        public String getCustomerName() {
            return customerName;
        }

        public void setCustomerName(String customerName) {
            this.customerName = customerName;
        }
    }

    public static class PurchaseResponseDto {
        private Boolean success;
        private String message;
        private UUID orderId;
        private Integer quantityPurchased;
        private Integer remainingQuantity;

        // Constructors
        public PurchaseResponseDto() {}

        public PurchaseResponseDto(Boolean success, String message) {
            this.success = success;
            this.message = message;
        }

        // Getters and Setters
        public Boolean getSuccess() {
            return success;
        }

        public void setSuccess(Boolean success) {
            this.success = success;
        }

        public String getMessage() {
            return message;
        }

        public void setMessage(String message) {
            this.message = message;
        }

        public UUID getOrderId() {
            return orderId;
        }

        public void setOrderId(UUID orderId) {
            this.orderId = orderId;
        }

        public Integer getQuantityPurchased() {
            return quantityPurchased;
        }

        public void setQuantityPurchased(Integer quantityPurchased) {
            this.quantityPurchased = quantityPurchased;
        }

        public Integer getRemainingQuantity() {
            return remainingQuantity;
        }

        public void setRemainingQuantity(Integer remainingQuantity) {
            this.remainingQuantity = remainingQuantity;
        }
    }
}
