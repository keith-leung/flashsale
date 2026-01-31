package com.flashsale.api.service;

import com.flashsale.api.dto.OrderDtos.*;
import com.flashsale.api.entity.*;
import com.flashsale.api.repository.*;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.time.Instant;
import java.time.LocalDateTime;
import java.util.*;
import java.util.AbstractMap;
import java.util.stream.Collectors;

@Service
@Transactional
public class OrderService {

    private final OrderRepository orderRepository;
    private final OrderLineItemRepository orderLineItemRepository;
    private final PaymentRepository paymentRepository;
    private final SkuRepository skuRepository;
    private final InventoryRepository inventoryRepository;
    private final FlashSaleRepository flashSaleRepository;
    private final SnowflakeIdGenerator idGenerator;
    private final RedisCacheService redisCache;
    private final AdaptiveInventoryManager adaptiveInventory;
    private final AllocationManagerV2 allocationManagerV2;
    private final CampaignMemoryAllocator campaignAllocator;

    @Autowired
    public OrderService(
            OrderRepository orderRepository,
            OrderLineItemRepository orderLineItemRepository,
            PaymentRepository paymentRepository,
            SkuRepository skuRepository,
            InventoryRepository inventoryRepository,
            FlashSaleRepository flashSaleRepository,
            SnowflakeIdGenerator idGenerator,
            RedisCacheService redisCache,
            AdaptiveInventoryManager adaptiveInventory,
            AllocationManagerV2 allocationManagerV2,
            CampaignMemoryAllocator campaignAllocator) {
        this.orderRepository = orderRepository;
        this.orderLineItemRepository = orderLineItemRepository;
        this.paymentRepository = paymentRepository;
        this.skuRepository = skuRepository;
        this.inventoryRepository = inventoryRepository;
        this.flashSaleRepository = flashSaleRepository;
        this.idGenerator = idGenerator;
        this.redisCache = redisCache;
        this.adaptiveInventory = adaptiveInventory;
        this.allocationManagerV2 = allocationManagerV2;
        this.campaignAllocator = campaignAllocator;
    }

    @Transactional(readOnly = true)
    public Page<OrderResponseDto> getAllOrders(int page, int size, String customerEmail) {
        Pageable pageable = PageRequest.of(page, size, Sort.by("createdAt").descending());
        Page<Order> orders = orderRepository.findAllWithFilter(customerEmail, pageable);
        return orders.map(this::mapToResponseDto);
    }

    @Transactional(readOnly = true)
    public Optional<OrderResponseDto> getOrderById(UUID id) {
        return orderRepository.findByIdWithLineItems(id)
                .map(this::mapToResponseDto);
    }

    /**
     * Create order with intelligent routing:
     * - If SKU is in active flash sale campaign → Use Variant A (In-memory allocation)
     * - Otherwise → Use Variant Y (database transaction)
     * Frontend sees same API, backend handles routing transparently.
     *
     * OPTIMIZED: Uses CampaignMemoryAllocator.getCampaignForSku() instead of Redis lookup.
     * This eliminates 1 Redis round-trip per request on the hot path.
     */
    public OrderResponseDto createOrder(OrderCreateDto createDto) {
        String orderNumber = String.format("ORD-%d", idGenerator.generate());

        // Step 1: Check if ANY SKU is in active flash sale campaign
        // FAST PATH: Check allocator directly (zero Redis I/O)
        List<UUID> skuIds = createDto.getLineItems().stream()
                .map(OrderLineItemCreateDto::getSkuId)
                .collect(Collectors.toList());

        UUID flashSaleId = null;
        boolean useVariantA = false;

        for (UUID skuId : skuIds) {
            // Zero Redis I/O - checks in-memory campaign registry
            CampaignMemoryAllocator.CampaignLookupResult result = campaignAllocator.getCampaignForSku(skuId);
            if (result.isLoaded) {
                flashSaleId = result.campaignId;
                useVariantA = true;
                break;
            }
        }

        if (useVariantA) {
            // VARIANT A: In-Memory Allocation (Flash Sale Path)
            return createOrderVariantA(createDto, orderNumber, flashSaleId);
        } else {
            // VARIANT Y: Database Transaction (Regular Order Path)
            return createOrderVariantY(createDto, orderNumber);
        }
    }

    /**
     * Variant Y: Traditional database transaction path (4-7 queries per order).
     * Used for regular orders when SKU is NOT in active flash sale.
     */
    private OrderResponseDto createOrderVariantY(OrderCreateDto createDto, String orderNumber) {
        // Create order
        Order order = new Order();
        order.setOrderNumber(orderNumber);
        order.setCustomerEmail(createDto.getCustomerEmail());
        order.setCustomerName(createDto.getCustomerName());
        order.setTaxAmount(createDto.getTaxAmount());
        order.setShippingAmount(createDto.getShippingAmount());
        order.setCurrency(createDto.getCurrency());
        order.setNotes(createDto.getNotes());
        order.setFlashSaleCampaignId(createDto.getFlashSaleCampaignId());

        order = orderRepository.save(order); // Get the order ID

        // Add line items and calculate totals
        BigDecimal subtotal = BigDecimal.ZERO;
        for (OrderLineItemCreateDto itemDto : createDto.getLineItems()) {
            // Get SKU information
            Sku sku = skuRepository.findByIdWithInventoryAndSpu(itemDto.getSkuId())
                    .orElseThrow(() -> new IllegalArgumentException("SKU " + itemDto.getSkuId() + " not found"));

            // Check inventory
            if (sku.getTrackInventory() && sku.getInventory() != null) {
                if (!sku.getInventory().canFulfillQuantity(itemDto.getQuantity())) {
                    throw new IllegalStateException("Insufficient inventory for SKU " + sku.getSkuCode());
                }

                // Reserve inventory
                sku.getInventory().reserveQuantity(itemDto.getQuantity());
                inventoryRepository.save(sku.getInventory());
            }

            // Check for active flash sale campaign and apply flash price
            FlashSale activeCampaign = null;
            if (sku.getSpuId() != null) {
                LocalDateTime now = LocalDateTime.now();
                List<FlashSale> campaigns = flashSaleRepository.findAll();
                activeCampaign = campaigns.stream()
                    .filter(c -> c.getSpuId().equals(sku.getSpuId()))
                    .filter(c -> c.getIsActive())
                    .filter(c -> "active".equals(c.getStatus()))
                    .filter(c -> !c.getStartTime().isAfter(now) && !c.getEndTime().isBefore(now))
                    .findFirst()
                    .orElse(null);
            }

            // Create line item - use flash price if campaign is active
            BigDecimal unitPrice;
            if (activeCampaign != null) {
                unitPrice = itemDto.getUnitPrice() != null ? itemDto.getUnitPrice() : activeCampaign.getFlashPrice();
            } else {
                unitPrice = itemDto.getUnitPrice() != null ? itemDto.getUnitPrice() : sku.getPrice();
            }
            BigDecimal totalPrice = unitPrice.multiply(BigDecimal.valueOf(itemDto.getQuantity()));

            OrderLineItem lineItem = new OrderLineItem();
            lineItem.setOrderId(order.getId());
            lineItem.setSkuId(sku.getId());
            lineItem.setQuantity(itemDto.getQuantity());
            lineItem.setUnitPrice(unitPrice);
            lineItem.setTotalPrice(totalPrice);
            lineItem.setProductName(sku.getSpu() != null ? sku.getSpu().getName() : (sku.getName() != null ? sku.getName() : "Product"));
            lineItem.setSkuCode(sku.getSkuCode());

            orderLineItemRepository.save(lineItem);
            subtotal = subtotal.add(totalPrice);
        }

        // Update order totals
        order.setSubtotal(subtotal);
        order.setTotalAmount(subtotal.add(order.getTaxAmount()).add(order.getShippingAmount()));
        order = orderRepository.save(order);

        return getOrderById(order.getId()).orElseThrow();
    }

    /**
     * Variant A: Dual-layer inventory with preallocated memory (99%+ zero network I/O)
     *
     * Architecture:
     * - Layer 1: SPU counter (campaign-wide limit) - enforces total campaign limit
     * - Layer 2: SKU caches (per-SKU inventory) - tracks individual variants
     *
     * Flow: Check SPU counter → decrement → check SKU cache → decrement → success
     * If SPU depleted: async refill from Redis pool (non-blocking)
     *
     * Orders queue to local buffer for fire-and-forget write-back.
     *
     * CRITICAL: NOT_SUPPORTED propagation prevents DB transaction overhead for in-memory operations
     */
    @Transactional(propagation = Propagation.NOT_SUPPORTED)
    private OrderResponseDto createOrderVariantA(OrderCreateDto createDto, String orderNumber, UUID flashSaleId) {
        // Track reservation results
        List<ReservedItem> reservedItems = new ArrayList<>();
        BigDecimal totalAmount = BigDecimal.ZERO;

        try {
            // Reserve each line item using CampaignMemoryAllocator
            for (OrderLineItemCreateDto itemDto : createDto.getLineItems()) {
                UUID skuId = itemDto.getSkuId();
                int quantity = itemDto.getQuantity();
                BigDecimal itemSubtotal = BigDecimal.ZERO;

                // Reserve items one by one using dual-layer CampaignMemoryAllocator
                for (int i = 0; i < quantity; i++) {
                    CampaignMemoryAllocator.ReservationResult result =
                        campaignAllocator.reserveItem(flashSaleId, skuId);

                    if (!result.success) {
                        switch (result.priceType) {
                            case "sold_out":
                                throw new IllegalStateException("SKU " + skuId + " sold out");
                            case "not_allocated":
                                throw new IllegalStateException("SKU " + skuId + " not available on this server");
                            case "not_loaded":
                                throw new IllegalStateException("Campaign " + flashSaleId + " not loaded");
                            case "ordinary":
                                throw new IllegalStateException("Campaign " + flashSaleId + " sold out");
                            default:
                                throw new IllegalStateException("Failed to reserve SKU " + skuId);
                        }
                    }

                    itemSubtotal = itemSubtotal.add(result.price);
                }

                totalAmount = totalAmount.add(itemSubtotal);
                reservedItems.add(new ReservedItem(
                    skuId, quantity, "flash",
                    itemSubtotal.divide(BigDecimal.valueOf(quantity), 2, java.math.RoundingMode.HALF_UP)
                ));
            }

            // FIRE-AND-FORGET: Queue to local buffer (zero blocking)
            Map<String, Object> orderPayload = new HashMap<>();
            orderPayload.put("order_number", orderNumber);
            orderPayload.put("customer_email", createDto.getCustomerEmail());
            orderPayload.put("customer_name", createDto.getCustomerName() != null ? createDto.getCustomerName() : "");
            orderPayload.put("flash_sale_id", flashSaleId.toString());
            orderPayload.put("total_amount", totalAmount.toString());
            orderPayload.put("created_at", System.currentTimeMillis());

            List<Map<String, Object>> lineItems = new ArrayList<>();
            for (ReservedItem item : reservedItems) {
                Map<String, Object> lineItem = new HashMap<>();
                lineItem.put("sku_id", item.skuId.toString());
                lineItem.put("quantity", item.quantity);
                lineItem.put("unit_price", item.unitPrice.toString());
                lineItems.add(lineItem);
            }
            orderPayload.put("line_items", lineItems);

            campaignAllocator.queueOrderFireAndForget(orderPayload);

            // Build immediate response
            OrderResponseDto response = new OrderResponseDto();
            response.setId(UUID.randomUUID());
            response.setOrderNumber(orderNumber);
            response.setCustomerEmail(createDto.getCustomerEmail());
            response.setCustomerName(createDto.getCustomerName());
            response.setSubtotal(totalAmount);
            response.setTaxAmount(BigDecimal.ZERO);
            response.setShippingAmount(BigDecimal.ZERO);
            response.setTotalAmount(totalAmount);
            response.setCurrency(createDto.getCurrency() != null ? createDto.getCurrency() : "USD");
            response.setStatus(OrderStatus.pending);
            response.setFlashSaleCampaignId(flashSaleId);
            response.setCreatedAt(LocalDateTime.now());
            response.setUpdatedAt(LocalDateTime.now());

            return response;

        } catch (Exception e) {
            throw e;
        }
    }


    /**
     * Helper class to track reserved items
     */
    private static class ReservedItem {
        final UUID skuId;
        final int quantity;
        final String priceType;
        final BigDecimal unitPrice;

        ReservedItem(UUID skuId, int quantity, String priceType, BigDecimal unitPrice) {
            this.skuId = skuId;
            this.quantity = quantity;
            this.priceType = priceType;
            this.unitPrice = unitPrice;
        }
    }

    public Optional<OrderResponseDto> updateOrderStatus(UUID id, String status) {
        try {
            OrderStatus orderStatus = OrderStatus.valueOf(status.toUpperCase());
            
            return orderRepository.findById(id)
                    .map(order -> {
                        order.setStatus(orderStatus);
                        orderRepository.save(order);
                        return mapToResponseDto(order);
                    });
        } catch (IllegalArgumentException e) {
            throw new IllegalArgumentException("Invalid order status: " + status);
        }
    }

    public boolean cancelOrder(UUID id) {
        Optional<Order> orderOpt = orderRepository.findByIdWithLineItems(id);
        if (orderOpt.isEmpty()) {
            return false;
        }

        Order order = orderOpt.get();
        
        // Release reserved inventory
        for (OrderLineItem lineItem : order.getLineItems()) {
            inventoryRepository.findBySkuId(lineItem.getSkuId())
                    .ifPresent(inventory -> {
                        inventory.releaseQuantity(lineItem.getQuantity());
                        inventoryRepository.save(inventory);
                    });
        }

        order.setStatus(OrderStatus.cancelled);
        orderRepository.save(order);
        
        return true;
    }

    public PaymentResponseDto createPayment(UUID orderId, PaymentCreateDto dto) {
        Order order = orderRepository.findById(orderId)
                .orElseThrow(() -> new IllegalArgumentException("Order not found"));

        Payment payment = new Payment();
        payment.setOrderId(orderId);
        payment.setAmount(dto.getAmount());
        payment.setCurrency(dto.getCurrency());
        payment.setPaymentMethod(dto.getPaymentMethod());
        payment.setReferenceNumber(dto.getReferenceNumber());
        payment.setNotes(dto.getNotes());

        // Simulate payment processing
        if (dto.getAmount().compareTo(BigDecimal.ZERO) > 0) {
            payment.setStatus(PaymentStatus.captured);
            payment.setGatewayTransactionId("txn_" + Instant.now().getEpochSecond());
            
            // Update order status
            order.setStatus(OrderStatus.confirmed);
            orderRepository.save(order);
        }

        payment = paymentRepository.save(payment);
        return mapPaymentToResponseDto(payment);
    }

    private OrderResponseDto mapToResponseDto(Order order) {
        OrderResponseDto dto = new OrderResponseDto();
        dto.setId(order.getId());
        dto.setOrderNumber(order.getOrderNumber());
        dto.setCustomerEmail(order.getCustomerEmail());
        dto.setCustomerName(order.getCustomerName());
        dto.setSubtotal(order.getSubtotal());
        dto.setTaxAmount(order.getTaxAmount());
        dto.setShippingAmount(order.getShippingAmount());
        dto.setTotalAmount(order.getTotalAmount());
        dto.setCurrency(order.getCurrency());
        dto.setStatus(order.getStatus());
        dto.setNotes(order.getNotes());
        dto.setFlashSaleCampaignId(order.getFlashSaleCampaignId());
        dto.setCreatedAt(order.getCreatedAt());
        dto.setUpdatedAt(order.getUpdatedAt());

        List<OrderLineItemResponseDto> lineItemDtos = order.getLineItems().stream()
                .map(this::mapLineItemToResponseDto)
                .collect(Collectors.toList());
        dto.setLineItems(lineItemDtos);

        return dto;
    }

    private OrderLineItemResponseDto mapLineItemToResponseDto(OrderLineItem lineItem) {
        OrderLineItemResponseDto dto = new OrderLineItemResponseDto();
        dto.setId(lineItem.getId());
        dto.setSkuId(lineItem.getSkuId());
        dto.setQuantity(lineItem.getQuantity());
        dto.setUnitPrice(lineItem.getUnitPrice());
        dto.setTotalPrice(lineItem.getTotalPrice());
        dto.setProductName(lineItem.getProductName());
        dto.setSkuCode(lineItem.getSkuCode());
        dto.setCreatedAt(lineItem.getCreatedAt());
        return dto;
    }

    private PaymentResponseDto mapPaymentToResponseDto(Payment payment) {
        PaymentResponseDto dto = new PaymentResponseDto();
        dto.setId(payment.getId());
        dto.setOrderId(payment.getOrderId());
        dto.setAmount(payment.getAmount());
        dto.setCurrency(payment.getCurrency());
        dto.setPaymentMethod(payment.getPaymentMethod());
        dto.setGatewayTransactionId(payment.getGatewayTransactionId());
        dto.setStatus(payment.getStatus());
        dto.setReferenceNumber(payment.getReferenceNumber());
        dto.setNotes(payment.getNotes());
        dto.setCreatedAt(payment.getCreatedAt());
        dto.setUpdatedAt(payment.getUpdatedAt());
        return dto;
    }
}
