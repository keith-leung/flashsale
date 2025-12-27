package com.flashsale.api.controller;

import com.flashsale.api.dto.OrderDtos.*;
import com.flashsale.api.service.OrderService;
import com.flashsale.api.service.OrderServiceVariantX;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.domain.Page;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.UUID;

@RestController
@RequestMapping("/api/v1/orders")
@Tag(name = "Order Management", description = "Order management operations (Variant X - Redis-Optimized)")
public class OrderController {

    private final OrderService orderService;
    private final OrderServiceVariantX orderServiceVariantX;

    @Autowired
    public OrderController(OrderService orderService, OrderServiceVariantX orderServiceVariantX) {
        this.orderService = orderService;
        this.orderServiceVariantX = orderServiceVariantX;
    }

    @GetMapping
    @Operation(summary = "Get all orders", description = "Retrieve a paginated list of all orders")
    @ApiResponses(value = {
        @ApiResponse(responseCode = "200", description = "Successfully retrieved orders")
    })
    public ResponseEntity<Page<OrderResponseDto>> getAllOrders(
            @Parameter(description = "Page number (0-based)")
            @RequestParam(defaultValue = "0") int page,
            @Parameter(description = "Page size")
            @RequestParam(defaultValue = "20") int size,
            @Parameter(description = "Filter by customer email")
            @RequestParam(required = false) String customerEmail) {
        
        Page<OrderResponseDto> orders = orderService.getAllOrders(page, size, customerEmail);
        return ResponseEntity.ok(orders);
    }

    @GetMapping("/{id}")
    @Operation(summary = "Get order by ID", description = "Retrieve a specific order by its ID")
    @ApiResponses(value = {
        @ApiResponse(responseCode = "200", description = "Successfully retrieved order"),
        @ApiResponse(responseCode = "404", description = "Order not found")
    })
    public ResponseEntity<OrderResponseDto> getOrderById(
            @Parameter(description = "Order ID")
            @PathVariable UUID id) {
        
        return orderService.getOrderById(id)
                .map(order -> ResponseEntity.ok(order))
                .orElse(ResponseEntity.notFound().build());
    }

    @PostMapping
    @Operation(summary = "Create new order", description = "Create a new order (Variant X: Redis-optimized)")
    @ApiResponses(value = {
        @ApiResponse(responseCode = "201", description = "Successfully created order"),
        @ApiResponse(responseCode = "400", description = "Invalid input or insufficient stock")
    })
    public ResponseEntity<OrderResponseDto> createOrder(
            @Parameter(description = "Order creation data")
            @Valid @RequestBody OrderCreateDto createDto) {

        try {
            // Use Variant X service with Redis optimization
            OrderResponseDto createdOrder = orderServiceVariantX.createOrder(createDto);
            return ResponseEntity.status(HttpStatus.CREATED).body(createdOrder);
        } catch (IllegalArgumentException | IllegalStateException e) {
            return ResponseEntity.badRequest().build();
        }
    }

    @PutMapping("/{id}/status")
    @Operation(summary = "Update order status", description = "Update the status of an existing order")
    @ApiResponses(value = {
        @ApiResponse(responseCode = "200", description = "Successfully updated order status"),
        @ApiResponse(responseCode = "400", description = "Invalid status"),
        @ApiResponse(responseCode = "404", description = "Order not found")
    })
    public ResponseEntity<OrderResponseDto> updateOrderStatus(
            @Parameter(description = "Order ID")
            @PathVariable UUID id,
            @Parameter(description = "New status")
            @RequestBody String status) {
        
        try {
            return orderService.updateOrderStatus(id, status)
                    .map(order -> ResponseEntity.ok(order))
                    .orElse(ResponseEntity.notFound().build());
        } catch (IllegalArgumentException e) {
            return ResponseEntity.badRequest().build();
        }
    }

    @DeleteMapping("/{id}")
    @Operation(summary = "Cancel order", description = "Cancel an existing order")
    @ApiResponses(value = {
        @ApiResponse(responseCode = "204", description = "Order cancelled successfully"),
        @ApiResponse(responseCode = "404", description = "Order not found")
    })
    public ResponseEntity<Void> cancelOrder(
            @Parameter(description = "Order ID")
            @PathVariable UUID id) {
        
        boolean cancelled = orderService.cancelOrder(id);
        return cancelled ? ResponseEntity.noContent().build() : ResponseEntity.notFound().build();
    }

    @PostMapping("/{orderId}/payments")
    @Operation(summary = "Create payment", description = "Create a payment for an order")
    @ApiResponses(value = {
        @ApiResponse(responseCode = "201", description = "Payment created successfully"),
        @ApiResponse(responseCode = "400", description = "Invalid payment data"),
        @ApiResponse(responseCode = "404", description = "Order not found")
    })
    public ResponseEntity<PaymentResponseDto> createPayment(
            @Parameter(description = "Order ID")
            @PathVariable UUID orderId,
            @Parameter(description = "Payment data")
            @Valid @RequestBody PaymentCreateDto dto) {
        
        try {
            PaymentResponseDto payment = orderService.createPayment(orderId, dto);
            return ResponseEntity.status(HttpStatus.CREATED).body(payment);
        } catch (IllegalArgumentException e) {
            return ResponseEntity.badRequest().build();
        }
    }
}
