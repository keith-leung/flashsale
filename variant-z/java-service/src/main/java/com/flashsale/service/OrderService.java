package com.flashsale.service;

import com.flashsale.entity.*;
import com.flashsale.exception.InsufficientStockException;
import com.flashsale.exception.SoldOutException;
import com.flashsale.repository.*;
import com.flashsale.service.dto.*;
import jakarta.transaction.Transactional;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Random;
import java.util.UUID;

/**
 * Order service - Variant Z (Token Pre-Allocation with Synchronous Persistence).
 * 
 * Handles both regular orders and flash sale orders:
 * - Flash sale: Use Redis token acquisition
 * - Regular: Use database transactions (Variant Y path)
 */
@Service
public class OrderService {

    private static final Logger logger = LoggerFactory.getLogger(OrderService.class);

    private final OrderRepository orderRepository;
    private final OrderLineItemRepository orderLineItemRepository;
    private final PaymentRepository paymentRepository;
    private final InventoryRepository inventoryRepository;
    private final SKURepository skuRepository;
    private final FlashSaleCampaignRepository campaignRepository;
    private final TokenService tokenService;

    public OrderService(OrderRepository orderRepository,
                    OrderLineItemRepository orderLineItemRepository,
                    PaymentRepository paymentRepository,
                    InventoryRepository inventoryRepository,
                    SKURepository skuRepository,
                    FlashSaleCampaignRepository campaignRepository,
                    TokenService tokenService) {
        this.orderRepository = orderRepository;
        this.orderLineItemRepository = orderLineItemRepository;
        this.paymentRepository = paymentRepository;
        this.inventoryRepository = inventoryRepository;
        this.skuRepository = skuRepository;
        this.campaignRepository = campaignRepository;
        this.tokenService = tokenService;
    }

    /**
     * Create order with token pre-allocation (Variant Z).
     */
    @Transactional
    public OrderResponse createOrder(OrderRequest orderRequest) {
        long requestStart = System.currentTimeMillis();
        
        // Get line item
        OrderRequest.LineItem lineItem = orderRequest.getLineItems().get(0);
        String skuId = lineItem.getSkuId();
        int quantity = lineItem.getQuantity();

        // Get SKU with inventory
        Optional<SKU> skuOpt = skuRepository.findByIdWithInventory(skuId);
        if (skuOpt.isEmpty()) {
            throw new IllegalArgumentException("SKU not found");
        }
        
        SKU sku = skuOpt.get();
        Inventory inventory = sku.getInventory();
        
        // Check if SKU belongs to active flash sale campaign
        Optional<FlashSaleCampaign> campaignOpt = getActiveCampaignForSKU(sku.getSpuId());
        
        String campaignIdRef = null;
        if (campaignOpt.isPresent()) {
            // Variant Z path: Use token pre-allocation
            FlashSaleCampaign campaign = campaignOpt.get();
            logger.info("SKU {} belongs to campaign {}", skuId, campaign.getId());
            
            // Check if campaign is sold out
            if (tokenService.isCampaignSoldOut(campaign.getId())) {
                throw new SoldOutException(
                    new FlashSaleSoldOutResponse(campaign.getId(), Instant.now().toString())
                );
            }
            
            // Acquire token atomically via Redis
            Map<String, Object> tokenResult = tokenService.acquireToken(
                campaign.getId(), skuId, quantity
            );
            
            if (tokenResult.containsKey("err")) {
                String errorCode = (String) tokenResult.get("err");
                logger.warn("Token acquisition failed: {}", errorCode);
                
                if ("TOKEN_NOT_AVAILABLE".equals(errorCode)) {
                    throw new SoldOutException(
                        new FlashSaleSoldOutResponse(campaign.getId(), Instant.now().toString())
                    );
                } else if ("INSUFFICIENT_STOCK".equals(errorCode)) {
                    throw new InsufficientStockException(
                        new InsufficientStockResponse(skuId, 
                            ((Number) tokenResult.getOrDefault("remaining_stock", 0)).intValue())
                    );
                } else {
                    throw new RuntimeException("Token acquisition error: " + errorCode);
                }
            }
            
            // Token acquired successfully
            logger.info("Token acquired for campaign {}, SKU {}", campaign.getId(), skuId);
            campaignIdRef = campaign.getId();
        } else {
            // Variant Y path: Use database transactions (no flash sale)
            logger.info("SKU {} not in active campaign - using Variant Y path", skuId);
            campaignIdRef = null;
            
            // Validate inventory
            if (inventory.getQuantity() < quantity) {
                throw new InsufficientStockException(
                    new InsufficientStockResponse(skuId, inventory.getQuantity())
                );
            }
        }
        
        // Generate order ID and number
        String orderId = UUID.randomUUID().toString();
        long timestamp = System.nanoTime() / 1000; // Microsecond precision
        int randomSuffix = 1000 + new Random().nextInt(9000); // 4-digit random suffix
        String orderNumber = String.format("ORD-%d-%d", timestamp, randomSuffix);
        
        // Synchronously persist order to database (Variant Z requirement)
        persistOrderSynchronously(
            orderId, orderNumber, 
            orderRequest.getCustomerName(), 
            orderRequest.getCustomerEmail(),
            skuId, quantity, sku.getPrice(), 
            campaignIdRef, sku, inventory
        );
        
        long duration = System.currentTimeMillis() - requestStart;
        logger.info("Order created (sync): {} ({}ms)", orderId, duration);
        
        double totalAmount = quantity * sku.getPrice();
        return new OrderResponse(orderId, "pending", totalAmount, orderRequest.getCustomerEmail());
    }

    /**
     * Get active flash sale campaign for SPU.
     */
    private Optional<FlashSaleCampaign> getActiveCampaignForSKU(String spuId) {
        Instant now = Instant.now();
        return campaignRepository.findBySPUAndActive(spuId, now);
    }

    /**
     * Synchronously persist order to database (Variant Z requirement).
     * 
     * This is the hot path - writes to database synchronously before returning 201.
     * All operations happen in a single transaction to ensure ACID guarantees.
     */
    private void persistOrderSynchronously(
        String orderId,
        String orderNumber,
        String customerName,
        String customerEmail,
        String skuId,
        int quantity,
        double unitPrice,
        String campaignId,
        SKU sku,
        Inventory inventory
    ) {
        // Calculate totals
        double subtotal = quantity * unitPrice;
        double totalAmount = subtotal; // No tax/shipping for flash sales
        
        // Create order
        Order order = new Order();
        order.setId(orderId);
        order.setOrderNumber(orderNumber);
        order.setCustomerEmail(customerEmail);
        order.setCustomerName(customerName);
        order.setSubtotal(subtotal);
        order.setTaxAmount(0.0);
        order.setShippingAmount(0.0);
        order.setTotalAmount(totalAmount);
        order.setCurrency("USD");
        order.setStatus("pending");
        order.setFlashSaleCampaignId(campaignId);
        orderRepository.save(order);
        
        // Create order line item
        OrderLineItem lineItem = new OrderLineItem();
        lineItem.setId(UUID.randomUUID().toString());
        lineItem.setOrderId(orderId);
        lineItem.setSkuId(skuId);
        lineItem.setQuantity(quantity);
        lineItem.setUnitPrice(unitPrice);
        lineItem.setTotalPrice(subtotal);
        lineItem.setProductName(sku.getName());
        lineItem.setSkuCode(sku.getSkuCode());
        orderLineItemRepository.save(lineItem);
        
        // Create payment record
        Payment payment = new Payment();
        payment.setId(UUID.randomUUID().toString());
        payment.setOrderId(orderId);
        payment.setAmount(totalAmount);
        payment.setCurrency("USD");
        payment.setPaymentMethod("flash_sale");
        payment.setGatewayTransactionId("TXN-" + System.nanoTime() / 1_000_000);
        payment.setGatewayResponse("");
        payment.setStatus("authorized");
        paymentRepository.save(payment);
        
        // Update inventory
        inventory.setQuantity(inventory.getQuantity() - quantity);
        inventory.setReservedQuantity(inventory.getReservedQuantity() + quantity);
        inventoryRepository.save(inventory);
        
        // Update campaign sold quantity (if flash sale)
        if (campaignId != null) {
            Optional<FlashSaleCampaign> campaignOpt = campaignRepository.findById(campaignId);
            if (campaignOpt.isPresent()) {
                FlashSaleCampaign campaign = campaignOpt.get();
                campaign.setSoldQuantity(campaign.getSoldQuantity() + quantity);
                campaign.setUpdatedAt(Instant.now());
                campaignRepository.save(campaign);
            }
        }
        
        logger.debug("Order {} persisted synchronously to database", orderId);
    }
}