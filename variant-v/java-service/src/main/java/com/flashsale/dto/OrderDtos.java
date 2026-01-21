package com.flashsale.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;
import java.math.BigDecimal;
import java.time.LocalDateTime;

public class OrderDtos {
    
    @Data
    public static class OrderCreateRequest {
        private String customerEmail;
        private String skuId;
        private Integer quantity;
        private BigDecimal unitPrice;
        private String flashSaleCampaignId;
    }
    
    @Data
    public static class OrderCreateResponse {
        private String auditId;
        private String orderId;
        private String status;
        private String message;
    }
    
    @Data
    public static class OrderStatusResponse {
        private String auditId;
        private String status;
        private LocalDateTime createdAt;
    }
}
