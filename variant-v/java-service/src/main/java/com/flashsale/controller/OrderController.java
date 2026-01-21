package com.flashsale.controller;

import com.flashsale.dto.OrderDtos;
import com.flashsale.entity.AuditOrderLog;
import com.flashsale.service.AuditService;
import com.flashsale.service.DistributedLockService;
import org.redisson.api.RedissonClient;
import org.redisson.api.RBucket;
import org.redisson.client.codec.StringCodec;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Collections;


@RestController
@RequestMapping("/api/v1/orders")
public class OrderController {
    
    private static final Logger logger = LoggerFactory.getLogger(OrderController.class);
    
    @Autowired
    private AuditService auditService;
    
    @Autowired
    private DistributedLockService lockService;
    
    @Autowired
    private RedissonClient redissonClient;
    
    @PostMapping
    public ResponseEntity<OrderDtos.OrderCreateResponse> createOrder(@RequestBody OrderDtos.OrderCreateRequest request) {
        OrderDtos.OrderCreateResponse response = new OrderDtos.OrderCreateResponse();
        
        // DEBUG: Force log to verify endpoint is hit
        logger.error("=== DEBUG: OrderController.createOrder() called ===");
        logger.error("Request: customerEmail={}, skuId={}, quantity={}, flashSaleCampaignId={}", 
                     request.getCustomerEmail(), request.getSkuId(), request.getQuantity(), request.getFlashSaleCampaignId());
        
        try {
            // Step 0: Early validation - Check campaign limits BEFORE creating audit
            String campaignKey = "campaign:" + request.getFlashSaleCampaignId() + ":total_sold";
            String totalLimitKey = "campaign:" + request.getFlashSaleCampaignId() + ":total_limit";
            String skuKey = "campaign:" + request.getFlashSaleCampaignId() + ":sku:" + request.getSkuId() + ":remaining";
            
            // Early check: campaign limit - FIX: Use RBucket with proper type
            org.redisson.api.RBucket<String> soldBucket = redissonClient.getBucket(campaignKey);
            org.redisson.api.RBucket<String> limitBucket = redissonClient.getBucket(totalLimitKey);
            String totalSoldStr = soldBucket.get();
            String totalLimitStr = limitBucket.get();
            
            Long totalSold = totalSoldStr != null ? Long.parseLong(totalSoldStr) : 0L;
            Long totalLimit = totalLimitStr != null ? Long.parseLong(totalLimitStr) : 1000L;
            
            if (totalSold >= totalLimit) {
                response.setStatus("FAILED");
                response.setMessage("Campaign sold out");
                return ResponseEntity.status(HttpStatus.CONFLICT).body(response);
            }
            
            // Early check: SKU remaining - FIX: Use RBucket with proper type
            org.redisson.api.RBucket<String> skuBucket = redissonClient.getBucket(skuKey);
            String skuRemainingStr = skuBucket.get();
            Long skuRemaining = skuRemainingStr != null ? Long.parseLong(skuRemainingStr) : 0L;
            
            if (skuRemaining < request.getQuantity()) {
                response.setStatus("FAILED");
                response.setMessage("Insufficient stock");
                return ResponseEntity.status(HttpStatus.CONFLICT).body(response);
            }
            
            // Step 1: Create audit record (write-ahead logging) - only if validation passed
            AuditOrderLog audit = auditService.createAuditRecord(
                request.getCustomerEmail(),
                request.getSkuId(),
                request.getQuantity(),
                request.getUnitPrice(),
                request.getFlashSaleCampaignId()
            );
            
            response.setAuditId(audit.getId());
            response.setOrderId(audit.getOrderId());
            
            // Step 2: Acquire distributed lock for the SKU
            try (DistributedLockService.LockGuard lockGuard = lockService.acquireLock(request.getSkuId().toString())) {
                
                // Re-validate after lock acquisition (double-check pattern)
                totalSoldStr = (String) redissonClient.getBucket(campaignKey, StringCodec.INSTANCE).get();
                totalSold = totalSoldStr != null ? Long.parseLong(totalSoldStr) : 0L;
                
                if (totalSold >= totalLimit) {
                    auditService.failAudit(audit.getId(), "Campaign limit exceeded");
                    response.setStatus("FAILED");
                    response.setMessage("Campaign sold out");
                    return ResponseEntity.status(HttpStatus.CONFLICT).body(response);
                }
                
                skuRemainingStr = (String) redissonClient.getBucket(skuKey, StringCodec.INSTANCE).get();
                skuRemaining = skuRemainingStr != null ? Long.parseLong(skuRemainingStr) : 0L;
                
                if (skuRemaining < request.getQuantity()) {
                    auditService.failAudit(audit.getId(), "Insufficient SKU stock");
                    response.setStatus("FAILED");
                    response.setMessage("Insufficient stock");
                    return ResponseEntity.status(HttpStatus.CONFLICT).body(response);
                }
                
                // Step 3: Update Redis counters atomically (using INCRBY for campaign counter)
                Long newTotalSold = redissonClient.getAtomicLong(campaignKey).addAndGet(request.getQuantity());
                Long newSkuRemaining = skuRemaining - request.getQuantity();
                
                // Verify increment didn't exceed limit
                if (newTotalSold > totalLimit) {
                    // Rollback: restore counter to previous value
                    redissonClient.getAtomicLong(campaignKey).addAndGet(-request.getQuantity());
                    
                    // Fail audit and return conflict
                    auditService.failAudit(audit.getId(), "Campaign limit exceeded");
                    response.setStatus("FAILED");
                    response.setMessage("Campaign sold out");
                    return ResponseEntity.status(HttpStatus.CONFLICT).body(response);
                }
                
                redissonClient.getBucket(skuKey, StringCodec.INSTANCE).set(newSkuRemaining.toString());
                
                // Step 4: Confirm audit record
                auditService.confirmAudit(audit.getId());
                
                response.setStatus("CONFIRMED");
                response.setMessage("Order created successfully");
                return ResponseEntity.status(HttpStatus.CREATED).body(response);
                
            } catch (InterruptedException e) {
                auditService.failAudit(audit.getId(), "Lock acquisition interrupted");
                response.setStatus("FAILED");
                response.setMessage("Lock timeout");
                return ResponseEntity.status(HttpStatus.CONFLICT).body(response);
            }
            
        } catch (Exception e) {
            // Only mark as failed for unexpected exceptions
            if (response.getAuditId() != null) {
                auditService.failAudit(response.getAuditId(), e.getMessage());
            }
            response.setStatus("FAILED");
            response.setMessage("Internal error: " + e.getMessage());
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(response);
        }
    }
    
    @GetMapping("/{auditId}")
    public ResponseEntity<OrderDtos.OrderStatusResponse> getOrderStatus(@PathVariable String auditId) {
        try {
            AuditOrderLog audit = auditService.getAuditById(auditId);
            OrderDtos.OrderStatusResponse response = new OrderDtos.OrderStatusResponse();
            response.setAuditId(audit.getId());
            response.setStatus(audit.getStatus().name());
            response.setCreatedAt(audit.getCreatedAt());
            return ResponseEntity.ok(response);
        } catch (Exception e) {
            return ResponseEntity.status(HttpStatus.NOT_FOUND).build();
        }
    }
}
