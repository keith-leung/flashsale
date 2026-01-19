package com.flashsale.api.controller;

import com.flashsale.service.OrderService;
import com.flashsale.service.TokenService;
import com.flashsale.service.dto.OrderRequest;
import com.flashsale.service.dto.OrderResponse;
import com.flashsale.service.dto.FlashSaleSoldOutResponse;
import com.flashsale.service.dto.InsufficientStockResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

/**
 * Orders API controller - Variant Z (Token Pre-Allocation with Synchronous Persistence).
 */
@RestController
@RequestMapping("/api/v1/orders")
public class OrderController {

    private static final Logger logger = LoggerFactory.getLogger(OrderController.class);

    private final OrderService orderService;
    private final TokenService tokenService;

    public OrderController(OrderService orderService, TokenService tokenService) {
        this.orderService = orderService;
        this.tokenService = tokenService;
    }

    /**
     * Create order with token pre-allocation (Variant Z).
     * 
     * Handles both regular orders and flash sale orders:
     * - Flash sale: Use Redis token acquisition
     * - Regular: Use database transactions (Variant Y path)
     */
    @PostMapping
    public ResponseEntity<OrderResponse> createOrder(@RequestBody OrderRequest orderRequest) {
        try {
            OrderResponse response = orderService.createOrder(orderRequest);
            return ResponseEntity.status(HttpStatus.CREATED).body(response);
        } catch (Exception e) {
            logger.error("Order creation failed: {}", e.getMessage(), e);
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).build();
        }
    }

    /**
     * Test endpoint to verify order creation.
     */
    @GetMapping("/test-data")
    public ResponseEntity<Map<String, Object>> testOrderData() {
        return ResponseEntity.ok(Map.of(
            "message", "Variant Z - Token Pre-Allocation",
            "endpoints", Map.of(
                "POST /api/v1/orders", "Create order (with or without flash sale)",
                "GET /api/v1/orders/test-data", "This endpoint"
            ),
            "architecture", Map.of(
                "token_pre_allocation", true,
                "redis_enabled", true,
                "synchronous_database_persistence", true,
                "wal_pattern", false,
                "description", "Pre-allocate tokens in Redis, acquire atomically via Lua, persist synchronously to database"
            )
        ));
    }
}