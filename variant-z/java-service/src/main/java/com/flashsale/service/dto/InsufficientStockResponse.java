package com.flashsale.service.dto;

/**
 * Insufficient stock response DTO.
 */
public class InsufficientStockResponse {

    private String skuId;
    private Integer available;
    private String message = "Insufficient stock available";

    public InsufficientStockResponse() {}

    public InsufficientStockResponse(String skuId, Integer available) {
        this.skuId = skuId;
        this.available = available;
    }

    // Getters and Setters
    public String getSkuId() {
        return skuId;
    }

    public void setSkuId(String skuId) {
        this.skuId = skuId;
    }

    public Integer getAvailable() {
        return available;
    }

    public void setAvailable(Integer available) {
        this.available = available;
    }

    public String getMessage() {
        return message;
    }

    public void setMessage(String message) {
        this.message = message;
    }
}