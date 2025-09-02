package com.flashsale.api.dto;

import com.flashsale.api.entity.OrderStatus;
import com.flashsale.api.entity.PaymentStatus;
import jakarta.validation.Valid;
import jakarta.validation.constraints.*;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;
import java.util.UUID;

public class OrderDtos {

    public static class OrderLineItemCreateDto {
        @NotNull
        private UUID skuId;

        @Min(1)
        private Integer quantity;

        @Positive
        @Digits(integer = 8, fraction = 2)
        private BigDecimal unitPrice;

        // Constructors
        public OrderLineItemCreateDto() {}

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

        public BigDecimal getUnitPrice() {
            return unitPrice;
        }

        public void setUnitPrice(BigDecimal unitPrice) {
            this.unitPrice = unitPrice;
        }
    }

    public static class OrderLineItemResponseDto {
        private UUID id;
        private UUID skuId;
        private Integer quantity;
        private BigDecimal unitPrice;
        private BigDecimal totalPrice;
        private String productName;
        private String skuCode;
        private LocalDateTime createdAt;

        // Constructors
        public OrderLineItemResponseDto() {}

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

        public BigDecimal getUnitPrice() {
            return unitPrice;
        }

        public void setUnitPrice(BigDecimal unitPrice) {
            this.unitPrice = unitPrice;
        }

        public BigDecimal getTotalPrice() {
            return totalPrice;
        }

        public void setTotalPrice(BigDecimal totalPrice) {
            this.totalPrice = totalPrice;
        }

        public String getProductName() {
            return productName;
        }

        public void setProductName(String productName) {
            this.productName = productName;
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
    }

    public static class OrderCreateDto {
        @NotBlank
        @Email
        private String customerEmail;

        private String customerName;

        @PositiveOrZero
        @Digits(integer = 8, fraction = 2)
        private BigDecimal taxAmount = BigDecimal.ZERO;

        @PositiveOrZero
        @Digits(integer = 8, fraction = 2)
        private BigDecimal shippingAmount = BigDecimal.ZERO;

        @NotBlank
        @Size(min = 3, max = 3)
        private String currency = "USD";

        private String notes;

        private UUID flashSaleId;

        @NotEmpty
        @Valid
        private List<OrderLineItemCreateDto> lineItems;

        // Constructors
        public OrderCreateDto() {}

        // Getters and Setters
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

        public BigDecimal getTaxAmount() {
            return taxAmount;
        }

        public void setTaxAmount(BigDecimal taxAmount) {
            this.taxAmount = taxAmount;
        }

        public BigDecimal getShippingAmount() {
            return shippingAmount;
        }

        public void setShippingAmount(BigDecimal shippingAmount) {
            this.shippingAmount = shippingAmount;
        }

        public String getCurrency() {
            return currency;
        }

        public void setCurrency(String currency) {
            this.currency = currency;
        }

        public String getNotes() {
            return notes;
        }

        public void setNotes(String notes) {
            this.notes = notes;
        }

        public UUID getFlashSaleId() {
            return flashSaleId;
        }

        public void setFlashSaleId(UUID flashSaleId) {
            this.flashSaleId = flashSaleId;
        }

        public List<OrderLineItemCreateDto> getLineItems() {
            return lineItems;
        }

        public void setLineItems(List<OrderLineItemCreateDto> lineItems) {
            this.lineItems = lineItems;
        }
    }

    public static class OrderUpdateDto {
        private String customerName;
        private OrderStatus status;
        private String notes;

        // Constructors
        public OrderUpdateDto() {}

        // Getters and Setters
        public String getCustomerName() {
            return customerName;
        }

        public void setCustomerName(String customerName) {
            this.customerName = customerName;
        }

        public OrderStatus getStatus() {
            return status;
        }

        public void setStatus(OrderStatus status) {
            this.status = status;
        }

        public String getNotes() {
            return notes;
        }

        public void setNotes(String notes) {
            this.notes = notes;
        }
    }

    public static class OrderResponseDto {
        private UUID id;
        private String orderNumber;
        private String customerEmail;
        private String customerName;
        private BigDecimal subtotal;
        private BigDecimal taxAmount;
        private BigDecimal shippingAmount;
        private BigDecimal totalAmount;
        private String currency;
        private OrderStatus status;
        private String notes;
        private UUID flashSaleId;
        private LocalDateTime createdAt;
        private LocalDateTime updatedAt;
        private List<OrderLineItemResponseDto> lineItems;

        // Constructors
        public OrderResponseDto() {}

        // Getters and Setters
        public UUID getId() {
            return id;
        }

        public void setId(UUID id) {
            this.id = id;
        }

        public String getOrderNumber() {
            return orderNumber;
        }

        public void setOrderNumber(String orderNumber) {
            this.orderNumber = orderNumber;
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

        public BigDecimal getSubtotal() {
            return subtotal;
        }

        public void setSubtotal(BigDecimal subtotal) {
            this.subtotal = subtotal;
        }

        public BigDecimal getTaxAmount() {
            return taxAmount;
        }

        public void setTaxAmount(BigDecimal taxAmount) {
            this.taxAmount = taxAmount;
        }

        public BigDecimal getShippingAmount() {
            return shippingAmount;
        }

        public void setShippingAmount(BigDecimal shippingAmount) {
            this.shippingAmount = shippingAmount;
        }

        public BigDecimal getTotalAmount() {
            return totalAmount;
        }

        public void setTotalAmount(BigDecimal totalAmount) {
            this.totalAmount = totalAmount;
        }

        public String getCurrency() {
            return currency;
        }

        public void setCurrency(String currency) {
            this.currency = currency;
        }

        public OrderStatus getStatus() {
            return status;
        }

        public void setStatus(OrderStatus status) {
            this.status = status;
        }

        public String getNotes() {
            return notes;
        }

        public void setNotes(String notes) {
            this.notes = notes;
        }

        public UUID getFlashSaleId() {
            return flashSaleId;
        }

        public void setFlashSaleId(UUID flashSaleId) {
            this.flashSaleId = flashSaleId;
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

        public List<OrderLineItemResponseDto> getLineItems() {
            return lineItems;
        }

        public void setLineItems(List<OrderLineItemResponseDto> lineItems) {
            this.lineItems = lineItems;
        }
    }

    public static class PaymentCreateDto {
        @NotNull
        @Positive
        @Digits(integer = 8, fraction = 2)
        private BigDecimal amount;

        @NotBlank
        @Size(min = 3, max = 3)
        private String currency = "USD";

        @NotBlank
        private String paymentMethod;

        private String referenceNumber;
        private String notes;

        // Constructors
        public PaymentCreateDto() {}

        // Getters and Setters
        public BigDecimal getAmount() {
            return amount;
        }

        public void setAmount(BigDecimal amount) {
            this.amount = amount;
        }

        public String getCurrency() {
            return currency;
        }

        public void setCurrency(String currency) {
            this.currency = currency;
        }

        public String getPaymentMethod() {
            return paymentMethod;
        }

        public void setPaymentMethod(String paymentMethod) {
            this.paymentMethod = paymentMethod;
        }

        public String getReferenceNumber() {
            return referenceNumber;
        }

        public void setReferenceNumber(String referenceNumber) {
            this.referenceNumber = referenceNumber;
        }

        public String getNotes() {
            return notes;
        }

        public void setNotes(String notes) {
            this.notes = notes;
        }
    }

    public static class PaymentResponseDto {
        private UUID id;
        private UUID orderId;
        private BigDecimal amount;
        private String currency;
        private String paymentMethod;
        private String gatewayTransactionId;
        private PaymentStatus status;
        private String referenceNumber;
        private String notes;
        private LocalDateTime createdAt;
        private LocalDateTime updatedAt;

        // Constructors
        public PaymentResponseDto() {}

        // Getters and Setters
        public UUID getId() {
            return id;
        }

        public void setId(UUID id) {
            this.id = id;
        }

        public UUID getOrderId() {
            return orderId;
        }

        public void setOrderId(UUID orderId) {
            this.orderId = orderId;
        }

        public BigDecimal getAmount() {
            return amount;
        }

        public void setAmount(BigDecimal amount) {
            this.amount = amount;
        }

        public String getCurrency() {
            return currency;
        }

        public void setCurrency(String currency) {
            this.currency = currency;
        }

        public String getPaymentMethod() {
            return paymentMethod;
        }

        public void setPaymentMethod(String paymentMethod) {
            this.paymentMethod = paymentMethod;
        }

        public String getGatewayTransactionId() {
            return gatewayTransactionId;
        }

        public void setGatewayTransactionId(String gatewayTransactionId) {
            this.gatewayTransactionId = gatewayTransactionId;
        }

        public PaymentStatus getStatus() {
            return status;
        }

        public void setStatus(PaymentStatus status) {
            this.status = status;
        }

        public String getReferenceNumber() {
            return referenceNumber;
        }

        public void setReferenceNumber(String referenceNumber) {
            this.referenceNumber = referenceNumber;
        }

        public String getNotes() {
            return notes;
        }

        public void setNotes(String notes) {
            this.notes = notes;
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
