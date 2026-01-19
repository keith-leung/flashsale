package com.flashsale.service.dto;

/**
 * Order response DTO.
 */
public class OrderResponse {

    private String orderId;
    private String status;
    private Double totalAmount;
    private String customerEmail;

    public OrderResponse() {}

    public OrderResponse(String orderId, String status, Double totalAmount, String customerEmail) {
        this.orderId = orderId;
        this.status = status;
        this.totalAmount = totalAmount;
        this.customerEmail = customerEmail;
    }

    // Getters and Setters
    public String getOrderId() {
        return orderId;
    }

    public void setOrderId(String orderId) {
        this.orderId = orderId;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public Double getTotalAmount() {
        return totalAmount;
    }

    public void setTotalAmount(Double totalAmount) {
        this.totalAmount = totalAmount;
    }

    public String getCustomerEmail() {
        return customerEmail;
    }

    public void setCustomerEmail(String customerEmail) {
        this.customerEmail = customerEmail;
    }
}